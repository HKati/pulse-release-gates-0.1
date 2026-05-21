#!/usr/bin/env python3
"""Contract checker for field_point_authority_map_v0 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "field_point_authority_map_v0.schema.json"


NORMATIVE_STATUSES = {
    "normative_input",
    "normative_enforcement",
    "normative_decision",
}

RECOGNITION_SURFACES = {
    "recognition_surface",
    "recognition_surface_drift",
    "readme",
    "about",
    "doi_record",
    "citation_metadata",
    "badge",
}

PUBLICATION_SURFACES = {
    "quality_ledger",
    "dashboard",
    "pages",
    "doi_record",
    "citation_metadata",
    "badge",
}

AUDIT_SURFACES = {
    "release_authority_manifest",
    "audit_bundle",
}

DIAGNOSTIC_SURFACES = {
    "diagnostic_contract",
    "hpc_evidence_bundle",
    "evidence_fold_in_admissibility",
    "pulse_pd_artifact",
    "recognition_surface_drift",
    "optional_analysis_surface",
}


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


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


def _has_policy_route(field_point: dict[str, Any]) -> bool:
    route = field_point.get("policy_route")

    if not isinstance(route, dict):
        return False

    policy_path = route.get("policy_path")
    gate_id = route.get("gate_id")

    return (
        isinstance(policy_path, str)
        and bool(policy_path.strip())
        and isinstance(gate_id, str)
        and bool(gate_id.strip())
    )


def _semantic_errors(instance: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if instance.get("authority_status") != "diagnostic_non_normative":
        errors.append("authority_status must be diagnostic_non_normative")

    if instance.get("creates_release_authority") is not False:
        errors.append("creates_release_authority must be false")

    field_points = instance.get("field_points")
    if not isinstance(field_points, list):
        return errors

    path_ids = instance.get("normative_materialization_path")
    if not isinstance(path_ids, list):
        return errors

    by_id: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    for index, point in enumerate(field_points):
        if not isinstance(point, dict):
            errors.append(f"field_points[{index}] must be an object")
            continue

        field_point_id = point.get("field_point_id")
        if not isinstance(field_point_id, str) or not field_point_id:
            errors.append(f"field_points[{index}].field_point_id must be a non-empty string")
            continue

        if field_point_id in seen:
            errors.append(f"duplicate field_point_id: {field_point_id}")
            continue

        seen.add(field_point_id)
        by_id[field_point_id] = point

    for field_point_id in path_ids:
        if not isinstance(field_point_id, str):
            errors.append("normative_materialization_path entries must be strings")
            continue

        point = by_id.get(field_point_id)
        if point is None:
            errors.append(
                f"normative_materialization_path references unknown field point: {field_point_id}"
            )
            continue

        authority_status = point.get("authority_status")
        relation = point.get("relation_to_normative_path")
        can_affect = point.get("can_affect_release_decision")

        if authority_status not in NORMATIVE_STATUSES:
            errors.append(
                f"{field_point_id}: normative path member must have normative authority status"
            )

        if relation != "normative_path_member":
            errors.append(
                f"{field_point_id}: normative path member must declare relation_to_normative_path=normative_path_member"
            )

        if can_affect is not True:
            errors.append(
                f"{field_point_id}: normative path member must set can_affect_release_decision=true"
            )

    for point in field_points:
        if not isinstance(point, dict):
            continue

        field_point_id = point.get("field_point_id", "<unknown>")
        surface_type = point.get("surface_type")
        authority_status = point.get("authority_status")
        relation = point.get("relation_to_normative_path")
        can_affect = point.get("can_affect_release_decision")
        creates_release_authority = point.get("creates_release_authority")
        in_normative_path = field_point_id in path_ids

        if creates_release_authority is not False:
            errors.append(f"{field_point_id}: creates_release_authority must be false")

        if authority_status in NORMATIVE_STATUSES and not in_normative_path:
            errors.append(
                f"{field_point_id}: normative authority status is only allowed for normative path members"
            )

        if relation == "normative_path_member" and not in_normative_path:
            errors.append(
                f"{field_point_id}: relation_to_normative_path=normative_path_member requires inclusion in normative_materialization_path"
            )

        if surface_type in RECOGNITION_SURFACES:
            if authority_status == "normative_input" or authority_status == "normative_enforcement" or authority_status == "normative_decision":
                errors.append(
                    f"{field_point_id}: recognition surfaces must not declare normative authority"
                )
            if can_affect is True:
                errors.append(
                    f"{field_point_id}: recognition surfaces must not affect release decisions directly"
                )

        if surface_type in PUBLICATION_SURFACES:
            if authority_status in NORMATIVE_STATUSES:
                errors.append(
                    f"{field_point_id}: publication surfaces must not declare normative authority"
                )
            if can_affect is True:
                errors.append(
                    f"{field_point_id}: publication surfaces must not affect release decisions directly"
                )

        if surface_type in AUDIT_SURFACES:
            if authority_status in NORMATIVE_STATUSES:
                errors.append(
                    f"{field_point_id}: audit/reconstruction surfaces must not declare normative authority"
                )
            if can_affect is True:
                errors.append(
                    f"{field_point_id}: audit/reconstruction surfaces must not affect release decisions directly"
                )

        if surface_type in DIAGNOSTIC_SURFACES:
            if authority_status in NORMATIVE_STATUSES:
                errors.append(
                    f"{field_point_id}: diagnostic surfaces must not declare normative authority"
                )

            if can_affect is True and not _has_policy_route(point):
                errors.append(
                    f"{field_point_id}: diagnostic surfaces that affect release decisions require explicit policy_route"
                )

        if can_affect is True and not in_normative_path and not _has_policy_route(point):
            errors.append(
                f"{field_point_id}: non-normative field point cannot affect release decisions without policy_route"
            )

    expected_result = "invalid" if errors else "valid"
    if instance.get("result") != expected_result:
        errors.append(
            f"result must be {expected_result!r} for this field-point map, found {instance.get('result')!r}"
        )

    return errors


def check(path: Path) -> tuple[bool, list[str]]:
    instance = _load_json(path)
    errors = _schema_errors(instance)
    errors.extend(_semantic_errors(instance))
    return errors == [], errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a field_point_authority_map_v0 artifact."
    )
    parser.add_argument("--in", dest="input_path", required=True)
    args = parser.parse_args()

    try:
        ok, errors = check(Path(args.input_path))
    except Exception as exc:
        print(f"::error::failed to check field_point_authority_map_v0: {exc}")
        return 1

    if not ok:
        print("::error::field_point_authority_map_v0 contract failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: field_point_authority_map_v0 contract valid: {args.input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
