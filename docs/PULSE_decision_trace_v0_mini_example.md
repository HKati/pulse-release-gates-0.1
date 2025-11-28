# Decision Trace v0 – mini example

This document provides a minimal, schematic example of a
`decision_trace_v0` object.

The goal is to show how a release decision can be represented as a
sequence of steps:

1. baseline status evaluation,
2. topology overlays (stability map + paradox field),
3. final decision with `release_state` and `stability_type`.

> Note: this is an illustrative example, not a full specification of
> the schema. Field names and structure should be aligned with
> `PULSE_decision_trace_v0.schema.json` in the repo.

---

## Example JSON snippet

Below is a minimal `decision_trace_v0` object inlined as JSON:

    {
      "decision_trace_v0": {
        "version": "PULSE_decision_trace_v0",
        "generated_at_utc": "2025-01-10T13:00:00Z",
        "release_id": "demo_release_001",
        "inputs": {
          "status_path": "PULSE_safe_pack_v0/artifacts/status.json",
          "stability_map_path": "PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json",
          "paradox_field_path": "PULSE_safe_pack_v0/artifacts/paradox_field_v0.json",
          "decision_engine_path": "PULSE_safe_pack_v0/artifacts/decision_engine_v0.json"
        },
        "steps": [
          {
            "step_id": "step_01_status",
            "kind": "status_evaluation",
            "summary": {
              "gate_count": 42,
              "failed_gates": [],
              "passed_gates": [
                "quality.q3_fairness_ok",
                "slo.q4_slo_ok"
              ],
              "rdsi": 0.94
            },
            "notes": "Baseline PULSE safe pack evaluation of gates and metrics."
          },
          {
            "step_id": "step_02_topology",
            "kind": "topology_overlays",
            "summary": {
              "stability_summary": {
                "cell_count": 1,
                "delta_bend_max": 1.0
              },
              "paradox_summary": {
                "atom_count": 3,
                "severe_atom_count": 1
              }
            },
            "notes": "Topology v0 overlays applied: stability map + paradox_field_v0."
          },
          {
            "step_id": "step_03_decision",
            "kind": "final_decision",
            "release_state": "PROD_OK",
            "stability_type": "unstably_good",
            "rationale": [
              "All required gates pass (PROD_OK).",
              "Topology overlays show non-trivial curvature and paradox atoms.",
              "Classified as 'unstably_good' to mark a green but structurally tense region."
            ]
          }
        ]
      }
    }

---

## Interpretation

From this trace we can reconstruct:

1. **What the baseline status said**

   - No failed gates.
   - `rdsi` is high (0.94).
   - Normally this would be a straightforward “green” release.

2. **What Topology v0 contributed**

   - `delta_bend_max > 0` → the decision field is locally curved.
   - non-zero `atom_count` → there are paradox atoms in the field.
   - Together they indicate a **non-trivial region**, not a flat surface.

3. **How the final decision is framed**

   - `release_state = "PROD_OK"` → release is allowed (from a gating perspective).
   - `stability_type = "unstably_good"` → governance is informed that:
     - this is a “green but tense” region,
     - small changes in data or thresholds may flip the outcome.

The trace makes the process explicit:

- it is not “just” a single label,
- but a **sequence of field-aware steps** from raw gates to a topological
  decision type.

This mini example can be:

- embedded in documentation,
- used as a reference for UI / dashboards that visualise decision traces,
- or as a test fixture for tools that consume `decision_trace_v0` artefacts.
