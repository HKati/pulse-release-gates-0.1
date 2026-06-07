#!/usr/bin/env python3
"""
Run all PULSE safe-pack checks and generate core artifacts.

This script is the main entrypoint for the PULSE_safe_pack_v0 "safe pack".
It orchestrates the configured checks/profiles and produces the baseline
status.json and related artifacts under the pack's artifacts directory,
which are then consumed by CI workflows and reporting tools.
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Optional, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.render_quality_ledger import (  # noqa: E402
    write_quality_ledger,
)

# Allow tests / callers to override artifact output directory.
# Default remains pack_root/artifacts to preserve existing behavior.
ART_DIR_ENV = os.getenv("PULSE_ARTIFACT_DIR")
art = pathlib.Path(ART_DIR_ENV) if ART_DIR_ENV else (ROOT / "artifacts")
art.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().isoformat() + "Z"

SUPPORTED_MODES = ("demo", "core", "prod")


def _sha256_file(p: pathlib.Path) -> str | None:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


parser = argparse.ArgumentParser(add_help=True)

_env_raw = os.getenv("PULSE_RUN_MODE")
_env_mode = _env_raw.strip().lower() if isinstance(_env_raw, str) and _env_raw.strip() else None

if _env_mode is not None and _env_mode not in SUPPORTED_MODES:
    parser.error(
        f"Invalid PULSE_RUN_MODE='{_env_raw}'. Expected one of: {', '.join(SUPPORTED_MODES)}"
    )

_default_mode = _env_mode or "demo"

parser.add_argument(
    "--mode",
    type=str.lower,
    choices=list(SUPPORTED_MODES),
    default=_default_mode,
    help="Run profile: demo|core|prod (default: PULSE_RUN_MODE or demo)",
)

# Accept existing workflow args (may be used for provenance even if pack is self-contained)
parser.add_argument("--pack_dir", default=str(ROOT))
parser.add_argument("--gate_policy", default=str(REPO_ROOT / "pulse_gate_policy_v0.yml"))


def _env_flag(name: str) -> bool:
    raw = os.getenv(name)
    if not isinstance(raw, str):
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


parser.add_argument(
    "--release-grade-materialized",
    action="store_true",
    default=_env_flag("PULSE_RELEASE_GRADE_MATERIALIZED"),
    help=(
        "Explicit prod-only preparation path for non-stubbed release-grade "
        "materialization. Without this opt-in, prod fails closed."
    ),
)
args, _unknown = parser.parse_known_args()


RUN_MODE = str(args.mode).strip().lower()
RELEASE_GRADE_MATERIALIZED = bool(args.release_grade_materialized)

if RELEASE_GRADE_MATERIALIZED and RUN_MODE != "prod":
    parser.error("--release-grade-materialized is prod-only")
if RUN_MODE == "demo":
    STATUS_VERSION = "1.0.0-demo"
elif RUN_MODE == "core":
    STATUS_VERSION = "1.0.0-core"
else:
    STATUS_VERSION = "1.0.0"


# Stability Map artefact (additive)
STABILITY_MAP_SCHEMA_V0 = "epf_stability_map_v0"
STABILITY_MAP_FILENAME = "epf_stability_map_v0.json"


def write_json_artifact(path: pathlib.Path, payload: dict) -> None:
    """
    Deterministic JSON artifact writer (sort_keys + indent).
    Fail-closed is not desired here: this is diagnostic output.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


AUDIT_BUNDLE_DIRNAME = "release_authority_audit_bundle"

CANONICAL_EXTERNAL_SUMMARY_STEMS = {
    "llamaguard_summary",
    "promptguard_summary",
    "garak_summary",
    "azure_eval_summary",
    "promptfoo_summary",
    "deepeval_summary",
}


def fail_closed(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)



def external_summary_files(art_dir: pathlib.Path) -> list[pathlib.Path]:
    external_dir = art_dir / "external"
    if not external_dir.exists():
        return []

    out: list[pathlib.Path] = []
    for p in sorted(external_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix not in {".json", ".jsonl"}:
            continue
        if p.stem in CANONICAL_EXTERNAL_SUMMARY_STEMS:
            out.append(p)
    return out



def materialize_release_grade_inputs(
    art_dir: pathlib.Path,
) -> tuple[dict[str, bool], dict[str, Any], dict[str, Any]]:
    """Fail closed until a trusted release-evidence verifier is wired.

    SECURITY HOTFIX:
    Release-required gates must not be derived from local, self-declared
    artifact-directory inputs. Local detector manifests, generic external
    summaries, and refusal-delta summaries may be diagnostic inputs, but they
    cannot materialize normative release-required gates until a verifier binds
    identity, provenance, policy, subject, and raw evidence.
    """
    self_declared_artifacts: list[str] = []

    for path in (
        art_dir / "detector_materialization_v0.json",
        art_dir / "refusal_delta_summary.json",
    ):
        if path.exists():
            self_declared_artifacts.append(path.name)

    for path in external_summary_files(art_dir):
        try:
            self_declared_artifacts.append(str(path.relative_to(art_dir)))
        except ValueError:
            self_declared_artifacts.append(str(path))

    suffix = (
        f" observed self-declared artifacts: {', '.join(self_declared_artifacts)}."
        if self_declared_artifacts
        else " no verified release evidence artifacts were found."
    )

    fail_closed(
        "release-grade materialized prod is disabled until a trusted recorded "
        "release-evidence verifier is implemented; local detector, external "
        "summary, and refusal-delta artifacts cannot set release-required gates "
        f"true.{suffix}"
    )


def build_release_authority_manifest(status_path: pathlib.Path) -> pathlib.Path:
    out_path = art / "release_authority_v0.json"
    builder = ROOT / "tools" / "build_release_authority_manifest_v0.py"
    registry = REPO_ROOT / "pulse_gate_registry_v0.yml"
    evaluator = ROOT / "tools" / "check_gates.py"

    cmd = [
        sys.executable,
        str(builder),
        "--status",
        str(status_path),
        "--policy",
        str(pathlib.Path(str(args.gate_policy))),
        "--registry",
        str(registry),
        "--evaluator",
        str(evaluator),
        "--policy-set",
        "required+release_required",
        "--run-mode",
        "prod",
        "--out",
        str(out_path),
    ]

    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        fail_closed(
            "release authority manifest build failed:\n"
            f"{result.stdout}\n{result.stderr}"
        )

    if not out_path.exists():
        fail_closed(f"release authority manifest was not written: {out_path}")

    return out_path


def write_release_authority_audit_bundle(
    *,
    status_path: pathlib.Path,
    report_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> pathlib.Path:
    bundle = art / AUDIT_BUNDLE_DIRNAME
    bundle.mkdir(parents=True, exist_ok=True)

    for src in (status_path, report_path, manifest_path):
        if not src.exists():
            fail_closed(f"cannot build audit bundle; missing artifact: {src}")
        shutil.copy2(src, bundle / src.name)

    return bundle


from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (  # noqa: E402
    HazardRuntimeState,
    probe_hazard_and_append_log,
)
from PULSE_safe_pack_v0.epf.epf_hazard_policy import (  # noqa: E402
    HazardGateConfig,
    evaluate_hazard_gate,
)
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (  # noqa: E402
    CALIBRATED_CRIT_THRESHOLD,
    CALIBRATED_WARN_THRESHOLD,
    DEFAULT_CRIT_THRESHOLD,
    DEFAULT_WARN_THRESHOLD,
    MIN_CALIBRATION_SAMPLES,
)

# Calibration path: prefer same filename inside the selected artifacts dir, if present.
try:
    from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (  # noqa: E402
        CALIBRATION_PATH as _HAZARD_CALIB_PATH_DEFAULT,
    )
except Exception:  # pragma: no cover
    _HAZARD_CALIB_PATH_DEFAULT = ROOT / "artifacts" / "epf_hazard_thresholds_v0.json"

_hazard_calib_candidate = art / pathlib.Path(_HAZARD_CALIB_PATH_DEFAULT).name
HAZARD_CALIB_PATH = (
    _hazard_calib_candidate
    if _hazard_calib_candidate.exists()
    else pathlib.Path(_HAZARD_CALIB_PATH_DEFAULT)
)


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


def classify_topology_region(*, baseline_ok: bool, hazard_zone: str) -> str:
    """
    Field topology region (diagnostic overlay):
      - stably_good / unstably_good / stably_bad / unstably_bad / unknown

    Stable is GREEN; anything else is "unstable" (AMBER/RED).
    """
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
# Helpers for EPF hazard history / context
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

BASE_GATES = {
    "pass_controls_refusal": True,
    "effect_present": True,
    "refusal_delta_evidence_present": False,
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

release_grade_metric_overrides: dict[str, Any] = {}
release_grade_external_section: dict[str, Any] = {}

if RUN_MODE in ("demo", "core"):
    gates = dict(BASE_GATES)  # smoke lanes
else:
    if not RELEASE_GRADE_MATERIALIZED:
        fail_closed(
            "prod mode is fail-closed without explicit "
            "--release-grade-materialized / "
            "PULSE_RELEASE_GRADE_MATERIALIZED=1"
        )
    gates = {k: False for k in BASE_GATES.keys()}
    (
        release_grade_gate_overrides,
        release_grade_metric_overrides,
        release_grade_external_section,
    ) = materialize_release_grade_inputs(art)
    gates.update(release_grade_gate_overrides)

metrics = {
    "RDSI": 0.92 if RUN_MODE in ("demo", "core") else 0.0,
    "rdsi_note": (
        "Demo value for CI smoke-run"
        if RUN_MODE == "demo"
        else "Core CI smoke-run"
        if RUN_MODE == "core"
        else "PROD placeholder: baseline gates are fail-closed until detectors are wired"
    ),
    "build_time": now,
}

if release_grade_metric_overrides:
    metrics.update(release_grade_metric_overrides)

metrics["run_mode"] = RUN_MODE

gp = pathlib.Path(str(args.gate_policy))
metrics["gate_policy_path"] = str(gp)
h = _sha256_file(gp) if gp.exists() else None
if h:
    metrics["gate_policy_sha256"] = h


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
hazard_feature_keys, hazard_feature_mode_source, hazard_feature_mode_active = (
    load_last_hazard_feature_context(
        hazard_log_path,
        gate_id=hazard_gate_id,
    )
)
metrics["hazard_feature_keys"] = hazard_feature_keys
metrics["hazard_feature_count"] = int(len(hazard_feature_keys))
metrics["hazard_feature_mode_source"] = str(hazard_feature_mode_source)
metrics["hazard_feature_mode_active"] = bool(hazard_feature_mode_active)
feature_mode_label = "ON" if bool(hazard_feature_mode_active) else "OFF"

# Calibration recommendation summary (if present)
calib_summary = load_calibration_recommendation(pathlib.Path(HAZARD_CALIB_PATH))
metrics["hazard_recommended_count"] = int(calib_summary.get("recommended_count", 0) or 0)
metrics["hazard_recommend_min_coverage"] = calib_summary.get("min_coverage")
metrics["hazard_recommend_max_features"] = calib_summary.get("max_features")
metrics["hazard_feature_allowlist_count"] = int(
    calib_summary.get("feature_allowlist_count", 0) or 0
)

# E-history for Stability Map artefact
E_history = load_hazard_E_history(hazard_log_path, max_points=20, gate_id=hazard_gate_id)

# Threshold regime label (for UI + Stability Map)
calib_is_effective = (
    CALIBRATED_WARN_THRESHOLD != DEFAULT_WARN_THRESHOLD
    or CALIBRATED_CRIT_THRESHOLD != DEFAULT_CRIT_THRESHOLD
)
threshold_regime = "CALIBRATED" if calib_is_effective else "BASELINE"

# ---------------------------------------------------------------------------
# Stability Map artefact (v0)
# ---------------------------------------------------------------------------

seed_T_points = int(metrics.get("hazard_seed_T_points", 0) or 0)
features_used_n = int(metrics.get("hazard_feature_count", 0) or 0)
rec_n = int(metrics.get("hazard_recommended_count", 0) or 0)
rec_min_cov = metrics.get("hazard_recommend_min_coverage")
rec_max_feats = metrics.get("hazard_recommend_max_features")

stability_map_payload = {
    "schema": STABILITY_MAP_SCHEMA_V0,
    "created_utc": now,
    "status_version": STATUS_VERSION,
    "gate_id": str(hazard_gate_id),
    "baseline_ok": bool(baseline_ok),
    "topology_region": str(hazard_topology_region),
    "hazard": {
        "zone": str(hazard_state.zone),
        "E": float(hazard_state.E),
        "T": float(hazard_state.T),
        "S": float(hazard_state.S),
        "D": float(hazard_state.D),
        "reason": str(hazard_state.reason),
        "ok": bool(hazard_decision.ok),
        "severity": str(hazard_decision.severity),
        "T_scaled": bool(hazard_T_scaled),
        "contributors_top": hazard_contributors_top,
    },
    "series": {
        "seed_T_points": int(seed_T_points),
        "history_E": list(E_history),
        # hazard_runtime.history_T already includes seeds + current T (adapter appends).
        "history_T": list((hazard_runtime.history_T or [])[-20:]),
    },
    "feature_mode": {
        "active": bool(hazard_feature_mode_active),
        "source": str(hazard_feature_mode_source),
        "used_feature_count": int(features_used_n),
        "used_feature_keys": list(hazard_feature_keys),
        "recommended_count": int(rec_n),
        "recommend_min_coverage": (
            float(rec_min_cov) if isinstance(rec_min_cov, (int, float)) else None
        ),
        "recommend_max_features": int(rec_max_feats) if isinstance(rec_max_feats, int) else None,
    },
    "thresholds": {
        "regime": str(threshold_regime),
        "warn": float(CALIBRATED_WARN_THRESHOLD),
        "crit": float(CALIBRATED_CRIT_THRESHOLD),
        "baseline_warn": float(DEFAULT_WARN_THRESHOLD),
        "baseline_crit": float(DEFAULT_CRIT_THRESHOLD),
        "min_samples": int(MIN_CALIBRATION_SAMPLES),
    },
    "provenance": {
        "run_key": str(run_key) if run_key else None,
        "git_sha": str(git_sha) if git_sha else None,
        "artifact_dir": str(art),
    },
}

stability_map_path = art / STABILITY_MAP_FILENAME
write_json_artifact(stability_map_path, stability_map_payload)

# Keep status metrics additive and safely excluded from field snapshots (hazard_* prefix).
metrics["hazard_stability_map_written"] = True
metrics["hazard_stability_map_schema"] = STABILITY_MAP_SCHEMA_V0
metrics["hazard_stability_map_path"] = str(stability_map_path)

# ---------------------------------------------------------------------------
# Shadow hazard gate (ENV-flag-enforceable)
# ---------------------------------------------------------------------------

enforce_hazard = os.getenv("EPF_HAZARD_ENFORCE", "0") == "1"
if enforce_hazard:
    gates["epf_hazard_ok"] = hazard_decision.ok
else:
    gates["epf_hazard_ok"] = True

if RUN_MODE in ("demo", "core"):
    stub_profile = "all_true_smoke"
    gates_stubbed = True
    gates["detectors_materialized_ok"] = False
    diagnostics = {
        "scaffold": True,
        "gates_stubbed": gates_stubbed,
        "stub_profile": stub_profile,
    }
else:
    stub_profile = "not_stubbed"
    gates_stubbed = False
    gates["detectors_materialized_ok"] = gates.get("detectors_materialized_ok") is True
    diagnostics = {
        "scaffold": False,
        "gates_stubbed": False,
        "stub_profile": stub_profile,
    }

status = {
    "version": STATUS_VERSION,
    "created_utc": now,
    "gates": gates,
    "metrics": metrics,
    "diagnostics": diagnostics,
}

if release_grade_external_section:
    status["external"] = release_grade_external_section

status_path = art / "status.json"
write_json_artifact(status_path, status)

# ---------------------------------------------------------------------------
# HTML report card via Quality Ledger renderer
# ---------------------------------------------------------------------------

report_card_path = art / "report_card.html"
write_quality_ledger(status_path, report_card_path)

release_authority_manifest_path: pathlib.Path | None = None
release_authority_bundle_path: pathlib.Path | None = None

if RELEASE_GRADE_MATERIALIZED:
    release_authority_manifest_path = build_release_authority_manifest(status_path)
    release_authority_bundle_path = write_release_authority_audit_bundle(
        status_path=status_path,
        report_path=report_card_path,
        manifest_path=release_authority_manifest_path,
    )

print("Wrote", status_path)
print("Wrote", report_card_path)
if release_authority_manifest_path is not None:
    print("Wrote", release_authority_manifest_path)
if release_authority_bundle_path is not None:
    print("Wrote", release_authority_bundle_path)
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
    f"enforce_hazard={enforce_hazard}",
    f"epf_hazard_ok_gate={gates['epf_hazard_ok']}",
)
