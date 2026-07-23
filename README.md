---
title: AIPRS Backend
emoji: 📈
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
---

<!--
  The block above is Hugging Face Spaces' required config header — it's read
  from README.md at the repo root when this repo is pushed as a Space's git
  remote, and tells HF to build the Dockerfile at the repo root and expose
  port 7860. Harmless to any other viewer (GitHub just renders it as-is).
-->

# AIPRS – AI-Powered Portfolio Recommendation System

![Status](https://img.shields.io/badge/status-in%20progress-yellow)

**AIPRS** is a personal project — an AI-assisted investment research companion. It profiles
investors using machine learning, recommends optimised portfolio allocations, delivers live and
delayed market data across two exchanges, analyses financial news sentiment, and provides
reinforcement-learning-based trading signals.

The project has two apps in this repo:

- **`frontend/` + `backend/`** — the current app: a React (Vite) frontend backed by a FastAPI API.
  This is what's actually deployed and being actively developed.
- **`Home.py` + `pages/`** — the original Streamlit prototype the project was built as before the
  React/FastAPI migration. Kept functional as a reference/fallback; not the primary app anymore.

---

## System Architecture

1. **Frontend** — React 18 + Vite SPA (`frontend/`), deployed to **Vercel**.
2. **Backend** — FastAPI (`backend/`), deployed as a Docker Space on **Hugging Face Spaces**.
   Session auth via an HTTP-only JWT cookie (keyed on email — the only guaranteed-unique field).
3. **ML / AI Layer**
   - **K-Means Clustering** — segments users into four risk profiles: Conservative, Moderate,
     Aggressive, Very Aggressive.
   - **Modern Portfolio Theory** — mean-variance optimisation for the "AI Recommendations" page,
     with a static cluster-allocation fallback when live price data is unavailable.
   - **PPO Reinforcement Learning** — two trained PPO agents produce BUY / HOLD / SELL signals
     with confidence scores: one for US equities, one for Pakistan Stock Exchange (PSX) equities.
     (Currently only available in the legacy Streamlit app — the React port is in progress.)
   - **NLP Sentiment Analysis** — a local FinBERT (ProsusAI) model scores financial news headlines
     as Positive, Neutral, or Negative.
4. **Data Layer**
   - US equity/crypto prices + news: Alpaca Markets API (IEX feed, 15-minute delay).
   - PSX historical prices: Yahoo Finance via `yfinance` (`.KA` suffix tickers).
   - PSX live prices: psxterminal.com (60-second refresh during market hours).
   - PSX news: Google News RSS.
5. **Storage** — MongoDB Atlas. User documents store name, email, bcrypt-hashed password, profile
   answers, cluster assignment, saved holdings, and email preferences.
6. **Transactional email** — Gmail SMTP + Jinja2 HTML templates for welcome, holdings-updated,
   credentials-updated, and account-deletion emails.

---

## Live Deployment

- **Backend** (FastAPI, Docker Space): `https://hnprivv-aiprs.hf.space`
- **Frontend** (Vercel): `https://aiprs.vercel.app`

The backend's `CORS_ORIGINS` env var must include the frontend's deployed URL, and the frontend's
`VITE_API_BASE` (a Vercel build-time env var) must point at the backend URL above — see
[Deployment](#deployment) below.

---

## Prerequisites

- **Backend:** Python 3.11+ (developed on 3.13), a MongoDB Atlas cluster, an Alpaca Markets
  account (paper or live) with API key/secret, a Gmail account with an
  [App Password](https://myaccount.google.com/apppasswords) for SMTP.
- **Frontend:** Node.js 20+.
- **Legacy Streamlit app only:** Python 3.10+ (uses `X | Y` union type hints).

---

## Local Setup — React + FastAPI (current app)

### 1. Clone and configure environment variables

```bash
git clone https://github.com/hnprivv/AIPRS-in-progress-.git
cd AIPRS-in-progress-
```

Create a `.env` file in the project root:

```
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
MONGODB_URI=your_mongodb_atlas_connection_string
JWT_SECRET=a_long_random_string
SMTP_USER=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_char_gmail_app_password
TRANSFORMERS_VERBOSITY=error

# Only needed in production (see Deployment below) — omit locally.
# ENVIRONMENT=production
# CORS_ORIGINS=https://aiprs.vercel.app
```

### 2. Backend

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (docs at `/docs`).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is now at `http://localhost:5173`, talking to the local backend by default
(override with a `frontend/.env` containing `VITE_API_BASE=...` if needed).

---

## Local Setup — Legacy Streamlit App

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

Uses the same root `.env` file as above (also reads `ALPACA_BASE_URL`, optional).

### Training the ML models (first run only)

Pre-trained model files are already included in the repo — retraining is only needed if the
underlying data or architecture changes.

```bash
python train_model.py       # K-Means clustering -> modules/model/{kmeans_model,scaler}.pkl
python train_ppo.py         # US equities PPO agent -> modules/model/ppo/
python train_ppo_psx.py     # PSX equities PPO agent -> modules/model/ppo_psx/
```

---

## Deployment

### Backend → Hugging Face Spaces (Docker SDK)

The root `Dockerfile` builds the FastAPI app in `backend/` (it also copies in `modules/` for the
ML models and `assets/` for the email logo — see the ROOT-relative path logic in
`backend/app/db.py`, `clustering.py`, and `email_service.py`).

1. Create a Space with SDK **Docker**, then add it as a git remote and push:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```
   Binary files (PPO model weights, PNGs) are tracked via **Git LFS** (`.gitattributes` at the
   repo root) — HF's server rejects large binaries pushed as plain git blobs.
2. In the Space's **Settings → Variables and secrets**, add as **secrets**: `MONGODB_URI`,
   `JWT_SECRET`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `SMTP_USER`, `SMTP_PASSWORD`, plus
   `ENVIRONMENT=production` and `CORS_ORIGINS=https://aiprs.vercel.app`.
3. In MongoDB Atlas → Network Access, allow `0.0.0.0/0` (Spaces containers don't have a static IP).
4. The Space rebuilds automatically on push and serves the API on port 7860.

`ENVIRONMENT=production` matters beyond just being a flag: it switches the session cookie from
`SameSite=Lax` (dev, same-origin) to `SameSite=None; Secure` (prod, cross-site — the frontend and
backend are on different domains), which is required for the browser to send the cookie at all on
cross-site API calls.

### Frontend → Vercel

1. Import the repo into Vercel with **Root Directory: `frontend`** (Framework Preset: Vite,
   auto-detected).
2. Add env var `VITE_API_BASE=https://hnprivv-aiprs.hf.space` (or your Space's URL) — apply to
   Production and Preview.
3. Deploy. Once you have the Vercel URL, set it as `CORS_ORIGINS` on the HF Space (step above) and
   the Space will pick it up on its next rebuild.

---

## Project Structure

```
AIPRS_Dashboard/
├── frontend/                    # React (Vite) SPA — the current app's UI
│   ├── src/
│   │   ├── pages/               # Dashboard, Recommendations, Market, News, Feedback, ...
│   │   ├── components/          # Navbar, Footer, CandlestickChart, Select, ...
│   │   └── api.js                # Fetch wrapper, VITE_API_BASE-driven
│   └── package.json
├── backend/                     # FastAPI app — the current app's API
│   ├── app/
│   │   ├── routers/             # auth, users, portfolio, recommendations, market, news, feedback
│   │   ├── email_templates/     # Jinja2 HTML templates for transactional emails
│   │   ├── auth.py              # JWT session cookie logic
│   │   ├── db.py                # MongoDB helpers (unique index on email)
│   │   └── main.py               # App entrypoint, CORS config
│   └── requirements.txt
├── Dockerfile                   # Builds backend/ for the HF Space (Docker SDK)
├── .dockerignore
├── Home.py                      # Legacy Streamlit app entrypoint
├── pages/                       # Legacy Streamlit pages (0-9)
├── train_model.py               # Trains the K-Means model
├── train_ppo.py                 # Trains the US equities PPO agent
├── train_ppo_psx.py             # Trains the PSX equities PPO agent
├── modules/
│   ├── utils.py                 # Streamlit-side MongoDB helpers, auth, CSS loader
│   ├── news_fetcher.py          # News API integration (Streamlit-side)
│   └── ai/
│       ├── ppo_agent.py         # PPO agent inference (shared by both apps)
│       ├── market_env.py        # RL market environment
│       ├── feature_eng.py       # Feature engineering for the PPO models
│       └── sentiment.py         # FinBERT sentiment pipeline (Streamlit-side)
├── modules/model/
│   ├── kmeans_model.pkl / scaler.pkl
│   ├── ppo/                     # Trained US equities PPO model
│   └── ppo_psx/                 # Trained PSX equities PPO model
├── assets/                      # Logo assets (used by both apps + backend emails)
├── .env                         # Environment variables (git-ignored, not committed)
└── data/
    └── users_dataset.json       # Dataset used for K-Means training
```

---

## Key Features

| Feature | Detail |
|---|---|
| Auth | Email/password signup+login, bcrypt hashing, JWT session cookie, password strength & duplicate-email validation |
| Risk Classification | K-Means assigns users to one of 4 risk clusters based on their profile |
| Dashboard | Portfolio metrics, performance chart, holdings input, asset allocation pie, PDF report export, 3D AI cluster placement |
| AI Recommendations | MPT-optimised allocation for your risk profile + "Trending with Investors Like You" peer insights |
| Market Overview | Live/delayed candlestick charts for US (stocks, crypto, indices, commodities) and PSX markets |
| News Sentiment | FinBERT-scored financial headlines, US (Alpaca) and PSX (Google News RSS) |
| Feedback | Quick feedback form + optional usability survey |
| Edit Profile | View/edit financial profile, change name/email (password-gated), export profile data, email preferences |
| Transactional Email | Welcome, holdings-updated, credentials-updated, and account-deletion emails via Gmail SMTP |
| PPO Advisors | BUY/HOLD/SELL signals with confidence, for US and PSX equities — Streamlit app only for now |

---

## Notes

- **No real financial advice.** AIPRS is an independent personal project for research and
  educational purposes. It is not a licensed financial advisory service and does not execute
  real trades.
- **Alpaca feed.** The IEX feed used is free-tier and carries a 15-minute delay.
- **Caching.** Market/news data is cached for 15 minutes server-side. Restart the backend (or use
  a page's "Refresh" control where available) to force a refetch.
- **Identity model.** Session identity is keyed on **email**, not display name — names are free
  text and intentionally not unique.

---

## License

All rights reserved. Not currently licensed for reuse or redistribution.
