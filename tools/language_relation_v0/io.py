"""Bounded, strict, offline I/O shared by LRM verification components."""

from __future__ import annotations

from functools import lru_cache
import errno
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 80
MAX_JSON_NODES = 100_000


class InputError(ValueError):
    """Invalid or unsupported input/configuration, not a relation diagnosis."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    value: dict = {}
    for key, child in pairs:
        if key in value:
            raise InputError(f"duplicate JSON key: {key!r}")
        value[key] = child
    return value


def _nonfinite(value: str) -> None:
    raise InputError(f"non-finite JSON number: {value}")


def strict_json(data: bytes) -> dict:
    if len(data) > MAX_JSON_BYTES:
        raise InputError("JSON byte limit exceeded")
    if data.startswith(b"\xef\xbb\xbf"):
        raise InputError("JSON UTF-8 BOM is not permitted")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_nonfinite)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(f"invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("JSON document must be an object")
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_NODES:
            raise InputError("JSON structure resource limit exceeded")
        if isinstance(node, str):
            try:
                node.encode("utf-8")
            except UnicodeError as exc:
                raise InputError("unpaired Unicode surrogate in JSON") from exc
        elif isinstance(node, float) and not math.isfinite(node):
            raise InputError("non-finite JSON number")
        elif isinstance(node, dict):
            pending.extend((key, depth + 1) for key in node)
            pending.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)
    return value


def relative_path(value: str) -> tuple[str, ...]:
    """Accept one unambiguous POSIX package locator, never a URL or escape."""
    parts = value.split("/")
    if (not value or "\\" in value or "\x00" in value or ":" in value
            or PurePosixPath(value).is_absolute()
            or any(part in ("", ".", "..") for part in parts)):
        raise InputError(f"unsafe relative path: {value!r}")
    return tuple(parts)


def safe_read(root: Path, locator: str, *, limit: int = MAX_JSON_BYTES) -> bytes:
    """Read a regular file under root with no symlink traversal or FIFO wait.

    The caller selects the root. Every package-controlled path component is
    opened relative to a directory descriptor with O_NOFOLLOW on Linux.
    """
    parts = relative_path(locator)
    directory = os.open(Path(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
            except OSError as exc:
                if exc.errno not in (errno.ELOOP, errno.ENOTDIR):
                    raise
                raise InputError(f"unreadable or unsafe path component: {part}") from exc
            os.close(directory)
            directory = child
        try:
            descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                 dir_fd=directory)
        except OSError as exc:
            if exc.errno not in (errno.ELOOP, errno.ENOTDIR):
                raise
            raise InputError(f"unreadable or unsafe package file: {locator}") from exc
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise InputError(f"not a regular file: {locator}")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise InputError(f"file byte limit exceeded: {locator}")
            return data
    finally:
        os.close(directory)


def read_input(path: Path, package_root: Path) -> bytes:
    root = Path(package_root).resolve(strict=True)
    # Do not resolve the final path before safe_read: that would hide symlinks.
    absolute = Path(os.path.abspath(path))
    try:
        locator = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise InputError("input file must be inside package_root") from exc
    return safe_read(root, locator)


@lru_cache(maxsize=8)
def validator(name: str) -> Draft202012Validator:
    allowed = {
        "language_relation_input_v0.schema.json",
        "language_relation_verification_v0.schema.json",
        "language_relation_evidence_v0.schema.json",
    }
    if name not in allowed:
        raise InputError("unknown local schema")
    schema = strict_json(safe_read(ROOT / "schemas", name))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_schema(value: dict, name: str) -> None:
    try:
        error = next(validator(name).iter_errors(value), None)
    except RecursionError as exc:
        raise InputError("schema validation depth exceeded") from exc
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        # A recursive oneOf error can contain a very large representation.
        raise InputError(f"schema violation at {location}: {error.message[:300]}")


_RECORD_KEYS = {
    "sources": "source_id", "source_anchors": "anchor_id",
    "entities": "entity_id", "domains": "domain_id", "relations": "relation_id",
    "groups": "group_id", "variants": "variant_id", "targets": "target_id",
    "correspondence": "correspondence_id", "coverage_obligations": "obligation_id",
    "claims": "claim_id", "rules": "rule_id", "checks": "check_id",
    "basis_records": "side", "entries": "entry_id", "source_bindings": "source_id",
}


def _ordered(value: object, key: str = "") -> object:
    if isinstance(value, dict):
        return {name: _ordered(child, name) for name, child in value.items()}
    if isinstance(value, list):
        items = [_ordered(child) for child in value]
        if (key.endswith("_ids") or key == "evidence_refs") and all(
                isinstance(child, str) for child in items):
            return sorted(items)
        primary = _RECORD_KEYS.get(key)
        if primary and all(isinstance(child, dict) and primary in child for child in items):
            return sorted(items, key=lambda child: child[primary])
        return items
    return value


def canonical_bytes(value: dict) -> bytes:
    """Profile-defined JSON, not JCS; ordered arguments/operands stay ordered."""
    return (json.dumps(_ordered(value), ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def unique_index(rows: list[dict], field: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        key = row[field]
        if key in result:
            raise InputError(f"duplicate {field}: {key}")
        result[key] = row
    return result
