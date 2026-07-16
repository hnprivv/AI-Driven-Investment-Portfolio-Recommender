import os
import re
import html as _html_mod
import datetime
import requests
import streamlit as st
from dotenv import load_dotenv
from email.utils import parsedate_to_datetime

load_dotenv()

_ALPACA_NEWS_URL = "https://data.alpaca.markets/v1beta1/news"


def _alpaca_headers() -> dict | None:
    key    = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        return None
    return {
        "APCA-API-KEY-ID":     key,
        "APCA-API-SECRET-KEY": secret,
        "accept":              "application/json",
    }


def _parse_articles(raw: list) -> list[dict]:
    articles = []
    for a in raw:
        images     = a.get("images") or []
        image_url  = images[0].get("url", "") if images else ""
        published  = a.get("created_at", "")
        articles.append({
            "id":           a.get("id"),
            "headline":     a.get("headline", ""),
            "summary":      a.get("summary", ""),
            "author":       a.get("author", ""),
            "source":       a.get("source", ""),
            "url":          a.get("url", ""),
            "published_at": published,
            "symbols":      a.get("symbols", []),
            "image_url":    image_url,
        })
    return articles


@st.cache_data(ttl=900, show_spinner=False)
def get_market_news(limit: int = 20) -> list[dict]:
    """Fetch general market-wide news headlines from Alpaca."""
    headers = _alpaca_headers()
    if headers is None:
        return []
    params = {
        "limit":           min(limit, 50),
        "sort":            "desc",
        "include_content": "false",
    }
    try:
        resp = requests.get(_ALPACA_NEWS_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return _parse_articles(resp.json().get("news", []))
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def get_ticker_news(ticker: str, limit: int = 15) -> list[dict]:
    """Fetch news articles tagged to a specific ticker from Alpaca."""
    headers = _alpaca_headers()
    if headers is None:
        return []
    params = {
        "symbols":         ticker.upper().strip(),
        "limit":           min(limit, 50),
        "sort":            "desc",
        "include_content": "false",
    }
    try:
        resp = requests.get(_ALPACA_NEWS_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return _parse_articles(resp.json().get("news", []))
    except Exception:
        return []


# ==============================================================================
# PSX NEWS  (Google News RSS — no API key required)
# ==============================================================================

_GNEWS_BASE = "https://news.google.com/rss/search"

def _parse_gnews_feed(feed_url: str, limit: int) -> list[dict]:
    """Parse a Google News RSS feed URL into the standard article dict format."""
    try:
        import feedparser
    except ImportError:
        return []

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return []

    articles = []
    for entry in feed.entries[:limit]:
        # Convert RFC 2822 date to ISO format so _fmt_date on the page works
        published_at = ""
        try:
            published_at = parsedate_to_datetime(entry.get("published", "")).isoformat()
        except Exception:
            published_at = entry.get("published", "")

        # Strip HTML tags, unescape entities, collapse whitespace
        headline_text = entry.get("title", "")
        raw_summary = re.sub(r"<[^>]+>", " ", entry.get("summary", ""))
        raw_summary = _html_mod.unescape(raw_summary)
        raw_summary = re.sub(r"\s+", " ", raw_summary).strip()
        # Suppress summary when it is a near-duplicate of the headline
        if raw_summary.lower().startswith(headline_text[:50].lower()):
            raw_summary = ""

        # Source title lives in entry.source.title when present
        source = ""
        try:
            source = entry.source.title
        except AttributeError:
            pass

        articles.append({
            "id":           entry.get("id", ""),
            "headline":     entry.get("title", ""),
            "summary":      raw_summary,
            "author":       "",
            "source":       source,
            "url":          entry.get("link", ""),
            "published_at": published_at,
            "symbols":      [],
            "image_url":    "",
        })

    return articles


@st.cache_data(ttl=900, show_spinner=False)
def get_psx_market_news(limit: int = 20) -> list[dict]:
    """Fetch general PSX / KSE-100 market news from Google News RSS."""
    url = f"{_GNEWS_BASE}?q=Pakistan+Stock+Exchange+KSE-100&hl=en&gl=PK&ceid=PK:en"
    return _parse_gnews_feed(url, limit)


@st.cache_data(ttl=900, show_spinner=False)
def get_psx_company_news(company_name: str, limit: int = 15) -> list[dict]:
    """Fetch company-specific PSX news from Google News RSS by company name."""
    query = company_name.strip().replace(" ", "+") + "+Pakistan+stock"
    url   = f"{_GNEWS_BASE}?q={query}&hl=en&gl=PK&ceid=PK:en"
    return _parse_gnews_feed(url, limit)
