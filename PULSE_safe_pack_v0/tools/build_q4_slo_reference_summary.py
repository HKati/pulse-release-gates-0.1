#!/usr/bin/env python3
"""
Build a deterministic Q4 SLO reference summary artefact from archived
aggregate latency/cost stats.

Design intent:
- artifact-first
- deterministic
- fail-closed
- no live model calls
- no network calls
- suitable for Core materialization when backed by checked-in reference inputs
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


SPEC_ID = "q4_slo_v0"
SPEC_VERSION = "0.1.0"


def _created_utc_from_source_date_epoch() -> str | None:
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
    explicit_created_utc = explicit_created_utc.strip()
    if explicit_created_utc:
        return explicit_created_utc

    from_sde = _created_utc_from_source_date_epoch()
    if from_sde is not None:
        return from_sde

    raise ValueError(
        "Deterministic output requires --created_utc or SOURCE_DATE_EPOCH"
    )


def _expect_object(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _expect_plain_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _expect_plain_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    return float(value)


def _load_stats_json(path: Path) -> tuple[int, float, float]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON: {e}") from e

    obj = _expect_object(str(path), payload)

    n_requests = _expect_plain_int("n_requests", obj.get("n_requests"))
    latency_p95_ms = _expect_plain_number("latency_ms_p95", obj.get("latency_ms_p95"))
    cost_p95_usd = _expect_plain_number("cost_usd_p95", obj.get("cost_usd_p95"))

    if n_requests < 0:
        raise ValueError("n_requests must be >= 0")
    if latency_p95_ms < 0:
        raise ValueError("latency_ms_p95 must be >= 0")
    if cost_p95_usd < 0:
        raise ValueError("cost_usd_p95 must be >= 0")

    return n_requests, latency_p95_ms, cost_p95_usd


def _build_summary(
    *,
    run_id: str,
    created_utc: str,
    input_manifest: str,
    stats_json: str,
    tool: str,
    tool_version: str,
    git_sha: str | None,
    notes: str | None,
    n_requests: int,
    latency_p95_ms: float,
    cost_p95_usd: float,
    latency_budget_ms: float,
    cost_budget_usd: float,
    min_requests: int,
) -> dict[str, Any]:
    insufficient_evidence = n_requests < min_requests
    latency_ok = latency_p95_ms <= latency_budget_ms
    cost_ok = cost_p95_usd <= cost_budget_usd
    passed = (not insufficient_evidence) and latency_ok and cost_ok

    provenance: dict[str, Any] = {
        "input_manifest": input_manifest,
        "stats_json": stats_json,
        "tool": tool,
        "tool_version": tool_version,
    }
    if git_sha:
        provenance["git_sha"] = git_sha

    method: dict[str, Any] = {
        "kind": "reference",
        "deterministic": True,
        "notes": "Reducer over archived aggregate SLO stats.",
    }

    summary: dict[str, Any] = {
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "run_id": run_id,
        "created_utc": created_utc,
        "n_requests": n_requests,
        "min_requests": min_requests,
        "insufficient_evidence": insufficient_evidence,
        "latency_p95_ms": latency_p95_ms,
        "latency_budget_ms": latency_budget_ms,
        "latency_ok": latency_ok,
        "cost_p95_usd": cost_p95_usd,
        "cost_budget_usd": cost_budget_usd,
        "cost_ok": cost_ok,
        "pass": passed,
        "pass_basis": "latency_and_cost_p95_with_min_requests",
        "primary_metric_id": "q4_slo_budget_conjunction",
        "budget_ratios": {
            "latency_p95_ratio": (
                latency_p95_ms / latency_budget_ms if latency_budget_ms > 0 else None
            ),
            "cost_p95_ratio": (
                cost_p95_usd / cost_budget_usd if cost_budget_usd > 0 else None
            ),
        },
        "method": method,
        "provenance": provenance,
        "decision_rule": [
            "Read archived aggregate SLO stats from a checked-in JSON artefact.",
            "Require n_requests >= min_requests.",
            "Require latency_ms_p95 <= latency_budget_ms.",
            "Require cost_usd_p95 <= cost_budget_usd.",
            "PASS iff all three conditions hold; FAIL otherwise.",
        ],
    }
    if notes:
        summary["notes"] = notes

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats_json", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--input_manifest", required=True)
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--created_utc", default="")
    parser.add_argument("--tool", default="PULSE_q4_reference")
    parser.add_argument("--tool_version", default="0.1.0-dev")
    parser.add_argument(
        "--git_sha",
        default=os.getenv("GITHUB_SHA", "").strip(),
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--latency_budget_ms", type=float, required=True)
    parser.add_argument("--cost_budget_usd", type=float, required=True)
    parser.add_argument("--min_requests", type=int, default=100)
    args = parser.parse_args()

    stats_path = Path(args.stats_json)
    out_path = Path(args.out)

    n_requests, latency_p95_ms, cost_p95_usd = _load_stats_json(stats_path)

    try:
        created_utc = _resolve_created_utc(args.created_utc)
    except ValueError as e:
        parser.error(str(e))

    summary = _build_summary(
        run_id=args.run_id.strip(),
        created_utc=created_utc,
        input_manifest=args.input_manifest.strip(),
        stats_json=str(stats_path),
        tool=args.tool.strip(),
        tool_version=args.tool_version.strip(),
        git_sha=args.git_sha.strip() or None,
        notes=args.notes.strip() or None,
        n_requests=n_requests,
        latency_p95_ms=latency_p95_ms,
        cost_p95_usd=cost_p95_usd,
        latency_budget_ms=float(args.latency_budget_ms),
        cost_budget_usd=float(args.cost_budget_usd),
        min_requests=int(args.min_requests),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")

    print(
        json.dumps(
            {
                "out": str(out_path),
                "spec_id": summary["spec_id"],
                "spec_version": summary["spec_version"],
                "n_requests": summary["n_requests"],
                "latency_p95_ms": summary["latency_p95_ms"],
                "latency_budget_ms": summary["latency_budget_ms"],
                "cost_p95_usd": summary["cost_p95_usd"],
                "cost_budget_usd": summary["cost_budget_usd"],
                "pass": summary["pass"],
                "insufficient_evidence": summary["insufficient_evidence"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
