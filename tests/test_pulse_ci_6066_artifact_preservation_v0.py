#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
ARCHIVE = (
    PRESERVATION_DIR
    / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
)
MANIFEST = PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
README = PRESERVATION_DIR / "README.md"
SHA256SUMS = PRESERVATION_DIR / "SHA256SUMS"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_pulse_ci_6066_artifact_preservation_v0.py"
ARCHIVE_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
OUTER_PREFIX = "pulse-ci-6066-preservation-v0/"
ORIGINAL_PREFIX = OUTER_PREFIX + "original-github-artifacts/"
EXPECTED_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_SOURCE_SHA = "46b639706e23f80fe296a8893be18e2b5ab21f7e"

EXPECTED_ARTIFACTS = {
    "complete-release-grade-reference-package-29249887581-1.zip": {
        "artifact_id": 8278987946,
        "role": "complete_release_grade_reference_package",
        "sha256": (
            "0549ea28c30dfdf6bc44a36a50fef3c21500a7ed1d9d58f448eaa1593ce3d264"
        ),
        "size_bytes": 44880,
    },
    "release-grade-package-completeness-29249887581-1.zip": {
        "artifact_id": 8278994595,
        "role": "structural_package_completeness_report",
        "sha256": (
            "827ee63e902ba1770639302ef52b46d2064e7f097903b1f8520afb26a306749d"
        ),
        "size_bytes": 2044,
    },
    "release-grade-reference-package-verification-29249887581-1.zip": {
        "artifact_id": 8278995165,
        "role": "independent_package_verification_report",
        "sha256": (
            "c5dcc93eb17fe166a575e7a83ab1f364f44504e3c53105213202752592094c85"
        ),
        "size_bytes": 2418,
    },
}

OUTER_MEMBERS = {
    OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json",
    OUTER_PREFIX + "README.md",
    OUTER_PREFIX + "SHA256SUMS",
    *{ORIGINAL_PREFIX + name for name in EXPECTED_ARTIFACTS},
}


class StrictJsonError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def load_strict_json(data: bytes) -> dict[str, Any]:
    loaded = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(loaded, dict)
    return loaded


def safe_zip_members(zf: zipfile.ZipFile) -> set[str]:
    infos = zf.infolist()
    names = [info.filename for info in infos]

    assert len(names) == len(set(names)), "duplicate ZIP member"
    assert zf.testzip() is None

    for info in infos:
        path = PurePosixPath(info.filename)
        mode = info.external_attr >> 16

        assert info.filename
        assert "\\" not in info.filename
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert not info.is_dir()
        assert not stat.S_ISLNK(mode)
        assert (info.flag_bits & 0x1) == 0

    return set(names)


def parse_sha256sums(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        digest, separator, relative = line.partition("  ")
        assert separator == "  "
        assert len(digest) == 64
        int(digest, 16)
        assert relative not in entries
        entries[relative] = digest
    return entries


def read_single_member_zip(data: bytes, expected_name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        assert safe_zip_members(zf) == {expected_name}
        return zf.read(expected_name)


def load_manifest() -> dict[str, Any]:
    return load_strict_json(MANIFEST.read_bytes())


def test_archive_digest_members_and_visible_carriers_are_locked() -> None:
    for path in (ARCHIVE, MANIFEST, README, SHA256SUMS):
        assert path.is_file(), path
        assert not path.is_symlink(), path

    assert ARCHIVE.stat().st_size == 44660
    assert sha256_file(ARCHIVE) == ARCHIVE_SHA256

    with zipfile.ZipFile(ARCHIVE, "r") as zf:
        assert safe_zip_members(zf) == OUTER_MEMBERS
        assert (
            zf.read(OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json")
            == MANIFEST.read_bytes()
        )
        assert zf.read(OUTER_PREFIX + "README.md") == README.read_bytes()
        assert (
            zf.read(OUTER_PREFIX + "SHA256SUMS")
            == SHA256SUMS.read_bytes()
        )


def test_manifest_locks_run_results_retention_and_non_authority() -> None:
    manifest = load_manifest()

    assert manifest["schema_id"] == (
        "pulse_ci_release_grade_artifact_preservation_manifest_v0"
    )
    assert manifest["schema_version"] == "0.1.0"
    assert manifest["repository"] == "HKati/pulse-release-gates-0.1"
    assert manifest["workflow"] == "PULSE CI"
    assert manifest["workflow_run_number"] == 6066
    assert manifest["workflow_run_id"] == 29249887581
    assert manifest["workflow_run_attempt"] == 1
    assert manifest["source_ref"] == "refs/heads/main"
    assert manifest["source_commit"] == EXPECTED_SOURCE_SHA
    assert manifest["run_mode"] == "prod"
    assert manifest["strict_external_evidence"] is True
    assert manifest["llamaguard_evidence_mode"] == "hosted_full_runtime"
    assert manifest["active_policy_sets"] == ["required", "release_required"]
    assert manifest["primary_gate_result"] == "allow"
    assert manifest["release_decision"] == "PROD-PASS"

    assert manifest["authority_boundary"] == {
        "alters_preserved_artifacts": False,
        "creates_release_authority": False,
        "preservation_copy_only": True,
        "replaces_original_github_attestations": False,
        "replaces_primary_ci_decision": False,
    }
    assert manifest["retention_risk"] == {
        "earliest_expiry_utc": "2026-08-12T12:30:10Z",
        "original_github_artifacts_expire": True,
        "reason_for_preservation": (
            "Preserve the completed fixed-source hosted release-grade baseline "
            "before GitHub Actions artifact expiry."
        ),
    }

    verification = manifest["local_verification"]
    assert verification["all_outer_artifact_digests_match_github"] is True
    assert verification["all_outer_artifact_sizes_match_github"] is True
    assert verification["complete_package_zip_members"] == 24
    assert verification["complete_package_inventory_entries"] == 23
    assert verification["complete_package_inventory_errors"] == []
    assert verification[
        "complete_package_unlisted_members_excluding_inventory"
    ] == []
    assert verification["structural_completeness_status"] == "complete"
    assert verification["structural_completeness_ok"] is True
    assert verification["structural_completeness_checks_total"] == 135
    assert verification["structural_completeness_checks_failed"] == 0
    assert verification["independent_verification_status"] == "verified"
    assert verification["independent_verification_verified"] is True
    assert verification["independent_verification_checks_total"] == 157
    assert verification["independent_verification_errors"] == []


def test_original_artifact_bytes_match_manifest_and_sha256sums() -> None:
    manifest = load_manifest()
    records = {
        record["file_name"]: record
        for record in manifest["github_artifacts"]
    }
    assert set(records) == set(EXPECTED_ARTIFACTS)

    sums = parse_sha256sums(SHA256SUMS.read_text(encoding="utf-8"))
    assert sums == {
        "PRESERVATION_MANIFEST_v0.json": sha256_file(MANIFEST),
        "README.md": sha256_file(README),
        **{
            "original-github-artifacts/" + name: expected["sha256"]
            for name, expected in EXPECTED_ARTIFACTS.items()
        },
    }

    with zipfile.ZipFile(ARCHIVE, "r") as zf:
        for name, expected in EXPECTED_ARTIFACTS.items():
            record = records[name]
            payload = zf.read(ORIGINAL_PREFIX + name)

            assert record["artifact_id"] == expected["artifact_id"]
            assert record["role"] == expected["role"]
            assert record["size_bytes"] == expected["size_bytes"]
            assert record["downloaded_size_bytes"] == expected["size_bytes"]
            assert record["github_sha256"] == expected["sha256"]
            assert record["downloaded_sha256"] == expected["sha256"]
            assert record["github_digest_match"] is True
            assert record["github_size_match"] is True
            assert len(payload) == expected["size_bytes"]
            assert sha256_bytes(payload) == expected["sha256"]


def test_complete_package_inventory_replays_from_preserved_bytes() -> None:
    package_name = (
        "complete-release-grade-reference-package-29249887581-1.zip"
    )

    with zipfile.ZipFile(ARCHIVE, "r") as outer:
        package_bytes = outer.read(ORIGINAL_PREFIX + package_name)

    with zipfile.ZipFile(io.BytesIO(package_bytes), "r") as package:
        package_members = safe_zip_members(package)
        inventory = load_strict_json(
            package.read("package_digest_inventory_v0.json")
        )

        assert inventory["schema_version"] == (
            "release_grade_reference_package_digest_inventory_v0"
        )
        assert inventory["algorithm"] == "sha256"
        assert inventory["file_count"] == 23
        assert inventory["authority_boundary"]["package_only"] is True
        assert inventory["authority_boundary"]["authorizes_release"] is False

        rows = inventory["files"]
        assert isinstance(rows, list)
        assert len(rows) == 23

        declared_paths: set[str] = set()
        for row in rows:
            assert isinstance(row, dict)
            relative = row["path"]
            assert relative not in declared_paths
            declared_paths.add(relative)

            payload = package.read(relative)
            assert len(payload) == row["size_bytes"]
            assert sha256_bytes(payload) == row["sha256"]

        assert package_members == declared_paths | {
            "package_digest_inventory_v0.json"
        }


def test_package_identity_decision_and_verifier_bindings_are_preserved() -> None:
    package_name = (
        "complete-release-grade-reference-package-29249887581-1.zip"
    )

    with zipfile.ZipFile(ARCHIVE, "r") as outer:
        package_bytes = outer.read(ORIGINAL_PREFIX + package_name)

    with zipfile.ZipFile(io.BytesIO(package_bytes), "r") as package:
        run_metadata = load_strict_json(package.read("run_metadata_v0.json"))
        status = load_strict_json(package.read("artifacts/status.json"))
        decision = load_strict_json(
            package.read("artifacts/release_decision_v0.json")
        )
        authority = load_strict_json(
            package.read("artifacts/release_authority_v0.json")
        )
        verifier = load_strict_json(
            package.read("artifacts/recorded_release_evidence_verifier_v0.json")
        )

    assert run_metadata["repository"] == "HKati/pulse-release-gates-0.1"
    assert run_metadata["run_id"] == 29249887581
    assert run_metadata["run_attempt"] == 1
    assert run_metadata["run_key"] == EXPECTED_RUN_KEY
    assert run_metadata["git_sha"] == EXPECTED_SOURCE_SHA
    assert run_metadata["authority_boundary"]["package_only"] is True
    assert run_metadata["authority_boundary"]["authorizes_release"] is False

    assert status["metrics"]["run_mode"] == "prod"
    assert status["metrics"]["run_key"] == EXPECTED_RUN_KEY
    assert status["metrics"]["git_sha"] == EXPECTED_SOURCE_SHA
    assert status["diagnostics"]["gates_stubbed"] is False
    assert status["diagnostics"]["scaffold"] is False
    assert len(status["gates"]) == 23
    assert all(value is True for value in status["gates"].values())

    assert decision["schema"] == "pulse_release_decision_v0"
    assert decision["git_sha"] == EXPECTED_SOURCE_SHA
    assert decision["run_mode"] == "prod"
    assert decision["active_gate_sets"] == ["required", "release_required"]
    assert decision["required_gates_passed"] is True
    assert decision["release_level"] == "PROD-PASS"
    assert decision["blocking_reasons"] == []
    assert len(decision["effective_required_gates"]) == 23

    assert authority["schema_version"] == "release_authority_v0"
    assert authority["run_identity"]["git_sha"] == EXPECTED_SOURCE_SHA
    assert authority["run_identity"]["run_mode"] == "prod"
    assert authority["decision"] == {"state": "PASS", "fail_closed": True}
    assert authority["authority"]["release_required_materialized"] is True
    assert len(authority["authority"]["effective_required_gates"]) == 23

    assert verifier["schema_version"] == "recorded_release_evidence_verifier_v0"
    assert verifier["status"] == "verified"
    assert verifier["errors"] == []
    assert verifier["run_identity"]["git_sha"] == EXPECTED_SOURCE_SHA
    assert verifier["run_identity"]["run_key"] == EXPECTED_RUN_KEY
    assert verifier["run_identity"]["run_mode"] == "prod"


def test_preserved_completeness_and_verification_reports_pass() -> None:
    completeness_name = (
        "release-grade-package-completeness-29249887581-1.zip"
    )
    verification_name = (
        "release-grade-reference-package-verification-29249887581-1.zip"
    )

    with zipfile.ZipFile(ARCHIVE, "r") as outer:
        completeness_bytes = outer.read(ORIGINAL_PREFIX + completeness_name)
        verification_bytes = outer.read(ORIGINAL_PREFIX + verification_name)

    completeness = load_strict_json(
        read_single_member_zip(
            completeness_bytes,
            "release_grade_package_completeness_v1.json",
        )
    )
    verification = load_strict_json(
        read_single_member_zip(
            verification_bytes,
            "release_grade_reference_package_verification_v0.json",
        )
    )

    assert completeness["schema_version"] == (
        "release_grade_package_completeness_v1"
    )
    assert completeness["status"] == "complete"
    assert completeness["ok"] is True
    assert completeness["errors"] == []
    assert completeness["summary"] == {
        "checks_total": 135,
        "checks_failed": 0,
        "required_files": 18,
        "required_dirs": 2,
    }
    assert len(completeness["checks"]) == 135
    assert all(check["passed"] is True for check in completeness["checks"])
    assert completeness["authority_boundary"]["read_only"] is True
    assert completeness["authority_boundary"]["authorizes_release"] is False

    assert verification["schema_version"] == (
        "release_grade_reference_package_verification_v0"
    )
    assert verification["status"] == "verified"
    assert verification["verified"] is True
    assert verification["errors"] == []
    assert len(verification["checks"]) == 157
    assert all(check["passed"] is True for check in verification["checks"])
    assert verification["authority_boundary"]["read_only"] is True
    assert verification["authority_boundary"]["authorizes_release"] is False


def test_readme_and_tools_manifest_keep_the_preservation_boundary_visible() -> None:
    text = README.read_text(encoding="utf-8")
    required_fragments = (
        "PULSE CI #6066 release-grade artifact preservation v0",
        "This is a preservation copy only.",
        "does not create release authority",
        "does not replace the primary CI decision",
        "does not replace the original GitHub attestations",
        "scheduled to expire on 2026-08-12",
    )
    for fragment in required_fragments:
        assert fragment in text

    entries = [
        line.split("#", 1)[0].strip()
        for line in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
    ]
    entries = [entry for entry in entries if entry]
    assert entries.count(THIS_TEST) == 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
