import os

import joblib
import pandas as pd

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
