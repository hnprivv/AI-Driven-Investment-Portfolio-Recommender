import os
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from app.portfolio import CLUSTER_LABELS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(ROOT, "modules", "model")

INCOME_MAP = {"< 25,000": 1, "25,000 - 50,000": 2, "50,000 - 100,000": 3, "100,000+": 4}
HORIZON_MAP = {"1 Year": 1, "3-5 Years": 3, "5-10 Years": 5, "10+ Years": 10}
EXPERIENCE_MAP = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}


def predict_user_cluster(
    age: int, income_range: str, risk_tolerance: int, horizon: str, experience: str
) -> int:
    """Mirrors modules/utils.py's predict_user_cluster — same model, same feature mapping."""
    try:
        model_path = os.path.join(MODEL_DIR, "kmeans_model.pkl")
        scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
        if not os.path.exists(model_path):
            return 0

        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        new_data = pd.DataFrame(
            {
                "Age": [age],
                "Income_Score": [INCOME_MAP.get(income_range, 1)],
                "Risk_Score": [risk_tolerance],
                "Horizon_Score": [HORIZON_MAP.get(horizon, 1)],
                "Exp_Score": [EXPERIENCE_MAP.get(experience, 1)],
            }
        )
        cluster_id = model.predict(scaler.transform(new_data))[0]
        return int(cluster_id)
    except Exception:
        return 0


@lru_cache(maxsize=1)
def get_cluster_background(n: int = 150, seed: int = 42) -> list[dict] | None:
    """150 synthetic investor profiles classified by the trained K-Means model,
    used as the background scatter for the 3D cluster-placement chart. Mirrors
    pages/1_Overview.py's AI CLUSTER PLACEMENT section exactly (same seed, same
    feature ranges), so the point cloud is pixel-for-pixel identical. Cached
    since it's fully deterministic and only needs computing once per process.
    """
    model_path = os.path.join(MODEL_DIR, "kmeans_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        return None

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    rng = np.random.RandomState(seed)  # same sequence as Streamlit's np.random.seed(42)
    bg_df = pd.DataFrame({
        "Age": rng.randint(18, 75, n),
        "Income_Score": rng.randint(1, 5, n),
        "Risk_Score": rng.randint(1, 11, n),
        "Horizon_Score": rng.choice([1, 3, 5, 10], n),
        "Exp_Score": rng.randint(1, 4, n),
    })
    bg_df["Cluster"] = model.predict(scaler.transform(bg_df))
    bg_df["Profile"] = bg_df["Cluster"].map(CLUSTER_LABELS)

    return [
        {
            "age": int(row.Age),
            "risk_score": int(row.Risk_Score),
            "exp_score": int(row.Exp_Score),
            "cluster": int(row.Cluster),
            "profile": row.Profile,
        }
        for row in bg_df.itertuples()
    ]
