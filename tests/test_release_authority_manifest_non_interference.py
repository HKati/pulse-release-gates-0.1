from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"
BUILDER = ROOT / "PULSE_safe_pack_v0" / "tools" / "build_release_authority_manifest_v0.py"
MANIFEST_CHECKER = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_authority_manifest_v0.py"

POLICY = ROOT / "pulse_gate_policy_v0.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
SCHEMA = ROOT / "schemas" / "release_authority_v0.schema.json"

CORE_REQUIRED = [
    "pass_controls_refusal",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def release_authority_input_snapshot(status: Path) -> dict[str, str]:
    watched_paths = [
        status,
        POLICY,
        REGISTRY,
        CHECK_GATES,
    ]
    return {str(path): sha256(path) for path in watched_paths}


def assert_release_authority_inputs_unchanged(
    before: dict[str, str],
    status: Path,
    label: str,
) -> None:
    after = release_authority_input_snapshot(status)
    assert after == before, (
        f"{label} modified release-authority inputs.\n"
        f"before={before}\n"
        f"after={after}"
    )


def write_status(tmp_path: Path, gates: dict[str, object]) -> Path:
    status = {
        "version": "test",
        "created_utc": "2026-04-27T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": gates,
    }
    path = tmp_path / "status.json"
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return path


def run_check_gates(status: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_GATES),
            "--status",
            str(status),
            "--require",
            *CORE_REQUIRED,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_builder(tmp_path: Path, status: Path) -> Path:
    out = tmp_path / "release_authority_v0.json"

    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--status",
            str(status),
            "--policy",
            str(POLICY),
            "--registry",
            str(REGISTRY),
            "--evaluator",
            str(CHECK_GATES),
            "--policy-set",
            "core_required",
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
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert out.exists()
    return out


def run_manifest_checker(manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(MANIFEST_CHECKER),
            "--manifest",
            str(manifest),
            "--schema",
            str(SCHEMA),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_builder_non_interference(
    tmp_path: Path,
    status: Path,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], dict]:
     watched_before = release_authority_input_snapshot(status)

    before = run_check_gates(status)
    assert_release_authority_inputs_unchanged(
        watched_before,
        status,
        "pre-builder check_gates run",
    )

    manifest_path = run_builder(tmp_path, status)

     assert_release_authority_inputs_unchanged(
        watched_before,
        status,
        "release authority manifest builder",
    )


    after = run_check_gates(status)

     assert_release_authority_inputs_unchanged(
        watched_before,
        status,
        "post-builder check_gates run",
    )

    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    assert after.stderr == before.stderr
  
   manifest_check = run_manifest_checker(manifest_path)
    assert manifest_check.returncode == 0, manifest_check.stderr
    assert_release_authority_inputs_unchanged(
        watched_before,
        status,
        "release authority manifest checker",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return before, after, manifest


def test_release_authority_builder_does_not_change_passing_gate_result(tmp_path: Path) -> None:
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

    before, after, manifest = assert_builder_non_interference(tmp_path, status)

    assert before.returncode == 0
    assert after.returncode == 0
    assert manifest["decision"]["state"] == "PASS"
    assert manifest["evaluation"]["failed_required_gates"] == []
    assert manifest["evaluation"]["missing_required_gates"] == []


def test_release_authority_builder_does_not_change_missing_gate_failure(tmp_path: Path) -> None:
    status = write_status(
        tmp_path,
        {
            "pass_controls_refusal": True,
            "pass_controls_sanit": True,
            "sanitization_effective": True,
            "q1_grounded_ok": True,
        },
    )

    before, after, manifest = assert_builder_non_interference(tmp_path, status)

    assert before.returncode != 0
    assert after.returncode != 0
    assert manifest["decision"]["state"] == "FAIL"
    assert manifest["evaluation"]["missing_required_gates"] == ["q4_slo_ok"]
    assert "q4_slo_ok" not in manifest["evaluation"]["required_gate_results"]


def test_release_authority_builder_does_not_change_failed_gate_result(tmp_path: Path) -> None:
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

    before, after, manifest = assert_builder_non_interference(tmp_path, status)

    assert before.returncode != 0
    assert after.returncode != 0
    assert manifest["decision"]["state"] == "FAIL"
    assert manifest["evaluation"]["failed_required_gates"] == ["q4_slo_ok"]
    assert manifest["evaluation"]["required_gate_results"]["q4_slo_ok"] is False


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
