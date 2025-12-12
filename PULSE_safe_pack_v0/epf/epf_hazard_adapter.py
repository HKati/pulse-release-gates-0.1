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
    - Sanitization is deterministic and bounded (max depth, max numeric items).
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

from .epf_hazard_forecast import HazardConfig, HazardState, forecast_hazard

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

    The caller is expected to keep one HazardRuntimeState per gate or per
    EPF field, and persist it only for the duration needed (e.g. one
    EPF experiment run).
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

    Inputs:
        gate_id:
            Identifier of the gate or EPF field this probe corresponds to.
            This is written into the log as a top-level field.
        current_snapshot:
            Dict of current metrics (e.g. gating feature vector).
        reference_snapshot:
            Dict of "good" baseline metrics (EPF symmetry reference or
            learned normal).
        stability_metrics:
            Dict of stability signals (e.g. { "RDSI": 0.82 }).
        runtime_state:
            HazardRuntimeState carrying the T-history; this will be
            mutated in-place by appending the latest T-value.
        log_dir:
            Directory where the JSONL log file will be written. The file
            name defaults to LOG_FILENAME_DEFAULT.
        cfg:
            Optional HazardConfig; if omitted, a default config is used.
        timestamp:
            Optional ISO-8601 timestamp string; if None, current UTC time
            is used.
        extra_meta:
            Optional dictionary of additional metadata to include in the
            log entry (e.g. run_id, commit hash, experiment id).
        log_snapshots:
            If True, include sanitized numeric-only current/reference snapshots
            in the JSONL entry to support later scaler calibration.

    Behaviour:
        - Calls forecast_hazard(...) with the current runtime_state.history_T.
        - Extends runtime_state.history_T with the resulting T.
        - Appends a JSON object to <log_dir>/epf_hazard_log.jsonl with:
            * gate_id
            * timestamp
            * fields from HazardState (T, S, D, E, zone, reason)
            * optional sanitized snapshots
            * any extra_meta fields under "meta".

    Returns:
        HazardState from the underlying forecast_hazard(...) call.
    """
    if cfg is None:
        cfg = HazardConfig()

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
