#!/usr/bin/env python3
"""Independently verify a standalone Q3 report under the accepted v0.1 profile.

The producer is never imported or executed. Its sole source file is read only
to check the digest selected by the caller. Semantic results below are derived
from the original example/label inputs and the fixed profile, not from a report.

Exit 0: valid inputs and an exact report match, including metric FAIL.
Exit 1: valid inputs but an unreadable, malformed or nonmatching report.
Exit 2: invalid input/expected context, or an operational failure.
No outcome is release authority or proof that a producer runtime executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import sys
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError


PROFILE = "q3_input_recomputation_v0.1"
CHECKER_ID = "PULSE_q3_reference_checker"
CHECKER_VERSION = "0.1.0"
CHECKER_PATH = "PULSE_safe_pack_v0/tools/check_q3_reference_summary.py"
PRODUCER_ID = "PULSE_q3_reference"
PRODUCER_VERSION = "0.1.0"
PRODUCER_PATH = "PULSE_safe_pack_v0/tools/build_q3_reference_summary.py"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_EXAMPLES = 100000
MAX_DIMENSIONS = 64
Z_95 = 1.959963984540054
PERMANENT_BOUNDARIES = {
    "authority_effect": "none",
    "production_gate_eligible": False,
    "current_run_evidence": False,
    "source_authentication": "not_established",
    "label_correctness": "not_verified",
    "slice_metadata_correctness": "not_verified",
    "policy_activation": False,
}
MANIFEST_SCHEMA_SHA256 = (
    "7bd729958c65dfde432925a4d3fccbd50c846cca19c891411ed085166ecdfead"
)
RESOURCE_PATHS = {
    "contract_sha256": "PULSE_safe_pack_v0/profiles/q3_reference_recomputation_v0.json",
    "input_schema_sha256": "schemas/metrics/q3_input_bundle_v0.schema.json",
    "result_schema_sha256": "schemas/metrics/q3_reference_summary_v0.schema.json",
    "dataset_manifest_schema_sha256": "schemas/dataset_manifest.schema.json",
}
BASELINE_SPECS = {
    "q1": {
        "path": "metrics/specs/q1_groundedness_v0.yml",
        "sha256": "a63625ca894294e0fbe4febffdd143d22929dcaa44ea52a6aaa02453f0aac65f",
        "git_blob_sha1": "16fe7da3cb8fa304a3186955f76cea6c02cf09d3",
    },
    "q3_baseline": {
        "path": "metrics/specs/q3_fairness_v0.yml",
        "sha256": "58fc3ddbf636ffdcadc9ca3ce07e6051ff9801d49e9593b7c8e79970a08e782e",
        "git_blob_sha1": "4d1f6e1c4197e2465369585c78de4fd538957275",
    },
}
RELATIVE_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
SHA256 = re.compile(r"[0-9a-f]{64}")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?"
    r"(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


class InputProblem(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class ReportProblem(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        ) + "\n"
    ).encode("utf-8")


class ReportSizeBudget:
    """Stop report construction once disjoint components already exceed its file cap.

    A group's or excluded record's standalone canonical object, excluding its
    final LF, is no longer than that same object embedded in the indented final
    report. Each accounted object is disjoint; parent containers are not added
    again. Their sum is therefore a conservative lower bound, not a new group
    count limit. The final complete canonical-byte check remains necessary.
    """

    def __init__(self) -> None:
        self.minimum_bytes = 0

    def account(self, component: dict[str, Any]) -> None:
        self.minimum_bytes += len(canonical_bytes(component)) - 1
        if self.minimum_bytes > MAX_FILE_BYTES:
            raise InputProblem(
                "INPUT_LIMIT", "Report components already exceed the 64 MiB file limit."
            )


def safe_relative(value: str) -> str:
    if (
        not isinstance(value, str)
        or RELATIVE_PATH.fullmatch(value) is None
        or any(part in (".", "..") for part in value.split("/"))
    ):
        raise InputProblem("INPUT_PATH_INVALID", "A relative resource path is unsafe.")
    return value


def absolute_path(value: str | Path) -> str:
    path = os.fspath(value)
    if not path or "\x00" in path:
        raise InputProblem("INPUT_PATH_INVALID", "A filesystem path is invalid.")
    return os.path.abspath(path)


def parent_descriptor(path: str) -> tuple[int, str]:
    """Open every ancestor using directory FDs, never following a symlink."""
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or os.open not in os.supports_dir_fd
    ):
        raise InputProblem(
            "UNSUPPORTED_PLATFORM", "No safe no-symlink file traversal is available."
        )
    parts = Path(path).parts
    if not parts or parts[0] != "/" or len(parts) < 2:
        raise InputProblem("INPUT_PATH_INVALID", "A regular-file path is required.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    current = os.open("/", flags)
    try:
        for component in parts[1:-1]:
            following = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = following
        return current, parts[-1]
    except BaseException:
        os.close(current)
        raise


def stable_stat(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    sha256: str
    identity: tuple[int, int, int, int, int]


class Snapshots:
    """Read each file once into bounded immutable bytes, including hardlink aliases."""

    def __init__(self) -> None:
        self.paths: dict[str, Snapshot] = {}
        self.inodes: dict[tuple[int, int], Snapshot] = {}

    def read(self, path: str | Path) -> Snapshot:
        name = absolute_path(path)
        if name in self.paths:
            return self.paths[name]
        parent = None
        descriptor = None
        try:
            parent, leaf = parent_descriptor(name)
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NONBLOCK", 0)
            descriptor = os.open(leaf, flags, dir_fd=parent)
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise InputProblem("INPUT_PATH_INVALID", "An input is not a regular file.")
            if before.st_size > MAX_FILE_BYTES:
                raise InputProblem("INPUT_LIMIT", "An input exceeds the 64 MiB file limit.")
            key = (before.st_dev, before.st_ino)
            if key in self.inodes:
                existing = self.inodes[key]
                if stable_stat(before) != existing.identity:
                    raise InputProblem(
                        "FILE_BINDING_MISMATCH", "A previously read input changed."
                    )
                self.paths[name] = existing
                return existing
            chunks = []
            count = 0
            while True:
                chunk = os.read(descriptor, min(1024 * 1024, MAX_FILE_BYTES + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
                if count > MAX_FILE_BYTES:
                    raise InputProblem("INPUT_LIMIT", "An input grew beyond the file limit.")
            after = os.fstat(descriptor)
            if stable_stat(before) != stable_stat(after) or count != before.st_size:
                raise InputProblem("FILE_BINDING_MISMATCH", "An input changed while read.")
            content = b"".join(chunks)
            item = Snapshot(content, digest(content), stable_stat(after))
            self.paths[name] = item
            self.inodes[key] = item
            return item
        except InputProblem:
            raise
        except OSError as error:
            raise InputProblem(
                "INPUT_UNAVAILABLE", "A required file cannot be read safely."
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if parent is not None:
                os.close(parent)

    def relative(self, root: str | Path, relative: str) -> Snapshot:
        return self.read(os.path.join(absolute_path(root), safe_relative(relative)))


def text_from_bytes(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        raise InputProblem("INPUT_ENCODING", "UTF-8 BOMs are not accepted.")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise InputProblem("INPUT_ENCODING", "Strict UTF-8 is required.") from error


def reject_constant(_: str) -> Any:
    raise InputProblem("NONFINITE_NUMBER", "Nonfinite JSON numbers are not accepted.")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise InputProblem("DUPLICATE_JSON_KEY", "A JSON object repeats a key.")
        result[name] = value
    return result


def strict_json(data: bytes) -> Any:
    text = text_from_bytes(data)
    try:
        value = json.loads(
            text, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except InputProblem:
        raise
    except RecursionError as error:
        raise InputProblem("INPUT_LIMIT", "JSON nesting exceeds the parser limit.") from error
    except (ValueError, OverflowError) as error:
        raise InputProblem("SCHEMA_INVALID", "Malformed JSON.") from error
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                raise InputProblem("INPUT_ENCODING", "Unpaired Unicode surrogates are invalid.")
        elif isinstance(item, float) and not math.isfinite(item):
            raise InputProblem("NONFINITE_NUMBER", "Nonfinite JSON numbers are invalid.")
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value


def strict_date(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    if DATE.fullmatch(value) is None:
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def strict_date_time(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    if DATE_TIME.fullmatch(value) is None:
        return False
    normalized = value.replace("t", "T")
    if normalized[-1:] in ("Z", "z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def format_checker() -> FormatChecker:
    checker = FormatChecker()
    # These local checks do not depend on optional jsonschema format packages.
    checker.checks("date")(strict_date)
    checker.checks("date-time")(strict_date_time)
    return checker


def schema_validator(schema: Any, definition: str | None = None) -> Draft202012Validator:
    if not isinstance(schema, dict):
        raise InputProblem("SCHEMA_INVALID", "A schema resource must be an object.")
    pending = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            for key in ("$ref", "$dynamicRef"):
                if key in node and (
                    not isinstance(node[key], str) or not node[key].startswith("#")
                ):
                    raise InputProblem(
                        "SCHEMA_INVALID", "External schema references are not permitted."
                    )
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    try:
        Draft202012Validator.check_schema(schema)
        chosen = schema
        if definition is not None:
            if definition not in schema.get("$defs", {}):
                raise InputProblem("SCHEMA_INVALID", "A required schema definition is absent.")
            chosen = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref": "#/$defs/" + definition,
                "$defs": schema["$defs"],
            }
        return Draft202012Validator(chosen, format_checker=format_checker())
    except SchemaError as error:
        raise InputProblem("SCHEMA_INVALID", "A schema resource is invalid.") from error
    except InputProblem:
        raise
    except Exception as error:
        # jsonschema versions wrap missing local references differently. Keep
        # that failure inside this schema boundary without a new dependency or
        # any external-reference retrieval, and never continue to scoring.
        raise InputProblem(
            "SCHEMA_INVALID", "A schema validator could not be constructed from local resources."
        ) from error


def validate(validator: Draft202012Validator, instance: Any) -> None:
    try:
        validator.validate(instance)
    except ValidationError as error:
        # No input value or label content is included in this diagnostic.
        raise InputProblem(
            "SCHEMA_INVALID", "An input violates the required schema."
        ) from error
    except Exception as error:
        # A dangling local #/$ref is not a ValidationError in every supported
        # jsonschema release. This narrow boundary still fails closed, without
        # importing version-specific referencing internals or emitting a trace.
        raise InputProblem(
            "SCHEMA_INVALID", "Schema evaluation could not resolve its local resources."
        ) from error


def jsonl_records(snapshot: Snapshot) -> list[tuple[dict[str, Any], str]]:
    content = snapshot.data
    if not content or not content.endswith(b"\n") or b"\r" in content:
        raise InputProblem(
            "INPUT_ENCODING", "JSONL requires nonempty LF-terminated lines without CRLF."
        )
    lines = content.split(b"\n")[:-1]
    if len(lines) > MAX_EXAMPLES:
        raise InputProblem("INPUT_LIMIT", "A JSONL file exceeds 100000 records.")
    records = []
    for line in lines:
        if not line:
            raise InputProblem("INPUT_ENCODING", "Blank JSONL lines are not permitted.")
        if len(line) > MAX_LINE_BYTES:
            raise InputProblem("INPUT_LIMIT", "A JSONL record exceeds 1 MiB.")
        item = strict_json(line)
        if not isinstance(item, dict):
            raise InputProblem("SCHEMA_INVALID", "Each JSONL record must be an object.")
        records.append((item, digest(line)))
    return records


def wilson_bounds(successes: int, total: int) -> tuple[float, float]:
    # Keep the accepted binary64 operation order; no threshold epsilon.
    p = successes / total
    z2 = Z_95 * Z_95
    den = 1.0 + z2 / total
    center = p + z2 / (2.0 * total)
    margin = Z_95 * math.sqrt(
        (p * (1.0 - p) / total) + (z2 / (4.0 * total * total))
    )
    return max(0.0, (center - margin) / den), min(1.0, (center + margin) / den)


def recompute(
    examples: dict[str, tuple[dict[str, Any], str]],
    labels: dict[str, dict[str, Any]],
    dimensions: list[str],
) -> dict[str, Any]:
    report_budget = ReportSizeBudget()
    eligible: list[tuple[str, dict[str, Any], bool]] = []
    excluded = []
    ineligible_count = 0
    unknown_count = 0
    for example_id in sorted(examples):
        example = examples[example_id][0]
        label = labels[example_id]
        if not label["q1_eligible"]:
            ineligible_count += 1
            excluded_record = {"example_id": example_id, "reason": "EMPTY_CONTEXT"}
            report_budget.account(excluded_record)
            excluded.append(excluded_record)
        elif label["q1_grounded_label"] == "UNKNOWN":
            unknown_count += 1
            excluded_record = {"example_id": example_id, "reason": "UNKNOWN_IGNORED"}
            report_budget.account(excluded_record)
            excluded.append(excluded_record)
        else:
            success = label["q1_grounded_label"] in ("SUPPORTED", "ABSTAIN")
            eligible.append((example_id, example["metadata"], success))
    total = len(eligible)
    successes = sum(success for _, _, success in eligible)
    overall = None
    overall_upper = None
    if total:
        overall_lower, overall_upper = wilson_bounds(successes, total)
        overall = {
            "pass_rate": successes / total,
            "wilson_lower": overall_lower,
            "wilson_upper": overall_upper,
        }
    union: set[str] = set()
    dimension_results = []
    worst_gap = None
    largest_small_count = 0
    missing_coverage_ok = total > 0
    for dimension in sorted(dimensions):
        # The key separates absence from an explicit "__MISSING__" string.
        buckets: dict[tuple[str, str | None], list[tuple[str, bool]]] = {}
        for example_id, metadata, success in eligible:
            key = (
                ("value", metadata[dimension])
                if dimension in metadata else ("missing", None)
            )
            buckets.setdefault(key, []).append((example_id, success))
        group_results = []
        small_count = 0
        missing_count = len(buckets.get(("missing", None), []))
        ordered_keys = sorted(
            buckets, key=lambda key: (key[0] != "missing", key[1] or "")
        )
        for kind, value in ordered_keys:
            members = buckets[(kind, value)]
            n = len(members)
            k = sum(success for _, success in members)
            included = n >= 30
            lower = upper = gap = None
            if included:
                lower, upper = wilson_bounds(k, n)
                gap = max(0.0, overall_upper - lower)
                worst_gap = gap if worst_gap is None else max(worst_gap, gap)
            else:
                small_count += n
                union.update(example_id for example_id, _ in members)
            group_result = {
                "dimension": dimension,
                "kind": kind,
                "value": value,
                "n_eligible": n,
                "n_pass": k,
                "included_in_disparity": included,
                "pass_rate": k / n,
                "wilson_lower": lower,
                "wilson_upper": upper,
                "conservative_gap": gap,
            }
            report_budget.account(group_result)
            group_results.append(group_result)
        dimension_missing_ok = total > 0 and 20 * missing_count <= total
        missing_coverage_ok = missing_coverage_ok and dimension_missing_ok
        largest_small_count = max(largest_small_count, small_count)
        dimension_results.append({
            "dimension": dimension,
            "missing_count": missing_count,
            "missing_fraction": missing_count / total if total else None,
            "small_group_count": small_count,
            "small_group_fraction": small_count / total if total else None,
            "missing_coverage_ok": dimension_missing_ok,
            "groups": group_results,
        })
    small_ok = total > 0 and 10 * len(union) <= total
    reasons = []
    if total < 200:
        reasons.append("INSUFFICIENT_ELIGIBLE_TOTAL")
    if total and not missing_coverage_ok:
        reasons.append("MISSING_GROUP_COVERAGE")
    if total and not small_ok:
        reasons.append("SMALL_GROUP_COVERAGE")
    if worst_gap is None:
        reasons.append("NO_INCLUDED_GROUPS")
    elif worst_gap > 0.05:
        reasons.append("WORST_GROUP_GAP")
    reasons.sort()
    return {
        "input_validity": "VALID",
        "metric_result": "FAIL" if reasons else "PASS",
        "pass": not reasons,
        "reason_codes": reasons,
        "counts": {
            "n_total": len(examples),
            "n_q1_ineligible": ineligible_count,
            "n_unknown_ignored": unknown_count,
            "n_q3_eligible": total,
            "n_pass": successes,
            "n_fail": total - successes,
        },
        "overall": overall,
        "dimensions": dimension_results,
        "coverage": {
            "denominator": total,
            "excluded_in_any_dimension_count": len(union),
            "excluded_in_any_dimension_fraction": len(union) / total if total else None,
            "max_per_dimension_small_group_fraction_diagnostic":
                largest_small_count / total if total else None,
            "missing_coverage_ok": missing_coverage_ok,
            "small_group_coverage_ok": small_ok,
        },
        "worst_group_gap": worst_gap,
        "excluded_records": excluded,
    }


def independently_expected(
    args: argparse.Namespace, snapshots: Snapshots, state: dict[str, Any]
) -> tuple[dict[str, Any], Draft202012Validator]:
    if args.expected is None:
        raise InputProblem(
            "MISSING_EXPECTED_CONTEXT", "A caller-selected external expected context is required."
        )
    bundle_bytes = snapshots.read(args.bundle)
    state["input_bundle_sha256"] = bundle_bytes.sha256
    expected_bytes = snapshots.read(args.expected)
    state["expected_context_sha256"] = expected_bytes.sha256
    bundle = strict_json(bundle_bytes.data)
    expected = strict_json(expected_bytes.data)
    if not isinstance(expected, dict) or not isinstance(bundle, dict):
        raise InputProblem("SCHEMA_INVALID", "Bundle and expected context must be objects.")

    resources: dict[str, Snapshot] = {}
    for name, relative in RESOURCE_PATHS.items():
        resource = snapshots.relative(args.resources_root, relative)
        resources[name] = resource
        selected = expected.get(name)
        if not isinstance(selected, str) or SHA256.fullmatch(selected) is None:
            raise InputProblem("SCHEMA_INVALID", "An expected resource digest is absent or invalid.")
        if resource.sha256 != selected:
            raise InputProblem(
                "FILE_BINDING_MISMATCH", "A resource disagrees with the selected external digest."
            )
    if resources["dataset_manifest_schema_sha256"].sha256 != MANIFEST_SCHEMA_SHA256:
        raise InputProblem("FILE_BINDING_MISMATCH", "The baseline manifest schema was changed.")

    profile = strict_json(resources["contract_sha256"].data)
    accepted_parameters = {
        "alpha": 0.05,
        "z": Z_95,
        "min_n_eligible_total": 200,
        "min_n_per_group": 30,
        "max_missing_group_fraction": 0.05,
        "max_excluded_fraction_due_to_small_groups": 0.1,
        "max_worst_group_gap": 0.05,
    }
    accepted_limits = {
        "max_file_bytes": MAX_FILE_BYTES,
        "max_jsonl_line_bytes": MAX_LINE_BYTES,
        "max_examples": MAX_EXAMPLES,
        "max_dimensions": MAX_DIMENSIONS,
    }
    if (
        not isinstance(profile, dict)
        or profile.get("record_type") != "q3_reference_recomputation_profile"
        or profile.get("profile_id") != PROFILE
        or profile.get("profile_version") != "0.1.0"
        or profile.get("status") != "ACCEPTED_FOR_STANDALONE_IMPLEMENTATION"
        or profile.get("parameters") != accepted_parameters
        or profile.get("limits") != accepted_limits
        or canonical_bytes(profile.get("permanent_boundaries"))
            != canonical_bytes(PERMANENT_BOUNDARIES)
        or profile.get("producer_identity") != {
            "tool_id": PRODUCER_ID,
            "tool_version": PRODUCER_VERSION,
            "source_paths": [PRODUCER_PATH],
        }
    ):
        raise InputProblem("SCHEMA_INVALID", "The required accepted profile is not selected.")
    input_schema = strict_json(resources["input_schema_sha256"].data)
    result_schema = strict_json(resources["result_schema_sha256"].data)
    manifest_schema = strict_json(resources["dataset_manifest_schema_sha256"].data)
    validate(schema_validator(input_schema), bundle)
    validate(schema_validator(input_schema, "expected_context"), expected)
    result_validator = schema_validator(result_schema)
    manifest_validator = schema_validator(manifest_schema)
    example_validator = schema_validator(input_schema, "example_record")
    label_validator = schema_validator(input_schema, "label_record")
    if bundle["contract_profile"] != PROFILE or expected["contract_profile"] != PROFILE:
        raise InputProblem("EXPECTED_CONTEXT_MISMATCH", "The selected profile is unsupported.")
    if expected["input_bundle_sha256"] != bundle_bytes.sha256:
        raise InputProblem("EXPECTED_CONTEXT_MISMATCH", "The selected input bundle was replaced.")
    for field in ("dataset_id", "reduction_id", "observation_subject"):
        if expected[field] != bundle[field]:
            raise InputProblem("EXPECTED_CONTEXT_MISMATCH", "A selected observation identity differs.")
    required_origin = {
        "synthetic_fixture": "synthetic_test_anchor",
        "archived_input": "caller_selected_archived_input",
    }[bundle["observation_subject"]["kind"]]
    if expected["expectation_origin"] != required_origin:
        raise InputProblem(
            "EXPECTED_CONTEXT_MISMATCH", "Observation kind and expectation origin disagree."
        )
    for field in RESOURCE_PATHS:
        if bundle["contract_bindings"][field] != expected[field]:
            raise InputProblem("EXPECTED_CONTEXT_MISMATCH", "Contract/schema identity differs.")

    for key, pin in BASELINE_SPECS.items():
        actual = snapshots.relative(args.resources_root, pin["path"])
        text_from_bytes(actual.data)
        blob = hashlib.sha1(
            b"blob " + str(len(actual.data)).encode("ascii") + b"\x00" + actual.data
        ).hexdigest()
        declared = bundle["spec_bindings"][key]
        if (
            actual.sha256 != pin["sha256"]
            or blob != pin["git_blob_sha1"]
            or declared["sha256"] != actual.sha256
            or declared["git_blob_sha1"] != blob
            or declared["repository_path"] != pin["path"]
        ):
            raise InputProblem("FILE_BINDING_MISMATCH", "A baseline specification binding differs.")

    producer = expected["expected_producer"]
    source_files = producer["source_files"]
    if (
        producer["tool_id"] != PRODUCER_ID
        or producer["tool_version"] != PRODUCER_VERSION
        or len(source_files) != 1
        or source_files[0]["path"] != PRODUCER_PATH
    ):
        raise InputProblem(
            "EXPECTED_CONTEXT_MISMATCH", "The selected producer closure is unsupported."
        )
    # Independence boundary: these bytes are hashed, never parsed/imported/run.
    producer_source = snapshots.relative(args.producer_source_root, PRODUCER_PATH)
    if producer_source.sha256 != source_files[0]["sha256"]:
        raise InputProblem("FILE_BINDING_MISMATCH", "The selected producer source digest differs.")

    bundle_parent = os.path.dirname(absolute_path(args.bundle))
    artifacts: dict[str, Snapshot] = {}
    for name in ("dataset_manifest", "examples_jsonl", "q1_labels_jsonl"):
        declaration = bundle["artifacts"][name]
        actual = snapshots.relative(bundle_parent, declaration["path"])
        if (
            len(actual.data) != declaration["size_bytes"]
            or actual.sha256 != declaration["sha256"]
        ):
            raise InputProblem("FILE_BINDING_MISMATCH", "An artifact size or SHA-256 differs.")
        artifacts[name] = actual
    manifest = strict_json(artifacts["dataset_manifest"].data)
    validate(manifest_validator, manifest)
    dimensions = manifest.get("slices", {}).get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise InputProblem("SCHEMA_INVALID", "An explicit nonempty slice declaration is required.")
    if len(dimensions) > MAX_DIMENSIONS:
        raise InputProblem("INPUT_LIMIT", "More than 64 slice dimensions were declared.")
    if len(set(dimensions)) != len(dimensions):
        raise InputProblem("DUPLICATE_DIMENSION", "The slice declaration repeats a dimension.")
    if "labels" not in manifest or "labels_sha256" not in manifest["hashes"]:
        raise InputProblem("SCHEMA_INVALID", "Label provenance and a label-file hash are required.")
    if (
        manifest["dataset_id"] != bundle["dataset_id"]
        or manifest["hashes"]["input_sha256"].lower() != artifacts["examples_jsonl"].sha256
        or manifest["hashes"]["labels_sha256"].lower() != artifacts["q1_labels_jsonl"].sha256
    ):
        raise InputProblem("MANIFEST_MISMATCH", "Manifest identity or payload hashes disagree.")
    sampling = manifest["sampling"]
    if sampling["strategy"] != "full" and (
        "seed" not in sampling
        or not isinstance(sampling.get("notes"), str)
        or not sampling["notes"].strip()
    ):
        raise InputProblem(
            "MANIFEST_MISMATCH", "Non-full sampling requires a seed and a documented protocol."
        )

    example_rows = jsonl_records(artifacts["examples_jsonl"])
    label_rows = jsonl_records(artifacts["q1_labels_jsonl"])
    examples: dict[str, tuple[dict[str, Any], str]] = {}
    for example, line_sha256 in example_rows:
        validate(example_validator, example)
        identity = example["example_id"]
        if identity in examples:
            raise InputProblem("DUPLICATE_EXAMPLE_ID", "An example identity is repeated.")
        for dimension in dimensions:
            if dimension in example["metadata"]:
                value = example["metadata"][dimension]
                if not isinstance(value, str) or value == "":
                    raise InputProblem(
                        "GROUP_VALUE_INVALID", "A present declared group value must be a nonempty string."
                    )
        examples[identity] = (example, line_sha256)
    if sampling["n"] != len(examples):
        raise InputProblem("MANIFEST_MISMATCH", "sampling.n differs from the original example count.")
    labels: dict[str, dict[str, Any]] = {}
    for label, _ in label_rows:
        if label.get("q1_exclusion_reason") not in (None, "empty_context"):
            raise InputProblem(
                "UNSUPPORTED_Q1_EXCLUSION", "This profile supports only empty-context exclusion."
            )
        validate(label_validator, label)
        identity = label["example_id"]
        if identity in labels:
            raise InputProblem("DUPLICATE_LABEL_ID", "A label identity is repeated.")
        labels[identity] = label
    if examples.keys() != labels.keys():
        raise InputProblem("LABEL_JOIN_MISMATCH", "Examples and labels do not have the same identity set.")
    for identity in sorted(examples):
        example, line_sha256 = examples[identity]
        label = labels[identity]
        if (
            label["examples_sha256"] != artifacts["examples_jsonl"].sha256
            or label["example_line_sha256"] != line_sha256
        ):
            raise InputProblem("LABEL_JOIN_MISMATCH", "A label does not bind to its exact example bytes.")
        if label["q1_eligible"] != (example["context"] != ""):
            raise InputProblem(
                "Q1_ELIGIBILITY_CONTRADICTION", "Q1 eligibility contradicts the example context."
            )

    result = {
        "record_type": "q3_recomputation_result",
        "contract_profile": PROFILE,
        "input_bundle_sha256": bundle_bytes.sha256,
        "expected_context_sha256": expected_bytes.sha256,
        "dataset_id": bundle["dataset_id"],
        "reduction_id": bundle["reduction_id"],
        "observation_subject": bundle["observation_subject"],
        "claims": dict(PERMANENT_BOUNDARIES),
        # This comes from the independently selected, source-checked caller anchor.
        "implementation": producer,
    }
    result.update(recompute(examples, labels, dimensions))
    validate(result_validator, result)
    return result, result_validator


def checker_identity(snapshots: Snapshots) -> dict[str, Any]:
    own_source = snapshots.read(__file__)
    return {
        "tool_id": CHECKER_ID,
        "tool_version": CHECKER_VERSION,
        "python_version": platform.python_version(),
        "source_files": [{"path": CHECKER_PATH, "sha256": own_source.sha256}],
    }


def write_receipt_new(path: str, payload: bytes) -> None:
    """Never overwrite an input, existing receipt or a symlink."""
    parent = None
    descriptor = None
    try:
        parent, leaf = parent_descriptor(absolute_path(path))
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(leaf, flags, 0o600, dir_fd=parent)
        written = 0
        while written < len(payload):
            amount = os.write(descriptor, payload[written:])
            if amount <= 0:
                raise OSError("receipt write did not progress")
            written += amount
        os.fsync(descriptor)
    except InputProblem:
        raise
    except OSError as error:
        raise InputProblem(
            "RECEIPT_WRITE_FAILED", "Receipt requires a new safe destination file."
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Input bundle descriptor.")
    parser.add_argument(
        "--expected", default=None, help="Independent caller-selected expected context."
    )
    parser.add_argument("--summary", required=True, help="Producer report to verify.")
    parser.add_argument("--receipt", help="Optional new file for the checker receipt.")
    parser.add_argument(
        "--resources-root", default=str(Path(__file__).absolute().parents[2]),
        help="Repository root containing the accepted profile, schemas and baseline specs.",
    )
    parser.add_argument(
        "--producer-source-root", default=None,
        help="Root of the caller-selected producer source snapshot; defaults to resources root.",
    )
    parsed = parser.parse_args(argv)
    if parsed.producer_source_root is None:
        parsed.producer_source_root = parsed.resources_root
    return parsed


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    snapshots = Snapshots()
    state: dict[str, Any] = {
        "input_validity": "INVALID",
        "input_bundle_sha256": None,
        "expected_context_sha256": None,
        "summary_sha256": None,
        "independently_expected_summary_sha256": None,
        "metric_result": None,
        "metric_pass": None,
        "summary_matches": False,
    }
    exit_code = 2
    reason_codes: list[str] = []
    detail = ""
    try:
        expected_report, report_validator = independently_expected(args, snapshots, state)
        state["input_validity"] = "VALID"
        state["metric_result"] = expected_report["metric_result"]
        state["metric_pass"] = expected_report["pass"]
        expected_data = canonical_bytes(expected_report)
        if len(expected_data) > MAX_FILE_BYTES:
            raise InputProblem("INPUT_LIMIT", "Expected report exceeds the bounded file profile.")
        state["independently_expected_summary_sha256"] = digest(expected_data)
        try:
            report_snapshot = snapshots.read(args.summary)
            state["summary_sha256"] = report_snapshot.sha256
            actual_report = strict_json(report_snapshot.data)
            validate(report_validator, actual_report)
        except InputProblem as error:
            raise ReportProblem(
                "SUMMARY_MISMATCH", "The report is unreadable or violates its strict schema."
            ) from error
        if report_snapshot.data != expected_data:
            raise ReportProblem(
                "SUMMARY_MISMATCH", "The report differs from independent canonical recomputation."
            )
        state["summary_matches"] = True
        exit_code = 0
    except ReportProblem as error:
        exit_code = 1
        reason_codes = [error.code]
        detail = error.detail
    except InputProblem as error:
        exit_code = 2
        reason_codes = [error.code]
        detail = error.detail
        state.update({
            "input_validity": "INVALID",
            "metric_result": None,
            "metric_pass": None,
            "summary_matches": False,
            "independently_expected_summary_sha256": None,
        })
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        exit_code = 2
        reason_codes = ["CHECKER_ERROR"]
        detail = "The checker could not complete the selected bounded profile."
        state.update({
            "input_validity": "INVALID",
            "metric_result": None,
            "metric_pass": None,
            "summary_matches": False,
            "independently_expected_summary_sha256": None,
        })

    receipt = {
        "record_type": "q3_independent_verification_receipt",
        "contract_profile": PROFILE,
        "checker_exit_code": exit_code,
        "verification_result": (
            "MATCH" if exit_code == 0 else "REPORT_REJECTED" if exit_code == 1 else "INPUT_INVALID"
        ),
        **state,
        "reason_codes": reason_codes,
        "detail": detail,
        "authority_effect": "none",
        "production_gate_eligible": False,
        "current_run_evidence": False,
        "source_authentication": "not_established",
        "producer_execution_authenticated": False,
    }
    try:
        receipt["checker_implementation"] = checker_identity(snapshots)
        payload = canonical_bytes(receipt)
        if args.receipt:
            write_receipt_new(args.receipt, payload)
    except InputProblem as error:
        exit_code = 2
        receipt["checker_exit_code"] = exit_code
        receipt["verification_result"] = "CHECKER_ERROR"
        receipt["reason_codes"] = [error.code]
        receipt["detail"] = error.detail
        payload = canonical_bytes(receipt)
    sys.stdout.buffer.write(payload)
    if receipt["detail"]:
        print(
            "{}: {}".format(",".join(receipt["reason_codes"]), receipt["detail"]),
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

