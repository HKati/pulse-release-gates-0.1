#!/usr/bin/env python3
"""Select a preserved probe build and read-only observer context before execution.

This command creates a new selection file only. It never imports the native
qualifier, invokes a compiler or probe, creates a child, or changes observer
state. A supplied environment reader always identifies scripted evidence.
Actual qualification and its separately authorized attempt remain later work.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import stat
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_selection_v0 as checker

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
CONTROL_BYTES = 2 * 1024 * 1024
PROC_BYTES = 65536
SECURITY_FIELDS = ("NoNewPrivs", "Seccomp", "Seccomp_filters", "CapEff", "CapPrm",
                   "CapInh", "CapBnd", "CapAmb")


class SelectionPreparationError(ValueError):
    """A bounded error code without reflected filesystem or parser content."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise SelectionPreparationError(code)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid)


def _read_fd(fd, maximum, *, empty=False, rewind=True):
    """Read bounded regular/proc bytes while preserving the opened identity."""
    need(type(maximum) is int and 0 < maximum <= 64 * 1024 * 1024,
         "guard_selection_read_bound")
    before = os.fstat(fd)
    need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum,
         "guard_selection_read_type")
    if rewind:
        os.lseek(fd, 0, os.SEEK_SET)
    result = bytearray()
    while len(result) <= maximum:
        block = os.read(fd, min(65536, maximum + 1 - len(result)))
        if not block:
            break
        result.extend(block)
        need(len(result) <= maximum, "guard_selection_read_extent")
    after = os.fstat(fd)
    need(_identity(before) == _identity(after)
         and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
         == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
         "guard_selection_read_changed")
    need(empty or bool(result), "guard_selection_read_empty")
    return bytes(result)


def _open_parent(path):
    path = Path(path)
    need(".." not in path.parts and "\x00" not in str(path), "guard_selection_path")
    if not path.is_absolute():
        path = Path.cwd() / path
    need(len(path.parts) > 1 and path.name not in ("", ".", ".."),
         "guard_selection_path")
    directory = os.open(path.anchor, DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=directory)
            os.close(directory)
            directory = child
        return path, directory, path.name
    except BaseException:
        os.close(directory)
        raise


def _read_regular(path, maximum):
    _path, directory, name = _open_parent(path)
    fd = None
    try:
        fd = os.open(name, READ_FLAGS, dir_fd=directory)
        return _read_fd(fd, maximum)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def _proc_read(proc, name, maximum, *, empty=False, follow=False):
    flags = READ_FLAGS & ~os.O_NOFOLLOW if follow else READ_FLAGS
    fd = os.open(name, flags, dir_fd=proc)
    try:
        return _read_fd(fd, maximum, empty=empty, rewind=False)
    finally:
        os.close(fd)


def _status_fields(raw):
    fields = {}
    for row in raw.decode("ascii").splitlines():
        key, separator, value = row.partition(":")
        need(separator and key not in fields, "guard_selection_status_shape")
        fields[key] = value.strip()
    need(all(name in fields for name in SECURITY_FIELDS), "guard_selection_status_fields")
    return fields


def read_environment():
    """Read the exact #3063 context shape without preparing a native observer."""
    need(sys.platform == "linux" and os.uname().machine == "x86_64"
         and sys.byteorder == "little" and struct.calcsize("P") == 8
         and os.sysconf("SC_PAGE_SIZE") == 4096, "guard_selection_platform")
    ids = {"uid": os.getuid(), "euid": os.geteuid(),
           "gid": os.getgid(), "egid": os.getegid()}
    need(ids["uid"] == ids["euid"] > 0 and ids["gid"] == ids["egid"] > 0,
         "guard_selection_nonroot_ids")
    own = str(os.getpid())
    need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
         "guard_selection_sigchld_handler")
    for fd in (0, 1, 2):
        os.fstat(fd)
    proc = os.open("/proc/" + own, DIRECTORY_FLAGS)
    task_dir = None
    try:
        task_dir = os.open("task", DIRECTORY_FLAGS, dir_fd=proc)
        need(os.listdir(task_dir) == [own], "guard_selection_observer_threads")
        fields = _status_fields(_proc_read(proc, "status", PROC_BYTES))
        need(all(int(fields[name], 16) == 0 for name in ("CapEff", "CapPrm", "CapInh")),
             "guard_selection_observer_capabilities")
        namespaces = {}
        for name in checker.raw.NAMESPACE_NAMES:
            try:
                namespaces[name] = os.readlink("ns/" + name, dir_fd=proc)
            except FileNotFoundError:
                need(name in ("time", "time_for_children"), "guard_selection_namespace_missing")
                namespaces[name] = None
        # The kernel-owned executable link is deliberately followed through the
        # pinned current-task directory. No caller-controlled link is followed.
        executable = _proc_read(proc, "exe", 64 * 1024 * 1024, follow=True)
        uname = os.uname()
        result = {
            "uname": {name: getattr(uname, name)
                      for name in ("sysname", "release", "version", "machine")},
            "boot_id": _read_regular("/proc/sys/kernel/random/boot_id", 128).decode("ascii").strip(),
            "observer_executable": checker.binding(executable),
            "python_version": list(sys.version_info[:3]),
            "ids": ids,
            "security": {name: int(fields[name]) if name in
                         ("NoNewPrivs", "Seccomp", "Seccomp_filters") else fields[name]
                         for name in SECURITY_FIELDS},
            "lsm_label_hex": _proc_read(proc, "attr/current", 4096, empty=True).hex(),
            "namespaces": namespaces,
        }
        checker.raw.validate_environment(result)
        return result
    finally:
        if task_dir is not None:
            os.close(task_dir)
        os.close(proc)


def _check_output(path, directory, name, fd, selected, expected):
    current = os.stat(name, dir_fd=directory, follow_symlinks=False)
    need(_identity(current) == _identity(selected)
         and _identity(os.fstat(fd)) == _identity(selected),
         "guard_selection_output_replaced")
    need(_read_fd(fd, max(1, len(expected)), empty=True) == expected,
         "guard_selection_output_changed")
    _path, public_parent, _leaf = _open_parent(path)
    try:
        parent_before, parent_after = os.fstat(directory), os.fstat(public_parent)
        need((parent_before.st_dev, parent_before.st_ino) ==
             (parent_after.st_dev, parent_after.st_ino), "guard_selection_parent_replaced")
        public = os.stat(name, dir_fd=public_parent, follow_symlinks=False)
        need(_identity(public) == _identity(selected), "guard_selection_output_replaced")
    finally:
        os.close(public_parent)


def _invalidate_owned(fd, selected, path):
    """Invalidate this call's inode only, never a substituted path or descriptor."""
    try:
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) == (selected.st_dev, selected.st_ino):
            os.ftruncate(fd, 0)
            os.fsync(fd)
            return
    except OSError:
        pass
    parent = reopened = None
    try:
        _path, parent, name = _open_parent(path)
        reopened = os.open(name, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC |
                           os.O_NONBLOCK, dir_fd=parent)
        current = os.fstat(reopened)
        if (current.st_dev, current.st_ino) == (selected.st_dev, selected.st_ino):
            os.ftruncate(reopened, 0)
            os.fsync(reopened)
    except (OSError, ValueError):
        pass
    finally:
        for item in (reopened, parent):
            if item is not None:
                try:
                    os.close(item)
                except OSError:
                    pass


def _publish(fd, raw):
    need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
         "guard_selection_output_extent")
    need(os.fstat(fd).st_size == 0, "guard_selection_output_not_empty")
    os.lseek(fd, 0, os.SEEK_SET)
    pending = memoryview(raw)
    while pending:
        count = os.write(fd, pending)
        need(type(count) is int and count > 0, "guard_selection_output_short_write")
        pending = pending[count:]
    os.fsync(fd)


def prepare(*, build_record_bytes, expected_build_record_sha256, probe_bytes,
            expected_probe_sha256, policy_bytes, accepted_policy_sha256, output,
            environment_reader=None, selection_id=None):
    """Publish one independently checked selection without executing a subject."""
    reader = read_environment if environment_reader is None else environment_reader
    need(callable(reader), "guard_selection_environment_reader")
    origin = "local_readonly_context" if environment_reader is None else "scripted_context"
    inputs = checker.source_bytes()
    checker.verify_sources(inputs=inputs)
    environment = reader()
    checker.raw.validate_environment(environment)
    # Freeze the first reading before a substituted reader can mutate/reuse it.
    environment_bytes = checker.canonical(environment)
    environment = json.loads(environment_bytes)
    selection = checker.derive_selection(
        build_record_bytes=build_record_bytes,
        expected_build_record_sha256=expected_build_record_sha256,
        probe_bytes=probe_bytes, expected_probe_sha256=expected_probe_sha256,
        environment=environment, environment_origin=origin,
        policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256,
        selection_id=os.urandom(16).hex() if selection_id is None else selection_id,
        source_inputs=inputs)
    encoded = checker.canonical(selection)
    checker.verify_selection(
        selection_bytes=encoded, expected_selection_sha256=checker.binding(encoded)["sha256"],
        build_record_bytes=build_record_bytes,
        expected_build_record_sha256=expected_build_record_sha256,
        probe_bytes=probe_bytes, expected_probe_sha256=expected_probe_sha256,
        policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256,
        source_inputs=inputs)
    path, parent, name = _open_parent(output)
    fd = selected = None
    try:
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                     os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
        selected = os.fstat(fd)
        need(stat.S_ISREG(selected.st_mode) and selected.st_nlink == 1
             and stat.S_IMODE(selected.st_mode) == 0o600
             and selected.st_uid == os.geteuid(), "guard_selection_output_identity")
        _check_output(path, parent, name, fd, selected, b"")
        after = reader()
        checker.raw.validate_environment(after)
        need(checker.canonical(after) == environment_bytes, "guard_selection_environment_changed")
        need(checker.source_bytes() == inputs, "guard_selection_sources_changed")
        _publish(fd, encoded)
        _check_output(path, parent, name, fd, selected, encoded)
        os.fsync(parent)
        _check_output(path, parent, name, fd, selected, encoded)
        return selection
    except BaseException:
        if fd is not None and selected is not None:
            _invalidate_owned(fd, selected, path)
        raise
    finally:
        failure = None
        try:
            os.close(parent)
        except BaseException as exc:
            failure = exc
            if fd is not None and selected is not None:
                _invalidate_owned(fd, selected, path)
        if fd is not None:
            try:
                os.close(fd)
            except BaseException as exc:
                failure = failure or exc
                if selected is not None:
                    _invalidate_owned(fd, selected, path)
        if failure is not None:
            raise failure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--expected-build-record-sha256", required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--expected-probe-sha256", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--accepted-policy-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        prepare(build_record_bytes=checker.read_file(args.build_record, CONTROL_BYTES),
                expected_build_record_sha256=args.expected_build_record_sha256,
                probe_bytes=checker.read_file(args.probe, 262144),
                expected_probe_sha256=args.expected_probe_sha256,
                policy_bytes=checker.read_file(args.policy, 65536),
                accepted_policy_sha256=args.accepted_policy_sha256, output=args.out)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        code = getattr(exc, "code", "guard_selection_preparation_failed")
        if type(code) is not str or re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code) is None:
            code = "guard_selection_preparation_failed"
        print(code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
