import streamlit as st
from datetime import datetime, timezone
import modules.utils

st.set_page_config(page_title="AIPRS – Feedback", page_icon="assets/aiprs.png", layout="wide")

modules.utils.load_css()

# ---- #1: Tab styling ----
st.markdown("""
<style>
[data-baseweb="tab-highlight"] {
    background-color: #D97706 !important;
    height: 2px !important;
}
[data-baseweb="tab-border"] {
    background-color: rgba(217,119,6,0.20) !important;
}
[data-baseweb="tab"] {
    color: #A1A1AA !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: color 0.2s ease !important;
}
[data-baseweb="tab"]:hover {
    color: #E4E4E7 !important;
    background: rgba(217,119,6,0.08) !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #FCD34D !important;
    text-shadow: 0 0 8px rgba(217,119,6,0.35) !important;
}

</style>
""", unsafe_allow_html=True)

if 'authenticated' in st.session_state and st.session_state.authenticated and 'username' in st.session_state:
    name = st.session_state.username
else:
    name = 'Guest'

modules.utils.set_sidebar_header(name)

# ---- HEADER ----
st.markdown("""
<div class='custom-title-box'>
    <h1>Share Your Feedback</h1>
</div>
<p style='text-align:center; color:#A1A1AA;'>Help us improve AIPRS by sharing your thoughts, suggestions, and reporting any issues.</p>
<br>
""", unsafe_allow_html=True)

# ---- Helpers ----

def form_divider():
    """#4: Compact ◆ section divider."""
    st.markdown("""
    <div style='display:flex;align-items:center;gap:12px;margin:20px 0 14px;'>
        <div style='flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(217,119,6,0.45));'></div>
        <div style='color:#D97706;font-size:11px;text-shadow:0 0 6px rgba(217,119,6,0.5);'>◆</div>
        <div style='flex:1;height:1px;background:linear-gradient(90deg,rgba(217,119,6,0.45),transparent);'></div>
    </div>
    """, unsafe_allow_html=True)

def section_heading(icon: str, title: str):
    """#8: Purple-bordered section heading card."""
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(217,119,6,0.09),rgba(255,255,255,0.02));"
        f"border:1px solid rgba(217,119,6,0.22);border-left:3px solid #D97706;"
        f"border-radius:10px;padding:10px 16px;margin-bottom:14px;'>"
        f"<span style='font-weight:700;font-size:15px;color:#FCD34D;'>{icon}&nbsp; {title}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

def success_card(message: str):
    """#5: Styled success card replacing st.success."""
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(217,119,6,0.10),rgba(252,211,77,0.05));"
        f"border:1px solid rgba(217,119,6,0.35);border-left:4px solid #D97706;"
        f"border-radius:14px;padding:22px 24px;margin-top:16px;"
        f"box-shadow:0 0 20px rgba(217,119,6,0.12);'>"
        f"<div style='font-size:28px;margin-bottom:10px;'>✅</div>"
        f"<div style='font-weight:700;color:#FCD34D;font-size:16px;margin-bottom:6px;'>Response Recorded</div>"
        f"<div style='color:#A1A1AA;font-size:14px;line-height:1.65;text-align:left;'>{message}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ---- Slider label helper (#6) ----
def slider_labels(low: str, high: str):
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;"
        f"margin-top:-14px;margin-bottom:14px;'>"
        f"<span style='color:#A1A1AA;font-size:11px;'>{low}</span>"
        f"<span style='color:#A1A1AA;font-size:11px;'>{high}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["📧 Quick Feedback Form", "📋 Optional System Survey"])

# ══════════════════════════════════════════════════════
# TAB 1 — QUICK FEEDBACK
# ══════════════════════════════════════════════════════
with tab1:

    # #2: Context card
    st.markdown("""
    <div style='background:linear-gradient(135deg,rgba(217,119,6,0.08),rgba(255,255,255,0.02));
                border:1px solid rgba(217,119,6,0.22);border-left:4px solid #D97706;
                border-radius:14px;padding:18px 22px;margin-bottom:22px;'>
        <p style='color:#A1A1AA;margin:0;font-size:14px;line-height:1.65;text-align:left;'>
            Use this form to send us <b style='color:#FCD34D;'>bug reports</b>,
            <b style='color:#FCD34D;'>feature suggestions</b>, or any
            <b style='color:#FCD34D;'>general comments</b>. Your input is logged and
            reviewed by the AIPRS team to continuously improve the platform.
        </p>
    </div>
    """, unsafe_allow_html=True)

    def _feedback_form(feedback_type: str, key: str):
        """Renders the Details + Follow-up form for a given feedback type."""
        with st.form(key=f"feedback_form_{key}", clear_on_submit=True):
            section_heading("📄", "Details")
            page = st.selectbox(
                "Related page (optional):",
                ['General System', 'Home', 'User Form', 'Overview',
                 'AI Recommendations', 'Other'],
                key=f"page_{key}",
            )
            feedback_text = st.text_area(
                "Your feedback / description of issue:",
                placeholder="Please be specific. E.g., 'The chart on the Performance Tracker page doesn't load when I click Refresh.'",
                key=f"text_{key}",
            )
            form_divider()
            section_heading("📬", "Follow-up")
            contact_info = st.text_input(
                "Email / contact info (optional):",
                placeholder="Your email if you'd like a follow-up response.",
                key=f"contact_{key}",
            )
            submit_button = st.form_submit_button("Send Feedback", use_container_width=True)

            if submit_button:
                if not feedback_text:
                    st.error("Please provide text feedback before submitting.")
                else:
                    feedback_doc = {
                        "timestamp":     datetime.now(timezone.utc),
                        "user_name":     name,
                        "feedback_type": feedback_type,
                        "related_page":  page,
                        "feedback_text": feedback_text,
                        "contact_info":  contact_info,
                    }
                    saved, msg = modules.utils.save_feedback(feedback_doc)
                    if saved:
                        success_card(
                            f"Thank you, <b style='color:#E4E4E7;'>{name}</b>! Your "
                            f"<b style='color:#E4E4E7;'>{feedback_type}</b> has been recorded. "
                            "We'll review it shortly."
                        )
                    else:
                        st.error(f"An error occurred while saving feedback: {msg}")

    type_tab1, type_tab2, type_tab3 = st.tabs([
        "🟢  Suggestion",
        "🔴  Bug Report",
        "🔵  General",
    ])
    with type_tab1:
        _feedback_form("Suggestion / Feature Request", "suggestion")
    with type_tab2:
        _feedback_form("Bug Report / Issue", "bug")
    with type_tab3:
        _feedback_form("General Comment", "general")

# ══════════════════════════════════════════════════════
# TAB 2 — SURVEY  (no st.form so progress bar is reactive)
# ══════════════════════════════════════════════════════
with tab2:

    # #2: Context card
    st.markdown("""
    <div style='background:linear-gradient(135deg,rgba(217,119,6,0.08),rgba(255,255,255,0.02));
                border:1px solid rgba(217,119,6,0.22);border-left:4px solid #D97706;
                border-radius:14px;padding:18px 22px;margin-bottom:22px;'>
        <p style='color:#A1A1AA;margin:0;font-size:14px;line-height:1.65;text-align:left;'>
            This optional survey helps us understand your overall experience with AIPRS.
            Ratings are <b style='color:#FCD34D;'>anonymous</b> and take under
            <b style='color:#FCD34D;'>2 minutes</b> to complete.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("survey_done"):
        success_card(
            f"Thank you, <b style='color:#E4E4E7;'>{name}</b>! "
            "Your detailed survey response has been recorded. "
            "Your input directly shapes the future of AIPRS."
        )
        if st.button("Submit Another Response", use_container_width=True):
            st.session_state.survey_done = False
            st.rerun()

    else:
        # #8: Section heading cards
        section_heading("⭐", "System Usability and Experience")

        q1 = st.slider("How intuitive did you find the AIPRS navigation?",           1, 5, 3, key="q1")
        slider_labels("1 — Not at all intuitive", "5 — Extremely intuitive")

        q2 = st.slider("How useful are the AI Recommendations for your decisions?",   1, 5, 3, key="q2")
        slider_labels("1 — Not useful at all", "5 — Extremely useful")

        q3 = st.slider("How satisfied are you with the visual design and aesthetics?", 1, 5, 4, key="q3")
        slider_labels("1 — Very unsatisfied", "5 — Very satisfied")

        form_divider()
        section_heading("💡", "Missing Features")

        lacking_text = st.text_area(
            "What key features do you feel are currently lacking?",
            placeholder="E.g., 'I would like to see a dedicated crypto portfolio section.'",
            key="lacking",
        )
        open_text = st.text_area(
            "Any other comments or suggestions for improvement?",
            placeholder="E.g., 'The performance tracker needs better filtering options.'",
            key="open_text",
        )

        # #7: Reactive progress bar
        signals  = [q1 != 3, q2 != 3, q3 != 4, bool(lacking_text.strip()), bool(open_text.strip())]
        pct      = int(sum(signals) / len(signals) * 100)
        st.markdown(
            f"<div style='margin:20px 0 10px;'>"
            f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
            f"<span style='color:#A1A1AA;font-size:12px;'>Response completeness</span>"
            f"<span style='color:#FCD34D;font-size:12px;font-weight:600;'>{pct}%</span>"
            f"</div>"
            f"<div style='background:rgba(255,255,255,0.07);border-radius:6px;height:6px;overflow:hidden;'>"
            f"<div style='width:{pct}%;height:100%;background:linear-gradient(90deg,#D97706,#FCD34D);border-radius:6px;'></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        # #9: Consistent full-width submit button
        if st.button("Submit Survey", use_container_width=True, key="survey_btn"):
            survey_doc = {
                "timestamp":        datetime.now(timezone.utc),
                "user_name":        name,
                "q1_intuitive":     q1,
                "q2_useful":        q2,
                "q3_satisfied":     q3,
                "lacking_features": lacking_text,
                "open_text":        open_text,
            }
            saved, msg = modules.utils.save_survey(survey_doc)
            if saved:
                st.session_state.survey_done = True
                st.rerun()
            else:
                st.error(f"An error occurred while saving the survey: {msg}")

modules.utils.render_footer()
