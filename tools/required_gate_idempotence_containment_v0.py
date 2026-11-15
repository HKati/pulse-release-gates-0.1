#!/usr/bin/env python3
"""Prepare a fixed pre-exec boundary and preserve bounded synthetic attempts.

Selected-runtime execution remains closed. The example-only primitive invokes
one selected host launcher with sealed input bytes and no host filesystem bind.
Its receipts are diagnostics, never host authentication or runtime qualification.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_bootstrap_v0 as bootstrap
import required_gate_idempotence_containment_policy_v0 as policy
import required_gate_idempotence_process_v0 as process
import check_required_gate_idempotence_containment_v0 as checker

ROOT = Path(__file__).resolve().parents[1]
PROFILE = checker.PROFILE
BOUNDARY = checker.BOUNDARY
BIN_LIMIT = 16 * 1024 * 1024
NAMESPACE_OPTIONS = (
    "--unshare-user", "--unshare-ipc", "--unshare-pid", "--unshare-net",
    "--unshare-uts", "--unshare-cgroup", "--disable-userns",
)
_ADMISSION = object()


class ContainmentError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class PreservationError(RuntimeError):
    code = "containment_preservation_failed"


def need(condition, code):
    if not condition:
        raise ContainmentError(code)


def binding(raw):
    return checker.binding(raw)


def canonical(value):
    return checker.canonical(value)


def _bound(raw, row, code):
    need(type(raw) is bytes and 0 < len(raw) <= BIN_LIMIT
         and binding(raw) == {key: row[key] for key in ("sha256", "size_bytes")}, code)


def _elf_header(raw):
    need(type(raw) is bytes and 64 <= len(raw) <= BIN_LIMIT, "containment_elf_size")
    need(raw[:7] == b"\x7fELF\x02\x01\x01" and raw[7] in (0, 3)
         and raw[8:16] == bytes(8), "containment_elf_identity")
    header = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    kind, machine, version, entry, phoff, _, flags, ehsize, phsize, phnum, *_ = header
    need(kind in (2, 3) and machine == 62 and version == 1 and flags == 0
         and ehsize == 64 and phsize == 56 and 0 < phnum <= 64
         and 64 <= phoff <= len(raw) and phnum * 56 <= len(raw) - phoff,
         "containment_elf_header")
    rows = [struct.unpack_from("<IIQQQQQQ", raw, phoff + index * 56) for index in range(phnum)]
    return kind, entry, rows


def validate_entry(raw):
    """Admit a bounded static ELF shape; do not claim source/binary equivalence."""
    kind, entry, rows = _elf_header(raw)
    need(kind == 2, "containment_entry_not_static_exec")
    need(all(row[0] not in {2, 3, 5} for row in rows), "containment_entry_dynamic_dependency")
    loads = [row for row in rows if row[0] == 1]
    stacks = [row for row in rows if row[0] == 0x6474E551]
    need(loads and len(stacks) == 1 and not (stacks[0][1] & 1), "containment_entry_stack_invalid")
    for _, flags, offset, address, _, size, memory, alignment in loads:
        need(offset <= len(raw) and size <= len(raw) - offset and size <= memory
             and address + memory < 2**64 and flags & ~7 == 0 and flags & 3 != 3
             and (alignment in (0, 1) or alignment & (alignment - 1) == 0),
             "containment_entry_segment_invalid")
        need(alignment < 2 or offset % alignment == address % alignment,
             "containment_entry_segment_alignment")
    need(any(flags & 1 and address <= entry < address + size
             for _, flags, _, address, _, size, _, _ in loads), "containment_entry_point_invalid")


def _argv(files, phase):
    # Mount namespace is unconditional in bubblewrap. Every other namespace is
    # requested strictly: no --try, broad host bind, /proc, /dev or fallback.
    argv = [*NAMESPACE_OPTIONS, "--cap-drop", "ALL", "--die-with-parent",
            "--clearenv", "--setenv", "LC_ALL", "C", "--setenv", "TZ", "UTC",
            "--tmpfs", "/"]
    directories = {"/empty"}
    for row in files:
        directories.update(str(parent) for parent in Path(row["path"]).parents if str(parent) != "/")
    for path in sorted(directories, key=lambda path: (path.count("/"), path)):
        argv.extend(("--perms", "0700", "--dir", path))
    for index, row in enumerate(files):
        argv.extend(("--perms", row["mode"], "--ro-bind-data", "@file:" + str(index), row["path"]))
    argv.extend(("--remount-ro", "/", "--seccomp", "@seccomp", "--chdir", "/empty",
                 "--", policy.ENTRY_PATH, phase))
    need(len(argv) + 2 < 9000, "containment_argument_budget_exceeded")
    return argv


@dataclass(frozen=True, init=False)
class PreparedContainment:
    inputs: tuple
    request_bytes: bytes
    contents: tuple
    _admission: object


def prepare_containment(*, bootstrap_prepared, expected_bootstrap_plan_sha256,
                        selection_bytes, expected_selection_sha256, launcher_bytes, entry_bytes):
    prepared = bootstrap._admitted(bootstrap_prepared)
    need(bootstrap.sha(prepared.plan_bytes) == expected_bootstrap_plan_sha256,
         "containment_bootstrap_plan_digest_mismatch")
    plan = bootstrap.parse(prepared.plan_bytes)
    selection = checker.validate_selection(selection_bytes, expected_selection_sha256,
                                           expected_bootstrap_plan_sha256, plan["record_status"])
    _bound(launcher_bytes, selection["launcher"], "containment_launcher_binding_mismatch")
    _bound(entry_bytes, selection["entry_shim"], "containment_entry_binding_mismatch")
    _elf_header(launcher_bytes)
    validate_entry(entry_bytes)
    sources = {}
    for key, path in (("entry_source", policy.ENTRY_SOURCE_PATH), ("policy_source", policy.POLICY_SOURCE_PATH)):
        sources[key] = bootstrap.runtime.observation.safe._read_regular(ROOT / path)
        _bound(sources[key], selection[key], "containment_implementation_binding_mismatch")
    contents = dict(prepared.contents)
    need(policy.ENTRY_PATH not in contents, "containment_entry_path_collision")
    contents[policy.ENTRY_PATH] = entry_bytes
    need(len(contents) <= bootstrap.MAX_VIEW_FILES
         and sum(map(len, contents.values())) <= bootstrap.VIEW_LIMIT, "containment_view_limit")
    files = []
    for path, raw in sorted(contents.items()):
        files.append({"path": path, "origin": "entry_shim" if path == policy.ENTRY_PATH else "bootstrap",
                      **binding(raw), "mode": "0500" if path in {policy.ENTRY_PATH, bootstrap.LOADER} else "0400"})
    file_paths = set(contents)
    need(not any(str(parent) in file_paths for path in contents for parent in Path(path).parents),
         "containment_view_path_collision")
    launch = next(row for row in plan["launches"] if row["phase"] == selection["phase"])
    request = {
        "record_type": "required_gate_idempotence_containment_request_v0", "profile": PROFILE,
        "record_status": selection["record_status"], "phase": selection["phase"],
        "bindings": {"bootstrap_plan": binding(prepared.plan_bytes), "containment_selection": binding(selection_bytes),
                     "launcher": binding(launcher_bytes), "entry_shim": binding(entry_bytes),
                     **{key: binding(raw) for key, raw in sources.items()}, "seccomp": binding(policy.policy_bytes())},
        "files": files, "empty_directories": plan["empty_directories"],
        "launch_policy": {"argv_template": _argv(files, selection["phase"]),
                          "environment": dict(bootstrap.ENVIRONMENT), "working_directory": "/",
                          "stdin": "empty_sealed_file", "limits": dict(bootstrap.LIMITS),
                          "selected_argv": launch["argv"], "selected_environment": launch["environment"],
                          "selected_working_directory": launch["working_directory"],
                          "initial_filter": policy.PROFILE, "same_process_execve": "permitted",
                          "launcher_new_session": True, "kill_scope": "owned_process_group",
                          "child_nofile_limit": 64, "file_descriptor_headroom": len(files) + 16,
                          "source_binary_equivalence_verified": False, "host_launcher_runtime_verified": False},
        **BOUNDARY,
    }
    raw_request = canonical(request)
    checker.parse(raw_request)
    result = object.__new__(PreparedContainment)
    object.__setattr__(result, "inputs", tuple(sorted({
        "bootstrap_prepared": prepared, "expected_bootstrap_plan_sha256": expected_bootstrap_plan_sha256,
        "selection_bytes": selection_bytes, "expected_selection_sha256": expected_selection_sha256,
        "launcher_bytes": launcher_bytes, "entry_bytes": entry_bytes}.items())))
    object.__setattr__(result, "request_bytes", raw_request)
    object.__setattr__(result, "contents", tuple(sorted(contents.items())))
    object.__setattr__(result, "_admission", _ADMISSION)
    return result


def _admitted(prepared):
    need(type(prepared) is PreparedContainment and getattr(prepared, "_admission", None) is _ADMISSION,
         "containment_preparation_required")
    checked = prepare_containment(**dict(prepared.inputs))
    need(checked.request_bytes == prepared.request_bytes and checked.contents == prepared.contents,
         "containment_prepared_bytes_mismatch")
    return checked


def verify_request(prepared, *, request_bytes, expected_request_sha256):
    checked = _admitted(prepared)
    need(type(request_bytes) is bytes and bootstrap.sha(request_bytes) == expected_request_sha256,
         "containment_request_digest_mismatch")
    need(request_bytes == checked.request_bytes, "containment_request_reconstruction_mismatch")
    return {"record_type": "required_gate_idempotence_containment_verification_v0", "status": "accepted",
            "request_sha256": expected_request_sha256, "boundary_request_verified": True,
            "attempt_complete": False, "finite_diagnostic_valid": False, **BOUNDARY}


def verify_attempt(prepared, *, receipt_bytes, expected_receipt_sha256, stdout_bytes, stderr_bytes):
    checked = _admitted(prepared)
    return checker.verify_receipt(request_bytes=checked.request_bytes,
                                  expected_request_sha256=bootstrap.sha(checked.request_bytes),
                                  receipt_bytes=receipt_bytes, expected_receipt_sha256=expected_receipt_sha256,
                                  stdout_bytes=stdout_bytes, stderr_bytes=stderr_bytes,
                                  probe_contract_bytes=dict(checked.contents)[bootstrap.CONTRACT_VIRTUAL])


def _seal(stack, name, raw):
    fd = process.sealed_buffer("containment-" + name, raw)
    stack.callback(os.close, fd)
    return fd


def _verify_preserved(directory, expected, identities):
    before_root = os.fstat(directory.fd)
    need(stat.S_ISDIR(before_root.st_mode) and stat.S_IMODE(before_root.st_mode) == 0o700,
         "containment_preserved_directory_invalid")
    with os.scandir(directory.fd) as entries:
        need({entry.name for entry in entries} == set(expected), "containment_preserved_inventory_mismatch")
    for name, raw in expected.items():
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory.fd)
        try:
            before = os.fstat(fd)
            need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                 and stat.S_IMODE(before.st_mode) == 0o600
                 and (before.st_dev, before.st_ino) == identities[name]
                 and before.st_size == len(raw), "containment_preserved_file_mismatch")
            chunks = bytearray()
            while len(chunks) <= len(raw):
                chunk = os.read(fd, min(65536, len(raw) + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
            need(bytes(chunks) == raw and bootstrap.runtime._identity(before) == bootstrap.runtime._identity(os.fstat(fd)),
                 "containment_preserved_file_mismatch")
        finally:
            os.close(fd)
    need(bootstrap.runtime._identity(before_root) == bootstrap.runtime._identity(os.fstat(directory.fd)),
         "containment_preserved_directory_changed")


def _backend(prepared, sink):
    """Single host-launcher attempt; bounded output survives every observed exit."""
    request = checker.parse(prepared.request_bytes)
    inputs = dict(prepared.inputs)
    limits = request["launch_policy"]["limits"]
    caps = {"stdout": limits["stdout_bytes"], "stderr": limits["stderr_bytes"]}
    buffers = {name: bytearray() for name in caps}
    sink_failed = False

    def retain(name, raw):
        nonlocal sink_failed
        try:
            sink(name, raw)
        except Exception as exc:
            sink_failed = True
            raise PreservationError("containment_preservation_failed") from exc
        buffers[name].extend(raw)

    observation = {"pid": None, "exit_code": None, "started_monotonic_ns": time.monotonic_ns(),
                   "completed_monotonic_ns": None}
    failure = None
    child = None
    deadline = time.monotonic() + limits["wall_seconds"]
    with ExitStack() as stack:
        try:
            launcher_fd = _seal(stack, "launcher", inputs["launcher_bytes"])
            stdin_fd = _seal(stack, "stdin", b"")
            seccomp_fd = _seal(stack, "seccomp", policy.policy_bytes())
            content = dict(prepared.contents)
            descriptors = [_seal(stack, "file-" + str(index), content[row["path"]])
                           for index, row in enumerate(request["files"])]
            substitutions = {"@seccomp": str(seccomp_fd),
                             **{"@file:" + str(index): str(fd) for index, fd in enumerate(descriptors)}}
            argv = [substitutions.get(value, value) for value in request["launch_policy"]["argv_template"]]
            args_fd = _seal(stack, "arguments", b"\0".join(value.encode("ascii") for value in argv) + b"\0")
            need(time.monotonic() < deadline, "containment_deadline_exceeded")
            child = subprocess.Popen(["bubblewrap", "--args", str(args_fd)],
                                     executable="/proc/self/fd/" + str(launcher_fd),
                                     stdin=stdin_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     cwd="/", env=dict(bootstrap.ENVIRONMENT), close_fds=True,
                                     pass_fds=tuple(sorted({launcher_fd, seccomp_fd, args_fd, *descriptors})),
                                     start_new_session=True)
            observation["pid"] = child.pid
            for name in caps:
                stack.callback(getattr(child, name).close)
            selector = stack.enter_context(selectors.DefaultSelector())
            for name in caps:
                stream = getattr(child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = "containment_deadline_exceeded"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    name = key.data
                    try:
                        raw = os.read(key.fd, min(65536, caps[name] - len(buffers[name]) + 1))
                    except BlockingIOError:
                        continue
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    available = caps[name] - len(buffers[name])
                    retained = raw[:available]
                    if retained:
                        retain(name, retained)
                    if len(raw) > available:
                        failure = "containment_" + name + "_limit"
                        break
                if failure:
                    break
            if not failure:
                try:
                    child.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    failure = "containment_deadline_exceeded"
            if not failure and child.returncode != 0:
                failure = "containment_backend_exit_nonzero"
        except (OSError, ValueError, ContainmentError, process.ProcessError) as exc:
            failure = (exc.code if isinstance(exc, ContainmentError) else
                       "containment_spawn_failed" if child is None else "containment_backend_operation_failed")
        finally:
            if child is not None:
                if child.returncode is None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.kill()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    failure = "containment_backend_reap_failed"
                observation["exit_code"] = child.returncode
                if failure and not sink_failed:
                    # Stop first, then retain only bytes already readable. Each
                    # pipe has its own remaining cap; never wait for more data.
                    try:
                        for name in caps:
                            stream = getattr(child, name)
                            os.set_blocking(stream.fileno(), False)
                            while len(buffers[name]) < caps[name]:
                                try:
                                    raw = os.read(stream.fileno(), min(65536, caps[name] - len(buffers[name])))
                                except BlockingIOError:
                                    break
                                if not raw:
                                    break
                                retain(name, raw)
                    except (OSError, ValueError) as exc:
                        raise PreservationError("containment_preservation_failed") from exc
            observation["completed_monotonic_ns"] = time.monotonic_ns()
    if not failure and observation["completed_monotonic_ns"] - observation["started_monotonic_ns"] > limits["wall_seconds"] * 1_000_000_000:
        failure = "containment_deadline_exceeded"
    return observation, failure, {name: bytes(raw) for name, raw in buffers.items()}


def run_example(prepared, *, output_directory):
    """Explicit synthetic route only. Never retry, qualify or unlock acquisition."""
    prepared = _admitted(prepared)
    request = checker.parse(prepared.request_bytes)
    need(request["record_status"] == "example", "selected_bootstrap_execution_not_ready")
    need(sys.platform == "linux" and platform.machine() == "x86_64" and hasattr(os, "memfd_create"),
         "containment_platform_unsupported")
    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    need(soft == resource.RLIM_INFINITY or soft >= request["launch_policy"]["file_descriptor_headroom"],
         "containment_descriptor_budget_insufficient")
    directory = None
    try:
        directory = bootstrap.runtime.acquisition._Directory(output_directory)
        expected = {"request.json": prepared.request_bytes, "selection.json": dict(prepared.inputs)["selection_bytes"],
                    "bootstrap_plan.json": dict(prepared.inputs)["bootstrap_prepared"].plan_bytes,
                    "attempt_start.json": canonical({"record_type": "required_gate_idempotence_containment_start_v0",
                        "request_sha256": bootstrap.sha(prepared.request_bytes), "attempt": 1, **BOUNDARY})}
        identities = {}
        for name, raw in expected.items():
            fd = directory.create(name)
            try:
                directory.append(fd, raw)
                info = os.fstat(fd)
                identities[name] = (info.st_dev, info.st_ino)
            finally:
                os.close(fd)
        with ExitStack() as stack:
            streams = {}
            for name in ("stdout", "stderr"):
                fd = directory.create(name + ".bin")
                stack.callback(os.close, fd)
                streams[name] = fd
                info = os.fstat(fd)
                identities[name + ".bin"] = (info.st_dev, info.st_ino)
            observed, failure, raw = _backend(prepared, lambda name, data: directory.append(streams[name], data))
        expected.update({name + ".bin": value for name, value in raw.items()})
        _verify_preserved(directory, expected, identities)
        if not failure:
            if raw["stderr"]:
                failure = "containment_stderr_not_empty"
            else:
                try:
                    checker.check_probe_report(raw["stdout"], checker.parse(dict(prepared.contents)[bootstrap.CONTRACT_VIRTUAL]),
                                               request["phase"])
                except checker.CheckerError:
                    failure = "containment_diagnostic_invalid"
        receipt = {"record_type": "required_gate_idempotence_containment_receipt_v0", "profile": PROFILE,
                   "status": "incomplete" if failure else "completed", "request_sha256": bootstrap.sha(prepared.request_bytes),
                   "phase": request["phase"], "streams": {name: binding(value) for name, value in raw.items()},
                   "process": observed, "error_code": failure, **BOUNDARY}
        receipt_bytes = canonical(receipt)
        checker.verify_receipt(request_bytes=prepared.request_bytes, expected_request_sha256=bootstrap.sha(prepared.request_bytes),
                               receipt_bytes=receipt_bytes, expected_receipt_sha256=bootstrap.sha(receipt_bytes),
                               stdout_bytes=raw["stdout"], stderr_bytes=raw["stderr"],
                               probe_contract_bytes=dict(prepared.contents)[bootstrap.CONTRACT_VIRTUAL])
        bootstrap.runtime._same_destination(directory.fd, output_directory)
        directory.write("receipt.json", receipt_bytes)
        return receipt
    except BaseException:
        if directory is not None:
            try:
                directory.write("attempt.incomplete.json", canonical({
                    "record_type": "required_gate_idempotence_containment_incomplete_v0", "status": "incomplete",
                    "error_code": "containment_preservation_failed", "request_sha256": bootstrap.sha(prepared.request_bytes), **BOUNDARY}))
            except Exception:
                pass
        raise
    finally:
        if directory is not None:
            directory.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check", "run-example", "check-attempt"))
    for name in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection", "bootstrap-plan", "containment-selection"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--entry-shim", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--request-sha256")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--stdout", type=Path)
    parser.add_argument("--stderr", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args(argv)
    read = lambda path, maximum=bootstrap.runtime.CONTROL_LIMIT: bootstrap.runtime.read_regular(path, maximum)
    output_parent = None
    try:
        if args.output is not None:
            output_parent, output_name = bootstrap.runtime.observation.safe._output_preflight(args.output)
        original = {name.replace("-", "_") + "_bytes": read(getattr(args, name.replace("-", "_")),
                    bootstrap.runtime.ARCHIVE_LIMIT if name == "capsule" else bootstrap.runtime.CONTROL_LIMIT)
                    for name in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection")}
        original.update({"expected_" + name.replace("-", "_") + "_sha256": getattr(args, name.replace("-", "_") + "_sha256")
                         for name in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection")})
        original["repository_root"] = args.repository_root
        preserved = bootstrap.prepare_bootstrap(**original)
        bootstrap.verify_bootstrap_plan(plan_bytes=read(args.bootstrap_plan), expected_plan_sha256=args.bootstrap_plan_sha256, **original)
        selection = checker.validate_selection(read(args.containment_selection), args.containment_selection_sha256)
        need(str(args.launcher) == selection["launcher"]["path"], "containment_launcher_path_mismatch")
        prepared = prepare_containment(bootstrap_prepared=preserved, expected_bootstrap_plan_sha256=args.bootstrap_plan_sha256,
                     selection_bytes=read(args.containment_selection), expected_selection_sha256=args.containment_selection_sha256,
                     launcher_bytes=read(args.launcher, BIN_LIMIT), entry_bytes=read(args.entry_shim, BIN_LIMIT))
        if args.command == "prepare":
            need(args.output is not None and args.output_directory is None, "containment_output_required")
            bootstrap.runtime.observation.safe._write_output(output_parent, output_name, prepared.request_bytes)
            report = verify_request(prepared, request_bytes=prepared.request_bytes, expected_request_sha256=bootstrap.sha(prepared.request_bytes))
        else:
            need(args.request is not None and args.request_sha256 is not None, "containment_request_required")
            report = verify_request(prepared, request_bytes=read(args.request), expected_request_sha256=args.request_sha256)
            if args.command == "run-example":
                need(args.output_directory is not None and args.output is None, "containment_directory_required")
                report = run_example(prepared, output_directory=args.output_directory)
            elif args.command == "check-attempt":
                need(all(value is not None for value in (args.receipt, args.receipt_sha256, args.stdout, args.stderr)),
                     "containment_receipt_inputs_required")
                report = verify_attempt(prepared, receipt_bytes=read(args.receipt), expected_receipt_sha256=args.receipt_sha256,
                                        stdout_bytes=read(args.stdout), stderr_bytes=read(args.stderr))
            if args.output is not None:
                bootstrap.runtime.observation.safe._write_output(output_parent, output_name, canonical(report))
        sys.stdout.buffer.write(canonical(report))
        return 0 if report.get("status") in {"accepted", "completed"} else 1
    except (ContainmentError, PreservationError, checker.CheckerError, bootstrap.BootstrapError,
            bootstrap.runtime.CapsuleError, bootstrap.runtime.observation.safe.ContractError,
            bootstrap.runtime.acquisition.AcquisitionError, OSError, ValueError, TypeError, KeyError) as exc:
        sys.stdout.buffer.write(canonical({"record_type": "required_gate_idempotence_containment_verification_v0",
                                          "status": "rejected", "error_code": getattr(exc, "code", "containment_operation_failed"), **BOUNDARY}))
        return 1
    finally:
        if output_parent is not None:
            os.close(output_parent)


if __name__ == "__main__":
    raise SystemExit(main())
