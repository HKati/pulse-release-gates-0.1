#!/usr/bin/env python3
"""Contract checker for evidence_fold_in_admissibility_v0 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "evidence_fold_in_admissibility_v0.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _is_real_artifact_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value != "_missing_source_artifact_path"
    )


def _schema_errors(instance: dict[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _expected_result(admissibilities: list[str]) -> str:
    if all(item == "admissible_for_fold_in" for item in admissibilities):
        return "admissible"

    if all(item == "advisory_only" for item in admissibilities):
        return "advisory_only"

    if all(item == "rejected" for item in admissibilities):
        return "rejected"

    return "mixed"


def _semantic_errors(instance: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if instance.get("authority_status") != "diagnostic_non_normative":
        errors.append("authority_status must be diagnostic_non_normative")

    if instance.get("creates_release_authority") is not False:
        errors.append("creates_release_authority must be false")

    candidates = instance.get("candidates")
    if not isinstance(candidates, list):
        return errors

    admissibilities: list[str] = []

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidates[{index}] must be an object")
            continue

        candidate_id = candidate.get("candidate_id", f"index-{index}")
        admissibility = candidate.get("admissibility")
        admissibilities.append(str(admissibility))

        source_surface_type = candidate.get("source_surface_type")
        source_artifact = candidate.get("source_artifact")

        artifact_path = None
        sha256 = None
        if isinstance(source_artifact, dict):
            artifact_path = source_artifact.get("path")
            sha256 = source_artifact.get("sha256")

        artifact_path_valid = _is_real_artifact_path(artifact_path)

        schema_valid = candidate.get("schema_valid")
        digest_valid = candidate.get("digest_valid")
        verification_status = candidate.get("verification_status")
        folded_requested = candidate.get("folded_into_status_requested")
        policy_route = candidate.get("policy_route")

        if source_surface_type == "recognition_surface":
            if admissibility == "admissible_for_fold_in":
                errors.append(
                    f"{candidate_id}: recognition surfaces are not admissible for fold-in by themselves"
                )
            if folded_requested is True:
                errors.append(
                    f"{candidate_id}: recognition surfaces must not request status fold-in"
                )

        if folded_requested is True:
            if not isinstance(policy_route, dict):
                errors.append(
                    f"{candidate_id}: folded evidence requires policy_route"
                )
            else:
                if not policy_route.get("policy_path"):
                    errors.append(
                        f"{candidate_id}: policy_route.policy_path is required"
                    )
                if not policy_route.get("gate_id"):
                    errors.append(
                        f"{candidate_id}: policy_route.gate_id is required"
                    )

        if admissibility == "admissible_for_fold_in":
            if folded_requested is not True:
                errors.append(
                    f"{candidate_id}: admissible evidence must request status fold-in"
                )
            if not artifact_path_valid:
                errors.append(
                    f"{candidate_id}: admissible evidence requires valid source_artifact.path"
                )
            if not _is_sha256(sha256):
                errors.append(
                    f"{candidate_id}: admissible evidence requires valid source_artifact.sha256"
                )
            if schema_valid is not True:
                errors.append(
                    f"{candidate_id}: admissible evidence requires schema_valid=true"
                )
            if digest_valid is not True:
                errors.append(
                    f"{candidate_id}: admissible evidence requires digest_valid=true"
                )
            if verification_status != "verified":
                errors.append(
                    f"{candidate_id}: admissible evidence requires verification_status=verified"
                )
            if not isinstance(policy_route, dict):
                errors.append(
                    f"{candidate_id}: admissible evidence requires policy_route"
                )

        if admissibility == "advisory_only" and folded_requested is True:
            errors.append(
                f"{candidate_id}: advisory-only evidence must not request status fold-in"
            )

        if admissibility == "rejected" and folded_requested is True:
            errors.append(
                f"{candidate_id}: rejected evidence must not request status fold-in"
            )

    if admissibilities:
        expected = _expected_result(admissibilities)
        if instance.get("result") != expected:
            errors.append(
                f"result must be {expected!r} for candidate admissibility mix, "
                f"found {instance.get('result')!r}"
            )

    return errors


def check(path: Path) -> tuple[bool, list[str]]:
    instance = _load_json(path)
    errors = _schema_errors(instance)
    errors.extend(_semantic_errors(instance))
    return errors == [], errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an evidence_fold_in_admissibility_v0 artifact."
    )
    parser.add_argument("--in", dest="input_path", required=True)
    args = parser.parse_args()

    try:
        ok, errors = check(Path(args.input_path))
    except Exception as exc:
        print(f"::error::failed to check evidence_fold_in_admissibility_v0: {exc}")
        return 1

    if not ok:
        print("::error::evidence_fold_in_admissibility_v0 contract failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: evidence_fold_in_admissibility_v0 contract valid: {args.input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
