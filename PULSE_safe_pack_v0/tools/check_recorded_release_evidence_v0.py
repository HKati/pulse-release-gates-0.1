#!/usr/bin/env python3
"""Verify recorded release evidence bindings for release-grade prerequisites.

This checker validates that candidate detector materialization artifacts,
canonical external summaries, and refusal-delta evidence are bound to:

- the declared run identity
- the declared policy context
- the declared subject binding
- trusted provenance expectations
- the declared raw evidence digest
- the manifest-declared gate materialization relations

The checker is prerequisite-only.
It does not compute release authority.
It does not replace check_gates.py.
It does not change status.json semantics, gate policy, or CI allow/block logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION = "recorded_release_evidence_verifier_v0"
REPORT_VERSION = "0.1.0"
INPUT_MANIFEST_SCHEMA_VERSION = "release_evidence_input_manifest_v0"
VERIFIED = "verified"
FAILED = "failed"


REQUIRED_BINDING_KEYS = ("git_sha", "run_key")


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{label} not found: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report parse errors clearly
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return data


def _section(
    obj: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    return value


def _list_section(
    obj: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> list[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        errors.append(f"{label}.{key} must be an array")
        return []
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value.lower()
    )


def _normalize_gate_list(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _binding_matches(
    actual: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> bool:
    ok = True
    for key in REQUIRED_BINDING_KEYS:
        expected_value = expected.get(key)
        actual_value = actual.get(key)
        if actual_value != expected_value:
            errors.append(
                f"{label}.{key} mismatch: expected {expected_value!r}, got {actual_value!r}"
            )
            ok = False
    return ok


def _policy_binding_matches(
    actual: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> bool:
    ok = True
    for key in ("policy_set", "policy_sha256"):
        expected_value = expected.get(key)
        actual_value = actual.get(key)
        if actual_value != expected_value:
            errors.append(
                f"{label}.{key} mismatch: expected {expected_value!r}, got {actual_value!r}"
            )
            ok = False
    return ok


def _build_empty_report(
    manifest_path: Path,
    manifest_sha256: str | None,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_version": REPORT_VERSION,
        "status": FAILED,
        "manifest": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "schema_version": None if manifest is None else manifest.get("schema_version"),
        },
        "run_identity": None if manifest is None else manifest.get("run_identity"),
        "subject": None if manifest is None else manifest.get("subject"),
        "policy_binding": None if manifest is None else manifest.get("policy_binding"),
        "registry_binding": None if manifest is None else manifest.get("registry_binding"),
        "verified_subjects": {},
        "evidence_results": {},
        "relation_binding_results": {},
        "gate_materialization_admissibility": {},
        "errors": [],
    }


def check_recorded_release_evidence(
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    manifest = _load_json(manifest_path, "release_evidence_input_manifest_v0.json", errors)
    manifest_sha256 = _sha256_file(manifest_path) if manifest_path.exists() else None
    report = _build_empty_report(manifest_path, manifest_sha256, manifest)
    if manifest is None:
        report["errors"] = errors
        return report

    if manifest.get("schema_version") != INPUT_MANIFEST_SCHEMA_VERSION:
        errors.append(
            "manifest.schema_version must be "
            f"{INPUT_MANIFEST_SCHEMA_VERSION!r}"
        )

    run_identity = _section(manifest, "run_identity", errors, "manifest")
    subject = _section(manifest, "subject", errors, "manifest")
    policy_binding = _section(manifest, "policy_binding", errors, "manifest")
    candidate_evidence = _section(manifest, "candidate_evidence", errors, "manifest")
    expected_relation_bindings = _section(
        manifest,
        "expected_relation_bindings",
        errors,
        "manifest",
    )
    expected_gate_materialization = _section(
        manifest,
        "expected_gate_materialization",
        errors,
        "manifest",
    )

    report["run_identity"] = run_identity
    report["subject"] = subject
    report["policy_binding"] = policy_binding
    report["registry_binding"] = manifest.get("registry_binding")
    report["verified_subjects"] = {
        "git_sha": run_identity.get("git_sha"),
        "run_key": run_identity.get("run_key"),
        "commit_sha": subject.get("commit_sha"),
    }

    if run_identity.get("run_mode") != "prod":
        errors.append(
            "manifest.run_identity.run_mode must be 'prod' for recorded "
            f"release-evidence verification (got {run_identity.get('run_mode')!r})"
        )
    if policy_binding.get("policy_set") != "required+release_required":
        errors.append(
            "manifest.policy_binding.policy_set must be 'required+release_required' "
            f"(got {policy_binding.get('policy_set')!r})"
        )
    if not _hex_digest(policy_binding.get("policy_sha256")):
        errors.append("manifest.policy_binding.policy_sha256 must be a 64-hex sha256")

    evidence_results: dict[str, Any] = {}
    verified_evidence_ids: set[str] = set()
    candidate_artifacts: dict[str, dict[str, Any]] = {}

    for evidence_id, candidate in candidate_evidence.items():
        candidate_errors: list[str] = []
        result: dict[str, Any] = {
            "path": None,
            "expected_sha256": None,
            "actual_sha256": None,
            "schema_version": None,
            "status": FAILED,
            "digest_match": False,
            "schema_version_match": False,
            "run_identity_match": False,
            "subject_binding_match": False,
            "policy_binding_match": False,
            "trusted_producer_verified": False,
            "raw_evidence_verified": False,
            "required_for_gates_match": False,
            "errors": candidate_errors,
        }
        evidence_results[evidence_id] = result

        if not isinstance(candidate, dict):
            errors.append(f"manifest.candidate_evidence.{evidence_id} must be an object")
            candidate_errors.append("candidate manifest entry must be an object")
            continue

        path_value = candidate.get("path")
        result["path"] = path_value
        expected_sha256 = candidate.get("expected_sha256")
        result["expected_sha256"] = expected_sha256
        expected_schema_version = candidate.get("schema_version")
        expected_binding = _section(
            candidate,
            "subject_binding",
            candidate_errors,
            f"manifest.candidate_evidence.{evidence_id}",
        )
        expected_required_gates = _normalize_gate_list(candidate.get("required_for_gates"))
        trusted_required = (
            _section(
                candidate,
                "provenance_expectations",
                candidate_errors,
                f"manifest.candidate_evidence.{evidence_id}",
            ).get("trusted_producer_required")
            is True
        )

        if candidate.get("verification_required") is not True:
            candidate_errors.append(
                "candidate evidence verification_required must be literal true"
            )

        if not isinstance(path_value, str) or not path_value:
            candidate_errors.append("candidate evidence path must be a non-empty string")
            continue

        artifact_path = repo_root / path_value
        if not artifact_path.exists():
            candidate_errors.append(f"candidate artifact not found: {artifact_path}")
            continue

        actual_sha256 = _sha256_file(artifact_path)
        result["actual_sha256"] = actual_sha256
        if actual_sha256 == expected_sha256:
            result["digest_match"] = True
        else:
            candidate_errors.append(
                f"candidate artifact sha256 mismatch: expected {expected_sha256!r}, got {actual_sha256!r}"
            )

        artifact = _load_json(artifact_path, f"candidate artifact {evidence_id}", candidate_errors)
        if artifact is None:
            continue
        candidate_artifacts[evidence_id] = artifact
        result["schema_version"] = artifact.get("schema_version")

        if artifact.get("schema_version") == expected_schema_version:
            result["schema_version_match"] = True
        else:
            candidate_errors.append(
                f"candidate artifact schema_version mismatch: expected {expected_schema_version!r}, got {artifact.get('schema_version')!r}"
            )

        artifact_run_identity = _section(
            artifact,
            "run_identity",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        if _binding_matches(
            artifact_run_identity,
            run_identity,
            f"candidate artifact {evidence_id}.run_identity",
            candidate_errors,
        ) and artifact_run_identity.get("run_mode") == run_identity.get("run_mode"):
            result["run_identity_match"] = True
        else:
            if artifact_run_identity.get("run_mode") != run_identity.get("run_mode"):
                candidate_errors.append(
                    "candidate artifact "
                    f"{evidence_id}.run_identity.run_mode mismatch: expected {run_identity.get('run_mode')!r}, got {artifact_run_identity.get('run_mode')!r}"
                )

        artifact_subject_binding = _section(
            artifact,
            "subject_binding",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        subject_expected_ok = _binding_matches(
            artifact_subject_binding,
            expected_binding,
            f"candidate artifact {evidence_id}.subject_binding",
            candidate_errors,
        )
        commit_sha = subject.get("commit_sha")
        if commit_sha is not None and artifact_subject_binding.get("git_sha") != commit_sha:
            candidate_errors.append(
                f"candidate artifact {evidence_id}.subject_binding.git_sha must also match manifest.subject.commit_sha {commit_sha!r}"
            )
            subject_expected_ok = False
        if subject_expected_ok:
            result["subject_binding_match"] = True

        artifact_policy_binding = _section(
            artifact,
            "policy_binding",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        if _policy_binding_matches(
            artifact_policy_binding,
            policy_binding,
            f"candidate artifact {evidence_id}.policy_binding",
            candidate_errors,
        ):
            result["policy_binding_match"] = True

        artifact_provenance = _section(
            artifact,
            "provenance",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        if trusted_required:
            if artifact_provenance.get("trusted_producer") is True:
                result["trusted_producer_verified"] = True
            else:
                candidate_errors.append(
                    f"candidate artifact {evidence_id}.provenance.trusted_producer must be true"
                )
        else:
            result["trusted_producer_verified"] = True

        raw_binding = _section(
            artifact,
            "raw_evidence_binding",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        raw_path_value = raw_binding.get("path")
        raw_sha_value = raw_binding.get("sha256")
        if not isinstance(raw_path_value, str) or not raw_path_value:
            candidate_errors.append(
                f"candidate artifact {evidence_id}.raw_evidence_binding.path must be a non-empty string"
            )
        elif not _hex_digest(raw_sha_value):
            candidate_errors.append(
                f"candidate artifact {evidence_id}.raw_evidence_binding.sha256 must be a 64-hex sha256"
            )
        else:
            raw_path = repo_root / raw_path_value
            if not raw_path.exists():
                candidate_errors.append(f"raw evidence not found: {raw_path}")
            else:
                actual_raw_sha = _sha256_file(raw_path)
                if actual_raw_sha == raw_sha_value:
                    result["raw_evidence_verified"] = True
                else:
                    candidate_errors.append(
                        f"raw evidence sha256 mismatch for {evidence_id}: expected {raw_sha_value!r}, got {actual_raw_sha!r}"
                    )

        artifact_required_gates = _normalize_gate_list(artifact.get("required_for_gates"))
        if artifact_required_gates == expected_required_gates:
            result["required_for_gates_match"] = True
        else:
            candidate_errors.append(
                "candidate artifact required_for_gates mismatch: expected "
                f"{sorted(expected_required_gates)!r}, got {sorted(artifact_required_gates)!r}"
            )

        if not candidate_errors:
            result["status"] = VERIFIED
            verified_evidence_ids.add(evidence_id)

    relation_binding_results: dict[str, Any] = {}
    satisfied_relation_ids: set[str] = set()
    for relation_id, relation in expected_relation_bindings.items():
        relation_errors: list[str] = []
        result = {
            "status": FAILED,
            "binding_type": None,
            "source_evidence_id": None,
            "expected_gate_id": None,
            "target": None,
            "errors": relation_errors,
        }
        relation_binding_results[relation_id] = result

        if not isinstance(relation, dict):
            relation_errors.append("relation binding entry must be an object")
            continue

        binding_type = relation.get("binding_type")
        source_evidence_id = relation.get("source_evidence_id")
        expected_gate_id = relation.get("expected_gate_id")
        target = relation.get("target")
        result["binding_type"] = binding_type
        result["source_evidence_id"] = source_evidence_id
        result["expected_gate_id"] = expected_gate_id
        result["target"] = target

        if source_evidence_id not in candidate_artifacts:
            relation_errors.append(
                f"relation binding source evidence missing: {source_evidence_id!r}"
            )
            continue
        if source_evidence_id not in verified_evidence_ids:
            relation_errors.append(
                f"relation binding source evidence not verified: {source_evidence_id!r}"
            )
            continue
        if expected_gate_id not in expected_gate_materialization:
            relation_errors.append(
                f"relation binding expected gate missing from manifest: {expected_gate_id!r}"
            )
            continue

        artifact = candidate_artifacts[source_evidence_id]
        artifact_required_gates = _normalize_gate_list(artifact.get("required_for_gates"))
        artifact_subject_binding = artifact.get("subject_binding")
        if not isinstance(artifact_subject_binding, dict):
            relation_errors.append(
                f"candidate artifact {source_evidence_id}.subject_binding must be an object"
            )
            continue

        if binding_type == "artifact_to_subject":
            commit_sha = subject.get("commit_sha")
            if artifact_subject_binding.get("git_sha") != commit_sha:
                relation_errors.append(
                    f"artifact_to_subject relation requires git_sha {commit_sha!r}"
                )
            elif target != "subject.commit_sha":
                relation_errors.append(
                    f"artifact_to_subject relation target must be 'subject.commit_sha' (got {target!r})"
                )
        elif binding_type == "artifact_to_gate":
            if expected_gate_id not in artifact_required_gates:
                relation_errors.append(
                    f"artifact_to_gate relation requires {source_evidence_id!r} to target gate {expected_gate_id!r}"
                )
            elif target != f"gate.{expected_gate_id}":
                relation_errors.append(
                    f"artifact_to_gate relation target must be 'gate.{expected_gate_id}' (got {target!r})"
                )
        else:
            relation_errors.append(f"unsupported binding_type: {binding_type!r}")

        if not relation_errors:
            result["status"] = VERIFIED
            satisfied_relation_ids.add(relation_id)

    gate_materialization_admissibility: dict[str, Any] = {}
    for gate_id, materialization in expected_gate_materialization.items():
        gate_errors: list[str] = []
        result = {
            "status": FAILED,
            "expected_value": None,
            "candidate_evidence_ids": [],
            "relation_binding_ids": [],
            "admissible": False,
            "errors": gate_errors,
        }
        gate_materialization_admissibility[gate_id] = result

        if not isinstance(materialization, dict):
            gate_errors.append("gate materialization entry must be an object")
            continue

        result["expected_value"] = materialization.get("expected_value")
        candidate_ids = materialization.get("candidate_evidence_ids")
        relation_ids = materialization.get("relation_binding_ids")
        result["candidate_evidence_ids"] = candidate_ids if isinstance(candidate_ids, list) else []
        result["relation_binding_ids"] = relation_ids if isinstance(relation_ids, list) else []

        if materialization.get("expected_value") is not True:
            gate_errors.append(f"gate {gate_id} expected_value must be literal true")
        if materialization.get("policy_relation") != "release_required":
            gate_errors.append(
                f"gate {gate_id} policy_relation must be 'release_required'"
            )
        if materialization.get("materialization_allowed_without_verifier") is not False:
            gate_errors.append(
                f"gate {gate_id} materialization_allowed_without_verifier must be false"
            )
        if not isinstance(candidate_ids, list):
            gate_errors.append(f"gate {gate_id} candidate_evidence_ids must be an array")
            candidate_ids = []
        if not isinstance(relation_ids, list):
            gate_errors.append(f"gate {gate_id} relation_binding_ids must be an array")
            relation_ids = []

        for evidence_id in candidate_ids:
            if evidence_id not in verified_evidence_ids:
                gate_errors.append(
                    f"gate {gate_id} candidate evidence not verified: {evidence_id!r}"
                )
        for relation_id in relation_ids:
            if relation_id not in satisfied_relation_ids:
                gate_errors.append(
                    f"gate {gate_id} relation binding not satisfied: {relation_id!r}"
                )

        if not gate_errors:
            result["status"] = VERIFIED
            result["admissible"] = True

    report["evidence_results"] = evidence_results
    report["relation_binding_results"] = relation_binding_results
    report["gate_materialization_admissibility"] = gate_materialization_admissibility
    report["errors"] = errors + [
        f"{evidence_id}: {message}"
        for evidence_id, result in evidence_results.items()
        for message in result["errors"]
    ] + [
        f"{relation_id}: {message}"
        for relation_id, result in relation_binding_results.items()
        for message in result["errors"]
    ] + [
        f"{gate_id}: {message}"
        for gate_id, result in gate_materialization_admissibility.items()
        for message in result["errors"]
    ]

    if not report["errors"]:
        report["status"] = VERIFIED
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify recorded release evidence bindings for release-grade "
            "materialization prerequisites."
        )
    )
    parser.add_argument(
        "--manifest",
        default="PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json",
        help="Path to release_evidence_input_manifest_v0.json.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to resolve candidate and raw evidence paths.",
    )
    parser.add_argument(
        "--out-json",
        default="PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json",
        help="Path to write the machine-readable verifier report.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    repo_root = Path(args.repo_root)
    out_json = Path(args.out_json)

    report = check_recorded_release_evidence(manifest_path=manifest_path, repo_root=repo_root)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if report["status"] != VERIFIED:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in report["errors"]:
            print(f" - {error}", file=sys.stderr)
        print(
            f"Verifier report written to {out_json}",
            file=sys.stderr,
        )
        return 1

    print("OK: recorded release-evidence verification satisfied")
    print(f"Verifier report written to {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
