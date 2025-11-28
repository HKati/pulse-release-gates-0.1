# Decision Engine v0 – `unstably_bad` example

This document provides a minimal example of a `decision_engine_v0.json`
snippet where:

- `release_state = "BLOCK"`
- `stability_type = "unstably_bad"`

The goal is to illustrate how a blocked release in a **paradox-rich /
curved** region of the decision field appears in the Decision Engine v0
overlay.

---

## Example JSON snippet

Below is an example `decision_engine_v0` object inlined as JSON:

    {
      "decision_engine_v0": {
        "version": "PULSE_decision_engine_v0",
        "generated_at_utc": "2025-01-10T12:45:00Z",
        "inputs": {
          "status_path": "PULSE_safe_pack_v0/artifacts/status.json",
          "stability_map_path": "PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json",
          "paradox_field_path": "PULSE_safe_pack_v0/artifacts/paradox_field_v0.json"
        },
        "release_state": "BLOCK",
        "stability_type": "unstably_bad",
        "status_summary": {
          "gate_count": 42,
          "failed_gates": [
            "safety.s1_blocking"
          ],
          "passed_gates": [
            "quality.q3_fairness_ok",
            "slo.q4_slo_ok"
          ],
          "rdsi": 0.41
        },
        "stability_summary": {
          "cell_count": 1,
          "delta_bend_max": 1.2
        },
        "paradox_summary": {
          "atom_count": 4,
          "severe_atom_count": 2
        }
      }
    }

---

### Interpretation

- `release_state = "BLOCK"`  
  – at least one blocking safety gate fails; the release must not go to prod.

- `stability_type = "unstably_bad"`  
  – topology signals (stability map + paradox field) indicate that:
    - the local decision field is strongly curved (`delta_bend_max > 0`), and
    - there are multiple non-trivial paradox atoms (`atom_count > 0`,
      `severe_atom_count > 0`).

**Intuition:**

> The release is bad (BLOCK), *and* it sits in a structurally tense region
> of the decision field. The failure is not just a simple, isolated gate
> violation – it reflects a deeper conflict in requirements (e.g. safety
> versus other constraints).

In governance terms:

- this is not only a “do not release” decision,
- but also a signal that the **field itself** (gates, SLOs, constraints)
  should be revisited.

This example can be:

- embedded in documentation,
- used as a reference for dashboards that highlight structural tension,
- or as a test fixture for tools that consume `decision_engine_v0` overlays.
