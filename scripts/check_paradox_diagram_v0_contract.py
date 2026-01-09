#!/usr/bin/env python3
"""
Fail-closed contract checker for Paradox Diagram v0.

What this checks (v0):
- JSON Schema validation (schemas/PULSE_paradox_diagram_v0.schema.json)
- Referential integrity:
    - node_id uniqueness
    - edge_id uniqueness
    - edge endpoints exist in nodes
    - endpoint kinds match edge kind constraints
- Stable ID contract:
    - node_id recomputed from ref_id / core_atom_id
    - edge_id recomputed from endpoints (canonical rules)
- Deterministic ordering:
    - references sorted by ref_id
    - nodes: reference nodes (ref_id asc) then atom nodes (rank asc, core_atom_id asc)
    - edges: co_occurrence (a,b,edge_id) then reference_relation (a,b,edge_id)
- Optional nondeterminism guardrails for metadata:
    - forbids obvious wall-clock / CI run fields at top-level and inside run_context
      (can be disabled via --allow-metadata-nondeterminism)

Notes:
- This checker is overlay-local: it reads only local files, no network calls.
- It is intentionally strict: fail-closed on contract violations.

Usage:
  python scripts/check_paradox_diagram_v0_contract.py --in out/paradox_diagram_v0.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DIAGRAM_SCHEMA = "PULSE_paradox_diagram_v0"
DIAGRAM_VERSION = 0


def _sha256_hex_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _id16(prefix: str, canonical_payload: str) -> str:
    return f"{prefix}{_sha256_hex_of_text(canonical_payload)[:16]}"


def expected_node_id_reference(ref_id: str) -> str:
    return _id16("r_", "ref\n" + ref_id)


def expected_node_id_atom(core_atom_id: str) -> str:
    return _id16("n_", "atom\n" + core_atom_id)


def expected_edge_id_co_occurrence(a_node_id: str, b_node_id: str) -> str:
    a_id, b_id = sorted([a_node_id, b_node_id])
    return _id16("e_", "co_occurrence\n" + a_id + "\n" + b_id)


def expected_edge_id_reference_relation(atom_node_id: str, ref_node_id: str) -> str:
    return _id16("e_", "reference_relation\n" + atom_node_id + "\n" + ref_node_id)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _find_diagram_obj(raw: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the diagram artifact itself (schema == PULSE_paradox_diagram_v0), or
      - a wrapper object containing a nested diagram artifact.

    Deterministic unwrap: scan nested dicts in sorted key order.
    """
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object (dict).")

    if raw.get("schema") == DIAGRAM_SCHEMA:
        return raw

    for k in sorted(raw.keys()):
        v = raw.get(k)
        if isinstance(v, dict) and v.get("schema") == DIAGRAM_SCHEMA:
            return v

    raise ValueError(f"Could not locate diagram object with schema == {DIAGRAM_SCHEMA}.")


def _default_schema_path() -> Path:
    # repo_root/scripts/this_file.py -> repo_root/schemas/...
    here = Path(__file__).resolve()
    repo_root = here.parents[1]
    return repo_root / "schemas" / "PULSE_paradox_diagram_v0.schema.json"


def _validate_jsonschema(diagram: Dict[str, Any], schema_path: Path) -> List[str]:
    """
    Return a list of human-friendly error strings.
    Fail-closed: if jsonschema isn't available, return a single error.
    """
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        return [f"jsonschema import failed: {e}. Install 'jsonschema' to validate schema contract."]

    schema = _load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)

    errors = []
    for err in sorted(validator.iter_errors(diagram), key=lambda e: (list(e.absolute_path), e.message)):
        path = "$"
        for p in err.absolute_path:
            if isinstance(p, int):
                path += f"[{p}]"
            else:
                path += f".{p}"
        errors.append(f"{path}: {err.message}")
    return errors


def _is_sorted_by(items: List[Any], key_fn) -> bool:
    keys = [key_fn(x) for x in items]
    return keys == sorted(keys)


def _first_sort_mismatch(items: List[Any], key_fn) -> Optional[Tuple[int, Any, Any]]:
    keys = [key_fn(x) for x in items]
    sorted_keys = sorted(keys)
    if keys == sorted_keys:
        return None
    for i, (a, b) in enumerate(zip(keys, sorted_keys)):
        if a != b:
            return (i, a, b)
    return (len(items) - 1, keys[-1], sorted_keys[-1])


def _format_path(parts: List[str]) -> str:
    if not parts:
        return "$"
    out = "$"
    for p in parts:
        if p.startswith("["):
            out += p
        else:
            out += "." + p
    return out


def _collect_errors() -> Tuple[List[str], Any]:
    errs: List[str] = []

    def add(path: str, msg: str) -> None:
        errs.append(f"{path}: {msg}")

    return errs, add


def _check_required_notes(diagram: Dict[str, Any]) -> List[str]:
    errs, add = _collect_errors()
    notes = diagram.get("notes", [])
    if not isinstance(notes, list):
        add("$.notes", "must be a list")
        return errs

    codes = []
    for i, n in enumerate(notes):
        if not isinstance(n, dict):
            add(f"$.notes[{i}]", "must be an object")
            continue
        code = n.get("code")
        if isinstance(code, str):
            codes.append(code)

    for required in ["NON_CAUSAL", "CI_NEUTRAL_DEFAULT"]:
        if required not in codes:
            add("$.notes", f"missing required note code '{required}'")

    return errs


FORBIDDEN_META_KEYS = {
    # obvious wall-clock / generation-time fields:
    "timestamp",
    "generated_at",
    "created_at",
    "built_at",
    # CI run identifiers:
    "run_number",
    "ci_run_number",
    "github_run_id",
    "github_run_number",
    "workflow_run_id",
}


def _check_metadata_nondeterminism(diagram: Dict[str, Any]) -> List[str]:
    """
    Strict but targeted: checks top-level keys and run_context for forbidden meta keys.
    Does NOT scan evidence payloads to avoid false positives in diagnostic evidence.
    """
    errs, add = _collect_errors()

    # top-level forbidden keys
    for k in sorted(diagram.keys()):
        if k in FORBIDDEN_META_KEYS:
            add("$", f"forbidden nondeterministic metadata key '{k}' present at top-level")

    # run_context forbidden keys (recursive)
    rc = diagram.get("run_context")
    if rc is None:
        return errs
    if not isinstance(rc, dict):
        add("$.run_context", "must be an object if present")
        return errs

    def walk(obj: Any, path_parts: List[str]) -> None:
        if isinstance(obj, dict):
            for kk in sorted(obj.keys()):
                if kk in FORBIDDEN_META_KEYS:
                    add(_format_path(["run_context"] + path_parts + [kk]), f"forbidden nondeterministic key '{kk}'")
                vv = obj[kk]
                walk(vv, path_parts + [kk])
        elif isinstance(obj, list):
            for i, vv in enumerate(obj):
                walk(vv, path_parts + [f"[{i}]"])

    walk(rc, [])
    return errs


def _check_schema_version(diagram: Dict[str, Any]) -> List[str]:
    errs, add = _collect_errors()
    if diagram.get("schema") != DIAGRAM_SCHEMA:
        add("$.schema", f"must be '{DIAGRAM_SCHEMA}'")
    if diagram.get("version") != DIAGRAM_VERSION:
        add("$.version", f"must be {DIAGRAM_VERSION}")
    return errs


def _check_references(diagram: Dict[str, Any]) -> List[str]:
    errs, add = _collect_errors()
    refs = diagram.get("references")
    if not isinstance(refs, list) or len(refs) < 1:
        add("$.references", "must be a non-empty list")
        return errs

    # ordering by ref_id
    def ref_key(r: Any) -> str:
        if not isinstance(r, dict):
            return ""
        return str(r.get("ref_id", ""))

    mm = _first_sort_mismatch(refs, ref_key)
    if mm is not None:
        i, got, exp = mm
        add("$.references", f"must be sorted by ref_id asc (first mismatch at index {i}: got {got} expected {exp})")

    # uniqueness
    seen = set()
    for i, r in enumerate(refs):
        if not isinstance(r, dict):
            add(f"$.references[{i}]", "must be an object")
            continue
        ref_id = r.get("ref_id")
        if not isinstance(ref_id, str) or not ref_id:
            add(f"$.references[{i}].ref_id", "must be a non-empty string")
            continue
        if ref_id in seen:
            add(f"$.references[{i}].ref_id", f"duplicate ref_id '{ref_id}'")
        seen.add(ref_id)

    return errs


def _check_nodes(diagram: Dict[str, Any]) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    errs, add = _collect_errors()
    nodes = diagram.get("nodes")
    node_by_id: Dict[str, Dict[str, Any]] = {}

    if not isinstance(nodes, list) or len(nodes) < 1:
        add("$.nodes", "must be a non-empty list")
        return errs, node_by_id

    # uniqueness + mapping
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            add(f"$.nodes[{i}]", "must be an object")
            continue
        nid = n.get("node_id")
        if not isinstance(nid, str) or not nid:
            add(f"$.nodes[{i}].node_id", "must be a non-empty string")
            continue
        if nid in node_by_id:
            add(f"$.nodes[{i}].node_id", f"duplicate node_id '{nid}'")
            continue
        node_by_id[nid] = n

    # stable node_id recompute
    for nid, n in sorted(node_by_id.items(), key=lambda kv: kv[0]):
        kind = n.get("kind")
        if kind == "reference":
            ref_id = n.get("ref_id")
            if isinstance(ref_id, str) and ref_id:
                exp = expected_node_id_reference(ref_id)
                if nid != exp:
                    add(f"$.nodes[node_id={nid}]", f"reference node_id mismatch (expected {exp} from ref_id={ref_id})")
            else:
                add(f"$.nodes[node_id={nid}].ref_id", "reference node must have ref_id")
        elif kind == "atom":
            atom_id = n.get("core_atom_id")
            if isinstance(atom_id, str) and atom_id:
                exp = expected_node_id_atom(atom_id)
                if nid != exp:
                    add(f"$.nodes[node_id={nid}]", f"atom node_id mismatch (expected {exp} from core_atom_id={atom_id})")
            else:
                add(f"$.nodes[node_id={nid}].core_atom_id", "atom node must have core_atom_id")
        else:
            add(f"$.nodes[node_id={nid}].kind", f"unknown node kind '{kind}'")

    # canonical ordering
    def node_sort_key(n: Any) -> Tuple[int, str, int, str]:
        if not isinstance(n, dict):
            return (9, "", 10**9, "")
        if n.get("kind") == "reference":
            return (0, str(n.get("ref_id", "")), 0, "")
        return (1, "", int(n.get("rank", 10**9)), str(n.get("core_atom_id", "")))

    mm = _first_sort_mismatch(nodes, node_sort_key)
    if mm is not None:
        i, got, exp = mm
        add("$.nodes", f"must be in canonical order (first mismatch at index {i}: got {got} expected {exp})")

    return errs, node_by_id


def _check_edges(diagram: Dict[str, Any], node_by_id: Dict[str, Dict[str, Any]]) -> List[str]:
    errs, add = _collect_errors()

    edges = diagram.get("edges")
    if edges is None:
        add("$.edges", "must be present (may be empty list)")
        return errs
    if not isinstance(edges, list):
        add("$.edges", "must be a list")
        return errs

    # edge_id uniqueness
    seen_edge_ids = set()
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            add(f"$.edges[{i}]", "must be an object")
            continue
        eid = e.get("edge_id")
        if not isinstance(eid, str) or not eid:
            add(f"$.edges[{i}].edge_id", "must be a non-empty string")
            continue
        if eid in seen_edge_ids:
            add(f"$.edges[{i}].edge_id", f"duplicate edge_id '{eid}'")
        seen_edge_ids.add(eid)

    # endpoint existence + kinds + stable edge_id recompute
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        eid = e.get("edge_id")
        a = e.get("a")
        b = e.get("b")

        path = f"$.edges[{i}]"

        if not isinstance(a, str) or not isinstance(b, str):
            add(path, "edge endpoints 'a' and 'b' must be strings")
            continue

        if a not in node_by_id:
            add(path, f"endpoint 'a' references missing node_id '{a}'")
        if b not in node_by_id:
            add(path, f"endpoint 'b' references missing node_id '{b}'")

        if a not in node_by_id or b not in node_by_id:
            continue

        a_kind = node_by_id[a].get("kind")
        b_kind = node_by_id[b].get("kind")

        if kind == "co_occurrence":
            # must be undirected and canonicalized a<=b
            if a > b:
                add(path, f"co_occurrence endpoints must be canonicalized with a<=b (got a={a}, b={b})")
            if a_kind != "atom" or b_kind != "atom":
                add(path, "co_occurrence must connect atom <-> atom")
            # stable edge id
            exp = expected_edge_id_co_occurrence(a, b)
            if isinstance(eid, str) and eid != exp:
                add(path, f"co_occurrence edge_id mismatch (expected {exp} from endpoints)")
            # directed must not appear (schema should already enforce, but belt+suspenders)
            if "directed" in e:
                add(path, "co_occurrence must not include 'directed' field")
        elif kind == "reference_relation":
            # must be atom -> reference
            if a_kind != "atom" or b_kind != "reference":
                add(path, "reference_relation must connect atom -> reference (a atom, b reference)")
            # if directed present, must be true
            if "directed" in e and e.get("directed") is not True:
                add(path, "reference_relation 'directed' must be true if present")
            # stable edge id (atom -> ref)
            exp = expected_edge_id_reference_relation(a, b)
            if isinstance(eid, str) and eid != exp:
                add(path, f"reference_relation edge_id mismatch (expected {exp} from endpoints a->b)")
        else:
            add(path + ".kind", f"unknown edge kind '{kind}'")

    # canonical ordering for edges
    def edge_group_order(e: Any) -> int:
        if not isinstance(e, dict):
            return 9
        k = e.get("kind")
        if k == "co_occurrence":
            return 0
        if k == "reference_relation":
            return 1
        return 9

    def edge_sort_key(e: Any) -> Tuple[int, str, str, str]:
        if not isinstance(e, dict):
            return (9, "", "", "")
        grp = edge_group_order(e)
        a = str(e.get("a", ""))
        b = str(e.get("b", ""))
        eid = str(e.get("edge_id", ""))
        return (grp, a, b, eid)

    mm = _first_sort_mismatch(edges, edge_sort_key)
    if mm is not None:
        i, got, exp = mm
        add("$.edges", f"must be in canonical order (first mismatch at index {i}: got {got} expected {exp})")

    # Ensure no kind-flip back (co_occurrence must come first as a block)
    seen_ref = False
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        k = e.get("kind")
        if k == "reference_relation":
            seen_ref = True
        if k == "co_occurrence" and seen_ref:
            add(f"$.edges[{i}].kind", "co_occurrence edges must precede reference_relation edges")

    return errs


def _check_relation_to_reference(diagram: Dict[str, Any], node_by_id: Dict[str, Dict[str, Any]]) -> List[str]:
    errs, add = _collect_errors()

    refs = diagram.get("references", [])
    ref_ids = set()
    for r in refs:
        if isinstance(r, dict) and isinstance(r.get("ref_id"), str):
            ref_ids.add(r["ref_id"])

    for nid, n in sorted(node_by_id.items(), key=lambda kv: kv[0]):
        if n.get("kind") != "atom":
            continue
        rel = n.get("relation_to_reference")
        if rel is None:
            continue
        if not isinstance(rel, dict):
            add(f"$.nodes[node_id={nid}].relation_to_reference", "must be an object if present")
            continue
        rid = rel.get("ref_id")
        if isinstance(rid, str) and rid and rid not in ref_ids:
            add(f"$.nodes[node_id={nid}].relation_to_reference.ref_id", f"unknown ref_id '{rid}' (not in references[])")

    return errs


def _check_weights_rounded(diagram: Dict[str, Any]) -> List[str]:
    """
    v0 determinism: weights emitted rounded to 6 decimals.
    We enforce this softly but fail-closed if it clearly violates the rule.
    """
    errs, add = _collect_errors()

    def is_round6(x: Any) -> bool:
        if not isinstance(x, (int, float)):
            return True
        # Compare to 6-decimal rounded representation.
        y = float(f"{float(x):.6f}")
        return abs(float(x) - y) <= 1e-12

    # nodes relation_to_reference.weight
    nodes = diagram.get("nodes", [])
    if isinstance(nodes, list):
        for i, n in enumerate(nodes):
            if not isinstance(n, dict):
                continue
            rel = n.get("relation_to_reference")
            if isinstance(rel, dict) and "weight" in rel:
                if not is_round6(rel.get("weight")):
                    add(f"$.nodes[{i}].relation_to_reference.weight", "must be rounded to 6 decimals (v0)")

    # edges weight
    edges = diagram.get("edges", [])
    if isinstance(edges, list):
        for i, e in enumerate(edges):
            if not isinstance(e, dict):
                continue
            if "weight" in e and not is_round6(e.get("weight")):
                add(f"$.edges[{i}].weight", "must be rounded to 6 decimals (v0)")

    return errs


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fail-closed contract check for Paradox Diagram v0.")
    p.add_argument("--in", dest="in_path", required=True, help="Path to paradox_diagram_v0.json")
    p.add_argument("--schema", dest="schema_path", default=None, help="Path to JSON Schema (defaults to repo schemas/...)")
    p.add_argument(
        "--allow-metadata-nondeterminism",
        action="store_true",
        help="Disable the nondeterministic metadata key guardrails (top-level + run_context).",
    )
    p.add_argument("--quiet", action="store_true", help="Only print PASS/FAIL.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        return 2

    schema_path = Path(args.schema_path) if args.schema_path else _default_schema_path()
    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}", file=sys.stderr)
        return 2

    try:
        raw = _load_json(in_path)
        diagram = _find_diagram_obj(raw)
    except Exception as e:
        print(f"FAIL: parse/unwarp error: {e}", file=sys.stderr)
        return 1

    errors: List[str] = []

    # Schema + required notes (schema should catch notes, but keep explicit).
    errors.extend(_check_schema_version(diagram))
    errors.extend(_validate_jsonschema(diagram, schema_path))
    errors.extend(_check_required_notes(diagram))

    # Deterministic + integrity checks.
    errors.extend(_check_references(diagram))
    node_errs, node_by_id = _check_nodes(diagram)
    errors.extend(node_errs)
    errors.extend(_check_edges(diagram, node_by_id))
    errors.extend(_check_relation_to_reference(diagram, node_by_id))
    errors.extend(_check_weights_rounded(diagram))

    if not args.allow_metadata_nondeterminism:
        errors.extend(_check_metadata_nondeterminism(diagram))

    if errors:
        if args.quiet:
            print("FAIL")
        else:
            print("FAIL: Paradox Diagram v0 contract violation(s):", file=sys.stderr)
            for msg in sorted(errors):
                print(" - " + msg, file=sys.stderr)
        return 1

    if args.quiet:
        print("PASS")
    else:
        print("PASS: Paradox Diagram v0 contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
