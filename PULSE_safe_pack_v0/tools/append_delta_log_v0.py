#!/usr/bin/env python
"""
append_delta_log_v0.py

Append a single run snapshot to delta_log_v0.jsonl, based on the
decision_paradox_summary_v0.json artefact.

Input (per run):
    - decision_paradox_summary_v0.json
      (produced by summarise_decision_paradox_v0.py)

Output (append mode):
    - delta_log_v0.jsonl

Each line in delta_log_v0.jsonl is a JSON object with:

    - decision
    - stability metrics:
        - instability_score
        - rdsi
        - risk_score_v0
        - risk_zone
    - paradox overview (max_tension, dominant axes)
    - EPF overview (phi/theta/energy)
    - optional git / pipeline metadata
"""

import argparse
import json
import os
from typing import Any, Dict, Optional, Tuple

Summary = Dict[str, Any]
DeltaRow = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _load_json(path: str) -> Optional[Summary]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[delta_log_v0] WARNING: summary file not found: {path!r}")
        return None
    except json.JSONDecodeError:
        print(f"[delta_log_v0] WARNING: invalid JSON in {path!r}")
        return None


def _compute_risk_score_and_zone(
    instability_score: Optional[float], rdsi: Optional[float]
) -> Tuple[Optional[float], str]:
    """Compute v0 decision risk score and zone from instability and RDSI."""
    if instability_score is None or rdsi is None:
        return None, "UNKNOWN"

    try:
        inst = float(instability_score)
        r = float(rdsi)
    except (TypeError, ValueError):
        return None, "UNKNOWN"

    raw = inst * (1.0 - r)

    # clamp to [0, 1]
    risk = max(0.0, min(1.0, raw))

    if risk < 0.25:
        zone = "LOW"
    elif risk < 0.50:
        zone = "MEDIUM"
    elif risk < 0.75:
        zone = "HIGH"
    else:
        zone = "CRITICAL"

    return risk, zone


def _build_delta_row(summary: Summary, args: argparse.Namespace) -> DeltaRow:
    stability = summary.get("stability") or {}
    paradox = summary.get("paradox_overview") or {}
    epf = summary.get("epf_overview") or {}

    instability_score = _safe_float(stability.get("instability_score"))
    rdsi = _safe_float(stability.get("rdsi"))

    risk_score = stability.get("risk_score_v0")
    risk_zone = stability.get("risk_zone")

    # fallback: ha a summary még nem tartalmazza a risk mezőket
    if risk_score is None or risk_zone is None:
        risk_score, risk_zone = _compute_risk_score_and_zone(
            instability_score,
            rdsi,
        )

    row: DeltaRow = {
        "run_id": summary.get("run_id"),
        "decision": summary.get("decision"),
        "type": summary.get("type"),
        # flattened stability
        "instability_score": instability_score,
        "rdsi": rdsi,
        "risk_score_v0": risk_score,
        "risk_zone": risk_zone,
        # paradox overview
        "max_paradox_tension": _safe_float(paradox.get("max_tension")),
        "dominant_axes": paradox.get("dominant_axes"),
        # EPF overview
        "phi_potential": _safe_float(epf.get("phi_potential")),
        "theta_distortion": _safe_float(epf.get("theta_distortion")),
        "energy_delta": _safe_float(epf.get("energy_delta")),
        # git / pipeline metadata (optional)
        "git_commit": args.git_commit,
        "git_branch": args.git_branch,
        "pipeline_run_id": args.pipeline_run_id,
    }

    return row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Append a single run snapshot from decision_paradox_summary_v0.json "
            "to delta_log_v0.jsonl."
        )
    )
    parser.add_argument(
        "--summary",
        dest="summary_path",
        default="artifacts/decision_paradox_summary_v0.json",
        help=(
            "Path to decision_paradox_summary_v0.json "
            "(default: artifacts/decision_paradox_summary_v0.json)"
        ),
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="artifacts/delta_log_v0.jsonl",
        help=(
            "Path to delta_log_v0.jsonl (default: artifacts/delta_log_v0.jsonl). "
            "File will be created if it does not exist."
        ),
    )
    parser.add_argument(
        "--git-commit",
        dest="git_commit",
        default=os.environ.get("GIT_COMMIT") or os.environ.get("GITHUB_SHA"),
        help="Git commit hash to record (default: $GIT_COMMIT or $GITHUB_SHA, if set).",
    )
    parser.add_argument(
        "--git-branch",
        dest="git_branch",
        default=os.environ.get("GIT_BRANCH") or os.environ.get("GITHUB_REF_NAME"),
        help="Git branch name to record (default: $GIT_BRANCH or $GITHUB_REF_NAME, if set).",
    )
    parser.add_argument(
        "--pipeline-run-id",
        dest="pipeline_run_id",
        default=os.environ.get("GITHUB_RUN_ID"),
        help="Optional CI/pipeline run identifier to attach as metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    summary = _load_json(args.summary_path)
    if summary is None:
        print("[delta_log_v0] nothing to append (summary missing)")
        return

    row = _build_delta_row(summary, args)

    # gondoskodunk róla, hogy a kimeneti könyvtár létezzen
    out_dir = os.path.dirname(args.out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    # append as one line of JSON
    with open(args.out_path, "a", encoding="utf-8") as f:
        json.dump(row, f, ensure_ascii=False)
        f.write("\n")

    print(f"[delta_log_v0] appended run {row.get('run_id')!r} to {args.out_path!r}")


if __name__ == "__main__":
    main()
