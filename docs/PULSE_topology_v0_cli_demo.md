# PULSE Topology v0 – CLI demo

This document shows how to run the Topology v0 overlays **entirely from the CLI**,
without touching CI workflows.

The goal is to go from a baseline PULSE run to three additional artefacts:

- `paradox_field_v0.json` – paradox atoms over gates
- `stability_map_v0_demo.json` (optional) – a tiny demo stability map cell
- `decision_engine_v0.json` – a compact decision overlay with release + stability type

on top of a single `status.json` produced by the safe pack.

> **Scope:** this is a *demo* pipeline for exploration and governance.
> It does not change core PULSE gating or CI behaviour.

---

## 0. Prerequisites

From the repo root:

    pip install -r requirements.txt

(optionally in a virtual environment).

All commands below assume you run them from the repository root.

---

## 1. Run the PULSE safe pack (baseline status.json)

First, run the standard PULSE safe pack to produce a `status.json` artefact.

    python PULSE_safe_pack_v0/tools/run_all.py

This will populate:

- `PULSE_safe_pack_v0/artifacts/status.json`

The exact contents depend on your configuration, but we assume:

- `status.json` contains:
  - top-level `gates` → boolean gate flags,
  - optional `metrics` (e.g. RDSI-like metrics),
  - metadata about the run.

This is the **only required input** for the CLI demo.

---

## 2. Build paradox_field_v0 from status artefacts

Next, we mine paradox atoms from the gate patterns in one or more `status.json`
artefacts. For the simplest demo, we use the safe pack’s default `artifacts/`
directory as the source.

    python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
      --status-dir PULSE_safe_pack_v0/artifacts \
      --output PULSE_safe_pack_v0/artifacts/paradox_field_v0.json \
      --max-atom-size 4

This writes:

- `PULSE_safe_pack_v0/artifacts/paradox_field_v0.json`

with structure:

    {
      "paradox_field_v0": {
        "version": "PULSE_paradox_field_v0",
        "generated_at_utc": "...",
        "source": {
          "status_dir": "PULSE_safe_pack_v0/artifacts",
          "run_count": 1
        },
        "atoms": [
          {
            "atom_id": "atom_0000",
            "gates": ["quality.q3_fairness_ok", "slo.q4_slo_ok"],
            "minimal": true,
            "severity": 0.9
          }
        ]
      }
    }

Where:

- `atoms[]` are **paradox atoms**:
  - minimal unsatisfiable gate sets (MUS) in the local decision field.
- `severity` is a simple `[0,1]` score for how “hard” the paradox is
  (e.g. how often the atom appears across runs, or how extreme the tradeoff is).

You can inspect the file directly, for example:

    jq '.paradox_field_v0.atoms[0]' PULSE_safe_pack_v0/artifacts/paradox_field_v0.json

(or use any JSON viewer you prefer).

---

## 3. (Optional) Build a demo stability_map_v0

For a full Topology v0 picture, we also want a notion of **stability / curvature**
over a small region of the decision field. The demo tool constructs a synthetic
2×2 cell for the fairness–SLO–EPF example.

    python PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py \
      --output PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json

This writes:

- `PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json`

with structure like:

    {
      "stability_map_v0": {
        "version": "PULSE_stability_map_v0_demo",
        "generated_at_utc": "...",
        "cells": [
          {
            "id": "cell_fairness_slo_epf_demo",
            "profile": "demo_profile_v0",
            "dataset_snapshot": "logs_demo_2025Q1",
            "axes": {
              "alpha_fairness": [0.7, 0.8],
              "slo_budget": [0.9, 0.95]
            },
            "runs": { },
            "gates": { },
            "delta_bend": 1,
            "tags": [
              "topology_demo_v0",
              "fairness_vs_slo",
              "epf_interaction"
            ]
          }
        ]
      }
    }

Key field:

- `delta_bend` – a simple Δ‑curvature signal for that cell:
  - `0` → flat / linear region,
  - `>0` → curved / unstable region (e.g. fairness–SLO tradeoff with EPF).

You can inspect it with:

    jq '.stability_map_v0.cells[0]' PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json

> If you don’t care about stability yet, you can skip this step.
> Decision Engine v0 will still run, just with less topology signal.

---

## 4. Run Decision Engine v0

Now we combine:

- the core `status.json`,
- the optional `stability_map_v0_demo.json`,
- the optional `paradox_field_v0.json`

into a compact `decision_engine_v0.json` overlay.

### 4.1. With both stability map and paradox field

    python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
      --status PULSE_safe_pack_v0/artifacts/status.json \
      --stability-map PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json \
      --paradox-field PULSE_safe_pack_v0/artifacts/paradox_field_v0.json \
      --output PULSE_safe_pack_v0/artifacts/decision_engine_v0.json

### 4.2. Without stability map or paradox field

You can also run with only `status.json`:

    python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
      --status PULSE_safe_pack_v0/artifacts/status.json \
      --output PULSE_safe_pack_v0/artifacts/decision_engine_v0.json

In that case the corresponding summary sections in the output will be `null`, and
`stability_type` will be classified using only gate information.

---

## 5. Inspecting decision_engine_v0

The Decision Engine v0 output looks like:

    {
      "decision_engine_v0": {
        "version": "PULSE_decision_engine_v0",
        "generated_at_utc": "...",
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

You can inspect it with:

    jq '.decision_engine_v0' PULSE_safe_pack_v0/artifacts/decision_engine_v0.json

---

## 6. Interpreting release_state and stability_type

### 6.1. release_state

A coarse label derived from gate outcomes:

- `PROD_OK`  
  – no failed gates in `status.json`.
- `STAGE_ONLY`  
  – only a small fraction of gates fail.
- `BLOCK`  
  – many gates fail.
- `UNKNOWN`  
  – no gates found or gate data incomplete.

This does **not** change `check_gates.py` or CI decisions; it is a diagnostic
overlay for governance and dashboards.

### 6.2. stability_type

A combined label from:

- `release_state` (good / bad / boundary),
- topology signal:
  - `delta_bend_max` from `stability_map_v0`, and/or
  - `atom_count` / `severe_atom_count` from `paradox_field_v0`.

Intuition:

- If `release_state = "PROD_OK"` and we have **non-trivial topology**  
  (`delta_bend_max > 0` or `atom_count > 0`):

  - we label it as **`unstably_good`**:
    > “Green, but on a curved / paradox-rich region of the field.”

- If `release_state = "PROD_OK"` and the topology signal is flat / empty:

  - we label it as **`stable_good`**:
    > “Green and locally flat; no strong curvature or paradox atoms detected.”

- If `release_state = "BLOCK"` and topology is non-trivial:

  - we label it as **`unstably_bad`**:
    > “Blocked and also on a curved / paradox region.”

- If `release_state = "BLOCK"` and topology is flat:

  - we label it as **`stable_bad`**:
    > “Blocked but the failure is stable; the field around it is locally simple.”

- If `release_state = "STAGE_ONLY"`:

  - we use boundary labels (e.g. `boundary`, `boundary_simple`),
  - indicating the decision is on a frontier region (e.g. between Q₃ and Q₄ thresholds).

---

## 7. Using this in practice

Once you have:

- `status.json`
- `paradox_field_v0.json`
- `stability_map_v0_demo.json` (optional)
- `decision_engine_v0.json`

you can:

- feed them into dashboards,
- attach them to release reviews,
- track how often your releases land in:
  - `stable_good` vs `unstably_good` regions,
  - which paradox atoms keep reappearing (e.g. fairness vs SLO),
  - how the field curvature (`delta_bend`) evolves over time.

The key point is:

> Topology v0 turns a single “pass/fail” surface into an explicit decision field,
> with paradox atoms and stability structure that can be inspected, audited and
> governed.

This CLI demo is the simplest way to see that field *without* relying on CI
workflows.
