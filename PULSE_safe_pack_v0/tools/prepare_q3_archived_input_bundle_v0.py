#!/usr/bin/env python3
"""Package explicitly selected Q3 input bytes, without scoring or granting authority.

The selection is a caller-controlled input made before scoring, not something
inferred from a report. Source authentication and label/runtime correctness are
not established here. Linux no-replace directory publication is required; there
is no overwrite or weaker publication fallback.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

TOOL_ID = "PULSE_q3_archived_input_preparation"
TOOL_VERSION = "0.1.0"
SOURCE_PATH = "PULSE_safe_pack_v0/tools/prepare_q3_archived_input_bundle_v0.py"
SELECTION_SCHEMA_PATH = "schemas/metrics/q3_archived_input_selection_v0.schema.json"
SELECTION_SCHEMA_SHA256 = "b50d558ca12af0044954cfdc907753f0b561cc0d7ca31c6aa1db261b35f29645"
PROFILE_ID = "q3_input_recomputation_v0.1"
PRODUCER_PATH = "PULSE_safe_pack_v0/tools/build_q3_reference_summary.py"
PRODUCER_SHA256 = "1662ff2a60664f19716162d77303353dd012a335f267a24a7aba29b58f54e5a7"
RESOURCE_PATHS = {
    "contract_sha256": "PULSE_safe_pack_v0/profiles/q3_reference_recomputation_v0.json",
    "input_schema_sha256": "schemas/metrics/q3_input_bundle_v0.schema.json",
    "result_schema_sha256": "schemas/metrics/q3_reference_summary_v0.schema.json",
    "dataset_manifest_schema_sha256": "schemas/dataset_manifest.schema.json",
    "q1_spec_sha256": "metrics/specs/q1_groundedness_v0.yml",
    "q3_spec_sha256": "metrics/specs/q3_fairness_v0.yml",
}
RESOURCE_SHA256 = {
    "contract_sha256": "e31e390d3ee5619bad082a6b04b7b556cfbed1690f97e35bc972816cb48db666",
    "input_schema_sha256": "41e235d887822e9f7ced148bd06c7cee7cb02984ebb9a59e3f333f11497350e5",
    "result_schema_sha256": "fd8caccf408192d11c086ef6ff7b932437dff91debba758eacc28daa0d1ddb1e",
    "dataset_manifest_schema_sha256": "7bd729958c65dfde432925a4d3fccbd50c846cca19c891411ed085166ecdfead",
    "q1_spec_sha256": "a63625ca894294e0fbe4febffdd143d22929dcaa44ea52a6aaa02453f0aac65f",
    "q3_spec_sha256": "58fc3ddbf636ffdcadc9ca3ce07e6051ff9801d49e9593b7c8e79970a08e782e",
}
ARTIFACT_NAMES = {
    "dataset_manifest": "dataset_manifest.json",
    "examples_jsonl": "examples.jsonl",
    "q1_labels_jsonl": "q1_labels.jsonl",
}
BUNDLE_RESOURCE_KEYS = tuple(list(RESOURCE_PATHS)[:4])
MAX_FILE_BYTES = 67_108_864
MAX_SELECTION_BYTES = 131_072
MAX_LINE_BYTES = 1_048_576
MAX_ROWS = 100_000
MAX_DIMENSIONS = 64
RELATIVE = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})"
)
CLAIMS = {
    "authority_effect": "none", "production_gate_eligible": False,
    "current_run_evidence": False, "source_authentication": "not_established",
    "label_correctness": "not_verified", "slice_metadata_correctness": "not_verified",
    "policy_activation": False, "metric_evaluated": False,
    "full_q3_semantics_verified": False,
    "selection_origin_authenticated": False,
}


class PreparationError(Exception):
    """Stable diagnostic; do not expose input contents in failure output."""
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.cleanup_complete: bool | None = None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("JSON_INVALID")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise PreparationError("JSON_INVALID")


def _finite(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise PreparationError("JSON_INVALID")
    return result


def _unicode(value: Any) -> None:
    if isinstance(value, str):
        value.encode("utf-8", "strict")
    elif isinstance(value, dict):
        for key, child in value.items():
            _unicode(key)
            _unicode(child)
    elif isinstance(value, list):
        for child in value:
            _unicode(child)


def strict_json(data: bytes) -> Any:
    try:
        if data.startswith(b"\xef\xbb\xbf"):
            raise PreparationError("JSON_INVALID")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=_constant, parse_float=_finite)
        _unicode(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PreparationError("JSON_INVALID") from exc


def _check_local_refs(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("$ref", "$dynamicRef") and (
                    not isinstance(child, str) or not child.startswith("#")):
                raise PreparationError("RESOURCE_BINDING_MISMATCH")
            _check_local_refs(child)
    elif isinstance(value, list):
        for child in value:
            _check_local_refs(child)


# Match the pinned producer locally; optional jsonschema plugins are not used.
FORMATS = FormatChecker(formats=[])


@FORMATS.checks("date")
def valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not DATE.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


@FORMATS.checks("date-time")
def valid_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not DATE_TIME.fullmatch(value):
        return False
    # RFC 3339 excludes hour 24 even when a runtime parser normalizes it.
    if int(value[11:13]) > 23:
        return False
    normalized = value.upper()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    else:
        # fromisoformat accepts overflowing offset minutes; RFC 3339 does not.
        if int(normalized[-5:-3]) > 23 or int(normalized[-2:]) > 59:
            return False
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
        return parsed.tzinfo is not None
    except ValueError:
        return False


def rule(schema: dict[str, Any], definition: str | None = None) -> Draft202012Validator:
    _check_local_refs(schema)
    Draft202012Validator.check_schema(schema)
    if definition:
        schema = {"$schema": schema["$schema"], "$defs": schema["$defs"],
                  "$ref": "#/$defs/" + definition}
    return Draft202012Validator(schema, format_checker=FORMATS)


def validate(value: Any, schema_rule: Draft202012Validator, code: str) -> None:
    try:
        schema_rule.validate(value)
    except Exception as exc:
        raise PreparationError(code) from exc


def absolute_path(path: Path) -> Path:
    # Reject traversal before abspath can erase it. Do not resolve symlinks.
    if any(part == ".." for part in path.parts) or "\x00" in os.fspath(path):
        raise PreparationError("UNSAFE_PATH")
    return Path(os.path.abspath(os.fspath(path)))


def relative_path(root: Path, value: str) -> Path:
    if (not isinstance(value, str) or not RELATIVE.fullmatch(value)
            or any(part in (".", "..") for part in value.split("/"))):
        raise PreparationError("UNSAFE_PATH")
    return absolute_path(root).joinpath(*value.split("/"))


def parent_directory(path: Path) -> tuple[int, str]:
    path = absolute_path(path)
    if not path.name:
        raise PreparationError("UNSAFE_PATH")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor, path.name
    except BaseException:
        os.close(descriptor)
        raise


def identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def inode(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


class Snapshots:
    """Immutable bounded bytes, rechecked on repeated paths and hardlink aliases."""
    def __init__(self) -> None:
        self.paths: dict[str, tuple[tuple[int, ...], bytes]] = {}
        self.inodes: dict[tuple[int, int], tuple[tuple[int, ...], bytes]] = {}

    def read(self, path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
        path = absolute_path(path)
        parent = descriptor = None
        try:
            parent, name = parent_directory(path)
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                                  | os.O_CLOEXEC, dir_fd=parent)
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise PreparationError("INPUT_UNAVAILABLE")
            if before.st_size > limit:
                raise PreparationError("INPUT_LIMIT")
            key = str(path)
            cached = self.paths.get(key) or self.inodes.get(inode(before))
            if cached is not None:
                if cached[0] != identity(before):
                    raise PreparationError("FILE_BINDING_MISMATCH")
                self.paths[key] = cached
                return cached[1]
            pieces = []
            length = 0
            while True:
                piece = os.read(descriptor, 65536)
                if not piece:
                    break
                length += len(piece)
                if length > limit:
                    raise PreparationError("INPUT_LIMIT")
                pieces.append(piece)
            after = os.fstat(descriptor)
            if identity(before) != identity(after) or length != before.st_size:
                raise PreparationError("FILE_BINDING_MISMATCH")
            data = b"".join(pieces)
            self.paths[key] = self.inodes[inode(before)] = (identity(after), data)
            return data
        except OSError as exc:
            raise PreparationError("INPUT_UNAVAILABLE") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if parent is not None:
                os.close(parent)

    def recheck(self) -> None:
        for path in tuple(self.paths):
            self.read(Path(path))


def load_resources(root: Path, snapshots: Snapshots) -> dict[str, bytes]:
    resources = {}
    for key, path in RESOURCE_PATHS.items():
        data = snapshots.read(relative_path(root, path))
        if sha256(data) != RESOURCE_SHA256[key]:
            raise PreparationError("RESOURCE_BINDING_MISMATCH")
        resources[key] = data
    return resources


def parse_rows(data: bytes, validator: Draft202012Validator) -> dict[str, tuple[dict, str]]:
    if (not data or not data.endswith(b"\n") or b"\r" in data
            or data.startswith(b"\xef\xbb\xbf")):
        raise PreparationError("INPUT_REPRESENTATION_INVALID")
    lines = data.split(b"\n")[:-1]
    if len(lines) > MAX_ROWS:
        raise PreparationError("INPUT_LIMIT")
    records = {}
    for line in lines:
        if not line or len(line) > MAX_LINE_BYTES:
            raise PreparationError("INPUT_REPRESENTATION_INVALID")
        value = strict_json(line)
        validate(value, validator, "INPUT_REPRESENTATION_INVALID")
        key = value["example_id"]
        if key in records:
            raise PreparationError("DUPLICATE_EXAMPLE_ID")
        records[key] = (value, sha256(line))
    return records


def preflight(selection: dict, artifacts: dict[str, bytes], input_schema: dict,
              manifest_schema: dict) -> None:
    """Check representation and byte joins, not eligibility/parity/metric truth."""
    manifest = strict_json(artifacts["dataset_manifest"])
    validate(manifest, rule(manifest_schema), "MANIFEST_INVALID")
    examples = parse_rows(artifacts["examples_jsonl"], rule(input_schema, "example_record"))
    labels = parse_rows(artifacts["q1_labels_jsonl"], rule(input_schema, "label_record"))
    dims = manifest.get("slices", {}).get("dimensions")
    if (not isinstance(dims, list) or not 1 <= len(dims) <= MAX_DIMENSIONS
            or any(not isinstance(d, str) or not d for d in dims)
            or len(set(dims)) != len(dims)):
        raise PreparationError("MANIFEST_INVALID")
    if (manifest["dataset_id"] != selection["dataset_id"]
            or manifest["sampling"]["n"] != len(examples)
            or "labels" not in manifest
            or manifest["hashes"]["input_sha256"].lower() != sha256(artifacts["examples_jsonl"])
            or manifest["hashes"].get("labels_sha256", "").lower() != sha256(artifacts["q1_labels_jsonl"])):
        raise PreparationError("MANIFEST_BINDING_MISMATCH")
    if examples.keys() != labels.keys():
        raise PreparationError("LABEL_JOIN_MISMATCH")
    examples_sha = sha256(artifacts["examples_jsonl"])
    for key, (label, _) in labels.items():
        if (label["examples_sha256"] != examples_sha
                or label["example_line_sha256"] != examples[key][1]):
            raise PreparationError("LABEL_BINDING_MISMATCH")


def selected_kind(selection: dict) -> str:
    kind = selection["observation_subject"]["kind"]
    origin = selection["selection_origin"]
    expected = {"archived_input": "caller_selected_archived_input",
                "synthetic_fixture": "synthetic_test_anchor"}[kind]
    if origin["kind"] != expected:
        raise PreparationError("SELECTION_ORIGIN_MISMATCH")
    runtime = selection["observation_subject"]["runtime_identity"]
    reference = origin["original_runtime_evidence_reference"]
    if (runtime is None) != (reference is None):
        raise PreparationError("RUNTIME_DECLARATION_MISMATCH")
    return expected


def describe(name: str, data: bytes) -> dict:
    return {"path": name, "sha256": sha256(data), "size_bytes": len(data)}


def build_package(selection_bytes: bytes, selection: dict, artifacts: dict[str, bytes],
                  resources: dict[str, bytes], preparer_source: bytes) -> dict[str, bytes]:
    bindings = {key: selection["resource_bindings"][key] for key in BUNDLE_RESOURCE_KEYS}
    specs = {}
    for role, key, version, spec_id in (
        ("q1", "q1_spec_sha256", "0.1.0", "q1_groundedness_v0"),
        ("q3_baseline", "q3_spec_sha256", "0.1.1", "q3_fairness_v0"),
    ):
        data = resources[key]
        specs[role] = {"spec_id": spec_id, "spec_version": version,
                       "repository_path": RESOURCE_PATHS[key],
                       "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode()
                                                    + b"\0" + data).hexdigest(),
                       "sha256": sha256(data)}
    subject_fields = {key: selection[key] for key in ("dataset_id", "reduction_id", "observation_subject")}
    bundle = {"record_type": "q3_input_bundle", "contract_profile": PROFILE_ID,
              **subject_fields, "artifacts": {
                  role: describe(name, artifacts[role]) for role, name in ARTIFACT_NAMES.items()},
              "spec_bindings": specs, "contract_bindings": bindings,
              "production_gate_eligible": False, "authority_effect": "none"}
    expected = {"record_type": "q3_expected_context", "contract_profile": PROFILE_ID,
                **subject_fields, **bindings, "input_bundle_sha256": sha256(canonical(bundle)),
                "expected_producer": selection["expected_producer"],
                "expectation_origin": selected_kind(selection), "authority_effect": "none"}
    input_schema = strict_json(resources["input_schema_sha256"])
    validate(bundle, rule(input_schema), "PACKAGE_SCHEMA_INVALID")
    validate(expected, rule(input_schema, "expected_context"), "PACKAGE_SCHEMA_INVALID")
    package = {name: artifacts[role] for role, name in ARTIFACT_NAMES.items()}
    package.update({"input_bundle.json": canonical(bundle),
                    "expected_context.json": canonical(expected),
                    "input_selection.json": selection_bytes})
    manifest = {
        "record_type": "q3_archived_input_preparation_manifest_v0",
        "preparation_result": "PREPARED", "selection_id": selection["selection_id"],
        "selection_sha256": sha256(selection_bytes), "selection_origin": selection["selection_origin"],
        "selection_schema_sha256": SELECTION_SCHEMA_SHA256,
        "original_runtime_identity_status": (
            "unavailable" if selection["observation_subject"]["runtime_identity"] is None
            else "caller_declared_not_verified"),
        "expected_producer_runtime_status": "caller_selected_not_executed",
        "structural_preflight": "representation_and_byte_joins_only",
        "preparer": {"tool_id": TOOL_ID, "tool_version": TOOL_VERSION,
                     "source_path": SOURCE_PATH, "source_sha256": sha256(preparer_source)},
        "members": [describe(name, data) for name, data in sorted(package.items())],
        "claims": CLAIMS,
    }
    package["preparation_manifest.json"] = canonical(manifest)
    return package


def ensure_platform() -> Any:
    required = ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")
    if not sys.platform.startswith("linux") or any(not hasattr(os, x) for x in required):
        raise PreparationError("UNSUPPORTED_FILESYSTEM")
    if any(fn not in os.supports_dir_fd for fn in (os.open, os.stat, os.unlink, os.mkdir, os.rmdir)):
        raise PreparationError("UNSUPPORTED_FILESYSTEM")
    try:
        rename = ctypes.CDLL(None, use_errno=True).renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        return rename
    except (AttributeError, OSError) as exc:
        raise PreparationError("UNSUPPORTED_FILESYSTEM") from exc


def rename_no_replace(function: Any, parent: int, old: str, new: str) -> None:
    if function(parent, os.fsencode(old), parent, os.fsencode(new), 1) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise PreparationError("OUTPUT_EXISTS")
        if error in (errno.ENOSYS, errno.EINVAL, errno.ENOTSUP):
            raise PreparationError("UNSUPPORTED_FILESYSTEM")
        raise OSError(error, "No-replace publication failed")


def check_parent_binding(path: Path, expected: tuple[int, int]) -> None:
    current, _ = parent_directory(path)
    try:
        if inode(os.fstat(current)) != expected:
            raise PreparationError("OUTPUT_BINDING_MISMATCH")
    finally:
        os.close(current)


def write_member(directory: int, name: str, data: bytes,
                 created: dict[str, tuple[int, int]]) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                          | os.O_CLOEXEC, 0o600, dir_fd=directory)
    try:
        created[name] = inode(os.fstat(descriptor))
        os.fchmod(descriptor, 0o600)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or inode(info) != created[name]
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise PreparationError("OUTPUT_BINDING_MISMATCH")
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError(errno.EIO, "Write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify_members(directory: int, package: dict[str, bytes],
                   created: dict[str, tuple[int, int]]) -> None:
    if set(os.listdir(directory)) != set(package):
        raise PreparationError("OUTPUT_BINDING_MISMATCH")
    for name, expected in package.items():
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                              | os.O_CLOEXEC, dir_fd=directory)
        try:
            before = os.fstat(descriptor)
            if (not stat.S_ISREG(before.st_mode) or inode(before) != created[name]
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_size != len(expected)):
                raise PreparationError("OUTPUT_BINDING_MISMATCH")
            hasher = hashlib.sha256()
            count = 0
            while True:
                piece = os.read(descriptor, 65536)
                if not piece:
                    break
                count += len(piece)
                if count > len(expected):
                    raise PreparationError("OUTPUT_BINDING_MISMATCH")
                hasher.update(piece)
            after = os.fstat(descriptor)
            if (identity(before) != identity(after) or stat.S_IMODE(after.st_mode) != 0o600
                    or count != len(expected) or hasher.hexdigest() != sha256(expected)):
                raise PreparationError("OUTPUT_BINDING_MISMATCH")
        finally:
            os.close(descriptor)


def check_output_directory(info: os.stat_result, expected: tuple[int, int]) -> None:
    if (not stat.S_ISDIR(info.st_mode) or inode(info) != expected
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise PreparationError("OUTPUT_BINDING_MISMATCH")


def cleanup_owned(parent: int, name: str, directory: int | None,
                  directory_identity: tuple[int, int],
                  created: dict[str, tuple[int, int]]) -> bool:
    """Best effort, nonrecursive. Preserve replacements and unrelated entries.

    An owned empty stage can be removed without reopening it after EMFILE or
    an initial open/fstat failure. Never infer ownership from a cleanup read.
    """
    if created and directory is None:
        return False
    complete = True
    ordered = sorted(created, key=lambda n: (n != "preparation_manifest.json", n))
    for member in ordered:
        try:
            current = os.stat(member, dir_fd=directory, follow_symlinks=False)
            if inode(current) != created[member] or not stat.S_ISREG(current.st_mode):
                complete = False
                continue
            os.unlink(member, dir_fd=directory)
        except FileNotFoundError:
            pass
        except OSError:
            complete = False
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode) and inode(info) == directory_identity:
            os.rmdir(name, dir_fd=parent)
        else:
            complete = False
    except FileNotFoundError:
        complete = False
    except OSError:
        complete = False
    return complete


def publish(package: dict[str, bytes], output: Path, rename_function: Any) -> None:
    parent = directory = None
    location = ""
    directory_identity = None
    staging_created = False
    created: dict[str, tuple[int, int]] = {}
    try:
        parent, final = parent_directory(output)
        parent_identity = inode(os.fstat(parent))
        try:
            os.stat(final, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise PreparationError("OUTPUT_EXISTS")
        location = ".q3-preparing-" + secrets.token_hex(16)
        os.mkdir(location, 0o700, dir_fd=parent)
        staging_created = True
        info = os.stat(location, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            raise PreparationError("OUTPUT_BINDING_MISMATCH")
        directory_identity = inode(info)
        # Restore owner access before opening: mkdir's mode is masked by umask.
        # The existing contract requires this parent to be caller-controlled.
        # Do not change the process-wide umask or follow a replacement symlink.
        os.chmod(location, 0o700, dir_fd=parent, follow_symlinks=False)
        check_output_directory(os.stat(location, dir_fd=parent, follow_symlinks=False),
                               directory_identity)
        directory = os.open(location, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                            | os.O_CLOEXEC, dir_fd=parent)
        check_output_directory(os.fstat(directory), directory_identity)
        for name in sorted(package, key=lambda n: (n == "preparation_manifest.json", n)):
            write_member(directory, name, package[name], created)
        verify_members(directory, package, created)
        check_output_directory(os.fstat(directory), directory_identity)
        os.fsync(directory)
        check_parent_binding(output, parent_identity)
        rename_no_replace(rename_function, parent, location, final)
        location = final
        os.fsync(parent)
        check_parent_binding(output, parent_identity)
        check_output_directory(os.stat(final, dir_fd=parent, follow_symlinks=False),
                               directory_identity)
        check_output_directory(os.fstat(directory), directory_identity)
        verify_members(directory, package, created)
    except BaseException as exc:
        complete = None
        if staging_created:
            complete = (cleanup_owned(parent, location, directory, directory_identity, created)
                        if directory_identity is not None else False)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        failure = exc if isinstance(exc, PreparationError) else PreparationError("OUTPUT_WRITE_FAILED")
        failure.cleanup_complete = complete
        if failure is exc:
            raise
        raise failure from exc
    finally:
        if directory is not None:
            os.close(directory)
        if parent is not None:
            os.close(parent)


def prepare(selection_path: Path, source_root: Path, resources_root: Path,
            producer_source_root: Path, output: Path) -> dict:
    rename_function = ensure_platform()
    snapshots = Snapshots()
    selection_schema_bytes = snapshots.read(relative_path(resources_root, SELECTION_SCHEMA_PATH))
    if sha256(selection_schema_bytes) != SELECTION_SCHEMA_SHA256:
        raise PreparationError("RESOURCE_BINDING_MISMATCH")
    selection_bytes = snapshots.read(selection_path, MAX_SELECTION_BYTES)
    selection = strict_json(selection_bytes)
    validate(selection, rule(strict_json(selection_schema_bytes)), "SELECTION_INVALID")
    selected_kind(selection)
    resources = load_resources(resources_root, snapshots)
    # Only source bytes are read. No producer/checker code is imported or run.
    producer = snapshots.read(relative_path(producer_source_root, PRODUCER_PATH))
    if sha256(producer) != PRODUCER_SHA256:
        raise PreparationError("PRODUCER_BINDING_MISMATCH")
    artifacts = {}
    for role in ARTIFACT_NAMES:
        selected = selection["artifacts"][role]
        data = snapshots.read(relative_path(source_root, selected["path"]))
        if len(data) != selected["size_bytes"] or sha256(data) != selected["sha256"]:
            raise PreparationError("FILE_BINDING_MISMATCH")
        artifacts[role] = data
    preflight(selection, artifacts, strict_json(resources["input_schema_sha256"]),
              strict_json(resources["dataset_manifest_schema_sha256"]))
    preparer_source = snapshots.read(Path(__file__))
    package = build_package(selection_bytes, selection, artifacts, resources, preparer_source)
    snapshots.recheck()
    publish(package, output, rename_function)
    return {"record_type": "q3_input_preparation_receipt_v0", "preparation_result": "PREPARED",
            "preparation_manifest_sha256": sha256(package["preparation_manifest.json"]),
            "selection_sha256": sha256(selection_bytes), "claims": dict(CLAIMS)}


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).absolute().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--resources-root", type=Path, default=root)
    parser.add_argument("--producer-source-root", type=Path, default=root)
    args = parser.parse_args(argv)
    try:
        receipt = prepare(args.selection, args.source_root, args.resources_root,
                          args.producer_source_root, args.out_dir)
    except PreparationError as exc:
        detail = "" if exc.cleanup_complete is None else (
            "; cleanup_complete=" + str(exc.cleanup_complete).lower())
        print("Q3_PREPARATION_FAILED: " + exc.code + detail, file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # Unexpected malformed data or operational failure never signals success.
        print("Q3_PREPARATION_FAILED: PREPARATION_FAILED", file=sys.stderr)
        return 2
    try:
        sys.stdout.buffer.write(canonical(receipt))
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        # Publication already completed; retain the package, but never claim a
        # delivered acknowledgement. Do not retry by overwriting this directory.
        print("Q3_PREPARATION_FAILED: RECEIPT_WRITE_FAILED", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
