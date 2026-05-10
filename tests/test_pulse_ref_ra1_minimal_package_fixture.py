from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "tests" / "fixtures" / "pulse_ref_ra1_package_minimal"

RELEASE_AUTHORITY_CHECKER = (
    ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_authority_manifest_v0.py"
)
RELEASE_AUTHORITY_SCHEMA = ROOT / "schemas" / "release_authority_v0.schema.json"


def _artifact(rel_path: str) -> Path:
    return PACKAGE / rel_path


def _read_json(rel_path: str) -> dict[str, Any]:
    return json.loads(_artifact(rel_path).read_text(encoding="utf-8"))


def _read_schema(rel_path: str) -> dict[str, Any]:
    return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def _validate_schema(instance: dict[str, Any], schema_path: str) -> None:
    schema = _read_schema(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        details = "\n".join(
            f"{list(error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise AssertionError(f"schema validation failed for {schema_path}:\n{details}")


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)

    return out


def test_expected_ra1_minimal_package_artifacts_exist() -> None:
    expected = [
        "README.md",
        "package_manifest.json",
        "status/status.json",
        "policy/pulse_gate_policy_v0.yml",
        "policy/pulse_gate_registry_v0.yml",
        "gates/materialized_gate_sets.json",
        "handoff/operator_handoff_report.json",
        "release_authority/release_authority_manifest.json",
        "ci/ci_outcome.json",
        "publication/publication_snapshot.json",
        "digests/package_digests.json",
    ]

    missing = [
        rel_path
        for rel_path in expected
        if not _artifact(rel_path).exists()
    ]

    assert missing == []


def test_ra1_minimal_package_json_artifacts_validate_schemas() -> None:
    targets = [
        (
            "package_manifest.json",
            "schemas/pulse_ref_release_reference_package_v0.schema.json",
        ),
        (
            "gates/materialized_gate_sets.json",
            "schemas/pulse_ref_materialized_gate_sets_v0.schema.json",
        ),
        (
            "handoff/operator_handoff_report.json",
            "schemas/pulse_ref_operator_handoff_report_v0.schema.json",
        ),
        (
            "ci/ci_outcome.json",
            "schemas/pulse_ref_ci_outcome_v0.schema.json",
        ),
        (
            "publication/publication_snapshot.json",
            "schemas/pulse_ref_publication_snapshot_v0.schema.json",
        ),
         (
            "digests/package_digests.json",
            "schemas/pulse_ref_package_digests_v0.schema.json",
        ),
    ]

    for artifact_path, schema_path in targets:
        _validate_schema(_read_json(artifact_path), schema_path)


def test_release_authority_manifest_validates_with_checker() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(RELEASE_AUTHORITY_CHECKER),
            "--manifest",
            str(_artifact("release_authority/release_authority_manifest.json")),
            "--schema",
            str(RELEASE_AUTHORITY_SCHEMA),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"release authority manifest validation failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_materialized_gate_sets_match_packaged_policy() -> None:
    policy_path = _artifact("policy/pulse_gate_policy_v0.yml")
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    gate_sets = _read_json("gates/materialized_gate_sets.json")

    required = list(policy["gates"]["required"])
    release_required = list(policy["gates"]["release_required"])
    effective = _unique_preserve_order(required + release_required)

    assert gate_sets["policy_path"] == "policy/pulse_gate_policy_v0.yml"
    assert gate_sets["policy_sha256"] == _sha256_file(policy_path)

    assert gate_sets["sets"]["required"] == required
    assert gate_sets["sets"]["release_required"] == release_required
    assert gate_sets["effective_required_gates"] == effective

    boundary = gate_sets["authority_boundary"]
    assert boundary["source"] == "declared_gate_policy"
    assert boundary["creates_release_authority"] is False


def test_status_satisfies_effective_required_gates() -> None:
    status = _read_json("status/status.json")
    gate_sets = _read_json("gates/materialized_gate_sets.json")

    assert status["metrics"]["run_mode"] == "prod"
    assert status["diagnostics"]["gates_stubbed"] is False

    status_gates = status["gates"]
    effective_required_gates = gate_sets["effective_required_gates"]

    missing = [
        gate_id
        for gate_id in effective_required_gates
        if gate_id not in status_gates
    ]
    false_gates = [
        gate_id
        for gate_id in effective_required_gates
        if status_gates.get(gate_id) is not True
    ]

    assert missing == []
    assert false_gates == []


def test_handoff_report_matches_status_and_materialized_gate_sets() -> None:
    handoff = _read_json("handoff/operator_handoff_report.json")
    gate_sets = _read_json("gates/materialized_gate_sets.json")

    status_sha = _sha256_file(_artifact("status/status.json"))
    policy_sha = _sha256_file(_artifact("policy/pulse_gate_policy_v0.yml"))
    gate_sets_sha = _sha256_file(_artifact("gates/materialized_gate_sets.json"))

    assert handoff["ok"] is True
    assert handoff["gate_mode"] == "release-grade"
    assert handoff["errors"] == []

    status_source = handoff["status_source"]
    assert status_source["mode"] == "existing"
    assert status_source["status_path"] == "status/status.json"
    assert status_source["status_sha256_before_run"] == status_sha
    assert status_source["status_sha256_after_generation"] == status_sha
    assert status_source["status_sha256_after_run"] == status_sha

    assert handoff["materialized_gate_sets"] == gate_sets["sets"]
    assert handoff["effective_required_gates"] == gate_sets["effective_required_gates"]

    files = {
        entry["path"]: entry
        for entry in handoff["files"]
    }

    assert files["status/status.json"]["exists"] is True
    assert files["status/status.json"]["sha256"] == status_sha

    assert files["policy/pulse_gate_policy_v0.yml"]["exists"] is True
    assert files["policy/pulse_gate_policy_v0.yml"]["sha256"] == policy_sha

    assert files["gates/materialized_gate_sets.json"]["exists"] is True
    assert files["gates/materialized_gate_sets.json"]["sha256"] == gate_sets_sha

    command_names = [
        command["name"]
        for command in handoff["commands"]
    ]

    assert "materialize_required" in command_names
    assert "materialize_release_required" in command_names
    assert "check_gates_release-grade" in command_names

    boundary = handoff["authority_boundary"]
    assert boundary["handoff_role"] == "release_grade_reconstruction"
    assert boundary["creates_release_authority"] is False


def test_release_authority_manifest_matches_package_core() -> None:
    manifest = _read_json("release_authority/release_authority_manifest.json")
    gate_sets = _read_json("gates/materialized_gate_sets.json")

    assert manifest["run_identity"]["run_mode"] == "prod"

    inputs = manifest["inputs"]

    assert inputs["status_json"]["path"] == "status/status.json"
    assert inputs["status_json"]["sha256"] == _sha256_file(
        _artifact("status/status.json")
    )

    assert inputs["gate_policy"]["path"] == "policy/pulse_gate_policy_v0.yml"
    assert inputs["gate_policy"]["sha256"] == _sha256_file(
        _artifact("policy/pulse_gate_policy_v0.yml")
    )

    assert inputs["gate_registry"]["path"] == "policy/pulse_gate_registry_v0.yml"
    assert inputs["gate_registry"]["sha256"] == _sha256_file(
        _artifact("policy/pulse_gate_registry_v0.yml")
    )

    authority = manifest["authority"]
    assert authority["policy_set"] == "required+release_required"
    assert authority["release_required_materialized"] is True
    assert authority["effective_required_gates"] == gate_sets["effective_required_gates"]

    evaluation = manifest["evaluation"]
    assert evaluation["failed_required_gates"] == []
    assert evaluation["missing_required_gates"] == []

    expected_results = {
        gate_id: True
        for gate_id in gate_sets["effective_required_gates"]
    }
    assert evaluation["required_gate_results"] == expected_results

    decision = manifest["decision"]
    assert decision["state"] == "PASS"
    assert decision["fail_closed"] is True

    diagnostics = manifest["diagnostics"]
    assert diagnostics["shadow_surfaces_non_normative"] is True


def test_ci_outcome_and_publication_snapshot_preserve_boundary() -> None:
    ci_outcome = _read_json("ci/ci_outcome.json")
    publication = _read_json("publication/publication_snapshot.json")
    release_authority = _read_json("release_authority/release_authority_manifest.json")

    assert ci_outcome["provider"] == "github_actions"
    assert ci_outcome["gate_check_conclusion"] == "success"
    assert ci_outcome["authority_boundary"]["creates_release_authority"] is False

    assert publication["creates_release_authority"] is False

    assert ci_outcome["run_id"] == release_authority["run_identity"]["run_id"]
    assert str(ci_outcome["run_attempt"]) == str(
        release_authority["run_identity"]["attempt"]
    )
    assert ci_outcome["commit_sha"] == release_authority["run_identity"]["git_sha"]

    assert publication["git_sha"] == ci_outcome["commit_sha"]
    assert ci_outcome["run_url"] == publication["ci_outcome_url"]

def test_package_digests_match_current_fixture_artifacts() -> None:
    package_digests = _read_json("digests/package_digests.json")

    assert package_digests["schema"] == "pulse_ref_package_digests_v0"
    assert package_digests["algorithm"] == "sha256"

    boundary = package_digests["authority_boundary"]
    assert boundary["digest_role"] == "artifact_integrity_verification"
    assert boundary["creates_release_authority"] is False

    artifacts = package_digests["artifacts"]

    expected_artifacts = [
        "README.md",
        "status/status.json",
        "policy/pulse_gate_policy_v0.yml",
        "policy/pulse_gate_registry_v0.yml",
        "gates/materialized_gate_sets.json",
        "handoff/operator_handoff_report.json",
        "release_authority/release_authority_manifest.json",
        "ci/ci_outcome.json",
        "publication/publication_snapshot.json",
    ]

    assert sorted(artifacts) == sorted(expected_artifacts)

    mismatches = []

    for rel_path in expected_artifacts:
        actual_sha = _sha256_file(_artifact(rel_path))
        expected_sha = artifacts[rel_path]

        if actual_sha != expected_sha:
            mismatches.append(
                {
                    "path": rel_path,
                    "expected": expected_sha,
                    "actual": actual_sha,
                }
            )

    assert mismatches == []

def test_package_manifest_matches_current_fixture_artifacts() -> None:
    manifest = _read_json("package_manifest.json")

    assert manifest["schema"] == "pulse_ref_release_reference_package_v0"
    assert manifest["package_id"] == "pulse-ref-ra1-minimal"
    assert manifest["run_key"] == "pulse-ref-ra1-minimal-fixture"
    assert manifest["git_sha"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    expected_refs = {
        "status_artifact": "status/status.json",
        "gate_policy": "policy/pulse_gate_policy_v0.yml",
        "gate_registry": "policy/pulse_gate_registry_v0.yml",
        "materialized_gate_sets": "gates/materialized_gate_sets.json",
        "operator_handoff_report": "handoff/operator_handoff_report.json",
        "release_authority_manifest": "release_authority/release_authority_manifest.json",
        "ci_outcome": "ci/ci_outcome.json",
        "publication_snapshot": "publication/publication_snapshot.json",
        "package_digests": "digests/package_digests.json",
    }

    mismatches = []

    for field, rel_path in expected_refs.items():
        artifact_ref = manifest[field]

        if artifact_ref["path"] != rel_path:
            mismatches.append(
                {
                    "field": field,
                    "expected_path": rel_path,
                    "actual_path": artifact_ref["path"],
                }
            )
            continue

        actual_sha = _sha256_file(_artifact(rel_path))
        expected_sha = artifact_ref["sha256"]

        if actual_sha != expected_sha:
            mismatches.append(
                {
                    "field": field,
                    "path": rel_path,
                    "expected_sha": expected_sha,
                    "actual_sha": actual_sha,
                }
            )

    assert mismatches == []

    boundary = manifest["authority_boundary"]
    assert boundary["package_role"] == "audit_preservation_reconstruction"
    assert boundary["creates_release_authority"] is False

    ci_outcome = _read_json("ci/ci_outcome.json")
    publication = _read_json("publication/publication_snapshot.json")
    release_authority = _read_json("release_authority/release_authority_manifest.json")

    assert manifest["git_sha"] == ci_outcome["commit_sha"]
    assert manifest["git_sha"] == publication["git_sha"]
    assert manifest["git_sha"] == release_authority["run_identity"]["git_sha"]

    assert manifest["run_key"] == publication["run_key"]

def main() -> int:
    tests = [
        test_expected_ra1_minimal_package_artifacts_exist,
        test_ra1_minimal_package_json_artifacts_validate_schemas,
        test_release_authority_manifest_validates_with_checker,
        test_materialized_gate_sets_match_packaged_policy,
        test_status_satisfies_effective_required_gates,
        test_handoff_report_matches_status_and_materialized_gate_sets,
        test_release_authority_manifest_matches_package_core,
        test_ci_outcome_and_publication_snapshot_preserve_boundary,
        test_package_digests_match_current_fixture_artifacts,
        test_package_manifest_matches_current_fixture_artifacts,
    ]
    
    

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 minimal package fixture smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
