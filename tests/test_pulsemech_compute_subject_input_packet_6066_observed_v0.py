#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest


ROOT = Path(__file__).resolve().parents[1]

OBSERVED_PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_observed_v0.json"
)
EXAMPLE_PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)
SCHEMA = ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
CARRIER = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"

PRODUCER_RELATIVE_PATH = (
    "tools/build_pulsemech_compute_subject_input_packet_v0.py"
)
PINNED_PRODUCER_REVISION = "3cd57dc9e88e6f804dbb134c864f4207688bddc2"
PINNED_PRODUCER_SHA256 = (
    "152e9ed67bf10389726ab7e27d59005afe62d23488e8cd13ffa58443bee13d18"
)
PINNED_PRODUCER_LINE_COUNT = 1963
PINNED_PRODUCER_BYTE_SIZE = 67686

EXPECTED_PACKET_SHA256 = (
    "b457383356d330ae40843a47f9adb83c4e7d7f14447218f951ca71e4ee287467"
)
EXPECTED_PACKET_LINE_COUNT = 738
EXPECTED_PACKET_BYTE_SIZE = 45914

EXPECTED_CARRIER_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_CARRIER_BYTE_SIZE = 44660

PACKET_CREATED_UTC = "2026-07-23T18:00:00Z"
PRODUCER_RUN_KEY = (
    "OFFLINE_PRODUCER=pulsemech-subject-input-fixed-source-6066-v0|ATTEMPT=1"
)
EXECUTION_IDENTITY = (
    "PULSEmech fixed-source subject-input producer / PULSE CI #6066 replay"
)
EXPECTED_PACKET_ID = (
    "subject-input:pulse-ci-6066/fixed-source-adapter/851cffe9ebee9399/v0"
)
EXPECTED_SUBJECT_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)

PRODUCER_INDEPENDENT_SURFACES = (
    "subject",
    "analysis_boundary",
    "authority_sources",
    "carrier",
    "artifacts",
    "role_bindings",
    "coverage",
    "content_boundary",
    "authority_boundary",
    "ok",
    "errors",
)


@dataclass(frozen=True)
class HistoricalReplay:
    worktree_head: str
    output_bytes: bytes
    stdout_text: str
    packet: dict[str, Any]


# ---------------------------------------------------------------------------
# Strict parsing, canonicalization, and module loading
# ---------------------------------------------------------------------------


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_bytes(value: bytes, *, label: str) -> dict[str, Any]:
    try:
        text = value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"{label}: invalid UTF-8: {exc}") from exc

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise AssertionError(f"{label}: duplicate JSON key: {key}")
            result[key] = item
        return result

    def reject_non_finite(item: str) -> None:
        raise AssertionError(f"{label}: non-finite JSON value: {item}")

    loaded = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(loaded, dict), f"{label}: expected a JSON object"
    return loaded


def strict_json_file(path: Path, *, label: str) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes(), label=label)


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def import_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR_MODULE = import_module(
    VALIDATOR,
    "pulsemech_subject_input_packet_validator_for_observed_6066_replay",
)


def observed_packet() -> dict[str, Any]:
    return strict_json_file(OBSERVED_PACKET, label="checked-in observed packet")


def example_packet() -> dict[str, Any]:
    return strict_json_file(EXAMPLE_PACKET, label="checked-in historical-data fixture")


def expected_packet_id(packet: dict[str, Any]) -> str:
    material = (
        packet["producer"]["producer_run_key"]
        + "\x00"
        + packet["packet_identity"]["packet_created_utc"]
        + "\x00"
        + packet["carrier"]["sha256"]
    ).encode("utf-8")
    suffix = sha256_bytes(material)[:16]
    return (
        "subject-input:pulse-ci-6066/fixed-source-adapter/"
        f"{suffix}/v0"
    )


def assert_pinned_observed_contract(packet: dict[str, Any]) -> None:
    assert packet["schema_version"] == "pulsemech_compute_subject_input_packet_v0"
    assert packet["packet_type"] == "pulsemech_compute_subject_input_packet"
    assert packet["record_status"] == "observed"
    assert "fixture_provenance" not in packet
    assert packet["ok"] is True
    assert packet["errors"] == []

    assert packet.get("producer") == {
        "ci_workflow_or_job_identity": EXECUTION_IDENTITY,
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": "PULSEmech compute subject-input packet producer",
        "producer_run_key": PRODUCER_RUN_KEY,
        "producer_source": PRODUCER_RELATIVE_PATH,
        "producer_source_revision": PINNED_PRODUCER_REVISION,
        "producer_source_sha256": PINNED_PRODUCER_SHA256,
        "producer_version": "0.1.0",
        "production_mode": "fixed_source_adapter",
    }

    identity = packet["packet_identity"]
    assert identity["canonicalization"] == "json-sort-keys-utf8-newline"
    assert identity["carrier_id"] == "carrier:preservation/pulse-ci-6066/v0"
    assert identity["packet_created_utc"] == PACKET_CREATED_UTC
    assert identity["packet_scope"] == "fixed_source_adapter"
    assert identity["subject_run_key"] == EXPECTED_SUBJECT_RUN_KEY
    assert identity["packet_id"] == EXPECTED_PACKET_ID
    assert identity["packet_id"] == expected_packet_id(packet)

    subject = packet["subject"]
    assert subject["repository"] == "HKati/pulse-release-gates-0.1"
    assert subject["workflow_name"] == "PULSE CI"
    assert subject["workflow_run_id"] == 29249887581
    assert subject["workflow_run_number"] == 6066
    assert subject["workflow_run_attempt"] == 1
    assert subject["subject_run_key"] == EXPECTED_SUBJECT_RUN_KEY
    assert subject["source_commit"] == "46b639706e23f80fe296a8893be18e2b5ab21f7e"
    assert subject["release_candidate_id"] == "main"
    assert subject["decision"] == "ALLOW"

    carrier = packet["carrier"]
    assert carrier["carrier_kind"] == "preservation_archive"
    assert (
        carrier["path_or_uri"]
        == "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
    )
    assert carrier["sha256"] == EXPECTED_CARRIER_SHA256
    assert carrier["size_bytes"] == EXPECTED_CARRIER_BYTE_SIZE
    assert carrier["root_prefix"] == "pulse-ci-6066-preservation-v0"
    assert carrier["immutable"] is True

    assert len(packet["artifacts"]) == 32
    assert sum(
        row.get("provider_binding") is not None
        for row in packet["artifacts"]
    ) == 3

    coverage = packet["coverage"]
    assert coverage["coverage_status"] == "complete"
    assert coverage["source_bindings_complete"] is True
    assert coverage["carrier_binding_complete"] is True
    assert coverage["artifact_graph_complete"] is True
    assert coverage["role_bindings_complete"] is True
    assert coverage["artifacts_total"] == 32
    assert coverage["provider_artifacts_total"] == 3
    assert coverage["provider_artifacts_bound"] == 3
    assert coverage["role_bindings_total"] == 28
    assert coverage["role_bindings_resolved"] == 28
    assert coverage["missing_roles"] == []
    assert coverage["unresolved_artifact_ids"] == []

    assert packet["content_boundary"] == {
        "artifact_bytes_embedded": False,
        "carrier_required_for_verification": True,
        "packet_payload_mode": "metadata_only",
        "raw_model_inputs_included": False,
        "raw_model_outputs_included": False,
        "raw_secrets_included": False,
    }
    assert packet["authority_boundary"] == {
        "activates_compute_gate": False,
        "changes_gate_policy": False,
        "changes_gate_semantics": False,
        "changes_release_authority": False,
        "creates_compute_budget": False,
        "creates_gate_result": False,
        "creates_release_decision": False,
        "mutates_carrier": False,
        "packet_is_release_authority": False,
        "write_mode": "subject_input_only",
        "writes_subject_run": False,
        "writes_target_repository": False,
    }

    fixture = example_packet()
    for surface in PRODUCER_INDEPENDENT_SURFACES:
        assert packet[surface] == fixture[surface], surface


# ---------------------------------------------------------------------------
# Trusted Git worktree replay
# ---------------------------------------------------------------------------


def trusted_git() -> Path:
    git = VALIDATOR_MODULE._trusted_git_executable()
    assert isinstance(git, Path)
    assert git.is_absolute()
    assert git.is_file()
    return git


def git_environment(git: Path) -> dict[str, str]:
    environment = VALIDATOR_MODULE._sanitized_git_environment(git)
    assert environment["PATH"] == str(git.parent)
    return environment


def run_git(
    repository_root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    root = repository_root.resolve(strict=True)
    git = trusted_git()
    completed = subprocess.run(
        [
            str(git),
            "--no-pager",
            "--no-replace-objects",
            "-c",
            f"safe.directory={root}",
            "-C",
            str(root),
            *arguments,
        ],
        check=False,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(git),
    )
    if check:
        assert completed.returncode == 0, (
            f"git {' '.join(arguments)} failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


@contextmanager
def detached_producer_worktree() -> Iterator[tuple[Path, Path]]:
    workspace_parent = ROOT.parent.resolve(strict=True)
    workspace = Path(
        tempfile.mkdtemp(
            prefix=".pulsemech-observed-6066-replay-",
            dir=str(workspace_parent),
        )
    )
    worktree = workspace / "producer-revision"
    output = workspace / "regenerated-observed-packet.json"
    added = False

    try:
        run_git(
            ROOT,
            [
                "worktree",
                "add",
                "--detach",
                "--force",
                str(worktree),
                PINNED_PRODUCER_REVISION,
            ],
        )
        added = True

        head = run_git(worktree, ["rev-parse", "HEAD"]).stdout.strip()
        assert head == PINNED_PRODUCER_REVISION

        yield worktree, output
    finally:
        if added:
            run_git(
                ROOT,
                ["worktree", "remove", "--force", str(worktree)],
                check=False,
            )
            run_git(ROOT, ["worktree", "prune"], check=False)
        shutil.rmtree(workspace, ignore_errors=True)


def execute_historical_producer(worktree: Path, output: Path) -> HistoricalReplay:
    producer = worktree / PRODUCER_RELATIVE_PATH
    carrier = worktree / CARRIER.name

    assert producer.is_file()
    assert carrier.is_file()
    assert not output.exists()
    assert not output.resolve().is_relative_to(worktree.resolve(strict=True))
    assert not output.resolve().is_relative_to(ROOT.resolve(strict=True))

    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [
            sys.executable,
            str(producer),
            "--carrier",
            str(carrier),
            "--repository-root",
            str(worktree),
            "--packet-created-utc",
            PACKET_CREATED_UTC,
            "--producer-run-key",
            PRODUCER_RUN_KEY,
            "--ci-workflow-or-job-identity",
            EXECUTION_IDENTITY,
            "--output",
            str(output),
        ],
        cwd=worktree,
        check=False,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )

    assert result.returncode == 0, (
        f"historical producer failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert result.stderr == ""
    assert output.is_file()
    assert not output.is_symlink()

    output_bytes = output.read_bytes()
    assert result.stdout.encode("utf-8") == output_bytes
    packet = strict_json_bytes(output_bytes, label="historically replayed packet")

    head = run_git(worktree, ["rev-parse", "HEAD"]).stdout.strip()
    return HistoricalReplay(
        worktree_head=head,
        output_bytes=output_bytes,
        stdout_text=result.stdout,
        packet=packet,
    )


@pytest.fixture(scope="session")
def historical_replay() -> HistoricalReplay:
    with detached_producer_worktree() as (worktree, output):
        yield execute_historical_producer(worktree, output)


# ---------------------------------------------------------------------------
# Exact checked-in proof and independent validation
# ---------------------------------------------------------------------------


def test_checked_in_observed_packet_identity_is_pinned() -> None:
    payload = OBSERVED_PACKET.read_bytes()

    assert len(payload.splitlines()) == EXPECTED_PACKET_LINE_COUNT
    assert len(payload) == EXPECTED_PACKET_BYTE_SIZE
    assert sha256_bytes(payload) == EXPECTED_PACKET_SHA256

    packet = strict_json_bytes(payload, label="checked-in observed packet")
    assert canonical_json_bytes(packet) == payload
    assert_pinned_observed_contract(packet)


def test_pinned_producer_blob_identity_is_reconstructable_from_git() -> None:
    payload = VALIDATOR_MODULE._git_blob_bytes(
        ROOT,
        revision=PINNED_PRODUCER_REVISION,
        path=PRODUCER_RELATIVE_PATH,
    )

    assert len(payload.splitlines()) == PINNED_PRODUCER_LINE_COUNT
    assert len(payload) == PINNED_PRODUCER_BYTE_SIZE
    assert sha256_bytes(payload) == PINNED_PRODUCER_SHA256


def test_observed_and_example_packets_share_producer_independent_surfaces() -> None:
    observed = observed_packet()
    example = example_packet()

    assert observed["record_status"] == "observed"
    assert "producer" in observed
    assert "fixture_provenance" not in observed

    assert example["record_status"] == "example"
    assert "producer" not in example
    assert example["fixture_provenance"]["source_data_status"] == (
        "historical_observed"
    )

    for surface in PRODUCER_INDEPENDENT_SURFACES:
        assert observed[surface] == example[surface], surface


def run_validator(
    packet_path: Path,
    *,
    carrier_path: Path = CARRIER,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--schema",
            str(SCHEMA),
            "--packet",
            str(packet_path),
            "--carrier",
            str(carrier_path),
            "--repository-root",
            str(ROOT),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_checked_in_observed_packet_passes_strict_validator() -> None:
    result = run_validator(OBSERVED_PACKET)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")

    diagnostic = strict_json_bytes(
        result.stdout.encode("utf-8"),
        label="strict observed-packet diagnostic",
    )
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert diagnostic["checks"]
    assert all(diagnostic["checks"].values())


def test_pinned_historical_producer_replays_checked_in_bytes(
    historical_replay: HistoricalReplay,
) -> None:
    expected = OBSERVED_PACKET.read_bytes()

    assert historical_replay.worktree_head == PINNED_PRODUCER_REVISION
    assert historical_replay.output_bytes == expected
    assert historical_replay.stdout_text.encode("utf-8") == expected
    assert historical_replay.packet == observed_packet()
    assert_pinned_observed_contract(historical_replay.packet)


# ---------------------------------------------------------------------------
# Fail-closed proof mutations
# ---------------------------------------------------------------------------


Mutation = Callable[[dict[str, Any]], None]


def mutate_producer_revision(packet: dict[str, Any]) -> None:
    packet["producer"]["producer_source_revision"] = "0" * 40


def mutate_producer_digest(packet: dict[str, Any]) -> None:
    packet["producer"]["producer_source_sha256"] = "0" * 64


def mutate_producer_run_key(packet: dict[str, Any]) -> None:
    packet["producer"]["producer_run_key"] += "|DRIFT=1"


def mutate_packet_created_utc(packet: dict[str, Any]) -> None:
    packet["packet_identity"]["packet_created_utc"] = "2026-07-23T18:00:01Z"


def mutate_packet_id(packet: dict[str, Any]) -> None:
    packet["packet_identity"]["packet_id"] = (
        "subject-input:pulse-ci-6066/fixed-source-adapter/"
        "0000000000000000/v0"
    )


def add_fixture_provenance(packet: dict[str, Any]) -> None:
    packet["fixture_provenance"] = copy.deepcopy(
        example_packet()["fixture_provenance"]
    )


def remove_producer(packet: dict[str, Any]) -> None:
    packet.pop("producer")


def mutate_record_status(packet: dict[str, Any]) -> None:
    packet["record_status"] = "example"


def mutate_packet_scope(packet: dict[str, Any]) -> None:
    packet["packet_identity"]["packet_scope"] = "example"


def mutate_carrier_digest(packet: dict[str, Any]) -> None:
    packet["carrier"]["sha256"] = "0" * 64


def mutate_carrier_size(packet: dict[str, Any]) -> None:
    packet["carrier"]["size_bytes"] += 1


def mutate_subject_run_key(packet: dict[str, Any]) -> None:
    packet["subject"]["subject_run_key"] += "|DRIFT=1"


def mutate_artifact_digest(packet: dict[str, Any]) -> None:
    packet["artifacts"][0]["sha256"] = "0" * 64


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(mutate_producer_revision, id="producer-revision"),
        pytest.param(mutate_producer_digest, id="producer-digest"),
        pytest.param(mutate_producer_run_key, id="producer-run-key"),
        pytest.param(mutate_packet_created_utc, id="packet-created-utc"),
        pytest.param(mutate_packet_id, id="packet-id"),
        pytest.param(add_fixture_provenance, id="fixture-provenance"),
        pytest.param(remove_producer, id="producer-removed"),
        pytest.param(mutate_record_status, id="record-status"),
        pytest.param(mutate_packet_scope, id="packet-scope"),
        pytest.param(mutate_carrier_digest, id="carrier-digest"),
        pytest.param(mutate_carrier_size, id="carrier-size"),
        pytest.param(mutate_subject_run_key, id="subject-run-key"),
        pytest.param(mutate_artifact_digest, id="artifact-digest"),
    ],
)
def test_pinned_observed_contract_rejects_mutations(mutation: Mutation) -> None:
    packet = copy.deepcopy(observed_packet())
    mutation(packet)

    with pytest.raises(AssertionError):
        assert_pinned_observed_contract(packet)

    assert canonical_json_bytes(packet) != OBSERVED_PACKET.read_bytes()


def test_noncanonical_checked_in_serialization_is_rejected(tmp_path: Path) -> None:
    packet = observed_packet()
    noncanonical = (
        json.dumps(
            packet,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert noncanonical != OBSERVED_PACKET.read_bytes()

    packet_path = tmp_path / "noncanonical-observed.json"
    packet_path.write_bytes(noncanonical)

    result = run_validator(packet_path)
    assert result.returncode != 0
    diagnostic = strict_json_bytes(
        result.stdout.encode("utf-8"),
        label="noncanonical observed-packet diagnostic",
    )
    assert diagnostic["ok"] is False
    assert diagnostic["checks"]["canonical_packet_serialization_ok"] is False
    assert (
        "check_failed: canonical_packet_serialization_ok"
        in diagnostic["errors"]
    )


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_pulsemech_compute_subject_input_packet_6066_observed_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_pulsemech_compute_subject_input_packet_6066_observed_v0()
