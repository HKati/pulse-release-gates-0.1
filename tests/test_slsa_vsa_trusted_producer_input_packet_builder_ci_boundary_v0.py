#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_slsa_vsa_trusted_producer_input_packet_builder_ci_boundary_v0.py"

BUILDER_BASENAME = "build_slsa_vsa_trusted_producer_input_packet_v0.py"
BUILDER_MODULE = "tools.build_slsa_vsa_trusted_producer_input_packet_v0"
BUILDER_RELATIVE_PATH = f"tools/{BUILDER_BASENAME}"
BUILDER_MARKERS = [BUILDER_BASENAME, BUILDER_MODULE]

REQUIRED_BUILDER_FLAGS = [
    "--schema",
    "--created-utc",
    "--producer-id",
    "--producer-name",
    "--producer-version",
    "--producer-source",
    "--ci-workflow-or-job-identity",
    "--current-run-id",
    "--current-run-number",
    "--current-run-attempt",
    "--workflow-name",
    "--job-name",
    "--commit-sha",
    "--release-candidate-id",
    "--artifact-subject-name",
    "--artifact-sha256",
    "--artifact-resource-uri",
    "--policy-id",
    "--policy-uri",
    "--policy-sha256",
    "--verifier-id",
    "--verified-level",
    "--time-verified",
    "--freshness-epoch",
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
    "release_authority",
    "release_authority_v0.json",
    "build_release_authority_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py",
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
    "release_authority",
    "release_authority_v0.json",
    "build_release_authority_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py",
]

MATERIALIZER_OR_FOLD_MARKERS = [
    "policy_to_require_args.py",
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "check_gates.py",
    "fold_slsa_vsa_intake_into_status_v0.py",
    "materialize_release_required_from_verifier_v0.py",
    "build_release_authority_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py",
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
    command_text: str
    after_text: str


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


def line_uses_builder(line: str) -> bool:
    return any(marker in line for marker in BUILDER_MARKERS)


def text_uses_builder(text: str) -> bool:
    return any(marker in text for marker in BUILDER_MARKERS)


def workflows_using_builder() -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []

    for path in workflow_paths():
        text = read(path)
        if text_uses_builder(text):
            matches.append((path, text))

    return matches


def invocation_command(lines: list[str], start_index: int) -> tuple[str, int]:
    command_lines = [lines[start_index]]
    end_index = start_index

    while command_lines[-1].rstrip().endswith("\\") and end_index + 1 < len(lines):
        end_index += 1
        command_lines.append(lines[end_index])

    return "\n".join(command_lines), end_index


def invocation_windows(
    text: str,
    workflow_path: Path,
    *,
    before: int = 12,
    after: int = 80,
) -> list[InvocationWindow]:
    lines = text.splitlines()
    windows: list[InvocationWindow] = []

    for index, line in enumerate(lines):
        if line_uses_builder(line):
            command_text, command_end_index = invocation_command(lines, index)

            start = max(0, index - before)
            end = min(len(lines), command_end_index + after)
            after_start = min(len(lines), command_end_index + 1)

            windows.append(
                InvocationWindow(
                    workflow_path=workflow_path,
                    line_number=index + 1,
                    text="\n".join(lines[start:end]),
                    command_text=command_text,
                    after_text="\n".join(lines[after_start:end]),
                )
            )

    return windows


def upload_artifact_windows(text: str, *, after: int = 30) -> list[str]:
    lines = text.splitlines()
    windows: list[str] = []

    for index, line in enumerate(lines):
        if "actions/upload-artifact" in line:
            end = min(len(lines), index + after)
            windows.append("\n".join(lines[index:end]))

    return windows


def output_paths(command_text: str) -> list[str]:
    return [
        match.group("path").strip("'\"")
        for match in OUTPUT_ARG_PATTERN.finditer(command_text)
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


def test_builder_marker_detects_common_prefixed_paths_and_module_invocations() -> None:
    samples = [
        f"python {BUILDER_RELATIVE_PATH}",
        f"python ./{BUILDER_RELATIVE_PATH}",
        f"python $GITHUB_WORKSPACE/{BUILDER_RELATIVE_PATH}",
        f"python ${{GITHUB_WORKSPACE}}/{BUILDER_RELATIVE_PATH}",
        f"python /home/runner/work/repo/repo/{BUILDER_RELATIVE_PATH}",
        f"python -m {BUILDER_MODULE}",
        f"python -m {BUILDER_MODULE} --help",
    ]

    for sample in samples:
        assert text_uses_builder(sample), sample


def test_invocation_command_text_is_scoped_to_the_builder_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            "          echo --schema --freshness-epoch --output generated_packet.json",
            f"          python {BUILDER_RELATIVE_PATH}",
            "          echo --producer-id --producer-name --policy-id",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert BUILDER_BASENAME in windows[0].command_text
    assert "--schema" not in windows[0].command_text
    assert "--freshness-epoch" not in windows[0].command_text
    assert "--output" not in windows[0].command_text


def test_invocation_command_text_includes_continued_builder_flags() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            f"          python {BUILDER_RELATIVE_PATH} \\",
            "            --schema schemas/slsa_vsa_trusted_producer_input_packet_v0.schema.json \\",
            "            --created-utc 2026-07-07T00:00:00Z \\",
            "            --producer-id producer \\",
            "            --freshness-epoch current_run \\",
            "            --output generated_packet.json",
            "          echo after-builder",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert "--schema" in windows[0].command_text
    assert "--created-utc" in windows[0].command_text
    assert "--producer-id" in windows[0].command_text
    assert "--freshness-epoch" in windows[0].command_text
    assert "--output" in windows[0].command_text
    assert "echo after-builder" not in windows[0].command_text


def test_upload_detection_uses_only_lines_after_the_builder_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - uses: actions/upload-artifact@v4",
            "        with:",
            "          path: generated_packet.json",
            "      - run: |",
            f"          python {BUILDER_RELATIVE_PATH} --output generated_packet.json",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert output_paths(windows[0].command_text) == ["generated_packet.json"]
    assert upload_artifact_windows(windows[0].after_text) == []


def test_upload_detection_accepts_upload_after_the_builder_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            f"          python {BUILDER_RELATIVE_PATH} --output generated_packet.json",
            "      - uses: actions/upload-artifact@v4",
            "        with:",
            "          path: generated_packet.json",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert output_paths(windows[0].command_text) == ["generated_packet.json"]
    upload_windows = upload_artifact_windows(windows[0].after_text)
    assert len(upload_windows) == 1
    assert "generated_packet.json" in upload_windows[0]


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
                assert required_flag in window.command_text, (
                    f"Missing required builder flag {required_flag!r} "
                    f"in the {BUILDER_BASENAME} command in {workflow_path} "
                    f"around line {window.line_number}"
                )


def test_builder_workflow_wiring_if_present_does_not_accept_hand_passed_run_key() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            assert "--current-run-key" not in window.command_text, (
                f"{workflow_path} appears to pass --current-run-key to "
                f"{BUILDER_BASENAME} around line {window.line_number}; "
                "the builder must compute current_run_key internally"
            )


def test_builder_workflow_wiring_if_present_uploads_the_builder_output_afterward() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            paths = output_paths(window.command_text)
            assert paths, (
                f"{workflow_path} invokes {BUILDER_BASENAME} without a parseable --output path "
                f"around line {window.line_number}"
            )

            for output_path in paths:
                assert Path(output_path).name != "status.json", (
                    f"{workflow_path} invokes {BUILDER_BASENAME} with forbidden "
                    f"status.json output path around line {window.line_number}"
                )

            upload_windows = upload_artifact_windows(window.after_text)
            assert upload_windows, (
                f"{workflow_path} invokes {BUILDER_BASENAME} but no later "
                f"actions/upload-artifact step is present around line {window.line_number}"
            )

            assert any(
                output_path in upload_window
                for output_path in paths
                for upload_window in upload_windows
            ), (
                f"{workflow_path} invokes {BUILDER_BASENAME}, but no later artifact upload "
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


def test_builder_workflow_wiring_if_present_does_not_consume_materializers_or_folders() -> None:
    for workflow_path, text in workflows_using_builder():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains builder marker but no invocation window"

        for window in windows:
            for marker in MATERIALIZER_OR_FOLD_MARKERS:
                assert marker not in window.text, (
                    f"{workflow_path} invokes {BUILDER_BASENAME} near materializer/fold "
                    f"marker {marker!r} around line {window.line_number}"
                )


def check_slsa_vsa_trusted_producer_input_packet_builder_ci_boundary_v0() -> None:
    test_guard_is_registered_in_tools_tests_manifest_exactly_once()
    test_builder_marker_detects_common_prefixed_paths_and_module_invocations()
    test_invocation_command_text_is_scoped_to_the_builder_command()
    test_invocation_command_text_includes_continued_builder_flags()
    test_upload_detection_uses_only_lines_after_the_builder_command()
    test_upload_detection_accepts_upload_after_the_builder_command()
    test_builder_ci_wiring_is_optional_and_not_required_today()
    test_builder_workflow_wiring_if_present_uses_required_validated_inputs()
    test_builder_workflow_wiring_if_present_does_not_accept_hand_passed_run_key()
    test_builder_workflow_wiring_if_present_uploads_the_builder_output_afterward()
    test_builder_workflow_wiring_if_present_is_artifact_or_diagnostic_only()
    test_builder_workflow_wiring_if_present_does_not_create_release_authority()
    test_builder_workflow_wiring_if_present_does_not_consume_materializers_or_folders()


def test_slsa_vsa_trusted_producer_input_packet_builder_ci_boundary_v0() -> None:
    check_slsa_vsa_trusted_producer_input_packet_builder_ci_boundary_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_producer_input_packet_builder_ci_boundary_v0()
    print("OK: SLSA VSA trusted producer input-packet builder CI boundary guard passed")
