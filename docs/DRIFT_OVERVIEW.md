# Drift and governance overview (v0)

> High-level note on how PULSE artefacts can support drift-aware governance.
> This page is descriptive, not a second decision engine.

For normative release semantics, use:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`

---

## 1. What we mean by “drift”

In this repository, “drift” can refer to several related but distinct changes:

- **Model drift**
  - model behaviour changes across versions, checkpoints, or fine-tuning updates.

- **Data / workload drift**
  - the input mix changes over time:
    - new prompt patterns,
    - new languages,
    - new customer segments,
    - new usage scenarios.

- **Policy drift**
  - release meaning changes because thresholds, required gates, or profiles change.

- **Tooling drift**
  - evaluator, detector, dataset, or contract changes alter what gets measured.

PULSE does not try to freeze all of these.
Instead, it tries to make them **observable, auditable, and reviewable** via
immutable run artefacts.

---

## 2. What PULSE already gives you today

PULSE already emits several artefacts that are useful for drift-aware
governance.

### Deterministic release state

The central machine-readable artefact is:

- `PULSE_safe_pack_v0/artifacts/status.json`

This is the most important anchor for later drift analysis, because it records
the gate outcomes and measured signals for one concrete run.

### Human-readable review surface

The corresponding human-readable artefact is:

- `PULSE_safe_pack_v0/artifacts/report_card.html`

This Quality Ledger is useful when humans need to compare runs, inspect
failures, and archive review context.

### Policy-grounded release meaning

The repository’s release meaning is grounded in:

- `pulse_gate_policy_v0.yml`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `.github/workflows/pulse_ci.yml`

This matters for drift work because “the model changed” and “the policy changed”
are not the same story.

### Optional external evidence

External detector summaries can be folded into the final status artefact.

This makes it possible to track, over time:

- whether external evidence was present,
- whether it passed overall,
- and whether detector results themselves are trending.

### EPF / paradox shadow artefacts

The EPF shadow path can emit comparison artefacts such as:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

These are especially useful when drift shows up first as borderline or unstable
behaviour near thresholds.

---

## 3. What this repository does *not* implement (yet)

This repository does **not** currently ship a full long-horizon drift monitoring
system.

In particular, it does not include:

- a built-in multi-run metrics store,
- automatic time-series dashboards for all gates and metrics,
- automatic alerts on long-horizon drift,
- autonomous threshold adaptation,
- automatic policy rewriting based on observed trends.

Those responsibilities are intentionally left to higher-level governance,
analytics, or monitoring layers built on top of archived PULSE artefacts.

---

## 4. Practical drift questions you can already answer

Even without a dedicated drift platform, archived PULSE runs can already help
answer questions such as:

- Did a newer model version start failing `q1_grounded_ok` more often?
- Did `q4_slo_ok` become less stable after an infrastructure change?
- Are refusal-delta or RDSI signals weakening over recent runs?
- Are external detectors appearing more often, or failing more often?
- Are EPF paradox candidates clustering around the same gate?
- Did a release outcome change because of model/data behaviour, or because the
  policy changed?

This is already useful governance value, even before adding a full trend system.

---

## 5. Recommended drift-aware workflow

A practical low-friction workflow is:

1. **Archive important run artefacts**
   - at minimum:
     - `status.json`
     - `report_card.html`
   - and, when relevant:
     - external detector summaries
     - EPF / paradox artefacts
     - optional JUnit / SARIF exports

2. **Tag runs with provenance**
   - model version
   - dataset version
   - policy version / commit
   - release context

3. **Compare history windows**
   - sample a recent window of runs,
   - group by model / policy / environment,
   - compare key metrics and gate outcomes.

4. **Separate signal types**
   - behaviour drift,
   - policy drift,
   - tooling drift,
   - evidence-availability drift.

5. **Feed conclusions back through normal review**
   - if drift is real and important:
     - open an issue / PR / tracked change,
     - document the observed pattern,
     - update policy or tests through the normal fail-closed review path.

This keeps drift handling auditable instead of ad hoc.

---

## 6. External evidence nuance

For drift work, external detector evidence has two separate questions:

### A. Was evidence present at all?

This is about summary presence / parseability.

### B. Did the folded evidence pass overall?

This is about aggregate detector outcome.

These are not the same thing.

When you study external-detector drift, do not look only at aggregate pass/fail.
Also track whether evidence was actually present and usable.

For release-grade workflows, strict evidence requirements should be enabled
explicitly rather than inferred indirectly.

---

## 7. EPF and paradox as drift prioritisation signals

EPF / paradox artefacts are useful not because they replace deterministic gates,
but because they can highlight **where drift pressure is accumulating**.

Good examples:

- a gate that still passes deterministically, but increasingly shows paradox
  candidates in shadow mode,
- a threshold that repeatedly flips under small perturbations,
- a quality metric that is technically passing but becoming operationally fragile.

That makes EPF/paradox a prioritisation surface for humans:

- which thresholds need review,
- which evaluations need richer coverage,
- which model changes deserve rollback or staging-only treatment.

---

## 8. Recommended archive bundle for drift/governance work

For important runs, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- the policy version / commit that governed the run
- external detector summaries, when used
- EPF / paradox artefacts, when produced
- any human review note, waiver, or release decision record

This makes later reconstruction much easier.

---

## 9. Future directions

Reasonable future extensions could include:

- a small history CLI that ingests multiple `status.json` files,
- drift summaries across a rolling window of runs,
- trend views for RDSI, refusal-delta, and key quality gates,
- organisation-level governance dashboards spanning multiple repos or services.

Those are natural next layers, but they are intentionally outside the current
repository’s core scope.

---

## 10. Summary

Today, PULSE is best understood as:

- a **deterministic release-state generator**,
- an **artifact-first review surface**,
- and a **good substrate for drift-aware governance**.

It is **not** yet a full drift monitoring platform.

That separation is healthy:
PULSE produces trustworthy run artefacts,
while long-horizon drift handling can be built on top of them without changing
the core release semantics.
