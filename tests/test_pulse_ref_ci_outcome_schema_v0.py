from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_ci_outcome_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_outcome() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_ci_outcome_v0",
        "provider": "github_actions",
        "workflow": "PULSE CI",
        "run_id": "25597787354",
        "run_attempt": 1,
        "run_url": "https://github.com/HKati/pulse-release-gates-0.1/actions/runs/25597787354",
        "repository": "HKati/pulse-release-gates-0.1",
        "commit_sha": "a" * 40,
        "gate_check_job": "Tools smoke tests",
        "gate_check_conclusion": "success",
        "created_utc": "2026-05-09T00:00:00Z",
        "started_utc": "2026-05-09T00:00:01Z",
        "completed_utc": "2026-05-09T00:00:02Z",
        "authority_boundary": {
            "normative_decision_path": (
                "status.json -> declared gate policy -> materialized required gates "
                "-> strict gate checking -> CI outcome"
            ),
            "ci_role": "records_declared_policy_enforcement",
            "creates_release_authority": False,
        },
    }


def _errors(instance: dict[str, Any]) -> list[ValidationError]:
    return list(_validator().iter_errors(instance))


def _has_error(
    errors: list[ValidationError],
    *,
    path: list[str] | None = None,
    validator: str | None = None,
) -> bool:
    for error in errors:
        if path is not None and list(error.absolute_path) != path:
            continue
        if validator is not None and error.validator != validator:
            continue
        return True

    return False


def test_schema_self_validates() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_valid_ci_outcome_passes() -> None:
    assert _errors(_valid_outcome()) == []


def test_run_attempt_is_required() -> None:
    outcome = _valid_outcome()
    outcome.pop("run_attempt")

    errors = _errors(outcome)

    assert _has_error(errors, validator="required")


def test_run_attempt_must_be_positive() -> None:
    outcome = _valid_outcome()
    outcome["run_attempt"] = 0

    errors = _errors(outcome)

    assert _has_error(errors, path=["run_attempt"], validator="minimum")


def test_provider_is_fixed() -> None:
    outcome = _valid_outcome()
    outcome["provider"] = "other_ci"

    errors = _errors(outcome)

    assert _has_error(errors, path=["provider"], validator="const")


def test_schema_id_is_fixed() -> None:
    outcome = _valid_outcome()
    outcome["schema"] = "other_schema"

    errors = _errors(outcome)

    assert _has_error(errors, path=["schema"], validator="const")


def test_run_id_must_be_numeric_string() -> None:
    outcome = _valid_outcome()
    outcome["run_id"] = "run-123"

    errors = _errors(outcome)

    assert _has_error(errors, path=["run_id"], validator="pattern")


def test_run_url_must_be_github_actions_run_url() -> None:
    outcome = _valid_outcome()
    outcome["run_url"] = "https://example.com/actions/runs/123"

    errors = _errors(outcome)

    assert _has_error(errors, path=["run_url"], validator="pattern")


def test_repository_must_be_owner_repo() -> None:
    outcome = _valid_outcome()
    outcome["repository"] = "not-a-repo-name"

    errors = _errors(outcome)

    assert _has_error(errors, path=["repository"], validator="pattern")


def test_commit_sha_must_be_40_hex_chars() -> None:
    outcome = _valid_outcome()
    outcome["commit_sha"] = "not-a-sha"

    errors = _errors(outcome)

    assert _has_error(errors, path=["commit_sha"], validator="pattern")


def test_gate_check_conclusion_accepts_all_expected_terminal_values() -> None:
    conclusions = [
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "startup_failure",
        "success",
        "timed_out",
    ]

    for conclusion in conclusions:
        outcome = _valid_outcome()
        outcome["gate_check_conclusion"] = conclusion

        assert _errors(outcome) == []


def test_gate_check_conclusion_rejects_unknown_value() -> None:
    outcome = _valid_outcome()
    outcome["gate_check_conclusion"] = "in_progress"

    errors = _errors(outcome)

    assert _has_error(errors, path=["gate_check_conclusion"], validator="enum")


def test_created_utc_is_required() -> None:
    outcome = _valid_outcome()
    outcome.pop("created_utc")

    errors = _errors(outcome)

    assert _has_error(errors, validator="required")


def test_authority_boundary_cannot_create_release_authority() -> None:
    outcome = _valid_outcome()
    outcome["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(outcome)

    assert _has_error(
        errors,
        path=["authority_boundary", "creates_release_authority"],
        validator="const",
    )


def test_authority_boundary_ci_role_is_fixed() -> None:
    outcome = _valid_outcome()
    outcome["authority_boundary"]["ci_role"] = "release_decision_engine"

    errors = _errors(outcome)

    assert _has_error(
        errors,
        path=["authority_boundary", "ci_role"],
        validator="const",
    )


def test_additional_top_level_property_fails() -> None:
    outcome = _valid_outcome()
    outcome["extra"] = "not allowed"

    errors = _errors(outcome)

    assert _has_error(errors, validator="additionalProperties")


def test_additional_authority_boundary_property_fails() -> None:
    outcome = _valid_outcome()
    outcome["authority_boundary"]["extra"] = "not allowed"

    errors = _errors(outcome)

    assert _has_error(
        errors,
        path=["authority_boundary"],
        validator="additionalProperties",
    )


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_ci_outcome_passes,
        test_run_attempt_is_required,
        test_run_attempt_must_be_positive,
        test_provider_is_fixed,
        test_schema_id_is_fixed,
        test_run_id_must_be_numeric_string,
        test_run_url_must_be_github_actions_run_url,
        test_repository_must_be_owner_repo,
        test_commit_sha_must_be_40_hex_chars,
        test_gate_check_conclusion_accepts_all_expected_terminal_values,
        test_gate_check_conclusion_rejects_unknown_value,
        test_created_utc_is_required,
        test_authority_boundary_cannot_create_release_authority,
        test_authority_boundary_ci_role_is_fixed,
        test_additional_top_level_property_fails,
        test_additional_authority_boundary_property_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 CI outcome schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
