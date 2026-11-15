#!/usr/bin/env python3
"""Preserve two fixed builds of the repository-owned static containment entry.

The resulting binaries are never executed. Toolchain paths and hashes are
observations of this producer, not proof of toolchain closure or physical
execution. Successful records retain all existing qualification boundaries.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_entry_build_v0 as checker
import required_gate_idempotence_containment_v0 as containment

runtime = containment.bootstrap.runtime
acquisition = runtime.acquisition
safe = runtime.observation.safe
ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/required_gate_idempotence_entry_build_v0.yml"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOOL_NAMES = ("as", "cc1", "collect2", "ld")


class PreservationError(RuntimeError):
    code = "entry_build_preservation_failed"


def _need(condition, code):
    checker.need(condition, code)


def _snapshot(path, maximum, *, executable=False):
    """Read one ordinary, single-link file through a non-following descriptor."""
    path = safe._absolute(Path(path))
    parent = fd = None
    try:
        parent, name = safe._parent_fd(path)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(fd)
        raw = runtime._read_fd(fd, maximum, allow_empty=not executable)
        _need(runtime._identity(before) == runtime._identity(os.fstat(fd)), "entry_build_file_changed")
        if executable:
            _need(bool(stat.S_IMODE(before.st_mode) & 0o111), "entry_build_tool_not_executable")
            _need(len(raw) >= 64 and raw[:7] == b"\x7fELF\x02\x01\x01"
                  and struct.unpack_from("<HHI", raw, 16) in {(2, 62, 1), (3, 62, 1)},
                  "entry_build_tool_elf_invalid")
        return raw, runtime._identity(before)
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def _tool(lookup_path):
    lookup = Path(lookup_path)
    _need(lookup.is_absolute() and str(lookup) == os.path.normpath(str(lookup)), "entry_build_tool_path_invalid")
    real = lookup.resolve(strict=True)
    raw, identity = _snapshot(real, checker.LIMITS["tool_bytes"], executable=True)
    return {"lookup_path": str(lookup), "path": str(real), **checker.binding(raw)}, identity


def _head(repository_root):
    safe._Reader(repository_root)
    environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
                   "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0",
                   "GIT_ASKPASS": "/bin/false", "GIT_SSH_COMMAND": "/bin/false"}
    try:
        result = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c", "protocol.allow=never",
                                 "-c", "credential.helper=", "-c", "core.fsmonitor=false", "-c", "gc.auto=0",
                                 "-C", str(repository_root), "rev-parse", "--verify", "HEAD^{commit}"],
                                env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise checker.BuildError("entry_build_source_git_unavailable") from exc
    _need(result.returncode == 0 and len(result.stdout) == 41 and result.stdout.endswith(b"\n"),
          "entry_build_source_git_unavailable")
    return result.stdout[:-1].decode("ascii")


def _context(source_commit, github):
    if not github:
        return {"kind": "local_example"}
    required = {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REF": "refs/heads/main",
                "GITHUB_SHA": source_commit, "GITHUB_WORKFLOW_SHA": source_commit,
                "GITHUB_RUN_ATTEMPT": "1", "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@refs/heads/main"}
    _need(all(os.environ.get(key) == value for key, value in required.items()), "entry_build_github_context_mismatch")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    _need(re.fullmatch(r"[1-9][0-9]{0,18}", run_id) is not None and int(run_id) < 2**63,
          "entry_build_github_run_invalid")
    return {"kind": "github_workflow", "repository": REPOSITORY, "workflow_path": WORKFLOW,
            "source_commit": source_commit, "workflow_sha": source_commit, "ref": "refs/heads/main",
            "run_id": int(run_id), "run_attempt": 1, "event_name": "workflow_dispatch"}


class _Evidence:
    """Own one new evidence directory and verify every retained inode and byte."""
    def __init__(self, path):
        self.path = Path(path)
        self.directory = acquisition._Directory(self.path)
        self.fd = self.directory.fd
        self.root_identity = (os.fstat(self.fd).st_dev, os.fstat(self.fd).st_ino)
        self.directories = {}
        self.directory_identities = {}
        self.expected = {}
        self.identities = {}

    def _parent(self, name):
        parts = name.split("/")
        _need(runtime.observation.path_ok(name) and len(parts) in {1, 2}, "entry_build_evidence_path_invalid")
        if len(parts) == 1:
            return self.fd, parts[0]
        _need(parts[0] in self.directories, "entry_build_evidence_directory_missing")
        return self.directories[parts[0]], parts[1]

    def mkdir(self, name):
        _need(name in {"build-1", "build-2"} and name not in self.directories, "entry_build_directory_invalid")
        os.mkdir(name, 0o700, dir_fd=self.fd)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.fd)
        self.directories[name] = fd
        info = os.fstat(fd)
        self.directory_identities[name] = (info.st_dev, info.st_ino)
        os.fsync(self.fd)
        return fd

    def create(self, name):
        parent, leaf = self._parent(name)
        fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        info = os.fstat(fd)
        self.expected[name] = b""
        self.identities[name] = (info.st_dev, info.st_ino)
        os.fsync(parent)
        return fd

    def append(self, name, fd, raw):
        try:
            acquisition._Directory.append(fd, raw)
        except Exception as exc:
            raise PreservationError("entry_build_preservation_failed") from exc
        self.expected[name] += raw

    def write(self, name, raw):
        fd = self.create(name)
        try:
            self.append(name, fd, raw)
        finally:
            os.close(fd)

    def read(self, name, maximum, *, sync=False):
        parent, leaf = self._parent(name)
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        try:
            before = os.fstat(fd)
            raw = runtime._read_fd(fd, maximum)
            if sync:
                os.fsync(fd)
            _need(runtime._identity(before) == runtime._identity(os.fstat(fd)), "entry_build_evidence_changed")
            return raw, (before.st_dev, before.st_ino)
        finally:
            os.close(fd)

    def adopt_entry(self, name):
        _need(name not in self.expected, "entry_build_entry_reused")
        raw, identity = self.read(name, checker.LIMITS["entry_bytes"], sync=True)
        containment.validate_entry(raw)
        self.expected[name] = raw
        self.identities[name] = identity
        parent, _leaf = self._parent(name)
        os.fsync(parent)
        return raw

    def verify_file(self, name):
        raw, identity = self.read(name, max(len(self.expected[name]), 1))
        _need(raw == self.expected[name] and identity == self.identities[name], "entry_build_evidence_mismatch")

    def remove_consolidated(self, name):
        """Remove only a successfully preserved, incorporated internal file."""
        self.verify_file(name)
        parent, leaf = self._parent(name)
        os.unlink(leaf, dir_fd=parent)
        os.fsync(parent)
        del self.expected[name]
        del self.identities[name]

    def verify(self):
        runtime._same_destination(self.fd, self.path)
        before = os.fstat(self.fd)
        _need((before.st_dev, before.st_ino) == self.root_identity
              and stat.S_IMODE(before.st_mode) == 0o700, "entry_build_evidence_root_changed")
        root_names = {name for name in self.expected if "/" not in name} | set(self.directories)
        with os.scandir(self.fd) as entries:
            _need({entry.name for entry in entries} == root_names, "entry_build_evidence_inventory_mismatch")
        for name, fd in self.directories.items():
            info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            _need(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
                  and (info.st_dev, info.st_ino) == self.directory_identities[name]
                  and (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == self.directory_identities[name],
                  "entry_build_evidence_directory_changed")
            expected = {path.split("/", 1)[1] for path in self.expected if path.startswith(name + "/")}
            with os.scandir(fd) as entries:
                _need({entry.name for entry in entries} == expected, "entry_build_evidence_inventory_mismatch")
        for name in self.expected:
            self.verify_file(name)
        _need(runtime._identity(before) == runtime._identity(os.fstat(self.fd)), "entry_build_evidence_root_changed")

    def publish(self, raw):
        self.write("record.pending", raw)
        self.verify()
        os.link("record.pending", "record.json", src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False)
        os.unlink("record.pending", dir_fd=self.fd)
        self.expected["record.json"] = self.expected.pop("record.pending")
        self.identities["record.json"] = self.identities.pop("record.pending")
        os.fsync(self.fd)

    def close(self):
        failure = None
        for fd in self.directories.values():
            try:
                os.close(fd)
            except OSError as exc:
                if failure is None:
                    failure = exc
        self.directories.clear()
        if failure is not None:
            raise failure
        self.directory.close()


def _mark_incomplete(evidence, source_commit, request_sha, code):
    try:
        fd = evidence.directory.fd
        _need(fd is not None and (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == evidence.root_identity,
              "entry_build_evidence_root_changed")
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,95}", code) is None:
            code = "entry_build_operation_failed"
        evidence.write("attempt.incomplete.json", checker.canonical({
            "format": "required_gate_idempotence_entry_build_incomplete_v0", "status": "incomplete",
            "source_commit": source_commit, "request_sha256": request_sha, "error_code": code,
            **checker.BOUNDARY}))
    except Exception:
        pass


def _run(argv, *, cwd, seconds, sink):
    """Bound one process and durably retain readable prefixes before returning."""
    caps = {name: checker.LIMITS[name + "_bytes"] for name in ("stdout", "stderr")}
    data = {name: bytearray() for name in caps}
    flags = {"timed_out": False, "stdout_overflow": False, "stderr_overflow": False}
    started = time.monotonic_ns()
    deadline = time.monotonic() + seconds
    child, failure, sink_failed = None, None, False

    def retain(name, raw):
        nonlocal sink_failed
        try:
            sink(name, raw)
        except Exception as exc:
            sink_failed = True
            raise PreservationError("entry_build_preservation_failed") from exc
        data[name].extend(raw)

    with ExitStack() as stack:
        if type(cwd) is int:
            working_directory = "/proc/self/fd/" + str(cwd)
            pass_fds = (cwd,)
        else:
            working_directory, pass_fds = str(cwd), ()
        try:
            child = subprocess.Popen(argv, cwd=working_directory, env=dict(checker.ENVIRONMENT),
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True, pass_fds=pass_fds, start_new_session=True, umask=0o077)
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
                    flags["timed_out"] = True
                    failure = "entry_build_process_timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    name = key.data
                    available = caps[name] - len(data[name])
                    try:
                        raw = os.read(key.fd, min(65536, available + 1))
                    except BlockingIOError:
                        continue
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    if raw[:available]:
                        retain(name, raw[:available])
                    if len(raw) > available:
                        flags[name + "_overflow"] = True
                        failure = "entry_build_" + name + "_limit"
                        break
                if failure:
                    break
            if failure is None:
                # Keep an exited leader waitable until its owned group is
                # stopped. Reaping it here could strand compiler descendants
                # with closed streams, or allow the numeric group ID to reuse.
                while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        flags["timed_out"] = True
                        failure = "entry_build_process_timeout"
                        break
                    time.sleep(min(remaining, 0.01))
        except (OSError, ValueError) as exc:
            failure = "entry_build_spawn_failed" if child is None else "entry_build_process_operation_failed"
        finally:
            if child is not None:
                if child.returncode is None:
                    try:
                        # An external reaper must not turn a stale PID into a
                        # signal target. WNOWAIT never consumes our own leader.
                        os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    except ChildProcessError:
                        failure = "entry_build_process_reap_failed"
                    else:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        child.kill()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    failure = "entry_build_process_reap_failed"
                if failure is not None and not sink_failed:
                    try:
                        for name in caps:
                            stream = getattr(child, name)
                            os.set_blocking(stream.fileno(), False)
                            while len(data[name]) < caps[name]:
                                try:
                                    raw = os.read(stream.fileno(), min(65536, caps[name] - len(data[name])))
                                except BlockingIOError:
                                    break
                                if not raw:
                                    break
                                retain(name, raw)
                    except (OSError, ValueError) as exc:
                        raise PreservationError("entry_build_preservation_failed") from exc
    if failure is None and child is not None and child.returncode != 0:
        failure = "entry_build_process_nonzero"
    elapsed = time.monotonic_ns() - started
    if elapsed > seconds * 1_000_000_000 and failure is None:
        flags["timed_out"] = True
        failure = "entry_build_process_timeout"
    observed = {"pid": None if child is None else child.pid,
                "exit_code": None if child is None else child.returncode,
                "elapsed_ns": elapsed, **flags}
    return observed, failure, {name: bytes(raw) for name, raw in data.items()}


def _capture(evidence, prefix, argv, *, cwd, seconds):
    names = {stream: prefix + "." + stream + ".bin" for stream in ("stdout", "stderr")}
    with ExitStack() as stack:
        fds = {}
        for stream, name in names.items():
            fds[stream] = evidence.create(name)
            stack.callback(os.close, fds[stream])
        result = _run(argv, cwd=cwd, seconds=seconds,
                      sink=lambda stream, raw: evidence.append(names[stream], fds[stream], raw))
    observed, failure, raw = result
    _need(all(raw[stream] == evidence.expected[name] for stream, name in names.items()),
          "entry_build_capture_mismatch")
    return observed, failure, raw, names


def _query_lookup(raw, name):
    try:
        value = raw.decode("ascii")
    except UnicodeError as exc:
        raise checker.BuildError("entry_build_tool_query_invalid") from exc
    _need(value.endswith("\n") and value.count("\n") == 1 and len(value) <= 4096
          and not any(char.isspace() for char in value[:-1]), "entry_build_tool_query_invalid")
    value = value[:-1]
    if value.startswith("/"):
        path = Path(value)
        _need(str(path) == os.path.normpath(value), "entry_build_tool_query_invalid")
        return path
    _need(value == name, "entry_build_tool_query_invalid")
    for directory in ("/usr/bin", "/bin"):
        path = Path(directory) / name
        if path.exists():
            return path
    raise checker.BuildError("entry_build_tool_query_missing")


def _toolchain(evidence, label, compiler_descriptor, compiler_identity):
    compiler = compiler_descriptor["path"]
    components = [{"name": "compiler", "lookup_path": compiler, **compiler_descriptor}]
    identities = {"compiler": compiler_identity}
    captured = []
    observations = {}
    for name, option in (("version", "--version"), *((name, "-print-prog-name=" + name) for name in TOOL_NAMES)):
        current, identity = _tool(compiler)
        _need({key: current[key] for key in ("path", "sha256", "size_bytes")} == compiler_descriptor
              and identity == compiler_identity, "entry_build_compiler_changed")
        argv = [compiler, option]
        process, failure, raw, names = _capture(evidence, "query-" + label + "-" + name, argv,
                                               cwd=evidence.fd, seconds=checker.LIMITS["query_seconds"])
        captured.extend(names.values())
        _need(failure is None, failure or "entry_build_tool_query_failed")
        _need(raw["stdout"] and not raw["stderr"], "entry_build_tool_query_invalid")
        observations[name] = {"argv": argv, "stdout_b64": base64.b64encode(raw["stdout"]).decode("ascii"),
                              "stderr_b64": base64.b64encode(raw["stderr"]).decode("ascii"), "process": process}
        if name != "version":
            descriptor, identity = _tool(_query_lookup(raw["stdout"], name))
            components.append({"name": name, **descriptor})
            identities[name] = identity
    # Queries execute the compiler too. Close the observation interval after
    # the last query, including components observed earlier in this sequence.
    for row in components:
        descriptor, identity = _tool(row["lookup_path"])
        _need(descriptor == {key: value for key, value in row.items() if key != "name"}
              and identity == identities[row["name"]], "entry_build_toolchain_changed")
    value = {"format": "required_gate_idempotence_entry_toolchain_v0",
             "components": sorted(components, key=lambda row: row["name"]), "version": observations["version"],
             "queries": [{"name": name, **observations[name]} for name in TOOL_NAMES]}
    destination = "toolchain-" + label + ".json"
    evidence.write(destination, checker.canonical(value))
    evidence.verify_file(destination)
    # Only successfully incorporated query bytes are consolidated. Any earlier
    # failure leaves all query files in the incomplete prefix without cleanup.
    for name in captured:
        evidence.remove_consolidated(name)
    return value, identities


def _toolchain_projection(value):
    return {"components": value["components"],
            "version": {key: item for key, item in value["version"].items() if key != "process"},
            "queries": [{key: item for key, item in row.items() if key != "process"} for row in value["queries"]]}


def acquire_entry_build(*, repository_root: Path, source_commit: str, compiler: Path,
                        expected_compiler_sha256: str, output_directory: Path, github: bool = False) -> dict:
    """Acquire exactly two fixed entry builds; never execute their binaries."""
    _need(sys.platform == "linux" and platform.machine() == "x86_64", "entry_build_platform_unsupported")
    _need(type(source_commit) is str and HEX40.fullmatch(source_commit) is not None,
          "entry_build_source_commit_invalid")
    _need(type(expected_compiler_sha256) is str and HEX64.fullmatch(expected_compiler_sha256) is not None,
          "entry_build_compiler_digest_invalid")
    repository_root = safe._absolute(Path(repository_root))
    safe._Reader(repository_root)
    _need(_head(repository_root) == source_commit, "entry_build_checkout_head_mismatch")
    source, source_identity = _snapshot(repository_root / checker.ENTRY_SOURCE_PATH, checker.ENTRY_SOURCE_SIZE)
    installed, _ = _snapshot(ROOT / checker.ENTRY_SOURCE_PATH, checker.ENTRY_SOURCE_SIZE)
    selected = runtime.observation._git_blob(repository_root, source_commit, checker.ENTRY_SOURCE_PATH,
                                             checker.ENTRY_SOURCE_SIZE)
    _need(source == installed == selected and len(source) == checker.ENTRY_SOURCE_SIZE
          and checker.sha(source) == checker.ENTRY_SOURCE_SHA256, "entry_build_source_mismatch")
    compiler = Path(compiler)
    _need(compiler.is_absolute(), "entry_build_compiler_path_invalid")
    descriptor, compiler_identity = _tool(compiler)
    descriptor = {key: descriptor[key] for key in ("path", "sha256", "size_bytes")}
    _need(descriptor["sha256"] == expected_compiler_sha256, "entry_build_compiler_digest_mismatch")
    output_directory = safe._absolute(Path(output_directory))
    _need(not output_directory.is_relative_to(repository_root), "entry_build_output_inside_checkout")
    context = _context(source_commit, github)
    request = {"format": "required_gate_idempotence_entry_build_request_v0", "profile": checker.PROFILE,
               "source_commit": source_commit,
               "source": {"path": checker.ENTRY_SOURCE_PATH, **checker.binding(source)},
               "compiler": descriptor, "argv_template": [descriptor["path"], *checker.CC_FLAGS, "entry.c", "-o", "entry"],
               "environment": dict(checker.ENVIRONMENT), "limits": dict(checker.LIMITS),
               "context": context, **checker.BOUNDARY}
    request_raw = checker.canonical(request)
    request_sha = checker.sha(request_raw)
    checker.validate_request(request_raw, request_sha, source_commit)
    evidence = None
    try:
        evidence = _Evidence(output_directory)
        evidence.write("request.json", request_raw)
        evidence.write("source.c", source)
        before, before_identities = _toolchain(evidence, "before", descriptor, compiler_identity)
        entries = []
        for build_id in ("build-1", "build-2"):
            cwd = evidence.mkdir(build_id)
            evidence.write(build_id + "/entry.c", source)
            with ExitStack() as stack:
                fds = {}
                for name in ("stdout", "stderr"):
                    fds[name] = evidence.create(build_id + "/" + name + ".bin")
                    stack.callback(os.close, fds[name])
                process, failure, raw = _run(request["argv_template"], cwd=cwd, seconds=checker.LIMITS["build_seconds"],
                    sink=lambda name, data: evidence.append(build_id + "/" + name + ".bin", fds[name], data))
            _need(all(raw[name] == evidence.expected[build_id + "/" + name + ".bin"] for name in raw),
                  "entry_build_capture_mismatch")
            result = {"format": "required_gate_idempotence_entry_build_execution_v0", "build_id": build_id,
                      "working_directory": build_id, "argv": request["argv_template"],
                      "environment": dict(checker.ENVIRONMENT), "process": process,
                      "source": checker.binding(source), "stdout": checker.binding(raw["stdout"]),
                      "stderr": checker.binding(raw["stderr"])}
            if failure is not None:
                evidence.write(build_id + "/result.json", checker.canonical({**result, "error_code": failure}))
                raise checker.BuildError(failure)
            evidence.verify_file(build_id + "/entry.c")
            entry = evidence.adopt_entry(build_id + "/entry")
            entries.append(entry)
            result["entry"] = checker.binding(entry)
            evidence.write(build_id + "/result.json", checker.canonical(result))
        _need(entries[0] == entries[1], "entry_build_repeat_mismatch")
        after, after_identities = _toolchain(evidence, "after", descriptor, compiler_identity)
        _need(_toolchain_projection(before) == _toolchain_projection(after)
              and before_identities == after_identities, "entry_build_toolchain_changed")
        final_source, final_identity = _snapshot(repository_root / checker.ENTRY_SOURCE_PATH, checker.ENTRY_SOURCE_SIZE)
        _need(final_source == source and final_identity == source_identity and _head(repository_root) == source_commit,
              "entry_build_source_changed")
        _need(set(evidence.expected) == set(checker.FILES), "entry_build_evidence_inventory_mismatch")
        record = {"format": "required_gate_idempotence_entry_build_v0", "profile": checker.PROFILE,
                  "status": "completed", "source_commit": source_commit, "request_sha256": request_sha,
                  "files": [{"path": path, **checker.binding(evidence.expected[path])} for path in sorted(evidence.expected)],
                  "build_ids": ["build-1", "build-2"], "repeat_build_equal": True,
                  "entry_static_shape_verified": True, "toolchain_observations_stable": True, **checker.BOUNDARY}
        record_raw = checker.canonical(record)
        checker.check_payload({**evidence.expected, "record.json": record_raw}, expected_request_sha256=request_sha,
                              expected_record_sha256=checker.sha(record_raw), source_commit=source_commit)
        evidence.verify()
        evidence.publish(record_raw)
        return record
    except BaseException as exc:
        if evidence is not None:
            _mark_incomplete(evidence, source_commit, request_sha, getattr(exc, "code", "entry_build_operation_failed"))
        raise
    finally:
        if evidence is not None:
            try:
                evidence.close()
            except BaseException:
                # _Directory.close fsyncs before closing its descriptor. A late
                # sync failure must invalidate an already published record too.
                _mark_incomplete(evidence, source_commit, request_sha, "entry_build_preservation_failed")
                try:
                    fd = evidence.directory.fd
                    if fd is not None and (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == evidence.root_identity:
                        os.close(fd)
                        evidence.directory.fd = None
                except OSError:
                    pass
                raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("acquire",))
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args(argv)
    try:
        record = acquire_entry_build(repository_root=args.repository_root, source_commit=args.source_commit,
                                     compiler=args.compiler, expected_compiler_sha256=args.compiler_sha256,
                                     output_directory=args.output_directory, github=args.github)
        sys.stdout.buffer.write(checker.canonical(record))
        return 0
    except (checker.BuildError, PreservationError, containment.ContainmentError, runtime.CapsuleError,
            acquisition.AcquisitionError, runtime.observation.VerificationError, safe.ContractError,
            OSError, ValueError) as exc:
        code = getattr(exc, "code", "entry_build_operation_failed")
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,95}", code) is None:
            code = "entry_build_operation_failed"
        sys.stdout.buffer.write(checker.canonical({"format": "required_gate_idempotence_entry_build_error_v0",
                                                  "status": "rejected", "error_code": code, **checker.BOUNDARY}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
