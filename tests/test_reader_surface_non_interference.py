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


# SEC-HISTORY-01: the history workflow is a diagnostic surface, not authority.
# These tests execute only allowlisted local processing steps in fresh fixtures.
# They do not run the PULSE pack, cache action, GitHub API or a workflow.
import copy
import shutil
import unittest

import yaml


HISTORY_WORKFLOW = REPO_ROOT / ".github/workflows/pulse_history_drift.yml"
_HISTORY_CACHE_REVISION = "55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
# Canonical parsed workflow, excluding only the top-level permissions mapping.
# Derived from 77f58886bd79bc0b8012c10a8aaea3f25c512d00. An intentional future
# workflow/pin change needs explicit review of this preservation guard too.
_HISTORY_BEHAVIOR_SHA256 = "744b822ccf1266ca9dfdbc8f3c689055c0611c54922167343baf855878b23543"


class _HistoryYamlLoader(yaml.BaseLoader):
    """Keep 'on' as text and reject ambiguous mappings in regression inputs."""


def _history_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str) or key in result:
            raise ValueError("duplicate or invalid history workflow mapping key")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_HistoryYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _history_mapping
)


def _load_history_workflow(text: str | None = None) -> dict:
    data = yaml.load(
        HISTORY_WORKFLOW.read_text(encoding="utf-8") if text is None else text,
        Loader=_HistoryYamlLoader,
    )
    if not isinstance(data, dict):
        raise ValueError("history workflow must be a mapping")
    return data


def _history_steps(data: dict) -> dict[str, dict]:
    steps = data["jobs"]["history-drift"]["steps"]
    result = {step["name"]: step for step in steps}
    if len(result) != len(steps):
        raise ValueError("duplicate history step names")
    return result


def _check_history_workflow(data: dict) -> None:
    """Test-only contract check, not a new production admission mechanism."""
    if data.get("permissions") != {"contents": "read"}:
        raise ValueError("history GITHUB_TOKEN permissions must be contents: read only")
    if data.get("on") != {"workflow_dispatch": {}}:
        raise ValueError("history trigger changed")
    if set(data.get("jobs", {})) != {"history-drift"}:
        raise ValueError("history job boundary changed")
    job = data["jobs"]["history-drift"]
    if "permissions" in job:
        raise ValueError("history job must not override token permissions")
    steps = _history_steps(data)
    for kind, name in (("restore", "Restore status history cache"),
                       ("save", "Save status history cache")):
        step = steps.get(name, {})
        if step.get("uses") != f"actions/cache/{kind}@{_HISTORY_CACHE_REVISION}":
            raise ValueError("history cache source identity missing or changed")
        if step.get("with", {}).get("path") != "${{ env.HISTORY_FILE }}":
            raise ValueError("history cache path changed")
        if step.get("with", {}).get("key") != "${{ env.HISTORY_CACHE_KEY }}":
            raise ValueError("history cache key changed")
    behavior = {key: value for key, value in data.items() if key != "permissions"}
    encoded = json.dumps(behavior, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != _HISTORY_BEHAVIOR_SHA256:
        raise ValueError("history behavior differs from the reviewed baseline")


class TestHistoryPermissions(unittest.TestCase):
    """SEC-HISTORY-01 static boundary and isolated processing regressions."""

    def setUp(self):
        self.workflow = _load_history_workflow()
        _check_history_workflow(self.workflow)
        self.steps = _history_steps(self.workflow)
        temp = tempfile.TemporaryDirectory(prefix="pulse-history-test-")
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        self.history = self.root / "logs/status_history.jsonl"
        self.status = self.root / "pack/artifacts/status.json"
        self.status.parent.mkdir(parents=True)
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("append_status_history.py", "diff_runs_minimal.py"):
            shutil.copyfile(REPO_ROOT / "scripts" / name, scripts / name)
        # Force shell `python` to be the interpreter running these tests.
        bindir = self.root / "bin"
        bindir.mkdir()
        (bindir / "python").symlink_to(sys.executable)
        self.environment = {
            "PATH": str(bindir) + os.pathsep + os.defpath,
            "HOME": str(self.root), "LANG": "C.UTF-8",
            "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "HISTORY_FILE": str(self.history),
            "PACK_DIR": str(self.root / "pack"),
            "GITHUB_RUN_ID": "synthetic-history-2",
            "GITHUB_OUTPUT": str(self.root / "outputs.txt"),
            "GITHUB_STEP_SUMMARY": str(self.root / "summary.md"),
        }

    def run_step(self, name: str, *, success: bool = True):
        allowed = {
            "Ensure logs/ exists (for first run)",
            "Append to status history",
            "Prepare last-two-run status snapshots",
            "Compute minimal diff between last two runs",
            "Workflow summary (diff excerpt)",
            "Check history file exists (guard cache save)",
        }
        if name not in allowed:
            raise ValueError("step is outside local history test execution scope")
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", self.steps[name]["run"]],
            cwd=self.root, env=self.environment, capture_output=True,
            text=True, timeout=20,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def write_history(self, statuses: list[dict]) -> bytes:
        self.history.parent.mkdir(parents=True, exist_ok=True)
        data = "\n".join(json.dumps({"run_id": str(i), "status": status},
                                    ensure_ascii=False)
                         for i, status in enumerate(statuses)) + "\n"
        self.history.write_text(data, encoding="utf-8")
        return self.history.read_bytes()

    def test_contents_read_only_contract(self):
        _check_history_workflow(self.workflow)
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("permissions", self.workflow["jobs"]["history-drift"])

    def test_cache_restore_save_and_upload_order(self):
        names = list(self.steps)
        order = ["Restore status history cache", "Append to status history",
                 "Prepare last-two-run status snapshots",
                 "Compute minimal diff between last two runs",
                 "Check history file exists (guard cache save)",
                 "Save status history cache", "Upload history & drift artefacts"]
        self.assertEqual([n for n in names if n in order], order)
        self.assertEqual(self.steps[order[-2]]["if"],
                         "${{ always() && steps.history_present.outputs.present == 'true' }}")
        self.assertEqual(self.steps[order[-1]]["if"], "always()")
        self.assertEqual(self.steps[order[0]]["with"]["restore-keys"],
                         "${{ env.HISTORY_CACHE_PREFIX }}\n")

    def test_module_is_registered_once_in_both_manifests(self):
        path = "tests/test_reader_surface_non_interference.py"
        for name in ("tools-tests.list", "pytest-tests.list"):
            with self.subTest(manifest=name):
                entries = [line.strip() for line in
                           (REPO_ROOT / "ci" / name).read_text().splitlines()
                           if line.strip() and not line.lstrip().startswith("#")]
                self.assertEqual(entries.count(path), 1)
                self.assertEqual(len(entries), len(set(entries)))

    def test_every_original_shell_block_parses(self):
        for name, step in self.steps.items():
            if "run" in step:
                with self.subTest(step=name):
                    result = subprocess.run(["bash", "-n"], input=step["run"],
                                            text=True, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_yaml_keys_are_rejected(self):
        for source in ("permissions: {}\npermissions: {contents: read}\n",
                       "jobs:\n  x: {}\n  x: {}\n"):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    _load_history_workflow(source)

    def test_missing_workflow_is_rejected(self):
        with self.assertRaises(ValueError):
            _load_history_workflow("")

    def test_non_mapping_workflow_is_rejected(self):
        with self.assertRaises(ValueError):
            _load_history_workflow("- workflow_dispatch")

    def test_unreviewed_step_cannot_be_executed_by_fixture(self):
        for name in ("Run PULSE pack (history/drift context)",
                     "Restore status history cache", "Save status history cache"):
            with self.subTest(step=name):
                with self.assertRaises(ValueError):
                    self.run_step(name)

    def test_first_run_creates_logs_and_does_not_claim_history(self):
        self.run_step("Ensure logs/ exists (for first run)")
        self.assertTrue(self.history.parent.is_dir())
        self.run_step("Check history file exists (guard cache save)")
        self.assertEqual((self.root / "outputs.txt").read_text(), "present=false\n")
        self.run_step("Prepare last-two-run status snapshots")
        self.run_step("Compute minimal diff between last two runs")
        self.assertFalse((self.root / "logs/diff_last_two_runs.json").exists())

    def test_empty_file_counts_as_existing_for_original_save_guard(self):
        self.history.parent.mkdir()
        self.history.touch()
        self.run_step("Check history file exists (guard cache save)")
        self.assertEqual((self.root / "outputs.txt").read_text(), "present=true\n")
        self.run_step("Prepare last-two-run status snapshots")
        self.assertFalse((self.root / "logs/_tmp_diff").exists())

    def test_directory_does_not_count_as_history_file(self):
        self.history.mkdir(parents=True)
        self.run_step("Check history file exists (guard cache save)")
        self.assertEqual((self.root / "outputs.txt").read_text(), "present=false\n")

    def test_single_record_has_no_diff(self):
        before = self.write_history([{"gates": {"g": {"ok": False}}}])
        self.run_step("Prepare last-two-run status snapshots")
        self.run_step("Compute minimal diff between last two runs")
        self.assertFalse((self.root / "logs/diff_last_two_runs.json").exists())
        self.assertEqual(self.history.read_bytes(), before)

    def test_restored_history_uses_last_two_records_deterministically(self):
        statuses = [
            {"gates": {"old": {"ok": False}}},
            {"gates": {"z": {"ok": False}, "a": {"ok": True}}, "note": "árvíz"},
            {"gates": {"a": {"ok": False}, "z": {"ok": True}}, "note": "tűrő"},
        ]
        before = self.write_history(statuses)
        for _ in range(2):
            self.run_step("Prepare last-two-run status snapshots")
            self.run_step("Compute minimal diff between last two runs")
            paths = [self.root / "logs/_tmp_diff/status_prev.json",
                     self.root / "logs/_tmp_diff/status_curr.json",
                     self.root / "logs/diff_last_two_runs.json",
                     self.root / "logs/diff_last_two_runs.md"]
            observed = [p.read_bytes() for p in paths]
            if _ == 0:
                first = observed
            else:
                self.assertEqual(observed, first)
        self.assertEqual(json.loads(paths[0].read_text()), statuses[-2])
        self.assertEqual(json.loads(paths[1].read_text()), statuses[-1])
        diff = json.loads(paths[2].read_text())
        self.assertEqual(diff["summary"]["changed_gates"], 2)
        self.assertEqual(diff["summary"]["pass_to_fail"], 1)
        self.assertEqual(diff["summary"]["fail_to_pass"], 1)
        self.assertEqual([g["id"] for g in diff["gates"]], ["a", "z"])
        self.assertEqual(self.history.read_bytes(), before)

    def test_blank_history_lines_preserve_last_two_selection(self):
        before = self.write_history([{"gates": {}}, {"gates": {"x": {"ok": True}}}])
        self.history.write_bytes(b"\n \n" + before.replace(b"\n", b"\n\n") + b" \n")
        before = self.history.read_bytes()
        self.run_step("Prepare last-two-run status snapshots")
        self.assertEqual(json.loads((self.root / "logs/_tmp_diff/status_curr.json").read_text()),
                         {"gates": {"x": {"ok": True}}})
        self.assertEqual(self.history.read_bytes(), before)

    def test_append_preserves_existing_history_and_source_status(self):
        before = self.write_history([{"gates": {"g": {"ok": False}}}])
        current = {"gates": {"g": {"ok": True}}, "note": "őrzött"}
        self.status.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        status_before = self.status.read_bytes()
        self.run_step("Append to status history")
        appended = self.history.read_bytes()
        self.assertTrue(appended.startswith(before))
        records = [json.loads(line) for line in appended.splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1]["run_id"], "synthetic-history-2")
        self.assertEqual(records[-1]["status"], current)
        self.assertEqual(self.status.read_bytes(), status_before)
        self.run_step("Prepare last-two-run status snapshots")
        self.run_step("Compute minimal diff between last two runs")
        self.run_step("Check history file exists (guard cache save)")
        self.assertEqual((self.root / "outputs.txt").read_text(), "present=true\n")
        self.assertEqual(self.history.read_bytes(), appended)
        self.assertEqual(self.status.read_bytes(), status_before)

    def test_append_first_record_without_prior_cache(self):
        self.status.write_text('{"gates": {}}')
        self.run_step("Append to status history")
        self.assertEqual(len(self.history.read_text().splitlines()), 1)
        self.run_step("Prepare last-two-run status snapshots")
        self.assertFalse((self.root / "logs/_tmp_diff").exists())

    def test_invalid_status_does_not_append(self):
        before = self.write_history([{"gates": {}}])
        for raw in ("{", "[]", "null", '"not-status"'):
            with self.subTest(raw=raw):
                self.status.write_text(raw)
                self.run_step("Append to status history", success=False)
                self.assertEqual(self.history.read_bytes(), before)

    def test_missing_status_does_not_append(self):
        before = self.write_history([{"gates": {}}])
        self.run_step("Append to status history", success=False)
        self.assertEqual(self.history.read_bytes(), before)

    def test_missing_append_script_fails(self):
        (self.root / "scripts/append_status_history.py").unlink()
        self.status.write_text('{"gates": {}}')
        self.run_step("Append to status history", success=False)
        self.assertFalse(self.history.exists())

    def test_malformed_last_record_fails_snapshot_processing(self):
        before = self.write_history([{"gates": {}}]) + b"{broken\n"
        self.history.write_bytes(before)
        self.run_step("Prepare last-two-run status snapshots", success=False)
        self.assertEqual(self.history.read_bytes(), before)
        self.assertFalse((self.root / "logs/diff_last_two_runs.json").exists())

    def test_missing_diff_script_fails(self):
        (self.root / "scripts/diff_runs_minimal.py").unlink()
        self.run_step("Compute minimal diff between last two runs", success=False)

    def test_invalid_snapshot_fails_diff_without_altering_inputs(self):
        folder = self.root / "logs/_tmp_diff"
        folder.mkdir(parents=True)
        prev = folder / "status_prev.json"
        curr = folder / "status_curr.json"
        prev.write_text('{"gates": {}}')
        curr.write_text("{")
        before = _snapshot([prev, curr])
        self.run_step("Compute minimal diff between last two runs", success=False)
        _assert_snapshot_unchanged(before, [prev, curr])
        self.assertFalse((self.root / "logs/diff_last_two_runs.json").exists())

    def test_summary_first_run_is_explicit(self):
        self.run_step("Workflow summary (diff excerpt)")
        text = (self.root / "summary.md").read_text()
        self.assertIn("No diff generated", text)
        self.assertNotIn("Cache saved", text)

    def test_summary_copies_existing_diff_without_changing_it(self):
        self.history.parent.mkdir()
        diff = self.root / "logs/diff_last_two_runs.md"
        diff.write_text("# fixed diagnostic\n", encoding="utf-8")
        before = diff.read_bytes()
        self.run_step("Workflow summary (diff excerpt)")
        self.assertIn("# fixed diagnostic", (self.root / "summary.md").read_text())
        self.assertEqual(diff.read_bytes(), before)


# Each mutation is separately collected by pytest and the direct unittest runner.
# These are negative static-contract fixtures, not GitHub permission probes.
_HISTORY_MUTATIONS = {
    "actions_write": (("permissions", "actions"), "write"),
    "contents_write": (("permissions", "contents"), "write"),
    "write_all": (("permissions",), "write-all"),
    "missing_permission_map": (("permissions",), None),
    "id_token_write": (("permissions", "id-token"), "write"),
    "packages_write": (("permissions", "packages"), "write"),
    "job_permission_override": (("jobs", "history-drift", "permissions"), {"actions": "write"}),
    "additional_job": (("jobs", "other"), {"permissions": "write-all"}),
    "automatic_trigger": (("on", "push"), {}),
    "untrusted_trigger": (("on", "pull_request_target"), {}),
    "missing_cache_pin": (("jobs", "history-drift", "steps", 2, "uses"), "actions/cache/restore"),
    "moving_restore_pin": (("jobs", "history-drift", "steps", 2, "uses"), "actions/cache/restore@main"),
    "wrong_save_source": (("jobs", "history-drift", "steps", 11, "uses"), "other/cache/save@" + _HISTORY_CACHE_REVISION),
    "missing_save_source": (("jobs", "history-drift", "steps", 11, "uses"), ""),
    "cache_path": (("jobs", "history-drift", "steps", 2, "with", "path"), "."),
    "save_key": (("jobs", "history-drift", "steps", 11, "with", "key"), "unscoped"),
    "restore_prefix": (("jobs", "history-drift", "steps", 2, "with", "restore-keys"), "pulse-history-"),
    "save_guard": (("jobs", "history-drift", "steps", 11, "if"), "always()"),
    "history_path": (("env", "HISTORY_FILE"), "status.json"),
    "branch_scope": (("env", "HISTORY_CACHE_PREFIX"), "pulse-history-"),
    "run_scope": (("env", "HISTORY_CACHE_KEY"), "pulse-history-${{ github.ref_name }}"),
    "persist_credentials": (("jobs", "history-drift", "steps", 0, "with", "persist-credentials"), "true"),
    "hidden_script": (("jobs", "history-drift", "steps", 1, "run"), "git push"),
    "cache_mode_override": (("cache-mode",), "write"),
    "history_env_token": (("env", "GITHUB_TOKEN"), "${{ secrets.GITHUB_TOKEN }}"),
    "save_failure_masking": (("jobs", "history-drift", "steps", 11, "continue-on-error"), "true"),
}


def _history_mutation_test(path, replacement):
    def test(self):
        changed = copy.deepcopy(self.workflow)
        node = changed
        for component in path[:-1]:
            node = node[component]
        node[path[-1]] = copy.deepcopy(replacement)
        self.assertNotEqual(changed, self.workflow, "mutation must change its target")
        with self.assertRaises(ValueError):
            _check_history_workflow(changed)
    return test


for _case, (_path, _replacement) in _HISTORY_MUTATIONS.items():
    setattr(TestHistoryPermissions, "test_reject_" + _case,
            _history_mutation_test(_path, _replacement))


def _run_history_regressions() -> bool:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHistoryPermissions)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return (result.wasSuccessful() and not result.skipped
            and result.testsRun == suite_count_history_tests())


def suite_count_history_tests() -> int:
    return len(unittest.defaultTestLoader.getTestCaseNames(TestHistoryPermissions))


def main() -> int:
    try:
        test_reader_surface_tools_do_not_mutate_release_authority_inputs()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    if not _run_history_regressions():
        return 1

    print("OK: reader-surface and history non-interference tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
