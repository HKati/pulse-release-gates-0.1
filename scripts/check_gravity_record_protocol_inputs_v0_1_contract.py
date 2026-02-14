#!/usr/bin/env python3
"""
Fail-closed contract check for gravity_record_protocol_inputs_v0_1 raw bundles.

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
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


CONTRACT_NAME = "gravity_record_protocol_inputs_v0_1"
DEFAULT_SCHEMA_PATH = "schemas/gravity_record_protocol_inputs_v0_1.schema.json"

STATUS_ALLOWED = {"PASS", "FAIL", "MISSING"}
SOURCE_KIND_ALLOWED = {"demo", "measurement", "simulation", "pipeline", "manual", "missing"}


def _fail_closed(msg: str) -> int:
    print(f"[contract:{CONTRACT_NAME}] FAIL_CLOSED: {msg}", file=sys.stderr)
    return 2


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _check_unknown_keys(obj: Dict[str, Any], allowed: set[str], path: str, errors: List[str]) -> None:
    extra = set(obj.keys()) - allowed
    if extra:
        errors.append(f"{path}: unknown keys not allowed: {sorted(extra)}")


def _check_status_object(p: Any, path: str, errors: List[str]) -> Optional[str]:
    if not isinstance(p, dict):
        errors.append(f"{path}: must be object")
        return None
    st = p.get("status")
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
    errors.append(f"{path}: r must be number or non-empty string")


def _check_point_common(pt: Any, path: str, errors: List[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(pt, dict):
        errors.append(f"{path}: point must be object")
        return None

    _check_unknown_keys(pt, {"r", "value", "uncertainty", "n"}, path, errors)

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

    return pt


def _check_lambda_point(pt: Any, path: str, errors: List[str]) -> None:
    d = _check_point_common(pt, path, errors)
    if d is not None and _is_number_no_bool(d.get("value")):
        if float(d["value"]) <= 0:
            errors.append(f"{path}.value: lambda value must be > 0")


def _check_kappa_point(pt: Any, path: str, errors: List[str]) -> None:
    d = _check_point_common(pt, path, errors)
    if d is not None and _is_number_no_bool(d.get("value")):
        v = float(d["value"])
        if v < 0 or v > 1:
            errors.append(f"{path}.value: kappa value must be in [0,1]")


def _check_scalar_point(pt: Any, path: str, errors: List[str]) -> None:
    _check_point_common(pt, path, errors)


def _check_points_array(points: Any, path: str, errors: List[str], kind: str) -> None:
    if not isinstance(points, list) or len(points) < 1:
        errors.append(f"{path}: points must be a non-empty array")
        return
    for i, pt in enumerate(points):
        ppath = f"{path}[{i}]"
        if kind == "lambda":
            _check_lambda_point(pt, ppath, errors)
        elif kind == "kappa":
            _check_kappa_point(pt, ppath, errors)
        else:
            _check_scalar_point(pt, ppath, errors)


def _check_profile(profile: Any, path: str, errors: List[str], kind: str) -> None:
    if not isinstance(profile, dict):
        errors.append(f"{path}: must be object")
        return

    # Accept either:
    #  - status-form: {status, points?}
    #  - points-only form: {points}
    has_status = "status" in profile
    has_points = "points" in profile

    if has_status:
        st = _check_status_object(profile, path, errors)
        pts = profile.get("points")
        if st == "PASS":
            if pts is None:
                errors.append(f"{path}.points: required when status=PASS")
            else:
                _check_points_array(pts, f"{path}.points", errors, kind)
        else:
            # FAIL/MISSING: points may be absent; if present must be array
            if pts is not None:
                if not isinstance(pts, list):
                    errors.append(f"{path}.points: must be array when present")
                elif len(pts) > 0:
                    _check_points_array(pts, f"{path}.points", errors, kind)
    else:
        # points-only form -> implied PASS
        if not has_points:
            errors.append(f"{path}: must provide either status or points")
            return
        _check_points_array(profile.get("points"), f"{path}.points", errors, kind)


def _check_station(st: Any, path: str, errors: List[str]) -> None:
    if not isinstance(st, dict):
        errors.append(f"{path}: station must be object")
        return
    _check_unknown_keys(st, {"station_id", "r_areal", "r_label"}, path, errors)

    sid = st.get("station_id")
    if not _is_nonempty_str(sid):
        errors.append(f"{path}.station_id: must be non-empty string")

    r_areal = st.get("r_areal")
    if r_areal is not None and not _is_number_no_bool(r_areal):
        errors.append(f"{path}.r_areal: must be finite number (or null)")

    r_label = st.get("r_label")
    if r_label is not None and not _is_nonempty_str(r_label):
        errors.append(f"{path}.r_label: must be non-empty string (or null)")


def _check_case(case: Any, idx: int, errors: List[str]) -> None:
    path = f"cases[{idx}]"
    if not isinstance(case, dict):
        errors.append(f"{path}: case must be object")
        return
    _check_unknown_keys(case, {"case_id", "description", "notes", "stations", "profiles"}, path, errors)

    cid = case.get("case_id")
    if not _is_nonempty_str(cid):
        errors.append(f"{path}.case_id: must be non-empty string")

    stations = case.get("stations")
    if not isinstance(stations, list):
        errors.append(f"{path}.stations: must be array")
    else:
        if len(stations) < 2:
            errors.append(f"{path}.stations: must contain at least 2 stations")
        for i, st in enumerate(stations):
            _check_station(st, f"{path}.stations[{i}]", errors)

    profs = case.get("profiles")
    if not isinstance(profs, dict):
        errors.append(f"{path}.profiles: must be object")
        return
    _check_unknown_keys(profs, {"lambda", "kappa", "s", "g"}, f"{path}.profiles", errors)

    if "lambda" not in profs:
        errors.append(f"{path}.profiles: missing required 'lambda'")
    else:
        _check_profile(profs.get("lambda"), f"{path}.profiles.lambda", errors, "lambda")

    if "kappa" not in profs:
        errors.append(f"{path}.profiles: missing required 'kappa'")
    else:
        _check_profile(profs.get("kappa"), f"{path}.profiles.kappa", errors, "kappa")

    for opt in ("s", "g"):
        if opt in profs and profs.get(opt) is not None:
            _check_profile(profs.get(opt), f"{path}.profiles.{opt}", errors, "scalar")


def _minimal_invariants(obj: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["root: must be object"]

    # Keep schema fields optional to avoid breaking legacy raw payloads.
    if "schema" in obj and obj.get("schema") != CONTRACT_NAME:
        errors.append(f"schema: expected '{CONTRACT_NAME}' when present")
    if "schema_version" in obj and obj.get("schema_version") != 1:
        errors.append("schema_version: expected 1 when present")

    _check_unknown_keys(obj, {"schema", "schema_version", "source_kind", "provenance", "cases", "raw_errors"}, "root", errors)

    sk = obj.get("source_kind")
    if not isinstance(sk, str) or sk not in SOURCE_KIND_ALLOWED:
        errors.append(f"source_kind: must be one of {sorted(SOURCE_KIND_ALLOWED)}")

    prov = obj.get("provenance")
    if prov is not None:
        if not isinstance(prov, dict):
            errors.append("provenance: must be object (or absent/null)")
        else:
            if not _is_nonempty_str(prov.get("generated_at_utc")):
                errors.append("provenance.generated_at_utc: required non-empty string")
            if not _is_nonempty_str(prov.get("generator")):
                errors.append("provenance.generator: required non-empty string")

    cases = obj.get("cases")
    if not isinstance(cases, list) or len(cases) < 1:
        errors.append("cases: must be non-empty array")
        return errors

    for i, c in enumerate(cases):
        _check_case(c, i, errors)

    return errors


def _schema_validate(obj: Any, schema_path: str) -> Optional[str]:
    try:
        schema = _read_json(schema_path)
    except Exception as e:
        return f"cannot read schema: {type(e).__name__}: {e}"

    try:
        import jsonschema  # type: ignore
    except Exception:
        # jsonschema not installed: minimal invariants still run
        return None

    try:
        jsonschema.validate(instance=obj, schema=schema)
        return None
    except Exception as e:
        return f"jsonschema validation failed: {type(e).__name__}: {e}"


def _dedup(errors: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for e in errors:
        if e not in seen:
            out.append(e)
            seen.add(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Raw input JSON to validate")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, help="Schema path")
    args = ap.parse_args()

    try:
        obj = _read_json(args.in_path)
    except Exception as e:
        return _fail_closed(f"cannot read JSON: {type(e).__name__}: {e}")

    schema_err = _schema_validate(obj, args.schema)
    inv_errs = _minimal_invariants(obj)

    if schema_err:
        inv_errs.insert(0, schema_err)

    inv_errs = _dedup(inv_errs)

    if inv_errs:
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
