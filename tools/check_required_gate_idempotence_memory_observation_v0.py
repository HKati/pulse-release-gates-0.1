#!/usr/bin/env python3
"""Reconstruct two selected memory ranges of one fixed authored stopped probe.

The collector is never imported. The unchanged mapping checker supplies bounded
JSON, filesystem admission and raw proc parsers. Each checkpoint/range occurrence
has its own byte obligation. Accepted captures authenticate neither the observer
history nor the kernel, physical memory, whole process or original launcher.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import struct
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_mapping_observation_v0 as shared

PROFILE = "linux_x86_64_fixed_probe_private_memory_transition_v0"
ROOT = Path(__file__).resolve().parents[1]
PROBE_SOURCE = "tools/required_gate_idempotence_memory_probe_v0.py"
SOURCE_PATHS = tuple(sorted((*shared.SOURCE_PATHS,
    "schemas/required_gate_idempotence_memory_observation_v0.schema.json",
    "tools/check_required_gate_idempotence_memory_observation_v0.py",
    "tools/required_gate_idempotence_memory_observation_v0.py", PROBE_SOURCE)))
BOUNDARY = dict(shared.BOUNDARY)
LIMITS = dict(shared.LIMITS)
BASE_ADDRESS, PAGE_BYTES, ENTRY_OFFSET, ELF_BYTES = 0x400000, 4096, 232, 8192
CHECKPOINTS = ("cp0", "cp1")
RANGES = [
    {"range_id": "rx", "address": BASE_ADDRESS, "size_bytes": PAGE_BYTES,
     "file_offset": 0, "permissions": "r-xp"},
    {"range_id": "rw", "address": BASE_ADDRESS + PAGE_BYTES, "size_bytes": PAGE_BYTES,
     "file_offset": PAGE_BYTES, "permissions": "rw-p"},
]
TRANSITION = {"after": "cp0", "before": "cp1", "continuations": 1,
              "range_id": "rw", "offset": 256, "before_hex": "00", "after_hex": "5a"}
CHECKPOINT_FILES = (
    "child.stat.before.bin", "child.status.before.bin", "child.maps.before.bin",
    "child.stat.after.bin", "child.status.after.bin", "child.maps.after.bin",
    "child.pidfd.info.bin", "child.exe.link.bin", "executable.elf", "host.json",
    "rx.first.bin", "rw.first.bin", "rx.second.bin", "rw.second.bin",
)
FILE_NAMES = tuple(sorted((
    "selection.json", "attempt_start.json", "probe.elf", "observer.exe.bin",
    "observer.stat.bin", "observer.status.bin", "kernel.boot_id.bin",
    "retained.before.elf", "retained.after.elf", "stdout.bin", "stderr.bin",
    *(cp + "." + name for cp in CHECKPOINTS for name in CHECKPOINT_FILES),
)))
MemoryCheckError = shared.MappingError
canonical, sha, binding = shared.canonical, shared.sha, shared.binding
_need, _keys, _integer, _same = shared._need, shared._keys, shared._integer, shared._same
_json, _bound, _digest = shared._json, shared._bound, shared._digest
read_selection_file, write_new = shared.read_selection_file, shared.write_new


def source_bindings():
    return [{"path": path, **binding(shared._source_bytes(path))} for path in SOURCE_PATHS]


def _probe_bytes(sources):
    selected = next(row for row in sources if row["path"] == PROBE_SOURCE)
    raw = shared._source_bytes(PROBE_SOURCE)
    _bound(raw, {k: selected[k] for k in ("sha256", "size_bytes")},
           "memory_probe_source_changed", shared.SOURCE_BYTES)
    module = types.ModuleType("_pulse_fixed_private_memory_probe")
    module.__file__ = str(ROOT / PROBE_SOURCE)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    _same([module.BASE_ADDRESS, module.PAGE_BYTES, module.ENTRY_OFFSET,
           module.DATA_OFFSET, module.MUTATION_OFFSET, module.MUTATION_BYTE, module.ELF_BYTES],
          [BASE_ADDRESS, PAGE_BYTES, ENTRY_OFFSET, PAGE_BYTES, 256, 0x5a, ELF_BYTES],
          "memory_probe_layout")
    result = module.probe_bytes()
    _need(type(result) is bytes and len(result) == ELF_BYTES, "memory_probe_bytes")
    _elf_ranges(result)
    _need(result[PAGE_BYTES:] == bytes(PAGE_BYTES), "memory_probe_initial_data")
    return result


def _elf_ranges(raw):
    """Derive the selected page-to-file relationship from admitted ELF headers."""
    _need(type(raw) is bytes and len(raw) == ELF_BYTES, "memory_elf_size")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    _same(list(header[1:]), [2, 62, 1, BASE_ADDRESS + ENTRY_OFFSET, 64, 0, 0,
                            64, 56, 3, 0, 0, 0], "memory_elf_header")
    _need(header[0] == b"\x7fELF\x02\x01\x01" + bytes(9), "memory_elf_identity")
    headers = [struct.unpack_from("<IIQQQQQQ", raw, 64 + index * 56) for index in range(3)]
    _same([list(row) for row in headers], [
        [1, 5, 0, BASE_ADDRESS, BASE_ADDRESS, PAGE_BYTES, PAGE_BYTES, PAGE_BYTES],
        [1, 6, PAGE_BYTES, BASE_ADDRESS + PAGE_BYTES, BASE_ADDRESS + PAGE_BYTES,
         PAGE_BYTES, PAGE_BYTES, PAGE_BYTES],
        [0x6474e551, 6, 0, 0, 0, 0, 0, 16],
    ], "memory_elf_segments")
    ranges = [{"range_id": name, "address": row[3], "size_bytes": row[6],
               "file_offset": row[2], "permissions": permissions}
              for row, name, permissions in zip(headers[:2], ("rx", "rw"), ("r-xp", "rw-p"))]
    _same(ranges, RANGES, "memory_elf_range_binding")
    return ranges


def validate_selection(selection_bytes, expected_selection_sha256):
    _digest(expected_selection_sha256, "memory_selection_digest")
    _need(sha(selection_bytes) == expected_selection_sha256, "memory_selection_digest_mismatch")
    selected = _json(selection_bytes, "memory_selection_json")
    _keys(selected, {"record_type", "profile", "attempt_id", "probe", "observer", "sources",
                     "limits", "checkpoints", "ranges", "transition", *BOUNDARY},
          "memory_selection_fields")
    _need(selected["record_type"] == "required_gate_idempotence_memory_selection_v0"
          and selected["profile"] == PROFILE, "memory_selection_profile")
    _need(type(selected["attempt_id"]) is str and shared.ATTEMPT_RE.fullmatch(selected["attempt_id"]),
          "memory_attempt_id")
    shared._boundary(selected)
    _same(selected["limits"], LIMITS, "memory_limits_changed")
    _same(selected["checkpoints"], list(CHECKPOINTS), "memory_checkpoint_selection")
    _same(selected["ranges"], RANGES, "memory_range_selection")
    _same(selected["transition"], TRANSITION, "memory_transition_selection")
    sources = source_bindings()
    _same(selected["sources"], sources, "memory_sources_changed")
    _bound(_probe_bytes(sources), selected["probe"], "memory_probe_binding")
    observer = selected["observer"]
    _keys(observer, ("path", "sha256", "size_bytes"), "memory_observer_selection")
    path = observer["path"]
    _need(type(path) is str and path.startswith("/") and "\x00" not in path
          and len(path) <= 4096 and all(x not in ("", ".", "..") for x in path[1:].split("/")),
          "memory_observer_path")
    _digest(observer["sha256"], "memory_observer_digest")
    _integer(observer["size_bytes"], "memory_observer_size", 1, LIMITS["observer_executable_bytes"])
    return selected


def file_limit(name):
    if name == "observer.exe.bin":
        return LIMITS["observer_executable_bytes"]
    if name.endswith(".elf"):
        return ELF_BYTES
    if re.fullmatch(r"cp[01]\.(rx|rw)\.(first|second)\.bin", name):
        return PAGE_BYTES
    if name in ("selection.json", "attempt_start.json"):
        return shared.CONTROL_BYTES
    if name in ("stdout.bin", "stderr.bin"):
        return LIMITS[name.split(".")[0] + "_bytes"]
    return LIMITS["proc_file_bytes"]


def _stat_record(value, *, memory=False):
    _keys(value, ("dev", "ino", "mode", "nlink", "size"), "memory_object_stat")
    for item in value.values():
        _integer(item, "memory_object_stat_integer", maximum=(1 << 64) - 1)
    _integer(value["mode"], "memory_object_mode", maximum=0xffff)
    _need(value["ino"] > 0 and stat.S_ISREG(value["mode"]), "memory_object_stat_shape")
    if memory:
        _need(value["size"] == 0 and value["nlink"] == 1, "memory_proc_object_shape")
    else:
        _need(value["mode"] & 0o111 and not value["mode"] & 0o6000
              and value["nlink"] == 0 and value["size"] == ELF_BYTES,
              "memory_executable_object_shape")


def _object_record(value):
    if value is None:
        return
    _keys(value, ("stat", "seals"), "memory_object_fields")
    _stat_record(value["stat"])
    _same(value["seals"], 15, "memory_object_seals")


def _check_maps(raw, obj, ranges):
    rows = shared.parse_maps(raw)
    device = obj["stat"]["dev"]
    major = ((device >> 8) & 0xfff) | ((device >> 32) & 0xfffff000)
    minor = (device & 0xff) | ((device >> 12) & 0xffffff00)
    payload, specials = [], set()
    special_permissions = {"[vvar]": "r--p", "[vvar_vclock]": "r--p", "[vdso]": "r-xp",
                           "[vsyscall]": "--xp", "[stack]": "rw-p"}
    for row in rows:
        if row["inode"]:
            _need((row["major"], row["minor"], row["inode"]) == (major, minor, obj["stat"]["ino"]),
                  "memory_foreign_backing_object")
            payload.append(row)
        else:
            name = row["path"]
            _need(name in special_permissions and name not in specials
                  and row["major"] == row["minor"] == row["offset"] == 0
                  and row["permissions"] == special_permissions[name],
                  "memory_unrecognized_external_mapping")
            specials.add(name)
    _need(len(payload) == len(ranges), "memory_mapping_occurrence_count")
    for row, selected in zip(payload, ranges):
        _need(row["start"] == selected["address"]
              and row["end"] == selected["address"] + selected["size_bytes"]
              and row["permissions"] == selected["permissions"]
              and row["offset"] == selected["file_offset"], "memory_mapping_range_binding")
    _need({"[stack]", "[vdso]", "[vvar]"} <= specials, "memory_kernel_mapping_roster")


def verify_checkpoint(capture, files, checkpoint_id):
    """Check one occurrence before continuation, without trusting a result flag."""
    _need(checkpoint_id in CHECKPOINTS, "memory_checkpoint_id")
    index = CHECKPOINTS.index(checkpoint_id)
    checkpoint = capture["checkpoints"][index]
    _need(checkpoint["checkpoint_id"] == checkpoint_id, "memory_checkpoint_order")
    _need(checkpoint["wait_status"] == shared.STOP_WAIT
          and checkpoint["observation_wait"] is None, "memory_checkpoint_wait")
    prefix = checkpoint_id + "."
    _need({prefix + name for name in CHECKPOINT_FILES} <= set(files), "memory_checkpoint_file_roster")
    local = {name: files[prefix + name] for name in CHECKPOINT_FILES}
    local.update({name: files[name] for name in (
        "observer.stat.bin", "observer.status.bin", "kernel.boot_id.bin")})
    shared._check_processes(capture, local)
    shared._check_host(local)
    obj = checkpoint["executable_object"]
    _need(obj is not None and capture["objects"]["retained_before"] is not None,
          "memory_checkpoint_objects")
    _object_record(obj)
    _same(obj, capture["objects"]["retained_before"], "memory_executable_object_mismatch")
    _need(checkpoint["memory_object"] is not None, "memory_checkpoint_mem_object")
    _stat_record(checkpoint["memory_object"], memory=True)
    _need(local["executable.elf"] == files["probe.elf"] == files["retained.before.elf"],
          "memory_backing_bytes_mismatch")
    ranges = _elf_ranges(files["probe.elf"])
    _need(local["child.maps.before.bin"] == local["child.maps.after.bin"], "memory_checkpoint_maps_changed")
    _check_maps(local["child.maps.before.bin"], obj, ranges)
    _need(0 < len(local["child.exe.link.bin"]) <= 4096
          and b"\x00" not in local["child.exe.link.bin"], "memory_executable_link")
    relations = []
    for selected in ranges:
        name = selected["range_id"]
        offset, count = selected["file_offset"], selected["size_bytes"]
        backing = files["probe.elf"][offset:offset + count]
        expected = bytearray(backing)
        if checkpoint_id == "cp1" and name == "rw":
            _need(expected[TRANSITION["offset"]] == 0, "memory_initial_byte")
            expected[TRANSITION["offset"]] = 0x5a
        first, second = local[name + ".first.bin"], local[name + ".second.bin"]
        _need(len(first) == len(second) == count, "memory_sample_size")
        _need(first == second, "memory_sample_changed_within_checkpoint")
        _need(first == bytes(expected), "memory_checkpoint_sample_mismatch")
        relations.append({"checkpoint_id": checkpoint_id, "range_id": name,
                          "address": selected["address"], "size_bytes": count,
                          "file_offset": offset, "observed": binding(first),
                          "backing": binding(backing), "matches_backing": first == backing})
    return relations


def _check_record_shape(capture):
    _keys(capture, {"record_type", "profile", "attempt_id", "selection_sha256", "status", "failure",
                    "observer_pid", "child_pid", "timing", "wait", "ownership", "objects",
                    "checkpoints", "files", *BOUNDARY}, "memory_capture_fields")
    _need(capture["record_type"] == "required_gate_idempotence_memory_capture_v0"
          and capture["profile"] == PROFILE, "memory_capture_profile")
    shared._boundary(capture)
    _need(capture["status"] in ("completed", "incomplete"), "memory_capture_status")
    complete = capture["status"] == "completed"
    _need((complete and capture["failure"] is None) or
          (not complete and type(capture["failure"]) is str and shared.ERROR_RE.fullmatch(capture["failure"])),
          "memory_capture_failure")
    _integer(capture["observer_pid"], "memory_observer_pid", 1, 0x7fffffff)
    if capture["child_pid"] is not None:
        _integer(capture["child_pid"], "memory_child_pid", 1, 0x7fffffff)
        _need(capture["child_pid"] != capture["observer_pid"], "memory_child_equals_observer")
    timing = capture["timing"]
    _keys(timing, ("started_ns", "continued_ns", "finished_ns"), "memory_timing_fields")
    for key in ("started_ns", "finished_ns"):
        _integer(timing[key], "memory_timing_integer")
    _need(timing["started_ns"] <= timing["finished_ns"], "memory_timing_order")
    if timing["continued_ns"] is not None:
        _integer(timing["continued_ns"], "memory_timing_integer", timing["started_ns"], timing["finished_ns"])
    _keys(capture["wait"], ("continued", "terminal"), "memory_wait_fields")
    _need(capture["wait"]["continued"] is None or
          type(capture["wait"]["continued"]) is int and capture["wait"]["continued"] == 65535,
          "memory_continued_wait")
    if capture["wait"]["terminal"] is not None:
        _integer(capture["wait"]["terminal"], "memory_wait_integer", maximum=0xffffffff)
    ownership = capture["ownership"]
    _keys(ownership, ("pidfd_opened", "proc_dir_pinned", "child_reaped", "continuations_sent"),
          "memory_ownership_fields")
    for key in ("pidfd_opened", "proc_dir_pinned", "child_reaped"):
        shared._boolean(ownership[key], "memory_ownership_boolean")
    _integer(ownership["continuations_sent"], "memory_continuation_count", maximum=1)
    if capture["wait"]["continued"] is not None:
        _need(ownership["continuations_sent"] == 1, "memory_unrequested_continued_wait")
    _keys(capture["objects"], ("retained_before", "retained_after"), "memory_objects_fields")
    for obj in capture["objects"].values():
        _object_record(obj)
    checkpoints = capture["checkpoints"]
    _need(type(checkpoints) is list and len(checkpoints) == 2, "memory_checkpoint_count")
    for checkpoint, name in zip(checkpoints, CHECKPOINTS):
        _keys(checkpoint, ("checkpoint_id", "stopped_ns", "observed_ns", "wait_status",
                           "observation_wait", "executable_object", "memory_object", "preserved"),
              "memory_checkpoint_fields")
        _need(checkpoint["checkpoint_id"] == name, "memory_checkpoint_order")
        shared._boolean(checkpoint["preserved"], "memory_checkpoint_preserved")
        for key in ("stopped_ns", "observed_ns"):
            if checkpoint[key] is not None:
                _integer(checkpoint[key], "memory_checkpoint_time", timing["started_ns"], timing["finished_ns"])
        for key in ("wait_status", "observation_wait"):
            if checkpoint[key] is not None:
                _integer(checkpoint[key], "memory_checkpoint_wait_integer", maximum=0xffffffff)
        _object_record(checkpoint["executable_object"])
        if checkpoint["memory_object"] is not None:
            _stat_record(checkpoint["memory_object"], memory=True)
    return complete


def verify_capture(*, selection_bytes, expected_selection_sha256, capture_bytes,
                   expected_capture_sha256, files):
    selection = validate_selection(selection_bytes, expected_selection_sha256)
    _digest(expected_capture_sha256, "memory_capture_digest")
    _need(sha(capture_bytes) == expected_capture_sha256, "memory_capture_digest_mismatch")
    capture = _json(capture_bytes, "memory_capture_json")
    complete = _check_record_shape(capture)
    _need(capture["attempt_id"] == selection["attempt_id"]
          and capture["selection_sha256"] == expected_selection_sha256, "memory_capture_selection_mismatch")
    _need(type(files) is dict and set(files) <= set(FILE_NAMES)
          and {"selection.json", "attempt_start.json"} <= set(files), "memory_file_roster")
    _need(all(type(raw) is bytes and len(raw) <= file_limit(name) for name, raw in files.items()),
          "memory_file_bound")
    _need(sum(len(raw) for raw in files.values()) <= LIMITS["total_capture_bytes"], "memory_capture_total_bytes")
    _same(capture["files"], [{"path": name, **binding(raw)} for name, raw in sorted(files.items())],
          "memory_file_binding_mismatch")
    _need(files["selection.json"] == selection_bytes, "memory_preserved_selection_mismatch")
    _same(_json(files["attempt_start.json"], "memory_attempt_start"), {
        "record_type": "required_gate_idempotence_memory_attempt_start_v0", "profile": PROFILE,
        "attempt_id": selection["attempt_id"], "selection_sha256": expected_selection_sha256,
        "observer_pid": capture["observer_pid"], "started_ns": capture["timing"]["started_ns"],
    }, "memory_attempt_start_mismatch")
    probe = _probe_bytes(selection["sources"])
    for name, raw in files.items():
        if name.endswith(".elf"):
            _need(raw == probe, "memory_fixed_probe_substitution")
    if "observer.exe.bin" in files:
        _bound(files["observer.exe.bin"], {k: selection["observer"][k] for k in ("sha256", "size_bytes")},
               "memory_observer_executable_mismatch", LIMITS["observer_executable_bytes"])
    relations, offsets = [], []
    if complete:
        _need(set(files) == set(FILE_NAMES), "memory_complete_file_roster")
        _need(capture["child_pid"] is not None, "memory_completed_process_missing")
        _same(capture["ownership"], {"pidfd_opened": True, "proc_dir_pinned": True,
                                    "child_reaped": True, "continuations_sent": 1},
              "memory_completed_ownership")
        _same(capture["wait"]["terminal"], shared.KILL_WAIT, "memory_completed_wait")
        _need(all(obj is not None for obj in capture["objects"].values()), "memory_completed_objects")
        _same(capture["objects"]["retained_before"], capture["objects"]["retained_after"],
              "memory_retained_object_changed")
        first, second = capture["checkpoints"]
        timing = capture["timing"]
        moments = [timing["started_ns"], first["stopped_ns"], first["observed_ns"],
                   timing["continued_ns"], second["stopped_ns"], second["observed_ns"], timing["finished_ns"]]
        _need(all(type(moment) is int for moment in moments) and moments == sorted(moments),
              "memory_checkpoint_time_order")
        _need(second["observed_ns"] - timing["started_ns"] <= LIMITS["wall_seconds"] * 10**9
              and timing["finished_ns"] - timing["started_ns"] <=
              (LIMITS["wall_seconds"] + LIMITS["cleanup_seconds"]) * 10**9, "memory_completed_deadline")
        for checkpoint in capture["checkpoints"]:
            _need(checkpoint["preserved"] is True, "memory_checkpoint_not_preserved")
            relations.extend(verify_checkpoint(capture, files, checkpoint["checkpoint_id"]))
        _same(first["memory_object"], second["memory_object"], "memory_proc_object_changed")
        _same(shared.parse_proc_stat(files["cp0.child.stat.before.bin"]),
              shared.parse_proc_stat(files["cp1.child.stat.before.bin"]), "memory_process_identity_changed")
        _same(shared.parse_proc_status(files["cp0.child.status.before.bin"]),
              shared.parse_proc_status(files["cp1.child.status.before.bin"]), "memory_process_status_changed")
        _need(files["cp0.child.maps.before.bin"] == files["cp1.child.maps.before.bin"], "memory_maps_changed_across_checkpoints")
        _need(files["cp0.host.json"] == files["cp1.host.json"], "memory_host_changed_across_checkpoints")
        _need(files["stdout.bin"] == files["stderr.bin"] == b"", "memory_unexpected_output")
        offsets = [i for i, (a, b) in enumerate(zip(files["cp0.rw.first.bin"], files["cp1.rw.first.bin"])) if a != b]
        _same(offsets, [TRANSITION["offset"]], "memory_data_delta")
    _same(source_bindings(), selection["sources"], "memory_sources_changed_during_check")
    return {"record_type": "required_gate_idempotence_memory_verification_v0", "profile": PROFILE,
            "attempt_id": selection["attempt_id"], "status": "accepted",
            "selection_sha256": expected_selection_sha256, "capture_sha256": expected_capture_sha256,
            "observation_record_verified": True, "observation_complete": complete,
            "sealed_backing_object_unchanged": complete, "selected_memory_ranges_observed": complete,
            "selected_rx_pages_match_backing": complete, "selected_rw_transition_observed": complete,
            "memory_relations": relations, "changed_data_offsets": offsets,
            "failure": capture["failure"], **BOUNDARY}


def read_capture_directory(path):
    chain = []
    try:
        fd, chain = shared._pin_directory(path)
        before = os.fstat(fd)
        _need(stat.S_ISDIR(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o700,
              "memory_directory_mode")
        with os.scandir(fd) as entries:
            names = sorted(entry.name for entry in entries)
        _need("capture.json" in names and set(names) <= {"capture.json", *FILE_NAMES},
              "memory_directory_roster")
        identities = {}
        capture = shared._read_relative(fd, "capture.json", shared.CONTROL_BYTES,
                                        private=True, identities=identities)
        files = {name: shared._read_relative(fd, name, file_limit(name), private=True, identities=identities)
                 for name in names if name != "capture.json"}
        _need(sum(len(raw) for raw in files.values()) <= LIMITS["total_capture_bytes"], "memory_capture_total_bytes")
        with os.scandir(fd) as entries:
            after_names = sorted(entry.name for entry in entries)
        _need(shared._identity(before) == shared._identity(os.fstat(fd)) and after_names == names,
              "memory_directory_changed")
        for name, identity in identities.items():
            _need(shared._identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == identity,
                  "memory_file_changed_after_read")
        shared._check_chain(chain)
        return capture, files
    except MemoryCheckError:
        raise
    except OSError as exc:
        raise MemoryCheckError("memory_directory_unreadable") from exc
    finally:
        shared._close_chain(chain)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--capture-directory", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        selection = read_selection_file(args.selection)
        capture, files = read_capture_directory(args.capture_directory)
        result = verify_capture(selection_bytes=selection, expected_selection_sha256=args.selection_sha256,
                                capture_bytes=capture, expected_capture_sha256=args.capture_sha256, files=files)
        raw = canonical(result)
        if args.output:
            write_new(args.output, raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (MemoryCheckError, OSError) as exc:
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
