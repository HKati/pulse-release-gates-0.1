# PULSE topology v0 CLI demo

> Practical CLI demo path for the topology family on top of deterministic PULSE artifacts.

This page is for readers who want to see how the current topology-family tools fit together from the command line **without confusing demo outputs with the repository’s normative release path**.

This page does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`
- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`

## Important boundary

- deterministic baseline artifacts record the run outcome
- topology tools are optional and diagnostic
- demo artifacts are not policy surfaces
- missing optional artifacts remain explicitly missing (missing ≠ stable)

Related docs:

- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_v0_quickstart_decision_engine_v0.md`
- `docs/PULSE_decision_engine_v0.md`
- `docs/PARADOX_RUNBOOK.md`

---

## 1. What this demo is for

Use this page to:

- start from a real deterministic baseline (`status.json`)
- optionally generate paradox/field context
- optionally generate a Stability Map **demo** artifact
- run Decision Engine v0 against artifacts you actually have
- read the output as a compact diagnostic overlay (not a policy rewrite)

---

## 2. Prerequisites

You need:

- a checked-out repo
- Python available
- the safe-pack tools and artifacts directory present

This demo assumes you are running from the repo root.

---

## 3. Step 1 — Produce the deterministic baseline

From repo root:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

Expected baseline artifacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Optional additive diagnostic artifact that may also appear (safe-pack output):

- `PULSE_safe_pack_v0/artifacts/epf_stability_map_v0.json`

Stop here if `status.json` is missing — topology demos should not fabricate baseline artifacts.

Optional schema sanity check (if the validator exists in your repo snapshot):

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

---

## 4. Step 2 — Generate optional paradox context

Create an output directory:

```bash
mkdir -p out
```

Generate paradox field:

```bash
python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
  --status-dir PULSE_safe_pack_v0/artifacts \
  --output out/paradox_field_v0.json
```

Output:

- `out/paradox_field_v0.json`

Use this when you want conflict/tension structure to remain explicit rather than flattened into one gate result.

---

## 5. Step 3 — Generate a Stability Map demo artifact (optional)

This is a **demo-only** artifact used for topology exploration:

```bash
python PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py \
  --output out/stability_map_v0_demo.json
```

Output:

- `out/stability_map_v0_demo.json`

### Important nuance: two “stability-like” artifacts exist

- `PULSE_safe_pack_v0/artifacts/epf_stability_map_v0.json`  
  *Safe-pack additive diagnostic artifact (hazard/zone style).*

- `out/stability_map_v0_demo.json`  
  *Demo Stability Map v0 surface (cells + stability-map style fields).*

These are **not the same schema**.

Decision Engine’s `--stability-map` input currently expects the **stability_map_v0-style** shape (demo surface), so passing `epf_stability_map_v0.json` there will not produce meaningful stability-map summaries.

If you do not have a real stability-map artifact, skip this step.

---

## 6. Step 4 — Run Decision Engine v0

Decision Engine v0 is a compact diagnostic summary overlay derived from archived artifacts.

### Baseline only

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --output out/decision_engine_v0.json
```

### Baseline + paradox field (optional)

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --paradox-field out/paradox_field_v0.json \
  --output out/decision_engine_v0.json
```

### Baseline + stability-map demo + paradox field (optional)

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --stability-map out/stability_map_v0_demo.json \
  --paradox-field out/paradox_field_v0.json \
  --output out/decision_engine_v0.json
```

Output:

- `out/decision_engine_v0.json`

If you ever suspect CLI drift, confirm flags via:

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py --help
```

---

## 7. Reading order (recommended)

This demo stays honest if you read artifacts in evidence-trace order:

1. `PULSE_safe_pack_v0/artifacts/status.json`
2. `PULSE_safe_pack_v0/artifacts/report_card.html`
3. optional `out/paradox_field_v0.json`
4. optional `out/stability_map_v0_demo.json`
5. `out/decision_engine_v0.json`

The compact summary is useful **only when the evidence chain beneath it is real**.

---

## 8. Minimal demo modes

You do not need every optional overlay.

### Mode A — Baseline only

Inputs:

- `status.json`

Outputs:

- `decision_engine_v0.json`

Best for:

- fastest “does it run?” demo
- smallest archive bundle

### Mode B — Baseline + paradox field

Inputs:

- `status.json`
- `paradox_field_v0.json`

Best for:

- making conflict/tension structure visible in compact form

### Mode C — Baseline + stability-map demo + paradox field

Inputs:

- `status.json`
- `stability_map_v0_demo.json`
- `paradox_field_v0.json`

Best for:

- richer stability posture demonstrations and exploration

---

## 9. Common mistakes to avoid

Do **not**:

- run Decision Engine without a real baseline `status.json`
- treat demo stability artifacts as policy surfaces
- pass `epf_stability_map_v0.json` as `--stability-map` and assume it means the same thing
- assume missing overlays imply stability or low risk
- archive only the compact summary without the baseline artifacts

---

## 10. Recommended archive bundle

If the demo produces something worth keeping, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- `out/decision_engine_v0.json`
- optional `out/paradox_field_v0.json`
- optional `out/stability_map_v0_demo.json`
- optional `PULSE_safe_pack_v0/artifacts/epf_stability_map_v0.json` (if present)

This keeps later reconstruction straightforward.

---

## 11. Summary

Shortest honest CLI demo path:

1. produce a deterministic baseline
2. optionally generate paradox context
3. optionally generate a Stability Map demo artifact
4. run Decision Engine against real artifacts
5. interpret the output as a diagnostic overlay, not a policy rewrite
