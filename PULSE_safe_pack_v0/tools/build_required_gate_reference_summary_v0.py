#!/usr/bin/env python3
"""Build deterministic reference summaries for release-grade required gates.

This reducer consumes a checked-in required-gate reference evidence file and
emits a small summary with literal ``pass: true`` only when the selected gate has
explicit passing evidence checks.

It is intentionally narrow:

- it does not read runtime status.json;
- it does not materialize gates;
- it does not call check_gates.py;
- it does not create release authority.

The summary is candidate evidence for the required-gate dispatcher only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "required_gate_reference_summary_v0"
TOOL_VERSION = "0.1.0"
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


class SummaryError(ValueError):
    """Strict deterministic summary-builder error."""


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise SummaryError(f"duplicate JSON key {key!r}")

        result[key] = value

    return result


def _bad_constant(value: str) -> None:
    raise SummaryError(f"non-finite JSON constant {value!r}")


def _finite(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise SummaryError(f"{label} contains a non-finite number")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{label}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{label}.{key}")
        return

    raise SummaryError(f"{label} contains unsupported value type")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SummaryError(f"{label} must be a non-empty string")

    return value.strip()


def _normalize_utc(value: Any) -> str:
    text = _require_text(value, "created_utc")
    parsed = text[:-1] + "+00:00" if text.endswith("Z") else text

    try:
        stamp = dt.datetime.fromisoformat(parsed)

    except ValueError as exc:
        raise SummaryError("created_utc must be ISO-8601") from exc

    if stamp.tzinfo is None:
        raise SummaryError("created_utc must include a timezone")

    return (
        stamp.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise SummaryError(f"{label} must be a regular non-symlink file: {path}")


def _load_evidence(path: Path) -> dict[str, Any]:
    _regular_file(path, "required-gate reference evidence")

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_pairs,
            parse_constant=_bad_constant,
        )

    except SummaryError:
        raise

    except Exception as exc:
        raise SummaryError(f"evidence file is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SummaryError("evidence file must be a JSON object")

    _finite(payload, "evidence")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp, path)

    except Exception:
        if temp.exists():
            temp.unlink()
        raise


def _gate_entry(payload: dict[str, Any], gate_id: str) -> dict[str, Any]:
    if payload.get("schema_version") != "required_gate_current_run_reference_v0":
        raise SummaryError(
            "evidence schema_version must be "
            "'required_gate_current_run_reference_v0'"
        )

    gates = payload.get("gates")
    if not isinstance(gates, dict):
        raise SummaryError("evidence.gates must be an object")

    entry = gates.get(gate_id)
    if not isinstance(entry, dict):
        raise SummaryError(f"evidence has no object entry for gate {gate_id!r}")

    return entry


def _validate_checks(entry: dict[str, Any], gate_id: str) -> tuple[bool, list[str]]:
    checks = entry.get("checks")
    diagnostics: list[str] = []

    if not isinstance(checks, list) or not checks:
        diagnostics.append(f"{gate_id} checks must be a non-empty array")
        return False, diagnostics

    seen: set[str] = set()

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            diagnostics.append(f"{gate_id} check {index} must be an object")
            continue

        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id.strip():
            diagnostics.append(f"{gate_id} check {index} has no id")
            continue

        if check_id in seen:
            diagnostics.append(f"{gate_id} duplicate check id {check_id!r}")
            continue

        seen.add(check_id)

        if check.get("pass") is not True:
            diagnostics.append(f"{gate_id} check {check_id!r} is not pass=true")

        rationale = check.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            diagnostics.append(f"{gate_id} check {check_id!r} has no rationale")

    return not diagnostics, diagnostics


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-id", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--created_utc", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--tool_version", required=True)
    parser.add_argument("--git_sha", required=True)
    parser.add_argument("--notes", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        gate_id = _require_text(args.gate_id, "gate_id")

        if not GATE_ID_RE.fullmatch(gate_id):
            raise SummaryError(f"invalid gate_id {gate_id!r}")

        git_sha = _require_text(args.git_sha, "git_sha").lower()
        if not GIT_SHA_RE.fullmatch(git_sha):
            raise SummaryError("git_sha must be a concrete 40-hex SHA")

        evidence_path = Path(args.evidence_json)
        output_path = Path(args.out)
        created_utc = _normalize_utc(args.created_utc)
        payload = _load_evidence(evidence_path)
        entry = _gate_entry(payload, gate_id)
        passed, diagnostics = _validate_checks(entry, gate_id)

        summary = {
            "schema_version": SCHEMA_VERSION,
            "gate_id": gate_id,
            "pass": passed,
            "status": "passed" if passed else "failed",
            "family": entry.get("family"),
            "created_utc": created_utc,
            "run": {
                "run_id": _require_text(args.run_id, "run_id"),
                "git_sha": git_sha,
            },
            "tool": {
                "name": _require_text(args.tool, "tool"),
                "version": _require_text(args.tool_version, "tool_version"),
                "builder": "build_required_gate_reference_summary_v0.py",
                "builder_version": TOOL_VERSION,
            },
            "checks": entry.get("checks"),
            "diagnostics": diagnostics,
            "notes": _require_text(args.notes, "notes") if args.notes else "",
            "authority_boundary": {
                "creates_release_authority": False,
                "materializes_status": False,
                "materializes_release_required": False,
                "replaces_check_gates": False,
                "reference_evidence_only": True,
            },
        }

        _atomic_json(output_path, summary)

    except SummaryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected summary-builder failure: {exc}", file=sys.stderr)
        return 1

    if not summary["pass"]:
        print(f"ERROR: required-gate reference summary failed for {gate_id}")
        return 1

    print(f"OK: required-gate reference summary passed for {gate_id}")
    print(f"OK: wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
