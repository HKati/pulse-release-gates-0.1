#!/usr/bin/env python3
"""WP2C: offline materialized verifier-record bindings, never semantic authority.

Run the installed WP2A/WP2B checker afresh, using one bounded BundleReader
snapshot for packets, sources and records. A matching record is still a
recorded declaration, not proof of verifier identity or execution.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "local_verifier_record_bindings_v1"
BINDING_PROFILES = ("wp2a", "wp2b-json-pointer-v1")
SCHEMAS = {
    "set": "anchor_integrity_verifier_record_set_v0_1.schema.json",
    "record": "anchor_integrity_verifier_record_v0_1.schema.json",
    "report": "anchor_integrity_verifier_record_report_v0_1.schema.json",
}
STATUSES = {
    "consistent": "LOCAL_RECORD_BINDINGS_CONSISTENT",
    "invalid": "LOCAL_RECORD_BINDINGS_INVALID",
    "incomplete": "LOCAL_RECORD_BINDINGS_INCOMPLETE",
}
UNPERFORMED = (
    "source_identity_authentication", "acquisition_authentication",
    "subject_observation_authentication", "verifier_identity_authentication",
    "verifier_execution_attestation", "semantic_support_verification",
    "typed_evidence_cycle_check", "response_mode_recommendation",
    "claim_set_completeness", "verified_binding_coverage",
    "verified_support_coverage",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def report_bytes(report: dict[str, Any]) -> bytes:
    """The exact stdout representation, also used for the base-report digest."""
    return (json.dumps(report, sort_keys=True, ensure_ascii=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def load_binding_checker() -> Any:
    """Load only the installed, trusted checker; artifacts never select code."""
    path = ROOT / "tools" / "check_anchor_integrity_bindings_v0_1.py"
    spec = importlib.util.spec_from_file_location("anchor_binding_wp2c_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("binding_checker_unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


class RecordSchemas:
    """Fixed self-contained schemas from the trusted installation, not input."""
    def __init__(self, base: Any) -> None:
        self.base = base
        self.hashes: dict[str, str] = {}
        self.validators: dict[str, Any] = {}
        for role, name in SCHEMAS.items():
            raw = (ROOT / "schemas" / name).read_bytes()
            schema = base.strict_json(raw)
            base._assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.validators[role] = jsonschema.Draft202012Validator(schema)
            self.hashes[name] = digest(raw)

    def validate(self, role: str, value: Any) -> None:
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise self.base.BindingError("schema_invalid_verifier_" + role)


class RecordReview:
    def __init__(self, base: Any, binding_profile: str) -> None:
        if binding_profile not in BINDING_PROFILES:
            raise base.BindingError("unsupported_binding_profile")
        self.base = base
        self.schemas = RecordSchemas(base)
        self.binding = base.Review(base.SchemaSet(binding_profile))
        self.profile = binding_profile
        self.report: dict[str, Any] = {
            "schema_version": "anchor_integrity_verifier_record_report_v0_1",
            "work_package": "WP2C", "profile": PROFILE,
            "verification_scope": "offline_bytes_and_recorded_verifier_links",
            "candidate_status": "diagnostic_only", "authority_effect": "none",
            "release_authority_activation": False, "requested_checks_complete": False,
            "accepted_as_semantic_support": False,
            "status": STATUSES["incomplete"], "binding_profile": binding_profile,
            "expected_digests": {k: None for k in ("input", "carriers", "record_set")},
            "observed_digests": {k: None for k in ("input", "carriers", "record_set")},
            "base_check": {"status": None, "report_sha256": None},
            "record_check": {"status": "not_run", "result": None,
                             "reason": "prerequisites_not_established"},
            "counts": {k: None for k in ("completed_relations", "listed_records", "matching_records")},
            "records": [], "issues": [],
            "unperformed_checks": {
                k: {"status": "not_run", "result": None,
                    "reason": "outside_wp2c_record_binding_scope"} for k in UNPERFORMED
            },
            "implementation": {
                "checker_sha256": digest(Path(__file__).read_bytes()),
                "binding_checker_sha256": self.binding.report["implementation"]["checker_sha256"],
                "json_pointer_module_sha256": self.binding.report["implementation"].get("json_pointer_module_sha256"),
                "schema_sha256": {**self.binding.schemas.hashes, **self.schemas.hashes},
            },
        }

    def issue(self, code: str, object_id: str, severity: str = "invalid") -> None:
        self.report["issues"].append({"code": code, "object_id": object_id,
                                      "severity": severity})

    def bound_set(self, reader: Any, path: str, expected: str) -> dict[str, Any]:
        raw = reader.read(path, "wp2c.record_set")
        self.report["observed_digests"]["record_set"] = digest(raw)
        if digest(raw) != expected:
            raise self.base.BindingError("record_set_digest_mismatch")
        value = self.base.strict_json(raw)
        self.schemas.validate("set", value)
        return value

    def prepare(self, reader: Any, record_set: dict[str, Any], *,
                input_path: str, input_digest: str, carriers_path: str,
                carriers_digest: str) -> None:
        expected = {
            "binding_profile": self.profile,
            "input_binding": {"path": input_path, "sha256": input_digest},
            "carriers_binding": {"path": carriers_path, "sha256": carriers_digest},
        }
        for key, value in expected.items():
            if record_set[key] != value:
                raise self.base.BindingError("record_set_" + key + "_mismatch")
        entries = record_set["records"]
        self.base._index(entries, "record_id")
        self.base._index(entries, "binding_id")
        # Reserve record paths before base checking, so a record cannot alias
        # a packet/source/response/manifest path even if hashes were recomputed.
        for entry in entries:
            reader.reserve(entry["path"], "wp2c.record:" + entry["record_id"])
        self.report["counts"]["listed_records"] = len(entries)

    def run_base(self, reader: Any, input_path: str, expected_input: str,
                 carriers_path: str, expected_carriers: str) -> bool:
        try:
            self.binding.review(reader, input_path, expected_input,
                                carriers_path, expected_carriers)
        except self.base.BindingError as exc:
            self.binding.issue(exc.code, "bundle", exc.severity)
        result = self.binding.finish()
        self.report["base_check"] = {
            "status": result["status"], "report_sha256": digest(report_bytes(result))}
        for kind, path in (("input", input_path), ("carriers", carriers_path)):
            raw = reader.cache.get(path)
            if raw is not None:
                self.report["observed_digests"][kind] = digest(raw)
        for issue in result["issues"]:
            self.issue("base." + issue["code"], issue["object_id"], issue["severity"])
        return result["status"] == "LOCAL_BINDINGS_CONSISTENT"

    def cached_json(self, reader: Any, path: str) -> dict[str, Any]:
        # Access exactly the bytes retained by the successful base check.
        # No second read or caller-supplied saved report can replace them.
        if path not in reader.cache:
            raise self.base.BindingError("base_snapshot_missing")
        value = self.base.strict_json(reader.cache[path])
        if not isinstance(value, dict):
            raise self.base.BindingError("base_snapshot_not_object")
        return value

    def records(self, reader: Any, record_set: dict[str, Any], input_path: str) -> None:
        inp = self.cached_json(reader, input_path)
        bindings = inp["packet_bindings"]
        packets = {
            role: self.cached_json(reader, bindings[key]["path"])
            for role, key in (("claims", "claim_packet"), ("evidence", "evidence_packet"),
                              ("relations", "relation_verification_packet"))
        }
        packet_digests = {
            role: digest(reader.cache[bindings[key]["path"]])
            for role, key in (("claims", "claim_packet"), ("evidence", "evidence_packet"),
                              ("relations", "relation_verification_packet"))
        }
        claims = self.base._index(packets["claims"]["claim_set"]["claims"], "claim_id")
        sources = self.base._index(packets["evidence"]["sources"], "source_id")
        evidence = self.base._index(packets["evidence"]["evidence_items"], "evidence_id")
        relations = self.base._index(packets["relations"]["relations"], "binding_id")
        completed = {k: r for k, r in relations.items()
                     if r["relation_verification"]["status"] == "completed"}
        # This profile is one materialized record per completed relation.
        # Multi-relation records require a separate declared contract.
        record_ids = [r["verifier_record_id"] for r in completed.values()]
        if len(set(record_ids)) != len(record_ids):
            self.issue("verifier_record_id_reused", "relations")
        entries = {e["binding_id"]: e for e in record_set["records"]}
        self.report["counts"].update(completed_relations=len(completed), matching_records=0)
        for binding_id in sorted(completed.keys() - entries.keys()):
            self.issue("verifier_record_not_listed", binding_id, "incomplete")
        for binding_id in sorted(entries.keys() - completed.keys()):
            self.issue("record_without_completed_relation", binding_id)
        for binding_id, entry in sorted(entries.items()):
            relation = completed.get(binding_id)
            row: dict[str, Any] = {
                "binding_id": binding_id, "record_id": entry["record_id"],
                "expected_sha256": entry["sha256"], "observed_sha256": None,
                "status": "not_run", "result": None, "reason": None,
                "mismatched_fields": [], "declared_result": None,
                "accepted_as_semantic_support": False,
            }
            self.report["records"].append(row)
            if relation is None:
                row["reason"] = "record_without_completed_relation"
                continue
            try:
                raw = reader.read(entry["path"], "wp2c.record:" + entry["record_id"])
                row["observed_sha256"] = digest(raw)
                if digest(raw) != entry["sha256"]:
                    row.update(status="completed", result="mismatch", reason="record_digest_mismatch")
                    self.issue("record_digest_mismatch", binding_id)
                    continue
                record = self.base.strict_json(raw)
                self.schemas.validate("record", record)
                claim = claims[relation["claim_id"]]
                item = evidence[relation["evidence_id"]]
                source = sources[item["source_id"]]
                expected = {
                    "record_id": relation["verifier_record_id"],
                    "subject": inp["subject"],
                    "input_sha256": self.report["expected_digests"]["input"],
                    "carriers_sha256": self.report["expected_digests"]["carriers"],
                    "packet_sha256": packet_digests,
                    "binding": {
                        "binding_id": binding_id, "claim_id": claim["claim_id"],
                        "claim_digest": claim["claim_digest"],
                        "evidence_id": item["evidence_id"], "source_id": source["source_id"],
                        "source_sha256": source["content_sha256"],
                        "evidence_sha256": item["content_sha256"],
                        "relation_type": relation["relation_type"],
                    },
                    "verifier": entry["expected_verifier"],
                    "verification": relation["relation_verification"],
                }
                mismatched = [k for k, value in expected.items() if record[k] != value]
                if entry["record_id"] != relation["verifier_record_id"]:
                    mismatched.append("manifest_record_id")
                row["mismatched_fields"] = sorted(mismatched)
                row.update(status="completed", result="mismatch" if mismatched else "match",
                           reason="record_binding_mismatch" if mismatched else None)
                if mismatched:
                    self.issue("record_binding_mismatch", binding_id)
                else:
                    # A matched declared label is not an endorsed semantic verdict.
                    row["declared_result"] = record["verification"]["result"]
                    self.report["counts"]["matching_records"] += 1
            except self.base.BindingError as exc:
                row.update(status="not_run", result=None, reason=exc.code)
                self.issue(exc.code, binding_id, exc.severity)
        self.report["record_check"] = {"status": "completed", "result": "match", "reason": None}

    def finish(self) -> dict[str, Any]:
        issues = self.report["issues"]
        self.report["issues"] = sorted({(x["severity"], x["object_id"], x["code"]): x
                                         for x in issues}.values(),
                                        key=lambda x: (x["severity"], x["object_id"], x["code"]))
        self.report["records"].sort(key=lambda x: (x["binding_id"], x["record_id"]))
        severities = {x["severity"] for x in issues}
        if "invalid" in severities:
            state = "invalid"
        elif "incomplete" in severities:
            state = "incomplete"
        elif self.report["record_check"]["status"] != "completed":
            self.issue("record_check_not_completed", "records", "incomplete")
            state = "incomplete"
        else:
            state = "consistent"
        self.report["status"] = STATUSES[state]
        stage = self.report["record_check"]
        if state == "invalid" and stage["status"] == "completed":
            stage.update(result="mismatch", reason="invalid_record_bindings")
        elif state == "incomplete" and stage["status"] == "completed":
            stage.update(status="not_run", result=None, reason="record_set_incomplete")
        self.schemas.validate("report", self.report)
        return self.report


def verify_records(root: Path, input_path: str, expected_input_sha256: str,
                   carriers_path: str, expected_carriers_sha256: str,
                   record_set_path: str, expected_record_set_sha256: str, *,
                   binding_profile: str) -> dict[str, Any]:
    base = load_binding_checker()
    review = RecordReview(base, binding_profile)
    try:
        for key, value in (("input", expected_input_sha256), ("carriers", expected_carriers_sha256),
                           ("record_set", expected_record_set_sha256)):
            if not isinstance(value, str) or base.HASH_RE.fullmatch(value) is None:
                raise base.BindingError("invalid_expected_" + key + "_digest")
            review.report["expected_digests"][key] = value
        with base.BundleReader(root) as reader:
            record_set = review.bound_set(reader, record_set_path, expected_record_set_sha256)
            review.prepare(reader, record_set, input_path=input_path, input_digest=expected_input_sha256,
                           carriers_path=carriers_path, carriers_digest=expected_carriers_sha256)
            if review.run_base(reader, input_path, expected_input_sha256, carriers_path, expected_carriers_sha256):
                review.records(reader, record_set, input_path)
    except base.BindingError as exc:
        review.issue(exc.code, "bundle", exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--carriers", required=True)
    parser.add_argument("--expected-carriers-sha256", required=True)
    parser.add_argument("--record-set", required=True)
    parser.add_argument("--expected-record-set-sha256", required=True)
    parser.add_argument("--binding-profile", choices=BINDING_PROFILES, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_records(args.bundle_root, args.input, args.expected_input_sha256,
                                args.carriers, args.expected_carriers_sha256,
                                args.record_set, args.expected_record_set_sha256,
                                binding_profile=args.binding_profile)
    except Exception as exc:
        # An installation/programming failure must never emit a success report
        # or artifact-controlled error text. It is distinct from a bound verdict.
        print("Anchor record checker error: " + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report_bytes(report))
    return {STATUSES["consistent"]: 0, STATUSES["invalid"]: 1,
            STATUSES["incomplete"]: 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
