#!/usr/bin/env python3
"""Synthetic preservation/restore tests; acquired runtime code is never run.

Small authored ELF images exercise native dependency metadata. Original
selected repository sources are preserved as inert bytes, while every Python
runtime fixture contains a raise marker to make accidental imports observable.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/required_gate_idempotence_runtime_v0.py"
SELF = "tests/test_required_gate_idempotence_runtime_v0.py"


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


def runtime():
    return module("idempotence_runtime_under_test", "tools/required_gate_idempotence_runtime_v0.py")


def elf_module():
    return module("idempotence_elf_under_test", "tools/required_gate_idempotence_elf_v0.py")


def acquisition_examples():
    return module("runtime_acquisition_examples", "tests/test_required_gate_idempotence_acquisition_v0.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def elf(*, interpreter=None, needed=(), soname=None, rpath=None, runpath=None,
        elf_type=3, additional_tags=()):
    """Construct a small ELF64 image from documented ABI fields, never execute it."""
    strings = bytearray(b"\0")
    tags = []

    def add_string(tag, value):
        offset = len(strings)
        strings.extend(value.encode("ascii") + b"\0")
        tags.append((tag, offset))

    for name in needed:
        add_string(1, name)
    for tag, value in ((14, soname), (15, rpath), (29, runpath)):
        if value is not None:
            add_string(tag, value)
    tags.extend([(5, 0x400400), (10, len(strings)), *additional_tags, (0, 0)])
    dynamic = b"".join(struct.pack("<qQ", tag, value) for tag, value in tags)
    assert len(dynamic) <= 0x200
    raw = bytearray(0x400 + len(strings))
    phnum = 3 if interpreter is not None else 2
    ident = b"\x7fELF" + bytes((2, 1, 1, 0)) + bytes(8)
    raw[:64] = struct.pack("<16sHHIQQQIHHHHHH", ident, elf_type, 62, 1,
                           0x400100 if interpreter else 0, 64, 0, 0, 64, 56, phnum, 0, 0, 0)
    headers = []
    if interpreter is not None:
        interp = interpreter.encode("ascii") + b"\0"
        assert len(interp) < 0x80
        raw[0x180:0x180 + len(interp)] = interp
        headers.append((3, 4, 0x180, 0x400180, 0, len(interp), len(interp), 1))
    headers.extend(((1, 5, 0, 0x400000, 0, len(raw), len(raw), 0x1000),
                    (2, 6, 0x200, 0x400200, 0, len(dynamic), len(dynamic), 8)))
    for index, header in enumerate(headers):
        raw[64 + 56 * index:64 + 56 * (index + 1)] = struct.pack("<IIQQQQQQ", *header)
    raw[0x200:0x200 + len(dynamic)] = dynamic
    raw[0x400:] = strings
    return bytes(raw)


def packed(members, *, compression=zipfile.ZIP_DEFLATED):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for name, raw in sorted(members.items()):
            item = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = (stat.S_IFREG | 0o600) << 16
            item.compress_type = compression
            archive.writestr(item, raw)
    return output.getvalue()


def unpack(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {item.filename: archive.read(item) for item in archive.infolist()}


def boundaries(report):
    for key in ("execution_ready", "execution_authorized", "runtime_closure_verified",
                "production_gate_eligible"):
        assert report[key] is False
    assert report["authority_effect"] == "none"
    assert report.get("metric_pass") is None
    assert report.get("host_environment_qualified", False) is False
    assert report.get("actual_reference_claimed", False) is False


class Example:
    def __init__(self):
        self.operator, sources = acquisition_examples().example_selection()
        self.payload = {}
        self.rows = []
        self.interpreter = "python/bin/python3.11"
        self.loader = "native/ld-linux-x86-64.so.2"
        self.libpython = "python/lib/libpython3.11.so.1.0"
        self.libc = "native/libc.so.6"
        self.add(self.interpreter, "interpreter", "elf", elf(
            interpreter="/lib64/ld-linux-x86-64.so.2", needed=("libpython3.11.so.1.0", "libc.so.6")))
        self.add(self.loader, "loader", "elf", elf(soname="ld-linux-x86-64.so.2"))
        self.add(self.libpython, "shared_library", "elf", elf(
            soname="libpython3.11.so.1.0", needed=("libc.so.6",)))
        self.add(self.libc, "shared_library", "elf", elf(soname="libc.so.6"))
        self.operator["environment"]["executable_sha256"] = digest(self.payload[self.interpreter])
        inert = b'raise RuntimeError("SYNTHETIC_RUNTIME_MUST_NOT_EXECUTE")\n'
        for relative in ("os.py", "codecs.py", "encodings/__init__.py", "encodings/aliases.py",
                         "encodings/utf_8.py", "json/__init__.py", "ctypes/__init__.py",
                         "collections/__init__.py", "importlib/__init__.py", "importlib/_bootstrap.py",
                         "importlib/_bootstrap_external.py", "argparse.py", "hashlib.py", "pathlib.py"):
            self.add("python/lib/python3.11/" + relative, "stdlib", "python", inert)
        for relative in ("yaml/__init__.py", "jsonschema/__init__.py", "referencing/__init__.py",
                         "attr/__init__.py", "attrs/__init__.py", "rpds/__init__.py",
                         "jsonschema_specifications/__init__.py", "typing_extensions.py"):
            self.add("python/lib/python3.11/site-packages/" + relative, "site_package", "python", inert)
        for distribution in ("pyyaml", "jsonschema", "referencing", "rpds-py", "attrs",
                             "jsonschema-specifications", "typing-extensions"):
            metadata_root = distribution.replace("-", "_") + "-1.0.dist-info"
            prefix = "python/lib/python3.11/site-packages/" + metadata_root
            self.add(prefix + "/METADATA", "site_package", "text",
                     ("Metadata-Version: 2.1\nName: " + distribution + "\nVersion: 1.0\n\n").encode())
            self.add(prefix + "/RECORD", "site_package", "text",
                     (metadata_root + "/METADATA,,\n" + metadata_root + "/RECORD,,\n").encode())
        self.add("licenses/NOTICE.txt", "license", "text", b"Authored synthetic runtime fixture; no runtime distribution.\n")
        original = {item["path"]: item for item in self.operator["sources"]}
        paths = sorted(set(sources) | set(runtime().VERIFIER_PATHS))
        for path in paths:
            raw = sources.get(path, (ROOT / path).read_bytes())
            source = original.get(path)
            self.add("repository/" + path, "repository_schema" if path.endswith(".json") else "repository_source",
                     "json" if path.endswith(".json") else "python", raw,
                     source_path=path,
                     source_revision=source["source_revision"] if source else self.operator["source_commit"])
        self.selection = {
            "record_type": "required_gate_idempotence_runtime_selection_v0", "record_status": "example",
            "profile": "selected_cpython_runtime_capsule_v0", "repository": "HKati/pulse-release-gates-0.1",
            "source_commit": self.operator["source_commit"], "operator_selection_sha256": digest(self.operator_bytes()),
            "environment": copy.deepcopy(self.operator["environment"]),
            "trees": [{"tree_id": name, "root": name} for name in ("python", "native", "repository", "licenses")],
            "files": self.rows,
            "native_bindings": [
                {"consumer": self.interpreter, "kind": "interpreter", "name": "/lib64/ld-linux-x86-64.so.2",
                 "provider": self.loader},
                {"consumer": self.interpreter, "kind": "needed", "name": "libpython3.11.so.1.0",
                 "provider": self.libpython},
                {"consumer": self.interpreter, "kind": "needed", "name": "libc.so.6", "provider": self.libc},
                {"consumer": self.libpython, "kind": "needed", "name": "libc.so.6", "provider": self.libc},
            ],
            "python": {"interpreter": self.interpreter, "loader": self.loader,
                       "stdlib_root": "python/lib/python3.11",
                       "site_packages_root": "python/lib/python3.11/site-packages"},
            "execution_ready": False, "execution_authorized": False, "runtime_closure_verified": False,
            "production_gate_eligible": False, "authority_effect": "none",
        }

    def add(self, path, role, format, raw, *, source_path=None, source_revision=None):
        self.payload[path] = raw
        self.rows.append({"path": path, "tree_id": path.split("/", 1)[0], "role": role, "format": format,
                          "sha256": digest(raw), "size_bytes": len(raw),
                          "source_path": source_path, "source_revision": source_revision})

    def replace(self, path, raw):
        self.payload[path] = raw
        row = next(row for row in self.rows if row["path"] == path)
        row.update(sha256=digest(raw), size_bytes=len(raw))
        if path == self.interpreter:
            self.operator["environment"]["executable_sha256"] = digest(raw)
            self.selection["environment"] = copy.deepcopy(self.operator["environment"])
            self.selection["operator_selection_sha256"] = digest(self.operator_bytes())

    def drop(self, path):
        self.rows[:] = [row for row in self.rows if row["path"] != path]
        self.payload.pop(path)

    def operator_bytes(self):
        return encoded(self.operator)

    def selection_bytes(self):
        return encoded(self.selection)

    def arguments(self):
        return {"selection_bytes": self.selection_bytes(),
                "expected_selection_sha256": digest(self.selection_bytes()),
                "operator_selection_bytes": self.operator_bytes(),
                "expected_operator_selection_sha256": digest(self.operator_bytes())}

    def stage(self, root):
        root.mkdir()
        for path, raw in self.payload.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return root

    def build(self, root):
        return runtime().build_capsule(**self.arguments(), source_root=root)

    def verify(self, raw):
        return runtime().verify_capsule(**self.arguments(), capsule_bytes=raw,
                                        expected_capsule_sha256=digest(raw))

    def restore(self, raw, directory):
        return runtime().restore_capsule(**self.arguments(), capsule_bytes=raw,
                                         expected_capsule_sha256=digest(raw), output_directory=directory)


@pytest.fixture(scope="module")
def valid(tmp_path_factory):
    example = Example()
    source = example.stage(tmp_path_factory.mktemp("runtime") / "source")
    raw = example.build(source)
    report = example.verify(raw)
    return example, raw, report


def test_valid_capsule_preserves_selected_bytes_without_runtime_claim(valid):
    example, raw, report = valid
    boundaries(report)
    assert report["selected_runtime_bytes_recoverable"] is True
    assert report["native_dependency_bindings_verified"] is True
    members = unpack(raw)
    assert members["selection/runtime_selection.json"] == example.selection_bytes()
    assert members["selection/operator_selection.json"] == example.operator_bytes()
    for path, content in example.payload.items():
        assert members["payload/" + path] == content
    assert len(members) == len(example.payload) + 3


def test_capsule_build_and_report_are_deterministic(valid, tmp_path):
    example, raw, report = valid
    source = example.stage(tmp_path / "source")
    assert example.build(source) == raw
    assert example.verify(raw) == report


def test_existing_acquire_command_remains_closed():
    result = subprocess.run([sys.executable, str(ROOT / "tools/acquire_required_gate_idempotence_v0.py"), "acquire"],
                            capture_output=True, timeout=15)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["errors"] == ["observed_acquisition_not_ready"]
    boundaries(report)


@pytest.mark.parametrize("argument", ["expected_selection_sha256", "expected_operator_selection_sha256",
                                      "expected_capsule_sha256"])
def test_independent_selection_hashes_are_required(valid, argument):
    example, raw, _ = valid
    arguments = {**example.arguments(), "capsule_bytes": raw, "expected_capsule_sha256": digest(raw)}
    arguments[argument] = "0" * 64
    with pytest.raises(runtime().CapsuleError):
        runtime().verify_capsule(**arguments)


@pytest.mark.parametrize("field,value", [
    ("execution_ready", True), ("execution_authorized", True), ("runtime_closure_verified", True),
    ("production_gate_eligible", True), ("authority_effect", "release"), ("unknown", False),
    ("source_commit", "b" * 40), ("operator_selection_sha256", "0" * 64),
    ("record_status", "observed"), ("profile", "arbitrary_runtime"),
])
def test_coherently_rehashed_selection_cannot_change_boundaries_or_subject(tmp_path, field, value):
    example = Example()
    example.selection[field] = value
    source = example.stage(tmp_path / "source")
    with pytest.raises(runtime().CapsuleError):
        example.build(source)


@pytest.mark.parametrize("field,value", [
    ("python_version", "3.11.15"), ("unicode_version", "15.0.0"),
    ("architecture", "aarch64"), ("executable_sha256", "1" * 64),
])
def test_runtime_environment_must_match_selected_operator(tmp_path, field, value):
    example = Example()
    example.selection["environment"][field] = value
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("change", ["missing", "duplicate", "wrong_provider", "wrong_kind", "wrong_consumer", "extra"])
def test_every_recorded_native_dependency_has_exactly_one_selected_binding(tmp_path, change):
    example = Example()
    edges = example.selection["native_bindings"]
    if change == "missing":
        edges.pop()
    elif change == "duplicate":
        edges.append(copy.deepcopy(edges[-1]))
    elif change == "wrong_provider":
        edges[-1]["provider"] = example.loader
    elif change == "wrong_kind":
        edges[-1]["kind"] = "interpreter"
    elif change == "wrong_consumer":
        edges[-1]["consumer"] = example.loader
    else:
        edges.append({"consumer": example.libc, "kind": "needed", "name": "absent.so", "provider": example.libpython})
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


def test_new_native_dependency_cannot_be_hidden_by_repinning_file(tmp_path):
    example = Example()
    example.replace(example.libpython, elf(soname="libpython3.11.so.1.0", needed=("libc.so.6", "undeclared.so")))
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


def test_duplicate_provider_soname_is_ambiguous_even_with_explicit_edges(tmp_path):
    example = Example()
    example.add("native/second-libc.so", "shared_library", "elf", elf(soname="libc.so.6"))
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("kind", ["executable_dependency", "unrelated_interpreter", "unrelated_loader_soname"])
def test_native_provider_identity_cannot_be_satisfied_by_an_unrelated_object(tmp_path, kind):
    example = Example()
    if kind == "executable_dependency":
        example.replace(example.libc, elf(elf_type=2, soname="libc.so.6"))
    elif kind == "unrelated_interpreter":
        example.replace(example.interpreter, elf(interpreter="/definitely/unrelated-loader",
                                                 needed=("libpython3.11.so.1.0", "libc.so.6")))
        example.selection["native_bindings"][0]["name"] = "/definitely/unrelated-loader"
    else:
        example.replace(example.loader, elf(soname="unrelated-library.so"))
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("kind", ["interpreter", "loader"])
def test_native_identity_paths_cannot_be_swapped(tmp_path, kind):
    example = Example()
    example.selection["python"][kind] = example.libc
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


def test_interpreter_digest_must_match_selected_environment_even_when_both_manifests_rehashed(tmp_path):
    example = Example()
    example.operator["environment"]["executable_sha256"] = "f" * 64
    example.selection["environment"] = copy.deepcopy(example.operator["environment"])
    example.selection["operator_selection_sha256"] = digest(example.operator_bytes())
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("role", ["interpreter", "loader", "stdlib", "site_package", "license"])
def test_required_runtime_sections_cannot_disappear_from_selected_roster(tmp_path, role):
    example = Example()
    for path in [row["path"] for row in example.rows if row["role"] == role]:
        example.drop(path)
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("kind", ["missing", "changed", "revision", "role", "locator"])
def test_required_repository_sources_remain_bound_to_operator_selection(tmp_path, kind):
    example = Example()
    path = "repository/tools/required_gate_idempotence_worker_v0.py"
    row = next(row for row in example.rows if row["path"] == path)
    if kind == "missing":
        example.drop(path)
    elif kind == "changed":
        example.replace(path, b"raise RuntimeError('changed implementation')\n")
    elif kind == "revision":
        row["source_revision"] = "f" * 40
    elif kind == "role":
        row["role"] = "runtime_data"
    else:
        row["source_path"] = "tools/different_worker.py"
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("kind", ["normal", "missing_process", "displaced_worker", "displaced_collector",
                                  "process_revision"])
def test_operator_selection_preserves_exact_acquisition_paths_roles_and_revisions(tmp_path, kind):
    example = Example()
    acquisition = runtime().acquisition
    by_path = {row["path"]: row for row in example.operator["sources"]}
    assert len(by_path) == 7
    if kind == "missing_process":
        example.operator["sources"].remove(by_path[acquisition.PROCESS])
    elif kind in {"displaced_worker", "displaced_collector"}:
        chosen = acquisition.WORKER if kind == "displaced_worker" else acquisition.COLLECTOR
        by_path[chosen]["role"], by_path[acquisition.PROCESS]["role"] = (
            by_path[acquisition.PROCESS]["role"], by_path[chosen]["role"])
    elif kind == "process_revision":
        by_path[acquisition.PROCESS]["source_revision"] = "b" * 40
        runtime_row = next(row for row in example.rows if row["path"] == "repository/" + acquisition.PROCESS)
        runtime_row["source_revision"] = "b" * 40
    example.selection["operator_selection_sha256"] = digest(example.operator_bytes())
    sources = {row["path"]: example.payload["repository/" + row["path"]]
               for row in example.operator["sources"]}
    # Every acquisition file is still present in the capsule roster. Admission
    # also depends on its exact operator-selection path, role and revision.
    assert all("repository/" + path in example.payload
               for path in (acquisition.WORKER, acquisition.COLLECTOR, acquisition.PROCESS))
    preparation_arguments = {"selection_bytes": example.operator_bytes(),
                             "expected_selection_sha256": digest(example.operator_bytes()),
                             "source_bytes": sources}
    source = example.stage(tmp_path / "source")
    if kind == "normal":
        prepared = acquisition.prepare_selection(**preparation_arguments)
        assert len(prepared.selection["sources"]) == 7
        report = example.verify(example.build(source))
        boundaries(report)
        assert report["selected_runtime_bytes_recoverable"] is True
    else:
        with pytest.raises(acquisition.AcquisitionError, match="acquisition_implementation_selection_mismatch"):
            acquisition.prepare_selection(**preparation_arguments)
        with pytest.raises(runtime().CapsuleError, match="runtime_acquisition_selection_mismatch"):
            example.build(source)


def test_selected_mode_requires_repository_git_admission(tmp_path):
    example = Example()
    example.selection["record_status"] = "selected"
    example.operator["record_status"] = "observed"
    example.selection["operator_selection_sha256"] = digest(example.operator_bytes())
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("path", [
    "python/lib/python3.11/encodings/__init__.py", "python/lib/python3.11/importlib/_bootstrap.py",
    "python/lib/python3.11/ctypes/__init__.py", "python/lib/python3.11/site-packages/yaml/__init__.py",
    "python/lib/python3.11/site-packages/rpds/__init__.py", "python/lib/python3.11/site-packages/typing_extensions.py",
    "python/lib/python3.11/site-packages/jsonschema-1.0.dist-info/METADATA",
    "python/lib/python3.11/site-packages/jsonschema-1.0.dist-info/RECORD",
])
def test_bootstrap_and_verifier_dependency_baseline_cannot_be_omitted(tmp_path, path):
    example = Example()
    example.drop(path)
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("raw", [
    b"Name: another-distribution\nVersion: 1.0\n\n",
    b"Name: jsonschema\nName: jsonschema\nVersion: 1.0\n\n",
    b"Name: jsonschema\nVersion: 1.0\nVersion: 2.0\n\n",
    b"Name: jsonschema\nVersion: \n\n", b"Version: 1.0\n\n",
])
def test_distribution_metadata_identity_is_single_and_explicit(tmp_path, raw):
    example = Example()
    example.replace("python/lib/python3.11/site-packages/jsonschema-1.0.dist-info/METADATA", raw)
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


def test_selected_native_bytes_cannot_hide_behind_data_format(tmp_path):
    example = Example()
    example.add("python/lib/python3.11/site-packages/hidden.bin", "runtime_data", "data",
                elf(soname="hidden.so", needed=("undeclared.so",)))
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("mutation", ["duplicate", "wrong_tree", "boolean_size", "float_size", "false_digest",
                                     "unknown_field", "runtime_source_locator", "wrong_format"])
def test_file_roster_is_closed_and_exactly_typed(tmp_path, mutation):
    example = Example()
    row = example.rows[0]
    if mutation == "duplicate":
        example.rows.append(copy.deepcopy(row))
    elif mutation == "wrong_tree":
        row["tree_id"] = "native"
    elif mutation == "boolean_size":
        row["size_bytes"] = True
    elif mutation == "float_size":
        row["size_bytes"] = float(row["size_bytes"])
    elif mutation == "false_digest":
        row["sha256"] = "f" * 64
    elif mutation == "unknown_field":
        row["verified"] = True
    elif mutation == "runtime_source_locator":
        row["source_path"] = "tools/fabricated.py"
        row["source_revision"] = example.operator["source_commit"]
    else:
        row["format"] = "data"
    with pytest.raises(runtime().CapsuleError):
        example.build(example.stage(tmp_path / "source"))


@pytest.mark.parametrize("bad_path", ["../outside", "/tmp/outside", "python/../outside", "python//empty",
                                     "python/./dot", "python/back\\slash", "python/file:alias", "python/a\x00b"])
def test_selected_payload_paths_are_relative_and_unambiguous(tmp_path, bad_path):
    example = Example()
    example.rows[0]["path"] = bad_path
    source = example.stage(tmp_path / "source")
    with pytest.raises(runtime().CapsuleError):
        example.build(source)


@pytest.mark.parametrize("kind", ["extra_file", "extra_directory", "missing", "changed", "file_symlink",
                                  "directory_symlink", "root_symlink", "hardlink", "fifo"])
def test_source_capture_is_closed_and_refuses_filesystem_substitutions(tmp_path, kind):
    example = Example()
    source = example.stage(tmp_path / "source")
    chosen = source / "licenses/NOTICE.txt"
    if kind == "extra_file":
        (source / "python/unlisted.txt").write_bytes(b"unselected")
    elif kind == "extra_directory":
        (source / "python/unlisted").mkdir()
    elif kind == "missing":
        chosen.unlink()
    elif kind == "changed":
        chosen.write_bytes(b"different bytes")
    elif kind == "file_symlink":
        other = tmp_path / "outside"
        other.write_bytes(chosen.read_bytes())
        chosen.unlink()
        chosen.symlink_to(other)
    elif kind == "directory_symlink":
        (source / "licenses").rename(tmp_path / "outside")
        (source / "licenses").symlink_to(tmp_path / "outside", target_is_directory=True)
    elif kind == "root_symlink":
        alternate = tmp_path / "alias"
        alternate.symlink_to(source, target_is_directory=True)
        source = alternate
    elif kind == "hardlink":
        os.link(chosen, tmp_path / "outside-hardlink")
    else:
        chosen.unlink()
        os.mkfifo(chosen)
    with pytest.raises(runtime().CapsuleError):
        example.build(source)


@pytest.mark.parametrize("member", ["selection/runtime_selection.json", "selection/operator_selection.json",
                                    "capture/member_inventory.json", "payload/native/libc.so.6"])
def test_capsule_missing_or_replaced_member_is_rejected(valid, member):
    example, raw, _ = valid
    members = unpack(raw)
    members.pop(member)
    with pytest.raises(runtime().CapsuleError):
        example.verify(packed(members))


@pytest.mark.parametrize("modification", ["extra", "replace", "prefix", "trailer", "concatenation"])
def test_capsule_bytes_cannot_be_extended_or_substituted(valid, modification):
    example, raw, _ = valid
    if modification == "prefix":
        changed = b"unindexed-prefix" + raw
    elif modification == "trailer":
        changed = raw + b"unindexed-trailer"
    elif modification == "concatenation":
        changed = raw + raw
    else:
        members = unpack(raw)
        if modification == "extra":
            members["payload/native/unlisted.so"] = elf(soname="unlisted.so")
        else:
            members["payload/native/libc.so.6"] += b"substitution"
        changed = packed(members)
    with pytest.raises(runtime().CapsuleError):
        example.verify(changed)


@pytest.mark.parametrize("mutation", ["omitted", "duplicate", "digest", "boolean_size", "self_index"])
def test_inventory_is_exact_and_independently_recomputed(valid, mutation):
    example, raw, _ = valid
    members = unpack(raw)
    inventory = json.loads(members["capture/member_inventory.json"])
    rows = inventory["members"]
    if mutation == "omitted":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "digest":
        rows[0]["sha256"] = "0" * 64
    elif mutation == "boolean_size":
        rows[0]["size_bytes"] = True
    else:
        rows.append({"member": "capture/member_inventory.json", "sha256": digest(members["capture/member_inventory.json"]),
                     "size_bytes": len(members["capture/member_inventory.json"])})
    members["capture/member_inventory.json"] = encoded(inventory)
    with pytest.raises(runtime().CapsuleError):
        example.verify(packed(members))


def test_rehashed_inventory_cannot_substitute_selected_payload(valid):
    example, raw, _ = valid
    members = unpack(raw)
    chosen = "payload/licenses/NOTICE.txt"
    members[chosen] = b"replacement with a consistently rehashed internal inventory\n"
    inventory = json.loads(members["capture/member_inventory.json"])
    row = next(row for row in inventory["members"] if row["member"] == chosen)
    row.update(sha256=digest(members[chosen]), size_bytes=len(members[chosen]))
    members["capture/member_inventory.json"] = encoded(inventory)
    with pytest.raises(runtime().CapsuleError):
        example.verify(packed(members))


@pytest.mark.parametrize("mutation", ["duplicate", "symlink", "member_comment", "archive_comment",
                                      "member_extra", "path_alias", "directory"])
def test_capsule_rejects_ambiguous_zip_layout_and_metadata(valid, mutation):
    example, raw, _ = valid
    members = unpack(raw)
    chosen = "payload/licenses/NOTICE.txt"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o400) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            if name == chosen:
                if mutation == "symlink":
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                elif mutation == "member_comment":
                    info.comment = b"unselected comment"
                elif mutation == "member_extra":
                    info.extra = struct.pack("<HH", 0xCAFE, 2) + b"xx"
                elif mutation == "path_alias":
                    info.filename = "payload/licenses/./NOTICE.txt"
                elif mutation == "directory":
                    info.filename += "/"
                    info.external_attr = (stat.S_IFDIR | 0o700) << 16
            archive.writestr(info, content)
        if mutation == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr(chosen, members[chosen])
        elif mutation == "archive_comment":
            archive.comment = b"unselected archive comment"
    with pytest.raises(runtime().CapsuleError):
        example.verify(output.getvalue())


def test_corrupt_deflate_is_a_structured_rejection_in_api_and_cli(valid, tmp_path):
    example, raw, _ = valid
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        item = archive.getinfo("payload/native/libc.so.6")
        assert item.compress_type == zipfile.ZIP_DEFLATED
        header = struct.unpack_from("<4s5H3L2H", raw, item.header_offset)
        offset = item.header_offset + 30 + header[-2] + header[-1]
    changed = bytearray(raw)
    changed[offset] = 0xFF  # Reserved DEFLATE block type, with otherwise unchanged ZIP layout.
    changed = bytes(changed)
    with pytest.raises(runtime().CapsuleError, match="capsule_invalid"):
        example.verify(changed)
    capsule = tmp_path / "corrupt-deflate.zip"
    capsule.write_bytes(changed)
    result = subprocess.run(cli_arguments(tmp_path, example, "check") +
                            ["--capsule", str(capsule), "--capsule-sha256", digest(changed)],
                            capture_output=True, timeout=30)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "rejected"
    assert report["errors"] == ["capsule_invalid"]
    boundaries(report)
    assert b"Traceback" not in result.stdout + result.stderr


def test_shared_library_interpreter_is_bound_to_selected_loader(tmp_path):
    example = Example()
    example.replace(example.libc, elf(soname="libc.so.6", interpreter="/lib64/ld-linux-x86-64.so.2"))
    example.selection["native_bindings"].append({"consumer": example.libc, "kind": "interpreter",
                                                "name": "/lib64/ld-linux-x86-64.so.2", "provider": example.loader})
    raw = example.build(example.stage(tmp_path / "source"))
    report = example.verify(raw)
    boundaries(report)
    assert report["native_dependency_bindings_verified"] is True
    example.selection["native_bindings"].pop()
    with pytest.raises(runtime().CapsuleError):
        example.build(tmp_path / "source")


def test_restoration_is_exact_read_only_and_nonexecuting(valid, tmp_path):
    example, raw, _ = valid
    destination = tmp_path / "restored"
    report = example.restore(raw, destination)
    boundaries(report)
    assert destination.stat().st_mode & 0o777 == 0o700
    for path, content in example.payload.items():
        restored = destination / "payload" / path
        assert restored.read_bytes() == content
        assert restored.stat().st_mode & 0o777 == 0o400
    assert (destination / "restoration.json").is_file()
    assert not list(destination.rglob("__pycache__"))


@pytest.mark.parametrize("kind", ["existing", "symlink", "parent_symlink"])
def test_restoration_refuses_replacement_or_symlink_paths(valid, tmp_path, kind):
    example, raw, _ = valid
    destination = tmp_path / "restored"
    if kind == "existing":
        destination.mkdir()
        (destination / "retained.txt").write_bytes(b"keep me")
    elif kind == "symlink":
        target = tmp_path / "existing"
        target.mkdir()
        destination.symlink_to(target, target_is_directory=True)
    else:
        target = tmp_path / "existing"
        target.mkdir()
        parent = tmp_path / "parent"
        parent.symlink_to(target, target_is_directory=True)
        destination = parent / "restored"
    with pytest.raises(runtime().CapsuleError):
        example.restore(raw, destination)
    if kind == "existing":
        assert (destination / "retained.txt").read_bytes() == b"keep me"
    elif kind == "parent_symlink":
        assert not (target / "restored").exists()


def test_invalid_capsule_creates_no_restoration(valid, tmp_path):
    example, raw, _ = valid
    destination = tmp_path / "restored"
    with pytest.raises(runtime().CapsuleError):
        example.restore(raw + b"bad", destination)
    assert not destination.exists()


def test_failed_restoration_retains_verified_prefix_and_marks_incomplete(valid, tmp_path, monkeypatch):
    example, raw, _ = valid
    directory_type = runtime().acquisition._Directory
    original_append = directory_type.append
    writes = 0

    def fail_once_after_partial_write(fd, content):
        nonlocal writes
        writes += 1
        if writes == 4:
            original_append(fd, content[:11])
            raise OSError("synthetic interrupted storage")
        original_append(fd, content)

    monkeypatch.setattr(directory_type, "append", staticmethod(fail_once_after_partial_write))
    destination = tmp_path / "restored"
    with pytest.raises(runtime().CapsuleError, match="runtime_restore_failed"):
        example.restore(raw, destination)
    assert destination.is_dir()
    assert not (destination / "restoration.json").exists()
    report = json.loads((destination / "restoration.incomplete.json").read_bytes())
    boundaries(report)
    assert report["status"] == "incomplete"
    assert report["automatic_cleanup"] is False
    assert report["errors"] == ["runtime_restore_failed"]
    assert report["capsule_sha256"] == digest(raw)
    assert report["runtime_selection_sha256"] == digest(example.selection_bytes())
    paths = sorted(example.payload)
    assert [row["path"] for row in report["completed_files"]] == ["payload/" + path for path in paths[:3]]
    for path in paths[:3]:
        restored = destination / "payload" / path
        assert restored.read_bytes() == example.payload[path]
        assert restored.stat().st_mode & 0o777 == 0o400
    partial = destination / "payload" / paths[3]
    assert partial.read_bytes() == example.payload[paths[3]][:11]
    assert partial.stat().st_mode & 0o111 == 0


@pytest.mark.parametrize("corrupt_original", [False, True])
def test_restoration_cannot_verify_a_pathname_decoy_for_another_owned_tree(valid, tmp_path, monkeypatch,
                                                                        corrupt_original):
    example, raw, _ = valid
    directory_type = runtime().acquisition._Directory
    original_append = directory_type.append
    destination, moved = tmp_path / "restored", tmp_path / "moved-original"
    writes = 0

    def swap_after_last_payload_write(fd, content):
        nonlocal writes
        original_append(fd, content)
        writes += 1
        if writes == len(example.payload):
            destination.rename(moved)
            shutil.copytree(moved, destination)
            if corrupt_original:
                changed = moved / "payload" / example.libc
                changed.chmod(0o600)
                changed.write_bytes(b"corrupted original file behind retained directory descriptor")
                changed.chmod(0o400)

    monkeypatch.setattr(directory_type, "append", staticmethod(swap_after_last_payload_write))
    with pytest.raises(runtime().CapsuleError):
        example.restore(raw, destination)
    assert destination.is_dir() and moved.is_dir()
    assert not (destination / "restoration.json").exists()
    assert not (moved / "restoration.json").exists()
    incomplete = json.loads((moved / "restoration.incomplete.json").read_bytes())
    assert incomplete["status"] == "incomplete"
    assert incomplete["automatic_cleanup"] is False
    boundaries(incomplete)
    assert (destination / "payload" / example.libc).read_bytes() == example.payload[example.libc]
    if corrupt_original:
        assert (moved / "payload" / example.libc).read_bytes() != example.payload[example.libc]


def test_build_verify_restore_never_start_inspected_runtime(tmp_path, monkeypatch):
    example = Example()
    source = example.stage(tmp_path / "source")
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("capsule operations must never start a child")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    raw = example.build(source)
    example.verify(raw)
    example.restore(raw, tmp_path / "restored")
    assert calls == []


def test_runtime_capsules_do_not_relax_observation_archive_limits(valid):
    assert runtime().observation.ARCHIVE_LIMIT == 4 * 1024 * 1024
    assert runtime().observation.TOTAL_LIMIT == 2 * 1024 * 1024
    assert runtime().observation.MEMBER_LIMIT == 512 * 1024


def cli_arguments(tmp_path, example, command):
    selection = tmp_path / "runtime-selection.json"
    operator = tmp_path / "operator-selection.json"
    selection.write_bytes(example.selection_bytes())
    operator.write_bytes(example.operator_bytes())
    return [sys.executable, str(TOOL), command, "--selection", str(selection),
            "--selection-sha256", digest(example.selection_bytes()),
            "--operator-selection", str(operator), "--operator-selection-sha256", digest(example.operator_bytes())]


def test_cli_build_check_and_restore_are_reviewable_offline_operations(tmp_path):
    example = Example()
    source = example.stage(tmp_path / "source")
    capsule = tmp_path / "runtime.zip"
    result = subprocess.run(cli_arguments(tmp_path, example, "build") +
                            ["--source-root", str(source), "--output", str(capsule)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    raw = capsule.read_bytes()
    boundaries(example.verify(raw))
    result = subprocess.run(cli_arguments(tmp_path, example, "check") +
                            ["--capsule", str(capsule), "--capsule-sha256", digest(raw)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    boundaries(json.loads(result.stdout))
    destination = tmp_path / "restored"
    result = subprocess.run(cli_arguments(tmp_path, example, "restore") +
                            ["--capsule", str(capsule), "--capsule-sha256", digest(raw),
                             "--output-directory", str(destination)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (destination / "payload" / example.interpreter).read_bytes() == example.payload[example.interpreter]
    boundaries(json.loads(result.stdout))


def test_cli_cannot_replace_existing_capsule(tmp_path):
    example = Example()
    source = example.stage(tmp_path / "source")
    capsule = tmp_path / "runtime.zip"
    capsule.write_bytes(b"keep existing bytes")
    result = subprocess.run(cli_arguments(tmp_path, example, "build") +
                            ["--source-root", str(source), "--output", str(capsule)], capture_output=True, timeout=30)
    assert result.returncode != 0
    assert capsule.read_bytes() == b"keep existing bytes"
    assert b"Traceback" not in result.stderr


def test_cli_digest_mismatch_rejects_without_echoing_untrusted_archive(valid, tmp_path):
    example, raw, _ = valid
    capsule = tmp_path / "runtime.zip"
    capsule.write_bytes(raw + b"PRIVATE_UNTRUSTED_FIXTURE_SENTINEL")
    result = subprocess.run(cli_arguments(tmp_path, example, "check") +
                            ["--capsule", str(capsule), "--capsule-sha256", digest(raw)], capture_output=True, timeout=30)
    assert result.returncode != 0
    report = json.loads(result.stdout)
    boundaries(report)
    assert b"PRIVATE_UNTRUSTED_FIXTURE_SENTINEL" not in result.stdout + result.stderr
    assert b"Traceback" not in result.stdout + result.stderr


def test_synthetic_elf_records_are_parsed_without_loading():
    raw = elf(interpreter="/lib64/ld-linux-x86-64.so.2", needed=("libc.so.6",), runpath="$ORIGIN/../lib")
    result = elf_module().inspect_elf(raw)
    assert result == {"elf_type": "ET_DYN", "interpreter": "/lib64/ld-linux-x86-64.so.2",
                      "needed": ["libc.so.6"], "soname": None, "rpath": None, "runpath": "$ORIGIN/../lib"}


@pytest.mark.parametrize("offset,change", [(0, b"NOT!"), (4, b"\x01"), (5, b"\x02"),
                                           (6, b"\x00"), (18, b"\xb7\x00"),
                                           (52, b"\x00\x00"), (54, b"\x00\x00"),
                                           (56, b"\x00\x00")])
def test_elf_header_substitutions_reject(offset, change):
    raw = bytearray(elf())
    raw[offset:offset + len(change)] = change
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(bytes(raw))


@pytest.mark.parametrize("name", ["../libc.so.6", "/lib/libc.so.6", "$ORIGIN/lib.so", "one:two.so", "bad;lib.so"])
def test_elf_dependency_names_cannot_introduce_path_search(name):
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(elf(needed=(name,)))


@pytest.mark.parametrize("tag", [0x6FFFFEFA, 0x6FFFFEFB, 0x6FFFFEFC, 0x7FFFFFFD, 0x7FFFFFFF])
def test_elf_additional_object_loading_extensions_reject(tag):
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(elf(additional_tags=((tag, 0),)))


def test_elf_dynamic_string_table_must_map_to_file_bytes():
    raw = bytearray(elf(needed=("libc.so.6",)))
    struct.pack_into("<Q", raw, 0x200 + 16 + 8, 0x900000)
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(bytes(raw))


def test_elf_dynamic_segment_requires_null_terminator():
    raw = bytearray(elf())
    struct.pack_into("<qQ", raw, 0x200 + 32, 21, 0)
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(bytes(raw))


def test_elf_interpreter_header_may_follow_load_header():
    raw = bytearray(elf(interpreter="/lib64/ld-linux-x86-64.so.2", needed=("libc.so.6",)))
    first, second = bytes(raw[64:120]), bytes(raw[120:176])
    raw[64:120], raw[120:176] = second, first
    assert elf_module().inspect_elf(bytes(raw))["interpreter"] == "/lib64/ld-linux-x86-64.so.2"


@pytest.mark.parametrize("field_offset,value", [(32, 2**32), (40, 0), (48, 3)])
def test_elf_load_segment_extent_memory_and_alignment_are_checked(field_offset, value):
    raw = bytearray(elf())
    struct.pack_into("<Q", raw, 64 + field_offset, value)
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(bytes(raw))


def test_elf_duplicate_file_backed_load_mapping_rejects():
    raw = bytearray(elf(needed=("libc.so.6",)))
    struct.pack_into("<H", raw, 56, 3)
    raw[176:232] = raw[64:120]
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(bytes(raw))


@pytest.mark.parametrize("tag", [5, 10, 14, 15, 29])
def test_elf_singleton_dynamic_tags_cannot_repeat(tag):
    kwargs = {14: {"soname": "library.so"}, 15: {"rpath": "$ORIGIN"},
              29: {"runpath": "$ORIGIN"}}.get(tag, {})
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(elf(**kwargs, additional_tags=((tag, 0),)))


def test_elf_needed_duplicates_reject():
    with pytest.raises(elf_module().ElfError):
        elf_module().inspect_elf(elf(needed=("libc.so.6", "libc.so.6")))


def test_runtime_module_is_registered_once_without_targeted_duplication():
    entries = [(ROOT / "ci" / name).read_text().splitlines()
               for name in ("tools-tests.list", "pytest-tests.list")]
    cleaned = [[line.split("#", 1)[0].strip() for line in values] for values in entries]
    assert cleaned[0].count(SELF) == 1
    assert cleaned[1].count(SELF) == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
