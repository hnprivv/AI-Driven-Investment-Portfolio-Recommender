"""PPO Advisor data layer — loads the trained PPO agents (modules/ai) and
turns live market data + a user's risk profile into BUY/HOLD/SELL advisory
recommendations. Mirrors pages/6_US_PPO_Advisor.py / 7_PSX_PPO_Advisor.py
function-for-function so the numbers match the legacy Streamlit app.
"""
import os
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.ai.feature_eng import (  # noqa: E402
    FeatureNormalizer,
    compute_features,
    compute_raw_log_returns,
    encode_user_profile,
)
from modules.ai.ppo_agent import PPOAgent  # noqa: E402

from app import market_overview as mo  # noqa: E402

US_MODEL_DIR = os.path.join(ROOT, "modules", "model", "ppo")
PSX_MODEL_DIR = os.path.join(ROOT, "modules", "model", "ppo_psx")

US_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "SPY", "QQQ", "GLD"]
PSX_TICKERS = list(mo.PSX_STOCKS.keys())

HISTORY_WINDOW = 60


class ModelNotReady(Exception):
    pass


@lru_cache(maxsize=1)
def _load_us():
    try:
        agent = PPOAgent.load(US_MODEL_DIR)
        normalizer = FeatureNormalizer.load(os.path.join(US_MODEL_DIR, "normalizer.pkl"))
        return agent, normalizer
    except FileNotFoundError:
        return None, None


@lru_cache(maxsize=1)
def _load_psx():
    try:
        agent = PPOAgent.load(PSX_MODEL_DIR)
        normalizer = FeatureNormalizer.load(os.path.join(PSX_MODEL_DIR, "normalizer.pkl"))
        return agent, normalizer
    except FileNotFoundError:
        return None, None


def get_user_vec(user: dict) -> np.ndarray:
    return encode_user_profile(user)


def _risk_note(risk_scaled: float) -> str:
    if risk_scaled < 0.4:
        return "Your conservative risk profile raises the confidence bar for directional actions."
    if risk_scaled > 0.7:
        return "Your aggressive risk profile allows lower-confidence directional calls."
    return ""


def _row(name: str, value: str, signal: str, tone: str) -> dict:
    return {"name": name, "value": value, "signal": signal, "tone": tone}


def _indicators(latest: pd.Series) -> list[dict]:
    """Mirrors the 'Key Market Signals' table from the legacy PPO pages."""
    rsi = float(latest["rsi_14"]) * 100
    bb = float(latest["bb_pos"])
    stoch = float(latest["stoch_k"]) * 100
    ema_s = float(latest["ema_ratio_short"]) * 100
    ema_l = float(latest["ema_ratio_long"]) * 100
    vol20 = float(latest["vol_20"])
    volr = float(latest["volume_ratio"])

    return [
        _row("RSI (14)", f"{rsi:.1f}",
             "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral",
             "buy" if rsi < 30 else "sell" if rsi > 70 else "neutral"),
        _row("Bollinger Position", f"{bb:.2f}",
             "Near Lower Band" if bb < 0.3 else "Near Upper Band" if bb > 0.7 else "Mid-Range",
             "buy" if bb < 0.3 else "sell" if bb > 0.7 else "neutral"),
        _row("Stochastic %K", f"{stoch:.1f}",
             "Oversold" if stoch < 20 else "Overbought" if stoch > 80 else "Neutral",
             "buy" if stoch < 20 else "sell" if stoch > 80 else "neutral"),
        _row("EMA Trend (9/21)", f"{ema_s:+.2f}%",
             "Bullish" if ema_s > 0 else "Bearish",
             "buy" if ema_s > 0 else "sell"),
        _row("EMA Trend (21/50)", f"{ema_l:+.2f}%",
             "Bullish" if ema_l > 0 else "Bearish",
             "buy" if ema_l > 0 else "sell"),
        _row("Volatility (20d)", f"{vol20 * 100:.2f}%",
             "High" if vol20 > 0.02 else "Low",
             "sell" if vol20 > 0.02 else "buy"),
        _row("Volume Ratio", f"{volr + 1:.2f}x",
             "Unusual" if abs(volr) > 1.5 else "Normal",
             "sell" if abs(volr) > 1.5 else "neutral"),
    ]


def _run_history(agent: PPOAgent, feat_norm: np.ndarray, user_vec: np.ndarray,
                  raw_rets: np.ndarray, window: int = HISTORY_WINDOW) -> list[dict]:
    risk_scaled = float(user_vec[0])
    start = max(0, len(feat_norm) - window)
    out = []
    for i in range(start, len(feat_norm)):
        obs = np.concatenate([feat_norm[i], user_vec]).astype(np.float32)
        rec = agent.ac.recommend(obs, risk_scaled)
        rec["actual_ret"] = float(raw_rets[i]) if i < len(raw_rets) else 0.0
        out.append(rec)
    return out


def _hit_rate(history: list[dict]) -> dict:
    directional = [h for h in history if h["action"] != "HOLD"]
    correct = sum(
        1 for h in directional
        if (h["action"] == "BUY" and h["actual_ret"] > 0)
        or (h["action"] == "SELL" and h["actual_ret"] < 0)
    )
    return {
        "directional_signals": len(directional),
        "correct": correct,
        "hit_rate_pct": (correct / len(directional) * 100) if directional else None,
        "buy_count": sum(1 for h in history if h["action"] == "BUY"),
        "sell_count": sum(1 for h in history if h["action"] == "SELL"),
        "hold_count": sum(1 for h in history if h["action"] == "HOLD"),
    }


def _advise_detail(agent: PPOAgent, normalizer: FeatureNormalizer, df: pd.DataFrame,
                    user_vec: np.ndarray, symbol: str, price: float, chg_pct: float,
                    is_live: bool, currency: str) -> dict | None:
    feat_df = compute_features(df)
    if len(feat_df) < 30:
        return None

    raw_rets = compute_raw_log_returns(df).reindex(feat_df.index).fillna(0.0).values
    feat_norm = normalizer.transform(feat_df)

    rec = agent.advise(feat_norm[-1], user_vec)
    history = _run_history(agent, feat_norm, user_vec, raw_rets)

    hist_len = len(history)
    price_tail = df.tail(hist_len).reset_index(drop=True)
    chart = []
    if len(price_tail) == hist_len:
        for i, h in enumerate(history):
            ts = price_tail["timestamp"].iloc[i]
            chart.append({
                "date": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "close": float(price_tail["close"].iloc[i]),
                "action": h["action"],
                "confidence": h["confidence"],
            })

    return {
        "symbol": symbol,
        "currency": currency,
        "price": price,
        "chg_pct": chg_pct,
        "is_live": is_live,
        "action": rec["action"],
        "confidence": rec["confidence"],
        "threshold": rec["threshold"],
        "probabilities": rec["probabilities"],
        "risk_note": _risk_note(float(user_vec[0])),
        "indicators": _indicators(feat_df.iloc[-1]),
        "chart": chart,
        "hit_rate": _hit_rate(history),
    }


def us_batch(user_vec: np.ndarray) -> list[dict]:
    agent, normalizer = _load_us()
    if agent is None:
        raise ModelNotReady("US PPO model not trained")

    results = []
    for symbol in US_TICKERS:
        df, is_live = mo.get_daily_bars(symbol, 400)
        if df is None or len(df) < 60:
            continue
        try:
            feat_df = compute_features(df)
            if feat_df.empty:
                continue
            feat_norm = normalizer.transform(feat_df)
            rec = agent.advise(feat_norm[-1], user_vec)
        except Exception:
            continue
        last_close = float(df["close"].iloc[-1])
        ret_1d = float((df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100) if len(df) >= 2 else 0.0
        results.append({
            "symbol": symbol, "action": rec["action"], "confidence": rec["confidence"],
            "probabilities": rec["probabilities"], "price": last_close, "chg_pct": ret_1d,
            "is_live": is_live,
        })
    return results


def us_detail(user_vec: np.ndarray, symbol: str) -> dict | None:
    agent, normalizer = _load_us()
    if agent is None:
        raise ModelNotReady("US PPO model not trained")
    df, is_live = mo.get_daily_bars(symbol, 400)
    if df is None or len(df) < 60:
        return None
    quote = mo.get_quote(symbol)
    return _advise_detail(agent, normalizer, df, user_vec, symbol, quote["price"], quote["chg_pct"], is_live, "$")


def psx_batch(user_vec: np.ndarray) -> list[dict]:
    agent, normalizer = _load_psx()
    if agent is None:
        raise ModelNotReady("PSX PPO model not trained")

    snapshot = mo.fetch_psx_snapshot()
    results = []
    for symbol in PSX_TICKERS:
        df = mo.fetch_psx_ohlcv(symbol)
        if df is None or len(df) < 60:
            continue
        try:
            feat_df = compute_features(df)
            if feat_df.empty:
                continue
            feat_norm = normalizer.transform(feat_df)
            rec = agent.advise(feat_norm[-1], user_vec)
        except Exception:
            continue
        quote = mo.get_psx_quote(symbol, snapshot)
        results.append({
            "symbol": symbol, "action": rec["action"], "confidence": rec["confidence"],
            "probabilities": rec["probabilities"], "price": quote["price"], "chg_pct": quote["chg_pct"],
            "is_live": bool(snapshot.get(symbol)),
        })
    return results


def psx_detail(user_vec: np.ndarray, symbol: str) -> dict | None:
    agent, normalizer = _load_psx()
    if agent is None:
        raise ModelNotReady("PSX PPO model not trained")
    df = mo.fetch_psx_ohlcv(symbol)
    if df is None or len(df) < 60:
        return None
    snapshot = mo.fetch_psx_snapshot()
    quote = mo.get_psx_quote(symbol, snapshot)
    return _advise_detail(
        agent, normalizer, df, user_vec, symbol, quote["price"], quote["chg_pct"],
        bool(snapshot.get(symbol)), "Rs ",
    )
