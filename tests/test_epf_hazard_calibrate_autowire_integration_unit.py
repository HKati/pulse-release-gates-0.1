import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf import epf_hazard_adapter as adapter
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import HazardConfig


def _write_jsonl_log(path: pathlib.Path, n: int = 25) -> None:
    """
    Write a minimal epf_hazard_log.jsonl compatible stream.

    - Always includes snapshot_current with keys a,b
    - Key c is missing in last 5 entries to force coverage < 1.0 (and below 1.0 threshold)
    """
    lines = []
    for i in range(n):
        snap = {
            "a": float(i + 1),
            "b": float((i + 1) * 2),
        }
        # Make 'c' present only for first 20 -> coverage = 20/25 = 0.8
        if i < 20:
            snap["c"] = float((i + 1) * 3)

        ev = {
            "gate_id": "G1",
            "timestamp": "2025-01-01T00:00:00Z",
            "hazard": {"E": float(i) / float(max(1, n - 1))},
            "snapshot_current": snap,
        }
        lines.append(json.dumps(ev, sort_keys=True))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_end_to_end_calibrate_then_autowire_uses_recommended_features(monkeypatch, tmp_path):
    log_path = tmp_path / "epf_hazard_log.jsonl"
    out_json = tmp_path / "epf_hazard_thresholds_v0.json"

    _write_jsonl_log(log_path, n=25)

    calibrator = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "epf_hazard_calibrate.py"
    assert calibrator.exists(), f"missing calibrator script: {calibrator}"

    # Run the real CLI (integration style) so we validate actual execution.
    # - min_samples=20 (matches adapter MIN_CALIBRATION_SAMPLES default)
    # - recommend_min_coverage=1.0 => only features with perfect coverage are recommended
    cmd = [
        sys.executable,
        str(calibrator),
        "--log",
        str(log_path),
        "--out-json",
        str(out_json),
        "--min-samples",
        "20",
        "--warn-p",
        "0.85",
        "--crit-p",
        "0.97",
        "--recommend-min-coverage",
        "1.0",
        "--recommend-max-features",
        "64",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"calibrator failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    data = json.loads(out_json.read_text(encoding="utf-8"))

    # Artifact should include these new Step-4 fields.
    assert "feature_coverage" in data
    assert "recommended_features" in data
    assert isinstance(data["recommended_features"], list)

    # With coverage threshold 1.0:
    # - a,b present in all 25 entries -> recommended
    # - c present only 20/25 -> not recommended
    assert data["recommended_features"] == ["a", "b"]

    # Now point the adapter to this artifact and autowire.
    monkeypatch.setattr(adapter, "CALIBRATION_PATH", out_json)

    cfg = HazardConfig()
    adapter._maybe_enable_feature_mode_from_calibration(
        cfg,
        current_snapshot={"a": 1.0, "b": 2.0, "c": 3.0},
        reference_snapshot={"a": 0.0, "b": 0.0, "c": 0.0},
        feature_allowlist=None,
    )

    keys = [fs.key for fs in (getattr(cfg, "feature_specs", []) or [])]
    assert keys == ["a", "b"]
