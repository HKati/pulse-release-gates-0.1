#!/usr/bin/env python3
"""Render legacy Anchor v0 data without promoting proxies into evidence.

WP2I changes the existing Markdown reader, not the preserved v0 JSON producer.
The CLI paths and CI-neutral unavailable-input behavior remain compatible.
This reader does not run WP2H, verify evidence, or decide release authority.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

READER_PROFILE = "legacy-v0-proxy-boundary-v1"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_LITERAL_CHARS = 256
DEFAULT_INPUT = "PULSE_safe_pack_v0/artifacts/anchor_integrity_v0.json"
DEFAULT_OUTPUT = "PULSE_safe_pack_v0/artifacts/anchor_integrity_overlay_v0.md"


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


def _shape_error(value: Any) -> str | None:
    # A format discriminator, not a full v0 schema validation or authentication.
    if not isinstance(value, dict):
        return "legacy_root_is_not_an_object"
    if value.get("schema") != "anchor_integrity_v0":
        return "unsupported_legacy_schema"
    if not isinstance(value.get("invariants"), dict):
        return "legacy_invariants_are_not_an_object"
    return None


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Bound memory and reject ambiguous JSON; paths are in a trusted local FS."""
    try:
        if not path.is_file():
            return None, "legacy_input_missing_or_not_a_regular_file"
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return None, "legacy_input_size_limit"
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant, parse_float=_finite_float)
        error = _shape_error(value)
        return (None, error) if error else (value, None)
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None, "legacy_input_unreadable_or_invalid_json"


def _literal(value: Any) -> str:
    """A bounded ASCII JSON scalar in one code span, never raw Markdown/HTML."""
    if value is not None and type(value) not in (str, bool, int, float):
        value = None
    if isinstance(value, float) and not math.isfinite(value):
        value = None
    if isinstance(value, str) and len(value) > MAX_LITERAL_CHARS:
        value = value[:MAX_LITERAL_CHARS] + "... [truncated]"
    try:
        text = json.dumps(value, ensure_ascii=True, allow_nan=False)
    except (ValueError, OverflowError):
        text = "null"
    if len(text) > 8 * MAX_LITERAL_CHARS:
        text = '"[oversized metadata omitted]"'
    for char in "`<>&":
        text = text.replace(char, "\\u%04x" % ord(char))
    return "`" + text + "`"


def _reported_proxy(value: Any) -> tuple[str, str]:
    if value is None:
        return "unavailable", "null"
    # No bool, string, percentage scaling, normalization or rounding to 1.0.
    if type(value) not in (int, float) or not 0 <= value <= 1:
        return "invalid", "null"
    if isinstance(value, float) and not math.isfinite(value):
        return "invalid", "null"
    return "reported", json.dumps(value, allow_nan=False)


def _render_md(data: dict[str, Any] | None, err: str | None, in_path: Path) -> str:
    error = err or _shape_error(data)
    available = error is None
    inv = data["invariants"] if available else {}
    proxy_status, proxy = _reported_proxy(inv.get("anchor_coverage"))
    lines = [
        "# Anchor Integrity — legacy v0 proxy view",
        "",
        "> **Legacy operational proxy only — not claim-evidence coverage.**",
        "> No claim support, measured cycle risk, response permission or release authority is established.",
        "",
        "## Reader boundary",
        "",
        f"- Reader profile: `{READER_PROFILE}`",
        "- Accepted input format: `anchor_integrity_v0`; raw JSON is not rewritten.",
        f"- Input path (caller-supplied): {_literal(in_path.as_posix())}",
        "- Result: **LEGACY_PROXY_RENDERED**" if available else "- Result: **UNAVAILABLE**",
        "- Fresh evidence checks executed: `false`",
        "- Authority effect: `none`",
        "- Release-authority activation: `false`",
        "",
    ]
    if error:
        lines += [f"- Input diagnostic: {_literal(error)}", ""]
    lines += [
        "## Reported operational proxy",
        "",
        f"- Reported value status: `{proxy_status}`",
        f"- Reported gate-signal proxy: `{proxy}`",
        "- This value is copied from the legacy numeric field, not recomputed from gates.",
        "- It is not a count or proportion of evidence-supported claims.",
        "",
        "## Evidence measurements",
        "",
        "| Measurement | Status | Result |",
        "|---|---|---|",
        "| Claim-level anchor presence | not_run | null |",
        "| Verified binding coverage | not_run | null |",
        "| Verified support coverage | not_run | null |",
        "| Typed dependency-cycle detection | not_run | null |",
        "| Loop risk | not_run | null |",
        "| Contradiction risk | not_run | null |",
        "| Independent-anchor classification | not_run | null |",
        "",
        "No measured result is inferred from a legacy risk label or Paradox source presence.",
        "Legacy state, response/gate recommendations, rationale and free-text notes are not adopted or rendered as findings.",
        "They remain in the original input JSON for historical inspection.",
        "This reader issues no response recommendation and does not authorize a reply or a release.",
        "",
    ]
    if available:
        meta = data.get("meta")
        meta = meta if isinstance(meta, dict) else {}
        inputs = data.get("inputs")
        inputs = inputs if isinstance(inputs, dict) else {}
        lines += ["## Unverified source metadata", ""]
        for key in ("run_id", "commit", "generator", "source_date_epoch"):
            lines.append(f"- {key}: {_literal(meta.get(key))}")
        for key in ("status_path", "paradox_source_path"):
            lines.append(f"- {key}: {_literal(inputs.get(key))}")
        lines += ["", "Metadata is displayed as bounded literal text, not authenticated identity.", ""]
    lines += [
        "## Evidence-bound diagnostics",
        "",
        "Use `tools/build_anchor_integrity_diagnostic_v0_1.py` with an explicitly pinned selection and actual input files.",
        "See `docs/ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md`.",
        "This legacy view does not run that pipeline or substitute for its report.",
        "",
    ]
    return "\n".join(lines)


def _check_output_target(in_path: Path, out_path: Path) -> None:
    """Do not overwrite the source JSON or follow an output file alias.

    The caller controls the local directory. This is not hostile-filesystem or
    concurrent-writer containment, nor an atomic-publication protocol.
    """
    if in_path.resolve() == out_path.resolve():
        raise ValueError("output_must_not_replace_input")
    if out_path.is_symlink():
        raise ValueError("output_symlink_rejected")
    if out_path.exists():
        if not out_path.is_file() or out_path.stat().st_nlink != 1:
            raise ValueError("output_must_be_an_unaliased_regular_file")
        if in_path.exists() and in_path.samefile(out_path):
            raise ValueError("output_must_not_alias_input")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", default=DEFAULT_INPUT,
                        help="Legacy anchor_integrity_v0.json input")
    parser.add_argument("--out", dest="out_path", default=DEFAULT_OUTPUT,
                        help="Markdown destination; only the reader presentation changes")
    args = parser.parse_args()
    in_path, out_path = Path(args.in_path), Path(args.out_path)
    try:
        _check_output_target(in_path, out_path)
        data, error = _read_json(in_path)
        text = _render_md(data, error, in_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Repeat alias guard immediately before the inherited explicit file write.
        _check_output_target(in_path, out_path)
        out_path.write_text(text, encoding="utf-8")
    except (OSError, ValueError, RuntimeError):
        print("Cannot write legacy proxy view: unsafe or unavailable output path.", file=sys.stderr)
        return 2
    # CI-neutral rendering success, including an explicit UNAVAILABLE placeholder.
    # This does not represent successful evidence verification.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
