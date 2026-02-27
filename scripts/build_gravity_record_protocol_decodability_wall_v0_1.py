#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_points(profile_obj: Any) -> Optional[List[Dict[str, Any]]]:
    if profile_obj is None:
        return None
    if isinstance(profile_obj, dict) and "points" in profile_obj:
        return profile_obj["points"]
    if isinstance(profile_obj, dict) and "status" in profile_obj and "points" in profile_obj:
        return profile_obj["points"]
    return None

def numeric_points(points: List[Dict[str, Any]]) -> Tuple[List[Tuple[float, float]], int]:
    """
    Returns sorted list of (r, value) for numeric r only, and count of rejected points.
    """
    ok: List[Tuple[float, float]] = []
    rejected = 0
    for p in points:
        r = p.get("r")
        v = p.get("value")
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            rejected += 1
            continue
        if isinstance(r, (int, float)) and math.isfinite(float(r)):
            ok.append((float(r), float(v)))
        else:
            rejected += 1
    ok.sort(key=lambda t: t[0])
    # de-dupe exact r by keeping last (deterministic after sort)
    dedup: List[Tuple[float, float]] = []
    last_r = None
    for r, v in ok:
        if last_r is not None and r == last_r:
            dedup[-1] = (r, v)
        else:
            dedup.append((r, v))
            last_r = r
    return dedup, rejected

def find_first_crossing(rs: List[float], diffs: List[float]) -> Tuple[int, int, int]:
    """
    Return (crossings, idx_ok, idx_fail) where idx_fail is first index with diff<0 and previous >=0.
    crossings counts how many sign changes into negative exist.
    If no crossing, idx_ok=idx_fail=-1.
    """
    crossings = 0
    idx_ok = -1
    idx_fail = -1
    for i in range(1, len(diffs)):
        if diffs[i-1] >= 0 and diffs[i] < 0:
            crossings += 1
            if idx_fail == -1:
                idx_ok = i - 1
                idx_fail = i
    return crossings, idx_ok, idx_fail

def linear_interp_r(rs: List[float], diffs: List[float], i_ok: int, i_fail: int) -> float:
    r0, d0 = rs[i_ok], diffs[i_ok]
    r1, d1 = rs[i_fail], diffs[i_fail]
    # d0 >= 0, d1 < 0 expected
    if r1 == r0:
        return r0
    # r = r0 + (r1-r0) * d0/(d0-d1)
    return r0 + (r1 - r0) * (d0 / (d0 - d1))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="gravity_record_protocol_inputs_v0_1.json")
    ap.add_argument("--out", dest="out_path", required=True, help="decodability_wall_v0_1.json")
    ap.add_argument("--alphabet-size", type=int, required=True, help="|Sigma| (>=2)")
    ap.add_argument("--log-base", choices=["log2", "ln"], default="log2")
    ap.add_argument("--h-req", type=float, default=None, help="Optional override h_req (if not derivable from lambda)")
    ap.add_argument("--method", choices=["linear_interp", "step"], default="linear_interp")
    ap.add_argument("--round-dp", type=int, default=6)
    args = ap.parse_args()

    errors: List[str] = []
    if args.alphabet_size < 2:
        errors.append("alphabet_size must be >= 2")

    try:
        inp = load_json(args.in_path)
    except Exception as e:
        errors.append(f"cannot read input json: {e}")
        inp = None

    out_obj: Dict[str, Any] = {
        "artifact_kind": "decodability_wall_v0_1",
        "version": "v0.1",
        "source_inputs": {
            "schema": "gravity_record_protocol_inputs_v0_1",
            "path": args.in_path,
        },
        "config": {
            "alphabet_size": args.alphabet_size,
            "log_base": args.log_base,
            "units": "bits_per_tick" if args.log_base == "log2" else "nats_per_tick",
            "method": args.method,
            "tie_break": "lowest_r",
        },
        "cases": [],
        "errors": []
    }

    # best-effort hash
    try:
        out_obj["source_inputs"]["sha256"] = sha256_file(args.in_path)
    except Exception:
        pass

    if inp is None or not isinstance(inp, dict):
        errors.append("input must be a JSON object")
    else:
        cases = inp.get("cases")
        if not isinstance(cases, list) or len(cases) < 1:
            errors.append("input.cases must be a non-empty array")
        else:
            log_sigma = math.log2(args.alphabet_size) if args.log_base == "log2" else math.log(args.alphabet_size)

            for c in cases:
                case_id = c.get("case_id", "")
                case_out: Dict[str, Any] = {
                    "case_id": case_id if isinstance(case_id, str) else "",
                    "wall_state": "insufficient_points",
                    "r_c": None,
                    "warnings": [],
                    "diagnostics": {"n_points": 0, "crossings": 0}
                }

                profiles = c.get("profiles", {}) if isinstance(c, dict) else {}
                kappa_prof = profiles.get("kappa") if isinstance(profiles, dict) else None
                lambda_prof = profiles.get("lambda") if isinstance(profiles, dict) else None

                kappa_points = get_points(kappa_prof)
                if not isinstance(kappa_points, list) or len(kappa_points) < 1:
                    case_out["wall_state"] = "missing_kappa"
                    out_obj["cases"].append(case_out)
                    continue

                kps, rejected = numeric_points(kappa_points)
                if rejected > 0:
                    case_out["warnings"].append(f"rejected_points={rejected} (non-numeric r or non-finite value)")

                if len(kps) < 2:
                    case_out["wall_state"] = "insufficient_points"
                    case_out["diagnostics"]["n_points"] = len(kps)
                    out_obj["cases"].append(case_out)
                    continue

                rs = [r for r, _ in kps]
                kappas = [v for _, v in kps]

                # derive h_req
                h_req: Optional[float] = args.h_req
                if h_req is None:
                    lp = get_points(lambda_prof)
                    if isinstance(lp, list) and len(lp) >= 1 and isinstance(lp[0], dict) and isinstance(lp[0].get("value"), (int, float)):
                        h_req = float(lp[0]["value"])
                        # if multiple lambda points exist, warn (we treat as constant for now)
                        if len(lp) > 1:
                            case_out["warnings"].append("lambda has multiple points; using first as constant h_req (v0.1)")
                    else:
                        case_out["wall_state"] = "missing_requirement"
                        out_obj["cases"].append(case_out)
                        continue

                if not math.isfinite(float(h_req)):
                    case_out["wall_state"] = "missing_requirement"
                    out_obj["cases"].append(case_out)
                    continue

                # compute diffs = C(r) - h_req
                diffs = []
                for kap in kappas:
                    C = kap * log_sigma
                    diffs.append(C - h_req)

                crossings, i_ok, i_fail = find_first_crossing(rs, diffs)
                case_out["diagnostics"]["n_points"] = len(rs)
                case_out["diagnostics"]["r_min"] = rs[0]
                case_out["diagnostics"]["r_max"] = rs[-1]
                case_out["diagnostics"]["crossings"] = crossings

                if crossings > 1:
                    case_out["wall_state"] = "non_monotone_warning"
                    case_out["warnings"].append("multiple crossings detected; choosing earliest crossing (lowest r)")

                # Determine state
                if diffs[0] < 0:
                    case_out["wall_state"] = "always_not_decodable"
                    out_obj["cases"].append(case_out)
                    continue

                if all(d >= 0 for d in diffs):
                    case_out["wall_state"] = "no_wall_in_range"
                    out_obj["cases"].append(case_out)
                    continue

                if i_fail == -1:
                    case_out["wall_state"] = "insufficient_points"
                    out_obj["cases"].append(case_out)
                    continue

                # crossing found
                if args.method == "step":
                    r_c = rs[i_fail]
                else:
                    r_c = linear_interp_r(rs, diffs, i_ok, i_fail)

                r_c = round(float(r_c), args.round_dp)
                case_out["wall_state"] = "wall_found"
                case_out["r_c"] = r_c
                case_out["bracket"] = {"r_ok": rs[i_ok], "r_fail": rs[i_fail]}

                out_obj["cases"].append(case_out)

    out_obj["errors"] = errors

    # write always (even if errors) to make debugging/diffing possible
    try:
        with open(args.out_path, "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"[builder-fail] cannot write output: {e}", file=sys.stderr)
        return 2

    # exit code: 0 if no errors, else 2
    if errors:
        for e in errors:
            print(f"[builder-error] {e}", file=sys.stderr)
        return 2

    print(f"[builder-ok] wrote {args.out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
