"""Offline decision for the exact original interpreter startup arguments.

The selected source, debug and instruction relationships support trace_mode=0
and open_mode=0 under the stated original invocation assumptions.  This module
does not observe those assumptions in a process, establish a source rebuild,
authenticate a historical build, or authorize an acquisition.  Target files
are parsed as data; no external decoder, compiler or target is executed.
"""

from __future__ import annotations

import copy
import hashlib
import posixpath
import struct

import required_gate_idempotence_loader_binary_v0 as binary
import required_gate_idempotence_loader_source_v0 as source


INPUT_BINDINGS = {
    "libc6_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 2846580,
        "sha256": "967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9"},
    "libc6-dbg_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 7373052,
        "sha256": "0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7"},
    "Sources.xz": {
        "size_bytes": 10540436,
        "sha256": "6002f81f463a2d976d84b34170367cc16da2d60bd0ba9ab9d868d6e1c1a935d9"},
    "glibc_2.41-12+deb13u4.dsc": {
        "size_bytes": 7576,
        "sha256": "0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e"},
    "glibc_2.41.orig.tar.xz": {
        "size_bytes": 20323540,
        "sha256": "f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998"},
    "glibc_2.41-12+deb13u4.debian.tar.xz": {
        "size_bytes": 499524,
        "sha256": "dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d"},
}
LOADER_BINDING = {
    "size_bytes": 225672,
    "sha256": "c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307"}
DEBUG_BINDING = {
    "size_bytes": 556488,
    "sha256": "34ab07395545cf33df8e551e809ebee6fd3fc2707ed848e390872dce539c4a78"}
SELECTED_SOURCE_BINDINGS = {
    "elf/rtld.c": {
        "size_bytes": 87900,
        "sha256": "e6f5a773bff5eb4d2312ce456992d8d3db849dcc4761adfe210e0fbcdc226b6f"},
    "elf/dl-main.h": {
        "size_bytes": 3961,
        "sha256": "43b6753c2c455a6ffb600316418a5eae2c123e63e5e169664b79230c6e7a0441"},
    "elf/dl-environ.c": {
        "size_bytes": 1991,
        "sha256": "e9a5cabdc31d397a4e58ce7f3a2f0bd3c506b30d0743fb5a086467b37a877ed5"},
    "sysdeps/unix/sysv/linux/dl-parse_auxv.h": {
        "size_bytes": 2705,
        "sha256": "c06c8be5a27c3cf0b5b31bf54758791bc96b1b417694905723a4a172d58d209f"},
    "sysdeps/unix/sysv/linux/dl-sysdep.c": {
        "size_bytes": 8817,
        "sha256": "b0df8f3fea3a01931a128317f21371bebaa20eca13b2009c5363f950e7c5d2bc"},
}
REUSED_SOURCE_BINDINGS = {
    "elf/dl-deps.c": {
        "size_bytes": 17592,
        "sha256": "2f23f25c68bdde0ca3c30a3186861be716d7790b17c4b99681bc8c5d9e554f8b"},
}
ORIGINAL_SOURCE_BINDINGS = {
    **SELECTED_SOURCE_BINDINGS, **REUSED_SOURCE_BINDINGS,
    "elf/rtld.c": {
        "size_bytes": 86992,
        "sha256": "dcc52dea8284139c8a55ac21bddd678d08ae9dc3b1de2d5dfc6342664174192e"},
}
ORIGINAL_INVOCATION = {
    "entry_route": "kernel_interpreter_startup",
    "argv": ["bubblewrap"],
    "cwd": "/",
    "environment": {"LC_ALL": "C", "TZ": "UTC"},
    "auxv_at_secure": 0,
    "launcher_entry_differs_from_loader_entry": True,
}
EXPECTED_MODES = {"trace_mode": 0, "open_mode": 0}
BOUNDARY = {
    "selected_startup_mode_decision_verified": True,
    "global_control_flow_or_source_build_equivalence_proved": False,
    "original_invocation_observed": False,
    "source_binary_equivalence_verified": False,
    "authenticated_build_provenance": False,
    "source_build_gate_satisfied": False,
    "live_private_abi_readout_qualified": False,
    "two_slot_breakpoint_qualified": False,
    "native_acquisition_performed": False,
    "consumer_resolution_observed": False,
    "acquisition_ready": False,
    "metric_pass": None,
    "authority_effect": "none",
}


class StartupError(ValueError):
    """Stable rejection code, without inspected input text or paths."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise StartupError(code)


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _bound(raw, expected, code):
    _need(type(raw) is bytes, code + "_type")
    _need(len(raw) == expected["size_bytes"], code + "_size")
    _need(hashlib.sha256(raw).hexdigest() == expected["sha256"], code + "_sha256")


def _preflight(inputs, loader, debug):
    _need(type(inputs) is dict and set(inputs) == set(INPUT_BINDINGS),
          "startup_input_inventory")
    # Check every raw size before the first hash or decompression.
    for name, expected in INPUT_BINDINGS.items():
        _need(type(inputs[name]) is bytes, "startup_input_type")
        _need(len(inputs[name]) == expected["size_bytes"], "startup_input_size")
    for raw, expected, label in ((loader, LOADER_BINDING, "loader"),
                                 (debug, DEBUG_BINDING, "debug")):
        _need(type(raw) is bytes, "startup_" + label + "_type")
        _need(len(raw) == expected["size_bytes"], "startup_" + label + "_size")
    for name, expected in INPUT_BINDINGS.items():
        _bound(inputs[name], expected, "startup_input")
    _bound(loader, LOADER_BINDING, "startup_loader")
    _bound(debug, DEBUG_BINDING, "startup_debug")


def _original_sources(raw):
    """Read the same closed tar dialect, with a separate selected roster."""
    selected = {source.SOURCE_ROOT + "/" + name for name in ORIGINAL_SOURCE_BINDINGS}
    reader = source._XZReader(raw)
    entries, retained = {}, {}
    retained_total = payload_total = 0
    while True:
        header = reader.exact(512)
        if not any(header):
            _need(not any(reader.exact(512)), "startup_tar_terminator")
            while True:
                tail = reader.read(65536)
                if not tail:
                    break
                _need(not any(tail), "startup_tar_trailing_data")
            _need(reader.total % 512 == 0, "startup_tar_alignment")
            break
        _need(len(entries) < source.SOURCE_MEMBER_COUNT_LIMIT, "startup_tar_member_limit")
        _need(source._octal(header[148:156]) ==
              sum(header[:148]) + 8 * 32 + sum(header[156:]), "startup_tar_checksum")
        magic = header[257:265]
        if magic == b"ustar\x0000":
            prefix = source._tar_text(header[345:500])
            _need(not any(header[500:]), "startup_tar_extension")
        elif magic == b"ustar  \x00":
            _need(not any(header[345:]), "startup_tar_extension")
            prefix = ""
        else:
            _need(not any(header[257:]), "startup_tar_format")
            prefix = ""
        kind = header[156:157]
        _need(kind in {b"\0", b"0", b"1", b"2", b"5"}, "startup_tar_extension")
        name = source._tar_text(header[:100])
        if prefix:
            name = prefix + "/" + name
        path = source._path(name, directory=kind == b"5")
        _need(path not in entries, "startup_tar_duplicate_path")
        _need(path == source.SOURCE_ROOT or path.startswith(source.SOURCE_ROOT + "/"),
              "startup_tar_root")
        _need(source._octal(header[100:108]) <= 0o7777, "startup_tar_mode")
        for field in (header[108:116], header[116:124], header[136:148]):
            source._octal(field)
        size = source._octal(header[124:136])
        _need(size <= source.SOURCE_TAR_LIMIT, "startup_tar_payload_limit")
        regular = kind in {b"\0", b"0"}
        _need(regular or size == 0, "startup_tar_nonregular_payload")
        link = source._tar_text(header[157:257])
        _need(bool(link) if kind in {b"1", b"2"} else not link, "startup_tar_link")
        entries[path] = kind
        keep = path in selected
        if keep:
            _need(regular and 0 < size <= source.SOURCE_MEMBER_LIMIT,
                  "startup_tar_selected_type_size")
            retained_total += size
            _need(retained_total <= source.RETAINED_SOURCE_LIMIT,
                  "startup_tar_retained_limit")
        payload_total += size
        parts, left = [], size
        while left:
            part = reader.exact(min(left, 65536))
            if keep:
                parts.append(part)
            left -= len(part)
        _need(not any(reader.exact((-size) % 512)), "startup_tar_padding")
        if keep:
            retained[path.removeprefix(source.SOURCE_ROOT + "/")] = b"".join(parts)
    for path in entries:
        parts = path.split("/")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            _need(parent not in entries or entries[parent] == b"5",
                  "startup_tar_ancestor_not_directory")
    _need(set(retained) == set(ORIGINAL_SOURCE_BINDINGS), "startup_tar_selected_missing")
    for name, expected in ORIGINAL_SOURCE_BINDINGS.items():
        _bound(retained[name], expected, "startup_original_source")
    return retained, {
        "compressed": _binding(raw),
        "decoded": {"size_bytes": reader.total, "sha256": reader.digest.hexdigest()},
        "member_count": len(entries), "member_payload_size_bytes": payload_total,
        "selected_member_count": len(retained), "selected_payload_size_bytes": retained_total,
    }


def _source_facts(inputs):
    original, archive = _original_sources(inputs["glibc_2.41.orig.tar.xz"])
    debian, debian_archive = source._source_tar(
        inputs["glibc_2.41-12+deb13u4.debian.tar.xz"], original=False)
    series = debian["debian/patches/series"]
    _bound(series, source.SERIES_BINDING, "startup_patch_series")
    order = source._series(series)
    _need(len(order) == 80, "startup_patch_count")
    sources = dict(original)
    steps = {path: [] for path in sources}
    patches = []
    for ordinal, member in enumerate(order):
        _need(member in debian, "startup_patch_member_missing")
        raw = debian[member]
        blocks = source._scan_patch(raw)
        selected, selected_hunks = [], 0
        for block in blocks:
            touched = set(sources).intersection({block["old"], block["new"], block["index"]})
            if not touched:
                continue
            _need(len(touched) == 1 and block["old"] == block["new"] and
                  block["old"] in touched and block["index"] in {None, block["old"]},
                  "startup_selected_patch_path")
            path = next(iter(touched))
            before = _binding(sources[path])
            sources[path], hunks = source._apply_hunks(sources[path], block["hunks"])
            steps[path].append({"order": ordinal, "member": member,
                                "hunk_count": len(hunks), "hunks": hunks,
                                "before": before, "after": _binding(sources[path])})
            selected.append(path)
            selected_hunks += len(hunks)
        patches.append({"order": ordinal, "member": member, "binding": _binding(raw),
                        "file_diff_count": len(blocks),
                        "hunk_count": sum(len(block["hunks"]) for block in blocks),
                        "selected_files": selected, "selected_hunk_count": selected_hunks})
    files = []
    for path, expected in {**SELECTED_SOURCE_BINDINGS, **REUSED_SOURCE_BINDINGS}.items():
        _bound(sources[path], expected, "startup_patched_source")
        files.append({"path": path,
                      "role": "additional_startup_source" if path in SELECTED_SOURCE_BINDINGS
                      else "previously_selected_argument_forwarding_source",
                      "original": {"member": source.SOURCE_ROOT + "/" + path,
                                   "binding": _binding(original[path])},
                      "patched": {"binding": _binding(sources[path])},
                      "patch_steps": steps[path]})
    _need([(x["order"], x["member"], x["hunk_count"]) for x in steps["elf/rtld.c"]] ==
          [(0, "debian/patches/git-updates.diff", 6)], "startup_rtld_patch_recipe")
    _need(all(not steps[name] for name in sources if name != "elf/rtld.c"),
          "startup_other_patch_recipe")
    _need(sum(x["file_diff_count"] for x in patches) == 478 and
          sum(x["hunk_count"] for x in patches) == 803, "startup_all_patch_inventory")
    return {"original_archive": archive, "debian_archive": debian_archive,
            "additional_source_count": 5, "reused_source_count": 1,
            "patch_series": {"member": "debian/patches/series", "binding": _binding(series),
                             "active_patch_count": len(order),
                             "patch_policy": source.PATCH_POLICY,
                             "all_active_patches_scanned": True, "patches": patches},
            "files": files}, sources


def _semantic_ranges(sources):
    selections = (
        ("normal_mode_initialization", "elf/rtld.c", 293, 304,
         (b"state->mode = rtld_mode_normal;",)),
        ("startup_and_interpreter_selection", "elf/rtld.c", 1356, 1390,
         (b"dl_main_state_init (&state);", b"skip_env = process_envvars (&state);",
          b"if (*user_entry == (ElfW(Addr)) ENTRY_POINT)")),
        ("startup_dependency_call", "elf/rtld.c", 1950, 1957,
         (b"_dl_map_object_deps (main_map, preloads, npreloads,",
          b"state.mode == rtld_mode_trace, 0);")),
        ("secure_environment_mode_guard", "elf/rtld.c", 2515, 2582,
         (b"process_envvars_secure", b"state->mode != rtld_mode_normal")),
        ("default_environment_selection", "elf/rtld.c", 2586, 2605,
         (b"process_envvars_default", b"_dl_next_ld_env_entry (&runp)")),
        ("trace_environment_assignment", "elf/rtld.c", 2702, 2711,
         (b'"TRACE_LOADED_OBJECTS"', b"state->mode = rtld_mode_trace;")),
        ("secure_or_default_environment", "elf/rtld.c", 2737, 2746,
         (b"process_envvars_secure (state);", b"process_envvars_default (state);")),
        ("mode_enumerators", "elf/dl-main.h", 62, 67,
         (b"rtld_mode_normal, rtld_mode_list, rtld_mode_verify, rtld_mode_trace,",)),
        ("startup_state_mode_member", "elf/dl-main.h", 71, 102,
         (b"enum rtld_mode mode;",)),
        ("only_LD_environment_entries", "elf/dl-environ.c", 24, 49,
         (b"_dl_next_ld_env_entry", b"(*current)[0] == 'L'",
          b"(*current)[1] == 'D' && (*current)[2] == '_'")),
        ("dependency_mode_arguments", "elf/dl-deps.c", 140, 142,
         (b"int trace_mode, int open_mode)",)),
        ("copy_modes_to_openaux_args", "elf/dl-deps.c", 208, 232,
         (b"args.trace_mode = trace_mode;", b"args.open_mode = open_mode;")),
        ("openaux_forwarding", "elf/dl-deps.c", 46, 68,
         (b"args->trace_mode, args->open_mode,", b"args->map->l_ns);")),
        ("initial_vector_arguments", "sysdeps/unix/sysv/linux/dl-sysdep.c", 76, 97,
         (b"_environ = _dl_argv + _dl_argc + 1;", b"_dl_parse_auxv (GLRO(dl_auxv), auxv_values);",
          b"args->user_entry = auxv_values[AT_ENTRY];")),
        ("auxiliary_vector_secure_flag", "sysdeps/unix/sysv/linux/dl-parse_auxv.h", 26, 47,
         (b"auxv_values[av->a_type] = av->a_un.a_val;",
          b"__libc_enable_secure = auxv_values[AT_SECURE];")),
        ("forward_initial_entry_to_dl_main", "sysdeps/unix/sysv/linux/dl-sysdep.c", 99, 143,
         (b"_dl_sysdep_parse_arguments (start_argptr, &dl_main_args);",
          b"&dl_main_args.user_entry, GLRO(dl_auxv));")),
    )
    rows = []
    for role, path, first, last, tokens in selections:
        lines = sources[path].split(b"\n")
        _need(1 <= first <= last < len(lines), "startup_source_line_bounds")
        raw = b"\n".join(lines[first - 1:last]) + b"\n"
        _need(all(token in raw for token in tokens), "startup_source_semantic_range")
        rows.append({"role": role, "source_path": path,
                     "first_physical_line": first, "last_physical_line": last,
                     "range": _binding(raw), "source": _binding(sources[path])})
    return rows


def _parse_rtld_cu(debug):
    start, expected_length, expected_abbrev = 0x80170, 0xA94D, 0x1024C
    info = debug.section(".debug_info")
    r = binary.Reader(info, start)
    length = r.uint(4)
    _need(length == expected_length, "startup_cu_length")
    r.end = start + 4 + length
    _need(r.end <= len(info), "startup_cu_end")
    version, unit_type, pointer_size, aboff = r.uint(2), r.uint(1), r.uint(1), r.uint(4)
    _need((version, unit_type, pointer_size, aboff) == (5, 1, 8, expected_abbrev),
          "startup_cu_header")
    ab, forms, abend = binary.abbrevs(debug.section(".debug_abbrev"), aboff)
    _need(forms == {1, 5, 7, 8, 11, 14, 19, 23, 24, 25, 31, 33},
          "startup_cu_forms")
    strings = debug.section(".debug_str")
    line_strings = debug.section(".debug_line_str")
    dies, stack, root = {}, [], None
    while r.p < r.end:
        _need(len(dies) < 8192 and len(stack) <= 64, "startup_die_bound")
        off, code = r.p, r.uleb()
        if code == 0:
            _need(bool(stack), "startup_die_unmatched_end")
            stack.pop()
            continue
        _need(code in ab, "startup_die_abbreviation")
        tag, child, attributes = ab[code]
        row = {"offset": off, "tag": tag, "attrs": {}, "children": []}
        for attribute, form, implicit in attributes:
            if form == 1:
                value = r.uint(8)
            elif form == 5:
                value = r.uint(2)
            elif form == 7:
                value = r.uint(8)
            elif form == 8:
                value, stop = binary.cstr(info, r.p)
                _need(stop <= r.end, "startup_inline_string_end")
                r.p = stop
            elif form == 11:
                value = r.uint(1)
            elif form in (14, 31):
                value, _ = binary.cstr(strings if form == 14 else line_strings, r.uint(4))
            elif form == 19:
                value = start + r.uint(4)
                _need(start <= value < r.end, "startup_die_reference")
            elif form == 23:
                value = r.uint(4)
            elif form == 24:
                size = r.uleb()
                _need(size <= 256, "startup_expression_size")
                value = r.raw(size).hex()
            elif form == 25:
                value = True
            elif form == 33:
                value = implicit
            else:
                raise StartupError("startup_cu_form")
            _need(attribute not in row["attrs"], "startup_duplicate_attribute")
            row["attrs"][attribute] = value
        dies[off] = row
        if stack:
            dies[stack[-1]]["children"].append(off)
        else:
            _need(root is None, "startup_multiple_cu_roots")
            root = off
        if child:
            stack.append(off)
    _need(r.p == r.end and not stack, "startup_complete_cu")
    return dies, {"offset": start, "length": length, "version": version,
                  "pointer_size": pointer_size, "abbrev_offset": aboff,
                  "abbrev_end": abend, "forms": sorted(forms),
                  "die_count": len(dies), "die_offset": root}


def _rtld_lines(debug, offset, comp_dir):
    """Decode only the pinned RTLD DWARF5 line-table dialect."""
    data, strings = debug.section(".debug_line"), debug.section(".debug_line_str")
    r = binary.Reader(data, offset)
    length = r.uint(4)
    _need(length == 18247 and offset == 0x1C930, "startup_line_table_identity")
    r.end = offset + 4 + length
    _need(r.end <= len(data), "startup_line_table_end")
    version, address_size, segment_size = r.uint(2), r.uint(1), r.uint(1)
    _need((version, address_size, segment_size) == (5, 8, 0), "startup_line_header")
    header_length = r.uint(4)
    header_end = r.p + header_length
    _need(header_end <= r.end, "startup_line_header_end")
    minimum, max_ops, default_stmt = r.uint(1), r.uint(1), r.uint(1)
    line_base = int.from_bytes(r.raw(1), "little", signed=True)
    line_range, opcode_base = r.uint(1), r.uint(1)
    _need((minimum, max_ops, default_stmt, line_base, line_range, opcode_base) ==
          (1, 1, 1, -5, 14, 13), "startup_line_parameters")
    _need(list(r.raw(12)) == [0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1],
          "startup_line_standard_lengths")

    def entries(max_count, expected_forms):
        count = r.uint(1)
        _need(0 < count <= 4, "startup_line_form_count")
        forms = [(r.uleb(), r.uleb()) for _ in range(count)]
        _need(forms == expected_forms, "startup_line_forms")
        count = r.uleb()
        _need(count <= max_count, "startup_line_entry_count")
        rows = []
        for _ in range(count):
            row = {}
            for key, form in forms:
                row[key] = (binary.cstr(strings, r.uint(4))[0]
                            if form == 0x1F else r.uleb())
            rows.append(row)
        return rows

    directories = entries(64, [(1, 0x1F)])
    raw_files = entries(128, [(1, 0x1F), (2, 0x0F)])
    _need(r.p == header_end, "startup_complete_line_header")
    files = []
    for index, row in enumerate(raw_files):
        directory_index = row[2]
        _need(directory_index < len(directories), "startup_line_directory_index")
        directory = directories[directory_index][1]
        base = directory if directory_index == 0 else posixpath.join(comp_dir, directory)
        files.append({"index": index, "source_path": posixpath.normpath(posixpath.join(base, row[1]))})
    _need(files[1]["source_path"] == "elf/rtld.c" and
          files[13]["source_path"] == "elf/dl-main.h", "startup_line_source_paths")
    rows = []
    state = {"address": 0, "file": 1, "line": 1, "column": 0, "is_stmt": True}

    def emit(end_sequence=False):
        _need(len(rows) < 16384 and 0 <= state["address"] < 1 << 64 and
              0 <= state["file"] < len(files) and -1000000 <= state["line"] <= 1000000,
              "startup_line_row_bounds")
        rows.append({**state, "end_sequence": end_sequence})

    while r.p < r.end:
        opcode = r.uint(1)
        if opcode == 0:
            size = r.uleb()
            _need(1 <= size <= 32, "startup_line_extended_length")
            extended = binary.Reader(r.raw(size))
            subop = extended.uint(1)
            if subop == 1:
                emit(True)
                state = {"address": 0, "file": 1, "line": 1, "column": 0, "is_stmt": True}
            elif subop == 2:
                state["address"] = extended.uint(8)
            elif subop == 4:
                extended.uleb()
            else:
                raise StartupError("startup_line_extended_opcode")
            _need(extended.p == extended.end, "startup_line_extended_end")
        elif opcode >= opcode_base:
            adjusted = opcode - opcode_base
            state["address"] += adjusted // line_range
            state["line"] += line_base + adjusted % line_range
            emit()
        elif opcode == 1:
            emit()
        elif opcode == 2:
            state["address"] += r.uleb()
        elif opcode == 3:
            state["line"] += r.sleb()
        elif opcode == 4:
            state["file"] = r.uleb()
        elif opcode == 5:
            state["column"] = r.uleb()
        elif opcode == 6:
            state["is_stmt"] = not state["is_stmt"]
        elif opcode in (7, 10, 11):
            pass
        elif opcode == 8:
            state["address"] += (255 - opcode_base) // line_range
        elif opcode == 9:
            state["address"] += r.uint(2)
        elif opcode == 12:
            r.uleb()
        else:
            raise StartupError("startup_line_standard_opcode")
    _need(r.p == r.end and rows and rows[-1]["end_sequence"], "startup_complete_line_program")
    expected = {0x1E63A: 302, 0x1E72F: 1383, 0x1E987: 2706, 0x2009B: 1955}
    selected = []
    for address, line in expected.items():
        matches = [row for row in rows if row["address"] == address and
                   row["file"] == 1 and row["line"] == line and not row["end_sequence"]]
        _need(bool(matches), "startup_instruction_source_line")
        selected.extend(matches)
    return {"offset": offset, "length": length, "version": version,
            "header_length": header_length, "program_offset": header_end,
            "source_content_hashes_present": False, "files": files,
            "selected_instruction_rows": selected, "total_row_count": len(rows)}


# Each range is a complete, finite partition into the selected original x86-64
# instructions. Branch displacements are decoded below; text is not a caller hint.
_INSTRUCTION_RANGES = (
    ("initial_argument_and_environment_cursor", 0x1BE40, (
        ("4157", "push r15"), ("4883c708", "add rdi,8"),
        ("4889f2", "mov rdx,rsi"), ("4156", "push r14"),
        ("4155", "push r13"), ("4154", "push r12"),
        ("55", "push rbp"), ("53", "push rbx"),
        ("4881ec40010000", "sub rsp,320"),
        ("488b47f8", "mov rax,qword [rdi-8]"),
        ("48893d159c0100", "mov qword [rip+dl_argv],rdi"),
        ("8905179c0100", "mov dword [rip+dl_argc],eax"), ("4898", "cdqe"),
        ("4c8d44c708", "lea r8,[rdi+rax*8+8]"),
        ("49833800", "cmp qword [r8],0"),
        ("4c890565b70100", "mov qword [rip+environ],r8"),
        ("740d", "je environment_terminator"), ("0f1f00", "nop"))),
    ("environment_terminator_and_auxv_zero_array", 0x1BE80, (
        ("4983c008", "add r8,8"), ("49833800", "cmp qword [r8],0"),
        ("75f6", "jne next_environment_pointer"), ("31c0", "xor eax,eax"),
        ("488d7c2498", "lea rdi,[rsp-104]"), ("498d7008", "lea rsi,[r8+8]"),
        ("b934000000", "mov ecx,52"), ("f348ab", "rep stosq"),
        ("498b4008", "mov rax,qword [r8+8]"))),
    ("auxv_default_entry_and_cursor", 0x1BEA1, (
        ("488d3d18140000", "lea rdi,[rip+loader_entry]"),
        ("488935599c0100", "mov qword [rip+dl_auxv],rsi"),
        ("48897c24e0", "mov qword [rsp-32],rdi"),
        ("48c74424c800100000", "mov qword [rsp-56],4096"),
        ("48c74424287f030000", "mov qword [rsp+40],895"),
        ("4885c0", "test rax,rax"), ("0f8429010000", "je empty_auxv"))),
    ("auxv_tag_indexed_copy", 0x1BEE0, (
        ("4883f833", "cmp rax,51"), ("7709", "ja next_auxv_entry"),
        ("488b4e08", "mov rcx,qword [rsi+8]"),
        ("48894cc498", "mov qword [rsp+rax*8-104],rcx"),
        ("488b4610", "mov rax,qword [rsi+16]"), ("4883c610", "add rsi,16"),
        ("4885c0", "test rax,rax"), ("75e4", "jne copy_auxv_entry"))),
    ("read_auxv_entry", 0x1BF1C, (("488b7c24e0", "mov rdi,qword [rsp-32]"),)),
    ("read_auxv_secure", 0x1BF25, (("448b7c2450", "mov r15d,dword [rsp+80]"),)),
    ("store_secure_flag", 0x1BFBB, (
        ("44893d869a0100", "mov dword [rip+libc_enable_secure],r15d"),)),
    ("store_initial_entry_argument", 0x1BFD6, (
        ("4c8902", "mov qword [rdx],r8"), ("894208", "mov dword [rdx+8],eax"),
        ("48897a10", "mov qword [rdx+16],rdi"))),
    ("sysdep_save_callback_and_parse_arguments", 0x1CC10, (
        ("53", "push rbx"), ("4889f3", "mov rbx,rsi"),
        ("4883ec20", "sub rsp,32"),
        ("48893d218e0100", "mov qword [rip+libc_stack_end],rdi"),
        ("4889e6", "mov rsi,rsp"), ("e819f2ffff", "call sysdep_parse_arguments"))),
    ("sysdep_forward_entry_to_callback", 0x1CC79, (
        ("8b742408", "mov esi,dword [rsp+8]"), ("488b3c24", "mov rdi,qword [rsp]"),
        ("488d542410", "lea rdx,[rsp+16]"),
        ("488b0d7b8e0100", "mov rcx,qword [rip+dl_auxv]"), ("ffd3", "call rbx"))),
    ("select_original_dl_main_callback", 0x1E419, (
        ("488d35e0010000", "lea rsi,[rip+dl_main]"),
        ("488905a18c0100", "mov qword [rip+rtld_link_map_field],rax"),
        ("48892d12760100", "mov qword [rip+libc_stack_end],rbp"),
        ("0f2925fb8f0100", "movaps xmmword [rip+rtld_state],xmm4"),
        ("e8d6e7ffff", "call sysdep_start"))),
    ("dl_main_frame", 0x1E600, (
        ("55", "push rbp"), ("660fefc0", "pxor xmm0,xmm0"),
        ("4889e5", "mov rbp,rsp"))),
    ("save_user_entry_argument", 0x1E621, (
        ("488995a8fdffff", "mov qword [rbp-600],rdx"),)),
    ("normal_mode_initialization", 0x1E63A, (
        ("c745c800000000", "mov dword [rbp-56],0"),)),
    ("nonsecure_environment_selection", 0x1E65D, (
        ("8b05e5730100", "mov eax,dword [rip+__libc_enable_secure]"),
        ("89c7", "mov edi,eax"), ("898590fdffff", "mov dword [rbp-624],eax"),
        ("488b056e8f0100", "mov rax,qword [rip+environ]"),
        ("85ff", "test edi,edi"), ("0f851c290000", "jne secure_environment"))),
    ("default_environment_cursor", 0x1E67A, (
        ("488985e0fdffff", "mov qword [rbp-544],rax"),
        ("4531ed", "xor r13d,r13d"), ("488d9de0fdffff", "lea rbx,[rbp-544]"))),
    ("default_environment_iteration", 0x1E6A0, (
        ("4889df", "mov rdi,rbx"), ("e858c1ffff", "call next_LD_environment_entry"),
        ("4889c1", "mov rcx,rax"), ("4885c0", "test rax,rax"),
        ("744d", "je after_default_environment"))),
    ("original_interpreter_branch", 0x1E710, (
        ("4c8b1561730100", "mov r10,qword [rip+dl_argv]"),
        ("488b8da8fdffff", "mov rcx,qword [rbp-600]"),
        ("488d059bebffff", "lea rax,[rip+loader_entry]"),
        ("498b3a", "mov rdi,qword [r10]"),
        ("4889bd88fdffff", "mov qword [rbp-632],rdi"),
        ("483901", "cmp qword [rcx],rax"),
        ("0f857e040000", "jne original_interpreter_path"))),
    ("trace_environment_assignment", 0x1E950, (
        ("48b854524143455f4c4f", "mov rax,TRACE_LO_prefix"),
        ("483301", "xor rax,qword [rcx]"),
        ("48ba414445445f4f424a", "mov rdx,ADED_OBJ_middle"),
        ("48335108", "xor rdx,qword [rcx+8]"), ("4809d0", "or rax,rdx"),
        ("0f852cfdffff", "jne next_environment_entry"),
        ("81791045435453", "cmp dword [rcx+16],ECTS_suffix"),
        ("0f851ffdffff", "jne next_environment_entry"),
        ("31f6", "xor esi,esi"), ("488d7915", "lea rdi,[rcx+21]"),
        ("c745c803000000", "mov dword [rbp-56],3"))),
    ("startup_dependency_call", 0x2009B, (
        ("31c9", "xor ecx,ecx"), ("4989c6", "mov r14,rax"),
        ("48c1e220", "shl rdx,32"), ("4889de", "mov rsi,rbx"),
        ("4c89ef", "mov rdi,r13"), ("4909d6", "or r14,rdx"),
        ("837dc803", "cmp dword [rbp-56],3"), ("4489e2", "mov edx,r12d"),
        ("0f94c1", "sete cl"), ("4531c0", "xor r8d,r8d"),
        ("e8c135feff", "call map_object_deps"))),
    ("dependency_function_entry", 0x3680, (
        ("55", "push rbp"), ("4189d1", "mov r9d,edx"),
        ("4989fa", "mov r10,rdi"), ("4889f7", "mov rdi,rsi"),
        ("418d4102", "lea eax,[r9+2]"), ("4189cb", "mov r11d,ecx"),
        ("488d0440", "lea rax,[rax+rax*2]"), ("4889e5", "mov rbp,rsp"))),
    ("save_open_mode", 0x36B8, (("4489852cfbffff", "mov dword [rbp-1236],r8d"),)),
    ("save_trace_mode", 0x37C6, (("44899d48fbffff", "mov dword [rbp-1208],r11d"),)),
    ("copy_modes_into_openaux_args", 0x38B5, (
        ("8b9d48fbffff", "mov ebx,dword [rbp-1208]"),
        ("488985a0fbffff", "mov qword [rbp-1120],rax"),
        ("4c89bd90fbffff", "mov qword [rbp-1136],r15"),
        ("899d98fbffff", "mov dword [rbp-1128],ebx"),
        ("8b9d2cfbffff", "mov ebx,dword [rbp-1236]"),
        ("899d9cfbffff", "mov dword [rbp-1124],ebx"))),
    ("needed_callback_args", 0x39B3, (
        ("488d9590fbffff", "lea rdx,[rbp-1136]"),
        ("488dbd70fbffff", "lea rdi,[rbp-1168]"),
        ("488985a8fbffff", "mov qword [rbp-1112],rax"),
        ("488d3571fcffff", "lea rsi,[rip+openaux]"),
        ("e84ce9ffff", "call catch_exception"))),
    ("only_LD_environment_scanner", 0x1A800, (
        ("488b17", "mov rdx,qword [rdi]"), ("488b02", "mov rax,qword [rdx]"),
        ("4885c0", "test rax,rax"), ("7522", "jne test_prefix"), ("c3", "ret"),
        ("66662e0f1f840000000000", "nop"), ("660f1f840000000000", "nop"),
        ("488b4208", "mov rax,qword [rdx+8]"), ("4883c208", "add rdx,8"),
        ("4885c0", "test rax,rax"), ("7423", "je return_NULL"),
        ("80384c", "cmp byte [rax],L"), ("75ee", "jne next_entry"),
        ("80780144", "cmp byte [rax+1],D"), ("75e8", "jne next_entry"),
        ("8078025f", "cmp byte [rax+2],underscore"), ("75e2", "jne next_entry"),
        ("4883c208", "add rdx,8"), ("4883c003", "add rax,3"),
        ("488917", "mov qword [rdi],rdx"), ("c3", "ret"),
        ("660f1f440000", "nop"), ("c3", "ret"))),
)


def _instruction_range(elf, role, start, templates):
    pc, rows, pieces = start, [], []
    for encoded, decoded in templates:
        expected = bytes.fromhex(encoded)
        offset = elf.offset(pc, len(expected))
        raw = binary.take(elf.data, offset, len(expected))
        _need(raw == expected, "startup_instruction_bytes")
        row = {"vaddr": pc, "file_offset": offset, "size_bytes": len(raw),
               "hex": raw.hex(), "decoded": decoded}
        if len(raw) == 5 and raw[0] in (0xE8, 0xE9):
            row["relative_kind"] = "direct_call" if raw[0] == 0xE8 else "direct_jump"
            row["target_vaddr"] = pc + len(raw) + int.from_bytes(raw[1:], "little", signed=True)
        elif len(raw) == 6 and raw[:2] in (b"\x0f\x84", b"\x0f\x85"):
            row["relative_kind"] = "conditional_jump"
            row["target_vaddr"] = pc + len(raw) + int.from_bytes(raw[2:], "little", signed=True)
        elif len(raw) == 2 and raw[0] in (0x74, 0x75, 0x77):
            row["relative_kind"] = "conditional_jump"
            row["target_vaddr"] = pc + len(raw) + int.from_bytes(raw[1:], "little", signed=True)
        elif (len(raw) == 6 and raw[0] in (0x89, 0x8B) and raw[1] & 0xC7 == 5) or (
                len(raw) == 7 and 0x40 <= raw[0] <= 0x4F and
                raw[1] in (0x89, 0x8B, 0x8D) and raw[2] & 0xC7 == 5):
            row["relative_kind"] = "rip_relative_address"
            row["target_vaddr"] = pc + len(raw) + int.from_bytes(raw[-4:], "little", signed=True)
        rows.append(row)
        pieces.append(raw)
        pc += len(raw)
    raw = b"".join(pieces)
    _need(elf.offset(start, len(raw)) + len(raw) == rows[-1]["file_offset"] + rows[-1]["size_bytes"],
          "startup_range_file_partition")
    return {"role": role, "vaddr": start, "end_vaddr": pc,
            "file_offset": elf.offset(start, len(raw)), **_binding(raw),
            "complete_selected_range_instruction_partition": True, "instructions": rows}


def _dwarf_facts(debug, sources):
    dies, cu = _parse_rtld_cu(debug)
    root = dies[cu["die_offset"]]["attrs"]
    _need((root[3], root[0x1B], root[0x10]) == ("rtld.c", "./elf", 0x1C930),
          "startup_cu_source_identity")
    lines = _rtld_lines(debug, root[0x10], root[0x1B])
    cu.update({"name": root[3], "comp_dir": root[0x1B], "producer": root[0x25]})
    selected = (
        (0x84BE8, 0x2E, "dl_main", "elf/rtld.c", 1356),
        (0x84CD2, 0x34, "state", "elf/rtld.c", 1369),
        (0x839B4, 0x13, "dl_main_state", "elf/dl-main.h", 71),
        (0x83A22, 0x0D, "mode", "elf/dl-main.h", 95),
        (0x8397A, 0x04, "rtld_mode", "elf/dl-main.h", 63),
    )
    declarations = []
    for offset, tag, name, path, line in selected:
        row = dies[offset]
        attrs = row["attrs"]
        _need(row["tag"] == tag and attrs[3] == name and attrs[0x3B] == line and
              lines["files"][attrs[0x3A]]["source_path"] == path,
              "startup_dwarf_declaration")
        physical = sources[path].split(b"\n")[line - 1]
        _need(name.encode("ascii") in physical, "startup_dwarf_source_line")
        declarations.append({"die_offset": offset, "tag": tag, "name": name,
                             "source_path": path, "physical_line": line,
                             "source": _binding(sources[path]),
                             "line_without_LF": _binding(physical)})
    function, variable, structure, member, enum = (
        dies[x] for x in (0x84BE8, 0x84CD2, 0x839B4, 0x83A22, 0x8397A))
    _need(0x84CD2 in function["children"] and 0x83A22 in structure["children"] and
          variable["attrs"][0x49] == 0x839B4 and member["attrs"][0x49] == 0x8397A,
          "startup_state_type_relationship")
    _need(function["attrs"][0x40] == "9c" and
          variable["attrs"][2] == "91f07b" and structure["attrs"][0x0B] == 464 and
          member["attrs"][0x38] == 456 and enum["attrs"][0x0B] == 4,
          "startup_state_location_layout")
    expression = binary.Reader(bytes.fromhex(variable["attrs"][2]))
    _need(expression.uint(1) == 0x91, "startup_state_fbreg_opcode")
    state_cfa_offset = expression.sleb()
    _need(state_cfa_offset == -528 and expression.p == expression.end,
          "startup_state_fbreg_value")
    enumerators = {dies[x]["attrs"][3]: dies[x]["attrs"][0x1C] for x in enum["children"]}
    _need(all(dies[x]["tag"] == 0x28 for x in enum["children"]) and enumerators == {
        "rtld_mode_normal": 0, "rtld_mode_list": 1, "rtld_mode_verify": 2,
        "rtld_mode_trace": 3, "rtld_mode_list_tunables": 4,
        "rtld_mode_list_diagnostics": 5, "rtld_mode_help": 6,
    }, "startup_mode_enumerators")

    range_offset = function["attrs"][0x55]
    _need(range_offset == 0x4CEF, "startup_function_range_offset")
    raw_ranges = debug.section(".debug_rnglists")
    reader = binary.Reader(raw_ranges, range_offset)
    ranges = []
    for _ in range(8):
        opcode = reader.uint(1)
        if opcode == 0:
            break
        _need(opcode == 7, "startup_function_range_opcode")
        address, size = reader.uint(8), reader.uleb()
        _need(0 < size <= 32768 and address + size < 1 << 64,
              "startup_function_range_bounds")
        ranges.append({"vaddr": address, "size_bytes": size})
    else:
        raise StartupError("startup_function_range_count")
    _need(ranges == [{"vaddr": 0x1E600, "size_bytes": 14636},
                    {"vaddr": 0x1BA2, "size_bytes": 775}], "startup_function_ranges")

    call = dies[0x8642F]
    _need(call["tag"] == 0x48 and call["attrs"][0x7D] == 0x200BF,
          "startup_callsite_return")
    declaration = dies[call["attrs"][0x7F]]
    _need(declaration["tag"] == 0x2E and declaration["attrs"][3] == "_dl_map_object_deps" and
          len(declaration["children"]) == 5 and
          all(dies[x]["tag"] == 5 for x in declaration["children"]),
          "startup_callsite_origin")
    signed_type = dies[dies[declaration["children"][-1]]["attrs"][0x49]]
    _need(signed_type["tag"] == 0x24 and signed_type["attrs"] ==
          {0x0B: 4, 0x3E: 5, 3: "int"}, "startup_open_mode_parameter_type")
    call_parameters = [dies[x] for x in call["children"]]
    _need(all(x["tag"] == 0x49 for x in call_parameters), "startup_callsite_parameter_tag")
    values = {x["attrs"][2]: x["attrs"][0x7E] for x in call_parameters}
    _need(len(values) == len(call_parameters) and values ==
          {"55": "7d00", "54": "7300", "51": "7c00", "58": "30"},
          "startup_callsite_parameter_values")
    return {
        "cu": cu, "line_table": lines, "declarations": declarations,
        "function_ranges": {"offset": range_offset,
                            "raw_hex": raw_ranges[range_offset:reader.p].hex(), "ranges": ranges},
        "state_location": {"variable_die": 0x84CD2, "structure_die": 0x839B4,
                           "expression_hex": "91f07b", "state_CFA_offset": state_cfa_offset,
                           "CFA_RBP_offset_from_selected_prologue": 16,
                           "state_RBP_offset": state_cfa_offset + 16,
                           "mode_member_offset": member["attrs"][0x38],
                           "mode_RBP_offset": state_cfa_offset + 16 + member["attrs"][0x38],
                           "mode_size_bytes": enum["attrs"][0x0B]},
        "mode_enumerators": enumerators,
        "startup_callsite": {"die_offset": 0x8642F, "return_vaddr": call["attrs"][0x7D],
                             "callee_declaration_die": declaration["offset"],
                             "callee": declaration["attrs"][3],
                             "parameters": [{"location_expression_hex": x["attrs"][2],
                                             "value_expression_hex": x["attrs"][0x7E]}
                                            for x in call_parameters],
                             "open_mode_R8_literal": 0,
                             "trace_mode_is_derived_from_original_instructions": True},
        "DWARF_embeds_source_content_hashes": False,
    }


def _binary_facts(loader, debug, sources):
    original = binary.ELF(loader, LOADER_BINDING["size_bytes"], LOADER_BINDING["sha256"])
    symbols_elf = binary.ELF(debug, DEBUG_BINDING["size_bytes"], DEBUG_BINDING["sha256"])
    # Reconstruct the unchanged openaux, private-layout and debuglink proof too.
    prior = binary.derive_binary_facts(loader_bytes=loader, debug_bytes=debug)
    symbols = symbols_elf.symbols()
    selected = {}
    for name, value, size, typ, section in (
            ("_dl_sysdep_parse_arguments", 0x1BE40, 502, 2, 10),
            ("_dl_sysdep_start", 0x1CC10, 183, 2, 10),
            ("dl_main", 0x1E600, 14636, 2, 10),
            ("dl_main.cold", 0x1BA2, 775, 2, 10),
            ("_dl_next_ld_env_entry", 0x1A800, 81, 2, 10),
            ("_dl_map_object_deps", 0x3680, 3979, 2, 10),
            ("openaux", 0x3640, 55, 2, 10),
            ("_dl_catch_exception", 0x2320, 377, 2, 10),
            ("_start", 0x1D2C0, 0, 0, 10),
            ("__libc_enable_secure", 0x35A48, 4, 1, 14),
            ("_environ", 0x375E0, 8, 1, 18),
            ("_dl_argv", 0x35A78, 8, 1, 14)):
        _need(len(symbols.get(name, [])) == 1, "startup_symbol_unique")
        row = symbols[name][0]
        _need((row["value"], row["size"], row["type"], row["section_index"]) ==
              (value, size, typ, section), "startup_symbol_location")
        selected[name] = row
    entry = struct.unpack_from("<Q", loader, 24)[0]
    _need(entry == selected["_start"]["value"], "startup_loader_entry")
    ranges = [_instruction_range(original, role, start, templates)
              for role, start, templates in _INSTRUCTION_RANGES]
    instructions = {row["vaddr"]: row for span in ranges for row in span["instructions"]}
    _need(len(instructions) == sum(len(span["instructions"]) for span in ranges),
          "startup_instruction_overlap")
    targets = {
        0x1BE5C: 0x35A78, 0x1BE63: 0x35A80, 0x1BE74: 0x375E0,
        0x1BE7B: 0x1BE8A, 0x1BE88: 0x1BE80,
        0x1BEA1: 0x1D2C0, 0x1BEA8: 0x35B08, 0x1BEC9: 0x1BFF8,
        0x1BEE4: 0x1BEEF, 0x1BEFA: 0x1BEE0, 0x1BFBB: 0x35A48,
        0x1CC22: 0x1BE40, 0x1CC86: 0x35B08,
        0x1E419: 0x1E600, 0x1E435: 0x1CC10,
        0x1E65D: 0x35A48, 0x1E66B: 0x375E0, 0x1E674: 0x20F96,
        0x1E6A3: 0x1A800, 0x1E6AE: 0x1E6FD,
        0x1E710: 0x35A78, 0x1E71E: 0x1D2C0, 0x1E732: 0x1EBB6,
        0x1E96E: 0x1E6A0, 0x1E97B: 0x1E6A0,
        0x200BA: 0x3680, 0x39C8: 0x3640, 0x39CF: 0x2320,
        0x1A809: 0x1A82D, 0x1A82B: 0x1A850,
        0x1A830: 0x1A820, 0x1A836: 0x1A820, 0x1A83C: 0x1A820,
    }
    for address, target in targets.items():
        _need(instructions[address].get("target_vaddr") == target, "startup_relative_target")
    # Decode the displacement arithmetic linking raw Linux auxiliary-vector
    # tags to the same globals and entry pointer used by dl_main.
    indexed = bytes.fromhex(instructions[0x1BEEA]["hex"])
    array_base = int.from_bytes(indexed[-1:], "little", signed=True)
    array_stride = 1 << (indexed[3] >> 6)
    tag_maximum = bytes.fromhex(instructions[0x1BEE0]["hex"])[-1]
    entry_slot = int.from_bytes(bytes.fromhex(instructions[0x1BF1C]["hex"])[-1:],
                               "little", signed=True)
    secure_slot = int.from_bytes(bytes.fromhex(instructions[0x1BF25]["hex"])[-1:],
                                "little", signed=True)
    argument_entry_offset = bytes.fromhex(instructions[0x1BFDC]["hex"])[-1]
    forwarded_entry_offset = bytes.fromhex(instructions[0x1CC81]["hex"])[-1]
    _need((array_base, array_stride, tag_maximum) == (-104, 8, 51) and
          array_base + 9 * array_stride == entry_slot == -32 and
          array_base + 23 * array_stride == secure_slot == 80 and
          argument_entry_offset == forwarded_entry_offset == 16,
          "startup_auxv_slot_relationship")
    dwarf = _dwarf_facts(symbols_elf, sources)
    _need(dwarf["state_location"]["mode_RBP_offset"] == -56,
          "startup_mode_frame_relationship")
    initial_mode = int.from_bytes(bytes.fromhex(instructions[0x1E63A]["hex"])[3:], "little")
    trace_enum = bytes.fromhex(instructions[0x200AD]["hex"])[3]
    _need(initial_mode == dwarf["mode_enumerators"]["rtld_mode_normal"] and
          trace_enum == dwarf["mode_enumerators"]["rtld_mode_trace"],
          "startup_binary_enum_relationship")
    modes = {"trace_mode": int(initial_mode == trace_enum),
             "open_mode": dwarf["startup_callsite"]["open_mode_R8_literal"]}
    _need(modes == EXPECTED_MODES, "startup_expected_modes")
    args = prior["openaux_args"]
    _need(args["size_bytes"] == 40 and
          (args["members"]["trace_mode"]["offset_bytes"],
           args["members"]["open_mode"]["offset_bytes"]) == (8, 12) and
          all(args["members"][name]["size_bytes"] == 4 and
              args["members"][name]["type"]["encoding"] == 5 for name in EXPECTED_MODES),
          "startup_args_layout")
    # The full symbol ranges bind code outside the selected local instruction
    # recipes too. They are not a claim of complete program verification.
    function_bindings = []
    for name in ("_dl_sysdep_parse_arguments", "_dl_sysdep_start", "dl_main", "dl_main.cold",
                 "_dl_next_ld_env_entry", "_dl_map_object_deps"):
        symbol = selected[name]
        offset = original.offset(symbol["value"], symbol["size"])
        raw = binary.take(loader, offset, symbol["size"])
        function_bindings.append({"name": name, "vaddr": symbol["value"],
                                  "file_offset": offset, **_binding(raw)})
    flow = {
        "proof_scope": "selected_source_debug_instruction_recipe_under_declared_original_startup",
        "loader": original.identity(), "debug": symbols_elf.identity(),
        "debuglink": prior["debuglink"], "symbols": selected,
        "loader_entry_vaddr": entry, "function_bindings": function_bindings,
        "instruction_ranges": ranges,
        "initial_vector_flow": {
            "auxv_array_RSP_offset": array_base, "auxv_array_element_size": array_stride,
            "copied_auxv_tag_maximum": tag_maximum,
            "AT_ENTRY": {"tag": 9, "array_RSP_offset": entry_slot,
                         "read_register": "RDI", "read_vaddr": 0x1BF1C,
                         "argument_field_offset": argument_entry_offset,
                         "argument_store_vaddr": 0x1BFDC,
                         "forward_pointer_register": "RDX", "forward_pointer_vaddr": 0x1CC81,
                         "dl_main_saved_pointer_RBP_offset": -600},
            "AT_SECURE": {"tag": 23, "array_RSP_offset": secure_slot,
                          "read_register": "R15D", "read_vaddr": 0x1BF25,
                          "global_store_vaddr": 0x1BFBB, "global_vaddr": 0x35A48,
                          "dl_main_global_read_vaddr": 0x1E65D,
                          "selected_input_value": 0},
            "environment_global_vaddr": 0x375E0,
            "environment_store_vaddr": 0x1BE74,
            "dl_main_environment_read_vaddr": 0x1E66B,
            "dl_main_callback_address_vaddr": 0x1E419,
            "sysdep_start_call_vaddr": 0x1E435,
            "sysdep_callback_save_vaddr": 0x1CC11,
            "sysdep_callback_register": "RBX", "sysdep_callback_call_vaddr": 0x1CC8D,
            "actual_initial_vector_observed": False,
        },
        "normal_mode_value": initial_mode, "trace_mode_enum_value": trace_enum,
        "state_mode_RBP_offset": dwarf["state_location"]["mode_RBP_offset"],
        "selected_branch_conditions": {
            "nonsecure_environment": "__libc_enable_secure_equals_zero",
            "environment_scan_result": "no_LD_entries_returns_NULL",
            "interpreter_entry": "original_launcher_AT_ENTRY_differs_from_loader_entry",
            "startup_mode": "normal_under_stated_original_startup_assumptions",
        },
        "startup_call": {"call_vaddr": 0x200BA, "target_vaddr": 0x3680,
                         "return_vaddr": 0x200BF,
                         "trace_mode_ECX": modes["trace_mode"],
                         "open_mode_R8D": modes["open_mode"]},
        "args_forwarding": {
            "trace_mode": {"incoming_register": "ECX", "saved_register": "R11D",
                           "spill_RBP_offset": -1208, "args_RBP_offset": -1136,
                           "field_RBP_offset": -1128, "field_offset": 8,
                           "openaux_outgoing_register": "ECX", "size_bytes": 4, "signed": True},
            "open_mode": {"incoming_register": "R8D", "spill_RBP_offset": -1236,
                          "args_RBP_offset": -1136, "field_RBP_offset": -1124,
                          "field_offset": 12, "openaux_outgoing_register": "R8D",
                          "size_bytes": 4, "signed": True},
            "callback_args_address_instruction": 0x39B3,
            "callback_function_address_instruction": 0x39C8,
            "original_return_checkpoint": prior["return_checkpoint"],
        },
        "other_global_paths_are_not_a_formal_verification_claim": True,
    }
    return flow, dwarf, modes


def derive_startup_facts(*, inputs, loader, debug):
    """Derive the selected conditional startup decision from complete originals.

    ``inputs`` is the exact six-name bytes dictionary used by the prior static
    binding. ``loader`` and ``debug`` are separately supplied complete ELF bytes;
    their package membership and exact identities are checked again here.
    """
    try:
        _preflight(inputs, loader, debug)
        package_members = []
        for name, package, member, supplied in (
                ("libc6", "libc6_2.41-12+deb13u4_amd64.deb", source.LOADER_MEMBER, loader),
                ("libc6-dbg", "libc6-dbg_2.41-12+deb13u4_amd64.deb", source.DEBUG_MEMBER, debug)):
            result = source.debian_package.inspect_package(
                inputs[package], member_path=member, expected_name=name,
                expected_version=source.VERSION, expected_architecture="amd64")
            reconstructed = result["member_bytes"]
            _need(len(reconstructed) == len(supplied) and reconstructed == supplied,
                  "startup_package_member_mismatch")
            package_members.append({"package": package, "member": member,
                                    "binding": _binding(reconstructed)})
        reconstruction, sources = _source_facts(inputs)
        reconstruction["package_members"] = package_members
        semantic_ranges = _semantic_ranges(sources)
        flow, dwarf, modes = _binary_facts(loader, debug, sources)
        return {
            "record_type": "required_gate_idempotence_loader_startup_facts_v0",
            "input_bindings": {name: _binding(inputs[name]) for name in INPUT_BINDINGS},
            "invocation_assumptions": copy.deepcopy(ORIGINAL_INVOCATION),
            "expected_modes": modes, "source_reconstruction": reconstruction,
            "source_semantic_ranges": semantic_ranges,
            "binary_flow": flow, "dwarf_bindings": dwarf, "boundary": copy.deepcopy(BOUNDARY),
        }
    except StartupError:
        raise
    except source.SourceError as exc:
        raise StartupError("startup_source_" + exc.code) from exc
    except source.debian_package.PackageError as exc:
        raise StartupError("startup_package_" + exc.code) from exc
    except binary.BinaryError as exc:
        raise StartupError("startup_binary_" + exc.code) from exc
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, struct.error) as exc:
        raise StartupError("startup_malformed_input") from exc
