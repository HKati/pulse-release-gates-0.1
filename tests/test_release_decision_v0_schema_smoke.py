#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "materialize_release_decision.py"
SCHEMA = ROOT / "schemas" / "release_decision_v0.schema.json"


POLICY_TEXT = """\
policy:
  id: pulse-gate-policy-v0-test
  version: "0.0.0"

enforcement:
  required_missing: FAIL
  required_false: FAIL
  advisory_missing: WARN
  advisory_false: WARN

gates:
  required:
    - pass_controls_refusal
    - q1_grounded_ok
  core_required:
    - pass_controls_refusal
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
  advisory:
    - external_summaries_present
    - external_all_pass
"""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema() -> dict[str, Any]:
    schema = _read_json(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(
        _load_schema(),
        format_checker=jsonschema.FormatChecker(),
    )


def _assert_schema_valid(payload: dict[str, Any]) -> None:
    validator = _validator()
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"- {'.'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise AssertionError(f"expected schema-valid artifact, got errors:\n{details}")


def _assert_schema_invalid(payload: dict[str, Any]) -> None:
    validator = _validator()
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if not errors:
        raise AssertionError(
            "expected schema-invalid artifact, but validation produced no errors"
        )


def _status(
    gates: dict[str, Any],
    *,
    run_mode: str = "prod",
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": "status_v1",
        "created_utc": "2026-04-20T00:00:00Z",
        "metrics": {
            "run_mode": run_mode
        },
        "gates": gates,
    }

    if diagnostics is not None:
        payload["diagnostics"] = diagnostics

    return payload


def _run_materializer(
    tmp_path: Path,
    *,
    status: dict[str, Any],
    target: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    status_path = tmp_path / "status.json"
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    out_path = tmp_path / "release_decision_v0.json"

    _write_json(status_path, status)
    policy_path.write_text(POLICY_TEXT, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--status",
            str(status_path),
            "--policy",
            str(policy_path),
            "--target",
            target,
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if not out_path.exists():
        raise AssertionError(
            "materializer did not write release_decision_v0.json\n"
            f"returncode={result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result, _read_json(out_path)


def _stage_pass_artifact() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-schema-") as tmp:
        result, decision = _run_materializer(
            Path(tmp),
            target="stage",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True,
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert decision["release_level"] == "STAGE-PASS"
    return decision


def _prod_pass_artifact() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-schema-") as tmp:
        result, decision = _run_materializer(
            Path(tmp),
            target="prod",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True,
                    "external_summaries_present": True,
                    "external_all_pass": True,
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert decision["release_level"] == "PROD-PASS"
    return decision


def _prod_fail_artifact() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-schema-") as tmp:
        result, decision = _run_materializer(
            Path(tmp),
            target="prod",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True,
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 1
    assert decision["release_level"] == "FAIL"
    return decision


def test_release_decision_schema_file_is_valid_json_schema() -> None:
    _load_schema()


def test_generated_stage_pass_artifact_validates_against_schema() -> None:
    _assert_schema_valid(_stage_pass_artifact())


def test_generated_prod_pass_artifact_validates_against_schema() -> None:
    _assert_schema_valid(_prod_pass_artifact())


def test_generated_fail_artifact_validates_against_schema() -> None:
    _assert_schema_valid(_prod_fail_artifact())


def test_contradictory_stage_pass_with_failed_required_gates_is_invalid() -> None:
    decision = _stage_pass_artifact()
    decision["required_gates_passed"] = False

    _assert_schema_invalid(decision)


def test_contradictory_stage_pass_with_stubbed_condition_is_invalid() -> None:
    decision = _stage_pass_artifact()
    decision["conditions"]["stubbed"] = True
    decision["conditions"]["no_stubbed_gates"] = False

    _assert_schema_invalid(decision)


def test_contradictory_stage_pass_with_blocking_reasons_is_invalid() -> None:
    decision = _stage_pass_artifact()
    decision["blocking_reasons"] = ["synthetic blocking reason"]

    _assert_schema_invalid(decision)


def test_contradictory_prod_pass_with_advisory_external_mode_is_invalid() -> None:
    decision = _prod_pass_artifact()
    decision["conditions"]["external_evidence_mode"] = "advisory"

    _assert_schema_invalid(decision)


def test_contradictory_prod_pass_with_external_all_pass_false_is_invalid() -> None:
    decision = _prod_pass_artifact()
    decision["conditions"]["external_all_pass"] = False

    _assert_schema_invalid(decision)


def test_contradictory_prod_pass_with_missing_release_required_set_is_invalid() -> None:
    decision = _prod_pass_artifact()
    decision["active_gate_sets"] = ["required"]

    _assert_schema_invalid(decision)


def test_contradictory_prod_pass_with_failed_gate_result_is_invalid() -> None:
    decision = _prod_pass_artifact()
    mutated = copy.deepcopy(decision)
    mutated["gate_results"][0]["passed"] = False

    _assert_schema_invalid(mutated)


def test_contradictory_prod_pass_with_blocking_reasons_is_invalid() -> None:
    decision = _prod_pass_artifact()
    decision["blocking_reasons"] = ["synthetic blocking reason"]

    _assert_schema_invalid(decision)


def main() -> int:
    tests = [
        test_release_decision_schema_file_is_valid_json_schema,
        test_generated_stage_pass_artifact_validates_against_schema,
        test_generated_prod_pass_artifact_validates_against_schema,
        test_generated_fail_artifact_validates_against_schema,
        test_contradictory_stage_pass_with_failed_required_gates_is_invalid,
        test_contradictory_stage_pass_with_stubbed_condition_is_invalid,
        test_contradictory_stage_pass_with_blocking_reasons_is_invalid,
        test_contradictory_prod_pass_with_advisory_external_mode_is_invalid,
        test_contradictory_prod_pass_with_external_all_pass_false_is_invalid,
        test_contradictory_prod_pass_with_missing_release_required_set_is_invalid,
        test_contradictory_prod_pass_with_failed_gate_result_is_invalid,
        test_contradictory_prod_pass_with_blocking_reasons_is_invalid,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"ERROR in {test.__name__}: {exc}")
            return 1
        except Exception as exc:
            print(f"ERROR in {test.__name__}: unexpected exception: {exc}")
            return 1

    print("OK: release_decision_v0 schema smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
