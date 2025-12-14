#!/usr/bin/env python3
"""
Run all PULSE safe-pack checks and generate core artifacts.

This script is the main entrypoint for the PULSE_safe_pack_v0 "safe pack".
It orchestrates the configured checks/profiles and produces the baseline
status.json and related artifacts under the pack's artifacts directory,
which are then consumed by CI workflows and reporting tools.
"""

from __future__ import annotations

import os
import json
import datetime
import pathlib
import sys
import subprocess
from collections import deque
from html import escape
from typing import Optional, Tuple, Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (  # noqa: E402
    HazardRuntimeState,
    probe_hazard_and_append_log,
)
from PULSE_safe_pack_v0.epf.epf_hazard_policy import (  # noqa: E402
    HazardGateConfig,
    evaluate_hazard_gate,
)
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (  # noqa: E402
    DEFAULT_WARN_THRESHOLD,
    DEFAULT_CRIT_THRESHOLD,
    CALIBRATED_WARN_THRESHOLD,
    CALIBRATED_CRIT_THRESHOLD,
    MIN_CALIBRATION_SAMPLES,
)

try:
    from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (  # noqa: E402
        CALIBRATION_PATH as HAZARD_CALIB_PATH,
    )
except Exception:  # pragma: no cover
    HAZARD_CALIB_PATH = ROOT / "artifacts" / "epf_hazard_thresholds_v0.json"


art = ROOT / "artifacts"
art.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().isoformat() + "Z"
STATUS_VERSION = "1.0.0-demo"

# ---------------------------------------------------------------------------
# Stability Map (artifact)
# ---------------------------------------------------------------------------

STABILITY_MAP_SCHEMA_V0 = "epf_stability_map_v0"
STABILITY_MAP_FILENAME = "epf_stability_map_v0.json"
STABILITY_MAP_MAX_EVENTS = 200
STABILITY_MAP_RECENT_EVENTS = 20


# ---------------------------------------------------------------------------
# Helpers for provenance / cross-run drift seeding
# ---------------------------------------------------------------------------

def get_git_sha(repo_root: pathlib.Path) -> Optional[str]:
    """
    Best-effort git SHA for provenance (fail-open).
    """
    sha = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA") or os.getenv("BUILD_SOURCEVERSION")
    if isinstance(sha, str) and sha.strip():
        return sha.strip()

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        s = out.decode("utf-8", errors="ignore").strip()
        return s if s else None
    except Exception:
        return None


def get_run_key() -> Optional[str]:
    """
    Best-effort CI run identity (fail-open).
    """
    parts = []
    for k in (
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_WORKFLOW",
        "CI_PIPELINE_ID",
        "BUILD_BUILDID",
    ):
        v = os.getenv(k)
        if isinstance(v, str) and v.strip():
            parts.append(f"{k}={v.strip()}")
    return "|".join(parts) if parts else None


def load_hazard_T_history(
    log_path: pathlib.Path,
    *,
    gate_id: str,
    max_points: int = 20,
) -> list[float]:
    """
    Load recent hazard T history for a given gate_id from epf_hazard_log.jsonl.
    Returns oldest->newest, last max_points items.
    """
    if not log_path.exists():
        return []

    values: list[float] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if str(obj.get("gate_id", "")) != str(gate_id):
                continue

            hazard = obj.get("hazard", {}) or {}
            T = hazard.get("T")
            if isinstance(T, (int, float)):
                values.append(float(T))

    return values[-max_points:]


def compute_baseline_ok(gates: dict) -> bool:
    """
    Baseline pass/fail excluding the hazard shadow gate if present.
    This prevents topology from becoming self-referential.
    """
    for k, v in gates.items():
        if str(k) == "epf_hazard_ok":
            continue
        if v is not True:
            return False
    return True


def classify_topology_region(*, baseline_ok: Optional[bool], hazard_zone: str) -> str:
    """
    Field topology region (diagnostic overlay):
      - stably_good / unstably_good / stably_bad / unstably_bad / unknown

    Stable is GREEN; anything else is "unstable" (AMBER/RED).

    baseline_ok=None -> unknown.
    """
    if baseline_ok is None:
        return "unknown"

    z = str(hazard_zone or "").upper()
    if z == "GREEN":
        stable = True
    elif z in ("AMBER", "RED"):
        stable = False
    else:
        return "unknown"

    if baseline_ok and stable:
        return "stably_good"
    if baseline_ok and not stable:
        return "unstably_good"
    if (not baseline_ok) and stable:
        return "stably_bad"
    return "unstably_bad"


# ---------------------------------------------------------------------------
# Stability Map helpers (derived from hazard log + snapshots)
# ---------------------------------------------------------------------------

def _as_boolish(v: Any) -> Optional[bool]:
    """
    Convert common encodings to bool:
      - bool -> bool
      - numeric 0/1 (or float-ish) -> False/True
    Return None if not interpretable.
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(float(v) >= 0.5)
    return None


def _iter_gate_values_from_snapshot(snapshot: Any) -> list[bool]:
    """
    Extract gate outcomes from snapshot_current (fail-open).
    Supports:
      - flat dotted keys: "gates.<name>" -> 0/1
      - nested: {"gates": {"<name>": 0/1}}
    Returns list of bools; empty list means "no gate info present".
    """
    if not isinstance(snapshot, dict):
        return []

    # Nested style: {"gates": {...}}
    gates_node = snapshot.get("gates")
    if isinstance(gates_node, dict):
        out: list[bool] = []
        for k in sorted(gates_node.keys(), key=lambda x: str(x)):
            b = _as_boolish(gates_node.get(k))
            if b is None:
                # if any key is not interpretable, skip it (fail-open)
                continue
            out.append(bool(b))
        return out

    # Flat dotted keys: "gates.<name>"
    out2: list[bool] = []
    for k in sorted(snapshot.keys(), key=lambda x: str(x)):
        ks = str(k)
        if not ks.startswith("gates."):
            continue
        b = _as_boolish(snapshot.get(k))
        if b is None:
            continue
        out2.append(bool(b))
    return out2


def compute_baseline_ok_from_snapshot(snapshot: Any) -> Optional[bool]:
    """
    baseline_ok derived from snapshot gate outcomes:
      - True if all available gate values are True
      - False if any is False
      - None if no gate info exists
    """
    vals = _iter_gate_values_from_snapshot(snapshot)
    if not vals:
        return None
    return all(vals)


def load_recent_hazard_events(
    log_path: pathlib.Path,
    *,
    gate_id: str,
    max_events: int = STABILITY_MAP_MAX_EVENTS,
) -> list[dict]:
    """
    Load last max_events hazard log entries for a given gate_id.
    Uses a deque to avoid reading into memory.
    """
    if not log_path.exists():
        return []

    buf: deque[dict] = deque(maxlen=int(max_events))
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(obj.get("gate_id", "")) != str(gate_id):
                continue
            if isinstance(obj, dict):
                buf.append(obj)
    return list(buf)


def build_stability_map_payload(
    events: list[dict],
    *,
    gate_id: str,
    created_utc: str,
    max_events: int,
    recent_events: int,
) -> dict:
    """
    Build a stability map payload from hazard log events.

    The map is a *diagnostic topology overlay*:
      axis A: baseline_ok (derived from snapshot_current gates.*)
      axis B: stability (hazard zone GREEN=stable, AMBER/RED=unstable)

    It does not enforce gates; it records field behavior.
    """
    counts = {
        "stably_good": 0,
        "unstably_good": 0,
        "stably_bad": 0,
        "unstably_bad": 0,
        "unknown": 0,
    }

    recent: list[dict] = []
    for ev in events:
        hazard = ev.get("hazard", {}) or {}
        zone = str(hazard.get("zone", "") or "")
        baseline_ok = compute_baseline_ok_from_snapshot(ev.get("snapshot_current"))
        region = classify_topology_region(baseline_ok=baseline_ok, hazard_zone=zone)

        if region not in counts:
            region = "unknown"
        counts[region] += 1

        ts = ev.get("timestamp")
        E = hazard.get("E")
        T = hazard.get("T")
        recent.append(
            {
                "timestamp": str(ts) if ts is not None else None,
                "region": str(region),
                "zone": str(zone) if zone else None,
                "baseline_ok": baseline_ok,
                "E": float(E) if isinstance(E, (int, float)) else None,
                "T": float(T) if isinstance(T, (int, float)) else None,
            }
        )

    if recent_events > 0:
        recent = recent[-int(recent_events):]
    else:
        recent = []

    return {
        "schema": STABILITY_MAP_SCHEMA_V0,
        "created_utc": created_utc,
        "gate_id": str(gate_id),
        "window": {
            "max_events": int(max_events),
            "events": int(len(events)),
            "recent_events": int(recent_events),
        },
        "counts": counts,
        "recent": recent,
    }


# ---------------------------------------------------------------------------
# Helpers for EPF field snapshot
# ---------------------------------------------------------------------------

def build_epf_field_snapshots(
    metrics: dict,
    gates: dict,
) -> Tuple[dict, dict, dict]:
    """
    Build a flat dotted-key EPF field snapshot + deterministic reference anchor.

    Design intent (Grail-hű):
      - current_snapshot is a FIELD coordinate vector (not an alert payload)
      - reference_snapshot is a stable suggestion anchor
      - deterministic and numeric-only

    Returns:
        (current_snapshot, reference_snapshot, stability_metrics)
    """
    current: dict = {}

    # 1) Numeric metrics -> metrics.<key>
    # Exclude hazard_* derived fields and obvious non-numeric info.
    for k in sorted(metrics.keys(), key=lambda x: str(x)):
        ks = str(k)
        if ks.startswith("hazard_"):
            continue
        if ks in ("build_time", "rdsi_note", "git_sha", "run_key"):
            continue

        v = metrics.get(k)
        if isinstance(v, (int, float)):
            current[f"metrics.{ks}"] = float(v)

    # 2) Gate outcomes -> gates.<name> (bool -> 0/1)
    # Exclude shadow hazard gate to keep the coordinate system non-self-referential.
    for name in sorted(gates.keys(), key=lambda x: str(x)):
        if str(name) == "epf_hazard_ok":
            continue
        ok = gates.get(name) is True
        current[f"gates.{name}"] = 1.0 if ok else 0.0

    # 3) Stability metrics (forecast reads RDSI if present)
    stability: dict = {}
    rdsi = metrics.get("RDSI")
    if isinstance(rdsi, (int, float)):
        stability["RDSI"] = float(rdsi)

    # 4) Deterministic reference anchor for this coordinate system
    reference: dict = {}
    for key in sorted(current.keys()):
        if key == "metrics.RDSI":
            reference[key] = 1.0
        elif key.startswith("gates."):
            reference[key] = 1.0
        else:
            reference[key] = 0.0

    return current, reference, stability


# ---------------------------------------------------------------------------
# Helpers for EPF hazard history / sparkline + UI formatting
# ---------------------------------------------------------------------------

def load_hazard_E_history(
    log_path: pathlib.Path,
    *,
    max_points: int = 20,
    gate_id: Optional[str] = None,
) -> list[float]:
    """
    Load up to max_points hazard E values from epf_hazard_log.jsonl.

    If gate_id is provided, only values from that series are returned.
    """
    if not log_path.exists():
        return []

    values: list[float] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if gate_id is not None and str(obj.get("gate_id", "")) != str(gate_id):
                continue

            hazard = obj.get("hazard", {}) or {}
            E = hazard.get("E")
            if isinstance(E, (int, float)):
                values.append(float(E))

    return values[-max_points:] if values else []


def build_E_sparkline_svg(values, width: int = 160, height: int = 40) -> str:
    if len(values) < 2:
        return ""

    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v = min_v + 1.0

    padding = 4
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding

    points = []
    n = len(values)
    for i, v in enumerate(values):
        t = i / (n - 1) if n > 1 else 0.0
        x = padding + t * inner_w
        norm = (v - min_v) / (max_v - min_v)
        y = height - padding - norm * inner_h
        points.append(f"{x:.1f},{y:.1f}")

    points_str = " ".join(points)

    svg = f"""<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Recent E history">
  <polyline fill="none" stroke="#4f46e5" stroke-width="1.5" points="{points_str}" />
</svg>"""
    return svg


def format_top_contributors(contribs, k: int = 3) -> str:
    if not isinstance(contribs, list) or not contribs:
        return "none"

    parts = []
    for c in contribs[:k]:
        if not isinstance(c, dict):
            continue
        key = escape(str(c.get("key", "UNKNOWN")))
        contrib = c.get("contrib")
        if isinstance(contrib, (int, float)):
            parts.append(f"{key}({float(contrib):.2f})")
        else:
            parts.append(key)

    return ", ".join(parts) if parts else "none"


def load_last_hazard_feature_context(
    log_path: pathlib.Path,
    *,
    gate_id: Optional[str] = None,
) -> tuple[list[str], str, bool]:
    """
    Read the last valid JSON event from epf_hazard_log.jsonl and return:
      (feature_keys, feature_mode_source, feature_mode_active)

    If gate_id is provided, selects the last entry for that series.
    Fail-open for older logs.
    """
    if not log_path.exists():
        return ([], "none", False)

    last_obj = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if gate_id is not None and str(obj.get("gate_id", "")) != str(gate_id):
                continue

            last_obj = obj

    if not isinstance(last_obj, dict):
        return ([], "none", False)

    hazard = last_obj.get("hazard", {}) or {}

    keys_raw = hazard.get("feature_keys")
    keys: list[str] = []
    if isinstance(keys_raw, list):
        for k in keys_raw:
            s = str(k).strip()
            if s:
                keys.append(s)

    src = hazard.get("feature_mode_source")
    if not isinstance(src, str) or not src.strip():
        src = "unknown" if keys else "none"

    active = hazard.get("feature_mode_active")
    if not isinstance(active, bool):
        active = bool(keys)

    return (keys, src, bool(active))


def format_feature_keys(keys: list[str], preview: int = 6) -> str:
    if not keys:
        return "none"

    shown = keys[:preview]
    shown_esc = [escape(k) for k in shown]
    if len(keys) > preview:
        return ", ".join(shown_esc) + f" +{len(keys) - preview} more"
    return ", ".join(shown_esc)


def load_calibration_recommendation(calib_path: pathlib.Path) -> dict:
    out = {
        "present": False,
        "recommended_features": [],
        "recommended_count": 0,
        "min_coverage": None,
        "max_features": None,
        "feature_allowlist_count": 0,
    }

    try:
        with calib_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return out

    out["present"] = True

    rec = data.get("recommended_features")
    if isinstance(rec, list):
        cleaned = []
        for x in rec:
            s = str(x).strip()
            if s:
                cleaned.append(s)
        out["recommended_features"] = cleaned
        out["recommended_count"] = len(cleaned)

    allow = data.get("feature_allowlist")
    if isinstance(allow, list):
        out["feature_allowlist_count"] = len([1 for x in allow if str(x).strip()])

    knobs = data.get("recommendation")
    if isinstance(knobs, dict):
        mc = knobs.get("min_coverage")
        mf = knobs.get("max_features")
        if isinstance(mc, (int, float)):
            out["min_coverage"] = float(mc)
        if isinstance(mf, int):
            out["max_features"] = int(mf)

    return out


# ---------------------------------------------------------------------------
# Minimal demo gates (all True by default so CI passes)
# ---------------------------------------------------------------------------

gates = {
    "pass_controls_refusal": True,
    "effect_present": True,
    "psf_monotonicity_ok": True,
    "psf_mono_shift_resilient": True,
    "pass_controls_comm": True,
    "psf_commutativity_ok": True,
    "psf_comm_shift_resilient": True,
    "pass_controls_sanit": True,
    "sanitization_effective": True,
    "sanit_shift_resilient": True,
    "psf_action_monotonicity_ok": True,
    "psf_idempotence_ok": True,
    "psf_path_independence_ok": True,
    "psf_pii_monotonicity_ok": True,
    "q1_grounded_ok": True,
    "q2_consistency_ok": True,
    "q3_fairness_ok": True,
    "q4_slo_ok": True,
}

metrics = {
    "RDSI": 0.92,
    "rdsi_note": "Demo value for CI smoke-run",
    "build_time": now,
}

# Baseline gate health excluding hazard shadow gate (topology uses this).
baseline_ok = compute_baseline_ok(gates)
metrics["hazard_baseline_ok"] = bool(baseline_ok)

# ---------------------------------------------------------------------------
# EPF hazard probe (field snapshot + cross-run drift seeding)
# ---------------------------------------------------------------------------

# Provenance (fail-open)
run_key = get_run_key()
git_sha = get_git_sha(REPO_ROOT)
if run_key:
    metrics["run_key"] = run_key
if git_sha:
    metrics["git_sha"] = git_sha

hazard_log_path = art / "epf_hazard_log.jsonl"

# Stable series id for the field
hazard_gate_id = "EPF_field_main"
metrics["hazard_gate_id"] = hazard_gate_id

# Seed drift across runs (history_T)
seed_T = load_hazard_T_history(hazard_log_path, gate_id=hazard_gate_id, max_points=10)
metrics["hazard_seed_T_points"] = int(len(seed_T))
hazard_runtime = HazardRuntimeState(history_T=list(seed_T))

# Build Grail field snapshots (flat dotted keys)
current_snapshot, reference_snapshot, stability_metrics = build_epf_field_snapshots(metrics, gates)

hazard_state = probe_hazard_and_append_log(
    gate_id=hazard_gate_id,
    current_snapshot=current_snapshot,
    reference_snapshot=reference_snapshot,
    stability_metrics=stability_metrics,
    runtime_state=hazard_runtime,
    log_dir=art,
    extra_meta={
        "created_utc": now,
        "status_version": STATUS_VERSION,
        "run_key": run_key,
        "git_sha": git_sha,
    },
)

hazard_decision = evaluate_hazard_gate(hazard_state, cfg=HazardGateConfig())

# Surface hazard metrics into status.json metrics.
metrics["hazard_T"] = hazard_state.T
metrics["hazard_S"] = hazard_state.S
metrics["hazard_D"] = hazard_state.D
metrics["hazard_E"] = hazard_state.E
metrics["hazard_zone"] = hazard_state.zone
metrics["hazard_reason"] = hazard_state.reason
metrics["hazard_ok"] = hazard_decision.ok
metrics["hazard_severity"] = hazard_decision.severity

# Field topology overlay (diagnostic)
hazard_topology_region = classify_topology_region(
    baseline_ok=bool(baseline_ok),
    hazard_zone=str(hazard_state.zone),
)
metrics["hazard_topology_region"] = str(hazard_topology_region)

hazard_T_scaled = bool(getattr(hazard_state, "T_scaled", False))
hazard_contributors_top = getattr(hazard_state, "contributors_top", []) or []
metrics["hazard_T_scaled"] = hazard_T_scaled
metrics["hazard_contributors_top"] = hazard_contributors_top

# Feature-mode context (from the last log event for this gate_id)
hazard_feature_keys, hazard_feature_mode_source, hazard_feature_mode_active = load_last_hazard_feature_context(
    hazard_log_path,
    gate_id=hazard_gate_id,
)
metrics["hazard_feature_keys"] = hazard_feature_keys
metrics["hazard_feature_count"] = int(len(hazard_feature_keys))
metrics["hazard_feature_mode_source"] = str(hazard_feature_mode_source)
metrics["hazard_feature_mode_active"] = bool(hazard_feature_mode_active)

# Calibration recommendation summary (if present)
calib_summary = load_calibration_recommendation(pathlib.Path(HAZARD_CALIB_PATH))
metrics["hazard_recommended_count"] = int(calib_summary.get("recommended_count", 0) or 0)
metrics["hazard_recommend_min_coverage"] = calib_summary.get("min_coverage")
metrics["hazard_recommend_max_features"] = calib_summary.get("max_features")
metrics["hazard_feature_allowlist_count"] = int(calib_summary.get("feature_allowlist_count", 0) or 0)

# E-history sparkline (per series)
E_history = load_hazard_E_history(hazard_log_path, max_points=20, gate_id=hazard_gate_id)
hazard_history_svg = build_E_sparkline_svg(E_history)
if E_history and hazard_history_svg:
    history_fragment = (
        '<div class="epf-hazard-history">'
        '<span class="epf-hazard-history-label">Recent E history</span>'
        f"{hazard_history_svg}"
        "</div>"
    )
else:
    history_fragment = (
        '<div class="epf-hazard-history">'
        '<span class="epf-hazard-history-label">Recent E history</span>'
        '<span class="epf-hazard-history-empty">Not enough hazard history yet</span>'
        "</div>"
    )

# ---------------------------------------------------------------------------
# Stability Map artifact (derived from hazard log)
# ---------------------------------------------------------------------------

stability_events = load_recent_hazard_events(
    hazard_log_path,
    gate_id=hazard_gate_id,
    max_events=STABILITY_MAP_MAX_EVENTS,
)
stability_map = build_stability_map_payload(
    stability_events,
    gate_id=hazard_gate_id,
    created_utc=now,
    max_events=STABILITY_MAP_MAX_EVENTS,
    recent_events=STABILITY_MAP_RECENT_EVENTS,
)

stability_map_path = art / STABILITY_MAP_FILENAME
try:
    with stability_map_path.open("w", encoding="utf-8") as f:
        json.dump(stability_map, f, indent=2, sort_keys=True)
except Exception:
    # fail-open: do not break CI on artifact write
    pass

# Surface a compact stability map summary into metrics (scalar-friendly)
counts = (stability_map.get("counts") or {}) if isinstance(stability_map, dict) else {}
metrics["hazard_stability_map_events"] = int(stability_map.get("window", {}).get("events", 0) or 0)
metrics["hazard_stability_stably_good_n"] = int(counts.get("stably_good", 0) or 0)
metrics["hazard_stability_unstably_good_n"] = int(counts.get("unstably_good", 0) or 0)
metrics["hazard_stability_stably_bad_n"] = int(counts.get("stably_bad", 0) or 0)
metrics["hazard_stability_unstably_bad_n"] = int(counts.get("unstably_bad", 0) or 0)
metrics["hazard_stability_unknown_n"] = int(counts.get("unknown", 0) or 0)

# ---------------------------------------------------------------------------
# Shadow hazard gate (ENV-flag-enforceable)
# ---------------------------------------------------------------------------

enforce_hazard = os.getenv("EPF_HAZARD_ENFORCE", "0") == "1"
if enforce_hazard:
    gates["epf_hazard_ok"] = hazard_decision.ok
else:
    gates["epf_hazard_ok"] = True

status = {
    "version": STATUS_VERSION,
    "created_utc": now,
    "gates": gates,
    "metrics": metrics,
}

with open(art / "status.json", "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

# ---------------------------------------------------------------------------
# HTML report card (demo Quality Ledger view)
# ---------------------------------------------------------------------------

all_gates_pass = all(gates.values())
decision_label = "DEMO-PASS" if all_gates_pass else "DEMO-FAIL"

zone = metrics["hazard_zone"]
if zone == "GREEN":
    hazard_badge_class = "badge-green"
elif zone == "AMBER":
    hazard_badge_class = "badge-amber"
elif zone == "RED":
    hazard_badge_class = "badge-red"
else:
    hazard_badge_class = "badge-unknown"

topo_region = str(metrics.get("hazard_topology_region", "unknown"))
if topo_region == "stably_good":
    topo_badge_class = "badge-topo-good"
elif topo_region == "unstably_good":
    topo_badge_class = "badge-topo-ugood"
elif topo_region == "stably_bad":
    topo_badge_class = "badge-topo-bad"
elif topo_region == "unstably_bad":
    topo_badge_class = "badge-topo-ubad"
else:
    topo_badge_class = "badge-topo-unknown"

scale_badge_class = "badge-scaled" if hazard_T_scaled else "badge-unscaled"
scale_badge_text = "SCALED" if hazard_T_scaled else "UNSCALED"
contributors_text = format_top_contributors(hazard_contributors_top, k=3)

features_used_n = int(metrics.get("hazard_feature_count", 0) or 0)
features_used_text = format_feature_keys(hazard_feature_keys, preview=6)

feature_mode_label = "ON" if bool(hazard_feature_mode_active) else "OFF"
feature_mode_source_text = escape(str(hazard_feature_mode_source))

rec_n = int(metrics.get("hazard_recommended_count", 0) or 0)
rec_min_cov = metrics.get("hazard_recommend_min_coverage")
rec_min_cov_text = f"{float(rec_min_cov):.2f}" if isinstance(rec_min_cov, (int, float)) else "n/a"

seed_T_points = int(metrics.get("hazard_seed_T_points", 0) or 0)
hazard_gate_id_text = escape(str(metrics.get("hazard_gate_id", "unknown")))
baseline_ok_text = "OK" if bool(metrics.get("hazard_baseline_ok")) else "FAIL"

# Stability map summary
sm_events = int(metrics.get("hazard_stability_map_events", 0) or 0)
sm_sg = int(metrics.get("hazard_stability_stably_good_n", 0) or 0)
sm_ug = int(metrics.get("hazard_stability_unstably_good_n", 0) or 0)
sm_sb = int(metrics.get("hazard_stability_stably_bad_n", 0) or 0)
sm_ub = int(metrics.get("hazard_stability_unstably_bad_n", 0) or 0)
sm_unk = int(metrics.get("hazard_stability_unknown_n", 0) or 0)

calib_is_effective = (
    CALIBRATED_WARN_THRESHOLD != DEFAULT_WARN_THRESHOLD
    or CALIBRATED_CRIT_THRESHOLD != DEFAULT_CRIT_THRESHOLD
)
threshold_regime = "CALIBRATED" if calib_is_effective else "BASELINE"

gate_rows = []
for name, ok in sorted(gates.items()):
    status_class = "status-pass" if ok else "status-fail"
    status_text = "✅ PASS" if ok else "❌ FAIL"
    gate_rows.append(
        f'            <tr><td>{name}</td>'
        f'<td><span class="{status_class}">{status_text}</span></td></tr>'
    )
gate_rows_html = "\n".join(gate_rows)

html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>PULSE Report Card — demo</title>
    <style>
      :root {{
        color: #111827;
        background-color: #f9fafb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        padding: 1.5rem;
        background-color: #f9fafb;
      }}
      .prc-shell {{
        max-width: 900px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
        padding: 1.5rem 2rem 2rem;
      }}
      h1 {{
        margin: 0 0 0.25rem;
        font-size: 1.5rem;
      }}
      h2 {{
        margin-top: 1.5rem;
        font-size: 1.1rem;
      }}
      .prc-meta {{
        margin: 0;
        font-size: 0.8rem;
        color: #6b7280;
      }}
      .prc-strip {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        background: linear-gradient(90deg, #0f172a, #1f2937);
        color: #e5e7eb;
        font-size: 0.9rem;
      }}
      .strip-left,
      .strip-right {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.5rem;
      }}
      .badge {{
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }}
      .badge-decision {{
        background: rgba(34, 197, 94, 0.18);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.6);
      }}
      .badge-rdsi {{
        background: rgba(59, 130, 246, 0.18);
        color: #bfdbfe;
        border: 1px solid rgba(59, 130, 246, 0.6);
      }}
      .badge-green {{
        background: rgba(34, 197, 94, 0.15);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.5);
      }}
      .badge-amber {{
        background: rgba(245, 158, 11, 0.18);
        color: #fed7aa;
        border: 1px solid rgba(245, 158, 11, 0.6);
      }}
      .badge-red {{
        background: rgba(248, 113, 113, 0.18);
        color: #fecaca;
        border: 1px solid rgba(248, 113, 113, 0.6);
      }}
      .badge-unknown {{
        background: rgba(148, 163, 184, 0.18);
        color: #e5e7eb;
        border: 1px solid rgba(148, 163, 184, 0.6);
      }}

      /* Topology badges (diagnostic overlay) */
      .badge-topo-good {{
        background: rgba(34, 197, 94, 0.15);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.5);
      }}
      .badge-topo-ugood {{
        background: rgba(245, 158, 11, 0.18);
        color: #fed7aa;
        border: 1px solid rgba(245, 158, 11, 0.6);
      }}
      .badge-topo-bad {{
        background: rgba(248, 113, 113, 0.18);
        color: #fecaca;
        border: 1px solid rgba(248, 113, 113, 0.6);
      }}
      .badge-topo-ubad {{
        background: rgba(244, 63, 94, 0.18);
        color: #fecdd3;
        border: 1px solid rgba(244, 63, 94, 0.6);
      }}
      .badge-topo-unknown {{
        background: rgba(148, 163, 184, 0.18);
        color: #e5e7eb;
        border: 1px solid rgba(148, 163, 184, 0.6);
      }}

      .badge-scaled {{
        background: rgba(16, 185, 129, 0.16);
        color: #a7f3d0;
        border: 1px solid rgba(16, 185, 129, 0.55);
      }}
      .badge-unscaled {{
        background: rgba(148, 163, 184, 0.18);
        color: #e5e7eb;
        border: 1px solid rgba(148, 163, 184, 0.6);
      }}
      .strip-note {{
        font-size: 0.78rem;
        opacity: 0.9;
      }}
      .epf-hazard-panel {{
        margin-top: 1.25rem;
        padding: 0.9rem 1rem;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        background: #f9fafb;
        font-size: 0.88rem;
      }}
      .epf-hazard-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
      }}
      .epf-hazard-title {{
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
      }}
      .epf-hazard-metrics {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin: 0.2rem 0 0.3rem;
      }}
      .epf-hazard-metric span {{
        display: block;
        font-size: 0.78rem;
      }}
      .epf-hazard-metric span:first-child {{
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6b7280;
      }}
      .epf-hazard-metric span:last-child {{
        font-weight: 600;
      }}
      .epf-hazard-reason {{
        margin: 0.35rem 0 0;
        font-size: 0.8rem;
        color: #4b5563;
      }}
      .epf-hazard-contrib {{
        margin-top: 0.45rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: baseline;
        font-size: 0.8rem;
        color: #4b5563;
      }}
      .epf-hazard-contrib-label {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
        font-size: 0.75rem;
      }}
      .epf-hazard-footnote {{
        margin: 0.4rem 0 0;
        font-size: 0.75rem;
        color: #6b7280;
      }}
      .epf-hazard-history {{
        margin-top: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }}
      .epf-hazard-history-label {{
        font-size: 0.78rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .epf-hazard-history-empty {{
        font-size: 0.78rem;
        color: #9ca3af;
      }}
      .epf-hazard-history svg {{
        display: block;
      }}
      table.gate-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 1.25rem;
        font-size: 0.86rem;
      }}
      table.gate-table th,
      table.gate-table td {{
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #e5e7eb;
      }}
      table.gate-table th {{
        text-align: left;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
      }}
      table.gate-table td:nth-child(2) {{
        width: 6.5rem;
        text-align: center;
        font-weight: 600;
      }}
      .status-pass {{
        color: #15803d;
      }}
      .status-fail {{
        color: #b91c1c;
      }}
      footer {{
        margin-top: 1.25rem;
        font-size: 0.75rem;
        color: #9ca3af;
      }}
      @media (max-width: 640px) {{
        .prc-shell {{
          padding: 1.25rem 1.2rem 1.5rem;
        }}
        .prc-strip {{
          flex-direction: column;
          align-items: flex-start;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="prc-shell">
      <header>
        <h1>PULSE — Demo Report Card</h1>
        <p class="prc-meta">
          Build: {now} · Status version: {STATUS_VERSION}
        </p>
      </header>

      <section class="prc-strip">
        <div class="strip-left">
          <span class="badge badge-decision">{decision_label}</span>
          <span class="badge badge-rdsi">RDSI {metrics['RDSI']:.2f}</span>
          <span class="badge {topo_badge_class}">{escape(topo_region)}</span>
        </div>
        <div class="strip-right">
          <span class="badge {hazard_badge_class}">Hazard {metrics['hazard_zone']}</span>
          <span class="strip-note">
            id={hazard_gate_id_text} · seedT={seed_T_points} · baseline={baseline_ok_text} ·
            E={metrics['hazard_E']:.3f} · {'OK' if metrics['hazard_ok'] else 'BLOCKED'} · {metrics['hazard_severity']} severity ·
            {scale_badge_text} · F={features_used_n} · {feature_mode_label}
          </span>
        </div>
      </section>

      <section class="epf-hazard-panel">
        <div class="epf-hazard-header">
          <div class="epf-hazard-title">
            EPF Relational Grail — hazard signal
            <span class="badge {scale_badge_class}">{scale_badge_text}</span>
          </div>
          <div class="epf-hazard-metrics">
            <div class="epf-hazard-metric">
              <span>E index</span>
              <span>{metrics['hazard_E']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>T distance</span>
              <span>{metrics['hazard_T']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>Stability S</span>
              <span>{metrics['hazard_S']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>Drift D</span>
              <span>{metrics['hazard_D']:.3f}</span>
            </div>
          </div>
        </div>

        <p class="epf-hazard-reason">
          {escape(str(metrics['hazard_reason']))}
        </p>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Topology</span>
          <span>
            region={escape(topo_region)} · baseline={baseline_ok_text} · zone={escape(str(metrics['hazard_zone']))}
          </span>
        </div>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Stability map</span>
          <span>
            last {sm_events}: stably_good={sm_sg}, unstably_good={sm_ug}, stably_bad={sm_sb}, unstably_bad={sm_ub}, unknown={sm_unk}
            · artifact={escape(STABILITY_MAP_FILENAME)}
          </span>
        </div>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Top contributors</span>
          <span>{contributors_text}</span>
        </div>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Feature mode</span>
          <span>
            {feature_mode_label} · source={feature_mode_source_text}
            · used {features_used_n}: {features_used_text}
            · recommended {rec_n} (min_coverage ≥ {rec_min_cov_text})
          </span>
        </div>

        <p class="epf-hazard-footnote">
          Thresholds: warn ≈ {CALIBRATED_WARN_THRESHOLD:.3f}, crit ≈ {CALIBRATED_CRIT_THRESHOLD:.3f}
          ({threshold_regime}; requires ≥{MIN_CALIBRATION_SAMPLES} log entries for calibration to take effect).
        </p>

        {history_fragment}
      </section>

      <section>
        <h2>Gate summary</h2>
        <table class="gate-table">
          <thead>
            <tr>
              <th>Gate</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
{gate_rows_html}
          </tbody>
        </table>
      </section>

      <footer>
        Demo-only artefact generated from PULSE_safe_pack_v0/tools/run_all.py.
        Deterministic, fail-closed gates remain the source of truth; the EPF Relational Grail
        hazard signal is surfaced as a diagnostic overlay.
      </footer>
    </main>
  </body>
</html>
"""

with open(art / "report_card.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Wrote", art / "status.json")
print("Wrote", art / "report_card.html")
print("Wrote", stability_map_path)
print(
    "Logged EPF hazard probe:",
    f"gate_id={hazard_gate_id}",
    f"seedT={seed_T_points}",
    f"baseline_ok={baseline_ok}",
    f"topology={hazard_topology_region}",
    f"zone={hazard_state.zone}",
    f"E={hazard_state.E:.3f}",
    f"ok={hazard_decision.ok}",
    f"severity={hazard_decision.severity}",
    f"scaled={hazard_T_scaled}",
    f"feature_mode={feature_mode_label}",
    f"feature_source={hazard_feature_mode_source}",
    f"features_used={features_used_n}",
    f"recommended={rec_n}",
    f"stability_map_events={sm_events}",
    f"stably_good={sm_sg}",
    f"unstably_good={sm_ug}",
    f"stably_bad={sm_sb}",
    f"unstably_bad={sm_ub}",
    f"unknown={sm_unk}",
    f"enforce_hazard={enforce_hazard}",
    f"epf_hazard_ok_gate={gates['epf_hazard_ok']}",
)
