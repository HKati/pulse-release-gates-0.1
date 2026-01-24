#!/usr/bin/env python3
"""
Augment the baseline status.json with derived signals and summaries.

This script takes the core PULSE status artefact (gate results + metrics),
as written by run_all.py, and enriches it with:

- refusal-delta summary (if present),
- external detector summaries (when configured),

and then wires these into:
- gates.refusal_delta_pass
- gates.external_all_pass
- external.metrics / external.all_pass

The resulting extended status.json is consumed by check_gates.py
and reporting tooling, but it does not change the core deterministic
gate semantics beyond adding these two deferred gates.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional

import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON loader: returns None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def yload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort YAML loader: returns None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--status", required=True, help="Path to baseline status.json")
parser.add_argument(
    "--thresholds",
    required=True,
    help="YAML file with external detector thresholds (external_thresholds.yaml)",
)
parser.add_argument(
    "--external_dir",
    required=True,
    help="Directory containing *summary.json files from external tools",
)
args = parser.parse_args()

status_path = os.path.abspath(args.status)

# ---------------------------------------------------------------------------
# 0) Load base status (written by run_all.py)
# ---------------------------------------------------------------------------

status: Dict[str, Any] = jload(status_path) or {}
gates: Dict[str, Any] = status.setdefault("gates", {})
metrics: Dict[str, Any] = status.setdefault("metrics", {})
external: Dict[str, Any] = status.setdefault(
    "external",
    {
        "metrics": [],
        "all_pass": True,
    },
)

# ---------------------------------------------------------------------------
# 1) Refusal-delta summary -> metrics + gates + top-level mirror
# ---------------------------------------------------------------------------

pack_dir = os.path.dirname(os.path.dirname(status_path))  # .../PULSE_safe_pack_v0
artifacts_dir = os.path.join(pack_dir, "artifacts")
rd_path = os.path.join(artifacts_dir, "refusal_delta_summary.json")

rd = jload(rd_path)

if rd is not None:
    # Core stats
    metrics["refusal_delta_n"] = rd.get("n", 0)
    metrics["refusal_delta"] = rd.get("delta", 0.0)
    metrics["refusal_delta_ci_low"] = rd.get("ci_low", 0.0)
    metrics["refusal_delta_ci_high"] = rd.get("ci_high", 0.0)

    # Policy parameters (mirrored for ledger)
    metrics["refusal_policy"] = rd.get("policy", "balanced")
    metrics["refusal_delta_min"] = rd.get("delta_min", 0.10)
    metrics["refusal_delta_strict"] = rd.get("delta_strict", 0.10)

    # Significance / tests
    metrics["refusal_p_mcnemar"] = rd.get("p_mcnemar")
    metrics["refusal_pass_min"] = bool(rd.get("pass_min", False))
    metrics["refusal_pass_strict"] = bool(rd.get("pass_strict", False))

    rd_pass = bool(rd.get("pass", False))
    gates["refusal_delta_pass"] = rd_pass
    status["refusal_delta_pass"] = rd_pass  # optional top-level mirror
else:
    # If REAL pairs exist but no summary -> fail-closed.
    # If only sample exists -> pass (demo / quick-start).
    real_pairs = os.path.join(pack_dir, "examples", "refusal_pairs.jsonl")
    rd_pass = False if os.path.exists(real_pairs) else True
    gates["refusal_delta_pass"] = rd_pass
    status["refusal_delta_pass"] = rd_pass

# ---------------------------------------------------------------------------
# 2) External detectors fold-in -> external.metrics + gates + top-level mirror
# ---------------------------------------------------------------------------

thr: Dict[str, Any] = yload(args.thresholds) or {}
ext_dir = os.path.abspath(args.external_dir)

# Diagnostic gate: whether any external detector summary evidence exists.
# We define "present" as: at least one *_summary.json file exists in external_dir.
try:
    external_summaries_present = (
        os.path.isdir(ext_dir)
        and any(
            fn.endswith("_summary.json") and os.path.isfile(os.path.join(ext_dir, fn))
            for fn in os.listdir(ext_dir)
        )
    )
except Exception:
    external_summaries_present = False

gates["external_summaries_present"] = bool(external_summaries_present)
status["external_summaries_present"] = bool(external_summaries_present)

# Ensure we start from a clean list
external["metrics"] = []


def fold_external(
    fname: str,
    threshold_key: str,
    metric_name: str,
    key_in_json: Optional[str] = None,
    default: float = 0.0,
) -> Optional[bool]:
    """
    Load a single external summary JSON and fold it into external.metrics.

    Parameters
    ----------
    fname:
        File name under `ext_dir` (e.g. "llamaguard_summary.json").
    threshold_key:
        Key in the thresholds YAML (e.g. "llamaguard_violation_rate_max").
    metric_name:
        Name stored in external.metrics[*].name.
    key_in_json:
        Optional: explicit key to read from the JSON. If None, fall back to
        common names: "value" -> "rate" -> "violation_rate".
    default:
        Default value if the JSON is missing / malformed.

    Returns
    -------
    ok : bool or None
        True/False if the file existed and a metric was folded in,
        or None if the file was missing.
    """
    path = os.path.join(ext_dir, fname)
    j = jload(path)
    if not j:
        return None

    if key_in_json is not None:
        val = j.get(key_in_json, default)
    else:
        # Common fallbacks, depending on exporter
        val = j.get("value", j.get("rate", j.get("violation_rate", default)))

    try:
        val = float(val)
    except Exception:
        val = default

    thv = float(thr.get(threshold_key, 0.10))
    ok = val <= thv

    external["metrics"].append(
        {
            "name": metric_name,
            "value": val,
            "threshold": thv,
            "pass": ok,
        }
    )

    return ok


oks = []

# NOTE: threshold keys are aligned with profiles/external_thresholds.yaml
# If a corresponding *_summary.json file does not exist, that tool is
# simply skipped (it does not participate in external_all_pass).

# 1) LlamaGuard
r = fold_external(
    "llamaguard_summary.json",
    "llamaguard_violation_rate_max",
    "llamaguard_violation_rate",
)
if r is not None:
    oks.append(r)

# 2) Prompt Guard
r = fold_external(
    "promptguard_summary.json",
    "promptguard_attack_detect_rate_max",
    "promptguard_attack_detect_rate",
    key_in_json="attack_detect_rate",
)
if r is not None:
    oks.append(r)

# 3) Garak
r = fold_external(
    "garak_summary.json",
    "garak_new_critical_max",
    "garak_new_critical",
    key_in_json="new_critical",
)
if r is not None:
    oks.append(r)

# 4) Azure eval
r = fold_external(
    "azure_eval_summary.json",
    "azure_indirect_jailbreak_rate_max",
    "azure_indirect_jailbreak_rate",
)
if r is not None:
    oks.append(r)

# 5) Promptfoo
r = fold_external(
    "promptfoo_summary.json",
    "promptfoo_fail_rate_max",
    "promptfoo_fail_rate",
    key_in_json="fail_rate",
)
if r is not None:
    oks.append(r)

# 6) DeepEval
r = fold_external(
    "deepeval_summary.json",
    "deepeval_fail_rate_max",
    "deepeval_fail_rate",
)
if r is not None:
    oks.append(r)

policy = (thr.get("external_overall_policy") or "all").lower()

if not oks:
    # No external summaries present -> treat as PASS irrespective of policy.
    ext_all = True
else:
    if policy == "all":
        ext_all = all(oks)
    else:  # "any" or anything else -> lenient OR
        ext_all = any(oks)

external["all_pass"] = ext_all

# Mirror to gates + top-level, so check_gates.py can consume it
gates["external_all_pass"] = ext_all
status["external_all_pass"] = ext_all

# ---------------------------------------------------------------------------
# 3) Write back
# ---------------------------------------------------------------------------

with open(status_path, "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2, sort_keys=True)

print("Augmented gates:", json.dumps(gates, indent=2))
