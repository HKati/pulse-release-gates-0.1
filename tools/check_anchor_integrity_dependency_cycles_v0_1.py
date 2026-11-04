#!/usr/bin/env python3
"""WP2D: observe cycles in an explicitly bound, typed dependency projection.

This is an offline diagnostic, not anchor authentication or semantic support.
An exit status of zero means analysis completed, including when cycles exist.
The fixed installed WP2C and WP2A/WP2B checkers run afresh on retained bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "typed-dependencies-v1"
GRAPH_VERSION = "anchor_integrity_dependency_graph_v0_1"
REPORT_VERSION = "anchor_integrity_dependency_cycle_report_v0_1"
MAX_GRAPH_NODES = 8192
MAX_GRAPH_EDGES = 8192
EDGE_TYPES = ("supported_by_claim", "derived_from_claim",
              "evidence_depends_on_claim", "claim_depends_on_claim")
DEPENDENCY_RELATIONS = ("supports", "derived_from")
SCHEMAS = {
    "graph": "anchor_integrity_dependency_graph_v0_1.schema.json",
    "report": "anchor_integrity_dependency_cycle_report_v0_1.schema.json",
}
STATUSES = {
    "analyzed": "LOCAL_DEPENDENCY_GRAPH_ANALYZED",
    "invalid": "LOCAL_DEPENDENCY_GRAPH_INVALID",
    "incomplete": "LOCAL_DEPENDENCY_GRAPH_INCOMPLETE",
}
UNPERFORMED = (
    "source_identity_authentication", "acquisition_authentication",
    "subject_observation_authentication", "verifier_identity_authentication",
    "verifier_execution_attestation", "semantic_support_verification",
    "dependency_inventory_authentication", "response_mode_recommendation",
    "claim_set_completeness", "verified_binding_coverage", "verified_support_coverage",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def load_record_checker() -> Any:
    """Only fixed installed code is loaded; no artifact can choose a module."""
    path = ROOT / "tools" / "check_anchor_integrity_verifier_records_v0_1.py"
    spec = importlib.util.spec_from_file_location("anchor_records_wp2d_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("record_checker_unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


class CycleSchemas:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.hashes: dict[str, str] = {}
        self.validators: dict[str, Any] = {}
        for role, name in SCHEMAS.items():
            raw = (ROOT / "schemas" / name).read_bytes()
            schema = base.strict_json(raw)
            base._assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.hashes[name] = digest(raw)
            self.validators[role] = jsonschema.Draft202012Validator(schema)

    def validate(self, role: str, value: Any) -> None:
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise self.base.BindingError("schema_invalid_dependency_" + role)


def _components(nodes: list[str], edges: list[dict[str, Any]]) -> list[list[str]]:
    """Iterative two-pass SCC decomposition; no recursion or path enumeration."""
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    reverse: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
        reverse[edge["to"]].append(edge["from"])
    for table in (adjacency, reverse):
        for node in table:
            table[node] = sorted(set(table[node]))
    visited: set[str] = set()
    finished: list[str] = []
    for root in sorted(nodes):
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(adjacency[root]))]
        while stack:
            node, iterator = stack[-1]
            target = next(iterator, None)
            if target is None:
                finished.append(node)
                stack.pop()
            elif target not in visited:
                visited.add(target)
                stack.append((target, iter(adjacency[target])))
    assigned: set[str] = set()
    components: list[list[str]] = []
    for root in reversed(finished):
        if root in assigned:
            continue
        assigned.add(root)
        stack = [root]
        component: list[str] = []
        while stack:
            node = stack.pop()
            component.append(node)
            for target in reverse[node]:
                if target not in assigned:
                    assigned.add(target)
                    stack.append(target)
        components.append(sorted(component))
    return sorted(components)


def _witness(nodes: list[str], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """One deterministic closed directed walk per cyclic SCC, with edge IDs."""
    adjacency: dict[str, list[tuple[str, str]]] = {n: [] for n in nodes}
    for edge in edges:
        adjacency[edge["from"]].append((edge["to"], edge["edge_key"]))
    for node in adjacency:
        adjacency[node].sort()
    done: set[str] = set()
    for root in sorted(nodes):
        if root in done:
            continue
        path = [root]
        path_edges: list[str] = []
        positions = {root: 0}
        stack = [iter(adjacency[root])]
        while stack:
            item = next(stack[-1], None)
            if item is None:
                done.add(path[-1])
                positions.pop(path.pop())
                stack.pop()
                if path_edges:
                    path_edges.pop()
                continue
            target, key = item
            if target in positions:
                start = positions[target]
                return {"nodes": path[start:] + [target],
                        "edge_keys": path_edges[start:] + [key]}
            if target not in done:
                positions[target] = len(path)
                path.append(target)
                path_edges.append(key)
                stack.append(iter(adjacency[target]))
    raise RuntimeError("cyclic_component_without_witness")


def analyze_projection(nodes: list[str], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze an already validated projection; do not classify anchor trust."""
    if len(nodes) > MAX_GRAPH_NODES or len(edges) > MAX_GRAPH_EDGES:
        raise ValueError("dependency_graph_resource_limit")
    if len(set(nodes)) != len(nodes):
        raise ValueError("duplicate_projection_node")
    known = set(nodes)
    keys = [e["edge_key"] for e in edges]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate_projection_edge_key")
    if any(e["from"] not in known or e["to"] not in known for e in edges):
        raise ValueError("unknown_projection_endpoint")
    components = _components(nodes, edges)
    membership = {node: index for index, group in enumerate(components) for node in group}
    internal: list[list[dict[str, Any]]] = [[] for _ in components]
    for edge in edges:
        index = membership[edge["from"]]
        if index == membership[edge["to"]]:
            internal[index].append(edge)
    cycles: list[dict[str, Any]] = []
    for index, group in enumerate(components):
        group_edges = sorted(internal[index], key=lambda e: e["edge_key"])
        if len(group) > 1 or any(e["from"] == e["to"] for e in group_edges):
            cycles.append({"component_id": "scc-" + str(index + 1), "nodes": group,
                           "internal_edge_keys": [e["edge_key"] for e in group_edges],
                           "witness": _witness(group, group_edges)})
    return {"component_count": len(components), "cyclic_components": cycles,
            "result": "cycle_detected" if cycles else "no_cycle_detected_in_declared_graph"}


class CycleReview:
    def __init__(self, records: Any, base: Any, binding_profile: str) -> None:
        self.records = records
        self.base = base
        self.record_review = records.RecordReview(base, binding_profile)
        self.schemas = CycleSchemas(base)
        upstream = self.record_review.report["implementation"]
        self.report: dict[str, Any] = {
            "schema_version": REPORT_VERSION, "work_package": "WP2D", "profile": PROFILE,
            "verification_scope": "declared_typed_dependency_projection_only",
            "candidate_status": "diagnostic_only", "authority_effect": "none",
            "release_authority_activation": False, "requested_checks_complete": False,
            "accepted_as_semantic_support": False,
            "whole_response_cycle_freedom_established": False,
            "status": STATUSES["incomplete"], "binding_profile": binding_profile,
            "expected_digests": {k: None for k in ("input", "carriers", "record_set")},
            "observed_digests": {k: None for k in ("input", "carriers", "record_set")},
            "record_check": {"status": None, "report_sha256": None},
            "graph_binding": {"path": None, "expected_sha256": None, "observed_sha256": None},
            "claim_materialization_status": None,
            "counts": {k: None for k in ("nodes", "claims", "evidence_items", "explicit_edges",
                                         "derived_relation_edges", "ignored_relations", "edges",
                                         "components", "cyclic_components")},
            "nodes": [], "edges": [], "ignored_relations": [], "cyclic_components": [],
            "cycle_detection": {"status": "not_run", "result": None,
                                "algorithm": None, "reason": "prerequisites_not_established"},
            "cycle_anchor_classification": {
                "status": "not_run", "result": None,
                "reason": "independently_verified_external_anchor_admission_not_implemented"},
            "unperformed_checks": {
                k: {"status": "not_run", "result": None,
                    "reason": "outside_wp2d_structural_observation_scope"} for k in UNPERFORMED},
            "issues": [],
            "implementation": {
                "checker_sha256": digest(Path(__file__).read_bytes()),
                "record_checker_sha256": upstream["checker_sha256"],
                "binding_checker_sha256": upstream["binding_checker_sha256"],
                "json_pointer_module_sha256": upstream["json_pointer_module_sha256"],
                "schema_sha256": {**upstream["schema_sha256"], **self.schemas.hashes},
            },
        }

    def issue(self, code: str, object_id: str, severity: str = "invalid") -> None:
        self.report["issues"].append({"code": code, "object_id": object_id, "severity": severity})

    def capture_records(self) -> bool:
        result = self.record_review.finish()
        self.report["record_check"] = {"status": result["status"],
                                       "report_sha256": digest(self.records.report_bytes(result))}
        self.report["observed_digests"] = dict(result["observed_digests"])
        for issue in result["issues"]:
            self.issue("records." + issue["code"], issue["object_id"], issue["severity"])
        return result["status"] == "LOCAL_RECORD_BINDINGS_CONSISTENT"

    def observe(self, reader: Any, input_path: str) -> None:
        cached = self.record_review.cached_json
        inp = cached(reader, input_path)
        binding = inp["paradox_graph_binding"]
        if binding is None:
            raise self.base.BindingError("dependency_graph_not_bound", "incomplete")
        raw = reader.cache.get(binding["path"])
        self.report["graph_binding"] = {
            "path": binding["path"], "expected_sha256": binding["sha256"],
            "observed_sha256": digest(raw) if raw is not None else None,
        }
        if raw is None:
            raise self.base.BindingError("dependency_graph_snapshot_missing", "incomplete")
        if digest(raw) != binding["sha256"]:
            raise self.base.BindingError("dependency_graph_digest_mismatch")
        if binding["schema_version"] != GRAPH_VERSION:
            raise self.base.BindingError("unsupported_dependency_graph_schema")
        graph = self.base.strict_json(raw)
        self.schemas.validate("graph", graph)
        packets = {
            role: cached(reader, inp["packet_bindings"][key]["path"])
            for role, key in (("claims", "claim_packet"), ("evidence", "evidence_packet"),
                              ("relations", "relation_verification_packet"))
        }
        expected_packets = {
            role: digest(reader.cache[inp["packet_bindings"][key]["path"]])
            for role, key in (("claims", "claim_packet"), ("evidence", "evidence_packet"),
                              ("relations", "relation_verification_packet"))
        }
        expected = {"subject": inp["subject"], "packet_sha256": expected_packets,
                    "claim_set_id": packets["claims"]["claim_set"]["claim_set_id"]}
        for key, value in expected.items():
            if graph[key] != value:
                raise self.base.BindingError("dependency_graph_" + key + "_mismatch")
        claims = self.base._index(packets["claims"]["claim_set"]["claims"], "claim_id")
        evidence = self.base._index(packets["evidence"]["evidence_items"], "evidence_id")
        nodes = sorted(["claim:" + key for key in claims] + ["evidence:" + key for key in evidence])
        if len(nodes) > MAX_GRAPH_NODES:
            raise self.base.BindingError("dependency_graph_node_limit")
        known = set(nodes)
        self.base._index(graph["dependency_edges"], "edge_id")
        edges: list[dict[str, Any]] = []
        signatures: set[tuple[str, str, str]] = set()
        for edge in graph["dependency_edges"]:
            source = edge["from"]["kind"] + ":" + edge["from"]["object_id"]
            target = edge["to"]["kind"] + ":" + edge["to"]["object_id"]
            if source not in known or target not in known:
                raise self.base.BindingError("dependency_graph_unknown_endpoint")
            signature = (edge["type"], source, target)
            if signature in signatures:
                raise self.base.BindingError("duplicate_typed_dependency_edge")
            signatures.add(signature)
            edges.append({"edge_key": "graph:" + edge["edge_id"], "from": source, "to": target,
                          "edge_type": edge["type"], "origin": "explicit_dependency_graph",
                          "binding_id": None, "declared_relation_type": None})
        ignored: list[dict[str, str]] = []
        for relation in packets["relations"]["relations"]:
            kind = relation["relation_type"]
            if kind not in DEPENDENCY_RELATIONS:
                ignored.append({"binding_id": relation["binding_id"], "relation_type": kind,
                                "reason": "not_a_dependency_relation_in_this_profile"})
                continue
            # Every declared supports/derived_from relation is projected, including
            # unresolved or unperformed ones. This is not a supported-claim verdict.
            edges.append({"edge_key": "relation:" + relation["binding_id"],
                          "from": "claim:" + relation["claim_id"],
                          "to": "evidence:" + relation["evidence_id"],
                          "edge_type": "claim_to_evidence_relation", "origin": "relation_packet",
                          "binding_id": relation["binding_id"], "declared_relation_type": kind})
        if len(edges) > MAX_GRAPH_EDGES:
            raise self.base.BindingError("dependency_graph_edge_limit")
        edges.sort(key=lambda e: e["edge_key"])
        analysis = analyze_projection(nodes, edges)
        self.report["claim_materialization_status"] = packets["claims"]["claim_set"]["materialization_status"]
        self.report["nodes"] = nodes
        self.report["edges"] = edges
        self.report["ignored_relations"] = sorted(ignored, key=lambda e: e["binding_id"])
        self.report["cyclic_components"] = analysis["cyclic_components"]
        self.report["counts"] = {
            "nodes": len(nodes), "claims": len(claims), "evidence_items": len(evidence),
            "explicit_edges": len(graph["dependency_edges"]),
            "derived_relation_edges": len(edges) - len(graph["dependency_edges"]),
            "ignored_relations": len(ignored), "edges": len(edges),
            "components": analysis["component_count"],
            "cyclic_components": len(analysis["cyclic_components"]),
        }
        self.report["cycle_detection"] = {
            "status": "completed", "result": analysis["result"],
            "algorithm": "iterative_scc_and_directed_witness_v1", "reason": None}

    def finish(self) -> dict[str, Any]:
        unique = {(i["severity"], i["object_id"], i["code"]): i for i in self.report["issues"]}
        self.report["issues"] = [unique[key] for key in sorted(unique)]
        severities = {i["severity"] for i in self.report["issues"]}
        if "invalid" in severities:
            state = "invalid"
        elif "incomplete" in severities or self.report["cycle_detection"]["status"] != "completed":
            state = "incomplete"
        else:
            state = "analyzed"
        self.report["status"] = STATUSES[state]
        self.schemas.validate("report", self.report)
        return self.report


def verify_cycles(root: Path, input_path: str, expected_input_sha256: str,
                  carriers_path: str, expected_carriers_sha256: str,
                  record_set_path: str, expected_record_set_sha256: str, *,
                  binding_profile: str, cycle_profile: str) -> dict[str, Any]:
    records = load_record_checker()
    base = records.load_binding_checker()
    review = CycleReview(records, base, binding_profile)
    child = review.record_review
    try:
        if cycle_profile != PROFILE:
            raise base.BindingError("unsupported_cycle_profile")
        for key, value in (("input", expected_input_sha256), ("carriers", expected_carriers_sha256),
                           ("record_set", expected_record_set_sha256)):
            if not isinstance(value, str) or base.HASH_RE.fullmatch(value) is None:
                raise base.BindingError("invalid_expected_" + key + "_digest")
            review.report["expected_digests"][key] = value
            child.report["expected_digests"][key] = value
        with base.BundleReader(root) as reader:
            try:
                record_set = child.bound_set(reader, record_set_path, expected_record_set_sha256)
                child.prepare(reader, record_set, input_path=input_path, input_digest=expected_input_sha256,
                              carriers_path=carriers_path, carriers_digest=expected_carriers_sha256)
                if child.run_base(reader, input_path, expected_input_sha256, carriers_path, expected_carriers_sha256):
                    child.records(reader, record_set, input_path)
            except base.BindingError as exc:
                child.issue(exc.code, "bundle", exc.severity)
            if review.capture_records():
                review.observe(reader, input_path)
    except base.BindingError as exc:
        review.issue(exc.code, "bundle", exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--carriers", required=True)
    parser.add_argument("--expected-carriers-sha256", required=True)
    parser.add_argument("--record-set", required=True)
    parser.add_argument("--expected-record-set-sha256", required=True)
    parser.add_argument("--binding-profile", choices=("wp2a", "wp2b-json-pointer-v1"), required=True)
    parser.add_argument("--cycle-profile", choices=(PROFILE,), required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_cycles(args.bundle_root, args.input, args.expected_input_sha256,
                               args.carriers, args.expected_carriers_sha256,
                               args.record_set, args.expected_record_set_sha256,
                               binding_profile=args.binding_profile, cycle_profile=args.cycle_profile)
    except Exception as exc:
        print("Anchor cycle checker error: " + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report_bytes(report))
    return {STATUSES["analyzed"]: 0, STATUSES["invalid"]: 1,
            STATUSES["incomplete"]: 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
