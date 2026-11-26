"""Evaluate the admitted deterministic cyclic-case profile.

The walk recorded here is a structural proposal.  Its construction does not
execute rules or turn unknown predicate facts into evidence of execution.
Repeated traversal is assessed parametrically, never by bounded sampling.
"""

from __future__ import annotations

from typing import Any, Iterable

from .contract import (
    E,
    R,
    U,
    QUESTIONS,
    REPORT_FORMAT,
    SEMANTICS,
    admit_bundle,
    digest,
)


_Rule = dict[str, Any]
_FactIndex = dict[tuple[str, str, str], dict[int, bool]]


def _facts_by_state(case: dict[str, Any]) -> _FactIndex:
    """Index only the finite facts actually supplied in the admitted input."""
    index: _FactIndex = {}
    for declaration in case["predicate_declarations"]:
        predicate = declaration["predicate_id"]
        for fact in declaration["facts"]:
            state = fact["state"]
            key = (predicate, state["subject_id"], state["mode"])
            index.setdefault(key, {})[state["counter"]] = fact["value"]
    return index


def _rule_facts(rule: _Rule, facts: _FactIndex) -> dict[int, bool]:
    key = (
        rule["guard"]["predicate_id"],
        rule["subject_id"],
        rule["from_mode"],
    )
    return facts.get(key, {})


def _guard_value(rule: _Rule, counter: int, facts: _FactIndex) -> bool | None:
    guard = rule["guard"]
    if guard["kind"] == "unconditional":
        return True
    if guard["kind"] == "counter_below":
        return counter < guard["limit"]
    # Admission restricts the remaining alternative to a declared predicate.
    return _rule_facts(rule, facts).get(counter)


def _conjunction(values: Iterable[bool | None]) -> str:
    unknown = False
    for value in values:
        if value is False:
            return R
        if value is None:
            unknown = True
    return U if unknown else E


def _combine_claims(values: Iterable[str]) -> str:
    unknown = False
    for value in values:
        if value == R:
            return R
        if value == U:
            unknown = True
    return U if unknown else E


def _structural_walk(
    rules: dict[str, _Rule], initial_mode: str
) -> tuple[list[_Rule], dict[str, str]]:
    """Follow the partial mode function until a terminal or first repetition."""
    visited: set[str] = set()
    word: list[_Rule] = []
    mode = initial_mode
    while mode not in visited:
        visited.add(mode)
        rule = rules.get(mode)
        if rule is None:
            return word, {"kind": "terminal", "mode": mode}
        word.append(rule)
        mode = rule["to_mode"]
    kind = "return" if mode == initial_mode else "other_cycle"
    return word, {"kind": kind, "mode": mode}


def _projection_obligation(
    mode: str, rule: _Rule | None, facts: _FactIndex
) -> tuple[dict[str, Any], str]:
    obligation: dict[str, Any] = {
        "mode": mode,
        "rule_id": None if rule is None else rule["rule_id"],
        "kind": "absent",
        "true_counter": None,
        "false_counter": 0,
    }
    if rule is None:
        return obligation, E

    guard = rule["guard"]
    if guard["kind"] == "unconditional":
        obligation.update(kind="unconditional", true_counter=0, false_counter=None)
        return obligation, E
    if guard["kind"] == "counter_below":
        limit = guard["limit"]
        if limit == 0:
            obligation["kind"] = "zero_limit"
            return obligation, E
        obligation.update(kind="finite_limit", true_counter=0, false_counter=limit)
        return obligation, R

    supplied = _rule_facts(rule, facts)
    true_counter = min((n for n, value in supplied.items() if value is True), default=None)
    false_counter = min((n for n, value in supplied.items() if value is False), default=None)
    conflict = true_counter is not None and false_counter is not None
    obligation.update(
        kind="predicate_conflict" if conflict else "predicate_unfixed",
        true_counter=true_counter,
        false_counter=false_counter,
    )
    return obligation, R if conflict else U


def _repeatability_obligation(
    rule: _Rule, offset: int, period: int, initial_counter: int, facts: _FactIndex
) -> tuple[dict[str, Any], str]:
    obligation: dict[str, Any] = {
        "rule_id": rule["rule_id"],
        "offset": offset,
        "period": period,
        "kind": "unconditional",
        "counter": None,
    }
    guard = rule["guard"]
    if guard["kind"] == "unconditional":
        return obligation, E

    first = initial_counter + offset
    if guard["kind"] == "counter_below":
        # The strict +1 invariant gives this exact arithmetic progression.
        # A finite limit has a finite blocking position even if it is distant.
        distance = max(0, guard["limit"] - first)
        repetitions = (distance + period - 1) // period
        obligation.update(kind="finite_limit", counter=first + repetitions * period)
        return obligation, R

    blocking_counter = min(
        (
            counter
            for counter, value in _rule_facts(rule, facts).items()
            if value is False
            and counter >= first
            and (counter - first) % period == 0
        ),
        default=None,
    )
    if blocking_counter is not None:
        obligation.update(kind="predicate_false", counter=blocking_counter)
        return obligation, R
    # Finite supplied facts cannot fix an infinite progression of predicate
    # values.  A false fact outside this progression does not refute this word.
    obligation["kind"] = "predicate_unfixed"
    return obligation, U


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    query = case["query"]
    subject = query["selected_subject_id"]
    initial_mode = query["initial_state"]["mode"]
    initial_counter = query["initial_state"]["counter"]
    failure_mode = case["failure_condition"]["mode_equals"]
    facts = _facts_by_state(case)
    phase_rules = {
        phase: {
            rule["from_mode"]: rule
            for rule in case[phase]["rules"]
            if rule["subject_id"] == subject
        }
        for phase in ("before", "after")
    }
    after = phase_rules["after"]

    direct_ids: dict[str, str | None] = {}
    for phase in ("before", "after"):
        rule = phase_rules[phase].get(initial_mode)
        direct_ids[phase] = (
            rule["rule_id"]
            if rule is not None and rule["to_mode"] == failure_mode
            else None
        )
    direct_removed = E if direct_ids["before"] is not None and direct_ids["after"] is None else R

    route_modes = query["displayed_new_failure_route_modes"]
    route_ids: list[str | None] = []
    route_before_ids: list[str | None] = []
    route_guards: list[bool | None] = []
    for offset, (source, target) in enumerate(zip(route_modes, route_modes[1:])):
        before_rule = phase_rules["before"].get(source)
        route_before_ids.append(
            before_rule["rule_id"]
            if before_rule is not None and before_rule["to_mode"] == target
            else None
        )
        rule = after.get(source)
        if rule is None or rule["to_mode"] != target:
            route_ids.append(None)
            route_guards.append(False)
        else:
            route_ids.append(rule["rule_id"])
            route_guards.append(_guard_value(rule, initial_counter + offset, facts))
    # Evaluate all positions before reducing: an earlier unknown cannot hide a
    # later definite blocker or a missing structural edge.
    route_feasible = _conjunction(route_guards)

    word, stop = _structural_walk(after, initial_mode)
    returns_through_failure = stop["kind"] == "return" and any(
        rule["from_mode"] == failure_mode for rule in word
    )
    failure_return = R
    if returns_through_failure:
        word_guards = [
            _guard_value(rule, initial_counter + offset, facts)
            for offset, rule in enumerate(word)
        ]
        failure_return = _conjunction(word_guards)

    projection = []
    projection_claims = []
    for mode in case["domain"]["modes"]:
        obligation, claim = _projection_obligation(mode, after.get(mode), facts)
        projection.append(obligation)
        projection_claims.append(claim)

    repeatability = []
    repeatability_claim = R
    if returns_through_failure:
        repetition_claims = []
        period = len(word)
        for offset, rule in enumerate(word):
            obligation, claim = _repeatability_obligation(
                rule, offset, period, initial_counter, facts
            )
            repeatability.append(obligation)
            repetition_claims.append(claim)
        repeatability_claim = _combine_claims(repetition_claims)

    verdicts = (
        direct_removed,
        route_feasible,
        failure_return,
        R,  # Any nonempty admitted word strictly increases the complete counter.
        _combine_claims(projection_claims),
        repeatability_claim,
    )
    return {
        "case_id": case["case_id"],
        "claims": dict(zip(QUESTIONS, verdicts, strict=True)),
        "certificate": {
            "direct_rule_ids": direct_ids,
            "displayed_route_rule_ids": route_ids,
            "displayed_route_before_rule_ids": route_before_ids,
            "mode_walk_rule_ids": [rule["rule_id"] for rule in word],
            "mode_walk_stop": stop,
            "counter_increment": 1,
            "projection": projection,
            "repeatability": repeatability,
        },
    }


def evaluate_bytes(input_raw: bytes) -> dict[str, Any]:
    """Admit exact input bytes and produce the six bounded model judgments."""
    bundle = admit_bundle(input_raw)
    return {
        "format": REPORT_FORMAT,
        "evaluation_status": "COMPLETED",
        "semantics": SEMANTICS,
        "input_sha256": digest(input_raw),
        "source_baseline": bundle["source_baseline"],
        "authority_effect": "none",
        "production_gate_eligible": False,
        "cases": [_evaluate_case(case) for case in bundle["cases"]],
    }
