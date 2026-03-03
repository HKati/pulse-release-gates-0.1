# PULSE topology v0 quickstart: Decision Engine v0

> Fastest practical path to a reviewer-facing Decision Engine summary on top of
> deterministic PULSE artifacts.

This quickstart shows how to use the current Decision Engine surface without
blurring the repository’s normative boundary.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- the Decision Engine is optional and diagnostic
- Decision Engine outputs summarize reviewer posture; they do not silently
  rewrite release policy

For the broader conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_overview_v0.md`

For the EPF/paradox side, see:

- `docs/PARADOX_RUNBOOK.md`
- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`

---

## 1. What this quickstart is for

Use this page if you want the fastest route from:

- one deterministic baseline run

to:

- one compact, reviewer-facing topology summary

using the current Decision Engine surface.

This quickstart is intentionally practical:

- start from the baseline `status.json`
- add optional context only if you already have it
- produce a compact decision artifact for dashboards, review notes, or handoff

---

## 2. Minimum artifact chain

The minimum required input is:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

That baseline artifact is non-negotiable.

Optional enrichments are:

- `paradox_field_v0.json`
- `stability_map_v0*.json`
- other topology/diagnostic overlays that remain artifact-first

The idea is simple:

- baseline first
- optional context second
- Decision Engine summary last

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
The Decision Engine should not be treated as authoritative without it.

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

```
out/paradox_field_v0.json
```

Use it when you want conflict/tension structure to inform the reviewer summary.

---

### Step 3 — Optionally prepare stability-map context

If you already have a Stability Map artifact from the repo’s demo/topology path,
keep it alongside the baseline artifact.

Typical example name:

```
stability_map_v0_demo.json
```

This is optional.

Do not invent a fake stability-map file just to satisfy the Decision Engine.  
Missing optional context is better than fabricated context.

---

### Step 4 — Inspect the live Decision Engine CLI

Before running the tool, inspect the current live CLI in your checkout:

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py --help
```

This is the safest quickstart because the artifact contract is more stable than
any one branch’s exact CLI flag spelling.

What matters methodologically is:

- required baseline input: `status.json`
- optional inputs: Stability Map / paradox field overlays
- output: `decision_engine_v0.json`

---

### Step 5 — Run the Decision Engine with the artifacts you actually have

Run the Decision Engine against:

- the required baseline `status.json`
- optional `paradox_field_v0.json`, if present
- optional `stability_map_v0*.json`, if present

Output target:

```
decision_engine_v0.json
```

The exact CLI flags should follow the live `--help` output in your checked-out tree.

---

## 4. Minimal operating modes

You do not need the full topology stack to get value.

### Mode A — Baseline only

Inputs:

- `status.json`

Good for:

- the smallest possible reviewer-facing summary
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

- showing recurring tension/conflict structure
- making fragile runs easier to summarize honestly

Tradeoff:

- still no dedicated Stability Map context

---

### Mode C — Baseline + Stability Map + paradox field

Inputs:

- `status.json`
- `stability_map_v0*.json`
- `paradox_field_v0.json`

Good for:

- richer reviewer-facing summaries
- stability posture + tension posture together
- dashboards and governance prototypes

Tradeoff:

- more moving pieces to archive and explain

---

## 5. What the output is for

A typical Decision Engine output is meant to compress a run into a compact,
reviewer-facing posture.

Common fields may include summaries such as:

- `release_state`
  - e.g. `BLOCK`, `STAGE_ONLY`, `PROD_OK`, `UNKNOWN`

- `stability_type`
  - e.g. `stable_good`, `unstably_good`, `stable_bad`, `unstably_bad`

Interpretation rule:

these are diagnostic review summaries.  
They are **not automatically the same thing as the normative release decision**.

That distinction matters a lot.

---

## 6. How to read the result

A good reading order is:

1. read the deterministic baseline first  
   - `status.json`  
   - `report_card.html`

2. inspect optional diagnostic context  
   - paradox field  
   - Stability Map  
   - EPF shadow outputs, if relevant

3. read the Decision Engine output last  
   as a compact summary of reviewer posture

This keeps the summary anchored to evidence.

---

## 7. Example interpretation patterns

### Baseline PASS + calm diagnostics

Possible summary:

```
release_state: PROD_OK
stability_type: stable_good
```

Meaning:

- positive baseline
- low reviewer concern
- ordinary confidence

---

### Baseline PASS + fragility/paradox pressure

Possible summary:

```
release_state: STAGE_ONLY
stability_type: unstably_good
```

Meaning:

- still positive deterministically
- but reviewer caution is more honest than routine production confidence

---

### Baseline FAIL

Possible summary:

```
release_state: BLOCK
stability_type: stable_bad or unstably_bad
```

Meaning:

- the baseline still governs
- optional overlays may explain the failure posture, but do not silently undo it

---

## 8. What remains normative

Keep this boundary stable:

- the deterministic gate path remains authoritative
- the Decision Engine remains a reviewer-facing summarizer
- optional overlays enrich interpretation, not policy
- missing diagnostic artifacts must never become silent PASS signals

If a Decision Engine summary and the deterministic baseline disagree,  
the baseline wins.

---

## 9. Recommended archive bundle

For any run where the Decision Engine output matters, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- `decision_engine_v0.json`
- `paradox_field_v0.json`, when produced
- `stability_map_v0*.json`, when produced
- EPF shadow artifacts, when relevant
- any short reviewer note derived from the same run

This makes the summary reconstructible later.

---

## 10. Common mistakes to avoid

Do **not**:

- run the Decision Engine without a real baseline `status.json`
- treat a reviewer-facing summary as a silent policy rewrite
- assume missing overlays imply calm/stable behavior
- fabricate optional artifacts just to make the output look richer
- skip the baseline artifacts and read only the compact decision summary

The compact summary is useful **only when the evidence chain under it is real**.

---

## 11. Summary

The fastest honest path is:

1. produce a deterministic baseline
2. optionally add paradox / stability context
3. run the Decision Engine
4. read the result as a reviewer-facing summary, not as a replacement for policy

That is where Decision Engine v0 is most useful today:

- dashboards
- governance notes
- reviewer handoff
- and compact “what posture does this run deserve?” summaries
