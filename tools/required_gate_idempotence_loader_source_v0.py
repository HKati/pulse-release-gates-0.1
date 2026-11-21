"""Reconstruct one pinned Debian loader/debug/source relationship as data.

The caller supplies the historical Release, complete decoded Packages index,
and six exact artifacts. No signature is freshly verified here. The externally
selected historical signature evidence and archive keyring remain trust inputs.
The result establishes archive-declared source identity and exact package
membership, not an independently reproduced source-to-binary build.

Source archives are inspected without extraction. Every active quilt patch is
scanned as a unified diff; only selected source members are replayed. Complete
old-hunk context must match. A stale coordinate is accepted only when the full
old hunk has a unique match, and that offset is explicitly recorded.
"""
from __future__ import annotations

import hashlib
import lzma
import re

import required_gate_idempotence_debian_metadata_v0 as debian_metadata
import required_gate_idempotence_launcher_package_v0 as debian_package


VERSION = "2.41-12+deb13u4"
SOURCE_NAME = "glibc"
SOURCE_ROOT = "glibc-2.41"
SOURCE_DIRECTORY = "pool/main/g/glibc"
SOURCE_TAR_LIMIT = 256 * 1024 * 1024
SOURCE_MEMBER_LIMIT = 2 * 1024 * 1024
SOURCE_MEMBER_COUNT_LIMIT = 24576
RETAINED_SOURCE_LIMIT = 8 * 1024 * 1024
PATCH_COUNT_LIMIT = 128
PATCH_LINE_LIMIT = 16384
PATCH_LINES_LIMIT = 32768
PATCH_HUNK_LIMIT = 2048
PATCH_FILE_LIMIT = 1024
XZ_MEMORY_LIMIT = 64 * 1024 * 1024
PATCH_POLICY = "full_context_unique_match_with_recorded_offsets_no_fuzz"

# These pin complete original artifacts, never cropped stanzas or saved verdicts.
INPUT_BINDINGS = {
    "libc6_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 2846580,
        "sha256": "967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9",
    },
    "libc6-dbg_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 7373052,
        "sha256": "0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7",
    },
    "Sources.xz": {
        "size_bytes": 10540436,
        "sha256": "6002f81f463a2d976d84b34170367cc16da2d60bd0ba9ab9d868d6e1c1a935d9",
    },
    "glibc_2.41-12+deb13u4.dsc": {
        "size_bytes": 7576,
        "sha256": "0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e",
    },
    "glibc_2.41.orig.tar.xz": {
        "size_bytes": 20323540,
        "sha256": "f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998",
    },
    "glibc_2.41-12+deb13u4.debian.tar.xz": {
        "size_bytes": 499524,
        "sha256": "dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d",
    },
}
RELEASE_BINDING = {
    "size_bytes": 138612,
    "sha256": "ed56aac47e7911e65ee63aae8d67e29f20e023f840e49f8ed037043a33de138a",
}
PACKAGES_BINDING = {
    "size_bytes": 56620099,
    "sha256": "4f2c68d67001d595fbd343f6dbad44468953a51c4d9dec3a4803249f6e295940",
}
SOURCES_BINDING = {
    "size_bytes": 57389881,
    "sha256": "ae99131b13c7e61c53a52c33a2f9088a1bc5db15a664f5d90cc3753ad9b65606",
}
SERIES_BINDING = {
    "size_bytes": 2574,
    "sha256": "cb7488954191709b6759021fbec3fecfa04727b94d039f339b1f31e4f1e9d00b",
}
LOADER_MEMBER = "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
DEBUG_MEMBER = "usr/lib/debug/.build-id/86/f7eb4ff495ed3f2831c6d3d662e4321762a2a3.debug"
LOADER_BINDING = {
    "size_bytes": 225672,
    "sha256": "c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307",
}
DEBUG_BINDING = {
    "size_bytes": 556488,
    "sha256": "34ab07395545cf33df8e551e809ebee6fd3fc2707ed848e390872dce539c4a78",
}
SELECTED_SOURCE_BINDINGS = {
    "elf/dl-deps.c": {
        "size_bytes": 17592,
        "sha256": "2f23f25c68bdde0ca3c30a3186861be716d7790b17c4b99681bc8c5d9e554f8b",
    },
    "elf/dl-load.c": {
        "size_bytes": 68566,
        "sha256": "9569f7343a86b0851404bb0ad839b8c7787d73aeaa19e06dc2e62d77b3e05d36",
    },
    "include/link.h": {
        "size_bytes": 13993,
        "sha256": "7ed94ef359bac5549a63a3c19a7a32e6cef6e18787201b765be63b1e1e1f983f",
    },
    "sysdeps/generic/ldsodefs.h": {
        "size_bytes": 54340,
        "sha256": "8a17e7e438fcfb2e89c2a58cf76ffe2a79c32f8816b2387de610ed996473e962",
    },
    "sysdeps/x86_64/dl-machine.h": {
        "size_bytes": 24634,
        "sha256": "1545fc722187437ac1c73b5e022fa409ace5998c21915e9d3133c23d0f4413a7",
    },
    "dlfcn/dlfcn.h": {
        "size_bytes": 8581,
        "sha256": "89e69b3e7f8f6863670d9e71d8e0344cff60758656758e549092ef44e566ef7c",
    },
    "elf/elf.h": {
        "size_bytes": 196094,
        "sha256": "1490fa24d00c6e1a803edd0402e24f11bcf9de0683953f83a726a9c5462fe46c",
    },
}
_HUNK = re.compile(rb"@@ -([0-9]+)(?:,([0-9]+))? \+([0-9]+)(?:,([0-9]+))? @@[^\n]*\n\Z")
_SAFE_PART = re.compile(r"[A-Za-z0-9_+.~,@=#-]+\Z")


class SourceError(ValueError):
    """A stable rejection code without inspected bytes, text, or paths."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise SourceError(code)


def _binding(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _check_binding(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(hashlib.sha256(raw).hexdigest() == expected["sha256"], code)


def _paragraphs(raw, *, maximum=250000, stanza_limit=256 * 1024):
    return debian_metadata._paragraphs(raw, stanza_limit=stanza_limit, maximum=maximum)


def _one_paragraph(raw, *, limit):
    items = list(_paragraphs(raw, maximum=2, stanza_limit=limit))
    _need(len(items) == 1, "source_metadata_paragraph_count")
    return debian_metadata._fields(items[0])


def _source_identity(fields, binary_version):
    text = debian_metadata._single(fields, "source")
    match = re.fullmatch(r"([a-z0-9][a-z0-9+.-]*)(?: \(([^() ]+)\))?", text)
    _need(match is not None, "source_binary_source_syntax")
    name, explicit = match.groups()
    version = binary_version if explicit is None else explicit
    _need(name == SOURCE_NAME and version == VERSION,
          "source_binary_source_identity")
    return {"name": name, "version": version, "version_explicit": explicit is not None}


def _sha_rows(fields, field):
    rows = debian_metadata._digest_rows(fields, field, 64)
    return {name: {"sha256": row[field], "size_bytes": row["size_bytes"]}
            for name, row in rows.items()}


def _metadata(release_bytes, packages_bytes, inputs):
    release = _one_paragraph(release_bytes, limit=1024 * 1024)
    identity = {key: debian_metadata._single(release, key)
                for key in ("origin", "label", "suite", "codename", "version", "date")}
    _need(all(identity[key] == value for key, value in {
        "origin": "Debian", "label": "Debian", "suite": "stable",
        "codename": "trixie", "version": "13.7",
        "date": "Sat, 12 Sep 2026 07:55:41 UTC",
    }.items()), "source_release_identity")
    release_rows = _sha_rows(release, "sha256")
    for path, expected in (
        ("main/binary-amd64/Packages", PACKAGES_BINDING),
        ("main/source/Sources.xz", INPUT_BINDINGS["Sources.xz"]),
        ("main/source/Sources", SOURCES_BINDING),
    ):
        _need(release_rows.get(path) == expected, "source_release_index_binding")

    selected_packages, packages_count = {}, 0
    for lines in _paragraphs(packages_bytes):
        packages_count += 1
        fields = debian_metadata._fields(lines)
        row = debian_metadata._package_row(fields)
        if row["name"] in {"libc6", "libc6-dbg"}:
            _need(row["name"] not in selected_packages, "source_binary_index_ambiguous")
            _need(row["version"] == VERSION and row["architecture"] == "amd64",
                  "source_binary_index_identity")
            filename = row["name"] + "_" + VERSION + "_amd64.deb"
            _need(row["filename"] == SOURCE_DIRECTORY + "/" + filename and
                  {key: row[key] for key in ("sha256", "size_bytes")} == INPUT_BINDINGS[filename],
                  "source_binary_index_binding")
            row["source"] = _source_identity(fields, row["version"])
            selected_packages[row["name"]] = row
    _need(set(selected_packages) == {"libc6", "libc6-dbg"}, "source_binary_index_missing")

    sources_bytes = debian_metadata._decode_index(inputs["Sources.xz"])
    _check_binding(sources_bytes, SOURCES_BINDING, "source_decoded_sources_binding")
    selected_source, sources_count = None, 0
    # The complete pinned index includes Linux stanzas of about 289 KiB.
    for lines in _paragraphs(sources_bytes, stanza_limit=512 * 1024):
        sources_count += 1
        fields = debian_metadata._fields(lines)
        name = debian_metadata._single(fields, "package")
        version = debian_metadata._single(fields, "version")
        directory = debian_metadata._single(fields, "directory")
        _need(debian_metadata.PACKAGE_NAME.fullmatch(name) is not None and
              debian_metadata._path(directory) and directory.startswith("pool/"),
              "source_source_index_identity")
        rows = _sha_rows(fields, "checksums-sha256")
        if name == SOURCE_NAME and version == VERSION:
            _need(selected_source is None, "source_source_index_ambiguous")
            _need(directory == SOURCE_DIRECTORY, "source_source_directory")
            binary_field = fields.get("binary")
            _need(type(binary_field) is list and len(binary_field) == 1 and
                  len(binary_field[0]) <= 4096, "source_source_binary_roster")
            binaries = binary_field[0].split(", ")
            _need(len(binaries) == len(set(binaries)) and
                  all(debian_metadata.PACKAGE_NAME.fullmatch(name) for name in binaries) and
                  {"libc6", "libc6-dbg"}.issubset(binaries), "source_source_binary_roster")
            selected_source = {"name": name, "version": version,
                               "directory": directory, "rows": rows}
    _need(selected_source is not None, "source_source_index_missing")
    component_names = ("glibc_2.41-12+deb13u4.dsc", "glibc_2.41.orig.tar.xz",
                       "glibc_2.41-12+deb13u4.debian.tar.xz")
    _need(set(selected_source["rows"]) == set(component_names), "source_component_roster")
    components = []
    for name in component_names:
        _need(selected_source["rows"][name] == INPUT_BINDINGS[name],
              "source_component_index_binding")
        components.append({"filename": name, "binding": _binding(inputs[name])})

    dsc = inputs[component_names[0]]
    prefix = b"-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\n"
    separator = b"\n-----BEGIN PGP SIGNATURE-----\n"
    _need(dsc.startswith(prefix) and dsc.count(separator) == 1 and
          dsc.endswith(b"-----END PGP SIGNATURE-----\n"), "source_dsc_clearsigned_shape")
    cleartext = dsc[len(prefix):dsc.index(separator)]
    cleartext = b"\n".join(line[2:] if line.startswith(b"- ") else line
                            for line in cleartext.split(b"\n")) + b"\n"
    fields = _one_paragraph(cleartext, limit=256 * 1024)
    _need(debian_metadata._single(fields, "format") == "3.0 (quilt)" and
          debian_metadata._single(fields, "source") == SOURCE_NAME and
          debian_metadata._single(fields, "version") == VERSION, "source_dsc_identity")
    dsc_rows = _sha_rows(fields, "checksums-sha256")
    _need(dsc_rows == {name: INPUT_BINDINGS[name] for name in component_names[1:]},
          "source_dsc_component_binding")
    facts = {
        "release": {"binding": _binding(release_bytes), "identity": identity},
        "packages_index": {"binding": _binding(packages_bytes),
                           "path": "main/binary-amd64/Packages", "paragraph_count": packages_count},
        "sources_index": {"compressed": {"path": "main/source/Sources.xz",
                                           "binding": _binding(inputs["Sources.xz"])},
                          "decoded": {"path": "main/source/Sources", "binding": _binding(sources_bytes)},
                          "paragraph_count": sources_count},
    }
    return facts, selected_packages, components


def _package(raw, name, index, member, expected_member):
    result = debian_package.inspect_package(
        raw, member_path=member, expected_name=name, expected_version=VERSION,
        expected_architecture="amd64")
    selected = result.pop("member_bytes")
    _check_binding(selected, expected_member, "source_package_member_binding")
    # The unchanged package reader deliberately returns only Package/Version/
    # Architecture. Inspect its bounded control member too to bind Source.
    ar_members = debian_package._ar(raw)
    control_tar = debian_package._decompress(*ar_members[1], debian_package.CONTROL_TAR_LIMIT)
    (control, _mode), _count = debian_package._tar(
        control_tar, "control", debian_package.CONTROL_TAR_LIMIT)
    fields = _one_paragraph(control, limit=debian_package.CONTROL_LIMIT)
    result["control_source"] = _source_identity(fields, VERSION)
    _need(result["control_source"] == index["source"], "source_package_source_disagreement")
    if name == "libc6-dbg":
        _need(debian_metadata._single(fields, "depends") == "libc6 (= " + VERSION + ")",
              "source_debug_dependency")
    result["index"] = index
    return result, selected


class _XZReader:
    """Single complete XZ stream; bounded chunks, output, decoder memory."""

    def __init__(self, raw):
        self.raw = raw
        self.position = 0
        self.buffer = bytearray()
        self.decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=XZ_MEMORY_LIMIT)
        self.total = 0
        self.digest = hashlib.sha256()
        self.done = False

    def _pump(self):
        if self.decoder.eof:
            _need(not self.decoder.unused_data and self.position == len(self.raw),
                  "source_tar_xz_trailing_data")
            self.done = True
            return
        if self.decoder.needs_input:
            _need(self.position < len(self.raw), "source_tar_xz_truncated")
            chunk = self.raw[self.position:self.position + 65536]
            self.position += len(chunk)
        else:
            chunk = b""
        try:
            out = self.decoder.decompress(chunk, max_length=65536)
        except lzma.LZMAError as exc:
            raise SourceError("source_tar_xz_invalid") from exc
        self.total += len(out)
        _need(self.total <= SOURCE_TAR_LIMIT, "source_tar_decoded_limit")
        self.digest.update(out)
        self.buffer.extend(out)

    def read(self, count):
        _need(type(count) is int and 0 <= count <= SOURCE_MEMBER_LIMIT,
              "source_tar_read_limit")
        while len(self.buffer) < count and not self.done:
            self._pump()
        out = bytes(self.buffer[:count])
        del self.buffer[:count]
        return out

    def exact(self, count):
        out = self.read(count)
        _need(len(out) == count, "source_tar_truncated")
        return out


def _octal(raw):
    value = raw.strip(b" \0")
    _need(bool(value) and len(value) <= 16 and all(c in b"01234567" for c in value),
          "source_tar_number")
    return int(value, 8)


def _tar_text(raw):
    value, separator, padding = raw.partition(b"\0")
    _need((not separator or not any(padding)) and all(32 <= c <= 126 for c in value),
          "source_tar_text")
    return value.decode("ascii")


def _path(text, *, directory=False):
    _need(type(text) is str and 0 < len(text) <= 256 and "\\" not in text,
          "source_member_path")
    if text.startswith("./"):
        text = text[2:]
    if directory and text.endswith("/"):
        text = text[:-1]
    _need(text and all(p not in {"", ".", ".."} and _SAFE_PART.fullmatch(p)
                       for p in text.split("/")), "source_member_path")
    return text


def _source_tar(raw, *, original):
    reader = _XZReader(raw)
    entries, retained = {}, {}
    retained_total = payload_total = 0
    selected = {SOURCE_ROOT + "/" + name for name in SELECTED_SOURCE_BINDINGS}
    while True:
        header = reader.exact(512)
        if not any(header):
            _need(not any(reader.exact(512)), "source_tar_terminator")
            while True:
                tail = reader.read(65536)
                if not tail:
                    break
                _need(not any(tail), "source_tar_trailing_data")
            _need(reader.total % 512 == 0, "source_tar_alignment")
            break
        _need(len(entries) < SOURCE_MEMBER_COUNT_LIMIT, "source_tar_member_limit")
        _need(_octal(header[148:156]) == sum(header[:148]) + 8 * 32 + sum(header[156:]),
              "source_tar_checksum")
        magic = header[257:265]
        if magic == b"ustar\x0000":
            prefix = _tar_text(header[345:500])
            _need(not any(header[500:]), "source_tar_extension_unsupported")
        elif magic == b"ustar  \x00":
            _need(not any(header[345:]), "source_tar_extension_unsupported")
            prefix = ""
        else:
            _need(not any(header[257:]), "source_tar_format_unsupported")
            prefix = ""
        kind = header[156:157]
        _need(kind in {b"\0", b"0", b"1", b"2", b"5"}, "source_tar_extension_unsupported")
        name = _tar_text(header[:100])
        if prefix:
            name = prefix + "/" + name
        path = _path(name, directory=kind == b"5")
        _need(path not in entries, "source_tar_duplicate_path")
        expected_root = SOURCE_ROOT if original else "debian"
        _need(path == expected_root or path.startswith(expected_root + "/"),
              "source_tar_root")
        _need(_octal(header[100:108]) <= 0o7777, "source_tar_mode")
        for field in (header[108:116], header[116:124], header[136:148]):
            _octal(field)
        size = _octal(header[124:136])
        _need(size <= SOURCE_TAR_LIMIT, "source_tar_member_payload_limit")
        regular = kind in {b"\0", b"0"}
        _need(regular or size == 0, "source_tar_nonregular_payload")
        link = _tar_text(header[157:257])
        _need(bool(link) if kind in {b"1", b"2"} else not link, "source_tar_link")
        entries[path] = kind
        keep = path in selected if original else path.startswith("debian/patches/") and regular
        if keep:
            _need(regular and 0 < size <= SOURCE_MEMBER_LIMIT, "source_selected_member_type_size")
            retained_total += size
            _need(retained_total <= RETAINED_SOURCE_LIMIT, "source_retained_size_limit")
        payload_total += size
        parts, left = [], size
        while left:
            part = reader.exact(min(left, 65536))
            if keep:
                parts.append(part)
            left -= len(part)
        _need(not any(reader.exact((-size) % 512)), "source_tar_padding")
        if keep:
            retained[path] = b"".join(parts)
    for path in entries:
        parts = path.split("/")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            _need(parent not in entries or entries[parent] == b"5",
                  "source_tar_ancestor_not_directory")
    if original:
        _need(set(retained) == selected, "source_selected_member_missing")
    else:
        _need("debian/patches/series" in retained, "source_patch_series_missing")
    facts = {"compressed": _binding(raw),
             "decoded": {"sha256": reader.digest.hexdigest(), "size_bytes": reader.total},
             "member_count": len(entries), "member_payload_size_bytes": payload_total,
             "selected_member_count": len(retained), "selected_payload_size_bytes": retained_total}
    return retained, facts


def _series(raw):
    _check_binding(raw, SERIES_BINDING, "source_patch_series_binding")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise SourceError("source_patch_series_encoding") from exc
    result = []
    for line in lines:
        text = line.partition("#")[0].strip()
        if not text:
            continue
        _need(len(result) < PATCH_COUNT_LIMIT and len(text.split()) == 1,
              "source_patch_series_options")
        path = "debian/patches/" + _path(text)
        _need(path not in result, "source_patch_series_duplicate")
        result.append(path)
    _need(len(result) == 80, "source_patch_series_count")
    return result


def _patch_path(line):
    parts = line[4:].split()
    _need(bool(parts), "source_patch_header_path")
    try:
        raw = parts[0].decode("ascii")
    except UnicodeError as exc:
        raise SourceError("source_patch_header_path") from exc
    if raw == "/dev/null":
        return None
    # Quilt's default -p1 is fixed by the option-free authenticated series.
    raw = _path(raw)
    _need("/" in raw, "source_patch_strip_level")
    return _path(raw.split("/", 1)[1])


def _lf_lines(raw):
    parts = raw.split(b"\n")
    return [part + b"\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _scan_patch(raw):
    """Parse every unified header and hunk, including unselected files."""
    _need(type(raw) is bytes and 0 < len(raw) <= SOURCE_MEMBER_LIMIT and
          b"\0" not in raw and raw.endswith(b"\n"), "source_patch_size_encoding")
    lines = _lf_lines(raw)
    _need(len(lines) <= PATCH_LINES_LIMIT and all(len(line) <= PATCH_LINE_LIMIT for line in lines),
          "source_patch_line_limit")
    blocks, position, total_hunks, pending_index = [], 0, 0, None
    while position < len(lines):
        line = lines[position]
        if not line.startswith(b"--- "):
            if line.startswith(b"Index: "):
                _need(pending_index is None, "source_patch_orphan_index")
                pending_index = _patch_path(b"--- " + line[7:])
            _need(not line.startswith((b"+++ ", b"@@", b"*** ", b"GIT binary patch",
                                       b"Binary files ", b"rename ", b"copy ",
                                       b"\\ No newline at end of file")),
                  "source_patch_unsupported_or_orphan")
            position += 1
            continue
        _need(len(blocks) < PATCH_FILE_LIMIT and position + 1 < len(lines) and
              lines[position + 1].startswith(b"+++ "), "source_patch_header_pair")
        old = _patch_path(line)
        new = _patch_path(lines[position + 1])
        index_path, pending_index = pending_index, None
        _need(old is not None or new is not None, "source_patch_null_paths")
        position += 2
        hunks = []
        while position < len(lines) and lines[position].startswith(b"@@"):
            match = _HUNK.fullmatch(lines[position])
            _need(match is not None and total_hunks < PATCH_HUNK_LIMIT, "source_patch_hunk_header")
            old_start, old_count, new_start, new_count = (
                int(value) if value is not None else 1 for value in match.groups())
            _need(max(old_start, old_count, new_start, new_count) <= 1000000,
                  "source_patch_hunk_range")
            _need(old_count > 0 or new_count > 0, "source_patch_empty_hunk")
            position += 1
            before, after, old_seen, new_seen = [], [], 0, 0
            while old_seen < old_count or new_seen < new_count:
                _need(position < len(lines), "source_patch_hunk_truncated")
                body = lines[position]
                tag = body[:1]
                _need(tag in {b" ", b"-", b"+"}, "source_patch_hunk_body")
                if tag in {b" ", b"-"}:
                    before.append(body[1:])
                    old_seen += 1
                if tag in {b" ", b"+"}:
                    after.append(body[1:])
                    new_seen += 1
                _need(old_seen <= old_count and new_seen <= new_count, "source_patch_hunk_count")
                position += 1
            hunks.append({"old_start": old_start, "old_count": old_count,
                          "new_start": new_start, "new_count": new_count,
                          "before": before, "after": after})
            total_hunks += 1
            if position < len(lines):
                following = lines[position]
                topgit_footer = (following == b"---\n" and position + 1 < len(lines)
                                 and lines[position + 1].startswith(b"tg: "))
                _need(not following.startswith((b" ", b"+", b"-")) or
                      following.startswith(b"--- ") or following == b"-- \n" or topgit_footer,
                      "source_patch_hunk_excess_body")
        _need(bool(hunks), "source_patch_header_without_hunks")
        blocks.append({"old": old, "new": new, "index": index_path, "hunks": hunks})
    _need(bool(blocks) and pending_index is None, "source_patch_no_unified_files")
    return blocks


def _apply_hunks(raw, hunks):
    lines = _lf_lines(raw)
    delta, minimum, facts = 0, 0, []
    for number, hunk in enumerate(hunks):
        before, after = hunk["before"], hunk["after"]
        _need(before and hunk["old_start"] > 0, "source_patch_selected_context_required")
        expected_new_start = hunk["old_start"] + delta - (0 if after else 1)
        _need(hunk["new_start"] == expected_new_start, "source_patch_hunk_coordinate_relation")
        expected = hunk["old_start"] - 1 + delta
        if 0 <= expected <= len(lines) - len(before) and lines[expected:expected + len(before)] == before:
            position = expected
            method = "declared_coordinates"
        else:
            matches = [index for index in range(len(lines) - len(before) + 1)
                       if lines[index:index + len(before)] == before]
            _need(len(matches) == 1, "source_patch_context_not_unique")
            position = matches[0]
            method = "unique_full_context"
        _need(position >= minimum, "source_patch_hunk_order")
        previous = b"".join(lines)
        lines[position:position + len(before)] = after
        current = b"".join(lines)
        _need(len(current) <= SOURCE_MEMBER_LIMIT, "source_patch_result_limit")
        facts.append({"hunk_index": number, "old_start": hunk["old_start"],
                      "old_count": hunk["old_count"], "new_start": hunk["new_start"],
                      "new_count": hunk["new_count"], "expected_current_start": expected + 1,
                      "applied_current_start": position + 1, "line_offset": position - expected,
                      "match_method": method, "old_hunk": _binding(b"".join(before)),
                      "new_hunk": _binding(b"".join(after)),
                      "before": _binding(previous), "after": _binding(current)})
        minimum = position + len(after)
        delta += len(after) - len(before)
    return b"".join(lines), facts


def _patch_sources(original, debian):
    series_member = "debian/patches/series"
    order = _series(debian[series_member])
    sources = {path: original[SOURCE_ROOT + "/" + path] for path in SELECTED_SOURCE_BINDINGS}
    steps = {path: [] for path in sources}
    patch_facts = []
    for number, member in enumerate(order):
        _need(member in debian, "source_patch_member_missing")
        raw = debian[member]
        blocks = _scan_patch(raw)
        selected_files, selected_hunks = [], 0
        for block in blocks:
            selected = set(sources).intersection({block["old"], block["new"], block["index"]})
            if not selected:
                continue
            _need(len(selected) == 1 and block["old"] == block["new"] and
                  block["old"] in selected and block["index"] in {None, block["old"]},
                  "source_patch_selected_creation_deletion")
            path = next(iter(selected))
            before = _binding(sources[path])
            sources[path], hunks = _apply_hunks(sources[path], block["hunks"])
            steps[path].append({"order": number, "member": member, "hunk_count": len(hunks),
                                "before": before, "after": _binding(sources[path]), "hunks": hunks})
            selected_files.append(path)
            selected_hunks += len(hunks)
        patch_facts.append({"order": number, "member": member, "binding": _binding(raw),
                            "file_diff_count": len(blocks),
                            "hunk_count": sum(len(block["hunks"]) for block in blocks),
                            "selected_files": selected_files, "selected_hunk_count": selected_hunks,
                            "unselected_alternative_path_blocks": [
                                {"old": block["old"], "new": block["new"], "index": block["index"]}
                                for block in blocks
                                if (block["old"] is not None and block["new"] is not None and
                                    block["old"] != block["new"]) or
                                   block["index"] not in {None, block["old"], block["new"]}]})
    files = []
    for path, expected in SELECTED_SOURCE_BINDINGS.items():
        _check_binding(sources[path], expected, "source_patched_member_binding")
        files.append({"path": path,
                      "original": {"member": SOURCE_ROOT + "/" + path,
                                   "binding": _binding(original[SOURCE_ROOT + "/" + path])},
                      "patched": {"binding": _binding(sources[path])}, "patch_steps": steps[path]})
    return sources, {"member": series_member, "binding": _binding(debian[series_member]),
                     "active_patch_count": len(order), "patch_policy": PATCH_POLICY,
                     "all_active_patches_scanned": True, "patches": patch_facts}, files


def derive_source_facts(*, release_bytes, packages_bytes, inputs):
    """Return JSON facts plus exact loader, debug, and patched selected bytes.

    ``inputs`` is exactly the six-basename-to-bytes mapping in INPUT_BINDINGS.
    No file reads/writes, extraction, network, package installation, subprocess,
    target execution, or external verifier invocation occurs in this function.
    """
    _need(type(inputs) is dict and set(inputs) == set(INPUT_BINDINGS), "source_input_roster")
    _check_binding(release_bytes, RELEASE_BINDING, "source_release_binding")
    _check_binding(packages_bytes, PACKAGES_BINDING, "source_packages_binding")
    for name, expected in INPUT_BINDINGS.items():
        _check_binding(inputs[name], expected, "source_artifact_binding")
    try:
        metadata, indexes, components = _metadata(release_bytes, packages_bytes, inputs)
        packages = {}
        packages["libc6"], loader = _package(
            inputs["libc6_2.41-12+deb13u4_amd64.deb"], "libc6", indexes["libc6"],
            LOADER_MEMBER, LOADER_BINDING)
        packages["libc6-dbg"], debug = _package(
            inputs["libc6-dbg_2.41-12+deb13u4_amd64.deb"], "libc6-dbg", indexes["libc6-dbg"],
            DEBUG_MEMBER, DEBUG_BINDING)
        original, original_facts = _source_tar(inputs["glibc_2.41.orig.tar.xz"], original=True)
        debian, debian_facts = _source_tar(inputs["glibc_2.41-12+deb13u4.debian.tar.xz"], original=False)
        sources, series, files = _patch_sources(original, debian)
    except debian_metadata.MetadataError as exc:
        raise SourceError("source_metadata_invalid") from exc
    except debian_package.PackageError as exc:
        raise SourceError("source_debian_package_invalid") from exc
    facts = {
        "inputs": [{"filename": name, **_binding(inputs[name])} for name in INPUT_BINDINGS],
        "metadata": metadata, "packages": packages,
        "source": {"name": SOURCE_NAME, "version": VERSION, "directory": SOURCE_DIRECTORY,
                   "components": components, "archives": {"original": original_facts, "debian": debian_facts},
                   "series": series, "files": files},
        "claim_limits": {"signature_freshly_verified": False,
                         "dsc_signature_freshly_verified": False,
                         "source_to_binary_rebuild_performed": False,
                         "signature_trust_basis": "externally_selected_historical_release_evidence",
                         "relationship": "archive_declared_source_and_exact_package_members"},
    }
    return {"facts": facts, "loader": loader, "debug": debug, "sources": sources}
