#!/usr/bin/env python3
"""
Fail-closed contract checker for gravity_record_protocol_decodability_wall_v0_1 artefacts.

Policy:
- The JSON Schema is the source of truth for required/optional fields.
- The checker must NOT be stricter than the schema (avoid false negatives).
- We add only "JSON/Python strictness" checks that are consistent with the schema intent,
  e.g. rejecting bools where JSON expects a number, and rejecting non-finite floats.

Exit codes:
- 0: contract OK
- 2: contract FAIL (one or more errors)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None


DEFAULT_SCHEMA_REL = Path("schemas/gravity_record_protocol_decodability_wall_v0_1.schema.json")


def _repo_root() -> Path:
    # scripts/ is expected to be at repo root: <root>/scripts/<thisfile>
    return Path(__file__).resolve().parent.parent


def _load_json_strict(path: Path) -> Any:
    """
    Load JSON while rejecting non-standard numeric constants (NaN/Infinity).
    """
    raw = path.read_text(encoding="utf-8")

    def _reject_constants(x: str) -> Any:
        raise ValueError(f"Non-JSON numeric constant encountered: {x}")

    return json.loads(raw, parse_constant=_reject_constants)


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    obj = _load_json_strict(schema_path)
    if not isinstance(obj, dict):
        raise ValueError("Schema must be a JSON object")
    return obj


def _format_schema_error(err: Any) -> str:
    # jsonschema.ValidationError has .absolute_path and .message
    path_parts = []
    for p in list(getattr(err, "absolute_path", [])):
        if isinstance(p, int):
            path_parts.append(f"[{p}]")
        else:
            # dot-path; escape-ish minimal
            path_parts.append(f".{p}")
    path = "$" + "".join(path_parts)
    msg = getattr(err, "message", str(err))
    return f"{path}: {msg}"


def _is_finite_json_number(x: Any) -> bool:
    """
    JSON number in practice:
    - int or float
    - BUT NOT bool (Python quirk: bool is subclass of int)
    - finite (no inf/nan)
    """
    if isinstance(x, bool):
        return False
    if not isinstance(x, (int, float)):
        return False
    return math.isfinite(float(x))


def _extra_strictness_checks(doc: Any) -> List[str]:
    """
    Extra checks that should not contradict the schema.

    We only validate a small set of known numeric fields where Python bools
    can sneak in even if the producer thinks they are emitting "numbers".
    """
    errs: List[str] = []

    if not isinstance(doc, dict):
        # Schema validation will also report this, but keep message clear.
        errs.append("$: input must be a JSON object")
        return errs

    cases = doc.get("cases")
    if not isinstance(cases, list):
        return errs  # schema layer will report; don't duplicate too much

    for i, c in enumerate(cases):
        pfx = f"$.cases[{i}]"
        if not isinstance(c, dict):
            continue  # schema layer will report

        # r_c: if present, must be a JSON number (not bool), finite
        if "r_c" in c:
            rc = c.get("r_c")
            if rc is None:
                # If schema allows null, fine; if not, schema validation will fail.
                pass
            else:
                if not _is_finite_json_number(rc):
                    errs.append(f"{pfx}.r_c: must be a finite JSON number (bool is not allowed)")

        # bracket: OPTIONAL unless the schema says otherwise.
        # If present, enforce endpoint types (again: bool must not pass).
        if "bracket" in c:
            br = c.get("bracket")
            if br is None:
                # Allowed if schema allows null/omitted; schema handles the rest.
                pass
            else:
                if not isinstance(br, dict):
                    errs.append(f"{pfx}.bracket: must be an object if present")
                else:
                    # If endpoints exist, they must be finite numbers and not bool.
                    # If schema requires them, schema validation will already catch missing keys;
                    # we still provide a clearer message for type issues.
                    for k in ("r_ok", "r_fail"):
                        if k in br:
                            v = br.get(k)
                            if v is None:
                                # schema decides whether null is allowed
                                continue
                            if not _is_finite_json_number(v):
                                errs.append(
                                    f"{pfx}.bracket.{k}: must be a finite JSON number (bool is not allowed)"
                                )

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Contract checker for gravity_record_protocol_decodability_wall_v0_1 artefacts (fail-closed)."
    )
    ap.add_argument("--in", dest="in_path", required=True, help="Path to artefact JSON to validate")
    ap.add_argument(
        "--schema",
        dest="schema_path",
        default=None,
        help="Path to schema JSON. Default: schemas/gravity_record_protocol_decodability_wall_v0_1.schema.json",
    )
    args = ap.parse_args()

    in_path = Path(args.in_path)
    schema_path = Path(args.schema_path) if args.schema_path else (_repo_root() / DEFAULT_SCHEMA_REL)

    errors: List[str] = []

    # Load input
    try:
        doc = _load_json_strict(in_path)
    except Exception as e:
        errors.append(f"$: failed to read/parse JSON input: {e}")
        _emit(errors)
        return 2

    # Load schema
    schema: Optional[Dict[str, Any]] = None
    try:
        schema = _load_schema(schema_path)
    except Exception as e:
        errors.append(f"$: failed to read/parse schema: {schema_path}: {e}")
        _emit(errors)
        return 2

    # Schema validation (preferred)
    if jsonschema is None:
        errors.append("$: jsonschema dependency not available; cannot validate against schema")
    else:
        try:
            Validator = jsonschema.validators.validator_for(schema)
            Validator.check_schema(schema)
            v = Validator(schema)
            for err in sorted(v.iter_errors(doc), key=lambda e: list(getattr(e, "absolute_path", []))):
                errors.append(_format_schema_error(err))
        except Exception as e:
            errors.append(f"$: schema validation failed unexpectedly: {e}")

    # Extra strictness checks (should not contradict schema)
    errors.extend(_extra_strictness_checks(doc))

    if errors:
        _emit(errors)
        return 2

    print("OK")
    return 0


def _emit(errors: List[str]) -> None:
    # Stable, line-based output for CI
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
