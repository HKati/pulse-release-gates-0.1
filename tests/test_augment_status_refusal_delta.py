import json
import subprocess
import sys
from pathlib import Path


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def run_augment_status(status_path: Path, thresholds_path: Path, external_dir: Path):
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--status",
            str(status_path),
            "--thresholds",
            str(thresholds_path),
            "--external_dir",
            str(external_dir),
        ],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    return result


def test_refusal_delta_summary_sets_metrics_and_gate(tmp_path: Path):
    """
    If refusal_delta_summary.json is present, augment_status should copy its
    fields into metrics.* and set the refusal_delta_pass gate accordingly.
    """
    pack_dir = tmp_path / "pack"
    artifacts_dir = pack_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    status_path = artifacts_dir / "status.json"
    write_json(status_path, {})

    thresholds_path = pack_dir / "thresholds.json"
    write_json(thresholds_path, {})

    external_dir = pack_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "n": 100,
        "delta": 0.05,
        "ci_low": 0.02,
        "ci_high": 0.08,
        "policy": "balanced",
        "delta_min": 0.10,
        "delta_strict": 0.20,
        "p_mcnemar": 0.01,
        "pass_min": True,
        "pass_strict": False,
        "pass": True,
    }
    write_json(artifacts_dir / "refusal_delta_summary.json", summary)

    run_augment_status(status_path, thresholds_path, external_dir)

    data = json.loads(status_path.read_text(encoding="utf-8"))
    metrics = data["metrics"]

    assert metrics["refusal_delta_n"] == 100
    assert metrics["refusal_delta"] == 0.05
    assert metrics["refusal_delta_ci_low"] == 0.02
    assert metrics["refusal_delta_ci_high"] == 0.08
    assert metrics["refusal_policy"] == "balanced"
    assert metrics["refusal_delta_min"] == 0.10
    assert metrics["refusal_delta_strict"] == 0.20
    assert metrics["refusal_p_mcnemar"] == 0.01
    assert metrics["refusal_pass_min"] is True
    assert metrics["refusal_pass_strict"] is False

    # Gate mirrors
    assert data["gates"]["refusal_delta_pass"] is True
    assert data["refusal_delta_pass"] is True


def test_refusal_delta_fail_closed_if_pairs_exist_and_no_summary(tmp_path: Path):
    """
    If real refusal_pairs.jsonl exists but no summary is present,
    augment_status should fail-closed (refusal_delta_pass = False).
    """
    pack_dir = tmp_path / "pack"
    artifacts_dir = pack_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    status_path = artifacts_dir / "status.json"
    write_json(status_path, {})

    thresholds_path = pack_dir / "thresholds.json"
    write_json(thresholds_path, {})

    external_dir = pack_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)

    # Presence of real pairs triggers fail-closed behaviour
    examples_dir = pack_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    (examples_dir / "refusal_pairs.jsonl").write_text("dummy\n", encoding="utf-8")

    run_augment_status(status_path, thresholds_path, external_dir)

    data = json.loads(status_path.read_text(encoding="utf-8"))

    assert data["gates"]["refusal_delta_pass"] is False
    assert data["refusal_delta_pass"] is False


def test_refusal_delta_pass_if_no_pairs_and_no_summary(tmp_path: Path):
    """
    If there is no summary and no real refusal_pairs.jsonl,
    augment_status should treat the gate as PASS by default.
    """
    pack_dir = tmp_path / "pack"
    artifacts_dir = pack_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    status_path = artifacts_dir / "status.json"
    write_json(status_path, {})

    thresholds_path = pack_dir / "thresholds.json"
    write_json(thresholds_path, {})

    external_dir = pack_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)

    # No artifacts/refusal_delta_summary.json and no examples/refusal_pairs.jsonl

    run_augment_status(status_path, thresholds_path, external_dir)

    data = json.loads(status_path.read_text(encoding="utf-8"))

    assert data["gates"]["refusal_delta_pass"] is True
    assert data["refusal_delta_pass"] is True
