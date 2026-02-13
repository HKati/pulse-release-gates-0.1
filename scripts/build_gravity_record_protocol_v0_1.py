mkdir -p scripts

cat > scripts/build_gravity_record_protocol_v0_1.py <<'PY'
#!/usr/bin/env python3
"""
Build a gravity_record_protocol_v0_1 artifact from a loose/raw JSON input.

Goals:
- Deterministic output (sorted keys, allow_nan=False)
- Never crash on malformed raw input; record issues in raw_errors
- Emit a schema/contract-shaped artifact for fail-closed checking + rendering
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


CONTRACT_NAME = "gravity_record_protocol_v0_1"
SCHEMA_VERSION = 1

STATUS_ALLOWED = {"PASS", "FAIL", "MISSING"}
SOURCE_KIND_ALLOWED = {"demo", "measurement", "simulation", "pipeline", "manual", "missing"}

DEFAULT_SCHEMA_PATH = "schemas/gravity_record_protocol_v0_1.schema.json"


def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _is_number_no_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        try:
            return math.isfinite(float(x))
        except Exception:
            return False
    return False


def _load_top_level_schema_props(schema_path: str, errors: List[str]) -> Optional[Set[str]]:
    """
    Best-effort: read schema and return the set of top-level property keys.
    Used to avoid emitting extra top-level keys when additionalProperties=false.
    """
    try:
        sch = _read_json(schema_path)
    except Exception as e:
        errors.append(f"schema: cannot read {schema_path}: {type(e).__name__}: {e}")
        return None

    props = sch.get("properties")
    if isinstance(props, dict):
        return set(props.keys())

    errors.append(f"schema: {schema_path} has no top-level 'properties' object")
    return None


def _sanitize_source_kind(raw_obj: Any, override: Optional[str], errors: List[str]) -> str:
    sk = override
    if sk is None and isinstance(raw_obj, dict):
        sk = raw_obj.get("source_kind")

    if isinstance(sk, str) and sk in SOURCE_KIND_ALLOWED:
        return sk

    if sk is not None:
        errors.append(f"source_kind: invalid value {sk!r} -> fallback to 'missing'")
    return "missing"


def _sanitize_provenance(raw_obj: Any, gen_at_override: Optional[str], gen_override: Optional[str], errors: List[str]) -> Dict[str, Any]:
    prov_raw = raw_obj.get("provenance") if isinstance(raw_obj, dict) else None
    prov_obj = prov_raw if isinstance(prov_raw, dict) else {}

    generated_at_utc = gen_at_override or (prov_obj.get("generated_at_utc") if _is_nonempty_str(prov_obj.get("generated_at_utc")) else None) or _utc_now_iso()
    generator = gen_override or (prov_obj.get("generator") if _is_nonempty_str(prov_obj.get("generator")) else None) or "scripts/build_gravity_record_protocol_v0_1.py"

    # Keep provenance minimal and safe (avoid extra keys if schema is strict)
    return {
        "generated_at_utc": generated_at_utc,
        "generator": generator,
    }


def _extract_raw_cases(raw_obj: Any, errors: List[str]) -> List[Dict[str, Any]]:
    if isinstance(raw_obj, dict):
        if isinstance(raw_obj.get("cases"), list):
            out: List[Dict[str, Any]] = []
            for i, c in enumerate(raw_obj["cases"]):
                if isinstance(c, dict):
                    out.append(c)
                else:
                    errors.append(f"raw.cases[{i}]: expected object")
            return out

        # accept single-case payload
        if "stations" in raw_obj or "profiles" in raw_obj:
            return [raw_obj]

    errors.append("raw: missing cases (expected root.cases[] or a single-case root payload)")
    return []


def _sanitize_station(st: Any, idx: int, errors: List[str]) -> Dict[str, Any]:
    st_obj = st if isinstance(st, dict) else {}
    sid = st_obj.get("station_id")
    if not _is_nonempty_str(sid):
        sid = f"S{idx+1}"
        errors.append(f"stations[{idx}].station_id: missing/invalid -> generated '{sid}'")

    r_areal = st_obj.get("r_areal")
    if r_areal is not None and not _is_number_no_bool(r_areal):
        errors.append(f"stations[{idx}].r_areal: invalid number -> set to null")
        r_areal = None
    elif r_areal is not None:
        r_areal = float(r_areal)

    r_label = st_obj.get("r_label")
    if r_label is not None and not _is_nonempty_str(r_label):
        errors.append(f"stations[{idx}].r_label: invalid string -> set to null")
        r_label = None

    # IMPORTANT: keep station keys minimal (avoid schema mismatch)
    return {
        "station_id": str(sid).strip(),
        "r_areal": r_areal,
        "r_label": r_label.strip() if isinstance(r_label, str) else None,
    }


def _sanitize_point(pt: Any, kind: str, where: str, errors: List[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(pt, dict):
        errors.append(f"{where}: expected object")
        return None

    r = pt.get("r")
    if r is None or isinstance(r, bool):
        errors.append(f"{where}.r: invalid (missing/bool)")
        return None
    if isinstance(r, (int, float)):
        if not math.isfinite(float(r)):
            errors.append(f"{where}.r: numeric r must be finite")
            return None
        r_out: Any = float(r)
    elif isinstance(r, str) and r.strip():
        r_out = r.strip()
    else:
        errors.append(f"{where}.r: must be number|string")
        return None

    v = pt.get("value")
    if not _is_number_no_bool(v):
        errors.append(f"{where}.value: must be finite number (no bool)")
        return None
    v_out = float(v)

    if kind == "lambda" and v_out <= 0:
        errors.append(f"{where}.value: lambda must be > 0")
        return None
    if kind == "kappa" and (v_out < 0 or v_out > 1):
        errors.append(f"{where}.value: kappa must be within [0,1]")
        return None

    out: Dict[str, Any] = {"r": r_out, "value": v_out}

    u = pt.get("uncertainty")
    if u is not None:
        if not _is_number_no_bool(u) or float(u) < 0:
            errors.append(f"{where}.uncertainty: invalid -> dropped")
        else:
            out["uncertainty"] = float(u)

    n = pt.get("n")
    if n is not None:
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            errors.append(f"{where}.n: invalid -> dropped")
        else:
            out["n"] = n

    return out


def _sanitize_profile(raw_prof: Any, kind: str, where: str, errors: List[str]) -> Dict[str, Any]:
    prof = raw_prof if isinstance(raw_prof, dict) else {}
    if raw_prof is not None and not isinstance(raw_prof, dict):
        errors.append(f"{where}: expected object")

    raw_status = prof.get("status")
    status = raw_status if isinstance(raw_status, str) and raw_status in STATUS_ALLOWED else None

    raw_points = prof.get("points")
    points_out: List[Dict[str, Any]] = []
    if raw_points is not None:
        if not isinstance(raw_points, list):
            errors.append(f"{where}.points: expected array")
        else:
            for i, pt in enumerate(raw_points):
                clean = _sanitize_point(pt, kind, f"{where}.points[{i}]", errors)
                if clean is not None:
                    points_out.append(clean)

    # infer status if missing/invalid
    if status is None:
        status = "PASS" if len(points_out) > 0 else "MISSING"
    # enforce PASS -> non-empty points (otherwise degrade)
    if status == "PASS" and len(points_out) == 0:
        errors.append(f"{where}: status=PASS but no valid points remained -> set to MISSING")
        status = "MISSING"

    # IMPORTANT: keep profile keys minimal (avoid schema mismatch)
    return {
        "status": status,
        "points": points_out if status == "PASS" else None,
    }


def _compute_inputs_digest(payload: Any, errors: List[str]) -> Optional[Dict[str, Any]]:
    canonicalization = "json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)"
    try:
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        return {"algo": "sha256", "sha256": sha, "canonicalization": canonicalization}
    except Exception as e:
        errors.append(f"inputs_digest: cannot compute sha256: {type(e).__name__}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="Raw input JSON")
    ap.add_argument("--out", required=True, help="Output artifact JSON")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA_PATH, help="Schema path (used to avoid extra top-level keys)")
    ap.add_argument("--source-kind", default=None, help="Override source_kind")
    ap.add_argument("--generated-at-utc", default=None, help="Override provenance.generated_at_utc")
    ap.add_argument("--generator", default=None, help="Override provenance.generator")
    args = ap.parse_args()

    raw_errors: List[str] = []

    try:
        raw_obj = _read_json(args.raw)
    except Exception as e:
        raw_errors.append(f"raw: cannot read JSON: {type(e).__name__}: {e}")
        raw_obj = {}

    schema_props = _load_top_level_schema_props(args.schema, raw_errors)

    def want_top(k: str) -> bool:
        # If schema can't be read, emit only the safest minimal set later.
        return schema_props is not None and (k in schema_props)

    source_kind = _sanitize_source_kind(raw_obj, args.source_kind, raw_errors)
    provenance = _sanitize_provenance(raw_obj, args.generated_at_utc, args.generator, raw_errors)

    raw_cases = _extract_raw_cases(raw_obj, raw_errors)
    cases_out: List[Dict[str, Any]] = []

    for ci, rc in enumerate(raw_cases):
        where = f"cases[{ci}]"

        cid = rc.get("case_id") if isinstance(rc, dict) else None
        if not _is_nonempty_str(cid):
            cid = f"case_{ci+1}"
            raw_errors.append(f"{where}.case_id: missing/invalid -> generated '{cid}'")

        stations_raw = rc.get("stations") if isinstance(rc, dict) else None
        stations_out: List[Dict[str, Any]] = []
        if not isinstance(stations_raw, list):
            raw_errors.append(f"{where}.stations: expected array")
            stations_raw = []
        for si, st in enumerate(stations_raw):
            stations_out.append(_sanitize_station(st, si, raw_errors))

        profiles_raw = rc.get("profiles") if isinstance(rc, dict) else None
        profiles_obj = profiles_raw if isinstance(profiles_raw, dict) else {}
        if profiles_raw is not None and not isinstance(profiles_raw, dict):
            raw_errors.append(f"{where}.profiles: expected object")

        profiles_out: Dict[str, Any] = {
            "lambda": _sanitize_profile(profiles_obj.get("lambda"), "lambda", f"{where}.profiles.lambda", raw_errors),
            "kappa": _sanitize_profile(profiles_obj.get("kappa"), "kappa", f"{where}.profiles.kappa", raw_errors),
        }
        # optional s/g
        if "s" in profiles_obj:
            profiles_out["s"] = _sanitize_profile(profiles_obj.get("s"), "scalar", f"{where}.profiles.s", raw_errors)
        if "g" in profiles_obj:
            profiles_out["g"] = _sanitize_profile(profiles_obj.get("g"), "scalar", f"{where}.profiles.g", raw_errors)

        cases_out.append(
            {
                "case_id": str(cid).strip(),
                "stations": stations_out,
                "profiles": profiles_out,
            }
        )

    # Minimal output (safe even if schema_props is unknown)
    out: Dict[str, Any] = {
        "schema": CONTRACT_NAME,
        "schema_version": SCHEMA_VERSION,
        "source_kind": source_kind,
        "provenance": provenance,
        "cases": cases_out,
    }

    # Optional top-level fields, only if schema declares them
    if want_top("inputs_digest"):
        payload = {"source_kind": source_kind, "cases": cases_out}
        out["inputs_digest"] = _compute_inputs_digest(payload, raw_errors)

    if want_top("raw_errors"):
        out["raw_errors"] = raw_errors

    _write_json(args.out, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x scripts/build_gravity_record_protocol_v0_1.py
