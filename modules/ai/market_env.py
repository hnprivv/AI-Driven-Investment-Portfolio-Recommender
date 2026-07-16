"""
Advisory Market Environment for PPO Training
=============================================

The agent receives a state vector (16 normalised market features + 8 user
profile features) and outputs a discrete advisory action each step:
    0 = HOLD   1 = BUY   2 = SELL

Reward is a risk-adjusted forward log-return — the environment does NOT
execute any actual trades.
"""
from __future__ import annotations

import numpy as np
from .feature_eng import encode_user_profile, STATE_DIM

ACTIONS       = {0: "HOLD", 1: "BUY", 2: "SELL"}
N_ACTIONS     = 3


class AdvisoryEnv:
    """
    Episodic advisory environment built around pre-computed feature matrices.

    Parameters
    ----------
    market_norm : np.ndarray, shape (T, 16)
        Normalised market feature matrix from FeatureNormalizer.transform().
    raw_log_rets : np.ndarray, shape (T,)
        Un-normalised 1-bar log returns (log(close_t / close_t-1)).
        Used only for reward computation — never exposed in the observation.
    user_vec : np.ndarray, shape (8,)
        Encoded user profile vector from encode_user_profile().
    episode_len : int
        Number of steps per episode (default 120 ≈ 6 months of trading days).
    """

    obs_dim: int = STATE_DIM   # 24

    def __init__(
        self,
        market_norm:  np.ndarray,
        raw_log_rets: np.ndarray,
        user_vec:     np.ndarray,
        episode_len:  int = 120,
    ):
        assert market_norm.shape[0] == raw_log_rets.shape[0], \
            "market_norm and raw_log_rets must have the same length"
        assert len(user_vec) == 8, "user_vec must be 8-dimensional"

        self._mf    = market_norm.astype(np.float32)
        self._rets  = raw_log_rets.astype(np.float32)
        self._uvec  = user_vec.astype(np.float32)
        self._elen  = episode_len
        self._T     = len(market_norm)

        self._start       = 0
        self._t           = 0
        self._prev_action = 0

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def reset(self, start: int | None = None) -> np.ndarray:
        """
        Reset episode.  start=None → uniform-random position in valid range.
        Returns initial observation vector of shape (24,).
        """
        max_start = self._T - self._elen - 2
        if max_start < 0:
            raise ValueError(
                f"Feature matrix has only {self._T} rows but episode_len={self._elen}. "
                "Use a larger lookback window."
            )
        self._start       = int(np.random.randint(0, max_start + 1)) if start is None else start
        self._t           = 0
        self._prev_action = 0
        return self._obs()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        """
        Execute advisory action, compute reward, advance one step.

        Returns
        -------
        obs : np.ndarray (24,)
        reward : float
        done : bool
        info : dict  {"log_ret": float}
        """
        idx      = self._start + self._t
        next_idx = idx + 1

        if next_idx >= self._T:
            return self._obs(), 0.0, True, {}

        next_ret = float(self._rets[next_idx])
        reward   = self._reward(action, next_ret)

        self._prev_action = action
        self._t += 1
        done = self._t >= self._elen

        return self._obs(), reward, done, {"log_ret": next_ret}

    # ── Reward ────────────────────────────────────────────────────────────────

    def _reward(self, action: int, next_log_ret: float) -> float:
        """
        Risk-adjusted reward:
          BUY  → +next_log_ret   (correct if price rises)
          SELL → -next_log_ret   (correct if price falls)
          HOLD → 0               (no directional bet)

        Reward is further scaled by the user's risk tolerance:
          - Gains    scaled by (0.5 + 0.5 * risk)        [0.5 – 1.0×]
          - Losses   scaled by (2.0 – risk) for caution  [1.0 – 2.0×]
        This makes the agent more conservative for risk-averse users.
        """
        risk = float(self._uvec[0])   # already normalised 0-1

        if action == 1:     # BUY
            base = next_log_ret
        elif action == 2:   # SELL
            base = -next_log_ret
        else:               # HOLD
            base = 0.0

        # Symmetric risk-scaled binary reward.
        #
        # The reward magnitude scales with the user's risk tolerance but the
        # gain/loss magnitudes are EQUAL, so E[random directional] = 0 for
        # every risk profile.  This prevents HOLD from being the trivially
        # dominant action before the agent has learnt any real signal.
        #
        #   scale = 0.5 + 0.5 × risk  →  [0.60 conservative … 0.95 aggressive]
        #
        # Risk conditioning is reinforced via:
        #   • the risk features in the state vector (agent learns cautious
        #     policies for conservative profiles through the state mapping)
        #   • the inference-time confidence threshold (already implemented in
        #     ppo_agent.py)
        scale = 0.5 + 0.5 * risk   # [0.60, 0.95]

        if action == 1:    # BUY
            base = +0.02 * scale if next_log_ret > 0 else -0.02 * scale
        elif action == 2:  # SELL
            base = +0.02 * scale if next_log_ret < 0 else -0.02 * scale
        else:              # HOLD
            base = 0.0

        # Small churn penalty: discourages rapid flip-flopping
        churn = -0.005 if (action != self._prev_action and self._prev_action != 0) else 0.0

        return float(np.clip(base + churn, -0.5, 0.5))

    # ── Observation ──────────────────────────────────────────────────────────

    def _obs(self) -> np.ndarray:
        idx = self._start + self._t
        return np.concatenate([self._mf[idx], self._uvec], axis=0)

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def from_arrays(
        cls,
        market_norm:  np.ndarray,
        raw_log_rets: np.ndarray,
        profile:      dict,
        episode_len:  int = 120,
    ) -> "AdvisoryEnv":
        """Convenience constructor that encodes the profile dict automatically."""
        return cls(market_norm, raw_log_rets, encode_user_profile(profile), episode_len)

    # ── Synthetic profile sampler (used during training) ──────────────────────

    @staticmethod
    def sample_profile() -> dict:
        """
        Sample a random synthetic user profile spanning the full training space.
        Returns a dict compatible with encode_user_profile().
        """
        horizons    = ["1 Year", "3-5 Years", "5-10 Years", "10+ Years"]
        experiences = ["Beginner", "Intermediate", "Advanced"]
        return {
            "risk_tolerance":    int(np.random.randint(1, 11)),
            "cluster":           int(np.random.randint(0, 4)),
            "investment_horizon": horizons[np.random.randint(0, 4)],
            "experience":         experiences[np.random.randint(0, 3)],
            "age":               int(np.random.randint(22, 76)),
        }
