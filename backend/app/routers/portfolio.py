from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_username
from app.clustering import EXPERIENCE_MAP, get_cluster_background
from app.db import get_user_by_name
from app.market_data import fetch_bars, fetch_ticker
from app.pdf_report import generate_pdf_report
from app.portfolio import (
    ASSET_TICKERS,
    BADGE_COLORS,
    CLUSTER_ALLOCATIONS,
    CLUSTER_LABELS,
    classify_ticker,
    compute_portfolio_metrics,
)

router = APIRouter()

# Static fallback used only if live price data can't be fetched at all.
_FALLBACK = {"return": 0.128, "vol": 0.082, "sharpe": 1.42}


def _compute_overview_data(user: dict) -> dict:
    """Shared by both /overview (JSON) and /report.pdf so the two never drift apart."""
    user_cluster = int(user.get("cluster", 1))
    risk_profile = CLUSTER_LABELS.get(user_cluster, "Moderate")
    allocation = CLUSTER_ALLOCATIONS.get(user_cluster, CLUSTER_ALLOCATIONS[1])
    badge_color = BADGE_COLORS.get(risk_profile, "#F59E0B")
    saved_holdings = user.get("holdings", [])

    # ---- Benchmark (cluster ETF blend) ----
    benchmark_series = {}
    for asset, ticker in ASSET_TICKERS.items():
        df = fetch_bars(ticker)
        if df is not None and len(df) > 20:
            benchmark_series[asset] = df.set_index("date")["close"]

    bm_return = bm_vol = bm_sharpe = None
    bm_curve = None
    if benchmark_series:
        assets_ordered = [a for a in ASSET_TICKERS if a in benchmark_series]
        bm_price_map = {ASSET_TICKERS[a]: benchmark_series[a] for a in assets_ordered}
        bm_weights_map = {ASSET_TICKERS[a]: allocation[a] for a in assets_ordered}
        bm_return, bm_vol, bm_sharpe, bm_curve = compute_portfolio_metrics(bm_price_map, bm_weights_map)

    if bm_return is None:
        bm_return, bm_vol, bm_sharpe = _FALLBACK["return"], _FALLBACK["vol"], _FALLBACK["sharpe"]

    # ---- User holdings (if any) ----
    user_metrics_available = False
    user_return = user_vol = user_sharpe = None
    user_curve = None
    failed_holdings = []

    if saved_holdings:
        price_series = {}
        weights_map = {h["ticker"]: h["weight"] for h in saved_holdings}
        for h in saved_holdings:
            df = fetch_ticker(h["ticker"], h.get("market", "US"))
            if df is not None and len(df) > 20:
                price_series[h["ticker"]] = df.set_index("date")["close"]
            else:
                failed_holdings.append(h["ticker"])

        if price_series:
            user_return, user_vol, user_sharpe, user_curve = compute_portfolio_metrics(
                price_series, weights_map
            )
            user_metrics_available = user_return is not None

    active_curve = user_curve if user_metrics_available else bm_curve
    metrics_source = "your holdings" if user_metrics_available else "cluster benchmark"
    display_return = user_return if user_metrics_available else bm_return
    display_vol = user_vol if user_metrics_available else bm_vol
    display_sharpe = user_sharpe if user_metrics_available else bm_sharpe

    curve_points = []
    if active_curve is not None:
        curve_points = [
            {"date": str(d), "value": float(v)} for d, v in active_curve.items()
        ]

    # ---- Holdings broken down by asset class (real breakdown, no price data needed) ----
    holdings_by_category = None
    if saved_holdings:
        holdings_by_category = {}
        for h in saved_holdings:
            cat = classify_ticker(h["ticker"])
            holdings_by_category[cat] = holdings_by_category.get(cat, 0) + h["weight"]

    return {
        "profile": {
            "name": user.get("name"),
            "age": user.get("age"),
            "income_range": user.get("income_range"),
            "risk_tolerance": user.get("risk_tolerance"),
            "investment_horizon": user.get("investment_horizon"),
            "experience": user.get("experience"),
            "goals": user.get("goals"),
            "preferences": user.get("preferences", []),
        },
        "cluster": user_cluster,
        "risk_profile": risk_profile,
        "badge_color": badge_color,
        "metrics_source": metrics_source,
        "metrics_available": user_metrics_available,
        "total_return": display_return,
        "ann_vol": display_vol,
        "sharpe": display_sharpe,
        "curve": curve_points,
        "holdings": saved_holdings,
        "holdings_by_category": holdings_by_category,
        "failed_holdings": failed_holdings,
    }


@router.get("/overview")
def get_overview(username: str = Depends(get_current_username)):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _compute_overview_data(user)


@router.get("/report.pdf")
def get_report_pdf(username: str = Depends(get_current_username)):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    overview = _compute_overview_data(user)
    pdf_bytes = generate_pdf_report(username=username, user=user, overview=overview)

    filename = f"aiprs_report_{username.lower().replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cluster-placement")
def get_cluster_placement(username: str = Depends(get_current_username)):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    background = get_cluster_background()
    if background is None:
        raise HTTPException(status_code=404, detail="Pre-trained AI models not found.")

    return {
        "background": background,
        "user_point": {
            "age": user.get("age", 30),
            "risk_score": user.get("risk_tolerance", 5),
            "exp_score": EXPERIENCE_MAP.get(user.get("experience", "Beginner"), 1),
        },
    }
