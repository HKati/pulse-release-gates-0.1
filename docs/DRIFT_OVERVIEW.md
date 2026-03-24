# PULSE drift overview (v0)

> High-level overview of how to read drift over archived PULSE run artifacts.

This note explains how drift can be studied from archived PULSE artifacts without silently rewriting release semantics.

It shows:

- what kinds of drift matter in this repository
- which archived artifacts already support drift reads
- how EPF, paradox, and topology help preserve drift-relevant structure
- what remains outside the current repository scope

It does not define release semantics. For normative release meaning, use:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`

Important boundary:

- deterministic archived artifacts carry the recorded release result for each run
- drift reads remain artifact-derived
- drift summaries do not silently mutate release semantics
- missing or degraded evidence remains explicit
- the same release polarity may correspond to different stability states across runs

For topology-facing drift reads, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_epf_hook_v0.md`

For EPF/paradox comparison and triage, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PARADOX_RUNBOOK.md`

---

## 1. What "drift" means here

In this repository, "drift" can refer to several related but distinct changes.

### A. Model drift

Model behavior changes across versions, checkpoints, adapters, or fine-tuning updates.

### B. Data or workload drift

The input mix changes over time, for example:

- new prompt patterns
- new languages
- new customer segments
- new usage scenarios

### C. Policy drift

Release meaning changes because thresholds, required gates, profiles, or explicit contract rules change.

### D. Tooling drift

Evaluator, detector, dataset, parser, or contract changes alter what gets measured or how results are materialized.

### E. Evidence-availability drift

The set of available signal families changes across runs, for example because an external summary is missing, degraded, or newly present.

### F. Stability or boundary drift

The recorded release polarity may stay the same while the surrounding field condition changes, for example from stable to boundary-close, pressure-loaded, or paradox-bearing.

These are not the same story.

A useful drift read keeps them separated instead of flattening them into one generic "the system changed" claim.

---

## 2. Why archived artifacts are the right drift surface

Drift is easiest to study honestly when it is anchored to archived run artifacts.

That matters because archived artifacts let you:

- compare concrete runs rather than vague memories of runs
- separate model or workload changes from policy or tooling changes
- keep missing evidence explicit
- reconstruct why an outcome changed
- preserve both machine-readable and human-readable history

This is why drift in PULSE should be read as an artifact-first historical comparison surface, not as a hidden live policy layer.

---

## 3. Current repo-level drift surfaces

The current repository already emits several useful drift surfaces.

### 3.1 Deterministic run artifacts

The primary single-run anchors are:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

These give you the recorded release result, gate outcomes, measured signals, and a human-readable review surface for one concrete run.

### 3.2 Normative release context

When you compare runs for drift, you also need the release-semantics context that governed them.

The key normative references are:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`

This matters because "the model changed" and "the policy changed" are different explanations.

### 3.3 External evidence surfaces

When external detector summaries are present and folded into the run outputs, they become useful drift signals.

They let you track, over time:

- whether external evidence was present
- whether folded evidence passed overall
- whether detector behavior itself appears to be changing

Presence and aggregate pass/fail should be tracked separately.

### 3.4 EPF shadow and paradox surfaces

The EPF shadow path can produce comparison artifacts such as:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

These are especially useful when drift first appears as threshold fragility, repeated disagreement, or local instability near a boundary.

### 3.5 Topology-facing drift surfaces

When topology-related artifacts are materialized, they add another useful drift surface.

Relevant artifacts may include:

- `stability_map_v0*.json`
- `paradox_field_v0.json`
- `decision_engine_v0.json`

These help preserve distinctions that flat PASS/FAIL history does not carry on its own, including:

- stability
- evidence completeness
- boundary pressure
- paradox concentration
- structurally stressed but still technically passing or failing regions

---

## 4. What the repository does not implement yet

This repository does not currently ship a full long-horizon drift monitoring system.

In particular, it does not include:

- a built-in multi-run metrics store
- general time-series dashboards for all gates and metrics
- automatic long-horizon drift alerts
- autonomous threshold adaptation
- automatic policy rewriting from observed trends
- a fully general history CLI for all artifact families

Those can be built on top of archived PULSE artifacts, but they are outside the current core scope.

---

## 5. Practical drift questions you can already answer

Even without a dedicated drift platform, archived PULSE runs can already help answer questions such as:

- Did a newer model version start failing `q1_grounded_ok` more often?
- Did `q4_slo_ok` become less stable after an infrastructure change?
- Are refusal-delta or RDSI signals weakening over recent runs?
- Are external detectors appearing more often, or failing more often?
- Are EPF disagreement or paradox candidates clustering around the same gate?
- Is the same release polarity becoming more boundary-close or pressure-loaded over time?
- Did an outcome change because of model or workload behavior, or because the policy changed?
- Did tooling or evidence availability change what was measurable?

That is already useful drift-analysis value even before adding a full trend system.

---

## 6. Recommended artifact-first drift workflow

A practical low-friction workflow is:

1. Archive important run artifacts
   - at minimum:
     - `status.json`
     - `report_card.html`
   - and, when relevant:
     - external detector summaries
     - EPF or paradox artifacts
     - topology artifacts
     - optional JUnit or SARIF exports

2. Tag runs with provenance
   - model version
   - dataset version
   - policy version or commit
   - environment or infrastructure context
   - release context

3. Compare paired runs or history windows
   - sample a recent run window
   - group by model, policy, dataset, or environment
   - compare gate outcomes and measured signals

4. Separate signal types
   - behavior drift
   - policy drift
   - tooling drift
   - evidence-availability drift
   - stability or boundary drift

5. Preserve structural differences, not just polarity
   - note whether the same polarity became more fragile
   - note whether paradox or pressure concentrated in one region
   - note where evidence became weaker or more incomplete

6. Feed conclusions back through normal reviewed paths
   - if drift is real and important:
     - open an issue or PR
     - document the observed pattern
     - update policy, tests, or tooling through explicit reviewed changes

This keeps drift handling auditable instead of ad hoc.

---

## 7. External evidence nuance

For drift work, external evidence has at least two separate questions.

### A. Was evidence present at all?

This is about summary presence, parseability, and basic usability.

### B. Did the folded evidence pass overall?

This is about aggregate detector outcome once evidence was available.

These are not the same thing.

When you study external-detector drift, do not look only at aggregate pass/fail.

Also track whether evidence was actually present and usable.

If a workflow needs strict evidence requirements, that should be enabled explicitly rather than inferred indirectly from drift summaries.

---

## 8. EPF, paradox, and topology as drift surfaces

EPF, paradox, and topology matter for drift work because they can reveal changes that flat release history hides.

### EPF shadow

Useful when:

- a threshold repeatedly flips under small perturbations
- the deterministic result stays the same but the run becomes fragile
- disagreement begins to recur near one boundary

### Paradox signals

Useful when:

- tension or conflict starts clustering in one gate family
- instability is recurring rather than isolated
- a run family starts to accumulate local contradiction pressure

### Topology and decision-field reads

Useful when:

- the same polarity starts moving from stable to unstable
- pressure or distortion concentrates even without a polarity flip
- evidence completeness changes across comparable runs
- a historically "passing" region becomes structurally stressed

These surfaces do not replace deterministic release semantics.

They make drift structurally legible.

---

## 9. Recommended archive bundle for drift work

For important runs, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- the policy version or commit that governed the run
- model, dataset, and environment provenance
- external detector summaries, when used
- EPF or paradox artifacts, when produced
- topology artifacts, when produced
- any tracked human review note or release record that depends on the run

This makes later reconstruction much easier.

---

## 10. Design invariants

A healthy drift layer keeps these invariants stable:

- drift reads remain artifact-derived
- deterministic archived artifacts carry the recorded release result
- missing evidence remains explicitly missing
- model or workload drift stays distinct from policy or tooling drift
- the same release polarity may correspond to different stability states
- drift summaries remain traceable to archived runs
- drift language must not become an implicit release-policy rewrite

---

## 11. Future directions

Reasonable future extensions could include:

- a small history CLI that ingests multiple `status.json` files
- rolling drift summaries across windows of runs
- trend views for RDSI, refusal-delta, and key quality gates
- multi-run views over EPF disagreement and paradox concentration
- organization-level dashboards spanning multiple repos or services

Those are natural next layers, but they are intentionally outside the current repository core.

---

## 12. Summary

Today, PULSE is best understood as:

- a deterministic release-artifact producer
- an artifact-first historical comparison surface
- a useful base for drift analysis across runs

It is not yet a full long-horizon drift monitoring platform.

That separation is healthy.

PULSE preserves concrete run evidence, and richer drift layers can be built on top of that evidence without silently changing release semantics.
