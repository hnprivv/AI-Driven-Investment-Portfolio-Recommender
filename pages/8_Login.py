import time
import bcrypt
import streamlit as st
import modules.utils

st.set_page_config(page_title="AIPRS – Login", page_icon="assets/aiprs.png", layout="centered")
modules.utils.load_css()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = "Guest"


def validate_login(email: str, password: str) -> str | None:
    """Returns display name on success, None on failure."""
    user = modules.utils.get_user_by_email(email)
    if user is None:
        return None
    stored_hash = user.get("password", "")
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return None
    return user.get("name") if ok else None


# ---- LOGGED-IN VIEW ---------------------------------------------------------

if st.session_state.authenticated:
    st.markdown(f"""
    <div class='custom-title-box'>
        <h1>👤 Welcome Back, {st.session_state.username}</h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("You are currently logged in.")
    if st.button("Log Out", type="primary", use_container_width=True):
        st.session_state["_overlay_notif"] = (
            "Logged Out",
            f"See you next time, {st.session_state.username}!",
        )
        st.session_state.authenticated = False
        st.session_state.username = "Guest"
        st.rerun()


# ---- LOGIN FORM VIEW --------------------------------------------------------

else:
    st.markdown("""
    <div class='custom-title-box'>
        <h1>Log In</h1>
    </div>
    <p style='text-align:center; color:#A1A1AA;'>Access your portfolio and personalized settings.</p>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email_input    = st.text_input("Email Address", placeholder="name@example.com")
        password_input = st.text_input("Password", type="password", placeholder="••••••••")
        submit = st.form_submit_button("Log In", use_container_width=True)

        if submit:
            if email_input and password_input:
                with st.spinner("Verifying credentials..."):
                    result = validate_login(email_input, password_input)
                if result:
                    st.session_state.authenticated = True
                    st.session_state.username = result
                    modules.utils.show_overlay_notification(
                        f"Welcome back,<br>{result}!",
                        "Redirecting you to your dashboard...",
                    )
                    time.sleep(2)
                    st.switch_page("Home.py")
                else:
                    st.error("Invalid email or password. Please try again.")
            else:
                st.error("Please enter both email and password.")

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account", use_container_width=True):
            st.switch_page("pages/0_User_Form.py")
    with col2:
        if st.button("Continue as Guest", use_container_width=True):
            st.switch_page("Home.py")

st.markdown(
    "<br><hr style='border:none;border-top:1px solid rgba(255,255,255,0.08);margin:0;'>"
    "<p style='color:#6B7280;font-size:12px;text-align:center;margin-top:8px;'>"
    "© 2026 AIPRS – All rights reserved.</p>",
    unsafe_allow_html=True,
)
