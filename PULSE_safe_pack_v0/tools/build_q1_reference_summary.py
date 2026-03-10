#!/usr/bin/env python3
"""
Build a deterministic Q1 groundedness reference summary artefact from
pre-labeled JSONL judgments.

Design intent:
- artifact-first
- deterministic reducer over archived judgments
- shadow/reference-only
- no live model calls, no network calls, no gate promotion by itself

Input JSONL format:
- one JSON object per line
- required field: `label`
- optional field: `eligible` (defaults to true)

Allowed labels:
- SUPPORTED
- UNSUPPORTED
- ABSTAIN
- UNKNOWN

Pass labels:
- SUPPORTED
- ABSTAIN
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Any

SPEC_ID = "q1_groundedness_v0"
SPEC_VERSION = "0.1.0"

ALLOWED_LABELS = ("SUPPORTED", "UNSUPPORTED", "ABSTAIN", "UNKNOWN")
PASS_LABELS = {"SUPPORTED", "ABSTAIN"}

PRIMARY_METRIC_ID = "grounded_rate"
THRESHOLD = 0.85
ALPHA = 0.05
MIN_N_ELIGIBLE = 100

# Normal approximation constant for Wilson interval at alpha=0.05
Z_95 = 1.959963984540054


def _created_utc_from_source_date_epoch() -> str | None:
    """
    Stable timestamp source for deterministic artefacts.
    Returns an ISO UTC string when SOURCE_DATE_EPOCH is set and valid,
    otherwise returns None.
    """
    sde = os.getenv("SOURCE_DATE_EPOCH", "").strip()
    if not sde:
        return None
    if not sde.isdigit():
        raise ValueError("SOURCE_DATE_EPOCH must be an integer Unix timestamp")
    ts = int(sde)
    return (
        dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _resolve_created_utc(explicit_created_utc: str) -> str:
    """
    Deterministic created_utc resolution:
    - prefer explicit --created_utc
    - else use SOURCE_DATE_EPOCH
    - else fail closed
    """
    explicit_created_utc = explicit_created_utc.strip()
    if explicit_created_utc:
        return explicit_created_utc

    from_sde = _created_utc_from_source_date_epoch()
    if from_sde is not None:
        return from_sde

    raise ValueError(
        "Deterministic output requires --created_utc or SOURCE_DATE_EPOCH"
    )


def _wilson_lower_bound(successes: int, n: int, z: float = Z_95) -> float:
    if n <= 0:
        return 0.0
    phat = successes / n
    denom = 1.0 + (z * z) / n
    center = phat + (z * z) / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) / n) + ((z * z) / (4.0 * n * n)))
    return max(0.0, (center - margin) / denom)


def _load_jsonl_labels(path: Path) -> tuple[int, int, dict[str, int]]:
    counts = {label: 0 for label in ALLOWED_LABELS}
    n_total = 0
    n_eligible = 0

    with path.open("r", encoding="utf-8", errors="strict") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}: invalid JSON on line {lineno}: {e}") from e

            if not isinstance(obj, dict):
                raise ValueError(f"{path}: line {lineno} is not a JSON object")

            n_total += 1

            eligible = obj.get("eligible", True)
            if not isinstance(eligible, bool):
                raise ValueError(f"{path}: line {lineno} has non-boolean 'eligible' field")

            if not eligible:
                continue

            label = obj.get("label")
            if not isinstance(label, str):
                raise ValueError(f"{path}: line {lineno} is missing string field 'label'")

            label = label.strip().upper()
            if label not in ALLOWED_LABELS:
                raise ValueError(
                    f"{path}: line {lineno} has invalid label {label!r}; "
                    f"expected one of {ALLOWED_LABELS}"
                )

            counts[label] += 1
            n_eligible += 1

    return n_total, n_eligible, counts


def _build_summary(
    *,
    run_id: str,
    created_utc: str,
    input_manifest: str,
    labels_jsonl: str,
    tool: str,
    tool_version: str,
    git_sha: str | None,
    notes: str | None,
    n_total: int,
    n_eligible: int,
    counts: dict[str, int],
) -> dict[str, Any]:
    successes = counts["SUPPORTED"] + counts["ABSTAIN"]
    grounded_rate = (successes / n_eligible) if n_eligible > 0 else 0.0
    wilson_lower_bound = _wilson_lower_bound(successes, n_eligible, z=Z_95)
    insufficient_evidence = n_eligible < MIN_N_ELIGIBLE
    passed = (not insufficient_evidence) and (wilson_lower_bound >= THRESHOLD)

    provenance: dict[str, Any] = {
        "input_manifest": input_manifest,
        "tool": tool,
        "tool_version": tool_version,
        "labels_jsonl": labels_jsonl,
    }
    if git_sha:
        provenance["git_sha"] = git_sha

    method: dict[str, Any] = {
        "kind": "reference",
        "deterministic": True,
        "notes": "Reducer over archived per-example groundedness labels.",
    }

    summary: dict[str, Any] = {
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "run_id": run_id,
        "created_utc": created_utc,
        "n": n_eligible,
        "score": grounded_rate,
        "threshold": THRESHOLD,
        "pass": passed,
        "method": method,
        "provenance": provenance,
        "primary_metric_id": PRIMARY_METRIC_ID,
        "grounded_rate": grounded_rate,
        "wilson_lower_bound": wilson_lower_bound,
        "alpha": ALPHA,
        "pass_basis": "wilson_lower_bound",
        "min_n_eligible": MIN_N_ELIGIBLE,
        "insufficient_evidence": insufficient_evidence,
        "counts": {
            "SUPPORTED": counts["SUPPORTED"],
            "UNSUPPORTED": counts["UNSUPPORTED"],
            "ABSTAIN": counts["ABSTAIN"],
            "UNKNOWN": counts["UNKNOWN"],
            "n_total": n_total,
            "n_eligible": n_eligible,
            "n_excluded": n_total - n_eligible,
        },
        "decision_rule": [
            "Compute grounded_rate over eligible examples.",
            "Compute Wilson lower bound (alpha=0.05).",
            "PASS iff n_eligible >= 100 and wilson_lower_bound >= 0.85.",
            "FAIL otherwise.",
        ],
    }

    if notes:
        summary["notes"] = notes

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels_jsonl", required=True, help="Path to per-example groundedness labels JSONL.")
    parser.add_argument("--out", required=True, help="Path to output Q1 summary artefact JSON.")
    parser.add_argument(
        "--input_manifest",
        required=True,
        help="Dataset/input manifest path recorded into provenance.",
    )
    parser.add_argument("--run_id", required=True, help="Stable run identifier for this summary.")
        parser.add_argument(
        "--created_utc",
        default="",
        help=(
            "UTC timestamp to embed in the artefact. "
            "Required unless SOURCE_DATE_EPOCH is set."
        ),
    )
    
    parser.add_argument(
        "--tool",
        default="PULSE_q1_reference",
        help="Tool name recorded in provenance.",
    )
    parser.add_argument(
        "--tool_version",
        default="0.1.0-dev",
        help="Tool version recorded in provenance.",
    )
    parser.add_argument(
        "--git_sha",
        default=os.getenv("GITHUB_SHA", "").strip(),
        help="Optional git SHA recorded in provenance.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Optional free-text note recorded at top level.",
    )
    args = parser.parse_args()

    labels_path = Path(args.labels_jsonl)
    out_path = Path(args.out)

    n_total, n_eligible, counts = _load_jsonl_labels(labels_path)

        try:
        created_utc = _resolve_created_utc(args.created_utc)
    except ValueError as e:
        parser.error(str(e))

    summary = _build_summary(
        run_id=args.run_id.strip(),
        created_utc=created_utc,
        input_manifest=args.input_manifest.strip(),
        labels_jsonl=str(labels_path),
        tool=args.tool.strip(),
        tool_version=args.tool_version.strip(),
        git_sha=args.git_sha.strip() or None,
        notes=args.notes.strip() or None,
        n_total=n_total,
        n_eligible=n_eligible,
        counts=counts,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")

    print(json.dumps(
        {
            "out": str(out_path),
            "spec_id": summary["spec_id"],
            "spec_version": summary["spec_version"],
            "n": summary["n"],
            "score": summary["score"],
            "threshold": summary["threshold"],
            "pass": summary["pass"],
            "wilson_lower_bound": summary["wilson_lower_bound"],
            "insufficient_evidence": summary["insufficient_evidence"],
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
