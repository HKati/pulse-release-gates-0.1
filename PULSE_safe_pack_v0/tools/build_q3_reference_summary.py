#!/usr/bin/env python3
"""Recompute the accepted standalone Q3 profile from bound local input bytes.

This tool neither acquires evidence nor activates a release gate. Labels, origin
and slice metadata remain supplied claims. The expected context is a separate,
caller-selected anchor; consistent hashes do not authenticate the original run.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError


PROFILE_ID = "q3_input_recomputation_v0.1"
SOURCE_PATH = "PULSE_safe_pack_v0/tools/build_q3_reference_summary.py"
PROFILE_PATH = "PULSE_safe_pack_v0/profiles/q3_reference_recomputation_v0.json"
INPUT_SCHEMA_PATH = "schemas/metrics/q3_input_bundle_v0.schema.json"
RESULT_SCHEMA_PATH = "schemas/metrics/q3_reference_summary_v0.schema.json"
MANIFEST_SCHEMA_PATH = "schemas/dataset_manifest.schema.json"
MAX_FILE_BYTES = 67_108_864
MAX_LINE_BYTES = 1_048_576
MAX_ROWS = 100_000
MAX_DIMENSIONS = 64
Z_95 = 1.959963984540054

BASELINE_HASHES = {
    "metrics/specs/q1_groundedness_v0.yml":
        "a63625ca894294e0fbe4febffdd143d22929dcaa44ea52a6aaa02453f0aac65f",
    "metrics/specs/q3_fairness_v0.yml":
        "58fc3ddbf636ffdcadc9ca3ce07e6051ff9801d49e9593b7c8e79970a08e782e",
    MANIFEST_SCHEMA_PATH:
        "7bd729958c65dfde432925a4d3fccbd50c846cca19c891411ed085166ecdfead",
}
PARAMETERS = {
    "alpha": 0.05,
    "z": Z_95,
    "min_n_eligible_total": 200,
    "min_n_per_group": 30,
    "max_missing_group_fraction": 0.05,
    "max_excluded_fraction_due_to_small_groups": 0.1,
    "max_worst_group_gap": 0.05,
}
CLAIMS = {
    "authority_effect": "none",
    "production_gate_eligible": False,
    "current_run_evidence": False,
    "source_authentication": "not_established",
    "label_correctness": "not_verified",
    "slice_metadata_correctness": "not_verified",
    "policy_activation": False,
}
RELATIVE_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})"
)


class InputFailure(Exception):
    """A stable public reason, without input contents or filesystem details."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not RELATIVE_PATH.fullmatch(relative)
            or any(part in (".", "..") for part in relative.split("/"))):
        raise InputFailure("SCHEMA_INVALID")
    return root.joinpath(*relative.split("/"))


def parent_directory(path: Path) -> tuple[int, str]:
    """Walk every parent using directory descriptors, without symlink traversal."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/", flags)
    try:
        for component in absolute.parts[1:-1]:
            following = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = following
        return fd, absolute.name
    except BaseException:
        os.close(fd)
        raise


def stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class Snapshots:
    """A single bounded, immutable byte snapshot per absolute input path."""

    def __init__(self) -> None:
        self._bytes: dict[str, bytes] = {}

    def read(self, path: Path) -> bytes:
        key = os.path.abspath(os.fspath(path))
        if key in self._bytes:
            return self._bytes[key]
        parent = None
        fd = None
        try:
            parent, name = parent_directory(Path(key))
            # O_NONBLOCK prevents a FIFO from hanging before the regular-file test.
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                         | os.O_CLOEXEC, dir_fd=parent)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise InputFailure("INPUT_UNAVAILABLE")
            if before.st_size > MAX_FILE_BYTES:
                raise InputFailure("INPUT_LIMIT")
            chunks = []
            length = 0
            while True:
                chunk = os.read(fd, min(1_048_576, MAX_FILE_BYTES + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                if length > MAX_FILE_BYTES:
                    raise InputFailure("INPUT_LIMIT")
            after = os.fstat(fd)
            if stat_identity(before) != stat_identity(after) or length != before.st_size:
                raise InputFailure("FILE_BINDING_MISMATCH")
            data = b"".join(chunks)
            self._bytes[key] = data
            return data
        except OSError as exc:
            raise InputFailure("INPUT_UNAVAILABLE") from exc
        finally:
            if fd is not None:
                os.close(fd)
            if parent is not None:
                os.close(parent)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputFailure("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise InputFailure("NONFINITE_NUMBER")
    return number


def forbidden_constant(_value: str) -> None:
    raise InputFailure("NONFINITE_NUMBER")


def check_unicode(value: object, path: tuple = (), dimensions: frozenset = frozenset()) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            # A declared group value has a more specific accepted failure code.
            code = ("GROUP_VALUE_INVALID" if len(path) == 2
                    and path[0] == "metadata" and path[1] in dimensions
                    else "INPUT_ENCODING")
            raise InputFailure(code)
    elif isinstance(value, dict):
        for key, item in value.items():
            check_unicode(key)
            check_unicode(item, path + (key,), dimensions)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_unicode(item, path + (index,), dimensions)


def strict_json(data: bytes, dimensions: frozenset = frozenset()) -> object:
    try:
        if data.startswith(b"\xef\xbb\xbf"):
            raise InputFailure("INPUT_ENCODING")
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=unique_object,
                           parse_float=finite_float, parse_constant=forbidden_constant)
        check_unicode(value, dimensions=dimensions)
        return value
    except UnicodeError as exc:
        raise InputFailure("INPUT_ENCODING") from exc
    except RecursionError as exc:
        raise InputFailure("INPUT_LIMIT") from exc
    except (ValueError, OverflowError) as exc:
        raise InputFailure("SCHEMA_INVALID") from exc


def jsonl_rows(data: bytes, dimensions: frozenset = frozenset()) -> list[tuple[dict, str]]:
    if not data or not data.endswith(b"\n") or b"\r" in data:
        raise InputFailure("INPUT_ENCODING")
    raw_lines = data.split(b"\n")[:-1]
    if len(raw_lines) > MAX_ROWS:
        raise InputFailure("INPUT_LIMIT")
    result = []
    for raw in raw_lines:
        if not raw:
            raise InputFailure("INPUT_ENCODING")
        if len(raw) > MAX_LINE_BYTES:
            raise InputFailure("INPUT_LIMIT")
        record = strict_json(raw, dimensions)
        if not isinstance(record, dict):
            raise InputFailure("SCHEMA_INVALID")
        result.append((record, digest(raw)))
    return result


FORMATS = FormatChecker(formats=[])


@FORMATS.checks("date")
def valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not DATE.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


@FORMATS.checks("date-time")
def valid_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not DATE_TIME.fullmatch(value):
        return False
    normalized = value.upper()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    else:
        # fromisoformat accepts overflowing offset minutes; RFC 3339 does not.
        if int(normalized[-5:-3]) > 23 or int(normalized[-2:]) > 59:
            return False
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
        return parsed.tzinfo is not None
    except ValueError:
        return False


def reject_external_refs(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("$ref", "$dynamicRef") and (
                    not isinstance(child, str) or not child.startswith("#")):
                raise InputFailure("SCHEMA_INVALID")
            reject_external_refs(child)
    elif isinstance(value, list):
        for child in value:
            reject_external_refs(child)


def validator(schema: object, definition: str | None = None) -> Draft202012Validator:
    try:
        reject_external_refs(schema)
        Draft202012Validator.check_schema(schema)
        if definition is not None:
            schema = {"$schema": schema["$schema"], "$defs": schema["$defs"],
                      "$ref": "#/$defs/" + definition}
        return Draft202012Validator(schema, format_checker=FORMATS)
    except (SchemaError, KeyError, TypeError, RecursionError) as exc:
        raise InputFailure("SCHEMA_INVALID") from exc
    except Exception as exc:
        # jsonschema versions expose local-reference resolution failures through
        # different exception classes. A broken schema must never escape as a
        # traceback or trigger acceptance; no optional resolver is required.
        raise InputFailure("SCHEMA_INVALID") from exc


def validate(instance: object, rule: Draft202012Validator) -> None:
    try:
        rule.validate(instance)
    except ValidationError as exc:
        raise InputFailure("SCHEMA_INVALID") from exc
    except RecursionError as exc:
        raise InputFailure("INPUT_LIMIT") from exc
    except Exception as exc:
        # Keep unresolved local references and other schema-evaluation failures
        # fail-closed across the repository's existing jsonschema>=4 dependency.
        raise InputFailure("SCHEMA_INVALID") from exc


def load_resources(root: Path, snapshots: Snapshots) -> dict:
    paths = {"contract_sha256": PROFILE_PATH,
             "input_schema_sha256": INPUT_SCHEMA_PATH,
             "result_schema_sha256": RESULT_SCHEMA_PATH,
             "dataset_manifest_schema_sha256": MANIFEST_SCHEMA_PATH}
    raw = {key: snapshots.read(relative_path(root, path)) for key, path in paths.items()}
    documents = {key: strict_json(data) for key, data in raw.items()}
    input_schema = documents["input_schema_sha256"]
    output_schema = documents["result_schema_sha256"]
    manifest_schema = documents["dataset_manifest_schema_sha256"]
    return {
        "hashes": {key: digest(data) for key, data in raw.items()},
        "profile": documents["contract_sha256"],
        "bundle_validator": validator(input_schema),
        "expected_validator": validator(input_schema, "expected_context"),
        "example_validator": validator(input_schema, "example_record"),
        "label_validator": validator(input_schema, "label_record"),
        "result_validator": validator(output_schema),
        "manifest_validator": validator(manifest_schema),
    }


def check_profile(profile: object) -> None:
    if not isinstance(profile, dict):
        raise InputFailure("SCHEMA_INVALID")
    required = {
        "record_type": "q3_reference_recomputation_profile",
        "profile_id": PROFILE_ID,
        "profile_version": "0.1.0",
        "status": "ACCEPTED_FOR_STANDALONE_IMPLEMENTATION",
        "parameters": PARAMETERS,
        "limits": {"max_file_bytes": MAX_FILE_BYTES,
                   "max_jsonl_line_bytes": MAX_LINE_BYTES,
                   "max_examples": MAX_ROWS, "max_dimensions": MAX_DIMENSIONS},
        "producer_identity": {"tool_id": "PULSE_q3_reference", "tool_version": "0.1.0",
                              "source_paths": [SOURCE_PATH]},
        "permanent_boundaries": CLAIMS,
    }
    if any(profile.get(key) != value for key, value in required.items()):
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")


def own_identity(script: Path, snapshots: Snapshots) -> dict:
    return {"tool_id": "PULSE_q3_reference", "tool_version": "0.1.0",
            "python_version": platform.python_version(),
            "source_files": [{"path": SOURCE_PATH,
                              "sha256": digest(snapshots.read(script))}]}


def check_source(expected: dict, actual: dict, root: Path, snapshots: Snapshots) -> None:
    source_files = expected["source_files"]
    if [entry["path"] for entry in source_files] != [SOURCE_PATH]:
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    entry = source_files[0]
    snapshot = snapshots.read(relative_path(root, entry["path"]))
    if digest(snapshot) != entry["sha256"]:
        raise InputFailure("FILE_BINDING_MISMATCH")
    if expected != actual:
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")


def check_manifest(manifest: dict, bundle: dict, examples_bytes: bytes,
                   labels_bytes: bytes) -> list[str]:
    slices = manifest.get("slices", {})
    dimensions = slices.get("dimensions")
    if (not isinstance(dimensions, list) or not dimensions
            or any(not isinstance(item, str) or item == "" for item in dimensions)):
        raise InputFailure("SCHEMA_INVALID")
    if len(dimensions) > MAX_DIMENSIONS:
        raise InputFailure("INPUT_LIMIT")
    if len(set(dimensions)) != len(dimensions):
        raise InputFailure("DUPLICATE_DIMENSION")
    if "labels" not in manifest or "labels_sha256" not in manifest["hashes"]:
        raise InputFailure("SCHEMA_INVALID")
    if (manifest["dataset_id"] != bundle["dataset_id"]
            or manifest["hashes"]["input_sha256"].lower() != digest(examples_bytes)
            or manifest["hashes"]["labels_sha256"].lower() != digest(labels_bytes)):
        raise InputFailure("MANIFEST_MISMATCH")
    sampling = manifest["sampling"]
    if sampling["strategy"] != "full" and (
            "seed" not in sampling or not sampling.get("notes", "").strip()):
        raise InputFailure("MANIFEST_MISMATCH")
    return sorted(dimensions)


def validate_records(examples_bytes: bytes, labels_bytes: bytes, dimensions: list[str],
                     manifest: dict, resources: dict) -> tuple[dict, dict]:
    rows = jsonl_rows(examples_bytes, frozenset(dimensions))
    examples = {}
    line_hashes = {}
    for row, line_hash in rows:
        validate(row, resources["example_validator"])
        example_id = row["example_id"]
        if example_id in examples:
            raise InputFailure("DUPLICATE_EXAMPLE_ID")
        for dimension in dimensions:
            if dimension in row["metadata"]:
                value = row["metadata"][dimension]
                if not isinstance(value, str) or value == "":
                    raise InputFailure("GROUP_VALUE_INVALID")
        examples[example_id] = row
        line_hashes[example_id] = line_hash
    # Duplicate example identities are checked before any label parsing or join.
    label_rows = jsonl_rows(labels_bytes)
    labels = {}
    examples_hash = digest(examples_bytes)
    for row, _line_hash in label_rows:
        if "q1_exclusion_reason" in row and row["q1_exclusion_reason"] not in (
                None, "empty_context"):
            raise InputFailure("UNSUPPORTED_Q1_EXCLUSION")
        validate(row, resources["label_validator"])
        example_id = row["example_id"]
        if example_id in labels:
            raise InputFailure("DUPLICATE_LABEL_ID")
        labels[example_id] = row
    if set(examples) != set(labels):
        raise InputFailure("LABEL_JOIN_MISMATCH")
    for example_id, row in labels.items():
        if (row["examples_sha256"] != examples_hash
                or row["example_line_sha256"] != line_hashes[example_id]):
            raise InputFailure("LABEL_JOIN_MISMATCH")
        if row["q1_eligible"] != (examples[example_id]["context"] != ""):
            raise InputFailure("Q1_ELIGIBILITY_CONTRADICTION")
    if manifest["sampling"]["n"] != len(examples):
        raise InputFailure("MANIFEST_MISMATCH")
    return examples, labels


def bound_inputs(args: argparse.Namespace, snapshots: Snapshots, resources: dict,
                 identity: dict, observed: dict) -> tuple[dict, dict, dict, list[str]]:
    # Both raw-file digests can be reported even if ordered validation fails.
    bundle_error = None
    bundle_bytes = None
    try:
        bundle_bytes = snapshots.read(Path(args.bundle))
        observed["input_bundle_sha256"] = digest(bundle_bytes)
    except InputFailure as exc:
        bundle_error = exc
    if args.expected is None:
        raise InputFailure("MISSING_EXPECTED_CONTEXT")
    expected_bytes = snapshots.read(Path(args.expected))
    observed["expected_context_sha256"] = digest(expected_bytes)
    expected = strict_json(expected_bytes)
    validate(expected, resources["expected_validator"])
    for key, actual_hash in resources["hashes"].items():
        if expected[key] != actual_hash:
            raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    check_profile(resources["profile"])
    check_source(expected["expected_producer"], identity,
                 Path(args.producer_source_root), snapshots)
    expected_kind = {"synthetic_fixture": "synthetic_test_anchor",
                     "archived_input": "caller_selected_archived_input"}
    if expected["expectation_origin"] != expected_kind[expected["observation_subject"]["kind"]]:
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    if bundle_error is not None:
        raise bundle_error
    if expected["input_bundle_sha256"] != observed["input_bundle_sha256"]:
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    bundle = strict_json(bundle_bytes)
    validate(bundle, resources["bundle_validator"])
    for key in ("dataset_id", "reduction_id", "observation_subject"):
        if bundle[key] != expected[key]:
            raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    if bundle["contract_bindings"] != resources["hashes"]:
        raise InputFailure("EXPECTED_CONTEXT_MISMATCH")
    resource_root = Path(args.resources_root)
    for path, pinned_hash in BASELINE_HASHES.items():
        if digest(snapshots.read(relative_path(resource_root, path))) != pinned_hash:
            raise InputFailure("FILE_BINDING_MISMATCH")
    artifacts = {}
    bundle_root = Path(os.path.abspath(args.bundle)).parent
    for role in ("dataset_manifest", "examples_jsonl", "q1_labels_jsonl"):
        binding = bundle["artifacts"][role]
        data = snapshots.read(relative_path(bundle_root, binding["path"]))
        if len(data) != binding["size_bytes"] or digest(data) != binding["sha256"]:
            raise InputFailure("FILE_BINDING_MISMATCH")
        artifacts[role] = data
    manifest = strict_json(artifacts["dataset_manifest"])
    validate(manifest, resources["manifest_validator"])
    dimensions = check_manifest(manifest, bundle, artifacts["examples_jsonl"],
                                artifacts["q1_labels_jsonl"])
    examples, labels = validate_records(artifacts["examples_jsonl"],
                                       artifacts["q1_labels_jsonl"], dimensions,
                                       manifest, resources)
    return bundle, examples, labels, dimensions


def wilson(k: int, n: int) -> tuple[float, float]:
    p = k / n
    z2 = Z_95 * Z_95
    den = 1.0 + z2 / n
    center = p + z2 / (2.0 * n)
    margin = Z_95 * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))
    lower = max(0.0, (center - margin) / den)
    upper = min(1.0, (center + margin) / den)
    return lower, upper


class OutputBudget:
    """Count disjoint compact fragments: a lower bound on the pretty report."""

    def __init__(self) -> None:
        self.minimum_size = 0

    def add_fragment(self, fragment: dict) -> None:
        self.minimum_size += len(json.dumps(fragment, ensure_ascii=False,
                                            separators=(",", ":"), allow_nan=False).encode("utf-8"))
        if self.minimum_size > MAX_FILE_BYTES:
            raise InputFailure("INPUT_LIMIT")


def empty_report(identity: dict, observed: dict) -> dict:
    return {"record_type": "q3_recomputation_result", "contract_profile": PROFILE_ID,
            "input_bundle_sha256": observed["input_bundle_sha256"],
            "expected_context_sha256": observed["expected_context_sha256"],
            "dataset_id": None, "reduction_id": None, "observation_subject": None,
            "input_validity": "INVALID", "metric_result": "FAIL", "pass": False,
            "reason_codes": [], "counts": None, "overall": None, "dimensions": [],
            "coverage": None, "worst_group_gap": None, "excluded_records": [],
            "claims": dict(CLAIMS), "implementation": identity}


def recompute(bundle: dict, examples: dict, labels: dict, dimensions: list[str],
              identity: dict, observed: dict) -> dict:
    report = empty_report(identity, observed)
    budget = OutputBudget()
    eligible = {}
    excluded = []
    q1_ineligible = 0
    unknown_ignored = 0
    for example_id in sorted(examples):
        row = labels[example_id]
        if not row["q1_eligible"]:
            q1_ineligible += 1
            reason = "EMPTY_CONTEXT"
        elif row["q1_grounded_label"] == "UNKNOWN":
            unknown_ignored += 1
            reason = "UNKNOWN_IGNORED"
        else:
            eligible[example_id] = row["q1_grounded_label"] in ("SUPPORTED", "ABSTAIN")
            continue
        entry = {"example_id": example_id, "reason": reason}
        budget.add_fragment(entry)
        excluded.append(entry)
    n = len(eligible)
    successes = sum(eligible.values())
    overall = None
    if n:
        lower, upper = wilson(successes, n)
        overall = {"pass_rate": successes / n, "wilson_lower": lower, "wilson_upper": upper}
    result_dimensions = []
    small_union = set()
    worst_gap = None
    max_small_count = 0
    all_missing_ok = bool(n)
    for dimension in dimensions:
        # Build one marginal dimension at a time; E is never pruned by coverage.
        marginal = {}
        for example_id, success in eligible.items():
            metadata = examples[example_id]["metadata"]
            key = (1, metadata[dimension]) if dimension in metadata else (0, None)
            if key not in marginal:
                marginal[key] = [0, 0, []]
            group = marginal[key]
            group[0] += 1
            group[1] += int(success)
            # Membership is only needed for small groups. Drop it at n=30.
            if group[0] < 30:
                group[2].append(example_id)
            elif group[0] == 30:
                group[2] = []
        groups = []
        small_count = 0
        missing_count = marginal.get((0, None), [0])[0]
        for (kind, value), (group_n, group_pass, members) in sorted(marginal.items()):
            included = group_n >= 30
            group_lower = group_upper = gap = None
            if included:
                group_lower, group_upper = wilson(group_pass, group_n)
                gap = max(0.0, overall["wilson_upper"] - group_lower)
                worst_gap = gap if worst_gap is None else max(worst_gap, gap)
            else:
                small_count += group_n
                small_union.update(members)
            record = {"dimension": dimension, "kind": "value" if kind else "missing",
                      "value": value, "n_eligible": group_n, "n_pass": group_pass,
                      "included_in_disparity": included, "pass_rate": group_pass / group_n,
                      "wilson_lower": group_lower, "wilson_upper": group_upper,
                      "conservative_gap": gap}
            budget.add_fragment(record)
            groups.append(record)
        missing_ok = bool(n and 20 * missing_count <= n)
        all_missing_ok = all_missing_ok and missing_ok
        max_small_count = max(max_small_count, small_count)
        result_dimensions.append({"dimension": dimension, "missing_count": missing_count,
                                  "missing_fraction": missing_count / n if n else None,
                                  "small_group_count": small_count,
                                  "small_group_fraction": small_count / n if n else None,
                                  "missing_coverage_ok": missing_ok, "groups": groups})
    small_ok = bool(n and 10 * len(small_union) <= n)
    reasons = []
    if n < 200:
        reasons.append("INSUFFICIENT_ELIGIBLE_TOTAL")
    if n and not all_missing_ok:
        reasons.append("MISSING_GROUP_COVERAGE")
    if n and not small_ok:
        reasons.append("SMALL_GROUP_COVERAGE")
    if worst_gap is None:
        reasons.append("NO_INCLUDED_GROUPS")
    elif worst_gap > 0.05:
        reasons.append("WORST_GROUP_GAP")
    report.update({
        "dataset_id": bundle["dataset_id"], "reduction_id": bundle["reduction_id"],
        "observation_subject": bundle["observation_subject"], "input_validity": "VALID",
        "metric_result": "FAIL" if reasons else "PASS", "pass": not reasons,
        "reason_codes": sorted(reasons),
        "counts": {"n_total": len(examples), "n_q1_ineligible": q1_ineligible,
                   "n_unknown_ignored": unknown_ignored, "n_q3_eligible": n,
                   "n_pass": successes, "n_fail": n - successes},
        "overall": overall, "dimensions": result_dimensions,
        "coverage": {"denominator": n, "excluded_in_any_dimension_count": len(small_union),
                     "excluded_in_any_dimension_fraction": len(small_union) / n if n else None,
                     "max_per_dimension_small_group_fraction_diagnostic":
                         max_small_count / n if n else None,
                     "missing_coverage_ok": all_missing_ok, "small_group_coverage_ok": small_ok},
        "worst_group_gap": worst_gap, "excluded_records": excluded,
    })
    return report


def canonical_bytes(report: dict) -> bytes:
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise InputFailure("INPUT_LIMIT")
    return data


def write_new_output(path: Path, data: bytes) -> None:
    """Create exactly one new regular file; existing aliases are never opened."""
    parent = None
    fd = None
    created = None
    try:
        parent, name = parent_directory(path)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                     | os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=parent)
        created = os.fstat(fd)
        if not stat.S_ISREG(created.st_mode):
            raise OSError("output is not regular")
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("incomplete output")
            remaining = remaining[written:]
        os.fsync(fd)
    except BaseException:
        if created is not None and parent is not None:
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                    os.unlink(name, dir_fd=parent)
            except OSError:
                pass
        raise
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def main(argv: list[str] | None = None) -> int:
    script = Path(os.path.abspath(__file__))
    default_root = script.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Local Q3 input descriptor")
    parser.add_argument("--expected", help="Separate caller-selected expected context")
    parser.add_argument("--out", required=True, help="New result path; must not exist")
    parser.add_argument("--resources-root", default=str(default_root))
    parser.add_argument("--producer-source-root", default=str(default_root))
    args = parser.parse_args(argv)
    snapshots = Snapshots()
    observed = {"input_bundle_sha256": None, "expected_context_sha256": None}
    try:
        identity = own_identity(script, snapshots)
        resources = load_resources(Path(args.resources_root), snapshots)
    except (InputFailure, OSError, ValueError, TypeError, AttributeError):
        print("q3_reference: SOURCE_UNAVAILABLE", file=sys.stderr)
        return 2
    try:
        bundle, examples, labels, dimensions = bound_inputs(
            args, snapshots, resources, identity, observed)
        report = recompute(bundle, examples, labels, dimensions, identity, observed)
        validate(report, resources["result_validator"])
        data = canonical_bytes(report)
    except InputFailure as exc:
        report = empty_report(identity, observed)
        report["reason_codes"] = [exc.code]
        try:
            validate(report, resources["result_validator"])
            data = canonical_bytes(report)
        except InputFailure:
            print("q3_reference: RESULT_SCHEMA_INVALID", file=sys.stderr)
            return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print("q3_reference: PROCESSING_ERROR", file=sys.stderr)
        return 2
    try:
        write_new_output(Path(args.out), data)
    except (OSError, ValueError, AttributeError):
        print("q3_reference: OUTPUT_UNAVAILABLE", file=sys.stderr)
        return 2
    if report["input_validity"] == "INVALID":
        return 2
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
