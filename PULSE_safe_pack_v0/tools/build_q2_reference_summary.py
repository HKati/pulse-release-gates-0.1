#!/usr/bin/env python3
"""Reduce declared Q2 response groups; never produce production gate authority.

Exit 0: a valid, passing reference summary was published.
Exit 1: a valid, non-passing reference summary was published.
Exit 2: malformed/mismatched input or publication failure; no PASS claim.
The original response records, not a precomputed result flag, are the input.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import unicodedata
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[2]
SPEC = "metrics/specs/q2_consistency_v0.yml"
SPEC_SHA256 = "bab4249805bf00099e95d5fc638d07a9537bd5b90195a54b3e4f88c192744ad4"
INPUT_SCHEMA = "schemas/metrics/q2_consistency_input_v0.schema.json"
SUMMARY_SCHEMA = "schemas/metrics/q2_consistency_summary_v0.schema.json"
MANIFEST_SCHEMA = "schemas/dataset_manifest.schema.json"
SCHEMA_DIGESTS = {
    "schemas/metrics/q2_consistency_input_v0.schema.json": "2c09f7c16bada21f48a13faf518f9b8e06a19fffe7fbd05ad40e01108138a969",
    "schemas/dataset_manifest.schema.json": "7bd729958c65dfde432925a4d3fccbd50c846cca19c891411ed085166ecdfead",
    "schemas/metrics/q2_consistency_summary_v0.schema.json": "3a6bb2b6bf4bdd29101899a92b9f7c7bd65c763af5263fbced211eb7db1f8eac",
}
INPUT_LIMIT = 8 * 1024 * 1024
MANIFEST_LIMIT = 512 * 1024


def _snapshot(path: Path, limit: int) -> bytes:
    # One bounded descriptor read: a supplied hash binds these actual bytes.
    required = ("O_NOFOLLOW", "O_NONBLOCK")
    if not all(hasattr(os, flag) for flag in required):
        raise ValueError("unsupported_file_boundary")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
            raise ValueError("invalid_file_shape")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(data) != before.st_size or len(data) > limit or stamp(before) != stamp(after):
        raise ValueError("input_changed_during_read")
    return data


def _json(data: bytes) -> dict[str, Any]:
    def object_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in items:
            if key in obj:
                raise ValueError("duplicate_json_key")
            obj[key] = value
        return obj

    def invalid_constant(_: str) -> None:
        raise ValueError("nonfinite_json")

    obj = json.loads(data.decode("utf-8", "strict"),
                     object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    if not isinstance(obj, dict):
        raise ValueError("expected_json_object")
    pending = [obj]
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            value.encode("utf-8", "strict")
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("nonfinite_json_number")
    return obj


def _descriptor(data: bytes) -> dict[str, Any]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _expected(data: bytes, digest: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("invalid_expected_digest")
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("expected_digest_mismatch")


def _validate(payload: dict[str, Any], schema: bytes) -> None:
    contract = _json(schema)
    Draft202012Validator.check_schema(contract)
    errors = Draft202012Validator(contract, format_checker=FormatChecker()).iter_errors(payload)
    if next(errors, None) is not None:
        raise ValueError("schema_rejected")


def _signature(response: dict[str, Any]) -> tuple[str, str] | None:
    if response["kind"] == "unknown":
        return None
    if response["kind"] == "refusal":
        return ("refusal", "__REFUSAL__")
    # Order is normative. Do not NFKC first or strip a second time.
    answer = unicodedata.normalize("NFKC", response["answer"].strip().casefold())
    if answer.casefold() in {"__unknown__", "__refusal__"}:
        raise ValueError("reserved_signature_requires_typed_tag")
    return ("answer", answer) if answer else None


def _wilson_lower(successes: int, n: int) -> Decimal:
    if type(n) is not int or type(successes) is not int or not 0 <= successes <= n:
        raise ValueError("invalid_binomial_counts")
    # The exact zero-success limit is zero; avoid cancellation residuals.
    if successes == 0:
        return Decimal(0)
    with localcontext() as context:
        context.prec = 60
        d_n = Decimal(n)
        rate = Decimal(successes) / d_n
        z = Decimal("1.959963984540054")
        lower = ((rate + z*z/(2*d_n) - z*(rate*(1-rate)/d_n +
                  z*z/(4*d_n*d_n)).sqrt()) / (1 + z*z/d_n))
        return max(Decimal(0), lower)


def build(groups_path: Path, manifest_path: Path,
          expected_groups: str, expected_manifest: str) -> dict[str, Any]:
    raw = _snapshot(groups_path, INPUT_LIMIT)
    manifest_raw = _snapshot(manifest_path, MANIFEST_LIMIT)
    _expected(raw, expected_groups)
    _expected(manifest_raw, expected_manifest)
    spec_raw = _snapshot(ROOT / SPEC, MANIFEST_LIMIT)
    _expected(spec_raw, SPEC_SHA256)
    input_schema = _snapshot(ROOT / INPUT_SCHEMA, MANIFEST_LIMIT)
    manifest_schema = _snapshot(ROOT / MANIFEST_SCHEMA, MANIFEST_LIMIT)
    summary_schema = _snapshot(ROOT / SUMMARY_SCHEMA, MANIFEST_LIMIT)
    for schema_path, schema_raw in ((INPUT_SCHEMA, input_schema),
                                    (MANIFEST_SCHEMA, manifest_schema),
                                    (SUMMARY_SCHEMA, summary_schema)):
        _expected(schema_raw, SCHEMA_DIGESTS[schema_path])
    document, manifest = _json(raw), _json(manifest_raw)
    _validate(document, input_schema)
    _validate(manifest, manifest_schema)
    groups = document["groups"]
    if manifest["hashes"]["input_sha256"].lower() != expected_groups:
        raise ValueError("manifest_input_digest_mismatch")
    # This profile's sampling unit is an agreement group, not a response.
    sampling = manifest["sampling"]
    if type(sampling["n"]) is not int or sampling["n"] != len(groups):
        raise ValueError("manifest_group_count_mismatch")
    if type(sampling.get("seed")) is not int or sampling["seed"] != document["grouping"]["seed"]:
        raise ValueError("manifest_seed_mismatch")
    if type(document["grouping"]["seed"]) is not int:
        raise ValueError("invalid_seed_type")
    group_ids: set[str] = set()
    response_ids: set[str] = set()
    rows = []
    counts = {key: 0 for key in ("groups_total", "groups_eligible", "consistent",
                                "inconsistent", "unknown", "responses_total",
                                "responses_eligible")}
    for group in groups:
        if group["group_id"] in group_ids:
            raise ValueError("duplicate_group_id")
        group_ids.add(group["group_id"])
        signatures = []
        for response in group["responses"]:
            if response["response_id"] in response_ids:
                raise ValueError("duplicate_response_id")
            response_ids.add(response["response_id"])
            signature = _signature(response)
            if signature is not None:
                signatures.append(signature)
        eligible = len(signatures)
        label = ("UNKNOWN" if eligible < 2 else
                 "CONSISTENT" if len(set(signatures)) == 1 else "INCONSISTENT")
        total = len(group["responses"])
        rows.append({"group_id": group["group_id"], "label": label,
                     "responses_total": total, "responses_eligible": eligible})
        counts["groups_total"] += 1
        counts[label.lower()] += 1
        counts["groups_eligible"] += int(label != "UNKNOWN")
        counts["responses_total"] += total
        counts["responses_eligible"] += eligible
    n, successes = counts["groups_eligible"], counts["consistent"]
    lower = _wilson_lower(successes, n)
    rate = successes / n if n else 0.0
    passed = n >= 50 and lower >= Decimal("0.90")
    result = {
        "schema_version": "q2_consistency_summary_v0", "spec_id": "q2_consistency_v0",
        "spec_version": "0.1.0", "record_status": document["record_status"],
        "method": {"kind": "deterministic_reference_reduction",
                   "extraction_profile": "typed_final_answer_or_refusal_v0",
                   "normalization_order": ["trim_whitespace", "casefold", "normalize_unicode_nfkc"],
                   "comparator": "exact_match", "unicode_version": unicodedata.unidata_version,
                   "grouping_authentication": "not_established", "inference_executed": False},
        "bindings": {name: _descriptor(data) for name, data in (
            ("groups", raw), ("dataset_manifest", manifest_raw), ("metric_spec", spec_raw),
            ("input_schema", input_schema), ("manifest_schema", manifest_schema),
            ("summary_schema", summary_schema))},
        "counts": counts, "groups": sorted(rows, key=lambda row: row["group_id"]),
        "consistency_rate": float(rate), "wilson_lower_bound": float(lower),
        "alpha": 0.05, "threshold": 0.90, "min_n_eligible_groups": 50,
        "insufficient_evidence": n < 50, "pass": passed,
        "authority_effect": "none", "production_gate_eligible": False,
    }
    _validate(result, summary_schema)
    return result


def _publish(output: Path, value: dict[str, Any]) -> None:
    data = (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=".q2-", dir=output.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Publish a complete file, without replacing any existing destination.
        os.link(temporary, output)
    finally:
        temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--expected-groups-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.groups, args.dataset_manifest,
                       args.expected_groups_sha256, args.expected_manifest_sha256)
        _publish(args.out, result)
    except (OSError, ValueError, RecursionError, ArithmeticError, SchemaError):
        # Never echo supplied answer text, manifest contents or secret-bearing paths.
        print("q2_reference_rejected", file=sys.stderr)
        return 2
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
