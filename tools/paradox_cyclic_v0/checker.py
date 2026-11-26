"""Independently check bounded cyclic-model reports against their raw source.

Only JSON parsing and source admission are shared with the evaluator.  This
module reconstructs the selected subject's topology, checks every certificate
obligation against the admitted source, and derives the six judgments itself.
It neither imports the evaluator nor executes a candidate or a model program.
"""

from __future__ import annotations

from typing import Any

from .contract import (
    E,
    QUESTIONS,
    R,
    REPORT_FORMAT,
    SEMANTICS,
    U,
    VERIFY_FORMAT,
    CyclicError,
    admit_bundle,
    digest,
    parse_json_bytes,
)


_HEADER_KEYS = frozenset(
    {
        "format",
        "evaluation_status",
        "semantics",
        "input_sha256",
        "source_baseline",
        "authority_effect",
        "production_gate_eligible",
        "cases",
    }
)
_CERTIFICATE_KEYS = frozenset(
    {
        "direct_rule_ids",
        "displayed_route_rule_ids",
        "displayed_route_before_rule_ids",
        "mode_walk_rule_ids",
        "mode_walk_stop",
        "counter_increment",
        "projection",
        "repeatability",
    }
)
_PROJECTION_KEYS = frozenset(
    {"mode", "rule_id", "kind", "true_counter", "false_counter"}
)
_REPEAT_KEYS = frozenset({"rule_id", "offset", "period", "kind", "counter"})


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CyclicError(code, kind="REPORT_REJECTED")


def _keys(value: Any, expected: frozenset[str], code: str) -> None:
    _require(type(value) is dict, code)
    _require(set(value) == expected, code)


def _same(value: Any, expected: Any, code: str) -> None:
    # Equality alone admits True as the integer 1 and False as the integer 0.
    _require(type(value) is type(expected) and value == expected, code)


def _list_size(value: Any, length: int, code: str) -> None:
    _require(type(value) is list, code)
    _require(len(value) == length, code)


def _optional_counter(value: Any, code: str) -> None:
    _require(value is None or (type(value) is int and value >= 0), code)


def _conjunction(judgments: list[str]) -> str:
    if R in judgments:
        return R
    if U in judgments:
        return U
    return E


def _selected_rules(case: dict[str, Any], phase: str) -> dict[str, dict[str, Any]]:
    selected = case["query"]["selected_subject_id"]
    # Source admission guarantees the deterministic per-subject/per-mode rule
    # inventory.  Rules for other subjects cannot supply a missing edge.
    return {
        rule["from_mode"]: rule
        for rule in case[phase]["rules"]
        if rule["subject_id"] == selected
    }


def _fact_inventory(
    case: dict[str, Any],
) -> dict[str, dict[tuple[str, str, int], bool]]:
    return {
        declaration["predicate_id"]: {
            (
                fact["state"]["subject_id"],
                fact["state"]["mode"],
                fact["state"]["counter"],
            ): fact["value"]
            for fact in declaration["facts"]
        }
        for declaration in case["predicate_declarations"]
    }


def _guard_judgment(
    rule: dict[str, Any],
    counter: int,
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> str:
    guard = rule["guard"]
    if guard["kind"] == "unconditional":
        return E
    if guard["kind"] == "counter_below":
        return E if counter < guard["limit"] else R
    state = (rule["subject_id"], rule["from_mode"], counter)
    value = facts[guard["predicate_id"]].get(state)
    if value is True:
        return E
    if value is False:
        return R
    return U


def _fact_counters(
    rule: dict[str, Any],
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> tuple[set[int], set[int]]:
    supplied_true: set[int] = set()
    supplied_false: set[int] = set()
    for (subject, mode, counter), value in facts[rule["guard"]["predicate_id"]].items():
        if subject == rule["subject_id"] and mode == rule["from_mode"]:
            (supplied_true if value else supplied_false).add(counter)
    return supplied_true, supplied_false


def _check_direct(
    case: dict[str, Any],
    certificate: dict[str, Any],
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> str:
    record = certificate["direct_rule_ids"]
    _keys(record, frozenset({"before", "after"}), "DIRECT_KEYS")
    initial = case["query"]["initial_state"]["mode"]
    failure = case["failure_condition"]["mode_equals"]
    identities: dict[str, str | None] = {}
    for phase, inventory in (("before", before), ("after", after)):
        rule = inventory.get(initial)
        identity = rule["rule_id"] if rule and rule["to_mode"] == failure else None
        _same(record[phase], identity, "DIRECT_SOURCE_MISMATCH")
        identities[phase] = identity
    return E if identities["before"] is not None and identities["after"] is None else R


def _check_displayed_route(
    case: dict[str, Any],
    certificate: dict[str, Any],
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> str:
    query = case["query"]
    route = query["displayed_new_failure_route_modes"]
    proof = certificate["displayed_route_rule_ids"]
    _list_size(proof, len(route) - 1, "DISPLAYED_ROUTE_LENGTH")
    before_proof = certificate["displayed_route_before_rule_ids"]
    _list_size(before_proof, len(route) - 1, "DISPLAYED_ROUTE_BEFORE_LENGTH")
    start_counter = query["initial_state"]["counter"]
    judgments: list[str] = []
    for position in range(len(route) - 1):
        previous_rule = before.get(route[position])
        previous_identity = (
            previous_rule["rule_id"]
            if previous_rule is not None and previous_rule["to_mode"] == route[position + 1]
            else None
        )
        _same(
            before_proof[position], previous_identity, "DISPLAYED_ROUTE_BEFORE_SOURCE_MISMATCH"
        )
        rule = after.get(route[position])
        if rule is None or rule["to_mode"] != route[position + 1]:
            _same(proof[position], None, "DISPLAYED_ROUTE_SOURCE_MISMATCH")
            judgments.append(R)
        else:
            _same(proof[position], rule["rule_id"], "DISPLAYED_ROUTE_SOURCE_MISMATCH")
            judgments.append(_guard_judgment(rule, start_counter + position, facts))
    # Every conjunct is inspected: a later known-false guard refutes a route
    # even when a preceding predicate fact is unknown.
    return _conjunction(judgments)


def _check_structural_walk(
    case: dict[str, Any],
    certificate: dict[str, Any],
    after: dict[str, dict[str, Any]],
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> tuple[list[dict[str, Any]], bool, str]:
    query = case["query"]
    initial = query["initial_state"]["mode"]
    mode = initial
    visited: set[str] = set()
    word: list[dict[str, Any]] = []
    while mode not in visited:
        visited.add(mode)
        rule = after.get(mode)
        if rule is None:
            stop_kind = "terminal"
            break
        word.append(rule)
        mode = rule["to_mode"]
    else:
        stop_kind = "return" if mode == initial else "other_cycle"

    proof = certificate["mode_walk_rule_ids"]
    _list_size(proof, len(word), "MODE_WALK_LENGTH")
    for identity, rule in zip(proof, word):
        _same(identity, rule["rule_id"], "MODE_WALK_SOURCE_MISMATCH")
    stop = certificate["mode_walk_stop"]
    _keys(stop, frozenset({"kind", "mode"}), "MODE_WALK_STOP_KEYS")
    _same(stop["kind"], stop_kind, "MODE_WALK_STOP_MISMATCH")
    _same(stop["mode"], mode, "MODE_WALK_STOP_MISMATCH")

    returns_through_failure = (
        stop_kind == "return" and case["failure_condition"]["mode_equals"] in visited
    )
    if not returns_through_failure:
        return word, False, R
    start_counter = query["initial_state"]["counter"]
    guards = [
        _guard_judgment(rule, start_counter + offset, facts)
        for offset, rule in enumerate(word)
    ]
    return word, True, _conjunction(guards)


def _check_projection(
    case: dict[str, Any],
    certificate: dict[str, Any],
    after: dict[str, dict[str, Any]],
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> str:
    modes = set(case["domain"]["modes"])
    proof = certificate["projection"]
    _list_size(proof, len(modes), "PROJECTION_LENGTH")
    seen: set[str] = set()
    judgments: list[str] = []
    for row in proof:
        _keys(row, _PROJECTION_KEYS, "PROJECTION_KEYS")
        mode = row["mode"]
        _require(type(mode) is str, "PROJECTION_MODE_TYPE")
        _require(mode in modes and mode not in seen, "PROJECTION_MODE_INVENTORY")
        seen.add(mode)
        rule = after.get(mode)
        _same(row["rule_id"], rule["rule_id"] if rule else None, "PROJECTION_SOURCE")
        true_counter, false_counter = row["true_counter"], row["false_counter"]
        _optional_counter(true_counter, "PROJECTION_COUNTER_TYPE")
        _optional_counter(false_counter, "PROJECTION_COUNTER_TYPE")

        if rule is None:
            _same(row["kind"], "absent", "PROJECTION_KIND")
            _same(true_counter, None, "PROJECTION_ABSENT_WITNESS")
            _same(false_counter, 0, "PROJECTION_ABSENT_WITNESS")
            judgments.append(E)
            continue

        guard = rule["guard"]
        if guard["kind"] == "unconditional":
            _same(row["kind"], "unconditional", "PROJECTION_KIND")
            _same(true_counter, 0, "PROJECTION_UNCONDITIONAL_WITNESS")
            _same(false_counter, None, "PROJECTION_UNCONDITIONAL_WITNESS")
            judgments.append(E)
        elif guard["kind"] == "counter_below":
            limit = guard["limit"]
            if limit == 0:
                _same(row["kind"], "zero_limit", "PROJECTION_KIND")
                _same(true_counter, None, "PROJECTION_ZERO_WITNESS")
                _same(false_counter, 0, "PROJECTION_ZERO_WITNESS")
                judgments.append(E)
            else:
                _same(row["kind"], "finite_limit", "PROJECTION_KIND")
                _require(
                    true_counter is not None and false_counter is not None,
                    "PROJECTION_LIMIT_WITNESS",
                )
                _require(true_counter < limit <= false_counter, "PROJECTION_LIMIT_WITNESS")
                judgments.append(R)
        else:
            supplied_true, supplied_false = _fact_counters(rule, facts)
            conflict = bool(supplied_true and supplied_false)
            _same(
                row["kind"],
                "predicate_conflict" if conflict else "predicate_unfixed",
                "PROJECTION_KIND",
            )
            for witness, inventory in (
                (true_counter, supplied_true),
                (false_counter, supplied_false),
            ):
                if inventory:
                    _require(witness is not None and witness in inventory, "PROJECTION_FACT")
                else:
                    _same(witness, None, "PROJECTION_FACT")
            judgments.append(R if conflict else U)

    # Length and uniqueness already imply coverage; keep the coverage check
    # explicit so future certificate changes cannot weaken this obligation.
    _require(seen == modes, "PROJECTION_MODE_INVENTORY")
    return _conjunction(judgments)


def _on_progression(counter: int, start: int, period: int) -> bool:
    return counter >= start and (counter - start) % period == 0


def _check_repeatability(
    case: dict[str, Any],
    certificate: dict[str, Any],
    word: list[dict[str, Any]],
    returns_through_failure: bool,
    facts: dict[str, dict[tuple[str, str, int], bool]],
) -> str:
    proof = certificate["repeatability"]
    if not returns_through_failure:
        _list_size(proof, 0, "REPEATABILITY_TOPOLOGY")
        return R

    period = len(word)
    _list_size(proof, period, "REPEATABILITY_LENGTH")
    initial_counter = case["query"]["initial_state"]["counter"]
    judgments: list[str] = []
    for offset, (row, rule) in enumerate(zip(proof, word)):
        _keys(row, _REPEAT_KEYS, "REPEATABILITY_KEYS")
        _same(row["rule_id"], rule["rule_id"], "REPEATABILITY_SOURCE")
        _same(row["offset"], offset, "REPEATABILITY_OFFSET")
        _same(row["period"], period, "REPEATABILITY_PERIOD")
        counter = row["counter"]
        _optional_counter(counter, "REPEATABILITY_COUNTER_TYPE")
        start = initial_counter + offset
        guard = rule["guard"]
        if guard["kind"] == "unconditional":
            _same(row["kind"], "unconditional", "REPEATABILITY_KIND")
            _same(counter, None, "REPEATABILITY_UNCONDITIONAL_WITNESS")
            judgments.append(E)
        elif guard["kind"] == "counter_below":
            _same(row["kind"], "finite_limit", "REPEATABILITY_KIND")
            _require(counter is not None, "REPEATABILITY_LIMIT_WITNESS")
            _require(
                counter >= guard["limit"] and _on_progression(counter, start, period),
                "REPEATABILITY_LIMIT_WITNESS",
            )
            judgments.append(R)
        else:
            _, supplied_false = _fact_counters(rule, facts)
            counterexamples = {
                value for value in supplied_false if _on_progression(value, start, period)
            }
            if counterexamples:
                _same(row["kind"], "predicate_false", "REPEATABILITY_KIND")
                _require(
                    counter is not None and counter in counterexamples,
                    "REPEATABILITY_FALSE_FACT",
                )
                judgments.append(R)
            else:
                _same(row["kind"], "predicate_unfixed", "REPEATABILITY_KIND")
                _same(counter, None, "REPEATABILITY_UNFIXED_WITNESS")
                judgments.append(U)
    return _conjunction(judgments)


def _check_case(case: dict[str, Any], record: dict[str, Any]) -> None:
    _keys(record, frozenset({"case_id", "claims", "certificate"}), "CASE_KEYS")
    _same(record["case_id"], case["case_id"], "CASE_ID_MISMATCH")
    certificate = record["certificate"]
    _keys(certificate, _CERTIFICATE_KEYS, "CERTIFICATE_KEYS")
    _same(certificate["counter_increment"], 1, "COUNTER_INCREMENT_INVARIANT")
    before = _selected_rules(case, "before")
    after = _selected_rules(case, "after")
    facts = _fact_inventory(case)

    direct = _check_direct(case, certificate, before, after)
    displayed = _check_displayed_route(case, certificate, before, after, facts)
    word, returns_through_failure, mode_return = _check_structural_walk(
        case, certificate, after, facts
    )
    projection = _check_projection(case, certificate, after, facts)
    repeatability = _check_repeatability(
        case, certificate, word, returns_through_failure, facts
    )
    # Every admitted transition preserves the subject and adds one to the
    # counter, so every nonempty path has strictly larger final counter.
    derived = {
        "direct_route_removed": direct,
        "new_failure_route_feasible": displayed,
        "failure_then_mode_return": mode_return,
        "complete_state_return": R,
        "counter_projection_sound": projection,
        "repeatable_structural_return": repeatability,
    }
    claims = record["claims"]
    _keys(claims, frozenset(QUESTIONS), "CLAIM_KEYS")
    for question in QUESTIONS:
        _same(claims[question], derived[question], "CLAIM_NOT_JUSTIFIED")


def verify_bytes(input_raw: bytes, report_raw: bytes) -> dict[str, Any]:
    """Verify a complete report against the exact admitted input byte string.

    Input errors retain INPUT_INVALID/INPUT_UNSUPPORTED.  All report parsing,
    binding, inventory, witness and judgment failures are REPORT_REJECTED.
    A VERIFIED result is local model proof consistency, not external attestation.
    """
    bundle = admit_bundle(input_raw)
    try:
        report = parse_json_bytes(report_raw)
    except CyclicError as error:
        raise CyclicError("REPORT_JSON_REJECTED", kind="REPORT_REJECTED") from error

    _keys(report, _HEADER_KEYS, "REPORT_KEYS")
    _same(report["format"], REPORT_FORMAT, "REPORT_FORMAT")
    _same(report["evaluation_status"], "COMPLETED", "REPORT_STATUS")
    _same(report["semantics"], SEMANTICS, "REPORT_SEMANTICS")
    input_sha256 = digest(input_raw)
    _same(report["input_sha256"], input_sha256, "INPUT_DIGEST_MISMATCH")
    _same(report["source_baseline"], bundle["source_baseline"], "SOURCE_BASELINE_MISMATCH")
    _same(report["authority_effect"], "none", "REPORT_AUTHORITY")
    _same(report["production_gate_eligible"], False, "REPORT_AUTHORITY")

    sources = {case["case_id"]: case for case in bundle["cases"]}
    records = report["cases"]
    _list_size(records, len(sources), "CASE_INVENTORY_LENGTH")
    checked: set[str] = set()
    for record in records:
        _keys(record, frozenset({"case_id", "claims", "certificate"}), "CASE_KEYS")
        identity = record["case_id"]
        _require(type(identity) is str, "CASE_ID_TYPE")
        _require(identity in sources and identity not in checked, "CASE_INVENTORY")
        _check_case(sources[identity], record)
        checked.add(identity)
    _require(checked == set(sources), "CASE_INVENTORY")

    return {
        "format": VERIFY_FORMAT,
        "verification_status": "VERIFIED",
        "semantics": SEMANTICS,
        "input_sha256": input_sha256,
        "report_sha256": digest(report_raw),
        "checked_cases": len(checked),
        "checked_claims": len(checked) * len(QUESTIONS),
        "authority_effect": "none",
        "production_gate_eligible": False,
    }
