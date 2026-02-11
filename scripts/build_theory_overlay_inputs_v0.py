#!/usr/bin/env python3
import argparse, json, os, sys, hashlib, datetime, pathlib
from typing import Any, Dict, Tuple, Optional

REQ_KEYS = ["u", "T", "lnT", "v_L", "lambda_eff"]

def utc_now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def canonical_json(obj: Any) -> str:
    # Determinisztikus: sorted keys + no whitespace; NaN/Inf tiltva
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def to_number_or_none(x: Any, errors: list, path: str) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        # allow_nan=False majd elkapja a NaN/Inf-et a canonicalizationnél,
        # de itt is kezelhetjük külön, ha akarod.
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            errors.append(f"{path}: not parseable number: {x!r}")
            return None
    errors.append(f"{path}: invalid type: {type(x).__name__}")
    return None

def extract_inputs(raw: Any) -> Tuple[Dict[str, Any], list]:
    errors = []
    if isinstance(raw, dict) and isinstance(raw.get("inputs"), dict):
        src = raw["inputs"]
    elif isinstance(raw, dict):
        src = raw
    else:
        return ({k: None for k in REQ_KEYS}, ["raw: not an object"])

    out: Dict[str, Any] = {}
    out["u"] = to_number_or_none(src.get("u"), errors, "inputs.u")
    out["T"] = to_number_or_none(src.get("T"), errors, "inputs.T")
    out["lnT"] = to_number_or_none(src.get("lnT"), errors, "inputs.lnT")
    out["v_L"] = to_number_or_none(src.get("v_L"), errors, "inputs.v_L")
    out["lambda_eff"] = to_number_or_none(src.get("lambda_eff"), errors, "inputs.lambda_eff")

    # opcionális blokkok
    if "params" in src:
        out["params"] = src.get("params")
    if "units" in src:
        out["units"] = src.get("units")

    # Ha mind T és lnT hiányzik, azt inkább soft hibának jelöljük (shadowban majd FAIL_CLOSED)
    if out["T"] is None and out["lnT"] is None:
        errors.append("inputs: both T and lnT are missing/null")

    return out, errors

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
        "run_url": run_url
    }

def atomic_write(path: pathlib.Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="raw input json (fixture or pipeline output)")
    ap.add_argument("--out", required=True, help="output bundle json")
    ap.add_argument("--source-kind", default=None, choices=["demo","pipeline","manual","missing"])
    args = ap.parse_args()

    raw_path = pathlib.Path(args.raw)
    raw_obj = None
    raw_errors = []
    try:
        raw_obj = json.loads(raw_path.read_text(encoding="utf-8"))
    except Exception as e:
        raw_errors.append(f"raw_read: {e}")
        raw_obj = {}

    inputs, parse_errors = extract_inputs(raw_obj)
    raw_errors.extend(parse_errors)

    # source_kind logika: explicit flag > raw meta > missing/demo fallback
    source_kind = args.source_kind
    if source_kind is None and isinstance(raw_obj, dict):
        source_kind = raw_obj.get("source_kind")
    if source_kind is None:
        source_kind = "missing" if raw_errors else "demo"

    # Digest kizárólag az inputs blokkra (timestamp/provenance ne befolyásolja!)
    try:
        canon = canonical_json(inputs)
        digest = sha256_hex(canon)
        canon_note = "json.dumps(sort_keys=True,separators=(',',':'),allow_nan=False) over bundle.inputs"
    except Exception as e:
        # allow_nan=False itt fogja elkapni a NaN/Inf-et; v0-ban ne borítsunk, inkább nullázzunk és jelezzünk.
        raw_errors.append(f"digest_fail_closed: {e}")
        inputs = {k: None for k in REQ_KEYS}
        canon = canonical_json(inputs)
        digest = sha256_hex(canon)
        canon_note = "fail_closed_reset_inputs_then_canonicalize"

    bundle = {
        "schema": "theory_overlay_inputs_v0",
        "schema_version": 0,
        "source_kind": source_kind,
        "provenance": build_provenance(),
        "inputs": inputs,
        "inputs_digest": {
            "algo": "sha256",
            "sha256": digest,
            "canonicalization": canon_note
        }
    }
    if raw_errors:
        bundle["raw_errors"] = raw_errors

    out_path = pathlib.Path(args.out)
    atomic_write(out_path, json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[bundle-builder] FAIL_CLOSED: {e}", file=sys.stderr)
        sys.exit(2)
