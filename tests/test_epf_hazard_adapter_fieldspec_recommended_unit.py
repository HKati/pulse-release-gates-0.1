import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf import epf_hazard_adapter as adapter
from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (
    HazardRuntimeState,
    probe_hazard_and_append_log,
    LOG_FILENAME_DEFAULT,
)
from PULSE_safe_pack_v0.epf.epf_hazard_field_spec import FieldSpecArtifactV0
from PULSE_safe_pack_v0.epf.epf_hazard_features import RobustScaler, FeatureScalersArtifactV0


def _read_last_log_entry(log_dir: pathlib.Path) -> dict:
    p = log_dir / LOG_FILENAME_DEFAULT
    text = p.read_text(encoding="utf-8").strip()
    assert text, "expected hazard JSONL log to be non-empty"
    last = text.splitlines()[-1]
    return json.loads(last)


def test_fieldspec_defaults_snapshot_logging_and_deny(tmp_path: pathlib.Path):
    # Create FieldSpec v0 artifact: explicit Grail coordinates + deny key.
    fs_path = tmp_path / "epf_hazard_field_spec_v0.json"
    fs = FieldSpecArtifactV0(
        features=["metrics.RDSI", "external.fail_rate"],
        deny_keys=["external.secret"],
        notes="unit test",
    )
    fs.save_json(fs_path)

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    runtime = HazardRuntimeState.empty()

    current_snapshot = {
        "metrics": {"RDSI": 0.92, "other": 123},
        "external": {"fail_rate": 0.1, "secret": 777},
        "junk": 1,
    }
    reference_snapshot = {
        "metrics": {"RDSI": 1.0, "other": 0},
        "external": {"fail_rate": 0.0, "secret": 0},
        "junk": 0,
    }
    stability_metrics = {"RDSI": 0.92}

    probe_hazard_and_append_log(
        gate_id="T_fieldspec_defaults",
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        stability_metrics=stability_metrics,
        runtime_state=runtime,
        log_dir=run_dir,
        field_spec_path=fs_path,
        # keep defaults: log_snapshots=True and no explicit snapshot policy
    )

    entry = _read_last_log_entry(run_dir)

    # FieldSpec provenance attached.
    assert entry["hazard"].get("field_spec_used") is True
    assert "field_spec_path" in entry["hazard"]

    # Snapshot is constrained to FieldSpec coordinates, and deny key is honored.
    snap = entry.get("snapshot_current") or {}
    assert "junk" not in snap
    assert "metrics" in snap and "RDSI" in snap["metrics"]
    assert "other" not in snap["metrics"]
    assert "external" in snap and "fail_rate" in snap["external"]
    assert "secret" not in snap["external"]

    # Snapshot meta includes policy + FieldSpec summary.
    sm = entry.get("snapshot_meta") or {}
    assert "field_spec" in sm
    assert sm["field_spec"].get("features_count") == 2
    assert sm["field_spec"].get("deny_keys_count") == 1

    cur_meta = sm.get("current") or {}
    policy = cur_meta.get("policy") or {}
    assert "metrics.RDSI" in (policy.get("allowed_prefixes") or [])
    assert "external.fail_rate" in (policy.get("allowed_prefixes") or [])
    assert "external.secret" in (policy.get("deny_keys") or [])


def test_autowire_honors_recommended_features(monkeypatch, tmp_path: pathlib.Path):
    # Build a calibration artifact with scalers for 3 keys.
    scalers = {
        "a.b": RobustScaler.fit([0.0, 1.0, 2.0, 3.0]),
        "x.y": RobustScaler.fit([0.0, 1.0, 2.0, 3.0]),
        "m.n": RobustScaler.fit([0.0, 1.0, 2.0, 3.0]),
    }
    artifact = FeatureScalersArtifactV0(
        count=int(adapter.MIN_CALIBRATION_SAMPLES),
        missing={},
        features=scalers,
    )

    cal_path = tmp_path / "epf_hazard_thresholds_v0.json"

    # Case A: recommended_features limits autowire to only "a.b".
    payload_a = {
        "feature_scalers": artifact.to_dict(),
        "recommended_features": ["a.b"],
    }
    cal_path.write_text(json.dumps(payload_a), encoding="utf-8")
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    run_a = tmp_path / "run_a"
    run_a.mkdir(parents=True, exist_ok=True)

    runtime = HazardRuntimeState.empty()
    current_snapshot = {"a": {"b": 1.0}, "x": {"y": 2.0}, "m": {"n": 3.0}}
    reference_snapshot = {"a": {"b": 0.0}, "x": {"y": 0.0}, "m": {"n": 0.0}}
    stability_metrics = {"RDSI": 1.0}

    probe_hazard_and_append_log(
        gate_id="T_recommended_features",
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        stability_metrics=stability_metrics,
        runtime_state=runtime,
        log_dir=run_a,
        cfg=None,  # trigger autowire
        field_spec_path=tmp_path / "missing_fieldspec.json",  # ensure no FieldSpec defaulting
    )

    entry_a = _read_last_log_entry(run_a)
    assert entry_a["hazard"]["feature_mode_active"] is True
    assert entry_a["hazard"]["feature_mode_source"] == "calibration_autowire"
    assert entry_a["hazard"]["feature_keys"] == ["a.b"]

    # Case B: explicit empty recommended_features means deny-all -> no feature mode.
    payload_b = {
        "feature_scalers": artifact.to_dict(),
        "recommended_features": [],
    }
    cal_path.write_text(json.dumps(payload_b), encoding="utf-8")

    run_b = tmp_path / "run_b"
    run_b.mkdir(parents=True, exist_ok=True)

    runtime2 = HazardRuntimeState.empty()
    probe_hazard_and_append_log(
        gate_id="T_recommended_empty",
        current_snapshot=current_snapshot,
        reference_snapshot=reference_snapshot,
        stability_metrics=stability_metrics,
        runtime_state=runtime2,
        log_dir=run_b,
        cfg=None,
        field_spec_path=tmp_path / "missing_fieldspec.json",
    )

    entry_b = _read_last_log_entry(run_b)
    assert entry_b["hazard"]["feature_mode_active"] is False
    assert entry_b["hazard"]["feature_keys"] == []
    assert entry_b["hazard"]["feature_mode_source"] == "none"
