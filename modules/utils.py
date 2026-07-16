import streamlit as st
import pandas as pd
import os
import joblib
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

load_dotenv()

# ---- FILE PATHS ----
MODULES_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR   = os.path.join(MODULES_DIR, 'model')

BASE_DIR = os.path.dirname(MODULES_DIR)

# ---- SHARED PLOTLY CONFIG ----
# Trims the modebar to the buttons actually used, so the row fits inside
# narrower chart containers instead of being clipped on the right.
PLOTLY_MODEBAR_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "lasso2d", "select2d", "toggleSpikelines",
        "hoverCompareCartesian", "hoverClosestCartesian",
    ],
}

if not os.path.exists(MODEL_DIR):
    MODEL_DIR = BASE_DIR

@st.cache_resource(show_spinner=False)
def get_db():
    """
    Returns the AIPRS MongoDB database object.
    Cached as a resource so the connection is reused across reruns
    rather than opening a new socket every time.
    """
    uri = os.getenv("MONGODB_URI")
    if not uri:
        st.error("MONGODB_URI not found in .env — database features are unavailable.")
        return None
    client = MongoClient(uri)
    db     = client["aiprs"]

    # ── Ensure indexes on first boot ──────────────────────────────────────────
    # Unique index on email so duplicate registrations are rejected at DB level
    db["users"].create_index([("email", ASCENDING)], unique=True)
    # Index on feedback/survey timestamps for chronological queries
    db["feedback"].create_index([("timestamp", ASCENDING)])
    db["surveys"].create_index([("timestamp",  ASCENDING)])

    return db


# ---- USER COLLECTION HELPERS ----

def create_user(user_data: dict) -> tuple[bool, str]:
    """
    Insert a new user document into the 'users' collection.
    Returns (success: bool, message: str).
    Fields stored: name, email, password (hashed), age, income_range,
                   risk_tolerance, investment_horizon, experience,
                   goals, preferences (list), cluster, created_at.
    """
    db = get_db()
    if db is None:
        return False, "Database unavailable."
    try:
        db["users"].insert_one(user_data)
        return True, "User created successfully."
    except DuplicateKeyError:
        return False, "An account with this email already exists."
    except Exception as e:
        return False, str(e)


def get_user_by_email(email: str) -> dict | None:
    """Fetch a single user document by email. Returns None if not found."""
    db = get_db()
    if db is None:
        return None
    return db["users"].find_one({"email": email.strip().lower()})


def get_user_by_name(name: str) -> dict | None:
    """Fetch a single user document by name. Returns None if not found."""
    db = get_db()
    if db is None:
        return None
    return db["users"].find_one({"name": name})


def get_all_users() -> list[dict]:
    """Return all user documents (excluding passwords) for cluster analysis."""
    db = get_db()
    if db is None:
        return []
    return list(db["users"].find({}, {"password": 0}))


def update_user(name: str, updates: dict) -> tuple[bool, str]:
    """Apply a $set update to a user document by name."""
    db = get_db()
    if db is None:
        return False, "Database unavailable."
    try:
        result = db["users"].update_one({"name": name}, {"$set": updates})
        if result.matched_count == 0:
            return False, "User not found."
        return True, "Updated successfully."
    except Exception as e:
        return False, str(e)


def delete_user(name: str) -> tuple[bool, str]:
    """Permanently delete a user document by name."""
    db = get_db()
    if db is None:
        return False, "Database unavailable."
    try:
        result = db["users"].delete_one({"name": name})
        if result.deleted_count == 0:
            return False, "User not found."
        return True, "Account deleted."
    except Exception as e:
        return False, str(e)


# ---- FEEDBACK COLLECTION HELPERS ----

def save_feedback(feedback_data: dict) -> tuple[bool, str]:
    """Insert a feedback document into the 'feedback' collection."""
    db = get_db()
    if db is None:
        return False, "Database unavailable."
    try:
        db["feedback"].insert_one(feedback_data)
        return True, "Feedback saved."
    except Exception as e:
        return False, str(e)


def save_survey(survey_data: dict) -> tuple[bool, str]:
    """Insert a survey document into the 'surveys' collection."""
    db = get_db()
    if db is None:
        return False, "Database unavailable."
    try:
        db["surveys"].insert_one(survey_data)
        return True, "Survey saved."
    except Exception as e:
        return False, str(e)


# ---- OVERLAY NOTIFICATION ----
def show_overlay_notification(message: str, submessage: str = ""):
    """
    Full-screen overlay notification that fades out after 3 seconds.
    Pure CSS animation, no JavaScript required.
    """
    sub_html = (
        f"<div style='color:#A1A1AA;font-size:14px;margin-top:10px;line-height:1.5;'>"
        f"{submessage}</div>"
    ) if submessage else ""
    st.markdown(f"""
    <style>
    @keyframes _aiprs_overlay {{
        0%   {{ opacity: 0; }}
        12%  {{ opacity: 1; }}
        75%  {{ opacity: 1; }}
        100% {{ opacity: 0; }}
    }}
    ._aiprs_overlay_wrap {{
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.72);
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: _aiprs_overlay 3s ease forwards;
        pointer-events: none;
    }}
    ._aiprs_overlay_card {{
        background: linear-gradient(135deg, rgba(12,10,0,0.97), rgba(28,20,0,0.97));
        border: 1px solid rgba(217,119,6,0.55);
        border-radius: 20px;
        padding: 40px 56px;
        text-align: center;
        box-shadow: 0 0 60px rgba(217,119,6,0.25), 0 0 120px rgba(217,119,6,0.08);
        max-width: 440px;
    }}
    ._aiprs_overlay_icon {{
        font-size: 52px;
        margin-bottom: 16px;
        line-height: 1;
    }}
    ._aiprs_overlay_msg {{
        color: #FCD34D;
        font-size: 22px;
        font-weight: 700;
        font-family: 'Poppins', sans-serif;
        letter-spacing: 0.3px;
    }}
    </style>
    <div class="_aiprs_overlay_wrap">
        <div class="_aiprs_overlay_card">
            <div class="_aiprs_overlay_icon">✅</div>
            <div class="_aiprs_overlay_msg">{message}</div>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---- AUTH WALL ----
def show_auth_wall(page_description: str = "this page"):
    """
    Renders a centered, styled 'Login Required' card and stops execution.
    Call after set_sidebar_header('Guest') and any page heading.
    """
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown(f"""
        <div style='
            background: linear-gradient(135deg, rgba(217,119,6,0.10), rgba(255,255,255,0.02));
            border: 1px solid rgba(217,119,6,0.30);
            border-left: 4px solid #D97706;
            border-radius: 14px;
            padding: 28px 28px;
            text-align: center;
            box-shadow: 0 0 24px rgba(217,119,6,0.12);
        '>
            <div style='font-size: 36px; margin-bottom: 12px;'>🔒︎</div>
            <div style='font-size: 17px; font-weight: 700; color: #E4E4E7; margin-bottom: 8px;'>
                Login Required
            </div>
            <div style='font-size: 13px; color: #A1A1AA; line-height: 1.6;'>
                You must be logged in to view {page_description}.<br>
                Sign in to unlock your personalised AIPRS experience.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("🔐 Go to Login", key="auth_wall_login_btn", use_container_width=True):
            st.switch_page("pages/8_Login.py")
    st.stop()


# ---- CSS LOADER ----
def load_css():
    hide_login_nav_css = """
    <style>
        [data-testid="stSidebarNav"] a[href*="Login"] {
            display: none !important;
        }
    </style>
    """
    st.markdown(hide_login_nav_css, unsafe_allow_html=True)

    css_path = "styles.css"
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


# ---- SIDEBAR HEADER & PROFILE ----
def set_sidebar_header(username="Guest"):
    if "_overlay_notif" in st.session_state:
        _notif = st.session_state.pop("_overlay_notif")
        show_overlay_notification(_notif[0], _notif[1])
    with st.sidebar:
        if username == "Guest":
            profile_html = """
            <div style='
                display: flex; align-items: center; gap: 12px;
                padding: 10px 12px;
                background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.09);
                margin-top: 8px;'>
                <div style='font-size: 20px; flex-shrink:0;'>👤</div>
                <div style='line-height: 1.3;'>
                    <div style='font-weight: 600; font-size: 14px; color: #FFF;'>Guest User</div>
                    <div style='font-size: 11px; color: #A1A1AA;'>Not Logged In</div>
                </div>
            </div>
            """
            st.markdown(profile_html, unsafe_allow_html=True)
            st.write("")
            if st.button("🔐 Log In", key="sidebar_login_btn", use_container_width=True):
                st.switch_page("pages/8_Login.py")
        else:
            initial = username[0].upper() if username else "U"
            profile_html = f"""
            <div style='
                display: flex; align-items: center; gap: 12px;
                padding: 10px 12px;
                background: linear-gradient(135deg, rgba(217,119,6,0.10), rgba(252,211,77,0.04));
                border-radius: 10px;
                border: 1px solid rgba(217,119,6,0.28);
                box-shadow: 0 0 12px rgba(217,119,6,0.10);
                margin-top: 8px;'>
                <div style='
                    background: linear-gradient(135deg, #D97706, #FCD34D);
                    color: white;
                    width: 36px; height: 36px; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    font-weight: bold; font-size: 15px;
                    box-shadow: 0 0 14px rgba(217, 119, 6, 0.55);
                    flex-shrink: 0;'>
                    {initial}
                </div>
                <div style='line-height: 1.3;'>
                    <div style='font-weight: 600; font-size: 14px; color: #FFF;'>{username}</div>
                    <div style='font-size: 11px; color: #00C853;'>
                        <span class='status-dot'>●</span> Active Investor
                    </div>
                </div>
            </div>
            """
            st.markdown(profile_html, unsafe_allow_html=True)
            st.write("")
            if st.button("Log Out", key="sidebar_logout_btn", use_container_width=True):
                st.session_state["_overlay_notif"] = (
                    "Logged Out",
                    f"See you next time, {username}!",
                )
                st.session_state.authenticated = False
                st.session_state.username = "Guest"
                st.rerun()


# ---- AI PREDICTION UTILS ----
INCOME_MAP     = {'< 25,000': 1, '25,000 - 50,000': 2, '50,000 - 100,000': 3, '100,000+': 4}
HORIZON_MAP    = {'1 Year': 1, '3-5 Years': 3, '5-10 Years': 5, '10+ Years': 10}
EXPERIENCE_MAP = {'Beginner': 1, 'Intermediate': 2, 'Advanced': 3}

def predict_user_cluster(age, income_range, risk_tolerance, horizon, experience):
    try:
        model_path  = os.path.join(MODEL_DIR, 'kmeans_model.pkl')
        scaler_path = os.path.join(MODEL_DIR, 'scaler.pkl')

        if not os.path.exists(model_path):
            return 0

        model  = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        new_data = pd.DataFrame({
            'Age':           [age],
            'Income_Score':  [INCOME_MAP.get(income_range, 1)],
            'Risk_Score':    [risk_tolerance],
            'Horizon_Score': [HORIZON_MAP.get(horizon, 1)],
            'Exp_Score':     [EXPERIENCE_MAP.get(experience, 1)],
        })

        cluster_id = model.predict(scaler.transform(new_data))[0]
        return int(cluster_id)

    except Exception:
        return 0

# ---- FOOTER ----
_PRIVACY_HTML = """
<div style='background:rgba(217,119,6,0.07);border-left:4px solid #D97706;border-radius:8px;padding:14px 18px;margin-bottom:20px;color:#A1A1AA;font-size:13px;line-height:1.6;'>
<strong style='color:#E4E4E7;'>In plain English:</strong> AIPRS collects your profile information to personalise AI investment recommendations. Your data is stored securely on MongoDB Atlas. We do not sell your data or use it for advertising. This is an academic platform, please do not use it as your sole basis for real financial decisions.
</div>
<p style='color:#A1A1AA;font-size:12px;'>Effective Date: June 2026 &nbsp;|&nbsp; Platform: AIPRS – AI-Powered Portfolio Recommendation System</p>
<hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);margin:12px 0;'>
<p style='color:#E4E4E7;font-size:13px;'><strong>1. Overview</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>AIPRS is an academic Final Year Project developed for research and educational purposes. This Privacy Policy explains what information we collect, how we use it, how it is stored, and your rights regarding your data. By using AIPRS, you consent to the practices described in this policy.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>2. Information We Collect</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>When you register and use AIPRS, we collect:</p>
<ul style='color:#A1A1AA;font-size:13px;line-height:1.9;padding-left:20px;'>
<li><strong style='color:#E4E4E7;'>Account credentials:</strong> full name, email address, and password. Passwords are hashed using bcrypt before storage and are never stored or accessible in plain text</li>
<li><strong style='color:#E4E4E7;'>Risk profile data:</strong> age, investment experience level, investment horizon, and risk tolerance score (1–10)</li>
<li><strong style='color:#E4E4E7;'>AI-derived data:</strong> your investor cluster classification generated by our K-Means model</li>
<li><strong style='color:#E4E4E7;'>Feedback and survey responses:</strong> any feedback or survey submissions you make within the platform</li>
<li><strong style='color:#E4E4E7;'>Session data:</strong> login state is maintained through Streamlit session state for the duration of your browser session. No persistent cookies are set by AIPRS</li>
</ul>
<p style='color:#E4E4E7;font-size:13px;'><strong>3. How We Use Your Information</strong></p>
<ul style='color:#A1A1AA;font-size:13px;line-height:1.9;padding-left:20px;'>
<li>Personalise PPO-based investment recommendations to your risk profile</li>
<li>Generate and display your investor cluster classification</li>
<li>Collect platform feedback to support academic evaluation and improvement</li>
<li>Maintain your authenticated session while you are using the platform</li>
</ul>
<p style='color:#E4E4E7;font-size:13px;'><strong>4. Data Storage</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>All user data is stored on <strong style='color:#E4E4E7;'>MongoDB Atlas</strong>, a cloud-hosted database service provided by MongoDB, Inc. MongoDB Atlas applies encryption at rest and in transit, and access is restricted to authorised system credentials only. CSV files may be present in the project directory as legacy artefacts but are no longer written to or used by the active system.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>5. Third-Party Data Sources</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>AIPRS retrieves market data from the following external services. Your personal information is never shared with these providers:</p>
<ul style='color:#A1A1AA;font-size:13px;line-height:1.9;padding-left:20px;'>
<li><strong style='color:#E4E4E7;'>Alpaca Markets:</strong> historical and live market data for US equities</li>
<li><strong style='color:#E4E4E7;'>Yahoo Finance:</strong> historical OHLCV data for PSX equities</li>
<li><strong style='color:#E4E4E7;'>psxterminal.com:</strong> live price snapshots and symbol lists for PSX equities</li>
</ul>
<p style='color:#E4E4E7;font-size:13px;'><strong>6. Cookies and Tracking</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>AIPRS does not use cookies, advertising trackers, or any third-party analytics tools. No behavioural tracking is performed.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>7. Data Security</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>Passwords are stored as hashed values and are never readable by the development team. Database access is protected by credentials restricted to the AIPRS application. As an academic prototype, AIPRS is not intended for production use and should not be used to store sensitive financial information beyond what is required for the platform.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>8. Data Retention</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>Your profile and account data are retained for the duration of your account. You may request deletion of your account and all associated data by contacting the AIPRS team.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>9. Your Rights</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>You have the right to access the personal data we hold about you, request correction of inaccurate data, and request full deletion of your account and associated data.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>10. Contact</strong></p>
<p style='color:#A1A1AA;font-size:13px;'>For any privacy-related queries, contact the AIPRS development team at: <strong style='color:#E4E4E7;'>aiprs.support@gmail.com</strong></p>
"""

_TC_HTML = """
<div style='background:rgba(217,119,6,0.07);border-left:4px solid #D97706;border-radius:8px;padding:14px 18px;margin-bottom:20px;color:#A1A1AA;font-size:13px;line-height:1.6;'>
<strong style='color:#E4E4E7;'>In plain English:</strong> AIPRS is a university final year project. Its AI recommendations are not professional financial advice and must not be used as the sole basis to make real investment decisions. Use this platform for educational purposes only.
</div>
<p style='color:#A1A1AA;font-size:12px;'>Effective Date: June 2026 &nbsp;|&nbsp; Platform: AIPRS – AI-Powered Portfolio Recommendation System</p>
<hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);margin:12px 0;'>
<p style='color:#E4E4E7;font-size:13px;'><strong>1. Acceptance of Terms</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>By registering and using AIPRS, you agree to these Terms &amp; Conditions in full. If you do not agree, you must not use the platform.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>2. Nature of the Platform</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>AIPRS is an <strong style='color:#E4E4E7;'>academic Final Year Project</strong> built for research and educational demonstration. It is not a licensed financial advisory service, investment platform, or brokerage. It is not regulated by any financial authority.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>3. Not Financial Advice and No Real-Money Use</strong></p>
<div style='background:rgba(239,68,68,0.08);border-left:4px solid #EF4444;border-radius:8px;padding:12px 16px;margin:8px 0 12px 0;'>
<p style='color:#E4E4E7;font-size:13px;margin:0;line-height:1.7;'><strong>AIPRS recommendations must not be used to make real investment decisions.</strong> All outputs, including BUY, HOLD, and SELL signals, confidence scores, and risk classifications are produced by experimental AI models for educational and demonstration purposes only. They do not constitute financial advice or regulated financial guidance. AIPRS and its developers accept <strong>no responsibility or liability whatsoever</strong> for any financial loss arising from actions taken based on anything displayed on this platform. Always consult a qualified and licensed financial advisor before making any investment.</p>
</div>
<p style='color:#E4E4E7;font-size:13px;'><strong>4. AI Model Limitations</strong></p>
<ul style='color:#A1A1AA;font-size:13px;line-height:1.9;padding-left:20px;'>
<li>Models are trained on a fixed universe of stocks and may not generalise reliably to all tickers</li>
<li>Training data spans approximately 5 years of historical market data, which may not reflect future market conditions</li>
<li>The US PPO model covers US equities; the PSX PPO model covers Pakistan Stock Exchange equities, and cross-market use is not supported</li>
<li>Model outputs are probabilistic and will sometimes be incorrect</li>
</ul>
<p style='color:#E4E4E7;font-size:13px;'><strong>5. Market Data Disclaimer</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>Market data is sourced from Alpaca Markets, Yahoo Finance, and psxterminal.com. AIPRS does not guarantee the accuracy, completeness, or timeliness of this data. Live PSX prices may be delayed or temporarily unavailable. All market data is provided for informational and educational purposes only.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>6. Eligibility and Intended Use</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>By using AIPRS, you confirm that you are using the platform for educational, research, or demonstration purposes only, and that you will not use AIPRS to manage, advise on, or execute real financial transactions.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>7. Acceptable Use</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>You agree not to attempt to reverse-engineer or exploit the platform or its AI models, use AIPRS to provide financial advice to any party, share your account credentials with others, or submit false or misleading information through any form or feedback mechanism on the platform.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>8. Account Termination</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>The AIPRS development team reserves the right to suspend or terminate any account found to be in violation of these Terms or misusing the platform.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>9. Intellectual Property</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>All source code, trained models, and content within AIPRS are the intellectual property of the AIPRS development team and are submitted as part of an academic Final Year Project. Unauthorised reproduction, distribution, or commercial use is not permitted.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>10. Modifications</strong></p>
<p style='color:#A1A1AA;font-size:13px;line-height:1.7;'>These Terms may be updated at any time without prior notice. Continued use of the platform following any changes constitutes your acceptance of the revised Terms.</p>
<p style='color:#E4E4E7;font-size:13px;'><strong>11. Contact</strong></p>
<p style='color:#A1A1AA;font-size:13px;'>For any queries regarding these Terms, contact the AIPRS development team at: <strong style='color:#E4E4E7;'>aiprs.support@gmail.com</strong></p>
"""


@st.dialog("📄 Privacy Policy", width="large")
def _privacy_policy_modal():
    st.markdown(_PRIVACY_HTML, unsafe_allow_html=True)


@st.dialog("📋 Terms & Conditions", width="large")
def _terms_conditions_modal():
    st.markdown(_TC_HTML, unsafe_allow_html=True)


def render_footer():
    st.markdown(
        "<br><hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);margin:0;'>",
        unsafe_allow_html=True,
    )
    st.markdown("""
    <style>
    /* Override the global .stButton > button rule for tertiary footer buttons */
    [data-testid="stBaseButton-tertiary"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 4px !important;
        min-height: unset !important;
        color: #6B7280 !important;
        font-weight: 400 !important;
        font-size: 12px !important;
    }
    [data-testid="stBaseButton-tertiary"]:hover {
        background: transparent !important;
        transform: none !important;
        box-shadow: none !important;
        color: #E4E4E7 !important;
        text-decoration: underline !important;
        cursor: pointer !important;
    }
    [data-testid="stBaseButton-tertiary"] p {
        color: #6B7280 !important;
        font-size: 12px !important;
        font-weight: 400 !important;
    }
    [data-testid="stBaseButton-tertiary"]:hover p {
        color: #E4E4E7 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    copy_col, pp_col, tc_col = st.columns([5, 0.8, 1], gap="small")
    with copy_col:
        st.markdown(
            "<p style='color:#6B7280;font-size:12px;margin:6px 0 0;'>"
            "© 2026 AIPRS – All rights reserved.</p>",
            unsafe_allow_html=True,
        )
    with pp_col:
        if st.button("Privacy Policy", key="footer_privacy_btn", type="tertiary"):
            _privacy_policy_modal()
    with tc_col:
        if st.button("Terms & Conditions", key="footer_tc_btn", type="tertiary"):
            _terms_conditions_modal()