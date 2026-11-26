#!/usr/bin/env python3
"""Reconstruct a selected two-slot qualification request and preserved attempt.

This module only reads data. It never imports the native producer, samples the
current host context or executes a probe. The acknowledgement is an invocation
safeguard, not proof of owner identity, execution or release authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_loader_two_slot_qualification_v0 as raw

ROOT = Path(__file__).resolve().parents[1]
REQUEST_TYPE = "required_gate_idempotence_loader_two_slot_request_v0"
ATTEMPT_TYPE = "required_gate_idempotence_loader_two_slot_attempt_v0"
PROFILE = "linux_x86_64_loader_two_slot_attempt_v0"
ACKNOWLEDGEMENT = "QUALIFY_LOADER_TWO_SLOT_ONLY"
REQUEST_SCHEMA_PATH = "schemas/required_gate_idempotence_loader_two_slot_request_v0.schema.json"
ATTEMPT_SCHEMA_PATH = "schemas/required_gate_idempotence_loader_two_slot_attempt_v0.schema.json"
SOURCE_PATHS = tuple(sorted((*raw.SOURCE_PATHS, REQUEST_SCHEMA_PATH, ATTEMPT_SCHEMA_PATH,
    "tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py",
    "tools/prepare_required_gate_idempotence_loader_two_slot_v0.py")))
BOUNDARY = dict(raw.BOUNDARY)
MAX_CONTROL_BYTES = 65536
MAX_SOURCE_BYTES = 1048576
MAX_QUALIFICATION_BYTES = raw.MAX_RECORD_BYTES
LIMITS = {
    "native_attempts": 1, "observation_ns": 15000000000,
    "cleanup_ns": 2000000000, "qualification_bytes": MAX_QUALIFICATION_BYTES,
    "decoded_raw_bytes": raw.MAX_RAW_BYTES, "raw_files": raw.MAX_RAW_FILES,
    "operations": raw.MAX_OPERATIONS,
}
PHASES = ("admission", "qualification", "verification", "publication", "complete")
ORIGINS = ("not_invoked", "native_owned_probe", "scripted_test_backend")
ERROR_RE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
_DIRECTORY_FLAGS = _READ_FLAGS | os.O_DIRECTORY


class AttemptError(ValueError):
    """Stable failure without inspected bytes, paths or process contents."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise AttemptError(code)


def canonical(value):
    return raw.canonical(value)


def binding(value):
    _need(type(value) is bytes, "two_slot_attempt_binding_type")
    return {"size_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, code)


def _pairs(items):
    value = {}
    for key, item in items:
        _need(key not in value, "two_slot_attempt_duplicate_key")
        value[key] = item
    return value


def _number(_value):
    raise AttemptError("two_slot_attempt_noninteger_json")


def parse(value, limit=MAX_CONTROL_BYTES):
    _need(type(value) is bytes and 0 < len(value) <= limit,
          "two_slot_attempt_control_extent")
    try:
        result = json.loads(value.decode("ascii"), object_pairs_hook=_pairs,
                            parse_float=_number, parse_constant=_number)
        pending, count = [(result, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _need(count <= 16000 and depth <= 24, "two_slot_attempt_json_structure")
            if type(item) is dict:
                _need(len(item) <= 128, "two_slot_attempt_json_structure")
                for key, child in item.items():
                    _need(type(key) is str and len(key) <= 256,
                          "two_slot_attempt_json_key")
                    pending.append((child, depth + 1))
            elif type(item) is list:
                _need(len(item) <= 160, "two_slot_attempt_json_structure")
                pending.extend((child, depth + 1) for child in item)
            elif type(item) is str:
                _need(len(item) <= 8192, "two_slot_attempt_json_string")
            else:
                _need(item is None or type(item) is bool or
                      (type(item) is int and -(1 << 63) < item < (1 << 63)),
                      "two_slot_attempt_json_value")
        return result
    except AttemptError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AttemptError("two_slot_attempt_invalid_json") from exc


def _selected_file(value, maximum, minimum=0):
    _need(type(value) is dict and set(value) == {"size_bytes", "sha256"},
          "two_slot_attempt_descriptor_fields")
    _need(type(value["size_bytes"]) is int and minimum <= value["size_bytes"] <= maximum,
          "two_slot_attempt_descriptor_extent")
    _digest(value["sha256"], "two_slot_attempt_descriptor_digest")


def _inventory(value):
    _need(type(value) is list and len(value) == len(SOURCE_PATHS),
          "two_slot_attempt_source_roster")
    for item, path in zip(value, SOURCE_PATHS):
        _need(type(item) is dict and set(item) == {"path", "size_bytes", "sha256"}
              and item["path"] == path, "two_slot_attempt_source_roster")
        _selected_file({key: item[key] for key in ("size_bytes", "sha256")},
                       MAX_SOURCE_BYTES, 1)


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _open_parent(path):
    """Pin real parent directories; reject symlink components and '..'."""
    _need(isinstance(path, (str, Path)), "two_slot_attempt_path")
    value = Path(path)
    _need(0 < len(str(value)) <= 4096 and len(value.parts) <= 128
          and ".." not in value.parts and value.name not in ("", ".", ".."),
          "two_slot_attempt_path")
    parts = value.parts[1:] if value.is_absolute() else value.parts
    directory = os.open("/" if value.is_absolute() else ".", _DIRECTORY_FLAGS)
    try:
        for part in parts[:-1]:
            next_directory = os.open(part, _DIRECTORY_FLAGS, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        return directory, parts[-1]
    except BaseException:
        os.close(directory)
        raise


def _read_at(directory, name, limit, *, empty=False):
    descriptor = os.open(name, _READ_FLAGS, dir_fd=directory)
    try:
        before = os.fstat(descriptor)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
              and (0 if empty else 1) <= before.st_size <= limit,
              "two_slot_attempt_input_extent")
        parts, size = [], 0
        while True:
            part = os.read(descriptor, min(65536, limit + 1 - size))
            if not part:
                break
            parts.append(part)
            size += len(part)
            _need(size <= limit, "two_slot_attempt_input_extent")
        after = os.fstat(descriptor)
        selected = os.stat(name, dir_fd=directory, follow_symlinks=False)
        _need(_identity(before) == _identity(after) == _identity(selected)
              and size == before.st_size, "two_slot_attempt_input_changed")
        return b"".join(parts)
    finally:
        os.close(descriptor)


def read_regular(path, limit=MAX_CONTROL_BYTES, *, empty=False):
    directory, name = _open_parent(path)
    try:
        return _read_at(directory, name, limit, empty=empty)
    finally:
        os.close(directory)


def _source_bytes():
    return {path: read_regular(ROOT / path, MAX_SOURCE_BYTES) for path in SOURCE_PATHS}


def source_inventory():
    return [{"path": path, **binding(value)} for path, value in _source_bytes().items()]


def _schema(value, schema_bytes):
    import jsonschema
    schema = parse(schema_bytes, MAX_SOURCE_BYTES)
    _need(next(jsonschema.Draft202012Validator(schema).iter_errors(value), None) is None,
          "two_slot_attempt_schema")


def _request_fields(request):
    """Check immutable selection fields without reading current source files."""
    _need(type(request) is dict and set(request) == {
        "record_type", "profile", "request_id", "acknowledgement", "expected_context",
        "sources", "probe", "limits", "boundary"}, "two_slot_attempt_request_fields")
    _need(request["record_type"] == REQUEST_TYPE and request["profile"] == PROFILE
          and request["acknowledgement"] == ACKNOWLEDGEMENT,
          "two_slot_attempt_request_profile")
    _need(type(request["request_id"]) is str and
          re.fullmatch(r"[0-9a-f]{32}", request["request_id"]) is not None,
          "two_slot_attempt_request_identity")
    raw.validate_context(request["expected_context"])
    _same(request["boundary"], BOUNDARY, "two_slot_attempt_boundary")
    _same(request["limits"], LIMITS, "two_slot_attempt_limits")
    _same(request["probe"], binding(raw.probe_bytes()), "two_slot_attempt_probe")
    _inventory(request["sources"])


def _validated_request(request_bytes, expected_request_sha256, source_bytes):
    _need(type(request_bytes) is bytes and 0 < len(request_bytes) <= MAX_CONTROL_BYTES,
          "two_slot_attempt_request_extent")
    _digest(expected_request_sha256, "two_slot_attempt_request_digest")
    _need(binding(request_bytes)["sha256"] == expected_request_sha256,
          "two_slot_attempt_request_digest_mismatch")
    request = parse(request_bytes)
    _schema(request, source_bytes[REQUEST_SCHEMA_PATH])
    _request_fields(request)
    inventory = [{"path": path, **binding(value)} for path, value in source_bytes.items()]
    _same(request["sources"], inventory, "two_slot_attempt_selected_sources")
    return request


def request_value(expected_context, *, request_id=None):
    """Construct a request from already independently acquired context data."""
    raw.validate_context(expected_context)
    result = {
        "record_type": REQUEST_TYPE, "profile": PROFILE,
        "request_id": uuid.uuid4().hex if request_id is None else request_id,
        "acknowledgement": ACKNOWLEDGEMENT,
        "expected_context": parse(canonical(expected_context)),
        "sources": source_inventory(), "probe": binding(raw.probe_bytes()),
        "limits": dict(LIMITS), "boundary": dict(BOUNDARY),
    }
    encoded = canonical(result)
    return verify_request(request_bytes=encoded, expected_request_sha256=binding(encoded)["sha256"])


def verify_request(*, request_bytes, expected_request_sha256):
    """Check exact request bytes and local selected source; read no live context."""
    try:
        _need(type(request_bytes) is bytes and 0 < len(request_bytes) <= MAX_CONTROL_BYTES,
              "two_slot_attempt_request_extent")
        sources_before = _source_bytes()
        request = _validated_request(request_bytes, expected_request_sha256, sources_before)
        _need(_source_bytes() == sources_before, "two_slot_attempt_sources_changed")
        return request
    except AttemptError:
        raise
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise AttemptError("two_slot_attempt_invalid_request") from exc


def inspect_qualification(*, request, qualification_bytes):
    """Reconstruct raw mechanics, or classify bounded unavailable diagnostics."""
    if qualification_bytes is None:
        return {"state": "absent", "error": "two_slot_attempt_qualification_absent", "report": None}
    _need(type(qualification_bytes) is bytes and len(qualification_bytes) <= MAX_QUALIFICATION_BYTES,
          "two_slot_attempt_qualification_extent")
    if not qualification_bytes:
        return {"state": "empty", "error": "two_slot_attempt_qualification_empty", "report": None}
    try:
        report = raw.verify_record(record_bytes=qualification_bytes,
            expected_record_sha256=binding(qualification_bytes)["sha256"],
            expected_context=request["expected_context"])
    except raw.QualificationError as exc:
        return {"state": "invalid", "error": exc.code, "report": None}
    return {"state": "completed" if report["complete_mechanics_verified"] else "incomplete",
            "error": None, "report": report}


def _attempt_fields(request, request_bytes, attempt_bytes, qualification_bytes, schema_bytes):
    _need(qualification_bytes is None or (type(qualification_bytes) is bytes and
          len(qualification_bytes) <= MAX_QUALIFICATION_BYTES),
          "two_slot_attempt_qualification_extent")
    attempt = parse(attempt_bytes)
    _schema(attempt, schema_bytes)
    _same(attempt["boundary"], BOUNDARY, "two_slot_attempt_boundary")
    _same(attempt["request"], binding(request_bytes), "two_slot_attempt_request_binding")
    _need(attempt["request_id"] == request["request_id"], "two_slot_attempt_request_identity")
    _same(attempt["qualification"], None if qualification_bytes is None else binding(qualification_bytes),
          "two_slot_attempt_qualification_binding")
    for name in ("context_before", "context_after"):
        if attempt[name] is not None:
            raw.validate_context(attempt[name])
    for name in ("sources_before", "sources_after"):
        if attempt[name] is not None:
            _inventory(attempt[name])
    calls, origin = attempt["producer_invocations"], attempt["evidence_origin"]
    _need(type(calls) is int and calls in (0, 1), "two_slot_attempt_invocation_count")
    _need((calls == 0 and origin == "not_invoked") or
          (calls == 1 and origin in ORIGINS[1:]), "two_slot_attempt_invocation_origin")
    if calls == 0:
        _need(qualification_bytes in (None, b""), "two_slot_attempt_uninvoked_record")
    # Even an incomplete record cannot be relabelled as another origin.
    if qualification_bytes:
        try:
            decoded = raw.parse(qualification_bytes)
        except raw.QualificationError:
            decoded = None
        if type(decoded) is dict and decoded.get("evidence_origin") in ORIGINS[1:]:
            _need(decoded["evidence_origin"] == origin, "two_slot_attempt_record_origin")
    if attempt["status"] == "incomplete":
        _need(attempt["phase"] != "complete" and type(attempt["failure"]) is str
              and ERROR_RE.fullmatch(attempt["failure"]), "two_slot_attempt_incomplete_reason")
    return attempt


def validate_incomplete_attempt(*, request_bytes, expected_request_sha256, attempt_bytes,
                                qualification_bytes, schema_bytes):
    """Validate diagnostics using the schema selected before source drift.

    This is a preservation-only guard, not independent reconstruction. It can
    never validate a completed receipt or return a verification report. The
    caller must have fully verified the selected request before execution and
    retained the exact selected schema bytes at that time. Replaying the result
    still requires verify_attempt with the complete selected implementation.
    """
    _digest(expected_request_sha256, "two_slot_attempt_request_digest")
    request = parse(request_bytes)
    _need(binding(request_bytes)["sha256"] == expected_request_sha256,
          "two_slot_attempt_request_digest_mismatch")
    _request_fields(request)
    _need(type(schema_bytes) is bytes and 0 < len(schema_bytes) <= MAX_SOURCE_BYTES,
          "two_slot_attempt_selected_schema_extent")
    selected = next(item for item in request["sources"] if item["path"] == ATTEMPT_SCHEMA_PATH)
    _same({key: selected[key] for key in ("size_bytes", "sha256")}, binding(schema_bytes),
          "two_slot_attempt_selected_schema_binding")
    attempt = _attempt_fields(request, request_bytes, attempt_bytes, qualification_bytes, schema_bytes)
    _need(attempt["status"] == "incomplete", "two_slot_attempt_diagnostic_only")
    return attempt


def verify_attempt(*, request_bytes, expected_request_sha256, attempt_bytes,
                   expected_attempt_sha256, qualification_bytes):
    """Reconstruct a complete or diagnostic receipt, never authenticate execution."""
    try:
        _need(type(request_bytes) is bytes and 0 < len(request_bytes) <= MAX_CONTROL_BYTES,
              "two_slot_attempt_request_extent")
        _need(type(attempt_bytes) is bytes and 0 < len(attempt_bytes) <= MAX_CONTROL_BYTES,
              "two_slot_attempt_receipt_extent")
        _need(qualification_bytes is None or (type(qualification_bytes) is bytes and
              len(qualification_bytes) <= MAX_QUALIFICATION_BYTES),
              "two_slot_attempt_qualification_extent")
        _digest(expected_attempt_sha256, "two_slot_attempt_receipt_digest")
        _need(binding(attempt_bytes)["sha256"] == expected_attempt_sha256,
              "two_slot_attempt_receipt_digest_mismatch")
        sources_before = _source_bytes()
        request = _validated_request(request_bytes, expected_request_sha256, sources_before)
        attempt = _attempt_fields(request, request_bytes, attempt_bytes, qualification_bytes,
                                  sources_before[ATTEMPT_SCHEMA_PATH])
        calls, origin = attempt["producer_invocations"], attempt["evidence_origin"]
        selected_context = (attempt["context_before"] == request["expected_context"]
                            and attempt["context_after"] == request["expected_context"])
        selected_sources = (attempt["sources_before"] == request["sources"]
                            and attempt["sources_after"] == request["sources"])
        result = inspect_qualification(request=request, qualification_bytes=qualification_bytes)
        complete = attempt["status"] == "completed"
        if complete:
            _need(attempt["phase"] == "complete" and attempt["failure"] is None
                  and calls == 1, "two_slot_attempt_completion_state")
            _need(selected_context, "two_slot_attempt_selected_context")
            _need(selected_sources, "two_slot_attempt_selected_sources")
            _need(result["state"] == "completed", "two_slot_attempt_raw_not_complete")
            _need(result["report"]["evidence_origin"] == origin, "two_slot_attempt_record_origin")
        else:
            _need(attempt["phase"] != "complete" and type(attempt["failure"]) is str
                  and ERROR_RE.fullmatch(attempt["failure"]), "two_slot_attempt_incomplete_reason")
        _need(_source_bytes() == sources_before, "two_slot_attempt_sources_changed")
        native = complete and origin == "native_owned_probe"
        scripted = complete and origin == "scripted_test_backend"
        return {
            "record_type": "required_gate_idempotence_loader_two_slot_attempt_verification_v0",
            "profile": PROFILE,
            "status": ("accepted_native_qualification_attempt" if native else
                       "accepted_scripted_qualification_attempt" if scripted else "preserved_incomplete"),
            "request_id": request["request_id"], "request": binding(request_bytes),
            "attempt": binding(attempt_bytes), "qualification": attempt["qualification"],
            "evidence_origin": origin, "producer_invocations": calls,
            "request_binding_verified": True, "attempt_binding_verified": True,
            "qualification_binding_verified": qualification_bytes is not None,
            "selected_context_binding_verified": selected_context,
            "source_inventory_verified": selected_sources,
            "qualification_record_state": result["state"],
            "qualification_error": result["error"],
            "complete_mechanics_verified": complete,
            "native_record_reconstructed": native, "scripted_record_reconstructed": scripted,
            "incomplete_attempt_preserved": not complete,
            "accepted_return_events": 9 if complete else 0,
            "post_terminal_resumes": 0 if complete else None,
            **BOUNDARY,
        }
    except AttemptError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        raise AttemptError("two_slot_attempt_invalid_receipt") from exc


def read_attempt_directory(path):
    """Read the finite receipt roster through a pinned, non-symlink directory."""
    parent, name = _open_parent(path)
    directory = None
    try:
        directory = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
        before = os.fstat(directory)
        names = set(os.listdir(directory))
        _need(names in ({"request.json", "attempt.json"},
                        {"request.json", "qualification.json", "attempt.json"}),
              "two_slot_attempt_directory_roster")
        request_bytes = _read_at(directory, "request.json", MAX_CONTROL_BYTES)
        attempt_bytes = _read_at(directory, "attempt.json", MAX_CONTROL_BYTES)
        qualification_bytes = (_read_at(directory, "qualification.json", MAX_QUALIFICATION_BYTES,
                                        empty=True) if "qualification.json" in names else None)
        after = os.fstat(directory)
        selected = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need(_identity(before) == _identity(after) == _identity(selected)
              and set(os.listdir(directory)) == names, "two_slot_attempt_directory_changed")
        return request_bytes, attempt_bytes, qualification_bytes
    finally:
        if directory is not None:
            os.close(directory)
        os.close(parent)


def _parent_unchanged(path, parent, name):
    current, current_name = _open_parent(path)
    try:
        original_stat, current_stat = os.fstat(parent), os.fstat(current)
        _need(current_name == name and
              (original_stat.st_dev, original_stat.st_ino) ==
              (current_stat.st_dev, current_stat.st_ino),
              "two_slot_attempt_output_parent_replaced")
    finally:
        os.close(current)


def _invalidate_output(path, descriptor, owned):
    """A failed close may have consumed its descriptor; reopen only our inode."""
    if owned is None:
        return
    if descriptor is not None:
        try:
            current = os.fstat(descriptor)
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                os.ftruncate(descriptor, 0)
                return
        except OSError:
            pass
    parent = replacement = None
    try:
        parent, name = _open_parent(path)
        replacement = os.open(name, os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
                              | os.O_NONBLOCK, dir_fd=parent)
        current = os.fstat(replacement)
        if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
            os.ftruncate(replacement, 0)
    except (OSError, ValueError):
        pass
    finally:
        for item in (replacement, parent):
            if item is not None:
                try:
                    os.close(item)
                except OSError:
                    pass


def _output_exact(descriptor, owned, data):
    """Detect content drift of the same owned inode, not only path replacement."""
    before = os.fstat(descriptor)
    _need((before.st_dev, before.st_ino, before.st_mode, before.st_nlink) ==
          (owned.st_dev, owned.st_ino, owned.st_mode, owned.st_nlink)
          and before.st_size == len(data), "two_slot_attempt_output_changed")
    parts, offset = [], 0
    while True:
        part = os.pread(descriptor, min(65536, len(data) + 1 - offset), offset)
        if not part:
            break
        parts.append(part)
        offset += len(part)
        _need(offset <= len(data), "two_slot_attempt_output_changed")
    after = os.fstat(descriptor)
    _need(_identity(before) == _identity(after) and b"".join(parts) == data,
          "two_slot_attempt_output_changed")


def write_new(path, data):
    """Publish only through a newly owned descriptor; invalidate on any failure."""
    _need(type(data) is bytes and 0 < len(data) <= MAX_CONTROL_BYTES,
          "two_slot_attempt_output_extent")
    parent, name = _open_parent(path)
    descriptor = None
    owned = None
    closing_descriptor = None
    try:
        descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
                             | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        owned = os.fstat(descriptor)
        _need(stat.S_ISREG(owned.st_mode) and owned.st_nlink == 1,
              "two_slot_attempt_output_identity")
        _parent_unchanged(path, parent, name)
        remaining = memoryview(data)
        while remaining:
            count = os.write(descriptor, remaining)
            _need(count > 0, "two_slot_attempt_output_write")
            remaining = remaining[count:]
        os.fsync(descriptor)
        _output_exact(descriptor, owned, data)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need((owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino)
              and current.st_nlink == 1, "two_slot_attempt_output_replaced")
        _parent_unchanged(path, parent, name)
        os.fsync(parent)
        _output_exact(descriptor, owned, data)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need((owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino)
              and current.st_nlink == 1, "two_slot_attempt_output_replaced")
        _parent_unchanged(path, parent, name)
        # Closing is part of publication, not a fallible finally after success.
        # Keep the owned file descriptor while closing the parent, so a failed
        # directory close can still invalidate the exact newly created inode.
        closing_parent = parent
        parent = None
        os.close(closing_parent)
        _output_exact(descriptor, owned, data)
        closing_descriptor = descriptor
        descriptor = None
        os.close(closing_descriptor)
        closing_descriptor = None
    except BaseException:
        # Do not retry a failed close: it may already have consumed the fd.
        # Identity-checked invalidation can use the still-owned fd or reopen
        # only the exact inode, without closing a possibly reused fd number.
        _invalidate_output(path, descriptor if descriptor is not None else closing_descriptor, owned)
        raise
    finally:
        for item in (descriptor, parent):
            if item is not None:
                try:
                    os.close(item)
                except OSError:
                    pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--attempt-directory", type=Path, required=True)
    parser.add_argument("--attempt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request_bytes = read_regular(args.request)
        preserved_request, attempt_bytes, qualification_bytes = read_attempt_directory(args.attempt_directory)
        _need(preserved_request == request_bytes, "two_slot_attempt_preserved_request")
        report = verify_attempt(request_bytes=request_bytes,
            expected_request_sha256=args.request_sha256, attempt_bytes=attempt_bytes,
            expected_attempt_sha256=args.attempt_sha256, qualification_bytes=qualification_bytes)
        write_new(args.output, canonical(report))
        return 0 if report["complete_mechanics_verified"] else 1
    except (OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, AttemptError) else "two_slot_attempt_io"
        sys.stderr.write(code + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
