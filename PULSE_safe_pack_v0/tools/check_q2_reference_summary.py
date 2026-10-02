#!/usr/bin/env python3
"""Check a Q2 summary by separately recomputing the original bound records.

No import or invocation of build_q2_reference_summary.py is permitted here.
Exit 0 means the summary matches its inputs, including a correct FAIL summary.
It does not mean q2_consistency_ok passed or that a release is authorized.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIGEST = "bab4249805bf00099e95d5fc638d07a9537bd5b90195a54b3e4f88c192744ad4"
SOURCES = {
    "metric_spec": "metrics/specs/q2_consistency_v0.yml",
    "input_schema": "schemas/metrics/q2_consistency_input_v0.schema.json",
    "manifest_schema": "schemas/dataset_manifest.schema.json",
    "summary_schema": "schemas/metrics/q2_consistency_summary_v0.schema.json",
}

CONTRACT_DIGESTS = {
    "input_schema": "2c09f7c16bada21f48a13faf518f9b8e06a19fffe7fbd05ad40e01108138a969",
    "manifest_schema": "7bd729958c65dfde432925a4d3fccbd50c846cca19c891411ed085166ecdfead",
    "summary_schema": "3a6bb2b6bf4bdd29101899a92b9f7c7bd65c763af5263fbced211eb7db1f8eac",
}

def _read(path: Path, maximum: int, expected: str | None = None) -> bytes:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise ValueError("unsupported_file_boundary")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size < 1 or info.st_size > maximum:
            raise ValueError("invalid_input_file")
        pieces = []
        length = 0
        while length <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - length))
            if not part:
                break
            length += len(part)
            pieces.append(part)
        final = os.fstat(fd)
        if (length != info.st_size or length > maximum or
                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) !=
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns, final.st_ctime_ns)):
            raise ValueError("unstable_input")
    finally:
        os.close(fd)
    data = b"".join(pieces)
    if expected is not None:
        if re.fullmatch("[0-9a-f]{64}", expected) is None:
            raise ValueError("invalid_expectation")
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("input_binding_mismatch")
    return data


def _decode(data: bytes) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        if len({key for key, _ in values}) != len(values):
            raise ValueError("ambiguous_json")
        return dict(values)

    def nonfinite(_: str) -> None:
        raise ValueError("nonfinite_json")

    result = json.loads(data.decode("utf-8", errors="strict"),
                        object_pairs_hook=pairs, parse_constant=nonfinite)
    if type(result) is not dict:
        raise ValueError("expected_object")
    stack = [result]
    while stack:
        item = stack.pop()
        if type(item) is str:
            item.encode("utf-8", errors="strict")
        elif type(item) is dict:
            stack.extend(item)
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is float and not math.isfinite(item):
            raise ValueError("nonfinite_json_number")
    return result


def _checked_formats() -> FormatChecker:
    # Independent component/range checks; never import the producer's parser.
    # Instance-only registration also works without optional format packages.
    formats = FormatChecker()

    @formats.checks("date", raises=ValueError)
    def check_date(value: Any) -> bool:
        if not isinstance(value, str):
            return True
        parts = re.fullmatch(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", value)
        if parts is None:
            return False
        date(*(int(part) for part in parts.groups()))
        return True

    @formats.checks("date-time", raises=ValueError)
    def check_timestamp(value: Any) -> bool:
        if not isinstance(value, str):
            return True
        parts = re.fullmatch(
            r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
            r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.[0-9]+)?"
            r"(?:[Zz]|[+-]([0-9]{2}):([0-9]{2}))", value)
        if parts is None:
            return False
        fields = parts.groups()
        date(*(int(part) for part in fields[:3]))
        # Preserve the ordinary-second format profile; no ISO normalization
        # may turn an out-of-range time or zone offset into an accepted one.
        if any(int(part) >= limit for part, limit in zip(fields[3:6], (24, 60, 60))):
            return False
        return fields[6] is None or (int(fields[6]) < 24 and int(fields[7]) < 60)

    return formats


def _schema_check(value: dict[str, Any], raw_schema: bytes) -> None:
    schema = _decode(raw_schema)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=_checked_formats())
    if not validator.is_valid(value):
        raise ValueError("contract_mismatch")


def _lower_limit(successes: int, n: int) -> Decimal:
    if type(successes) is not int or type(n) is not int:
        raise ValueError("noninteger_binomial_counts")
    if n < 0 or successes < 0 or successes > n:
        raise ValueError("invalid_binomial_counts")
    if successes == 0:
        return Decimal(0)
    with localcontext() as ctx:
        ctx.prec = 60
        dn, ds = Decimal(n), Decimal(successes)
        z = Decimal("1.959963984540054")
        # Algebraically separate form; do not consume the producer's bound.
        bound = ((2 * ds + z*z - z*(z*z + 4*ds*(1-ds/dn)).sqrt()) /
                 (2 * (dn + z*z)))
        return max(Decimal(0), bound)


def verify(groups_path: Path, manifest_path: Path, summary_path: Path,
           groups_sha256: str, manifest_sha256: str, summary_sha256: str) -> bool:
    inputs = {"groups": _read(groups_path, 8 * 1024 * 1024, groups_sha256),
              "dataset_manifest": _read(manifest_path, 512 * 1024, manifest_sha256)}
    recorded = _read(summary_path, 16 * 1024 * 1024, summary_sha256)
    for role, path in SOURCES.items():
        inputs[role] = _read(ROOT / path, 512 * 1024,
                            SPEC_DIGEST if role == "metric_spec" else CONTRACT_DIGESTS[role])
    groups_doc = _decode(inputs["groups"])
    manifest = _decode(inputs["dataset_manifest"])
    summary = _decode(recorded)
    _schema_check(groups_doc, inputs["input_schema"])
    _schema_check(manifest, inputs["manifest_schema"])
    _schema_check(summary, inputs["summary_schema"])
    groups = groups_doc["groups"]
    if manifest["hashes"]["input_sha256"].lower() != groups_sha256:
        raise ValueError("manifest_hash_mismatch")
    sample = manifest["sampling"]
    if type(sample["n"]) is not int or sample["n"] != len(groups):
        raise ValueError("manifest_extent_mismatch")
    if (type(sample.get("seed")) is not int or
            type(groups_doc["grouping"]["seed"]) is not int or
            sample["seed"] != groups_doc["grouping"]["seed"]):
        raise ValueError("manifest_sampling_mismatch")
    identifiers = [group["group_id"] for group in groups]
    response_ids = [response["response_id"] for group in groups for response in group["responses"]]
    if len(set(identifiers)) != len(identifiers) or len(set(response_ids)) != len(response_ids):
        raise ValueError("duplicate_occurrence")

    # Recompute normalization, eligible response sets and labels from source records.
    rows = []
    for group in sorted(groups, key=lambda item: item["group_id"]):
        eligible = []
        for item in group["responses"]:
            kind = item["kind"]
            if kind == "unknown":
                continue
            if kind == "refusal":
                eligible.append((1, "__REFUSAL__"))
            else:
                text = item["answer"].strip()
                folded = text.casefold()
                normalized = unicodedata.normalize("NFKC", folded)
                if normalized.casefold() in ("__refusal__", "__unknown__"):
                    raise ValueError("reserved_signature_as_answer")
                if normalized:
                    eligible.append((0, normalized))
        count = len(eligible)
        label = "UNKNOWN"
        if count >= 2:
            label = "CONSISTENT" if all(x == eligible[0] for x in eligible[1:]) else "INCONSISTENT"
        rows.append({"group_id": group["group_id"], "label": label,
                     "responses_total": len(group["responses"]), "responses_eligible": count})
    labels = Counter(row["label"] for row in rows)
    n = labels["CONSISTENT"] + labels["INCONSISTENT"]
    successes = labels["CONSISTENT"]
    bound = _lower_limit(successes, n)
    rate = successes / n if n else 0.0
    decision = n >= 50 and bound >= Decimal("0.90")
    recomputed = {
        "schema_version": "q2_consistency_summary_v0", "spec_id": "q2_consistency_v0",
        "spec_version": "0.1.0", "record_status": groups_doc["record_status"],
        "method": {"kind": "deterministic_reference_reduction",
                   "extraction_profile": "typed_final_answer_or_refusal_v0",
                   "normalization_order": ["trim_whitespace", "casefold", "normalize_unicode_nfkc"],
                   "comparator": "exact_match", "unicode_version": unicodedata.unidata_version,
                   "grouping_authentication": "not_established", "inference_executed": False},
        "bindings": {key: {"sha256": hashlib.sha256(value).hexdigest(), "size_bytes": len(value)}
                     for key, value in inputs.items()},
        "counts": {"groups_total": len(rows), "groups_eligible": n,
                   "consistent": successes, "inconsistent": labels["INCONSISTENT"],
                   "unknown": labels["UNKNOWN"], "responses_total": len(response_ids),
                   "responses_eligible": sum(row["responses_eligible"] for row in rows)},
        "groups": rows, "consistency_rate": float(rate), "wilson_lower_bound": float(bound),
        "alpha": 0.05, "threshold": 0.90, "min_n_eligible_groups": 50,
        "insufficient_evidence": n < 50, "pass": decision,
        "authority_effect": "none", "production_gate_eligible": False,
    }
    expected_bytes = (json.dumps(recomputed, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    if recorded != expected_bytes:
        raise ValueError("summary_recomputation_mismatch")
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", required=True, type=Path)
    parser.add_argument("--dataset-manifest", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--expected-groups-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-summary-sha256", required=True)
    args = parser.parse_args()
    try:
        decision = verify(args.groups, args.dataset_manifest, args.summary,
                          args.expected_groups_sha256, args.expected_manifest_sha256,
                          args.expected_summary_sha256)
    except (OSError, ValueError, RecursionError, ArithmeticError, SchemaError):
        print("q2_reference_check_rejected", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "recomputed_pass": decision,
                      "authority_effect": "none", "production_gate_eligible": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
