"""Independently reconstruct a fixed-probe stopped mapping observation.

The checked relationship concerns the kernel-reported executable backing object
at one cooperative post-exec stop. It does not authenticate the kernel, collector
history, resident memory, a selected runtime, or the whole native dependency set.
The collector is deliberately never imported by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types


PROFILE = "linux_x86_64_fixed_probe_stopped_mapping_v0"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "schemas/required_gate_idempotence_mapping_observation_v0.schema.json",
    "tools/check_required_gate_idempotence_mapping_observation_v0.py",
    "tools/required_gate_idempotence_mapping_observation_v0.py",
    "tools/required_gate_idempotence_mapping_probe_v0.py",
)
PROBE_SOURCE = "tools/required_gate_idempotence_mapping_probe_v0.py"
LIMITS = {
    "wall_seconds": 15,
    "cleanup_seconds": 2,
    "proc_file_bytes": 65536,
    "observer_executable_bytes": 33554432,
    "stdout_bytes": 4096,
    "stderr_bytes": 4096,
    "total_capture_bytes": 41943040,
}
BOUNDARY = {
    "record_status": "example",
    "diagnostic_only": True,
    "physical_execution_authenticated": False,
    "host_observation_authenticated": False,
    "host_environment_qualified": False,
    "host_launcher_runtime_verified": False,
    "loader_resolution_verified": False,
    "process_memory_bytes_verified": False,
    "complete_native_closure_verified": False,
    "containment_enforced": False,
    "execution_ready": False,
    "execution_authorized": False,
    "selected_runtime_executed": False,
    "production_gate_eligible": False,
    "metric_pass": None,
    "authority_effect": "none",
}
FILE_NAMES = (
    "attempt_start.json", "child.exe.link.bin", "child.maps.after.bin",
    "child.maps.before.bin", "child.pidfd.info.bin", "child.stat.after.bin",
    "child.stat.before.bin", "child.status.after.bin", "child.status.before.bin",
    "executable.elf", "host.json", "kernel.boot_id.bin", "observer.exe.bin",
    "observer.stat.bin", "observer.status.bin", "probe.elf", "retained.elf",
    "selection.json", "stderr.bin", "stdout.bin",
)
NAMESPACES = ("cgroup", "ipc", "mnt", "net", "pid", "user", "uts")
CONTROL_BYTES = 1024 * 1024
SOURCE_BYTES = 1024 * 1024
MAX_INTEGER = (1 << 63) - 1
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
ATTEMPT_RE = re.compile(r"[0-9a-f]{32}\Z")
ERROR_RE = re.compile(r"[a-z][a-z0-9_]{0,119}\Z")
BASE_ADDRESS = 0x400000
PAGE_BYTES = 4096
ENTRY_OFFSET = 176
FULL_SEALS = 15
STOP_WAIT = (19 << 8) | 0x7f
KILL_WAIT = 9


class MappingError(ValueError):
    """A stable, finite rejection reason."""


def _need(condition, code):
    if not condition:
        raise MappingError(code)


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise MappingError("mapping_json_value") from exc


def sha(raw):
    _need(type(raw) is bytes, "mapping_bytes_required")
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def _keys(value, names, code):
    _need(type(value) is dict and set(value) == set(names), code)


def _integer(value, code, minimum=0, maximum=MAX_INTEGER):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _boolean(value, code):
    _need(type(value) is bool, code)
    return value


def _digest(value, code):
    _need(type(value) is str and SHA_RE.fullmatch(value), code)
    return value


def _same(value, expected, code):
    # Canonical comparison distinguishes bools from integers and null from zero.
    _need(canonical(value) == canonical(expected), code)


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "mapping_duplicate_json_key")
        result[key] = value
    return result


def _constant(_value):
    raise MappingError("mapping_nonfinite_json_number")


def _json(raw, code, limit=CONTROL_BYTES):
    _need(type(raw) is bytes and 0 < len(raw) <= limit, code)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
    except MappingError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise MappingError(code) from exc
    _need(canonical(value) == raw, code + "_canonical")
    return value


def _bound(raw, descriptor, code, maximum=CONTROL_BYTES):
    _keys(descriptor, ("sha256", "size_bytes"), code)
    _digest(descriptor["sha256"], code)
    _integer(descriptor["size_bytes"], code, maximum=maximum)
    _same(binding(raw), descriptor, code)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _directory_identity(info):
    return info.st_dev, info.st_ino, info.st_mode


def _close_chain(chain):
    for fd, _parent, _name, _original in reversed(chain):
        os.close(fd)


def _pin_directory(path):
    """Open each component without following links; retain the entire chain."""
    value = os.fspath(path)
    _need(type(value) is str and value and "\x00" not in value,
          "mapping_directory_path")
    if not value.startswith("/"):
        value = os.getcwd() + "/" + value
    parts = value.split("/")
    _need(".." not in parts, "mapping_directory_path")
    parts = [part for part in parts if part not in ("", ".")]
    chain = []
    try:
        root_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        chain.append((root_fd, None, "/", _directory_identity(os.fstat(root_fd))))
        for part in parts:
            parent = chain[-1][0]
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=parent)
            chain.append((fd, parent, part, _directory_identity(os.fstat(fd))))
        _check_chain(chain)
        return chain[-1][0], chain
    except BaseException:
        _close_chain(chain)
        raise


def _check_chain(chain):
    for fd, parent, name, original in chain:
        current = os.fstat(fd)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need(stat.S_ISDIR(current.st_mode)
              and _directory_identity(current) == _directory_identity(named) == original,
              "mapping_directory_chain_changed")


def _file_parent(path):
    value = os.fspath(path)
    _need(type(value) is str and value and "\x00" not in value, "mapping_file_path")
    parent, name = os.path.split(value)
    _need(name not in ("", ".", ".."), "mapping_file_path")
    return parent or ".", name


def _read_fd(fd, limit, code):
    out = bytearray()
    while len(out) <= limit:
        block = os.read(fd, min(65536, limit + 1 - len(out)))
        if not block:
            break
        out.extend(block)
    _need(len(out) <= limit, code + "_size")
    return bytes(out)


def _read_relative(parent_fd, name, limit, *, private=False, identities=None):
    _need(type(name) is str and name not in ("", ".", "..") and "/" not in name,
          "mapping_file_name")
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
          "mapping_file_identity")
    if private:
        _need(stat.S_IMODE(before.st_mode) == 0o600, "mapping_file_mode")
    _need(before.st_size <= limit, "mapping_file_size")
    # A substituted FIFO must not block before descriptor identity is checked.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                 dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        _need(_identity(before) == _identity(opened), "mapping_file_changed")
        raw = _read_fd(fd, limit, "mapping_file")
        after = os.fstat(fd)
        final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        _need(_identity(opened) == _identity(after) == _identity(final),
              "mapping_file_changed")
        _need(len(raw) == after.st_size, "mapping_file_changed")
        if identities is not None:
            identities[name] = _identity(after)
        return raw
    finally:
        os.close(fd)


def _source_bytes(relative):
    parts = relative.split("/")
    opened = []
    try:
        fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        opened.append(fd)
        for part in parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=fd)
            opened.append(fd)
        return _read_relative(fd, parts[-1], SOURCE_BYTES)
    except OSError as exc:
        raise MappingError("mapping_source_unreadable") from exc
    finally:
        for fd in reversed(opened):
            os.close(fd)


def source_bindings():
    return [{"path": path, **binding(_source_bytes(path))} for path in SOURCE_PATHS]


def _probe_bytes(sources):
    selected = next(row for row in sources if row["path"] == PROBE_SOURCE)
    raw = _source_bytes(PROBE_SOURCE)
    _bound(raw, {k: selected[k] for k in ("sha256", "size_bytes")},
           "mapping_probe_source_changed", maximum=SOURCE_BYTES)
    module = types.ModuleType("_pulse_mapping_fixed_probe")
    module.__file__ = str(ROOT / PROBE_SOURCE)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    _need(module.BASE_ADDRESS == BASE_ADDRESS and module.PAGE_BYTES == PAGE_BYTES
          and module.ENTRY_OFFSET == ENTRY_OFFSET, "mapping_probe_layout")
    result = module.probe_bytes()
    _need(type(result) is bytes and len(result) == PAGE_BYTES, "mapping_probe_bytes")
    return result


def _boundary(value):
    _same({key: value[key] for key in BOUNDARY}, BOUNDARY, "mapping_boundary_changed")


def validate_selection(selection_bytes, expected_selection_sha256):
    _digest(expected_selection_sha256, "mapping_selection_digest")
    _need(sha(selection_bytes) == expected_selection_sha256,
          "mapping_selection_digest_mismatch")
    selection = _json(selection_bytes, "mapping_selection_json")
    _keys(selection, {"record_type", "profile", "attempt_id", "probe", "observer",
                      "sources", "limits", *BOUNDARY}, "mapping_selection_fields")
    _need(selection["record_type"] == "required_gate_idempotence_mapping_selection_v0"
          and selection["profile"] == PROFILE, "mapping_selection_profile")
    _need(type(selection["attempt_id"]) is str and ATTEMPT_RE.fullmatch(selection["attempt_id"]),
          "mapping_attempt_id")
    _boundary(selection)
    _same(selection["limits"], LIMITS, "mapping_limits_changed")
    expected_sources = source_bindings()
    _same(selection["sources"], expected_sources, "mapping_sources_changed")
    _bound(_probe_bytes(expected_sources), selection["probe"], "mapping_probe_binding")
    observer = selection["observer"]
    _keys(observer, ("path", "sha256", "size_bytes"), "mapping_observer_selection")
    path = observer["path"]
    _need(type(path) is str and path.startswith("/") and "\x00" not in path
          and len(path) <= 4096 and all(x not in ("", ".", "..") for x in path[1:].split("/")),
          "mapping_observer_path")
    _digest(observer["sha256"], "mapping_observer_digest")
    _integer(observer["size_bytes"], "mapping_observer_size", minimum=1,
             maximum=LIMITS["observer_executable_bytes"])
    return selection


def file_limit(name):
    if name == "observer.exe.bin":
        return LIMITS["observer_executable_bytes"]
    if name in ("probe.elf", "retained.elf", "executable.elf"):
        return PAGE_BYTES
    if name in ("selection.json", "attempt_start.json"):
        return CONTROL_BYTES
    if name in ("stdout.bin", "stderr.bin"):
        return LIMITS[name.split(".")[0] + "_bytes"]
    return LIMITS["proc_file_bytes"]


def _stat_record(value):
    _keys(value, ("dev", "ino", "mode", "nlink", "size"), "mapping_object_stat")
    for key in value:
        _integer(value[key], "mapping_object_stat_integer", maximum=(1 << 64) - 1)
    _need(value["ino"] > 0 and stat.S_ISREG(value["mode"])
          and value["mode"] & 0o111 and not value["mode"] & 0o6000
          and value["nlink"] == 0 and value["size"] == PAGE_BYTES,
          "mapping_object_stat_shape")


def _object_record(value):
    if value is None:
        return
    _keys(value, ("stat", "seals"), "mapping_object_fields")
    _stat_record(value["stat"])
    _need(type(value["seals"]) is int and value["seals"] == FULL_SEALS,
          "mapping_object_seals")


def _ascii(raw, code):
    _need(type(raw) is bytes and 0 < len(raw) <= LIMITS["proc_file_bytes"] and b"\x00" not in raw,
          code)
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MappingError(code) from exc


def parse_proc_stat(raw):
    text = _ascii(raw, "mapping_proc_stat")
    _need(text.endswith("\n") and "(" in text, "mapping_proc_stat")
    left, right = text.find("("), text.rfind(")")
    _need(left > 0 and right > left and text[right + 1:right + 2] == " ",
          "mapping_proc_stat")
    pid_text = text[:left].strip()
    _need(re.fullmatch(r"[1-9][0-9]{0,9}", pid_text), "mapping_proc_stat_pid")
    fields = text[right + 2:].split()
    _need(len(fields) == 50 and fields[0] in tuple("RSDZTWtXxKPI"), "mapping_proc_stat_fields")
    _need(all(re.fullmatch(r"-?[0-9]{1,20}", item) for item in fields[1:]),
          "mapping_proc_stat_integer")
    values = [int(item) for item in fields[1:]]
    _need(all(-(1 << 63) <= item < (1 << 64) for item in values),
          "mapping_proc_stat_integer")
    result = {"pid": int(pid_text), "state": fields[0], "ppid": int(fields[1]),
              "threads": int(fields[17]), "starttime": int(fields[19])}
    _integer(result["pid"], "mapping_proc_pid", minimum=1, maximum=0x7fffffff)
    _integer(result["ppid"], "mapping_proc_ppid", maximum=0x7fffffff)
    _integer(result["threads"], "mapping_proc_threads", minimum=1)
    _integer(result["starttime"], "mapping_proc_starttime")
    return result


def _colon_fields(raw, code):
    text = _ascii(raw, code)
    _need(text.endswith("\n"), code)
    fields = {}
    for line in text.splitlines():
        _need(":" in line, code)
        key, value = line.split(":", 1)
        _need(re.fullmatch(r"[A-Za-z0-9_]+", key) and key not in fields, code)
        fields[key] = value.strip()
    return fields


def _decimal(text, code, minimum=0, maximum=MAX_INTEGER):
    _need(type(text) is str and 1 <= len(text) <= len(str(maximum))
          and re.fullmatch(r"[0-9]+", text), code)
    return _integer(int(text), code, minimum=minimum, maximum=maximum)


def parse_proc_status(raw):
    fields = _colon_fields(raw, "mapping_proc_status")
    _need({"State", "Pid", "Tgid", "PPid", "Threads", "TracerPid"} <= set(fields),
          "mapping_proc_status_fields")
    state = fields["State"].split()
    _need(state and state[0] in tuple("RSDZTWtXxKPI"), "mapping_proc_status_state")
    result = {"state": state[0], "pid": _decimal(fields["Pid"], "mapping_proc_pid", 1, 0x7fffffff),
              "tgid": _decimal(fields["Tgid"], "mapping_proc_tgid", 1, 0x7fffffff),
              "ppid": _decimal(fields["PPid"], "mapping_proc_ppid", maximum=0x7fffffff),
              "threads": _decimal(fields["Threads"], "mapping_proc_threads", 1, 0x7fffffff),
              "tracer": _decimal(fields["TracerPid"], "mapping_proc_tracer", maximum=0x7fffffff)}
    result["nspid"] = None
    if "NSpid" in fields:
        parts = fields["NSpid"].split()
        _need(parts and len(parts) <= 32, "mapping_proc_nspid")
        result["nspid"] = [_decimal(x, "mapping_proc_nspid", 1, 0x7fffffff) for x in parts]
        _need(result["nspid"][0] == result["pid"], "mapping_proc_nspid")
    return result


def parse_maps(raw):
    text = _ascii(raw, "mapping_maps")
    _need(text.endswith("\n"), "mapping_maps")
    rows = []
    last_end = 0
    pattern = re.compile(r"([0-9a-f]{1,16})-([0-9a-f]{1,16}) ([r-][w-][x-][ps]) ([0-9a-f]{1,16}) "
                         r"([0-9a-f]{1,8}):([0-9a-f]{1,8}) ([0-9]{1,20})(?:\s+(.*))?")
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        _need(match is not None and len(rows) < 128, "mapping_maps_row")
        start, end, offset = (int(match.group(x), 16) for x in (1, 2, 4))
        _need(0 <= last_end <= start < end < (1 << 64)
              and start % PAGE_BYTES == end % PAGE_BYTES == offset % PAGE_BYTES == 0,
              "mapping_maps_overlap_or_alignment")
        last_end = end
        inode = int(match.group(7))
        _need(inode < (1 << 64), "mapping_maps_inode")
        rows.append({"start": start, "end": end, "permissions": match.group(3),
                     "offset": offset, "major": int(match.group(5), 16),
                     "minor": int(match.group(6), 16), "inode": inode,
                     "path": match.group(8) or ""})
    _need(rows, "mapping_maps_empty")
    return rows


def _check_processes(capture, files):
    observer_stat = parse_proc_stat(files["observer.stat.bin"])
    observer_status = parse_proc_status(files["observer.status.bin"])
    opid, cpid = capture["observer_pid"], capture["child_pid"]
    _need(observer_stat["pid"] == observer_status["pid"] == observer_status["tgid"] == opid,
          "mapping_observer_pid_mismatch")
    _need(observer_stat["ppid"] == observer_status["ppid"], "mapping_observer_ppid_mismatch")
    _need(observer_stat["threads"] == observer_status["threads"] == 1,
          "mapping_observer_threads")
    child_stats, child_statuses = [], []
    for suffix in ("before", "after"):
        cs = parse_proc_stat(files["child.stat." + suffix + ".bin"])
        ct = parse_proc_status(files["child.status." + suffix + ".bin"])
        _need(cs["pid"] == ct["pid"] == ct["tgid"] == cpid, "mapping_child_pid_mismatch")
        _need(cs["ppid"] == ct["ppid"] == opid, "mapping_child_parent_mismatch")
        _need(cs["state"] == ct["state"] == "T", "mapping_child_not_stopped")
        _need(cs["threads"] == ct["threads"] == 1 and ct["tracer"] == 0,
              "mapping_child_threads_or_tracer")
        _need(cs["starttime"] >= observer_stat["starttime"], "mapping_child_starttime")
        child_stats.append(cs)
        child_statuses.append(ct)
    _same(child_stats[0], child_stats[1], "mapping_child_identity_changed")
    _same(child_statuses[0], child_statuses[1], "mapping_child_status_changed")
    fdinfo = _colon_fields(files["child.pidfd.info.bin"], "mapping_pidfd_info")
    _need("Pid" in fdinfo and _decimal(fdinfo["Pid"], "mapping_pidfd_pid", 1, 0x7fffffff) == cpid,
          "mapping_pidfd_pid_mismatch")
    if "NSpid" in fdinfo:
        parts = fdinfo["NSpid"].split()
        _need(parts and len(parts) <= 32, "mapping_pidfd_nspid")
        nspid = [_decimal(x, "mapping_pidfd_nspid", 1, 0x7fffffff) for x in parts]
        _need(nspid[0] == cpid, "mapping_pidfd_nspid")
        if child_statuses[0]["nspid"] is not None:
            _same(nspid, child_statuses[0]["nspid"], "mapping_pidfd_nspid_mismatch")


def _check_maps(capture, files):
    _need(files["child.maps.before.bin"] == files["child.maps.after.bin"],
          "mapping_maps_changed")
    rows = parse_maps(files["child.maps.before.bin"])
    obj = capture["objects"]["retained"]["stat"]
    # Linux dev_t encoding; replay does not consult its own host's devices.
    device = obj["dev"]
    major = ((device >> 8) & 0xfff) | ((device >> 32) & 0xfffff000)
    minor = (device & 0xff) | ((device >> 12) & 0xffffff00)
    payload, specials = [], set()
    special_permissions = {"[vvar]": "r--p", "[vvar_vclock]": "r--p", "[vdso]": "r-xp",
                           "[vsyscall]": "--xp", "[stack]": "rw-p"}
    for row in rows:
        if row["inode"]:
            _need((row["major"], row["minor"], row["inode"]) == (major, minor, obj["ino"]),
                  "mapping_foreign_backing_object")
            payload.append(row)
        else:
            name = row["path"]
            _need(name in special_permissions and name not in specials
                  and row["major"] == row["minor"] == row["offset"] == 0
                  and row["permissions"] == special_permissions[name],
                  "mapping_unrecognized_external_mapping")
            specials.add(name)
    _need(len(payload) == 1, "mapping_payload_occurrence_count")
    row = payload[0]
    _need(row["start"] == BASE_ADDRESS and row["end"] == BASE_ADDRESS + PAGE_BYTES
          and row["permissions"] == "r-xp" and row["offset"] == 0
          and row["start"] <= BASE_ADDRESS + ENTRY_OFFSET < row["end"],
          "mapping_payload_layout")
    _need({"[stack]", "[vdso]", "[vvar]"} <= specials, "mapping_kernel_mapping_roster")


def _check_host(files):
    host = _json(files["host.json"], "mapping_host_json", LIMITS["proc_file_bytes"])
    _keys(host, ("platform", "observer_namespaces", "child_namespaces"), "mapping_host_fields")
    platform = host["platform"]
    _keys(platform, ("system", "machine", "release", "version"), "mapping_platform_fields")
    _need(platform["system"] == "Linux" and platform["machine"] == "x86_64",
          "mapping_platform")
    for key in ("release", "version"):
        value = platform[key]
        _need(type(value) is str and 0 < len(value) <= 1024
              and not any(ord(c) < 32 or ord(c) == 127 for c in value), "mapping_platform_text")
    for owner in ("observer_namespaces", "child_namespaces"):
        _keys(host[owner], NAMESPACES, "mapping_namespace_roster")
        for name, value in host[owner].items():
            _need(type(value) is str and re.fullmatch(re.escape(name) + r":\[[1-9][0-9]{0,19}\]", value),
                  "mapping_namespace_identity")
            _need(int(value.split("[", 1)[1][:-1]) < (1 << 64), "mapping_namespace_identity")
    _same(host["observer_namespaces"], host["child_namespaces"], "mapping_namespace_changed")
    _need(re.fullmatch(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n",
                      files["kernel.boot_id.bin"]), "mapping_boot_id")


def verify_capture(*, selection_bytes, expected_selection_sha256, capture_bytes,
                   expected_capture_sha256, files):
    selection = validate_selection(selection_bytes, expected_selection_sha256)
    _digest(expected_capture_sha256, "mapping_capture_digest")
    _need(sha(capture_bytes) == expected_capture_sha256, "mapping_capture_digest_mismatch")
    capture = _json(capture_bytes, "mapping_capture_json")
    _keys(capture, {"record_type", "profile", "attempt_id", "selection_sha256", "status", "failure",
                    "observer_pid", "child_pid", "timing", "wait", "ownership", "objects", "files",
                    *BOUNDARY}, "mapping_capture_fields")
    _need(capture["record_type"] == "required_gate_idempotence_mapping_capture_v0"
          and capture["profile"] == PROFILE, "mapping_capture_profile")
    _boundary(capture)
    _need(capture["attempt_id"] == selection["attempt_id"]
          and capture["selection_sha256"] == expected_selection_sha256,
          "mapping_capture_selection_mismatch")
    _need(capture["status"] in ("completed", "incomplete"), "mapping_capture_status")
    complete = capture["status"] == "completed"
    _need((complete and capture["failure"] is None) or
          (not complete and type(capture["failure"]) is str and ERROR_RE.fullmatch(capture["failure"])),
          "mapping_capture_failure")
    _integer(capture["observer_pid"], "mapping_observer_pid", 1, 0x7fffffff)
    if capture["child_pid"] is not None:
        _integer(capture["child_pid"], "mapping_child_pid", 1, 0x7fffffff)
        _need(capture["child_pid"] != capture["observer_pid"], "mapping_child_equals_observer")
    _keys(capture["timing"], ("started_ns", "stopped_ns", "finished_ns"), "mapping_timing_fields")
    timing = capture["timing"]
    for key in ("started_ns", "finished_ns"):
        _integer(timing[key], "mapping_timing_integer")
    _need(timing["finished_ns"] >= timing["started_ns"], "mapping_timing_order")
    if timing["stopped_ns"] is not None:
        _integer(timing["stopped_ns"], "mapping_timing_integer")
        _need(timing["started_ns"] <= timing["stopped_ns"] <= timing["finished_ns"],
              "mapping_timing_order")
    _keys(capture["wait"], ("initial", "observation", "terminal"), "mapping_wait_fields")
    for value in capture["wait"].values():
        if value is not None:
            _integer(value, "mapping_wait_integer", maximum=0xffffffff)
    ownership = capture["ownership"]
    _keys(ownership, ("pidfd_opened", "proc_dir_pinned", "child_reaped", "resumed_after_stop"),
          "mapping_ownership_fields")
    for value in ownership.values():
        _boolean(value, "mapping_ownership_boolean")
    _need(ownership["resumed_after_stop"] is False, "mapping_probe_resumed")
    _keys(capture["objects"], ("retained", "executable"), "mapping_objects_fields")
    for value in capture["objects"].values():
        _object_record(value)
    _need(type(files) is dict and set(files) <= set(FILE_NAMES)
          and {"selection.json", "attempt_start.json"} <= set(files), "mapping_file_roster")
    _need(all(type(raw) is bytes and len(raw) <= file_limit(name) for name, raw in files.items()),
          "mapping_file_bound")
    _need(sum(len(raw) for raw in files.values()) <= LIMITS["total_capture_bytes"],
          "mapping_capture_total_bytes")
    inventory = [{"path": name, **binding(files[name])} for name in sorted(files)]
    _same(capture["files"], inventory, "mapping_file_binding_mismatch")
    _need(files["selection.json"] == selection_bytes, "mapping_preserved_selection_mismatch")
    start = _json(files["attempt_start.json"], "mapping_attempt_start")
    _same(start, {"record_type": "required_gate_idempotence_mapping_attempt_start_v0",
                  "profile": PROFILE, "attempt_id": selection["attempt_id"],
                  "selection_sha256": expected_selection_sha256,
                  "observer_pid": capture["observer_pid"], "started_ns": timing["started_ns"]},
          "mapping_attempt_start_mismatch")
    probe = _probe_bytes(selection["sources"])
    for name in ("probe.elf", "retained.elf", "executable.elf"):
        if name in files:
            _need(files[name] == probe, "mapping_fixed_probe_substitution")
    if "observer.exe.bin" in files:
        _bound(files["observer.exe.bin"], {k: selection["observer"][k] for k in ("sha256", "size_bytes")},
               "mapping_observer_executable_mismatch", LIMITS["observer_executable_bytes"])
    if complete:
        _need(set(files) == set(FILE_NAMES), "mapping_complete_file_roster")
        _need(capture["child_pid"] is not None and timing["stopped_ns"] is not None,
              "mapping_completed_process_missing")
        _need(timing["stopped_ns"] - timing["started_ns"] <= LIMITS["wall_seconds"] * 10**9
              and timing["finished_ns"] - timing["started_ns"] <=
              (LIMITS["wall_seconds"] + LIMITS["cleanup_seconds"]) * 10**9,
              "mapping_completed_deadline")
        _same(capture["wait"], {"initial": STOP_WAIT, "observation": None, "terminal": KILL_WAIT},
              "mapping_completed_wait")
        _same(ownership, {"pidfd_opened": True, "proc_dir_pinned": True,
                          "child_reaped": True, "resumed_after_stop": False},
              "mapping_completed_ownership")
        _need(all(x is not None for x in capture["objects"].values()), "mapping_completed_objects")
        _same(capture["objects"]["retained"], capture["objects"]["executable"],
              "mapping_executable_object_mismatch")
        _need(files["stdout.bin"] == files["stderr.bin"] == b"", "mapping_unexpected_output")
        _need(0 < len(files["child.exe.link.bin"]) <= 4096 and b"\x00" not in files["child.exe.link.bin"],
              "mapping_executable_link")
        _check_processes(capture, files)
        _check_maps(capture, files)
        _check_host(files)
    _same(source_bindings(), selection["sources"], "mapping_sources_changed_during_check")
    return {"record_type": "required_gate_idempotence_mapping_verification_v0", "profile": PROFILE,
            "attempt_id": selection["attempt_id"], "status": "accepted",
            "selection_sha256": expected_selection_sha256, "capture_sha256": expected_capture_sha256,
            "observation_record_verified": True, "observation_complete": complete,
            "stopped_executable_backing_relation_verified": complete,
            "sealed_executable_object_binding_verified": complete,
            "failure": capture["failure"], **BOUNDARY}


def read_capture_directory(path):
    chain = []
    try:
        fd, chain = _pin_directory(path)
        before = os.fstat(fd)
        _need(stat.S_ISDIR(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o700,
              "mapping_directory_mode")
        names = sorted(entry.name for entry in os.scandir(fd))
        _need("capture.json" in names and set(names) <= {"capture.json", *FILE_NAMES},
              "mapping_directory_roster")
        identities = {}
        capture_bytes = _read_relative(fd, "capture.json", CONTROL_BYTES, private=True,
                                       identities=identities)
        files = {name: _read_relative(fd, name, file_limit(name), private=True,
                                      identities=identities)
                 for name in names if name != "capture.json"}
        _need(sum(len(raw) for raw in files.values()) <= LIMITS["total_capture_bytes"],
              "mapping_capture_total_bytes")
        after = os.fstat(fd)
        _need(_identity(before) == _identity(after)
              and sorted(entry.name for entry in os.scandir(fd)) == names,
              "mapping_directory_changed")
        for name, expected in identities.items():
            _need(_identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == expected,
                  "mapping_file_changed_after_read")
        _check_chain(chain)
        return capture_bytes, files
    except MappingError:
        raise
    except OSError as exc:
        raise MappingError("mapping_directory_unreadable") from exc
    finally:
        _close_chain(chain)


def read_selection_file(path):
    parent, name = _file_parent(path)
    chain = []
    try:
        fd, chain = _pin_directory(parent)
        raw = _read_relative(fd, name, CONTROL_BYTES)
        _check_chain(chain)
        return raw
    except OSError as exc:
        raise MappingError("mapping_selection_unreadable") from exc
    finally:
        _close_chain(chain)


def write_new(path, raw):
    parent, name = _file_parent(path)
    chain, fd = [], None
    try:
        pfd, chain = _pin_directory(parent)
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=pfd)
        os.fchmod(fd, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            _need(written > 0, "mapping_output_write")
            view = view[written:]
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        _need(_read_fd(fd, len(raw), "mapping_output") == raw, "mapping_output_bytes")
        info = os.fstat(fd)
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600
              and _identity(info) == _identity(os.stat(name, dir_fd=pfd, follow_symlinks=False)),
              "mapping_output_identity")
        _check_chain(chain)
    except MappingError:
        raise
    except OSError as exc:
        raise MappingError("mapping_output_unavailable") from exc
    finally:
        if fd is not None:
            os.close(fd)
        _close_chain(chain)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--capture-directory", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        selected = read_selection_file(args.selection)
        capture, files = read_capture_directory(args.capture_directory)
        result = verify_capture(selection_bytes=selected, expected_selection_sha256=args.selection_sha256,
                                capture_bytes=capture, expected_capture_sha256=args.capture_sha256,
                                files=files)
        raw = canonical(result)
        if args.output:
            write_new(args.output, raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (MappingError, OSError) as exc:
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
