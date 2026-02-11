#!/usr/bin/env python3
"""
Fail-closed contract validation for theory_overlay_inputs_v0 bundles.

- Validates JSON syntax
- Validates against schemas/theory_overlay_inputs_v0.schema.json (if jsonschema installed)
- Provides a minimal fallback validator if jsonschema is unavailable
- Exits with code 2 on any contract violation (fail-closed)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_DEFAULT_PATH = "schemas/theory_overlay_inputs_v0.schema.json"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _die(msg: str, exit_code: int = 2) -> None:
    print(f"[contract:theory_overlay_inputs_v0] FAIL_CLOSED: {msg}", file=sys.stderr)
    raise SystemExit(exit_code)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"invalid JSON at {path}: {e}")


def _is_number(x: Any) -> bool:
    # JSON "number" -> python int/float. (bool is subclass of int, exclude it)
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _minimal_validate(obj: Any) -> None:
    if not isinstance(obj, dict):
        _die("root must be an object")

    # Required top-level keys
    req_top = ["schema", "schema_version", "source_kind", "provenance", "inputs", "inputs_digest"]
    for k in req_top:
        if k not in obj:
            _die(f"missing top-level key: {k}")

    if obj.get("schema") != "theory_overlay_inputs_v0":
        _die("schema must equal 'theory_overlay_inputs_v0'")
    if obj.get("schema_version") != 0:
        _die("schema_version must equal 0")

    if obj.get("source_kind") not in ("demo", "pipeline", "manual", "missing"):
        _die("source_kind must be one of: demo|pipeline|manual|missing")

    prov = obj.get("provenance")
    if not isinstance(prov, dict):
        _die("provenance must be an object")
    for k in ("generated_at_utc", "generator"):
        if k not in prov:
            _die(f"missing provenance.{k}")
        if not isinstance(prov.get(k), str):
            _die(f"provenance.{k} must be a string")

    # params: optional top-level
    if "params" in obj and obj["params"] is not None and not isinstance(obj["params"], dict):
        _die("params must be an object or null")

    inputs = obj.get("inputs")
    if not isinstance(inputs, dict):
        _die("inputs must be an object")

    # Required keys (may be null, but must exist)
    for k in ("u", "v_L", "lambda_eff"):
        if k not in inputs:
            _die(f"missing inputs.{k}")
        v = inputs.get(k)
        if v is not None and not _is_number(v):
            _die(f"inputs.{k} must be a number or null")

    # Forbid inputs.params (consumer reads top-level params)
    if "params" in inputs:
        _die("inputs.params is forbidden; use top-level params")

    # Require T OR lnT to be present and numeric (not null)
    T = inputs.get("T", None)
    lnT = inputs.get("lnT", None)

    ok_T = _is_number(T)
    ok_lnT = _is_number(lnT)

    if not (ok_T or ok_lnT):
        _die("inputs must provide T (number) or lnT (number)")

    # If present, allow T/lnT to be null per v0 shadow, but then the other must be number
    if "T" in inputs and T is not None and not _is_number(T):
        _die("inputs.T must be a number or null")
    if "lnT" in inputs and lnT is not None and not _is_number(lnT):
        _die("inputs.lnT must be a number or null")

    # units: optional object or null
    if "units" in inputs and inputs["units"] is not None and not isinstance(inputs["units"], dict):
        _die("inputs.units must be an object or null")

    dig = obj.get("inputs_digest")
    if not isinstance(dig, dict):
        _die("inputs_digest must be an object")

    if dig.get("algo") != "sha256":
        _die("inputs_digest.algo must equal 'sha256'")

    sha = dig.get("sha256")
    if not isinstance(sha, str) or not SHA256_RE.match(sha):
        _die("inputs_digest.sha256 must be a 64-char lowercase hex string")

    canon = dig.get("canonicalization")
    if not isinstance(canon, str):
        _die("inputs_digest.canonicalization must be a string")

    # raw_errors: optional list of strings
    if "raw_errors" in obj:
        re_list = obj["raw_errors"]
        if not isinstance(re_list, list) or any(not isinstance(x, str) for x in re_list):
            _die("raw_errors must be an array of strings")


def _schema_validate(obj: Any, schema_path: Path) -> None:
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError:
        # No dependency -> fallback
        _minimal_validate(obj)
        return

    schema = _read_json(schema_path)
    try:
        jsonschema.validate(instance=obj, schema=schema)
    except Exception as e:
        _die(f"schema validation failed: {e}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="path to theory_overlay_inputs_v0.json")
    ap.add_argument(
        "--schema",
        dest="schema_path",
        default=SCHEMA_DEFAULT_PATH,
        help=f"path to JSON Schema (default: {SCHEMA_DEFAULT_PATH})",
    )
    args = ap.parse_args(argv)

    in_path = Path(args.in_path)
    if not in_path.exists():
        _die(f"input file not found: {in_path}")

    schema_path = Path(args.schema_path)
    if not schema_path.exists():
        _die(f"schema file not found: {schema_path}")

    obj = _read_json(in_path)
    _schema_validate(obj, schema_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
