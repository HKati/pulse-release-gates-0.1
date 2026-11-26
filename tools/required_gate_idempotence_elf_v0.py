#!/usr/bin/env python3
"""Bounded, static ELF metadata for the selected idempotence runtime capsule.

This parser never loads or executes the inspected object, invokes ``ldd``, or
searches the host for a dependency. Its result describes selected native-file
metadata; it is not proof of loader resolution, ABI compatibility, dynamic
imports, runtime closure, or a successful execution.

The supported profile is ordinary ELF64 little-endian x86-64 ET_EXEC/ET_DYN,
with an explicit dynamic segment. Program headers, not optional section names,
locate the bytes that a loader would use. Unsupported extensions reject.
"""
from __future__ import annotations

import re
import struct
from typing import Any

MAX_ELF_BYTES = 128 * 1024 * 1024
MAX_PROGRAM_HEADERS = 1024
MAX_DYNAMIC_ENTRIES = 8192
MAX_STRING_TABLE_BYTES = 4 * 1024 * 1024
MAX_STRING_BYTES = 4096
MAX_NEEDED = 512
UINT64_MAX = 2**64 - 1

PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_SHLIB = 1, 2, 3, 5
DT_NULL, DT_NEEDED, DT_STRTAB, DT_STRSZ = 0, 1, 5, 10
DT_SONAME, DT_RPATH, DT_RUNPATH = 14, 15, 29

# Standard gABI tags through DT_RELRENT plus the GNU metadata tags used by the
# supported Linux profile. Configuration/audit/filter extensions can introduce
# other loaded objects and are deliberately outside this contract. An unknown
# processor/OS extension is not silently assumed to be dependency-neutral.
_DYNAMIC_TAGS = set(range(38)) | {
    0x6FFFFEF5,  # DT_GNU_HASH
    0x6FFFFEF6,  # DT_TLSDESC_PLT
    0x6FFFFEF7,  # DT_TLSDESC_GOT
    0x6FFFFFF0,  # DT_VERSYM
    0x6FFFFFF9,  # DT_RELACOUNT
    0x6FFFFFFA,  # DT_RELCOUNT
    0x6FFFFFFB,  # DT_FLAGS_1
    0x6FFFFFFC,  # DT_VERDEF
    0x6FFFFFFD,  # DT_VERDEFNUM
    0x6FFFFFFE,  # DT_VERNEED
    0x6FFFFFFF,  # DT_VERNEEDNUM
    0x70000000,  # DT_X86_64_PLT
    0x70000001,  # DT_X86_64_PLTSZ
    0x70000003,  # DT_X86_64_PLTENT
}
_OTHER_OBJECT_TAGS = {
    0x6FFFFEFA,  # DT_CONFIG
    0x6FFFFEFB,  # DT_DEPAUDIT
    0x6FFFFEFC,  # DT_AUDIT
    0x7FFFFFFD,  # DT_AUXILIARY
    0x7FFFFFFE,  # DT_USED (deprecated)
    0x7FFFFFFF,  # DT_FILTER
}
_SINGLETONS = {DT_STRTAB, DT_STRSZ, DT_SONAME, DT_RPATH, DT_RUNPATH}
_STRING_TAGS = {DT_NEEDED, DT_SONAME, DT_RPATH, DT_RUNPATH}
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+\-]{0,254}\Z")
_PATH_PART = re.compile(r"[A-Za-z0-9_.+\-]+\Z")


class ElfError(ValueError):
    """Stable public rejection code, with no inspected byte content echoed."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise ElfError(code)


def _extent(offset: int, size: int, limit: int, code: str) -> tuple[int, int]:
    _need(0 <= offset <= limit and 0 <= size <= limit - offset, code)
    return offset, offset + size


def _address_extent(address: int, size: int) -> tuple[int, int]:
    _need(0 <= address <= UINT64_MAX and 0 <= size <= UINT64_MAX - address,
          "elf_address_overflow")
    return address, address + size


def _cstring(raw: bytes, offset: int, *, code: str) -> str:
    _need(0 <= offset < len(raw), code)
    end = raw.find(b"\0", offset, min(len(raw), offset + MAX_STRING_BYTES + 1))
    _need(end >= 0 and 0 < end - offset <= MAX_STRING_BYTES, code)
    try:
        value = raw[offset:end].decode("ascii")
    except UnicodeError as exc:
        raise ElfError(code) from exc
    _need(all(32 <= ord(character) <= 126 for character in value), code)
    return value


def _interpreter(raw: bytes) -> str:
    _need(2 <= len(raw) <= MAX_STRING_BYTES + 1 and raw.endswith(b"\0")
          and raw.count(b"\0") == 1, "elf_interpreter_invalid")
    value = _cstring(raw, 0, code="elf_interpreter_invalid")
    parts = value.split("/")
    _need(value.startswith("/") and len(parts) > 1
          and all(part not in {"", ".", ".."} and _PATH_PART.fullmatch(part) is not None
                  for part in parts[1:]), "elf_interpreter_invalid")
    return value


def _library_name(value: str) -> str:
    _need(_NAME.fullmatch(value) is not None and value not in {".", ".."},
          "elf_dependency_name_invalid")
    return value


def inspect_elf(raw: bytes) -> dict[str, Any]:
    """Return selected dynamic-linking metadata without loading the object.

    Missing dynamic metadata, ambiguous virtual/file mappings, alternate
    object-loading extensions and unsupported layouts reject. Empty DT_NEEDED
    is valid, for example for a loader that has no further native dependencies.
    RPATH/RUNPATH are retained as metadata, not interpreted as host lookup rules.
    """
    _need(type(raw) is bytes and 64 <= len(raw) <= MAX_ELF_BYTES, "elf_size_limit")
    ident = raw[:16]
    _need(ident[:4] == b"\x7fELF", "elf_magic_invalid")
    _need(ident[4] == 2 and ident[5] == 1 and ident[6] == 1,
          "elf_encoding_unsupported")
    _need(ident[7] in {0, 3} and ident[8] == 0 and ident[9:] == bytes(7),
          "elf_abi_unsupported")
    try:
        (object_type, machine, version, _entry, phoff, _shoff, flags, ehsize,
         phentsize, phnum, _shentsize, _shnum, _shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    except struct.error as exc:
        raise ElfError("elf_header_invalid") from exc
    _need(object_type in {2, 3} and machine == 62 and version == 1 and flags == 0,
          "elf_architecture_unsupported")
    _need(ehsize == 64 and phentsize == 56 and 1 <= phnum <= MAX_PROGRAM_HEADERS
          and phoff >= ehsize, "elf_program_headers_invalid")
    _extent(phoff, phnum * phentsize, len(raw), "elf_program_headers_invalid")
    headers = []
    for index in range(phnum):
        kind, permission, offset, address, _physical, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", raw, phoff + index * phentsize)
        if kind == 0:
            continue  # All other PT_NULL fields have no ABI meaning.
        _need(kind != PT_SHLIB, "elf_segment_type_unsupported")
        _extent(offset, filesz, len(raw), "elf_segment_outside_file")
        _address_extent(address, memsz)
        _need(align in {0, 1} or (align & (align - 1) == 0 and address % align == offset % align),
              "elf_segment_alignment_invalid")
        if kind in {PT_LOAD, PT_DYNAMIC, PT_INTERP}:
            _need(filesz <= memsz, "elf_segment_memory_size_invalid")
        headers.append({"index": index, "type": kind, "flags": permission, "offset": offset,
                        "address": address, "filesz": filesz, "memsz": memsz})
    loads = [header for header in headers if header["type"] == PT_LOAD]
    _need(bool(loads), "elf_load_segment_missing")
    _need([header["address"] for header in loads] == sorted(header["address"] for header in loads),
          "elf_load_order_invalid")
    mapped = [header for header in loads if header["filesz"]]
    for left, right in zip(mapped, mapped[1:]):
        _need(left["address"] + left["filesz"] <= right["address"], "elf_load_mapping_ambiguous")

    def file_offset(address: int, size: int) -> int:
        _address_extent(address, size)
        matches = [header for header in mapped if header["address"] <= address
                   and size <= header["filesz"] - (address - header["address"])]
        _need(len(matches) == 1, "elf_virtual_mapping_invalid")
        header = matches[0]
        offset = header["offset"] + address - header["address"]
        _extent(offset, size, len(raw), "elf_virtual_mapping_invalid")
        return offset

    interpreters = [header for header in headers if header["type"] == PT_INTERP]
    _need(len(interpreters) <= 1, "elf_interpreter_duplicate")
    interpreter = None
    if interpreters:
        header = interpreters[0]
        # Relocated Linux distributions can place PT_INTERP after PT_LOAD.
        # Its file extent, uniqueness and pathname remain checked; this reader
        # does not claim full gABI conformance from program-header ordering.
        interpreter = _interpreter(raw[header["offset"]:header["offset"] + header["filesz"]])
    dynamic = [header for header in headers if header["type"] == PT_DYNAMIC]
    _need(len(dynamic) == 1, "elf_dynamic_segment_invalid")
    header = dynamic[0]
    _need(16 <= header["filesz"] <= MAX_DYNAMIC_ENTRIES * 16 and header["filesz"] % 16 == 0,
          "elf_dynamic_size_invalid")
    _need(file_offset(header["address"], header["filesz"]) == header["offset"],
          "elf_dynamic_mapping_invalid")
    entries = []
    singletons = {}
    terminated = False
    for offset in range(header["offset"], header["offset"] + header["filesz"], 16):
        tag, value = struct.unpack_from("<qQ", raw, offset)
        if tag == DT_NULL:
            _need(value == 0, "elf_dynamic_terminator_invalid")
            terminated = True
            continue
        _need(not terminated, "elf_dynamic_trailing_data")
        _need(tag not in _OTHER_OBJECT_TAGS, "elf_external_loading_unsupported")
        _need(tag in _DYNAMIC_TAGS, "elf_dynamic_tag_unsupported")
        if tag in _SINGLETONS:
            _need(tag not in singletons, "elf_dynamic_tag_duplicate")
            singletons[tag] = value
        entries.append((tag, value))
    _need(terminated, "elf_dynamic_terminator_missing")
    string_tags = [(tag, value) for tag, value in entries if tag in _STRING_TAGS]
    has_table = DT_STRTAB in singletons or DT_STRSZ in singletons
    strings = b""
    if has_table or string_tags:
        _need(DT_STRTAB in singletons and DT_STRSZ in singletons, "elf_string_table_missing")
        size = singletons[DT_STRSZ]
        _need(1 <= size <= MAX_STRING_TABLE_BYTES, "elf_string_table_size_invalid")
        offset = file_offset(singletons[DT_STRTAB], size)
        strings = raw[offset:offset + size]
        _need(strings[0] == 0 and strings[-1] == 0, "elf_string_table_boundary_invalid")
    needed, soname, rpath, runpath = [], None, None, None
    for tag, offset in string_tags:
        value = _cstring(strings, offset, code="elf_dynamic_string_invalid")
        if tag == DT_NEEDED:
            needed.append(_library_name(value))
        elif tag == DT_SONAME:
            soname = _library_name(value)
        elif tag == DT_RPATH:
            rpath = value
        elif tag == DT_RUNPATH:
            runpath = value
    _need(len(needed) <= MAX_NEEDED and len(needed) == len(set(needed)), "elf_needed_duplicate_or_excess")
    return {"elf_type": "ET_EXEC" if object_type == 2 else "ET_DYN", "interpreter": interpreter,
            "needed": needed, "soname": soname, "rpath": rpath, "runpath": runpath}
