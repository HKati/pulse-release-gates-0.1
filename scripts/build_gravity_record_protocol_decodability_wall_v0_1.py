#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_gravity_record_protocol_decodability_wall_v0_1.py

Build a decodability_wall_v0_1 artifact from a
gravity_record_protocol_inputs_v0_1 bundle.

Fail-closed + always-write behavior:
- Always attempts to write the output JSON artifact to --out (even on errors).
- Records producer-facing issues under top-level `errors`.
- Exit code:
    0 -> output written and errors is empty
    2 -> output written and errors is non-empty

Decodability condition (v0.1):
Given matched numeric r-points for required profiles lambda and kappa:
    diff(r) = kappa(r) * log_base(alphabet_size) - lambda(r) - margin
A point is decodable iff diff(r) >= 0.

Wall estimate (best effort):
- no_wall_in_range       : all diffs >= 0
- always_not_decodable   : all diffs < 0
- wall_found             : exactly one crossing
- non_monotone_warning   : multiple crossings; report lowest-r crossing
- missing_requirement    : required inputs missing / unusable
- insufficient_points    : not enough matched numeric points
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple


ARTIFACT_KIND = "decodability_wall_v0_1"
ARTIFACT_VERSION = "v0.1"
INPUT_SCHEMA = "gravity_record_protocol_inputs_v0_1"


# -----------------------------
# Helpers
# -----------------------------

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


def is_number(x: Any) -> bool:
    # bool is a subclass of int -> explicitly reject
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_finite_number(x: Any) -> bool:
    """
    JSON number in practice:
    - int or float
    - BUT NOT bool
    - finite

    Important:
    - do not force int -> float here, because very large valid JSON integers
      may raise OverflowError on float(x)
    """
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    if isinstance(x, float):
        return math.isfinite(x)
    return False


def to_finite_float(x: Any, label: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Convert a JSON number to finite float safely.

    Returns:
      (float_value, None) on success
      (None, error_message) on failure

    Notes:
    - bool is rejected
    - large ints that overflow float conversion are rejected with a structured error
    """
    if isinstance(x, bool):
        return None, f"{label} must be a finite number (bool rejected)"
    if isinstance(x, int):
        try:
            xf = float(x)
        except OverflowError:
            return None, f"{label} must be representable as a finite float"
        if not math.isfinite(xf):
            return None, f"{label} must be representable as a finite float"
        return xf, None
    if isinstance(x, float):
        if not math.isfinite(x):
            return None, f"{label} must be a finite number"
        return x, None
    return None, f"{label} must be a finite number (bool rejected)"


def sort_key_r(r: Any) -> Tuple[int, int, Any]:
    """
    Deterministic ordering without forcing numeric values through float().

    Order:
    1) ints
    2) finite floats
    3) other floats (nan/inf)
    4) strings / other JSON-ish values
    """
    if isinstance(r, bool):
        return (4, 0, "bool")
    if isinstance(r, int):
        return (0, 0, r)
    if isinstance(r, float):
        if math.isnan(r):
            return (2, 0, "nan")
        if math.isinf(r):
            return (2, 1, "+inf" if r > 0 else "-inf")
        return (1, 0, r)
    return (3, 0, str(r))


def normalize_profile_obj(profile_obj: Any) -> Tuple[Optional[str], Optional[List[Any]], List[str]]:
    """
    Accept either:
      - { "status": "PASS|FAIL|MISSING", "points": [...] }
      - { "points": [...] }   (interpreted as PASS)

    Returns:
      (status, points, errors)
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

    if status == "MISSING":
        if points not in (None, []):
            errs.append("profile.status=MISSING but points is not null/empty")
        return status, None if points is None else points, errs

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

        raw_r = p.get("r")
        raw_v = p.get("value")

        rec: Dict[str, Any] = {
            "r": raw_r,
            "value": raw_v,
        }

        value_f, value_err = to_finite_float(raw_v, f"{label}.points[{i}].value")
        if value_err is not None:
            errs.append(value_err)
            rec["valid"] = False
            out_points.append(rec)
            continue

        if not is_number(raw_r):
            rec["valid"] = False
            rec["note"] = "non-numeric r ignored for wall math"
            out_points.append(rec)
            continue

        r_f, r_err = to_finite_float(raw_r, f"{label}.points[{i}].r")
        if r_err is not None:
            errs.append(r_err)
            rec["valid"] = False
            out_points.append(rec)
            continue

        rec["r"] = r_f
        rec["value"] = value_f
        rec["valid"] = True
        out_points.append(rec)

        # Deduplicate deterministically: keep first, record error for duplicates
        if r_f in m:
            errs.append(f"{label}.points has duplicate r={r_f}; keeping first occurrence")
            continue
        m[r_f] = value_f

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
        return float(math.log(alphabet_size))
    except Exception as e:
        errs.append(f"failed to compute log_sigma: {e}")
        return None


def estimate_crossing_linear(r0: float, d0: float, r1: float, d1: float, errs: List[str]) -> float:
    """
    Linear interpolation for d(r)=0 between (r0,d0) and (r1,d1).
    """
    if r1 == r0:
        errs.append("cannot interpolate: identical r values in bracket")
        return r0

    denom = d1 - d0
    if denom == 0:
        errs.append("cannot interpolate: d1 == d0 in bracket; using midpoint")
        return (r0 + r1) / 2.0

    t = (0.0 - d0) / denom
    t = max(0.0, min(1.0, t))
    return r0 + t * (r1 - r0)


# -----------------------------
# Core builder
# -----------------------------

def build_case(case_in: Dict[str, Any], log_sigma: float, margin: float) -> Dict[str, Any]:
    """
    Build one schema-aligned case output record. Never throws.
    """
    case_errors: List[str] = []
    warnings: List[str] = []

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

    if lam_status == "MISSING" or kap_status == "MISSING":
        case_errors.append("required profiles include MISSING; cannot compute wall")
        state = "missing_kappa" if kap_status == "MISSING" else "missing_requirement"
        return {
            "case_id": case_id,
            "wall_state": state,
            "r_c": None,
            "diagnostics": {"n_points": 0, "crossings": 0},
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    if lam_points_raw is None or kap_points_raw is None:
        case_errors.append("missing points for required profiles; cannot compute wall")
        return {
            "case_id": case_id,
            "wall_state": "missing_requirement",
            "r_c": None,
            "diagnostics": {"n_points": 0, "crossings": 0},
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    lam_map, _, lam_pts_errs = extract_numeric_points(lam_points_raw, "lambda")
    kap_map, _, kap_pts_errs = extract_numeric_points(kap_points_raw, "kappa")
    case_errors.extend(lam_pts_errs)
    case_errors.extend(kap_pts_errs)

    if any(not is_number(p.get("r")) for p in (lam_points_raw + kap_points_raw) if isinstance(p, dict)):
        warnings.append("non-numeric r values were ignored for wall math")

    common_rs = sorted(set(lam_map.keys()) & set(kap_map.keys()))
    if len(common_rs) < 1:
        case_errors.append("no matched numeric r points between lambda and kappa")
        return {
            "case_id": case_id,
            "wall_state": "unsupported_non_numeric_r",
            "r_c": None,
            "diagnostics": {"n_points": 0, "crossings": 0},
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    if len(common_rs) < 2:
        return {
            "case_id": case_id,
            "wall_state": "insufficient_points",
            "r_c": None,
            "diagnostics": {
                "r_min": min(common_rs),
                "r_max": max(common_rs),
                "n_points": len(common_rs),
                "crossings": 0,
            },
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    points: List[Dict[str, Any]] = []
    diffs: List[float] = []

    for r in common_rs:
        lam = lam_map[r]
        kap = kap_map[r]
        diff = (kap * log_sigma) - lam - margin
        diffs.append(diff)
        points.append({
            "r": r,
            "lambda": lam,
            "kappa": kap,
            "diff": diff,
            "decodable": diff >= 0.0,
        })

    diagnostics: Dict[str, Any] = {
        "r_min": min(common_rs),
        "r_max": max(common_rs),
        "n_points": len(common_rs),
    }

    if all(d >= 0.0 for d in diffs):
        diagnostics["crossings"] = 0
        return {
            "case_id": case_id,
            "wall_state": "no_wall_in_range",
            "r_c": None,
            "diagnostics": diagnostics,
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    if all(d < 0.0 for d in diffs):
        diagnostics["crossings"] = 0
        return {
            "case_id": case_id,
            "wall_state": "always_not_decodable",
            "r_c": None,
            "diagnostics": diagnostics,
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    crossings: List[Dict[str, Any]] = []
    for i in range(len(points) - 1):
        r0, d0 = points[i]["r"], points[i]["diff"]
        r1, d1 = points[i + 1]["r"], points[i + 1]["diff"]

        if d0 < 0.0 and d1 >= 0.0:
            crossings.append({
                "kind": "up",
                "i0": i,
                "r0": r0, "d0": d0,
                "r1": r1, "d1": d1,
            })
        elif d0 >= 0.0 and d1 < 0.0:
            crossings.append({
                "kind": "down",
                "i0": i,
                "r0": r0, "d0": d0,
                "r1": r1, "d1": d1,
            })

    diagnostics["crossings"] = len(crossings)

    if len(crossings) == 1:
        c = crossings[0]
        r0, d0, r1, d1 = float(c["r0"]), float(c["d0"]), float(c["r1"]), float(c["d1"])
        r_star = estimate_crossing_linear(r0, d0, r1, d1, case_errors)
        r_ok, r_fail = (r1, r0) if d1 >= 0.0 else (r0, r1)
        return {
            "case_id": case_id,
            "wall_state": "wall_found",
            "r_c": r_star,
            "bracket": {"r_ok": r_ok, "r_fail": r_fail},
            "diagnostics": diagnostics,
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    if len(crossings) > 1:
        c = crossings[0]
        r0, d0, r1, d1 = float(c["r0"]), float(c["d0"]), float(c["r1"]), float(c["d1"])
        r_star = estimate_crossing_linear(r0, d0, r1, d1, case_errors)
        r_ok, r_fail = (r1, r0) if d1 >= 0.0 else (r0, r1)
        warnings.append("multiple wall crossings observed; reporting lowest-r crossing")
        return {
            "case_id": case_id,
            "wall_state": "non_monotone_warning",
            "r_c": r_star,
            "bracket": {"r_ok": r_ok, "r_fail": r_fail},
            "diagnostics": diagnostics,
            "warnings": warnings,
            "_case_errors": case_errors,
        }

    return {
        "case_id": case_id,
        "wall_state": "no_wall_in_range",
        "r_c": None,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "_case_errors": case_errors,
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
    errors: List[str] = []
    debug: Dict[str, Any] = {}

    out_obj: Dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "version": ARTIFACT_VERSION,
        "source_inputs": {
            "schema": INPUT_SCHEMA,
            "path": in_path,
            "sha256": None,
        },
        "config": {
            "alphabet_size": alphabet_size,
            "log_base": log_base,
            "units": "bits_per_tick" if log_base == "log2" else "nats_per_tick",
            "method": "linear_interp",
            "tie_break": "lowest_r",
        },
        "cases": [],
        "errors": errors,
    }

    try:
        out_obj["source_inputs"]["sha256"] = sha256_file(in_path)
    except Exception:
        pass

    inp, err = read_json_best_effort(in_path)
    if err is not None:
        errors.append(err)

    if inp is None:
        errors.append("input is null; expected JSON object")
        debug["input"] = None
    else:
        debug["input_type"] = type(inp).__name__

    if inp is not None and not isinstance(inp, dict):
        errors.append("input must be a JSON object (top-level dict)")
        inp = None

    log_sigma = compute_log_sigma(alphabet_size, log_base, errors)

    if log_sigma is None:
        try:
            write_json(out_path, out_obj, pretty=pretty)
        except Exception as e:
            sys.stderr.write(f"FATAL: failed to write out artifact: {e}\n")
            return 2

        if debug_out:
            try:
                debug["note"] = "log_sigma missing -> wall not computed"
                debug["errors"] = errors
                write_json(debug_out, debug, pretty=pretty)
            except Exception:
                pass

        return 2

    cases = None
    if inp is not None:
        cases = inp.get("cases")

    if cases is None:
        errors.append("input.cases is required")
        cases = []
    elif not isinstance(cases, list):
        errors.append("input.cases must be an array")
        cases = []

    if isinstance(cases, list) and len(cases) < 1:
        errors.append("input.cases must be a non-empty array")

    case_dicts: List[Dict[str, Any]] = []
    for i, c in enumerate(cases if isinstance(cases, list) else []):
        if not isinstance(c, dict):
            errors.append(f"cases[{i}] must be an object")
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
            built_case = build_case(c, log_sigma=log_sigma, margin=margin)
            case_errors = built_case.pop("_case_errors", [])
            for ce in case_errors:
                cid = built_case.get("case_id", "")
                errors.append(f"case[{cid}]: {ce}")
            out_cases.append(built_case)
        except Exception as e:
            cid = c.get("case_id")
            errors.append(f"case build failed for case_id={cid!r}: {e}")
            out_cases.append({
                "case_id": cid if isinstance(cid, str) else str(cid),
                "wall_state": "missing_requirement",
                "r_c": None,
                "diagnostics": {"n_points": 0, "crossings": 0},
                "warnings": ["internal builder exception"],
            })

    out_obj["cases"] = out_cases

    try:
        write_json(out_path, out_obj, pretty=pretty)
    except Exception as e:
        sys.stderr.write(f"FATAL: failed to write out artifact: {e}\n")
        return 2

    if debug_out:
        try:
            debug["source_inputs"] = out_obj["source_inputs"]
            debug["config"] = out_obj["config"]
            debug["errors"] = errors
            debug["cases_count"] = len(out_cases)
            write_json(debug_out, debug, pretty=pretty)
        except Exception:
            pass

    return 0 if len(errors) == 0 else 2


# -----------------------------
# CLI
# -----------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build decodability_wall_v0_1 artifact from gravity record protocol inputs bundle."
    )
    p.add_argument("--in", dest="in_path", required=True, help="Path to gravity_record_protocol_inputs_v0_1.json")
    p.add_argument("--out", dest="out_path", required=True, help="Output path for decodability wall artifact JSON")
    p.add_argument("--debug-out", dest="debug_out", default=None, help="Optional debug artifact JSON output path")

    p.add_argument(
        "--alphabet-size",
        dest="alphabet_size",
        type=int,
        required=True,
        help="Alphabet size (sigma). Must be >= 2.",
    )
    p.add_argument(
        "--log-base",
        dest="log_base",
        choices=["log2", "ln"],
        default="log2",
        help="Log base for log_sigma = log(alphabet_size).",
    )
    p.add_argument(
        "--margin",
        dest="margin",
        type=float,
        default=0.0,
        help="Optional margin subtracted from diff before decodability test.",
    )
    p.add_argument(
        "--compact",
        dest="pretty",
        action="store_false",
        help="Write compact JSON (no indent). Default is pretty JSON.",
    )

    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

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
        errors = [f"unhandled exception: {e}"]
        tb = traceback.format_exc()

        out_obj = {
            "artifact_kind": ARTIFACT_KIND,
            "version": ARTIFACT_VERSION,
            "source_inputs": {
                "schema": INPUT_SCHEMA,
                "path": getattr(args, "in_path", None),
                "sha256": None,
            },
            "config": {
                "alphabet_size": getattr(args, "alphabet_size", None),
                "log_base": getattr(args, "log_base", None),
                "units": "bits_per_tick" if getattr(args, "log_base", None) == "log2" else "nats_per_tick",
                "method": "linear_interp",
                "tie_break": "lowest_r",
            },
            "cases": [],
            "errors": errors + [tb],
        }

        try:
            write_json(getattr(args, "out_path", "decodability_wall_out.json"), out_obj, pretty=True)
        except Exception:
            sys.stderr.write(tb + "\n")
            return 2

        if getattr(args, "debug_out", None):
            try:
                write_json(args.debug_out, {"traceback": tb, "errors": errors}, pretty=True)
            except Exception:
                pass

        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
