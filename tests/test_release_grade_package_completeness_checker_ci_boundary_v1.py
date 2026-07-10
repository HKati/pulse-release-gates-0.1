#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_release_grade_package_completeness_checker_ci_boundary_v1.py"

CHECKER_BASENAME = "check_release_grade_package_complete_v1.py"
CHECKER_MODULE = "tools.check_release_grade_package_complete_v1"
CHECKER_RELATIVE_PATH = f"tools/{CHECKER_BASENAME}"
CHECKER_MARKERS = [CHECKER_BASENAME, CHECKER_MODULE]

REQUIRED_CHECKER_FLAGS = [
    "--package-dir",
    "--output",
]

FORBIDDEN_NEAR_CHECKER = [
    "check_gates.py",
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "policy_to_require_args.py",
    "fold_slsa_vsa_intake_into_status_v0.py",
    "materialize_release_required_from_verifier_v0.py",
    "build_release_authority_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py",
    "release_required",
    "release_blocking",
    "prod_required",
    "stage_required",
    "gate_materialization",
    "required_gates",
    "status.gates",
    "status_gates",
]

RELEASE_AUTHORITY_MARKERS = [
    "check_gates.py",
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "policy_to_require_args.py",
    "fold_slsa_vsa_intake_into_status_v0.py",
    "materialize_release_required_from_verifier_v0.py",
    "build_release_authority_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py",
    "release_required",
    "release_blocking",
    "prod_required",
    "stage_required",
    "required gates",
    "required_gates",
    "status.gates",
    "status_gates",
    "gate_materialization",
]

OUTPUT_ARG_PATTERN = re.compile(
    r"--output(?:=|\s+)(['\"]?)(?P<path>[^\s'\"\\]+)\1",
    re.MULTILINE,
)

PACKAGE_DIR_ARG_PATTERN = re.compile(
    r"--package-dir(?:=|\s+)(['\"]?)(?P<path>[^\s'\"\\]+)\1",
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


def line_uses_checker(line: str) -> bool:
    return any(marker in line for marker in CHECKER_MARKERS)


def text_uses_checker(text: str) -> bool:
    return any(marker in text for marker in CHECKER_MARKERS)


def workflows_using_checker() -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []

    for path in workflow_paths():
        text = read(path)
        if text_uses_checker(text):
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
        if line_uses_checker(line):
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


def _normalize_shell_path(value: str) -> str:
    normalized = value.strip("'\"")
    normalized = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", r"$\1", normalized)
    return normalized.rstrip("/")


def output_paths(command_text: str) -> list[str]:
    return [
        _normalize_shell_path(match.group("path"))
        for match in OUTPUT_ARG_PATTERN.finditer(command_text)
    ]


def package_dirs(command_text: str) -> list[str]:
    return [
        _normalize_shell_path(match.group("path"))
        for match in PACKAGE_DIR_ARG_PATTERN.finditer(command_text)
    ]


def output_path_refused(output_path: str, package_dir: str | None) -> str | None:
    normalized_output = _normalize_shell_path(output_path)

    if Path(normalized_output).name == "status.json":
        return "status.json output path"

    if package_dir is not None:
        normalized_package = _normalize_shell_path(package_dir)

        if normalized_output == normalized_package:
            return "output equals package directory"

        if normalized_output.startswith(normalized_package + "/"):
            return "output is inside package directory"

    return None


def assert_marker_absent(window: InvocationWindow, marker: str) -> None:
    assert marker not in window.text, (
        f"Forbidden marker {marker!r} appears near {CHECKER_BASENAME} "
        f"in {window.workflow_path} around line {window.line_number}"
    )


def test_guard_is_registered_in_tools_tests_manifest_exactly_once() -> None:
    entries = manifest_entries()

    assert entries.count(THIS_TEST) == 1, (
        f"{THIS_TEST} must be registered exactly once in {TOOLS_TESTS_LIST}"
    )


def test_guard_is_placed_after_completeness_checker_smoke() -> None:
    entries = manifest_entries()

    guard_index = entries.index(THIS_TEST)
    checker_index = entries.index("tests/test_check_release_grade_package_complete_v1.py")
    next_boundary_index = entries.index(
        "tests/test_release_grade_reference_qualification_advisory_boundary_v0.py"
    )

    assert checker_index < guard_index < next_boundary_index


def test_checker_marker_detects_common_prefixed_paths_and_module_invocations() -> None:
    samples = [
        f"python {CHECKER_RELATIVE_PATH}",
        f"python ./{CHECKER_RELATIVE_PATH}",
        f"python $GITHUB_WORKSPACE/{CHECKER_RELATIVE_PATH}",
        f"python ${{GITHUB_WORKSPACE}}/{CHECKER_RELATIVE_PATH}",
        f"python /home/runner/work/repo/repo/{CHECKER_RELATIVE_PATH}",
        f"python -m {CHECKER_MODULE}",
        f"python -m {CHECKER_MODULE} --help",
    ]

    for sample in samples:
        assert text_uses_checker(sample), sample


def test_invocation_command_text_is_scoped_to_the_checker_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            "          echo --package-dir release_package --output report.json",
            f"          python {CHECKER_RELATIVE_PATH}",
            "          echo --package-dir release_package --output report.json",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert CHECKER_BASENAME in windows[0].command_text
    assert "--package-dir" not in windows[0].command_text
    assert "--output" not in windows[0].command_text


def test_invocation_command_text_includes_continued_checker_flags() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            f"          python {CHECKER_RELATIVE_PATH} \\",
            "            --package-dir $RUNNER_TEMP/release_grade_package \\",
            "            --output $RUNNER_TEMP/release_grade_completeness_report.json",
            "          echo after-checker",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert "--package-dir" in windows[0].command_text
    assert "--output" in windows[0].command_text
    assert "echo after-checker" not in windows[0].command_text


def test_upload_detection_uses_only_lines_after_the_checker_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - uses: actions/upload-artifact@v4",
            "        with:",
            "          path: $RUNNER_TEMP/release_grade_completeness_report.json",
            "      - run: |",
            f"          python {CHECKER_RELATIVE_PATH} "
            "--package-dir $RUNNER_TEMP/release_grade_package "
            "--output $RUNNER_TEMP/release_grade_completeness_report.json",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert output_paths(windows[0].command_text) == [
        "$RUNNER_TEMP/release_grade_completeness_report.json"
    ]
    assert upload_artifact_windows(windows[0].after_text) == []


def test_upload_detection_accepts_upload_after_the_checker_command() -> None:
    text = "\n".join(
        [
            "name: synthetic",
            "jobs:",
            "  build:",
            "    steps:",
            "      - run: |",
            f"          python {CHECKER_RELATIVE_PATH} "
            "--package-dir $RUNNER_TEMP/release_grade_package "
            "--output $RUNNER_TEMP/release_grade_completeness_report.json",
            "      - uses: actions/upload-artifact@v4",
            "        with:",
            "          path: $RUNNER_TEMP/release_grade_completeness_report.json",
        ]
    )

    windows = invocation_windows(text, Path("synthetic.yml"))

    assert len(windows) == 1
    assert output_paths(windows[0].command_text) == [
        "$RUNNER_TEMP/release_grade_completeness_report.json"
    ]

    upload_windows = upload_artifact_windows(windows[0].after_text)
    assert len(upload_windows) == 1
    assert "$RUNNER_TEMP/release_grade_completeness_report.json" in upload_windows[0]


def test_output_path_guard_rejects_status_json_and_package_internal_outputs() -> None:
    assert output_path_refused("status.json", "$PKG") == "status.json output path"
    assert output_path_refused("$PKG/status.json", "$PKG") == "status.json output path"
    assert (
        output_path_refused("$PKG/completeness_report.json", "$PKG")
        == "output is inside package directory"
    )
    assert (
        output_path_refused("${PKG}/completeness_report.json", "$PKG")
        == "output is inside package directory"
    )
    assert output_path_refused("$RUNNER_TEMP/report.json", "$PKG") is None


def test_checker_ci_wiring_is_optional_and_not_required_today() -> None:
    assert WORKFLOWS_DIR.exists()

    # Current workflows do not have to invoke the checker yet. This guard
    # constrains any future workflow that introduces it.
    assert isinstance(workflows_using_checker(), list)


def test_checker_workflow_wiring_if_present_uses_required_inputs() -> None:
    for workflow_path, text in workflows_using_checker():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains checker marker but no invocation window"

        for window in windows:
            for required_flag in REQUIRED_CHECKER_FLAGS:
                assert required_flag in window.command_text, (
                    f"Missing required checker flag {required_flag!r} "
                    f"in the {CHECKER_BASENAME} command in {workflow_path} "
                    f"around line {window.line_number}"
                )


def test_checker_workflow_wiring_if_present_uses_safe_output_path() -> None:
    for workflow_path, text in workflows_using_checker():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains checker marker but no invocation window"

        for window in windows:
            paths = output_paths(window.command_text)
            packages = package_dirs(window.command_text)
            package_dir = packages[0] if packages else None

            assert paths, (
                f"{workflow_path} invokes {CHECKER_BASENAME} without a parseable --output path "
                f"around line {window.line_number}"
            )

            for output_path in paths:
                refused_reason = output_path_refused(output_path, package_dir)
                assert refused_reason is None, (
                    f"{workflow_path} invokes {CHECKER_BASENAME} with unsafe output "
                    f"path {output_path!r}: {refused_reason} around line {window.line_number}"
                )


def test_checker_workflow_wiring_if_present_uploads_output_afterward() -> None:
    for workflow_path, text in workflows_using_checker():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains checker marker but no invocation window"

        for window in windows:
            paths = output_paths(window.command_text)
            assert paths, (
                f"{workflow_path} invokes {CHECKER_BASENAME} without a parseable --output path "
                f"around line {window.line_number}"
            )

            upload_windows = upload_artifact_windows(window.after_text)
            assert upload_windows, (
                f"{workflow_path} invokes {CHECKER_BASENAME} but no later "
                f"actions/upload-artifact step is present around line {window.line_number}"
            )

            assert any(
                output_path in upload_window
                for output_path in paths
                for upload_window in upload_windows
            ), (
                f"{workflow_path} invokes {CHECKER_BASENAME}, but no later artifact upload "
                f"references its --output path(s): {paths}"
            )


def test_checker_workflow_wiring_if_present_is_artifact_or_diagnostic_only() -> None:
    for workflow_path, text in workflows_using_checker():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains checker marker but no invocation window"

        for window in windows:
            for marker in FORBIDDEN_NEAR_CHECKER:
                assert_marker_absent(window, marker)


def test_checker_workflow_wiring_if_present_does_not_create_release_authority() -> None:
    for workflow_path, text in workflows_using_checker():
        windows = invocation_windows(text, workflow_path)
        assert windows, f"{workflow_path} contains checker marker but no invocation window"

        for window in windows:
            for marker in RELEASE_AUTHORITY_MARKERS:
                assert marker not in window.text, (
                    f"{workflow_path} appears to mix {CHECKER_BASENAME} with "
                    f"release-authority marker {marker!r} around line {window.line_number}"
                )


def check_release_grade_package_completeness_checker_ci_boundary_v1() -> None:
    test_guard_is_registered_in_tools_tests_manifest_exactly_once()
    test_guard_is_placed_after_completeness_checker_smoke()
    test_checker_marker_detects_common_prefixed_paths_and_module_invocations()
    test_invocation_command_text_is_scoped_to_the_checker_command()
    test_invocation_command_text_includes_continued_checker_flags()
    test_upload_detection_uses_only_lines_after_the_checker_command()
    test_upload_detection_accepts_upload_after_the_checker_command()
    test_output_path_guard_rejects_status_json_and_package_internal_outputs()
    test_checker_ci_wiring_is_optional_and_not_required_today()
    test_checker_workflow_wiring_if_present_uses_required_inputs()
    test_checker_workflow_wiring_if_present_uses_safe_output_path()
    test_checker_workflow_wiring_if_present_uploads_output_afterward()
    test_checker_workflow_wiring_if_present_is_artifact_or_diagnostic_only()
    test_checker_workflow_wiring_if_present_does_not_create_release_authority()


def test_release_grade_package_completeness_checker_ci_boundary_v1() -> None:
    check_release_grade_package_completeness_checker_ci_boundary_v1()


if __name__ == "__main__":
    check_release_grade_package_completeness_checker_ci_boundary_v1()
    print("OK: release-grade package completeness checker CI boundary guard passed")
