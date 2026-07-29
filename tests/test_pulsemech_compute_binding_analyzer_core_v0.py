#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import pytest


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools" / "pulsemech_compute_binding_analyzer_core_v0.py"
FIXED_WRAPPER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
SUBJECT_BRIDGE = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_binding_report_from_subject_input_v0.py"
)
PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_observed_v0.json"
)
CARRIER = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
MANIFEST = PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
README = PRESERVATION_DIR / "README.md"
SHA256SUMS = PRESERVATION_DIR / "SHA256SUMS"
REPORT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
REPORT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
TOOLS_TESTS = ROOT / "ci" / "tools-tests.list"

ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)
CORE_MODULE_NAME = "pulsemech_compute_binding_analyzer_core_v0"
CI_ENTRY = "tests/test_pulsemech_compute_binding_analyzer_core_v0.py"


ANALYZER_DEFINITIONS = (
    "build_report",
    "make_compute_node",
    "make_state_node",
    "make_edge",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strict_json_text(text: str, *, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(f"{label}: duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        raise AssertionError(f"{label}: non-finite JSON value: {value}")

    loaded = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(loaded, dict), f"{label}: expected object"
    return loaded


def load_source_module(path: Path, module_name: str) -> Any:
    source = path.read_bytes()
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = sha256_bytes(source)
    sys.modules[module_name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def run_fixed_wrapper() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FIXED_WRAPPER),
            "--archive",
            str(CARRIER),
            "--manifest",
            str(MANIFEST),
            "--readme",
            str(README),
            "--sha256sums",
            str(SHA256SUMS),
            "--schema",
            str(REPORT_SCHEMA),
            "--validator",
            str(REPORT_VALIDATOR),
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_subject_bridge() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SUBJECT_BRIDGE),
            "--packet",
            str(PACKET),
            "--carrier",
            str(CARRIER),
            "--repository-root",
            str(ROOT),
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_core() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CORE),
            "--archive",
            str(CARRIER),
            "--manifest",
            str(MANIFEST),
            "--readme",
            str(README),
            "--sha256sums",
            str(SHA256SUMS),
            "--schema",
            str(REPORT_SCHEMA),
            "--validator",
            str(REPORT_VALIDATOR),
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def snapshot_tools_tree() -> tuple[tuple[str, str, int, str | None], ...]:
    records: list[tuple[str, str, int, str | None]] = []
    tools = ROOT / "tools"
    for path in sorted(tools.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(tools).as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            records.append((relative, "symlink", metadata.st_size, os.readlink(path)))
        elif stat.S_ISDIR(metadata.st_mode):
            records.append((relative, "directory", metadata.st_size, None))
        elif stat.S_ISREG(metadata.st_mode):
            data = path.read_bytes()
            records.append((relative, "file", len(data), sha256_bytes(data)))
        else:
            records.append((relative, "other", metadata.st_size, None))
    return tuple(records)


def analysis_projection(report: dict[str, Any]) -> dict[str, Any]:
    projected = json.loads(json.dumps(report))
    projected["tool"]["source_sha256"] = "<producer-entrypoint>"
    return projected


@pytest.fixture(scope="module")
def fixed_result() -> tuple[str, dict[str, Any]]:
    result = run_fixed_wrapper()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    return result.stdout, strict_json_text(result.stdout, label="fixed report")


def test_required_core_wrapper_bridge_and_inputs_exist() -> None:
    for path in (
        CORE,
        FIXED_WRAPPER,
        SUBJECT_BRIDGE,
        PACKET,
        CARRIER,
        MANIFEST,
        README,
        SHA256SUMS,
        REPORT_SCHEMA,
        REPORT_VALIDATOR,
        TOOLS_TESTS,
    ):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_analyzer_definitions_exist_only_in_core() -> None:
    core_source = CORE.read_text(encoding="utf-8")
    fixed_source = FIXED_WRAPPER.read_text(encoding="utf-8")
    bridge_source = SUBJECT_BRIDGE.read_text(encoding="utf-8")

    for name in ANALYZER_DEFINITIONS:
        marker = f"def {name}("
        assert core_source.count(marker) == 1, name
        assert marker not in fixed_source, name
        assert marker not in bridge_source, name


def test_fixed_entrypoint_reexports_exact_core_implementation() -> None:
    sys.modules.pop(CORE_MODULE_NAME, None)
    wrapper = load_source_module(
        FIXED_WRAPPER,
        "pulsemech_compute_binding_fixed_wrapper_v0_under_test",
    )

    assert wrapper.ANALYZER_CORE.resolve() == CORE.resolve()
    assert wrapper.ANALYZER_CORE_SOURCE_SHA256 == sha256_file(CORE)
    assert wrapper.build_report.__module__ == CORE_MODULE_NAME
    assert wrapper.load_observed_bundle.__module__ == CORE_MODULE_NAME
    assert wrapper.make_compute_node.__module__ == CORE_MODULE_NAME
    assert wrapper.make_state_node.__module__ == CORE_MODULE_NAME
    assert wrapper.make_edge.__module__ == CORE_MODULE_NAME


def test_fixed_wrapper_and_subject_bridge_are_byte_identical(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    fixed_stdout, report = fixed_result
    bridge = run_subject_bridge()
    assert bridge.returncode == 0, bridge.stdout + bridge.stderr
    assert bridge.stderr == ""
    assert bridge.stdout == fixed_stdout

    assert report["tool"] == {
        "id": "build_pulsemech_compute_binding_report_v0",
        "version": "0.1.0",
        "source_sha256": sha256_file(FIXED_WRAPPER),
    }
    observer = next(
        node
        for node in report["compute_nodes"]
        if node["node_id"] == "compute:offline-observer"
    )
    assert observer["source_identity"] == {
        "source_kind": "repository_file",
        "source_path_or_uri": "tools/pulsemech_compute_binding_analyzer_core_v0.py",
        "source_revision": "0.1.0",
        "source_sha256": sha256_file(CORE),
    }


def test_direct_core_preserves_analysis_payload(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    _fixed_stdout, fixed_report = fixed_result
    core = run_core()
    assert core.returncode == 0, core.stdout + core.stderr
    assert core.stderr == ""
    core_report = strict_json_text(core.stdout, label="core report")

    assert core_report["tool"]["source_sha256"] == sha256_file(CORE)
    assert analysis_projection(core_report) == analysis_projection(fixed_report)


def test_repeated_wrapper_execution_is_deterministic(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    first_stdout, _report = fixed_result
    second = run_fixed_wrapper()
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stderr == ""
    assert second.stdout == first_stdout


def test_core_extraction_writes_no_tools_entry(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    before = snapshot_tools_tree()
    fixed = run_fixed_wrapper()
    bridge = run_subject_bridge()
    core = run_core()
    after = snapshot_tools_tree()

    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    assert bridge.returncode == 0, bridge.stdout + bridge.stderr
    assert core.returncode == 0, core.stdout + core.stderr
    assert before == after


def test_core_and_wrappers_compile_from_exact_source_bytes() -> None:
    for path in (CORE, FIXED_WRAPPER, SUBJECT_BRIDGE):
        compile(path.read_bytes(), str(path), "exec", dont_inherit=True)


def test_core_test_is_registered_exactly_once() -> None:
    entries = [
        line.strip()
        for line in TOOLS_TESTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert entries.count(CI_ENTRY) == 1


def test_core_cli_and_fixed_cli_remain_available() -> None:
    for path in (CORE, FIXED_WRAPPER):
        result = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        assert "--archive" in result.stdout
        assert "--analysis-run-key" in result.stdout


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_pulsemech_compute_binding_analyzer_core_v0() -> None:
    raise SystemExit(
        pytest.main(
            [
                __file__,
                "-q",
                "-p",
                "no:cacheprovider",
            ]
        )
    )


if __name__ == "__main__":
    check_pulsemech_compute_binding_analyzer_core_v0()
