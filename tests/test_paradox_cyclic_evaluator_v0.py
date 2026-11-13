#!/usr/bin/env python3
"""Bounded model evaluation/checking regressions; no candidate execution.

The frozen expected file is consulted only by the reference comparison test.
Other cases have explicit, independently reasoned outcomes. Temporary CLI
trees deliberately contain no expected file, and the checker tree contains
no evaluator module. These are local model checks, not native observations.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.paradox_cyclic_v0 import checker, evaluator
from tools.paradox_cyclic_v0.contract import (
    CyclicError, E, R, U, QUESTIONS, REPORT_FORMAT, SEMANTICS, VERIFY_FORMAT,
    parse_json_bytes,
)


INPUT_PATH = ROOT / "examples/paradox_cyclic_case_v0/cases.json"
REFERENCE_PATH = ROOT / "examples/paradox_cyclic_case_v0/expected.json"
FROZEN_RAW = INPUT_PATH.read_bytes()
FROZEN = json.loads(FROZEN_RAW)
EXPECTED_QUESTIONS = (
    "direct_route_removed", "new_failure_route_feasible",
    "failure_then_mode_return", "complete_state_return",
    "counter_projection_sound", "repeatable_structural_return",
)
BASELINE = {
    "K00": (E, E, E, R, E, E),
    "K01": (E, E, E, R, R, R),
    "K02": (E, E, R, R, E, R),
    "K03": (E, R, R, R, E, R),
    "K04": (E, U, U, R, U, U),
}


def raw_json(value):
    """Test serialization is independent of the production encoder."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def single_case(index=0):
    bundle = copy.deepcopy(FROZEN)
    bundle["cases"] = [bundle["cases"][index]]
    bundle["cases"][0]["case_id"] = "Synthetic"
    return bundle


def selected_rule(case, mode, phase="after"):
    subject = case["query"]["selected_subject_id"]
    return next(rule for rule in case[phase]["rules"]
                if rule["subject_id"] == subject and rule["from_mode"] == mode)


def add_fact(case, counter, value, mode="B", subject=None):
    case["predicate_declarations"][0]["facts"].append({
        "state": {"subject_id": subject or case["query"]["selected_subject_id"],
                  "mode": mode, "counter": counter},
        "value": value,
    })


def set_path(value, path, replacement):
    current = value
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = replacement


class CyclicEvaluatorTests(unittest.TestCase):
    def checked(self, bundle):
        raw = raw_json(bundle)
        report = evaluator.evaluate_bytes(raw)
        verified = checker.verify_bytes(raw, raw_json(report))
        self.assertEqual(verified["verification_status"], "VERIFIED")
        self.assertEqual(verified["checked_cases"], len(bundle["cases"]))
        self.assertEqual(verified["checked_claims"], 6 * len(bundle["cases"]))
        self.assertEqual(report["authority_effect"], "none")
        self.assertIs(report["production_gate_eligible"], False)
        self.assertEqual(verified["authority_effect"], "none")
        self.assertIs(verified["production_gate_eligible"], False)
        return report

    def assert_claims(self, bundle, expected):
        result = self.checked(bundle)["cases"][0]
        self.assertEqual(set(result["claims"]), set(EXPECTED_QUESTIONS))
        self.assertEqual(tuple(result["claims"][q] for q in EXPECTED_QUESTIONS), expected)
        return result

    def reject_input(self, raw, kind="INPUT_INVALID"):
        for operation in (lambda: evaluator.evaluate_bytes(raw),
                          lambda: checker.verify_bytes(raw, b"{}")):
            with self.assertRaises(CyclicError) as caught:
                operation()
            self.assertEqual(caught.exception.kind, kind)
            self.assertTrue(caught.exception.code)

    def reject_report(self, raw, report):
        with self.assertRaises(CyclicError) as caught:
            checker.verify_bytes(raw, raw_json(report))
        self.assertEqual(caught.exception.kind, "REPORT_REJECTED")
        self.assertTrue(caught.exception.code)

    def test_frozen_reference_binding_and_all_thirty_claims(self):
        reference = json.loads(REFERENCE_PATH.read_bytes())
        self.assertEqual(tuple(QUESTIONS), EXPECTED_QUESTIONS)
        self.assertEqual((E, R, U), (
            "ESTABLISHED_IN_MODEL", "REFUTED_IN_MODEL", "UNRESOLVED"))
        self.assertEqual(reference["status"], "hand_derived_reference_not_execution")
        self.assertEqual(reference["input_file_sha256"], hashlib.sha256(FROZEN_RAW).hexdigest())
        self.assertEqual(reference["source_baseline"], FROZEN["source_baseline"])
        input_ids = [case["case_id"] for case in FROZEN["cases"]]
        reference_ids = [case["case_id"] for case in reference["results"]]
        self.assertEqual(len(reference_ids), len(set(reference_ids)))
        self.assertEqual(set(input_ids), set(reference_ids))
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        rows = {case["case_id"]: case for case in report["cases"]}
        self.assertEqual(set(rows), set(BASELINE))
        for case in reference["results"]:
            with self.subTest(case=case["case_id"]):
                actual = rows[case["case_id"]]["claims"]
                self.assertEqual(actual, case["claims"])
                self.assertEqual(tuple(actual[q] for q in QUESTIONS), BASELINE[case["case_id"]])
                self.assertEqual(rows[case["case_id"]]["certificate"]["displayed_route_before_rule_ids"],
                                 [None, None])
        verified = checker.verify_bytes(FROZEN_RAW, raw_json(report))
        self.assertEqual((verified["checked_cases"], verified["checked_claims"]), (5, 30))

    def test_exact_report_and_verification_headers(self):
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        report_raw = raw_json(report)
        verified = checker.verify_bytes(FROZEN_RAW, report_raw)
        self.assertEqual(set(report), {
            "format", "evaluation_status", "semantics", "input_sha256",
            "source_baseline", "authority_effect", "production_gate_eligible", "cases"})
        self.assertEqual(report["format"], REPORT_FORMAT)
        self.assertEqual(report["evaluation_status"], "COMPLETED")
        self.assertEqual(report["semantics"], SEMANTICS)
        self.assertEqual(report["input_sha256"], hashlib.sha256(FROZEN_RAW).hexdigest())
        self.assertEqual(report["source_baseline"], FROZEN["source_baseline"])
        self.assertEqual(set(verified), {
            "format", "verification_status", "semantics", "input_sha256", "report_sha256",
            "checked_cases", "checked_claims", "authority_effect", "production_gate_eligible"})
        self.assertEqual(verified["format"], VERIFY_FORMAT)
        self.assertEqual(verified["semantics"], SEMANTICS)
        self.assertEqual(verified["report_sha256"], hashlib.sha256(report_raw).hexdigest())
        self.assertEqual(verified["input_sha256"], report["input_sha256"])
        self.assertIs(type(verified["checked_cases"]), int)
        self.assertIs(type(verified["checked_claims"]), int)
        self.assertEqual(raw_json(report), raw_json(evaluator.evaluate_bytes(FROZEN_RAW)))
        self.assertEqual(verified["authority_effect"], "none")
        self.assertIs(verified["production_gate_eligible"], False)

    def test_identifier_renaming_preserves_claims_and_bindings(self):
        bundle = copy.deepcopy(FROZEN)
        add_fact(bundle["cases"][4], 1, True)
        add_fact(bundle["cases"][4], 4, False)
        original = {}
        for index, case in enumerate(bundle["cases"]):
            renamed_id = "RenamedCase" + str(index)
            original[renamed_id] = BASELINE[case["case_id"]]
            if index == 4:
                original[renamed_id] = (E, E, E, R, R, R)
            case["case_id"] = renamed_id
            subjects = {name: "Entity" + str(i) for i, name in enumerate(case["domain"]["subject_ids"])}
            modes = {name: "State" + str(i) for i, name in enumerate(case["domain"]["modes"])}
            predicates = {p["predicate_id"]: "Condition" + str(i)
                          for i, p in enumerate(case["predicate_declarations"])}
            case["domain"]["subject_ids"] = list(subjects.values())
            case["domain"]["modes"] = list(modes.values())
            case["failure_condition"]["mode_equals"] = modes[case["failure_condition"]["mode_equals"]]
            query = case["query"]
            query["selected_subject_id"] = subjects[query["selected_subject_id"]]
            query["initial_state"]["subject_id"] = subjects[query["initial_state"]["subject_id"]]
            query["initial_state"]["mode"] = modes[query["initial_state"]["mode"]]
            query["displayed_new_failure_route_modes"] = [modes[m] for m in query["displayed_new_failure_route_modes"]]
            for phase in ("before", "after"):
                for i, rule in enumerate(case[phase]["rules"]):
                    rule["rule_id"] = phase + "Step" + str(i)
                    rule["subject_id"] = subjects[rule["subject_id"]]
                    rule["from_mode"], rule["to_mode"] = modes[rule["from_mode"]], modes[rule["to_mode"]]
                    if rule["guard"]["kind"] == "predicate":
                        rule["guard"]["predicate_id"] = predicates[rule["guard"]["predicate_id"]]
            for declaration in case["predicate_declarations"]:
                declaration["predicate_id"] = predicates[declaration["predicate_id"]]
                for fact in declaration["facts"]:
                    fact["state"]["subject_id"] = subjects[fact["state"]["subject_id"]]
                    fact["state"]["mode"] = modes[fact["state"]["mode"]]
        for row in self.checked(bundle)["cases"]:
            self.assertEqual(tuple(row["claims"][q] for q in QUESTIONS), original[row["case_id"]])

    def test_inventory_reordering_preserves_each_case_meaning(self):
        bundle = copy.deepcopy(FROZEN)
        bundle["cases"].reverse()
        for case in bundle["cases"]:
            case["domain"]["subject_ids"].reverse()
            case["domain"]["modes"].reverse()
            case["predicate_declarations"].reverse()
            case["before"]["rules"].reverse()
            case["after"]["rules"].reverse()
        for row in self.checked(bundle)["cases"]:
            self.assertEqual(tuple(row["claims"][q] for q in QUESTIONS), BASELINE[row["case_id"]])

    def test_same_case_identifier_does_not_select_an_expected_result(self):
        bundle = single_case(2)
        bundle["cases"][0]["case_id"] = "K00"
        self.assert_claims(bundle, BASELINE["K02"])

    def test_pure_apis_do_not_read_expected_files(self):
        raw = raw_json(single_case(4))
        with mock.patch("builtins.open", side_effect=AssertionError("unexpected file read")), \
             mock.patch.object(io, "open", side_effect=AssertionError("unexpected file read")):
            report = evaluator.evaluate_bytes(raw)
            checked = checker.verify_bytes(raw, raw_json(report))
        self.assertEqual(checked["verification_status"], "VERIFIED")

    def test_checker_does_not_call_evaluator(self):
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        with mock.patch.object(evaluator, "evaluate_bytes", side_effect=AssertionError("evaluator called")):
            verified = checker.verify_bytes(FROZEN_RAW, raw_json(report))
        self.assertEqual(verified["verification_status"], "VERIFIED")

    def test_direct_relation_is_compared_by_meaning_not_rule_spelling(self):
        bundle = single_case()
        case = bundle["cases"][0]
        direct = selected_rule(case, "A", "before")
        direct["rule_id"] = selected_rule(case, "A")["rule_id"]
        self.assert_claims(bundle, (E, E, E, R, E, E))
        selected_rule(case, "A")["to_mode"] = "F"
        case["query"]["displayed_new_failure_route_modes"] = ["A", "F"]
        selected_rule(case, "A")["rule_id"] = "UnrelatedNewName"
        self.assert_claims(bundle, (R, E, E, R, E, E))

    def test_absent_before_direct_relation_does_not_establish_removal(self):
        bundle = single_case()
        bundle["cases"][0]["before"]["rules"] = []
        self.assert_claims(bundle, (R, E, E, R, E, E))

    def test_existing_before_route_does_not_change_after_feasibility(self):
        bundle = single_case()
        case = bundle["cases"][0]
        case["before"]["rules"] = copy.deepcopy(case["after"]["rules"])
        for rule in case["before"]["rules"]:
            rule["rule_id"] = "prior_" + rule["rule_id"]
        row = self.assert_claims(bundle, (R, E, E, R, E, E))
        self.assertEqual(row["certificate"]["displayed_route_before_rule_ids"],
                         ["prior_r2", "prior_r3"])
        self.assertEqual(row["certificate"]["displayed_route_rule_ids"], ["r2", "r3"])
        # A feasible after course is not evidence that its relations are new.
        self.assertEqual(row["claims"]["new_failure_route_feasible"], E)

    def test_before_route_proof_cannot_suppress_or_substitute_bound_rules(self):
        bundle = single_case()
        case = bundle["cases"][0]
        case["before"]["rules"] = copy.deepcopy(case["after"]["rules"])
        for rule in case["before"]["rules"]:
            rule["rule_id"] = "prior_" + rule["rule_id"]
        raw = raw_json(bundle)
        original = evaluator.evaluate_bytes(raw)
        checker.verify_bytes(raw, raw_json(original))
        for values in ([None, "prior_r3"], ["r2", "prior_r3"],
                       ["prior_r1", "prior_r3"], ["prior_r2"]):
            report = copy.deepcopy(original)
            report["cases"][0]["certificate"]["displayed_route_before_rule_ids"] = values
            with self.subTest(before_ids=values):
                self.reject_report(raw, report)
        # In the frozen case, r0 exists before but goes A -> F, not A -> B.
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        self.assertEqual(report["cases"][0]["certificate"]["displayed_route_before_rule_ids"],
                         [None, None])
        report["cases"][0]["certificate"]["displayed_route_before_rule_ids"][0] = "r0"
        self.reject_report(FROZEN_RAW, report)

    def test_true_first_fact_admits_only_the_first_course(self):
        bundle = single_case(4)
        add_fact(bundle["cases"][0], 1, True)
        self.assert_claims(bundle, (E, E, E, R, U, U))

    def test_false_first_fact_refutes_course_but_not_all_state_projection(self):
        bundle = single_case(4)
        add_fact(bundle["cases"][0], 1, False)
        self.assert_claims(bundle, (E, R, R, R, U, R))

    def test_later_false_fact_on_progression_refutes_repetition(self):
        bundle = single_case(4)
        add_fact(bundle["cases"][0], 1, True)
        add_fact(bundle["cases"][0], 4, False)
        row = self.assert_claims(bundle, (E, E, E, R, R, R))
        witness = row["certificate"]["repeatability"][1]
        self.assertEqual((witness["kind"], witness["counter"]), ("predicate_false", 4))

    def test_off_progression_false_facts_do_not_refute_repetition(self):
        for counter in (0, 2, 3, 5):
            with self.subTest(counter=counter):
                bundle = single_case(4)
                add_fact(bundle["cases"][0], 1, True)
                add_fact(bundle["cases"][0], counter, False)
                self.assert_claims(bundle, (E, E, E, R, R, U))

    def test_progression_is_bound_to_nonzero_initial_counter(self):
        for false_counter, repeatability in ((4, U), (6, R), (9, R), (10, U)):
            with self.subTest(false_counter=false_counter):
                bundle = single_case(4)
                case = bundle["cases"][0]
                case["query"]["initial_state"]["counter"] = 5
                if false_counter != 6:
                    add_fact(case, 6, True)
                add_fact(case, false_counter, False)
                expected_route = R if false_counter == 6 else E
                expected_projection = U if false_counter == 6 else R
                self.assert_claims(bundle, (E, expected_route, expected_route, R,
                                            expected_projection, repeatability))

    def test_finite_true_facts_never_establish_unbounded_repetition(self):
        bundle = single_case(4)
        for counter in range(1, 100, 3):
            add_fact(bundle["cases"][0], counter, True)
        self.assert_claims(bundle, (E, E, E, R, U, U))

    def test_predicate_facts_are_bound_to_subject_and_mode(self):
        bundle = single_case(4)
        case = bundle["cases"][0]
        case["domain"]["subject_ids"].append("OtherSubject")
        add_fact(case, 1, False, subject="OtherSubject")
        add_fact(case, 1, False, mode="A")
        self.assert_claims(bundle, (E, U, U, R, U, U))

    def test_unknown_prefix_does_not_hide_later_false_guard(self):
        bundle = single_case(4)
        case = bundle["cases"][0]
        selected_rule(case, "A")["guard"] = {"kind": "predicate", "predicate_id": "permit"}
        selected_rule(case, "B")["guard"] = {"kind": "counter_below", "limit": 0}
        self.assert_claims(bundle, (E, R, R, R, U, R))

    def test_unknown_prefix_does_not_hide_missing_route_edge(self):
        bundle = single_case(4)
        case = bundle["cases"][0]
        selected_rule(case, "A")["guard"] = {"kind": "predicate", "predicate_id": "permit"}
        case["after"]["rules"] = [rule for rule in case["after"]["rules"] if rule["from_mode"] != "B"]
        self.assert_claims(bundle, (E, R, R, R, U, R))

    def test_other_cycle_is_not_a_return_to_the_initial_mode(self):
        bundle = single_case(4)
        case = bundle["cases"][0]
        selected_rule(case, "B")["to_mode"] = "B"
        row = self.assert_claims(bundle, (E, R, R, R, U, R))
        self.assertEqual(row["certificate"]["mode_walk_stop"], {"kind": "other_cycle", "mode": "B"})
        self.assertEqual(row["certificate"]["repeatability"], [])

    def test_initial_return_without_failure_is_not_failure_return(self):
        bundle = single_case()
        selected_rule(bundle["cases"][0], "B")["to_mode"] = "A"
        self.assert_claims(bundle, (E, R, R, R, E, R))

    def test_unreachable_counter_dependency_changes_only_all_state_projection(self):
        bundle = single_case()
        case = bundle["cases"][0]
        case["domain"]["modes"].append("Unreached")
        case["after"]["rules"].append({
            "rule_id": "unreached_step", "subject_id": "subject-X",
            "from_mode": "Unreached", "to_mode": "Unreached",
            "guard": {"kind": "counter_below", "limit": 10}, "counter_increment": 1})
        self.assert_claims(bundle, (E, E, E, R, R, E))

    def test_zero_limit_is_a_constant_disabled_relation(self):
        bundle = single_case(1)
        for phase in ("before", "after"):
            for rule in bundle["cases"][0][phase]["rules"]:
                rule["guard"]["limit"] = 0
        self.assert_claims(bundle, (E, R, R, R, E, R))

    def test_huge_finite_limit_is_refuted_without_simulating_to_the_limit(self):
        bundle = single_case(1)
        for phase in ("before", "after"):
            for rule in bundle["cases"][0][phase]["rules"]:
                rule["guard"]["limit"] = 10**12
        row = self.assert_claims(bundle, (E, E, E, R, R, R))
        self.assertEqual(len(row["certificate"]["mode_walk_rule_ids"]), 3)
        for witness in row["certificate"]["repeatability"]:
            self.assertGreaterEqual(witness["counter"], 10**12)
            self.assertEqual((witness["counter"] - witness["offset"]) % 3, 0)

    def test_exhaustive_small_limits_have_independently_derived_outcomes(self):
        # Guards are n < L. First failure uses n=0,1; first return adds n=2.
        # Any positive L distinguishes enabled n=0 from disabled n=L.
        for limit in range(7):
            with self.subTest(limit=limit):
                bundle = single_case(1)
                for phase in ("before", "after"):
                    for rule in bundle["cases"][0][phase]["rules"]:
                        rule["guard"]["limit"] = limit
                self.assert_claims(bundle, (
                    E, E if limit >= 2 else R, E if limit >= 3 else R,
                    R, E if limit == 0 else R, R))

    def test_malformed_json_is_rejected_before_model_evaluation(self):
        bad = (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
               b'{"x":-Infinity}', b'{"x":"\\ud800"}', b'\xff',
               b'\xef\xbb\xbf{}', b'{} trailing', b'')
        for raw in bad:
            with self.subTest(raw=raw[:50]):
                self.reject_input(raw)

    def test_json_resource_exclusions_are_distinct_from_malformed_syntax(self):
        for raw in (b'[' * 40 + b'0' + b']' * 40,
                    b'{"x":' + b'1' * 129 + b'}', b'{"x":1e9999}'):
            with self.subTest(raw=raw[:50]):
                self.reject_input(raw, "INPUT_UNSUPPORTED")

    def test_parser_keeps_exact_integer_values_without_float_rounding(self):
        parsed = parse_json_bytes(b'{"x":9007199254740993,"y":1.0,"z":1e3}')
        self.assertEqual(parsed, {"x": 9007199254740993, "y": 1, "z": 1000})
        self.assertIs(type(parsed["x"]), int)
        raw = raw_json(single_case()).replace(b'"counter":0', b'"counter":0.0')
        report = evaluator.evaluate_bytes(raw)
        self.assertEqual(report["cases"][0]["claims"][QUESTIONS[3]], R)
        checker.verify_bytes(raw, raw_json(report))

    def test_wrong_shape_types_and_foreign_keys_are_invalid(self):
        mutations = [
            (("format",), "wrong"), (("source_baseline",), "x" * 40),
            (("authority_effect",), "release"), (("production_gate_eligible",), 0),
            (("question_ids",), list(reversed(QUESTIONS))), (("cases",), []),
            (("cases", 0, "case_id"), "bad id"),
            (("cases", 0, "domain", "modes"), ["A", "B", "F", "A"]),
            (("cases", 0, "query", "initial_state", "counter"), True),
            (("cases", 0, "query", "initial_state", "counter"), -1),
            (("cases", 0, "query", "initial_state", "counter"), 1.5),
            (("cases", 0, "query", "initial_state", "subject_id"), "Undeclared"),
            (("cases", 0, "query", "displayed_new_failure_route_modes"), ["B", "F"]),
            (("cases", 0, "query", "displayed_new_failure_route_modes"), ["A", "B"]),
            (("cases", 0, "after", "complete_rule_inventory"), 1),
            (("cases", 0, "after", "rules", 0, "counter_increment"), True),
            (("cases", 0, "after", "rules", 0, "counter_increment"), 2),
            (("cases", 0, "after", "rules", 0, "to_mode"), "Undeclared"),
            (("cases", 0, "after", "rules", 0, "guard"), {"kind": "unconditional", "limit": 3}),
            (("cases", 0, "after", "rules", 0, "guard"), {"kind": "counter_below", "limit": True}),
            (("cases", 0, "after", "rules", 0, "guard"), {"kind": "predicate", "predicate_id": "Undeclared"}),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                bundle = single_case()
                set_path(bundle, path, value)
                self.reject_input(raw_json(bundle))
        for path in ((), ("cases", 0), ("cases", 0, "query")):
            bundle = single_case()
            node = bundle
            for key in path:
                node = node[key]
            node["unexpected"] = "ignored data must not be admitted"
            with self.subTest(extra_at=path):
                self.reject_input(raw_json(bundle))

    def test_duplicate_case_rule_and_predicate_identities_are_invalid(self):
        bundle = single_case()
        bundle["cases"].append(copy.deepcopy(bundle["cases"][0]))
        self.reject_input(raw_json(bundle))
        bundle = single_case()
        rules = bundle["cases"][0]["after"]["rules"]
        rules[1]["rule_id"] = rules[0]["rule_id"]
        self.reject_input(raw_json(bundle))
        bundle = single_case(4)
        predicates = bundle["cases"][0]["predicate_declarations"]
        predicates.append(copy.deepcopy(predicates[0]))
        self.reject_input(raw_json(bundle))

    def test_duplicate_contradictory_or_unbound_facts_are_invalid(self):
        for second_value in (True, False):
            bundle = single_case(4)
            add_fact(bundle["cases"][0], 1, True)
            add_fact(bundle["cases"][0], 1, second_value)
            with self.subTest(second_value=second_value):
                self.reject_input(raw_json(bundle))
        for field, value in (("value", 1), ("subject_id", "Undeclared"),
                             ("mode", "Undeclared"), ("counter", True)):
            bundle = single_case(4)
            add_fact(bundle["cases"][0], 1, True)
            fact = bundle["cases"][0]["predicate_declarations"][0]["facts"][0]
            (fact if field == "value" else fact["state"])[field] = value
            with self.subTest(field=field):
                self.reject_input(raw_json(bundle))

    def test_parallel_rules_are_unsupported_even_when_disabled(self):
        for phase in ("before", "after"):
            bundle = single_case()
            case = bundle["cases"][0]
            alternative = copy.deepcopy(selected_rule(case, "A", phase))
            alternative["rule_id"] = "Alternative"
            alternative["guard"] = {"kind": "counter_below", "limit": 0}
            case[phase]["rules"].append(alternative)
            with self.subTest(phase=phase):
                self.reject_input(raw_json(bundle), "INPUT_UNSUPPORTED")

    def test_initial_failure_state_is_explicitly_unsupported(self):
        bundle = single_case()
        case = bundle["cases"][0]
        case["query"]["initial_state"]["mode"] = "F"
        case["query"]["displayed_new_failure_route_modes"] = ["F", "A", "B", "F"]
        self.reject_input(raw_json(bundle), "INPUT_UNSUPPORTED")

    def test_well_formed_input_resource_limits_are_unsupported(self):
        variants = []
        bundle = single_case()
        bundle["cases"] = [dict(copy.deepcopy(bundle["cases"][0]), case_id="Case" + str(i)) for i in range(17)]
        variants.append(("cases", bundle))
        bundle = single_case()
        bundle["cases"][0]["domain"]["subject_ids"] += ["S" + str(i) for i in range(16)]
        variants.append(("subjects", bundle))
        bundle = single_case()
        bundle["cases"][0]["domain"]["modes"] += ["M" + str(i) for i in range(62)]
        variants.append(("modes", bundle))
        bundle = single_case(4)
        base = bundle["cases"][0]["predicate_declarations"][0]
        bundle["cases"][0]["predicate_declarations"] += [dict(copy.deepcopy(base), predicate_id="P" + str(i)) for i in range(32)]
        variants.append(("predicates", bundle))
        bundle = single_case(4)
        for i in range(4097):
            add_fact(bundle["cases"][0], i, True)
        variants.append(("facts", bundle))
        bundle = single_case()
        bundle["cases"][0]["query"]["displayed_new_failure_route_modes"] = ["A"] + ["B"] * 255 + ["F"]
        variants.append(("route", bundle))
        for path in (("query", "initial_state", "counter"),
                     ("after", "rules", 0, "guard", "limit")):
            bundle = single_case(1)
            set_path(bundle["cases"][0], path, 10**12 + 1)
            variants.append((str(path), bundle))
        bundle = single_case(4)
        add_fact(bundle["cases"][0], 10**12 + 1, True)
        variants.append(("fact counter", bundle))
        # 129 distinct (subject, mode) pairs exceed only the phase rule budget.
        bundle = single_case()
        case = bundle["cases"][0]
        case["domain"]["subject_ids"] += ["S1", "S2"]
        case["domain"]["modes"] += ["M" + str(i) for i in range(41)]
        case["after"]["rules"] = []
        for subject in case["domain"]["subject_ids"]:
            for mode in case["domain"]["modes"]:
                case["after"]["rules"].append({"rule_id": "Step" + str(len(case["after"]["rules"])),
                    "subject_id": subject, "from_mode": mode, "to_mode": "F",
                    "guard": {"kind": "unconditional"}, "counter_increment": 1})
        case["after"]["rules"] = case["after"]["rules"][:129]
        variants.append(("rules", bundle))
        for name, bundle in variants:
            with self.subTest(limit=name):
                self.reject_input(raw_json(bundle), "INPUT_UNSUPPORTED")
        self.reject_input(raw_json(single_case()) + b" " * (1024 * 1024), "INPUT_UNSUPPORTED")

    def test_raw_input_binding_rejects_even_whitespace_only_change(self):
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        self.reject_report(FROZEN_RAW + b"\n", report)

    def test_report_headers_authority_and_case_bijection_are_checked(self):
        original = evaluator.evaluate_bytes(FROZEN_RAW)
        mutations = [(("format",), "wrong"), (("evaluation_status",), "PASS"),
            (("semantics",), "different"), (("input_sha256",), "0" * 64),
            (("source_baseline",), "0" * 40), (("authority_effect",), "release"),
            (("production_gate_eligible",), True), (("production_gate_eligible",), 0),
            (("cases", 0, "case_id"), "OtherCase")]
        for path, value in mutations:
            report = copy.deepcopy(original)
            set_path(report, path, value)
            with self.subTest(path=path, value=value):
                self.reject_report(FROZEN_RAW, report)
        for operation in (lambda r: r["cases"].pop(),
                          lambda r: r["cases"].append(copy.deepcopy(r["cases"][0])),
                          lambda r: r.update(unexpected=True)):
            report = copy.deepcopy(original)
            operation(report)
            self.reject_report(FROZEN_RAW, report)

    def test_each_claim_is_independently_rederived(self):
        original = evaluator.evaluate_bytes(FROZEN_RAW)
        for index, case in enumerate(original["cases"]):
            for question in QUESTIONS:
                report = copy.deepcopy(original)
                current = case["claims"][question]
                report["cases"][index]["claims"][question] = R if current != R else E
                with self.subTest(case=case["case_id"], question=question):
                    self.reject_report(FROZEN_RAW, report)

    def test_proof_structure_bindings_and_types_are_checked(self):
        original = evaluator.evaluate_bytes(FROZEN_RAW)
        prefix = ("cases", 0, "certificate")
        mutations = [
            (("direct_rule_ids", "before"), None), (("direct_rule_ids", "after"), "r2"),
            (("displayed_route_rule_ids",), ["r2"]),
            (("displayed_route_rule_ids", 0), "r1"),
            (("mode_walk_rule_ids",), ["r2", "r3"]),
            (("mode_walk_rule_ids",), ["r2", "r3", "r1", "r2"]),
            (("mode_walk_stop", "kind"), "terminal"),
            (("mode_walk_stop", "mode"), "B"), (("counter_increment",), True),
            (("projection", 0, "rule_id"), "Wrong"),
            (("projection", 0, "true_counter"), False),
            (("repeatability", 1, "offset"), True),
            (("repeatability", 0, "period"), True),
            (("repeatability", 0, "kind"), "predicate_unfixed"),
            (("repeatability", 0, "counter"), 0),
        ]
        for suffix, value in mutations:
            report = copy.deepcopy(original)
            set_path(report, prefix + suffix, value)
            with self.subTest(suffix=suffix):
                self.reject_report(FROZEN_RAW, report)
        for section in ("projection", "repeatability"):
            for operation in (lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[0]))):
                report = copy.deepcopy(original)
                operation(report["cases"][0]["certificate"][section])
                with self.subTest(section=section):
                    self.reject_report(FROZEN_RAW, report)
        report = copy.deepcopy(original)
        report["cases"][0]["certificate"]["unexpected"] = "proof bypass"
        self.reject_report(FROZEN_RAW, report)
        report = copy.deepcopy(original)
        report["cases"][0]["certificate"] = copy.deepcopy(report["cases"][1]["certificate"])
        self.reject_report(FROZEN_RAW, report)

    def test_projection_and_repeatability_witnesses_are_validated_not_trusted(self):
        bundle = single_case(4)
        add_fact(bundle["cases"][0], 1, True)
        add_fact(bundle["cases"][0], 4, False)
        raw = raw_json(bundle)
        original = evaluator.evaluate_bytes(raw)
        cert = original["cases"][0]["certificate"]
        projection_index = next(i for i, row in enumerate(cert["projection"]) if row["mode"] == "B")
        for path, value in ((["projection", projection_index, "false_counter"], 2),
                            (["projection", projection_index, "true_counter"], 4),
                            (["repeatability", 1, "counter"], 2),
                            (["repeatability", 1, "kind"], "predicate_unfixed")):
            report = copy.deepcopy(original)
            set_path(report["cases"][0]["certificate"], path, value)
            with self.subTest(path=path):
                self.reject_report(raw, report)

    def test_checker_accepts_alternative_valid_finite_limit_witness(self):
        bundle = single_case(1)
        raw = raw_json(bundle)
        report = evaluator.evaluate_bytes(raw)
        for row in report["cases"][0]["certificate"]["projection"]:
            row["true_counter"], row["false_counter"] = 2, 100
        for row in report["cases"][0]["certificate"]["repeatability"]:
            row["counter"] += 3
        verified = checker.verify_bytes(raw, raw_json(report))
        self.assertEqual(verified["verification_status"], "VERIFIED")

    def test_report_case_order_can_change_without_changing_identity(self):
        report = evaluator.evaluate_bytes(FROZEN_RAW)
        report["cases"].reverse()
        verified = checker.verify_bytes(FROZEN_RAW, raw_json(report))
        self.assertEqual(verified["checked_claims"], 30)

    def test_malformed_report_is_report_rejection_not_an_input_result(self):
        for raw in (b'{"x":1,"x":2}', b'NaN', b'[]', b'null', b'\xff'):
            with self.subTest(raw=raw):
                with self.assertRaises(CyclicError) as caught:
                    checker.verify_bytes(FROZEN_RAW, raw)
                self.assertEqual(caught.exception.kind, "REPORT_REJECTED")

    def test_cli_isolated_from_reference_and_checker_isolated_from_evaluator(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_path = temporary / "inputs.json"
            input_path.write_bytes(FROZEN_RAW)
            outputs = {}
            for role, script, module in (
                ("evaluation", "evaluate_paradox_cyclic_v0.py", "evaluator.py"),
                ("verification", "check_paradox_cyclic_result_v0.py", "checker.py"),
            ):
                tree = temporary / role
                package = tree / "tools/paradox_cyclic_v0"
                package.mkdir(parents=True)
                for name in ("__init__.py", "contract.py", module):
                    shutil.copyfile(ROOT / "tools/paradox_cyclic_v0" / name, package / name)
                shutil.copyfile(ROOT / "tools" / script, tree / "tools" / script)
                command = [sys.executable, str(tree / "tools" / script), "--input", str(input_path)]
                if role == "verification":
                    report_path = temporary / "report.json"
                    report_path.write_bytes(outputs["evaluation"].stdout)
                    command += ["--report", str(report_path)]
                process = subprocess.run(command, cwd=tree, capture_output=True, timeout=20)
                self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
                self.assertEqual(process.stderr, b"")
                outputs[role] = process
            self.assertEqual(json.loads(outputs["evaluation"].stdout)["evaluation_status"], "COMPLETED")
            self.assertEqual(json.loads(outputs["verification"].stdout)["verification_status"], "VERIFIED")

    def test_cli_help_usage_and_rejected_input_exit_codes(self):
        evaluate_tool = ROOT / "tools/evaluate_paradox_cyclic_v0.py"
        check_tool = ROOT / "tools/check_paradox_cyclic_result_v0.py"
        for tool in (evaluate_tool, check_tool):
            for arguments, expected_code in ((["--help"], 0), ([], 2)):
                with self.subTest(tool=tool.name, arguments=arguments):
                    process = subprocess.run([sys.executable, str(tool), *arguments],
                        cwd=ROOT, capture_output=True, timeout=20)
                    self.assertEqual(process.returncode, expected_code)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_bytes(b'{"x":1,"x":2}')
            process = subprocess.run([sys.executable, str(evaluate_tool), "--input", str(path)],
                cwd=ROOT, capture_output=True, timeout=20)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(process.stdout, b"")
            error = json.loads(process.stderr)
            self.assertEqual(error["error"], "INPUT_INVALID")
            self.assertTrue(error["code"])
            self.assertEqual(error["authority_effect"], "none")
            self.assertIs(error["production_gate_eligible"], False)
            path.write_bytes(raw_json(single_case()))
            report_path = Path(directory) / "bad-report.json"
            report_path.write_bytes(b"{}")
            process = subprocess.run([sys.executable, str(check_tool), "--input", str(path),
                "--report", str(report_path)], cwd=ROOT, capture_output=True, timeout=20)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(process.stdout, b"")
            error = json.loads(process.stderr)
            self.assertEqual(error["error"], "REPORT_REJECTED")
            self.assertTrue(error["code"])
            self.assertEqual(error["authority_effect"], "none")
            self.assertIs(error["production_gate_eligible"], False)


if __name__ == "__main__":
    unittest.main()
