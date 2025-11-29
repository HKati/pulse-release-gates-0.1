# Drift and governance overview (v0)

This document sketches how PULSE can be used as part of a broader
drift/governance story, and what is currently *in scope* vs *out of
scope* for the repository.

It is intentionally high-level: it does not prescribe a single drift
monitoring stack, but outlines how existing PULSE signals can be
combined over time.

---

## What we call "drift"

In this context, "drift" can refer to several related phenomena:

- **Model drift** – the behaviour of a model changes over versions
  (e.g. new checkpoint, new fine-tuning) in ways that affect safety or
  quality metrics.
- **Data / workload drift** – the distribution of inputs or use cases
  shifts (e.g. new languages, domains, or prompt patterns).
- **Policy drift** – the gate policies, thresholds or profiles change
  over time (intentionally or accidentally).
- **Tooling drift** – changes in evaluation tooling, detectors or
  reference datasets that affect measured metrics.

PULSE does not attempt to "freeze" any of these, but aims to make
changes **observable and auditable** via:

- deterministic, fail-closed gates,
- the Quality Ledger,
- per-run stability signals such as RDSI,
- optional external detectors and EPF experiments.

---

## Existing building blocks

Today, the repository already provides several components that are
useful for drift-aware governance:

- **Deterministic gates and policies**
  - Strict thresholds and profiles (`pulse_policy.yml`, `profiles/`)
    encode the current expectations.
  - Any change to these profiles is versioned and can be reviewed.

- **Quality Ledger**
  - Each CI run can produce a structured ledger of gate outcomes,
    reason codes and key metrics.
  - Over time, these ledgers form a history of model and policy
    behaviour.

- **RDSI (Release Decision Stability Index)**
  - Per-run stability signal under small perturbations.
  - Helps identify decisions that are fragile vs robust in the current
    configuration.
  - See `docs/RDSI_STABILITY_NOTES.md` for more detail.

- **EPF and paradox reporting**
  - Shadow evaluations near thresholds can surface cases where the
    deterministic gates and adaptive logic disagree.
  - `epf_report.txt` and `epf_paradox_summary.json` highlight gates
    that are borderline or potentially miscalibrated.
  - See `docs/PARADOX_RUNBOOK.md` for handling such cases.

- **External detectors (optional)**
  - External tools can add safety/quality signals that are either
    gating or advisory, depending on configuration.
  - See `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md` for details.

Taken together, these form a rich **audit trail** that drift analysis
can build on.

---

## What is *not* implemented (yet)

This repository does **not** ship a full drift monitoring or anomaly
detection system. In particular, it does not include:

- automatic time-series storage and dashboards for all metrics,
- built-in alerts when metrics or RDSI change beyond some global
  threshold over many runs,
- automatic adaptation of thresholds or policies based on observed
  drift.

All of these are deliberately left to higher-level governance systems
or to downstream integrations (e.g. internal dashboards, notebooks,
or external monitoring platforms).

---

## How to use PULSE data for drift (practical sketch)

Even without a dedicated drift service, you can start building a
drift-aware view of your system by:

1. **Persisting run artefacts**
   - Archive the Quality Ledger, RDSI outputs, and key status files
     for important runs (for example via your CI artefact storage,
     object storage, or Zenodo snapshots).
   - Tag snapshots with model version, dataset version, and policy
     version where applicable.

2. **Sampling a history window**
   - Periodically (e.g. weekly), sample a set of recent runs:
     - read their ledgers,
     - extract key metrics and RDSI values,
     - group by model/policy version.

3. **Looking for directional patterns**
   - For each metric of interest (e.g. groundedness, refusal rate):
     - plot or tabulate its values over the sampled runs,
     - look for monotonic trends (steady degradation or improvement).
   - For RDSI:
     - watch for sustained drops in stability over multiple runs.

4. **Combining with EPF/paradox signals**
   - Check whether gates that appear frequently in paradox reports or
     borderline states are also the ones drifting.
   - Use this to prioritise which policies to revisit first.

5. **Feeding back into governance**
   - When a drift pattern is identified and confirmed:
     - open a tracked change (issue/PR/ticket) describing:
       - what drift was observed,
       - which metrics/gates are affected,
       - what change is proposed (threshold adjustment, new tests,
         model rollback, etc.).
     - apply changes through the usual CI+review process so that the
       governance trail remains intact.

---

## Possible future directions

Future versions of PULSE or downstream systems could add more explicit
support for drift analysis, for example:

- a small CLI or library that:
  - ingests multiple Quality Ledgers and RDSI reports,
  - computes basic summaries and trend metrics,
  - exports data to plotting tools or dashboards.

- a "governance topology" layer that:
  - aggregates state from multiple repositories or services,
  - defines organisation-level drift policies,
  - provides a central view of model and gate evolution.

Those extensions are intentionally out of scope for the current
repository, but this document can serve as a design seed for such
work.

---

## Summary

- PULSE already provides several useful signals for drift-aware
  governance: deterministic gates, Quality Ledger, RDSI, EPF, and
  optional external detectors.
- The repository does **not** include a full drift monitoring
  solution; instead, it exposes rich artefacts that can be analysed
  over time.
- Drift analysis today is expected to be orchestrated by higher-level
  tools or manual workflows that consume these artefacts and feed
  results back into policy changes.

This keeps PULSE focused: it is a **reliable, auditable gate and
signal generator**, while broader, long-term drift handling remains a
responsibility of governance and monitoring layers built on top of it.
