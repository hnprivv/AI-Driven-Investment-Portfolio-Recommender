from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.auth import create_session_token, get_current_email, verify_password
from app.clustering import predict_user_cluster
from app.db import get_db, get_user_by_email
from app.email_service import send_welcome_email
from app.portfolio import CLUSTER_LABELS
from app.validation import EMAIL_RE, validate_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    age: int = Field(ge=18, le=100)
    income_range: str
    investment_horizon: str
    experience: str
    goals: str
    preferences: list[str] = []
    risk_tolerance: int = Field(ge=1, le=10)


class UserOut(BaseModel):
    name: str
    email: str
    cluster: int | None = None
    risk_tolerance: int | None = None


def _get_user_by_email(email: str) -> dict | None:
    return get_db()["users"].find_one({"email": email.strip().lower()})


@router.post("/login")
def login(body: LoginRequest):
    user = _get_user_by_email(body.email)
    if user is None or not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"name": user["name"], "token": create_session_token(user["email"])}


@router.post("/signup")
def signup(body: SignupRequest):
    name = body.name.strip()
    email = body.email.strip().lower()

    if not name or not email or not body.password:
        raise HTTPException(status_code=400, detail="Please fill out all required fields.")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if _get_user_by_email(email) is not None:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        )

    pw_error = validate_password(body.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    cluster = predict_user_cluster(
        age=body.age,
        income_range=body.income_range,
        risk_tolerance=body.risk_tolerance,
        horizon=body.investment_horizon,
        experience=body.experience,
    )

    user_doc = {
        "name": name,
        "email": email,
        "age": body.age,
        "income_range": body.income_range,
        "risk_tolerance": body.risk_tolerance,
        "investment_horizon": body.investment_horizon,
        "experience": body.experience,
        "goals": body.goals,
        "preferences": body.preferences,
        "cluster": cluster,
        "created_at": datetime.now(timezone.utc),
        "password": bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode(),
    }

    try:
        get_db()["users"].insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        )

    send_welcome_email(name, email, CLUSTER_LABELS.get(cluster, "Moderate"))

    return {"name": name, "cluster": cluster, "token": create_session_token(email)}


@router.post("/logout")
def logout():
    # Nothing to do server-side — the frontend just discards its stored
    # token. Kept as a route so the frontend's logout() call has something
    # to hit without a client-side special case.
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(email: str = Depends(get_current_email)):
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(
        name=user["name"],
        email=user.get("email", ""),
        cluster=user.get("cluster"),
        risk_tolerance=user.get("risk_tolerance"),
    )
