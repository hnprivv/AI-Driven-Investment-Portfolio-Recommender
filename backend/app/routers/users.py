from typing import List

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import get_current_username, verify_password
from app.clustering import predict_user_cluster
from app.db import delete_user, get_user_by_name, update_user
from app.portfolio import parse_holdings_input

router = APIRouter()


def _serialise(user: dict) -> dict:
    """Strip internal/sensitive fields and make everything JSON-safe."""
    out = {k: v for k, v in user.items() if k not in ("_id", "password")}
    for k, v in out.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


@router.get("/me")
def get_profile(username: str = Depends(get_current_username)):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialise(user)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.put("/me/password")
def change_password(
    body: ChangePasswordRequest, username: str = Depends(get_current_username)
):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt()).decode()
    if not update_user(username, {"password": new_hash}):
        raise HTTPException(status_code=500, detail="Could not update password")
    return {"ok": True}


class ProfileUpdateRequest(BaseModel):
    age: int = Field(ge=18, le=100)
    income_range: str
    investment_horizon: str
    experience: str
    goals: str
    preferences: List[str] = []
    risk_tolerance: int = Field(ge=1, le=10)


@router.put("/me/profile")
def update_profile(body: ProfileUpdateRequest, username: str = Depends(get_current_username)):
    cluster = predict_user_cluster(
        age=body.age,
        income_range=body.income_range,
        risk_tolerance=body.risk_tolerance,
        horizon=body.investment_horizon,
        experience=body.experience,
    )
    updates = {
        "age": body.age,
        "income_range": body.income_range,
        "investment_horizon": body.investment_horizon,
        "experience": body.experience,
        "goals": body.goals,
        "preferences": body.preferences,
        "risk_tolerance": body.risk_tolerance,
        "cluster": cluster,
    }
    if not update_user(username, updates):
        raise HTTPException(status_code=500, detail="Could not update profile")

    user = get_user_by_name(username)
    return _serialise(user)


class HoldingsRequest(BaseModel):
    holdings_text: str


@router.put("/me/holdings")
def save_holdings(body: HoldingsRequest, username: str = Depends(get_current_username)):
    if not body.holdings_text.strip():
        raise HTTPException(status_code=400, detail="Please enter at least one ticker.")

    parsed, err = parse_holdings_input(body.holdings_text)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if not update_user(username, {"holdings": parsed}):
        raise HTTPException(status_code=500, detail="Could not save holdings")
    return {"holdings": parsed}


@router.delete("/me/holdings")
def clear_holdings(username: str = Depends(get_current_username)):
    if not update_user(username, {"holdings": []}):
        raise HTTPException(status_code=500, detail="Could not clear holdings")
    return {"holdings": []}


class DeleteAccountRequest(BaseModel):
    password: str


@router.delete("/me")
def delete_account(
    body: DeleteAccountRequest,
    response: Response,
    username: str = Depends(get_current_username),
):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Incorrect password")

    if not delete_user(username):
        raise HTTPException(status_code=500, detail="Could not delete account")

    response.delete_cookie("aiprs_session")
    return {"ok": True}
