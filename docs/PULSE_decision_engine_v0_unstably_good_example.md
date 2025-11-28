# Decision Engine v0 – `unstably_good` example

This document provides a minimal example of a `decision_engine_v0.json`
snippet where:

- `release_state = "PROD_OK"`
- `stability_type = "unstably_good"`

The goal is to illustrate how a “green but structurally tense” release
appears in the Decision Engine v0 overlay.

---

## Example JSON snippet

Below is an example `decision_engine_v0` object inlined as JSON:

    {
      "decision_engine_v0": {
        "version": "PULSE_decision_engine_v0",
        "generated_at_utc": "2025-01-10T12:34:56Z",
        "inputs": {
          "status_path": "PULSE_safe_pack_v0/artifacts/status.json",
          "stability_map_path": "PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json",
          "paradox_field_path": "PULSE_safe_pack_v0/artifacts/paradox_field_v0.json"
        },
        "release_state": "PROD_OK",
        "stability_type": "unstably_good",
        "status_summary": {
          "gate_count": 42,
          "failed_gates": [],
          "passed_gates": [
            "quality.q3_fairness_ok",
            "slo.q4_slo_ok"
          ],
          "rdsi": 0.94
        },
        "stability_summary": {
          "cell_count": 1,
          "delta_bend_max": 1.0
        },
        "paradox_summary": {
          "atom_count": 3,
          "severe_atom_count": 1
        }
      }
    }

### Interpretation

- `release_state = "PROD_OK"`  
  – all required gates pass; the release is “green” in the usual sense.

- `stability_type = "unstably_good"`  
  – topology signals (stability map + paradox field) indicate that:
    - the local decision field is curved (`delta_bend_max > 0`), and/or
    - there are non-trivial paradox atoms (`atom_count > 0`).

**Intuition:**

> The release is good (PROD_OK), but it lives in a structurally tense
> region of the decision field. Small changes in data or thresholds may
> flip the outcome.

This example can be:

- embedded in documentation,
- used as a reference for dashboards,
- or as a test fixture for tools that consume `decision_engine_v0` overlays.
