# EPF primer v0

## EPF in one sentence

**EPF** is a **shadow evaluation profile** that runs *next to* the baseline gates and highlights **where decisions are sensitive** (borderline, unstable, or policy‑dependent), without turning that signal into an immediate hard block.

---

## Why EPF exists (what problem it solves)

Baseline gates answer: **“Ship or block?”**  
EPF shadow answers: **“Is this decision stable and explainable?”**

EPF is meant to reduce two failure modes in release governance:

- **Silent ignorance:** users ignore a theoretical concept because it produces no actionable output.
- **Over‑gating:** users treat every EPF deviation as a hard stop, causing unnecessary blocks (false blocks).

EPF should be used as a **diagnostic lens**:
- to find borderline cases,
- to spot potential flakiness / sensitivity,
- and to guide threshold/metric discussions with concrete artifacts.

---

## When EPF matters (and when it does not)

### EPF matters when
- A gate is **close to threshold** and you need to know if the decision is robust.
- You suspect **flakiness** (PASS/FAIL flipping across runs).
- You are doing **policy tuning** (tightening/loosening thresholds) and want to quantify impact.
- You are comparing two environments or configurations (A/B) and need a stable “diff story”.

### EPF does *not* matter when
- The baseline result is clearly and repeatedly **far** from thresholds (strong PASS or strong FAIL).
- You are diagnosing a **broken pipeline** (missing inputs, contract violations). Fix pipeline first.

---

## Baseline vs EPF shadow: what the difference means

Think of EPF as a **second opinion** that must be interpreted carefully.

### 1) Baseline PASS, EPF PASS
**Interpretation:** stable / low‑risk.  
**Action:** ship as usual; keep EPF records for drift tracking.

### 2) Baseline FAIL, EPF FAIL
**Interpretation:** consistent block.  
**Action:** treat as a real block; investigate the failing gate(s) with the normal playbook.

### 3) Baseline PASS, EPF FAIL
**Interpretation:** **borderline** or **sensitive** decision.  
**Action (recommended):**
- inspect which gate(s) disagree and whether they are near thresholds,
- rerun with the same determinism settings (seeded / fixed inputs),
- if reproducible: record as “policy‑sensitive”; consider whether thresholds or metric definitions need refinement.

### 4) Baseline FAIL, EPF PASS
**Interpretation:** possible **false block**, or policy mismatch, or instability.  
**Action (recommended):**
- confirm the baseline FAIL is reproducible (repeat run / seeded),
- check if the failing gate is known to be noisy or environment‑dependent,
- treat as “needs review” rather than “auto‑ship”.

> Rule of thumb: **EPF disagreement is a signal to investigate**, not an automatic ship/block decision.

---

## Where to find EPF outputs (artifacts)

EPF is only useful if reviewers can find it quickly.

### Canonical artifacts (by convention)
When running baseline + EPF shadow, keep the outputs side-by-side:

- `out/status_baseline.json` (or equivalent baseline status snapshot)
- `out/status_epf.json` (or equivalent EPF/shadow status snapshot)

Recommended derived artifacts (human + machine):
- `out/epf_shadow_summary_v0.md` (human‑readable “what differs”)
- `out/epf_shadow_diff_v0.json` (machine‑readable diff)

If you do not see these names in CI yet, search the workflow artifacts for:
- `status*.json`
- `epf*`
- `shadow*`

---

## “If you see X, do Y” — playbook

### If a single gate flips (PASS→FAIL or FAIL→PASS)
1) Identify the gate key/name.
2) Check whether the underlying metric is close to its threshold.
3) Re-run once with identical determinism controls (seeded inputs, fixed versions).
4) If the flip persists: mark the gate as “sensitive” and treat it as a candidate for drift tracking.

### If many gates flip at once
This is rarely “policy nuance” and often “environment change”.

1) Check obvious run context changes (versions, dependencies, model endpoints, dataset revisions).
2) Compare to the previous successful run (A↔B diff).
3) Treat as environment drift until proven otherwise.

### If EPF disagreements are frequent
1) Do not turn EPF into a hard block automatically.
2) Aggregate disagreements over time (drift/flakiness report).
3) Only after stability is measurable should you consider raising EPF to a stronger governance role.

---

## Common misunderstandings (FAQ)

### “EPF is the new baseline, right?”
No. Baseline gates decide ship/block. EPF is a shadow signal unless explicitly promoted.

### “Any EPF FAIL should block shipping.”
Not by default. That creates false blocks and defeats the purpose of a diagnostic layer.

### “EPF is too theoretical.”
It becomes practical only with artifacts: a deterministic diff summary and a short playbook.

---

## Definition of done (EPF primer v0)

- A reviewer can understand EPF in <10 minutes.
- A reviewer can find baseline + EPF artifacts in CI without guessing paths.
- A reviewer has a concrete “If you see X, do Y” playbook for disagreements.
