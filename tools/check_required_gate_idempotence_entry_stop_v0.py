#!/usr/bin/env python3
"""Independently reconstruct one bounded original executable-entry capture.

Only preserved bytes are inspected. This module never imports an acquisition
module, executes a payload, installs a filter, changes tracing state or verifies
distribution signatures. Request derivation follows separate fresh original
admission; a valid request is not execution authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import check_required_gate_idempotence_exec_stop_v0 as cp0
import check_required_gate_idempotence_entry_stop_plan_v0 as plan_check
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

old = cp0.old
ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_original_launcher_entry_stop_v0"
SCHEMA_REL = "schemas/required_gate_idempotence_entry_stop_v0.schema.json"
PLAN_REL = "docs/compute/required_gate_idempotence_entry_stop_plan_v0/plan_v0.json"
PLAN = {"size_bytes": 26997, "sha256": "2e289c818aaa6a51ab6757dc0995a5fe78f38e7022a8b7ca35ea250a45b0f191"}
CONTROL_BYTES = 1024 * 1024
PAGE_BYTES = 4096
STOP_WAIT, EXEC_WAIT, ENTRY_WAIT, KILL_WAIT = 4991, 263551, 1407, 9
PTRACE_OPTIONS = 0x10001e
DR6_RESERVED = 0xffff0ff0
HARDWARE_BOUNDARY = {"original_native_acquisition_performed": False,
                     "hosted_environment_qualified": False,
                     "physical_authentication": False, "execution_authorized": False,
                     "authority_effect": "none"}
HARDWARE_PROBE = {"size_bytes": 130,
                  "sha256": "abc49f273badbc70283221499d9cffafcdd9d2e56cd6f23fee1efcd6a6226872"}
HARDWARE_SOURCES = tuple(sorted((
    "tools/qualify_required_gate_idempotence_entry_stop_v0.py",
    "tools/required_gate_idempotence_entry_stop_v0.py",
    "tools/check_required_gate_idempotence_entry_stop_v0.py",
    "tools/check_required_gate_idempotence_entry_task_guard_v0.py",
    "tools/required_gate_idempotence_entry_task_guard_v0.py")))
HARDWARE_FILES = tuple(sorted((
    "observer.stat.bin", "observer.status.bin", "child.stat.setup.bin",
    "child.status.setup.bin", "child.pidfd.info.bin", "cp0.child.stat.bin",
    "cp0.child.status.bin", "entry.child.stat.bin", "entry.child.status.bin",
    "cp0.regs.bin", "entry.regs.bin", "cp0.auxv.bin", "entry.auxv.bin",
    "executable.elf", "entry.memory.bin", "cp0.debug.before.bin",
    "cp0.debug.armed.bin", "entry.debug.bin", "entry.siginfo.bin")))
BOUNDARY = dict(cp0.BOUNDARY)
NARROW_FLAGS = ("kernel_exec_checkpoint_observed", "fresh_cp0_prefix_verified",
                "entry_checkpoint_observed", "selected_native_image_bindings_verified",
                "selected_entry_memory_ranges_observed", "selected_entry_rx_ranges_match_original",
                "task_guard_installation_verified", "hardware_entry_stop_verified",
                "owned_entry_stop_cleanup_verified")
NATIVE = cp0.NATIVE
ROLES = {"launcher": "native/bwrap", "loader": "native/ld-linux-x86-64.so.2",
         "libc": "native/libc.so.6", "libcap": "native/libcap.so.2",
         "libpcre2": "native/libpcre2-8.so.0", "libselinux": "native/libselinux.so.1"}
LIMITS = {"wall_seconds": 15, "cleanup_seconds": 2, "owned_tracees": 1,
          "wait_records": 8, "capture_files": 160, "control_file_bytes": CONTROL_BYTES,
          "proc_file_bytes": 65536, "stdout_bytes": 4096, "stderr_bytes": 4096,
          "total_capture_bytes": 41943040, "deadline_extension_or_implicit_retry": False,
          "observer_executable_bytes": 14472}
MAPPING_METADATA_POLICY = {
    "total_rows": 128, "selected_file_mapping_policy": "exact_original_PT_LOAD_file_page_coverage",
    "required_kernel_rows": ["[stack]", "[vdso]", "[vvar]"],
    "kernel_rows": {"[stack]": {"permissions": "rw-p", "max_bytes": 8 * 1024 * 1024},
                    "[vdso]": {"permissions": "r-xp", "max_bytes": 1024 * 1024},
                    "[vvar]": {"permissions": "r--p", "max_bytes": 1024 * 1024},
                    "[vvar_vclock]": {"permissions": "r--p", "max_bytes": 1024 * 1024},
                    "[vsyscall]": {"permissions": "--xp", "max_bytes": 1024 * 1024}},
    "anonymous_names": ["", "[heap]"], "anonymous_permissions": ["r--p", "rw-p"],
    "anonymous_rows": 16, "anonymous_total_bytes": 64 * 1024 * 1024,
    "anonymous_and_kernel_identity": "zero_device_inode_and_file_offset",
    "unselected_file_mappings_allowed": False, "anonymous_content_verified": False,
    "all_raw_rows_preserved": True,
}
GUARD_SOURCES = ("tools/check_required_gate_idempotence_entry_task_guard_v0.py",
                 "tools/required_gate_idempotence_entry_task_guard_v0.py")
NEW_SOURCES = (PLAN_REL, plan_check.SCHEMA_REL,
               "tools/check_required_gate_idempotence_entry_stop_plan_v0.py",
               SCHEMA_REL, "tools/check_required_gate_idempotence_entry_stop_v0.py",
               "tools/required_gate_idempotence_entry_stop_v0.py",
               "tools/prepare_required_gate_idempotence_entry_stop_v0.py",
               "tools/qualify_required_gate_idempotence_entry_stop_v0.py", *GUARD_SOURCES)
FILE_NAMES = tuple(sorted((
    "request.json", "attempt_start.json", "observer.exe.bin", "observer.stat.bin",
    "observer.status.bin", "kernel.boot_id.bin", "host.json", "child.stat.setup.bin",
    "child.status.setup.bin", "child.pidfd.info.bin", "stdout.bin", "stderr.bin",
    "guard.program.bin", "guard.install.json", "guard.qualification.json",
    "breakpoint.qualification.json", "child.fds.setup.json", "child.fds.cp0.json",
    "child.fds.entry.json", "breakpoint.json", "cp0.debug.before.bin", "cp0.debug.armed.bin",
    "entry.debug.before.bin", "entry.debug.after.bin", "entry.siginfo.bin",
    *("native." + role + "." + side + ".elf" for role in ROLES for side in ("before", "after")),
    *(point + ".child." + kind + "." + side + ".bin" for point in ("cp0", "entry")
      for kind in ("stat", "status", "maps") for side in ("before", "after")),
    *(point + "." + kind + "." + side + ".bin" for point in ("cp0", "entry")
      for kind in ("regs", "auxv") for side in ("before", "after")),
    *(point + suffix for point in ("cp0", "entry") for suffix in (".child.exe.link.bin", ".executable.elf")),
    *("cp0." + role + ".rx.sample" + str(sample) + ".bin" for role in ("launcher", "loader") for sample in (0, 1)),
    *("entry." + role + ".rx.sample" + str(sample) + ".bin" for role in ROLES for sample in (0, 1)),
)))


class EntryStopError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise EntryStopError(code)


def canonical(value):
    try:
        return plan_check.canonical(value)
    except ValueError as exc:
        raise EntryStopError("entry_stop_json_value") from exc


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"size_bytes": len(raw), "sha256": sha(raw)}


def _json(raw):
    try:
        return plan_check.parse(raw)
    except ValueError as exc:
        raise EntryStopError("entry_stop_json") from exc


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _integer(value, code, minimum=0, maximum=(1 << 63) - 1):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _boolean(value, code):
    _need(type(value) is bool, code)


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), code)


def _binding(value, code, maximum=CONTROL_BYTES):
    _keys(value, ("size_bytes", "sha256"), code)
    _integer(value["size_bytes"], code, 1, maximum)
    _digest(value["sha256"], code)


def _bound(raw, expected, code):
    _need(type(raw) is bytes and binding(raw) == expected, code)


def _source(path):
    try:
        return transport.read_regular(ROOT / path, CONTROL_BYTES)
    except (OSError, ValueError) as exc:
        raise EntryStopError("entry_stop_source_unreadable") from exc


def _guard_checker():
    import check_required_gate_idempotence_entry_task_guard_v0
    return check_required_gate_idempotence_entry_task_guard_v0


def _admitted_plan():
    raw = _source(PLAN_REL)
    _bound(raw, PLAN, "entry_stop_original_plan_changed")
    try:
        baseline = transport.read_regular(ROOT / plan_check.BASELINE_REL, plan_check.BASELINE["size_bytes"])
        originals = transport.read_regular(ROOT / plan_check.ORIGINALS_REL, plan_check.ORIGINALS["size_bytes"])
        plan_check.verify_plan(plan_bytes=raw, expected_plan_sha256=PLAN["sha256"],
                              baseline_archive_bytes=baseline, originals_archive_bytes=originals)
        with zipfile.ZipFile(io.BytesIO(baseline)) as archive:
            historical = _json(archive.read("acquisition/source-bindings.json"))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise EntryStopError("entry_stop_plan_prerequisite") from exc
    return _json(raw), historical


def source_bindings(historical=None):
    if historical is None:
        _plan, historical = _admitted_plan()
    result = []
    for path in sorted(set(historical) | set(NEW_SOURCES)):
        actual = binding(_source(path))
        if path in historical:
            _same(actual, historical[path], "entry_stop_historical_source_changed")
        result.append({"path": path, **actual})
    return result


def _guard_sources(sources=None):
    if sources is None:
        return [{"path": path, **binding(_source(path))} for path in GUARD_SOURCES]
    selected = {row["path"]: {key: row[key] for key in ("size_bytes", "sha256")}
                for row in sources if row["path"] in GUARD_SOURCES}
    _need(set(selected) == set(GUARD_SOURCES), "entry_stop_guard_sources")
    return [{"path": path, **selected[path]} for path in GUARD_SOURCES]


def _request(attempt_id, qualification, hardware_qualification):
    _need(type(attempt_id) is str and re.fullmatch(r"[0-9a-f]{32}", attempt_id), "entry_stop_attempt_id")
    _need(attempt_id != plan_check.HISTORICAL_CONTEXT["attempt_id"], "entry_stop_historical_attempt_reused")
    for descriptor in (qualification, hardware_qualification):
        _binding(descriptor, "entry_stop_qualification_binding")
    plan, historical = _admitted_plan()
    checkpoint = {key: value for key, value in plan["checkpoint"].items() if key != "capability_qualified"}
    return {"record_type": "required_gate_idempotence_entry_stop_request_v0", "profile": PROFILE,
            "attempt_id": attempt_id, "plan": {"path": PLAN_REL, **PLAN}, "observer": plan["observer"],
            "cp0_request": cp0._request(attempt_id, plan["observer"]),
            "native_objects": plan["native_objects"], "static_relationships": plan["static_relationships"],
            "checkpoint": checkpoint,
            "execution": {key: plan["execution_policy"][key] for key in ("argv", "environment", "cwd")},
            "guard": {"program": _guard_checker().program_binding(), "qualification": qualification},
            "hardware_qualification": hardware_qualification,
            "mapping_metadata_policy": MAPPING_METADATA_POLICY,
            "limits": LIMITS, "sources": source_bindings(historical), **BOUNDARY}


def make_request(*, attempt_id, qualification_bytes, expected_qualification_sha256,
                 hardware_qualification_bytes, expected_hardware_qualification_sha256,
                 observer_descriptor=None):
    """Derive selected bytes after separate original admission; no acquisition."""
    _digest(expected_qualification_sha256, "entry_stop_guard_qualification_digest")
    _need(type(qualification_bytes) is bytes and sha(qualification_bytes) == expected_qualification_sha256,
          "entry_stop_guard_qualification_digest")
    qualification = _json(qualification_bytes)
    try:
        _guard_checker().validate_qualification(qualification_bytes, expected_sources=_guard_sources(),
                                                expected_environment=qualification["environment"])
    except (ValueError, KeyError, TypeError) as exc:
        raise EntryStopError("entry_stop_guard_qualification") from exc
    validate_hardware_qualification(hardware_qualification_bytes,
                                    expected_hardware_qualification_sha256,
                                    expected_context=qualification["environment"])
    _fresh_attempt(attempt_id, qualification, _json(hardware_qualification_bytes))
    result = _request(attempt_id, binding(qualification_bytes), binding(hardware_qualification_bytes))
    _same(qualification["environment"]["observer"],
          {key: result["observer"][key] for key in ("size_bytes", "sha256")},
          "entry_stop_qualification_observer")
    if observer_descriptor is not None:
        _same(observer_descriptor, result["observer"], "entry_stop_observer_selection")
    _validate_schema(result)
    return result


def validate_request(request_bytes, expected_request_sha256):
    _digest(expected_request_sha256, "entry_stop_request_digest")
    _need(type(request_bytes) is bytes and sha(request_bytes) == expected_request_sha256,
          "entry_stop_request_digest_mismatch")
    request = _json(request_bytes)
    try:
        expected = _request(request["attempt_id"], request["guard"]["qualification"], request["hardware_qualification"])
    except (KeyError, TypeError) as exc:
        raise EntryStopError("entry_stop_request_fields") from exc
    _same(request, expected, "entry_stop_request_contract")
    _validate_schema(request)
    return request


def file_limit(name):
    _need(name in FILE_NAMES, "entry_stop_file_name")
    if name == "observer.exe.bin":
        return LIMITS["observer_executable_bytes"]
    if name.startswith("native."):
        return NATIVE[ROLES[name.split(".")[1]]]["size_bytes"]
    if name.endswith(".executable.elf"):
        return NATIVE[ROLES["launcher"]]["size_bytes"]
    if ".rx.sample" in name:
        return NATIVE[ROLES[name.split(".")[1]]]["size_bytes"]
    if name in ("stdout.bin", "stderr.bin"):
        return LIMITS[name.split(".")[0] + "_bytes"]
    if name.endswith(".json"):
        return CONTROL_BYTES
    if ".debug." in name:
        return 48
    if name == "entry.siginfo.bin":
        return 128
    return LIMITS["proc_file_bytes"]


def _object(value, role=None, complete=False):
    if value is None:
        _need(not complete, "entry_stop_object_missing")
        return
    _keys(value, ("stat", "seals"), "entry_stop_object_fields")
    info = value["stat"]
    _keys(info, ("dev", "ino", "mode", "nlink", "size"), "entry_stop_stat_fields")
    for number in info.values():
        _integer(number, "entry_stop_stat_integer", maximum=(1 << 64) - 1)
    _integer(info["mode"], "entry_stop_stat_mode", maximum=0xffff)
    if value["seals"] is not None:
        _integer(value["seals"], "entry_stop_seals", maximum=0xffffffff)
    if not complete:
        return
    if role in ("launcher", "memory"):
        cp0._object(value, role)
    else:
        _need(role in ROLES and info["ino"] > 0 and stat.S_ISREG(info["mode"])
              and not info["mode"] & 0o6000 and info["nlink"] >= 1
              and info["size"] == NATIVE[ROLES[role]]["size_bytes"] and value["seals"] is None,
              "entry_stop_native_object")


def _point_files(files, point):
    result = {name[len(point) + 1:]: raw for name, raw in files.items() if name.startswith(point + ".")}
    for name in ("observer.exe.bin", "observer.stat.bin", "observer.status.bin", "kernel.boot_id.bin",
                 "host.json", "child.stat.setup.bin", "child.status.setup.bin", "child.pidfd.info.bin"):
        if name in files:
            result[name] = files[name]
    return result


def derive_cp0_spans(request, capture, files):
    projected = {"objects": {"executable": capture["objects"]["cp0_executable"],
                             "loader_before": capture["objects"]["native"]["loader"]["before"]}}
    try:
        return cp0.derive_spans(request["cp0_request"], projected, _point_files(files, "cp0"))
    except (ValueError, KeyError, struct.error) as exc:
        raise EntryStopError("entry_stop_cp0_relationships") from exc


def _entry_layout(request, capture, files):
    """Derive selected file-page coverage; unrelated maps remain metadata only."""
    maps = old.parse_maps(files["entry.child.maps.before.bin"])
    aux = cp0._auxv(files["cp0.auxv.before.bin"])
    objects = {row["path"]: row for row in request["native_objects"]}
    identities = {role: cp0._dev(capture["objects"]["native"][role]["before"]["stat"]) for role in ROLES}
    _need(len(set(identities.values())) == len(ROLES), "entry_stop_native_object_alias")
    _mapping_metadata(maps, set(identities.values()))
    spans, all_pages, rows_out = {}, set(), []
    for role, path in ROLES.items():
        obj = objects[path]
        rows = [row for row in maps if (row["major"], row["minor"], row["inode"]) == identities[role]]
        _need(rows, "entry_stop_selected_mapping_missing")
        segments = obj["elf"]["segments"]
        candidates = None
        for row in rows:
            possible = set()
            for segment in segments:
                file_start = segment["offset"] // PAGE_BYTES * PAGE_BYTES
                file_end = (segment["offset"] + segment["filesz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
                if file_start <= row["offset"] < file_end:
                    possible.add(row["start"] - segment["vaddr"] // PAGE_BYTES * PAGE_BYTES - (row["offset"] - file_start))
            candidates = possible if candidates is None else candidates & possible
        _need(candidates is not None and len(candidates) == 1, "entry_stop_mapping_bias_ambiguous")
        bias = next(iter(candidates))
        _need(0 < bias < (1 << 47) and bias % PAGE_BYTES == 0, "entry_stop_mapping_bias")
        if role == "launcher":
            _need(bias + obj["elf"]["entry"] == aux[9], "entry_stop_launcher_bias")
        elif role == "loader":
            _need(bias == aux[7], "entry_stop_loader_bias")
        relro = set()
        for region in obj["initialization"]["gnu_relro"]:
            start = (bias + region["vaddr"]) // PAGE_BYTES * PAGE_BYTES
            end = (bias + region["vaddr"] + region["memsz"]) // PAGE_BYTES * PAGE_BYTES
            _need(0 <= end - start <= NATIVE[path]["size_bytes"] + 2 * PAGE_BYTES, "entry_stop_relro_bounds")
            relro.update(range(start, end, PAGE_BYTES))
        expected = {}
        for segment in segments:
            start = (bias + segment["vaddr"]) // PAGE_BYTES * PAGE_BYTES
            end = (bias + segment["vaddr"] + segment["filesz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
            permissions = "r" + ("w" if segment["flags"] & 2 else "-") + ("x" if segment["flags"] & 1 else "-") + "p"
            for page in range(start, end, PAGE_BYTES):
                _need(page not in expected and page not in all_pages, "entry_stop_selected_segment_overlap")
                allowed = {permissions}
                if page in relro and permissions[1] == "w":
                    allowed.add(permissions[0] + "-" + permissions[2:])
                expected[page] = (segment["offset"] // PAGE_BYTES * PAGE_BYTES + page - start, allowed)
            rows_out.append({"object": role, "segment_index": segment["index"], "load_bias": bias,
                             "address": bias + segment["vaddr"], "file_offset": segment["offset"],
                             "file_bytes": segment["filesz"], "mapping_coverage_verified": True})
        seen = set()
        for row in rows:
            _need((row["end"] - row["start"]) // PAGE_BYTES <= len(expected), "entry_stop_mapping_range")
            for page in range(row["start"], row["end"], PAGE_BYTES):
                _need(page in expected and page not in seen, "entry_stop_extra_selected_mapping")
                offset, permissions = expected[page]
                _need(row["offset"] + page - row["start"] == offset, "entry_stop_mapping_file_offset")
                _need(row["permissions"] in permissions, "entry_stop_mapping_permissions")
                seen.add(page)
        _need(seen == set(expected), "entry_stop_mapping_coverage")
        all_pages.update(seen)
        rx = [segment for segment in segments if segment["flags"] == 5]
        _need(len(rx) == 1, "entry_stop_rx_profile")
        spans[role] = {"address": bias + rx[0]["vaddr"], "size": rx[0]["filesz"]}
    return spans, rows_out


def _mapping_metadata(maps, selected):
    """Bound every remaining row without assigning anonymous-byte authority."""
    policy = MAPPING_METADATA_POLICY
    _need(len(maps) <= policy["total_rows"], "entry_stop_map_count")
    specials, anonymous_rows, anonymous_bytes, heaps = set(), 0, 0, 0
    for row in maps:
        if (row["major"], row["minor"], row["inode"]) in selected:
            continue
        _need(row["major"] == row["minor"] == row["inode"] == row["offset"] == 0,
              "entry_stop_unselected_file_mapping")
        size, name = row["end"] - row["start"], row["path"]
        if name in policy["kernel_rows"]:
            expected = policy["kernel_rows"][name]
            _need(name not in specials and row["permissions"] == expected["permissions"]
                  and size <= expected["max_bytes"], "entry_stop_kernel_mapping_metadata")
            specials.add(name)
        else:
            _need(name in policy["anonymous_names"] and row["permissions"] in policy["anonymous_permissions"],
                  "entry_stop_anonymous_mapping_metadata")
            anonymous_rows += 1
            anonymous_bytes += size
            heaps += name == "[heap]"
    _need(set(policy["required_kernel_rows"]) <= specials, "entry_stop_kernel_mapping_missing")
    _need(anonymous_rows <= policy["anonymous_rows"] and anonymous_bytes <= policy["anonymous_total_bytes"]
          and heaps <= 1, "entry_stop_anonymous_mapping_budget")


def derive_entry_spans(request, capture, files):
    try:
        return _entry_layout(request, capture, files)[0]
    except (ValueError, KeyError, struct.error) as exc:
        if isinstance(exc, EntryStopError):
            raise
        raise EntryStopError("entry_stop_entry_relationships") from exc


def _validate_schema(value):
    try:
        schema = _json(_source(SCHEMA_REL))
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise EntryStopError("entry_stop_schema") from exc


def _lifecycle(value, *, complete):
    """Check the owned one-child transition transcript without taking actions."""
    _integer(value["observer_pid"], "entry_stop_observer_pid", 1, 0x7fffffff)
    child = value["child_pid"]
    if child is not None:
        _integer(child, "entry_stop_child_pid", 1, 0x7fffffff)
        _need(child != value["observer_pid"], "entry_stop_child_equals_observer")
    timing = value["timing"]
    _keys(timing, ("started_ns", "cp0_ns", "entry_ns", "finished_ns"), "entry_stop_timing_fields")
    for name, number in timing.items():
        if number is not None or name in ("started_ns", "finished_ns"):
            _integer(number, "entry_stop_timing_integer")
    start, finish = timing["started_ns"], timing["finished_ns"]
    _need(start <= finish, "entry_stop_timing_order")
    previous = start
    for name in ("cp0_ns", "entry_ns"):
        if timing[name] is not None:
            _need(previous <= timing[name] <= finish, "entry_stop_timing_order")
            previous = timing[name]
    _need(timing["entry_ns"] is None or timing["cp0_ns"] is not None,
          "entry_stop_entry_without_cp0")
    wait = value["wait"]
    _keys(wait, ("setup", "cp0", "entry", "terminal", "event_msg"), "entry_stop_wait_fields")
    for number in wait.values():
        if number is not None:
            _integer(number, "entry_stop_wait_integer", maximum=0xffffffff)
    ownership = value["ownership"]
    _keys(ownership, ("pidfd_opened", "proc_dir_pinned", "child_reaped", "pre_exec_resumes",
                     "cp0_to_entry_resumes", "post_entry_resumes", "detached", "ptrace_options",
                     "kill_sent"), "entry_stop_ownership_fields")
    for name in ("pidfd_opened", "proc_dir_pinned", "child_reaped", "detached", "kill_sent"):
        _boolean(ownership[name], "entry_stop_ownership_boolean")
    for name in ("pre_exec_resumes", "cp0_to_entry_resumes"):
        _integer(ownership[name], "entry_stop_resume_integer", maximum=1)
    _integer(ownership["post_entry_resumes"], "entry_stop_forbidden_resume", maximum=0)
    _integer(ownership["ptrace_options"], "entry_stop_ptrace_options", maximum=PTRACE_OPTIONS)
    _need(ownership["ptrace_options"] in (0, PTRACE_OPTIONS) and not ownership["detached"],
          "entry_stop_forbidden_transition")
    _need(ownership["cp0_to_entry_resumes"] <= ownership["pre_exec_resumes"],
          "entry_stop_resume_order")
    events = value["events"]
    _need(type(events) is list and len(events) <= LIMITS["wait_records"], "entry_stop_event_count")
    previous = start
    for event in events:
        _keys(event, ("phase", "pid", "status", "event_msg", "observed_ns"), "entry_stop_event_fields")
        _need(event["phase"] in ("setup", "cp0", "entry", "terminal", "unexpected"),
              "entry_stop_event_phase")
        _integer(event["pid"], "entry_stop_event_pid", 1, 0x7fffffff)
        _integer(event["status"], "entry_stop_event_status", maximum=0xffffffff)
        if event["event_msg"] is not None:
            _integer(event["event_msg"], "entry_stop_event_msg", maximum=(1 << 64) - 1)
        _integer(event["observed_ns"], "entry_stop_event_time")
        _need(previous <= event["observed_ns"] <= finish, "entry_stop_event_order")
        previous = event["observed_ns"]
    if not complete:
        return
    _need(child is not None and timing["cp0_ns"] is not None and timing["entry_ns"] is not None,
          "entry_stop_complete_process")
    _need(timing["entry_ns"] - start <= LIMITS["wall_seconds"] * 10**9
          and finish - start <= (LIMITS["wall_seconds"] + LIMITS["cleanup_seconds"]) * 10**9,
          "entry_stop_deadline")
    _same(wait, {"setup": STOP_WAIT, "cp0": EXEC_WAIT, "entry": ENTRY_WAIT,
                 "terminal": KILL_WAIT, "event_msg": child}, "entry_stop_completed_wait")
    _same(ownership, {"pidfd_opened": True, "proc_dir_pinned": True, "child_reaped": True,
                     "pre_exec_resumes": 1, "cp0_to_entry_resumes": 1, "post_entry_resumes": 0,
                     "detached": False, "ptrace_options": PTRACE_OPTIONS, "kill_sent": True},
          "entry_stop_completed_ownership")
    _need(len(events) == 4, "entry_stop_completed_events")
    for event, phase, status in zip(events, ("setup", "cp0", "entry", "terminal"),
                                    (STOP_WAIT, EXEC_WAIT, ENTRY_WAIT, KILL_WAIT)):
        _same({key: event[key] for key in ("phase", "pid", "status", "event_msg")},
              {"phase": phase, "pid": child, "status": status,
               "event_msg": child if phase == "cp0" else None}, "entry_stop_completed_event")
    _need(events[1]["observed_ns"] <= timing["cp0_ns"] <= events[2]["observed_ns"]
          <= timing["entry_ns"] <= events[3]["observed_ns"], "entry_stop_checkpoint_event_order")


def _rip(raw):
    _need(type(raw) is bytes and len(raw) == 216, "entry_stop_register_size")
    return struct.unpack_from("<Q", raw, 16 * 8)[0]


def _debug(raw, expected):
    _need(type(raw) is bytes and len(raw) == 48, "entry_stop_debug_size")
    _same(list(struct.unpack("<6Q", raw)), list(expected), "entry_stop_debug_state")


def _breakpoint(record, target, before, armed, hit, siginfo):
    _integer(target, "entry_stop_target", 1, (1 << 47) - 1)
    _same(record, {"target": target, "writes": [
        {"register": 0, "value": target, "returncode": 0, "errno": 0},
        {"register": 6, "value": DR6_RESERVED, "returncode": 0, "errno": 0},
        {"register": 7, "value": 1, "returncode": 0, "errno": 0}],
        "general_register_writes": 0, "instruction_pointer_writes": 0,
        "target_memory_writes": 0}, "entry_stop_breakpoint_programming")
    _debug(before, (0, 0, 0, 0, DR6_RESERVED, 0))
    _debug(armed, (target, 0, 0, 0, DR6_RESERVED, 1))
    _debug(hit, (target, 0, 0, 0, DR6_RESERVED | 1, 1))
    _need(type(siginfo) is bytes and len(siginfo) == 128, "entry_stop_siginfo_size")
    _need(struct.unpack_from("<iii", siginfo) == (5, 0, 4)
          and struct.unpack_from("<Q", siginfo, 16)[0] == target, "entry_stop_trap_cause")


def validate_hardware_qualification(raw, expected_sha256, expected_context=None):
    """Reconstruct the separate, benign static-ELF ABI qualification only."""
    try:
        return _validate_hardware_qualification(raw, expected_sha256, expected_context)
    except (ValueError, KeyError, TypeError, IndexError, struct.error, OverflowError) as exc:
        if isinstance(exc, EntryStopError):
            raise
        raise EntryStopError("entry_stop_hardware_evidence_invalid") from exc


def _validate_hardware_qualification(raw, expected_sha256, expected_context=None):
    _digest(expected_sha256, "entry_stop_hardware_digest")
    _need(type(raw) is bytes and sha(raw) == expected_sha256, "entry_stop_hardware_digest_mismatch")
    value = _json(raw)
    _keys(value, ("record_type", "profile", "status", "failure", "attempt_id", "context", "sources",
                  "probe", "observer_pid", "child_pid", "wait", "events", "ownership", "timing",
                  "raw", "breakpoint", *HARDWARE_BOUNDARY), "entry_stop_hardware_fields")
    _need(value["record_type"] == "required_gate_idempotence_entry_stop_hardware_qualification_v0"
          and value["profile"] == "linux_x86_64_entry_stop_hardware_qualification_v0"
          and value["status"] == "completed" and value["failure"] is None,
          "entry_stop_hardware_incomplete")
    _need(type(value["attempt_id"]) is str and re.fullmatch(r"[0-9a-f]{32}", value["attempt_id"]),
          "entry_stop_hardware_attempt")
    _same({key: value[key] for key in HARDWARE_BOUNDARY}, HARDWARE_BOUNDARY, "entry_stop_hardware_boundary")
    guard = _guard_checker()
    guard.validate_environment(value["context"])
    if expected_context is not None:
        _same(value["context"], expected_context, "entry_stop_hardware_context")
    _same(value["sources"], [{"path": path, **binding(_source(path))} for path in HARDWARE_SOURCES],
          "entry_stop_hardware_sources")
    _same(value["probe"], HARDWARE_PROBE, "entry_stop_hardware_probe")
    _lifecycle(value, complete=True)
    _keys(value["raw"], HARDWARE_FILES, "entry_stop_hardware_raw_roster")
    files = {}
    for name, encoded in value["raw"].items():
        _need(type(encoded) is str and 0 < len(encoded) <= 2 * LIMITS["proc_file_bytes"]
              and len(encoded) % 2 == 0 and re.fullmatch(r"[0-9a-f]+", encoded),
              "entry_stop_hardware_raw_encoding")
        files[name] = bytes.fromhex(encoded)
    _bound(files["executable.elf"], HARDWARE_PROBE, "entry_stop_hardware_executable")
    _need(files["entry.memory.bin"] == b"\x0f\x0b", "entry_stop_hardware_entry_bytes")
    for point in ("cp0", "entry"):
        projected = {name: files[name] for name in ("observer.stat.bin", "observer.status.bin",
            "child.stat.setup.bin", "child.status.setup.bin", "child.pidfd.info.bin")}
        for kind in ("stat", "status"):
            for side in ("before", "after"):
                projected["child." + kind + "." + side + ".bin"] = files[point + ".child." + kind + ".bin"]
        cp0._processes(value, projected)
        _need(_rip(files[point + ".regs.bin"]) == 0x400080, "entry_stop_hardware_entry_rip")
    _need(files["cp0.auxv.bin"] == files["entry.auxv.bin"], "entry_stop_hardware_auxv_changed")
    aux = cp0._auxv(files["cp0.auxv.bin"])
    _same({key: aux[key] for key in (3, 4, 5, 6, 7, 9)},
          {3: 0x400040, 4: 56, 5: 1, 6: 4096, 7: 0, 9: 0x400080},
          "entry_stop_hardware_auxv")
    _breakpoint(value["breakpoint"], 0x400080, files["cp0.debug.before.bin"],
                files["cp0.debug.armed.bin"], files["entry.debug.bin"], files["entry.siginfo.bin"])
    _validate_schema(value)
    return {"status": "accepted", "hardware_qualification_verified": True,
            "qualification": binding(raw), "context": value["context"], **HARDWARE_BOUNDARY}


def _context(request, files):
    host = _json(files["host.json"])
    _keys(host, ("platform", "observer_namespaces", "child_namespaces"), "entry_stop_host_fields")
    _keys(host["platform"], ("system", "machine", "release", "version"), "entry_stop_host_platform")
    _same(host["observer_namespaces"], host["child_namespaces"], "entry_stop_namespaces_changed")
    boot = files["kernel.boot_id.bin"]
    _need(type(boot) is bytes and re.fullmatch(
        rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n", boot),
        "entry_stop_boot_identity")
    context = {"uname": {"sysname": host["platform"]["system"],
                         "release": host["platform"]["release"], "version": host["platform"]["version"],
                         "machine": host["platform"]["machine"]},
               "boot_id": boot.decode("ascii").rstrip("\n"),
               "observer": binding(files["observer.exe.bin"]), "namespaces": host["observer_namespaces"]}
    _guard_checker().validate_environment(context)
    _same(context["observer"], {key: request["observer"][key] for key in ("size_bytes", "sha256")},
          "entry_stop_observer_binding")
    return context


def _fresh_attempt(attempt_id, qualification, hardware):
    selected = {row["attempt_id"] for row in qualification["cases"]}
    selected.update((hardware["attempt_id"], plan_check.HISTORICAL_CONTEXT["attempt_id"]))
    _need(attempt_id not in selected, "entry_stop_qualification_attempt_reused")


def _fresh_child(pid, starttime, qualification, hardware):
    identities = {(row["child_pid"], row["starttime"]) for row in qualification["cases"]}
    hardware_stat = old.parse_proc_stat(bytes.fromhex(hardware["raw"]["child.stat.setup.bin"]))
    identities.add((hardware["child_pid"], hardware_stat["starttime"]))
    _need((pid, starttime) not in identities, "entry_stop_qualification_child_reused")


def _guard_evidence(request, capture, files, context):
    guard = _guard_checker()
    _bound(files["guard.qualification.json"], request["guard"]["qualification"],
           "entry_stop_guard_qualification_binding")
    guard.validate_qualification(files["guard.qualification.json"],
        expected_sources=_guard_sources(request["sources"]), expected_environment=context)
    qualified = _json(files["guard.qualification.json"])
    _need(qualified["timing"]["finished_ns"] <= capture["timing"]["started_ns"],
          "entry_stop_guard_not_prequalified")
    _bound(files["breakpoint.qualification.json"], request["hardware_qualification"],
           "entry_stop_hardware_qualification_binding")
    validate_hardware_qualification(files["breakpoint.qualification.json"],
        request["hardware_qualification"]["sha256"], expected_context=context)
    hardware = _json(files["breakpoint.qualification.json"])
    _need(hardware["timing"]["finished_ns"] <= capture["timing"]["started_ns"],
          "entry_stop_hardware_not_prequalified")
    _fresh_attempt(request["attempt_id"], qualified, hardware)
    _keys(capture["guard"], ("launcher_fd", "receipt_fd"), "entry_stop_guard_descriptor_fields")
    launcher_fd, receipt_fd = capture["guard"]["launcher_fd"], capture["guard"]["receipt_fd"]
    for fd in (launcher_fd, receipt_fd):
        _integer(fd, "entry_stop_guard_fd", 3, (1 << 20) - 1)
    _need(launcher_fd != receipt_fd, "entry_stop_guard_descriptor_alias")
    starttime = old.parse_proc_stat(files["child.stat.setup.bin"])["starttime"]
    _fresh_child(capture["child_pid"], starttime, qualified, hardware)
    setup_fds = _json(files["child.fds.setup.json"])
    guard.validate_installation(files["guard.install.json"], files["guard.program.bin"],
        expected_pid=capture["child_pid"], expected_parent_pid=capture["observer_pid"],
        expected_starttime=starttime, expected_launcher_fd=launcher_fd, expected_receipt_fd=receipt_fd,
        expected_attempt_id=request["attempt_id"], expected_request_sha256=capture["request_sha256"],
        setup_status_bytes=files["child.status.setup.bin"], setup_fd_records=setup_fds,
        checkpoint_status_bytes=tuple(files[point + ".child.status." + side + ".bin"]
                                      for point in ("cp0", "entry") for side in ("before", "after")))
    normalized = guard.validate_descriptors(setup_fds, (0, 1, 2, launcher_fd), launcher_fd)
    retained = capture["objects"]["retained"]["stat"]
    _same({key: normalized[launcher_fd]["stat"][key] for key in ("dev", "ino", "mode", "size")},
          {key: retained[key] for key in ("dev", "ino", "mode", "size")},
          "entry_stop_guard_launcher_object")
    for point in ("cp0", "entry"):
        observed = guard.validate_descriptors(_json(files["child.fds." + point + ".json"]), (0, 1, 2))
        _same(observed, {fd: normalized[fd] for fd in (0, 1, 2)}, "entry_stop_inherited_fds_changed")


def verify_capture(*, request_bytes, expected_request_sha256, capture_bytes,
                   expected_capture_sha256, files):
    """Accept a bounded retained record; completion requires every obligation."""
    try:
        return _verify_capture(request_bytes=request_bytes, expected_request_sha256=expected_request_sha256,
            capture_bytes=capture_bytes, expected_capture_sha256=expected_capture_sha256, files=files)
    except (ValueError, KeyError, TypeError, IndexError, struct.error, OverflowError) as exc:
        if isinstance(exc, EntryStopError):
            raise
        raise EntryStopError("entry_stop_evidence_invalid") from exc


def _verify_capture(*, request_bytes, expected_request_sha256, capture_bytes,
                    expected_capture_sha256, files):
    request = validate_request(request_bytes, expected_request_sha256)
    _digest(expected_capture_sha256, "entry_stop_capture_digest")
    _need(type(capture_bytes) is bytes and sha(capture_bytes) == expected_capture_sha256,
          "entry_stop_capture_digest_mismatch")
    capture = _json(capture_bytes)
    _keys(capture, ("record_type", "profile", "attempt_id", "request_sha256", "status", "failure",
                   "observer_pid", "child_pid", "timing", "wait", "events", "ownership", "guard",
                   "objects", "files", *BOUNDARY), "entry_stop_capture_fields")
    _validate_schema(capture)
    _need(capture["record_type"] == "required_gate_idempotence_entry_stop_capture_v0"
          and capture["profile"] == PROFILE and capture["attempt_id"] == request["attempt_id"]
          and capture["request_sha256"] == expected_request_sha256, "entry_stop_capture_request")
    _same({key: capture[key] for key in BOUNDARY}, BOUNDARY, "entry_stop_boundary")
    _need(capture["status"] in ("completed", "incomplete"), "entry_stop_capture_status")
    complete = capture["status"] == "completed"
    _need((complete and capture["failure"] is None) or (not complete and type(capture["failure"]) is str
          and re.fullmatch(r"[a-z][a-z0-9_]{0,119}", capture["failure"])), "entry_stop_failure")
    _lifecycle(capture, complete=complete)
    _keys(capture["guard"], ("launcher_fd", "receipt_fd"), "entry_stop_guard_fields")
    for number in capture["guard"].values():
        if number is not None:
            _integer(number, "entry_stop_guard_fd", 3, (1 << 20) - 1)
    objects = capture["objects"]
    _keys(objects, ("retained", "cp0_executable", "entry_executable", "cp0_memory", "entry_memory", "native"),
          "entry_stop_objects_fields")
    _keys(objects["native"], ROLES, "entry_stop_native_object_roster")
    for name in ("retained", "cp0_executable", "entry_executable", "cp0_memory", "entry_memory"):
        _object(objects[name], "memory" if name.endswith("_memory") else "launcher", complete)
    for role in ROLES:
        _keys(objects["native"][role], ("before", "after"), "entry_stop_native_snapshots")
        for obj in objects["native"][role].values():
            _object(obj, role, complete)
    _need(type(files) is dict and {"request.json", "attempt_start.json"} <= set(files) <= set(FILE_NAMES),
          "entry_stop_file_roster")
    _need(all(type(raw) is bytes and len(raw) <= file_limit(name) for name, raw in files.items())
          and len(files) + 1 <= LIMITS["capture_files"]
          and len(capture_bytes) + sum(map(len, files.values())) <= LIMITS["total_capture_bytes"],
          "entry_stop_file_bounds")
    _same(capture["files"], [{"path": name, **binding(raw)} for name, raw in sorted(files.items())],
          "entry_stop_file_bindings")
    _need(files["request.json"] == request_bytes, "entry_stop_preserved_request")
    _same(_json(files["attempt_start.json"]),
          {"record_type": "required_gate_idempotence_entry_stop_attempt_start_v0", "profile": PROFILE,
           "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
           "observer_pid": capture["observer_pid"], "started_ns": capture["timing"]["started_ns"]},
          "entry_stop_attempt_start")
    memory_relations, segment_relations = [], []
    if complete:
        _need(set(files) == set(FILE_NAMES), "entry_stop_complete_roster")
        for role, path in ROLES.items():
            before, after = objects["native"][role]["before"], objects["native"][role]["after"]
            _same(before, after, "entry_stop_native_object_changed")
            for side in ("before", "after"):
                _bound(files["native." + role + "." + side + ".elf"], NATIVE[path],
                       "entry_stop_original_native_bytes")
        for name in ("cp0_executable", "entry_executable"):
            _same(objects[name], objects["retained"], "entry_stop_launcher_object_changed")
        _same(objects["native"]["launcher"]["before"], objects["retained"],
              "entry_stop_retained_native_launcher")
        for point in ("cp0", "entry"):
            _bound(files[point + ".executable.elf"], NATIVE[ROLES["launcher"]], "entry_stop_executable_bytes")
            link = files[point + ".child.exe.link.bin"]
            _need(0 < len(link) <= 4096 and b"\0" not in link, "entry_stop_executable_link")
            for stem in ("child.maps", "regs", "auxv"):
                _need(files[point + "." + stem + ".before.bin"] == files[point + "." + stem + ".after.bin"],
                      "entry_stop_checkpoint_changed")
            cp0._processes(capture, _point_files(files, point))
        _need(files["cp0.auxv.before.bin"] == files["entry.auxv.before.bin"], "entry_stop_auxv_changed")
        context = _context(request, files)
        _guard_evidence(request, capture, files, context)
        cp0_spans = derive_cp0_spans(request, capture, files)
        entry_spans, segment_relations = _entry_layout(request, capture, files)
        target = cp0._auxv(files["cp0.auxv.before.bin"])[9]
        _need(_rip(files["entry.regs.before.bin"]) == target, "entry_stop_entry_rip")
        _breakpoint(_json(files["breakpoint.json"]), target, files["cp0.debug.before.bin"],
                    files["cp0.debug.armed.bin"], files["entry.debug.before.bin"], files["entry.siginfo.bin"])
        _need(files["entry.debug.before.bin"] == files["entry.debug.after.bin"], "entry_stop_debug_changed")
        for row in request["cp0_request"]["memory_obligations"]:
            raw = files["cp0." + row["file"]]
            _bound(raw, {key: row[key] for key in ("size_bytes", "sha256")}, "entry_stop_cp0_sample")
            memory_relations.append({"checkpoint": "cp0", "object": row["object"],
                "segment_index": row["segment_index"], "sample_index": row["sample_index"],
                "address": cp0_spans[row["object"]]["address"], "file_offset": row["file_offset"],
                **binding(raw), "matches_original": True})
        for obj in request["native_objects"]:
            role = next(role for role, path in ROLES.items() if path == obj["path"])
            for sample in obj["rx_samples"]:
                name = "entry." + role + ".rx.sample" + str(sample["sample_index"]) + ".bin"
                raw = files[name]
                _bound(raw, {key: sample[key] for key in ("size_bytes", "sha256")}, "entry_stop_entry_sample")
                memory_relations.append({"checkpoint": "entry", "object": role,
                    "segment_index": sample["segment_index"], "sample_index": sample["sample_index"],
                    "address": entry_spans[role]["address"], "file_offset": sample["file_offset"],
                    **binding(raw), "matches_original": True})
        _need(len(segment_relations) == 24 and len(memory_relations) == 16,
              "entry_stop_obligation_cardinality")
    _same(source_bindings(), request["sources"], "entry_stop_sources_changed")
    return {"record_type": "required_gate_idempotence_entry_stop_verification_v0", "profile": PROFILE,
            "attempt_id": request["attempt_id"], "status": "accepted", "request_sha256": expected_request_sha256,
            "capture_sha256": expected_capture_sha256, "observation_record_verified": True,
            "observation_complete": complete, **{name: complete for name in NARROW_FLAGS},
            "memory_relations": memory_relations, "segment_relations": segment_relations,
            "static_relationships": request["static_relationships"],
            "consumer_resolution_observed": False, "failure": capture["failure"], **BOUNDARY}


def read_capture_directory(path):
    chain = []
    try:
        fd, chain = old._pin_directory(path)
        before = os.fstat(fd)
        _need(stat.S_IMODE(before.st_mode) == 0o700, "entry_stop_directory_mode")
        names = sorted(entry.name for entry in os.scandir(fd))
        _need("capture.json" in names and set(names) <= {"capture.json", *FILE_NAMES},
              "entry_stop_directory_roster")
        identities = {}
        raw = old._read_relative(fd, "capture.json", CONTROL_BYTES, private=True, identities=identities)
        files = {name: old._read_relative(fd, name, file_limit(name), private=True, identities=identities)
                 for name in names if name != "capture.json"}
        _need(len(files) + 1 <= LIMITS["capture_files"]
              and len(raw) + sum(map(len, files.values())) <= LIMITS["total_capture_bytes"],
              "entry_stop_capture_size")
        _need(old._identity(before) == old._identity(os.fstat(fd))
              and sorted(entry.name for entry in os.scandir(fd)) == names, "entry_stop_directory_changed")
        for name, expected in identities.items():
            _need(old._identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == expected,
                  "entry_stop_file_changed_after_read")
        old._check_chain(chain)
        return raw, files
    except OSError as exc:
        raise EntryStopError("entry_stop_directory_unreadable") from exc
    finally:
        old._close_chain(chain)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--capture-directory", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        request = old.read_selection_file(args.request)
        capture, files = read_capture_directory(args.capture_directory)
        result = verify_capture(request_bytes=request, expected_request_sha256=args.request_sha256,
            capture_bytes=capture, expected_capture_sha256=args.capture_sha256, files=files)
        raw = canonical(result)
        if args.output:
            old.write_new(args.output, raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (ValueError, OSError) as exc:
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

