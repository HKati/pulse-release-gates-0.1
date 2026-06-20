#!/usr/bin/env python3
"""Golden-path and fail-closed regression coverage for canonical Q4 SLO v0."""

from __future__ import annotations   

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator, FormatChecker


JsonMutator = Callable[[dict[str, Any]], None]


def _find_repo_root() -> Path:
    starts: list[Path] = []

    try:
        starts.append(Path(__file__).resolve().parent)
    except NameError:
        pass

    starts.append(Path.cwd().resolve())

    seen: set[Path] = set()

    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue

            seen.add(candidate)

            required = (
                candidate
                / "PULSE_safe_pack_v0"
                / "tools"
                / "build_q4_slo_reference_summary.py",
                candidate
                / "schemas"
                / "metrics"
                / "q4_slo_summary_v0.schema.json",
                candidate
                / "metrics"
                / "specs"
                / "q4_slo_v0.yml",
                candidate
                / "examples"
                / "q4_slo_input_manifest.json",
                candidate
                / "examples"
                / "q4_slo_stats.pass_v0.json",
                candidate
                / "examples"
                / "q4_slo_summary.example.json",
            )

            if all(path.is_file() for path in required):
                return candidate

    raise RuntimeError(
        "Could not locate repository root containing the canonical Q4 artifacts"
    )


ROOT = _find_repo_root()

RUNNER = (
    ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_q4_slo_reference_summary.py"
)

SCHEMA = (
    ROOT
    / "schemas"
    / "metrics"
    / "q4_slo_summary_v0.schema.json"
)

SPEC = (
    ROOT
    / "metrics"
    / "specs"
    / "q4_slo_v0.yml"
)

MANIFEST = (
    ROOT
    / "examples"
    / "q4_slo_input_manifest.json"
)

STATS = (
    ROOT
    / "examples"
    / "q4_slo_stats.pass_v0.json"
)

EXAMPLE = (
    ROOT
    / "examples"
    / "q4_slo_summary.example.json"
)

SPEC_REL = "metrics/specs/q4_slo_v0.yml"
MANIFEST_REL = "examples/q4_slo_input_manifest.json"
STATS_REL = "examples/q4_slo_stats.pass_v0.json"

RUN_ID = "q4-ref-2026-04-03T20:00:00Z"
CREATED_UTC = "2026-04-03T20:00:00Z"
TOOL = "PULSE_q4_reference"
TOOL_VERSION = "0.1.0-dev"
GIT_SHA = "example-q4-ref"
NOTES = "Minimal example artefact for schema consumers and tests."


def _load_json(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(
        payload,
        dict,
    )

    return payload


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _relative(
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(
            ROOT.resolve()
        )
        .as_posix()
    )


def _pretty_json(
    payload: dict[str, Any],
) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )


def _assert_schema_valid(
    payload: dict[str, Any],
) -> None:
    schema = _load_json(
        SCHEMA
    )

    Draft202012Validator.check_schema(
        schema
    )

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(
            payload
        ),
        key=lambda error: tuple(
            str(part)
            for part in error.absolute_path
        ),
    )

    if errors:
        rendered = "\n".join(
            (
                f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
                f"{error.message}"
            )
            for error in errors
        )

        raise AssertionError(
            "Q4 summary failed schema validation:\n"
            + rendered
        )


def _run_runner(
    *,
    stats_arg: str,
    manifest_arg: str,
    spec_arg: str,
    out_path: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--stats_json",
        stats_arg,
        "--out",
        str(out_path),
        "--input_manifest",
        manifest_arg,
        "--spec",
        spec_arg,
        "--run_id",
        RUN_ID,
        "--created_utc",
        CREATED_UTC,
        "--tool",
        TOOL,
        "--tool_version",
        TOOL_VERSION,
        "--git_sha",
        GIT_SHA,
        "--notes",
        NOTES,
    ]

    if extra_args:
        command.extend(
            extra_args
        )

    return subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _run_checked_in_fixture() -> tuple[
    subprocess.CompletedProcess[str],
    dict[str, Any] | None,
]:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_path = (
            Path(temp_dir)
            / "q4_slo_summary.json"
        )

        result = _run_runner(
            stats_arg=STATS_REL,
            manifest_arg=MANIFEST_REL,
            spec_arg=SPEC_REL,
            out_path=out_path,
        )

        summary = (
            _load_json(out_path)
            if out_path.is_file()
            else None
        )

        return result, summary


def _run_modified_fixture(
    *,
    mutate_stats: JsonMutator | None = None,
    mutate_manifest: JsonMutator | None = None,
    raw_stats: str | None = None,
    raw_spec: str | None = None,
) -> tuple[
    subprocess.CompletedProcess[str],
    dict[str, Any] | None,
]:
    scratch_root = (
        ROOT
        / "tests"
        / "out"
    )

    scratch_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="q4-slo-",
        dir=scratch_root,
    ) as temp_dir:
        work = Path(
            temp_dir
        )

        stats_path = (
            work
            / "stats.json"
        )

        manifest_path = (
            work
            / "manifest.json"
        )

        out_path = (
            work
            / "summary.json"
        )

        if raw_stats is None:
            stats_payload = copy.deepcopy(
                _load_json(
                    STATS
                )
            )

            if mutate_stats is not None:
                mutate_stats(
                    stats_payload
                )

            _write_json(
                stats_path,
                stats_payload,
            )

        else:
            stats_payload = None

            stats_path.write_text(
                raw_stats,
                encoding="utf-8",
            )

        manifest_payload = copy.deepcopy(
            _load_json(
                MANIFEST
            )
        )

        manifest_payload[
            "source"
        ][
            "uri"
        ] = _relative(
            stats_path
        )

        manifest_payload[
            "hashes"
        ][
            "input_sha256"
        ] = _sha256(
            stats_path
        )

        if isinstance(
            stats_payload,
            dict,
        ):
            n_requests = stats_payload.get(
                "n_requests"
            )

            if (
                isinstance(
                    n_requests,
                    int,
                )
                and not isinstance(
                    n_requests,
                    bool,
                )
            ):
                manifest_payload[
                    "sampling"
                ][
                    "n"
                ] = n_requests

        if mutate_manifest is not None:
            mutate_manifest(
                manifest_payload
            )

        _write_json(
            manifest_path,
            manifest_payload,
        )

        spec_arg = SPEC_REL

        if raw_spec is not None:
            spec_path = (
                work
                / "q4_slo_v0.yml"
            )

            spec_path.write_text(
                raw_spec,
                encoding="utf-8",
            )

            spec_arg = _relative(
                spec_path
            )

        result = _run_runner(
            stats_arg=_relative(
                stats_path
            ),
            manifest_arg=_relative(
                manifest_path
            ),
            spec_arg=spec_arg,
            out_path=out_path,
        )

        summary = (
            _load_json(out_path)
            if out_path.is_file()
            else None
        )

        return result, summary


def test_checked_in_q4_summary_example_matches_schema(
) -> None:
    example = _load_json(
        EXAMPLE
    )

    _assert_schema_valid(
        example
    )

    assert (
        example["spec_id"]
        == "q4_slo_v0"
    )

    assert (
        example["spec_version"]
        == "0.1.0"
    )

    assert (
        example["pass"]
        is True
    )

    assert (
        example["pass_basis"]
        == (
            "latency_p95_and_cost_mean_"
            "with_evidence_quality"
        )
    )

    assert (
        example[
            "cost_mean_usd_per_request"
        ]
        == pytest.approx(
            0.004
        )
    )

    assert (
        example[
            "cost_mean_budget_usd_per_request"
        ]
        == pytest.approx(
            0.005
        )
    )

    assert (
        example[
            "n_eligible_requests"
        ]
        == 248
    )

    assert (
        example[
            "n_excluded_requests"
        ]
        == 2
    )

    assert (
        example[
            "excluded_fraction"
        ]
        == pytest.approx(
            0.008
        )
    )

    assert (
        example[
            "provenance"
        ][
            "spec_path"
        ]
        == SPEC_REL
    )

    assert (
        "min_requests"
        not in example
    )

    assert (
        "cost_p95_usd"
        not in example
    )

    assert (
        "cost_budget_usd"
        not in example
    )


def test_checked_in_manifest_binds_current_stats_fixture(
) -> None:
    manifest = _load_json(
        MANIFEST
    )

    assert (
        manifest[
            "source"
        ][
            "uri"
        ]
        == STATS_REL
    )

    assert (
        manifest[
            "hashes"
        ][
            "input_sha256"
        ]
        == _sha256(
            STATS
        )
    )

    assert (
        manifest[
            "budgets"
        ]
        == {
            "latency_p95_ms_max": 1500.0,
            "cost_mean_usd_per_request_max": 0.005,
            "min_eligible_requests": 200,
            "max_excluded_fraction": 0.02,
        }
    )


def test_runner_reproduces_checked_in_q4_summary_example(
) -> None:
    expected = _load_json(
        EXAMPLE
    )

    result, actual = (
        _run_checked_in_fixture()
    )

    assert (
        result.returncode
        == 0
    ), (
        "Runner returned non-zero exit code: "
        f"{result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}\n"
    )

    assert actual is not None, (
        "Runner did not emit a Q4 summary artifact"
    )

    _assert_schema_valid(
        actual
    )

    assert actual == expected, (
        "Checked-in Q4 summary example drifted "
        "from current runner output.\n\n"
        f"EXPECTED:\n{_pretty_json(expected)}\n\n"
        f"ACTUAL:\n{_pretty_json(actual)}\n"
    )


def test_cost_p95_is_diagnostic_only(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats[
            "cost_p95_usd_per_request"
        ] = 999.0

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        == 0
    ), result.stderr

    assert (
        summary is not None
    )

    _assert_schema_valid(
        summary
    )

    assert (
        summary[
            "cost_p95_usd_per_request"
        ]
        == pytest.approx(
            999.0
        )
    )

    assert (
        summary[
            "cost_mean_usd_per_request"
        ]
        == pytest.approx(
            0.004
        )
    )

    assert (
        summary["cost_ok"]
        is True
    )

    assert (
        summary["pass"]
        is True
    )


def test_mean_cost_failure_is_not_replaced_by_low_p95_cost(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats[
            "cost_mean_usd_per_request"
        ] = 0.006

        stats[
            "cost_p95_usd_per_request"
        ] = 0.001

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        == 0
    ), result.stderr

    assert (
        summary is not None
    )

    _assert_schema_valid(
        summary
    )

    assert (
        summary[
            "cost_mean_usd_per_request"
        ]
        == pytest.approx(
            0.006
        )
    )

    assert (
        summary[
            "cost_p95_usd_per_request"
        ]
        == pytest.approx(
            0.001
        )
    )

    assert (
        summary["cost_ok"]
        is False
    )

    assert (
        summary["pass"]
        is False
    )


def test_insufficient_eligible_evidence_materializes_fail(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats[
            "n_requests"
        ] = 200

        stats[
            "n_eligible_requests"
        ] = 199

        stats[
            "n_excluded_requests"
        ] = 1

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        == 0
    ), result.stderr

    assert (
        summary is not None
    )

    _assert_schema_valid(
        summary
    )

    assert (
        summary[
            "insufficient_evidence"
        ]
        is True
    )

    assert (
        summary[
            "measurement_quality_ok"
        ]
        is True
    )

    assert (
        summary["pass"]
        is False
    )


def test_excessive_excluded_fraction_materializes_fail(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats[
            "n_requests"
        ] = 250

        stats[
            "n_eligible_requests"
        ] = 240

        stats[
            "n_excluded_requests"
        ] = 10

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        == 0
    ), result.stderr

    assert (
        summary is not None
    )

    _assert_schema_valid(
        summary
    )

    assert (
        summary[
            "excluded_fraction"
        ]
        == pytest.approx(
            0.04
        )
    )

    assert (
        summary[
            "measurement_quality_ok"
        ]
        is False
    )

    assert (
        summary[
            "insufficient_evidence"
        ]
        is False
    )

    assert (
        summary["pass"]
        is False
    )


def test_missing_mean_cost_fails_closed_without_output(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats.pop(
            "cost_mean_usd_per_request"
        )

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        "cost_mean_usd_per_request must be a number"
        in result.stderr
    )


def test_malformed_request_counts_fail_closed_without_output(
) -> None:
    def mutate(
        stats: dict[str, Any],
    ) -> None:
        stats[
            "n_requests"
        ] = 250

        stats[
            "n_eligible_requests"
        ] = 249

        stats[
            "n_excluded_requests"
        ] = 2

    result, summary = (
        _run_modified_fixture(
            mutate_stats=mutate,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        (
            "n_eligible_requests + "
            "n_excluded_requests must equal "
            "n_requests"
        )
        in result.stderr
    )


def test_manifest_budget_drift_fails_closed_without_output(
) -> None:
    def mutate(
        manifest: dict[str, Any],
    ) -> None:
        manifest[
            "budgets"
        ][
            "cost_mean_usd_per_request_max"
        ] = 0.006

    result, summary = (
        _run_modified_fixture(
            mutate_manifest=mutate,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        (
            "input-manifest mean-cost budget "
            "does not match the canonical "
            "Q4 specification"
        )
        in result.stderr
    )


def test_duplicate_stats_json_key_fails_closed_without_output(
) -> None:
    raw_stats = """{
  "spec_id": "q4_slo_input_v0",
  "spec_version": "0.2.0",
  "created_utc": "2026-04-03T20:00:00Z",
  "n_requests": 250,
  "n_requests": 251,
  "n_eligible_requests": 248,
  "n_excluded_requests": 2,
  "latency_ms_p95": 180.0,
  "cost_mean_usd_per_request": 0.004
}
"""

    result, summary = (
        _run_modified_fixture(
            raw_stats=raw_stats,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        "duplicate JSON key 'n_requests'"
        in result.stderr
    )


def test_nonfinite_stats_value_fails_closed_without_output(
) -> None:
    raw_stats = """{
  "spec_id": "q4_slo_input_v0",
  "spec_version": "0.2.0",
  "created_utc": "2026-04-03T20:00:00Z",
  "n_requests": 250,
  "n_eligible_requests": 248,
  "n_excluded_requests": 2,
  "latency_ms_p95": 180.0,
  "cost_mean_usd_per_request": NaN
}
"""

    result, summary = (
        _run_modified_fixture(
            raw_stats=raw_stats,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        "non-finite JSON constant not allowed"
        in result.stderr
    )


def test_duplicate_spec_yaml_key_fails_closed_without_output(
) -> None:
    raw_spec = """spec:
  id: q4_slo_v0
  version: "0.1.0"
  category: "Q"
  metric_id: "q4_slo"
  gate_signal: "q4_slo_ok"

gating:
  threshold:
    latency_p95_ms: 1500
    latency_p95_ms: 1400
    cost_mean_usd_per_request: 0.005
  evidence_requirements:
    min_n_eligible_requests:
      value: 200
    max_excluded_fraction:
      value: 0.02
"""

    result, summary = (
        _run_modified_fixture(
            raw_spec=raw_spec,
        )
    )

    assert (
        result.returncode
        != 0
    )

    assert (
        summary is None
    )

    assert (
        "duplicate YAML key 'latency_p95_ms'"
        in result.stderr
    )


def test_legacy_budget_flags_are_not_accepted(
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_path = (
            Path(temp_dir)
            / "q4_slo_summary.json"
        )

        result = _run_runner(
            stats_arg=STATS_REL,
            manifest_arg=MANIFEST_REL,
            spec_arg=SPEC_REL,
            out_path=out_path,
            extra_args=[
                "--latency_budget_ms",
                "250",
                "--cost_budget_usd",
                "0.01",
                "--min_requests",
                "100",
            ],
        )

        assert (
            result.returncode
            != 0
        )

        assert (
            not out_path.exists()
        )

        assert (
            "unrecognized arguments"
            in result.stderr
        )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [
                "-q",
                __file__,
            ]
        )
    )
