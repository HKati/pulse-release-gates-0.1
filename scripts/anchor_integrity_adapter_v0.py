#!/usr/bin/env python3
"""Emit a conservative, schema-compatible legacy Anchor v0 diagnostic.

WP2J removes gate-derived evidence claims from the existing JSON producer.
Gate booleans are unverified operational notes only. No claim/evidence or
cycle check runs here. Use WP2H with explicit evidence for fresh diagnostics.
UNKNOWN/SILENCE/CLOSED are legacy non-enforcing compatibility placeholders,
not a finding of anchor loss, response enforcement, or release authority.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any

PRODUCER_PROFILE = "legacy-v0-unmeasured-boundary-v1"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
DEFAULT_STATUS = "PULSE_safe_pack_v0/artifacts/status.json"
DEFAULT_PARADOX_SOURCE = "_site/paradox/core/v0/source_v0.json"
DEFAULT_OUTPUT = "anchor_integrity_v0.json"
SIGNAL_IDS = (
    "q1_grounded_ok", "q2_consistency_ok", "q3_fairness_ok",
    "q4_slo_ok", "external_all_pass",
)
RATIONALE = (
    "Unmeasured legacy diagnostic: claim/evidence and cycle checks were not run. "
    "UNKNOWN/SILENCE/CLOSED are non-enforcing compatibility placeholders, "
    "not anchor-loss findings, response enforcement or a release decision. "
    "Use tools/build_anchor_integrity_diagnostic_v0_1.py with explicit evidence."
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non_finite_json_constant")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non_finite_json_number")
    return number


def _check_json_depth(raw: bytes) -> None:
    """Bound container nesting before decoding; quoted delimiters are inert.

    This is only a resource precheck. The standard JSON decoder still validates
    grammar, encoding, duplicate keys and numeric representations.
    """
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
                raise ValueError("input_depth_limit")
        elif byte in (93, 125):
            depth -= 1
            if depth < 0:
                raise ValueError("invalid_container_nesting")


def _read_json(path: Path) -> dict[str, Any]:
    """Bound reads of local regular files. No network or code is evaluated.

    The caller controls the local filesystem. This is not a source-authentication
    boundary or an atomic snapshot. The nonblocking open prevents FIFO hangs.
    """
    if path.is_symlink():
        raise ValueError("input_symlink_rejected")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("input_not_regular")
        if before.st_size > MAX_INPUT_BYTES:
            raise ValueError("input_size_limit")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(fd)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("input_size_limit")
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != after.st_size:
            raise ValueError("input_changed_during_read")
    finally:
        os.close(fd)
    _check_json_depth(raw)
    value = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=_unique_object,
                       parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(value, dict):
        raise ValueError("input_root_not_object")
    return value


def _safe_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _read_json(path), None
    except FileNotFoundError:
        return None, "input_missing"
    except (OSError, UnicodeError, ValueError, RecursionError):
        # Fixed diagnostic: do not echo input text or OS exception content.
        return None, "input_unreadable_or_invalid"


def _anchor_signals_from_status(status: dict[str, Any]) -> tuple[None, None, list[dict[str, str]]]:
    """Retain only literal Boolean observations, never anchor or coverage claims.

    There is deliberately no gate-ratio computation. The v0 schema has no typed
    operational-proxy field; do not overload its evidence-measurement slots.
    """
    gates = status.get("gates")
    if not isinstance(gates, dict):
        code = "status_gates_missing" if "gates" not in status else "status_gates_not_object"
        return None, None, [{"kind": "input_diagnostic", "message": code}]
    notes = []
    for name in SIGNAL_IDS:
        if name not in gates:
            continue
        value = gates[name]
        if type(value) is bool:
            notes.append({"kind": "operational_signal", "message":
                          name + "=" + ("true" if value else "false") +
                          "; unverified gate declaration, not claim evidence"})
        else:
            notes.append({"kind": "input_diagnostic", "message":
                          name + ": non_boolean_operational_signal_ignored"})
    return None, None, notes


def _loop_risk_from_paradox_source(source: dict[str, Any] | None) -> tuple[None, list[dict[str, str]]]:
    notes = [] if source is None else [{"kind": "input_diagnostic", "message":
             "paradox_metadata_present; cycle_check_not_run; no_risk_inferred"}]
    return None, notes


def _classify(anchor_presence: Any, anchor_coverage: Any, loop_risk: Any) -> tuple[str, str, str, str]:
    """The retained helper cannot promote supplied/proxy values to permission."""
    return "UNKNOWN", "SILENCE", "CLOSED", RATIONALE


def _source_epoch() -> int | None:
    value = os.environ.get("SOURCE_DATE_EPOCH", "")
    if not value:
        return None
    # Metadata is caller supplied, not a trusted clock or signing time.
    if not value.isascii() or not value.isdecimal() or len(value) > 19:
        raise ValueError("invalid_source_date_epoch")
    epoch = int(value)
    if epoch > 2**63 - 1:
        raise ValueError("invalid_source_date_epoch")
    return epoch


def build_overlay(status_path: Path, paradox_path: Path | None,
                  run_id: str = "", commit: str = "",
                  source_date_epoch: int | None = None) -> dict[str, Any]:
    if source_date_epoch is not None and (type(source_date_epoch) is not int or
                                         not 0 <= source_date_epoch <= 2**63 - 1):
        raise ValueError("invalid_source_date_epoch")
    if not isinstance(run_id, str) or not isinstance(commit, str):
        raise ValueError("invalid_identity_metadata")
    notes = [{"kind": "producer_profile", "message": PRODUCER_PROFILE},
             {"kind": "measurement_boundary", "message":
              "claim/evidence, cycle and contradiction checks: not_run; results: null"}]
    status, error = _safe_read_json(status_path)
    if error:
        notes.append({"kind": "input_diagnostic", "message": "status:" + error})
    else:
        _, _, observed = _anchor_signals_from_status(status)
        notes.extend(observed)
    if paradox_path is not None:
        source, error = _safe_read_json(paradox_path)
        if error:
            notes.append({"kind": "input_diagnostic", "message": "paradox:" + error})
        else:
            _, observed = _loop_risk_from_paradox_source(source)
            notes.extend(observed)
    state, response, gate, rationale = _classify(None, None, None)
    return {
        "schema": "anchor_integrity_v0",
        "meta": {"run_id": run_id or None, "commit": commit or None,
                 "generator": "scripts/anchor_integrity_adapter_v0.py",
                 "source_date_epoch": source_date_epoch},
        "inputs": {"status_path": str(status_path),
                   "paradox_source_path": str(paradox_path) if paradox_path is not None else None,
                   "scanned_paths": [str(status_path)] +
                       ([str(paradox_path)] if paradox_path is not None else [])},
        "invariants": {"anchor_presence": None, "anchor_coverage": None,
                       "loop_risk": None, "contradiction_risk": None,
                       "notes": PRODUCER_PROFILE + "; diagnostic_only; authority_effect=none; "
                           "all evidence measurements not_run; no gate ratio emitted"},
        "state": state,
        "recommendation": {"response_mode": response, "gate_action": gate,
                           "rationale": rationale},
        "evidence": sorted(notes, key=lambda item: (item["kind"], item["message"])),
    }


def _check_output_target(inputs: list[Path], output: Path) -> None:
    """Protect both input roles under a trusted local-directory assumption.

    Not an atomic publication protocol or hostile concurrent-writer containment.
    """
    resolved = output.resolve()
    if any(path.resolve() == resolved for path in inputs):
        raise ValueError("output_must_not_replace_input")
    if output.is_symlink():
        raise ValueError("output_symlink_rejected")
    if output.exists():
        info = output.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("output_must_be_unaliased_regular_file")
        if any(path.exists() and path.samefile(output) for path in inputs):
            raise ValueError("output_must_not_alias_input")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", default=DEFAULT_STATUS)
    parser.add_argument("--paradox-source", default=DEFAULT_PARADOX_SOURCE,
                        help="Optional local Paradox metadata; empty string disables this input")
    parser.add_argument("--out", default=DEFAULT_OUTPUT)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument("--commit", default=os.getenv("GITHUB_SHA", ""))
    args = parser.parse_args()
    status_path = Path(args.status)
    paradox_path = Path(args.paradox_source) if args.paradox_source else None
    output = Path(args.out)
    inputs = [status_path] + ([paradox_path] if paradox_path is not None else [])
    try:
        _check_output_target(inputs, output)
        overlay = build_overlay(status_path, paradox_path, args.run_id, args.commit, _source_epoch())
        raw = (json.dumps(overlay, indent=2, sort_keys=True, ensure_ascii=True,
                          allow_nan=False) + "\n").encode("utf-8")
        _check_output_target(inputs, output)
        output.write_bytes(raw)
    except (OSError, ValueError, RuntimeError):
        print("Cannot write legacy Anchor diagnostic: invalid metadata or unsafe/unavailable output.",
              file=sys.stderr)
        return 2
    # Compatibility: writing an explicit unknown diagnostic is CI-neutral.
    # Exit 0 is not an evidence check, authority approval or reply permission.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
