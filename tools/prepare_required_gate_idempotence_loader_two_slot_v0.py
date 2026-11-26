#!/usr/bin/env python3
"""Prepare a context-bound request or explicitly attempt one fixed probe.

Preparation reads context and implementation bytes only.  The ``attempt``
command is a separate execution entry point: its exact acknowledgement permits
one invocation of the unchanged bounded two-slot producer.  It never invokes
the original launcher, dispatches a workflow, or supplies execution authority.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_loader_two_slot_attempt_v0 as checker


ACKNOWLEDGEMENT = checker.ACKNOWLEDGEMENT
DIRECTORY_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
ROSTER = frozenset(("request.json", "qualification.json", "attempt.json"))


class AttemptError(ValueError):
    """A bounded public failure code without raw exception text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise AttemptError(code)


def _failure(error):
    code = getattr(error, "code", None)
    if type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code):
        return code
    if isinstance(error, OSError):
        return "two_slot_attempt_os_error_" + str(max(0, min(error.errno or 0, 4095)))
    return ("two_slot_attempt_interrupted" if not isinstance(error, Exception)
            else "two_slot_attempt_failed")


def _file_identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid)


def _read_fd(fd, limit, *, allow_empty=False):
    before = os.fstat(fd)
    _need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit,
          "two_slot_attempt_input_extent")
    os.lseek(fd, 0, os.SEEK_SET)
    result = bytearray()
    while True:
        block = os.read(fd, min(65536, limit + 1 - len(result)))
        if not block:
            break
        result.extend(block)
        _need(len(result) <= limit, "two_slot_attempt_input_extent")
    after = os.fstat(fd)
    _need(_file_identity(before) == _file_identity(after)
          and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
          == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
          "two_slot_attempt_input_changed")
    _need(allow_empty or len(result) > 0, "two_slot_attempt_input_empty")
    return bytes(result)


def _open_parent(path):
    """Pin every directory component and reject symlinks and parent traversal."""
    path = Path(path)
    _need(".." not in path.parts and "\x00" not in str(path),
          "two_slot_attempt_path")
    if not path.is_absolute():
        path = Path.cwd() / path
    _need(len(path.parts) > 1 and path.name not in ("", ".", ".."),
          "two_slot_attempt_path")
    fd = os.open(path.anchor, DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = following
        return path, fd, path.name
    except BaseException:
        os.close(fd)
        raise


def _read_input(path, limit):
    _path, parent, name = _open_parent(path)
    fd = None
    try:
        fd = os.open(name, READ_FLAGS, dir_fd=parent)
        return _read_fd(fd, limit)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def read_context():
    """Read a fresh selection without importing or constructing a native backend."""
    _need(sys.platform == "linux" and os.uname().machine == "x86_64",
          "two_slot_attempt_platform")
    proc = os.open("/proc/" + str(os.getpid()), DIRECTORY_FLAGS)
    try:
        names = {}
        for name in checker.raw.NAMESPACE_NAMES:
            try:
                names[name] = os.readlink("ns/" + name, dir_fd=proc)
            except FileNotFoundError:
                if name not in ("time", "time_for_children"):
                    raise
                names[name] = None
        # The kernel's exe link is the one deliberately followed input.  Its
        # opened regular-file identity is checked around the complete read.
        executable = os.open("exe", os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK,
                             dir_fd=proc)
        try:
            executable_bytes = _read_fd(executable, 64 * 1024 * 1024)
        finally:
            os.close(executable)
        boot = _read_input("/proc/sys/kernel/random/boot_id", 128)
        uname = os.uname()
        value = {
            "uname": {key: getattr(uname, key)
                      for key in ("sysname", "release", "version", "machine")},
            "boot_id": boot.decode("ascii").strip(),
            "observer": checker.binding(executable_bytes), "namespaces": names,
        }
        checker.raw.validate_context(value)
        return value
    finally:
        os.close(proc)


def _publish(fd, raw):
    """Publish exact bytes to an exclusively reserved, empty regular file."""
    _need(type(raw) is bytes and len(raw) > 0, "two_slot_attempt_output_bytes")
    _need(os.fstat(fd).st_size == 0, "two_slot_attempt_output_not_empty")
    pending = memoryview(raw)
    while pending:
        written = os.write(fd, pending)
        _need(type(written) is int and written > 0, "two_slot_attempt_output_write")
        pending = pending[written:]
    os.fsync(fd)
    _need(os.fstat(fd).st_size == len(raw), "two_slot_attempt_output_extent")


def _invalidate(fd):
    """Invalidate only this call's pinned inode; never touch a replacement path."""
    try:
        os.ftruncate(fd, 0)
        os.fsync(fd)
    except OSError:
        pass


def _invalidate_owned(fd, selected, path):
    """Also handle a close which raised after consuming its descriptor."""
    try:
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) == (selected.st_dev, selected.st_ino):
            _invalidate(fd)
            return
    except OSError:
        pass
    parent = reopened = None
    try:
        _path, parent, name = _open_parent(path)
        reopened = os.open(name, os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
                           | os.O_NONBLOCK, dir_fd=parent)
        # Reopening is only a way to reacquire the inode already owned by this
        # call.  A substituted path is never truncated, removed or repaired.
        current = os.fstat(reopened)
        if (current.st_dev, current.st_ino) == (selected.st_dev, selected.st_ino):
            _invalidate(reopened)
    except (OSError, ValueError):
        pass
    finally:
        for item in (reopened, parent):
            if item is not None:
                try:
                    os.close(item)
                except OSError:
                    pass


def _close_all(descriptors, *, final=None):
    """Close the receipt last so any earlier close failure can invalidate it."""
    failure = None
    for fd in descriptors:
        if fd is None:
            continue
        try:
            os.close(fd)
        except BaseException as error:
            failure = failure or error
            if final is not None:
                _invalidate_owned(*final)
    if final is not None:
        fd, selected, path = final
        try:
            os.close(fd)
        except BaseException as error:
            failure = failure or error
            _invalidate_owned(fd, selected, path)
    if failure is not None:
        raise failure


def _reserved_file(parent, name):
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
                 | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
    try:
        selected = os.fstat(fd)
        _need(stat.S_ISREG(selected.st_mode) and selected.st_nlink == 1
              and stat.S_IMODE(selected.st_mode) == 0o600
              and selected.st_uid == os.geteuid(), "two_slot_attempt_output_identity")
        return fd, selected
    except BaseException:
        os.close(fd)
        raise


def _check_file(parent, name, fd, selected):
    current = os.stat(name, dir_fd=parent, follow_symlinks=False)
    _need(_file_identity(current) == _file_identity(selected)
          and _file_identity(os.fstat(fd)) == _file_identity(selected),
          "two_slot_attempt_output_replaced")


def _check_content(fd, expected):
    """An unchanged inode alone cannot establish exact preserved bytes."""
    _need(_read_fd(fd, len(expected), allow_empty=True) == expected,
          "two_slot_attempt_output_changed")


def _check_parent(path, parent):
    _path, current, _name = _open_parent(path)
    try:
        before, after = os.fstat(parent), os.fstat(current)
        _need((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
              "two_slot_attempt_parent_replaced")
    finally:
        os.close(current)


def prepare(*, output, context_reader=None, request_id=None):
    """Write a closed pre-execution request and return its exact selected bytes."""
    reader = read_context if context_reader is None else context_reader
    context = reader()
    checker.raw.validate_context(context)
    request = checker.request_value(context, request_id=request_id)
    encoded = checker.canonical(request)
    _need(len(encoded) <= checker.MAX_CONTROL_BYTES, "two_slot_attempt_request_extent")
    checker.verify_request(request_bytes=encoded,
                           expected_request_sha256=checker.binding(encoded)["sha256"])
    _need(checker.canonical(reader()) == checker.canonical(context),
          "two_slot_attempt_context_changed")
    path, parent, name = _open_parent(output)
    fd = None
    try:
        fd, selected = _reserved_file(parent, name)
        _check_parent(path, parent)
        _check_file(parent, name, fd, selected)
        _check_content(fd, b"")
        _publish(fd, encoded)
        _check_file(parent, name, fd, selected)
        _check_content(fd, encoded)
        os.fsync(parent)
        _check_parent(path, parent)
        _check_file(parent, name, fd, selected)
        _check_content(fd, encoded)
        return encoded
    except BaseException:
        if fd is not None:
            _invalidate(fd)
        raise
    finally:
        _close_all([parent], final=None if fd is None else (fd, selected, path))


def attempt(*, request_bytes, expected_request_sha256, acknowledgement,
            output_directory, backend=None, context_reader=None):
    """Reserve outputs, admit the selected context, and invoke the producer once.

    Any explicitly supplied backend selects scripted evidence.  Ordinary
    admission or producer failures are preserved in an incomplete receipt.
    An output identity or publication failure invalidates the owned receipt
    inode and raises; no completed receipt survives that failure.
    """
    _need(type(acknowledgement) is str and acknowledgement == ACKNOWLEDGEMENT,
          "two_slot_attempt_acknowledgement")
    request = checker.verify_request(request_bytes=request_bytes,
                                     expected_request_sha256=expected_request_sha256)
    selected_schema = checker.read_regular(checker.ROOT / checker.ATTEMPT_SCHEMA_PATH,
                                           checker.MAX_SOURCE_BYTES)
    schema_selection = next(row for row in request["sources"]
                            if row["path"] == checker.ATTEMPT_SCHEMA_PATH)
    _need(checker.binding(selected_schema)
          == {key: schema_selection[key] for key in ("size_bytes", "sha256")},
          "two_slot_attempt_schema_changed")
    reader = read_context if context_reader is None else context_reader
    path, parent, name = _open_parent(output_directory)
    directory = None
    files = {}
    expected_files = {leaf: b"" for leaf in ROSTER}
    try:
        # mkdir is exclusive.  Reusing an old output directory cannot execute
        # even a scripted backend, and this function never retries the probe.
        os.mkdir(name, mode=0o700, dir_fd=parent)
        directory = os.open(name, DIRECTORY_FLAGS, dir_fd=parent)
        selected_directory = os.fstat(directory)
        _need(stat.S_IMODE(selected_directory.st_mode) == 0o700
              and selected_directory.st_uid == os.geteuid(),
              "two_slot_attempt_directory_identity")
        for leaf in sorted(ROSTER):
            files[leaf] = _reserved_file(directory, leaf)

        def check_outputs():
            _check_parent(path, parent)
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _need(_file_identity(current) == _file_identity(selected_directory)
                  and _file_identity(os.fstat(directory)) == _file_identity(selected_directory),
                  "two_slot_attempt_directory_replaced")
            _need(set(os.listdir(directory)) == ROSTER, "two_slot_attempt_directory_roster")
            for leaf, (fd, selected) in files.items():
                _check_file(directory, leaf, fd, selected)
                _check_content(fd, expected_files[leaf])

        check_outputs()
        _publish(files["request.json"][0], request_bytes)
        expected_files["request.json"] = request_bytes
        os.fsync(directory)
        os.fsync(parent)
        check_outputs()
        receipt = {
            "record_type": checker.ATTEMPT_TYPE, "profile": checker.PROFILE,
            "request_id": request["request_id"], "request": checker.binding(request_bytes),
            "status": "incomplete", "phase": "admission", "failure": None,
            "producer_invocations": 0, "evidence_origin": "not_invoked",
            "context_before": None, "context_after": None,
            "sources_before": None, "sources_after": None,
            "qualification": checker.binding(b""), "boundary": dict(checker.BOUNDARY),
        }
        qualification = b""
        try:
            current_context = reader()
            checker.raw.validate_context(current_context)
            receipt["context_before"] = current_context
            receipt["sources_before"] = checker.source_inventory()
            _need(checker.canonical(current_context) == checker.canonical(request["expected_context"]),
                  "two_slot_attempt_context_mismatch")
            _need(checker.canonical(receipt["sources_before"]) == checker.canonical(request["sources"]),
                  "two_slot_attempt_sources_mismatch")
            check_outputs()
            # Lazy import is after request validation, output reservation and
            # fresh admission.  The checker never imports this execution path.
            import qualify_required_gate_idempotence_loader_two_slot_v0 as producer
            receipt["phase"] = "qualification"
            receipt["evidence_origin"] = ("native_owned_probe" if backend is None
                                          else "scripted_test_backend")
            receipt["producer_invocations"] = 1
            record = producer.qualify() if backend is None else producer.qualify(backend=backend)
            encoded = checker.canonical(record)
            _need(0 < len(encoded) <= checker.MAX_QUALIFICATION_BYTES,
                  "two_slot_attempt_qualification_extent")
            qualification = encoded
            if type(record) is dict and record.get("status") == "incomplete":
                reason = record.get("failure")
                receipt["failure"] = (reason if type(reason) is str and
                    re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason)
                    else "two_slot_attempt_qualification_incomplete")
        except BaseException as error:
            receipt["failure"] = _failure(error)

        # These snapshots are independently obtained after the producer's own
        # cleanup, including an incomplete producer result or interruption.
        if receipt["failure"] is None:
            receipt["phase"] = "verification" if receipt["producer_invocations"] else "admission"
        for field, operation in (("context_after", reader),
                                 ("sources_after", checker.source_inventory)):
            try:
                value = operation()
                if field == "context_after":
                    checker.raw.validate_context(value)
                receipt[field] = value
                expected = request["expected_context"] if field == "context_after" else request["sources"]
                _need(checker.canonical(value) == checker.canonical(expected),
                      "two_slot_attempt_context_changed" if field == "context_after"
                      else "two_slot_attempt_sources_changed")
            except BaseException as error:
                receipt["failure"] = receipt["failure"] or _failure(error)

        if qualification:
            check_outputs()
            _publish(files["qualification.json"][0], qualification)
            expected_files["qualification.json"] = qualification
            check_outputs()
        receipt["qualification"] = checker.binding(qualification)
        try:
            inspected = checker.inspect_qualification(request=request,
                                                       qualification_bytes=qualification)
            _need(inspected["state"] == "completed",
                  inspected.get("error") or "two_slot_attempt_qualification_incomplete")
            _need(inspected["report"] is not None, "two_slot_attempt_qualification_report")
            parsed_record = checker.raw.parse(qualification)
            _need(parsed_record["evidence_origin"] == receipt["evidence_origin"],
                  "two_slot_attempt_origin_mismatch")
        except BaseException as error:
            receipt["failure"] = receipt["failure"] or _failure(error)
        if receipt["failure"] is None:
            receipt["status"], receipt["phase"] = "completed", "complete"
        encoded_receipt = checker.canonical(receipt)
        _need(len(encoded_receipt) <= checker.MAX_CONTROL_BYTES,
              "two_slot_attempt_receipt_extent")
        if receipt["status"] == "completed":
            try:
                checker.verify_attempt(request_bytes=request_bytes,
                    expected_request_sha256=expected_request_sha256, attempt_bytes=encoded_receipt,
                    expected_attempt_sha256=checker.binding(encoded_receipt)["sha256"],
                    qualification_bytes=qualification)
            except BaseException as error:
                # A source can also change after the last snapshot but before
                # fresh verification.  Preserve that rejection as diagnostics;
                # it must never cause a completed receipt to be published.
                receipt.update(status="incomplete", phase="verification", failure=_failure(error))
                for field, operation in (("context_after", reader),
                                         ("sources_after", checker.source_inventory)):
                    try:
                        value = operation()
                        if field == "context_after":
                            checker.raw.validate_context(value)
                        receipt[field] = value
                    except BaseException:
                        receipt[field] = None
                encoded_receipt = checker.canonical(receipt)
        if receipt["status"] == "incomplete":
            # A changed source file is itself evidence to preserve.  Validate
            # diagnostics using the preselected schema bytes instead of making
            # their publication depend on the changed live source inventory.
            checker.validate_incomplete_attempt(request_bytes=request_bytes,
                expected_request_sha256=expected_request_sha256, attempt_bytes=encoded_receipt,
                qualification_bytes=qualification, schema_bytes=selected_schema)
        check_outputs()
        _publish(files["attempt.json"][0], encoded_receipt)
        expected_files["attempt.json"] = encoded_receipt
        os.fsync(directory)
        os.fsync(parent)
        check_outputs()
        return receipt
    except BaseException:
        if "attempt.json" in files:
            _invalidate(files["attempt.json"][0])
        raise
    finally:
        receipt_file = files.get("attempt.json")
        final = None if receipt_file is None else (*receipt_file, path / "attempt.json")
        descriptors = [fd for leaf, (fd, _selected) in files.items()
                       if leaf != "attempt.json"]
        _close_all([*descriptors, directory, parent], final=final)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparer = commands.add_parser("prepare", help="prepare a request without executing a probe")
    preparer.add_argument("--output", type=Path, required=True)
    runner = commands.add_parser("attempt", help="explicitly execute at most one fixed synthetic probe")
    runner.add_argument("--request", type=Path, required=True)
    runner.add_argument("--request-sha256", required=True)
    runner.add_argument("--acknowledgement", required=True)
    runner.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(output=args.output)
            return 0
        request_bytes = checker.read_regular(args.request, checker.MAX_CONTROL_BYTES)
        receipt = attempt(request_bytes=request_bytes,
            expected_request_sha256=args.request_sha256, acknowledgement=args.acknowledgement,
            output_directory=args.output_directory)
        return 0 if receipt["status"] == "completed" else 1
    except BaseException as error:
        sys.stderr.write(_failure(error) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
