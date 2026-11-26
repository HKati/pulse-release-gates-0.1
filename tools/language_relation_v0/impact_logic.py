"""Finite condition effects in one recorded variant and common configuration.

This module checks the supplied relation model only. It neither accepts source
meaning/evidence nor grants release authority. The caller must independently
close the applicable target, correspondence and coverage premises.

Condition satisfaction compares corresponding values in each configuration.
Joint possibility compares complete answer-vector sets, retaining the recorded
variant partitions. The two questions intentionally need not have one answer.
"""

from __future__ import annotations

from .comparator import _identity_gap, _relevant_correspondences
from .logic import LogicProblem, VariantLogic, _atoms, _truth, _tuple_key


MAX_CONDITION_TARGETS = 256
MAX_CONDITION_VARIANTS = 64
MAX_CONDITION_CONFIGURATIONS = 4096
MAX_CONDITION_EVALUATIONS = 1048576


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise LogicProblem(code, detail)


def _unresolved(target_ids: list[str], reason: str) -> dict:
    return {identifier: {"conclusion": "unresolved", "reason": reason}
            for identifier in target_ids}


def _projected_valuation(logic: VariantLogic, selected: dict,
                         configuration: dict, expected: tuple[bool, bool]) -> list[dict]:
    """Check the exact atom scope required by one target, including context."""
    projected = {key: configuration[key] for key in selected["atoms"]}
    valuation, complete = logic._valuation(projected)
    _require(complete and valuation is not None, "incomplete_condition_valuation",
             "A condition difference requires a complete, unambiguous named ground-ATOM valuation.")
    checked = logic.check_valuation(selected["before"], selected["after"], valuation)
    _require((checked["before_value"], checked["after_value"]) == expected,
             "condition_valuation_mismatch", "The named valuation does not reproduce the evaluated condition values.")
    return valuation


def _checked_group_valuation(logic: VariantLogic, selections: list[dict],
                             configuration: dict, nodes: dict) -> list[dict]:
    valuation, complete = logic._valuation(configuration)
    _require(complete and valuation is not None, "incomplete_joint_valuation",
             "A joint possibility difference requires aliases for every atom of its common configuration.")
    # Every target is checked as a projection of this very same configuration.
    # Unioning selected roots could duplicate an already-expanded helper and
    # consume extra AST budget; it is not needed to check the union of atoms.
    for selected in selections:
        expected = tuple(_truth(nodes[selected[side + "_key"]], configuration)
                         for side in ("before", "after"))
        _projected_valuation(logic, selected, configuration, expected)
    return valuation


def _evaluate_variant(document: dict, profile: dict, targets: list[dict],
                      variant: dict, evaluations: list[int]) -> dict:
    relevant = sorted({identifier for target in targets
                       for identifier in _relevant_correspondences(document, target, variant)})
    logic = VariantLogic(document, profile, variant, correspondence_ids=relevant)
    selections, nodes = [], {}
    context_atoms = _atoms(logic._ground_constraints)
    for target in targets:
        selection = {side: logic.selected(side, target) for side in ("before", "after")}
        _require(not any(row["embedded_only"] for row in selection.values()),
                 "embedded_condition_root",
                 f"Target {target['target_id']} selects a relation only inside an enclosing operator or context.")
        _require(not any(row["missing"] or not row["selected"] for row in selection.values()),
                 "missing_condition_root",
                 f"Target {target['target_id']} requires nonempty, fully conveyed roots on both sides.")
        selected = {"target_id": target["target_id"],
                    **{side: selection[side]["selected"] for side in ("before", "after")}}
        _require(not _identity_gap(logic, selected["before"], selected["after"]),
                 "unresolved_condition_identity",
                 f"Target {target['target_id']} has unresolved cross-source participant or proposition identity.")
        selected["atoms"] = set(context_atoms)
        for side in ("before", "after"):
            node = logic._ground(logic.roots(side, selected[side]))
            key = _tuple_key(node)
            nodes.setdefault(key, node)
            selected[side + "_key"] = key
            selected["atoms"].update(_atoms(node))
        selections.append(selected)

    before_configurations, after_configurations, first_differences = {}, {}, {}
    configuration_count = 0
    for configuration in logic._configurations(nodes.values()):
        configuration_count += 1
        _require(configuration_count <= MAX_CONDITION_CONFIGURATIONS,
                 "condition_configuration_limit", "A variant exceeds the 4096 common-configuration bound.")
        cost = 2 * len(selections)
        _require(evaluations[0] + cost <= MAX_CONDITION_EVALUATIONS,
                 "condition_evaluation_limit",
                 f"The condition evaluation exceeds the shared {MAX_CONDITION_EVALUATIONS} target-value budget.")
        evaluations[0] += cost
        # Canonically equal conditions share evaluation work, but remain
        # separate coordinates of the complete target answer vector.
        values = {key: _truth(node, configuration) for key, node in nodes.items()}
        before_vector = tuple(values[row["before_key"]] for row in selections)
        after_vector = tuple(values[row["after_key"]] for row in selections)
        before_configurations.setdefault(before_vector, configuration)
        after_configurations.setdefault(after_vector, configuration)
        for index, selected in enumerate(selections):
            if before_vector[index] != after_vector[index]:
                first_differences.setdefault(selected["target_id"], (
                    configuration, (before_vector[index], after_vector[index])))
    _require(configuration_count > 0, "incompatible_context",
             "The selected joint conditions admit no common context configuration.")

    per_target, counterexamples, failures = {}, {}, []
    for selected in selections:
        identifier = selected["target_id"]
        per_target[identifier] = {"conclusion": "preserved", "reason": None}
        if identifier not in first_differences:
            continue
        configuration, expected = first_differences[identifier]
        try:
            counterexamples[identifier] = _projected_valuation(logic, selected, configuration, expected)
            per_target[identifier]["conclusion"] = "changed"
        except LogicProblem as exc:
            per_target[identifier] = {"conclusion": "unresolved", "reason": exc.detail}
            failures.append({"target_id": identifier, "code": exc.code, "detail": exc.detail})

    before_vectors, after_vectors = set(before_configurations), set(after_configurations)
    joint_witness = None
    joint_conclusion, joint_reason = "preserved", None
    if before_vectors != after_vectors:
        side = "before" if before_vectors - after_vectors else "after"
        difference = before_vectors - after_vectors if side == "before" else after_vectors - before_vectors
        vector = min(difference)
        configurations = before_configurations if side == "before" else after_configurations
        try:
            valuation = _checked_group_valuation(logic, selections, configurations[vector], nodes)
            joint_witness = {"side": side, "vector": list(vector), "valuation": valuation}
            joint_conclusion = "changed"
        except LogicProblem as exc:
            joint_conclusion, joint_reason = "unresolved", exc.detail
            failures.append({"target_id": None, "code": exc.code, "detail": exc.detail})

    return {"variant_id": variant["variant_id"], "configuration_count": configuration_count,
            "selected_roots": {row["target_id"]: {"before_relation_ids": row["before"],
                                                   "after_relation_ids": row["after"]}
                               for row in selections},
            "before_vectors": [list(vector) for vector in sorted(before_vectors)],
            "after_vectors": [list(vector) for vector in sorted(after_vectors)],
            "changed_target_ids": sorted(identifier for identifier, row in per_target.items()
                                         if row["conclusion"] == "changed"),
            "counterexamples": counterexamples, "joint_witness": joint_witness,
            "per_target": per_target, "joint_conclusion": joint_conclusion,
            "joint_reason": joint_reason, "resources": dict(logic.resources), "failures": failures}


def evaluate_condition_group(document: dict, profile: dict, targets: list[dict], *,
                             _evaluation_budget: list[int] | None = None) -> dict:
    """Evaluate bounded model conditions, without accepting their evidence.

    Input/schema validity belongs to the caller. Target IDs and recorded variant
    IDs define deterministic output order. Each configuration is hypothetical;
    valuations are named relation aliases, never support-model claim IDs.

    A failed or incomplete variant prevents aggregate identification. A complete
    family containing only incompatible variants is incompatible, never vacuously
    preserved. Individual and joint conclusions aggregate separately; different
    conclusions across variant partitions remain unresolved.

    The optional private counter is shared by the caller's individual-target
    and joint-group calls. It counts additional condition target-value work,
    not source verification or preceding LRM-03 comparison. Reservations never
    exceed the bound; the returned count is this call's actual contribution.
    """
    targets = sorted(targets, key=lambda row: row["target_id"])
    target_ids = [row["target_id"] for row in targets]
    family = document["interpretations"]
    result = {"target_ids": target_ids, "state": "unresolved", "reason": None,
              "variants": [], "per_target": {}, "joint_conclusion": "unresolved",
              "joint_reason": None, "family_state": family["state"],
              "enumeration_complete": False, "failures": [],
              "limits": {"max_targets": MAX_CONDITION_TARGETS,
                         "max_joint_variants": MAX_CONDITION_VARIANTS,
                         "max_ast_nodes_per_variant": 256,
                         "max_expanded_boolean_atoms": 12,
                         "max_configurations_per_variant": MAX_CONDITION_CONFIGURATIONS,
                         "max_target_value_evaluations": MAX_CONDITION_EVALUATIONS},
              "target_value_evaluations": 0}

    def unresolved(reason: str) -> dict:
        result.update(reason=reason, joint_reason=reason,
                      per_target=_unresolved(target_ids, reason))
        return result

    if not targets:
        return unresolved("A condition group requires at least one explicit target.")
    if len(targets) > MAX_CONDITION_TARGETS:
        return unresolved("The condition group exceeds the 256-target bound.")
    if len(set(target_ids)) != len(target_ids):
        return unresolved("A condition group must not repeat a target identifier.")
    if family["state"] == "unknown":
        return unresolved("The interpretation family is unknown.")
    if family["state"] == "empty":
        result["state"] = "incompatible"
        return unresolved("The declared interpretation family is empty; no vacuous preservation follows.")

    variant_limit = min(MAX_CONDITION_VARIANTS, profile["limits"]["max_joint_variants"])
    declared_variants = sorted(family["variants"], key=lambda row: row["variant_id"])
    overflow = len(declared_variants) > variant_limit
    evaluations = [0] if _evaluation_budget is None else _evaluation_budget
    starting_evaluations = evaluations[0]
    for variant in declared_variants[:variant_limit]:
        if evaluations[0] >= MAX_CONDITION_EVALUATIONS:
            result["failures"].append({"variant_id": variant["variant_id"],
                                       "code": "condition_evaluation_limit",
                                       "detail": f"The shared {MAX_CONDITION_EVALUATIONS} target-value budget is exhausted."})
            break
        try:
            result["variants"].append(_evaluate_variant(document, profile, targets, variant, evaluations))
        except LogicProblem as exc:
            result["failures"].append({"variant_id": variant["variant_id"],
                                       "code": exc.code, "detail": exc.detail})
            if exc.code == "condition_evaluation_limit":
                break
        except RecursionError:
            result["failures"].append({"variant_id": variant["variant_id"],
                                       "code": "condition_recursion_limit",
                                       "detail": "The condition variant exceeds the supported cumulative recursion budget."})
    result["target_value_evaluations"] = evaluations[0] - starting_evaluations
    complete = family["state"] == "complete" and not overflow and not result["failures"] and bool(result["variants"])
    result["enumeration_complete"] = complete
    if not complete:
        if family["state"] == "complete" and not overflow and result["failures"] and not result["variants"] and all(
                row["code"] == "incompatible_context" for row in result["failures"]):
            result["state"] = "incompatible"
        reason = ("The interpretation family is truncated or exceeds the 64-variant bound."
                  if family["state"] == "truncated" or overflow else
                  "; ".join(row["detail"] for row in result["failures"]) or
                  "No nonempty admissible interpretation family was completely evaluated.")
        return unresolved(reason)

    for identifier in target_ids:
        rows = [variant["per_target"][identifier] for variant in result["variants"]]
        conclusions = {row["conclusion"] for row in rows}
        conclusion = next(iter(conclusions)) if len(conclusions) == 1 else "unresolved"
        reason = None if conclusion != "unresolved" else next(
            (row["reason"] for row in rows if row["reason"]),
            "The recorded joint variants give different condition-satisfaction conclusions.")
        result["per_target"][identifier] = {"conclusion": conclusion, "reason": reason}
    joint = {variant["joint_conclusion"] for variant in result["variants"]}
    result["joint_conclusion"] = next(iter(joint)) if len(joint) == 1 else "unresolved"
    if result["joint_conclusion"] == "unresolved":
        result["joint_reason"] = next((variant["joint_reason"] for variant in result["variants"]
                                       if variant["joint_reason"]),
                                      "The recorded joint variants give different joint-possibility conclusions.")
    reasons = [row["reason"] for row in result["per_target"].values() if row["conclusion"] == "unresolved"]
    if result["joint_reason"]:
        reasons.append(result["joint_reason"])
    if reasons:
        result["reason"] = "; ".join(dict.fromkeys(reasons))
    else:
        result["state"] = "identified"
    return result
