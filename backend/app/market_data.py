import datetime
import os
import time

import pandas as pd
import requests

ALPACA_DATA_URL = "https://data.alpaca.markets/v2"
CACHE_TTL_SECONDS = 900  # matches the Streamlit app's ttl=900

_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    return value


def _cache_set(key: str, value):
    _cache[key] = (time.time(), value)


def _alpaca_headers():
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        return None
    return {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "accept": "application/json",
    }


def fetch_bars(ticker: str, period_days: int = 365) -> pd.DataFrame | None:
    """US equities via Alpaca. Mirrors pages/1_Overview.py's fetch_bars."""
    cache_key = f"alpaca:{ticker}:{period_days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    headers = _alpaca_headers()
    if headers is None:
        return None

    end = datetime.datetime.now(datetime.timezone.utc)
    start = end - datetime.timedelta(days=period_days)
    params = {
        "timeframe": "1Day",
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 10_000,
        "feed": "iex",
        "sort": "desc",
    }
    try:
        resp = requests.get(
            f"{ALPACA_DATA_URL}/stocks/{ticker}/bars",
            headers=headers, params=params, timeout=10,
        )
        resp.raise_for_status()
        bars = resp.json().get("bars", [])
        if not bars:
            return None
        df = pd.DataFrame(bars)
        df.rename(columns={"t": "date", "c": "close"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.iloc[::-1].reset_index(drop=True)
        result = df[["date", "close"]]
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


def fetch_bars_yahoo(ticker: str) -> pd.DataFrame | None:
    """PSX equities (.KA tickers) via yfinance. Mirrors fetch_bars_yahoo."""
    cache_key = f"yahoo:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if df.empty:
            return None
        close = df["Close"] if "Close" in df.columns else df.iloc[:, -1]
        if hasattr(close, "squeeze"):
            close = close.squeeze()
        result = pd.DataFrame({
            "date": pd.to_datetime(close.index).date,
            "close": close.values,
        }).dropna()
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


def fetch_ticker(ticker: str, market: str) -> pd.DataFrame | None:
    if market == "PSX":
        return fetch_bars_yahoo(ticker)
    return fetch_bars(ticker)
