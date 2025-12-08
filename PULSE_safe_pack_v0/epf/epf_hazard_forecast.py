"""
epf_hazard_forecast.py

Early-warning probe for viszony-alapú (relational) hazard forecasting
in the PULSE · EPF (Extended Paradox Field) layer.

Core idea:
    - We do NOT wait for a concrete "error event".
    - Instead, we monitor the *relationship* between the current state
      and a stable reference state (x vs x*), plus existing stability metrics.
    - From this, we derive an early-warning index E(t), which signals:
        GREEN  : stable field (no near-term hazard)
        AMBER  : field distortion (pre-hazard regime)
        RED    : unstable field (hazard imminent or active)

This module is intentionally minimal and "proto-level":
    - It does NOT know about concrete PULSE metrics.
    - It only works with generic snapshots (dict-like), plus an RDSI-like
      stability metric (if present).
    - Integration into PULSE_safe_pack_v0 is expected via a thin adapter
      that maps real metrics into:
        current_snapshot, reference_snapshot, stability_metrics, history_T.

License: same as the PULSE repo (Apache-2.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional
import math
import statistics


# ---------------------------------------------------------------------------
# Configuration and state dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HazardConfig:
    """
    Configuration for the hazard forecasting probe.

    alpha, beta:
        Weights for drift (D) and stability-loss (1 - S) in the hazard index E.
    warn_threshold:
        E >= warn_threshold → "AMBER" (pre-hazard regime).
    crit_threshold:
        E >= crit_threshold → "RED" (hazard imminent/active).
    min_history:
        Size of the short T-history window used to estimate drift.
        If more values are provided, we keep only the most recent min_history
        points.
    """
    alpha: float = 1.0
    beta: float = 1.0
    warn_threshold: float = 0.3
    crit_threshold: float = 0.7
    min_history: int = 3


@dataclass
class HazardState:
    """
    Output state of a single hazard forecasting call.

    Fields:
        T   : norm-like distance between current and reference snapshot.
        S   : stability index ∈ [0, 1], e.g. an RDSI-like signal (fallback: 0.5).
        D   : drift estimate for T over a short history window.
        E   : combined hazard index (alpha*D + beta*(1-S)).
        zone:
            "GREEN" : stable field
            "AMBER" : field distortion (pre-hazard)
            "RED"   : unstable field (hazard regime)
        reason:
            Short, human- and machine-readable explanation string.
    """
    T: float
    S: float
    D: float
    E: float
    zone: str
    reason: str


# ---------------------------------------------------------------------------
# Core computations
# ---------------------------------------------------------------------------

def compute_T(current: Dict[str, float],
              reference: Dict[str, float]) -> float:
    """
    Compute T(t): a simple Euclidean norm between current and reference
    snapshot vectors.

    Both current and reference are expected to be dict-like:
        { "metric_name": value, ... }

    Any missing keys in reference default to 0.0.
    Extra keys in reference are ignored.
    """
    sq_sum = 0.0
    for key, v_curr in current.items():
        v_ref = reference.get(key, 0.0)
        sq_sum += (v_curr - v_ref) ** 2
    return math.sqrt(sq_sum)


def estimate_S(stability_metrics: Dict[str, float]) -> float:
    """
    Estimate S(t) ∈ [0, 1] – a generic stability index.

    If "RDSI" is present in stability_metrics, we use it directly,
    clamped to [0,1].  Otherwise, we return 0.5 as a neutral stability.

    In a fully integrated PULSE setup, this would likely read the real
    RDSI or other EPF-derived stability fields.
    """
    if "RDSI" in stability_metrics:
        r = stability_metrics["RDSI"]
        return max(0.0, min(1.0, r))
    return 0.5


def estimate_D(history_T: List[float]) -> float:
    """
    Estimate drift D(t) from a short history of T-values.

    Simple approach:
        D ≈ mean( |T_i - T_{i-1}| ) over the given history.
    If fewer than 2 points are available, returns 0.0.
    """
    if len(history_T) < 2:
        return 0.0
    diffs = [abs(history_T[i] - history_T[i - 1]) for i in range(1, len(history_T))]
    return statistics.mean(diffs)


def classify_zone(E: float, cfg: HazardConfig) -> str:
    """
    Classify hazard index E into one of three zones:

        GREEN  : E < warn_threshold
        AMBER  : warn_threshold <= E < crit_threshold
        RED    : E >= crit_threshold
    """
    if E >= cfg.crit_threshold:
        return "RED"
    if E >= cfg.warn_threshold:
        return "AMBER"
    return "GREEN"


def build_reason(E: float, zone: str, T: float, S: float, D: float) -> str:
    """
    Build a short explanation string for the computed hazard state.

    This is deliberately simple and free-form; in a later integration
    step, we can enrich it with concrete metric names, EPF field tags,
    or paradoxon-interpretations.
    """
    base = f"E={E:.3f}, T={T:.3f}, S={S:.3f}, D={D:.3f}"
    if zone == "GREEN":
        return base + " → field stable, no near-term hazard signal."
    if zone == "AMBER":
        return base + " → field distortion detected (pre-hazard regime)."
    if zone == "RED":
        return base + " → field unstable, hazard imminent or active."
    return base + " → unknown zone."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast_hazard(
    current_snapshot: Dict[str, float],
    reference_snapshot: Dict[str, float],
    stability_metrics: Dict[str, float],
    history_T: List[float],
    cfg: Optional[HazardConfig] = None,
) -> HazardState:
    """
    Main entry point for viszony-alapú hazard forecasting.

    Inputs:
        current_snapshot:
            Current metrics snapshot, e.g. a gating input feature vector.
        reference_snapshot:
            "Good" baseline snapshot (EPF symmetry reference or learned normal).
        stability_metrics:
            Dict of existing stability signals (e.g. { "RDSI": 0.82 } ).
        history_T:
            Recent history of T-values (distance between current and reference).
        cfg:
            Optional HazardConfig (weights and thresholds).

    Output:
        HazardState with T, S, D, E, zone and reason.
    """
    if cfg is None:
        cfg = HazardConfig()

    T = compute_T(current_snapshot, reference_snapshot)
    S = estimate_S(stability_metrics)

    # Extend T-history with the current T.
    extended_history = history_T + [T]
    if len(extended_history) > cfg.min_history:
        extended_history = extended_history[-cfg.min_history:]

    D = estimate_D(extended_history)
    E = cfg.alpha * D + cfg.beta * (1.0 - S)

    zone = classify_zone(E, cfg)
    reason = build_reason(E, zone, T, S, D)

    return HazardState(
        T=T,
        S=S,
        D=D,
        E=E,
        zone=zone,
        reason=reason,
    )
