# Paradox Gate triage SVG v0 (shadow)

This repo produces a small **diagnostic (shadow-only)** SVG (“Paradox diagram v0”) from the Paradox Gate triage summary.
It is **not a release gate** and **does not block merges**.

> Canonical doc filename: `docs/paradox_gate_triage_svg_v0.md`.
>
> This page documents the shadow SVG triage flow (`paradox_diagram_input_v0.json` → `paradox_diagram_v0.svg`) used by Paradox Gate diagnostics.

## What it is
- A compact visualization of key Paradox Gate metrics:
  - `settle_time_p95_ms` vs `settle_time_budget_ms`
  - `downstream_error_rate`
  - `paradox_density`
- Intended for quick PR triage / trend spotting.

## Where it is produced
In GitHub Actions, the Paradox Gate (shadow) workflow:
- Writes an input JSON artifact:
  - `PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json`
- Validates it with the contract checker:
  - `scripts/check_paradox_diagram_input_v0_contract.py`
- Renders the SVG (best-effort) if the contract passes:
  - `tools/render_paradox_diagram_v0.py`
  - Output: `PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg`

## Input contract
The canonical schema is:
- `schemas/paradox_diagram_input_v0.schema.json`

A concrete example is:
- `schemas/examples/paradox_diagram_input_v0.example.json`

Contract checker (stdlib-only):
- `scripts/check_paradox_diagram_input_v0_contract.py`

Notes:
- Metrics are validated strictly (e.g., booleans are rejected for numeric fields).
- `decision_raw` is provenance/debug and may be `null` when unavailable (schema/contract aligned).

## Run locally

Validate the example:

    python scripts/check_paradox_diagram_input_v0_contract.py \
      --in schemas/examples/paradox_diagram_input_v0.example.json

Render the SVG:

    python tools/render_paradox_diagram_v0.py \
      --in schemas/examples/paradox_diagram_input_v0.example.json \
      --out /tmp/paradox_diagram_v0.svg

## Shadow-only behavior
- Contract failures should emit warnings/diagnostics but should not block merges.
- Rendering is best-effort and should be skipped if the contract check did not succeed.
