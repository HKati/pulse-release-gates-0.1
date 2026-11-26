#!/usr/bin/env python3
"""Check authored loader-readout fixtures without acquiring or executing anything.

This is a data-only decoder for the separately fixed original loader recipe.
It accepts only the explicit authored_test_fixture envelope. Matching synthetic
process metadata and memory prove consistency of a test, never an actual live
read, hardware qualification, source/build provenance, or loader observation.
The caller separately reconstructs the full original static binding before
using this module. Its exact canonical record is additionally pinned here.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import stat
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import check_required_gate_idempotence_mapping_observation_v0 as proc
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REL = "schemas/required_gate_idempotence_loader_readout_event_v0.schema.json"
PROFILE = "linux_x86_64_original_loader_readout_fixture_v0"
RECORD_TYPE = "required_gate_idempotence_loader_readout_event_v0"
STATIC_RECORD_CANONICAL_SHA256 = "fdea8e5e54e2254fe686c2fb33c9cc57e8d103d9719cc9886a73df066bb7790a"
LOADER = "native/ld-linux-x86-64.so.2"
LAUNCHER = "native/bwrap"
PAGE_BYTES = 4096
ADDRESS_LIMIT = 1 << 47
DR6_RESERVED = 0xffff0ff0
NATIVE_BINDINGS = {
    "native/bwrap": {"size_bytes": 80248, "sha256": "573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f"},
    LOADER: {"size_bytes": 225672, "sha256": "c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307"},
    "native/libc.so.6": {"size_bytes": 1995216, "sha256": "9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92"},
    "native/libcap.so.2": {"size_bytes": 47288, "sha256": "41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b"},
    "native/libpcre2-8.so.0": {"size_bytes": 711216, "sha256": "92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3"},
    "native/libselinux.so.1": {"size_bytes": 202984, "sha256": "5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c"},
}
FILE_NAMES = tuple(sorted((
    "observer.stat.bin", "observer.status.bin", "child.stat.setup.bin",
    "child.status.setup.bin", "child.pidfd.info.bin", "siginfo.bin",
    *("child." + kind + "." + side + ".bin"
      for kind in ("stat", "status") for side in ("before", "after")),
    *(kind + "." + side + ".bin"
      for kind in ("maps", "regs", "auxv", "debug") for side in ("before", "after")),
    *(kind + ".sample" + str(sample) + ".bin"
      for kind in ("memory", "loader.rx") for sample in (0, 1)),
)))
RANGE_ROLES = ("args", "consumer_map", "provider_map", "needed_name")
POLICY = {
    "evidence_origin": "authored_test_fixture",
    "native_bytes_role": "pinned_original_fixture_inputs",
    "contemporaneous_backing_acquisition_authenticated": False,
    "rflags_resume_policy_qualified": False,
    "checkpoint_vaddr": 0x3671,
    "argument_register": "RBX", "provider_register": "RAX",
    "argument_bytes": 40, "map_prefix_bytes": 56,
    "return_slot": 0, "entry_slot": 1, "dr7": 5,
    "samples_per_range": 2, "event_files": 22,
    "runtime_ranges": 4, "runtime_window_bytes": 4096,
    "runtime_sample_bytes": 131072, "needed_name_bytes": 256,
    "proc_file_bytes": 65536, "control_bytes": 1048576,
    "loader_rx_bytes": 160721, "fixture_set_events": 9,
    "invocation_mode_policy_qualified": False,
    "actual_event_lifecycle_qualified": False,
}
BOUNDARY = {
    "contemporaneous_backing_acquisition_authenticated": False,
    "rflags_resume_policy_qualified": False,
    "live_private_abi_readout_qualified": False,
    "consumer_resolution_observed": False,
    "source_build_gate_satisfied": False,
    "acquisition_ready": False,
    "invocation_mode_policy_qualified": False,
    "metric_pass": None,
    "authority_effect": "none",
}


class ReadoutError(ValueError):
    """A stable rejection code that does not include inspected data."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise ReadoutError(code)


def _integer(value, code, minimum=0, maximum=(1 << 63) - 1):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _keys(value, keys, code):
    _need(type(value) is dict and len(value) == len(keys) and set(value) == set(keys), code)


def _json_bytes(value):
    """Bound direct Python inputs before serialization, excluding floats."""
    count, text_bytes = 0, 0

    def visit(item, depth):
        nonlocal count, text_bytes
        count += 1
        _need(count <= 50000 and depth <= 32, "loader_readout_control_complexity")
        if type(item) is dict:
            _need(len(item) <= 50000, "loader_readout_control_complexity")
            for key, child in item.items():
                _need(type(key) is str, "loader_readout_control_key")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is list:
            _need(len(item) <= 50000, "loader_readout_control_complexity")
            for child in item:
                visit(child, depth + 1)
        elif type(item) is str:
            _need(len(item) <= POLICY["control_bytes"], "loader_readout_control_size")
            text_bytes += len(item.encode("utf-8"))
            _need(text_bytes <= POLICY["control_bytes"], "loader_readout_control_size")
        elif type(item) is int:
            _need(-(1 << 63) <= item < (1 << 64), "loader_readout_control_integer")
        else:
            _need(item is None or type(item) is bool, "loader_readout_control_type")

    visit(value, 0)
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    _need(len(raw) <= POLICY["control_bytes"], "loader_readout_control_size")
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def _same(actual, expected, code):
    _need(_json_bytes(actual) == _json_bytes(expected), code)


def _lengths(files, native):
    """All raw byte-length checks precede any hashing or binary parsing."""
    _keys(files, FILE_NAMES, "loader_readout_raw_roster")
    _keys(native, NATIVE_BINDINGS, "loader_readout_native_roster")
    for path, descriptor in NATIVE_BINDINGS.items():
        _need(type(native[path]) is bytes and len(native[path]) == descriptor["size_bytes"],
              "loader_readout_native_size")
    for name, raw in files.items():
        _need(type(raw) is bytes, "loader_readout_raw_type")
        if name.startswith("regs."):
            _need(len(raw) == 216, "loader_readout_register_size")
        elif name.startswith("debug."):
            _need(len(raw) == 48, "loader_readout_debug_size")
        elif name == "siginfo.bin":
            _need(len(raw) == 128, "loader_readout_siginfo_size")
        elif name.startswith("loader.rx."):
            _need(len(raw) == POLICY["loader_rx_bytes"], "loader_readout_rx_size")
        elif name.startswith("memory."):
            _need(0 < len(raw) <= POLICY["runtime_sample_bytes"], "loader_readout_memory_size")
        else:
            _need(0 < len(raw) <= POLICY["proc_file_bytes"], "loader_readout_proc_size")


def _schema(event):
    _json_bytes(event)
    schema_raw = transport.read_regular(ROOT / SCHEMA_REL, POLICY["control_bytes"])
    try:
        schema = json.loads(schema_raw)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(event)
    except (jsonschema.ValidationError, jsonschema.SchemaError, json.JSONDecodeError) as exc:
        raise ReadoutError("loader_readout_event_schema") from exc


def _static(record, native):
    _need(sha(_json_bytes(record)) == STATIC_RECORD_CANONICAL_SHA256,
          "loader_readout_static_record_changed")
    for path, expected in NATIVE_BINDINGS.items():
        _need(sha(native[path]) == expected["sha256"], "loader_readout_native_digest")
    recipe = record["recipe"]
    _need(recipe["checkpoint_vaddr"] == 0x3671
          and recipe["args_pointer_register"] == "RBX"
          and recipe["provider_map_register"] == "RAX"
          and recipe["args_bytes"] == 40
          and recipe["consumer_map_bytes"] == recipe["provider_map_bytes"] == 56,
          "loader_readout_selected_recipe")
    _need(len(record["occurrence_bindings"]) == 9, "loader_readout_occurrence_roster")


def _processes(event, files):
    observer = proc.parse_proc_stat(files["observer.stat.bin"])
    status = proc.parse_proc_status(files["observer.status.bin"])
    opid, child = event["observer_pid"], event["child_pid"]
    _need(opid != child and observer["pid"] == status["pid"] == status["tgid"] == opid
          and observer["threads"] == status["threads"] == 1
          and observer["ppid"] == status["ppid"] and status["tracer"] == 0,
          "loader_readout_observer_identity")
    selected = []
    for side in ("setup", "before", "after"):
        ps = proc.parse_proc_stat(files["child.stat." + side + ".bin"])
        pt = proc.parse_proc_status(files["child.status." + side + ".bin"])
        _need(ps["pid"] == pt["pid"] == pt["tgid"] == child
              and ps["ppid"] == pt["ppid"] == opid
              and ps["threads"] == pt["threads"] == 1
              and ps["state"] == pt["state"] == "t" and pt["tracer"] == opid
              and ps["starttime"] == event["child_starttime"] >= observer["starttime"],
              "loader_readout_child_identity")
        selected.append(ps)
    _same(selected[0], selected[1], "loader_readout_child_changed")
    _same(selected[1], selected[2], "loader_readout_child_changed")
    _need(files["child.stat.before.bin"] == files["child.stat.after.bin"]
          and files["child.status.before.bin"] == files["child.status.after.bin"],
          "loader_readout_process_sample_changed")
    info = proc._colon_fields(files["child.pidfd.info.bin"], "loader_readout_pidfd_encoding")
    _need("Pid" in info and proc._decimal(info["Pid"], "loader_readout_pidfd_pid", 1) == child,
          "loader_readout_pidfd_identity")


def _headers(raw):
    """Only called after the exact six original ELF byte bindings pass."""
    phoff = struct.unpack_from("<Q", raw, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", raw, 54)
    _need(phentsize == 56 and 0 < phnum <= 1024
          and phoff + phentsize * phnum <= len(raw), "loader_readout_program_headers")
    result = []
    for number in range(phnum):
        kind, flags, offset, address, _physical, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", raw, phoff + number * phentsize)
        result.append({"type": kind, "flags": flags, "offset": offset,
                       "vaddr": address, "filesz": filesz, "memsz": memsz, "align": align})
    return result


def _backings(event):
    _need(len(event["backings"]) == len(NATIVE_BINDINGS), "loader_readout_backing_roster")
    result, identities = {}, set()
    for item in event["backings"]:
        path = item["native_path"]
        _need(path in NATIVE_BINDINGS and path not in result, "loader_readout_backing_roster")
        _same(item["content"], NATIVE_BINDINGS[path], "loader_readout_backing_content")
        _same(item["before"], item["after"], "loader_readout_backing_changed")
        value = item["before"]
        _need(stat.S_ISREG(value["mode"]) and value["size_bytes"] == NATIVE_BINDINGS[path]["size_bytes"],
              "loader_readout_backing_kind_or_size")
        identity = (value["device_major"], value["device_minor"], value["inode"])
        _need(identity not in identities, "loader_readout_backing_alias")
        identities.add(identity)
        result[path] = identity
    return result


def _layout(raw, rows):
    headers = _headers(raw)
    segments = [row for row in headers if row["type"] == 1 and row["filesz"]]
    candidates = None
    for row in rows:
        possible = set()
        for segment in segments:
            start = segment["offset"] // PAGE_BYTES * PAGE_BYTES
            end = (segment["offset"] + segment["filesz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
            if start <= row["offset"] < end:
                possible.add(row["start"] - segment["vaddr"] // PAGE_BYTES * PAGE_BYTES
                             - (row["offset"] - start))
        candidates = possible if candidates is None else candidates & possible
    _need(candidates is not None and len(candidates) == 1, "loader_readout_mapping_bias_ambiguous")
    bias = next(iter(candidates))
    _integer(bias, "loader_readout_mapping_bias", 1, ADDRESS_LIMIT - 1)
    _need(bias % PAGE_BYTES == 0, "loader_readout_mapping_alignment")
    relro = set()
    for region in (row for row in headers if row["type"] == 0x6474e552):
        start = (bias + region["vaddr"]) // PAGE_BYTES * PAGE_BYTES
        end = (bias + region["vaddr"] + region["memsz"]) // PAGE_BYTES * PAGE_BYTES
        _need(0 <= end - start <= len(raw) + 2 * PAGE_BYTES, "loader_readout_relro_bounds")
        relro.update(range(start, end, PAGE_BYTES))
    expected = {}
    for segment in segments:
        start = (bias + segment["vaddr"]) // PAGE_BYTES * PAGE_BYTES
        end = (bias + segment["vaddr"] + segment["filesz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
        _need(0 < start < end < ADDRESS_LIMIT and end - start <= len(raw) + 2 * PAGE_BYTES,
              "loader_readout_mapping_extent")
        permission = "r" + ("w" if segment["flags"] & 2 else "-") + ("x" if segment["flags"] & 1 else "-") + "p"
        for page in range(start, end, PAGE_BYTES):
            _need(page not in expected, "loader_readout_selected_segment_overlap")
            allowed = {permission}
            if page in relro and permission[1] == "w":
                allowed.add(permission[0] + "-" + permission[2:])
            expected[page] = (segment["offset"] // PAGE_BYTES * PAGE_BYTES + page - start, allowed)
    seen = set()
    for row in rows:
        _need((row["end"] - row["start"]) // PAGE_BYTES <= len(expected), "loader_readout_mapping_range")
        for page in range(row["start"], row["end"], PAGE_BYTES):
            _need(page in expected and page not in seen, "loader_readout_extra_mapping")
            offset, permissions = expected[page]
            _need(row["offset"] + page - row["start"] == offset
                  and row["permissions"] in permissions, "loader_readout_mapping_backing")
            seen.add(page)
    _need(seen == set(expected), "loader_readout_mapping_coverage")
    dynamic = [row for row in headers if row["type"] == 2]
    rx = [row for row in segments if row["flags"] == 5]
    _need(len(dynamic) == len(rx) == 1, "loader_readout_original_segment_profile")
    phoff = struct.unpack_from("<Q", raw, 32)[0]
    phdr_spans = [row for row in segments if row["offset"] <= phoff
                  and phoff + len(headers) * 56 <= row["offset"] + row["filesz"]]
    _need(len(phdr_spans) == 1, "loader_readout_phdr_file_mapping")
    phdr_vaddr = phdr_spans[0]["vaddr"] + phoff - phdr_spans[0]["offset"]
    return {"bias": bias, "dynamic": dynamic[0], "rx": rx[0],
            "phdr_vaddr": phdr_vaddr, "phnum": len(headers),
            "entry": struct.unpack_from("<Q", raw, 24)[0]}


def _maps(event, files, native):
    _need(files["maps.before.bin"] == files["maps.after.bin"], "loader_readout_maps_changed")
    rows = proc.parse_maps(files["maps.before.bin"])
    backings = _backings(event)
    identities = set(backings.values())
    layouts = {}
    for path, identity in backings.items():
        selected = [row for row in rows if (row["major"], row["minor"], row["inode"]) == identity]
        if selected:
            layouts[path] = _layout(native[path], selected)
    _need(LOADER in layouts and LAUNCHER in layouts, "loader_readout_cp0_object_missing")
    specials, anonymous, anonymous_bytes, heaps = set(), 0, 0, 0
    kernel = {"[stack]": ("rw-p", 8 * 1024 * 1024), "[vdso]": ("r-xp", 1024 * 1024),
              "[vvar]": ("r--p", 1024 * 1024), "[vvar_vclock]": ("r--p", 1024 * 1024),
              "[vsyscall]": ("--xp", 1024 * 1024)}
    for row in rows:
        if (row["major"], row["minor"], row["inode"]) in identities:
            continue
        _need(row["major"] == row["minor"] == row["inode"] == row["offset"] == 0,
              "loader_readout_unselected_file_mapping")
        size, name = row["end"] - row["start"], row["path"]
        if name in kernel:
            _need(name not in specials and row["permissions"] == kernel[name][0]
                  and size <= kernel[name][1], "loader_readout_kernel_metadata")
            specials.add(name)
        else:
            _need(name in ("", "[heap]") and row["permissions"] in ("r--p", "rw-p"),
                  "loader_readout_anonymous_metadata")
            anonymous += 1
            anonymous_bytes += size
            heaps += name == "[heap]"
    _need({"[stack]", "[vdso]", "[vvar]"} <= specials and anonymous <= 16
          and anonymous_bytes <= 64 * 1024 * 1024 and heaps <= 1,
          "loader_readout_mapping_metadata_budget")
    return rows, layouts


def _auxv(files, layouts):
    _need(files["auxv.before.bin"] == files["auxv.after.bin"], "loader_readout_auxv_changed")
    raw = files["auxv.before.bin"]
    _need(len(raw) % 16 == 0, "loader_readout_auxv_size")
    pairs = list(struct.iter_unpack("<QQ", raw))
    _need(pairs[-1] == (0, 0) and all(key > 0 for key, _value in pairs[:-1]),
          "loader_readout_auxv_terminator")
    values = dict(pairs[:-1])
    _need(len(values) == len(pairs) - 1 and {3, 4, 5, 6, 7, 9} <= set(values),
          "loader_readout_auxv_roster")
    _need(values[3] == layouts[LAUNCHER]["bias"] + layouts[LAUNCHER]["phdr_vaddr"]
          and values[4] == 56 and values[5] == layouts[LAUNCHER]["phnum"]
          and values[6] == PAGE_BYTES and values[7] == layouts[LOADER]["bias"]
          and values[9] == layouts[LAUNCHER]["bias"] + layouts[LAUNCHER]["entry"],
          "loader_readout_auxv_targets")
    return values


def _readable(rows, address, length):
    _integer(address, "loader_readout_memory_address", 1, ADDRESS_LIMIT - 1)
    _integer(length, "loader_readout_memory_length", 1, POLICY["runtime_window_bytes"])
    _need(length <= ADDRESS_LIMIT - address, "loader_readout_memory_extent")
    cursor, end = address, address + length
    for row in rows:
        if row["end"] <= cursor:
            continue
        if row["start"] > cursor:
            break
        _need(row["permissions"][0] == "r", "loader_readout_unreadable_memory")
        cursor = min(end, row["end"])
        if cursor == end:
            return
    raise ReadoutError("loader_readout_unmapped_memory")


def _ranges(event, files, rows):
    _need(files["memory.sample0.bin"] == files["memory.sample1.bin"],
          "loader_readout_memory_sample_changed")
    packed = files["memory.sample0.bin"]
    result, intervals, cursor = {}, [], 0
    for row in event["runtime_ranges"]:
        role = row["role"]
        _need(role not in result and role in RANGE_ROLES, "loader_readout_range_roster")
        size = row["size_bytes"]
        _need(row["offset"] == cursor and cursor <= len(packed)
              and size <= len(packed) - cursor, "loader_readout_packed_extent")
        address = row["address"]
        _readable(rows, address, size)
        _need(all(address + size <= start or address >= end for start, end in intervals),
              "loader_readout_runtime_range_overlap")
        intervals.append((address, address + size))
        result[role] = {"address": address, "raw": packed[cursor:cursor + size]}
        cursor += size
    _need(set(result) == set(RANGE_ROLES) and cursor == len(packed),
          "loader_readout_unused_or_missing_range")
    for role, length in (("args", 40), ("consumer_map", 56), ("provider_map", 56)):
        _need(len(result[role]["raw"]) == length, "loader_readout_runtime_layout_size")
        _need(result[role]["address"] % 8 == 0, "loader_readout_pointer_alignment")
    _need(1 < len(result["needed_name"]["raw"]) <= POLICY["needed_name_bytes"],
          "loader_readout_name_size")
    return result


def _map_identity(sample, layouts):
    raw, pointer = sample["raw"], sample["address"]
    load_bias, dynamic = struct.unpack_from("<Q", raw, 0)[0], struct.unpack_from("<Q", raw, 16)[0]
    real, namespace = struct.unpack_from("<Qq", raw, 40)
    _need(real == pointer and namespace == 0, "loader_readout_map_namespace_or_proxy")
    candidates = [path for path, layout in layouts.items()
                  if layout["bias"] == load_bias
                  and load_bias + layout["dynamic"]["vaddr"] == dynamic]
    _need(len(candidates) == 1, "loader_readout_map_original_identity")
    return candidates[0], load_bias


def _verify(event, files, record, native):
    _schema(event)
    _static(record, native)
    for name in FILE_NAMES:
        _same(event["raw_files"][name], binding(files[name]), "loader_readout_raw_binding")
    _processes(event, files)
    rows, layouts = _maps(event, files, native)
    aux = _auxv(files, layouts)
    _need(event["stop_wait_status"] == 1407, "loader_readout_stop_wait")
    _need(files["regs.before.bin"] == files["regs.after.bin"], "loader_readout_register_sample_changed")
    registers = struct.unpack("<27Q", files["regs.before.bin"])
    _need(registers[18] & 0x100 == 0, "loader_readout_single_step_flag")
    return_target = layouts[LOADER]["bias"] + 0x3671
    _need(registers[16] == return_target and return_target != aux[9], "loader_readout_return_pc")
    _need(files["debug.before.bin"] == files["debug.after.bin"], "loader_readout_debug_sample_changed")
    _need(struct.unpack("<6Q", files["debug.before.bin"]) ==
          (return_target, aux[9], 0, 0, DR6_RESERVED | 1, 5), "loader_readout_breakpoint_cause")
    _need(struct.unpack_from("<iii", files["siginfo.bin"]) == (5, 0, 4)
          and struct.unpack_from("<Q", files["siginfo.bin"], 16)[0] == return_target,
          "loader_readout_siginfo_cause")
    rx = layouts[LOADER]["rx"]
    _same(event["loader_rx_range"], {"address": layouts[LOADER]["bias"] + rx["vaddr"],
                                     "size_bytes": rx["filesz"]}, "loader_readout_rx_range")
    expected_rx = native[LOADER][rx["offset"]:rx["offset"] + rx["filesz"]]
    _need(files["loader.rx.sample0.bin"] == files["loader.rx.sample1.bin"] == expected_rx,
          "loader_readout_original_rx_mismatch")
    ranges = _ranges(event, files, rows)
    _need(ranges["args"]["address"] == registers[5]
          and ranges["provider_map"]["address"] == registers[10], "loader_readout_register_pointer")
    args = ranges["args"]["raw"]
    consumer_pointer, trace_mode, open_mode, strtab, name_pointer, _stale_aux = struct.unpack("<QiiQQQ", args)
    _need(consumer_pointer == ranges["consumer_map"]["address"]
          and name_pointer == ranges["needed_name"]["address"], "loader_readout_argument_pointer")
    consumer, consumer_bias = _map_identity(ranges["consumer_map"], layouts)
    provider, provider_bias = _map_identity(ranges["provider_map"], layouts)
    name = ranges["needed_name"]["raw"]
    _need(name.endswith(b"\0") and name.count(b"\0") == 1, "loader_readout_name_terminator")
    matches = []
    for occurrence in record["occurrence_bindings"]:
        if occurrence["consumer"]["path"] != consumer:
            continue
        expected_name = bytes.fromhex(occurrence["name_with_NUL"]["hex"])
        if name == expected_name:
            matches.append(occurrence)
    _need(len(matches) == 1, "loader_readout_original_occurrence")
    occurrence = matches[0]
    _need(strtab == consumer_bias + occurrence["strtab_vaddr"]
          and name_pointer == strtab + occurrence["string_table_offset"],
          "loader_readout_exact_dynstr_pointer")
    _need(provider == occurrence["expected_provider"]["path"], "loader_readout_provider_identity")
    join = {
        "event_index": event["event_index"], "consumer": consumer, "provider": provider,
        "dynamic_entry_ordinal": occurrence["dynamic_entry_ordinal"],
        "needed_ordinal": occurrence["needed_ordinal"], "name": occurrence["name"],
        "loader_load_bias": layouts[LOADER]["bias"], "consumer_load_bias": consumer_bias,
        "provider_load_bias": provider_bias, "args_pointer": registers[5],
        "consumer_map_pointer": consumer_pointer, "provider_map_pointer": registers[10],
        "name_pointer": name_pointer, "trace_mode": trace_mode, "open_mode": open_mode,
        "invocation_mode_policy_qualified": False,
    }
    return {"fixture_readout_consistent": True, "occurrence_join": join, **copy.deepcopy(BOUNDARY)}


def verify_event(*, event, files, static_record, native):
    """Validate one authored fixture, never an actual observation or readiness."""
    try:
        _lengths(files, native)
        return _verify(event, files, static_record, native)
    except ReadoutError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OSError, struct.error,
            OverflowError, UnicodeError, RecursionError) as exc:
        raise ReadoutError("loader_readout_fixture_invalid") from exc


def verify_event_set(*, events, files_by_event, static_record, native):
    """Require the exact nine unique original joins in one authored fixture set.

    The supplied order is a fixture sequence, not evidence of historical runtime
    ordering. No final entry, real process lifecycle or source/build admission is
    established by this set checker.
    """
    try:
        _need(type(events) is list and len(events) == 9
              and type(files_by_event) is list and len(files_by_event) == 9,
              "loader_readout_fixture_set_count")
        # Preflight the complete set before any hash or expensive parsing.
        for files in files_by_event:
            _lengths(files, native)
        results, keys, identity = [], set(), None
        backing_roster, auxv, object_biases = None, None, {}
        for index, (event, files) in enumerate(zip(events, files_by_event)):
            result = _verify(event, files, static_record, native)
            _need(event["event_index"] == index, "loader_readout_fixture_sequence")
            observer = proc.parse_proc_stat(files["observer.stat.bin"])
            current = tuple(event[key] for key in ("attempt_id", "observer_pid", "child_pid", "child_starttime"))
            current += (observer["starttime"], observer["ppid"])
            if identity is None:
                identity = current
            _need(current == identity, "loader_readout_fixture_context_changed")
            current_backings = {item["native_path"]: item for item in event["backings"]}
            if backing_roster is None:
                backing_roster, auxv = current_backings, files["auxv.before.bin"]
            _same(current_backings, backing_roster, "loader_readout_fixture_backing_changed")
            _need(files["auxv.before.bin"] == auxv, "loader_readout_fixture_auxv_changed")
            join = result["occurrence_join"]
            for path, bias in ((LOADER, join["loader_load_bias"]),
                               (join["consumer"], join["consumer_load_bias"]),
                               (join["provider"], join["provider_load_bias"])):
                _need(path not in object_biases or object_biases[path] == bias,
                      "loader_readout_fixture_object_relocated")
                object_biases[path] = bias
            key = (join["consumer"], join["dynamic_entry_ordinal"], join["name"])
            _need(key not in keys, "loader_readout_duplicate_occurrence")
            keys.add(key)
            results.append(join)
        expected = {(row["consumer"]["path"], row["dynamic_entry_ordinal"], row["name"])
                    for row in static_record["occurrence_bindings"]}
        _need(keys == expected and len(keys) == 9, "loader_readout_missing_occurrence")
        return {"fixture_readout_consistent": True, "occurrence_joins": results, **copy.deepcopy(BOUNDARY)}
    except ReadoutError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OSError, struct.error,
            OverflowError, UnicodeError, RecursionError) as exc:
        raise ReadoutError("loader_readout_fixture_set_invalid") from exc
