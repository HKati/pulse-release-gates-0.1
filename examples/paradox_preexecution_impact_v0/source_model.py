#!/usr/bin/env python3
"""PD-SM-02 closed source recognizer and relational model extractor.

The module parses a deliberately small Python syntax profile.  It never imports
or executes candidate code and it does not emit an impact verdict.  Its output
is an auditable source-derived model for the independent checker.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


MODEL_SCHEMA = "pd_sm_02_source_model_v0"


class ModelError(ValueError):
    """Typed fail-closed source/model error."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ModelError("duplicate_json_key", key)
        out[key] = value
    return out


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ModelError("non_finite_json_number", value)
            ),
        )
    except UnicodeDecodeError as exc:
        raise ModelError("json_not_utf8", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise ModelError("invalid_json", str(exc)) from exc


def canonical_bytes(value: Any) -> bytes:
    def reject_nonfinite(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ModelError("non_finite_value")
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise ModelError("non_string_json_key")
                reject_nonfinite(nested)
        elif isinstance(item, list):
            for nested in item:
                reject_nonfinite(nested)

    reject_nonfinite(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ModelError(code, detail)


def _validate_profile(profile: dict[str, Any]) -> None:
    _require(profile.get("schema_version") == "pd_sm_02_profile_v0", "profile_schema")
    _require(profile.get("profile_id") == "PD-SM-02-preexecution-impact-v0", "profile_id")
    language = profile.get("candidate_language")
    _require(isinstance(language, dict), "candidate_language")
    primitives = language.get("primitives")
    _require(isinstance(primitives, dict) and primitives, "primitive_contract")
    domains = profile.get("domains")
    _require(isinstance(domains, dict), "domain_contract")
    for name, spec in primitives.items():
        _require(isinstance(name, str) and name.isidentifier(), "primitive_name", str(name))
        _require(isinstance(spec, dict), "primitive_spec", name)
        _require(isinstance(spec.get("arity"), int) and spec["arity"] >= 0, "primitive_arity", name)
        arg_domains = spec.get("arg_domains")
        _require(isinstance(arg_domains, list) and len(arg_domains) == spec["arity"], "primitive_domains", name)
        for domain in arg_domains:
            _require(domain in domains and isinstance(domains[domain], list), "unknown_domain", str(domain))


def _resolve_arg(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in aliases:
        return aliases[node.id]
    raise ModelError("unsupported_call_argument", f"line {getattr(node, 'lineno', '?')}")


def _source_segment(source_text: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source_text, node)
    return segment if segment is not None else ""


def parse_candidate(source: bytes, profile: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Return normalized primitive operations and private constant aliases."""
    _validate_profile(profile)
    language = profile["candidate_language"]
    _require(len(source) <= language["max_source_bytes"], "source_too_large")
    _require(not source.startswith(b"\xef\xbb\xbf"), "utf8_bom_not_allowed")
    if language.get("final_newline_required"):
        _require(source.endswith(b"\n"), "final_newline_required")
    try:
        text = source.decode(language.get("encoding", "utf-8"))
    except UnicodeDecodeError as exc:
        raise ModelError("source_not_utf8", str(exc)) from exc
    try:
        module = ast.parse(text, filename="<pd-sm-02-candidate>", mode="exec", type_comments=False)
    except SyntaxError as exc:
        raise ModelError("source_syntax_error", f"line {exc.lineno}: {exc.msg}") from exc

    _require(len(module.body) == 1, "module_shape", "exactly one function is required")
    fn = module.body[0]
    _require(isinstance(fn, ast.FunctionDef), "module_shape", "top-level item must be a function")
    _require(fn.name == language["entrypoint"], "entrypoint_name", fn.name)
    _require(not fn.decorator_list, "decorators_not_allowed")
    _require(fn.returns is None and fn.type_comment is None, "annotations_not_allowed")
    args = fn.args
    _require(
        not args.posonlyargs
        and not args.args
        and args.vararg is None
        and not args.kwonlyargs
        and args.kwarg is None
        and not args.defaults
        and not args.kw_defaults,
        "entrypoint_arguments_not_allowed",
    )
    _require(bool(fn.body), "empty_entrypoint")

    aliases: dict[str, str] = {}
    operations: list[dict[str, Any]] = []
    primitives: dict[str, Any] = language["primitives"]
    domains: dict[str, list[str]] = profile["domains"]
    maximum_aliases = int(language.get("allowed_local_binding_count", 16))

    for statement in fn.body:
        if isinstance(statement, ast.Assign):
            _require(len(statement.targets) == 1, "multiple_assignment_targets")
            target = statement.targets[0]
            _require(isinstance(target, ast.Name), "assignment_target")
            name = target.id
            _require(name.isidentifier() and not name.startswith("__"), "local_name", name)
            _require(name not in primitives, "local_shadows_primitive", name)
            _require(name not in aliases, "local_reassignment", name)
            _require(isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str), "local_value", name)
            _require(len(aliases) < maximum_aliases, "too_many_local_bindings")
            aliases[name] = statement.value.value
            continue

        _require(isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call), "unsupported_statement", f"line {getattr(statement, 'lineno', '?')}")
        call = statement.value
        _require(isinstance(call.func, ast.Name), "indirect_call_not_allowed", f"line {call.lineno}")
        name = call.func.id
        _require(name in primitives, "unknown_primitive", name)
        _require(not call.keywords, "keyword_arguments_not_allowed", name)
        spec = primitives[name]
        _require(len(call.args) == spec["arity"], "primitive_arity", name)
        resolved = [_resolve_arg(item, aliases) for item in call.args]
        for index, (value, domain_name) in enumerate(zip(resolved, spec["arg_domains"])):
            _require(value in domains[domain_name], "argument_out_of_domain", f"{name}[{index}]={value}")
        operations.append(
            {
                "index": len(operations),
                "primitive": name,
                "args": resolved,
                "kind": spec["kind"],
                "line": int(call.lineno),
                "column": int(call.col_offset),
                "source_fragment_sha256": sha256(_source_segment(text, statement).encode("utf-8")),
            }
        )

    _require(bool(operations), "no_primitive_operations")
    return operations, aliases


def _derive_relations(operations: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    actors: set[str] = set()
    bound_requests: dict[str, dict[str, str]] = {}
    guards: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    monitor_requests: list[dict[str, Any]] = []
    reservations: list[dict[str, Any]] = []

    for operation in operations:
        primitive = operation["primitive"]
        args = operation["args"]
        if primitive == "actor":
            actors.add(args[0])
        elif primitive == "bind_request":
            request_id, target, payload = args
            if request_id in bound_requests:
                raise ModelError("duplicate_request_binding", request_id)
            bound_requests[request_id] = {"target": target, "payload": payload}
        elif primitive.startswith("require_"):
            guards.append({"operation_index": operation["index"], "primitive": primitive, "args": args})
        elif primitive == "broker_request":
            actors.add(args[0])
            monitor_requests.append({"operation_index": operation["index"], "actor": args[0], "request_id": args[1]})
        elif primitive == "reserve":
            reservations.append({"operation_index": operation["index"], "request_id": args[0]})
        elif primitive == "append_sink":
            effects.append(
                {
                    "operation_index": operation["index"],
                    "route": "broker_append",
                    "actor": profile["protected_contract"]["effect_actor"],
                    "request_id": args[0],
                    "prefix_operation_indexes": list(range(operation["index"])),
                }
            )
        elif primitive == "direct_sink_write":
            actors.add(args[0])
            effects.append(
                {
                    "operation_index": operation["index"],
                    "route": "direct_sink_write",
                    "actor": args[0],
                    "request_id": args[1],
                    "prefix_operation_indexes": list(range(operation["index"])),
                }
            )

    return {
        "roles": sorted(actors),
        "bound_requests": bound_requests,
        "guard_occurrences": guards,
        "monitor_request_occurrences": monitor_requests,
        "reservation_occurrences": reservations,
        "effect_occurrences": effects,
        "effect_route_count": len(effects),
        "configuration_domain": {
            "environment_scenarios": [row["id"] for row in profile["environment_scenarios"]],
            "scenario_count": len(profile["environment_scenarios"]),
            "model_nonempty_status": "NONEMPTY_BY_DECLARED_SCENARIOS",
        },
    }


def build_model(source: bytes, profile: dict[str, Any]) -> dict[str, Any]:
    operations, aliases = parse_candidate(source, profile)
    profile_digest = sha256(canonical_bytes(profile))
    candidate_digest = sha256(source)
    relation_model = _derive_relations(operations, profile)
    result: dict[str, Any] = {
        "schema_version": MODEL_SCHEMA,
        "profile_id": profile["profile_id"],
        "candidate_sha256": candidate_digest,
        "candidate_bytes": len(source),
        "profile_sha256": profile_digest,
        "source_language_status": "SUPPORTED",
        "source_model_mapping_status": "COMPLETE_FOR_SUPPORTED_LANGUAGE",
        "mapper_verdict": None,
        "entrypoint": profile["candidate_language"]["entrypoint"],
        "private_constant_bindings": aliases,
        "operations": operations,
        "relations": relation_model,
        "source_imported_or_executed": False,
        "authority_effect": "none",
    }
    digest_view = dict(result)
    digest_view["model_sha256"] = None
    result["model_sha256"] = sha256(canonical_bytes(digest_view))
    return result


def _error_record(source: bytes, profile: dict[str, Any] | None, error: ModelError) -> dict[str, Any]:
    return {
        "schema_version": MODEL_SCHEMA,
        "profile_id": profile.get("profile_id") if isinstance(profile, dict) else None,
        "candidate_sha256": sha256(source),
        "candidate_bytes": len(source),
        "profile_sha256": sha256(canonical_bytes(profile)) if isinstance(profile, dict) else None,
        "source_language_status": "UNSUPPORTED",
        "source_model_mapping_status": "INCOMPLETE",
        "error": {"code": error.code, "detail": error.detail},
        "source_imported_or_executed": False,
        "authority_effect": "none",
    }


def build_model_record(source: bytes, profile: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Return a success or fail-closed unsupported record without execution."""
    try:
        return build_model(source, profile), 0
    except ModelError as exc:
        return _error_record(source, profile, exc), 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = args.candidate.read_bytes()
    profile: dict[str, Any] | None = None
    try:
        loaded = strict_json(args.profile.read_bytes())
        _require(isinstance(loaded, dict), "profile_not_object")
        profile = loaded
        result, exit_code = build_model_record(source, profile)
    except ModelError as exc:
        result = _error_record(source, profile, exc)
        exit_code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
