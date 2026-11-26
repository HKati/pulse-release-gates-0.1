#!/usr/bin/env python3
"""Fixed original-loader acquisition supervisor and independent data-only replay.

Acquisition supervises one observer process, distinct from PID 1. That process
uses the unchanged collector, which owns its fresh same-observer qualification
and one bounded original capture. Verification never imports the collector or
adapter. Its only subprocesses are the two independent raw checker commands.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import sys


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import required_gate_idempotence_loader_resolution_v0 as core
import check_required_gate_idempotence_loader_resolution_v0 as raw_checker
import check_required_gate_idempotence_loader_resolution_hosted_v0 as hosted
import required_gate_idempotence_exec_stop_hosted_io_v0 as bounded_io

PYTHON = "/usr/local/bin/python3.11"
CONFIG = "tools/required_gate_idempotence_loader_resolution_hosted_v0"
RUNNER = REPO / CONFIG / "run.py"
CAPTURE_CHECKER = REPO / "tools/check_required_gate_idempotence_loader_resolution_v0.py"
CONTROL = Path("/control")
INPUT = Path("/input")
OUTPUT = Path("/output")
BUILD_RECORD = Path("/opt/pulse-loader-resolution-build/build-environment-record.json")
CONTROL_LIMIT = 1024 * 1024


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _selection(phase):
    value = core.parse(bounded_io.read_regular(CONTROL / "hosted-selection.json", CONTROL_LIMIT))
    hosted.validate_selection(value, phase)
    _need(hosted.context() == value["context"]
          and os.environ.get("LOADER_RESOLUTION_HOSTED_PHASE") == phase
          and os.environ.get("LOADER_RESOLUTION_HOSTED_IMAGE_ID") == value["image_id"]
          and os.environ.get("ACCEPTED_POLICY_SHA256") == value["context"]["accepted_policy_sha256"],
          "loader_resolution_hosted_inner_context")
    if phase == "verify":
        _need(hosted.handoff() == value["handoff"], "loader_resolution_hosted_inner_handoff")
    _need(value["sources"] == hosted.source_bindings(),
          "loader_resolution_hosted_inner_sources")
    return value


def _command(argv, logdir, label, timeout_seconds, stream_cap=1048576):
    return bounded_io.run_command(argv, logdir, label, timeout_seconds, stream_cap)


def _environment_check(preserve=False):
    """Check the selected interpreter, crypto tools and original bytes passively."""
    selected = hosted.environment()
    python = selected["python"]
    _need(platform.system() == "Linux" and platform.machine() == "x86_64"
          and platform.python_version() == python["version"]
          and sys.executable == python["executable"] and sys.flags.isolated == 1,
          "loader_resolution_hosted_inner_interpreter")
    _need(os.getuid() > 0 and os.getgid() > 0
          and os.getresuid() == (os.getuid(),) * 3
          and os.getresgid() == (os.getgid(),) * 3,
          "loader_resolution_hosted_inner_identity")
    _need(core.binding(bounded_io.read_regular(python["executable"],
              python["observer_binding"]["size_bytes"])) == python["observer_binding"],
          "loader_resolution_hosted_inner_interpreter_binding")
    for item in selected["expected_files"]:
        original_path = Path(item["path"])
        # Distribution-owned loader/library aliases are selected paths; bind
        # their regular terminal object and recheck resolution after the read.
        resolved = original_path.resolve(strict=True)
        expected = {key: item[key] for key in ("size_bytes", "sha256")}
        _need(core.binding(bounded_io.read_regular(resolved, item["size_bytes"])) == expected
              and original_path.resolve(strict=True) == resolved,
              "loader_resolution_hosted_inner_runtime_file")
    # Original inputs are admitted from the selected /repo archive by the
    # unchanged collector/checker. The image's retained private build payloads
    # are not an input to that admission; current installed objects are checked
    # above, and the build record binds the six original installation inputs.
    for package in python["packages"]:
        try:
            actual = importlib.metadata.version(package["name"])
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError("loader_resolution_hosted_inner_package_missing") from exc
        _need(actual == package["version"], "loader_resolution_hosted_inner_package_version")
    environment_raw = bounded_io.read_regular(REPO / CONFIG / "environment.json", CONTROL_LIMIT)
    requirements_raw = bounded_io.read_regular(REPO / CONFIG / "requirements.lock", 16384)
    _need(core.binding(environment_raw) == hosted.ENVIRONMENT_BINDING
          and core.binding(requirements_raw) == selected["requirements"],
          "loader_resolution_hosted_inner_environment_binding")
    raw = bounded_io.read_regular(BUILD_RECORD, CONTROL_LIMIT)
    record = core.parse(raw)
    _need(core.canonical(record) == raw, "loader_resolution_hosted_inner_build_canonical")
    hosted.validate_build_record(record, selected,
        core.binding(environment_raw), core.binding(requirements_raw))
    if preserve:
        hosted.write_new(OUTPUT / "build-environment-record.json", raw)
    return record


def _clean_result(result, accepted=(0,)):
    return (type(result) is dict and type(result.get("returncode")) is int
            and result["returncode"] in accepted
            and result.get("failure") is None
            and result.get("overflowed_streams") == []
            and result.get("cleanup", {}).get("child_started") is True
            and result.get("cleanup", {}).get("child_reaped") is True
            and result.get("cleanup", {}).get("kill_group_sent") is False
            and result.get("cleanup", {}).get("kill_error_errno") is None
            and result.get("cleanup", {}).get("pending_output_drain_attempted") is True)


def _available(path, limit=CONTROL_LIMIT):
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    return bounded_io.read_regular(path, limit)


def _materials(root):
    return (_available(root / "request.json"),
            _available(root / "capture/capture.json"))


def observe():
    """Invoke the existing native adapter exactly once in its observer process."""
    selection = _selection("acquire")
    _need(os.getpid() >= 2, "loader_resolution_hosted_observer_pid")
    _environment_check()
    # This is the sole import of the adapter. Its run-owner command performs
    # admission and owns the native collector's same-observer qualifications.
    import prepare_required_gate_idempotence_loader_resolution_v0 as adapter
    request = core.make_request(attempt_id=hosted.request_identity(selection["context"]),
                                observer_descriptor=core.original._observer())
    _need(request["observer"] == {"path": PYTHON, **hosted.OBSERVER_BINDING},
          "loader_resolution_hosted_inner_selected_observer")
    request_bytes = core.canonical(request)
    hosted.write_new(OUTPUT / "request.json", request_bytes)
    result = adapter.main([
        "run-owner", "--request", str(OUTPUT / "request.json"),
        "--request-sha256", core.sha(request_bytes),
        "--accepted-policy-sha256", selection["context"]["accepted_policy_sha256"],
        "--acknowledgement", os.environ["LOADER_RESOLUTION_HOSTED_ACKNOWLEDGEMENT"],
        "--output-directory", str(OUTPUT / "capture")])
    _need(type(result) is int and result in (0, 1), "loader_resolution_hosted_inner_adapter_result")
    _need(_selection("acquire") == selection, "loader_resolution_hosted_inner_selection_drift")
    return result


def _native_report(report, request, request_bytes, capture_bytes):
    expected_boundary = {**core.BOUNDARY,
        "consumer_resolution_observed": True, "loader_resolution_verified": True}
    _need(type(report) is dict
          and report.get("record_type") == "required_gate_idempotence_loader_resolution_verification_v0"
          and report.get("profile") == core.PROFILE
          and report.get("status") == "accepted_native_loader_resolution_record"
          and report.get("evidence_origin") == "native_original_loader_capture"
          and report.get("attempt_id") == request["attempt_id"]
          and report.get("request") == core.binding(request_bytes)
          and report.get("capture") == core.binding(capture_bytes)
          and report.get("record_binding_verified") is True
          and report.get("native_record_reconstructed") is True
          and report.get("scripted_record_reconstructed") is False
          and report.get("complete_mechanics_verified") is True
          and report.get("original_loader_capture_completed") is True
          and report.get("incomplete_record_preserved") is False
          and report.get("failure") is None
          and report.get("source_build_policy_admitted_for_replay") is True
          and report.get("current_backing_read_records_verified") is True
          and report.get("original_invocation_record_verified") is True
          and report.get("original_acquisition_ready") is False
          and report.get("future_host_admitted") is False
          and all(type(report.get(key)) is int and report[key] == value for key, value in
                  (("accepted_return_events", 9), ("ptrace_cont_count", 11), ("post_entry_resumes", 0)))
          and all(key in report and type(report[key]) is type(value) and report[key] == value
                  for key, value in expected_boundary.items()),
          "loader_resolution_hosted_inner_native_report")


def _replay(root, selection, phase):
    request_bytes = bounded_io.read_regular(root / "request.json", CONTROL_LIMIT)
    request_sha = core.sha(request_bytes)
    request = core.validate_request(request_bytes, request_sha)
    _need(request["attempt_id"] == hosted.request_identity(selection["context"]),
          "loader_resolution_hosted_inner_attempt_id")
    _need(request["observer"] == {"path": PYTHON, **hosted.OBSERVER_BINDING},
          "loader_resolution_hosted_inner_selected_observer")
    capture_bytes, files = raw_checker.read_capture_directory(root / "capture")
    _need(files.get("request.json") == request_bytes,
          "loader_resolution_hosted_inner_request_copy")
    capture_sha = core.sha(capture_bytes)
    reports = []
    for ordinal in (1, 2):
        label = "capture-check-" + str(ordinal)
        output = OUTPUT / (label + ".json")
        result = _command(
            [PYTHON, "-I", "-B", str(CAPTURE_CHECKER),
             "--request", str(root / "request.json"), "--request-sha256", request_sha,
             "--capture-dir", str(root / "capture"), "--capture-sha256", capture_sha,
             "--accepted-policy-sha256", selection["context"]["accepted_policy_sha256"],
             "--output", str(output)], OUTPUT / "commands", label, 180)
        _need(_clean_result(result), "loader_resolution_hosted_inner_checker_command")
        raw = bounded_io.read_regular(output, CONTROL_LIMIT)
        report = core.parse(raw)
        _need(core.canonical(report) == raw, "loader_resolution_hosted_inner_report_canonical")
        _native_report(report, request, request_bytes, capture_bytes)
        reports.append(raw)
    _need(reports[0] == reports[1], "loader_resolution_hosted_inner_report_divergence")
    _need(bounded_io.read_regular(root / "request.json", CONTROL_LIMIT) == request_bytes
          and raw_checker.read_capture_directory(root / "capture") == (capture_bytes, files),
          "loader_resolution_hosted_inner_evidence_drift")
    _need(_selection(phase) == selection, "loader_resolution_hosted_inner_selection_drift")
    return tuple(reports)


def _error(exc):
    candidate = getattr(exc, "code", None)
    if candidate is None and type(exc) is ValueError:
        candidate = str(exc)
    if (type(candidate) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", candidate)
            and candidate.startswith(("loader_resolution_", "hosted_io_"))):
        return candidate
    return "loader_resolution_hosted_inner_failure"


def _summarize(phase, selection, root, reports=(), error_code=None):
    try:
        request, capture = _materials(root)
    except (OSError, ValueError):
        request, capture = None, None
        error_code = "loader_resolution_hosted_inner_evidence_read"
    summary = hosted.make_summary(phase, selection, request_bytes=request,
        capture_bytes=capture, report_bytes=reports, error_code=error_code)
    leaf = "acquisition-summary.json" if phase == "acquire" else "verification-summary.json"
    hosted.write_new(OUTPUT / leaf, core.canonical(summary))
    return summary


def acquire():
    selection = _selection("acquire")
    reports, error_code = (), None
    try:
        _environment_check(preserve=True)
        result = _command([PYTHON, "-I", "-B", str(RUNNER), "observe"],
                          OUTPUT / "commands", "observe", 240)
        _need(_clean_result(result), "loader_resolution_hosted_inner_observer_command")
        reports = _replay(OUTPUT, selection, "acquire")
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        error_code = _error(exc)
    return _summarize("acquire", selection, OUTPUT, reports, error_code)


def verify():
    selection = _selection("verify")
    reports, error_code = (), None
    root = INPUT / "observation"
    try:
        _environment_check(preserve=True)
        reports = _replay(root, selection, "verify")
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        error_code = _error(exc)
    return _summarize("verify", selection, root, reports, error_code)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("acquire", "verify", "observe"))
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.phase == "observe":
            return observe()
        summary = acquire() if args.phase == "acquire" else verify()
        return 0 if summary["status"] == "completed_native_reconstruction" else 1
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        print(_error(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
