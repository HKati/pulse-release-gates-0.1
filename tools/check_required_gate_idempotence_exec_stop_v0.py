"""Reconstruct one original-launcher kernel exec stop without importing its collector.

make_request is a byte-derivation API, not original-evidence admission. Its caller
must freshly reconstruct the complete distribution/launch-host chain first.
The public preparation adapter performs that admission for prepare and check.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_mapping_observation_v0 as old

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_original_launcher_exec_stop_v0"
BOUNDARY = dict(old.BOUNDARY)
NARROW_FLAGS = ("kernel_exec_checkpoint_observed", "launcher_image_binding_verified",
                "interpreter_image_binding_verified", "selected_exec_memory_ranges_observed",
                "selected_exec_rx_ranges_match_original", "owned_exec_stop_cleanup_verified")
LIMITS = dict(old.LIMITS)
CONTROL_BYTES = old.CONTROL_BYTES
STOP_WAIT, EXEC_WAIT, KILL_WAIT = 4991, 263551, 9
PTRACE_OPTIONS = 0x100010
PAGE_BYTES = 4096
INTERPRETER_PATH = "/lib64/ld-linux-x86-64.so.2"
ROLE_PATHS = {"launcher": "native/bwrap", "loader": "native/ld-linux-x86-64.so.2"}
SOURCE_PATHS = tuple(sorted((*old.SOURCE_PATHS,
    "schemas/required_gate_idempotence_exec_stop_v0.schema.json",
    "tools/check_required_gate_idempotence_exec_stop_v0.py",
    "tools/required_gate_idempotence_exec_stop_v0.py",
    "tools/required_gate_idempotence_launch_host_v0.py",
    "tools/required_gate_idempotence_launcher_distribution_v0.py",
    "tools/prepare_required_gate_idempotence_exec_stop_v0.py")))
NATIVE = {
    "native/bwrap": {"size_bytes": 80248, "sha256": "573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f"},
    "native/ld-linux-x86-64.so.2": {"size_bytes": 225672, "sha256": "c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307"},
    "native/libc.so.6": {"size_bytes": 1995216, "sha256": "9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92"},
    "native/libcap.so.2": {"size_bytes": 47288, "sha256": "41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b"},
    "native/libpcre2-8.so.0": {"size_bytes": 711216, "sha256": "92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3"},
    "native/libselinux.so.1": {"size_bytes": 202984, "sha256": "5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c"},
}
ORIGINAL_BINDINGS = {
    "launch_host_plan": {"size_bytes": 10792, "sha256": "314acd23ea1ba43dc3ccf337d0171473c43422c7c026d9548d104d88c968bcf5"},
    "launch_host_report": {"size_bytes": 4284, "sha256": "720a2cf4ade0e2b575440e4b3e02bee8df9ef754d2f120ac4632fa9fc1ce9806"},
    "distribution_record": {"size_bytes": 6142, "sha256": "1f0259701194b485fdb15a442ce1a3e72c9d60d136d6b308468b40a4d1b85060"},
    "distribution_report": {"size_bytes": 3780, "sha256": "a0d7cf825dce1c8a3b09a2306f155f24bdcabc4a16cb90215f6d4e04925f4f36"},
}


def _segment(index, offset, vaddr, filesz, memsz, flags):
    return dict(index=index, offset=offset, vaddr=vaddr, filesz=filesz,
                memsz=memsz, flags=flags, align=PAGE_BYTES)


LAYOUTS = {
    "launcher": {"entry": 21904, "phoff": 64, "phentsize": 56, "phnum": 14,
        "interpreter": INTERPRETER_PATH, "segments": [
            _segment(2, 0, 0, 9616, 9616, 4),
            _segment(3, 12288, 12288, 39761, 39761, 5),
            _segment(4, 53248, 53248, 21400, 21400, 4),
            _segment(5, 76016, 80112, 2045, 2312, 6)]},
    "loader": {"entry": 119488, "phoff": 64, "phentsize": 56, "phnum": 9,
        "interpreter": None, "segments": [
            _segment(0, 0, 0, 3280, 3280, 4),
            _segment(1, 4096, 4096, 160721, 160721, 5),
            _segment(2, 167936, 167936, 44336, 44336, 4),
            _segment(3, 213568, 213568, 10508, 13224, 6)]},
}
RX_BINDINGS = {
    "launcher": {"size_bytes": 39761, "sha256": "023deed07f1021011871b69ab9836728306e2c00413623eec1ddce4ae1cee036"},
    "loader": {"size_bytes": 160721, "sha256": "d37e7ccdc896ff037553cc924c788f81b8dcb0fa6a69a5717a03c87ad67dee21"},
}
EDGE_TUPLES = (
    ("bwrap", "interpreter", INTERPRETER_PATH, "ld-linux-x86-64.so.2"),
    ("bwrap", "needed", "libc.so.6", "libc.so.6"),
    ("bwrap", "needed", "libcap.so.2", "libcap.so.2"),
    ("bwrap", "needed", "libselinux.so.1", "libselinux.so.1"),
    ("libc.so.6", "interpreter", INTERPRETER_PATH, "ld-linux-x86-64.so.2"),
    ("libc.so.6", "needed", "ld-linux-x86-64.so.2", "ld-linux-x86-64.so.2"),
    ("libcap.so.2", "interpreter", INTERPRETER_PATH, "ld-linux-x86-64.so.2"),
    ("libcap.so.2", "needed", "libc.so.6", "libc.so.6"),
    ("libpcre2-8.so.0", "needed", "libc.so.6", "libc.so.6"),
    ("libselinux.so.1", "needed", "ld-linux-x86-64.so.2", "ld-linux-x86-64.so.2"),
    ("libselinux.so.1", "needed", "libc.so.6", "libc.so.6"),
    ("libselinux.so.1", "needed", "libpcre2-8.so.0", "libpcre2-8.so.0"),
)
FILE_NAMES = tuple(sorted((
    "request.json", "attempt_start.json", "launcher.elf", "retained.elf", "executable.elf",
    "loader.before.elf", "loader.after.elf", "observer.exe.bin", "observer.stat.bin",
    "observer.status.bin", "child.stat.setup.bin", "child.status.setup.bin",
    "child.stat.before.bin", "child.stat.after.bin", "child.status.before.bin",
    "child.status.after.bin", "child.maps.before.bin", "child.maps.after.bin",
    "child.pidfd.info.bin", "child.exe.link.bin", "regs.before.bin", "regs.after.bin",
    "auxv.before.bin", "auxv.after.bin", "launcher.rx.sample0.bin", "launcher.rx.sample1.bin",
    "loader.rx.sample0.bin", "loader.rx.sample1.bin", "host.json", "kernel.boot_id.bin",
    "stdout.bin", "stderr.bin")))

ExecStopError = old.MappingError
canonical, sha, binding = old.canonical, old.sha, old.binding
_need, _same, _keys = old._need, old._same, old._keys
_json, _integer, _bound = old._json, old._integer, old._bound
read_request_file, write_new = old.read_selection_file, old.write_new


def source_bindings():
    return [{"path": path, **binding(old._source_bytes(path))} for path in SOURCE_PATHS]


def elf_layout(raw):
    _need(type(raw) is bytes and 64 <= len(raw) <= 16 * 1024 * 1024, "exec_stop_elf_size")
    h = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    _need(h[0][:7] == b"\x7fELF\x02\x01\x01" and h[1:4] == (3, 62, 1)
          and h[8] == 64 and h[9] == 56 and 1 <= h[10] <= 64
          and h[5] + h[9] * h[10] <= len(raw), "exec_stop_elf_header")
    segments, interpreter = [], None
    for index in range(h[10]):
        kind, flags, offset, vaddr, _physical, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", raw, h[5] + index * h[9])
        _need(offset + filesz <= len(raw), "exec_stop_elf_segment_bounds")
        if kind == 3:
            _need(interpreter is None and 1 < filesz <= 4096 and raw[offset + filesz - 1] == 0,
                  "exec_stop_elf_interpreter")
            try:
                interpreter = raw[offset:offset + filesz - 1].decode("ascii")
            except UnicodeDecodeError as exc:
                raise ExecStopError("exec_stop_elf_interpreter") from exc
            _need("\0" not in interpreter, "exec_stop_elf_interpreter")
        if kind == 1:
            _need(0 < filesz <= memsz and vaddr + memsz < (1 << 63)
                  and flags in (4, 5, 6) and align == PAGE_BYTES
                  and offset % PAGE_BYTES == vaddr % PAGE_BYTES, "exec_stop_elf_load")
            segments.append(_segment(index, offset, vaddr, filesz, memsz, flags))
    return dict(entry=h[4], phoff=h[5], phentsize=h[9], phnum=h[10],
                interpreter=interpreter, segments=segments)


def _relationships():
    return [{"consumer": "native/" + c, "kind": k, "name": n, "provider": "native/" + p,
             "checkpoint_status": "required_at_cp0" if c == "bwrap" and k == "interpreter"
             else "not_observed_at_cp0"} for c, k, n, p in EDGE_TUPLES]


def _memory_obligations():
    rows = []
    for role in ROLE_PATHS:
        selected = [s for s in LAYOUTS[role]["segments"] if s["flags"] == 5]
        _need(len(selected) == 1, "exec_stop_rx_segment_count")
        seg = selected[0]
        for sample in (0, 1):
            rows.append({"id": "cp0." + role + ".rx." + str(sample), "object": role,
                         "segment_index": seg["index"], "sample_index": sample,
                         "file": role + ".rx.sample" + str(sample) + ".bin",
                         "file_offset": seg["offset"], "vaddr": seg["vaddr"], **RX_BINDINGS[role]})
    return rows


def _observer(value):
    _keys(value, ("path", "sha256", "size_bytes"), "exec_stop_observer_fields")
    path = value["path"]
    _need(type(path) is str and path.startswith("/") and len(path) <= 4096 and "\0" not in path
          and all(x not in ("", ".", "..") for x in path[1:].split("/")), "exec_stop_observer_path")
    old._digest(value["sha256"], "exec_stop_observer_digest")
    _integer(value["size_bytes"], "exec_stop_observer_size", 1, LIMITS["observer_executable_bytes"])


def _request(attempt_id, observer):
    return {"record_type": "required_gate_idempotence_exec_stop_request_v0", "profile": PROFILE,
            "attempt_id": attempt_id, "observer": observer, "originals": ORIGINAL_BINDINGS,
            "native_files": [{"path": path, **NATIVE[path], "checkpoint_status":
                "required_at_cp0" if path in ROLE_PATHS.values() else "not_observed_at_cp0"}
                for path in sorted(NATIVE)],
            "elf": LAYOUTS, "native_relationships": _relationships(),
            "memory_obligations": _memory_obligations(),
            "event": {"kind": "PTRACE_EVENT_EXEC", "post_exec_resumes": 0},
            "execution": {"argv": ["bubblewrap"], "environment": {"LC_ALL": "C", "TZ": "UTC"}, "cwd": "/"},
            "sources": source_bindings(), "limits": LIMITS, **BOUNDARY}


def make_request(*, attempt_id, launch_host_plan_bytes, launch_host_report_bytes,
                 distribution_record_bytes, distribution_report_bytes, native_files,
                 observer_executable_bytes=None, observer_executable_path=None,
                 observer_descriptor=None):
    """Derive after caller's fresh original-chain admission; never execute payloads."""
    for name, raw in (("launch_host_plan", launch_host_plan_bytes),
                      ("launch_host_report", launch_host_report_bytes),
                      ("distribution_record", distribution_record_bytes),
                      ("distribution_report", distribution_report_bytes)):
        _bound(raw, ORIGINAL_BINDINGS[name], "exec_stop_original_" + name)
    _keys(native_files, NATIVE, "exec_stop_native_roster")
    for path, raw in native_files.items():
        _bound(raw, NATIVE[path], "exec_stop_native_binding", 16 * 1024 * 1024)
    for role, path in ROLE_PATHS.items():
        _same(elf_layout(native_files[path]), LAYOUTS[role], "exec_stop_original_elf_layout")
        seg = next(s for s in LAYOUTS[role]["segments"] if s["flags"] == 5)
        _bound(native_files[path][seg["offset"]:seg["offset"] + seg["filesz"]],
               RX_BINDINGS[role], "exec_stop_original_rx_binding")
    if observer_descriptor is None:
        _need(type(observer_executable_bytes) is bytes, "exec_stop_observer_bytes")
        observer = {"path": observer_executable_path, **binding(observer_executable_bytes)}
    else:
        _need(observer_executable_bytes is None and observer_executable_path is None,
              "exec_stop_observer_ambiguous")
        observer = dict(observer_descriptor)
    result = _request(attempt_id, observer)
    return validate_request(canonical(result), sha(canonical(result)))


def validate_request(request_bytes, expected_request_sha256):
    old._digest(expected_request_sha256, "exec_stop_request_digest")
    _need(sha(request_bytes) == expected_request_sha256, "exec_stop_request_digest_mismatch")
    request = _json(request_bytes, "exec_stop_request_json")
    _need(type(request) is dict and "attempt_id" in request and "observer" in request,
          "exec_stop_request_fields")
    _need(type(request["attempt_id"]) is str and old.ATTEMPT_RE.fullmatch(request["attempt_id"]),
          "exec_stop_attempt_id")
    _observer(request["observer"])
    _same(request, _request(request["attempt_id"], request["observer"]), "exec_stop_request_contract")
    return request


def file_limit(name):
    if name == "observer.exe.bin":
        return LIMITS["observer_executable_bytes"]
    if name in ("launcher.elf", "retained.elf", "executable.elf"):
        return NATIVE[ROLE_PATHS["launcher"]]["size_bytes"]
    if name in ("loader.before.elf", "loader.after.elf"):
        return 16 * 1024 * 1024
    if ".rx.sample" in name:
        return RX_BINDINGS[name.split(".")[0]]["size_bytes"]
    if name in ("request.json", "attempt_start.json"):
        return CONTROL_BYTES
    if name in ("stdout.bin", "stderr.bin"):
        return LIMITS[name.split(".")[0] + "_bytes"]
    return LIMITS["proc_file_bytes"]


def _object(value, role, *, exact=True):
    if value is None:
        return
    _keys(value, ("stat", "seals"), "exec_stop_object_fields")
    info = value["stat"]
    _keys(info, ("dev", "ino", "mode", "nlink", "size"), "exec_stop_stat_fields")
    for number in info.values():
        _integer(number, "exec_stop_stat_integer", maximum=(1 << 64) - 1)
    _integer(info["mode"], "exec_stop_stat_mode", maximum=0xffff)
    if value["seals"] is not None:
        _integer(value["seals"], "exec_stop_seals_integer", maximum=0xffffffff)
    if not exact:
        return
    if role == "memory":
        _need(info["ino"] > 0 and stat.S_ISREG(info["mode"]) and info["nlink"] == 1
              and not info["mode"] & 0o111 and info["size"] == 0
              and value["seals"] is None, "exec_stop_memory_object")
        return
    _need(info["ino"] > 0 and stat.S_ISREG(info["mode"]) and info["mode"] & 0o111
          and not info["mode"] & 0o6000 and 0 < info["size"] <= 16 * 1024 * 1024,
          "exec_stop_object_shape")
    if exact or role == "launcher":
        _need(info["size"] == NATIVE[ROLE_PATHS[role]]["size_bytes"], "exec_stop_object_size")
    if role == "launcher":
        _need(info["nlink"] == 0 and type(value["seals"]) is int and value["seals"] == 15,
              "exec_stop_launcher_seals")
    else:
        _need(info["nlink"] >= 1 and value["seals"] is None, "exec_stop_loader_object")


def _auxv(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= LIMITS["proc_file_bytes"]
          and len(raw) % 16 == 0, "exec_stop_auxv_size")
    rows = list(struct.iter_unpack("<QQ", raw))
    _need(rows[-1] == (0, 0) and all(k > 0 for k, _v in rows[:-1]), "exec_stop_auxv_terminator")
    result = dict(rows[:-1])
    _need(len(result) == len(rows) - 1 and {3, 4, 5, 6, 7, 9} <= set(result),
          "exec_stop_auxv_fields")
    return result


def _dev(info):
    device = info["dev"]
    return (((device >> 8) & 0xfff) | ((device >> 32) & 0xfffff000),
            (device & 0xff) | ((device >> 12) & 0xffffff00), info["ino"])


def derive_spans(request, capture, files):
    """Validate cp0 address evidence before the collector reads selected memory."""
    aux = _auxv(files["auxv.before.bin"])
    regs = files["regs.before.bin"]
    _need(len(regs) == 216, "exec_stop_register_size")
    rip = struct.unpack_from("<Q", regs, 16 * 8)[0]
    biases = {"launcher": aux[9] - request["elf"]["launcher"]["entry"], "loader": aux[7]}
    for value in biases.values():
        _need(0 < value < (1 << 47) and value % PAGE_BYTES == 0, "exec_stop_load_bias")
    launch = request["elf"]["launcher"]
    _need(aux[6] == PAGE_BYTES and aux[3] == biases["launcher"] + launch["phoff"]
          and aux[4] == launch["phentsize"] and aux[5] == launch["phnum"], "exec_stop_auxv_layout")
    _need(rip == biases["loader"] + request["elf"]["loader"]["entry"], "exec_stop_interpreter_entry")
    expected = {}
    for role in ROLE_PATHS:
        for seg in request["elf"][role]["segments"]:
            start = biases[role] + seg["vaddr"] // PAGE_BYTES * PAGE_BYTES
            file_end = (biases[role] + seg["vaddr"] + seg["filesz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
            end = (biases[role] + seg["vaddr"] + seg["memsz"] + PAGE_BYTES - 1) // PAGE_BYTES * PAGE_BYTES
            perms = "r" + ("w" if seg["flags"] & 2 else "-") + ("x" if seg["flags"] & 1 else "-") + "p"
            for page in range(start, end, PAGE_BYTES):
                _need(page not in expected, "exec_stop_segment_overlap")
                expected[page] = (role, perms, seg["offset"] // PAGE_BYTES * PAGE_BYTES + page - start,
                                  page >= file_end)
    objects = {"launcher": capture["objects"]["executable"], "loader": capture["objects"]["loader_before"]}
    for role, value in objects.items():
        _need(value is not None, "exec_stop_checkpoint_object_missing")
        _object(value, role)
    _need(_dev(objects["launcher"]["stat"]) != _dev(objects["loader"]["stat"]),
          "exec_stop_object_alias")
    seen, specials = set(), set()
    allowed = {"[vvar]": "r--p", "[vvar_vclock]": "r--p", "[vdso]": "r-xp",
               "[vsyscall]": "--xp", "[stack]": "rw-p"}
    for row in old.parse_maps(files["child.maps.before.bin"]):
        if row["inode"] == 0 and row["path"] in allowed:
            _need(row["path"] not in specials and row["permissions"] == allowed[row["path"]]
                  and row["major"] == row["minor"] == row["offset"] == 0,
                  "exec_stop_kernel_mapping")
            _need(not any(row["start"] <= page < row["end"] for page in expected),
                  "exec_stop_kernel_mapping_overlap")
            specials.add(row["path"])
            continue
        _need((row["end"] - row["start"]) // PAGE_BYTES <= len(expected), "exec_stop_mapping_range")
        for page in range(row["start"], row["end"], PAGE_BYTES):
            _need(page in expected and page not in seen, "exec_stop_mapping_extra_or_duplicate")
            role, perms, offset, anonymous = expected[page]
            _need(row["permissions"] == perms, "exec_stop_mapping_permissions")
            if anonymous:
                _need(row["inode"] == row["major"] == row["minor"] == row["offset"] == 0
                      and row["path"] == "", "exec_stop_bss_mapping")
            else:
                _need((row["major"], row["minor"], row["inode"]) == _dev(objects[role]["stat"])
                      and row["offset"] + page - row["start"] == offset, "exec_stop_mapping_backing")
            seen.add(page)
    _need(seen == set(expected) and {"[stack]", "[vdso]", "[vvar]"} <= specials,
          "exec_stop_mapping_coverage")
    return {role: {"address": biases[role] + next(s["vaddr"] for s in request["elf"][role]["segments"]
                    if s["flags"] == 5), "size": RX_BINDINGS[role]["size_bytes"]} for role in ROLE_PATHS}


def _processes(capture, files):
    opid, cpid = capture["observer_pid"], capture["child_pid"]
    observer = old.parse_proc_stat(files["observer.stat.bin"])
    status = old.parse_proc_status(files["observer.status.bin"])
    _need(observer["pid"] == status["pid"] == status["tgid"] == opid
          and observer["threads"] == status["threads"] == 1
          and observer["ppid"] == status["ppid"] and status["tracer"] == 0,
          "exec_stop_observer_identity")
    identities = []
    for suffix in ("setup", "before", "after"):
        ps = old.parse_proc_stat(files["child.stat." + suffix + ".bin"])
        pt = old.parse_proc_status(files["child.status." + suffix + ".bin"])
        _need(ps["pid"] == pt["pid"] == pt["tgid"] == cpid and ps["ppid"] == pt["ppid"] == opid
              and ps["threads"] == pt["threads"] == 1 and ps["state"] == pt["state"] == "t"
              and pt["tracer"] == opid and ps["starttime"] >= observer["starttime"],
              "exec_stop_child_identity")
        identities.append(ps)
    _same(identities[0], identities[1], "exec_stop_child_changed")
    _same(identities[1], identities[2], "exec_stop_child_changed")
    _same(old.parse_proc_status(files["child.status.before.bin"]),
          old.parse_proc_status(files["child.status.after.bin"]), "exec_stop_child_status_changed")
    fdinfo = old._colon_fields(files["child.pidfd.info.bin"], "exec_stop_pidfd_info")
    _need("Pid" in fdinfo and old._decimal(fdinfo["Pid"], "exec_stop_pidfd_pid", 1) == cpid,
          "exec_stop_pidfd_identity")


def verify_capture(*, request_bytes, expected_request_sha256, capture_bytes,
                   expected_capture_sha256, files):
    request = validate_request(request_bytes, expected_request_sha256)
    old._digest(expected_capture_sha256, "exec_stop_capture_digest")
    _need(sha(capture_bytes) == expected_capture_sha256, "exec_stop_capture_digest_mismatch")
    capture = _json(capture_bytes, "exec_stop_capture_json")
    _keys(capture, {"record_type", "profile", "attempt_id", "request_sha256", "status", "failure",
          "observer_pid", "child_pid", "timing", "wait", "ownership", "objects", "files", *BOUNDARY},
          "exec_stop_capture_fields")
    _need(capture["record_type"] == "required_gate_idempotence_exec_stop_capture_v0"
          and capture["profile"] == PROFILE and capture["attempt_id"] == request["attempt_id"]
          and capture["request_sha256"] == expected_request_sha256, "exec_stop_capture_request")
    _same({k: capture[k] for k in BOUNDARY}, BOUNDARY, "exec_stop_boundary")
    _need(capture["status"] in ("completed", "incomplete"), "exec_stop_capture_status")
    complete = capture["status"] == "completed"
    _need((complete and capture["failure"] is None) or (not complete
          and type(capture["failure"]) is str and old.ERROR_RE.fullmatch(capture["failure"])),
          "exec_stop_capture_failure")
    _integer(capture["observer_pid"], "exec_stop_observer_pid", 1, 0x7fffffff)
    if capture["child_pid"] is not None:
        _integer(capture["child_pid"], "exec_stop_child_pid", 1, 0x7fffffff)
        _need(capture["child_pid"] != capture["observer_pid"], "exec_stop_child_equals_observer")
    timing = capture["timing"]
    _keys(timing, ("started_ns", "stopped_ns", "finished_ns"), "exec_stop_timing_fields")
    for key in ("started_ns", "finished_ns"):
        _integer(timing[key], "exec_stop_timing_integer")
    _need(timing["started_ns"] <= timing["finished_ns"], "exec_stop_timing_order")
    if timing["stopped_ns"] is not None:
        _integer(timing["stopped_ns"], "exec_stop_timing_integer")
        _need(timing["started_ns"] <= timing["stopped_ns"] <= timing["finished_ns"], "exec_stop_timing_order")
    _keys(capture["wait"], ("setup", "exec", "terminal", "event_msg"), "exec_stop_wait_fields")
    for value in capture["wait"].values():
        if value is not None:
            _integer(value, "exec_stop_wait_integer", maximum=0xffffffff)
    ownership = capture["ownership"]
    _keys(ownership, ("pidfd_opened", "proc_dir_pinned", "child_reaped", "post_exec_resumes",
                     "detached", "pre_exec_resumes", "ptrace_options", "kill_sent"), "exec_stop_ownership_fields")
    for key in ("pidfd_opened", "proc_dir_pinned", "child_reaped", "detached", "kill_sent"):
        old._boolean(ownership[key], "exec_stop_ownership_boolean")
    _integer(ownership["pre_exec_resumes"], "exec_stop_resume_integer", maximum=1)
    _integer(ownership["post_exec_resumes"], "exec_stop_resume_integer", maximum=0)
    _integer(ownership["ptrace_options"], "exec_stop_options_integer", maximum=PTRACE_OPTIONS)
    _need(ownership["ptrace_options"] in (0, PTRACE_OPTIONS) and not ownership["detached"],
          "exec_stop_forbidden_transition")
    _keys(capture["objects"], ("retained", "executable", "loader_before", "loader_after", "memory"), "exec_stop_objects_fields")
    for name, value in capture["objects"].items():
        role = "memory" if name == "memory" else "loader" if name.startswith("loader") else "launcher"
        _object(value, role, exact=complete)
    _need(type(files) is dict and {"request.json", "attempt_start.json"} <= set(files) <= set(FILE_NAMES),
          "exec_stop_file_roster")
    _need(all(type(raw) is bytes and len(raw) <= file_limit(name) for name, raw in files.items())
          and sum(map(len, files.values())) <= LIMITS["total_capture_bytes"], "exec_stop_file_bound")
    _same(capture["files"], [{"path": name, **binding(raw)} for name, raw in sorted(files.items())],
          "exec_stop_file_bindings")
    _need(files["request.json"] == request_bytes, "exec_stop_preserved_request")
    _same(_json(files["attempt_start.json"], "exec_stop_start_json"),
          {"record_type": "required_gate_idempotence_exec_stop_attempt_start_v0", "profile": PROFILE,
           "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
           "observer_pid": capture["observer_pid"], "started_ns": timing["started_ns"]}, "exec_stop_start_binding")
    for name in ("launcher.elf", "retained.elf", "executable.elf", "loader.before.elf", "loader.after.elf"):
        if name in files:
            role = "loader" if name.startswith("loader") else "launcher"
            if complete:
                _bound(files[name], NATIVE[ROLE_PATHS[role]], "exec_stop_original_object_binding", 16 * 1024 * 1024)
                _same(elf_layout(files[name]), request["elf"][role], "exec_stop_observed_elf_layout")
    if complete and "observer.exe.bin" in files:
        _bound(files["observer.exe.bin"], {k: request["observer"][k] for k in ("sha256", "size_bytes")},
               "exec_stop_observer_binding", LIMITS["observer_executable_bytes"])
    relations = []
    if complete:
        _need(set(files) == set(FILE_NAMES), "exec_stop_complete_roster")
        _need(capture["child_pid"] is not None and timing["stopped_ns"] is not None,
              "exec_stop_complete_process")
        _need(timing["stopped_ns"] - timing["started_ns"] <= LIMITS["wall_seconds"] * 10**9
              and timing["finished_ns"] - timing["started_ns"] <=
              (LIMITS["wall_seconds"] + LIMITS["cleanup_seconds"]) * 10**9, "exec_stop_deadline")
        _same(capture["wait"], {"setup": STOP_WAIT, "exec": EXEC_WAIT, "terminal": KILL_WAIT,
                                "event_msg": capture["child_pid"]}, "exec_stop_completed_wait")
        _same(ownership, {"pidfd_opened": True, "proc_dir_pinned": True, "child_reaped": True,
              "post_exec_resumes": 0, "detached": False, "pre_exec_resumes": 1,
              "ptrace_options": PTRACE_OPTIONS, "kill_sent": True}, "exec_stop_completed_ownership")
        _need(all(x is not None for x in capture["objects"].values()), "exec_stop_complete_objects")
        _same(capture["objects"]["retained"], capture["objects"]["executable"], "exec_stop_launcher_object_changed")
        _same(capture["objects"]["loader_before"], capture["objects"]["loader_after"], "exec_stop_loader_object_changed")
        _need(files["stdout.bin"] == files["stderr.bin"] == b"", "exec_stop_unexpected_output")
        _need(0 < len(files["child.exe.link.bin"]) <= 4096 and b"\0" not in files["child.exe.link.bin"],
              "exec_stop_executable_link")
        for stem in ("child.maps", "regs", "auxv"):
            _need(files[stem + ".before.bin"] == files[stem + ".after.bin"], "exec_stop_checkpoint_changed")
        _processes(capture, files)
        old._check_host(files)
        spans = derive_spans(request, capture, files)
        for row in request["memory_obligations"]:
            _bound(files[row["file"]], {k: row[k] for k in ("sha256", "size_bytes")}, "exec_stop_memory_sample")
            relations.append({"id": row["id"], "object": row["object"], "segment_index": row["segment_index"],
                "sample_index": row["sample_index"], "address": spans[row["object"]]["address"],
                "file_offset": row["file_offset"], **binding(files[row["file"]]), "matches_original": True})
    _same(source_bindings(), request["sources"], "exec_stop_sources_changed")
    return {"record_type": "required_gate_idempotence_exec_stop_verification_v0", "profile": PROFILE,
            "attempt_id": request["attempt_id"], "status": "accepted", "request_sha256": expected_request_sha256,
            "capture_sha256": expected_capture_sha256, "observation_record_verified": True,
            "observation_complete": complete, "kernel_exec_checkpoint_observed": complete,
            "launcher_image_binding_verified": complete, "interpreter_image_binding_verified": complete,
            "selected_exec_memory_ranges_observed": complete, "selected_exec_rx_ranges_match_original": complete,
            "owned_exec_stop_cleanup_verified": complete, "memory_relations": relations,
            "failure": capture["failure"], **BOUNDARY}


def read_capture_directory(path):
    chain = []
    try:
        fd, chain = old._pin_directory(path)
        before = os.fstat(fd)
        _need(stat.S_IMODE(before.st_mode) == 0o700, "exec_stop_directory_mode")
        names = sorted(entry.name for entry in os.scandir(fd))
        _need("capture.json" in names and set(names) <= {"capture.json", *FILE_NAMES}, "exec_stop_directory_roster")
        identities = {}
        raw = old._read_relative(fd, "capture.json", CONTROL_BYTES, private=True, identities=identities)
        files = {name: old._read_relative(fd, name, file_limit(name), private=True, identities=identities)
                 for name in names if name != "capture.json"}
        _need(sum(map(len, files.values())) <= LIMITS["total_capture_bytes"], "exec_stop_capture_size")
        _need(old._identity(before) == old._identity(os.fstat(fd))
              and sorted(entry.name for entry in os.scandir(fd)) == names, "exec_stop_directory_changed")
        for name, expected in identities.items():
            _need(old._identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == expected,
                  "exec_stop_file_changed_after_read")
        old._check_chain(chain)
        return raw, files
    except OSError as exc:
        raise ExecStopError("exec_stop_directory_unreadable") from exc
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
        request = read_request_file(args.request)
        capture, files = read_capture_directory(args.capture_directory)
        result = verify_capture(request_bytes=request, expected_request_sha256=args.request_sha256,
                                capture_bytes=capture, expected_capture_sha256=args.capture_sha256,
                                files=files)
        raw = canonical(result)
        if args.output:
            write_new(args.output, raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (ExecStopError, OSError) as exc:
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
