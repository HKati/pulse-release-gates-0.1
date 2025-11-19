# PULSE EPF shadow pipeline v0 – quickstart

Status: v0, shadow-only  
Audience: developers who already run the PULSE Topology v0 pipeline and want
to try the EPF + paradox field layer without changing gate logic.

This is a minimal, command-level quickstart. For full details, see:

- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PULSE_paradox_field_v0_walkthrough.md`
- `docs/PULSE_paradox_field_v0_case_study.md`

---

## 1. Prerequisites

You should already have a working PULSE topology pipeline that produces:

- `stability_map.json` (Topology v0 + Stability Map v0), and
- optionally EPF-related fields (`epf.available`, `epf.L`, `epf.shadow_pass`).

How you obtain `stability_map.json` is out of scope for this quickstart;
see `docs/PULSE_topology_v0_methods.md` for the topology pipeline.

All commands below are intended to be run from the repo root.

---

## 2. Single-run EPF shadow pipeline

This section shows the minimal set of commands to project the EPF signal and
paradox field onto a single run, and produce a decision-level summary.

### Step 1 – Enrich Stability Map with paradox / EPF field

```bash
python PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py \
  --map stability_map.json
