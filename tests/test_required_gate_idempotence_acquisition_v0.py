#!/usr/bin/env python3
"""Synthetic acquisition orchestration and fail-closed preservation regressions.

The selected sanitizer is never imported or executed by this module. Controlled
runner results exercise the collector and its unchanged offline observation
contract; dedicated process tests use only authored inert fixture programs.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative_path: str):
    if name not in sys.modules:
        tools_path = str(ROOT / "tools")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        specification = importlib.util.spec_from_file_location(name, ROOT / relative_path)
        assert specification is not None and specification.loader is not None
        module = importlib.util.module_from_spec(specification)
        sys.modules[name] = module
        specification.loader.exec_module(module)
    return sys.modules[name]


def acquisition():
    return _module("idempotence_acquisition_under_test", "tools/acquire_required_gate_idempotence_v0.py")


def observation_examples():
    return _module("idempotence_observation_examples", "tests/test_required_gate_idempotence_observation_v0.py")


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def boundaries(record):
    assert record["execution_ready"] is False
    assert record["execution_authorized"] is False
    assert record["runtime_closure_verified"] is False
    assert record["actual_reference_claimed"] is False
    assert record["property_semantics_verified"] is False
    assert record["metric_pass"] is None
    assert record["production_gate_eligible"] is False
    assert record["authority_effect"] == "none"


def example_selection():
    example = observation_examples().Example()
    selected = [copy.deepcopy(row) for row in example.selection["sources"]
                if row["role"] in {"operator", "operator_dependency"}]
    sources = {row["path"]: example.members[row["member"]] for row in selected}
    for role, path in (
        ("worker", "tools/required_gate_idempotence_worker_v0.py"),
        ("collector", "tools/acquire_required_gate_idempotence_v0.py"),
        ("implementation_dependency", "tools/required_gate_idempotence_process_v0.py"),
    ):
        raw = (ROOT / path).read_bytes()
        selected.append({"role": role, "path": path,
                         "source_revision": example.selection["source_commit"],
                         "sha256": digest(raw), "size_bytes": len(raw), "member": "sources/" + path})
        sources[path] = raw
    example.selection["sources"] = selected
    return example.selection, sources


def prepare(selection=None, sources=None):
    if selection is None:
        selection, sources = example_selection()
    raw = encoded(selection)
    return acquisition().prepare_selection(selection_bytes=raw,
                                           expected_selection_sha256=digest(raw),
                                           source_bytes=sources)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ScriptedRunner:
    """Author process records and differing outputs; never launch the operator."""

    def __init__(self, *, fail_at=None, mutate=None, raised=None):
        self.calls = []
        self.results = []
        self.fail_at = fail_at
        self.mutate = mutate
        self.raised = raised

    def __call__(self, *, application_id, input_bytes, input_descriptor, deadline, sink):
        index = len(self.calls)
        self.calls.append({"application_id": application_id, "input_bytes": input_bytes,
                           "input_descriptor": copy.deepcopy(input_descriptor), "deadline": deadline})
        started_utc, started_mono = utc_now(), time.monotonic_ns()
        stdout = encoded({"synthetic_occurrence": index + 1})
        stderr = b"synthetic diagnostic\n"
        sink("stdout", stdout)
        sink("stderr", stderr)
        if self.raised is not None and index == self.fail_at:
            raise self.raised
        result = {
            "process_id": os.getpid() + 1000 + index,
            "started_utc": started_utc, "completed_utc": utc_now(),
            "started_monotonic_ns": started_mono, "completed_monotonic_ns": time.monotonic_ns(),
            "exit_code": 0, "status": "complete", "error_code": None,
            "input_read_sha256": digest(input_bytes), "input_read_size_bytes": len(input_bytes),
            "input_read_complete": True,
            "snapshot_bytes": encoded({"metrics": {"synthetic_value": index + 1}}),
            "metadata_bytes": encoded({"synthetic": True, "occurrence": index + 1}),
            "stderr_bytes": stderr, "stdout_bytes": stdout, "worker_report": {},
        }
        if index == self.fail_at:
            result.update(status="incomplete", exit_code=17, error_code="synthetic_worker_failed")
        if self.mutate is not None:
            self.mutate(index, result)
        self.results.append(copy.deepcopy(result))
        return result


def collect(tmp_path, runner=None, prepared=None):
    runner = runner or ScriptedRunner()
    destination = tmp_path / "attempt"
    result = acquisition().collect_example(prepared=prepared or prepare(),
                                           output_directory=destination, runner=runner)
    return result, destination, runner


def check_complete_carrier(destination: Path):
    selection = (destination / "selection.json").read_bytes()
    carrier = (destination / "acquisition.zip").read_bytes()
    return observation_examples().checker().verify_observation(
        selection_bytes=selection, expected_selection_sha256=digest(selection),
        carrier_bytes=carrier, expected_carrier_sha256=digest(carrier))


@pytest.fixture(scope="module")
def completed_example(tmp_path_factory):
    return collect(tmp_path_factory.mktemp("completed-idempotence-example"))


def test_complete_synthetic_collector_preserves_all_twenty_four_relations(completed_example):
    summary, destination, runner = completed_example
    assert summary["status"] == "complete"
    assert summary["completed_applications"] == 24
    assert summary["attempted_applications"] == 24
    assert summary["expected_applications"] == 24
    assert summary["failure_code"] is None
    assert summary["failed_application_id"] is None
    assert summary["synthetic_execution"] is True
    assert summary["record_status"] == "example"
    boundaries(summary)
    assert len(runner.calls) == 24
    assert [row["application_id"] for row in runner.calls] == [
        "idem-%02d.%s" % (case, phase) for case in range(1, 13) for phase in ("first", "second")]
    report = check_complete_carrier(destination)
    assert report["ok"] is True
    assert report["case_count"] == 12
    assert report["application_count"] == 24
    assert report["source_git_binding_verified"] is False
    boundaries(report)
    assert summary["carrier_sha256"] == digest((destination / "acquisition.zip").read_bytes())


@pytest.mark.parametrize("case_index", range(12))
def test_second_application_consumes_own_first_bytes_and_state(completed_example, case_index):
    summary, destination, runner = completed_example
    assert summary["status"] == "complete"
    first = runner.calls[2 * case_index]
    second = runner.calls[2 * case_index + 1]
    assert second["input_bytes"] == runner.results[2 * case_index]["snapshot_bytes"]
    assert second["input_bytes"] != first["input_bytes"]
    first_receipt = json.loads((destination / "receipts" / (first["application_id"] + ".json")).read_bytes())
    assert second["input_descriptor"] == first_receipt["snapshot"]
    assert second["input_descriptor"]["state_id"] != first["input_descriptor"]["state_id"]
    assert runner.results[2 * case_index + 1]["snapshot_bytes"] != second["input_bytes"]


def test_original_input_bytes_are_not_reserialized(completed_example):
    summary, _, runner = completed_example
    assert summary["status"] == "complete"
    catalog = json.loads((ROOT / "docs/compute/required_gate_idempotence_protocol_v0/inputs_v0.json").read_bytes())
    assert [row["input_bytes"] for row in runner.calls[::2]] == [
        case["input_utf8"].encode("utf-8") for case in catalog["cases"]]


@pytest.mark.parametrize("fail_at", [0, 1, 7, 23])
def test_worker_failure_preserves_prefix_and_stops_without_retry(tmp_path, fail_at):
    summary, destination, runner = collect(tmp_path, ScriptedRunner(fail_at=fail_at))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == fail_at
    assert summary["attempted_applications"] == fail_at + 1
    assert len(runner.calls) == fail_at + 1
    assert summary["failure_code"] == "worker_incomplete"
    assert summary["failed_application_id"] == runner.calls[-1]["application_id"]
    assert summary["carrier_sha256"] is None
    boundaries(summary)
    assert not (destination / "acquisition.zip").exists()
    assert (destination / "attempt.started.json").is_file()
    assert (destination / "attempt.json").is_file()
    for index, call in enumerate(runner.calls):
        application_id = call["application_id"]
        assert (destination / "raw" / (application_id + ".stdout")).read_bytes() == runner.results[index]["stdout_bytes"]
        assert (destination / "raw" / (application_id + ".stderr")).read_bytes() == runner.results[index]["stderr_bytes"]
    assert len(list((destination / "receipts").glob("*.json"))) == fail_at


@pytest.mark.parametrize("exception,code", [
    (RuntimeError("untrusted sensitive detail must not be copied"), "runner_error"),
    (KeyboardInterrupt(), "runner_interrupted"),
    (SystemExit(0), "runner_interrupted"),
])
def test_runner_exception_retains_started_occurrence_and_raw_prefix(tmp_path, exception, code):
    summary, destination, runner = collect(tmp_path, ScriptedRunner(fail_at=2, raised=exception))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 2
    assert summary["attempted_applications"] == 3
    assert len(runner.calls) == 3
    assert summary["failure_code"] == code
    assert (destination / "raw/idem-02.first.stderr").read_bytes() == b"synthetic diagnostic\n"
    assert b"untrusted sensitive detail" not in (destination / "attempt.json").read_bytes()
    assert not (destination / "acquisition.zip").exists()


def test_attempt_and_occurrence_start_are_durable_before_runner(tmp_path):
    destination = tmp_path / "attempt"
    scripted = ScriptedRunner(fail_at=0)

    def runner(**arguments):
        assert (destination / "selection.json").is_file()
        assert (destination / "sources.zip").is_file()
        assert (destination / "attempt.started.json").is_file()
        event = json.loads((destination / "events/0001.started.json").read_bytes())
        assert event["application_id"] == arguments["application_id"]
        assert event["input"] == arguments["input_descriptor"]
        assert not (destination / "attempt.json").exists()
        return scripted(**arguments)

    summary = acquisition().collect_example(prepared=prepare(), output_directory=destination, runner=runner)
    assert summary["status"] == "incomplete"
    assert len(scripted.calls) == 1


def test_failed_worker_lifecycle_is_preserved_before_receipt_rejection(tmp_path):
    summary, destination, runner = collect(tmp_path, ScriptedRunner(fail_at=0))
    assert summary["status"] == "incomplete"
    result = runner.results[0]
    journal = json.loads((destination / "events/0001.result.json").read_bytes())
    assert journal["application_id"] == "idem-01.first"
    assert journal["synthetic_execution"] is True
    for key in ("process_id", "started_utc", "completed_utc", "started_monotonic_ns",
                "completed_monotonic_ns", "exit_code", "status", "error_code",
                "input_read_sha256", "input_read_size_bytes", "input_read_complete"):
        assert journal["capture"][key] == result[key]
    assert journal["invalid_fields"] == []
    for role in ("snapshot", "metadata", "stdout", "stderr"):
        raw = result[role + "_bytes"]
        assert journal["outputs"][role] == {
            "observed_size_bytes": len(raw), "retained_prefix": {"sha256": digest(raw), "size_bytes": len(raw)},
            "truncated": False}
    assert not (destination / "receipts/idem-01.first.json").exists()


def test_oversized_output_preserves_exact_prefix_and_explicit_truncation_facts(tmp_path):
    oversized = b"bounded prefix" * 400

    def mutate(index, result):
        result["snapshot_bytes"] = oversized

    summary, destination, runner = collect(tmp_path, ScriptedRunner(mutate=mutate))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 0
    assert len(runner.calls) == 1
    journal = json.loads((destination / "events/0001.result.json").read_bytes())
    prefix = oversized[:4096]
    assert journal["outputs"]["snapshot"] == {
        "observed_size_bytes": len(oversized),
        "retained_prefix": {"sha256": digest(prefix), "size_bytes": 4096}, "truncated": True}
    assert (destination / "produced/idem-01.first.snapshot.json").read_bytes() == prefix
    assert not (destination / "receipts/idem-01.first.json").exists()
    assert not (destination / "acquisition.zip").exists()


@pytest.mark.parametrize("channel,maximum", [("stdout", 20480), ("stderr", 4096)])
def test_collector_stream_overflow_retains_exact_bounded_prefix(tmp_path, channel, maximum):
    calls = []

    def runner(**arguments):
        calls.append(arguments["application_id"])
        arguments["sink"](channel, b"p" * (maximum + 1))
        raise AssertionError("stream overflow must interrupt the occurrence")

    summary, destination, _ = collect(tmp_path, runner)
    assert summary["status"] == "incomplete"
    assert summary["failure_code"] == "stream_size_limit"
    assert calls == ["idem-01.first"]
    assert (destination / "raw" / ("idem-01.first." + channel)).read_bytes() == b"p" * maximum
    assert not (destination / "acquisition.zip").exists()


def test_exhausted_suite_budget_stops_before_first_runner(tmp_path, monkeypatch):
    module = acquisition()
    limits = dict(module.LIMITS, suite_wall_seconds=0)
    monkeypatch.setattr(module, "LIMITS", limits)
    summary, destination, runner = collect(tmp_path)
    assert summary["status"] == "incomplete"
    assert summary["failure_code"] == "suite_wall_time_limit"
    assert summary["attempted_applications"] == 0
    assert summary["completed_applications"] == 0
    assert runner.calls == []
    assert (destination / "attempt.started.json").is_file()
    assert not (destination / "acquisition.zip").exists()


def test_journal_io_exhausting_suite_budget_cannot_launch_late_runner(tmp_path, monkeypatch):
    module = acquisition()
    clock = {"offset": 0.0}
    real_write = module._Directory.write

    def write_then_expire(directory, relative, data):
        real_write(directory, relative, data)
        if relative == "events/0001.started.json":
            clock["offset"] += 1000.0

    monkeypatch.setattr(module, "time", SimpleNamespace(
        monotonic=lambda: time.monotonic() + clock["offset"], monotonic_ns=time.monotonic_ns))
    monkeypatch.setattr(module._Directory, "write", write_then_expire)
    summary, destination, runner = collect(tmp_path)
    assert summary["status"] == "incomplete"
    assert summary["failure_code"] == "suite_wall_time_limit"
    assert summary["attempted_applications"] == 0
    assert summary["completed_applications"] == 0
    assert summary["attempted_application_ids"] == []
    assert runner.calls == []
    assert (destination / "events/0001.started.json").is_file()
    assert (destination / "raw/idem-01.first.stdout").read_bytes() == b""
    assert (destination / "raw/idem-01.first.stderr").read_bytes() == b""
    assert not (destination / "events/0001.result.json").exists()
    assert not (destination / "acquisition.zip").exists()
    preserved = {item["member"] for item in summary["files"]}
    assert {"events/0001.started.json", "raw/idem-01.first.stdout", "raw/idem-01.first.stderr"} <= preserved


@pytest.mark.parametrize("field,value", [
    ("input_read_sha256", "0" * 64),
    ("input_read_size_bytes", 0),
    ("input_read_complete", False),
    ("exit_code", 9),
    ("process_id", 0),
    ("snapshot_bytes", b'{"metrics":true}\n'),
    ("snapshot_bytes", b'{"metrics":"not-numeric"}\n'),
    ("snapshot_bytes", b'{"metrics":[]}\n'),
    ("snapshot_bytes", b'{"metrics":null}\n'),
    ("snapshot_bytes", b'{ "metrics":1 }\n'),
    ("snapshot_bytes", b'{"metrics":NaN}\n'),
    ("snapshot_bytes", b'{"metrics":1e999}\n'),
    ("snapshot_bytes", b'{"metrics":1,"metrics":2}\n'),
    ("snapshot_bytes", b"x" * 4097),
    ("metadata_bytes", b"[]\n"),
    ("metadata_bytes", b"x" * 4097),
    ("stderr_bytes", b"x" * 4097),
])
def test_invalid_worker_result_never_supplies_next_application(tmp_path, field, value):
    def mutate(index, result):
        if index == 0:
            result[field] = value

    summary, destination, runner = collect(tmp_path, ScriptedRunner(mutate=mutate))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 0
    assert summary["attempted_applications"] == 1
    assert len(runner.calls) == 1
    assert summary["failure_code"]
    assert not (destination / "acquisition.zip").exists()
    assert (destination / "raw/idem-01.first.stdout").is_file()


def test_process_identity_reuse_is_incomplete_without_fabricated_replacement(tmp_path):
    def mutate(index, result):
        result["process_id"] = os.getpid() + 1000

    summary, destination, runner = collect(tmp_path, ScriptedRunner(mutate=mutate))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 1
    assert summary["attempted_applications"] == 2
    assert len(runner.calls) == 2
    assert not (destination / "acquisition.zip").exists()


def test_collector_process_cannot_be_relabelled_as_subject_worker(tmp_path):
    def mutate(index, result):
        result["process_id"] = os.getpid()

    summary, _, runner = collect(tmp_path, ScriptedRunner(mutate=mutate))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 0
    assert len(runner.calls) == 1


@pytest.mark.parametrize("change", ["negative", "over_wall", "utc_reverse", "outside_capture"])
def test_invalid_worker_time_is_preserved_as_incomplete(tmp_path, change):
    def mutate(index, result):
        if change == "negative":
            result["completed_monotonic_ns"] = result["started_monotonic_ns"] - 1
        elif change == "over_wall":
            result["completed_monotonic_ns"] = result["started_monotonic_ns"] + 5_000_000_001
        elif change == "utc_reverse":
            result["completed_utc"] = "2000-01-01T00:00:00Z"
        else:
            result["started_monotonic_ns"] = 0
            result["completed_monotonic_ns"] = 1

    summary, _, runner = collect(tmp_path, ScriptedRunner(mutate=mutate))
    assert summary["status"] == "incomplete"
    assert summary["completed_applications"] == 0
    assert len(runner.calls) == 1


def test_existing_output_directory_cannot_start_or_overwrite_an_attempt(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_bytes(b"owner data\n")
    runner = ScriptedRunner()
    with pytest.raises(acquisition().AcquisitionError):
        acquisition().collect_example(prepared=prepare(), output_directory=destination, runner=runner)
    assert runner.calls == []
    assert marker.read_bytes() == b"owner data\n"
    assert sorted(item.name for item in destination.iterdir()) == ["keep.txt"]


def test_same_attempt_directory_cannot_be_reused_after_failure(tmp_path):
    prepared = prepare()
    summary, destination, first_runner = collect(tmp_path, ScriptedRunner(fail_at=0), prepared)
    assert summary["status"] == "incomplete"
    before = {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    second_runner = ScriptedRunner()
    with pytest.raises(acquisition().AcquisitionError):
        acquisition().collect_example(prepared=prepared, output_directory=destination, runner=second_runner)
    assert len(first_runner.calls) == 1
    assert second_runner.calls == []
    assert {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("symlink_parent", [False, True])
def test_symlink_output_paths_are_rejected_before_runner(tmp_path, symlink_parent):
    target = tmp_path / "real"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    destination = alias / "attempt" if symlink_parent else alias
    runner = ScriptedRunner()
    with pytest.raises(acquisition().AcquisitionError):
        acquisition().collect_example(prepared=prepare(), output_directory=destination, runner=runner)
    assert runner.calls == []
    assert list(target.iterdir()) == []


def test_selection_digest_is_independently_required():
    selection, sources = example_selection()
    with pytest.raises(acquisition().AcquisitionError):
        acquisition().prepare_selection(selection_bytes=encoded(selection),
                                        expected_selection_sha256="0" * 64, source_bytes=sources)


@pytest.mark.parametrize("role", ["worker", "collector", "implementation_dependency", "operator"])
def test_source_byte_substitution_rejects_before_acquisition(role):
    selection, sources = example_selection()
    row = next(item for item in selection["sources"] if item["role"] == role)
    sources[row["path"]] += b"\n# substituted source\n"
    with pytest.raises(acquisition().AcquisitionError):
        prepare(selection, sources)


@pytest.mark.parametrize("role", ["worker", "collector", "implementation_dependency"])
def test_repinning_different_installed_implementation_does_not_select_it(role):
    selection, sources = example_selection()
    row = next(item for item in selection["sources"] if item["role"] == role)
    replacement = sources[row["path"]] + b"\n# substituted implementation\n"
    sources[row["path"]] = replacement
    row["sha256"], row["size_bytes"] = digest(replacement), len(replacement)
    with pytest.raises(acquisition().AcquisitionError):
        prepare(selection, sources)


def test_missing_process_dependency_rejects_preparation():
    selection, sources = example_selection()
    selection["sources"] = [row for row in selection["sources"] if row["role"] != "implementation_dependency"]
    with pytest.raises(acquisition().AcquisitionError):
        prepare(selection, sources)


def test_preparation_captures_source_bytes_before_caller_mutation(tmp_path):
    selection, sources = example_selection()
    prepared = prepare(selection, sources)
    for path in sources:
        sources[path] = b"replacement after preparation\n"
    summary, destination, _ = collect(tmp_path, prepared=prepared)
    assert summary["status"] == "complete"
    assert check_complete_carrier(destination)["ok"] is True


def test_preparation_is_explicitly_non_authorizing():
    report = acquisition().preparation_report(prepare())
    boundaries(report)


def test_preparation_constructor_cannot_create_an_admitted_record():
    module = acquisition()
    prepared = prepare()
    with pytest.raises(module.AcquisitionError, match="preparation_direct_construction_forbidden"):
        module.PreparedSelection(prepared.selection_bytes, prepared.members)


@pytest.mark.parametrize("operation", ["report", "archive", "write", "collect"])
def test_serialized_admission_assertion_cannot_restore_preparation(tmp_path, operation):
    module = acquisition()
    original = prepare()
    forged = object.__new__(module.PreparedSelection)
    object.__setattr__(forged, "selection_bytes", original.selection_bytes)
    object.__setattr__(forged, "members", original.members)
    object.__setattr__(forged, "_admission", True)
    destination = tmp_path / "forged"
    runner = ScriptedRunner()
    with pytest.raises(module.AcquisitionError, match="preparation_required"):
        if operation == "report":
            module.preparation_report(forged)
        elif operation == "archive":
            module.source_archive(forged)
        elif operation == "write":
            module.write_preparation(forged, destination)
        else:
            module.collect_example(prepared=forged, output_directory=destination, runner=runner)
    assert not destination.exists()
    assert runner.calls == []


def test_returned_selection_is_a_copy_of_admitted_immutable_bytes(tmp_path):
    prepared = prepare()
    inspected = prepared.selection
    inspected["record_status"] = "observed"
    inspected["sources"][0]["sha256"] = "0" * 64
    summary, _, _ = collect(tmp_path, prepared=prepared)
    assert summary["status"] == "complete"
    assert summary["record_status"] == "example"


def test_relabelling_example_preparation_observed_cannot_launch(tmp_path):
    module = acquisition()
    prepared = prepare()
    changed = prepared.selection
    changed["record_status"] = "observed"
    object.__setattr__(prepared, "selection_bytes", encoded(changed))
    runner = ScriptedRunner()
    destination = tmp_path / "observed"
    with pytest.raises(module.AcquisitionError, match="observed_acquisition_not_ready"):
        module.collect_example(prepared=prepared, output_directory=destination, runner=runner)
    assert not destination.exists()
    assert runner.calls == []


def test_observed_selection_cannot_override_git_sources_with_in_memory_bytes():
    selection, sources = example_selection()
    selection["record_status"] = "observed"
    with pytest.raises(acquisition().AcquisitionError, match="observed_source_override_forbidden"):
        prepare(selection, sources)


def test_preparation_bundle_has_acyclic_complete_byte_inventory(tmp_path):
    module = acquisition()
    prepared = prepare()
    destination = tmp_path / "prepared"
    report = module.write_preparation(prepared, destination)
    boundaries(report)
    assert report["operator_applications"] == 0
    assert report["observed_acquisition_supported"] is False
    assert report["host_environment_qualified"] is False
    raw = (destination / "sources.zip").read_bytes()
    assert report["source_archive"] == {"member": "sources.zip", "sha256": digest(raw), "size_bytes": len(raw)}
    members = observation_examples().checker().read_archive(raw)
    inventory_name = "preparation/member_inventory.json"
    inventory = json.loads(members[inventory_name])
    assert {item["member"] for item in inventory["members"]} == set(members) - {inventory_name}
    assert members["selection/pre_acquisition_selection.json"] == prepared.selection_bytes
    assert not any(name.startswith(("snapshots/", "metadata/", "diagnostics/", "capture/")) for name in members)
    for item in inventory["members"]:
        assert item["sha256"] == digest(members[item["member"]])
        assert item["size_bytes"] == len(members[item["member"]])
    outside = json.loads((destination / "preparation_inventory.json").read_bytes())
    assert {item["member"] for item in outside["files"]} == {"selection.json", "sources.zip", "preparation.json"}
    for item in outside["files"]:
        preserved = (destination / item["member"]).read_bytes()
        assert item["sha256"] == digest(preserved)
        assert item["size_bytes"] == len(preserved)


@pytest.mark.parametrize("fail_at", [None, 0, 7])
def test_terminal_attempt_inventory_binds_every_preserved_file(tmp_path, fail_at):
    summary, destination, _ = collect(tmp_path, ScriptedRunner(fail_at=fail_at))
    actual = {path.relative_to(destination).as_posix(): path.read_bytes()
              for path in destination.rglob("*") if path.is_file()}
    assert json.loads(actual["attempt.json"]) == summary
    assert {item["member"] for item in summary["files"]} == set(actual) - {"attempt.json"}
    assert len(summary["files"]) == len(set(item["member"] for item in summary["files"]))
    for item in summary["files"]:
        assert item["sha256"] == digest(actual[item["member"]])
        assert item["size_bytes"] == len(actual[item["member"]])
    assert destination.stat().st_mode & 0o777 == 0o700
    for path in destination.rglob("*"):
        assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600)


def test_cli_observed_launch_is_closed_before_input_read_or_output_creation(tmp_path):
    output = tmp_path / "must-not-exist"
    result = subprocess.run([sys.executable, str(ROOT / "tools/acquire_required_gate_idempotence_v0.py"),
                             "acquire"],
                            capture_output=True, timeout=15)
    assert result.returncode != 0
    assert b"observed_acquisition_not_ready" in result.stdout + result.stderr
    assert not output.exists()


def process_module():
    return _module("idempotence_process_under_test", "tools/required_gate_idempotence_process_v0.py")


SYNTHETIC_SOURCE_PATHS = (
    "PULSE_safe_pack_v0/epf/epf_hazard_features.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_forecast.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_field_spec.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_adapter.py",
)


def synthetic_sources(body="return {'metrics': {'synthetic': -0.0}}, {'synthetic': True}", *, prelude=""):
    """Only authored source is evaluated by child process regression tests."""
    result = {path: b"# Authored inert synthetic dependency; not selected repository source.\n"
              for path in SYNTHETIC_SOURCE_PATHS}
    result[SYNTHETIC_SOURCE_PATHS[-1]] = (
        "# Authored synthetic callable; not the selected sanitizer.\n" + prelude +
        "\ndef sanitize_snapshot_for_log(value, **configuration):\n" +
        textwrap.indent(textwrap.dedent(body), "    ") + "\n").encode("utf-8")
    return result


def process_arguments(**changes):
    interpreter = Path(sys.executable).resolve()
    arguments = {
        "worker_bytes": (ROOT / "tools/required_gate_idempotence_worker_v0.py").read_bytes(),
        "source_bytes": synthetic_sources(), "input_bytes": b'{ "metrics": {"public": 1} }\n',
        "configuration": {"max_depth": 2, "max_items": 3, "allowed_prefixes": ["metrics"],
                          "deny_keys": ["metrics.pii", "metrics.secret"]},
        "application_id": "idem-01.first", "interpreter": interpreter,
        "expected_interpreter_sha256": digest(interpreter.read_bytes()),
        "deadline": time.monotonic() + 10,
    }
    arguments.update(changes)
    return arguments


def run_synthetic_process(body=None, *, prelude="", **changes):
    if body is not None:
        changes["source_bytes"] = synthetic_sources(body, prelude=prelude)
    return process_module().run_worker(**process_arguments(**changes))


def test_real_worker_process_reads_exact_synthetic_bytes_under_limits():
    arguments = process_arguments()
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    result = process_module().run_worker(**arguments, sink=lambda channel, raw: streams[channel].extend(raw))
    assert result["status"] == "complete", result
    assert result["exit_code"] == 0
    assert result["error_code"] is None
    assert result["process_id"] != os.getpid()
    assert result["input_read_sha256"] == digest(arguments["input_bytes"])
    assert result["input_read_size_bytes"] == len(arguments["input_bytes"])
    assert result["input_read_complete"] is True
    assert result["snapshot_bytes"] == b'{"metrics":{"synthetic":-0.0}}\n'
    assert result["metadata_bytes"] == b'{"synthetic":true}\n'
    assert result["worker_report"]["sandbox"]["no_new_privs"] is True
    assert result["worker_report"]["sandbox"]["seccomp_mode"] == 2
    assert result["worker_report"]["sandbox"]["rlimit_cpu_seconds"] == 2
    assert result["worker_report"]["sandbox"]["rlimit_as_bytes"] == 256 * 1024 * 1024
    assert result["completed_monotonic_ns"] - result["started_monotonic_ns"] < 5_000_000_000
    assert dict((name, bytes(raw)) for name, raw in streams.items()) == {
        "stdout": result["stdout_bytes"], "stderr": result["stderr_bytes"]}


def test_selected_interpreter_library_path_replaces_ambient_loader_environment(monkeypatch):
    process = process_module()
    real_popen = process.subprocess.Popen
    captured_environments = []

    def capture_real_spawn(*args, **kwargs):
        captured_environments.append(dict(kwargs["env"]))
        return real_popen(*args, **kwargs)

    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/unselected-synthetic-libraries")
    monkeypatch.setenv("LD_PRELOAD", "/tmp/unselected-synthetic-preload.so")
    monkeypatch.setenv("PYTHONPATH", "/tmp/unselected-synthetic-pythonpath")
    monkeypatch.setenv("PYTHONHOME", "/tmp/unselected-synthetic-pythonhome")
    monkeypatch.setattr(process.subprocess, "Popen", capture_real_spawn)
    arguments = process_arguments()
    selected_library_directory = arguments["interpreter"].parent.parent / "lib"
    assert selected_library_directory.is_dir()
    result = process.run_worker(**arguments)
    assert result["status"] == "complete", result
    assert captured_environments == [{"LC_ALL": "C", "TZ": "UTC",
                                     "LD_LIBRARY_PATH": str(selected_library_directory)}]
    assert result["stderr_bytes"] == b""


@pytest.mark.parametrize("operation", [
    "open('/etc/passwd', 'rb')",
    "os.open('/etc/passwd', os.O_RDONLY)",
    "os.open('/tmp/idempotence-synthetic-forbidden-write', os.O_WRONLY | os.O_CREAT, 0o600)",
    "os.fork()",
    "os.execv('/bin/true', ['/bin/true'])",
    "os.dup(1)",
    "os.read(0, 1)",
])
def test_selected_source_boundary_denies_ambient_capabilities(operation):
    body = """
        import errno
        import os
        try:
            OPERATION
        except OSError as error:
            denied = int(error.errno == errno.EPERM)
        else:
            denied = 0
        return {'metrics': {'denied': denied}}, {'synthetic': True}
    """.replace("OPERATION", operation)
    result = run_synthetic_process(body)
    assert result["status"] == "complete", result
    assert result["snapshot_bytes"] == b'{"metrics":{"denied":1}}\n'


@pytest.mark.parametrize("family", [1, 2, 10])
def test_worker_denies_unix_ipv4_and_ipv6_socket_creation(family):
    body = """
        import ctypes
        import errno
        libc = ctypes.CDLL(None, use_errno=True)
        result = libc.socket(FAMILY, 1, 0)
        denied = int(result == -1 and ctypes.get_errno() == errno.EPERM)
        return {'metrics': {'denied': denied}}, {'synthetic': True}
    """.replace("FAMILY", str(family))
    result = run_synthetic_process(body)
    assert result["status"] == "complete", result
    assert result["snapshot_bytes"] == b'{"metrics":{"denied":1}}\n'


def test_filesystem_is_denied_before_selected_module_top_level_executes():
    prelude = """
import errno
try:
    open('/etc/passwd', 'rb')
except OSError as error:
    top_level_denied = int(error.errno == errno.EPERM)
else:
    top_level_denied = 0
"""
    result = run_synthetic_process("return {'metrics': {'denied': top_level_denied}}, {'synthetic': True}",
                                   prelude=prelude)
    assert result["status"] == "complete", result
    assert result["snapshot_bytes"] == b'{"metrics":{"denied":1}}\n'


def test_worker_empty_environment_and_virtual_sources_do_not_read_calibration():
    body = """
        import os
        from pathlib import Path
        path = str(Path(__file__).resolve())
        clean = int('PULSE_TEST_PRIVATE_SENTINEL' not in os.environ and path.startswith('/selected/'))
        return {'metrics': {'clean': clean}}, {'synthetic': True}
    """
    previous = os.environ.get("PULSE_TEST_PRIVATE_SENTINEL")
    os.environ["PULSE_TEST_PRIVATE_SENTINEL"] = "must-not-enter-child"
    try:
        result = run_synthetic_process(body)
    finally:
        if previous is None:
            os.environ.pop("PULSE_TEST_PRIVATE_SENTINEL", None)
        else:
            os.environ["PULSE_TEST_PRIVATE_SENTINEL"] = previous
    assert result["status"] == "complete", result
    assert result["snapshot_bytes"] == b'{"metrics":{"clean":1}}\n'


def test_worker_address_space_limit_is_enforced_by_kernel():
    result = run_synthetic_process("""
        try:
            value = bytearray(300 * 1024 * 1024)
        except MemoryError:
            blocked = 1
        else:
            blocked = 0
        return {'metrics': {'blocked': blocked}}, {'synthetic': True}
    """)
    assert result["status"] == "complete", result
    assert result["snapshot_bytes"] == b'{"metrics":{"blocked":1}}\n'


def test_worker_cpu_limit_terminates_busy_child():
    result = run_synthetic_process("while True:\n    pass")
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_nonzero_exit"
    assert result["exit_code"] < 0
    assert result["input_read_complete"] is False
    assert result["snapshot_bytes"] == b""
    assert result["completed_monotonic_ns"] - result["started_monotonic_ns"] < 5_000_000_000


def test_supervisor_deadline_terminates_child_and_retains_emitted_prefix():
    result = run_synthetic_process("""
        import os
        os.write(2, b'bounded synthetic prefix\\n')
        while True:
            pass
    """, deadline=time.monotonic() + 0.8)
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_wall_timeout"
    assert result["stderr_bytes"] == b"bounded synthetic prefix\n"
    assert result["completed_monotonic_ns"] - result["started_monotonic_ns"] < 2_000_000_000


def test_stderr_overflow_preserves_bound_and_rejects_without_retry():
    streamed = bytearray()
    result = run_synthetic_process("""
        import os
        os.write(2, b'x' * 9000)
        return {}, {'synthetic': True}
    """, sink=lambda channel, raw: streamed.extend(raw) if channel == "stderr" else None)
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_stderr_limit"
    assert result["stderr_bytes"] == b"x" * 4096
    assert bytes(streamed) == result["stderr_bytes"]


def test_stdout_overflow_preserves_bound_and_rejects_without_retry():
    result = run_synthetic_process("""
        import os
        os.write(1, b'x' * 30000)
        return {}, {'synthetic': True}
    """)
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_stdout_limit"
    assert result["stdout_bytes"] == b"x" * 20480


def test_failure_drain_preserves_both_streams_with_one_overflow():
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    result = run_synthetic_process("""
        import os
        os.write(2, b'bounded diagnostic prefix\\n')
        os.write(1, b'x' * 30000)
        return {}, {'synthetic': True}
    """, sink=lambda channel, raw: streams[channel].extend(raw))
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_stdout_limit"
    assert result["stdout_bytes"] == b"x" * 20480
    assert result["stderr_bytes"] == b"bounded diagnostic prefix\n"
    assert bytes(streams["stdout"]) == result["stdout_bytes"]
    assert bytes(streams["stderr"]) == result["stderr_bytes"]


@pytest.mark.parametrize("payload", [b"[]\n", b'{"a":1,"a":2}\n', b'{"x":NaN}\n', b'{"x":1e999}\n'])
def test_real_worker_rejects_invalid_input_before_synthetic_operator(payload):
    result = run_synthetic_process("raise RuntimeError('operator must not run')", input_bytes=payload)
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_nonzero_exit"
    assert b"operator must not run" not in result["stderr_bytes"]
    assert result["snapshot_bytes"] == b""


@pytest.mark.parametrize("body", [
    "return {'metrics': True}, {}",
    "return {'metrics': '1'}, {}",
    "return {'metrics': []}, {}",
    "return {'metrics': None}, {}",
    "return {'metrics': float('nan')}, {}",
    "return {'metrics': float('inf')}, {}",
    "return {}, []",
    "return {}, {'oversized': 'x' * 4096}",
])
def test_real_worker_rejects_invalid_synthetic_outputs(body):
    result = run_synthetic_process(body)
    assert result["status"] == "incomplete"
    assert result["error_code"] == "worker_nonzero_exit"
    assert result["snapshot_bytes"] == b""


@pytest.mark.parametrize("change", [
    {"worker_bytes": b""},
    {"source_bytes": {}},
    {"input_bytes": b""},
    {"input_bytes": b"x" * 4097},
    {"application_id": "idem-01.third"},
    {"application_id": "idem-13.first"},
    {"expected_interpreter_sha256": "0" * 64},
    {"expected_interpreter_sha256": "invalid"},
    {"deadline": 0},
    {"deadline": float("inf")},
    {"configuration": {"max_depth": 2.0, "max_items": 3, "allowed_prefixes": ["metrics"],
                       "deny_keys": ["metrics.pii", "metrics.secret"]}},
])
def test_process_preflight_invalid_arguments_never_start_child(monkeypatch, change):
    process = process_module()
    calls = []

    def forbidden_launch(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("invalid preflight must not launch")

    monkeypatch.setattr(process.subprocess, "Popen", forbidden_launch)
    with pytest.raises(process.ProcessError):
        process.run_worker(**process_arguments(**change))
    assert calls == []


def test_process_unsupported_architecture_never_starts_child(monkeypatch):
    process = process_module()
    monkeypatch.setattr(process.platform, "machine", lambda: "aarch64")
    with pytest.raises(process.ProcessError, match="process_platform_unsupported"):
        process.run_worker(**process_arguments())


def test_deadline_exhausted_during_sealing_cannot_launch_a_late_child(monkeypatch):
    process = process_module()
    clock = {"now": 10.0}
    real_sealed_buffer = process.sealed_buffer
    sealed_roles = []
    launches = []

    def seal_then_expire(role, raw):
        fd = real_sealed_buffer(role, raw)
        sealed_roles.append(role)
        if role == "input":
            clock["now"] = 12.0
        return fd

    def forbidden_launch(*args, **kwargs):
        launches.append((args, kwargs))
        raise AssertionError("sealing exhausted the deadline")

    monkeypatch.setattr(process, "time", SimpleNamespace(monotonic=lambda: clock["now"],
                                                       monotonic_ns=time.monotonic_ns, sleep=time.sleep))
    monkeypatch.setattr(process, "sealed_buffer", seal_then_expire)
    monkeypatch.setattr(process.subprocess, "Popen", forbidden_launch)
    with pytest.raises(process.ProcessError, match="suite_deadline_exhausted"):
        process.run_worker(**process_arguments(deadline=11.0))
    assert "input" in sealed_roles
    assert launches == []


def test_worker_source_and_input_buffers_are_kernel_sealed():
    process = process_module()
    fd = process.sealed_buffer("synthetic-test", b"immutable bytes\n")
    try:
        with pytest.raises(PermissionError):
            os.write(fd, b"substitution")
        with pytest.raises(PermissionError):
            os.ftruncate(fd, 0)
        assert os.read(fd, 100) == b"immutable bytes\n"
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
