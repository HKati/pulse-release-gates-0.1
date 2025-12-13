import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf import epf_hazard_adapter as adapter
from PULSE_safe_pack_v0.epf.epf_hazard_features import RobustScaler, FeatureScalersArtifactV0
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import HazardConfig


def _make_scalers(keys):
    vals = [float(i) for i in range(1, 30)]
    return {k: RobustScaler.fit(vals) for k in keys}


def _write_calibration(tmp_path: pathlib.Path, payload: dict) -> pathlib.Path:
    p = tmp_path / "epf_hazard_thresholds_v0.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_source_recommended_features(monkeypatch, tmp_path):
    scalers = _make_scalers(["a", "b"])
    artifact = FeatureScalersArtifactV0(count=25, missing={"a": 0, "b": 0}, features=scalers)
    cal_path = _write_calibration(
        tmp_path,
        {"feature_scalers": artifact.to_dict(), "recommended_features": ["b"]},
    )
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0},
        reference_snapshot={"a": 0.0, "b": 0.0},
        feature_allowlist=None,
    )

    assert getattr(cfg, "feature_mode_source", None) == "recommended_features"
    assert [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])] == ["b"]
    assert bool(getattr(cfg, "feature_mode_active", False)) is True


def test_source_artifact_allowlist_overrides_recommended(monkeypatch, tmp_path):
    scalers = _make_scalers(["a", "b"])
    artifact = FeatureScalersArtifactV0(count=25, missing={"a": 0, "b": 0}, features=scalers)
    cal_path = _write_calibration(
        tmp_path,
        {
            "feature_scalers": artifact.to_dict(),
            "feature_allowlist": ["a"],
            "recommended_features": ["b"],
        },
    )
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0},
        reference_snapshot={"a": 0.0, "b": 0.0},
        feature_allowlist=None,
    )

    assert getattr(cfg, "feature_mode_source", None) == "artifact_allowlist"
    assert [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])] == ["a"]


def test_source_runtime_allowlist(monkeypatch, tmp_path):
    scalers = _make_scalers(["a", "b"])
    artifact = FeatureScalersArtifactV0(count=25, missing={"a": 0, "b": 0}, features=scalers)
    cal_path = _write_calibration(
        tmp_path,
        {"feature_scalers": artifact.to_dict(), "recommended_features": ["b"]},
    )
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0},
        reference_snapshot={"a": 0.0, "b": 0.0},
        feature_allowlist=["a"],
    )

    assert getattr(cfg, "feature_mode_source", None) == "runtime_allowlist"
    assert [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])] == ["a"]


def test_source_runtime_and_artifact_intersection_disjoint_denies(monkeypatch, tmp_path):
    scalers = _make_scalers(["a", "b"])
    artifact = FeatureScalersArtifactV0(count=25, missing={"a": 0, "b": 0}, features=scalers)
    cal_path = _write_calibration(
        tmp_path,
        {"feature_scalers": artifact.to_dict(), "feature_allowlist": ["a"]},
    )
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0},
        reference_snapshot={"a": 0.0, "b": 0.0},
        feature_allowlist=["b"],  # disjoint with artifact_allowlist=["a"]
    )

    assert getattr(cfg, "feature_mode_source", None) == "runtime_and_artifact_allowlist"
    assert (getattr(cfg, "feature_specs", None) in (None, []))
    assert bool(getattr(cfg, "feature_mode_active", False)) is False


def test_source_snapshot_intersection_fallback(monkeypatch, tmp_path):
    scalers = _make_scalers(["a", "b"])
    artifact = FeatureScalersArtifactV0(count=25, missing={"a": 0, "b": 0}, features=scalers)
    cal_path = _write_calibration(tmp_path, {"feature_scalers": artifact.to_dict()})
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", cal_path)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0},
        reference_snapshot={"a": 0.0, "b": 0.0},
        feature_allowlist=None,
    )

    assert getattr(cfg, "feature_mode_source", None) == "snapshot_intersection"
    assert [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])] == ["a", "b"]
