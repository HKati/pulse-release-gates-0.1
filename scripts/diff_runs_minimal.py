#!/usr/bin/env python3
"""
diff_runs_minimal.py

Compute a minimal, gate-level diff between two PULSE runs.

By default the script compares two status.json files and prints a compact
JSON summary of gates whose outcome changed between the runs.

It can be extended later to read from a JSONL history file, but v0 keeps
the interface simple and explicit.

Example usage:

    # Compare two explicit status.json files
    python scripts/diff_runs_minimal.py \
        --a runA/status.json \
        --b runB/status.json

    # Use the default locations under the safe-pack (for quick local runs)
    python scripts/diff_runs_minimal.py

Output (JSON, simplified):

    {
      "run_a": {"label": "runA/status.json"},
      "run_b": {"label": "runB/status.json"},
      "summary": {
        "total_gates": 12,
        "changed_gates": 3,
        "pass_to_fail": 1,
        "fail_to_pass": 2,
        "other_changes": 0
      },
      "gates": [
        {
          "id": "q1_grounded_ok",
          "state_a": "pass",
          "state_b": "fail",
          "change": "pass_to_fail"
        },
        ...
      ]
    }

You can also ask for a markdown table:

    python scripts/diff_runs_minimal.py --format markdown
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass
class GateState:
    id: str
    state: str  # "pass" | "fail" | "missing" | "other"
    raw: Any


@dataclass
class GateDiff:
    id: str
    state_a: str
    state_b: str
    change: str  # "pass_to_fail" | "fail_to_pass" | "added" | "removed" | "other_change"


def _default_status_path(side: str) -> str:
    """
    Default status.json path for a given side ("a" or "b").

    We assume the safe-pack default:
    PULSE_safe_pack_v0/artifacts/status.json

    Callers can override with --a / --b.
    """
    return os.path.join("PULSE_safe_pack_v0", "artifacts", "status.json")


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a minimal gate-level diff between two PULSE runs."
    )

    parser.add_argument(
        "--a",
        type=str,
        default=_default_status_path("a"),
        help=(
            "Path to status.json for run A. "
            "Defaults to PULSE_safe_pack_v0/artifacts/status.json."
        ),
    )

    parser.add_argument(
        "--b",
        type=str,
        default=None,
        help=(
            "Path to status.json for run B. "
            "If not provided, defaults to the same as --a (useful only "
            "when overridden in CI or wrappers)."
        ),
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=("json", "markdown"),
        default="json",
        help="Output format: 'json' (default) or 'markdown'.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output file path. If not set, prints to stdout.",
    )

    return parser.parse_args(argv)


def _load_json(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"failed to parse JSON from {path}: {e}") from e


def _extract_gates(status: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Extract gate entries from a status.json object into a dict keyed by gate id.

    Supports two common layouts:
    - status["gates"] is a dict: {gate_id: gate_object}
    - status["gates"] is a list: [{"id": "...", ...}, {"id": "...", ...}, ...]

    Falls back to empty dict if 'gates' is missing or unrecognised.
    """
    gates_obj = status.get("gates")
    result: Dict[str, Any] = {}

    if isinstance(gates_obj, dict):
        # Assume keys are gate IDs
        for gate_id, gate_val in gates_obj.items():
            result[str(gate_id)] = gate_val
    elif isinstance(gates_obj, list):
        for item in gates_obj:
            if not isinstance(item, dict):
                continue
            gate_id = item.get("id") or item.get("name")
            if gate_id:
                result[str(gate_id)] = item
    else:
        # Unknown structure; return empty and let caller handle
        return {}

    return result


def _infer_state(gate: Optional[Mapping[str, Any]]) -> GateState:
    """
    Infer a coarse state label for a gate.

    The heuristic looks for:
    - boolean 'ok' or 'pass' fields
    - string 'status' fields (PASS/FAIL-like)
    and falls back to 'other' if it cannot classify.

    If gate is None, returns state 'missing'.
    """
    if gate is None:
        return GateState(id="", state="missing", raw=None)  # id will be set by caller

    # Prefer explicit booleans
    for key in ("ok", "pass"):
        val = gate.get(key)
        if isinstance(val, bool):
            return GateState(id="", state="pass" if val else "fail", raw=gate)

    # Fall back to string status
    status_val = gate.get("status")
    if isinstance(status_val, str):
        s = status_val.strip().lower()
        if s in ("pass", "ok", "success", "passed"):
            return GateState(id="", state="pass", raw=gate)
        if s in ("fail", "failed", "error", "blocked"):
            return GateState(id="", state="fail", raw=gate)

    # Unknown classification
    return GateState(id="", state="other", raw=gate)


def _classify_change(state_a: str, state_b: str) -> str:
    if state_a == "missing" and state_b != "missing":
        return "added"
    if state_b == "missing" and state_a != "missing":
        return "removed"
    if state_a == "pass" and state_b == "fail":
        return "pass_to_fail"
    if state_a == "fail" and state_b == "pass":
        return "fail_to_pass"
    if state_a == state_b:
        return "unchanged"
    return "other_change"


def _compute_gate_diffs(
    gates_a: Mapping[str, Any],
    gates_b: Mapping[str, Any],
) -> Tuple[List[GateDiff], Dict[str, int]]:
    diffs: List[GateDiff] = []
    summary = {
        "total_gates": 0,
        "changed_gates": 0,
        "pass_to_fail": 0,
        "fail_to_pass": 0,
        "added": 0,
        "removed": 0,
        "other_changes": 0,
    }

    all_ids = sorted(set(gates_a.keys()) | set(gates_b.keys()))
    summary["total_gates"] = len(all_ids)

    for gate_id in all_ids:
        raw_a = gates_a.get(gate_id)
        raw_b = gates_b.get(gate_id)

        gs_a = _infer_state(raw_a)
        gs_b = _infer_state(raw_b)
        gs_a.id = gate_id
        gs_b.id = gate_id

        change = _classify_change(gs_a.state, gs_b.state)
        if change == "unchanged":
            continue

        summary["changed_gates"] += 1
        if change in summary:
            summary[change] += 1
        elif change == "other_change":
            summary["other_changes"] += 1

        diffs.append(
            GateDiff(
                id=gate_id,
                state_a=gs_a.state,
                state_b=gs_b.state,
                change=change,
            )
        )

    return diffs, summary


def _format_json_output(
    label_a: str,
    label_b: str,
    diffs: List[GateDiff],
    summary: Dict[str, int],
) -> str:
    payload = {
        "run_a": {"label": label_a},
        "run_b": {"label": label_b},
        "summary": summary,
        "gates": [
            {
                "id": d.id,
                "state_a": d.state_a,
                "state_b": d.state_b,
                "change": d.change,
            }
            for d in diffs
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def _format_markdown_output(
    label_a: str,
    label_b: str,
    diffs: List[GateDiff],
    summary: Dict[str, int],
) -> str:
    lines: List[str] = []
    lines.append(f"# PULSE minimal diff: {label_a} → {label_b}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| metric         | value |")
    lines.append("|----------------|-------|")
    for key in ("total_gates", "changed_gates", "pass_to_fail", "fail_to_pass", "added", "removed", "other_changes"):
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.append("")
    lines.append("## Gate-level changes")
    lines.append("")
    if not diffs:
        lines.append("_No gate-level changes detected._")
        return "\n".join(lines)

    lines.append("| gate_id | state_a | state_b | change |")
    lines.append("|---------|---------|---------|--------|")
    for d in diffs:
        lines.append(f"| {d.id} | {d.state_a} | {d.state_b} | {d.change} |")

    return "\n".join(lines)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)

    path_a = args.a
    path_b = args.b or args.a  # if b not provided, use a (caller should usually override)

    try:
        status_a = _load_json(path_a)
        status_b = _load_json(path_b)
    except Exception as exc:  # noqa: BLE001
        print(f"[diff_runs_minimal] ERROR: {exc}", file=sys.stderr)
        return 1

    if not isinstance(status_a, dict) or not isinstance(status_b, dict):
        print(
            "[diff_runs_minimal] ERROR: expected both status files to have "
            "JSON objects at top level.",
            file=sys.stderr,
        )
        return 1

    gates_a = _extract_gates(status_a)
    gates_b = _extract_gates(status_b)

    diffs, summary = _compute_gate_diffs(gates_a, gates_b)

    label_a = path_a
    label_b = path_b

    if args.format == "json":
        output = _format_json_output(label_a, label_b, diffs, summary)
    else:
        output = _format_markdown_output(label_a, label_b, diffs, summary)

    if args.output:
        try:
            parent = os.path.dirname(os.path.abspath(args.output))
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
                f.write("\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[diff_runs_minimal] ERROR writing to {args.output}: {exc}", file=sys.stderr)
            return 1
        print(f"[diff_runs_minimal] Wrote diff to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
