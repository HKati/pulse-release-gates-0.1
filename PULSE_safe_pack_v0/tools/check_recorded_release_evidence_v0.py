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

try:
    import yaml
except Exception:  # pragma: no cover - fail-closed at runtime if unavailable
    yaml = None

if __package__:
    from .build_recorded_release_candidates_v0 import (
        build_canonical_candidates_for_replay,
    )
else:  # pragma: no cover - direct CLI execution
    from build_recorded_release_candidates_v0 import (
        build_canonical_candidates_for_replay,
    )

REPORT_SCHEMA_VERSION = "recorded_release_evidence_verifier_v0"
REPORT_VERSION = "0.2.0"
INPUT_MANIFEST_SCHEMA_VERSION = "release_evidence_input_manifest_v0"
VERIFIED = "verified"
FAILED = "failed"
EXPECTED_POLICY_SET = "required+release_required"
EXPECTED_RUN_MODE = "prod"

REQUIRED_BINDING_KEYS = ("git_sha", "run_key")


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _yaml_loader_no_duplicates():
    if yaml is None:
        raise RuntimeError("PyYAML is required for policy/registry verification")

    class Loader(yaml.SafeLoader):
        pass

    def construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML key {key!r}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    Loader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    return Loader


def _is_hex_digest(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(
        c in "0123456789abcdef" for c in value.lower()
    )


def _is_git_sha(value: Any) -> bool:
    return _is_hex_digest(value, 40)


def _is_sha256(value: Any) -> bool:
    return _is_hex_digest(value, 64)


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _candidate_for_replay_comparison(
    candidate: dict[str, Any],
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    """Normalize only the non-authoritative creation timestamp."""

    created_utc = candidate.get("created_utc")

    if not _is_non_empty_text(created_utc):
        errors.append(
            f"{label}.created_utc must be a non-empty string"
        )
        return None

    normalized = dict(candidate)
    normalized["created_utc"] = (
        "<normalized-created-utc>"
    )

    return normalized

def _safe_report_digest(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
    except OSError:
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _sha256_file(path: Path, label: str, errors: list[str]) -> str | None:
    try:
        if not path.exists():
            errors.append(f"{label} not found: {path}")
            return None
        if not path.is_file():
            errors.append(f"{label} must be a file: {path}")
            return None
    except OSError as exc:
        errors.append(f"{label} path check failed: {exc}")
        return None

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return None
    return digest.hexdigest()


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        if not path.exists():
            errors.append(f"{label} not found: {path}")
            return None
        if not path.is_file():
            errors.append(f"{label} must be a file: {path}")
            return None
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return None

    try:
        data = json.loads(text, object_pairs_hook=_json_object_no_duplicates)
    except Exception as exc:  # noqa: BLE001 - CLI should report parse errors clearly
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return data


def _load_yaml(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if yaml is None:
        errors.append(f"{label} could not be loaded: PyYAML is unavailable")
        return None

    try:
        if not path.exists():
            errors.append(f"{label} not found: {path}")
            return None
        if not path.is_file():
            errors.append(f"{label} must be a file: {path}")
            return None
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return None

    try:
        loader = _yaml_loader_no_duplicates()
        data = yaml.load(text, Loader=loader)
    except Exception as exc:  # noqa: BLE001 - fail-closed parse reporting
        errors.append(f"{label} is not valid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} must be a YAML mapping")
        return None
    return data


def _section(
    obj: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
    *,
    require_non_empty: bool = False,
) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    if require_non_empty and not value:
        errors.append(f"{label}.{key} must not be empty")
    return value


def _validate_git_sha(value: Any, label: str, errors: list[str]) -> bool:
    if not _is_git_sha(value):
        errors.append(f"{label} must be a 40-hex git sha")
        return False
    return True


def _validate_run_key(value: Any, label: str, errors: list[str]) -> bool:
    if not _is_non_empty_text(value):
        errors.append(f"{label} must be a non-empty string")
        return False
    return True


def _validate_binding_identity(binding: dict[str, Any], label: str, errors: list[str]) -> bool:
    ok = True
    ok = _validate_git_sha(binding.get("git_sha"), f"{label}.git_sha", errors) and ok
    ok = _validate_run_key(binding.get("run_key"), f"{label}.run_key", errors) and ok
    return ok


def _binding_matches(
    actual: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> bool:
    ok = True
    ok = _validate_binding_identity(expected, f"{label}.expected", errors) and ok
    ok = _validate_binding_identity(actual, f"{label}.actual", errors) and ok
    for key in REQUIRED_BINDING_KEYS:
        expected_value = expected.get(key)
        actual_value = actual.get(key)
        if actual_value != expected_value:
            errors.append(
                f"{label}.{key} mismatch: expected {expected_value!r}, got {actual_value!r}"
            )
            ok = False
    return ok


def _run_identity_matches(
    actual: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> bool:
    ok = _binding_matches(actual, expected, label, errors)
    actual_run_mode = actual.get("run_mode")
    expected_run_mode = expected.get("run_mode")
    if not _is_non_empty_text(expected_run_mode):
        errors.append(f"{label}.expected.run_mode must be a non-empty string")
        ok = False
    if not _is_non_empty_text(actual_run_mode):
        errors.append(f"{label}.actual.run_mode must be a non-empty string")
        ok = False
    if actual_run_mode != expected_run_mode:
        errors.append(
            f"{label}.run_mode mismatch: expected {expected_run_mode!r}, got {actual_run_mode!r}"
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
        if key == "policy_sha256":
            if not _is_sha256(expected_value):
                errors.append(f"{label}.expected.policy_sha256 must be a 64-hex sha256")
                ok = False
            if not _is_sha256(actual_value):
                errors.append(f"{label}.actual.policy_sha256 must be a 64-hex sha256")
                ok = False
        else:
            if not _is_non_empty_text(expected_value):
                errors.append(f"{label}.expected.policy_set must be a non-empty string")
                ok = False
            if not _is_non_empty_text(actual_value):
                errors.append(f"{label}.actual.policy_set must be a non-empty string")
                ok = False
        if actual_value != expected_value:
            errors.append(
                f"{label}.{key} mismatch: expected {expected_value!r}, got {actual_value!r}"
            )
            ok = False
    return ok


def _normalize_gate_list(value: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return set()
    if not value:
        errors.append(f"{label} must not be empty")
        return set()
    result: set[str] = set()
    for item in value:
        if not _is_non_empty_text(item):
            errors.append(f"{label} entries must be non-empty strings")
            continue
        if item in result:
            errors.append(f"{label} contains duplicate gate id {item!r}")
            continue
        result.add(item)
    return result


def _extract_release_required_gates(
    policy_obj: dict[str, Any],
    errors: list[str],
) -> set[str]:
    gates = policy_obj.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy file must contain top-level gates mapping"
        )
        return set()
  
    return _normalize_gate_list(
        gates.get("release_required"),
        "policy.gates.release_required",
        errors,
    )


def _extract_registry_gate_ids(registry_obj: dict[str, Any], errors: list[str]) -> set[str]:
    gates = registry_obj.get("gates")
    if not isinstance(gates, dict):
        errors.append("registry file must contain top-level gates mapping")
        return set()
    result: set[str] = set()
    for gate_id in gates:
        if not _is_non_empty_text(gate_id):
            errors.append("registry gate ids must be non-empty strings")
            continue
        result.add(gate_id)
    if not result:
        errors.append("registry file must declare at least one gate id")
    return result


def _validate_gate_membership(
    gate_ids: set[str],
    label: str,
    release_required_gates: set[str],
    registry_gate_ids: set[str],
    errors: list[str],
) -> bool:
    ok = True
    for gate_id in sorted(gate_ids):
        if gate_id not in release_required_gates:
            errors.append(
               f"{label} contains gate {gate_id!r} which is not declared in gates.release_required"    
            )
            ok = False
        if gate_id not in registry_gate_ids:
            errors.append(
                f"{label} contains gate {gate_id!r} which is not declared in the gate registry"
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
    manifest_sha256 = _safe_report_digest(manifest_path)
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
    registry_binding = _section(manifest, "registry_binding", errors, "manifest")
    candidate_evidence = _section(
        manifest,
        "candidate_evidence",
        errors,
        "manifest",
        require_non_empty=True,
    )
    expected_relation_bindings = _section(
        manifest,
        "expected_relation_bindings",
        errors,
        "manifest",
        require_non_empty=True,
    )
    expected_gate_materialization = _section(
        manifest,
        "expected_gate_materialization",
        errors,
        "manifest",
        require_non_empty=True,
    )

    report["run_identity"] = run_identity
    report["subject"] = subject
    report["policy_binding"] = policy_binding
    report["registry_binding"] = registry_binding
    report["verified_subjects"] = {
        "git_sha": run_identity.get("git_sha"),
        "run_key": run_identity.get("run_key"),
        "commit_sha": subject.get("commit_sha"),
    }

    run_identity_ok = _validate_binding_identity(run_identity, "manifest.run_identity", errors)
    if not _is_non_empty_text(run_identity.get("run_mode")):
        errors.append("manifest.run_identity.run_mode must be a non-empty string")
        run_identity_ok = False
    if run_identity.get("run_mode") != EXPECTED_RUN_MODE:
        errors.append(
            "manifest.run_identity.run_mode must be 'prod' for recorded "
            f"release-evidence verification (got {run_identity.get('run_mode')!r})"
        )
        run_identity_ok = False

    if not _validate_git_sha(subject.get("commit_sha"), "manifest.subject.commit_sha", errors):
        pass
    elif subject.get("commit_sha") != run_identity.get("git_sha"):
        errors.append(
            "manifest.subject.commit_sha must match manifest.run_identity.git_sha "
            f"(expected {run_identity.get('git_sha')!r}, got {subject.get('commit_sha')!r})"
        )

    if policy_binding.get("policy_set") != EXPECTED_POLICY_SET:
        errors.append(
            "manifest.policy_binding.policy_set must be 'required+release_required' "
            f"(got {policy_binding.get('policy_set')!r})"
        )
    if not _is_sha256(policy_binding.get("policy_sha256")):
        errors.append("manifest.policy_binding.policy_sha256 must be a 64-hex sha256")
    if not _is_non_empty_text(policy_binding.get("policy_path")):
        errors.append("manifest.policy_binding.policy_path must be a non-empty string")

    if not _is_non_empty_text(registry_binding.get("registry_path")):
        errors.append("manifest.registry_binding.registry_path must be a non-empty string")
    if not _is_sha256(registry_binding.get("registry_sha256")):
        errors.append("manifest.registry_binding.registry_sha256 must be a 64-hex sha256")

    release_required_gates: set[str] = set()
    registry_gate_ids: set[str] = set()

    policy_path_value = policy_binding.get("policy_path")
    if _is_non_empty_text(policy_path_value) and _is_sha256(policy_binding.get("policy_sha256")):
        policy_path = repo_root / str(policy_path_value)
        actual_policy_sha = _sha256_file(policy_path, "policy file", errors)
        if actual_policy_sha is not None:
            if actual_policy_sha != policy_binding.get("policy_sha256"):
                errors.append(
                    "policy file sha256 mismatch: expected "
                    f"{policy_binding.get('policy_sha256')!r}, got {actual_policy_sha!r}"
                )
            policy_obj = _load_yaml(policy_path, "policy file", errors)
            if policy_obj is not None:
                release_required_gates = _extract_release_required_gates(policy_obj, errors)

    registry_path_value = registry_binding.get("registry_path")
    if _is_non_empty_text(registry_path_value) and _is_sha256(registry_binding.get("registry_sha256")):
        registry_path = repo_root / str(registry_path_value)
        actual_registry_sha = _sha256_file(registry_path, "registry file", errors)
        if actual_registry_sha is not None:
            if actual_registry_sha != registry_binding.get("registry_sha256"):
                errors.append(
                    "registry file sha256 mismatch: expected "
                    f"{registry_binding.get('registry_sha256')!r}, got {actual_registry_sha!r}"
                )
            registry_obj = _load_yaml(registry_path, "registry file", errors)
            if registry_obj is not None:
                registry_gate_ids = _extract_registry_gate_ids(registry_obj, errors)

    if release_required_gates and registry_gate_ids:
        missing_registry_ids = release_required_gates - registry_gate_ids
        if missing_registry_ids:
            errors.append(
                "gates.release_required contains unknown registry gate ids: "
                f"{sorted(missing_registry_ids)!r}"
            )

    canonical_candidates: dict[
        str,
        dict[str, Any],
    ] = {}

    if not errors:
        try:
            (
                replayed_candidates,
                replayed_index,
                replay_errors,
            ) = build_canonical_candidates_for_replay(
                repo_root
            )

        except Exception as exc:  # noqa: BLE001
            errors.append(
                "canonical candidate replay could not "
                f"be completed: {exc}"
            )

        else:
            if replay_errors:
                errors.extend(
                    "canonical candidate replay failed: "
                    f"{error}"
                    for error in replay_errors
                )

            if (
                not replay_errors
                and isinstance(
                    replayed_candidates,
                    dict,
                )
                and isinstance(
                    replayed_index,
                    dict,
                )
            ):
                canonical_candidates = (
                    replayed_candidates
                )

                canonical_candidate_ids = set(
                    canonical_candidates
                )
                manifest_candidate_ids = set(
                    candidate_evidence
                )

                missing_candidates = sorted(
                    canonical_candidate_ids
                    - manifest_candidate_ids
                )
                extra_candidates = sorted(
                    manifest_candidate_ids
                    - canonical_candidate_ids
                )

                if missing_candidates:
                    errors.append(
                        "manifest candidate set is missing "
                        "canonical candidates: "
                        f"{missing_candidates!r}"
                    )

                if extra_candidates:
                    errors.append(
                        "manifest candidate set contains "
                        "non-canonical candidates: "
                        f"{extra_candidates!r}"
                    )

                if (
                    replayed_index.get(
                        "candidate_ids"
                    )
                    != sorted(
                        canonical_candidate_ids
                    )
                ):
                    errors.append(
                        "canonical candidate replay index "
                        "candidate_ids mismatch"
                    )

            elif not replay_errors:
                errors.append(
                    "canonical candidate replay did not "
                    "return candidate envelopes and index"
                )
    
    evidence_results: dict[str, Any] = {}
    verified_evidence_ids: set[str] = set()
    candidate_artifacts: dict[str, dict[str, Any]] = {}

    manifest_binding_expected = {
        "git_sha": run_identity.get("git_sha"),
        "run_key": run_identity.get("run_key"),
    }

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
        expected_required_gates = _normalize_gate_list(
            candidate.get("required_for_gates"),
            f"manifest.candidate_evidence.{evidence_id}.required_for_gates",
            candidate_errors,
        )
        provenance_expectations = _section(
            candidate,
            "provenance_expectations",
            candidate_errors,
            f"manifest.candidate_evidence.{evidence_id}",
        )
        trusted_required_value = provenance_expectations.get("trusted_producer_required")
        trusted_required = trusted_required_value is True
        if trusted_required_value is not True:
            candidate_errors.append(
                "manifest.candidate_evidence."
                f"{evidence_id}.provenance_expectations.trusted_producer_required must be literal true"
            )

        if candidate.get("verification_required") is not True:
            candidate_errors.append(
                "candidate evidence verification_required must be literal true"
            )
        if not _is_sha256(expected_sha256):
            candidate_errors.append("candidate evidence expected_sha256 must be a 64-hex sha256")
        if not _is_non_empty_text(expected_schema_version):
            candidate_errors.append("candidate evidence schema_version must be a non-empty string")

        if _binding_matches(
            expected_binding,
            manifest_binding_expected,
            f"manifest.candidate_evidence.{evidence_id}.subject_binding",
            candidate_errors,
        ) and subject.get("commit_sha") == run_identity.get("git_sha"):
            pass

        if release_required_gates and registry_gate_ids:
            _validate_gate_membership(
                expected_required_gates,
                f"manifest.candidate_evidence.{evidence_id}.required_for_gates",
                release_required_gates,
                registry_gate_ids,
                candidate_errors,
            )

        if not isinstance(path_value, str) or not path_value.strip():
            candidate_errors.append("candidate evidence path must be a non-empty string")
            continue

        artifact_path = repo_root / path_value
        if not artifact_path.exists():
            candidate_errors.append(f"candidate artifact not found: {artifact_path}")
            continue
        if not artifact_path.is_file():
            candidate_errors.append(f"candidate artifact must be a file: {artifact_path}")
            continue

        actual_sha256 = _sha256_file(artifact_path, f"candidate artifact {evidence_id}", candidate_errors)
        result["actual_sha256"] = actual_sha256
        if actual_sha256 is not None and actual_sha256 == expected_sha256:
            result["digest_match"] = True
        elif actual_sha256 is not None:
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
                "candidate artifact schema_version mismatch: expected "
                f"{expected_schema_version!r}, got {artifact.get('schema_version')!r}"
            )

        artifact_run_identity = _section(
            artifact,
            "run_identity",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        if _run_identity_matches(
            artifact_run_identity,
            run_identity,
            f"candidate artifact {evidence_id}.run_identity",
            candidate_errors,
        ):
            result["run_identity_match"] = True

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
        subject_run_ok = _binding_matches(
            artifact_subject_binding,
            manifest_binding_expected,
            f"candidate artifact {evidence_id}.subject_binding_to_run_identity",
            candidate_errors,
        )
        commit_sha = subject.get("commit_sha")
        if _is_git_sha(commit_sha) and artifact_subject_binding.get("git_sha") != commit_sha:
            candidate_errors.append(
                f"candidate artifact {evidence_id}.subject_binding.git_sha must also match manifest.subject.commit_sha {commit_sha!r}"
            )
            subject_expected_ok = False
        if subject_expected_ok and subject_run_ok:
            result["subject_binding_match"] = True

        artifact_policy_binding = _section(
            artifact,
            "policy_binding",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        if _policy_binding_matches(
            artifact_policy_binding,
            {
                "policy_set": policy_binding.get("policy_set"),
                "policy_sha256": policy_binding.get("policy_sha256"),
            },
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
        if (
            trusted_required
            and artifact_provenance.get(
                "trusted_producer"
            )
            is not True
        ):
            candidate_errors.append(
                f"candidate artifact {evidence_id}."
                "provenance.trusted_producer "
                "must be true"
            )

        canonical_artifact = (
            canonical_candidates.get(
                evidence_id
            )
        )

        if not isinstance(
            canonical_artifact,
            dict,
        ):
            candidate_errors.append(
                f"candidate artifact {evidence_id} "
                "is missing from canonical "
                "candidate replay"
            )

        else:
            supplied_for_comparison = (
                _candidate_for_replay_comparison(
                    artifact,
                    (
                        "candidate artifact "
                        f"{evidence_id}"
                    ),
                    candidate_errors,
                )
            )

            replayed_for_comparison = (
                _candidate_for_replay_comparison(
                    canonical_artifact,
                    (
                        "canonical candidate replay "
                        f"{evidence_id}"
                    ),
                    candidate_errors,
                )
            )

            if (
                supplied_for_comparison
                is not None
                and replayed_for_comparison
                is not None
            ):
                if (
                    supplied_for_comparison
                    != replayed_for_comparison
                ):
                    candidate_errors.append(
                        f"candidate artifact "
                        f"{evidence_id} does not "
                        "match canonical candidate "
                        "replay"
                    )

                elif trusted_required:
                    result[
                        "trusted_producer_verified"
                    ] = True
      
        raw_binding = _section(
            artifact,
            "raw_evidence_binding",
            candidate_errors,
            f"candidate artifact {evidence_id}",
        )
        raw_path_value = raw_binding.get("path")
        raw_sha_value = raw_binding.get("sha256")
        if not isinstance(raw_path_value, str) or not raw_path_value.strip():
            candidate_errors.append(
                f"candidate artifact {evidence_id}.raw_evidence_binding.path must be a non-empty string"
            )
        elif not _is_sha256(raw_sha_value):
            candidate_errors.append(
                f"candidate artifact {evidence_id}.raw_evidence_binding.sha256 must be a 64-hex sha256"
            )
        else:
            raw_path = repo_root / raw_path_value
            if not raw_path.exists():
                candidate_errors.append(f"raw evidence not found: {raw_path}")
            elif not raw_path.is_file():
                candidate_errors.append(f"raw evidence must be a file: {raw_path}")
            else:
                actual_raw_sha = _sha256_file(
                    raw_path,
                    f"raw evidence for {evidence_id}",
                    candidate_errors,
                )
                if actual_raw_sha is not None and actual_raw_sha == raw_sha_value:
                    result["raw_evidence_verified"] = True
                elif actual_raw_sha is not None:
                    candidate_errors.append(
                        f"raw evidence sha256 mismatch for {evidence_id}: expected {raw_sha_value!r}, got {actual_raw_sha!r}"
                    )

        artifact_required_gates = _normalize_gate_list(
            artifact.get("required_for_gates"),
            f"candidate artifact {evidence_id}.required_for_gates",
            candidate_errors,
        )
        if release_required_gates and registry_gate_ids:
            _validate_gate_membership(
                artifact_required_gates,
                f"candidate artifact {evidence_id}.required_for_gates",
                release_required_gates,
                registry_gate_ids,
                candidate_errors,
            )
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

        if binding_type not in {"artifact_to_subject", "artifact_to_gate"}:
            relation_errors.append(f"unsupported binding_type: {binding_type!r}")
            continue
        if not _is_non_empty_text(source_evidence_id):
            relation_errors.append("relation binding source_evidence_id must be a non-empty string")
            continue
        if not _is_non_empty_text(expected_gate_id):
            relation_errors.append("relation binding expected_gate_id must be a non-empty string")
            continue
        if not _is_non_empty_text(target):
            relation_errors.append("relation binding target must be a non-empty string")
            continue

        if release_required_gates and registry_gate_ids:
            _validate_gate_membership(
                {str(expected_gate_id)},
                f"relation binding {relation_id}.expected_gate_id",
                release_required_gates,
                registry_gate_ids,
                relation_errors,
            )

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
        artifact_required_gates = _normalize_gate_list(
            artifact.get("required_for_gates"),
            f"candidate artifact {source_evidence_id}.required_for_gates",
            relation_errors,
        )
        artifact_subject_binding = artifact.get("subject_binding")
        if not isinstance(artifact_subject_binding, dict):
            relation_errors.append(
                f"candidate artifact {source_evidence_id}.subject_binding must be an object"
            )
            continue

        if binding_type == "artifact_to_subject":
            if not _binding_matches(
                artifact_subject_binding,
                manifest_binding_expected,
                f"relation binding {relation_id}.subject_binding_to_run_identity",
                relation_errors,
            ):
                pass
            if target != "subject.commit_sha":
                relation_errors.append(
                    f"artifact_to_subject relation target must be 'subject.commit_sha' (got {target!r})"
                )
        else:
            if expected_gate_id not in artifact_required_gates:
                relation_errors.append(
                    f"artifact_to_gate relation requires {source_evidence_id!r} to target gate {expected_gate_id!r}"
                )
            if target != f"gate.{expected_gate_id}":
                relation_errors.append(
                    f"artifact_to_gate relation target must be 'gate.{expected_gate_id}' (got {target!r})"
                )

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

        if release_required_gates and registry_gate_ids:
            _validate_gate_membership(
                {gate_id},
                f"manifest.expected_gate_materialization[{gate_id!r}]",
                release_required_gates,
                registry_gate_ids,
                gate_errors,
            )

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
        if not isinstance(candidate_ids, list) or not candidate_ids:
            gate_errors.append(f"gate {gate_id} candidate_evidence_ids must be a non-empty array")
            candidate_ids = []
        if not isinstance(relation_ids, list) or not relation_ids:
            gate_errors.append(f"gate {gate_id} relation_binding_ids must be a non-empty array")
            relation_ids = []

        for evidence_id in candidate_ids:
            if evidence_id not in verified_evidence_ids:
                gate_errors.append(
                    f"gate {gate_id} candidate evidence not verified: {evidence_id!r}"
                )

        gate_target_relation_sources: set[str] = set()
        for relation_id in relation_ids:
            relation_result = relation_binding_results.get(relation_id)
            relation = expected_relation_bindings.get(relation_id)
            if relation_id not in satisfied_relation_ids:
                gate_errors.append(
                    f"gate {gate_id} relation binding not satisfied: {relation_id!r}"
                )
                continue
            if not isinstance(relation, dict):
                gate_errors.append(
                    f"gate {gate_id} relation binding definition missing: {relation_id!r}"
                )
                continue

            relation_source = relation.get("source_evidence_id")
            relation_binding_type = relation.get("binding_type")
            relation_expected_gate = relation.get("expected_gate_id")
            relation_target = relation.get("target")

            if relation_source not in candidate_ids:
                gate_errors.append(
                    f"gate {gate_id} relation binding source must be listed candidate evidence: {relation_id!r}"
                )

            if relation_binding_type == "artifact_to_subject":
                if relation_target != "subject.commit_sha":
                    gate_errors.append(
                        f"gate {gate_id} subject relation target must be 'subject.commit_sha' (got {relation_target!r})"
                    )
            elif relation_binding_type == "artifact_to_gate":
                if relation_expected_gate != gate_id:
                    gate_errors.append(
                        f"gate {gate_id} relation {relation_id!r} must target expected_gate_id {gate_id!r}"
                    )
                if relation_target != f"gate.{gate_id}":
                    gate_errors.append(
                        f"gate {gate_id} relation {relation_id!r} must target 'gate.{gate_id}'"
                    )
                if relation_expected_gate == gate_id and relation_target == f"gate.{gate_id}":
                    gate_target_relation_sources.add(str(relation_source))
            else:
                gate_errors.append(
                    f"gate {gate_id} has unsupported relation binding type in {relation_id!r}: {relation_binding_type!r}"
                )

        if not gate_target_relation_sources:
            gate_errors.append(
                f"gate {gate_id} must include at least one satisfied artifact_to_gate relation targeting gate.{gate_id}"
            )
        for evidence_id in candidate_ids:
            if evidence_id not in gate_target_relation_sources:
                gate_errors.append(
                    f"gate {gate_id} is missing a gate-targeted relation for candidate evidence {evidence_id!r}"
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
