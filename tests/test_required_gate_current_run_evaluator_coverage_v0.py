#!/usr/bin/env python3
"""Lock release-grade required-gate evaluator coverage.

The controlled strict release-grade run failed before status.json because the
required-gate evidence producer correctly failed closed for required gates that
still had no dedicated current-run evaluator.

This test locks the next mechanical requirement:

    every gate in pulse_gate_policy_v0.yml:gates.required
    must have a dedicated checked-in current-run evaluator recipe.

It does not require removing the unsupported/fail-closed helper entirely. That
helper may remain for unknown or future gates. The invariant is narrower:
nothing in the normative release-grade required set may still route through the
unsupported fallback.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "pulse_gate_policy_v0.yml"
PLAN_PATH = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "profiles"
    / "required_gate_evaluations_v0.json"
)
EVALUATOR_PATH = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "evaluate_required_gate_v0.py"
)

TEST_PATH = (
    "tests/test_required_gate_current_run_evaluator_coverage_v0.py"
)
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

FAILED_GATE_IDS_FROM_DIAGNOSTIC_RUN = {
    "effect_present",
    "pass_controls_comm",
    "psf_action_monotonicity_ok",
    "psf_comm_shift_resilient",
    "psf_commutativity_ok",
    "psf_idempotence_ok",
    "psf_mono_shift_resilient",
    "psf_monotonicity_ok",
    "psf_path_independence_ok",
    "psf_pii_monotonicity_ok",
    "q2_consistency_ok",
    "q3_fairness_ok",
    "sanit_shift_resilient",
}


def _load_policy_required_gates() -> list[str]:
    assert POLICY_PATH.is_file(), f"missing policy: {POLICY_PATH}"

    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "policy must be a mapping"

    gates = payload.get("gates")
    assert isinstance(gates, dict), "policy must contain gates mapping"

    required = gates.get("required")
    assert isinstance(required, list), "gates.required must be a list"
    assert required, "gates.required must not be empty"

    result: list[str] = []
    seen: set[str] = set()

    for item in required:
        assert isinstance(item, str) and item, (
            f"required gate ID must be a non-empty string: {item!r}"
        )
        assert item not in seen, f"duplicate required gate ID: {item}"
        seen.add(item)
        result.append(item)

    return result


def _load_evaluator_module() -> Any:
    assert EVALUATOR_PATH.is_file(), (
        f"missing required-gate evaluator: {EVALUATOR_PATH}"
    )

    spec = importlib.util.spec_from_file_location(
        "pulse_required_gate_evaluator_under_test",
        EVALUATOR_PATH,
    )
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repo_relative_path(raw: str) -> Path:
    assert isinstance(raw, str) and raw, (
        f"path must be a non-empty string: {raw!r}"
    )
    path = Path(raw)
    assert not path.is_absolute(), f"path must be repository-relative: {raw!r}"

    resolved = (REPO_ROOT / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise AssertionError(f"path escapes repository root: {raw!r}") from exc

    return resolved


def _recipe_paths(recipe: Any) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = [
        ("builder", recipe.builder),
    ]

    for source_name, source_path in recipe.sources:
        paths.append((f"source:{source_name}", source_path))

    for index, extra_path in enumerate(recipe.extra_inputs):
        paths.append((f"extra_input:{index}", extra_path))

    return paths


def test_every_required_gate_has_dedicated_current_run_recipe() -> None:
    required = set(_load_policy_required_gates())
    module = _load_evaluator_module()

    recipes = getattr(module, "RECIPES", None)
    assert isinstance(recipes, dict), "evaluator must expose RECIPES mapping"

    unsupported_reasons = getattr(module, "UNSUPPORTED_REASONS", None)
    assert isinstance(unsupported_reasons, dict), (
        "evaluator must expose UNSUPPORTED_REASONS mapping"
    )

    missing_recipes = sorted(required - set(recipes))
    assert not missing_recipes, (
        "every gates.required entry must have a dedicated current-run "
        f"evaluator recipe; missing: {missing_recipes}"
    )

    required_still_unsupported = sorted(required & set(unsupported_reasons))
    assert not required_still_unsupported, (
        "no gates.required entry may remain routed through the unsupported "
        f"fallback; still unsupported: {required_still_unsupported}"
    )


def test_previous_failed_required_gates_are_now_recipe_backed() -> None:
    module = _load_evaluator_module()

    recipes = getattr(module, "RECIPES", {})
    unsupported_reasons = getattr(module, "UNSUPPORTED_REASONS", {})

    missing = sorted(FAILED_GATE_IDS_FROM_DIAGNOSTIC_RUN - set(recipes))
    unsupported = sorted(
        FAILED_GATE_IDS_FROM_DIAGNOSTIC_RUN & set(unsupported_reasons)
    )

    assert not missing, (
        "the gates that failed in the controlled strict release-grade "
        f"diagnostic run must now be recipe-backed; missing: {missing}"
    )
    assert not unsupported, (
        "the gates that failed in the controlled strict release-grade "
        f"diagnostic run must no longer be unsupported: {unsupported}"
    )


def test_required_gate_recipes_are_checked_in_and_non_symlinked() -> None:
    required = _load_policy_required_gates()
    module = _load_evaluator_module()
    recipes = getattr(module, "RECIPES", {})

    for gate_id in required:
        recipe = recipes.get(gate_id)
        assert recipe is not None, f"missing recipe for {gate_id}"

        for label, raw_path in _recipe_paths(recipe):
            path = _repo_relative_path(raw_path)

            assert path.is_file(), (
                f"{gate_id} recipe {label} must be a checked-in file: "
                f"{raw_path}"
            )
            assert not path.is_symlink(), (
                f"{gate_id} recipe {label} must not be a symlink: "
                f"{raw_path}"
            )


def test_required_gate_plan_remains_exactly_policy_required() -> None:
    required = set(_load_policy_required_gates())
    assert PLAN_PATH.is_file(), f"missing required-gate plan: {PLAN_PATH}"

    import json

    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "required_gate_evaluation_plan_v0"

    evaluations = payload.get("evaluations")
    assert isinstance(evaluations, dict), "plan.evaluations must be an object"

    planned = set(evaluations)

    missing = sorted(required - planned)
    extra = sorted(planned - required)

    assert not missing, f"plan is missing required gates: {missing}"
    assert not extra, f"plan contains non-required gates: {extra}"

    for gate_id, entry in sorted(evaluations.items()):
        assert isinstance(entry, dict), f"{gate_id} plan entry must be object"

        command = entry.get("command")
        assert isinstance(command, list), f"{gate_id} command must be list"
        assert command[:2] == [
            "{python}",
            "PULSE_safe_pack_v0/tools/evaluate_required_gate_v0.py",
        ], f"{gate_id} must invoke the canonical dispatcher"

        assert "require-dedicated-current-run-evaluator" not in command, (
            f"{gate_id} plan must not invoke unsupported fallback directly"
        )

        result = entry.get("result")
        assert isinstance(result, dict), f"{gate_id} result must be object"
        assert result.get("json_pointer") == "/pass", (
            f"{gate_id} result must bind to /pass"
        )


def test_required_gate_current_run_evaluator_coverage_smoke_registered() -> None:
    assert TOOLS_TESTS_LIST.is_file(), (
        f"missing tools-test manifest: {TOOLS_TESTS_LIST}"
    )

    entries = [
        line.strip()
        for line in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert entries.count(TEST_PATH) == 1, (
        f"{TEST_PATH} must appear exactly once in ci/tools-tests.list"
    )


def main() -> int:
    test_every_required_gate_has_dedicated_current_run_recipe()
    test_previous_failed_required_gates_are_now_recipe_backed()
    test_required_gate_recipes_are_checked_in_and_non_symlinked()
    test_required_gate_plan_remains_exactly_policy_required()
    test_required_gate_current_run_evaluator_coverage_smoke_registered()
    print("OK: required-gate current-run evaluator coverage locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
