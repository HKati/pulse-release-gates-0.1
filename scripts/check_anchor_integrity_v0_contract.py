#!/usr/bin/env python3
"""
check_anchor_integrity_v0_contract.py

Fail-closed contract check for anchor_integrity_v0 overlay output.

Goals:
- Enforce required keys (missing != null).
- Enforce allowed enums and type ranges.
- Enforce "additionalProperties: false" semantics (no unexpected keys).

This script is intended to be used in CI for diagnostic overlays:
- If the overlay JSON is present, it must conform to the schema contract.
- If the overlay JSON is missing, the caller/workflow decides how to behave.

Usage:
  python scripts/check_anchor_integrity_v0_contract.py --in path/to/anchor_integrity_v0.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ALLOWED_STATE = {"ANCHORED", "PARTIAL", "ANCHOR_LOST", "UNKNOWN"}
ALLOWED_RESPONSE_MODE = {"ANSWER", "BOUNDARY", "ASK_FOR_ANCHOR", "SILENCE"}
ALLOWED_GATE_ACTION = {"OPEN", "SLOW", "CLOSED"}
ALLOWED_RISK = {"low", "medium", "high"}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {e}") from e


def _is_str_nonempty(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _is_str_or_null(x: Any) -> bool:
    return x is None or isinstance(x, str)


def _is_bool_or_null(x: Any) -> bool:
    return x is None or isinstance(x, bool)


def _is_int_or_null_nonneg(x: Any) -> bool:
    return x is None or (isinstance(x, int) and x >= 0)


def _is_float01_or_null(x: Any) -> bool:
    if x is None:
        return True
    if isinstance(x, bool):
        # bool is a subclass of int in Python; reject explicitly
        return False
    if not isinstance(x, (int, float)):
        return False
    return 0.0 <= float(x) <= 1.0


def _path_join(parts: Sequence[Any]) -> str:
    # Render a stable path string for error messages
    out: List[str] = []
    for p in parts:
        if isinstance(p, int):
            out.append(f"[{p}]")
        else:
            out.append(str(p))
    return ".".join(out).replace(".[", "[")


def _require(cond: bool, msg: str, errors: List[str]) -> None:
    if not cond:
        errors.append(msg)


def _require_keys(obj: Any, required: Sequence[str], where: Sequence[Any], errors: List[str]) -> None:
    if not isinstance(obj, dict):
        _require(False, f"{_path_join(where)} must be an object", errors)
        return
    for k in required:
        _require(k in obj, f"{_path_join(where)} missing required key: {k}", errors)


def _require_no_extra_keys(obj: Any, allowed: Iterable[str], where: Sequence[Any], errors: List[str]) -> None:
    if not isinstance(obj, dict):
        return
    allowed_set = set(allowed)
    extra = sorted([k for k in obj.keys() if k not in allowed_set])
    if extra:
        _require(False, f"{_path_join(where)} has unexpected keys: {extra}", errors)


def _check_meta(meta: Any, where: Sequence[Any], errors: List[str]) -> None:
    req = ["run_id", "commit", "generator", "source_date_epoch"]
    _require_keys(meta, req, where, errors)
    _require_no_extra_keys(meta, req, where, errors)
    if not isinstance(meta, dict):
        return

    _require(_is_str_or_null(meta.get("run_id")), f"{_path_join(where)}.run_id must be string|null", errors)
    _require(_is_str_or_null(meta.get("commit")), f"{_path_join(where)}.commit must be string|null", errors)
    _require(_is_str_nonempty(meta.get("generator")), f"{_path_join(where)}.generator must be non-empty string", errors)
    _require(_is_int_or_null_nonneg(meta.get("source_date_epoch")), f"{_path_join(where)}.source_date_epoch must be integer>=0|null", errors)


def _check_inputs(inputs: Any, where: Sequence[Any], errors: List[str]) -> None:
    req = ["status_path", "paradox_source_path", "scanned_paths"]
    _require_keys(inputs, req, where, errors)
    _require_no_extra_keys(inputs, req, where, errors)
    if not isinstance(inputs, dict):
        return

    _require(_is_str_nonempty(inputs.get("status_path")), f"{_path_join(where)}.status_path must be non-empty string", errors)
    _require(_is_str_or_null(inputs.get("paradox_source_path")), f"{_path_join(where)}.paradox_source_path must be string|null", errors)

    sp = inputs.get("scanned_paths")
    _require(isinstance(sp, list), f"{_path_join(where)}.scanned_paths must be array", errors)
    if isinstance(sp, list):
        for i, v in enumerate(sp):
            _require(isinstance(v, str), f"{_path_join(where + ['scanned_paths', i])} must be string", errors)


def _check_invariants(inv: Any, where: Sequence[Any], errors: List[str]) -> None:
    req = ["anchor_presence", "anchor_coverage", "loop_risk", "contradiction_risk", "notes"]
    _require_keys(inv, req, where, errors)
    _require_no_extra_keys(inv, req, where, errors)
    if not isinstance(inv, dict):
        return

    _require(_is_bool_or_null(inv.get("anchor_presence")), f"{_path_join(where)}.anchor_presence must be boolean|null", errors)
    _require(_is_float01_or_null(inv.get("anchor_coverage")), f"{_path_join(where)}.anchor_coverage must be number in [0..1] | null", errors)

    loop_risk = inv.get("loop_risk")
    _require(loop_risk is None or (isinstance(loop_risk, str) and loop_risk in ALLOWED_RISK),
             f"{_path_join(where)}.loop_risk must be one of {sorted(ALLOWED_RISK)}|null",
             errors)

    contradiction_risk = inv.get("contradiction_risk")
    _require(contradiction_risk is None or (isinstance(contradiction_risk, str) and contradiction_risk in ALLOWED_RISK),
             f"{_path_join(where)}.contradiction_risk must be one of {sorted(ALLOWED_RISK)}|null",
             errors)

    notes = inv.get("notes")
    _require(notes is None or isinstance(notes, str), f"{_path_join(where)}.notes must be string|null", errors)


def _check_recommendation(rec: Any, where: Sequence[Any], errors: List[str]) -> None:
    req = ["response_mode", "gate_action", "rationale"]
    _require_keys(rec, req, where, errors)
    _require_no_extra_keys(rec, req, where, errors)
    if not isinstance(rec, dict):
        return

    rm = rec.get("response_mode")
    _require(isinstance(rm, str) and rm in ALLOWED_RESPONSE_MODE,
             f"{_path_join(where)}.response_mode must be one of {sorted(ALLOWED_RESPONSE_MODE)}",
             errors)

    ga = rec.get("gate_action")
    _require(isinstance(ga, str) and ga in ALLOWED_GATE_ACTION,
             f"{_path_join(where)}.gate_action must be one of {sorted(ALLOWED_GATE_ACTION)}",
             errors)

    _require(_is_str_nonempty(rec.get("rationale")), f"{_path_join(where)}.rationale must be non-empty string", errors)


def _check_evidence(evidence: Any, where: Sequence[Any], errors: List[str]) -> None:
    _require(isinstance(evidence, list), f"{_path_join(where)} must be array", errors)
    if not isinstance(evidence, list):
        return

    allowed_keys = ["kind", "message", "ref"]
    req_keys = ["kind", "message"]

    for i, item in enumerate(evidence):
        iw = list(where) + [i]
        _require(isinstance(item, dict), f"{_path_join(iw)} must be object", errors)
        if not isinstance(item, dict):
            continue
        _require_keys(item, req_keys, iw, errors)
        _require_no_extra_keys(item, allowed_keys, iw, errors)

        _require(_is_str_nonempty(item.get("kind")), f"{_path_join(iw)}.kind must be non-empty string", errors)
        _require(_is_str_nonempty(item.get("message")), f"{_path_join(iw)}.message must be non-empty string", errors)
        _require(item.get("ref") is None or isinstance(item.get("ref"), str),
                 f"{_path_join(iw)}.ref must be string|null",
                 errors)


def check_contract(doc: Any) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    top_req = ["schema", "meta", "inputs", "invariants", "state", "recommendation", "evidence"]
    _require(isinstance(doc, dict), "document root must be an object", errors)
    if not isinstance(doc, dict):
        return False, errors

    _require_keys(doc, top_req, [], errors)
    _require_no_extra_keys(doc, top_req, [], errors)

    _require(doc.get("schema") == "anchor_integrity_v0", "schema must be 'anchor_integrity_v0'", errors)

    state = doc.get("state")
    _require(isinstance(state, str) and state in ALLOWED_STATE,
             f"state must be one of {sorted(ALLOWED_STATE)}",
             errors)

    _check_meta(doc.get("meta"), ["meta"], errors)
    _check_inputs(doc.get("inputs"), ["inputs"], errors)
    _check_invariants(doc.get("invariants"), ["invariants"], errors)
    _check_recommendation(doc.get("recommendation"), ["recommendation"], errors)
    _check_evidence(doc.get("evidence"), ["evidence"], errors)

    return len(errors) == 0, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Path to anchor_integrity_v0.json")
    args = ap.parse_args()

    path = Path(args.inp)

    try:
        doc = _read_json(path)
    except FileNotFoundError:
        sys.stderr.write(f"::error::Input file not found: {path}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"::error::Failed to read/parse JSON: {path}\n")
        sys.stderr.write(f"::error::{e}\n")
        return 1

    ok, errors = check_contract(doc)
    if ok:
        sys.stderr.write(f"[OK] anchor_integrity_v0 contract check passed: {path}\n")
        return 0

    sys.stderr.write(f"::error::anchor_integrity_v0 contract check FAILED: {path}\n")
    for msg in errors:
        sys.stderr.write(f"::error::{msg}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
