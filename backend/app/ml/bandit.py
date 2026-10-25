"""
Thompson Sampling Contextual Bandit for Sequential Offer Escalation.

Patent Feature: Adaptive dispatch ordering that learns from historical
accept/decline patterns without storing raw personal data.

Context dimensions: trade (profession) x hour_bucket (morning/afternoon/evening/night)
Arms: offer_rank (0=first, 1=second, 2=third)
Reward: 1 if accepted, 0 if declined

State stored in: backend/app/ml/artifacts/bandit_state.json
(Updated in-memory; persisted on write calls)
"""
import json
import logging
import random
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

BANDIT_STATE_PATH = Path(__file__).resolve().parent / "artifacts" / "bandit_state.json"
N_ARMS = 3  # offer ranks: 0 (1st), 1 (2nd), 2 (3rd)

# Beta distribution parameters: alpha[arm] = successes+1, beta[arm] = failures+1
# State shape: {context_key: {"alpha": [a0,a1,a2], "beta": [b0,b1,b2]}}
_bandit_state: Dict[str, Any] = {}
_state_loaded = False


def _hour_bucket(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _context_key(trade: str, hour: int) -> str:
    trade_clean = (trade or "general").lower().replace(" ", "_")[:20]
    return f"{trade_clean}_{_hour_bucket(hour)}"


def _load_state() -> None:
    global _bandit_state, _state_loaded
    if _state_loaded:
        return
    _state_loaded = True
    if not getattr(settings, "ML_ENABLED", True):
        return
    try:
        if BANDIT_STATE_PATH.is_file():
            with open(BANDIT_STATE_PATH, "r", encoding="utf-8") as f:
                _bandit_state = json.load(f)
            logger.info("Loaded bandit state from %s (%d contexts)", BANDIT_STATE_PATH, len(_bandit_state))
    except Exception as exc:
        logger.warning("Failed to load bandit state: %s", exc)
        _bandit_state = {}


def _save_state() -> None:
    try:
        BANDIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BANDIT_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(_bandit_state, f, indent=2)
    except Exception as exc:
        logger.warning("Failed to save bandit state: %s", exc)


def _get_context(key: str) -> Dict[str, list]:
    if key not in _bandit_state:
        _bandit_state[key] = {
            "alpha": [1.0] * N_ARMS,
            "beta":  [1.0] * N_ARMS,
        }
    return _bandit_state[key]


def sample_best_arm(trade: str, hour: int, rng_seed: Optional[int] = None) -> int:
    """
    Thompson Sampling: draw from Beta(alpha, beta) for each arm, return argmax.
    Returns the recommended offer rank (0 = dispatch first, 1 = dispatch second, etc.)
    Falls back to arm 0 if ML is disabled or state unavailable.
    """
    if not getattr(settings, "ML_ENABLED", True):
        return 0
    _load_state()
    try:
        key = _context_key(trade, hour)
        ctx = _get_context(key)
        rng = np.random.default_rng(rng_seed)
        samples = [
            rng.beta(ctx["alpha"][i], ctx["beta"][i])
            for i in range(N_ARMS)
        ]
        return int(np.argmax(samples))
    except Exception as exc:
        logger.warning("sample_best_arm failed: %s", exc)
        return 0


def record_outcome(trade: str, hour: int, arm: int, accepted: bool) -> None:
    """
    Update Beta distribution parameters after observing an outcome.
    arm: 0, 1, or 2 (offer rank that was used)
    accepted: True if worker accepted the offer, False if declined.
    Persists state to disk after update.
    """
    if not getattr(settings, "ML_ENABLED", True):
        return
    _load_state()
    try:
        key = _context_key(trade, hour)
        ctx = _get_context(key)
        arm = max(0, min(N_ARMS - 1, arm))
        if accepted:
            ctx["alpha"][arm] += 1.0
        else:
            ctx["beta"][arm] += 1.0
        _save_state()
    except Exception as exc:
        logger.warning("record_outcome failed: %s", exc)


def get_bandit_stats() -> Dict[str, Any]:
    """Return summary of bandit state for admin diagnostics."""
    _load_state()
    total_contexts = len(_bandit_state)
    total_trials = 0
    for ctx in _bandit_state.values():
        a = ctx.get("alpha", [1]*N_ARMS)
        b = ctx.get("beta",  [1]*N_ARMS)
        # trials = (alpha - 1) + (beta - 1) per arm, summed
        for i in range(N_ARMS):
            total_trials += (a[i] - 1) + (b[i] - 1)
    return {
        "total_contexts": total_contexts,
        "total_trials": int(total_trials),
        "state_file": str(BANDIT_STATE_PATH),
        "n_arms": N_ARMS,
    }


def reset_state() -> None:
    """Reset bandit state (for testing)."""
    global _bandit_state, _state_loaded
    _bandit_state = {}
    _state_loaded = False
