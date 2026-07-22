import numpy as np
import pandas as pd

CLUSTER_LABELS = {0: "Conservative", 1: "Moderate", 2: "Aggressive", 3: "Very Aggressive"}
BADGE_COLORS = {
    "Conservative": "#16a34a", "Moderate": "#FFE600",
    "Aggressive": "#ff8400", "Very Aggressive": "#b71212",
}

CLUSTER_ALLOCATIONS = {
    0: {"Equities": 30, "Fixed Income": 50, "Commodities": 10, "Cash": 10},
    1: {"Equities": 60, "Fixed Income": 25, "Commodities": 10, "Cash": 5},
    2: {"Equities": 85, "Fixed Income": 5, "Commodities": 8, "Cash": 2},
    3: {"Equities": 90, "Fixed Income": 5, "Commodities": 3, "Cash": 2},
}

ASSET_TICKERS = {"Equities": "SPY", "Fixed Income": "AGG", "Commodities": "GLD", "Cash": "BIL"}

# Same heuristic classifier as pages/1_Overview.py — anything not in this
# lookup (individual stocks, index ETFs, PSX tickers) defaults to Equities.
TICKER_CATEGORY_MAP = {
    "AGG": "Fixed Income", "BND": "Fixed Income", "TLT": "Fixed Income",
    "IEF": "Fixed Income", "SHY": "Fixed Income", "LQD": "Fixed Income",
    "HYG": "Fixed Income", "MUB": "Fixed Income", "TIP": "Fixed Income",
    "GLD": "Commodities", "SLV": "Commodities", "DBC": "Commodities",
    "USO": "Commodities", "IAU": "Commodities", "PPLT": "Commodities",
    "BIL": "Cash", "SHV": "Cash", "SGOV": "Cash", "ICSH": "Cash",
}


def classify_ticker(ticker: str) -> str:
    return TICKER_CATEGORY_MAP.get(ticker.upper(), "Equities")


def parse_holdings_input(text: str) -> tuple[list[dict], str | None]:
    """Parses 'AAPL:40, MSFT:30, OGDC.KA:30' or 'AAPL, MSFT' (equal weight).
    Mirrors pages/1_Overview.py's parse_holdings_input exactly.
    Returns (holdings_list, error_msg)."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return [], "Please enter at least one ticker."

    holdings = []
    has_any_colon = any(":" in p for p in parts)

    for part in parts:
        if ":" in part:
            bits = part.split(":", 1)
            ticker = bits[0].strip().upper()
            if not ticker:
                return [], "Ticker cannot be empty."
            try:
                weight = float(bits[1].strip())
            except ValueError:
                return [], f"Invalid weight for '{ticker}' — use a number."
            if weight <= 0:
                return [], f"Weight for '{ticker}' must be greater than 0."
            holdings.append({"ticker": ticker, "weight": weight})
        else:
            ticker = part.strip().upper()
            if not ticker:
                continue
            if has_any_colon:
                return [], "Please specify weights for all tickers or none."
            holdings.append({"ticker": ticker, "weight": None})

    if not holdings:
        return [], "No valid tickers found."

    if any(h["weight"] is None for h in holdings):
        equal_w = round(100 / len(holdings), 4)
        for h in holdings:
            h["weight"] = equal_w

    total = sum(h["weight"] for h in holdings)
    if abs(total - 100) > 2:
        return [], f"Weights sum to {total:.1f}% but must sum to 100%."

    for h in holdings:
        h["weight"] = round(h["weight"] / total * 100, 4)
        h["market"] = "PSX" if h["ticker"].endswith(".KA") else "US"

    return holdings, None


def compute_portfolio_metrics(
    price_series: dict, weights_map: dict
) -> tuple[float | None, float | None, float | None, pd.Series | None]:
    """Mirrors pages/1_Overview.py's compute_portfolio_metrics exactly."""
    tickers = list(price_series.keys())
    prices_df = pd.DataFrame({t: price_series[t] for t in tickers}).dropna()
    if len(prices_df) < 21:
        return None, None, None, None
    weights = np.array([weights_map[t] / 100 for t in tickers])
    daily_returns = prices_df.pct_change().dropna()
    port_daily = daily_returns.values @ weights
    equity_curve = pd.Series((1 + port_daily).cumprod(), index=daily_returns.index)
    total_return = float(equity_curve.iloc[-1] - 1)
    ann_vol = float(np.std(port_daily) * np.sqrt(252))
    ann_return = float((equity_curve.iloc[-1] ** (252 / max(len(port_daily), 1))) - 1)
    sharpe = float((ann_return - 0.045) / ann_vol) if ann_vol > 0 else 0.0
    return total_return, ann_vol, sharpe, equity_curve
