#!/usr/bin/env python3
"""Independent PD-SM-02 source/model/certificate checker.

This checker deliberately does not import source_model.py or candidate code.  It
reparses the exact source bytes, checks the supplied model, enumerates the fixed
finite environment, and reports model preservation, useful operation, binding,
and unresolved obligations separately.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


REPORT_SCHEMA = "pd_sm_02_impact_report_v0"

# These codes describe an honest refusal of the closed candidate language.
# They are used only after the mapper has emitted an UNSUPPORTED record and
# the independent parser has confirmed that the exact source is outside the
# profile.  A supported-model/source mismatch remains INVALID_MAPPING.
UNSUPPORTED_SOURCE_CODES = {
    "source_too_large",
    "utf8_bom_not_allowed",
    "final_newline_required",
    "source_not_utf8",
    "source_syntax_error",
    "module_shape",
    "entrypoint_name",
    "function_metadata",
    "entrypoint_arguments_not_allowed",
    "assignment_target",
    "local_name",
    "local_binding_conflict",
    "local_value",
    "too_many_local_bindings",
    "unsupported_statement",
    "indirect_call_not_allowed",
    "unknown_primitive",
    "keyword_arguments_not_allowed",
    "primitive_arity",
    "unsupported_call_argument",
    "argument_out_of_domain",
    "no_primitive_operations",
    "duplicate_request_binding",
}


class CheckError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CheckError("duplicate_json_key", key)
        out[key] = value
    return out


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                CheckError("non_finite_json_number", value)
            ),
        )
    except UnicodeDecodeError as exc:
        raise CheckError("json_not_utf8", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise CheckError("invalid_json", str(exc)) from exc


def canonical_bytes(value: Any) -> bytes:
    def walk(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise CheckError("non_finite_value")
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise CheckError("non_string_json_key")
                walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise CheckError(code, detail)


def _resolve_arg(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in aliases:
        return aliases[node.id]
    raise CheckError("unsupported_call_argument", f"line {getattr(node, 'lineno', '?')}")


def independently_parse(source: bytes, profile: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Independent parser; intentionally duplicated rather than shared with mapper."""
    require(profile.get("schema_version") == "pd_sm_02_profile_v0", "profile_schema")
    language = profile.get("candidate_language")
    require(isinstance(language, dict), "candidate_language")
    require(len(source) <= int(language["max_source_bytes"]), "source_too_large")
    require(not source.startswith(b"\xef\xbb\xbf"), "utf8_bom_not_allowed")
    if language.get("final_newline_required"):
        require(source.endswith(b"\n"), "final_newline_required")
    try:
        text = source.decode(language.get("encoding", "utf-8"))
    except UnicodeDecodeError as exc:
        raise CheckError("source_not_utf8", str(exc)) from exc
    try:
        module = ast.parse(text, filename="<pd-sm-02-independent-check>", mode="exec", type_comments=False)
    except SyntaxError as exc:
        raise CheckError("source_syntax_error", f"line {exc.lineno}: {exc.msg}") from exc
    require(len(module.body) == 1 and isinstance(module.body[0], ast.FunctionDef), "module_shape")
    fn = module.body[0]
    require(fn.name == language["entrypoint"], "entrypoint_name")
    require(not fn.decorator_list and fn.returns is None and fn.type_comment is None, "function_metadata")
    args = fn.args
    require(
        not args.posonlyargs and not args.args and args.vararg is None and not args.kwonlyargs
        and args.kwarg is None and not args.defaults and not args.kw_defaults,
        "entrypoint_arguments_not_allowed",
    )

    primitives = language["primitives"]
    domains = profile["domains"]
    aliases: dict[str, str] = {}
    operations: list[dict[str, Any]] = []
    for statement in fn.body:
        if isinstance(statement, ast.Assign):
            require(len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name), "assignment_target")
            name = statement.targets[0].id
            require(name.isidentifier() and not name.startswith("__"), "local_name", name)
            require(name not in primitives and name not in aliases, "local_binding_conflict", name)
            require(isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str), "local_value", name)
            require(len(aliases) < int(language.get("allowed_local_binding_count", 16)), "too_many_local_bindings")
            aliases[name] = statement.value.value
            continue
        require(isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call), "unsupported_statement")
        call = statement.value
        require(isinstance(call.func, ast.Name), "indirect_call_not_allowed")
        primitive = call.func.id
        require(primitive in primitives, "unknown_primitive", primitive)
        require(not call.keywords, "keyword_arguments_not_allowed", primitive)
        spec = primitives[primitive]
        require(len(call.args) == spec["arity"], "primitive_arity", primitive)
        resolved = [_resolve_arg(item, aliases) for item in call.args]
        for index, (value, domain) in enumerate(zip(resolved, spec["arg_domains"])):
            require(value in domains[domain], "argument_out_of_domain", f"{primitive}[{index}]={value}")
        fragment = ast.get_source_segment(text, statement) or ""
        operations.append(
            {
                "index": len(operations),
                "primitive": primitive,
                "args": resolved,
                "kind": spec["kind"],
                "line": int(call.lineno),
                "column": int(call.col_offset),
                "source_fragment_sha256": sha256(fragment.encode("utf-8")),
            }
        )
    require(bool(operations), "no_primitive_operations")
    return operations, aliases


def expected_relations(operations: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    actors: set[str] = set()
    requests: dict[str, dict[str, str]] = {}
    guards: list[dict[str, Any]] = []
    monitors: list[dict[str, Any]] = []
    reservations: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    for op in operations:
        primitive, args = op["primitive"], op["args"]
        if primitive == "actor":
            actors.add(args[0])
        elif primitive == "bind_request":
            require(args[0] not in requests, "duplicate_request_binding", args[0])
            requests[args[0]] = {"target": args[1], "payload": args[2]}
        elif primitive.startswith("require_"):
            guards.append({"operation_index": op["index"], "primitive": primitive, "args": args})
        elif primitive == "broker_request":
            actors.add(args[0])
            monitors.append({"operation_index": op["index"], "actor": args[0], "request_id": args[1]})
        elif primitive == "reserve":
            reservations.append({"operation_index": op["index"], "request_id": args[0]})
        elif primitive == "append_sink":
            effects.append({
                "operation_index": op["index"], "route": "broker_append",
                "actor": profile["protected_contract"]["effect_actor"], "request_id": args[0],
                "prefix_operation_indexes": list(range(op["index"])),
            })
        elif primitive == "direct_sink_write":
            actors.add(args[0])
            effects.append({
                "operation_index": op["index"], "route": "direct_sink_write",
                "actor": args[0], "request_id": args[1],
                "prefix_operation_indexes": list(range(op["index"])),
            })
    return {
        "roles": sorted(actors),
        "bound_requests": requests,
        "guard_occurrences": guards,
        "monitor_request_occurrences": monitors,
        "reservation_occurrences": reservations,
        "effect_occurrences": effects,
        "effect_route_count": len(effects),
        "configuration_domain": {
            "environment_scenarios": [row["id"] for row in profile["environment_scenarios"]],
            "scenario_count": len(profile["environment_scenarios"]),
            "model_nonempty_status": "NONEMPTY_BY_DECLARED_SCENARIOS",
        },
    }


def check_model(source: bytes, profile: dict[str, Any], model: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    # Validate identity bindings before interpreting an UNSUPPORTED claim.  A
    # mismatched model must not obtain the less severe coverage classification.
    require(model.get("schema_version") == "pd_sm_02_source_model_v0", "model_schema")
    require(model.get("profile_id") == profile.get("profile_id"), "model_profile_id")
    require(model.get("candidate_sha256") == sha256(source), "model_candidate_binding")
    require(model.get("profile_sha256") == sha256(canonical_bytes(profile)), "model_profile_binding")

    language_status = model.get("source_language_status")
    if language_status == "UNSUPPORTED":
        require(model.get("source_model_mapping_status") == "INCOMPLETE", "unsupported_model_status")
        error = model.get("error")
        require(isinstance(error, dict) and isinstance(error.get("code"), str), "unsupported_model_error")
        try:
            operations, _aliases = independently_parse(source, profile)
            # Relation extraction is part of the closed source profile: a
            # duplicate binding, for example, is an honest unsupported source
            # condition only when the independent implementation also sees it.
            expected_relations(operations, profile)
        except CheckError as exc:
            if exc.code not in UNSUPPORTED_SOURCE_CODES:
                raise
            detail = exc.code if not exc.detail else f"{exc.code}: {exc.detail}"
            raise CheckError("unsupported_source_confirmed", detail) from exc
        raise CheckError("mapper_claimed_unsupported_for_supported_source")

    require(language_status == "SUPPORTED", "source_language_status")
    operations, aliases = independently_parse(source, profile)
    require(model.get("operations") == operations, "model_operation_mismatch")
    require(model.get("private_constant_bindings") == aliases, "model_alias_mismatch")
    relations = expected_relations(operations, profile)
    supplied = model.get("relations")
    require(isinstance(supplied, dict), "model_relations_missing")
    domain = supplied.get("configuration_domain")
    if not isinstance(domain, dict) or domain.get("scenario_count") == 0 or domain.get("model_nonempty_status") != "NONEMPTY_BY_DECLARED_SCENARIOS":
        raise CheckError("model_empty_or_inconsistent")
    require(supplied == relations, "model_relation_mismatch")
    digest_view = dict(model)
    digest = digest_view.pop("model_sha256", None)
    digest_view["model_sha256"] = None
    require(digest == sha256(canonical_bytes(digest_view)), "model_digest")
    return operations, aliases


def evidence_closure(evidence: dict[str, Any]) -> tuple[set[str], bool]:
    facts = evidence.get("facts")
    rules = evidence.get("rules")
    require(isinstance(facts, list) and all(isinstance(item, str) for item in facts), "evidence_facts")
    require(len(facts) == len(set(facts)), "duplicate_evidence_fact")
    require(isinstance(rules, list), "evidence_rules")
    normalized: list[tuple[tuple[str, ...], str]] = []
    graph: dict[str, set[str]] = {}
    for row in rules:
        require(isinstance(row, dict), "evidence_rule")
        premises, conclusion = row.get("premises"), row.get("conclusion")
        require(isinstance(premises, list) and all(isinstance(item, str) for item in premises), "evidence_premises")
        require(isinstance(conclusion, str), "evidence_conclusion")
        normalized.append((tuple(premises), conclusion))
        for premise in premises:
            graph.setdefault(premise, set()).add(conclusion)
    closure = set(facts)
    changed = True
    while changed:
        changed = False
        for premises, conclusion in normalized:
            if set(premises).issubset(closure) and conclusion not in closure:
                closure.add(conclusion)
                changed = True

    # Detect a positive cycle in the rule graph.  It is reported only as a
    # possible ungrounded-support reason; it never manufactures closure.
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle = False

    def dfs(node: str) -> None:
        nonlocal cycle
        if node in visiting:
            cycle = True
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, set()):
            dfs(nxt)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        dfs(node)
    return closure, cycle


def submitted_request(kind: str, protected: dict[str, Any]) -> dict[str, str]:
    result = {
        "request_id": protected["request_id"],
        "target": protected["target"],
        "payload": protected["payload"],
    }
    if kind == "target_mismatch":
        result["target"] = "alternate_target"
    elif kind == "payload_mismatch":
        result["payload"] = "DIFFERENT"
    elif kind != "exact":
        raise CheckError("unknown_submitted_request", kind)
    return result


def monitor_result(mode: str, request: dict[str, str], joint_binding: str) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    if mode == "absent":
        return None, None
    if mode == "exit_before_ack":
        return None, dict(request)
    if mode == "ack_without_record":
        return dict(request), None
    if mode == "wrong_ack":
        wrong = dict(request)
        wrong["request_id"] = "request-1"
        return wrong, dict(request)
    require(mode == "normal", "monitor_mode", mode)
    if joint_binding == "ack_audit_different":
        audit = dict(request)
        audit["request_id"] = "request-1"
        return dict(request), audit
    require(joint_binding == "same", "joint_binding", joint_binding)
    return dict(request), dict(request)


def simulate(
    operations: list[dict[str, Any]], profile: dict[str, Any], context: dict[str, Any], closure: set[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    protected = profile["protected_contract"]
    required_obligation = protected["source_obligation"]
    required_request = {
        "request_id": protected["request_id"],
        "target": protected["target"],
        "payload": protected["payload"],
    }
    all_scenarios: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    healthy_effects: list[dict[str, Any]] = []

    for scenario in profile["environment_scenarios"]:
        submitted = submitted_request(scenario["submitted_request"], protected)
        used: set[str] = set()
        monitor_capacity = int(protected["monitor_request_capacity"])
        effects: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        for attempt_index in range(int(scenario["attempts"])):
            blocked = False
            ack: dict[str, str] | None = None
            audit: dict[str, str] | None = None
            reserved_request_ids: set[str] = set()
            bound_request: dict[str, str] | None = None
            actor = "primary"
            trace: list[dict[str, Any]] = []

            for op in operations:
                if blocked:
                    break
                primitive, args = op["primitive"], op["args"]
                if primitive == "actor":
                    actor = args[0]
                elif primitive == "bind_request":
                    request_id, target, payload = args
                    ok = bound_request is None
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    if ok:
                        bound_request = {"request_id": request_id, "target": target, "payload": payload}
                    else:
                        blocked = True
                elif primitive == "require_source":
                    ok = args[0] in closure
                    trace.append({"operation": primitive, "accepted": ok})
                    blocked = not ok
                elif primitive == "require_request_match":
                    request_id = args[0]
                    ok = (
                        bound_request is not None
                        and bound_request == submitted
                        and bound_request == required_request
                        and request_id == bound_request["request_id"]
                    )
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    blocked = not ok
                elif primitive == "require_unused":
                    request_id = args[0]
                    ok = (
                        bound_request is not None
                        and bound_request["request_id"] == request_id
                        and request_id not in used
                    )
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    blocked = not ok
                elif primitive == "reserve":
                    request_id = args[0]
                    ok = bound_request is not None and bound_request["request_id"] == request_id
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    if ok:
                        used.add(request_id)
                        reserved_request_ids.add(request_id)
                    else:
                        blocked = True
                elif primitive == "broker_request":
                    actor_name, request_id = args
                    binding_ok = (
                        actor == actor_name
                        and bound_request is not None
                        and bound_request["request_id"] == request_id
                    )
                    capacity_ok = monitor_capacity > 0
                    ok = binding_ok and capacity_ok
                    if ok:
                        monitor_capacity -= 1
                        ack, audit = monitor_result(
                            scenario["monitor_mode"], submitted, scenario["joint_binding"]
                        )
                    trace.append({
                        "operation": primitive,
                        "accepted": ok,
                        "request_id": request_id,
                        "monitor_capacity_remaining": monitor_capacity,
                    })
                    blocked = not ok
                elif primitive in {"require_ack_match", "require_ack_present"}:
                    request_id = args[0]
                    request_aligned = (
                        bound_request is not None
                        and bound_request["request_id"] == request_id
                        and submitted["request_id"] == request_id
                    )
                    if primitive == "require_ack_match":
                        ok = request_aligned and ack == submitted
                    else:
                        ok = request_aligned and ack is not None
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    blocked = not ok
                elif primitive in {"require_audit_match", "require_audit_present"}:
                    request_id = args[0]
                    request_aligned = (
                        bound_request is not None
                        and bound_request["request_id"] == request_id
                        and submitted["request_id"] == request_id
                    )
                    if primitive == "require_audit_match":
                        ok = request_aligned and audit == submitted
                    else:
                        ok = request_aligned and audit is not None
                    trace.append({"operation": primitive, "accepted": ok, "request_id": request_id})
                    blocked = not ok
                elif primitive == "append_sink":
                    effect_request_id = args[0]
                    executable = (
                        bound_request is not None
                        and bound_request["request_id"] == effect_request_id
                        and effect_request_id in reserved_request_ids
                    )
                    if not executable:
                        trace.append({
                            "operation": primitive,
                            "accepted": False,
                            "request_id": effect_request_id,
                            "reason": "effect_request_or_reservation",
                        })
                        blocked = True
                        continue
                    prior_same_request = sum(
                        1 for item in effects if item["effect_request_id"] == effect_request_id
                    )
                    request_identity = (
                        bound_request == submitted
                        and bound_request == required_request
                        and effect_request_id == submitted["request_id"]
                    )
                    support = {
                        "source": required_obligation in closure,
                        "program_request_binding": request_identity,
                        "intent": audit == submitted and audit.get("request_id") == effect_request_id if audit else False,
                        "ack": ack == submitted and ack.get("request_id") == effect_request_id if ack else False,
                        "audit": audit == submitted and audit.get("request_id") == effect_request_id if audit else False,
                        "prerequisite_dependencies": effect_request_id in reserved_request_ids,
                        "single_use": prior_same_request < int(protected["max_effects_per_request"]),
                        "actor_route": protected["effect_actor"] == "broker",
                    }
                    effect = {
                        "scenario": scenario["id"],
                        "attempt": attempt_index,
                        "operation_index": op["index"],
                        "route": "broker_append",
                        "actor": protected["effect_actor"],
                        "effect_request_id": effect_request_id,
                        "bound_request": dict(bound_request),
                        "request": dict(submitted),
                        "reserved_request_ids": sorted(reserved_request_ids),
                        "support": support,
                        "invariant_satisfied": all(support.values()),
                    }
                    effects.append(effect)
                    trace.append({"operation": primitive, "accepted": True, "effect_index": len(effects) - 1})
                    if not effect["invariant_satisfied"]:
                        counterexamples.append(effect)
                elif primitive == "direct_sink_write":
                    effect_request_id = args[1]
                    prior_same_request = sum(
                        1 for item in effects if item["effect_request_id"] == effect_request_id
                    )
                    request_identity = (
                        bound_request is not None
                        and bound_request == submitted
                        and bound_request == required_request
                        and effect_request_id == submitted["request_id"]
                    )
                    support = {
                        "source": required_obligation in closure,
                        "program_request_binding": request_identity,
                        "intent": audit == submitted and audit.get("request_id") == effect_request_id if audit else False,
                        "ack": ack == submitted and ack.get("request_id") == effect_request_id if ack else False,
                        "audit": audit == submitted and audit.get("request_id") == effect_request_id if audit else False,
                        "prerequisite_dependencies": False,
                        "single_use": prior_same_request < int(protected["max_effects_per_request"]),
                        "actor_route": False,
                    }
                    effect = {
                        "scenario": scenario["id"],
                        "attempt": attempt_index,
                        "operation_index": op["index"],
                        "route": "direct_sink_write",
                        "actor": args[0],
                        "effect_request_id": effect_request_id,
                        "bound_request": dict(bound_request) if bound_request is not None else None,
                        "request": dict(submitted),
                        "reserved_request_ids": sorted(reserved_request_ids),
                        "support": support,
                        "invariant_satisfied": False,
                    }
                    effects.append(effect)
                    trace.append({"operation": primitive, "accepted": True, "effect_index": len(effects) - 1})
                    counterexamples.append(effect)
            attempts.append({
                "attempt": attempt_index,
                "blocked": blocked,
                "bound_request": dict(bound_request) if bound_request is not None else None,
                "reserved_request_ids": sorted(reserved_request_ids),
                "trace": trace,
            })
        if scenario["id"] == "healthy":
            healthy_effects = list(effects)
        all_scenarios.append({"scenario": scenario["id"], "attempts": attempts, "effects": effects})

    useful = (
        len(healthy_effects) == int(protected["healthy_required_effects"])
        and all(item["invariant_satisfied"] for item in healthy_effects)
        and all(item["effect_request_id"] == protected["request_id"] for item in healthy_effects)
        and all(item["bound_request"] == required_request for item in healthy_effects)
        and all(item["request"] == required_request for item in healthy_effects)
    )
    return all_scenarios, {
        "counterexamples": counterexamples,
        "invariant_holds_for_all_effects": not counterexamples,
        "healthy_effect_count": len(healthy_effects),
        "useful_operation_satisfied": useful,
    }


def _base_report(profile: dict[str, Any], source: bytes, model: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "profile_id": profile.get("profile_id"),
        "source_binding_status": "BOUND" if model.get("candidate_sha256") == sha256(source) else "MISMATCH",
        "supported_profile_status": "SUPPORTED",
        "source_model_mapping_status": "UNCHECKED",
        "coverage_status": "UNCHECKED",
        "model_nonempty_status": "UNCHECKED",
        "invariant_assessment": "UNCHECKED",
        "useful_operation_assessment": "UNCHECKED",
        "counterexample_realizability_status": "NOT_EVALUATED",
        "proof_applicability_status": "UNCHECKED",
        "unresolved_critical_obligations": [],
        "candidate_sha256": sha256(source),
        "profile_sha256": sha256(canonical_bytes(profile)),
        "model_sha256": model.get("model_sha256"),
        "context_sha256": sha256(canonical_bytes(context)),
        "bound_environment_identity": context.get("environment_identity"),
        "bound_subject_request": context.get("binding"),
        "checker_sha256": sha256(Path(__file__).read_bytes()),
        "execution_observation_status": "NOT_RUN",
        "candidate_imported_or_executed": False,
        "authority_effect": "none",
    }


def assess(source: bytes, profile: dict[str, Any], model: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    report = _base_report(profile, source, model, context)
    try:
        require(context.get("schema_version") == "pd_sm_02_context_v0", "context_schema")
        require(context.get("profile_id") == profile.get("profile_id"), "context_profile")
        binding = context.get("binding")
        require(isinstance(binding, dict), "binding_record")
        protected = profile["protected_contract"]
        required_binding = {
            "request_id": protected["request_id"],
            "target": protected["target"],
            "payload": protected["payload"],
            "subject": "PD-SM-02-protected-scratch-operation",
        }
        if binding != required_binding:
            report.update(
                assessment="BINDING_REJECTED",
                source_model_mapping_status="NOT_REUSABLE",
                coverage_status="NOT_EVALUATED",
                model_nonempty_status="NOT_EVALUATED",
                invariant_assessment="NOT_EVALUATED",
                useful_operation_assessment="NOT_EVALUATED",
                proof_applicability_status="BINDING_REJECTED",
                unresolved_critical_obligations=["exact subject/request/target binding"],
            )
            return report
        if context.get("preexecution_boundary_complete") is not True:
            report.update(
                assessment="NO_UNCHECKED_LAUNCH",
                source_model_mapping_status="NOT_EVALUATED",
                coverage_status="INCOMPLETE",
                model_nonempty_status="NOT_EVALUATED",
                invariant_assessment="NOT_EVALUATED",
                useful_operation_assessment="NOT_EVALUATED",
                proof_applicability_status="NOT_ESTABLISHED",
                unresolved_critical_obligations=["completed pre-execution boundary"],
            )
            return report
        if context.get("observer_contract_complete") is not True:
            report.update(
                assessment="OBSERVATION_INCOMPLETE",
                source_model_mapping_status="NOT_EVALUATED",
                coverage_status="INCOMPLETE",
                model_nonempty_status="NOT_EVALUATED",
                invariant_assessment="NOT_EVALUATED",
                useful_operation_assessment="NOT_EVALUATED",
                proof_applicability_status="NOT_ESTABLISHED",
                unresolved_critical_obligations=["effect observer completion and byte capture"],
            )
            return report

        try:
            operations, _aliases = check_model(source, profile, model)
        except CheckError as exc:
            if exc.code == "unsupported_source_confirmed":
                report.update(
                    assessment="UNRESOLVED",
                    supported_profile_status="UNSUPPORTED",
                    source_model_mapping_status="INCOMPLETE",
                    coverage_status="INCOMPLETE",
                    model_nonempty_status="NOT_EVALUATED",
                    invariant_assessment="NOT_EVALUATED",
                    useful_operation_assessment="NOT_EVALUATED",
                    proof_applicability_status="NOT_ESTABLISHED",
                    unresolved_critical_obligations=[f"unsupported source semantics: {exc.detail}"],
                )
                return report
            if exc.code == "model_empty_or_inconsistent":
                report.update(
                    assessment="INCONSISTENT_OR_INVALID",
                    source_model_mapping_status="INVALID",
                    coverage_status="EMPTY_OR_INCONSISTENT",
                    model_nonempty_status="FAILED",
                    invariant_assessment="NOT_EVALUATED",
                    useful_operation_assessment="FAILED",
                    proof_applicability_status="NOT_ESTABLISHED",
                    unresolved_critical_obligations=["nonempty source-derived configuration family"],
                )
                return report
            report.update(
                assessment="INVALID_MAPPING",
                source_model_mapping_status="INVALID",
                coverage_status="INCOMPLETE",
                model_nonempty_status="NOT_EVALUATED",
                invariant_assessment="NOT_EVALUATED",
                useful_operation_assessment="NOT_EVALUATED",
                proof_applicability_status="NOT_ESTABLISHED",
                unresolved_critical_obligations=[f"source/model mismatch: {exc.code}"],
            )
            return report

        evidence = context.get("evidence")
        require(isinstance(evidence, dict), "evidence_record")
        closure, cycle = evidence_closure(evidence)
        required_source = protected["source_obligation"]
        source_justified = required_source in closure
        scenarios, result = simulate(operations, profile, context, closure)
        report.update(
            source_model_mapping_status="VERIFIED_FOR_SUPPORTED_LANGUAGE",
            coverage_status="COMPLETE_FOR_DECLARED_FINITE_PROFILE",
            model_nonempty_status="NONEMPTY",
            finite_scenarios=scenarios,
            invariant_assessment="SATISFIED" if result["invariant_holds_for_all_effects"] else "VIOLATED",
            useful_operation_assessment="SATISFIED" if result["useful_operation_satisfied"] else "NOT_SATISFIED",
            counterexamples=result["counterexamples"],
            counterexample_realizability_status="MODEL_WITNESS_ONLY" if result["counterexamples"] else "NOT_APPLICABLE",
            evidence_closure=sorted(closure),
            source_justification_status="JUSTIFIED" if source_justified else "UNRESOLVED_CYCLE" if cycle else "NOT_JUSTIFIED",
        )

        if result["counterexamples"]:
            report.update(
                assessment="REFUTED_IN_MODEL",
                proof_applicability_status="REFUTED_FOR_DECLARED_MODEL",
                unresolved_critical_obligations=[],
            )
        elif not source_justified:
            report.update(
                assessment="UNRESOLVED",
                proof_applicability_status="NOT_ESTABLISHED",
                unresolved_critical_obligations=[
                    "grounded source justification" if cycle else "admitted source evidence"
                ],
            )
        elif not result["useful_operation_satisfied"]:
            report.update(
                assessment="SAFETY_ONLY_NOT_ACCEPTABLE",
                proof_applicability_status="SAFETY_ONLY",
                unresolved_critical_obligations=["healthy useful-operation witness"],
            )
        else:
            primitives = [row["primitive"] for row in operations]
            if "require_unused" not in primitives:
                report.update(
                    assessment="PROPERTY_DEPENDENT",
                    proof_applicability_status="ESTABLISHED_FOR_PROTECTED_RELATION_ONLY",
                    unresolved_critical_obligations=[
                        "rejection-reason equivalence and future multi-request monitor behavior"
                    ],
                )
            else:
                report.update(
                    assessment="ESTABLISHED_CONDITIONAL",
                    proof_applicability_status="ESTABLISHED_FOR_DECLARED_PROFILE",
                    unresolved_critical_obligations=[],
                )
        return report
    except CheckError as exc:
        report.update(
            assessment="INCONSISTENT_OR_INVALID",
            source_model_mapping_status="INVALID",
            coverage_status="NOT_EVALUATED",
            model_nonempty_status="NOT_EVALUATED",
            invariant_assessment="NOT_EVALUATED",
            useful_operation_assessment="NOT_EVALUATED",
            proof_applicability_status="NOT_ESTABLISHED",
            unresolved_critical_obligations=[f"invalid record: {exc.code}"],
            error={"code": exc.code, "detail": exc.detail},
        )
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.candidate.read_bytes()
    profile = strict_json(args.profile.read_bytes())
    model = strict_json(args.model.read_bytes())
    context = strict_json(args.context.read_bytes())
    require(isinstance(profile, dict), "profile_not_object")
    require(isinstance(model, dict), "model_not_object")
    require(isinstance(context, dict), "context_not_object")
    report = assess(source, profile, model, context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    return 0 if report.get("assessment") in {"ESTABLISHED_CONDITIONAL", "PROPERTY_DEPENDENT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
