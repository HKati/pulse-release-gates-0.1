#!/usr/bin/env python3
"""Bounded child-process primitive for the selected idempotence acquisition.

This module is not an acquisition authorization or a runtime-closure verifier.
The public collector must qualify selected source/runtime inputs before calling
it. Tests may pass explicitly synthetic source bytes through this library API.
"""
from __future__ import annotations

import base64
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import selectors
import signal
import stat
import subprocess
import sys
import time
import unicodedata
from contextlib import ExitStack
from typing import Callable

WALL_SECONDS = 5.0
STDOUT_LIMIT = 20 * 1024
STDERR_LIMIT = 4096
INPUT_LIMIT = 4096
SOURCE_LIMIT = 512 * 1024
REQUEST_LIMIT = 3 * 1024 * 1024
INTERPRETER_LIMIT = 128 * 1024 * 1024
F_ADD_SEALS, F_GET_SEALS = 1033, 1034
SEALS = 0x0008 | 0x0004 | 0x0002 | 0x0001
SOURCE_PATHS = (
    "PULSE_safe_pack_v0/epf/epf_hazard_features.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_forecast.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_field_spec.py",
    "PULSE_safe_pack_v0/epf/epf_hazard_adapter.py",
)
CONFIGURATION = {"max_depth": 2, "max_items": 3, "allowed_prefixes": ["metrics"],
                 "deny_keys": ["metrics.pii", "metrics.secret"]}
SANDBOX = {
    "profile": "linux_x86_64_seccomp_compute_v0", "no_new_privs": True,
    "seccomp_mode": 2, "rlimit_cpu_seconds": 2, "rlimit_as_bytes": 256 * 1024 * 1024,
    "rlimit_core_bytes": 0, "rlimit_fsize_bytes": 0,
    "filesystem_open_syscalls": "denied", "network_syscalls": "denied",
    "process_creation_syscalls": "denied",
}


class ProcessError(ValueError):
    """Stable prelaunch rejection; no operator child was launched."""


def need(condition: bool, code: str) -> None:
    if not condition:
        raise ProcessError(code)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def strict(raw: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in items:
            need(key not in result, "worker_response_duplicate_key")
            result[key] = value
        return result

    def number(text: str) -> float:
        value = float(text)
        need(math.isfinite(value), "worker_response_nonfinite")
        return value

    def constant(_: str) -> object:
        raise ProcessError("worker_response_nonfinite")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=constant)


def sealed_buffer(role: str, raw: bytes) -> int:
    need(type(raw) is bytes, "sealed_input_type")
    fd = os.memfd_create("pulse-idempotence-" + role, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            need(count > 0, "sealed_write_failed")
            view = view[count:]
        fcntl.fcntl(fd, F_ADD_SEALS, SEALS)
        need(fcntl.fcntl(fd, F_GET_SEALS) == SEALS, "sealed_state_mismatch")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_descriptor(fd: int, limit: int) -> bytes:
    info = os.fstat(fd)
    need(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, "interpreter_file_invalid")
    os.lseek(fd, 0, os.SEEK_SET)
    result = bytearray()
    while True:
        chunk = os.read(fd, min(65536, limit + 1 - len(result)))
        if not chunk:
            break
        result.extend(chunk)
        need(len(result) <= limit, "interpreter_size_limit")
    need(len(result) == info.st_size, "interpreter_read_incomplete")
    after = os.fstat(fd)
    attributes = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    need(all(getattr(info, key) == getattr(after, key) for key in attributes),
         "interpreter_changed_during_read")
    return bytes(result)


def _snapshot_domain(value: object) -> bool:
    return type(value) is dict and all(
        type(key) is str and (_snapshot_domain(item) if type(item) is dict else
                            type(item) in (int, float) and math.isfinite(item))
        for key, item in value.items())


def _bootstrap_environment(interpreter_path: Path) -> dict[str, str]:
    """Supply one derived loader directory without inheriting loader settings.

    A sealed executable has no installation-directory $ORIGIN. Some CPython
    distributions consequently need their sibling lib directory to find
    libpython before the worker can start. This explicit host dependency is
    not pinned by the executable digest and does not establish runtime closure.
    """
    environment = {"LC_ALL": "C", "TZ": "UTC"}
    library_path = interpreter_path.parent.parent / "lib"
    try:
        info = library_path.lstat()
    except FileNotFoundError:
        return environment
    need(stat.S_ISDIR(info.st_mode), "interpreter_library_directory_invalid")
    value = str(library_path)
    need(library_path.is_absolute() and not any(character in value for character in (":", ";", "$", "\x00")),
         "interpreter_library_path_invalid")
    environment["LD_LIBRARY_PATH"] = value
    return environment


def _decode_report(raw: bytes, application_id: str, input_bytes: bytes) -> tuple[dict, bytes, bytes]:
    report = strict(raw)
    need(type(report) is dict and set(report) == {
        "record_type", "application_id", "configuration_sha256", "input_read_sha256",
        "input_read_size_bytes", "input_read_complete", "snapshot_base64", "metadata_base64",
        "sandbox"}, "worker_response_shape")
    need(report["record_type"] == "required_gate_idempotence_worker_result_v0" and
         report["application_id"] == application_id, "worker_response_identity")
    need(report["configuration_sha256"] == sha(canonical(CONFIGURATION)), "worker_configuration_binding")
    need(report["input_read_sha256"] == sha(input_bytes) and
         type(report["input_read_size_bytes"]) is int and report["input_read_size_bytes"] == len(input_bytes)
         and report["input_read_complete"] is True, "worker_read_binding")
    need(canonical(report["sandbox"]) == canonical(SANDBOX), "worker_sandbox_report")
    need(type(report["snapshot_base64"]) is str and type(report["metadata_base64"]) is str,
         "worker_output_encoding")
    snapshot = base64.b64decode(report["snapshot_base64"], validate=True)
    metadata = base64.b64decode(report["metadata_base64"], validate=True)
    need(len(snapshot) <= 4096 and len(metadata) <= 4096, "worker_output_limit")
    snapshot_value, metadata_value = strict(snapshot), strict(metadata)
    need(_snapshot_domain(snapshot_value) and canonical(snapshot_value) == snapshot, "worker_snapshot_domain")
    need(type(metadata_value) is dict and canonical(metadata_value) == metadata, "worker_metadata_domain")
    need(canonical(report) == raw, "worker_response_noncanonical")
    return report, snapshot, metadata


def run_worker(*, worker_bytes: bytes, source_bytes: dict[str, bytes], input_bytes: bytes,
               configuration: dict, application_id: str, interpreter: Path,
               expected_interpreter_sha256: str, deadline: float,
               sink: Callable[[str, bytes], None] | None = None) -> dict:
    """Run one fresh child and retain its bounded output on every launched path.

    The deadline uses time.monotonic().  The caller supplies its suite deadline;
    this function applies the smaller of that deadline and five seconds.  Sink
    receives permitted raw stream bytes before parsing, including failed runs.
    It must durably preserve them and must never launch additional workers.
    """
    need(sys.platform == "linux" and platform.machine() == "x86_64" and hasattr(os, "memfd_create"),
         "process_platform_unsupported")
    need(sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 11) and
         unicodedata.unidata_version == "14.0.0", "process_runtime_unsupported")
    need(type(worker_bytes) is bytes and 0 < len(worker_bytes) <= SOURCE_LIMIT, "worker_source_limit")
    need(type(source_bytes) is dict and set(source_bytes) == set(SOURCE_PATHS) and all(
        type(raw) is bytes and 0 < len(raw) <= SOURCE_LIMIT for raw in source_bytes.values()), "source_roster")
    need(type(input_bytes) is bytes and 0 < len(input_bytes) <= INPUT_LIMIT, "input_size_limit")
    need(canonical(configuration) == canonical(CONFIGURATION), "configuration_mismatch")
    need(type(application_id) is str and application_id in {
        f"idem-{case:02d}.{phase}" for case in range(1, 13) for phase in ("first", "second")},
        "application_id_invalid")
    need(type(expected_interpreter_sha256) is str and len(expected_interpreter_sha256) == 64 and
         all(char in "0123456789abcdef" for char in expected_interpreter_sha256), "interpreter_digest_invalid")
    need(type(deadline) in (int, float) and math.isfinite(deadline) and deadline > time.monotonic(),
         "suite_deadline_exhausted")
    need(sink is None or callable(sink), "sink_invalid")
    interpreter_path = Path(interpreter).resolve(strict=True)
    need(interpreter_path.is_absolute(), "interpreter_path_invalid")
    environment = _bootstrap_environment(interpreter_path)
    request = canonical({"record_type": "required_gate_idempotence_worker_request_v0",
                         "application_id": application_id, "configuration": CONFIGURATION,
                         "input_sha256": sha(input_bytes), "input_size_bytes": len(input_bytes),
                         "sources": {path: base64.b64encode(source_bytes[path]).decode("ascii")
                                     for path in sorted(source_bytes)}})
    need(len(request) <= REQUEST_LIMIT, "request_size_limit")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": STDOUT_LIMIT, "stderr": STDERR_LIMIT}
    process = None
    failure = None
    result = {"process_id": None, "started_utc": None, "completed_utc": None,
              "started_monotonic_ns": None, "completed_monotonic_ns": None,
              "exit_code": None, "status": "incomplete", "error_code": None,
              "input_read_sha256": None, "input_read_size_bytes": None,
              "input_read_complete": False, "snapshot_bytes": b"", "metadata_bytes": b"",
              "stderr_bytes": b"", "stdout_bytes": b"", "worker_report": None}
    with ExitStack() as stack:
        selected_fd = os.open(interpreter_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        stack.callback(os.close, selected_fd)
        interpreter_raw = _read_descriptor(selected_fd, INTERPRETER_LIMIT)
        need(sha(interpreter_raw) == expected_interpreter_sha256, "interpreter_digest_mismatch")
        executable_fd = sealed_buffer("interpreter", interpreter_raw)
        stack.callback(os.close, executable_fd)
        # Execute immutable selected bytes, preserving the original path as
        # argv[0] for CPython prefix discovery. Shared libraries/stdlib remain
        # runtime dependencies; this is not a complete runtime closure.
        descriptors = {}
        for role, raw in (("worker", worker_bytes), ("request", request), ("input", input_bytes)):
            fd = sealed_buffer(role, raw)
            stack.callback(os.close, fd)
            descriptors[role] = fd
        result["started_utc"] = utc_now()
        result["started_monotonic_ns"] = time.monotonic_ns()
        worker_deadline = min(float(deadline), time.monotonic() + WALL_SECONDS)
        # Capturing the interpreter and sealing all inputs can exhaust the
        # caller's suite budget. Never launch a child after that preparation.
        need(time.monotonic() < worker_deadline, "suite_deadline_exhausted")
        try:
            process = subprocess.Popen(
                [str(interpreter_path), "-I", "-S", "-B", "/proc/self/fd/" + str(descriptors["worker"]),
                 "--request-fd", str(descriptors["request"]), "--input-fd", str(descriptors["input"])],
                executable="/proc/self/fd/" + str(executable_fd),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=environment, cwd="/", close_fds=True,
                pass_fds=tuple(descriptors.values()) + (executable_fd,), shell=False, start_new_session=True)
            result["process_id"] = process.pid
            with selectors.DefaultSelector() as selector:
                for name in buffers:
                    pipe = getattr(process, name)
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, name)
                while selector.get_map():
                    remaining = worker_deadline - time.monotonic()
                    if remaining <= 0:
                        failure = "worker_wall_timeout"
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        name = key.data
                        available = limits[name] - len(buffers[name])
                        block = os.read(key.fileobj.fileno(), min(65536, available + 1))
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        retained = block[:available]
                        buffers[name].extend(retained)
                        if retained and sink is not None:
                            sink(name, retained)
                        if len(block) > available:
                            failure = "worker_" + name + "_limit"
                            break
                    if failure:
                        break
                if failure is None:
                    # Leave the exited leader unreaped until its process group
                    # is killed.  Otherwise its PID could be reused between
                    # wait() and killpg(), targeting an unrelated new group.
                    while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                        remaining = worker_deadline - time.monotonic()
                        if remaining <= 0:
                            failure = "worker_wall_timeout"
                            break
                        time.sleep(min(remaining, 0.005))
        except BaseException as exc:
            failure = "worker_launch_failed" if process is None else "worker_capture_failed"
            if isinstance(exc, ProcessError):
                failure = str(exc)
        finally:
            if process is not None:
                # The owned leader is still unreaped, so its PID cannot have
                # been recycled into an unrelated process group.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    failure = "worker_reap_failed"
                result["exit_code"] = process.returncode
                for name in buffers:
                    pipe = getattr(process, name)
                    if pipe is not None:
                        # Retain bounded bytes already produced on either
                        # stream, including when another stream caused failure.
                        # The child is gone; no further producer can extend it.
                        try:
                            os.set_blocking(pipe.fileno(), False)
                        except OSError:
                            failure = "worker_capture_failed"
                        while True:
                            available = limits[name] - len(buffers[name])
                            try:
                                block = os.read(pipe.fileno(), min(65536, available + 1))
                            except (BlockingIOError, OSError):
                                break
                            if not block:
                                break
                            retained = block[:available]
                            buffers[name].extend(retained)
                            if retained and sink is not None:
                                try:
                                    sink(name, retained)
                                except BaseException:
                                    failure = "worker_capture_failed"
                            if len(block) > available:
                                if failure is None:
                                    failure = "worker_" + name + "_limit"
                                break
                        pipe.close()
            result["completed_monotonic_ns"] = time.monotonic_ns()
            result["completed_utc"] = utc_now()
            result["stdout_bytes"] = bytes(buffers["stdout"])
            result["stderr_bytes"] = bytes(buffers["stderr"])
    if failure is None and result["exit_code"] != 0:
        failure = "worker_nonzero_exit"
    if failure is None:
        try:
            report, snapshot, metadata = _decode_report(result["stdout_bytes"], application_id, input_bytes)
            result.update(worker_report=report, snapshot_bytes=snapshot, metadata_bytes=metadata,
                          input_read_sha256=report["input_read_sha256"],
                          input_read_size_bytes=report["input_read_size_bytes"], input_read_complete=True,
                          status="complete")
        except (ProcessError, ValueError, TypeError, UnicodeError, KeyError, RecursionError):
            failure = "worker_response_invalid"
    result["error_code"] = failure
    return result
