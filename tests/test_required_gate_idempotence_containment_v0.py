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


@pytest.mark.parametrize("kind", ["selection", "capture_record", "capture_member"])
def test_mapping_checker_rejects_fifo_replacement_at_input_open(tmp_path, kind):
    # Replace the stat-validated regular file at the exact open boundary.
    # Run the real FIFO operation in an owned subprocess: an implementation
    # regression must fail within the timeout rather than hang the CI worker.
    directory = tmp_path / "private-input"
    directory.mkdir(mode=0o700)
    for name, raw in (("selection.json", b"selected bytes\n"),
                      ("capture.json", b"capture bytes\n"),
                      ("child.maps.before.bin", b"raw mapping bytes\n")):
        path = directory / name
        path.write_bytes(raw)
        path.chmod(0o600)
    script = r'''
import importlib.util, json, os, pathlib, stat, sys
spec = importlib.util.spec_from_file_location("fifo_boundary_checker", sys.argv[1])
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
directory, kind = pathlib.Path(sys.argv[2]), sys.argv[3]
target = {"selection": "selection.json", "capture_record": "capture.json",
          "capture_member": "child.maps.before.bin"}[kind]
def read_input():
    if kind == "selection":
        return checker.read_selection_file(directory / target)
    return checker.read_capture_directory(directory)
# These are filesystem-reader fixtures, not claims of valid evidence.
# Confirm the unchanged private regular files can be read before the race.
before = read_input()
if kind == "selection":
    assert before == b"selected bytes\n"
else:
    assert before[0] == b"capture bytes\n"
    assert before[1]["child.maps.before.bin"] == b"raw mapping bytes\n"
original_open, changed = checker.os.open, []
def replace_before_open(name, flags, mode=0o777, *, dir_fd=None):
    if name == target and dir_fd is not None and not changed:
        info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        assert stat.S_ISREG(info.st_mode)
        os.unlink(name, dir_fd=dir_fd)
        os.mkfifo(name, 0o600, dir_fd=dir_fd)
        assert stat.S_ISFIFO(os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode)
        changed.append(True)
        print(json.dumps({"event": "fifo_substituted", "kind": kind}), flush=True)
    return original_open(name, flags, mode, dir_fd=dir_fd)
checker.os.open = replace_before_open
try:
    read_input()
except checker.MappingError as error:
    assert changed == [True] and (directory / target).is_fifo()
    print(json.dumps({"event": "rejected", "reason": str(error), "kind": kind}), flush=True)
else:
    raise AssertionError("substituted FIFO was accepted")
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                             str(MAPPING_CHECKER), str(directory), kind],
                            capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stderr == b""
    assert [json.loads(line) for line in result.stdout.splitlines()] == [
        {"event": "fifo_substituted", "kind": kind},
        {"event": "rejected", "reason": "mapping_file_changed", "kind": kind},
    ]


# Separate two-stop authored probe: actual selected virtual-memory bytes are
# observed at both checkpoints. Rehashed mutations below test reconstruction;
# they are not additional live observations or original-runtime executions.
MEMORY_TOOL = ROOT / "tools/required_gate_idempotence_memory_observation_v0.py"
MEMORY_CHECKER = ROOT / "tools/check_required_gate_idempotence_memory_observation_v0.py"


def memory_probe():
    return module("required_gate_idempotence_memory_probe_v0", "tools/required_gate_idempotence_memory_probe_v0.py")


def memory_subject():
    return module("required_gate_idempotence_memory_observation_v0", "tools/required_gate_idempotence_memory_observation_v0.py")


def memory_checker():
    return module("check_required_gate_idempotence_memory_observation_v0", "tools/check_required_gate_idempotence_memory_observation_v0.py")


@pytest.fixture(scope="module")
def memory_observed_case(tmp_path_factory):
    observer, checker = memory_subject(), memory_checker()
    selection_raw = observer.make_selection("d8c508b275a34e8ca65862010a86f4f0")
    directory = tmp_path_factory.mktemp("memory-observation") / "capture"
    report = observer.run_example(selection_bytes=selection_raw,
                                  expected_selection_sha256=digest(selection_raw),
                                  output_directory=directory)
    assert report["observation_complete"] is True, report
    capture_raw, files = checker.read_capture_directory(directory)
    assert files["selection.json"] == selection_raw
    return SimpleNamespace(directory=directory, selection_raw=selection_raw,
                           selection=json.loads(selection_raw), capture_raw=capture_raw,
                           capture=json.loads(capture_raw), files=files, report=report)


def memory_verify_changed(case, *, capture=None, files=None, selection_raw=None):
    """Rehash authored changes so acceptance must depend on the finite relation."""
    value = copy.deepcopy(case.capture if capture is None else capture)
    raw_files = dict(case.files if files is None else files)
    value["files"] = [{"path": name, **bound(raw)} for name, raw in sorted(raw_files.items())]
    raw = encoded(value)
    chosen = case.selection_raw if selection_raw is None else selection_raw
    return memory_checker().verify_capture(selection_bytes=chosen,
        expected_selection_sha256=digest(chosen), capture_bytes=raw,
        expected_capture_sha256=digest(raw), files=raw_files)


def memory_incomplete_boundaries(report):
    assert report["status"] == "accepted" and report["observation_record_verified"] is True
    for name in ("observation_complete", "sealed_backing_object_unchanged",
                 "selected_memory_ranges_observed", "selected_rx_pages_match_backing",
                 "selected_rw_transition_observed"):
        assert report[name] is False, name
    assert report["memory_relations"] == [] and report["changed_data_offsets"] == []
    for key, value in memory_checker().BOUNDARY.items():
        assert type(report[key]) is type(value) and report[key] == value, key


def test_memory_fixed_probe_has_two_exact_load_pages_and_no_loader():
    raw = memory_probe().probe_bytes()
    assert len(raw) == 8192 and raw == memory_probe().probe_bytes()
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    assert header[:4] == (b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1)
    assert header[4:7] == (0x4000E8, 64, 0) and header[8:11] == (64, 56, 3)
    rows = [struct.unpack_from("<IIQQQQQQ", raw, 64 + index * 56) for index in range(3)]
    assert rows == [(1, 5, 0, 0x400000, 0x400000, 4096, 4096, 4096),
                    (1, 6, 4096, 0x401000, 0x401000, 4096, 4096, 4096),
                    (0x6474E551, 6, 0, 0, 0, 0, 0, 16)]
    assert raw[4096:] == bytes(4096)
    # The old never-resumed subject remains a different exact byte object.
    assert raw != mapping_probe().probe_bytes()
    assert digest(mapping_probe().probe_bytes()) == "dfa1de8166ef6447cc053ca82abf4fd443757e926bc8dd4097c9afbfd7bb2c1a"


@pytest.mark.parametrize("arguments, expected_exit", [
    ([], 126), (["00000000"], 126), (["ffffffff"], 126),
    (["0000000G"], 126), (["00000001", "extra"], 126), (["00000001"], 127),
])
def test_memory_fixed_probe_rejects_invalid_parent_before_any_checkpoint(arguments, expected_exit):
    assert os.getpid() != 1
    fd = os.memfd_create("memory-probe-invalid-parent", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        raw = memory_probe().probe_bytes()
        assert os.write(fd, raw) == len(raw)
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, 1033, 15)
        result = subprocess.run(["fixed-memory-probe", *arguments],
                                executable=f"/proc/self/fd/{fd}", pass_fds=(fd,),
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=3)
        assert result.returncode == expected_exit and result.stdout == result.stderr == b""
    finally:
        os.close(fd)


def test_memory_actual_two_checkpoint_observation_reconstructs_each_range(memory_observed_case):
    case, checker = memory_observed_case, memory_checker()
    report = memory_verify_changed(case)
    assert report == case.report and report["observation_complete"] is True
    for name in ("sealed_backing_object_unchanged", "selected_memory_ranges_observed",
                 "selected_rx_pages_match_backing", "selected_rw_transition_observed"):
        assert report[name] is True, name
    assert report["changed_data_offsets"] == [256]
    rows = report["memory_relations"]
    assert [(row["checkpoint_id"], row["range_id"]) for row in rows] == [
        ("cp0", "rx"), ("cp0", "rw"), ("cp1", "rx"), ("cp1", "rw")]
    assert [row["matches_backing"] for row in rows] == [True, True, True, False]
    assert len(case.files) == 39 and set(case.files) == set(checker.FILE_NAMES)
    original = memory_probe().probe_bytes()
    for name in ("probe.elf", "retained.before.elf", "retained.after.elf",
                 "cp0.executable.elf", "cp1.executable.elf"):
        assert case.files[name] == original
    expected_final = bytearray(4096)
    expected_final[256] = 0x5a
    for checkpoint in ("cp0", "cp1"):
        for read in ("first", "second"):
            assert case.files[f"{checkpoint}.rx.{read}.bin"] == original[:4096]
            assert case.files[f"{checkpoint}.rw.{read}.bin"] == (
                bytes(4096) if checkpoint == "cp0" else bytes(expected_final))
    assert case.capture["ownership"]["continuations_sent"] == 1
    assert case.capture["ownership"]["child_reaped"] is True
    assert [item["wait_status"] for item in case.capture["checkpoints"]] == [4991, 4991]
    assert case.capture["wait"]["terminal"] == 9
    for key, value in checker.BOUNDARY.items():
        assert type(report[key]) is type(value) and report[key] == value, key
    with pytest.raises(ChildProcessError):
        os.waitpid(case.capture["child_pid"], os.WNOHANG)


@pytest.mark.parametrize("which", ["selection", "capture"])
def test_memory_external_digests_cannot_be_replaced_by_internal_inventory(memory_observed_case, which):
    case = memory_observed_case
    arguments = dict(selection_bytes=case.selection_raw,
                     expected_selection_sha256=digest(case.selection_raw),
                     capture_bytes=case.capture_raw,
                     expected_capture_sha256=digest(case.capture_raw), files=case.files)
    arguments[f"expected_{which}_sha256"] = "0" * 64
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_checker().verify_capture(**arguments)


@pytest.mark.parametrize("change", ["range_address", "range_size", "range_offset", "range_permissions",
    "range_duplicate", "checkpoint_order", "checkpoint_duplicate", "write_offset", "write_value",
    "continuations", "source_digest", "source_removed", "probe_digest", "wall_limit"])
def test_memory_selection_cannot_redefine_ranges_transition_or_sources(memory_observed_case, change):
    selected = copy.deepcopy(memory_observed_case.selection)
    if change.startswith("range_"):
        if change == "range_duplicate":
            selected["ranges"][1] = copy.deepcopy(selected["ranges"][0])
        else:
            key = {"range_address": "address", "range_size": "size_bytes",
                   "range_offset": "file_offset", "range_permissions": "permissions"}[change]
            selected["ranges"][1][key] = "rwxp" if key == "permissions" else selected["ranges"][1][key] + 1
    elif change == "checkpoint_order":
        selected["checkpoints"].reverse()
    elif change == "checkpoint_duplicate":
        selected["checkpoints"][1] = selected["checkpoints"][0]
    elif change == "write_offset":
        selected["transition"]["offset"] += 1
    elif change == "write_value":
        selected["transition"]["after_hex"] = "5b"
    elif change == "continuations":
        selected["transition"]["continuations"] = 2
    elif change == "source_digest":
        selected["sources"][0]["sha256"] = "0" * 64
    elif change == "source_removed":
        selected["sources"].pop()
    elif change == "probe_digest":
        selected["probe"]["sha256"] = "0" * 64
    else:
        selected["limits"]["wall_seconds"] += 1
    raw = encoded(selected)
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_checker().validate_selection(raw, digest(raw))


def test_memory_selection_pins_all_reused_mapping_sources(memory_observed_case):
    rows = memory_observed_case.selection["sources"]
    assert len(rows) == 8 and [row["path"] for row in rows] == sorted(row["path"] for row in rows)
    assert set(mapping_checker().SOURCE_PATHS) < {row["path"] for row in rows}
    for row in rows:
        assert {key: row[key] for key in ("sha256", "size_bytes")} == bound((ROOT / row["path"]).read_bytes())


def test_memory_boundary_cannot_be_promoted_by_rehashing_selected_or_observed_records(memory_observed_case):
    checker, case = memory_checker(), memory_observed_case
    for key, value in checker.BOUNDARY.items():
        replacement = not value if type(value) is bool else (True if value is None else "promoted")
        selected = copy.deepcopy(case.selection)
        selected[key] = replacement
        raw = encoded(selected)
        with pytest.raises(checker.MemoryCheckError):
            checker.validate_selection(raw, digest(raw))
        capture = copy.deepcopy(case.capture)
        capture[key] = replacement
        with pytest.raises(checker.MemoryCheckError):
            memory_verify_changed(case, capture=capture)


@pytest.mark.parametrize("name", [f"{checkpoint}.{region}.{read}.bin"
    for checkpoint in ("cp0", "cp1") for region in ("rx", "rw") for read in ("first", "second")])
def test_memory_every_checkpoint_range_and_read_must_match_its_own_bytes(memory_observed_case, name):
    files = dict(memory_observed_case.files)
    changed = bytearray(files[name])
    changed[17] ^= 1
    files[name] = bytes(changed)
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(memory_observed_case, files=files)


@pytest.mark.parametrize("change", ["missing_write", "wrong_value", "wrong_offset", "extra_write",
                                  "swapped_checkpoint_pages", "short_second_read"])
def test_memory_repeated_range_cannot_mask_an_incorrect_second_checkpoint(memory_observed_case, change):
    files = dict(memory_observed_case.files)
    if change == "swapped_checkpoint_pages":
        for read in ("first", "second"):
            before, after = f"cp0.rw.{read}.bin", f"cp1.rw.{read}.bin"
            files[before], files[after] = files[after], files[before]
    elif change == "short_second_read":
        files["cp1.rw.second.bin"] = files["cp1.rw.second.bin"][:-1]
    else:
        page = bytearray(files["cp1.rw.first.bin"])
        if change == "missing_write":
            page[256] = 0
        elif change == "wrong_value":
            page[256] = 0x5b
        elif change == "wrong_offset":
            page[256], page[257] = 0, 0x5a
        else:
            page[257] = 0x5a
        # Both repeated reads agree, so checking only repeatability is insufficient.
        files["cp1.rw.first.bin"] = files["cp1.rw.second.bin"] = bytes(page)
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(memory_observed_case, files=files)


@pytest.mark.parametrize("change", ["checkpoint_order", "duplicate_checkpoint", "old_process_starttime",
                                  "wrong_parent", "foreign_memory_object", "foreign_executable_object"])
def test_memory_two_checkpoints_cannot_be_composed_from_different_occurrences(memory_observed_case, change):
    case = memory_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    if change == "checkpoint_order":
        capture["checkpoints"].reverse()
    elif change == "duplicate_checkpoint":
        capture["checkpoints"][1]["checkpoint_id"] = "cp0"
    elif change == "old_process_starttime":
        for suffix in ("before", "after"):
            name = f"cp1.child.stat.{suffix}.bin"
            old = mapping_checker().parse_proc_stat(files[name])["starttime"]
            files[name] = mapping_stat_field(files[name], 22, old + 1)
    elif change == "wrong_parent":
        for suffix in ("before", "after"):
            name = f"cp1.child.stat.{suffix}.bin"
            files[name] = mapping_stat_field(files[name], 4, capture["observer_pid"] + 1000)
            name = f"cp1.child.status.{suffix}.bin"
            files[name] = mapping_status_field(files[name], "PPid", capture["observer_pid"] + 1000)
    elif change == "foreign_memory_object":
        capture["checkpoints"][1]["memory_object"]["ino"] += 1
    else:
        capture["checkpoints"][1]["executable_object"]["stat"]["ino"] += 1
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(case, capture=capture, files=files)


@pytest.mark.parametrize("change", ["data_offset", "data_inode", "data_permissions", "extra_mapping"])
def test_memory_each_mapping_occurrence_is_related_to_the_selected_file_page(memory_observed_case, change):
    case, files = memory_observed_case, dict(memory_observed_case.files)
    rows = files["cp1.child.maps.before.bin"].splitlines()
    for index, raw in enumerate(rows):
        parts = raw.split(None, 5)
        if parts[0] != b"00401000-00402000":
            continue
        if change == "data_offset":
            parts[2] = b"00000000"
        elif change == "data_inode":
            parts[4] = str(int(parts[4]) + 1).encode()
        elif change == "data_permissions":
            parts[1] = b"rw-s"
        rows[index] = b" ".join(parts)
        break
    else:
        pytest.fail("fixed data mapping missing from actual observation")
    if change == "extra_mapping":
        rows.insert(2, b"00600000-00601000 r-xp 00000000 00:00 0")
    changed = b"\n".join(rows) + b"\n"
    # Preserve matching before/after maps; the declared occurrence itself is wrong.
    files["cp1.child.maps.before.bin"] = files["cp1.child.maps.after.bin"] = changed
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(case, files=files)


@pytest.mark.parametrize("change", ["unpreserved_cp0", "unpreserved_cp1", "early_continue", "early_cp1",
    "missing_continue", "extra_continue", "unexpected_wait", "not_reaped", "wrong_terminal", "deadline"])
def test_memory_completed_transition_requires_ordered_preservation_and_owned_cleanup(memory_observed_case, change):
    case, capture = memory_observed_case, copy.deepcopy(memory_observed_case.capture)
    if change.startswith("unpreserved_"):
        capture["checkpoints"][int(change[-1])]["preserved"] = False
    elif change == "early_continue":
        capture["timing"]["continued_ns"] = capture["checkpoints"][0]["observed_ns"] - 1
    elif change == "early_cp1":
        capture["checkpoints"][1]["stopped_ns"] = capture["timing"]["continued_ns"] - 1
    elif change == "missing_continue":
        capture["ownership"]["continuations_sent"] = 0
    elif change == "extra_continue":
        capture["ownership"]["continuations_sent"] = 2
    elif change == "unexpected_wait":
        capture["checkpoints"][1]["observation_wait"] = 0xffff
    elif change == "not_reaped":
        capture["ownership"]["child_reaped"] = False
    elif change == "wrong_terminal":
        capture["wait"]["terminal"] = 0
    else:
        capture["timing"]["finished_ns"] = capture["timing"]["started_ns"] + 18 * 10**9
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(case, capture=capture)


@pytest.mark.parametrize("name", ["retained.after.elf", "cp1.executable.elf"])
def test_memory_sealed_backing_bytes_cannot_be_replaced_by_changed_process_bytes(memory_observed_case, name):
    case, files = memory_observed_case, dict(memory_observed_case.files)
    files[name] = files[name][:4096] + files["cp1.rw.first.bin"]
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(case, files=files)


@pytest.mark.parametrize("change", ["missing_sample", "extra_file", "duplicate_row", "incorrect_size"])
def test_memory_manifest_binds_the_exact_raw_roster(memory_observed_case, change):
    case = memory_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    if change == "missing_sample":
        files.pop("cp1.rw.second.bin")
    elif change == "extra_file":
        files["unselected-page.bin"] = bytes(4096)
    elif change == "duplicate_row":
        capture["files"].append(copy.deepcopy(capture["files"][0]))
    else:
        capture["files"][0]["size_bytes"] += 1
    if change in ("missing_sample", "extra_file"):
        capture["files"] = [{"path": name, **bound(raw)} for name, raw in sorted(files.items())]
    raw = encoded(capture)
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_checker().verify_capture(selection_bytes=case.selection_raw,
            expected_selection_sha256=digest(case.selection_raw), capture_bytes=raw,
            expected_capture_sha256=digest(raw), files=files)


def test_memory_independent_checker_processes_produce_identical_canonical_reports(memory_observed_case, tmp_path):
    case = memory_observed_case
    arguments = ["--selection", str(case.directory / "selection.json"),
                 "--selection-sha256", digest(case.selection_raw),
                 "--capture-directory", str(case.directory),
                 "--capture-sha256", digest(case.capture_raw)]
    reports = []
    for index in range(2):
        output = tmp_path / f"memory-checker-{index}.json"
        result = subprocess.run([sys.executable, "-I", "-B", str(MEMORY_CHECKER),
                                 *arguments, "--output", str(output)],
                                capture_output=True, timeout=15)
        assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
        assert result.stderr == b"" and output.read_bytes() == result.stdout
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        assert result.stdout == encoded(json.loads(result.stdout))
        reports.append(result.stdout)
    assert reports[0] == reports[1] == encoded(case.report)


@pytest.mark.parametrize("kind", ["selection", "capture_record", "capture_member"])
def test_memory_checker_preserves_nonblocking_fifo_admission(tmp_path, kind):
    directory = tmp_path / "private-memory-input"
    directory.mkdir(mode=0o700)
    for name, raw in (("selection.json", b"selected bytes\n"),
                      ("capture.json", b"capture bytes\n"),
                      ("cp1.rw.second.bin", b"raw memory bytes\n")):
        path = directory / name
        path.write_bytes(raw)
        path.chmod(0o600)
    # Filesystem-only fixture; a FIFO at the stat/open boundary must fail in
    # the wrapper as well as in its reused admission helper, without hanging.
    script = r'''
import importlib.util, json, os, pathlib, stat, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location("memory_fifo_checker", sys.argv[1])
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
directory, kind = pathlib.Path(sys.argv[2]), sys.argv[3]
target = {"selection": "selection.json", "capture_record": "capture.json",
          "capture_member": "cp1.rw.second.bin"}[kind]
def read_input():
    if kind == "selection":
        return checker.read_selection_file(directory / target)
    return checker.read_capture_directory(directory)
read_input()
original_open, changed = os.open, []
def replace_before_open(name, flags, mode=0o777, *, dir_fd=None):
    if name == target and dir_fd is not None and not changed:
        assert stat.S_ISREG(os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode)
        os.unlink(name, dir_fd=dir_fd)
        os.mkfifo(name, 0o600, dir_fd=dir_fd)
        changed.append(True)
        print(json.dumps({"event": "fifo_substituted", "kind": kind}), flush=True)
    return original_open(name, flags, mode, dir_fd=dir_fd)
os.open = replace_before_open
try:
    read_input()
except checker.MemoryCheckError as error:
    assert changed == [True] and (directory / target).is_fifo()
    print(json.dumps({"event": "rejected", "reason": str(error), "kind": kind}), flush=True)
else:
    raise AssertionError("substituted FIFO was accepted")
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                             str(MEMORY_CHECKER), str(directory), kind],
                            capture_output=True, timeout=5)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert result.stderr == b""
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events == [{"event": "fifo_substituted", "kind": kind},
                      {"event": "rejected", "reason": "mapping_file_changed", "kind": kind}]


@pytest.mark.parametrize("change", ["capture_attempt", "selection_reference", "attempt_start"])
def test_memory_preserved_observation_cannot_be_relabelled_as_a_new_attempt(memory_observed_case, change):
    case = memory_observed_case
    capture, files = copy.deepcopy(case.capture), dict(case.files)
    if change == "capture_attempt":
        capture["attempt_id"] = "0" * 32
    elif change == "selection_reference":
        capture["selection_sha256"] = "0" * 64
    else:
        start = json.loads(files["attempt_start.json"])
        start["attempt_id"] = "0" * 32
        files["attempt_start.json"] = encoded(start)
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(case, capture=capture, files=files)


def test_memory_numeric_types_and_duplicate_json_keys_do_not_change_the_closed_contract(memory_observed_case):
    case, checker = memory_observed_case, memory_checker()
    duplicate = case.selection_raw[:-2] + b',"attempt_id":"' + case.selection["attempt_id"].encode() + b'"}\n'
    with pytest.raises(checker.MemoryCheckError):
        checker.validate_selection(duplicate, digest(duplicate))
    capture = copy.deepcopy(case.capture)
    capture["ownership"]["continuations_sent"] = True
    with pytest.raises(checker.MemoryCheckError):
        memory_verify_changed(case, capture=capture)
    capture = copy.deepcopy(case.capture)
    capture["checkpoints"][0]["observed_ns"] = float(capture["checkpoints"][0]["observed_ns"])
    with pytest.raises(checker.MemoryCheckError):
        memory_verify_changed(case, capture=capture)
    capture = copy.deepcopy(case.capture)
    capture["checkpoints"][1]["memory_object"]["nlink"] = True
    with pytest.raises(checker.MemoryCheckError):
        memory_verify_changed(case, capture=capture)


def test_memory_schema_accepts_the_actual_selection_capture_and_reconstruction(memory_observed_case):
    import jsonschema
    schema = json.loads((ROOT / "schemas/required_gate_idempotence_memory_observation_v0.schema.json").read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    case = memory_observed_case
    for record in (case.selection, case.capture, case.report, json.loads(case.files["attempt_start.json"])):
        validator.validate(record)


@pytest.mark.parametrize("checkpoint, failure", [
    ("cp0", "denied"), ("cp0", "short"), ("cp0", "changed"),
    ("cp1", "denied"), ("cp1", "short"), ("cp1", "changed"),
])
def test_memory_failed_page_acquisition_preserves_prefix_and_stops_further_progress(tmp_path, monkeypatch,
                                                                                 checkpoint, failure):
    observer, checker = memory_subject(), memory_checker()
    selected = observer.make_selection("5b062f3dfc754d579339e6cc19aec53d")
    original_pread, send_signal = os.pread, mapping_signal.pidfd_send_signal
    calls, signals = [], []
    target_read = 1 if checkpoint == "cp0" else 5
    def authored_read(fd, size, address):
        assert size == 4096 and address in (0x400000, 0x401000)
        calls.append((size, address))
        if len(calls) != target_read:
            return original_pread(fd, size, address)
        if failure == "denied":
            raise PermissionError(errno.EACCES, "authored own-child memory-read denial")
        raw = original_pread(fd, size, address)
        if failure == "short":
            return raw[:19]
        return raw[:17] + bytes((raw[17] ^ 1,)) + raw[18:]
    def tracked_signal(fd, sig, *args, **kwargs):
        signals.append(sig)
        return send_signal(fd, sig, *args, **kwargs)
    monkeypatch.setattr(observer.os, "pread", authored_read)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", tracked_signal)
    output = tmp_path / "incomplete-memory"
    report = observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                                  output_directory=output)
    memory_incomplete_boundaries(report)
    capture_raw, files = checker.read_capture_directory(output)
    capture = json.loads(capture_raw)
    assert capture["ownership"]["child_reaped"] is True
    assert capture["wait"]["terminal"] == 9
    assert capture["ownership"]["continuations_sent"] == (checkpoint == "cp1")
    assert signals == ([mapping_signal.SIGCONT] if checkpoint == "cp1" else []) + [mapping_signal.SIGKILL]
    sample = f"{checkpoint}.rx.first.bin"
    if failure == "denied":
        assert sample not in files and len(calls) == target_read
    elif failure == "short":
        assert files[sample] == memory_probe().probe_bytes()[:19] and len(calls) == target_read
    else:
        assert len(files[sample]) == 4096 and files[sample] != memory_probe().probe_bytes()[:4096]
        assert len(calls) == (4 if checkpoint == "cp0" else 8)
    assert files["retained.after.elf"] == files["retained.before.elf"] == memory_probe().probe_bytes()
    if checkpoint == "cp0":
        assert not any(name.startswith("cp1.") for name in files)
    with pytest.raises(ChildProcessError):
        os.waitpid(capture["child_pid"], os.WNOHANG)
    # A structurally retained failure cannot be promoted by a status-only edit.
    capture.update(status="completed", failure=None)
    failed_case = SimpleNamespace(capture=capture, files=files, selection_raw=selected)
    with pytest.raises(checker.MemoryCheckError):
        memory_verify_changed(failed_case)


def test_memory_success_uses_exactly_one_continue_then_owned_kill(tmp_path, monkeypatch):
    observer = memory_subject()
    selected = observer.make_selection("381142297d6e45d289e16d858d0a9fc4")
    send_signal, signals = mapping_signal.pidfd_send_signal, []
    def tracked_signal(fd, sig, *args, **kwargs):
        signals.append(sig)
        return send_signal(fd, sig, *args, **kwargs)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", tracked_signal)
    report = observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                                  output_directory=tmp_path / "two-stops")
    assert report["observation_complete"] is True
    assert signals == [mapping_signal.SIGCONT, mapping_signal.SIGKILL]


def test_memory_checkpoint_zero_disk_substitution_prevents_continuation(tmp_path, monkeypatch):
    observer = memory_subject()
    selected = observer.make_selection("84f0726532c14339b14ba89345aa9dd8")
    output = tmp_path / "capture"
    preserve, spawn = observer._preserve, observer._spawn_probe
    send_signal, changed, signals, children = mapping_signal.pidfd_send_signal, [], [], []
    def authored_substitution(directory, name, raw):
        preserve(directory, name, raw)
        if name == "cp0.child.stat.after.bin" and not changed:
            path = output / "cp0.rx.first.bin"
            retained = tmp_path / "original-first-page"
            path.rename(retained)
            path.write_bytes(retained.read_bytes())
            path.chmod(0o600)
            changed.append(True)
    def tracked_spawn(*args, **kwargs):
        child = spawn(*args, **kwargs)
        children.append(child)
        return child
    def tracked_signal(fd, sig, *args, **kwargs):
        signals.append(sig)
        return send_signal(fd, sig, *args, **kwargs)
    monkeypatch.setattr(observer, "_preserve", authored_substitution)
    monkeypatch.setattr(observer, "_spawn_probe", tracked_spawn)
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", tracked_signal)
    with pytest.raises(observer.shared.MappingPreservationError):
        observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                             output_directory=output)
    assert changed == [True] and signals == [mapping_signal.SIGKILL]
    assert len(children) == 1 and children[0].returncode == -mapping_signal.SIGKILL
    assert not (output / "capture.json").exists()
    assert not any(path.name.startswith("cp1.") for path in output.iterdir())
    assert (output / "selection.json").read_bytes() == selected
    assert (output / "attempt.incomplete.json").is_file()
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)


@pytest.mark.parametrize("kind", ["existing", "symlink"])
def test_memory_preservation_destination_rejects_before_probe_execution(tmp_path, monkeypatch, kind):
    observer = memory_subject()
    selected = observer.make_selection("a2047079266b45c196a7115c07d5298a")
    owned = tmp_path / "existing"
    owned.mkdir()
    original = owned / "original-bytes"
    original.write_bytes(b"preserve original\n")
    destination = owned
    if kind == "symlink":
        destination = tmp_path / "alias"
        destination.symlink_to(owned, target_is_directory=True)
    def forbidden(*args, **kwargs):
        pytest.fail("reused or aliased output must reject before fixed-probe execution")
    monkeypatch.setattr(observer, "_spawn_probe", forbidden)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        observer.run_example(selection_bytes=selected, expected_selection_sha256=digest(selected),
                             output_directory=destination)
    assert original.read_bytes() == b"preserve original\n"
    assert sorted(path.name for path in owned.iterdir()) == ["original-bytes"]


def test_memory_selected_status_rejects_before_capture_and_spawn(memory_observed_case, tmp_path, monkeypatch):
    observer = memory_subject()
    selected = copy.deepcopy(memory_observed_case.selection)
    selected["record_status"] = "selected"
    raw = encoded(selected)
    def forbidden(*args, **kwargs):
        pytest.fail("selected-runtime status must not reach the authored-probe execution path")
    monkeypatch.setattr(observer, "_spawn_probe", forbidden)
    output = tmp_path / "must-not-exist"
    with pytest.raises(memory_checker().MemoryCheckError):
        observer.run_example(selection_bytes=raw, expected_selection_sha256=digest(raw),
                             output_directory=output)
    assert not output.exists()


@pytest.mark.parametrize("scenario", ["permitted", "premature", "duplicate"])
def test_memory_optional_continued_wait_event_is_bounded_to_the_single_transition(monkeypatch, scenario):
    observer = memory_subject()
    process = SimpleNamespace(pid=12345, returncode=None)
    checkpoint = observer._new_checkpoint("cp0" if scenario == "premature" else "cp1")
    capture = {"ownership": {"continuations_sent": 0 if scenario == "premature" else 1,
                              "child_reaped": False},
               "timing": {"continued_ns": None if scenario == "premature" else 1},
               "wait": {"continued": None, "terminal": None}}
    statuses = iter([0xffff, 0xffff] if scenario == "duplicate" else [0xffff, 4991])
    calls = []
    def authored_wait(pid, flags):
        assert pid == process.pid
        calls.append(True)
        return pid, next(statuses)
    monkeypatch.setattr(observer.os, "waitpid", authored_wait)
    deadline = time.monotonic_ns() + 10**9
    if scenario == "permitted":
        observer._wait_for_stop(process, capture, checkpoint, deadline)
        assert checkpoint["wait_status"] == 4991 and checkpoint["stopped_ns"] is not None
        assert capture["wait"]["continued"] == 0xffff and len(calls) == 2
    else:
        with pytest.raises(observer.MemoryObservationError):
            observer._wait_for_stop(process, capture, checkpoint, deadline)
        assert checkpoint["stopped_ns"] is None
        assert len(calls) == (1 if scenario == "premature" else 2)


@pytest.mark.parametrize("object_name", ["retained", "executable", "memory"])
def test_memory_out_of_range_file_modes_reject_with_a_controlled_checker_error(memory_observed_case, object_name):
    capture = copy.deepcopy(memory_observed_case.capture)
    if object_name == "retained":
        selected = capture["objects"]["retained_before"]["stat"]
    elif object_name == "executable":
        selected = capture["checkpoints"][1]["executable_object"]["stat"]
    else:
        selected = capture["checkpoints"][1]["memory_object"]
    # stat.S_ISREG must not receive an integer wider than its accepted C type.
    selected["mode"] = 2**32
    with pytest.raises(memory_checker().MemoryCheckError):
        memory_verify_changed(memory_observed_case, capture=capture)


# Original-launcher cp0 acquisition regressions use authored inert ELF bytes and
# mocked owned-child boundaries only.  No original launcher, loader, hosted
# entry, selected runtime or model is executed by these tests.
NATIVE_ACQUISITION_TOOL = ROOT / "tools/required_gate_idempotence_exec_stop_v0.py"
NATIVE_ACQUISITION_CHECKER = ROOT / "tools/check_required_gate_idempotence_exec_stop_v0.py"


def native_acquisition_subject():
    return module("required_gate_idempotence_exec_stop_v0",
                  "tools/required_gate_idempotence_exec_stop_v0.py")


def native_acquisition_checker():
    return module("check_required_gate_idempotence_exec_stop_v0",
                  "tools/check_required_gate_idempotence_exec_stop_v0.py")


def native_acquisition_preparation():
    return module("prepare_required_gate_idempotence_exec_stop_v0",
                  "tools/prepare_required_gate_idempotence_exec_stop_v0.py")


def native_acquisition_authored_elf(*, interpreter=False, marker=0x41):
    """Two distinct, inert ET_DYN inputs with four page-aligned loads each.

    Headers and map expectations are authored here rather than derived by the
    checker under test.  The payload is deliberately never executed.
    """
    raw = bytearray().join(bytes((marker + index,)) * 4096 for index in range(4))
    count = 5 if interpreter else 4
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    struct.pack_into("<16sHHIQQQIHHHHHH", raw, 0, ident, 3, 62, 1,
                     0x1010, 64, 0, 0, 64, 56, count, 0, 0, 0)
    for index, flags in enumerate((4, 5, 4, 6)):
        offset = index * 4096
        struct.pack_into("<IIQQQQQQ", raw, 64 + index * 56,
                         1, flags, offset, offset, offset, 4096, 4096, 4096)
    if interpreter:
        name = b"/lib64/ld-linux-x86-64.so.2\0"
        raw[0x300:0x300 + len(name)] = name
        struct.pack_into("<IIQQQQQQ", raw, 64 + 4 * 56,
                         3, 4, 0x300, 0x300, 0x300, len(name), len(name), 1)
    return bytes(raw)


def native_acquisition_proc_stat(pid, parent, state, start):
    fields = ["0"] * 50
    fields[0], fields[1], fields[17], fields[19] = state, str(parent), "1", str(start)
    return (str(pid) + " (authored inert subject) " + " ".join(fields) + "\n").encode("ascii")


def native_acquisition_proc_status(pid, parent, state, tracer):
    return (f"State:\t{state}\nPid:\t{pid}\nTgid:\t{pid}\nPPid:\t{parent}\n"
            f"Threads:\t1\nTracerPid:\t{tracer}\nNSpid:\t{pid}\n").encode("ascii")


@pytest.fixture
def native_acquisition_case(monkeypatch):
    checker = native_acquisition_checker()
    launcher = native_acquisition_authored_elf(interpreter=True, marker=0x31)
    loader = native_acquisition_authored_elf(marker=0x71)
    native = {"native/bwrap": launcher, "native/ld-linux-x86-64.so.2": loader,
              **{"native/" + name: ("inert dependency: " + name).encode("ascii")
                 for name in ("libc.so.6", "libcap.so.2", "libpcre2-8.so.0", "libselinux.so.1")}}
    layouts = {}
    for role in ("launcher", "loader"):
        layouts[role] = {
            "entry": 0x1010, "phoff": 64, "phentsize": 56,
            "phnum": 5 if role == "launcher" else 4,
            "interpreter": "/lib64/ld-linux-x86-64.so.2" if role == "launcher" else None,
            "segments": [{"index": index, "offset": index * 4096, "vaddr": index * 4096,
                          "filesz": 4096, "memsz": 4096, "flags": flags, "align": 4096}
                         for index, flags in enumerate((4, 5, 4, 6))],
        }
    originals = {name: encoded({"authored_original": name}) for name in (
        "launch_host_plan", "launch_host_report", "distribution_record", "distribution_report")}
    # Only this fixture changes the fixed production profile. None of these
    # test bytes can be admitted by the unpatched original-byte selection.
    monkeypatch.setattr(checker, "NATIVE", {name: bound(raw) for name, raw in native.items()})
    monkeypatch.setattr(checker, "LAYOUTS", layouts)
    monkeypatch.setattr(checker, "RX_BINDINGS", {"launcher": bound(launcher[4096:8192]),
                                               "loader": bound(loader[4096:8192])})
    monkeypatch.setattr(checker, "ORIGINAL_BINDINGS", {name: bound(raw) for name, raw in originals.items()})
    observer_raw = b"authored inert observer bytes\n"
    observer = {"path": "/authored/observer", **bound(observer_raw)}
    request = checker.make_request(attempt_id="59a9fdd937d74531af23439c29fcecb9",
        native_files=native, observer_descriptor=observer,
        **{name + "_bytes": raw for name, raw in originals.items()})
    request_raw = encoded(request)
    observer_pid, child_pid = 1001, 1002
    launcher_object = {"stat": {"dev": os.makedev(0, 1), "ino": 123, "mode": stat.S_IFREG | 0o500,
                                "nlink": 0, "size": len(launcher)}, "seals": 15}
    loader_object = {"stat": {"dev": os.makedev(8, 1), "ino": 456, "mode": stat.S_IFREG | 0o755,
                              "nlink": 1, "size": len(loader)}, "seals": None}
    bases = {"launcher": 0x40000000, "loader": 0x70000000}
    map_rows = []
    for role, device, inode, label in (("launcher", "00:01", 123, "/memfd:authored-launcher (deleted)"),
                                       ("loader", "08:01", 456, "/lib64/ld-linux-x86-64.so.2")):
        for index, permissions in enumerate(("r--p", "r-xp", "r--p", "rw-p")):
            address = bases[role] + index * 4096
            map_rows.append(f"{address:x}-{address + 4096:x} {permissions} {index * 4096:08x} {device} {inode} {label}\n")
    map_rows.extend(("7ff00000-7ff01000 r--p 00000000 00:00 0 [vvar]\n",
                     "7ff01000-7ff02000 r-xp 00000000 00:00 0 [vdso]\n",
                     "7fff0000-80000000 rw-p 00000000 00:00 0 [stack]\n"))
    maps_raw = "".join(map_rows).encode("ascii")
    registers = bytearray(216)
    struct.pack_into("<Q", registers, 16 * 8, bases["loader"] + 0x1010)
    auxv = b"".join(struct.pack("<QQ", key, value) for key, value in (
        (3, bases["launcher"] + 64), (4, 56), (5, 5), (6, 4096),
        (7, bases["loader"]), (9, bases["launcher"] + 0x1010), (0, 0)))
    namespaces = {name: f"{name}:[4026531836]" for name in checker.old.NAMESPACES}
    files = {
        "request.json": request_raw,
        "attempt_start.json": encoded({"record_type": "required_gate_idempotence_exec_stop_attempt_start_v0",
            "profile": checker.PROFILE, "attempt_id": request["attempt_id"],
            "request_sha256": digest(request_raw), "observer_pid": observer_pid, "started_ns": 10**9}),
        "launcher.elf": launcher, "retained.elf": launcher, "executable.elf": launcher,
        "loader.before.elf": loader, "loader.after.elf": loader, "observer.exe.bin": observer_raw,
        "observer.stat.bin": native_acquisition_proc_stat(observer_pid, 1, "S", 100),
        "observer.status.bin": native_acquisition_proc_status(observer_pid, 1, "S", 0),
        "child.maps.before.bin": maps_raw, "child.maps.after.bin": maps_raw,
        "child.pidfd.info.bin": f"Pid:\t{child_pid}\nNSpid:\t{child_pid}\n".encode("ascii"),
        "child.exe.link.bin": b"/memfd:authored-launcher (deleted)",
        "regs.before.bin": bytes(registers), "regs.after.bin": bytes(registers),
        "auxv.before.bin": auxv, "auxv.after.bin": auxv,
        "host.json": encoded({"platform": {"system": "Linux", "machine": "x86_64",
                                           "release": "authored", "version": "authored"},
                              "observer_namespaces": namespaces, "child_namespaces": namespaces}),
        "kernel.boot_id.bin": b"83b18223-3b38-4a2d-97f5-85682b8baf02\n",
        "stdout.bin": b"", "stderr.bin": b"",
    }
    for suffix in ("setup", "before", "after"):
        files[f"child.stat.{suffix}.bin"] = native_acquisition_proc_stat(child_pid, observer_pid, "t", 200)
        files[f"child.status.{suffix}.bin"] = native_acquisition_proc_status(child_pid, observer_pid, "t", observer_pid)
    for role, raw in (("launcher", launcher), ("loader", loader)):
        for sample in (0, 1):
            files[f"{role}.rx.sample{sample}.bin"] = raw[4096:8192]
    capture = {
        "record_type": "required_gate_idempotence_exec_stop_capture_v0", "profile": checker.PROFILE,
        "attempt_id": request["attempt_id"], "request_sha256": digest(request_raw),
        "status": "completed", "failure": None, "observer_pid": observer_pid, "child_pid": child_pid,
        "timing": {"started_ns": 10**9, "stopped_ns": 2 * 10**9, "finished_ns": 3 * 10**9},
        "wait": {"setup": 4991, "exec": 263551, "terminal": 9, "event_msg": child_pid},
        "ownership": {"pidfd_opened": True, "proc_dir_pinned": True, "child_reaped": True,
                      "pre_exec_resumes": 1, "ptrace_options": 0x100010, "kill_sent": True,
                      "post_exec_resumes": 0, "detached": False},
        "objects": {"retained": copy.deepcopy(launcher_object), "executable": copy.deepcopy(launcher_object),
                    "loader_before": copy.deepcopy(loader_object), "loader_after": copy.deepcopy(loader_object),
                    "memory": {"stat": {"dev": os.makedev(0, 5), "ino": 789, "mode": stat.S_IFREG | 0o600,
                                        "nlink": 1, "size": 0}, "seals": None}},
        "files": [{"path": name, **bound(raw)} for name, raw in sorted(files.items())], **checker.BOUNDARY,
    }
    return SimpleNamespace(request=request, request_raw=request_raw, native=native,
        originals=originals, observer_raw=observer_raw, capture=capture, files=files, bases=bases)


def native_acquisition_verify_changed(case, *, capture=None, files=None, request_raw=None):
    chosen = case.request_raw if request_raw is None else request_raw
    raw_files = dict(case.files if files is None else files)
    value = copy.deepcopy(case.capture if capture is None else capture)
    value["files"] = [{"path": name, **bound(raw)} for name, raw in sorted(raw_files.items())]
    raw = encoded(value)
    return native_acquisition_checker().verify_capture(request_bytes=chosen,
        expected_request_sha256=digest(chosen), capture_bytes=raw,
        expected_capture_sha256=digest(raw), files=raw_files)


def test_native_acquisition_authored_cp0_reconstructs_all_loads_and_each_rx_occurrence(native_acquisition_case):
    case, checker = native_acquisition_case, native_acquisition_checker()
    first = native_acquisition_verify_changed(case)
    second = native_acquisition_verify_changed(case)
    assert encoded(first) == encoded(second)
    assert first["status"] == "accepted" and first["observation_complete"] is True
    assert first["kernel_exec_checkpoint_observed"] is True
    assert first["selected_exec_rx_ranges_match_original"] is True
    assert len(case.files) == 32 and set(case.files) == set(checker.FILE_NAMES)
    assert [(row["object"], row["segment_index"], row["sample_index"]) for row in first["memory_relations"]] == [
        ("launcher", 1, 0), ("launcher", 1, 1), ("loader", 1, 0), ("loader", 1, 1)]
    assert [row["address"] for row in first["memory_relations"]] == [
        0x40001000, 0x40001000, 0x70001000, 0x70001000]
    for key, value in checker.BOUNDARY.items():
        assert type(first[key]) is type(value) and first[key] == value, key


@pytest.mark.parametrize("which", ["request", "capture"])
def test_native_acquisition_external_hashes_are_required_even_with_a_rebound_inventory(native_acquisition_case, which):
    case, checker = native_acquisition_case, native_acquisition_checker()
    raw = encoded(case.capture)
    arguments = dict(request_bytes=case.request_raw, expected_request_sha256=digest(case.request_raw),
                     capture_bytes=raw, expected_capture_sha256=digest(raw), files=case.files)
    arguments[f"expected_{which}_sha256"] = "0" * 64
    with pytest.raises(checker.ExecStopError):
        checker.verify_capture(**arguments)


@pytest.mark.parametrize("role,sample", [("launcher", 0), ("launcher", 1), ("loader", 0), ("loader", 1)])
def test_native_acquisition_each_rx_sample_is_required_independently(native_acquisition_case, role, sample):
    case, files = native_acquisition_case, dict(native_acquisition_case.files)
    name = f"{role}.rx.sample{sample}.bin"
    raw = bytearray(files[name])
    raw[123] ^= 1
    files[name] = bytes(raw)
    # The other read of this same object's segment still matches; it must not
    # mask this occurrence after the transport inventory is recomputed.
    assert files[f"{role}.rx.sample{1 - sample}.bin"] != files[name]
    with pytest.raises(native_acquisition_checker().ExecStopError, match="exec_stop_memory_sample"):
        native_acquisition_verify_changed(case, files=files)


@pytest.mark.parametrize("load_index", range(8))
def test_native_acquisition_each_selected_load_segment_requires_mapping_coverage(native_acquisition_case, load_index):
    files = dict(native_acquisition_case.files)
    rows = files["child.maps.before.bin"].splitlines(keepends=True)
    del rows[load_index]
    files["child.maps.before.bin"] = files["child.maps.after.bin"] = b"".join(rows)
    with pytest.raises(native_acquisition_checker().ExecStopError, match="exec_stop_mapping_coverage"):
        native_acquisition_verify_changed(native_acquisition_case, files=files)


@pytest.mark.parametrize("change", ["generic_sigtrap", "wrong_setup", "different_event_pid", "second_pre_exec_resume",
    "post_exec_resume", "detach", "weaker_options", "unreaped_child"])
def test_native_acquisition_kernel_event_and_no_post_exec_progress_are_mandatory(native_acquisition_case, change):
    capture = copy.deepcopy(native_acquisition_case.capture)
    if change == "generic_sigtrap": capture["wait"]["exec"] = (5 << 8) | 0x7f
    elif change == "wrong_setup": capture["wait"]["setup"] = (5 << 8) | 0x7f
    elif change == "different_event_pid": capture["wait"]["event_msg"] += 1
    elif change == "second_pre_exec_resume": capture["ownership"]["pre_exec_resumes"] = 2
    elif change == "post_exec_resume": capture["ownership"]["post_exec_resumes"] = 1
    elif change == "detach": capture["ownership"]["detached"] = True
    elif change == "weaker_options": capture["ownership"]["ptrace_options"] = 0x10
    else: capture["ownership"]["child_reaped"] = False
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_verify_changed(native_acquisition_case, capture=capture)


@pytest.mark.parametrize("field", ["AT_BASE", "AT_PHDR", "AT_ENTRY", "AT_PHNUM", "RIP"])
def test_native_acquisition_register_auxv_and_load_bias_must_agree(native_acquisition_case, field):
    files = dict(native_acquisition_case.files)
    if field == "RIP":
        raw = bytearray(files["regs.before.bin"])
        struct.pack_into("<Q", raw, 16 * 8, native_acquisition_case.bases["launcher"] + 0x1010)
        files["regs.before.bin"] = files["regs.after.bin"] = bytes(raw)
    else:
        key = {"AT_BASE": 7, "AT_PHDR": 3, "AT_ENTRY": 9, "AT_PHNUM": 5}[field]
        rows = list(struct.iter_unpack("<QQ", files["auxv.before.bin"]))
        raw = b"".join(struct.pack("<QQ", k, v + (4096 if field != "AT_PHNUM" else 1) if k == key else v)
                       for k, v in rows)
        files["auxv.before.bin"] = files["auxv.after.bin"] = raw
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_verify_changed(native_acquisition_case, files=files)


@pytest.mark.parametrize("change", ["same_name_wrong_inode", "same_name_wrong_offset", "one_segment_bias", "writable_rx"])
def test_native_acquisition_descriptor_relation_cannot_be_replaced_by_a_mapping_name(native_acquisition_case, change):
    files = dict(native_acquisition_case.files)
    rows = files["child.maps.before.bin"].splitlines()
    fields = rows[5].split(b" ", 5)  # Loader's RX row; preserve its display pathname.
    if change == "same_name_wrong_inode": fields[4] = b"987"
    elif change == "same_name_wrong_offset": fields[2] = b"00002000"
    elif change == "writable_rx": fields[1] = b"rwxp"
    else: fields[0] = b"70001800-70002800"
    rows[5] = b" ".join(fields)
    files["child.maps.before.bin"] = files["child.maps.after.bin"] = b"\n".join(rows) + b"\n"
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_verify_changed(native_acquisition_case, files=files)


def test_native_acquisition_mapping_display_name_has_no_authority_over_descriptor_identity(native_acquisition_case):
    files = dict(native_acquisition_case.files)
    for name in ("child.maps.before.bin", "child.maps.after.bin"):
        files[name] = files[name].replace(b"/lib64/ld-linux-x86-64.so.2", b"/untrusted/display-name")
    report = native_acquisition_verify_changed(native_acquisition_case, files=files)
    assert report["interpreter_image_binding_verified"] is True


@pytest.mark.parametrize("object_name", ["executable", "loader_before", "memory"])
def test_native_acquisition_object_mode_overflow_is_a_controlled_rejection(native_acquisition_case, object_name):
    capture = copy.deepcopy(native_acquisition_case.capture)
    capture["objects"][object_name]["stat"]["mode"] = 2**32
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_verify_changed(native_acquisition_case, capture=capture)


@pytest.mark.parametrize("change", ["sample_alias", "native_digest", "missing_relationship", "source_digest"])
def test_native_acquisition_request_cannot_redefine_original_selection_or_per_occurrence_duties(native_acquisition_case, change):
    request = copy.deepcopy(native_acquisition_case.request)
    if change == "sample_alias": request["memory_obligations"][1] = copy.deepcopy(request["memory_obligations"][0])
    elif change == "native_digest": request["native_files"][0]["sha256"] = "0" * 64
    elif change == "missing_relationship": request["native_relationships"].pop()
    else: request["sources"][0]["sha256"] = "0" * 64
    raw = encoded(request)
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_checker().validate_request(raw, digest(raw))


def test_native_acquisition_tracing_denial_receipt_retains_diagnostics_without_observation_claims(native_acquisition_case):
    case, checker = native_acquisition_case, native_acquisition_checker()
    capture = copy.deepcopy(case.capture)
    capture.update(status="incomplete", failure="exec_stop_ptrace_traceme_denied")
    capture["timing"]["stopped_ns"] = None
    capture["wait"].update(setup=126 << 8, exec=None, terminal=126 << 8, event_msg=None)
    capture["ownership"].update(pre_exec_resumes=0, ptrace_options=0, kill_sent=False)
    capture["objects"]["executable"] = capture["objects"]["loader_after"] = capture["objects"]["memory"] = None
    files = {name: raw for name, raw in case.files.items() if name in (
        "request.json", "attempt_start.json", "launcher.elf", "loader.before.elf", "retained.elf", "observer.exe.bin")}
    files.update({"stdout.bin": b"", "stderr.bin": b"ptrace denied\n"})
    report = native_acquisition_verify_changed(case, capture=capture, files=files)
    assert report["status"] == "accepted" and report["observation_complete"] is False
    assert report["kernel_exec_checkpoint_observed"] is False and report["memory_relations"] == []
    assert report["failure"] == "exec_stop_ptrace_traceme_denied"
    for key, value in checker.BOUNDARY.items():
        assert type(report[key]) is type(value) and report[key] == value, key
    capture.update(status="completed", failure=None)
    with pytest.raises(checker.ExecStopError):
        native_acquisition_verify_changed(case, capture=capture, files=files)


def test_native_acquisition_owner_acknowledgement_precedes_verification_and_dispatch(tmp_path, monkeypatch, capfd):
    preparation = native_acquisition_preparation()
    def forbidden(*args, **kwargs):
        pytest.fail("wrong acknowledgement must reject before reading or verifying any original")
    monkeypatch.setattr(preparation.safe, "read_selection_file", forbidden)
    monkeypatch.setattr(preparation, "reconstruct_originals", forbidden)
    monkeypatch.setattr(preparation.distribution_io, "VerificationDirectory", forbidden)
    result = preparation.main([
        "run-owner", "--originals-directory", str(tmp_path / "originals"),
        "--originals-sha256", preparation.ORIGINAL_MANIFEST_SHA256,
        "--verification-directory", str(tmp_path / "verification"),
        "--request", str(tmp_path / "request.json"), "--request-sha256", "0" * 64,
        "--acknowledgement", "RUN_ANY_SELECTED_PAYLOAD", "--output-directory", str(tmp_path / "capture"),
    ])
    assert result == 1
    report = json.loads(capfd.readouterr().out)
    assert report["error_code"] == "exec_stop_owner_acknowledgement"
    assert not (tmp_path / "verification").exists() and not (tmp_path / "capture").exists()


def test_native_acquisition_preparation_requires_the_reviewed_original_manifest_before_reading(tmp_path, monkeypatch):
    preparation = native_acquisition_preparation()
    # A self-consistent caller-selected manifest must not replace the original
    # externally selected 111-file preservation case.
    unrelated = encoded({"record_type": "launcher_distribution_original_byte_example_v0",
                         "record_status": "example", "files": {str(index): {} for index in range(111)}})
    def forbidden(*args, **kwargs):
        pytest.fail("an unreviewed manifest digest must reject before input acquisition")
    monkeypatch.setattr(preparation, "_member", forbidden)
    with pytest.raises(preparation.safe.MappingError, match="exec_stop_original_manifest_selection"):
        preparation.load_originals(tmp_path, digest(unrelated))


def test_native_acquisition_original_member_fifo_substitution_rejects_without_blocking(tmp_path):
    directory = tmp_path / "originals"
    directory.mkdir()
    selected = directory / "selected.json"
    selected.write_bytes(b"preserved original\n")
    script = r'''
import importlib.util, json, os, pathlib, stat, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location("exec_stop_fifo_preparation", sys.argv[1])
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)
directory = pathlib.Path(sys.argv[2])
assert preparation._member(directory, "selected.json", 128) == b"preserved original\n"
original_open, replaced = os.open, []
def replace(name, flags, mode=0o777, *, dir_fd=None):
    if name == "selected.json" and dir_fd is not None and not replaced:
        assert stat.S_ISREG(os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode)
        os.unlink(name, dir_fd=dir_fd)
        os.mkfifo(name, 0o600, dir_fd=dir_fd)
        replaced.append(True)
    return original_open(name, flags, mode, dir_fd=dir_fd)
os.open = replace
try:
    preparation._member(directory, "selected.json", 128)
except preparation.safe.MappingError:
    assert replaced == [True] and (directory / "selected.json").is_fifo()
    print(json.dumps({"fifo_rejected": True}))
else:
    raise AssertionError("substituted FIFO was accepted")
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                             str(ROOT / "tools/prepare_required_gate_idempotence_exec_stop_v0.py"),
                             str(directory)], capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stderr == b"" and json.loads(result.stdout) == {"fifo_rejected": True}


@pytest.mark.parametrize("mismatch", ["payload", "observer", "host_loader"])
def test_native_acquisition_preflight_mismatches_stop_before_any_child(native_acquisition_case, tmp_path, monkeypatch, mismatch):
    case, observer = native_acquisition_case, native_acquisition_subject()
    payload = {path: case.native[path] for path in ("native/bwrap", "native/ld-linux-x86-64.so.2")}
    def forbidden(*args, **kwargs):
        pytest.fail("preflight mismatch must not spawn or execute a native child")
    monkeypatch.setattr(observer, "_spawn_child", forbidden)
    if mismatch == "payload":
        payload["native/bwrap"] += b"changed"
    observer_raw = case.observer_raw + (b"changed" if mismatch == "observer" else b"")
    monkeypatch.setattr(observer, "_actual_observer", lambda: (
        {"path": case.request["observer"]["path"], **bound(observer_raw)}, observer_raw))
    parent = os.getpid()
    def authored_proc(fd, name, limit, deadline):
        return (native_acquisition_proc_stat(parent, 1, "S", 100) if name == "stat"
                else native_acquisition_proc_status(parent, 1, "S", 0))
    monkeypatch.setattr(observer, "_read_proc", authored_proc)
    loader = tmp_path / "inert-loader"
    raw = case.native["native/ld-linux-x86-64.so.2"]
    loader.write_bytes(raw[:-1] + bytes((raw[-1] ^ 1,)) if mismatch == "host_loader" else raw)
    loader.chmod(0o500)
    monkeypatch.setattr(observer, "_open_loader", lambda: os.open(loader, os.O_RDONLY | os.O_NONBLOCK))
    output = tmp_path / "capture"
    arguments = dict(request_bytes=case.request_raw, expected_request_sha256=digest(case.request_raw),
                     native_files=payload, output_directory=output, acknowledgement=observer.ACKNOWLEDGEMENT)
    if mismatch == "payload":
        with pytest.raises(observer.ExecStopObservationError, match="exec_stop_original_binding"):
            observer.run_acquisition(**arguments)
        assert not output.exists()
    else:
        report = observer.run_acquisition(**arguments)
        assert report["observation_complete"] is False and report["kernel_exec_checkpoint_observed"] is False
        assert report["failure"] == {"observer": "exec_stop_observer_selection_mismatch",
                                     "host_loader": "exec_stop_host_loader_selection_mismatch"}[mismatch]
        capture_raw, files = native_acquisition_checker().read_capture_directory(output)
        capture = json.loads(capture_raw)
        assert capture["child_pid"] is None and capture["ownership"]["pre_exec_resumes"] == 0
        assert files["stdout.bin"] == files["stderr.bin"] == b""


def test_native_acquisition_traceme_denial_exits_child_setup_before_stop_or_exec(monkeypatch):
    observer, calls, messages = native_acquisition_subject(), [], []
    class AuthoredExit(BaseException):
        pass
    def terminate(code):
        calls.append(("exit", code))
        raise AuthoredExit
    def deny(request, pid, *args):
        calls.append(("ptrace", request, pid))
        raise PermissionError(errno.EPERM, "authored TRACEME denial")
    def forbidden(*args, **kwargs):
        pytest.fail("denied child setup must not stop, continue or exec an image")
    monkeypatch.setattr(observer.os, "dup2", lambda *args: None)
    monkeypatch.setattr(observer.os, "setsid", lambda: None)
    monkeypatch.setattr(observer.os, "chdir", lambda path: None)
    monkeypatch.setattr(observer.os, "getppid", lambda: 1234)
    monkeypatch.setattr(observer, "_LIBC", SimpleNamespace(prctl=lambda *args: 0))
    monkeypatch.setattr(observer, "_ptrace", deny)
    monkeypatch.setattr(observer.os, "kill", forbidden)
    monkeypatch.setattr(observer.os, "execve", forbidden)
    monkeypatch.setattr(observer.os, "write", lambda fd, raw: messages.append((fd, raw)) or len(raw))
    monkeypatch.setattr(observer.os, "_exit", terminate)
    with pytest.raises(AuthoredExit):
        observer._child_setup(51, 1234, 52, 53, 54, ())
    assert calls == [("ptrace", observer.PTRACE_TRACEME, 0), ("exit", 120)]
    assert messages == [(2, b"exec_stop_child_os_error_1\n")]


@pytest.mark.parametrize("failure", ["option_denied", "setup_deadline"])
def test_native_acquisition_failed_tracing_setup_never_reaches_pre_exec_continue(native_acquisition_case, tmp_path,
                                                                                 monkeypatch, failure):
    case, observer = native_acquisition_case, native_acquisition_subject()
    parent, child = os.getpid(), os.getpid() + 100000
    calls, spawned, cleaned = [], [], []
    loader = tmp_path / "inert-loader"
    loader.write_bytes(case.native["native/ld-linux-x86-64.so.2"])
    loader.chmod(0o500)
    monkeypatch.setattr(observer, "_actual_observer", lambda: (case.request["observer"], case.observer_raw))
    monkeypatch.setattr(observer, "_open_loader", lambda: os.open(loader, os.O_RDONLY | os.O_NONBLOCK))
    original_open = os.open
    def redirect_owned_proc(path, flags, mode=0o777, *, dir_fd=None):
        if path == f"/proc/{child}": path = f"/proc/{parent}"
        return original_open(path, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(observer.os, "open", redirect_owned_proc)
    monkeypatch.setattr(observer.os, "pidfd_open", lambda pid, flags=0: original_open("/dev/null", os.O_RDONLY))
    def authored_proc(fd, name, limit, deadline):
        pid, ppid, state, tracer, start = (child, parent, "t", parent, 200) if spawned else (parent, 1, "S", 0, 100)
        return (native_acquisition_proc_stat(pid, ppid, state, start) if name == "stat"
                else native_acquisition_proc_status(pid, ppid, state, tracer))
    monkeypatch.setattr(observer, "_read_proc", authored_proc)
    def spawn(fd, parent_pid):
        assert parent_pid == parent
        stdout_r, stdout_w = os.pipe()
        stderr_r, stderr_w = os.pipe()
        os.write(stdout_w, b"AB")
        os.write(stderr_w, b"pending setup diagnostics\n")
        os.close(stdout_w)
        os.close(stderr_w)
        process = SimpleNamespace(pid=child, returncode=None,
            stdout=os.fdopen(stdout_r, "rb", buffering=0), stderr=os.fdopen(stderr_r, "rb", buffering=0))
        spawned.append(process)
        return process
    monkeypatch.setattr(observer, "_spawn_child", spawn)
    def wait(process, deadline, capture, phase):
        assert phase == "setup"
        if failure == "setup_deadline":
            raise observer.ExecStopObservationError("exec_stop_wall_deadline")
        capture["wait"]["setup"] = 4991
        return 4991
    monkeypatch.setattr(observer, "_wait_event", wait)
    def deny_option(request, pid, *args):
        calls.append(request)
        assert request == observer.PTRACE_SETOPTIONS
        raise PermissionError(errno.EPERM, "authored SETOPTIONS denial")
    monkeypatch.setattr(observer, "_ptrace", deny_option)
    def cleanup(process, pidfd, capture):
        cleaned.append(process.pid)
        capture["ownership"].update(child_reaped=True, kill_sent=True)
        capture["wait"]["terminal"] = 9
        process.returncode = -9
        return None
    monkeypatch.setattr(observer, "_cleanup", cleanup)
    output = tmp_path / "capture"
    report = observer.run_acquisition(request_bytes=case.request_raw, expected_request_sha256=digest(case.request_raw),
        native_files={path: case.native[path] for path in ("native/bwrap", "native/ld-linux-x86-64.so.2")},
        output_directory=output, acknowledgement=observer.ACKNOWLEDGEMENT)
    assert report["observation_complete"] is False
    assert report["failure"] == ("exec_stop_os_error_1" if failure == "option_denied" else "exec_stop_wall_deadline")
    assert calls == ([observer.PTRACE_SETOPTIONS] if failure == "option_denied" else [])
    assert cleaned == [child]
    capture_raw, files = native_acquisition_checker().read_capture_directory(output)
    capture = json.loads(capture_raw)
    assert capture["ownership"]["pre_exec_resumes"] == capture["ownership"]["post_exec_resumes"] == 0
    assert capture["ownership"]["child_reaped"] is True
    assert files["stdout.bin"] == b"AB" and files["stderr.bin"] == b"pending setup diagnostics\n"
    assert spawned[0].stdout.closed and spawned[0].stderr.closed


@pytest.mark.parametrize("overflow", [None, "stdout", "stderr"])
def test_native_acquisition_failed_attempt_drains_both_pending_streams_to_their_caps(overflow):
    observer, preserved = native_acquisition_subject(), {}
    process = SimpleNamespace(pid=12345, returncode=-9)
    originals = {}
    for name in ("stdout", "stderr"):
        read_fd, write_fd = os.pipe()
        os.set_blocking(write_fd, False)
        raw = (b"O" * (observer.LIMITS[name + "_bytes"] + 1)) if overflow == name else b"AB"
        try:
            assert os.write(write_fd, raw) == len(raw)
        finally:
            os.close(write_fd)
        originals[name] = raw
        setattr(process, name, os.fdopen(read_fd, "rb", buffering=0))
    output = SimpleNamespace(preserve=lambda name, raw: preserved.setdefault(name, raw))
    failure = observer._drain_outputs(process, output, {}, "exec_stop_wall_deadline")
    assert failure == "exec_stop_wall_deadline"
    assert preserved == {name + ".bin": raw[:observer.LIMITS[name + "_bytes"]]
                         for name, raw in originals.items()}
    assert process.stdout.closed and process.stderr.closed


@pytest.mark.parametrize("failure", [None, "deadline", "pidfd_signal"])
def test_native_acquisition_cleanup_only_kills_and_reaps_the_owned_child(monkeypatch, failure):
    observer, signals = native_acquisition_subject(), []
    process = SimpleNamespace(pid=12345, returncode=None)
    capture = {"ownership": {"child_reaped": False, "kill_sent": False}, "wait": {"terminal": None}}
    def signal_pidfd(fd, sig):
        signals.append(("pidfd", fd, sig))
        if failure == "pidfd_signal": raise OSError(errno.EIO, "authored pidfd failure")
    monkeypatch.setattr(observer.signal, "pidfd_send_signal", signal_pidfd)
    monkeypatch.setattr(observer.os, "kill", lambda pid, sig: signals.append(("owned_pid", pid, sig)))
    monkeypatch.setattr(observer.os, "waitpid", lambda pid, flags: (pid, 9))
    if failure == "deadline":
        ticks = iter((0, 3 * 10**9))
        monkeypatch.setattr(observer.time, "monotonic_ns", lambda: next(ticks))
    result = observer._cleanup(process, 42, capture)
    assert all(call[2] == mapping_signal.SIGKILL for call in signals)
    assert signals == [("pidfd", 42, mapping_signal.SIGKILL)] + (
        [("owned_pid", process.pid, mapping_signal.SIGKILL)] if failure == "pidfd_signal" else [])
    if failure == "deadline":
        assert result == "exec_stop_cleanup_deadline" and capture["ownership"]["child_reaped"] is False
    else:
        assert capture["ownership"]["child_reaped"] is True and capture["wait"]["terminal"] == 9
        assert process.returncode == -9
        assert result == ("exec_stop_cleanup_pidfd_signal_failed" if failure == "pidfd_signal" else None)


def native_acquisition_mock_preparation(case, monkeypatch):
    preparation = native_acquisition_preparation()
    manifest = {"files": {str(index): {} for index in range(111)}, "source_file_count": 43,
                "explicit_signature_policy": {"evaluation_time_epoch": 1794787200}}
    closed = []
    monkeypatch.setattr(preparation.distribution_io, "VerificationDirectory", lambda path: SimpleNamespace(
        count=1, close=lambda: closed.append(True)))
    monkeypatch.setattr(preparation, "reconstruct_originals", lambda *args: (manifest, {}))
    monkeypatch.setattr(preparation, "derive_request", lambda *args, **kwargs: copy.deepcopy(case.request))
    monkeypatch.setattr(preparation, "_observer", lambda: case.request["observer"])
    return preparation, manifest, closed


@pytest.mark.parametrize("command", ["prepare", "check"])
def test_native_acquisition_preparation_and_check_do_not_import_the_collector(native_acquisition_case, tmp_path,
                                                                           monkeypatch, capfd, command):
    import builtins
    case = native_acquisition_case
    preparation, manifest, closed = native_acquisition_mock_preparation(case, monkeypatch)
    source = tmp_path / "request.json"
    source.write_bytes(case.request_raw)
    output = tmp_path / "output.json"
    original_import = builtins.__import__
    def forbid_collector(name, *args, **kwargs):
        assert name != "required_gate_idempotence_exec_stop_v0", "preparation imported the execution collector"
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", forbid_collector)
    arguments = [command, "--originals-directory", str(tmp_path / "originals"),
        "--originals-sha256", preparation.ORIGINAL_MANIFEST_SHA256,
        "--verification-directory", str(tmp_path / "verification"), "--output", str(output)]
    arguments += (["--attempt-id", case.request["attempt_id"]] if command == "prepare" else
                  ["--request", str(source), "--request-sha256", digest(case.request_raw)])
    assert preparation.main(arguments) == 0
    report = json.loads(capfd.readouterr().out)
    assert report["status"] == "accepted" and report["native_acquisition_performed"] is False
    assert report["original_exec_reached"] is False and closed == [True]
    if command == "prepare": assert output.read_bytes() == case.request_raw
    else: assert json.loads(output.read_bytes()) == report


def test_native_acquisition_check_requires_exact_fresh_request_reconstruction(native_acquisition_case, tmp_path,
                                                                           monkeypatch, capfd):
    case = native_acquisition_case
    preparation, manifest, closed = native_acquisition_mock_preparation(case, monkeypatch)
    changed = copy.deepcopy(case.request)
    changed["attempt_id"] = "f" * 32
    monkeypatch.setattr(preparation, "derive_request", lambda *args, **kwargs: changed)
    source = tmp_path / "request.json"
    source.write_bytes(case.request_raw)
    output = tmp_path / "must-not-exist.json"
    result = preparation.main(["check", "--originals-directory", str(tmp_path / "originals"),
        "--originals-sha256", preparation.ORIGINAL_MANIFEST_SHA256,
        "--verification-directory", str(tmp_path / "verification"), "--output", str(output),
        "--request", str(source), "--request-sha256", digest(case.request_raw)])
    assert result == 1 and not output.exists() and closed == [True]
    assert json.loads(capfd.readouterr().out)["error_code"] == "exec_stop_request_reconstruction"


def test_native_acquisition_schema_preserves_original_request_and_non_authorizing_record_shapes(native_acquisition_case):
    import jsonschema
    case, checker = native_acquisition_case, native_acquisition_checker()
    schema = json.loads((ROOT / "schemas/required_gate_idempotence_exec_stop_v0.schema.json").read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    # A separate unpatched module supplies the production fixed identities.
    # This only constructs metadata; it never reads or executes native inputs.
    original_profile = module("exec_stop_schema_original_profile", "tools/check_required_gate_idempotence_exec_stop_v0.py")
    original_request = original_profile._request("a" * 32, case.request["observer"])
    validator.validate(original_request)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(case.request)
    validator.validate(case.capture)
    validator.validate(native_acquisition_verify_changed(case))
    manifest = {"files": {str(index): {} for index in range(111)}, "source_file_count": 43,
                "explicit_signature_policy": {"evaluation_time_epoch": 1794787200}}
    validator.validate(native_acquisition_preparation()._preparation_report(case.request_raw, manifest))


@pytest.mark.parametrize("kind", ["request", "capture_member"])
def test_native_acquisition_checker_fifo_substitution_rejects_without_blocking(tmp_path, kind):
    directory = tmp_path / "private-input"
    directory.mkdir(mode=0o700)
    for name, raw in (("request.json", b"request bytes\n"), ("capture.json", b"capture bytes\n"),
                      ("launcher.rx.sample0.bin", b"sample bytes\n")):
        path = directory / name
        path.write_bytes(raw)
        path.chmod(0o600)
    script = r'''
import importlib.util, json, os, pathlib, stat, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location("exec_stop_fifo_checker", sys.argv[1])
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
directory, kind = pathlib.Path(sys.argv[2]), sys.argv[3]
name = "request.json" if kind == "request" else "launcher.rx.sample0.bin"
def read():
    return checker.read_request_file(directory / name) if kind == "request" else checker.read_capture_directory(directory)
read()
original_open, replaced = os.open, []
def replace(path, flags, mode=0o777, *, dir_fd=None):
    if path == name and dir_fd is not None and not replaced:
        assert stat.S_ISREG(os.stat(path, dir_fd=dir_fd, follow_symlinks=False).st_mode)
        os.unlink(path, dir_fd=dir_fd)
        os.mkfifo(path, 0o600, dir_fd=dir_fd)
        replaced.append(True)
    return original_open(path, flags, mode, dir_fd=dir_fd)
os.open = replace
try:
    read()
except checker.ExecStopError:
    assert replaced == [True] and (directory / name).is_fifo()
    print(json.dumps({"fifo_rejected": True, "kind": kind}))
else:
    raise AssertionError("substituted FIFO was accepted")
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                             str(NATIVE_ACQUISITION_CHECKER), str(directory), kind],
                            capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stderr == b"" and json.loads(result.stdout) == {"fifo_rejected": True, "kind": kind}


@pytest.mark.parametrize("change", ["missing", "nonregular", "nonzero_size", "unlinked", "executable"])
def test_native_acquisition_complete_reads_require_a_regular_owned_memory_descriptor(native_acquisition_case, change):
    capture = copy.deepcopy(native_acquisition_case.capture)
    if change == "missing": capture["objects"]["memory"] = None
    elif change == "nonregular": capture["objects"]["memory"]["stat"]["mode"] = stat.S_IFIFO | 0o600
    elif change == "nonzero_size": capture["objects"]["memory"]["stat"]["size"] = 1
    elif change == "executable": capture["objects"]["memory"]["stat"]["mode"] = stat.S_IFREG | 0o700
    else: capture["objects"]["memory"]["stat"]["nlink"] = 0
    with pytest.raises(native_acquisition_checker().ExecStopError):
        native_acquisition_verify_changed(native_acquisition_case, capture=capture)


def test_native_acquisition_observer_with_an_external_tracer_cannot_complete(native_acquisition_case):
    case, files = native_acquisition_case, dict(native_acquisition_case.files)
    files["observer.status.bin"] = mapping_status_field(files["observer.status.bin"], "TracerPid", 999)
    with pytest.raises(native_acquisition_checker().ExecStopError, match="exec_stop_observer_identity"):
        native_acquisition_verify_changed(case, files=files)


# Hosted transport tests execute only authored Python diagnostic children.
def hosted_transport():
    return module("required_gate_idempotence_exec_stop_hosted_io_v0",
                  "tools/required_gate_idempotence_exec_stop_hosted_io_v0.py")


def test_hosted_original_input_carrier_preserves_all_selected_bytes(tmp_path):
    import stat
    transport = hosted_transport()
    selection = transport.original_selection()
    archive = ROOT / transport.ARCHIVE_REL
    before = transport.binding(transport.read_regular(archive, transport.ARCHIVE_SIZE))
    destination = tmp_path / "originals"
    result = transport.extract_originals(archive, destination)
    assert result["archive"] == before == {key: selection["archive"][key]
                                           for key in ("sha256", "size_bytes")}
    assert result["member_count"] == 114 and result["decoded_bytes"] == 72234203
    assert {p.relative_to(destination).as_posix() for p in destination.rglob("*")
            if p.is_file()} == set(selection["files"])
    for name, expected in selection["files"].items():
        raw = transport.read_regular(destination / name, expected["size_bytes"], private=True)
        assert transport.binding(raw) == expected
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o700 for p in destination.rglob("*")
               if p.is_dir())
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert transport.binding(transport.read_regular(archive, transport.ARCHIVE_SIZE)) == before
    assert selection["scope"]["original_launcher_executed_by_preservation"] is False
    assert selection["scope"]["authority_effect"] == "none"


def test_hosted_original_input_archive_digest_precedes_extraction(tmp_path):
    transport = hosted_transport()
    changed = tmp_path / "changed.zip"
    changed.write_bytes(b"not the selected original input archive")
    destination = tmp_path / "originals"
    with pytest.raises(transport.HostedIOError, match="hosted_io_archive_digest"):
        transport.extract_originals(changed, destination)
    assert not destination.exists()


def test_hosted_original_selection_is_anchored_outside_its_own_fields(tmp_path, monkeypatch):
    transport = hosted_transport()
    raw = (ROOT / transport.SELECTION_REL).read_bytes()
    modified = raw.replace(b'"preserved_input"', b'"forged____input"')
    assert modified != raw and len(modified) == len(raw)
    path = tmp_path / transport.SELECTION_REL
    path.parent.mkdir(parents=True)
    path.write_bytes(modified)
    monkeypatch.setattr(transport, "ROOT", tmp_path)
    with pytest.raises(transport.HostedIOError, match="hosted_io_selection_digest"):
        transport.original_selection()


def test_hosted_read_refuses_fifo_substitution_without_waiting_for_writer(tmp_path, monkeypatch):
    transport = hosted_transport()
    path = tmp_path / "selected.bin"
    path.write_bytes(b"selected")
    original_open = os.open
    replaced = False

    def replacing_open(name, flags, *args, **kwargs):
        nonlocal replaced
        if name == "selected.bin" and kwargs.get("dir_fd") is not None and not replaced:
            assert flags & os.O_NONBLOCK
            os.unlink(name, dir_fd=kwargs["dir_fd"])
            os.mkfifo(name, 0o600, dir_fd=kwargs["dir_fd"])
            replaced = True
        return original_open(name, flags, *args, **kwargs)

    monkeypatch.setattr(transport.os, "open", replacing_open)
    with pytest.raises(transport.HostedIOError, match="hosted_io_file_changed"):
        transport.read_regular(path, 32)
    assert replaced


@pytest.mark.parametrize("ancestor", [False, True])
def test_hosted_read_rejects_final_and_ancestor_symlinks(tmp_path, ancestor):
    transport = hosted_transport()
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "file").write_bytes(b"bytes")
    alias = tmp_path / "alias"
    alias.symlink_to(actual if ancestor else actual / "file", target_is_directory=ancestor)
    with pytest.raises(transport.HostedIOError):
        transport.read_regular(alias / "file" if ancestor else alias, 16)


def test_hosted_private_write_is_exclusive_and_does_not_follow_aliases(tmp_path):
    import stat
    transport = hosted_transport()
    path = tmp_path / "kept"
    assert transport.write_new(path, b"first") == transport.binding(b"first")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(transport.HostedIOError):
        transport.write_new(path, b"second")
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(transport.HostedIOError):
        transport.write_new(alias, b"third")
    assert path.read_bytes() == b"first"
    empty = tmp_path / "empty"
    transport.write_new(empty, b"")
    assert transport.read_regular(empty, 0, private=True) == b""


def test_hosted_private_copy_checks_complete_roster_and_restores_modes(tmp_path):
    import stat
    transport = hosted_transport()
    source = tmp_path / "source"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested/file").write_bytes(b"preserved")
    (source / "empty").write_bytes(b"")
    expected = {"nested/file": transport.binding(b"preserved"), "empty": transport.binding(b"")}
    output = tmp_path / "output"
    assert transport.copy_private_tree(source, output, expected) == {
        "member_count": 2, "decoded_bytes": 9}
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "nested").stat().st_mode) == 0o700
    assert transport.read_regular(output / "nested/file", 9, private=True) == b"preserved"
    assert transport.read_regular(output / "empty", 0, private=True) == b""
    with pytest.raises(transport.HostedIOError):
        transport.copy_private_tree(source, output, expected)
    assert (output / "nested/file").read_bytes() == b"preserved"


@pytest.mark.parametrize("fault", ["extra_file", "extra_directory", "digest", "fifo", "alias"])
def test_hosted_private_copy_rejects_unselected_source_before_creating_output(tmp_path, fault):
    transport = hosted_transport()
    source = tmp_path / "source"
    source.mkdir()
    selected = source / "file"
    selected.write_bytes(b"selected")
    expected = {"file": transport.binding(b"selected")}
    if fault == "extra_file":
        (source / "extra").write_bytes(b"extra")
    elif fault == "extra_directory":
        (source / "extra").mkdir()
    elif fault == "digest":
        selected.write_bytes(b"tampered")
    else:
        selected.unlink()
        if fault == "fifo":
            os.mkfifo(selected)
        else:
            outside = tmp_path / "outside"
            outside.write_bytes(b"selected")
            selected.symlink_to(outside)
    output = tmp_path / "output"
    with pytest.raises(transport.HostedIOError):
        transport.copy_private_tree(source, output, expected)
    assert not output.exists()


@pytest.mark.parametrize("name", [".", "../x", "/x", "a//b", "a/./b", "a/../b", "a\\b"])
def test_hosted_private_copy_rejects_noncanonical_member_names(tmp_path, name):
    transport = hosted_transport()
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(transport.HostedIOError, match="hosted_io_member_path"):
        transport.copy_private_tree(source, tmp_path / "output", {name: transport.binding(b"")})


def test_hosted_private_copy_never_creates_output_inside_source(tmp_path):
    transport = hosted_transport()
    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_bytes(b"selected")
    with pytest.raises(transport.HostedIOError, match="hosted_io_copy_destination"):
        transport.copy_private_tree(source, source / "output", {"file": transport.binding(b"selected")})
    assert not (source / "output").exists()


@pytest.mark.parametrize("exit_code", [0, 7])
def test_hosted_command_preserves_both_streams_and_ordinary_exit(tmp_path, exit_code):
    transport = hosted_transport()
    argv = [sys.executable, "-c",
            "import os,sys;os.write(1,b'out');os.write(2,b'err');sys.exit(" + str(exit_code) + ")"]
    logs = tmp_path / "logs"
    secret = "authored-test-secret-not-for-recording"
    result = transport.run_command(argv, logs, "authored", 5, stream_cap=32,
                                   env={"HOSTED_TEST_SECRET": secret})
    assert result["returncode"] == exit_code and result["failure"] is None
    assert result["cleanup"]["child_reaped"] is True
    assert result["stdout"] == transport.binding(b"out")
    assert result["stderr"] == transport.binding(b"err")
    assert transport.read_regular(logs / "authored.stdout.bin", 32, private=True) == b"out"
    assert transport.read_regular(logs / "authored.stderr.bin", 32, private=True) == b"err"
    assert json.loads((logs / "authored.result.json").read_bytes()) == result
    assert json.loads((logs / "authored.argv.json").read_bytes()) == {"argv": argv}
    assert all(secret.encode() not in path.read_bytes() for path in logs.iterdir())


def test_hosted_command_deadline_kills_reaps_and_retains_both_diagnostics(tmp_path):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    result = transport.run_command([sys.executable, "-c",
        "import os,time;os.write(1,b'before');os.write(2,b'deadline');time.sleep(10)"],
        logs, "deadline", 0.25, stream_cap=32)
    assert result["failure"] == "hosted_process_deadline"
    assert result["returncode"] < 0
    assert result["cleanup"]["kill_group_sent"] and result["cleanup"]["child_reaped"]
    assert result["cleanup"]["pending_output_drain_attempted"]
    assert (logs / "deadline.stdout.bin").read_bytes() == b"before"
    assert (logs / "deadline.stderr.bin").read_bytes() == b"deadline"


@pytest.mark.parametrize("stdout_cap", [None, 8])
def test_hosted_command_overflow_drains_other_buffered_stream_after_slow_sink(tmp_path, monkeypatch,
                                                                           stdout_cap):
    import time
    transport = hosted_transport()
    original_write = os.write
    actual_selector = transport.selectors.DefaultSelector
    delayed = False

    class StderrFirstSelector(actual_selector):
        def select(self, timeout=None):
            ready = super().select(timeout)
            stderr = [entry for entry in ready if entry[0].data == "stderr"]
            return stderr[:1] if stderr else ready

    def slow_sink(fd, raw):
        nonlocal delayed
        count = original_write(fd, raw)
        if bytes(raw) == b"A" and not delayed:
            delayed = True
            time.sleep(0.2)
        return count

    monkeypatch.setattr(transport.selectors, "DefaultSelector", StderrFirstSelector)
    monkeypatch.setattr(transport.os, "write", slow_sink)
    logs = tmp_path / "logs"
    result = transport.run_command([sys.executable, "-c",
        "import os,time;os.write(1,b'A');time.sleep(.05);os.write(2,b'E'*64);"
        "os.write(1,b'B');time.sleep(10)"], logs, "overflow", 5, stream_cap=32,
        stdout_cap=stdout_cap)
    assert delayed and result["failure"] == "hosted_process_stderr_limit"
    assert result["overflowed_streams"] == ["stderr"]
    assert result["cleanup"]["child_reaped"] is True
    assert result["stdout"] == transport.binding(b"AB")
    assert (logs / "overflow.stdout.bin").read_bytes() == b"AB"
    assert (logs / "overflow.stderr.bin").read_bytes() == b"E" * 32


@pytest.mark.parametrize("descriptor,stream", [(1, "stdout"), (2, "stderr")])
def test_hosted_command_limits_each_stream_independently(tmp_path, descriptor, stream):
    transport = hosted_transport()
    result = transport.run_command([sys.executable, "-c",
        "import os;os.write(" + str(descriptor) + ",b'Z'*65)"],
        tmp_path / "logs", "limit", 5, stream_cap=64)
    assert result["failure"] == "hosted_process_" + stream + "_limit"
    assert result[stream] == transport.binding(b"Z" * 64)
    assert result["stderr" if stream == "stdout" else "stdout"] == transport.binding(b"")
    assert result["cleanup"]["child_reaped"]


def test_hosted_command_start_failure_still_has_complete_empty_diagnostics(tmp_path):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    result = transport.run_command([str(tmp_path / "missing-program")], logs, "absent", 5)
    assert result["returncode"] is None and result["failure"] == "hosted_process_start_failed"
    assert result["cleanup"]["child_started"] is False
    assert result["stdout"] == result["stderr"] == transport.binding(b"")
    assert json.loads((logs / "absent.result.json").read_bytes()) == result


def test_hosted_command_log_collision_rejects_before_start(tmp_path, monkeypatch):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    logs.mkdir(mode=0o700)
    (logs / "collision.result.json").write_bytes(b"keep original")

    def forbidden_start(*_args, **_kwargs):
        raise AssertionError("child must not start over existing diagnostics")

    monkeypatch.setattr(transport.subprocess, "Popen", forbidden_start)
    with pytest.raises(transport.HostedIOError, match="hosted_process_log_exists"):
        transport.run_command([sys.executable, "-c", "pass"], logs, "collision", 5)
    assert (logs / "collision.result.json").read_bytes() == b"keep original"
    assert len(list(logs.iterdir())) == 1


@pytest.mark.parametrize("label,timeout,cap", [
    ("../escape", 5, 32), ("space name", 5, 32), ("okay", 0, 32),
    ("okay", float("inf"), 32), ("okay", True, 32), ("okay", 5, 0),
    ("okay", 5, True), ("okay", 5, 16777217),
])
def test_hosted_command_invalid_limits_reject_before_creation(tmp_path, label, timeout, cap):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    with pytest.raises(transport.HostedIOError):
        transport.run_command([sys.executable, "-c", "pass"], logs, label, timeout, cap)
    assert not logs.exists()


@pytest.mark.parametrize("stdout_cap", [0, -1, True, 1.0, 268435457])
def test_hosted_command_rejects_invalid_archive_stdout_bound(tmp_path, stdout_cap):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    with pytest.raises(transport.HostedIOError, match="hosted_process_stdout_cap"):
        transport.run_command([sys.executable, "-c", "pass"], logs, "invalid", 5,
                              stdout_cap=stdout_cap)
    assert not logs.exists()


@pytest.mark.parametrize("stdout_cap", [8, 33554432, 268435456])
def test_hosted_command_archive_bound_is_separate_from_stderr_bound(tmp_path, stdout_cap):
    transport = hosted_transport()
    logs = tmp_path / "logs"
    result = transport.run_command([sys.executable, "-c",
        "import os;os.write(1,b'archive');os.write(2,b'err')"], logs, "archive", 5,
        stream_cap=3, stdout_cap=stdout_cap)
    assert result["returncode"] == 0 and result["failure"] is None
    assert result["stdout_cap"] == stdout_cap and result["stream_cap"] == 3
    assert result["stdout"] == transport.binding(b"archive")
    assert result["stderr"] == transport.binding(b"err")


def test_hosted_command_smaller_selected_stdout_bound_is_enforced(tmp_path):
    transport = hosted_transport()
    result = transport.run_command([sys.executable, "-c",
        "import os;os.write(1,b'S'*9)"], tmp_path / "logs", "small", 5,
        stream_cap=32, stdout_cap=8)
    assert result["failure"] == "hosted_process_stdout_limit"
    assert result["stdout_cap"] == 8 and result["stdout"] == transport.binding(b"S" * 8)
    assert result["cleanup"]["child_reaped"]


def test_hosted_private_copy_retains_written_prefix_after_sink_failure(tmp_path, monkeypatch):
    import errno
    transport = hosted_transport()
    source = tmp_path / "source"
    source.mkdir()
    (source / "a").write_bytes(b"first")
    (source / "z").write_bytes(b"second")
    expected = {"a": transport.binding(b"first"), "z": transport.binding(b"second")}
    actual_write = transport._write_at

    def failing_sink(parent, name, raw):
        if name == "z":
            raise OSError(errno.EIO, "authored sink failure")
        return actual_write(parent, name, raw)

    monkeypatch.setattr(transport, "_write_at", failing_sink)
    output = tmp_path / "output"
    with pytest.raises(transport.HostedIOError, match="hosted_io_copy_failed"):
        transport.copy_private_tree(source, output, expected)
    assert transport.read_regular(output / "a", 5, private=True) == b"first"
    assert not (output / "z").exists()
    assert (source / "a").read_bytes() == b"first" and (source / "z").read_bytes() == b"second"


def test_hosted_command_interruption_still_kills_and_reaps_owned_child(tmp_path, monkeypatch):
    transport = hosted_transport()
    actual_start = transport.subprocess.Popen
    actual_selector = transport.selectors.DefaultSelector
    children = []

    def record_child(*args, **kwargs):
        child = actual_start(*args, **kwargs)
        children.append(child)
        return child

    class InterruptedSelector(actual_selector):
        def select(self, timeout=None):
            raise KeyboardInterrupt()

    monkeypatch.setattr(transport.subprocess, "Popen", record_child)
    monkeypatch.setattr(transport.selectors, "DefaultSelector", InterruptedSelector)
    logs = tmp_path / "logs"
    with pytest.raises(KeyboardInterrupt):
        transport.run_command([sys.executable, "-c", "import time;time.sleep(10)"],
                              logs, "interrupted", 5)
    assert len(children) == 1 and children[0].returncode < 0
    assert (logs / "interrupted.argv.json").is_file()
    assert (logs / "interrupted.stdout.bin").is_file()
    assert not (logs / "interrupted.result.json").exists()


# Hosted container boundary tests are pure: no Docker, ptrace or original child.
def hosted_container_runner():
    return module("required_gate_idempotence_exec_stop_hosted_run_v0",
                  "tools/required_gate_idempotence_exec_stop_hosted_run_v0.py")


def hosted_container_context_environment(phase="acquire"):
    runner = hosted_container_runner()
    source = "a" * 40
    return {
        "GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1",
        "GITHUB_REPOSITORY_ID": "1061766508",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": runner.WORKFLOW_REF,
        "EXEC_STOP_ACKNOWLEDGEMENT": runner.ACKNOWLEDGEMENT, "EXEC_STOP_PHASE": phase,
        "EXPECTED_SOURCE_COMMIT": source, "GITHUB_SHA": source,
        "GITHUB_WORKFLOW_SHA": source, "GITHUB_RUN_ID": "123456789",
    }


def test_hosted_container_attempt_changes_with_source_and_run_only():
    runner = hosted_container_runner()
    one = runner.validate_context(hosted_container_context_environment(), "acquire")
    two = runner.validate_context(hosted_container_context_environment("verify"), "verify")
    assert one == two and runner.derive_attempt_id(one) == runner.derive_attempt_id(two)
    assert len(runner.derive_attempt_id(one)) == 32
    changed = dict(one, run_id=one["run_id"] + 1)
    assert runner.derive_attempt_id(changed) != runner.derive_attempt_id(one)
    changed = dict(one, source_commit="b" * 40)
    assert runner.derive_attempt_id(changed) != runner.derive_attempt_id(one)


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REPOSITORY", "somebody/pulse-release-gates-0.1"),
    ("GITHUB_REPOSITORY_ID", "1"), ("GITHUB_EVENT_NAME", "push"),
    ("GITHUB_REF", "refs/heads/topic"), ("GITHUB_ACTOR", "other"),
    ("GITHUB_TRIGGERING_ACTOR", "other"), ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_WORKFLOW_REF", "other.yml@refs/heads/main"),
    ("EXEC_STOP_ACKNOWLEDGEMENT", "yes"), ("EXEC_STOP_PHASE", "verify"),
    ("EXPECTED_SOURCE_COMMIT", "A" * 40), ("EXPECTED_SOURCE_COMMIT", "a" * 39),
    ("GITHUB_SHA", "b" * 40), ("GITHUB_WORKFLOW_SHA", "b" * 40),
    ("GITHUB_RUN_ID", "0"), ("GITHUB_RUN_ID", "01"),
    ("GITHUB_RUN_ID", "1\n"), ("GITHUB_RUN_ID", "1" * 21),
])
def test_hosted_container_context_rejects_a_changed_dispatch(key, value):
    runner = hosted_container_runner()
    environment = hosted_container_context_environment()
    environment[key] = value
    with pytest.raises(runner.HostedRunError):
        runner.validate_context(environment, "acquire")


def hosted_container_status(**changes):
    values = {
        "Name": "python3.11", "Uid": "1001 1001 1001 1001",
        "Gid": "1002 1002 1002 1002", "Threads": "1", "TracerPid": "0",
        "NoNewPrivs": "1", "Seccomp": "2",
        **{name: "0000000000000000" for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
    }
    values.update(changes)
    return "".join(name + ":\t" + value + "\n" for name, value in values.items()).encode()


def test_hosted_container_status_accepts_only_untraced_single_thread_unprivileged_profile():
    runner = hosted_container_runner()
    actual = runner.validate_process_status(hosted_container_status(), 1001, 1002)
    assert actual["Seccomp"] == "2" and actual["CapBnd"] == "0" * 16


@pytest.mark.parametrize("key,value", [
    ("Threads", "2"), ("TracerPid", "10"), ("NoNewPrivs", "0"), ("Seccomp", "0"),
    ("Seccomp", "1"), ("CapInh", "0000000000000001"), ("CapPrm", "0000000000000001"),
    ("CapEff", "0000000000000001"), ("CapBnd", "0000000000000001"),
    ("CapAmb", "0000000000000001"), ("CapEff", "not_hexadecimal"),
    ("Uid", "1001 0 1001 1001"), ("Gid", "1002 1002 0 1002"),
])
def test_hosted_container_status_rejects_capability_or_identity_changes(key, value):
    runner = hosted_container_runner()
    with pytest.raises(runner.HostedRunError):
        runner.validate_process_status(hosted_container_status(**{key: value}), 1001, 1002)


@pytest.mark.parametrize("uid,gid", [(0, 1002), (1001, 0), (True, 1002)])
def test_hosted_container_status_rejects_root_or_boolean_identity(uid, gid):
    runner = hosted_container_runner()
    with pytest.raises(runner.HostedRunError):
        runner.validate_process_status(hosted_container_status(), uid, gid)


def test_hosted_container_status_rejects_duplicate_fields():
    runner = hosted_container_runner()
    with pytest.raises(runner.HostedRunError, match="status_duplicate"):
        runner.validate_process_status(hosted_container_status() + b"Seccomp:\t2\n", 1001, 1002)


def hosted_container_complete_report():
    runner = hosted_container_runner()
    return {
        "record_type": "required_gate_idempotence_exec_stop_verification_v0",
        "profile": runner.PROFILE, "status": "accepted", "attempt_id": "c" * 32,
        "request_sha256": "d" * 64, "capture_sha256": "e" * 64,
        "observation_record_verified": True, "observation_complete": True,
        **{name: True for name in runner.NARROW_FLAGS},
        "failure": None, "authority_effect": "none",
    }


def test_hosted_container_complete_report_requires_the_exact_attempt_and_bindings():
    runner = hosted_container_runner()
    report = hosted_container_complete_report()
    assert runner.complete_report(report, "c" * 32, "d" * 64, "e" * 64)
    assert not runner.complete_report(report, "f" * 32, "d" * 64, "e" * 64)
    assert not runner.complete_report(report, "c" * 32, "f" * 64, "e" * 64)
    assert not runner.complete_report(report, "c" * 32, "d" * 64, "f" * 64)


@pytest.mark.parametrize("field", [
    "observation_record_verified", "observation_complete", "kernel_exec_checkpoint_observed",
    "launcher_image_binding_verified", "interpreter_image_binding_verified",
    "selected_exec_memory_ranges_observed", "selected_exec_rx_ranges_match_original",
    "owned_exec_stop_cleanup_verified",
])
@pytest.mark.parametrize("value", [False, 1, None])
def test_hosted_container_accepted_incomplete_report_never_completes(field, value):
    runner = hosted_container_runner()
    report = hosted_container_complete_report()
    report[field] = value
    assert not runner.complete_report(report, "c" * 32, "d" * 64, "e" * 64)


@pytest.mark.parametrize("result", [
    {"returncode": 1, "failure": None}, {"returncode": None, "failure": None},
    {"returncode": False, "failure": None}, {"returncode": 0, "failure": "hosted_process_deadline"},
])
def test_hosted_container_process_failure_never_counts_as_success(result):
    runner = hosted_container_runner()
    assert not runner.command_succeeded(result)
    assert runner.command_succeeded({"returncode": 0, "failure": None})


def test_hosted_container_canonical_reports_cannot_hide_format_or_duplicate_key_changes():
    runner = hosted_container_runner()
    assert runner._canonical_json(b'{"a":1}\n') == {"a": 1}
    for raw in (b'{ "a": 1 }\n', b'{"a":1,"a":1}\n', b'{"a":NaN}\n', b'[]\n', b'null\n'):
        with pytest.raises(ValueError):
            runner._canonical_json(raw)


def test_hosted_container_capture_roster_comes_only_from_receipt_prefix():
    runner = hosted_container_runner()
    descriptor = {"sha256": "a" * 64, "size_bytes": 1}
    receipt = {"files": {
        "observation/capture/capture.json": descriptor,
        "observation/capture/request.json": descriptor,
        "other/capture.json": descriptor,
        "observation/commands/acquisition.result.json": descriptor,
    }}
    assert runner.capture_inventory(receipt) == {"capture.json": descriptor, "request.json": descriptor}
    receipt["files"]["observation/capture/../escape.bin"] = descriptor
    with pytest.raises(ValueError):
        runner.capture_inventory(receipt)


@pytest.mark.parametrize("missing", ["capture.json", "request.json"])
def test_hosted_container_missing_capture_remains_an_incomplete_attempt(missing):
    runner = hosted_container_runner()
    descriptor = {"sha256": "a" * 64, "size_bytes": 1}
    receipt = {"files": {"observation/capture/" + name: descriptor
                         for name in ("capture.json", "request.json") if name != missing}}
    with pytest.raises(runner.HostedRunError, match="receipt_capture_missing"):
        runner.capture_inventory(receipt)


def test_hosted_container_fixed_request_observer_cannot_be_replaced():
    runner = hosted_container_runner()
    request = {"profile": runner.PROFILE, "attempt_id": "c" * 32,
               "observer": {"path": runner.PYTHON, **runner.EXPECTED_FILES[runner.PYTHON]}}
    raw = runner.io.canonical(request)
    assert runner._request(raw, "c" * 32) == request
    request["observer"]["path"] = "/tmp/python"
    with pytest.raises(runner.HostedRunError, match="request_observer"):
        runner._request(runner.io.canonical(request), "c" * 32)


# Hosted original-launcher workflow: no original acquisition is executed here.
HOSTED_EXEC_STOP_WORKFLOW = ".github/workflows/required_gate_idempotence_exec_stop_v0.yml"
HOSTED_EXEC_STOP_WORKFLOW_SHA256 = "8f4ec694d60e455273d2e29bccae289a7821363781ddb8c5b05096b01534b182"


def hosted_exec_stop_workflow():
    import yaml
    return yaml.load((ROOT / HOSTED_EXEC_STOP_WORKFLOW).read_text(), Loader=yaml.BaseLoader)


def hosted_exec_stop_step(job, identifier):
    return next(step for step in job["steps"] if step.get("id") == identifier)


def hosted_exec_stop_guard_environment(phase="acquire"):
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1", "GITHUB_REPOSITORY_ID": "1061766508",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "987654321",
        "EXPECTED_SOURCE_COMMIT": "a" * 40, "GITHUB_SHA": "a" * 40,
        "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_WORKFLOW_REF": "HKati/pulse-release-gates-0.1/" + HOSTED_EXEC_STOP_WORKFLOW + "@refs/heads/main",
        "EXEC_STOP_ACKNOWLEDGEMENT": "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY",
        "EXEC_STOP_PHASE": phase, "EXEC_STOP_ARTIFACT_ID": "123456789",
        "EXPECTED_RECEIPT_SHA256": "b" * 64,
    }


def test_hosted_exec_stop_workflow_is_manual_owner_scoped_and_has_separate_signer_permissions():
    value = hosted_exec_stop_workflow()
    assert set(value["on"]) == {"workflow_dispatch"}
    assert set(value["on"]["workflow_dispatch"]["inputs"]) == {"expected_source_commit", "acknowledgement"}
    assert value["permissions"] == {"contents": "read"}
    assert value["concurrency"] == {
        "group": "pulsemech-required-gate-idempotence-exec-stop-v0", "cancel-in-progress": "false"}
    assert set(value["jobs"]) == {"acquire", "verify"}
    acquire, verify = value["jobs"]["acquire"], value["jobs"]["verify"]
    assert acquire["permissions"] == {"contents": "read"}
    assert verify["permissions"] == {
        "contents": "read", "actions": "read", "id-token": "write", "attestations": "write"}
    for name, job in value["jobs"].items():
        assert job["runs-on"] == "ubuntu-24.04" and int(job["timeout-minutes"]) <= 30
        assert job["steps"][0]["id"] == "context"
        assert job["env"]["EXEC_STOP_PHASE"] == name
        assert job["env"]["EXPECTED_SOURCE_COMMIT"] == "${{ inputs.expected_source_commit }}"
        assert job["env"]["EXEC_STOP_ACKNOWLEDGEMENT"] == "${{ inputs.acknowledgement }}"
        assert "GH_TOKEN" not in job["env"] and "GITHUB_TOKEN" not in job["env"]
        assert all("continue-on-error" not in step for step in job["steps"])


@pytest.mark.parametrize("phase", ["acquire", "verify"])
def test_hosted_exec_stop_actual_context_guard_accepts_the_exact_owner_context(phase):
    guard = hosted_exec_stop_step(hosted_exec_stop_workflow()["jobs"][phase], "context")["run"]
    result = subprocess.run(["bash", "-c", guard], env=hosted_exec_stop_guard_environment(phase),
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


@pytest.mark.parametrize("phase", ["acquire", "verify"])
@pytest.mark.parametrize("field,value", [
    ("GITHUB_REPOSITORY", "other/pulse-release-gates-0.1"),
    ("GITHUB_REPOSITORY_ID", "1061766509"),
    ("GITHUB_EVENT_NAME", "pull_request"),
    ("GITHUB_REF", "refs/heads/unreviewed"),
    ("GITHUB_ACTOR", "other"),
    ("GITHUB_TRIGGERING_ACTOR", "other"),
    ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_RUN_ID", "0"),
    ("EXPECTED_SOURCE_COMMIT", "b" * 40),
    ("GITHUB_WORKFLOW_SHA", "b" * 40),
    ("GITHUB_WORKFLOW_REF", "HKati/pulse-release-gates-0.1/.github/workflows/other.yml@refs/heads/main"),
    ("EXEC_STOP_ACKNOWLEDGEMENT", "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY "),
])
def test_hosted_exec_stop_actual_context_guard_rejects_independent_identity_drift(phase, field, value):
    guard = hosted_exec_stop_step(hosted_exec_stop_workflow()["jobs"][phase], "context")["run"]
    environment = hosted_exec_stop_guard_environment(phase)
    environment[field] = value
    result = subprocess.run(["bash", "-c", guard], env=environment,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode != 0


@pytest.mark.parametrize("field,value", [
    ("EXEC_STOP_ARTIFACT_ID", ""), ("EXEC_STOP_ARTIFACT_ID", "0"),
    ("EXPECTED_RECEIPT_SHA256", ""), ("EXPECTED_RECEIPT_SHA256", "b" * 63),
])
def test_hosted_exec_stop_verification_guard_requires_an_external_current_run_handoff(field, value):
    guard = hosted_exec_stop_step(hosted_exec_stop_workflow()["jobs"]["verify"], "context")["run"]
    environment = hosted_exec_stop_guard_environment("verify")
    environment[field] = value
    result = subprocess.run(["bash", "-c", guard], env=environment,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode != 0


@pytest.mark.parametrize("phase", ["acquire", "verify"])
def test_hosted_exec_stop_actual_prefix_preserves_exact_start_context_privately(tmp_path, phase):
    prefix = hosted_exec_stop_step(hosted_exec_stop_workflow()["jobs"][phase], "prefix")["run"]
    environment = hosted_exec_stop_guard_environment(phase)
    environment["RUNNER_TEMP"] = str(tmp_path)
    result = subprocess.run(["bash", "-c", prefix], env=environment,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    name = "required-gate-exec-stop-" + ("verification-" if phase == "verify" else "") + "987654321-1"
    root = tmp_path / name
    record = root / "workflow-start.json"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(record.stat().st_mode) == 0o600
    assert json.loads(record.read_bytes()) == {
        "format": "required_gate_idempotence_exec_stop_workflow_start_v0", "phase": phase,
        "repository": "HKati/pulse-release-gates-0.1", "repository_id": "1061766508",
        "source_commit": "a" * 40, "workflow_sha": "a" * 40,
        "workflow_ref": environment["GITHUB_WORKFLOW_REF"], "run_id": 987654321, "run_attempt": 1,
        "event_name": "workflow_dispatch", "ref": "refs/heads/main", "actor": "HKati",
        "triggering_actor": "HKati", "acknowledgement": "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY",
        "selected_runtime_executed": False, "authority_effect": "none"}
    before = record.read_bytes()
    repeated = subprocess.run(["bash", "-c", prefix], env=environment,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert repeated.returncode != 0 and record.read_bytes() == before


def test_hosted_exec_stop_workflow_actions_are_immutable_and_checkout_has_no_write_credentials():
    pins = {
        "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
        "actions/download-artifact": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
        "actions/attest": "f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"}
    for job in hosted_exec_stop_workflow()["jobs"].values():
        for step in job["steps"]:
            if "uses" not in step:
                continue
            action, revision = step["uses"].split("@")
            assert revision == pins[action]
            if action == "actions/checkout":
                assert step["with"] == {
                    "ref": "${{ github.sha }}", "fetch-depth": "1", "persist-credentials": "false"}
    text = (ROOT / HOSTED_EXEC_STOP_WORKFLOW).read_text()
    assert "setup-python" not in text and "python-version:" not in text


def test_hosted_exec_stop_workflow_checks_failed_attempts_and_preserves_both_prefixes():
    jobs = hosted_exec_stop_workflow()["jobs"]
    acquire, verify = jobs["acquire"], jobs["verify"]
    ids = [step.get("id") for step in acquire["steps"]]
    assert ids.index("context") < ids.index("prefix") < ids.index("checkout") < ids.index("acquire")
    assert ids.index("acquire") < ids.index("finalize") < ids.index("preserve")
    assert hosted_exec_stop_step(acquire, "finalize")["if"] == (
        "always() && steps.prefix.outcome == 'success' && steps.checkout.outcome == 'success'")
    assert "always()" in verify["if"] and "needs.acquire.result == 'success'" not in verify["if"]
    assert "needs.acquire.outputs.artifact_id != ''" in verify["if"]
    assert "needs.acquire.outputs.receipt_sha256 != ''" in verify["if"]
    for job in jobs.values():
        uploads = [step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
        assert len(uploads) == 1
        upload = uploads[0]
        assert upload["if"] == "always() && steps.prefix.outcome == 'success'"
        assert upload["with"]["overwrite"] == "false" and upload["with"]["if-no-files-found"] == "error"
        assert upload["with"]["compression-level"] == "0" and upload["with"]["retention-days"] == "90"
        assert upload["with"]["include-hidden-files"] == "true"
        assert "${{ github.run_id }}-${{ github.run_attempt }}" in upload["with"]["name"]


def test_hosted_exec_stop_workflow_pins_download_receipt_and_attests_only_completed_verification():
    acquire, verify = (hosted_exec_stop_workflow()["jobs"][name] for name in ("acquire", "verify"))
    assert acquire["outputs"]["artifact_id"] == "${{ steps.preserve.outputs.artifact-id }}"
    assert acquire["outputs"]["receipt_sha256"] == "${{ steps.finalize.outputs.receipt_sha256 }}"
    download = next(step for step in verify["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    assert download["with"]["artifact-ids"] == "${{ needs.acquire.outputs.artifact_id }}"
    assert download["with"]["repository"] == "${{ github.repository }}"
    assert download["with"]["run-id"] == "${{ github.run_id }}"
    assert download["with"]["digest-mismatch"] == "error" and "name" not in download["with"]
    checked = hosted_exec_stop_step(verify, "verify")["run"]
    assert 'exec_stop_hosted_v0.py verify' in checked
    assert '--receipt-sha256 "$EXPECTED_RECEIPT_SHA256"' in checked
    assert 'exec_stop_hosted_v0.py acquire' not in "\n".join(step.get("run", "") for step in verify["steps"])
    attest = hosted_exec_stop_step(verify, "attest")
    assert attest["if"] == "success() && steps.verify.outcome == 'success'"
    assert attest["with"]["subject-path"].endswith("/verified-binding.json")
    assert attest["with"]["create-storage-record"] == "false"
    assert "predicate" not in attest["with"] and "predicate-type" not in attest["with"]
    signature = hosted_exec_stop_step(verify, "attest_verify")
    assert signature["if"] == "success() && steps.attest.outcome == 'success'"
    assert 'exec_stop_hosted_v0.py attest-verify' in signature["run"]
    assert signature["env"]["GH_TOKEN"] == "${{ github.token }}"
    for step in verify["steps"]:
        if step.get("id") != "attest_verify":
            assert "GH_TOKEN" not in step.get("env", {})


def test_hosted_exec_stop_workflow_shell_and_embedded_python_parse_without_acquisition(tmp_path):
    import ast
    import re
    for name, job in hosted_exec_stop_workflow()["jobs"].items():
        for index, step in enumerate(job["steps"]):
            if "run" not in step:
                continue
            script = tmp_path / (name + "-" + str(index) + ".sh")
            script.write_text(step["run"])
            result = subprocess.run(["bash", "-n", str(script)], capture_output=True, timeout=5)
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            for snippet in re.findall(r"<<'PY'[^\n]*\n(.*?)^PY$", step["run"], re.MULTILINE | re.DOTALL):
                ast.parse(snippet, feature_version=(3, 11))


def hosted_exec_stop_classifier():
    return module("hosted_exec_stop_normative_inventory", "scripts/build_normative_shadow_inventory_v0.py")


def test_hosted_exec_stop_exact_workflow_has_observation_provenance_without_release_authority():
    path = ROOT / HOSTED_EXEC_STOP_WORKFLOW
    assert digest(path.read_bytes()) == HOSTED_EXEC_STOP_WORKFLOW_SHA256
    item = hosted_exec_stop_classifier().classify_workflow(path, repo_root=ROOT)
    assert item["primary_role"] == "non-authorizing original-launcher exec-stop observation workflow"
    assert item["carrier_class"] == "audit_preservation" and item["authority_impacting"] == "no"
    assert item["required_gate_participation"] is False and item["release_path_participation"] is False
    assert item["attestation_participation"] is True
    assert "no continuation or detach after PTRACE_EVENT_EXEC" in item["authority_boundary"]
    assert "incomplete" in item["notes"] and "keep #2879 open" in item["notes"]


@pytest.mark.parametrize("fault", ["name", "permission", "trigger", "target", "retention", "newline", "crlf", "symlink"])
def test_hosted_exec_stop_changed_workflow_does_not_inherit_reviewed_classification(tmp_path, fault):
    path = tmp_path / HOSTED_EXEC_STOP_WORKFLOW
    path.parent.mkdir(parents=True)
    original = (ROOT / HOSTED_EXEC_STOP_WORKFLOW).read_bytes()
    changes = {
        "name": (b"PULSEmech original launcher exec-stop observation v0", b"Changed observation"),
        "permission": (b"contents: read", b"contents: write"),
        "trigger": (b"workflow_dispatch:", b"push:"),
        "target": (b"/verified-binding.json", b"/other-binding.json"),
        "retention": (b"retention-days: 90", b"retention-days: 1"),
        "crlf": (b"\n", b"\r\n")}
    if fault == "symlink":
        saved = tmp_path / "original-workflow.txt"
        saved.write_bytes(original)
        path.symlink_to(saved)
    elif fault == "newline":
        path.write_bytes(original + b"\n")
    else:
        old, new = changes[fault]
        assert old in original
        path.write_bytes(original.replace(old, new))
    item = hosted_exec_stop_classifier().classify_workflow(path, repo_root=tmp_path)
    assert item["primary_role"] == "unclassified workflow" and item["authority_impacting"] == "conditional"
    assert hosted_exec_stop_classifier().drift_findings([item]) == [{
        "severity": "warning", "path": HOSTED_EXEC_STOP_WORKFLOW,
        "finding": "workflow requires explicit carrier-role classification"}]


def test_hosted_exec_stop_identical_workflow_at_another_path_is_not_reviewed(tmp_path):
    path = tmp_path / ".github/workflows/unreviewed_exec_stop_neighbor.yml"
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / HOSTED_EXEC_STOP_WORKFLOW).read_bytes())
    item = hosted_exec_stop_classifier().classify_workflow(path, repo_root=tmp_path)
    assert item["primary_role"] == "unclassified workflow" and item["authority_impacting"] == "conditional"


# Host bridge regressions: Docker, original acquisition and GH are substituted.
def hosted_driver():
    return module("required_gate_idempotence_exec_stop_hosted_v0",
                  "tools/required_gate_idempotence_exec_stop_hosted_v0.py")


def hosted_driver_environment(phase="acquire"):
    return {
        "EXPECTED_SOURCE_COMMIT": "a" * 40,
        "GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1", "GITHUB_REPOSITORY_ID": "1061766508",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "987654321",
        "GITHUB_SHA": "a" * 40, "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_WORKFLOW_REF": "HKati/pulse-release-gates-0.1/.github/workflows/required_gate_idempotence_exec_stop_v0.yml@refs/heads/main",
        "EXEC_STOP_ACKNOWLEDGEMENT": "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY",
        "EXEC_STOP_PHASE": phase, "EXEC_STOP_ARTIFACT_ID": "123456789",
    }


def hosted_driver_context():
    return hosted_driver().context(hosted_driver_environment())


def hosted_driver_prefix(root, phase, context):
    root.mkdir(mode=0o700)
    value = {"format": "required_gate_idempotence_exec_stop_workflow_start_v0", "phase": phase,
             **context, "selected_runtime_executed": False, "authority_effect": "none"}
    hosted_driver().io.write_new(root / "workflow-start.json", encoded(value))


def hosted_driver_receipt(monkeypatch, *, sources_present=True, request_present=True, capture_present=True):
    driver = hosted_driver()
    context = hosted_driver_context()
    sources = {"tools/reviewed-source.py": bound(b"pass\n")}
    monkeypatch.setattr(driver, "source_bindings", lambda: copy.deepcopy(sources))
    payloads = {"workflow-start.json": encoded({"preserved": "authored acquisition prefix"})}
    if sources_present:
        payloads["source/tools/reviewed-source.py"] = b"pass\n"
    if request_present:
        payloads["observation/request.json"] = encoded({"request": "authored; never executed"})
    if capture_present:
        payloads["observation/capture/capture.json"] = encoded({"status": "incomplete"})
    files = {name: bound(raw) for name, raw in sorted(payloads.items())}
    record = {
        "record_type": "required_gate_idempotence_exec_stop_hosted_receipt_v0", "profile": driver.PROFILE,
        "context": context, "files": files, "file_count": len(files),
        "total_size_bytes": sum(len(raw) for raw in payloads.values()),
        "source_bindings": sources, "source_prefix_complete": sources_present,
        "request": files.get("observation/request.json"),
        "capture": files.get("observation/capture/capture.json"),
        "preservation_is_observation_acceptance": False, **driver.BOUNDARY,
    }
    return context, payloads, record


def hosted_driver_tree(root, payloads):
    root.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        hosted_driver().io.write_new(path, raw)


def test_hosted_driver_context_requires_all_identity_fields_without_coercion():
    result = hosted_driver_context()
    assert result["repository_id"] == "1061766508"
    assert type(result["run_id"]) is int and result["run_id"] == 987654321
    assert type(result["run_attempt"]) is int and result["run_attempt"] == 1
    assert result["source_commit"] == result["workflow_sha"] == "a" * 40


@pytest.mark.parametrize("field,value", [
    ("EXPECTED_SOURCE_COMMIT", "A" * 40), ("EXPECTED_SOURCE_COMMIT", "a" * 39),
    ("GITHUB_REPOSITORY", "other/repo"), ("GITHUB_REPOSITORY_ID", "1061766509"),
    ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_REF", "refs/heads/unreviewed"),
    ("GITHUB_ACTOR", "other"), ("GITHUB_TRIGGERING_ACTOR", "other"),
    ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_RUN_ATTEMPT", 1),
    ("GITHUB_RUN_ID", "0"), ("GITHUB_RUN_ID", "01"), ("GITHUB_RUN_ID", "1" * 21),
    ("GITHUB_SHA", "b" * 40), ("GITHUB_WORKFLOW_SHA", "b" * 40),
    ("GITHUB_WORKFLOW_REF", "HKati/pulse-release-gates-0.1/.github/workflows/other.yml@refs/heads/main"),
    ("EXEC_STOP_ACKNOWLEDGEMENT", "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY "),
])
def test_hosted_driver_rejects_independent_context_drift(field, value):
    environment = hosted_driver_environment()
    environment[field] = value
    with pytest.raises((ValueError, TypeError)):
        hosted_driver().context(environment)


@pytest.mark.parametrize("phase", ["acquire", "verify"])
def test_hosted_driver_container_argv_is_nonroot_fixed_and_does_not_forward_tokens(tmp_path, monkeypatch, phase):
    driver = hosted_driver()
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(key, "SECRET_DO_NOT_FORWARD_" + key)
    original, output, previous = (tmp_path / name for name in ("originals", "output", "previous"))
    argv = driver.docker_create_args("sha256:" + "c" * 64, hosted_driver_context(), original, output,
                                    phase=phase, previous=previous if phase == "verify" else None,
                                    uid=1001, gid=1002)
    options = lambda name: [argv[i + 1] for i, item in enumerate(argv[:-1]) if item == name]
    assert argv[:2] == ["docker", "create"]
    assert options("--user") == ["1001:1002"] and options("--network") == ["none"]
    assert options("--cap-drop") == ["ALL"] and options("--security-opt") == ["no-new-privileges"]
    assert "--read-only" in argv and "--privileged" not in argv and "--cap-add" not in argv
    assert options("--pids-limit") == ["64"] and options("--memory") == ["1g"]
    assert options("--cpus") == ["1"] and options("--tmpfs") == ["/tmp:rw,nosuid,nodev,size=64m"]
    mounts = options("--mount")
    assert "type=bind,source=" + str(driver.ROOT) + ",target=/repo,readonly" in mounts
    assert "type=bind,source=" + str(original) + ",target=/originals,readonly" in mounts
    assert "type=bind,source=" + str(output) + ",target=/output" in mounts
    assert len(mounts) == (4 if phase == "verify" else 3)
    if phase == "verify":
        assert "type=bind,source=" + str(previous) + ",target=/input,readonly" in mounts
    environment = dict(value.split("=", 1) for value in options("--env"))
    assert environment["EXEC_STOP_PHASE"] == phase
    assert environment["EXPECTED_SOURCE_COMMIT"] == "a" * 40
    assert not any("TOKEN" in key or "SECRET" in key for key in environment)
    assert not any("SECRET_DO_NOT_FORWARD" in value for value in argv)
    assert not any("unconfined" in value for value in argv)
    assert argv[-4:] == ["-I", "-B", "/repo/tools/required_gate_idempotence_exec_stop_hosted_run_v0.py", phase]


@pytest.mark.parametrize("uid,gid", [(0, 1001), (1001, 0), (-1, 1001), (True, 1001), (1001, False)])
def test_hosted_driver_container_rejects_root_or_noninteger_identity(tmp_path, uid, gid):
    with pytest.raises(ValueError, match="hosted_nonroot_user"):
        hosted_driver().docker_create_args("sha256:" + "c" * 64, hosted_driver_context(),
                                          tmp_path / "originals", tmp_path / "output",
                                          phase="acquire", uid=uid, gid=gid)


@pytest.mark.parametrize("phase,previous", [("other", None), ("verify", None), ("acquire", "/input")])
def test_hosted_driver_container_rejects_phase_input_confusion(tmp_path, phase, previous):
    with pytest.raises(ValueError, match="hosted_container_phase"):
        hosted_driver().docker_create_args("sha256:" + "c" * 64, hosted_driver_context(),
                                          tmp_path / "originals", tmp_path / "output",
                                          phase=phase, previous=previous, uid=1001, gid=1002)


def test_hosted_driver_receipt_is_anchored_by_the_external_digest(monkeypatch):
    context, _payloads, record = hosted_driver_receipt(monkeypatch)
    raw = encoded(record)
    assert hosted_driver().validate_receipt(raw, digest(raw), context) == record
    with pytest.raises(ValueError, match="hosted_receipt_digest"):
        hosted_driver().validate_receipt(raw, "0" * 64, context)
    changed = copy.deepcopy(record)
    changed["context"]["source_commit"] = "b" * 40
    with pytest.raises(ValueError, match="hosted_receipt_digest"):
        hosted_driver().validate_receipt(encoded(changed), digest(raw), context)


@pytest.mark.parametrize("fault", [
    "source_commit", "run_id", "run_attempt_type", "profile", "authority", "boundary_type",
    "extra_field", "file_count", "total_size", "source_binding", "source_prefix",
    "request_binding", "capture_binding", "self_binding", "parent_path", "absolute_path",
])
def test_hosted_driver_rejects_rehashed_inconsistent_receipts(monkeypatch, fault):
    context, _payloads, record = hosted_driver_receipt(monkeypatch)
    value = copy.deepcopy(record)
    if fault == "source_commit":
        value["context"]["source_commit"] = "b" * 40
    elif fault == "run_id":
        value["context"]["run_id"] += 1
    elif fault == "run_attempt_type":
        value["context"]["run_attempt"] = True
    elif fault == "profile":
        value["profile"] = "other"
    elif fault == "authority":
        value["authority_effect"] = "release"
    elif fault == "boundary_type":
        value["selected_runtime_executed"] = 0
    elif fault == "extra_field":
        value["accepted"] = True
    elif fault == "file_count":
        value["file_count"] += 1
    elif fault == "total_size":
        value["total_size_bytes"] += 1
    elif fault == "source_binding":
        value["source_bindings"]["tools/reviewed-source.py"]["sha256"] = "b" * 64
    elif fault == "source_prefix":
        value["source_prefix_complete"] = False
    elif fault in {"request_binding", "capture_binding"}:
        value[fault.removesuffix("_binding")] = bound(b"other bytes")
    else:
        name = {"self_binding": "receipt.json", "parent_path": "../escaped", "absolute_path": "/escaped"}[fault]
        value["files"][name] = bound(b"x")
        value["file_count"] += 1
        value["total_size_bytes"] += 1
    raw = encoded(value)
    with pytest.raises(ValueError):
        hosted_driver().validate_receipt(raw, digest(raw), context)


def test_hosted_driver_receipt_rejects_reformatted_json_with_a_new_digest(monkeypatch):
    context, _payloads, record = hosted_driver_receipt(monkeypatch)
    raw = json.dumps(record, indent=2).encode()
    with pytest.raises(ValueError, match="hosted_receipt_shape"):
        hosted_driver().validate_receipt(raw, digest(raw), context)


@pytest.mark.parametrize("missing", ["sources", "request", "capture"])
def test_hosted_driver_verifies_incomplete_prefix_bytes_then_stops_before_environment(tmp_path, monkeypatch, missing):
    driver = hosted_driver()
    context, payloads, record = hosted_driver_receipt(
        monkeypatch, sources_present=missing != "sources", request_present=missing != "request",
        capture_present=missing != "capture")
    raw = encoded(record)
    source, output = tmp_path / "download", tmp_path / "verification"
    hosted_driver_tree(source, {**payloads, "receipt.json": raw})
    hosted_driver_prefix(output, "verify", context)
    for name, value in hosted_driver_environment("verify").items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("EXPECTED_RECEIPT_SHA256", digest(raw))
    calls = []
    def forbidden(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("an incomplete prefix must not launch environment work")
    for name in ("environment", "_materials", "_build_image", "_container", "acquire", "_command"):
        monkeypatch.setattr(driver, name, forbidden)
    with pytest.raises(ValueError, match="hosted_capture_not_published"):
        driver.verify(output, source, digest(raw), context)
    assert calls == [] and not (output / "verified-binding.json").exists()
    result = json.loads((output / "receipt-verification.json").read_bytes())
    assert result["all_preserved_bytes_verified"] is True and result["observation_complete"] is False
    assert (output / "private-input/receipt.json").read_bytes() == raw
    assert all((output / "private-input" / name).read_bytes() == value for name, value in payloads.items())


@pytest.mark.parametrize("fault", ["extra", "missing", "changed", "symlink"])
def test_hosted_driver_verification_rejects_any_download_roster_or_byte_drift(tmp_path, monkeypatch, fault):
    driver = hosted_driver()
    context, payloads, record = hosted_driver_receipt(monkeypatch)
    raw = encoded(record)
    source, output = tmp_path / "download", tmp_path / "verification"
    hosted_driver_tree(source, {**payloads, "receipt.json": raw})
    hosted_driver_prefix(output, "verify", context)
    for name, value in hosted_driver_environment("verify").items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("EXPECTED_RECEIPT_SHA256", digest(raw))
    if fault == "extra":
        (source / "not-in-receipt.bin").write_bytes(b"x")
    else:
        path = source / "observation/request.json"
        if fault == "changed":
            path.write_bytes(b"changed")
        else:
            path.unlink()
            if fault == "symlink":
                (tmp_path / "replacement").write_bytes(payloads["observation/request.json"])
                path.symlink_to(tmp_path / "replacement")
    def forbidden(*_args, **_kwargs):
        raise AssertionError("unverified download reached environment work")
    for name in ("environment", "_materials", "_build_image", "_container", "_command"):
        monkeypatch.setattr(driver, name, forbidden)
    with pytest.raises(ValueError):
        driver.verify(output, source, digest(raw), context)
    assert not (output / "receipt-verification.json").exists()
    assert not (output / "verified-binding.json").exists()


def hosted_driver_attestation_fixture(tmp_path, monkeypatch):
    driver = hosted_driver()
    context = hosted_driver_context()
    root = tmp_path / "verification"
    hosted_driver_prefix(root, "verify", context)
    for name, value in hosted_driver_environment("verify").items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GH_TOKEN", "SYNTHETIC_SECRET_DO_NOT_PRESERVE")
    monkeypatch.setenv("EXEC_STOP_ATTESTATION_ID", "1234")
    monkeypatch.setenv("EXEC_STOP_ATTESTATION_URL", "https://github.com/HKati/pulse-release-gates-0.1/attestations/1234")
    value = {
        "record_type": "required_gate_idempotence_exec_stop_hosted_verified_binding_v0",
        "profile": driver.PROFILE, "status": "accepted", "context": context,
        "artifact_id": 123456789, "observation_complete": True,
        "canonical_reports_byte_identical": True, "verification_acquisition_repeated": False,
        **driver.BOUNDARY,
    }
    raw = encoded(value)
    driver.io.write_new(root / "verified-binding.json", raw)
    bundle = tmp_path / "action-bundle.json"
    bundle.write_bytes(b'{"authored_bundle":"never sent to GH"}\n')
    return driver, context, root, bundle, raw


def test_hosted_driver_attestation_verifier_pins_original_bundle_source_workflow_and_oidc(tmp_path, monkeypatch):
    driver, context, root, bundle, raw = hosted_driver_attestation_fixture(tmp_path, monkeypatch)
    calls = []
    def command(*args, **kwargs):
        calls.append((args, kwargs))
        return {"returncode": 0, "failure": None}
    monkeypatch.setattr(driver, "_command", command)
    assert driver.attest_verify(root, bundle, context) == 0
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:2] == (root, "attestation-verify")
    assert args[2] == [
        "gh", "attestation", "verify", str(root / "verified-binding.json"),
        "--bundle", str(root / "attestation.bundle.json"),
        "--repo", "HKati/pulse-release-gates-0.1",
        "--signer-workflow", "HKati/pulse-release-gates-0.1/.github/workflows/required_gate_idempotence_exec_stop_v0.yml",
        "--signer-digest", "a" * 40, "--source-digest", "a" * 40,
        "--source-ref", "refs/heads/main", "--predicate-type", "https://slsa.dev/provenance/v1",
        "--cert-oidc-issuer", "https://token.actions.githubusercontent.com",
        "--deny-self-hosted-runners", "--format", "json"]
    assert args[3] <= 120 and kwargs["require"] is False
    assert (root / "attestation.bundle.json").read_bytes() == bundle.read_bytes()
    result = json.loads((root / "attestation-verification.json").read_bytes())
    assert result["subject"] == bound(raw) and result["bundle"] == bound(bundle.read_bytes())
    assert result["github_signature_verification_succeeded"] is True
    assert all(b"SYNTHETIC_SECRET_DO_NOT_PRESERVE" not in path.read_bytes()
               for path in root.rglob("*") if path.is_file())


@pytest.mark.parametrize("fault", ["exit", "timeout", "subject", "bundle"])
def test_hosted_driver_attestation_cannot_accept_failed_or_changed_verification(tmp_path, monkeypatch, fault):
    driver, context, root, bundle, _raw = hosted_driver_attestation_fixture(tmp_path, monkeypatch)
    def command(*_args, **_kwargs):
        if fault == "subject":
            (root / "verified-binding.json").write_bytes(b"changed subject")
        if fault == "bundle":
            (root / "attestation.bundle.json").write_bytes(b"changed preserved bundle")
        return {"returncode": 1 if fault == "exit" else 0,
                "failure": "hosted_process_timeout" if fault == "timeout" else None}
    monkeypatch.setattr(driver, "_command", command)
    with pytest.raises(ValueError):
        driver.attest_verify(root, bundle, context)
    assert not (root / "attestation-verification.json").exists()


@pytest.mark.parametrize("fault", ["read_error", "deadline", "oversized"])
def test_hosted_driver_download_retains_bounded_received_prefix_on_failure(tmp_path, monkeypatch, fault):
    driver = hosted_driver()
    item = {"url": "https://deb.debian.org/debian/authored.deb", **bound(b"expected")}
    prefix = b"part" if fault != "oversized" else b"x" * (item["size_bytes"] + 1)
    class Response:
        status = 200
        calls = 0
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def geturl(self):
            return item["url"]
        def read(self, limit):
            self.calls += 1
            if self.calls == 1:
                assert len(prefix) <= limit
                return prefix
            raise OSError("authored interrupted response")
    response = Response()
    opener = SimpleNamespace(open=lambda *_args, **_kwargs: response)
    monkeypatch.setattr(driver.urllib.request, "build_opener", lambda *_args: opener)
    if fault == "deadline":
        ticks = iter((0, 1, 121))
        monkeypatch.setattr(driver.time, "monotonic", lambda: next(ticks))
    destination = tmp_path / "partial.deb"
    with pytest.raises((ValueError, OSError)):
        driver.download(item, destination)
    assert destination.read_bytes() == prefix
    assert len(destination.read_bytes()) <= item["size_bytes"] + 1


@pytest.mark.parametrize("fault", ["privileged", "writable", "network", "cap_added", "seccomp"])
def test_hosted_driver_rejects_changed_container_policy_before_start_and_cleans_up(tmp_path, monkeypatch, fault):
    driver = hosted_driver()
    context = hosted_driver_context()
    root = tmp_path / "attempt"
    root.mkdir(mode=0o700)
    (root / "environment").mkdir(mode=0o700)
    container_id, image_id = "d" * 64, "sha256:" + "c" * 64
    host_config = {"Privileged": False, "ReadonlyRootfs": True, "NetworkMode": "none", "CapDrop": ["ALL"],
                   "CapAdd": None, "SecurityOpt": ["no-new-privileges"], "PidsLimit": 64,
                   "Memory": 1024 * 1024 * 1024, "NanoCpus": 1000000000}
    changes = {"privileged": ("Privileged", True), "writable": ("ReadonlyRootfs", False),
               "network": ("NetworkMode", "host"), "cap_added": ("CapAdd", ["SYS_PTRACE"]),
               "seccomp": ("SecurityOpt", ["no-new-privileges", "seccomp=unconfined"])}
    key, value = changes[fault]
    host_config[key] = value
    labels = []
    def command(path, label, argv, *_args, **_kwargs):
        labels.append(label)
        if label == "container-create":
            (path / "host-commands").mkdir(mode=0o700)
            driver.io.write_new(path / "host-commands/container-create.stdout.bin", (container_id + "\n").encode())
        return {"returncode": 0, "failure": None}
    def inspection(*_args, **_kwargs):
        return [{"Id": container_id, "Image": image_id, "HostConfig": host_config,
                 "Config": {"User": "1001:1002"}, "State": {"Running": False, "ExitCode": 0}}]
    monkeypatch.setattr(driver.os, "getuid", lambda: 1001)
    monkeypatch.setattr(driver.os, "getgid", lambda: 1002)
    monkeypatch.setattr(driver, "_command", command)
    monkeypatch.setattr(driver, "_command_json", inspection)
    with pytest.raises(ValueError, match="hosted_container_policy"):
        driver._container(root, {}, image_id, context, tmp_path / "originals", "acquire")
    assert labels == ["container-create", "container-remove"]
    cleanup = json.loads((root / "environment/container-cleanup.json").read_bytes())
    assert cleanup["container_id"] == container_id and cleanup["owned_container_removed"] is True


def hosted_driver_build_fixture(tmp_path, monkeypatch, phase="acquire", *, archive_fault=None, inspect_fault=None):
    driver = hosted_driver()
    selected = driver.environment()
    root, materials = tmp_path / "phase", tmp_path / "materials"
    root.mkdir(mode=0o700)
    materials.mkdir(mode=0o700)
    base_id = "sha256:" + selected["base_image"]["config_sha256"]
    local_tag = "localhost/pulse-exec-stop-base:" + selected["base_image"]["config_sha256"]
    image_id = "sha256:" + "e" * 64
    saved = b"authored docker-save archive; never passed to Docker\n"
    previous = None
    if phase == "verify":
        previous = tmp_path / "previous"
        value = {"returncode": 0, "failure": None, "stdout": bound(saved),
                 "argv": ["docker", "image", "save", local_tag]}
        if archive_fault == "digest":
            value["stdout"] = bound(saved + b"changed")
        elif archive_fault == "exit":
            value["returncode"] = 1
        elif archive_fault == "failure":
            value["failure"] = "hosted_process_stdout_limit"
        elif archive_fault == "argv":
            value["argv"][-1] = "unreviewed:latest"
        hosted_driver_tree(previous, {"host-commands/base-save.stdout.bin": saved,
                                      "host-commands/base-save.result.json": encoded(value)})
    calls = []
    def command(path, label, argv, *args, **kwargs):
        calls.append((label, list(argv), args, kwargs))
        if label == "base-save":
            logs = path / "host-commands"
            logs.mkdir(mode=0o700, exist_ok=True)
            driver.io.write_new(logs / "base-save.stdout.bin", saved)
        elif label == "docker-build":
            iidfile = Path(argv[argv.index("--iidfile") + 1])
            driver.io.write_new(iidfile, (image_id + "\n").encode())
        return {"returncode": 0, "failure": None}
    def inspection(path, label, argv, *_args, **_kwargs):
        calls.append((label, list(argv), (), {}))
        value = {"Id": image_id if label == "image-inspect" else base_id,
                 "Architecture": "amd64", "Os": "linux"}
        if inspect_fault == label:
            value["Id"] = "sha256:" + "f" * 64
        return [value]
    def forbidden(*_args, **_kwargs):
        raise AssertionError("image reconstruction attempted an unselected download")
    monkeypatch.setattr(driver, "_command", command)
    monkeypatch.setattr(driver, "_command_json", inspection)
    monkeypatch.setattr(driver, "download", forbidden)
    return driver, root, materials, previous, selected, calls, saved, local_tag, image_id


@pytest.mark.parametrize("phase", ["acquire", "verify"])
def test_hosted_driver_build_uses_preserved_base_offline_for_verification(tmp_path, monkeypatch, phase):
    driver, root, materials, previous, selected, calls, saved, local_tag, image_id = hosted_driver_build_fixture(
        tmp_path, monkeypatch, phase)
    assert driver._build_image(root, selected, materials, previous) == image_id
    by_label = {label: (argv, args, kwargs) for label, argv, args, kwargs in calls}
    assert len(by_label) == len(calls)
    build = by_label["docker-build"][0]
    assert build[:2] == ["docker", "build"]
    assert build[build.index("--network") + 1] == "none"
    assert build[build.index("--platform") + 1] == "linux/amd64"
    assert build[build.index("--build-arg") + 1] == "PULSE_EXEC_STOP_BASE=" + local_tag
    assert "--pull=false" in build and "--no-cache" in build and build[-1] == str(materials)
    if phase == "acquire":
        assert by_label["docker-pull"][0] == [
            "docker", "pull", "--platform", "linux/amd64", selected["base_image"]["reference"]]
        assert by_label["base-save"][0] == ["docker", "image", "save", local_tag]
        assert by_label["base-save"][2]["stdout_cap"] == driver.FILE_LIMIT
        assert (root / "host-commands/base-save.stdout.bin").read_bytes() == saved
        assert "base-load" not in by_label
    else:
        assert not {"docker-pull", "base-save", "base-tag"} & set(by_label)
        assert by_label["base-load"][0] == [
            "docker", "image", "load", "--input", str(previous / "host-commands/base-save.stdout.bin")]
        assert by_label["base-inspect"][0] == ["docker", "image", "inspect", local_tag]
        assert all("pull" not in argv and "save" not in argv for _label, argv, _args, _kwargs in calls)
    record = json.loads((root / "environment/selection.json").read_bytes())
    assert record["base_archive"] == bound(saved)
    assert record["base_loaded_from_preserved_bytes"] is (phase == "verify")
    assert record["base_local_build_tag"] == local_tag and record["constructed_image_id"] == image_id
    assert record["image_reproducibility_claimed"] is False and record["authority_effect"] == "none"


@pytest.mark.parametrize("fault", ["digest", "exit", "failure", "argv"])
def test_hosted_driver_rejects_changed_or_incomplete_saved_base_before_loading(tmp_path, monkeypatch, fault):
    driver, root, materials, previous, selected, calls, *_ = hosted_driver_build_fixture(
        tmp_path, monkeypatch, "verify", archive_fault=fault)
    with pytest.raises(ValueError, match="hosted_preserved_base_archive"):
        driver._build_image(root, selected, materials, previous)
    labels = [item[0] for item in calls]
    assert labels == ["docker-version", "docker-info"]
    assert not (root / "environment/selection.json").exists()


@pytest.mark.parametrize("phase", ["acquire", "verify"])
@pytest.mark.parametrize("fault", ["base-inspect", "base-tag-inspect", "base-after"])
def test_hosted_driver_rejects_pulled_loaded_or_rebound_base_config_identity(tmp_path, monkeypatch, phase, fault):
    driver, root, materials, previous, selected, calls, *_ = hosted_driver_build_fixture(
        tmp_path, monkeypatch, phase, inspect_fault=fault)
    with pytest.raises(ValueError, match="hosted_base_"):
        driver._build_image(root, selected, materials, previous)
    labels = [item[0] for item in calls]
    if fault != "base-after":
        assert "docker-build" not in labels
    assert not (root / "environment/selection.json").exists()


def test_hosted_driver_expired_phase_budget_blocks_work_but_preserves_cleanup_allowance(tmp_path, monkeypatch):
    driver = hosted_driver()
    root = tmp_path / "attempt"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(driver, "STAGE_DEADLINE", 99)
    monkeypatch.setattr(driver.time, "monotonic", lambda: 100)
    calls = []
    def run(*args, **kwargs):
        calls.append((args, kwargs))
        return {"returncode": 0, "failure": None}
    monkeypatch.setattr(driver.io, "run_command", run)
    with pytest.raises(ValueError):
        driver._command(root, "docker-build", ["docker", "build", "."], 600)
    assert calls == []
    driver._command(root, "container-remove", ["docker", "rm", "--force", "d" * 64],
                    30, require=False, cleanup=True)
    assert len(calls) == 1 and calls[0][1]["timeout_seconds"] == 30


def hosted_environment_builder_fixture(tmp_path, monkeypatch):
    """Exercise the installer with authored bytes; no package process executes."""
    builder = module(
        "hosted_exec_stop_environment_builder_regression_v0",
        "tools/required_gate_idempotence_exec_stop_hosted_v0/build_environment.py",
    )
    config = ROOT / "tools/required_gate_idempotence_exec_stop_hosted_v0"
    selected = json.loads((config / "environment.json").read_bytes())
    inputs = tmp_path / "build-inputs"
    inputs.mkdir()
    for directory, entries in (("debs", selected["debian"]["packages"]),
                               ("wheels", selected["python"]["packages"])):
        (inputs / directory).mkdir()
        for item in entries:
            raw = ("authored non-executable " + item["filename"] + "\n").encode()
            (inputs / directory / item["filename"]).write_bytes(raw)
            item.update(bound(raw))
    runtime = tmp_path / "authored-runtime"
    runtime.mkdir()
    runtime_paths = {}
    for ordinal, item in enumerate(selected["expected_files"]):
        path = runtime / str(ordinal)
        raw = ("authored non-executable runtime file " + item["path"] + "\n").encode()
        path.write_bytes(raw)
        item.update(bound(raw))
        runtime_paths[item["path"]] = path
    (inputs / "environment.json").write_bytes(encoded(selected))
    (inputs / "requirements.lock").write_text("\n".join(
        item["name"] + "==" + item["version"] + " --hash=sha256:" + item["sha256"]
        for item in selected["python"]["packages"]
    ) + "\n")
    before = {item["name"]: item["base_version"] for item in selected["debian"]["closure"]
              if item["base_version"] is not None}
    state = SimpleNamespace(
        builder=builder, inputs=inputs, selected=selected, calls=[], runtime_paths=runtime_paths,
        after={item["name"]: item["version"] for item in selected["debian"]["closure"]},
        python_versions={builder.normalized_name(item["name"]): item["version"]
                         for item in selected["python"]["packages"]},
        status_reads=0, dpkg_failure=False, change_runtime_after_install=False,
    )

    def installed_debian():
        state.status_reads += 1
        return dict(before if state.status_reads == 1 else state.after)

    def run(argv, **kwargs):
        state.calls.append((list(argv), kwargs))
        if argv[0] == "/usr/bin/dpkg":
            if state.dpkg_failure:
                raise subprocess.CalledProcessError(1, argv)
        elif argv[:5] == [builder.PYTHON, "-I", "-m", "pip", "install"]:
            pass
        elif argv == [builder.PYTHON, "-I", "-m", "pip", "check"]:
            if state.change_runtime_after_install:
                path = runtime_paths["/usr/bin/gpg"]
                raw = path.read_bytes()
                path.write_bytes(b"X" + raw[1:])
        else:
            raise AssertionError("offline installer attempted an unselected command: " + repr(argv))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(builder, "sys", SimpleNamespace(executable=builder.PYTHON, platform="linux"))
    monkeypatch.setattr(builder, "platform", SimpleNamespace(
        python_version=lambda: builder.PYTHON_VERSION, machine=lambda: "x86_64"))
    monkeypatch.setattr(builder, "Path", lambda value: runtime_paths.get(str(value), Path(value)))
    monkeypatch.setattr(builder, "installed_debian", installed_debian)
    monkeypatch.setattr(builder, "importlib", SimpleNamespace(metadata=SimpleNamespace(
        version=lambda name: state.python_versions[builder.normalized_name(name)])))
    monkeypatch.setattr(builder, "subprocess", SimpleNamespace(run=run))
    return state


def test_hosted_environment_builder_installs_only_verified_local_overlay(tmp_path, monkeypatch):
    state = hosted_environment_builder_fixture(tmp_path, monkeypatch)
    result = state.builder.install(state.inputs)
    assert len(state.calls) == 3 and state.status_reads == 2
    argv, options = state.calls[0]
    selected_paths = [str(state.inputs / "debs" / item["filename"])
                      for item in state.selected["debian"]["packages"]]
    # No resolver, dependency force, recursive input, or trigger suppression.
    assert argv == ["/usr/bin/dpkg", "--install", *selected_paths]
    assert len(selected_paths) == 7 and all(Path(path).is_absolute() for path in selected_paths)
    assert options["check"] is True and options["timeout"] == 300
    assert options["env"]["DEBIAN_FRONTEND"] == "noninteractive"
    pip_install = state.calls[1][0]
    assert {"--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:"} <= set(pip_install)
    assert "--find-links=" + str(state.inputs / "wheels") in pip_install
    assert state.calls[2][0] == [state.builder.PYTHON, "-I", "-m", "pip", "check"]
    record_path = state.inputs / "build-environment-record.json"
    assert json.loads(record_path.read_bytes()) == result
    assert stat.S_IMODE(record_path.stat().st_mode) == 0o644
    assert result["environment_selection"] == bound((state.inputs / "environment.json").read_bytes())
    assert result["installed_debian_delta"] == [
        {"name": item["name"], "version": item["version"]} for item in state.selected["debian"]["packages"]]
    assert len(result["checked_files"]) == len(state.selected["expected_files"])
    assert result["authority_effect"] == "none"
    assert result["host_environment_qualified"] is False and result["native_acquisition_performed"] is False
    assert not (state.inputs / "debs").exists() and not (state.inputs / "wheels").exists()


def test_hosted_environment_builder_dpkg_failure_stops_before_pip_or_record(tmp_path, monkeypatch):
    state = hosted_environment_builder_fixture(tmp_path, monkeypatch)
    state.dpkg_failure = True
    with pytest.raises(subprocess.CalledProcessError):
        state.builder.install(state.inputs)
    assert len(state.calls) == 1 and state.calls[0][0][:2] == ["/usr/bin/dpkg", "--install"]
    assert state.status_reads == 1
    assert not (state.inputs / "build-environment-record.json").exists()
    assert (state.inputs / "debs").is_dir() and (state.inputs / "wheels").is_dir()


@pytest.mark.parametrize("directory", ["debs", "wheels"])
@pytest.mark.parametrize("fault", ["changed", "missing", "extra"])
def test_hosted_environment_builder_rejects_payload_fault_before_any_process(tmp_path, monkeypatch, directory, fault):
    state = hosted_environment_builder_fixture(tmp_path, monkeypatch)
    payloads = state.inputs / directory
    path = sorted(payloads.iterdir())[0]
    if fault == "changed":
        raw = path.read_bytes()
        path.write_bytes(b"X" + raw[1:])
    elif fault == "missing":
        path.unlink()
    else:
        (payloads / "unselected-payload").write_bytes(b"authored extra input\n")
    with pytest.raises(ValueError, match="build_payload_binding|build_payload_members"):
        state.builder.install(state.inputs)
    assert state.calls == []
    assert not (state.inputs / "build-environment-record.json").exists()


@pytest.mark.parametrize("fault", ["debian-version", "python-version", "runtime-hash"])
def test_hosted_environment_builder_rejects_post_install_mismatch_without_record(tmp_path, monkeypatch, fault):
    state = hosted_environment_builder_fixture(tmp_path, monkeypatch)
    if fault == "debian-version":
        state.after["gpg"] = "0"
        reason = "build_installed_package_version"
    elif fault == "python-version":
        state.python_versions["jsonschema"] = "0"
        reason = "build_installed_python_version"
    else:
        state.change_runtime_after_install = True
        reason = "build_runtime_file_binding"
    with pytest.raises(ValueError, match=reason):
        state.builder.install(state.inputs)
    assert len(state.calls) == 3 and state.status_reads == 2
    assert not (state.inputs / "build-environment-record.json").exists()
    assert (state.inputs / "debs").is_dir() and (state.inputs / "wheels").is_dir()


# Entry-stop proposal checks consume historical bytes only. No original child,
# dynamic loader, entry collector or new hosted acquisition executes here.
ENTRY_STOP_PLAN_REL = "docs/compute/required_gate_idempotence_entry_stop_plan_v0/plan_v0.json"


@pytest.fixture(scope="module")
def entry_stop_plan_case():
    checker = module("check_required_gate_idempotence_entry_stop_plan_v0",
                     "tools/check_required_gate_idempotence_entry_stop_plan_v0.py")
    raw = (ROOT / ENTRY_STOP_PLAN_REL).read_bytes()
    return SimpleNamespace(checker=checker, raw=raw, plan=json.loads(raw),
        baseline=(ROOT / checker.BASELINE_REL).read_bytes(),
        originals=(ROOT / checker.ORIGINALS_REL).read_bytes())


def entry_stop_plan_check(case, raw=None, **overrides):
    raw = case.raw if raw is None else raw
    arguments = dict(plan_bytes=raw, expected_plan_sha256=digest(raw),
                     baseline_archive_bytes=case.baseline,
                     originals_archive_bytes=case.originals)
    arguments.update(overrides)
    return case.checker.verify_plan(**arguments)


def test_entry_stop_plan_reconstructs_actual_cp0_and_original_native_extents(entry_stop_plan_case):
    import zipfile
    case = entry_stop_plan_case
    report = entry_stop_plan_check(case)
    assert report == entry_stop_plan_check(case)
    assert report["status"] == "accepted" and report["plan_consistency_verified"] is True
    assert report["historical_cp0"] == {
        "run_id": 44375052171, "run_attempt": 1,
        "source_commit": "84b78ff1758ed3db73fbb1db1b37451ca6620373",
        "attempt_id": "d54f64c544090b13d2c2633b32204e02",
        "lower_level_reconstruction_accepted": True,
        "report": {"sha256": "8a2769ae4e7858f73b7cca9285724aabaee152f4dbf6e5bfb6c603cea538b34b", "size_bytes": 2200},
        "source_file_count": 62,
    }
    assert {row["path"] for row in case.plan["native_objects"]} == {
        "native/bwrap", "native/ld-linux-x86-64.so.2", "native/libc.so.6",
        "native/libcap.so.2", "native/libpcre2-8.so.0", "native/libselinux.so.1",
    }
    load_count, rx_bytes, rx_count = 0, 0, 0
    with zipfile.ZipFile(io.BytesIO(case.originals)) as archive:
        for row in case.plan["native_objects"]:
            raw = archive.read(row["path"])
            assert bound(raw) == {name: row[name] for name in ("sha256", "size_bytes")}
            header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
            for index in range(header[10]):
                kind, flags, _offset, _vaddr, _paddr, filesz, _memsz, _align = struct.unpack_from(
                    "<IIQQQQQQ", raw, header[5] + index * header[9])
                load_count += kind == 1
                if kind == 1 and flags == 5:
                    rx_bytes += filesz
                    rx_count += 1
            for sample in row["rx_samples"]:
                segment = next(item for item in row["elf"]["segments"] if item["index"] == sample["segment_index"])
                selected = raw[segment["offset"]:segment["offset"] + segment["filesz"]]
                assert bound(selected) == {name: sample[name] for name in ("sha256", "size_bytes")}
    assert report["totals"] == {
        "native_objects": 6, "pt_load_occurrences": load_count,
        "rx_sample_occurrences": 2 * rx_count, "rx_sample_bytes": 2 * rx_bytes,
        "distinct_rx_bytes": rx_bytes, "static_relationships": 12,
        "dt_needed_relationships": 9, "pt_interp_relationships": 3,
    }
    assert (load_count, rx_count, rx_bytes) == (24, 6, 2300774)
    assert report["original_native_bytes_verified"] is True
    for flag in ("entry_checkpoint_observed", "additional_native_objects_observed",
                 "native_acquisition_performed", "collector_implemented", "execution_authorized",
                 "selected_runtime_executed", "loader_resolution_verified", "b2_complete",
                 "distribution_signature_freshly_verified", "attestation_signature_freshly_verified",
                 "full_hosted_replay_performed", "production_gate_eligible"):
        assert report[flag] is False, flag
    assert report["metric_pass"] is None and report["authority_effect"] == "none"


@pytest.mark.parametrize("fault", [
    "object_missing", "object_duplicate", "object_substituted", "object_digest",
    "segment_missing", "segment_duplicate", "segment_offset", "segment_flags",
    "sample_missing", "sample_duplicate", "sample_other_object", "sample_digest",
])
def test_entry_stop_plan_rehashed_native_obligations_cannot_change(entry_stop_plan_case, fault):
    case = entry_stop_plan_case
    plan = copy.deepcopy(case.plan)
    objects = plan["native_objects"]
    segments, samples = objects[0]["elf"]["segments"], objects[0]["rx_samples"]
    if fault == "object_missing": objects.pop()
    elif fault == "object_duplicate": objects[-1] = copy.deepcopy(objects[0])
    elif fault == "object_substituted": objects[0]["path"] = "native/other-launcher"
    elif fault == "object_digest": objects[0]["sha256"] = "0" * 64
    elif fault == "segment_missing": segments.pop()
    elif fault == "segment_duplicate": segments[-1] = copy.deepcopy(segments[0])
    elif fault == "segment_offset": segments[1]["offset"] += 4096
    elif fault == "segment_flags": segments[1]["flags"] = 7
    elif fault == "sample_missing": samples.pop()
    elif fault == "sample_duplicate": samples[1] = copy.deepcopy(samples[0])
    elif fault == "sample_other_object": samples[0] = copy.deepcopy(objects[1]["rx_samples"][0])
    else: samples[0]["sha256"] = "0" * 64
    raw = encoded(plan)
    assert json.loads(raw) != case.plan
    with pytest.raises(case.checker.PlanError):
        entry_stop_plan_check(case, raw)


@pytest.mark.parametrize("fault", [
    "missing", "duplicate", "provider_substituted", "consumer_substituted",
    "needed_as_interpreter", "metadata_interpreter_executed", "mapping_promoted_to_resolution",
])
def test_entry_stop_plan_rehashed_relationships_keep_occurrence_meanings(entry_stop_plan_case, fault):
    case = entry_stop_plan_case
    plan = copy.deepcopy(case.plan)
    rows = plan["static_relationships"]
    if fault == "missing": rows.pop()
    elif fault == "duplicate": rows[-1] = copy.deepcopy(rows[0])
    elif fault == "provider_substituted": rows[1]["provider"] = "native/libcap.so.2"
    elif fault == "consumer_substituted": rows[1]["consumer"] = "native/libselinux.so.1"
    elif fault == "needed_as_interpreter": rows[1]["kind"] = "interpreter"
    elif fault == "metadata_interpreter_executed":
        row = next(item for item in rows if item["consumer"] == "native/libc.so.6" and item["kind"] == "interpreter")
        row["entry_obligation"] = "fresh_kernel_interpreter_continuity"
    else:
        rows[1]["provider_mapping_observed"] = True
        rows[1]["consumer_resolution_observed"] = True
    with pytest.raises(case.checker.PlanError):
        entry_stop_plan_check(case, encoded(plan))


@pytest.mark.parametrize("section,field,value", [
    ("historical_baseline", "historical_child_resumable", True),
    ("historical_baseline", "run_attempt", 2),
    ("future_attempt", "historical_pid_or_aslr_address_reusable", True),
    ("future_attempt", "completed_historical_cp0_report_reusable_as_live_prefix", True),
    ("future_attempt", "fresh_cp0_required", False),
    ("future_attempt", "authorization_supplied_by_plan", True),
    ("execution_policy", "post_entry_resumes", 1),
    ("execution_policy", "cp0_to_entry_resumes", 2),
    ("execution_policy", "absence_of_pre_entry_side_effects_claimed", True),
    ("checkpoint", "debug_register_writes", ["DR0", "DR1", "DR6", "DR7"]),
    ("checkpoint", "software_breakpoint_or_target_code_patch", True),
    ("checkpoint", "general_register_or_instruction_pointer_write", True),
    ("task_creation_guard", "ptrace_events_alone_establish_no_task_creation", True),
    ("evidence_policy", "saved_success_booleans_replace_raw_reconstruction", True),
    ("boundary", "entry_checkpoint_observed", True),
    ("boundary", "loader_resolution_verified", True),
    ("boundary", "authority_effect", "release"),
    ("boundary", "metric_pass", True),
])
def test_entry_stop_plan_rehash_does_not_authorize_scope_changes(entry_stop_plan_case, section, field, value):
    case = entry_stop_plan_case
    plan = copy.deepcopy(case.plan)
    plan[section][field] = value
    with pytest.raises(case.checker.PlanError):
        entry_stop_plan_check(case, encoded(plan))


@pytest.mark.parametrize("field,value", [
    ("wall_seconds", 60), ("cleanup_seconds", 20), ("owned_tracees", 2),
    ("wait_records", 100), ("total_capture_bytes", 83886080),
])
def test_entry_stop_plan_rehashed_limits_cannot_expand(entry_stop_plan_case, field, value):
    case = entry_stop_plan_case
    plan = copy.deepcopy(case.plan)
    plan["limits"][field] = value
    with pytest.raises(case.checker.PlanError):
        entry_stop_plan_check(case, encoded(plan))


@pytest.mark.parametrize("fault", [
    "duplicate_top", "duplicate_nested", "float", "boolean", "nonfinite", "invalid_utf8", "array", "oversized",
])
def test_entry_stop_plan_strict_json_and_numeric_types(entry_stop_plan_case, fault):
    case = entry_stop_plan_case
    raw = encoded(case.plan)
    if fault == "duplicate_top": raw = b'{"profile":"discarded",' + raw[1:]
    elif fault == "duplicate_nested": raw = raw.replace(b'"wall_seconds":15', b'"wall_seconds":15,"wall_seconds":15', 1)
    elif fault == "float": raw = raw.replace(b'"wall_seconds":15', b'"wall_seconds":15.0', 1)
    elif fault == "boolean": raw = raw.replace(b'"owned_tracees":1', b'"owned_tracees":true', 1)
    elif fault == "nonfinite": raw = raw.replace(b'"wall_seconds":15', b'"wall_seconds":NaN', 1)
    elif fault == "invalid_utf8": raw += b"\xff"
    elif fault == "array": raw = b"[]\n"
    else: raw = b" " * (case.checker.CONTROL_BYTES + 1)
    assert raw != encoded(case.plan)
    with pytest.raises(case.checker.PlanError):
        entry_stop_plan_check(case, raw)


@pytest.mark.parametrize("expected", ["0" * 64, "a" * 63, "A" * 64, False])
def test_entry_stop_plan_requires_the_external_plan_digest(entry_stop_plan_case, expected):
    case = entry_stop_plan_case
    with pytest.raises(case.checker.PlanError, match="entry_stop_plan_(external_digest|digest_mismatch)"):
        entry_stop_plan_check(case, expected_plan_sha256=expected)


@pytest.mark.parametrize("which", ["baseline", "originals"])
@pytest.mark.parametrize("fault", ["changed", "truncated", "wrong_type"])
def test_entry_stop_plan_both_selected_archives_require_exact_bytes(entry_stop_plan_case, which, fault):
    case = entry_stop_plan_case
    raw = getattr(case, which)
    if fault == "changed": raw = raw[:-1] + bytes([raw[-1] ^ 1])
    elif fault == "truncated": raw = raw[:-1]
    else: raw = bytearray(raw)
    parameter = "baseline_archive_bytes" if which == "baseline" else "originals_archive_bytes"
    with pytest.raises(case.checker.PlanError, match="entry_stop_plan_archive_binding"):
        entry_stop_plan_check(case, **{parameter: raw})


@pytest.mark.parametrize("fault", ["rejected", "incomplete"])
def test_entry_stop_plan_saved_cp0_reports_cannot_override_fresh_reconstruction(entry_stop_plan_case, monkeypatch, fault):
    import zipfile
    case = entry_stop_plan_case
    with zipfile.ZipFile(io.BytesIO(case.baseline)) as archive:
        saved = json.loads(archive.read("verification/verification/capture-check-1.json"))
    calls = []

    def reject(**inputs):
        calls.append(inputs)
        if fault == "rejected":
            raise case.checker.cp0.ExecStopError("authored_raw_capture_rejection")
        return dict(saved, observation_complete=False)

    monkeypatch.setattr(case.checker.cp0, "verify_capture", reject)
    with pytest.raises(case.checker.PlanError, match="entry_stop_plan_historical_cp0_(rejected|incomplete)"):
        entry_stop_plan_check(case)
    assert len(calls) == 1
    assert digest(calls[0]["capture_bytes"]) == "0e7bc25175f9c95393ab7bd9a9895e72be5f608b17c2012c4249775e3c5dce13"
    assert len(calls[0]["files"]) == 32 and saved["observation_complete"] is True


@pytest.mark.parametrize("which", ["historical", "checker", "schema"])
def test_entry_stop_plan_source_changes_during_verification_are_rejected(entry_stop_plan_case, monkeypatch, which):
    case = entry_stop_plan_case
    target = {
        "historical": "docs/compute/required_gate_idempotence_protocol_v0/inputs_v0.json",
        "checker": "tools/check_required_gate_idempotence_entry_stop_plan_v0.py",
        "schema": case.checker.SCHEMA_REL,
    }[which]
    actual_source = case.checker._source
    reads = []

    def changed_source(path):
        raw = actual_source(path)
        if path == target:
            reads.append(path)
            if which == "historical" or len(reads) > 1:
                return raw + b"\n"
        return raw

    monkeypatch.setattr(case.checker, "_source", changed_source)
    with pytest.raises(case.checker.PlanError, match="entry_stop_plan_(historical_source_changed|checker_source_changed)"):
        entry_stop_plan_check(case)
    assert len(reads) == (1 if which == "historical" else 2)


def test_entry_stop_plan_shape_acceptance_does_not_replace_original_byte_semantics(entry_stop_plan_case):
    import jsonschema
    case = entry_stop_plan_case
    plan = copy.deepcopy(case.plan)
    plan["native_objects"][0]["sha256"] = "0" * 64
    schema = json.loads((ROOT / case.checker.SCHEMA_REL).read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(plan)
    with pytest.raises(case.checker.PlanError, match="entry_stop_plan_native_obligations"):
        entry_stop_plan_check(case, encoded(plan))


def test_entry_stop_plan_verification_never_imports_collectors_or_starts_execution(entry_stop_plan_case, monkeypatch):
    import builtins
    import ctypes
    case = entry_stop_plan_case
    actual_import = builtins.__import__
    collectors = {
        "required_gate_idempotence_exec_stop_v0", "prepare_required_gate_idempotence_exec_stop_v0",
        "required_gate_idempotence_exec_stop_hosted_v0", "required_gate_idempotence_containment_v0",
    }

    def guarded_import(name, *args, **kwargs):
        assert name not in collectors, "proposal checker imported a live acquisition adapter"
        return actual_import(name, *args, **kwargs)

    def forbidden_execution(*args, **kwargs):
        raise AssertionError("proposal verification must only reconstruct preserved data")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(subprocess, "Popen", forbidden_execution)
    monkeypatch.setattr(os, "fork", forbidden_execution)
    monkeypatch.setattr(os, "execve", forbidden_execution)
    monkeypatch.setattr(os, "system", forbidden_execution)
    monkeypatch.setattr(ctypes, "CDLL", forbidden_execution)
    monkeypatch.setattr(case.checker.transport, "run_command", forbidden_execution)
    independent = module("entry_stop_plan_no_execution", "tools/check_required_gate_idempotence_entry_stop_plan_v0.py")
    report = independent.verify_plan(plan_bytes=case.raw, expected_plan_sha256=digest(case.raw),
        baseline_archive_bytes=case.baseline, originals_archive_bytes=case.originals)
    assert report["status"] == "accepted" and report["native_acquisition_performed"] is False


def test_entry_stop_plan_cli_preserves_an_existing_output(entry_stop_plan_case, tmp_path):
    case = entry_stop_plan_case
    target = tmp_path / "entry-stop-plan-verification.json"
    argv = [sys.executable, "-I", "-B",
        str(ROOT / "tools/check_required_gate_idempotence_entry_stop_plan_v0.py"),
        "--plan", str(ROOT / ENTRY_STOP_PLAN_REL), "--plan-sha256", digest(case.raw),
        "--output", str(target)]
    first = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60, check=False)
    assert first.returncode == 0, first.stderr.decode()
    saved = target.read_bytes()
    assert first.stdout == saved
    report = json.loads(saved)
    assert report["plan"] == bound(case.raw) and report["status"] == "accepted"
    assert report["native_acquisition_performed"] is False and report["authority_effect"] == "none"
    second = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60, check=False)
    assert second.returncode == 1 and target.read_bytes() == saved
    assert json.loads(second.stderr)["status"] == "rejected"
