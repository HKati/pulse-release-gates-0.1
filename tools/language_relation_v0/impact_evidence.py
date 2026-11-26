"""Resolve independently pinned, target-local support and observation premises.

The operator supplies this configuration outside the measured package.  A file
hash binds the bytes of that premise; it does not authenticate its author or
turn a reviewed model into world truth.  Source acceptance, comparison closure,
processing acceptance, and the actual impact calculation remain separate gates.
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .comparison_evidence import relevant_context_ids
from .io import (InputError, ROOT, canonical_bytes, relative_path, safe_read,
                 sha256, strict_json, unique_index)
from .logic import LogicProblem
from .support import _expression_key
from .trust import _external


SCHEMA_PATH = "language_relation_impact_evidence_v0.schema.json"
CONFIG_VERSION = "language_relation_impact_trust_config_v0"
REVIEW_VERSION = "language_relation_impact_review_v0"
OBSERVATION_VERSION = "language_relation_impact_observation_v0"
_SIDES = ("before", "after")
_SOURCE_FIELDS = ("source_id", "role", "language", "revision", "content_sha256", "byte_length")
_MAX_OPPOSITION_SCAN_CLAIMS = 4096
_MAX_OPPOSITION_SCAN_TOKENS = 262144
_MAX_OPPOSITION_PAIRS = 65536


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = strict_json(safe_read(ROOT / "schemas", SCHEMA_PATH))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate(value: dict) -> None:
    try:
        error = next(_validator().iter_errors(value), None)
    except RecursionError as exc:
        raise InputError("impact evidence schema depth exceeded") from exc
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise InputError(f"impact evidence schema violation at {location}: {error.message[:300]}")


def _target(document: dict, target_id: str) -> dict:
    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    if target_id not in targets:
        raise InputError(f"unresolved impact evidence target: {target_id}")
    return targets[target_id]


def _result(result: str, reason: str | None, *, record: dict | None = None,
            model: dict | None = None, base_ids: list[str] = (), rule_ids: list[str] = (),
            evidence: list[str] = (), observation: dict | None = None) -> dict:
    return {"result": result, "reason": reason,
            "mode": record["mode"] if record else None,
            "claim_ids": sorted(record["claim_ids"]) if record else [],
            "model": deepcopy(model), "admitted_base_claim_ids": sorted(base_ids),
            "admitted_rule_ids": sorted(rule_ids), "evidence_refs": sorted(set(evidence)),
            "observation": deepcopy(observation),
            "verification_ids": [record["verification_id"]] if record else []}


def _check(check: dict | None, label: str, failures: list, evidence: list) -> None:
    if check is None:
        failures.append(("unresolved", f"{label} has no independently configured check"))
        return
    evidence.append(check["check_id"])
    evidence.extend(check["evidence_refs"])
    if check["status"] != "completed" or check["result"] != "pass":
        result = "fail" if check["status"] == "completed" and check["result"] == "fail" else "unresolved"
        failures.append((result, f"{label} was not completed successfully: "
                         f"{check['reason'] or check['status']}"))
    elif not check["evidence_refs"]:
        failures.append(("fail", f"{label} has no named independent evidence"))


def _possible_opponents(claims: dict[str, dict]) -> dict[str, set[str]]:
    """Index exact modeled A/NOT A pairs without asserting either is grounded.

    Use the same bounded iterative structural keys as the support conflict
    detector.  Scoping must retain an opposing claim's support routes before
    actual closure decides whether there is a conflict.  No logical rewriting,
    REF expansion, pairwise reachability, or world-level contradiction is inferred.
    """
    if len(claims) > _MAX_OPPOSITION_SCAN_CLAIMS:
        raise LogicProblem("impact_opposition_scan_limit", "The model exceeds the 4096-claim opposition scan bound.")
    by_expression, operands = defaultdict(list), {}
    tokens = 0
    for identifier, claim in claims.items():
        expression = claim["expression"]
        key = _expression_key(expression)
        tokens += len(key)
        by_expression[key].append(identifier)
        if expression["op"] == "NOT":
            operands[identifier] = _expression_key(expression["operand"])
            tokens += len(operands[identifier])
        if tokens > _MAX_OPPOSITION_SCAN_TOKENS:
            raise LogicProblem("impact_opposition_scan_limit", "The model exceeds the 262144-token opposition scan bound.")
    opponents = defaultdict(set)
    pairs = 0
    for identifier, operand in operands.items():
        for opposed in by_expression.get(operand, []):
            if opposed in opponents[identifier]:
                continue
            pairs += 1
            if pairs > _MAX_OPPOSITION_PAIRS:
                raise LogicProblem("impact_opposition_pair_limit", "The model exceeds the 65536-pair opposition bound.")
            opponents[identifier].add(opposed)
            opponents[opposed].add(identifier)
    return opponents


def _scoped_model(model: dict, claim_ids: list[str]) -> dict:
    """Keep incoming routes and exact possible opponents of relevant claims.

    An unreviewed alternative route cannot silently disappear and thereby
    manufacture loss of support; an opposing grounded claim must not vanish
    merely because it is outside the selected claim's ancestry.  Conversely,
    an unrelated graph/opposition component is not a premise of this target.
    """
    claims = unique_index(model["claims"], "claim_id")
    rules = unique_index(model["rules"], "rule_id")
    opponents = _possible_opponents(claims)
    incoming = defaultdict(list)
    for rule in rules.values():
        incoming[rule["conclusion_claim_id"]].append(rule)
    needed_claims, needed_rules = set(claim_ids), set()
    pending = deque(claim_ids)
    while pending:
        identifier = pending.popleft()
        for opposed in opponents[identifier]:
            if opposed not in needed_claims:
                needed_claims.add(opposed)
                pending.append(opposed)
        for rule in incoming[identifier]:
            needed_rules.add(rule["rule_id"])
            for premise in rule["premise_claim_ids"]:
                if premise not in needed_claims:
                    needed_claims.add(premise)
                    pending.append(premise)
    return {"model_id": model["model_id"],
            "claims": [claims[key] for key in sorted(needed_claims)],
            "rules": [rules[key] for key in sorted(needed_rules)],
            "withdrawn_claim_ids": sorted(set(model["withdrawn_claim_ids"]) & needed_claims),
            "target_claim_ids": sorted(claim_ids)}


def _dependencies(document: dict, side: str, roots: set[str],
                  expressions: list[dict]) -> tuple[set[str], set[str]]:
    """Iterative dependency walk; model/context expressions have global IDs."""
    representation = document["representations"][side]
    relations = unique_index(representation["relations"], "relation_id")
    entities = unique_index(representation["entities"], "entity_id")
    domains = unique_index(representation["domains"], "domain_id")
    seen, used_entities = set(), set()
    pending, nodes = list(roots), list(expressions)
    while pending or nodes:
        if pending:
            key = pending.pop()
            if key in seen:
                continue
            seen.add(key)
            row = relations[key]
            if row["speaker_entity_id"] is not None:
                used_entities.add(row["speaker_entity_id"])
            nodes.append(row["expression"])
        while nodes:
            node = nodes.pop()
            op = node["op"]
            if op == "ATOM":
                for argument in node["arguments"]:
                    value = argument["value"]
                    if value.get("entity_id") in entities:
                        used_entities.add(value["entity_id"])
                    elif value.get("relation_id") in relations:
                        pending.append(value["relation_id"])
            elif op == "REF" and node["relation_id"] in relations:
                pending.append(node["relation_id"])
            elif op in ("FORALL", "EXISTS"):
                if node["domain_id"] in domains:
                    used_entities.update(domains[node["domain_id"]]["entity_ids"])
                nodes.append(node["body"])
            elif op == "CONTEXT":
                if node["speaker_entity_id"] in entities:
                    used_entities.add(node["speaker_entity_id"])
                nodes.append(node["body"])
            elif op == "NOT":
                nodes.append(node["operand"])
            elif op in ("AND", "OR"):
                nodes.extend(node["operands"])
            elif op == "IMPLIES":
                nodes.extend((node["antecedent"], node["consequent"]))
    return seen, used_entities


def _scope_requirements(document: dict, target_id: str, model: dict | None) -> tuple[set, set]:
    target = _target(document, target_id)
    variants = document["interpretations"]["variants"]
    expressions = [node for variant in variants for node in variant["context_constraints"]]
    anchor_ids = set()
    if model is not None:
        expressions.extend(row["expression"] for row in model["claims"])
        anchor_ids.update(key for row in model["claims"] for key in row["source_anchor_ids"])
    groups = {side: unique_index(document["representations"][side]["groups"], "group_id")
              for side in _SIDES}

    def expand(side: str, identifiers) -> set:
        return {relation for key in identifiers
                for relation in groups[side].get(key, {"relation_ids": [key]})["relation_ids"]}

    dependencies = {}
    for side in _SIDES:
        roots = expand(side, target[f"{side}_ids"])
        if side == "after" and not roots:
            roots.update(key for variant in variants for key in variant["after_relation_ids"])
        dependencies[side] = _dependencies(document, side, roots, expressions)
    selected = set()
    declared = {key for variant in variants for key in variant["correspondence_ids"]}
    for row in document["correspondence"]:
        if row["correspondence_id"] not in declared:
            continue
        position = 1 if row["kind"] in ("entity", "event") else 0
        if any((set(row[f"{side}_ids"]) if position else expand(side, row[f"{side}_ids"]))
               & dependencies[side][position] for side in _SIDES):
            selected.add(row["correspondence_id"])
    context = set(relevant_context_ids(
        document, target_id, sorted(selected),
        relation_ids_by_side={side: sorted(dependencies[side][0]) for side in _SIDES}))
    for side in _SIDES:
        entities = unique_index(document["representations"][side]["entities"], "entity_id")
        anchor_ids.update(key for identifier in dependencies[side][1]
                          for key in entities[identifier]["anchor_ids"])
    anchors = unique_index(document["source_anchors"], "anchor_id")
    context_sources = {row["source_id"] for row in document["sources"] if row["role"] == "context"}
    context.update(anchors[key]["source_id"] for key in anchor_ids
                   if anchors[key]["source_id"] in context_sources)
    return context, selected


@dataclass
class ImpactTrust:
    reviews: dict = field(default_factory=dict)
    observations: dict = field(default_factory=dict)
    config_pin: str | None = None
    payload_pins: dict = field(default_factory=dict)

    @property
    def config_sha256(self) -> str | None:
        return self.config_pin.removeprefix("impact-trust.sha256:") if self.config_pin else None

    @property
    def evidence_pins(self) -> list[dict]:
        """Stable content provenance without external filesystem locations."""
        rows = []
        for kind, version, records in (("review", REVIEW_VERSION, self.reviews),
                                        ("observation", OBSERVATION_VERSION, self.observations)):
            for identifier in records:
                rows.append({"kind": kind, "artifact_id": identifier,
                             "content_sha256": self.payload_pins[(version, identifier)].removeprefix("sha256:")})
        return sorted(rows, key=lambda row: (row["kind"], row["artifact_id"]))

    @classmethod
    def load(cls, config_path: Path | None, package_root: Path) -> "ImpactTrust":
        store = cls()
        if config_path is None:
            return store
        path = _external(Path(config_path), package_root)
        root = path.parent.resolve(strict=True)
        raw = safe_read(root, path.name)
        config = strict_json(raw)
        _validate(config)
        if config["schema_version"] != CONFIG_VERSION:
            raise InputError("expected an impact trust configuration")
        store.config_pin = "impact-trust.sha256:" + sha256(raw)
        kinds = (("review_files", REVIEW_VERSION, "verification_id", store.reviews),
                 ("observation_files", OBSERVATION_VERSION, "observation_id", store.observations))
        if sum(len(config[key]) for key, *_ in kinds) > 128:
            raise InputError("impact trust file limit exceeded")
        paths, subjects = set(), set()
        total = 0
        for list_key, version, id_key, destination in kinds:
            for reference in config[list_key]:
                parts = relative_path(reference["path"])
                _external(root.joinpath(*parts), package_root)
                if reference["path"] in paths:
                    raise InputError("duplicate impact trust payload path")
                paths.add(reference["path"])
                raw = safe_read(root, reference["path"])
                total += len(raw)
                if total > 16 * 1024 * 1024:
                    raise InputError("impact trust total byte limit exceeded")
                if sha256(raw) != reference["content_sha256"]:
                    raise InputError(f"impact evidence digest mismatch: {reference['path']}")
                record = strict_json(raw)
                _validate(record)
                if record["schema_version"] != version:
                    raise InputError(f"wrong impact evidence record type in {list_key}")
                identifier = record[id_key]
                if identifier in destination:
                    raise InputError(f"duplicate impact {id_key}: {identifier}")
                if version == REVIEW_VERSION:
                    subject = (record["input_ref"]["artifact_id"], record["input_ref"]["content_sha256"],
                               record["profile_ref"]["profile_id"], record["profile_ref"]["content_sha256"],
                               record["target_id"])
                    if subject in subjects:
                        raise InputError("multiple impact reviews for one exact target subject")
                    subjects.add(subject)
                    unique_index(record["base_checks"], "claim_id")
                    unique_index(record["rule_checks"], "rule_id")
                    unique_index([record["scope_check"], *record["base_checks"], *record["rule_checks"]],
                                 "check_id")
                else:
                    unique_index(record["source_bindings"], "source_id")
                destination[identifier] = record
                store.payload_pins[(version, identifier)] = "sha256:" + sha256(raw)
        return store

    def target_review(self, document: dict, input_ref: dict, target_id: str, *,
                      variant_ids: list[str]) -> dict:
        """Resolve the explicit claim/event mapping for the exact target.

        Passing this review supplies accepted reference premises only.  The
        caller still establishes source acceptance, compatible complete joint
        interpretations, comparison closure, and (for events) processing capture.
        """
        _target(document, target_id)
        declared = {row["variant_id"] for row in document["interpretations"]["variants"]}
        if len(variant_ids) != len(set(variant_ids)) or set(variant_ids) != declared:
            raise InputError("impact review must retain the declared joint variant family")
        evidence = [self.config_pin] if self.config_pin else []
        matching = [row for row in self.reviews.values()
                    if row["target_id"] == target_id and row["input_ref"] == input_ref
                    and row["profile_ref"] == document["profile_ref"]]
        if not matching:
            stale = any(row["target_id"] == target_id for row in self.reviews.values())
            return _result("fail" if stale else "unresolved",
                           "impact review input/profile subject mismatch" if stale else
                           "impact review is not independently configured for this target",
                           evidence=evidence)
        record = matching[0]
        evidence.extend((record["verification_id"], self.payload_pins[(REVIEW_VERSION, record["verification_id"])]))
        failures = []
        if set(record["reviewed_variant_ids"]) != declared:
            failures.append(("fail", "impact review does not bind the declared joint variant family"))
        if not declared:
            failures.append(("unresolved", "impact review has no declared interpretation variant"))
        model = None
        base_ids, rule_ids = [], []
        if record["mode"] == "support":
            original = document["impact_model"]
            if original is None:
                failures.append(("fail", "support review has no input impact model"))
            elif record["model_ref"] != {"model_id": original["model_id"],
                                          "content_sha256": sha256(canonical_bytes(original))}:
                failures.append(("fail", "impact model identity/digest mismatch"))
            elif not set(record["claim_ids"]) <= set(original["target_claim_ids"]):
                failures.append(("fail", "impact review claim mapping is outside the declared model goals"))
            else:
                try:
                    model = _scoped_model(original, record["claim_ids"])
                except LogicProblem as exc:
                    failures.append(("unresolved", f"impact support scope is incomplete: {exc.code}: {exc.detail}"))
            if model is not None:
                base_ids = [row["claim_id"] for row in model["claims"] if row["is_base"]]
                rule_ids = [row["rule_id"] for row in model["rules"]]
                base_checks = unique_index(record["base_checks"], "claim_id")
                rule_checks = unique_index(record["rule_checks"], "rule_id")
                all_claims = unique_index(original["claims"], "claim_id")
                all_rules = unique_index(original["rules"], "rule_id")
                if (not set(base_checks) <= all_claims.keys() or not set(rule_checks) <= all_rules.keys()
                        or any(not all_claims[key]["is_base"] for key in base_checks if key in all_claims)):
                    failures.append(("fail", "impact review contains an unknown or nonbase check subject"))
                for identifier in sorted(base_ids):
                    _check(base_checks.get(identifier), f"base claim {identifier}", failures, evidence)
                for identifier in sorted(rule_ids):
                    check = rule_checks.get(identifier)
                    _check(check, f"support rule {identifier}", failures, evidence)
                    if check is not None and check["rule_basis_ref"] != all_rules[identifier]["rule_basis_ref"]:
                        failures.append(("fail", f"support rule reference identity mismatch: {identifier}"))
        required_context, required_correspondences = _scope_requirements(document, target_id, model)
        scope = record["scope_check"]
        _check(scope, "target/model scope review", failures, evidence)
        known_context = {row["source_id"] for row in document["sources"] if row["role"] == "context"}
        known_correspondences = {row["correspondence_id"] for row in document["correspondence"]}
        if (not set(scope["context_source_ids"]) <= known_context
                or not set(scope["correspondence_ids"]) <= known_correspondences):
            failures.append(("fail", "impact scope review contains an unresolved context/correspondence"))
        if not required_context <= set(scope["context_source_ids"]):
            failures.append(("fail", "impact scope review omits required target/model context"))
        if not required_correspondences <= set(scope["correspondence_ids"]):
            failures.append(("fail", "impact scope review omits required target/model correspondence"))
        observation = None
        if record["mode"] == "observed":
            observation = self._observation(document, input_ref, record, required_context,
                                            failures, evidence)
        outcome = "fail" if any(row[0] == "fail" for row in failures) else "unresolved" if failures else "pass"
        return _result(outcome, "; ".join(row[1] for row in failures) if failures else None,
                       record=record, model=model, evidence=evidence,
                       base_ids=base_ids if outcome == "pass" else [],
                       rule_ids=rule_ids if outcome == "pass" else [],
                       observation=observation if outcome == "pass" else None)

    def _observation(self, document: dict, input_ref: dict, review: dict,
                     required_context: set[str], failures: list, evidence: list) -> dict | None:
        reference = review["observation_ref"]
        observation = self.observations.get(reference["observation_id"])
        if observation is None:
            failures.append(("unresolved", "observation is not independently configured"))
            return None
        identifier = observation["observation_id"]
        evidence.extend((identifier, self.payload_pins[(OBSERVATION_VERSION, identifier)]))
        _check(observation["check"], "independent before/after observation", failures, evidence)
        for key, expected in {"input_ref": input_ref, "profile_ref": document["profile_ref"],
                              "target_id": review["target_id"], **reference}.items():
            if observation[key] != expected:
                failures.append(("fail", f"observation {key} subject mismatch"))
        if set(observation["reviewed_variant_ids"]) != set(review["reviewed_variant_ids"]):
            failures.append(("fail", "observation joint variant family mismatch"))
        binding = document["processing_binding"]
        if binding is None:
            failures.append(("unresolved", "observed consequence has no processing-instance binding"))
            return observation
        if observation["processing_id"] != binding["processing_id"]:
            failures.append(("fail", "observation processing instance mismatch"))
        if not required_context <= set(binding["context_source_ids"]):
            failures.append(("fail", "observed processing binding omits required target context"))
        ids = {binding["before_source_id"], binding["after_source_id"], *binding["context_source_ids"]}
        sources = unique_index(document["sources"], "source_id")
        expected = [{key: sources[source_id][key] for key in _SOURCE_FIELDS} for source_id in sorted(ids)]
        if sorted(observation["source_bindings"], key=lambda row: row["source_id"]) != expected:
            failures.append(("fail", "observation source/context instance mismatch"))
        return observation
