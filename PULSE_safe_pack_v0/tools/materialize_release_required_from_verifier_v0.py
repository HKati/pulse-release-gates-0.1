#!/usr/bin/env python3
"""Materialize release-required gates from a verified recorded-evidence report.

This tool is a prerequisite/admission step only.

It does not replace check_gates.py.
It does not redefine status.json semantics.
It does not change gate policy.
It does not create independent release authority.

Role:
verified recorded release-evidence report
-> policy-derived release_required gate set
-> literal true materialization into status["gates"]
-> existing check_gates.py path
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fail closed at runtime if unavailable
    yaml = None

EXPECTED_VERIFIER_SCHEMA = "recorded_release_evidence_verifier_v0"
EXPECTED_VERIFIER_STATUS = "verified"
EXPECTED_POLICY_SET = "required+release_required"
EXPECTED_RUN_MODE = "prod"


def _repo_root_from_tool() -> Path:
    return Path(__file__).resolve().parents[2]


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _yaml_loader_no_duplicates():
    if yaml is None:
        raise RuntimeError("PyYAML is required for YAML verification")

    class Loader(yaml.SafeLoader):
        pass

    def construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML key {key!r}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    Loader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    return Loader


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value.lower()
    )


def _is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(
        c in "0123456789abcdef" for c in value.lower()
    )


def _safe_read_text(path: Path, label: str, errors: list[str]) -> str | None:
    try:
        if not path.exists():
            errors.append(f"{label} not found: {path}")
            return None
        if not path.is_file():
            errors.append(f"{label} must be a file: {path}")
            return None
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return None


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    text = _safe_read_text(path, label, errors)
    if text is None:
        return None
    try:
        data = json.loads(text, object_pairs_hook=_json_object_no_duplicates)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return data


def _load_yaml(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if yaml is None:
        errors.append(f"{label} could not be loaded: PyYAML is unavailable")
        return None
    text = _safe_read_text(path, label, errors)
    if text is None:
        return None
    try:
        loader = _yaml_loader_no_duplicates()
        data = yaml.load(text, Loader=loader)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} must be a YAML mapping")
        return None
    return data


def _sha256_file(path: Path, label: str, errors: list[str]) -> str | None:
    try:
        if not path.exists():
            errors.append(f"{label} not found: {path}")
            return None
        if not path.is_file():
            errors.append(f"{label} must be a file: {path}")
            return None
    except OSError as exc:
        errors.append(f"{label} path check failed: {exc}")
        return None

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return None
    return digest.hexdigest()


def _require_object(parent: dict[str, Any], key: str, label: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    return value


def _normalize_gate_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if not value:
        errors.append(f"{label} must not be empty")
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not _is_non_empty_text(item):
            errors.append(f"{label} entries must be non-empty strings")
            continue
        gate_id = str(item).strip()
        if gate_id in seen:
            errors.append(f"{label} contains duplicate gate id {gate_id!r}")
            continue
        seen.add(gate_id)
        normalized.append(gate_id)
    return normalized


def _extract_release_required_gates(policy_obj: dict[str, Any], errors: list[str]) -> list[str]:
    gates = policy_obj.get("gates")
    if not isinstance(gates, dict):
        errors.append("policy file must contain top-level gates mapping")
        return []

        return _normalize_gate_list(
        gates.get("release_required"),
        "gates.release_required",
        errors,
    )


def _extract_registry_gate_ids(registry_obj: dict[str, Any], errors: list[str]) -> set[str]:
    gates = registry_obj.get("gates")
    if not isinstance(gates, dict):
        errors.append("registry file must contain top-level gates mapping")
        return set()

    gate_ids: set[str] = set()
    for gate_id in gates:
        if not _is_non_empty_text(gate_id):
            errors.append("registry gate ids must be non-empty strings")
            continue
        gate_ids.add(str(gate_id))
    if not gate_ids:
        errors.append("registry file must declare at least one gate id")
    return gate_ids


def _validate_git_sha(value: Any, label: str, errors: list[str]) -> bool:
    if not _is_git_sha(value):
        errors.append(f"{label} must be a 40-hex git sha")
        return False
    return True


def _validate_run_key(value: Any, label: str, errors: list[str]) -> bool:
    if not _is_non_empty_text(value):
        errors.append(f"{label} must be a non-empty string")
        return False
    return True


def _canonical_repo_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:  # noqa: BLE001
        return str(path)


def _path_matches_recorded(value: Any, path: Path, repo_root: Path) -> bool:
    if not _is_non_empty_text(value):
        return False
    actual = str(value).strip()
    candidates = {
        str(path),
        str(path.resolve()),
        _canonical_repo_path(path, repo_root),
    }
    return actual in candidates


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def materialize_release_required_from_verifier(
    *,
    status_path: Path,
    verifier_report_path: Path,
    policy_path: Path,
    registry_path: Path,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    errors: list[str] = []
    materialized_gates: list[str] = []
    repo_root = _repo_root_from_tool()

    status = _load_json(status_path, "status.json", errors)
    verifier_report = _load_json(
        verifier_report_path,
        "recorded_release_evidence_verifier_v0.json",
        errors,
    )
    policy_obj = _load_yaml(policy_path, "policy file", errors)
    registry_obj = _load_yaml(registry_path, "registry file", errors)

    if status is None or verifier_report is None or policy_obj is None or registry_obj is None:
        return None, materialized_gates, errors

    metrics = _require_object(status, "metrics", "status", errors)
    diagnostics = status.get("diagnostics")
    if diagnostics is None:
        diagnostics_obj: dict[str, Any] = {}
    elif isinstance(diagnostics, dict):
        diagnostics_obj = diagnostics
    else:
        errors.append("status.diagnostics must be an object when present")
        diagnostics_obj = {}

    gates = status.get("gates")
    if not isinstance(gates, dict):
        errors.append("status.gates must be an object")
        gates = {}

    status_git_sha = metrics.get("git_sha")
    status_run_key = metrics.get("run_key")
    status_run_mode = metrics.get("run_mode")
    status_policy_path = metrics.get("gate_policy_path")
    status_policy_sha = metrics.get("gate_policy_sha256")

    _validate_git_sha(status_git_sha, "status.metrics.git_sha", errors)
    _validate_run_key(status_run_key, "status.metrics.run_key", errors)

    if status_run_mode != EXPECTED_RUN_MODE:
        errors.append(
            "status.metrics.run_mode must be 'prod' for release-grade materialization "
            f"(got {status_run_mode!r})"
        )

    if diagnostics_obj.get("gates_stubbed") is True:
        errors.append("status.diagnostics.gates_stubbed must not be true for release-grade materialization")
    if diagnostics_obj.get("scaffold") is True:
        errors.append("status.diagnostics.scaffold must not be true for release-grade materialization")

    if not _is_non_empty_text(status_policy_path):
        errors.append("status.metrics.gate_policy_path must be a non-empty string")
    elif not _path_matches_recorded(status_policy_path, policy_path, repo_root):
        errors.append(
            "status.metrics.gate_policy_path does not match the current policy file "
            f"(got {status_policy_path!r}, expected {_canonical_repo_path(policy_path, repo_root)!r})"
        )

    if not _is_sha256(status_policy_sha):
        errors.append("status.metrics.gate_policy_sha256 must be a 64-hex sha256")

    if verifier_report.get("schema_version") != EXPECTED_VERIFIER_SCHEMA:
        errors.append(
            "verifier report schema_version must be "
            f"{EXPECTED_VERIFIER_SCHEMA!r}"
        )
    if verifier_report.get("status") != EXPECTED_VERIFIER_STATUS:
        errors.append(
            "verifier report status must be "
            f"{EXPECTED_VERIFIER_STATUS!r} (got {verifier_report.get('status')!r})"
        )

    verifier_errors = verifier_report.get("errors")
    if verifier_errors is not None:
        if not isinstance(verifier_errors, list):
            errors.append("verifier_report.errors must be an array when present")
        elif verifier_errors:
            errors.append("verifier_report.errors must be absent or empty before materialization")

    policy_sha = _sha256_file(policy_path, "policy file", errors)
    registry_sha = _sha256_file(registry_path, "registry file", errors)

    if policy_sha is not None and status_policy_sha is not None and status_policy_sha != policy_sha:
        errors.append(
            "status.metrics.gate_policy_sha256 does not match the current policy file "
            f"(expected {policy_sha!r}, got {status_policy_sha!r})"
        )

    run_identity = _require_object(verifier_report, "run_identity", "verifier_report", errors)
    report_git_sha = run_identity.get("git_sha")
    report_run_key = run_identity.get("run_key")
    report_run_mode = run_identity.get("run_mode")

    _validate_git_sha(report_git_sha, "verifier_report.run_identity.git_sha", errors)
    _validate_run_key(report_run_key, "verifier_report.run_identity.run_key", errors)
    if report_run_mode != EXPECTED_RUN_MODE:
        errors.append(
            "verifier_report.run_identity.run_mode must be 'prod' "
            f"(got {report_run_mode!r})"
        )

    if status_git_sha != report_git_sha:
        errors.append(
            "status.metrics.git_sha must match verifier_report.run_identity.git_sha "
            f"(expected {report_git_sha!r}, got {status_git_sha!r})"
        )
    if status_run_key != report_run_key:
        errors.append(
            "status.metrics.run_key must match verifier_report.run_identity.run_key "
            f"(expected {report_run_key!r}, got {status_run_key!r})"
        )

    verified_subjects = _require_object(verifier_report, "verified_subjects", "verifier_report", errors)
    verified_subject_git_sha = verified_subjects.get("git_sha")
    verified_subject_run_key = verified_subjects.get("run_key")
    verified_subject_commit_sha = verified_subjects.get("commit_sha")

    _validate_git_sha(verified_subject_git_sha, "verifier_report.verified_subjects.git_sha", errors)
    _validate_run_key(verified_subject_run_key, "verifier_report.verified_subjects.run_key", errors)
    _validate_git_sha(verified_subject_commit_sha, "verifier_report.verified_subjects.commit_sha", errors)

    if verified_subject_git_sha != status_git_sha:
        errors.append(
            "verifier_report.verified_subjects.git_sha must match status.metrics.git_sha "
            f"(expected {status_git_sha!r}, got {verified_subject_git_sha!r})"
        )
    if verified_subject_run_key != status_run_key:
        errors.append(
            "verifier_report.verified_subjects.run_key must match status.metrics.run_key "
            f"(expected {status_run_key!r}, got {verified_subject_run_key!r})"
        )
    if verified_subject_commit_sha != status_git_sha:
        errors.append(
            "verifier_report.verified_subjects.commit_sha must match status.metrics.git_sha "
            f"(expected {status_git_sha!r}, got {verified_subject_commit_sha!r})"
        )

    policy_binding = _require_object(verifier_report, "policy_binding", "verifier_report", errors)
    report_policy_set = policy_binding.get("policy_set")
    report_policy_sha = policy_binding.get("policy_sha256")

    if report_policy_set != EXPECTED_POLICY_SET:
        errors.append(
            "verifier_report.policy_binding.policy_set must be "
            f"{EXPECTED_POLICY_SET!r} (got {report_policy_set!r})"
        )
    if not _is_sha256(report_policy_sha):
        errors.append("verifier_report.policy_binding.policy_sha256 must be a 64-hex sha256")

    if policy_sha is not None and report_policy_sha != policy_sha:
        errors.append(
            "verifier_report.policy_binding.policy_sha256 does not match the current policy file "
            f"(expected {policy_sha!r}, got {report_policy_sha!r})"
        )
    if status_policy_sha is not None and report_policy_sha != status_policy_sha:
        errors.append(
            "verifier_report.policy_binding.policy_sha256 must match status.metrics.gate_policy_sha256 "
            f"(expected {status_policy_sha!r}, got {report_policy_sha!r})"
        )

    registry_binding = _require_object(verifier_report, "registry_binding", "verifier_report", errors)
    report_registry_sha = registry_binding.get("registry_sha256")
    if not _is_sha256(report_registry_sha):
        errors.append("verifier_report.registry_binding.registry_sha256 must be a 64-hex sha256")
    if registry_sha is not None and report_registry_sha != registry_sha:
        errors.append(
            "verifier_report.registry_binding.registry_sha256 does not match the current registry file "
            f"(expected {registry_sha!r}, got {report_registry_sha!r})"
        )

    release_required_gates = _extract_release_required_gates(policy_obj, errors)
    registry_gate_ids = _extract_registry_gate_ids(registry_obj, errors)
    for gate_id in release_required_gates:
        if gate_id not in registry_gate_ids:
            errors.append(
                f"policy.gates.release_required contains unknown registry gate id {gate_id!r}"
            )

    admissibility = verifier_report.get("gate_materialization_admissibility")
    if not isinstance(admissibility, dict):
        errors.append("verifier_report.gate_materialization_admissibility must be an object")
        admissibility = {}

    if errors:
        return None, materialized_gates, errors

    for gate_id in release_required_gates:
        entry = admissibility.get(gate_id)
        if not isinstance(entry, dict):
            errors.append(
                f"verifier_report.gate_materialization_admissibility.{gate_id} must be an object"
            )
            continue

        if entry.get("status") != "verified":
            errors.append(
                "verifier_report.gate_materialization_admissibility."
                f"{gate_id}.status must be 'verified' (got {entry.get('status')!r})"
            )
            continue

        if entry.get("admissible") is not True:
            errors.append(
                "verifier_report.gate_materialization_admissibility."
                f"{gate_id}.admissible must be literal true"
            )
            continue

        entry_errors = entry.get("errors")
        if entry_errors is not None:
            if not isinstance(entry_errors, list):
                errors.append(
                    "verifier_report.gate_materialization_admissibility."
                    f"{gate_id}.errors must be an array when present"
                )
                continue
            if entry_errors:
                errors.append(
                    "verifier_report.gate_materialization_admissibility."
                    f"{gate_id}.errors must be absent or empty before materialization"
                )
                continue

        gates[gate_id] = True
        materialized_gates.append(gate_id)

    if errors:
        return None, materialized_gates, errors

    status["gates"] = gates
    return status, materialized_gates, errors


def main(argv: list[str] | None = None) -> int:
    root = _repo_root_from_tool()
    parser = argparse.ArgumentParser(
        description=(
            "Materialize release-required gates into status.json from a verified "
            "recorded release-evidence verifier report."
        )
    )
    parser.add_argument(
        "--status",
        default=str(root / "PULSE_safe_pack_v0" / "artifacts" / "status.json"),
        help="Path to the input status.json.",
    )
    parser.add_argument(
        "--verifier-report",
        default=str(
            root / "PULSE_safe_pack_v0" / "artifacts" / "recorded_release_evidence_verifier_v0.json"
        ),
        help="Path to recorded_release_evidence_verifier_v0.json.",
    )
    parser.add_argument(
        "--policy",
        default=str(root / "pulse_gate_policy_v0.yml"),
        help="Path to pulse_gate_policy_v0.yml.",
    )
    parser.add_argument(
        "--registry",
        default=str(root / "pulse_gate_registry_v0.yml"),
        help="Path to pulse_gate_registry_v0.yml.",
    )
    parser.add_argument(
        "--out",
        default=str(root / "PULSE_safe_pack_v0" / "artifacts" / "status.json"),
        help="Path to write the materialized status.json.",
    )
    args = parser.parse_args(argv)

    status, materialized_gates, errors = materialize_release_required_from_verifier(
        status_path=Path(args.status),
        verifier_report_path=Path(args.verifier_report),
        policy_path=Path(args.policy),
        registry_path=Path(args.registry),
    )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    assert status is not None
    _write_json(Path(args.out), status)
    print(
        "OK: materialized release-required gates from verified recorded evidence: "
        + ", ".join(materialized_gates)
    )
    print(f"Status written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
