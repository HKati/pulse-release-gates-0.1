"""Bounded offline membership checks for one selected Debian package member.

This deliberately narrow reader accepts exactly the three ordinary ar members
of a v2 Debian package, with uncompressed, gzip or xz control/data tar archives.
It accepts ordinary v7, GNU and POSIX ustar headers, but no PAX, GNU long-name,
sparse, device or other extension records. It never extracts, follows a link,
executes package code, invokes a package manager or authenticates distribution
origin. A caller must independently select the original package digest.
"""
from __future__ import annotations

import hashlib
import lzma
import re
import zlib

PACKAGE_LIMIT = 32 * 1024 * 1024
TAR_LIMIT = 128 * 1024 * 1024
CONTROL_TAR_LIMIT = 4 * 1024 * 1024
CONTROL_LIMIT = 256 * 1024
MEMBER_LIMIT = 16 * 1024 * 1024
MEMBER_COUNT_LIMIT = 4096
XZ_MEMORY_LIMIT = 64 * 1024 * 1024
_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]{0,127}\Z")
_VERSION = re.compile(r"[0-9][A-Za-z0-9.+:~\-]{0,127}\Z")
_ARCHITECTURE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_FIELD = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}\Z")


class PackageError(ValueError):
    """Stable rejection code without inspected package content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise PackageError(code)


def _binding(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _number(raw, base, code, *, empty=False):
    value = raw.strip(b" \0")
    if not value and empty:
        return 0
    alphabet = b"01234567" if base == 8 else b"0123456789"
    _need(bool(value) and all(character in alphabet for character in value), code)
    return int(value, base)


def _ar(raw):
    _need(type(raw) is bytes and 8 <= len(raw) <= PACKAGE_LIMIT,
          "launcher_package_size_limit")
    _need(raw[:8] == b"!<arch>\n", "launcher_package_ar_magic")
    members = []
    offset = 8
    while offset < len(raw):
        _need(len(members) < 3 and len(raw) - offset >= 60,
              "launcher_package_ar_roster")
        header = raw[offset:offset + 60]
        _need(header[58:] == b"`\n" and all(32 <= value <= 126 for value in header[:58]),
              "launcher_package_ar_header")
        try:
            name = header[:16].decode("ascii").rstrip(" ")
        except UnicodeError as exc:
            raise PackageError("launcher_package_ar_name") from exc
        if name.endswith("/"):
            name = name[:-1]
        _need(re.fullmatch(r"[a-z][a-z0-9.-]{0,14}", name) is not None,
              "launcher_package_ar_name")
        for field in (header[16:28], header[28:34], header[34:40]):
            _number(field, 10, "launcher_package_ar_header")
        _number(header[40:48], 8, "launcher_package_ar_header")
        size = _number(header[48:58], 10, "launcher_package_ar_header")
        start = offset + 60
        _need(size <= len(raw) - start, "launcher_package_ar_truncated")
        members.append((name, raw[start:start + size]))
        offset = start + size
        if size % 2:
            _need(raw[offset:offset + 1] == b"\n", "launcher_package_ar_padding")
            offset += 1
    _need(len(members) == 3 and members[0] == ("debian-binary", b"2.0\n"),
          "launcher_package_ar_roster")
    for index, prefix in ((1, "control.tar"), (2, "data.tar")):
        _need(members[index][0] in {prefix, prefix + ".gz", prefix + ".xz"},
              "launcher_package_compression_unsupported")
    return members


def _decompress(name, raw, limit):
    if name.endswith(".tar"):
        _need(len(raw) <= limit, "launcher_package_tar_size_limit")
        return raw
    try:
        if name.endswith(".gz"):
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            result = decoder.decompress(raw, limit + 1)
        else:
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ,
                                          memlimit=XZ_MEMORY_LIMIT)
            result = decoder.decompress(raw, max_length=limit + 1)
        _need(len(result) <= limit, "launcher_package_tar_size_limit")
        # A single complete stream is required: neither a hidden second stream
        # nor bytes following the compressed archive may be silently ignored.
        _need(decoder.eof and not decoder.unused_data,
              "launcher_package_compression_invalid")
        return result
    except (lzma.LZMAError, zlib.error, EOFError) as exc:
        raise PackageError("launcher_package_compression_invalid") from exc


def _text(raw):
    value, separator, padding = raw.partition(b"\0")
    _need(not separator or not any(padding), "launcher_package_tar_text_invalid")
    _need(all(32 <= character <= 126 for character in value),
          "launcher_package_tar_text_invalid")
    return value.decode("ascii")


def _path(value, *, directory=False):
    _need(type(value) is str and 0 < len(value) <= 256 and "\\" not in value,
          "launcher_package_member_path")
    if directory and value in {".", "./"}:
        return ""
    if value.startswith("./"):
        value = value[2:]
    if directory and value.endswith("/"):
        value = value[:-1]
    _need(value and not value.startswith("/") and
          all(part not in {"", ".", ".."} for part in value.split("/")) and
          all(33 <= ord(character) <= 126 for character in value),
          "launcher_package_member_path")
    return value


def _tar(raw, selected, limit):
    _need(1024 <= len(raw) <= limit and len(raw) % 512 == 0,
          "launcher_package_tar_size_limit")
    entries = {}
    found = None
    offset = 0
    while offset < len(raw):
        header = raw[offset:offset + 512]
        if not any(header):
            _need(len(raw) - offset >= 1024 and not any(raw[offset:]),
                  "launcher_package_tar_trailing_data")
            break
        _need(len(entries) < MEMBER_COUNT_LIMIT, "launcher_package_tar_member_limit")
        checksum = _number(header[148:156], 8, "launcher_package_tar_checksum")
        _need(checksum == sum(header[:148]) + 8 * 32 + sum(header[156:]),
              "launcher_package_tar_checksum")
        magic = header[257:265]
        if magic == b"ustar\x0000":
            prefix = _text(header[345:500])
            _need(not any(header[500:]), "launcher_package_tar_extension_unsupported")
        elif magic == b"ustar  \x00":
            # GNU's tail is not a POSIX prefix. Any GNU extra metadata here
            # would need its own supported semantics; do not reinterpret it.
            _need(not any(header[345:]), "launcher_package_tar_extension_unsupported")
            prefix = ""
        else:
            _need(not any(header[257:]), "launcher_package_tar_format_unsupported")
            prefix = ""
        kind = header[156:157]
        _need(kind in {b"\0", b"0", b"1", b"2", b"5"},
              "launcher_package_tar_extension_unsupported")
        name = _text(header[:100])
        if prefix:
            name = prefix + "/" + name
        path = _path(name, directory=kind == b"5")
        _need(path not in entries, "launcher_package_tar_duplicate_path")
        mode = _number(header[100:108], 8, "launcher_package_tar_mode")
        _need(mode <= 0o7777, "launcher_package_tar_mode")
        for field in (header[108:116], header[116:124], header[136:148]):
            _number(field, 8, "launcher_package_tar_number", empty=True)
        size = _number(header[124:136], 8, "launcher_package_tar_number", empty=True)
        regular = kind in {b"\0", b"0"}
        _need(regular or size == 0, "launcher_package_tar_nonregular_payload")
        link = _text(header[157:257])
        _need(bool(link) if kind in {b"1", b"2"} else not link,
              "launcher_package_tar_link_invalid")
        start = offset + 512
        end = start + size
        padded = start + ((size + 511) // 512) * 512
        _need(padded <= len(raw), "launcher_package_tar_truncated")
        _need(not any(raw[end:padded]), "launcher_package_tar_padding")
        entries[path] = kind
        if path == selected:
            _need(regular, "launcher_package_selected_member_not_regular")
            maximum = CONTROL_LIMIT if selected == "control" else MEMBER_LIMIT
            _need(0 < size <= maximum, "launcher_package_selected_member_size")
            found = (raw[start:end], mode)
        offset = padded
    else:
        raise PackageError("launcher_package_tar_terminator_missing")
    for path in entries:
        parts = path.split("/")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            _need(parent not in entries or entries[parent] == b"5",
                  "launcher_package_tar_ancestor_not_directory")
    _need(found is not None, "launcher_package_selected_member_missing")
    return found, len(entries)


def _control(raw):
    _need(0 < len(raw) <= CONTROL_LIMIT and raw.endswith(b"\n") and b"\r" not in raw,
          "launcher_package_control_invalid")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise PackageError("launcher_package_control_invalid") from exc
    _need(all(character in "\n\t" or ord(character) >= 32 for character in text),
          "launcher_package_control_invalid")
    fields = {}
    previous = None
    ended = False
    for line in text.split("\n"):
        _need(len(line) <= 16384, "launcher_package_control_line_limit")
        if not line:
            ended = True
            continue
        _need(not ended, "launcher_package_control_multiple_paragraphs")
        if line[0] in " \t":
            _need(previous is not None and previous not in {"package", "version", "architecture"},
                  "launcher_package_control_identity_continuation")
            continue
        name, separator, value = line.partition(":")
        _need(separator and _FIELD.fullmatch(name) is not None,
              "launcher_package_control_field_invalid")
        previous = name.lower()
        _need(previous not in fields, "launcher_package_control_duplicate_field")
        fields[previous] = value.strip(" \t")
    result = {"name": fields.get("package"), "version": fields.get("version"),
              "architecture": fields.get("architecture")}
    for key, pattern in (("name", _NAME), ("version", _VERSION), ("architecture", _ARCHITECTURE)):
        _need(type(result[key]) is str and pattern.fullmatch(result[key]) is not None,
              "launcher_package_control_identity_invalid")
    return result


def inspect_package(raw, *, member_path, expected_name, expected_version, expected_architecture):
    """Bind one plain member to an exact original package and control identity.

    ``member_path`` is canonical and relative (for example ``usr/bin/bwrap``).
    Raw tar names may have a single leading ``./``. Links elsewhere are recorded
    only as headers and never followed; a selected link or non-directory ancestor
    rejects. All PAX/GNU extension records and unsupported compression reject.
    The returned ``member_bytes`` is the sole selected payload, kept in memory.
    """
    _need(_path(member_path) == member_path, "launcher_package_member_path")
    expected = {"name": expected_name, "version": expected_version,
                "architecture": expected_architecture}
    for key, pattern in (("name", _NAME), ("version", _VERSION), ("architecture", _ARCHITECTURE)):
        _need(type(expected[key]) is str and pattern.fullmatch(expected[key]) is not None,
              "launcher_package_expected_identity_invalid")
    members = _ar(raw)
    control_tar = _decompress(*members[1], CONTROL_TAR_LIMIT)
    (control_bytes, _), control_count = _tar(control_tar, "control", CONTROL_TAR_LIMIT)
    control = _control(control_bytes)
    _need(control == expected, "launcher_package_control_identity_mismatch")
    data_tar = _decompress(*members[2], TAR_LIMIT - len(control_tar))
    (selected, mode), data_count = _tar(data_tar, member_path, TAR_LIMIT - len(control_tar))
    _need(control_count + data_count <= MEMBER_COUNT_LIMIT, "launcher_package_tar_member_limit")
    return {"package": _binding(raw), "control": control,
            "member": {"path": member_path, **_binding(selected), "mode": format(mode, "04o")},
            "member_bytes": selected,
            "archive_members": [{"name": name, **_binding(value)} for name, value in members],
            "tar_archives": [{"name": members[index][0], **_binding(value), "member_count": count}
                             for index, value, count in ((1, control_tar, control_count),
                                                         (2, data_tar, data_count))]}
