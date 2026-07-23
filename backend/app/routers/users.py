from typing import List

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import create_session_token, get_current_username, verify_password
from app.clustering import predict_user_cluster
from app.db import delete_user, get_user_by_email, get_user_by_name, update_user
from app.email_service import (
    send_account_deleted_email,
    send_credentials_updated_email,
    send_holdings_updated_email,
)
from app.portfolio import parse_holdings_input
from app.validation import EMAIL_RE

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

    if user.get("email_opt_in") and user.get("email"):
        send_credentials_updated_email(username, user["email"], "password")

    return {"ok": True}


class AccountUpdateRequest(BaseModel):
    name: str
    email: str
    password: str = ""


@router.put("/me/account")
def update_account(
    body: AccountUpdateRequest,
    response: Response,
    username: str = Depends(get_current_username),
):
    user = get_user_by_name(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_name = body.name.strip()
    new_email = body.email.strip().lower()
    if not new_name or not new_email:
        raise HTTPException(status_code=400, detail="Name and email cannot be empty.")
    if not EMAIL_RE.match(new_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    email_changed = new_email != user.get("email", "")
    if email_changed:
        if not body.password:
            raise HTTPException(status_code=400, detail="Please enter your password to change your email.")
        if not verify_password(body.password, user.get("password", "")):
            raise HTTPException(status_code=401, detail="Incorrect password.")
        existing = get_user_by_email(new_email)
        if existing is not None and existing.get("name") != username:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

    if not update_user(username, {"name": new_name, "email": new_email}):
        raise HTTPException(status_code=500, detail="Could not update account")

    if email_changed and user.get("email_opt_in") and user.get("email"):
        send_credentials_updated_email(
            username, user["email"], "email",
            extra=f"It was changed to {new_email}.",
        )

    # "name" doubles as the session identity, so a rename invalidates the
    # current cookie's subject — reissue it against the new name.
    if new_name != username:
        token = create_session_token(new_name)
        response.set_cookie(
            key="aiprs_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=24 * 3600,
        )

    updated = get_user_by_name(new_name)
    return _serialise(updated)


class EmailPreferenceRequest(BaseModel):
    email_opt_in: bool


@router.put("/me/email-preference")
def update_email_preference(
    body: EmailPreferenceRequest, username: str = Depends(get_current_username)
):
    if not update_user(username, {"email_opt_in": body.email_opt_in}):
        raise HTTPException(status_code=500, detail="Could not update email preference")
    return {"email_opt_in": body.email_opt_in}


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

    user = get_user_by_name(username)
    if user and user.get("email_opt_in") and user.get("email"):
        send_holdings_updated_email(username, user["email"], parsed)

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

    if user.get("email"):
        send_account_deleted_email(username, user["email"])

    response.delete_cookie("aiprs_session")
    return {"ok": True}
