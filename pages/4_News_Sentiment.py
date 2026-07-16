import datetime
import html as _html
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import modules.utils
from modules.news_fetcher import (
    get_market_news, get_ticker_news,
    get_psx_market_news, get_psx_company_news,
)
from modules.ai.sentiment import analyze_articles, _load_finbert

st.set_page_config(page_title="News Sentiment", page_icon="assets/aiprs.png", layout="wide")

modules.utils.load_css()

# ── Auth (guest accessible) ────────────────────────────────────────────────────
if "authenticated" in st.session_state and st.session_state.authenticated and "username" in st.session_state:
    name           = st.session_state.username
    is_auth        = True
else:
    name           = "Guest"
    is_auth        = False

modules.utils.set_sidebar_header(name)


# ==============================================================================
# HELPERS
# ==============================================================================

PSX_STOCKS = {
    "HBL":    "Habib Bank Limited",
    "ENGRO":  "Engro Corporation",
    "LUCK":   "Lucky Cement",
    "MCB":    "MCB Bank",
    "UBL":    "United Bank Limited",
    "PPL":    "Pakistan Petroleum",
    "OGDC":   "Oil & Gas Dev. Company",
    "PSO":    "Pakistan State Oil",
    "NESTLE": "Nestle Pakistan",
    "SYS":    "Systems Limited",
    "TRG":    "TRG Pakistan",
    "HUBC":   "Hub Power Company",
    "ATRL":   "Attock Refinery",
    "MEBL":   "Meezan Bank",
    "NBP":    "National Bank of Pakistan",
    "FFC":    "Fauji Fertilizer Company",
    "EFERT":  "Engro Fertilizers",
    "DGKC":   "D.G. Khan Cement",
    "COLG":   "Colgate-Palmolive Pakistan",
    "GLAXO":  "GlaxoSmithKline Pakistan",
}


@st.cache_data(ttl=900, show_spinner=False)
def _enriched_market_news(limit: int = 20) -> list[dict]:
    return analyze_articles(get_market_news(limit))


@st.cache_data(ttl=900, show_spinner=False)
def _enriched_ticker_news(ticker: str, limit: int = 15) -> list[dict]:
    return analyze_articles(get_ticker_news(ticker, limit))


@st.cache_data(ttl=900, show_spinner=False)
def _enriched_psx_market_news(limit: int = 20) -> list[dict]:
    return analyze_articles(get_psx_market_news(limit))


@st.cache_data(ttl=900, show_spinner=False)
def _enriched_psx_company_news(company_name: str, limit: int = 15) -> list[dict]:
    return analyze_articles(get_psx_company_news(company_name, limit))


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return ""


def _impact_badge(sentiment: dict) -> str:
    color = sentiment["impact_color"]
    label = sentiment["impact_label"]
    return (
        f"<span style='"
        f"background:{color}22; color:{color}; border:1px solid {color}55; "
        f"border-radius:6px; padding:3px 10px; font-size:11px; font-weight:700; "
        f"letter-spacing:0.3px;'>{label}</span>"
    )


def _confidence_pill(sentiment: dict) -> str:
    if sentiment["inconclusive"]:
        return "<span style='color:#64748b; font-size:11px;'>Confidence: —</span>"
    pct = sentiment["confidence"] * 100
    color = sentiment["impact_color"]
    return f"<span style='color:{color}; font-size:11px; font-weight:600;'>Confidence: {pct:.0f}%</span>"


def _ticker_tags(symbols: list[str]) -> str:
    if not symbols:
        return ""
    tags = "".join(
        f"<span style='"
        f"background:rgba(245,158,11,0.15); color:#F59E0B; border:1px solid rgba(245,158,11,0.3); "
        f"border-radius:4px; padding:1px 7px; font-size:10px; font-weight:600; margin-right:4px;'>"
        f"{s}</span>"
        for s in symbols[:5]
    )
    return tags


def render_article_card(article: dict):
    sentiment   = article["sentiment"]
    raw_summary = article.get("summary", "")
    source      = article.get("source", "").upper()
    published   = _fmt_date(article.get("published_at", ""))
    symbols     = article.get("symbols", [])
    url         = article.get("url", "")

    # Escape all user-provided text to prevent HTML/Markdown injection
    headline    = _html.escape(article.get("headline", "No headline"))
    summary_esc = _html.escape(raw_summary[:220]) + ("..." if len(raw_summary) > 220 else "")
    source_line = _html.escape(f"{source}  ·  {published}" if published else source)

    badge       = _impact_badge(sentiment)
    conf_pill   = _confidence_pill(sentiment)
    ticker_tags = _ticker_tags(symbols)

    read_more = (
        f"<a href='{_html.escape(url)}' target='_blank' style='"
        f"color:#F59E0B; font-size:12px; text-decoration:none; font-weight:600;'>"
        f"Read Full Article &#8594;</a>"
        if url else ""
    )

    # Build HTML as joined parts — no blank lines between elements so CommonMark
    # never closes the HTML block mid-card and renders the rest as a code block.
    parts = [
        "<div style='background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:16px 20px; margin-bottom:12px;'>",
        f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>{badge}<span style='color:#A1A1AA; font-size:11px;'>{source_line}</span></div>",
        f"<p style='color:#E4E4E7; font-size:15px; font-weight:600; margin:0 0 4px; line-height:1.4;'>{headline}</p>",
    ]
    if raw_summary:
        parts.append(f"<p style='color:#A1A1AA; font-size:13px; margin:8px 0 10px; line-height:1.5;'>{summary_esc}</p>")
    parts.append(
        f"<div style='display:flex; justify-content:space-between; align-items:center; margin-top:6px;'>"
        f"<div>{ticker_tags}</div>"
        f"<div style='display:flex; gap:16px; align-items:center;'>{conf_pill}{read_more}</div>"
        f"</div>"
    )
    parts.append("</div>")

    st.markdown("".join(parts), unsafe_allow_html=True)


def render_sentiment_summary(articles: list[dict]):
    if not articles:
        return
    counts = {"positive": 0, "negative": 0, "neutral": 0, "inconclusive": 0}
    for a in articles:
        s = a["sentiment"]
        if s["inconclusive"]:
            counts["inconclusive"] += 1
        else:
            counts[s["label"]] = counts.get(s["label"], 0) + 1

    total = len(articles)
    pos_pct = (counts["positive"] / total) * 100
    neg_pct = (counts["negative"] / total) * 100
    neu_pct = (counts["neutral"]  / total) * 100
    inc_pct = (counts["inconclusive"] / total) * 100

    # Overall mood
    if counts["positive"] > counts["negative"]:
        mood_label, mood_color = "Broadly Positive", "#22C55E"
    elif counts["negative"] > counts["positive"]:
        mood_label, mood_color = "Broadly Negative", "#EF4444"
    else:
        mood_label, mood_color = "Mixed / Neutral", "#A1A1AA"

    st.markdown(f"""
    <div style='
        background:rgba(255,255,255,0.03);
        border:1px solid rgba(255,255,255,0.07);
        border-radius:12px;
        padding:16px 20px;
        margin-top:20px;
    '>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
            <span style='color:#E4E4E7; font-size:14px; font-weight:600;'>Sentiment Summary</span>
            <span style='background:{mood_color}22; color:{mood_color}; border:1px solid {mood_color}55;
                border-radius:6px; padding:3px 10px; font-size:12px; font-weight:700;'>
                {mood_label}
            </span>
        </div>
        <div style='display:flex; gap:20px; margin-bottom:12px; flex-wrap:wrap;'>
            <span style='color:#22C55E; font-size:13px;'>● Positive: {counts['positive']}</span>
            <span style='color:#EF4444; font-size:13px;'>● Negative: {counts['negative']}</span>
            <span style='color:#A1A1AA; font-size:13px;'>● Neutral: {counts['neutral']}</span>
            <span style='color:#64748b; font-size:13px;'>● Inconclusive: {counts['inconclusive']}</span>
        </div>
        <div style='display:flex; height:8px; border-radius:4px; overflow:hidden;'>
            <div style='width:{pos_pct:.1f}%; background:#22C55E;'></div>
            <div style='width:{neg_pct:.1f}%; background:#EF4444;'></div>
            <div style='width:{neu_pct:.1f}%; background:#A1A1AA;'></div>
            <div style='width:{inc_pct:.1f}%; background:#64748b;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_ppo_confluence(ticker: str, news_sentiment_label: str):
    """Show a confluence notice if PPO results are cached for this ticker."""
    cached_ticker  = st.session_state.get("ppo_ticker", "")
    cached_results = st.session_state.get("ppo_results", {})
    if not cached_ticker or cached_ticker.upper() != ticker.upper():
        return
    if not cached_results or "rec" not in cached_results:
        return

    rec    = cached_results["rec"]
    action = rec.get("action", "HOLD")

    # Check directional alignment
    action_positive = action == "BUY"
    action_negative = action == "SELL"
    news_positive   = news_sentiment_label == "positive"
    news_negative   = news_sentiment_label == "negative"

    aligned = (action_positive and news_positive) or (action_negative and news_negative)

    if aligned:
        ppo_color    = "#22C55E" if action_positive else "#EF4444"
        news_color   = "#22C55E" if news_positive   else "#EF4444"
        st.markdown(f"""
        <div style='
            background:rgba(245,158,11,0.08);
            border:1px solid rgba(245,158,11,0.3);
            border-radius:10px;
            padding:14px 18px;
            margin-top:16px;
        '>
            <span style='color:#F59E0B; font-size:13px; font-weight:700;'>⚡ Confluence Signal</span>
            <p style='color:#E4E4E7; font-size:13px; margin:6px 0 0;'>
                Your PPO agent recommends
                <span style='color:{ppo_color}; font-weight:700;'>{action}</span>
                for <b>{ticker.upper()}</b>, and the latest news sentiment is
                <span style='color:{news_color}; font-weight:700;'>
                    {"Positive" if news_positive else "Negative"}
                </span>.
                Both signals agree — this is a stronger combined indicator.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='
            background:rgba(255,179,0,0.06);
            border:1px solid rgba(255,179,0,0.25);
            border-radius:10px;
            padding:14px 18px;
            margin-top:16px;
        '>
            <span style='color:#FFB300; font-size:13px; font-weight:700;'>⚠ Signal Divergence</span>
            <p style='color:#E4E4E7; font-size:13px; margin:6px 0 0;'>
                Your PPO agent recommends <b>{action}</b> for <b>{ticker.upper()}</b>,
                but the news sentiment points in a different direction.
                Exercise caution — conflicting signals warrant closer review.
            </p>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE HEADER
# ==============================================================================

st.markdown("<div class='custom-title-box'><h1>News & Market Sentiment</h1></div>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#A1A1AA;'>"
    "AI-powered market-impact analysis of financial headlines via FinBERT. "
    "<b>No login required.</b>"
    "</p>",
    unsafe_allow_html=True,
)

# Guest / auth notice
if not is_auth:
    st.info(
        "You are viewing as a guest. "
        "Log in to see PPO confluence signals when viewing asset-specific news.",
        icon="ℹ️"
    )

st.markdown("<br>", unsafe_allow_html=True)

# Warm up FinBERT once — subsequent loads are instant via cache_resource
with st.spinner("Loading AI sentiment model (first run only)..."):
    _load_finbert()

# Refresh button
_hdr_left, _hdr_right = st.columns([6, 1])
with _hdr_right:
    if st.button("⟳ Refresh", use_container_width=True, help="Clear cache and fetch latest headlines"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)


# ==============================================================================
# OUTER TABS — US Market / PSX Market
# ==============================================================================

outer_us, outer_psx = st.tabs(["US Market", "PSX Market"])


# ══════════════════════════════════════════════════════════════════════════════
# US MARKET
# ══════════════════════════════════════════════════════════════════════════════
with outer_us:

    tab_market, tab_asset = st.tabs(["Global Market News", "Asset-Specific News"])

    # ── Global Market News ────────────────────────────────────────────────────
    with tab_market:
        st.markdown(
            "<p style='color:#A1A1AA; font-size:13px;'>"
            "Latest financial headlines from global markets, analyzed for potential market impact."
            "</p>",
            unsafe_allow_html=True,
        )

        _limit_col, _ = st.columns([2, 5])
        with _limit_col:
            article_limit = st.slider("Number of articles", 5, 50, 20, step=5, key="market_limit")

        with st.spinner("Fetching and analyzing market news..."):
            market_articles = _enriched_market_news(article_limit)

        if not market_articles:
            st.warning(
                "No market news available. Check your Alpaca API credentials in `.env`.",
                icon="⚠️"
            )
        else:
            st.markdown(
                f"<p style='color:#A1A1AA; font-size:12px;'>Showing {len(market_articles)} articles</p>",
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2, gap="medium")
            for i, article in enumerate(market_articles):
                with (col_a if i % 2 == 0 else col_b):
                    render_article_card(article)
            render_sentiment_summary(market_articles)

    # ── Asset-Specific News ───────────────────────────────────────────────────
    with tab_asset:
        st.markdown(
            "<p style='color:#A1A1AA; font-size:13px;'>"
            "Enter a ticker to see recent news and its predicted impact on that asset."
            "</p>",
            unsafe_allow_html=True,
        )

        t_col1, t_col2, _ = st.columns([2, 2, 3])
        with t_col1:
            ticker_input = st.text_input(
                "Ticker Symbol", placeholder="e.g. AAPL", key="news_ticker",
            ).strip().upper()
        with t_col2:
            asset_limit = st.slider("Number of articles", 5, 50, 15, step=5, key="asset_limit")

        if ticker_input:
            with st.spinner(f"Fetching and analyzing news for {ticker_input}..."):
                ticker_articles = _enriched_ticker_news(ticker_input, asset_limit)

            if not ticker_articles:
                st.warning(
                    f"No news found for **{ticker_input}**. "
                    "Check the ticker is valid, or try a more actively covered symbol.",
                    icon="⚠️"
                )
            else:
                if is_auth:
                    dominant_label = max(
                        ["positive", "negative", "neutral"],
                        key=lambda l: sum(
                            1 for a in ticker_articles
                            if not a["sentiment"]["inconclusive"] and a["sentiment"]["label"] == l
                        )
                    )
                    render_ppo_confluence(ticker_input, dominant_label)

                st.markdown(
                    f"<p style='color:#A1A1AA; font-size:12px; margin-top:12px;'>"
                    f"Showing {len(ticker_articles)} articles for <b style='color:#E4E4E7;'>{ticker_input}</b>"
                    f"</p>",
                    unsafe_allow_html=True,
                )
                col_a, col_b = st.columns(2, gap="medium")
                for i, article in enumerate(ticker_articles):
                    with (col_a if i % 2 == 0 else col_b):
                        render_article_card(article)
                render_sentiment_summary(ticker_articles)
        else:
            st.markdown("""
            <div style='background:rgba(255,255,255,0.03);border:1px dashed rgba(255,255,255,0.12);
                border-radius:12px;padding:40px;text-align:center;margin-top:12px;'>
                <p style='color:#A1A1AA;font-size:14px;margin:0;'>
                    Enter a ticker symbol above to load asset-specific news and sentiment analysis.
                </p>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PSX MARKET
# ══════════════════════════════════════════════════════════════════════════════
with outer_psx:

    tab_psx_market, tab_psx_asset = st.tabs(["General Market News", "Stock-Specific News"])

    # ── PSX General Market News ───────────────────────────────────────────────
    with tab_psx_market:
        st.markdown(
            "<p style='color:#A1A1AA; font-size:13px;'>"
            "Latest Pakistan Stock Exchange and KSE-100 headlines, analyzed for market impact."
            "</p>",
            unsafe_allow_html=True,
        )

        _psx_limit_col, _ = st.columns([2, 5])
        with _psx_limit_col:
            psx_market_limit = st.slider("Number of articles", 5, 30, 15, step=5, key="psx_market_limit")

        with st.spinner("Fetching and analyzing PSX market news..."):
            psx_market_articles = _enriched_psx_market_news(psx_market_limit)

        if not psx_market_articles:
            st.warning(
                "No PSX market news could be retrieved. "
                "Ensure `feedparser` is installed (`pip install feedparser`) and you have internet access.",
                icon="⚠️"
            )
        else:
            st.markdown(
                f"<p style='color:#A1A1AA; font-size:12px;'>Showing {len(psx_market_articles)} articles "
                f"· Sourced via Google News RSS</p>",
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2, gap="medium")
            for i, article in enumerate(psx_market_articles):
                with (col_a if i % 2 == 0 else col_b):
                    render_article_card(article)
            render_sentiment_summary(psx_market_articles)

    # ── PSX Stock-Specific News ───────────────────────────────────────────────
    with tab_psx_asset:
        st.markdown(
            "<p style='color:#A1A1AA; font-size:13px;'>"
            "Enter a PSX ticker symbol or company name to load news and sentiment analysis."
            "</p>",
            unsafe_allow_html=True,
        )

        p_col1, p_col2, _ = st.columns([2, 2, 3])
        with p_col1:
            psx_search_input = st.text_input(
                "PSX Symbol or Company Name",
                placeholder="e.g. HBL, ENGRO, Lucky Cement",
                key="psx_news_search",
            ).strip()
        with p_col2:
            psx_asset_limit = st.slider("Number of articles", 5, 30, 15, step=5, key="psx_asset_limit")

        # Resolve: known symbol → full company name, otherwise use input directly
        psx_sym_upper = psx_search_input.upper()
        if psx_sym_upper in PSX_STOCKS:
            company_name  = PSX_STOCKS[psx_sym_upper]
            display_label = f"{psx_sym_upper} — {company_name}"
        else:
            company_name  = psx_search_input
            display_label = psx_search_input

        if not psx_search_input:
            st.markdown("""
            <div style='background:rgba(255,255,255,0.03);border:1px dashed rgba(255,255,255,0.12);
                border-radius:12px;padding:40px;text-align:center;margin-top:12px;'>
                <p style='color:#A1A1AA;font-size:14px;margin:0;'>
                    Enter a PSX ticker or company name above to load stock-specific news.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.spinner(f"Fetching and analyzing news for {display_label}..."):
                psx_company_articles = _enriched_psx_company_news(company_name, psx_asset_limit)

            if not psx_company_articles:
                st.warning(
                    f"No news found for **{display_label}**. "
                    "Try a different symbol or company name.",
                    icon="⚠️"
                )
            else:
                st.markdown(
                    f"<p style='color:#A1A1AA; font-size:12px; margin-top:12px;'>"
                    f"Showing {len(psx_company_articles)} articles for "
                    f"<b style='color:#E4E4E7;'>{display_label}</b>"
                    f"</p>",
                    unsafe_allow_html=True,
                )
                col_a, col_b = st.columns(2, gap="medium")
                for i, article in enumerate(psx_company_articles):
                    with (col_a if i % 2 == 0 else col_b):
                        render_article_card(article)
                render_sentiment_summary(psx_company_articles)


# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<p style='color:#A1A1AA; font-size:12px;'>
US news sourced from <b>Alpaca Markets</b> (Benzinga feed, 15-min delayed).
PSX news sourced from <b>Google News RSS</b>.
Sentiment analysis powered by <b>FinBERT</b> (ProsusAI), a transformer model trained on financial text.
</p>
""", unsafe_allow_html=True)

modules.utils.render_footer()
