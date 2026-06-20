#!/usr/bin/env python3
"""Build a deterministic Q4 SLO reference summary from archived aggregate stats.

The canonical Q4 contract is read from ``metrics/specs/q4_slo_v0.yml``.
The builder gates on:

- eligible-request count,
- excluded-request fraction,
- p95 latency, and
- mean cost per eligible request.

Optional p95 cost is recorded as a diagnostic only. It never substitutes for
the canonical mean-cost gate.

This tool is artifact-first, deterministic, fail-closed, performs no network
or model calls, and does not create release authority by itself.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Any

import yaml


SPEC_ID = "q4_slo_v0"
SPEC_VERSION = "0.1.0"

INPUT_SPEC_ID = "q4_slo_input_v0"
INPUT_SPEC_VERSION = "0.2.0"

DEFAULT_SPEC_PATH = "metrics/specs/q4_slo_v0.yml"


class UniqueYamlLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(
            key_node,
            deep=deep,
        )

        if key in out:
            raise ValueError(
                f"duplicate YAML key {key!r}"
            )

        out[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return out


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key, value in pairs:
        if key in out:
            raise ValueError(
                f"duplicate JSON key {key!r}"
            )

        out[key] = value

    return out


def _reject_nonfinite_json_constant(
    value: str,
) -> None:
    raise ValueError(
        f"non-finite JSON constant not allowed: "
        f"{value}"
    )


def _created_utc_from_source_date_epoch(
) -> str | None:
    raw = os.getenv(
        "SOURCE_DATE_EPOCH",
        "",
    ).strip()

    if not raw:
        return None

    if not raw.isdigit():
        raise ValueError(
            "SOURCE_DATE_EPOCH must be an "
            "integer Unix timestamp"
        )

    return (
        dt.datetime.fromtimestamp(
            int(raw),
            tz=dt.timezone.utc,
        )
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _resolve_created_utc(
    explicit_created_utc: str,
) -> str:
    value = explicit_created_utc.strip()

    if value:
        return value

    from_sde = (
        _created_utc_from_source_date_epoch()
    )

    if from_sde is not None:
        return from_sde

    raise ValueError(
        "Deterministic output requires "
        "--created_utc or SOURCE_DATE_EPOCH"
    )


def _expect_object(
    name: str,
    value: Any,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be an object"
        )

    return value


def _expect_non_empty_string(
    name: str,
    value: Any,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{name} must be a non-empty string"
        )

    return value.strip()


def _expect_plain_int(
    name: str,
    value: Any,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise ValueError(
            f"{name} must be an integer"
        )

    return value


def _expect_nonnegative_int(
    name: str,
    value: Any,
) -> int:
    result = _expect_plain_int(
        name,
        value,
    )

    if result < 0:
        raise ValueError(
            f"{name} must be >= 0"
        )

    return result


def _expect_positive_int(
    name: str,
    value: Any,
) -> int:
    result = _expect_plain_int(
        name,
        value,
    )

    if result <= 0:
        raise ValueError(
            f"{name} must be > 0"
        )

    return result


def _expect_plain_number(
    name: str,
    value: Any,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{name} must be a number"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite"
        )

    return result


def _expect_nonnegative_number(
    name: str,
    value: Any,
) -> float:
    result = _expect_plain_number(
        name,
        value,
    )

    if result < 0:
        raise ValueError(
            f"{name} must be >= 0"
        )

    return result


def _expect_positive_number(
    name: str,
    value: Any,
) -> float:
    result = _expect_plain_number(
        name,
        value,
    )

    if result <= 0:
        raise ValueError(
            f"{name} must be > 0"
        )

    return result


def _expect_fraction(
    name: str,
    value: Any,
) -> float:
    result = _expect_plain_number(
        name,
        value,
    )

    if result < 0 or result > 1:
        raise ValueError(
            f"{name} must be in [0, 1]"
        )

    return result


def _load_json_object(
    path: Path,
    label: str,
) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8",
            ),
            object_pairs_hook=(
                _unique_json_object
            ),
            parse_constant=(
                _reject_nonfinite_json_constant
            ),
        )

    except OSError as exc:
        raise ValueError(
            f"{label} could not be read: {exc}"
        ) from exc

    except (
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{label} is not valid JSON: {exc}"
        ) from exc

    return _expect_object(
        label,
        payload,
    )


def _load_yaml_object(
    path: Path,
    label: str,
) -> dict[str, Any]:
    try:
        payload = yaml.load(
            path.read_text(
                encoding="utf-8",
            ),
            Loader=UniqueYamlLoader,
        )

    except OSError as exc:
        raise ValueError(
            f"{label} could not be read: {exc}"
        ) from exc

    except (
        yaml.YAMLError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{label} is not valid YAML: {exc}"
        ) from exc

    return _expect_object(
        label,
        payload,
    )


def _repo_relative_or_supplied(
    path: Path,
    supplied: str,
) -> str:
    repo_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    try:
        return (
            path.resolve()
            .relative_to(
                repo_root.resolve()
            )
            .as_posix()
        )

    except ValueError:
        return supplied


def _load_contract(
    spec_path: Path,
) -> tuple[
    float,
    float,
    int,
    float,
]:
    payload = _load_yaml_object(
        spec_path,
        "Q4 metric specification",
    )

    spec = _expect_object(
        "spec",
        payload.get("spec"),
    )

    if spec.get("id") != SPEC_ID:
        raise ValueError(
            "spec.id must be "
            f"{SPEC_ID!r}; "
            f"got {spec.get('id')!r}"
        )

    if (
        str(spec.get("version"))
        != SPEC_VERSION
    ):
        raise ValueError(
            "spec.version must be "
            f"{SPEC_VERSION!r}; "
            f"got {spec.get('version')!r}"
        )

    if (
        spec.get("gate_signal")
        != "q4_slo_ok"
    ):
        raise ValueError(
            "spec.gate_signal must be "
            "literal 'q4_slo_ok'"
        )

    gating = _expect_object(
        "gating",
        payload.get("gating"),
    )

    threshold = _expect_object(
        "gating.threshold",
        gating.get("threshold"),
    )

    evidence = _expect_object(
        "gating.evidence_requirements",
        gating.get(
            "evidence_requirements"
        ),
    )

    min_n = _expect_object(
        (
            "gating.evidence_requirements."
            "min_n_eligible_requests"
        ),
        evidence.get(
            "min_n_eligible_requests"
        ),
    )

    max_excluded = _expect_object(
        (
            "gating.evidence_requirements."
            "max_excluded_fraction"
        ),
        evidence.get(
            "max_excluded_fraction"
        ),
    )

    latency_budget_ms = (
        _expect_positive_number(
            (
                "gating.threshold."
                "latency_p95_ms"
            ),
            threshold.get(
                "latency_p95_ms"
            ),
        )
    )

    cost_mean_budget = (
        _expect_positive_number(
            (
                "gating.threshold."
                "cost_mean_usd_per_request"
            ),
            threshold.get(
                "cost_mean_usd_per_request"
            ),
        )
    )

    min_eligible_requests = (
        _expect_positive_int(
            (
                "gating.evidence_requirements."
                "min_n_eligible_requests.value"
            ),
            min_n.get("value"),
        )
    )

    max_excluded_fraction = (
        _expect_fraction(
            (
                "gating.evidence_requirements."
                "max_excluded_fraction.value"
            ),
            max_excluded.get("value"),
        )
    )

    return (
        latency_budget_ms,
        cost_mean_budget,
        min_eligible_requests,
        max_excluded_fraction,
    )


def _validate_manifest(
    manifest_path: Path,
    *,
    stats_path: Path,
    latency_budget_ms: float,
    cost_mean_budget: float,
    min_eligible_requests: int,
    max_excluded_fraction: float,
) -> None:
    manifest = _load_json_object(
        manifest_path,
        "Q4 input manifest",
    )

    source = _expect_object(
        "source",
        manifest.get("source"),
    )

    budgets = _expect_object(
        "budgets",
        manifest.get("budgets"),
    )

    expected_stats = (
        _repo_relative_or_supplied(
            stats_path,
            str(stats_path),
        )
    )

    if source.get("kind") != "artifact":
        raise ValueError(
            "source.kind must be "
            "literal 'artifact'"
        )

    if source.get("uri") != expected_stats:
        raise ValueError(
            "source.uri must match the "
            "supplied stats artifact: "
            f"expected {expected_stats!r}, "
            f"got {source.get('uri')!r}"
        )

    manifest_latency_budget = (
        _expect_positive_number(
            "budgets.latency_p95_ms_max",
            budgets.get(
                "latency_p95_ms_max"
            ),
        )
    )

    manifest_cost_budget = (
        _expect_positive_number(
            (
                "budgets."
                "cost_mean_usd_per_request_max"
            ),
            budgets.get(
                "cost_mean_usd_per_request_max"
            ),
        )
    )

    manifest_min_eligible = (
        _expect_positive_int(
            "budgets.min_eligible_requests",
            budgets.get(
                "min_eligible_requests"
            ),
        )
    )

    manifest_max_excluded = (
        _expect_fraction(
            "budgets.max_excluded_fraction",
            budgets.get(
                "max_excluded_fraction"
            ),
        )
    )

    if (
        manifest_latency_budget
        != latency_budget_ms
    ):
        raise ValueError(
            "input-manifest latency budget "
            "does not match the canonical "
            "Q4 specification"
        )

    if (
        manifest_cost_budget
        != cost_mean_budget
    ):
        raise ValueError(
            "input-manifest mean-cost budget "
            "does not match the canonical "
            "Q4 specification"
        )

    if (
        manifest_min_eligible
        != min_eligible_requests
    ):
        raise ValueError(
            "input-manifest minimum "
            "eligible-request count does not "
            "match the canonical Q4 specification"
        )

    if (
        manifest_max_excluded
        != max_excluded_fraction
    ):
        raise ValueError(
            "input-manifest excluded-fraction "
            "limit does not match the canonical "
            "Q4 specification"
        )


def _load_stats(
    path: Path,
) -> tuple[
    int,
    int,
    int,
    float,
    float,
    float | None,
]:
    payload = _load_json_object(
        path,
        "Q4 stats artifact",
    )

    if (
        payload.get("spec_id")
        != INPUT_SPEC_ID
    ):
        raise ValueError(
            "stats spec_id must be "
            f"{INPUT_SPEC_ID!r}; "
            f"got {payload.get('spec_id')!r}"
        )

    if (
        str(payload.get("spec_version"))
        != INPUT_SPEC_VERSION
    ):
        raise ValueError(
            "stats spec_version must be "
            f"{INPUT_SPEC_VERSION!r}; "
            f"got "
            f"{payload.get('spec_version')!r}"
        )

    n_requests = _expect_positive_int(
        "n_requests",
        payload.get("n_requests"),
    )

    n_eligible = _expect_nonnegative_int(
        "n_eligible_requests",
        payload.get(
            "n_eligible_requests"
        ),
    )

    n_excluded = _expect_nonnegative_int(
        "n_excluded_requests",
        payload.get(
            "n_excluded_requests"
        ),
    )

    if (
        n_eligible + n_excluded
        != n_requests
    ):
        raise ValueError(
            "n_eligible_requests + "
            "n_excluded_requests must equal "
            "n_requests"
        )

    latency_p95_ms = (
        _expect_nonnegative_number(
            "latency_ms_p95",
            payload.get(
                "latency_ms_p95"
            ),
        )
    )

    cost_mean = (
        _expect_nonnegative_number(
            (
                "cost_mean_usd_per_request"
            ),
            payload.get(
                "cost_mean_usd_per_request"
            ),
        )
    )

    raw_cost_p95 = payload.get(
        "cost_p95_usd_per_request"
    )

    cost_p95: float | None = None

    if raw_cost_p95 is not None:
        cost_p95 = (
            _expect_nonnegative_number(
                (
                    "cost_p95_usd_per_request"
                ),
                raw_cost_p95,
            )
        )

    return (
        n_requests,
        n_eligible,
        n_excluded,
        latency_p95_ms,
        cost_mean,
        cost_p95,
    )


def _build_summary(
    *,
    run_id: str,
    created_utc: str,
    input_manifest: str,
    stats_json: str,
    spec_path: str,
    tool: str,
    tool_version: str,
    git_sha: str | None,
    notes: str | None,
    n_requests: int,
    n_eligible: int,
    n_excluded: int,
    latency_p95_ms: float,
    cost_mean: float,
    cost_p95: float | None,
    latency_budget_ms: float,
    cost_mean_budget: float,
    min_eligible_requests: int,
    max_excluded_fraction: float,
) -> dict[str, Any]:
    excluded_fraction = (
        n_excluded / n_requests
    )

    insufficient_evidence = (
        n_eligible
        < min_eligible_requests
    )

    measurement_quality_ok = (
        excluded_fraction
        <= max_excluded_fraction
    )

    latency_ok = (
        latency_p95_ms
        <= latency_budget_ms
    )

    cost_ok = (
        cost_mean
        <= cost_mean_budget
    )

    passed = (
        not insufficient_evidence
        and measurement_quality_ok
        and latency_ok
        and cost_ok
    )

    provenance: dict[str, Any] = {
        "input_manifest": input_manifest,
        "stats_json": stats_json,
        "spec_path": spec_path,
        "tool": tool,
        "tool_version": tool_version,
    }

    if git_sha:
        provenance["git_sha"] = git_sha

    summary: dict[str, Any] = {
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "run_id": run_id,
        "created_utc": created_utc,
        "n_requests": n_requests,
        "n_eligible_requests": (
            n_eligible
        ),
        "min_eligible_requests": (
            min_eligible_requests
        ),
        "n_excluded_requests": (
            n_excluded
        ),
        "excluded_fraction": (
            excluded_fraction
        ),
        "max_excluded_fraction": (
            max_excluded_fraction
        ),
        "insufficient_evidence": (
            insufficient_evidence
        ),
        "measurement_quality_ok": (
            measurement_quality_ok
        ),
        "latency_p95_ms": (
            latency_p95_ms
        ),
        "latency_budget_ms": (
            latency_budget_ms
        ),
        "latency_ok": latency_ok,
        "cost_mean_usd_per_request": (
            cost_mean
        ),
        (
            "cost_mean_budget_"
            "usd_per_request"
        ): cost_mean_budget,
        "cost_ok": cost_ok,
        "pass": passed,
        "pass_basis": (
            "latency_p95_and_cost_mean_"
            "with_evidence_quality"
        ),
        "primary_metric_id": (
            "q4_slo_budget_conjunction"
        ),
        "budget_ratios": {
            "latency_p95_ratio": (
                latency_p95_ms
                / latency_budget_ms
            ),
            "cost_mean_ratio": (
                cost_mean
                / cost_mean_budget
            ),
            "excluded_fraction_ratio": (
                (
                    excluded_fraction
                    / max_excluded_fraction
                )
                if max_excluded_fraction > 0
                else (
                    0.0
                    if excluded_fraction == 0
                    else None
                )
            ),
        },
        "method": {
            "kind": "reference",
            "deterministic": True,
            "notes": (
                "Reducer over archived "
                "aggregate Q4 SLO stats "
                "using the canonical metric "
                "specification."
            ),
        },
        "provenance": provenance,
        "decision_rule": [
            (
                "Read canonical thresholds and "
                "evidence requirements from "
                "metrics/specs/q4_slo_v0.yml."
            ),
            (
                "Require "
                "n_eligible_requests >= "
                "min_eligible_requests."
            ),
            (
                "Require excluded_fraction <= "
                "max_excluded_fraction."
            ),
            (
                "Require latency_ms_p95 <= "
                "latency_budget_ms."
            ),
            (
                "Require "
                "cost_mean_usd_per_request <= "
                "cost_mean_budget_"
                "usd_per_request."
            ),
            (
                "Treat "
                "cost_p95_usd_per_request "
                "as diagnostic only when present."
            ),
            (
                "PASS iff all required "
                "conditions hold; FAIL otherwise."
            ),
        ],
    }

    if cost_p95 is not None:
        summary[
            "cost_p95_usd_per_request"
        ] = cost_p95

    if notes:
        summary["notes"] = notes

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--stats_json",
        required=True,
    )

    parser.add_argument(
        "--out",
        required=True,
    )

    parser.add_argument(
        "--input_manifest",
        required=True,
    )

    parser.add_argument(
        "--spec",
        default=DEFAULT_SPEC_PATH,
    )

    parser.add_argument(
        "--run_id",
        required=True,
    )

    parser.add_argument(
        "--created_utc",
        default="",
    )

    parser.add_argument(
        "--tool",
        default="PULSE_q4_reference",
    )

    parser.add_argument(
        "--tool_version",
        default="0.1.0-dev",
    )

    parser.add_argument(
        "--git_sha",
        default=os.getenv(
            "GITHUB_SHA",
            "",
        ).strip(),
    )

    parser.add_argument(
        "--notes",
        default="",
    )

    args = parser.parse_args()

    stats_path = Path(
        args.stats_json
    )

    manifest_path = Path(
        args.input_manifest
    )

    spec_path = Path(
        args.spec
    )

    out_path = Path(
        args.out
    )

    try:
        run_id = _expect_non_empty_string(
            "--run_id",
            args.run_id,
        )

        tool = _expect_non_empty_string(
            "--tool",
            args.tool,
        )

        tool_version = (
            _expect_non_empty_string(
                "--tool_version",
                args.tool_version,
            )
        )

        created_utc = (
            _resolve_created_utc(
                args.created_utc
            )
        )

        (
            latency_budget_ms,
            cost_mean_budget,
            min_eligible_requests,
            max_excluded_fraction,
        ) = _load_contract(
            spec_path
        )

        _validate_manifest(
            manifest_path,
            stats_path=stats_path,
            latency_budget_ms=(
                latency_budget_ms
            ),
            cost_mean_budget=(
                cost_mean_budget
            ),
            min_eligible_requests=(
                min_eligible_requests
            ),
            max_excluded_fraction=(
                max_excluded_fraction
            ),
        )

        (
            n_requests,
            n_eligible,
            n_excluded,
            latency_p95_ms,
            cost_mean,
            cost_p95,
        ) = _load_stats(
            stats_path
        )

    except ValueError as exc:
        parser.error(
            str(exc)
        )

    summary = _build_summary(
        run_id=run_id,
        created_utc=created_utc,
        input_manifest=(
            _repo_relative_or_supplied(
                manifest_path,
                args.input_manifest,
            )
        ),
        stats_json=(
            _repo_relative_or_supplied(
                stats_path,
                args.stats_json,
            )
        ),
        spec_path=(
            _repo_relative_or_supplied(
                spec_path,
                args.spec,
            )
        ),
        tool=tool,
        tool_version=tool_version,
        git_sha=(
            args.git_sha.strip()
            or None
        ),
        notes=(
            args.notes.strip()
            or None
        ),
        n_requests=n_requests,
        n_eligible=n_eligible,
        n_excluded=n_excluded,
        latency_p95_ms=(
            latency_p95_ms
        ),
        cost_mean=cost_mean,
        cost_p95=cost_p95,
        latency_budget_ms=(
            latency_budget_ms
        ),
        cost_mean_budget=(
            cost_mean_budget
        ),
        min_eligible_requests=(
            min_eligible_requests
        ),
        max_excluded_fraction=(
            max_excluded_fraction
        ),
    )

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = out_path.with_name(
        out_path.name + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        out_path,
    )

    print(
        json.dumps(
            {
                "out": str(out_path),
                "spec_id": (
                    summary["spec_id"]
                ),
                "spec_version": (
                    summary["spec_version"]
                ),
                "n_requests": (
                    summary["n_requests"]
                ),
                "n_eligible_requests": (
                    summary[
                        "n_eligible_requests"
                    ]
                ),
                "excluded_fraction": (
                    summary[
                        "excluded_fraction"
                    ]
                ),
                "latency_p95_ms": (
                    summary[
                        "latency_p95_ms"
                    ]
                ),
                (
                    "cost_mean_"
                    "usd_per_request"
                ): summary[
                    (
                        "cost_mean_"
                        "usd_per_request"
                    )
                ],
                "pass": summary["pass"],
                "insufficient_evidence": (
                    summary[
                        "insufficient_evidence"
                    ]
                ),
                "measurement_quality_ok": (
                    summary[
                        "measurement_quality_ok"
                    ]
                ),
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
