#!/usr/bin/env python3
"""Check preserved fixed-entry build records without authenticating a compiler.

The checker reads bytes only. It never invokes a compiler, an entry binary,
GitHub, a launcher, or an attestation verifier. A consistent repeated build
record does not establish source/binary equivalence or execution authority.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_containment_v0 as containment

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_entry_build_v0.schema.json"
SCHEMA_SHA256 = "ff382fe396ef01309db95ad129b30b6ec4c4dc8d4460d54448637c9cdac6d6af"
ENTRY_SOURCE_PATH = "tools/required_gate_idempotence_containment_entry_v0.c"
ENTRY_SOURCE_SHA256 = "0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f"
ENTRY_SOURCE_SIZE = 4598
PROFILE = "gcc_static_entry_repeat_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW_PATH = ".github/workflows/required_gate_idempotence_entry_build_v0.yml"
CC_FLAGS = (
    "-v", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-ffreestanding",
    "-fno-builtin", "-fno-pie", "-fno-stack-protector", "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables", "-nostdlib", "-static", "-no-pie", "-Wl,--build-id=none",
    "-Wl,-z,noexecstack",
)
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC",
               "SOURCE_DATE_EPOCH": "0", "TMPDIR": "."}
LIMITS = {"build_seconds": 30, "query_seconds": 10, "stdout_bytes": 65536,
          "stderr_bytes": 262144, "entry_bytes": 16777216, "tool_bytes": 134217728,
          "control_bytes": 1048576, "builds": 2}
BOUNDARY = {**containment.BOUNDARY, "entry_binary_executed": False,
            "compiler_closure_verified": False, "source_binary_equivalence_verified": False,
            "github_build_provenance_verified": False, "host_launcher_runtime_verified": False,
            "toolchain_execution_authenticated": False}
BUILD_IDS = ("build-1", "build-2")
TOOL_NAMES = ("as", "cc1", "collect2", "compiler", "ld")
QUERY_NAMES = tuple(name for name in TOOL_NAMES if name != "compiler")
FILES = tuple(sorted(("request.json", "source.c", "toolchain-before.json", "toolchain-after.json",
                      *(build + "/" + name for build in BUILD_IDS
                        for name in ("entry.c", "entry", "stdout.bin", "stderr.bin", "result.json")))))
HASH = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
PATH_PART = re.compile(r"[A-Za-z0-9_.+\-]+\Z")


class BuildError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise BuildError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("ascii")


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= LIMITS["control_bytes"], "entry_build_control_size")

    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "entry_build_duplicate_key")
            result[key] = value
        return result

    def invalid(_value):
        raise BuildError("entry_build_json_invalid")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BuildError("entry_build_json_invalid") from exc
    need(type(value) is dict, "entry_build_object_required")
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(depth <= 32 and count <= 10000, "entry_build_json_complexity")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        else:
            need(item is None or type(item) in (str, bool, int), "entry_build_json_value_type")
            if type(item) is int:
                need(-(2**63) <= item < 2**63, "entry_build_json_integer_range")
    return value


def binding(raw):
    need(type(raw) is bytes, "entry_build_bytes_required")
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def _same(actual, expected):
    return canonical(actual) == canonical(expected)


def _keys(value, keys, code):
    need(type(value) is dict and set(value) == set(keys), code)


def _hash(value):
    return type(value) is str and HASH.fullmatch(value) is not None


def _commit(value):
    return type(value) is str and COMMIT.fullmatch(value) is not None


def _path(value):
    return (type(value) is str and value.startswith("/") and len(value) <= 4096
            and all(part not in {"", ".", ".."} and PATH_PART.fullmatch(part)
                    for part in value.split("/")[1:]))


def _descriptor(value, *, maximum, empty=False, extra=()):
    _keys(value, {"sha256", "size_bytes", *extra}, "entry_build_descriptor_invalid")
    need(_hash(value["sha256"]) and type(value["size_bytes"]) is int
         and (0 if empty else 1) <= value["size_bytes"] <= maximum, "entry_build_descriptor_invalid")


def _bound(raw, value, maximum, *, empty=False):
    _descriptor(value, maximum=maximum, empty=empty)
    need(type(raw) is bytes and binding(raw) == value, "entry_build_file_binding_mismatch")


def _boundary(value):
    for key, required in BOUNDARY.items():
        need(key in value and type(value[key]) is type(required) and value[key] == required,
             "entry_build_authority_boundary_mismatch")


def _canonical_record(raw):
    result = parse(raw)
    need(canonical(result) == raw, "entry_build_noncanonical_record")
    return result


def validate_request(raw, expected_sha256, source_commit):
    need(_hash(expected_sha256) and type(raw) is bytes and sha(raw) == expected_sha256,
         "entry_build_request_digest_mismatch")
    need(_commit(source_commit), "entry_build_source_commit_invalid")
    request = _canonical_record(raw)
    _keys(request, {"format", "profile", "source_commit", "source", "compiler", "argv_template",
                    "environment", "limits", "context", *BOUNDARY}, "entry_build_request_shape")
    _boundary(request)
    need(request["format"] == "required_gate_idempotence_entry_build_request_v0"
         and request["profile"] == PROFILE and request["source_commit"] == source_commit,
         "entry_build_request_identity_mismatch")
    need(_same(request["source"], {"path": ENTRY_SOURCE_PATH, "sha256": ENTRY_SOURCE_SHA256,
                                   "size_bytes": ENTRY_SOURCE_SIZE}), "entry_build_source_binding_mismatch")
    compiler = request["compiler"]
    _descriptor(compiler, maximum=LIMITS["tool_bytes"], extra=("path",))
    need(_path(compiler["path"]), "entry_build_compiler_path_invalid")
    need(_same(request["argv_template"], [compiler["path"], *CC_FLAGS, "entry.c", "-o", "entry"])
         and _same(request["environment"], ENVIRONMENT) and _same(request["limits"], LIMITS),
         "entry_build_recipe_mismatch")
    context = request["context"]
    if context != {"kind": "local_example"}:
        _keys(context, {"kind", "repository", "workflow_path", "source_commit", "workflow_sha", "ref",
                        "run_id", "run_attempt", "event_name"}, "entry_build_context_invalid")
        need(context["kind"] == "github_workflow" and context["repository"] == REPOSITORY
             and context["workflow_path"] == WORKFLOW_PATH and context["source_commit"] == source_commit
             and context["workflow_sha"] == source_commit and context["ref"] == "refs/heads/main"
             and type(context["run_id"]) is int and 0 < context["run_id"] < 2**63
             and type(context["run_attempt"]) is int and context["run_attempt"] == 1
             and context["event_name"] == "workflow_dispatch", "entry_build_context_invalid")
    safe = containment.bootstrap.runtime.observation.safe
    try:
        schema_raw = safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(schema_raw) == SCHEMA_SHA256, "entry_build_schema_source_mismatch")
        safe._validate_schema(request, parse(schema_raw), "entry_build_request_schema_invalid", "request")
    except safe.ContractError as exc:
        raise BuildError(exc.code) from exc
    return request


def _process(value, seconds):
    _keys(value, {"pid", "exit_code", "elapsed_ns", "timed_out", "stdout_overflow", "stderr_overflow"},
          "entry_build_process_shape")
    need(type(value["pid"]) is int and 0 < value["pid"] < 2**31
         and type(value["exit_code"]) is int and value["exit_code"] == 0
         and type(value["elapsed_ns"]) is int and 0 < value["elapsed_ns"] <= seconds * 1_000_000_000
         and all(value[key] is False for key in ("timed_out", "stdout_overflow", "stderr_overflow")),
         "entry_build_process_incomplete")


def _base64(value, maximum):
    need(type(value) is str and len(value) <= ((maximum + 2) // 3) * 4, "entry_build_query_bytes_invalid")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise BuildError("entry_build_query_bytes_invalid") from exc
    need(len(raw) <= maximum and base64.b64encode(raw).decode("ascii") == value, "entry_build_query_bytes_invalid")
    return raw


def _toolchain(raw, request):
    value = _canonical_record(raw)
    _keys(value, {"format", "components", "version", "queries"}, "entry_build_toolchain_shape")
    need(value["format"] == "required_gate_idempotence_entry_toolchain_v0", "entry_build_toolchain_shape")
    components = value["components"]
    need(type(components) is list and len(components) == len(TOOL_NAMES), "entry_build_toolchain_components")
    for expected, row in zip(TOOL_NAMES, components):
        _descriptor(row, maximum=LIMITS["tool_bytes"], extra=("name", "lookup_path", "path"))
        need(row["name"] == expected and _path(row["lookup_path"]) and _path(row["path"]),
             "entry_build_toolchain_components")
    by_name = {row["name"]: row for row in components}
    compiler = request["compiler"]
    need(_same(by_name["compiler"], {"name": "compiler", "lookup_path": compiler["path"], **compiler}),
         "entry_build_toolchain_compiler_mismatch")
    version = value["version"]
    _keys(version, {"argv", "stdout_b64", "stderr_b64", "process"}, "entry_build_version_shape")
    need(_same(version["argv"], [compiler["path"], "--version"]), "entry_build_query_argv_mismatch")
    _process(version["process"], LIMITS["query_seconds"])
    version_out = _base64(version["stdout_b64"], LIMITS["stdout_bytes"])
    version_err = _base64(version["stderr_b64"], LIMITS["stderr_bytes"])
    need(bool(version_out) and not version_err, "entry_build_version_invalid")
    queries = value["queries"]
    need(type(queries) is list and len(queries) == len(QUERY_NAMES), "entry_build_query_inventory")
    stable_queries = []
    for name, row in zip(QUERY_NAMES, queries):
        _keys(row, {"name", "argv", "stdout_b64", "stderr_b64", "process"}, "entry_build_query_shape")
        need(row["name"] == name and _same(row["argv"], [compiler["path"], "-print-prog-name=" + name]),
             "entry_build_query_argv_mismatch")
        _process(row["process"], LIMITS["query_seconds"])
        stdout = _base64(row["stdout_b64"], LIMITS["stdout_bytes"])
        stderr = _base64(row["stderr_b64"], LIMITS["stderr_bytes"])
        need(not stderr and stdout.endswith(b"\n") and stdout.count(b"\n") == 1,
             "entry_build_tool_query_invalid")
        try:
            queried = stdout[:-1].decode("ascii")
        except UnicodeError as exc:
            raise BuildError("entry_build_tool_query_invalid") from exc
        lookup = by_name[name]["lookup_path"]
        if queried.startswith("/"):
            need(_path(queried) and lookup == queried, "entry_build_tool_lookup_mismatch")
        else:
            need(queried == name
                 and lookup in {"/usr/bin/" + queried, "/bin/" + queried}, "entry_build_tool_lookup_mismatch")
        stable_queries.append({key: item for key, item in row.items() if key != "process"})
    return {"components": components, "version": {key: item for key, item in version.items() if key != "process"},
            "queries": stable_queries}


def file_limit(name):
    if name.endswith("/entry"):
        return LIMITS["entry_bytes"]
    if name.endswith("/stdout.bin"):
        return LIMITS["stdout_bytes"]
    if name.endswith("/stderr.bin"):
        return LIMITS["stderr_bytes"]
    if name in {"source.c", "build-1/entry.c", "build-2/entry.c"}:
        return ENTRY_SOURCE_SIZE
    return LIMITS["control_bytes"]


def check_payload(payload, *, expected_request_sha256, expected_record_sha256, source_commit):
    need(type(payload) is dict and set(payload) == set(FILES) | {"record.json"}, "entry_build_inventory_mismatch")
    for name, raw in payload.items():
        need(type(raw) is bytes and len(raw) <= file_limit(name), "entry_build_file_size")
    request = validate_request(payload["request.json"], expected_request_sha256, source_commit)
    need(_hash(expected_record_sha256) and sha(payload["record.json"]) == expected_record_sha256,
         "entry_build_record_digest_mismatch")
    record = _canonical_record(payload["record.json"])
    _keys(record, {"format", "profile", "status", "source_commit", "request_sha256", "files", "build_ids",
                   "repeat_build_equal", "entry_static_shape_verified", "toolchain_observations_stable", *BOUNDARY},
          "entry_build_record_shape")
    _boundary(record)
    need(record["format"] == "required_gate_idempotence_entry_build_v0" and record["profile"] == PROFILE
         and record["status"] == "completed" and record["source_commit"] == source_commit
         and record["request_sha256"] == expected_request_sha256 and record["build_ids"] == list(BUILD_IDS)
         and record["repeat_build_equal"] is True and record["entry_static_shape_verified"] is True
         and record["toolchain_observations_stable"] is True, "entry_build_record_identity_mismatch")
    need(type(record["files"]) is list and len(record["files"]) == len(FILES), "entry_build_manifest_invalid")
    for name, row in zip(FILES, record["files"]):
        _descriptor(row, maximum=file_limit(name), empty=name.endswith(".bin"), extra=("path",))
        need(row["path"] == name and _same(row, {"path": name, **binding(payload[name])}),
             "entry_build_manifest_binding_mismatch")
    source = payload["source.c"]
    _bound(source, {"sha256": ENTRY_SOURCE_SHA256, "size_bytes": ENTRY_SOURCE_SIZE}, ENTRY_SOURCE_SIZE)
    before = _toolchain(payload["toolchain-before.json"], request)
    after = _toolchain(payload["toolchain-after.json"], request)
    need(_same(before, after), "entry_build_toolchain_changed")
    for build in BUILD_IDS:
        result = _canonical_record(payload[build + "/result.json"])
        _keys(result, {"format", "build_id", "working_directory", "argv", "environment", "process",
                       "source", "stdout", "stderr", "entry"}, "entry_build_execution_shape")
        need(result["format"] == "required_gate_idempotence_entry_build_execution_v0"
             and result["build_id"] == build and result["working_directory"] == build
             and _same(result["argv"], request["argv_template"])
             and _same(result["environment"], ENVIRONMENT), "entry_build_execution_recipe_mismatch")
        _process(result["process"], LIMITS["build_seconds"])
        need(payload[build + "/entry.c"] == source, "entry_build_occurrence_source_mismatch")
        for key, filename in (("source", "entry.c"), ("stdout", "stdout.bin"), ("stderr", "stderr.bin"), ("entry", "entry")):
            name = build + "/" + filename
            _bound(payload[name], result[key], file_limit(name), empty=key in {"stdout", "stderr"})
        need(payload[build + "/stdout.bin"] == b"", "entry_build_stdout_not_empty")
        try:
            containment.validate_entry(payload[build + "/entry"])
        except containment.ContainmentError as exc:
            raise BuildError(exc.code) from exc
    need(payload["build-1/entry"] == payload["build-2/entry"], "entry_build_outputs_differ")
    return {"format": "required_gate_idempotence_entry_build_verification_v0", "profile": PROFILE,
            "status": "accepted", "source_commit": source_commit, "request_sha256": expected_request_sha256,
            "record_sha256": expected_record_sha256, "entry": binding(payload["build-1/entry"]),
            "entry_build_record_verified": True, "repeat_build_equal": True,
            "entry_static_shape_verified": True, "toolchain_observations_stable": True, **BOUNDARY}


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _open_directory(path):
    path = Path(path)
    need(path.is_absolute() and ".." not in path.parts, "entry_build_directory_path_invalid")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_directory(path):
    """Read the exact successful roster through pinned directory descriptors.

    Transport can normalize permission bits; modes are not a proof of the
    original build directory. Symlinks, hardlinks and changing files reject.
    """
    root = _open_directory(Path(path).absolute())
    payload = {}

    def scan(fd, prefix):
        before = os.fstat(fd)
        expected = {name[len(prefix):].split("/", 1)[0] for name in (*FILES, "record.json") if name.startswith(prefix)}
        with os.scandir(fd) as entries:
            names = {entry.name for entry in entries}
        need(names == expected, "entry_build_inventory_mismatch")
        for name in sorted(names):
            relative = prefix + name
            if relative in BUILD_IDS:
                nested = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    scan(nested, relative + "/")
                finally:
                    os.close(nested)
            else:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
                try:
                    first = os.fstat(child)
                    maximum = file_limit(relative)
                    need(stat.S_ISREG(first.st_mode) and first.st_nlink == 1 and 0 <= first.st_size <= maximum,
                         "entry_build_regular_file_required")
                    data = bytearray()
                    while len(data) <= maximum:
                        raw = os.read(child, min(65536, maximum + 1 - len(data)))
                        if not raw:
                            break
                        data.extend(raw)
                    need(len(data) == first.st_size and _identity(first) == _identity(os.fstat(child)),
                         "entry_build_file_changed")
                    payload[relative] = bytes(data)
                finally:
                    os.close(child)
        need(_identity(before) == _identity(os.fstat(fd)), "entry_build_directory_changed")

    try:
        scan(root, "")
        # Reopen the user-visible path to detect substitution of the prefix.
        current = _open_directory(Path(path).absolute())
        try:
            need(_identity(os.fstat(current)) == _identity(os.fstat(root)), "entry_build_directory_changed")
        finally:
            os.close(current)
    finally:
        os.close(root)
    return payload


def check_directory(path, *, expected_request_sha256, expected_record_sha256, source_commit):
    return check_payload(read_directory(path), expected_request_sha256=expected_request_sha256,
                         expected_record_sha256=expected_record_sha256, source_commit=source_commit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--record-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    parent = None
    try:
        if args.output is not None:
            need(not args.output.absolute().is_relative_to(args.evidence_dir.absolute()),
                 "entry_build_verification_output_must_be_external")
            parent, name = containment.bootstrap.runtime.observation.safe._output_preflight(args.output)
        result = check_directory(args.evidence_dir, expected_request_sha256=args.request_sha256,
                                 expected_record_sha256=args.record_sha256, source_commit=args.source_commit)
        if parent is not None:
            containment.bootstrap.runtime.observation.safe._write_output(parent, name, canonical(result))
        sys.stdout.buffer.write(canonical(result))
        return 0
    except (BuildError, OSError, ValueError, containment.bootstrap.runtime.observation.safe.ContractError) as exc:
        sys.stdout.buffer.write(canonical({"format": "required_gate_idempotence_entry_build_verification_v0",
                                          "status": "rejected", "error_code": getattr(exc, "code", "entry_build_io_failed"),
                                          "entry_build_record_verified": False, "repeat_build_equal": False, **BOUNDARY}))
        return 1
    finally:
        if parent is not None:
            os.close(parent)


if __name__ == "__main__":
    raise SystemExit(main())
