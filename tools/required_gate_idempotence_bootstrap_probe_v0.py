#!/usr/bin/env python3
"""Fixed finite bootstrap diagnostics for a future contained runtime runner.

This program is not a launcher, containment mechanism or qualification grant.
It must only be run inside the separately reviewed launch view. Its observations
are self-reported diagnostics, not authenticated evidence of prior file reads.
It never calls the selected sanitizer or any acquisition entry point.
"""
from __future__ import annotations

# Keep startup inspection ahead of imports resolved from the runtime file tree.
import posix
import sys

PREFIX = "/runtime/python"
INTERPRETER_PATH = PREFIX + "/bin/python3.11"
PROBE_PATH = "/runtime/bootstrap/probe.py"
CONTRACT_PATH = "/runtime/bootstrap/contract.json"
STDLIB_ROOT = PREFIX + "/lib/python3.11"
DYNLIB_ROOT = STDLIB_ROOT + "/lib-dynload"
SITE_PACKAGES_ROOT = STDLIB_ROOT + "/site-packages"
REPOSITORY_TOOLS_ROOT = "/runtime/repository/tools"
SEARCH_ROOTS = (STDLIB_ROOT, DYNLIB_ROOT, SITE_PACKAGES_ROOT, REPOSITORY_TOOLS_ROOT)
INITIAL_SYS_PATH = (PREFIX + "/lib/python311.zip", STDLIB_ROOT, DYNLIB_ROOT)
EXPECTED_ENVIRONMENT = {"LC_ALL": "C", "TZ": "UTC"}
WORKER_MODULES = tuple(sorted((
    "_ctypes", "argparse", "base64", "collections.abc", "ctypes", "dataclasses",
    "datetime", "enum", "errno", "fcntl", "hashlib", "json", "logging", "math",
    "os", "pathlib", "platform", "resource", "statistics", "sys", "types",
    "typing", "unicodedata", "required_gate_idempotence_worker_v0",
)))
COLLECTOR_MODULES = tuple(sorted((
    "check_required_gate_suite_contract_v0",
    "check_required_gate_idempotence_observation_v0",
    "pulsemech_compute_standalone_runtime_v0",
    "pulsemech_compute_binding_analyzer_core_v0",
    "build_pulsemech_compute_planned_observed_relation_v0",
    "check_pulsemech_compute_runtime_observation_packet_v0",
    "acquire_required_gate_idempotence_v0", "required_gate_idempotence_process_v0",
    "yaml", "jsonschema", "referencing", "rpds", "rpds.rpds", "attr", "attrs",
    "jsonschema_specifications", "typing_extensions",
)))
MODULE_TARGETS = tuple(sorted(set(WORKER_MODULES) | set(COLLECTOR_MODULES)))
MODULE_NAMES = tuple(sorted(set(MODULE_TARGETS) | {
    ".".join(name.split(".")[:index])
    for name in MODULE_TARGETS for index in range(1, len(name.split(".")))
}))
DRAFT = "https://json-schema.org/draft/2020-12/"
REQUIRED_RESOURCE_IDS = tuple(sorted((DRAFT + "schema", *(DRAFT + "meta/" + name for name in (
    "core", "applicator", "unevaluated", "validation", "meta-data", "format-annotation", "content",
)))))
HASH_FIELDS = ("runtime_selection_sha256", "operator_selection_sha256", "capsule_sha256",
               "bootstrap_selection_sha256")
CONTROL_LIMIT = 4 * 1024 * 1024
REPORT_LIMIT = 64 * 1024
FILE_LIMIT = 128 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
FORBIDDEN_OPERATOR_NAMES = frozenset((
    "epf_hazard_features", "epf_hazard_forecast", "epf_hazard_field_spec", "epf_hazard_adapter",
))
BOUNDARY = {
    "diagnostic_only": True, "runtime_execution_authenticated": False,
    "restored_bootstrap_qualified": False, "loader_resolution_verified": False,
    "python_import_closure_verified": False, "host_environment_qualified": False,
    "runtime_closure_verified": False, "execution_ready": False,
    "execution_authorized": False, "observed_acquisition_supported": False,
    "property_semantics_verified": False, "metric_pass": None,
    "actual_reference_claimed": False, "production_gate_eligible": False,
    "authority_effect": "none", "operator_applications": 0, "model_calls": 0,
}


class ProbeError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise ProbeError(code)


def _hash_ok(value):
    return type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _path_ok(value):
    return (type(value) is str and value.startswith("/") and 0 < len(value) <= 500
            and all(part and part not in {".", ".."} and all(
                char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" for char in part)
                    for part in value[1:].split("/")))


def _read_regular(path, limit):
    """Bounded descriptor-relative reads; no links or path normalization."""
    _need(_path_ok(path), "probe_file_path_invalid")
    directory = posix.open("/", posix.O_RDONLY | posix.O_DIRECTORY | posix.O_CLOEXEC)
    descriptor = None
    try:
        parts = path[1:].split("/")
        for component in parts[:-1]:
            child = posix.open(component, posix.O_RDONLY | posix.O_DIRECTORY | posix.O_NOFOLLOW
                               | posix.O_CLOEXEC, dir_fd=directory)
            posix.close(directory)
            directory = child
        descriptor = posix.open(parts[-1], posix.O_RDONLY | posix.O_NOFOLLOW | posix.O_NONBLOCK
                                | posix.O_CLOEXEC, dir_fd=directory)
        before = posix.fstat(descriptor)
        _need(before.st_mode & 0o170000 == 0o100000 and before.st_nlink == 1
              and 0 <= before.st_size <= limit, "probe_file_type_or_size_invalid")
        result = bytearray()
        while True:
            block = posix.read(descriptor, min(65536, limit + 1 - len(result)))
            if not block:
                break
            result.extend(block)
            _need(len(result) <= limit, "probe_file_size_limit")
        after = posix.fstat(descriptor)
        keys = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        _need(len(result) == before.st_size and all(getattr(before, key) == getattr(after, key)
                                                   for key in keys), "probe_file_changed")
        return bytes(result)
    except OSError as exc:
        raise ProbeError("probe_file_unavailable") from exc
    finally:
        if descriptor is not None:
            posix.close(descriptor)
        posix.close(directory)


def _import_module(name):
    _need(name in MODULE_NAMES, "probe_module_not_selected")
    __import__(name)
    _need(name in sys.modules, "probe_module_missing")
    return sys.modules[name]


def _canonical(value):
    return (_import_module("json").dumps(value, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def _sha(raw):
    return _import_module("hashlib").sha256(raw).hexdigest()


def _parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_LIMIT, "probe_control_size_limit")

    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "probe_json_duplicate_key")
            result[key] = value
        return result

    def finite(text):
        value = float(text)
        _need(-float("inf") < value < float("inf"), "probe_json_nonfinite")
        return value

    def constant(_text):
        raise ProbeError("probe_json_nonfinite")

    try:
        result = _import_module("json").loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                                               parse_float=finite, parse_constant=constant)
        count = 0
        pending = [(result, 0)]
        while pending:
            value, depth = pending.pop()
            count += 1
            _need(depth <= 64 and count <= 100000, "probe_json_complexity_limit")
            if type(value) is dict:
                pending.extend((child, depth + 1) for child in value.values())
                pending.extend((key, depth + 1) for key in value)
            elif type(value) is list:
                pending.extend((child, depth + 1) for child in value)
            elif type(value) is str:
                _need(not any(0xD800 <= ord(char) <= 0xDFFF for char in value), "probe_json_surrogate")
        _need(type(result) is dict, "probe_json_object_required")
        return result
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ProbeError):
            raise
        raise ProbeError("probe_json_invalid") from exc


def _startup():
    """Inspect startup state before adding any explicit package/repository path."""
    _need(sys.platform == "linux" and posix.uname().machine == "x86_64", "probe_platform_mismatch")
    _need(sys.implementation.name == "cpython" and tuple(sys.version_info[:3]) == (3, 11, 16),
          "probe_python_mismatch")
    flags = {name: getattr(sys.flags, name) for name in (
        "isolated", "ignore_environment", "no_site", "no_user_site", "dont_write_bytecode", "safe_path")}
    _need(all(value == 1 for value in flags.values()), "probe_startup_flags_mismatch")
    _need(all(getattr(sys, name) == PREFIX for name in (
        "prefix", "exec_prefix", "base_prefix", "base_exec_prefix")), "probe_prefix_mismatch")
    _need(sys.executable == INTERPRETER_PATH, "probe_executable_mismatch")
    _need(type(sys.path) is list and tuple(sys.path) == INITIAL_SYS_PATH, "probe_initial_sys_path_mismatch")
    _need(posix.getcwd() == "/empty", "probe_working_directory_mismatch")
    try:
        environment = {key.decode("ascii"): value.decode("ascii") for key, value in posix.environ.items()}
    except (AttributeError, UnicodeError) as exc:
        raise ProbeError("probe_environment_mismatch") from exc
    _need(environment == EXPECTED_ENVIRONMENT, "probe_environment_mismatch")
    record = {"python_implementation": "CPython", "python_version": "3.11.16",
              "architecture": "x86_64", "os_name": "Linux", "prefix": sys.prefix,
              "exec_prefix": sys.exec_prefix, "base_prefix": sys.base_prefix,
              "base_exec_prefix": sys.base_exec_prefix, "executable": sys.executable,
              "working_directory": "/empty", "initial_sys_path": list(sys.path),
              "environment": environment, "flags": flags}
    sys.path[:] = SEARCH_ROOTS
    unicode_module = _import_module("unicodedata")
    _need(unicode_module.unidata_version == "14.0.0", "probe_unicode_version_mismatch")
    record.update(unicode_version=unicode_module.unidata_version, probe_sys_path=list(sys.path))
    return record


def _validate_contract(contract, phase):
    _need(type(phase) is str and phase in {"worker", "collector"}, "probe_phase_invalid")
    _need(type(contract) is dict and set(contract) == {
        "record_type", "profile", *HASH_FIELDS, "modules", "resources", "phases"}, "probe_contract_shape")
    _need(contract["record_type"] == "required_gate_idempotence_bootstrap_contract_v0"
          and contract["profile"] == "restored_bootstrap_plan_v0", "probe_contract_profile")
    _need(all(_hash_ok(contract[key]) for key in HASH_FIELDS), "probe_contract_digest_invalid")
    _need(type(contract["phases"]) is dict
          and contract["phases"] == {"worker": list(WORKER_MODULES), "collector": list(COLLECTOR_MODULES)},
          "probe_phase_roster_mismatch")
    modules = contract["modules"]
    _need(type(modules) is list and len(modules) == len(MODULE_NAMES), "probe_module_roster_mismatch")
    names, module_paths = [], []
    total = 0
    for row in modules:
        _need(type(row) is dict and set(row) == {"name", "kind", "path", "sha256", "size_bytes"},
              "probe_module_shape")
        _need(type(row["name"]) is str and row["name"] in MODULE_NAMES
              and type(row["kind"]) is str and row["kind"] in {"source", "extension", "builtin", "frozen"}
              and _hash_ok(row["sha256"]) and type(row["size_bytes"]) is int
              and 0 <= row["size_bytes"] <= FILE_LIMIT, "probe_module_descriptor_invalid")
        names.append(row["name"])
        if row["kind"] in {"builtin", "frozen"}:
            _need(row["path"] is None and row["size_bytes"] > 0, "probe_interpreter_binding_invalid")
        else:
            path = row["path"]
            _need(_path_ok(path) and any(path.startswith(root + "/") for root in SEARCH_ROOTS),
                  "probe_module_path_invalid")
            _need((row["kind"] == "source" and path.endswith(".py"))
                  or (row["kind"] == "extension" and path.endswith(".so")), "probe_module_format_invalid")
            module_paths.append(path)
            total += row["size_bytes"]
    _need(names == list(MODULE_NAMES) and len(module_paths) == len(set(module_paths)),
          "probe_module_roster_mismatch")
    resources = contract["resources"]
    _need(type(resources) is list and len(resources) == len(REQUIRED_RESOURCE_IDS), "probe_resource_roster_mismatch")
    identifiers, paths = [], []
    for row in resources:
        _need(type(row) is dict and set(row) == {"path", "sha256", "size_bytes", "schema_id"},
              "probe_resource_shape")
        _need(_path_ok(row["path"]) and row["path"].endswith(".json") and row["path"].startswith(
            SITE_PACKAGES_ROOT + "/jsonschema_specifications/schemas/")
              and _hash_ok(row["sha256"]) and type(row["size_bytes"]) is int
              and 0 < row["size_bytes"] <= CONTROL_LIMIT and row["schema_id"] in REQUIRED_RESOURCE_IDS,
              "probe_resource_descriptor_invalid")
        identifiers.append(row["schema_id"])
        paths.append(row["path"])
        total += row["size_bytes"]
    _need(identifiers == list(REQUIRED_RESOURCE_IDS) and len(paths) == len(set(paths))
          and not (set(paths) & set(module_paths)), "probe_resource_roster_mismatch")
    _need(total <= TOTAL_LIMIT, "probe_selected_size_limit")
    return {row["name"]: row for row in modules}


def _bound(raw, row):
    _need(len(raw) == row["size_bytes"] and _sha(raw) == row["sha256"], "probe_file_binding_mismatch")


def _module_observation(row, interpreter_raw, preloaded):
    name, kind = row["name"], row["kind"]
    if kind in {"source", "extension"}:
        _bound(_read_regular(row["path"], FILE_LIMIT), row)
    else:
        _bound(interpreter_raw, row)
    module = _import_module(name)
    specification = getattr(module, "__spec__", None)
    _need(specification is not None and getattr(specification, "name", None) == name, "probe_module_spec_mismatch")
    if kind == "builtin":
        _need(name in sys.builtin_module_names and getattr(specification, "origin", None) == "built-in",
              "probe_builtin_kind_mismatch")
    elif kind == "frozen":
        import _imp
        _need(_imp.is_frozen(name) and getattr(specification, "origin", None) == "frozen", "probe_frozen_kind_mismatch")
    else:
        _need(getattr(specification, "origin", None) == row["path"]
              and getattr(module, "__file__", None) == row["path"],
              "probe_module_origin_mismatch")
        loader_name = type(getattr(specification, "loader", None)).__name__
        _need(loader_name == ("SourceFileLoader" if kind == "source" else "ExtensionFileLoader"),
              "probe_module_loader_mismatch")
        _bound(_read_regular(row["path"], FILE_LIMIT), row)
    return {"name": name, "kind": kind, "path": row["path"], "sha256": row["sha256"],
            "size_bytes": row["size_bytes"], "observed_origin": specification.origin,
            "present_before_phase": preloaded}


def _finite_checks(phase):
    value = {"z": [1, True, None], "n": -0.0, "a": {"unicode": "\u00e9"}}
    expected = b'{"a":{"unicode":"\\u00e9"},"n":-0.0,"z":[1,true,null]}\n'
    _need(_canonical(value) == expected, "probe_canonical_json_failed")
    _need(_sha(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
          "probe_sha256_failed")
    unicode_module = _import_module("unicodedata")
    _need(unicode_module.unidata_version == "14.0.0" and unicode_module.normalize("NFC", "e\u0301") == "\u00e9"
          and unicode_module.category("\u00e9") == "Ll", "probe_unicode_failed")
    result = {"canonical_json": True, "sha256": True, "unicode": True}
    if phase == "collector":
        validator_type = _import_module("jsonschema").Draft202012Validator
        schema = {"$schema": DRAFT + "schema", "type": "object", "required": ["value"],
                  "properties": {"value": {"type": "integer", "minimum": 0}}, "additionalProperties": False}
        validator_type.check_schema(schema)
        validator = validator_type(schema)
        _need(validator.is_valid({"value": 1}) and not validator.is_valid({"value": True})
              and not validator.is_valid({"value": -1}) and not validator.is_valid({"value": 1, "extra": 2}),
              "probe_jsonschema_failed")
        result["draft202012_validator"] = True
    return result


class _DenyOperatorImports:
    def find_spec(self, fullname, path=None, target=None):
        _need(fullname.rsplit(".", 1)[-1] not in FORBIDDEN_OPERATOR_NAMES, "probe_operator_import_forbidden")
        return None


def _run_phase(contract, phase, startup):
    by_name = _validate_contract(contract, phase)
    _need(not any(name.rsplit(".", 1)[-1] in FORBIDDEN_OPERATOR_NAMES for name in sys.modules),
          "probe_operator_import_forbidden")
    targets = set(contract["phases"][phase]) | {"hashlib", "json", "unicodedata"}
    targets.update(".".join(name.split(".")[:index])
                   for name in tuple(targets) for index in range(1, len(name.split("."))))
    preloaded = set(sys.modules)
    interpreter_raw = _read_regular(INTERPRETER_PATH, FILE_LIMIT)
    observations = []
    guard = _DenyOperatorImports()
    sys.meta_path.insert(0, guard)
    try:
        for name in sorted(targets):
            observations.append(_module_observation(by_name[name], interpreter_raw, name in preloaded))
        resources = []
        for row in contract["resources"]:
            raw = _read_regular(row["path"], CONTROL_LIMIT)
            _bound(raw, row)
            document = _parse(raw)
            _need(document.get("$id") == row["schema_id"] and document.get("$schema") == DRAFT + "schema",
                  "probe_resource_identity_mismatch")
            resources.append(dict(row))
        finite = _finite_checks(phase)
        _need(not any(name.rsplit(".", 1)[-1] in FORBIDDEN_OPERATOR_NAMES for name in sys.modules),
              "probe_operator_import_forbidden")
        _need(type(sys.path) is list and all(type(path) is str and path in SEARCH_ROOTS for path in sys.path)
              and set(sys.path) == set(SEARCH_ROOTS), "probe_post_phase_sys_path_mismatch")
    finally:
        if guard in sys.meta_path:
            sys.meta_path.remove(guard)
    return {"record_type": "required_gate_idempotence_bootstrap_diagnostic_v0",
            "profile": "restored_bootstrap_plan_v0", "status": "completed", "phase": phase,
            **{key: contract[key] for key in HASH_FIELDS}, "startup": startup,
            "module_observations": observations, "resource_observations": resources,
            "finite_checks": finite, "post_phase_sys_path": list(sys.path), **BOUNDARY}


def run_phase(contract, phase):
    """Run only one fixed diagnostic phase; every success remains diagnostic."""
    return _run_phase(contract, phase, _startup())


def _rejection(code):
    # No import or untrusted input interpolation is required on startup failure.
    _need(type(code) is str and code and all(char in "abcdefghijklmnopqrstuvwxyz_0123456789" for char in code),
          "probe_error_code_invalid")
    return ('{"actual_reference_claimed":false,"authority_effect":"none","diagnostic_only":true,'
            '"errors":["' + code + '"],"execution_authorized":false,"execution_ready":false,'
            '"host_environment_qualified":false,"loader_resolution_verified":false,"metric_pass":null,'
            '"model_calls":0,"observed_acquisition_supported":false,"operator_applications":0,'
            '"production_gate_eligible":false,"property_semantics_verified":false,'
            '"python_import_closure_verified":false,'
            '"record_type":"required_gate_idempotence_bootstrap_diagnostic_v0",'
            '"restored_bootstrap_qualified":false,"runtime_closure_verified":false,'
            '"runtime_execution_authenticated":false,"status":"rejected"}\n').encode("ascii")


def main(argv=None):
    try:
        arguments = sys.argv[1:] if argv is None else argv
        _need(type(arguments) is list and len(arguments) == 2 and all(type(value) is str for value in arguments)
              and arguments[0] == "--phase"
              and arguments[1] in {"worker", "collector"}, "probe_arguments_invalid")
        startup = _startup()
        contract = _parse(_read_regular(CONTRACT_PATH, CONTROL_LIMIT))
        result = _run_phase(contract, arguments[1], startup)
        raw = _canonical(result)
        _need(len(raw) <= REPORT_LIMIT, "probe_report_size_limit")
        sys.stdout.buffer.write(raw)
        return 0
    except ProbeError as exc:
        sys.stdout.buffer.write(_rejection(exc.code))
        return 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, RecursionError, RuntimeError):
        sys.stdout.buffer.write(_rejection("probe_operation_failed"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
