#!/usr/bin/env python3
"""Build evidence_fold_in_admissibility_v0 diagnostic artifacts.

This builder does not fold evidence into status.json.

It materializes a non-normative admissibility artifact from structured candidate
input. The output states whether each candidate is admissible for future fold-in,
advisory-only, or rejected.

The produced artifact does not create release authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "evidence_fold_in_admissibility_v0"
AUTHORITY_STATUS = "diagnostic_non_normative"
INVARIANT = (
    "non_normative_field_points_must_not_enter_recorded_release_evidence_"
    "without_mechanical_admissibility"
)

SOURCE_SURFACE_TYPES = {
    "external_detector_summary",
    "hpc_evidence_bundle",
    "pulse_pd_artifact",
    "recognition_surface",
    "recognition_surface_drift",
    "ra1_verifier_report",
    "audit_bundle",
    "publication_snapshot",
    "diagnostic_overlay",
    "other",
}

SOURCE_AUTHORITY_STATUSES = {
    "non_normative",
    "diagnostic_non_normative",
    "audit_non_normative",
    "publication_non_normative",
    "recognition_non_normative",
}

EVIDENCE_ROLES = {
    "detector_evidence",
    "hpc_evidence",
    "analysis_evidence",
    "recognition_diagnostic",
    "audit_evidence",
    "publication_evidence",
    "other",
}

VERIFICATION_STATUSES = {
    "verified",
    "unverified",
    "failed",
    "not_applicable",
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


def _require_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("candidates must be an array")

    if not value:
        raise ValueError("candidates must not be empty")

    out: list[dict[str, Any]] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"candidates[{index}] must be an object")
        out.append(item)

    return out


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _enum(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return default


def _source_authority_default(source_surface_type: str) -> str:
    if source_surface_type == "recognition_surface":
        return "recognition_non_normative"
    if source_surface_type in {"audit_bundle", "ra1_verifier_report"}:
        return "audit_non_normative"
    if source_surface_type == "publication_snapshot":
        return "publication_non_normative"
    if source_surface_type in {
        "hpc_evidence_bundle",
        "pulse_pd_artifact",
        "recognition_surface_drift",
        "diagnostic_overlay",
        "external_detector_summary",
    }:
        return "diagnostic_non_normative"
    return "non_normative"


def _evidence_role_default(source_surface_type: str) -> str:
    if source_surface_type == "external_detector_summary":
        return "detector_evidence"
    if source_surface_type == "hpc_evidence_bundle":
        return "hpc_evidence"
    if source_surface_type == "pulse_pd_artifact":
        return "analysis_evidence"
    if source_surface_type in {"recognition_surface", "recognition_surface_drift"}:
        return "recognition_diagnostic"
    if source_surface_type in {"audit_bundle", "ra1_verifier_report"}:
        return "audit_evidence"
    if source_surface_type == "publication_snapshot":
        return "publication_evidence"
    return "other"


def _source_artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    raw = candidate.get("source_artifact")
    if isinstance(raw, dict):
        path = raw.get("path")
        sha256 = raw.get("sha256")
    else:
        path = candidate.get("path")
        sha256 = candidate.get("sha256")

    if not isinstance(path, str) or not path:
        path = "_missing_source_artifact_path"

    if not _is_sha256(sha256):
        sha256 = None

    return {
        "path": path,
        "sha256": sha256,
    }


def _policy_route(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    policy_path = value.get("policy_path")
    gate_id = value.get("gate_id")

    if not isinstance(policy_path, str) or not policy_path:
        return None
    if not isinstance(gate_id, str) or not gate_id:
        return None

    out = dict(value)
    out["policy_path"] = policy_path
    out["gate_id"] = gate_id
    return out


def _wants_fold_in(candidate: dict[str, Any]) -> bool:
    for key in (
        "folded_into_status_requested",
        "fold_into_status_requested",
        "request_status_fold_in",
    ):
        if candidate.get(key) is True:
            return True
    return False


def _candidate_result(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        candidate_id = "candidate"

    source_surface_type = _enum(
        candidate.get("source_surface_type"),
        SOURCE_SURFACE_TYPES,
        "other",
    )

    source_authority_status = _enum(
        candidate.get("source_authority_status"),
        SOURCE_AUTHORITY_STATUSES,
        _source_authority_default(source_surface_type),
    )

    evidence_role = _enum(
        candidate.get("evidence_role"),
        EVIDENCE_ROLES,
        _evidence_role_default(source_surface_type),
    )

    source_artifact = _source_artifact(candidate)
    sha256 = source_artifact["sha256"]

    schema_path = candidate.get("schema_path")
    if not isinstance(schema_path, str):
        schema_path = None

    schema_valid = candidate.get("schema_valid") is True
    digest_valid = candidate.get("digest_valid") is True and _is_sha256(sha256)

    verification_status = _enum(
        candidate.get("verification_status"),
        VERIFICATION_STATUSES,
        "unverified",
    )

    fold_requested = _wants_fold_in(candidate)
    policy_route = _policy_route(candidate.get("policy_route"))

    missing: list[str] = []

    if not _is_sha256(sha256):
        missing.append("valid source_artifact.sha256")
    if not schema_valid:
        missing.append("schema_valid=true")
    if not digest_valid:
        missing.append("digest_valid=true")
    if verification_status != "verified":
        missing.append("verification_status=verified")
    if policy_route is None:
        missing.append("policy_route")

    if source_surface_type == "recognition_surface":
        admissibility = "rejected"
        folded_into_status_requested = False
        reason = (
            "Recognition surfaces are not admissible for release-evidence "
            "fold-in by themselves."
        )
    elif fold_requested and not missing:
        admissibility = "admissible_for_fold_in"
        folded_into_status_requested = True
        reason = (
            "Digest-backed, schema-valid, verified evidence with explicit "
            "policy route."
        )
    elif fold_requested:
        admissibility = "rejected"
        folded_into_status_requested = False
        reason = (
            "Fold-in requested but mechanical admissibility is incomplete: "
            + ", ".join(missing)
            + "."
        )
    elif _is_sha256(sha256) or digest_valid or schema_valid or verification_status in {
        "verified",
        "not_applicable",
    }:
        admissibility = "advisory_only"
        folded_into_status_requested = False
        reason = (
            "Candidate remains advisory-only because status fold-in was not "
            "requested with a complete policy route."
        )
    else:
        admissibility = "rejected"
        folded_into_status_requested = False
        reason = "Candidate lacks sufficient mechanical evidence for admissibility."

    return {
        "candidate_id": candidate_id,
        "source_surface_type": source_surface_type,
        "source_authority_status": source_authority_status,
        "evidence_role": evidence_role,
        "source_artifact": source_artifact,
        "schema_path": schema_path,
        "schema_valid": schema_valid,
        "digest_valid": digest_valid,
        "verification_status": verification_status,
        "folded_into_status_requested": folded_into_status_requested,
        "policy_route": policy_route,
        "admissibility": admissibility,
        "reason": reason,
    }


def _overall_result(candidates: list[dict[str, Any]]) -> str:
    values = [candidate["admissibility"] for candidate in candidates]

    if all(value == "admissible_for_fold_in" for value in values):
        return "admissible"

    if all(value == "advisory_only" for value in values):
        return "advisory_only"

    if all(value == "rejected" for value in values):
        return "rejected"

    return "mixed"


def build(input_obj: dict[str, Any]) -> dict[str, Any]:
    raw_candidates = _require_candidates(input_obj.get("candidates"))
    candidates = [_candidate_result(candidate) for candidate in raw_candidates]

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "authority_status": AUTHORITY_STATUS,
        "creates_release_authority": False,
        "invariant": INVARIANT,
        "candidates": candidates,
        "result": _overall_result(candidates),
    }

    notes = input_obj.get("notes")
    if isinstance(notes, str) and notes:
        out["notes"] = notes

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an evidence_fold_in_admissibility_v0 diagnostic artifact."
    )
    parser.add_argument("--input", required=True, help="Input candidate bundle JSON.")
    parser.add_argument("--out", required=True, help="Output diagnostic JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        input_obj = _load_json_object(Path(args.input))
        output_obj = build(input_obj)
        _write_json(Path(args.out), output_obj)
    except Exception as exc:
        print(f"::error::failed to build evidence_fold_in_admissibility_v0: {exc}")
        return 1

    print(f"OK: wrote evidence_fold_in_admissibility_v0 artifact: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
