#!/usr/bin/env python3
"""Bind a selected outer launcher and preserve passive host prerequisites.

This tool reads bytes and a fixed host-information whitelist. It never runs a
launcher, package manager, loader, preserved entry, selected runtime or model.
A checked plan records concrete byte relationships and pending qualification
obligations; it grants no execution or release authority.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import resource
import stat
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_launch_host_v0 as checker
import check_required_gate_idempotence_entry_build_v0 as entry_build
import required_gate_idempotence_containment_v0 as containment
import required_gate_idempotence_launcher_package_v0 as package

bootstrap = containment.bootstrap
runtime = bootstrap.runtime
safe = runtime.observation.safe
HOST_READ_LIMIT = 16384
HOST_PATHS = (
    "/proc/self/status",
    "/proc/sys/user/max_user_namespaces",
    "/proc/sys/kernel/unprivileged_userns_clone",
    "/proc/sys/kernel/apparmor_restrict_unprivileged_userns",
    "/proc/sys/vm/memfd_noexec",
    "/etc/ld.so.preload",
)
NAMESPACES = ("user", "mnt", "ipc", "pid", "net", "uts", "cgroup")
_ADMISSION = object()


def _read_host_file(path):
    """Read one fixed source, retaining an explicit failure or bounded prefix."""
    if path not in HOST_PATHS:
        raise checker.HostError("launch_host_observation_path_invalid")
    fd = None
    result = {"path": path, "status": "unreadable", "data_b64": None}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            result["status"] = "unsafe"
            return result
        data = bytearray()
        while len(data) <= HOST_READ_LIMIT:
            block = os.read(fd, min(4096, HOST_READ_LIMIT + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        result["status"] = "oversize" if len(data) > HOST_READ_LIMIT else "present"
        result["data_b64"] = base64.b64encode(bytes(data[:HOST_READ_LIMIT])).decode("ascii")
    except OSError as exc:
        result["status"] = ("absent" if exc.errno == errno.ENOENT else
                            "unsafe" if exc.errno in {errno.ELOOP, errno.ENOTDIR} else "unreadable")
        result["data_b64"] = None
    finally:
        if fd is not None:
            os.close(fd)
    return result


def _namespace(name):
    if name not in NAMESPACES:
        raise checker.HostError("launch_host_namespace_invalid")
    result = {"name": name, "status": "unreadable", "target": None}
    try:
        result.update(status="present", target=os.readlink("/proc/self/ns/" + name))
    except OSError as exc:
        result["status"] = "absent" if exc.errno == errno.ENOENT else "unreadable"
    return result


def observe_host():
    """Return one passive snapshot. API availability is not operation success."""
    uname = os.uname()
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    try:
        with os.scandir("/proc/self/fd") as entries:
            open_fds = sum(1 for _ in entries)
    except OSError:
        open_fds = None
    value = {
        "record_type": "required_gate_idempotence_launch_host_observation_v0",
        "profile": checker.PROFILE,
        "observation_id": uuid.uuid4().hex,
        "platform": {"system": uname.sysname, "machine": uname.machine, "release": uname.release},
        "identity": {"uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid(), "egid": os.getegid()},
        "nofile": {"soft": "unlimited" if soft == resource.RLIM_INFINITY else soft,
                   "hard": "unlimited" if hard == resource.RLIM_INFINITY else hard},
        "memfd_create_api": callable(getattr(os, "memfd_create", None)),
        "open_fd_count": open_fds,
        "files": [_read_host_file(path) for path in HOST_PATHS],
        "namespaces": [_namespace(name) for name in NAMESPACES],
    }
    raw = checker.canonical(value)
    checker.validate_host_observation(raw)
    return raw


@dataclass(frozen=True, init=False)
class PreparedLaunchHost:
    inputs: tuple
    plan_bytes: bytes
    _admission: object


def _unfreeze(inputs):
    value = dict(inputs)
    for key in ("entry_build_payload", "native_payload"):
        value[key] = dict(value[key])
    return value


def prepare_launch_host(**inputs):
    plan_bytes = checker.derive_plan(**inputs)
    stored = dict(inputs)
    for key in ("entry_build_payload", "native_payload"):
        stored[key] = tuple(sorted(stored[key].items()))
    result = object.__new__(PreparedLaunchHost)
    object.__setattr__(result, "inputs", tuple(sorted(stored.items())))
    object.__setattr__(result, "plan_bytes", plan_bytes)
    object.__setattr__(result, "_admission", _ADMISSION)
    return result


def verify_launch_host(prepared, *, plan_bytes, expected_plan_sha256):
    if type(prepared) is not PreparedLaunchHost or getattr(prepared, "_admission", None) is not _ADMISSION:
        raise checker.HostError("launch_host_preparation_required")
    inputs = _unfreeze(prepared.inputs)
    if checker.derive_plan(**inputs) != prepared.plan_bytes:
        raise checker.HostError("launch_host_prepared_bytes_mismatch")
    return checker.verify_plan(plan_bytes=plan_bytes, expected_plan_sha256=expected_plan_sha256, **inputs)


def read_native_directory(path, selection):
    """Read the exact roster with selected per-file bounds and pinned paths."""
    path = Path(path).absolute()
    root_fd = entry_build._open_directory(path)
    selected = {row["path"]: row for row in selection["native_files"]}
    payload = {}

    def scan(fd, prefix):
        before = os.fstat(fd)
        expected = {name[len(prefix):].split("/", 1)[0] for name in selected if name.startswith(prefix)}
        with os.scandir(fd) as entries:
            names = {item.name for item in entries}
        if names != expected:
            raise checker.HostError("launch_host_native_inventory_mismatch")
        for name in sorted(names):
            relative = prefix + name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if relative not in selected:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    if entry_build._identity(info) != entry_build._identity(os.fstat(child)):
                        raise checker.HostError("launch_host_native_directory_changed")
                    scan(child, relative + "/")
                finally:
                    os.close(child)
            else:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
                try:
                    if entry_build._identity(info) != entry_build._identity(os.fstat(child)):
                        raise checker.HostError("launch_host_native_file_changed")
                    raw = runtime._read_fd(child, selected[relative]["size_bytes"], allow_empty=False)
                    descriptor = {key: selected[relative][key] for key in ("sha256", "size_bytes")}
                    if checker.binding(raw) != descriptor:
                        raise checker.HostError("launch_host_native_file_binding_mismatch")
                    payload[relative] = raw
                finally:
                    os.close(child)
        if entry_build._identity(before) != entry_build._identity(os.fstat(fd)):
            raise checker.HostError("launch_host_native_directory_changed")

    try:
        scan(root_fd, "")
        if set(payload) != set(selected):
            raise checker.HostError("launch_host_native_inventory_mismatch")
        current = entry_build._open_directory(path)
        try:
            if entry_build._identity(os.fstat(current)) != entry_build._identity(os.fstat(root_fd)):
                raise checker.HostError("launch_host_native_directory_changed")
        finally:
            os.close(current)
        return payload
    finally:
        os.close(root_fd)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    observer = commands.add_parser("observe-host", help="Preserve one passive finite host snapshot.")
    observer.add_argument("--output", type=Path, required=True)
    for name in ("prepare", "check"):
        command = commands.add_parser(name)
        for item in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection",
                     "bootstrap-plan", "containment-selection", "containment-request", "launch-host-selection"):
            command.add_argument("--" + item, type=Path, required=True)
            command.add_argument("--" + item + "-sha256", required=True)
        for item in ("launcher", "entry-shim", "entry-build-directory", "launcher-package", "native-root", "host-observation"):
            command.add_argument("--" + item, type=Path, required=True)
        command.add_argument("--repository-root", type=Path)
        command.add_argument("--output", type=Path, required=name == "prepare")
        if name == "check":
            command.add_argument("--plan", type=Path, required=True)
            command.add_argument("--plan-sha256", required=True)
    return parser


def _original_inputs(args):
    read = runtime.read_regular
    original = {"repository_root": args.repository_root}
    for name in ("runtime_selection", "operator_selection", "capsule", "bootstrap_selection"):
        original[name + "_bytes"] = read(getattr(args, name), runtime.ARCHIVE_LIMIT if name == "capsule" else runtime.CONTROL_LIMIT)
        original["expected_" + name + "_sha256"] = getattr(args, name + "_sha256")
    preserved = bootstrap.prepare_bootstrap(**original)
    bootstrap.verify_bootstrap_plan(plan_bytes=read(args.bootstrap_plan, runtime.CONTROL_LIMIT),
                                    expected_plan_sha256=args.bootstrap_plan_sha256, **original)
    containment_selection_bytes = read(args.containment_selection, runtime.CONTROL_LIMIT)
    selected = containment.checker.validate_selection(containment_selection_bytes, args.containment_selection_sha256)
    if str(args.launcher) != selected["launcher"]["path"]:
        raise checker.HostError("launch_host_launcher_path_mismatch")
    prepared = containment.prepare_containment(
        bootstrap_prepared=preserved, expected_bootstrap_plan_sha256=args.bootstrap_plan_sha256,
        selection_bytes=containment_selection_bytes, expected_selection_sha256=args.containment_selection_sha256,
        launcher_bytes=read(args.launcher, containment.BIN_LIMIT), entry_bytes=read(args.entry_shim, containment.BIN_LIMIT))
    containment.verify_request(prepared, request_bytes=read(args.containment_request, runtime.CONTROL_LIMIT),
                               expected_request_sha256=args.containment_request_sha256)
    selection_bytes = read(args.launch_host_selection, runtime.CONTROL_LIMIT)
    selection = checker.validate_selection(selection_bytes, args.launch_host_selection_sha256)
    return {
        "containment_prepared": prepared,
        "expected_containment_request_sha256": args.containment_request_sha256,
        "selection_bytes": selection_bytes,
        "expected_selection_sha256": args.launch_host_selection_sha256,
        "entry_build_payload": entry_build.read_directory(args.entry_build_directory),
        "launcher_package_bytes": read(args.launcher_package, 32 * 1024 * 1024),
        "native_payload": read_native_directory(args.native_root, selection),
        "host_observation_bytes": read(args.host_observation, runtime.CONTROL_LIMIT),
    }


def main(argv=None):
    args = _parser().parse_args(argv)
    output_parent = None
    try:
        if args.output is not None:
            output_parent, output_name = safe._output_preflight(args.output)
        if args.command == "observe-host":
            raw = observe_host()
            safe._write_output(output_parent, output_name, raw)
        else:
            inputs = _original_inputs(args)
            if args.command == "prepare":
                prepared = prepare_launch_host(**inputs)
                # Check the exact bytes before publishing a plan.
                report = checker.verify_plan(plan_bytes=prepared.plan_bytes,
                                             expected_plan_sha256=checker.sha(prepared.plan_bytes), **inputs)
                safe._write_output(output_parent, output_name, prepared.plan_bytes)
            else:
                report = checker.verify_plan(plan_bytes=runtime.read_regular(args.plan, runtime.CONTROL_LIMIT),
                                             expected_plan_sha256=args.plan_sha256, **inputs)
                if output_parent is not None:
                    safe._write_output(output_parent, output_name, checker.canonical(report))
            raw = checker.canonical(report)
        sys.stdout.buffer.write(raw)
        return 0
    except (checker.HostError, package.PackageError, entry_build.BuildError,
            containment.ContainmentError, containment.checker.CheckerError,
            bootstrap.BootstrapError, runtime.CapsuleError, runtime.observation.VerificationError,
            runtime.acquisition.AcquisitionError, safe.ContractError,
            OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_launch_host_verification_v0",
            "profile": checker.PROFILE, "status": "rejected",
            "error_code": getattr(exc, "code", "launch_host_operation_failed"), **checker.BOUNDARY,
        }))
        return 1
    finally:
        if output_parent is not None:
            os.close(output_parent)


if __name__ == "__main__":
    raise SystemExit(main())
