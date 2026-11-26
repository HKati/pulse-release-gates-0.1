#!/usr/bin/env python3
"""Preserve and inspect selected runtime bytes without executing them.

This capsule closes a caller-selected file inventory and explicit static ELF
dependency bindings. It does not establish actual loader resolution, all Python
imports, host qualification, execution authorization or full runtime closure.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import io
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acquire_required_gate_idempotence_v0 as acquisition
import check_required_gate_idempotence_observation_v0 as observation
import required_gate_idempotence_elf_v0 as elf

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_runtime_v0.schema.json"
SCHEMA_SHA256 = "fa5b046ebd66f0003becaa040cdae8d6df1d10f8e4fbe16544cff4cc7623f83e"
CONTROL_LIMIT = 4 * 1024 * 1024
FILE_LIMIT = 128 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
ARCHIVE_LIMIT = 384 * 1024 * 1024
MAX_FILES = 4096
INVENTORY = "capture/member_inventory.json"
RUNTIME_SELECTION = "selection/runtime_selection.json"
OPERATOR_SELECTION = "selection/operator_selection.json"
TREES = tuple({"tree_id": name, "root": name} for name in ("python", "native", "repository", "licenses"))
BOOTSTRAP_FILES = (
    "encodings/__init__.py", "encodings/aliases.py", "encodings/utf_8.py",
    "importlib/__init__.py", "importlib/_bootstrap.py", "importlib/_bootstrap_external.py",
    "json/__init__.py", "ctypes/__init__.py", "argparse.py", "hashlib.py", "pathlib.py",
)
SITE_FILES = ("yaml/__init__.py", "jsonschema/__init__.py", "referencing/__init__.py",
              "rpds/__init__.py", "attr/__init__.py", "attrs/__init__.py",
              "jsonschema_specifications/__init__.py", "typing_extensions.py")
DISTRIBUTIONS = frozenset({"pyyaml", "jsonschema", "referencing", "rpds-py", "attrs",
                           "jsonschema-specifications", "typing-extensions"})
VERIFIER_PATHS = (
    "tools/check_required_gate_suite_contract_v0.py",
    "tools/check_required_gate_idempotence_observation_v0.py",
    "tools/pulsemech_compute_standalone_runtime_v0.py",
    "tools/pulsemech_compute_binding_analyzer_core_v0.py",
    "tools/build_pulsemech_compute_planned_observed_relation_v0.py",
    "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
    "schemas/required_gate_suite_contract_v0.schema.json",
    "schemas/required_gate_idempotence_observation_v0.schema.json",
    "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
    "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
    "schemas/pulsemech_compute_binding_report_v0.schema.json",
    "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json",
    "schemas/pulsemech_integration_plan_v0.schema.json",
)
BOUNDARY = {**observation.BOUNDARY, "host_environment_qualified": False,
            "python_import_closure_verified": False, "loader_resolution_verified": False,
            "restored_runtime_executed": False, "observed_acquisition_supported": False}


class CapsuleError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition: bool, code: str) -> None:
    if not condition:
        raise CapsuleError(code)


def sha(raw: bytes) -> str:
    return observation.sha(raw)


def canonical_bytes(value) -> bytes:
    return observation.canonical_bytes(value)


def parse(raw: bytes) -> dict:
    need(type(raw) is bytes and 0 < len(raw) <= CONTROL_LIMIT, "control_size_limit")
    try:
        return observation.safe._json(raw)
    except observation.safe.ContractError as exc:
        raise CapsuleError(exc.code) from exc


def validate_shape(value: dict, definition: str) -> None:
    try:
        raw = observation.safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(raw) == SCHEMA_SHA256, "runtime_schema_source_mismatch")
        observation.safe._validate_schema(value, parse(raw), definition + "_schema_invalid", definition)
    except observation.safe.ContractError as exc:
        raise CapsuleError(exc.code) from exc


def _bound(raw: bytes, descriptor: dict, code: str) -> None:
    need(type(raw) is bytes and type(descriptor.get("size_bytes")) is int
         and len(raw) == descriptor["size_bytes"] and sha(raw) == descriptor.get("sha256"), code)


def _select(selection_bytes, expected_selection_sha256, operator_selection_bytes,
            expected_operator_selection_sha256) -> tuple[dict, dict]:
    need(type(selection_bytes) is bytes and sha(selection_bytes) == expected_selection_sha256,
         "runtime_selection_digest_mismatch")
    need(type(operator_selection_bytes) is bytes and sha(operator_selection_bytes) == expected_operator_selection_sha256,
         "operator_selection_digest_mismatch")
    selection, operator = parse(selection_bytes), parse(operator_selection_bytes)
    validate_shape(selection, "selection")
    try:
        observation.validate_shape(operator, "selection")
    except observation.VerificationError as exc:
        raise CapsuleError(exc.code) from exc
    need(selection["operator_selection_sha256"] == expected_operator_selection_sha256,
         "runtime_operator_selection_mismatch")
    need(selection["repository"] == operator["repository"] and selection["source_commit"] == operator["source_commit"]
         and canonical_bytes(selection["environment"]) == canonical_bytes(operator["environment"]),
         "runtime_subject_mismatch")
    need((selection["record_status"], operator["record_status"]) in {("example", "example"), ("selected", "observed")},
         "runtime_record_status_mismatch")
    need(sorted(selection["trees"], key=lambda value: value["tree_id"])
         == sorted(TREES, key=lambda value: value["tree_id"]), "runtime_tree_roster_mismatch")
    files = selection["files"]
    paths = [item["path"] for item in files]
    need(len(paths) == len(set(paths)), "runtime_duplicate_path")
    need(all(observation.path_ok(path) and len(path.split("/")) <= 32 for path in paths), "runtime_path_invalid")
    need(sum(item["size_bytes"] for item in files) <= TOTAL_LIMIT, "runtime_total_size_limit")
    by_path = {item["path"]: item for item in files}
    for path in paths:
        parts = path.split("/")
        need(not any("/".join(parts[:index]) in by_path for index in range(1, len(parts))),
             "runtime_file_directory_collision")
        need("__pycache__" not in parts and not path.endswith((".pyc", ".pyo", ".pth"))
             and parts[-1] not in {"sitecustomize.py", "usercustomize.py"}, "runtime_startup_injection_file")
    for item in files:
        path, role, fmt = item["path"], item["role"], item["format"]
        need(path.startswith(item["tree_id"] + "/"), "runtime_tree_assignment_mismatch")
        if role in {"repository_source", "repository_schema", "repository_data"}:
            need(item["tree_id"] == "repository" and item["source_path"] is not None
                 and item["source_revision"] is not None
                 and observation.path_ok(item["source_path"])
                 and path == "repository/" + item["source_path"], "repository_source_locator_mismatch")
            need((role == "repository_source" and fmt == "python" and path.endswith(".py"))
                 or (role == "repository_schema" and fmt == "json" and path.endswith(".json"))
                 or role == "repository_data", "repository_source_format_mismatch")
        else:
            need(item["source_path"] is None and item["source_revision"] is None
                 and item["tree_id"] != "repository", "nonrepository_source_locator")
        if role in {"interpreter", "loader", "shared_library"}:
            need(fmt == "elf" and item["size_bytes"] > 0, "native_format_mismatch")
        if role == "license":
            need(item["tree_id"] == "licenses" and fmt == "text" and item["size_bytes"] > 0,
                 "license_selection_invalid")
        else:
            need(item["tree_id"] != "licenses", "license_tree_assignment_mismatch")
        if role == "stdlib":
            need(path.startswith(selection["python"]["stdlib_root"] + "/")
                 and not path.startswith(selection["python"]["site_packages_root"] + "/"), "stdlib_assignment_mismatch")
        if role == "site_package":
            need(path.startswith(selection["python"]["site_packages_root"] + "/"), "site_package_assignment_mismatch")
    for role, key in (("interpreter", "interpreter"), ("loader", "loader")):
        selected = [row for row in files if row["role"] == role]
        need(len(selected) == 1 and selected[0]["path"] == selection["python"][key], "native_role_mismatch")
    need(by_path[selection["python"]["interpreter"]]["sha256"] == selection["environment"]["executable_sha256"],
         "interpreter_selection_mismatch")
    for role, prefix, baseline in (("stdlib", selection["python"]["stdlib_root"], BOOTSTRAP_FILES),
                                   ("site_package", selection["python"]["site_packages_root"], SITE_FILES)):
        need(all(by_path.get(prefix + "/" + path, {}).get("role") == role for path in baseline),
             "runtime_baseline_file_missing")
    need(any(row["role"] == "license" for row in files), "runtime_notice_missing")
    return selection, operator


def _native(selection: dict, payload: dict[str, bytes]) -> list[dict]:
    parsed = {}
    for item in selection["files"]:
        raw = payload[item["path"]]
        need(not raw.startswith(b"\x7fELF") or item["format"] == "elf", "undeclared_elf_file")
        if item["format"] == "elf":
            try:
                parsed[item["path"]] = elf.inspect_elf(raw)
            except elf.ElfError as exc:
                raise CapsuleError(exc.code) from exc
    interpreter, loader = selection["python"]["interpreter"], selection["python"]["loader"]
    need(parsed[interpreter]["interpreter"] is not None, "interpreter_loader_missing")
    need(parsed[loader]["elf_type"] == "ET_DYN" and parsed[loader]["interpreter"] is None, "loader_elf_invalid")
    providers = {}
    for path, record in parsed.items():
        name = record["soname"]
        if name is not None:
            need(name not in providers, "native_provider_ambiguous")
            providers[name] = path
    expected = set()
    for path, record in parsed.items():
        if record["interpreter"] is not None:
            expected.add((path, "interpreter", record["interpreter"]))
        expected.update((path, "needed", name) for name in record["needed"])
    rows = selection["native_bindings"]
    keys = [(row["consumer"], row["kind"], row["name"]) for row in rows]
    need(len(keys) == len(set(keys)) and set(keys) == expected, "native_binding_coverage_mismatch")
    for row in rows:
        need(row["provider"] in parsed, "native_provider_missing")
        if row["kind"] == "interpreter":
            need(row["provider"] == loader, "native_loader_binding_mismatch")
            name = row["name"].rsplit("/", 1)[-1]
            need(name == loader.rsplit("/", 1)[-1]
                 and parsed[loader]["soname"] in {None, name}, "native_loader_identity_mismatch")
        else:
            need(providers.get(row["name"]) == row["provider"], "native_needed_binding_mismatch")
            need(parsed[row["provider"]]["elf_type"] == "ET_DYN", "native_provider_type_invalid")
    return [{"path": path, **record} for path, record in sorted(parsed.items())]


def _packages(selection: dict, payload: dict[str, bytes]) -> list[dict]:
    site = selection["python"]["site_packages_root"] + "/"
    seen = {}
    by_path = {row["path"]: row for row in selection["files"]}
    for path, raw in sorted(payload.items()):
        if not path.startswith(site) or not path.endswith(".dist-info/METADATA"):
            continue
        need(len(raw) <= CONTROL_LIMIT and by_path[path]["role"] == "site_package", "distribution_metadata_invalid")
        document = BytesParser().parsebytes(raw, headersonly=True)
        names, versions = document.get_all("Name", []), document.get_all("Version", [])
        need(len(names) == len(versions) == 1 and isinstance(names[0], str) and isinstance(versions[0], str),
             "distribution_identity_invalid")
        name = re.sub(r"[-_.]+", "-", names[0]).lower()
        need(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", name) is not None
             and re.fullmatch(r"[A-Za-z0-9.!+_-]{1,100}", versions[0]) is not None
             and name not in seen, "distribution_identity_invalid")
        record = path.rsplit("/", 1)[0] + "/RECORD"
        need(record in payload and by_path[record]["role"] == "site_package", "distribution_record_missing")
        seen[name] = {"name": name, "declared_version": versions[0], "metadata_path": path,
                      "metadata_sha256": sha(raw), "record_path": record, "record_sha256": sha(payload[record])}
    need(DISTRIBUTIONS <= set(seen), "distribution_baseline_missing")
    return [seen[name] for name in sorted(seen)]


def _payload(selection: dict, operator: dict, payload: dict[str, bytes], repository_root: Path | None):
    files = {row["path"]: row for row in selection["files"]}
    need(set(payload) == set(files), "runtime_payload_roster_mismatch")
    for path, descriptor in files.items():
        _bound(payload[path], descriptor, "runtime_file_digest_mismatch")
    # The existing source selection rules, including the four original pins,
    # remain authoritative for the subject sources. This module never executes
    # any selected source or trusts a capsule-supplied admission assertion.
    observation_members = {"selection/" + name: observation.safe._read_regular(acquisition.PROPOSAL / name)
                           for name in observation.PROTOCOL_PINS}
    operator_sources = {row["path"]: row for row in operator["sources"]}
    for role, path in (("worker", acquisition.WORKER), ("collector", acquisition.COLLECTOR),
                       ("implementation_dependency", acquisition.PROCESS)):
        item = operator_sources.get(path, {})
        need(item.get("role") == role and item.get("source_revision") == selection["source_commit"],
             "runtime_acquisition_selection_mismatch")
    for path, source in operator_sources.items():
        item = files.get("repository/" + path, {})
        need(item.get("role") == "repository_source"
             and all(item.get(key) == source[key] for key in ("sha256", "size_bytes", "source_revision")),
             "runtime_operator_source_mismatch")
        observation_members[source["member"]] = payload["repository/" + path]
    for path in (*VERIFIER_PATHS, acquisition.WORKER, acquisition.COLLECTOR, acquisition.PROCESS):
        virtual = "repository/" + path
        need(virtual in files, "runtime_verifier_source_missing")
        need(payload[virtual] == observation.safe._read_regular(ROOT / path), "runtime_installed_source_mismatch")
    if selection["record_status"] == "selected":
        need(repository_root is not None, "selected_repository_required")
    for path, item in files.items():
        if item["source_path"] is None:
            continue
        expected_revision = (operator_sources[item["source_path"]]["source_revision"]
                             if item["source_path"] in operator_sources else selection["source_commit"])
        need(item["source_revision"] == expected_revision, "runtime_source_revision_mismatch")
        if selection["record_status"] == "selected":
            need(observation._git_blob(repository_root, item["source_revision"], item["source_path"], item["size_bytes"])
                 == payload[path], "runtime_source_git_mismatch")
    observation._selection(operator, observation_members, repository_root=repository_root)
    return _native(selection, payload), _packages(selection, payload)


def read_archive(raw: bytes) -> dict[str, bytes]:
    need(type(raw) is bytes and 0 < len(raw) <= ARCHIVE_LIMIT, "capsule_size_limit")
    members = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(0 < len(entries) <= MAX_FILES + 3 and not archive.comment, "capsule_member_count_limit")
            total = 0
            for entry in entries:
                name = entry.filename
                need(observation.path_ok(name) and entry.orig_filename == name and not entry.is_dir()
                     and name not in members, "capsule_member_path_invalid")
                need(stat.S_IFMT(entry.external_attr >> 16) in {0, stat.S_IFREG}, "capsule_member_type_invalid")
                need(entry.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                     and not entry.comment and not entry.extra and not (entry.flag_bits & (1 | 64)),
                     "capsule_encoding_unsupported")
                maximum = FILE_LIMIT if name.startswith("payload/") else CONTROL_LIMIT
                need(0 <= entry.file_size <= maximum, "capsule_member_size_limit")
                total += entry.file_size
                need(total <= TOTAL_LIMIT, "capsule_total_size_limit")
                with archive.open(entry) as stream:
                    data = stream.read(entry.file_size + 1)
                need(len(data) == entry.file_size, "capsule_member_size_mismatch")
                members[name] = data
            observation._zip_layout(raw, entries)
    except observation.VerificationError as exc:
        raise CapsuleError(exc.code) from exc
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError,
            UnicodeError, struct.error, zlib.error) as exc:
        if isinstance(exc, CapsuleError):
            raise
        raise CapsuleError("capsule_invalid") from exc
    return members


def _verify(*, selection_bytes, expected_selection_sha256, operator_selection_bytes,
            expected_operator_selection_sha256, capsule_bytes, expected_capsule_sha256, repository_root=None):
    selection, operator = _select(selection_bytes, expected_selection_sha256,
                                  operator_selection_bytes, expected_operator_selection_sha256)
    need(type(capsule_bytes) is bytes and sha(capsule_bytes) == expected_capsule_sha256, "capsule_digest_mismatch")
    members = read_archive(capsule_bytes)
    expected = {RUNTIME_SELECTION, OPERATOR_SELECTION, INVENTORY}
    expected.update("payload/" + row["path"] for row in selection["files"])
    need(set(members) == expected, "capsule_inventory_mismatch")
    need(members[RUNTIME_SELECTION] == selection_bytes and members[OPERATOR_SELECTION] == operator_selection_bytes,
         "capsule_selection_copy_mismatch")
    inventory = parse(members[INVENTORY])
    validate_shape(inventory, "inventory")
    indexed = [row["member"] for row in inventory["members"]]
    need(len(indexed) == len(set(indexed)) and set(indexed) == expected - {INVENTORY}, "capsule_inventory_coverage_mismatch")
    for row in inventory["members"]:
        _bound(members[row["member"]], row, "capsule_inventory_digest_mismatch")
    payload = {row["path"]: members["payload/" + row["path"]] for row in selection["files"]}
    native, packages = _payload(selection, operator, payload, repository_root)
    report = {"record_type": "required_gate_idempotence_runtime_verification_v0", "status": "accepted", "ok": True,
              "record_status": selection["record_status"], "runtime_selection_sha256": expected_selection_sha256,
              "operator_selection_sha256": expected_operator_selection_sha256,
              "capsule_sha256": expected_capsule_sha256, "capsule_size_bytes": len(capsule_bytes),
              "verification_scope": "selected_runtime_bytes_and_static_native_bindings",
              "selected_runtime_bytes_recoverable": True, "native_dependency_bindings_verified": True,
              "source_git_binding_verified": selection["record_status"] == "selected",
              "file_count": len(payload), "payload_size_bytes": sum(map(len, payload.values())),
              "files": [{key: row[key] for key in ("path", "role", "sha256", "size_bytes")}
                        for row in sorted(selection["files"], key=lambda value: value["path"])],
              "native_objects": native,
              "native_bindings": sorted(selection["native_bindings"], key=lambda row: (row["consumer"], row["kind"], row["name"])),
              "distributions": packages, "declared_environment": selection["environment"],
              "outstanding": ["restored_bootstrap_qualification", "dynamic_import_and_dlopen_closure",
                              "actual_loader_path_enforcement", "host_containment_review",
                              "observed_launch_integration", "separate_owner_authorization"], **BOUNDARY}
    return report, payload


def verify_capsule(**kwargs) -> dict:
    try:
        return _verify(**kwargs)[0]
    except (observation.VerificationError, observation.safe.ContractError, elf.ElfError) as exc:
        raise CapsuleError(exc.code) from exc


def _identity(info):
    return tuple(getattr(info, key) for key in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))


def _read_fd(fd: int, maximum: int, *, allow_empty: bool = True) -> bytes:
    before = os.fstat(fd)
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "runtime_file_not_private_regular")
    need((0 if allow_empty else 1) <= before.st_size <= maximum, "runtime_file_size_limit")
    raw = bytearray()
    while True:
        block = os.read(fd, min(65536, maximum + 1 - len(raw)))
        if not block:
            break
        raw.extend(block)
        need(len(raw) <= maximum, "runtime_file_size_limit")
    need(len(raw) == before.st_size and _identity(before) == _identity(os.fstat(fd)), "runtime_file_changed_during_read")
    return bytes(raw)


def read_regular(path: Path, maximum: int) -> bytes:
    parent = fd = None
    try:
        parent, name = observation.safe._parent_fd(observation.safe._absolute(path))
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        return _read_fd(fd, maximum)
    except (OSError, observation.safe.ContractError) as exc:
        raise CapsuleError("runtime_input_path_unsafe") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def _snapshot_at(root_fd: int, selection: dict) -> dict[str, bytes]:
    """Read the exact selected tree through an already pinned directory."""
    selected = {row["path"]: row for row in selection["files"]}
    directories = {str(Path(path).parent).replace(os.sep, "/") for path in selected}
    for path in list(directories):
        directories.update(str(parent).replace(os.sep, "/") for parent in Path(path).parents if str(parent) != ".")
    result = {}
    count = 0

    def walk(fd: int, prefix: str):
        nonlocal count
        before = os.fstat(fd)
        with os.scandir(fd) as entries:
            for entry in entries:
                count += 1
                need(count <= MAX_FILES * 8, "runtime_tree_entry_limit")
                path = prefix + entry.name
                need(observation.path_ok(path), "runtime_path_invalid")
                info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    need(path in directories, "source_tree_inventory_mismatch")
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                    try:
                        need(_identity(info) == _identity(os.fstat(child)), "runtime_tree_changed")
                        walk(child, path + "/")
                    finally:
                        os.close(child)
                else:
                    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "runtime_file_not_private_regular")
                    need(path in selected, "source_tree_inventory_mismatch")
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
                    try:
                        need(_identity(info) == _identity(os.fstat(child)), "runtime_tree_changed")
                        raw = _read_fd(child, FILE_LIMIT)
                    finally:
                        os.close(child)
                    _bound(raw, selected[path], "runtime_file_digest_mismatch")
                    result[path] = raw
        need(_identity(before) == _identity(os.fstat(fd)), "runtime_tree_changed")

    walk(root_fd, "")
    need(set(result) == set(selected), "source_tree_inventory_mismatch")
    return result


def _snapshot(source_root: Path, selection: dict) -> dict[str, bytes]:
    parent = root_fd = None
    try:
        parent, name = observation.safe._parent_fd(observation.safe._absolute(source_root))
        root_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        return _snapshot_at(root_fd, selection)
    except (OSError, observation.safe.ContractError) as exc:
        raise CapsuleError("runtime_source_root_unsafe") from exc
    finally:
        if root_fd is not None:
            os.close(root_fd)
        if parent is not None:
            os.close(parent)


def _same_destination(directory_fd: int, output_directory: Path) -> None:
    """Detect a destination substitution before publishing the completion record."""
    parent = current = None
    try:
        parent, name = observation.safe._parent_fd(observation.safe._absolute(output_directory))
        current = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        original_info, current_info = os.fstat(directory_fd), os.fstat(current)
        need((original_info.st_dev, original_info.st_ino) == (current_info.st_dev, current_info.st_ino),
             "runtime_restore_destination_changed")
    except (OSError, observation.safe.ContractError) as exc:
        raise CapsuleError("runtime_restore_destination_changed") from exc
    finally:
        if current is not None:
            os.close(current)
        if parent is not None:
            os.close(parent)


def _archive(members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o400) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return output.getvalue()


def build_capsule(*, selection_bytes, expected_selection_sha256, operator_selection_bytes,
                  expected_operator_selection_sha256, source_root, repository_root=None) -> bytes:
    try:
        selection, operator = _select(selection_bytes, expected_selection_sha256,
                                      operator_selection_bytes, expected_operator_selection_sha256)
        payload = _snapshot(source_root, selection)
        _payload(selection, operator, payload, repository_root)
        members = {"payload/" + path: raw for path, raw in payload.items()}
        members.update({RUNTIME_SELECTION: selection_bytes, OPERATOR_SELECTION: operator_selection_bytes})
        members[INVENTORY] = canonical_bytes({"record_type": "required_gate_idempotence_runtime_inventory_v0",
                                             "members": [{"member": name, "sha256": sha(raw), "size_bytes": len(raw)}
                                                         for name, raw in sorted(members.items())]})
        result = _archive(members)
        verify_capsule(selection_bytes=selection_bytes, expected_selection_sha256=expected_selection_sha256,
                       operator_selection_bytes=operator_selection_bytes,
                       expected_operator_selection_sha256=expected_operator_selection_sha256,
                       capsule_bytes=result, expected_capsule_sha256=sha(result), repository_root=repository_root)
        return result
    except (observation.VerificationError, observation.safe.ContractError, elf.ElfError) as exc:
        raise CapsuleError(exc.code) from exc


def restore_capsule(*, output_directory, **kwargs) -> dict:
    try:
        report, payload = _verify(**kwargs)
    except (observation.VerificationError, observation.safe.ContractError, elf.ElfError) as exc:
        raise CapsuleError(exc.code) from exc
    directory = None
    completed = []
    try:
        directory = acquisition._Directory(output_directory)
        for path, raw in sorted(payload.items()):
            relative = "payload/" + path
            fd = directory.create(relative)
            try:
                directory.append(fd, raw)
                os.fchmod(fd, 0o400)
                os.fsync(fd)
            finally:
                os.close(fd)
            completed.append({"path": relative, "sha256": sha(raw), "size_bytes": len(raw), "mode": "0400"})
        # Re-open under the same pinned output directory used for writes. A
        # substituted pathname must not redirect this check to a clean decoy.
        payload_fd = os.open("payload", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=directory.fd)
        try:
            restored = _snapshot_at(payload_fd, parse(kwargs["selection_bytes"]))
        finally:
            os.close(payload_fd)
        need(restored == payload, "restored_bytes_mismatch")
        directory.write("runtime_selection.json", kwargs["selection_bytes"])
        directory.write("operator_selection.json", kwargs["operator_selection_bytes"])
        result = {**report, "record_type": "required_gate_idempotence_runtime_restoration_v0",
                  "status": "restored", "restored_bytes_verified": True,
                  "execution_permissions_added": False, "restored_files": completed}
        _same_destination(directory.fd, output_directory)
        directory.write("restoration.json", canonical_bytes(result))
        return result
    except BaseException as exc:
        code = exc.code if isinstance(exc, (CapsuleError, acquisition.AcquisitionError)) else "runtime_restore_failed"
        if directory is not None:
            try:
                directory.write("restoration.incomplete.json", canonical_bytes({
                    "record_type": "required_gate_idempotence_runtime_restoration_v0", "status": "incomplete",
                    "errors": [code], "completed_files": completed,
                    "runtime_selection_sha256": report["runtime_selection_sha256"],
                    "capsule_sha256": report["capsule_sha256"], "automatic_cleanup": False, **BOUNDARY}))
            except BaseException:
                pass  # Existing files remain if storage failure prevents a terminal record.
        raise CapsuleError(code) from exc
    finally:
        if directory is not None:
            directory.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check", "restore"):
        sub = commands.add_parser(name)
        sub.add_argument("--selection", type=Path, required=True)
        sub.add_argument("--selection-sha256", required=True)
        sub.add_argument("--operator-selection", type=Path, required=True)
        sub.add_argument("--operator-selection-sha256", required=True)
        sub.add_argument("--repository-root", type=Path)
        if name == "build":
            sub.add_argument("--source-root", type=Path, required=True)
            sub.add_argument("--output", type=Path, required=True)
        else:
            sub.add_argument("--capsule", type=Path, required=True)
            sub.add_argument("--capsule-sha256", required=True)
            if name == "restore":
                sub.add_argument("--output-directory", type=Path, required=True)
            else:
                sub.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output_parent = None
    try:
        if getattr(args, "output", None) is not None:
            output_parent, output_name = observation.safe._output_preflight(args.output)
        common = {"selection_bytes": read_regular(args.selection, CONTROL_LIMIT),
                  "expected_selection_sha256": args.selection_sha256,
                  "operator_selection_bytes": read_regular(args.operator_selection, CONTROL_LIMIT),
                  "expected_operator_selection_sha256": args.operator_selection_sha256,
                  "repository_root": args.repository_root}
        if args.command == "build":
            capsule = build_capsule(**common, source_root=args.source_root)
            observation.safe._write_output(output_parent, output_name, capsule)
            result = verify_capsule(**common, capsule_bytes=capsule, expected_capsule_sha256=sha(capsule))
        else:
            common.update(capsule_bytes=read_regular(args.capsule, ARCHIVE_LIMIT),
                          expected_capsule_sha256=args.capsule_sha256)
            result = (restore_capsule(**common, output_directory=args.output_directory)
                      if args.command == "restore" else verify_capsule(**common))
            if output_parent is not None:
                observation.safe._write_output(output_parent, output_name, canonical_bytes(result))
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (CapsuleError, observation.VerificationError, observation.safe.ContractError, acquisition.AcquisitionError) as exc:
        result = {"record_type": "required_gate_idempotence_runtime_verification_v0", "status": "rejected", "ok": False,
                  "errors": [exc.code], "selected_runtime_bytes_recoverable": False,
                  "native_dependency_bindings_verified": False, **BOUNDARY}
        sys.stdout.buffer.write(canonical_bytes(result))
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        sys.stdout.buffer.write(canonical_bytes({"status": "rejected", "ok": False,
                                                "errors": ["runtime_operation_failed"], **BOUNDARY}))
        return 1
    finally:
        if output_parent is not None:
            os.close(output_parent)


if __name__ == "__main__":
    raise SystemExit(main())
