#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import jsonschema


TOOL_ID = "build_pulsemech_compute_planned_observed_relation_v0"
TOOL_VERSION = "0.1.0"
RELATION_SCHEMA_VERSION = "pulsemech_compute_planned_observed_relation_v0"
RELATION_TYPE = "pulsemech_compute_planned_observed_relation"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_SCHEMA = ROOT / "schemas" / "pulsemech_integration_plan_v0.schema.json"
DEFAULT_REPORT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
DEFAULT_PACKET_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
DEFAULT_RELATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
DEFAULT_REPORT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
DEFAULT_PACKET_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_runtime_observation_packet_v0.py"
)
DEFAULT_RELATION_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

OPERATION_DIGEST_FIELDS = (
    "action",
    "component_id",
    "reason",
    "source_path",
    "source_sha256",
    "source_size_bytes",
    "target_path",
    "target_state",
)

EXPECTATION_KINDS = (
    "planned_presence_only",
    "planned_execution_expected",
    "planned_execution_and_consumption_expected",
)

RELATION_STATUSES = (
    "planned_presence_only",
    "planned_and_observed",
    "planned_but_not_observed",
    "observed_but_not_planned",
    "execution_identity_mismatch",
    "source_digest_mismatch",
    "run_binding_mismatch",
    "declared_role_mismatch",
    "authority_class_mismatch",
    "downstream_consumption_missing",
    "ambiguous_observation_match",
    "unresolved_due_to_coverage",
)

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

MUTATION_AUTHORITY_RANK = {
    "none": 0,
    "advisory_output": 10,
    "preservation_output": 20,
    "release_evidence": 30,
    "candidate_state": 40,
    "verifier_state": 50,
    "materialized_gate_set": 60,
    "final_status": 70,
    "release_decision": 80,
}

ROLE_TO_BOUND_CLASS = {
    "transition": "transition_bound",
    "evidence": "evidence_bound",
    "preservation": "preservation_bound",
    "advisory": "advisory_bound",
    "observer": "observer",
}

RUNTIME_OBSERVATION_KINDS = {
    "runtime_execution",
    "external_call",
    "model_inference",
}

FINDING_TYPE_BY_RELATION_STATUS = {
    "planned_but_not_observed": "planned_execution_not_observed",
    "observed_but_not_planned": "observed_execution_not_planned",
    "execution_identity_mismatch": "execution_identity_mismatch",
    "source_digest_mismatch": "source_digest_mismatch",
    "run_binding_mismatch": "run_binding_mismatch",
    "declared_role_mismatch": "declared_role_mismatch",
    "authority_class_mismatch": "authority_class_mismatch",
    "downstream_consumption_missing": "downstream_consumption_missing",
    "ambiguous_observation_match": "ambiguous_observation_match",
    "unresolved_due_to_coverage": "comparison_coverage_partial",
}


class BuilderError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Strict parsing, validation, canonical rendering, and safe output
# ---------------------------------------------------------------------------


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def require_regular_non_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise BuilderError(f"{label}_is_symlink: {path}")
    if not path.is_file():
        raise BuilderError(f"{label}_not_regular_file: {path}")


def load_json_document(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    require_regular_non_symlink(path, label=label)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BuilderError(f"{label}_read_failed: {path}: {exc}") from exc

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise BuilderError(f"{label}_json_invalid: {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise BuilderError(f"{label}_not_object: {path}")
    return value, raw


def render_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def validate_schema_document(schema: dict[str, Any], *, label: str) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise BuilderError(f"{label}_schema_invalid: {exc}") from exc


def schema_errors(schema: dict[str, Any], value: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(
            validator.iter_errors(value),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    ]


def validate_document(
    *,
    schema: dict[str, Any],
    value: Any,
    label: str,
) -> None:
    errors = schema_errors(schema, value)
    if errors:
        raise BuilderError(f"{label}_invalid: " + "; ".join(errors))


def expectations_input_schema(relation_schema: dict[str, Any]) -> dict[str, Any]:
    try:
        definitions = copy.deepcopy(relation_schema["$defs"])
    except KeyError as exc:
        raise BuilderError("relation_schema_missing_defs") from exc
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": definitions,
        "type": "object",
        "propertyNames": {"$ref": "#/$defs/expectation_id"},
        "additionalProperties": {"$ref": "#/$defs/expectation_record"},
    }


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        pass
    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass
    return False


def path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
        return True
    except (OSError, ValueError):
        return False


def reject_symlink_chain(path: Path) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise BuilderError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def reject_unsafe_output(
    output: Path | None,
    *,
    protected_paths: Sequence[Path],
    subject_root: Path | None,
) -> None:
    if output is None:
        return

    for protected in protected_paths:
        if same_target(output, protected):
            raise BuilderError(f"refusing_to_overwrite_input: {protected}")

    if output.name in {"status.json", "release_decision_v0.json"}:
        raise BuilderError(
            f"refusing_authority_surface_output: {output.name}"
        )

    reject_symlink_chain(output)

    if subject_root is None:
        raise BuilderError("subject_root_required_when_output_is_used")
    if subject_root.is_symlink():
        raise BuilderError(f"subject_root_is_symlink: {subject_root}")
    if not subject_root.is_dir():
        raise BuilderError(f"subject_root_not_directory: {subject_root}")
    if path_is_within(output, subject_root):
        raise BuilderError(f"refusing_output_inside_subject_root: {output}")


def snapshot_regular_files(
    paths: Iterable[Path],
) -> dict[Path, tuple[int, str]]:
    result: dict[Path, tuple[int, str]] = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            continue
        canonical = path.resolve(strict=True)
        result[canonical] = (canonical.stat().st_size, sha256_file(canonical))
    return result


def verify_regular_file_snapshots(
    snapshots: dict[Path, tuple[int, str]],
) -> None:
    for path, expected in snapshots.items():
        if path.is_symlink() or not path.is_file():
            raise BuilderError(f"protected_input_changed_or_missing: {path}")
        observed = (path.stat().st_size, sha256_file(path))
        if observed != expected:
            raise BuilderError(f"protected_input_changed: {path}")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    reject_symlink_chain(path)

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def invoke_json_validator(
    *,
    validator_path: Path,
    schema_path: Path,
    document_path: Path,
    document_flag: str,
    label: str,
) -> dict[str, Any]:
    require_regular_non_symlink(validator_path, label=f"{label}_validator")
    require_regular_non_symlink(schema_path, label=f"{label}_schema")
    require_regular_non_symlink(document_path, label=label)
    result = subprocess.run(
        [
            sys.executable,
            str(validator_path),
            "--schema",
            str(schema_path),
            document_flag,
            str(document_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stdout.strip() or result.stderr.strip()
        raise BuilderError(f"{label}_strict_validation_failed: {detail}")
    try:
        diagnostic = json.loads(result.stdout)
    except Exception as exc:
        raise BuilderError(f"{label}_validator_diagnostic_invalid: {exc}") from exc
    if not isinstance(diagnostic, dict) or diagnostic.get("ok") is not True:
        raise BuilderError(
            f"{label}_validator_returned_not_ok: "
            + json.dumps(diagnostic, sort_keys=True)
        )
    return diagnostic


# ---------------------------------------------------------------------------
# Deterministic identities and shared mechanics
# ---------------------------------------------------------------------------


def git_head(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        return None
    revision = result.stdout.strip().lower()
    return revision if re.fullmatch(r"[0-9a-f]{40}", revision) else None


def git_revision_contains_current_tool(revision: str) -> bool | None:
    try:
        relative = Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return None
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{revision}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        return None
    try:
        return result.stdout == Path(__file__).read_bytes()
    except OSError:
        return False


def resolve_tool_source_revision(
    explicit: str | None,
    *,
    record_status: str,
) -> str | None:
    if explicit is not None:
        normalized = explicit.strip().lower()
        if re.fullmatch(r"[0-9a-f]{40}", normalized) is None:
            raise BuilderError(f"tool_source_revision_invalid: {explicit!r}")
        match = git_revision_contains_current_tool(normalized)
        if match is None:
            raise BuilderError(
                "tool_source_revision_unverifiable"
            )
        if match is False:
            raise BuilderError(
                "tool_source_revision_does_not_match_builder_bytes"
            )
        return normalized

    discovered = git_head(ROOT)
    if discovered is not None:
        match = git_revision_contains_current_tool(discovered)
        if match is True:
            return discovered
        if match is False and record_status == "observed":
            raise BuilderError(
                "tool_source_revision_does_not_match_builder_bytes"
            )
    if record_status == "observed":
        raise BuilderError("tool_source_revision_required_for_observed_record")
    return None


def slug(value: str, *, fallback: str = "record") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._+-]+", "-", value).strip("-")
    return normalized or fallback


def deterministic_id(prefix: str, *parts: Any, hint: str | None = None) -> str:
    digest = sha256_bytes(canonical_json_bytes(list(parts)))[:16]
    if hint:
        return f"{prefix}:{slug(hint)}:{digest}"
    return f"{prefix}:{digest}"


def sorted_unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def normalize_kind_for_comparison(value: Any) -> Any:
    return "action" if value in {"action", "github_action"} else value


def subject_tuple_from_report(report: dict[str, Any]) -> tuple[str, str, str, str]:
    subject = report.get("subject", {})
    boundary = report.get("analysis_boundary", {})
    values = (
        subject.get("repository"),
        boundary.get("subject_run_key"),
        subject.get("source_commit"),
        subject.get("release_candidate_id"),
    )
    if not all(isinstance(value, str) and value for value in values):
        raise BuilderError(f"compute_report_subject_incomplete: {values!r}")
    return values  # type: ignore[return-value]


def subject_tuple_from_packet(packet: dict[str, Any]) -> tuple[str, str, str, str]:
    subject = packet.get("subject", {})
    values = (
        subject.get("repository"),
        subject.get("subject_run_key"),
        subject.get("source_commit"),
        subject.get("release_candidate_id"),
    )
    if not all(isinstance(value, str) and value for value in values):
        raise BuilderError(f"runtime_packet_subject_incomplete: {values!r}")
    return values  # type: ignore[return-value]


def operation_digest(operation: dict[str, Any]) -> str:
    payload = {field: operation.get(field) for field in OPERATION_DIGEST_FIELDS}
    return sha256_bytes(canonical_json_bytes(payload))


def canonical_operation_ref(operation: dict[str, Any]) -> dict[str, Any]:
    action = operation.get("action")
    target_state = operation.get("target_state")
    if action not in {"create", "preserve"}:
        raise BuilderError(
            f"plan_operation_not_successful: {operation.get('component_id')}: {action!r}"
        )
    if action == "create" and target_state != "missing":
        raise BuilderError(
            f"plan_operation_create_target_state_invalid: {target_state!r}"
        )
    if action == "preserve" and target_state != "identical":
        raise BuilderError(
            f"plan_operation_preserve_target_state_invalid: {target_state!r}"
        )

    record = {
        "action": action,
        "component_id": operation.get("component_id"),
        "operation_canonicalization": "json-sort-keys-utf8-no-whitespace",
        "operation_digest_scope": "pulsemech_integration_plan_operation_v0",
        "operation_sha256": "",
        "reason": operation.get("reason"),
        "source_path": operation.get("source_path"),
        "source_sha256": operation.get("source_sha256"),
        "source_size_bytes": operation.get("source_size_bytes"),
        "target_path": operation.get("target_path"),
        "target_state": target_state,
    }
    record["operation_sha256"] = operation_digest(record)
    return record


def highest_mutation_authority(classes: Iterable[str]) -> str:
    values = [value for value in classes if value in MUTATION_AUTHORITY_RANK]
    if not values:
        return "none"
    return max(values, key=lambda value: MUTATION_AUTHORITY_RANK[value])


def derived_binding_class(
    *,
    execution_scope: str,
    declared_role: str,
    binding_status: str,
) -> str:
    if execution_scope in {"analysis_observer", "observation_collector"}:
        return "observer"
    if binding_status == "none":
        return "unbound"
    if binding_status != "complete":
        return "unknown"
    return ROLE_TO_BOUND_CLASS.get(declared_role, "unknown")


def combine_statuses(
    statuses: Iterable[str],
    *,
    empty: str = "not_required",
) -> str:
    values = [
        status
        for status in statuses
        if status in {"complete", "partial", "unknown"}
    ]
    if not values:
        return empty
    if all(status == "complete" for status in values):
        return "complete"
    if "unknown" in values:
        return "unknown"
    return "partial"


def incomplete_coverage_result(coverage: dict[str, Any]) -> str:
    statuses = {
        coverage.get(field)
        for field in (
            "identity_coverage_status",
            "execution_coverage_status",
            "declared_role_coverage_status",
            "authority_coverage_status",
            "downstream_consumption_coverage_status",
        )
    }
    return "unknown" if "unknown" in statuses else "partial"


# ---------------------------------------------------------------------------
# Integration-plan binding and expectation construction
# ---------------------------------------------------------------------------


def validate_plan_mechanics(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != "pulsemech_integration_plan_v0":
        raise BuilderError("integration_plan_schema_version_invalid")
    if plan.get("plan_type") != "pulsemech_integration_plan":
        raise BuilderError("integration_plan_type_invalid")
    if plan.get("apply_eligible") is not True:
        raise BuilderError("integration_plan_not_apply_eligible")
    if plan.get("conflicts") not in ([], None):
        raise BuilderError("integration_plan_contains_conflicts")
    if plan.get("unresolved") not in ([], None):
        raise BuilderError("integration_plan_contains_unresolved_conditions")

    operations = plan.get("operations")
    if not isinstance(operations, list):
        raise BuilderError("integration_plan_operations_not_array")
    for operation in operations:
        if not isinstance(operation, dict):
            raise BuilderError("integration_plan_operation_not_object")
        canonical_operation_ref(operation)

    summary = plan.get("summary", {})
    if isinstance(summary, dict):
        if summary.get("files_total") != len(operations):
            raise BuilderError("integration_plan_operation_count_mismatch")
        successful = sum(
            1 for operation in operations if operation.get("action") in {"create", "preserve"}
        )
        if successful != len(operations):
            raise BuilderError("integration_plan_contains_non_successful_operation")


def build_plan_binding(
    plan: dict[str, Any],
    *,
    plan_bytes: bytes,
    path_or_uri: str,
) -> dict[str, Any]:
    source = plan.get("source", {})
    target = plan.get("target", {})
    operations = plan.get("operations", [])
    required = {
        "source_repository": source.get("repository"),
        "source_revision": source.get("revision"),
        "component_manifest_sha256": source.get("component_manifest_sha256"),
        "policy_sha256": source.get("policy_sha256"),
        "target_repository_id": target.get("repository_id"),
        "target_default_branch": target.get("default_branch"),
        "declared_ci_provider": target.get("declared_ci_provider"),
    }
    if not all(isinstance(value, str) and value for value in required.values()):
        raise BuilderError(f"integration_plan_binding_incomplete: {required!r}")

    return {
        "apply_eligible": True,
        "component_manifest_sha256": required["component_manifest_sha256"],
        "declared_ci_provider": required["declared_ci_provider"],
        "operation_count": len(operations),
        "path_or_uri": path_or_uri,
        "plan_type": "pulsemech_integration_plan",
        "policy_sha256": required["policy_sha256"],
        "request_id": plan.get("request_id"),
        "schema_version": "pulsemech_integration_plan_v0",
        "sha256": sha256_bytes(plan_bytes),
        "source_repository": required["source_repository"],
        "source_revision": required["source_revision"],
        "target_default_branch": required["target_default_branch"],
        "target_repository_id": required["target_repository_id"],
    }


def build_operation_indexes(
    plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records = [canonical_operation_ref(operation) for operation in plan["operations"]]
    records.sort(
        key=lambda item: (
            str(item.get("component_id")),
            str(item.get("target_path")),
            str(item.get("operation_sha256")),
        )
    )
    by_digest: dict[str, dict[str, Any]] = {}
    for record in records:
        digest = record["operation_sha256"]
        if digest in by_digest:
            raise BuilderError(f"duplicate_plan_operation_digest: {digest}")
        by_digest[digest] = record
    return records, by_digest


def extract_expectations(document: dict[str, Any]) -> dict[str, Any]:
    if (
        document.get("schema_version") == RELATION_SCHEMA_VERSION
        and isinstance(document.get("expectations"), dict)
    ):
        return copy.deepcopy(document["expectations"])
    return copy.deepcopy(document)


def contains_example_only_identity(value: Any) -> bool:
    if isinstance(value, str):
        return value.startswith("example:")
    if isinstance(value, dict):
        return any(contains_example_only_identity(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_example_only_identity(item) for item in value)
    return False


def validate_explicit_expectations(
    expectations: dict[str, Any],
    *,
    operation_by_digest: dict[str, dict[str, Any]],
    subject: tuple[str, str, str, str],
    record_status: str,
) -> set[str]:
    referenced: set[str] = set()
    for expectation_id, expectation in expectations.items():
        if not isinstance(expectation, dict):
            raise BuilderError(f"expectation_not_object: {expectation_id}")
        if record_status == "observed" and contains_example_only_identity(
            expectation
        ):
            raise BuilderError(
                f"observed_expectation_contains_example_identity: {expectation_id}"
            )

        scope = expectation.get("expectation_scope", {})
        if scope.get("scope_kind") == "subject_run":
            observed = (
                subject[0],
                scope.get("subject_run_key"),
                scope.get("subject_source_commit"),
                scope.get("release_candidate_id"),
            )
            if observed != subject:
                raise BuilderError(
                    f"expectation_subject_binding_mismatch: {expectation_id}"
                )

        component_id = expectation.get("component_id")
        operation_refs = expectation.get("plan_operation_refs", [])
        for operation in operation_refs:
            if not isinstance(operation, dict):
                raise BuilderError(
                    f"expectation_operation_not_object: {expectation_id}"
                )
            digest = operation.get("operation_sha256")
            canonical = operation_by_digest.get(str(digest))
            if canonical is None:
                raise BuilderError(
                    f"expectation_operation_not_in_plan: {expectation_id}: {digest}"
                )
            if operation != canonical:
                raise BuilderError(
                    f"expectation_operation_identity_mismatch: {expectation_id}: {digest}"
                )
            if operation.get("component_id") != component_id:
                raise BuilderError(
                    f"expectation_component_operation_mismatch: {expectation_id}"
                )
            referenced.add(str(digest))

        basis_records = expectation.get("basis_records", [])
        integration_basis_digests = {
            basis.get("source_sha256")
            for basis in basis_records
            if isinstance(basis, dict)
            and basis.get("basis_kind") == "integration_plan_operation"
        }
        operation_digests = {
            operation.get("operation_sha256")
            for operation in operation_refs
            if isinstance(operation, dict)
        }
        if not integration_basis_digests.issubset(operation_digests):
            raise BuilderError(
                f"expectation_integration_basis_mismatch: {expectation_id}"
            )
    return referenced


def automatic_presence_expectation(
    operation: dict[str, Any],
    *,
    plan_path_or_uri: str,
    plan_source_revision: str,
) -> tuple[str, dict[str, Any]]:
    digest = str(operation["operation_sha256"])
    component_id = str(operation["component_id"])
    expectation_id = f"expectation:presence:{digest[:24]}"
    basis_id = f"basis:plan:{digest[:24]}"
    record = {
        "basis_records": [
            {
                "basis_id": basis_id,
                "basis_kind": "integration_plan_operation",
                "evidence_refs": sorted(
                    [f"plan-operation:{component_id}", f"sha256:{digest}"]
                ),
                "source_path_or_uri": f"{plan_path_or_uri}#operation/{digest}",
                "source_revision": plan_source_revision,
                "source_sha256": digest,
                "subject_run_key": None,
                "supports": ["component_presence", "source_identity"],
            }
        ],
        "component_id": component_id,
        "evidence_refs": sorted(
            [f"component:{component_id}", f"plan-operation-sha256:{digest}"]
        ),
        "expectation_kind": "planned_presence_only",
        "expectation_scope": {
            "release_candidate_id": None,
            "scope_kind": "repository_presence",
            "subject_run_key": None,
            "subject_source_commit": None,
        },
        "expected_compute": {
            "downstream_consumption_required": False,
            "execution_required": False,
            "selector": {
                "command_sha256": None,
                "job_name": None,
                "node_type": None,
                "step_name": None,
                "tool_id": None,
                "workflow_name": None,
            },
        },
        "expected_declared_role": None,
        "expected_mutation_authority": None,
        "expected_source_identity": {
            "action_commit_sha": None,
            "action_ref": None,
            "action_repository": None,
            "container_image_digest": None,
            "identity_status": "exact",
            "source_kind": "repository_file",
            "source_path_or_uri": operation["source_path"],
            "source_revision": plan_source_revision,
            "source_sha256": operation["source_sha256"],
        },
        "plan_operation_refs": [copy.deepcopy(operation)],
    }
    return expectation_id, record


def build_expectation_map(
    *,
    explicit: dict[str, Any],
    plan: dict[str, Any],
    plan_path_or_uri: str,
    operation_records: list[dict[str, Any]],
    operation_by_digest: dict[str, dict[str, Any]],
    subject: tuple[str, str, str, str],
    record_status: str,
) -> dict[str, Any]:
    expectations = copy.deepcopy(explicit)
    referenced = validate_explicit_expectations(
        expectations,
        operation_by_digest=operation_by_digest,
        subject=subject,
        record_status=record_status,
    )

    for operation in operation_records:
        digest = str(operation["operation_sha256"])
        if digest in referenced:
            continue
        expectation_id, record = automatic_presence_expectation(
            operation,
            plan_path_or_uri=plan_path_or_uri,
            plan_source_revision=str(plan["source"]["revision"]),
        )
        if expectation_id in expectations:
            raise BuilderError(
                f"automatic_expectation_id_collision: {expectation_id}"
            )
        expectations[expectation_id] = record

    for expectation in expectations.values():
        expectation["basis_records"] = sorted(
            expectation.get("basis_records", []),
            key=lambda item: str(item.get("basis_id")),
        )
        expectation["plan_operation_refs"] = sorted(
            expectation.get("plan_operation_refs", []),
            key=lambda item: (
                str(item.get("component_id")),
                str(item.get("target_path")),
                str(item.get("operation_sha256")),
            ),
        )
        expectation["evidence_refs"] = sorted_unique_strings(
            expectation.get("evidence_refs", [])
        )
        for basis in expectation["basis_records"]:
            basis["supports"] = sorted_unique_strings(basis.get("supports", []))
            basis["evidence_refs"] = sorted_unique_strings(
                basis.get("evidence_refs", [])
            )

    return dict(sorted(expectations.items()))


# ---------------------------------------------------------------------------
# Observation normalization
# ---------------------------------------------------------------------------


def empty_source_identity() -> dict[str, Any]:
    return {
        "action_commit_sha": None,
        "action_ref": None,
        "action_repository": None,
        "container_image_digest": None,
        "identity_status": "unknown",
        "source_kind": "unknown",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
    }


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _valid_sha40(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def normalize_report_source_identity(value: dict[str, Any]) -> dict[str, Any]:
    kind = value.get("source_kind")
    path = value.get("source_path_or_uri")
    revision = value.get("source_revision")
    digest = value.get("source_sha256")
    image_digest = value.get("container_image_digest")

    if kind not in {
        "repository_file",
        "action",
        "container_image",
        "external_service",
        "model",
        "builtin",
    }:
        return empty_source_identity()

    result = empty_source_identity()
    result.update(
        {
            "source_kind": kind,
            "source_path_or_uri": path if isinstance(path, str) and path else None,
            "source_revision": (
                revision if isinstance(revision, str) and revision else None
            ),
            "source_sha256": digest if _valid_sha256(digest) else None,
            "container_image_digest": (
                image_digest
                if isinstance(image_digest, str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest)
                else None
            ),
        }
    )

    exact = False
    if kind in {"repository_file", "action"}:
        exact = (
            isinstance(path, str)
            and bool(path)
            and isinstance(revision, str)
            and bool(revision)
            and _valid_sha256(digest)
        )
    elif kind in {"external_service", "model", "builtin"}:
        exact = isinstance(path, str) and bool(path) and _valid_sha256(digest)
    elif kind == "container_image":
        exact = (
            isinstance(path, str)
            and bool(path)
            and result["container_image_digest"] is not None
        )

    if exact:
        result["identity_status"] = "exact"
    elif any(
        result[field] is not None
        for field in (
            "source_path_or_uri",
            "source_revision",
            "source_sha256",
            "container_image_digest",
        )
    ):
        result["identity_status"] = "partial"
    else:
        return empty_source_identity()
    return result


def normalize_runtime_source_identity(value: dict[str, Any]) -> dict[str, Any]:
    result = empty_source_identity()
    kind = value.get("source_kind")
    status = value.get("identity_status")
    if kind not in {
        "repository_file",
        "github_action",
        "container_image",
        "external_service",
        "model",
        "builtin",
        "unknown",
    }:
        return result

    for field in result:
        if field in value:
            result[field] = value[field]
    result["source_kind"] = kind

    if status not in {"exact", "partial", "unknown"} or kind == "unknown":
        return empty_source_identity()

    meaningful_fields = (
        "source_path_or_uri",
        "source_revision",
        "source_sha256",
        "action_repository",
        "action_ref",
        "action_commit_sha",
        "container_image_digest",
    )
    any_identity = any(result.get(field) is not None for field in meaningful_fields)
    if not any_identity:
        return empty_source_identity()

    exact = False
    if kind == "repository_file":
        exact = (
            isinstance(result.get("source_path_or_uri"), str)
            and bool(result["source_path_or_uri"])
            and isinstance(result.get("source_revision"), str)
            and bool(result["source_revision"])
            and _valid_sha256(result.get("source_sha256"))
        )
    elif kind == "github_action":
        exact = (
            isinstance(result.get("action_repository"), str)
            and bool(result["action_repository"])
            and isinstance(result.get("action_ref"), str)
            and bool(result["action_ref"])
            and _valid_sha40(result.get("action_commit_sha"))
        )
    elif kind == "container_image":
        digest = result.get("container_image_digest")
        exact = (
            isinstance(result.get("source_path_or_uri"), str)
            and bool(result["source_path_or_uri"])
            and isinstance(digest, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None
        )
    elif kind in {"external_service", "model", "builtin"}:
        exact = (
            isinstance(result.get("source_path_or_uri"), str)
            and bool(result["source_path_or_uri"])
            and _valid_sha256(result.get("source_sha256"))
        )

    result["identity_status"] = "exact" if status == "exact" and exact else "partial"
    return result


def model_source_identity(model: dict[str, Any]) -> dict[str, Any]:
    model_id = model.get("model_id")
    revision = model.get("model_revision")
    digest = model.get("model_sha256")
    status = model.get("model_content_digest_status")

    result = empty_source_identity()
    if not isinstance(model_id, str) or not model_id:
        return result
    result.update(
        {
            "source_kind": "model",
            "source_path_or_uri": model_id,
            "source_revision": revision if isinstance(revision, str) and revision else None,
            "source_sha256": digest if _valid_sha256(digest) else None,
        }
    )
    if status == "exact_digest" and _valid_sha256(digest):
        result["identity_status"] = "exact"
    else:
        result["identity_status"] = "partial"
    return result


def external_service_source_identity(service: dict[str, Any]) -> dict[str, Any]:
    provider = service.get("provider")
    name = service.get("service_name")
    origin = service.get("endpoint_origin")
    operation = service.get("operation")
    api_version = service.get("api_version")

    parts = [part for part in (provider, name, operation) if isinstance(part, str) and part]
    path = origin if isinstance(origin, str) and origin else "/".join(parts)
    if not path:
        return empty_source_identity()

    result = empty_source_identity()
    result.update(
        {
            "identity_status": "partial",
            "source_kind": "external_service",
            "source_path_or_uri": path,
            "source_revision": (
                api_version if isinstance(api_version, str) and api_version else None
            ),
        }
    )
    return result


def source_identity_coverage(identity: dict[str, Any]) -> str:
    status = identity.get("identity_status")
    if status == "exact":
        return "complete"
    if status == "partial":
        return "partial"
    return "unknown"


def report_state_consumers(
    report: dict[str, Any],
) -> dict[str, tuple[list[str], list[str], list[str], bool]]:
    consumers: dict[str, set[str]] = defaultdict(set)
    edges: dict[str, set[str]] = defaultdict(set)
    evidence: dict[str, set[str]] = defaultdict(set)
    incomplete: dict[str, bool] = defaultdict(bool)

    for edge in report.get("edges", []):
        if not isinstance(edge, dict) or edge.get("observed") is not True:
            continue
        source = edge.get("from_id")
        target = edge.get("to_id")
        edge_id = edge.get("edge_id")
        if not (
            isinstance(source, str)
            and source.startswith("state:")
            and isinstance(target, str)
            and target.startswith("compute:")
        ):
            continue
        if edge.get("binding_status") == "complete":
            consumers[source].add(target)
            if isinstance(edge_id, str):
                edges[source].add(edge_id)
        else:
            incomplete[source] = True
        evidence[source].add(source)
        evidence[source].update(
            digest
            for digest in edge.get("evidence_digests", [])
            if isinstance(digest, str)
        )

    return {
        state_id: (
            sorted(consumers[state_id]),
            sorted(edges[state_id]),
            sorted(evidence[state_id]),
            bool(incomplete[state_id]),
        )
        for state_id in sorted(
            set(consumers) | set(edges) | set(evidence) | set(incomplete)
        )
    }


def downstream_for_states(
    output_state_ids: Iterable[str],
    *,
    consumer_index: dict[str, tuple[list[str], list[str], list[str], bool]],
    evidence_complete: bool,
) -> dict[str, Any]:
    states = sorted_unique_strings(output_state_ids)
    if not states:
        return {
            "consumer_ids": [],
            "edge_ids": [],
            "evidence_refs": [],
            "status": "not_applicable",
        }

    consumer_ids: set[str] = set()
    edge_ids: set[str] = set()
    evidence_refs: set[str] = set(states)
    incomplete_evidence = False
    for state_id in states:
        consumers, edges, evidence, incomplete = consumer_index.get(
            state_id, ([], [], [], False)
        )
        consumer_ids.update(consumers)
        edge_ids.update(edges)
        evidence_refs.update(evidence)
        incomplete_evidence = incomplete_evidence or incomplete

    if consumer_ids or edge_ids:
        status = "observed"
    elif incomplete_evidence:
        status = "unresolved"
    elif evidence_complete:
        status = "not_observed"
    else:
        status = "unresolved"

    return {
        "consumer_ids": sorted(consumer_ids),
        "edge_ids": sorted(edge_ids),
        "evidence_refs": sorted(evidence_refs),
        "status": status,
    }


def normalize_report_observations(
    report: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
) -> dict[str, Any]:
    consumer_index = report_state_consumers(report)
    workflow_name = report.get("subject", {}).get("workflow")
    observations: dict[str, Any] = {}

    for node in report.get("compute_nodes", []):
        if not isinstance(node, dict):
            raise BuilderError("compute_report_node_not_object")
        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not node_id.startswith("compute:"):
            raise BuilderError(f"compute_report_node_id_invalid: {node_id!r}")

        observation_id = deterministic_id(
            "observation",
            "compute_binding_report",
            node_id,
            hint=node_id.removeprefix("compute:"),
        )
        if observation_id in observations:
            raise BuilderError(f"observation_id_collision: {observation_id}")

        source = normalize_report_source_identity(node.get("source_identity", {}))
        binding_status = node.get("binding_status")
        if binding_status not in {"complete", "partial", "none", "unknown"}:
            binding_status = "unknown"
        execution_scope = node.get("execution_scope")
        if execution_scope not in {"subject", "analysis_observer", "observation_collector"}:
            execution_scope = "subject"
        declared_role = node.get("declared_role")
        if declared_role not in {
            "transition",
            "evidence",
            "preservation",
            "advisory",
            "observer",
            "unknown",
        }:
            declared_role = "unknown"
        mutation_authority = node.get("mutation_authority")
        if mutation_authority not in MUTATION_AUTHORITY_RANK:
            mutation_authority = "none"
        mutation_classes = sorted_unique_strings(node.get("observed_mutation_classes", []))
        binding_class = derived_binding_class(
            execution_scope=execution_scope,
            declared_role=declared_role,
            binding_status=binding_status,
        )
        coverage_status = (
            "complete"
            if binding_status in {"complete", "none"}
            else "partial"
            if binding_status == "partial"
            else "unknown"
        )

        run_binding = node.get("run_binding", {})
        execution_run_key = run_binding.get("execution_run_key")
        observed_run_key = (
            execution_run_key
            if isinstance(execution_run_key, str) and execution_run_key
            else subject[1]
        )
        output_states = sorted_unique_strings(node.get("output_state_ids", []))
        downstream = downstream_for_states(
            output_states,
            consumer_index=consumer_index,
            evidence_complete=coverage_status == "complete",
        )
        tool_id = source.get("source_path_or_uri")
        node_type = node.get("node_type")
        if not isinstance(node_type, str) or not node_type:
            node_type = "unknown"

        evidence_refs = {
            f"compute-binding-report-record:{node_id}",
            *sorted_unique_strings(node.get("input_state_ids", [])),
            *output_states,
            *downstream["edge_ids"],
        }
        observations[observation_id] = {
            "binding_class": binding_class,
            "binding_status": binding_status,
            "coverage_status": coverage_status,
            "declared_role": declared_role,
            "downstream_consumption": downstream,
            "evidence_refs": sorted(evidence_refs),
            "execution_identity": {
                "command_sha256": None,
                "job_name": None,
                "node_type": node_type,
                "step_name": None,
                "tool_id": tool_id if isinstance(tool_id, str) else None,
                "workflow_name": (
                    workflow_name if isinstance(workflow_name, str) else None
                ),
            },
            "execution_scope": execution_scope,
            "input_state_ids": sorted_unique_strings(node.get("input_state_ids", [])),
            "mutation_authority": mutation_authority,
            "observation_kind": "compute_node",
            "observed_mutation_classes": mutation_classes,
            "output_state_ids": output_states,
            "release_candidate_id": subject[3],
            "source_identity": source,
            "source_record_id": node_id,
            "source_record_kind": "compute_binding_report",
            "subject_run_key": observed_run_key,
            "subject_source_commit": subject[2],
            "unbound_authoritative_mutation": (
                binding_class == "unbound"
                and bool(set(mutation_classes) & AUTHORITATIVE_MUTATION_CLASSES)
            ),
        }

    return dict(sorted(observations.items()))


def packet_state_indexes(
    packet: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, tuple[list[str], list[str], list[str], bool]],
]:
    states: dict[str, dict[str, Any]] = {}
    for state in packet.get("state_observations", []):
        if not isinstance(state, dict):
            raise BuilderError("runtime_state_not_object")
        state_id = state.get("state_id")
        if not isinstance(state_id, str) or not state_id.startswith("state:"):
            raise BuilderError(f"runtime_state_id_invalid: {state_id!r}")
        if state_id in states:
            raise BuilderError(f"duplicate_runtime_state_id: {state_id}")
        states[state_id] = state

    consumers: dict[str, set[str]] = defaultdict(set)
    edge_ids: dict[str, set[str]] = defaultdict(set)
    evidence_refs: dict[str, set[str]] = defaultdict(set)

    def add_consumer(state_id: Any, consumer_id: str) -> None:
        if not isinstance(state_id, str) or not state_id.startswith("state:"):
            return
        consumers[state_id].add(consumer_id)
        edge_ids[state_id].add(
            deterministic_id(
                "edge",
                "runtime-state-consumption",
                state_id,
                consumer_id,
                hint="runtime-consumption",
            )
        )
        evidence_refs[state_id].add(state_id)

    for execution in packet.get("executions", []):
        execution_id = execution.get("execution_id")
        if not isinstance(execution_id, str):
            continue
        for state_id in execution.get("input_state_ids", []):
            add_consumer(state_id, execution_id)

    for call in packet.get("external_calls", []):
        call_id = call.get("call_id")
        if not isinstance(call_id, str):
            continue
        for state_id in call.get("request", {}).get("payload", {}).get("state_ids", []):
            add_consumer(state_id, call_id)

    for inference in packet.get("model_inferences", []):
        inference_id = inference.get("inference_id")
        if not isinstance(inference_id, str):
            continue
        for state_id in inference.get("request", {}).get("input_state_ids", []):
            add_consumer(state_id, inference_id)

    index = {
        state_id: (
            sorted(consumers[state_id]),
            sorted(edge_ids[state_id]),
            sorted(evidence_refs[state_id]),
            False,
        )
        for state_id in sorted(set(consumers) | set(edge_ids) | set(evidence_refs))
    }
    return states, index


def mutation_classes_for_states(
    state_ids: Iterable[str],
    states: dict[str, dict[str, Any]],
) -> list[str]:
    return sorted_unique_strings(
        states[state_id].get("mutation_class")
        for state_id in state_ids
        if state_id in states
        and states[state_id].get("mutation_class") not in {None, "none"}
    )


def runtime_parent_index(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for execution in packet.get("executions", []):
        execution_id = execution.get("execution_id")
        if isinstance(execution_id, str):
            result[execution_id] = execution
    return result


def runtime_binding_status(
    *,
    capture_status: Any,
    run_binding_complete: bool,
    source_identity: dict[str, Any],
) -> str:
    identity_status = source_identity.get("identity_status")
    if capture_status == "unknown" or identity_status == "unknown":
        return "unknown"
    if (
        capture_status != "complete"
        or not run_binding_complete
        or identity_status == "partial"
    ):
        return "partial"
    return "complete"


def runtime_execution_observation(
    execution: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
    states: dict[str, dict[str, Any]],
    consumers: dict[str, tuple[list[str], list[str], list[str], bool]],
) -> tuple[str, dict[str, Any]]:
    execution_id = execution.get("execution_id")
    if not isinstance(execution_id, str) or not execution_id.startswith("execution:"):
        raise BuilderError(f"runtime_execution_id_invalid: {execution_id!r}")

    source = normalize_runtime_source_identity(execution.get("source_identity", {}))
    run_binding = execution.get("run_binding", {})
    run_complete = run_binding.get("binding_complete") is True
    capture_status = execution.get("capture_status")
    binding_status = runtime_binding_status(
        capture_status=capture_status,
        run_binding_complete=run_complete,
        source_identity=source,
    )
    scope = execution.get("execution_scope")
    if scope not in {"subject", "analysis_observer", "observation_collector"}:
        scope = "subject"
    role = execution.get("declared_role")
    if role not in {
        "transition",
        "evidence",
        "preservation",
        "advisory",
        "observer",
        "unknown",
    }:
        role = "unknown"
    mutation_authority = execution.get("permitted_mutation_authority")
    if mutation_authority not in MUTATION_AUTHORITY_RANK:
        mutation_authority = "none"
    output_states = sorted_unique_strings(execution.get("output_state_ids", []))
    mutation_classes = mutation_classes_for_states(output_states, states)
    binding_class = derived_binding_class(
        execution_scope=scope,
        declared_role=role,
        binding_status=binding_status,
    )
    coverage_status = (
        "complete"
        if binding_status == "complete"
        else "partial"
        if binding_status == "partial"
        else "unknown"
    )
    downstream = downstream_for_states(
        output_states,
        consumer_index=consumers,
        evidence_complete=coverage_status == "complete",
    )
    command = execution.get("command_identity", {})
    execution_run_key = run_binding.get("execution_run_key")
    observed_run_key = (
        execution_run_key
        if isinstance(execution_run_key, str) and execution_run_key
        else subject[1]
    )
    tool_id = source.get("source_path_or_uri")
    observation_id = deterministic_id(
        "observation",
        "runtime_execution",
        execution_id,
        hint=execution_id.removeprefix("execution:"),
    )
    evidence = {
        f"runtime-execution:{execution_id}",
        *sorted_unique_strings(execution.get("input_state_ids", [])),
        *output_states,
        *downstream["edge_ids"],
    }
    return observation_id, {
        "binding_class": binding_class,
        "binding_status": binding_status,
        "coverage_status": coverage_status,
        "declared_role": role,
        "downstream_consumption": downstream,
        "evidence_refs": sorted(evidence),
        "execution_identity": {
            "command_sha256": (
                command.get("command_sha256")
                if _valid_sha256(command.get("command_sha256"))
                else None
            ),
            "job_name": execution.get("job_name"),
            "node_type": execution.get("execution_kind", "unknown"),
            "step_name": execution.get("step_name"),
            "tool_id": tool_id if isinstance(tool_id, str) else None,
            "workflow_name": execution.get("workflow_name"),
        },
        "execution_scope": scope,
        "input_state_ids": sorted_unique_strings(execution.get("input_state_ids", [])),
        "mutation_authority": mutation_authority,
        "observation_kind": "runtime_execution",
        "observed_mutation_classes": mutation_classes,
        "output_state_ids": output_states,
        "release_candidate_id": subject[3],
        "source_identity": source,
        "source_record_id": execution_id,
        "source_record_kind": "runtime_observation_packet",
        "subject_run_key": observed_run_key,
        "subject_source_commit": subject[2],
        "unbound_authoritative_mutation": (
            binding_class == "unbound"
            and bool(set(mutation_classes) & AUTHORITATIVE_MUTATION_CLASSES)
        ),
    }


def parent_execution_context(
    parent_id: Any,
    executions: dict[str, dict[str, Any]],
    *,
    subject: tuple[str, str, str, str],
) -> tuple[
    str,
    str,
    str,
    str,
    bool,
    str | None,
    str | None,
    str | None,
]:
    parent = executions.get(parent_id) if isinstance(parent_id, str) else None
    if parent is None:
        return (
            "subject",
            "unknown",
            "none",
            subject[1],
            False,
            None,
            None,
            None,
        )

    scope = parent.get("execution_scope")
    if scope not in {"subject", "analysis_observer", "observation_collector"}:
        scope = "subject"
    role = parent.get("declared_role")
    if role not in {
        "transition",
        "evidence",
        "preservation",
        "advisory",
        "observer",
        "unknown",
    }:
        role = "unknown"
    authority = parent.get("permitted_mutation_authority")
    if authority not in MUTATION_AUTHORITY_RANK:
        authority = "none"
    run_binding = parent.get("run_binding", {})
    run_key = run_binding.get("execution_run_key")
    if not isinstance(run_key, str) or not run_key:
        run_key = subject[1]
    run_binding_complete = run_binding.get("binding_complete") is True
    return (
        scope,
        role,
        authority,
        run_key,
        run_binding_complete,
        parent.get("workflow_name"),
        parent.get("job_name"),
        parent.get("step_name"),
    )


def external_call_observation(
    call: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
    executions: dict[str, dict[str, Any]],
    states: dict[str, dict[str, Any]],
    consumers: dict[str, tuple[list[str], list[str], list[str], bool]],
) -> tuple[str, dict[str, Any]]:
    call_id = call.get("call_id")
    if not isinstance(call_id, str) or not call_id.startswith("call:"):
        raise BuilderError(f"runtime_call_id_invalid: {call_id!r}")
    (
        scope,
        role,
        authority,
        run_key,
        run_binding_complete,
        workflow,
        job,
        step,
    ) = parent_execution_context(
        call.get("parent_execution_id"), executions, subject=subject
    )
    source = external_service_source_identity(call.get("service_identity", {}))
    capture = call.get("capture_status")
    binding_status = runtime_binding_status(
        capture_status=capture,
        run_binding_complete=run_binding_complete,
        source_identity=source,
    )
    request_states = sorted_unique_strings(
        call.get("request", {}).get("payload", {}).get("state_ids", [])
    )
    response_states = sorted_unique_strings(
        call.get("response", {}).get("payload", {}).get("state_ids", [])
    )
    mutation_classes = mutation_classes_for_states(response_states, states)
    binding_class = derived_binding_class(
        execution_scope=scope,
        declared_role=role,
        binding_status=binding_status,
    )
    coverage_status = (
        "complete"
        if binding_status == "complete"
        else "partial"
        if binding_status == "partial"
        else "unknown"
    )
    downstream = downstream_for_states(
        response_states,
        consumer_index=consumers,
        evidence_complete=coverage_status == "complete",
    )
    service = call.get("service_identity", {})
    service_name = "/".join(
        str(value)
        for value in (
            service.get("provider"),
            service.get("service_name"),
            service.get("operation"),
        )
        if isinstance(value, str) and value
    ) or None
    observation_id = deterministic_id(
        "observation",
        "external_call",
        call_id,
        hint=call_id.removeprefix("call:"),
    )
    evidence = {
        f"runtime-external-call:{call_id}",
        *request_states,
        *response_states,
        *downstream["edge_ids"],
    }
    return observation_id, {
        "binding_class": binding_class,
        "binding_status": binding_status,
        "coverage_status": coverage_status,
        "declared_role": role,
        "downstream_consumption": downstream,
        "evidence_refs": sorted(evidence),
        "execution_identity": {
            "command_sha256": None,
            "job_name": job,
            "node_type": "external_service_call",
            "step_name": step,
            "tool_id": service_name,
            "workflow_name": workflow,
        },
        "execution_scope": scope,
        "input_state_ids": request_states,
        "mutation_authority": authority,
        "observation_kind": "external_call",
        "observed_mutation_classes": mutation_classes,
        "output_state_ids": response_states,
        "release_candidate_id": subject[3],
        "source_identity": source,
        "source_record_id": call_id,
        "source_record_kind": "runtime_observation_packet",
        "subject_run_key": run_key,
        "subject_source_commit": subject[2],
        "unbound_authoritative_mutation": (
            binding_class == "unbound"
            and bool(set(mutation_classes) & AUTHORITATIVE_MUTATION_CLASSES)
        ),
    }


def model_inference_observation(
    inference: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
    executions: dict[str, dict[str, Any]],
    states: dict[str, dict[str, Any]],
    consumers: dict[str, tuple[list[str], list[str], list[str], bool]],
) -> tuple[str, dict[str, Any]]:
    inference_id = inference.get("inference_id")
    if not isinstance(inference_id, str) or not inference_id.startswith("inference:"):
        raise BuilderError(f"runtime_inference_id_invalid: {inference_id!r}")
    (
        scope,
        role,
        authority,
        run_key,
        run_binding_complete,
        workflow,
        job,
        step,
    ) = parent_execution_context(
        inference.get("parent_execution_id"), executions, subject=subject
    )
    source = model_source_identity(inference.get("model_identity", {}))
    capture = inference.get("capture_status")
    binding_status = runtime_binding_status(
        capture_status=capture,
        run_binding_complete=run_binding_complete,
        source_identity=source,
    )
    input_states = sorted_unique_strings(
        inference.get("request", {}).get("input_state_ids", [])
    )
    output_states = sorted_unique_strings(
        inference.get("response", {}).get("output_state_ids", [])
    )
    mutation_classes = mutation_classes_for_states(output_states, states)
    binding_class = derived_binding_class(
        execution_scope=scope,
        declared_role=role,
        binding_status=binding_status,
    )
    coverage_status = (
        "complete"
        if binding_status == "complete"
        else "partial"
        if binding_status == "partial"
        else "unknown"
    )
    downstream = downstream_for_states(
        output_states,
        consumer_index=consumers,
        evidence_complete=coverage_status == "complete",
    )
    model_id = inference.get("model_identity", {}).get("model_id")
    observation_id = deterministic_id(
        "observation",
        "model_inference",
        inference_id,
        hint=inference_id.removeprefix("inference:"),
    )
    evidence = {
        f"runtime-model-inference:{inference_id}",
        *input_states,
        *output_states,
        *downstream["edge_ids"],
    }
    return observation_id, {
        "binding_class": binding_class,
        "binding_status": binding_status,
        "coverage_status": coverage_status,
        "declared_role": role,
        "downstream_consumption": downstream,
        "evidence_refs": sorted(evidence),
        "execution_identity": {
            "command_sha256": None,
            "job_name": job,
            "node_type": "model_inference",
            "step_name": step,
            "tool_id": model_id if isinstance(model_id, str) else None,
            "workflow_name": workflow,
        },
        "execution_scope": scope,
        "input_state_ids": input_states,
        "mutation_authority": authority,
        "observation_kind": "model_inference",
        "observed_mutation_classes": mutation_classes,
        "output_state_ids": output_states,
        "release_candidate_id": subject[3],
        "source_identity": source,
        "source_record_id": inference_id,
        "source_record_kind": "runtime_observation_packet",
        "subject_run_key": run_key,
        "subject_source_commit": subject[2],
        "unbound_authoritative_mutation": (
            binding_class == "unbound"
            and bool(set(mutation_classes) & AUTHORITATIVE_MUTATION_CLASSES)
        ),
    }


def normalize_runtime_packet_observations(
    packet: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
) -> dict[str, Any]:
    states, consumers = packet_state_indexes(packet)
    executions = runtime_parent_index(packet)
    observations: dict[str, Any] = {}

    for execution in packet.get("executions", []):
        observation_id, record = runtime_execution_observation(
            execution,
            subject=subject,
            states=states,
            consumers=consumers,
        )
        if observation_id in observations:
            raise BuilderError(f"observation_id_collision: {observation_id}")
        observations[observation_id] = record

    for call in packet.get("external_calls", []):
        observation_id, record = external_call_observation(
            call,
            subject=subject,
            executions=executions,
            states=states,
            consumers=consumers,
        )
        if observation_id in observations:
            raise BuilderError(f"observation_id_collision: {observation_id}")
        observations[observation_id] = record

    for inference in packet.get("model_inferences", []):
        observation_id, record = model_inference_observation(
            inference,
            subject=subject,
            executions=executions,
            states=states,
            consumers=consumers,
        )
        if observation_id in observations:
            raise BuilderError(f"observation_id_collision: {observation_id}")
        observations[observation_id] = record

    return dict(sorted(observations.items()))


def runtime_packet_binding(
    packet: dict[str, Any],
    *,
    packet_bytes: bytes,
    path_or_uri: str,
) -> dict[str, Any]:
    subject = subject_tuple_from_packet(packet)
    identity = packet.get("packet_identity", {})
    return {
        "ok": True,
        "packet_id": identity.get("packet_id"),
        "packet_scope": identity.get("packet_scope"),
        "packet_sequence": identity.get("packet_sequence"),
        "packet_type": packet.get("packet_type"),
        "path_or_uri": path_or_uri,
        "record_status": packet.get("record_status"),
        "release_candidate_id": subject[3],
        "schema_version": packet.get("schema_version"),
        "sha256": sha256_bytes(packet_bytes),
        "subject_repository": subject[0],
        "subject_run_key": subject[1],
        "subject_source_commit": subject[2],
    }


def verify_runtime_packet_chain(
    packets: list[tuple[dict[str, Any], bytes, str]],
    *,
    subject: tuple[str, str, str, str],
    record_status: str,
) -> tuple[list[tuple[dict[str, Any], bytes, str]], bool]:
    ordered = sorted(
        packets,
        key=lambda item: (
            item[0].get("packet_identity", {}).get("packet_sequence", -1),
            str(item[0].get("packet_identity", {}).get("packet_id")),
            sha256_bytes(item[1]),
        ),
    )
    ids: set[str] = set()
    sequences: set[int] = set()
    previous_sequence: int | None = None
    previous_digest: str | None = None
    chain_complete = not ordered or (
        ordered[0][0].get("packet_identity", {}).get("packet_sequence") == 0
    )

    for packet, raw, _display in ordered:
        if subject_tuple_from_packet(packet) != subject:
            raise BuilderError("runtime_packet_subject_binding_mismatch")
        if packet.get("record_status") != record_status:
            raise BuilderError("runtime_packet_record_status_mismatch")

        identity = packet.get("packet_identity", {})
        packet_id = identity.get("packet_id")
        sequence = identity.get("packet_sequence")
        predecessor = identity.get("previous_packet_sha256")

        if not isinstance(packet_id, str) or packet_id in ids:
            raise BuilderError(
                f"runtime_packet_id_duplicate_or_invalid: {packet_id!r}"
            )
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
            raise BuilderError(f"runtime_packet_sequence_invalid: {sequence!r}")
        if sequence in sequences:
            raise BuilderError(f"runtime_packet_sequence_duplicate: {sequence}")

        if sequence == 0:
            if predecessor is not None:
                raise BuilderError("runtime_packet_root_predecessor_not_null")
        elif not _valid_sha256(predecessor):
            raise BuilderError(
                f"runtime_packet_predecessor_invalid: sequence={sequence}"
            )

        if previous_sequence is not None:
            if sequence == previous_sequence + 1:
                if predecessor != previous_digest:
                    raise BuilderError(
                        f"runtime_packet_predecessor_mismatch: sequence={sequence}"
                    )
            else:
                chain_complete = False

        ids.add(packet_id)
        sequences.add(sequence)
        previous_sequence = sequence
        previous_digest = sha256_bytes(raw)

    return ordered, chain_complete


# ---------------------------------------------------------------------------
# Input bindings, cross-input consistency, and coverage derivation
# ---------------------------------------------------------------------------


def compute_report_binding(
    report: dict[str, Any],
    *,
    report_bytes: bytes,
    path_or_uri: str,
) -> dict[str, Any]:
    subject = subject_tuple_from_report(report)
    analysis_level = report.get("analysis_boundary", {}).get("analysis_level")
    if analysis_level not in {"artifact_observed", "runtime_observed"}:
        raise BuilderError(f"compute_report_analysis_level_invalid: {analysis_level!r}")
    if report.get("ok") is not True:
        raise BuilderError("compute_report_not_ok")
    return {
        "analysis_level": analysis_level,
        "ok": True,
        "path_or_uri": path_or_uri,
        "record_status": report.get("record_status"),
        "release_candidate_id": subject[3],
        "report_type": report.get("report_type"),
        "schema_version": report.get("schema_version"),
        "sha256": sha256_bytes(report_bytes),
        "subject_repository": subject[0],
        "subject_run_key": subject[1],
        "subject_source_commit": subject[2],
    }


def runtime_observation_status(
    packets: list[tuple[dict[str, Any], bytes, str]],
    *,
    chain_complete: bool,
) -> str:
    if not packets:
        return "none"
    statuses = [
        packet.get("coverage", {}).get("coverage_status")
        for packet, _, _ in packets
    ]
    return (
        "complete"
        if chain_complete
        and statuses
        and all(status == "complete" for status in statuses)
        else "partial"
    )


def validate_cross_input_bindings(
    *,
    plan_binding: dict[str, Any],
    report: dict[str, Any],
    packets: list[tuple[dict[str, Any], bytes, str]],
) -> tuple[tuple[str, str, str, str], str, str]:
    subject = subject_tuple_from_report(report)
    if plan_binding.get("target_repository_id") != subject[0]:
        raise BuilderError("plan_target_subject_repository_mismatch")

    record_status = report.get("record_status")
    if record_status not in {"example", "observed"}:
        raise BuilderError(f"compute_report_record_status_invalid: {record_status!r}")

    analysis_level = report.get("analysis_boundary", {}).get("analysis_level")
    if analysis_level == "artifact_observed" and packets:
        raise BuilderError(
            "artifact_observed_report_cannot_bind_runtime_packets"
        )
    if analysis_level == "runtime_observed" and not packets:
        raise BuilderError("runtime_observed_report_requires_runtime_packet")

    for packet, _, _ in packets:
        if packet.get("observation_boundary", {}).get("target_analysis_level") != "runtime_observed":
            raise BuilderError("runtime_packet_target_analysis_level_invalid")
        if packet.get("ok") is not True:
            raise BuilderError("runtime_packet_not_ok")

    return subject, str(record_status), str(analysis_level)


def derive_axis_coverage(
    observations: dict[str, Any],
    *,
    report: dict[str, Any],
    packets: list[tuple[dict[str, Any], bytes, str]],
    execution_required: bool,
    runtime_status: str,
    analysis_level: str,
) -> dict[str, str]:
    values = list(observations.values())
    if not values:
        identity_status = "not_required"
        role_status = "not_required"
        authority_status = "not_required"
        downstream_status = "not_required"
        execution_status = "unknown" if execution_required else "not_required"
    else:
        identity_values = [
            source_identity_coverage(observation.get("source_identity", {}))
            for observation in values
        ]
        identity_status = combine_statuses(identity_values)

        roles = [observation.get("declared_role") for observation in values]
        role_status = "unknown" if "unknown" in roles else "complete"

        authority_status = "complete"

        downstream_values: list[str] = []
        for observation in values:
            status = observation.get("downstream_consumption", {}).get("status")
            coverage = observation.get("coverage_status")
            if status == "unresolved":
                downstream_values.append(
                    "unknown" if coverage == "unknown" else "partial"
                )
            else:
                downstream_values.append("complete")
        downstream_status = combine_statuses(downstream_values)

        observation_coverage = [
            observation.get("coverage_status") for observation in values
        ]
        execution_status = combine_statuses(observation_coverage, empty="unknown")

    report_nodes = report.get("compute_nodes", [])
    if report_nodes:
        report_binding_statuses = [
            node.get("binding_status")
            for node in report_nodes
            if isinstance(node, dict)
        ]
        if "unknown" in report_binding_statuses:
            execution_status = "unknown"
        elif "partial" in report_binding_statuses and execution_status != "unknown":
            execution_status = "partial"

    for packet, _, _ in packets:
        packet_status = packet.get("coverage", {}).get("coverage_status")
        if packet_status == "unknown":
            execution_status = "unknown"
        elif packet_status == "partial" and execution_status != "unknown":
            execution_status = "partial"

    if analysis_level == "runtime_observed" and runtime_status != "complete":
        if execution_status != "unknown":
            execution_status = "partial"

    return {
        "authority_coverage_status": authority_status,
        "declared_role_coverage_status": role_status,
        "downstream_consumption_coverage_status": downstream_status,
        "execution_coverage_status": execution_status,
        "identity_coverage_status": identity_status,
    }


def unresolved_reasons_from_axes(
    axes: dict[str, str],
    *,
    analysis_level: str,
    observations: dict[str, Any],
) -> list[str]:
    reasons: set[str] = set()
    if axes["identity_coverage_status"] in {"partial", "unknown"}:
        reasons.add("source_identity_unavailable")
    if axes["execution_coverage_status"] in {"partial", "unknown"}:
        reasons.add(
            "runtime_coverage_partial"
            if analysis_level == "runtime_observed"
            else "artifact_coverage_partial"
        )
    if axes["declared_role_coverage_status"] in {"partial", "unknown"}:
        reasons.add("declared_role_unavailable")
    if axes["authority_coverage_status"] in {"partial", "unknown"}:
        reasons.add("authority_class_unavailable")
    if axes["downstream_consumption_coverage_status"] in {"partial", "unknown"}:
        reasons.add("downstream_consumption_unavailable")
    if observations and all(
        observation.get("execution_scope") in {"analysis_observer", "observation_collector"}
        for observation in observations.values()
    ):
        reasons.add("observer_only_record")
    return sorted(reasons)


# ---------------------------------------------------------------------------
# Deterministic matching and relation evaluation
# ---------------------------------------------------------------------------


def selector_fields(selector: dict[str, Any]) -> dict[str, Any]:
    return {
        field: selector.get(field)
        for field in (
            "node_type",
            "workflow_name",
            "job_name",
            "step_name",
            "tool_id",
            "command_sha256",
        )
        if selector.get(field) is not None
    }


def source_anchor_match(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    expected_kind = normalize_kind_for_comparison(expected.get("source_kind"))
    observed_kind = normalize_kind_for_comparison(observed.get("source_kind"))
    if expected_kind != observed_kind:
        return False

    if expected_kind == "action":
        expected_values = {
            value
            for value in (
                expected.get("source_path_or_uri"),
                expected.get("action_repository"),
            )
            if isinstance(value, str) and value
        }
        observed_values = {
            value
            for value in (
                observed.get("source_path_or_uri"),
                observed.get("action_repository"),
            )
            if isinstance(value, str) and value
        }
        if expected_values & observed_values:
            return True

    anchors = ("source_path_or_uri", "container_image_digest")
    present = [field for field in anchors if expected.get(field) is not None]
    return bool(present) and any(
        observed.get(field) == expected.get(field) for field in present
    )


def candidate_score(
    expectation: dict[str, Any],
    observation: dict[str, Any],
) -> int | None:
    selector = selector_fields(expectation.get("expected_compute", {}).get("selector", {}))
    expected_source = expectation.get("expected_source_identity", {})
    actual_identity = observation.get("execution_identity", {})
    observed_source = observation.get("source_identity", {})

    expected_role = expectation.get("expected_declared_role")
    expected_authority = expectation.get("expected_mutation_authority")
    if observation.get("execution_scope") in {"analysis_observer", "observation_collector"}:
        if expected_role != "observer" and selector.get("node_type") != "observer_execution":
            return None

    score = 0
    strong_anchor = False

    if source_anchor_match(expected_source, observed_source):
        score += 120
        strong_anchor = True

    expected_digest = expected_source.get("source_sha256")
    observed_digest = observed_source.get("source_sha256")
    if expected_digest is not None and observed_digest is not None:
        score += 35 if expected_digest == observed_digest else 5

    expected_action_commit = expected_source.get("action_commit_sha")
    if expected_action_commit is not None:
        if observed_source.get("action_commit_sha") == expected_action_commit:
            score += 35
            strong_anchor = True

    weights = {
        "tool_id": 90,
        "step_name": 55,
        "job_name": 35,
        "workflow_name": 25,
        "command_sha256": 70,
        "node_type": 15,
    }
    for field, expected_value in selector.items():
        actual_value = actual_identity.get(field)
        if actual_value == expected_value:
            score += weights[field]
            if field != "node_type":
                strong_anchor = True
        elif actual_value is not None:
            score -= max(5, weights[field] // 3)

    if expected_role is not None and observation.get("declared_role") == expected_role:
        score += 8
    if (
        expected_authority is not None
        and observation.get("mutation_authority") == expected_authority
    ):
        score += 8

    if not strong_anchor:
        return None
    return score


def observation_anchor_labels(
    expectation: dict[str, Any],
    observation: dict[str, Any],
) -> set[str]:
    labels: set[str] = set()
    expected_source = expectation.get("expected_source_identity", {})
    observed_source = observation.get("source_identity", {})
    selector = selector_fields(
        expectation.get("expected_compute", {}).get("selector", {})
    )
    actual = observation.get("execution_identity", {})

    expected_kind = normalize_kind_for_comparison(
        expected_source.get("source_kind")
    )
    observed_kind = normalize_kind_for_comparison(
        observed_source.get("source_kind")
    )
    if expected_kind == observed_kind:
        if expected_kind == "action":
            expected_values = {
                value
                for value in (
                    expected_source.get("source_path_or_uri"),
                    expected_source.get("action_repository"),
                )
                if isinstance(value, str) and value
            }
            observed_values = {
                value
                for value in (
                    observed_source.get("source_path_or_uri"),
                    observed_source.get("action_repository"),
                )
                if isinstance(value, str) and value
            }
            if expected_values & observed_values:
                labels.add("source_surface")
        else:
            for field in ("source_path_or_uri", "container_image_digest"):
                expected_value = expected_source.get(field)
                if (
                    expected_value is not None
                    and observed_source.get(field) == expected_value
                ):
                    labels.add("source_surface")

    for field in (
        "tool_id",
        "step_name",
        "job_name",
        "command_sha256",
    ):
        expected_value = selector.get(field)
        if expected_value is not None and actual.get(field) == expected_value:
            labels.add(field)

    if (
        selector.get("workflow_name") is not None
        and actual.get("workflow_name") == selector.get("workflow_name")
        and (
            selector.get("job_name") is not None
            or selector.get("node_type") == "workflow_job"
        )
    ):
        labels.add("workflow_name")

    return labels


def observations_can_share_relation(
    expectation: dict[str, Any],
    observations: list[dict[str, Any]],
) -> bool:
    if len(observations) <= 1:
        return True

    source_record_kinds = [
        observation.get("source_record_kind") for observation in observations
    ]
    if set(source_record_kinds) != {
        "compute_binding_report",
        "runtime_observation_packet",
    }:
        return False
    if source_record_kinds.count("compute_binding_report") != 1:
        return False
    if source_record_kinds.count("runtime_observation_packet") != 1:
        return False

    anchor_sets = [
        observation_anchor_labels(expectation, observation)
        for observation in observations
    ]
    if any(not anchors for anchors in anchor_sets):
        return False
    if not set.intersection(*anchor_sets):
        return False

    return True


def select_candidate_observations(
    expectation: dict[str, Any],
    observations: dict[str, Any],
    available_ids: set[str],
) -> tuple[list[str], bool]:
    scored_by_source: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for observation_id in sorted(available_ids):
        score = candidate_score(expectation, observations[observation_id])
        if score is None:
            continue
        source_kind = str(
            observations[observation_id].get("source_record_kind")
        )
        scored_by_source[source_kind].append((score, observation_id))

    if not scored_by_source:
        return [], False

    selected: list[str] = []
    ambiguous = False
    for source_kind in sorted(scored_by_source):
        scored = scored_by_source[source_kind]
        best = max(score for score, _ in scored)
        winners = sorted(
            observation_id
            for score, observation_id in scored
            if score == best
        )
        selected.extend(winners)
        if len(winners) > 1:
            ambiguous = True

    selected = sorted(selected)
    if not ambiguous and len(selected) > 1:
        records = [observations[observation_id] for observation_id in selected]
        ambiguous = not observations_can_share_relation(
            expectation,
            records,
        )
    return selected, ambiguous


def source_identity_result(
    expected: dict[str, Any],
    observations: list[dict[str, Any]],
) -> str:
    if expected.get("identity_status") == "unknown":
        return "unavailable"
    if not observations:
        return "not_required"

    comparable = (
        "source_path_or_uri",
        "source_revision",
        "source_sha256",
        "action_repository",
        "action_ref",
        "action_commit_sha",
        "container_image_digest",
    )
    results: list[str] = []
    for observation in observations:
        observed = observation.get("source_identity", {})
        if normalize_kind_for_comparison(
            expected.get("source_kind")
        ) != normalize_kind_for_comparison(observed.get("source_kind")):
            results.append("mismatch")
            continue
        mismatch = False
        unavailable = False
        for field in comparable:
            expected_value = expected.get(field)
            if expected_value is None:
                continue
            actual_value = observed.get(field)
            if actual_value is None:
                unavailable = True
            elif actual_value != expected_value:
                mismatch = True
        if mismatch:
            results.append("mismatch")
        elif unavailable:
            results.append("unavailable")
        else:
            results.append("match")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def selector_result(
    selector: dict[str, Any],
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"
    expected = selector_fields(selector)
    if not expected:
        return "not_required"

    results: list[str] = []
    for observation in observations:
        actual = observation.get("execution_identity", {})
        mismatch = False
        unavailable = False
        for field, expected_value in expected.items():
            actual_value = actual.get(field)
            if actual_value is None:
                unavailable = True
            elif actual_value != expected_value:
                mismatch = True
        if mismatch:
            results.append("mismatch")
        elif unavailable:
            results.append("unavailable")
        else:
            results.append("match")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def run_binding_result(
    expected_subject: tuple[Any, Any, Any, Any],
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"
    expected = expected_subject[1:]
    return (
        "match"
        if all(
            (
                observation.get("subject_run_key"),
                observation.get("subject_source_commit"),
                observation.get("release_candidate_id"),
            )
            == expected
            for observation in observations
        )
        else "mismatch"
    )


def field_match_result(
    expected: Any,
    observations: list[dict[str, Any]],
    field: str,
) -> str:
    if expected is None or not observations:
        return "not_required"

    results: list[str] = []
    for observation in observations:
        actual = observation.get(field)
        if actual in {None, "unknown"}:
            results.append("unavailable")
        elif actual == expected:
            results.append("match")
        else:
            results.append("mismatch")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def downstream_result(
    required: bool,
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"
    statuses = {
        observation.get("downstream_consumption", {}).get("status")
        for observation in observations
    }
    if "observed" in statuses:
        return "observed"
    if not required:
        return "not_required"
    if "unresolved" in statuses:
        return "unresolved"
    return "not_observed"


def relation_coverage_result(
    observations: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> str:
    if not observations:
        status = coverage.get("execution_coverage_status")
        if status == "complete":
            return "complete"
        if status == "unknown":
            return "unknown"
        return "partial"
    statuses = {observation.get("coverage_status") for observation in observations}
    if statuses == {"complete"}:
        return "complete"
    if "unknown" in statuses:
        return "unknown"
    return "partial"


def full_relation_evaluation(
    expectation: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    comparison_subject: tuple[str, str, str, str],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    kind = expectation.get("expectation_kind")
    if kind == "planned_presence_only":
        return {
            "authority_class": "not_required",
            "coverage": "complete",
            "decisive": True,
            "declared_role": "not_required",
            "downstream_consumption": "not_required",
            "execution_identity": "not_required",
            "execution_observation": "not_required",
            "run_binding": "not_required",
            "source_identity": "not_required",
        }

    if not observations:
        if coverage.get("execution_coverage_status") == "complete":
            return {
                "authority_class": "not_required",
                "coverage": "complete",
                "decisive": True,
                "declared_role": "not_required",
                "downstream_consumption": "not_required",
                "execution_identity": "not_required",
                "execution_observation": "not_observed",
                "run_binding": "not_required",
                "source_identity": "not_required",
            }
        incomplete = incomplete_coverage_result(coverage)
        return {
            "authority_class": "unavailable",
            "coverage": incomplete,
            "decisive": False,
            "declared_role": "unavailable",
            "downstream_consumption": "unresolved",
            "execution_identity": "unavailable",
            "execution_observation": "unresolved",
            "run_binding": "unavailable",
            "source_identity": "unavailable",
        }

    scope = expectation.get("expectation_scope", {})
    expected_subject: tuple[Any, Any, Any, Any]
    if scope.get("scope_kind") == "subject_run":
        expected_subject = (
            comparison_subject[0],
            scope.get("subject_run_key"),
            scope.get("subject_source_commit"),
            scope.get("release_candidate_id"),
        )
    else:
        expected_subject = comparison_subject

    expected_compute = expectation.get("expected_compute", {})
    coverage_result = relation_coverage_result(observations, coverage)
    result: dict[str, Any] = {
        "authority_class": field_match_result(
            expectation.get("expected_mutation_authority"),
            observations,
            "mutation_authority",
        ),
        "coverage": coverage_result,
        "declared_role": field_match_result(
            expectation.get("expected_declared_role"),
            observations,
            "declared_role",
        ),
        "downstream_consumption": downstream_result(
            bool(expected_compute.get("downstream_consumption_required")),
            observations,
        ),
        "execution_identity": selector_result(
            expected_compute.get("selector", {}), observations
        ),
        "execution_observation": "observed",
        "run_binding": run_binding_result(expected_subject, observations),
        "source_identity": source_identity_result(
            expectation.get("expected_source_identity", {}), observations
        ),
    }
    result["decisive"] = (
        coverage_result == "complete"
        and result["execution_identity"] != "unavailable"
        and result["source_identity"] != "unavailable"
        and result["run_binding"] != "unavailable"
        and result["declared_role"] != "unavailable"
        and result["authority_class"] != "unavailable"
        and result["downstream_consumption"] != "unresolved"
    )
    return result


def ambiguous_evaluation(
    observations: list[dict[str, Any]],
    *,
    coverage: dict[str, Any],
) -> dict[str, Any]:
    coverage_result = relation_coverage_result(observations, coverage)
    return {
        "authority_class": "unavailable",
        "coverage": coverage_result,
        "decisive": False,
        "declared_role": "unavailable",
        "downstream_consumption": "unresolved",
        "execution_identity": "unavailable",
        "execution_observation": "unresolved",
        "run_binding": "unavailable",
        "source_identity": "unavailable",
    }


def relation_status_from_evaluation(
    evaluation: dict[str, Any],
    *,
    downstream_required: bool,
) -> str:
    if evaluation.get("execution_observation") == "unresolved":
        return "unresolved_due_to_coverage"
    if evaluation.get("execution_observation") == "not_observed":
        return "planned_but_not_observed"
    if (
        evaluation.get("coverage") != "complete"
        or evaluation.get("decisive") is not True
        or "unavailable" in evaluation.values()
        or evaluation.get("downstream_consumption") == "unresolved"
    ):
        return "unresolved_due_to_coverage"
    if evaluation.get("run_binding") == "mismatch":
        return "run_binding_mismatch"
    if evaluation.get("execution_identity") == "mismatch":
        return "execution_identity_mismatch"
    if evaluation.get("source_identity") == "mismatch":
        return "source_digest_mismatch"
    if evaluation.get("declared_role") == "mismatch":
        return "declared_role_mismatch"
    if evaluation.get("authority_class") == "mismatch":
        return "authority_class_mismatch"
    if downstream_required and evaluation.get("downstream_consumption") == "not_observed":
        return "downstream_consumption_missing"
    return "planned_and_observed"


def relation_id_for_expectation(expectation_id: str) -> str:
    return deterministic_id(
        "relation",
        "expectation",
        expectation_id,
        hint=expectation_id.removeprefix("expectation:"),
    )


def relation_for_expectation(
    expectation_id: str,
    expectation: dict[str, Any],
    *,
    selected_ids: list[str],
    ambiguous: bool,
    observations: dict[str, Any],
    subject: tuple[str, str, str, str],
    coverage: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    relation_id = relation_id_for_expectation(expectation_id)
    selected = [observations[observation_id] for observation_id in selected_ids]
    kind = expectation.get("expectation_kind")

    if kind == "planned_presence_only":
        selected_ids = []
        selected = []
        evaluation = full_relation_evaluation(
            expectation,
            [],
            comparison_subject=subject,
            coverage=coverage,
        )
        status = "planned_presence_only"
        notes = ["Repository presence does not create a subject-run execution expectation."]
    elif ambiguous:
        evaluation = ambiguous_evaluation(selected, coverage=coverage)
        status = "ambiguous_observation_match"
        notes = ["More than one incompatible observation matches the planned execution expectation."]
    else:
        evaluation = full_relation_evaluation(
            expectation,
            selected,
            comparison_subject=subject,
            coverage=coverage,
        )
        status = relation_status_from_evaluation(
            evaluation,
            downstream_required=bool(
                expectation.get("expected_compute", {}).get(
                    "downstream_consumption_required"
                )
            ),
        )
        if status == "unresolved_due_to_coverage":
            incomplete = incomplete_coverage_result(coverage)
            evaluation = {
                "authority_class": "unavailable",
                "coverage": incomplete,
                "decisive": False,
                "declared_role": "unavailable",
                "downstream_consumption": "unresolved",
                "execution_identity": "unavailable",
                "execution_observation": "unresolved",
                "run_binding": "unavailable",
                "source_identity": "unavailable",
            }
        notes = [
            {
                "planned_and_observed": "The planned execution is observed with matching bound mechanics.",
                "planned_but_not_observed": "The planned execution is not observed under complete execution coverage.",
                "execution_identity_mismatch": "An observation is present but its execution identity differs from the expectation.",
                "source_digest_mismatch": "An observation is present at the expected source surface with a different source identity or digest.",
                "run_binding_mismatch": "An observation is present but is bound to a different run, revision, or release candidate.",
                "declared_role_mismatch": "An observation is present with a different declared role.",
                "authority_class_mismatch": "An observation is present with a different mutation-authority class.",
                "downstream_consumption_missing": "Execution is observed but required downstream consumption is not observed.",
                "unresolved_due_to_coverage": "The relation cannot be decided because relevant observation coverage is incomplete.",
            }.get(status, "The relation was classified deterministically."),
        ]

    evidence = set(expectation.get("evidence_refs", []))
    evidence.add(expectation_id)
    for observation_id in selected_ids:
        evidence.add(observation_id)
        evidence.update(observations[observation_id].get("evidence_refs", []))

    return relation_id, {
        "evaluation": evaluation,
        "evidence_refs": sorted_unique_strings(evidence),
        "expectation_id": expectation_id,
        "notes": sorted_unique_strings(notes),
        "observation_ids": sorted(selected_ids),
        "relation_status": status,
    }


def relation_for_unplanned_observation(
    observation_id: str,
    observation: dict[str, Any],
    *,
    subject: tuple[str, str, str, str],
    coverage: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    selected = [observation]
    run_result = run_binding_result(subject, selected)
    coverage_result = relation_coverage_result(selected, coverage)
    decisive = coverage_result == "complete" and run_result == "match"

    if decisive:
        status = "observed_but_not_planned"
        evaluation = {
            "authority_class": "not_required",
            "coverage": coverage_result,
            "decisive": True,
            "declared_role": "not_required",
            "downstream_consumption": "not_required",
            "execution_identity": "not_required",
            "execution_observation": "observed",
            "run_binding": "match",
            "source_identity": "not_required",
        }
        note = "The observed execution has no explicit planned execution expectation."
    else:
        status = "unresolved_due_to_coverage"
        evaluation = {
            "authority_class": "unavailable",
            "coverage": incomplete_coverage_result(coverage),
            "decisive": False,
            "declared_role": "unavailable",
            "downstream_consumption": "unresolved",
            "execution_identity": "unavailable",
            "execution_observation": "unresolved",
            "run_binding": "unavailable",
            "source_identity": "unavailable",
        }
        note = "The unplanned observation cannot be classified decisively under the available coverage."

    relation_id = deterministic_id(
        "relation",
        "unplanned-observation",
        observation_id,
        hint="unplanned",
    )
    return relation_id, {
        "evaluation": evaluation,
        "evidence_refs": sorted_unique_strings(
            [observation_id, *observation.get("evidence_refs", [])]
        ),
        "expectation_id": None,
        "notes": [note],
        "observation_ids": [observation_id],
        "relation_status": status,
    }


def build_relations(
    *,
    expectations: dict[str, Any],
    observations: dict[str, Any],
    subject: tuple[str, str, str, str],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    relations: dict[str, Any] = {}
    all_observation_ids = set(observations)
    selections: dict[str, tuple[list[str], bool]] = {}
    observation_owners: dict[str, list[str]] = defaultdict(list)

    for expectation_id, expectation in expectations.items():
        if expectation.get("expectation_kind") == "planned_presence_only":
            selection = ([], False)
        else:
            selection = select_candidate_observations(
                expectation, observations, all_observation_ids
            )
        selections[expectation_id] = selection
        for observation_id in selection[0]:
            observation_owners[observation_id].append(expectation_id)

    overlaps = {
        observation_id: sorted(owner_ids)
        for observation_id, owner_ids in observation_owners.items()
        if len(owner_ids) > 1
    }
    if overlaps:
        detail = "; ".join(
            f"{observation_id}=>{','.join(owner_ids)}"
            for observation_id, owner_ids in sorted(overlaps.items())
        )
        raise BuilderError(
            f"overlapping_expectation_observation_candidates: {detail}"
        )

    consumed: set[str] = set()
    for expectation_id, expectation in expectations.items():
        selected_ids, ambiguous = selections[expectation_id]
        relation_id, record = relation_for_expectation(
            expectation_id,
            expectation,
            selected_ids=selected_ids,
            ambiguous=ambiguous,
            observations=observations,
            subject=subject,
            coverage=coverage,
        )
        if relation_id in relations:
            raise BuilderError(f"relation_id_collision: {relation_id}")
        relations[relation_id] = record
        consumed.update(selected_ids)

    for observation_id in sorted(all_observation_ids - consumed):
        relation_id, record = relation_for_unplanned_observation(
            observation_id,
            observations[observation_id],
            subject=subject,
            coverage=coverage,
        )
        if relation_id in relations:
            raise BuilderError(f"relation_id_collision: {relation_id}")
        relations[relation_id] = record

    return dict(sorted(relations.items()))


# ---------------------------------------------------------------------------
# Findings, coverage, summary, and final relation record
# ---------------------------------------------------------------------------


def finding_id_for(
    finding_type: str,
    *,
    expectation_id: str | None,
    relation_id: str | None,
    observation_ids: Iterable[str],
) -> str:
    return deterministic_id(
        "finding",
        finding_type,
        expectation_id,
        relation_id,
        sorted(observation_ids),
        hint=finding_type,
    )


def build_findings(
    *,
    relations: dict[str, Any],
    observations: dict[str, Any],
) -> dict[str, Any]:
    findings: dict[str, Any] = {}
    authority_observations_covered: set[str] = set()

    for relation_id, relation in relations.items():
        status = relation.get("relation_status")
        observation_ids = relation.get("observation_ids", [])
        expectation_id = relation.get("expectation_id")
        if status in {"planned_presence_only", "planned_and_observed"}:
            continue

        finding_type = FINDING_TYPE_BY_RELATION_STATUS.get(str(status))
        if finding_type is None:
            continue

        selected = [
            observations[observation_id]
            for observation_id in observation_ids
            if observation_id in observations
        ]
        flagged = [
            observation_id
            for observation_id in observation_ids
            if observations.get(observation_id, {}).get(
                "unbound_authoritative_mutation"
            )
            is True
        ]
        if flagged or status == "authority_class_mismatch":
            severity = "authority_integrity_candidate"
            authority_observations_covered.update(flagged)
        elif status == "observed_but_not_planned" and selected and all(
            observation.get("execution_scope")
            in {"analysis_observer", "observation_collector"}
            for observation in selected
        ):
            severity = "information"
        else:
            severity = "advisory"

        message = {
            "planned_but_not_observed": "A subject-run execution expectation is not observed under complete execution coverage.",
            "observed_but_not_planned": "An observed execution has no explicit planned execution expectation.",
            "execution_identity_mismatch": "Observed execution identity differs from the planned selector.",
            "source_digest_mismatch": "Observed source identity or digest differs from the planned source.",
            "run_binding_mismatch": "Observed compute is bound to a different run, revision, or release candidate.",
            "declared_role_mismatch": "Observed declared role differs from the planned role.",
            "authority_class_mismatch": "Observed mutation authority differs from the planned authority class.",
            "downstream_consumption_missing": "Required downstream consumption is not observed.",
            "ambiguous_observation_match": "Multiple incompatible observations match one planned execution expectation.",
            "unresolved_due_to_coverage": "The relation remains unresolved because relevant observation coverage is incomplete.",
        }.get(str(status), "A planned-observed relation finding was recorded.")

        evidence = set(relation.get("evidence_refs", []))
        finding_id = finding_id_for(
            finding_type,
            expectation_id=expectation_id,
            relation_id=relation_id,
            observation_ids=observation_ids,
        )
        findings[finding_id] = {
            "evidence_refs": sorted_unique_strings(evidence),
            "expectation_id": expectation_id,
            "finding_type": finding_type,
            "message": message,
            "observation_ids": sorted_unique_strings(observation_ids),
            "relation_id": relation_id,
            "severity": severity,
        }

    for observation_id, observation in observations.items():
        if observation.get("unbound_authoritative_mutation") is not True:
            continue
        if observation_id in authority_observations_covered:
            continue

        containing_relation_id: str | None = None
        expectation_id: str | None = None
        for relation_id, relation in relations.items():
            if observation_id in relation.get("observation_ids", []):
                containing_relation_id = relation_id
                expectation_id = relation.get("expectation_id")
                break

        finding_type = "authority_class_mismatch"
        finding_id = finding_id_for(
            finding_type,
            expectation_id=expectation_id,
            relation_id=containing_relation_id,
            observation_ids=[observation_id],
        )
        findings[finding_id] = {
            "evidence_refs": sorted_unique_strings(
                [observation_id, *observation.get("evidence_refs", [])]
            ),
            "expectation_id": expectation_id,
            "finding_type": finding_type,
            "message": "An unbound observation records an authority-bearing mutation.",
            "observation_ids": [observation_id],
            "relation_id": containing_relation_id,
            "severity": "authority_integrity_candidate",
        }

    fingerprints: set[tuple[Any, ...]] = set()
    for finding in findings.values():
        fingerprint = (
            finding.get("finding_type"),
            finding.get("severity"),
            finding.get("expectation_id"),
            finding.get("relation_id"),
            tuple(finding.get("observation_ids", [])),
        )
        if fingerprint in fingerprints:
            raise BuilderError(f"duplicate_finding_fingerprint: {fingerprint!r}")
        fingerprints.add(fingerprint)

    return dict(sorted(findings.items()))


def build_coverage(
    *,
    plan_binding: dict[str, Any],
    expectations: dict[str, Any],
    observations: dict[str, Any],
    relations: dict[str, Any],
    axes: dict[str, str],
    runtime_status: str,
    analysis_level: str,
) -> dict[str, Any]:
    referenced_operations = {
        operation.get("operation_sha256")
        for expectation in expectations.values()
        for operation in expectation.get("plan_operation_refs", [])
        if isinstance(operation, dict)
        and isinstance(operation.get("operation_sha256"), str)
    }
    total_operations = int(plan_binding["operation_count"])
    missing_count = total_operations - len(referenced_operations)
    if missing_count < 0:
        raise BuilderError("referenced_plan_operation_count_exceeds_plan")
    missing_refs = [
        f"unreferenced-plan-operation:{index + 1}"
        for index in range(missing_count)
    ]

    classified_expectations = {
        relation.get("expectation_id")
        for relation in relations.values()
        if relation.get("expectation_id") in expectations
    }
    classified_observations = {
        observation_id
        for relation in relations.values()
        for observation_id in relation.get("observation_ids", [])
        if observation_id in observations
    }
    unclassified_expectations = sorted(set(expectations) - classified_expectations)
    unclassified_observations = sorted(set(observations) - classified_observations)

    unresolved_reasons = set(
        unresolved_reasons_from_axes(
            axes,
            analysis_level=analysis_level,
            observations=observations,
        )
    )
    relation_statuses = {
        relation.get("relation_status") for relation in relations.values()
    }
    if "ambiguous_observation_match" in relation_statuses:
        unresolved_reasons.add("ambiguous_match")
    if analysis_level == "runtime_observed" and runtime_status != "complete":
        unresolved_reasons.add("runtime_coverage_partial")
    if "unresolved_due_to_coverage" in relation_statuses and not unresolved_reasons:
        unresolved_reasons.add(
            "runtime_coverage_partial"
            if analysis_level == "runtime_observed"
            else "artifact_coverage_partial"
        )

    all_axes_complete = all(
        axes[field] in {"complete", "not_required"}
        for field in (
            "identity_coverage_status",
            "execution_coverage_status",
            "declared_role_coverage_status",
            "authority_coverage_status",
            "downstream_consumption_coverage_status",
        )
    )
    all_relations_decisive = all(
        relation.get("evaluation", {}).get("decisive") is True
        for relation in relations.values()
    )
    complete = (
        not missing_refs
        and not unclassified_expectations
        and not unclassified_observations
        and not unresolved_reasons
        and all_axes_complete
        and all_relations_decisive
        and (
            analysis_level != "runtime_observed"
            or runtime_status == "complete"
        )
        and "ambiguous_observation_match" not in relation_statuses
        and "unresolved_due_to_coverage" not in relation_statuses
    )
    if complete:
        comparison_status = "complete"
    elif "unknown" in axes.values():
        comparison_status = "unknown"
    else:
        comparison_status = "partial"

    return {
        "authority_coverage_status": axes["authority_coverage_status"],
        "comparison_status": comparison_status,
        "declared_role_coverage_status": axes["declared_role_coverage_status"],
        "downstream_consumption_coverage_status": axes[
            "downstream_consumption_coverage_status"
        ],
        "execution_coverage_status": axes["execution_coverage_status"],
        "expectations_classified": len(classified_expectations),
        "expectations_total": len(expectations),
        "identity_coverage_status": axes["identity_coverage_status"],
        "missing_plan_operation_refs": missing_refs,
        "observations_classified": len(classified_observations),
        "observations_total": len(observations),
        "plan_operations_referenced": len(referenced_operations),
        "plan_operations_total": total_operations,
        "relations_total": len(relations),
        "runtime_observation_status": runtime_status,
        "unclassified_expectation_ids": unclassified_expectations,
        "unclassified_observation_ids": unclassified_observations,
        "unresolved_reasons": sorted(unresolved_reasons),
    }


def build_summary(
    *,
    plan_binding: dict[str, Any],
    expectations: dict[str, Any],
    observations: dict[str, Any],
    relations: dict[str, Any],
    findings: dict[str, Any],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    expectation_counts = Counter(
        expectation.get("expectation_kind") for expectation in expectations.values()
    )
    relation_counts = Counter(
        relation.get("relation_status") for relation in relations.values()
    )
    decisive = sum(
        relation.get("evaluation", {}).get("decisive") is True
        for relation in relations.values()
    )
    unresolved = len(relations) - decisive
    authority_findings = sum(
        finding.get("severity") == "authority_integrity_candidate"
        for finding in findings.values()
    )
    comparison_complete = (
        coverage.get("comparison_status") == "complete"
        and unresolved == 0
        and relation_counts.get("ambiguous_observation_match", 0) == 0
        and relation_counts.get("unresolved_due_to_coverage", 0) == 0
    )

    summary: dict[str, Any] = {
        "authority_integrity_candidate_count": authority_findings,
        "comparison_complete": comparison_complete,
        "decisive_relations": decisive,
        "expectations": len(expectations),
        "observations": len(observations),
        "plan_operations": int(plan_binding["operation_count"]),
        "relations": len(relations),
        "unresolved_relations": unresolved,
    }
    for kind in EXPECTATION_KINDS:
        summary[kind] = expectation_counts.get(kind, 0)
    for status in RELATION_STATUSES:
        summary[status] = relation_counts.get(status, 0)
    return summary


def default_relation_record_id(
    *,
    subject: tuple[str, str, str, str],
    plan_sha256: str,
    report_sha256: str,
    packet_sha256s: list[str],
) -> str:
    return deterministic_id(
        "planned-observed",
        subject,
        plan_sha256,
        report_sha256,
        packet_sha256s,
        hint=subject[1],
    )


def merge_observation_maps(
    target: dict[str, Any],
    incoming: dict[str, Any],
) -> None:
    for observation_id, observation in incoming.items():
        existing = target.get(observation_id)
        if existing is None:
            target[observation_id] = observation
        elif existing != observation:
            raise BuilderError(f"observation_identity_conflict: {observation_id}")


def build_relation_record(
    *,
    plan: dict[str, Any],
    plan_bytes: bytes,
    plan_path_or_uri: str,
    report: dict[str, Any],
    report_bytes: bytes,
    report_path_or_uri: str,
    packets: list[tuple[dict[str, Any], bytes, str]],
    explicit_expectations: dict[str, Any],
    relation_id: str | None,
    tool_source_revision: str | None,
) -> dict[str, Any]:
    validate_plan_mechanics(plan)
    plan_binding = build_plan_binding(
        plan,
        plan_bytes=plan_bytes,
        path_or_uri=plan_path_or_uri,
    )
    ordered_packets, packet_chain_complete = verify_runtime_packet_chain(
        packets,
        subject=subject_tuple_from_report(report),
        record_status=str(report.get("record_status")),
    )
    subject, record_status, analysis_level = validate_cross_input_bindings(
        plan_binding=plan_binding,
        report=report,
        packets=ordered_packets,
    )

    operation_records, operation_by_digest = build_operation_indexes(plan)
    expectations = build_expectation_map(
        explicit=explicit_expectations,
        plan=plan,
        plan_path_or_uri=plan_path_or_uri,
        operation_records=operation_records,
        operation_by_digest=operation_by_digest,
        subject=subject,
        record_status=record_status,
    )

    observations: dict[str, Any] = {}
    merge_observation_maps(
        observations,
        normalize_report_observations(report, subject=subject),
    )
    for packet, _packet_bytes, _display in ordered_packets:
        merge_observation_maps(
            observations,
            normalize_runtime_packet_observations(packet, subject=subject),
        )
    observations = dict(sorted(observations.items()))

    runtime_status = runtime_observation_status(
        ordered_packets,
        chain_complete=packet_chain_complete,
    )
    execution_required = any(
        expectation.get("expected_compute", {}).get("execution_required") is True
        for expectation in expectations.values()
    )
    axes = derive_axis_coverage(
        observations,
        report=report,
        packets=ordered_packets,
        execution_required=execution_required,
        runtime_status=runtime_status,
        analysis_level=analysis_level,
    )
    if any(
        (
            observation.get("subject_run_key"),
            observation.get("subject_source_commit"),
            observation.get("release_candidate_id"),
        )
        != subject[1:]
        for observation in observations.values()
    ):
        axes["execution_coverage_status"] = (
            "unknown"
            if axes["execution_coverage_status"] == "unknown"
            else "partial"
        )

    preliminary_coverage = {
        **axes,
        "runtime_observation_status": runtime_status,
    }
    relations = build_relations(
        expectations=expectations,
        observations=observations,
        subject=subject,
        coverage=preliminary_coverage,
    )
    if (
        any(
            relation.get("relation_status") == "unresolved_due_to_coverage"
            for relation in relations.values()
        )
        and all(
            axes[field] in {"complete", "not_required"}
            for field in (
                "identity_coverage_status",
                "execution_coverage_status",
                "declared_role_coverage_status",
                "authority_coverage_status",
                "downstream_consumption_coverage_status",
            )
        )
    ):
        axes["identity_coverage_status"] = "unknown"
        preliminary_coverage = {
            **axes,
            "runtime_observation_status": runtime_status,
        }
        relations = build_relations(
            expectations=expectations,
            observations=observations,
            subject=subject,
            coverage=preliminary_coverage,
        )
    coverage = build_coverage(
        plan_binding=plan_binding,
        expectations=expectations,
        observations=observations,
        relations=relations,
        axes=axes,
        runtime_status=runtime_status,
        analysis_level=analysis_level,
    )
    findings = build_findings(relations=relations, observations=observations)
    summary = build_summary(
        plan_binding=plan_binding,
        expectations=expectations,
        observations=observations,
        relations=relations,
        findings=findings,
        coverage=coverage,
    )

    report_binding = compute_report_binding(
        report,
        report_bytes=report_bytes,
        path_or_uri=report_path_or_uri,
    )
    packet_bindings = [
        runtime_packet_binding(
            packet,
            packet_bytes=packet_bytes,
            path_or_uri=display,
        )
        for packet, packet_bytes, display in ordered_packets
    ]
    packet_bindings.sort(
        key=lambda item: (
            item["packet_sequence"],
            item["packet_id"],
            item["sha256"],
        )
    )

    relation_record_id = relation_id or default_relation_record_id(
        subject=subject,
        plan_sha256=plan_binding["sha256"],
        report_sha256=report_binding["sha256"],
        packet_sha256s=[binding["sha256"] for binding in packet_bindings],
    )
    if re.fullmatch(r"planned-observed:[A-Za-z0-9._:/@+-]+", relation_record_id) is None:
        raise BuilderError(f"relation_id_invalid: {relation_record_id!r}")

    return {
        "authority_boundary": {
            "activates_compute_gate": False,
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "changes_release_authority": False,
            "creates_compute_budget": False,
            "creates_gate_result": False,
            "creates_release_decision": False,
            "mutates_subject_run": False,
            "relation_record_is_release_authority": False,
            "write_mode": "relation_only",
            "writes_target_repository": False,
        },
        "comparison_boundary": {
            "comparison_writes_subject": False,
            "execution_implies_downstream_consumption": False,
            "expectation_basis_required_for_execution": True,
            "observed_analysis_level": analysis_level,
            "observer_in_subject_totals": False,
            "plan_target_matches_subject_repository": True,
            "presence_implies_execution": False,
        },
        "comparison_identity": {
            "canonicalization": "json-sort-keys-utf8-newline",
            "comparison_scope": "example" if record_status == "example" else "subject_run",
            "relation_record_id": relation_record_id,
            "release_candidate_id": subject[3],
            "subject_repository": subject[0],
            "subject_run_key": subject[1],
            "subject_source_commit": subject[2],
        },
        "coverage": coverage,
        "errors": [],
        "expectations": expectations,
        "findings": findings,
        "observation_bindings": {
            "compute_binding_report": report_binding,
            "runtime_observation_packets": packet_bindings,
            "runtime_observation_status": runtime_status,
        },
        "observations": observations,
        "ok": True,
        "plan_binding": plan_binding,
        "record_status": record_status,
        "relation_type": RELATION_TYPE,
        "relations": relations,
        "schema_version": RELATION_SCHEMA_VERSION,
        "summary": summary,
        "tool": {
            "id": TOOL_ID,
            "source_revision": tool_source_revision,
            "source_sha256": sha256_file(Path(__file__)),
            "version": TOOL_VERSION,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic, read-only PULSEmech compute "
            "planned-observed relation record v0."
        )
    )
    parser.add_argument("--plan", required=True)
    parser.add_argument("--compute-report", required=True)
    parser.add_argument(
        "--expectations",
        help=(
            "Optional ID-keyed expectation map. A complete planned-observed "
            "relation record is also accepted; only its expectations map is "
            "read. Successful plan operations not referenced by explicit "
            "expectations become presence-only expectations."
        ),
    )
    parser.add_argument(
        "--runtime-packet",
        action="append",
        default=[],
        help="Optional runtime-observation packet. Repeat for a packet chain.",
    )
    parser.add_argument("--relation-id")
    parser.add_argument("--tool-source-revision")
    parser.add_argument("--plan-schema", default=str(DEFAULT_PLAN_SCHEMA))
    parser.add_argument("--report-schema", default=str(DEFAULT_REPORT_SCHEMA))
    parser.add_argument("--runtime-packet-schema", default=str(DEFAULT_PACKET_SCHEMA))
    parser.add_argument("--relation-schema", default=str(DEFAULT_RELATION_SCHEMA))
    parser.add_argument("--report-validator", default=str(DEFAULT_REPORT_VALIDATOR))
    parser.add_argument("--runtime-packet-validator", default=str(DEFAULT_PACKET_VALIDATOR))
    parser.add_argument("--relation-validator", default=str(DEFAULT_RELATION_VALIDATOR))
    parser.add_argument(
        "--subject-root",
        help=(
            "Local subject-repository root. Required when --output is used; "
            "output inside this tree is refused."
        ),
    )
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan)
    report_path = Path(args.compute_report)
    expectations_path = Path(args.expectations) if args.expectations else None
    packet_paths = [Path(value) for value in args.runtime_packet]
    plan_schema_path = Path(args.plan_schema)
    report_schema_path = Path(args.report_schema)
    packet_schema_path = Path(args.runtime_packet_schema)
    relation_schema_path = Path(args.relation_schema)
    report_validator_path = Path(args.report_validator)
    packet_validator_path = Path(args.runtime_packet_validator)
    relation_validator_path = Path(args.relation_validator)
    subject_root = Path(args.subject_root) if args.subject_root else None
    output_path = Path(args.output) if args.output else None

    protected_paths: list[Path] = [
        plan_path,
        report_path,
        *packet_paths,
        plan_schema_path,
        report_schema_path,
        packet_schema_path,
        relation_schema_path,
        report_validator_path,
        packet_validator_path,
        relation_validator_path,
        Path(__file__),
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    ]
    if expectations_path is not None:
        protected_paths.append(expectations_path)

    try:
        reject_unsafe_output(
            output_path,
            protected_paths=protected_paths,
            subject_root=subject_root,
        )
        protected_snapshots = snapshot_regular_files(protected_paths)

        schemas: dict[str, dict[str, Any]] = {}
        for label, path in (
            ("plan", plan_schema_path),
            ("report", report_schema_path),
            ("runtime_packet", packet_schema_path),
            ("relation", relation_schema_path),
        ):
            schema, _ = load_json_document(path, label=f"{label}_schema")
            validate_schema_document(schema, label=label)
            schemas[label] = schema

        plan, plan_bytes = load_json_document(plan_path, label="plan")
        report, report_bytes = load_json_document(report_path, label="compute_report")
        validate_document(schema=schemas["plan"], value=plan, label="plan")
        validate_document(schema=schemas["report"], value=report, label="compute_report")

        invoke_json_validator(
            validator_path=report_validator_path,
            schema_path=report_schema_path,
            document_path=report_path,
            document_flag="--report",
            label="compute_report",
        )

        packet_documents: list[tuple[dict[str, Any], bytes, str]] = []
        for packet_path in packet_paths:
            packet, raw = load_json_document(packet_path, label="runtime_packet")
            validate_document(
                schema=schemas["runtime_packet"],
                value=packet,
                label="runtime_packet",
            )
            invoke_json_validator(
                validator_path=packet_validator_path,
                schema_path=packet_schema_path,
                document_path=packet_path,
                document_flag="--packet",
                label="runtime_packet",
            )
            packet_documents.append((packet, raw, packet_path.as_posix()))

        if expectations_path is None:
            explicit_expectations: dict[str, Any] = {}
        else:
            expectations_document, _ = load_json_document(
                expectations_path,
                label="expectations",
            )
            explicit_expectations = extract_expectations(expectations_document)

        expectation_schema = expectations_input_schema(schemas["relation"])
        validate_schema_document(expectation_schema, label="expectations")
        validate_document(
            schema=expectation_schema,
            value=explicit_expectations,
            label="expectations",
        )

        record_status = report.get("record_status")
        tool_source_revision = resolve_tool_source_revision(
            args.tool_source_revision,
            record_status=str(record_status),
        )
        relation = build_relation_record(
            plan=plan,
            plan_bytes=plan_bytes,
            plan_path_or_uri=plan_path.as_posix(),
            report=report,
            report_bytes=report_bytes,
            report_path_or_uri=report_path.as_posix(),
            packets=packet_documents,
            explicit_expectations=explicit_expectations,
            relation_id=args.relation_id,
            tool_source_revision=tool_source_revision,
        )

        validate_document(
            schema=schemas["relation"],
            value=relation,
            label="generated_relation",
        )

        rendered = render_json(relation)
        with tempfile.TemporaryDirectory(
            prefix="pulsemech-planned-observed-builder-v0-"
        ) as temporary_directory:
            relation_path = Path(temporary_directory) / "relation.json"
            relation_path.write_text(rendered, encoding="utf-8")
            invoke_json_validator(
                validator_path=relation_validator_path,
                schema_path=relation_schema_path,
                document_path=relation_path,
                document_flag="--relation",
                label="generated_relation",
            )

        verify_regular_file_snapshots(protected_snapshots)
        if output_path is not None:
            atomic_write_text(output_path, rendered)
        sys.stdout.write(rendered)
        return 0

    except BuilderError as exc:
        diagnostic = {
            "errors": [str(exc)],
            "ok": False,
            "relation_type": RELATION_TYPE,
            "schema_version": RELATION_SCHEMA_VERSION,
            "tool": TOOL_ID,
        }
        sys.stderr.write(render_json(diagnostic))
        return 2
    except Exception as exc:
        diagnostic = {
            "errors": [f"unexpected_builder_error: {type(exc).__name__}: {exc}"],
            "ok": False,
            "relation_type": RELATION_TYPE,
            "schema_version": RELATION_SCHEMA_VERSION,
            "tool": TOOL_ID,
        }
        sys.stderr.write(render_json(diagnostic))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
