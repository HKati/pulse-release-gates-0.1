#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import Any, Dict, List

HEX64 = re.compile(r"^[a-f0-9]{64}$")

ALLOWED_WALL_STATES = {
    "wall_found",
    "no_wall_in_range",
    "always_not_decodable",
    "insufficient_points",
    "unsupported_non_numeric_r",
    "missing_kappa",
    "missing_requirement",
    "non_monotone_warning",
}

def fail(msgs: List[str]) -> int:
    for m in msgs:
        print(f"[contract-fail] {m}", file=sys.stderr)
    return 2

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input decodability_wall_v0_1.json")
    args = ap.parse_args()

    try:
        with open(args.in_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        return fail([f"cannot read json: {e}"])

    errs: List[str] = []

    if not isinstance(obj, dict):
        return fail(["top-level must be an object"])

    if obj.get("artifact_kind") != "decodability_wall_v0_1":
        errs.append("artifact_kind must be 'decodability_wall_v0_1'")
    if obj.get("version") != "v0.1":
        errs.append("version must be 'v0.1'")

    # source_inputs optional
    si = obj.get("source_inputs")
    if si is not None:
        if not isinstance(si, dict):
            errs.append("source_inputs must be an object")
        else:
            if "schema" not in si or "path" not in si:
                errs.append("source_inputs must include schema and path")
            sha = si.get("sha256")
            if sha is not None and (not isinstance(sha, str) or not HEX64.match(sha)):
                errs.append("source_inputs.sha256 must be 64 lowercase hex chars")

    cases = obj.get("cases")
    if not isinstance(cases, list) or len(cases) < 1:
        errs.append("cases must be a non-empty array")
    else:
        for i, c in enumerate(cases):
            pfx = f"cases[{i}]"
            if not isinstance(c, dict):
                errs.append(f"{pfx} must be an object")
                continue
            cid = c.get("case_id")
            if not isinstance(cid, str) or not cid.strip():
                errs.append(f"{pfx}.case_id must be non-empty string")

            ws = c.get("wall_state")
            if ws not in ALLOWED_WALL_STATES:
                errs.append(f"{pfx}.wall_state invalid: {ws}")

            rc = c.get("r_c", None)
            if rc is not None and not isinstance(rc, (int, float)):
                errs.append(f"{pfx}.r_c must be number or null")

            # if wall_found -> r_c required and bracket strongly recommended
            if ws == "wall_found":
                if rc is None:
                    errs.append(f"{pfx}: wall_found requires r_c")
                br = c.get("bracket")
                if br is None:
                    errs.append(f"{pfx}: wall_found should include bracket (r_ok, r_fail)")
                else:
                    if not isinstance(br, dict) or "r_ok" not in br or "r_fail" not in br:
                        errs.append(f"{pfx}.bracket must contain r_ok and r_fail")

    # errors optional but if present must be array of strings
    earr = obj.get("errors")
    if earr is not None:
        if not isinstance(earr, list) or any(not isinstance(x, str) for x in earr):
            errs.append("errors must be an array of strings")

    if errs:
        return fail(errs)

    print("[contract-ok] decodability_wall_v0_1")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
