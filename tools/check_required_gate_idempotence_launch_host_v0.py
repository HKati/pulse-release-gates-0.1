#!/usr/bin/env python3
"""Check launch-host byte relationships without launching selected code.

This checker re-admits the original containment and entry-build inputs. Package
membership and a closed static native graph do not authenticate origin, observe
the host loader's choices, qualify a host or authorize selected execution.
Selected-source readmission retains the existing local, transport-disabled Git
blob checks. No launcher, entry, selected runtime or package content executes.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_containment_v0 as containment
import check_required_gate_idempotence_entry_build_v0 as entry_build
import required_gate_idempotence_elf_v0 as elf
import required_gate_idempotence_launcher_package_v0 as package_reader

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_launch_host_v0.schema.json"
SCHEMA_SHA256 = "89a322039339d90cec438fb9e553e61d04a94b1a49fcce46cd4fde7c9b7dc9be"
PROFILE = "linux_x86_64_bubblewrap_launch_host_v0"
CONTROL_LIMIT = 4 * 1024 * 1024
HOST_LIMIT = 256 * 1024
HOST_FILE_LIMIT = 16384
NATIVE_FILE_LIMIT = 16 * 1024 * 1024
NATIVE_TOTAL_LIMIT = 128 * 1024 * 1024
MAX_NATIVE_FILES = 64
MAX_NATIVE_BINDINGS = 4096
BOUNDARY = {**entry_build.BOUNDARY, "launcher_executed": False,
            "launcher_origin_authenticated": False, "host_observation_authenticated": False}
HOST_PATHS = (
    "/proc/self/status", "/proc/sys/user/max_user_namespaces",
    "/proc/sys/kernel/unprivileged_userns_clone",
    "/proc/sys/kernel/apparmor_restrict_unprivileged_userns",
    "/proc/sys/vm/memfd_noexec", "/etc/ld.so.preload",
)
NAMESPACE_NAMES = ("user", "mnt", "ipc", "pid", "net", "uts", "cgroup")
PENDING_OBLIGATIONS = (
    "authenticated_launcher_package_and_build_origin",
    "same_attempt_host_and_actual_mapped_native_identity",
    "strict_namespaces_and_read_only_execution_view",
    "intended_syscall_filter_and_denied_operations",
    "descriptor_closure_and_resource_limits",
    "bounded_stdout_stderr_and_failure_preservation",
    "reviewed_selected_bootstrap_integration",
    "separate_execution_authorization",
)
HASH = re.compile(r"[0-9a-f]{64}\Z")
PART = re.compile(r"[A-Za-z0-9_.+\-]+\Z")
PROC_FIELDS = ("NoNewPrivs", "Seccomp", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")


class HostError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise HostError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def binding(raw):
    need(type(raw) is bytes, "launch_host_bytes_required")
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= CONTROL_LIMIT,
         "launch_host_control_size")

    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "launch_host_duplicate_key")
            result[key] = value
        return result

    def invalid(_value):
        raise HostError("launch_host_json_invalid")

    def integer(value):
        need(re.fullmatch(r"-?(?:0|[1-9][0-9]{0,18})", value) is not None,
             "launch_host_json_integer_range")
        result = int(value)
        need(-(2**63) <= result < 2**63, "launch_host_json_integer_range")
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=invalid, parse_float=invalid, parse_int=integer)
    except HostError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise HostError("launch_host_json_invalid") from exc
    need(type(value) is dict, "launch_host_object_required")
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(depth <= 32 and count <= 100000, "launch_host_json_complexity")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        else:
            need(item is None or type(item) in (str, bool, int), "launch_host_json_value_type")
            if type(item) is int:
                need(-(2**63) <= item < 2**63, "launch_host_json_integer_range")
    return value


def _hash(value):
    return type(value) is str and HASH.fullmatch(value) is not None


def _path(value, *, absolute=False):
    if type(value) is not str or not 0 < len(value) <= 500 or value.startswith("/") != absolute:
        return False
    pieces = value[1:].split("/") if absolute else value.split("/")
    return all(part not in {"", ".", ".."} and PART.fullmatch(part) is not None for part in pieces)


def _boundary(value):
    for key, expected in BOUNDARY.items():
        need(key in value and type(value[key]) is type(expected) and value[key] == expected,
             "launch_host_authority_boundary_mismatch")


def _schema(value, definition):
    safe = containment.bootstrap.runtime.observation.safe
    try:
        raw = safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(raw) == SCHEMA_SHA256, "launch_host_schema_source_mismatch")
        safe._validate_schema(value, parse(raw), "launch_host_" + definition + "_schema_invalid", definition)
    except safe.ContractError as exc:
        raise HostError(exc.code) from exc


def validate_selection(selection_bytes, expected_sha256):
    need(_hash(expected_sha256) and type(selection_bytes) is bytes
         and sha(selection_bytes) == expected_sha256, "launch_host_selection_digest_mismatch")
    selection = parse(selection_bytes)
    _schema(selection, "selection")
    _boundary(selection)
    files = selection["native_files"]
    paths = [row["path"] for row in files]
    host_paths = [row["host_path"] for row in files]
    need(len(paths) == len(set(paths)) and len(host_paths) == len(set(host_paths)),
         "launch_host_native_path_duplicate")
    need(all(_path(path) for path in paths)
         and all(_path(path, absolute=True) for path in host_paths), "launch_host_native_path_invalid")
    need(all(not any(str(parent) in paths for parent in PurePosixPath(path).parents) for path in paths),
         "launch_host_native_path_collision")
    need(all(type(row["size_bytes"]) is int for row in files)
         and sum(row["size_bytes"] for row in files) <= NATIVE_TOTAL_LIMIT,
         "launch_host_native_total_limit")
    by_path = {row["path"]: row for row in files}
    for role, key in (("launcher", "launcher_path"), ("loader", "loader_path")):
        selected = [row["path"] for row in files if row["role"] == role]
        need(selected == [selection[key]] and selection[key] in by_path,
             "launch_host_native_role_mismatch")
    need(selection["launcher_path"] != selection["loader_path"], "launch_host_native_role_mismatch")
    for row in selection["native_bindings"]:
        need(_path(row["consumer"]) and _path(row["provider"]), "launch_host_native_edge_path_invalid")
    return selection


def _decoded_file(row):
    if row["status"] not in {"present", "oversize"}:
        need(row["data_b64"] is None, "launch_host_observation_data_invalid")
        return None
    encoded = row["data_b64"]
    need(type(encoded) is str, "launch_host_observation_data_invalid")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HostError("launch_host_observation_base64_invalid") from exc
    need(base64.b64encode(raw).decode("ascii") == encoded and len(raw) <= HOST_FILE_LIMIT,
         "launch_host_observation_base64_invalid")
    need(row["status"] != "oversize" or len(raw) == HOST_FILE_LIMIT,
         "launch_host_observation_prefix_invalid")
    return raw


def validate_host_observation(raw):
    need(type(raw) is bytes and 0 < len(raw) <= HOST_LIMIT, "launch_host_observation_size")
    observation = parse(raw)
    need(canonical(observation) == raw, "launch_host_observation_noncanonical")
    _schema(observation, "host_observation")
    need(re.fullmatch(r"[0-9a-f]{32}", observation["observation_id"]) is not None,
         "launch_host_observation_identity_invalid")
    need(all(type(value) is int for value in observation["identity"].values())
         and (observation["open_fd_count"] is None or type(observation["open_fd_count"]) is int),
         "launch_host_observation_integer_invalid")
    need(all(all(32 <= ord(char) <= 126 for char in value)
             for value in observation["platform"].values()), "launch_host_observation_platform_invalid")
    soft, hard = (observation["nofile"][key] for key in ("soft", "hard"))
    need(all(value == "unlimited" or type(value) is int for value in (soft, hard)),
         "launch_host_observation_nofile_invalid")
    need(hard == "unlimited" or soft != "unlimited" and soft <= hard,
         "launch_host_observation_nofile_invalid")
    rows = observation["files"]
    need(len(rows) == len(HOST_PATHS) and {row["path"] for row in rows} == set(HOST_PATHS),
         "launch_host_observation_file_roster")
    for row in rows:
        _decoded_file(row)
    namespaces = observation["namespaces"]
    need(len(namespaces) == len(NAMESPACE_NAMES)
         and {row["name"] for row in namespaces} == set(NAMESPACE_NAMES),
         "launch_host_observation_namespace_roster")
    for row in namespaces:
        if row["status"] == "present":
            need(type(row["target"]) is str and re.fullmatch(
                re.escape(row["name"]) + r":\[[1-9][0-9]{0,19}\]", row["target"]) is not None,
                "launch_host_observation_namespace_target")
            need(int(row["target"].split("[")[1][:-1]) < 2**64,
                 "launch_host_observation_namespace_target")
        else:
            need(row["target"] is None, "launch_host_observation_namespace_target")
    return observation


def _native_graph(selection, payload):
    need(type(payload) is dict and set(payload) == {row["path"] for row in selection["native_files"]},
         "launch_host_native_inventory_mismatch")
    by_path = {row["path"]: row for row in selection["native_files"]}
    parsed = {}
    for path, row in by_path.items():
        raw = payload[path]
        need(type(raw) is bytes and 64 <= len(raw) <= NATIVE_FILE_LIMIT
             and binding(raw) == {key: row[key] for key in ("sha256", "size_bytes")},
             "launch_host_native_binding_mismatch")
        try:
            metadata = elf.inspect_elf(raw)
        except elf.ElfError as exc:
            raise HostError(exc.code) from exc
        need(metadata["rpath"] is None and metadata["runpath"] is None,
             "launch_host_loader_search_path_unsupported")
        parsed[path] = metadata
    launcher, loader = (selection[key] for key in ("launcher_path", "loader_path"))
    need(parsed[launcher]["interpreter"] is not None, "launch_host_launcher_loader_missing")
    need(parsed[loader]["elf_type"] == "ET_DYN" and parsed[loader]["interpreter"] is None,
         "launch_host_loader_invalid")
    providers = {}
    for path, metadata in parsed.items():
        name = metadata["soname"]
        if name is not None:
            need(name not in providers, "launch_host_native_provider_ambiguous")
            providers[name] = path
    expected = set()
    for path, metadata in parsed.items():
        if metadata["interpreter"] is not None:
            expected.add((path, "interpreter", metadata["interpreter"]))
        expected.update((path, "needed", name) for name in metadata["needed"])
    rows = selection["native_bindings"]
    keys = [(row["consumer"], row["kind"], row["name"]) for row in rows]
    need(len(keys) == len(set(keys)) and set(keys) == expected, "launch_host_native_edge_coverage")
    graph = {path: set() for path in parsed}
    for row in rows:
        provider = row["provider"]
        need(provider in parsed, "launch_host_native_provider_missing")
        if row["kind"] == "interpreter":
            need(provider == loader, "launch_host_loader_binding_mismatch")
            basename = row["name"].rsplit("/", 1)[-1]
            need(by_path[loader]["host_path"].rsplit("/", 1)[-1] == basename
                 and parsed[loader]["soname"] in {None, basename}, "launch_host_loader_identity_mismatch")
        else:
            need(providers.get(row["name"]) == provider, "launch_host_needed_binding_mismatch")
            need(parsed[provider]["elf_type"] == "ET_DYN", "launch_host_native_provider_type")
        graph[row["consumer"]].add(provider)
    reached, pending = set(), [launcher]
    while pending:
        path = pending.pop()
        if path not in reached:
            reached.add(path)
            pending.extend(graph[path] - reached)
    need(reached == set(parsed), "launch_host_native_unreachable")
    return {"launcher": launcher, "loader": loader,
            "files": [{**by_path[path], "elf": parsed[path]} for path in sorted(parsed)],
            "bindings": sorted(rows, key=lambda row: (row["consumer"], row["kind"], row["name"], row["provider"]))}


def _proc_fields(file_rows):
    row = file_rows["/proc/self/status"]
    if row["status"] != "present":
        return {key: None for key in PROC_FIELDS}
    try:
        lines = _decoded_file(row).decode("ascii").splitlines()
    except UnicodeError:
        return {key: None for key in PROC_FIELDS}
    found = {key: [] for key in PROC_FIELDS}
    for line in lines:
        key, separator, value = line.partition(":")
        if separator and key in found:
            found[key].append(value.strip())
    result = {}
    for key, values in found.items():
        value = values[0] if len(values) == 1 else None
        if key.startswith("Cap"):
            result[key] = (format(int(value, 16), "016x") if value is not None
                           and re.fullmatch(r"[0-9a-fA-F]{1,16}", value) else None)
        else:
            allowed = {"0", "1"} if key == "NoNewPrivs" else {"0", "1", "2"}
            result[key] = int(value) if value in allowed else None
    return result


def _decimal(row):
    if row["status"] != "present":
        return None
    raw = _decoded_file(row).strip()
    if not raw or len(raw) > 19 or re.fullmatch(rb"[0-9]+", raw) is None:
        return None
    value = int(raw)
    return value if value < 2**63 else None


def _passive_results(observation, request):
    results = []

    def add(identifier, status, value, reason):
        results.append({"id": identifier, "status": status, "value": value, "reason": reason})

    platform = observation["platform"]
    add("platform", "satisfied" if platform["system"] == "Linux" and platform["machine"] == "x86_64"
        else "blocked", platform, "recorded_platform_for_selected_profile")
    add("memfd_create_api", "satisfied" if observation["memfd_create_api"] else "blocked",
        observation["memfd_create_api"], "api_presence_only_no_memfd_or_execution_test")
    current = observation["open_fd_count"]
    add("proc_self_fd_accessible", "satisfied" if current is not None else "unknown", current,
        "observer_descriptor_count_not_launcher_descriptor_closure")
    headroom = request["launch_policy"]["file_descriptor_headroom"]
    need(type(headroom) is int and headroom == len(request["files"]) + 16,
         "launch_host_descriptor_requirement_mismatch")
    soft = observation["nofile"]["soft"]
    required = current + headroom if current is not None else None
    status = ("unknown" if required is None else "satisfied" if soft == "unlimited" or soft >= required else "blocked")
    add("descriptor_headroom", status,
        {"open_fd_count": current, "new_descriptor_headroom": headroom,
         "required_soft_limit": required, "observed_soft_limit": soft},
        "current_open_fds_plus_reconstructed_view_file_count_plus_16")
    rows = {row["path"]: row for row in observation["files"]}
    proc = _proc_fields(rows)
    maximum = _decimal(rows["/proc/sys/user/max_user_namespaces"])
    add("user_namespace_limit", "unknown" if maximum is None else "satisfied" if maximum > 0 else "blocked",
        maximum, "positive_limit_does_not_measure_usage_or_ancestor_limits")
    clone = _decimal(rows["/proc/sys/kernel/unprivileged_userns_clone"])
    unprivileged = observation["identity"]["euid"] != 0 and all(
        proc[key] == "0000000000000000" for key in ("CapInh", "CapPrm", "CapEff"))
    clone_status = ("satisfied" if clone == 1 else "blocked" if clone == 0 and unprivileged else "unknown")
    add("unprivileged_userns_clone", clone_status, clone,
        "zero_blocks_observed_nonroot_zero_capability_context_other_privilege_cases_unresolved")
    apparmor = _decimal(rows["/proc/sys/kernel/apparmor_restrict_unprivileged_userns"])
    add("apparmor_unprivileged_userns", "satisfied" if apparmor == 0 else "unknown", apparmor,
        "restriction_one_requires_separate_profile_permission_observation")
    memfd = _decimal(rows["/proc/sys/vm/memfd_noexec"])
    add("memfd_executable_default", "satisfied" if memfd == 0 else "blocked" if memfd in (1, 2) else "unknown",
        memfd, "current_sealed_buffer_omits_explicit_MFD_EXEC")
    preload = rows["/etc/ld.so.preload"]
    if preload["status"] == "absent":
        preload_status, preload_value = "satisfied", "absent"
    elif preload["status"] == "present":
        empty = not _decoded_file(preload).strip()
        preload_status, preload_value = ("satisfied", "empty") if empty else ("blocked", "nonempty")
    else:
        preload_status, preload_value = "unknown", preload["status"]
    add("loader_preload", preload_status, preload_value,
        "finite_profile_requires_absent_or_empty_preload_configuration")
    for key in PROC_FIELDS:
        add("observer_" + key, "observed" if proc[key] is not None else "unknown", proc[key],
            "observer_context_does_not_identify_intended_filter_or_child_state")
    return results


def derive_plan(*, containment_prepared, expected_containment_request_sha256,
                selection_bytes, expected_selection_sha256, entry_build_payload,
                launcher_package_bytes, native_payload, host_observation_bytes):
    """Reconstruct a finite relationship plan from externally selected originals."""
    selection = validate_selection(selection_bytes, expected_selection_sha256)
    try:
        prepared = containment._admitted(containment_prepared)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        raise HostError(getattr(exc, "code", "launch_host_containment_readmission_failed")) from exc
    need(_hash(expected_containment_request_sha256)
         and sha(prepared.request_bytes) == expected_containment_request_sha256
         and selection["containment_request_sha256"] == expected_containment_request_sha256,
         "launch_host_containment_request_mismatch")
    request = parse(prepared.request_bytes)
    need(selection["record_status"] == request["record_status"], "launch_host_record_status_mismatch")
    original = dict(prepared.inputs)
    containment_selection = parse(original["selection_bytes"])
    build = selection["entry_build"]
    try:
        build_report = entry_build.check_payload(entry_build_payload,
            expected_request_sha256=build["request_sha256"],
            expected_record_sha256=build["record_sha256"], source_commit=build["source_commit"])
    except (entry_build.BuildError, ValueError, TypeError, KeyError) as exc:
        raise HostError(getattr(exc, "code", "launch_host_entry_build_invalid")) from exc
    need(all(entry_build_payload[build_id + "/entry"] == original["entry_bytes"]
             for build_id in entry_build.BUILD_IDS), "launch_host_entry_build_binding_mismatch")
    source = entry_build_payload["source.c"]
    need(binding(source) == request["bindings"]["entry_source"], "launch_host_entry_source_binding_mismatch")
    try:
        installed_source = containment.bootstrap.runtime.observation.safe._read_regular(
            ROOT / containment.policy.ENTRY_SOURCE_PATH)
    except (OSError, ValueError) as exc:
        raise HostError("launch_host_entry_source_unavailable") from exc
    need(source == installed_source, "launch_host_entry_source_binding_mismatch")
    native = _native_graph(selection, native_payload)
    launcher = selection["launcher_path"]
    row = next(row for row in selection["native_files"] if row["path"] == launcher)
    need(row["host_path"] == containment_selection["launcher"]["path"],
         "launch_host_launcher_path_mismatch")
    need(native_payload[launcher] == original["launcher_bytes"], "launch_host_launcher_binding_mismatch")
    origin = selection["launcher_origin"]
    need(type(launcher_package_bytes) is bytes and binding(launcher_package_bytes) == origin["package"],
         "launch_host_package_binding_mismatch")
    try:
        package = package_reader.inspect_package(launcher_package_bytes,
            member_path=origin["member_path"], expected_name=origin["name"],
            expected_version=origin["version"], expected_architecture=origin["architecture"])
    except package_reader.PackageError as exc:
        raise HostError(exc.code) from exc
    need(package["member_bytes"] == native_payload[launcher], "launch_host_package_member_mismatch")
    mode = int(package["member"]["mode"], 8)
    need(not (mode & 0o6000) and bool(mode & 0o111), "launch_host_package_member_mode")
    need(type(host_observation_bytes) is bytes
         and binding(host_observation_bytes) == selection["host_observation"],
         "launch_host_observation_binding_mismatch")
    observation = validate_host_observation(host_observation_bytes)
    plan = {
        "record_type": "required_gate_idempotence_launch_host_plan_v0", "profile": PROFILE,
        "record_status": selection["record_status"],
        "bindings": {"selection": binding(selection_bytes), "containment_request": binding(prepared.request_bytes),
                     "entry_build_request": binding(entry_build_payload["request.json"]),
                     "entry_build_record": binding(entry_build_payload["record.json"]),
                     "launcher_package": binding(launcher_package_bytes),
                     "host_observation": binding(host_observation_bytes)},
        "entry_build": {**build, "checker_report": binding(canonical(build_report)),
                        "entry": binding(original["entry_bytes"]), "source": binding(source)},
        "containment": {"phase": request["phase"],
                        **{key: request["bindings"][key] for key in ("entry_source", "policy_source", "seccomp")}},
        "launcher_origin": {key: value for key, value in package.items() if key != "member_bytes"},
        "native": native,
        "host": {"observation": binding(host_observation_bytes),
                 "passive_prerequisites": _passive_results(observation, request),
                 "namespace_observations": [
                     {"name": row["name"], "status": "observed" if row["status"] == "present" else "unknown",
                      "source_status": row["status"], "target": row["target"]}
                     for row in sorted(observation["namespaces"], key=lambda row: row["name"])]},
        "pending_obligations": list(PENDING_OBLIGATIONS), **BOUNDARY,
    }
    result = canonical(plan)
    parse(result)
    return result


def verify_plan(*, plan_bytes, expected_plan_sha256, **inputs):
    need(_hash(expected_plan_sha256) and type(plan_bytes) is bytes
         and sha(plan_bytes) == expected_plan_sha256, "launch_host_plan_digest_mismatch")
    plan = parse(plan_bytes)
    need(canonical(plan) == plan_bytes, "launch_host_plan_noncanonical")
    _boundary(plan)
    expected = derive_plan(**inputs)
    need(plan_bytes == expected, "launch_host_plan_reconstruction_mismatch")
    return {"record_type": "required_gate_idempotence_launch_host_verification_v0",
            "profile": PROFILE, "status": "accepted", "record_status": plan["record_status"],
            "plan_sha256": expected_plan_sha256,
            "selection_sha256": inputs["expected_selection_sha256"],
            "containment_request_sha256": inputs["expected_containment_request_sha256"],
            "entry_build_binding_verified": True, "launcher_package_member_verified": True,
            "launcher_native_bindings_verified": True, "host_observation_record_verified": True,
            "passive_prerequisites": plan["host"]["passive_prerequisites"],
            "pending_obligations": list(PENDING_OBLIGATIONS), **BOUNDARY}


if __name__ == "__main__":
    # Original-input collection belongs to the coordinator's `check` command.
    # Running this library filename alone must never look like verification.
    sys.stdout.buffer.write(canonical({
        "record_type": "required_gate_idempotence_launch_host_verification_v0",
        "profile": PROFILE, "status": "rejected",
        "error_code": "launch_host_original_inputs_required", **BOUNDARY,
    }))
    raise SystemExit(1)
