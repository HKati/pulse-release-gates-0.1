#!/usr/bin/env python3
"""Preserve one separately authorized, selected task-guard qualification attempt.

Importing this adapter has no execution effect. Its native CLI is a disposable
observer: it must terminate if the unchanged qualifier cannot close its owned
tasks. An acknowledgement is an execution safeguard, not proof of owner identity.
An explicitly injected backend always remains scripted evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_attempt_v0 as checker
import check_required_gate_idempotence_containment_task_guard_selection_v0 as selection
import prepare_required_gate_idempotence_containment_task_guard_selection_v0 as preparer
import qualify_required_gate_idempotence_containment_task_guard_v0 as qualifier

ACKNOWLEDGEMENT = "QUALIFY_CONTAINMENT_TASK_GUARD_ONLY"
CONTROL_LIMIT = 131072
FILE_LIMITS = {
    "request.json": CONTROL_LIMIT, "attempt.json": CONTROL_LIMIT,
    "selection.json": 65536, "build_record.json": 2097152,
    "probe.elf": 262144, "policy.json": 65536,
    "qualification.json": 33554432,
}
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
EXIT_MARKER = "task_guard_native_requires_observer_exit"
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class AttemptError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ObserverExitRequired(AttemptError):
    """The caller must end this disposable observer, even if saving failed."""
    def __init__(self, record):
        self.record = record
        super().__init__("containment_guard_attempt_requires_observer_exit")


def need(condition, code):
    if not condition:
        raise AttemptError(code)


def failure_code(exc):
    code = getattr(exc, "code", None)
    if type(code) is str and _CODE.fullmatch(code):
        return code
    if isinstance(exc, OSError):
        return "containment_guard_attempt_os_error_" + str(max(0, min(exc.errno or 0, 4095)))
    return ("containment_guard_attempt_interrupted" if not isinstance(exc, Exception)
            else "containment_guard_attempt_failed")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid)


def _snapshot(info):
    return (*_identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class OwnedBundle:
    """Create-only, descriptor-owned fixed output set with a final commit record.

The attempt file is reserved empty. Every other file is written and closed
before any completed attempt can be published. A late failure invalidates only
the owned attempt inode, including an ambiguous close that already closed it.
"""
    def __init__(self, path):
        self.path = None
        self.parents, self.directory = [], None
        self.directory_info = None
        self.files, self.selected, self.contents = {}, {}, {}
        self.closed = False
        try:
            self.path, parent, self.parents = selection._parent(path)
            os.mkdir(self.path.name, 0o700, dir_fd=parent)
            before = os.stat(self.path.name, dir_fd=parent, follow_symlinks=False)
            need(stat.S_ISDIR(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o700
                 and before.st_uid == os.geteuid(), "containment_guard_attempt_directory_identity")
            self.directory = os.open(self.path.name, DIRECTORY_FLAGS, dir_fd=parent)
            self.directory_info = os.fstat(self.directory)
            need(_identity(self.directory_info) == _identity(before),
                 "containment_guard_attempt_directory_replaced")
            for name in FILE_LIMITS:
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                             os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.directory)
                self.files[name] = fd
                info = os.fstat(fd)
                self.selected[name] = info
                need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                     and stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.geteuid(),
                     "containment_guard_attempt_output_identity")
                self.contents[name] = b""
            self.check()
        except BaseException:
            self.invalidate_attempt()
            try:
                self.close()
            except BaseException:
                pass
            raise

    def _public_directory(self):
        path, parent, opened = selection._parent(self.path)
        try:
            public = os.open(path.name, DIRECTORY_FLAGS, dir_fd=parent)
            opened.append(public)
            need(_identity(os.fstat(public)) == _identity(self.directory_info),
                 "containment_guard_attempt_public_directory_changed")
            return public, opened
        except BaseException:
            for fd in reversed(opened):
                os.close(fd)
            raise

    def _check_file(self, directory, name):
        fd = os.open(name, READ_FLAGS, dir_fd=directory)
        try:
            before = os.fstat(fd)
            need(_identity(before) == _identity(self.selected[name])
                 and before.st_size == len(self.contents[name]),
                 "containment_guard_attempt_file_replaced")
            data = bytearray()
            while len(data) <= FILE_LIMITS[name]:
                block = os.read(fd, min(65536, FILE_LIMITS[name] + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
            need(bytes(data) == self.contents[name]
                 and _snapshot(os.fstat(fd)) == _snapshot(before)
                 and _snapshot(os.stat(name, dir_fd=directory, follow_symlinks=False)) == _snapshot(before),
                 "containment_guard_attempt_file_changed")
        finally:
            os.close(fd)

    def check(self):
        need(self.directory_info is not None, "containment_guard_attempt_bundle_unreserved")
        if not self.closed:
            need(self.directory is not None
                 and _identity(os.fstat(self.directory)) == _identity(self.directory_info),
                 "containment_guard_attempt_directory_changed")
        public, opened = self._public_directory()
        try:
            need(set(os.listdir(public)) == set(self.contents),
                 "containment_guard_attempt_bundle_members")
            for name in self.contents:
                self._check_file(public, name)
        finally:
            for fd in reversed(opened):
                os.close(fd)

    def publish(self, name, data):
        need(name in self.files and self.files[name] is not None
             and type(data) is bytes and 0 < len(data) <= FILE_LIMITS[name],
             "containment_guard_attempt_output_extent")
        self.check()
        fd = self.files[name]
        need(self.contents[name] == b"" and os.fstat(fd).st_size == 0,
             "containment_guard_attempt_output_already_written")
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            need(count > 0, "containment_guard_attempt_short_write")
            view = view[count:]
        os.fsync(fd)
        self.contents[name] = data
        self.check()
        os.fsync(self.directory)
        self.check()

    def close_file(self, name):
        fd = self.files[name]
        if fd is not None:
            self.files[name] = None
            try:
                os.close(fd)
            except BaseException:
                self.invalidate_attempt()
                raise

    def omit_qualification(self):
        name = "qualification.json"
        need(self.contents[name] == b"", "containment_guard_attempt_qualification_already_written")
        self.check()
        current = os.stat(name, dir_fd=self.directory, follow_symlinks=False)
        need(_identity(current) == _identity(self.selected[name]),
             "containment_guard_attempt_qualification_replaced")
        os.unlink(name, dir_fd=self.directory)
        del self.contents[name]
        self.close_file(name)
        os.fsync(self.directory)
        self.check()

    def invalidate_attempt(self):
        """Never truncate a replacement or caller-owned inode."""
        if self.path is None or "attempt.json" not in self.selected:
            return
        selected = self.selected["attempt.json"]
        identity = selected.st_dev, selected.st_ino
        fd = self.files.get("attempt.json")
        if fd is not None:
            try:
                current = os.fstat(fd)
                if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity:
                    os.ftruncate(fd, 0)
                    os.fsync(fd)
                    return
            except BaseException:
                pass
        # close() can consume the file descriptor and then raise. The public
        # directory may also have been renamed/replaced. Its retained owned
        # directory handle still reaches our original inode in that case.
        reopened = None
        if self.directory is not None:
            try:
                need(_identity(os.fstat(self.directory)) == _identity(self.directory_info),
                     "containment_guard_attempt_invalidation_directory_changed")
                reopened = os.open("attempt.json", os.O_WRONLY | os.O_CLOEXEC |
                                   os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.directory)
                current = os.fstat(reopened)
                if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity:
                    os.ftruncate(reopened, 0)
                    os.fsync(reopened)
                    return
            except BaseException:
                pass
            finally:
                if reopened is not None:
                    try:
                        os.close(reopened)
                    except BaseException:
                        pass
        try:
            selection._invalidate_owned_output(self.path / "attempt.json",
                selected)
        except BaseException:
            pass

    def close(self):
        if self.closed:
            return
        errors = []
        # Keep the completion inode open until all other owned outputs close.
        names = [name for name in self.files if name != "attempt.json"] + ["attempt.json"]
        for name in names:
            if name not in self.files:
                continue
            try:
                self.close_file(name)
            except BaseException as exc:
                errors.append(exc)
        descriptors = ([self.directory] if self.directory is not None else []) + list(reversed(self.parents))
        for fd in descriptors:
            try:
                os.close(fd)
            except BaseException as exc:
                errors.append(exc)
                self.invalidate_attempt()
        self.directory, self.parents, self.closed = None, [], True
        if errors:
            self.invalidate_attempt()
            raise errors[0]


def _environment(reader):
    value = reader()
    selection.raw.validate_environment(value)
    # Freeze a substituted reader's return before any later callback can reuse it.
    return json.loads(checker.canonical(value))


def _unresolved(value):
    if type(value) is not dict:
        return False
    failures = value.get("cleanup_failures")
    if type(failures) is list and EXIT_MARKER in failures:
        return True
    cases = value.get("cases")
    if type(cases) is not list:
        return False
    return any(type(case) is dict and bool(case.get("unresolved_tasks"))
               for case in cases)


def _incomplete(record, exc, *, cleanup=False):
    code = failure_code(exc)
    record["status"] = "incomplete"
    if record["failure"] is None:
        record["failure"] = code
    if cleanup and code not in record["cleanup_failures"]:
        record["cleanup_failures"].append(code)


def attempt(*, selection_bytes, expected_selection_sha256, build_record_bytes,
            expected_build_record_sha256, probe_bytes, expected_probe_sha256,
            policy_bytes, accepted_policy_sha256, acknowledgement, output,
            backend=None, environment_reader=None, request_id=None):
    """Preserve zero or one qualifier invocation; never retry a failed prefix.

Failures after reservation return an incomplete record and retain the available
bounded files. Invalid request prefixes remain unverified. ObserverExitRequired
is different: its record must be preserved if possible and the observer must end.
The one-call limit is per invocation/output set, not global selection consumption.
"""
    need(acknowledgement == ACKNOWLEDGEMENT, "containment_guard_attempt_acknowledgement")
    need(environment_reader is None or backend is not None,
         "containment_guard_attempt_reader_requires_scripted_backend")
    reader = preparer.read_environment if environment_reader is None else environment_reader
    need(callable(reader), "containment_guard_attempt_environment_reader")
    mode = "native" if backend is None else "scripted"
    inputs = dict(selection_bytes=selection_bytes,
        expected_selection_sha256=expected_selection_sha256,
        build_record_bytes=build_record_bytes,
        expected_build_record_sha256=expected_build_record_sha256,
        probe_bytes=probe_bytes, expected_probe_sha256=expected_probe_sha256,
        policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256)
    request = checker.derive_request(**inputs,
        request_id=os.urandom(16).hex() if request_id is None else request_id,
        execution_mode=mode)
    request_bytes = checker.canonical(request)
    request_sha = checker.binding(request_bytes)["sha256"]
    destination = OwnedBundle(output)
    record = {"record_type": checker.ATTEMPT_TYPE, "profile": checker.PROFILE,
        "request": checker.binding(request_bytes), "status": "incomplete",
        "execution_mode": mode, "invocation_count": 0, "preflight_verified": False,
        "environment_before": None, "environment_after": None,
        "sources_before": [], "sources_after": [], "qualification": None,
        "qualification_verification": "not_available", "observer_exit_required": False,
        "failure": None, "cleanup_failures": [], "boundary": dict(checker.BOUNDARY)}
    qualification_bytes = None
    fatal_exit = False
    try:
        for name, data in (("selection.json", selection_bytes),
                           ("build_record.json", build_record_bytes),
                           ("probe.elf", probe_bytes), ("policy.json", policy_bytes),
                           ("request.json", request_bytes)):
            destination.publish(name, data)
            destination.close_file(name)
        checker.verify_request(request_bytes=request_bytes,
            expected_request_sha256=request_sha, **inputs)
        selected = selection.parse(selection_bytes, 65536)
        record["environment_before"] = _environment(reader)
        need(checker.canonical(record["environment_before"]) == checker.canonical(selected["environment"]),
             "containment_guard_attempt_context_mismatch")
        record["sources_before"] = checker.source_inventory()
        need(record["sources_before"] == request["sources"],
             "containment_guard_attempt_sources_before_changed")
        destination.check()
        need(checker.source_inventory() == request["sources"],
             "containment_guard_attempt_sources_before_invocation_changed")
        record["preflight_verified"] = True
        # Count immediately before the only call; exceptions never trigger retry.
        record["invocation_count"] = 1
        try:
            value = qualifier.qualify(probe_bytes=probe_bytes,
                expected_probe_sha256=expected_probe_sha256,
                expected_environment_sha256=selected["bindings"]["environment"]["sha256"],
                acknowledgement=acknowledgement, backend=backend)
        except qualifier.ObserverExitRequired as exc:
            value, fatal_exit = exc.record, True
        fatal_exit = fatal_exit or _unresolved(value)
        record["observer_exit_required"] = fatal_exit
        qualification_bytes = selection.raw.canonical(value)
        need(0 < len(qualification_bytes) <= FILE_LIMITS["qualification.json"],
             "containment_guard_attempt_qualification_extent")
        record["qualification"] = checker.binding(qualification_bytes)
        record["qualification_verification"] = "not_checked"
        destination.publish("qualification.json", qualification_bytes)
        destination.close_file("qualification.json")
        if fatal_exit:
            raise AttemptError("containment_guard_attempt_requires_observer_exit")
        expected_origin = "native_owned_probe" if mode == "native" else "scripted_test_backend"
        if type(value) is not dict or value.get("evidence_origin") != expected_origin:
            record["qualification_verification"] = "rejected"
            raise AttemptError("containment_guard_attempt_qualification_origin")
        try:
            raw_report = selection.raw.verify_record(record_bytes=qualification_bytes,
                expected_record_sha256=record["qualification"]["sha256"],
                expected_probe_sha256=expected_probe_sha256,
                expected_environment_sha256=selected["bindings"]["environment"]["sha256"])
        except Exception:
            record["qualification_verification"] = "rejected"
            raise
        record["qualification_verification"] = (
            "completed" if raw_report["complete_guard_probe_sequence_verified"] else "incomplete")
        need(raw_report["complete_guard_probe_sequence_verified"],
             "containment_guard_attempt_qualification_incomplete")
        record["environment_after"] = _environment(reader)
        need(checker.canonical(record["environment_after"]) == checker.canonical(record["environment_before"]),
             "containment_guard_attempt_context_changed")
        record["sources_after"] = checker.source_inventory()
        need(record["sources_after"] == request["sources"],
             "containment_guard_attempt_sources_after_changed")
        record["status"] = "completed"
        candidate = checker.canonical(record)
        report = checker.verify_attempt(attempt_bytes=candidate,
            expected_attempt_sha256=checker.binding(candidate)["sha256"],
            request_bytes=request_bytes, expected_request_sha256=request_sha,
            qualification_bytes=qualification_bytes, **inputs)
        need(report["selected_attempt_verified"], "containment_guard_attempt_replay_incomplete")
        need(checker.source_inventory() == request["sources"],
             "containment_guard_attempt_sources_before_publication_changed")
        destination.check()
    except BaseException as exc:
        _incomplete(record, exc)
    finally:
        try:
            if qualification_bytes is None:
                destination.omit_qualification()
            # The final attempt is the sole completion commit point. Every
            # immutable input and raw-record descriptor closes before it.
            for name in tuple(destination.files):
                if name != "attempt.json":
                    destination.close_file(name)
            destination.publish("attempt.json", checker.canonical(record))
            destination.check()
        except BaseException as exc:
            _incomplete(record, exc, cleanup=True)
            destination.invalidate_attempt()
        finally:
            try:
                destination.close()
                destination.check()
            except BaseException as exc:
                _incomplete(record, exc, cleanup=True)
                destination.invalidate_attempt()
            finally:
                if fatal_exit:
                    record["observer_exit_required"] = True
                    raise ObserverExitRequired(record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--expected-selection-sha256", required=True)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--expected-build-record-sha256", required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--expected-probe-sha256", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--accepted-policy-sha256", required=True)
    parser.add_argument("--acknowledgement", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    need(args.acknowledgement == ACKNOWLEDGEMENT, "containment_guard_attempt_acknowledgement")
    fatal_exit = False
    try:
        try:
            record = attempt(
                selection_bytes=selection.read_file(args.selection, FILE_LIMITS["selection.json"]),
                expected_selection_sha256=args.expected_selection_sha256,
                build_record_bytes=selection.read_file(args.build_record, FILE_LIMITS["build_record.json"]),
                expected_build_record_sha256=args.expected_build_record_sha256,
                probe_bytes=selection.read_file(args.probe, FILE_LIMITS["probe.elf"]),
                expected_probe_sha256=args.expected_probe_sha256,
                policy_bytes=selection.read_file(args.policy, FILE_LIMITS["policy.json"]),
                accepted_policy_sha256=args.accepted_policy_sha256,
                acknowledgement=args.acknowledgement, output=args.out)
        except ObserverExitRequired as exc:
            record, fatal_exit = exc.record, True
        return 0 if record["status"] == "completed" else 1
    finally:
        if fatal_exit:
            # Required even if saving/closing failed: EXITKILL activates when
            # this disposable observer actually exits. Missing cleanup remains
            # missing evidence; termination is never a completion claim.
            os._exit(1)


if __name__ == "__main__":
    raise SystemExit(main())
