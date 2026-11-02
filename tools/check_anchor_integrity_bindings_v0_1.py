#!/usr/bin/env python3
"""WP2A: offline byte/reference checks, never semantic or release authority.

The caller supplies two independently retained SHA-256 expectations. Those
expectations bind this invocation; they do not authenticate who supplied them.
All artifact content is data. No network, Git command, plugin or artifact code
is executed. stdout is the only output. See the WP2A document for the profile.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 4096
MAX_DEPTH = 64
MAX_NODES = 100000
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
PATH_RE = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")
SCHEMAS = {
    "input": "anchor_integrity_input_v0_1.schema.json",
    "claims": "anchor_integrity_claim_packet_v0_1.schema.json",
    "evidence": "anchor_integrity_evidence_packet_v0_1.schema.json",
    "relations": "anchor_integrity_relation_verification_packet_v0_1.schema.json",
    "carriers": "anchor_integrity_local_carriers_v0_1.schema.json",
    "report": "anchor_integrity_binding_report_v0_1.schema.json",
}
UNPERFORMED = (
    "source_identity_authentication", "acquisition_authentication",
    "subject_observation_authentication", "semantic_support_verification",
    "typed_evidence_cycle_check", "response_mode_recommendation",
    "claim_set_completeness", "verified_binding_coverage",
    "verified_support_coverage",
)


class BindingError(Exception):
    """A stable failure code, without artifact-controlled exception text."""
    def __init__(self, code: str, severity: str = "invalid") -> None:
        super().__init__(code)
        self.code = code
        self.severity = severity


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_constant(_value: str) -> Any:
    raise BindingError("non_finite_json")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BindingError("duplicate_json_key")
        result[key] = value
    return result


def strict_json(data: bytes) -> Any:
    """Bounded JSON with no duplicate keys, non-finite numbers or surrogates."""
    if len(data) > MAX_FILE_BYTES:
        raise BindingError("file_limit_exceeded")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_object_pairs,
                           parse_constant=_reject_constant)
        stack = [(value, 0)]
        nodes = 0
        while stack:
            item, depth = stack.pop()
            nodes += 1
            if depth > MAX_DEPTH or nodes > MAX_NODES:
                raise BindingError("json_complexity_limit")
            if isinstance(item, dict):
                stack.extend((key, depth + 1) for key in item)
                stack.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list):
                if len(item) > MAX_ITEMS:
                    raise BindingError("item_limit_exceeded")
                stack.extend((v, depth + 1) for v in item)
            elif isinstance(item, str):
                item.encode("utf-8", errors="strict")
            elif isinstance(item, float) and not math.isfinite(item):
                raise BindingError("non_finite_json")
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BindingError("invalid_json_encoding_or_syntax") from exc


def _assert_self_contained(schema: Any) -> None:
    """This profile uses no reference resolver, including for local refs."""
    stack = [schema]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if any(k in item for k in ("$ref", "$dynamicRef", "$recursiveRef")):
                raise BindingError("schema_reference_not_allowed")
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


class SchemaSet:
    """Only reviewed repository schemas, never a bundle-selected schema."""
    def __init__(self) -> None:
        self.validators: dict[str, Any] = {}
        self.hashes: dict[str, str] = {}
        for role, name in SCHEMAS.items():
            raw = (ROOT / "schemas" / name).read_bytes()
            schema = strict_json(raw)
            _assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.validators[role] = jsonschema.Draft202012Validator(schema)
            self.hashes[name] = sha256(raw)

    def validate(self, role: str, value: Any) -> None:
        # Consume just the first error: never produce unbounded error listings.
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise BindingError("schema_invalid_" + role)


def safe_relative(path: Any) -> str:
    if (not isinstance(path, str) or len(path) > 512 or
            PATH_RE.fullmatch(path) is None or
            any(p in (".", "..") or p.endswith(".") for p in path.split("/"))):
        raise BindingError("unsafe_relative_path")
    return path


class BundleReader:
    """Read one immutable per-invocation snapshot from regular local files.

    Linux/POSIX dir-fd + O_NOFOLLOW checks cover every component. Hard links,
    FIFOs, devices and symlinks are not carriers in this profile. The host and
    selected root are trusted; this is not a hostile-root containment boundary.
    """
    def __init__(self, root: Path) -> None:
        if (os.name != "posix" or
                not all(hasattr(os, key) for key in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")) or
                os.open not in os.supports_dir_fd):
            raise BindingError("unsupported_safe_file_platform")
        try:
            self.fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as exc:
            raise BindingError("bundle_root_unavailable") from exc
        self.total = 0
        self.cache: dict[str, bytes] = {}
        self.owners: dict[str, str] = {}
        self.folded: dict[str, str] = {}

    def __enter__(self) -> "BundleReader":
        return self

    def __exit__(self, *_args: Any) -> None:
        os.close(self.fd)

    def reserve(self, path: str, role: str) -> None:
        path = safe_relative(path)
        old = self.owners.get(path)
        if old is not None and old != role:
            raise BindingError("carrier_path_reused")
        folded = path.casefold()
        if folded in self.folded and self.folded[folded] != path:
            raise BindingError("case_colliding_paths")
        self.owners[path] = role
        self.folded[folded] = path

    def read(self, path: str, role: str) -> bytes:
        self.reserve(path, role)
        if path in self.cache:
            return self.cache[path]
        parent = os.dup(self.fd)
        leaf = None
        try:
            parts = path.split("/")
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=parent)
                os.close(parent)
                parent = child
            leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                           dir_fd=parent)
            before = os.fstat(leaf)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise BindingError("non_regular_or_linked_carrier")
            if before.st_size > MAX_FILE_BYTES:
                raise BindingError("file_limit_exceeded")
            chunks = []
            size = 0
            while True:
                block = os.read(leaf, min(65536, MAX_FILE_BYTES + 1 - size))
                if not block:
                    break
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise BindingError("file_limit_exceeded")
                chunks.append(block)
            after = os.fstat(leaf)
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
            if any(getattr(before, x) != getattr(after, x) for x in fields) or size != before.st_size:
                raise BindingError("carrier_changed_during_read")
            self.total += size
            if self.total > MAX_TOTAL_BYTES:
                raise BindingError("bundle_limit_exceeded")
            data = b"".join(chunks)
            self.cache[path] = data
            return data
        except FileNotFoundError as exc:
            raise BindingError("missing_carrier", "incomplete") from exc
        except OSError as exc:
            raise BindingError("unsafe_or_unreadable_carrier") from exc
        finally:
            if leaf is not None:
                os.close(leaf)
            os.close(parent)


def select_content(data: bytes, locator: dict[str, Any]) -> bytes:
    kind = locator.get("type")
    if kind == "json_pointer":
        # WP1 defines the pointer, not a selected-value byte representation.
        # Do not silently invent canonicalization or serialize a parsed value.
        raise BindingError("json_pointer_projection_not_implemented", "incomplete")
    if kind == "line_range":
        start, end = locator.get("start_line"), locator.get("end_line")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise BindingError("invalid_line_range")
        # Locate LF boundaries without expanding a large file into a line list.
        # Preserve CR/LF bytes and do not invent a final empty line.
        position = 0
        selected_start = None
        for number in range(1, end + 1):
            if position >= len(data):
                raise BindingError("line_range_out_of_bounds")
            if number == start:
                selected_start = position
            lf = data.find(b"\n", position)
            position = len(data) if lf == -1 else lf + 1
        return data[selected_start:position]
    if kind == "character_span":
        start, end = locator.get("start"), locator.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise BindingError("invalid_character_span")
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise BindingError("character_source_not_utf8") from exc
        if end > len(text):
            raise BindingError("character_span_out_of_bounds")
        # Unicode scalar/code-point offsets, zero-based [start,end), no NFC/NFD.
        return text[start:end].encode("utf-8")
    raise BindingError("unknown_locator_type")


def _index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    if len(items) > MAX_ITEMS:
        raise BindingError("item_limit_exceeded")
    result = {}
    for item in items:
        ident = item[key]
        if ident in result:
            raise BindingError("duplicate_" + key)
        result[ident] = item
    return result


class Review:
    def __init__(self, schemas: SchemaSet) -> None:
        self.schemas = schemas
        self.report: dict[str, Any] = {
            "schema_version": "anchor_integrity_binding_report_v0_1",
            "candidate_status": "diagnostic_only", "authority_effect": "none",
            "release_authority_activation": False, "work_package": "WP2A",
            "verification_scope": "offline_bytes_and_recorded_links",
            "status": "LOCAL_BINDINGS_INCOMPLETE", "input_sha256": None,
            "carriers_sha256": None, "expected_input_sha256": None,
            "expected_carriers_sha256": None, "baseline_commit": None, "subject": None,
            "claim_set_materialization_status": None,
            "counts": {k: None for k in ("claims", "sources", "evidence_items", "relations",
                       "claims_with_recorded_anchors", "claims_without_recorded_anchors")},
            "checks": [], "issues": [], "recorded_relation_results": [],
            "unperformed_checks": {k: {"status": "not_run", "result": None,
                "reason": "outside_wp2a_local_binding_scope"} for k in UNPERFORMED},
            "requested_checks_complete": False,
            "implementation": {"checker_sha256": sha256(Path(__file__).read_bytes()),
                               "schema_sha256": dict(schemas.hashes)},
        }

    def issue(self, code: str, ident: str, severity: str = "invalid") -> None:
        self.report["issues"].append({"severity": severity, "code": code, "object_id": ident})

    def check(self, ident: str, matches: bool) -> None:
        self.report["checks"].append({"id": ident, "status": "completed",
              "result": "match" if matches else "mismatch",
              "reason": None if matches else "comparison_failed"})
        if not matches:
            self.issue("comparison_failed", ident)

    def attempt(self, ident: str, call: Any) -> Any:
        try:
            return call()
        except BindingError as exc:
            self.issue(exc.code, ident, exc.severity)
            self.report["checks"].append({"id": ident, "status": "not_run",
                                          "result": None, "reason": exc.code})
            return None

    def bound_json(self, reader: BundleReader, path: str, digest: str,
                   ident: str, schema_role: str | None = None) -> Any:
        raw = reader.read(path, ident)
        if ident in ("input", "carriers"):
            self.report[ident + "_sha256"] = sha256(raw)
        if not isinstance(digest, str) or HASH_RE.fullmatch(digest) is None:
            raise BindingError("invalid_expected_digest")
        if sha256(raw) != digest:
            self.check(ident + ".sha256", False)
            raise BindingError("digest_mismatch")
        self.check(ident + ".sha256", True)
        value = strict_json(raw)
        if not isinstance(value, dict):
            raise BindingError("json_object_required")
        if schema_role:
            self.schemas.validate(schema_role, value)
        return value

    def finish(self) -> dict[str, Any]:
        self.report["issues"] = sorted(
            { (x["severity"], x["code"], x["object_id"]): x
              for x in self.report["issues"] }.values(),
            key=lambda x: (x["severity"], x["object_id"], x["code"]))
        self.report["checks"].sort(key=lambda x: (x["id"], x["status"], str(x["result"])))
        self.report["recorded_relation_results"].sort(key=lambda x: x["binding_id"])
        severity = {x["severity"] for x in self.report["issues"]}
        self.report["status"] = ("LOCAL_BINDINGS_INVALID" if "invalid" in severity else
            "LOCAL_BINDINGS_INCOMPLETE" if "incomplete" in severity else "LOCAL_BINDINGS_CONSISTENT")
        self.schemas.validate("report", self.report)
        return self.report

    def review(self, reader: BundleReader, input_path: str, expected_input: str,
               carriers_path: str, expected_carriers: str) -> None:
        for name, digest in (("input", expected_input), ("carriers", expected_carriers)):
            if not isinstance(digest, str) or HASH_RE.fullmatch(digest) is None:
                raise BindingError("invalid_expected_" + name + "_digest")
            self.report["expected_" + name + "_sha256"] = digest
        inp = self.attempt("input", lambda: self.bound_json(reader, input_path, expected_input, "input", "input"))
        carriers = self.attempt("carriers", lambda: self.bound_json(reader, carriers_path, expected_carriers, "carriers", "carriers"))
        if inp is None or carriers is None:
            return
        self.report.update(input_sha256=expected_input, carriers_sha256=expected_carriers,
                           baseline_commit=inp["baseline_commit"], subject=inp["subject"])
        self.check("carriers.input_sha256", carriers["input_sha256"] == expected_input)
        bindings = inp["packet_bindings"]
        packets = {}
        for key, role in (("claim_packet", "claims"), ("evidence_packet", "evidence"),
                          ("relation_verification_packet", "relations")):
            binding = bindings[key]
            packets[role] = self.attempt(role, lambda b=binding, r=role: self.bound_json(
                reader, b["path"], b["sha256"], r, r))
        # These remain opaque JSON data; byte/tag checks do not validate their meaning.
        for key in ("legacy_overlay", "paradox_graph_binding"):
            binding = inp[key]
            if binding is None:
                continue
            def opaque(b: dict[str, Any] = binding, k: str = key) -> None:
                value = self.bound_json(reader, b["path"], b["sha256"], k)
                tags = [value[x] for x in ("schema", "schema_version") if x in value]
                self.check(k + ".schema_tag", bool(tags) and all(t == b["schema_version"] for t in tags))
            self.attempt(key, opaque)
        if any(v is None for v in packets.values()):
            return
        cp, ep, rp = packets["claims"], packets["evidence"], packets["relations"]
        for role, packet in packets.items():
            self.check(role + ".subject", {k: packet["subject"][k] for k in ("subject_id", "run_id")} == inp["subject"])
        self.check("relations.claim_packet_binding", rp["claim_packet_binding"] == bindings["claim_packet"])
        self.check("relations.evidence_packet_binding", rp["evidence_packet_binding"] == bindings["evidence_packet"])
        ids = [cp["packet_id"], ep["packet_id"], rp["packet_id"]]
        self.check("packet_id_uniqueness", len(set(ids)) == 3)
        claims = _index(cp["claim_set"]["claims"], "claim_id")
        sources = _index(ep["sources"], "source_id")
        items = _index(ep["evidence_items"], "evidence_id")
        relations = _index(rp["relations"], "binding_id")
        source_map = _index(carriers["sources"], "source_id")
        self.check("carriers.no_unknown_sources", set(source_map) <= set(sources))
        for source_id, carrier in source_map.items():
            reader.reserve(carrier["path"], "source:" + source_id)
        if carriers["source_response"]:
            reader.reserve(carriers["source_response"]["path"], "source_response")
        cs = cp["claim_set"]
        self.report["claim_set_materialization_status"] = cs["materialization_status"]
        if cs["materialization_status"] != "complete":
            self.issue("claim_set_not_declared_complete", "claim_set", "incomplete")
        self.report["counts"].update(claims=len(claims), sources=len(sources), evidence_items=len(items), relations=len(relations))
        response = None
        if carriers["source_response"] is None:
            self.issue("source_response_not_supplied", "source_response", "incomplete")
        else:
            response_ref = carriers["source_response"]
            self.check("source_response.id", response_ref["source_response_id"] == cp["subject"]["source_response_id"])
            response = self.attempt("source_response", lambda: reader.read(response_ref["path"], "source_response"))
            if response is not None:
                self.check("source_response.sha256", sha256(response) == cp["subject"]["source_response_sha256"])
        for claim_id, claim in sorted(claims.items()):
            self.check("claim:" + claim_id + ".text_digest", sha256(claim["claim_text"].encode("utf-8")) == claim["claim_digest"])
            if response is not None:
                selection = self.attempt("claim:" + claim_id + ".locator", lambda c=claim: select_content(response, c["locator"]))
                if selection is not None:
                    self.check("claim:" + claim_id + ".selected_text", selection == claim["claim_text"].encode("utf-8"))
        source_bytes: dict[str, bytes] = {}
        for source_id, source in sorted(sources.items()):
            carrier = source_map.get(source_id)
            if carrier is None:
                self.issue("source_carrier_not_supplied", source_id, "incomplete")
                continue
            self.check("source:" + source_id + ".declared_identity", all(
                carrier[k] == source[k] for k in ("canonical_identifier", "revision")))
            data = self.attempt("source:" + source_id, lambda c=carrier, s=source_id: reader.read(c["path"], "source:" + s))
            if data is not None:
                source_bytes[source_id] = data
                self.check("source:" + source_id + ".sha256", sha256(data) == source["content_sha256"])
        for evidence_id, item in sorted(items.items()):
            source_id = item["source_id"]
            self.check("evidence:" + evidence_id + ".source_reference", source_id in sources)
            binding = item["subject_binding"]
            expected = {"subject_id": binding["expected_subject_id"], "run_id": binding["expected_run_id"]}
            self.check("evidence:" + evidence_id + ".expected_subject", expected == inp["subject"])
            # Null means no recorded run identity; null==null is not a run proof.
            observed = {"subject_id": binding["observed_subject_id"], "run_id": binding["observed_run_id"]}
            if observed["subject_id"] is None:
                self.issue("observed_subject_missing", evidence_id, "incomplete")
            else:
                self.check("evidence:" + evidence_id + ".recorded_subject_id", observed["subject_id"] == expected["subject_id"])
            if expected["run_id"] is not None:
                if observed["run_id"] is None:
                    self.issue("observed_run_missing", evidence_id, "incomplete")
                else:
                    self.check("evidence:" + evidence_id + ".recorded_run_id", observed["run_id"] == expected["run_id"])
            elif observed["run_id"] is not None:
                self.check("evidence:" + evidence_id + ".recorded_run_id", False)
            else:
                self.report["checks"].append({"id": "evidence:" + evidence_id + ".recorded_run_id",
                    "status": "not_run", "result": None, "reason": "no_run_identity_declared"})
            data = source_bytes.get(source_id)
            if data is not None:
                selected = self.attempt("evidence:" + evidence_id + ".locator", lambda d=data, i=item: select_content(d, i["locator"]))
                if selected is not None:
                    self.check("evidence:" + evidence_id + ".sha256", sha256(selected) == item["content_sha256"])
        anchored = set()
        for binding_id, relation in sorted(relations.items()):
            valid_ref = relation["claim_id"] in claims and relation["evidence_id"] in items
            self.check("relation:" + binding_id + ".references", valid_ref)
            if valid_ref:
                anchored.add(relation["claim_id"])
            verification = relation["relation_verification"]
            self.report["recorded_relation_results"].append({
                "binding_id": binding_id, "claim_id": relation["claim_id"],
                "evidence_id": relation["evidence_id"], "relation_type": relation["relation_type"],
                "declared_status": verification["status"], "declared_result": verification["result"],
                "verifier_record_id": relation["verifier_record_id"], "accepted_as_semantic_support": False})
        self.report["counts"].update(claims_with_recorded_anchors=len(anchored),
                                     claims_without_recorded_anchors=len(claims) - len(anchored))


def verify_bundle(root: Path, input_path: str, expected_input_sha256: str,
                  carriers_path: str, expected_carriers_sha256: str) -> dict[str, Any]:
    review = Review(SchemaSet())
    try:
        with BundleReader(root) as reader:
            review.review(reader, input_path, expected_input_sha256,
                          carriers_path, expected_carriers_sha256)
    except BindingError as exc:
        review.issue(exc.code, "bundle", exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--input", required=True, help="Relative to the explicit bundle root")
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--carriers", required=True, help="Local-carrier manifest path")
    parser.add_argument("--expected-carriers-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_bundle(args.bundle_root, args.input, args.expected_input_sha256,
                               args.carriers, args.expected_carriers_sha256)
    except (OSError, jsonschema.exceptions.SchemaError, BindingError) as exc:
        # Local implementation/schema installation failure: no success-shaped report.
        print("Anchor binding checker installation error: " + type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False))
    return {"LOCAL_BINDINGS_CONSISTENT": 0, "LOCAL_BINDINGS_INCOMPLETE": 2,
            "LOCAL_BINDINGS_INVALID": 1}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
