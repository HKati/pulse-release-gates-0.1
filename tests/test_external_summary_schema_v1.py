#!/usr/bin/env python3
"""
PULSE-REF external summary schema tests v1.

These tests validate the canonical external summary schema and envelope schema
used by PULSE-REF release-grade evidence handling.

The tests do not define release authority.
They verify evidence-shape and verification-before-fold-in constraints only.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SCHEMA_PATH = ROOT / "schemas" / "external_summary_v1.schema.json"
ENVELOPE_SCHEMA_PATH = ROOT / "schemas" / "external_summary_envelope_v1.schema.json"
SIGNER_POLICY_PATH = ROOT / "policy" / "external_signers_v1.yml"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_jsonschema():
    try:
        import jsonschema  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest("jsonschema is not available") from exc

    return jsonschema


def valid_summary() -> dict[str, Any]:
    return {
        "schema_version": "external_summary_v1",
        "summary_id": "summary-1",
        "tool": {
            "name": "promptfoo",
            "version": "1.0.0",
            "adapter": "promptfoo_to_summary_v1",
            "adapter_version": "v1"
        },
        "run": {
            "run_id": "run-1",
            "generated_at": "2026-05-03T00:00:00Z",
            "dataset_digest": "a" * 64,
            "evaluator_digest": "b" * 64,
            "model_id": "pulse-ref-candidate"
        },
        "subject": {
            "kind": "release_candidate",
            "id": "pulse-ref-candidate",
            "digest_algorithm": "sha256",
            "digest": "c" * 64
        },
        "metrics": [
            {
                "key": "jailbreak_fail_rate",
                "value": 0.0,
                "unit": "rate",
                "threshold": 0.01,
                "comparator": "lte",
                "passed": True,
                "severity": "critical"
            }
        ],
        "threshold_ref": {
            "key": "pulse_ref_external_thresholds_v1",
            "version": "v1",
            "uri": "policy/external_thresholds_v1.yml"
        },
        "evidence": {
            "raw_artifact_uri": "artifacts/external/promptfoo_raw.json",
            "raw_artifact_digest": "d" * 64,
            "summary_digest": "e" * 64
        },
        "signing": {
            "mode": "sigstore-keyless",
            "identity": "repo:HKati/pulse-release-gates-0.1:workflow:external-eval",
            "bundle_path": "artifacts/external/promptfoo_summary.sigstore.json",
            "verified": True
        },
        "result": {
            "passed": True,
            "reason": "All release-grade external checks passed.",
            "release_contribution": "required"
        },
        "authority_boundary": "This external summary does not define release authority. It is recorded evidence that may be folded into status.json only after schema, identity, signer, and policy validation."
    }


def valid_envelope() -> dict[str, Any]:
    return {
        "schema_version": "external_summary_envelope_v1",
        "envelope_id": "env-1",
        "summary_ref": {
            "uri": "external_summary.json",
            "schema_version": "external_summary_v1",
            "summary_id": "summary-1"
        },
        "summary_digest": {
            "algorithm": "sha256",
            "value": "f" * 64
        },
        "signing": {
            "mode": "sigstore-keyless",
            "identity": "repo:HKati/pulse-release-gates-0.1:workflow:external-eval",
            "issuer": "https://token.actions.githubusercontent.com",
            "bundle_uri": "external_summary.sigstore.json"
        },
        "verification": {
            "verified": True,
            "verified_at": "2026-05-03T00:00:00Z",
            "verifier": {
                "name": "pulse-verifier",
                "version": "v1"
            },
            "result_reason": "Signature and identity verified."
        },
        "policy_context": {
            "signer_policy_ref": "policy/external_signers_v1.yml",
            "threshold_policy_ref": "policy/external_thresholds_v1.yml",
            "release_contribution": "required",
            "fold_in_allowed": True
        },
        "authority_boundary": "This external summary envelope does not define release authority. It records digest, signer, verification, and policy context for external evidence before any policy-controlled fold-in to status.json."
    }


class TestExternalSummarySchemaV1(unittest.TestCase):
    def setUp(self) -> None:
        self.jsonschema = require_jsonschema()
        self.summary_schema = load_json(SUMMARY_SCHEMA_PATH)
        self.envelope_schema = load_json(ENVELOPE_SCHEMA_PATH)

        self.jsonschema.Draft202012Validator.check_schema(self.summary_schema)
        self.jsonschema.Draft202012Validator.check_schema(self.envelope_schema)

        self.summary_validator = self.jsonschema.Draft202012Validator(self.summary_schema)
        self.envelope_validator = self.jsonschema.Draft202012Validator(self.envelope_schema)

    def test_valid_external_summary_passes_schema(self) -> None:
        self.summary_validator.validate(valid_summary())

    def test_external_summary_requires_tool_version(self) -> None:
        doc = valid_summary()
        del doc["tool"]["version"]

        errors = list(self.summary_validator.iter_errors(doc))
        self.assertTrue(errors)
        self.assertTrue(any("version" in str(error) for error in errors))

    def test_external_summary_requires_subject_digest(self) -> None:
        doc = valid_summary()
        del doc["subject"]["digest"]

        errors = list(self.summary_validator.iter_errors(doc))
        self.assertTrue(errors)
        self.assertTrue(any("digest" in str(error) for error in errors))

    def test_external_summary_rejects_bad_sha256_digest(self) -> None:
        doc = valid_summary()
        doc["subject"]["digest"] = "not-a-sha256"

        errors = list(self.summary_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_external_summary_requires_metric_items(self) -> None:
        doc = valid_summary()
        doc["metrics"] = []

        errors = list(self.summary_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_external_summary_requires_authority_boundary(self) -> None:
        doc = valid_summary()
        del doc["authority_boundary"]

        errors = list(self.summary_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_valid_envelope_passes_schema(self) -> None:
        self.envelope_validator.validate(valid_envelope())

    def test_envelope_requires_summary_digest(self) -> None:
        doc = valid_envelope()
        del doc["summary_digest"]

        errors = list(self.envelope_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_envelope_requires_signing_identity(self) -> None:
        doc = valid_envelope()
        del doc["signing"]["identity"]

        errors = list(self.envelope_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_envelope_requires_verifier_identity(self) -> None:
        doc = valid_envelope()
        del doc["verification"]["verifier"]["name"]

        errors = list(self.envelope_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_envelope_rejects_fold_in_when_unverified(self) -> None:
        doc = valid_envelope()
        doc["verification"]["verified"] = False
        doc["policy_context"]["fold_in_allowed"] = True

        errors = list(self.envelope_validator.iter_errors(doc))
        self.assertTrue(
            errors,
            "Envelope must reject fold_in_allowed=true when verification.verified=false.",
        )

    def test_envelope_allows_unverified_when_fold_in_not_allowed(self) -> None:
        doc = valid_envelope()
        doc["verification"]["verified"] = False
        doc["policy_context"]["fold_in_allowed"] = False

        self.envelope_validator.validate(doc)

    def test_envelope_authority_boundary_is_required(self) -> None:
        doc = valid_envelope()
        del doc["authority_boundary"]

        errors = list(self.envelope_validator.iter_errors(doc))
        self.assertTrue(errors)

    def test_signer_policy_exists_and_is_yaml(self) -> None:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest("PyYAML is not available") from exc

        policy = yaml.safe_load(SIGNER_POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], "external_signers_v1")
        self.assertTrue(policy["release_grade_defaults"]["require_verification_before_fold_in"])
        self.assertFalse(policy["release_grade_defaults"]["allow_unsigned_release_grade"])
        self.assertFalse(policy["release_grade_defaults"]["allow_unverified_fold_in"])
        self.assertEqual(
            policy["failure_behavior"]["unsigned_release_grade_summary"],
            "fail_closed",
        )
        self.assertIn(
            "does not define release authority",
            policy["authority_boundary"]["statement"],
        )


if __name__ == "__main__":
    unittest.main()
