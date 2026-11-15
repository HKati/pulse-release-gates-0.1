#!/usr/bin/env python3
"""Synthetic bootstrap planning; selected runtime and operator bytes stay inert."""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SELF = "tests/test_required_gate_idempotence_bootstrap_v0.py"
TOOL = ROOT / "tools/required_gate_idempotence_bootstrap_v0.py"
PROBE = "tools/required_gate_idempotence_bootstrap_probe_v0.py"
INERT = b'raise RuntimeError("SYNTHETIC_BOOTSTRAP_PROVIDER_MUST_NOT_EXECUTE")\n'


def module(name, relative):
    if name not in sys.modules:
        tools = str(ROOT / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        specification = importlib.util.spec_from_file_location(name, ROOT / relative)
        assert specification is not None and specification.loader is not None
        loaded = importlib.util.module_from_spec(specification)
        sys.modules[name] = loaded
        specification.loader.exec_module(loaded)
    return sys.modules[name]


def bootstrap():
    return module("idempotence_bootstrap_under_test", "tools/required_gate_idempotence_bootstrap_v0.py")


def probe():
    return module("idempotence_bootstrap_probe_under_test", PROBE)


def runtime_examples():
    return module("bootstrap_runtime_examples", "tests/test_required_gate_idempotence_runtime_v0.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def boundaries(record):
    for name in ("execution_ready", "execution_authorized", "runtime_closure_verified",
                 "production_gate_eligible"):
        assert record[name] is False
    assert record["authority_effect"] == "none"
    assert record.get("metric_pass") is None
    for name in ("host_environment_qualified", "python_import_closure_verified",
                 "loader_resolution_verified", "restored_runtime_executed",
                 "observed_acquisition_supported", "actual_reference_claimed"):
        assert record.get(name, False) is False


class Example:
    def __init__(self):
        self.runtime = runtime_examples().Example()
        self.site = self.runtime.selection["python"]["site_packages_root"]
        self.stdlib = self.runtime.selection["python"]["stdlib_root"]
        self.resident = [{"name": "sys", "kind": "builtin"}, {"name": "os", "kind": "frozen"}]
        resident = {row["name"] for row in self.resident}
        self.module_paths = {}
        for name in probe().MODULE_TARGETS:
            if name in resident:
                continue
            relative = name.replace(".", "/")
            if name in {"_ctypes", "rpds.rpds"}:
                path = (self.stdlib + "/lib-dynload/_ctypes.cpython-311-x86_64-linux-gnu.so"
                        if name == "_ctypes" else self.site + "/rpds/rpds.cpython-311-x86_64-linux-gnu.so")
                self.runtime.add(path, "stdlib" if name == "_ctypes" else "site_package", "elf",
                                 runtime_examples().elf(needed=("libc.so.6",)))
                self.runtime.selection["native_bindings"].append({
                    "consumer": path, "kind": "needed", "name": "libc.so.6", "provider": self.runtime.libc})
                self.module_paths[name] = path
                if name == "_ctypes":
                    self.extension = path
                continue
            candidates = [
                self.stdlib + "/" + relative + ".py",
                self.stdlib + "/" + relative + "/__init__.py",
                self.site + "/" + relative + ".py",
                self.site + "/" + relative + "/__init__.py",
                "repository/tools/" + relative + ".py",
            ]
            existing = [path for path in candidates if path in self.runtime.payload]
            if existing:
                assert len(existing) == 1, (name, existing)
                self.module_paths[name] = existing[0]
                continue
            prefix = self.stdlib
            if "." in name and self.site + "/" + name.split(".")[0] + "/__init__.py" in self.runtime.payload:
                prefix = self.site
            path = prefix + "/" + relative + ".py"
            self.runtime.add(path, "site_package" if prefix == self.site else "stdlib", "python", INERT)
            self.module_paths[name] = path
        self.schema_paths = []
        for name in ("schema", "meta/core", "meta/applicator", "meta/unevaluated", "meta/validation",
                     "meta/meta-data", "meta/format-annotation", "meta/content"):
            path = self.site + "/jsonschema_specifications/schemas/draft202012/" + name + ".json"
            raw = encoded({"$id": "https://json-schema.org/draft/2020-12/" + name,
                           "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"})
            self.runtime.add(path, "site_package", "json", raw)
            self.schema_paths.append(path)
        probe_bytes = (ROOT / PROBE).read_bytes()
        self.selection = {
            "record_type": "required_gate_idempotence_bootstrap_selection_v0",
            "record_status": "example", "profile": "restored_bootstrap_plan_v0",
            "runtime_selection_sha256": digest(self.runtime.selection_bytes()),
            "operator_selection_sha256": digest(self.runtime.operator_bytes()),
            "capsule_sha256": "0" * 64,
            "probe": {"path": PROBE, "sha256": digest(probe_bytes), "size_bytes": len(probe_bytes)},
            "interpreter_modules": self.resident,
            "execution_ready": False, "execution_authorized": False,
            "runtime_closure_verified": False, "production_gate_eligible": False,
            "authority_effect": "none",
        }
        self.capsule = None

    def seal(self, root):
        self.capsule = self.runtime.build(self.runtime.stage(root))
        self.selection.update(runtime_selection_sha256=digest(self.runtime.selection_bytes()),
                              operator_selection_sha256=digest(self.runtime.operator_bytes()),
                              capsule_sha256=digest(self.capsule))
        return self

    def selection_bytes(self):
        return encoded(self.selection)

    def arguments(self):
        assert self.capsule is not None
        return {"runtime_selection_bytes": self.runtime.selection_bytes(),
                "expected_runtime_selection_sha256": digest(self.runtime.selection_bytes()),
                "operator_selection_bytes": self.runtime.operator_bytes(),
                "expected_operator_selection_sha256": digest(self.runtime.operator_bytes()),
                "capsule_bytes": self.capsule, "expected_capsule_sha256": digest(self.capsule),
                "bootstrap_selection_bytes": self.selection_bytes(),
                "expected_bootstrap_selection_sha256": digest(self.selection_bytes())}

    def prepare(self):
        return bootstrap().prepare_bootstrap(**self.arguments())

    def verify(self, plan_bytes):
        return bootstrap().verify_bootstrap_plan(**self.arguments(), plan_bytes=plan_bytes,
                                                 expected_plan_sha256=digest(plan_bytes))


@pytest.fixture(scope="module")
def valid(tmp_path_factory):
    example = Example().seal(tmp_path_factory.mktemp("bootstrap") / "source")
    prepared = example.prepare()
    return example, prepared


def test_prepared_plan_is_canonical_deterministic_and_not_execution(valid):
    example, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    assert encoded(plan) == prepared.plan_bytes
    assert example.prepare().plan_bytes == prepared.plan_bytes
    boundaries(plan)
    first = example.verify(prepared.plan_bytes)
    assert first == example.verify(prepared.plan_bytes)
    boundaries(first)


@pytest.mark.parametrize("argument", ["expected_runtime_selection_sha256", "expected_operator_selection_sha256",
                                      "expected_capsule_sha256", "expected_bootstrap_selection_sha256"])
def test_every_external_input_digest_is_required(valid, argument):
    example, _ = valid
    arguments = example.arguments()
    arguments[argument] = "0" * 64
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


def test_plan_digest_is_independently_required(valid):
    example, prepared = valid
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().verify_bootstrap_plan(**example.arguments(), plan_bytes=prepared.plan_bytes,
                                         expected_plan_sha256="0" * 64)


@pytest.mark.parametrize("field,value", [
    ("record_type", "other"), ("record_status", "selected"), ("profile", "other"),
    ("execution_ready", True), ("execution_authorized", True), ("runtime_closure_verified", True),
    ("production_gate_eligible", True), ("authority_effect", "release"),
    ("runtime_selection_sha256", "1" * 64), ("operator_selection_sha256", "1" * 64),
    ("capsule_sha256", "1" * 64), ("unexpected", "not allowed"),
])
def test_rehashed_selection_cannot_change_subject_or_boundary(valid, field, value):
    example, _ = valid
    arguments = example.arguments()
    selection = copy.deepcopy(example.selection)
    selection[field] = value
    raw = encoded(selection)
    arguments.update(bootstrap_selection_bytes=raw, expected_bootstrap_selection_sha256=digest(raw))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


@pytest.mark.parametrize("field,value", [("path", "tools/other_probe.py"), ("sha256", "1" * 64),
                                         ("size_bytes", 1), ("size_bytes", True), ("extra", False)])
def test_probe_selection_must_match_installed_fixed_probe(valid, field, value):
    example, _ = valid
    selection = copy.deepcopy(example.selection)
    selection["probe"][field] = value
    raw = encoded(selection)
    arguments = example.arguments()
    arguments.update(bootstrap_selection_bytes=raw, expected_bootstrap_selection_sha256=digest(raw))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


@pytest.mark.parametrize("rows", [
    [{"name": "sys", "kind": "builtin"}, {"name": "sys", "kind": "builtin"}],
    [{"name": "sys", "kind": "builtin"}, {"name": "sys", "kind": "frozen"}],
    [{"name": "../sys", "kind": "builtin"}], [{"name": "sys", "kind": "unknown"}],
    [{"name": "sys", "kind": "builtin", "trusted": True}],
])
def test_interpreter_module_declarations_are_closed_and_unambiguous(valid, rows):
    example, _ = valid
    selection = copy.deepcopy(example.selection)
    selection["interpreter_modules"] = rows
    raw = encoded(selection)
    arguments = example.arguments()
    arguments.update(bootstrap_selection_bytes=raw, expected_bootstrap_selection_sha256=digest(raw))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


@pytest.mark.parametrize("change", ["duplicate_key", "nonfinite", "not_object", "trailing_data"])
def test_bootstrap_selection_uses_strict_json(valid, change):
    example, _ = valid
    raw = example.selection_bytes()
    if change == "duplicate_key":
        raw = raw.replace(b'"record_status":"example"', b'"record_status":"example","record_status":"example"')
    elif change == "nonfinite":
        raw = raw.replace(b'"execution_ready":false', b'"execution_ready":NaN')
    elif change == "not_object":
        raw = b"[]\n"
    else:
        raw += b"{}"
    arguments = example.arguments()
    arguments.update(bootstrap_selection_bytes=raw, expected_bootstrap_selection_sha256=digest(raw))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


@pytest.mark.parametrize("change", ["missing", "source_and_package", "stdlib_and_site", "wrong_format"])
def test_fixed_module_targets_need_one_selected_provider(tmp_path, change):
    example = Example()
    name = "statistics"
    path = example.module_paths[name]
    if change == "missing":
        example.runtime.drop(path)
    elif change == "source_and_package":
        example.runtime.add(example.stdlib + "/statistics/__init__.py", "stdlib", "python", INERT)
    elif change == "stdlib_and_site":
        example.runtime.add(example.site + "/statistics.py", "site_package", "python", INERT)
    else:
        next(row for row in example.runtime.rows if row["path"] == path)["format"] = "data"
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


def test_selected_extension_and_required_schema_resources_cannot_be_omitted(tmp_path):
    example = Example()
    example.runtime.drop(example.extension)
    example.runtime.selection["native_bindings"] = [row for row in example.runtime.selection["native_bindings"]
                                                     if row["consumer"] != example.extension]
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


def test_cpython_prefix_landmark_is_required_even_for_declared_frozen_os(tmp_path):
    example = Example()
    example.runtime.drop(example.stdlib + "/os.py")
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


@pytest.mark.parametrize("name", ["_ctypes", "rpds.rpds"])
def test_native_python_extension_provider_must_be_a_shared_elf_object(tmp_path, name):
    example = Example()
    path = example.module_paths[name]
    example.runtime.replace(path, runtime_examples().elf(elf_type=2, needed=("libc.so.6",)))
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError, match="bootstrap_extension_type_invalid"):
        example.prepare()


@pytest.mark.parametrize("change", ["missing", "changed_id", "duplicate_id", "invalid_json", "wrong_format",
                                     "list_id", "mapping_id", "missing_dialect", "wrong_dialect"])
def test_schema_resource_roster_is_bound_to_selected_bytes(tmp_path, change):
    example = Example()
    path = example.schema_paths[0]
    if change == "missing":
        example.runtime.drop(path)
    elif change == "changed_id":
        example.runtime.replace(path, encoded({"$id": "https://example.invalid/unrelated"}))
    elif change == "duplicate_id":
        example.runtime.add(example.site + "/jsonschema_specifications/schemas/draft202012/duplicate.json",
                            "site_package", "json", example.runtime.payload[path])
    elif change == "invalid_json":
        example.runtime.replace(path, b"{not json}\n")
    elif change in {"list_id", "mapping_id"}:
        example.runtime.replace(path, encoded({"$id": [] if change == "list_id" else {"forged": "identity"}}))
    elif change in {"missing_dialect", "wrong_dialect"}:
        value = json.loads(example.runtime.payload[path])
        value.pop("$schema")
        if change == "wrong_dialect":
            value["$schema"] = "http://json-schema.org/draft-07/schema#"
        example.runtime.replace(path, encoded(value))
    else:
        next(row for row in example.runtime.rows if row["path"] == path)["format"] = "data"
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


def compiled_contract(prepared):
    plan = json.loads(prepared.plan_bytes)
    row = next(row for row in plan["files"] if row["origin"] == "contract")
    return json.loads(dict(prepared.contents)[row["path"]])


def test_generated_contract_and_probe_agree_when_schema_paths_have_different_order(tmp_path):
    example = Example()
    path = example.schema_paths[0]
    raw = example.runtime.payload[path]
    example.runtime.drop(path)
    example.runtime.add(example.site + "/jsonschema_specifications/schemas/draft202012/000-root.json",
                        "site_package", "json", raw)
    example.seal(tmp_path / "source")
    contract = compiled_contract(example.prepare())
    assert [row["path"] for row in contract["resources"]] != sorted(row["path"] for row in contract["resources"])
    for phase in ("worker", "collector"):
        assert set(probe()._validate_contract(contract, phase)) == set(probe().MODULE_NAMES)


@pytest.mark.parametrize("phase", ["worker", "collector"])
def test_generated_contract_is_accepted_by_its_fixed_diagnostic_consumer(valid, phase):
    _, prepared = valid
    contract = compiled_contract(prepared)
    assert set(probe()._validate_contract(contract, phase)) == set(probe().MODULE_NAMES)


@pytest.mark.parametrize("change", ["extra_key", "phase_roster", "missing_module", "duplicate_module",
                                     "builtin_path", "module_digest", "resource_digest", "resource_count"])
def test_probe_contract_validation_rejects_changed_fixed_rosters(valid, change):
    _, prepared = valid
    contract = compiled_contract(prepared)
    if change == "extra_key":
        contract["execution_authorized"] = True
    elif change == "phase_roster":
        contract["phases"]["worker"].append("epf_hazard_adapter")
    elif change == "missing_module":
        contract["modules"].pop()
    elif change == "duplicate_module":
        contract["modules"][-1] = copy.deepcopy(contract["modules"][0])
    elif change == "builtin_path":
        next(row for row in contract["modules"] if row["kind"] == "builtin")["path"] = "/host/sys.py"
    elif change == "module_digest":
        contract["modules"][0]["sha256"] = "invalid"
    elif change == "resource_digest":
        contract["resources"][0]["sha256"] = "invalid"
    else:
        contract["resources"].pop()
    with pytest.raises(probe().ProbeError):
        probe()._validate_contract(contract, "worker")


@pytest.mark.parametrize("phase", ["", "operator", "worker;exec", None, []])
def test_probe_accepts_only_its_two_finite_phases(valid, phase):
    _, prepared = valid
    with pytest.raises(probe().ProbeError):
        probe()._validate_contract(compiled_contract(prepared), phase)


@pytest.mark.parametrize("kind", ["source", "extension"])
def test_probe_file_observations_bind_bytes_and_matching_module_origin(monkeypatch, kind):
    raw = b"authored inert selected module bytes\n"
    path = "/runtime/python/lib/python3.11/statistics" + (".py" if kind == "source" else ".so")
    row = {"name": "statistics", "kind": kind, "path": path,
           "sha256": digest(raw), "size_bytes": len(raw)}
    loader_name = "SourceFileLoader" if kind == "source" else "ExtensionFileLoader"
    fake = SimpleNamespace(__file__=path, __spec__=SimpleNamespace(
        name="statistics", origin=path, loader=type(loader_name, (), {})()))
    reads, imports = [], []

    def read(selected, limit):
        reads.append(selected)
        assert selected == path and limit >= len(raw)
        return raw

    def load(name):
        imports.append(name)
        assert name == "statistics"
        return fake

    monkeypatch.setattr(probe(), "_read_regular", read)
    monkeypatch.setattr(probe(), "_import_module", load)
    monkeypatch.setattr(probe(), "_sha", digest)
    observed = probe()._module_observation(row, b"unused interpreter", True)
    assert observed["sha256"] == digest(raw)
    assert observed["present_before_phase"] is True
    assert observed["observed_origin"] == path
    assert reads == [path, path] and imports == ["statistics"]


@pytest.mark.parametrize("change", ["before_bytes", "after_bytes", "spec_name", "spec_origin", "module_file", "loader"])
def test_probe_does_not_accept_unbound_file_module_observations(monkeypatch, change):
    raw = b"authored inert selected module bytes\n"
    path = "/runtime/python/lib/python3.11/statistics.py"
    row = {"name": "statistics", "kind": "source", "path": path,
           "sha256": digest(raw), "size_bytes": len(raw)}
    fake = SimpleNamespace(__file__=path, __spec__=SimpleNamespace(
        name="statistics", origin=path, loader=type("SourceFileLoader", (), {})()))
    if change == "spec_name":
        fake.__spec__.name = "another_module"
    elif change == "spec_origin":
        fake.__spec__.origin = "/host/other.py"
    elif change == "module_file":
        fake.__file__ = "/host/other.py"
    elif change == "loader":
        fake.__spec__.loader = object()
    reads, imports = [], []

    def read(selected, limit):
        reads.append(selected)
        if change == "before_bytes" or (change == "after_bytes" and len(reads) == 2):
            return b"substituted bytes\n"
        return raw

    def load(name):
        imports.append(name)
        return fake

    monkeypatch.setattr(probe(), "_read_regular", read)
    monkeypatch.setattr(probe(), "_import_module", load)
    monkeypatch.setattr(probe(), "_sha", digest)
    with pytest.raises(probe().ProbeError):
        probe()._module_observation(row, b"unused interpreter", False)
    if change == "before_bytes":
        assert imports == []


@pytest.mark.parametrize("kind,name,origin", [("builtin", "sys", "built-in"), ("frozen", "os", "frozen")])
def test_probe_interpreter_resident_observation_binds_interpreter_bytes(monkeypatch, kind, name, origin):
    import _imp
    raw = b"authored interpreter bytes\n"
    row = {"name": name, "kind": kind, "path": None, "sha256": digest(raw), "size_bytes": len(raw)}
    fake = SimpleNamespace(__spec__=SimpleNamespace(name=name, origin=origin))
    monkeypatch.setattr(probe(), "_sha", digest)
    monkeypatch.setattr(probe(), "_import_module", lambda selected: fake)
    monkeypatch.setattr(_imp, "is_frozen", lambda selected: selected == "os")
    observed = probe()._module_observation(row, raw, False)
    assert observed["kind"] == kind and observed["sha256"] == digest(raw)
    with pytest.raises(probe().ProbeError):
        probe()._module_observation(row, b"different interpreter", False)


@pytest.mark.parametrize("name", ["epf_hazard_adapter", "PULSE_safe_pack_v0.epf.epf_hazard_forecast",
                                    "PULSE_safe_pack_v0.epf.epf_hazard_features",
                                    "PULSE_safe_pack_v0.epf.epf_hazard_field_spec"])
def test_probe_import_guard_refuses_original_operator_modules(name):
    with pytest.raises(probe().ProbeError, match="probe_operator_import_forbidden"):
        probe()._DenyOperatorImports().find_spec(name)


def test_probe_rejection_is_machine_readable_and_carries_no_authority():
    record = json.loads(probe()._rejection("probe_sha256_failed"))
    assert record["status"] == "rejected" and record["errors"] == ["probe_sha256_failed"]
    assert record["diagnostic_only"] is True
    assert record["operator_applications"] == record["model_calls"] == 0
    boundaries(record)


@pytest.mark.parametrize("phase", ["worker", "collector"])
def test_synthetic_phase_reports_only_fixed_targets_and_diagnostic_results(valid, monkeypatch, phase):
    example, prepared = valid
    contract = compiled_contract(prepared)
    observed = []
    prior_finders = list(sys.meta_path)

    def read(path, limit):
        if path == probe().INTERPRETER_PATH:
            return example.runtime.payload[example.runtime.interpreter]
        assert path.startswith("/runtime/")
        return example.runtime.payload[path.removeprefix("/runtime/")]

    def observe(row, interpreter_bytes, preloaded):
        assert interpreter_bytes == example.runtime.payload[example.runtime.interpreter]
        observed.append(row["name"])
        return {**row, "observed_origin": row["path"] or row["kind"], "present_before_phase": preloaded}

    monkeypatch.setattr(probe(), "_read_regular", read)
    monkeypatch.setattr(probe(), "_module_observation", observe)
    monkeypatch.setattr(probe(), "_sha", digest)
    monkeypatch.setattr(probe(), "_parse", json.loads)
    monkeypatch.setattr(probe(), "_finite_checks", lambda selected: {"authored_phase": selected})
    monkeypatch.setattr(sys, "path", list(probe().SEARCH_ROOTS))
    result = probe()._run_phase(contract, phase, {"fixture": "synthetic startup"})
    expected = set(contract["phases"][phase]) | {"json", "hashlib", "unicodedata"}
    expected.update(".".join(name.split(".")[:index])
                    for name in tuple(expected) for index in range(1, len(name.split("."))))
    assert observed == sorted(expected)
    assert result["phase"] == phase and result["status"] == "completed"
    assert result["diagnostic_only"] is True and result["runtime_execution_authenticated"] is False
    assert result["restored_bootstrap_qualified"] is False
    assert result["operator_applications"] == result["model_calls"] == 0
    assert len(result["resource_observations"]) == 8
    assert sys.meta_path == prior_finders
    boundaries(result)


def test_probe_phase_refuses_an_already_imported_original_operator(valid, monkeypatch):
    _, prepared = valid
    contract = compiled_contract(prepared)
    monkeypatch.setitem(sys.modules, "PULSE_safe_pack_v0.epf.epf_hazard_adapter", SimpleNamespace())
    with pytest.raises(probe().ProbeError, match="probe_operator_import_forbidden"):
        probe()._run_phase(contract, "worker", {"fixture": "synthetic startup"})


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'[]',
                                  b'{"a":"\\ud800"}', b'{}{}'])
def test_probe_control_parser_rejects_ambiguous_or_nonfinite_data(monkeypatch, raw):
    monkeypatch.setattr(probe(), "_import_module", lambda name: json)
    with pytest.raises(probe().ProbeError):
        probe()._parse(raw)


def test_fixed_probe_cli_rejects_ambient_host_before_selected_imports():
    result = subprocess.run([sys.executable, str(ROOT / PROBE), "--phase", "worker"],
                            capture_output=True, timeout=15)
    assert result.returncode == 1
    record = json.loads(result.stdout)
    assert record["status"] == "rejected" and record["diagnostic_only"] is True
    assert record["errors"] and record["operator_applications"] == 0
    assert record["errors"][0] in {"probe_platform_mismatch", "probe_python_mismatch",
                                    "probe_startup_flags_mismatch", "probe_prefix_mismatch"}
    boundaries(record)


@pytest.mark.parametrize("arguments", [[], ["--phase", "operator"], ["--phase", "worker", "--allow-host"],
                                         ["--run-operator"]])
def test_fixed_probe_cli_has_no_authorization_or_operator_option(arguments):
    result = subprocess.run([sys.executable, str(ROOT / PROBE), *arguments], capture_output=True, timeout=15)
    assert result.returncode == 1
    record = json.loads(result.stdout)
    assert record["errors"] == ["probe_arguments_invalid"]
    assert record["diagnostic_only"] is True and record["operator_applications"] == 0
    boundaries(record)


@pytest.mark.parametrize("change", ["prefix", "trailer", "source_tamper"])
def test_rehashed_runtime_capsule_still_needs_original_runtime_admission(valid, change):
    example, _ = valid
    capsule = example.capsule
    if change == "prefix":
        capsule = b"hidden" + capsule
    elif change == "trailer":
        capsule += b"hidden"
    else:
        members = runtime_examples().unpack(capsule)
        path = "payload/" + example.module_paths["statistics"]
        members[path] = b"substituted provider\n"
        capsule = runtime_examples().packed(members)
    selection = copy.deepcopy(example.selection)
    selection["capsule_sha256"] = digest(capsule)
    raw = encoded(selection)
    arguments = example.arguments()
    arguments.update(capsule_bytes=capsule, expected_capsule_sha256=digest(capsule),
                     bootstrap_selection_bytes=raw, expected_bootstrap_selection_sha256=digest(raw))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().prepare_bootstrap(**arguments)


@pytest.mark.parametrize("change", ["extra_field", "ready", "selection_hash", "trailing_whitespace"])
def test_plan_verification_reconstructs_exact_bytes_instead_of_trusting_the_report(valid, change):
    example, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    if change == "extra_field":
        plan["unverified_addition"] = "do not adopt me"
    elif change == "ready":
        plan["execution_ready"] = True
    elif change == "selection_hash":
        plan["bootstrap_selection_sha256"] = "1" * 64
    raw = encoded(plan)
    if change == "trailing_whitespace":
        raw += b" \n"
    with pytest.raises(bootstrap().BootstrapError):
        example.verify(raw)


@pytest.mark.parametrize("field", ["bindings", "files", "empty_directories", "modules", "resources",
                                   "phases", "launches", "containment_requirements"])
def test_rehashed_plan_cannot_change_any_derived_layout_or_launch_section(valid, field):
    example, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    original = plan[field]
    if isinstance(original, list):
        plan[field] = [] if original else ["unreviewed"]
    elif isinstance(original, dict):
        plan[field] = {} if original else {"unreviewed": True}
    else:
        plan[field] = "unreviewed"
    with pytest.raises(bootstrap().BootstrapError):
        example.verify(encoded(plan))


@pytest.mark.parametrize("field,value", [("path", "/outside/unreviewed"), ("sha256", "1" * 64),
                                         ("size_bytes", 1), ("mode", "0500"), ("origin", "host")])
def test_layout_file_descriptors_cannot_be_edited_even_with_fresh_plan_hash(valid, field, value):
    example, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    plan["files"][0][field] = value
    with pytest.raises(bootstrap().BootstrapError):
        example.verify(encoded(plan))


def test_native_alias_collision_with_selected_regular_data_rejects(tmp_path):
    example = Example()
    example.runtime.add("native/libpython3.11.so.1.0", "runtime_data", "data", b"conflicting selected data\n")
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


def test_interpreter_alias_cannot_escape_finite_linux_loader_paths(tmp_path):
    example = Example()
    original = example.runtime.payload[example.runtime.interpreter]
    replacement = runtime_examples().elf(interpreter="/unselected/ld-linux-x86-64.so.2",
                                         needed=("libpython3.11.so.1.0", "libc.so.6"))
    assert original != replacement
    example.runtime.replace(example.runtime.interpreter, replacement)
    for row in example.runtime.selection["native_bindings"]:
        if row["consumer"] == example.runtime.interpreter and row["kind"] == "interpreter":
            row["name"] = "/unselected/ld-linux-x86-64.so.2"
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


@pytest.mark.parametrize("path", ["python/pyvenv.cfg", "python/bin/python3.11._pth", "python/lib/python311.zip",
                                   "python/lib/plugin.egg", "python/lib/plugin.whl"])
def test_selected_startup_override_files_cannot_change_fixed_bootstrap_profile(tmp_path, path):
    example = Example()
    example.runtime.add(path, "runtime_data", "data", b"authored startup override bytes\n")
    example.seal(tmp_path / "source")
    with pytest.raises(bootstrap().BootstrapError):
        example.prepare()


def test_materialization_recovers_every_planned_byte_without_execute_permissions(valid, tmp_path):
    example, prepared = valid
    destination = tmp_path / "materialized"
    result = bootstrap().materialize_bootstrap(prepared, output_directory=destination)
    assert result["status"] == "materialized"
    assert result["bootstrap_view_bytes_verified"] is True
    assert result["restored_bootstrap_qualified"] is False
    boundaries(result)
    plan = json.loads(prepared.plan_bytes)
    expected = {row["path"].lstrip("/") for row in plan["files"]}
    actual = {path.relative_to(destination / "rootfs").as_posix()
              for path in (destination / "rootfs").rglob("*") if path.is_file()}
    assert actual == expected
    for row in plan["files"]:
        assert row["path"].startswith("/")
        restored = destination / "rootfs" / row["path"].lstrip("/")
        raw = restored.read_bytes()
        assert len(raw) == row["size_bytes"] and digest(raw) == row["sha256"]
        assert restored.stat().st_mode & 0o777 == 0o400
        assert not restored.is_symlink()
    for path, raw in example.runtime.payload.items():
        assert (destination / "rootfs/runtime" / path).read_bytes() == raw
    assert (destination / "rootfs/runtime/native/libpython3.11.so.1.0").read_bytes() == example.runtime.payload[example.runtime.libpython]
    assert (destination / "rootfs/lib64/ld-linux-x86-64.so.2").read_bytes() == example.runtime.payload[example.runtime.loader]
    for name, raw in (("bootstrap_selection.json", example.selection_bytes()),
                      ("runtime_selection.json", example.runtime.selection_bytes()),
                      ("operator_selection.json", example.runtime.operator_bytes()), ("plan.json", prepared.plan_bytes)):
        assert (destination / name).read_bytes() == raw
        assert (destination / name).stat().st_mode & 0o777 == 0o600
    assert json.loads((destination / "materialization.json").read_bytes()) == result
    assert not (destination / "materialization.incomplete.json").exists()
    for path in destination.rglob("*"):
        if path.is_dir():
            assert path.stat().st_mode & 0o777 == 0o700


def test_preparation_is_immutable_and_direct_construction_does_not_admit(valid, tmp_path):
    _, prepared = valid
    with pytest.raises((AttributeError, FrozenInstanceError)):
        prepared.plan_bytes = b"{}"
    try:
        direct = bootstrap().PreparedBootstrap()
    except bootstrap().BootstrapError:
        direct = None
    if direct is not None:
        with pytest.raises(bootstrap().BootstrapError):
            bootstrap().materialize_bootstrap(direct, output_directory=tmp_path / "direct")
        assert not (tmp_path / "direct").exists()
    forged = object.__new__(bootstrap().PreparedBootstrap)
    destination = tmp_path / "forged"
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().materialize_bootstrap(forged, output_directory=destination)
    assert not destination.exists()


def test_mutating_an_admitted_preparation_cannot_substitute_its_plan(valid, tmp_path):
    _, prepared = valid
    substituted = copy.copy(prepared)
    object.__setattr__(substituted, "plan_bytes", b"{}\n")
    destination = tmp_path / "substituted"
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().materialize_bootstrap(substituted, output_directory=destination)
    assert not destination.exists()


def test_planning_and_materialization_never_launch_a_child(valid, tmp_path, monkeypatch):
    example, _ = valid
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("bootstrap planning must not launch any selected runtime")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    prepared = example.prepare()
    example.verify(prepared.plan_bytes)
    report = bootstrap().materialize_bootstrap(prepared, output_directory=tmp_path / "materialized")
    boundaries(report)
    assert calls == []


@pytest.mark.parametrize("kind", ["existing", "symlink", "parent_symlink"])
def test_materialization_refuses_existing_or_redirected_destination(valid, tmp_path, kind):
    _, prepared = valid
    destination = tmp_path / "materialized"
    if kind == "existing":
        destination.mkdir()
        (destination / "retained.txt").write_bytes(b"keep me")
    elif kind == "symlink":
        target = tmp_path / "target"
        target.mkdir()
        destination.symlink_to(target, target_is_directory=True)
    else:
        target = tmp_path / "parent-target"
        target.mkdir()
        parent = tmp_path / "linked-parent"
        parent.symlink_to(target, target_is_directory=True)
        destination = parent / "materialized"
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().materialize_bootstrap(prepared, output_directory=destination)
    if kind == "existing":
        assert (destination / "retained.txt").read_bytes() == b"keep me"
    elif kind == "parent_symlink":
        assert not (target / "materialized").exists()


def test_partial_materialization_preserves_completed_prefix_and_partial_file(valid, tmp_path, monkeypatch):
    _, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    paths = sorted(row["path"] for row in plan["files"])
    partial_relative = "rootfs/" + paths[3].lstrip("/")
    directory_type = runtime_examples().runtime().acquisition._Directory
    original_create, original_append = directory_type.create, directory_type.append
    descriptors = {}
    failed = False

    def tracked_create(self, relative):
        fd = original_create(self, relative)
        descriptors[fd] = relative
        return fd

    def fail_once(fd, raw):
        nonlocal failed
        if descriptors.get(fd) == partial_relative and not failed:
            failed = True
            original_append(fd, raw[:11])
            raise OSError("authored interrupted storage")
        original_append(fd, raw)

    monkeypatch.setattr(directory_type, "create", tracked_create)
    monkeypatch.setattr(directory_type, "append", staticmethod(fail_once))
    destination = tmp_path / "materialized"
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().materialize_bootstrap(prepared, output_directory=destination)
    assert failed
    assert destination.is_dir()
    assert (destination / "materialization_start.json").is_file()
    assert not (destination / "materialization.json").exists()
    report = json.loads((destination / "materialization.incomplete.json").read_bytes())
    assert report["status"] == "incomplete" and report["automatic_cleanup"] is False
    boundaries(report)
    rows = {row["path"]: row for row in plan["files"]}
    for path in paths[:3]:
        restored = destination / "rootfs" / path.lstrip("/")
        assert digest(restored.read_bytes()) == rows[path]["sha256"]
        assert restored.stat().st_mode & 0o777 == 0o400
    partial = destination / partial_relative
    assert partial.stat().st_size == 11
    assert partial.stat().st_mode & 0o111 == 0


@pytest.mark.parametrize("corrupt_original", [False, True])
def test_materialization_verifies_its_owned_directory_not_a_pathname_decoy(valid, tmp_path, monkeypatch,
                                                                        corrupt_original):
    _, prepared = valid
    plan = json.loads(prepared.plan_bytes)
    last_relative = "rootfs/" + sorted(row["path"] for row in plan["files"])[-1].lstrip("/")
    target_relative = "rootfs/runtime/native/libc.so.6"
    directory_type = runtime_examples().runtime().acquisition._Directory
    original_create, original_append = directory_type.create, directory_type.append
    descriptors = {}
    destination, moved = tmp_path / "materialized", tmp_path / "moved-original"
    swapped = False

    def tracked_create(self, relative):
        fd = original_create(self, relative)
        descriptors[fd] = relative
        return fd

    def swap_after_last_write(fd, raw):
        nonlocal swapped
        original_append(fd, raw)
        if descriptors.get(fd) == last_relative and not swapped:
            swapped = True
            destination.rename(moved)
            shutil.copytree(moved, destination)
            if corrupt_original:
                target = moved / target_relative
                target.chmod(0o600)
                target.write_bytes(b"changed bytes behind the retained directory descriptor\n")
                target.chmod(0o400)

    monkeypatch.setattr(directory_type, "create", tracked_create)
    monkeypatch.setattr(directory_type, "append", staticmethod(swap_after_last_write))
    with pytest.raises(bootstrap().BootstrapError):
        bootstrap().materialize_bootstrap(prepared, output_directory=destination)
    assert swapped
    assert destination.is_dir() and moved.is_dir()
    assert not (destination / "materialization.json").exists()
    assert not (moved / "materialization.json").exists()
    report = json.loads((moved / "materialization.incomplete.json").read_bytes())
    assert report["status"] == "incomplete" and report["automatic_cleanup"] is False
    boundaries(report)


def cli_arguments(root, example, command):
    values = {"runtime-selection": example.runtime.selection_bytes(),
              "operator-selection": example.runtime.operator_bytes(),
              "bootstrap-selection": example.selection_bytes(), "capsule": example.capsule}
    arguments = [sys.executable, str(TOOL), command]
    for name, raw in values.items():
        path = root / (name + (".zip" if name == "capsule" else ".json"))
        path.write_bytes(raw)
        arguments.extend(["--" + name, str(path), "--" + name + "-sha256", digest(raw)])
    return arguments


def test_cli_prepare_check_and_materialize_remain_offline_reviewable_operations(valid, tmp_path):
    example, prepared = valid
    plan = tmp_path / "reviewed-plan.json"
    result = subprocess.run(cli_arguments(tmp_path, example, "prepare") + ["--output", str(plan)],
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    boundaries(json.loads(result.stdout))
    assert plan.read_bytes() == prepared.plan_bytes
    result = subprocess.run(cli_arguments(tmp_path, example, "check") +
                            ["--plan", str(plan), "--plan-sha256", digest(plan.read_bytes())],
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    boundaries(json.loads(result.stdout))
    destination = tmp_path / "materialized"
    result = subprocess.run(cli_arguments(tmp_path, example, "materialize") +
                            ["--plan", str(plan), "--plan-sha256", digest(plan.read_bytes()),
                             "--output-directory", str(destination)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "materialized"
    boundaries(report)
    assert (destination / "plan.json").read_bytes() == prepared.plan_bytes


def test_cli_cannot_materialize_an_unreviewed_plan(valid, tmp_path):
    example, prepared = valid
    plan = tmp_path / "reviewed-plan.json"
    plan.write_bytes(prepared.plan_bytes)
    destination = tmp_path / "materialized"
    result = subprocess.run(cli_arguments(tmp_path, example, "materialize") +
                            ["--plan", str(plan), "--plan-sha256", "0" * 64,
                             "--output-directory", str(destination)], capture_output=True, timeout=30)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "rejected"
    assert not destination.exists()


def test_cli_refuses_to_replace_existing_plan_output(valid, tmp_path):
    example, _ = valid
    plan = tmp_path / "existing.json"
    plan.write_bytes(b"retained existing file\n")
    result = subprocess.run(cli_arguments(tmp_path, example, "prepare") + ["--output", str(plan)],
                            capture_output=True, timeout=30)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "rejected"
    assert plan.read_bytes() == b"retained existing file\n"


def test_existing_observed_acquisition_command_remains_closed():
    result = subprocess.run([sys.executable, str(ROOT / "tools/acquire_required_gate_idempotence_v0.py"), "acquire"],
                            capture_output=True, timeout=15)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["errors"] == ["observed_acquisition_not_ready"]
    boundaries(report)


def test_bootstrap_module_is_registered_once_without_targeted_duplication():
    cleaned = [[line.split("#", 1)[0].strip() for line in (ROOT / "ci" / name).read_text().splitlines()]
               for name in ("tools-tests.list", "pytest-tests.list")]
    assert cleaned[0].count(SELF) == 1
    assert cleaned[1].count(SELF) == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
