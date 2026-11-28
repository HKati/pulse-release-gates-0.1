#!/usr/bin/env python3
"""Preserve two fixed compile-only builds of the selected task-guard probe.

No output executable is run. The selected compiler is opened and byte-bound
before invocation; its descriptor remains pinned through both builds. Recorded
process observations and equal ELF outputs do not authenticate the compiler's
runtime closure, physical execution, or source/binary semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_selection_v0 as checker


READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
DIRECTORY_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY
BUILD_IDS = ("build-1", "build-2")


def need(condition, code):
    checker.need(condition, code)


def failure_code(exc, default="probe_build_operation_failed"):
    code = getattr(exc, "code", None)
    return code if type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code) else default


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _object(info):
    return info.st_dev, info.st_ino


def _absolute(path):
    try:
        value = os.fspath(path)
    except TypeError as exc:
        raise checker.SelectionError("probe_build_path_invalid") from exc
    need(type(value) is str and value.startswith("/") and "\0" not in value
         and value == os.path.normpath(value) and value != "/", "probe_build_path_invalid")
    return value


class _PinnedParent:
    """Keep every directory component and its public parent relation pinned."""

    def __init__(self, path):
        self.path = _absolute(path)
        parts = self.path.split("/")[1:]
        self.leaf = parts[-1]
        self.descriptors = []
        self.names = []
        self.identities = []
        try:
            descriptor = os.open("/", DIRECTORY_FLAGS)
            self.descriptors.append(descriptor)
            self.identities.append(_object(os.fstat(descriptor)))
            for name in parts[:-1]:
                need(name not in ("", ".", ".."), "probe_build_parent_invalid")
                descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=self.descriptors[-1])
                self.names.append(name)
                self.descriptors.append(descriptor)
                self.identities.append(_object(os.fstat(descriptor)))
            self.verify()
        except BaseException:
            self.close()
            raise

    @property
    def fd(self):
        return self.descriptors[-1]

    def verify(self):
        need(bool(self.descriptors), "probe_build_parent_closed")
        for index, descriptor in enumerate(self.descriptors):
            info = os.fstat(descriptor)
            need(stat.S_ISDIR(info.st_mode) and _object(info) == self.identities[index],
                 "probe_build_parent_changed")
            if index:
                linked = os.stat(self.names[index - 1], dir_fd=self.descriptors[index - 1],
                                 follow_symlinks=False)
                need(stat.S_ISDIR(linked.st_mode) and _object(linked) == self.identities[index],
                     "probe_build_parent_replaced")
        need(_object(os.stat("/", follow_symlinks=False)) == self.identities[0],
             "probe_build_root_changed")

    def close(self):
        descriptors, self.descriptors = self.descriptors, []
        failed = False
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                failed = True
        need(not failed, "probe_build_parent_close_failed")


def _read_fd(descriptor, maximum, *, executable=False):
    before = os.fstat(descriptor)
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
         and not (before.st_mode & (stat.S_ISUID | stat.S_ISGID)), "probe_build_file_type")
    need(type(maximum) is int and 0 <= before.st_size <= maximum, "probe_build_file_limit")
    if executable:
        need(bool(before.st_mode & 0o111), "probe_build_compiler_not_executable")
    chunks = bytearray()
    offset = 0
    while len(chunks) <= maximum:
        block = os.pread(descriptor, min(65536, maximum + 1 - len(chunks)), offset)
        if not block:
            break
        chunks.extend(block)
        offset += len(block)
        need(len(chunks) <= maximum, "probe_build_file_limit")
    need(_identity(os.fstat(descriptor)) == _identity(before)
         and len(chunks) == before.st_size, "probe_build_file_changed")
    return bytes(chunks), _identity(before)


class _Compiler:
    def __init__(self, path, expected_sha256):
        self.path = _absolute(path)
        self.parent = _PinnedParent(self.path)
        self.fd = None
        try:
            self.fd = os.open(self.parent.leaf, READ_FLAGS, dir_fd=self.parent.fd)
            self.raw, self.identity = _read_fd(self.fd, checker.BUILD_LIMITS["compiler_bytes"], executable=True)
            need(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
                 and hashlib.sha256(self.raw).hexdigest() == expected_sha256,
                 "probe_build_compiler_digest")
            need(len(self.raw) >= 64 and self.raw[:7] == b"\x7fELF\x02\x01\x01"
                 and struct.unpack_from("<HHI", self.raw, 16) in ((2, 62, 1), (3, 62, 1)),
                 "probe_build_compiler_elf")
            self.descriptor = {"path": self.path, **checker.binding(self.raw)}
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        self.parent.verify()
        info = os.stat(self.parent.leaf, dir_fd=self.parent.fd, follow_symlinks=False)
        need(stat.S_ISREG(info.st_mode) and _identity(info) == self.identity,
             "probe_build_compiler_replaced")
        raw, identity = _read_fd(self.fd, checker.BUILD_LIMITS["compiler_bytes"], executable=True)
        need(identity == self.identity and raw == self.raw, "probe_build_compiler_changed")
        return {"path": self.path, **checker.binding(raw)}

    def close(self):
        failure = None
        if self.fd is not None:
            descriptor = self.fd
            self.fd = None
            try:
                os.close(descriptor)
            except OSError as exc:
                failure = exc
        try:
            self.parent.close()
        except BaseException as exc:
            failure = failure or exc
        need(failure is None, "probe_build_compiler_close_failed")


class _OwnedDirectory:
    """New private directory; no overwrite, reuse, extraction or cleanup removal."""

    def __init__(self, path):
        self.path = _absolute(path)
        self.parent = _PinnedParent(self.path)
        self.fd = None
        self.builds = {}
        self.files = {}
        self.reserved = {}
        try:
            os.mkdir(self.parent.leaf, 0o700, dir_fd=self.parent.fd)
            created = os.stat(self.parent.leaf, dir_fd=self.parent.fd, follow_symlinks=False)
            self.fd = os.open(self.parent.leaf, DIRECTORY_FLAGS, dir_fd=self.parent.fd)
            self.identity = _object(os.fstat(self.fd))
            need(stat.S_ISDIR(created.st_mode) and _object(created) == self.identity
                 and stat.S_IMODE(created.st_mode) == 0o700
                 and created.st_uid == os.geteuid(), "probe_build_directory_ownership")
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        self.parent.verify()
        linked = os.stat(self.parent.leaf, dir_fd=self.parent.fd, follow_symlinks=False)
        need(stat.S_ISDIR(linked.st_mode) and _object(linked) == self.identity
             and _object(os.fstat(self.fd)) == self.identity
             and stat.S_IMODE(linked.st_mode) == 0o700 and linked.st_uid == os.geteuid(),
             "probe_build_directory_replaced")
        for name, (descriptor, identity) in self.builds.items():
            info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            need(stat.S_ISDIR(info.st_mode) and _object(info) == identity
                 and _object(os.fstat(descriptor)) == identity
                 and stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.geteuid(),
                 "probe_build_work_directory_replaced")

    def mkdir(self, name):
        need(name in BUILD_IDS and name not in self.builds, "probe_build_work_directory_name")
        self.verify()
        os.mkdir(name, 0o700, dir_fd=self.fd)
        before = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=self.fd)
        try:
            need(stat.S_ISDIR(before.st_mode) and _object(before) == _object(os.fstat(descriptor))
                 and before.st_uid == os.geteuid() and stat.S_IMODE(before.st_mode) == 0o700,
                 "probe_build_work_directory_ownership")
            self.builds[name] = descriptor, _object(before)
            self.verify()
            os.fsync(self.fd)
            return descriptor
        except BaseException:
            if name not in self.builds:
                os.close(descriptor)
            raise

    def _at(self, name):
        if name in ("policy.json", "build.json"):
            return self.fd, name
        parts = name.split("/")
        need(len(parts) == 2 and parts[0] in self.builds
             and parts[1] in ("probe.c", "probe.elf"), "probe_build_output_name")
        return self.builds[parts[0]][0], parts[1]

    def reserve(self, name):
        self.verify()
        need(name not in self.files, "probe_build_file_already_owned")
        parent, leaf = self._at(name)
        descriptor = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=parent)
        self.files[name] = (_object(os.fstat(descriptor)), None)
        self.reserved[name] = descriptor
        os.fsync(parent)

    def write(self, name, raw):
        need(type(raw) is bytes, "probe_build_output_bytes")
        if name not in self.reserved:
            self.reserve(name)
        self.verify()
        descriptor = self.reserved[name]
        parent, leaf = self._at(name)
        info = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == 0
             and _object(info) == self.files[name][0]
             and _object(os.fstat(descriptor)) == self.files[name][0], "probe_build_output_replaced")
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, raw[offset:offset + 65536])
            need(count > 0, "probe_build_output_short_write")
            offset += count
        os.fsync(descriptor)
        self.files[name] = (self.files[name][0], raw)
        del self.reserved[name]
        os.close(descriptor)
        need(self.read(name, max(len(raw), 1)) == raw, "probe_build_output_readback")
        self.verify()

    def read(self, name, maximum, *, enforce_expected=True):
        self.verify()
        parent, leaf = self._at(name)
        descriptor = os.open(leaf, READ_FLAGS, dir_fd=parent)
        try:
            info = os.fstat(descriptor)
            need(info.st_uid == os.geteuid(), "probe_build_output_owner")
            if name in self.files:
                need(_object(info) == self.files[name][0], "probe_build_output_replaced")
            raw, identity_value = _read_fd(descriptor, maximum)
            need(_identity(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) == identity_value,
                 "probe_build_output_replaced")
            if enforce_expected and name in self.files and self.files[name][1] is not None:
                need(raw == self.files[name][1], "probe_build_output_changed")
            if name not in self.files:
                # Pin each compiler-created output at its first successful
                # observation, so the final publication checks the same bytes.
                need(leaf == "probe.elf", "probe_build_unowned_file")
                self.files[name] = (_object(info), raw)
            self.verify()
            return raw
        finally:
            os.close(descriptor)

    def verify_build(self, name):
        self.verify()
        need(set(os.listdir(self.builds[name][0])) == {"probe.c", "probe.elf"},
             "probe_build_work_directory_inventory")
        return True

    def verify_complete(self):
        self.verify()
        need(set(os.listdir(self.fd)) == {"policy.json", "build.json", *BUILD_IDS},
             "probe_build_directory_inventory")
        for name in BUILD_IDS:
            self.verify_build(name)
        for name, (_identity_value, raw) in self.files.items():
            if raw is not None:
                need(self.read(name, max(1, len(raw))) == raw, "probe_build_output_changed")
        return True

    def close(self):
        descriptors = list(self.reserved.values()) + [row[0] for row in self.builds.values()]
        self.reserved = {}
        self.builds = {}
        if self.fd is not None:
            descriptors.append(self.fd)
            self.fd = None
        failed = False
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                failed = True
        try:
            self.parent.close()
        except BaseException:
            failed = True
        need(not failed, "probe_build_directory_close_failed")

    def invalidate_completed(self, expected):
        """Remove only our exact completed record after a failed publication.

        Reopen through pinned parents because late close failure may have already
        disposed every original descriptor. Never remove a replacement inode or
        modified bytes; leave all other attempt files as the diagnostic prefix.
        """
        if type(expected) is not bytes or "build.json" not in self.files:
            return
        parent = None
        descriptor = None
        try:
            parent = _PinnedParent(self.path + "/build.json")
            if _object(os.fstat(parent.fd)) != self.identity:
                return
            descriptor = os.open(parent.leaf, READ_FLAGS, dir_fd=parent.fd)
            if _object(os.fstat(descriptor)) != self.files["build.json"][0]:
                return
            actual, identity = _read_fd(descriptor, checker.BUILD_LIMITS["record_bytes"])
            if actual != expected:
                return
            parent.verify()
            if _identity(os.stat(parent.leaf, dir_fd=parent.fd, follow_symlinks=False)) != identity:
                return
            os.unlink(parent.leaf, dir_fd=parent.fd)
            os.fsync(parent.fd)
        except BaseException:
            pass
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if parent is not None:
                try:
                    parent.close()
                except BaseException:
                    pass


class NativeCompilerBackend:
    """Run only the selected compiler through its pinned descriptor.

The session leader stays waitable until its owned compiler process group has
received cleanup. This does not claim a traced compiler descendant closure.
"""

    def __init__(self, compiler_fd):
        self.compiler_fd = compiler_fd
        self.unresolved_processes = []

    def run(self, argv, *, cwd_fd, environment, limits):
        need(sys.platform == "linux" and os.uname().machine == "x86_64",
             "probe_build_platform")
        need(environment == checker.BUILD_ENV and limits == checker.BUILD_LIMITS,
             "probe_build_backend_selection")
        need(type(self.compiler_fd) is int and self.compiler_fd >= 3
             and type(cwd_fd) is int and cwd_fd >= 3 and cwd_fd != self.compiler_fd,
             "probe_build_descriptor_layout")
        need(type(argv) is list and len(argv) == len(checker.CC_FLAGS) + 4
             and argv[1:] == [*checker.CC_FLAGS, "probe.c", "-o", "probe.elf"],
             "probe_build_backend_argv")
        need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL
             and os.listdir("/proc/self/task") == [str(os.getpid())],
             "probe_build_wait_consumer")
        started = time.monotonic_ns()
        deadline = time.monotonic() + limits["build_seconds"]
        buffers = {name: bytearray() for name in ("stdout", "stderr")}
        flags = {"timed_out": False, "stdout_overflow": False, "stderr_overflow": False}
        child = None
        selector = None
        failure = None
        cleanup_failures = []
        reaped = False

        def retain(name, raw):
            nonlocal failure
            available = limits[name + "_bytes"] - len(buffers[name])
            buffers[name].extend(raw[:available])
            if len(raw) > available:
                flags[name + "_overflow"] = True
                failure = failure or "probe_build_" + name + "_limit"

        try:
            child = subprocess.Popen(argv, executable="/proc/self/fd/" + str(self.compiler_fd),
                cwd="/proc/self/fd/" + str(cwd_fd), env=dict(environment), shell=False,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                close_fds=True, pass_fds=(self.compiler_fd, cwd_fd),
                start_new_session=True, umask=0o077)
            selector = selectors.DefaultSelector()
            for name in buffers:
                stream = getattr(child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() and failure is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    flags["timed_out"] = True
                    failure = "probe_build_timeout"
                    break
                for key, _mask in selector.select(min(remaining, 0.1)):
                    name = key.data
                    available = limits[name + "_bytes"] - len(buffers[name])
                    try:
                        raw = os.read(key.fd, min(65536, available + 1))
                    except BlockingIOError:
                        continue
                    if not raw:
                        selector.unregister(key.fileobj)
                    else:
                        retain(name, raw)
                    if failure is not None:
                        break
            if failure is None:
                while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        flags["timed_out"] = True
                        failure = "probe_build_timeout"
                        break
                    time.sleep(min(remaining, 0.01))
        except BaseException as exc:
            failure = failure or failure_code(exc, "probe_build_spawn_failed" if child is None
                                               else "probe_build_process_operation_failed")
        finally:
            cleanup_deadline = time.monotonic() + limits["cleanup_seconds"]
            if child is not None:
                owned = False
                try:
                    os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    owned = True
                except (ChildProcessError, OSError):
                    cleanup_failures.append("probe_build_wait_ownership_lost")
                if owned:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except OSError:
                        cleanup_failures.append("probe_build_group_signal_failed")
                    try:
                        os.kill(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except OSError:
                        cleanup_failures.append("probe_build_leader_signal_failed")
                    try:
                        child.wait(timeout=max(0.001, cleanup_deadline - time.monotonic()))
                        reaped = True
                    except (subprocess.TimeoutExpired, ChildProcessError, OSError):
                        cleanup_failures.append("probe_build_reap_failed")
                if not reaped:
                    self.unresolved_processes.append(child)
                # Already-acquired prefixes survive failures. Draining is
                # bounded and never waits beyond the separate cleanup deadline.
                for name in buffers:
                    stream = getattr(child, name, None)
                    if stream is None:
                        continue
                    try:
                        os.set_blocking(stream.fileno(), False)
                        while time.monotonic() < cleanup_deadline:
                            available = limits[name + "_bytes"] - len(buffers[name])
                            try:
                                raw = os.read(stream.fileno(), min(65536, available + 1))
                            except BlockingIOError:
                                break
                            if not raw:
                                break
                            retain(name, raw)
                            if flags[name + "_overflow"]:
                                break
                    except (OSError, ValueError):
                        cleanup_failures.append("probe_build_cleanup_stream_failed")
                    finally:
                        try:
                            stream.close()
                        except (OSError, ValueError):
                            cleanup_failures.append("probe_build_cleanup_stream_close_failed")
            if selector is not None:
                try:
                    selector.close()
                except (OSError, ValueError):
                    cleanup_failures.append("probe_build_cleanup_selector_close_failed")
        elapsed = max(0, time.monotonic_ns() - started)
        if child is not None and reaped and child.returncode != 0:
            failure = failure or "probe_build_nonzero"
        if elapsed > limits["build_seconds"] * 1_000_000_000:
            flags["timed_out"] = True
            failure = failure or "probe_build_timeout"
        process = None if child is None else {
            "pid": child.pid, "exit_code": child.returncode, "elapsed_ns": elapsed,
            **flags, "reaped": reaped}
        return {"process": process, "stdout": bytes(buffers["stdout"]),
                "stderr": bytes(buffers["stderr"]), "failure": failure,
                "cleanup_failures": cleanup_failures}


def _check_result(result):
    need(type(result) is dict and set(result) ==
         {"process", "stdout", "stderr", "failure", "cleanup_failures"}, "probe_build_backend_result")
    for name in ("stdout", "stderr"):
        need(type(result[name]) is bytes and len(result[name]) <= checker.BUILD_LIMITS[name + "_bytes"],
             "probe_build_backend_output")
    need(result["failure"] is None or (type(result["failure"]) is str
         and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", result["failure"])), "probe_build_backend_failure")
    need(type(result["cleanup_failures"]) is list and len(result["cleanup_failures"]) <= 16
         and all(type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code)
                 for code in result["cleanup_failures"]), "probe_build_backend_cleanup")
    process = result["process"]
    if process is None:
        need(result["failure"] is not None and result["stdout"] == result["stderr"] == b"",
             "probe_build_backend_unspawned")
        return
    need(type(process) is dict and set(process) == {"pid", "exit_code", "elapsed_ns", "timed_out",
         "stdout_overflow", "stderr_overflow", "reaped"}, "probe_build_backend_process")
    need(type(process["pid"]) is int and 0 < process["pid"] < 2 ** 31
         and type(process["elapsed_ns"]) is int and 0 <= process["elapsed_ns"] < 2 ** 64,
         "probe_build_backend_process_value")
    need(process["exit_code"] is None or (type(process["exit_code"]) is int
         and -255 <= process["exit_code"] <= 255),
         "probe_build_backend_exit")
    need(all(type(process[name]) is bool for name in
         ("timed_out", "stdout_overflow", "stderr_overflow", "reaped")), "probe_build_backend_flags")


def capture_probe_build(*, compiler_path, expected_compiler_sha256, policy_bytes,
                        accepted_policy_sha256, output_directory, acknowledgement, backend=None):
    """Capture a fixed two-build attempt; explicit backends are always scripted.

Invalid preflight selection raises before a compiler invocation. Once the new
evidence directory is owned, recoverable failures are published as an incomplete
build.json. Publication failures raise and never claim a complete delivery.
"""
    need(acknowledgement == checker.BUILD_ACK, "probe_build_acknowledgement")
    checker.verify_policy(policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256)
    sources = checker.source_bytes()
    inventory = checker.verify_sources(inputs=sources)
    source = sources[checker.PROBE_PATH]
    compiler = _Compiler(compiler_path, expected_compiler_sha256)
    evidence = None
    record = None
    published_raw = None
    try:
        request = checker.derive_build_request(compiler=compiler.descriptor,
            policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256,
            source_inputs=sources)
        need(request["sources"] == inventory, "probe_build_source_inventory")
        evidence = _OwnedDirectory(output_directory)
        evidence.reserve("build.json")
        evidence.write("policy.json", policy_bytes)
        origin = "recorded_compile_only" if backend is None else "scripted_build_backend"
        selected_backend = NativeCompilerBackend(compiler.fd) if backend is None else backend
        record = {"record_type": checker.BUILD_TYPE, "profile": checker.PROFILE,
                  "attempt_id": uuid.uuid4().hex, "status": "incomplete", "evidence_origin": origin,
                  "request": request, "source_hex": source.hex(), "compiler_after": None,
                  "sources_after": [], "builds": [], "failure": None, "cleanup_failures": [],
                  "boundary": dict(checker.BOUNDARY)}

        def fail(exc, default="probe_build_operation_failed"):
            if record["failure"] is None:
                record["failure"] = failure_code(exc, default)

        try:
            for build_id in BUILD_IDS:
                compiler.verify()
                need(checker.source_bytes() == sources, "probe_build_sources_changed")
                cwd_fd = evidence.mkdir(build_id)
                evidence.write(build_id + "/probe.c", source)
                need(evidence.read(build_id + "/probe.c", len(source)) == source,
                     "probe_build_staged_source_changed")
                result = selected_backend.run(list(request["argv"]), cwd_fd=cwd_fd,
                    environment=dict(checker.BUILD_ENV), limits=dict(checker.BUILD_LIMITS))
                _check_result(result)
                if result["failure"] is not None:
                    record["failure"] = record["failure"] or result["failure"]
                record["cleanup_failures"].extend(result["cleanup_failures"])
                if result["process"] is None:
                    break
                row = {"build_id": build_id, "argv": list(request["argv"]),
                       "environment": dict(checker.BUILD_ENV), "source_hex": source.hex(),
                       "source_after_hex": None, "process": dict(result["process"]),
                       "stdout_hex": result["stdout"].hex(), "stderr_hex": result["stderr"].hex(),
                       "probe_hex": None, "directory_verified": False}
                record["builds"].append(row)
                try:
                    row["source_after_hex"] = evidence.read(build_id + "/probe.c", len(source),
                                                            enforce_expected=False).hex()
                    need(row["source_after_hex"] == source.hex(), "probe_build_staged_source_changed")
                except BaseException as exc:
                    fail(exc)
                try:
                    row["probe_hex"] = evidence.read(build_id + "/probe.elf", checker.BUILD_LIMITS["probe_bytes"]).hex()
                except BaseException as exc:
                    fail(exc, "probe_build_output_missing")
                try:
                    row["directory_verified"] = evidence.verify_build(build_id)
                except BaseException as exc:
                    fail(exc)
                process = row["process"]
                if (process["exit_code"] != 0 or not process["reaped"] or process["timed_out"]
                        or process["stdout_overflow"] or process["stderr_overflow"]
                        or process["elapsed_ns"] <= 0
                        or process["elapsed_ns"] > checker.BUILD_LIMITS["build_seconds"] * 1_000_000_000):
                    record["failure"] = record["failure"] or "probe_build_process_incomplete"
                if record["cleanup_failures"]:
                    record["failure"] = record["failure"] or "probe_build_cleanup_incomplete"
                if record["failure"] is not None:
                    break
                probe = bytes.fromhex(row["probe_hex"])
                checker.raw.verify_probe_elf(probe, expected_probe_sha256=checker.binding(probe)["sha256"])
                compiler.verify()
                need(checker.source_bytes() == sources, "probe_build_sources_changed")
            if record["failure"] is None:
                need(len(record["builds"]) == 2
                     and record["builds"][0]["probe_hex"] == record["builds"][1]["probe_hex"],
                     "probe_build_outputs_differ")
                evidence.verify_complete()
        except BaseException as exc:
            fail(exc)
        finally:
            try:
                record["compiler_after"] = compiler.verify()
            except BaseException as exc:
                fail(exc)
            try:
                after = checker.source_bytes()
                record["sources_after"] = checker.source_inventory(inputs=after)
                need(after == sources, "probe_build_sources_changed")
            except BaseException as exc:
                fail(exc)

        if record["failure"] is None and not record["cleanup_failures"]:
            record["status"] = "completed"
            try:
                raw = checker.canonical(record)
                checker.verify_build_record(record_bytes=raw,
                    expected_record_sha256=checker.binding(raw)["sha256"], policy_bytes=policy_bytes,
                    accepted_policy_sha256=accepted_policy_sha256, source_inputs=sources)
                evidence.verify_complete()
            except BaseException as exc:
                record["status"] = "incomplete"
                fail(exc)
        raw = checker.canonical(record)
        need(len(raw) <= checker.BUILD_LIMITS["record_bytes"], "probe_build_record_limit")
        published_raw = raw
        evidence.write("build.json", raw)
        need(evidence.read("build.json", checker.BUILD_LIMITS["record_bytes"]) == raw,
             "probe_build_record_readback")
        if record["status"] == "completed":
            evidence.verify_complete()
        return record
    except BaseException:
        if evidence is not None and record is not None and record["status"] == "completed":
            evidence.invalidate_completed(published_raw)
        raise
    finally:
        close_failure = None
        try:
            compiler.close()
        except BaseException as exc:
            close_failure = exc
        if evidence is not None:
            try:
                evidence.close()
            except BaseException as exc:
                close_failure = close_failure or exc
        if close_failure is not None:
            if evidence is not None and record is not None and record["status"] == "completed":
                evidence.invalidate_completed(published_raw)
            raise checker.SelectionError("probe_build_publication_close_failed") from close_failure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--expected-compiler-sha256", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--accepted-policy-sha256", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--acknowledgement", required=True)
    args = parser.parse_args(argv)
    try:
        record = capture_probe_build(compiler_path=args.compiler,
            expected_compiler_sha256=args.expected_compiler_sha256,
            policy_bytes=checker.read_file(args.policy, 65536),
            accepted_policy_sha256=args.accepted_policy_sha256,
            output_directory=args.out_dir, acknowledgement=args.acknowledgement)
    except BaseException as exc:
        print(failure_code(exc), file=sys.stderr)
        return 1
    if record["status"] != "completed":
        print(record["failure"] or "probe_build_incomplete", file=sys.stderr)
        return 1
    print(str(Path(args.out_dir) / "build.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
