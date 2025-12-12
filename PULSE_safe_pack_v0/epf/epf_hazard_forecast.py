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

Relational Grail (optional):
    - If HazardConfig.feature_specs is provided, T can be computed in a
      deterministic feature space with optional robust scaling (median/MAD)
      and top-contributor explainability. This is opt-in and does not change
      default behavior.

License: same as the PULSE repo (Apache-2.0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple
import math
import statistics
import json
import pathlib

from .epf_hazard_features import (
    FeatureSpec,
    RobustScaler,
    compute_feature_contributions,
    weighted_l2_distance,
    top_contributors,
    format_top_contributors_reason,
)


# ---------------------------------------------------------------------------
# Calibration-aware defaults
# ---------------------------------------------------------------------------

def _find_pack_root() -> pathlib.Path:
    """
    Locate PULSE_safe_pack_v0 root directory deterministically.

    This file typically lives in: PULSE_safe_pack_v0/epf/epf_hazard_forecast.py
    so the pack root is usually a parent named "PULSE_safe_pack_v0".
    """
    here = pathlib.Path(__file__).resolve()
    for p in here.parents:
        if p.name == "PULSE_safe_pack_v0":
            return p
    # Fallback: conservative local parent
    return here.parent


# PULSE_safe_pack_v0 root
PACK_ROOT = _find_pack_root()

# Default location of the calibration artefact produced by
# tools/epf_hazard_calibrate.py
CALIBRATION_PATH = PACK_ROOT / "artifacts" / "epf_hazard_thresholds_v0.json"

# Built-in baseline thresholds (used if no reliable calibration is found)
DEFAULT_WARN_THRESHOLD = 0.3
DEFAULT_CRIT_THRESHOLD = 0.7

# Minimum number of samples required in the calibration artefact before we
# trust the calibrated thresholds.
MIN_CALIBRATION_SAMPLES = 20


def _load_calibrated_thresholds(
    path: pathlib.Path = CALIBRATION_PATH,
) -> Tuple[float, float]:
    """
    Try to load warn/crit thresholds from a calibration JSON artefact.

    Falls back to DEFAULT_* if:
    - the file is missing,
    - the JSON is invalid,
    - the global stats.count is missing or too small,
    - the thresholds are not numeric or obviously invalid.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD
    except json.JSONDecodeError:
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD
    except OSError:
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD

    global_cfg = data.get("global", {})
    stats = global_cfg.get("stats", {})
    count = stats.get("count")

    # Not enough data: don't trust this calibration yet.
    if not isinstance(count, int) or count < MIN_CALIBRATION_SAMPLES:
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD

    warn = global_cfg.get("warn_threshold")
    crit = global_cfg.get("crit_threshold")

    if not isinstance(warn, (int, float)) or not isinstance(crit, (int, float)):
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD

    warn_f = float(warn)
    crit_f = float(crit)

    if not (math.isfinite(warn_f) and math.isfinite(crit_f)):
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD

    # Basic sanity check: we expect 0 <= warn <= crit
    if not (0.0 <= warn_f <= crit_f):
        return DEFAULT_WARN_THRESHOLD, DEFAULT_CRIT_THRESHOLD

    return warn_f, crit_f


CALIBRATED_WARN_THRESHOLD, CALIBRATED_CRIT_THRESHOLD = _load_calibrated_thresholds()


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

    Relational Grail (optional):
        feature_specs:
            If provided (non-empty), compute T using these feature specs rather than
            legacy compute_T(current, reference).
        feature_scalers:
            Optional robust scalers by feature key (median/MAD), used to compute
            deltas in z-space. If absent, feature mode still works but is unscaled.
        top_k_contributors:
            Number of top contributors to include in explainability outputs.
    """
    alpha: float = 1.0
    beta: float = 1.0

    # These defaults may come from a calibration artefact, or fall back to
    # the built-in 0.3 / 0.7 baseline if calibration is not available or
    # not yet trustworthy.
    warn_threshold: float = CALIBRATED_WARN_THRESHOLD
    crit_threshold: float = CALIBRATED_CRIT_THRESHOLD
    min_history: int = 3

    # --- Relational Grail (opt-in) ---
    feature_specs: Optional[List[FeatureSpec]] = None
    feature_scalers: Optional[Dict[str, RobustScaler]] = None
    top_k_contributors: int = 3


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

        contributors_top:
            Optional compact list (top-K) of per-feature contributors when
            feature_specs are used (Relational Grail mode).
        T_scaled:
            True if at least one feature used a provided scaler (median/MAD).
    """
    T: float
    S: float
    D: float
    E: float
    zone: str
    reason: str

    # --- Relational Grail (optional, additive) ---
    contributors_top: List[Dict[str, Any]] = field(default_factory=list)
    T_scaled: bool = False


# ---------------------------------------------------------------------------
# Core computations
# ---------------------------------------------------------------------------

def compute_T(current: Mapping[str, Any], reference: Mapping[str, Any]) -> float:
    """
    Compute T(t): a simple Euclidean norm between current and reference
    snapshot vectors.

    Both current and reference are expected to be dict-like:
        { "metric_name": value, ... }

    Any missing keys in reference default to 0.0.
    Extra keys in reference are ignored.

    Defensive behavior:
        Non-numeric or non-finite values in current are ignored.
        Non-numeric or non-finite reference values are treated as 0.0.
    """
    sq_sum = 0.0
    for key, v_curr in current.items():
        if not isinstance(v_curr, (int, float)) or not math.isfinite(float(v_curr)):
            continue
        v_ref = reference.get(key, 0.0)
        if not isinstance(v_ref, (int, float)) or not math.isfinite(float(v_ref)):
            v_ref = 0.0
        dv = float(v_curr) - float(v_ref)
        sq_sum += dv * dv
    return math.sqrt(sq_sum)


def estimate_S(stability_metrics: Mapping[str, Any]) -> float:
    """
    Estimate S(t) ∈ [0, 1] – a generic stability index.

    If "RDSI" is present in stability_metrics, we use it directly,
    clamped to [0,1]. Otherwise, we return 0.5 as a neutral stability.
    """
    if "RDSI" in stability_metrics:
        r = stability_metrics.get("RDSI")
        if isinstance(r, (int, float)) and math.isfinite(float(r)):
            return max(0.0, min(1.0, float(r)))
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
    """
    base = f"E={E:.3f}, T={T:.3f}, S={S:.3f}, D={D:.3f}"
    if zone == "GREEN":
        return base + " → field stable, no near-term hazard signal."
    if zone == "AMBER":
        return base + " → field distortion detected (pre-hazard regime)."
    if zone == "RED":
        return base + " → field unstable, hazard imminent or active."
    return base + " → unknown zone."


def _compute_T_and_explain(
    current_snapshot: Mapping[str, Any],
    reference_snapshot: Mapping[str, Any],
    cfg: HazardConfig,
) -> Tuple[float, List[Dict[str, Any]], bool, str]:
    """
    Compute T with optional Relational Grail feature mode.

    Returns:
        (T, contributors_top_compact, used_scaling, reason_suffix)

    Deterministic:
        - contributor ordering is stable (handled by top_contributors)
        - reason suffix is stable
    """
    specs = cfg.feature_specs or []
    if not specs:
        # Legacy mode: keep behavior unchanged.
        return compute_T(current_snapshot, reference_snapshot), [], False, ""

    scalers = cfg.feature_scalers or {}

    contribs = compute_feature_contributions(
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        feature_specs=specs,
        scalers=scalers,
    )

    T = weighted_l2_distance(contribs)

    k = int(cfg.top_k_contributors) if isinstance(cfg.top_k_contributors, int) else 3
    if k <= 0:
        k = 3

    top = top_contributors(contribs, k=k, min_contrib=0.0)
    top_compact = [c.to_compact_dict() for c in top]

    used_scaling = any(c.scaled for c in contribs)
    suffix = format_top_contributors_reason(contribs, k=k)

    return float(T), top_compact, bool(used_scaling), suffix


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast_hazard(
    current_snapshot: Mapping[str, Any],
    reference_snapshot: Mapping[str, Any],
    stability_metrics: Mapping[str, Any],
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
        If feature_specs are provided in cfg, also includes top contributors and
        whether scaling was used.
    """
    if cfg is None:
        cfg = HazardConfig()

    # Compute T (legacy) or T (feature mode) + explainability.
    T, contrib_top, used_scaling, suffix = _compute_T_and_explain(
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        cfg=cfg,
    )

    S = estimate_S(stability_metrics)

    # Extend T-history with the current T.
    extended_history = history_T + [T]
    if len(extended_history) > cfg.min_history:
        extended_history = extended_history[-cfg.min_history:]

    D = estimate_D(extended_history)
    E = cfg.alpha * D + cfg.beta * (1.0 - S)

    zone = classify_zone(E, cfg)
    reason = build_reason(E, zone, T, S, D)

    if suffix:
        reason = f"{reason} | {suffix}"

    return HazardState(
        T=T,
        S=S,
        D=D,
        E=E,
        zone=zone,
        reason=reason,
        contributors_top=contrib_top,
        T_scaled=used_scaling,
    )
