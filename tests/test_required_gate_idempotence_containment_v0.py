#!/usr/bin/env python3
"""Synthetic containment regression; no selected runtime or operator executes.

Compiler tests use inert capsule bytes. Parent-process tests substitute an
authored host child at the Popen boundary; they never invoke bubblewrap or the
selected capsule. Only invalid-argument entry checks and a separate fixed-filter
child execute native test code. Neither establishes namespace containment.
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
