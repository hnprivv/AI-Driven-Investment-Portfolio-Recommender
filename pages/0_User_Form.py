import re
import streamlit as st
import modules.utils
import time
import bcrypt
from datetime import datetime, timezone

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "1234567890", "qwerty123", "qwerty", "abc12345", "iloveyou",
    "admin123", "letmein", "welcome1", "monkey123", "dragon123",
}

def _validate_password(pw: str) -> str | None:
    """Returns an error message string, or None if the password is valid."""
    if not pw.strip():
        return "Password must not consist of only whitespace."
    if len(pw) < 8:
        return "Password must be at least 8 characters long."
    if len(pw) > 128:
        return "Password must not exceed 128 characters."
    if pw.lower() in _COMMON_PASSWORDS:
        return "This password is too common. Please choose a stronger one."
    if not re.search(r"[A-Z]", pw):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"\d", pw):
        return "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain at least one special character (e.g. @, #, !)."
    return None

st.set_page_config(page_title="AIPRS – Create Profile", page_icon="assets/aiprs.png", layout="wide")
modules.utils.load_css()

if "authenticated" in st.session_state and st.session_state.authenticated and "username" in st.session_state:
    name = st.session_state.username
else:
    name = "Guest"

modules.utils.set_sidebar_header(name)

# ---- HEADER ----
st.markdown("""
<div class='custom-title-box'>
    <h1>Investor Profile & Sign Up</h1>
</div>
<p style='text-align:center; color:#A1A1AA;'>
    Create your account and let our AI analyze your financial profile in one step.
</p>
<br>
""", unsafe_allow_html=True)

# ---- FORM ----
with st.form("user_profile_form"):

    st.markdown("### 1. Account Details")
    col_acc1, col_acc2 = st.columns(2)
    with col_acc1:
        name_input  = st.text_input("Full Name",     placeholder="e.g. John Doe")
        email_input = st.text_input("Email Address", placeholder="name@example.com")
    with col_acc2:
        password_input = st.text_input("Create Password",  type="password")
        confirm_pass   = st.text_input("Confirm Password", type="password")

    st.markdown("---")

    st.markdown("### 2. Financial Profile")
    col1, col2 = st.columns(2)
    with col1:
        age_input    = st.number_input("Age", min_value=18, max_value=100, value=25)
        income_input = st.selectbox("Annual Income Range",
            ["< 25,000", "25,000 - 50,000", "50,000 - 100,000", "100,000+"])
    with col2:
        horizon_input = st.selectbox("Investment Horizon",
            ["1 Year", "3-5 Years", "5-10 Years", "10+ Years"])
        exp_input     = st.selectbox("Investment Experience",
            ["Beginner", "Intermediate", "Advanced"])

    st.markdown("### 3. Goals & Preferences")
    goals_input       = st.selectbox("Primary Goal",
        ["Stable income", "Long-term stability", "Short-term trading", "Retirement"])
    preferences_input = st.multiselect("Preferred Assets (Optional)",
        ["Stocks", "Bonds", "Real Estate", "Crypto", "ETFs", "Commodities"])

    st.markdown("### 4. Risk Assessment")
    risk_slider = st.slider("Risk Tolerance (1 = Low, 10 = High)", 1, 10, 5)

    agreed = st.checkbox(
        "I have read and agree to the Privacy Policy and Terms & Conditions"
    )

    st.write("")
    submitted = st.form_submit_button("Create Account & Analyze Profile", use_container_width=True)

    if submitted:
        # ---- Validation ----
        valid = True
        if not agreed:
            st.error("You must read and agree to the Privacy Policy and Terms & Conditions to create an account.")
            valid = False
        elif not (name_input and email_input and password_input):
            st.error("Please fill out all Account Details (Name, Email, Password).")
            valid = False
        elif not _EMAIL_RE.match(email_input.strip()):
            st.error("Please enter a valid email address (e.g. name@example.com).")
            valid = False
        elif modules.utils.get_user_by_email(email_input) is not None:
            st.error("An account with this email already exists. Please log in instead.")
            valid = False
        else:
            pw_error = _validate_password(password_input)
            if pw_error:
                st.error(pw_error)
                valid = False
            elif password_input != confirm_pass:
                st.error("Passwords do not match!")
                valid = False

        if valid:
            # ---- AI Clustering ----
            predicted_cluster = modules.utils.predict_user_cluster(
                age=age_input,
                income_range=income_input,
                risk_tolerance=risk_slider,
                horizon=horizon_input,
                experience=exp_input,
            )

            # ---- Build document ----
            user_doc = {
                "name":               name_input,
                "email":              email_input.strip().lower(),
                "age":                int(age_input),
                "income_range":       income_input,
                "risk_tolerance":     int(risk_slider),
                "investment_horizon": horizon_input,
                "experience":         exp_input,
                "goals":              goals_input,
                "preferences":        preferences_input,
                "cluster":            predicted_cluster,
                "created_at":         datetime.now(timezone.utc),
                "password":           bcrypt.hashpw(
                                          password_input.encode("utf-8"), bcrypt.gensalt()
                                      ).decode("utf-8"),
            }

            # ---- Save to MongoDB ----
            success, message = modules.utils.create_user(user_doc)

            if success:
                st.success(f"Profile created! Our AI has assigned you to Investor Group {predicted_cluster}.")
                st.session_state.authenticated = True
                st.session_state.username = name_input.strip()
                time.sleep(2)
                st.switch_page("Home.py")
            else:
                st.error(f"Could not create account: {message}")

modules.utils.render_footer()
