"""Data-only reconstruction of native original-loader checkpoints.

This is a distinct native record contract.  No fixture event is relabelled or
passed to the fixture acceptance APIs.  Pinned ELF/layout and procfs parsing
primitives are reused after this module checks current full-file read records.
The helper itself cannot establish admission, execution, or physical provenance.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_loader_readout_v0 as decoding
import required_gate_idempotence_loader_startup_readout_v0 as startup
import check_required_gate_idempotence_entry_task_guard_v0 as guard

PROFILE = "linux_x86_64_original_launcher_loader_resolution_v0"
NATIVE = copy.deepcopy(decoding.NATIVE_BINDINGS)
LAUNCHER, LOADER = decoding.LAUNCHER, decoding.LOADER
DR6_RESERVED = 0xFFFF0FF0
CHECKPOINT_FIELDS = frozenset(("phase", "sample_started_ns", "sample_finished_ns", "raw_files",
    "backings", "runtime_ranges", "loader_rx_range", "native_rx_ranges", "executable"))
STAT_FIELDS = frozenset(("dev", "ino", "mode", "nlink", "size", "mtime_ns", "ctime_ns"))
BACKING_FIELDS = frozenset(("native_path", "before", "after", "content"))
COMMON_ROLES = frozenset(("observer.stat.bin", "observer.status.bin", "child.stat.setup.bin",
                         "child.status.setup.bin", "child.pidfd.info.bin"))
RETURN_ROLES = tuple(sorted((*decoding.FILE_NAMES, "environment.json", "fds.json")))
CP0_ROLES = tuple(sorted((*startup.FILE_NAMES, "debug.before.bin", "debug.armed.bin",
    "native.rx.sample0.bin", "native.rx.sample1.bin", "executable.elf", "child.exe.link.bin",
    "environment.json", "fds.json")))
ENTRY_ROLES = tuple(sorted((set(decoding.FILE_NAMES) - {
    "memory.sample0.bin", "memory.sample1.bin", "loader.rx.sample0.bin", "loader.rx.sample1.bin"})
    | {"native.rx.sample0.bin", "native.rx.sample1.bin", "executable.elf", "child.exe.link.bin",
       "environment.json", "fds.json"}))
MAX_INTEGER = (1 << 63) - 1
SAFE_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\Z")


class ReadoutError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value:
        raise ReadoutError(code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _integer(value, code, minimum=0, maximum=MAX_INTEGER):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def safe_path(path):
    _need(type(path) is str and SAFE_PATH.fullmatch(path) is not None and ".." not in path,
          "loader_resolution_raw_path")
    return path


def referenced_bytes(reference, files, maximum):
    _keys(reference, ("path", "size_bytes", "sha256"), "loader_resolution_raw_reference")
    path = safe_path(reference["path"])
    _integer(reference["size_bytes"], "loader_resolution_raw_reference_size", 0, maximum)
    _need(type(reference["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]),
          "loader_resolution_raw_reference_digest")
    _need(type(files) is dict and path in files and type(files[path]) is bytes
          and len(files[path]) == reference["size_bytes"], "loader_resolution_raw_reference_bytes")
    raw = files[path]
    _same(binding(raw), {key: reference[key] for key in ("size_bytes", "sha256")},
          "loader_resolution_raw_reference_binding")
    return raw


def _stat(value, native_path):
    _keys(value, STAT_FIELDS, "loader_resolution_backing_stat")
    for name, number in value.items():
        _integer(number, "loader_resolution_backing_stat_integer", maximum=(1 << 64) - 1)
    _need(stat.S_ISREG(value["mode"]) and value["size"] == NATIVE[native_path]["size_bytes"],
          "loader_resolution_backing_kind_size")
    _need(value["ino"] > 0, "loader_resolution_backing_inode")
    return value


def backing_record(row, files, native_files):
    _keys(row, BACKING_FIELDS, "loader_resolution_backing_record")
    path = row["native_path"]
    _need(path in NATIVE, "loader_resolution_backing_native_path")
    before, after = _stat(row["before"], path), _stat(row["after"], path)
    _same(before, after, "loader_resolution_backing_changed_during_read")
    raw = referenced_bytes(row["content"], files, NATIVE[path]["size_bytes"])
    _same(binding(raw), NATIVE[path], "loader_resolution_original_backing_bytes")
    _need(type(native_files) is dict and path in native_files and raw == native_files[path],
          "loader_resolution_backing_admitted_bytes")
    _need(row["content"]["path"] == "native." + NATIVE[path]["sha256"] + ".elf",
          "loader_resolution_backing_blob_name")
    return before


def _backings(backings, files, native_files):
    _need(type(backings) is list and len(backings) == len(NATIVE),
          "loader_resolution_backing_roster")
    result, identities = {}, set()
    for row in backings:
        value = backing_record(row, files, native_files)
        path = row["native_path"]
        identity = (os.major(value["dev"]), os.minor(value["dev"]), value["ino"])
        _need(path not in result and identity not in identities, "loader_resolution_backing_alias")
        identities.add(identity)
        result[path] = {"stat": copy.deepcopy(value), "identity": identity,
                        "content": copy.deepcopy(row["content"])}
    _need(set(result) == set(NATIVE), "loader_resolution_backing_roster")
    return result


def validate_preload(value, *, expected=None):
    """Validate fresh fixed-path preload evidence, including directory custody.

    The producer opens the child's pinned proc-root and its fixed ``etc``
    directory. This record describes those reads; it does not authenticate a
    historical filesystem operation. Only ENOENT or a stable empty regular
    file is an acceptable observation.
    """
    _keys(value, ("status", "root", "parent", "file", "content", "open_errno"),
          "loader_resolution_preload_fields")
    _same(value["content"], binding(b""), "loader_resolution_preload_content")
    for name in ("root", "parent", "file"):
        pair = value[name]
        if name == "file" and value["status"] == "absent":
            _need(pair is None, "loader_resolution_preload_absent_file")
            continue
        _keys(pair, ("before", "after"), "loader_resolution_preload_stat_pair")
        for side in ("before", "after"):
            observed = pair[side]
            _keys(observed, STAT_FIELDS, "loader_resolution_preload_stat")
            for number in observed.values():
                _integer(number, "loader_resolution_preload_stat_integer", maximum=(1 << 64) - 1)
            _need(observed["ino"] > 0 and observed["nlink"] > 0,
                  "loader_resolution_preload_identity")
            if name == "file":
                _need(stat.S_ISREG(observed["mode"]) and observed["size"] == 0,
                      "loader_resolution_preload_empty_regular")
            else:
                _need(stat.S_ISDIR(observed["mode"]), "loader_resolution_preload_directory")
        _same(pair["before"], pair["after"], "loader_resolution_preload_changed_during_read")
    _need(type(value["open_errno"]) is int and (
        value["status"] == "absent" and value["open_errno"] == 2 and value["file"] is None
        or value["status"] == "empty" and value["open_errno"] == 0 and value["file"] is not None),
        "loader_resolution_preload_status")
    if expected is not None:
        validate_preload(expected)
        _need(value["status"] == expected["status"], "loader_resolution_preload_status_changed")
        for name in ("root", "parent", "file"):
            if value[name] is not None:
                # Directory mtime/ctime also expose a create-and-remove cycle
                # between two absent observations. Ordinary reads affect only
                # atime, which is intentionally outside this stat projection.
                _same(value[name]["before"], expected[name]["before"],
                      "loader_resolution_preload_custody_changed")
    return copy.deepcopy(value)


def _layouts(maps_bytes, backings, native_files):
    _need(type(maps_bytes) is bytes and 0 < len(maps_bytes) <= 65536,
          "loader_resolution_maps_size")
    rows = decoding.proc.parse_maps(maps_bytes)
    layouts = {}
    identities = {value["identity"] for value in backings.values()}
    for path, value in backings.items():
        selected = [row for row in rows
                    if (row["major"], row["minor"], row["inode"]) == value["identity"]]
        if selected:
            layouts[path] = decoding._layout(native_files[path], selected)
    _need({LAUNCHER, LOADER} <= set(layouts), "loader_resolution_loader_launcher_mapping")
    specials, anonymous, anonymous_bytes, heaps = set(), 0, 0, 0
    kernel = {"[stack]": ("rw-p", 8 * 1024 * 1024), "[vdso]": ("r-xp", 1024 * 1024),
              "[vvar]": ("r--p", 1024 * 1024), "[vvar_vclock]": ("r--p", 1024 * 1024),
              "[vsyscall]": ("--xp", 1024 * 1024)}
    for row in rows:
        if (row["major"], row["minor"], row["inode"]) in identities:
            continue
        _need(row["major"] == row["minor"] == row["inode"] == row["offset"] == 0,
              "loader_resolution_unselected_file_mapping")
        size, name = row["end"] - row["start"], row["path"]
        if name in kernel:
            _need(name not in specials and row["permissions"] == kernel[name][0]
                  and size <= kernel[name][1], "loader_resolution_kernel_mapping")
            specials.add(name)
        else:
            _need(name in ("", "[heap]") and row["permissions"] in ("r--p", "rw-p"),
                  "loader_resolution_anonymous_mapping")
            anonymous += 1
            anonymous_bytes += size
            heaps += name == "[heap]"
    _need({"[stack]", "[vdso]", "[vvar]"} <= specials and anonymous <= 16
          and anonymous_bytes <= 64 * 1024 * 1024 and heaps <= 1,
          "loader_resolution_mapping_budget")
    return rows, layouts


def _auxv(raw, layouts):
    _need(type(raw) is bytes and 16 <= len(raw) <= 1024 and len(raw) % 16 == 0,
          "loader_resolution_auxv_size")
    pairs = list(struct.iter_unpack("<QQ", raw))
    _need(pairs[-1] == (0, 0) and all(key > 0 for key, _value in pairs[:-1]),
          "loader_resolution_auxv_terminator")
    values = dict(pairs[:-1])
    _need(len(values) == len(pairs) - 1 and {3, 4, 5, 6, 7, 9, 23} <= set(values),
          "loader_resolution_auxv_roster")
    _need(values[3] == layouts[LAUNCHER]["bias"] + layouts[LAUNCHER]["phdr_vaddr"]
          and values[4] == 56 and values[5] == layouts[LAUNCHER]["phnum"]
          and values[6] == 4096 and values[7] == layouts[LOADER]["bias"]
          and values[9] == layouts[LAUNCHER]["bias"] + layouts[LAUNCHER]["entry"]
          and values[23] == 0, "loader_resolution_auxv_targets")
    return values


def derive_targets(*, maps_bytes, auxv_bytes, backings, files, native_files):
    """Derive addresses from one snapshot; this does not accept a checkpoint."""
    try:
        selected = _backings(backings, files, native_files)
        rows, layouts = _layouts(maps_bytes, selected, native_files)
        aux = _auxv(auxv_bytes, layouts)
        result = {"return_target": layouts[LOADER]["bias"] + 0x3671,
                  "entry_target": aux[9],
                  "initial_loader_pc": layouts[LOADER]["bias"] + layouts[LOADER]["entry"],
                  "layouts": layouts, "rows": rows}
        _need(len({result[key] for key in ("return_target", "entry_target", "initial_loader_pc")}) == 3,
              "loader_resolution_target_alias")
        return result
    except ReadoutError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, struct.error) as exc:
        raise ReadoutError("loader_resolution_target_derivation") from exc


def rx_ranges(layouts, native_paths):
    result, offset = [], 0
    for path in sorted(native_paths):
        _need(path in layouts and path in NATIVE, "loader_resolution_rx_object")
        layout, rx = layouts[path], layouts[path]["rx"]
        result.append({"native_path": path, "address": layout["bias"] + rx["vaddr"],
                       "offset": offset, "size_bytes": rx["filesz"]})
        offset += rx["filesz"]
    return result


def role_limit(role):
    if role.startswith("native.rx."):
        return sum(item["size_bytes"] for item in NATIVE.values())
    if role.startswith("loader.rx."):
        return 160721
    if role.startswith("memory."):
        return 131072
    if role == "executable.elf":
        return NATIVE[LAUNCHER]["size_bytes"]
    if role.startswith("regs."):
        return 216
    if role.startswith("debug."):
        return 48
    if role == "siginfo.bin":
        return 128
    if role.startswith("auxv."):
        return 1024
    if role.startswith("stack.words."):
        return 1072
    if role.startswith("stack.strings."):
        return len(startup.STRING_BYTES)
    if role == "child.exe.link.bin":
        return 4096
    return 65536


def checkpoint_files(checkpoint, files, *, complete=True):
    phase = checkpoint["phase"]
    roles = CP0_ROLES if phase == "cp0" else ENTRY_ROLES if phase == "entry" else RETURN_ROLES
    references = checkpoint["raw_files"]
    _need(type(references) is dict and (set(references) == set(roles) if complete
                                      else set(references) <= set(roles)),
          "loader_resolution_checkpoint_raw_roster")
    result = {}
    for role, reference in references.items():
        raw = referenced_bytes(reference, files, role_limit(role))
        permitted = {phase + "." + role}
        if role in COMMON_ROLES:
            permitted.add(role)
        if role == "executable.elf":
            permitted.add("native." + NATIVE[LAUNCHER]["sha256"] + ".elf")
        _need(reference["path"] in permitted, "loader_resolution_checkpoint_raw_phase")
        result[role] = raw
    references_count = {item["path"] for item in references.values()}
    for backing in checkpoint["backings"]:
        references_count.add(backing["content"]["path"])
    if checkpoint["executable"] is not None:
        references_count.add(checkpoint["executable"]["content"]["path"])
    _need(len(references_count) <= 32, "loader_resolution_checkpoint_file_budget")
    return result


def _registers(raw, *, hardware):
    _need(type(raw) is bytes and len(raw) == 216, "loader_resolution_register_size")
    values = struct.unpack("<27Q", raw)
    _need(values[18] & 0x100 == 0 and (not hardware or values[18] & 0x10000 != 0),
          "loader_resolution_resume_flags")
    return values


def _debug(raw, expected):
    _need(type(raw) is bytes and len(raw) == 48 and struct.unpack("<6Q", raw) == expected,
          "loader_resolution_debug_state")


def _stack(raw, rows, registers, auxv_raw):
    words, strings = raw["stack.words.before.bin"], raw["stack.strings.before.bin"]
    _need(words == raw["stack.words.after.bin"] and strings == raw["stack.strings.after.bin"],
          "loader_resolution_stack_sample_changed")
    _need(len(words) == 48 + len(auxv_raw) and words[48:] == auxv_raw,
          "loader_resolution_stack_auxv")
    argc, argv0, argv_null, env0, env1, env_null = struct.unpack_from("<6Q", words)
    _need(argc == 1 and argv_null == env_null == 0 and strings == startup.STRING_BYTES,
          "loader_resolution_invocation_shape")
    stacks = [row for row in rows if row["path"] == "[stack]"]
    _need(len(stacks) == 1 and registers[19] % 16 == 0, "loader_resolution_stack_pointer")
    intervals = []
    for address, size in ((registers[19], len(words)), *zip((argv0, env0, env1),
                                                        map(len, startup.EXPECTED_STRINGS))):
        _need(type(address) is int and 0 < address < 1 << 47
              and stacks[0]["start"] <= address < address + size <= stacks[0]["end"],
              "loader_resolution_stack_range")
        _need(all(address + size <= low or address >= high for low, high in intervals),
              "loader_resolution_stack_overlap")
        intervals.append((address, address + size))
    return {"argc": 1, "argv": ["bubblewrap"], "envp": ["LC_ALL=C", "TZ=UTC"],
            "stack_pointer": registers[19]}


def _packed_rx(checkpoint, raw, layouts, native_files, paths):
    expected = rx_ranges(layouts, paths)
    _same(checkpoint["native_rx_ranges"], expected, "loader_resolution_native_rx_ranges")
    packed = b"".join(native_files[row["native_path"]][
        layouts[row["native_path"]]["rx"]["offset"]:
        layouts[row["native_path"]]["rx"]["offset"] + row["size_bytes"]] for row in expected)
    _need(raw["native.rx.sample0.bin"] == raw["native.rx.sample1.bin"] == packed,
          "loader_resolution_native_rx_bytes")


def _return_join(checkpoint, raw, targets, registers, static_record, native_files):
    layouts, rows = targets["layouts"], targets["rows"]
    rx = layouts[LOADER]["rx"]
    _same(checkpoint["loader_rx_range"], {"address": layouts[LOADER]["bias"] + rx["vaddr"],
                                         "size_bytes": rx["filesz"]},
          "loader_resolution_loader_rx_range")
    expected = native_files[LOADER][rx["offset"]:rx["offset"] + rx["filesz"]]
    _need(raw["loader.rx.sample0.bin"] == raw["loader.rx.sample1.bin"] == expected,
          "loader_resolution_loader_rx_bytes")
    _same(checkpoint["native_rx_ranges"], [], "loader_resolution_return_native_rx")
    ranges = decoding._ranges(checkpoint, raw, rows)
    _need(ranges["args"]["address"] == registers[5]
          and ranges["provider_map"]["address"] == registers[10],
          "loader_resolution_register_pointer")
    consumer_ptr, trace_mode, open_mode, strtab, name_ptr, _unused = struct.unpack(
        "<QiiQQQ", ranges["args"]["raw"])
    _need(trace_mode == open_mode == 0, "loader_resolution_invocation_modes")
    _need(consumer_ptr == ranges["consumer_map"]["address"]
          and name_ptr == ranges["needed_name"]["address"], "loader_resolution_argument_pointer")
    consumer, consumer_bias = decoding._map_identity(ranges["consumer_map"], layouts)
    provider, provider_bias = decoding._map_identity(ranges["provider_map"], layouts)
    name = ranges["needed_name"]["raw"]
    _need(name.endswith(b"\0") and name.count(b"\0") == 1, "loader_resolution_name_terminator")
    matches = [row for row in static_record["occurrence_bindings"]
               if row["consumer"]["path"] == consumer and bytes.fromhex(row["name_with_NUL"]["hex"]) == name]
    _need(len(matches) == 1, "loader_resolution_original_occurrence")
    match = matches[0]
    _need(strtab == consumer_bias + match["strtab_vaddr"]
          and name_ptr == strtab + match["string_table_offset"], "loader_resolution_dynstr_pointer")
    _need(provider == match["expected_provider"]["path"], "loader_resolution_returned_provider")
    return {"phase": checkpoint["phase"], "consumer": consumer, "provider": provider,
            "dynamic_entry_ordinal": match["dynamic_entry_ordinal"],
            "needed_ordinal": match["needed_ordinal"], "name": match["name"],
            "loader_load_bias": layouts[LOADER]["bias"], "consumer_load_bias": consumer_bias,
            "provider_load_bias": provider_bias, "args_pointer": registers[5],
            "consumer_map_pointer": consumer_ptr, "provider_map_pointer": registers[10],
            "name_pointer": name_ptr, "trace_mode": trace_mode, "open_mode": open_mode}


def _validate_checkpoint(*, checkpoint, files, process, static_record, native_files):
    _keys(checkpoint, CHECKPOINT_FIELDS, "loader_resolution_checkpoint_fields")
    phase = checkpoint["phase"]
    _need(phase in ("cp0", "entry") or type(phase) is str and re.fullmatch(r"return\.(0[1-9]|10)", phase),
          "loader_resolution_checkpoint_phase")
    start = _integer(checkpoint["sample_started_ns"], "loader_resolution_sample_time", 1)
    end = _integer(checkpoint["sample_finished_ns"], "loader_resolution_sample_time", start + 1)
    _need(end - start <= 15000000000, "loader_resolution_sample_deadline")
    decoding._static(static_record, native_files)
    raw = checkpoint_files(checkpoint, files)
    selected = _backings(checkpoint["backings"], files, native_files)
    event_identity = {"observer_pid": process["observer_pid"], "child_pid": process["child_pid"],
                      "child_starttime": process["starttime"]}
    decoding._processes(event_identity, raw)
    for stem in ("maps", "regs", "auxv"):
        _need(raw[stem + ".before.bin"] == raw[stem + ".after.bin"],
              "loader_resolution_stopped_sample_changed")
    targets = derive_targets(maps_bytes=raw["maps.before.bin"], auxv_bytes=raw["auxv.before.bin"],
        backings=checkpoint["backings"], files=files, native_files=native_files)
    layouts, rows = targets["layouts"], targets["rows"]
    auxv = _auxv(raw["auxv.before.bin"], layouts)
    registers = _registers(raw["regs.before.bin"], hardware=phase != "cp0")
    _registers(raw["regs.after.bin"], hardware=phase != "cp0")
    environment = guard.strict(raw["environment.json"])
    _keys(environment, ("cwd_hex", "namespaces", "preload"), "loader_resolution_checkpoint_environment")
    _need(environment["cwd_hex"] == "2f", "loader_resolution_working_directory")
    _keys(environment["namespaces"], guard.NAMESPACE_NAMES, "loader_resolution_child_namespaces")
    preload = validate_preload(environment["preload"])
    fds = guard.validate_descriptors(guard.strict(raw["fds.json"]), (0, 1, 2))
    for side in ("before", "after"):
        status = guard.parse_status(raw["child.status." + side + ".bin"])
        _need(status["NoNewPrivs"] == 1 and status["Seccomp"] == 2 and status["Seccomp_filters"] >= 1,
              "loader_resolution_guard_state")
    armed = (targets["return_target"], targets["entry_target"], 0, 0, DR6_RESERVED, 5)
    invocation, join = None, None
    if phase == "cp0":
        _need(set(layouts) == {LAUNCHER, LOADER}, "loader_resolution_cp0_mapping_roster")
        _need(registers[16] == targets["initial_loader_pc"], "loader_resolution_initial_pc")
        _debug(raw["debug.before.bin"], (0, 0, 0, 0, DR6_RESERVED, 0))
        _debug(raw["debug.armed.bin"], armed)
        invocation = _stack(raw, rows, registers, raw["auxv.before.bin"])
        _packed_rx(checkpoint, raw, layouts, native_files, (LAUNCHER, LOADER))
    else:
        target = targets["entry_target"] if phase == "entry" else targets["return_target"]
        bit = 2 if phase == "entry" else 1
        _need(registers[16] == target, "loader_resolution_checkpoint_pc")
        _need(raw["debug.before.bin"] == raw["debug.after.bin"], "loader_resolution_debug_sample_changed")
        _debug(raw["debug.before.bin"], (*armed[:4], DR6_RESERVED | bit, 5))
        siginfo = raw["siginfo.bin"]
        _need(len(siginfo) == 128 and struct.unpack_from("<iii", siginfo) == (5, 0, 4)
              and struct.unpack_from("<Q", siginfo, 16)[0] == target,
              "loader_resolution_hardware_cause")
        if phase == "entry":
            _need(set(layouts) == set(NATIVE), "loader_resolution_entry_mapping_roster")
            _packed_rx(checkpoint, raw, layouts, native_files, NATIVE)
        else:
            _need(checkpoint["executable"] is None, "loader_resolution_return_executable_role")
            join = _return_join(checkpoint, raw, targets, registers, static_record, native_files)
    if phase in ("cp0", "entry"):
        _same(checkpoint["runtime_ranges"], [], "loader_resolution_nonreturn_runtime_ranges")
        _need(checkpoint["loader_rx_range"] is None, "loader_resolution_nonreturn_loader_rx")
        executable = checkpoint["executable"]
        _need(type(executable) is dict and executable.get("native_path") == LAUNCHER,
              "loader_resolution_executable_record")
        identity = backing_record(executable, files, native_files)
        _same(identity, selected[LAUNCHER]["stat"], "loader_resolution_executable_identity")
        _need(raw["executable.elf"] == native_files[LAUNCHER]
              and 0 < len(raw["child.exe.link.bin"]) <= 4096
              and b"\0" not in raw["child.exe.link.bin"], "loader_resolution_executable_bytes")
    return {"phase": phase, **targets, "auxv": auxv, "auxv_bytes": raw["auxv.before.bin"],
            "invocation": invocation, "occurrence_join": join, "backing_identities": selected,
            "descriptors": fds, "raw_files": raw, "namespaces": environment["namespaces"],
            "preload": preload,
            "sample_started_ns": start, "sample_finished_ns": end}


def validate_checkpoint(*, checkpoint, files, process, static_record, native_files):
    """Reconstruct one complete checkpoint; never execute or imply admission."""
    try:
        return _validate_checkpoint(checkpoint=checkpoint, files=files, process=process,
                                    static_record=static_record, native_files=native_files)
    except ReadoutError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, struct.error, RecursionError) as exc:
        raise ReadoutError("loader_resolution_checkpoint_rejected") from exc
