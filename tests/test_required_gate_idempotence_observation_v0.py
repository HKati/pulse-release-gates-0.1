#!/usr/bin/env python3
"""Adversarial replay tests for the explicitly synthetic idempotence profile.

These tests manufacture evidence records; they never invoke the selected
sanitizer, a worker, a model, or a workflow. Re-pinning a controlled negative
fixture reaches deeper validation checks and is not trust discovery.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_REL = "tools/check_required_gate_idempotence_observation_v0.py"
TOOL = ROOT / TOOL_REL
PROPOSAL_ROOT = ROOT / "docs/compute/required_gate_idempotence_protocol_v0"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def archive(members: dict[str, bytes], *, compression=zipfile.ZIP_DEFLATED) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as zipped:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            info.compress_type = compression
            zipped.writestr(info, raw)
    return output.getvalue()


def checker():
    name = "required_gate_idempotence_observation_under_test"
    if name not in sys.modules:
        tools_path = str(ROOT / "tools")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        spec = importlib.util.spec_from_file_location(name, TOOL)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def boundary(report):
    assert report["execution_authorized"] is False
    assert report["metric_pass"] is None
    assert report["production_gate_eligible"] is False
    assert report["authority_effect"] == "none"
    assert report["anchor_authentication"] == "not_established"
    assert "gate_results" not in report
    assert "release_decision" not in report


def run_cli(tmp_path: Path, selection: bytes, carrier: bytes, *extra,
            selection_sha256=None, carrier_sha256=None, timeout=20):
    selection_path = tmp_path / "selection.json"
    carrier_path = tmp_path / "acquisition.zip"
    selection_path.write_bytes(selection)
    carrier_path.write_bytes(carrier)
    return subprocess.run([
        sys.executable, str(TOOL),
        "--selection", str(selection_path),
        "--selection-sha256", selection_sha256 or digest(selection),
        "--carrier", str(carrier_path),
        "--carrier-sha256", carrier_sha256 or digest(carrier),
        *map(str, extra),
    ], capture_output=True, timeout=timeout)


def reference(member, raw, state_id=None):
    result = {"member": member, "sha256": digest(raw), "size_bytes": len(raw)}
    if state_id is not None:
        result["state_id"] = state_id
    return result


def consumed(state):
    return {**copy.deepcopy(state), "read_sha256": state["sha256"],
            "read_size_bytes": state["size_bytes"], "read_complete": True}


def invocation(selection, application_id, input_state):
    """Independently encode the documented invocation contract for fixtures."""
    args = {"application_id": application_id,
            "configuration_sha256": digest(encoded(selection["configuration"])),
            "input_state_id": input_state["state_id"],
            "input_sha256": input_state["sha256"],
            "input_size_bytes": input_state["size_bytes"]}
    args_sha = digest(encoded(args))
    worker = next(item for item in selection["sources"] if item["role"] == "worker")
    command = {"worker_path": worker["path"], "worker_revision": worker["source_revision"],
               "worker_sha256": worker["sha256"],
               "executable_sha256": selection["environment"]["executable_sha256"],
               "arguments_sha256": args_sha}
    return args_sha, digest(encoded(command))


class Example:
    """Authored synthetic receipts: every snapshot is {}, never a calculation.

    Equal bytes across all cases deliberately prevent digest uniqueness from
    concealing a wrong producer, state, occurrence, or case assignment.
    """
    def __init__(self):
        self.members = {
            "selection/" + name: (PROPOSAL_ROOT / name).read_bytes()
            for name in ("protocol_proposal_v0.json", "inputs_v0.json", "observation_mapping_v0.json")
        }
        proposal = json.loads(self.members["selection/protocol_proposal_v0.json"])
        catalog = json.loads(self.members["selection/inputs_v0.json"])
        revision = "a" * 40  # Explicit example identity; not claimed as a Git commit.
        sources = []
        for item in proposal["source_inventory"][:4]:
            raw = (ROOT / item["path"]).read_bytes()
            assert digest(raw) == item["sha256"] and len(raw) == item["size_bytes"]
            member = "sources/" + item["path"]
            self.members[member] = raw
            sources.append({"role": "operator" if item["role"] == "selected_operator_module" else "operator_dependency",
                            "path": item["path"], "source_revision": item["source_commit"],
                            **reference(member, raw)})
        for role in ("worker", "collector"):
            path = "tools/example_" + role + ".py"
            raw = ('raise RuntimeError("SYNTHETIC_' + role.upper() + '_MUST_NOT_EXECUTE")\n').encode()
            member = "sources/" + path
            self.members[member] = raw
            sources.append({"role": role, "path": path, "source_revision": revision,
                            **reference(member, raw)})
        self.selection = {
            "record_type": "required_gate_idempotence_selection_v0",
            "record_status": "example", "profile": "standalone_operator_v0",
            "protocol_id": "epf_snapshot_idempotence_v0",
            "repository": "HKati/pulse-release-gates-0.1", "source_commit": revision,
            "acquisition_id": "example-idempotence-001", "acquisition_attempt": 1,
            "configuration": {"max_depth": 2, "max_items": 3, "allowed_prefixes": ["metrics"],
                              "deny_keys": ["metrics.pii", "metrics.secret"]},
            "environment": {"python_implementation": "CPython", "python_version": "3.11.16",
                            "unicode_version": "14.0.0", "os_name": "Linux", "architecture": "x86_64",
                            "executable_sha256": digest(b"authored synthetic interpreter identity\n")},
            "sources": sources,
            "applications": [{"case_id": item["case_id"],
                              "first_application_id": item["case_id"] + ".first",
                              "second_application_id": item["case_id"] + ".second"}
                             for item in catalog["cases"]],
            "execution_authorized": False, "production_gate_eligible": False, "authority_effect": "none",
        }
        self.context = {
            "record_type": "standalone_operator_capture_context_v0", "record_status": "example",
            "selection_sha256": "", "acquisition_id": self.selection["acquisition_id"],
            "acquisition_attempt": 1, "repository": self.selection["repository"],
            "source_commit": revision, "environment": copy.deepcopy(self.selection["environment"]),
            "started_utc": "2026-11-14T00:00:00Z", "completed_utc": "2026-11-14T00:00:30Z",
            "started_monotonic_ns": 1_000_000_000, "completed_monotonic_ns": 31_000_000_000,
            "collector": {"execution_id": "execution:example-collector", "process_id": 900,
                          "source_path": "tools/example_collector.py", "source_revision": revision,
                          "command_sha256": digest(b"synthetic collector command\n"),
                          "arguments_sha256": digest(b"synthetic collector arguments\n"), "exit_code": 0},
        }
        self.receipts = {"record_type": "standalone_operator_application_receipts_v0",
                         "record_status": "example", "selection_sha256": "", "applications": []}
        for index, case in enumerate(catalog["cases"], 1):
            case_id = case["case_id"]
            original = case["input_utf8"].encode("utf-8")
            initial_member = "inputs/" + case_id + ".json"
            self.members[initial_member] = original
            previous = reference(initial_member, original, "state:example-input-%02d" % index)
            for phase_index, phase in enumerate(("first", "second")):
                application_id = case_id + "." + phase
                prefix = "state:example-%02d-%s-" % (index, phase)
                row = {
                    "application_id": application_id, "case_id": case_id, "phase": phase,
                    "execution_id": "execution:example-%02d-%s" % (index, phase),
                    "process_id": 1000 + index * 2 + phase_index,
                    "source_path": "tools/example_worker.py", "source_revision": revision,
                    "configuration_sha256": digest(encoded(self.selection["configuration"])),
                    "environment_sha256": digest(encoded(self.selection["environment"])),
                    "started_utc": "2026-11-14T00:00:0%dZ" % (1 + 2 * phase_index),
                    "completed_utc": "2026-11-14T00:00:0%dZ" % (2 + 2 * phase_index),
                    "started_monotonic_ns": (2 + 2 * phase_index) * 1_000_000_000,
                    "completed_monotonic_ns": (3 + 2 * phase_index) * 1_000_000_000,
                    "exit_code": 0, "capture_status": "complete", "input": consumed(previous),
                }
                for role, member, raw in (
                    ("snapshot", "snapshots/" + application_id + ".json", b"{}\n"),
                    ("metadata", "metadata/" + application_id + ".json", encoded({"synthetic": True, "phase": phase})),
                    ("stderr", "diagnostics/" + application_id + ".stderr", b""),
                ):
                    self.members[member] = raw
                    row[role] = reference(member, raw, prefix + role)
                self.wire(row)
                self.receipts["applications"].append(row)
                previous = row["snapshot"]
        self.reselect()

    @property
    def selection_bytes(self):
        return encoded(self.selection)

    def reselect(self):
        """Controlled test-only re-selection; all selected bytes remain explicit."""
        pin = digest(self.selection_bytes)
        self.context["selection_sha256"] = pin
        self.receipts["selection_sha256"] = pin

    def row(self, case=1, phase="first"):
        application_id = "idem-%02d.%s" % (case, phase)
        return next(row for row in self.receipts["applications"] if row["application_id"] == application_id)

    def wire(self, row):
        row["arguments_sha256"], row["command_sha256"] = invocation(self.selection, row["application_id"], row["input"])

    def set_input(self, row, state):
        row["input"] = consumed(state)
        self.wire(row)

    def rewrite_output(self, row, role, raw, *, follow_input=False):
        old = row[role]
        self.members[old["member"]] = raw
        old.update(sha256=digest(raw), size_bytes=len(raw))
        if follow_input:
            for candidate in self.receipts["applications"]:
                if candidate["input"]["state_id"] == old["state_id"]:
                    self.set_input(candidate, old)

    def packed(self, *, raw_context=None, raw_receipts=None, inventory=None):
        members = dict(self.members)
        members["selection/pre_acquisition_selection.json"] = self.selection_bytes
        members["capture/context.json"] = encoded(self.context) if raw_context is None else raw_context
        members["capture/application_receipts.json"] = encoded(self.receipts) if raw_receipts is None else raw_receipts
        members["capture/member_inventory.json"] = encoded({
            "record_type": "standalone_operator_member_inventory_v0",
            "members": [reference(name, raw) for name, raw in sorted(members.items())],
        }) if inventory is None else inventory
        return archive(members)

    def check(self, *, selection=None, carrier=None, selection_pin=None, carrier_pin=None, repository_root=None):
        selection = self.selection_bytes if selection is None else selection
        carrier = self.packed() if carrier is None else carrier
        return checker().verify_observation(
            selection_bytes=selection, expected_selection_sha256=digest(selection) if selection_pin is None else selection_pin,
            carrier_bytes=carrier, expected_carrier_sha256=digest(carrier) if carrier_pin is None else carrier_pin,
            repository_root=repository_root,
        )

    def reject(self, **kwargs):
        with pytest.raises(checker().VerificationError) as caught:
            self.check(**kwargs)
        assert isinstance(caught.value.code, str) and caught.value.code
        return caught.value.code


def test_example_binding_reconstructs_all_cases_without_metric_or_execution_authority():
    case = Example()
    report = case.check()
    assert report["status"] == "accepted" and report["ok"] is True
    assert report["record_status"] == "example" and report["binding_complete"] is True
    assert report["packet_semantics_verified"] is True
    assert report["property_semantics_verified"] is False
    assert report["execution_ready"] is False and report["runtime_closure_verified"] is False
    assert len(report["case_results"]) == 12
    assert report["subject_packet"] and report["runtime_packet"] and report["planned_observed_relation"]
    boundary(report)


def test_fixture_has_fixed_inputs_24_distinct_applications_and_97_members():
    case = Example()
    assert len(case.receipts["applications"]) == 24
    assert len({row["execution_id"] for row in case.receipts["applications"]}) == 24
    with zipfile.ZipFile(io.BytesIO(case.packed())) as zipped:
        assert len(zipped.namelist()) == 97
    assert case.row(1)["input"]["sha256"] == case.row(1)["snapshot"]["sha256"]
    assert case.row(1)["input"]["state_id"] != case.row(1)["snapshot"]["state_id"]
    assert len({row["snapshot"]["sha256"] for row in case.receipts["applications"]}) == 1


def test_example_verification_cannot_execute_selected_source_or_process(monkeypatch):
    case = Example()
    def forbidden(*args, **kwargs):
        raise AssertionError("offline example verification attempted process execution")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    boundary(case.check())


def test_equal_payloads_keep_distinct_state_and_producer_identities():
    case = Example()
    first, second = case.row(1), case.row(1, "second")
    assert first["input"]["sha256"] == first["snapshot"]["sha256"] == second["snapshot"]["sha256"]
    assert len({first["input"]["state_id"], first["snapshot"]["state_id"], second["snapshot"]["state_id"]}) == 3
    assert second["input"]["state_id"] == first["snapshot"]["state_id"]
    assert case.check()["binding_complete"] is True


def test_changed_metadata_does_not_change_composition_binding():
    case = Example()
    case.rewrite_output(case.row(1), "metadata", b'{"first_pass_dropped": 7}\n')
    case.rewrite_output(case.row(1, "second"), "metadata", b'{"second_pass_dropped": 0}\n')
    assert case.check()["binding_complete"] is True


def test_unequal_second_snapshot_is_valid_binding_without_property_verdict():
    case = Example()
    case.rewrite_output(case.row(1, "second"), "snapshot", encoded({"metrics": {"a": 1.0}}))
    report = case.check()
    assert report["binding_complete"] is True
    assert report["property_semantics_verified"] is False
    boundary(report)


@pytest.mark.parametrize("phase", ["first", "second"])
@pytest.mark.parametrize("value", ["numeric-looking-1.25", [1.25], None, True, False])
def test_snapshot_domain_rejects_nonnumeric_leaves_in_both_phases(phase, value):
    case = Example()
    case.rewrite_output(case.row(1, phase), "snapshot", encoded({"metrics": {"value": value}}),
                        follow_input=phase == "first")
    case.reject()


def test_snapshot_domain_accepts_finite_numbers_empty_objects_and_signed_zero():
    case = Example()
    first = {"metrics": {"integer": 7, "float": 1.25, "negative_zero": -0.0,
                         "nested": {"negative": -3, "empty": {}}}, "empty": {}}
    second = copy.deepcopy(first)
    second["metrics"]["negative_zero"] = 0.0
    assert encoded(first) != encoded(second)
    case.rewrite_output(case.row(1), "snapshot", encoded(first), follow_input=True)
    case.rewrite_output(case.row(1, "second"), "snapshot", encoded(second))
    report = case.check()
    assert report["binding_complete"] is True and report["property_semantics_verified"] is False
    boundary(report)


def test_empty_selected_implementation_dependency_is_valid_source_evidence():
    case = Example()
    path = "tools/example_package/__init__.py"
    member = "sources/" + path
    case.members[member] = b""
    case.selection["sources"].append({
        "role": "implementation_dependency", "path": path,
        "source_revision": case.selection["source_commit"], **reference(member, b""),
    })
    case.reselect()
    report = case.check()
    assert report["binding_complete"] is True
    assert report["subject_packet"]["carrier"]["member_count"] == 98
    boundary(report)


def test_array_order_does_not_decide_acceptance():
    case = Example()
    case.selection["sources"].reverse()
    case.selection["applications"].reverse()
    case.receipts["applications"].reverse()
    case.reselect()
    assert case.check()["binding_complete"] is True


@pytest.mark.parametrize("field,value", [("max_depth", 2.0), ("max_items", 3.0)])
def test_fixed_configuration_preserves_selected_numeric_types(field, value):
    case = Example()
    case.selection["configuration"][field] = value
    for row in case.receipts["applications"]:
        row["configuration_sha256"] = digest(encoded(case.selection["configuration"]))
        case.wire(row)
    case.reselect()
    assert case.reject() == "configuration_mismatch"


@pytest.mark.parametrize("case_number", [1, 2, 12])
def test_second_original_input_is_rejected_even_when_its_bytes_equal_intermediate(case_number):
    case = Example()
    case.set_input(case.row(case_number, "second"), case.row(case_number)["input"])
    case.reject()


@pytest.mark.parametrize("case_number", range(1, 13))
def test_cross_case_intermediate_substitution_cannot_hide_behind_equal_digests(case_number):
    case = Example()
    other = case_number % 12 + 1
    case.set_input(case.row(case_number, "second"), case.row(other)["snapshot"])
    case.reject()


def test_copied_intermediate_with_new_state_id_is_rejected():
    case = Example()
    second = case.row(1, "second")
    second["input"]["state_id"] = "state:copied-intermediate-with-same-bytes"
    case.wire(second)
    case.reject()


def test_metadata_cannot_substitute_for_actual_first_snapshot():
    case = Example()
    case.rewrite_output(case.row(1), "metadata", b"{}\n")
    case.set_input(case.row(1, "second"), case.row(1)["metadata"])
    case.reject()


def test_decorative_original_input_cannot_satisfy_second_payload_consumption():
    case = Example()
    second = case.row(2, "second")
    case.set_input(second, case.row(2)["input"])
    second["input_state_ids"] = [second["input"]["state_id"], case.row(2)["snapshot"]["state_id"]]
    case.reject()


@pytest.mark.parametrize("field,value", [
    ("read_complete", False), ("read_sha256", "f" * 64), ("read_size_bytes", 4),
    ("sha256", "f" * 64), ("size_bytes", 4), ("size_bytes", True),
])
def test_each_second_input_requires_exact_observed_read(field, value):
    case = Example()
    row = case.row(1, "second")
    row["input"][field] = value
    case.wire(row)
    case.reject()


@pytest.mark.parametrize("field,value", [
    ("execution_id", "execution:example-01-first"),
    ("process_id", 1002), ("source_path", "tools/example_collector.py"),
    ("source_revision", "b" * 40), ("configuration_sha256", "f" * 64),
    ("environment_sha256", "f" * 64), ("arguments_sha256", "f" * 64),
    ("command_sha256", "f" * 64), ("capture_status", "partial"),
    ("exit_code", 1), ("exit_code", False), ("case_id", "idem-02"),
    ("phase", "first"), ("application_id", "idem-01.first"),
])
def test_occurrence_identity_source_invocation_and_completion_are_required(field, value):
    case = Example()
    case.row(1, "second")[field] = value
    case.reject()


@pytest.mark.parametrize("field", ["execution_id", "process_id"])
def test_collector_cannot_replace_subject_application(field):
    case = Example()
    case.row(1)[field] = case.context["collector"][field]
    case.reject()


@pytest.mark.parametrize("role", ["snapshot", "metadata", "stderr"])
def test_state_identity_cannot_be_reused_for_different_application(role):
    case = Example()
    case.row(2)[role]["state_id"] = case.row(1)[role]["state_id"]
    case.reject()


@pytest.mark.parametrize("mutation", ["missing_first", "missing_second", "duplicate", "extra", "swapped"])
def test_complete_application_roster_cannot_be_shrunk_duplicated_or_swapped(mutation):
    case = Example()
    rows = case.receipts["applications"]
    if mutation == "missing_first":
        rows.pop(0)
    elif mutation == "missing_second":
        rows.pop(1)
    elif mutation == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif mutation == "extra":
        rows.append(copy.deepcopy(rows[0]))
    else:
        rows[0]["application_id"], rows[1]["application_id"] = rows[1]["application_id"], rows[0]["application_id"]
        case.wire(rows[0])
        case.wire(rows[1])
    case.reject()


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "wrong_phase_id", "new_case"])
def test_preselected_protocol_roster_cannot_be_redefined(mutation):
    case = Example()
    apps = case.selection["applications"]
    if mutation == "missing":
        apps.pop()
    elif mutation == "duplicate":
        apps[1] = copy.deepcopy(apps[0])
    elif mutation == "wrong_phase_id":
        apps[0]["second_application_id"] = "idem-01.other"
    else:
        apps[0]["case_id"] = "idem-99"
    case.reselect()
    case.reject()


@pytest.mark.parametrize("key,value", [
    ("selection_sha256", "f" * 64), ("acquisition_id", "other-acquisition"),
    ("acquisition_attempt", 2), ("source_commit", "b" * 40),
    ("repository", "different/repository"), ("record_status", "observed"),
])
def test_capture_context_must_match_independent_selection(key, value):
    case = Example()
    case.context[key] = value
    case.reject()


@pytest.mark.parametrize("which", ["first_before_suite", "second_before_first_completed", "worker_wall_limit", "suite_wall_limit", "utc_reversed", "utc_pair_order"])
def test_causal_order_and_recorded_time_bounds(which):
    case = Example()
    first, second = case.row(1), case.row(1, "second")
    if which == "first_before_suite":
        first["started_monotonic_ns"] = 0
    elif which == "second_before_first_completed":
        second["started_monotonic_ns"] = 2_500_000_000
    elif which == "worker_wall_limit":
        second["completed_monotonic_ns"] = 10_000_000_000
        second["completed_utc"] = "2026-11-14T00:00:09Z"
    elif which == "suite_wall_limit":
        case.context["completed_monotonic_ns"] = 182_000_000_000
        case.context["completed_utc"] = "2026-11-14T00:03:01Z"
    elif which == "utc_reversed":
        first["completed_utc"] = "2026-11-13T23:59:59Z"
    else:
        second["started_utc"] = "2026-11-14T00:00:01Z"
    case.reject()


@pytest.mark.parametrize("role", ["worker", "collector", "operator", "operator_dependency"])
def test_selected_source_bytes_are_checked_without_execution(role):
    case = Example()
    source = next(item for item in case.selection["sources"] if item["role"] == role)
    case.members[source["member"]] += b"# tampered inert bytes\n"
    case.reject()


def test_operator_hash_cannot_be_changed_with_consistent_selection_repinning():
    case = Example()
    source = next(item for item in case.selection["sources"] if item["role"] == "operator")
    case.members[source["member"]] += b"# replaced operator\n"
    raw = case.members[source["member"]]
    source.update(sha256=digest(raw), size_bytes=len(raw))
    case.reselect()
    case.reject()


@pytest.mark.parametrize("mutation", ["no_worker", "no_collector", "duplicate_path", "duplicate_role", "wrong_revision"])
def test_source_role_selection_is_closed(mutation):
    case = Example()
    sources = case.selection["sources"]
    worker = next(item for item in sources if item["role"] == "worker")
    collector = next(item for item in sources if item["role"] == "collector")
    if mutation == "no_worker":
        sources.remove(worker)
    elif mutation == "no_collector":
        sources.remove(collector)
    elif mutation == "duplicate_path":
        collector["path"] = worker["path"]
    elif mutation == "duplicate_role":
        collector["role"] = "worker"
    else:
        worker["source_revision"] = "b" * 40
    case.reselect()
    case.reject()


def test_example_cannot_be_promoted_to_observed_without_committed_source_verification():
    case = Example()
    for item in (case.selection, case.context, case.receipts):
        item["record_status"] = "observed"
    case.reselect()
    case.reject()


@pytest.mark.parametrize("target", ["selection", "context", "receipt"])
@pytest.mark.parametrize("field,value", [("source_verified", True), ("workflow_run_id", 123), ("release_candidate_id", "invented"), ("authority_effect", "allow")])
def test_self_asserted_source_or_release_authority_fields_are_rejected(target, field, value):
    case = Example()
    document = {"selection": case.selection, "context": case.context, "receipt": case.row(1)}[target]
    document[field] = value
    if target == "selection":
        case.reselect()
    case.reject()


@pytest.mark.parametrize("name", ["protocol_proposal_v0.json", "inputs_v0.json", "observation_mapping_v0.json"])
def test_original_protocol_companions_remain_exact_selected_bytes(name):
    case = Example()
    case.members["selection/" + name] += b"\n"
    case.reject()


def test_initial_input_cannot_be_substituted_even_with_updated_receipt_digest():
    case = Example()
    row = case.row(2)
    raw = b"{}\n"
    case.members[row["input"]["member"]] = raw
    changed = reference(row["input"]["member"], raw, row["input"]["state_id"])
    case.set_input(row, changed)
    case.reject()


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'{"a":1e999}\n', b'[]\n', b'{ "a": 1 }\n', b'{"a":"\\ud800"}\n', b'{}', b'\xff'])
def test_snapshot_must_be_strict_canonical_finite_object_json(raw):
    case = Example()
    case.rewrite_output(case.row(1), "snapshot", raw, follow_input=True)
    case.reject()


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":Infinity}', b'{"a":1e999}', b'[]', b'\xff'])
def test_metadata_is_strict_json_despite_being_excluded_from_metric(raw):
    case = Example()
    case.rewrite_output(case.row(1), "metadata", raw)
    case.reject()


@pytest.mark.parametrize("role", ["snapshot", "metadata", "stderr"])
def test_each_output_is_bounded(role):
    case = Example()
    raw = encoded({"padding": "x" * 4096}) if role != "stderr" else b"x" * 4097
    case.rewrite_output(case.row(1), role, raw, follow_input=role == "snapshot")
    case.reject()


@pytest.mark.parametrize("target", ["selection", "context", "receipts"])
def test_duplicate_json_keys_are_rejected_before_record_normalization(target):
    case = Example()
    document = {"selection": case.selection, "context": case.context, "receipts": case.receipts}[target]
    raw = encoded(document)
    raw = b'{"record_status":"example",' + raw[1:]
    if target == "selection":
        code = case.reject(selection=raw)
    else:
        code = case.reject(carrier=case.packed(**{"raw_" + target: raw}))
    assert "duplicate" in code, code


@pytest.mark.parametrize("kind", ["selection", "carrier"])
def test_external_selection_digests_are_mandatory_and_exact(kind):
    case = Example()
    code = case.reject(**{kind + "_pin": "0" * 64})
    assert "hash" in code or "digest" in code, code


@pytest.mark.parametrize("name", ["extra.txt", "../outside.txt", "/absolute.txt", "inputs//alias.json", "inputs/./alias.json", "inputs\\alias.json"])
def test_extra_or_unsafe_archive_members_fail_closed(name):
    case = Example()
    case.members[name] = b"unexpected\n"
    case.reject()


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_legitimate_closed_stored_and_deflated_carriers_remain_accepted(compression):
    case = Example()
    with zipfile.ZipFile(io.BytesIO(case.packed())) as zipped:
        members = {entry.filename: zipped.read(entry) for entry in zipped.infolist()}
    carrier = archive(members, compression=compression)
    assert case.check(carrier=carrier)["binding_complete"] is True


@pytest.mark.parametrize("kind", ["prefix", "trailer", "concatenated_archive"])
def test_carrier_physical_extent_excludes_unselected_prefixes_trailers_and_archives(kind):
    case = Example()
    raw = case.packed()
    altered = {"prefix": b"PREFIX" + raw, "trailer": raw + b"TRAILER",
               "concatenated_archive": raw + raw}[kind]
    # These altered carriers remain readable through Python's ordinary ZIP
    # interface. Their physical bytes extend beyond the admitted member set.
    with zipfile.ZipFile(io.BytesIO(altered)) as zipped:
        assert len(zipped.namelist()) == 97 and zipped.testzip() is None
    assert case.reject(carrier=altered) == "carrier_layout_invalid"


def test_unindexed_local_entry_cannot_hide_before_the_central_directory():
    case = Example()
    raw = case.packed()
    central_start = struct.unpack_from("<L", raw, len(raw) - 6)[0]
    hidden_archive = archive({"unindexed-private.bin": b"unselected payload\n"})
    hidden_central_start = struct.unpack_from("<L", hidden_archive, len(hidden_archive) - 6)[0]
    hidden_local_entry = hidden_archive[:hidden_central_start]
    altered = bytearray(raw[:central_start] + hidden_local_entry + raw[central_start:])
    struct.pack_into("<L", altered, len(altered) - 6, central_start + len(hidden_local_entry))
    with zipfile.ZipFile(io.BytesIO(raw)) as original, zipfile.ZipFile(io.BytesIO(altered)) as zipped:
        assert zipped.namelist() == original.namelist()
        assert all(zipped.read(name) == original.read(name) for name in original.namelist())
    assert case.reject(carrier=bytes(altered)) == "carrier_layout_invalid"


def test_deflate_stream_cannot_hide_trailing_bytes_inside_a_declared_member():
    case = Example()
    raw = case.packed()
    central_start = struct.unpack_from("<L", raw, len(raw) - 6)[0]
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        entries = zipped.infolist()
        last = entries[-1]
        assert last.compress_type == zipfile.ZIP_DEFLATED
        assert last.header_offset == max(entry.header_offset for entry in entries)
        last_directory_header = central_start + sum(
            46 + len(entry.filename.encode("ascii")) + len(entry.extra) + len(entry.comment)
            for entry in entries[:-1])
        original_bytes = zipped.read(last)
    junk = b"UNSELECTED_AFTER_DEFLATE_END"
    altered = bytearray(raw[:central_start] + junk + raw[central_start:])
    struct.pack_into("<L", altered, last.header_offset + 18, last.compress_size + len(junk))
    struct.pack_into("<L", altered, last_directory_header + len(junk) + 20,
                     last.compress_size + len(junk))
    struct.pack_into("<L", altered, len(altered) - 6, central_start + len(junk))
    with zipfile.ZipFile(io.BytesIO(altered)) as zipped:
        assert zipped.read(last.filename) == original_bytes and zipped.testzip() is None
    assert case.reject(carrier=bytes(altered)) == "carrier_deflate_extent_invalid"


def test_missing_payload_member_is_rejected():
    case = Example()
    del case.members[case.row(12, "second")["snapshot"]["member"]]
    case.reject()


def test_duplicate_archive_member_cannot_replace_selected_payload():
    case = Example()
    out = io.BytesIO(case.packed())
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr("inputs/idem-01.json", b"{}\n")
    case.reject(carrier=out.getvalue())


@pytest.mark.parametrize("mode", [stat.S_IFLNK | 0o777, stat.S_IFDIR | 0o700])
def test_non_regular_archive_members_are_rejected(mode):
    case = Example()
    raw = case.packed()
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as original, zipfile.ZipFile(out, "w") as changed:
        for item in original.infolist():
            data = original.read(item)
            if item.filename == "inputs/idem-01.json":
                item.create_system = 3
                item.external_attr = mode << 16
            changed.writestr(item, data)
    case.reject(carrier=out.getvalue())


def test_inventory_must_hash_members_and_exclude_itself():
    case = Example()
    with zipfile.ZipFile(io.BytesIO(case.packed())) as zipped:
        inventory = json.loads(zipped.read("capture/member_inventory.json"))
    inventory["members"].append(reference("capture/member_inventory.json", b"invented self hash"))
    case.reject(carrier=case.packed(inventory=encoded(inventory)))


def test_inventory_digest_mismatch_is_rejected_after_carrier_reselection():
    case = Example()
    with zipfile.ZipFile(io.BytesIO(case.packed())) as zipped:
        inventory = json.loads(zipped.read("capture/member_inventory.json"))
    inventory["members"][0]["sha256"] = "f" * 64
    case.reject(carrier=case.packed(inventory=encoded(inventory)))


def test_one_compressed_member_cannot_exceed_the_uncompressed_member_limit():
    case = Example()
    source = next(row for row in case.selection["sources"] if row["role"] == "worker")
    raw = b"#" * (512 * 1024 + 1)
    case.members[source["member"]] = raw
    source.update(sha256=digest(raw), size_bytes=len(raw))
    for row in case.receipts["applications"]:
        case.wire(row)
    case.reselect()
    code = case.reject()
    assert "limit" in code or "size" in code, code


def test_aggregate_uncompressed_member_limit_applies_to_selected_source_closure():
    case = Example()
    for number in range(5):
        path = "tools/example_dependency_%d.py" % number
        member = "sources/" + path
        raw = b"#" * (450 * 1024)
        case.members[member] = raw
        case.selection["sources"].append({
            "role": "implementation_dependency", "path": path,
            "source_revision": case.selection["source_commit"], **reference(member, raw),
        })
    case.reselect()
    code = case.reject()
    assert "limit" in code or "size" in code, code


def test_two_cli_replays_are_accepted_and_byte_identical(tmp_path):
    case = Example()
    first = run_cli(tmp_path, case.selection_bytes, case.packed())
    second = run_cli(tmp_path, case.selection_bytes, case.packed())
    assert first.returncode == second.returncode == 0, (first.stderr, second.stderr)
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["status"] == "accepted" and report["binding_complete"] is True
    boundary(report)


def test_invalid_cli_replay_is_deterministic_and_does_not_echo_payload(tmp_path):
    case = Example()
    case.row(1)["private_extra"] = "PRIVATE_IDEMPOTENCE_SENTINEL_MUST_NOT_ECHO"
    first = run_cli(tmp_path, case.selection_bytes, case.packed())
    second = run_cli(tmp_path, case.selection_bytes, case.packed())
    assert first.returncode == second.returncode == 1
    assert first.stdout == second.stdout
    assert b"PRIVATE_IDEMPOTENCE_SENTINEL" not in first.stdout + first.stderr
    report = json.loads(first.stdout)
    assert report["ok"] is False and report["status"] == "rejected"
    assert report["binding_complete"] is False and report["packet_semantics_verified"] is False
    boundary(report)


def test_cli_creates_canonical_report_without_overwriting_existing_output(tmp_path):
    case = Example()
    output = tmp_path / "verification.json"
    first = run_cli(tmp_path, case.selection_bytes, case.packed(), "--output", output)
    assert first.returncode == 0, first.stderr
    stored = output.read_bytes()
    assert json.loads(stored)["ok"] is True
    second = run_cli(tmp_path, case.selection_bytes, case.packed(), "--output", output)
    assert second.returncode != 0
    assert output.read_bytes() == stored


@pytest.mark.parametrize("filename", ["status.json", "release_decision_v0.json", "release_authority_v0.json"])
def test_cli_refuses_authority_output_names(tmp_path, filename):
    case = Example()
    output = tmp_path / filename
    result = run_cli(tmp_path, case.selection_bytes, case.packed(), "--output", output)
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.skipif(os.name != "posix", reason="descriptor-safe CLI is POSIX-only")
@pytest.mark.parametrize("which", ["selection", "carrier", "parent", "output"])
def test_cli_refuses_symlink_inputs_parents_and_output(tmp_path, which):
    case = Example()
    selection = tmp_path / "selected.json"
    carrier = tmp_path / "selected.zip"
    selection.write_bytes(case.selection_bytes)
    carrier.write_bytes(case.packed())
    output = tmp_path / "report.json"
    if which == "selection":
        link = tmp_path / "linked-selection.json"
        link.symlink_to(selection)
        selection = link
    elif which == "carrier":
        link = tmp_path / "linked-carrier.zip"
        link.symlink_to(carrier)
        carrier = link
    elif which == "parent":
        actual = tmp_path / "actual"
        actual.mkdir()
        linked = tmp_path / "linked"
        linked.symlink_to(actual, target_is_directory=True)
        (actual / "selected.json").write_bytes(case.selection_bytes)
        selection = linked / "selected.json"
    else:
        existing = tmp_path / "untouched.txt"
        existing.write_bytes(b"untouched\n")
        output.symlink_to(existing)
    result = subprocess.run([sys.executable, str(TOOL), "--selection", str(selection),
        "--selection-sha256", digest(case.selection_bytes), "--carrier", str(carrier),
        "--carrier-sha256", digest(case.packed()), "--output", str(output)], capture_output=True, timeout=20)
    assert result.returncode != 0
    if which == "output":
        assert existing.read_bytes() == b"untouched\n"
    elif output.exists():
        # A safe diagnostic output may record the failed intake; it must never
        # promote the missing selected bytes into an accepted observation.
        rejected = json.loads(output.read_bytes())
        assert rejected["ok"] is False and rejected["binding_complete"] is False
        boundary(rejected)


def test_cli_requires_both_external_digest_arguments(tmp_path):
    case = Example()
    selection, carrier = tmp_path / "selection.json", tmp_path / "acquisition.zip"
    selection.write_bytes(case.selection_bytes)
    carrier.write_bytes(case.packed())
    result = subprocess.run([sys.executable, str(TOOL), "--selection", str(selection),
                             "--carrier", str(carrier)], capture_output=True, timeout=20)
    assert result.returncode == 2


def test_observation_regression_is_registered_once_without_targeted_duplication():
    name = "tests/test_required_gate_idempotence_observation_v0.py"
    def entries(path):
        return [line.split("#", 1)[0].strip() for line in path.read_text().splitlines()
                if line.split("#", 1)[0].strip()]
    assert entries(ROOT / "ci/tools-tests.list").count(name) == 1
    assert name not in entries(ROOT / "ci/pytest-tests.list")


def shared_index_inputs():
    case = Example()
    packet = case.check()["runtime_packet"]
    sources = [{"path": row["path"], "source_revision": row["source_revision"],
                "sha256": row["sha256"], "size_bytes": row["size_bytes"],
                "data": case.members[row["member"]]} for row in case.selection["sources"]]
    return case, packet, sources


def assess_first_pair(index, case):
    first, second = case.row(1), case.row(1, "second")
    return checker().core.assess_runtime_output_consumption(
        index, producer_execution_id=first["execution_id"],
        required_output_state_ids=[first["snapshot"]["state_id"]],
        required_consumer_execution_ids={first["snapshot"]["state_id"]: [second["execution_id"]]},
    )


def test_serialized_index_cannot_recreate_immutable_source_admission():
    case, packet, sources = shared_index_inputs()
    index = checker().standalone.validate_and_index(encoded(packet), expected_subject=packet["subject"], selected_sources=sources)
    assert assess_first_pair(index, case)["status"] == "observed"
    copied = json.loads(encoded(index))
    copied["source_verified"] = True
    assert assess_first_pair(copied, case)["status"] == "unresolved"
    assert checker().core.runtime_consumption_map(copied)[case.row(1)["snapshot"]["state_id"]] == []


@pytest.mark.parametrize("mutation", ["data", "size", "digest", "mutable_bytes", "duplicate_path"])
def test_shared_source_admission_requires_exact_immutable_selected_bytes(mutation):
    _case, packet, sources = shared_index_inputs()
    if mutation == "data":
        sources[0]["data"] += b"changed\n"
    elif mutation == "size":
        sources[0]["size_bytes"] += 1
    elif mutation == "digest":
        sources[0]["sha256"] = "f" * 64
    elif mutation == "mutable_bytes":
        sources[0]["data"] = bytearray(sources[0]["data"])
    else:
        sources.append(copy.deepcopy(sources[0]))
    with pytest.raises(checker().standalone.StandaloneError):
        checker().standalone.validate_and_index(encoded(packet), expected_subject=packet["subject"], selected_sources=sources)


def test_shared_index_rejects_mutable_runtime_packet_bytes():
    _case, packet, sources = shared_index_inputs()
    with pytest.raises(checker().standalone.StandaloneError):
        checker().standalone.validate_and_index(bytearray(encoded(packet)), expected_subject=packet["subject"], selected_sources=sources)


def test_standalone_sources_cannot_be_applied_to_legacy_subject_context():
    _case, packet, sources = shared_index_inputs()
    legacy = json.loads((ROOT / "tests/fixtures/required_gate_suite_contract_v0/runtime_packet.json").read_bytes())["subject"]
    with pytest.raises(checker().standalone.StandaloneError):
        checker().standalone.validate_and_index(encoded(packet), expected_subject=legacy, selected_sources=sources)


@pytest.mark.parametrize("field,value", [("source_revision", "b" * 40), ("action_repository", "invented/action")])
def test_shared_consumption_rechecks_full_source_identity_on_each_occurrence(field, value):
    case, packet, sources = shared_index_inputs()
    index = checker().standalone.validate_and_index(encoded(packet), expected_subject=packet["subject"], selected_sources=sources)
    row = index["records"]["executions"][case.row(1, "second")["execution_id"]]["record"]
    row["source_identity"][field] = value
    assert assess_first_pair(index, case)["status"] == "unresolved"


def test_legacy_observed_repository_source_downgrade_is_unchanged():
    _case, packet, _sources = shared_index_inputs()
    identity = packet["executions"][0]["source_identity"]
    assert identity["source_kind"] == "repository_file" and identity["identity_status"] == "exact"
    effective = checker().core.runtime_effective_source_identity(identity, record_status="observed")
    assert effective["identity_status"] == "partial"
    assert identity["identity_status"] == "exact"


def test_missing_git_object_cannot_launch_promisor_helper_or_retry(tmp_path, monkeypatch):
    """Selected Git reads must stay offline even in a hostile local config.

    The empty repository needs no commit. Before transport denial this missing
    object read launched the ext helper during Git's implicit lazy fetch.
    """
    repository = tmp_path / "source-repository"
    subprocess.run(["/usr/bin/git", "init", "-q", str(repository)],
                   check=True, capture_output=True, timeout=10)
    marker = tmp_path / "remote-helper-invoked"
    # git-remote-ext uses percent escapes for literal percent and space. This
    # keeps the deliberately hostile fixture confined to the test directory.
    marker_argument = str(marker).replace("%", "%%").replace(" ", "% ")
    (repository / ".git/config").write_text(
        "[core]\n repositoryformatversion = 1\n bare = false\n"
        "[extensions]\n partialClone = origin\n"
        '[remote "origin"]\n url = ext::/usr/bin/touch ' + marker_argument + "\n"
        " promisor = true\n partialclonefilter = blob:none\n"
        '[protocol "ext"]\n allow = always\n', encoding="utf-8")
    calls = []
    original_run = subprocess.run
    def recorded_run(arguments, *args, **kwargs):
        calls.append(list(arguments))
        return original_run(arguments, *args, **kwargs)
    monkeypatch.setattr(checker().subprocess, "run", recorded_run)
    with pytest.raises(checker().VerificationError) as caught:
        checker()._git_blob(repository, "a" * 40, "tools/example_worker.py", 1)
    assert caught.value.code == "source_git_unavailable"
    assert not marker.exists()
    assert len(calls) == 1
    assert calls[0][-3:] == ["cat-file", "-t", "a" * 40]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
