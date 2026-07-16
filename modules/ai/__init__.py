from .feature_eng import (
    compute_features,
    compute_raw_log_returns,
    FeatureNormalizer,
    encode_user_profile,
    FEATURE_NAMES,
    STATE_DIM,
    N_MARKET_FEATURES,
    N_USER_FEATURES,
)
from .market_env import AdvisoryEnv, ACTIONS, N_ACTIONS

# PPOAgent requires torch — imported lazily so the rest of the package
# loads cleanly even before torch is installed.
try:
    from .ppo_agent import PPOAgent, ActorCritic, ACTION_LABELS
except ImportError:
    pass

__all__ = [
    "compute_features", "compute_raw_log_returns",
    "FeatureNormalizer", "encode_user_profile",
    "FEATURE_NAMES", "STATE_DIM", "N_MARKET_FEATURES", "N_USER_FEATURES",
    "AdvisoryEnv", "ACTIONS", "N_ACTIONS",
    "PPOAgent", "ActorCritic", "ACTION_LABELS",
]
