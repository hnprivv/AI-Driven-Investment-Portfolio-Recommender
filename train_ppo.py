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
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from modules.ai.feature_eng import (
    compute_features,
    compute_raw_log_returns,
    FeatureNormalizer,
    STATE_DIM,
)
from modules.ai.market_env import AdvisoryEnv
from modules.ai.ppo_agent  import PPOAgent

MODEL_DIR = os.path.join(ROOT, "modules", "model", "ppo")
LOG_PATH  = os.path.join(MODEL_DIR, "training_log.json")

ALPACA_DATA_URL = "https://data.alpaca.markets/v2"

# ── Training universe ─────────────────────────────────────────────────────────
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META",  "JPM",  "BAC",  "JNJ",
    "SPY",  "QQQ",   "IWM",  "GLD",
]

# ── Hyperparameters ───────────────────────────────────────────────────────────
HYPERPARAMS = dict(
    total_steps  = 3_000_000,
    rollout_len  = 512,
    episode_len  = 120,
    lr           = 2e-4,
    gamma        = 0.99,
    gae_lambda   = 0.95,
    clip_eps     = 0.2,
    vf_coef      = 0.5,
    ent_coef     = 0.005,   # symmetric reward removes HOLD dominance; 0.005 sustains exploration
    n_epochs     = 4,
    batch_size   = 64,
    hidden       = 128,
    lookback_days = 1825,    # ~5 years of calendar days
    eval_every   = 200_000,
    save_every   = 200_000,
)


# ── Alpaca data download ───────────────────────────────────────────────────────

def _alpaca_headers() -> dict | None:
    key    = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        return None
    return {
        "APCA-API-KEY-ID":     key,
        "APCA-API-SECRET-KEY": secret,
        "accept": "application/json",
    }


def _fetch_daily_bars(symbol: str, lookback_days: int) -> pd.DataFrame | None:
    """
    Fetch up to `lookback_days` of daily bars for `symbol` from Alpaca.
    Uses sort=desc so the limit anchors to today, then reverses for
    chronological order.
    Returns a DataFrame with columns [timestamp, open, high, low, close, volume]
    or None on failure.
    """
    headers = _alpaca_headers()
    if headers is None:
        return None

    end   = pd.Timestamp.utcnow()
    start = end - pd.Timedelta(days=lookback_days)

    params = {
        "timeframe": "1Day",
        "start":     start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end":       end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit":     10_000,
        "feed":      "iex",
        "sort":      "desc",
    }
    try:
        url  = f"{ALPACA_DATA_URL}/stocks/{symbol}/bars"
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        bars = resp.json().get("bars", [])
        if not bars:
            return None
        df = pd.DataFrame(bars)
        df.rename(columns={"t": "timestamp", "o": "open", "h": "high",
                            "l": "low", "c": "close", "v": "volume"}, inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.iloc[::-1].reset_index(drop=True)   # chronological order
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"    Alpaca fetch error for {symbol}: {e}")
        return None


def download_data(tickers: list[str], lookback_days: int) -> dict[str, pd.DataFrame]:
    """
    Fetch daily OHLCV from Alpaca for each ticker.
    Returns dict {ticker: DataFrame}.  Skips tickers that fail.
    """
    headers = _alpaca_headers()
    if headers is None:
        print(
            "ERROR: Alpaca API keys not found.\n"
            "Add ALPACA_API_KEY and ALPACA_SECRET_KEY to your .env file."
        )
        sys.exit(1)

    end_date   = pd.Timestamp.utcnow().date()
    start_date = (pd.Timestamp.utcnow() - pd.Timedelta(days=lookback_days)).date()
    print(f"\nDownloading daily bars from Alpaca for {len(tickers)} tickers "
          f"({start_date} → {end_date}) …")

    data: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        df = _fetch_daily_bars(ticker, lookback_days)
        if df is None or len(df) < 200:
            print(f"  {ticker:8s}  SKIPPED (insufficient data: "
                  f"{len(df) if df is not None else 0} bars)")
            continue
        data[ticker] = df
        print(f"  {ticker:8s}  {len(df)} bars")

    if not data:
        print("ERROR: No data downloaded. Check API keys and internet connection.")
        sys.exit(1)

    return data


# ── Feature preparation ───────────────────────────────────────────────────────

def prepare_datasets(
    raw_data: dict[str, pd.DataFrame],
    train_frac: float = 0.8,
) -> tuple[dict, dict, FeatureNormalizer]:
    """
    Compute features for every ticker, fit a single FeatureNormalizer on
    the combined training portion, then split into train/eval dicts.

    Returns (train_dict, eval_dict, normalizer)
    Each dict maps ticker → {"feat_norm": ndarray, "rets": ndarray}.
    """
    print("\nComputing technical features …")
    raw_feats: dict[str, tuple[pd.DataFrame, np.ndarray]] = {}
    for ticker, df in raw_data.items():
        try:
            feat_df  = compute_features(df)
            raw_rets = compute_raw_log_returns(df).reindex(feat_df.index).fillna(0.0)
            if len(feat_df) < 100:
                continue
            raw_feats[ticker] = (feat_df, raw_rets.values)
        except Exception as e:
            print(f"  {ticker} feature error: {e}")

    if not raw_feats:
        print("ERROR: Feature computation failed for all tickers.")
        sys.exit(1)

    # Fit normaliser on training portion of all tickers combined
    all_train = pd.concat(
        [v[0].iloc[: int(len(v[0]) * train_frac)] for v in raw_feats.values()],
        ignore_index=True,
    )
    norm = FeatureNormalizer().fit(all_train)
    n = len(raw_feats)
    print(f"  Normaliser fitted on {len(all_train):,} rows from {n} tickers")

    os.makedirs(MODEL_DIR, exist_ok=True)
    norm.save(os.path.join(MODEL_DIR, "normalizer.pkl"))
    print(f"  Normaliser saved → {MODEL_DIR}/normalizer.pkl")

    train_ds, eval_ds = {}, {}
    for ticker, (feat_df, rets) in raw_feats.items():
        split     = int(len(feat_df) * train_frac)
        feat_norm = norm.transform(feat_df)
        train_ds[ticker] = {"feat_norm": feat_norm[:split], "rets": rets[:split]}
        eval_ds[ticker]  = {"feat_norm": feat_norm[split:], "rets": rets[split:]}

    return train_ds, eval_ds, norm


# ── Training helpers ──────────────────────────────────────────────────────────

def _make_env(datasets: dict, episode_len: int) -> tuple[AdvisoryEnv, str]:
    """Pick a random ticker + random synthetic user profile, return a fresh env."""
    ticker  = np.random.choice(list(datasets.keys()))
    ds      = datasets[ticker]
    profile = AdvisoryEnv.sample_profile()
    env     = AdvisoryEnv.from_arrays(
        ds["feat_norm"], ds["rets"], profile, episode_len
    )
    return env, ticker


# ── Main training loop ────────────────────────────────────────────────────────

def train(args: argparse.Namespace):
    hp      = {**HYPERPARAMS}
    if args.steps:
        hp["total_steps"] = args.steps

    tickers = args.tickers or DEFAULT_TICKERS

    # ── Data ─────────────────────────────────────────────────────────────────
    raw_data              = download_data(tickers, hp["lookback_days"])
    train_ds, eval_ds, _ = prepare_datasets(raw_data)

    # ── Agent ─────────────────────────────────────────────────────────────────
    agent = PPOAgent(
        obs_dim    = STATE_DIM,
        hidden     = hp["hidden"],
        lr         = hp["lr"],
        gamma      = hp["gamma"],
        gae_lambda = hp["gae_lambda"],
        clip_eps   = hp["clip_eps"],
        vf_coef    = hp["vf_coef"],
        ent_coef   = hp["ent_coef"],
        n_epochs   = hp["n_epochs"],
        batch_size = hp["batch_size"],
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log: list[dict]       = []
    ep_returns: deque     = deque(maxlen=100)
    ep_return             = 0.0
    best_eval             = -np.inf
    metrics               = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
    t0                    = time.time()

    env, _ = _make_env(train_ds, hp["episode_len"])
    obs    = env.reset()

    print(f"\n{'='*62}")
    print(f"  AIPRS PPO Training   steps = {hp['total_steps']:,}")
    print(f"  tickers  : {list(train_ds.keys())}")
    print(f"  obs_dim  : {STATE_DIM}   actions : 3 (HOLD / BUY / SELL)")
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

        # ── PPO update ────────────────────────────────────────────────────────
        if step % hp["rollout_len"] == 0:
            _, _, last_val, _ = agent.ac.act(obs)
            metrics = agent.update(last_val)

            if step % 10_000 == 0:
                mean_ret = np.mean(ep_returns) if ep_returns else 0.0
                fps      = step / max(time.time() - t0, 1)
                ent      = metrics["entropy"]
                # Warn if entropy drifts outside the healthy 0.03–0.40 range
                ent_flag = "  ⚠ COLLAPSE" if ent < 0.03 else "  ⚠ EXPLOSION" if ent > 0.40 else ""
                print(
                    f"  step {step:>9,}  "
                    f"ret={mean_ret:+.4f}  "
                    f"p={metrics['policy_loss']:+.4f}  "
                    f"v={metrics['value_loss']:.4f}  "
                    f"ent={ent:.3f}{ent_flag}  "
                    f"fps={fps:.0f}"
                )

        # ── Periodic evaluation ───────────────────────────────────────────────
        if step % hp["eval_every"] == 0:
            eval_ret = _evaluate(agent, eval_ds, hp["episode_len"], n_episodes=50)
            print(f"\n  [EVAL  step={step:,}]  mean_return = {eval_ret:+.4f}")
            entry = {
                "step": step,
                "train_return": float(np.mean(ep_returns)) if ep_returns else 0.0,
                "eval_return":  float(eval_ret),
                **{k: float(v) for k, v in metrics.items()},
            }
            log.append(entry)
            with open(LOG_PATH, "w") as f:
                json.dump(log, f, indent=2)

            if eval_ret > best_eval:
                best_eval = eval_ret
                agent.save(MODEL_DIR)
                print(f"  → New best {best_eval:+.4f}. Saved.")
            print()

        elif step % hp["save_every"] == 0:
            agent.save(MODEL_DIR)

    # ── Final save ────────────────────────────────────────────────────────────
    agent.save(MODEL_DIR)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed/60:.1f} min.  Best eval return: {best_eval:+.4f}")
    print(f"Artefacts saved to: {MODEL_DIR}")


# ── Evaluation helper ─────────────────────────────────────────────────────────

def _evaluate(agent: PPOAgent, eval_ds: dict, episode_len: int,
              n_episodes: int = 50) -> float:
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


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train AIPRS PPO advisory agent")
    parser.add_argument("--steps",     type=int,  default=None,
                        help="Total env steps (default 3_000_000)")
    parser.add_argument("--tickers",   nargs="+", default=None,
                        help="Ticker symbols to train on")
    parser.add_argument("--eval-only", action="store_true",
                        help="Skip training; load saved model and evaluate")
    args = parser.parse_args()

    if args.eval_only:
        try:
            agent = PPOAgent.load(MODEL_DIR)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        tickers  = args.tickers or DEFAULT_TICKERS
        raw_data = download_data(tickers, lookback_days=730)
        _, eval_ds, _ = prepare_datasets(raw_data, train_frac=0.0)
        ret = _evaluate(agent, eval_ds, episode_len=120, n_episodes=200)
        print(f"Eval mean return: {ret:+.4f}")
    else:
        train(args)


if __name__ == "__main__":
    main()
