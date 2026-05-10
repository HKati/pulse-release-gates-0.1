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

def main() -> int:
    tests = [
        test_valid_ra1_minimal_package_verifies,
        test_digest_mismatch_fails_with_schema_valid_report,
        test_symlinked_artifact_outside_package_root_fails_with_schema_valid_report,
        test_malformed_digest_string_fails_with_schema_valid_report,
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
