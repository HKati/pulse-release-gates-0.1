#!/usr/bin/env python3
"""
Build a theory_overlay_inputs_v0 bundle from a raw input JSON.

Key contract behaviors (v0):
- Emits a contract-shaped bundle:
  schema, schema_version, source_kind, provenance, inputs, inputs_digest (+ optional params, raw_errors)
- T-or-lnT semantics: raw may provide either; builder does not fabricate values
- params MUST be top-level; inputs.params is forbidden by contract
  - If raw.inputs.params exists, it is promoted to top-level params ONLY if root params
    was not explicitly provided
  - If raw.params is explicitly null, that is an explicit unset and MUST block promotion
    of raw.inputs.params (migration safety)
- source_kind is sanitized to demo|pipeline|manual|missing (fallback on invalid)
- Numeric parsing rejects booleans and non-finite numbers (no silent 0/1 coercion)
- inputs_digest is sha256 over canonicalized bundle.inputs only (deterministic)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REQ_KEYS = ["u", "T", "lnT", "v_L", "lambda_eff"]
ALLOWED_SOURCE_KIND = {"demo", "pipeline", "manual", "missing"}


def utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def canonical_json(obj: Any) -> str:
    # Deterministic: sorted keys + compact separators; disallow NaN/Inf at serialization time.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def to_number_or_none(x: Any, errors: List[str], path: str) -> Optional[float]:
    # Reject booleans explicitly (bool is a subclass of int in Python).
    if isinstance(x, bool):
        errors.append(f"{path}: invalid type bool")
        return None

    if x is None:
        return None

    if isinstance(x, (int, float)):
        val = float(x)
        if not math.isfinite(val):
            errors.append(f"{path}: non-finite number")
            return None
        return val

    if isinstance(x, str):
        s = x.strip()
        try:
            val = float(s)
        except Exception:
            errors.append(f"{path}: not parseable number: {x!r}")
            return None

        if not math.isfinite(val):
            errors.append(f"{path}: non-finite number from string: {x!r}")
            return None
        return val

    errors.append(f"{path}: invalid type: {type(x).__name__}")
    return None


def extract_inputs_and_params(
    raw: Any,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], bool, List[str]]:
    """
    Returns: (inputs_out, params_out, root_params_explicit, errors)

    root_params_explicit is True when raw.params was explicitly provided as:
      - null (explicit unset), or
      - dict (explicit params object)

    This flag is used to prevent legacy nested inputs.params from overriding an
    intentional explicit root null during migrations.
    """
    errors: List[str] = []
    inputs_out: Dict[str, Any] = {k: None for k in REQ_KEYS}
    params_out: Optional[Dict[str, Any]] = None
    root_params_explicit = False

    if not isinstance(raw, dict):
        return inputs_out, None, False, ["raw: not an object"]

    # Root params (preferred, contract source of truth)
    if "params" in raw:
        if raw["params"] is None:
            # Explicit unset (must block inputs.params promotion)
            root_params_explicit = True
            params_out = None
        elif isinstance(raw["params"], dict):
            root_params_explicit = True
            params_out = raw["params"]
        else:
            # Invalid root params: ignore and allow fallback to inputs.params if present
            errors.append("params: root params is not an object/null (ignored; may fallback to inputs.params)")
            root_params_explicit = False
            params_out = None

    # inputs source: raw.inputs if present, otherwise raw root
    src: Any = raw.get("inputs")
    if not isinstance(src, dict):
        src = raw

    # Legacy nested inputs.params: promote ONLY if root params was not explicitly set
    if isinstance(src, dict) and "params" in src:
        nested = src.get("params")
        if nested is None:
            pass
        elif not isinstance(nested, dict):
            errors.append("params: inputs.params is not an object/null (ignored)")
        else:
            if root_params_explicit:
                errors.append("params: inputs.params ignored (root params explicitly set)")
            elif params_out is None:
                params_out = nested
                errors.append("params: promoted inputs.params to top-level params")
            else:
                errors.append("params: inputs.params ignored (top-level params already present)")

    # Extract numeric inputs (never emit params under inputs)
    inputs_out["u"] = to_number_or_none(src.get("u"), errors, "inputs.u")
    inputs_out["T"] = to_number_or_none(src.get("T"), errors, "inputs.T")
    inputs_out["lnT"] = to_number_or_none(src.get("lnT"), errors, "inputs.lnT")
    inputs_out["v_L"] = to_number_or_none(src.get("v_L"), errors, "inputs.v_L")
    inputs_out["lambda_eff"] = to_number_or_none(src.get("lambda_eff"), errors, "inputs.lambda_eff")

    # Optional units (allowed under inputs)
    if isinstance(src, dict) and "units" in src:
        units = src.get("units")
        if units is None or isinstance(units, dict):
            inputs_out["units"] = units
        else:
            errors.append("inputs.units: invalid type (must be object/null)")

    # The contract requires T OR lnT to be numeric; we don't fabricate. Warn here for visibility.
    if inputs_out["T"] is None and inputs_out["lnT"] is None:
        errors.append("inputs: both T and lnT are missing/null (bundle will fail contract)")

    return inputs_out, params_out, root_params_explicit, errors


def build_provenance() -> Dict[str, Any]:
    git_sha = os.environ.get("GITHUB_SHA")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_url = None
    if os.environ.get("GITHUB_SERVER_URL") and os.environ.get("GITHUB_REPOSITORY") and run_id:
        run_url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}"

    return {
        "generated_at_utc": utc_now_iso(),
        "generator": "scripts/build_theory_overlay_inputs_v0.py",
        "git_sha": git_sha,
        "run_id": run_id,
        "run_url": run_url,
    }


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def normalize_source_kind(candidate: Any, errors: List[str]) -> Optional[str]:
    if candidate is None:
        return None
    if not isinstance(candidate, str):
        errors.append(f"source_kind_invalid: non-string value ignored: {candidate!r}")
        return None
    if candidate not in ALLOWED_SOURCE_KIND:
        errors.append(f"source_kind_invalid: {candidate!r} (ignored)")
        return None
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="raw input json (fixture or pipeline output)")
    ap.add_argument("--out", required=True, help="output bundle json")
    ap.add_argument("--source-kind", default=None, choices=sorted(ALLOWED_SOURCE_KIND))
    args = ap.parse_args()

    raw_path = Path(args.raw)
    raw_obj: Any = {}
    raw_errors: List[str] = []

    try:
        raw_obj = json.loads(raw_path.read_text(encoding="utf-8"))
    except Exception as e:
        raw_errors.append(f"raw_read: {e}")
        raw_obj = {}

    inputs, params, root_params_explicit, parse_errors = extract_inputs_and_params(raw_obj)
    raw_errors.extend(parse_errors)

    # source_kind: explicit flag > validated raw metadata > fallback
    source_kind = args.source_kind
    if source_kind is None and isinstance(raw_obj, dict):
        source_kind = normalize_source_kind(raw_obj.get("source_kind"), raw_errors)

    if source_kind is None:
        # Only mark as "missing" on severe read/shape failures; otherwise default to "demo".
        severe = any(e.startswith("raw_read:") or e.startswith("raw:") for e in raw_errors)
        source_kind = "missing" if severe else "demo"

    # Digest over inputs only (provenance/timestamps must not affect it).
    try:
        canon = canonical_json(inputs)
        digest = sha256_hex(canon)
        canon_note = "json.dumps(sort_keys=True,separators=(',',':'),allow_nan=False) over bundle.inputs"
    except Exception as e:
        # Fail-closed digest: reset inputs to deterministic nulls
        raw_errors.append(f"digest_fail_closed: {e}")
        inputs = {k: None for k in REQ_KEYS}
        canon = canonical_json(inputs)
        digest = sha256_hex(canon)
        canon_note = "fail_closed_reset_inputs_then_canonicalize"

    bundle: Dict[str, Any] = {
        "schema": "theory_overlay_inputs_v0",
        "schema_version": 0,
        "source_kind": source_kind,
        "provenance": build_provenance(),
        "inputs": inputs,
        "inputs_digest": {
            "algo": "sha256",
            "sha256": digest,
            "canonicalization": canon_note,
        },
    }

    # Emit top-level params:
    # - if root params was explicitly set (dict or null), preserve that intent (including null),
    # - else emit promoted nested params if present.
    if root_params_explicit or params is not None:
        bundle["params"] = params

    if raw_errors:
        bundle["raw_errors"] = raw_errors

    out_path = Path(args.out)
    atomic_write(out_path, json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[bundle-builder] FAIL_CLOSED: {e}", file=sys.stderr)
        sys.exit(2)
