"""Deterministically build the three workbook fixtures, outside any repository."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from comparison_probe import (FULL, SMALL, FIXTURE_NAMES, comparison_rule,
                              digest, observation_frame)


def refresh_references(fixture):
    def refresh(value, hashes):
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "sha256"}:
                value["sha256"] = hashes[value["artifact_id"]]
            else:
                for child in value.values():
                    refresh(child, hashes)
        elif isinstance(value, list):
            for child in value:
                refresh(child, hashes)
    for _ in range(len(fixture["artifacts"]) + 2):
        hashes = {key: digest(item["payload"]) for key, item in fixture["artifacts"].items()}
        refresh(fixture["comparison_binding"], hashes)
        for item in fixture["artifacts"].values():
            refresh(item["payload"], hashes)
        updated = {key: digest(item["payload"]) for key, item in fixture["artifacts"].items()}
        if hashes == updated:
            for key, item in fixture["artifacts"].items():
                item["sha256"] = updated[key]
            return fixture
    raise ValueError("artifact references do not form a stable acyclic graph")


def rewrite_artifact(fixture, artifact_id, payload):
    fixture["artifacts"][artifact_id]["payload"] = deepcopy(payload)
    return refresh_references(fixture)


def build_fixture(fixture_id, target_scale, target_support):
    from fractions import Fraction
    payloads = {}
    def add(artifact_id, payload):
        payloads[artifact_id] = payload
        return {"artifact_id": artifact_id, "sha256": digest(payload)}
    reference = add("reference_domain", {
        "kind": "finite_reference_partition_v0", "dimension": 3,
        "cells": sorted(FULL), "cell_reference_volume": "1/64", "sectional_curvature": "1"})
    field_type = add("field_type", {"kind": "rational_scalar_field_v0",
                                   "fiber_map": "identity_v0", "unit": "dimensionless"})
    endpoints = {}
    for label, scale, support, step in (
            ("source", "1", FULL, 0), ("target", target_scale, target_support, 1)):
        support_ref = add(f"{label}_support", {"kind": "system_support_v0", "cells": sorted(support)})
        coverage_ref = add(f"{label}_coverage", {"kind": "successful_observation_coverage_v0",
                                               "cells": sorted(support)})
        state_ref = add(f"{label}_state", {"state_id": f"{fixture_id}:{label}", "step_index": step,
            "curvature_observation": str(1 / Fraction(scale)**2),
            "field_observations": {cell: "1" for cell in sorted(support)}})
        metric_ref = add(f"{label}_metric", {"kind": "uniform_scale_spatial_metric_v0",
                                            "scale_factor": scale})
        frame_ref = add(f"{label}_frame", observation_frame())
        endpoints[label] = {"state_ref": state_ref, "metric_ref": metric_ref,
            "system_support": {"status": "known", "ref": support_ref},
            "observation_coverage": {"status": "known", "ref": coverage_ref},
            "observation_frame_ref": frame_ref}
    transport = add("transport", {"kind": "identity_on_reference_labels_v0",
                                  "fiber_map": "identity_v0", "reference_domain_ref": reference})
    from comparison_probe import OPERATOR, UNITS
    normalization = add("normalization", {"kind": "identity_v0", "accepted_operator": OPERATOR,
        "accepted_units": UNITS, "common_codomain": "bound_curvature_and_scalar_samples_v0"})
    rule = add("comparison_rule", comparison_rule())
    fixture = {"fixture_id": fixture_id, "record_status": "synthetic_review_fixture",
        "comparison_binding": {"schema_version": "comparison_binding_v0", "authority_effect": "none",
            "reference_domain_ref": reference, "field_type_ref": field_type,
            "source": endpoints["source"], "target": endpoints["target"],
            "transport_ref": transport, "observation_normalization_ref": normalization,
            "comparison_rule_ref": rule},
        "artifacts": {key: {"payload": value, "sha256": digest(value)} for key, value in payloads.items()}}
    return refresh_references(fixture)


def write_fixtures():
    root = Path(__file__).resolve().parent / "fixtures"
    root.mkdir(exist_ok=True)
    parameters = (("fixture_a", "2", FULL), ("fixture_b", "1/2", FULL),
                  ("fixture_c", "2", SMALL))
    for name, args in zip(FIXTURE_NAMES, parameters):
        (root / name).write_text(json.dumps(build_fixture(*args), ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")


if __name__ == "__main__":
    write_fixtures()
