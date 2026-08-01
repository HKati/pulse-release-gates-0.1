#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]

WRAPPER = ROOT / "tools" / "build_pulsemech_compute_subject_input_packet_v0.py"
PRODUCER_CORE = (
    ROOT
    / "tools"
    / "pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"

PACKET_CREATED_UTC = "2026-07-23T18:00:00Z"
PRODUCER_RUN_KEY = (
    "OFFLINE_PRODUCER=pulsemech-subject-input-fixed-source-6066-v0|ATTEMPT=1"
)
EXECUTION_IDENTITY = (
    "PULSEmech fixed-source subject-input producer / PULSE CI #6066 replay"
)

EXPECTED_WRAPPER_SOURCE_PATH = (
    "tools/build_pulsemech_compute_subject_input_packet_v0.py"
)
EXPECTED_CORE_SOURCE_PATH = (
    "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py"
)

PACKET_IMPLEMENTATION_FUNCTIONS = frozenset(
    {
        "verify_exact_carrier_identity",
        "extract_visible_preservation_files",
        "load_exact_bundle",
        "build_artifacts",
        "role_bindings",
        "build_inputs",
        "build_subject_and_sources",
        "producer_identity",
        "coverage",
        "build_packet",
        "validate_generated_packet",
        "reject_output",
        "atomic_write",
    }
)


@dataclass(frozen=True)
class EntrypointEquivalence:
    wrapper_result: subprocess.CompletedProcess[str]
    core_result: subprocess.CompletedProcess[str]
    wrapper_packet: dict[str, Any]
    core_packet: dict[str, Any]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIRECT_CORE_BOOTSTRAP = r"""
import hashlib
import importlib.util
import sys
from pathlib import Path

core_path = Path(sys.argv[1]).resolve(strict=True)
wrapper_path = Path(sys.argv[2]).resolve(strict=True)
arguments = sys.argv[3:]

spec = importlib.util.spec_from_file_location(
    "pulsemech_subject_input_packet_direct_core_v0",
    core_path,
)
if spec is None or spec.loader is None:
    raise SystemExit("direct_core_import_spec_unavailable")

core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

sys.argv = [str(core_path), *arguments]
raise SystemExit(
    core.main(
        profile=core.FIXED_SOURCE_6066_PROFILE,
        producer_source_path=wrapper_path,
        producer_core_source_sha256=hashlib.sha256(
            core_path.read_bytes()
        ).hexdigest(),
    )
)
"""


def cli_arguments(*, packet_created_utc: str) -> list[str]:
    return [
        "--carrier",
        str(ARCHIVE),
        "--repository-root",
        str(ROOT),
        "--packet-created-utc",
        packet_created_utc,
        "--producer-run-key",
        PRODUCER_RUN_KEY,
        "--ci-workflow-or-job-identity",
        EXECUTION_IDENTITY,
    ]


def run_wrapper(
    *,
    packet_created_utc: str = PACKET_CREATED_UTC,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            *cli_arguments(packet_created_utc=packet_created_utc),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_direct_core(
    *,
    packet_created_utc: str = PACKET_CREATED_UTC,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            DIRECT_CORE_BOOTSTRAP,
            str(PRODUCER_CORE),
            str(WRAPPER),
            *cli_arguments(packet_created_utc=packet_created_utc),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


@pytest.fixture(scope="module")
def wrapper_module() -> Any:
    return import_module(
        WRAPPER,
        "pulsemech_subject_input_packet_wrapper_v0_for_core_equivalence",
    )


@pytest.fixture(scope="module")
def equivalence() -> EntrypointEquivalence:
    wrapper_result = run_wrapper()
    core_result = run_direct_core()

    assert wrapper_result.returncode == 0, (
        wrapper_result.stdout + wrapper_result.stderr
    )
    assert core_result.returncode == 0, core_result.stdout + core_result.stderr
    assert wrapper_result.stderr == ""
    assert core_result.stderr == ""
    assert wrapper_result.stdout.endswith("\n")
    assert core_result.stdout.endswith("\n")

    wrapper_packet = strict_json_text(
        wrapper_result.stdout,
        label="wrapper packet",
    )
    core_packet = strict_json_text(
        core_result.stdout,
        label="direct-core packet",
    )
    return EntrypointEquivalence(
        wrapper_result=wrapper_result,
        core_result=core_result,
        wrapper_packet=wrapper_packet,
        core_packet=core_packet,
    )


def top_level_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_required_wrapper_core_and_carrier_exist() -> None:
    for path in (WRAPPER, PRODUCER_CORE, ARCHIVE):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_wrapper_remains_thin_and_core_owns_packet_implementation() -> None:
    wrapper_functions = top_level_function_names(WRAPPER)
    core_functions = top_level_function_names(PRODUCER_CORE)

    assert {
        "sha256_bytes",
        "_load_producer_core",
        "executed_producer_source_path",
        "main",
    } <= wrapper_functions
    assert wrapper_functions.isdisjoint(PACKET_IMPLEMENTATION_FUNCTIONS)
    assert PACKET_IMPLEMENTATION_FUNCTIONS <= core_functions

    wrapper_source = WRAPPER.read_text(encoding="utf-8")
    assert EXPECTED_CORE_SOURCE_PATH.split("/")[-1] in wrapper_source
    assert "producer_source_path=Path(__file__).resolve()" in wrapper_source
    assert (
        "producer_core_source_sha256=PRODUCER_CORE_SOURCE_SHA256"
        in wrapper_source
    )


def test_wrapper_loads_and_binds_the_exact_current_core_bytes(
    wrapper_module: Any,
) -> None:
    core_bytes = PRODUCER_CORE.read_bytes()
    core_sha256 = sha256_bytes(core_bytes)

    assert Path(wrapper_module.PRODUCER_CORE).resolve(strict=True) == (
        PRODUCER_CORE.resolve(strict=True)
    )
    assert wrapper_module.PRODUCER_CORE_SOURCE_SHA256 == core_sha256
    assert (
        wrapper_module._PRODUCER_CORE.__pulsemech_source_sha256__
        == core_sha256
    )
    assert Path(wrapper_module._PRODUCER_CORE.__file__).resolve(strict=True) == (
        PRODUCER_CORE.resolve(strict=True)
    )


def test_wrapper_reexports_core_functions_without_second_implementation(
    wrapper_module: Any,
) -> None:
    core_module = wrapper_module._PRODUCER_CORE

    for name in PACKET_IMPLEMENTATION_FUNCTIONS:
        assert getattr(wrapper_module, name) is getattr(core_module, name), name

    assert wrapper_module.main is not core_module.main
    assert (
        wrapper_module.executed_producer_source_path
        is not core_module.executed_producer_source_path
    )


def test_default_direct_core_profile_is_the_fixed_source_6066_profile(
    wrapper_module: Any,
) -> None:
    core_module = wrapper_module._PRODUCER_CORE
    profile = core_module.DEFAULT_PRODUCER_PROFILE

    assert profile is core_module.FIXED_SOURCE_6066_PROFILE
    assert profile.profile_id == "pulse_ci_6066_fixed_source_v0"
    assert profile.producer_source_path == EXPECTED_WRAPPER_SOURCE_PATH
    assert profile.default_carrier.resolve(strict=True) == ARCHIVE.resolve(
        strict=True
    )
    assert profile.production_mode == "fixed_source_adapter"
    assert profile.packet_scope == "fixed_source_adapter"
    assert profile.packet_identity_mode == "fixed-source-adapter"


def test_wrapper_and_direct_core_emit_byte_identical_packets(
    equivalence: EntrypointEquivalence,
) -> None:
    assert equivalence.wrapper_result.stdout == equivalence.core_result.stdout
    assert equivalence.wrapper_packet == equivalence.core_packet


def test_equivalent_packet_preserves_fixed_source_identity_and_boundaries(
    equivalence: EntrypointEquivalence,
) -> None:
    packet = equivalence.wrapper_packet

    assert packet["schema_version"] == (
        "pulsemech_compute_subject_input_packet_v0"
    )
    assert packet["packet_type"] == (
        "pulsemech_compute_subject_input_packet"
    )
    assert packet["record_status"] == "observed"
    assert packet["producer"]["producer_source"] == (
        EXPECTED_WRAPPER_SOURCE_PATH
    )
    assert packet["producer"]["production_mode"] == "fixed_source_adapter"
    assert packet["packet_identity"]["packet_scope"] == (
        "fixed_source_adapter"
    )
    assert packet["authority_boundary"]["packet_is_release_authority"] is False
    assert packet["authority_boundary"]["changes_release_authority"] is False
    assert packet["authority_boundary"]["activates_compute_gate"] is False
    assert packet["errors"] == []
    assert packet["ok"] is True


def test_wrapper_and_direct_core_failure_surfaces_are_both_machine_readable() -> None:
    invalid_time = "2026-07-23T18:00:00+00:00"

    results = []
    for label, result in (
        ("wrapper", run_wrapper(packet_created_utc=invalid_time)),
        ("direct-core", run_direct_core(packet_created_utc=invalid_time)),
    ):
        assert result.returncode in {1, 2}
        assert result.stdout == ""
        assert "Traceback" not in result.stderr
        diagnostic = strict_json_text(
            result.stderr,
            label=f"{label} diagnostic",
        )
        assert diagnostic["tool"] == (
            "build_pulsemech_compute_subject_input_packet_v0"
        )
        assert diagnostic["ok"] is False
        assert isinstance(diagnostic["errors"], list)
        assert diagnostic["errors"]
        results.append(diagnostic)

    assert results[0] == results[1]


def check_pulsemech_compute_subject_input_packet_producer_core_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_pulsemech_compute_subject_input_packet_producer_core_v0()
