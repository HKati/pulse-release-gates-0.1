from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "PULSE_safe_pack_v0" / "tools" / "build_release_authority_manifest_v0.py"
CHECKER = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_authority_manifest_v0.py"
SCHEMA = ROOT / "schemas" / "release_authority_v0.schema.json"


def write_status(tmp_path: Path, gates: dict[str, object], run_mode: str = "core") -> Path:
    status = {
        "version": "test",
        "created_utc": "2026-04-27T00:00:00Z",
        "metrics": {"run_mode": run_mode},
        "gates": gates,
    }
    path = tmp_path / "status.json"
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return path


def run_builder(tmp_path: Path, status: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    out = tmp_path / "release_authority_v0.json"
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--status",
            str(status),
            "--policy",
            str(ROOT / "pulse_gate_policy_v0.yml"),
            "--registry",
            str(ROOT / "pulse_gate_registry_v0.yml"),
            "--evaluator",
            str(ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"),
            "--out",
            str(out),
            "--created-utc",
            "2026-04-27T00:00:00Z",
            "--workflow-name",
            "PULSE CI",
            "--event-name",
            "pull_request",
            "--ref",
            "refs/pull/1/merge",
            "--git-sha",
            "0" * 40,
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--manifest",
            str(path),
            "--schema",
            str(SCHEMA),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "release_authority_v0.json").read_text(encoding="utf-8"))


def test_builds_core_pass_manifest(tmp_path: Path) -> None:
    status = write_status(
        tmp_path,
        {
            "pass_controls_refusal": True,
            "pass_controls_sanit": True,
            "sanitization_effective": True,
            "q1_grounded_ok": True,
            "q4_slo_ok": True,
        },
    )

    result = run_builder(tmp_path, status)
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["authority"]["policy_set"] == "core_required"
    assert manifest["decision"]["state"] == "PASS"
    assert manifest["evaluation"]["failed_required_gates"] == []
    assert manifest["evaluation"]["missing_required_gates"] == []

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


def test_builds_missing_gate_fail_closed_manifest(tmp_path: Path) -> None:
    status = write_status(
        tmp_path,
        {
            "pass_controls_refusal": True,
            "pass_controls_sanit": True,
            "sanitization_effective": True,
            "q1_grounded_ok": True,
        },
    )

    result = run_builder(tmp_path, status)
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["decision"]["state"] == "FAIL"
    assert manifest["evaluation"]["missing_required_gates"] == ["q4_slo_ok"]
    assert "q4_slo_ok" not in manifest["evaluation"]["required_gate_results"]

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


def test_builds_failed_gate_fail_closed_manifest(tmp_path: Path) -> None:
    status = write_status(
        tmp_path,
        {
            "pass_controls_refusal": True,
            "pass_controls_sanit": True,
            "sanitization_effective": True,
            "q1_grounded_ok": True,
            "q4_slo_ok": False,
        },
    )

    result = run_builder(tmp_path, status)
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["decision"]["state"] == "FAIL"
    assert manifest["evaluation"]["failed_required_gates"] == ["q4_slo_ok"]
    assert manifest["evaluation"]["required_gate_results"]["q4_slo_ok"] is False

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


def test_builds_required_plus_release_required_manifest(tmp_path: Path) -> None:
    required_gates = [
        "pass_controls_refusal",
        "refusal_delta_pass",
        "effect_present",
        "psf_monotonicity_ok",
        "psf_mono_shift_resilient",
        "pass_controls_comm",
        "psf_commutativity_ok",
        "psf_comm_shift_resilient",
        "pass_controls_sanit",
        "sanitization_effective",
        "sanit_shift_resilient",
        "psf_action_monotonicity_ok",
        "psf_idempotence_ok",
        "psf_path_independence_ok",
        "psf_pii_monotonicity_ok",
        "q1_grounded_ok",
        "q2_consistency_ok",
        "q3_fairness_ok",
        "q4_slo_ok",
        "detectors_materialized_ok",
        "external_summaries_present",
        "external_all_pass",
    ]
    status = write_status(tmp_path, {gate: True for gate in required_gates}, run_mode="prod")

    result = run_builder(
        tmp_path,
        status,
        "--policy-set",
        "required+release_required",
        "--run-mode",
        "prod",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["run_identity"]["run_mode"] == "prod"
    assert manifest["authority"]["policy_set"] == "required+release_required"
    assert manifest["authority"]["release_required_materialized"] is True
    assert "external_all_pass" in manifest["authority"]["effective_required_gates"]
    assert manifest["decision"]["state"] == "PASS"

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr

def test_builds_all_required_missing_fail_closed_manifest(tmp_path: Path) -> None:
    status = write_status(tmp_path, {})

    result = run_builder(tmp_path, status)
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["decision"]["state"] == "FAIL"
    assert manifest["evaluation"]["required_gate_results"] == {}
    assert manifest["evaluation"]["missing_required_gates"] == [
        "pass_controls_refusal",
        "pass_controls_sanit",
        "sanitization_effective",
        "q1_grounded_ok",
        "q4_slo_ok",
    ]

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


def test_omits_empty_policy_version(tmp_path: Path) -> None:
    policy = tmp_path / "pulse_gate_policy_no_version.yml"
    policy.write_text(
        """
policy:
  id: pulse-gate-policy-v0

gates:
  core_required:
    - pass_controls_refusal
  advisory: []
""".lstrip(),
        encoding="utf-8",
    )
    status = write_status(tmp_path, {"pass_controls_refusal": True})

    result = run_builder(
        tmp_path,
        status,
        "--policy",
        str(policy),
        "--policy-set",
        "core_required",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["inputs"]["gate_policy"]["policy_id"] == "pulse-gate-policy-v0"
    assert "version" not in manifest["inputs"]["gate_policy"]

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


def test_preserves_numeric_zero_policy_version(tmp_path: Path) -> None:
    policy = tmp_path / "pulse_gate_policy_zero_version.yml"
    policy.write_text(
        """
policy:
  id: pulse-gate-policy-v0
  version: 0

gates:
  core_required:
    - pass_controls_refusal
  advisory: []
""".lstrip(),
        encoding="utf-8",
    )
    status = write_status(tmp_path, {"pass_controls_refusal": True})

    result = run_builder(
        tmp_path,
        status,
        "--policy",
        str(policy),
        "--policy-set",
        "core_required",
    )
    assert result.returncode == 0, result.stderr

    manifest = read_manifest(tmp_path)
    assert manifest["inputs"]["gate_policy"]["version"] == "0"

    check = run_checker(tmp_path / "release_authority_v0.json")
    assert check.returncode == 0, check.stderr


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
