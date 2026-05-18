from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_pulse_ref_ra1_package.py"
PACKAGE = ROOT / "tests" / "fixtures" / "pulse_ref_ra1_package_minimal"
REPORT_SCHEMA = ROOT / "schemas" / "pulse_ref_package_verifier_report_v0.schema.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def _run(package_root: Path, out_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--package-root",
            str(package_root),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _validate_report(report: dict[str, Any]) -> None:
    schema = _read_json(REPORT_SCHEMA)
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(report),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        details = "\n".join(
            f"{list(error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise AssertionError(f"verifier report schema validation failed:\n{details}")


def test_valid_ra1_minimal_package_verifies() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        out_path = Path(tmp) / "verifier_report.json"

        result = _run(PACKAGE, out_path)

        assert result.returncode == 0, (
            f"unexpected verifier failure\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["schema"] == "pulse_ref_package_verifier_report_v0"
        assert report["ok"] is True
        assert report["errors"] == []
        assert report["package_id"] == "pulse-ref-ra1-minimal"
        assert report["run_key"] == "pulse-ref-ra1-minimal-fixture"
        assert report["git_sha"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        assert report["authority_boundary"]["verifier_role"] == "external_reconstruction_check"
        assert report["authority_boundary"]["creates_release_authority"] is False

        assert all(check["ok"] is True for check in report["schemas_validated"])
        assert all(check["ok"] is True for check in report["artifact_digests_checked"])
        assert all(check["ok"] is True for check in report["cross_artifact_checks"])

        digest_sources = {
            check.get("source")
            for check in report["artifact_digests_checked"]
        }

        assert "package_manifest" in digest_sources
        assert "package_digests" in digest_sources

        schema_paths = {
            check["artifact_path"]
            for check in report["schemas_validated"]
        }

        assert "package_manifest.json" in schema_paths
        assert "digests/package_digests.json" in schema_paths
        assert "gates/materialized_gate_sets.json" in schema_paths
        assert "handoff/operator_handoff_report.json" in schema_paths
        assert "release_authority/release_authority_manifest.json" in schema_paths
        assert "ci/ci_outcome.json" in schema_paths
        assert "publication/publication_snapshot.json" in schema_paths

        cross_check_names = {
            check["name"]
            for check in report["cross_artifact_checks"]
        }

        assert "materialized_gate_sets_match_policy" in cross_check_names
        assert "status_satisfies_effective_required_gates" in cross_check_names
        assert "handoff_matches_status_and_gate_sets" in cross_check_names
        assert "release_authority_manifest_matches_package_core" in cross_check_names
        assert "ci_outcome_and_publication_match_release_identity" in cross_check_names
        assert "package_digests_cover_manifest_payload" in cross_check_names
        assert "package_inventory_matches_manifest" in cross_check_names
        assert "package_manifest_uses_canonical_layout" in cross_check_names
        assert "package_payload_files_are_regular_files" in cross_check_names
        assert "package_manifest_uses_canonical_layout" in cross_check_names
        assert "package_identity_matches_release_surfaces" in cross_check_names
        assert "package_manifest_authority_boundary" in cross_check_names
        assert "package_digests_authority_boundary" in cross_check_names
        assert "package_id_consistency" in cross_check_names
     
        cross_check_order = [
            check["name"]
            for check in report["cross_artifact_checks"]
        ]
        assert cross_check_order.index(
            "release_authority_manifest_matches_package_core"
        ) < cross_check_order.index(
            "ci_outcome_and_publication_match_release_identity"
        )


def test_digest_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.fail.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["sha256"] = "0" * 64
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert report["errors"] != []

        failing_checks = [
            check
            for check in report["artifact_digests_checked"]
            if (
                check["artifact_path"] == "status/status.json"
                and check.get("source") == "package_manifest"
            )
        ]

        assert len(failing_checks) == 1
        assert failing_checks[0]["ok"] is False
        assert failing_checks[0]["actual_sha256"] is not None


def test_package_manifest_git_sha_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.git_sha_mismatch.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["git_sha"] = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        identity_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_identity_matches_release_surfaces"
        ]

        assert len(identity_checks) == 1
        assert identity_checks[0]["ok"] is False


def test_symlinked_artifact_outside_package_root_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.symlink_fail.json"
        outside_status = tmp_path / "outside_status.json"

        shutil.copytree(PACKAGE, package_copy)

        outside_status.write_text(
            json.dumps(
                {
                    "outside": True,
                    "note": "This file is outside the package root.",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        outside_sha = _sha256_file(outside_status)

        status_path = package_copy / "status" / "status.json"
        status_path.unlink()

        try:
            status_path.symlink_to(outside_status)
        except (OSError, NotImplementedError):
            return

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["status/status.json"] = outside_sha
        _write_json(digests_path, digests)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["sha256"] = outside_sha
        manifest["package_digests"]["sha256"] = _sha256_file(digests_path)
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "resolves outside package root" in error
            for error in report["errors"]
        )

def test_malformed_digest_string_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.malformed_digest.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["sha256"] = "not-a-sha"
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "expected_sha256 is not a lowercase SHA-256 digest" in error
            for error in report["errors"]
        )

        status_checks = [
            check
            for check in report["artifact_digests_checked"]
            if (
                check["artifact_path"] == "status/status.json"
                and check.get("source") == "package_manifest"
            )
        ]

        assert len(status_checks) == 1
        assert status_checks[0]["ok"] is False
        assert status_checks[0]["expected_sha256"] == "0" * 64

def test_schema_invalid_package_artifact_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.schema_fail.json"

        shutil.copytree(PACKAGE, package_copy)

        publication_path = package_copy / "publication" / "publication_snapshot.json"
        publication = _read_json(publication_path)
        publication["creates_release_authority"] = True
        _write_json(publication_path, publication)

        publication_sha = _sha256_file(publication_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["publication/publication_snapshot.json"] = publication_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["publication_snapshot"]["sha256"] = publication_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        publication_schema_checks = [
            check
            for check in report["schemas_validated"]
            if check["artifact_path"] == "publication/publication_snapshot.json"
        ]

        assert len(publication_schema_checks) == 1
        assert publication_schema_checks[0]["ok"] is False
        assert any(
            "publication/publication_snapshot.json schema validation failed" in error
            for error in report["errors"]
        )

def test_false_effective_required_gate_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.false_gate.json"

        shutil.copytree(PACKAGE, package_copy)

        status_path = package_copy / "status" / "status.json"
        status = _read_json(status_path)
        status["gates"]["q4_slo_ok"] = False
        _write_json(status_path, status)

        status_sha = _sha256_file(status_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["status/status.json"] = status_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["sha256"] = status_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        status_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "status_satisfies_effective_required_gates"
        ]

        assert len(status_checks) == 1
        assert status_checks[0]["ok"] is False
        assert "q4_slo_ok" in status_checks[0]["message"]
        assert any(
            "false effective required gates" in error
            for error in report["errors"]
        )


def test_materialized_gate_set_policy_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.gate_set_mismatch.json"

        shutil.copytree(PACKAGE, package_copy)

        gate_sets_path = package_copy / "gates" / "materialized_gate_sets.json"
        gate_sets = _read_json(gate_sets_path)
        gate_sets["sets"]["required"] = [
            gate_id
            for gate_id in gate_sets["sets"]["required"]
            if gate_id != "q4_slo_ok"
        ]
        _write_json(gate_sets_path, gate_sets)

        gate_sets_sha = _sha256_file(gate_sets_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["gates/materialized_gate_sets.json"] = gate_sets_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["materialized_gate_sets"]["sha256"] = gate_sets_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        gate_set_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "materialized_gate_sets_match_policy"
        ]

        assert len(gate_set_checks) == 1
        assert gate_set_checks[0]["ok"] is False
        assert "sets.required does not match" in gate_set_checks[0]["message"]

def test_handoff_status_digest_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.handoff_status_digest.json"

        shutil.copytree(PACKAGE, package_copy)

        handoff_path = package_copy / "handoff" / "operator_handoff_report.json"
        handoff = _read_json(handoff_path)
        handoff["status_source"]["status_sha256_before_run"] = "0" * 64
        _write_json(handoff_path, handoff)

        handoff_sha = _sha256_file(handoff_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["handoff/operator_handoff_report.json"] = handoff_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["operator_handoff_report"]["sha256"] = handoff_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        handoff_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "handoff_matches_status_and_gate_sets"
        ]

        assert len(handoff_checks) == 1
        assert handoff_checks[0]["ok"] is False
        assert "status_sha256_before_run mismatch" in handoff_checks[0]["message"]


def test_handoff_effective_required_gates_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.handoff_effective_gates.json"

        shutil.copytree(PACKAGE, package_copy)

        handoff_path = package_copy / "handoff" / "operator_handoff_report.json"
        handoff = _read_json(handoff_path)
        handoff["effective_required_gates"] = [
            gate_id
            for gate_id in handoff["effective_required_gates"]
            if gate_id != "q4_slo_ok"
        ]
        _write_json(handoff_path, handoff)

        handoff_sha = _sha256_file(handoff_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["handoff/operator_handoff_report.json"] = handoff_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["operator_handoff_report"]["sha256"] = handoff_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        handoff_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "handoff_matches_status_and_gate_sets"
        ]

        assert len(handoff_checks) == 1
        assert handoff_checks[0]["ok"] is False
        assert "effective_required_gates does not match" in handoff_checks[0]["message"]

def test_release_authority_status_digest_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.release_authority_status_digest.json"

        shutil.copytree(PACKAGE, package_copy)

        release_authority_path = (
            package_copy
            / "release_authority"
            / "release_authority_manifest.json"
        )
        release_authority = _read_json(release_authority_path)
        release_authority["inputs"]["status_json"]["sha256"] = "0" * 64
        _write_json(release_authority_path, release_authority)

        release_authority_sha = _sha256_file(release_authority_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"][
            "release_authority/release_authority_manifest.json"
        ] = release_authority_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["release_authority_manifest"]["sha256"] = release_authority_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        release_authority_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "release_authority_manifest_matches_package_core"
        ]

        assert len(release_authority_checks) == 1
        assert release_authority_checks[0]["ok"] is False
        assert "inputs.status_json.sha256 mismatch" in release_authority_checks[0]["message"]


def test_release_authority_effective_gates_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.release_authority_effective_gates.json"

        shutil.copytree(PACKAGE, package_copy)

        release_authority_path = (
            package_copy
            / "release_authority"
            / "release_authority_manifest.json"
        )
        release_authority = _read_json(release_authority_path)
        release_authority["authority"]["effective_required_gates"] = [
            gate_id
            for gate_id in release_authority["authority"]["effective_required_gates"]
            if gate_id != "q4_slo_ok"
        ]
        _write_json(release_authority_path, release_authority)

        release_authority_sha = _sha256_file(release_authority_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"][
            "release_authority/release_authority_manifest.json"
        ] = release_authority_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["release_authority_manifest"]["sha256"] = release_authority_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        release_authority_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "release_authority_manifest_matches_package_core"
        ]

        assert len(release_authority_checks) == 1
        assert release_authority_checks[0]["ok"] is False
        assert (
            "authority.effective_required_gates does not match package gate sets"
            in release_authority_checks[0]["message"]
        )

def test_ci_outcome_commit_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.ci_commit_mismatch.json"

        shutil.copytree(PACKAGE, package_copy)

        ci_path = package_copy / "ci" / "ci_outcome.json"
        ci_outcome = _read_json(ci_path)
        ci_outcome["commit_sha"] = "b" * 40
        _write_json(ci_path, ci_outcome)

        ci_sha = _sha256_file(ci_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["ci/ci_outcome.json"] = ci_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["ci_outcome"]["sha256"] = ci_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        ci_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "ci_outcome_and_publication_match_release_identity"
        ]

        assert len(ci_checks) == 1
        assert ci_checks[0]["ok"] is False
        assert "ci_outcome.commit_sha mismatch" in ci_checks[0]["message"]


def test_publication_ci_url_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.publication_ci_url.json"

        shutil.copytree(PACKAGE, package_copy)

        publication_path = package_copy / "publication" / "publication_snapshot.json"
        publication = _read_json(publication_path)
        publication["ci_outcome_url"] = (
            "https://github.com/HKati/pulse-release-gates-0.1/actions/runs/999999999"
        )
        _write_json(publication_path, publication)

        publication_sha = _sha256_file(publication_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["publication/publication_snapshot.json"] = publication_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["publication_snapshot"]["sha256"] = publication_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        ci_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "ci_outcome_and_publication_match_release_identity"
        ]

        assert len(ci_checks) == 1
        assert ci_checks[0]["ok"] is False
        assert "publication_snapshot.ci_outcome_url mismatch" in ci_checks[0]["message"]


def test_missing_package_digest_entry_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.missing_digest_entry.json"

        shutil.copytree(PACKAGE, package_copy)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"].pop("ci/ci_outcome.json")
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        coverage_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_digests_cover_manifest_payload"
        ]

        assert len(coverage_checks) == 1
        assert coverage_checks[0]["ok"] is False
        assert "ci/ci_outcome.json" in coverage_checks[0]["message"]
        assert "missing expected payload artifacts" in coverage_checks[0]["message"]


def test_unexpected_package_digest_entry_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.unexpected_digest_entry.json"

        shutil.copytree(PACKAGE, package_copy)

        extra_dir = package_copy / "extra"
        extra_dir.mkdir()
        extra_artifact = extra_dir / "unused.json"
        extra_artifact.write_text(
            json.dumps(
                {
                    "unused": True,
                    "note": "This artifact is not referenced by the package manifest.",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["extra/unused.json"] = _sha256_file(extra_artifact)
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        coverage_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_digests_cover_manifest_payload"
        ]

        assert len(coverage_checks) == 1
        assert coverage_checks[0]["ok"] is False
        assert "extra/unused.json" in coverage_checks[0]["message"]
        assert "unexpected artifact entries" in coverage_checks[0]["message"]

def test_untracked_package_file_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.untracked_file.json"

        shutil.copytree(PACKAGE, package_copy)

        extra_dir = package_copy / "extra"
        extra_dir.mkdir()
        extra_file = extra_dir / "untracked.json"
        extra_file.write_text(
            json.dumps(
                {
                    "untracked": True,
                    "note": "This file is present in the package but not declared.",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        inventory_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_inventory_matches_manifest"
        ]

        assert len(inventory_checks) == 1
        assert inventory_checks[0]["ok"] is False
        assert "extra/untracked.json" in inventory_checks[0]["message"]
        assert "unexpected files" in inventory_checks[0]["message"]


def test_missing_package_file_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.missing_file.json"

        shutil.copytree(PACKAGE, package_copy)

        readme_path = package_copy / "README.md"
        readme_path.unlink()

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        inventory_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_inventory_matches_manifest"
        ]

        assert len(inventory_checks) == 1
        assert inventory_checks[0]["ok"] is False
        assert "README.md" in inventory_checks[0]["message"]
        assert "missing expected files" in inventory_checks[0]["message"]

def test_noncanonical_status_artifact_path_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.noncanonical_status_path.json"

        shutil.copytree(PACKAGE, package_copy)

        old_status_path = package_copy / "status" / "status.json"
        new_status_path = package_copy / "status" / "status.alt.json"

        new_status_path.write_text(
            old_status_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        old_status_path.unlink()

        status_sha = _sha256_file(new_status_path)

        handoff_path = package_copy / "handoff" / "operator_handoff_report.json"
        handoff = _read_json(handoff_path)
        handoff["status_source"]["status_path"] = "status/status.alt.json"
        handoff["status_source"]["status_sha256_before_run"] = status_sha
        handoff["status_source"]["status_sha256_after_generation"] = status_sha
        handoff["status_source"]["status_sha256_after_run"] = status_sha
        _write_json(handoff_path, handoff)
        handoff_sha = _sha256_file(handoff_path)

        release_authority_path = (
            package_copy
            / "release_authority"
            / "release_authority_manifest.json"
        )
        release_authority = _read_json(release_authority_path)
        release_authority["inputs"]["status_json"]["path"] = "status/status.alt.json"
        release_authority["inputs"]["status_json"]["sha256"] = status_sha
        _write_json(release_authority_path, release_authority)
        release_authority_sha = _sha256_file(release_authority_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"].pop("status/status.json")
        digests["artifacts"]["status/status.alt.json"] = status_sha
        digests["artifacts"]["handoff/operator_handoff_report.json"] = handoff_sha
        digests["artifacts"][
            "release_authority/release_authority_manifest.json"
        ] = release_authority_sha
        _write_json(digests_path, digests)
        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["path"] = "status/status.alt.json"
        manifest["status_artifact"]["sha256"] = status_sha
        manifest["operator_handoff_report"]["sha256"] = handoff_sha
        manifest["release_authority_manifest"]["sha256"] = release_authority_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        layout_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_manifest_uses_canonical_layout"
        ]

        assert len(layout_checks) == 1
        assert layout_checks[0]["ok"] is False
        assert "status_artifact path mismatch" in layout_checks[0]["message"]
        assert "status/status.alt.json" in layout_checks[0]["message"]

def test_package_manifest_git_sha_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.package_manifest_git_sha.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["git_sha"] = "b" * 40
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        identity_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "package_identity_matches_release_surfaces"
        ]

        assert len(identity_checks) == 1
        assert identity_checks[0]["ok"] is False
        assert "package_manifest.git_sha mismatch" in identity_checks[0]["message"]
    
def test_malformed_effective_required_gate_id_fails_without_crash() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.malformed_gate_id.json"

        shutil.copytree(PACKAGE, package_copy)

        gate_sets_path = package_copy / "gates" / "materialized_gate_sets.json"
        gate_sets = _read_json(gate_sets_path)
        gate_sets["effective_required_gates"] = [
            {"bad": "gate-id-object"}
        ]
        _write_json(gate_sets_path, gate_sets)

        gate_sets_sha = _sha256_file(gate_sets_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["gates/materialized_gate_sets.json"] = gate_sets_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["materialized_gate_sets"]["sha256"] = gate_sets_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "effective_required_gates" in error
            and "must be a string gate ID" in error
            for error in report["errors"]
        )


def test_unsafe_manifest_artifact_path_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.unsafe_manifest_path.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["path"] = "../outside/status.json"
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "unsafe artifact path" in error
            or "schema validation failed" in error
            or "does not match" in error
            for error in report["errors"]
        )

def test_package_digests_self_digest_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.package_digests_self_mismatch.json"

        shutil.copytree(PACKAGE, package_copy)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)

        # Mutate the digest manifest itself without updating the package_manifest
        # reference to digests/package_digests.json. This must be detected as a
        # package-manifest digest mismatch.
        digests["package_id"] = "tampered-package-id"
        _write_json(digests_path, digests)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        digest_checks = [
            check
            for check in report["artifact_digests_checked"]
            if (
                check["artifact_path"] == "digests/package_digests.json"
                and check.get("source") == "package_manifest"
            )
        ]

        assert len(digest_checks) == 1
        assert digest_checks[0]["ok"] is False
        assert digest_checks[0]["actual_sha256"] is not None
        assert any(
            "digests/package_digests.json digest mismatch" in error
            for error in report["errors"]
        )


def test_unsafe_manifest_artifact_path_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.unsafe_manifest_path.json"

        shutil.copytree(PACKAGE, package_copy)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["status_artifact"]["path"] = "../outside/status.json"
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "unsafe artifact path" in error
            or "schema validation failed" in error
            or "does not match" in error
            for error in report["errors"]
        )


def test_publication_git_sha_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.publication_git_sha.json"

        shutil.copytree(PACKAGE, package_copy)

        publication_path = package_copy / "publication" / "publication_snapshot.json"
        publication = _read_json(publication_path)
        publication["git_sha"] = "b" * 40
        _write_json(publication_path, publication)

        publication_sha = _sha256_file(publication_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["publication/publication_snapshot.json"] = publication_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["publication_snapshot"]["sha256"] = publication_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False

        ci_checks = [
            check
            for check in report["cross_artifact_checks"]
            if check["name"] == "ci_outcome_and_publication_match_release_identity"
        ]

        assert len(ci_checks) == 1
        assert ci_checks[0]["ok"] is False
        assert "publication_snapshot.git_sha mismatch" in ci_checks[0]["message"]


def test_publication_package_id_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.publication_package_id.json"

        shutil.copytree(PACKAGE, package_copy)

        publication_path = package_copy / "publication" / "publication_snapshot.json"
        publication = _read_json(publication_path)
        publication["package_id"] = "tampered-publication-package-id"
        _write_json(publication_path, publication)

        publication_sha = _sha256_file(publication_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["publication/publication_snapshot.json"] = publication_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["publication_snapshot"]["sha256"] = publication_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "publication_snapshot.package_id mismatch" in error
            for error in report["errors"]
        )


def test_publication_run_key_mismatch_fails_with_schema_valid_report() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-ra1-verifier-") as tmp:
        tmp_path = Path(tmp)
        package_copy = tmp_path / "package"
        out_path = tmp_path / "verifier_report.publication_run_key.json"

        shutil.copytree(PACKAGE, package_copy)

        publication_path = package_copy / "publication" / "publication_snapshot.json"
        publication = _read_json(publication_path)
        publication["run_key"] = "tampered-publication-run-key"
        _write_json(publication_path, publication)

        publication_sha = _sha256_file(publication_path)

        digests_path = package_copy / "digests" / "package_digests.json"
        digests = _read_json(digests_path)
        digests["artifacts"]["publication/publication_snapshot.json"] = publication_sha
        _write_json(digests_path, digests)

        digests_sha = _sha256_file(digests_path)

        manifest_path = package_copy / "package_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["publication_snapshot"]["sha256"] = publication_sha
        manifest["package_digests"]["sha256"] = digests_sha
        _write_json(manifest_path, manifest)

        result = _run(package_copy, out_path)

        assert result.returncode == 1
        assert out_path.exists()
        assert "Traceback" not in result.stderr

        report = _read_json(out_path)
        _validate_report(report)

        assert report["ok"] is False
        assert any(
            "publication_snapshot.run_key mismatch" in error
            for error in report["errors"]
        )


def main() -> int:
    tests = [
        test_valid_ra1_minimal_package_verifies,
        test_digest_mismatch_fails_with_schema_valid_report,
        test_symlinked_artifact_outside_package_root_fails_with_schema_valid_report,
        test_malformed_digest_string_fails_with_schema_valid_report,
        test_schema_invalid_package_artifact_fails_with_schema_valid_report,
        test_false_effective_required_gate_fails_with_schema_valid_report,
        test_materialized_gate_set_policy_mismatch_fails_with_schema_valid_report,
        test_handoff_status_digest_mismatch_fails_with_schema_valid_report,
        test_handoff_effective_required_gates_mismatch_fails_with_schema_valid_report,
        test_release_authority_status_digest_mismatch_fails_with_schema_valid_report,
        test_release_authority_effective_gates_mismatch_fails_with_schema_valid_report,
        test_ci_outcome_commit_mismatch_fails_with_schema_valid_report,
        test_publication_ci_url_mismatch_fails_with_schema_valid_report,
        test_missing_package_digest_entry_fails_with_schema_valid_report,
        test_unexpected_package_digest_entry_fails_with_schema_valid_report,
        test_untracked_package_file_fails_with_schema_valid_report,
        test_missing_package_file_fails_with_schema_valid_report,
        test_noncanonical_status_artifact_path_fails_with_schema_valid_report,
        test_package_manifest_git_sha_mismatch_fails_with_schema_valid_report,
        test_malformed_effective_required_gate_id_fails_without_crash,
        test_package_digests_self_digest_mismatch_fails_with_schema_valid_report,
        test_unsafe_manifest_artifact_path_fails_with_schema_valid_report,
        test_publication_git_sha_mismatch_fails_with_schema_valid_report,
        test_publication_package_id_mismatch_fails_with_schema_valid_report,
        test_publication_run_key_mismatch_fails_with_schema_valid_report,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 package verifier tool smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
