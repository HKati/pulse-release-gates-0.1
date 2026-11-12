#!/usr/bin/env python3
"""Check the bounded legacy Anchor v0 format, never evidence or authority.

WP2K rejects ambiguous byte inputs and checks exact numeric values. The frozen
v0 schema still admits historical measurements/labels as data; accepting their
format does not verify them or authorize responses/releases. The WP2J producer
and WP2I reader are not changed. CLI: --in FILE; exit 0=format only, 1=rejected,
2=argument/installation failure. This checker never writes to input files.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
from decimal import Decimal, InvalidOperation
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ALLOWED_STATE = {"ANCHORED", "PARTIAL", "ANCHOR_LOST", "UNKNOWN"}
ALLOWED_RESPONSE_MODE = {"ANSWER", "BOUNDARY", "ASK_FOR_ANCHOR", "SILENCE"}
ALLOWED_GATE_ACTION = {"OPEN", "SLOW", "CLOSED"}
ALLOWED_RISK = {"low", "medium", "high"}


CHECKER_PROFILE = "legacy-v0-strict-format-v1"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_NUMBER_CHARS = 1024
MAX_ERRORS = 64


class InputRejected(ValueError):
    """A fixed diagnostic code; never include untrusted JSON or path text."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputRejected("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise InputRejected("non_finite_json_number")


def _parse_integer(token: str) -> int:
    if len(token) > MAX_NUMBER_CHARS:
        raise InputRejected("numeric_token_limit")
    return int(token)


def _parse_decimal(token: str) -> Decimal:
    if len(token) > MAX_NUMBER_CHARS:
        raise InputRejected("numeric_token_limit")
    try:
        number = Decimal(token)
    except (InvalidOperation, ValueError) as exc:
        raise InputRejected("invalid_json_number") from exc
    if not number.is_finite():
        raise InputRejected("non_finite_json_number")
    return number


def _check_json_depth(raw: bytes) -> None:
    """Resource precheck only; the JSON decoder still validates the grammar."""
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise InputRejected("input_depth_limit")
        elif byte in (93, 125):
            depth -= 1
            if depth < 0:
                raise InputRejected("invalid_json_nesting")


def _decode_json(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise InputRejected("input_size_limit")
    _check_json_depth(raw)
    try:
        return json.loads(raw.decode("utf-8", errors="strict"),
                          object_pairs_hook=_unique_object,
                          parse_int=_parse_integer, parse_float=_parse_decimal,
                          parse_constant=_reject_constant)
    except InputRejected:
        raise
    except (UnicodeError, ValueError, RecursionError, InvalidOperation) as exc:
        raise InputRejected("invalid_json") from exc


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _read_json(path: Path) -> Any:
    """Read one bounded regular file; retained bytes are not a host attestation.

    The local host and parent directories remain trusted. Final symlinks are
    rejected; NONBLOCK prevents a selected FIFO from blocking before fstat.
    Before/after metadata checks detect observed changes, not hostile races.
    """
    if path.is_symlink():
        raise InputRejected("input_symlink_rejected")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise InputRejected("input_not_regular")
        if before.st_size > MAX_INPUT_BYTES:
            raise InputRejected("input_size_limit")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(fd)
        if len(raw) > MAX_INPUT_BYTES:
            raise InputRejected("input_size_limit")
        if _file_identity(before) != _file_identity(after) or len(raw) != after.st_size:
            raise InputRejected("input_changed_during_read")
    finally:
        os.close(fd)
    return _decode_json(raw)


def _is_str_nonempty(x: Any) -> bool:
    return isinstance(x, str) and len(x) >= 1


def _is_str_or_null(x: Any) -> bool:
    return x is None or isinstance(x, str)


def _is_bool_or_null(x: Any) -> bool:
    return x is None or isinstance(x, bool)


def _is_int_or_null_nonneg(x: Any) -> bool:
    if x is None:
        return True
    if type(x) is int:
        return x >= 0
    if type(x) is float:
        return math.isfinite(x) and x >= 0 and x.is_integer()
    if type(x) is Decimal:
        return x.is_finite() and x >= 0 and x == x.to_integral_value()
    return False


def _is_float01_or_null(x: Any) -> bool:
    if x is None:
        return True
    if type(x) is int:
        # Do not cast enormous integers to float or round at the range boundary.
        return 0 <= x <= 1
    if type(x) is float:
        return math.isfinite(x) and 0 <= x <= 1
    if type(x) is Decimal:
        return x.is_finite() and 0 <= x <= 1
    return False


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
    if not cond and len(errors) < MAX_ERRORS:
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
    if any(k not in allowed_set for k in obj):
        # Do not echo arbitrary key text into GitHub annotation messages.
        _require(False, f"{_path_join(where)} has unexpected keys", errors)


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True, help="Legacy JSON file; format check only")
    args = ap.parse_args()
    try:
        doc = _read_json(Path(args.inp))
    except FileNotFoundError:
        sys.stderr.write("::error::anchor_integrity_v0: input_missing\n")
        return 1
    except InputRejected as exc:
        sys.stderr.write(f"::error::anchor_integrity_v0: {exc}\n")
        return 1
    except (OSError, ValueError, RecursionError, OverflowError):
        sys.stderr.write("::error::anchor_integrity_v0: input_unreadable_or_invalid\n")
        return 1

    ok, errors = check_contract(doc)
    if ok:
        sys.stderr.write(
            "[OK] anchor_integrity_v0 format contract check passed; "
            f"profile={CHECKER_PROFILE}; scope=format_only; "
            "evidence_verification=not_run; authority_effect=none\n"
        )
        return 0

    sys.stderr.write("::error::anchor_integrity_v0 format contract check FAILED\n")
    for msg in errors:
        sys.stderr.write(f"::error::{msg}\n")
    if len(errors) == MAX_ERRORS:
        sys.stderr.write("::error::Diagnostic limit reached; further errors may be omitted.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
