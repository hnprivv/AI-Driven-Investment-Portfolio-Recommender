from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from modules.ai.feature_eng import (
    compute_features, compute_raw_log_returns,
    FeatureNormalizer, STATE_DIM,
)
from modules.ai.market_env import AdvisoryEnv
from modules.ai.ppo_agent  import PPOAgent

MODEL_DIR = os.path.join(ROOT, "modules", "model", "ppo_psx")
LOG_PATH  = os.path.join(MODEL_DIR, "training_log.json")

PSX_BASE = "https://psxterminal.com"
PSX_WS   = "wss://psxterminal.com/"

# ── PSX universe (plain symbols, no .KA suffix) ───────────────────────────────
# Expanded training universe — ~80 liquid PSX equities across all major sectors.
# The model learns general PSX market patterns and generalises to any symbol
# at inference time, just like the US model works on any US ticker.
# Symbols with -MAY/-ETF/indices are excluded — plain equity symbols only.
DEFAULT_TICKERS = [
    # Banking (12)
    "HBL", "UBL", "MCB", "NBP", "BAHL", "MEBL", "FABL",
    "AKBL", "SNBL", "BOK", "BOP", "HMB",
    # Energy / Oil & Gas / Power (10)
    "OGDC", "PPL", "PSO", "SNGP", "SSGC", "HUBC",
    "KAPCO", "PNSC", "MARI", "POL",
    # Fertiliser (5)
    "ENGRO", "EFERT", "FFC", "FATIMA", "DAWH",
    # Cement (8)
    "LUCK", "DGKC", "MLCF", "CHCC", "FCCL", "PIOC", "KOHC", "ACPL",
    # Technology / Telecom (5)
    "TRG", "AIRLINK", "SYS", "NETSOL", "PTC",
    # Consumer / Food / Retail (6)
    "NESTLE", "COLG", "UNITY", "TREET", "QUICE", "BATA",
    # Pharma (5)
    "SEARL", "FEROZ", "GLAXO", "HINOON", "AGP",
    # Steel / Engineering / Industrial (6)
    "MUGHAL", "ISL", "ASL", "ASTL", "CSAP", "ATRL",
    # Refinery / Chemical / Petrochemical (5)
    "NRL", "EPCL", "LOTCHEM", "ICI", "COLG",
    # Textile (7)
    "NML", "NCL", "MTL", "GATM", "AMTEX", "KTML", "GHNI",
    # Insurance / Misc (5)
    "AVN", "JVDC", "HCAR", "PAEL", "LOADS",
]
# Remove any duplicates while preserving order
DEFAULT_TICKERS = list(dict.fromkeys(DEFAULT_TICKERS))

HYPERPARAMS = dict(
    total_steps  = 3_000_000,
    rollout_len  = 512,
    episode_len  = 60,     # shorter episodes → more diverse market conditions per update
    lr           = 1e-4,   # slower learning → more stable policy
    gamma        = 0.99,
    gae_lambda   = 0.95,
    clip_eps     = 0.15,   # tighter clipping → prevents overconfident updates
    vf_coef      = 0.5,
    ent_coef     = 0.02,   # stronger exploration → prevents SELL collapse
    n_epochs     = 4,
    batch_size   = 64,
    hidden       = 128,
    eval_every   = 200_000,
    save_every   = 200_000,
)


# ── PSX Terminal helpers ──────────────────────────────────────────────────────

def list_symbols() -> list[str]:
    """Return list of Regular Market symbol strings from PSX Terminal."""
    try:
        r = requests.get(f"{PSX_BASE}/api/symbols", timeout=10)
        d = r.json()
        if not d.get("success"):
            return []
        raw = d.get("data", [])
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                mkt = item.get("market", "REG")
                if mkt == "REG":
                    result.append(item.get("symbol", ""))
        return [s for s in result if s]
    except Exception as e:
        print(f"  Symbol fetch error: {e}")
        return []


def fetch_yfinance(symbol: str, period_years: int = 5) -> pd.DataFrame | None:
    """
    Fetch historical daily OHLCV from Yahoo Finance using the .KA suffix.
    PSX symbols on yfinance: HBL -> HBL.KA, ENGRO -> ENGRO.KA etc.
    Falls back to plain symbol if .KA returns nothing.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed.\n  Run: pip install yfinance")
        sys.exit(1)

    end   = pd.Timestamp.today()
    start = end - pd.DateOffset(years=period_years)

    for ticker_str in [f"{symbol}.KA", symbol]:
        try:
            raw = yf.download(
                ticker_str,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=True,
                progress=False,
                multi_level_index=False,
            )
            if raw is None or len(raw) < 200:
                continue
            raw.columns = [c.lower() for c in raw.columns]
            if "close" not in raw.columns:
                continue
            df = raw[["open", "high", "low", "close", "volume"]].copy()
            df.index = pd.to_datetime(df.index)
            df = df[df["volume"] > 0].dropna()
            if len(df) >= 200:
                return df
        except Exception:
            continue
    return None


def download_data(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """
    Download 5 years of daily OHLCV from Yahoo Finance (.KA suffix) for each PSX ticker.
    psxterminal.com is used only for live price ticks on the frontend.
    """
    try:
        import yfinance  # noqa
    except ImportError:
        print("ERROR: yfinance not installed.\n  Run: pip install yfinance")
        sys.exit(1)

    print(f"\nDownloading 5yr daily OHLCV from Yahoo Finance (.KA) for {len(tickers)} symbols …\n")
    data: dict[str, pd.DataFrame] = {}
    for sym in tickers:
        df = fetch_yfinance(sym)
        if df is None:
            print(f"  {sym:12s}  SKIPPED (not found on Yahoo Finance)")
            continue
        data[sym] = df
        print(f"  {sym:12s}  {len(df)} bars  ({df.index[0].date()} -> {df.index[-1].date()})")
    if not data:
        print("\nERROR: No data fetched. Run: pip install yfinance")
        sys.exit(1)
    print(f"\nLoaded {len(data)}/{len(tickers)} symbols.\n")
    return data


# ── Feature prep ─────────────────────────────────────────────────────────────

def prepare_datasets(raw_data, train_frac=0.8):
    print("Computing technical features …")
    raw_feats = {}
    for sym, df in raw_data.items():
        try:
            feat_df  = compute_features(df)
            raw_rets = compute_raw_log_returns(df).reindex(feat_df.index).fillna(0.0)
            if len(feat_df) >= 100:
                raw_feats[sym] = (feat_df, raw_rets.values)
                print(f"  {sym:12s}  {len(feat_df)} rows")
        except Exception as e:
            print(f"  {sym} error: {e}")

    if not raw_feats:
        print("ERROR: Feature computation failed for all symbols.")
        sys.exit(1)

    all_train = pd.concat(
        [v[0].iloc[:int(len(v[0]) * train_frac)] for v in raw_feats.values()],
        ignore_index=True,
    )
    norm = FeatureNormalizer().fit(all_train)
    print(f"\n  Normaliser fitted on {len(all_train):,} rows from {len(raw_feats)} symbols")

    os.makedirs(MODEL_DIR, exist_ok=True)
    norm.save(os.path.join(MODEL_DIR, "normalizer.pkl"))
    print(f"  Normaliser saved → {MODEL_DIR}/normalizer.pkl\n")

    train_ds, eval_ds = {}, {}
    for sym, (feat_df, rets) in raw_feats.items():
        split     = int(len(feat_df) * train_frac)
        feat_norm = norm.transform(feat_df)
        train_ds[sym] = {"feat_norm": feat_norm[:split], "rets": rets[:split]}
        eval_ds[sym]  = {"feat_norm": feat_norm[split:], "rets": rets[split:]}
    return train_ds, eval_ds, norm


# ── Training helpers ──────────────────────────────────────────────────────────

def _make_env(datasets, episode_len):
    sym     = np.random.choice(list(datasets.keys()))
    ds      = datasets[sym]
    profile = AdvisoryEnv.sample_profile()
    env     = AdvisoryEnv.from_arrays(ds["feat_norm"], ds["rets"], profile, episode_len)
    return env, sym


def _evaluate(agent, eval_ds, episode_len, n_episodes=50):
    returns = []
    agent.ac.eval()
    for _ in range(n_episodes):
        env, _ = _make_env(eval_ds, episode_len)
        try:
            obs = env.reset()
        except ValueError:
            continue
        total, done = 0.0, False
        while not done:
            action, _, _, _ = agent.ac.act(obs)
            obs, r, done, _ = env.step(action)
            total += r
        returns.append(total)
    agent.ac.eval()
    return float(np.mean(returns)) if returns else 0.0


# ── Main training loop ────────────────────────────────────────────────────────

def train(args):
    hp      = {**HYPERPARAMS}
    if args.steps:
        hp["total_steps"] = args.steps
    tickers = args.tickers or DEFAULT_TICKERS

    raw_data              = download_data(tickers)
    train_ds, eval_ds, _ = prepare_datasets(raw_data)

    agent = PPOAgent(
        obs_dim=STATE_DIM, hidden=hp["hidden"], lr=hp["lr"],
        gamma=hp["gamma"], gae_lambda=hp["gae_lambda"], clip_eps=hp["clip_eps"],
        vf_coef=hp["vf_coef"], ent_coef=hp["ent_coef"],
        n_epochs=hp["n_epochs"], batch_size=hp["batch_size"],
    )

    log, ep_returns = [], deque(maxlen=100)
    ep_return, best_eval = 0.0, -np.inf
    metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
    t0 = time.time()

    env, _ = _make_env(train_ds, hp["episode_len"])
    obs    = env.reset()

    print(f"\n{'='*62}")
    print(f"  AIPRS PSX PPO Training   steps = {hp['total_steps']:,}")
    print(f"  symbols  : {list(train_ds.keys())}")
    print(f"  obs_dim  : {STATE_DIM}   actions: HOLD / BUY / SELL")
    print(f"  model dir: {MODEL_DIR}")
    print(f"{'='*62}\n")

    for step in range(1, hp["total_steps"] + 1):
        action, lp, val, _ = agent.ac.act(obs)
        next_obs, reward, done, _ = env.step(action)
        ep_return += reward
        agent.store(obs, action, reward, val, lp, done)
        obs = next_obs

        if done:
            ep_returns.append(ep_return)
            ep_return = 0.0
            env, _ = _make_env(train_ds, hp["episode_len"])
            obs    = env.reset()

        if step % hp["rollout_len"] == 0:
            _, _, last_val, _ = agent.ac.act(obs)
            metrics = agent.update(last_val)
            if step % 10_000 == 0:
                mean_ret = np.mean(ep_returns) if ep_returns else 0.0
                fps      = step / max(time.time() - t0, 1)
                ent      = metrics["entropy"]
                flag     = "  ⚠ COLLAPSE" if ent < 0.03 else "  ⚠ EXPLOSION" if ent > 0.40 else ""
                print(f"  step {step:>9,}  ret={mean_ret:+.4f}  "
                      f"p={metrics['policy_loss']:+.4f}  v={metrics['value_loss']:.4f}  "
                      f"ent={ent:.3f}{flag}  fps={fps:.0f}")

        if step % hp["eval_every"] == 0:
            eval_ret = _evaluate(agent, eval_ds, hp["episode_len"], n_episodes=50)
            print(f"\n  [EVAL  step={step:,}]  mean_return = {eval_ret:+.4f}")
            log.append({
                "step": step,
                "train_return": float(np.mean(ep_returns)) if ep_returns else 0.0,
                "eval_return":  float(eval_ret),
                **{k: float(v) for k, v in metrics.items()},
            })
            with open(LOG_PATH, "w") as f:
                json.dump(log, f, indent=2)
            if eval_ret > best_eval:
                best_eval = eval_ret
                agent.save(MODEL_DIR)
                print(f"  → New best {best_eval:+.4f}. Saved.")
            print()
        elif step % hp["save_every"] == 0:
            agent.save(MODEL_DIR)

    agent.save(MODEL_DIR)
    print(f"\nDone in {(time.time()-t0)/60:.1f} min.  Best eval: {best_eval:+.4f}")
    print(f"Artefacts saved to: {MODEL_DIR}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Train AIPRS PPO on PSX (Pakistan Stock Exchange)")
    p.add_argument("--steps",        type=int, default=None)
    p.add_argument("--tickers",      nargs="+", default=None,
                   help="e.g. ENGRO HBL OGDC  (no .KA suffix)")
    p.add_argument("--eval-only",    action="store_true")
    p.add_argument("--list-symbols", action="store_true")
    args = p.parse_args()

    if args.list_symbols:
        print("Fetching symbols from psxterminal.com …\n")
        syms = list_symbols()
        if not syms:
            print("No symbols returned. Check internet connection.")
            return
        print(f"Regular Market — {len(syms)} symbols:")
        for i, s in enumerate(syms):
            print(f"  {s:12s}", end="\n" if (i + 1) % 6 == 0 else "")
        print()
        return

    if args.eval_only:
        agent    = PPOAgent.load(MODEL_DIR)
        tickers  = args.tickers or DEFAULT_TICKERS
        raw_data = download_data(tickers)
        _, eval_ds, _ = prepare_datasets(raw_data, train_frac=0.0)
        ret = _evaluate(agent, eval_ds, episode_len=120, n_episodes=200)
        print(f"PSX Eval mean return: {ret:+.4f}")
    else:
        train(args)


if __name__ == "__main__":
    main()