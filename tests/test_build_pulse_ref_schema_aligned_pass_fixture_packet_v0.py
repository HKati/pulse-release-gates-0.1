#!/usr/bin/env python3
"""Smoke tests for the schema-aligned pass fixture packet builder."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py"
CHECKER = ROOT / "scripts" / "check_pulse_ref_schema_aligned_packet_v0.py"

SOURCE_STATUS = ROOT / "tests" / "fixtures" / "release_reference_v1" / "pass" / "status.json"
SOURCE_EXPECTED = (
    ROOT / "tests" / "fixtures" / "release_reference_v1" / "pass" / "expected_outcome.json"
)

REQUIRED_PACKET_PATHS = [
    "README.md",
    "package_manifest.json",
    "status/status.json",
    "reconstruction/source_expected_outcome.json",
    "policy/pulse_gate_policy_v0.yml",
    "policy/pulse_gate_registry_v0.yml",
    "gates/materialized_gate_sets.json",
    "ci/ci_outcome.json",
    "release_authority/release_authority_manifest.json",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
    "digests/package_digests.json",
    "handoff/operator_handoff_report.json",
    "external/summaries/README.md",
    "reconstruction/reconstruction_instructions.md",
]


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_builder_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "build_pulse_ref_schema_aligned_pass_fixture_packet_v0",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_builder(out_dir: Path) -> Path:
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    packet_root = out_dir / "pulse_ref_evidence_packet_v0"
    assert packet_root.is_dir()
    return packet_root


def _run_checker(packet_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--packet-root",
            str(packet_root),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_builder_file_exists() -> None:
    assert BUILDER.is_file()


def test_builder_creates_required_packet_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))

        for rel_path in REQUIRED_PACKET_PATHS:
            assert (packet_root / rel_path).is_file(), rel_path


def test_builder_preserves_source_status_and_expected_outcome() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))

        assert _load_json(packet_root / "status/status.json") == _load_json(SOURCE_STATUS)
        assert _load_json(packet_root / "reconstruction/source_expected_outcome.json") == _load_json(SOURCE_EXPECTED)


def test_builder_packet_passes_schema_aligned_validator() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))
        result = _run_checker(packet_root)

        assert result.returncode == 0, result.stdout + result.stderr
        assert "OK: PULSE-REF schema-aligned packet artifacts valid" in result.stdout


def test_builder_materializes_gates_from_declared_policy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))
        gate_sets = _load_json(packet_root / "gates/materialized_gate_sets.json")

        assert gate_sets["schema"] == "pulse_ref_materialized_gate_sets_v0"
        assert gate_sets["policy_path"] == "policy/pulse_gate_policy_v0.yml"
        assert gate_sets["authority_boundary"]["source"] == "declared_gate_policy"
        assert gate_sets["authority_boundary"]["creates_release_authority"] is False

        required = gate_sets["sets"]["required"]
        release_required = gate_sets["sets"]["release_required"]
        effective = gate_sets["effective_required_gates"]

        assert required
        assert release_required
        assert effective == list(dict.fromkeys(required + release_required))


def test_builder_emits_canonical_packet_manifest_and_digests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))

        manifest = _load_json(packet_root / "package_manifest.json")
        digests = _load_json(packet_root / "digests/package_digests.json")

        assert manifest["schema"] == "pulse_ref_release_reference_package_v0"
        assert manifest["status_artifact"]["path"] == "status/status.json"
        assert manifest["materialized_gate_sets"]["path"] == "gates/materialized_gate_sets.json"
        assert manifest["ci_outcome"]["path"] == "ci/ci_outcome.json"
        assert manifest["package_digests"]["path"] == "digests/package_digests.json"

        assert digests["schema"] == "pulse_ref_package_digests_v0"
        assert digests["algorithm"] == "sha256"
        assert "status/status.json" in digests["artifacts"]
        assert "gates/materialized_gate_sets.json" in digests["artifacts"]


def test_builder_emits_canonical_ci_and_handoff_shapes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))

        ci_outcome = _load_json(packet_root / "ci/ci_outcome.json")
        handoff = _load_json(packet_root / "handoff/operator_handoff_report.json")

        assert ci_outcome["schema"] == "pulse_ref_ci_outcome_v0"
        assert ci_outcome["provider"] == "github_actions"
        assert ci_outcome["gate_check_conclusion"] == "success"
        assert ci_outcome["authority_boundary"]["creates_release_authority"] is False

        assert handoff["schema"] == "pulse_ref_operator_handoff_report_v0"
        assert handoff["ok"] is True
        assert handoff["gate_mode"] == "release-grade"
        assert handoff["errors"] == []
        assert handoff["authority_boundary"]["creates_release_authority"] is False


def test_builder_rejects_false_required_gate_in_pass_fixture() -> None:
    builder = _load_builder_module()

    status = _load_json(SOURCE_STATUS)
    effective_required = ["pass_controls_refusal"]

    status["gates"]["pass_controls_refusal"] = False

    try:
        builder._status_gate_results(status, effective_required)
    except ValueError as exc:
        assert "must be literal true" in str(exc)
        assert "pass_controls_refusal" in str(exc)
    else:
        raise AssertionError("builder accepted a false required gate")


def test_release_reference_guard_rejects_stubbed_source_status() -> None:
    builder = _load_builder_module()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_status = Path(tmp) / "status.json"
        status = _load_json(SOURCE_STATUS)
        status["diagnostics"]["gates_stubbed"] = True
        tmp_status.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        try:
            builder._run_release_reference_guard(tmp_status)
        except RuntimeError as exc:
            assert "release-reference completeness guard" in str(exc)
        else:
            raise AssertionError("builder accepted a stubbed source status")


def test_builder_handoff_commands_are_replayable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))
        handoff = _load_json(packet_root / "handoff/operator_handoff_report.json")

        for command in handoff["commands"]:
            cmd = command["cmd"]
            assert cmd, command["name"]
            assert Path(cmd[0]).is_absolute(), command["name"]

            result = subprocess.run(
                cmd,
                cwd=Path(tmp),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            assert result.returncode == command["returncode"], (
                command["name"],
                result.stdout,
                result.stderr,
            )

        check_command = next(
            command
            for command in handoff["commands"]
            if command["name"] == "check_gates_release-grade"
        )

        assert str(ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py") in check_command["cmd"]
        assert str(packet_root / "status" / "status.json") in check_command["cmd"]


def test_builder_accepts_relative_out_dir_from_non_repo_cwd() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        out_dir = Path("relative-out")

        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--out-dir",
                str(out_dir),
            ],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr

        packet_root = cwd / out_dir / "pulse_ref_evidence_packet_v0"
        assert packet_root.is_dir()

        checker = _run_checker(packet_root)
        assert checker.returncode == 0, checker.stdout + checker.stderr


def main() -> int:
    try:
        test_builder_file_exists()
        test_builder_creates_required_packet_paths()
        test_builder_preserves_source_status_and_expected_outcome()
        test_builder_packet_passes_schema_aligned_validator()
        test_builder_materializes_gates_from_declared_policy()
        test_builder_emits_canonical_packet_manifest_and_digests()
        test_builder_emits_canonical_ci_and_handoff_shapes()
        test_builder_rejects_false_required_gate_in_pass_fixture()
        test_release_reference_guard_rejects_stubbed_source_status()
        test_builder_handoff_commands_are_replayable()
        test_builder_accepts_relative_out_dir_from_non_repo_cwd()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: schema-aligned pass fixture packet builder smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
