from fastapi import APIRouter, Depends, HTTPException, Query

from app import ppo_service
from app.auth import get_current_email
from app.db import get_user_by_email

router = APIRouter()


def _require_user(email: str) -> dict:
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/us/batch")
def get_us_batch(email: str = Depends(get_current_email)):
    user = _require_user(email)
    try:
        return ppo_service.us_batch(ppo_service.get_user_vec(user))
    except ppo_service.ModelNotReady:
        raise HTTPException(status_code=503, detail="US PPO model is not available yet.")


@router.get("/us/detail")
def get_us_detail(symbol: str = Query(...), email: str = Depends(get_current_email)):
    user = _require_user(email)
    try:
        result = ppo_service.us_detail(ppo_service.get_user_vec(user), symbol.strip().upper())
    except ppo_service.ModelNotReady:
        raise HTTPException(status_code=503, detail="US PPO model is not available yet.")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch sufficient data for {symbol.strip().upper()}.")
    return result


@router.get("/psx/batch")
def get_psx_batch(email: str = Depends(get_current_email)):
    user = _require_user(email)
    try:
        return ppo_service.psx_batch(ppo_service.get_user_vec(user))
    except ppo_service.ModelNotReady:
        raise HTTPException(status_code=503, detail="PSX PPO model is not available yet.")


@router.get("/psx/detail")
def get_psx_detail(symbol: str = Query(...), email: str = Depends(get_current_email)):
    user = _require_user(email)
    try:
        result = ppo_service.psx_detail(ppo_service.get_user_vec(user), symbol.strip().upper())
    except ppo_service.ModelNotReady:
        raise HTTPException(status_code=503, detail="PSX PPO model is not available yet.")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch sufficient data for {symbol.strip().upper()}.")
    return result
