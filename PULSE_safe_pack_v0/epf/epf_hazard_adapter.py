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
        * optional feature_allowlist can further constrain selection
          (runtime allowlist intersects artifact allowlist if both exist)
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
    """
    Prefix match for dotted paths.
    - exact match: path == prefix
    - subtree match: path startswith prefix + "."
    """
    return path == prefix or path.startswith(prefix + ".")


def _is_denied(path: str, deny: Optional[List[str]]) -> bool:
    if not deny:
        return False
    return any(_matches_prefix(path, d) for d in deny)


def _is_allowed_leaf(path: str, allowed: Optional[List[str]]) -> bool:
    """
    If allowed is None/empty -> everything allowed.
    Else leaf allowed if it matches any allowed prefix.
    """
    if not allowed:
        return True
    return any(_matches_prefix(path, a) for a in allowed)


def _should_traverse(path: str, allowed: Optional[List[str]]) -> bool:
    """
    Decide whether to traverse into a subtree at 'path' given allowed prefixes.

    We traverse if:
      - no allowlist is set (allowed is None), OR
      - some allowed prefix is:
          * equal to path, OR
          * deeper under path (allowed startswith path + "."), OR
          * shallower than path (path startswith allowed + ".")
    """
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

    Rules:
        - Keep only finite numeric scalars:
            int/float (finite), bool -> 0/1, numeric strings -> float
        - Keep nested mappings up to max_depth.
        - Drop lists/tuples/sets and non-numeric objects.
        - Deterministic traversal (sorted keys).
        - Enforce max_items budget on numeric leaf values.

    Policy (dotted paths):
        allowed_prefixes:
            If set, only keys under these prefixes are kept.
            Example: ["metrics", "external.fail_rate"]
        deny_keys:
            Always drop keys/subtrees matching these prefixes.
            Example: ["pii", "secrets.api_key", "raw_prompt"]

    Returns:
        (sanitized_snapshot, meta)
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

    # Deterministic traversal: keys sorted by string representation.
    for k in sorted(m.keys(), key=lambda x: str(x)):
        if budget[0] <= 0:
            stats["truncated"] = True
            break

        key_str = str(k)
        path = _join_path(path_prefix, key_str)

        # Deny overrides everything.
        if _is_denied(path, deny_keys):
            stats["dropped"] += 1
            continue

        v = m.get(k)

        if isinstance(v, Mapping):
            if depth <= 0:
                stats["dropped"] += 1
                continue

            # If allowlist is present, only traverse subtrees that can contain allowed keys.
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

        # Explicitly drop container types to keep logs bounded and predictable.
        if isinstance(v, (list, tuple, set)):
            stats["dropped"] += 1
            continue

        # Apply allowlist at leaf-level.
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


# ---------------------------------------------------------------------------
# Feature-mode autowire discipline (allowlist + snapshot intersection)
# ---------------------------------------------------------------------------

def _normalize_feature_key_list(x: Any) -> Optional[List[str]]:
    """
    Normalize feature allowlist from either:
      - comma-separated string
      - list/tuple/set of items
    Returns sorted unique list, or None if empty.
    """
    keys: List[str] = []
    if x is None:
        return None

    if isinstance(x, str):
        parts = [p.strip() for p in x.split(",")]
        keys = [p for p in parts if p]
    elif isinstance(x, (list, tuple, set)):
        for it in x:
            s = str(it).strip()
            if s:
                keys.append(s)
    else:
        s = str(x).strip()
        if s:
            keys = [s]

    keys = sorted(set(keys))
    return keys or None


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
      - if allowlist is provided, must also be in allowlist
    """
    snap_keys = {str(k) for k in list(current_snapshot.keys()) + list(reference_snapshot.keys())}
    candidates = set(map(str, scaler_keys)) & snap_keys
    if allowlist:
        candidates &= set(allowlist)
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

    Feature selection is disciplined:
      - only keys that appear in current/reference snapshot are considered
      - optional allowlist can further constrain selection
        (runtime allowlist intersects artifact allowlist if both exist)

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

    runtime_allow = _normalize_feature_key_list(feature_allowlist)
    artifact_allow = _normalize_feature_key_list(data.get("feature_allowlist"))

    if runtime_allow and artifact_allow:
        effective_allow = sorted(set(runtime_allow) & set(artifact_allow))
    else:
        effective_allow = runtime_allow or artifact_allow

    keys = _select_feature_keys_for_autowire(
        list(scalers.keys()),
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        allowlist=effective_allow,
    )
    if not keys:
        return

    cfg.feature_scalers = {k: scalers[k] for k in keys}
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
    snapshot_allowed_prefixes: Optional[List[str]] = None,
    snapshot_deny_keys: Optional[List[str]] = None,
    feature_allowlist: Optional[List[str]] = None,
) -> HazardState:
    """
    Run the EPF hazard forecasting probe and append the result to a JSONL log.

    Snapshot policy (when log_snapshots=True):
        - snapshot_allowed_prefixes: dotted prefixes to allow (optional)
        - snapshot_deny_keys: dotted prefixes to deny (optional)

    Feature-mode policy (only when cfg is None and we autowire from calibration):
        - feature_allowlist: optional list of feature keys to allow
          (intersects artifact "feature_allowlist" if present)

    Defaults preserve legacy behavior:
        - if snapshot policy omitted -> log all numeric keys
        - if feature allowlist omitted -> use snapshot-present keys ∩ scaler keys
    """
    if cfg is None:
        cfg = HazardConfig()
        _maybe_enable_feature_mode_from_calibration(
            cfg,
            current_snapshot=current_snapshot,
            reference_snapshot=reference_snapshot,
            feature_allowlist=feature_allowlist,
        )

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
            # Additive: which feature keys were used when feature-mode is active.
            "feature_keys": [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])],
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
        # Keep meta separate to avoid collisions with core fields.
        entry["meta"] = extra_meta

    log_path = Path(log_dir) / LOG_FILENAME_DEFAULT
    _append_jsonl(log_path, entry)

    return state
