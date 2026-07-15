#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TOOL = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_binding_report_v0.py"
)
SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_binding_report_v0.schema.json"
)
EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_binding_report_6066_example_v0.json"
)

RESOURCE_CLASSES = (
    "transition_bound",
    "evidence_bound",
    "preservation_bound",
    "advisory_bound",
    "unbound",
    "unknown",
)


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_tool(
    report_path: Path = EXAMPLE,
    *,
    schema_path: Path = SCHEMA,
    output_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(schema_path),
        "--report",
        str(report_path),
    ]

    if output_path is not None:
        command.extend(["--output", str(output_path)])

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_diagnostic(
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    assert result.stdout, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def assert_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert any(
        expected_fragment in error
        for error in diagnostic["errors"]
    ), diagnostic["errors"]
    return diagnostic


def find_node(
    report: dict[str, Any],
    node_id: str,
) -> dict[str, Any]:
    return next(
        node
        for node in report["compute_nodes"]
        if node["node_id"] == node_id
    )


def recompute_summary_and_resources(
    report: dict[str, Any],
) -> None:
    subject_nodes = [
        node
        for node in report["compute_nodes"]
        if node["execution_scope"] == "subject"
    ]
    observer_nodes = [
        node
        for node in report["compute_nodes"]
        if node["execution_scope"] == "analysis_observer"
    ]

    counts = Counter(
        node["binding_class"]
        for node in subject_nodes
    )

    summary = report["summary"]
    summary["subject_compute_nodes"] = len(subject_nodes)
    summary["observer_nodes"] = len(observer_nodes)
    summary["transition_bound_nodes"] = counts["transition_bound"]
    summary["evidence_bound_nodes"] = counts["evidence_bound"]
    summary["preservation_bound_nodes"] = counts["preservation_bound"]
    summary["advisory_bound_nodes"] = counts["advisory_bound"]
    summary["unbound_nodes"] = counts["unbound"]
    summary["unknown_nodes"] = counts["unknown"]
    summary["unbound_authoritative_mutation_count"] = sum(
        1
        for node in subject_nodes
        if node["unbound_authoritative_mutation"] is True
    )

    axes = report["resource_summary"]["axes"]
    axis_names = set(axes)

    for node in report["compute_nodes"]:
        node["flags"]["resource_measurement_partial"] = (
            set(node["resource_usage"]) != axis_names
        )

    for axis_name, axis in axes.items():
        category_values = {
            binding_class: 0.0
            for binding_class in RESOURCE_CLASSES
        }

        measured_subject_nodes = [
            node
            for node in subject_nodes
            if axis_name in node["resource_usage"]
        ]
        measured_observer_nodes = [
            node
            for node in observer_nodes
            if axis_name in node["resource_usage"]
        ]

        for node in measured_subject_nodes:
            category_values[node["binding_class"]] += float(
                node["resource_usage"][axis_name]
            )

        measured_total = sum(category_values.values())
        observer_overhead = sum(
            float(node["resource_usage"][axis_name])
            for node in measured_observer_nodes
        )

        axis["measured_total"] = (
            int(measured_total)
            if isinstance(axis["measured_total"], int)
            and measured_total.is_integer()
            else measured_total
        )
        for binding_class, value in category_values.items():
            axis[binding_class] = (
                int(value)
                if isinstance(axis[binding_class], int)
                and value.is_integer()
                else value
            )

        axis["observer_overhead"] = (
            int(observer_overhead)
            if isinstance(axis["observer_overhead"], int)
            and observer_overhead.is_integer()
            else observer_overhead
        )
        axis["nodes_with_measurement"] = len(measured_subject_nodes)
        axis["total_subject_nodes"] = len(subject_nodes)
        axis["measurement_coverage_ratio"] = (
            len(measured_subject_nodes) / len(subject_nodes)
            if subject_nodes
            else 0.0
        )
        axis["ratios"] = {
            binding_class: (
                category_values[binding_class] / measured_total
                if measured_total
                else 0.0
            )
            for binding_class in RESOURCE_CLASSES
        }

    if not axes:
        summary["resource_measurement_status"] = "none"
    elif all(
        math.isclose(
            axis["measurement_coverage_ratio"],
            1.0,
        )
        for axis in axes.values()
    ):
        summary["resource_measurement_status"] = "complete"
    else:
        summary["resource_measurement_status"] = "partial"


def sort_contract_arrays(report: dict[str, Any]) -> None:
    report["subject"]["active_policy_sets"] = sorted(
        set(report["subject"]["active_policy_sets"])
    )
    report["inputs"] = sorted(
        report["inputs"],
        key=lambda item: (
            item["role"],
            item["path_or_uri"],
            item["sha256"],
        ),
    )
    report["compute_nodes"] = sorted(
        report["compute_nodes"],
        key=lambda node: node["node_id"],
    )
    report["state_nodes"] = sorted(
        report["state_nodes"],
        key=lambda state: state["state_id"],
    )
    report["edges"] = sorted(
        report["edges"],
        key=lambda edge: edge["edge_id"],
    )
    report["findings"] = sorted(
        report["findings"],
        key=lambda finding: (
            finding["finding_id"],
            finding["node_id"] or "",
            finding["state_id"] or "",
            finding["edge_id"] or "",
            finding["message"],
        ),
    )
    report["errors"] = sorted(set(report["errors"]))

    for node in report["compute_nodes"]:
        node["input_state_ids"] = sorted(
            set(node["input_state_ids"])
        )
        node["output_state_ids"] = sorted(
            set(node["output_state_ids"])
        )
        node["observed_mutation_classes"] = sorted(
            set(node["observed_mutation_classes"])
        )
        node["resource_usage"] = dict(
            sorted(node["resource_usage"].items())
        )

    for edge in report["edges"]:
        edge["evidence_digests"] = sorted(
            set(edge["evidence_digests"])
        )
        edge["notes"] = sorted(set(edge["notes"]))

    for finding in report["findings"]:
        finding["evidence_refs"] = sorted(
            set(finding["evidence_refs"])
        )

    report["resource_summary"]["axes"] = dict(
        sorted(
            report["resource_summary"]["axes"].items()
        )
    )


def test_valid_example_passes() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["tool"] == (
        "check_pulsemech_compute_binding_report_v0"
    )
    assert diagnostic["ok"] is True
    assert diagnostic["schema_valid"] is True
    assert diagnostic["errors"] == []
    assert all(diagnostic["checks"].values())


def test_output_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "diagnostic.json"
    result = run_tool(output_path=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert read_json(output) == parse_diagnostic(result)


def test_block_decision_can_have_valid_report_ok(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["subject"]["decision"] = "BLOCK"

    report_path = tmp_path / "block_report.json"
    write_json(report_path, report)

    result = run_tool(report_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert parse_diagnostic(result)["ok"] is True


def test_duplicate_json_key_is_rejected(tmp_path: Path) -> None:
    raw = EXAMPLE.read_text(encoding="utf-8")
    raw = raw.replace(
        '"schema_version": "pulsemech_compute_binding_report_v0",',
        (
            '"schema_version": "pulsemech_compute_binding_report_v0",\n'
            '  "schema_version": "pulsemech_compute_binding_report_v0",'
        ),
        1,
    )
    report_path = tmp_path / "duplicate_key.json"
    report_path.write_text(raw, encoding="utf-8")

    assert_failure(
        run_tool(report_path),
        "duplicate JSON key: schema_version",
    )


def test_non_finite_number_is_rejected(tmp_path: Path) -> None:
    raw = EXAMPLE.read_text(encoding="utf-8")
    raw = raw.replace(
        '"workflow_run_id": 29249887581',
        '"workflow_run_id": NaN',
        1,
    )
    report_path = tmp_path / "non_finite.json"
    report_path.write_text(raw, encoding="utf-8")

    assert_failure(
        run_tool(report_path),
        "non-finite JSON value: NaN",
    )


def test_unknown_remains_distinct_from_unbound(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:unbound-diagnostic")
    node["binding_status"] = "unknown"
    node["binding_class"] = "unknown"

    finding = next(
        finding
        for finding in report["findings"]
        if finding["finding_id"] == "unbound_compute"
    )
    finding["finding_id"] = "unknown_compute_binding"
    finding["message"] = (
        "The diagnostic relation cannot be classified from "
        "the available evidence."
    )

    recompute_summary_and_resources(report)
    sort_contract_arrays(report)

    report_path = tmp_path / "unknown_binding.json"
    write_json(report_path, report)

    result = run_tool(report_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert parse_diagnostic(result)["ok"] is True



def make_structural_declared_report() -> dict[str, Any]:
    report = read_json(EXAMPLE)
    report["analysis_boundary"]["analysis_level"] = "structural_declared"

    for node in report["compute_nodes"]:
        node["observed_mutation_classes"] = []
        node["unbound_authoritative_mutation"] = False
        node["binding_status"] = "partial"
        node["binding_class"] = (
            "observer"
            if node["execution_scope"] == "analysis_observer"
            else "unknown"
        )

    for edge in report["edges"]:
        edge["observed"] = False
        edge["binding_status"] = "partial"
        edge["evidence_digests"] = []

    for finding in report["findings"]:
        if finding["finding_id"] == "unbound_compute":
            finding["finding_id"] = "unknown_compute_binding"
            finding["message"] = (
                "The structural-only contract does not claim an "
                "observed downstream binding."
            )

    recompute_summary_and_resources(report)
    sort_contract_arrays(report)
    return report


def test_structural_declared_report_cannot_claim_observed_binding(
    tmp_path: Path,
) -> None:
    report = make_structural_declared_report()

    report_path = tmp_path / "structural_declared.json"
    write_json(report_path, report)

    result = run_tool(report_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert parse_diagnostic(result)["ok"] is True

    report["edges"][0]["observed"] = True
    report["edges"][0]["evidence_digests"] = ["a" * 64]

    report_path = tmp_path / "structural_with_observed_edge.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "structural_level_cannot_claim_observed_edge",
    )

def test_binding_class_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:check-gates")
    node["binding_class"] = "advisory_bound"
    recompute_summary_and_resources(report)

    report_path = tmp_path / "binding_class_mismatch.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "binding_class",
    )


def test_observer_cannot_be_counted_as_subject_compute(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["summary"]["subject_compute_nodes"] += 1
    report["summary"]["observer_nodes"] -= 1

    report_path = tmp_path / "observer_in_subject_total.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "subject_compute_nodes_mismatch",
    )


def test_observer_overhead_cannot_enter_measured_subject_total(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    axis = report["resource_summary"]["axes"][
        "runner_wall_seconds"
    ]
    axis["measured_total"] += axis["observer_overhead"]

    report_path = tmp_path / "observer_in_total.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "measured_total_mismatch",
    )


def test_partial_measurement_status_is_derived(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["summary"]["resource_measurement_status"] = "complete"

    report_path = tmp_path / "wrong_measurement_status.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "resource_measurement_status_mismatch",
    )


def test_resource_flag_must_match_axis_coverage(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:check-gates")
    node["flags"]["resource_measurement_partial"] = False

    report_path = tmp_path / "wrong_resource_flag.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "resource_measurement_partial_mismatch",
    )


def test_missing_observed_output_edge_is_rejected(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["edges"] = [
        edge
        for edge in report["edges"]
        if edge["edge_id"] != "edge:011-decision-produced"
    ]

    report_path = tmp_path / "missing_output_edge.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "output_edge_missing:state:decision",
    )


def test_dangling_state_reference_is_rejected(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:check-gates")
    node["input_state_ids"].append("state:missing")
    node["input_state_ids"].sort()

    report_path = tmp_path / "dangling_state.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "input_state_ids_missing:state:missing",
    )


def test_duplicate_node_id_is_rejected(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    duplicate = copy.deepcopy(report["compute_nodes"][0])
    report["compute_nodes"].append(duplicate)
    report["compute_nodes"].sort(key=lambda node: node["node_id"])

    report_path = tmp_path / "duplicate_node.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "duplicate_compute_node_id",
    )


def test_unbound_authoritative_mutation_is_representable(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:unbound-diagnostic")
    node["mutation_authority"] = "final_status"
    node["observed_mutation_classes"] = ["final_status"]
    node["unbound_authoritative_mutation"] = True
    node["flags"]["mutation_authority_present"] = True

    report["findings"].append(
        {
            "finding_id": "undeclared_authoritative_writer",
            "severity": "authority_integrity_candidate",
            "node_id": "compute:unbound-diagnostic",
            "state_id": None,
            "edge_id": None,
            "message": (
                "The illustrative unbound node records a "
                "final-status mutation."
            ),
            "evidence_refs": ["compute:unbound-diagnostic"],
        }
    )

    recompute_summary_and_resources(report)
    sort_contract_arrays(report)

    report_path = tmp_path / "unbound_authoritative.json"
    write_json(report_path, report)

    result = run_tool(report_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert parse_diagnostic(result)["ok"] is True


def test_unbound_authoritative_mutation_flag_must_be_exact(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:unbound-diagnostic")
    node["mutation_authority"] = "final_status"
    node["observed_mutation_classes"] = ["final_status"]
    node["unbound_authoritative_mutation"] = False
    node["flags"]["mutation_authority_present"] = True

    report_path = tmp_path / "wrong_unbound_authoritative_flag.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "unbound_authoritative_mutation_mismatch",
    )


def test_subject_run_binding_cannot_drift(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    node = find_node(report, "compute:check-gates")
    node["run_binding"]["subject_run_key"] = "different-run"

    report_path = tmp_path / "run_binding_drift.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "subject_run_key_mismatch",
    )


def test_unsorted_contract_array_is_rejected(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["compute_nodes"] = list(reversed(report["compute_nodes"]))

    report_path = tmp_path / "unsorted_nodes.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "compute_nodes_not_sorted",
    )


def test_finding_reference_must_resolve(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["findings"][0]["node_id"] = "compute:missing"

    report_path = tmp_path / "missing_finding_reference.json"
    write_json(report_path, report)

    assert_failure(
        run_tool(report_path),
        "finding:resource_measurement_partial.node_id_missing",
    )


def test_output_refuses_status_json(
    tmp_path: Path,
) -> None:
    output = tmp_path / "status.json"

    assert_failure(
        run_tool(output_path=output),
        "refusing_to_write_status_json",
    )
    assert not output.exists()


def test_output_refuses_to_overwrite_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        EXAMPLE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    original = report_path.read_bytes()

    assert_failure(
        run_tool(report_path, output_path=report_path),
        "refusing_to_overwrite_report",
    )
    assert report_path.read_bytes() == original


def test_schema_invalid_report_fails_closed(
    tmp_path: Path,
) -> None:
    report = read_json(EXAMPLE)
    report["resource_summary"]["axes"][
        "runner_wall_seconds"
    ]["unit"] = "tokens"

    report_path = tmp_path / "schema_invalid.json"
    write_json(report_path, report)

    diagnostic = assert_failure(
        run_tool(report_path),
        "schema_error",
    )
    assert diagnostic["schema_valid"] is False


def check_pulsemech_compute_binding_report_v0() -> None:
    test_valid_example_passes()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)
        test_output_matches_stdout(tmp_path)
        test_block_decision_can_have_valid_report_ok(tmp_path)
        test_duplicate_json_key_is_rejected(tmp_path)
        test_non_finite_number_is_rejected(tmp_path)
        test_unknown_remains_distinct_from_unbound(tmp_path)
        test_structural_declared_report_cannot_claim_observed_binding(tmp_path)
        test_binding_class_mismatch_is_rejected(tmp_path)
        test_observer_cannot_be_counted_as_subject_compute(tmp_path)
        test_observer_overhead_cannot_enter_measured_subject_total(tmp_path)
        test_partial_measurement_status_is_derived(tmp_path)
        test_resource_flag_must_match_axis_coverage(tmp_path)
        test_missing_observed_output_edge_is_rejected(tmp_path)
        test_dangling_state_reference_is_rejected(tmp_path)
        test_duplicate_node_id_is_rejected(tmp_path)
        test_unbound_authoritative_mutation_is_representable(tmp_path)
        test_unbound_authoritative_mutation_flag_must_be_exact(tmp_path)
        test_subject_run_binding_cannot_drift(tmp_path)
        test_unsorted_contract_array_is_rejected(tmp_path)
        test_finding_reference_must_resolve(tmp_path)
        test_output_refuses_status_json(tmp_path)
        test_output_refuses_to_overwrite_report(tmp_path)
        test_schema_invalid_report_fails_closed(tmp_path)


def test_check_pulsemech_compute_binding_report_v0() -> None:
    test_valid_example_passes()


if __name__ == "__main__":
    check_pulsemech_compute_binding_report_v0()
    print("OK: PULSEmech compute-binding report validator v0 passed")
