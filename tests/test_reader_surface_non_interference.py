#!/usr/bin/env python3
"""Reader-surface non-interference tests for PULSE v0.

These tests prove that reader/export/diagnostic tools can produce their
outputs without mutating release-authority inputs.

Covered surfaces:

- Quality Ledger / report_card.html
- status summary Markdown / JSON
- JUnit export
- SARIF export
- Decision Engine diagnostic overlay

This is test-only hardening. These tests do not change release semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "PULSE_safe_pack_v0" / "tools"

RENDER_QUALITY_LEDGER = TOOLS_DIR / "render_quality_ledger.py"
STATUS_TO_SUMMARY = TOOLS_DIR / "status_to_summary.py"
STATUS_TO_JUNIT = TOOLS_DIR / "status_to_junit.py"
STATUS_TO_SARIF = TOOLS_DIR / "status_to_sarif.py"
DECISION_ENGINE = TOOLS_DIR / "pulse_decision_engine_v0.py"

GATE_POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"
GATE_REGISTRY = REPO_ROOT / "pulse_gate_registry_v0.yml"
CHECK_GATES = TOOLS_DIR / "check_gates.py"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(paths: Iterable[pathlib.Path]) -> dict[str, str]:
    return {str(path): _sha256(path) for path in paths}


def _assert_paths_exist(paths: Iterable[pathlib.Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    assert not missing, f"Missing expected repo paths: {missing}"


def _assert_snapshot_unchanged(
    before: dict[str, str],
    paths: Iterable[pathlib.Path],
) -> None:
    after = _snapshot(paths)
    assert after == before, (
        "Expected watched release-authority inputs to remain byte-identical.\n"
        f"before={before}\n"
        f"after={after}"
    )


def _tmp_files(root: pathlib.Path) -> set[pathlib.Path]:
    return {path.resolve() for path in root.rglob("*") if path.is_file()}


def _run_tool(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    # Keep the test hermetic. Reader/export tools must use the explicit CLI
    # paths passed by this test, not environment-driven defaults.
    for name in (
        "PULSE_STATUS",
        "PULSE_JUNIT",
        "PULSE_SARIF",
        "GITHUB_STEP_SUMMARY",
    ):
        env.pop(name, None)

    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    assert result.returncode == 0, (
        f"{label} failed with exit={result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def _write_status_fixture(path: pathlib.Path) -> None:
    status = {
        "version": "1.0.0-reader-surface-non-interference",
        "created_utc": "2026-06-09T00:00:00Z",
        "metrics": {
            "run_mode": "core",
            "git_sha": "reader-surface-non-interference-test",
            "run_key": "reader-surface-non-interference-v0",
            "gate_policy_path": str(GATE_POLICY),
            "required_gate_set": "core_required",
        },
        "gates": {
            "gate_a": True,
            "gate_b": False,
            "detectors_materialized_ok": False,
            "external_summaries_present": True,
            "external_all_pass": True,
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
        },
    }

    path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _assert_only_expected_files_created(
    before_files: set[pathlib.Path],
    root: pathlib.Path,
    expected_created: Iterable[pathlib.Path],
    label: str,
) -> None:
    after_files = _tmp_files(root)
    created = after_files - before_files
    expected = {path.resolve() for path in expected_created}

    assert created == expected, (
        f"{label} created unexpected files.\n"
        f"expected_created={sorted(str(path) for path in expected)}\n"
        f"actual_created={sorted(str(path) for path in created)}"
    )


def test_reader_surface_tools_do_not_mutate_release_authority_inputs() -> None:
    repo_watched_paths = [
        GATE_POLICY,
        GATE_REGISTRY,
        CHECK_GATES,
    ]

    tool_paths = [
        RENDER_QUALITY_LEDGER,
        STATUS_TO_SUMMARY,
        STATUS_TO_JUNIT,
        STATUS_TO_SARIF,
        DECISION_ENGINE,
    ]

    _assert_paths_exist([*repo_watched_paths, *tool_paths])

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = pathlib.Path(raw_tmp)
        status_path = tmp_path / "status.json"
        _write_status_fixture(status_path)

        watched_paths = [status_path, *repo_watched_paths]
        watched_before = _snapshot(watched_paths)

        quality_ledger_path = tmp_path / "report_card.html"
        summary_md_path = tmp_path / "status_summary.md"
        summary_json_path = tmp_path / "status_summary.json"
        junit_path = tmp_path / "junit.xml"
        sarif_path = tmp_path / "sarif.json"
        decision_engine_path = tmp_path / "decision_engine_v0.json"

        commands: list[tuple[str, list[str], list[pathlib.Path]]] = [
            (
                "Quality Ledger render",
                [
                    sys.executable,
                    str(RENDER_QUALITY_LEDGER),
                    "--status",
                    str(status_path),
                    "--out",
                    str(quality_ledger_path),
                ],
                [quality_ledger_path],
            ),
            (
                "status summary export",
                [
                    sys.executable,
                    str(STATUS_TO_SUMMARY),
                    "--status",
                    str(status_path),
                    "--out_md",
                    str(summary_md_path),
                    "--out_json",
                    str(summary_json_path),
                ],
                [summary_md_path, summary_json_path],
            ),
            (
                "JUnit export",
                [
                    sys.executable,
                    str(STATUS_TO_JUNIT),
                    "--status",
                    str(status_path),
                    "--out",
                    str(junit_path),
                ],
                [junit_path],
            ),
            (
                "SARIF export",
                [
                    sys.executable,
                    str(STATUS_TO_SARIF),
                    "--status",
                    str(status_path),
                    "--out",
                    str(sarif_path),
                ],
                [sarif_path],
            ),
            (
                "Decision Engine diagnostic export",
                [
                    sys.executable,
                    str(DECISION_ENGINE),
                    "--status",
                    str(status_path),
                    "--output",
                    str(decision_engine_path),
                ],
                [decision_engine_path],
            ),
        ]

        for label, cmd, expected_outputs in commands:
            before_files = _tmp_files(tmp_path)

            result = _run_tool(cmd)
            _assert_success(result, label)

            for output_path in expected_outputs:
                assert output_path.is_file(), (
                    f"{label} did not create expected output: {output_path}"
                )

            _assert_only_expected_files_created(
                before_files,
                tmp_path,
                expected_outputs,
                label,
            )

            _assert_snapshot_unchanged(watched_before, watched_paths)

        quality_ledger_text = quality_ledger_path.read_text(encoding="utf-8")
        assert "pure reader / renderer" in quality_ledger_text
        assert "status.json" in quality_ledger_text

        summary_json = json.loads(summary_json_path.read_text(encoding="utf-8"))
        assert summary_json["schema"] == "pulse_status_summary_v1"
        assert summary_json["gates"]["total"] == 5

        sarif_json = json.loads(sarif_path.read_text(encoding="utf-8"))
        assert sarif_json["version"] == "2.1.0"

        decision_engine_json = json.loads(
            decision_engine_path.read_text(encoding="utf-8")
        )
        decision_engine = decision_engine_json["decision_engine_v0"]
        assert decision_engine["inputs"]["status_path"] == str(status_path)
        assert decision_engine["release_state"] in {
            "PROD_OK",
            "STAGE_ONLY",
            "BLOCK",
            "UNKNOWN",
        }

        # Final guard: no reader/export/diagnostic tool mutated release-authority
        # inputs after all outputs were produced.
        _assert_snapshot_unchanged(watched_before, watched_paths)


def main() -> int:
    try:
        test_reader_surface_tools_do_not_mutate_release_authority_inputs()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: reader-surface non-interference test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
