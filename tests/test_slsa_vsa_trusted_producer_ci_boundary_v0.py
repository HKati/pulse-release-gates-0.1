#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_slsa_vsa_trusted_producer_ci_boundary_v0.py"

BUILDER_BASENAME = "build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0.py"
BUILDER_RELATIVE_PATH = f"tools/{BUILDER_BASENAME}"

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
    "status.gates",
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

POLICY_OR_REGISTRY_MATERIALIZER_MARKERS = [
    "pulse_gate_policy_v0.yml",
    "pulse_gate_registry_v0.yml",
    "policy_to_require_args.py",
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "check_gates.py",
]

RELEASE_AUTHORITY_MARKERS = [
    "release_required",
    "release_blocking",
    "prod_required",
    "stage_required",
    "required gates",
    "required_gates",
    "check_gates.py",
    "status.gates",
    "status_gates",
    "status.json",
]

OUTPUT_ARG_PATTERN = re.compile(
    r"--output(?:=|\s+)(['\"]?)(?P<path>[^\s'\"\\]+)\1",
    re.MULTILINE,
)


@dataclass(frozen=True)
class InvocationWindow:
    workflow_path: Path
    line_number: int
    text: str


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


def manifest_entries() -> list[str]:
    entries: list[str] = []

    for raw in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)

    return entries


def text_uses_builder(text: str) -> bool:
    return BUILDER_BASENAME in text


def workflows_using_builder() -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []

    for path in workflow_paths():
        text = read(path)
        if text_uses_builder(text):
            matches.append((path, text))

    return matches


def invocation_windows(text: str, workflow_path: Path, *, before: int = 12, after: int = 80) -> list[InvocationWindow]:
    lines = text.splitlines()
    windows: list[InvocationWindow] = []

    for index, line in enumerate(lines):
        if BUILDER_BASENAME in line:
            start = max(0, index - before)
            end = min(len(lines), index + after)
            windows.append(
                InvocationWindow(
                    workflow_path=workflow_path,
                    line_number=index + 1,
                    text="\n".join(lines[start:end]),
                )
            )

    return windows


def upload_artifact_windows(window: str, *, after: int = 30) -> list[str]:
    lines = window.splitlines()
    windows: list[str] = []

    for index, line in enumerate(lines):
        if "actions/upload-artifact" in line:
            end = min(len(lines), index + after)
            windows.append("\n".join(lines[index:end]))

    return windows


def output_paths(window: str) -> list[str]:
    return [
        match.group("path").strip("'\"")
        for match in OUTPUT_ARG_PATTERN.finditer(window)
    ]


def assert_marker_absent(window: InvocationWindow, marker: str) -> None:
    assert marker not in window.text, (
        f"Forbidden marker {marker!r} appears near {BUILDER_BASENAME} "
        f"in {window.workflow_path} around line {window.line_number}"
    )


def test_guard_is_registered_in_tools_tests_manifest_exactly_once() -> None:
    entries = manifest_entries()

    assert entries.count(THIS_TEST) == 1, (
        f"{THIS_TEST} must be registered exactly once in {TOOLS_TESTS_LIST}"
    )


def test_builder_marker_detects_common_prefixed_paths() -> None:
    samples = [
        f"python {BUILDER_RELATIVE_PATH}",
        f"python ./{BUILDER_RELATIVE_PATH}",
        f"python $GITHUB_WORKSPACE/{BUILDER_RELATIVE_PATH}",
        f"python ${{GITHUB_WORKSPACE}}/{BUILDER_RELATIVE_PATH}",
        f"python /home/runner/work/repo/repo/{BUILDER_RELATIVE_PATH}",
    ]

    for sample in samples:
        assert text_uses_builder(sample), sample


def test_builder_ci_wiring_is_optional_and_not_required_today() -> None:
    assert WORKFLOWS_DIR.exists()

    # Current workflows do not have to invoke the builder yet. This guard
    # constrains any future workflow that introduces the builder.
    assert isinstance(workflows_using_builder(), list)


def test_builder_workflow_wiring_if_present_uses_required_validated_inputs() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for required_flag in REQUIRED_BUILDER_FLAGS:
                assert required_flag in window.text, (
                    f"Missing required builder flag {required_flag!r} "
                    f"near {BUILDER_BASENAME} in {workflow_path} "
                    f"around line {window.line_number}"
                )


def test_builder_workflow_wiring_if_present_uploads_the_builder_output_nearby() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            paths = output_paths(window.text)
            assert paths, (
                f"{workflow_path} invokes {BUILDER_BASENAME} without a parseable --output path "
                f"around line {window.line_number}"
            )

            upload_windows = upload_artifact_windows(window.text)
            assert upload_windows, (
                f"{workflow_path} invokes {BUILDER_BASENAME} but no nearby "
                f"actions/upload-artifact step is present around line {window.line_number}"
            )

            assert any(
                output_path in upload_window
                for output_path in paths
                for upload_window in upload_windows
            ), (
                f"{workflow_path} invokes {BUILDER_BASENAME}, but no nearby artifact upload "
                f"references its --output path(s): {paths}"
            )


def test_builder_workflow_wiring_if_present_is_artifact_or_diagnostic_only() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in FORBIDDEN_NEAR_BUILDER:
                assert_marker_absent(window, marker)


def test_builder_workflow_wiring_if_present_does_not_create_release_authority() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in RELEASE_AUTHORITY_MARKERS:
                assert marker not in window.text, (
                    f"{workflow_path} appears to mix {BUILDER_BASENAME} with "
                    f"release-authority marker {marker!r} around line {window.line_number}"
                )


def test_builder_workflow_wiring_if_present_does_not_consume_policy_materializers() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in POLICY_OR_REGISTRY_MATERIALIZER_MARKERS:
                assert marker not in window.text, (
                    f"{workflow_path} invokes {BUILDER_BASENAME} near policy/materializer "
                    f"marker {marker!r} around line {window.line_number}"
                )


def check_slsa_vsa_trusted_producer_ci_boundary_v0() -> None:
    test_guard_is_registered_in_tools_tests_manifest_exactly_once()
    test_builder_marker_detects_common_prefixed_paths()
    test_builder_ci_wiring_is_optional_and_not_required_today()
    test_builder_workflow_wiring_if_present_uses_required_validated_inputs()
    test_builder_workflow_wiring_if_present_uploads_the_builder_output_nearby()
    test_builder_workflow_wiring_if_present_is_artifact_or_diagnostic_only()
    test_builder_workflow_wiring_if_present_does_not_create_release_authority()
    test_builder_workflow_wiring_if_present_does_not_consume_policy_materializers()


def test_slsa_vsa_trusted_producer_ci_boundary_v0() -> None:
    check_slsa_vsa_trusted_producer_ci_boundary_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_producer_ci_boundary_v0()
    print("OK: SLSA VSA trusted producer CI boundary guard passed")
