"""Resolve independently configured comparison-reference checks for one target.

This extends the LRM-02 acceptance boundary; it does not infer cross-source
identity from labels or turn an accepted reference into a controlled proof.
The operator fixes the external configuration independently of the package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .io import (InputError, ROOT, relative_path, safe_read, sha256,
                 strict_json, unique_index)
from .trust import SCOPES, _external


SCHEMA_PATH = "language_relation_comparison_evidence_v0.schema.json"
REVIEW_VERSION = "language_relation_comparison_review_v0"
CONFIG_VERSION = "language_relation_comparison_trust_config_v0"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = strict_json(safe_read(ROOT / "schemas", SCHEMA_PATH))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate(value: dict) -> None:
    try:
        error = next(_validator().iter_errors(value), None)
    except RecursionError as exc:
        raise InputError("comparison evidence schema depth exceeded") from exc
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise InputError(f"comparison evidence schema violation at {location}: {error.message[:300]}")


def _passed(check: dict) -> bool:
    return check["status"] == "completed" and check["result"] == "pass"


def _failure(check: dict, label: str) -> tuple[str, str]:
    result = "fail" if check["status"] == "completed" and check["result"] == "fail" else "unresolved"
    return result, f"{label} was not completed successfully: {check['reason'] or check['status']}"


def _result(result: str, reason: str | None, *, evidence: list[str] | None = None,
            record_id: str | None = None, closed: list[str] | None = None,
            accepted: list[str] | None = None, family: bool = False,
            context: bool = False) -> dict:
    basis = "accepted_reference" if result == "pass" else "candidate_only"
    return {"result": result, "reason": reason, "basis": basis,
            "claim_scope": SCOPES[basis], "evidence_refs": sorted(set(evidence or [])),
            "verification_ids": [record_id] if record_id else [],
            "closed_obligation_ids": sorted(closed or []),
            "accepted_correspondence_ids": sorted(accepted or []),
            "family_checked": family, "context_checked": context}


def _target(document: dict, target_id: str) -> dict:
    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    if target_id not in targets:
        raise InputError(f"unresolved comparison evidence target: {target_id}")
    return targets[target_id]


def relevant_context_ids(document: dict, target_id: str,
                         correspondence_ids: list[str], *,
                         relation_ids_by_side: dict[str, list[str]] | None = None) -> list[str]:
    """Return context sources used by the selected target and its premises.

    Follow relation/proposition references and finite domains to their entity
    anchors. Additional relation roots extend the target's proof scope, as for
    a separately assessed addition; they never replace its original roots.
    An unrelated target's context is not imported into this target.
    """
    target = _target(document, target_id)
    sources = unique_index(document["sources"], "source_id")
    context = {key for key, row in sources.items() if row["role"] == "context"}
    anchors = unique_index(document["source_anchors"], "anchor_id")
    obligations = unique_index(document["coverage_obligations"], "obligation_id")
    correspondences = unique_index(document["correspondence"], "correspondence_id")
    additional = {} if relation_ids_by_side is None else relation_ids_by_side
    if not isinstance(additional, dict) or not set(additional) <= {"before", "after"}:
        raise InputError("invalid additional comparison relation sides")
    needed = set(target["context_source_ids"])
    for identifier in target["required_obligation_ids"]:
        needed.update(context.intersection(obligations[identifier]["source_ids"]))
    anchor_ids = set()
    for identifier in correspondence_ids:
        if identifier not in correspondences:
            raise InputError(f"unresolved comparison correspondence: {identifier}")
        anchor_ids.update(correspondences[identifier]["anchor_ids"])
    constraints = [node for variant in document["interpretations"]["variants"]
                   for node in variant["context_constraints"]]
    for side in ("before", "after"):
        representation = document["representations"][side]
        relations = unique_index(representation["relations"], "relation_id")
        entities = unique_index(representation["entities"], "entity_id")
        domains = unique_index(representation["domains"], "domain_id")
        groups = unique_index(representation["groups"], "group_id")
        pending = [relation for identifier in target[f"{side}_ids"]
                   for relation in groups.get(identifier, {"relation_ids": [identifier]})["relation_ids"]]
        extra = additional.get(side, [])
        if (not isinstance(extra, list) or any(not isinstance(key, str) for key in extra)
                or len(extra) != len(set(extra)) or not set(extra) <= relations.keys()):
            raise InputError(f"invalid additional {side} comparison relation IDs")
        pending.extend(extra)
        entity_ids = set()
        for identifier in correspondence_ids:
            item = correspondences[identifier]
            if item["kind"] in ("entity", "event"):
                entity_ids.update(item[f"{side}_ids"])
            else:
                pending.extend(relation for key in item[f"{side}_ids"]
                               for relation in groups.get(key, {"relation_ids": [key]})["relation_ids"])
        seen = set()
        # Constraint identifiers are unqualified but structure validation has
        # required them to resolve unambiguously across the two sides.
        nodes = list(constraints)
        while pending or nodes:
            if pending:
                identifier = pending.pop()
                if identifier in seen:
                    continue
                seen.add(identifier)
                relation = relations[identifier]
                anchor_ids.update(relation["anchor_ids"])
                if relation["speaker_entity_id"] is not None:
                    entity_ids.add(relation["speaker_entity_id"])
                nodes.append(relation["expression"])
            while nodes:
                node = nodes.pop()
                op = node["op"]
                if op == "ATOM":
                    for argument in node["arguments"]:
                        value = argument["value"]
                        if "entity_id" in value and value["entity_id"] in entities:
                            entity_ids.add(value["entity_id"])
                        elif "relation_id" in value and value["relation_id"] in relations:
                            pending.append(value["relation_id"])
                elif op == "REF" and node["relation_id"] in relations:
                    pending.append(node["relation_id"])
                elif op in ("FORALL", "EXISTS"):
                    if node["domain_id"] in domains:
                        entity_ids.update(domains[node["domain_id"]]["entity_ids"])
                    nodes.append(node["body"])
                elif op == "CONTEXT":
                    if node["speaker_entity_id"] in entities:
                        entity_ids.add(node["speaker_entity_id"])
                    nodes.append(node["body"])
                elif op == "NOT":
                    nodes.append(node["operand"])
                elif op in ("AND", "OR"):
                    nodes.extend(node["operands"])
                elif op == "IMPLIES":
                    nodes.extend((node["antecedent"], node["consequent"]))
        for identifier in entity_ids:
            anchor_ids.update(entities[identifier]["anchor_ids"])
    needed.update(anchors[key]["source_id"] for key in anchor_ids
                  if anchors[key]["source_id"] in context)
    return sorted(needed)


@dataclass
class ComparisonTrust:
    reviews: dict = field(default_factory=dict)
    config_pin: str | None = None
    payload_pins: dict = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Path | None, package_root: Path) -> "ComparisonTrust":
        store = cls()
        if config_path is None:
            return store
        path = _external(Path(config_path), package_root)
        root = path.parent.resolve(strict=True)
        raw = safe_read(root, path.name)
        config = strict_json(raw)
        _validate(config)
        if config["schema_version"] != CONFIG_VERSION:
            raise InputError("expected a comparison trust configuration")
        store.config_pin = "comparison-trust.sha256:" + sha256(raw)
        if len(config["review_files"]) > 128:
            raise InputError("comparison trust file limit exceeded")
        paths = set()
        subjects = set()
        total = 0
        for reference in config["review_files"]:
            parts = relative_path(reference["path"])
            _external(root.joinpath(*parts), package_root)
            if reference["path"] in paths:
                raise InputError("duplicate comparison review path")
            paths.add(reference["path"])
            raw = safe_read(root, reference["path"])
            total += len(raw)
            if total > 16 * 1024 * 1024:
                raise InputError("comparison trust total byte limit exceeded")
            if sha256(raw) != reference["content_sha256"]:
                raise InputError(f"comparison review digest mismatch: {reference['path']}")
            record = strict_json(raw)
            _validate(record)
            if record["schema_version"] != REVIEW_VERSION:
                raise InputError("expected a comparison review record")
            identifier = record["verification_id"]
            if identifier in store.reviews:
                raise InputError(f"duplicate comparison verification_id: {identifier}")
            subject = (record["input_ref"]["artifact_id"], record["input_ref"]["content_sha256"],
                       record["profile_ref"]["profile_id"], record["profile_ref"]["content_sha256"],
                       record["target_id"])
            if subject in subjects:
                raise InputError("multiple comparison reviews for one exact target subject")
            subjects.add(subject)
            unique_index(record["correspondence_checks"], "correspondence_id")
            unique_index(record["coverage_checks"], "obligation_id")
            unique_index(record["addition_checks"], "relation_id")
            unique_index([*record["correspondence_checks"], *record["coverage_checks"],
                          *record["addition_checks"], record["family_check"], record["context_check"]],
                         "check_id")
            store.reviews[identifier] = record
            store.payload_pins[identifier] = "sha256:" + sha256(raw)
        return store

    def _record(self, document: dict, input_ref: dict, target_id: str) -> tuple[dict | None, dict]:
        _target(document, target_id)
        evidence = [self.config_pin] if self.config_pin else []
        matching = [row for row in self.reviews.values()
                    if row["target_id"] == target_id and row["input_ref"] == input_ref
                    and row["profile_ref"] == document["profile_ref"]]
        if not matching:
            stale = any(row["target_id"] == target_id for row in self.reviews.values())
            return None, _result("fail" if stale else "unresolved",
                                  "comparison review input/profile subject mismatch" if stale else
                                  "comparison review is not independently configured for this target",
                                  evidence=evidence)
        record = matching[0]
        evidence.extend((record["verification_id"], self.payload_pins[record["verification_id"]]))
        correspondences = unique_index(document["correspondence"], "correspondence_id")
        obligations = unique_index(document["coverage_obligations"], "obligation_id")
        after_relations = unique_index(document["representations"]["after"]["relations"], "relation_id")
        variants = unique_index(document["interpretations"]["variants"], "variant_id")
        context = {row["source_id"] for row in document["sources"] if row["role"] == "context"}
        invalid = (
            any(row["correspondence_id"] not in correspondences for row in record["correspondence_checks"])
            or any(row["obligation_id"] not in obligations
                   or obligations[row["obligation_id"]]["target_id"] != target_id
                   for row in record["coverage_checks"])
            or any(row["relation_id"] not in after_relations for row in record["addition_checks"])
            or not set(record["reviewed_variant_ids"]) <= variants.keys()
            or not set(record["context_check"]["context_source_ids"]) <= context)
        if invalid:
            return None, _result("fail", "comparison review contains an unresolved or foreign-target subject",
                                  evidence=evidence, record_id=record["verification_id"])
        return record, _result("pass", None, evidence=evidence, record_id=record["verification_id"])

    def target_review(self, document: dict, input_ref: dict, target_id: str, *,
                      correspondence_ids: list[str], variant_ids: list[str],
                      relation_ids_by_side: dict[str, list[str]] | None = None) -> dict:
        """Resolve the target's own requested reference premises.

        ``variant_ids`` names the declared family inspected for this target,
        including variants subsequently rejected by the finite evaluator.
        A review of a truncated family remains a review of that partial family;
        this method does not turn it into exhaustive comparison.
        ``relation_ids_by_side`` optionally extends the context dependency
        closure to additional actual relations used by this target's proof.
        It does not change the exact input/target subject or discard any of
        the target's original context dependencies.
        """
        target = _target(document, target_id)
        if len(correspondence_ids) != len(set(correspondence_ids)) or len(variant_ids) != len(set(variant_ids)):
            raise InputError("duplicate requested comparison premise")
        correspondences = unique_index(document["correspondence"], "correspondence_id")
        if not set(correspondence_ids) <= correspondences.keys():
            raise InputError("unresolved requested comparison correspondence")
        declared_variants = {row["variant_id"] for row in document["interpretations"]["variants"]}
        if set(variant_ids) != declared_variants:
            raise InputError("comparison review must retain the declared joint variant family")
        required_context = set(relevant_context_ids(
            document, target_id, correspondence_ids,
            relation_ids_by_side=relation_ids_by_side))
        record, initial = self._record(document, input_ref, target_id)
        if record is None:
            return initial
        evidence = list(initial["evidence_refs"])
        failures = []
        accepted = []
        closed = []
        family = record["family_check"]
        family_checked = (_passed(family)
                          and family["family_state"] == document["interpretations"]["state"]
                          and set(record["reviewed_variant_ids"]) == declared_variants)
        if not family_checked:
            failures.append(_failure(family, "interpretation-family review") if not _passed(family) else
                            ("fail", "comparison review does not bind the declared joint variant family"))
        else:
            evidence.append(family["check_id"])
        context = record["context_check"]
        context_checked = _passed(context) and required_context <= set(context["context_source_ids"])
        if not context_checked:
            failures.append(_failure(context, "context review") if not _passed(context) else
                            ("fail", "comparison review omits required target context"))
        else:
            evidence.append(context["check_id"])
        correspondence_checks = unique_index(record["correspondence_checks"], "correspondence_id")
        for identifier in sorted(correspondence_ids):
            item = correspondences[identifier]
            check = correspondence_checks.get(identifier)
            if item["basis"] != "accepted_reference":
                failures.append(("unresolved", f"correspondence has no accepted-reference premise: {identifier}"))
            elif check is None:
                failures.append(("unresolved", f"correspondence review is absent: {identifier}"))
            elif check["reference_id"] != item["rule_or_reference_id"]:
                failures.append(("fail", f"correspondence reference identity mismatch: {identifier}"))
            elif not _passed(check):
                failures.append(_failure(check, f"correspondence {identifier}"))
            else:
                accepted.append(identifier)
                evidence.extend((check["check_id"], check["reference_id"]))
        obligations = unique_index(document["coverage_obligations"], "obligation_id")
        coverage_checks = unique_index(record["coverage_checks"], "obligation_id")
        for identifier in sorted(target["required_obligation_ids"]):
            item = obligations[identifier]
            check = coverage_checks.get(identifier)
            if item["state"] != "fulfilled":
                failures.append(("unresolved", f"submitted coverage remains incomplete: {identifier}"))
            elif record["verification_id"] not in item["evidence_refs"]:
                failures.append(("unresolved", f"coverage does not name this independent review: {identifier}"))
            elif check is None:
                failures.append(("unresolved", f"coverage review is absent: {identifier}"))
            elif set(check["source_ids"]) != set(item["source_ids"]):
                failures.append(("fail", f"coverage source scope mismatch: {identifier}"))
            elif not _passed(check):
                failures.append(_failure(check, f"coverage {identifier}"))
            else:
                closed.append(identifier)
                evidence.append(check["check_id"])
        outcome = "fail" if any(row[0] == "fail" for row in failures) else "unresolved" if failures else "pass"
        reason = "; ".join(row[1] for row in failures) if failures else None
        return _result(outcome, reason, evidence=evidence, record_id=record["verification_id"],
                       closed=closed, accepted=accepted, family=family_checked, context=context_checked)

    def addition_support(self, document: dict, input_ref: dict,
                         target_id: str, relation_id: str) -> dict:
        """Resolve a separate, named support check for an after-side relation.

        This does not establish introduction, source coverage, or world truth.
        The comparator must separately establish the relation's target boundary.
        A passing target review alone never supplies support for an addition.
        """
        after_relations = unique_index(document["representations"]["after"]["relations"], "relation_id")
        if relation_id not in after_relations:
            raise InputError(f"unresolved after-side addition: {relation_id}")
        record, initial = self._record(document, input_ref, target_id)
        if record is None:
            return initial
        checks = unique_index(record["addition_checks"], "relation_id")
        check = checks.get(relation_id)
        if check is None:
            return _result("unresolved", "addition has no independently reviewed support record",
                           evidence=initial["evidence_refs"], record_id=record["verification_id"])
        if not _passed(check):
            result, reason = _failure(check, f"addition support for {relation_id}")
            return _result(result, reason, evidence=initial["evidence_refs"],
                           record_id=record["verification_id"])
        if not check["evidence_refs"]:
            return _result("fail", "addition support has no named independent evidence",
                           evidence=initial["evidence_refs"], record_id=record["verification_id"])
        return _result("pass", None, evidence=[*initial["evidence_refs"], check["check_id"],
                                                *check["evidence_refs"]],
                       record_id=record["verification_id"])
