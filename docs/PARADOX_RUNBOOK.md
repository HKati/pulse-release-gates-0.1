# Paradox runbook

> What to do when EPF shadow disagrees with the baseline deterministic decision.

This runbook is for **shadow disagreement triage**.

It applies when the EPF shadow workflow reports that one or more gates have a
different decision in shadow mode than in the baseline deterministic run.

Important boundary:

- the baseline deterministic path remains the source of truth for release gating
- EPF shadow disagreement is a diagnostic signal, not an automatic release rewrite

For the broader repository model, see:

- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`
- `docs/status_json.md`

For normative release meaning, use:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`

---

## 1. When this runbook applies

Use this runbook when the EPF shadow workflow reports something like:

- “EPF shadow detected N gate(s) with different decisions than the baseline.”

Typical artefacts to inspect are:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

This is a **triage path**, not a second release policy.

---

## 2. Current workflow model

The current EPF shadow workflow does the following:

1. tries to produce a baseline `status.json` via `PULSE_safe_pack_v0/tools/run_all.py`
2. copies that baseline into:
   - `status_baseline.json`
   - `status_epf.json`
3. runs the baseline deterministic checker with:
   - `python scripts/check_gates.py --config pulse_gates.yaml --status status_baseline.json --defer-policy fail`
4. runs the EPF shadow checker with:
   - `python scripts/check_gates.py --config pulse_gates.yaml --status status_epf.json --epf-shadow --seed 1737 --defer-policy warn`
5. compares baseline vs EPF decisions
6. writes:
   - `epf_report.txt`
   - `epf_paradox_summary.json`

This means a paradox candidate is currently a **difference between baseline and
EPF shadow decisions under the EPF experiment workflow**, not a direct change to
the main release gate set.

---

## 3. First question: was this a real run or a stub?

Before interpreting any disagreement, verify that the workflow actually had real
inputs.

Check `epf_report.txt` and the job logs for:

- dependency install status
- `run_all.py` return code
- baseline checker return code
- EPF checker return code

Also check whether the workflow fell back to stub mode because:

- `PULSE_safe_pack_v0/artifacts/status.json` was missing, or
- `pulse_gates.yaml` was missing.

### If the run was stub / degraded

Do **not** treat the disagreement as a real paradox signal.

Fix the wiring first:

- make sure `run_all.py` produces a baseline status artefact
- make sure `pulse_gates.yaml` exists
- make sure `scripts/check_gates.py` is present and runnable

Then re-run the workflow.

---

## 4. Gather the comparison evidence

For a real paradox candidate, collect these artefacts together:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

Recommended extras:

- the corresponding `PULSE_safe_pack_v0/artifacts/status.json`
- the corresponding `PULSE_safe_pack_v0/artifacts/report_card.html`
- the commit / PR that triggered the run
- any threshold/config file that changed in the same PR

The goal is to keep the disagreement reproducible and reviewable.

---

## 5. Classify the disagreement

A paradox candidate is not automatically “bad”.
First classify what kind of disagreement it is.

### A. Boundary sensitivity

Typical signs:

- the metric is very close to threshold
- EPF uses the adaptive band (`epsilon`) and baseline does not
- a small perturbation flips the decision

Interpretation:

- this is a stability warning around a boundary,
- not necessarily a bug.

Typical action:

- record it,
- inspect whether the threshold is too sharp or the evidence too thin,
- consider richer evaluation coverage before changing policy.

### B. Missing / weak evidence

Typical signs:

- a metric is missing
- the run is partly stubbed
- sample size is too small
- the baseline or shadow decision is driven by incomplete evidence

Interpretation:

- the disagreement may be an artefact of missing information.

Typical action:

- improve data collection or artefact generation,
- re-run before drawing governance conclusions.

### C. Config drift

Typical signs:

- `pulse_gates.yaml` changed
- threshold / `epsilon` / `adapt` / `min_samples` changed
- the disagreement appears immediately after config edits

Interpretation:

- the meaning of the shadow experiment changed.

Typical action:

- review the config diff directly,
- decide whether the change was intentional,
- document why the altered shadow behavior is acceptable.

### D. Implementation drift

Typical signs:

- `scripts/check_gates.py` changed
- EPF helper logic changed
- the disagreement appears after checker / adapter edits rather than model changes

Interpretation:

- this is tooling drift, not necessarily model drift.

Typical action:

- inspect the code diff,
- add or update a regression fixture,
- avoid changing release meaning implicitly through shadow tooling.

### E. Real behavioral fragility

Typical signs:

- the disagreement repeats across reruns
- the same gate repeatedly shows borderline instability
- EPF shadow consistently warns where the baseline barely passes

Interpretation:

- this is the most interesting class:
  the release decision may be technically deterministic, but operationally fragile.

Typical action:

- keep the finding visible,
- consider staging-only rollout, more data, or broader evaluation,
- discuss whether a future policy or threshold update is justified.

---

## 6. Decision rules

### Case 1 — Baseline FAIL, EPF PASS

Treat the **baseline FAIL** as authoritative for release gating.

Do **not** let EPF shadow “rescue” a failing release automatically.

Reasonable next steps:

- inspect whether the gate is too brittle near threshold
- collect more evidence
- open a tracked issue / PR if the pattern repeats
- only change normative policy through a deliberate reviewed change

### Case 2 — Baseline PASS, EPF FAIL or DEFER

The normative release path still says PASS, but the shadow path is warning that
the decision may be fragile.

Reasonable next steps:

- treat it as a stability warning
- consider staging-only or extra review
- expand evaluation coverage if the same gate keeps appearing
- avoid silently rewriting main release semantics based on one shadow run

### Case 3 — Repeated disagreement on the same gate

Escalate from “interesting shadow signal” to “tracked governance problem”.

Reasonable next steps:

- add coverage / fixtures
- inspect whether the threshold definition is still appropriate
- decide whether the signal should stay diagnostic or eventually be promoted into
  a stricter policy path

Promotion into normative policy should happen in a normal reviewed PR, not
inside shadow triage.

---

## 7. What to edit — and what not to edit

### If the problem is data / evidence quality

Fix:

- dataset / fixture quality
- missing artefacts
- insufficient evidence collection
- reproducibility gaps

### If the problem is EPF shadow configuration

Fix or review:

- `pulse_gates.yaml`
- `scripts/check_gates.py`
- EPF helper / adapter logic

These changes affect the **shadow experiment** and should stay clearly
distinguished from the main release gate semantics.

### If the problem really changes release meaning

Then the change belongs in the **normative layer**, for example:

- `pulse_gate_policy_v0.yml`
- the main release-gating docs / contracts
- the required CI path

That kind of change should also come with:

- changelog coverage
- reviewable explanation
- and, ideally, a regression fixture or reproducible example

Do not smuggle a release-policy rewrite into “just fixing the paradox runbook”.

---

## 8. Local reproduction

A close local reproduction of the current shadow workflow is:

```bash
python PULSE_safe_pack_v0/tools/run_all.py

cp PULSE_safe_pack_v0/artifacts/status.json status_baseline.json
cp PULSE_safe_pack_v0/artifacts/status.json status_epf.json

python scripts/check_gates.py \
  --config pulse_gates.yaml \
  --status status_baseline.json \
  --defer-policy fail

python scripts/check_gates.py \
  --config pulse_gates.yaml \
  --status status_epf.json \
  --epf-shadow \
  --seed 1737 \
  --defer-policy warn
```

Then compare:

- baseline decisions in `status_baseline.json`
- shadow decisions under `status_epf.json["experiments"]["epf"]`

If local reproduction does not reproduce the CI disagreement, record that as
a non-reproducible or environment-sensitive result.

---

## 9. What to record in the issue / PR

When a paradox candidate is real enough to track, record:

- affected gate id(s)
- baseline decision
- EPF shadow decision
- whether the run was fully real or partially stubbed
- the triggering PR / commit
- whether the disagreement reproduced
- your classification:
  - boundary sensitivity
  - missing evidence
  - config drift
  - implementation drift
  - real behavioral fragility
- the chosen action:
  - ignore for now
  - add coverage
  - tune shadow config
  - stage-only caution
  - propose normative policy change

This keeps the shadow layer useful instead of noisy.

---

## 10. Summary

A paradox candidate means:

“the shadow interpretation disagreed with the baseline,”

not:

“the main release policy has already changed.”

Use the disagreement to:

- inspect fragility,
- improve coverage,
- and prioritise governance work.

Keep the deterministic baseline authoritative until a deliberate reviewed change
promotes a new rule into the normative path.
