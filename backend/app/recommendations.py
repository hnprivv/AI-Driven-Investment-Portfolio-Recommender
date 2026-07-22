from collections import Counter

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.db import get_all_users
from app.market_data import fetch_bars
from app.portfolio import ASSET_TICKERS, CLUSTER_ALLOCATIONS

STRATEGY_INFO = {
    "Conservative": (
        "Capital Preservation",
        "This portfolio prioritises stability, weighting toward Fixed Income and Cash to minimise volatility.",
    ),
    "Moderate": (
        "Balanced Growth",
        "This portfolio balances growth and stability across Equities, Fixed Income, and Commodities.",
    ),
    "Aggressive": (
        "Growth-Focused",
        "This portfolio prioritises growth, weighting toward Equities and Commodities to maximise expected return.",
    ),
    "Very Aggressive": (
        "Maximum Growth",
        "This portfolio is heavily weighted toward Equities and Commodities for maximum expected return, accepting higher volatility.",
    ),
}


def compute_mpt_allocation(risk_tolerance: int) -> dict | None:
    """Mean-variance (Markowitz) optimisation over the same 4-asset universe
    used on the Overview page: maximise expected return subject to a
    volatility ceiling, long-only, weights summing to 1. Mirrors
    pages/2_AI_Recommendations.py's compute_mpt_allocation exactly.
    Not cached here since fetch_bars() already has its own 900s TTL cache
    for the underlying price data — this keeps the optimization result
    fresh whenever prices refresh, instead of pinning it for the process
    lifetime.
    """
    price_series = {}
    for label, ticker in ASSET_TICKERS.items():
        df = fetch_bars(ticker)
        if df is not None and len(df) >= 30:
            price_series[label] = df.set_index("date")["close"]

    if len(price_series) < len(ASSET_TICKERS):
        return None

    prices_df = pd.DataFrame(price_series).dropna()
    if len(prices_df) < 30:
        return None

    returns = prices_df.pct_change().dropna()
    ann_returns = returns.mean().values * 252
    ann_cov = returns.cov().values * 252

    n = len(ASSET_TICKERS)
    risk_free = 0.045
    target_vol = float(np.interp(risk_tolerance, [1, 10], [0.06, 0.22]))

    bounds = [(0, 1)] * n
    sum_to_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    w0 = np.array([1 / n] * n)

    def port_vol_fn(w):
        return float(np.sqrt(w @ ann_cov @ w))

    min_var_result = minimize(
        lambda w: w @ ann_cov @ w, w0, method="SLSQP",
        bounds=bounds, constraints=[sum_to_one],
    )
    min_var_weights = min_var_result.x if min_var_result.success else w0
    min_achievable_vol = port_vol_fn(min_var_weights)

    effective_target = max(target_vol, min_achievable_vol)

    constraints = [
        sum_to_one,
        {"type": "ineq", "fun": lambda w: effective_target - port_vol_fn(w)},
    ]
    result = minimize(
        lambda w: -(w @ ann_returns), w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
    )
    weights = result.x if result.success else min_var_weights
    weights = np.clip(weights, 0, None)
    weights = weights / weights.sum()

    port_return = float(weights @ ann_returns)
    port_vol = float(np.sqrt(weights @ ann_cov @ weights))
    sharpe = (port_return - risk_free) / port_vol if port_vol > 0 else 0.0

    return {
        "weights": dict(zip(ASSET_TICKERS.keys(), weights.tolist())),
        "exp_return": port_return,
        "exp_vol": port_vol,
        "sharpe": sharpe,
    }


def get_collaborative_recs(current_user_name: str):
    """Finds assets preferred by other users in the same cluster.
    Returns (recommendations list, cluster id) or (None, error message).
    """
    all_users = get_all_users()
    if not all_users:
        return None, "No user data available."

    current_user = next((u for u in all_users if u.get("name") == current_user_name), None)
    if current_user is None:
        return None, "User profile not found."

    user_cluster = current_user.get("cluster")
    current_prefs = current_user.get("preferences", [])
    if isinstance(current_prefs, str):
        current_prefs = [p.strip() for p in current_prefs.split(",")]

    neighbors = [
        u for u in all_users
        if u.get("cluster") == user_cluster and u.get("name") != current_user_name
    ]

    if not neighbors:
        return None, "No data available for peer comparison yet."

    all_neighbor_prefs = []
    for u in neighbors:
        prefs = u.get("preferences", [])
        if isinstance(prefs, str):
            prefs = [p.strip() for p in prefs.split(",")]
        all_neighbor_prefs.extend(prefs)

    pref_counts = Counter(all_neighbor_prefs)
    recommendations = [
        (asset, count)
        for asset, count in pref_counts.most_common(5)
        if asset not in current_prefs
    ]

    return recommendations, user_cluster
