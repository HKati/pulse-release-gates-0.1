#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import warnings
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]

PRODUCER = ROOT / "tools" / "build_pulsemech_compute_subject_input_packet_v0.py"
VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
FIXED_SOURCE_BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
SCHEMA = ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)
ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
POLICY = ROOT / "pulse_gate_policy_v0.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
SIGNER_POLICY = ROOT / "policy" / "external_signers_v1.yml"
THRESHOLD_POLICY = (
    ROOT / "PULSE_safe_pack_v0" / "profiles" / "external_thresholds.yaml"
)

EXPECTED_PRODUCER_SHA256 = (
    "2279217d7d76df920b2f0cc41f130e10347d598e2073bf46f4029b19640aa9f8"
)
EXPECTED_PRODUCER_SIZE_BYTES = 66017
EXPECTED_PRODUCER_LINE_COUNT = 1901

EXPECTED_CARRIER_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_CARRIER_SIZE_BYTES = 44660
EXPECTED_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
EXPECTED_SUBJECT_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_ARTIFACT_COUNT = 32
EXPECTED_PROVIDER_COUNT = 3
EXPECTED_ROLE_REFERENCE_COUNT = 28

PACKET_CREATED_UTC = "2026-07-23T18:00:00Z"
PRODUCER_RUN_KEY = (
    "OFFLINE_PRODUCER=pulsemech-subject-input-fixed-source-6066-v0|ATTEMPT=1"
)
EXECUTION_IDENTITY = (
    "PULSEmech fixed-source subject-input producer / PULSE CI #6066 replay"
)

POISONED_GIT_ENVIRONMENT = {
    "GIT_DIR": "/attacker/repository/.git",
    "GIT_WORK_TREE": "/attacker/repository",
    "GIT_COMMON_DIR": "/attacker/common",
    "GIT_OBJECT_DIRECTORY": "/attacker/objects",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/attacker/alternates",
    "GIT_INDEX_FILE": "/attacker/index",
    "GIT_NAMESPACE": "attacker",
    "GIT_CONFIG_PARAMETERS": "'core.worktree=/attacker/repository'",
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "core.worktree",
    "GIT_CONFIG_VALUE_0": "/attacker/repository",
    "GIT_EXEC_PATH": "/attacker/git-core",
    "GIT_CEILING_DIRECTORIES": "/attacker",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
    "GIT_SHALLOW_FILE": "/attacker/shallow",
}


@dataclass(frozen=True)
class CliBuild:
    result: subprocess.CompletedProcess[str]
    packet: dict[str, Any]
    rendered: str
    output: Path
    protected_before: dict[str, tuple[int, str]]
    protected_after: dict[str, tuple[int, str]]


@dataclass(frozen=True)
class ConstructedState:
    revision: str
    validator: Any
    fixed_builder: Any
    inputs: Any
    subject: dict[str, Any]
    sources: dict[str, Any]
    producer: dict[str, Any]
    packet: dict[str, Any]
    rendered: str


# ---------------------------------------------------------------------------
# Strict helpers and module loading
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def strict_json_file(path: Path, *, label: str) -> dict[str, Any]:
    return strict_json_text(path.read_text(encoding="utf-8"), label=label)


def import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PRODUCER_MODULE = import_module(
    PRODUCER,
    "pulsemech_subject_input_packet_producer_v0_under_test",
)


@lru_cache(maxsize=1)
def validator_module() -> Any:
    return import_module(
        VALIDATOR,
        "pulsemech_subject_input_packet_validator_v0_for_producer_test",
    )


@lru_cache(maxsize=1)
def fixed_builder_module() -> Any:
    return import_module(
        FIXED_SOURCE_BUILDER,
        "pulsemech_compute_binding_fixed_builder_v0_for_producer_test",
    )


def protected_snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str]]:
    return {
        str(path): (path.stat().st_size, sha256_file(path))
        for path in paths
    }


def current_head() -> str:
    return PRODUCER_MODULE.current_head(ROOT)


def canonical_render(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def run_producer(
    *,
    carrier: Path = ARCHIVE,
    repository_root: Path = ROOT,
    packet_created_utc: str = PACKET_CREATED_UTC,
    producer_run_key: str = PRODUCER_RUN_KEY,
    execution_identity: str = EXECUTION_IDENTITY,
    output: Path | None = None,
    extra_env: Mapping[str, str | None] | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PRODUCER),
        "--carrier",
        str(carrier),
        "--repository-root",
        str(repository_root),
        "--packet-created-utc",
        packet_created_utc,
        "--producer-run-key",
        producer_run_key,
        "--ci-workflow-or-job-identity",
        execution_identity,
    ]
    if output is not None:
        command.extend(["--output", str(output)])
    if extra_args:
        command.extend(extra_args)

    environment = dict(os.environ)
    for key, value in dict(extra_env or {}).items():
        if value is None:
            environment.pop(key, None)
        else:
            environment[key] = value

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )


def assert_producer_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int | tuple[int, ...] = 1,
) -> dict[str, Any]:
    expected_codes = (
        (expected_returncode,)
        if isinstance(expected_returncode, int)
        else expected_returncode
    )
    assert result.returncode in expected_codes, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    diagnostic = strict_json_text(result.stderr, label="producer diagnostic")
    assert diagnostic["tool"] == "build_pulsemech_compute_subject_input_packet_v0"
    assert diagnostic["ok"] is False
    assert isinstance(diagnostic["errors"], list)
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def trusted_git_run(
    repository: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    trusted_git = PRODUCER_MODULE._trusted_git_executable()
    return subprocess.run(
        [str(trusted_git), *arguments],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=PRODUCER_MODULE._sanitized_git_environment(trusted_git),
    )


def create_git_repository(
    tmp_path: Path,
    *,
    files: Mapping[str, bytes],
) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    trusted_git_run(repository, "init", "-q", str(repository))
    for relative, payload in files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    trusted_git_run(repository, "add", "--", ".")
    trusted_git_run(
        repository,
        "-c",
        "user.name=PULSEmech producer regression",
        "-c",
        "user.email=pulsemech-producer@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    revision = trusted_git_run(repository, "rev-parse", "HEAD").stdout.strip()
    assert len(revision) == 40
    return repository, revision


def copy_zip_with_extra_member(
    source: Path,
    destination: Path,
    *,
    name: str,
    payload: bytes = b"extra\n",
    symlink: bool = False,
) -> Path:
    with zipfile.ZipFile(source, "r") as source_zip:
        with zipfile.ZipFile(destination, "w") as target_zip:
            for info in source_zip.infolist():
                data = b"" if info.is_dir() else source_zip.read(info.filename)
                target_zip.writestr(copy.copy(info), data)
            if symlink:
                link = zipfile.ZipInfo(name)
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                target_zip.writestr(link, b"README.md")
            else:
                target_zip.writestr(name, payload)
    return destination


def copy_zip_with_duplicate_member(source: Path, destination: Path) -> Path:
    with zipfile.ZipFile(source, "r") as source_zip:
        infos = source_zip.infolist()
        assert infos
        duplicate = infos[0]
        duplicate_payload = source_zip.read(duplicate.filename)
        with zipfile.ZipFile(destination, "w") as target_zip:
            for info in infos:
                data = b"" if info.is_dir() else source_zip.read(info.filename)
                target_zip.writestr(copy.copy(info), data)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                target_zip.writestr(copy.copy(duplicate), duplicate_payload)
    return destination


def create_fake_git_executable(
    tmp_path: Path,
    *,
    repository_root: Path,
    forged_revision: str,
    forged_path: str,
    forged_bytes: bytes,
) -> tuple[Path, Path]:
    if os.name == "nt":
        pytest.skip("POSIX fake-Git regression uses /bin/sh")
    attacker_bin = tmp_path / "attacker-bin"
    attacker_bin.mkdir()
    marker = tmp_path / "fake-git-invoked.marker"
    fake_git = attacker_bin / "git"
    trusted_git = PRODUCER_MODULE._trusted_git_executable()
    escaped_bytes = forged_bytes.decode("ascii")
    pattern = f"{forged_revision}:{forged_path}"
    lines = [
        "#!/bin/sh",
        f"printf 'invoked\\n' >> {shlex.quote(str(marker))}",
        'case "$*" in',
        '  *"rev-parse --show-toplevel"*)',
        f"    printf '%s\\n' {shlex.quote(str(repository_root))}",
        "    exit 0",
        "    ;;",
        f'  *"cat-file blob {pattern}"*)',
        f"    printf '%s' {shlex.quote(escaped_bytes)}",
        "    exit 0",
        "    ;;",
        "esac",
        f'exec {shlex.quote(str(trusted_git))} "$@"',
        "",
    ]
    fake_git.write_text("\n".join(lines), encoding="utf-8")
    fake_git.chmod(0o755)
    return fake_git, marker


# ---------------------------------------------------------------------------
# Shared exact construction fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def constructed_state() -> ConstructedState:
    revision = current_head()
    for relative, label in (
        (PRODUCER_MODULE.PRODUCER_SOURCE_PATH, "producer"),
        (PRODUCER_MODULE.SCHEMA_SOURCE_PATH, "schema"),
        (PRODUCER_MODULE.VALIDATOR_SOURCE_PATH, "validator"),
        (PRODUCER_MODULE.FIXED_SOURCE_BUILDER_PATH, "fixed_source_builder"),
    ):
        PRODUCER_MODULE.committed_repository_file(
            ROOT,
            revision=revision,
            relative_path=relative,
            label=label,
        )

    validator = validator_module()
    fixed_builder = fixed_builder_module()
    inputs = PRODUCER_MODULE.build_inputs(
        carrier_path=ARCHIVE,
        repository_root=ROOT,
        validator=validator,
        fixed_builder=fixed_builder,
    )
    subject, sources = PRODUCER_MODULE.build_subject_and_sources(
        inputs=inputs,
        repository_root=ROOT,
        validator=validator,
    )
    producer = PRODUCER_MODULE.producer_identity(
        repository_root=ROOT,
        revision=revision,
        source_path=PRODUCER,
        execution_identity=EXECUTION_IDENTITY,
        producer_run_key=PRODUCER_RUN_KEY,
    )
    packet = PRODUCER_MODULE.build_packet(
        inputs=inputs,
        subject=subject,
        sources=sources,
        producer=producer,
        packet_created_utc=PACKET_CREATED_UTC,
    )
    rendered = PRODUCER_MODULE.render_json(packet)
    return ConstructedState(
        revision=revision,
        validator=validator,
        fixed_builder=fixed_builder,
        inputs=inputs,
        subject=subject,
        sources=sources,
        producer=producer,
        packet=packet,
        rendered=rendered,
    )


@pytest.fixture(scope="module")
def cli_build(tmp_path_factory: pytest.TempPathFactory) -> CliBuild:
    output_directory = tmp_path_factory.mktemp("subject-input-packet-producer-v0")
    output = output_directory / "observed-subject-input-packet-v0.json"
    protected = (
        PRODUCER,
        VALIDATOR,
        FIXED_SOURCE_BUILDER,
        SCHEMA,
        EXAMPLE,
        ARCHIVE,
        POLICY,
        REGISTRY,
        WORKFLOW,
        SIGNER_POLICY,
        THRESHOLD_POLICY,
        PRODUCER_MODULE._trusted_git_executable(),
    )
    before = protected_snapshot(protected)
    result = run_producer(output=output)
    after = protected_snapshot(protected)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert output.is_file()
    assert not output.is_symlink()
    assert output.read_text(encoding="utf-8") == result.stdout
    packet = strict_json_text(result.stdout, label="generated observed packet")
    return CliBuild(
        result=result,
        packet=packet,
        rendered=result.stdout,
        output=output,
        protected_before=before,
        protected_after=after,
    )


# ---------------------------------------------------------------------------
# Contract files, exact identities, and CLI surface
# ---------------------------------------------------------------------------


def test_required_producer_contract_and_subject_files_exist() -> None:
    for path in (
        PRODUCER,
        VALIDATOR,
        FIXED_SOURCE_BUILDER,
        SCHEMA,
        EXAMPLE,
        ARCHIVE,
        POLICY,
        REGISTRY,
        WORKFLOW,
        SIGNER_POLICY,
        THRESHOLD_POLICY,
    ):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_producer_file_identity_is_pinned() -> None:
    payload = PRODUCER.read_bytes()
    assert len(payload) == EXPECTED_PRODUCER_SIZE_BYTES
    assert len(payload.splitlines()) == EXPECTED_PRODUCER_LINE_COUNT
    assert sha256_bytes(payload) == EXPECTED_PRODUCER_SHA256


def test_exact_preservation_carrier_identity_is_pinned() -> None:
    assert ARCHIVE.stat().st_size == EXPECTED_CARRIER_SIZE_BYTES
    assert sha256_file(ARCHIVE) == EXPECTED_CARRIER_SHA256


def test_cli_help_exposes_only_subject_and_execution_inputs() -> None:
    result = subprocess.run(
        [sys.executable, str(PRODUCER), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    for option in (
        "--carrier",
        "--repository-root",
        "--packet-created-utc",
        "--producer-run-key",
        "--ci-workflow-or-job-identity",
        "--output",
    ):
        assert option in result.stdout
    for forbidden in (
        "--schema",
        "--validator",
        "--fixed-source-builder",
        "--git-executable",
    ):
        assert forbidden not in result.stdout


def test_checked_in_contract_example_remains_a_fixture() -> None:
    example = strict_json_file(EXAMPLE, label="checked-in example")
    assert example["record_status"] == "example"
    assert "fixture_provenance" in example
    assert "producer" not in example
    assert example["carrier"]["carrier_kind"] == "preservation_archive"


# ---------------------------------------------------------------------------
# Complete producer positive path
# ---------------------------------------------------------------------------


def test_cli_emits_observed_producer_branch(cli_build: CliBuild) -> None:
    packet = cli_build.packet
    assert packet["schema_version"] == "pulsemech_compute_subject_input_packet_v0"
    assert packet["packet_type"] == "pulsemech_compute_subject_input_packet"
    assert packet["record_status"] == "observed"
    assert "fixture_provenance" not in packet
    assert packet["producer"]["production_mode"] == "fixed_source_adapter"
    assert packet["packet_identity"]["packet_scope"] == "fixed_source_adapter"
    assert packet["ok"] is True
    assert packet["errors"] == []


def test_producer_identity_is_exact_current_committed_source(
    cli_build: CliBuild,
) -> None:
    producer = cli_build.packet["producer"]
    revision = current_head()
    committed = PRODUCER_MODULE._git_blob_bytes(
        ROOT,
        revision=revision,
        path="tools/build_pulsemech_compute_subject_input_packet_v0.py",
    )
    assert producer == {
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": "PULSEmech compute subject-input packet producer",
        "producer_version": "0.1.0",
        "producer_source": (
            "tools/build_pulsemech_compute_subject_input_packet_v0.py"
        ),
        "producer_source_revision": revision,
        "producer_source_sha256": sha256_bytes(committed),
        "ci_workflow_or_job_identity": EXECUTION_IDENTITY,
        "producer_run_key": PRODUCER_RUN_KEY,
        "production_mode": "fixed_source_adapter",
    }
    assert committed == PRODUCER.read_bytes()


def test_packet_identity_is_deterministic_and_exact(cli_build: CliBuild) -> None:
    identity_material = (
        PRODUCER_RUN_KEY
        + "\x00"
        + PACKET_CREATED_UTC
        + "\x00"
        + EXPECTED_CARRIER_SHA256
    ).encode("utf-8")
    identity_digest = sha256_bytes(identity_material)[:16]
    assert cli_build.packet["packet_identity"] == {
        "packet_id": (
            "subject-input:pulse-ci-6066/fixed-source-adapter/"
            f"{identity_digest}/v0"
        ),
        "packet_scope": "fixed_source_adapter",
        "packet_created_utc": PACKET_CREATED_UTC,
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "carrier_id": "carrier:preservation/pulse-ci-6066/v0",
        "canonicalization": "json-sort-keys-utf8-newline",
    }


def test_machine_reconstruction_matches_historical_example_surfaces(
    cli_build: CliBuild,
) -> None:
    packet = cli_build.packet
    example = strict_json_file(EXAMPLE, label="checked-in example")
    for field in (
        "subject",
        "analysis_boundary",
        "authority_sources",
        "carrier",
        "artifacts",
        "role_bindings",
        "coverage",
        "content_boundary",
        "authority_boundary",
    ):
        assert packet[field] == example[field], field


def test_artifact_graph_is_complete_content_addressed_and_acyclic(
    cli_build: CliBuild,
) -> None:
    rows = cli_build.packet["artifacts"]
    assert len(rows) == EXPECTED_ARTIFACT_COUNT
    assert [row["artifact_id"] for row in rows] == sorted(
        row["artifact_id"] for row in rows
    )
    indexed = {row["artifact_id"]: row for row in rows}
    assert len(indexed) == len(rows)

    for row in rows:
        assert len(row["sha256"]) == 64
        int(row["sha256"], 16)
        assert row["size_bytes"] >= 0
        assert row["digest_verified"] is True
        assert row["size_verified"] is True
        assert row["container_path_verified"] is True
        parent = row["container_artifact_id"]
        if parent is None:
            assert row["display_path_or_uri"] == (
                cli_build.packet["carrier"]["path_or_uri"]
                + "!/"
                + row["member_path"]
            )
        else:
            assert parent in indexed
            assert indexed[parent]["content_kind"] == "archive"
            assert row["display_path_or_uri"] == (
                indexed[parent]["display_path_or_uri"]
                + "!/"
                + row["member_path"]
            )

        seen: set[str] = set()
        cursor = row
        while cursor["container_artifact_id"] is not None:
            current = cursor["artifact_id"]
            assert current not in seen
            seen.add(current)
            cursor = indexed[cursor["container_artifact_id"]]


def test_provider_bindings_are_exact_and_complete(cli_build: CliBuild) -> None:
    providers = [
        row["provider_binding"]
        for row in cli_build.packet["artifacts"]
        if row["provider_binding"] is not None
    ]
    assert len(providers) == EXPECTED_PROVIDER_COUNT
    assert {row["provider_artifact_id"] for row in providers} == {
        "8278987946",
        "8278994595",
        "8278995165",
    }
    assert all(row["provider"] == "github_actions" for row in providers)
    assert all(row["downloaded_sha256_matches"] is True for row in providers)
    assert all(row["downloaded_size_matches"] is True for row in providers)


def test_role_bindings_and_coverage_are_exact(cli_build: CliBuild) -> None:
    coverage = cli_build.packet["coverage"]
    assert coverage == {
        "coverage_status": "complete",
        "source_bindings_complete": True,
        "carrier_binding_complete": True,
        "artifact_graph_complete": True,
        "role_bindings_complete": True,
        "artifacts_total": EXPECTED_ARTIFACT_COUNT,
        "provider_artifacts_total": EXPECTED_PROVIDER_COUNT,
        "provider_artifacts_bound": EXPECTED_PROVIDER_COUNT,
        "role_bindings_total": EXPECTED_ROLE_REFERENCE_COUNT,
        "role_bindings_resolved": EXPECTED_ROLE_REFERENCE_COUNT,
        "missing_roles": [],
        "unresolved_artifact_ids": [],
    }
    artifact_ids = {
        row["artifact_id"] for row in cli_build.packet["artifacts"]
    }
    references: list[str] = []
    for value in cli_build.packet["role_bindings"].values():
        if isinstance(value, str):
            references.append(value)
        else:
            references.extend(value)
    assert len(references) == EXPECTED_ROLE_REFERENCE_COUNT
    assert all(reference in artifact_ids for reference in references)


def test_metadata_only_and_non_authority_boundaries_are_locked(
    cli_build: CliBuild,
) -> None:
    assert cli_build.packet["content_boundary"] == {
        "packet_payload_mode": "metadata_only",
        "artifact_bytes_embedded": False,
        "carrier_required_for_verification": True,
        "raw_secrets_included": False,
        "raw_model_inputs_included": False,
        "raw_model_outputs_included": False,
    }
    assert cli_build.packet["analysis_boundary"] == {
        "target_analysis_level": "artifact_observed",
        "runtime_observation_included": False,
        "runtime_observation_required_for_runtime_classification": True,
        "observer_in_subject_totals": False,
        "current_repository_state_substitution_allowed": False,
        "packet_is_compute_report": False,
        "packet_is_runtime_observation": False,
    }
    assert cli_build.packet["authority_boundary"] == {
        "write_mode": "subject_input_only",
        "writes_subject_run": False,
        "writes_target_repository": False,
        "mutates_carrier": False,
        "changes_release_authority": False,
        "changes_gate_policy": False,
        "changes_gate_semantics": False,
        "creates_release_decision": False,
        "creates_gate_result": False,
        "activates_compute_gate": False,
        "creates_compute_budget": False,
        "packet_is_release_authority": False,
    }


def test_direct_in_process_construction_matches_cli_bytes(
    constructed_state: ConstructedState,
    cli_build: CliBuild,
) -> None:
    assert constructed_state.rendered == cli_build.rendered
    assert constructed_state.packet == cli_build.packet


def test_generated_packet_passes_schema_and_full_semantic_validator(
    cli_build: CliBuild,
) -> None:
    validator = validator_module()
    schema = validator.load_json_bytes(SCHEMA.read_bytes(), label="schema")
    assert validator.schema_errors(schema, cli_build.packet) == []
    diagnostic, return_code, carrier, _snapshots = validator.build_diagnostic(
        schema_path=SCHEMA,
        packet_path=cli_build.output,
        explicit_carrier=ARCHIVE,
        repository_root=ROOT,
    )
    assert return_code == 0, diagnostic
    assert carrier is not None
    assert carrier.resolve(strict=True) == ARCHIVE.resolve(strict=True)
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert all(diagnostic["checks"].values())


def test_output_matches_stdout_and_all_protected_inputs_remain_unchanged(
    cli_build: CliBuild,
) -> None:
    assert cli_build.output.read_text(encoding="utf-8") == cli_build.rendered
    assert cli_build.output.read_bytes().endswith(b"\n")
    assert cli_build.protected_before == cli_build.protected_after
    assert not list(cli_build.output.parent.glob(".*.tmp"))


def test_complete_cli_is_byte_deterministic(cli_build: CliBuild) -> None:
    second = run_producer()
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stderr == ""
    assert second.stdout == cli_build.rendered


def test_exact_carrier_outside_repository_uses_file_uri_and_validates(
    tmp_path: Path,
) -> None:
    carrier = tmp_path / ARCHIVE.name
    shutil.copy2(ARCHIVE, carrier)
    result = run_producer(carrier=carrier)
    assert result.returncode == 0, result.stdout + result.stderr
    packet = strict_json_text(result.stdout, label="external-carrier packet")
    assert packet["carrier"]["path_or_uri"] == carrier.resolve().as_uri()
    assert all(
        row["display_path_or_uri"].startswith(carrier.resolve().as_uri() + "!/")
        for row in packet["artifacts"]
        if row["container_artifact_id"] is None
    )


# ---------------------------------------------------------------------------
# Git executable, environment, repository, and dependency binding
# ---------------------------------------------------------------------------


def test_git_child_environment_drops_caller_command_and_git_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/attacker/bin")
    monkeypatch.setenv("PATHEXT", ".ATTACK;.EXE")
    for key, value in POISONED_GIT_ENVIRONMENT.items():
        monkeypatch.setenv(key, value)

    trusted_git = PRODUCER_MODULE._trusted_git_executable()
    child = PRODUCER_MODULE._sanitized_git_environment(trusted_git)
    fixed_keys = {
        "PATH",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_COUNT",
        "GIT_OPTIONAL_LOCKS",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_TERMINAL_PROMPT",
        "LC_ALL",
        "LANG",
    }
    assert set(child) <= set(PRODUCER_MODULE.GIT_PROCESS_ENV_ALLOWLIST) | fixed_keys
    assert "PATH" not in PRODUCER_MODULE.GIT_PROCESS_ENV_ALLOWLIST
    assert "PATHEXT" not in PRODUCER_MODULE.GIT_PROCESS_ENV_ALLOWLIST
    assert child["PATH"] == str(trusted_git.parent)
    assert child["PATH"] != "/attacker/bin"
    assert "PATHEXT" not in child
    for key in POISONED_GIT_ENVIRONMENT:
        if key == "GIT_CONFIG_COUNT":
            assert child[key] == "0"
        else:
            assert key not in child


def test_trusted_git_is_absolute_regular_and_self_resolving() -> None:
    trusted_git = PRODUCER_MODULE._trusted_git_executable()
    assert trusted_git.is_absolute()
    assert trusted_git.resolve(strict=True) == trusted_git
    assert trusted_git.is_file()
    assert not trusted_git.is_symlink()
    assert os.access(trusted_git, os.X_OK)


def test_relative_trusted_git_candidate_is_rejected() -> None:
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="git_executable_untrusted: path_not_absolute",
    ):
        PRODUCER_MODULE._validate_trusted_git_executable(Path("git"))


def test_symlink_trusted_git_candidate_is_rejected(tmp_path: Path) -> None:
    link = tmp_path / "git"
    try:
        link.symlink_to(PRODUCER_MODULE._trusted_git_executable())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="git_executable_untrusted: symlink_or_alias_path",
    ):
        PRODUCER_MODULE._validate_trusted_git_executable(link)


def test_untrusted_posix_candidate_component_is_rejected(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX ownership and writable-component check")
    candidate = tmp_path / "git"
    candidate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    candidate.chmod(0o755)
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="non_root_owned_component|writable_component",
    ):
        PRODUCER_MODULE._validate_trusted_git_executable(candidate)


def test_no_trusted_candidate_fails_without_path_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-git"
    PRODUCER_MODULE._trusted_git_executable.cache_clear()
    monkeypatch.setattr(
        PRODUCER_MODULE,
        "_trusted_git_executable_candidates",
        lambda: (missing,),
    )
    try:
        with pytest.raises(
            PRODUCER_MODULE.BuilderError,
            match="git_process_executable_unavailable",
        ):
            PRODUCER_MODULE._trusted_git_executable()
    finally:
        PRODUCER_MODULE._trusted_git_executable.cache_clear()


def test_windows_candidates_use_system_and_machine_wide_roots() -> None:
    default = PRODUCER_MODULE._windows_trusted_git_executable_candidate_strings(
        system_windows_directory=r"C:\Windows",
    )
    assert default == (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
    )

    relocated = PRODUCER_MODULE._windows_trusted_git_executable_candidate_strings(
        system_windows_directory=r"C:\Windows",
        registry_program_files_roots=(
            r"E:\Trusted Programs",
            r"C:\Program Files",
            r"e:\trusted programs",
            r"relative\programs",
            r"%SYSTEMDRIVE%\Program Files",
        ),
    )
    assert relocated[:2] == (
        r"E:\Trusted Programs\Git\cmd\git.exe",
        r"E:\Trusted Programs\Git\bin\git.exe",
    )
    assert relocated.count(r"C:\Program Files\Git\cmd\git.exe") == 1
    assert all("%" not in value for value in relocated)
    assert all(not value.startswith("relative") for value in relocated)


def test_invalid_windows_system_directory_fails_closed() -> None:
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="windows_system_directory_invalid",
    ):
        PRODUCER_MODULE._windows_trusted_git_executable_candidate_strings(
            system_windows_directory=r"Windows",
        )


def test_repository_root_must_equal_git_top_level() -> None:
    nested = ROOT / "tests"
    assert nested.is_dir()
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="git_repository_root_mismatch",
    ):
        PRODUCER_MODULE._verified_git_repository_root(nested)


def test_committed_dependency_binding_detects_working_tree_drift(
    tmp_path: Path,
) -> None:
    relative = "tools/dependency.py"
    repository, revision = create_git_repository(
        tmp_path,
        files={relative: b"committed dependency\n"},
    )
    path = PRODUCER_MODULE.committed_repository_file(
        repository,
        revision=revision,
        relative_path=relative,
        label="dependency",
    )
    assert path.read_bytes() == b"committed dependency\n"
    path.write_bytes(b"working-tree drift\n")
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="dependency_committed_bytes_mismatch",
    ):
        PRODUCER_MODULE.committed_repository_file(
            repository,
            revision=revision,
            relative_path=relative,
            label="dependency",
        )


def test_producer_identity_binds_exact_synthetic_committed_source(
    tmp_path: Path,
) -> None:
    relative = PRODUCER_MODULE.PRODUCER_SOURCE_PATH
    source_bytes = b"#!/usr/bin/env python3\nprint('producer')\n"
    repository, revision = create_git_repository(
        tmp_path,
        files={relative: source_bytes},
    )
    path = repository / relative
    identity = PRODUCER_MODULE.producer_identity(
        repository_root=repository,
        revision=revision,
        source_path=path,
        execution_identity="synthetic producer execution",
        producer_run_key="SYNTHETIC_PRODUCER_RUN=1",
    )
    assert identity["producer_source_revision"] == revision
    assert identity["producer_source_sha256"] == sha256_bytes(source_bytes)
    assert identity["producer_source"] == relative

    path.write_bytes(b"working-tree producer drift\n")
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="producer_source_bytes_mismatch",
    ):
        PRODUCER_MODULE.producer_identity(
            repository_root=repository,
            revision=revision,
            source_path=path,
            execution_identity="synthetic producer execution",
            producer_run_key="SYNTHETIC_PRODUCER_RUN=1",
        )


def test_empty_producer_execution_identity_and_run_key_are_rejected() -> None:
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="producer_execution_identity_missing_or_invalid",
    ):
        PRODUCER_MODULE.producer_identity(
            repository_root=ROOT,
            revision=current_head(),
            source_path=PRODUCER,
            execution_identity="",
            producer_run_key=PRODUCER_RUN_KEY,
        )
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="producer_run_key_missing_or_invalid",
    ):
        PRODUCER_MODULE.producer_identity(
            repository_root=ROOT,
            revision=current_head(),
            source_path=PRODUCER,
            execution_identity=EXECUTION_IDENTITY,
            producer_run_key="",
        )


def test_fake_git_on_caller_path_cannot_forge_source_reads(
    tmp_path: Path,
) -> None:
    forged_revision = "f" * 40
    forged_path = "attacker-source.txt"
    forged_bytes = b"attacker-controlled historical source"
    fake_git, marker = create_fake_git_executable(
        tmp_path,
        repository_root=ROOT,
        forged_revision=forged_revision,
        forged_path=forged_path,
        forged_bytes=forged_bytes,
    )
    attacker_bin = fake_git.parent

    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{forged_revision}:{forged_path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": str(attacker_bin)},
    )
    assert raw.returncode == 0
    assert raw.stdout == forged_bytes
    assert marker.is_file()
    marker.unlink()

    with pytest.MonkeyPatch.context() as poisoned:
        poisoned.setenv("PATH", str(attacker_bin))
        with pytest.raises(
            PRODUCER_MODULE.BuilderError,
            match="git_blob_unavailable",
        ):
            PRODUCER_MODULE._git_blob_bytes(
                ROOT,
                revision=forged_revision,
                path=forged_path,
            )
    assert not marker.exists()

    complete = run_producer(extra_env={"PATH": str(attacker_bin)})
    assert complete.returncode == 0, complete.stdout + complete.stderr
    assert not marker.exists()


def test_complete_cli_ignores_poisoned_git_environment() -> None:
    result = run_producer(extra_env=POISONED_GIT_ENVIRONMENT)
    assert result.returncode == 0, result.stdout + result.stderr
    packet = strict_json_text(result.stdout, label="poisoned-environment packet")
    assert packet["ok"] is True
    assert packet["producer"]["producer_source_revision"] == current_head()


def test_complete_cli_does_not_require_caller_path_or_pathext() -> None:
    result = run_producer(extra_env={"PATH": None, "PATHEXT": None})
    assert result.returncode == 0, result.stdout + result.stderr
    packet = strict_json_text(result.stdout, label="missing-path packet")
    assert packet["ok"] is True


# ---------------------------------------------------------------------------
# Carrier, archive, provider, subject, and role fail-closed paths
# ---------------------------------------------------------------------------


def test_missing_and_symlink_carriers_are_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing.zip"
    with pytest.raises(PRODUCER_MODULE.BuilderError, match="carrier_missing"):
        PRODUCER_MODULE.load_exact_bundle(
            carrier_path=missing,
            fixed_builder=fixed_builder_module(),
        )

    link = tmp_path / "carrier-link.zip"
    try:
        link.symlink_to(ARCHIVE)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")
    with pytest.raises(PRODUCER_MODULE.BuilderError, match="carrier_symlink_rejected"):
        PRODUCER_MODULE.load_exact_bundle(
            carrier_path=link,
            fixed_builder=fixed_builder_module(),
        )


def test_carrier_digest_and_size_drift_are_rejected(tmp_path: Path) -> None:
    same_size = tmp_path / "same-size-corrupt.zip"
    payload = bytearray(ARCHIVE.read_bytes())
    payload[len(payload) // 2] ^= 0x01
    same_size.write_bytes(payload)
    assert same_size.stat().st_size == EXPECTED_CARRIER_SIZE_BYTES
    with pytest.raises(
        Exception,
        match="preservation_archive_sha256_mismatch",
    ):
        PRODUCER_MODULE.load_exact_bundle(
            carrier_path=same_size,
            fixed_builder=fixed_builder_module(),
        )

    truncated = tmp_path / "truncated.zip"
    truncated.write_bytes(ARCHIVE.read_bytes()[:-1])
    with pytest.raises(
        Exception,
        match="preservation_archive_size_mismatch",
    ):
        PRODUCER_MODULE.load_exact_bundle(
            carrier_path=truncated,
            fixed_builder=fixed_builder_module(),
        )


@pytest.mark.parametrize(
    ("kind", "expected_fragment"),
    [
        ("unsafe", "unsafe_member_path"),
        ("duplicate", "duplicate_member"),
        ("symlink", "symlink_member"),
    ],
)
def test_unsafe_duplicate_and_symlink_zip_members_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    expected_fragment: str,
) -> None:
    variant = tmp_path / f"{kind}.zip"
    if kind == "unsafe":
        copy_zip_with_extra_member(
            ARCHIVE,
            variant,
            name="../escape.txt",
        )
    elif kind == "duplicate":
        copy_zip_with_duplicate_member(ARCHIVE, variant)
    else:
        copy_zip_with_extra_member(
            ARCHIVE,
            variant,
            name="pulse-ci-6066-preservation-v0/UNDECLARED_SYMLINK",
            symlink=True,
        )

    monkeypatch.setattr(
        PRODUCER_MODULE,
        "EXPECTED_CARRIER_SHA256",
        sha256_file(variant),
    )
    monkeypatch.setattr(
        PRODUCER_MODULE,
        "EXPECTED_CARRIER_SIZE",
        variant.stat().st_size,
    )
    with pytest.raises(Exception, match=expected_fragment):
        PRODUCER_MODULE.load_exact_bundle(
            carrier_path=variant,
            fixed_builder=fixed_builder_module(),
        )


def test_provider_manifest_digest_state_drift_is_rejected(
    constructed_state: ConstructedState,
) -> None:
    record = copy.deepcopy(
        constructed_state.inputs.bundle.manifest["github_artifacts"][0]
    )
    record["github_digest_match"] = False
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="provider_digest_mismatch",
    ):
        PRODUCER_MODULE.provider_binding(record)


def test_subject_source_commit_and_policy_set_drift_are_rejected(
    constructed_state: ConstructedState,
) -> None:
    source_drift = copy.deepcopy(constructed_state.inputs)
    source_drift.bundle.manifest["source_commit"] = "0" * 40
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="subject_source_commit_not_unique|expected_commit_mismatch",
    ):
        PRODUCER_MODULE.build_subject_and_sources(
            inputs=source_drift,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )

    policy_drift = copy.deepcopy(constructed_state.inputs)
    policy_drift.bundle.manifest["active_policy_sets"] = ["required"]
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="decision_policy_sets_mismatch|binding_policy_sets_mismatch",
    ):
        PRODUCER_MODULE.build_subject_and_sources(
            inputs=policy_drift,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )


def test_missing_candidate_role_binding_is_rejected(
    constructed_state: ConstructedState,
) -> None:
    without_candidates = tuple(
        item
        for item in constructed_state.inputs.artifacts
        if item.role != "candidate_record"
    )
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="candidate_records_missing",
    ):
        PRODUCER_MODULE.role_bindings(without_candidates)


def test_coverage_downgrades_when_source_binding_is_incomplete(
    constructed_state: ConstructedState,
) -> None:
    sources = copy.deepcopy(constructed_state.sources)
    sources["additional_sources"][0]["source_revision"] = None
    coverage = PRODUCER_MODULE.coverage(constructed_state.inputs, sources)
    assert coverage["coverage_status"] == "partial"
    assert coverage["source_bindings_complete"] is False
    assert coverage["artifact_graph_complete"] is True
    assert coverage["role_bindings_complete"] is True


# ---------------------------------------------------------------------------
# Determinism, schema rejection, and semantic rejection
# ---------------------------------------------------------------------------


def test_build_packet_is_deterministic_for_identical_explicit_inputs(
    constructed_state: ConstructedState,
) -> None:
    first = PRODUCER_MODULE.build_packet(
        inputs=constructed_state.inputs,
        subject=constructed_state.subject,
        sources=constructed_state.sources,
        producer=constructed_state.producer,
        packet_created_utc=PACKET_CREATED_UTC,
    )
    second = PRODUCER_MODULE.build_packet(
        inputs=constructed_state.inputs,
        subject=constructed_state.subject,
        sources=constructed_state.sources,
        producer=constructed_state.producer,
        packet_created_utc=PACKET_CREATED_UTC,
    )
    assert first == second
    assert PRODUCER_MODULE.render_json(first) == PRODUCER_MODULE.render_json(second)


def test_packet_id_changes_with_explicit_time_or_producer_run_key(
    constructed_state: ConstructedState,
) -> None:
    later = PRODUCER_MODULE.build_packet(
        inputs=constructed_state.inputs,
        subject=constructed_state.subject,
        sources=constructed_state.sources,
        producer=constructed_state.producer,
        packet_created_utc="2026-07-23T18:00:01Z",
    )
    changed_producer = copy.deepcopy(constructed_state.producer)
    changed_producer["producer_run_key"] = PRODUCER_RUN_KEY + "|REPLAY=2"
    changed = PRODUCER_MODULE.build_packet(
        inputs=constructed_state.inputs,
        subject=constructed_state.subject,
        sources=constructed_state.sources,
        producer=changed_producer,
        packet_created_utc=PACKET_CREATED_UTC,
    )
    assert later["packet_identity"]["packet_id"] != (
        constructed_state.packet["packet_identity"]["packet_id"]
    )
    assert changed["packet_identity"]["packet_id"] != (
        constructed_state.packet["packet_identity"]["packet_id"]
    )
    assert later["subject"] == constructed_state.packet["subject"]
    assert changed["carrier"] == constructed_state.packet["carrier"]


def test_schema_invalid_generated_packet_is_rejected_before_output(
    constructed_state: ConstructedState,
) -> None:
    packet = copy.deepcopy(constructed_state.packet)
    packet["producer"]["production_mode"] = "example"
    rendered = PRODUCER_MODULE.render_json(packet)
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="generated_packet_schema_invalid",
    ):
        PRODUCER_MODULE.validate_generated_packet(
            packet=packet,
            rendered=rendered,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )


def test_schema_valid_but_semantically_mismatched_packet_is_rejected(
    constructed_state: ConstructedState,
) -> None:
    packet = copy.deepcopy(constructed_state.packet)
    packet["subject"]["decision"] = "BLOCK"
    rendered = PRODUCER_MODULE.render_json(packet)
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="generated_packet_rejected",
    ):
        PRODUCER_MODULE.validate_generated_packet(
            packet=packet,
            rendered=rendered,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )


def test_noncanonical_packet_timestamp_fails_closed() -> None:
    result = run_producer(packet_created_utc="2026-07-23T18:00:00+00:00")
    diagnostic = assert_producer_failure(
        result,
        "canonical",
        expected_returncode=(1, 2),
    )
    assert any(
        "UTC" in str(error) or "packet_created_utc" in str(error)
        for error in diagnostic["errors"]
    )


# ---------------------------------------------------------------------------
# Output safety, atomicity, and protected-input mutation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
    ],
)
def test_authority_surface_output_names_are_rejected(
    tmp_path: Path,
    constructed_state: ConstructedState,
    name: str,
) -> None:
    output = tmp_path / name
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="refusing_authority_surface_output",
    ):
        PRODUCER_MODULE.reject_output(
            output=output,
            packet=constructed_state.packet,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            validator_path=VALIDATOR,
            fixed_builder_path=FIXED_SOURCE_BUILDER,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )
    assert not output.exists()


def test_output_inside_repository_is_rejected(
    constructed_state: ConstructedState,
) -> None:
    output = ROOT / "generated-observed-subject-input-packet-v0.json"
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="refusing_output_inside_repository",
    ):
        PRODUCER_MODULE.reject_output(
            output=output,
            packet=constructed_state.packet,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            validator_path=VALIDATOR,
            fixed_builder_path=FIXED_SOURCE_BUILDER,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )
    assert not output.exists()


def test_trusted_git_executable_is_protected_from_output_overwrite(
    constructed_state: ConstructedState,
) -> None:
    trusted_git = PRODUCER_MODULE._trusted_git_executable()
    before = sha256_file(trusted_git)
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="refusing_to_overwrite_input",
    ):
        PRODUCER_MODULE.reject_output(
            output=trusted_git,
            packet=constructed_state.packet,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            validator_path=VALIDATOR,
            fixed_builder_path=FIXED_SOURCE_BUILDER,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )
    assert sha256_file(trusted_git) == before


def test_symlink_output_path_is_rejected(
    tmp_path: Path,
    constructed_state: ConstructedState,
) -> None:
    target = tmp_path / "target.json"
    link = tmp_path / "output.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="output_symlink_rejected",
    ):
        PRODUCER_MODULE.reject_output(
            output=link,
            packet=constructed_state.packet,
            carrier_path=ARCHIVE,
            schema_path=SCHEMA,
            validator_path=VALIDATOR,
            fixed_builder_path=FIXED_SOURCE_BUILDER,
            repository_root=ROOT,
            validator=constructed_state.validator,
        )
    assert not target.exists()


def test_atomic_write_requires_existing_parent_and_leaves_no_temp(
    tmp_path: Path,
) -> None:
    missing_parent = tmp_path / "missing" / "output.json"
    with pytest.raises(
        PRODUCER_MODULE.BuilderError,
        match="output_parent_missing_or_not_directory",
    ):
        PRODUCER_MODULE.atomic_write(missing_parent, "{}\n")

    output = tmp_path / "output.json"
    PRODUCER_MODULE.atomic_write(output, "{\"ok\": true}\n")
    assert output.read_text(encoding="utf-8") == '{"ok": true}\n'
    assert not list(tmp_path.glob(".output.json.*.tmp"))


def test_protected_input_mutation_after_validation_prevents_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    carrier = tmp_path / ARCHIVE.name
    shutil.copy2(ARCHIVE, carrier)
    output = tmp_path / "observed-packet.json"
    original_validate = PRODUCER_MODULE.validate_generated_packet

    def mutate_after_validation(**kwargs: Any) -> None:
        original_validate(**kwargs)
        carrier.write_bytes(carrier.read_bytes() + b"mutation")

    monkeypatch.setattr(
        PRODUCER_MODULE,
        "validate_generated_packet",
        mutate_after_validation,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(PRODUCER),
            "--carrier",
            str(carrier),
            "--repository-root",
            str(ROOT),
            "--packet-created-utc",
            PACKET_CREATED_UTC,
            "--producer-run-key",
            PRODUCER_RUN_KEY,
            "--ci-workflow-or-job-identity",
            EXECUTION_IDENTITY,
            "--output",
            str(output),
        ],
    )
    assert PRODUCER_MODULE.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    diagnostic = strict_json_text(captured.err, label="mutation diagnostic")
    assert any(
        "protected_inputs_after_build_mismatch" in str(error)
        for error in diagnostic["errors"]
    )
    assert not output.exists()


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_build_pulsemech_compute_subject_input_packet_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_build_pulsemech_compute_subject_input_packet_v0()
