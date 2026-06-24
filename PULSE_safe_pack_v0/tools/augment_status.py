#!/usr/bin/env python3
"""Augment baseline status.json with derived evidence summaries.

The tool folds refusal-delta and external-detector evidence into status.json.
It remains a materialization helper, not a second release-decision engine.
Release authority remains declared-policy enforcement over materialized state.

External summaries may use either:

- legacy top-level metric keys, or
- canonical external_summary_v1 metrics[] entries.

When --require_external_summaries is enabled, absence of a successfully folded
canonical detector summary makes external_all_pass fail closed.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
from typing import Any, Dict, Optional

import yaml


CANONICAL_EXTERNAL_SUMMARY_FILENAMES = (
    "llamaguard_summary.json",
    "llamaguard_summary.jsonl",
    "promptguard_summary.json",
    "promptguard_summary.jsonl",
    "garak_summary.json",
    "garak_summary.jsonl",
    "azure_eval_summary.json",
    "azure_eval_summary.jsonl",
    "promptfoo_summary.json",
    "promptfoo_summary.jsonl",
    "deepeval_summary.json",
    "deepeval_summary.jsonl",
)


# ---------------------------------------------------------------------------
# Loaders and scalar helpers
# ---------------------------------------------------------------------------


def jload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON loader: return a dict or None."""

    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)

        return value if isinstance(value, dict) else None

    except Exception:
        return None


def jload_with_raw_bytes(
    path: str,
) -> tuple[Optional[Dict[str, Any]], Optional[bytes]]:
    """Best-effort JSON loader preserving the source bytes."""

    try:
        raw = open(path, "rb").read()
        value = json.loads(raw)

        return (
            (value, raw)
            if isinstance(value, dict)
            else (None, None)
        )

    except Exception:
        return None, None


def jload_json_or_jsonl(
    path: str,
) -> Optional[Dict[str, Any]]:
    """Load one JSON object or the last non-empty JSONL object."""

    try:
        if path.lower().endswith(".jsonl"):
            last: Optional[Dict[str, Any]] = None

            with open(path, encoding="utf-8") as handle:
                for raw in handle:
                    text = raw.strip()

                    if not text:
                        continue

                    value = json.loads(text)

                    if isinstance(value, dict):
                        last = value

            return last

        return jload(path)

    except Exception:
        return None


def yload(path: str) -> Optional[Dict[str, Any]]:
    """Best-effort YAML loader: return a mapping or None."""

    try:
        with open(path, encoding="utf-8") as handle:
            value = yaml.safe_load(handle)

        return value if isinstance(value, dict) else None

    except Exception:
        return None


def coerce_float_strict(
    value: Any,
    default: float,
) -> tuple[float, bool]:
    """Coerce one scalar to a finite float."""

    if value is None or isinstance(value, bool):
        return default, False

    if isinstance(value, (int, float)):
        result = float(value)
        return (
            (result, True)
            if math.isfinite(result)
            else (default, False)
        )

    if isinstance(value, str):
        try:
            result = float(value.strip())
        except Exception:
            return default, False

        return (
            (result, True)
            if math.isfinite(result)
            else (default, False)
        )

    if isinstance(value, dict) and len(value) == 1:
        return coerce_float_strict(
            next(iter(value.values())),
            default,
        )

    if isinstance(value, list) and len(value) == 1:
        return coerce_float_strict(
            value[0],
            default,
        )

    return default, False


# ---------------------------------------------------------------------------
# Q1 reader-only shadow projection
# ---------------------------------------------------------------------------


def ensure_meta(
    status: Dict[str, Any],
) -> Dict[str, Any]:
    """Ensure a mapping-valued meta block and return it."""

    meta = status.get("meta")

    if isinstance(meta, dict):
        return meta

    status["meta"] = {}
    return status["meta"]


def extract_q1_n_eligible(
    q1: Dict[str, Any],
) -> tuple[Optional[Any], bool]:
    """Return the supported Q1 eligible-count source."""

    if "n_eligible" in q1:
        return q1["n_eligible"], True

    if "n" in q1:
        return q1["n"], True

    counts = q1.get("counts")

    if (
        isinstance(counts, dict)
        and "n_eligible" in counts
    ):
        return counts["n_eligible"], True

    return None, False


def build_q1_reference_shadow_block(
    q1: Dict[str, Any],
    *,
    abs_path: str,
    raw: bytes,
) -> Optional[Dict[str, Any]]:
    """Build the non-authorizing Q1 reference shadow block."""

    required_fields = (
        "pass",
        "grounded_rate",
        "wilson_lower_bound",
        "threshold",
    )

    if any(
        field not in q1
        for field in required_fields
    ):
        return None

    n_eligible, found_n = extract_q1_n_eligible(q1)

    if not found_n:
        return None

    return {
        "pass": q1["pass"],
        "grounded_rate": q1["grounded_rate"],
        "wilson_lower_bound": q1[
            "wilson_lower_bound"
        ],
        "n_eligible": n_eligible,
        "threshold": q1["threshold"],
        "summary_artifact": {
            "path": abs_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }


def fold_q1_reference_shadow(
    status: Dict[str, Any],
    summary_path: Optional[str],
) -> None:
    """Optionally project Q1 summary state without changing gates."""

    if summary_path is None:
        return

    existing_meta = status.get("meta")

    if isinstance(existing_meta, dict):
        existing_meta.pop(
            "q1_reference_shadow",
            None,
        )

    abs_path = os.path.abspath(summary_path)
    q1, raw = jload_with_raw_bytes(abs_path)

    if q1 is None or raw is None:
        return

    shadow = build_q1_reference_shadow_block(
        q1,
        abs_path=abs_path,
        raw=raw,
    )

    if shadow is None:
        return

    ensure_meta(status)[
        "q1_reference_shadow"
    ] = shadow


# ---------------------------------------------------------------------------
# External-summary discovery and canonical metric reading
# ---------------------------------------------------------------------------


def list_external_summary_files(
    external_dir: str,
) -> list[str]:
    if not os.path.isdir(external_dir):
        return []

    files = sorted(
        glob.glob(
            os.path.join(
                external_dir,
                "*_summary.json",
            )
        )
    )
    files += sorted(
        glob.glob(
            os.path.join(
                external_dir,
                "*_summary.jsonl",
            )
        )
    )

    return sorted(files)


def list_canonical_external_summary_files(
    external_dir: str,
) -> list[str]:
    if not os.path.isdir(external_dir):
        return []

    result: list[str] = []

    for filename in CANONICAL_EXTERNAL_SUMMARY_FILENAMES:
        path = os.path.join(
            external_dir,
            filename,
        )

        if os.path.exists(path):
            result.append(path)

    return sorted(result)


def extract_external_summary_v1_metric(
    summary: Dict[str, Any],
    *,
    metric_name: str,
    threshold_key: str,
    canonical_threshold: float,
) -> tuple[
    bool,
    Any,
    Optional[bool],
    Optional[str],
]:
    """Read one exact metric from external_summary_v1.

    Returns:

        is_canonical_summary,
        metric_value,
        declared_pass,
        error
    """

    if (
        summary.get("schema_version")
        != "external_summary_v1"
    ):
        return False, None, None, None

    metrics = summary.get("metrics")

    if not isinstance(metrics, list):
        return (
            True,
            None,
            None,
            "metrics must be an array",
        )

    matches = [
        item
        for item in metrics
        if (
            isinstance(item, dict)
            and item.get("key") == metric_name
        )
    ]

    if len(matches) != 1:
        return (
            True,
            None,
            None,
            (
                "canonical metric must occur "
                "exactly once"
            ),
        )

    metric = matches[0]

    if "value" not in metric:
        return (
            True,
            None,
            None,
            "canonical metric value is missing",
        )

    metric_passed = metric.get("passed")

    if not isinstance(metric_passed, bool):
        return (
            True,
            None,
            None,
            (
                "canonical metric passed state "
                "must be boolean"
            ),
        )

    result = summary.get("result")

    if (
        not isinstance(result, dict)
        or not isinstance(
            result.get("passed"),
            bool,
        )
    ):
        return (
            True,
            None,
            None,
            (
                "canonical aggregate passed state "
                "must be boolean"
            ),
        )

    threshold_ref = summary.get("threshold_ref")

    if (
        not isinstance(threshold_ref, dict)
        or threshold_ref.get("key")
        != threshold_key
    ):
        return (
            True,
            None,
            None,
            "canonical threshold reference mismatch",
        )

    declared_threshold = metric.get("threshold")
    threshold_value, threshold_ok = (
        coerce_float_strict(
            declared_threshold,
            canonical_threshold,
        )
    )

    if (
        not threshold_ok
        or threshold_value != canonical_threshold
    ):
        return (
            True,
            None,
            None,
            "canonical metric threshold mismatch",
        )

    if metric.get("comparator") != "lte":
        return (
            True,
            None,
            None,
            "canonical metric comparator must be 'lte'",
        )

    return (
        True,
        metric["value"],
        (
            metric_passed
            and result["passed"]
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Main materialization
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--status",
        required=True,
        help="Path to baseline status.json",
    )
    parser.add_argument(
        "--thresholds",
        required=True,
        help=(
            "YAML file with external detector "
            "thresholds"
        ),
    )
    parser.add_argument(
        "--external_dir",
        required=True,
        help=(
            "Directory containing canonical external "
            "summary JSON or JSONL files"
        ),
    )
    parser.add_argument(
        "--require_external_summaries",
        action="store_true",
        help=(
            "Fail closed when no external summary "
            "is successfully folded"
        ),
    )
    parser.add_argument(
        "--q1-reference-summary",
        "--q1_reference_summary",
        dest="q1_reference_summary",
        help=(
            "Optional Q1 reference summary projected "
            "into meta.q1_reference_shadow"
        ),
    )

    args = parser.parse_args()
    status_path = os.path.abspath(args.status)

    status: Dict[str, Any] = jload(status_path) or {}

    gates = status.get("gates")
    if not isinstance(gates, dict):
        gates = {}
        status["gates"] = gates

    metrics = status.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        status["metrics"] = metrics

    external = status.get("external")
    if not isinstance(external, dict):
        external = {}
        status["external"] = external

    external["metrics"] = []

    # Refusal-delta summary belongs to the pack that owns status.json.
    artifacts_dir = os.path.dirname(status_path)
    pack_dir = os.path.dirname(artifacts_dir)
    refusal_path = os.path.join(
        artifacts_dir,
        "refusal_delta_summary.json",
    )

    refusal = jload(refusal_path)
    refusal_delta_evidence_present = False

    if refusal is not None:
        try:
            refusal_n = int(
                refusal.get("n", 0) or 0
            )
        except (TypeError, ValueError):
            refusal_n = 0

        refusal_delta_evidence_present = (
            refusal_n > 0
        )

        metrics["refusal_delta_n"] = refusal_n
        metrics["refusal_delta"] = refusal.get(
            "delta",
            0.0,
        )
        metrics["refusal_delta_ci_low"] = refusal.get(
            "ci_low",
            0.0,
        )
        metrics["refusal_delta_ci_high"] = refusal.get(
            "ci_high",
            0.0,
        )
        metrics["refusal_policy"] = refusal.get(
            "policy",
            "balanced",
        )
        metrics["refusal_delta_min"] = refusal.get(
            "delta_min",
            0.10,
        )
        metrics["refusal_delta_strict"] = refusal.get(
            "delta_strict",
            0.10,
        )
        metrics["refusal_p_mcnemar"] = refusal.get(
            "p_mcnemar"
        )
        metrics["refusal_pass_min"] = bool(
            refusal.get("pass_min", False)
        )
        metrics["refusal_pass_strict"] = bool(
            refusal.get("pass_strict", False)
        )

        refusal_pass = bool(
            refusal.get("pass", False)
        )

    else:
        real_pairs = os.path.join(
            pack_dir,
            "examples",
            "refusal_pairs.jsonl",
        )
        refusal_pass = not os.path.exists(
            real_pairs
        )

    gates["refusal_delta_pass"] = refusal_pass
    status["refusal_delta_pass"] = refusal_pass
    gates["refusal_delta_evidence_present"] = bool(
        refusal_delta_evidence_present
    )
    status["refusal_delta_evidence_present"] = bool(
        refusal_delta_evidence_present
    )

    thresholds: Dict[str, Any] = yload(
        args.thresholds
    ) or {}
    external_dir = os.path.abspath(
        args.external_dir
    )

    summary_files = list_external_summary_files(
        external_dir
    )
    canonical_summary_files = (
        list_canonical_external_summary_files(
            external_dir
        )
    )

    summary_file_set = set(summary_files)
    canonical_summary_file_set = set(
        canonical_summary_files
    )
    unrecognized_summary_files = sorted(
        summary_file_set
        - canonical_summary_file_set
    )

    summaries_present = bool(
        canonical_summary_files
    )

    external["summaries_present"] = summaries_present
    external["summary_count"] = len(summary_files)
    external["canonical_summary_count"] = len(
        canonical_summary_files
    )
    external["unrecognized_summary_count"] = len(
        unrecognized_summary_files
    )
    external["unrecognized_summaries"] = [
        os.path.basename(path)
        for path in unrecognized_summary_files
    ]

    gates["external_summaries_present"] = (
        summaries_present
    )
    status["external_summaries_present"] = (
        summaries_present
    )

    def fold_external(
        filename: str,
        threshold_key: str,
        metric_name: str,
        key_in_json: Optional[str] = None,
        default: float = 0.0,
        fallback_keys: Optional[list[str]] = None,
    ) -> Optional[bool]:
        """Fold a legacy or canonical external-summary metric."""

        path = os.path.join(
            external_dir,
            filename,
        )

        if not os.path.exists(path):
            if filename.lower().endswith(".json"):
                alternative = os.path.join(
                    external_dir,
                    filename[:-5] + ".jsonl",
                )

                if os.path.exists(alternative):
                    path = alternative
                else:
                    return None
            else:
                return None

        summary = jload_json_or_jsonl(path)

        try:
            canonical_threshold = float(
                thresholds.get(
                    threshold_key,
                    0.10,
                )
            )
        except (TypeError, ValueError):
            canonical_threshold = float("nan")

        if not math.isfinite(canonical_threshold):
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": canonical_threshold,
                    "pass": False,
                    "parse_error": True,
                    "bad_threshold_value": True,
                }
            )
            return False

        if summary is None:
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": canonical_threshold,
                    "pass": False,
                    "parse_error": True,
                }
            )
            return False

        raw_value: Any = None
        found = False
        canonical_declared_pass: Optional[bool] = None

        (
            is_canonical,
            canonical_value,
            canonical_declared_pass,
            canonical_error,
        ) = extract_external_summary_v1_metric(
            summary,
            metric_name=metric_name,
            threshold_key=threshold_key,
            canonical_threshold=canonical_threshold,
        )

        if is_canonical:
            if canonical_error is not None:
                external["metrics"].append(
                    {
                        "name": metric_name,
                        "value": default,
                        "threshold": canonical_threshold,
                        "pass": False,
                        "parse_error": True,
                        "canonical_metric_error": (
                            canonical_error
                        ),
                    }
                )
                return False

            raw_value = canonical_value
            found = True

        # Legacy and third-party compatibility path.
        if (
            not found
            and key_in_json is not None
            and key_in_json in summary
        ):
            raw_value = summary.get(key_in_json)
            found = True

        keys = [
            "value",
            "rate",
            "violation_rate",
            "attack_detect_rate",
            "fail_rate",
            "new_critical",
        ]

        if fallback_keys:
            keys.extend(fallback_keys)

        if not found:
            for key in keys:
                if key in summary:
                    raw_value = summary.get(key)
                    found = True
                    break

        failure_rates = summary.get(
            "failure_rates"
        )

        if (
            not found
            and isinstance(failure_rates, dict)
        ):
            if (
                key_in_json
                and key_in_json in failure_rates
            ):
                raw_value = failure_rates.get(
                    key_in_json
                )
                found = True

            elif metric_name in failure_rates:
                raw_value = failure_rates.get(
                    metric_name
                )
                found = True

            else:
                numeric_values = [
                    value
                    for value in failure_rates.values()
                    if (
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(float(value))
                    )
                ]

                if numeric_values:
                    raw_value = max(numeric_values)
                    found = True

        if not found:
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": canonical_threshold,
                    "pass": False,
                    "parse_error": True,
                    "missing_metric_key": True,
                    "expected_key": key_in_json,
                }
            )
            return False

        value, numeric_ok = coerce_float_strict(
            raw_value,
            default,
        )

        if not numeric_ok:
            external["metrics"].append(
                {
                    "name": metric_name,
                    "value": default,
                    "threshold": canonical_threshold,
                    "pass": False,
                    "parse_error": True,
                    "bad_metric_value": True,
                    "expected_key": key_in_json,
                }
            )
            return False

        passed = value <= canonical_threshold

        if canonical_declared_pass is not None:
            passed = (
                passed
                and canonical_declared_pass
            )

        external["metrics"].append(
            {
                "name": metric_name,
                "value": value,
                "threshold": canonical_threshold,
                "pass": passed,
            }
        )

        return passed

    folded_results: list[bool] = []

    detector_specs = (
        (
            "llamaguard_summary.json",
            "llamaguard_violation_rate_max",
            "llamaguard_violation_rate",
            None,
        ),
        (
            "promptguard_summary.json",
            "promptguard_attack_detect_rate_max",
            "promptguard_attack_detect_rate",
            "attack_detect_rate",
        ),
        (
            "garak_summary.json",
            "garak_new_critical_max",
            "garak_new_critical",
            "new_critical",
        ),
        (
            "azure_eval_summary.json",
            "azure_indirect_jailbreak_rate_max",
            "azure_indirect_jailbreak_rate",
            "azure_indirect_jailbreak_rate",
        ),
        (
            "promptfoo_summary.json",
            "promptfoo_fail_rate_max",
            "promptfoo_fail_rate",
            "fail_rate",
        ),
        (
            "deepeval_summary.json",
            "deepeval_fail_rate_max",
            "deepeval_fail_rate",
            "fail_rate",
        ),
    )

    for (
        filename,
        threshold_key,
        metric_name,
        preferred_key,
    ) in detector_specs:
        result = fold_external(
            filename,
            threshold_key,
            metric_name,
            key_in_json=preferred_key,
        )

        if result is not None:
            folded_results.append(result)

    policy = str(
        thresholds.get(
            "external_overall_policy",
            "all",
        )
        or "all"
    ).lower()

    if not folded_results:
        external_all_pass = (
            False
            if args.require_external_summaries
            else True
        )

    elif policy == "all":
        external_all_pass = all(
            folded_results
        )

    else:
        external_all_pass = any(
            folded_results
        )

    external["all_pass"] = external_all_pass
    gates["external_all_pass"] = external_all_pass
    status["external_all_pass"] = external_all_pass

    fold_q1_reference_shadow(
        status,
        args.q1_reference_summary,
    )

    with open(
        status_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            status,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")

    print(
        "Augmented gates:",
        json.dumps(
            gates,
            indent=2,
            sort_keys=True,
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
