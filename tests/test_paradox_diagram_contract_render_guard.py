#!/usr/bin/env python3
"""
Regression tests for Paradox diagram v0 contract + render gating.

What this locks in:
1) The GitHub Actions workflow gates SVG rendering on contract validity
   (so invalid input won't produce/publish misleading artifacts).
2) The contract checker rejects invalid inputs (fail-closed at the input boundary).
3) A minimal schema-derived valid input passes contract and can be rendered to SVG.

This test is deterministic, stdlib-only, and does not require network access.

Run (direct):
  python tests/test_paradox_diagram_contract_render_guard.py

Run (pytest):
  pytest -q
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _pick_number(schema: Dict[str, Any]) -> float:
    # Choose a number that satisfies >= minimum / exclusiveMinimum if present.
    if "minimum" in schema:
        return float(schema["minimum"])
    if "exclusiveMinimum" in schema:
        # small epsilon above exclusiveMinimum
        return float(schema["exclusiveMinimum"]) + 1.0
    # default safe non-negative
    return 0.0


def _pick_int(schema: Dict[str, Any]) -> int:
    if "minimum" in schema:
        return int(schema["minimum"])
    if "exclusiveMinimum" in schema:
        return int(schema["exclusiveMinimum"]) + 1
    return 0


def _pick_string(schema: Dict[str, Any]) -> str:
    if "const" in schema:
        return str(schema["const"])
    if "enum" in schema and schema["enum"]:
        return str(schema["enum"][0])

    fmt = schema.get("format")
    if fmt == "date-time":
        return "2026-02-06T00:00:00Z"

    min_len = int(schema.get("minLength") or 1)
    return "x" * max(1, min_len)


def _normalize_type(schema: Dict[str, Any]) -> Optional[str]:
    t = schema.get("type")
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        # Prefer a non-null type if union includes null.
        for cand in t:
            if cand != "null":
                return cand
        return t[0] if t else None
    return None


def _gen_from_schema(schema: Dict[str, Any]) -> Any:
    """
    Generate a minimal instance that should satisfy common JSON Schema constraints.
    Supports: type/object/array/string/number/integer/boolean, enum/const, anyOf/oneOf/allOf.
    """
    if "const" in schema:
        return schema["const"]

    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    # Handle composition keywords
    for key in ("oneOf", "anyOf"):
        if key in schema and isinstance(schema[key], list) and schema[key]:
            return _gen_from_schema(schema[key][0])

    if "allOf" in schema and isinstance(schema["allOf"], list) and schema["allOf"]:
        # Merge object-ish allOf schemas minimally: generate from first, then overlay required fields from others.
        base = _gen_from_schema(schema["allOf"][0])
        if isinstance(base, dict):
            for sub in schema["allOf"][1:]:
                sub_req = sub.get("required") or []
                props = sub.get("properties") or {}
                for k in sub_req:
                    if k not in base and k in props:
                        base[k] = _gen_from_schema(props[k])
        return base

    t = _normalize_type(schema)

    if t == "object" or (t is None and "properties" in schema):
        out: Dict[str, Any] = {}
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        for k in required:
            if k not in props:
                # If schema marks it required but doesn't define it, keep it explicit as null-ish.
                out[k] = None
            else:
                out[k] = _gen_from_schema(props[k])
        # Respect minProperties if it demands more than required
        min_props = int(schema.get("minProperties") or 0)
        if min_props > len(out):
            # Add additional properties deterministically if available.
            for k, v_schema in props.items():
                if k in out:
                    continue
                out[k] = _gen_from_schema(v_schema)
                if len(out) >= min_props:
                    break
        return out

    if t == "array":
        items_schema = schema.get("items") or {}
        min_items = int(schema.get("minItems") or 0)
        return [_gen_from_schema(items_schema) for _ in range(min_items)]

    if t == "string":
        return _pick_string(schema)

    if t == "integer":
        return _pick_int(schema)

    if t == "number":
        return _pick_number(schema)

    if t == "boolean":
        # default false
        return False

    # Fallback: if schema is very permissive, return an empty object.
    return {}


# -------------------------
# Tests (pytest entrypoints)
# -------------------------

def test_workflow_gates_render_on_contract_ok() -> None:
    """
    Hard regression lock: the workflow must NOT render SVG unless contract check succeeded.
    This avoids publishing misleading diagrams from invalid inputs.
    """
    root = _repo_root()
    wf = root / ".github" / "workflows" / "pulse-paradox-gate.yml"
    assert wf.exists(), f"missing workflow: {wf}"

    txt = wf.read_text(encoding="utf-8")

    # Ensure the contract step exists with the expected id
    assert re.search(r"^\s*id:\s*paradox_contract\s*$", txt, re.MULTILINE), (
        "Expected workflow to set id: paradox_contract on the contract-check step."
    )

    # Ensure render step is gated on that output
    assert re.search(
        r"steps\.paradox_contract\.outputs\.ok\s*==\s*'true'",
        txt,
    ), (
        "Expected render step to be gated on steps.paradox_contract.outputs.ok == 'true'. "
        "This prevents rendering/publishing SVG from invalid contract input."
    )


def test_contract_rejects_invalid_input() -> None:
    root = _repo_root()
    contract = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    assert contract.exists(), f"missing contract checker: {contract}"

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        invalid = base / "invalid.json"
        _write_json(invalid, {})  # intentionally invalid (should miss required keys)

        r = _run([sys.executable, str(contract), "--in", str(invalid)])
        assert r.returncode != 0, (
            "Expected contract checker to fail on invalid input.\n"
            f"stdout:\n{r.stdout}\n\nstderr:\n{r.stderr}"
        )


def test_valid_input_passes_contract_and_renders_svg() -> None:
    root = _repo_root()
    schema = root / "schemas" / "paradox_diagram_input_v0.schema.json"
    contract = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    renderer = root / "tools" / "render_paradox_diagram_v0.py"

    assert schema.exists(), f"missing schema: {schema}"
    assert contract.exists(), f"missing contract checker: {contract}"
    assert renderer.exists(), f"missing renderer wrapper: {renderer}"

    schema_obj = _read_json(schema)
    assert isinstance(schema_obj, dict), "schema must be a JSON object"

    valid_obj = _gen_from_schema(schema_obj)

    # Extra safety: ensure numbers are not booleans (bool is int subclass in Python).
    # If generator produced booleans for numeric fields by accident, convert them.
    def _fix_bool_numbers(o: Any) -> Any:
        if isinstance(o, dict):
            return {k: _fix_bool_numbers(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_fix_bool_numbers(v) for v in o]
        if isinstance(o, bool):
            return o
        return o

    valid_obj = _fix_bool_numbers(valid_obj)

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        inp = base / "paradox_diagram_input_v0.json"
        out_svg = base / "paradox_diagram_v0.svg"

        _write_json(inp, valid_obj)

        # Contract must pass
        r1 = _run([sys.executable, str(contract), "--in", str(inp)])
        assert r1.returncode == 0, (
            "Expected contract checker to accept schema-derived minimal valid input.\n"
            f"stdout:\n{r1.stdout}\n\nstderr:\n{r1.stderr}\n\ninput:\n{inp.read_text(encoding='utf-8')}"
        )

        # Renderer must produce an SVG
        r2 = _run([sys.executable, str(renderer), "--in", str(inp), "--out", str(out_svg)])
        assert r2.returncode == 0, (
            "Expected renderer to succeed for contract-valid input.\n"
            f"stdout:\n{r2.stdout}\n\nstderr:\n{r2.stderr}\n\ninput:\n{inp.read_text(encoding='utf-8')}"
        )

        assert out_svg.exists(), f"Expected SVG output to exist: {out_svg}"
        data = out_svg.read_bytes()
        assert len(data) > 50, "SVG output seems too small to be valid"
        # Soft signature check
        assert b"<svg" in data[:5000], "Expected SVG output to contain <svg tag near the top"


# -------------------------
# Script entrypoint (direct run)
# -------------------------

def main() -> int:
    test_workflow_gates_render_on_contract_ok()
    test_contract_rejects_invalid_input()
    test_valid_input_passes_contract_and_renders_svg()
    print("OK: paradox diagram contract + workflow render gating + svg render smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
