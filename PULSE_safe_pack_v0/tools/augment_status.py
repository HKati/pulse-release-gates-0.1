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

Optional strict mode:
- when --require_external_summaries is enabled, missing external summaries
  make external_all_pass fail closed
- default behavior remains onboarding-friendly unless that flag is used
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from typing import Any, Dict, Optional

import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON loader: returns dict or None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def jload_with_raw_bytes(path: str) -> tuple[Optional[Dict[str, Any]], Optional[bytes]]:
    """Best-effort JSON loader returning (dict, raw_bytes) or (None, None) on failure."""
    try:
        raw = open(path, "rb").read()
        obj = json.loads(raw)
        return (obj, raw) if isinstance(obj, dict) else (None, None)
    except Exception:
        return None, None


def jload_json_or_jsonl(path: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort loader for either:
      - JSON file containing a single object, or
      - JSONL file where each non-empty line is a JSON object.

    Returns the last successfully parsed dict (common JSONL pattern),
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
    """Best-effort YAML loader: returns dict or None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = yaml.safe_load(f)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def coerce_float_strict(x: Any, default: float) -> tuple[float, bool]:
    """
    Coerce a value to float.
    Returns (value, ok). ok=False means "present but not parseable".

    Supports simple wrappers (single-value dict/list), which sometimes appear in adapters.
    """
    if x is None:
        return default, False

    if isinstance(x, (int, float)):
        return float(x), True

    if isinstance(x, str):
        try:
            return float(x.strip()), True
        except Exception:
            return default, False

    if isinstance(x, dict):
        # allow a single-value dict wrapper
        if len(x) == 1:
            only = next(iter(x.values()))
            return coerce_float_strict(only, default)
        return default, False

    if isinstance(x, list):
        # allow a single-value list wrapper
        if len(x) == 1:
            return coerce_float_strict(x[0], default)
        return default, False

    return default, False


def ensure_meta(status: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure status has a dict-valued meta block and return it."""
    meta = status.get("meta")
    if isinstance(meta, dict):
        return meta
    status["meta"] = {}
    return status["meta"]


def extract_q1_n_eligible(q1: Dict[str, Any]) -> tuple[Optional[Any], bool]:
    """
    Extract the eligible-count source for q1_reference_shadow.n_eligible.

    Accepted source shapes:
    - top-level n_eligible
    - canonical top-level n
    - nested counts.n_eligible

    Returns (value, found).
    """
    if "n_eligible" in q1:
        return q1["n_eligible"], True

    if "n" in q1:
        return q1["n"], True

    counts = q1.get("counts")
    if isinstance(counts, dict) and "n_eligible" in counts:
        return counts["n_eligible"], True

    return None, False


def build_q1_reference_shadow_block(
    q1: Dict[str, Any],
    *,
    abs_path: str,
    raw: bytes,
) -> Optional[Dict[str, Any]]:
    """
    Build the q1_reference_shadow block from a valid source summary.

    Required source fields:
    - pass
    - grounded_rate
    - wilson_lower_bound
    - threshold
    - eligible-count source: n_eligible OR canonical n OR counts.n_eligible
    """
    required_fields = (
        "pass",
        "grounded_rate",
        "wilson_lower_bound",
        "threshold",
    )
    if any(field not in q1 for field in required_fields):
        return None

    n_eligible, found_n = extract_q1_n_eligible(q1)
    if not found_n:
        return None

    return {
        "pass": q1["pass"],
        "grounded_rate": q1["grounded_rate"],
        "wilson_lower_bound": q1["wilson_lower_bound"],
        "n_eligible": n_eligible,
        "threshold": q1["threshold"],
        "summary_artifact": {
            "path": abs_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }


def fold_q1_reference_shadow(status: Dict[str, Any], summary_path: Optional[str]) -> None:
    """
    Optionally fold a valid Q1 reference summary into status["meta"]["q1_reference_shadow"].

    Behavior:
    - if summary_path is None: no-op
    - if explicitly provided but invalid / missing / incomplete: omit the block
    - if valid and complete: copy / map fields without recomputation
    """
    if summary_path is None:
        return

    existing_meta = status.get("meta")
    if isinstance(existing_meta, dict):
        existing_meta.pop("q1_reference_shadow", None)

    abs_path = os.path.abspath(summary_path)
    q1, raw = jload_with_raw_bytes(abs_path)
    if q1 is None or raw is None:
        return

    shadow = build_q1_reference_shadow_block(q1, abs_path=abs_path, raw=raw)
    if shadow is None:
        return

    meta = ensure_meta(status)
    meta["q1_reference_shadow"] = shadow


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
    parser.add_argument(
        "--require_external_summaries",
        action="store_true",
        help=(
            "Fail-closed when no external summary files are present. "
            "Default behavior remains permissive for onboarding unless this flag is set."
        ),
    )
    parser.add_argument(
    "--q1-reference-summary",
    "--q1_reference_summary",
    dest="q1_reference_summary",
    help=(
        "Optional Q1 reference summary JSON artefact to fold into "
        'status["meta"]["q1_reference_shadow"]'
    ),
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
        {"metrics": [], "all_pass": True},
    )

    # -----------------------------------------------------------------------
    # 1) Refusal-delta summary -> metrics + gates + top-level mirror
    # -----------------------------------------------------------------------
    # Pack dir: stable (script location), not derived from status path
    pack_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../PULSE_safe_pack_v0

    # Artifacts dir: derive from the baseline status.json location
    artifacts_dir = os.path.dirname(status_path)

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
        # If REAL pairs exist but no summary -> fail-closed.
        # If only sample exists -> pass (demo / quick-start).
        real_pairs = os.path.join(pack_dir, "examples", "refusal_pairs.jsonl")
        rd_pass = False if os.path.exists(real_pairs) else True
        gates["refusal_delta_pass"] = rd_pass
        status["refusal_delta_pass"] = rd_pass

    # -----------------------------------------------------------------------
    # 2) External detectors fold-in -> external.metrics + gates + top-level mirror
    # -----------------------------------------------------------------------
    thr: Dict[str, Any] = yload(args.thresholds) or {}
    ext_dir = os.path.abspath(args.external_dir)

    # Ensure we start from a clean list
    external["metrics"] = []

    summary_files: list[str] = []
    if os.path.isdir(ext_dir):
        summary_files = sorted(glob.glob(os.path.join(ext_dir, "*_summary.json")))
        summary_files += sorted(glob.glob(os.path.join(ext_dir, "*_summary.jsonl")))

    summaries_present = bool(summary_files)
    external["summaries_present"] = summaries_present
    external["summary_count"] = len(summary_files)

    # Diagnostic gate (normative only if policy promotes it)
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

        Policy:
        - Prefer key_in_json when present
        - BUT: do NOT disable fallback if key_in_json is missing
        - If no usable metric exists -> parse_error + fail-closed
        """
        path = os.path.join(ext_dir, fname)

        # allow .json -> .jsonl fallback when caller uses .json
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

        raw_val: Any = None
        found = False

        # 1) Prefer explicit key if present
        if key_in_json is not None and key_in_json in j:
            raw_val = j.get(key_in_json)
            found = True

        # 2) Fallback keys (covers older + third-party summaries)
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

        if not found:
            for k in keys:
                if k in j:
                    raw_val = j.get(k)
                    found = True
                    break

        # 3) Nested dict fallback: failure_rates (Azure-style)
        #    Prefer exact match first, else conservative max numeric.
        if (not found) and isinstance(j.get("failure_rates"), dict):
            fr = j["failure_rates"]

            if key_in_json and key_in_json in fr:
                raw_val = fr.get(key_in_json)
                found = True
            elif metric_name in fr:
                raw_val = fr.get(metric_name)
                found = True
            else:
                nums = [v for v in fr.values() if isinstance(v, (int, float))]
                if nums:
                    raw_val = max(nums)
                    found = True

        # 4) If still nothing -> fail-closed
        if not found:
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

        val, ok_num = coerce_float_strict(raw_val, default)
        if not ok_num:
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

    # 4) Azure eval (prefer canonical key, but keep fallbacks when missing)
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
        # Default/onboarding: no folded external evidence does not fail the run.
        # Strict/release-grade: fail closed only when summaries are explicitly required
        # and none are present on disk. Filename/metric-key strictness belongs to the
        # dedicated precheck path.
        if args.require_external_summaries and not summaries_present:
            ext_all = False
        else:
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
    # 3) Optional Q1 reference summary shadow fold-in
    # -----------------------------------------------------------------------
    fold_q1_reference_shadow(status, args.q1_reference_summary)

    # -----------------------------------------------------------------------
    # 4) Write back
    # -----------------------------------------------------------------------
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, sort_keys=True)

    print("Augmented gates:", json.dumps(gates, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
