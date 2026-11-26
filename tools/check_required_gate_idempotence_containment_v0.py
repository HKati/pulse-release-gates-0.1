#!/usr/bin/env python3
"""Check selected containment records without authenticating their execution.

All accepted results remain diagnostic. A reconstructed request and byte-bound
receipt can establish record consistency, never a trusted host, enforced kernel
boundary, bootstrap qualification or permission to acquire an actual reference.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_bootstrap_v0 as bootstrap
import required_gate_idempotence_bootstrap_probe_v0 as probe

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_containment_v0.schema.json"
SCHEMA_SHA256 = "c22eddba2c3dbef425557aa2f6df4c27e499caac44e8710984494927ce5c7bd2"
PROFILE = "linux_x86_64_bubblewrap_bootstrap_v0"
CONTROL_LIMIT = 4 * 1024 * 1024
STDOUT_LIMIT = 65536
STDERR_LIMIT = 4096
SELECTION_BOUNDARY = {
    "execution_ready": False, "execution_authorized": False,
    "runtime_closure_verified": False, "restored_bootstrap_qualified": False,
    "containment_enforced": False, "production_gate_eligible": False,
    "authority_effect": "none",
}
BOUNDARY = {**probe.BOUNDARY, "containment_enforced": False,
            "bootstrap_execution_observed": False}


class CheckerError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise CheckerError(code)


def sha(raw):
    return bootstrap.sha(raw)


def canonical(value):
    return bootstrap.canonical_bytes(value)


def parse(raw, *, limit=CONTROL_LIMIT):
    need(type(raw) is bytes and 0 < len(raw) <= limit, "containment_record_size_invalid")
    try:
        value = bootstrap.parse(raw)
    except bootstrap.BootstrapError as exc:
        raise CheckerError(exc.code) from exc
    need(type(value) is dict, "containment_record_object_required")
    return value


def binding(raw):
    need(type(raw) is bytes, "containment_stream_type_invalid")
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def _same(actual, expected):
    return canonical(actual) == canonical(expected)


def _boundary(value, expected):
    for key, required in expected.items():
        need(key in value and type(value[key]) is type(required) and value[key] == required,
             "containment_authority_boundary_mismatch")


def validate_selection(selection_bytes, expected_selection_sha256,
                       expected_bootstrap_plan_sha256=None, record_status=None):
    """Validate a closed selection; this function never grants launch authority."""
    need(type(selection_bytes) is bytes and sha(selection_bytes) == expected_selection_sha256,
         "containment_selection_digest_mismatch")
    value = parse(selection_bytes)
    try:
        schema_bytes = bootstrap.runtime.observation.safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(schema_bytes) == SCHEMA_SHA256, "containment_schema_source_mismatch")
        bootstrap.runtime.observation.safe._validate_schema(
            value, parse(schema_bytes), "containment_selection_schema_invalid", "selection")
    except bootstrap.runtime.observation.safe.ContractError as exc:
        raise CheckerError(exc.code) from exc
    _boundary(value, SELECTION_BOUNDARY)
    need(probe._hash_ok(value["bootstrap_plan_sha256"]), "containment_selection_binding_invalid")
    for name in ("launcher", "entry_shim", "entry_source", "policy_source"):
        row = value[name]
        need(probe._hash_ok(row["sha256"]) and type(row["size_bytes"]) is int,
             "containment_selection_binding_invalid")
    need(probe._path_ok(value["launcher"]["path"]), "containment_launcher_path_invalid")
    if expected_bootstrap_plan_sha256 is not None:
        need(value["bootstrap_plan_sha256"] == expected_bootstrap_plan_sha256,
             "containment_bootstrap_plan_mismatch")
    if record_status is not None:
        need(value["record_status"] == record_status, "containment_record_status_mismatch")
    return value


def expected_startup():
    """The fixed probe's declared startup profile, not a host attestation."""
    return {
        "python_implementation": "CPython", "python_version": "3.11.16",
        "architecture": "x86_64", "os_name": "Linux",
        "prefix": probe.PREFIX, "exec_prefix": probe.PREFIX,
        "base_prefix": probe.PREFIX, "base_exec_prefix": probe.PREFIX,
        "executable": probe.INTERPRETER_PATH, "working_directory": "/empty",
        "initial_sys_path": list(probe.INITIAL_SYS_PATH),
        "environment": dict(probe.EXPECTED_ENVIRONMENT),
        "flags": {"isolated": 1, "ignore_environment": 1, "no_site": 1,
                  "no_user_site": 1, "dont_write_bytecode": 1, "safe_path": True},
        "unicode_version": "14.0.0", "probe_sys_path": list(probe.SEARCH_ROOTS),
    }


def check_probe_report(raw, contract, phase):
    """Check the finite report against the independently reconstructed contract.

    A caller must supply the contract from original admitted bootstrap inputs.
    Matching this record does not prove those observations physically occurred.
    """
    try:
        by_name = probe._validate_contract(contract, phase)
    except probe.ProbeError as exc:
        raise CheckerError(exc.code) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckerError("containment_probe_contract_invalid") from exc
    report = parse(raw, limit=STDOUT_LIMIT)
    need(canonical(report) == raw, "containment_probe_report_noncanonical")
    required = {"record_type", "profile", "status", "phase", *probe.HASH_FIELDS,
                "startup", "module_observations", "resource_observations", "finite_checks",
                "post_phase_sys_path", *probe.BOUNDARY}
    need(set(report) == required, "containment_probe_report_shape")
    need(report["record_type"] == "required_gate_idempotence_bootstrap_diagnostic_v0"
         and report["profile"] == "restored_bootstrap_plan_v0"
         and report["status"] == "completed" and report["phase"] == phase,
         "containment_probe_report_identity")
    _boundary(report, probe.BOUNDARY)
    need(all(report[key] == contract[key] for key in probe.HASH_FIELDS),
         "containment_probe_subject_mismatch")
    need(_same(report["startup"], expected_startup()), "containment_probe_startup_mismatch")
    targets = set(contract["phases"][phase]) | {"hashlib", "json", "unicodedata"}
    targets.update(".".join(name.split(".")[:index])
                   for name in tuple(targets) for index in range(1, len(name.split("."))))
    rows = report["module_observations"]
    need(type(rows) is list and len(rows) == len(targets), "containment_probe_module_roster")
    for name, row in zip(sorted(targets), rows):
        provider = by_name[name]
        expected_origin = (provider["path"] if provider["path"] is not None
                           else "built-in" if provider["kind"] == "builtin" else "frozen")
        need(type(row) is dict and set(row) == set(provider) | {"observed_origin", "present_before_phase"},
             "containment_probe_module_shape")
        need(_same({key: row[key] for key in provider}, provider)
             and row["observed_origin"] == expected_origin
             and type(row["present_before_phase"]) is bool,
             "containment_probe_module_binding")
    need(_same(report["resource_observations"], contract["resources"]),
         "containment_probe_resource_binding")
    expected_checks = {"canonical_json": True, "sha256": True, "unicode": True}
    if phase == "collector":
        expected_checks["draft202012_validator"] = True
    need(_same(report["finite_checks"], expected_checks), "containment_probe_finite_checks")
    paths = report["post_phase_sys_path"]
    need(type(paths) is list and all(type(path) is str and path in probe.SEARCH_ROOTS for path in paths)
         and set(paths) == set(probe.SEARCH_ROOTS), "containment_probe_post_phase_paths")
    return report


def _request(request_bytes, expected_request_sha256, probe_contract_bytes):
    need(type(request_bytes) is bytes and sha(request_bytes) == expected_request_sha256,
         "containment_request_digest_mismatch")
    request = parse(request_bytes)
    need(canonical(request) == request_bytes, "containment_request_noncanonical")
    need(set(request) == {"record_type", "profile", "record_status", "phase", "bindings",
                          "files", "empty_directories", "launch_policy", *BOUNDARY},
         "containment_request_shape")
    need(request["record_type"] == "required_gate_idempotence_containment_request_v0"
         and request["profile"] == PROFILE and request["record_status"] in ("example", "selected")
         and request["phase"] in ("worker", "collector"), "containment_request_identity")
    _boundary(request, BOUNDARY)
    descriptors = request["bindings"]
    need(type(descriptors) is dict and set(descriptors) == {
        "bootstrap_plan", "containment_selection", "launcher", "entry_shim", "entry_source",
        "policy_source", "seccomp"}, "containment_request_bindings")
    for row in descriptors.values():
        need(type(row) is dict and set(row) == {"sha256", "size_bytes"}
             and probe._hash_ok(row["sha256"]) and type(row["size_bytes"]) is int
             and 0 < row["size_bytes"] <= bootstrap.VIEW_LIMIT, "containment_request_binding_invalid")
    files = request["files"]
    need(type(files) is list and 0 < len(files) <= bootstrap.MAX_VIEW_FILES + 1
         and all(type(row) is dict and type(row.get("path")) is str for row in files),
         "containment_request_files_invalid")
    rows = [row for row in files if row["path"] == bootstrap.CONTRACT_VIRTUAL]
    need(len(rows) == 1 and set(binding(probe_contract_bytes)) <= set(rows[0])
         and _same(binding(probe_contract_bytes), {key: rows[0][key] for key in ("sha256", "size_bytes")}),
         "containment_probe_contract_binding")
    contract = parse(probe_contract_bytes)
    need(canonical(contract) == probe_contract_bytes, "containment_probe_contract_noncanonical")
    try:
        probe._validate_contract(contract, request["phase"])
    except probe.ProbeError as exc:
        raise CheckerError(exc.code) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckerError("containment_probe_contract_invalid") from exc
    return request, contract


def verify_receipt(*, request_bytes, expected_request_sha256, receipt_bytes,
                   expected_receipt_sha256, stdout_bytes, stderr_bytes, probe_contract_bytes):
    """Check bounded attempt records against an already reconstructed request.

    This low-level function intentionally does not reconstruct a request from
    source inputs. Call the coordinator's verify_attempt wrapper to re-admit all
    original selections and selected bytes before invoking it. An expected hash
    of a caller-authored request is not a substitute for that reconstruction.

    Accepted incomplete records preserve failed attempts. Accepted completed
    records establish only finite report consistency, with every qualification
    and execution-authority flag still false.
    """
    need(type(stdout_bytes) is bytes and len(stdout_bytes) <= STDOUT_LIMIT,
         "containment_stdout_limit")
    need(type(stderr_bytes) is bytes and len(stderr_bytes) <= STDERR_LIMIT,
         "containment_stderr_limit")
    request, contract = _request(request_bytes, expected_request_sha256, probe_contract_bytes)
    need(type(receipt_bytes) is bytes and sha(receipt_bytes) == expected_receipt_sha256,
         "containment_receipt_digest_mismatch")
    receipt = parse(receipt_bytes)
    need(canonical(receipt) == receipt_bytes, "containment_receipt_noncanonical")
    need(set(receipt) == {"record_type", "profile", "status", "request_sha256", "phase", "streams",
                          "process", "error_code", *BOUNDARY}, "containment_receipt_shape")
    need(receipt["record_type"] == "required_gate_idempotence_containment_receipt_v0"
         and receipt["profile"] == PROFILE and receipt["status"] in ("completed", "incomplete")
         and receipt["request_sha256"] == expected_request_sha256
         and receipt["phase"] == request["phase"], "containment_receipt_identity")
    _boundary(receipt, BOUNDARY)
    streams = {"stdout": binding(stdout_bytes), "stderr": binding(stderr_bytes)}
    need(_same(receipt["streams"], streams), "containment_receipt_stream_mismatch")
    process = receipt["process"]
    need(type(process) is dict and set(process) == {
        "pid", "exit_code", "started_monotonic_ns", "completed_monotonic_ns"},
        "containment_process_shape")
    need((process["pid"] is None or type(process["pid"]) is int and process["pid"] > 0)
         and (process["exit_code"] is None or type(process["exit_code"]) is int)
         and type(process["started_monotonic_ns"]) is int
         and type(process["completed_monotonic_ns"]) is int
         and 0 < process["started_monotonic_ns"] <= process["completed_monotonic_ns"],
         "containment_process_descriptor_invalid")
    need(process["pid"] is not None or process["exit_code"] is None,
         "containment_process_exit_without_pid")
    complete = receipt["status"] == "completed"
    if complete:
        need(request["record_status"] == "example", "containment_selected_execution_closed")
        need(process["pid"] is not None and process["exit_code"] == 0
             and stderr_bytes == b"" and receipt["error_code"] is None,
             "containment_completed_attempt_invalid")
        need(process["completed_monotonic_ns"] - process["started_monotonic_ns"]
             <= bootstrap.LIMITS["wall_seconds"] * 1_000_000_000,
             "containment_completed_wall_limit")
        check_probe_report(stdout_bytes, contract, request["phase"])
    else:
        code = receipt["error_code"]
        need(type(code) is str and 0 < len(code) <= 128
             and all(char in "abcdefghijklmnopqrstuvwxyz_0123456789" for char in code),
             "containment_incomplete_error_required")
        if request["record_status"] == "selected":
            need(process["pid"] is None and process["exit_code"] is None,
                 "containment_selected_execution_closed")
    return {"record_type": "required_gate_idempotence_containment_verification_v0",
            "profile": PROFILE, "status": "accepted", "ok": True,
            "record_status": request["record_status"], "phase": request["phase"],
            "request_sha256": expected_request_sha256, "receipt_sha256": expected_receipt_sha256,
            "record_bindings_verified": True, "attempt_complete": complete,
            "finite_diagnostic_valid": complete, "streams": streams,
            "attempt_status": receipt["status"], "error_code": receipt["error_code"],
            **BOUNDARY}
