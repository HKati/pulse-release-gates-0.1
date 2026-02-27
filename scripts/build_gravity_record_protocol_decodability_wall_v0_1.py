#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_gravity_record_protocol_decodability_wall_v0_1.py

Builds a gravity_record_protocol_decodability_wall_v0_1 artifact from a
gravity_record_protocol_inputs_v0_1 bundle.

Fail-closed + always-write behavior:
- Always attempts to write the output JSON artifact to --out (even on errors).
- Records producer-facing issues under `raw_errors` (top-level + per-case).
- Exit code:
    0 -> output written and raw_errors is empty
    2 -> output written and raw_errors is non-empty

Decodability condition (v0.1):
Given matched numeric r-points for required profiles lambda and kappa:
    diff(r) = kappa(r) * log_base(alphabet_size) - lambda(r) - margin
A point is decodable iff diff(r) >= 0.

Wall estimate (best effort):
- always_decodable      : all diffs >= 0
- always_not_decodable  : all diffs < 0
- wall_estimate         : a single "up-crossing" from <0 to >=0 and no down-crossings
- non_monotone          : multiple crossings or any down-crossing present
- insufficient_data     : cannot compute diffs (missing/invalid points)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_ID = "gravity_record_protocol_decodability_wall_v0_1"
SCHEMA_VERSION = "0.1"


# -----------------------------
# Helpers
# -----------------------------

def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def is_number(x: Any) -> bool:
    # bool is a subclass of int -> explicitly reject
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_finite_number(x: Any) -> bool:
    return is_number(x) and math.isfinite(float(x))


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_best_effort(path: str) -> Tuple[Optional[Any], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"failed to read/parse JSON: {e}"


def write_json(path: str, obj: Any, pretty: bool = True) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            f.write("\n")


def sort_key_r(r: Any) -> Tuple[int, Any]:
    """
    Deterministic ordering: numeric r first, then strings.
    """
    if is_number(r):
        return (0, float(r))
    return (1, str(r))


def normalize_profile_obj(profile_obj: Any) -> Tuple[Optional[str], Optional[List[Any]], List[str]]:
    """
    Accepts either:
      - { "status": "PASS|FAIL|MISSING", "points": [...] }
      - { "points": [...] }   (interpreted as PASS)
    Returns: (status, points, errors)
    """
    errs: List[str] = []
    if profile_obj is None:
        errs.append("profile object is null")
        return None, None, errs
    if not isinstance(profile_obj, dict):
        errs.append("profile object must be a JSON object")
        return None, None, errs

    status = profile_obj.get("status")
    points = profile_obj.get("points")

    if status is None:
        status = "PASS"

    if status not in ("PASS", "FAIL", "MISSING"):
        errs.append(f"invalid profile.status: {status!r} (expected PASS|FAIL|MISSING)")
        # continue best effort

    if status == "MISSING":
        # points should be null (per inputs builder docs), but tolerate [] too.
        if points not in (None, []):
            errs.append("profile.status=MISSING but points is not null/empty")
        return status, None if points is None else points, errs

    # PASS/FAIL:
    if points is None:
        errs.append("profile.points is required (or use status=MISSING with points:null)")
        return status, None, errs
    if not isinstance(points, list):
        errs.append("profile.points must be an array")
        return status, None, errs
    if status == "PASS" and len(points) < 1:
        errs.append("profile.status=PASS requires non-empty points array")
    return status, points, errs


def extract_numeric_points(points: List[Any], label: str) -> Tuple[Dict[float, float], List[Dict[str, Any]], List[str]]:
    """
    Extract numeric r -> value mapping.
    Returns:
      - map_r_to_value
      - points_out (normalized points for debug/output)
      - errors
    """
    errs: List[str] = []
    out_points: List[Dict[str, Any]] = []
    m: Dict[float, float] = {}

    if not isinstance(points, list):
        errs.append(f"{label}.points is not an array")
        return m, out_points, errs

    for i, p in enumerate(points):
        if not isinstance(p, dict):
            errs.append(f"{label}.points[{i}] must be an object")
            continue

        r = p.get("r")
        v = p.get("value")

        rec: Dict[str, Any] = {
            "r": r,
            "value": v,
        }

        # Validate value
        if not is_finite_number(v):
            errs.append(f"{label}.points[{i}].value must be a finite number (bool rejected)")
            rec["valid"] = False
            out_points.append(rec)
            continue

        # Validate r
        if not is_number(r):
            # keep it in out_points for visibility, but can't use for wall math
            rec["valid"] = False
            rec["note"] = "non-numeric r ignored for wall math"
            out_points.append(rec)
            continue

        rf = float(r)
        if not math.isfinite(rf):
            errs.append(f"{label}.points[{i}].r must be finite")
            rec["valid"] = False
            out_points.append(rec)
            continue

        rec["r"] = rf
        rec["value"] = float(v)
        rec["valid"] = True
        out_points.append(rec)

        # Deduplicate deterministically: keep first, record error for duplicates
        if rf in m:
            errs.append(f"{label}.points has duplicate r={rf}; keeping first occurrence")
            continue
        m[rf] = float(v)

    # Sort out_points deterministically
    out_points.sort(key=lambda d: sort_key_r(d.get("r")))
    return m, out_points, errs


def compute_log_sigma(alphabet_size: Optional[int], log_base: str, errs: List[str]) -> Optional[float]:
    """
    Returns log_base(alphabet_size) in either log2 or natural log.
    Guards against invalid alphabet_size to prevent crashes.
    """
    if alphabet_size is None:
        errs.append("alphabet_size is required")
        return None
    if not isinstance(alphabet_size, int) or isinstance(alphabet_size, bool):
        errs.append("alphabet_size must be an integer")
        return None
    if alphabet_size < 2:
        errs.append("alphabet_size must be >= 2")
        return None

    try:
        if log_base == "log2":
            return float(math.log2(alphabet_size))
        # default natural log
        return float(math.log(alphabet_size))
    except Exception as e:
        errs.append(f"failed to compute log_sigma: {e}")
        return None


def estimate_crossing_linear(r0: float, d0: float, r1: float, d1: float, errs: List[str]) -> float:
    """
    Linear interpolation for d(r)=0 between (r0,d0) and (r1,d1).
    Assumes d0 < 0 and d1 >= 0.
    """
    if r1 == r0:
        errs.append("cannot interpolate: identical r values in bracket")
        return r0
    denom = (d1 - d0)
    if denom == 0:
        errs.append("cannot interpolate: d1 == d0 in bracket; using midpoint")
        return (r0 + r1) / 2.0
    t = (0.0 - d0) / denom
    # clamp just in case of numeric noise
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0
    return r0 + t * (r1 - r0)


# -----------------------------
# Core builder
# -----------------------------

def build_case(case_in: Dict[str, Any], log_sigma: float, margin: float) -> Dict[str, Any]:
    """
    Builds one case output record. Never throws; returns case_out with case_errors as needed.
    """
    case_errors: List[str] = []
    case_id = case_in.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        case_errors.append("case.case_id must be a non-empty string")
        case_id = str(case_id) if case_id is not None else ""

    profiles = case_in.get("profiles")
    if not isinstance(profiles, dict):
        case_errors.append("case.profiles must be an object")
        profiles = {}

    lam_obj = profiles.get("lambda")
    kap_obj = profiles.get("kappa")

    lam_status, lam_points_raw, lam_errs = normalize_profile_obj(lam_obj)
    kap_status, kap_points_raw, kap_errs = normalize_profile_obj(kap_obj)
    case_errors.extend([f"lambda: {e}" for e in lam_errs])
    case_errors.extend([f"kappa: {e}" for e in kap_errs])

    # Early stop if missing required profiles
    if lam_status == "MISSING" or kap_status == "MISSING":
        case_errors.append("required profiles include MISSING; cannot compute wall")
        return {
            "case_id": case_id,
            "wall_state": "insufficient_data",
            "wall_r_estimate": None,
            "wall_r_bracket": None,
            "crossings": [],
            "points": [],
            "case_errors": case_errors,
        }

    if lam_points_raw is None or kap_points_raw is None:
        case_errors.append("missing points for required profiles; cannot compute wall")
        return {
            "case_id": case_id,
            "wall_state": "insufficient_data",
            "wall_r_estimate": None,
            "wall_r_bracket": None,
            "crossings": [],
            "points": [],
            "case_errors": case_errors,
        }

    lam_map, lam_points_out, lam_pts_errs = extract_numeric_points(lam_points_raw, "lambda")
    kap_map, kap_points_out, kap_pts_errs = extract_numeric_points(kap_points_raw, "kappa")
    case_errors.extend(lam_pts_errs)
    case_errors.extend(kap_pts_errs)

    # Match common numeric r values
    common_rs = sorted(set(lam_map.keys()) & set(kap_map.keys()))
    if len(common_rs) < 1:
        case_errors.append("no matched numeric r points between lambda and kappa")
        return {
            "case_id": case_id,
            "wall_state": "insufficient_data",
            "wall_r_estimate": None,
            "wall_r_bracket": None,
            "crossings": [],
            "points": [],
            "case_errors": case_errors,
            "lambda_points": lam_points_out,
            "kappa_points": kap_points_out,
        }

    # Build diff series
    points: List[Dict[str, Any]] = []
    diffs: List[float] = []
    dec_flags: List[bool] = []
    for r in common_rs:
        lam = lam_map[r]
        kap = kap_map[r]

        # Core condition:
        # diff = kappa * log_sigma - lambda - margin
        diff = (kap * log_sigma) - lam - margin

        diffs.append(diff)
        dec = (diff >= 0.0)
        dec_flags.append(dec)

        points.append({
            "r": r,
            "lambda": lam,
            "kappa": kap,
            "diff": diff,
            "decodable": dec,
        })

    # Deterministic sort (already by common_rs asc)
    # Classify states
    if all(d >= 0.0 for d in diffs):
        return {
            "case_id": case_id,
            "wall_state": "always_decodable",
            "wall_r_estimate": None,
            "wall_r_bracket": None,
            "crossings": [],
            "points": points,
            "case_errors": case_errors,
            "lambda_points": lam_points_out,
            "kappa_points": kap_points_out,
        }

    # Codex P2 fix: only always_not_decodable if ALL points fail
    if all(d < 0.0 for d in diffs):
        return {
            "case_id": case_id,
            "wall_state": "always_not_decodable",
            "wall_r_estimate": None,
            "wall_r_bracket": None,
            "crossings": [],
            "points": points,
            "case_errors": case_errors,
            "lambda_points": lam_points_out,
            "kappa_points": kap_points_out,
        }

    # Find crossings
    crossings: List[Dict[str, Any]] = []
    for i in range(len(points) - 1):
        r0, d0 = points[i]["r"], points[i]["diff"]
        r1, d1 = points[i + 1]["r"], points[i + 1]["diff"]

        if d0 < 0.0 and d1 >= 0.0:
            # up-crossing
            crossings.append({
                "kind": "up",
                "i0": i,
                "r0": r0, "d0": d0,
                "r1": r1, "d1": d1,
            })
        elif d0 >= 0.0 and d1 < 0.0:
            # down-crossing
            crossings.append({
                "kind": "down",
                "i0": i,
                "r0": r0, "d0": d0,
                "r1": r1, "d1": d1,
            })

    # Decide if we can provide a clean wall estimate
    up = [c for c in crossings if c["kind"] == "up"]
    down = [c for c in crossings if c["kind"] == "down"]

    # "wall_estimate" only if:
    # - exactly one up-crossing
    # - no down-crossings
    # - and the series starts not decodable, ends decodable (best effort monotone)
    if len(up) == 1 and len(down) == 0 and (dec_flags[0] is False) and (dec_flags[-1] is True):
        c = up[0]
        r0, d0, r1, d1 = float(c["r0"]), float(c["d0"]), float(c["r1"]), float(c["d1"])
        r_star = estimate_crossing_linear(r0, d0, r1, d1, case_errors)
        return {
            "case_id": case_id,
            "wall_state": "wall_estimate",
            "wall_r_estimate": r_star,
            "wall_r_bracket": [r0, r1],
            "crossings": crossings,
            "points": points,
            "case_errors": case_errors,
            "lambda_points": lam_points_out,
            "kappa_points": kap_points_out,
        }

    # Otherwise: non-monotone / ambiguous crossing pattern
    case_errors.append("non-monotone or multi-crossing diff series; wall estimate not stable")
    return {
        "case_id": case_id,
        "wall_state": "non_monotone",
        "wall_r_estimate": None,
        "wall_r_bracket": None,
        "crossings": crossings,
        "points": points,
        "case_errors": case_errors,
        "lambda_points": lam_points_out,
        "kappa_points": kap_points_out,
    }


def build_artifact(
    in_path: str,
    out_path: str,
    debug_out: Optional[str],
    alphabet_size: Optional[int],
    log_base: str,
    margin: float,
    pretty: bool,
) -> int:
    raw_errors: List[str] = []
    debug: Dict[str, Any] = {}

    out_obj: Dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "source_inputs": {
            "path": in_path,
            "sha256": None,
        },
        "params": {
            "alphabet_size": alphabet_size,
            "log_base": log_base,
            "margin": margin,
        },
        "log_sigma": None,
        "cases": [],
        "raw_errors": raw_errors,
    }

    # Best-effort sha256 (Codex note)
    try:
        out_obj["source_inputs"]["sha256"] = sha256_file(in_path)
    except Exception:
        # no error: this is best-effort
        pass

    # Read input JSON (best effort)
    inp, err = read_json_best_effort(in_path)
    if err is not None:
        raw_errors.append(err)

    if inp is None:
        raw_errors.append("input is null; expected JSON object")
        # still write output below
        debug["input"] = None
    else:
        debug["input_type"] = type(inp).__name__

    if inp is not None and not isinstance(inp, dict):
        raw_errors.append("input must be a JSON object (top-level dict)")
        inp = None

    # Compute log_sigma with guard (Codex P1 fix)
    log_sigma = compute_log_sigma(alphabet_size, log_base, raw_errors)
    out_obj["log_sigma"] = log_sigma

    # If log_sigma is missing, we cannot compute wall safely
    if log_sigma is None:
        # Still write output artifact and optional debug artifact
        try:
            write_json(out_path, out_obj, pretty=pretty)
        except Exception as e:
            # If even writing out fails, that's a hard failure
            sys.stderr.write(f"FATAL: failed to write out artifact: {e}\n")
            return 2

        if debug_out:
            try:
                debug["note"] = "log_sigma missing -> wall not computed"
                debug["raw_errors"] = raw_errors
                write_json(debug_out, debug, pretty=pretty)
            except Exception:
                pass

        return 2

    # Extract cases
    cases = None
    if inp is not None:
        cases = inp.get("cases")

    if cases is None:
        raw_errors.append("input.cases is required")
        cases = []
    elif not isinstance(cases, list):
        raw_errors.append("input.cases must be an array")
        cases = []

    if isinstance(cases, list) and len(cases) < 1:
        raw_errors.append("input.cases must be a non-empty array")

    # Build each case deterministically (by case_id)
    case_dicts: List[Dict[str, Any]] = []
    for i, c in enumerate(cases if isinstance(cases, list) else []):
        if not isinstance(c, dict):
            raw_errors.append(f"cases[{i}] must be an object")
            continue
        case_dicts.append(c)

    def case_sort_key(c: Dict[str, Any]) -> Tuple[int, str]:
        cid = c.get("case_id")
        if isinstance(cid, str):
            return (0, cid)
        return (1, str(cid))

    case_dicts.sort(key=case_sort_key)

    out_cases: List[Dict[str, Any]] = []
    for c in case_dicts:
        try:
            out_cases.append(build_case(c, log_sigma=log_sigma, margin=margin))
        except Exception as e:
            # never crash a single case; record error
            cid = c.get("case_id")
            raw_errors.append(f"case build failed for case_id={cid!r}: {e}")
            out_cases.append({
                "case_id": cid if isinstance(cid, str) else str(cid),
                "wall_state": "insufficient_data",
                "wall_r_estimate": None,
                "wall_r_bracket": None,
                "crossings": [],
                "points": [],
                "case_errors": [f"exception: {e}"],
            })

    out_obj["cases"] = out_cases

    # Write output + optional debug
    try:
        write_json(out_path, out_obj, pretty=pretty)
    except Exception as e:
        sys.stderr.write(f"FATAL: failed to write out artifact: {e}\n")
        return 2

    if debug_out:
        try:
            debug["generated_at_utc"] = out_obj["generated_at_utc"]
            debug["source_inputs"] = out_obj["source_inputs"]
            debug["params"] = out_obj["params"]
            debug["log_sigma"] = out_obj["log_sigma"]
            debug["raw_errors"] = raw_errors
            debug["cases_count"] = len(out_cases)
            write_json(debug_out, debug, pretty=pretty)
        except Exception:
            # debug is best-effort
            pass

    return 0 if len(raw_errors) == 0 else 2


# -----------------------------
# CLI
# -----------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build gravity_record_protocol_decodability_wall_v0_1 artifact from protocol inputs bundle."
    )
    p.add_argument("--in", dest="in_path", required=True, help="Path to gravity_record_protocol_inputs_v0_1.json")
    p.add_argument("--out", dest="out_path", required=True, help="Output path for decodability wall artifact JSON")
    p.add_argument("--debug-out", dest="debug_out", default=None, help="Optional debug artifact JSON output path")

    p.add_argument("--alphabet-size", dest="alphabet_size", type=int, required=True,
                   help="Alphabet size (sigma). Must be >= 2.")
    p.add_argument("--log-base", dest="log_base", choices=["log2", "ln"], default="log2",
                   help="Log base for log_sigma = log(alphabet_size).")
    p.add_argument("--margin", dest="margin", type=float, default=0.0,
                   help="Optional margin subtracted from diff before decodability test.")
    p.add_argument("--compact", dest="pretty", action="store_false",
                   help="Write compact JSON (no indent). Default is pretty JSON.")

    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    # Ultra-safe wrapper: never leave without trying to write --out
    try:
        return build_artifact(
            in_path=args.in_path,
            out_path=args.out_path,
            debug_out=args.debug_out,
            alphabet_size=args.alphabet_size,
            log_base=args.log_base,
            margin=args.margin,
            pretty=args.pretty,
        )
    except Exception as e:
        # last-resort: attempt to write a minimal artifact
        raw_errors = [f"unhandled exception: {e}"]
        tb = traceback.format_exc()

        out_obj = {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": utc_now_iso(),
            "source_inputs": {
                "path": getattr(args, "in_path", None),
                "sha256": None,
            },
            "params": {
                "alphabet_size": getattr(args, "alphabet_size", None),
                "log_base": getattr(args, "log_base", None),
                "margin": getattr(args, "margin", None),
            },
            "log_sigma": None,
            "cases": [],
            "raw_errors": raw_errors,
            "traceback": tb,
        }

        try:
            write_json(getattr(args, "out_path", "decodability_wall_out.json"), out_obj, pretty=True)
        except Exception:
            # nothing more we can do
            sys.stderr.write(tb + "\n")
            return 2

        if getattr(args, "debug_out", None):
            try:
                write_json(args.debug_out, {"traceback": tb, "raw_errors": raw_errors}, pretty=True)
            except Exception:
                pass

        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
