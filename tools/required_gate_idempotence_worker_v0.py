#!/usr/bin/env python3
"""One bounded sanitizer application, entered only by the acquisition collector.

The collector supplies sealed descriptors.  Selected modules are evaluated only
after the Linux compute-only syscall filter has been installed.  This worker
does not discover repository files, calibration, credentials, or dependencies.
"""
from __future__ import annotations

import argparse
import base64
import collections.abc
import ctypes
import dataclasses
import datetime
import enum
import errno
import fcntl
import hashlib
import json
import logging
import math
import os
import pathlib
import platform
import resource
import statistics
import sys
import types
import typing
import unicodedata

CPU_SECONDS = 2
ADDRESS_SPACE_BYTES = 256 * 1024 * 1024
INPUT_LIMIT = 4096
SOURCE_LIMIT = 512 * 1024
REQUEST_LIMIT = 3 * 1024 * 1024
OUTPUT_LIMIT = 4096
STDOUT_LIMIT = 20 * 1024
# Linux UAPI values, including Python builds compiled against older headers.
F_GET_SEALS = 1034
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
    "seccomp_mode": 2, "rlimit_cpu_seconds": CPU_SECONDS,
    "rlimit_as_bytes": ADDRESS_SPACE_BYTES, "rlimit_core_bytes": 0,
    "rlimit_fsize_bytes": 0, "filesystem_open_syscalls": "denied",
    "network_syscalls": "denied", "process_creation_syscalls": "denied",
}


class WorkerError(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise WorkerError(code)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def strict(raw: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in items:
            need(key not in result, "json_duplicate_key")
            result[key] = value
        return result

    def number(text: str) -> float:
        value = float(text)
        need(math.isfinite(value), "json_nonfinite")
        return value

    def constant(_: str) -> typing.NoReturn:
        raise WorkerError("json_nonfinite")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=constant)


def read_sealed(fd: int, limit: int) -> bytes:
    need(type(fd) is int and fd > 2, "descriptor_invalid")
    need(fcntl.fcntl(fd, F_GET_SEALS) == SEALS, "descriptor_unsealed")
    info = os.fstat(fd)
    need(info.st_size <= limit, "descriptor_size_limit")
    os.lseek(fd, 0, os.SEEK_SET)
    result = bytearray()
    while True:
        block = os.read(fd, min(65536, limit + 1 - len(result)))
        if not block:
            break
        result.extend(block)
        need(len(result) <= limit, "descriptor_size_limit")
    need(len(result) == info.st_size, "descriptor_read_incomplete")
    return bytes(result)


def install_limits() -> None:
    need(sys.platform == "linux" and platform.machine() == "x86_64",
         "sandbox_platform_unsupported")
    need(sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 11) and
         unicodedata.unidata_version == "14.0.0", "worker_runtime_unsupported")
    for kind, limit in ((resource.RLIMIT_CPU, CPU_SECONDS),
                        (resource.RLIMIT_AS, ADDRESS_SPACE_BYTES),
                        (resource.RLIMIT_CORE, 0), (resource.RLIMIT_FSIZE, 0)):
        resource.setrlimit(kind, (limit, limit))
        need(resource.getrlimit(kind) == (limit, limit), "sandbox_rlimit_mismatch")


def install_filter(input_fd: int) -> None:
    """Deny unknown syscalls and all ambient I/O before selected source executes.

    The architecture comparison precedes the syscall table; x32 numbers cannot
    match its native x86_64 entries.  Read is limited to the sealed payload and
    writes to the two collector pipes.  No file-open, network, process creation,
    exec, ptrace, io_uring, descriptor duplication or resource-limit call passes.
    """
    class Instruction(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Instruction))]

    # BPF_LD|BPF_W|BPF_ABS, BPF_JMP|BPF_JEQ|BPF_K, BPF_RET|BPF_K.
    load, equal, ret = 0x20, 0x15, 0x06
    allow, deny, kill = 0x7FFF0000, 0x00050000 | errno.EPERM, 0x80000000
    instructions = [
        (load, 0, 0, 4), (equal, 1, 0, 0xC000003E), (ret, 0, 0, kill),
        (load, 0, 0, 0),
        # read(fd, ...) is restricted to the pre-opened sealed input descriptor.
        (equal, 0, 4, 0), (load, 0, 0, 16),
        (equal, 0, 1, input_fd), (ret, 0, 0, allow), (ret, 0, 0, deny),
        # write(fd, ...) is restricted to stdout/stderr.
        (equal, 0, 5, 1), (load, 0, 0, 16),
        (equal, 1, 0, 1), (equal, 0, 1, 2),
        (ret, 0, 0, allow), (ret, 0, 0, deny),
    ]
    # Pure computation, memory management, signal handling and process-local
    # observations. fstat/lseek are limited to existing descriptors.
    # They cannot open a new capability or duplicate an FD: fcntl is excluded
    # after prefilter validation; fstat/lseek alone do not read file contents.
    for syscall in (3, 5, 8, 9, 10, 11, 12, 13, 14, 15, 24, 28, 39,
                    60, 96, 186, 202, 218, 228, 231, 273):
        instructions.extend(((equal, 0, 1, syscall), (ret, 0, 0, allow)))
    instructions.append((ret, 0, 0, deny))
    array = (Instruction * len(instructions))(*(Instruction(*i) for i in instructions))
    program = Program(len(instructions), array)
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    need(prctl(38, 1, 0, 0, 0) == 0, "sandbox_no_new_privs_failed")
    need(prctl(39, 0, 0, 0, 0) == 1, "sandbox_no_new_privs_unconfirmed")
    need(prctl(22, 2, ctypes.byref(program), 0, 0) == 0, "sandbox_filter_failed")


def snapshot_domain(value: object) -> bool:
    if type(value) is dict:
        return all(type(key) is str and (snapshot_domain(item) if type(item) is dict
                   else type(item) in (int, float) and math.isfinite(item))
                   for key, item in value.items())
    return False


def run(request_fd: int, input_fd: int) -> dict:
    install_limits()
    need(request_fd != input_fd, "descriptor_roles_overlap")
    request = strict(read_sealed(request_fd, REQUEST_LIMIT))
    os.close(request_fd)
    need(type(request) is dict and set(request) == {
        "record_type", "application_id", "configuration", "input_sha256",
        "input_size_bytes", "sources"}, "request_shape")
    need(request["record_type"] == "required_gate_idempotence_worker_request_v0", "request_type")
    need(type(request["application_id"]) is str and request["application_id"] in {
        f"idem-{case:02d}.{phase}" for case in range(1, 13) for phase in ("first", "second")},
        "application_id_invalid")
    need(canonical(request["configuration"]) == canonical(CONFIGURATION), "configuration_mismatch")
    need(type(request["input_size_bytes"]) is int and 0 <= request["input_size_bytes"] <= INPUT_LIMIT,
         "input_size_invalid")
    need(type(request["input_sha256"]) is str and len(request["input_sha256"]) == 64,
         "input_digest_invalid")
    sources = request["sources"]
    need(type(sources) is dict and set(sources) == set(SOURCE_PATHS), "source_roster")
    compiled = {}
    for path in SOURCE_PATHS:
        need(type(sources[path]) is str, "source_encoding")
        raw = base64.b64decode(sources[path], validate=True)
        need(0 < len(raw) <= SOURCE_LIMIT, "source_size_limit")
        compiled[path] = compile(raw.decode("utf-8"), "/selected/" + path, "exec", dont_inherit=True)
    # Validate the input descriptor before the filter (fcntl itself is denied
    # afterwards), but read the payload only inside the compute boundary.
    need(type(input_fd) is int and input_fd > 2, "descriptor_invalid")
    need(fcntl.fcntl(input_fd, F_GET_SEALS) == SEALS, "descriptor_unsealed")
    need(os.fstat(input_fd).st_size == request["input_size_bytes"], "input_size_mismatch")
    os.lseek(input_fd, 0, os.SEEK_SET)
    # Drop all capabilities other than the input and output pipes.  The worker
    # and interpreter descriptors are supplied only for immutable launch.
    for filename in os.listdir("/proc/self/fd"):
        descriptor = int(filename)
        if descriptor > 2 and descriptor != input_fd:
            try:
                os.close(descriptor)
            except OSError:
                pass
    install_filter(input_fd)
    payload = bytearray()
    while True:
        chunk = os.read(input_fd, INPUT_LIMIT + 1 - len(payload))
        if not chunk:
            break
        payload.extend(chunk)
        need(len(payload) <= INPUT_LIMIT, "input_size_limit")
    os.close(input_fd)
    raw_input = bytes(payload)
    need(len(raw_input) == request["input_size_bytes"] and
         hashlib.sha256(raw_input).hexdigest() == request["input_sha256"], "input_binding")
    value = strict(raw_input)
    need(type(value) is dict, "input_domain")
    # Synthetic package parents carry no repository initialization or file path
    # search capability.  Each pinned module is evaluated exactly once.
    for name in ("PULSE_safe_pack_v0", "PULSE_safe_pack_v0.epf"):
        module = types.ModuleType(name)
        module.__path__ = []
        module.__package__ = name
        sys.modules[name] = module
    for path in SOURCE_PATHS:
        name = path[:-3].replace("/", ".")
        module = types.ModuleType(name)
        module.__package__ = name.rpartition(".")[0]
        module.__file__ = "/selected/" + path
        sys.modules[name] = module
        exec(compiled[path], module.__dict__)
    operator = sys.modules["PULSE_safe_pack_v0.epf.epf_hazard_adapter"].sanitize_snapshot_for_log
    snapshot, metadata = operator(value, **CONFIGURATION)
    need(snapshot_domain(snapshot), "snapshot_domain")
    need(type(metadata) is dict, "metadata_domain")
    snapshot_raw, metadata_raw = canonical(snapshot), canonical(metadata)
    need(len(snapshot_raw) <= OUTPUT_LIMIT and len(metadata_raw) <= OUTPUT_LIMIT, "output_size_limit")
    return {"record_type": "required_gate_idempotence_worker_result_v0",
            "application_id": request["application_id"],
            "configuration_sha256": hashlib.sha256(canonical(CONFIGURATION)).hexdigest(),
            "input_read_sha256": hashlib.sha256(raw_input).hexdigest(),
            "input_read_size_bytes": len(raw_input), "input_read_complete": True,
            "snapshot_base64": base64.b64encode(snapshot_raw).decode("ascii"),
            "metadata_base64": base64.b64encode(metadata_raw).decode("ascii"),
            "sandbox": dict(SANDBOX)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-fd", type=int, required=True)
    parser.add_argument("--input-fd", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        output = canonical(run(args.request_fd, args.input_fd))
        need(len(output) <= STDOUT_LIMIT, "response_size_limit")
        view = memoryview(output)
        while view:
            count = os.write(1, view)
            need(count > 0, "response_write_failed")
            view = view[count:]
        return 0
    except BaseException as exc:
        code = str(exc) if isinstance(exc, WorkerError) else "worker_execution_failed"
        try:
            os.write(2, ("idempotence_worker_rejected: " + code + "\n").encode("ascii"))
        except BaseException:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
