"""Narrow offline correlation of the exact historical loader and matching debug.

This data-only module never loads or runs the target ELF and does not establish
signed distribution provenance. Every input-dependent walk is bounded; only
one exact loader/debug pair is admitted. Its facts must be combined with an
independently verified provenance carrier and the distribution source.
"""

from __future__ import annotations

import hashlib
import posixpath
import struct
import zlib


LOADER_SHA = "c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307"
DEBUG_SHA = "34ab07395545cf33df8e551e809ebee6fd3fc2707ed848e390872dce539c4a78"
BUILD_ID = "86f7eb4ff495ed3f2831c6d3d662e4321762a2a3"
CU_START = 0xBCA5
MAX_DECODED_SECTION = 2 * 1024 * 1024


class BinaryError(ValueError):
    """Stable rejection code; it contains no inspected input or path."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(test, code):
    if not test:
        raise BinaryError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def take(data, off, size):
    need(0 <= off <= len(data) and 0 <= size <= len(data) - off, "bounded_slice")
    return data[off:off + size]


def cstr(data, off):
    need(0 <= off < len(data), "string_offset")
    stop = data.find(b"\0", off, min(len(data), off + 4096))
    need(stop != -1, "bounded_nul_string")
    return data[off:stop].decode("utf-8", errors="strict"), stop + 1


class Reader:
    def __init__(self, data, start=0, end=None):
        self.data = data
        self.p = start
        self.end = len(data) if end is None else end
        need(0 <= start <= self.end <= len(data), "reader_bounds")

    def raw(self, n):
        need(0 <= n <= self.end - self.p, "reader_overrun")
        out = self.data[self.p:self.p + n]
        self.p += n
        return out

    def uint(self, n):
        return int.from_bytes(self.raw(n), "little")

    def uleb(self):
        out = 0
        for i in range(10):
            x = self.uint(1)
            out |= (x & 127) << (i * 7)
            if x < 128:
                need(out < (1 << 64), "uleb64_overflow")
                return out
        raise BinaryError("uleb64_length")

    def sleb(self):
        out = 0
        for i in range(10):
            x = self.uint(1)
            out |= (x & 127) << (i * 7)
            if x < 128:
                if x & 64:
                    out -= 1 << ((i + 1) * 7)
                need(-(1 << 63) <= out < (1 << 63), "sleb64_overflow")
                return out
        raise BinaryError("sleb64_length")


class ELF:
    def __init__(self, data, expected_size, expected_sha):
        need(type(data) is bytes, "input_type")
        need(len(data) == expected_size, "input_size")
        self.data = data
        need(sha(self.data) == expected_sha, "input_sha256")
        d = self.data
        need(d[:7] == b"\x7fELF\x02\x01\x01", "elf64_little_endian")
        need(struct.unpack_from("<HH", d, 16) == (3, 62), "et_dyn_x86_64")
        phoff, shoff = struct.unpack_from("<QQ", d, 32)
        ehsize, phsize, phnum, shsize, shnum, shstridx = struct.unpack_from("<HHHHHH", d, 52)
        need(ehsize == 64 and phsize == 56 and shsize == 64, "elf_entry_sizes")
        need(0 < phnum <= 32 and 0 < shnum <= 128 and shstridx < shnum, "elf_counts")
        sh = [struct.unpack("<IIQQQQIIQQ", take(d, shoff + i * 64, 64)) for i in range(shnum)]
        names = take(d, sh[shstridx][4], sh[shstridx][5])
        self.sections = {}
        for index, s in enumerate(sh):
            name, _ = cstr(names, s[0])
            need(name not in self.sections, "duplicate_elf_section_name")
            self.sections[name] = {
                "index": index, "type": s[1], "flags": s[2], "vaddr": s[3],
                "offset": s[4], "size": s[5], "link": s[6], "entry_size": s[9]
            }
        self.ph = [struct.unpack("<IIQQQQQQ", take(d, phoff + i * 56, 56)) for i in range(phnum)]

    def section(self, name):
        s = self.sections[name]
        need(s["type"] != 8, "nobits_section_cannot_prove_file_bytes")
        raw = take(self.data, s["offset"], s["size"])
        if s["flags"] & 0x800:
            typ, reserved, size, alignment = struct.unpack("<IIQQ", take(raw, 0, 24))
            need(typ == 1 and reserved == 0 and size <= MAX_DECODED_SECTION, "zlib_section_header")
            dec = zlib.decompressobj()
            out = dec.decompress(raw[24:], size + 1)
            need(len(out) == size and dec.eof and not dec.unused_data and not dec.unconsumed_tail,
                 "bounded_complete_zlib_section")
            return out
        return raw

    def identity(self):
        n = self.section(".note.gnu.build-id")
        need(struct.unpack("<III", n[:12]) == (4, 20, 3) and n[12:16] == b"GNU\0", "build_id_note")
        need(n[16:36].hex() == BUILD_ID, "build-ID")
        return {"sha256": sha(self.data), "size_bytes": len(self.data), "build_id": BUILD_ID}

    def offset(self, va, length):
        hits = [p[2] + va - p[3] for p in self.ph
                if p[0] == 1 and p[1] & 1 and p[3] <= va and length <= p[5] - (va - p[3])]
        need(len(hits) == 1, "unique_file_backed_executable_pt_load")
        return hits[0]

    def symbols(self):
        raw = self.section(".symtab")
        strings = self.section(".strtab")
        need(len(raw) % 24 == 0 and len(raw) // 24 <= 4096, "symbol_count")
        out = {}
        for i in range(len(raw) // 24):
            name, info, other, ndx, value, size = struct.unpack("<IBBHQQ", raw[i * 24:(i + 1) * 24])
            text, _ = cstr(strings, name)
            if text:
                out.setdefault(text, []).append({"index": i, "value": value, "size": size,
                                                "type": info & 15, "section_index": ndx})
        return out


def abbrevs(data, offset):
    r = Reader(data, offset)
    out = {}
    forms = set()
    for _ in range(256):
        code = r.uleb()
        if code == 0:
            return out, forms, r.p
        need(code not in out, "duplicate_abbreviation")
        tag, child = r.uleb(), r.uint(1)
        need(child in (0, 1), "children_flag")
        attrs = []
        for _ in range(64):
            a, form = r.uleb(), r.uleb()
            if a == form == 0:
                break
            need(a != 0 and form != 0, "abbreviation_attribute_pair")
            value = r.sleb() if form == 0x21 else None
            attrs.append((a, form, value))
            forms.add(form)
        else:
            raise BinaryError("attribute_count")
        out[code] = (tag, child, attrs)
    raise BinaryError("abbreviation_count")


def parse_cu(debug):
    info = debug.section(".debug_info")
    r = Reader(info, CU_START)
    length = r.uint(4)
    need(length == 0x35DF, "selected_cu_length")
    end = CU_START + 4 + length
    r.end = end
    version, unit_type, ptrsize, aboff = r.uint(2), r.uint(1), r.uint(1), r.uint(4)
    need((version, unit_type, ptrsize, aboff) == (5, 1, 8, 0x17F4), "selected_cu_header")
    ab, forms, abend = abbrevs(debug.section(".debug_abbrev"), aboff)
    allowed = {1, 5, 7, 8, 11, 14, 19, 23, 24, 25, 31, 33}
    need(forms == allowed, "closed_cu_form_inventory")
    strings = debug.section(".debug_str")
    line_strings = debug.section(".debug_line_str")
    dies = {}
    stack = []
    root = None
    while r.p < r.end:
        need(len(dies) < 4096 and len(stack) <= 64, "die_bound")
        off = r.p
        code = r.uleb()
        if code == 0:
            need(stack, "unmatched_die_end")
            stack.pop()
            continue
        need(code in ab, "unknown_abbreviation")
        tag, child, attrs = ab[code]
        row = {"offset": off, "tag": tag, "attrs": {}, "forms": {}, "children": []}
        for a, form, implicit in attrs:
            if form == 1:
                v = r.uint(8)
            elif form == 5:
                v = r.uint(2)
            elif form == 7:
                v = r.uint(8)
            elif form == 8:
                v, stop = cstr(info, r.p)
                need(stop <= r.end, "inline_string_past_cu")
                r.p = stop
            elif form == 11:
                v = r.uint(1)
            elif form in (14, 31):
                v, _ = cstr(strings if form == 14 else line_strings, r.uint(4))
            elif form == 19:
                v = CU_START + r.uint(4)
                need(CU_START <= v < end, "die_reference_outside_selected_cu")
            elif form == 23:
                v = r.uint(4)
            elif form == 24:
                size = r.uleb()
                need(size <= 256, "expression_length")
                v = r.raw(size).hex()
            elif form == 25:
                v = True
            elif form == 33:
                v = implicit
            else:
                raise BinaryError("unsupported_dwarf_form")
            need(a not in row["attrs"], "duplicate_attribute")
            row["attrs"][a] = v
            row["forms"][a] = form
        dies[off] = row
        if stack:
            dies[stack[-1]]["children"].append(off)
        else:
            need(root is None, "multiple_cu_roots")
            root = off
        if child:
            stack.append(off)
    need(r.p == end and not stack, "complete_selected_cu")
    return dies, {"offset": CU_START, "length": length, "version": version,
                  "pointer_size": ptrsize, "abbrev_offset": aboff, "abbrev_end": abend,
                  "forms": sorted(forms), "die_count": len(dies)}


def locations(debug, off):
    data = debug.section(".debug_loclists")
    r = Reader(data, off)
    base = None
    entries = []
    for _ in range(16):
        op = r.uint(1)
        if op == 0:
            return entries, data[off:r.p].hex()
        if op == 6:
            base = r.uint(8)
        elif op == 4:
            need(base is not None, "location_base")
            start, end = base + r.uleb(), base + r.uleb()
            size = r.uleb()
            need(start < end and size <= 32, "bounded_location_expression")
            entries.append({"begin": start, "end": end, "expression_hex": r.raw(size).hex()})
        else:
            raise BinaryError("unsupported_selected_location_list_opcode")
    raise BinaryError("location_list_entry_count")


def source_lines(debug, off, comp_dir):
    """Decode the selected DWARF5 line header and its finite line program."""
    data = debug.section(".debug_line")
    strings = debug.section(".debug_line_str")
    r = Reader(data, off)
    length = r.uint(4)
    need(length <= 16384, "line_table_length")
    table_end = off + 4 + length
    need(table_end <= len(data), "line_table_end")
    r.end = table_end
    version, address_size, segment_size = r.uint(2), r.uint(1), r.uint(1)
    need((version, address_size, segment_size) == (5, 8, 0), "line_table_header")
    header_length = r.uint(4)
    header_end = r.p + header_length
    need(header_end <= table_end, "line_header_end")
    minimum, max_ops, default_stmt = r.uint(1), r.uint(1), r.uint(1)
    line_base = int.from_bytes(r.raw(1), "little", signed=True)
    line_range, opcode_base = r.uint(1), r.uint(1)
    need((minimum, max_ops, default_stmt, line_base, line_range, opcode_base) == (1, 1, 1, -5, 14, 13),
         "line_program_parameters")
    standard_lengths = list(r.raw(opcode_base - 1))
    need(standard_lengths == [0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1], "line_standard_op_lengths")

    def table_entries(max_count):
        nforms = r.uint(1)
        need(0 < nforms <= 4, "line_table_format_count")
        forms = [(r.uleb(), r.uleb()) for _ in range(nforms)]
        need(len({key for key, _ in forms}) == nforms, "line_table_duplicate_content")
        need(all(key in (1, 2) and form in (0x0F, 0x1F) for key, form in forms), "line_table_closed_forms")
        count = r.uleb()
        need(count <= max_count, "line_table_entry_count")
        entries = []
        for _ in range(count):
            entry = {}
            for key, form in forms:
                if form == 0x1F:
                    entry[key], _ = cstr(strings, r.uint(4))
                else:
                    entry[key] = r.uleb()
            entries.append(entry)
        return forms, entries

    directory_forms, raw_dirs = table_entries(64)
    file_forms, raw_files = table_entries(128)
    need(directory_forms == [(1, 0x1F)] and file_forms == [(1, 0x1F), (2, 0x0F)], "selected_line_table_forms")
    need(r.p == header_end, "complete_line_header")
    directories = [{"index": i, "path": d[1]} for i, d in enumerate(raw_dirs)]
    files = []
    for i, f in enumerate(raw_files):
        directory_index = f[2]
        need(directory_index < len(directories), "line_directory_index")
        directory = directories[directory_index]["path"]
        # This exact CU records directory[0] as its compilation directory.
        # Other relative directories are relative to that compilation directory.
        directory_path = directory if directory_index == 0 else posixpath.join(comp_dir, directory)
        source_path = posixpath.normpath(posixpath.join(directory_path, f[1]))
        files.append({"index": i, "name": f[1], "directory_index": directory_index,
                      "directory": directory, "source_path": source_path})
    need(files[1]["source_path"] == "elf/dl-deps.c", "deps_source_path")
    need(files[4]["source_path"] == "sysdeps/generic/ldsodefs.h", "prototype_source_path")
    need(files[21]["source_path"] == "dlfcn/dlfcn.h", "namespace_source_path")
    need(files[22]["source_path"] == "include/link.h", "link_map_source_path")

    rows = []
    state = {"address": 0, "file": 1, "line": 1, "column": 0, "is_stmt": bool(default_stmt)}

    def emit(end_sequence=False):
        need(len(rows) < 8192, "line_row_count")
        need(0 <= state["address"] < (1 << 64) and 0 <= state["file"] < len(files), "line_row_address_file")
        need(-1000000 <= state["line"] <= 1000000, "line_row_number")
        rows.append({**state, "end_sequence": end_sequence})

    while r.p < r.end:
        op = r.uint(1)
        if op == 0:
            size = r.uleb()
            need(1 <= size <= 32, "line_extended_opcode_length")
            extended = Reader(r.raw(size))
            subop = extended.uint(1)
            if subop == 1:
                emit(True)
                state = {"address": 0, "file": 1, "line": 1, "column": 0, "is_stmt": bool(default_stmt)}
            elif subop == 2:
                state["address"] = extended.uint(address_size)
            elif subop == 4:
                extended.uleb()  # discriminator does not alter source path/line
            else:
                raise BinaryError("line_extended_opcode")
            need(extended.p == extended.end, "complete_line_extended_opcode")
        elif op >= opcode_base:
            adjusted = op - opcode_base
            state["address"] += adjusted // line_range
            state["line"] += line_base + adjusted % line_range
            emit()
        elif op == 1:
            emit()
        elif op == 2:
            state["address"] += r.uleb()
        elif op == 3:
            state["line"] += r.sleb()
        elif op == 4:
            state["file"] = r.uleb()
        elif op == 5:
            state["column"] = r.uleb()
        elif op == 6:
            state["is_stmt"] = not state["is_stmt"]
        elif op in (7, 10, 11):
            pass  # basic_block / prologue_end / epilogue_begin
        elif op == 8:
            state["address"] += (255 - opcode_base) // line_range
        elif op == 9:
            state["address"] += r.uint(2)
        elif op == 12:
            r.uleb()  # ISA does not alter source path/line
        else:
            raise BinaryError("line_standard_opcode")
    need(r.p == table_end and rows[-1]["end_sequence"], "complete_line_program")
    selected = [x for x in rows if 0x3640 <= x["address"] < 0x3677 and not x["end_sequence"]]
    need([x for x in selected if x["address"] == 0x3671] ==
         [{"address": 0x3671, "file": 1, "line": 64, "column": 13, "is_stmt": False, "end_sequence": False}],
         "return_site_line_row")
    return {"offset": off, "length": length, "version": version,
            "header_length": header_length, "program_offset": header_end,
            "source_content_hashes_present": False,
            "directories": directories, "files": files,
            "openaux_rows": selected, "total_row_count": len(rows)}


def _derive_binary_facts(loader_bytes, debug_bytes):
    loader = ELF(loader_bytes, 225672, LOADER_SHA)
    debug = ELF(debug_bytes, 556488, DEBUG_SHA)
    original_id, debug_id = loader.identity(), debug.identity()
    dl = loader.section(".gnu_debuglink")
    name, off = cstr(dl, 0)
    crc = int.from_bytes(take(dl, (off + 3) & ~3, 4), "little")
    need(name == BUILD_ID[2:] + ".debug", "debuglink_filename")
    need(crc == zlib.crc32(debug.data), "debuglink_crc32")

    symbols = debug.symbols()
    symbol_records = {}
    for name, value, size in (("openaux", 0x3640, 55), ("_dl_map_object", 0x93A0, 2859),
                              ("_dl_map_object_deps", 0x3680, 3979),
                              ("_dl_map_object.cold", 0x141E, 62)):
        need(len(symbols.get(name, [])) == 1, "unique_selected_symbol")
        row = symbols[name][0]
        need((row["value"], row["size"], row["type"], row["section_index"]) == (value, size, 2, 10),
             "selected_symbol_location")
        symbol_records[name] = row

    # This fixed, finite decoder admits only the actual instruction sequence.
    # Each opcode template includes ModRM / displacement bytes where present.
    templates = [
        ("53", "push rbx"),
        ("4889fb", "mov rbx,rdi"),
        ("488b3f", "mov rdi,[rdi]"),
        ("8b4b08", "mov ecx,[rbx+8]"),
        ("488b7318", "mov rsi,[rbx+24]"),
        ("0fb68754030000", "movzx eax,byte [rdi+852]"),
        ("448b430c", "mov r8d,[rbx+12]"),
        ("4c8b4f30", "mov r9,[rdi+48]"),
        ("89c2", "mov edx,eax"),
        ("83e203", "and edx,3"),
        ("a803", "test al,3"),
        ("b801000000", "mov eax,1"),
        ("0f44d0", "cmove edx,eax"),
        ("e82f5d0000", "call rel32"),
        ("48894320", "mov [rbx+32],rax"),
        ("5b", "pop rbx"),
        ("c3", "ret"),
    ]
    instructions = []
    pc = 0x3640
    for encoded, meaning in templates:
        raw = bytes.fromhex(encoded)
        file_off = loader.offset(pc, len(raw))
        need(take(loader.data, file_off, len(raw)) == raw, "instruction_bytes")
        row = {"vaddr": pc, "file_offset": file_off, "size": len(raw), "hex": encoded,
               "decoded": meaning}
        if raw[0] == 0xE8:
            row["target_vaddr"] = pc + len(raw) + int.from_bytes(raw[1:], "little", signed=True)
            row["return_vaddr"] = pc + len(raw)
            need((row["target_vaddr"], row["return_vaddr"]) == (0x93A0, 0x3671), "direct_call_relationship")
        instructions.append(row)
        pc += len(raw)
    need(pc == 0x3677, "complete_function_instruction_partition")

    dies, cu = parse_cu(debug)
    attrs = lambda n: dies[n]["attrs"]
    need((attrs(0xBCB1)[3], attrs(0xBCB1)[0x1B]) == ("dl-deps.c", "./elf"), "cu_source_identity")
    lines = source_lines(debug, attrs(0xBCB1)[0x10], attrs(0xBCB1)[0x1B])
    cu.update({"die_offset": 0xBCB1, "name": attrs(0xBCB1)[3],
               "comp_dir": attrs(0xBCB1)[0x1B], "producer": attrs(0xBCB1)[0x25],
               "statement_list_offset": attrs(0xBCB1)[0x10],
               "line_table": lines})
    source_declarations = []
    for die_offset in (0xF151, 0xE2F9, 0xC4B0, 0xE3B4, 0xC3FF, 0xC306):
        declaration = dies[die_offset]
        declaration_attrs = declaration["attrs"]
        need(all(key in declaration_attrs for key in (3, 0x3A, 0x3B)), "source_declaration_attributes")
        file_index = declaration_attrs[0x3A]
        need(0 <= file_index < len(lines["files"]), "source_declaration_file_index")
        source_declarations.append({
            "die_offset": die_offset,
            "name": declaration_attrs[3],
            "tag": declaration["tag"],
            "decl_file": file_index,
            "decl_line": declaration_attrs[0x3B],
            "source_path": lines["files"][file_index]["source_path"],
        })
    need(dies[0xF151]["tag"] == 0x2E and attrs(0xF151)[3] == "openaux", "openaux_die")
    need((attrs(0xF151)[0x11], attrs(0xF151)[0x12]) == (0x3640, 55), "openaux_dwarf_range")
    need(dies[0xF193]["tag"] == 0x48 and 0xF193 in dies[0xF151]["children"], "child_callsite")
    need(attrs(0xF193)[0x7D] == 0x3671 and attrs(0xF193)[0x7F] == 0xE3B4, "callsite_origin")
    need(attrs(0xE3B4)[3] == "_dl_map_object" and attrs(0xE3B4)[0x49] == 0xC9A3, "callee_return_pointer_type")
    need(dies[0xC9A3]["tag"] == 0x0F and attrs(0xC9A3)[0x49] == 0xC4B0, "link_map_pointer")
    need(attrs(0xC9A3)[0x0B] == 8, "link_map_pointer_width")
    need(0xF180 in dies[0xF151]["children"] and attrs(0xF180)[3] == "args", "args_variable")
    need(attrs(0xF180)[0x49] == 0xF1A1 and attrs(0xF1A1)[0x49] == 0xE2F9, "args_type_chain")
    need(attrs(0xF1A1)[0x0B] == 8, "args_pointer_width")
    locs, loc_hex = locations(debug, attrs(0xF180)[2])
    live = [x for x in locs if x["begin"] <= 0x3671 < x["end"]]
    need(live == [{"begin": 0x3647, "end": 0x3676, "expression_hex": "53"}], "live_args_is_rbx")

    def scalar_type(off):
        seen = set()
        chain = []
        for _ in range(8):
            need(off in dies and off not in seen, "bounded_type_chain")
            seen.add(off)
            d = dies[off]
            a = d["attrs"]
            chain.append(off)
            if d["tag"] in (0x0F, 0x24, 0x04):
                return {"size_bytes": a[0x0B], "kind": d["tag"], "encoding": a.get(0x3E), "chain": chain}
            need(d["tag"] in (0x16, 0x26, 0x35), "scalar_typedef_or_qualifier")
            off = a[0x49]
        raise BinaryError("type_depth")

    def full_type_chain(off):
        seen = set()
        chain = []
        for _ in range(12):
            need(off in dies and off not in seen, "bounded_full_type_chain")
            seen.add(off)
            d = dies[off]
            a = d["attrs"]
            row = {"die_offset": off, "tag": d["tag"], "name": a.get(3),
                   "size_bytes": a.get(0x0B), "encoding": a.get(0x3E)}
            if 0x3A in a:
                need(a[0x3A] < len(lines["files"]), "type_source_file_index")
                row.update({"decl_file": a[0x3A], "decl_line": a.get(0x3B),
                            "source_path": lines["files"][a[0x3A]]["source_path"]})
            chain.append(row)
            if 0x49 not in a:
                return chain
            need(d["tag"] in (0x0F, 0x16, 0x26, 0x35, 0x04), "full_type_chain_tag")
            off = a[0x49]
        raise BinaryError("full_type_depth")

    def members(structoff, name, size, expected):
        a = attrs(structoff)
        need(dies[structoff]["tag"] == 0x13 and (a[3], a[0x0B]) == (name, size), "structure_identity")
        out = {}
        children = dies[structoff]["children"]
        for field, offset, width in expected:
            found = [dies[n] for n in children if attrs(n).get(3) == field]
            need(len(found) == 1, "unique_selected_field")
            d = found[0]
            a = d["attrs"]
            typ = scalar_type(a[0x49])
            need(a[0x38] == offset and typ["size_bytes"] == width, "member_layout")
            out[field] = {"die_offset": d["offset"], "offset_bytes": offset,
                          "size_bytes": width, "type": typ,
                          "full_type_chain": full_type_chain(a[0x49]),
                          "decl_file": a[0x3A], "decl_line": a[0x3B],
                          "source_path": lines["files"][a[0x3A]]["source_path"]}
        return out

    args = members(0xE2F9, "openaux_args", 40,
                   [("map", 0, 8), ("trace_mode", 8, 4), ("open_mode", 12, 4),
                    ("strtab", 16, 8), ("name", 24, 8), ("aux", 32, 8)])
    maps = members(0xC4B0, "link_map", 1208,
                   [("l_addr", 0, 8), ("l_ld", 16, 8), ("l_real", 40, 8), ("l_ns", 48, 8)])
    need(maps["l_ns"]["type"]["encoding"] == 5, "signed_namespace_type")
    need(maps["l_addr"]["type"]["encoding"] == 7, "unsigned_address_type")
    for field in ("map", "aux"):
        need(args[field]["type"]["chain"] == [0xC9A3], "args_link_map_pointer_type")
    for field in ("trace_mode", "open_mode"):
        need(args[field]["type"]["kind"] == 0x24 and args[field]["type"]["encoding"] == 5,
             "args_signed_int_type")
    for field in ("strtab", "name"):
        need([x["die_offset"] for x in args[field]["full_type_chain"]] == [0xBD47, 0xBD53, 0xBD4C],
             "args_const_char_pointer_type")
    need(maps["l_real"]["type"]["chain"] == [0xC9A3], "real_map_pointer_type")
    need([x["die_offset"] for x in maps["l_ld"]["full_type_chain"]] == [0xCCD7, 0xC306, 0xC2DF],
         "dynamic_section_pointer_type")
    need(0xC605 in dies[0xC4B0]["children"] and attrs(0xC605)[0x49] == 0xCE67, "l_type_membership")
    need(attrs(0xC605)[3] == "l_type" and attrs(0xC605)[0x0D] == 2
         and attrs(0xC605)[0x6B] == 6816, "l_type_bitfield")
    enums = {attrs(x)[3]: attrs(x)[0x1C] for x in dies[0xCE67]["children"]}
    need(enums == {"lt_executable": 0, "lt_library": 1, "lt_loaded": 2}, "l_type_enumerators")
    ranges = []
    for role, start, length in (("openaux", 0x3640, 55), ("map_object_hot", 0x93A0, 2859),
                                ("map_object_cold", 0x141E, 62),
                                ("map_object_return", 0x94D3, 21),
                                ("args_initialization", 0x38A0, 63),
                                ("needed_name_branch", 0x3A65, 45),
                                ("needed_callback", 0x39B3, 33)):
        off = loader.offset(start, length)
        raw = take(loader.data, off, length)
        ranges.append({"role": role, "vaddr": start, "file_offset": off, "size_bytes": length,
                       "sha256": sha(raw), **({"hex": raw.hex()} if length <= 128 else {})})
    need(take(loader.data, loader.offset(0x94D3, 21), 21).hex() ==
         "4881c4d80300004c89f85b5d415c415d415e415fc3", "callee_normal_return_epilogue")
    fde_off = loader.sections[".eh_frame"]["offset"] + 0x320
    fde = take(loader.data, fde_off, 28)
    need(fde.hex() == "18000000240300004833fdff3700000000410e108302750e08000000", "original_openaux_cfi")
    need(fde_off + 8 + int.from_bytes(fde[8:12], "little", signed=True) == 0x3640, "cfi_pc_relative_start")
    need(int.from_bytes(fde[12:16], "little") == 55, "cfi_function_range")

    return {
        "record_type": "required_gate_idempotence_loader_binary_facts_v0",
        "loader": original_id, "debug": debug_id,
        "debuglink": {"filename": BUILD_ID[2:] + ".debug", "crc32": f"{crc:08x}"},
        "byte_and_debug_correlation_passed": True,
        "signed_distribution_provenance_verified_by_this_script": False,
        "full_source_build_provenance_gate_passed_by_this_script": False,
        "source_build_reproduced": False,
        "runtime_acquisition_performed": False, "runtime_resolution_observed": False,
        "hardware_stop_qualified": False, "execution_authorized": False,
        "symbols": symbol_records, "cu": cu,
        "source_declarations": source_declarations,
        "openaux_instructions": instructions, "original_byte_ranges": ranges,
        "return_checkpoint": {"vaddr": 0x3671, "file_offset": loader.offset(0x3671, 4),
                              "instruction_size": 4, "instruction_hex": "48894320",
                              "before_result_store": True, "provider_register": "RAX",
                              "args_register": "RBX", "args_aux_fresh": False,
                              "args_assumed_in_rdi": False,
                              "callsite_die": 0xF193, "callee_declaration_die": 0xE3B4},
        "args_location": {"variable_die": 0xF180, "location_list_offset": attrs(0xF180)[2],
                          "raw_location_list_hex": loc_hex, "entries": locs},
        "openaux_args": {"die_offset": 0xE2F9, "size_bytes": 40, "members": args},
        "link_map": {"die_offset": 0xC4B0, "size_bytes": 1208, "required_prefix_bytes": 56,
                     "members": maps, "l_type_bit_offset": 6816, "l_type_bit_size": 2,
                     "l_type_enumerators": enums},
        "original_eh_frame": {"section_offset": 0x320, "file_offset": fde_off,
                              "size_bytes": 28, "sha256": sha(fde), "hex": fde.hex()},
        "runtime_recipe_conditions": [
            "Fresh original loader load bias and live RIP must yield load_bias + 0x3671.",
            "Read args from live RBX, provider link_map from live RAX; never recover args from RDI.",
            "Two stopped samples must agree on registers and each bounded memory range.",
            "Read 40 bytes from args, 56 bytes from args.map, and 56 bytes from provider.",
            "For each map require l_ns == 0, l_real == the map pointer, and current mapped-file identity.",
            "Bind l_addr and l_ld against fresh original-object PT_LOAD and PT_DYNAMIC relationships.",
            "Read bounded args.name bytes and require exact original consumer dynstr pointer and bytes.",
            "Uniquely join original consumer identity and name to its static DT_NEEDED occurrence.",
            "Do not accept stale args.aux, occurrence order, pathname alone, or precomputed provider expectations.",
        ],
    }


def derive_binary_facts(*, loader_bytes, debug_bytes):
    """Return exact-byte-derived facts for the single admitted original pair.

    The function is data-only: it performs no filesystem access, subprocesses,
    target loading, or target execution. Provenance and authorization remain
    independent requirements handled by the calling profile.
    """
    try:
        return _derive_binary_facts(loader_bytes, debug_bytes)
    except BinaryError:
        raise
    except (KeyError, IndexError, struct.error, UnicodeError, zlib.error, OverflowError):
        raise BinaryError("malformed_binary") from None
