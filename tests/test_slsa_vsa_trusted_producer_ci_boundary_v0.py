#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

BUILDER_TOOL = "tools/build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0.py"

REQUIRED_BUILDER_FLAGS = [
    "--evidence-schema",
    "--evidence",
    "--input-packet-schema",
    "--input-packet",
    "--input-packet-validator",
    "--report-schema",
    "--report-validator",
    "--output",
]

FORBIDDEN_NEAR_BUILDER = [
    "status.json",
    "status_gates",
    "check_gates.py",
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "fold_slsa_vsa_intake_into_status_v0.py",
    "policy_to_require_args.py",
    "materialize_release_required_from_verifier_v0.py",
    "release_required",
    "release_blocking",
    "prod_required",
    "stage_required",
    "gate_materialization",
]


def workflow_paths() -> list[Path]:
    if not WORKFLOWS_DIR.exists():
        return []

    return sorted(
        path
        for path in WORKFLOWS_DIR.iterdir()
        if path.suffix in {".yml", ".yaml"} and path.is_file()
    )


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def workflows_using_builder() -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []

    for path in workflow_paths():
        text = read(path)
        if BUILDER_TOOL in text:
            matches.append((path, text))

    return matches


def invocation_windows(text: str, *, radius: int = 80) -> list[str]:
    lines = text.splitlines()
    windows: list[str] = []

    for index, line in enumerate(lines):
        if BUILDER_TOOL in line:
            start = max(0, index - 10)
            end = min(len(lines), index + radius)
            windows.append("\n".join(lines[start:end]))

    return windows


def assert_marker_absent(window: str, marker: str, workflow_path: Path) -> None:
    assert marker not in window, (
        f"Forbidden marker {marker!r} appears near {BUILDER_TOOL} "
        f"in {workflow_path}"
    )


def test_builder_ci_wiring_is_optional_and_not_required_today() -> None:
    assert WORKFLOWS_DIR.exists()

    # This guard intentionally allows the current state where no workflow
    # invokes the builder yet. It constrains any future workflow wiring.
    assert isinstance(workflows_using_builder(), list)


def test_builder_workflow_wiring_if_present_uses_required_validated_inputs() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for required_flag in REQUIRED_BUILDER_FLAGS:
                assert required_flag in window, (
                    f"Missing required builder flag {required_flag!r} "
                    f"near {BUILDER_TOOL} in {workflow_path}"
                )


def test_builder_workflow_wiring_if_present_is_artifact_or_diagnostic_only() -> None:
    for workflow_path, text in workflows_using_builder():
        assert "actions/upload-artifact" in text, (
            f"{workflow_path} invokes {BUILDER_TOOL} but does not upload an artifact"
        )

        windows = invocation_windows(text)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in FORBIDDEN_NEAR_BUILDER:
                assert_marker_absent(window, marker, workflow_path)


def test_builder_workflow_wiring_if_present_does_not_create_release_authority() -> None:
    release_authority_markers = [
        "release_required",
        "release_blocking",
        "prod_required",
        "stage_required",
        "required gates",
        "required_gates",
        "check_gates.py",
        "status_gates",
        "status.json",
    ]

    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in release_authority_markers:
                assert marker not in window, (
                    f"{workflow_path} appears to mix {BUILDER_TOOL} with "
                    f"release-authority marker {marker!r}"
                )


def test_current_workflows_do_not_treat_trusted_producer_report_as_policy_materializer() -> None:
    for workflow_path, text in workflows_using_builder():
        assert "pulse_gate_policy_v0.yml" not in text, (
            f"{workflow_path} invokes {BUILDER_TOOL} and references active policy"
        )
        assert "pulse_gate_registry_v0.yml" not in text, (
            f"{workflow_path} invokes {BUILDER_TOOL} and references gate registry"
        )


def check_slsa_vsa_trusted_producer_ci_boundary_v0() -> None:
    test_builder_ci_wiring_is_optional_and_not_required_today()
    test_builder_workflow_wiring_if_present_uses_required_validated_inputs()
    test_builder_workflow_wiring_if_present_is_artifact_or_diagnostic_only()
    test_builder_workflow_wiring_if_present_does_not_create_release_authority()
    test_current_workflows_do_not_treat_trusted_producer_report_as_policy_materializer()


def test_slsa_vsa_trusted_producer_ci_boundary_v0() -> None:
    check_slsa_vsa_trusted_producer_ci_boundary_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_producer_ci_boundary_v0()
    print("OK: SLSA VSA trusted producer CI boundary guard passed")
