"""AIPRS API — FastAPI backend.

Skeleton for the React migration: currently exposes just the auth flow
(login/me/logout) so the new frontend can be proven end-to-end before the
rest of the pages are ported over. The existing Streamlit app keeps running
unchanged during the migration.
"""
import os

from dotenv import load_dotenv

# Must run before any other `app.*` import — several modules (app.auth in
# particular) read os.getenv(...) at module-import time, so .env has to be
# loaded before those imports happen, not just before they're first called.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, feedback, market, news, portfolio, recommendations, users

app = FastAPI(title="AIPRS API")

# Vite dev server + preview build are always allowed; the deployed frontend
# origin(s) (e.g. https://your-app.vercel.app) come from CORS_ORIGINS, a
# comma-separated env var set on the hosting platform — never hardcoded here.
_default_origins = ["http://localhost:5173", "http://localhost:4173"]
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# allow_credentials is deliberately False: session auth is a bearer token
# (see app/auth.py), not a cookie, because Hugging Face Spaces' edge proxy
# answers CORS preflight (OPTIONS) requests itself and never forwards them
# to this app — it can't be made to echo Access-Control-Allow-Credentials,
# which browsers require for cookie-based (credentials: "include") requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition carries the PDF report's server-chosen filename —
    # browsers hide response headers from JS by default unless explicitly
    # exposed, even same-origin-looking ones on a cross-site fetch.
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(news.router, prefix="/news", tags=["news"])
app.include_router(feedback.router, prefix="", tags=["feedback"])


@app.get("/health")
def health():
    return {"status": "ok"}
