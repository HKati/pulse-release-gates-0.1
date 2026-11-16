#!/usr/bin/env python3
"""Synthetic containment regression; no selected runtime or operator executes.

Compiler tests use inert capsule bytes. Parent-process tests substitute an
authored host child at the Popen boundary; they never invoke bubblewrap or the
selected capsule. Native test code consists of invalid-argument entry checks,
a separate fixed-filter child and the fixed authored static mapping probe.
These tests do not establish namespace containment or selected-runtime execution.
Outer-launcher tests add authored package/native/host declarations and check
their exact relations without running the selected launcher or qualifying a host.
"""
from __future__ import annotations

import base64
import copy
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
import errno
import fcntl
import gzip
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import resource
import select
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
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


@contextmanager
def staged_overflow_child(monkeypatch, tmp_path, overflow_stream):
    """Buffer the other stream's second byte before servicing an overflow.

    Pipe handshakes establish the ordering; no sleep or pipe-capacity assumption
    controls it. The selector deliberately services the overflowing stream once
    the first other-stream byte reaches the sink.
    """
    other = "stderr" if overflow_stream == "stdout" else "stdout"
    limit = 65536 if overflow_stream == "stdout" else 4096
    other_fd, overflow_fd = ((2, 1) if overflow_stream == "stdout" else (1, 2))
    gate_r, gate_w = os.pipe()
    ready_r, ready_w = os.pipe()
    descriptors = [gate_r, gate_w, ready_r, ready_w]
    children = []
    code = (
        "import os,signal\n"
        f"os.write({other_fd},b'A')\n"
        f"assert os.read({gate_r},1)==b'G'\n"
        f"os.write({other_fd},b'B')\n"
        f"os.write({ready_w},b'R')\n"
        f"data=b'x'*{limit + 1}\n"
        f"while data:\n count=os.write({overflow_fd},data);data=data[count:]\n"
        "signal.pause()\n"
    )

    def popen(_argv, **kwargs):
        child = REAL_POPEN([sys.executable, "-I", "-S", "-B", "-c", code],
                           stdin=kwargs["stdin"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           close_fds=True, pass_fds=(gate_r, ready_w), cwd=tmp_path,
                           env={"LC_ALL": "C", "TZ": "UTC"}, start_new_session=True)
        children.append(child)
        for fd in (gate_r, ready_w):
            os.close(fd)
            descriptors.remove(fd)
        return child

    def release():
        os.write(gate_w, b"G")
        assert select.select([ready_r], [], [], 5)[0], "authored child did not buffer its second byte"
        assert os.read(ready_r, 1) == b"R"

    selector_type = subject().selectors.DefaultSelector

    class OrderedSelector(selector_type):
        prefix_selected = False

        def select(self, timeout=None):
            name = overflow_stream if self.prefix_selected else other
            key = self.get_key(getattr(children[0], name))
            if select.select([key.fd], [], [], timeout)[0]:
                self.prefix_selected = True
                return [(key, subject().selectors.EVENT_READ)]
            return []

    monkeypatch.setattr(subject().subprocess, "Popen", popen)
    monkeypatch.setattr(subject().selectors, "DefaultSelector", OrderedSelector)
    try:
        yield SimpleNamespace(children=children, release=release, other=other, limit=limit)
    finally:
        for fd in descriptors:
            os.close(fd)
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@contextmanager
def buffered_deadline_child(monkeypatch, tmp_path, *, keep_writers=False):
    """Expire the observed deadline only after both real pipes contain bytes."""
    ready_r, ready_w = os.pipe()
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    descriptors = [ready_r, ready_w, out_r, out_w, err_r, err_w]
    children = []
    clock, offset = time.monotonic, [0]
    monkeypatch.setattr(subject().time, "monotonic", lambda: clock() + offset[0])
    code = ("import os,signal\n"
            "os.write(1,b'pending stdout')\n"
            "os.write(2,b'pending stderr')\n"
            f"os.write({ready_w},b'R')\n"
            "signal.pause()\n")

    def popen(_argv, **kwargs):
        child = REAL_POPEN([sys.executable, "-I", "-S", "-B", "-c", code],
                           stdin=kwargs["stdin"], stdout=out_w, stderr=err_w,
                           close_fds=True, pass_fds=(ready_w,), cwd=tmp_path,
                           env={"LC_ALL": "C", "TZ": "UTC"}, start_new_session=True)
        children.append(child)
        child.stdout = os.fdopen(out_r, "rb", buffering=0)
        child.stderr = os.fdopen(err_r, "rb", buffering=0)
        for fd in (out_r, err_r):
            descriptors.remove(fd)
        for fd in (ready_w,) if keep_writers else (ready_w, out_w, err_w):
            os.close(fd)
            descriptors.remove(fd)
        assert select.select([ready_r], [], [], 5)[0], "authored child did not buffer both streams"
        assert os.read(ready_r, 1) == b"R"
        offset[0] = 16
        return child

    monkeypatch.setattr(subject().subprocess, "Popen", popen)
    try:
        yield children
    finally:
        for fd in descriptors:
            os.close(fd)
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize("overflow_stream", ["stdout", "stderr"])
def test_failed_attempt_drains_other_stream_before_binding_receipt(valid, tmp_path, monkeypatch, overflow_stream):
    directory = subject().bootstrap.runtime.acquisition._Directory
    append, read = directory.append, os.read
    drained = []
    destination = tmp_path / "attempt"
    with staged_overflow_child(monkeypatch, tmp_path, overflow_stream) as staged:
        def preserve(fd, data):
            name = Path(os.readlink("/proc/self/fd/" + str(fd))).stem
            if name == staged.other and data == b"A":
                staged.release()
            elif name == staged.other:
                assert staged.children[0].returncode is not None
                drained.append(data)
            append(fd, data)

        def bounded_read(fd, size):
            if staged.children and staged.children[0].returncode is not None:
                child = staged.children[0]
                stream = getattr(child, overflow_stream)
                assert stream.closed or fd != stream.fileno(), "full stream must not be drained again"
            return read(fd, size)

        monkeypatch.setattr(directory, "append", staticmethod(preserve))
        monkeypatch.setattr(subject().os, "read", bounded_read)
        receipt = subject().run_example(valid, output_directory=destination)
        assert len(staged.children) == 1 and staged.children[0].returncode is not None
        expected = {overflow_stream: b"x" * staged.limit, staged.other: b"AB"}
    assert b"".join(drained) == b"B"
    assert receipt["status"] == "incomplete"
    assert receipt["error_code"] == "containment_" + overflow_stream + "_limit"
    for name, raw in expected.items():
        assert (destination / (name + ".bin")).read_bytes() == raw
        assert receipt["streams"][name] == bound(raw)
    checked = verify(valid, receipt, expected["stdout"], expected["stderr"])
    assert checked["attempt_complete"] is False and checked["finite_diagnostic_valid"] is False
    boundaries(checked)


@pytest.mark.parametrize("keep_writers", [False, True])
def test_deadline_drain_preserves_both_pipes_without_waiting_for_eof(valid, tmp_path, monkeypatch, keep_writers):
    read = os.read
    empty_nonblocking = []
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    with buffered_deadline_child(monkeypatch, tmp_path, keep_writers=keep_writers) as children:
        def checked_read(fd, size):
            if children and children[0].returncode is not None:
                assert not os.get_blocking(fd)
            try:
                return read(fd, size)
            except BlockingIOError:
                empty_nonblocking.append(fd)
                raise

        def preserve(name, data):
            assert children[0].returncode is not None, "pending bytes must be drained after stopping the child"
            chunks[name].extend(data)

        monkeypatch.setattr(subject().os, "read", checked_read)
        observed, failure, raw = subject()._backend(valid, preserve)
        assert len(children) == 1 and children[0].returncode is not None
        assert observed["exit_code"] is not None
    assert failure == "containment_deadline_exceeded"
    assert raw == {"stdout": b"pending stdout", "stderr": b"pending stderr"}
    assert raw == {name: bytes(value) for name, value in chunks.items()}
    assert len(empty_nonblocking) == (2 if keep_writers else 0)


def test_drain_sink_failure_preserves_partial_bytes_without_receipt(valid, tmp_path, monkeypatch):
    directory = subject().bootstrap.runtime.acquisition._Directory
    append = directory.append
    retained = []
    destination = tmp_path / "attempt"
    with buffered_deadline_child(monkeypatch, tmp_path) as children:
        def partial(fd, data):
            if os.readlink("/proc/self/fd/" + str(fd)).endswith("/stdout.bin"):
                assert children[0].returncode is not None
                retained.append(data[:3])
                os.write(fd, retained[-1])
                raise OSError(errno.ENOSPC, "authored drain preservation failure")
            append(fd, data)

        monkeypatch.setattr(directory, "append", staticmethod(partial))
        with pytest.raises(subject().PreservationError):
            subject().run_example(valid, output_directory=destination)
        assert len(children) == 1 and children[0].returncode is not None
    assert retained == [b"pen"]
    assert (destination / "stdout.bin").read_bytes() == b"pen"
    assert not (destination / "receipt.json").exists()
    marker = json.loads((destination / "attempt.incomplete.json").read_bytes())
    assert marker["error_code"] == "containment_preservation_failed"
    boundaries(marker)


def test_capture_sink_failure_is_not_retried_by_pending_output_drain(valid, tmp_path, monkeypatch):
    directory = subject().bootstrap.runtime.acquisition._Directory
    append = directory.append
    retained = []
    destination = tmp_path / "attempt"
    with staged_overflow_child(monkeypatch, tmp_path, "stderr") as staged:
        def partial(fd, data):
            if os.readlink("/proc/self/fd/" + str(fd)).endswith("/stdout.bin"):
                assert data == b"A", "a failed sink must not be retried with buffered B"
                staged.release()
                retained.append(data)
                os.write(fd, data)
                raise OSError(errno.ENOSPC, "authored capture preservation failure")
            append(fd, data)

        monkeypatch.setattr(directory, "append", staticmethod(partial))
        with pytest.raises(subject().PreservationError):
            subject().run_example(valid, output_directory=destination)
        assert len(staged.children) == 1 and staged.children[0].returncode is not None
    assert retained == [b"A"]
    assert (destination / "stdout.bin").read_bytes() == b"A"
    assert (destination / "stderr.bin").read_bytes() == b""
    assert not (destination / "receipt.json").exists()
    marker = json.loads((destination / "attempt.incomplete.json").read_bytes())
    assert marker["error_code"] == "containment_preservation_failed"


def test_drain_read_error_cannot_publish_a_shortened_receipt(valid, tmp_path, monkeypatch):
    read = os.read
    destination = tmp_path / "attempt"
    with buffered_deadline_child(monkeypatch, tmp_path) as children:
        def broken_read(fd, size):
            if (children and children[0].returncode is not None and not children[0].stdout.closed
                    and fd == children[0].stdout.fileno()):
                raise OSError(errno.EIO, "authored pending-pipe read failure")
            return read(fd, size)

        monkeypatch.setattr(subject().os, "read", broken_read)
        with pytest.raises(subject().PreservationError):
            subject().run_example(valid, output_directory=destination)
        assert len(children) == 1 and children[0].returncode is not None
    assert not (destination / "receipt.json").exists()
    marker = json.loads((destination / "attempt.incomplete.json").read_bytes())
    assert marker["error_code"] == "containment_preservation_failed"


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
    assert len(tools) == len(set(tools)) == 189 and tools.count(SELF) == 1
    assert len(targeted) == len(set(targeted)) == 40 and SELF not in targeted


# The outer-launcher plan is part of this same containment boundary. These
# fixtures are authored bytes and passive declarations, never a qualified host.
LAUNCH_HOST_TOOL = ROOT / "tools/required_gate_idempotence_launch_host_v0.py"
LAUNCH_HOST_VERSION = "0.12.0-1+fixture1"
LAUNCH_HOST_LOADER = "/lib64/ld-linux-x86-64.so.2"


def launch_host_subject():
    return module("required_gate_idempotence_launch_host_v0", "tools/required_gate_idempotence_launch_host_v0.py")


def launch_host_checker():
    return module("check_required_gate_idempotence_launch_host_v0", "tools/check_required_gate_idempotence_launch_host_v0.py")


def launch_host_packages():
    return module("required_gate_idempotence_launcher_package_v0", "tools/required_gate_idempotence_launcher_package_v0.py")


def launch_host_tar(rows):
    target = io.BytesIO()
    with tarfile.open(fileobj=target, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, raw, mode, kind, link in rows:
            item = tarfile.TarInfo(name)
            item.mode, item.type, item.linkname = mode, kind, link
            item.size = len(raw) if kind == tarfile.REGTYPE else 0
            archive.addfile(item, io.BytesIO(raw) if kind == tarfile.REGTYPE else None)
    return target.getvalue()


def launch_host_ar(rows):
    result = bytearray(b"!<arch>\n")
    for name, raw in rows:
        header = ((name + "/").ljust(16) + "0".ljust(12) + "0".ljust(6) + "0".ljust(6)
                  + "100644".ljust(8) + str(len(raw)).ljust(10) + "`\n").encode("ascii")
        assert len(header) == 60
        result.extend(header + raw + (b"\n" if len(raw) % 2 else b""))
    return bytes(result)


def launch_host_package(launcher, *, compression="xz", control=None, mode=0o755, data_rows=None):
    if control is None:
        control = ("Package: bubblewrap\nVersion: " + LAUNCH_HOST_VERSION
                   + "\nArchitecture: amd64\nDescription: Authored test package\n"
                     " continued description retained in the original control bytes\n"
                     " .\n another paragraph in the same field\n").encode()
    control_tar = launch_host_tar([("./", b"", 0o755, tarfile.DIRTYPE, ""),
                                   ("./control", control, 0o644, tarfile.REGTYPE, "")])
    if data_rows is None:
        data_rows = [("./", b"", 0o755, tarfile.DIRTYPE, ""),
                     ("./usr/", b"", 0o755, tarfile.DIRTYPE, ""),
                     ("./usr/bin/", b"", 0o755, tarfile.DIRTYPE, ""),
                     ("./usr/bin/bwrap", launcher, mode, tarfile.REGTYPE, "")]
    data_tar = launch_host_tar(data_rows)
    compress = {"xz": lzma.compress, "gz": lambda raw: gzip.compress(raw, mtime=0), "tar": lambda raw: raw}[compression]
    suffix = "" if compression == "tar" else "." + compression
    return launch_host_ar([("debian-binary", b"2.0\n"),
                           ("control.tar" + suffix, compress(control_tar)),
                           ("data.tar" + suffix, compress(data_tar))])


def launch_host_observation():
    status = (b"Name:\tauthored-observer\nUid:\t1000\t1000\t1000\t1000\n"
              b"Gid:\t1000\t1000\t1000\t1000\nCapInh:\t0000000000000000\n"
              b"CapPrm:\t0000000000000000\nCapEff:\t0000000000000000\n"
              b"CapBnd:\t0000000000000000\nCapAmb:\t0000000000000000\n"
              b"NoNewPrivs:\t1\nSeccomp:\t2\nSeccomp_filters:\t1\n")
    files = {
        "/proc/self/status": status,
        "/proc/sys/user/max_user_namespaces": b"28633\n",
        "/proc/sys/kernel/unprivileged_userns_clone": b"1\n",
        "/proc/sys/kernel/apparmor_restrict_unprivileged_userns": b"0\n",
        "/proc/sys/vm/memfd_noexec": b"0\n",
        "/etc/ld.so.preload": b"",
    }
    return {"record_type": "required_gate_idempotence_launch_host_observation_v0",
            "profile": "linux_x86_64_bubblewrap_launch_host_v0", "observation_id": "f" * 32,
            "platform": {"system": "Linux", "machine": "x86_64", "release": "6.8.0-authored"},
            "identity": {"uid": 1000, "euid": 1000, "gid": 1000, "egid": 1000},
            "nofile": {"soft": 1024, "hard": 1048576}, "memfd_create_api": True,
            "open_fd_count": 7,
            "files": [{"path": path, "status": "present", "data_b64": base64.b64encode(raw).decode()}
                      for path, raw in sorted(files.items())],
            "namespaces": [{"name": name, "status": "present", "target": name + ":[4026531837]"}
                           for name in ("user", "mnt", "ipc", "pid", "net", "uts", "cgroup")]}


@pytest.fixture(scope="module")
def launch_host_case(fixture):
    c = launch_host_checker()
    native_examples = module("launch_host_native_examples", "tests/test_required_gate_idempotence_runtime_v0.py")
    native = {
        "native/bwrap": native_examples.elf(interpreter=LAUNCH_HOST_LOADER,
                                             needed=("libc.so.6", "libcap.so.2")),
        "native/ld-linux-x86-64.so.2": native_examples.elf(soname="ld-linux-x86-64.so.2"),
        "native/libc.so.6": native_examples.elf(soname="libc.so.6", needed=("ld-linux-x86-64.so.2",)),
        "native/libcap.so.2": native_examples.elf(soname="libcap.so.2", needed=("libc.so.6",)),
    }
    launcher = native["native/bwrap"]
    copied = SimpleNamespace(original=fixture.original, bootstrap=fixture.bootstrap,
                             entry=fixture.entry, launcher=launcher)
    prepared = subject().prepare_containment(**arguments(copied))
    build_examples = module("launch_host_build_examples", "tests/test_required_gate_idempotence_entry_build_v0.py")
    payload = build_examples.authored_payload(SimpleNamespace(
        entry=fixture.entry, source=(ROOT / "tools/required_gate_idempotence_containment_entry_v0.c").read_bytes()))
    package = launch_host_package(launcher)
    host_raw = encoded(launch_host_observation())
    roles = {"native/bwrap": ("launcher", "/selected-host/bwrap"),
             "native/ld-linux-x86-64.so.2": ("loader", LAUNCH_HOST_LOADER),
             "native/libc.so.6": ("shared_library", "/lib/x86_64-linux-gnu/libc.so.6"),
             "native/libcap.so.2": ("shared_library", "/lib/x86_64-linux-gnu/libcap.so.2")}
    chosen = {
        "record_type": "required_gate_idempotence_launch_host_selection_v0", "profile": c.PROFILE,
        "record_status": "example", "containment_request_sha256": digest(prepared.request_bytes),
        "entry_build": {"source_commit": "a" * 40, "request_sha256": digest(payload["request.json"]),
                        "record_sha256": digest(payload["record.json"])},
        "launcher_path": "native/bwrap", "loader_path": "native/ld-linux-x86-64.so.2",
        "native_files": [{"path": path, "host_path": roles[path][1], "role": roles[path][0], **bound(raw)}
                         for path, raw in sorted(native.items())],
        "native_bindings": [
            {"consumer": "native/bwrap", "kind": "interpreter", "name": LAUNCH_HOST_LOADER,
             "provider": "native/ld-linux-x86-64.so.2"},
            {"consumer": "native/bwrap", "kind": "needed", "name": "libc.so.6", "provider": "native/libc.so.6"},
            {"consumer": "native/bwrap", "kind": "needed", "name": "libcap.so.2", "provider": "native/libcap.so.2"},
            {"consumer": "native/libcap.so.2", "kind": "needed", "name": "libc.so.6", "provider": "native/libc.so.6"},
            {"consumer": "native/libc.so.6", "kind": "needed", "name": "ld-linux-x86-64.so.2",
             "provider": "native/ld-linux-x86-64.so.2"}],
        "launcher_origin": {"kind": "debian_package_member", "package": bound(package),
                            "member_path": "usr/bin/bwrap", "name": "bubblewrap", "version": LAUNCH_HOST_VERSION,
                            "architecture": "amd64"},
        "host_observation": bound(host_raw), **c.BOUNDARY,
    }
    return SimpleNamespace(fixture=copied, containment=prepared, entry_payload=payload, native=native,
                           package=package, host_raw=host_raw, selection=chosen)


def launch_host_arguments(case, *, chosen=None, **changes):
    raw = encoded(case.selection if chosen is None else chosen)
    result = {"containment_prepared": case.containment,
              "expected_containment_request_sha256": digest(case.containment.request_bytes),
              "selection_bytes": raw, "expected_selection_sha256": digest(raw),
              "entry_build_payload": dict(case.entry_payload), "launcher_package_bytes": case.package,
              "native_payload": dict(case.native), "host_observation_bytes": case.host_raw}
    result.update(changes)
    return result


def launch_host_plan(case, *, chosen=None, **changes):
    return json.loads(launch_host_checker().derive_plan(**launch_host_arguments(case, chosen=chosen, **changes)))


def launch_host_rebind_native(chosen, native):
    for row in chosen["native_files"]:
        row.update(bound(native[row["path"]]))


def launch_host_host_change(case, path, raw=None, *, status="present"):
    host = json.loads(case.host_raw)
    row = next(item for item in host["files"] if item["path"] == path)
    row.update(status=status, data_b64=base64.b64encode(raw).decode() if raw is not None else None)
    host_raw = encoded(host)
    chosen = copy.deepcopy(case.selection)
    chosen["host_observation"] = bound(host_raw)
    return chosen, host_raw


def test_launch_host_plan_and_independent_report_are_canonical_and_non_authorizing(launch_host_case):
    c, p = launch_host_checker(), launch_host_subject()
    args = launch_host_arguments(launch_host_case)
    prepared = p.prepare_launch_host(**args)
    assert prepared.plan_bytes == c.derive_plan(**args) == c.derive_plan(**args)
    assert encoded(json.loads(prepared.plan_bytes)) == prepared.plan_bytes
    report = c.verify_plan(plan_bytes=prepared.plan_bytes, expected_plan_sha256=digest(prepared.plan_bytes), **args)
    assert report == p.verify_launch_host(prepared, plan_bytes=prepared.plan_bytes,
                                          expected_plan_sha256=digest(prepared.plan_bytes))
    assert report["status"] == "accepted"
    for key in ("entry_build_binding_verified", "launcher_package_member_verified",
                "launcher_native_bindings_verified", "host_observation_record_verified"):
        assert report[key] is True
    for value in (json.loads(prepared.plan_bytes), report):
        for key, expected in c.BOUNDARY.items():
            assert value[key] == expected and type(value[key]) is type(expected)
    with pytest.raises(FrozenInstanceError):
        prepared.plan_bytes = b"substitution"
    assert all(row["status"] == "observed" for row in
               json.loads(prepared.plan_bytes)["host"]["namespace_observations"])
    passive = {row["id"]: row for row in json.loads(prepared.plan_bytes)["host"]["passive_prerequisites"]}
    assert passive["observer_NoNewPrivs"]["status"] == passive["observer_Seccomp"]["status"] == "observed"
    assert passive["observer_NoNewPrivs"]["value"] == 1 and passive["observer_Seccomp"]["value"] == 2
    assert report["containment_enforced"] is False and report["host_environment_qualified"] is False


def test_launch_host_relationship_checks_never_execute_native_or_network_inputs(launch_host_case, monkeypatch):
    import socket
    import urllib.request
    def forbidden(*args, **kwargs):
        raise AssertionError("offline launch-host checking attempted execution or network access")
    for obj, name in ((subprocess, "Popen"), (subprocess, "run"), (os, "system"), (os, "execve"),
                      (socket, "create_connection"), (urllib.request, "urlopen")):
        monkeypatch.setattr(obj, name, forbidden)
    p = launch_host_subject().prepare_launch_host(**launch_host_arguments(launch_host_case))
    assert launch_host_checker().verify_plan(plan_bytes=p.plan_bytes,
        expected_plan_sha256=digest(p.plan_bytes), **launch_host_arguments(launch_host_case))["status"] == "accepted"


@pytest.mark.parametrize("field", ["expected_selection_sha256", "expected_containment_request_sha256"])
def test_launch_host_external_hashes_remain_required(launch_host_case, field):
    with pytest.raises(launch_host_checker().HostError):
        launch_host_checker().derive_plan(**launch_host_arguments(launch_host_case, **{field: "0" * 64}))


@pytest.mark.parametrize("raw", [b'{"x":1,"x":1}', b'{"x":1.0}', b'{"x":NaN}',
                                 b'{"x":' + b'9' * 5000 + b'}'])
def test_launch_host_control_json_rejects_ambiguity_and_unbounded_numbers(raw):
    with pytest.raises(launch_host_checker().HostError):
        launch_host_checker().parse(raw)


@pytest.mark.parametrize("change", ["extra", "missing", "duplicate_path", "host_alias", "relative_traversal",
                                    "absolute_path", "host_normalization", "boolean_size", "selected_status"])
def test_launch_host_closed_selection_rejects_rehashed_inventory_changes(launch_host_case, change):
    chosen = copy.deepcopy(launch_host_case.selection)
    if change == "extra": chosen["qualified"] = True
    elif change == "missing": chosen.pop("host_observation")
    elif change == "duplicate_path": chosen["native_files"].append(copy.deepcopy(chosen["native_files"][0]))
    elif change == "host_alias": chosen["native_files"][1]["host_path"] = chosen["native_files"][0]["host_path"]
    elif change == "relative_traversal": chosen["launcher_path"] = "native/../bwrap"
    elif change == "absolute_path": chosen["launcher_path"] = "/native/bwrap"
    elif change == "host_normalization": chosen["native_files"][0]["host_path"] = "/selected-host/./bwrap"
    elif change == "boolean_size": chosen["native_files"][0]["size_bytes"] = True
    else: chosen["record_status"] = "selected"
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen)


@pytest.mark.parametrize("field", ["execution_ready", "execution_authorized", "host_launcher_runtime_verified",
                                   "github_build_provenance_verified", "launcher_executed",
                                   "launcher_origin_authenticated", "host_observation_authenticated", "authority_effect"])
def test_launch_host_selection_cannot_promote_passive_relationships(launch_host_case, field):
    chosen = copy.deepcopy(launch_host_case.selection)
    chosen[field] = "release" if field == "authority_effect" else True
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen)


@pytest.mark.parametrize("change", ["omit_other_consumer", "duplicate", "wrong_provider", "invented_edge", "wrong_loader"])
def test_launch_host_native_edges_are_checked_for_every_consumer(launch_host_case, change):
    chosen = copy.deepcopy(launch_host_case.selection)
    rows = chosen["native_bindings"]
    if change == "omit_other_consumer":
        rows[:] = [row for row in rows if row["consumer"] != "native/libcap.so.2"]
        assert any(row["name"] == "libc.so.6" for row in rows)
    elif change == "duplicate": rows.append(copy.deepcopy(rows[0]))
    elif change == "wrong_provider": rows[1]["provider"] = "native/libcap.so.2"
    elif change == "invented_edge": rows.append({"consumer": "native/bwrap", "kind": "needed", "name": "invented.so", "provider": "native/libc.so.6"})
    else: rows[0]["provider"] = "native/libc.so.6"
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen)


@pytest.mark.parametrize("change", ["unselected_payload", "missing_payload", "unreachable", "duplicate_soname",
                                    "rpath", "runpath", "loader_interpreter", "loader_wrong_soname"])
def test_launch_host_native_inventory_does_not_hide_ambient_or_unrelated_objects(launch_host_case, change):
    chosen, native = copy.deepcopy(launch_host_case.selection), dict(launch_host_case.native)
    elf = module("launch_host_native_examples", "tests/test_required_gate_idempotence_runtime_v0.py").elf
    if change == "unselected_payload": native["native/extra.so"] = elf(soname="extra.so")
    elif change == "missing_payload": native.pop("native/libcap.so.2")
    elif change in {"unreachable", "duplicate_soname"}:
        raw = elf(soname="unreachable.so" if change == "unreachable" else "libc.so.6")
        native["native/extra.so"] = raw
        chosen["native_files"].append({"path": "native/extra.so", "host_path": "/lib/extra.so", "role": "shared_library", **bound(raw)})
    elif change in {"rpath", "runpath"}:
        native["native/libcap.so.2"] = elf(soname="libcap.so.2", needed=("libc.so.6",), **{change: "/ambient"})
    elif change == "loader_interpreter":
        native["native/ld-linux-x86-64.so.2"] = elf(soname="ld-linux-x86-64.so.2", interpreter=LAUNCH_HOST_LOADER)
    else: native["native/ld-linux-x86-64.so.2"] = elf(soname="unrelated-loader.so")
    if change != "missing_payload": launch_host_rebind_native(chosen, native)
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen, native_payload=native)


def test_launch_host_reachable_native_cycle_is_not_mistaken_for_missing_evidence(launch_host_case):
    chosen, native = copy.deepcopy(launch_host_case.selection), dict(launch_host_case.native)
    elf = module("launch_host_native_examples", "tests/test_required_gate_idempotence_runtime_v0.py").elf
    native["native/ld-linux-x86-64.so.2"] = elf(soname="ld-linux-x86-64.so.2", needed=("libc.so.6",))
    launch_host_rebind_native(chosen, native)
    chosen["native_bindings"].append({"consumer": "native/ld-linux-x86-64.so.2", "kind": "needed",
                                       "name": "libc.so.6", "provider": "native/libc.so.6"})
    plan = launch_host_plan(launch_host_case, chosen=chosen, native_payload=native)
    assert plan["host_launcher_runtime_verified"] is False


def test_launch_host_coherently_replaced_package_and_launcher_do_not_replace_containment_selection(launch_host_case):
    chosen, native = copy.deepcopy(launch_host_case.selection), dict(launch_host_case.native)
    native["native/bwrap"] += b"different inert bytes after the selected ELF metadata"
    launch_host_rebind_native(chosen, native)
    package = launch_host_package(native["native/bwrap"])
    chosen["launcher_origin"]["package"] = bound(package)
    with pytest.raises(launch_host_checker().HostError) as caught:
        launch_host_plan(launch_host_case, chosen=chosen, native_payload=native, launcher_package_bytes=package)
    assert caught.value.code == "launch_host_launcher_binding_mismatch"


@pytest.mark.parametrize("change", ["source_commit", "request_hash", "record_hash", "missing_build", "rehashed_other_entry"])
def test_launch_host_requires_original_build_inputs_and_exact_containment_entry(launch_host_case, change):
    chosen, payload = copy.deepcopy(launch_host_case.selection), dict(launch_host_case.entry_payload)
    if change in {"source_commit", "request_hash", "record_hash"}:
        key = {"source_commit": "source_commit", "request_hash": "request_sha256", "record_hash": "record_sha256"}[change]
        chosen["entry_build"][key] = "0" * (40 if key == "source_commit" else 64)
    elif change == "missing_build": payload.pop("build-2/entry")
    else:
        for number in (1, 2):
            name = "build-" + str(number)
            payload[name + "/entry"] += b"independently different inert entry bytes"
            receipt = json.loads(payload[name + "/result.json"])
            receipt["entry"] = bound(payload[name + "/entry"])
            payload[name + "/result.json"] = encoded(receipt)
        module("launch_host_build_examples", "tests/test_required_gate_idempotence_entry_build_v0.py").reseal(payload)
        chosen["entry_build"]["record_sha256"] = digest(payload["record.json"])
        # The alternate two-build record remains internally valid. Admission
        # must still require equality with the original containment entry.
        report = module("launch_host_build_examples", "tests/test_required_gate_idempotence_entry_build_v0.py").checker().check_payload(
            payload, expected_request_sha256=chosen["entry_build"]["request_sha256"],
            expected_record_sha256=chosen["entry_build"]["record_sha256"], source_commit=chosen["entry_build"]["source_commit"])
        assert report["status"] == "accepted"
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen, entry_build_payload=payload)


@pytest.mark.parametrize("compression", ["xz", "gz", "tar"])
def test_launch_host_package_accepts_realistic_directories_and_multiline_control(launch_host_case, compression):
    raw = launch_host_package(launch_host_case.fixture.launcher, compression=compression)
    report = launch_host_packages().inspect_package(raw, member_path="usr/bin/bwrap", expected_name="bubblewrap",
        expected_version=LAUNCH_HOST_VERSION, expected_architecture="amd64")
    assert report["package"] == bound(raw)
    assert report["control"] == {"name": "bubblewrap", "version": LAUNCH_HOST_VERSION, "architecture": "amd64"}
    assert report["member_bytes"] == launch_host_case.fixture.launcher
    assert report["member"] == {"path": "usr/bin/bwrap", "mode": "0755", **bound(launch_host_case.fixture.launcher)}
    assert len(report["archive_members"]) == 3 and len(report["tar_archives"]) == 2


@pytest.mark.parametrize("limit,accepted", [(5, False), (6, True)])
def test_launch_host_package_member_budget_covers_control_and_data_together(launch_host_case, monkeypatch, limit, accepted):
    package = launch_host_packages()
    # The authored control tar has two members and data tar has four. Both
    # individually fit either limit, so only a combined budget detects five.
    monkeypatch.setattr(package, "MEMBER_COUNT_LIMIT", limit)
    args = {"member_path": "usr/bin/bwrap", "expected_name": "bubblewrap",
            "expected_version": LAUNCH_HOST_VERSION, "expected_architecture": "amd64"}
    if accepted:
        report = package.inspect_package(launch_host_case.package, **args)
        assert sum(row["member_count"] for row in report["tar_archives"]) == 6
    else:
        with pytest.raises(package.PackageError) as caught:
            package.inspect_package(launch_host_case.package, **args)
        assert caught.value.code == "launcher_package_tar_member_limit"


@pytest.mark.parametrize("change", ["member_substitution", "setuid", "setgid", "non_executable", "package_hash",
                                    "version", "architecture", "member_path"])
def test_launch_host_package_identity_and_selected_executable_remain_bound(launch_host_case, change):
    chosen, raw = copy.deepcopy(launch_host_case.selection), launch_host_case.package
    if change == "member_substitution": raw = launch_host_package(b"unrelated executable bytes")
    elif change in {"setuid", "setgid", "non_executable"}:
        raw = launch_host_package(launch_host_case.fixture.launcher, mode={"setuid": 0o4755, "setgid": 0o2755, "non_executable": 0o644}[change])
    elif change == "package_hash": chosen["launcher_origin"]["package"]["sha256"] = "0" * 64
    elif change == "version": chosen["launcher_origin"]["version"] = "0.12.0-2"
    elif change == "architecture": chosen["launcher_origin"]["architecture"] = "arm64"
    else: chosen["launcher_origin"]["member_path"] = "usr/bin/other"
    if change in {"member_substitution", "setuid", "setgid", "non_executable"}:
        chosen["launcher_origin"]["package"] = bound(raw)
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen, launcher_package_bytes=raw)


@pytest.mark.parametrize("change", ["ar_magic", "ar_truncated", "ar_extra", "tar_traversal", "tar_duplicate",
                                    "selected_link", "ancestor_link", "duplicate_control", "continued_identity",
                                    "second_control_paragraph"])
def test_launch_host_package_reader_rejects_ambiguous_or_unsafe_original_archives(launch_host_case, change):
    launcher = launch_host_case.fixture.launcher
    raw = launch_host_case.package
    if change == "ar_magic": raw = b"?" + raw[1:]
    elif change == "ar_truncated": raw = raw[:-5]
    elif change == "ar_extra": raw += launch_host_ar([("extra", b"hidden")])[8:]
    elif change in {"tar_traversal", "tar_duplicate", "selected_link", "ancestor_link"}:
        rows = [("./usr/bin/bwrap", launcher, 0o755, tarfile.REGTYPE, "")]
        if change == "tar_traversal": rows.append(("../escape", b"hidden", 0o644, tarfile.REGTYPE, ""))
        elif change == "tar_duplicate": rows.append(("usr/bin/bwrap", launcher, 0o755, tarfile.REGTYPE, ""))
        elif change == "selected_link": rows = [("./usr/bin/bwrap", b"", 0o755, tarfile.SYMTYPE, "/elsewhere")]
        else: rows.insert(0, ("usr", b"", 0o755, tarfile.SYMTYPE, "/ambient"))
        raw = launch_host_package(launcher, data_rows=rows)
    else:
        control = ("Package: bubblewrap\nVersion: " + LAUNCH_HOST_VERSION + "\nArchitecture: amd64\n").encode()
        control += {"duplicate_control": b"Architecture: amd64\n", "continued_identity": b" hidden identity suffix\n",
                    "second_control_paragraph": b"\nPackage: hidden\n"}[change]
        raw = launch_host_package(launcher, control=control)
    with pytest.raises(launch_host_packages().PackageError):
        launch_host_packages().inspect_package(raw, member_path="usr/bin/bwrap", expected_name="bubblewrap",
            expected_version=LAUNCH_HOST_VERSION, expected_architecture="amd64")


@pytest.mark.parametrize("change", ["wrong_hash", "extra_source", "missing_source", "duplicate_source", "invalid_base64",
                                    "status_payload", "short_oversize", "namespace_target", "boolean_uid", "boolean_fd_count",
                                    "negative_limit", "qualification_claim", "observation_id_newline"])
def test_launch_host_observation_is_closed_raw_evidence_not_a_success_claim(launch_host_case, change):
    host, chosen = json.loads(launch_host_case.host_raw), copy.deepcopy(launch_host_case.selection)
    if change == "extra_source": host["files"].append({"path": "/proc/version", "status": "present", "data_b64": ""})
    elif change == "missing_source": host["files"].pop()
    elif change == "duplicate_source": host["files"].append(copy.deepcopy(host["files"][0]))
    elif change == "invalid_base64": host["files"][0]["data_b64"] = "@@@"
    elif change == "status_payload": host["files"][0]["status"] = "absent"
    elif change == "short_oversize": host["files"][0].update(status="oversize", data_b64="QQ==")
    elif change == "namespace_target": host["namespaces"][0]["target"] = "net:[4026531837]"
    elif change == "boolean_uid": host["identity"]["uid"] = True
    elif change == "boolean_fd_count": host["open_fd_count"] = True
    elif change == "negative_limit": host["nofile"]["soft"] = -1
    elif change == "qualification_claim": host["host_environment_qualified"] = True
    elif change == "observation_id_newline": host["observation_id"] = "a" * 32 + "\n"
    raw = encoded(host)
    chosen["host_observation"] = bound(raw)
    if change == "wrong_hash": chosen["host_observation"]["sha256"] = "0" * 64
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen, host_observation_bytes=raw)


@pytest.mark.parametrize("path,raw,status,result_id", [
    ("/proc/sys/user/max_user_namespaces", b"0\n", "present", "user_namespace_limit"),
    ("/proc/sys/kernel/unprivileged_userns_clone", b"0\n", "present", "unprivileged_userns_clone"),
    ("/proc/sys/vm/memfd_noexec", b"2\n", "present", "memfd_executable_default"),
    ("/etc/ld.so.preload", b"/ambient/injected.so\n", "present", "loader_preload"),
])
def test_launch_host_blocked_prerequisites_are_retained_without_qualification(launch_host_case, path, raw, status, result_id):
    chosen, host = launch_host_host_change(launch_host_case, path, raw, status=status)
    plan = launch_host_plan(launch_host_case, chosen=chosen, host_observation_bytes=host)
    assert next(row for row in plan["host"]["passive_prerequisites"] if row["id"] == result_id)["status"] == "blocked"
    assert plan["host_launcher_runtime_verified"] is False and plan["execution_ready"] is False


@pytest.mark.parametrize("path,raw,status,result_id", [
    ("/proc/sys/kernel/unprivileged_userns_clone", None, "absent", "unprivileged_userns_clone"),
    ("/proc/sys/kernel/apparmor_restrict_unprivileged_userns", None, "unreadable", "apparmor_unprivileged_userns"),
    ("/proc/sys/kernel/apparmor_restrict_unprivileged_userns", b"1\n", "present", "apparmor_unprivileged_userns"),
    ("/proc/sys/vm/memfd_noexec", b"77\n", "present", "memfd_executable_default"),
    ("/proc/sys/user/max_user_namespaces", b"not a number\n", "present", "user_namespace_limit"),
    ("/etc/ld.so.preload", None, "unsafe", "loader_preload"),
    ("/proc/self/status", b"NoNewPrivs:\t1\nNoNewPrivs:\t0\nSeccomp:\t2\n", "present", "observer_NoNewPrivs"),
])
def test_launch_host_unknown_prerequisites_cannot_become_positive_capability_tests(launch_host_case, path, raw, status, result_id):
    chosen, host = launch_host_host_change(launch_host_case, path, raw, status=status)
    plan = launch_host_plan(launch_host_case, chosen=chosen, host_observation_bytes=host)
    assert next(row for row in plan["host"]["passive_prerequisites"] if row["id"] == result_id)["status"] == "unknown"
    assert plan["host_launcher_runtime_verified"] is False


@pytest.mark.parametrize("change", ["headroom", "missing_fd_observation", "no_memfd", "wrong_platform"])
def test_launch_host_api_and_descriptor_preconditions_do_not_invent_readiness(launch_host_case, change):
    host, chosen = json.loads(launch_host_case.host_raw), copy.deepcopy(launch_host_case.selection)
    if change == "headroom": host["nofile"]["soft"] = 8
    elif change == "missing_fd_observation": host["open_fd_count"] = None
    elif change == "no_memfd": host["memfd_create_api"] = False
    else: host["platform"]["machine"] = "aarch64"
    raw = encoded(host)
    chosen["host_observation"] = bound(raw)
    plan = launch_host_plan(launch_host_case, chosen=chosen, host_observation_bytes=raw)
    assert any(row["status"] in {"blocked", "unknown"} for row in plan["host"]["passive_prerequisites"])
    assert plan["execution_authorized"] is False


@pytest.mark.parametrize("delta,status", [(-1, "blocked"), (0, "satisfied")])
def test_launch_host_descriptor_threshold_uses_observed_open_fds_and_reconstructed_view(launch_host_case, delta, status):
    host, chosen = json.loads(launch_host_case.host_raw), copy.deepcopy(launch_host_case.selection)
    needed = len(json.loads(launch_host_case.containment.request_bytes)["files"]) + 16 + host["open_fd_count"]
    host["nofile"]["soft"] = needed + delta
    raw = encoded(host)
    chosen["host_observation"] = bound(raw)
    plan = launch_host_plan(launch_host_case, chosen=chosen, host_observation_bytes=raw)
    observed = next(row for row in plan["host"]["passive_prerequisites"] if row["id"] == "descriptor_headroom")
    assert observed["status"] == status and observed["value"]["required_soft_limit"] == needed
    assert plan["execution_ready"] is False


@pytest.mark.parametrize("change", ["pending", "native", "host", "authority"])
def test_launch_host_checker_reconstructs_original_relations_after_plan_rehashing(launch_host_case, change):
    c, args = launch_host_checker(), launch_host_arguments(launch_host_case)
    plan = json.loads(c.derive_plan(**args))
    if change == "pending": plan["pending_obligations"] = []
    elif change == "native": plan["native"]["bindings"] = []
    elif change == "host": plan["host"]["passive_prerequisites"][0]["status"] = "invented"
    else: plan["execution_authorized"] = True
    raw = encoded(plan)
    with pytest.raises(c.HostError):
        c.verify_plan(plan_bytes=raw, expected_plan_sha256=digest(raw), **args)


def test_launch_host_prepared_wrapper_cannot_replace_original_evidence(launch_host_case):
    p, c = launch_host_subject(), launch_host_checker()
    prepared = p.prepare_launch_host(**launch_host_arguments(launch_host_case))
    altered = json.loads(prepared.plan_bytes)
    altered["pending_obligations"] = []
    raw = encoded(altered)
    object.__setattr__(prepared, "plan_bytes", raw)
    with pytest.raises(c.HostError):
        p.verify_launch_host(prepared, plan_bytes=raw, expected_plan_sha256=digest(raw))


def test_launch_host_readmits_containment_instead_of_trusting_a_rehashed_request(launch_host_case):
    prepared = subject().prepare_containment(**dict(launch_host_case.containment.inputs))
    altered = json.loads(prepared.request_bytes)
    altered["phase"] = "collector"
    raw = encoded(altered)
    object.__setattr__(prepared, "request_bytes", raw)
    chosen = copy.deepcopy(launch_host_case.selection)
    chosen["containment_request_sha256"] = digest(raw)
    with pytest.raises(launch_host_checker().HostError):
        launch_host_plan(launch_host_case, chosen=chosen, containment_prepared=prepared,
                         expected_containment_request_sha256=digest(raw))


def test_launch_host_passive_observer_reads_only_fixed_sources_once(monkeypatch):
    p, observed = launch_host_subject(), launch_host_observation()
    file_rows = {row["path"]: row for row in observed["files"]}
    namespace_rows = {row["name"]: row for row in observed["namespaces"]}
    files, namespaces = [], []
    def read_file(path):
        files.append(path)
        return copy.deepcopy(file_rows[path])
    def read_namespace(name):
        namespaces.append(name)
        return copy.deepcopy(namespace_rows[name])
    def forbidden(*args, **kwargs):
        raise AssertionError("passive observer attempted child execution")
    monkeypatch.setattr(p, "_read_host_file", read_file)
    monkeypatch.setattr(p, "_namespace", read_namespace)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    raw = p.observe_host()
    result = json.loads(raw)
    assert files == list(p.HOST_PATHS) and len(files) == len(set(files)) == 6
    assert namespaces == list(p.NAMESPACES) and len(namespaces) == len(set(namespaces)) == 7
    assert len(result["observation_id"]) == 32 and raw == encoded(result)
    assert "host_environment_qualified" not in result and "execution_ready" not in result


@pytest.mark.parametrize("error,expected", [(errno.ENOENT, "absent"), (errno.EACCES, "unreadable"), (errno.ELOOP, "unsafe")])
def test_launch_host_passive_read_failures_are_explicit(monkeypatch, error, expected):
    p = launch_host_subject()
    def fail(*args, **kwargs): raise OSError(error, "authored read failure")
    monkeypatch.setattr(os, "open", fail)
    assert p._read_host_file("/etc/ld.so.preload") == {"path": "/etc/ld.so.preload", "status": expected, "data_b64": None}


def test_launch_host_passive_reader_caps_bytes_and_closes_descriptor(monkeypatch):
    p, requested, closed = launch_host_subject(), [], []
    source = io.BytesIO(b"A" * (p.HOST_READ_LIMIT + 100))
    real_open, real_fstat, real_read, real_close = os.open, os.fstat, os.read, os.close
    with monkeypatch.context() as patch:
        patch.setattr(os, "open", lambda path, *args, **kwargs:
                      123456 if path == "/proc/self/status" else real_open(path, *args, **kwargs))
        patch.setattr(os, "fstat", lambda fd: SimpleNamespace(st_mode=stat.S_IFREG | 0o444)
                      if fd == 123456 else real_fstat(fd))
        def read(fd, size):
            if fd != 123456:
                return real_read(fd, size)
            requested.append(size)
            return source.read(size)
        patch.setattr(os, "read", read)
        patch.setattr(os, "close", lambda fd: closed.append(fd) if fd == 123456 else real_close(fd))
        row = p._read_host_file("/proc/self/status")
    assert row["status"] == "oversize" and len(base64.b64decode(row["data_b64"])) == p.HOST_READ_LIMIT
    assert source.tell() == p.HOST_READ_LIMIT + 1 and max(requested) <= 4096 and closed == [123456]


def test_launch_host_passive_sources_cannot_be_expanded_by_caller(monkeypatch):
    p = launch_host_subject()
    def forbidden(*args, **kwargs): raise AssertionError("unselected source was accessed")
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(os, "readlink", forbidden)
    with pytest.raises(launch_host_checker().HostError): p._read_host_file("/tmp/unselected")
    with pytest.raises(launch_host_checker().HostError): p._namespace("../unselected")


def launch_host_cli_inputs(case, directory):
    args, prepared = cli_inputs(case.fixture, directory / "originals")
    chosen = copy.deepcopy(case.selection)
    chosen["containment_request_sha256"] = digest(prepared.request_bytes)
    next(row for row in chosen["native_files"] if row["role"] == "launcher")["host_path"] = str(directory / "originals/launcher")
    request = directory / "containment-request.json"
    request.write_bytes(prepared.request_bytes)
    chosen_raw = encoded(chosen)
    selection_path = directory / "launch-host-selection.json"
    selection_path.write_bytes(chosen_raw)
    build_root = directory / "entry-build"
    for name, raw in case.entry_payload.items():
        path = build_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    native_root = directory / "native"
    for name, raw in case.native.items():
        path = native_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    package_path, observation_path = directory / "launcher.deb", directory / "host-observation.json"
    package_path.write_bytes(case.package)
    observation_path.write_bytes(case.host_raw)
    args += ["--containment-request", str(request), "--containment-request-sha256", digest(prepared.request_bytes),
             "--launch-host-selection", str(selection_path), "--launch-host-selection-sha256", digest(chosen_raw),
             "--entry-build-directory", str(build_root), "--native-root", str(native_root),
             "--launcher-package", str(package_path), "--host-observation", str(observation_path)]
    return args, native_root


def test_launch_host_cli_preserves_and_independently_checks_exact_plan_bytes(launch_host_case, tmp_path):
    args, _ = launch_host_cli_inputs(launch_host_case, tmp_path)
    path = tmp_path / "plan.json"
    created = subprocess.run([sys.executable, str(LAUNCH_HOST_TOOL), "prepare", *args, "--output", str(path)],
                             capture_output=True, timeout=30)
    assert created.returncode == 0, created.stdout.decode() + created.stderr.decode()
    raw = path.read_bytes()
    checked = subprocess.run([sys.executable, str(LAUNCH_HOST_TOOL), "check", *args, "--plan", str(path),
                              "--plan-sha256", digest(raw)], capture_output=True, timeout=30)
    assert checked.returncode == 0, checked.stdout.decode() + checked.stderr.decode()
    assert created.stdout == checked.stdout and path.read_bytes() == raw
    assert json.loads(checked.stdout)["status"] == "accepted"


def test_launch_host_checker_direct_invocation_requires_original_inputs():
    result = subprocess.run([sys.executable, str(ROOT / "tools/check_required_gate_idempotence_launch_host_v0.py")],
                            capture_output=True, timeout=15)
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "rejected"


@pytest.mark.parametrize("change", ["extra_file", "extra_directory", "symlink", "hardlink", "root_symlink", "existing_output"])
def test_launch_host_cli_refuses_native_substitution_and_output_replacement(launch_host_case, tmp_path, change):
    args, native_root = launch_host_cli_inputs(launch_host_case, tmp_path)
    target, output = native_root / "native/bwrap", tmp_path / "plan.json"
    if change == "extra_file": (native_root / "unselected").write_bytes(b"extra")
    elif change == "extra_directory": (native_root / "unselected").mkdir()
    elif change in {"symlink", "hardlink"}:
        outside = tmp_path / "outside-launcher"
        outside.write_bytes(target.read_bytes())
        target.unlink()
        if change == "symlink": target.symlink_to(outside)
        else: os.link(outside, target)
    elif change == "root_symlink":
        moved = native_root.with_name("moved-native")
        native_root.rename(moved)
        native_root.symlink_to(moved, target_is_directory=True)
    else: output.write_bytes(b"preserve original output\n")
    result = subprocess.run([sys.executable, str(LAUNCH_HOST_TOOL), "prepare", *args, "--output", str(output)],
                            capture_output=True, timeout=30)
    assert result.returncode == 1, result.stdout.decode() + result.stderr.decode()
    assert json.loads(result.stdout)["status"] == "rejected"
    if change == "existing_output": assert output.read_bytes() == b"preserve original output\n"
    else: assert not output.exists()


# Distribution authentication extends the same passive boundary. The following
# RSA key and detached signature are public authored test data, never operational
# credentials. Their private key was discarded after fixture authoring. Only the
# explicitly hash-bound verifier (or a small authored capture child) may run.
DISTRIBUTION_TOOL = ROOT / "tools/required_gate_idempotence_launcher_distribution_v0.py"
DISTRIBUTION_CREATED = 1767229200
DISTRIBUTION_EVALUATION = 1767232800
DISTRIBUTION_FINGERPRINT = "A72AC1F3E2671BFF31AF873C77FE94169196DC10"
DISTRIBUTION_KEYRING_B64 = (
    "xv8AAAENBGlVuQABCACpgGE/QYAwK0uWPr2xgcy4keSbHSFPrhnC8HdC/M3QB+EGLCnztLRcL3ftNtjiKSEaY3TuqQcApNHJ"
    "FlX0RM+Zk7JXiq50zFJIXl6lOydIOC/wCuFOcD3jBBFR5QW3qt5YRaobMlILrYnV/g9DGrb/f90MsdJ7LViSYHyU5cmCKxSp"
    "RBsTEQVl1UDibDWk5Oy8QU4WDa0VEp9ym3sTTjChHsXxhA/f1IRYzWedvDy7OgJTm/kON8nGBtaGepvnf1xe/tV6DIRJ0to3"
    "NfSGbMZb55WOAnZ4Y+AcTD22ASk8C26mkw7XQUPWNWoTg5FB/qfG8GK3rsrlsAXAIEx6Ug2JABEBAAHN/wAAAEBBdXRob3Jl"
    "ZCBkaXN0cmlidXRpb24gdGVzdCBmaXh0dXJlIDxuby1pZGVudGl0eUBleGFtcGxlLmludmFsaWQ+wv8AAAE2BBMBCAAgBQJp"
    "VbkAFiEEpyrB8+JnG/8xr4c8d/6UFpGW3BACGwMACgkQd/6UFpGW3BCqBwf/XEa1d4a2DxauicXwOPoJB1Eb1wfb+K0lTu92"
    "W7mfNktCbVqEdhNX77wsSMeBW3z5PX1dThfPedylyJwP4N5WRROFmhhUQyav/NTV4r3ouNsyS4VOCnfhhOz1EZJEZGgy2915"
    "WlkR9PftjrDETJ/UWWeyiSQbLvSXcaimkyLr6a2O2bwFC6i9YBPcz5pdw0XJXm4ihBlNMFQe5ZQOso8I1uYA2UshJ84TMt6D"
    "Dok6Qt+R+glGOshXRVpNDojwbpICMVeVnyX3SL4cByfIAuMsvlgXI9vFI+WbApn1RuRQQBNFxoamy60Tk5G2JXnuMZQLwPhP"
    "tALtf6C2EkB8BaYl3w=="
)
DISTRIBUTION_SIGNATURE_B64 = (
    "wv8AAAEzBAABCAAdBQJpVccQFiEEpyrB8+JnG/8xr4c8d/6UFpGW3BAACgkQd/6UFpGW3BCvmQf/bpUVqHkW39lfPw/VXhoO"
    "kNlJEd7j8I2kykW5ctpQDWpS0bw3M+RTiYniBC8uixCIMq4B3ryp91QYn3LLdhGjglt53UjHEaTarnaoSLb3S1Z7El2uZR2p"
    "zxDHgyAwfTWykvfnQznyofdlaM7X8F+w5DmHuBa1dPXiplWKxRi+dp0rDlmIcRDTLxPRFV4WRCPmO9f/WHErvtq4bhO2CdZ3"
    "o3lNaGJRBxbKs8iUDTkZIidYJiFGNTLBR7RKXMBsBPo7oxPE258AKr0jrFYY84k+9/JKTAu/dQkeOSgNQGU+GTUOMY3AUQUc"
    "5AsQ/7B1XPhGXGaE/HhHnkd80LXGvgW/9A=="
)


def distribution_checker():
    return module("check_required_gate_idempotence_launcher_distribution_v0",
                  "tools/check_required_gate_idempotence_launcher_distribution_v0.py")


def distribution_metadata():
    return module("required_gate_idempotence_debian_metadata_v0",
                  "tools/required_gate_idempotence_debian_metadata_v0.py")


def distribution_signature():
    return module("required_gate_idempotence_distribution_signature_v0",
                  "tools/required_gate_idempotence_distribution_signature_v0.py")


def distribution_documents(package):
    paragraph = (f"Package: bubblewrap\nVersion: {LAUNCH_HOST_VERSION}\nArchitecture: amd64\n"
                 f"Filename: pool/main/b/bubblewrap/bubblewrap_{LAUNCH_HOST_VERSION}_amd64.deb\n"
                 f"Size: {len(package)}\nSHA256: {digest(package)}\nDescription: Authored public fixture\n"
                 " continuation retained in the entire selected index\n")
    unselected = ("Package: unrelated\nVersion: 1\nArchitecture: all\n"
                  "Filename: pool/main/u/unrelated/unrelated_1_all.deb\nSize: 1\nSHA256: "
                  + "b" * 64 + "\nDescription: Unselected authored paragraph\n")
    decoded = (unselected + "\n" + paragraph + "\n").encode()
    compressed = lzma.compress(decoded)
    release = ("Origin: Authored\nLabel: Authored launcher fixture\nSuite: stable\nCodename: fixture\nVersion: 1\n"
               "Date: Thu, 01 Jan 2026 00:00:00 UTC\nValid-Until: Fri, 02 Jan 2026 00:00:00 UTC\n"
               "Architectures: amd64 arm64\nComponents: main contrib\nDescription: Public authored repository\n"
               "SHA256:\n"
               f" {digest(compressed)} {len(compressed)} main/binary-amd64/Packages.xz\n"
               f" {digest(decoded)} {len(decoded)} main/binary-amd64/Packages\n").encode()
    return release, compressed, decoded


@pytest.fixture(scope="module")
def distribution_case(launch_host_case):
    c = distribution_checker()
    old_inputs = launch_host_arguments(launch_host_case)
    old_plan = launch_host_checker().derive_plan(**old_inputs)
    release, compressed, decoded = distribution_documents(launch_host_case.package)
    assert digest(release) == "faf8bad56c1185eb2dd01b9ea9f737a0241738cf40dac9d179e97008857a574d"
    keyring = base64.b64decode(DISTRIBUTION_KEYRING_B64, validate=True)
    signature = base64.b64decode(DISTRIBUTION_SIGNATURE_B64, validate=True)
    verifier = Path("/usr/bin/gpg")
    assert verifier.is_file() and not verifier.is_symlink(), "the explicit test verification tool is required"
    trust = {
        "record_type": "required_gate_idempotence_distribution_trust_policy_v0", "profile": c.TRUST_PROFILE,
        "keyring": bound(keyring), "verifier": {"kind": "gpg", "path": str(verifier), **bound(verifier.read_bytes())},
        "required_signers": [{"signing_fingerprint": DISTRIBUTION_FINGERPRINT,
                              "primary_fingerprint": DISTRIBUTION_FINGERPRINT}],
        "evaluation_time": DISTRIBUTION_EVALUATION, "max_release_age_seconds": 86400, "require_valid_until": True,
    }
    selection = {
        "record_type": "required_gate_idempotence_launcher_distribution_selection_v0", "profile": c.PROFILE,
        "record_status": "example", "launch_host_plan": bound(old_plan), "trust_policy": bound(encoded(trust)),
        "release": bound(release), "release_signature": bound(signature),
        "repository": {"origin": "Authored", "label": "Authored launcher fixture", "suite": "stable",
                       "codename": "fixture", "version": "1", "component": "main", "architecture": "amd64"},
        "index": {"compressed": {"path": "main/binary-amd64/Packages.xz", **bound(compressed)},
                  "decoded": {"path": "main/binary-amd64/Packages", **bound(decoded)}},
        "package": {"name": "bubblewrap", "version": LAUNCH_HOST_VERSION, "architecture": "amd64",
                    "filename": f"pool/main/b/bubblewrap/bubblewrap_{LAUNCH_HOST_VERSION}_amd64.deb",
                    **bound(launch_host_case.package)}, **c.BOUNDARY,
    }
    return SimpleNamespace(host=launch_host_case, host_inputs=old_inputs, host_plan=old_plan,
                           release=release, compressed=compressed, decoded=decoded, keyring=keyring,
                           signature=signature, verifier=verifier, trust=trust, selection=selection)


def distribution_arguments(case, *, selection=None, trust=None, **changes):
    chosen_trust = case.trust if trust is None else trust
    chosen = copy.deepcopy(case.selection if selection is None else selection)
    if trust is not None:
        chosen["trust_policy"] = bound(encoded(chosen_trust))
    result = {
        "launch_host_inputs": dict(case.host_inputs), "launch_host_plan_bytes": case.host_plan,
        "expected_launch_host_plan_sha256": digest(case.host_plan), "selection_bytes": encoded(chosen),
        "expected_selection_sha256": digest(encoded(chosen)), "trust_policy_bytes": encoded(chosen_trust),
        "expected_trust_policy_sha256": digest(encoded(chosen_trust)), "release_bytes": case.release,
        "release_signature_bytes": case.signature, "packages_xz_bytes": case.compressed,
        "keyring_bytes": case.keyring, "verifier_path": case.verifier,
    }
    result.update(changes)
    return result


def distribution_metadata_arguments(case, *, decoded=None, compressed=None, **changes):
    index = copy.deepcopy(case.selection["index"])
    release = case.release
    if decoded is not None or compressed is not None:
        decoded = case.decoded if decoded is None else decoded
        compressed = lzma.compress(decoded) if compressed is None else compressed
        for role, raw in (("compressed", compressed), ("decoded", decoded)):
            old = index[role]
            release = release.replace(f" {old['sha256']} {old['size_bytes']} {old['path']}\n".encode(),
                                      f" {digest(raw)} {len(raw)} {old['path']}\n".encode())
            old.update(bound(raw))
    result = {"release_bytes": release, "packages_xz_bytes": case.compressed if compressed is None else compressed,
              "repository": copy.deepcopy(case.selection["repository"]), "index": index,
              "package": copy.deepcopy(case.selection["package"]),
              "evaluation_time": DISTRIBUTION_EVALUATION, "max_release_age_seconds": 86400,
              "require_valid_until": True}
    result.update(changes)
    return result


def distribution_signature_arguments(case, **changes):
    result = {"release_bytes": case.release, "signature_bytes": case.signature, "keyring_bytes": case.keyring,
              "expected_keyring_sha256": digest(case.keyring), "verifier_path": case.verifier,
              "expected_verifier": copy.deepcopy(case.trust["verifier"]),
              "required_signers": copy.deepcopy(case.trust["required_signers"]),
              "evaluation_time": DISTRIBUTION_EVALUATION}
    result.update(changes)
    return result


def distribution_status(*, signing=DISTRIBUTION_FINGERPRINT, primary=DISTRIBUTION_FINGERPRINT,
                        created=DISTRIBUTION_CREATED, expires=0, public=1, digest_algorithm=8,
                        version=4, kind="00"):
    return (f"[GNUPG:] NEWSIG\n[GNUPG:] KEY_CONSIDERED {primary} 0\n"
            f"[GNUPG:] GOODSIG {signing[-16:]} Authored identity has no authority\n"
            f"[GNUPG:] VALIDSIG {signing} 2026-01-01 {created} {expires} {version} 0 "
            f"{public} {digest_algorithm} {kind} {primary}\n[GNUPG:] TRUST_UNDEFINED 0 pgp\n").encode()


def distribution_capture_result(**changes):
    process = {"pid": 12345, "exit_code": 0, "timed_out": False, "output_limited": False,
               "limited_streams": [], "capture_complete": True, "error_code": None,
               "started_monotonic_ns": 1, "completed_monotonic_ns": 2}
    process.update(changes)
    return {"stdout_bytes": distribution_status(), "stderr_bytes": b"authored diagnostic\n", "process_record": process}


def test_distribution_full_original_chain_is_canonical_and_keeps_existing_boundary(distribution_case):
    c, case = distribution_checker(), distribution_case
    captures = []
    args = distribution_arguments(case, signature_evidence_sink=captures.append)
    first, second = c.derive_record(**args), c.derive_record(**args)
    assert first == second == encoded(json.loads(first))
    report = c.verify_record(record_bytes=first, expected_record_sha256=digest(first), **args)
    assert report["status"] == "accepted" and len(captures) == 3
    for name in ("distribution_signature_verified", "release_index_binding_verified", "index_package_binding_verified",
                 "package_launcher_binding_verified", "launcher_distribution_authenticated"):
        assert report[name] is True, name
    for value in (json.loads(first), report):
        for name, expected in c.BOUNDARY.items():
            assert type(value[name]) is type(expected) and value[name] == expected, name
    assert launch_host_checker().derive_plan(**case.host_inputs) == case.host_plan
    assert json.loads(case.host_plan)["launcher_origin_authenticated"] is False
    assert all(item["process_record"]["verification_status"] == "accepted" for item in captures)


@pytest.mark.parametrize("key", ["expected_selection_sha256", "expected_trust_policy_sha256",
                                "expected_launch_host_plan_sha256"])
def test_distribution_external_anchors_fail_before_verifier(distribution_case, monkeypatch, key):
    def forbidden(*args, **kwargs):
        pytest.fail("an invalid external anchor must reject before verifier execution")
    monkeypatch.setattr(distribution_signature(), "verify_detached", forbidden)
    with pytest.raises(distribution_checker().DistributionError):
        distribution_checker().derive_record(**distribution_arguments(distribution_case, **{key: "0" * 64}))


@pytest.mark.parametrize("key", ["release_bytes", "release_signature_bytes", "packages_xz_bytes",
                                "keyring_bytes", "launch_host_plan_bytes"])
def test_distribution_original_replacement_cannot_borrow_retained_bindings(distribution_case, key):
    args = distribution_arguments(distribution_case)
    args[key] += b"replacement"
    with pytest.raises(distribution_checker().DistributionError):
        distribution_checker().derive_record(**args)


@pytest.mark.parametrize("path,replacement", [
    (("unexpected",), True), (("record_status",), "observed"), (("execution_authorized",), True),
    (("distribution_trust_freshness_verified",), True), (("verifier_runtime_closure_verified",), True),
    (("release", "size_bytes"), True), (("index", "decoded", "path"), "main/../Packages"),
    (("index", "compressed", "path"), "main/binary-amd64/Packages.gz"),
    (("package", "filename"), "pool/../bubblewrap.deb"), (("package", "filename"), "/pool/bubblewrap.deb"),
    (("package", "sha256"), "f" * 63), (("repository", "component"), "main/../contrib"),
])
def test_distribution_selection_is_closed_and_strict(distribution_case, path, replacement):
    c, chosen = distribution_checker(), copy.deepcopy(distribution_case.selection)
    parent = chosen
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    raw = encoded(chosen)
    with pytest.raises(c.DistributionError):
        c.validate_selection(raw, digest(raw))


@pytest.mark.parametrize("path,replacement", [
    (("threshold",), 1), (("evaluation_time",), True), (("evaluation_time",), 0),
    (("evaluation_time",), 4102444801), (("max_release_age_seconds",), True),
    (("max_release_age_seconds",), 0), (("max_release_age_seconds",), 31622401),
    (("require_valid_until",), 1), (("keyring", "size_bytes"), True),
    (("verifier", "kind"), "shell"), (("verifier", "path"), "gpg"),
    (("verifier", "path"), "/usr/bin/../bin/gpg"), (("required_signers",), []),
    (("required_signers",), [{"signing_fingerprint": "7" * 16, "primary_fingerprint": DISTRIBUTION_FINGERPRINT}]),
    (("required_signers",), [{"signing_fingerprint": DISTRIBUTION_FINGERPRINT.lower(),
                             "primary_fingerprint": DISTRIBUTION_FINGERPRINT}]),
])
def test_distribution_trust_policy_cannot_relax_fixed_verification_rules(distribution_case, path, replacement):
    c, trust = distribution_checker(), copy.deepcopy(distribution_case.trust)
    parent = trust
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    raw = encoded(trust)
    with pytest.raises(c.DistributionError):
        c.validate_trust_policy(raw, digest(raw))


def test_distribution_duplicate_signer_pair_is_not_an_extra_authorization(distribution_case):
    c, trust = distribution_checker(), copy.deepcopy(distribution_case.trust)
    trust["required_signers"] *= 2
    raw = encoded(trust)
    with pytest.raises(c.DistributionError):
        c.validate_trust_policy(raw, digest(raw))


def test_distribution_metadata_retains_both_full_indexes_and_all_paragraphs(distribution_case):
    case = distribution_case
    result = distribution_metadata().inspect_metadata(**distribution_metadata_arguments(case))
    assert result["index"]["compressed"] == case.selection["index"]["compressed"]
    assert result["index"]["decoded"] == case.selection["index"]["decoded"]
    assert result["index"]["package_paragraphs"] == 2
    assert result["package"] == case.selection["package"]
    assert result["release"]["date_epoch"] == 1767225600
    assert result["release"]["valid_until_epoch"] == 1767312000


@pytest.mark.parametrize("old,new", [
    (b"Origin: Authored\n", b"Origin: Authored\norigin: Authored\n"),
    (b"Origin: Authored\n", b"Origin: Authored\n extra identity\n"),
    (b"Origin: Authored\n", b"Origin: Other\n"),
    (b"Architectures: amd64 arm64", b"Architectures: arm64"),
    (b"Components: main contrib", b"Components: contrib"),
    (b"Date: Thu, 01 Jan 2026 00:00:00 UTC", b"Date: malformed"),
    (b"Version: 1\n", b"Version: 1\r\n"),
    (b"Description: Public authored repository", b"Description: bad\x00value"),
    (b"SHA256:\n", b"SHA256:\n nonsense\n"),
    (b"main/binary-amd64/Packages.xz", b"main/../Packages.xz"),
])
def test_distribution_signed_release_ambiguity_and_identity_mismatches_reject(distribution_case, old, new):
    m, case = distribution_metadata(), distribution_case
    assert old in case.release
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**distribution_metadata_arguments(case, release_bytes=case.release.replace(old, new)))


@pytest.mark.parametrize("kind", ["duplicate", "zero_prefix", "wrong_digest", "wrong_size", "missing_decoded"])
def test_distribution_release_sha256_rows_are_unique_canonical_and_complete(distribution_case, kind):
    m, case = distribution_metadata(), distribution_case
    descriptor = case.selection["index"]["decoded"]
    row = f" {descriptor['sha256']} {descriptor['size_bytes']} {descriptor['path']}\n".encode()
    replacement = {"duplicate": row + row, "zero_prefix": row.replace(f" {len(case.decoded)} ".encode(),
                                                                       f" 0{len(case.decoded)} ".encode()),
                   "wrong_digest": row.replace(descriptor["sha256"].encode(), b"0" * 64),
                   "wrong_size": row.replace(f" {len(case.decoded)} ".encode(), b" 1 "),
                   "missing_decoded": b""}[kind]
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**distribution_metadata_arguments(case, release_bytes=case.release.replace(row, replacement)))


@pytest.mark.parametrize("old,new", [
    (b"Package: bubblewrap\n", b"Package: bubblewrap\npackage: bubblewrap\n"),
    (b"Package: unrelated\n", b"Package: unrelated\npackage: unrelated\n"),
    (b"Package: unrelated\n", b"malformed unselected paragraph\n"),
    (b"Architecture: amd64\n", b"Architecture: arm64\n"),
    (b"Filename: pool/main/b/bubblewrap/", b"Filename: pool/../b/bubblewrap/"),
    (b"Description: Unselected authored paragraph", b"Description: bad\x00value"),
    (b"Version: 1\n", b"Version: 1\r\n"),
])
def test_distribution_entire_decoded_index_is_parsed_before_selected_package_acceptance(distribution_case, old, new):
    m, case = distribution_metadata(), distribution_case
    assert old in case.decoded
    args = distribution_metadata_arguments(case, decoded=case.decoded.replace(old, new))
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**args)


def test_distribution_duplicate_selected_paragraph_rejects_even_when_identical(distribution_case):
    m, case = distribution_metadata(), distribution_case
    selected = case.decoded.split(b"\n\n")[1] + b"\n\n"
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**distribution_metadata_arguments(case, decoded=case.decoded + selected))


@pytest.mark.parametrize("kind", ["truncated", "trailing", "concatenated"])
def test_distribution_compressed_index_has_one_complete_xz_stream(distribution_case, kind):
    m, case = distribution_metadata(), distribution_case
    compressed = {"truncated": case.compressed[:-4], "trailing": case.compressed + b"trailing",
                  "concatenated": case.compressed + lzma.compress(b"unselected tail")}[kind]
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**distribution_metadata_arguments(case, compressed=compressed))


@pytest.mark.parametrize("evaluation,max_age,accepted", [
    (1767225600, 1, True), (1767225599, 86400, False), (1767232800, 7200, True),
    (1767232800, 7199, False), (1767311999, 86400, True), (1767312000, 86400, True),
    (1767312001, 86401, False),
])
def test_distribution_release_time_uses_only_explicit_epoch_and_exact_boundaries(distribution_case, evaluation, max_age, accepted):
    m = distribution_metadata()
    args = distribution_metadata_arguments(distribution_case, evaluation_time=evaluation, max_release_age_seconds=max_age)
    if accepted:
        assert m.inspect_metadata(**args)["release"]["date_epoch"] == 1767225600
    else:
        with pytest.raises(m.MetadataError):
            m.inspect_metadata(**args)


def test_distribution_missing_valid_until_requires_an_explicit_policy_choice(distribution_case):
    m, case = distribution_metadata(), distribution_case
    raw = case.release.replace(b"Valid-Until: Fri, 02 Jan 2026 00:00:00 UTC\n", b"")
    with pytest.raises(m.MetadataError):
        m.inspect_metadata(**distribution_metadata_arguments(case, release_bytes=raw))
    result = m.inspect_metadata(**distribution_metadata_arguments(case, release_bytes=raw, require_valid_until=False))
    assert result["release"]["valid_until_epoch"] is None


def test_distribution_signature_real_verifier_uses_only_sealed_bound_originals(distribution_case, monkeypatch):
    sig, case = distribution_signature(), distribution_case
    captures, calls = [], []
    original = sig._capture
    expected_raw = [case.verifier.read_bytes(), case.keyring, case.signature, case.release]
    def capture(**kwargs):
        argv = kwargs["argv"]
        assert argv[0] == str(case.verifier) and argv[-3] == "--verify"
        assert argv[argv.index("--faked-system-time") + 1] == str(DISTRIBUTION_EVALUATION) + "!"
        assert set(("--no-options", "--no-default-keyring", "--no-auto-key-retrieve", "--no-auto-key-import",
                    "--no-autostart", "--disable-dirmngr", "--batch", "--no-tty")).issubset(argv)
        assert "--import" not in argv and "--recv-keys" not in argv and "--ignore-time-conflict" not in argv
        assert len(kwargs["pass_fds"]) == 4 and kwargs["executable_fd"] == kwargs["pass_fds"][0]
        for descriptor, raw in zip(kwargs["pass_fds"], expected_raw):
            # Some supported CPython builds omit the Linux constants while the
            # kernel exposes the same fixed seal ABI used by the verifier.
            seals = fcntl.fcntl(descriptor, getattr(fcntl, "F_GET_SEALS", 1034))
            required = (getattr(fcntl, "F_SEAL_SEAL", 1) | getattr(fcntl, "F_SEAL_SHRINK", 2)
                        | getattr(fcntl, "F_SEAL_GROW", 4) | getattr(fcntl, "F_SEAL_WRITE", 8))
            assert seals & required == required
            assert os.pread(descriptor, len(raw) + 1, 0) == raw
        assert Path(kwargs["directory"]).stat().st_mode & 0o077 == 0
        calls.append(tuple(argv))
        return original(**kwargs)
    monkeypatch.setattr(sig, "_capture", capture)
    result = sig.verify_detached(**distribution_signature_arguments(case, evidence_sink=captures.append))
    assert len(calls) == len(captures) == 1
    assert result["backend"] == case.trust["verifier"]
    assert result["verified_signatures"][0]["signing_fingerprint"] == DISTRIBUTION_FINGERPRINT
    record = captures[0]["process_record"]
    assert record["inputs"] == {"release": bound(case.release), "signature": bound(case.signature), "keyring": bound(case.keyring)}
    assert record["verification_status"] == "accepted" and record["execution"] == "sealed_verifier_memfd"
    assert record["verifier_runtime_closure_verified"] is False


@pytest.mark.parametrize("key", ["release_bytes", "signature_bytes"])
def test_distribution_actual_crypto_rejects_changed_originals_and_preserves_diagnostics(distribution_case, key):
    sig = distribution_signature()
    args = distribution_signature_arguments(distribution_case)
    args[key] = args[key][:-1] + bytes([args[key][-1] ^ 1])
    evidence = []
    with pytest.raises(sig.SignatureError):
        sig.verify_detached(**args, evidence_sink=evidence.append)
    assert len(evidence) == 1 and evidence[0]["stderr_bytes"]
    assert evidence[0]["process_record"]["verification_status"] == "rejected"


@pytest.mark.parametrize("key", ["expected_keyring_sha256", "expected_verifier"])
def test_distribution_verifier_and_keyring_substitution_fail_before_spawn(distribution_case, monkeypatch, key):
    sig, args = distribution_signature(), distribution_signature_arguments(distribution_case)
    args[key] = "0" * 64 if key == "expected_keyring_sha256" else {**args[key], "sha256": "0" * 64}
    def forbidden(**kwargs):
        pytest.fail("unbound verification inputs must not execute")
    monkeypatch.setattr(sig, "_capture", forbidden)
    with pytest.raises(sig.SignatureError):
        sig.verify_detached(**args)


@pytest.mark.parametrize("changes", [
    {"public": 17}, {"digest_algorithm": 2}, {"version": 3}, {"kind": "01"},
    {"created": DISTRIBUTION_EVALUATION + 1}, {"expires": DISTRIBUTION_EVALUATION},
    {"expires": DISTRIBUTION_CREATED - 1}, {"primary": "1" * 40}, {"signing": "2" * 40},
])
def test_distribution_status_rejects_unselected_signers_formats_algorithms_and_times(distribution_case, changes):
    sig = distribution_signature()
    with pytest.raises(sig.SignatureError):
        sig._parse_status(distribution_status(**changes), distribution_case.trust["required_signers"], DISTRIBUTION_EVALUATION)


@pytest.mark.parametrize("status", ["BADSIG", "ERRSIG", "EXPSIG", "EXPKEYSIG", "REVKEYSIG", "NO_PUBKEY",
                                  "NODATA", "FAILURE", "ERROR", "KEYEXPIRED", "SIGEXPIRED", "KEYREVOKED", "UNKNOWN_STATUS"])
def test_distribution_one_good_signature_cannot_hide_any_failed_or_unknown_group(distribution_case, status):
    sig = distribution_signature()
    raw = distribution_status() + f"[GNUPG:] NEWSIG\n[GNUPG:] {status} diagnostic\n".encode()
    with pytest.raises(sig.SignatureError):
        sig._parse_status(raw, distribution_case.trust["required_signers"], DISTRIBUTION_EVALUATION)


@pytest.mark.parametrize("kind", ["missing_newsig", "missing_good", "missing_valid", "duplicate_good",
                                  "duplicate_valid", "duplicate_group", "extra_noise", "wrong_date", "no_newline"])
def test_distribution_status_group_grammar_cannot_combine_partial_observations(distribution_case, kind):
    sig, raw = distribution_signature(), distribution_status()
    lines = raw.splitlines(keepends=True)
    good = next(line for line in lines if b" GOODSIG " in line)
    valid = next(line for line in lines if b" VALIDSIG " in line)
    changed = {"missing_newsig": raw.replace(b"[GNUPG:] NEWSIG\n", b""),
               "missing_good": raw.replace(good, b""), "missing_valid": raw.replace(valid, b""),
               "duplicate_good": raw.replace(good, good + good), "duplicate_valid": raw.replace(valid, valid + valid),
               "duplicate_group": raw + raw, "extra_noise": b"success\n" + raw,
               "wrong_date": raw.replace(b"2026-01-01", b"2026-01-02"), "no_newline": raw[:-1]}[kind]
    with pytest.raises(sig.SignatureError):
        sig._parse_status(changed, distribution_case.trust["required_signers"], DISTRIBUTION_EVALUATION)


def test_distribution_full_subkey_primary_pair_and_exact_roster_are_required():
    sig = distribution_signature()
    first = {"signing_fingerprint": "1" * 40, "primary_fingerprint": "2" * 40}
    second = {"signing_fingerprint": "3" * 40, "primary_fingerprint": "4" * 40}
    first_status = distribution_status(signing=first["signing_fingerprint"], primary=first["primary_fingerprint"])
    second_status = distribution_status(signing=second["signing_fingerprint"], primary=second["primary_fingerprint"])
    facts = sig._parse_status(second_status + first_status, [second, first], DISTRIBUTION_EVALUATION)
    assert [(value["signing_fingerprint"], value["primary_fingerprint"]) for value in facts] == [
        (first["signing_fingerprint"], first["primary_fingerprint"]),
        (second["signing_fingerprint"], second["primary_fingerprint"])]
    for raw, roster in ((first_status, [first, second]), (first_status + second_status, [first]),
                        (first_status, [{**first, "primary_fingerprint": "5" * 40}])):
        with pytest.raises(sig.SignatureError):
            sig._parse_status(raw, roster, DISTRIBUTION_EVALUATION)


@pytest.mark.parametrize("changes,error", [
    ({"exit_code": 1}, "signature_verification_failed"),
    ({"timed_out": True, "capture_complete": False, "error_code": "signature_wall_timeout"}, "signature_wall_timeout"),
    ({"output_limited": True, "limited_streams": ["stderr"], "error_code": "signature_stderr_limit"}, "signature_stderr_limit"),
    ({"capture_complete": False}, "signature_capture_incomplete"),
])
def test_distribution_failed_verifier_attempt_is_preserved_once_before_rejection(distribution_case, monkeypatch, changes, error):
    sig, evidence = distribution_signature(), []
    monkeypatch.setattr(sig, "_capture", lambda **kwargs: distribution_capture_result(**changes))
    with pytest.raises(sig.SignatureError, match="^" + error + "$"):
        sig.verify_detached(**distribution_signature_arguments(distribution_case, evidence_sink=evidence.append))
    assert len(evidence) == 1 and evidence[0]["stderr_bytes"] == b"authored diagnostic\n"
    record = evidence[0]["process_record"]
    assert record["verification_error_code"] == error and record["verification_status"] == "rejected"
    assert record["stdout"] == bound(evidence[0]["stdout_bytes"])
    assert record["stderr"] == bound(evidence[0]["stderr_bytes"])


def test_distribution_failed_preservation_never_returns_accepted_signature(distribution_case, monkeypatch):
    sig, calls = distribution_signature(), []
    monkeypatch.setattr(sig, "_capture", lambda **kwargs: distribution_capture_result())
    def failed_sink(payload):
        calls.append(payload)
        raise OSError("authored preservation failure")
    with pytest.raises(sig.SignatureError, match="^signature_evidence_preservation_failed$"):
        sig.verify_detached(**distribution_signature_arguments(distribution_case, evidence_sink=failed_sink))
    assert len(calls) == 1


def test_distribution_verifier_capture_drains_other_pipe_after_cap_failure(tmp_path, monkeypatch):
    sig = distribution_signature()
    original_selector = sig.selectors.DefaultSelector
    class StderrFirstSelector(original_selector):
        def select(self, timeout=None):
            time.sleep(0.03)
            return sorted(super().select(timeout), key=lambda result: result[0].data != "stderr")
    code = "import os,time; os.write(1,b'AB'); os.write(2,b'overflow'); time.sleep(3)"
    def authored(_argv, **kwargs):
        kwargs.pop("executable")
        return REAL_POPEN([sys.executable, "-c", code], **kwargs)
    monkeypatch.setattr(sig.subprocess, "Popen", authored)
    monkeypatch.setattr(sig.selectors, "DefaultSelector", StderrFirstSelector)
    monkeypatch.setattr(sig, "STDOUT_LIMIT", 16)
    monkeypatch.setattr(sig, "STDERR_LIMIT", 4)
    monkeypatch.setattr(sig, "WALL_SECONDS", 0.5)
    result = sig._capture(executable_fd=-1, argv=["authored-capture-child"], directory=str(tmp_path), pass_fds=())
    assert result["stdout_bytes"] == b"AB" and result["stderr_bytes"] == b"over"
    assert result["process_record"]["error_code"] == "signature_stderr_limit"
    assert result["process_record"]["limited_streams"] == ["stderr"]
    assert result["process_record"]["exit_code"] is not None


def test_distribution_verifier_deadline_keeps_pending_diagnostics(tmp_path, monkeypatch):
    sig = distribution_signature()
    code = "import os,time; os.write(1,b'bounded status'); os.write(2,b'bounded diagnostic'); time.sleep(3)"
    def authored(_argv, **kwargs):
        kwargs.pop("executable")
        return REAL_POPEN([sys.executable, "-c", code], **kwargs)
    monkeypatch.setattr(sig.subprocess, "Popen", authored)
    monkeypatch.setattr(sig, "WALL_SECONDS", 0.15)
    result = sig._capture(executable_fd=-1, argv=["authored-capture-child"], directory=str(tmp_path), pass_fds=())
    assert result["stdout_bytes"] == b"bounded status" and result["stderr_bytes"] == b"bounded diagnostic"
    assert result["process_record"]["timed_out"] is True
    assert result["process_record"]["error_code"] == "signature_wall_timeout"
    assert result["process_record"]["exit_code"] is not None


def test_distribution_checker_direct_invocation_requires_originals():
    result = subprocess.run([sys.executable, str(ROOT / "tools/check_required_gate_idempotence_launcher_distribution_v0.py")],
                            capture_output=True, timeout=15)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "rejected" and report.get("launcher_distribution_authenticated", False) is False
    assert report["execution_authorized"] is False and report["authority_effect"] == "none"


@pytest.fixture(scope="module")
def distribution_record(distribution_case):
    return distribution_checker().derive_record(**distribution_arguments(distribution_case))


@pytest.mark.parametrize("path,replacement", [
    (("bindings", "launch_host_verification", "sha256"), "0" * 64),
    (("bindings", "launcher", "sha256"), "1" * 64),
    (("verification_policy", "evaluation_time"), DISTRIBUTION_EVALUATION + 1),
    (("metadata", "package", "size_bytes"), 1),
])
def test_distribution_rehashed_saved_record_requires_complete_fresh_reconstruction(
        distribution_case, distribution_record, path, replacement):
    c, changed = distribution_checker(), json.loads(distribution_record)
    parent = changed
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    raw = encoded(changed)
    with pytest.raises(c.DistributionError, match="^distribution_record_reconstruction_mismatch$"):
        c.verify_record(record_bytes=raw, expected_record_sha256=digest(raw), **distribution_arguments(distribution_case))


def test_distribution_saved_accepted_record_does_not_replace_fresh_crypto(distribution_case, distribution_record, monkeypatch):
    c, sig, evidence, calls = distribution_checker(), distribution_signature(), [], []
    def failed_new_attempt(**kwargs):
        calls.append(kwargs["argv"])
        result = distribution_capture_result(exit_code=1)
        result["stdout_bytes"] = b"[GNUPG:] NEWSIG\n[GNUPG:] BADSIG 77FE94169196DC10 authored failure\n"
        return result
    monkeypatch.setattr(sig, "_capture", failed_new_attempt)
    with pytest.raises(c.DistributionError, match="^signature_verification_failed$"):
        c.verify_record(record_bytes=distribution_record, expected_record_sha256=digest(distribution_record),
                        **distribution_arguments(distribution_case, signature_evidence_sink=evidence.append))
    assert len(calls) == len(evidence) == 1
    assert evidence[0]["process_record"]["verification_status"] == "rejected"


@pytest.mark.parametrize("key,replacement", [("name", "unrelated"), ("version", "9.9"),
                                            ("sha256", "0" * 64), ("size_bytes", 1)])
def test_distribution_new_selection_cannot_rebind_the_old_launcher_package(distribution_case, key, replacement):
    c, chosen = distribution_checker(), copy.deepcopy(distribution_case.selection)
    chosen["package"][key] = replacement
    with pytest.raises(c.DistributionError, match="^distribution_package_launch_host_mismatch$"):
        c.derive_record(**distribution_arguments(distribution_case, selection=chosen))


def test_distribution_signature_creation_cannot_predate_the_signed_release(distribution_case, monkeypatch):
    c, sig = distribution_checker(), distribution_signature()
    facts = sig._parse_status(distribution_status(), distribution_case.trust["required_signers"], DISTRIBUTION_EVALUATION)
    facts[0]["signature_created_epoch"] = 1767225599
    monkeypatch.setattr(sig, "verify_detached", lambda **kwargs: {
        "verified_signatures": facts, "backend": distribution_case.trust["verifier"]})
    with pytest.raises(c.DistributionError):
        c.derive_record(**distribution_arguments(distribution_case))


@pytest.mark.parametrize("limit,value,error", [
    ("MAX_PACKAGE_STANZAS", 1, "distribution_metadata_paragraph_limit"),
    ("MAX_DIGEST_ROWS", 1, "distribution_metadata_digest_row_limit"),
    ("STANZA_LIMIT", 64, "distribution_metadata_stanza_limit"),
])
def test_distribution_parser_count_and_stanza_bounds_are_enforced(distribution_case, monkeypatch, limit, value, error):
    m = distribution_metadata()
    monkeypatch.setattr(m, limit, value)
    with pytest.raises(m.MetadataError, match="^" + error + "$"):
        m.inspect_metadata(**distribution_metadata_arguments(distribution_case))


def test_distribution_parser_line_limit_is_not_evaded_in_unselected_metadata(distribution_case, monkeypatch):
    m, case = distribution_metadata(), distribution_case
    maximum = max(map(len, (case.release + case.decoded).splitlines()))
    monkeypatch.setattr(m, "LINE_LIMIT", maximum)
    raw = case.decoded.replace(b"Description: Unselected authored paragraph", b"Description: " + b"x" * (maximum + 1))
    with pytest.raises(m.MetadataError, match="^distribution_metadata_line_limit$"):
        m.inspect_metadata(**distribution_metadata_arguments(case, decoded=raw))


@pytest.mark.parametrize("limit,value", [("INDEX_COMPRESSED_LIMIT", 1), ("INDEX_DECODED_LIMIT", 1), ("XZ_MEMORY_LIMIT", 1)])
def test_distribution_decompression_has_compressed_decoded_and_memory_bounds(distribution_case, monkeypatch, limit, value):
    m = distribution_metadata()
    monkeypatch.setattr(m, limit, value)
    with pytest.raises(m.MetadataError):
        m._decode_index(distribution_case.compressed)


@pytest.mark.parametrize("kind", ["symlink", "script", "non_executable"])
def test_distribution_verifier_identity_cannot_be_redirected_or_interpreted(distribution_case, tmp_path, monkeypatch, kind):
    sig, path = distribution_signature(), tmp_path / "selected-gpg"
    if kind == "symlink":
        path.symlink_to(distribution_case.verifier)
        raw = distribution_case.verifier.read_bytes()
    else:
        raw = b"#!/bin/sh\necho must-never-run\n" if kind == "script" else distribution_case.verifier.read_bytes()
        path.write_bytes(raw)
        path.chmod(0o755 if kind == "script" else 0o644)
    def forbidden(**kwargs):
        pytest.fail("an unsafe verifier path must not execute")
    monkeypatch.setattr(sig, "_capture", forbidden)
    expected = {"kind": "gpg", "path": str(path), **bound(raw)}
    with pytest.raises(sig.SignatureError):
        sig.verify_detached(**distribution_signature_arguments(distribution_case, verifier_path=path, expected_verifier=expected))


def distribution_cli_inputs(case, directory):
    args, _ = launch_host_cli_inputs(case.host, directory)
    host_cli = launch_host_subject()
    old_args = host_cli._parser().parse_args(["prepare", *args, "--output", str(directory / "unused-old-output.json")])
    plan = launch_host_checker().derive_plan(**host_cli._original_inputs(old_args))
    chosen = copy.deepcopy(case.selection)
    chosen["launch_host_plan"] = bound(plan)
    bound_files = [("launch-host-plan", plan), ("distribution-selection", encoded(chosen)), ("trust-policy", encoded(case.trust))]
    for name, raw in bound_files:
        path = directory / (name + ".json")
        path.write_bytes(raw)
        args += ["--" + name, str(path), "--" + name + "-sha256", digest(raw)]
    for name, raw in (("release", case.release), ("release-signature", case.signature),
                      ("packages-xz", case.compressed), ("keyring", case.keyring)):
        path = directory / name
        path.write_bytes(raw)
        args += ["--" + name, str(path)]
    return args + ["--verifier", str(case.verifier)]


def test_distribution_cli_prepares_and_freshly_rechecks_with_original_process_evidence(distribution_case, tmp_path):
    args = distribution_cli_inputs(distribution_case, tmp_path)
    record_path, first_evidence, next_evidence = tmp_path / "record.json", tmp_path / "prepare-evidence", tmp_path / "check-evidence"
    made = subprocess.run([sys.executable, str(DISTRIBUTION_TOOL), "prepare", *args, "--output", str(record_path),
                           "--verification-directory", str(first_evidence)], capture_output=True, timeout=45)
    assert made.returncode == 0, made.stdout.decode() + made.stderr.decode()
    raw = record_path.read_bytes()
    checked = subprocess.run([sys.executable, str(DISTRIBUTION_TOOL), "check", *args,
                              "--record", str(record_path), "--record-sha256", digest(raw),
                              "--verification-directory", str(next_evidence)], capture_output=True, timeout=30)
    assert checked.returncode == 0, checked.stdout.decode() + checked.stderr.decode()
    assert made.stdout == checked.stdout and record_path.read_bytes() == raw
    assert json.loads(checked.stdout)["launcher_distribution_authenticated"] is True
    for directory, invocations in ((first_evidence, 2), (next_evidence, 1)):
        assert len(list(directory.iterdir())) == invocations * 3
        for number in range(1, invocations + 1):
            prefix = directory / f"verification-{number}"
            process = json.loads(prefix.with_suffix(".process.json").read_bytes())
            assert process["verification_status"] == "accepted"
            assert process["stdout"] == bound(prefix.with_suffix(".status.bin").read_bytes())
            assert process["stderr"] == bound(prefix.with_suffix(".stderr.bin").read_bytes())


@pytest.mark.parametrize("kind", ["existing_output", "existing_evidence"])
def test_distribution_cli_does_not_replace_previous_record_or_evidence(distribution_case, tmp_path, kind):
    args = distribution_cli_inputs(distribution_case, tmp_path)
    output, evidence = tmp_path / "record.json", tmp_path / "evidence"
    if kind == "existing_output":
        output.write_bytes(b"retain existing record\n")
    else:
        evidence.mkdir()
        (evidence / "retain").write_bytes(b"retain existing evidence\n")
    result = subprocess.run([sys.executable, str(DISTRIBUTION_TOOL), "prepare", *args, "--output", str(output),
                             "--verification-directory", str(evidence)], capture_output=True, timeout=30)
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "rejected"
    if kind == "existing_output":
        assert output.read_bytes() == b"retain existing record\n" and not evidence.exists()
    else:
        assert not output.exists() and (evidence / "retain").read_bytes() == b"retain existing evidence\n"


def test_distribution_coordinator_offers_no_execution_or_transcript_replay_command():
    p = module("required_gate_idempotence_launcher_distribution_v0", "tools/required_gate_idempotence_launcher_distribution_v0.py")
    actions = p._parser()._subparsers._group_actions
    assert len(actions) == 1 and set(actions[0].choices) == {"prepare", "check"}
    for command in actions[0].choices.values():
        options = {option for action in command._actions for option in action.option_strings}
        assert "--release-signature" in options and "--trust-policy-sha256" in options
        assert not options & {"--status-transcript", "--signature-status", "--skip-verification", "--execute"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))


# Fixed authored probe observations.  The positive fixture captures actual owned
# process/kernel evidence; mutations below are explicitly authored rejection
# cases and never stand in for the successful live observation.
import signal as mapping_signal

MAPPING_TOOL = ROOT / "tools/required_gate_idempotence_mapping_observation_v0.py"
MAPPING_CHECKER = ROOT / "tools/check_required_gate_idempotence_mapping_observation_v0.py"


def mapping_probe():
    return module("required_gate_idempotence_mapping_probe_v0", "tools/required_gate_idempotence_mapping_probe_v0.py")


def mapping_subject():
    return module("required_gate_idempotence_mapping_observation_v0", "tools/required_gate_idempotence_mapping_observation_v0.py")


def mapping_checker():
    return module("check_required_gate_idempotence_mapping_observation_v0", "tools/check_required_gate_idempotence_mapping_observation_v0.py")


@contextmanager
def mapping_probe_fd():
    fd = os.memfd_create("mapping-fixed-probe-test", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        raw = mapping_probe().probe_bytes()
        assert os.write(fd, raw) == len(raw)
        os.fchmod(fd, 0o500)
        # Fixed Linux ABI: F_ADD_SEALS=1033, all four mutation seals=15.
        # The pinned CPython build need not export the symbolic constants.
        fcntl.fcntl(fd, 1033, 15)
        yield fd
    finally:
        os.close(fd)


def test_mapping_fixed_probe_has_exact_static_single_rx_page_and_nonexecuting_stack():
    raw = mapping_probe().probe_bytes()
    assert len(raw) == 4096 and raw == mapping_probe().probe_bytes()
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    assert header[:4] == (b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1)
    assert header[4:7] == (0x4000B0, 64, 0)
    assert header[8:11] == (64, 56, 2)
    program_headers = [struct.unpack_from("<IIQQQQQQ", raw, 64 + index * 56) for index in range(2)]
    assert program_headers[0] == (1, 5, 0, 0x400000, 0x400000, 4096, 4096, 4096)
    assert program_headers[1] == (0x6474E551, 6, 0, 0, 0, 0, 0, 16)
    assert all(row[0] not in (2, 3) for row in program_headers)


@pytest.mark.parametrize("arguments, expected_exit", [
    ([], 126), ([""], 126), (["00000000"], 126), (["ffffffff"], 126),
    (["0000000G"], 126), (["000000001"], 126), (["00000001", "extra"], 126),
    (["00000001"], 127),
])
def test_mapping_fixed_probe_rejects_invalid_or_wrong_parent_without_stopping(arguments, expected_exit):
    assert os.getpid() != 1
    with mapping_probe_fd() as fd:
        result = subprocess.run(["fixed-mapping-probe", *arguments],
                                executable=f"/proc/self/fd/{fd}", pass_fds=(fd,),
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=3)
    assert result.returncode == expected_exit
    assert result.stdout == result.stderr == b""


def test_mapping_fixed_probe_dies_with_its_parent_without_continuation():
    # The subreaper setting and both native children exist only in this dedicated
    # test subprocess.  Every reap is for an owned child; no host-wide setting or
    # selected launcher/runtime is changed or executed.
    script = r'''
import ctypes, fcntl, json, os, select, signal, sys, time
sys.path.insert(0, sys.argv[1])
from required_gate_idempotence_mapping_probe_v0 import probe_bytes, parent_argument
libc = ctypes.CDLL(None, use_errno=True)
def prctl(option, value):
    if libc.prctl(option, value, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "prctl failed")
prctl(36, 1)  # PR_SET_CHILD_SUBREAPER in this test subprocess only.
owner_pid = os.getpid()
read_fd, write_fd = os.pipe()
supervisor = os.fork()
if supervisor == 0:
    os.close(read_fd)
    prctl(1, signal.SIGKILL)
    if os.getppid() != owner_pid:
        os._exit(81)
    fd = os.memfd_create("mapping-pdeath-test", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    raw = probe_bytes()
    if os.write(fd, raw) != len(raw):
        os._exit(82)
    os.fchmod(fd, 0o500)
    fcntl.fcntl(fd, 1033, 15)
    supervisor_pid = os.getpid()
    probe = os.fork()
    if probe == 0:
        os.execve(f"/proc/self/fd/{fd}", ["fixed-mapping-probe", parent_argument(supervisor_pid)], {})
    os.close(fd)
    waited, stop = os.waitpid(probe, os.WUNTRACED)
    if waited != probe or not os.WIFSTOPPED(stop) or os.WSTOPSIG(stop) != signal.SIGSTOP:
        os._exit(83)
    os.write(write_fd, (str(probe) + " " + str(stop) + "\n").encode("ascii"))
    while True:
        signal.pause()
os.close(write_fd)
reaped, probe = set(), None
def reap_owned(pid):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        waited, status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            reaped.add(pid)
            return status
        time.sleep(0.01)
    raise AssertionError("owned child was not reaped")
try:
    assert select.select([read_fd], [], [], 3)[0], "probe did not reach its stopped checkpoint"
    line = os.read(read_fd, 256)
    probe, stopped = map(int, line.strip().split())
    os.kill(supervisor, signal.SIGKILL)
    parent_status = reap_owned(supervisor)
    child_status = reap_owned(probe)
    assert os.WIFSIGNALED(parent_status) and os.WTERMSIG(parent_status) == signal.SIGKILL
    assert os.WIFSIGNALED(child_status) and os.WTERMSIG(child_status) == signal.SIGKILL
    print(json.dumps({"stopped": os.WSTOPSIG(stopped),
                      "parent_signal": os.WTERMSIG(parent_status),
                      "probe_signal": os.WTERMSIG(child_status)}))
finally:
    os.close(read_fd)
    for pid in (supervisor, probe):
        if pid is not None and pid not in reaped:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(ROOT / "tools")],
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert result.stderr == b""
    assert json.loads(result.stdout) == {"stopped": mapping_signal.SIGSTOP,
                                       "parent_signal": mapping_signal.SIGKILL,
                                       "probe_signal": mapping_signal.SIGKILL}


@pytest.fixture(scope="module")
def mapping_observed_case(tmp_path_factory):
    observer, checker = mapping_subject(), mapping_checker()
    selection_raw = observer.make_selection("20a5c0e4612f483da30e6a51d04a9c83")
    directory = tmp_path_factory.mktemp("mapping-observation") / "capture"
    report = observer.run_example(selection_bytes=selection_raw,
                                  expected_selection_sha256=digest(selection_raw),
                                  output_directory=directory)
    assert report["observation_complete"] is True, report
    capture_raw, files = checker.read_capture_directory(directory)
    assert files["selection.json"] == selection_raw
    return SimpleNamespace(directory=directory, selection_raw=selection_raw,
                           selection=json.loads(selection_raw), capture_raw=capture_raw,
                           capture=json.loads(capture_raw), files=files, report=report)


def mapping_verify_changed(case, *, capture=None, files=None, selection_raw=None):
    """Rebind authored mutations internally so the semantic relation is tested."""
    value = copy.deepcopy(case.capture if capture is None else capture)
    raw_files = dict(case.files if files is None else files)
    value["files"] = [{"path": name, **bound(raw)} for name, raw in sorted(raw_files.items())]
    raw = encoded(value)
    chosen = case.selection_raw if selection_raw is None else selection_raw
    return mapping_checker().verify_capture(selection_bytes=chosen,
        expected_selection_sha256=digest(chosen), capture_bytes=raw,
        expected_capture_sha256=digest(raw), files=raw_files)


def mapping_stat_field(raw, number, value):
    name, tail = raw.rsplit(b") ", 1)
    fields = tail.split()
    if number == 1:
        _, command = name.split(b" ", 1)
        name = str(value).encode("ascii") + b" " + command
    else:
        fields[number - 3] = str(value).encode("ascii")
    return name + b") " + b" ".join(fields) + b"\n"


def mapping_status_field(raw, name, value):
    key = name.encode("ascii") + b":"
    rows = raw.splitlines()
    assert sum(row.startswith(key) for row in rows) == 1
    return b"\n".join(key + b"\t" + str(value).encode("ascii") if row.startswith(key) else row
                       for row in rows) + b"\n"


def test_mapping_actual_owned_stopped_probe_capture_is_independently_reconstructed(mapping_observed_case):
    case, checker = mapping_observed_case, mapping_checker()
    result = mapping_verify_changed(case)
    assert result == case.report
    assert result["status"] == "accepted" and result["observation_record_verified"] is True
    assert result["observation_complete"] is True
    assert result["stopped_executable_backing_relation_verified"] is True
    assert result["sealed_executable_object_binding_verified"] is True
    for key, value in checker.BOUNDARY.items():
        assert type(result[key]) is type(value) and result[key] == value
    assert case.capture["objects"]["retained"] == case.capture["objects"]["executable"]
    assert case.capture["objects"]["retained"]["seals"] == 15
    assert case.files["probe.elf"] == case.files["retained.elf"] == case.files["executable.elf"] == mapping_probe().probe_bytes()
    assert case.files["child.maps.before.bin"] == case.files["child.maps.after.bin"]
    assert os.WIFSTOPPED(case.capture["wait"]["initial"])
    assert os.WSTOPSIG(case.capture["wait"]["initial"]) == mapping_signal.SIGSTOP
    assert case.capture["wait"]["observation"] is None
    assert os.WIFSIGNALED(case.capture["wait"]["terminal"])
    assert os.WTERMSIG(case.capture["wait"]["terminal"]) == mapping_signal.SIGKILL
    assert case.capture["ownership"]["child_reaped"] is True
    assert case.capture["ownership"]["resumed_after_stop"] is False
    assert set(case.files) == set(checker.FILE_NAMES)
    assert case.files["stdout.bin"] == case.files["stderr.bin"] == b""


@pytest.mark.parametrize("which", ["selection", "capture"])
def test_mapping_external_anchors_cannot_be_supplied_by_the_capture(mapping_observed_case, which):
    case = mapping_observed_case
    arguments = dict(selection_bytes=case.selection_raw,
                     expected_selection_sha256=digest(case.selection_raw),
                     capture_bytes=case.capture_raw, expected_capture_sha256=digest(case.capture_raw),
                     files=case.files)
    arguments["expected_" + which + "_sha256"] = "0" * 64
    with pytest.raises(mapping_checker().MappingError):
        mapping_checker().verify_capture(**arguments)


@pytest.mark.parametrize("change", ["probe", "observer_path", "source", "source_roster", "limits",
                                   "attempt_id", "selected", "extra"])
def test_mapping_selection_cannot_redefine_the_fixed_observer_profile(mapping_observed_case, change):
    selected = copy.deepcopy(mapping_observed_case.selection)
    if change == "probe":
        selected["probe"]["sha256"] = "0" * 64
    elif change == "observer_path":
        selected["observer"]["path"] = "/valid/../unselected/python"
    elif change == "source":
        selected["sources"][0]["sha256"] = "0" * 64
    elif change == "source_roster":
        selected["sources"] = selected["sources"][:-1]
    elif change == "limits":
        selected["limits"]["wall_seconds"] += 1
    elif change == "attempt_id":
        selected["attempt_id"] = "A" * 32
    elif change == "selected":
        selected["record_status"] = "selected"
    else:
        selected["command"] = ["/bin/true"]
    raw = encoded(selected)
    with pytest.raises(mapping_checker().MappingError):
        mapping_checker().validate_selection(raw, digest(raw))


def test_mapping_selection_and_capture_reject_boundary_promotion(mapping_observed_case):
    case, checker = mapping_observed_case, mapping_checker()
    attempts = {"physical_execution_authenticated": True, "host_observation_authenticated": True,
                "process_memory_bytes_verified": True, "complete_native_closure_verified": True,
                "containment_enforced": True, "execution_authorized": True,
                "selected_runtime_executed": True, "production_gate_eligible": True,
                "metric_pass": True, "authority_effect": "release", "diagnostic_only": False}
    for key, replacement in attempts.items():
        selected = copy.deepcopy(case.selection)
        selected[key] = replacement
        raw = encoded(selected)
        with pytest.raises(checker.MappingError):
            checker.validate_selection(raw, digest(raw))
        capture = copy.deepcopy(case.capture)
        capture[key] = replacement
        with pytest.raises(checker.MappingError):
            mapping_verify_changed(case, capture=capture)


@pytest.mark.parametrize("name", ["probe.elf", "retained.elf", "executable.elf", "observer.exe.bin"])
def test_mapping_each_original_byte_object_remains_bound_after_inventory_rehash(mapping_observed_case, name):
    files = dict(mapping_observed_case.files)
    original = files[name]
    files[name] = original[:-1] + bytes((original[-1] ^ 1,))
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(mapping_observed_case, files=files)


@pytest.mark.parametrize("change", ["capture_attempt", "start_attempt", "start_observer", "start_time",
                                   "selection_copy", "pidfd_pid", "observer_pid"])
def test_mapping_same_attempt_and_owned_process_identities_cannot_be_composed(mapping_observed_case, change):
    case = mapping_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    start = json.loads(files["attempt_start.json"])
    if change == "capture_attempt":
        capture["attempt_id"] = "d" * 32
    elif change == "start_attempt":
        start["attempt_id"] = "d" * 32
    elif change == "start_observer":
        start["observer_pid"] += 1
    elif change == "start_time":
        start["started_ns"] += 1
    elif change == "selection_copy":
        chosen = json.loads(files["selection.json"])
        chosen["attempt_id"] = "d" * 32
        files["selection.json"] = encoded(chosen)
    elif change == "pidfd_pid":
        files["child.pidfd.info.bin"] = mapping_status_field(files["child.pidfd.info.bin"],
                                                            "Pid", capture["child_pid"] + 1)
    else:
        files["observer.stat.bin"] = mapping_stat_field(files["observer.stat.bin"], 1,
                                                        capture["observer_pid"] + 1)
    files["attempt_start.json"] = encoded(start)
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, capture=capture, files=files)


@pytest.mark.parametrize("change", ["after_starttime", "after_parent", "before_pid", "before_threads",
                                   "after_tracer", "after_running", "duplicate_status_pid"])
def test_mapping_both_stopped_process_occurrences_are_required(mapping_observed_case, change):
    case, files = mapping_observed_case, dict(mapping_observed_case.files)
    if change == "after_starttime":
        old = int(files["child.stat.after.bin"].rsplit(b") ", 1)[1].split()[19])
        files["child.stat.after.bin"] = mapping_stat_field(files["child.stat.after.bin"], 22, old + 1)
    elif change == "after_parent":
        wrong = case.capture["observer_pid"] + 1
        files["child.stat.after.bin"] = mapping_stat_field(files["child.stat.after.bin"], 4, wrong)
        files["child.status.after.bin"] = mapping_status_field(files["child.status.after.bin"], "PPid", wrong)
    elif change == "before_pid":
        files["child.stat.before.bin"] = mapping_stat_field(files["child.stat.before.bin"], 1,
                                                           case.capture["child_pid"] + 1)
    elif change == "before_threads":
        files["child.status.before.bin"] = mapping_status_field(files["child.status.before.bin"], "Threads", 2)
    elif change == "after_tracer":
        files["child.status.after.bin"] = mapping_status_field(files["child.status.after.bin"], "TracerPid", 1)
    elif change == "after_running":
        files["child.stat.after.bin"] = mapping_stat_field(files["child.stat.after.bin"], 3, "R")
        files["child.status.after.bin"] = mapping_status_field(files["child.status.after.bin"], "State", "R (running)")
    else:
        files["child.status.after.bin"] += f"Pid:\t{case.capture['child_pid']}\n".encode("ascii")
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, files=files)


@pytest.mark.parametrize("change", ["inode", "permissions", "offset", "extent", "extra_file",
                                   "duplicate", "anonymous_exec", "second_snapshot"])
def test_mapping_every_mapping_occurrence_must_match_the_fixed_backing_object(mapping_observed_case, change):
    case, files = mapping_observed_case, dict(mapping_observed_case.files)
    rows = files["child.maps.before.bin"].splitlines()
    index = next(i for i, row in enumerate(rows) if row.split()[0] == b"00400000-00401000")
    fields = rows[index].split(maxsplit=5)
    if change == "inode":
        fields[4] = str(int(fields[4]) + 1).encode("ascii")
    elif change == "permissions":
        fields[1] = b"rwxp"
    elif change == "offset":
        fields[2] = b"00001000"
    elif change == "extent":
        fields[0] = b"00400000-00402000"
    elif change == "extra_file":
        extra = list(fields)
        extra[0], extra[4] = b"00500000-00501000", str(int(fields[4]) + 1).encode("ascii")
        rows.insert(index + 1, b" ".join(extra))
    elif change == "duplicate":
        rows.insert(index + 1, rows[index])
    elif change == "anonymous_exec":
        rows.insert(index + 1, b"00500000-00501000 r-xp 00000000 00:00 0")
    elif change == "second_snapshot":
        fields[4] = str(int(fields[4]) + 1).encode("ascii")
    rows[index] = b" ".join(fields)
    changed = b"\n".join(rows) + b"\n"
    files["child.maps.after.bin"] = changed
    if change != "second_snapshot":
        files["child.maps.before.bin"] = changed
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, files=files)


@pytest.mark.parametrize("change", ["missing_seal", "different_executable", "linked_object", "privileged_mode",
                                   "different_namespace", "malformed_boot_id", "output"])
def test_mapping_kernel_object_and_host_relations_are_reconstructed(mapping_observed_case, change):
    case = mapping_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    if change == "missing_seal":
        capture["objects"]["retained"]["seals"] = 7
    elif change == "different_executable":
        capture["objects"]["executable"]["stat"]["ino"] += 1
    elif change == "linked_object":
        for obj in capture["objects"].values():
            obj["stat"]["nlink"] = 1
    elif change == "privileged_mode":
        for obj in capture["objects"].values():
            obj["stat"]["mode"] |= stat.S_ISUID
    elif change == "different_namespace":
        host = json.loads(files["host.json"])
        host["child_namespaces"]["pid"] = "pid:[1]"
        files["host.json"] = encoded(host)
    elif change == "malformed_boot_id":
        files["kernel.boot_id.bin"] = b"unidentified-host\n"
    else:
        files["stdout.bin"] = b"unexpected child output\n"
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, capture=capture, files=files)


@pytest.mark.parametrize("change", ["wrong_stop", "additional_event", "normal_exit", "unreaped",
                                   "resumed", "no_pidfd", "late_stop", "late_cleanup"])
def test_mapping_completed_capture_requires_exact_stop_and_bounded_terminal_cleanup(mapping_observed_case, change):
    case, capture = mapping_observed_case, copy.deepcopy(mapping_observed_case.capture)
    if change == "wrong_stop":
        capture["wait"]["initial"] = (mapping_signal.SIGTRAP << 8) | 0x7f
    elif change == "additional_event":
        capture["wait"]["observation"] = capture["wait"]["initial"]
    elif change == "normal_exit":
        capture["wait"]["terminal"] = 0
    elif change == "unreaped":
        capture["ownership"]["child_reaped"] = False
    elif change == "resumed":
        capture["ownership"]["resumed_after_stop"] = True
    elif change == "no_pidfd":
        capture["ownership"]["pidfd_opened"] = False
    elif change == "late_stop":
        capture["timing"]["stopped_ns"] = capture["timing"]["started_ns"] + 15_000_000_001
        capture["timing"]["finished_ns"] = capture["timing"]["stopped_ns"] + 1
    else:
        capture["timing"]["finished_ns"] = capture["timing"]["started_ns"] + 17_000_000_001
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, capture=capture)


def test_mapping_valid_incomplete_record_never_becomes_a_completed_observation(mapping_observed_case):
    case, capture = mapping_observed_case, copy.deepcopy(mapping_observed_case.capture)
    capture.update(status="incomplete", failure="mapping_probe_spawn_failed", child_pid=None)
    capture["timing"]["stopped_ns"] = None
    capture["wait"] = {"initial": None, "observation": None, "terminal": None}
    capture["ownership"] = {"pidfd_opened": False, "proc_dir_pinned": False,
                            "child_reaped": False, "resumed_after_stop": False}
    capture["objects"] = {"retained": None, "executable": None}
    files = {name: case.files[name] for name in ("selection.json", "attempt_start.json")}
    result = mapping_verify_changed(case, capture=capture, files=files)
    assert result["status"] == "accepted" and result["observation_record_verified"] is True
    assert result["observation_complete"] is False
    assert result["stopped_executable_backing_relation_verified"] is False
    assert result["sealed_executable_object_binding_verified"] is False
    assert result["failure"] == "mapping_probe_spawn_failed"
    capture.update(status="completed", failure=None)
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, capture=capture, files=files)


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "wrong_size"])
def test_mapping_capture_inventory_is_exact_and_binds_all_raw_bytes(mapping_observed_case, change):
    case = mapping_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    if change == "missing":
        files.pop("child.status.after.bin")
    elif change == "extra":
        files["invented.json"] = b"{}\n"
    elif change == "duplicate":
        capture["files"].append(copy.deepcopy(capture["files"][0]))
    else:
        capture["files"][0]["size_bytes"] += 1
    if change in ("missing", "extra"):
        capture["files"] = [{"path": name, **bound(raw)} for name, raw in sorted(files.items())]
    raw = encoded(capture)
    with pytest.raises(mapping_checker().MappingError):
        mapping_checker().verify_capture(selection_bytes=case.selection_raw,
            expected_selection_sha256=digest(case.selection_raw), capture_bytes=raw,
            expected_capture_sha256=digest(raw), files=files)


@pytest.mark.parametrize("change", ["symlink_file", "hardlink_file", "symlink_directory", "symlink_parent", "extra", "mode"])
def test_mapping_capture_reader_rejects_aliased_or_unpreserved_inputs(mapping_observed_case, tmp_path, change):
    case, path = mapping_observed_case, tmp_path / "capture"
    shutil.copytree(case.directory, path)
    selected = path / "child.stat.before.bin"
    if change == "symlink_file":
        target = tmp_path / "unbound-stat"
        selected.replace(target)
        selected.symlink_to(target)
    elif change == "hardlink_file":
        os.link(selected, tmp_path / "unbound-alias")
    elif change == "symlink_directory":
        target = tmp_path / "moved"
        path.rename(target)
        path.symlink_to(target, target_is_directory=True)
    elif change == "symlink_parent":
        alias = tmp_path / "parent-alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        path = alias / "capture"
    elif change == "extra":
        (path / "unrecorded.bin").write_bytes(b"extra")
    else:
        selected.chmod(0o644)
    with pytest.raises((mapping_checker().MappingError, OSError)):
        mapping_checker().read_capture_directory(path)


def test_mapping_independent_checker_processes_reconstruct_identical_canonical_reports(mapping_observed_case, tmp_path):
    case = mapping_observed_case
    arguments = ["--selection", str(case.directory / "selection.json"),
                 "--selection-sha256", digest(case.selection_raw),
                 "--capture-directory", str(case.directory),
                 "--capture-sha256", digest(case.capture_raw)]
    reports = []
    for index in range(2):
        output = tmp_path / f"checker-{index}.json"
        result = subprocess.run([sys.executable, "-I", "-B", str(MAPPING_CHECKER),
                                 *arguments, "--output", str(output)],
                                capture_output=True, timeout=15)
        assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
        assert result.stderr == b"" and output.read_bytes() == result.stdout
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        assert result.stdout == encoded(json.loads(result.stdout))
        reports.append(result.stdout)
    assert reports[0] == reports[1] == encoded(case.report)
    existing = tmp_path / "checker-0.json"
    result = subprocess.run([sys.executable, "-I", "-B", str(MAPPING_CHECKER),
                             *arguments, "--output", str(existing)],
                            capture_output=True, timeout=15)
    assert result.returncode != 0 and existing.read_bytes() == reports[0]


def test_mapping_selected_status_rejects_before_capture_creation_or_spawn(mapping_observed_case, tmp_path, monkeypatch):
    observer = mapping_subject()
    selected = copy.deepcopy(mapping_observed_case.selection)
    selected["record_status"] = "selected"
    raw = encoded(selected)
    def forbidden(*args, **kwargs):
        pytest.fail("selected target must not reach the fixed-probe spawn path")
    monkeypatch.setattr(observer, "_spawn_probe", forbidden)
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        observer.run_example(selection_bytes=raw, expected_selection_sha256=digest(raw),
                             output_directory=output)
    assert not output.exists()


def test_mapping_spawn_denial_is_preserved_as_incomplete_without_retry(tmp_path, monkeypatch):
    observer, calls = mapping_subject(), []
    selected = observer.make_selection("f04bb46c3a10470d8bca412b9b4f44c0")
    def denied(*args, **kwargs):
        calls.append(True)
        raise PermissionError(errno.EPERM, "authored spawn denial")
    monkeypatch.setattr(observer, "_spawn_probe", denied)
    output = tmp_path / "incomplete"
    report = observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                                  output_directory=output)
    assert len(calls) == 1
    assert report["observation_record_verified"] is True and report["observation_complete"] is False
    assert report["stopped_executable_backing_relation_verified"] is False
    assert report["sealed_executable_object_binding_verified"] is False
    capture_raw, files = mapping_checker().read_capture_directory(output)
    assert json.loads(capture_raw)["status"] == "incomplete"
    assert json.loads(capture_raw)["child_pid"] is None
    assert files["selection.json"] == selected


@pytest.mark.parametrize("kind", ["existing", "symlink"])
def test_mapping_run_requires_a_new_private_directory_before_any_child(tmp_path, monkeypatch, kind):
    observer = mapping_subject()
    selected = observer.make_selection("5adfeac5e056421eb0aa72e0944cb58c")
    retained = tmp_path / "retained"
    retained.mkdir()
    marker = retained / "owner-bytes"
    marker.write_bytes(b"retain this original\n")
    output = retained
    if kind == "symlink":
        output = tmp_path / "alias"
        output.symlink_to(retained, target_is_directory=True)
    def forbidden(*args, **kwargs):
        pytest.fail("an existing or aliased output must reject before spawning")
    monkeypatch.setattr(observer, "_spawn_probe", forbidden)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                             output_directory=output)
    assert marker.read_bytes() == b"retain this original\n"
    assert sorted(path.name for path in retained.iterdir()) == ["owner-bytes"]


@pytest.mark.parametrize("change", ["new_inode_same_bytes", "changed_bytes", "extra_file", "directory_mode", "directory_replaced"])
def test_mapping_live_preservation_substitution_cannot_publish_a_normal_capture(tmp_path, monkeypatch, change):
    observer = mapping_subject()
    chosen = observer.make_selection("96fc40b257f349a7834e1fd3dc9841f7")
    output_path, moved = tmp_path / "capture", tmp_path / "retained-original-directory"
    preserve, changed = observer._preserve, []
    def substitute(output, name, raw):
        preserve(output, name, raw)
        if name != "stdout.bin" or changed:
            return
        changed.append(True)
        target = output_path / "probe.elf"
        if change == "new_inode_same_bytes":
            original = target.read_bytes()
            target.rename(tmp_path / "retained-original-probe")
            target.write_bytes(original)
            target.chmod(0o600)
        elif change == "changed_bytes":
            original = target.read_bytes()
            target.write_bytes(original[:-1] + bytes((original[-1] ^ 1,)))
        elif change == "extra_file":
            (output_path / "unrecorded.bin").write_bytes(b"unrecorded\n")
        elif change == "directory_mode":
            output_path.chmod(0o755)
        else:
            output_path.rename(moved)
            output_path.mkdir(mode=0o700)
    monkeypatch.setattr(observer, "_preserve", substitute)
    with pytest.raises((observer.MappingPreservationError, mapping_checker().MappingError)):
        observer.run_example(selection_bytes=chosen, expected_selection_sha256=digest(chosen),
                             output_directory=output_path)
    assert changed == [True]
    assert not (output_path / "capture.json").exists()
    assert not (moved / "capture.json").exists()
    original_directory = moved if change == "directory_replaced" else output_path
    assert (original_directory / "selection.json").read_bytes() == chosen
    assert (original_directory / "attempt_start.json").is_file()


def test_mapping_partial_preservation_failure_retains_prefix_without_normal_capture(tmp_path, monkeypatch):
    observer = mapping_subject()
    chosen = observer.make_selection("8b15d47a43b64e2e9ae8213ed18a4f71")
    output_path, preserve, failures = tmp_path / "capture", observer._preserve, []
    def partial(output, name, raw):
        if name == "child.maps.before.bin":
            failures.append(raw[:7])
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=output.fd)
            try:
                assert os.write(fd, raw[:7]) == 7
            finally:
                os.close(fd)
            raise observer.MappingPreservationError("mapping_preservation_failed")
        preserve(output, name, raw)
    monkeypatch.setattr(observer, "_preserve", partial)
    with pytest.raises(observer.MappingPreservationError):
        observer.run_example(selection_bytes=chosen, expected_selection_sha256=digest(chosen),
                             output_directory=output_path)
    assert len(failures) == 1 and (output_path / "child.maps.before.bin").read_bytes() == failures[0]
    assert not (output_path / "capture.json").exists()
    marker = json.loads((output_path / "attempt.incomplete.json").read_bytes())
    assert marker["status"] == "incomplete" and marker["authority_effect"] == "none"


@pytest.mark.parametrize("failure", ["proc_denied", "deadline"])
def test_mapping_failed_stopped_observation_kills_and_reaps_without_resuming(tmp_path, monkeypatch, failure):
    observer = mapping_subject()
    chosen = observer.make_selection("27a489b0c4d949c2a35ab3c0af7b741c")
    read_proc, deadline, signal_pidfd = observer._read_proc, observer._check_deadline, observer.signal.pidfd_send_signal
    checkpoints, signals = [], []
    def observed_read(fd, name, limit):
        if name == "maps":
            checkpoints.append(name)
            if failure == "proc_denied":
                raise PermissionError(errno.EACCES, "authored proc denial")
        return read_proc(fd, name, limit)
    def expired(bound):
        if failure == "deadline" and checkpoints:
            raise observer.MappingObservationError("mapping_wall_deadline")
        deadline(bound)
    def retain_signal(fd, sig, *args, **kwargs):
        signals.append(sig)
        return signal_pidfd(fd, sig, *args, **kwargs)
    monkeypatch.setattr(observer, "_read_proc", observed_read)
    monkeypatch.setattr(observer, "_check_deadline", expired)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", retain_signal)
    output = tmp_path / "incomplete"
    result = observer.run_example(selection_bytes=chosen, expected_selection_sha256=digest(chosen),
                                  output_directory=output)
    assert checkpoints and signals == [mapping_signal.SIGKILL]
    assert result["observation_complete"] is False and result["physical_execution_authenticated"] is False
    raw, _ = mapping_checker().read_capture_directory(output)
    capture = json.loads(raw)
    assert capture["ownership"]["child_reaped"] is True
    assert capture["ownership"]["resumed_after_stop"] is False
    assert os.WSTOPSIG(capture["wait"]["initial"]) == mapping_signal.SIGSTOP
    assert os.WTERMSIG(capture["wait"]["terminal"]) == mapping_signal.SIGKILL
    with pytest.raises(ChildProcessError):
        os.waitpid(capture["child_pid"], os.WNOHANG)


def test_mapping_actual_observer_mismatch_rejects_before_output_and_spawn(mapping_observed_case, tmp_path, monkeypatch):
    observer = mapping_subject()
    descriptor = copy.deepcopy(mapping_observed_case.selection["observer"])
    descriptor["sha256"] = "0" * 64
    monkeypatch.setattr(observer, "_actual_observer", lambda: (descriptor, mapping_observed_case.files["observer.exe.bin"]))
    def forbidden(*args, **kwargs):
        pytest.fail("a substituted observer cannot spawn the authored probe")
    monkeypatch.setattr(observer, "_spawn_probe", forbidden)
    output = tmp_path / "must-not-exist"
    with pytest.raises(observer.MappingObservationError):
        observer.run_example(selection_bytes=mapping_observed_case.selection_raw,
                             expected_selection_sha256=digest(mapping_observed_case.selection_raw),
                             output_directory=output)
    assert not output.exists()


def test_mapping_json_ambiguity_and_equal_looking_numeric_types_reject(mapping_observed_case):
    case, checker = mapping_observed_case, mapping_checker()
    duplicate = case.selection_raw[:-2] + b',"attempt_id":"' + case.selection["attempt_id"].encode() + b'"}\n'
    with pytest.raises(checker.MappingError):
        checker.validate_selection(duplicate, digest(duplicate))
    capture = copy.deepcopy(case.capture)
    capture["wait"]["terminal"] = float(capture["wait"]["terminal"])
    with pytest.raises(checker.MappingError):
        mapping_verify_changed(case, capture=capture)
    capture = copy.deepcopy(case.capture)
    capture["objects"]["retained"]["stat"]["nlink"] = False
    with pytest.raises(checker.MappingError):
        mapping_verify_changed(case, capture=capture)


@pytest.mark.parametrize("kind", ["maps_inode", "stat_integer", "status_pid"])
def test_mapping_bounded_raw_records_reject_oversized_numbers_with_controlled_errors(mapping_observed_case, kind):
    case, files = mapping_observed_case, dict(mapping_observed_case.files)
    huge = "9" * 5000
    if kind == "maps_inode":
        rows = files["child.maps.before.bin"].splitlines()
        index = next(i for i, row in enumerate(rows) if row.split()[0] == b"00400000-00401000")
        fields = rows[index].split(maxsplit=5)
        fields[4] = huge.encode("ascii")
        rows[index] = b" ".join(fields)
        files["child.maps.before.bin"] = files["child.maps.after.bin"] = b"\n".join(rows) + b"\n"
    elif kind == "stat_integer":
        files["child.stat.after.bin"] = mapping_stat_field(files["child.stat.after.bin"], 22, huge)
    else:
        files["child.status.after.bin"] = mapping_status_field(files["child.status.after.bin"], "Pid", huge)
    assert all(len(raw) <= 65536 for name, raw in files.items() if name.startswith("child."))
    with pytest.raises(mapping_checker().MappingError):
        mapping_verify_changed(case, files=files)


def test_mapping_late_failure_still_gets_a_bounded_owned_child_reap(monkeypatch):
    observer, process = mapping_subject(), SimpleNamespace(pid=12345, returncode=None)
    capture = {"ownership": {"child_reaped": False}, "wait": {"terminal": None}}
    signals, waits = [], []
    monkeypatch.setattr(observer.time, "monotonic_ns", lambda: 100_000_000_000)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", lambda fd, sig: signals.append((fd, sig)))
    def terminal(pid, flags):
        waits.append(pid)
        return pid, int(mapping_signal.SIGKILL)
    monkeypatch.setattr(observer.os, "waitpid", terminal)
    assert observer._cleanup(process, 321, capture, 1_000_000_000) is None
    assert signals == [(321, mapping_signal.SIGKILL)] and waits == [12345]
    assert capture["ownership"]["child_reaped"] is True
    assert process.returncode == -mapping_signal.SIGKILL
    assert observer._cleanup(process, 321, capture, 1_000_000_000) is None
    assert signals == [(321, mapping_signal.SIGKILL)] and waits == [12345]


def test_mapping_pidfd_signal_denial_remains_incomplete_after_owned_child_cleanup(tmp_path, monkeypatch):
    observer, children = mapping_subject(), []
    selected = observer.make_selection("da5171a3c2994ee8ac2ae658c57c124c")
    spawn = observer._spawn_probe
    def owned(fd, pid):
        child = spawn(fd, pid)
        children.append(child)
        return child
    def denied(fd, sig, *args, **kwargs):
        raise PermissionError(errno.EPERM, "authored signal denial")
    monkeypatch.setattr(observer, "_spawn_probe", owned)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", denied)
    try:
        output = tmp_path / "incomplete"
        result = observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                                      output_directory=output)
        assert len(children) == 1 and result["observation_complete"] is False
        assert result["failure"] == "mapping_cleanup_pidfd_signal_failed"
        raw, _ = mapping_checker().read_capture_directory(output)
        capture = json.loads(raw)
        assert capture["ownership"]["child_reaped"] is True
        assert os.WTERMSIG(capture["wait"]["terminal"]) == mapping_signal.SIGKILL
        assert result["stopped_executable_backing_relation_verified"] is False
    finally:
        # The denial above is an authored fault.  Reap our actual stopped child
        # through the unaffected process handle so the regression leaves no task.
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=3)


def test_mapping_reader_rechecks_already_read_capture_after_later_file_reads(mapping_observed_case, tmp_path, monkeypatch):
    checker, path = mapping_checker(), tmp_path / "capture"
    shutil.copytree(mapping_observed_case.directory, path)
    target = path / "capture.json"
    before, directory_before = target.stat(), path.stat()
    original, reads, changed = target.read_bytes(), [], []
    read_relative = checker._read_relative
    def alter_earlier_file(parent_fd, name, limit, **kwargs):
        raw = read_relative(parent_fd, name, limit, **kwargs)
        reads.append(name)
        if name == "stdout.bin":
            assert reads[0] == "capture.json" and not changed
            with target.open("r+b") as stream:
                assert stream.write(bytes((original[0] ^ 1,))) == 1
            # An explicit timestamp advance makes this race regression
            # deterministic even on a filesystem with coarse write timestamps.
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
            changed.append(True)
        return raw
    monkeypatch.setattr(checker, "_read_relative", alter_earlier_file)
    with pytest.raises(checker.MappingError, match="^mapping_file_changed_after_read$"):
        checker.read_capture_directory(path)
    after, directory_after = target.stat(), path.stat()
    assert changed == [True] and target.read_bytes() == bytes((original[0] ^ 1,)) + original[1:]
    assert (after.st_dev, after.st_ino, after.st_size) == (before.st_dev, before.st_ino, before.st_size)
    assert (directory_after.st_ino, directory_after.st_mtime_ns, directory_after.st_ctime_ns) == (
        directory_before.st_ino, directory_before.st_mtime_ns, directory_before.st_ctime_ns)


def test_mapping_final_publish_rechecks_earlier_raw_files_after_later_reads(tmp_path, monkeypatch):
    observer, path = mapping_subject(), tmp_path / "capture"
    selected = observer.make_selection("d26ca6af305a4c1b95ad8ea88c91ae72")
    read_fd, changed = observer._read_fd, []
    def alter_earlier_file(fd, limit, **kwargs):
        raw = read_fd(fd, limit, **kwargs)
        if not changed and (path / "capture.json").is_file():
            current, final_file = os.fstat(fd), (path / "stdout.bin").stat()
            if (current.st_dev, current.st_ino) == (final_file.st_dev, final_file.st_ino):
                target = path / "attempt_start.json"
                before, original = target.stat(), target.read_bytes()
                with target.open("r+b") as stream:
                    assert stream.write(bytes((original[0] ^ 1,))) == 1
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                after = target.stat()
                assert (after.st_dev, after.st_ino, after.st_size) == (before.st_dev, before.st_ino, before.st_size)
                changed.append(original)
        return raw
    monkeypatch.setattr(observer, "_read_fd", alter_earlier_file)
    with pytest.raises(observer.MappingPreservationError) as rejected:
        observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                             output_directory=path)
    assert str(rejected.value.__cause__) == "mapping_preserved_identity_changed"
    assert len(changed) == 1 and (path / "capture.json").is_file()
    assert (path / "attempt_start.json").read_bytes() == bytes((changed[0][0] ^ 1,)) + changed[0][1:]
    assert (path / "selection.json").read_bytes() == selected
    failure = json.loads((path / "attempt.incomplete.json").read_bytes())
    assert failure["status"] == "incomplete" and failure["authority_effect"] == "none"
    assert failure["failure"] == "mapping_capture_not_published"
    # The written prefix is retained for diagnosis, but it is not readable as
    # an accepted capture after the final preservation check has failed.
    with pytest.raises(mapping_checker().MappingError, match="^mapping_directory_roster$"):
        mapping_checker().read_capture_directory(path)
