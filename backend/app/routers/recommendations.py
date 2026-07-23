from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_email
from app.db import get_user_by_email
from app.portfolio import CLUSTER_ALLOCATIONS, CLUSTER_LABELS
from app.recommendations import STRATEGY_INFO, compute_mpt_allocation, get_collaborative_recs

router = APIRouter()


@router.get("")
def get_recommendations(email: str = Depends(get_current_email)):
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_cluster = int(user.get("cluster", 1))
    risk_tolerance = int(user.get("risk_tolerance", 5))
    risk_profile = CLUSTER_LABELS.get(user_cluster, "Moderate")

    mpt_result = compute_mpt_allocation(risk_tolerance)

    if mpt_result:
        weights_map = mpt_result["weights"]
        exp_return = mpt_result["exp_return"]
        exp_vol = mpt_result["exp_vol"]
        mpt_available = True
    else:
        fallback = CLUSTER_ALLOCATIONS.get(user_cluster, CLUSTER_ALLOCATIONS[1])
        weights_map = {k: v / 100 for k, v in fallback.items()}
        exp_return = None
        exp_vol = None
        mpt_available = False

    if exp_vol is not None:
        vol_label = "Low" if exp_vol < 0.08 else "Medium" if exp_vol < 0.15 else "High"
    else:
        vol_label = {
            "Conservative": "Low", "Moderate": "Medium",
            "Aggressive": "High", "Very Aggressive": "High",
        }.get(risk_profile, "Medium")

    strategy_title, strategy_desc = STRATEGY_INFO.get(risk_profile, STRATEGY_INFO["Moderate"])

    recs, status_or_cluster = get_collaborative_recs(email)
    peer_recs = []
    peer_status = "ok"
    if recs:
        max_count = max(count for _, count in recs)
        peer_recs = [
            {"asset": asset, "count": count, "pct": int((count / max_count) * 100) if max_count > 0 else 0}
            for asset, count in recs[:3]
        ]
    elif recs == []:
        peer_status = "all_invested"
    else:
        peer_status = "unavailable"

    return {
        "risk_profile": risk_profile,
        "strategy_title": strategy_title,
        "strategy_desc": strategy_desc,
        "allocation": {k: round(v * 100, 1) for k, v in weights_map.items()},
        "exp_return": exp_return,
        "exp_vol": exp_vol,
        "vol_label": vol_label,
        "mpt_available": mpt_available,
        "peer_recs": peer_recs,
        "peer_status": peer_status,
        "peer_status_message": status_or_cluster if peer_status == "unavailable" else None,
    }
