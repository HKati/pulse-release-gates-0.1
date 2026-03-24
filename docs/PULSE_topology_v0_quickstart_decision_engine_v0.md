# PULSE topology v0 quickstart: Decision Engine v0

> Fastest practical path from one deterministic baseline run to one compact Decision Engine summary artifact.

This quickstart shows how to use the current Decision Engine surface without blurring the repository’s release-semantics boundary.

This page does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`
- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`

## Important boundary

- the deterministic baseline artifacts carry the recorded run outcome
- Decision Engine is optional and diagnostic
- Decision Engine outputs are compact summaries; they do not silently rewrite release policy
- missing optional context must remain explicit (missing ≠ stable)

For the broader conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_engine_v0.md`

For EPF/paradox triage, see:

- `docs/PARADOX_RUNBOOK.md`
- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`

---

## 1. What this quickstart is for

Use this page if you want the fastest route from:

- one deterministic baseline run

to:

- one compact, dashboard-friendly `decision_engine_v0.json` artifact.

This quickstart is intentionally practical:

- start from the baseline `status.json`
- add optional context only if you already have it
- produce a compact decision artifact for dashboards, triage notes, or handoff

---

## 2. Minimum artifact chain

The minimum required input is:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

That baseline artifact is non-negotiable.

Recommended companion:

- `PULSE_safe_pack_v0/artifacts/report_card.html`

Optional enrichments are:

- `paradox_field_v0.json`
- `stability_map_v0*.json` (demo/topology surface)
- EPF shadow A/B artifacts (when relevant)
- other diagnostic overlays that remain artifact-derived

Reading order (evidence-trace order):

1. baseline artifacts first
2. optional diagnostics next
3. Decision Engine output last as a compact summary

---

## 3. Fastest path

### Step 1 — Produce the deterministic baseline

From repo root:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

Expected baseline artifacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

If you do not have a valid baseline `status.json`, stop here.

---

### Step 2 — Optionally generate paradox context

If you want paradox/field context in the Decision Engine input chain:

```bash
mkdir -p out

python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
  --status-dir PULSE_safe_pack_v0/artifacts \
  --output out/paradox_field_v0.json
```

This gives you an optional:

```text
out/paradox_field_v0.json
```

Use it when you want recurring tension/conflict structure to inform the compact summary.

---

### Step 3 — Optionally prepare stability-map context

If you already have a `stability_map_v0`-style artifact (for example from the demo/topology path), keep it alongside the baseline artifact.

Typical example name:

```text
out/stability_map_v0_demo.json
```

If you want the demo artifact:

```bash
python PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py \
  --output out/stability_map_v0_demo.json
```

Important nuance:

- the safe-pack may also emit `PULSE_safe_pack_v0/artifacts/epf_stability_map_v0.json`
- that file is a different diagnostic surface and is **not** the same schema as the `stability_map_v0` demo input expected by Decision Engine’s `--stability-map`

If you do not have a real stability-map artifact, skip this step. Missing optional context is better than fabricated context.

---

### Step 4 — Run the Decision Engine

Output target:

```text
out/decision_engine_v0.json
```

#### Baseline only

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --output out/decision_engine_v0.json
```

#### Baseline + paradox field (optional)

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --paradox-field out/paradox_field_v0.json \
  --output out/decision_engine_v0.json
```

#### Baseline + stability-map demo + paradox field (optional)

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --stability-map out/stability_map_v0_demo.json \
  --paradox-field out/paradox_field_v0.json \
  --output out/decision_engine_v0.json
```

Tip:

- if you ever suspect the CLI changed, you can still confirm via:

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py --help
```

---

## 4. Minimal operating modes

You do not need the full topology stack to get value.

### Mode A — Baseline only

Inputs:

- `status.json`

Good for:

- the smallest possible compact summary
- proving the Decision Engine path works
- demos and handoff notes

Tradeoff:

- least context-rich interpretation

---

### Mode B — Baseline + paradox field

Inputs:

- `status.json`
- `paradox_field_v0.json`

Good for:

- making conflict/tension structure visible in compact form
- more honest summaries for fragile-looking runs

Tradeoff:

- still no dedicated stability-map context

---

### Mode C — Baseline + stability map + paradox field

Inputs:

- `status.json`
- `stability_map_v0*.json`
- `paradox_field_v0.json`

Good for:

- richer compact summaries
- stability posture + tension posture together
- dashboards and exploration

Tradeoff:

- more moving pieces to archive and explain

---

## 5. What the output is for

A typical Decision Engine output compresses a run into a compact posture label set.

Common fields include:

- `release_state` (e.g. `BLOCK`, `STAGE_ONLY`, `PROD_OK`, `UNKNOWN`)
- `stability_type` (e.g. `stable_good`, `unstably_good`, `stable_bad`, `unstably_bad`, `boundary*`, `unknown`)

Interpretation rule:

- these are diagnostic compact summaries
- they are **not automatically the same thing as the normative release decision**

---

## 6. How to read the result

Recommended reading order:

1. Read the deterministic baseline first
   - `status.json`
   - `report_card.html`

2. Inspect optional diagnostic context (if present)
   - paradox field
   - Stability Map demo artifact
   - EPF shadow outputs, when relevant

3. Read `decision_engine_v0.json` last as a compact summary

This keeps the summary anchored to evidence.

---

## 7. Example interpretation patterns

### Baseline PASS + calm diagnostics

Possible summary:

```text
release_state: PROD_OK
stability_type: stable_good
```

Meaning:

- positive baseline
- low diagnostic concern

---

### Baseline PASS + fragility/paradox pressure

Possible summary:

```text
release_state: PROD_OK
stability_type: unstably_good
```

Meaning:

- deterministic baseline still passes
- the compact label stays `PROD_OK`
- but `unstably_good` signals that caution is more honest than routine confidence

---

### Baseline FAIL

Possible summary:

```text
release_state: BLOCK
stability_type: stable_bad  (or unstably_bad)
```

Meaning:

- the baseline still governs
- optional overlays may explain failure posture, but do not silently undo it

---

## 8. What remains normative

Keep this boundary stable:

- deterministic gates remain authoritative for release semantics
- Decision Engine remains a compact diagnostic summarizer
- optional overlays enrich interpretation, not policy
- missing diagnostic artifacts must never become silent PASS signals

If a Decision Engine summary and the deterministic baseline disagree, the baseline wins.

---

## 9. Recommended archive bundle

For any run where the Decision Engine output matters, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- `out/decision_engine_v0.json`
- `out/paradox_field_v0.json`, when produced
- `out/stability_map_v0_demo.json`, when produced
- EPF shadow artifacts, when relevant
- any short note derived from the same run

This makes the summary reconstructible later.

---

## 10. Common mistakes to avoid

Do **not**:

- run the Decision Engine without a real baseline `status.json`
- treat a compact summary as a silent policy rewrite
- assume missing overlays imply calm/stable behavior
- fabricate optional artifacts just to make the output look richer
- skip baseline artifacts and read only the compact summary

The compact summary is useful **only when the evidence chain under it is real**.

---

## 11. Summary

Fastest honest path:

1. produce a deterministic baseline
2. optionally add paradox / stability context
3. run the Decision Engine
4. read the result as a compact diagnostic summary, not as a replacement for policy
