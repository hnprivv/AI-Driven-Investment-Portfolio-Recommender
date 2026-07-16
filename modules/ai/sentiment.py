import streamlit as st

_CONFIDENCE_THRESHOLD = 0.60

_IMPACT = {
    "positive": ("Likely Positive Market Impact", "#22C55E"),
    "negative": ("Likely Negative Market Impact", "#EF4444"),
    "neutral":  ("Neutral / No Clear Market Impact", "#A1A1AA"),
}

# ProsusAI/finbert id2label: 0=positive, 1=negative, 2=neutral
_LABELS = ["positive", "negative", "neutral"]


@st.cache_resource(show_spinner=False)
def _load_finbert():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    model     = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    model.eval()
    return tokenizer, model


def _inconclusive(probs: dict | None = None) -> dict:
    return {
        "label":         "neutral",
        "confidence":    0.0,
        "probabilities": probs or {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
        "impact_label":  "Inconclusive",
        "impact_color":  "#64748b",
        "inconclusive":  True,
    }


def analyze_sentiment(text: str) -> dict:
    """
    Run FinBERT on a headline/summary string and return market-impact sentiment.
    Uses AutoModel directly to avoid torchvision dependency triggered by pipeline API.
    """
    if not text or not text.strip():
        return _inconclusive()
    try:
        import torch
        import torch.nn.functional as F

        tokenizer, model = _load_finbert()
        inputs = tokenizer(
            text[:1000],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = model(**inputs).logits
        probs      = F.softmax(logits, dim=-1)[0]
        prob_dict  = {_LABELS[i]: probs[i].item() for i in range(len(_LABELS))}
        best_idx   = int(probs.argmax())
        label      = _LABELS[best_idx]
        confidence = probs[best_idx].item()
        if confidence < _CONFIDENCE_THRESHOLD:
            return _inconclusive(prob_dict)
        impact_label, impact_color = _IMPACT.get(label, ("Neutral", "#A1A1AA"))
        return {
            "label":         label,
            "confidence":    confidence,
            "probabilities": prob_dict,
            "impact_label":  impact_label,
            "impact_color":  impact_color,
            "inconclusive":  False,
        }
    except Exception:
        return _inconclusive()


def analyze_articles(articles: list[dict]) -> list[dict]:
    """Enrich each article dict with a 'sentiment' key."""
    enriched = []
    for article in articles:
        text = article.get("headline", "") + ". " + article.get("summary", "")
        enriched.append({**article, "sentiment": analyze_sentiment(text)})
    return enriched
