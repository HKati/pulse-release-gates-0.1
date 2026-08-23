#!/usr/bin/env python3
from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools" / "build_pulsemech_device_ledger_reference_v0.py"
VERIFIER_PATH = ROOT / "tools" / "verify_pulsemech_device_ledger_v0.py"
CANONICALIZATION_PATH = ROOT / "contracts" / "pulsemech_device_canonical_json_v0.json"
OBSERVATION_CONTRACT_PATH = ROOT / "contracts" / "pulsemech_ios_observation_contract_v0.json"
SIGNATURE_SCHEMA_PATH = ROOT / "schemas" / "pulsemech_device_signature_v0.schema.json"
LEDGER_SCHEMA_PATH = ROOT / "schemas" / "pulsemech_device_transition_ledger_v0.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "pulsemech_device_ledger_manifest_v0.schema.json"
REPORT_SCHEMA_PATH = ROOT / "schemas" / "pulsemech_device_ledger_verification_report_v0.schema.json"
REFERENCE_ROOT = ROOT / "examples" / "device_transition_ledger"
REFERENCE_LEDGER_PATH = REFERENCE_ROOT / "pulsemech_device_transition_ledger_reference_v0.json"
REFERENCE_MANIFEST_PATH = REFERENCE_ROOT / "pulsemech_device_ledger_manifest_reference_v0.json"
REFERENCE_PACKAGE_PATH = REFERENCE_ROOT / "pulsemech_device_transition_ledger_reference_v0.pulseledger"

EXPECTED_OBSERVER_FINGERPRINT = (
    "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
)

EXPECTED_IDENTITIES: dict[str, tuple[int, str]] = {
    "contracts/pulsemech_device_canonical_json_v0.json": (
        2719,
        "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
    ),
    "contracts/pulsemech_ios_observation_contract_v0.json": (
        9893,
        "e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2",
    ),
    "schemas/pulsemech_device_signature_v0.schema.json": (
        5031,
        "80304b08b73f3c05092909e7917240af94121e2c15b9305440a7e01460c049c0",
    ),
    "schemas/pulsemech_device_transition_ledger_v0.schema.json": (
        54069,
        "58eddf75d9c89fef4aa3787e3e4db4d86624f4a387b2a33a3c2fd1f972d6c07f",
    ),
    "schemas/pulsemech_device_ledger_manifest_v0.schema.json": (
        19913,
        "bf8126db9a9c5c40f1dbe3ad835ae7711a98d77fa8b3a59016f4ebd406d0ce3d",
    ),
    "schemas/pulsemech_device_ledger_verification_report_v0.schema.json": (
        92135,
        "26b2ab8bed78f46c499d48b6f0b6af28ee9c23c2deafd773e4657e3d082aafd0",
    ),
    "tools/verify_pulsemech_device_ledger_v0.py": (
        123099,
        "5c5fe7d741a508d47586a144e74775bd5c8b987a9d1d5dbc64690c1e7df90bd3",
    ),
    "tools/build_pulsemech_device_ledger_reference_v0.py": (
        51405,
        "ba6cac46d0290a85a8efb4b11c3b57757aee9dbe4798610d81bf0db131934ba7",
    ),
    "examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.json": (
        31904,
        "360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77",
    ),
    "examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json": (
        5764,
        "47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1",
    ),
    "examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger": (
        133568,
        "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3",
    ),
}

STANDARD_LIBRARY_IMPORT_ROOTS = {
    "__future__",
    "argparse",
    "ast",
    "base64",
    "binascii",
    "copy",
    "dataclasses",
    "hashlib",
    "hmac",
    "io",
    "json",
    "os",
    "pathlib",
    "re",
    "secrets",
    "stat",
    "struct",
    "sys",
    "typing",
    "unicodedata",
    "zipfile",
    "zlib",
}


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _load_module(BUILDER_PATH, "pulsemech_device_reference_builder_regression")
VERIFIER = _load_module(VERIFIER_PATH, "pulsemech_device_ledger_verifier_regression")

LEDGER_SCHEMA = json.loads(LEDGER_SCHEMA_PATH.read_text(encoding="utf-8"))
MANIFEST_SCHEMA = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
SIGNATURE_SCHEMA = json.loads(SIGNATURE_SCHEMA_PATH.read_text(encoding="utf-8"))
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
REFERENCE_LEDGER = json.loads(REFERENCE_LEDGER_PATH.read_text(encoding="utf-8"))
REFERENCE_MANIFEST = json.loads(REFERENCE_MANIFEST_PATH.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return BUILDER.canonical_json_bytes(value)


def _reference_members() -> dict[str, bytes]:
    with zipfile.ZipFile(REFERENCE_PACKAGE_PATH, mode="r") as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def _zip_bytes(
    entries: Sequence[tuple[str, bytes]],
    *,
    compression: int = zipfile.ZIP_STORED,
    timestamp: tuple[int, int, int, int, int, int] = (1980, 1, 1, 0, 0, 0),
    external_attributes: Mapping[str, int] | None = None,
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=compression,
        allowZip64=False,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=timestamp)
            info.compress_type = compression
            info.create_system = 3
            info.external_attr = (
                external_attributes[name]
                if external_attributes is not None and name in external_attributes
                else (stat.S_IFREG | 0o644) << 16
            )
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            info.flag_bits = 0
            archive.writestr(info, payload)
    return output.getvalue()


def _write_subject(tmp_path: Path, payload: bytes, name: str = "subject.pulseledger") -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _verify_bytes(tmp_path: Path, payload: bytes, **kwargs: Any) -> dict[str, Any]:
    return VERIFIER.verify_package(_write_subject(tmp_path, payload), **kwargs)


def _assert_rejected(
    report: Mapping[str, Any],
    *,
    stage: str | None = None,
    check_id: str | None = None,
    error_code: str | None = None,
) -> None:
    assert report["ok"] is False
    assert report["result"] == "rejected"
    assert report["authority_boundary"]["authority_effect"] == "none"
    assert report["errors"]
    if stage is not None:
        assert report["failure_stage"] == stage, report
    if check_id is not None:
        assert check_id in report["failed_check_ids"], report
    if error_code is not None:
        assert any(row["error_code"] == error_code for row in report["errors"]), report


def _fixture_private_scalar() -> int:
    return BUILDER._fixture_private_scalar()


def _signature_document(
    *,
    role: str,
    ledger_id: str,
    observer_fingerprint: str,
    signed_object_sha256: str,
) -> dict[str, Any]:
    checkpoint = role == "ledger_checkpoint"
    return BUILDER._signature_document(
        private_scalar=_fixture_private_scalar(),
        ledger_id=ledger_id,
        observer_fingerprint=observer_fingerprint,
        signature_domain=(
            BUILDER.CHECKPOINT_SIGNATURE_DOMAIN
            if checkpoint
            else BUILDER.PACKAGE_SIGNATURE_DOMAIN
        ),
        signature_role=role,
        signed_object_sha256=signed_object_sha256,
        signed_object_type=(
            "checkpoint_record_sha256" if checkpoint else "ledger_manifest_sha256"
        ),
    )


def _assemble_package(
    *,
    ledger_bytes: bytes,
    ledger_object: Mapping[str, Any] | None = None,
    checkpoint: Mapping[str, Any] | None = None,
    public_key_bytes: bytes | None = None,
    checkpoint_signature_document: Mapping[str, Any] | None = None,
    manifest_mutator: Callable[[dict[str, Any]], None] | None = None,
    package_signature_mutator: Callable[[dict[str, Any]], None] | None = None,
) -> bytes:
    ledger = copy.deepcopy(ledger_object if ledger_object is not None else REFERENCE_LEDGER)
    checkpoint_record = copy.deepcopy(
        checkpoint if checkpoint is not None else ledger["records"][-1]
    )
    if public_key_bytes is None:
        public_key_bytes = BUILDER._public_key_bytes(_fixture_private_scalar())
    observer_fingerprint = sha256_bytes(public_key_bytes)
    if checkpoint_signature_document is None:
        checkpoint_signature_document = _signature_document(
            role="ledger_checkpoint",
            ledger_id=ledger["ledger_identity"]["ledger_id"],
            observer_fingerprint=observer_fingerprint,
            signed_object_sha256=checkpoint_record["record_sha256"],
        )
    checkpoint_signature_bytes = _canonical_bytes(checkpoint_signature_document)
    members_before_manifest: dict[str, bytes] = {
        BUILDER.CANONICALIZATION_PROFILE_PATH: CANONICALIZATION_PATH.read_bytes(),
        BUILDER.OBSERVATION_CONTRACT_PATH: OBSERVATION_CONTRACT_PATH.read_bytes(),
        BUILDER.OBSERVER_PUBLIC_KEY_PATH: public_key_bytes,
        BUILDER.LEDGER_PATH: ledger_bytes,
        BUILDER.MANIFEST_SCHEMA_PATH: MANIFEST_SCHEMA_PATH.read_bytes(),
        BUILDER.SIGNATURE_SCHEMA_PATH: SIGNATURE_SCHEMA_PATH.read_bytes(),
        BUILDER.LEDGER_SCHEMA_PATH: LEDGER_SCHEMA_PATH.read_bytes(),
        BUILDER.CHECKPOINT_SIGNATURE_PATH: checkpoint_signature_bytes,
    }
    manifest = BUILDER._build_manifest(
        members=members_before_manifest,
        ledger=ledger,
        ledger_bytes=ledger_bytes,
        checkpoint=checkpoint_record,
        observer_fingerprint=observer_fingerprint,
    )
    if manifest_mutator is not None:
        manifest_mutator(manifest)
    manifest_bytes = _canonical_bytes(manifest)
    package_signature = _signature_document(
        role="ledger_package",
        ledger_id=ledger["ledger_identity"]["ledger_id"],
        observer_fingerprint=observer_fingerprint,
        signed_object_sha256=sha256_bytes(manifest_bytes),
    )
    if package_signature_mutator is not None:
        package_signature_mutator(package_signature)
    members: dict[str, bytes] = {
        BUILDER.CANONICALIZATION_PROFILE_PATH: members_before_manifest[
            BUILDER.CANONICALIZATION_PROFILE_PATH
        ],
        BUILDER.OBSERVATION_CONTRACT_PATH: members_before_manifest[
            BUILDER.OBSERVATION_CONTRACT_PATH
        ],
        BUILDER.OBSERVER_PUBLIC_KEY_PATH: public_key_bytes,
        BUILDER.LEDGER_PATH: ledger_bytes,
        BUILDER.MANIFEST_PATH: manifest_bytes,
        BUILDER.MANIFEST_SCHEMA_PATH: members_before_manifest[
            BUILDER.MANIFEST_SCHEMA_PATH
        ],
        BUILDER.SIGNATURE_SCHEMA_PATH: members_before_manifest[
            BUILDER.SIGNATURE_SCHEMA_PATH
        ],
        BUILDER.LEDGER_SCHEMA_PATH: members_before_manifest[BUILDER.LEDGER_SCHEMA_PATH],
        BUILDER.CHECKPOINT_SIGNATURE_PATH: checkpoint_signature_bytes,
        BUILDER.PACKAGE_SIGNATURE_PATH: _canonical_bytes(package_signature),
    }
    return BUILDER._deterministic_zip(members)


def _record_reference(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record["record_id"],
        "record_sha256": record["record_sha256"],
        "sequence_index": record["sequence_index"],
    }


def _rewrite_record_references(value: Any, records_by_id: Mapping[str, Mapping[str, Any]]) -> None:
    if isinstance(value, dict):
        if {"record_id", "record_sha256", "sequence_index"}.issubset(value):
            record_id = value.get("record_id")
            if isinstance(record_id, str) and record_id in records_by_id:
                value.update(_record_reference(records_by_id[record_id]))
                return
        for child in value.values():
            _rewrite_record_references(child, records_by_id)
    elif isinstance(value, list):
        for child in value:
            _rewrite_record_references(child, records_by_id)


def _rebuild_ledger(
    ledger: Mapping[str, Any],
    *,
    sequence_overrides: Mapping[int, int] | None = None,
    previous_overrides: Mapping[int, str | None] | None = None,
) -> dict[str, Any]:
    value = copy.deepcopy(ledger)
    records = value["records"]
    assert records and records[-1]["record_type"] == "checkpoint"
    sequence_overrides = dict(sequence_overrides or {})
    previous_overrides = dict(previous_overrides or {})

    non_checkpoint = records[:-1]
    sessions = {
        item["session_id"]
        for item in non_checkpoint
        if isinstance(item.get("session_id"), str)
    }
    epochs = {
        item["clock_epoch_id"]
        for item in non_checkpoint
        if isinstance(item.get("clock_epoch_id"), str)
    }
    type_counts = {
        kind: sum(item["record_type"] == kind for item in non_checkpoint)
        for kind in (
            "coverage_interval",
            "observation_event",
            "session_boundary",
            "state_snapshot",
            "transition",
        )
    }
    coverage_summary = {
        "continuous_intervals": sum(
            item["record_type"] == "coverage_interval"
            and item["payload"].get("coverage_status") == "continuous"
            for item in non_checkpoint
        ),
        "interrupted_intervals": sum(
            item["record_type"] == "coverage_interval"
            and item["payload"].get("coverage_status") == "interrupted"
            for item in non_checkpoint
        ),
    }
    transition_summary = {
        "endpoint_difference_only": sum(
            item["record_type"] == "transition"
            and item["payload"].get("transition_class") == "endpoint_difference_only"
            for item in non_checkpoint
        ),
        "event_bound": sum(
            item["record_type"] == "transition"
            and item["payload"].get("transition_class") == "event_bound"
            for item in non_checkpoint
        ),
    }

    records_by_id: dict[str, Mapping[str, Any]] = {}
    previous: str | None = None
    for index, record in enumerate(records):
        record["sequence_index"] = sequence_overrides.get(index, index)
        record["previous_record_sha256"] = previous_overrides.get(index, previous)
        if record["record_type"] == "checkpoint":
            payload = record["payload"]
            payload["closed_record_count"] = len(non_checkpoint)
            payload["terminal_sequence_index"] = non_checkpoint[-1]["sequence_index"]
            payload["first_record"] = _record_reference(non_checkpoint[0])
            payload["terminal_record"] = _record_reference(non_checkpoint[-1])
            payload["record_type_counts"] = type_counts
            payload["session_count"] = len(sessions)
            payload["clock_epoch_count"] = len(epochs)
            payload["coverage_summary"] = coverage_summary
            payload["transition_summary"] = transition_summary
        _rewrite_record_references(record["payload"], records_by_id)
        subject = copy.deepcopy(record)
        subject.pop("record_sha256", None)
        record["record_sha256"] = sha256_bytes(_canonical_bytes(subject))
        previous = record["record_sha256"]
        records_by_id[record["record_id"]] = record

    value["ledger_summary"] = {
        "checkpoint_record_sha256": records[-1]["record_sha256"],
        "clock_epoch_count": len(epochs),
        "coverage_interval_count": type_counts["coverage_interval"],
        "observation_event_count": type_counts["observation_event"],
        "record_count": len(records),
        "session_boundary_count": type_counts["session_boundary"],
        "session_count": len(sessions),
        "snapshot_count": type_counts["state_snapshot"],
        "terminal_record_sha256": records[-1]["record_sha256"],
        "transition_count": type_counts["transition"],
    }
    return value


def _signed_ledger_mutation(mutator: Callable[[dict[str, Any]], None]) -> bytes:
    ledger = copy.deepcopy(REFERENCE_LEDGER)
    mutator(ledger)
    ledger = _rebuild_ledger(ledger)
    return _assemble_package(
        ledger_bytes=_canonical_bytes(ledger),
        ledger_object=ledger,
        checkpoint=ledger["records"][-1],
    )


def _package_with_invalid_ledger_bytes(raw: bytes) -> bytes:
    return _assemble_package(ledger_bytes=raw)


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            result.add(node.module.split(".", 1)[0])
    return result


def test_repository_artifact_identities_match_reviewed_reference() -> None:
    for relative, (expected_size, expected_sha) in EXPECTED_IDENTITIES.items():
        payload = (ROOT / relative).read_bytes()
        assert len(payload) == expected_size, relative
        assert sha256_bytes(payload) == expected_sha, relative
    assert not REFERENCE_LEDGER_PATH.read_bytes().endswith(b"\n")
    assert not REFERENCE_MANIFEST_PATH.read_bytes().endswith(b"\n")


def test_producer_and_verifier_are_separate_standard_library_implementations() -> None:
    builder_source = BUILDER_PATH.read_text(encoding="utf-8")
    verifier_source = VERIFIER_PATH.read_text(encoding="utf-8")
    assert "verify_pulsemech_device_ledger_v0" not in builder_source
    assert "build_pulsemech_device_ledger_reference_v0" not in verifier_source
    assert _import_roots(BUILDER_PATH) <= STANDARD_LIBRARY_IMPORT_ROOTS
    assert _import_roots(VERIFIER_PATH) <= STANDARD_LIBRARY_IMPORT_ROOTS
    assert BUILDER.SIGNATURE_SUITE == "ecdsa-p256-sha256"
    assert VERIFIER.SIGNATURE_SUITE == "ecdsa-p256-sha256"
    combined = (builder_source + "\n" + verifier_source).lower()
    assert "ed25519" not in combined
    assert "curve25519" not in combined


def test_all_device_schemas_and_checked_in_instances_validate() -> None:
    for schema in (SIGNATURE_SCHEMA, LEDGER_SCHEMA, MANIFEST_SCHEMA, REPORT_SCHEMA):
        jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(LEDGER_SCHEMA).validate(REFERENCE_LEDGER)
    jsonschema.Draft202012Validator(MANIFEST_SCHEMA).validate(REFERENCE_MANIFEST)
    members = _reference_members()
    for path in (BUILDER.CHECKPOINT_SIGNATURE_PATH, BUILDER.PACKAGE_SIGNATURE_PATH):
        jsonschema.Draft202012Validator(SIGNATURE_SCHEMA).validate(
            json.loads(members[path])
        )


def test_reference_package_verifies_with_all_checks_and_expected_observer() -> None:
    report = VERIFIER.verify_package(
        REFERENCE_PACKAGE_PATH,
        expected_observer_fingerprint=EXPECTED_OBSERVER_FINGERPRINT,
    )
    assert report["ok"] is True
    assert report["result"] == "verified_with_declared_unavailability"
    assert report["errors"] == []
    assert report["failed_check_ids"] == []
    assert report["failure_stage"] is None
    assert len(report["checks"]) == 49
    assert set(report["checks"].values()) == {"passed"}
    assert report["observer_verification"]["status"] == "verified"
    assert report["observer_verification"]["reconstructed_fingerprint_sha256"] == (
        EXPECTED_OBSERVER_FINGERPRINT
    )
    assert report["signature_verification"]["checkpoint"]["signature_status"] == "verified"
    assert report["signature_verification"]["package"]["signature_status"] == "verified"
    assert report["semantic_summary"]["declared_unavailability_present"] is True
    assert report["semantic_summary"]["event_bound_transition_count"] == 1
    assert report["semantic_summary"]["endpoint_difference_only_transition_count"] == 1
    jsonschema.Draft202012Validator(REPORT_SCHEMA).validate(report)


def test_verification_report_is_byte_deterministic_and_output_matches_stdout(
    tmp_path: Path,
) -> None:
    first = VERIFIER.canonical_json_bytes(VERIFIER.verify_package(REFERENCE_PACKAGE_PATH))
    second = VERIFIER.canonical_json_bytes(VERIFIER.verify_package(REFERENCE_PACKAGE_PATH))
    assert first == second
    assert not first.endswith(b"\n")
    output = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(VERIFIER_PATH),
            str(REFERENCE_PACKAGE_PATH),
            "--expected-observer-fingerprint",
            EXPECTED_OBSERVER_FINGERPRINT,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    assert completed.stderr == b""
    assert completed.stdout == output.read_bytes()
    assert completed.stdout == VERIFIER.canonical_json_bytes(json.loads(completed.stdout))
    jsonschema.Draft202012Validator(REPORT_SCHEMA).validate(json.loads(completed.stdout))


def test_reproduction_context_does_not_create_external_validation() -> None:
    report = VERIFIER.verify_package(
        REFERENCE_PACKAGE_PATH,
        reproduction_class="same_operator_clean_room",
        producer_environment_available=False,
    )
    assert report["ok"] is True
    assert report["reproduction_context"] == {
        "external_validation_claim": "none",
        "producer_environment_available_to_verifier": False,
        "reproduction_class": "same_operator_clean_room",
        "same_project_implementation": True,
        "verifier_implementation_relation": "separate_from_producer_code",
    }


def test_wrong_expected_observer_fingerprint_is_rejected() -> None:
    report = VERIFIER.verify_package(
        REFERENCE_PACKAGE_PATH,
        expected_observer_fingerprint="0" * 64,
    )
    _assert_rejected(
        report,
        stage="observer_identity",
        check_id="observer_public_key_fingerprint_valid",
        error_code="expected_observer_fingerprint_mismatch",
    )


def test_verifier_is_read_only_and_rejects_symlink_input(tmp_path: Path) -> None:
    subject = tmp_path / "copy.pulseledger"
    subject.write_bytes(REFERENCE_PACKAGE_PATH.read_bytes())
    before = (subject.stat().st_size, sha256_bytes(subject.read_bytes()))
    report = VERIFIER.verify_package(subject)
    after = (subject.stat().st_size, sha256_bytes(subject.read_bytes()))
    assert report["ok"] is True
    assert before == after
    link = tmp_path / "link.pulseledger"
    try:
        link.symlink_to(subject)
    except OSError:
        pytest.skip("symlink creation unavailable")
    _assert_rejected(
        VERIFIER.verify_package(link),
        stage="input_boundary",
        check_id="input_regular_file",
    )


def test_verifier_output_cannot_alias_carrier_or_verifier_source(tmp_path: Path) -> None:
    subject = tmp_path / "copy.pulseledger"
    subject.write_bytes(REFERENCE_PACKAGE_PATH.read_bytes())
    before_subject = subject.read_bytes()
    completed = subprocess.run(
        [sys.executable, "-I", str(VERIFIER_PATH), str(subject), "--output", str(subject)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert json.loads(completed.stderr)["ok"] is True
    assert subject.read_bytes() == before_subject

    before_source = VERIFIER_PATH.read_bytes()
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(VERIFIER_PATH),
            str(subject),
            "--output",
            str(VERIFIER_PATH),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert VERIFIER_PATH.read_bytes() == before_source


def test_reference_producer_rebuilds_all_checked_in_outputs_byte_identically(
    tmp_path: Path,
) -> None:
    outputs: list[Path] = []
    for index in range(2):
        output = tmp_path / f"generated-{index}"
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                str(BUILDER_PATH),
                "--repository-root",
                str(ROOT),
                "--output-directory",
                str(output),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
        assert completed.stderr == b""
        summary = json.loads(completed.stdout)
        assert summary["carrier_sha256"] == EXPECTED_IDENTITIES[
            "examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger"
        ][1]
        outputs.append(output)
    expected = {
        BUILDER.OUTPUT_CARRIER_NAME: REFERENCE_PACKAGE_PATH.read_bytes(),
        BUILDER.OUTPUT_LEDGER_NAME: REFERENCE_LEDGER_PATH.read_bytes(),
        BUILDER.OUTPUT_MANIFEST_NAME: REFERENCE_MANIFEST_PATH.read_bytes(),
    }
    for output in outputs:
        assert {path.name: path.read_bytes() for path in output.iterdir()} == expected
    assert {
        path.name: path.read_bytes() for path in outputs[0].iterdir()
    } == {path.name: path.read_bytes() for path in outputs[1].iterdir()}


def _copy_contract_repository(destination: Path) -> None:
    for relative in (
        BUILDER.CANONICALIZATION_PROFILE_PATH,
        BUILDER.OBSERVATION_CONTRACT_PATH,
        BUILDER.MANIFEST_SCHEMA_PATH,
        BUILDER.SIGNATURE_SCHEMA_PATH,
        BUILDER.LEDGER_SCHEMA_PATH,
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def test_reference_producer_rejects_contract_drift_and_unsafe_output_boundaries(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _copy_contract_repository(repository)
    contract = repository / BUILDER.OBSERVATION_CONTRACT_PATH
    contract.write_bytes(contract.read_bytes() + b"\n")
    output = tmp_path / "drift-output"
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(BUILDER_PATH),
            "--repository-root",
            str(repository),
            "--output-directory",
            str(output),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert b"contract_identity_mismatch" in completed.stderr
    assert not output.exists()

    repository = tmp_path / "clean-repository"
    repository.mkdir()
    _copy_contract_repository(repository)
    inside = repository / "generated"
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(BUILDER_PATH),
            "--repository-root",
            str(repository),
            "--output-directory",
            str(inside),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert b"output_directory_inside_repository" in completed.stderr
    assert not inside.exists()

    existing = tmp_path / "existing-output"
    existing.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(BUILDER_PATH),
            "--repository-root",
            str(repository),
            "--output-directory",
            str(existing),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert b"output_directory_exists" in completed.stderr


def test_single_byte_carrier_payload_mutation_is_rejected(tmp_path: Path) -> None:
    carrier = bytearray(REFERENCE_PACKAGE_PATH.read_bytes())
    marker = b'"device-ledger:iphone-synthetic-reference-v0"'
    position = carrier.index(marker)
    carrier[position + 1] ^= 1
    report = _verify_bytes(tmp_path, bytes(carrier))
    _assert_rejected(report, stage="zip_structure", check_id="zip_crc32_valid")


@pytest.mark.parametrize(
    ("case", "builder"),
    [
        (
            "extra",
            lambda members: _zip_bytes(
                [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER]
                + [("extra.json", b"{}")]
            ),
        ),
        (
            "missing",
            lambda members: _zip_bytes(
                [
                    (name, members[name])
                    for name in BUILDER.PACKAGE_MEMBER_ORDER
                    if name != BUILDER.PACKAGE_SIGNATURE_PATH
                ]
            ),
        ),
        (
            "traversal",
            lambda members: _zip_bytes(
                [
                    (
                        "../ledger.json" if name == BUILDER.LEDGER_PATH else name,
                        members[name],
                    )
                    for name in BUILDER.PACKAGE_MEMBER_ORDER
                ]
            ),
        ),
        (
            "deflate",
            lambda members: _zip_bytes(
                [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER],
                compression=zipfile.ZIP_DEFLATED,
            ),
        ),
        (
            "timestamp",
            lambda members: _zip_bytes(
                [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER],
                timestamp=(2020, 1, 1, 0, 0, 0),
            ),
        ),
        (
            "trailing-data",
            lambda members: REFERENCE_PACKAGE_PATH.read_bytes() + b"trailing",
        ),
    ],
)
def test_zip_structure_falsification_is_rejected(
    tmp_path: Path,
    case: str,
    builder: Callable[[dict[str, bytes]], bytes],
) -> None:
    del case
    report = _verify_bytes(tmp_path, builder(_reference_members()))
    _assert_rejected(report, stage="zip_structure")


def test_duplicate_zip_member_is_rejected(tmp_path: Path) -> None:
    members = _reference_members()
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_STORED) as archive:
            for name in BUILDER.PACKAGE_MEMBER_ORDER:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, members[name])
            name = BUILDER.LEDGER_PATH
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, members[name])
    _assert_rejected(
        _verify_bytes(tmp_path, output.getvalue()),
        stage="zip_structure",
        check_id="zip_exact_member_set_valid",
    )


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_non_regular_zip_member_is_rejected(tmp_path: Path, kind: str) -> None:
    members = _reference_members()
    external = {
        BUILDER.LEDGER_PATH: (
            ((stat.S_IFDIR | 0o755) << 16)
            if kind == "directory"
            else ((stat.S_IFLNK | 0o777) << 16)
        )
    }
    package = _zip_bytes(
        [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER],
        external_attributes=external,
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="zip_structure",
        check_id="zip_member_types_valid",
    )


def test_member_resource_limit_is_rejected(tmp_path: Path) -> None:
    members = _reference_members()
    members[BUILDER.LEDGER_PATH] = b"0" * (VERIFIER.MAX_MEMBER_BYTES + 1)
    package = _zip_bytes(
        [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER]
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="zip_structure",
        check_id="zip_member_types_valid",
    )


@pytest.mark.parametrize(
    ("name", "mutator"),
    [
        (
            "record-deletion",
            lambda ledger: ledger["records"].pop(3),
        ),
        (
            "event-insertion",
            lambda ledger: ledger["records"].insert(
                4,
                {
                    **copy.deepcopy(ledger["records"][3]),
                    "record_id": "record:003b-path-cellular-a-duplicate",
                    "payload": {
                        **copy.deepcopy(ledger["records"][3]["payload"]),
                        "event_id": "event:path-cellular-a-duplicate",
                    },
                },
            ),
        ),
        (
            "record-reordering",
            lambda ledger: ledger["records"].__setitem__(
                slice(1, 3),
                [ledger["records"][2], ledger["records"][1]],
            ),
        ),
        (
            "source-endpoint-substitution",
            lambda ledger: ledger["records"][6]["payload"].__setitem__(
                "source_snapshot",
                copy.deepcopy(ledger["records"][4]["payload"]["source_event_binding"]),
            ),
        ),
        (
            "target-endpoint-substitution",
            lambda ledger: ledger["records"][12]["payload"].__setitem__(
                "target_snapshot",
                _record_reference(ledger["records"][4]),
            ),
        ),
        (
            "coverage-widening",
            lambda ledger: ledger["records"][11]["payload"].__setitem__(
                "coverage_status", "continuous"
            ),
        ),
        (
            "source-overclaim",
            lambda ledger: ledger["records"][12]["payload"].update(
                {
                    "initiating_source_status": "identified",
                    "initiating_source_identity": "source:synthetic",
                }
            ),
        ),
        (
            "causal-overclaim",
            lambda ledger: ledger["records"][12]["payload"]["axes"].update(
                {
                    "causal_sufficiency_status": "established",
                    "causal_necessity_status": "established",
                }
            ),
        ),
    ],
)
def test_semantic_relation_falsification_with_rebuilt_integrity_is_rejected(
    tmp_path: Path,
    name: str,
    mutator: Callable[[dict[str, Any]], None],
) -> None:
    del name
    report = _verify_bytes(tmp_path, _signed_ledger_mutation(mutator))
    _assert_rejected(report)
    assert report["failure_stage"] in {"ledger_admission", "record_chain", "semantic_relations"}



def test_checkpoint_terminal_substitution_with_rebuilt_signature_is_rejected(
    tmp_path: Path,
) -> None:
    ledger = _rebuild_ledger(REFERENCE_LEDGER)
    checkpoint = ledger["records"][-1]
    checkpoint["payload"]["terminal_record"] = _record_reference(ledger["records"][6])
    subject = copy.deepcopy(checkpoint)
    subject.pop("record_sha256", None)
    checkpoint["record_sha256"] = sha256_bytes(_canonical_bytes(subject))
    ledger["ledger_summary"]["checkpoint_record_sha256"] = checkpoint["record_sha256"]
    ledger["ledger_summary"]["terminal_record_sha256"] = checkpoint["record_sha256"]
    package = _assemble_package(
        ledger_bytes=_canonical_bytes(ledger),
        ledger_object=ledger,
        checkpoint=checkpoint,
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="semantic_relations",
        check_id="checkpoint_closure_valid",
    )

def test_duplicate_sequence_with_rebuilt_integrity_is_rejected(tmp_path: Path) -> None:
    ledger = _rebuild_ledger(REFERENCE_LEDGER, sequence_overrides={3: 2})
    package = _assemble_package(
        ledger_bytes=_canonical_bytes(ledger),
        ledger_object=ledger,
        checkpoint=ledger["records"][-1],
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="record_chain",
        check_id="record_sequence_valid",
    )


def test_incorrect_previous_record_digest_with_self_consistent_record_hash_is_rejected(
    tmp_path: Path,
) -> None:
    ledger = _rebuild_ledger(REFERENCE_LEDGER, previous_overrides={4: "0" * 64})
    package = _assemble_package(
        ledger_bytes=_canonical_bytes(ledger),
        ledger_object=ledger,
        checkpoint=ledger["records"][-1],
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="record_chain",
        check_id="record_chain_valid",
    )


@pytest.mark.parametrize(
    ("name", "raw_builder", "expected_check"),
    [
        (
            "noncanonical-whitespace",
            lambda raw: raw.replace(b'"authority_boundary":', b'"authority_boundary": ', 1),
            "ledger_canonical_json_valid",
        ),
        (
            "duplicate-key",
            lambda raw: raw[:-1]
            + b',"schema_version":"pulsemech_device_transition_ledger_v0"}',
            "ledger_strict_json_valid",
        ),
        (
            "floating-point",
            lambda raw: raw.replace(b'"record_count":14', b'"record_count":14.0', 1),
            "ledger_strict_json_valid",
        ),
        (
            "negative-zero",
            lambda raw: raw.replace(b'"sequence_index":0', b'"sequence_index":-0', 1),
            "ledger_strict_json_valid",
        ),
        (
            "utf8-bom",
            lambda raw: b"\xef\xbb\xbf" + raw,
            "ledger_strict_json_valid",
        ),
        (
            "malformed-utf8",
            lambda raw: raw[:20] + b"\xff" + raw[21:],
            "ledger_strict_json_valid",
        ),
        (
            "non-ascii-v0",
            lambda raw: raw.replace(
                b'"record_status":"synthetic_reference"',
                '"record_status":"synthetic_réference"'.encode("utf-8"),
                1,
            ),
            "ledger_strict_json_valid",
        ),
        (
            "alternate-forward-slash-escape",
            lambda raw: raw.replace(b'"/network_path/is_expensive"', b'"\\/network_path\\/is_expensive"', 1),
            "ledger_canonical_json_valid",
        ),
    ],
)
def test_strict_and_canonical_json_falsification_is_rejected(
    tmp_path: Path,
    name: str,
    raw_builder: Callable[[bytes], bytes],
    expected_check: str,
) -> None:
    del name
    raw = raw_builder(REFERENCE_LEDGER_PATH.read_bytes())
    report = _verify_bytes(tmp_path, _package_with_invalid_ledger_bytes(raw))
    _assert_rejected(report, stage="ledger_admission", check_id=expected_check)


def test_manifest_noncanonical_bytes_are_rejected(tmp_path: Path) -> None:
    members = _reference_members()
    manifest = members[BUILDER.MANIFEST_PATH].replace(
        b'"authority_boundary":', b'"authority_boundary": ', 1
    )
    members[BUILDER.MANIFEST_PATH] = manifest
    package = _zip_bytes(
        [(name, members[name]) for name in BUILDER.PACKAGE_MEMBER_ORDER]
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="manifest_admission",
        check_id="manifest_canonical_json_valid",
    )


def test_manifest_payload_digest_substitution_with_valid_package_signature_is_rejected(
    tmp_path: Path,
) -> None:
    def mutate(manifest: dict[str, Any]) -> None:
        row = next(
            item
            for item in manifest["payload_members"]
            if item["role"] == "transition_ledger"
        )
        row["sha256"] = "0" * 64

    package = _assemble_package(
        ledger_bytes=REFERENCE_LEDGER_PATH.read_bytes(),
        manifest_mutator=mutate,
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="manifest_admission",
        check_id="manifest_payload_inventory_valid",
    )


@pytest.mark.parametrize("kind", ["wrong_prefix", "off_curve"])
def test_malformed_observer_public_key_is_rejected(tmp_path: Path, kind: str) -> None:
    public_key = (b"\x05" + b"\x00" * 64) if kind == "wrong_prefix" else (b"\x04" + b"\x00" * 64)
    package = _assemble_package(
        ledger_bytes=REFERENCE_LEDGER_PATH.read_bytes(),
        public_key_bytes=public_key,
    )
    report = _verify_bytes(tmp_path, package)
    _assert_rejected(report, stage="observer_identity")
    assert any(
        check in report["failed_check_ids"]
        for check in (
            "observer_public_key_encoding_valid",
            "observer_public_key_curve_membership_valid",
        )
    )


def _mutated_checkpoint_signature(mutator: Callable[[bytearray], None]) -> dict[str, Any]:
    checkpoint = REFERENCE_LEDGER["records"][-1]
    document = _signature_document(
        role="ledger_checkpoint",
        ledger_id=REFERENCE_LEDGER["ledger_identity"]["ledger_id"],
        observer_fingerprint=EXPECTED_OBSERVER_FINGERPRINT,
        signed_object_sha256=checkpoint["record_sha256"],
    )
    raw = bytearray(base64.b64decode(document["signature_base64"], validate=True))
    mutator(raw)
    document["signature_base64"] = base64.b64encode(raw).decode("ascii")
    return document


@pytest.mark.parametrize(
    ("name", "mutator"),
    [
        ("zero-r", lambda raw: raw.__setitem__(slice(0, 32), b"\x00" * 32)),
        (
            "high-s",
            lambda raw: raw.__setitem__(
                slice(32, 64),
                (VERIFIER.P256_N - int.from_bytes(raw[32:], "big")).to_bytes(32, "big"),
            ),
        ),
        ("signature-bit", lambda raw: raw.__setitem__(63, raw[63] ^ 1)),
    ],
)
def test_checkpoint_signature_falsification_is_rejected(
    tmp_path: Path,
    name: str,
    mutator: Callable[[bytearray], None],
) -> None:
    del name
    package = _assemble_package(
        ledger_bytes=REFERENCE_LEDGER_PATH.read_bytes(),
        checkpoint_signature_document=_mutated_checkpoint_signature(mutator),
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="checkpoint_signature",
        check_id="checkpoint_signature_valid",
    )


def test_package_signature_mutation_is_rejected(tmp_path: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        raw = bytearray(base64.b64decode(document["signature_base64"], validate=True))
        raw[-1] ^= 1
        document["signature_base64"] = base64.b64encode(raw).decode("ascii")

    package = _assemble_package(
        ledger_bytes=REFERENCE_LEDGER_PATH.read_bytes(),
        package_signature_mutator=mutate,
    )
    _assert_rejected(
        _verify_bytes(tmp_path, package),
        stage="package_signature",
        check_id="package_signature_valid",
    )


def test_claim_and_authority_overreach_are_rejected(tmp_path: Path) -> None:
    def claim_mutation(ledger: dict[str, Any]) -> None:
        ledger["claim_boundary"]["device_security_claim"] = "device_secure"

    claim_report = _verify_bytes(tmp_path, _signed_ledger_mutation(claim_mutation))
    _assert_rejected(claim_report)

    def authority_mutation(ledger: dict[str, Any]) -> None:
        ledger["authority_boundary"]["authority_effect"] = "release"

    authority_report = _verify_bytes(
        tmp_path,
        _signed_ledger_mutation(authority_mutation),
    )
    _assert_rejected(authority_report)


def test_rejected_cli_returns_two_and_schema_valid_machine_report(tmp_path: Path) -> None:
    subject = tmp_path / "bad.pulseledger"
    subject.write_bytes(REFERENCE_PACKAGE_PATH.read_bytes() + b"trailing")
    completed = subprocess.run(
        [sys.executable, "-I", str(VERIFIER_PATH), str(subject)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 2
    assert completed.stderr == b""
    report = json.loads(completed.stdout)
    _assert_rejected(report, stage="zip_structure")
    jsonschema.Draft202012Validator(REPORT_SCHEMA).validate(report)
    assert completed.stdout == VERIFIER.canonical_json_bytes(report)


def _run_authoritative_regression() -> int:
    environment = dict(os.environ)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTEST_PLUGINS", None)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "--noconftest",
            str(Path(__file__).resolve()),
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        timeout=240,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
