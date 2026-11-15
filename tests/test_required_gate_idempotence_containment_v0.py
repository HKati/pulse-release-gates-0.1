#!/usr/bin/env python3
"""Synthetic containment regression; no selected runtime or operator executes.

Compiler tests use inert capsule bytes. Parent-process tests substitute an
authored host child at the Popen boundary; they never invoke bubblewrap or the
selected capsule. Only invalid-argument entry checks and a separate fixed-filter
child execute native test code. Neither establishes namespace containment.
"""
from __future__ import annotations

import base64
import copy
from dataclasses import FrozenInstanceError
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import struct
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SELF = "tests/test_required_gate_idempotence_containment_v0.py"
TOOL = ROOT / "tools/required_gate_idempotence_containment_v0.py"
REAL_POPEN = subprocess.Popen
CC_FLAGS = (
    "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-ffreestanding",
    "-fno-builtin", "-fno-pie", "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
    "-nostdlib", "-static", "-no-pie", "-Wl,--build-id=none", "-Wl,-z,noexecstack",
)


def module(name, relative):
    if name not in sys.modules:
        tools = str(ROOT / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        assert spec is not None and spec.loader is not None
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[name] = loaded
        spec.loader.exec_module(loaded)
    return sys.modules[name]


def subject():
    return module("required_gate_idempotence_containment_v0", "tools/required_gate_idempotence_containment_v0.py")


def examples():
    return module("containment_bootstrap_examples", "tests/test_required_gate_idempotence_bootstrap_v0.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bound(raw):
    return {"sha256": digest(raw), "size_bytes": len(raw)}


def boundaries(record):
    false = (
        "execution_ready", "execution_authorized", "runtime_closure_verified",
        "restored_bootstrap_qualified", "containment_enforced",
        "production_gate_eligible", "actual_reference_claimed",
        "host_environment_qualified", "python_import_closure_verified",
        "loader_resolution_verified", "observed_acquisition_supported",
        "runtime_execution_authenticated", "bootstrap_execution_observed",
    )
    for key in false:
        assert record[key] is False, key
    assert record["authority_effect"] == "none"
    assert record["metric_pass"] is None
    assert record["diagnostic_only"] is True
    assert type(record["operator_applications"]) is int and record["operator_applications"] == 0
    assert type(record["model_calls"]) is int and record["model_calls"] == 0


@pytest.fixture(scope="module")
def entry_binary(tmp_path_factory):
    directory = tmp_path_factory.mktemp("containment-entry")
    compiler = shutil.which("cc")
    assert compiler is not None, "C compiler required for fixed-entry regression"
    path = directory / "entry"
    result = subprocess.run(
        [compiler, *CC_FLAGS, str(ROOT / "tools/required_gate_idempotence_containment_entry_v0.c"), "-o", str(path)],
        capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout == b""
    return path


@pytest.fixture(scope="module")
def fixture(tmp_path_factory, entry_binary):
    original = examples().Example().seal(tmp_path_factory.mktemp("containment-source") / "source")
    prepared = subject().bootstrap.prepare_bootstrap(**original.arguments())
    entry = entry_binary.read_bytes()
    launcher = original.runtime.payload[original.runtime.interpreter]
    return SimpleNamespace(original=original, bootstrap=prepared, entry=entry, launcher=launcher)


def selection(fixture, *, phase="worker"):
    policy = subject().policy
    return {
        "record_type": "required_gate_idempotence_containment_selection_v0",
        "profile": "linux_x86_64_bubblewrap_bootstrap_v0", "record_status": "example",
        "bootstrap_plan_sha256": digest(fixture.bootstrap.plan_bytes), "phase": phase,
        "launcher": {"path": "/selected-host/bwrap", **bound(fixture.launcher)},
        "entry_shim": bound(fixture.entry),
        "entry_source": {"path": policy.ENTRY_SOURCE_PATH, **bound((ROOT / policy.ENTRY_SOURCE_PATH).read_bytes())},
        "policy_source": {"path": policy.POLICY_SOURCE_PATH, **bound((ROOT / policy.POLICY_SOURCE_PATH).read_bytes())},
        "execution_ready": False, "execution_authorized": False, "runtime_closure_verified": False,
        "restored_bootstrap_qualified": False, "containment_enforced": False,
        "production_gate_eligible": False, "authority_effect": "none",
    }


def arguments(fixture, *, value=None, phase="worker"):
    raw = encoded(selection(fixture, phase=phase) if value is None else value)
    return {
        "bootstrap_prepared": fixture.bootstrap,
        "expected_bootstrap_plan_sha256": digest(fixture.bootstrap.plan_bytes),
        "selection_bytes": raw, "expected_selection_sha256": digest(raw),
        "launcher_bytes": fixture.launcher, "entry_bytes": fixture.entry,
    }


@pytest.fixture(scope="module")
def valid(fixture):
    return subject().prepare_containment(**arguments(fixture))


def contract(prepared):
    return json.loads(dict(prepared.contents)[subject().bootstrap.CONTRACT_VIRTUAL])


def authored_report(prepared):
    selected = contract(prepared)
    probe = subject().checker.probe
    phase = json.loads(prepared.request_bytes)["phase"]
    names = set(selected["phases"][phase]) | {"hashlib", "json", "unicodedata"}
    names.update(".".join(name.split(".")[:index]) for name in tuple(names)
                 for index in range(1, len(name.split("."))))
    providers = {row["name"]: row for row in selected["modules"]}
    rows = []
    for name in sorted(names):
        row = copy.deepcopy(providers[name])
        row.update(observed_origin=row["path"] if row["path"] is not None else
                   "built-in" if row["kind"] == "builtin" else "frozen", present_before_phase=False)
        rows.append(row)
    checks = {"canonical_json": True, "sha256": True, "unicode": True}
    if phase == "collector":
        checks["draft202012_validator"] = True
    return {
        "record_type": "required_gate_idempotence_bootstrap_diagnostic_v0",
        "profile": "restored_bootstrap_plan_v0", "status": "completed", "phase": phase,
        **{key: selected[key] for key in probe.HASH_FIELDS},
        "startup": {
            "python_implementation": "CPython", "python_version": "3.11.16",
            "architecture": "x86_64", "os_name": "Linux",
            "prefix": "/runtime/python", "exec_prefix": "/runtime/python",
            "base_prefix": "/runtime/python", "base_exec_prefix": "/runtime/python",
            "executable": "/runtime/python/bin/python3.11", "working_directory": "/empty",
            "initial_sys_path": ["/runtime/python/lib/python311.zip", "/runtime/python/lib/python3.11",
                                 "/runtime/python/lib/python3.11/lib-dynload"],
            "environment": {"LC_ALL": "C", "TZ": "UTC"},
            "flags": {"isolated": 1, "ignore_environment": 1, "no_site": 1,
                      "no_user_site": 1, "dont_write_bytecode": 1, "safe_path": True},
            "unicode_version": "14.0.0",
            "probe_sys_path": ["/runtime/python/lib/python3.11",
                              "/runtime/python/lib/python3.11/lib-dynload",
                              "/runtime/python/lib/python3.11/site-packages", "/runtime/repository/tools"],
        },
        "module_observations": rows, "resource_observations": copy.deepcopy(selected["resources"]),
        "finite_checks": checks, "post_phase_sys_path": list(probe.SEARCH_ROOTS), **probe.BOUNDARY,
    }


def authored_receipt(prepared, stdout, stderr=b"", *, error=None):
    request = json.loads(prepared.request_bytes)
    return {
        "record_type": "required_gate_idempotence_containment_receipt_v0",
        "profile": subject().PROFILE, "status": "completed" if error is None else "incomplete",
        "request_sha256": digest(prepared.request_bytes), "phase": request["phase"],
        "streams": {"stdout": bound(stdout), "stderr": bound(stderr)},
        "process": {"pid": 12345, "exit_code": 0 if error is None else 1,
                    "started_monotonic_ns": 1_000_000_000, "completed_monotonic_ns": 2_000_000_000},
        "error_code": error, **subject().BOUNDARY,
    }


def verify(prepared, receipt, stdout, stderr=b""):
    raw = encoded(receipt)
    return subject().verify_attempt(prepared, receipt_bytes=raw, expected_receipt_sha256=digest(raw),
                                    stdout_bytes=stdout, stderr_bytes=stderr)


def fake_backend(stdout, stderr=b"", *, error=None, mutate=None):
    def run(prepared, sink):
        if stdout:
            sink("stdout", stdout)
        if stderr:
            sink("stderr", stderr)
        if mutate is not None:
            mutate()
        process = {"pid": 12345, "exit_code": 0 if error is None else 1,
                   "started_monotonic_ns": 1_000_000_000, "completed_monotonic_ns": 2_000_000_000}
        return process, error, {"stdout": stdout, "stderr": stderr}
    return run


def test_compiled_entry_is_static_and_has_no_interpreter_dependency(fixture):
    subject().validate_entry(fixture.entry)
    kind, entry, rows = subject()._elf_header(fixture.entry)
    assert kind == 2 and entry > 0
    assert all(row[0] not in {2, 3, 5} for row in rows)
    assert len([row for row in rows if row[0] == 0x6474E551 and not row[1] & 1]) == 1


@pytest.mark.parametrize("argv", [[], [""], ["operator"], ["worker", "extra"]])
def test_static_entry_rejects_invalid_arguments_before_any_loader_execution(entry_binary, argv):
    result = subprocess.run([str(entry_binary), *argv], capture_output=True, timeout=5)
    assert result.returncode == 64
    assert result.stdout == b""
    assert result.stderr == b"containment_entry_phase_invalid\n"


@pytest.mark.parametrize("change", ["truncated", "class", "endian", "architecture", "type", "ph_bounds",
                                     "dynamic", "interpreter", "exec_stack", "missing_stack", "writable_exec",
                                     "segment_bounds", "entry_outside"])
def test_entry_admission_rejects_unsupported_or_inconsistent_elf(fixture, change):
    raw = bytearray(fixture.entry)
    _, _, rows = subject()._elf_header(raw if type(raw) is bytes else bytes(raw))
    phoff = struct.unpack_from("<Q", raw, 32)[0]
    load = next(index for index, row in enumerate(rows) if row[0] == 1 and row[1] & 1)
    stack = next(index for index, row in enumerate(rows) if row[0] == 0x6474E551)
    if change == "truncated":
        raw = raw[:40]
    elif change == "class":
        raw[4] = 1
    elif change == "endian":
        raw[5] = 2
    elif change == "architecture":
        struct.pack_into("<H", raw, 18, 183)
    elif change == "type":
        struct.pack_into("<H", raw, 16, 3)
    elif change == "ph_bounds":
        struct.pack_into("<Q", raw, 32, len(raw))
    elif change in {"dynamic", "interpreter"}:
        struct.pack_into("<I", raw, phoff + 56 * stack, 2 if change == "dynamic" else 3)
    elif change == "exec_stack":
        struct.pack_into("<I", raw, phoff + 56 * stack + 4, 7)
    elif change == "missing_stack":
        struct.pack_into("<I", raw, phoff + 56 * stack, 0)
    elif change == "writable_exec":
        struct.pack_into("<I", raw, phoff + 56 * load + 4, 7)
    elif change == "segment_bounds":
        struct.pack_into("<Q", raw, phoff + 56 * load + 32, len(raw) + 1)
    else:
        struct.pack_into("<Q", raw, 24, 1)
    with pytest.raises(subject().ContainmentError):
        subject().validate_entry(bytes(raw))


@pytest.mark.parametrize("phase", ["worker", "collector"])
def test_prepare_request_is_deterministic_canonical_and_diagnostic(fixture, phase):
    inputs = arguments(fixture, phase=phase)
    first, second = subject().prepare_containment(**inputs), subject().prepare_containment(**inputs)
    assert first.request_bytes == second.request_bytes and first.contents == second.contents
    request = json.loads(first.request_bytes)
    assert encoded(request) == first.request_bytes and request["phase"] == phase
    assert request["launch_policy"]["selected_argv"][-2:] == ["--phase", phase]
    assert request["launch_policy"]["source_binary_equivalence_verified"] is False
    assert request["launch_policy"]["host_launcher_runtime_verified"] is False
    result = subject().verify_request(first, request_bytes=first.request_bytes,
                                      expected_request_sha256=digest(first.request_bytes))
    assert result["boundary_request_verified"] is True
    assert result["attempt_complete"] is False
    for value in (request, result):
        boundaries(value)


@pytest.mark.parametrize("field,value", [
    ("extra", True), ("record_type", "forged"), ("profile", "forged"),
    ("record_status", "observed"), ("phase", "operator"),
    ("bootstrap_plan_sha256", "0" * 64), ("execution_ready", True),
    ("execution_authorized", True), ("runtime_closure_verified", True),
    ("restored_bootstrap_qualified", True), ("containment_enforced", True),
    ("production_gate_eligible", True), ("authority_effect", "release"),
])
def test_selection_is_closed_and_cannot_promote_authority(fixture, field, value):
    chosen = selection(fixture)
    chosen[field] = value
    with pytest.raises(subject().checker.CheckerError):
        subject().prepare_containment(**arguments(fixture, value=chosen))


@pytest.mark.parametrize("field", ["expected_selection_sha256", "expected_bootstrap_plan_sha256"])
def test_independently_selected_hashes_are_required(fixture, field):
    inputs = arguments(fixture)
    inputs[field] = "0" * 64
    with pytest.raises((subject().ContainmentError, subject().checker.CheckerError)):
        subject().prepare_containment(**inputs)


@pytest.mark.parametrize("role", ["launcher", "entry_shim", "entry_source", "policy_source"])
@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("size_bytes", 1)])
def test_all_selected_implementation_byte_bindings_are_checked(fixture, role, field, value):
    chosen = selection(fixture)
    chosen[role][field] = value
    with pytest.raises(subject().ContainmentError):
        subject().prepare_containment(**arguments(fixture, value=chosen))


@pytest.mark.parametrize("role", ["launcher", "entry_shim", "entry_source", "policy_source"])
@pytest.mark.parametrize("change", ["float_size", "boolean_size", "newline_digest"])
def test_descriptor_types_cannot_exploit_json_schema_numeric_or_regex_equivalence(fixture, role, change):
    chosen = selection(fixture)
    if change == "float_size":
        chosen[role]["size_bytes"] = float(chosen[role]["size_bytes"])
    elif change == "boolean_size":
        chosen[role]["size_bytes"] = True
    else:
        chosen[role]["sha256"] += "\n"
    with pytest.raises(subject().checker.CheckerError):
        subject().prepare_containment(**arguments(fixture, value=chosen))


@pytest.mark.parametrize("path", ["/selected-host/../bwrap", "/selected-host/./bwrap", "relative", "/with space/bwrap"])
def test_launcher_path_is_absolute_and_normalization_free(fixture, path):
    chosen = selection(fixture)
    chosen["launcher"]["path"] = path
    raw = encoded(chosen)
    with pytest.raises(subject().checker.CheckerError):
        subject().checker.validate_selection(raw, digest(raw))


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b"[]", b"{} trailing", b""])
def test_selection_parser_rejects_ambiguous_or_invalid_json(raw):
    with pytest.raises(subject().checker.CheckerError):
        subject().checker.validate_selection(raw, digest(raw))


def test_selected_status_can_be_prepared_as_metadata_but_cannot_mismatch_example(fixture):
    chosen = selection(fixture)
    chosen["record_status"] = "selected"
    raw = encoded(chosen)
    accepted = subject().checker.validate_selection(raw, digest(raw))
    assert accepted["record_status"] == "selected" and accepted["execution_authorized"] is False
    with pytest.raises(subject().checker.CheckerError, match="containment_record_status_mismatch"):
        subject().prepare_containment(**arguments(fixture, value=chosen))


def test_view_uses_only_sealed_data_and_fixed_namespace_policy(valid):
    request = json.loads(valid.request_bytes)
    args = request["launch_policy"]["argv_template"]
    for flag in ("--unshare-user", "--unshare-ipc", "--unshare-pid", "--unshare-net",
                 "--unshare-uts", "--unshare-cgroup", "--disable-userns",
                 "--die-with-parent", "--clearenv"):
        assert args.count(flag) == 1
    assert args[args.index("--cap-drop") + 1] == "ALL"
    assert args[args.index("--tmpfs") + 1] == "/"
    assert args[-7:] == ["--seccomp", "@seccomp", "--chdir", "/empty",
                         "--", "/runtime/bootstrap/containment-entry", "worker"]
    assert args[args.index("--remount-ro") + 1] == "/"
    assert args.count("--ro-bind-data") == len(request["files"])
    assert not any(value in args for value in ("--bind", "--ro-bind", "--bind-try", "--dev", "--proc",
                                               "--share-net", "--unshare-user-try", "--not-a-security-boundary",
                                               "--new-session"))
    assert request["launch_policy"]["launcher_new_session"] is True
    assert request["launch_policy"]["kill_scope"] == "owned_process_group"
    data = dict(valid.contents)
    for row in request["files"]:
        assert bound(data[row["path"]]) == {key: row[key] for key in ("sha256", "size_bytes")}
        expected = "0500" if row["path"] in {subject().policy.ENTRY_PATH, subject().bootstrap.LOADER} else "0400"
        assert row["mode"] == expected
    assert request["launch_policy"]["environment"] == {"LC_ALL": "C", "TZ": "UTC"}
    assert request["launch_policy"]["stdin"] == "empty_sealed_file"
    assert request["launch_policy"]["limits"] == {
        "wall_seconds": 15, "cpu_seconds": 5, "address_space_bytes": 512 * 1024 * 1024,
        "stdout_bytes": 65536, "stderr_bytes": 4096, "applications": 0, "attempts": 1,
    }


def test_argument_limit_is_checked_before_an_oversized_bubblewrap_command():
    files = [{"path": "/runtime/files/f" + str(index), "mode": "0400"} for index in range(2000)]
    with pytest.raises(subject().ContainmentError):
        subject()._argv(files, "worker")


@pytest.mark.parametrize("field", ["argv", "environment", "limits", "files", "bindings", "authority"])
def test_rehashed_request_tampering_cannot_replace_independent_reconstruction(valid, field):
    request = json.loads(valid.request_bytes)
    if field == "argv":
        request["launch_policy"]["argv_template"].insert(0, "--share-net")
    elif field == "environment":
        request["launch_policy"]["environment"]["PYTHONPATH"] = "/host"
    elif field == "limits":
        request["launch_policy"]["limits"]["attempts"] = 2
    elif field == "files":
        request["files"][0]["sha256"] = "0" * 64
    elif field == "bindings":
        request["bindings"]["launcher"]["sha256"] = "0" * 64
    else:
        request["containment_enforced"] = True
    raw = encoded(request)
    with pytest.raises(subject().ContainmentError, match="containment_request_reconstruction_mismatch"):
        subject().verify_request(valid, request_bytes=raw, expected_request_sha256=digest(raw))


def test_external_request_digest_and_canonical_bytes_are_both_required(valid):
    with pytest.raises(subject().ContainmentError, match="containment_request_digest_mismatch"):
        subject().verify_request(valid, request_bytes=valid.request_bytes, expected_request_sha256="0" * 64)
    raw = valid.request_bytes + b"\n"
    with pytest.raises(subject().ContainmentError, match="containment_request_reconstruction_mismatch"):
        subject().verify_request(valid, request_bytes=raw, expected_request_sha256=digest(raw))


def test_prepared_container_is_immutable_and_re_admitted(valid):
    with pytest.raises(FrozenInstanceError):
        valid.request_bytes = b"{}"
    for field, value in (("request_bytes", valid.request_bytes + b" "),
                         ("contents", valid.contents[:-1]), ("_admission", object())):
        forged = object.__new__(subject().PreparedContainment)
        for key in ("inputs", "request_bytes", "contents", "_admission"):
            object.__setattr__(forged, key, value if key == field else getattr(valid, key))
        with pytest.raises(subject().ContainmentError):
            subject().verify_request(forged, request_bytes=forged.request_bytes,
                                      expected_request_sha256=digest(forged.request_bytes))


def test_selected_execution_is_rejected_before_backend_or_output_creation(valid, tmp_path, monkeypatch):
    request = json.loads(valid.request_bytes)
    request["record_status"] = "selected"
    admitted = SimpleNamespace(request_bytes=encoded(request))
    monkeypatch.setattr(subject(), "_admitted", lambda _value: admitted)
    monkeypatch.setattr(subject(), "_backend", lambda *_args: pytest.fail("selected execution must not reach backend"))
    destination = tmp_path / "attempt"
    with pytest.raises(subject().ContainmentError, match="selected_bootstrap_execution_not_ready"):
        subject().run_example(valid, output_directory=destination)
    assert not destination.exists()


def test_descriptor_budget_failure_precedes_output_and_backend(valid, tmp_path, monkeypatch):
    monkeypatch.setattr(resource, "getrlimit", lambda _which: (1, 1))
    monkeypatch.setattr(subject(), "_backend", lambda *_args: pytest.fail("insufficient descriptor budget"))
    destination = tmp_path / "attempt"
    with pytest.raises(subject().ContainmentError, match="containment_descriptor_budget_insufficient"):
        subject().run_example(valid, output_directory=destination)
    assert not destination.exists()


def install_authored_child(monkeypatch, prepared, tmp_path, *, stdout=b"", stderr=b"", exit_code=0,
                           sleep=False, close_streams=False, after_spawn=None, inspect=None):
    code = (
        "import os,time,base64\n"
        "out=base64.b64decode(" + repr(base64.b64encode(stdout).decode()) + ")\n"
        "err=base64.b64decode(" + repr(base64.b64encode(stderr).decode()) + ")\n"
        "for fd,data in ((1,out),(2,err)):\n"
        " while data:\n"
        "  count=os.write(fd,data); data=data[count:]\n"
        + ("os.close(1);os.close(2)\n" if close_streams else "")
        + ("time.sleep(30)\n" if sleep else "")
        + "os._exit(" + str(exit_code) + ")\n"
    )
    children = []

    def popen(argv, **kwargs):
        if inspect is not None:
            inspect(argv, kwargs)
        child = REAL_POPEN([sys.executable, "-I", "-S", "-B", "-c", code], stdin=kwargs["stdin"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
                           cwd=tmp_path, env={"LC_ALL": "C", "TZ": "UTC"}, start_new_session=True)
        children.append(child)
        if after_spawn is not None:
            after_spawn(child)
        return child

    monkeypatch.setattr(subject().subprocess, "Popen", popen)
    return children


def test_backend_seals_every_input_and_uses_exact_descriptor_arguments(valid, tmp_path, monkeypatch):
    request = json.loads(valid.request_bytes)
    inspected = []
    fds = []

    def inspect(argv, kwargs):
        assert argv[:2] == ["bubblewrap", "--args"]
        assert kwargs["close_fds"] is True and kwargs["start_new_session"] is True
        assert kwargs["env"] == {"LC_ALL": "C", "TZ": "UTC"} and kwargs["cwd"] == "/"
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
        launcher_fd = int(kwargs["executable"].removeprefix("/proc/self/fd/"))
        assert os.pread(launcher_fd, 16 * 1024 * 1024, 0) == dict(valid.inputs)["launcher_bytes"]
        assert os.pread(kwargs["stdin"], 1, 0) == b""
        args_fd = int(argv[2])
        args = os.pread(args_fd, 4 * 1024 * 1024, 0).decode("ascii").split("\0")
        assert args.pop() == ""
        template = request["launch_policy"]["argv_template"]
        assert len(args) == len(template)
        for index, expected in enumerate(template):
            if expected == "@seccomp":
                assert os.pread(int(args[index]), 65536, 0) == subject().policy.policy_bytes()
            elif expected.startswith("@file:"):
                row = request["files"][int(expected.split(":")[1])]
                assert os.pread(int(args[index]), 16 * 1024 * 1024, 0) == dict(valid.contents)[row["path"]]
            else:
                assert args[index] == expected
        for fd in (*kwargs["pass_fds"], kwargs["stdin"]):
            assert fcntl.fcntl(fd, 1034) == 15
            fds.append(fd)
        assert kwargs["pass_fds"] == tuple(sorted(set(kwargs["pass_fds"])))
        inspected.append(True)

    children = install_authored_child(monkeypatch, valid, tmp_path, stdout=b"authored output\n",
                                      stderr=b"authored diagnostic\n", inspect=inspect)
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    observed, failure, raw = subject()._backend(valid, lambda name, data: chunks[name].extend(data))
    assert inspected == [True] and len(children) == 1
    assert failure is None and observed["exit_code"] == 0
    assert raw == {name: bytes(value) for name, value in chunks.items()}
    assert raw == {"stdout": b"authored output\n", "stderr": b"authored diagnostic\n"}
    for fd in set(fds):
        with pytest.raises(OSError):
            os.fstat(fd)


@pytest.mark.parametrize("stream,limit", [("stdout", 65536), ("stderr", 4096)])
def test_backend_retains_exact_bounded_prefix_and_stops_overflow(valid, tmp_path, monkeypatch, stream, limit):
    children = install_authored_child(monkeypatch, valid, tmp_path, **{stream: b"x" * (limit + 1)}, sleep=True)
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    observed, failure, raw = subject()._backend(valid, lambda name, data: chunks[name].extend(data))
    assert failure == "containment_" + stream + "_limit"
    assert raw[stream] == bytes(chunks[stream]) == b"x" * limit
    assert observed["exit_code"] is not None and children[0].poll() is not None
    assert len(children) == 1


def test_backend_timeout_kills_and_reaps_one_child(valid, tmp_path, monkeypatch):
    clock = time.monotonic
    offset = [0]
    monkeypatch.setattr(subject().time, "monotonic", lambda: clock() + offset[0])
    children = install_authored_child(monkeypatch, valid, tmp_path, sleep=True,
                                      after_spawn=lambda _child: offset.__setitem__(0, 16))
    observed, failure, raw = subject()._backend(valid, lambda *_args: None)
    assert failure == "containment_deadline_exceeded"
    assert observed["exit_code"] is not None and children[0].poll() is not None
    assert raw == {"stdout": b"", "stderr": b""} and len(children) == 1


def test_backend_preserves_nonzero_exit_output_and_never_retries(valid, tmp_path, monkeypatch):
    children = install_authored_child(monkeypatch, valid, tmp_path, stdout=b"partial\n", exit_code=23)
    signals = []
    monkeypatch.setattr(subject().os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    observed, failure, raw = subject()._backend(valid, lambda *_args: None)
    assert failure == "containment_backend_exit_nonzero" and observed["exit_code"] == 23
    assert raw["stdout"] == b"partial\n" and len(children) == 1
    assert signals == [], "A reaped child's process group may have been reused."


def test_backend_wait_is_bounded_after_both_output_pipes_close(valid, tmp_path, monkeypatch):
    waits = []

    def intercept_wait(child):
        real_wait = child.wait

        def wait(timeout=None):
            waits.append(timeout)
            return real_wait(timeout=min(timeout, 0.03) if len(waits) == 1 else timeout)

        child.wait = wait

    children = install_authored_child(monkeypatch, valid, tmp_path, sleep=True, close_streams=True,
                                      after_spawn=intercept_wait)
    observed, failure, raw = subject()._backend(valid, lambda *_args: None)
    assert failure == "containment_deadline_exceeded"
    assert waits and all(timeout is not None and timeout <= 15 for timeout in waits)
    assert observed["exit_code"] is not None and children[0].poll() is not None
    assert raw == {"stdout": b"", "stderr": b""} and len(children) == 1


def test_spawn_failure_preserves_an_incomplete_empty_attempt(valid, tmp_path, monkeypatch):
    calls = []

    def rejected(*args, **kwargs):
        calls.append(True)
        raise OSError(errno.ENOEXEC, "authored unavailable host launcher")

    monkeypatch.setattr(subject().subprocess, "Popen", rejected)
    destination = tmp_path / "attempt"
    result = subject().run_example(valid, output_directory=destination)
    assert calls == [True]
    assert result["status"] == "incomplete" and result["error_code"] == "containment_spawn_failed"
    assert result["process"]["pid"] is result["process"]["exit_code"] is None
    assert (destination / "stdout.bin").read_bytes() == (destination / "stderr.bin").read_bytes() == b""
    checked = verify(valid, result, b"")
    assert checked["attempt_complete"] is False and checked["finite_diagnostic_valid"] is False
    boundaries(checked)


@pytest.mark.parametrize("phase", ["worker", "collector"])
def test_completed_authored_attempt_is_preserved_and_independently_checked(fixture, tmp_path, monkeypatch, phase):
    prepared = subject().prepare_containment(**arguments(fixture, phase=phase))
    raw = encoded(authored_report(prepared))
    monkeypatch.setattr(subject(), "_backend", fake_backend(raw))
    destination = tmp_path / "attempt"
    receipt = subject().run_example(prepared, output_directory=destination)
    assert receipt["status"] == "completed"
    assert {path.name for path in destination.iterdir()} == {
        "request.json", "selection.json", "bootstrap_plan.json", "attempt_start.json",
        "stdout.bin", "stderr.bin", "receipt.json"}
    assert (destination / "request.json").read_bytes() == prepared.request_bytes
    assert (destination / "stdout.bin").read_bytes() == raw
    assert (destination / "stderr.bin").read_bytes() == b""
    assert json.loads((destination / "receipt.json").read_bytes()) == receipt
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in destination.iterdir())
    checked = verify(prepared, receipt, raw)
    assert checked["attempt_complete"] is True and checked["finite_diagnostic_valid"] is True
    boundaries(receipt)
    boundaries(checked)


@pytest.mark.parametrize("case", ["stderr", "invalid_json", "wrong_phase"])
def test_zero_exit_is_insufficient_for_completed_diagnostic(valid, tmp_path, monkeypatch, case):
    report = authored_report(valid)
    raw, stderr = encoded(report), b""
    if case == "stderr":
        stderr = b"unexpected diagnostic\n"
    elif case == "invalid_json":
        raw = b"not JSON\n"
    else:
        report["phase"] = "collector"
        raw = encoded(report)
    monkeypatch.setattr(subject(), "_backend", fake_backend(raw, stderr))
    receipt = subject().run_example(valid, output_directory=tmp_path / "attempt")
    assert receipt["status"] == "incomplete"
    assert receipt["error_code"] == ("containment_stderr_not_empty" if case == "stderr" else "containment_diagnostic_invalid")
    assert verify(valid, receipt, raw, stderr)["attempt_complete"] is False


def test_partial_stream_preservation_failure_keeps_prefix_without_receipt(valid, tmp_path, monkeypatch):
    raw = encoded(authored_report(valid))
    directory = subject().bootstrap.runtime.acquisition._Directory
    append = directory.append
    retained_prefix = []

    def partial(fd, data):
        if os.readlink("/proc/self/fd/" + str(fd)).endswith("/stdout.bin"):
            retained_prefix.append(data[:17])
            os.write(fd, retained_prefix[-1])
            raise OSError(errno.ENOSPC, "authored partial write")
        append(fd, data)

    monkeypatch.setattr(directory, "append", staticmethod(partial))
    children = install_authored_child(monkeypatch, valid, tmp_path, stdout=raw, sleep=True)
    destination = tmp_path / "attempt"
    with pytest.raises(subject().PreservationError):
        subject().run_example(valid, output_directory=destination)
    assert len(retained_prefix) == 1 and 0 < len(retained_prefix[0]) <= 17
    assert retained_prefix[0] == raw[:len(retained_prefix[0])]
    assert (destination / "stdout.bin").read_bytes() == retained_prefix[0]
    assert not (destination / "receipt.json").exists()
    marker = json.loads((destination / "attempt.incomplete.json").read_bytes())
    assert marker["error_code"] == "containment_preservation_failed"
    assert len(children) == 1 and children[0].poll() is not None
    boundaries(marker)


@pytest.mark.parametrize("change", ["bytes", "inode", "symlink", "hardlink", "mode", "extra", "directory_mode"])
def test_preserved_attempt_substitution_cannot_receive_a_receipt(valid, tmp_path, monkeypatch, change):
    raw = encoded(authored_report(valid))
    destination = tmp_path / "attempt"

    def mutate():
        path = destination / "stdout.bin"
        if change == "bytes":
            path.write_bytes(b"x" * len(raw))
        elif change == "inode":
            path.unlink()
            path.write_bytes(raw)
            path.chmod(0o600)
        elif change == "symlink":
            elsewhere = tmp_path / "elsewhere"
            elsewhere.write_bytes(raw)
            path.unlink()
            path.symlink_to(elsewhere)
        elif change == "hardlink":
            os.link(path, tmp_path / "linked")
        elif change == "mode":
            path.chmod(0o644)
        elif change == "extra":
            (destination / "unselected.bin").write_bytes(b"extra")
        else:
            destination.chmod(0o755)

    monkeypatch.setattr(subject(), "_backend", fake_backend(raw, mutate=mutate))
    with pytest.raises((subject().ContainmentError, OSError)):
        subject().run_example(valid, output_directory=destination)
    assert (destination / "attempt_start.json").exists()
    assert not (destination / "receipt.json").exists()


def test_output_path_substitution_is_checked_against_pinned_directory(valid, tmp_path, monkeypatch):
    raw = encoded(authored_report(valid))
    destination, moved = tmp_path / "attempt", tmp_path / "moved"

    def substitute():
        destination.rename(moved)
        destination.mkdir(mode=0o700)

    monkeypatch.setattr(subject(), "_backend", fake_backend(raw, mutate=substitute))
    with pytest.raises(subject().bootstrap.runtime.CapsuleError):
        subject().run_example(valid, output_directory=destination)
    assert (moved / "stdout.bin").read_bytes() == raw
    assert (moved / "attempt.incomplete.json").exists()
    assert not (moved / "receipt.json").exists() and not (destination / "receipt.json").exists()


@pytest.mark.parametrize("kind", ["existing", "symlink", "parent_symlink"])
def test_output_must_be_new_and_refuses_links_before_backend(valid, tmp_path, monkeypatch, kind):
    destination = tmp_path / "attempt"
    if kind == "existing":
        destination.mkdir()
        (destination / "keep").write_bytes(b"existing")
    elif kind == "symlink":
        existing = tmp_path / "existing"
        existing.mkdir()
        destination.symlink_to(existing, target_is_directory=True)
    else:
        existing = tmp_path / "existing"
        existing.mkdir()
        parent = tmp_path / "parent"
        parent.symlink_to(existing, target_is_directory=True)
        destination = parent / "attempt"
    monkeypatch.setattr(subject(), "_backend", lambda *_args: pytest.fail("no retry or overwrite"))
    with pytest.raises(subject().bootstrap.runtime.acquisition.AcquisitionError):
        subject().run_example(valid, output_directory=destination)
    if kind == "existing":
        assert (destination / "keep").read_bytes() == b"existing"


@pytest.mark.parametrize("change", ["startup", "subject", "module_digest", "module_origin", "module_roster",
                                     "module_preloaded_type", "resource_digest", "resource_roster",
                                     "finite_checks", "outside_path", "missing_path", "authority",
                                     "extra_field", "phase", "noncanonical"])
def test_checker_rejects_rebound_invalid_finite_probe_reports(valid, change):
    report = authored_report(valid)
    if change == "startup":
        report["startup"]["prefix"] = "/host"
    elif change == "subject":
        report["capsule_sha256"] = "0" * 64
    elif change == "module_digest":
        report["module_observations"][0]["sha256"] = "0" * 64
    elif change == "module_origin":
        report["module_observations"][0]["observed_origin"] = "/host/module.py"
    elif change == "module_roster":
        report["module_observations"].pop()
    elif change == "module_preloaded_type":
        report["module_observations"][0]["present_before_phase"] = 0
    elif change == "resource_digest":
        report["resource_observations"][0]["sha256"] = "0" * 64
    elif change == "resource_roster":
        report["resource_observations"].pop()
    elif change == "finite_checks":
        report["finite_checks"]["sha256"] = 1
    elif change == "outside_path":
        report["post_phase_sys_path"].append("/host")
    elif change == "missing_path":
        report["post_phase_sys_path"].pop()
    elif change == "authority":
        report["execution_authorized"] = True
    elif change == "extra_field":
        report["unselected"] = True
    elif change == "phase":
        report["phase"] = "collector"
    raw = encoded(report) + (b" " if change == "noncanonical" else b"")
    receipt = authored_receipt(valid, raw)
    with pytest.raises(subject().checker.CheckerError):
        verify(valid, receipt, raw)


def test_allowed_duplicate_import_roots_do_not_expand_path_roster(valid):
    report = authored_report(valid)
    report["post_phase_sys_path"].insert(0, "/runtime/repository/tools")
    raw = encoded(report)
    checked = verify(valid, authored_receipt(valid, raw), raw)
    assert checked["finite_diagnostic_valid"] is True
    boundaries(checked)


@pytest.mark.parametrize("change", ["request", "phase", "stdout_binding", "stderr_binding", "pid",
                                     "exit", "clock", "wall_limit", "error", "extra", "authority"])
def test_receipt_mutations_remain_invalid_after_rehashing(valid, change):
    raw = encoded(authored_report(valid))
    receipt = authored_receipt(valid, raw)
    if change == "request":
        receipt["request_sha256"] = "0" * 64
    elif change == "phase":
        receipt["phase"] = "collector"
    elif change in {"stdout_binding", "stderr_binding"}:
        receipt["streams"][change.split("_")[0]]["sha256"] = "0" * 64
    elif change == "pid":
        receipt["process"]["pid"] = True
    elif change == "exit":
        receipt["process"]["exit_code"] = 1
    elif change == "clock":
        receipt["process"]["completed_monotonic_ns"] = 1
    elif change == "wall_limit":
        receipt["process"]["completed_monotonic_ns"] = 17_000_000_001
    elif change == "error":
        receipt["error_code"] = "failed"
    elif change == "extra":
        receipt["approved"] = True
    else:
        receipt["containment_enforced"] = True
    with pytest.raises(subject().checker.CheckerError):
        verify(valid, receipt, raw)


def test_receipt_expected_digest_and_raw_streams_are_independent_inputs(valid):
    raw = encoded(authored_report(valid))
    receipt = encoded(authored_receipt(valid, raw))
    with pytest.raises(subject().checker.CheckerError, match="containment_receipt_digest_mismatch"):
        subject().verify_attempt(valid, receipt_bytes=receipt, expected_receipt_sha256="0" * 64,
                                 stdout_bytes=raw, stderr_bytes=b"")
    with pytest.raises(subject().checker.CheckerError, match="containment_receipt_stream_mismatch"):
        subject().verify_attempt(valid, receipt_bytes=receipt, expected_receipt_sha256=digest(receipt),
                                 stdout_bytes=raw + b"x", stderr_bytes=b"")


def test_incomplete_record_acceptance_cannot_be_promoted_to_completion(valid):
    raw = b"partial diagnostic bytes\n"
    receipt = authored_receipt(valid, raw, error="containment_backend_exit_nonzero")
    checked = verify(valid, receipt, raw)
    assert checked["status"] == "accepted" and checked["attempt_complete"] is False
    assert checked["finite_diagnostic_valid"] is False
    boundaries(checked)
    receipt.update(status="completed", error_code=None)
    receipt["process"]["exit_code"] = 0
    with pytest.raises(subject().checker.CheckerError):
        verify(valid, receipt, raw)


@pytest.mark.parametrize("error", [None, "", "UPPER", "contains space", True, "x" * 129])
def test_incomplete_receipt_requires_a_bounded_machine_readable_error(valid, error):
    receipt = authored_receipt(valid, b"", error="initial")
    receipt["error_code"] = error
    with pytest.raises(subject().checker.CheckerError, match="containment_incomplete_error_required"):
        verify(valid, receipt, b"")


def bpf_evaluate(program, arch, number):
    """Independent tiny interpreter for the emitted classic-BPF subset."""
    data = struct.pack("<II", number, arch)
    accumulator = 0
    pc = 0
    for _ in range(len(program) + 1):
        op, yes, no, value = program[pc]
        if op == 0x20:
            accumulator = struct.unpack_from("<I", data, value)[0]
            pc += 1
        elif op == 0x15:
            pc += 1 + (yes if accumulator == value else no)
        elif op == 0x45:
            pc += 1 + (yes if accumulator & value else no)
        elif op == 0x06:
            return value
        else:
            raise AssertionError("unexpected BPF opcode")
    raise AssertionError("BPF program failed to terminate")


def test_emitted_filter_has_independently_verified_architecture_and_syscall_outcomes():
    policy = subject().policy
    raw = policy.policy_bytes()
    assert raw == b"".join(struct.pack("<HBBI", *row) for row in policy.policy_instructions())
    instructions = tuple(struct.unpack_from("<HBBI", raw, offset) for offset in range(0, len(raw), 8))
    for number in (0, 1, 2, 3, 9, 39, 59, 60, 257, 302, 318, 436):
        assert bpf_evaluate(instructions, 0xC000003E, number) == 0x7FFF0000
    forbidden = (16, 41, 42, 43, 56, 57, 58, 101, 112, 155, 161, 165, 166, 175, 246,
                 250, 272, 298, 308, 310, 311, 321, 322, 425, 435, 437, 9999)
    for number in forbidden:
        assert bpf_evaluate(instructions, 0xC000003E, number) == 0x00050001
    for arch, number in ((0x40000003, 39), (0xC00000B7, 39), (0, 0), (0xC000003E, 0x40000000)):
        assert bpf_evaluate(instructions, arch, number) == 0x80000000
    for number in range(450):
        assert bpf_evaluate(instructions, policy.AUDIT_ARCH_X86_64, number) == policy.evaluate_policy(policy.AUDIT_ARCH_X86_64, number)


def test_fixed_filter_denies_forbidden_calls_in_an_isolated_authored_child(tmp_path):
    raw = subject().policy.policy_bytes()
    script = """
import ctypes,json,os,sys
class Filter(ctypes.Structure):
    _fields_=[("code",ctypes.c_ushort),("jt",ctypes.c_ubyte),("jf",ctypes.c_ubyte),("k",ctypes.c_uint)]
class Program(ctypes.Structure):
    _fields_=[("length",ctypes.c_ushort),("filters",ctypes.POINTER(Filter))]
raw=bytes.fromhex(sys.argv[1])
rows=(Filter*(len(raw)//8)).from_buffer_copy(raw)
program=Program(len(rows),rows)
libc=ctypes.CDLL(None,use_errno=True)
libc.syscall.restype=ctypes.c_long
if libc.prctl(38,1,0,0,0)!=0 or libc.prctl(22,2,ctypes.byref(program),0,0)!=0:
    raise RuntimeError("fixed filter installation failed")
denied=[]
for name,number,args in (
 ("socket",41,(2,1,0)),("fork",57,()),("clone3",435,(0,0)),
 ("mount",165,(0,0,0,0,0)),("ptrace",101,(0x7fffffff,0,0,0)),
 ("unshare",272,(0,)),("openat2",437,(-100,0,0,0)),
 ("io_uring_setup",425,(0,0)),("bpf",321,(0,0,0))):
    ctypes.set_errno(0)
    result=libc.syscall(number,*args)
    error=ctypes.get_errno()
    if name=="fork" and result==0:
        os._exit(91)
    if result!=-1 or error!=1:
        raise RuntimeError(name+" was not denied")
    denied.append(name)
assert libc.syscall(39)>0
print(json.dumps({"denied":denied,"getpid_allowed":True},sort_keys=True))
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script, raw.hex()],
                            capture_output=True, cwd=tmp_path, timeout=10)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stderr == b""
    report = json.loads(result.stdout)
    assert report["getpid_allowed"] is True
    assert report["denied"] == ["socket", "fork", "clone3", "mount", "ptrace", "unshare", "openat2", "io_uring_setup", "bpf"]


def cli_inputs(fixture, directory):
    directory.mkdir()
    args = []
    for name, raw in (
        ("runtime-selection", fixture.original.runtime.selection_bytes()),
        ("operator-selection", fixture.original.runtime.operator_bytes()),
        ("capsule", fixture.original.capsule),
        ("bootstrap-selection", fixture.original.selection_bytes()),
        ("bootstrap-plan", fixture.bootstrap.plan_bytes),
    ):
        path = directory / (name + (".zip" if name == "capsule" else ".json"))
        path.write_bytes(raw)
        args.extend(("--" + name, str(path), "--" + name + "-sha256", digest(raw)))
    launcher, entry = directory / "launcher", directory / "entry"
    launcher.write_bytes(fixture.launcher)
    entry.write_bytes(fixture.entry)
    chosen = selection(fixture)
    chosen["launcher"]["path"] = str(launcher)
    raw = encoded(chosen)
    path = directory / "containment-selection.json"
    path.write_bytes(raw)
    args.extend(("--containment-selection", str(path), "--containment-selection-sha256", digest(raw),
                 "--launcher", str(launcher), "--entry-shim", str(entry)))
    prepared = subject().prepare_containment(**arguments(fixture, value=chosen))
    return args, prepared


def test_cli_prepare_check_and_empty_stderr_receipt_round_trip(fixture, tmp_path):
    args, prepared = cli_inputs(fixture, tmp_path / "inputs")
    request = tmp_path / "request.json"
    created = subprocess.run([sys.executable, str(TOOL), "prepare", *args, "--output", str(request)],
                             capture_output=True, timeout=20)
    assert created.returncode == 0, created.stdout.decode(errors="replace") + created.stderr.decode(errors="replace")
    assert request.read_bytes() == prepared.request_bytes
    boundaries(json.loads(created.stdout))
    checked = subprocess.run([sys.executable, str(TOOL), "check", *args, "--request", str(request),
                              "--request-sha256", digest(prepared.request_bytes)], capture_output=True, timeout=20)
    assert checked.returncode == 0 and json.loads(checked.stdout)["boundary_request_verified"] is True
    stdout = encoded(authored_report(prepared))
    receipt = encoded(authored_receipt(prepared, stdout))
    receipt_path, stdout_path, stderr_path = (tmp_path / name for name in ("receipt.json", "stdout.bin", "stderr.bin"))
    receipt_path.write_bytes(receipt)
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(b"")
    verified = subprocess.run(
        [sys.executable, str(TOOL), "check-attempt", *args, "--request", str(request),
         "--request-sha256", digest(prepared.request_bytes), "--receipt", str(receipt_path),
         "--receipt-sha256", digest(receipt), "--stdout", str(stdout_path), "--stderr", str(stderr_path)],
        capture_output=True, timeout=20,
    )
    assert verified.returncode == 0, verified.stdout.decode(errors="replace") + verified.stderr.decode(errors="replace")
    report = json.loads(verified.stdout)
    assert report["attempt_complete"] is True
    boundaries(report)


def test_cli_rejects_existing_output_without_replacing_it(fixture, tmp_path):
    args, _ = cli_inputs(fixture, tmp_path / "inputs")
    output = tmp_path / "existing.json"
    output.write_bytes(b"preserve me\n")
    result = subprocess.run([sys.executable, str(TOOL), "prepare", *args, "--output", str(output)],
                            capture_output=True, timeout=20)
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "rejected"
    assert output.read_bytes() == b"preserve me\n"


def test_original_observed_acquisition_stays_closed():
    result = subprocess.run([sys.executable, str(ROOT / "tools/acquire_required_gate_idempotence_v0.py"), "acquire"],
                            capture_output=True, timeout=15)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["errors"] == ["observed_acquisition_not_ready"]
    assert report["execution_authorized"] is False and report["authority_effect"] == "none"


def test_containment_module_is_registered_once_without_targeted_duplication():
    def entries(name):
        return [value for line in (ROOT / "ci" / name).read_text().splitlines()
                if (value := line.split("#", 1)[0].strip())]
    tools, targeted = entries("tools-tests.list"), entries("pytest-tests.list")
    assert len(tools) == len(set(tools)) == 188 and tools.count(SELF) == 1
    assert len(targeted) == len(set(targeted)) == 40 and SELF not in targeted


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
