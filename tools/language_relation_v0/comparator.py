"""LRM-03 deterministic comparison of source-bound, explicitly scoped relations.

The finite algebra checks the supplied model. Source semantics additionally
require independent source and correspondence/coverage acceptance. No expected
corpus, language model, impact evaluator or release decision is used here.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .comparison_evidence import ComparisonTrust
from .io import (InputError, ROOT, canonical_bytes, read_input, safe_read, sha256,
                 strict_json, unique_index, validate_schema)
from .logic import LogicProblem, VariantLogic
from .trust import SCOPES
from .verifier import CHECKER_FILES, PROFILE_PATH, verify_input


VERSION = "0.1.0"
EVALUATOR_FILES = tuple(sorted(set(CHECKER_FILES) | {
    "tools/measure_language_relations_v0.py",
    "tools/language_relation_v0/comparator.py",
    "tools/language_relation_v0/logic.py",
    "tools/language_relation_v0/comparison_evidence.py",
    "schemas/language_relation_measurement_v0.schema.json",
    "schemas/language_relation_comparison_evidence_v0.schema.json",
}))


def evaluator_reference() -> dict:
    files = [{"path": name, "content_sha256": sha256(safe_read(ROOT, name))}
             for name in EVALUATOR_FILES]
    return {"tool_id": "language_relation_comparator_v0", "version": VERSION,
            "content_sha256": sha256(canonical_bytes({"files": files}))}


@lru_cache(maxsize=1)
def _measurement_validator() -> Draft202012Validator:
    schema = strict_json(safe_read(ROOT / "schemas", "language_relation_measurement_v0.schema.json"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _id(prefix: str, value: dict) -> str:
    return prefix + "." + sha256(canonical_bytes(value))[:48]


def _check(identifier: str, kind: str, target: str, result: str,
           reason: str | None, evidence: list[str] = ()) -> dict:
    return {"check_id": identifier, "kind": kind, "target_ids": [target],
            "status": "completed", "result": result, "reason": reason,
            "evidence_refs": sorted(set(evidence))}


def _expand(document: dict, side: str, identifiers: list[str]) -> set[str]:
    groups = {row["group_id"]: row["relation_ids"]
              for row in document["representations"][side]["groups"]}
    return {key for identifier in identifiers for key in groups.get(identifier, [identifier])}


def _dependencies(document: dict, side: str, identifiers: set[str], *,
                  expressions: list[dict] = ()) -> tuple[set[str], set[str]]:
    representation = document["representations"][side]
    relations = {row["relation_id"]: row for row in representation["relations"]}
    known_entities = {row["entity_id"] for row in representation["entities"]}
    domains = {row["domain_id"]: row["entity_ids"] for row in representation["domains"]}
    seen, entities = set(), set()
    pending = list(identifiers)
    nodes = list(expressions)
    while pending or nodes:
        if pending:
            key = pending.pop()
            if key in seen:
                continue
            seen.add(key)
            relation = relations[key]
            if relation["speaker_entity_id"] is not None:
                entities.add(relation["speaker_entity_id"])
            nodes.append(relation["expression"])
        while nodes:
            node = nodes.pop()
            op = node["op"]
            if op == "ATOM":
                for argument in node["arguments"]:
                    value = argument["value"]
                    if value.get("entity_id") in known_entities:
                        entities.add(value["entity_id"])
                    elif value.get("relation_id") in relations:
                        pending.append(value["relation_id"])
            elif op == "REF" and node["relation_id"] in relations:
                pending.append(node["relation_id"])
            elif op in ("FORALL", "EXISTS"):
                entities.update(domains.get(node["domain_id"], []))
                nodes.append(node["body"])
            elif op == "CONTEXT":
                if node["speaker_entity_id"] in known_entities:
                    entities.add(node["speaker_entity_id"])
                nodes.append(node["body"])
            elif op == "NOT":
                nodes.append(node["operand"])
            elif op in ("AND", "OR"):
                nodes.extend(node["operands"])
            elif op == "IMPLIES":
                nodes.extend((node["antecedent"], node["consequent"]))
    return seen, entities


def _relevant_correspondences(document: dict, target: dict, variant: dict) -> list[str]:
    dependencies = {}
    for side in ("before", "after"):
        identifiers = _expand(document, side, target[f"{side}_ids"])
        if side == "after" and not identifiers:
            # Proving absence inspects the actual processed roots, including
            # their identity premises, even when the requested selection is empty.
            identifiers.update(variant["after_relation_ids"])
        dependencies[side] = _dependencies(document, side, identifiers,
                                            expressions=variant["context_constraints"])
    rows = {row["correspondence_id"]: row for row in document["correspondence"]}
    selected = set()
    for identifier in variant["correspondence_ids"]:
        row = rows[identifier]
        position = 1 if row["kind"] in ("entity", "event") else 0
        for side in ("before", "after"):
            ids = (set(row[f"{side}_ids"]) if position else
                   _expand(document, side, row[f"{side}_ids"]))
            if ids & dependencies[side][position]:
                selected.add(identifier)
    return sorted(selected)


def _relation_link(document: dict, variant: dict, before: list[str], after: list[str],
                   selection: dict) -> dict[str, set[str]]:
    selected = set(variant["correspondence_ids"])
    wanted = {"before": set(before), "after": set(after)}
    covered = {"before": set(), "after": set()}
    for row in document["correspondence"]:
        if row["correspondence_id"] not in selected or row["kind"] not in ("relation", "relation_group"):
            continue
        endpoints = {side: _expand(document, side, row[f"{side}_ids"]) & set(selection[side]["reachable"])
                     for side in wanted}
        # A whole hyperedge cannot justify an arbitrary pair of its members.
        # Inactive alternatives are filtered by this exact joint variant.
        if all(endpoints[side] and endpoints[side] <= wanted[side] for side in wanted):
            for side in wanted:
                covered[side].update(endpoints[side])
    return covered


def _identity_gap(logic: VariantLogic, before: list[str], after: list[str]) -> bool:
    unmatched_types = {"before": set(), "after": set()}
    for row in logic.missing_identity(before, after):
        side = row["side"]
        kind = (logic.entities[side][row["entity_id"]]["entity_type"]
                if "entity_id" in row else "proposition")
        unmatched_types[side].add(kind)
    return bool(unmatched_types["before"] & unmatched_types["after"])


def _conjunction_contains(before: tuple, after: tuple) -> bool:
    """Containment under only transparent, same-context AND composition."""
    wanted = Counter(before[1] if before[0] == "AND" else (before,))
    available = Counter(after[1] if after[0] == "AND" else (after,))
    return wanted <= available


def _continuation_reason(document: dict, target: dict, variant: dict,
                         logic: VariantLogic, before: list[str], after_selection: dict) -> str | None:
    """Search conveyed continuation without deriving absence from a selection gap."""
    inspected_after = variant["after_relation_ids"]
    mapped = any(
        row["correspondence_id"] in logic.correspondence_ids
        and row["kind"] in ("relation", "relation_group")
        and _expand(document, "before", row["before_ids"]) & set(before)
        and _expand(document, "after", row["after_ids"]) & set(after_selection["reachable"])
        for row in document["correspondence"])
    if mapped or _conjunction_contains(logic.signature("before", before),
                                      logic.signature("after", inspected_after)):
        return "A possible joint continuation exists outside the selected after IDs."
    if _identity_gap(logic, before, inspected_after):
        return "Unresolved processed-side participant/proposition identity prevents proving absence."
    if target["question"] == "condition_impact" and inspected_after:
        candidates = {tuple(sorted(inspected_after)), *((key,) for key in inspected_after)}
        active = set(after_selection["safe_reachable"])
        for group in document["representations"]["after"]["groups"]:
            members = set(group["relation_ids"]) & active
            if members:
                candidates.add(tuple(sorted(members)))
            if len(candidates) > 256:
                return "The processed condition continuation scope exceeds the finite comparison bound."
        for identifiers in sorted(candidates):
            if logic.compare(before, identifiers, boolean_equivalence=True)["equivalent"]:
                return "A Boolean-equivalent condition continuation exists outside the selected after IDs."
        # An empty target does not specify which subset of independently
        # conveyed conditions would constitute the required joint continuation.
        # Do not invent a subset search or call that absent.
        if len(inspected_after) > 1:
            return "The required joint continuation among processed conditions is not selected."
    return None


def _witness(target: dict, variant_ids: list[str], before: list[str], after: list[str],
             kind: str, description: str, *, valuation: list[dict] = (),
             premises: list[str] = (), rules: list[str] = ()) -> dict:
    value = {"target_id": target["target_id"], "kind": kind,
             "variant_ids": sorted(set(variant_ids)),
             "before_relation_ids": sorted(set(before)), "after_relation_ids": sorted(set(after)),
             "valuation": sorted(valuation, key=lambda row: row["atom_id"]),
             "premise_refs": sorted(set(premises)), "rule_refs": sorted(set(rules)),
             "description": description}
    return {"witness_id": _id("lrm03.witness", value), **value}


def _difference_witness(logic: VariantLogic, target: dict, variant: dict,
                        before: list[str], after: list[str], comparison: dict) -> dict:
    valuation = comparison.get("counterexample")
    if comparison.get("aliases_complete") and valuation is not None:
        checked = logic.check_valuation(before, after, valuation)
        if not checked["different"]:
            raise RuntimeError("generated comparison valuation does not witness a difference")
        return _witness(target, [variant["variant_id"]], before, after, "configuration",
                        "A common profile-bounded valuation gives different selected condition values; "
                        "this configuration is hypothetical, not event evidence.",
                        valuation=valuation, rules=["LOGIC_01", "LOGIC_02"])
    kind = comparison.get("difference_kind", "operator_difference")
    if kind not in ("operator_difference", "role_difference"):
        kind = "operator_difference"
    return _witness(target, [variant["variant_id"]], before, after, kind,
                    comparison.get("detail") or "The bound typed relation structures differ.",
                    rules=["CONTEXT_01", "RELATION_01", "EQUIV_01", "EQUIV_02"])


def _variant_comparison(document: dict, profile: dict, target: dict, variant: dict,
                        correspondence_ids: list[str]) -> dict:
    logic = VariantLogic(document, profile, variant, correspondence_ids=correspondence_ids)
    selection = {side: logic.selected(side, target) for side in ("before", "after")}
    before, after = (selection[side]["selected"] for side in ("before", "after"))
    result = {"variant": variant, "logic": logic, "before": before, "after": after,
              "state": "UNDETERMINED", "witness": None, "reason": None}
    if any(row.get("embedded_only") for row in selection.values()):
        result["reason"] = "A selected helper occurs only inside an enclosing operator/context; its scope cannot be discarded."
        return result
    if target["granularity"] == "relation" and any(row["missing"] for row in selection.values()):
        result["reason"] = "A selected relation is outside this variant's conveyed root closure."
        return result
    if not before:
        result["reason"] = "No original relation is selected in this variant; additions are assessed separately."
        return result
    result["before_signature"] = logic.signature("before", before)
    result["after_signature"] = logic.signature("after", after)
    if not after:
        # Search the actual processed model, not just the caller's empty target
        # list. A missed selection cannot manufacture a broken relation.
        reason = _continuation_reason(document, target, variant, logic, before, selection["after"])
        if reason:
            result["reason"] = reason
            return result
        result.update(state="BROKEN", witness=_witness(
            target, [variant["variant_id"]], before, variant["after_relation_ids"], "absence",
            "No selected continuation exists in the inspected processed root scope. "
            "This absence claim requires the recorded complete target coverage.",
            rules=["RELATION_01", "IDENTITY_01"]))
        return result
    if _identity_gap(logic, before, after):
        result["reason"] = "Cross-source participant/proposition identity is unresolved; equal labels or bodies are insufficient."
        return result
    comparison = logic.compare(before, after,
                               boolean_equivalence=target["question"] == "condition_impact")
    linked = _relation_link(document, variant, before, after, selection)
    fully_linked = set(before) <= linked["before"] and set(after) <= linked["after"]
    withdrawal = (not comparison["equivalent"] and bool(linked["before"])
                  and set(after) <= linked["after"] and bool(set(before) - linked["before"]))
    if not fully_linked and not withdrawal:
        result["reason"] = "The complete selected relation/group lacks an explicit joint correspondence."
        return result
    if withdrawal:
        # A complete group can change when an original member is withdrawn.
        # This cannot justify PRESERVED, and needs processed-side coverage.
        reason = _continuation_reason(document, target, variant, logic,
                                      sorted(set(before) - linked["before"]), selection["after"])
        if reason:
            result["reason"] = reason
            return result
        result["requires_processed_scope"] = True
    if comparison["equivalent"]:
        result["state"] = "PRESERVED"
    else:
        result.update(state="CHANGED", witness=_difference_witness(
            logic, target, variant, before, after, comparison))
    return result


def _source_scope(document: dict, target: dict, side: str, closed: set[str]) -> list[str]:
    sources = {row["source_id"]: row["role"] for row in document["sources"]}
    return sorted(row["obligation_id"] for row in document["coverage_obligations"]
                  if row["obligation_id"] in closed and row["target_id"] == target["target_id"]
                  and row["kind"] == "source_scope" and row["side"] in (side, "both")
                  and side in {sources[key] for key in row["source_ids"]})


def _obligation_checked(document: dict, obligation: dict, review: dict,
                        result_basis: str) -> bool:
    """Close only a performed finite-model or independently reviewed check.

    The caller separately requires complete evaluation of this target's joint
    family. External context or named evidence cannot be discharged by copying
    a submitted fulfilled flag into a successful diagnostic.
    """
    if obligation["state"] != "fulfilled":
        return False
    side = obligation["side"]
    sources = {row["source_id"]: row["role"] for row in document["sources"]}
    if side == "context":
        scope_ok = all(sources[key] == "context" for key in obligation["source_ids"])
    else:
        sides = ("before", "after") if side == "both" else (side,)
        scope_ok = all(document["representations"][item]["source_id"] in obligation["source_ids"]
                       for item in sides)
    if not scope_ok:
        return False
    reviewed = (review["result"] == "pass"
                and obligation["obligation_id"] in review["closed_obligation_ids"])
    if (result_basis != "candidate_only" or side == "context" or obligation["kind"] == "context"
            or obligation["evidence_refs"]):
        return reviewed
    return obligation["kind"] in {
        "source_scope", "entity", "relation", "operator_scope", "correspondence", "interpretation_family"}


def _additions(document: dict, profile: dict, target: dict, rows: list[dict],
               closed: set[str], complete: bool, trust: ComparisonTrust,
               input_ref: dict, result_basis: str) -> tuple[list[dict], list[dict], list[dict]]:
    if not rows:
        return [], [], []
    relations = {row["correspondence_id"]: row for row in document["correspondence"]}
    per_variant, all_additions = [], set()
    for row in rows:
        variant = row["variant"]
        paired = set()
        for identifier in variant["correspondence_ids"]:
            mapping = relations[identifier]
            if mapping["kind"] in ("relation", "relation_group"):
                before_selection = row["logic"].selected("before", {"before_ids": mapping["before_ids"]})
                if set(before_selection["selected"]) & set(before_selection["safe_reachable"]):
                    paired.update(_expand(document, "after", mapping["after_ids"]))
        introduced = set(variant["after_relation_ids"]) - paired
        per_variant.append(introduced)
        all_additions.update(introduced)
    source_obligations = _source_scope(document, target, "before", closed)
    additions, witnesses = [], []
    for identifier in sorted(all_additions):
        item = {"relation_id": identifier, "target_id": target["target_id"],
                "novelty": "unresolved", "evidence_status": "unresolved", "evidence_refs": [],
                "derivation_ref": None, "source_coverage_obligation_ids": source_obligations,
                "reason": "Introduction requires complete original scope and a stable result across variants."}
        if not complete or not source_obligations or not all(identifier in ids for ids in per_variant):
            additions.append(item)
            continue
        # This is a separate proof subject. The original target's review may
        # cover fewer identities than the full premise set needed by an addition.
        addition_correspondences = {}
        for row in rows:
            variant = row["variant"]
            addition_target = {**target, "before_ids": variant["before_relation_ids"],
                               "after_ids": [identifier]}
            addition_correspondences[variant["variant_id"]] = _relevant_correspondences(
                document, addition_target, variant)
        if result_basis != "candidate_only":
            addition_review = trust.target_review(
                document, input_ref, target["target_id"],
                correspondence_ids=sorted({key for ids in addition_correspondences.values() for key in ids}),
                variant_ids=[variant["variant_id"] for variant in document["interpretations"]["variants"]],
                relation_ids_by_side={
                    "before": sorted({key for row in rows for key in row["variant"]["before_relation_ids"]}),
                    "after": [identifier]})
            item["evidence_refs"] = addition_review["evidence_refs"]
            if addition_review["result"] != "pass":
                item["reason"] = "The addition's own identity/context premises are not independently accepted: " + addition_review["reason"]
                additions.append(item)
                continue
        evaluations = []
        for row in rows:
            try:
                variant = row["variant"]
                logic = VariantLogic(document, profile, variant,
                                     correspondence_ids=addition_correspondences[variant["variant_id"]])
                original = variant["before_relation_ids"]
                if _identity_gap(logic, original, [identifier]):
                    item["reason"] = "The addition's cross-source participant/proposition identity is unresolved."
                    evaluations = []
                    break
                same = any(logic.compare([key], [identifier])["equivalent"] for key in original)
                try:
                    entailment = logic.entailment(original, identifier)
                except LogicProblem as exc:
                    if exc.code != "unsupported_entailment_context":
                        raise
                    # The Boolean derivation path cannot erase a typed claim's
                    # context. Its own independent support can still be resolved
                    # after the identity, context and finite-scope checks above.
                    entailment = None
                evaluations.append((row, same, entailment))
            except LogicProblem:
                evaluations = []
                break
        if not evaluations:
            if item["reason"] == "Introduction requires complete original scope and a stable result across variants.":
                item["reason"] = "The addition's independent comparison/derivation scope is unresolved."
            additions.append(item)
            continue
        if any(value is not None and not value["premises_satisfiable"] for _, _, value in evaluations):
            item["reason"] = "The original premises are inconsistent in a retained joint variant; no arbitrary conclusion is derived."
            additions.append(item)
            continue
        derivation_checked = all(value is not None for _, _, value in evaluations)
        exact = derivation_checked and all(same for _, same, _ in evaluations)
        derived = derivation_checked and all(value["entailed"] and value["premises_satisfiable"]
                      for _, _, value in evaluations)
        if exact or derived:
            before = sorted({key for row, _, _ in evaluations
                             for key in row["variant"]["before_relation_ids"]})
            witness = _witness(target, [row["variant"]["variant_id"] for row, _, _ in evaluations],
                               before, [identifier], "derivation",
                               "Each declared joint variant separately establishes this conclusion from "
                               "satisfiable original premises under the finite profile; no premises are "
                               "combined across variants and no world-truth claim is made.",
                               premises=before, rules=["LOGIC_01", "LOGIC_02", "EQUIV_01"])
            item.update(novelty="new_expression" if exact else "derived_explicitization",
                        evidence_status="supported", derivation_ref=witness["witness_id"], reason=None)
            witnesses.append(witness)
        else:
            support = trust.addition_support(document, input_ref, target["target_id"], identifier)
            if support["result"] == "pass" and result_basis != "candidate_only":
                item.update(novelty="externally_supported", evidence_status="supported",
                            evidence_refs=support["evidence_refs"], reason=None)
            elif not derivation_checked:
                item["reason"] = ("Boolean derivation is unsupported for the retained typed context, "
                                  "and no independently accepted addition support is available within "
                                  "the target's evidence boundary.")
            else:
                item.update(novelty="new_content", evidence_status="unsupported",
                            reason="No checked derivation or independently resolved support for this "
                                   "addition is available in the declared target scope.")
        additions.append(item)
    checks = [_check(
        _id("lrm03.addition", {"target_id": target["target_id"], "relation_id": item["relation_id"]}),
        "correspondence", target["target_id"],
        "unresolved" if item["novelty"] == "unresolved" else "pass",
        item["reason"] or "The addition's own finite comparison/derivation or independent support was checked within its target boundary.",
        item["evidence_refs"]) for item in additions]
    return additions, witnesses, checks


def _validate_measurement(report: dict, document: dict, verification: dict) -> None:
    error = next(_measurement_validator().iter_errors(report), None)
    if error is not None:
        raise RuntimeError("generated measurement violates its schema: " + error.message[:250])
    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    results = unique_index(report["results"], "target_id")
    witnesses = unique_index(report["witnesses"], "witness_id")
    if set(results) != set(targets):
        raise RuntimeError("measurement omits or duplicates a requested target")
    variants = {row["variant_id"] for row in document["interpretations"]["variants"]}
    relations = {side: {row["relation_id"]: row for row in representation["relations"]}
                 for side, representation in document["representations"].items()}
    for result in results.values():
        required = set(targets[result["target_id"]]["required_obligation_ids"])
        if set(result["coverage_obligation_ids"]) != required:
            raise RuntimeError("target obligation binding mismatch")
        if not set(result["closed_obligation_ids"]) <= required:
            raise RuntimeError("closed obligation belongs to another target")
        if result["assessment_state"] == "IDENTIFIED" and set(result["closed_obligation_ids"]) != required:
            raise RuntimeError("identified result has incomplete obligations")
        for key in result["witness_ids"]:
            if key not in witnesses or witnesses[key]["target_id"] != result["target_id"]:
                raise RuntimeError("unresolved or cross-target witness")
    for witness in witnesses.values():
        if not set(witness["variant_ids"]) <= variants:
            raise RuntimeError("witness names an unknown interpretation")
        for side in relations:
            if not set(witness[f"{side}_relation_ids"]) <= relations[side].keys():
                raise RuntimeError("witness names an unknown relation")
        unique_index(witness["valuation"], "atom_id")
        for atom in witness["valuation"]:
            matches = [index[atom["atom_id"]] for index in relations.values() if atom["atom_id"] in index]
            if (len(matches) != 1 or matches[0]["expression"]["op"] != "ATOM"
                    or any("variable" in value["value"] for value in matches[0]["expression"]["arguments"])):
                raise RuntimeError("valuation alias is not an unambiguous declared ground atom")
    if report["verification_refs"] != [{"artifact_id": verification["verification_id"],
                                        "content_sha256": sha256(canonical_bytes(verification))}]:
        raise RuntimeError("measurement verification-byte binding mismatch")


def measure_bundle(input_path: Path, *, package_root: Path | None = None,
                   trust_config: Path | None = None,
                   comparison_trust_config: Path | None = None) -> dict:
    """Recompute checks and comparison; return exact verification and measurement.

    Source and comparison trust configurations are independent operator premises.
    Candidate diagnoses refer to the supplied finite model only. The result has
    no aggregate PASS and does not evaluate downstream impact or release gates.
    """
    input_path = Path(input_path)
    root = (Path(package_root) if package_root is not None else input_path.absolute().parent).resolve(strict=True)
    raw = read_input(input_path, root)
    document = strict_json(raw)
    source_verification = verify_input(input_path, package_root=root, trust_config=trust_config)
    if (source_verification["input_ref"]["content_sha256"] != sha256(raw)
            or read_input(input_path, root) != raw):
        raise InputError("input changed during source verification")
    profile = strict_json(safe_read(ROOT, PROFILE_PATH))
    trust = ComparisonTrust.load(comparison_trust_config, root)
    input_ref = source_verification["input_ref"]
    source_checks = {row["check_id"]: row for row in source_verification["checks"]}
    source_bases = {row["side"]: row["representation_basis"] for row in source_verification["basis_records"]}
    verification = deepcopy(source_verification)
    verification["checks"] = [row for row in verification["checks"] if row["kind"] != "correspondence"]
    evaluator = evaluator_reference()
    verification["checker_ref"] = evaluator
    verification.pop("verification_id", None)
    results, witnesses, introduced, unresolved = [], {}, [], []
    family = document["interpretations"]
    declared_variants = sorted(family["variants"], key=lambda row: row["variant_id"])
    overflow = len(declared_variants) > profile["limits"]["max_joint_variants"]
    variants = declared_variants[:profile["limits"]["max_joint_variants"]]
    obligations = unique_index(document["coverage_obligations"], "obligation_id")
    for target in sorted(document["measurement_request"]["targets"], key=lambda row: row["target_id"]):
        target_id = target["target_id"]
        relevant = {variant["variant_id"]: _relevant_correspondences(document, target, variant)
                    for variant in variants}
        used_correspondences = sorted({key for ids in relevant.values() for key in ids})
        review = trust.target_review(document, input_ref, target_id,
                                    correspondence_ids=used_correspondences,
                                    variant_ids=[row["variant_id"] for row in declared_variants])
        result_basis = ("accepted_reference" if review["result"] == "pass"
                        and all(value != "candidate_only" for value in source_bases.values())
                        else "candidate_only")
        review_id = _id("lrm03.review", {"target_id": target_id})
        verification["checks"].append(_check(review_id, "reference_acceptance", target_id,
                                              review["result"], review["reason"], review["evidence_refs"]))
        result = {"target_id": target_id, "relation_state": "UNDETERMINED",
                  "assessment_state": "UNRESOLVED", "representation_basis": result_basis,
                  "claim_scope": SCOPES[result_basis], "verification_ids": [],
                  "coverage_obligation_ids": sorted(target["required_obligation_ids"]),
                  "closed_obligation_ids": [], "compatible_variant_ids": [],
                  "possible_relation_states": [], "witness_ids": [], "reason": None}
        rows, failures = [], []
        bound = all(row["result"] == "pass" for row in source_checks.values()
                    if row["kind"] == "source_binding")
        mapping_failed = any(source_checks[f"mapping.{side}"]["result"] == "fail"
                             for side in ("before", "after"))
        processing_bound = (document["measurement_request"]["processing_claim"] != "processing_change"
                            or source_checks["processing"]["result"] == "pass")
        if not bound or not processing_bound:
            result.update(assessment_state="UNBOUND", reason="Required source/context or processing-instance binding is not established.")
        elif family["state"] == "unknown":
            result.update(assessment_state="UNBOUND", reason="The interpretation family is unknown.")
        elif family["state"] == "empty":
            result.update(assessment_state="INCOMPATIBLE", reason="The declared candidate/reference interpretation family is empty; no vacuous preservation follows.")
        elif mapping_failed:
            result["reason"] = "The independent source checker contradicts a submitted representation."
        elif review["result"] == "fail":
            result["reason"] = "An independently configured necessary comparison premise failed: " + review["reason"]
        elif target["question"] in ("support_preservation", "observed_effect"):
            result["reason"] = "Support and observed-effect evaluation belong to LRM-04."
        else:
            for variant in variants:
                try:
                    rows.append(_variant_comparison(document, profile, target, variant, relevant[variant["variant_id"]]))
                except LogicProblem as exc:
                    failures.append((variant["variant_id"], exc.code, exc.detail))
            complete = family["state"] == "complete" and not overflow and not failures and bool(rows)
            locally_closed = bool(rows) and not failures and all(row["state"] != "UNDETERMINED" for row in rows)
            closed = []
            for identifier in target["required_obligation_ids"]:
                obligation = obligations[identifier]
                if (complete and locally_closed
                        and _obligation_checked(document, obligation, review, result_basis)):
                    closed.append(identifier)
            result["closed_obligation_ids"] = sorted(closed)
            result["compatible_variant_ids"] = sorted(row["variant"]["variant_id"] for row in rows)
            states = sorted({row["state"] for row in rows})
            for row in rows:
                if row["witness"] is not None:
                    witnesses[row["witness"]["witness_id"]] = row["witness"]
                    result["witness_ids"].append(row["witness"]["witness_id"])
            if (target["question"] == "interpretation_preservation" and complete and locally_closed
                    and {row["before_signature"] for row in rows} != {row["after_signature"] for row in rows}):
                witness = _witness(target, result["compatible_variant_ids"],
                                   sorted({key for row in rows for key in row["before"]}),
                                   sorted({key for row in rows for key in row["after"]}),
                                   "alternative_loss", "The complete declared family changes its selected "
                                   "interpretation alternatives. Each before/after/context choice remains in "
                                   "its recorded joint variant; the actual reading is not identified.",
                                   rules=["VARIANT_01", "IDENTITY_01"])
                witnesses[witness["witness_id"]] = witness
                result["witness_ids"].append(witness["witness_id"])
                states = ["CHANGED"]
            result["possible_relation_states"] = states
            if complete and set(closed) == set(target["required_obligation_ids"]) and len(states) == 1 and states[0] != "UNDETERMINED":
                if ((states[0] == "BROKEN" or any(row.get("requires_processed_scope") for row in rows))
                        and not _source_scope(document, target, "after", set(closed))):
                    result["reason"] = "Relation absence/withdrawal requires sufficient processed-side source scope."
                else:
                    result.update(relation_state=states[0], assessment_state="IDENTIFIED", reason=None)
            elif failures and all(code == "incompatible_context" for _, code, _ in failures) and not rows and family["state"] == "complete" and not overflow:
                result.update(assessment_state="INCOMPATIBLE", reason="No declared joint variant satisfies its checked context constraints.")
            elif not complete:
                result["reason"] = ("The interpretation family is truncated or exceeds the finite bound."
                                    if family["state"] == "truncated" or overflow else
                                    "; ".join(detail for _, _, detail in failures) or "No compatible variant was fully evaluated.")
            elif set(closed) != set(target["required_obligation_ids"]):
                result["reason"] = next((row["reason"] for row in rows if row["reason"]),
                                        "Required target coverage is not closed by the performed checks.")
            else:
                result["reason"] = "The admissible joint variants give different target outcomes."
            additions, addition_witnesses, addition_checks = _additions(
                document, profile, target, rows, set(closed), complete, trust, input_ref, result_basis)
            introduced.extend(additions)
            verification["checks"].extend(addition_checks)
            for witness in addition_witnesses:
                witnesses[witness["witness_id"]] = witness
        if result["reason"] is None and result["assessment_state"] != "IDENTIFIED":
            result["reason"] = "Required target evaluation is unresolved."
        result["witness_ids"] = sorted(set(result["witness_ids"]))
        for identifier in target["required_obligation_ids"]:
            closed = identifier in result["closed_obligation_ids"]
            verification["checks"].append(_check(
                _id("lrm03.coverage", {"target_id": target_id, "obligation_id": identifier}),
                "coverage", target_id, "pass" if closed else "unresolved",
                ("Checked closure of the supplied finite candidate model only; no source-extraction completeness claim."
                 if result_basis == "candidate_only" else "Closure conditional on the exact independently reviewed target.")
                if closed else result["reason"] or "Target coverage is unresolved.",
                review["evidence_refs"] if result_basis != "candidate_only" else []))
            if not closed:
                unresolved.append({"obligation_id": identifier, "target_ids": [target_id],
                                   "reason_code": "target_obligation_unresolved",
                                   "detail": result["reason"] or "Target obligation remains unresolved.",
                                   "source_anchor_ids": []})
        correspondence_closed = bool(rows) and all(row["state"] != "UNDETERMINED" for row in rows)
        verification["checks"].append(_check(
            _id("lrm03.correspondence", {"target_id": target_id}), "correspondence", target_id,
            "pass" if correspondence_closed else "unresolved",
            "Checked explicit correspondence within the recorded result scope." if correspondence_closed else
            result["reason"] or "Target correspondence is unresolved.", used_correspondences))
        if target["question"] == "condition_impact" or document["impact_model"] is not None:
            unresolved.append({"obligation_id": _id("lrm03.impact", {"target_id": target_id}),
                               "target_ids": [target_id], "reason_code": "impact_not_evaluated",
                               "detail": "LRM-03 compares the selected relations/conditions; downstream impact and support evaluation belong to LRM-04.",
                               "source_anchor_ids": []})
        results.append(result)
    unique_index(verification["checks"], "check_id")
    verification["checks"].sort(key=lambda row: row["check_id"])
    if any(row["result"] == "fail" for row in verification["checks"]):
        verification["status_axes"]["consistency_status"] = "conflicting"
    verification["verification_id"] = _id("lrm03.verification", verification)
    validate_schema(verification, "language_relation_verification_v0.schema.json")
    for result in results:
        result["verification_ids"] = [verification["verification_id"]]
    report = {"schema_version": "language_relation_measurement_v0", "artifact_kind": "language_relation_measurement",
              "provenance": "measurement_run", "input_ref": input_ref,
              "verification_refs": [{"artifact_id": verification["verification_id"],
                                     "content_sha256": sha256(canonical_bytes(verification))}],
              "profile_ref": document["profile_ref"], "evaluator_ref": evaluator,
              "execution": {"status": "completed", "reason": None}, "results": results,
              "introduced_relations": sorted(introduced, key=lambda row: (row["target_id"], row["relation_id"])),
              "witnesses": sorted(witnesses.values(), key=lambda row: row["witness_id"]),
              "impacts": [], "support": None,
              "unresolved": sorted(unresolved, key=lambda row: (row["target_ids"], row["obligation_id"])),
              "status_axes": deepcopy(verification["status_axes"]),
              "authority_effect": "none", "release_authority_activation": False}
    report["measurement_id"] = _id("lrm03.measurement", report)
    _validate_measurement(report, document, verification)
    if read_input(input_path, root) != raw:
        raise InputError("input changed during relation measurement")
    return {"measurement": report, "verification": verification}


def measure_input(input_path: Path, *, package_root: Path | None = None,
                  trust_config: Path | None = None,
                  comparison_trust_config: Path | None = None) -> dict:
    """Return the deterministic measurement; measure_bundle also returns checks."""
    return measure_bundle(input_path, package_root=package_root, trust_config=trust_config,
                          comparison_trust_config=comparison_trust_config)["measurement"]
