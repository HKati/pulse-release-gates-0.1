"""Small fail-closed primitives shared by the isolated QRH 003 audit.

Canonicalization is explicitly this implementation's sorted compact JSON, not
an assertion of RFC 8785 conformance. No module executes repository code.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import stat

SUBJECT_COMMIT = "adc7f1241b42e322a6451854ab7e4b4c146bf78a"
PULSE_COMMIT = "288bb9a45764d2a30f72fdf4c417e9dd5b3087c5"
GATE_IDS = (
    "qrh003_subject_bound", "qrh003_scope_bound",
    "qrh003_source_closure_verified", "qrh003_build_closure_verified",
    "qrh003_clean_builds_verified", "qrh003_formal_match_verified",
    "qrh003_axioms_verified", "qrh003_execution_isolation_verified",
    "qrh003_input_policy_binding_verified", "qrh003_certificate_boundary_verified",
    "qrh003_claim_semantics_verified", "qrh003_independent_lean_review_verified",
    "qrh003_independent_domain_review_verified",
)


class AuditError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code + (": " + self.detail if self.detail else ""))


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("DUPLICATE_JSON_KEY", key)
        result[key] = value
    return result


def strict_loads(data: bytes):
    if not isinstance(data, bytes):
        raise AuditError("JSON_INPUT_NOT_BYTES")
    try:
        result = json.loads(
            data.decode("utf-8", "strict"), object_pairs_hook=_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                AuditError("NONFINITE_JSON_NUMBER", value)),
        )
        _json_types(result)
        return result
    except AuditError:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise AuditError("INVALID_JSON", str(exc)) from exc


def _json_types(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_types(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_types(item)
        return
    raise AuditError("NONCANONICAL_JSON_TYPE", type(value).__name__)


def canonical_bytes(obj) -> bytes:
    _json_types(obj)
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise AuditError("CANONICAL_JSON_FAILED", str(exc)) from exc


canonical_json = canonical_bytes


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _open_dir(path) -> int:
    """Walk even the root path without following any symlink component."""
    full = os.path.abspath(os.fspath(path))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in full.split("/")[1:]:
            if not component:
                continue
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY |
                          os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except OSError as exc:
        os.close(fd)
        raise AuditError("UNSAFE_OR_MISSING_DIRECTORY", full) from exc


def _components(relative_path):
    raw = os.fspath(relative_path)
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw:
        raise AuditError("UNSAFE_PATH", str(raw))
    parts = raw.split("/")
    if any(part in ("", ".", "..") or "\x00" in part for part in parts):
        raise AuditError("UNSAFE_PATH", raw)
    return parts


def secure_read(root, relative_path, max_bytes=134217728) -> bytes:
    parts = _components(relative_path)
    parent = _open_dir(root)
    handle = None
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                          os.O_CLOEXEC, dir_fd=parent)
            os.close(parent)
            parent = nxt
        handle = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                         dir_fd=parent)
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode):
            raise AuditError("NONREGULAR_ARTIFACT", str(relative_path))
        if before.st_size > max_bytes:
            raise AuditError("ARTIFACT_TOO_LARGE", str(relative_path))
        chunks, size = [], 0
        while True:
            chunk = os.read(handle, min(1048576, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise AuditError("ARTIFACT_TOO_LARGE", str(relative_path))
        after = os.fstat(handle)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                    after.st_mtime_ns, after.st_ctime_ns):
            raise AuditError("ARTIFACT_CHANGED_DURING_READ", str(relative_path))
        return b"".join(chunks)
    except AuditError:
        raise
    except OSError as exc:
        raise AuditError("UNSAFE_OR_MISSING_ARTIFACT", str(relative_path)) from exc
    finally:
        if handle is not None:
            os.close(handle)
        os.close(parent)


def read_json(path):
    p = Path(path).absolute()
    return strict_loads(secure_read(p.parent, p.name))


def sha256_file(path) -> str:
    """Stream large archives while rejecting a symlink at every path level."""
    p = Path(path).absolute()
    parent = _open_dir(p.parent)
    fd = None
    try:
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                     dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise AuditError("NONREGULAR_ARTIFACT", str(p))
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1048576):
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                    after.st_mtime_ns, after.st_ctime_ns):
            raise AuditError("ARTIFACT_CHANGED_DURING_READ", str(p))
        return digest.hexdigest()
    except OSError as exc:
        raise AuditError("UNSAFE_OR_MISSING_ARTIFACT", str(p)) from exc
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def exclusive_write(path, data: bytes):
    """Publish complete bytes atomically, never replace a previous artifact."""
    if not isinstance(data, bytes):
        raise AuditError("WRITE_INPUT_NOT_BYTES")
    p = Path(path).absolute()
    _components(p.name)
    parent = _open_dir(p.parent)
    temporary = ".qrh-write-" + secrets.token_hex(16)
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, p.name, src_dir_fd=parent, dst_dir_fd=parent,
                follow_symlinks=False)
        os.fsync(parent)
    except OSError as exc:
        raise AuditError("EXCLUSIVE_WRITE_FAILED", str(p)) from exc
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


def write_json(path, obj):
    exclusive_write(path, canonical_bytes(obj) + b"\n")


def verify_signed_receipt(payload_bytes, signature_hex, public_key_hex) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        key.verify(bytes.fromhex(signature_hex), payload_bytes)
        return True
    except Exception:
        return False
