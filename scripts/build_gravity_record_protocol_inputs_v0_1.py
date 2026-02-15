#!/usr/bin/env python3
"""
Build gravity_record_protocol_inputs_v0_1 bundle from a simple JSONL rawlog.

JSONL record types (one JSON object per line):
- {"type":"meta","source_kind":..., "provenance":{generated_at_utc,generator,...}}
- {"type":"station","case_id":..., "station_id":..., "r_areal":..., "r_label":...}
- {"type":"point","case_id":..., "profile":"lambda|kappa|s|g", "r":..., "value":..., "uncertainty":..., "n":...}

Output (bundle):
- schema = "gravity_record_protocol_inputs_v0_1"
- schema_version = 1
- source_kind
- provenance
- cases[] with stations[] and profiles{lambda,kappa,(s,g)} points-only encoding
- raw_errors[] (if any)

Exit codes:
- 0: wrote output, no raw_errors
- 2: wrote output, but raw_errors present OR fatal I/O
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


CONTRACT_NAME = "gravity_record_protocol_inputs_v0_1"
SCHEMA_VERSION = 1
PROFILE_ALLOWED = {"lambda", "kappa", "s", "g"}


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _is_int_no_bool(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_number_no_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        try:
            return math.isfinite(float(x))
        except Exception:
            return False
    return False


def _r_sort_key(r: Any) -> Tuple[int, Any]:
    # numeric r first, then string labels; stable deterministic ordering
    if _is_number_no_bool(r):
        return (0, float(r))
    return (1, str(r))


def _read_jsonl(path: Path, errors: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"rawlog: cannot read file: {type(e).__name__}: {e}")
        return out

    for idx, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            obj = json.loads(s)
        except Exception as e:
            errors.append(f"rawlog:L{idx}: invalid JSON: {type(e).__name__}: {e}")
            continue
        if not isinstance(obj, dict):
            errors.append(f"rawlog:L{idx}: record must be an object")
            continue
        out.append(obj)
    return out


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rawlog", required=True, help="Input JSONL rawlog path")
    ap.add_argument("--out", required=True, help="Output bundle JSON path")
    ap.add_argument("--source-kind", default=None, help="Override source_kind (optional)")
    args = ap.parse_args()

    rawlog_path = Path(args.rawlog)
    out_path = Path(args.out)

    raw_errors: List[str] = []
    records = _read_jsonl(rawlog_path, raw_errors)

    meta_source_kind: str | None = None
    provenance: Dict[str, Any] | None = None

    # case_id -> accumulators
    cases: Dict[str, Dict[str, Any]] = {}

    def get_case(case_id: str) -> Dict[str, Any]:
        if case_id not in cases:
            cases[case_id] = {
                "case_id": case_id,
                "_stations": {},  # station_id -> station dict
                "_profiles": {p: [] for p in PROFILE_ALLOWED},  # profile -> list[point]
            }
        return cases[case_id]

    for i, rec in enumerate(records, start=1):
        rtype = rec.get("type")
        if rtype == "meta":
            sk = rec.get("source_kind")
            if isinstance(sk, str) and sk:
                if meta_source_kind is None:
                    meta_source_kind = sk
                elif meta_source_kind != sk:
                    raw_errors.append(f"rawlog: meta source_kind mismatch: '{meta_source_kind}' vs '{sk}'")

            prov = rec.get("provenance")
            if isinstance(prov, dict):
                # keep first; mismatch -> error
                if provenance is None:
                    provenance = prov
                else:
                    raw_errors.append("rawlog: duplicate meta.provenance encountered; keeping first")
            continue

        if rtype == "station":
            case_id = rec.get("case_id")
            sid = rec.get("station_id")
            if not _is_nonempty_str(case_id):
                raw_errors.append("rawlog: station missing non-empty case_id")
                continue
            if not _is_nonempty_str(sid):
                raw_errors.append(f"rawlog: station missing non-empty station_id (case_id={case_id})")
                continue

            c = get_case(case_id.strip())
            sid_norm = sid.strip()
            if sid_norm in c["_stations"]:
                raw_errors.append(f"rawlog: duplicate station_id '{sid_norm}' in case_id={case_id}")
                continue

            st: Dict[str, Any] = {"station_id": sid_norm}

            r_areal = rec.get("r_areal")
            if r_areal is not None:
                if _is_number_no_bool(r_areal):
                    st["r_areal"] = float(r_areal)
                else:
                    raw_errors.append(f"rawlog: station r_areal must be finite number (case_id={case_id}, station_id={sid_norm})")
                    st["r_areal"] = None

            r_label = rec.get("r_label")
            if r_label is not None:
                if _is_nonempty_str(r_label):
                    st["r_label"] = r_label.strip()
                else:
                    raw_errors.append(f"rawlog: station r_label must be non-empty string (case_id={case_id}, station_id={sid_norm})")
                    st["r_label"] = None

            c["_stations"][sid_norm] = st
            continue

        if rtype == "point":
            case_id = rec.get("case_id")
            profile = rec.get("profile")
            if not _is_nonempty_str(case_id):
                raw_errors.append("rawlog: point missing non-empty case_id")
                continue
            if not _is_nonempty_str(profile) or profile.strip() not in PROFILE_ALLOWED:
                raw_errors.append(f"rawlog: point has invalid profile (case_id={case_id})")
                continue
            profile = profile.strip()

            r = rec.get("r")
            if not (_is_number_no_bool(r) or _is_nonempty_str(r)):
                raw_errors.append(f"rawlog: point r must be finite number or non-empty string (case_id={case_id}, profile={profile})")
                continue

            value = rec.get("value")
            if not _is_number_no_bool(value):
                raw_errors.append(f"rawlog: point value must be finite number (no bool) (case_id={case_id}, profile={profile})")
                continue

            v = float(value)
            if profile == "lambda" and v <= 0:
                raw_errors.append(f"rawlog: lambda value must be > 0 (case_id={case_id})")
                continue
            if profile == "kappa" and (v < 0 or v > 1):
                raw_errors.append(f"rawlog: kappa value must be in [0,1] (case_id={case_id})")
                continue

            pt: Dict[str, Any] = {"r": (float(r) if _is_number_no_bool(r) else str(r).strip()), "value": v}

            unc = rec.get("uncertainty")
            if unc is not None:
                if _is_number_no_bool(unc) and float(unc) >= 0:
                    pt["uncertainty"] = float(unc)
                else:
                    raw_errors.append(f"rawlog: uncertainty must be >=0 finite number (case_id={case_id}, profile={profile})")

            n = rec.get("n")
            if n is not None:
                if _is_int_no_bool(n) and int(n) >= 0:
                    pt["n"] = int(n)
                else:
                    raw_errors.append(f"rawlog: n must be >=0 int (case_id={case_id}, profile={profile})")

            c = get_case(case_id.strip())
            c["_profiles"][profile].append(pt)
            continue

        raw_errors.append(f"rawlog: unknown record type '{rtype}' (record #{i})")

    # Choose source_kind: CLI override > meta > fallback
    source_kind = args.source_kind or meta_source_kind or "missing"
    if source_kind not in {"demo", "measurement", "simulation", "pipeline", "manual", "missing"}:
        raw_errors.append(f"source_kind: invalid '{source_kind}', falling back to 'missing'")
        source_kind = "missing"

    # Provenance: use meta if valid, otherwise omit (or fallback deterministic)
    prov_out: Dict[str, Any] | None = None
    if isinstance(provenance, dict):
        ga = provenance.get("generated_at_utc")
        gg = provenance.get("generator")
        if _is_nonempty_str(ga) and _is_nonempty_str(gg):
            prov_out = dict(provenance)
        else:
            raw_errors.append("provenance: meta.provenance missing generated_at_utc/generator; omitting provenance block")

    # Build final cases list deterministically
    case_list: List[Dict[str, Any]] = []
    for case_id in sorted(cases.keys()):
        c = cases[case_id]
        stations_map: Dict[str, Any] = c["_stations"]
        prof_map: Dict[str, List[Dict[str, Any]]] = c["_profiles"]

        stations = [stations_map[k] for k in sorted(stations_map.keys())]

        profiles_out: Dict[str, Any] = {}
        for prof in ("lambda", "kappa", "s", "g"):
            pts = prof_map.get(prof) or []
            pts_sorted = sorted(pts, key=lambda p: _r_sort_key(p.get("r")))
            if pts_sorted:
                profiles_out[prof] = {"points": pts_sorted}

        case_list.append(
            {
                "case_id": c["case_id"],
                "stations": stations,
                "profiles": profiles_out,
            }
        )

    out_obj: Dict[str, Any] = {
        "schema": CONTRACT_NAME,
        "schema_version": SCHEMA_VERSION,
        "source_kind": source_kind,
        "cases": case_list,
    }
    if prov_out is not None:
        out_obj["provenance"] = prov_out
    if raw_errors:
        out_obj["raw_errors"] = raw_errors

    try:
        _write_json(out_path, out_obj)
    except Exception as e:
        print(f"[build:{CONTRACT_NAME}] FAIL_CLOSED: cannot write output: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if raw_errors:
        print(f"[build:{CONTRACT_NAME}] FAIL_CLOSED: {raw_errors[0]}", file=sys.stderr)
        return 2

    print(f"[build:{CONTRACT_NAME}] PASS: wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
