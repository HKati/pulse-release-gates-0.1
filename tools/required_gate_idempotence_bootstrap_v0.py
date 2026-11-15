#!/usr/bin/env python3
"""Compile and preserve a finite bootstrap launch view without launching it.

Plan acceptance binds exact selected bytes and a fixed diagnostic program.
It does not qualify bootstrap execution, import closure, loader resolution,
host containment or an observed acquisition route.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_runtime_v0 as runtime
import required_gate_idempotence_bootstrap_probe_v0 as probe

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_bootstrap_v0.schema.json"
SCHEMA_SHA256 = "8dff32af9d769ee0f7e60b3942ce0b7cd908b61a4393cc5a3a1682b4b9599b7a"
PROBE_PATH = "tools/required_gate_idempotence_bootstrap_probe_v0.py"
PROFILE = "restored_bootstrap_plan_v0"
PROBE_VIRTUAL = "/runtime/bootstrap/probe.py"
CONTRACT_VIRTUAL = "/runtime/bootstrap/contract.json"
INTERPRETER = "/runtime/python/bin/python3.11"
LOADER = "/runtime/native/ld-linux-x86-64.so.2"
STDLIB = "python/lib/python3.11"
DYNLIB = STDLIB + "/lib-dynload"
SITE = STDLIB + "/site-packages"
IMPORT_ROOTS = (STDLIB, DYNLIB, SITE, "repository/tools")
EXTENSION_SUFFIXES = (".cpython-311-x86_64-linux-gnu.so", ".abi3.so", ".so")
INTERPRETER_ALIASES = frozenset({"/lib64/ld-linux-x86-64.so.2",
                                "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"})
ENVIRONMENT = {"LC_ALL": "C", "TZ": "UTC"}
LIMITS = {"wall_seconds": 15, "cpu_seconds": 5, "address_space_bytes": 512 * 1024 * 1024,
          "stdout_bytes": 65536, "stderr_bytes": 4096, "applications": 0, "attempts": 1}
VIEW_LIMIT = 512 * 1024 * 1024
MAX_VIEW_FILES = 8192
BOUNDARY = {**runtime.BOUNDARY, "restored_bootstrap_qualified": False,
            "bootstrap_execution_observed": False, "interpreter_module_membership_verified": False,
            "containment_enforced": False}
_ADMISSION = object()


class BootstrapError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition: bool, code: str) -> None:
    if not condition:
        raise BootstrapError(code)


def sha(raw: bytes) -> str:
    return runtime.sha(raw)


def canonical_bytes(value) -> bytes:
    return runtime.canonical_bytes(value)


def parse(raw: bytes) -> dict:
    try:
        return runtime.parse(raw)
    except runtime.CapsuleError as exc:
        raise BootstrapError(exc.code) from exc


def _shape(value: dict) -> None:
    raw = runtime.observation.safe._read_regular(ROOT / SCHEMA_PATH)
    need(sha(raw) == SCHEMA_SHA256, "bootstrap_schema_source_mismatch")
    runtime.observation.safe._validate_schema(value, parse(raw), "bootstrap_selection_schema_invalid", "selection")


def _name_set() -> set[str]:
    result = set(probe.MODULE_TARGETS)
    for name in tuple(result):
        parts = name.split(".")
        result.update(".".join(parts[:index]) for index in range(1, len(parts)))
    return result


def _candidates(name: str, files: dict) -> list[str]:
    relative = name.replace(".", "/")
    result = set()
    for root in IMPORT_ROOTS:
        for suffix in (".py", "/__init__.py", *EXTENSION_SUFFIXES):
            path = root + "/" + relative + suffix
            if path in files:
                result.add(path)
    return sorted(result)


def _modules(selection: dict, runtime_selection: dict, payload: dict, native_objects: list[dict]) -> list[dict]:
    files = {row["path"]: row for row in runtime_selection["files"]}
    native = {row["path"]: row for row in native_objects}
    names = _name_set()
    declarations = selection["interpreter_modules"]
    declared = {row["name"]: row["kind"] for row in declarations}
    need(len(declared) == len(declarations) and set(declared) <= names, "bootstrap_interpreter_module_roster")
    parents = {name.rsplit(".", 1)[0] for name in names if "." in name}
    need(not (set(declared) & parents), "bootstrap_package_parent_invalid")
    interpreter = files[runtime_selection["python"]["interpreter"]]
    result = []
    provider_by_name = {}
    for name in sorted(names):
        if name in declared:
            provider = {"name": name, "kind": declared[name], "path": None,
                        "sha256": interpreter["sha256"], "size_bytes": interpreter["size_bytes"]}
        else:
            candidates = _candidates(name, files)
            need(bool(candidates), "bootstrap_module_missing")
            need(len(candidates) == 1, "bootstrap_module_ambiguous")
            path = candidates[0]
            item = files[path]
            source = path.endswith(".py")
            need((source and item["format"] == "python"
                  and item["role"] in {"stdlib", "site_package", "repository_source"})
                 or (not source and item["format"] == "elf"
                     and item["role"] in {"stdlib", "site_package", "shared_library"}),
                 "bootstrap_module_format_mismatch")
            if not source:
                need(native.get(path, {}).get("elf_type") == "ET_DYN", "bootstrap_extension_type_invalid")
            if source:
                need(0 < len(payload[path]) <= 512 * 1024, "bootstrap_module_size_limit")
                try:
                    ast.parse(payload[path], filename=path, feature_version=(3, 11))
                except (SyntaxError, ValueError, RecursionError) as exc:
                    raise BootstrapError("bootstrap_module_syntax_invalid") from exc
            if name in parents:
                need(source and path.endswith("/__init__.py"), "bootstrap_package_parent_invalid")
            provider = {"name": name, "kind": "source" if source else "extension",
                        "path": "/runtime/" + path, "sha256": item["sha256"], "size_bytes": item["size_bytes"]}
        provider_by_name[name] = provider
        result.append(provider)
    for name, provider in provider_by_name.items():
        if "." not in name:
            continue
        parent = provider_by_name[name.rsplit(".", 1)[0]]
        if provider["path"] is not None:
            need(provider["path"].startswith(parent["path"].rsplit("/", 1)[0] + "/"),
                 "bootstrap_package_provider_mismatch")
    return result


def _resources(runtime_selection: dict, payload: dict) -> list[dict]:
    expected = set(probe.REQUIRED_RESOURCE_IDS)
    found = {}
    prefix = SITE + "/jsonschema_specifications/schemas/"
    for item in runtime_selection["files"]:
        path = item["path"]
        if not path.startswith(prefix) or not path.endswith(".json"):
            continue
        need(item["role"] == "site_package" and item["format"] == "json", "bootstrap_resource_format_mismatch")
        document = parse(payload[path])
        need(type(document) is dict, "bootstrap_resource_invalid")
        identity = document.get("$id")
        need(identity is None or type(identity) is str, "bootstrap_resource_identity_invalid")
        if identity not in expected:
            continue
        need(document.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
             "bootstrap_resource_dialect_mismatch")
        need(identity not in found, "bootstrap_resource_ambiguous")
        found[identity] = {"path": "/runtime/" + path, "sha256": item["sha256"],
                           "size_bytes": item["size_bytes"], "schema_id": identity}
    need(set(found) == expected, "bootstrap_resource_missing")
    return [found[identity] for identity in sorted(found)]


def _layout(selection: dict, report: dict, payload: dict, contract: bytes, probe_bytes: bytes):
    files = {}
    content = {}

    def add(path: str, raw: bytes, origin: str, source_path: str | None):
        need(path.startswith("/") and runtime.observation.path_ok(path[1:]), "bootstrap_view_path_invalid")
        row = {"path": path, "origin": origin, "source_path": source_path,
               "sha256": sha(raw), "size_bytes": len(raw), "mode": "0400"}
        if path in files:
            need(files[path] == row and content[path] == raw, "bootstrap_view_collision")
            return
        files[path], content[path] = row, raw

    for path, raw in sorted(payload.items()):
        basename = path.rsplit("/", 1)[-1]
        need(basename != "pyvenv.cfg" and not basename.endswith("._pth")
             and not basename.endswith((".zip", ".egg", ".whl")), "bootstrap_startup_override_forbidden")
        add("/runtime/" + path, raw, "capsule", path)
    for record in report["native_objects"]:
        source = record["path"]
        if record["soname"] is not None:
            add("/runtime/native/" + record["soname"], payload[source], "capsule", source)
        if record["interpreter"] is not None:
            need(record["interpreter"] in INTERPRETER_ALIASES, "bootstrap_interpreter_path_unsupported")
            loader_source = selection["python"]["loader"]
            add(record["interpreter"], payload[loader_source], "capsule", loader_source)
    add(PROBE_VIRTUAL, probe_bytes, "probe", PROBE_PATH)
    add(CONTRACT_VIRTUAL, contract, "contract", None)
    need(len(files) <= MAX_VIEW_FILES and sum(map(len, content.values())) <= VIEW_LIMIT, "bootstrap_view_size_limit")
    for path in files:
        parts = path[1:].split("/")
        need(not any("/" + "/".join(parts[:index]) in files for index in range(1, len(parts))),
             "bootstrap_view_file_directory_collision")
    return [files[path] for path in sorted(files)], content


@dataclass(frozen=True, init=False)
class PreparedBootstrap:
    inputs: tuple
    plan_bytes: bytes
    contents: tuple[tuple[str, bytes], ...]
    _admission: object


def _prepare(*, runtime_selection_bytes, expected_runtime_selection_sha256,
             operator_selection_bytes, expected_operator_selection_sha256,
             capsule_bytes, expected_capsule_sha256, bootstrap_selection_bytes,
             expected_bootstrap_selection_sha256, repository_root=None) -> PreparedBootstrap:
    need(type(bootstrap_selection_bytes) is bytes and sha(bootstrap_selection_bytes) == expected_bootstrap_selection_sha256,
         "bootstrap_selection_digest_mismatch")
    selected = parse(bootstrap_selection_bytes)
    _shape(selected)
    for key, expected in (("runtime_selection_sha256", expected_runtime_selection_sha256),
                          ("operator_selection_sha256", expected_operator_selection_sha256),
                          ("capsule_sha256", expected_capsule_sha256)):
        need(selected[key] == expected, "bootstrap_subject_mismatch")
    report, payload = runtime._verify(selection_bytes=runtime_selection_bytes,
                                     expected_selection_sha256=expected_runtime_selection_sha256,
                                     operator_selection_bytes=operator_selection_bytes,
                                     expected_operator_selection_sha256=expected_operator_selection_sha256,
                                     capsule_bytes=capsule_bytes, expected_capsule_sha256=expected_capsule_sha256,
                                     repository_root=repository_root)
    runtime_selection = parse(runtime_selection_bytes)
    need(selected["record_status"] == runtime_selection["record_status"], "bootstrap_record_status_mismatch")
    probe_bytes = runtime.observation.safe._read_regular(ROOT / PROBE_PATH)
    runtime._bound(probe_bytes, selected["probe"], "bootstrap_probe_source_mismatch")
    by_path = {row["path"]: row for row in runtime_selection["files"]}
    landmark = by_path.get(STDLIB + "/os.py", {})
    need(landmark.get("role") == "stdlib" and landmark.get("format") == "python"
         and landmark.get("size_bytes", 0) > 0, "bootstrap_prefix_landmark_missing")
    need(any(row["path"].startswith(DYNLIB + "/") and row["format"] == "elf"
             and row["role"] == "stdlib" for row in runtime_selection["files"]), "bootstrap_dynload_anchor_missing")
    modules = _modules(selected, runtime_selection, payload, report["native_objects"])
    resources = _resources(runtime_selection, payload)
    phases = {"worker": list(probe.WORKER_MODULES), "collector": list(probe.COLLECTOR_MODULES)}
    bindings = {"runtime_selection_sha256": expected_runtime_selection_sha256,
                "operator_selection_sha256": expected_operator_selection_sha256,
                "capsule_sha256": expected_capsule_sha256,
                "bootstrap_selection_sha256": expected_bootstrap_selection_sha256}
    contract_record = {"record_type": "required_gate_idempotence_bootstrap_contract_v0",
                       "profile": PROFILE, **bindings, "modules": modules,
                       "resources": resources, "phases": phases}
    for phase in phases:
        probe._validate_contract(contract_record, phase)
    contract = canonical_bytes(contract_record)
    files, contents = _layout(runtime_selection, report, payload, contract, probe_bytes)
    launches = [{"phase": phase,
                 "argv": [LOADER, "--inhibit-cache", "--library-path", "/runtime/native", INTERPRETER,
                          "-I", "-S", "-B", PROBE_VIRTUAL, "--phase", phase],
                 "environment": dict(ENVIRONMENT), "working_directory": "/empty", "limits": dict(LIMITS)}
                for phase in ("worker", "collector")]
    plan = {"record_type": "required_gate_idempotence_bootstrap_plan_v0", "profile": PROFILE,
            "record_status": selected["record_status"], "bindings": bindings,
            "files": files, "empty_directories": ["/empty"], "modules": modules,
            "resources": resources, "phases": phases, "launches": launches,
            "containment_requirements": {
                "installed_before_first_exec": True, "filesystem_root": "exact_materialized_view",
                "filesystem_read_only": True, "ambient_host_files": "unavailable",
                "network": "denied", "unrelated_descriptors": "closed",
                "native_provider_bytes": "independently_confirmed_by_contained_runner",
                "dynamic_python_and_resource_reads": "independently_bound_by_contained_runner",
                "limits": "enforced_by_parent", "operator_applications": "forbidden",
                "receipt_authority": "diagnostic_only"}, **BOUNDARY}
    encoded = canonical_bytes(plan)
    need(len(encoded) <= runtime.CONTROL_LIMIT, "bootstrap_plan_size_limit")
    # Ensure the generated plan also obeys the bounded JSON parser's limits.
    parse(encoded)
    prepared = object.__new__(PreparedBootstrap)
    object.__setattr__(prepared, "inputs", tuple(sorted({
        "runtime_selection_bytes": runtime_selection_bytes,
        "expected_runtime_selection_sha256": expected_runtime_selection_sha256,
        "operator_selection_bytes": operator_selection_bytes,
        "expected_operator_selection_sha256": expected_operator_selection_sha256,
        "capsule_bytes": capsule_bytes, "expected_capsule_sha256": expected_capsule_sha256,
        "bootstrap_selection_bytes": bootstrap_selection_bytes,
        "expected_bootstrap_selection_sha256": expected_bootstrap_selection_sha256,
        "repository_root": repository_root}.items())))
    object.__setattr__(prepared, "plan_bytes", encoded)
    object.__setattr__(prepared, "contents", tuple(sorted(contents.items())))
    object.__setattr__(prepared, "_admission", _ADMISSION)
    return prepared


def prepare_bootstrap(**kwargs) -> PreparedBootstrap:
    try:
        return _prepare(**kwargs)
    except (runtime.CapsuleError, runtime.observation.VerificationError,
            runtime.observation.safe.ContractError, probe.ProbeError) as exc:
        raise BootstrapError(exc.code) from exc


def _report(prepared: PreparedBootstrap) -> dict:
    plan = parse(prepared.plan_bytes)
    return {"record_type": "required_gate_idempotence_bootstrap_verification_v0",
            "status": "accepted", "ok": True, "record_status": plan["record_status"],
            "plan_sha256": sha(prepared.plan_bytes), "plan_size_bytes": len(prepared.plan_bytes),
            "bindings": plan["bindings"], "bootstrap_plan_verified": True,
            "bootstrap_view_bytes_verified": False, "view_file_count": len(plan["files"]),
            "view_size_bytes": sum(row["size_bytes"] for row in plan["files"]),
            "module_targets": list(probe.MODULE_TARGETS), "module_bindings": plan["modules"],
            "resource_bindings": plan["resources"],
            "interpreter_module_declarations": [row["name"] for row in plan["modules"]
                                                if row["kind"] in {"builtin", "frozen"}],
            "outstanding": ["pre_exec_filesystem_containment", "contained_bootstrap_execution",
                            "dynamic_import_and_dlopen_binding", "actual_loader_resolution",
                            "host_containment_review", "observed_launch_integration", "separate_owner_authorization"],
            **BOUNDARY}


def verify_bootstrap_plan(*, plan_bytes, expected_plan_sha256, **kwargs) -> dict:
    need(type(plan_bytes) is bytes and sha(plan_bytes) == expected_plan_sha256, "bootstrap_plan_digest_mismatch")
    parse(plan_bytes)
    prepared = prepare_bootstrap(**kwargs)
    need(plan_bytes == prepared.plan_bytes, "bootstrap_plan_reconstruction_mismatch")
    return _report(prepared)


def _admitted(prepared: PreparedBootstrap) -> PreparedBootstrap:
    need(type(prepared) is PreparedBootstrap and getattr(prepared, "_admission", None) is _ADMISSION,
         "bootstrap_preparation_required")
    checked = prepare_bootstrap(**dict(prepared.inputs))
    need(checked.plan_bytes == prepared.plan_bytes and checked.contents == prepared.contents,
         "bootstrap_prepared_bytes_mismatch")
    return checked


def _verify_view(root_fd: int, files: list[dict], empty_directories: list[str]) -> None:
    selected = {row["path"].lstrip("/"): row for row in files}
    empty = {path.lstrip("/") for path in empty_directories}
    directories = set(empty)
    for path in [*selected, *empty]:
        directories.update(str(parent) for parent in Path(path).parents if str(parent) != ".")
    seen_files, seen_dirs = set(), set()

    def walk(fd: int, prefix: str):
        before = os.fstat(fd)
        need(stat.S_ISDIR(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o700,
             "bootstrap_materialized_directory_invalid")
        with os.scandir(fd) as entries:
            for entry in entries:
                path = prefix + entry.name
                need(runtime.observation.path_ok(path), "bootstrap_materialized_path_invalid")
                info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    need(path in directories and not prefix.rstrip("/") in empty,
                         "bootstrap_materialized_inventory_mismatch")
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                    try:
                        need(runtime._identity(info) == runtime._identity(os.fstat(child)), "bootstrap_view_changed")
                        seen_dirs.add(path)
                        walk(child, path + "/")
                    finally:
                        os.close(child)
                else:
                    need(path in selected and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                         and stat.S_IMODE(info.st_mode) == 0o400, "bootstrap_materialized_file_invalid")
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
                    try:
                        need(runtime._identity(info) == runtime._identity(os.fstat(child)), "bootstrap_view_changed")
                        raw = runtime._read_fd(child, runtime.FILE_LIMIT)
                    finally:
                        os.close(child)
                    runtime._bound(raw, selected[path], "bootstrap_materialized_digest_mismatch")
                    seen_files.add(path)
        need(runtime._identity(before) == runtime._identity(os.fstat(fd)), "bootstrap_view_changed")

    walk(root_fd, "")
    need(seen_files == set(selected) and seen_dirs == directories, "bootstrap_materialized_inventory_mismatch")


def materialize_bootstrap(prepared: PreparedBootstrap, *, output_directory: Path) -> dict:
    prepared = _admitted(prepared)
    report = _report(prepared)
    plan = parse(prepared.plan_bytes)
    directory = None
    completed = []
    try:
        directory = runtime.acquisition._Directory(output_directory)
        arguments = dict(prepared.inputs)
        for name, raw in (("bootstrap_selection.json", arguments["bootstrap_selection_bytes"]),
                          ("runtime_selection.json", arguments["runtime_selection_bytes"]),
                          ("operator_selection.json", arguments["operator_selection_bytes"]),
                          ("plan.json", prepared.plan_bytes)):
            directory.write(name, raw)
        directory.write("materialization_start.json", canonical_bytes({
            "record_type": "required_gate_idempotence_bootstrap_materialization_v0",
            "status": "started", "plan_sha256": report["plan_sha256"], "automatic_cleanup": False, **BOUNDARY}))
        for path, raw in prepared.contents:
            relative = "rootfs" + path
            fd = directory.create(relative)
            try:
                directory.append(fd, raw)
                os.fchmod(fd, 0o400)
                os.fsync(fd)
            finally:
                os.close(fd)
            completed.append({"path": relative, "sha256": sha(raw), "size_bytes": len(raw), "mode": "0400"})
        for path in plan["empty_directories"]:
            parent, name = directory._parent("rootfs" + path)
            try:
                os.mkdir(name, 0o700, dir_fd=parent)
                os.fsync(parent)
            finally:
                os.close(parent)
        root_fd = os.open("rootfs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory.fd)
        try:
            _verify_view(root_fd, plan["files"], plan["empty_directories"])
        finally:
            os.close(root_fd)
        runtime._same_destination(directory.fd, output_directory)
        result = {**report, "record_type": "required_gate_idempotence_bootstrap_materialization_v0",
                  "status": "materialized", "bootstrap_view_bytes_verified": True,
                  "execution_permissions_added": False, "materialized_files": completed}
        directory.write("materialization.json", canonical_bytes(result))
        return result
    except BaseException as exc:
        code = getattr(exc, "code", "bootstrap_materialization_failed")
        if directory is not None:
            try:
                directory.write("materialization.incomplete.json", canonical_bytes({
                    "record_type": "required_gate_idempotence_bootstrap_materialization_v0", "status": "incomplete",
                    "errors": [code], "completed_files": completed, "plan_sha256": report["plan_sha256"],
                    "bootstrap_view_bytes_verified": False, "automatic_cleanup": False, **BOUNDARY}))
            except BaseException:
                pass
        raise BootstrapError(code) from exc
    finally:
        if directory is not None:
            directory.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "check", "materialize"):
        sub = commands.add_parser(command)
        for name in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection"):
            sub.add_argument("--" + name, type=Path, required=True)
            sub.add_argument("--" + name + "-sha256", required=True)
        sub.add_argument("--repository-root", type=Path)
        if command != "prepare":
            sub.add_argument("--plan", type=Path, required=True)
            sub.add_argument("--plan-sha256", required=True)
        if command == "materialize":
            sub.add_argument("--output-directory", type=Path, required=True)
        else:
            sub.add_argument("--output", type=Path, required=command == "prepare")
    args = parser.parse_args(argv)
    output_parent = None
    try:
        if getattr(args, "output", None) is not None:
            output_parent, output_name = runtime.observation.safe._output_preflight(args.output)
        common = {"repository_root": args.repository_root}
        for name in ("runtime_selection", "operator_selection", "capsule", "bootstrap_selection"):
            maximum = runtime.ARCHIVE_LIMIT if name == "capsule" else runtime.CONTROL_LIMIT
            common[name + "_bytes"] = runtime.read_regular(getattr(args, name), maximum)
            common["expected_" + name + "_sha256"] = getattr(args, name + "_sha256")
        if args.command == "prepare":
            prepared = prepare_bootstrap(**common)
            runtime.observation.safe._write_output(output_parent, output_name, prepared.plan_bytes)
            result = _report(prepared)
        else:
            plan_bytes = runtime.read_regular(args.plan, runtime.CONTROL_LIMIT)
            result = verify_bootstrap_plan(**common, plan_bytes=plan_bytes, expected_plan_sha256=args.plan_sha256)
            if args.command == "materialize":
                result = materialize_bootstrap(prepare_bootstrap(**common), output_directory=args.output_directory)
            elif output_parent is not None:
                runtime.observation.safe._write_output(output_parent, output_name, canonical_bytes(result))
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (BootstrapError, runtime.CapsuleError, runtime.observation.VerificationError,
            runtime.observation.safe.ContractError, runtime.acquisition.AcquisitionError) as exc:
        result = {"record_type": "required_gate_idempotence_bootstrap_verification_v0",
                  "status": "rejected", "ok": False, "errors": [exc.code],
                  "bootstrap_plan_verified": False, "bootstrap_view_bytes_verified": False, **BOUNDARY}
        sys.stdout.buffer.write(canonical_bytes(result))
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        sys.stdout.buffer.write(canonical_bytes({"status": "rejected", "ok": False,
                                                "errors": ["bootstrap_operation_failed"], **BOUNDARY}))
        return 1
    finally:
        if output_parent is not None:
            os.close(output_parent)


if __name__ == "__main__":
    raise SystemExit(main())
