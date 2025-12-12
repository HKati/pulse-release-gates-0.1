"""
epf_hazard_adapter.py

Thin adapter utilities for running the EPF hazard forecasting probe from
PULSE EPF experiments and appending results to a JSONL log artefact.

Goals:
    - Keep epf_hazard_forecast.py generic and free of PULSE runtime
      concerns (no file I/O, no global state).
    - Provide a minimal helper that:
        * maintains a short T-history for a given gate,
        * runs forecast_hazard(...),
        * appends a structured JSON line to an epf_hazard_log.jsonl file.

Typical usage:
    - One HazardRuntimeState per gate (or per EPF field) in the runtime.
    - On each EPF cycle:
        * call probe_hazard_and_append_log(...),
        * inspect the returned HazardState if needed,
        * the adapter will update history_T and append a JSONL entry.

The produced log is intended as a diagnostic/analysis artefact, not as a
hard gating signal (at least in the proto phase).

Snapshot logging:
    - Optionally logs sanitized current/reference snapshots (numeric-only)
      into JSONL entries to support later feature-scaler calibration.

Relational Grail wiring (opt-in by artifact presence):
    - If cfg is not provided by caller, the adapter may auto-enable the
      forecast's feature mode using feature scalers from the calibration
      artifact (when available and sufficiently sampled).
    - This keeps the core forecast generic while allowing PULSE runtime
      to "light up" scaling/explainability once calibration exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import logging
import math

from .epf_hazard_forecast import (
    HazardConfig,
    HazardState,
    forecast_hazard,
    CALIBRATION_PATH,
    MIN_CALIBRATION_SAMPLES,
)
from .epf_hazard_features import FeatureSpec, FeatureScalersArtifactV0

LOG = logging.getLogger(__name__)

# Default filename for the JSONL hazard log.
LOG_FILENAME_DEFAULT = "epf_hazard_log.jsonl"

# Snapshot logging schema + bounds (defensive against oversized logs).
HAZARD_SNAPSHOT_SCHEMA_V0 = "epf_hazard_snapshot_v0"
DEFAULT_SNAPSHOT_MAX_DEPTH = 4
DEFAULT_SNAPSHOT_MAX_ITEMS = 2000


@dataclass
class HazardRuntimeState:
    """
    Minimal runtime state for the hazard probe.

    Fields:
        history_T:
            Short history of T-values (distance between current and
            reference snapshots). This is passed into forecast_hazard(...)
            on each call and extended with the latest T afterwards.
    """
    history_T: List[float]

    @classmethod
    def empty(cls) -> "HazardRuntimeState":
        """Create a new runtime state with an empty T-history."""
        return cls(history_T=[])


def _current_utc_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    """
    Append a single JSON object as one line to the given path.

    If the directory does not exist, it will be created. Errors during
    writing are logged but not raised, to avoid breaking the main EPF
    experiment flow due to logging issues.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError as exc:  # pragma: no cover - defensive logging
        LOG.warning("Failed to append hazard log entry to %s: %s", path, exc)


def sanitize_snapshot_for_log(
    snapshot: Mapping[str, Any],
    *,
    max_depth: int = DEFAULT_SNAPSHOT_MAX_DEPTH,
    max_items: int = DEFAULT_SNAPSHOT_MAX_ITEMS,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Sanitize a snapshot for safe JSONL logging (numeric-only).

    Rules:
        - Keep only finite numeric scalars:
            int/float (finite), bool -> 0/1, numeric strings -> float
        - Keep nested mappings up to max_depth.
        - Drop lists/tuples/sets and non-numeric objects.
        - Deterministic traversal (sorted keys).
        - Enforce max_items budget on numeric leaf values.

    Returns:
        (sanitized_snapshot, meta)
    """
    meta_base = {
        "schema": HAZARD_SNAPSHOT_SCHEMA_V0,
        "max_depth": int(max_depth),
        "max_items": int(max_items),
        "kept": 0,
        "dropped": 0,
        "truncated": False,
    }

    if not isinstance(snapshot, Mapping):
        meta_base["dropped"] = 1
        return {}, meta_base

    budget = [int(max_items)]
    stats = {"kept": 0, "dropped": 0, "truncated": False}

    sanitized = _sanitize_mapping(snapshot, depth=int(max_depth), budget=budget, stats=stats)

    meta_base["kept"] = int(stats["kept"])
    meta_base["dropped"] = int(stats["dropped"])
    meta_base["truncated"] = bool(stats["truncated"])
    return sanitized, meta_base


def _sanitize_mapping(
    m: Mapping[str, Any],
    *,
    depth: int,
    budget: List[int],
    stats: Dict[str, Any],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # Deterministic traversal: keys sorted by string representation.
    for k in sorted(m.keys(), key=lambda x: str(x)):
        if budget[0] <= 0:
            stats["truncated"] = True
            break

        v = m.get(k)

        if isinstance(v, Mapping):
            if depth <= 0:
                stats["dropped"] += 1
                continue
            child = _sanitize_mapping(v, depth=depth - 1, budget=budget, stats=stats)
            if child:
                out[str(k)] = child
            else:
                stats["dropped"] += 1
            continue

        # Explicitly drop container types to keep logs bounded and predictable.
        if isinstance(v, (list, tuple, set)):
            stats["dropped"] += 1
            continue

        num = _coerce_finite_number(v)
        if num is None:
            stats["dropped"] += 1
            continue

        out[str(k)] = num
        stats["kept"] += 1
        budget[0] -= 1

    return out


def _coerce_finite_number(value: Any) -> Optional[float]:
    """
    Best-effort conversion to finite float.

    Accepted:
        - bool -> 0.0/1.0
        - int/float (finite)
        - numeric strings (finite)
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return 1.0 if value else 0.0

    if isinstance(value, (int, float)):
        x = float(value)
        return x if math.isfinite(x) else None

    if isinstance(value, str):
        try:
            x = float(value.strip())
            return x if math.isfinite(x) else None
        except Exception:
            return None

    return None


def _maybe_enable_feature_mode_from_calibration(cfg: HazardConfig) -> None:
    """
    If caller did not provide cfg, we create one. In that case we may
    auto-enable feature mode when calibration artifact includes robust
    feature scalers with sufficient samples.

    Fail-open: any errors mean "leave cfg as-is".
    """
    # Respect explicit caller intent: if feature_specs already set, do nothing.
    if getattr(cfg, "feature_specs", None):
        return

    try:
        with CALIBRATION_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    fs = data.get("feature_scalers")
    if not isinstance(fs, Mapping):
        return

    try:
        artifact = FeatureScalersArtifactV0.from_dict(fs)
    except Exception:
        return

    # Guard: require enough snapshot-bearing events.
    if int(getattr(artifact, "count", 0)) < int(MIN_CALIBRATION_SAMPLES):
        return

    scalers = getattr(artifact, "features", {}) or {}
    if not scalers:
        return

    # Only use keys we can scale. Avoid mixing scaled/unscaled by default.
    keys = sorted(scalers.keys())
    cfg.feature_scalers = dict(scalers)
    cfg.feature_specs = [FeatureSpec(key=k) for k in keys]


def probe_hazard_and_append_log(
    gate_id: str,
    current_snapshot: Dict[str, float],
    reference_snapshot: Dict[str, float],
    stability_metrics: Dict[str, float],
    runtime_state: HazardRuntimeState,
    log_dir: Union[str, Path],
    cfg: Optional[HazardConfig] = None,
    timestamp: Optional[str] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
    log_snapshots: bool = True,
) -> HazardState:
    """
    Run the EPF hazard forecasting probe and append the result to a JSONL log.
    """
    if cfg is None:
        cfg = HazardConfig()
        _maybe_enable_feature_mode_from_calibration(cfg)

    # Run the core hazard forecast.
    state = forecast_hazard(
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        stability_metrics=stability_metrics,
        history_T=runtime_state.history_T,
        cfg=cfg,
    )

    # Update runtime T-history (unbounded; forecast_hazard handles its own window).
    runtime_state.history_T.append(state.T)

    # Build log entry.
    ts = timestamp or _current_utc_iso()
    entry: Dict[str, Any] = {
        "gate_id": gate_id,
        "timestamp": ts,
        "hazard": {
            "T": state.T,
            "S": state.S,
            "D": state.D,
            "E": state.E,
            "zone": state.zone,
            "reason": state.reason,
            # Additive: Relational Grail explainability (if present).
            "T_scaled": bool(getattr(state, "T_scaled", False)),
            "contributors_top": getattr(state, "contributors_top", []) or [],
        },
    }

    if log_snapshots:
        snap_cur, meta_cur = sanitize_snapshot_for_log(current_snapshot)
        snap_ref, meta_ref = sanitize_snapshot_for_log(reference_snapshot)
        entry["snapshot_current"] = snap_cur
        entry["snapshot_reference"] = snap_ref
        entry["snapshot_meta"] = {
            "schema": HAZARD_SNAPSHOT_SCHEMA_V0,
            "current": meta_cur,
            "reference": meta_ref,
        }

    if extra_meta:
        # Keep meta separate to avoid collisions with core fields.
        entry["meta"] = extra_meta

    log_path = Path(log_dir) / LOG_FILENAME_DEFAULT
    _append_jsonl(log_path, entry)

    return state
