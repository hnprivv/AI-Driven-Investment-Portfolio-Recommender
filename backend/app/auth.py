import datetime
import os

import bcrypt
import jwt
from fastapi import Cookie, HTTPException, Response

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24
SESSION_COOKIE_NAME = "aiprs_session"

# In production the frontend (Vercel) and backend (Hugging Face Spaces) live
# on different domains, so the session cookie is cross-site — browsers only
# send it on cross-site fetch/XHR requests when it's SameSite=None + Secure.
# Locally both run on http://localhost on different ports, which browsers
# treat as same-site, so Lax (and no Secure, since there's no HTTPS) works.
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "samesite": "none" if IS_PRODUCTION else "lax",
        "secure": IS_PRODUCTION,
    }


def set_session_cookie(response: Response, email: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(email),
        max_age=24 * 3600,
        **_cookie_kwargs(),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, **_cookie_kwargs())


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


def get_current_email(aiprs_session: str | None = Cookie(default=None)) -> str:
    if aiprs_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_session_token(aiprs_session)


def get_current_email_optional(aiprs_session: str | None = Cookie(default=None)) -> str | None:
    """Like get_current_email, but returns None instead of raising when
    there's no session — for pages that work for logged-out visitors too."""
    if aiprs_session is None:
        return None
    try:
        return decode_session_token(aiprs_session)
    except HTTPException:
        return None
