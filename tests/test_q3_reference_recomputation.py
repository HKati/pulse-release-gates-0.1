"""Offline, synthetic CLI conformance for the standalone Q3 reducer/checker.

No model calls, historical Q2 inputs, workflow execution or release authority.
The 42 accepted design cases are exercised with actual byte-bound fixtures.
Expected counts/decisions are separate predicates, not producer outputs reused
as an oracle. The checker receives the original caller-selected expectation.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/q3_reference_v0"
_spec = importlib.util.spec_from_file_location("q3_fixture_builder", FIXTURES / "fixture_builder.py")
fb = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = fb
_spec.loader.exec_module(fb)
PRODUCER = ROOT / fb.PRODUCER_PATH
CHECKER = ROOT / fb.CHECKER_PATH
CATALOG = fb.read_json(FIXTURES / "case_expectations.json")
CASES = {int(c["case_id"].rsplit("-", 1)[1]): c for c in CATALOG["cases"]}
SEMANTIC_KEYS = ("input_validity", "metric_result", "pass", "reason_codes", "counts",
                 "overall", "dimensions", "coverage", "worst_group_gap", "excluded_records", "claims")


class Q3ReferenceRecomputationTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.result_schema = fb.read_json(ROOT / fb.RESOURCE_PATHS["result_schema_sha256"])
        cls.input_schema = fb.read_json(ROOT / fb.RESOURCE_PATHS["input_schema_sha256"])
        Draft202012Validator.check_schema(cls.result_schema)
        Draft202012Validator.check_schema(cls.input_schema)
        cls.result_validator = Draft202012Validator(cls.result_schema)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pulse-q3-conformance-")
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)

    def invoke(self, program, arguments, *, env=None):
        process_env = os.environ.copy()
        process_env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        if env:
            process_env.update(env)
        completed = subprocess.run([sys.executable, str(program), *map(str, arguments)],
                                   cwd=self.temp, env=process_env, capture_output=True,
                                   text=True, encoding="utf-8", timeout=30, check=False)
        self.assertNotIn("Traceback (most recent call last)", completed.stderr,
                         msg=f"Unhandled exception: {completed.stderr}")
        return completed

    def roots_and_input(self, fixture):
        args = ["--bundle", fixture.bundle, "--resources-root", fixture.resources_root,
                "--producer-source-root", fixture.producer_source_root]
        if not fixture.omit_expected_argument:
            args += ["--expected", fixture.expected]
        return args

    def produce(self, fixture, *, out_name="summary.json", env=None):
        path = fixture.root / out_name
        completed = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", path], env=env)
        self.assertTrue(path.is_file(), msg=f"No result file; exit={completed.returncode}, stderr={completed.stderr}")
        result = fb.read_json(path)
        self.result_validator.validate(result)
        self.assertEqual(path.read_bytes(), fb.json_bytes(result), "Result serialization must be canonical")
        self.assertEqual(result["reason_codes"], sorted(set(result["reason_codes"])))
        self.assertEqual(result["claims"], {
            "authority_effect": "none", "production_gate_eligible": False,
            "current_run_evidence": False, "source_authentication": "not_established",
            "label_correctness": "not_verified", "slice_metadata_correctness": "not_verified",
            "policy_activation": False,
        })
        return completed, result, path

    def check(self, fixture, summary, expected_exit, *, receipt_name="receipt.json"):
        receipt_path = fixture.root / receipt_name
        completed = self.invoke(CHECKER, [*self.roots_and_input(fixture), "--summary", summary,
                                          "--receipt", receipt_path])
        self.assertEqual(completed.returncode, expected_exit,
                         msg=f"checker stderr={completed.stderr}\nstdout={completed.stdout}")
        self.assertTrue(receipt_path.is_file(), msg=completed.stdout + completed.stderr)
        receipt = fb.read_json(receipt_path)
        self.assertEqual(receipt["checker_exit_code"], expected_exit)
        return receipt

    def assert_invalid(self, fixture, expected_reason=None):
        completed, result, path = self.produce(fixture)
        self.assertEqual(completed.returncode, 2, msg=completed.stdout + completed.stderr)
        self.assertEqual(result["input_validity"], "INVALID")
        self.assertFalse(result["pass"])
        self.assertEqual(result["metric_result"], "FAIL")
        for name in ("counts", "overall", "coverage", "worst_group_gap",
                     "dataset_id", "reduction_id", "observation_subject"):
            self.assertIsNone(result[name], name)
        self.assertEqual(result["dimensions"], [])
        self.assertEqual(result["excluded_records"], [])
        self.assertTrue(result["reason_codes"])
        if expected_reason:
            self.assertEqual(set(result["reason_codes"]), {expected_reason})
        self.check(fixture, path, 2)
        return result

    def assert_valid(self, fixture, expected_pass=True):
        completed, result, path = self.produce(fixture)
        self.assertEqual(completed.returncode, 0 if expected_pass else 1,
                         msg=completed.stdout + completed.stderr)
        self.assertEqual(result["input_validity"], "VALID")
        self.assertIs(result["pass"], expected_pass)
        self.assertEqual(result["metric_result"], "PASS" if expected_pass else "FAIL")
        self.check(fixture, path, 0)
        return result, path

    def number(self, value):
        if isinstance(value, dict) and "numerator" in value:
            return value["numerator"] / value["denominator"]
        return value

    def assert_expected_predicates(self, result, expected, case_id, variant):
        self.assertEqual(result["input_validity"], expected["input_validity"])
        self.assertEqual(result["metric_result"], expected["metric_result"])
        self.assertIs(result["pass"], expected["metric_pass"])
        codes = expected.get("reason_codes_by_variant", {}).get(variant, expected.get("reason_codes", []))
        self.assertEqual(set(result["reason_codes"]), set(codes))
        if result["input_validity"] == "INVALID":
            for key in ("counts", "overall", "coverage", "worst_group_gap"):
                self.assertIsNone(result[key])
            self.assertEqual(result["dimensions"], [])
            self.assertEqual(result["excluded_records"], [])
            if "expected_context_sha256" in expected:
                self.assertEqual(result["expected_context_sha256"], expected["expected_context_sha256"])
            return
        counts = result["counts"]
        fields = {"n_input": "n_total", "n_q1_ineligible": "n_q1_ineligible",
                  "n_q3_unknown_excluded": "n_unknown_ignored", "n_q3_eligible": "n_q3_eligible",
                  "n_pass": "n_pass", "n_fail": "n_fail"}
        for source, dest in fields.items():
            if source in expected:
                self.assertEqual(counts[dest], expected[source], source)
        if "n_q1_eligible" in expected:
            self.assertEqual(counts["n_total"] - counts["n_q1_ineligible"], expected["n_q1_eligible"])
        self.assertEqual(counts["n_total"], counts["n_q1_ineligible"] + counts["n_unknown_ignored"] + counts["n_q3_eligible"])
        self.assertEqual(counts["n_q3_eligible"], counts["n_pass"] + counts["n_fail"])
        dimensions = {d["dimension"]: d for d in result["dimensions"]}
        self.assertEqual(list(dimensions), sorted(dimensions))
        groups = [g for d in result["dimensions"] for g in d["groups"]]
        included = [g for g in groups if g["included_in_disparity"]]
        excluded = [g for g in groups if not g["included_in_disparity"]]
        for dimension in dimensions.values():
            self.assertEqual(sum(g["n_eligible"] for g in dimension["groups"]), counts["n_q3_eligible"])
            self.assertEqual(sum(g["n_pass"] for g in dimension["groups"]), counts["n_pass"])
        comparable = expected.get("comparable_groups_by_variant", {}).get(variant, expected.get("comparable_groups"))
        if comparable is not None:
            self.assertEqual(len(included), comparable)
        if "excluded_groups" in expected:
            self.assertEqual(len(excluded), expected["excluded_groups"])
        if "distinct_group_keys" in expected:
            self.assertEqual(len({(g["dimension"], g["kind"], g["value"]) for g in groups}), expected["distinct_group_keys"])
        if "total_marginal_group_memberships" in expected:
            self.assertEqual(sum(g["n_eligible"] for g in groups), expected["total_marginal_group_memberships"])
        coverage = result["coverage"]
        if "small_group_union_count" in expected:
            self.assertEqual(coverage["excluded_in_any_dimension_count"], expected["small_group_union_count"])
        if "small_group_union_fraction" in expected:
            self.assertEqual(coverage["excluded_in_any_dimension_fraction"], self.number(expected["small_group_union_fraction"]))
        if "alternative_per_dimension_max" in expected:
            self.assertEqual(coverage["max_per_dimension_small_group_fraction_diagnostic"], self.number(expected["alternative_per_dimension_max"]))
        for field, actual_key in (("missing_count_by_dimension", "missing_count"),
                                  ("missing_fraction_by_dimension", "missing_fraction"),
                                  ("small_count_by_dimension", "small_group_count")):
            for name, value in expected.get(field, {}).items():
                self.assertEqual(dimensions[name][actual_key], self.number(value))
        if "max_missing_count" in expected:
            self.assertEqual(max(d["missing_count"] for d in dimensions.values()), expected["max_missing_count"])
        for field, actual_key in (("overall_pass_rate", "pass_rate"),
                                  ("overall_wilson_lower", "wilson_lower"),
                                  ("overall_wilson_upper", "wilson_upper")):
            if field in expected:
                value = None if result["overall"] is None else result["overall"][actual_key]
                reference = self.number(expected[field])
                if actual_key.startswith("wilson_") and value is not None and reference is not None:
                    # The design records analytical endpoints; binary64 may
                    # differ by a few ulps. Decisions never use this tolerance.
                    self.assertAlmostEqual(value, reference, delta=1e-14)
                else:
                    self.assertEqual(value, reference)
        if "worst_group_gap" in expected:
            self.assertEqual(result["worst_group_gap"], expected["worst_group_gap"])
        relation = expected.get("worst_gap_relation_to_threshold")
        if relation == "> 0.05":
            self.assertGreater(result["worst_group_gap"], 0.05)
        elif relation == "<= 0.05":
            self.assertLessEqual(result["worst_group_gap"], 0.05)
        analytical_n = {5: 30, 15: 80, 39: 80, 40: 400}.get(case_id)
        if analytical_n:
            z2 = 1.959963984540054 ** 2
            self.assertAlmostEqual(result["worst_group_gap"], z2 / (analytical_n + z2), delta=1e-14)
        if case_id == 4:
            for key, value in expected["undersized_group_diagnostics"].items():
                self.assertEqual(excluded[0][key], value)
        if case_id == 7:
            self.assertIsNone(result["overall"])
            self.assertIsNone(coverage["excluded_in_any_dimension_fraction"])
            self.assertIsNone(coverage["max_per_dimension_small_group_fraction_diagnostic"])
            self.assertFalse(coverage["missing_coverage_ok"])
            self.assertFalse(coverage["small_group_coverage_ok"])
            for dimension in dimensions.values():
                self.assertIsNone(dimension["missing_fraction"])
                self.assertIsNone(dimension["small_group_fraction"])
        if case_id == 15:
            by_value = {g["value"]: g for g in dimensions["B"]["groups"]}
            self.assertEqual(by_value["small_but_comparable"]["n_eligible"], 80)
            self.assertEqual(by_value["small_but_comparable"]["n_pass"], 80)
            self.assertEqual(by_value["large"]["n_eligible"], 320)
        if case_id == 24:
            self.assertEqual([(g["value"], g["n_eligible"]) for g in groups if g["kind"] == "missing"], [(None, 20)])
            self.assertEqual([g["n_eligible"] for g in groups if g["kind"] == "value" and g["value"] == "__MISSING__"], [80])
        if case_id == 25:
            self.assertEqual({g["value"] for g in groups}, {"en", "EN", "en ", " ", "é", "e\u0301"})
        if case_id == 40:
            for g in included:
                self.assertAlmostEqual(g["wilson_lower"], 0, delta=1e-14)

    def run_design_case(self, case_id, selected_variant=None):
        for variant in (selected_variant,):
            with self.subTest(case=f"Q3C-{case_id:03d}", variant=variant):
                fixture = fb.materialize(case_id, self.temp / (variant or "default"), variant=variant)
                completed, result, summary = self.produce(fixture)
                expected = CASES[case_id]["expected"]
                self.assert_expected_predicates(result, expected, case_id, variant)
                expected_exit = 2 if not expected["input_valid"] else (0 if expected["metric_pass"] else 1)
                self.assertEqual(completed.returncode, expected_exit, msg=completed.stdout + completed.stderr)
                if case_id == 34:
                    altered = copy.deepcopy(result)
                    altered["counts"]["n_q3_eligible"] = 401
                    altered["counts"]["n_pass"] = 401
                    fb.write_json(summary, altered)
                elif case_id == 41:
                    altered = copy.deepcopy(result)
                    altered["implementation"]["tool_version"] = "other-structurally-valid-version"
                    fb.write_json(summary, altered)
                checker_exit = expected.get("expected_checker_exit_code", 0 if expected["input_valid"] else 2)
                receipt = self.check(fixture, summary, checker_exit)
                if expected.get("checker_error_codes"):
                    self.assertEqual(set(receipt["reason_codes"]), set(expected["checker_error_codes"]))

    def test_catalog_is_complete_and_synthetic(self):
        self.assertEqual(sorted(CASES), list(range(1, 43)))
        self.assertEqual(CATALOG["case_count"], 42)
        self.assertTrue(CATALOG["synthetic_only"])
        self.assertEqual(CATALOG["authority_effect"], "none")
        inventory = fb.read_json(FIXTURES / "baseline/payload_inventory.json")
        self.assertTrue(inventory["synthetic_only"])
        self.assertEqual(inventory["actual_model_calls"], 0)
        generated = fb.materialize(1, self.temp / "baseline-regeneration")
        for entry in inventory["files"]:
            payload = (FIXTURES / "baseline" / entry["path"]).read_bytes()
            self.assertEqual(len(payload), entry["size_bytes"])
            self.assertEqual(fb.sha256(payload), entry["sha256"])
            self.assertEqual(payload, (generated.root / entry["path"]).read_bytes())
        self.assertFalse((FIXTURES / "baseline/expected_context.json").exists())

    def test_canonical_output_is_repeatable_across_process_hash_seeds(self):
        fixture = fb.materialize(25, self.temp / "unicode")
        _, first, first_path = self.produce(fixture, out_name="first.json", env={"PYTHONHASHSEED": "1", "TZ": "UTC"})
        _, second, second_path = self.produce(fixture, out_name="second.json", env={"PYTHONHASHSEED": "73017", "TZ": "Pacific/Honolulu"})
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        self.assertEqual(first, second)
        self.check(fixture, second_path, 0)

    def test_row_label_and_dimension_order_do_not_change_metrics(self):
        examples, labels, dimensions = fb.records_for_case(14)
        original = fb.write_fixture(self.temp / "original", examples, labels, dimensions)
        first, _ = self.assert_valid(original)
        reordered = fb.write_fixture(self.temp / "reordered", list(reversed(examples)), list(reversed(labels)), list(reversed(dimensions)))
        lines = reordered.labels.read_bytes().splitlines()
        reordered.labels.write_bytes(b"\n".join(lines[1::2] + lines[::2]) + b"\n")
        self.rebind_labels(reordered)
        second, _ = self.assert_valid(reordered)
        self.assertNotEqual(first["input_bundle_sha256"], second["input_bundle_sha256"])
        self.assertEqual({k: first[k] for k in SEMANTIC_KEYS}, {k: second[k] for k in SEMANTIC_KEYS})

    def rebind_labels(self, fixture):
        manifest = fb.read_json(fixture.manifest)
        manifest["hashes"]["labels_sha256"] = fb.sha256(fixture.labels.read_bytes())
        fb.write_json(fixture.manifest, manifest)
        fb.rebind_bundle(fixture)

    def test_unrounded_gap_decides_near_five_percent(self):
        for n, decision in ((72, False), (73, True)):
            with self.subTest(group_size=n):
                examples, labels, dimensions = fb.base_records()
                fb.partition(examples, "region", [("small", n), ("large", 400 - n)])
                fixture = fb.write_fixture(self.temp / str(n), examples, labels, dimensions)
                result, _ = self.assert_valid(fixture, decision)
                self.assertEqual(round(result["worst_group_gap"], 2), 0.05)
                self.assertEqual(result["reason_codes"], [] if decision else ["WORST_GROUP_GAP"])

    def test_unequal_group_outcomes_match_independent_analytical_vector(self):
        examples, labels, dimensions = fb.base_records()
        for label in labels[60:200]:
            label["q1_grounded_label"] = "UNSUPPORTED"
        fixture = fb.write_fixture(self.temp / "unequal", examples, labels, dimensions)
        result, _ = self.assert_valid(fixture, False)
        self.assertEqual(result["counts"]["n_pass"], 260)
        self.assertEqual(result["counts"]["n_fail"], 140)
        self.assertEqual(result["reason_codes"], ["WORST_GROUP_GAP"])
        groups = {g["value"]: g for g in result["dimensions"][0]["groups"]}
        self.assertEqual((groups["a"]["n_pass"], groups["a"]["n_eligible"]), (60, 200))
        self.assertEqual((groups["b"]["n_pass"], groups["b"]["n_eligible"]), (200, 200))
        # Independent 60-decimal-digit analytical evaluation of the declared
        # Wilson expression, rounded here solely for diagnostic assertions.
        self.assertAlmostEqual(result["overall"]["wilson_upper"], 0.6951143509922373, delta=1e-14)
        self.assertAlmostEqual(groups["a"]["wilson_lower"], 0.2407474468237140, delta=1e-14)
        self.assertAlmostEqual(result["worst_group_gap"], 0.45436690416852325, delta=1e-14)
        self.assertEqual(groups["b"]["conservative_gap"], 0)

    def test_undeclared_metadata_is_not_inferred_as_a_dimension(self):
        examples, labels, dimensions = fb.base_records()
        original = fb.write_fixture(self.temp / "plain", examples, labels, dimensions)
        first, _ = self.assert_valid(original)
        for i, row in enumerate(examples):
            row["metadata"]["undeclared_numeric"] = i
            row["metadata"]["undeclared_object"] = {"synthetic": True}
        altered = fb.write_fixture(self.temp / "extra", examples, labels, dimensions)
        second, _ = self.assert_valid(altered)
        self.assertEqual({k: first[k] for k in SEMANTIC_KEYS}, {k: second[k] for k in SEMANTIC_KEYS})

    def test_excluded_rows_still_validate_group_values(self):
        for mode in ("UNKNOWN", "empty_context"):
            with self.subTest(mode=mode):
                examples, labels, dimensions = fb.base_records()
                examples[0]["metadata"]["region"] = None
                if mode == "UNKNOWN":
                    labels[0]["q1_grounded_label"] = "UNKNOWN"
                else:
                    examples[0]["context"] = ""
                    labels[0].update(q1_eligible=False, q1_exclusion_reason="empty_context")
                fixture = fb.write_fixture(self.temp / mode, examples, labels, dimensions)
                self.assert_invalid(fixture, "GROUP_VALUE_INVALID")

    def test_label_join_rejects_duplicate_missing_and_extra_rows(self):
        for mode in ("duplicate", "missing", "extra", "wrong_examples_digest"):
            with self.subTest(mode=mode):
                fixture = fb.materialize(1, self.temp / mode)
                labels = [json.loads(line) for line in fixture.labels.read_bytes().splitlines()]
                if mode == "duplicate":
                    labels[1]["example_id"] = labels[0]["example_id"]
                elif mode == "missing":
                    labels.pop()
                elif mode == "extra":
                    extra = copy.deepcopy(labels[0])
                    extra["example_id"] = "outside-dataset"
                    labels.append(extra)
                else:
                    labels[0]["examples_sha256"] = "0" * 64
                fixture.labels.write_bytes(b"\n".join(fb.row_bytes(row) for row in labels) + b"\n")
                self.rebind_labels(fixture)
                self.assert_invalid(fixture, "DUPLICATE_LABEL_ID" if mode == "duplicate" else "LABEL_JOIN_MISMATCH")

    def test_strict_json_and_jsonl_framing_even_with_refreshed_outer_hashes(self):
        def duplicate_key(data):
            return data.replace(b'"context":', b'"context":"duplicate","context":', 1)
        def bad_number(data):
            return data.replace(b'"metadata":{', b'"metadata":{"undeclared":NaN,', 1)
        def bad_surrogate(data):
            return data.replace(b'"metadata":{', b'"metadata":{"undeclared":"\\ud800",', 1)
        mutations = {
            "duplicate_key": duplicate_key,
            "nonfinite": bad_number,
            "unpaired_surrogate": bad_surrogate,
            "bom": lambda data: b"\xef\xbb\xbf" + data,
            "invalid_utf8": lambda data: data.replace(b"Synthetic", b"\xffynthetic", 1),
            "crlf": lambda data: data.replace(b"\n", b"\r\n"),
            "bare_cr": lambda data: data.replace(b'{"context":', b'{\r"context":', 1),
            "missing_final_lf": lambda data: data[:-1],
            "blank_line": lambda data: data + b"\n",
        }
        for name, mutation in mutations.items():
            with self.subTest(mutation=name):
                fixture = fb.materialize(1, self.temp / name)
                fb.replace_examples_bytes(fixture, mutation(fixture.examples.read_bytes()))
                self.assert_invalid(fixture)

    def test_closed_records_reject_unknown_fields(self):
        for target in ("example", "label", "bundle", "expected",
                       "synthetic_with_archived_anchor", "archived_with_synthetic_anchor"):
            with self.subTest(target=target):
                examples, labels, dimensions = fb.base_records()
                if target == "example":
                    examples[0]["unapproved"] = "extra"
                if target == "label":
                    labels[0]["unapproved"] = "extra"
                fixture = fb.write_fixture(self.temp / target, examples, labels, dimensions)
                if target == "bundle":
                    bundle = fb.read_json(fixture.bundle)
                    bundle["unapproved"] = "extra"
                    fb.write_json(fixture.bundle, bundle)
                    fb.rebind_bundle(fixture)
                if target == "expected":
                    expected = fb.read_json(fixture.expected)
                    expected["unapproved"] = "extra"
                    fb.write_json(fixture.expected, expected)
                if target == "synthetic_with_archived_anchor":
                    expected = fb.read_json(fixture.expected)
                    expected["expectation_origin"] = "caller_selected_archived_input"
                    fb.write_json(fixture.expected, expected)
                if target == "archived_with_synthetic_anchor":
                    bundle = fb.read_json(fixture.bundle)
                    bundle["observation_subject"]["kind"] = "archived_input"
                    fb.write_json(fixture.bundle, bundle)
                    expected = fb.read_json(fixture.expected)
                    expected["observation_subject"] = bundle["observation_subject"]
                    expected["input_bundle_sha256"] = fb.sha256(fixture.bundle.read_bytes())
                    fb.write_json(fixture.expected, expected)
                self.assert_invalid(fixture)

    def test_manifest_overlay_requires_counts_labels_and_sampling_protocol(self):
        for mode in ("wrong_total", "missing_label_origin", "missing_label_digest",
                     "nonfull_no_seed", "nonfull_no_protocol", "nonfull_whitespace_protocol"):
            with self.subTest(mode=mode):
                fixture = fb.materialize(1, self.temp / mode)
                manifest = fb.read_json(fixture.manifest)
                if mode == "wrong_total":
                    manifest["sampling"]["n"] = 401
                elif mode == "missing_label_origin":
                    del manifest["labels"]
                elif mode == "missing_label_digest":
                    del manifest["hashes"]["labels_sha256"]
                elif mode == "nonfull_no_seed":
                    manifest["sampling"].update(strategy="random", notes="Synthetic selection by fixed fixture protocol.")
                elif mode == "nonfull_no_protocol":
                    manifest["sampling"].update(strategy="random", seed=123)
                else:
                    manifest["sampling"].update(strategy="random", seed=123, notes=" \t ")
                fb.write_json(fixture.manifest, manifest)
                fb.rebind_bundle(fixture)
                self.assert_invalid(fixture)

    def test_existing_manifest_allows_uppercase_hash_spelling_and_documented_sampling(self):
        fixture = fb.materialize(1, self.temp / "compatible")
        manifest = fb.read_json(fixture.manifest)
        for key in ("input_sha256", "labels_sha256"):
            manifest["hashes"][key] = manifest["hashes"][key].upper()
        manifest["sampling"].update(strategy="random", seed=123,
                                     notes="Synthetic fixture selection is pre-materialized; no new sampling occurs.")
        fb.write_json(fixture.manifest, manifest)
        fb.rebind_bundle(fixture)
        self.assert_valid(fixture)

    def test_report_tampering_cannot_create_authority_or_hide_changes(self):
        fixture = fb.materialize(1, self.temp / "valid")
        original, summary = self.assert_valid(fixture)
        mutations = {
            "authority": lambda r: r["claims"].update(authority_effect="release"),
            "production": lambda r: r["claims"].update(production_gate_eligible=True),
            "current_run": lambda r: r["claims"].update(current_run_evidence=True),
            "authenticity": lambda r: r["claims"].update(source_authentication="verified"),
            "wrong_expected_hash": lambda r: r.update(expected_context_sha256="0" * 64),
            "wrong_group_count": lambda r: r["dimensions"][0]["groups"][0].update(n_pass=199),
            "tiny_numeric_change": lambda r: r.update(worst_group_gap=r["worst_group_gap"] + 1e-12),
            "unknown_property": lambda r: r.update(unapproved=True),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                altered = copy.deepcopy(original)
                mutate(altered)
                fb.write_json(summary, altered)
                self.check(fixture, summary, 1, receipt_name=f"receipt-{name}.json")
        summary.write_bytes(json.dumps(original, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
        self.check(fixture, summary, 1, receipt_name="receipt-noncanonical.json")

    def assert_reselected_input_schema_rejected(self, fixture, reference_result):
        # All attacker-selected outer bindings are coherent. Rejection must
        # come from the implementation's supported schema, not a stale digest.
        selected_schema = fixture.resources_root / fb.RESOURCE_PATHS["input_schema_sha256"]
        selected_digest = fb.sha256(selected_schema.read_bytes())
        expected = fb.read_json(fixture.expected)
        bundle = fb.read_json(fixture.bundle)
        self.assertEqual(expected["input_schema_sha256"], selected_digest)
        self.assertEqual(bundle["contract_bindings"]["input_schema_sha256"], selected_digest)
        self.assertEqual(expected["input_bundle_sha256"], fb.sha256(fixture.bundle.read_bytes()))
        self.assertNotEqual(selected_digest,
                            fb.sha256((ROOT / fb.RESOURCE_PATHS["input_schema_sha256"]).read_bytes()))

        summary = fixture.root / "new-summary.json"
        producer = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", summary])
        self.assertEqual(producer.returncode, 2, msg=producer.stdout + producer.stderr)
        self.assertIn("FILE_BINDING_MISMATCH", producer.stderr)
        self.assertFalse(summary.exists(), "Unsupported schema must be rejected before a report is written")

        # Seed a formerly self-consistent report with the matching supported
        # calculation, then refresh its input bindings. This tests the checker
        # separately from the fixed producer's refusal to create a report.
        forged = copy.deepcopy(reference_result)
        forged["input_bundle_sha256"] = fb.sha256(fixture.bundle.read_bytes())
        forged["expected_context_sha256"] = fb.sha256(fixture.expected.read_bytes())
        fb.write_json(summary, forged)
        receipt = self.check(fixture, summary, 2)
        self.assertEqual(receipt["verification_result"], "INPUT_INVALID")
        self.assertEqual(receipt["input_validity"], "INVALID")
        self.assertEqual(receipt["reason_codes"], ["FILE_BINDING_MISMATCH"])
        self.assertFalse(receipt["summary_matches"])
        self.assertIsNone(receipt["independently_expected_summary_sha256"])

    def test_reselected_input_schema_cannot_extend_label_enum(self):
        examples, labels, dimensions = fb.base_records()
        for label in labels[:200]:
            label["q1_grounded_label"] = "UNSUPPORTED"
        original = fb.write_fixture(self.temp / "supported-labels", examples, labels, dimensions)
        reference_result, _ = self.assert_valid(original, False)
        self.assertEqual(reference_result["counts"]["n_fail"], 200)

        resources = fb.copy_resources(self.temp / "extended-enum-resources")
        schema_path = resources / fb.RESOURCE_PATHS["input_schema_sha256"]
        schema = fb.read_json(schema_path)
        schema["$defs"]["label_record"]["properties"]["q1_grounded_label"]["enum"].append("OTHER")
        Draft202012Validator.check_schema(schema)
        fb.write_json(schema_path, schema)
        for label in labels[:200]:
            label["q1_grounded_label"] = "OTHER"
        selected = fb.write_fixture(self.temp / "other-labels", examples, labels, dimensions,
                                    resources_root=resources)
        self.assert_reselected_input_schema_rejected(selected, reference_result)

    def test_reselected_input_schema_cannot_open_closed_example_records(self):
        examples, labels, dimensions = fb.base_records()
        original = fb.write_fixture(self.temp / "closed-records", examples, labels, dimensions)
        reference_result, _ = self.assert_valid(original)

        resources = fb.copy_resources(self.temp / "open-record-resources")
        schema_path = resources / fb.RESOURCE_PATHS["input_schema_sha256"]
        schema = fb.read_json(schema_path)
        schema["$defs"]["example_record"]["additionalProperties"] = True
        Draft202012Validator.check_schema(schema)
        fb.write_json(schema_path, schema)
        examples[0]["out_of_contract_field"] = "A selected digest cannot authorize this field."
        selected = fb.write_fixture(self.temp / "open-records", examples, labels, dimensions,
                                    resources_root=resources)
        self.assert_reselected_input_schema_rejected(selected, reference_result)

    def test_exact_input_schema_at_alternate_resources_root_remains_supported(self):
        resources = fb.copy_resources(self.temp / "exact-resources")
        source = ROOT / fb.RESOURCE_PATHS["input_schema_sha256"]
        copied = resources / fb.RESOURCE_PATHS["input_schema_sha256"]
        self.assertEqual(copied.read_bytes(), source.read_bytes())
        fixture = fb.materialize(1, self.temp / "alternate-root", resources_root=resources)
        self.assert_valid(fixture)

    def assert_reselected_profile_rejected(self, fixture, reference_result):
        # A new external anchor selects the changed profile coherently. The
        # implementation's supported contract must still reject its semantics.
        profile_path = fixture.resources_root / fb.RESOURCE_PATHS["contract_sha256"]
        selected_digest = fb.sha256(profile_path.read_bytes())
        expected = fb.read_json(fixture.expected)
        bundle = fb.read_json(fixture.bundle)
        self.assertEqual(expected["contract_sha256"], selected_digest)
        self.assertEqual(bundle["contract_bindings"]["contract_sha256"], selected_digest)
        self.assertEqual(expected["input_bundle_sha256"], fb.sha256(fixture.bundle.read_bytes()))
        self.assertNotEqual(selected_digest,
                            fb.sha256((ROOT / fb.RESOURCE_PATHS["contract_sha256"]).read_bytes()))

        summary = fixture.root / "new-summary.json"
        producer = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", summary])
        self.assertEqual(producer.returncode, 2, msg=producer.stdout + producer.stderr)
        self.assertIn("FILE_BINDING_MISMATCH", producer.stderr)
        self.assertFalse(summary.exists(), "An unsupported profile must not produce a report")

        # Independently test the checker with the old hard-coded calculation
        # and matching new outer bindings, not just a missing producer report.
        forged = copy.deepcopy(reference_result)
        forged["input_bundle_sha256"] = fb.sha256(fixture.bundle.read_bytes())
        forged["expected_context_sha256"] = fb.sha256(fixture.expected.read_bytes())
        fb.write_json(summary, forged)
        receipt = self.check(fixture, summary, 2)
        self.assertEqual(receipt["verification_result"], "INPUT_INVALID")
        self.assertEqual(receipt["input_validity"], "INVALID")
        self.assertEqual(receipt["reason_codes"], ["FILE_BINDING_MISMATCH"])
        self.assertFalse(receipt["summary_matches"])
        self.assertIsNone(receipt["independently_expected_summary_sha256"])

    def test_reselected_profile_cannot_replace_union_with_per_dimension_maximum(self):
        original = fb.materialize(12, self.temp / "supported-union")
        reference_result, _ = self.assert_valid(original, False)
        self.assertEqual(reference_result["coverage"]["excluded_in_any_dimension_count"], 48)
        self.assertEqual(reference_result["coverage"]["excluded_in_any_dimension_fraction"], 0.12)
        self.assertEqual(reference_result["coverage"]["max_per_dimension_small_group_fraction_diagnostic"], 0.06)
        self.assertFalse(reference_result["coverage"]["small_group_coverage_ok"])

        resources = fb.copy_resources(self.temp / "max-dimension-profile-resources")
        profile_path = resources / fb.RESOURCE_PATHS["contract_sha256"]
        profile = fb.read_json(profile_path)
        decision = next(d for d in profile["decisions"] if d["id"] == "Q3_D01_SMALL_GROUP_UNION")
        decision["rule"] = (
            "Small-group coverage passes iff 10 * max_d(len(S_d)) <= len(E); "
            "do not use the deduplicated union."
        )
        fb.write_json(profile_path, profile)
        selected = fb.materialize(12, self.temp / "selected-max-dimension", resources_root=resources)
        self.assert_reselected_profile_rejected(selected, reference_result)

    def test_reselected_profile_cannot_change_recomputation_eligibility(self):
        original = fb.materialize(7, self.temp / "supported-unknown-exclusion")
        reference_result, _ = self.assert_valid(original, False)
        self.assertEqual(reference_result["counts"]["n_unknown_ignored"], 200)
        self.assertEqual(reference_result["counts"]["n_q3_eligible"], 0)

        resources = fb.copy_resources(self.temp / "changed-eligibility-profile-resources")
        profile_path = resources / fb.RESOURCE_PATHS["contract_sha256"]
        profile = fb.read_json(profile_path)
        # This semantic clause is outside decisions and the selected top-level
        # checks. Pinning just Q3_D01 must not leave other contract claims open.
        profile["recomputation_contract"]["eligible"] = (
            "E contains every Q1-eligible example, including UNKNOWN labels."
        )
        fb.write_json(profile_path, profile)
        selected = fb.materialize(7, self.temp / "selected-unknown-inclusion", resources_root=resources)
        self.assert_reselected_profile_rejected(selected, reference_result)

    def test_exact_profile_at_alternate_resources_root_remains_supported(self):
        resources = fb.copy_resources(self.temp / "exact-profile-resources")
        source = ROOT / fb.RESOURCE_PATHS["contract_sha256"]
        copied = resources / fb.RESOURCE_PATHS["contract_sha256"]
        self.assertEqual(copied.read_bytes(), source.read_bytes())
        fixture = fb.materialize(1, self.temp / "exact-profile-alternate-root", resources_root=resources)
        self.assert_valid(fixture)


    def test_fixed_pins_reject_changed_contract_or_schema_resources(self):
        for key, relative in fb.RESOURCE_PATHS.items():
            with self.subTest(resource=relative):
                fixture = fb.materialize(1, self.temp / key)
                fixture.resources_root = fb.copy_resources(fixture.root / "modified_resources")
                path = fixture.resources_root / relative
                path.write_bytes(path.read_bytes() + b" \n")
                if key in ("contract_sha256", "input_schema_sha256"):
                    summary = fixture.root / "summary.json"
                    producer = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", summary])
                    self.assertEqual(producer.returncode, 2, msg=producer.stdout + producer.stderr)
                    self.assertIn("FILE_BINDING_MISMATCH", producer.stderr)
                    self.assertFalse(summary.exists())
                    receipt = self.check(fixture, summary, 2)
                    self.assertEqual(receipt["verification_result"], "INPUT_INVALID")
                    self.assertEqual(receipt["reason_codes"], ["FILE_BINDING_MISMATCH"])
                else:
                    self.assert_invalid(fixture)
        with self.subTest(resource="missing_local_ref_with_new_explicit_anchor"):
            resources = fb.copy_resources(self.temp / "invalid-schema-resources")
            path = resources / fb.RESOURCE_PATHS["input_schema_sha256"]
            schema = fb.read_json(path)
            schema["$defs"]["example_record"] = {"$ref": "#/$defs/nonexistent_definition"}
            fb.write_json(path, schema)
            # Refreshing the caller anchor cannot authorize unsupported schema
            # semantics. Reject its bytes before parsing its local references.
            fixture = fb.materialize(1, self.temp / "bad-local-ref", resources_root=resources)
            summary = fixture.root / "summary.json"
            producer = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", summary])
            self.assertEqual(producer.returncode, 2, msg=producer.stdout + producer.stderr)
            self.assertIn("FILE_BINDING_MISMATCH", producer.stderr)
            self.assertFalse(summary.exists())
            checker = self.invoke(CHECKER, [*self.roots_and_input(fixture), "--summary", summary,
                                            "--receipt", fixture.root / "receipt.json"])
            self.assertEqual(checker.returncode, 2, msg=checker.stdout + checker.stderr)
            receipt = json.loads(checker.stdout)
            self.assertEqual(receipt["verification_result"], "INPUT_INVALID")
            self.assertEqual(receipt["reason_codes"], ["FILE_BINDING_MISMATCH"])

    def test_self_consistency_with_a_new_caller_anchor_is_not_origin_authentication(self):
        examples, labels, dimensions = fb.base_records()
        examples[0]["prompt"] = "A deliberately different, newly selected synthetic dataset."
        fixture = fb.write_fixture(self.temp / "new_anchor", examples, labels, dimensions,
                                   dataset_id="new-synthetic-source-selected-by-caller")
        result, _ = self.assert_valid(fixture)
        self.assertEqual(result["claims"]["source_authentication"], "not_established")
        self.assertEqual(result["claims"]["label_correctness"], "not_verified")
        self.assertFalse(result["claims"]["current_run_evidence"])

    def test_path_escape_and_symlink_inputs_are_rejected(self):
        fixture = fb.materialize(1, self.temp / "escape")
        bundle = fb.read_json(fixture.bundle)
        bundle["artifacts"]["examples_jsonl"]["path"] = "../outside.jsonl"
        fb.write_json(fixture.bundle, bundle)
        expected = fb.read_json(fixture.expected)
        expected["input_bundle_sha256"] = fb.sha256(fixture.bundle.read_bytes())
        fb.write_json(fixture.expected, expected)
        self.assert_invalid(fixture)
        fixture = fb.materialize(1, self.temp / "symlink")
        original = fixture.labels.read_bytes()
        target = fixture.root / "label_target.jsonl"
        target.write_bytes(original)
        fixture.labels.unlink()
        fixture.labels.symlink_to(target.name)
        self.assert_invalid(fixture)

    def test_output_never_overwrites_bundle_expected_or_data_inputs(self):
        for target in ("bundle", "expected", "labels"):
            with self.subTest(target=target):
                fixture = fb.materialize(1, self.temp / target)
                path = getattr(fixture, target)
                before = path.read_bytes()
                completed = self.invoke(PRODUCER, [*self.roots_and_input(fixture), "--out", path])
                self.assertEqual(completed.returncode, 2, msg=completed.stdout + completed.stderr)
                self.assertEqual(path.read_bytes(), before, "Input bytes changed by forbidden output path")

    def test_checker_receipt_never_overwrites_inputs_or_summary(self):
        for target in ("bundle", "expected", "labels", "summary"):
            with self.subTest(target=target):
                fixture = fb.materialize(1, self.temp / target)
                _, summary = self.assert_valid(fixture)
                path = summary if target == "summary" else getattr(fixture, target)
                before = path.read_bytes()
                completed = self.invoke(CHECKER, [*self.roots_and_input(fixture),
                                                  "--summary", summary, "--receipt", path])
                self.assertEqual(completed.returncode, 2, msg=completed.stdout + completed.stderr)
                self.assertEqual(path.read_bytes(), before, "Input/report bytes changed by receipt output")

    def receipt_writer_module(self):
        name = f"q3_checker_receipt_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(name, CHECKER)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        return module

    def assert_receipt_failure_is_cleaned_up(self, failure):
        checker = self.receipt_writer_module()
        destination = self.temp / "receipt.json"
        payload = b'{"receipt":"synthetic fault injection"}\n'
        original_write = os.write
        write_calls = 0
        bytes_at_failure = None

        def failing_write(descriptor, data):
            nonlocal write_calls, bytes_at_failure
            write_calls += 1
            if failure == "zero_progress":
                bytes_at_failure = os.fstat(descriptor).st_size
                return 0
            if write_calls == 1:
                return original_write(descriptor, data[:7])
            bytes_at_failure = os.fstat(descriptor).st_size
            raise OSError("injected quota failure after partial write")

        def failing_fsync(descriptor):
            nonlocal bytes_at_failure
            bytes_at_failure = os.fstat(descriptor).st_size
            raise OSError("injected fsync failure")

        operation = "fsync" if failure == "fsync" else "write"
        injected = failing_fsync if failure == "fsync" else failing_write
        with mock.patch.object(checker.os, operation, side_effect=injected):
            with self.assertRaises(checker.InputProblem) as caught:
                checker.write_receipt_new(str(destination), payload)
        self.assertEqual(caught.exception.code, "RECEIPT_WRITE_FAILED")
        self.assertEqual(bytes_at_failure, {"partial_write": 7, "zero_progress": 0,
                                           "fsync": len(payload)}[failure])
        self.assertFalse(destination.exists(), "Failed receipt must not retain the destination")
        checker.write_receipt_new(str(destination), payload)
        self.assertEqual(destination.read_bytes(), payload, "The same path must be reusable after cleanup")

    def test_checker_receipt_partial_write_failure_cleans_up_and_allows_retry(self):
        self.assert_receipt_failure_is_cleaned_up("partial_write")

    def test_checker_receipt_zero_progress_cleans_up_and_allows_retry(self):
        self.assert_receipt_failure_is_cleaned_up("zero_progress")

    def test_checker_receipt_fsync_failure_cleans_up_and_allows_retry(self):
        self.assert_receipt_failure_is_cleaned_up("fsync")

    def test_checker_receipt_failure_preserves_preexisting_files_and_links(self):
        checker = self.receipt_writer_module()
        sentinel = b"existing evidence must remain unchanged\n"
        for kind in ("regular", "hardlink", "symlink"):
            with self.subTest(destination=kind):
                target = self.temp / f"target-{kind}"
                target.write_bytes(sentinel)
                destination = self.temp / f"receipt-{kind}.json"
                if kind == "regular":
                    destination.write_bytes(sentinel)
                elif kind == "hardlink":
                    os.link(target, destination)
                else:
                    destination.symlink_to(target.name)
                before = destination.lstat()
                with mock.patch.object(checker.os, "write", side_effect=AssertionError("Existing output was opened for writing")):
                    with self.assertRaises(checker.InputProblem) as caught:
                        checker.write_receipt_new(str(destination), b"new receipt\n")
                self.assertEqual(caught.exception.code, "RECEIPT_WRITE_FAILED")
                after = destination.lstat()
                self.assertEqual((after.st_dev, after.st_ino), (before.st_dev, before.st_ino))
                self.assertEqual(destination.read_bytes(), sentinel)
                self.assertEqual(target.read_bytes(), sentinel)
                self.assertEqual(destination.is_symlink(), kind == "symlink")

    def test_checker_receipt_failure_preserves_substituted_destination(self):
        checker = self.receipt_writer_module()
        original_write = os.write
        sentinel = b"replacement evidence must remain unchanged\n"
        for kind in ("regular", "symlink"):
            with self.subTest(replacement=kind):
                destination = self.temp / f"receipt-{kind}.json"
                moved_receipt = self.temp / f"moved-{kind}.json"
                target = self.temp / f"target-{kind}"
                target.write_bytes(sentinel)
                replacement_identity = None

                def replace_then_fail(descriptor, data):
                    nonlocal replacement_identity
                    original_write(descriptor, data[:7])
                    destination.rename(moved_receipt)
                    if kind == "regular":
                        destination.write_bytes(sentinel)
                    else:
                        destination.symlink_to(target.name)
                    replacement = destination.lstat()
                    replacement_identity = (replacement.st_dev, replacement.st_ino)
                    raise OSError("injected write failure after destination substitution")

                with mock.patch.object(checker.os, "write", side_effect=replace_then_fail):
                    with self.assertRaises(checker.InputProblem) as caught:
                        checker.write_receipt_new(str(destination), b"new receipt\n")
                self.assertEqual(caught.exception.code, "RECEIPT_WRITE_FAILED")
                after = destination.lstat()
                self.assertEqual((after.st_dev, after.st_ino), replacement_identity)
                self.assertEqual(destination.read_bytes(), sentinel)
                self.assertEqual(target.read_bytes(), sentinel)
                self.assertEqual(destination.is_symlink(), kind == "symlink")
                self.assertEqual(moved_receipt.read_bytes(), b"new rec")

    def test_checker_receipt_cleanup_failure_retains_original_error(self):
        checker = self.receipt_writer_module()
        destination = self.temp / "receipt.json"
        original_write = os.write
        write_failure = OSError("injected primary write failure")

        def write_then_fail(descriptor, data):
            original_write(descriptor, data[:7])
            raise write_failure

        with mock.patch.object(checker.os, "write", side_effect=write_then_fail):
            with mock.patch.object(checker.os, "unlink", side_effect=OSError("injected cleanup denial")):
                with self.assertRaises(checker.InputProblem) as caught:
                    checker.write_receipt_new(str(destination), b"new receipt\n")
        self.assertEqual(caught.exception.code, "RECEIPT_WRITE_FAILED")
        self.assertIs(caught.exception.__cause__, write_failure)
        self.assertEqual(destination.read_bytes(), b"new rec")

    def producer_snapshot_module(self):
        name = f"q3_producer_snapshot_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(name, PRODUCER)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        return module

    def test_producer_snapshot_unchanged_hardlink_reuses_original_bytes(self):
        producer = self.producer_snapshot_module()
        first = self.temp / "first.bin"
        alias = self.temp / "alias.bin"
        data = b"unchanged synthetic snapshot\n"
        first.write_bytes(data)
        os.link(first, alias)
        snapshots = producer.Snapshots()
        self.assertEqual(snapshots.read(first), data)
        with mock.patch.object(producer.os, "read", side_effect=AssertionError("Hardlink bytes were read twice")):
            self.assertEqual(snapshots.read(alias), data)

    def test_producer_snapshot_rejects_rewritten_hardlink_with_same_length(self):
        producer = self.producer_snapshot_module()
        first = self.temp / "first.bin"
        alias = self.temp / "alias.bin"
        first.write_bytes(b"before\n")
        os.link(first, alias)
        snapshots = producer.Snapshots()
        self.assertEqual(snapshots.read(first), b"before\n")
        before = alias.stat()
        alias.write_bytes(b"after!\n")
        os.utime(alias, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        after = alias.stat()
        self.assertEqual((before.st_dev, before.st_ino, before.st_size),
                         (after.st_dev, after.st_ino, after.st_size))
        with self.assertRaises(producer.InputFailure) as caught:
            snapshots.read(alias)
        self.assertEqual(caught.exception.code, "FILE_BINDING_MISMATCH")

    def test_producer_snapshot_distinct_inodes_remain_independent(self):
        producer = self.producer_snapshot_module()
        first = self.temp / "first.bin"
        second = self.temp / "second.bin"
        first.write_bytes(b"initial\n")
        second.write_bytes(b"initial\n")
        self.assertFalse(os.path.samefile(first, second))
        snapshots = producer.Snapshots()
        self.assertEqual(snapshots.read(first), b"initial\n")
        second.write_bytes(b"changed\n")
        self.assertEqual(snapshots.read(second), b"changed\n")
        self.assertEqual(snapshots.read(first), b"initial\n")

    def test_producer_snapshot_mutation_during_read_still_fails_closed(self):
        producer = self.producer_snapshot_module()
        path = self.temp / "changing.bin"
        path.write_bytes(b"before\n")
        original_read = os.read
        changed = False

        def read_then_rewrite(descriptor, length):
            nonlocal changed
            data = original_read(descriptor, length)
            if data and not changed:
                before = path.stat()
                path.write_bytes(b"after!\n")
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                changed = True
            return data

        with mock.patch.object(producer.os, "read", side_effect=read_then_rewrite):
            with self.assertRaises(producer.InputFailure) as caught:
                producer.Snapshots().read(path)
        self.assertTrue(changed)
        self.assertEqual(caught.exception.code, "FILE_BINDING_MISMATCH")

    def test_producer_hardlink_rewrite_cannot_mix_example_and_label_snapshots(self):
        producer = self.producer_snapshot_module()
        fixture = fb.materialize(1, self.temp / "hardlinked-artifacts")
        examples_bytes = fixture.examples.read_bytes()
        labels_bytes = fixture.labels.read_bytes()
        self.assertNotEqual(examples_bytes, labels_bytes)
        original_bundle = fixture.bundle.read_bytes()
        original_expected = fixture.expected.read_bytes()
        fixture.labels.unlink()
        os.link(fixture.examples, fixture.labels)
        self.assertTrue(os.path.samefile(fixture.examples, fixture.labels))
        original_read = producer.Snapshots.read
        examples_read = False
        rewrites = 0

        def rewrite_before_label_snapshot(snapshots, path):
            nonlocal examples_read, rewrites
            absolute = Path(os.path.abspath(os.fspath(path)))
            if absolute == fixture.labels:
                self.assertTrue(examples_read, "Mutation must follow the completed examples read")
                before = fixture.labels.stat()
                fixture.labels.write_bytes(labels_bytes)
                os.utime(fixture.labels, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                after = fixture.labels.stat()
                self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
                rewrites += 1
            data = original_read(snapshots, path)
            if absolute == fixture.examples:
                self.assertEqual(data, examples_bytes)
                examples_read = True
            return data

        summary = fixture.root / "summary.json"
        arguments = [*self.roots_and_input(fixture), "--out", summary]
        with mock.patch.object(producer.Snapshots, "read", rewrite_before_label_snapshot):
            exit_code = producer.main([os.fspath(argument) for argument in arguments])
        self.assertEqual(rewrites, 1)
        self.assertEqual(exit_code, 2)
        result = fb.read_json(summary)
        self.result_validator.validate(result)
        self.assertEqual(result["input_validity"], "INVALID")
        self.assertEqual(result["reason_codes"], ["FILE_BINDING_MISMATCH"])
        self.assertFalse(result["pass"])
        self.assertIsNone(result["counts"])
        self.assertEqual(fixture.bundle.read_bytes(), original_bundle)
        self.assertEqual(fixture.expected.read_bytes(), original_expected)

    def test_file_line_and_dimension_limits_fail_closed(self):
        for target in ("file", "line", "dimensions"):
            with self.subTest(target=target):
                if target == "file":
                    fixture = fb.materialize(1, self.temp / target)
                    # A sparse oversized file reaches the stat-size boundary
                    # without allocating a 64 MiB test string or new evidence.
                    with fixture.examples.open("wb") as stream:
                        stream.truncate(64 * 1024 * 1024 + 1)
                else:
                    examples, labels, dimensions = fb.base_records()
                    if target == "line":
                        examples[0]["prompt"] = "x" * (1024 * 1024)
                    else:
                        dimensions = [f"d{i:02d}" for i in range(65)]
                        for row in examples:
                            row["metadata"] = {name: "all" for name in dimensions}
                    fixture = fb.write_fixture(self.temp / target, examples, labels, dimensions)
                self.assert_invalid(fixture, "INPUT_LIMIT")

    def test_checker_has_no_producer_import_or_process_execution_dependency(self):
        tree = ast.parse(CHECKER.read_text(encoding="utf-8"), filename=str(CHECKER))
        forbidden_modules = {"subprocess", "runpy", "importlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("build_q3_reference_summary", alias.name)
                    self.assertNotIn(alias.name.split(".")[0], forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("build_q3_reference_summary", node.module or "")
                self.assertNotIn((node.module or "").split(".")[0], forbidden_modules)
                for alias in node.names:
                    self.assertNotIn("build_q3_reference_summary", alias.name)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"exec", "eval", "compile", "__import__"})

    def test_producer_and_checker_stop_report_expansion_at_output_budget(self):
        # Exercise each independently written guard with a small isolated cap.
        # The checker itself still never imports the producer. No large payload
        # or model call is needed to reach either allocation failure boundary.
        for kind, path in (("producer", PRODUCER), ("checker", CHECKER)):
            name = f"q3_{kind}_output_budget_test"
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            self.addCleanup(sys.modules.pop, name, None)
            spec.loader.exec_module(module)
            module.MAX_FILE_BYTES = 1024
            error = module.InputFailure if kind == "producer" else module.InputProblem
            for mode in ("groups", "excluded_records"):
                with self.subTest(implementation=kind, expansion=mode):
                    rows, labels, dimensions = fb.base_records(40)
                    for i, (row, label) in enumerate(zip(rows, labels)):
                        row["metadata"]["region"] = f"distinct-{i:02d}"
                        if mode == "excluded_records":
                            label["q1_grounded_label"] = "UNKNOWN"
                    labels_by_id = {label["example_id"]: label for label in labels}
                    with self.assertRaises(error) as caught:
                        if kind == "checker":
                            examples_by_id = {row["example_id"]: (row, fb.sha256(fb.row_bytes(row))) for row in rows}
                            module.recompute(examples_by_id, labels_by_id, dimensions)
                        else:
                            examples_by_id = {row["example_id"]: row for row in rows}
                            bundle = {"dataset_id": "synthetic-budget-test", "reduction_id": "synthetic-budget-test",
                                      "observation_subject": {"kind": "synthetic_fixture", "subject_id": "budget",
                                                              "source_reference": "urn:pulse:synthetic:budget", "runtime_identity": None}}
                            observed = {"input_bundle_sha256": None, "expected_context_sha256": None}
                            module.recompute(bundle, examples_by_id, labels_by_id, dimensions, {}, observed)
                    self.assertEqual(caught.exception.code, "INPUT_LIMIT")


def _design_case_test(case_id, variant):
    def test(self):
        self.run_design_case(case_id, variant)
    suffix = "" if variant is None else "_" + variant
    test.__name__ = f"test_design_case_{case_id:03d}{suffix}"
    test.__doc__ = CASES[case_id]["title"] + ("" if variant is None else " / " + variant)
    return test


for _case_id in sorted(CASES):
    for _variant in fb.variants(_case_id):
        _test = _design_case_test(_case_id, _variant)
        setattr(Q3ReferenceRecomputationTests, _test.__name__, _test)


if __name__ == "__main__":
    unittest.main(verbosity=2)
