"""
PPO Advisory Agent — Actor-Critic Implementation
=================================================
Proximal Policy Optimisation for the AIPRS advisory recommendation system.

Actions: 0=HOLD  1=BUY  2=SELL
The agent is trained to maximise risk-adjusted forward returns and is
deployed as a READ-ONLY advisory tool — it never places real orders.
"""
from __future__ import annotations

import json
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

from .feature_eng import STATE_DIM

N_ACTIONS = 3
ACTION_LABELS = ["HOLD", "BUY", "SELL"]

_DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "model", "ppo"
)


# ── Neural network ────────────────────────────────────────────────────────────

class ActorCritic(nn.Module):
    """
    Shared-backbone Actor-Critic network.

    Architecture:
        Input (24) → 128 → 128 → 64    [shared trunk, LayerNorm + Tanh]
        → Actor head:  64 → 32 → 3     [log-softmax]
        → Critic head: 64 → 32 → 1     [scalar value]

    LayerNorm (vs BatchNorm) is used because episodes are sequential and
    minibatch sizes are small.  Tanh suits the bounded [-3, 3] input range.
    """

    def __init__(self, obs_dim: int = STATE_DIM, n_actions: int = N_ACTIONS,
                 hidden: int = 128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.LayerNorm(hidden), nn.Tanh(),
            nn.Linear(hidden, hidden),  nn.LayerNorm(hidden), nn.Tanh(),
            nn.Linear(hidden, 64),      nn.LayerNorm(64),     nn.Tanh(),
        )
        self.actor_head = nn.Sequential(
            nn.Linear(64, 32), nn.Tanh(),
            nn.Linear(32, n_actions),
        )
        self.critic_head = nn.Sequential(
            nn.Linear(64, 32), nn.Tanh(),
            nn.Linear(32, 1),
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                nn.init.zeros_(m.bias)
        # Smaller init for output layers so early actions are near-uniform
        nn.init.orthogonal_(self.actor_head[-1].weight, gain=0.01)
        nn.init.orthogonal_(self.critic_head[-1].weight, gain=1.0)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h      = self.trunk(x)
        logits = self.actor_head(h)
        value  = self.critic_head(h).squeeze(-1)
        return logits, value

    @torch.no_grad()
    def act(self, obs: np.ndarray) -> tuple[int, float, float, float]:
        """
        Sample one action.
        Returns (action_int, log_prob, value, entropy).
        """
        x = torch.FloatTensor(obs).unsqueeze(0)
        logits, value = self(x)
        dist   = Categorical(logits=logits)
        action = dist.sample()
        return (
            int(action.item()),
            float(dist.log_prob(action).item()),
            float(value.item()),
            float(dist.entropy().item()),
        )

    @torch.no_grad()
    def recommend(self, obs: np.ndarray, risk_scaled: float = 0.5) -> dict:
        """
        Advisory inference: returns recommendation dict.

        Temperature scaling (T=4.0) softens overconfident logits before
        computing probabilities. Trained PPO networks produce very peaked
        softmax outputs (90%+ on nearly every stock), which are not
        meaningful confidence estimates for financial predictions. Dividing
        the logits by a temperature constant before softmax flattens the
        distribution into a realistic 45-75% range WITHOUT changing which
        action has the highest score. This is a standard post-training
        calibration technique and requires no retraining. Applies to both
        the US and PSX agents since both call this method via advise().

        Risk-adaptive confidence threshold:
            threshold = 0.50 + 0.10 * (1 - risk_scaled)
        A conservative user (risk=0.2) needs ~58% confidence before a
        directional action is issued; an aggressive user (risk=0.9) needs
        ~51%. If no action exceeds the threshold the recommendation falls
        back to HOLD. This makes conservative profiles see more HOLD calls
        and aggressive profiles see more directional calls.
        """
        TEMPERATURE = 4.0   # raise to soften confidence further; lower to sharpen

        x = torch.FloatTensor(obs).unsqueeze(0)
        logits, value = self(x)

        # Temperature scaling — flatten peaked logits before softmax
        scaled_logits = logits / TEMPERATURE
        probs = torch.softmax(scaled_logits, dim=-1).squeeze(0).numpy()

        threshold   = 0.50 + 0.10 * (1.0 - float(risk_scaled))
        action_idx  = int(np.argmax(probs))
        confidence  = float(probs[action_idx])

        if confidence < threshold and action_idx != 0:
            action_idx = 0   # fall back to HOLD

        return {
            "action":        ACTION_LABELS[action_idx],
            "action_idx":    action_idx,
            "confidence":    confidence,
            "threshold":     threshold,
            "probabilities": {
                "HOLD": float(probs[0]),
                "BUY":  float(probs[1]),
                "SELL": float(probs[2]),
            },
            "value_estimate": float(value.item()),
        }

    def evaluate(
        self, obs: torch.Tensor, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, values = self(obs)
        dist      = Categorical(logits=logits)
        log_probs = dist.log_prob(actions)
        entropy   = dist.entropy()
        return log_probs, values, entropy


# ── PPO Agent ─────────────────────────────────────────────────────────────────

class PPOAgent:
    """
    Proximal Policy Optimisation agent wrapping ActorCritic.

    Typical training loop:
        agent = PPOAgent(obs_dim=STATE_DIM)
        obs = env.reset()
        for step in range(total_steps):
            action, lp, val, ent = agent.ac.act(obs)
            next_obs, reward, done, _ = env.step(action)
            agent.store(obs, action, reward, val, lp, done)
            obs = env.reset() if done else next_obs
            if (step + 1) % rollout_len == 0:
                last_val = agent.ac.act(obs)[2]
                agent.update(last_val)
    """

    def __init__(
        self,
        obs_dim:    int   = STATE_DIM,
        n_actions:  int   = N_ACTIONS,
        hidden:     int   = 128,
        lr:         float = 3e-4,
        gamma:      float = 0.99,
        gae_lambda: float = 0.95,
        clip_eps:   float = 0.2,
        vf_coef:    float = 0.5,
        ent_coef:   float = 0.01,
        n_epochs:   int   = 4,
        batch_size: int   = 64,
    ):
        self.gamma      = gamma
        self.gae_lambda = gae_lambda
        self.clip_eps   = clip_eps
        self.vf_coef    = vf_coef
        self.ent_coef   = ent_coef
        self.n_epochs   = n_epochs
        self.batch_size = batch_size

        self.ac        = ActorCritic(obs_dim, n_actions, hidden)
        self.optimizer = optim.Adam(self.ac.parameters(), lr=lr, eps=1e-5)
        self._reset_buffers()

    # ── Rollout buffer ────────────────────────────────────────────────────────

    def _reset_buffers(self):
        self._obs  : list[np.ndarray] = []
        self._acts : list[int]        = []
        self._rews : list[float]      = []
        self._vals : list[float]      = []
        self._lps  : list[float]      = []
        self._done : list[bool]       = []

    def store(self, obs: np.ndarray, action: int, reward: float,
              value: float, log_prob: float, done: bool):
        self._obs.append(obs)
        self._acts.append(action)
        self._rews.append(reward)
        self._vals.append(value)
        self._lps.append(log_prob)
        self._done.append(done)

    # ── GAE advantage estimation ──────────────────────────────────────────────

    def _compute_gae(self, last_value: float) -> tuple[np.ndarray, np.ndarray]:
        rewards   = np.array(self._rews, dtype=np.float32)
        values    = np.array(self._vals, dtype=np.float32)
        dones     = np.array(self._done, dtype=np.float32)
        n         = len(rewards)
        advantages = np.zeros(n, dtype=np.float32)
        gae = 0.0
        for t in reversed(range(n)):
            nv    = last_value if t == n - 1 else values[t + 1]
            delta = rewards[t] + self.gamma * nv * (1.0 - dones[t]) - values[t]
            gae   = delta + self.gamma * self.gae_lambda * (1.0 - dones[t]) * gae
            advantages[t] = gae
        returns = advantages + values
        return advantages, returns

    # ── PPO update ────────────────────────────────────────────────────────────

    def update(self, last_value: float = 0.0) -> dict[str, float]:
        """
        Run PPO update on the current rollout buffer.
        Returns dict of mean losses for logging.
        """
        advantages, returns = self._compute_gae(last_value)

        obs     = torch.FloatTensor(np.array(self._obs))
        actions = torch.LongTensor(np.array(self._acts))
        old_lps = torch.FloatTensor(np.array(self._lps))
        advs    = torch.FloatTensor(advantages)
        rets    = torch.FloatTensor(returns)

        # Normalise advantages within the batch
        advs = (advs - advs.mean()) / (advs.std() + 1e-8)

        n = len(obs)
        metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        n_updates = 0

        self.ac.train()
        for _ in range(self.n_epochs):
            idx_perm = np.random.permutation(n)
            for start in range(0, n, self.batch_size):
                idx = idx_perm[start: start + self.batch_size]

                lps, vals, ent = self.ac.evaluate(obs[idx], actions[idx])

                ratio  = torch.exp(lps - old_lps[idx])
                surr1  = ratio * advs[idx]
                surr2  = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * advs[idx]

                p_loss = -torch.min(surr1, surr2).mean()
                v_loss = nn.functional.mse_loss(vals, rets[idx])
                e_loss = -ent.mean()

                loss = p_loss + self.vf_coef * v_loss + self.ent_coef * e_loss

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.ac.parameters(), 0.5)
                self.optimizer.step()

                metrics["policy_loss"] += p_loss.item()
                metrics["value_loss"]  += v_loss.item()
                metrics["entropy"]     += (-e_loss.item())
                n_updates += 1

        self.ac.eval()
        self._reset_buffers()

        return {k: v / max(n_updates, 1) for k, v in metrics.items()}

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, directory: str | None = None):
        """Save model weights, actor-only weights, and config JSON."""
        directory = directory or _DEFAULT_MODEL_DIR
        os.makedirs(directory, exist_ok=True)

        # Full checkpoint
        torch.save(
            {
                "model_state":     self.ac.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
            },
            os.path.join(directory, "ppo_model.pt"),
        )

        # Actor-only (smaller, used at inference)
        torch.save(self.ac.state_dict(), os.path.join(directory, "ppo_actor.pt"))

        # Config
        config = {
            "obs_dim":    self.ac.trunk[0].in_features,
            "n_actions":  N_ACTIONS,
            "hidden":     self.ac.trunk[0].out_features,
            "action_labels": ACTION_LABELS,
        }
        with open(os.path.join(directory, "ppo_config.json"), "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def load(cls, directory: str | None = None, inference_only: bool = False) -> "PPOAgent":
        """Load a trained PPO agent from disk."""
        directory = directory or _DEFAULT_MODEL_DIR
        config_path = os.path.join(directory, "ppo_config.json")
        model_path  = os.path.join(directory, "ppo_actor.pt")

        if not os.path.exists(config_path) or not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model artefacts not found in {directory}. "
                "Run `python train_ppo.py` first."
            )

        with open(config_path) as f:
            cfg = json.load(f)

        agent = cls(obs_dim=cfg["obs_dim"], n_actions=cfg["n_actions"], hidden=cfg["hidden"])
        agent.ac.load_state_dict(torch.load(model_path, map_location="cpu"))
        agent.ac.eval()
        return agent

    # ── Convenience inference wrapper ─────────────────────────────────────────

    def advise(self, market_norm: np.ndarray, user_vec: np.ndarray) -> dict:
        """
        High-level advisory call for a single timestep.
        market_norm : shape (16,) — normalised market features for the latest bar
        user_vec    : shape (8,)  — encoded user profile
        """
        obs         = np.concatenate([market_norm, user_vec]).astype(np.float32)
        risk_scaled = float(user_vec[0])
        return self.ac.recommend(obs, risk_scaled)
