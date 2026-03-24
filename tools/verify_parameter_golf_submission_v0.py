#!/usr/bin/env python3
"""Validate a Parameter Golf evidence artifact against the v0 shadow contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "parameter_golf_submission_evidence_v0.schema.json"
)


def _decode_json_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _resolve_local_anchor(
    schema_root: dict[str, Any] | bool,
    anchor: str,
) -> Any | None:
    """Resolve a local $anchor / $dynamicAnchor like '#artifact'."""

    if not isinstance(schema_root, dict):
        return None

    def walk(node: Any) -> Any | None:
        if isinstance(node, dict):
            if node.get("$anchor") == anchor or node.get("$dynamicAnchor") == anchor:
                return node
            for value in node.values():
                found = walk(value)
                if found is not None:
                    return found
            return None

        if isinstance(node, list):
            for item in node:
                found = walk(item)
                if found is not None:
                    return found

        return None

    return walk(schema_root)


def _resolve_local_ref(
    schema_root: dict[str, Any] | bool,
    ref: str,
) -> Any | None:
    """Resolve a local JSON Pointer or local anchor ref against the selected schema."""
    if not isinstance(schema_root, dict):
        return None

    if ref == "#":
        return schema_root

    if ref.startswith("#/"):
        current: Any = schema_root
        for raw_token in ref[2:].split("/"):
            token = _decode_json_pointer_token(raw_token)

            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
                continue

            if isinstance(current, list):
                try:
                    index = int(token)
                except ValueError:
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue

            return None

        return current

    if ref.startswith("#") and len(ref) > 1:
        return _resolve_local_anchor(schema_root, ref[1:])

    return None


def _branch_matches_instance(
    branch_schema: Any,
    instance: Any,
    schema_root: dict[str, Any] | bool,
    jsonschema_mod: Any | None,
) -> bool:
    """Return True only when a union branch matches the current instance."""
    if isinstance(branch_schema, bool):
        return branch_schema

    if not isinstance(branch_schema, dict) or jsonschema_mod is None:
        return False

    try:
        validator_cls = jsonschema_mod.validators.validator_for(schema_root)
        validator_cls.check_schema(schema_root)
        root_validator = validator_cls(schema_root)

        if hasattr(root_validator, "evolve"):
            return root_validator.evolve(schema=branch_schema).is_valid(instance)

        # Fallback for older validator implementations.
        return validator_cls(branch_schema).is_valid(instance)
    except Exception:
        return False


def _iter_composed_subschemas(
    schema_node: Any,
    schema_root: dict[str, Any] | bool,
    instance: Any = None,
    jsonschema_mod: Any | None = None,
    seen_refs: set[str] | None = None,
):
    """Yield a schema node plus locally composed/ref-resolved subschemas."""
    if seen_refs is None:
        seen_refs = set()

    if isinstance(schema_node, bool):
        yield schema_node
        return

    if not isinstance(schema_node, dict):
        return

    yield schema_node

    ref = schema_node.get("$ref")
    if isinstance(ref, str) and ref not in seen_refs:
        target = _resolve_local_ref(schema_root, ref)
        if target is not None:
            yield from _iter_composed_subschemas(
                target,
                schema_root,
                instance=instance,
                jsonschema_mod=jsonschema_mod,
                seen_refs=seen_refs | {ref},
            )

    branch = schema_node.get("allOf")
    if isinstance(branch, list):
        for item in branch:
            yield from _iter_composed_subschemas(
                item,
                schema_root,
                instance=instance,
                jsonschema_mod=jsonschema_mod,
                seen_refs=seen_refs,
            )

    for key in ("anyOf", "oneOf"):
        branch = schema_node.get(key)
        if isinstance(branch, list) and jsonschema_mod is not None:
            for item in branch:
                if _branch_matches_instance(item, instance, schema_root, jsonschema_mod):
                    yield from _iter_composed_subschemas(
                        item,
                        schema_root,
                        instance=instance,
                        jsonschema_mod=jsonschema_mod,
                        seen_refs=seen_refs,
                    )


def _collect_property_schemas(
    schema_node: Any,
    property_name: str,
    schema_root: dict[str, Any] | bool,
    instance: Any = None,
    jsonschema_mod: Any | None = None,
) -> list[Any]:
    matches: list[Any] = []
    for node in _iter_composed_subschemas(
        schema_node,
        schema_root,
        instance=instance,
        jsonschema_mod=jsonschema_mod,
    ):
        if not isinstance(node, dict):
            continue
        props = node.get("properties")
        if isinstance(props, dict) and property_name in props:
            matches.append(props[property_name])
    return matches


def resolve_artifact_limit_default(
    schema: dict[str, Any] | bool,
    evidence: dict[str, Any] | None = None,
    jsonschema_mod: Any | None = None,
) -> int | None:
    """Resolve artifact.artifact_limit_bytes.default for the current evidence instance.

    Direct properties, local $ref, local anchors, and allOf are always followed.
    anyOf / oneOf branches are only considered when they match the current
    evidence instance.
    """
    if not isinstance(schema, dict):
        return None

    artifact_instance = None
    if isinstance(evidence, dict):
        artifact_instance = evidence.get("artifact")

    defaults: list[int] = []

    artifact_schemas = _collect_property_schemas(
        schema,
        "artifact",
        schema,
        instance=evidence,
        jsonschema_mod=jsonschema_mod,
    )
    for artifact_schema in artifact_schemas:
        limit_schemas = _collect_property_schemas(
            artifact_schema,
            "artifact_limit_bytes",
            schema,
            instance=artifact_instance,
            jsonschema_mod=jsonschema_mod,
        )
        for limit_schema in limit_schemas:
            if not isinstance(limit_schema, dict):
                continue
            default_value = limit_schema.get("default")
            if isinstance(default_value, int):
                defaults.append(default_value)

    unique_defaults = list(dict.fromkeys(defaults))
    if len(unique_defaults) == 1:
        return unique_defaults[0]

    return None


class MissingDependencyError(RuntimeError):
    """Raised when an optional runtime dependency is unavailable."""


def _load_jsonschema() -> Any:
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError as exc:
        raise MissingDependencyError(
            "Missing dependency: 'jsonschema'.\n"
            "Install it with: pip install jsonschema"
        ) from exc
    return jsonschema


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(
    evidence: dict[str, Any],
    schema: dict[str, Any] | bool,
    jsonschema_mod: Any,
) -> None:
    if not isinstance(schema, (dict, bool)):
        raise jsonschema_mod.SchemaError(
            "Provided schema must be a JSON object or boolean schema"
        )

    try:
        validator_cls = jsonschema_mod.validators.validator_for(schema)
    except TypeError as exc:
        raise jsonschema_mod.SchemaError(f"Provided schema is invalid: {exc}") from exc

    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    validator.validate(evidence)


def semantic_checks(
    evidence: dict[str, Any],
    artifact_limit_default: int | None = None,
) -> list[str]:
    warnings: list[str] = []

    artifact = evidence.get("artifact", {})
    code_bytes = artifact.get("code_bytes")
    model_bytes = artifact.get("model_bytes_int8_zlib")
    total_bytes = artifact.get("total_bytes_int8_zlib")
    declared_limit_bytes = artifact.get("artifact_limit_bytes")
    tokenizer_counted = artifact.get("tokenizer_counted")
    tokenizer_bytes = artifact.get("tokenizer_bytes_if_counted")

    effective_limit_bytes: int | None = None
    limit_is_defaulted = False
    if isinstance(declared_limit_bytes, int):
        effective_limit_bytes = declared_limit_bytes
    elif declared_limit_bytes is None and isinstance(artifact_limit_default, int):
        effective_limit_bytes = artifact_limit_default
        limit_is_defaulted = True

    expected_total: int | None = None
    if isinstance(code_bytes, int) and isinstance(model_bytes, int):
        expected_total = code_bytes + model_bytes

        if tokenizer_counted is True:
            if isinstance(tokenizer_bytes, int):
                expected_total += tokenizer_bytes
            else:
                warnings.append(
                    "tokenizer_counted is true but tokenizer_bytes_if_counted is missing/non-integer"
                )
                expected_total = None

    if expected_total is not None and isinstance(total_bytes, int):
        if total_bytes != expected_total:
            if tokenizer_counted is True:
                warnings.append(
                    "artifact.total_bytes_int8_zlib does not equal "
                    "artifact.code_bytes + artifact.model_bytes_int8_zlib + "
                    "artifact.tokenizer_bytes_if_counted"
                )
            else:
                warnings.append(
                    "artifact.total_bytes_int8_zlib does not equal "
                    "artifact.code_bytes + artifact.model_bytes_int8_zlib"
                )

    if (
        isinstance(total_bytes, int)
        and isinstance(effective_limit_bytes, int)
        and total_bytes > effective_limit_bytes
    ):
        if limit_is_defaulted:
            warnings.append(
                f"artifact total ({total_bytes}) exceeds effective schema-default limit ({effective_limit_bytes})"
            )
        else:
            warnings.append(
                f"artifact total ({total_bytes}) exceeds declared limit ({effective_limit_bytes})"
            )

    if tokenizer_counted is False and tokenizer_bytes in (None, 0):
        warnings.append(
            "tokenizer_counted is false but tokenizer_bytes_if_counted is missing/zero; "
            "advisory visibility is reduced"
        )

    train = evidence.get("train", {})
    train_wallclock_s = train.get("train_wallclock_s")
    max_wallclock_s = train.get("max_wallclock_s")
    if (
        isinstance(train_wallclock_s, (int, float))
        and isinstance(max_wallclock_s, (int, float))
        and train_wallclock_s > max_wallclock_s
    ):
        warnings.append(
            f"train wallclock ({train_wallclock_s}) exceeds declared max ({max_wallclock_s})"
        )

    evaluation = evidence.get("evaluation", {})
    mode = evaluation.get("mode")
    stride = evaluation.get("stride")
    val_bpb = evaluation.get("val_bpb")

    if mode == "sliding_window" and stride in (None, 0):
        warnings.append("evaluation.mode is sliding_window but stride is missing")

    if mode == "standard" and stride not in (None,):
        warnings.append("evaluation.mode is standard but stride is present")

    if val_bpb is None:
        warnings.append("evaluation.val_bpb is missing")

    stats = evidence.get("stats", {})
    run_logs = stats.get("run_logs") or []
    n_runs = stats.get("n_runs")
    p_value = stats.get("p_value")
    exemption = stats.get("claim_exemption_reason")

    if p_value is not None and n_runs is None:
        warnings.append("stats.p_value is present but stats.n_runs is missing")

    if isinstance(n_runs, int) and len(run_logs) > 0 and len(run_logs) != n_runs:
        warnings.append(
            f"stats.n_runs ({n_runs}) does not match number of run_logs ({len(run_logs)})"
        )

    if evidence.get("submission_type") == "record":
        if not run_logs and not exemption:
            warnings.append(
                "record submission has neither run_logs nor claim_exemption_reason"
            )

    return warnings


def build_summary(
    evidence: dict[str, Any],
    warnings: list[str],
    artifact_limit_default: int | None = None,
) -> dict[str, Any]:
    artifact = evidence.get("artifact", {})
    evaluation = evidence.get("evaluation", {})

    declared_limit_bytes = artifact.get("artifact_limit_bytes")
    effective_limit_bytes = (
        declared_limit_bytes
        if isinstance(declared_limit_bytes, int)
        else artifact_limit_default
    )

    return {
        "valid_schema": True,
        "warning_count": len(warnings),
        "warnings": warnings,
        "summary": {
            "submission_type": evidence.get("submission_type"),
            "total_bytes_int8_zlib": artifact.get("total_bytes_int8_zlib"),
            "artifact_limit_bytes": effective_limit_bytes,
            "artifact_limit_bytes_declared": declared_limit_bytes,
            "evaluation_mode": evaluation.get("mode"),
            "val_bpb": evaluation.get("val_bpb"),
        },
    }


def emit_invalid_result(
    *,
    as_json: bool,
    error_kind: str,
    message: str,
    path_key: str | None = None,
    path_value: list[Any] | None = None,
) -> None:
    if as_json:
        payload: dict[str, Any] = {
            "valid_schema": False,
            "error_kind": error_kind,
            "error": message,
        }
        if path_key is not None and path_value is not None:
            payload[path_key] = path_value
        print(json.dumps(payload, indent=2))
        return

    print("INVALID")
    print(message)
    if path_key is not None and path_value is not None:
        label = "schema path" if path_key == "schema_path" else "path"
        rendered_path = "/".join(map(str, path_value)) if path_value else ""
        print(f"At {label}: {rendered_path}")


def emit_load_error(*, as_json: bool, error_kind: str, message: str) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "valid_schema": False,
                    "error_kind": error_kind,
                    "error": message,
                },
                indent=2,
            )
        )
    else:
        print(f"ERROR: {message}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Parameter Golf evidence artifact."
    )
    parser.add_argument("--evidence", required=True, help="Path to evidence JSON.")
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to schema JSON. Defaults to the repo-local v0 schema.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat semantic warnings as a non-zero exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a structured JSON result instead of a text summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)
    schema_path = Path(args.schema)

    try:
        evidence = load_json(evidence_path)
    except FileNotFoundError:
        emit_load_error(
            as_json=args.json,
            error_kind="evidence_file_not_found",
            message=f"evidence file not found: {evidence_path}",
        )
        return 1
    except json.JSONDecodeError as exc:
        emit_load_error(
            as_json=args.json,
            error_kind="evidence_json_decode_error",
            message=f"invalid JSON in evidence file: {exc}",
        )
        return 1

    try:
        schema = load_json(schema_path)
    except FileNotFoundError:
        emit_load_error(
            as_json=args.json,
            error_kind="schema_file_not_found",
            message=f"schema file not found: {schema_path}",
        )
        return 1
    except json.JSONDecodeError as exc:
        emit_load_error(
            as_json=args.json,
            error_kind="schema_json_decode_error",
            message=f"invalid JSON in schema file: {exc}",
        )
        return 1

    try:
        jsonschema_mod = _load_jsonschema()
    except MissingDependencyError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "valid_schema": False,
                        "error_kind": "missing_dependency",
                        "error": str(exc),
                    },
                    indent=2,
                )
            )
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        validate_schema(evidence, schema, jsonschema_mod)
    except jsonschema_mod.ValidationError as exc:
        emit_invalid_result(
            as_json=args.json,
            error_kind="validation_error",
            message=f"Schema validation failed: {exc.message}",
            path_key="path",
            path_value=list(exc.absolute_path),
        )
        return 1
    except jsonschema_mod.SchemaError as exc:
        emit_invalid_result(
            as_json=args.json,
            error_kind="schema_error",
            message=f"Provided schema is invalid: {exc.message}",
            path_key="schema_path",
            path_value=list(exc.absolute_schema_path),
        )
        return 1

    artifact_limit_default = resolve_artifact_limit_default(
        schema,
        evidence=evidence,
        jsonschema_mod=jsonschema_mod,
    )

    warnings = semantic_checks(
        evidence,
        artifact_limit_default=artifact_limit_default,
    )
    result = build_summary(
        evidence,
        warnings,
        artifact_limit_default=artifact_limit_default,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        artifact_total = result["summary"]["total_bytes_int8_zlib"]
        artifact_limit = result["summary"]["artifact_limit_bytes"]
        artifact_limit_declared = result["summary"]["artifact_limit_bytes_declared"]

        if artifact_limit_declared is None and artifact_limit is None:
            bytes_fragment = (
                f"{artifact_total} "
                "(artifact_limit_bytes undeclared; selected schema has no default)"
            )
        elif artifact_limit_declared is None:
            bytes_fragment = (
                f"{artifact_total}/{artifact_limit} "
                "(effective schema default; artifact_limit_bytes undeclared)"
            )
        else:
            bytes_fragment = f"{artifact_total}/{artifact_limit}"

        print("VALID")
        print(
            "Submission type: "
            f"{result['summary']['submission_type']} | "
            "mode: "
            f"{result['summary']['evaluation_mode']} | "
            "val_bpb: "
            f"{result['summary']['val_bpb']} | "
            "bytes: "
            f"{bytes_fragment}"
        )

        if warnings:
            print("Warnings:")
            for item in warnings:
                print(f"- {item}")
        else:
            print("No semantic warnings.")

    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
