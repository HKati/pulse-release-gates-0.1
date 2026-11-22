#!/usr/bin/env python3
"""Fixed container entrypoint for one synthetic qualification or data-only replay.

The acquire entrypoint supervises one probe subprocess. The probe, not PID 1,
prepares its own context-bound request and invokes the unchanged native adapter.
The verify path never imports the adapter or native producer.
"""
import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import sys


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import check_required_gate_idempotence_loader_two_slot_attempt_v0 as core
import check_required_gate_idempotence_loader_two_slot_hosted_v0 as hosted
import required_gate_idempotence_exec_stop_hosted_io_v0 as bounded_io

PYTHON = "/usr/local/bin/python3.11"
RUNNER = REPO / "tools/required_gate_idempotence_loader_two_slot_hosted_v0/run.py"
ATTEMPT_CHECKER = REPO / "tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py"
CONTROL = Path("/control")
INPUT = Path("/input")
OUTPUT = Path("/output")
BUILD_RECORD = Path("/opt/pulse-two-slot-build/build-environment-record.json")


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _selection(phase):
    value = core.parse(core.read_regular(CONTROL / "hosted-selection.json"))
    hosted.validate_selection(value, phase)
    _need(hosted.context() == value["context"]
          and os.environ.get("TWO_SLOT_HOSTED_PHASE") == phase
          and os.environ.get("TWO_SLOT_HOSTED_IMAGE_ID") == value["image_id"],
          "two_slot_hosted_inner_context")
    if phase == "verify":
        _need(hosted.handoff() == value["handoff"], "two_slot_hosted_inner_handoff")
    _need(value["sources"] == hosted.source_bindings(),
          "two_slot_hosted_inner_sources")
    return value


def _command(argv, logdir, label, timeout_seconds, stream_cap=1048576):
    return bounded_io.run_command(argv, logdir, label, timeout_seconds, stream_cap)


def _environment_check(preserve=False):
    """Passively check the selected interpreter and installed verifier closure."""
    selected = hosted.environment()
    python = selected["python"]
    _need(platform.system() == "Linux" and platform.machine() == "x86_64"
          and platform.python_version() == python["version"]
          and sys.executable == python["executable"] and sys.flags.isolated == 1,
          "two_slot_hosted_inner_interpreter")
    _need(core.binding(core.read_regular(python["executable"])) == python["observer_binding"],
          "two_slot_hosted_inner_interpreter_binding")
    installed = {}
    for package in python["packages"]:
        try:
            actual = importlib.metadata.version(package["name"])
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError("two_slot_hosted_inner_package_missing") from exc
        _need(actual == package["version"], "two_slot_hosted_inner_package_version")
        installed[package["name"]] = actual
    expected = {
        "record_type": "required_gate_idempotence_loader_two_slot_build_v0",
        "profile": hosted.PROFILE, "environment": hosted.ENVIRONMENT_BINDING,
        "requirements": selected["requirements"],
        "wheels": {package["filename"]: {key: package[key] for key in ("size_bytes", "sha256")}
                   for package in python["packages"]},
        "python": python["observer_binding"], "installed": installed,
        "offline_install": True, "reproducible_image_claimed": False,
        "original_payload_included": False, "authority_effect": "none"}
    raw = core.read_regular(BUILD_RECORD)
    _need(raw == core.canonical(expected), "two_slot_hosted_inner_build_record")
    if preserve:
        core.write_new(OUTPUT / "build-environment-record.json", raw)
    return expected


def _clean_result(result, accepted=(0,)):
    return (type(result) is dict and type(result.get("returncode")) is int
            and result["returncode"] in accepted
            and result.get("failure") is None
            and result.get("overflowed_streams") == []
            and result.get("cleanup", {}).get("child_started") is True
            and result.get("cleanup", {}).get("child_reaped") is True
            and result.get("cleanup", {}).get("kill_group_sent") is False
            and result.get("cleanup", {}).get("kill_error_errno") is None)


def _available(path, limit=65536, empty=False):
    try:
        return core.read_regular(path, limit, empty=empty)
    except FileNotFoundError:
        return None


def _materials(root):
    return (_available(root / "request.json"),
            _available(root / "attempt/attempt.json"),
            _available(root / "attempt/qualification.json", core.MAX_QUALIFICATION_BYTES,
                       empty=True))


def probe():
    """The only function allowed to import and invoke the native attempt adapter."""
    selection = _selection("acquire")
    _need(os.getpid() >= 2, "two_slot_hosted_probe_pid")
    _environment_check()
    # Delayed import is deliberate: verification imports no producer path.
    import prepare_required_gate_idempotence_loader_two_slot_v0 as adapter
    request_bytes = adapter.prepare(
        output=OUTPUT / "request.json",
        request_id=hosted.request_identity(selection["context"]))
    receipt = adapter.attempt(
        request_bytes=request_bytes,
        expected_request_sha256=core.binding(request_bytes)["sha256"],
        acknowledgement=core.ACKNOWLEDGEMENT,
        output_directory=OUTPUT / "attempt")
    _need(_selection("acquire") == selection, "two_slot_hosted_inner_selection_drift")
    return 0 if (receipt["status"] == "completed"
                 and receipt["evidence_origin"] == "native_owned_probe"
                 and type(receipt["producer_invocations"]) is int
                 and receipt["producer_invocations"] == 1) else 1


def _replay(root, selection, phase):
    request_bytes = core.read_regular(root / "request.json")
    request = core.verify_request(
        request_bytes=request_bytes,
        expected_request_sha256=core.binding(request_bytes)["sha256"])
    _need(request["request_id"] == hosted.request_identity(selection["context"]),
          "two_slot_hosted_inner_request_id")
    _need(request["expected_context"]["observer"] == hosted.OBSERVER_BINDING,
          "two_slot_hosted_inner_selected_observer")
    preserved_request, attempt_bytes, qualification_bytes = core.read_attempt_directory(
        root / "attempt")
    _need(preserved_request == request_bytes, "two_slot_hosted_inner_request_copy")
    request_sha = core.binding(request_bytes)["sha256"]
    attempt_sha = core.binding(attempt_bytes)["sha256"]
    reports = []
    for ordinal in (1, 2):
        output = OUTPUT / ("attempt-check-" + str(ordinal) + ".json")
        result = _command(
            [PYTHON, "-I", "-B", str(ATTEMPT_CHECKER),
             "--request", str(root / "request.json"), "--request-sha256", request_sha,
             "--attempt-directory", str(root / "attempt"), "--attempt-sha256", attempt_sha,
             "--output", str(output)], OUTPUT / "commands",
            "attempt-check-" + str(ordinal), 30)
        _need(_clean_result(result), "two_slot_hosted_inner_checker_command")
        raw = core.read_regular(output)
        report = core.parse(raw)
        _need(core.canonical(report) == raw
              and report.get("status") == "accepted_native_qualification_attempt"
              and report.get("evidence_origin") == "native_owned_probe"
              and type(report.get("producer_invocations")) is int
              and report.get("producer_invocations") == 1
              and report.get("native_record_reconstructed") is True
              and report.get("scripted_record_reconstructed") is False
              and report.get("complete_mechanics_verified") is True
              and report.get("request_id") == request["request_id"]
              and report.get("request") == core.binding(request_bytes)
              and report.get("attempt") == core.binding(attempt_bytes)
              and all(key in report and type(report[key]) is type(value)
                      and report[key] == value for key, value in core.BOUNDARY.items()),
              "two_slot_hosted_inner_native_report")
        reports.append(raw)
    _need(reports[0] == reports[1], "two_slot_hosted_inner_report_divergence")
    _need(core.read_regular(root / "request.json") == request_bytes
          and core.read_attempt_directory(root / "attempt")
          == (preserved_request, attempt_bytes, qualification_bytes),
          "two_slot_hosted_inner_evidence_drift")
    _need(_selection(phase) == selection, "two_slot_hosted_inner_selection_drift")
    return tuple(reports)


def _error(exc):
    candidate = getattr(exc, "code", None)
    if type(candidate) is str and candidate.startswith("two_slot_"):
        return candidate
    if type(exc) is ValueError and str(exc).startswith("two_slot_"):
        return str(exc)
    return "two_slot_hosted_inner_failure"


def _summarize(phase, selection, root, reports=(), error_code=None):
    try:
        request, attempt, qualification = _materials(root)
    except (OSError, ValueError):
        request, attempt, qualification = None, None, None
        error_code = "two_slot_hosted_inner_evidence_read"
    summary = hosted.make_summary(
        phase, selection, request_bytes=request, attempt_bytes=attempt,
        qualification_bytes=qualification, report_bytes=reports, error_code=error_code)
    leaf = "acquisition-summary.json" if phase == "acquire" else "verification-summary.json"
    core.write_new(OUTPUT / leaf, core.canonical(summary))
    return summary


def acquire():
    selection = _selection("acquire")
    reports, error_code = (), None
    try:
        _environment_check(preserve=True)
        result = _command([PYTHON, "-I", "-B", str(RUNNER), "probe"],
                          OUTPUT / "commands", "probe", 45)
        _need(_clean_result(result), "two_slot_hosted_inner_probe_command")
        reports = _replay(OUTPUT, selection, "acquire")
    except (OSError, ValueError) as exc:
        error_code = _error(exc)
    return _summarize("acquire", selection, OUTPUT, reports, error_code)


def verify():
    selection = _selection("verify")
    reports, error_code = (), None
    root = INPUT / "observation"
    try:
        _environment_check(preserve=True)
        reports = _replay(root, selection, "verify")
    except (OSError, ValueError) as exc:
        error_code = _error(exc)
    return _summarize("verify", selection, root, reports, error_code)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("acquire", "verify", "probe"))
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.phase == "probe":
            return probe()
        summary = acquire() if args.phase == "acquire" else verify()
        return 0 if summary["status"] == "completed_native_reconstruction" else 1
    except (OSError, ValueError) as exc:
        print(_error(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
