#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence


TOOL_NAME = "fold_pulsemech_compute_planned_observed_relation_into_status_v0"
TOOL_VERSION = "0.1.0"
RELATION_SCHEMA_VERSION = "pulsemech_compute_planned_observed_relation_v0"
RELATION_TYPE = "pulsemech_compute_planned_observed_relation"
CANDIDATE_GATE_SET = "compute_planned_observed_relation_candidate"

CANDIDATE_GATES = (
    "compute_transition_path_complete",
    "compute_transition_authority_binding_ok",
    "compute_transition_unbound_mutation_absent",
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
DEFAULT_RELATION_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

PATH_FAILURE_STATUSES = {
    "planned_but_not_observed",
    "observed_but_not_planned",
    "execution_identity_mismatch",
    "downstream_consumption_missing",
    "ambiguous_observation_match",
    "unresolved_due_to_coverage",
}

PATH_FAILURE_FINDINGS = {
    "plan_target_subject_mismatch",
    "plan_operation_unreferenced",
    "execution_expectation_basis_missing",
    "downstream_expectation_basis_missing",
    "planned_execution_not_observed",
    "observed_execution_not_planned",
    "execution_identity_mismatch",
    "downstream_consumption_missing",
    "ambiguous_observation_match",
    "observation_identity_unresolved",
    "comparison_coverage_partial",
    "observer_boundary_violation",
    "duplicate_relation_candidate",
    "invalid_relation_classification",
}

AUTHORITY_FAILURE_STATUSES = {
    "source_digest_mismatch",
    "run_binding_mismatch",
    "declared_role_mismatch",
    "authority_class_mismatch",
}

AUTHORITY_FAILURE_FINDINGS = {
    "source_digest_mismatch",
    "run_binding_mismatch",
    "declared_role_mismatch",
    "authority_class_mismatch",
    "observation_identity_unresolved",
}

BOUND_AUTHORITY_CLASSES = {
    "transition_bound",
    "evidence_bound",
    "preservation_bound",
    "advisory_bound",
}

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

FORBIDDEN_OUTPUT_NAMES = {
    "status.json",
    "release_decision_v0.json",
    "pulsemech_compute_planned_observed_relation_v0.json",
}


class MaterializerError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Strict parsing, deterministic rendering, and file-boundary guards
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
        raise MaterializerError(f"{label}_is_symlink: {path}")
    if not path.is_file():
        raise MaterializerError(f"{label}_not_regular_file: {path}")


def load_json_document(path: Path, *, label: str) -> tuple[Any, bytes]:
    require_regular_non_symlink(path, label=label)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise MaterializerError(f"{label}_read_failed: {path}: {exc}") from exc

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise MaterializerError(f"{label}_json_invalid: {path}: {exc}") from exc
    return value, raw


def parse_json_text(text: str, *, label: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise MaterializerError(f"{label}_json_invalid: {exc}") from exc


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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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


def reject_symlink_chain(path: Path) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise MaterializerError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def reject_unsafe_output(
    output: Path,
    *,
    protected_paths: Sequence[Path],
) -> None:
    for protected in protected_paths:
        if same_target(output, protected):
            raise MaterializerError(f"refusing_to_overwrite_input: {protected}")

    if output.name in FORBIDDEN_OUTPUT_NAMES:
        raise MaterializerError(
            f"refusing_authority_or_contract_surface_output: {output.name}"
        )

    reject_symlink_chain(output)

    if output.exists() and not output.is_file():
        raise MaterializerError(f"output_not_regular_file: {output}")


def snapshot_regular_files(
    paths: Iterable[Path],
) -> dict[Path, tuple[int, str]]:
    snapshots: dict[Path, tuple[int, str]] = {}
    for path in paths:
        require_regular_non_symlink(path, label="protected_input")
        canonical = path.resolve(strict=True)
        snapshots[canonical] = (
            canonical.stat().st_size,
            sha256_file(canonical),
        )
    return snapshots


def verify_regular_file_snapshots(
    snapshots: dict[Path, tuple[int, str]],
) -> None:
    for path, expected in snapshots.items():
        if path.is_symlink() or not path.is_file():
            raise MaterializerError(f"protected_input_changed_or_missing: {path}")
        observed = (path.stat().st_size, sha256_file(path))
        if observed != expected:
            raise MaterializerError(f"protected_input_changed: {path}")


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


# ---------------------------------------------------------------------------
# Strict upstream relation validation
# ---------------------------------------------------------------------------


def invoke_relation_validator(
    *,
    validator_path: Path,
    schema_path: Path,
    relation_path: Path,
) -> dict[str, Any]:
    require_regular_non_symlink(validator_path, label="relation_validator")
    require_regular_non_symlink(schema_path, label="relation_schema")
    require_regular_non_symlink(relation_path, label="relation")

    result = subprocess.run(
        [
            sys.executable,
            str(validator_path),
            "--schema",
            str(schema_path),
            "--relation",
            str(relation_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )

    detail = result.stdout.strip() or result.stderr.strip()
    if not detail:
        raise MaterializerError("relation_validator_produced_no_diagnostic")

    diagnostic = parse_json_text(detail, label="relation_validator_diagnostic")
    if not isinstance(diagnostic, dict):
        raise MaterializerError("relation_validator_diagnostic_not_object")

    if result.returncode != 0:
        errors = diagnostic.get("errors")
        raise MaterializerError(
            "relation_strict_validation_failed: "
            + json.dumps(errors if isinstance(errors, list) else diagnostic, sort_keys=True)
        )

    checks = diagnostic.get("checks")
    if diagnostic.get("tool") != "check_pulsemech_compute_planned_observed_relation_v0":
        raise MaterializerError("relation_validator_tool_mismatch")
    if diagnostic.get("schema_version") != RELATION_SCHEMA_VERSION:
        raise MaterializerError("relation_validator_schema_version_mismatch")
    if diagnostic.get("relation_type") != RELATION_TYPE:
        raise MaterializerError("relation_validator_relation_type_mismatch")
    if diagnostic.get("ok") is not True:
        raise MaterializerError("relation_validator_not_ok")
    if diagnostic.get("schema_valid") is not True:
        raise MaterializerError("relation_validator_schema_not_valid")
    if diagnostic.get("errors") != []:
        raise MaterializerError("relation_validator_errors_not_empty")
    if not isinstance(checks, dict) or not checks:
        raise MaterializerError("relation_validator_checks_missing")
    if any(value is not True for value in checks.values()):
        raise MaterializerError("relation_validator_check_not_true")

    return diagnostic


# ---------------------------------------------------------------------------
# Candidate gate derivation
# ---------------------------------------------------------------------------


def require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MaterializerError(f"{label}_not_object")
    return value


def require_object_map(value: Any, *, label: str) -> dict[str, dict[str, Any]]:
    mapping = require_object(value, label=label)
    if any(not isinstance(item, dict) for item in mapping.values()):
        raise MaterializerError(f"{label}_value_not_object")
    return mapping  # type: ignore[return-value]


def require_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise MaterializerError(f"{label}_not_string_array")
    return value


def validate_relation_materialization_boundary(
    relation: dict[str, Any],
) -> None:
    errors: list[str] = []

    if relation.get("schema_version") != RELATION_SCHEMA_VERSION:
        errors.append("relation_schema_version_mismatch")
    if relation.get("relation_type") != RELATION_TYPE:
        errors.append("relation_type_mismatch")
    if relation.get("record_status") not in {"example", "observed"}:
        errors.append("relation_record_status_invalid")
    if relation.get("ok") is not True:
        errors.append("relation_not_ok")
    if relation.get("errors") != []:
        errors.append("relation_errors_not_empty")

    plan_binding = require_object(relation.get("plan_binding"), label="plan_binding")
    if plan_binding.get("apply_eligible") is not True:
        errors.append("relation_plan_not_apply_eligible")

    comparison_boundary = require_object(
        relation.get("comparison_boundary"),
        label="comparison_boundary",
    )
    if comparison_boundary.get("plan_target_matches_subject_repository") is not True:
        errors.append("relation_plan_target_subject_mismatch")
    if comparison_boundary.get("comparison_writes_subject") is not False:
        errors.append("relation_comparison_writes_subject")

    authority = require_object(
        relation.get("authority_boundary"),
        label="authority_boundary",
    )
    expected_authority = {
        "write_mode": "relation_only",
        "writes_target_repository": False,
        "mutates_subject_run": False,
        "changes_release_authority": False,
        "changes_gate_policy": False,
        "changes_gate_semantics": False,
        "creates_release_decision": False,
        "creates_gate_result": False,
        "activates_compute_gate": False,
        "creates_compute_budget": False,
        "relation_record_is_release_authority": False,
    }
    for field, expected in expected_authority.items():
        if authority.get(field) != expected:
            errors.append(f"relation_authority_boundary_mismatch: {field}")

    require_object_map(relation.get("expectations"), label="expectations")
    require_object_map(relation.get("observations"), label="observations")
    require_object_map(relation.get("relations"), label="relations")
    require_object_map(relation.get("findings"), label="findings")
    require_object(relation.get("coverage"), label="coverage")
    require_object(relation.get("summary"), label="summary")
    require_object(relation.get("comparison_identity"), label="comparison_identity")

    if errors:
        raise MaterializerError("; ".join(sorted(set(errors))))


def coverage_counts_are_closed(
    coverage: dict[str, Any],
    *,
    expectations: dict[str, dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    relations: dict[str, dict[str, Any]],
) -> bool:
    return (
        coverage.get("plan_operations_referenced")
        == coverage.get("plan_operations_total")
        and coverage.get("expectations_total") == len(expectations)
        and coverage.get("expectations_classified") == len(expectations)
        and coverage.get("observations_total") == len(observations)
        and coverage.get("observations_classified") == len(observations)
        and coverage.get("relations_total") == len(relations)
        and coverage.get("missing_plan_operation_refs") == []
        and coverage.get("unclassified_expectation_ids") == []
        and coverage.get("unclassified_observation_ids") == []
        and coverage.get("unresolved_reasons") == []
    )


def coverage_axes_are_closed(coverage: dict[str, Any]) -> bool:
    return all(
        coverage.get(field) in {"complete", "not_required"}
        for field in (
            "identity_coverage_status",
            "execution_coverage_status",
            "declared_role_coverage_status",
            "authority_coverage_status",
            "downstream_consumption_coverage_status",
        )
    )


def relation_records_are_decisive_and_complete(
    relations: dict[str, dict[str, Any]],
) -> bool:
    return all(
        isinstance(relation.get("evaluation"), dict)
        and relation["evaluation"].get("decisive") is True
        and relation["evaluation"].get("coverage") == "complete"
        for relation in relations.values()
    )


def execution_expectation_count(expectations: dict[str, dict[str, Any]]) -> int:
    return sum(
        expectation.get("expectation_kind")
        in {
            "planned_execution_expected",
            "planned_execution_and_consumption_expected",
        }
        for expectation in expectations.values()
    )


def finding_types(findings: dict[str, dict[str, Any]]) -> set[str]:
    return {
        str(finding.get("finding_type"))
        for finding in findings.values()
        if isinstance(finding.get("finding_type"), str)
    }


def derive_transition_path_complete(
    relation: dict[str, Any],
) -> bool:
    expectations = require_object_map(
        relation.get("expectations"),
        label="expectations",
    )
    observations = require_object_map(
        relation.get("observations"),
        label="observations",
    )
    relations = require_object_map(relation.get("relations"), label="relations")
    findings = require_object_map(relation.get("findings"), label="findings")
    coverage = require_object(relation.get("coverage"), label="coverage")
    summary = require_object(relation.get("summary"), label="summary")

    statuses = {
        str(item.get("relation_status"))
        for item in relations.values()
    }

    return (
        execution_expectation_count(expectations) > 0
        and coverage.get("comparison_status") == "complete"
        and coverage_counts_are_closed(
            coverage,
            expectations=expectations,
            observations=observations,
            relations=relations,
        )
        and coverage_axes_are_closed(coverage)
        and summary.get("comparison_complete") is True
        and summary.get("relations") == len(relations)
        and summary.get("decisive_relations") == len(relations)
        and summary.get("unresolved_relations") == 0
        and relation_records_are_decisive_and_complete(relations)
        and not (statuses & PATH_FAILURE_STATUSES)
        and not (finding_types(findings) & PATH_FAILURE_FINDINGS)
    )


def derive_transition_authority_binding_ok(
    relation: dict[str, Any],
) -> bool:
    relations = require_object_map(relation.get("relations"), label="relations")
    findings = require_object_map(relation.get("findings"), label="findings")
    coverage = require_object(relation.get("coverage"), label="coverage")

    if coverage.get("identity_coverage_status") not in {"complete", "not_required"}:
        return False
    if coverage.get("declared_role_coverage_status") not in {"complete", "not_required"}:
        return False
    if coverage.get("authority_coverage_status") not in {"complete", "not_required"}:
        return False

    statuses = {
        str(item.get("relation_status"))
        for item in relations.values()
    }
    if statuses & AUTHORITY_FAILURE_STATUSES:
        return False
    if finding_types(findings) & AUTHORITY_FAILURE_FINDINGS:
        return False

    allowed = {"match", "not_required"}
    for relation_record in relations.values():
        evaluation = relation_record.get("evaluation")
        if not isinstance(evaluation, dict):
            return False
        for field in (
            "source_identity",
            "run_binding",
            "declared_role",
            "authority_class",
        ):
            if evaluation.get(field) not in allowed:
                return False

    return True


def derive_unbound_authoritative_mutation_absent(
    relation: dict[str, Any],
) -> bool:
    observations = require_object_map(
        relation.get("observations"),
        label="observations",
    )

    for observation in observations.values():
        if observation.get("unbound_authoritative_mutation") is True:
            return False

        mutation_classes = observation.get("observed_mutation_classes")
        if not isinstance(mutation_classes, list):
            return False
        authority_mutation = bool(
            set(mutation_classes) & AUTHORITATIVE_MUTATION_CLASSES
        )
        if not authority_mutation:
            continue
        if observation.get("binding_status") != "complete":
            return False
        if observation.get("binding_class") not in BOUND_AUTHORITY_CLASSES:
            return False

    return True


def derive_candidate_gates(relation: dict[str, Any]) -> dict[str, bool]:
    gates = {
        "compute_transition_path_complete": derive_transition_path_complete(
            relation
        ),
        "compute_transition_authority_binding_ok": (
            derive_transition_authority_binding_ok(relation)
        ),
        "compute_transition_unbound_mutation_absent": (
            derive_unbound_authoritative_mutation_absent(relation)
        ),
    }

    if tuple(gates) != CANDIDATE_GATES:
        raise MaterializerError("candidate_gate_identity_order_mismatch")
    if any(type(value) is not bool for value in gates.values()):
        raise MaterializerError("candidate_gate_value_not_boolean")
    return gates


# ---------------------------------------------------------------------------
# Status fold and deterministic diagnostic
# ---------------------------------------------------------------------------


def validate_base_status(status: Any) -> dict[str, Any]:
    if not isinstance(status, dict):
        raise MaterializerError("status_not_object")
    gates = status.get("gates")
    if not isinstance(gates, dict):
        raise MaterializerError("status_gates_not_object")
    return status


def validate_existing_gate_conflicts(
    status: dict[str, Any],
    candidate_gates: dict[str, bool],
) -> None:
    gates = status["gates"]
    for gate_id, incoming in candidate_gates.items():
        if gate_id not in gates:
            continue
        existing = gates[gate_id]
        if type(existing) is not bool:
            raise MaterializerError(
                f"existing_candidate_gate_not_boolean: {gate_id}"
            )
        if existing is not incoming:
            raise MaterializerError(f"existing_gate_conflict: {gate_id}")


def fold_candidate_gates(
    status: dict[str, Any],
    candidate_gates: dict[str, bool],
) -> dict[str, Any]:
    folded = copy.deepcopy(status)
    gates = folded["gates"]
    for gate_id in CANDIDATE_GATES:
        gates[gate_id] = candidate_gates[gate_id]
    return folded


def make_report(
    *,
    ok: bool,
    relation_validated: bool,
    output_status_written: bool,
    relation_record_id: str | None,
    record_status: str | None,
    base_status_sha256: str | None,
    relation_sha256: str | None,
    output_status_sha256: str | None,
    candidate_gates: dict[str, bool],
    errors: list[str],
) -> dict[str, Any]:
    has_complete_gate_map = tuple(candidate_gates) == CANDIDATE_GATES
    candidate_all_true: bool | None = (
        all(candidate_gates.values()) if has_complete_gate_map else None
    )
    return {
        "base_status_sha256": base_status_sha256,
        "candidate_all_true": candidate_all_true,
        "candidate_gate_set": CANDIDATE_GATE_SET,
        "candidate_gates": dict(candidate_gates),
        "errors": sorted(set(errors)),
        "folded_gates": list(CANDIDATE_GATES) if output_status_written else [],
        "ok": ok,
        "output_status_sha256": output_status_sha256,
        "output_status_written": output_status_written,
        "record_status": record_status,
        "relation_record_id": relation_record_id,
        "relation_sha256": relation_sha256,
        "relation_validated": relation_validated,
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
    }


def build_and_write_folded_status(
    *,
    status_path: Path,
    relation_path: Path,
    schema_path: Path,
    validator_path: Path,
    output_path: Path,
) -> tuple[dict[str, Any], int]:
    relation_validated = False
    candidate_gates: dict[str, bool] = {}
    relation_record_id: str | None = None
    record_status: str | None = None
    base_status_sha256: str | None = None
    relation_sha256: str | None = None
    output_status_sha256: str | None = None
    output_written = False

    protected_paths = (
        status_path,
        relation_path,
        schema_path,
        validator_path,
        Path(__file__),
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    )

    try:
        reject_unsafe_output(output_path, protected_paths=protected_paths)
        snapshots = snapshot_regular_files(protected_paths)
        status_raw, status_bytes = load_json_document(status_path, label="status")
        relation_raw, relation_bytes = load_json_document(
            relation_path,
            label="relation",
        )
        base_status_sha256 = sha256_bytes(status_bytes)
        relation_sha256 = sha256_bytes(relation_bytes)

        if isinstance(relation_raw, dict):
            identity = relation_raw.get("comparison_identity")
            if isinstance(identity, dict):
                value = identity.get("relation_record_id")
                if isinstance(value, str):
                    relation_record_id = value
            value = relation_raw.get("record_status")
            if isinstance(value, str):
                record_status = value

        invoke_relation_validator(
            validator_path=validator_path,
            schema_path=schema_path,
            relation_path=relation_path,
        )
        relation_validated = True
        verify_regular_file_snapshots(snapshots)

        status = validate_base_status(status_raw)
        relation = require_object(relation_raw, label="relation")
        validate_relation_materialization_boundary(relation)

        candidate_gates = derive_candidate_gates(relation)
        validate_existing_gate_conflicts(status, candidate_gates)
        folded_status = fold_candidate_gates(status, candidate_gates)
        rendered_status = render_json(folded_status)
        output_status_sha256 = sha256_bytes(rendered_status.encode("utf-8"))

        verify_regular_file_snapshots(snapshots)
        atomic_write_text(output_path, rendered_status)
        output_written = True
        verify_regular_file_snapshots(snapshots)

    except MaterializerError as exc:
        if output_written and output_path.is_file() and not output_path.is_symlink():
            try:
                output_path.unlink()
            except OSError:
                pass
        report = make_report(
            ok=False,
            relation_validated=relation_validated,
            output_status_written=False,
            relation_record_id=relation_record_id,
            record_status=record_status,
            base_status_sha256=base_status_sha256,
            relation_sha256=relation_sha256,
            output_status_sha256=None,
            candidate_gates=candidate_gates,
            errors=[str(exc)],
        )
        return report, 1
    except (OSError, subprocess.SubprocessError) as exc:
        if output_written and output_path.is_file() and not output_path.is_symlink():
            try:
                output_path.unlink()
            except OSError:
                pass
        report = make_report(
            ok=False,
            relation_validated=relation_validated,
            output_status_written=False,
            relation_record_id=relation_record_id,
            record_status=record_status,
            base_status_sha256=base_status_sha256,
            relation_sha256=relation_sha256,
            output_status_sha256=None,
            candidate_gates=candidate_gates,
            errors=[f"materializer_io_or_process_error: {exc}"],
        )
        return report, 2

    report = make_report(
        ok=True,
        relation_validated=True,
        output_status_written=True,
        relation_record_id=relation_record_id,
        record_status=record_status,
        base_status_sha256=base_status_sha256,
        relation_sha256=relation_sha256,
        output_status_sha256=output_status_sha256,
        candidate_gates=candidate_gates,
        errors=[],
    )
    return report, 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Strictly validate a PULSEmech compute planned-observed relation "
            "and fold its three non-active candidate gate values into a new "
            "status JSON without modifying the input status."
        )
    )
    parser.add_argument("--status", required=True, help="Base status JSON path.")
    parser.add_argument(
        "--relation",
        required=True,
        help="Planned-observed relation JSON path.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_RELATION_SCHEMA),
        help="Planned-observed relation schema path.",
    )
    parser.add_argument(
        "--validator",
        default=str(DEFAULT_RELATION_VALIDATOR),
        help="Strict planned-observed relation validator path.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help=(
            "Separate candidate status output path. The tool refuses in-place "
            "writes and final authority-surface filenames."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, exit_code = build_and_write_folded_status(
        status_path=Path(args.status),
        relation_path=Path(args.relation),
        schema_path=Path(args.schema),
        validator_path=Path(args.validator),
        output_path=Path(args.output),
    )
    sys.stdout.write(render_json(report))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
