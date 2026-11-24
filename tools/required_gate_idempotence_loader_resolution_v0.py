"""Fixed request and fresh admission for one original-loader observation.

Request construction is data-only.  Admission reconstructs the complete pinned
original distribution and selected rebuild-policy chain; an old report is never
an admission input.  Only the separate, explicitly acknowledged producer can
run the fixed capability probes and one original launcher.  Replay never runs
the original launcher or either capability probe.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_exec_stop_v0 as cp0
import check_required_gate_idempotence_entry_stop_v0 as entry
import check_required_gate_idempotence_entry_stop_plan_v0 as entry_plan
import check_required_gate_idempotence_entry_task_guard_v0 as guard
import check_required_gate_idempotence_loader_binary_binding_v0 as static
import check_required_gate_idempotence_loader_readout_contract_v0 as readout
import check_required_gate_idempotence_loader_startup_contract_v0 as startup
import check_required_gate_idempotence_loader_rebuild_acceptance_v0 as acceptance
import check_required_gate_idempotence_loader_two_slot_qualification_v0 as two_slot
import prepare_required_gate_idempotence_exec_stop_v0 as original
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport
import required_gate_idempotence_distribution_signature_v0 as distribution_signature


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_original_launcher_loader_resolution_v0"
REQUEST_TYPE = "required_gate_idempotence_loader_resolution_request_v0"
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY"
ACKNOWLEDGEMENT_SCOPE = (
    "fresh_fixed_guard_and_two_slot_probes_then_one_original_launcher_"
    "through_nine_selected_loader_returns_and_entry_with_owned_cleanup"
)
CONTROL_BYTES = 1048576
LIMITS = {
    "observation_ns": 15000000000, "cleanup_ns": 2000000000,
    "owned_tracees": 1, "max_wait_records": 20,
    "expected_return_events": 9, "max_return_events": 10,
    "max_continuations": 11, "post_terminal_continuations": 0,
    "max_raw_files": 512, "max_raw_bytes": 67108864,
    "max_control_bytes": CONTROL_BYTES, "max_operations": 256,
    "max_proc_bytes": 65536, "max_auxv_bytes": 1024,
    "max_event_files": 32, "max_runtime_ranges": 32,
    "max_runtime_window_bytes": 4096, "max_needed_name_bytes": 256,
    "max_runtime_sample_bytes": 131072,
    "max_event_runtime_sample_bytes": 262144,
    "max_loader_rx_sample_bytes": 160721, "samples_per_range": 2,
    "max_mappings": 128, "max_pointer_indirections": 4,
    "max_stdout_bytes": 4096, "max_stderr_bytes": 4096,
    "max_qualification_control_bytes": CONTROL_BYTES,
    "max_source_carrier_bytes": 67108864,
}
BOUNDARY = {
    "original_acquisition_authorized": False,
    "native_acquisition_performed": False,
    "consumer_resolution_observed": False,
    "loader_resolution_verified": False,
    "complete_native_closure_verified": False,
    "physical_execution_authenticated": False,
    "full_runtime_observed": False,
    "containment_enforced": False,
    "selected_runtime_executed": False,
    "production_gate_eligible": False,
    "b2_complete": False, "metric_pass": None, "authority_effect": "none",
}
ACCEPTANCE_RECORD = {
    "size_bytes": 27407,
    "sha256": "99936de0b0bc2c0e9f0ed52d66cd6a1d7c8d567c55c7cb25c762e04d3f7a6240",
}
STATIC_RECORD = dict(readout.STATIC_RECORD)
STARTUP_CONTRACT = {
    "sha256": "d4cd7d8183aedf83bb92b92a72c714bc4f5cf333a974611364bc67128c3370e1",
}
NEW_SOURCES = (
    "tools/required_gate_idempotence_loader_resolution_v0.py",
    "tools/prepare_required_gate_idempotence_loader_resolution_v0.py",
    "tools/collect_required_gate_idempotence_loader_resolution_v0.py",
    "tools/check_required_gate_idempotence_loader_resolution_v0.py",
    "tools/required_gate_idempotence_loader_resolution_readout_v0.py",
    "schemas/required_gate_idempotence_loader_resolution_v0.schema.json",
)
SOURCE_PATHS = tuple(sorted(set(
    cp0.SOURCE_PATHS + entry.NEW_SOURCES + two_slot.SOURCE_PATHS
    + acceptance.NEW_SOURCES + readout.NEW_SOURCES + startup.NEW_SOURCES
    + NEW_SOURCES + (
        "tools/prepare_required_gate_idempotence_exec_stop_v0.py",
        "tools/required_gate_idempotence_entry_stop_v0.py",
        "tools/required_gate_idempotence_entry_task_guard_v0.py",
        "tools/check_required_gate_idempotence_entry_task_guard_v0.py",
        "tools/required_gate_idempotence_loader_startup_readout_v0.py",
        "tools/required_gate_idempotence_exec_stop_hosted_io_v0.py",
        "tools/required_gate_idempotence_launcher_distribution_v0.py",
        "tools/check_required_gate_idempotence_launcher_distribution_v0.py",
        "tools/required_gate_idempotence_distribution_signature_v0.py",
        "tools/required_gate_idempotence_process_v0.py",
        "tools/required_gate_idempotence_elf_v0.py",
        "tools/check_required_gate_idempotence_loader_resolution_plan_v0.py",
        "tools/check_required_gate_idempotence_loader_binary_binding_v0.py",
        "tools/required_gate_idempotence_loader_binary_v0.py",
        "tools/required_gate_idempotence_loader_source_v0.py",
        "tools/check_required_gate_idempotence_loader_build_record_binding_v0.py",
        "tools/required_gate_idempotence_loader_build_envelope_v0.py",
        "tools/required_gate_idempotence_loader_buildinfo_v0.py",
        "tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py",
        "tools/required_gate_idempotence_loader_rebuild_attestation_v0.py",
        "tools/check_anchor_integrity_record_signatures_v0_1.py",
    )
)))
_ACCEPTANCE_INPUT_NAMES = (
    "evidence_archive_bytes", "prior_record_bytes", "build_record_bytes",
    "startup_contract_bytes", "prior_contract_bytes", "static_record_bytes",
    "historical_entry_archive_bytes", "artifact_members", "build_carriers",
    "attestations", "public_keys_bytes",
)
ADMISSION_INPUT_NAMES = frozenset(_ACCEPTANCE_INPUT_NAMES + (
    "originals_archive_bytes", "record_bytes", "policy_bytes",
))


class ResolutionError(ValueError):
    """Stable error code without inspected data, paths or environment values."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise ResolutionError(code)


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ResolutionError("loader_resolution_json_value") from exc


def sha(raw):
    _need(type(raw) is bytes, "loader_resolution_bytes_required")
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"size_bytes": len(raw), "sha256": sha(raw)}


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "loader_resolution_duplicate_json_key")
        value[key] = item
    return value


def _number(_value):
    raise ResolutionError("loader_resolution_noninteger_json_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_resolution_control_size")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_number, parse_constant=_number)
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _need(depth <= 32 and count <= 65536, "loader_resolution_json_complexity")
            if type(item) is dict:
                pending.extend((v, depth + 1) for v in item.values())
            elif type(item) is list:
                pending.extend((v, depth + 1) for v in item)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ResolutionError("loader_resolution_json") from exc


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, code)


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(sha(raw) == expected["sha256"], code)


def _read(path, limit=CONTROL_BYTES):
    return transport.read_regular(ROOT / path, limit)


def source_bindings():
    """Pin the closed implementation roster; no caller path enters this read."""
    return {path: binding(_read(path)) for path in SOURCE_PATHS}


def _fixed_records():
    plan_raw = _read(entry.PLAN_REL)
    _bound(plan_raw, entry.PLAN, "loader_resolution_entry_plan_binding")
    static_raw = _read(static.RECORD_REL)
    _bound(static_raw, STATIC_RECORD, "loader_resolution_static_record_binding")
    acceptance_raw = _read(acceptance.RECORD_REL)
    _bound(acceptance_raw, ACCEPTANCE_RECORD, "loader_resolution_acceptance_record_binding")
    policy_raw = _read(acceptance.POLICY_REL)
    _bound(policy_raw, acceptance.POLICY_BINDING, "loader_resolution_policy_binding")
    startup_raw = _read(startup.CONTRACT_REL)
    _need(sha(startup_raw) == STARTUP_CONTRACT["sha256"],
          "loader_resolution_startup_contract_binding")
    return parse(plan_raw), parse(static_raw)


def make_request(*, attempt_id, observer_descriptor):
    """Construct a source-bound request, without claiming admission or execution."""
    _need(type(attempt_id) is str and re.fullmatch(r"[0-9a-f]{32}", attempt_id) is not None,
          "loader_resolution_attempt_id")
    _need(attempt_id not in {entry_plan.HISTORICAL_CONTEXT["attempt_id"],
                           static.prior.HISTORICAL_CONTEXT["attempt_id"]},
          "loader_resolution_historical_attempt_reused")
    cp0._observer(observer_descriptor)
    plan, record = _fixed_records()
    return {
        "record_type": REQUEST_TYPE, "profile": PROFILE,
        "attempt_id": attempt_id, "observer": copy.deepcopy(observer_descriptor),
        "cp0_request": cp0._request(attempt_id, copy.deepcopy(observer_descriptor)),
        "native_objects": copy.deepcopy(plan["native_objects"]),
        "recipe": copy.deepcopy(record["recipe"]),
        "occurrence_obligations": copy.deepcopy(record["occurrence_bindings"]),
        "execution": {"argv": ["bubblewrap"],
                      "environment": {"LC_ALL": "C", "TZ": "UTC"}, "cwd": "/"},
        "acknowledgement": {"token": ACKNOWLEDGEMENT, "scope": ACKNOWLEDGEMENT_SCOPE},
        "guard": {"program": guard.program_binding(), "fresh_qualification_required": True},
        "two_slot": {"fresh_qualification_required": True, "same_observer_required": True},
        "source_build": {"record": dict(ACCEPTANCE_RECORD),
                         "policy": dict(acceptance.POLICY_BINDING),
                         "external_selection_required": True},
        "originals": {"archive": dict(entry_plan.ORIGINALS),
                      "manifest_sha256": original.ORIGINAL_MANIFEST_SHA256},
        "limits": dict(LIMITS), "sources": source_bindings(),
        "boundary": dict(BOUNDARY),
    }


def validate_request(request_bytes, expected_request_sha256):
    _digest(expected_request_sha256, "loader_resolution_external_request_digest")
    request = parse(request_bytes)
    _need(sha(request_bytes) == expected_request_sha256,
          "loader_resolution_request_digest_mismatch")
    _need(type(request) is dict and {"attempt_id", "observer"} <= set(request),
          "loader_resolution_request_fields")
    wanted = make_request(attempt_id=request["attempt_id"], observer_descriptor=request["observer"])
    _same(request, wanted, "loader_resolution_request_contract")
    _need(canonical(request) == request_bytes, "loader_resolution_request_canonical")
    return request


def _admit_originals(archive_bytes):
    """Replay the original 111-file chain and its selected historical signature epoch."""
    _bound(archive_bytes, entry_plan.ORIGINALS, "loader_resolution_originals_archive_binding")
    members = entry_plan._archive(archive_bytes, entry_plan.ORIGINALS, 114, 72234203)
    manifest_raw = members["CASE_INPUTS.json"]
    _need(sha(manifest_raw) == original.ORIGINAL_MANIFEST_SHA256,
          "loader_resolution_original_manifest_binding")
    manifest = parse(manifest_raw)
    _need(manifest["record_type"] == "launcher_distribution_original_byte_example_v0"
          and manifest["record_status"] == "example"
          and type(manifest["files"]) is dict and len(manifest["files"]) == 111,
          "loader_resolution_original_manifest_profile")
    wanted_names = set(manifest["files"]) | {
        "CASE_INPUTS.json", "results/checker-1.json", "results/checker-2.json"}
    _need(set(members) == wanted_names, "loader_resolution_original_member_roster")
    originals = {}
    for name, descriptor in sorted(manifest["files"].items()):
        _bound(members[name], descriptor, "loader_resolution_original_member_binding")
        originals[name] = members[name]
    saved = members["results/checker-1.json"]
    _bound(saved, original.ORIGINAL_REPORT, "loader_resolution_original_report_binding")
    _need(saved == members["results/checker-2.json"], "loader_resolution_original_reports_differ")
    originals["distribution-verification.json"] = saved
    original._check_old_sources(manifest, originals)
    evidence = []

    def preserve(payload):
        _need(type(payload) is dict and set(payload) == {
            "stdout_bytes", "stderr_bytes", "process_record"} and not evidence,
            "loader_resolution_signature_evidence_roster")
        for key in ("stdout_bytes", "stderr_bytes"):
            _need(type(payload[key]) is bytes and len(payload[key]) <= CONTROL_BYTES,
                  "loader_resolution_signature_evidence_size")
        _need(type(payload["process_record"]) is dict,
              "loader_resolution_signature_process_record")
        item = {"stdout_hex": payload["stdout_bytes"].hex(),
                "stderr_hex": payload["stderr_bytes"].hex(),
                "process_record": copy.deepcopy(payload["process_record"])}
        _need(len(canonical(item)) <= CONTROL_BYTES,
              "loader_resolution_signature_evidence_size")
        evidence.append(item)

    inputs = original._original_inputs(manifest, originals, preserve)
    record_raw = originals["launcher-distribution-record.json"]
    report = original.distribution.verify_record(
        record_bytes=record_raw, expected_record_sha256=sha(record_raw), **inputs)
    _need(len(evidence) == 1, "loader_resolution_fresh_signature_evidence_missing")
    _need(original.distribution.canonical(report) == saved,
          "loader_resolution_original_report_reconstruction")
    distribution_record = original.distribution.parse(record_raw)
    _same(distribution_record["bindings"]["launch_host_verification"],
          binding(originals["launch-host-verification.json"]),
          "loader_resolution_original_host_binding")
    _same(distribution_record["bindings"]["packages_decoded"],
          binding(originals["distribution-origin/Packages"]),
          "loader_resolution_original_packages_binding")
    original._check_old_sources(manifest, originals)
    native = {path: originals[path] for path in cp0.NATIVE}
    for path, raw in native.items():
        _bound(raw, cp0.NATIVE[path], "loader_resolution_original_native_binding")
    summary = {
        "original_archive": dict(entry_plan.ORIGINALS),
        "manifest_sha256": original.ORIGINAL_MANIFEST_SHA256,
        "original_input_count": 111, "historical_source_count": 43,
        "distribution_signature_freshly_verified": True,
        "signature_evaluation_epoch": manifest["explicit_signature_policy"]["evaluation_time_epoch"],
        "original_reports_reconstructed": True,
        "report": binding(saved), "signature_evidence": evidence,
    }
    return originals, native, summary


def reconstruct_admission(*, request_bytes, expected_request_sha256,
                          admission_inputs=None, accepted_policy_sha256):
    """Fresh raw-input admission; the policy digest is a caller trust-root input.

    ``admission_inputs`` accepts only the named bounded raw carriers accepted by
    the unchanged prior verifiers.  It has no report, readiness or approval input.
    None uses the exact pinned repository carriers.  This function executes only
    the existing signature verification backends, never a target or probe.
    """
    _digest(accepted_policy_sha256, "loader_resolution_external_policy_required")
    _need(accepted_policy_sha256 == acceptance.POLICY_BINDING["sha256"],
          "loader_resolution_selected_policy_mismatch")
    request = validate_request(request_bytes, expected_request_sha256)
    sources_before = dict(request["sources"])
    supplied = {} if admission_inputs is None else admission_inputs
    _need(type(supplied) is dict and set(supplied) <= ADMISSION_INPUT_NAMES,
          "loader_resolution_admission_input_roster")
    for name, item in supplied.items():
        if name in {"artifact_members", "build_carriers", "attestations"}:
            _need(type(item) is dict, "loader_resolution_admission_carrier_type")
        else:
            _need(type(item) is bytes, "loader_resolution_admission_bytes_required")
    acceptance_raw = supplied.get("record_bytes")
    if acceptance_raw is None:
        acceptance_raw = _read(acceptance.RECORD_REL)
    policy_raw = supplied.get("policy_bytes")
    if policy_raw is None:
        policy_raw = _read(acceptance.POLICY_REL)
    _bound(acceptance_raw, ACCEPTANCE_RECORD, "loader_resolution_acceptance_record_binding")
    _bound(policy_raw, acceptance.POLICY_BINDING, "loader_resolution_policy_binding")
    archive = supplied.get("originals_archive_bytes")
    if archive is None:
        archive = _read(entry_plan.ORIGINALS_REL, entry_plan.ORIGINALS["size_bytes"])
    originals, native, original_summary = _admit_originals(archive)
    cp0_derived = original.derive_request(originals, attempt_id=request["attempt_id"],
                                          observer_descriptor=request["observer"])
    _same(cp0_derived, request["cp0_request"], "loader_resolution_fresh_cp0_request_mismatch")
    objects, _relationships = entry_plan.derive_native_obligations(archive)
    _same(objects, request["native_objects"], "loader_resolution_native_obligations_mismatch")
    rebuild = acceptance.verify_acceptance(
        record_bytes=acceptance_raw, expected_record_sha256=ACCEPTANCE_RECORD["sha256"],
        policy_bytes=policy_raw, accepted_policy_sha256=accepted_policy_sha256,
        **{name: supplied[name] for name in _ACCEPTANCE_INPUT_NAMES if name in supplied})
    _need(rebuild.get("source_build_gate_satisfied_under_policy") is True
          and rebuild.get("policy_selection") == "externally_selected_exact_policy",
          "loader_resolution_source_build_policy_not_admitted")
    record_raw = supplied.get("static_record_bytes")
    if record_raw is None:
        record_raw = _read(static.RECORD_REL)
    _bound(record_raw, STATIC_RECORD, "loader_resolution_static_record_binding")
    record = static.parse(record_raw)
    _same(request["recipe"], record["recipe"], "loader_resolution_recipe_mismatch")
    _same(request["occurrence_obligations"], record["occurrence_bindings"],
          "loader_resolution_occurrences_mismatch")
    _same(source_bindings(), sources_before, "loader_resolution_admission_sources_changed")
    return {"request": request, "native_files": native, "static_record": record,
            "source_build_report": rebuild, "original_admission": original_summary}


def _admission_json(raw):
    """The unchanged GPG process record has one fixed 20.0-second JSON value.

    This exception belongs only to preserved verifier diagnostics. Request,
    capture, timing, identity and other control numbers remain integer-only.
    Exact subsequent field comparisons confine this spelling to its old limit.
    """
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_resolution_admission_summary_size")

    def wall_seconds(value):
        _need(value == "20.0", "loader_resolution_admission_summary_number")
        return 20.0

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=wall_seconds, parse_constant=_number)
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _need(depth <= 32 and count <= 65536, "loader_resolution_admission_summary_complexity")
            if type(item) is dict:
                pending.extend((child, depth + 1) for child in item.values())
            elif type(item) is list:
                pending.extend((child, depth + 1) for child in item)
        _need(canonical(value) == raw, "loader_resolution_admission_summary_canonical")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ResolutionError("loader_resolution_admission_summary_json") from exc


def _signature_evidence(value, fresh):
    _need(type(value) is list and len(value) == len(fresh) == 1,
          "loader_resolution_preserved_signature_count")
    saved, current = value[0], fresh[0]
    _need(type(saved) is dict and set(saved) == {
        "stdout_hex", "stderr_hex", "process_record"},
        "loader_resolution_preserved_signature_fields")
    raw = {}
    for label, limit in (("stdout", distribution_signature.STDOUT_LIMIT),
                         ("stderr", distribution_signature.STDERR_LIMIT)):
        text = saved[label + "_hex"]
        _need(type(text) is str and len(text) % 2 == 0 and len(text) <= 2 * limit
              and re.fullmatch(r"[0-9a-f]*", text) is not None,
              "loader_resolution_preserved_signature_hex")
        raw[label] = bytes.fromhex(text)
    record, current_record = saved["process_record"], current["process_record"]
    _need(type(record) is dict and set(record) == set(current_record),
          "loader_resolution_preserved_signature_record_fields")
    varying = {"pid", "started_monotonic_ns", "completed_monotonic_ns", "argv", "stdout", "stderr"}
    _same({key: item for key, item in record.items() if key not in varying},
          {key: item for key, item in current_record.items() if key not in varying},
          "loader_resolution_preserved_signature_stable_fields")
    _need(type(record["pid"]) is int and 1 < record["pid"] < 1 << 31,
          "loader_resolution_preserved_signature_pid")
    start, end = record["started_monotonic_ns"], record["completed_monotonic_ns"]
    _need(type(start) is int and type(end) is int and 0 < start <= end < 1 << 63
          and end - start <= int(distribution_signature.WALL_SECONDS + 2) * 10**9,
          "loader_resolution_preserved_signature_timing")
    for label in raw:
        _same(record[label], binding(raw[label]), "loader_resolution_preserved_signature_stream_binding")
    argv, current_argv = record["argv"], current_record["argv"]
    _need(type(argv) is list and len(argv) == len(current_argv),
          "loader_resolution_preserved_signature_command")
    fds = []
    for token, wanted in zip(argv, current_argv):
        _need(type(token) is str, "loader_resolution_preserved_signature_command")
        if re.fullmatch(r"/proc/self/fd/[0-9]+", wanted):
            _need(re.fullmatch(r"/proc/self/fd/[0-9]+", token) is not None,
                  "loader_resolution_preserved_signature_descriptor")
            number = int(token.rsplit("/", 1)[1])
            _need(3 <= number < 1 << 20 and token.endswith("/" + str(number)),
                  "loader_resolution_preserved_signature_descriptor")
            fds.append(number)
        else:
            _need(token == wanted, "loader_resolution_preserved_signature_command")
    _need(len(fds) == 3 and len(set(fds)) == 3,
          "loader_resolution_preserved_signature_descriptor_alias")
    saved_facts = distribution_signature._parse_status(
        raw["stdout"], current_record["required_signers"], current_record["evaluation_time"])
    current_facts = distribution_signature._parse_status(
        bytes.fromhex(current["stdout_hex"]), current_record["required_signers"],
        current_record["evaluation_time"])
    _same(saved_facts, current_facts, "loader_resolution_preserved_signature_status")


def validate_preserved_admission(*, source_build_bytes, original_admission_bytes, admitted):
    """Check saved diagnostics against an already freshly reconstructed input chain.

    The public capture verifier must call ``reconstruct_admission`` itself first.
    This helper never supplies admission and never authenticates an earlier
    verifier process. Only bounded process-local diagnostics vary across replay
    hosts; every input, policy, signature fact and stable scope claim must match.
    """
    source_build = parse(source_build_bytes)
    _need(canonical(source_build) == source_build_bytes,
          "loader_resolution_preserved_source_build_canonical")
    current = admitted["source_build_report"]
    _need(type(source_build) is dict and set(source_build) == set(current),
          "loader_resolution_preserved_source_build_fields")
    varying = {"backend_observation", "prior_report"}
    _same({key: value for key, value in source_build.items() if key not in varying},
          {key: value for key, value in current.items() if key not in varying},
          "loader_resolution_preserved_source_build_facts")
    observed = source_build["backend_observation"]
    _need(type(observed) is dict and set(observed) == {
        "path", "binary_sha256", "version", "suite", "known_answer_self_test"},
        "loader_resolution_preserved_backend_fields")
    _need(observed["path"] == "/usr/bin/openssl" and observed["suite"] == "ed25519"
          and observed["known_answer_self_test"] == "passed"
          and type(observed["version"]) is str and len(observed["version"]) <= 256
          and re.match(r"^OpenSSL 3\.[0-9]+\.", observed["version"]) is not None
          and all(32 <= ord(character) <= 126 for character in observed["version"]),
          "loader_resolution_preserved_backend_profile")
    _digest(observed["binary_sha256"], "loader_resolution_preserved_backend_digest")
    prior = source_build["prior_report"]
    _need(type(prior) is dict and set(prior) == {"size_bytes", "sha256"}
          and type(prior["size_bytes"]) is int and 0 < prior["size_bytes"] <= CONTROL_BYTES,
          "loader_resolution_preserved_prior_report_binding")
    _digest(prior["sha256"], "loader_resolution_preserved_prior_report_digest")
    # The stable prior-report digest remains part of the exact comparison above.
    # A prior report containing the old runtime backend is diagnostic custody.
    saved_original = _admission_json(original_admission_bytes)
    fresh_original = admitted["original_admission"]
    _need(type(saved_original) is dict and set(saved_original) == set(fresh_original),
          "loader_resolution_preserved_original_fields")
    _same({key: value for key, value in saved_original.items() if key != "signature_evidence"},
          {key: value for key, value in fresh_original.items() if key != "signature_evidence"},
          "loader_resolution_preserved_original_facts")
    _signature_evidence(saved_original["signature_evidence"], fresh_original["signature_evidence"])
    return {"preserved_admission_summaries_consistent": True,
            "fresh_original_and_rebuild_inputs_reconstructed": True,
            "preserved_backend_execution_authenticated": False}
