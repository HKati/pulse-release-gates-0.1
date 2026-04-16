#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

CONTRACT_CHECKER_VERSION = "shadow_layer_registry_contract_v0"
EXPECTED_REGISTRY_VERSION = "shadow_layer_registry_v0"

CONTRACT_STAGES = {
    "research",
    "shadow-contracted",
    "advisory",
    "release-candidate",
    "release-required",
}
STAGE_ORDER = {
    "research": 0,
    "shadow-contracted": 1,
    "advisory": 2,
    "release-candidate": 3,
    "release-required": 4,
}
CONSUMER_AUTHORITIES = {
    "display-only",
    "review-only",
    "advisory-only",
    "policy-bound",
}
RUN_REALITY_STATES = {
    "real",
    "partial",
    "stub",
    "degraded",
    "invalid",
    "absent",
}
OWNER_SURFACES = {
    "docs",
    "workflow",
    "tool",
    "renderer",
}
HIGHER_STAGES = {
    "shadow-contracted",
    "advisory",
    "release-candidate",
    "release-required",
}

TOP_LEVEL_REQUIRED = {
    "version",
    "layers",
}
TOP_LEVEL_ALLOWED = set(TOP_LEVEL_REQUIRED)

LAYER_REQUIRED = {
    "layer_id",
    "family",
    "current_stage",
    "default_role",
    "consumer_authority",
    "run_reality_states",
    "normative",
    "notes",
}
LAYER_ALLOWED = LAYER_REQUIRED | {
    "target_stage",
    "owner_surface",
    "primary_entrypoint",
    "primary_artifact",
    "status_foldin",
    "schema",
    "semantic_checker",
    "fixtures",
    "valid_fixtures",
    "invalid_fixtures",
    "tests",
    "promotion_blockers",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_FOLDIN_RE = re.compile(r"^meta(?:\.[A-Za-z0-9_]+)+$")
LAYER_ID_RE = re.compile(r"^[a-z0-9_]+$")
FAMILY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _add_issue(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _check_required_and_extra_keys(
    obj: dict[str, Any],
    required: set[str],
    allowed: set[str],
    path: str,
    errors: list[dict[str, str]],
) -> None:
    for key in sorted(required):
        if key not in obj:
            _add_issue(errors, f"{path}.{key}" if path else key, f"missing required field: {key}")

    for key in sorted(obj.keys()):
        if key not in allowed:
            _add_issue(errors, f"{path}.{key}" if path else key, f"unexpected field: {key}")


def _validate_repo_relative_path(
    value: Any,
    *,
    path: str,
    errors: list[dict[str, str]],
    must_exist: bool,
) -> None:
    if not _is_non_empty_str(value):
        _add_issue(errors, path, f"{path} must be a non-empty repo-relative path string")
        return

    rel = Path(str(value))
    if rel.is_absolute():
        _add_issue(errors, path, f"{path} must be repo-relative, not absolute")
        return

    if any(part == ".." for part in rel.parts):
        _add_issue(errors, path, f"{path} must not contain '..' path traversal")
        return

    if must_exist and not (REPO_ROOT / rel).exists():
        _add_issue(errors, path, f"{path} does not exist in repository: {value}")


def _validate_non_empty_string_array(
    value: Any,
    *,
    path: str,
    errors: list[dict[str, str]],
) -> list[str] | None:
    if not isinstance(value, list):
        _add_issue(errors, path, f"{path} must be an array")
        return None
    if len(value) == 0:
        _add_issue(errors, path, f"{path} must not be empty")
        return None

    out: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(value):
        if not _is_non_empty_str(item):
            _add_issue(errors, f"{path}[{idx}]", f"{path} items must be non-empty strings")
            continue
        item_s = str(item)
        if item_s in seen:
            _add_issue(errors, f"{path}[{idx}]", f"duplicate item in {path}: {item_s}")
            continue
        seen.add(item_s)
        out.append(item_s)
    return out


def _validate_enum_string_array(
    value: Any,
    *,
    path: str,
    allowed: set[str],
    errors: list[dict[str, str]],
) -> list[str] | None:
    items = _validate_non_empty_string_array(value, path=path, errors=errors)
    if items is None:
        return None

    for idx, item in enumerate(items):
        if item not in allowed:
            _add_issue(
                errors,
                f"{path}[{idx}]",
                f"{path} items must be one of: {', '.join(sorted(allowed))}",
            )
    return items


def _load_registry(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ValueError(f"failed to read {path}: {exc}") from exc

    if path.suffix.lower() == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid registry syntax: {exc}") from exc

    if yaml is None:
        raise ValueError("PyYAML is required to read non-JSON shadow layer registry files")

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        raise ValueError(f"invalid registry syntax: {exc}") from exc


def validate_shadow_layer_registry(obj: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(obj, dict):
        _add_issue(errors, "$", "registry must be a mapping/object")
        return {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "registry_version": None,
            "layer_count": 0,
            "errors": errors,
            "warnings": warnings,
        }

    _check_required_and_extra_keys(
        obj=obj,
        required=TOP_LEVEL_REQUIRED,
        allowed=TOP_LEVEL_ALLOWED,
        path="",
        errors=errors,
    )

    version = obj.get("version")
    if not _is_non_empty_str(version):
        _add_issue(errors, "version", "version must be a non-empty string")
    elif version != EXPECTED_REGISTRY_VERSION:
        _add_issue(
            errors,
            "version",
            f"version must equal {EXPECTED_REGISTRY_VERSION!r}",
        )

    layers = obj.get("layers")
    if not isinstance(layers, list):
        _add_issue(errors, "layers", "layers must be an array")
        layers = []
    elif len(layers) == 0:
        _add_issue(errors, "layers", "layers must not be empty")

    seen_layer_ids: dict[str, int] = {}

    for idx, layer in enumerate(layers):
        path_prefix = f"layers[{idx}]"

        if not isinstance(layer, dict):
            _add_issue(errors, path_prefix, "layer entry must be an object")
            continue

        _check_required_and_extra_keys(
            obj=layer,
            required=LAYER_REQUIRED,
            allowed=LAYER_ALLOWED,
            path=path_prefix,
            errors=errors,
        )

        layer_id = layer.get("layer_id")
        if not _is_non_empty_str(layer_id):
            _add_issue(errors, f"{path_prefix}.layer_id", "layer_id must be a non-empty string")
            layer_id_s = None
        else:
            layer_id_s = str(layer_id)
            if LAYER_ID_RE.fullmatch(layer_id_s) is None:
                _add_issue(
                    errors,
                    f"{path_prefix}.layer_id",
                    "layer_id must match ^[a-z0-9_]+$",
                )
            if layer_id_s in seen_layer_ids:
                _add_issue(
                    errors,
                    f"{path_prefix}.layer_id",
                    f"duplicate layer_id: {layer_id_s} (already used by layers[{seen_layer_ids[layer_id_s]}])",
                )
            else:
                seen_layer_ids[layer_id_s] = idx

        family = layer.get("family")
        if not _is_non_empty_str(family):
            _add_issue(errors, f"{path_prefix}.family", "family must be a non-empty string")
        elif FAMILY_RE.fullmatch(str(family)) is None:
            _add_issue(
                errors,
                f"{path_prefix}.family",
                "family must match ^[a-z0-9][a-z0-9_-]*$",
            )

        current_stage = layer.get("current_stage")
        if current_stage not in CONTRACT_STAGES:
            _add_issue(
                errors,
                f"{path_prefix}.current_stage",
                f"current_stage must be one of: {', '.join(sorted(CONTRACT_STAGES))}",
            )
            current_stage_s: str | None = None
        else:
            current_stage_s = str(current_stage)

        if "target_stage" in layer:
            target_stage = layer.get("target_stage")
            if target_stage not in CONTRACT_STAGES:
                _add_issue(
                    errors,
                    f"{path_prefix}.target_stage",
                    f"target_stage must be one of: {', '.join(sorted(CONTRACT_STAGES))}",
                )
            elif current_stage_s is not None:
                current_rank = STAGE_ORDER[current_stage_s]
                target_rank = STAGE_ORDER[str(target_stage)]
                if target_rank < current_rank:
                    _add_issue(
                        errors,
                        f"{path_prefix}.target_stage",
                        "target_stage must not be lower than current_stage",
                    )
                elif target_rank == current_rank:
                    _add_issue(
                        warnings,
                        f"{path_prefix}.target_stage",
                        "target_stage is identical to current_stage",
                    )

        if not _is_non_empty_str(layer.get("default_role")):
            _add_issue(errors, f"{path_prefix}.default_role", "default_role must be a non-empty string")

        consumer_authority = layer.get("consumer_authority")
        if consumer_authority not in CONSUMER_AUTHORITIES:
            _add_issue(
                errors,
                f"{path_prefix}.consumer_authority",
                f"consumer_authority must be one of: {', '.join(sorted(CONSUMER_AUTHORITIES))}",
            )

        if "owner_surface" in layer:
            _validate_enum_string_array(
                layer.get("owner_surface"),
                path=f"{path_prefix}.owner_surface",
                allowed=OWNER_SURFACES,
                errors=errors,
            )

        if "primary_entrypoint" in layer:
            _validate_repo_relative_path(
                layer.get("primary_entrypoint"),
                path=f"{path_prefix}.primary_entrypoint",
                errors=errors,
                must_exist=True,
            )

        if "primary_artifact" in layer:
            _validate_repo_relative_path(
                layer.get("primary_artifact"),
                path=f"{path_prefix}.primary_artifact",
                errors=errors,
                must_exist=False,
            )

        if "status_foldin" in layer:
            status_foldin = layer.get("status_foldin")
            if not _is_non_empty_str(status_foldin):
                _add_issue(
                    errors,
                    f"{path_prefix}.status_foldin",
                    "status_foldin must be a non-empty dotted path string",
                )
            elif STATUS_FOLDIN_RE.fullmatch(str(status_foldin)) is None:
                _add_issue(
                    errors,
                    f"{path_prefix}.status_foldin",
                    "status_foldin must match ^meta(?:\\.[A-Za-z0-9_]+)+$",
                )

        if "schema" in layer:
            _validate_repo_relative_path(
                layer.get("schema"),
                path=f"{path_prefix}.schema",
                errors=errors,
                must_exist=True,
            )

        if "semantic_checker" in layer:
            _validate_repo_relative_path(
                layer.get("semantic_checker"),
                path=f"{path_prefix}.semantic_checker",
                errors=errors,
                must_exist=True,
            )

        fixtures: list[str] | None = None
        valid_fixtures: list[str] | None = None
        invalid_fixtures: list[str] | None = None

        if "fixtures" in layer:
            fixtures = _validate_non_empty_string_array(
                layer.get("fixtures"),
                path=f"{path_prefix}.fixtures",
                errors=errors,
            )
            if fixtures is not None:
                for fixture_idx, fixture in enumerate(fixtures):
                    _validate_repo_relative_path(
                        fixture,
                        path=f"{path_prefix}.fixtures[{fixture_idx}]",
                        errors=errors,
                        must_exist=True,
                    )

        if "valid_fixtures" in layer:
            valid_fixtures = _validate_non_empty_string_array(
                layer.get("valid_fixtures"),
                path=f"{path_prefix}.valid_fixtures",
                errors=errors,
            )
            if valid_fixtures is not None:
                for fixture_idx, fixture in enumerate(valid_fixtures):
                    _validate_repo_relative_path(
                        fixture,
                        path=f"{path_prefix}.valid_fixtures[{fixture_idx}]",
                        errors=errors,
                        must_exist=True,
                    )

        if "invalid_fixtures" in layer:
            invalid_fixtures = _validate_non_empty_string_array(
                layer.get("invalid_fixtures"),
                path=f"{path_prefix}.invalid_fixtures",
                errors=errors,
            )
            if invalid_fixtures is not None:
                for fixture_idx, fixture in enumerate(invalid_fixtures):
                    _validate_repo_relative_path(
                        fixture,
                        path=f"{path_prefix}.invalid_fixtures[{fixture_idx}]",
                        errors=errors,
                        must_exist=True,
                    )

        if valid_fixtures is not None and invalid_fixtures is not None:
            overlap = sorted(set(valid_fixtures) & set(invalid_fixtures))
            for item in overlap:
                _add_issue(
                    errors,
                    f"{path_prefix}.invalid_fixtures",
                    f"fixture must not appear in both valid_fixtures and invalid_fixtures: {item}",
                )

        if "tests" in layer:
            tests = _validate_non_empty_string_array(
                layer.get("tests"),
                path=f"{path_prefix}.tests",
                errors=errors,
            )
            if tests is not None:
                for test_idx, test_path in enumerate(tests):
                    _validate_repo_relative_path(
                        test_path,
                        path=f"{path_prefix}.tests[{test_idx}]",
                        errors=errors,
                        must_exist=True,
                    )

        run_reality_states = _validate_enum_string_array(
            layer.get("run_reality_states"),
            path=f"{path_prefix}.run_reality_states",
            allowed=RUN_REALITY_STATES,
            errors=errors,
        )

        if "promotion_blockers" in layer:
            _validate_non_empty_string_array(
                layer.get("promotion_blockers"),
                path=f"{path_prefix}.promotion_blockers",
                errors=errors,
            )

        normative = layer.get("normative")
        if not isinstance(normative, bool):
            _add_issue(errors, f"{path_prefix}.normative", "normative must be a boolean")

        if not _is_non_empty_str(layer.get("notes")):
            _add_issue(errors, f"{path_prefix}.notes", "notes must be a non-empty string")

        if current_stage_s in HIGHER_STAGES:
            for required_field in (
                "primary_entrypoint",
                "primary_artifact",
                "schema",
                "semantic_checker",
                "tests",
            ):
                if required_field not in layer:
                    _add_issue(
                        errors,
                        f"{path_prefix}.{required_field}",
                        f"{required_field} is required when current_stage is {current_stage_s}",
                    )

            if "fixtures" not in layer and "valid_fixtures" not in layer:
                _add_issue(
                    errors,
                    f"{path_prefix}.valid_fixtures",
                    f"fixtures or valid_fixtures is required when current_stage is {current_stage_s}",
                )

        if normative is True and current_stage_s != "release-required":
            _add_issue(
                errors,
                f"{path_prefix}.current_stage",
                "normative=true requires current_stage=release-required",
            )

        if current_stage_s == "release-required" and normative is not True:
            _add_issue(
                errors,
                f"{path_prefix}.normative",
                "current_stage=release-required requires normative=true",
            )

        if current_stage_s == "research" and run_reality_states is not None and len(run_reality_states) == 0:
            _add_issue(
                errors,
                f"{path_prefix}.run_reality_states",
                "run_reality_states must not be empty",
            )

    return {
        "ok": len(errors) == 0,
        "neutral": False,
        "contract_checker_version": CONTRACT_CHECKER_VERSION,
        "registry_version": version if _is_non_empty_str(version) else None,
        "layer_count": len(layers),
        "errors": errors,
        "warnings": warnings,
    }


def _write_result(result: dict[str, Any], output_path: Path | None) -> None:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output_path is not None:
        output_path.write_text(rendered + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the shadow layer registry contract.",
    )
    parser.add_argument("--input", required=True, help="Path to the registry YAML or JSON file.")
    parser.add_argument("--output", help="Optional path to write the checker result JSON.")
    parser.add_argument(
        "--if-input-present",
        action="store_true",
        help="Treat missing input as neutral success.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        result = {
            "ok": bool(args.if_input_present),
            "neutral": bool(args.if_input_present),
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "registry_version": None,
            "layer_count": 0,
            "errors": [] if args.if_input_present else [{"path": "input", "message": "input registry not found"}],
            "warnings": (
                [{"path": "input", "message": "input registry not found; neutral absence preserved"}]
                if args.if_input_present
                else []
            ),
        }
        _write_result(result, output_path)
        return 0 if args.if_input_present else 1

    try:
        obj = _load_registry(input_path)
    except ValueError as exc:
        result = {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "registry_version": None,
            "layer_count": 0,
            "errors": [{"path": "input", "message": str(exc)}],
            "warnings": [],
        }
        _write_result(result, output_path)
        return 1

    result = validate_shadow_layer_registry(obj)
    _write_result(result, output_path)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
