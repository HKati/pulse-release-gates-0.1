"""LRM-02 orchestration: source binding and independent representation checks."""

from __future__ import annotations

from pathlib import Path

from . import __version__
from .binding import bind_sources
from .io import (InputError, ROOT, canonical_bytes, read_input, safe_read, sha256,
                 strict_json, unique_index, validate_schema)
from .profile import check_profile_mapping
from .structure import validate_structure
from .trust import SCOPES, TrustStore


PROFILE_PATH = "contracts/language_relation_profile_v0.json"
PROFILE_ID = "lrm_finite_reference_profile_v0"
# The parser implements this exact preserved grammar, not a caller-editable one.
PROFILE_SHA256 = "f98a7c59b97f3854f9d585ae0fbf47b4427dd21345104def885fc046a3c8a2ad"
CHECKER_FILES = tuple(sorted([
    "tools/check_language_relation_input_v0.py",
    *[f"tools/language_relation_v0/{name}.py" for name in
      ("__init__", "io", "binding", "structure", "profile", "trust", "verifier")],
    "schemas/language_relation_input_v0.schema.json",
    "schemas/language_relation_verification_v0.schema.json",
    "schemas/language_relation_evidence_v0.schema.json",
    PROFILE_PATH,
]))


def checker_reference() -> dict:
    files = [{"path": name, "content_sha256": sha256(safe_read(ROOT, name))}
             for name in CHECKER_FILES]
    return {"tool_id": "language_relation_input_verifier_v0", "version": __version__,
            "content_sha256": sha256(canonical_bytes({"files": files}))}


def _check_id(prefix: str, identifier: str) -> str:
    result = f"{prefix}.{identifier}"
    return result if len(result) <= 128 else f"{prefix}.{sha256(identifier.encode('utf-8'))}"


def _check(check_id: str, kind: str, targets: list[str], *,
           result: str | None = None, reason: str | None = None,
           status: str = "completed", evidence: list[str] | None = None) -> dict:
    return {"check_id": check_id, "kind": kind, "target_ids": sorted(targets),
            "status": status, "result": result, "reason": reason,
            "evidence_refs": sorted(set(evidence or []))}


def _joint_limits(mappings: dict, profile: dict) -> None:
    """Never turn two locally bounded checks into an unbounded joint claim."""
    details = [mappings[side].get("details", {}) for side in ("before", "after")]
    atoms = sum(row.get("expanded_boolean_atoms", 0) for row in details)
    costs = {}
    for row in details:
        for variant in row.get("checked_variants", []):
            key = variant["variant_id"]
            costs[key] = costs.get(key, 0) + variant["expanded_ast_nodes"]
    limits = profile["limits"]
    if (atoms > limits["max_expanded_boolean_atoms"]
            or sum(row.get("source_ast_nodes", 0) for row in details) > limits["max_ast_nodes_per_variant"]
            or any(cost > limits["max_ast_nodes_per_variant"] for cost in costs.values())):
        for mapping in mappings.values():
            if mapping["result"] == "pass":
                mapping.update(result="unresolved", reason="joint variant resource bound exceeded")


def _target_roots_checked(document: dict, side: str, mapping: dict) -> bool:
    variants = mapping.get("details", {}).get("checked_variants", [])
    if not variants:
        return False
    checked = set.intersection(*[set(row["checked_relation_ids"]) for row in variants])
    groups = {row["group_id"]: row["relation_ids"]
              for row in document["representations"][side]["groups"]}
    needed = set()
    for target in document["measurement_request"]["targets"]:
        for identifier in target[f"{side}_ids"]:
            needed.update(groups.get(identifier, [identifier]))
    return needed <= checked


def verify_input(input_path: Path, *, package_root: Path | None = None,
                 trust_config: Path | None = None) -> dict:
    """Return a schema-valid verification artifact, with no aggregate PASS.

    Malformed/unsafe input raises InputError; I/O failures propagate OSError.
    A completed failing or unresolved check is a diagnostic, not an exception.
    Stronger input basis labels are requests whose evidence must be resolved.
    """
    input_path = Path(input_path)
    root = Path(package_root) if package_root is not None else input_path.absolute().parent
    root = root.resolve(strict=True)
    raw = read_input(input_path, root)
    document = strict_json(raw)
    validate_schema(document, "language_relation_input_v0.schema.json")
    profile_raw = safe_read(ROOT, PROFILE_PATH)
    profile = strict_json(profile_raw)
    expected_profile = {"profile_id": PROFILE_ID, "content_sha256": PROFILE_SHA256}
    if sha256(profile_raw) != PROFILE_SHA256 or document["profile_ref"] != expected_profile:
        raise InputError("unsupported profile or exact profile digest mismatch")
    validate_structure(document, profile)
    trust = TrustStore.load(trust_config, root)
    texts, bindings = bind_sources(document, root)
    input_ref = {"artifact_id": document["case_id"], "content_sha256": sha256(raw)}
    targets = [row["target_id"] for row in document["measurement_request"]["targets"]]
    checks = []
    for side, binding in bindings.items():
        checks.append(_check(f"source.{side}", "source_binding", targets,
                             result=binding["result"], reason=binding["reason"],
                             evidence=binding["evidence_refs"]))
    context_bound = bindings.get("context", {"result": "pass"})["result"] == "pass"
    mappings = {}
    for side in ("before", "after"):
        if bindings[side]["result"] != "pass" or not context_bound:
            mappings[side] = {"result": None, "reason": "required source binding failed",
                              "status": "not_run", "details": {}}
        else:
            mappings[side] = check_profile_mapping(document, profile, texts, side)
    _joint_limits(mappings, profile)
    for side, mapping in mappings.items():
        checked = mapping.get("details", {})
        evidence = [*checked.get("checked_anchor_ids", []),
                    *checked.get("checked_relation_ids", [])]
        checks.append(_check(f"mapping.{side}", "representation_mapping", targets,
                             result=mapping["result"], reason=mapping["reason"],
                             status=mapping.get("status", "completed"), evidence=evidence))

    accepted = {}
    basis_records = []
    context_ids = {row["source_id"] for row in document["sources"] if row["role"] == "context"}
    context_anchors = {row["anchor_id"] for row in document["source_anchors"]
                       if row["source_id"] in context_ids}
    external_context = (
        any(row["context_constraints"] for row in document["interpretations"]["variants"])
        or any(row["context_source_ids"] for row in document["measurement_request"]["targets"])
        or any(row["kind"] == "context" or context_ids.intersection(row["source_ids"])
               for row in document["coverage_obligations"])
        or any(context_anchors.intersection(row["anchor_ids"])
               for representation in document["representations"].values()
               for row in [*representation["entities"], *representation["relations"]]))
    for side in ("before", "after"):
        submitted = document["representation_basis"][side]
        requested = submitted["basis"]
        mapping = mappings[side]
        if requested == "candidate_only":
            accepted[side] = {"result": None, "reason": "stronger basis was not requested",
                              "status": "not_run", "evidence_refs": []}
        elif bindings[side]["result"] != "pass" or not context_bound:
            accepted[side] = {"result": None, "reason": "required source binding failed",
                              "status": "not_run", "evidence_refs": []}
        else:
            accepted[side] = trust.acceptance(document, side, input_ref)
            if trust.config_pin:
                accepted[side]["evidence_refs"] = sorted(set(
                    [trust.config_pin, *accepted[side]["evidence_refs"]]))
        acceptance = accepted[side]
        checks.append(_check(f"acceptance.{side}", "reference_acceptance", targets,
                             result=acceptance["result"], reason=acceptance["reason"],
                             status=acceptance.get("status", "completed"),
                             evidence=acceptance["evidence_refs"]))
        allow = acceptance["result"] == "pass" and mapping["result"] != "fail"
        reason = acceptance["reason"]
        if mapping["result"] == "fail":
            reason = "independent source mapping contradicts the submitted representation"
        if requested == "profile_verified":
            allow = (allow and mapping["result"] == "pass" and not external_context
                     and _target_roots_checked(document, side, mapping))
            if not allow and acceptance["result"] == "pass" and mapping["result"] != "fail":
                reason = "controlled mapping, selected target, or external context is not fully verified"
        result_basis = requested if allow else "candidate_only"
        ids = [f"source.{side}"] if bindings[side]["result"] == "pass" else []
        if result_basis != "candidate_only":
            ids.append(f"acceptance.{side}")
            if mapping["result"] == "pass":
                ids.append(f"mapping.{side}")
            if "context" in bindings:
                ids.append("source.context")
        basis_records.append({"side": side, "representation_basis": result_basis,
                              "claim_scope": SCOPES[result_basis], "check_ids": sorted(ids),
                              "acceptance_ref": submitted["acceptance_ref"] if allow else None,
                              "reason": None if allow else reason})

    if document["processing_binding"] is None:
        checks.append(_check("processing", "subject_binding", targets, status="not_run",
                             reason="structural comparison has no processing event to verify"))
    elif any(row["result"] != "pass" for row in bindings.values()):
        checks.append(_check("processing", "subject_binding", targets, status="not_run",
                             reason="required source binding failed"))
    else:
        result = trust.processing_binding(document, input_ref)
        if trust.config_pin:
            result["evidence_refs"] = sorted(set([trust.config_pin, *result["evidence_refs"]]))
        checks.append(_check("processing", "subject_binding", targets,
                             result=result["result"], reason=result["reason"],
                             evidence=result["evidence_refs"]))

    for obligation in document["coverage_obligations"]:
        side = obligation["side"]
        sides = ("before", "after") if side == "both" else (side,)
        supported_kind = obligation["kind"] in {
            "source_scope", "entity", "relation", "operator_scope", "interpretation_family"}
        dependencies = []
        supported = supported_kind and side != "context"
        complete_family = (document["interpretations"]["state"] == "complete"
                           and bool(document["interpretations"]["variants"]))
        for selected in sides:
            if selected == "context":
                supported = False
                continue
            mapping = mappings[selected]
            profile_closed = (mapping["result"] == "pass" and not external_context
                              and _target_roots_checked(document, selected, mapping))
            reference_closed = (accepted[selected]["result"] == "pass"
                                and document["representation_basis"][selected]["basis"] == "accepted_reference"
                                and mapping["result"] != "fail" and complete_family)
            supported &= (profile_closed or reference_closed)
            dependencies.append(f"mapping.{selected}" if profile_closed else f"acceptance.{selected}")
        checks.append(_check(_check_id("coverage", obligation["obligation_id"]), "coverage",
                             [obligation["target_id"]], result="pass" if supported else "unresolved",
                             reason=None if supported else "coverage is not closed by an actual check in this implementation",
                             evidence=dependencies if supported else []))
    for correspondence in document["correspondence"]:
        checks.append(_check(_check_id("correspondence", correspondence["correspondence_id"]),
                             "correspondence", targets, status="not_run",
                             reason="cross-source correspondence verification belongs to LRM-03"))
    any_binding = any(row["result"] == "pass" for row in bindings.values())
    unique_index(checks, "check_id")
    report = {
        "schema_version": "language_relation_verification_v0",
        "artifact_kind": "language_relation_verification", "provenance": "verification_run",
        "input_ref": input_ref, "profile_ref": expected_profile, "checker_ref": checker_reference(),
        "checks": sorted(checks, key=lambda row: row["check_id"]),
        "basis_records": sorted(basis_records, key=lambda row: row["side"]),
        "status_axes": {
            "observation_status": "partially_observed" if any_binding else "not_observed",
            "binding_status": "partially_bound" if any_binding else "unbound",
            "consistency_status": "conflicting" if any(row["result"] == "fail" for row in checks)
                                  else "internally_incomplete",
            "reproduction_status": "not_tested", "causal_status": "not_evaluated",
            "authority_status": "none",
        },
        "authority_effect": "none", "release_authority_activation": False,
    }
    report["verification_id"] = "lrm02." + sha256(canonical_bytes(report))[:48]
    validate_schema(report, "language_relation_verification_v0.schema.json")
    return report
