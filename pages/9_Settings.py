import streamlit as st
import bcrypt
import json
import modules.utils

st.set_page_config(page_title="Settings", page_icon="assets/aiprs.png", layout="wide")

modules.utils.load_css()

# ---- Auth guard ----
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    modules.utils.set_sidebar_header("Guest")
    st.markdown("<h1 style='text-align:center;'>Settings</h1>", unsafe_allow_html=True)
    modules.utils.show_auth_wall("and manage your settings and account options")

name = st.session_state.username
modules.utils.set_sidebar_header(name)

# ---- Load user from DB ----
user = modules.utils.get_user_by_name(name)
if user is None:
    st.error("Could not load your profile. Please log in again.")
    st.stop()

# ---- Helper: section card wrapper ----
def section_card(title: str):
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, rgba(217,119,6,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(217,119,6,0.25);
        border-radius: 16px;
        padding: 22px 24px 8px;
        margin-bottom: 6px;
        box-shadow: 0 0 18px rgba(217,119,6,0.10);
    '>
    <h3 style='margin-top:0;'>{title}</h3>
    </div>
    """, unsafe_allow_html=True)

# ---- HEADER ----
st.markdown("""
<div class='custom-title-box'>
    <h1>Settings</h1>
</div>
<p style='text-align:center; color:#A1A1AA;'>Manage your account, notifications, and data.</p>
<br>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════
# LEFT COLUMN
# ══════════════════════════════════════════════════════
with col1:

    # ── Change Password ───────────────────────────────
    st.markdown("### 🔑 Change Password")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    with st.form("change_password_form", clear_on_submit=True):
        current_pw  = st.text_input("Current Password",     type="password", placeholder="••••••••")
        new_pw      = st.text_input("New Password",         type="password", placeholder="Min. 8 characters")
        confirm_pw  = st.text_input("Confirm New Password", type="password", placeholder="••••••••")
        pw_submit   = st.form_submit_button("Update Password", use_container_width=True)

    if pw_submit:
        if not current_pw or not new_pw or not confirm_pw:
            st.error("Please fill in all password fields.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        elif len(new_pw) < 8:
            st.error("New password must be at least 8 characters.")
        else:
            stored_hash = user.get("password", "")
            try:
                valid = bcrypt.checkpw(current_pw.encode(), stored_hash.encode())
            except Exception:
                valid = False

            if not valid:
                st.error("Current password is incorrect.")
            else:
                new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                ok, msg  = modules.utils.update_user(name, {"password": new_hash})
                if ok:
                    st.success("Password updated successfully.")
                else:
                    st.error(f"Could not update password: {msg}")

    st.markdown("---")

# ══════════════════════════════════════════════════════
# RIGHT COLUMN
# ══════════════════════════════════════════════════════
with col2:

    # ── Export Profile ────────────────────────────────
    st.markdown("### 📤 Export Profile Data")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#A1A1AA; font-size:14px;'>"
        "Download a copy of your AIPRS profile as a JSON file. "
        "Your password is excluded from the export."
        "</p>",
        unsafe_allow_html=True,
    )

    export_data = {k: v for k, v in user.items() if k not in ("_id", "password")}
    # Make non-serialisable types (ObjectId, datetime) safe
    for key, val in export_data.items():
        if hasattr(val, 'isoformat'):
            export_data[key] = val.isoformat()
        elif not isinstance(val, (str, int, float, bool, list, dict, type(None))):
            export_data[key] = str(val)

    st.download_button(
        label="⬇️ Download My Data",
        data=json.dumps(export_data, indent=2),
        file_name=f"aiprs_profile_{name.lower().replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("---")

    # ── Danger Zone ───────────────────────────────────
    st.markdown("""
    <div style='
        background: rgba(220,38,38,0.07);
        border: 1px solid rgba(220,38,38,0.35);
        border-bottom: none;
        border-radius: 16px 16px 0 0;
        padding: 20px 24px 16px;
        box-shadow: 0 0 16px rgba(220,38,38,0.08);
    '>
        <h3 style='
            background: linear-gradient(90deg, #dc2626, #f87171);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-top: 0;
        '>⚠️ Danger Zone</h3>
        <p style='color:#A1A1AA; font-size:13px; margin-bottom:0;'>
            Deleting your account is <b style='color:#f87171;'>permanent and cannot be undone</b>.
            All your profile data, risk assessments, and preferences will be removed.
        </p>
    </div>
    <div style='
        background: rgba(220,38,38,0.04);
        border: 1px solid rgba(220,38,38,0.35);
        border-top: none;
        border-radius: 0 0 16px 16px;
        padding: 16px 24px 20px;
    '>
    </div>
    """, unsafe_allow_html=True)

    # Form elements sit flush below the card — visually continuous
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-child(2) > div:last-child [data-testid="stTextInput"],
    div[data-testid="column"]:nth-child(2) > div:last-child [data-testid="stButton"] {
        margin-top: -8px;
    }
    </style>
    """, unsafe_allow_html=True)

    confirm_name = st.text_input("Type your username to confirm", placeholder=name, key="delete_confirm")
    delete_btn   = st.button("🗑️ Permanently Delete Account", type="primary", use_container_width=True)

    if delete_btn:
        if confirm_name != name:
            st.error("Username does not match. Deletion cancelled.")
        else:
            ok, msg = modules.utils.delete_user(name)
            if ok:
                st.session_state.authenticated = False
                st.session_state.username = "Guest"
                st.success("Your account has been deleted.")
                st.switch_page("Home.py")
            else:
                st.error(f"Could not delete account: {msg}")

# ---- FOOTER ----
st.markdown("""
<p style='text-align:center; color:#A1A1AA; font-size:13px;'>
AIPRS respects your privacy, no sensitive data is transmitted or shared externally.
</p>
""", unsafe_allow_html=True)

modules.utils.render_footer()
