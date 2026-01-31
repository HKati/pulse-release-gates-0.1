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
import glob
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
            obj = json.load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def jload_json_or_jsonl(path: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort loader for either:
      - JSON file containing a single object, or
      - JSONL file where each non-empty line is a JSON object.

    Returns the last successfully parsed object (common pattern for JSONL),
    or None on failure.
    """
    try:
        if path.lower().endswith(".jsonl"):
            last: Optional[Dict[str, Any]] = None
            with open(path, encoding="utf-8") as f:
                for raw in f:
                    ln = raw.strip()
                    if not ln:
                        continue
                    obj = json.loads(ln)
                    if isinstance(obj, dict):
                        last = obj
            return last
        return jload(path)
    except Exception:
        return None


def yload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort YAML loader: returns None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = yaml.safe_load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def coerce_float(x: Any, default: float) -> float:
    """Coerce a value to float, with defensive handling for dict/list wrappers."""
    if x is None:
        return default

    if isinstance(x, (int, float)):
        return float(x)

    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return default

    # Some adapters may emit dicts (e.g., {"failure_rates": {...}} or {"k": 0.1})
    if isinstance(x, dict):
        if len(x) == 1:
            only = next(iter(x.values()))
            return coerce_float(only, default)
        return default

    if isinstance(x, list) and len(x) == 1:
        return coerce_float(x[0], default)

    return default


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
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
        help="Directory containing *_summary.(json|jsonl) files from external tools",
    )
    args = parser.parse_args()

    status_path = os.path.abspath(args.status)

    # -----------------------------------------------------------------------
    # 0) Load base status (written by run_all.py)
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 1) Refusal-delta summary -> metrics + gates + top-level mirror
    # -----------------------------------------------------------------------
    pack_dir = os.path.dirname(os.path.dirname(status_path))  # .../PULSE_safe_pack_v0
    artifacts_dir = os.path.join(pack_dir, "artifacts")
    rd_path = os.path.join(artifacts_dir, "refusal_delta_summary.json")

    rd = jload(rd_path)

    if rd is not None:
        metrics["refusal_delta_n"] = rd.get("n", 0)
        metrics["refusal_delta"] = rd.get("delta", 0.0)
        metrics["refusal_delta_ci_low"] = rd.get("ci_low", 0.0)
        metrics["refusal_delta_ci_high"] = rd.get("ci_high", 0.0)

        metrics["refusal_policy"] = rd.get("policy", "balanced")
        metrics["refusal_delta_min"] = rd.get("delta_min", 0.10)
        metrics["refusal_delta_strict"] = rd.get("delta_strict", 0.10)

        metrics["refusal_p_mcnemar"] = rd.get("p_mcnemar")
        metrics["refusal_pass_min"] = bool(rd.get("pass_min", False))
        metrics["refusal_pass_strict"] = bool(rd.get("pass_strict", False))

        rd_pass = bool(rd.get("pass", False))
        gates["refusal_delta_pass"] = rd_pass
        status["refusal_delta_pass"] = rd_pass
    else:
        real_pairs = os.path.join(pack_dir, "examples", "refusal_pairs.jsonl")
        rd_pass = False if os.path.exists(real_pairs) else True
        gates["refusal_delta_pass"] = rd_pass
        status["refusal_delta_pass"] = rd_pass

    # -----------------------------------------------------------------------
    # 2) External detectors fold-in -> external.metrics + gates + top-level mirror
    # -----------------------------------------------------------------------
    thr: Dict[str, Any] = yload(args.thresholds) or {}
    ext_dir = os.path.abspath(args.external_dir)

    external["metrics"] = []

    summary_files: list[str] = []
    if os.path.isdir(ext_dir):
        summary_files = sorted(glob.glob(os.path.join(ext_dir, "*_summary.json")))
        summary_files += sorted(glob.glob(os.path.join(ext_dir, "*_summary.jsonl")))

    summaries_present = bool(summary_files)

    external["summaries_present"] = summaries_present
    external["summary_count"] = len(summary_files)

    gates["external_summaries_present"] = summaries_present
    status["external_summaries_present"] = summaries_present

    def fold_external(
        fname: str,
        threshold_key: str,
        metric_name: str,
        key_in_json: Optional[str] = None,
        default: float = 0.0,
        fallback_keys: Optional[list[str]] = None,
    ) -> Optional[bool]:
        """
        Load a single external summary JSON/JSONL and fold it into external.metrics.

        Returns True/False if file exists and a metric was folded in,
        or None if file is missing (skipped).
        """
        path = os.path.join(ext_dir, fname)
        if not os.path.exists(path):
            if fname.lower().endswith(".json"):
                alt = os.path.join(ext_dir, fname[:-5] + ".jsonl")
                if os.path.exists(alt):
                    path = alt
                else:
                    return None
            else:
                return None

        j = jload_json_or_jsonl(path)
        thv = float(thr.get(threshold_key, 0.10))

        if j is None or not isinstance(j, dict):
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": thv,
                    "pass": False,
                    "parse_error": True,
                }
            )
            return False

        # Prefer explicit key if present, but DO NOT disable fallback lookups.
        raw_val: Any = None
        found = False

        if key_in_json is not None and key_in_json in j:
            raw_val = j.get(key_in_json)
            found = True
        else:
            keys = [
                "value",
                "rate",
                "violation_rate",
                "attack_detect_rate",
                "fail_rate",
                "new_critical",
            ]
            if fallback_keys:
                keys.extend(list(fallback_keys))

            for k in keys:
                if k in j:
                    raw_val = j.get(k)
                    found = True
                    break

            # Azure-style structured output: failure_rates is a dict of per-category/per-metric rates.
            # If present, prefer exact match (key_in_json, then metric_name), else conservative max numeric.
            fr = j.get("failure_rates")
            if (not found) and isinstance(fr, dict):
                if key_in_json and key_in_json in fr:
                    raw_val = fr.get(key_in_json)
                    found = True
                elif metric_name in fr:
                    raw_val = fr.get(metric_name)
                    found = True
                else:
                    nums = [float(v) for v in fr.values() if isinstance(v, (int, float))]
                    if nums:
                        raw_val = max(nums)
                        found = True

        if not found:
            # Fail-closed: metric key missing, do not silently default to 0.0 and pass.
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": thv,
                    "pass": False,
                    "parse_error": True,
                    "missing_metric_key": True,
                    "expected_key": key_in_json,
                }
            )
            return False

        val = coerce_float(raw_val, default)

        # If we "found" a field but couldn't coerce to float, treat as parse error (fail-closed).
        # (Avoids accidental pass when raw_val is non-numeric.)
        if val == default and not (
            isinstance(raw_val, (int, float)) and float(raw_val) == float(default)
        ):
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": thv,
                    "pass": False,
                    "parse_error": True,
                    "bad_metric_value": True,
                    "expected_key": key_in_json,
                }
            )
            return False

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

    oks: list[bool] = []

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
        key_in_json="azure_indirect_jailbreak_rate",
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
        key_in_json="fail_rate",
    )
    if r is not None:
        oks.append(r)

    policy = (thr.get("external_overall_policy") or "all").lower()

    if not oks:
        ext_all = True
    else:
        if policy == "all":
            ext_all = all(oks)
        else:
            ext_all = any(oks)

    external["all_pass"] = ext_all
    gates["external_all_pass"] = ext_all
    status["external_all_pass"] = ext_all

    # -----------------------------------------------------------------------
    # 3) Write back
    # -----------------------------------------------------------------------
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, sort_keys=True)

    print("Augmented gates:", json.dumps(gates, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
