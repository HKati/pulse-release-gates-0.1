#!/usr/bin/env python3
"""Closed container commands for one original-launcher entry-stop observation.

Only ``acquire`` can invoke the acknowledged collector, once, after two accepted
request reconstructions. ``verify`` only reconstructs the preserved capture.
All executable Python sources come from the read-only reviewed checkout.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import required_gate_idempotence_exec_stop_hosted_io_v0 as io

REPO = Path("/repo")
ORIGINALS = Path("/originals")
OUTPUT = Path("/output")
INPUT = Path("/input")
ENVIRONMENT = REPO / "tools/required_gate_idempotence_entry_stop_hosted_v0/environment.json"
REQUIREMENTS = ENVIRONMENT.with_name("requirements.lock")
BUILD_RECORD = Path("/opt/pulse-entry-stop-build/build-environment-record.json")
ADAPTER = REPO / "tools/prepare_required_gate_idempotence_entry_stop_v0.py"
PYTHON = "/usr/local/bin/python3.11"
PROFILE = "linux_x86_64_original_launcher_entry_stop_v0"
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_ENTRY_STOP_ONLY"
WORKFLOW_REF = (
    "HKati/pulse-release-gates-0.1/"
    ".github/workflows/required_gate_idempotence_entry_stop_v0.yml@refs/heads/main"
)
CONTROL_BYTES = 1024 * 1024
COMMAND_SECONDS = 300
NARROW_FLAGS = (
    "kernel_exec_checkpoint_observed", "fresh_cp0_prefix_verified", "entry_checkpoint_observed",
    "selected_native_image_bindings_verified", "selected_entry_memory_ranges_observed",
    "selected_entry_rx_ranges_match_original", "task_guard_installation_verified",
    "hardware_entry_stop_verified", "owned_entry_stop_cleanup_verified",
)
EXPECTED_FILES = {'/lib64/ld-linux-x86-64.so.2': {'sha256': 'c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307',
                                 'size_bytes': 225672},
 '/usr/bin/gpg': {'sha256': '7c9d2f9416aabcd10199e2984439f49612644a948279ac56bdf70d69c8958ddf',
                  'size_bytes': 1230080},
 '/usr/local/bin/python3.11': {'sha256': '92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79',
                               'size_bytes': 14472},
 '/usr/lib/x86_64-linux-gnu/libc.so.6': {'sha256': '9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92',
                                         'size_bytes': 1995216},
 '/usr/lib/x86_64-linux-gnu/libcap.so.2': {'sha256': '41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b',
                                           'size_bytes': 47288},
 '/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0': {'sha256': '92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3',
                                               'size_bytes': 711216},
 '/usr/lib/x86_64-linux-gnu/libselinux.so.1': {'sha256': '5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c',
                                               'size_bytes': 202984}}

# This one pre-build restoration is selected independently of the original
# object checks. It accepts only the preserved base object's exact before bytes.
NATIVE_RESTORATIONS = [{
    "input": "native/libpcre2-8.so.0",
    "host_path": "/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0",
    "symlink_target": "libpcre2-8.so.0.14.0",
    "resolved_path": "/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0.14.0",
    "before": {
        "sha256": "8dde125b341abfdf4a596d2974cd3048e350cbc8d2d77acd54ea044f7815ca77",
        "size_bytes": 711216,
    },
    "after": {
        "sha256": "92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3",
        "size_bytes": 711216,
    },
    "mode": 420,
}]

PYTHON_PACKAGES = {
    "pyyaml": "6.0.3", "attrs": "26.1.0", "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1", "referencing": "0.37.0",
    "rpds-py": "2026.9.1", "typing-extensions": "4.16.0",
}
CHILD_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
}


class HostedRunError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise HostedRunError(code)


def _canonical_json(raw):
    value = io._parse(raw)
    _need(type(value) is dict and io.canonical(value) == raw, "hosted_runner_noncanonical_json")
    return value


def validate_context(environment, phase):
    """Validate only the exact, manually dispatched owner/main/attempt-1 case."""
    _need(phase in {"acquire", "verify"}, "hosted_runner_phase")
    expected = {
        "GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1",
        "GITHUB_REPOSITORY_ID": "1061766508",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
        "ENTRY_STOP_ACKNOWLEDGEMENT": ACKNOWLEDGEMENT, "ENTRY_STOP_PHASE": phase,
    }
    _need(all(environment.get(name) == value for name, value in expected.items()),
          "hosted_runner_workflow_context")
    source = environment.get("EXPECTED_SOURCE_COMMIT", "")
    _need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}", source) is not None
          and environment.get("GITHUB_SHA") == source
          and environment.get("GITHUB_WORKFLOW_SHA") == source,
          "hosted_runner_source_context")
    run_id = environment.get("GITHUB_RUN_ID", "")
    _need(type(run_id) is str and re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is not None,
          "hosted_runner_run_id")
    return {
        "repository": expected["GITHUB_REPOSITORY"],
        "repository_id": expected["GITHUB_REPOSITORY_ID"],
        "source_commit": source, "workflow_sha": source, "workflow_ref": WORKFLOW_REF,
        "run_id": int(run_id), "run_attempt": 1,
        "event_name": "workflow_dispatch", "ref": "refs/heads/main",
        "actor": "HKati", "triggering_actor": "HKati", "acknowledgement": ACKNOWLEDGEMENT,
    }


def derive_attempt_id(context):
    return io.sha(io.canonical({
        "source_commit": context["source_commit"], "run_id": context["run_id"],
        "run_attempt": context["run_attempt"], "profile": PROFILE,
    }))[:32]


def validate_process_status(raw, uid, gid):
    """Pure validation of the recorded observer status; never changes policy."""
    _need(type(uid) is int and type(gid) is int and uid > 0 and gid > 0,
          "hosted_runner_nonroot_identity")
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise HostedRunError("hosted_runner_status_encoding") from exc
    fields = {}
    for line in text.splitlines():
        _need(":" in line, "hosted_runner_status_line")
        name, value = line.split(":", 1)
        _need(name not in fields, "hosted_runner_status_duplicate")
        fields[name] = value.strip()
    for name, expected in {"Threads": "1", "TracerPid": "0", "NoNewPrivs": "1", "Seccomp": "2"}.items():
        _need(fields.get(name) == expected, "hosted_runner_process_policy")
    for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
        value = fields.get(name, "")
        _need(re.fullmatch(r"[0-9a-fA-F]{16}", value) is not None and int(value, 16) == 0,
              "hosted_runner_capabilities")
    for name, selected in (("Uid", uid), ("Gid", gid)):
        values = fields.get(name, "").split()
        _need(len(values) == 4 and all(value == str(selected) for value in values),
              "hosted_runner_process_identity")
    return {name: fields[name] for name in (
        "Uid", "Gid", "Threads", "TracerPid", "CapInh", "CapPrm", "CapEff", "CapBnd",
        "CapAmb", "NoNewPrivs", "Seccomp",
    )}


def _passive_read(path, limit, *, pseudo=False):
    """Pin an ordinary system symlink target before bounded passive reading.

    /proc/self/fd is used only to read the already owned O_PATH descriptor.
    A substituted FIFO/device is rejected before any readable open. No native
    object is launched and no tracing or security policy is changed.
    """
    allowed = {*EXPECTED_FILES, "/proc/self/exe", "/proc/self/status",
               "/proc/sys/kernel/random/boot_id", "/etc/os-release"}
    _need(str(path) in allowed and type(limit) is int and 0 < limit <= 2 * 1024 * 1024,
          "hosted_runner_passive_selection")
    pin = os.open(path, os.O_PATH | os.O_CLOEXEC)
    readable = None
    try:
        before = os.fstat(pin)
        _need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit,
              "hosted_runner_passive_type")
        readable = os.open("/proc/self/fd/" + str(pin), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        opened = os.fstat(readable)
        _need(io._identity(before) == io._identity(opened), "hosted_runner_passive_identity")
        chunks, size = [], 0
        while size <= limit:
            piece = os.read(readable, min(65536, limit + 1 - size))
            if not piece:
                break
            chunks.append(piece)
            size += len(piece)
        _need(size <= limit and (pseudo or size == before.st_size), "hosted_runner_passive_size")
        _need(io._identity(before) == io._identity(os.fstat(readable))
              == io._identity(os.fstat(pin)), "hosted_runner_passive_changed")
        return b"".join(chunks)
    finally:
        if readable is not None:
            os.close(readable)
        os.close(pin)


def validate_build_record(record, selection, selection_raw, lock_raw):
    _need(record.get("record_type") == "required_gate_idempotence_entry_stop_hosted_environment_build_v0",
          "hosted_runner_build_record_type")
    _need(record.get("environment_selection") == io.binding(selection_raw)
          and record.get("requirements_lock") == io.binding(lock_raw),
          "hosted_runner_build_input_binding")
    _need(record.get("base_image_reference") == selection["base_image"]["reference"]
          and record.get("python_version") == "3.11.16", "hosted_runner_build_environment")
    _need(record.get("installed_debian_delta") == [
        {"name": item["name"], "version": item["version"]} for item in selection["debian"]["packages"]
    ], "hosted_runner_build_debian_selection")
    _need(record.get("selected_python_packages") == [
        {"name": item["name"], "version": item["version"]} for item in selection["python"]["packages"]
    ], "hosted_runner_build_python_selection")
    checked = record.get("checked_files")
    _need(type(checked) is list and len(checked) == len(EXPECTED_FILES), "hosted_runner_build_file_roster")
    _need({item["path"]: {key: item[key] for key in ("sha256", "size_bytes")}
           for item in checked} == EXPECTED_FILES, "hosted_runner_build_file_binding")
    _need(io.canonical(selection.get("native_object_restorations")) == io.canonical(NATIVE_RESTORATIONS),
          "hosted_runner_native_restoration_selection")
    expected_restorations = [{**item, "action": "restored_selected_base_original",
        "observed_before": item["before"], "observed_after": item["after"]}
        for item in NATIVE_RESTORATIONS]
    _need(io.canonical(record.get("native_object_restorations")) == io.canonical(expected_restorations),
          "hosted_runner_build_native_restoration_binding")
    for item in NATIVE_RESTORATIONS:
        _need(item["after"] == EXPECTED_FILES[item["host_path"]]
              and all(row.get("resolved_path") == item["resolved_path"]
                      for row in checked if row["path"] == item["host_path"]),
              "hosted_runner_build_native_restoration_path")
    objects = record.get("original_native_objects")
    _need(type(objects) is list and len(objects) == 6, "hosted_runner_build_native_roster")
    for actual, selected in zip(objects, selection["original_native_objects"]):
        _need(type(actual) is dict and set(actual) == set(selected) | {"action", "resolved_path"}
              and all(actual.get(key) == value for key, value in selected.items()),
              "hosted_runner_build_native_binding")
        if selected["host_path"] is None:
            _need(actual["action"] == "retained_data_only" and actual["resolved_path"] is None,
                  "hosted_runner_build_launcher_data_only")
        else:
            allowed = {"existing_original_verified"}
            if selected["installation"] == "install_if_absent_or_require_existing_exact":
                allowed.add("installed_absent_original")
            _need(actual["action"] in allowed and type(actual["resolved_path"]) is str
                  and actual["resolved_path"].startswith("/"), "hosted_runner_build_native_action")
    for restored in NATIVE_RESTORATIONS:
        rows = [item for item in objects if item["input"] == restored["input"]]
        _need(len(rows) == 1 and rows[0]["action"] == "existing_original_verified"
              and rows[0]["resolved_path"] == restored["resolved_path"],
              "hosted_runner_build_native_restoration_result")
    _need(record.get("host_environment_qualified") is False
          and record.get("native_acquisition_performed") is False
          and record.get("authority_effect") == "none", "hosted_runner_build_scope")


def _mkdir_private(path):
    parent, chain = io._pin_directory(path.parent)
    try:
        os.mkdir(path.name, mode=0o700, dir_fd=parent)
        io._check_chain(chain)
    finally:
        io._close_chain(chain)


def validate_runtime(environment):
    """Preserve and check passive facts before calling any original adapter."""
    evidence = OUTPUT / "host-evidence"
    _mkdir_private(evidence)
    selection_raw = io.read_regular(ENVIRONMENT, CONTROL_BYTES)
    selection = io._parse(selection_raw)
    _need(selection["record_type"] == "required_gate_idempotence_entry_stop_hosted_environment_v0"
          and selection["profile"] == PROFILE and selection["platform"] == "linux/amd64",
          "hosted_runner_environment_selection")
    _need(len(selection["expected_files"]) == len(EXPECTED_FILES)
          and {item["path"]: {key: item[key] for key in ("sha256", "size_bytes")}
               for item in selection["expected_files"]} == EXPECTED_FILES,
          "hosted_runner_environment_file_selection")
    _need(io.canonical(selection.get("native_object_restorations")) == io.canonical(NATIVE_RESTORATIONS),
          "hosted_runner_native_restoration_selection")
    image_id = environment.get("ENTRY_STOP_IMAGE_ID", "")
    _need(type(image_id) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None,
          "hosted_runner_image_id")
    _need(sys.executable == PYTHON and platform.python_version() == "3.11.16"
          and sys.platform == "linux" and os.uname().machine == "x86_64",
          "hosted_runner_python_identity")
    _need(selection["python"]["executable"] == PYTHON and selection["python"]["version"] == "3.11.16"
          and selection["python"]["observer_binding"] == EXPECTED_FILES[PYTHON],
          "hosted_runner_python_selection")
    uid, gid = os.getuid(), os.getgid()
    _need(os.getresuid() == (uid, uid, uid) and os.getresgid() == (gid, gid, gid),
          "hosted_runner_effective_identity")
    raw_status = _passive_read("/proc/self/status", 65536, pseudo=True)
    io.write_new(evidence / "observer.status.bin", raw_status)
    status = validate_process_status(raw_status, uid, gid)
    boot_id = _passive_read("/proc/sys/kernel/random/boot_id", 256, pseudo=True)
    io.write_new(evidence / "kernel.boot_id.bin", boot_id)
    _need(re.fullmatch(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n", boot_id) is not None,
          "hosted_runner_boot_id")
    os_release = _passive_read("/etc/os-release", 16384)
    io.write_new(evidence / "os-release.bin", os_release)
    uname = dict(zip(("sysname", "nodename", "release", "version", "machine"), os.uname()))
    io.write_new(evidence / "uname.json", io.canonical(uname))

    _need(os.readlink("/proc/self/exe") == PYTHON, "hosted_runner_observer_path")
    observer = _passive_read("/proc/self/exe", EXPECTED_FILES[PYTHON]["size_bytes"])
    _need(io.binding(observer) == EXPECTED_FILES[PYTHON]
          and os.readlink("/proc/self/exe") == PYTHON, "hosted_runner_observer_bytes")
    checked_files = []
    for path, expected in EXPECTED_FILES.items():
        raw = _passive_read(path, expected["size_bytes"])
        _need(io.binding(raw) == expected, "hosted_runner_file_binding")
        checked_files.append({"path": path, **io.binding(raw)})
    packages = selection["python"]["packages"]
    normalized = lambda value: re.sub(r"[-_.]+", "-", value).lower()
    _need(len(packages) == len(PYTHON_PACKAGES) and {
        normalized(item["name"]): item["version"] for item in packages
    } == PYTHON_PACKAGES, "hosted_runner_python_package_selection")
    try:
        versions = {name: importlib.metadata.version(name) for name in PYTHON_PACKAGES}
    except importlib.metadata.PackageNotFoundError as error:
        raise HostedRunError("hosted_runner_python_package_missing") from error
    _need(versions == PYTHON_PACKAGES, "hosted_runner_installed_python_packages")
    build_raw = io.read_regular(BUILD_RECORD, CONTROL_BYTES)
    io.write_new(evidence / "build-environment-record.json", build_raw)
    build = _canonical_json(build_raw)
    validate_build_record(build, selection, selection_raw, io.read_regular(REQUIREMENTS, 16384))
    record = {
        "record_type": "required_gate_idempotence_entry_stop_hosted_runtime_environment_v0",
        "profile": PROFILE, "environment_selection": io.binding(selection_raw),
        "build_environment_record": io.binding(build_raw),
        "base_image": selection["base_image"],
        "image_id": image_id, "image_id_origin": "external_host_docker_inspect_assertion",
        "python_executable": PYTHON, "python_version": platform.python_version(),
        "observer_executable": io.binding(observer), "python_packages": versions,
        "uid": uid, "gid": gid, "process_status": status,
        "raw_status": io.binding(raw_status), "boot_id": io.binding(boot_id),
        "os_release": io.binding(os_release), "uname": uname, "checked_files": checked_files,
        "host_environment_qualified": False, "native_acquisition_performed": False,
        "authority_effect": "none",
    }
    io.write_new(OUTPUT / "runtime-environment.json", io.canonical(record))
    return record


def command_succeeded(result):
    return type(result.get("returncode")) is int and result["returncode"] == 0 and result.get("failure") is None


def complete_report(report, attempt_id, request_sha256, capture_sha256):
    return (
        type(report) is dict
        and report.get("record_type") == "required_gate_idempotence_entry_stop_verification_v0"
        and report.get("profile") == PROFILE and report.get("status") == "accepted"
        and report.get("attempt_id") == attempt_id
        and report.get("request_sha256") == request_sha256
        and report.get("capture_sha256") == capture_sha256
        and report.get("observation_record_verified") is True
        and report.get("observation_complete") is True
        and all(report.get(name) is True for name in NARROW_FLAGS)
        and report.get("failure") is None and report.get("authority_effect") == "none"
        and "metric_pass" in report and report["metric_pass"] is None
    )


def _request(raw, attempt_id):
    request = _canonical_json(raw)
    _need(request.get("profile") == PROFILE and request.get("attempt_id") == attempt_id,
          "hosted_runner_request_attempt")
    _need(request.get("observer") == {"path": PYTHON, **EXPECTED_FILES[PYTHON]},
          "hosted_runner_request_observer")
    guard = io.read_regular(_qualification_path("task_guard"), CONTROL_BYTES, private=True)
    hardware = io.read_regular(_qualification_path("hardware"), CONTROL_BYTES, private=True)
    _need(request.get("guard", {}).get("qualification") == io.binding(guard)
          and request.get("hardware_qualification") == io.binding(hardware),
          "hosted_runner_request_qualification_binding")
    return request


def _prepared_report(raw, attempt_id, request_binding):
    report = _canonical_json(raw)
    _need(report.get("record_type") == "required_gate_idempotence_entry_stop_preparation_verification_v0"
          and report.get("profile") == PROFILE and report.get("status") == "accepted"
          and report.get("attempt_id") == attempt_id and report.get("request") == request_binding,
          "hosted_runner_preparation_report")
    _need(all(report.get(name) is True for name in (
        "original_relationships_reconstructed", "distribution_signature_freshly_verified",
        "original_reports_reproduced", "task_guard_qualification_record_verified",
        "hardware_qualification_record_verified",
    )), "hosted_runner_preparation_incomplete")
    return report


def _adapter(command, label, *, request_sha256=None, capture_sha256=None, attempt_id=None):
    argv = [PYTHON, "-I", "-B", str(ADAPTER), command,
            "--originals-directory", str(ORIGINALS), "--originals-sha256", io.MANIFEST_SHA256,
            "--verification-directory", str(OUTPUT / (label + "-signature"))]
    for option, name in (("task-guard", "task_guard"), ("hardware", "hardware")):
        path = _qualification_path(name)
        raw = io.read_regular(path, CONTROL_BYTES, private=True)
        argv.extend(("--" + option + "-qualification", str(path),
                     "--" + option + "-qualification-sha256", io.sha(raw)))
    if command == "prepare":
        argv.extend(("--attempt-id", attempt_id, "--output", str(OUTPUT / "request.json")))
    else:
        argv.extend(("--request", str(OUTPUT / "request.json"), "--request-sha256", request_sha256))
        if command == "run-owner":
            argv.extend(("--acknowledgement", ACKNOWLEDGEMENT, "--output-directory", str(OUTPUT / "capture")))
        else:
            argv.extend(("--output", str(OUTPUT / (label + ".json"))))
        if command == "check-capture":
            argv.extend(("--capture-directory", str(OUTPUT / "capture"), "--capture-sha256", capture_sha256))
    return io.run_command(argv, OUTPUT / "commands", label, COMMAND_SECONDS, env=CHILD_ENV)


def _capture_binding():
    path = OUTPUT / "capture/capture.json"
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    return io.binding(io.read_regular(path, CONTROL_BYTES, private=True))


def _qualification_path(name):
    _need(name in {"task_guard", "hardware"}, "hosted_runner_qualification_name")
    return OUTPUT / "qualifications" / ("task-guard.json" if name == "task_guard" else "hardware.json")


def _validate_qualifications(summary, expected_context=None):
    """Validate preserved records as data; verification never probes its host."""
    import check_required_gate_idempotence_entry_task_guard_v0 as guard_check
    import check_required_gate_idempotence_entry_stop_v0 as entry_check
    guard_raw = io.read_regular(_qualification_path("task_guard"), CONTROL_BYTES, private=True)
    hardware_raw = io.read_regular(_qualification_path("hardware"), CONTROL_BYTES, private=True)
    guard_record = _canonical_json(guard_raw)
    _canonical_json(hardware_raw)
    if expected_context is not None:
        _need(io.canonical(guard_record["environment"]) == io.canonical(expected_context),
              "hosted_runner_qualification_current_context")
    sources = [{"path": name, **io.binding(io.read_regular(REPO / name, CONTROL_BYTES))}
               for name in entry_check.GUARD_SOURCES]
    guard_check.validate_qualification(guard_raw, expected_sources=sources,
                                       expected_environment=guard_record["environment"])
    entry_check.validate_hardware_qualification(hardware_raw, io.sha(hardware_raw),
                                               expected_context=guard_record["environment"])
    summary["qualifications"] = {"task_guard": io.binding(guard_raw), "hardware": io.binding(hardware_raw)}
    summary["qualification_preconditions_verified"] = True
    return summary["qualifications"]


def _qualify(summary):
    """Attempt both authored probes before assessing either as an admission."""
    _mkdir_private(OUTPUT / "qualifications")
    commands = (
        ("task_guard", "task-guard-qualification", 40,
         [PYTHON, "-I", "-B", str(REPO / "tools/required_gate_idempotence_entry_task_guard_v0.py"),
          "qualify", "--output", str(_qualification_path("task_guard"))]),
        ("hardware", "hardware-qualification", 30,
         [PYTHON, "-I", "-B", str(REPO / "tools/qualify_required_gate_idempotence_entry_stop_v0.py"),
          "--output", str(_qualification_path("hardware"))]),
    )
    results = []
    for name, label, seconds, argv in commands:
        try:
            result = io.run_command(argv, OUTPUT / "commands", label, seconds, env=CHILD_ENV)
        except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            result = {"returncode": None, "failure": "hosted_runner_qualification_command_failed"}
        results.append(result)
    summary["qualification_commands_completed"] = all(type(result.get("returncode")) is int for result in results)
    for name in ("task_guard", "hardware"):
        try:
            summary["qualifications"][name] = io.binding(io.read_regular(
                _qualification_path(name), CONTROL_BYTES, private=True))
        except FileNotFoundError:
            pass
    _need(all(command_succeeded(result) for result in results), "hosted_runner_capability_incomplete")
    # This import is acquire-only. Reading current_context is passive: it does
    # not install a filter, fork a probe or invoke the original collector.
    import required_gate_idempotence_entry_task_guard_v0 as guard_native
    current = guard_native.current_context()
    io.write_new(OUTPUT / "qualifications/acquisition-context.json", io.canonical(current))
    _validate_qualifications(summary, expected_context=current)


def acquire(context, summary):
    _qualify(summary)
    attempt_id = derive_attempt_id(context)
    result = _adapter("prepare", "prepare", attempt_id=attempt_id)
    _need(command_succeeded(result), "hosted_runner_prepare_failed")
    request_raw = io.read_regular(OUTPUT / "request.json", CONTROL_BYTES, private=True)
    _request(request_raw, attempt_id)
    summary["request"] = request_binding = io.binding(request_raw)
    _prepared_report(io.read_regular(OUTPUT / "commands/prepare.stdout.bin", CONTROL_BYTES, private=True),
                     attempt_id, request_binding)
    results = [_adapter("check", "request-check-" + str(number), request_sha256=request_binding["sha256"])
               for number in (1, 2)]
    _need(all(command_succeeded(item) for item in results), "hosted_runner_request_check_failed")
    reports = [io.read_regular(OUTPUT / ("request-check-" + str(number) + ".json"), CONTROL_BYTES, private=True)
               for number in (1, 2)]
    for number, raw in enumerate(reports, 1):
        _prepared_report(raw, attempt_id, request_binding)
        summary["reports"]["request-check-" + str(number)] = io.binding(raw)
    _need(reports[0] == reports[1], "hosted_runner_request_reports_differ")
    summary["canonical_reports_byte_identical"] = True
    summary["acquisition_command_invoked"] = True
    result = _adapter("run-owner", "acquisition", request_sha256=request_binding["sha256"])
    summary["acquisition_returncode"] = result["returncode"]
    summary["capture"] = capture_binding = _capture_binding()
    raw = io.read_regular(OUTPUT / "commands/acquisition.stdout.bin", CONTROL_BYTES, private=True)
    summary["reports"]["acquisition"] = io.binding(raw)
    report = _canonical_json(raw)
    _need(capture_binding is not None, "hosted_runner_capture_missing")
    _need(command_succeeded(result)
          and complete_report(report, attempt_id, request_binding["sha256"], capture_binding["sha256"]),
          "hosted_runner_acquisition_incomplete")
    summary.update({"observation_complete": True, "status": "completed", **{name: True for name in NARROW_FLAGS}})


def capture_inventory(receipt):
    """Select the exact capture tree from the host-verified full artifact receipt."""
    files = receipt.get("files")
    _need(type(files) is dict, "hosted_runner_receipt_files")
    prefix = "observation/capture/"
    result = {name[len(prefix):]: descriptor for name, descriptor in files.items()
              if type(name) is str and name.startswith(prefix)}
    _need("capture.json" in result and "request.json" in result, "hosted_runner_receipt_capture_missing")
    io._inventory(result)
    return result


def validate_preserved_build_record(receipt):
    """Recheck the acquisition's selected restoration as preserved data only."""
    relative = "observation/host-evidence/build-environment-record.json"
    raw = io.read_regular(INPUT / relative, CONTROL_BYTES, private=True)
    _need(receipt["files"].get(relative) == io.binding(raw),
          "hosted_runner_receipt_build_record_binding")
    record = _canonical_json(raw)
    selection_raw = io.read_regular(ENVIRONMENT, CONTROL_BYTES)
    selection = io._parse(selection_raw)
    validate_build_record(record, selection, selection_raw, io.read_regular(REQUIREMENTS, 16384))
    return io.binding(raw)


def verify(context, summary):
    attempt_id = derive_attempt_id(context)
    receipt = _canonical_json(io.read_regular(INPUT / "receipt.json", 8 * CONTROL_BYTES, private=True))
    _need(receipt.get("context") == context, "hosted_runner_receipt_context")
    validate_preserved_build_record(receipt)
    _mkdir_private(OUTPUT / "qualifications")
    for name, field in (("task_guard", "task_guard_qualification"), ("hardware", "hardware_qualification")):
        relative = "observation/qualifications/" + _qualification_path(name).name
        raw = io.read_regular(INPUT / relative, CONTROL_BYTES, private=True)
        expected = io.binding(raw)
        _need(receipt.get(field) == expected and receipt["files"].get(relative) == expected,
              "hosted_runner_receipt_qualification_binding")
        io.write_new(_qualification_path(name), raw)
    context_path = "observation/qualifications/acquisition-context.json"
    context_raw = io.read_regular(INPUT / context_path, CONTROL_BYTES, private=True)
    _need(receipt["files"].get(context_path) == io.binding(context_raw),
          "hosted_runner_receipt_qualification_context_binding")
    original_context = _canonical_json(context_raw)
    io.write_new(OUTPUT / "qualifications/acquisition-context.json", context_raw)
    _validate_qualifications(summary, expected_context=original_context)
    inventory = capture_inventory(receipt)
    request_raw = io.read_regular(INPUT / "observation/request.json", CONTROL_BYTES, private=True)
    _request(request_raw, attempt_id)
    request_binding = io.binding(request_raw)
    _need(receipt["files"].get("observation/request.json") == request_binding,
          "hosted_runner_receipt_request_binding")
    io.write_new(OUTPUT / "request.json", request_raw)
    summary["request"] = request_binding
    io.copy_private_tree(INPUT / "observation/capture", OUTPUT / "capture", inventory)
    summary["capture"] = capture_binding = _capture_binding()
    _need(capture_binding == inventory["capture.json"], "hosted_runner_capture_binding")
    original_result_raw = io.read_regular(INPUT / "observation/commands/acquisition.result.json", CONTROL_BYTES, private=True)
    _need(receipt["files"].get("observation/commands/acquisition.result.json") == io.binding(original_result_raw),
          "hosted_runner_acquisition_result_binding")
    original_result = _canonical_json(original_result_raw)
    summary["acquisition_returncode"] = original_result.get("returncode")
    results = [_adapter("check-capture", "capture-check-" + str(number),
                        request_sha256=request_binding["sha256"], capture_sha256=capture_binding["sha256"])
               for number in (1, 2)]
    _need(all(command_succeeded(item) for item in results), "hosted_runner_capture_check_failed")
    reports = [io.read_regular(OUTPUT / ("capture-check-" + str(number) + ".json"), CONTROL_BYTES, private=True)
               for number in (1, 2)]
    decoded = []
    for number, raw in enumerate(reports, 1):
        decoded.append(_canonical_json(raw))
        summary["reports"]["capture-check-" + str(number)] = io.binding(raw)
    _need(reports[0] == reports[1], "hosted_runner_capture_reports_differ")
    summary["canonical_reports_byte_identical"] = True
    _need(command_succeeded(original_result) and all(
        complete_report(report, attempt_id, request_binding["sha256"], capture_binding["sha256"])
        for report in decoded
    ), "hosted_runner_observation_incomplete")
    summary.update({"observation_complete": True, "status": "completed", **{name: True for name in NARROW_FLAGS}})


def _failure_code(error):
    code = getattr(error, "code", "")
    return code if type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,119}", code) else "hosted_runner_failed"


def run_phase(phase, environment):
    summary = {
        "record_type": "required_gate_idempotence_entry_stop_hosted_" + ("acquisition" if phase == "acquire" else "verification") + "_v0",
        "profile": PROFILE, "phase": phase, "context": None, "attempt_id": None,
        "status": "incomplete", "failure": None, "observation_complete": False,
        "request": None, "capture": None, "reports": {},
        "qualifications": {"task_guard": None, "hardware": None},
        "qualification_commands_completed": False, "qualification_preconditions_verified": False,
        "canonical_reports_byte_identical": False, "acquisition_returncode": None,
        "acquisition_command_invoked": False,
        **{name: False for name in NARROW_FLAGS},
        "host_environment_qualified": False, "actual_reference_claimed": False,
        "production_gate_eligible": False, "post_entry_continuation_performed": False,
        "metric_pass": None, "authority_effect": "none",
    }
    try:
        _need(phase in {"acquire", "verify"}, "hosted_runner_phase")
        fd, chain = io._pin_directory(OUTPUT)
        try:
            info = os.fstat(fd)
            _need(stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid()
                  and not os.listdir(fd), "hosted_runner_output_directory")
            io._check_chain(chain)
        finally:
            io._close_chain(chain)
        context = validate_context(environment, phase)
        summary["context"] = context
        summary["attempt_id"] = derive_attempt_id(context)
        io.write_new(OUTPUT / "context.json", io.canonical(context))
        _mkdir_private(OUTPUT / "commands")
        validate_runtime(environment)
        (acquire if phase == "acquire" else verify)(context, summary)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        summary["failure"] = _failure_code(error)
    name = "acquisition-summary.json" if phase == "acquire" else "verification-summary.json"
    raw = io.canonical(summary)
    try:
        io.write_new(OUTPUT / name, raw)
    except (OSError, ValueError):
        sys.stderr.write("hosted_runner_summary_preservation_failed\n")
        return 1
    sys.stdout.buffer.write(raw)
    return 0 if summary["observation_complete"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("acquire", "verify"))
    args = parser.parse_args(argv)
    os.umask(0o077)
    return run_phase(args.phase, os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
