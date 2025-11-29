# Paradox & EPF runbook

This document describes what a human maintainer is expected to do when
the EPF experiment (shadow) workflow reports differences between the
baseline gates and the EPF shadow evaluation.

The EPF workflow is diagnostic only: it never changes CI outcomes, but
it **can** highlight paradox-like situations where the deterministic
gates and the adaptive shadow layer disagree.

---

## When does a "paradox" show up?

The `.github/workflows/epf_experiment.yml` job compares two views of
the gates:

- baseline decisions (from `status_baseline.json`), and
- EPF shadow decisions (from `status_epf.json`).

It then writes:

- `epf_report.txt` – a human-readable A/B diff, and
- `epf_paradox_summary.json` – a structured summary with:
  - `total_gates`
  - `changed`
  - a small list of example diffs.

In the GitHub Actions summary, you will see one of:

- `✅ EPF shadow run: no gate-level decision changes detected.`
- `⚠️ EPF shadow detected N gate(s) with different decisions than the baseline.`

We loosely refer to the latter case as a **paradox candidate**.

---

## Step 1 – Inspect the EPF artefacts

When you see the ⚠️ message:

1. Open the EPF experiment workflow run.
2. Download the `epf-ab-artifacts` bundle.
3. Inspect:
   - `epf_report.txt` – which gates changed?
   - `epf_paradox_summary.json` – how many gates, and what kind of diffs?

Typical patterns:

- `PASS → FAIL` or `FAIL → PASS` changes for a small number of gates,
- only gates near thresholds are affected,
- or EPF flags higher risk than the baseline gate.

---

## Step 2 – Classify the situation

For each changed gate, decide **what kind of tension** you are seeing.

Some common cases:

1. **EPF more strict than baseline**  
   - Baseline: `PASS`  
   - EPF: `FAIL` or higher risk  
   → EPF suggests the gate might be under-sensitive or too optimistic.

2. **EPF more lenient than baseline**  
   - Baseline: `FAIL`  
   - EPF: `PASS` or lower risk  
   → EPF suggests the gate might be over-sensitive or causing false fails
     near the threshold.

3. **EPF unstable**  
   - The same gate flips between PASS/FAIL in different EPF runs,
     even when the underlying metrics barely change.  
   → EPF configuration or its contraction logic may need tuning.

Make a short note (locally or in your tracking system) for each gate:
- gate name,
- baseline decision,
- EPF decision,
- your intuitive classification (more strict / more lenient / unstable).

---

## Step 3 – Check profiles and thresholds

Once you know which gates are affected:

1. Locate the corresponding profile / policy entry:
   - `PULSE_safe_pack_v0/pulse_policy.yml`, and/or
   - `profiles/*.yaml` if the gate is profile-specific.

2. Check:
   - the **threshold** value and `epsilon` (if any),
   - any `max_risk` / risk-related fields.

3. Ask:
   - Is the threshold still aligned with current requirements?
   - Did the underlying metric change over time (e.g. a new model,
     different evaluation distribution)?
   - Is the EPF band (`[threshold - ε, threshold]`) too wide or too narrow?

Do **not** rush to change thresholds based on a single EPF run; focus on
gates that show consistent paradox patterns across runs.

---

## Step 4 – Decide on a human action

Depending on your classification and risk appetite, typical actions are:

- **Accept stricter EPF view**  
  - If EPF consistently catches issues that the baseline misses, consider:
    - tightening the baseline threshold,
    - or promoting parts of the EPF logic into the deterministic gates.
  - This should be done via a normal PR with review, not ad-hoc changes.

- **Relax over-sensitive gates**  
  - If EPF repeatedly says "this almost always passes under small
    perturbations" while the baseline fails near the threshold, consider:
    - adjusting the threshold upward/downward (depending on the metric),
    - OR adding a small buffer (`epsilon`) in the policy.

- **Tune or disable unstable EPF rules**  
  - If EPF itself behaves in a clearly unstable way (frequent flips,
    no clear pattern), treat it as a research signal rather than a
    production signal:
    - refine EPF configuration,
    - or temporarily disable the problematic EPF rule until it can be
      stabilised.

In all cases, keep in mind:

> The main PULSE CI remains the fail-closed source of truth.  
> EPF exists to *inform* adjustments, not to override them automatically.

---

## Step 5 – Record the outcome

To keep the governance story auditable:

- Reference the EPF workflow run (SHA / date) in your PR or notes.
- Briefly state:
  - which gate(s) were impacted,
  - what EPF showed,
  - what you decided to change (or not change) and why.

If you maintain a Quality Ledger or external changelog, you can
summarise paradox-related adjustments there as well.

---

## Summary

When EPF shows a paradox candidate (baseline vs EPF gate differences):

1. Inspect `epf_report.txt` and `epf_paradox_summary.json`.
2. Classify the type of difference (strict/lenient/unstable).
3. Review thresholds and profiles for the affected gates.
4. Decide on a concrete human action (tighten, relax, or tune EPF).
5. Record the reasoning in your usual governance/logging channel.

This runbook keeps EPF in its intended role: a **diagnostic, auditable
signal** to help humans evolve the gate policies over time, without
ever silently changing release decisions on its own.
