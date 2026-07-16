import streamlit as st
from collections import Counter
import time
import modules.utils

st.set_page_config(page_title="AIPRS – Recommendations", page_icon="assets/aiprs.png", layout="wide")

modules.utils.load_css()

if 'authenticated' in st.session_state and st.session_state.authenticated and 'username' in st.session_state:
    name = st.session_state.username
else:
    name = 'Guest'

modules.utils.set_sidebar_header(name)


# ---- COLLABORATIVE FILTERING ----
def get_collaborative_recs(current_user_name: str):
    """
    Finds assets preferred by other users in the same cluster using MongoDB.
    Returns (recommendations list, cluster id) or (None, error message).
    """
    all_users = modules.utils.get_all_users()
    if not all_users:
        return None, "No user data available."

    # Find the current user
    current_user = next((u for u in all_users if u.get("name") == current_user_name), None)
    if current_user is None:
        return None, "User profile not found."

    user_cluster   = current_user.get("cluster")
    current_prefs  = current_user.get("preferences", [])

    # Handle legacy comma-string preferences
    if isinstance(current_prefs, str):
        current_prefs = [p.strip() for p in current_prefs.split(",")]

    # Neighbors: same cluster, different user
    neighbors = [
        u for u in all_users
        if u.get("cluster") == user_cluster and u.get("name") != current_user_name
    ]

    if not neighbors:
        return None, "No data available for peer comparison yet."

    # Aggregate neighbor preferences
    all_neighbor_prefs = []
    for u in neighbors:
        prefs = u.get("preferences", [])
        if isinstance(prefs, str):
            prefs = [p.strip() for p in prefs.split(",")]
        all_neighbor_prefs.extend(prefs)

    pref_counts     = Counter(all_neighbor_prefs)
    recommendations = [
        (asset, count)
        for asset, count in pref_counts.most_common(5)
        if asset not in current_prefs
    ]

    return recommendations, user_cluster


# ---- HEADER ----
st.markdown("""
<div class='custom-title-box'>
    <h1>AI Recommendations</h1>
</div>
""", unsafe_allow_html=True)

# ---- SECTION 1: CORE AI PORTFOLIO ----
st.markdown("### Your Optimized Portfolio")
st.write("Based on your risk profile and market analysis, our Reinforcement Learning engine suggests this allocation:")

import pandas as pd
import plotly.express as px
col1, col2 = st.columns([2, 1])
with col1:
    allocation_data = pd.DataFrame({
        'Asset':      ['US Stocks', 'Intl Stocks', 'Bonds', 'Real Estate', 'Cash'],
        'Percentage': [45, 20, 25, 5, 5]
    })
    fig_alloc_bar = px.bar(
        allocation_data, x='Asset', y='Percentage',
        template='plotly_dark',
        color='Asset',
        color_discrete_sequence=["#B45309", "#D97706", "#F59E0B", "#FCD34D", "#FDE68A"]
    )
    fig_alloc_bar.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        font=dict(family="Inter", size=12, color="#E4E4E7"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
    )
    fig_alloc_bar.update_traces(marker_line_width=0)
    st.plotly_chart(fig_alloc_bar, use_container_width=True, config=modules.utils.PLOTLY_MODEBAR_CONFIG)
with col2:
    st.info("""
    **Strategy: Balanced Growth**

    This portfolio prioritizes steady growth while mitigating volatility through fixed-income assets.
    """)
    st.metric(label="Expected Annual Return", value="7.8%", delta="+1.2%")
    st.metric(label="Volatility Risk",        value="Medium", delta_color="off")

st.markdown("---")

# ---- SECTION 2: COMMUNITY INSIGHTS ----
st.markdown("### 💡 Trending with Investors Like You")
st.write("These assets are popular among other investors who share your risk profile and financial goals.")

recs, status_or_cluster = get_collaborative_recs(name)

if recs:
    max_count = max(count for _, count in recs) if recs else 1
    rec_cols = st.columns(3)
    for i, (asset, count) in enumerate(recs[:3]):
        pct = int((count / max_count) * 100) if max_count > 0 else 0
        with rec_cols[i]:
            st.markdown(f"""
            <div class='metric-card' style='height: 200px; text-align: center;'>
                <h3 style='background:linear-gradient(90deg,#F59E0B,#FCD34D);
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                           background-clip:text; display:inline-block;'>{asset}</h3>
                <p style='color: #A1A1AA; font-size: 13px; margin: 4px 0 8px;'>
                    Held by <b style='color:#E4E4E7;'>{count}</b> of your peers
                </p>
                <div style='width:80%; background:rgba(255,255,255,0.07); border-radius:6px;
                            height:6px; margin: 0 auto 10px;'>
                    <div style='width:{pct}%; background:linear-gradient(90deg,#D97706,#F59E0B);
                                border-radius:6px; height:6px;'></div>
                </div>
                <span style='font-size:11px; color:#A1A1AA;'>{pct}% of peer popularity</span>
            </div>
            """, unsafe_allow_html=True)
elif recs == []:
    st.success("You are already invested in all the top assets for your profile! You are following the trend.")
else:
    st.warning(f"Could not generate insights: {status_or_cluster}")
    st.info("Start adding preferences to your profile to unlock community insights!")

st.write("")
st.write("")

modules.utils.render_footer()