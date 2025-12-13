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

Snapshot logging:
    - Optionally logs sanitized current/reference snapshots (numeric-only)
      into JSONL entries to support later feature-scaler calibration.
    - Snapshot logging can be constrained by a deterministic policy:
        * allowed_prefixes (dotted paths): only keep keys under these prefixes
        * deny_keys (dotted paths): always drop these keys/subtrees

Relational Grail wiring (opt-in by artifact presence):
    - If cfg is not provided by caller, the adapter may auto-enable the
      forecast's feature mode using feature scalers from the calibration
      artifact (when available and sufficiently sampled).
    - Feature autowire is disciplined:
        * only keys present in current/reference snapshots are eligible
        * priority of constraints:
            1) runtime feature_allowlist (if provided)
            2) artifact feature_allowlist (if provided)
            3) artifact recommended_features (if present; may be empty -> deny all)
            4) fallback: snapshot-keys ∩ scaler keys
        * if both runtime + artifact allowlists are provided -> intersection

NEW (Step 8):
    - Log provenance of feature-mode selection:
        * hazard.feature_mode_source
        * hazard.feature_mode_active
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

LOG_FILENAME_DEFAULT = "epf_hazard_log.jsonl"

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
    except OSError as exc:  # pragma: no cover
        LOG.warning("Failed to append hazard log entry to %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Snapshot sanitization + policy
# ---------------------------------------------------------------------------

def _normalize_path_list(xs: Optional[List[str]]) -> Optional[List[str]]:
    """
    Normalize dotted-path lists deterministically.
    - strip whitespace
    - drop empties
    - drop trailing dots
    - sort unique for determinism
    """
    if not xs:
        return None
    out: List[str] = []
    for x in xs:
        if x is None:
            continue
        s = str(x).strip()
        if not s:
            continue
        if s.endswith("."):
            s = s[:-1]
        if s:
            out.append(s)
    if not out:
        return None
    return sorted(set(out))


def _join_path(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + ".")


def _is_denied(path: str, deny: Optional[List[str]]) -> bool:
    if not deny:
        return False
    return any(_matches_prefix(path, d) for d in deny)


def _is_allowed_leaf(path: str, allowed: Optional[List[str]]) -> bool:
    if not allowed:
        return True
    return any(_matches_prefix(path, a) for a in allowed)


def _should_traverse(path: str, allowed: Optional[List[str]]) -> bool:
    if not allowed:
        return True
    for a in allowed:
        if a == path:
            return True
        if a.startswith(path + "."):
            return True
        if path.startswith(a + "."):
            return True
    return False


def sanitize_snapshot_for_log(
    snapshot: Mapping[str, Any],
    *,
    max_depth: int = DEFAULT_SNAPSHOT_MAX_DEPTH,
    max_items: int = DEFAULT_SNAPSHOT_MAX_ITEMS,
    allowed_prefixes: Optional[List[str]] = None,
    deny_keys: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Sanitize a snapshot for safe JSONL logging (numeric-only), with optional policy.
    """
    allowed_n = _normalize_path_list(allowed_prefixes)
    deny_n = _normalize_path_list(deny_keys)

    meta_base: Dict[str, Any] = {
        "schema": HAZARD_SNAPSHOT_SCHEMA_V0,
        "max_depth": int(max_depth),
        "max_items": int(max_items),
        "kept": 0,
        "dropped": 0,
        "truncated": False,
    }
    if allowed_n or deny_n:
        meta_base["policy"] = {
            "allowed_prefixes": allowed_n or [],
            "deny_keys": deny_n or [],
        }

    if not isinstance(snapshot, Mapping):
        meta_base["dropped"] = 1
        return {}, meta_base

    budget = [int(max_items)]
    stats = {"kept": 0, "dropped": 0, "truncated": False}

    sanitized = _sanitize_mapping(
        snapshot,
        depth=int(max_depth),
        budget=budget,
        stats=stats,
        path_prefix="",
        allowed_prefixes=allowed_n,
        deny_keys=deny_n,
    )

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
    path_prefix: str,
    allowed_prefixes: Optional[List[str]],
    deny_keys: Optional[List[str]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for k in sorted(m.keys(), key=lambda x: str(x)):
        if budget[0] <= 0:
            stats["truncated"] = True
            break

        key_str = str(k)
        path = _join_path(path_prefix, key_str)

        if _is_denied(path, deny_keys):
            stats["dropped"] += 1
            continue

        v = m.get(k)

        if isinstance(v, Mapping):
            if depth <= 0:
                stats["dropped"] += 1
                continue
            if not _should_traverse(path, allowed_prefixes):
                stats["dropped"] += 1
                continue

            child = _sanitize_mapping(
                v,
                depth=depth - 1,
                budget=budget,
                stats=stats,
                path_prefix=path,
                allowed_prefixes=allowed_prefixes,
                deny_keys=deny_keys,
            )
            if child:
                out[key_str] = child
            else:
                stats["dropped"] += 1
            continue

        if isinstance(v, (list, tuple, set)):
            stats["dropped"] += 1
            continue

        if not _is_allowed_leaf(path, allowed_prefixes):
            stats["dropped"] += 1
            continue

        num = _coerce_finite_number(v)
        if num is None:
            stats["dropped"] += 1
            continue

        out[key_str] = num
        stats["kept"] += 1
        budget[0] -= 1

    return out


def _coerce_finite_number(value: Any) -> Optional[float]:
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


# ---------------------------------------------------------------------------
# Feature-mode autowire discipline + provenance
# ---------------------------------------------------------------------------

def _normalize_feature_key_list(x: Any) -> Optional[List[str]]:
    """
    Normalize feature lists from either:
      - comma-separated string
      - list/tuple/set of items

    Semantics:
      - None -> None (unspecified)
      - ""   -> None (unspecified)
      - []   -> []   (explicit deny-all)
      - ["a", "b"] -> ["a", "b"] (sorted unique)
    """
    if x is None:
        return None

    if isinstance(x, str):
        parts = [p.strip() for p in x.split(",") if p.strip()]
        return sorted(set(parts)) or None

    if isinstance(x, (list, tuple, set)):
        keys: List[str] = []
        for it in x:
            s = str(it).strip()
            if s:
                keys.append(s)
        return sorted(set(keys))  # may be []

    s = str(x).strip()
    return [s] if s else None


def _select_feature_keys_for_autowire(
    scaler_keys: List[str],
    current_snapshot: Mapping[str, Any],
    reference_snapshot: Mapping[str, Any],
    allowlist: Optional[List[str]] = None,
) -> List[str]:
    """
    Select feature keys deterministically for feature-mode autowire.

    Rules:
      - must exist in scaler_keys
      - must exist in current_snapshot or reference_snapshot (avoid "phantom" features)
      - if allowlist is provided (even if empty), restrict to allowlist

    NOTE:
      - allowlist=None -> no allowlist restriction
      - allowlist=[]   -> deny all
    """
    snap_keys = {str(k) for k in list(current_snapshot.keys()) + list(reference_snapshot.keys())}
    candidates = {str(k) for k in scaler_keys} & snap_keys

    # Apply allowlist whenever explicitly provided.
    if allowlist is not None:
        candidates &= {str(x) for x in allowlist}

    return sorted(candidates)


def _maybe_enable_feature_mode_from_calibration(
    cfg: HazardConfig,
    *,
    current_snapshot: Mapping[str, Any],
    reference_snapshot: Mapping[str, Any],
    feature_allowlist: Optional[List[str]] = None,
) -> None:
    """
    Auto-enable feature mode when calibration artifact includes robust feature scalers
    with sufficient samples.

    Constraint priority:
      1) runtime feature_allowlist (if provided)
      2) artifact feature_allowlist (if provided)
      3) artifact recommended_features (if present; may be empty -> deny all)
      4) fallback: snapshot-keys ∩ scaler keys

    If both runtime + artifact allowlists are provided -> intersection.

    Provenance:
      - cfg.feature_mode_source: which constraint was used
      - cfg.feature_mode_active: whether feature mode was activated
    """
    if getattr(cfg, "feature_specs", None):
        # Caller already configured feature mode explicitly.
        setattr(cfg, "feature_mode_source", "caller_cfg")
        setattr(cfg, "feature_mode_active", True)
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

    if int(getattr(artifact, "count", 0)) < int(MIN_CALIBRATION_SAMPLES):
        return

    scalers = getattr(artifact, "features", {}) or {}
    if not scalers:
        return

    runtime_allow = _normalize_feature_key_list(feature_allowlist)
    artifact_allow = _normalize_feature_key_list(data.get("feature_allowlist"))
    recommended = _normalize_feature_key_list(data.get("recommended_features"))

    # Decide constraint source + effective allowlist.
    if runtime_allow is not None and artifact_allow is not None:
        source = "runtime_and_artifact_allowlist"
        effective_allow: Optional[List[str]] = sorted(set(runtime_allow) & set(artifact_allow))
    elif runtime_allow is not None:
        source = "runtime_allowlist"
        effective_allow = runtime_allow
    elif artifact_allow is not None:
        source = "artifact_allowlist"
        effective_allow = artifact_allow
    elif recommended is not None:
        source = "recommended_features"
        effective_allow = recommended
    else:
        source = "snapshot_intersection"
        effective_allow = None

    # Record provenance even if we end up not enabling.
    setattr(cfg, "feature_mode_source", source)

    # Explicit empty constraint means deny-all -> do not enable feature mode.
    if effective_allow is not None and len(effective_allow) == 0:
        setattr(cfg, "feature_mode_active", False)
        return

    keys = _select_feature_keys_for_autowire(
        list(scalers.keys()),
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        allowlist=effective_allow,
    )
    if not keys:
        setattr(cfg, "feature_mode_active", False)
        return

    cfg.feature_scalers = {k: scalers[k] for k in keys}
    cfg.feature_specs = [FeatureSpec(key=k) for k in keys]
    setattr(cfg, "feature_mode_active", True)


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
    snapshot_allowed_prefixes: Optional[List[str]] = None,
    snapshot_deny_keys: Optional[List[str]] = None,
    feature_allowlist: Optional[List[str]] = None,
) -> HazardState:
    """
    Run the EPF hazard forecasting probe and append the result to a JSONL log.
    """
    cfg_provided_by_caller = cfg is not None

    if cfg is None:
        cfg = HazardConfig()
        _maybe_enable_feature_mode_from_calibration(
            cfg,
            current_snapshot=current_snapshot,
            reference_snapshot=reference_snapshot,
            feature_allowlist=feature_allowlist,
        )

    state = forecast_hazard(
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        stability_metrics=stability_metrics,
        history_T=runtime_state.history_T,
        cfg=cfg,
    )

    runtime_state.history_T.append(state.T)

    feature_keys = [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])]
    feature_mode_active = bool(feature_keys)

    src = getattr(cfg, "feature_mode_source", None)
    if not isinstance(src, str) or not src.strip():
        if feature_mode_active and cfg_provided_by_caller:
            src = "caller_cfg"
        elif feature_mode_active:
            src = "unknown"
        else:
            src = "none"

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
            "T_scaled": bool(getattr(state, "T_scaled", False)),
            "contributors_top": getattr(state, "contributors_top", []) or [],
            "feature_keys": feature_keys,
            "feature_mode_active": feature_mode_active,
            "feature_mode_source": src,
        },
    }

    if log_snapshots:
        snap_cur, meta_cur = sanitize_snapshot_for_log(
            current_snapshot,
            allowed_prefixes=snapshot_allowed_prefixes,
            deny_keys=snapshot_deny_keys,
        )
        snap_ref, meta_ref = sanitize_snapshot_for_log(
            reference_snapshot,
            allowed_prefixes=snapshot_allowed_prefixes,
            deny_keys=snapshot_deny_keys,
        )
        entry["snapshot_current"] = snap_cur
        entry["snapshot_reference"] = snap_ref
        entry["snapshot_meta"] = {
            "schema": HAZARD_SNAPSHOT_SCHEMA_V0,
            "current": meta_cur,
            "reference": meta_ref,
        }

    if extra_meta:
        entry["meta"] = extra_meta

    log_path = Path(log_dir) / LOG_FILENAME_DEFAULT
    _append_jsonl(log_path, entry)

    return state
