"""Bounded grounded support over explicitly admitted LRM claim/rule records.

This module evaluates an already selected finite model.  Submitted base flags,
source anchors and evidence-reference strings never admit themselves: the caller
supplies the independently checked base and rule IDs and owns their claim scope.
Rules use positive, conjunctive claim membership, even when a claim's typed
expression contains NOT.  Conflict is reported without an explosion rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import product
from typing import Iterable

from .logic import LogicProblem


MAX_SUPPORT_CLAIMS = 256
MAX_SUPPORT_RULES = 256
MAX_SUPPORT_PATHS = 4096
MAX_SUPPORT_COMBINATIONS = 65536
MAX_SUPPORT_EXPRESSION_TOKENS = 16384


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise LogicProblem(code, detail)


def _index(rows: list[dict], key: str, limit: int) -> dict[str, dict]:
    _require(isinstance(rows, list), "support_model_shape", "Support records must be a list.")
    _require(len(rows) <= limit, "support_model_limit", "The support model exceeds its finite record bound.")
    result = {}
    for row in rows:
        _require(isinstance(row, dict) and isinstance(row.get(key), str) and bool(row[key]),
                 "support_model_shape", "A support record lacks its declared identifier.")
        identifier = row[key]
        _require(identifier not in result, "support_duplicate_identifier",
                 f"Duplicate support {key}: {identifier}")
        result[identifier] = row
    return result


def _ids(values: Iterable[str], known: dict[str, dict], label: str) -> set[str]:
    _require(not isinstance(values, (str, bytes)), "support_model_shape",
             f"The {label} must be an identifier collection.")
    try:
        selected = set(values)
    except TypeError as exc:
        raise LogicProblem("support_model_shape", f"The {label} is not an identifier collection.") from exc
    _require(all(isinstance(value, str) for value in selected), "support_model_shape",
             f"The {label} contains a non-string identifier.")
    _require(selected <= known.keys(), "support_unknown_identifier",
             f"The {label} names an unknown support record.")
    return selected


def _expression_key(expression: dict) -> tuple:
    """An exact, flat JSON-structure key; no semantic rewriting or REF expansion."""
    _require(isinstance(expression, dict), "support_expression_shape",
             "A support claim requires a structured expression.")
    tokens = []
    pending = [(False, expression)]
    while pending:
        literal, value = pending.pop()
        _require(len(tokens) < MAX_SUPPORT_EXPRESSION_TOKENS, "support_expression_limit",
                 "An exact support expression exceeds the finite token bound.")
        if literal:
            tokens.append(value)
        elif isinstance(value, dict):
            _require(len(value) <= MAX_SUPPORT_EXPRESSION_TOKENS, "support_expression_limit",
                     "A support expression object exceeds the finite token bound.")
            _require(all(isinstance(key, str) for key in value), "support_expression_shape",
                     "Expression object keys must be strings.")
            tokens.append(("object", len(value)))
            for key in sorted(value, reverse=True):
                pending.append((False, value[key]))
                pending.append((True, ("key", key)))
        elif isinstance(value, list):
            _require(len(value) <= MAX_SUPPORT_EXPRESSION_TOKENS, "support_expression_limit",
                     "A support expression list exceeds the finite token bound.")
            tokens.append(("array", len(value)))
            pending.extend((False, item) for item in reversed(value))
        elif value is None:
            tokens.append(("null", None))
        elif type(value) is bool:
            tokens.append(("boolean", value))
        elif type(value) is int:
            tokens.append(("integer", value))
        elif isinstance(value, str):
            tokens.append(("string", value))
        else:
            raise LogicProblem("support_expression_shape", "Unsupported support-expression value.")
    return tuple(tokens)


@dataclass(frozen=True)
class _Proof:
    bases: frozenset[str]
    rules: frozenset[str]
    claims: frozenset[str]

    def order_key(self) -> tuple:
        return tuple(sorted(self.bases)), tuple(sorted(self.rules)), tuple(sorted(self.claims))


def _unsupported_cycles(claims: dict[str, dict], rules: dict[str, dict],
                        grounded: set[str]) -> list[str]:
    """Return ungrounded members of admitted-rule SCCs, using iterative DFS.

    Pairwise arcs identify structural cycles only.  Actual support is computed
    separately with every conjunctive premise; reachability cannot ground a
    claim.  Unsupported tails outside a cyclic component are not cycle members.
    """
    forward: dict[str, set[str]] = {key: set() for key in claims}
    reverse: dict[str, set[str]] = {key: set() for key in claims}
    for rule in rules.values():
        conclusion = rule["conclusion_claim_id"]
        for premise in rule["premise_claim_ids"]:
            forward[premise].add(conclusion)
            reverse[conclusion].add(premise)
    visited, finished = set(), []
    for start in sorted(claims):
        if start in visited:
            continue
        pending = [(start, False)]
        while pending:
            node, leaving = pending.pop()
            if leaving:
                finished.append(node)
            elif node not in visited:
                visited.add(node)
                pending.append((node, True))
                pending.extend((child, False) for child in sorted(forward[node], reverse=True)
                               if child not in visited)
    visited.clear()
    unsupported = set()
    for start in reversed(finished):
        if start in visited:
            continue
        component = set()
        pending = [start]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            pending.extend(sorted(reverse[node] - visited, reverse=True))
        if len(component) > 1 or start in forward[start]:
            unsupported.update(component - grounded)
    return sorted(unsupported)


def _conflicts(claims: dict[str, dict], grounded: set[str]) -> list[dict]:
    by_expression: dict[tuple, list[str]] = {}
    for identifier in sorted(grounded):
        expression = claims[identifier].get("expression")
        by_expression.setdefault(_expression_key(expression), []).append(identifier)
    pairs = set()
    for identifier in sorted(grounded):
        expression = claims[identifier]["expression"]
        if expression.get("op") == "NOT":
            operand = _expression_key(expression.get("operand"))
            for opposed in by_expression.get(operand, []):
                pairs.add(tuple(sorted((identifier, opposed))))
    return [{"claim_id": left, "opposes_claim_id": right} for left, right in sorted(pairs)]


def grounded_closure(model: dict, *, admitted_base_claim_ids: Iterable[str],
                     admitted_rule_ids: Iterable[str],
                     withdrawn_claim_ids: Iterable[str] = ()) -> dict:
    """Recompute complete grounded closure from the supplied admitted records.

    A withdrawal removes a claim's direct base seed, not every possible proof
    of that claim.  Independent admitted rules may derive it again.  Distinct
    acyclic proof routes are preserved; repeating a claim within one derivation
    does not create another foundation.  Exhaustion raises LogicProblem before
    any partial closure is returned as a completed support record.

    The result conforms to the existing measurement artifact's support object.
    It does not assert source acceptance, event observation or release authority.
    """
    _require(isinstance(model, dict), "support_model_shape", "A support model must be an object.")
    claims = _index(model.get("claims"), "claim_id", MAX_SUPPORT_CLAIMS)
    all_rules = _index(model.get("rules"), "rule_id", MAX_SUPPORT_RULES)
    bases = _ids(admitted_base_claim_ids, claims, "admitted base set")
    selected_rules = _ids(admitted_rule_ids, all_rules, "admitted rule set")
    withdrawn = _ids(withdrawn_claim_ids, claims, "withdrawal set")
    _require(all(claims[key].get("is_base") is True for key in bases),
             "support_base_mismatch", "An admitted base must be declared as a base claim.")
    rules = {}
    for identifier in sorted(selected_rules):
        row = all_rules[identifier]
        premises = row.get("premise_claim_ids")
        _require(isinstance(premises, list) and bool(premises), "support_rule_shape",
                 "A support rule requires at least one conjunctive premise.")
        selected = _ids(premises, claims, "support rule premises")
        _require(len(selected) == len(premises), "support_rule_shape",
                 "A support rule repeats a conjunctive premise.")
        _require(row.get("conclusion_claim_id") in claims, "support_unknown_identifier",
                 "A support rule conclusion does not resolve.")
        rules[identifier] = {"premise_claim_ids": sorted(selected),
                             "conclusion_claim_id": row["conclusion_claim_id"]}

    proofs: dict[str, set[_Proof]] = {identifier: set() for identifier in claims}
    path_count = 0
    for identifier in sorted(bases - withdrawn):
        path_count += 1
        _require(path_count <= MAX_SUPPORT_PATHS, "support_path_limit",
                 "The complete alternative support paths exceed the finite bound.")
        proofs[identifier].add(_Proof(frozenset((identifier,)), frozenset(), frozenset((identifier,))))
    consumers: dict[str, set[str]] = {identifier: set() for identifier in claims}
    for identifier, rule in rules.items():
        for premise in rule["premise_claim_ids"]:
            consumers[premise].add(identifier)
    queued = {identifier for identifier, rule in rules.items()
              if all(proofs[premise] for premise in rule["premise_claim_ids"])}
    pending = sorted(queued)
    seen: dict[str, set[tuple[_Proof, ...]]] = {identifier: set() for identifier in rules}
    combinations = 0
    while pending:
        identifier = heappop(pending)
        queued.remove(identifier)
        rule = rules[identifier]
        conclusion = rule["conclusion_claim_id"]
        choices = [sorted(proofs[premise], key=_Proof.order_key) for premise in rule["premise_claim_ids"]]
        if any(not choice for choice in choices):
            continue
        changed = False
        for parents in product(*choices):
            combinations += 1
            _require(combinations <= MAX_SUPPORT_COMBINATIONS, "support_combination_limit",
                     "Support proof combinations exceed the finite evaluation bound.")
            if parents in seen[identifier]:
                continue
            seen[identifier].add(parents)
            used_claims = frozenset().union(*(parent.claims for parent in parents))
            if conclusion in used_claims:
                continue
            proof = _Proof(frozenset().union(*(parent.bases for parent in parents)),
                           frozenset((identifier,)).union(*(parent.rules for parent in parents)),
                           used_claims | {conclusion})
            if proof in proofs[conclusion]:
                continue
            path_count += 1
            _require(path_count <= MAX_SUPPORT_PATHS, "support_path_limit",
                     "The complete alternative support paths exceed the finite bound.")
            proofs[conclusion].add(proof)
            changed = True
        if changed:
            for consumer in sorted(consumers[conclusion]):
                if consumer not in queued:
                    heappush(pending, consumer)
                    queued.add(consumer)

    grounded = {identifier for identifier, routes in proofs.items() if routes}
    paths = []
    for identifier in sorted(grounded):
        for proof in sorted(proofs[identifier], key=_Proof.order_key):
            paths.append({"claim_id": identifier, "base_claim_ids": sorted(proof.bases),
                          "rule_ids": sorted(proof.rules)})
    return {"grounded_claim_ids": sorted(grounded),
            "unsupported_cycle_claim_ids": _unsupported_cycles(claims, rules, grounded),
            "conflicts": _conflicts(claims, grounded), "support_paths": paths,
            "recomputed_after_withdrawal": bool(withdrawn)}


def support_transition(model: dict, *, admitted_base_claim_ids: Iterable[str],
                       admitted_rule_ids: Iterable[str]) -> dict:
    """Compare fresh closures before and after the model's recorded withdrawal."""
    _require(not isinstance(admitted_base_claim_ids, (str, bytes))
             and not isinstance(admitted_rule_ids, (str, bytes)), "support_model_shape",
             "Admitted support IDs must be identifier collections.")
    bases, rules = tuple(admitted_base_claim_ids), tuple(admitted_rule_ids)
    before = grounded_closure(model, admitted_base_claim_ids=bases, admitted_rule_ids=rules)
    withdrawn = model.get("withdrawn_claim_ids", [])
    after = grounded_closure(model, admitted_base_claim_ids=bases, admitted_rule_ids=rules,
                             withdrawn_claim_ids=withdrawn)
    after["recomputed_after_withdrawal"] = True
    prior, current = set(before["grounded_claim_ids"]), set(after["grounded_claim_ids"])
    return {"before": before, "after": after, "withdrawn_claim_ids": sorted(set(withdrawn)),
            "lost_claim_ids": sorted(prior - current), "retained_claim_ids": sorted(prior & current)}
