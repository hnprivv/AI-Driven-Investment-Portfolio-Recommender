import datetime
import os

import bcrypt
import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


def create_session_token(email: str) -> str:
    """The session's subject is the user's email — the only field actually
    guaranteed unique (enforced both at signup and by a DB unique index).
    Display names are NOT unique and must never be used as an identity key."""
    payload = {
        "sub": email,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_session_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def _extract_token(authorization: str | None) -> str | None:
    """Session tokens are sent as `Authorization: Bearer <token>` rather than
    a cookie — Hugging Face Spaces' edge proxy answers CORS preflight
    (OPTIONS) requests itself and never forwards them to the app, so it
    can't be made to echo Access-Control-Allow-Credentials. That breaks
    cookies (which require the browser to see that header) but has no
    effect on a bearer token, since it isn't sent in credentialed mode."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def get_current_email(authorization: str | None = Header(default=None)) -> str:
    token = _extract_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_session_token(token)


def get_current_email_optional(authorization: str | None = Header(default=None)) -> str | None:
    """Like get_current_email, but returns None instead of raising when
    there's no session — for pages that work for logged-out visitors too."""
    token = _extract_token(authorization)
    if token is None:
        return None
    try:
        return decode_session_token(token)
    except HTTPException:
        return None
