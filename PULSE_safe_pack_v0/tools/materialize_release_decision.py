#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_ID = "pulse_release_decision_v0"
VERSION = "0.1.0"
PRODUCER_NAME = "materialize_release_decision.py"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATUS = REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
DEFAULT_POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_OUT = REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts" / "release_decision_v0.json"

_MISSING = object()

STUB_FLAG_PATHS = (
    "diagnostics.gates_stubbed",
    "metrics.gates_stubbed",
    "meta.diagnostics.gates_stubbed",
)

SCAFFOLD_FLAG_PATHS = (
    "diagnostics.scaffold",
    "metrics.scaffold",
    "meta.diagnostics.scaffold",
)

STUB_PROFILE_PATHS = (
    "diagnostics.stub_profile",
    "metrics.stub_profile",
    "meta.diagnostics.stub_profile",
)

NEUTRAL_STUB_PROFILES = {
    "",
    "none",
    "false",
    "real",
    "not_stubbed",
}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> Any:
    try:
        import yaml
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "PyYAML is required to read pulse_gate_policy_v0.yml"
        ) from exc

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _git_sha() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    sha = proc.stdout.strip()
    return sha or None


def _get_path(obj: Any, dotted: str) -> Any:
    """Return a dotted path value, using None for both missing and explicit null.

    Use _get_path_or_missing when the distinction between missing and explicit
    JSON null matters.
    """
    value = _get_path_or_missing(obj, dotted)
    if value is _MISSING:
        return None
    return value


def _get_path_or_missing(obj: Any, dotted: str) -> Any:
    """Return a dotted path value or _MISSING when any component is absent.

    This intentionally preserves explicit JSON null as None, so callers can
    distinguish a missing diagnostic flag from a present-but-null malformed flag.
    """
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _blocking_flag_present(obj: Any, *paths: str) -> bool:
    """Return true when any diagnostic flag blocks release-level pass.

    Missing values are neutral.

    Boolean false is neutral.
    Boolean true blocks.

    Any present non-boolean value, including explicit JSON null, blocks
    fail-closed. Diagnostic scaffold/stub flags must not be silently ignored
    when malformed.
    """
    for path in paths:
        value = _get_path_or_missing(obj, path)

        if value is _MISSING:
            continue

        if value is False:
            continue

        if value is True:
            return True

        # Present but malformed: null, string, number, array, object, etc.
        return True

    return False


def _stub_profile_blocks(value: Any) -> bool:
    """Return true when a present stub_profile value blocks release-level pass.

    Missing values must be handled by the caller.

    Strings are normalized and compared against known neutral profiles.
    Boolean false is neutral.
    Boolean true blocks.
    Explicit null and any other present non-string/non-boolean value block
    fail-closed.
    """
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in NEUTRAL_STUB_PROFILES

    if value is False:
        return False

    if value is True:
        return True

    # Present but malformed, including explicit JSON null.
    return True


def _stubbed(status: dict[str, Any]) -> bool:
    if _blocking_flag_present(status, *STUB_FLAG_PATHS):
        return True

    for path in STUB_PROFILE_PATHS:
        value = _get_path_or_missing(status, path)
        if value is _MISSING:
            continue
        if _stub_profile_blocks(value):
            return True

    return False


def _scaffold(status: dict[str, Any]) -> bool:
    return _blocking_flag_present(status, *SCAFFOLD_FLAG_PATHS)


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _gate_result(status: dict[str, Any], gate_id: str) -> dict[str, Any]:
    gates = status.get("gates")

    if not isinstance(gates, dict):
        return {
            "gate_id": gate_id,
            "present": False,
            "passed": False,
            "value_type": "missing",
            "reason": "status.gates is missing or not an object",
        }

    if gate_id not in gates:
        return {
            "gate_id": gate_id,
            "present": False,
            "passed": False,
            "value_type": "missing",
            "reason": "missing required gate",
        }

    value = gates[gate_id]
    passed = value is True

    return {
        "gate_id": gate_id,
        "present": True,
        "passed": passed,
        "value_type": _value_type(value),
        "reason": None if passed else "gate value is not literal true",
    }


def _gate_passed(status: dict[str, Any], gate_id: str) -> bool:
    return _gate_result(status, gate_id)["passed"] is True


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)

    return out


def _policy_gate_set(policy: dict[str, Any], name: str) -> list[str]:
    gates = policy.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("policy.gates is missing or not an object")

    values = gates.get(name)
    if not isinstance(values, list):
        raise ValueError(f"policy.gates.{name} is missing or not a list")

    out: list[str] = []
    for idx, item in enumerate(values):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"policy.gates.{name}[{idx}] is not a non-empty string")
        out.append(item)

    return out


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _validate_status_schema(
    status: dict[str, Any],
    schema_path: Path | None,
) -> dict[str, Any]:
    if schema_path is None:
        return {
            "mode": "not_requested",
            "ok": None,
            "schema_path": None,
            "errors": [],
        }

    errors: list[str] = []

    try:
        import jsonschema
    except Exception as exc:  # pragma: no cover - environment-specific
        return {
            "mode": "validated",
            "ok": False,
            "schema_path": _rel(schema_path),
            "errors": [f"jsonschema import failed: {exc}"],
        }

    try:
        schema = _read_json(schema_path)
        validator = jsonschema.Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(status), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in error.path) or "<root>"
            errors.append(f"{path}: {error.message}")
    except Exception as exc:
        errors.append(str(exc))

    return {
        "mode": "validated",
        "ok": not errors,
        "schema_path": _rel(schema_path),
        "errors": errors,
    }


def _materialize_decision(
    *,
    status: dict[str, Any],
    policy: dict[str, Any],
    target: str,
    status_path: Path,
    policy_path: Path,
    status_schema_path: Path | None,
    preexisting_errors: list[str],
) -> dict[str, Any]:
    blocking_reasons: list[str] = list(preexisting_errors)
    decision_basis: list[str] = []

    active_gate_sets = ["required"] if target == "stage" else ["required", "release_required"]

    effective_required_gates: list[str] = []
    gate_results: list[dict[str, Any]] = []

    if not preexisting_errors:
        try:
            for gate_set in active_gate_sets:
                effective_required_gates.extend(_policy_gate_set(policy, gate_set))
            effective_required_gates = _unique_preserve_order(effective_required_gates)
        except Exception as exc:
            _add_reason(blocking_reasons, f"policy materialization failed: {exc}")

    for gate_id in effective_required_gates:
        result = _gate_result(status, gate_id)
        gate_results.append(result)

        if not result["passed"]:
            reason = result["reason"] or "gate did not pass"
            _add_reason(blocking_reasons, f"{gate_id}: {reason}")

    detectors_materialized_ok = _gate_passed(status, "detectors_materialized_ok")
    external_summaries_present = _gate_passed(status, "external_summaries_present")
    external_all_pass = _gate_passed(status, "external_all_pass")

    stubbed = _stubbed(status)
    scaffold = _scaffold(status)
    no_stubbed_gates = not stubbed and not scaffold

    if target == "stage":
        if not detectors_materialized_ok:
            _add_reason(
                blocking_reasons,
                "detectors_materialized_ok: required for STAGE-PASS and not literal true",
            )
        external_evidence_mode = "advisory"
        decision_basis.append("stage target uses required gate set plus stage release conditions")
    else:
        external_evidence_mode = "required"
        decision_basis.append("prod target uses required + release_required gate sets")

    if stubbed:
        _add_reason(blocking_reasons, "stubbed diagnostics are present")
    if scaffold:
        _add_reason(blocking_reasons, "scaffold diagnostics are present")

    status_schema_validation = _validate_status_schema(status, status_schema_path)
    if status_schema_validation["ok"] is False:
        for error in status_schema_validation["errors"]:
            _add_reason(blocking_reasons, f"status schema validation failed: {error}")

    required_gates_passed = bool(effective_required_gates) and all(
        result["passed"] for result in gate_results
    )

    if not effective_required_gates:
        _add_reason(blocking_reasons, "effective required gate set is empty")

    if blocking_reasons:
        release_level = "FAIL"
    elif target == "stage":
        release_level = "STAGE-PASS"
    else:
        release_level = "PROD-PASS"

    if required_gates_passed:
        decision_basis.append("all effective required gates are literal true")
    else:
        decision_basis.append("one or more effective required gates failed or were missing")

    if no_stubbed_gates:
        decision_basis.append("no stubbed/scaffold diagnostics detected")
    else:
        decision_basis.append("stubbed/scaffold diagnostics block release-level pass")

    if detectors_materialized_ok:
        decision_basis.append("detectors_materialized_ok is literal true")

    if target == "prod" and external_summaries_present and external_all_pass:
        decision_basis.append("external evidence is present and aggregate external pass is true")

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "created_utc": _utc_now(),
        "producer": {
            "name": PRODUCER_NAME,
            "version": VERSION,
        },
        "target": target,
        "release_level": release_level,
        "status_path": _rel(status_path),
        "policy_path": _rel(policy_path),
        "status_sha256": _sha256(status_path),
        "policy_sha256": _sha256(policy_path),
        "git_sha": _git_sha(),
        "run_mode": _get_path(status, "metrics.run_mode"),
        "active_gate_sets": active_gate_sets,
        "effective_required_gates": effective_required_gates,
        "required_gates_passed": required_gates_passed,
        "conditions": {
            "detectors_materialized_ok": detectors_materialized_ok,
            "external_summaries_present": external_summaries_present,
            "external_all_pass": external_all_pass,
            "stubbed": stubbed,
            "scaffold": scaffold,
            "no_stubbed_gates": no_stubbed_gates,
            "external_evidence_mode": external_evidence_mode,
        },
        "status_schema_validation": status_schema_validation,
        "gate_results": gate_results,
        "blocking_reasons": blocking_reasons,
        "decision_basis": decision_basis,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the PULSEmech release_decision_v0 artifact."
    )

    parser.add_argument(
        "--status",
        default=str(DEFAULT_STATUS),
        help="Path to the status.json artifact.",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY),
        help="Path to pulse_gate_policy_v0.yml.",
    )
    parser.add_argument(
        "--target",
        choices=["stage", "prod"],
        required=True,
        help="Release target to materialize.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Path to write release_decision_v0.json.",
    )
    parser.add_argument(
        "--status-schema",
        default=None,
        help=(
            "Optional JSON schema path for validating status.json before "
            "materializing the release decision."
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    status_path = Path(args.status)
    policy_path = Path(args.policy)
    out_path = Path(args.out)
    status_schema_path = Path(args.status_schema) if args.status_schema else None

    if not status_path.is_absolute():
        status_path = REPO_ROOT / status_path
    if not policy_path.is_absolute():
        policy_path = REPO_ROOT / policy_path
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    if status_schema_path is not None and not status_schema_path.is_absolute():
        status_schema_path = REPO_ROOT / status_schema_path

    errors: list[str] = []

    status: dict[str, Any] = {}
    policy: dict[str, Any] = {}

    try:
        loaded_status = _read_json(status_path)
        if not isinstance(loaded_status, dict):
            errors.append("status artifact root is not an object")
        else:
            status = loaded_status
    except Exception as exc:
        errors.append(f"status artifact could not be read: {exc}")

    try:
        loaded_policy = _read_yaml(policy_path)
        if not isinstance(loaded_policy, dict):
            errors.append("policy root is not an object")
        else:
            policy = loaded_policy
    except Exception as exc:
        errors.append(f"policy could not be read: {exc}")

    decision = _materialize_decision(
        status=status,
        policy=policy,
        target=args.target,
        status_path=status_path,
        policy_path=policy_path,
        status_schema_path=status_schema_path,
        preexisting_errors=errors,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(decision, indent=2, sort_keys=True))

    return 0 if decision["release_level"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
