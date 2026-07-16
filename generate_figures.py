"""
AIPRS — Complete Figure Generation Script
==========================================
Run this from the root of your AIPRS_Dashboard directory:

    python generate_figures.py

Requirements (all already in requirements.txt):
    pip install yfinance scikit-learn matplotlib seaborn pandas numpy torch joblib

All figures are saved to: ./paper_figures/
Estimated runtime: 3–6 minutes (depends on Yahoo Finance download speed).
"""

import os
import sys
import json
import pickle
import warnings
import time

warnings.filterwarnings("ignore")

# ── Make sure AIPRS modules are importable ────────────────────────────────────
ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
import torch
import joblib
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    confusion_matrix,
    classification_report,
)

from modules.ai.ppo_agent import ActorCritic
from modules.ai.feature_eng import (
    compute_features,
    FeatureNormalizer,
    encode_user_profile,
    FEATURE_NAMES,
)

# ── Output directory ──────────────────────────────────────────────────────────
OUT = os.path.join(ROOT, "paper_figures")
os.makedirs(OUT, exist_ok=True)
print(f"Figures will be saved to: {OUT}\n")

# ── Colour palette ────────────────────────────────────────────────────────────
CLUSTER_COLORS = ["#2563EB", "#10B981", "#F59E0B", "#DC2626"]
CLUSTER_LABELS = {
    0: "Conservative",
    1: "Moderate",
    2: "Aggressive",
    3: "Very Aggressive",
}
NAVY  = "#1E3A5F"
AMBER = "#D97706"
GREEN = "#10B981"
RED   = "#EF4444"
GRAY  = "#6B7280"
BENCHMARK_COLOR = "#374151"

plt.rcParams.update({
    "font.family":        "serif",
    "font.size":          10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "figure.dpi":         150,
})

# ── Ticker universes ──────────────────────────────────────────────────────────
US_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "JPM",  "SPY",  "QQQ", "GLD",
]

PSX_TICKERS = [
    "HBL.KA", "ENGRO.KA", "LUCK.KA", "MCB.KA",  "PPL.KA",
    "OGDC.KA","UBL.KA",   "FFC.KA",  "EFERT.KA", "MARI.KA",
]

# Portfolio asset-class proxies (real ETFs)
PORTFOLIO_ETFS = {
    "US Equities":  "VTI",   # Vanguard Total Stock Market ETF
    "Fixed Income": "BND",   # Vanguard Total Bond Market ETF
    "Commodities":  "DJP",   # iPath Bloomberg Commodity Index
    "Cash":         "SHY",   # iShares 1-3 Year Treasury Bond ETF
    "Benchmark (SPY)": "SPY",
}

ALLOCATIONS = {
    "Conservative":    {"US Equities": 0.40, "Fixed Income": 0.40, "Commodities": 0.10, "Cash": 0.10},
    "Moderate":        {"US Equities": 0.60, "Fixed Income": 0.25, "Commodities": 0.10, "Cash": 0.05},
    "Aggressive":      {"US Equities": 0.75, "Fixed Income": 0.15, "Commodities": 0.07, "Cash": 0.03},
    "Very Aggressive": {"US Equities": 0.90, "Fixed Income": 0.05, "Commodities": 0.03, "Cash": 0.02},
}

# ── Model paths ───────────────────────────────────────────────────────────────
MODEL_DIR     = os.path.join(ROOT, "modules", "model")
KMEANS_PATH   = os.path.join(MODEL_DIR, "kmeans_model.pkl")
SCALER_PATH   = os.path.join(MODEL_DIR, "scaler.pkl")
PPO_US_DIR    = os.path.join(MODEL_DIR, "ppo")
PPO_PSX_DIR   = os.path.join(MODEL_DIR, "ppo_psx")
PROFILE_CSV   = os.path.join(ROOT, "data", "user_profile.csv")
TRAINING_LOG  = os.path.join(PPO_PSX_DIR, "training_log.json")

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save(fname):
    path = os.path.join(OUT, fname)
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  Saved -> {fname}")


def load_agent(model_dir):
    cfg_path  = os.path.join(model_dir, "ppo_config.json")
    act_path  = os.path.join(model_dir, "ppo_actor.pt")
    norm_path = os.path.join(model_dir, "normalizer.pkl")
    with open(cfg_path) as f:
        cfg = json.load(f)
    ac = ActorCritic(cfg["obs_dim"], cfg["n_actions"], cfg["hidden"])
    sd = torch.load(act_path, map_location="cpu")
    ac.load_state_dict(sd)
    ac.eval()
    norm = FeatureNormalizer.load(norm_path)
    return ac, norm


def fetch_ohlcv(ticker, period="5y", retries=3):
    """Download daily OHLCV bars from Yahoo Finance. Returns None on failure."""
    for attempt in range(retries):
        try:
            raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            if raw.empty:
                return None
            # Flatten MultiIndex if present
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0].lower() for c in raw.columns]
            else:
                raw.columns = [c.lower() for c in raw.columns]
            df = raw[["open", "high", "low", "close", "volume"]].dropna()
            if len(df) < 100:
                return None
            return df
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"    Warning: could not download {ticker} — {e}")
                return None


def prep_profile_data(df_prof):
    """Encode categorical profile fields for clustering."""
    income_map  = {"Less than 25,000": 1, "25,000 - 50,000": 2,
                   "50,000 - 100,000": 3, "100,000+": 4}
    horizon_map = {"< 1 Year": 1, "1 Year": 1, "1-3 Years": 2,
                   "3-5 Years": 3, "5-10 Years": 4, "10+ Years": 5}
    exp_map     = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
    df = df_prof.copy()
    df["income_num"]  = df["Income Range"].map(income_map).fillna(2)
    df["horizon_num"] = df["Investment Horizon"].map(horizon_map).fillna(3)
    df["exp_num"]     = df["Experience"].map(exp_map).fillna(1)
    cols = ["Age", "income_num", "Risk Tolerance", "horizon_num", "exp_num"]
    return df[cols].values.astype(float)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD MODELS + PROFILE DATA
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("Loading models ...")
km    = joblib.load(KMEANS_PATH)
sc    = joblib.load(SCALER_PATH)
ac_us, norm_us   = load_agent(PPO_US_DIR)
ac_psx, norm_psx = load_agent(PPO_PSX_DIR)
print("  K-Means, US PPO, PSX PPO loaded.")

df_prof  = pd.read_csv(PROFILE_CSV)
X_raw    = prep_profile_data(df_prof)
X_scaled = sc.transform(X_raw)
labels   = km.predict(X_scaled)

with open(TRAINING_LOG) as f:
    training_log = json.load(f)

# Default profile for agent evaluation (Moderate investor)
EVAL_PROFILE = {
    "risk_tolerance":    5,
    "cluster":           1,
    "investment_horizon":"3-5 Years",
    "experience":        "Intermediate",
    "age":               35,
}
USER_VEC = encode_user_profile(EVAL_PROFILE)

# ─────────────────────────────────────────────────────────────────────────────
# FIG 1 — ELBOW CURVE + SILHOUETTE
# ─────────────────────────────────────────────────────────────────────────────

print("\n[Fig 1] Elbow curve + Silhouette ...")
sil = silhouette_score(X_scaled, labels)
dbi = davies_bouldin_score(X_scaled, labels)

# k limited by n_samples - 1
max_k = min(8, len(X_scaled) - 1)
inertias, sil_scores, k_vals = [], [], []
for k in range(2, max_k + 1):
    km_t = KMeans(n_clusters=k, random_state=42, n_init=20).fit(X_scaled)
    inertias.append(km_t.inertia_)
    sil_scores.append(silhouette_score(X_scaled, km_t.labels_))
    k_vals.append(k)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
fig.suptitle("K-Means Model Selection", fontsize=13, fontweight="bold")

ax1.plot(k_vals, inertias, "o-", color=NAVY, lw=2.2, ms=8,
         markerfacecolor="white", markeredgewidth=2)
ax1.axvline(4, color=AMBER, ls="--", lw=2, label="Selected k = 4")
ax1.fill_between(k_vals, inertias, min(inertias) * 0.95, alpha=0.06, color=NAVY)
ax1.set_xlabel("Number of clusters (k)"); ax1.set_ylabel("Inertia (Within-Cluster SSE)")
ax1.set_title("(a) Elbow Curve", fontweight="bold")
ax1.legend(); ax1.grid(True, alpha=0.25); ax1.set_xticks(k_vals)

ax2.plot(k_vals, sil_scores, "s-", color=GREEN, lw=2.2, ms=8,
         markerfacecolor="white", markeredgewidth=2)
ax2.axvline(4, color=AMBER, ls="--", lw=2, label="Selected k = 4")
ax2.axhline(sil, color=RED, ls=":", lw=1.5, label=f"Actual silhouette = {sil:.3f}")
ax2.set_xlabel("Number of clusters (k)"); ax2.set_ylabel("Silhouette Score")
ax2.set_title("(b) Silhouette Score vs k", fontweight="bold")
ax2.legend(); ax2.grid(True, alpha=0.25); ax2.set_xticks(k_vals)

plt.tight_layout(); save("fig1_elbow.png")
print(f"  Silhouette = {sil:.4f}   Davies-Bouldin = {dbi:.4f}   Inertia(k=4) = {km.inertia_:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 2 — PCA SCATTER
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 2] PCA scatter ...")
pca  = PCA(n_components=2)
X2d  = pca.fit_transform(X_scaled)
ev   = pca.explained_variance_ratio_

fig, ax = plt.subplots(figsize=(7, 5.5))
for cl in sorted(set(labels)):
    idx = labels == cl
    ax.scatter(X2d[idx, 0], X2d[idx, 1], c=CLUSTER_COLORS[cl],
               label=CLUSTER_LABELS[cl], s=150, edgecolors="white", lw=1.5, zorder=3)
cents = pca.transform(km.cluster_centers_)
ax.scatter(cents[:, 0], cents[:, 1], c="black", marker="X", s=260, zorder=5,
           label="Centroids", edgecolors="white", lw=1.2)
ax.set_xlabel(f"PC1 ({ev[0]*100:.1f}% variance explained)")
ax.set_ylabel(f"PC2 ({ev[1]*100:.1f}% variance explained)")
ax.set_title("Cluster Separation — PCA 2-D Projection", fontweight="bold")
ax.legend(fontsize=9, framealpha=0.9); ax.grid(True, alpha=0.22); ax.set_facecolor("#F9FAFB")
ax.text(0.02, 0.97,
        f"Silhouette = {sil:.3f}\nDavies-Bouldin = {dbi:.3f}",
        transform=ax.transAxes, fontsize=9, va="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85))
plt.tight_layout(); save("fig2_pca.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 3 — CENTROID RADAR CHART
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 3] Centroid radar ...")
categories = ["Age", "Income", "Risk\nTolerance", "Horizon", "Experience"]
N = len(categories)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]

fig, ax = plt.subplots(figsize=(7, 8), subplot_kw=dict(polar=True))
for i, col in enumerate(CLUSTER_COLORS):
    c    = km.cluster_centers_[i]
    vals = list(c) + [c[0]]
    ax.plot(angles, vals, "o-", lw=2.2, color=col, label=CLUSTER_LABELS[i])
    ax.fill(angles, vals, alpha=0.09, color=col)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, size=10.5)
ax.set_title("Cluster Centroid Profiles\n(Normalised Feature Space)",
             size=11, fontweight="bold", pad=22)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=10)
plt.tight_layout(); save("fig3_radar.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 4 — PPO TRAINING CURVES (real training_log.json)
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 4] Training curves (real PSX log) ...")
steps     = [e["step"] / 1e6 for e in training_log]
train_ret = [e["train_return"]  for e in training_log]
eval_ret  = [e["eval_return"]   for e in training_log]
pol_loss  = [e["policy_loss"]   for e in training_log]
val_loss  = [e["value_loss"]    for e in training_log]
entropy   = [e["entropy"]       for e in training_log]

fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
fig.suptitle("PSX PPO Agent — Training Metrics (3M Steps, 15 Checkpoints)",
             fontsize=12, fontweight="bold")

ax = axes[0, 0]
ax.plot(steps, train_ret, "o-", color=AMBER, lw=2, ms=6, label="Train return")
ax.plot(steps, eval_ret,  "s-", color=NAVY,  lw=2, ms=6, label="Eval return")
ax.axhline(0, color=GRAY, ls="--", lw=1.2, alpha=0.6)
ax.fill_between(steps, train_ret, 0, alpha=0.08, color=AMBER)
ax.fill_between(steps, eval_ret,  0, alpha=0.08, color=NAVY)
ax.set_xlabel("Training Steps (millions)"); ax.set_ylabel("Episode Return")
ax.set_title("(a) Train vs Evaluation Return", fontweight="bold")
ax.legend(fontsize=9); ax.grid(True, alpha=0.22)

ax = axes[0, 1]
ax.plot(steps, entropy, "D-", color=GREEN, lw=2, ms=6)
ax.axhline(np.log(3), color=GRAY, ls="--", lw=1.2, alpha=0.6, label="Max entropy (uniform)")
ax.fill_between(steps, entropy, min(entropy) * 0.95, alpha=0.1, color=GREEN)
ax.set_xlabel("Training Steps (millions)"); ax.set_ylabel("Policy Entropy (nats)")
ax.set_title("(b) Policy Entropy", fontweight="bold")
ax.legend(fontsize=9); ax.grid(True, alpha=0.22)

ax = axes[1, 0]
ax.plot(steps, pol_loss, "^-", color=RED, lw=2, ms=6)
ax.axhline(0, color=GRAY, ls="--", lw=1.2, alpha=0.6)
ax.set_xlabel("Training Steps (millions)"); ax.set_ylabel("Policy Loss")
ax.set_title("(c) Policy Loss (PPO-Clip Objective)", fontweight="bold")
ax.grid(True, alpha=0.22)

ax = axes[1, 1]
ax.plot(steps, val_loss, "o-", color="#8B5CF6", lw=2, ms=6)
ax.set_xlabel("Training Steps (millions)"); ax.set_ylabel("Value Loss (MSE)")
ax.set_title("(d) Critic Value Loss", fontweight="bold")
ax.grid(True, alpha=0.22)

plt.tight_layout(); save("fig4_training_curves.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 5 — CORRECTED BINARY REWARD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 5] Reward function (corrected binary) ...")
fig, ax = plt.subplots(figsize=(9, 5.5))
x_ret = np.linspace(-0.05, 0.05, 2000)

for risk, label, col, ls in [
    (0.0, "Conservative (risk=0.0)",    NAVY,  "-"),
    (0.5, "Moderate (risk=0.5)",         AMBER, "--"),
    (1.0, "Very Aggressive (risk=1.0)", RED,   ":"),
]:
    scale = 0.5 + 0.5 * risk
    buy  = np.where(x_ret > 0,  +0.02 * scale, -0.02 * scale)
    sell = np.where(x_ret < 0,  +0.02 * scale, -0.02 * scale)
    ax.plot(x_ret * 100, buy,  lw=2.0, color=col, ls=ls, label=f"BUY — {label}")
    ax.plot(x_ret * 100, sell, lw=2.0, color=col, ls=ls, alpha=0.38)

ax.axhline(0, color=GRAY, lw=1.2, label="HOLD (reward = 0)")
ax.axvline(0, color=GRAY, lw=0.8, ls="--", alpha=0.5)
ax.fill_betweenx([-0.025, 0.025],  0, 5,  alpha=0.04, color=GREEN)
ax.fill_betweenx([-0.025, 0.025], -5, 0,  alpha=0.04, color=RED)
ax.text( 2.2,  0.016, "Correct\ndirection", fontsize=8, color=GREEN, ha="center")
ax.text(-2.2,  0.016, "Wrong\ndirection",   fontsize=8, color=RED,   ha="center")
ax.set_xlabel("1-Bar Forward Return (%)"); ax.set_ylabel("Reward Signal")
ax.set_title(
    "Risk-Adaptive Binary Reward Function\n"
    "(BUY solid, SELL faded; reward = ±0.02 × scale, independent of return magnitude)",
    fontweight="bold")
ax.text(0.98, 0.03,
        "scale = 0.5 + 0.5 × risk_scaled\n"
        "reward(BUY)  = +0.02×scale  if r_t > 0  else  −0.02×scale\n"
        "reward(SELL) = +0.02×scale  if r_t < 0  else  −0.02×scale\n"
        "reward(HOLD) = 0\n"
        "(churn penalty: −0.005 on non-HOLD action switch)",
        transform=ax.transAxes, fontsize=8.2, va="bottom", ha="right",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#FFFBEB", alpha=0.92))
ax.legend(fontsize=8.5, loc="upper left"); ax.grid(True, alpha=0.22)
plt.tight_layout(); save("fig5_reward_fn.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 6 — RISK-ADAPTIVE CONFIDENCE THRESHOLD
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 6] Confidence threshold ...")
rs     = np.linspace(0, 1, 400)
thresh = 0.35 + 0.15 * (1 - rs)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(rs, thresh, lw=2.5, color=NAVY)
ax.fill_between(rs, thresh, 0.35, alpha=0.1, color=NAVY)

cluster_rs   = [0.1, 0.4, 0.7, 0.95]
cluster_labs = ["Conservative\n(k=0)", "Moderate\n(k=1)",
                "Aggressive\n(k=2)", "Very Aggressive\n(k=3)"]
for rs_v, lab, col in zip(cluster_rs, cluster_labs, CLUSTER_COLORS):
    t = 0.35 + 0.15 * (1 - rs_v)
    ax.scatter([rs_v], [t], color=col, s=120, zorder=5,
               edgecolors="white", lw=1.5)
    ax.annotate(f"{lab}\n→ {t:.2f}", (rs_v, t),
                textcoords="offset points", xytext=(0, 14),
                ha="center", fontsize=8, color=col, fontweight="bold")

ax.axhline(0.35, color=GRAY, ls=":", lw=1.5, label="Min threshold (0.35)")
ax.axhline(0.50, color=GRAY, ls=":", lw=1.5, label="Max threshold (0.50)")
ax.set_xlabel("risk_scaled  (0 = most conservative → 1 = most aggressive)")
ax.set_ylabel("Minimum Confidence Threshold")
ax.set_title(
    "Risk-Adaptive PPO Confidence Threshold\n"
    "threshold = 0.35 + 0.15 × (1 − risk_scaled)",
    fontweight="bold")
ax.set_ylim(0.30, 0.58); ax.set_xlim(-0.02, 1.02)
ax.legend(fontsize=9); ax.grid(True, alpha=0.22)
plt.tight_layout(); save("fig6_threshold.png")

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD PRICE DATA (used by Figs 7–12)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Downloading price data from Yahoo Finance ...")

us_data, psx_data = {}, {}

print("  US tickers:")
for t in US_TICKERS:
    df = fetch_ohlcv(t, period="5y")
    if df is not None:
        us_data[t] = df
        print(f"    {t}: {len(df)} bars")
    else:
        print(f"    {t}: SKIPPED (no data)")

print("  PSX tickers:")
for t in PSX_TICKERS:
    df = fetch_ohlcv(t, period="5y")
    if df is not None:
        psx_data[t] = df
        print(f"    {t}: {len(df)} bars")
    else:
        print(f"    {t}: SKIPPED (no data)")

print("  Portfolio ETFs:")
etf_data = {}
for name, ticker in PORTFOLIO_ETFS.items():
    df = fetch_ohlcv(ticker, period="5y")
    if df is not None:
        etf_data[name] = df
        print(f"    {ticker} ({name}): {len(df)} bars")
    else:
        print(f"    {ticker} ({name}): SKIPPED")

# ─────────────────────────────────────────────────────────────────────────────
# AGENT EVALUATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_agent(ac, norm, price_data_dict, test_frac=0.33):
    """
    Run PPO agent on real price data (held-out test split) and return
    raw predictions vs ground-truth direction labels.

    Ground truth:
        BUY  if next-bar simple return > +0.5%
        SELL if next-bar simple return < -0.5%
        HOLD otherwise
    """
    all_preds, all_actuals = [], []
    for ticker, df in price_data_dict.items():
        feat = compute_features(df)
        feat = feat.dropna()
        if len(feat) < 80:
            continue
        nm    = norm.transform(feat)
        close = df["close"].reindex(feat.index).values
        split = int(len(nm) * (1 - test_frac))
        tm    = nm[split:]
        tc    = close[split:]
        for j in range(len(tm) - 1):
            state = np.concatenate([tm[j], USER_VEC]).astype(np.float32)
            with torch.no_grad():
                logits, _ = ac(torch.from_numpy(state).unsqueeze(0))
                probs = torch.softmax(logits, dim=-1).squeeze(0).numpy()
            pred = int(np.argmax(probs))
            ret  = tc[j + 1] / tc[j] - 1
            true = 1 if ret > 0.005 else (2 if ret < -0.005 else 0)
            all_preds.append(pred)
            all_actuals.append(true)
    return all_preds, all_actuals


def plot_confusion_pair(preds, actuals, title, fname):
    labels = ["HOLD", "BUY", "SELL"]
    cm     = confusion_matrix(actuals, preds, labels=[0, 1, 2])
    cm_n   = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-10)
    report = classification_report(actuals, preds, target_names=labels, output_dict=True)
    acc    = report["accuracy"]
    macro  = report["macro avg"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.suptitle(title, fontsize=11, fontweight="bold")

    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax1,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, linecolor="white", cbar=True,
                annot_kws={"size": 13, "weight": "bold"})
    ax1.set_xlabel("Predicted Signal"); ax1.set_ylabel("True Direction")
    ax1.set_title("(a) Raw Counts", fontweight="bold")

    sns.heatmap(cm_n, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax2,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, linecolor="white", cbar=True,
                vmin=0, vmax=1, annot_kws={"size": 13})
    ax2.set_xlabel("Predicted Signal"); ax2.set_ylabel("True Direction")
    ax2.set_title("(b) Row-Normalised (Recall per Class)", fontweight="bold")

    txt = (f"n = {len(preds)}\n"
           f"Accuracy  = {acc:.3f}\n"
           f"Macro F1  = {macro['f1-score']:.3f}\n"
           f"Macro Prec = {macro['precision']:.3f}\n"
           f"Macro Rec  = {macro['recall']:.3f}")
    ax2.text(1.18, 0.98, txt, transform=ax2.transAxes, fontsize=8.5, va="top",
             bbox=dict(boxstyle="round,pad=0.45", facecolor="#EFF6FF", alpha=0.9))

    plt.tight_layout()
    save(fname)
    return report


# ─────────────────────────────────────────────────────────────────────────────
# FIG 7 — US CONFUSION MATRIX
# ─────────────────────────────────────────────────────────────────────────────

print("\n[Fig 7] US PPO confusion matrix ...")
if us_data:
    preds_us, actual_us = evaluate_agent(ac_us, norm_us, us_data)
    print(f"  Test steps: {len(preds_us)}")
    rep_us = plot_confusion_pair(
        preds_us, actual_us,
        f"PPO Advisory Agent — Confusion Matrix (US Equities, {len(us_data)} Tickers, 33% Test Split)",
        "fig7_cm_us.png",
    )
    print(classification_report(actual_us, preds_us, target_names=["HOLD","BUY","SELL"], digits=3))
else:
    print("  SKIPPED — no US data downloaded.")
    rep_us = None

# ─────────────────────────────────────────────────────────────────────────────
# FIG 8 — PSX CONFUSION MATRIX
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 8] PSX PPO confusion matrix ...")
if psx_data:
    preds_psx, actual_psx = evaluate_agent(ac_psx, norm_psx, psx_data)
    print(f"  Test steps: {len(preds_psx)}")
    rep_psx = plot_confusion_pair(
        preds_psx, actual_psx,
        f"PPO Advisory Agent — Confusion Matrix (PSX Equities, {len(psx_data)} Tickers, 33% Test Split)",
        "fig8_cm_psx.png",
    )
    print(classification_report(actual_psx, preds_psx, target_names=["HOLD","BUY","SELL"], digits=3))
else:
    print("  SKIPPED — no PSX data downloaded.")
    rep_psx = None

# ─────────────────────────────────────────────────────────────────────────────
# FIG 9 — CLASSIFICATION METRICS BAR CHART
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 9] Classification metric bars ...")
if rep_us and rep_psx:
    metrics = ["precision", "recall", "f1-score"]
    classes = ["HOLD", "BUY", "SELL"]
    x = np.arange(len(classes)); w = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharey=False)
    fig.suptitle("PPO Agent Classification Metrics by Signal Class (Real Price Data)",
                 fontsize=11, fontweight="bold")
    for i, m in enumerate(metrics):
        ax       = axes[i]
        us_vals  = [rep_us[c][m]  for c in classes]
        psx_vals = [rep_psx[c][m] for c in classes]
        ax.bar(x - w / 2, us_vals,  w, label="US Agent",  color=NAVY,  alpha=0.85)
        ax.bar(x + w / 2, psx_vals, w, label="PSX Agent", color=AMBER, alpha=0.85)
        for xi, (uv, pv) in enumerate(zip(us_vals, psx_vals)):
            ax.text(xi - w / 2, uv  + 0.01, f"{uv:.2f}",  ha="center", va="bottom", fontsize=8)
            ax.text(xi + w / 2, pv  + 0.01, f"{pv:.2f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x); ax.set_xticklabels(classes)
        ax.set_ylim(0, 1.05); ax.set_ylabel(m.capitalize())
        ax.set_title(m.capitalize(), fontweight="bold")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.22, axis="y")
    plt.tight_layout(); save("fig9_clf_bars.png")
else:
    print("  SKIPPED — need both US and PSX reports.")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 10 — EQUITY CURVES (real ETF data)
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 10] Portfolio equity curves (real ETF returns) ...")

if len(etf_data) >= 3:
    # Align all ETFs to a common daily returns index
    ret_series = {}
    for name, df in etf_data.items():
        ret_series[name] = df["close"].pct_change().dropna()

    # Common date range
    common_idx = None
    for s in ret_series.values():
        common_idx = s.index if common_idx is None else common_idx.intersection(s.index)

    aligned = {k: v.reindex(common_idx).fillna(0) for k, v in ret_series.items()}
    dates   = common_idx

    portfolio_curves  = {}
    portfolio_results = {}

    for name, alloc in ALLOCATIONS.items():
        port_ret = pd.Series(0.0, index=dates)
        for asset, w in alloc.items():
            if asset in aligned:
                port_ret += w * aligned[asset]
        cum     = (1 + port_ret).cumprod()
        ann_ret = (cum.iloc[-1] ** (252 / len(cum)) - 1) * 100
        ann_vol = port_ret.std() * np.sqrt(252) * 100
        sharpe  = (port_ret.mean() * 252 - 0.04) / (port_ret.std() * np.sqrt(252) + 1e-10)
        rm      = cum.cummax()
        max_dd  = ((cum - rm) / rm).min() * 100
        portfolio_curves[name]  = cum
        portfolio_results[name] = {
            "Ann. Return (%)":    round(ann_ret, 2),
            "Ann. Volatility (%)":round(ann_vol, 2),
            "Sharpe Ratio":       round(sharpe,  3),
            "Max Drawdown (%)":   round(max_dd,  2),
        }

    # Benchmark
    if "Benchmark (SPY)" in aligned:
        spy_ret = aligned["Benchmark (SPY)"]
        spy_cum = (1 + spy_ret).cumprod()
        ann_ret = (spy_cum.iloc[-1] ** (252 / len(spy_cum)) - 1) * 100
        ann_vol = spy_ret.std() * np.sqrt(252) * 100
        sharpe  = (spy_ret.mean() * 252 - 0.04) / (spy_ret.std() * np.sqrt(252) + 1e-10)
        rm      = spy_cum.cummax()
        max_dd  = ((spy_cum - rm) / rm).min() * 100
        portfolio_curves["Benchmark (SPY)"]  = spy_cum
        portfolio_results["Benchmark (SPY)"] = {
            "Ann. Return (%)":    round(ann_ret, 2),
            "Ann. Volatility (%)":round(ann_vol, 2),
            "Sharpe Ratio":       round(sharpe,  3),
            "Max Drawdown (%)":   round(max_dd,  2),
        }

    print("  Portfolio results (real ETF data):")
    for name, m in portfolio_results.items():
        print(f"    {name:20s}  Ret={m['Ann. Return (%)']:6.2f}%  "
              f"Vol={m['Ann. Volatility (%)']:5.2f}%  "
              f"Sharpe={m['Sharpe Ratio']:5.3f}  "
              f"MaxDD={m['Max Drawdown (%)']:6.2f}%")

    all_names = list(ALLOCATIONS.keys()) + ["Benchmark (SPY)"]
    all_colors = CLUSTER_COLORS + [BENCHMARK_COLOR]

    fig, ax = plt.subplots(figsize=(11, 6))
    for name, col in zip(all_names, all_colors):
        if name not in portfolio_curves:
            continue
        ls = "-." if name == "Benchmark (SPY)" else "-"
        lw = 2.2  if name == "Benchmark (SPY)" else 1.8
        ax.plot(portfolio_curves[name].index,
                portfolio_curves[name].values,
                label=name, color=col, lw=lw, ls=ls)
    ax.set_xlabel("Date"); ax.set_ylabel("Portfolio Value (Normalised, Start = 1.0)")
    ax.set_title(
        "Cumulative Portfolio Growth by Risk Profile\n"
        "(Real ETF returns: VTI=Equities, BND=Fixed Income, DJP=Commodities, SHY=Cash)",
        fontweight="bold")
    ax.legend(fontsize=9.5, framealpha=0.9)
    ax.grid(True, alpha=0.22); ax.set_facecolor("#FAFAFA")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.2f}×"))
    plt.tight_layout(); save("fig10_equity_curves.png")

    # ─── FIG 11: Portfolio metrics bar chart ────────────────────────────────
    print("[Fig 11] Portfolio metrics bars ...")
    names   = [n for n in all_names if n in portfolio_results]
    colors  = all_colors[: len(names)]
    metrics_list = ["Ann. Return (%)", "Ann. Volatility (%)", "Sharpe Ratio", "Max Drawdown (%)"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle(
        "Portfolio Performance Metrics by Risk Profile\n(Real ETF data, 5-year window)",
        fontsize=11, fontweight="bold")
    display_names = [n.replace("Benchmark (SPY)", "SPY\nBenchmark") for n in names]
    for idx, (m, ax) in enumerate(zip(metrics_list, axes.flat)):
        vals = [portfolio_results[n][m] for n in names]
        bars = ax.bar(range(len(names)), vals, color=colors, alpha=0.85,
                      edgecolor="white", lw=1.2)
        for bar, val in zip(bars, vals):
            offset = abs(max(vals, key=abs)) * 0.015
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (offset if val >= 0 else -offset * 3),
                    f"{val:.2f}", ha="center",
                    va="bottom" if val >= 0 else "top",
                    fontsize=8.5, fontweight="bold")
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(display_names, rotation=45, ha="right", fontsize=8)
        ax.set_title(m, fontweight="bold"); ax.grid(True, alpha=0.22, axis="y")
        ax.axhline(0, color="black", lw=0.6)
        if "Return" in m or "Volatility" in m or "Drawdown" in m:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))
    plt.tight_layout(); save("fig11_portfolio_metrics.png")

else:
    print("  SKIPPED — insufficient ETF data downloaded.")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 12 — STRATEGY BACKTEST (real price data)
# ─────────────────────────────────────────────────────────────────────────────

print("[Fig 12] Strategy backtest (real price data) ...")

def backtest_real(ac, norm, price_data_dict, test_frac=0.33):
    """
    Backtest PPO agent vs buy-and-hold vs random on real price data.
    Returns per-ticker P&L for each strategy.
    """
    ppo_rets, bh_rets, rnd_rets = [], [], []
    rng = np.random.default_rng(42)
    for ticker, df in price_data_dict.items():
        feat = compute_features(df)
        feat = feat.dropna()
        if len(feat) < 80:
            continue
        nm    = norm.transform(feat)
        close = df["close"].reindex(feat.index).values
        split = int(len(nm) * (1 - test_frac))
        tm    = nm[split:]
        tc    = close[split:]
        if len(tc) < 2:
            continue

        # Buy-and-hold: single return over the test period
        bh_rets.append((tc[-1] / tc[0] - 1) * 100)

        ppo_pnl, rnd_pnl = 0.0, 0.0
        for j in range(len(tm) - 1):
            state = np.concatenate([tm[j], USER_VEC]).astype(np.float32)
            with torch.no_grad():
                logits, _ = ac(torch.from_numpy(state).unsqueeze(0))
                probs     = torch.softmax(logits, dim=-1).squeeze(0).numpy()
            action  = int(np.argmax(probs))
            bar_ret = tc[j + 1] / tc[j] - 1

            # Long on BUY, short on SELL, flat on HOLD
            if action == 1:
                ppo_pnl += bar_ret * 100
            elif action == 2:
                ppo_pnl -= bar_ret * 100

            rnd_action = rng.integers(0, 3)
            if rnd_action == 1:
                rnd_pnl += bar_ret * 100
            elif rnd_action == 2:
                rnd_pnl -= bar_ret * 100

        ppo_rets.append(ppo_pnl)
        rnd_rets.append(rnd_pnl)

    def stats(arr):
        a = np.array(arr)
        if len(a) == 0:
            return {"mean": 0, "std": 0, "sharpe": 0, "win_rate": 0}
        return {
            "mean":     round(float(np.mean(a)), 2),
            "std":      round(float(np.std(a)),  2),
            "sharpe":   round(float(np.mean(a) / (np.std(a) + 1e-10)), 3),
            "win_rate": round(float(np.mean(a > 0) * 100), 1),
        }
    return stats(ppo_rets), stats(bh_rets), stats(rnd_rets)


results_bt = {}
if us_data:
    ppo_us, bh_us, rnd_us = backtest_real(ac_us, norm_us, us_data)
    results_bt["US"] = (ppo_us, bh_us, rnd_us)
    print(f"  US   PPO={ppo_us['mean']:.2f}%  B&H={bh_us['mean']:.2f}%  Rnd={rnd_us['mean']:.2f}%")

if psx_data:
    ppo_psx, bh_psx, rnd_psx = backtest_real(ac_psx, norm_psx, psx_data)
    results_bt["PSX"] = (ppo_psx, bh_psx, rnd_psx)
    print(f"  PSX  PPO={ppo_psx['mean']:.2f}%  B&H={bh_psx['mean']:.2f}%  Rnd={rnd_psx['mean']:.2f}%")

if results_bt:
    markets  = list(results_bt.keys())
    n_panels = len(markets)
    fig, axes = plt.subplots(1, n_panels, figsize=(6 * n_panels, 5.5))
    if n_panels == 1:
        axes = [axes]
    fig.suptitle(
        "Strategy Comparison: PPO Agent vs Buy-and-Hold vs Random\n"
        "(Real price data, 33% held-out test period)",
        fontsize=11, fontweight="bold")

    for ax, market in zip(axes, markets):
        ppo_s, bh_s, rnd_s = results_bt[market]
        strats = ["PPO Agent", "Buy-and-Hold", "Random"]
        means  = [ppo_s["mean"],  bh_s["mean"],  rnd_s["mean"]]
        stds   = [ppo_s["std"],   bh_s["std"],   rnd_s["std"]]
        cols   = [NAVY, GREEN, GRAY]
        bars = ax.bar(strats, means, color=cols, alpha=0.85, edgecolor="white", lw=1.2)
        ax.errorbar(strats, means, yerr=stds, fmt="none", color="black", capsize=5, lw=1.5)
        for bar, m, s in zip(bars, means, stds):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    m + (s if m >= 0 else -s) + 0.3,
                    f"{m:.2f}%", ha="center",
                    va="bottom" if m >= 0 else "top",
                    fontsize=9, fontweight="bold")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_ylabel("Mean Total Return per Ticker (%)"); ax.set_title(market, fontweight="bold")
        ax.grid(True, alpha=0.22, axis="y")
        sharpes = [ppo_s["sharpe"], bh_s["sharpe"], rnd_s["sharpe"]]
        win_r   = [ppo_s["win_rate"], bh_s["win_rate"], rnd_s["win_rate"]]
        for xi, (sh, wr) in enumerate(zip(sharpes, win_r)):
            ax.text(xi, ax.get_ylim()[0] * 0.95,
                    f"Sharpe: {sh:.3f}\nWin: {wr:.0f}%",
                    ha="center", va="top", fontsize=8, color="#374151")
    plt.tight_layout(); save("fig12_backtest.png")
else:
    print("  SKIPPED — no price data available.")

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"All figures saved to: {OUT}")
print("Files generated:")
for f in sorted(os.listdir(OUT)):
    size_kb = os.path.getsize(os.path.join(OUT, f)) / 1024
    print(f"  {f:<40s}  {size_kb:6.1f} KB")
print("\nKey metrics:")
print(f"  K-Means  Silhouette = {sil:.4f}")
print(f"  K-Means  Davies-Bouldin = {dbi:.4f}")
print(f"  K-Means  Inertia (k=4) = {km.inertia_:.2f}")
print("Done.")
