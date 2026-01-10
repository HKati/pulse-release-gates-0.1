#!/usr/bin/env python3
"""
check_paradox_diagram_v0_contract.py

Fail-closed contract checker for Paradox Diagram v0.

Enforces:
- Schema validation (JSON Schema) when available (unless --skip-schema)
- Deterministic invariants (ordering, IDs, endpoint validity, non-causal guardrails)

New:
- --skip-schema / --skip_schema:
  Skip JSON Schema validation (useful in dependency-light CI where jsonschema isn't installed).
  Invariants still run and failures are still fail-closed.

Exit codes:
- 0 on success
- 2 on contract violation / error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DIAGRAM_SCHEMA = "PULSE_paradox_diagram_v0"


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _node_id_ref(ref_id: str) -> str:
    return "r_" + _sha256_hex("ref\n" + ref_id)[:16]


def _node_id_atom(core_atom_id: str) -> str:
    return "n_" + _sha256_hex("atom\n" + core_atom_id)[:16]


def _edge_id_co_occurrence(a: str, b: str) -> str:
    aa, bb = sorted([a, b])
    return "e_" + _sha256_hex("co_occurrence\n" + aa + "\n" + bb)[:16]


def _edge_id_reference_relation(atom_node_id: str, ref_node_id: str) -> str:
    return "e_" + _sha256_hex("reference_relation\n" + atom_node_id + "\n" + ref_node_id)[:16]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(path: Path) -> Dict[str, Any]:
    obj = _load_json(path)
    if not isinstance(obj, dict):
        raise ValueError("Schema file must be a JSON object.")
    return obj


def _find_diagram_obj(raw: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the diagram artifact itself (schema == PULSE_paradox_diagram_v0), or
      - a wrapper object containing a nested diagram artifact (possibly deeply nested).

    Deterministic unwrap:
      - dict keys are scanned in sorted order
      - lists are scanned in natural index order
    """
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object (dict).")

    def walk(x: Any) -> Optional[Dict[str, Any]]:
        if isinstance(x, dict):
            if x.get("schema") == DIAGRAM_SCHEMA:
                return x
            for k in sorted(x.keys(), key=lambda kk: str(kk)):
                res = walk(x.get(k))
                if res is not None:
                    return res
        elif isinstance(x, list):
            for item in x:
                res = walk(item)
                if res is not None:
                    return res
        return None

    found = walk(raw)
    if found is None:
        raise ValueError(f"Could not locate diagram object with schema == {DIAGRAM_SCHEMA}.")
    return found


def _schema_validate(diagram: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validate using jsonschema. Import happens here (after args parsing),
    so --skip-schema can be used even if jsonschema isn't installed.
    """
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "jsonschema is not available but schema validation is required.\n"
            "Install 'jsonschema' or run with --skip-schema.\n"
            f"Import error: {e}"
        )

    jsonschema.validate(instance=diagram, schema=schema)


def _safe_int(x: Any, default: int) -> int:
    if isinstance(x, bool):
        return default
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        try:
            return int(x)
        except Exception:
            return default
    return default


def _node_sort_key(n: Dict[str, Any]) -> Tuple[int, str, int, str]:
    """
    Canonical node ordering:
      - reference nodes first by ref_id asc
      - then atom nodes by rank asc, then core_atom_id asc
    """
    if n.get("kind") == "reference":
        return (0, str(n.get("ref_id", "")), 0, "")
    rank = _safe_int(n.get("rank"), 10**9)
    return (1, "", rank, str(n.get("core_atom_id", "")))


def _edge_group(kind: str) -> int:
    if kind == "co_occurrence":
        return 0
    if kind == "reference_relation":
        return 1
    return 9


def _edge_sort_key(e: Dict[str, Any]) -> Tuple[int, str, str, str]:
    return (
        _edge_group(str(e.get("kind", ""))),
        str(e.get("a", "")),
        str(e.get("b", "")),
        str(e.get("edge_id", "")),
    )


def _scan_forbidden_metadata(obj: Any) -> List[str]:
    forbidden_keys = {
        "timestamp",
        "created_at",
        "generated_at",
        "wall_clock",
        "wallclock",
        "now",
        "datetime",
        "run_started_at",
    }

    hits: List[str] = []

    def walk(x: Any, path: str) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and k in forbidden_keys:
                    hits.append(f"{path}.{k}" if path else k)
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")

    walk(obj, "")
    return hits


def _invariants(diagram: Dict[str, Any], allow_metadata_nondeterminism: bool) -> None:
    errors: List[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    if diagram.get("schema") != DIAGRAM_SCHEMA:
        err(f"$.schema must be '{DIAGRAM_SCHEMA}'")

    v = diagram.get("version")
    if v not in (0, "v0"):
        err("$.version must be 0 or 'v0'")

    notes = diagram.get("notes")
    if not isinstance(notes, list):
        err("$.notes must be a list")
    else:
        codes: List[str] = []
        for i, n in enumerate(notes):
            if not isinstance(n, dict):
                err(f"$.notes[{i}] must be an object")
                continue
            code = n.get("code")
            if not isinstance(code, str) or not code:
                err(f"$.notes[{i}].code must be a non-empty string")
                continue
            codes.append(code)
        for required in ["NON_CAUSAL", "CI_NEUTRAL_DEFAULT"]:
            if required not in codes:
                err(f"$.notes missing required code '{required}'")

    refs = diagram.get("references")
    if not isinstance(refs, list) or len(refs) < 1:
        err("$.references must be a non-empty list")
        refs = []
    else:
        ref_ids: List[str] = []
        for i, r in enumerate(refs):
            if not isinstance(r, dict):
                err(f"$.references[{i}] must be an object")
                continue
            rid = r.get("ref_id")
            if not isinstance(rid, str) or not rid:
                err(f"$.references[{i}].ref_id must be a non-empty string")
                continue
            ref_ids.append(rid)
        if ref_ids and ref_ids != sorted(ref_ids):
            err("$.references must be sorted by ref_id asc")

    nodes = diagram.get("nodes")
    if not isinstance(nodes, list) or len(nodes) < 1:
        err("$.nodes must be a non-empty list")
        nodes = []

    node_by_id: Dict[str, Dict[str, Any]] = {}
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            err(f"$.nodes[{i}] contains non-object entry")
            continue
        nid = n.get("node_id")
        if not isinstance(nid, str) or not nid:
            err(f"$.nodes[{i}].node_id must be a non-empty string")
            continue
        if nid in node_by_id:
            err(f"duplicate node_id: {nid}")
            continue
        node_by_id[nid] = n

    for nid, n in node_by_id.items():
        kind = n.get("kind")
        if kind == "reference":
            rid = n.get("ref_id")
            if not isinstance(rid, str) or not rid:
                err(f"reference node missing ref_id (node_id={nid})")
            else:
                exp = _node_id_ref(rid)
                if nid != exp:
                    err(f"reference node_id mismatch (got={nid}, expected={exp}, ref_id={rid})")
        elif kind == "atom":
            aid = n.get("core_atom_id")
            if not isinstance(aid, str) or not aid:
                err(f"atom node missing core_atom_id (node_id={nid})")
            else:
                exp = _node_id_atom(aid)
                if nid != exp:
                    err(f"atom node_id mismatch (got={nid}, expected={exp}, core_atom_id={aid})")

            if "rank" in n and not isinstance(n.get("rank"), int):
                err(f"atom node rank must be int when present (node_id={nid})")
        else:
            err(f"unknown node kind '{kind}' (node_id={nid})")

    node_keys = [_node_sort_key(n) for n in nodes if isinstance(n, dict)]
    if node_keys and node_keys != sorted(node_keys):
        err("$.nodes must be in canonical order (reference by ref_id, then atoms by rank/core_atom_id)")

    edges = diagram.get("edges")
    if not isinstance(edges, list):
        err("$.edges must be a list")
        edges = []

    edge_seen: set[str] = set()
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            err(f"$.edges[{i}] contains non-object entry")
            continue
        eid = e.get("edge_id")
        if not isinstance(eid, str) or not eid:
            err(f"$.edges[{i}].edge_id must be a non-empty string")
            continue
        if eid in edge_seen:
            err(f"duplicate edge_id: {eid}")
        edge_seen.add(eid)

    seen_ref_rel = False
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        a = e.get("a")
        b = e.get("b")
        eid = e.get("edge_id")

        if not isinstance(a, str) or not isinstance(b, str):
            err(f"$.edges[{i}]: edge endpoints a/b must be strings")
            continue
        if a not in node_by_id:
            err(f"$.edges[{i}]: edge references missing node a={a}")
            continue
        if b not in node_by_id:
            err(f"$.edges[{i}]: edge references missing node b={b}")
            continue

        ak = node_by_id[a].get("kind")
        bk = node_by_id[b].get("kind")

        if kind == "co_occurrence":
            if seen_ref_rel:
                err("co_occurrence edges must precede reference_relation edges")
            if ak != "atom" or bk != "atom":
                err("co_occurrence must connect atom <-> atom")
            if a > b:
                err("co_occurrence endpoints must be canonicalized with a<=b")
            exp = _edge_id_co_occurrence(a, b)
            if isinstance(eid, str) and eid != exp:
                err(f"co_occurrence edge_id mismatch (got={eid}, expected={exp})")
            if "directed" in e:
                err("co_occurrence must not include 'directed'")
        elif kind == "reference_relation":
            seen_ref_rel = True
            if ak != "atom" or bk != "reference":
                err("reference_relation must connect atom -> reference (a atom, b reference)")
            if "directed" in e and e.get("directed") is not True:
                err("reference_relation directed must be true if present")
            exp = _edge_id_reference_relation(a, b)
            if isinstance(eid, str) and eid != exp:
                err(f"reference_relation edge_id mismatch (got={eid}, expected={exp})")
        else:
            err(f"unknown edge kind '{kind}'")

    edge_keys = [_edge_sort_key(e) for e in edges if isinstance(e, dict)]
    if edge_keys and edge_keys != sorted(edge_keys):
        err("$.edges must be in canonical order (co_occurrence then reference_relation; within: a,b,edge_id)")

    if not allow_metadata_nondeterminism:
        hits = _scan_forbidden_metadata(diagram)
        if hits:
            err("forbidden nondeterministic metadata keys found: " + ", ".join(hits))

    if errors:
        raise RuntimeError("Diagram contract violation(s):\n" + "\n".join(f" - {x}" for x in errors))


def _repo_root_from_here() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        if (p / "schemas").is_dir():
            return p
        if (p / ".git").exists():
            return p
    try:
        return here.parents[1]
    except Exception:
        return here.parent


def _looks_like_bundle_builder_args(argv: List[str]) -> bool:
    bundle_flags = {"--field", "--edges", "--out-dir", "--out_dir", "--k", "--metric"}
    return any(a in bundle_flags for a in argv)


def _has_in_flag(argv: List[str]) -> bool:
    for a in argv:
        if a in ("--in", "--input"):
            return True
        if a.startswith("--in=") or a.startswith("--input="):
            return True
    return False


def _boolish(v: Any) -> bool:
    # Accept: --skip-schema, --skip-schema true, --skip-schema=true
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {v!r}")


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    # Normalize argv so miswired calls (import main() without argv) are diagnosable.
    if argv is None:
        argv = sys.argv[1:]

    # If someone accidentally wires this checker where the bundle builder should run,
    # make it very explicit in CI logs.
    if _looks_like_bundle_builder_args(argv) and not _has_in_flag(argv):
        raise RuntimeError(
            "Miswired invocation detected.\n"
            "This file is the Paradox Diagram v0 contract checker and requires --in/--input.\n"
            "But it looks like it is being invoked with reviewer bundle builder flags "
            "(--field/--edges/--out-dir/--k/--metric).\n\n"
            "Most likely causes:\n"
            "  1) scripts/paradox_core_reviewer_bundle_v0.py was overwritten with this checker,\n"
            "     OR\n"
            "  2) the bundle builder imports this checker and calls main() without argv,\n"
            "     so the checker tries to parse the bundle builder sys.argv.\n\n"
            "Fix: ensure the bundle builder runs its own argparse, and call this checker as:\n"
            "  python scripts/check_paradox_diagram_v0_contract.py --in <diagram.json> [--skip-schema]\n"
            "or (if imported): main([\"--in\", <path>, \"--skip-schema\"])."
        )

    repo_root = _repo_root_from_here()
    default_schema = repo_root / "schemas" / "PULSE_paradox_diagram_v0.schema.json"

    ap = argparse.ArgumentParser(prog="check_paradox_diagram_v0_contract.py")
    ap.add_argument(
        "--in",
        "--input",
        dest="in_path",
        required=True,
        help="Path to paradox_diagram_v0.json (or wrapper JSON containing it)",
    )
    ap.add_argument(
        "--schema",
        dest="schema_path",
        default=str(default_schema),
        help="Path to diagram JSON schema",
    )
    ap.add_argument(
        "--allow-metadata-nondeterminism",
        action="store_true",
        help="Allow nondeterministic metadata fields (diagnostic escape hatch)",
    )
    ap.add_argument(
        "--skip-schema",
        "--skip_schema",
        nargs="?",
        const=True,
        default=False,
        type=_boolish,
        help="Skip JSON Schema validation (useful when jsonschema is unavailable). Invariants still run.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress warnings/errors output (exit code still indicates status)",
    )
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = _parse_args(argv)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    in_path = Path(args.in_path)
    if not in_path.exists():
        if not args.quiet:
            print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        return 2

    try:
        raw = _load_json(in_path)
        diagram = _find_diagram_obj(raw)

        # Optional schema validation
        if not args.skip_schema:
            schema_path = Path(args.schema_path)
            if not schema_path.exists():
                raise RuntimeError(f"Schema not found: {schema_path}")
            schema = _load_schema(schema_path)
            _schema_validate(diagram=diagram, schema=schema)
        else:
            if not args.quiet:
                print("WARNING: schema validation skipped (--skip-schema).", file=sys.stderr)

        # Invariants always run (fail-closed)
        _invariants(diagram=diagram, allow_metadata_nondeterminism=bool(args.allow_metadata_nondeterminism))

    except Exception as e:
        if not args.quiet:
            print(f"ERROR: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
