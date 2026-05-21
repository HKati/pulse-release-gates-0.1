#!/usr/bin/env python3
"""Build field_point_authority_map_v0 diagnostic artifacts.

This builder does not create release authority.

It materializes a non-normative field-point authority map from structured input.
Each PULSE field point is classified by role, authority status, and relation to
the normative materialization path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "field_point_authority_map_v0"
AUTHORITY_STATUS = "diagnostic_non_normative"
INVARIANT = (
    "field_points_must_declare_role_and_authority_status_before_interpretation"
)

SURFACE_TYPES = {
    "recorded_release_evidence",
    "status_artifact",
    "declared_policy",
    "materialized_gate_set",
    "ci_enforcement",
    "ci_decision",
    "quality_ledger",
    "release_authority_manifest",
    "audit_bundle",
    "dashboard",
    "pages",
    "badge",
    "doi_record",
    "citation_metadata",
    "readme",
    "about",
    "diagnostic_contract",
    "hpc_evidence_bundle",
    "evidence_fold_in_admissibility",
    "pulse_pd_artifact",
    "recognition_surface",
    "recognition_surface_drift",
    "optional_analysis_surface",
    "other",
}

AUTHORITY_STATUSES = {
    "normative_input",
    "normative_enforcement",
    "normative_decision",
    "diagnostic_non_normative",
    "audit_non_normative",
    "publication_non_normative",
    "recognition_non_normative",
    "optional_analysis_non_normative",
    "proposed_non_normative",
}

NORMATIVE_STATUSES = {
    "normative_input",
    "normative_enforcement",
    "normative_decision",
}

RELATIONS = {
    "normative_path_member",
    "candidate_evidence_surface",
    "diagnostic_observer",
    "audit_reconstruction",
    "publication_reader",
    "recognition_surface",
    "optional_analysis",
    "future_proposed",
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


def _load_json_object(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _enum(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return default


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_string_list(name: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")

    if not value:
        raise ValueError(f"{name} must not be empty")

    out: list[str] = []

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name}[{index}] must be a non-empty string")
        out.append(item)

    return out


def _require_field_points(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("field_points must be an array")

    if not value:
        raise ValueError("field_points must not be empty")

    out: list[dict[str, Any]] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"field_points[{index}] must be an object")
        out.append(item)

    return out


def _policy_route(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    policy_path = value.get("policy_path")
    gate_id = value.get("gate_id")

    if not isinstance(policy_path, str) or not policy_path.strip():
        return None
    if not isinstance(gate_id, str) or not gate_id.strip():
        return None

    out = dict(value)
    out["policy_path"] = policy_path
    out["gate_id"] = gate_id
    return out


def _default_authority_status(
    surface_type: str,
    *,
    in_normative_path: bool,
) -> str:
    if in_normative_path:
        if surface_type == "ci_enforcement":
            return "normative_enforcement"
        if surface_type == "ci_decision":
            return "normative_decision"
        return "normative_input"

    if surface_type in RECOGNITION_SURFACES:
        return "recognition_non_normative"
    if surface_type in PUBLICATION_SURFACES:
        return "publication_non_normative"
    if surface_type in AUDIT_SURFACES:
        return "audit_non_normative"
    if surface_type in DIAGNOSTIC_SURFACES:
        if surface_type == "optional_analysis_surface" or surface_type == "pulse_pd_artifact":
            return "optional_analysis_non_normative"
        return "diagnostic_non_normative"

    return "diagnostic_non_normative"


def _default_relation(
    surface_type: str,
    *,
    in_normative_path: bool,
) -> str:
    if in_normative_path:
        return "normative_path_member"

    if surface_type in RECOGNITION_SURFACES:
        return "recognition_surface"
    if surface_type in PUBLICATION_SURFACES:
        return "publication_reader"
    if surface_type in AUDIT_SURFACES:
        return "audit_reconstruction"
    if surface_type in {"hpc_evidence_bundle"}:
        return "candidate_evidence_surface"
    if surface_type in {"pulse_pd_artifact", "optional_analysis_surface"}:
        return "optional_analysis"
    if surface_type in DIAGNOSTIC_SURFACES:
        return "diagnostic_observer"

    return "diagnostic_observer"


def _normalize_field_point(
    point: dict[str, Any],
    *,
    normative_ids: set[str],
) -> dict[str, Any]:
    field_point_id = _require_string(
        "field_point_id",
        point.get("field_point_id"),
    )
    path_or_label = _require_string(
        f"{field_point_id}.path_or_label",
        point.get("path_or_label"),
    )
    field_role = _require_string(
        f"{field_point_id}.field_role",
        point.get("field_role"),
    )

    surface_type = _enum(
        point.get("surface_type"),
        SURFACE_TYPES,
        "other",
    )

    in_normative_path = field_point_id in normative_ids

    authority_status = _enum(
        point.get("authority_status"),
        AUTHORITY_STATUSES,
        _default_authority_status(
            surface_type,
            in_normative_path=in_normative_path,
        ),
    )

    relation = _enum(
        point.get("relation_to_normative_path"),
        RELATIONS,
        _default_relation(
            surface_type,
            in_normative_path=in_normative_path,
        ),
    )

    if "can_affect_release_decision" in point:
        can_affect = point.get("can_affect_release_decision") is True
    else:
        can_affect = in_normative_path

    notes = point.get("notes")
    policy_route = _policy_route(point.get("policy_route"))

    out: dict[str, Any] = {
        "field_point_id": field_point_id,
        "path_or_label": path_or_label,
        "surface_type": surface_type,
        "authority_status": authority_status,
        "field_role": field_role,
        "relation_to_normative_path": relation,
        "can_affect_release_decision": can_affect,
        "creates_release_authority": False,
        "policy_route": policy_route,
    }

    if isinstance(notes, str) and notes:
        out["notes"] = notes

    return out


def _has_policy_route(field_point: dict[str, Any]) -> bool:
    return _policy_route(field_point.get("policy_route")) is not None


def _semantic_errors(
    *,
    normative_materialization_path: list[str],
    field_points: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []

    path_ids = set(normative_materialization_path)
    by_id: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    for point in field_points:
        field_point_id = point["field_point_id"]
        if field_point_id in seen:
            errors.append(f"duplicate field_point_id: {field_point_id}")
            continue
        seen.add(field_point_id)
        by_id[field_point_id] = point

    for field_point_id in normative_materialization_path:
        point = by_id.get(field_point_id)
        if point is None:
            errors.append(
                f"normative_materialization_path references unknown field point: {field_point_id}"
            )
            continue

        if point["authority_status"] not in NORMATIVE_STATUSES:
            errors.append(
                f"{field_point_id}: normative path member must have normative authority status"
            )
        if point["relation_to_normative_path"] != "normative_path_member":
            errors.append(
                f"{field_point_id}: normative path member must declare relation_to_normative_path=normative_path_member"
            )
        if point["can_affect_release_decision"] is not True:
            errors.append(
                f"{field_point_id}: normative path member must set can_affect_release_decision=true"
            )

    for point in field_points:
        field_point_id = point["field_point_id"]
        surface_type = point["surface_type"]
        authority_status = point["authority_status"]
        relation = point["relation_to_normative_path"]
        can_affect = point["can_affect_release_decision"]
        in_normative_path = field_point_id in path_ids

        if point["creates_release_authority"] is not False:
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
            if authority_status in NORMATIVE_STATUSES:
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

    return errors


def build(input_obj: dict[str, Any]) -> dict[str, Any]:
    normative_materialization_path = _require_string_list(
        "normative_materialization_path",
        input_obj.get("normative_materialization_path"),
    )
    raw_field_points = _require_field_points(input_obj.get("field_points"))

    normative_ids = set(normative_materialization_path)

    field_points = [
        _normalize_field_point(point, normative_ids=normative_ids)
        for point in raw_field_points
    ]

    errors = _semantic_errors(
        normative_materialization_path=normative_materialization_path,
        field_points=field_points,
    )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "authority_status": AUTHORITY_STATUS,
        "creates_release_authority": False,
        "invariant": INVARIANT,
        "normative_materialization_path": normative_materialization_path,
        "field_points": field_points,
        "result": "invalid" if errors else "valid",
    }

    notes = input_obj.get("notes")
    if isinstance(notes, str) and notes:
        out["notes"] = notes

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a field_point_authority_map_v0 diagnostic artifact."
    )
    parser.add_argument("--input", required=True, help="Input field-point bundle JSON.")
    parser.add_argument("--out", required=True, help="Output diagnostic JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        input_obj = _load_json_object(Path(args.input))
        output_obj = build(input_obj)
        _write_json(Path(args.out), output_obj)
    except Exception as exc:
        print(f"::error::failed to build field_point_authority_map_v0: {exc}")
        return 1

    print(f"OK: wrote field_point_authority_map_v0 artifact: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
