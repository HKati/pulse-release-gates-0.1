#!/usr/bin/env python3
"""
Fail-closed contract check for gravity_record_protocol_v0_1 artifacts.

Design goals:
- Deterministic, fail-closed: malformed JSON or invariant violations -> non-zero exit.
- Environment-independent: even if jsonschema is available, we still run minimal invariants.
- CI-friendly: prints a single FAIL_CLOSED reason line suitable for GitHub Actions logs.

Exit codes:
- 0: PASS
- 2: FAIL_CLOSED (contract/invariant violation)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CONTRACT_NAME = "gravity_record_protocol_v0_1"
DEFAULT_SCHEMA_PATH = "schemas/gravity_record_protocol_v0_1.schema.json"

STATUS_ALLOWED = {"PASS", "FAIL", "MISSING"}
SOURCE_KIND_ALLOWED = {"demo", "measurement", "simulation", "pipeline", "manual", "missing"}


def _fail_closed(msg: str) -> int:
    print(f"[contract:{CONTRACT_NAME}] FAIL_CLOSED: {msg}", file=sys.stderr)
    return 2


def _read_json(path: str) -> Any:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


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


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _check_status(obj: Any, path: str, errors: List[str]) -> Optional[str]:
    if not isinstance(obj, dict):
        errors.append(f"{path}: must be object")
        return None
    st = obj.get("status")
    if not isinstance(st, str) or st not in STATUS_ALLOWED:
        errors.append(f"{path}.status: must be one of {sorted(STATUS_ALLOWED)}")
        return None
    return st


def _check_r_label(r: Any, path: str, errors: List[str]) -> None:
    if isinstance(r, bool):
        errors.append(f"{path}: r must not be bool")
        return
    if isinstance(r, (int, float)):
        if not math.isfinite(float(r)):
            errors.append(f"{path}: r numeric must be finite")
        return
    if isinstance(r, str):
        if r.strip() == "":
            errors.append(f"{path}: r string must be non-empty")
        return
    errors.append(f"{path}: r must be number or string")


def _check_point_common(pt: Any, path: str, errors: List[str]) -> None:
    if not isinstance(pt, dict):
        errors.append(f"{path}: point must be object")
        return

    if "r" not in pt:
        errors.append(f"{path}: missing r")
    else:
        _check_r_label(pt.get("r"), f"{path}.r", errors)

    if "value" not in pt:
        errors.append(f"{path}: missing value")
    else:
        v = pt.get("value")
        if not _is_number_no_bool(v):
            errors.append(f"{path}.value: must be finite number (no bool)")

    u = pt.get("uncertainty")
    if u is not None:
        if not _is_number_no_bool(u) or float(u) < 0:
            errors.append(f"{path}.uncertainty: must be >=0 finite number (or null)")

    n = pt.get("n")
    if n is not None:
        if not _is_int_no_bool(n) or n < 0:
            errors.append(f"{path}.n: must be >=0 integer (or null)")


def _check_lambda_point(pt: Any, path: str, errors: List[str]) -> None:
    _check_point_common(pt, path, errors)
    if isinstance(pt, dict) and _is_number_no_bool(pt.get("value")):
        if float(pt["value"]) <= 0:
            errors.append(f"{path}.value: lambda value must be > 0")


def _check_kappa_point(pt: Any, path: str, errors: List[str]) -> None:
    _check_point_common(pt, path, errors)
    if isinstance(pt, dict) and _is_number_no_bool(pt.get("value")):
        v = float(pt["value"])
        if v < 0 or v > 1:
            errors.append(f"{path}.value: kappa value must be in [0,1]")


def _check_scalar_point(pt: Any, path: str, errors: List[str]) -> None:
    _check_point_common(pt, path, errors)
    # scalar points allow any finite number value


def _check_profile_points(
    profile: Dict[str, Any],
    st: str,
    path: str,
    errors: List[str],
    point_kind: str,
) -> None:
    pts = profile.get("points")
    if st == "PASS":
        if not isinstance(pts, list) or len(pts) < 1:
            errors.append(f"{path}.points: required non-empty array when status=PASS")
            return
    if pts is None:
        return
    if not isinstance(pts, list):
        errors.append(f"{path}.points: must be array or null")
        return

    for i, pt in enumerate(pts):
        ppath = f"{path}.points[{i}]"
        if point_kind == "lambda":
            _check_lambda_point(pt, ppath, errors)
        elif point_kind == "kappa":
            _check_kappa_point(pt, ppath, errors)
        else:
            _check_scalar_point(pt, ppath, errors)


def _check_profiles(case: Dict[str, Any], path: str, errors: List[str]) -> None:
    profs = case.get("profiles")
    if not isinstance(profs, dict):
        errors.append(f"{path}.profiles: must be object")
        return

    # Required: lambda + kappa
    for key in ("lambda", "kappa"):
        if key not in profs:
            errors.append(f"{path}.profiles: missing required '{key}' profile")

    # Lambda
    lam = profs.get("lambda")
    if isinstance(lam, dict):
        st = _check_status(lam, f"{path}.profiles.lambda", errors)
        if st:
            _check_profile_points(lam, st, f"{path}.profiles.lambda", errors, "lambda")

    # Kappa
    kap = profs.get("kappa")
    if isinstance(kap, dict):
        st = _check_status(kap, f"{path}.profiles.kappa", errors)
        if st:
            _check_profile_points(kap, st, f"{path}.profiles.kappa", errors, "kappa")

    # Optional: s, g (scalar profiles)
    for opt in ("s", "g"):
        p = profs.get(opt)
        if p is None:
            continue
        if not isinstance(p, dict):
            errors.append(f"{path}.profiles.{opt}: must be object")
            continue
        st = _check_status(p, f"{path}.profiles.{opt}", errors)
        if st:
            _check_profile_points(p, st, f"{path}.profiles.{opt}", errors, "scalar")


def _check_stations(case: Dict[str, Any], path: str, errors: List[str]) -> None:
    stations = case.get("stations")
    if not isinstance(stations, list):
        errors.append(f"{path}.stations: must be array")
        return

    # Codex P1: require at least two stations for comparative protocols (A<->B).
    if len(stations) < 2:
        errors.append(f"{path}.stations: must contain at least 2 stations")
        return

    seen_ids: set[str] = set()
    for i, st in enumerate(stations):
        sp = f"{path}.stations[{i}]"
        if not isinstance(st, dict):
            errors.append(f"{sp}: station must be object")
            continue

        sid = st.get("station_id")
        if not _is_nonempty_str(sid):
            errors.append(f"{sp}.station_id: must be non-empty string")
            continue

        sid_norm = sid.strip()
        if sid_norm in seen_ids:
            errors.append(f"{sp}.station_id: duplicate station_id '{sid_norm}'")
        seen_ids.add(sid_norm)

        r_areal = st.get("r_areal")
        if r_areal is not None:
            if not _is_number_no_bool(r_areal):
                errors.append(f"{sp}.r_areal: must be finite number (or null)")

        r_label = st.get("r_label")
        if r_label is not None and not (isinstance(r_label, str) and r_label.strip() != ""):
            errors.append(f"{sp}.r_label: must be non-empty string (or null)")


def _check_case(case: Any, idx: int, errors: List[str]) -> None:
    path = f"cases[{idx}]"
    if not isinstance(case, dict):
        errors.append(f"{path}: case must be object")
        return

    cid = case.get("case_id")
    if not _is_nonempty_str(cid):
        errors.append(f"{path}.case_id: must be non-empty string")

    _check_stations(case, path, errors)
    _check_profiles(case, path, errors)

    # Optional derived block
    derived = case.get("derived")
    if derived is not None:
        if not isinstance(derived, dict):
            errors.append(f"{path}.derived: must be object (or null)")
        else:
            gvl = derived.get("g_vs_lambda")
            if gvl is not None:
                st = _check_status(gvl, f"{path}.derived.g_vs_lambda", errors)
                if st == "PASS":
                    en = gvl.get("error_norm")
                    if not _is_number_no_bool(en) or float(en) < 0:
                        errors.append(f"{path}.derived.g_vs_lambda.error_norm: must be >=0 finite number when status=PASS")

    # Optional wall classification
    wc = case.get("wall_classification")
    if wc is not None:
        if not isinstance(wc, dict):
            errors.append(f"{path}.wall_classification: must be object (or null)")
        else:
            for key in ("frequency_wall", "delay_wall", "record_wall"):
                if key in wc and wc[key] is not None:
                    if not isinstance(wc[key], str) or wc[key] not in STATUS_ALLOWED:
                        errors.append(f"{path}.wall_classification.{key}: must be one of {sorted(STATUS_ALLOWED)} (or absent/null)")


def _minimal_invariants(obj: Any) -> List[str]:
    errors: List[str] = []

    if not isinstance(obj, dict):
        return ["root: must be object"]

    if obj.get("schema") != CONTRACT_NAME:
        errors.append(f"schema: expected '{CONTRACT_NAME}'")

    if obj.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    sk = obj.get("source_kind")
    if not isinstance(sk, str) or sk not in SOURCE_KIND_ALLOWED:
        errors.append(f"source_kind: must be one of {sorted(SOURCE_KIND_ALLOWED)}")

    prov = obj.get("provenance")
    if not isinstance(prov, dict):
        errors.append("provenance: must be object")
    else:
        if not _is_nonempty_str(prov.get("generated_at_utc")):
            errors.append("provenance.generated_at_utc: required non-empty string")
        if not _is_nonempty_str(prov.get("generator")):
            errors.append("provenance.generator: required non-empty string")

    cases = obj.get("cases")
    if not isinstance(cases, list) or len(cases) < 1:
        errors.append("cases: must be non-empty array")
        return errors  # cannot continue safely

    for i, c in enumerate(cases):
        _check_case(c, i, errors)

    return errors


def _schema_validate(obj: Any, schema_path: str) -> Optional[str]:
    """
    Returns None if ok, otherwise a short error string.
    Note: minimal invariants must still run even if this passes.
    """
    try:
        schema = _read_json(schema_path)
    except Exception as e:
        return f"cannot read schema: {type(e).__name__}: {e}"

    try:
        import jsonschema  # type: ignore
    except Exception:
        # jsonschema not installed: caller will rely on minimal invariants
        return None

    try:
        jsonschema.validate(instance=obj, schema=schema)
        return None
    except Exception as e:
        return f"jsonschema validation failed: {type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input JSON artifact to validate")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, help="Schema path (default: schemas/gravity_record_protocol_v0_1.schema.json)")
    args = ap.parse_args()

    # Load artifact JSON
    try:
        obj = _read_json(args.in_path)
    except Exception as e:
        return _fail_closed(f"cannot read JSON: {type(e).__name__}: {e}")

    # Schema validation (if available) + ALWAYS run invariants (environment-independent)
    schema_err = _schema_validate(obj, args.schema)
    inv_errs = _minimal_invariants(obj)

    if schema_err:
        inv_errs.insert(0, schema_err)

    if inv_errs:
        # print first error as headline; keep the rest compact
        headline = inv_errs[0]
        if len(inv_errs) > 1:
            tail = "; ".join(inv_errs[1:6])
            if len(inv_errs) > 6:
                tail += f"; (+{len(inv_errs) - 6} more)"
            headline = f"{headline} | {tail}"
        return _fail_closed(headline)

    print(f"[contract:{CONTRACT_NAME}] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
