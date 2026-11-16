#!/usr/bin/env python3
"""Reconstruct a bounded Debian Release -> full Packages -> package byte chain.

This module does not authenticate signatures or trust roots. Its caller must
verify the exact original Release bytes under an independently selected policy.
It neither downloads, installs nor executes any package content.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import lzma
import re

RELEASE_LIMIT = 1024 * 1024
INDEX_COMPRESSED_LIMIT = 16 * 1024 * 1024
INDEX_DECODED_LIMIT = 128 * 1024 * 1024
XZ_MEMORY_LIMIT = 64 * 1024 * 1024
LINE_LIMIT = 128 * 1024
STANZA_LIMIT = 256 * 1024
MAX_PACKAGE_STANZAS = 250000
MAX_DIGEST_ROWS = 16384
MAX_EPOCH = 4102444800
MAX_RELEASE_AGE = 31622400
HASH = re.compile(r"[0-9a-f]{64}\Z")
FIELD = re.compile(rb"[A-Za-z0-9][A-Za-z0-9-]*\Z")
CONTROL = re.compile(rb"[\x00-\x08\x0a-\x1f\x7f]")
TOKEN = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
PACKAGE_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]*\Z")
PATH_PART = re.compile(r"[A-Za-z0-9_+~.-]+\Z")
DATE = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([0-9]{2}) "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"([0-9]{4}) ([0-9]{2}):([0-9]{2}):([0-9]{2}) (UTC|GMT|\+0000)\Z"
)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
REPOSITORY_KEYS = {"origin", "label", "suite", "codename", "version", "component", "architecture"}
PACKAGE_KEYS = {"name", "version", "architecture", "filename", "sha256", "size_bytes"}


class MetadataError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise MetadataError("distribution_metadata_" + code)


def binding(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _path(value):
    return (type(value) is str and 0 < len(value) <= 500
            and all(part not in {"", ".", ".."} and PATH_PART.fullmatch(part)
                    for part in value.split("/")))


def _ascii(value):
    return type(value) is str and 0 < len(value) <= 500 and all(32 <= ord(char) <= 126 for char in value)


def _decimal(value, code):
    need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]{0,18})", value) is not None, code)
    result = int(value)
    need(result < 2**63, code)
    return result


def _descriptor(value, maximum):
    return (type(value) is dict and set(value) == {"path", "sha256", "size_bytes"}
            and _path(value["path"]) and type(value["sha256"]) is str
            and HASH.fullmatch(value["sha256"]) is not None
            and type(value["size_bytes"]) is int and 0 < value["size_bytes"] <= maximum)


def _paragraphs(raw, *, stanza_limit, maximum):
    """Yield complete original paragraphs without materializing an index of them."""
    stream = io.BytesIO(raw)
    rows, size, count = [], 0, 0
    while True:
        line = stream.readline(LINE_LIMIT + 2)
        if not line:
            if rows:
                count += 1
                need(count <= maximum, "paragraph_limit")
                yield rows
            return
        value = line[:-1] if line.endswith(b"\n") else line
        need(len(value) <= LINE_LIMIT, "line_limit")
        need(CONTROL.search(value) is None, "control_character")
        if value == b"":
            if rows:
                count += 1
                need(count <= maximum, "paragraph_limit")
                yield rows
                rows, size = [], 0
            continue
        size += len(line)
        need(size <= stanza_limit, "stanza_limit")
        rows.append(value)


def _fields(lines):
    result, current = {}, None
    for line in lines:
        try:
            if line[:1] in (b" ", b"\t"):
                need(current is not None, "orphan_continuation")
                result[current].append(line[1:].decode("utf-8").strip(" \t"))
                continue
            need(b":" in line, "field_syntax")
            name, value = line.split(b":", 1)
            need(FIELD.fullmatch(name) is not None, "field_name")
            current = name.decode("ascii").lower()
            need(current not in result, "duplicate_field")
            result[current] = [value.decode("utf-8").strip(" \t")]
        except UnicodeError as exc:
            raise MetadataError("distribution_metadata_text_encoding") from exc
    return result


def _single(fields, name):
    values = fields.get(name)
    need(type(values) is list and len(values) == 1 and _ascii(values[0]),
         "identity_field_" + name)
    return values[0]


def _date(value):
    matched = DATE.fullmatch(value)
    need(matched is not None, "date_format")
    weekday, day, month, year, hour, minute, second, _zone = matched.groups()
    try:
        parsed = datetime(int(year), MONTHS.index(month) + 1, int(day),
                          int(hour), int(minute), int(second), tzinfo=timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise MetadataError("distribution_metadata_date_invalid") from exc
    need(WEEKDAYS[parsed.weekday()] == weekday, "date_weekday")
    epoch = int(parsed.timestamp())
    need(0 < epoch <= MAX_EPOCH, "date_range")
    return epoch


def _digest_rows(fields, name, digits):
    values = fields.get(name)
    need(type(values) is list and values, "digest_field_" + name)
    result = {}
    for number, row in enumerate(values):
        if number == 0 and row == "":
            continue
        need(row and all(32 <= ord(char) <= 126 or char == "\t" for char in row),
             "digest_row")
        parts = row.split()
        need(len(parts) == 3, "digest_row")
        digest, size_text, path = parts
        need(re.fullmatch(r"[0-9a-f]{" + str(digits) + r"}", digest) is not None
             and _path(path), "digest_row")
        size = _decimal(size_text, "digest_size")
        need(path not in result, "digest_path_duplicate")
        need(len(result) < MAX_DIGEST_ROWS, "digest_row_limit")
        result[path] = {"path": path, "sha256" if name == "sha256" else name: digest,
                        "size_bytes": size}
    need(result, "digest_field_empty")
    return result


def _decode_index(raw):
    need(type(raw) is bytes and 0 < len(raw) <= INDEX_COMPRESSED_LIMIT,
         "compressed_index_size")
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=XZ_MEMORY_LIMIT)
        decoded = decoder.decompress(raw, max_length=INDEX_DECODED_LIMIT + 1)
        need(0 < len(decoded) <= INDEX_DECODED_LIMIT, "decoded_index_size")
        need(decoder.eof and not decoder.unused_data, "xz_stream")
    except lzma.LZMAError as exc:
        raise MetadataError("distribution_metadata_xz_invalid") from exc
    return decoded


def _package_row(fields):
    name = _single(fields, "package")
    version = _single(fields, "version")
    architecture = _single(fields, "architecture")
    filename = _single(fields, "filename")
    size = _decimal(_single(fields, "size"), "package_size")
    digest = _single(fields, "sha256")
    need(PACKAGE_NAME.fullmatch(name) is not None and TOKEN.fullmatch(architecture) is not None
         and _path(filename) and filename.startswith("pool/") and filename.endswith(".deb")
         and HASH.fullmatch(digest) is not None and size > 0, "package_fields")
    return {"name": name, "version": version, "architecture": architecture,
            "filename": filename, "sha256": digest, "size_bytes": size}


def inspect_metadata(*, release_bytes, packages_xz_bytes, repository, index, package,
                     evaluation_time, max_release_age_seconds, require_valid_until):
    need(type(release_bytes) is bytes and 0 < len(release_bytes) <= RELEASE_LIMIT, "release_size")
    need(type(repository) is dict and set(repository) == REPOSITORY_KEYS
         and all(_ascii(value) for value in repository.values())
         and TOKEN.fullmatch(repository["component"]) is not None
         and TOKEN.fullmatch(repository["architecture"]) is not None, "repository_selection")
    need(type(index) is dict and set(index) == {"compressed", "decoded"}
         and _descriptor(index["compressed"], INDEX_COMPRESSED_LIMIT)
         and _descriptor(index["decoded"], INDEX_DECODED_LIMIT), "index_selection")
    prefix = repository["component"] + "/binary-" + repository["architecture"] + "/Packages"
    need(index["compressed"]["path"] == prefix + ".xz" and index["decoded"]["path"] == prefix,
         "index_path_selection")
    need(type(package) is dict and set(package) == PACKAGE_KEYS
         and all(_ascii(package[key]) for key in PACKAGE_KEYS - {"size_bytes"})
         and PACKAGE_NAME.fullmatch(package["name"]) is not None
         and package["architecture"] == repository["architecture"]
         and _path(package["filename"])
         and package["filename"].startswith("pool/" + repository["component"] + "/")
         and package["filename"].endswith(".deb")
         and HASH.fullmatch(package["sha256"]) is not None
         and type(package["size_bytes"]) is int and 0 < package["size_bytes"] < 2**63,
         "package_selection")
    need(type(evaluation_time) is int and 0 < evaluation_time <= MAX_EPOCH
         and type(max_release_age_seconds) is int and 1 <= max_release_age_seconds <= MAX_RELEASE_AGE
         and type(require_valid_until) is bool, "time_policy")

    paragraphs = list(_paragraphs(release_bytes, stanza_limit=RELEASE_LIMIT, maximum=2))
    need(len(paragraphs) == 1, "release_paragraph_count")
    fields = _fields(paragraphs[0])
    for name in ("origin", "label", "suite", "codename", "version"):
        need(_single(fields, name) == repository[name], "release_identity_" + name)
    for field, selected in (("components", repository["component"]),
                            ("architectures", repository["architecture"])):
        tokens = _single(fields, field).split()
        need(tokens and all(TOKEN.fullmatch(token) is not None for token in tokens)
             and len(tokens) == len(set(tokens)) and selected in tokens, "release_" + field)
    released_at = _date(_single(fields, "date"))
    valid_until = _date(_single(fields, "valid-until")) if "valid-until" in fields else None
    need(released_at <= evaluation_time, "release_in_future")
    need(evaluation_time - released_at <= max_release_age_seconds, "release_too_old")
    need(not require_valid_until or valid_until is not None, "valid_until_required")
    if valid_until is not None:
        need(valid_until >= released_at, "valid_until_before_release")
        need(evaluation_time <= valid_until, "release_expired")
    digests = _digest_rows(fields, "sha256", 64)
    for field, digits in (("md5sum", 32), ("sha1", 40), ("sha512", 128)):
        if field in fields:
            _digest_rows(fields, field, digits)
    for name in ("compressed", "decoded"):
        selected = index[name]
        need(digests.get(selected["path"]) == selected, "release_index_binding")

    need(type(packages_xz_bytes) is bytes
         and 0 < len(packages_xz_bytes) <= INDEX_COMPRESSED_LIMIT
         and binding(packages_xz_bytes) == {
             key: index["compressed"][key] for key in ("sha256", "size_bytes")
         }, "compressed_index_binding")
    decoded = _decode_index(packages_xz_bytes)
    need(binding(decoded) == {key: index["decoded"][key] for key in ("sha256", "size_bytes")},
         "decoded_index_binding")
    found, count = None, 0
    for lines in _paragraphs(decoded, stanza_limit=STANZA_LIMIT, maximum=MAX_PACKAGE_STANZAS):
        count += 1
        row = _package_row(_fields(lines))
        if all(row[key] == package[key] for key in ("name", "version", "architecture")):
            need(found is None, "package_ambiguous")
            found = row
    need(found is not None, "package_missing")
    need(found == package, "index_package_binding")
    return {
        "release": {"identity": dict(repository), "date_epoch": released_at,
                    "valid_until_epoch": valid_until},
        "index": {"compressed": dict(index["compressed"]), "decoded": dict(index["decoded"]),
                  "package_paragraphs": count},
        "package": dict(found),
    }
