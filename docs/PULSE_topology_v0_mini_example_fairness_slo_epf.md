# PULSE Topology v0 — Mini Example (Q3 Fairness · Q4 SLO · EPF)

This note gives a concrete, minimal example of the Topology v0 layer on top of the deterministic PULSE gates (I₂–I₇, Q₁–Q₄, SLO). It is designed as a toy model that fits inside `stability_map_v0` and `paradox_field_v0` without changing any CI behaviour.

The example focuses on a 2×2 cell defined by:

- a policy axis **a** (fairness threshold), and  
- an EPF axis **b** (EPF disabled vs enabled).

We consider two gates:

- `q3_fairness_ok` — fairness gate (Q₃)  
- `q4_slo_ok` — SLO gate (Q₄; p95 latency & cost budget)

## 1. Configuration space

Let

- a ∈ {0, 1}:  
  - a = 0 → loose fairness threshold  
  - a = 1 → strict fairness threshold

- b ∈ {0, 1}:  
  - b = 0 → EPF OFF (baseline PULSE)  
  - b = 1 → EPF ON (shadow instrumentation, extra detectors only in the band)

Define four configurations:

- x₀₀ = (a=0, b=0)  
- x₁₀ = (a=1, b=0)  
- x₀₁ = (a=0, b=1)  
- x₁₁ = (a=1, b=1)

Each configuration corresponds to one PULSE run and one `status.json` entry.

## 2. Gate field on the 2×2 cell

We assign PASS/FAIL to the gates as follows (toy, but realistic):

- Fairness (Q₃):

  - `q3_fairness_ok(x00) = 0` (FAIL)  
  - `q3_fairness_ok(x10) = 1` (PASS)  
  - `q3_fairness_ok(x01) = 0` (FAIL)  
  - `q3_fairness_ok(x11) = 1` (PASS)

  Intuition: strict fairness threshold passes, loose threshold fails, independently of EPF.

- SLO (Q₄):

  - `q4_slo_ok(x00) = 1` (PASS)  
  - `q4_slo_ok(x10) = 0` (FAIL)  
  - `q4_slo_ok(x01) = 0` (FAIL)  
  - `q4_slo_ok(x11) = 0` (FAIL)

  Intuition:  
  - loose fairness + EPF off → cheap → passes SLO;  
  - strict fairness → fairness pipeline is expensive → fails SLO;  
  - EPF adds overhead, so any EPF=1 configuration also fails SLO.

This already encodes a realistic **fairness–SLO tension**.

## 3. Δ-curvature on the fairness axis

For a given gate g and the policy axis a, we define discrete derivatives at fixed b:

- Δₐ g | b=0 = g(x₁₀) − g(x₀₀)  
- Δₐ g | b=1 = g(x₁₁) − g(x₀₁)

and a discrete curvature:

- Kᵍ = (Δₐ g | b=1) − (Δₐ g | b=0)

If the effect of tightening fairness is independent of EPF, we expect Kᵍ = 0.  
If EPF changes how fairness interacts with the gate, we get Kᵍ ≠ 0.

### 3.1. Fairness gate

For `q3_fairness_ok`:

- Δₐ g | b=0 = 1 − 0 = +1  
- Δₐ g | b=1 = 1 − 0 = +1  
- K_fairness = +1 − +1 = 0

The fairness gate front does **not bend** in the EPF dimension: tightening the threshold
has the same effect with and without EPF.

### 3.2. SLO gate

For `q4_slo_ok`:

- Δₐ g | b=0 = 0 − 1 = −1  
- Δₐ g | b=1 = 0 − 0 = 0  
- K_slo = 0 − (−1) = +1

Here the SLO front **bends** in the EPF dimension: under EPF, tightening fairness no
longer produces an additional SLO drop (SLO is already failing). This is a small but
non‑zero Δ‑curvature.

We can define a cell‑level “bend”:

- Δ_bend(cell) = max(|K_fairness|, |K_slo|) = 1

In `stability_map_v0`, this can be stored as a diagnostic value for this 2×2 cell.

## 4. Example stability_map_v0 cell

Below is a self-contained Stability Map v0 fragment for this toy cell. It only uses
fields that are safe to add as optional extensions on top of the existing
`PULSE_stability_map_v0.schema.json`.

```jsonc
{
  "cells": [
    {
      "id": "cell_fairness_slo_epf_demo",
      "profile": "prod_v_demo",
      "dataset_snapshot": "logs_demo_2025Q1",

      "axes": {
        "a": { "name": "fairness_threshold", "values": [0, 1] },
        "b": { "name": "epf_enabled",         "values": [0, 1] }
      },

      "runs": {
        "x00": "run_loose_epf0",
        "x10": "run_strict_epf0",
        "x01": "run_loose_epf1",
        "x11": "run_strict_epf1"
      },

      "gates": {
        "q3_fairness_ok": {
          "values": { "x00": 0, "x10": 1, "x01": 0, "x11": 1 },
          "delta_a_b0": 1,
          "delta_a_b1": 1,
          "K": 0
        },
        "q4_slo_ok": {
          "values": { "x00": 1, "x10": 0, "x01": 0, "x11": 0 },
          "delta_a_b0": -1,
          "delta_a_b1": 0,
          "K": 1
        }
      },

      "delta_bend": 1,
      "tags": ["topology_demo_v0", "fairness_vs_slo", "epf_interaction"]
    }
  ]
}
