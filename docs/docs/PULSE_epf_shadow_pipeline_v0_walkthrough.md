# PULSE EPF shadow pipeline v0 – walkthrough

Status: **v0, shadow-only**  
Scope: Stability Map v0 + Decision Engine v0 + paradox / EPF field

This document explains how the EPF signal is integrated into PULSE as an
_external sensor_ and how it appears in the Topology / Stability Map /
Decision Engine outputs, without changing any gate logic.

The goal is to make the EPF field visible as a **paradox / tension field**,
not as an extra hard-coded gate.

---

## 1. High-level picture

The EPF shadow integration in v0 is a 3-step pipeline:

1. **Topology / Stability Map v0**

   - `stability_map.json` is generated as before (Topology v0).
   - Then we enrich each `ReleaseState` with:
     - `paradox_field_v0`
     - `epf_field_v0`

2. **Decision Engine v0 (shadow-only view)**

   - We build `decision_output_v0.json` on top of the Stability Map.
   - It exposes:
     - the selected `ReleaseState`,
     - the paradox/EPF field,
     - a minimal `decision_trace[]` with a `paradox_stamp`,
     - a `dual_view` with a `paradox_panel_v0`.

3. **Summary / dashboard view**

   - We build a compact summary JSON:
     - `decision_output_v0_summary.json`
   - It is a "headline" view: decision + stability + paradox/EPF field.

At no point do we modify the release gate decision tree. The EPF field is
a **shadow layer** on top of the existing logic.

---

## 2. Inputs and prerequisites

The pipeline assumes the existing PULSE topology / gate machinery already
produces:

- `status.json`
- (optionally) `status_epf.json`
- `stability_map.json` via `build_stability_map_v0.py`

Additionally, the Stability Map schema was extended:

- `schemas/PULSE_stability_map_v0.schema.json` now allows, per `ReleaseState`:
  - `paradox_field_v0`
  - `epf_field_v0`

Existing fields (`rdsi`, `epf`, `instability`, `paradox`, etc.) and their
semantics are unchanged.

---

## 3. Step 1 – Enrich Stability Map with paradox/EPF field

**Tool:**

```text
PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py
