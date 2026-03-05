# Paradox runbook

> What to do when EPF shadow disagrees with the deterministic baseline in the current shadow comparison workflow.

This runbook explains how to triage disagreement between baseline and EPF shadow artifacts produced by the current EPF experiment workflow.

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

Important boundary:

- deterministic archived artifacts carry the recorded baseline result for the experiment flow
- EPF shadow disagreement is a diagnostic signal, not an automatic policy rewrite
- missing or degraded inputs remain explicit

For workflow details, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`

For the topology-facing interpretation path, see:

- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For normative release meaning, use:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`

---

## 1. When this runbook applies

Use this runbook when the EPF shadow workflow reports one or more gate-level differences between baseline and EPF shadow outputs.

Typical artifacts to inspect are:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

This is a triage path over archived comparison artifacts.  
It is not a second release authority.

---

## 2. Current workflow model

The current EPF shadow workflow is a shared-input A/B comparison flow.

At a high level, it:

1. tries to produce a common `status.json` via `PULSE_safe_pack_v0/tools/run_all.py`
2. falls back to a stub `status.json` if no real baseline artifact appears
3. copies that common input into:
   - `status_baseline.json`
   - `status_epf.json`
4. runs the deterministic checker with:
   - `python scripts/check_gates.py --config pulse_gates.yaml --status status_baseline.json --defer-policy fail`
5. runs the EPF shadow checker with:
   - `python scripts/check_gates.py --config pulse_gates.yaml --status status_epf.json --epf-shadow --seed 1737 --defer-policy warn`
6. compares baseline vs EPF-side decisions
7. writes:
   - `epf_report.txt`
   - `epf_paradox_summary.json`

This means a paradox candidate is currently:

- a gate-level decision delta surfaced by the EPF shadow experiment workflow

not:

- a direct change to the main release-semantics contract

---

## 3. First question: was this a real run or a degraded run?

Before interpreting any disagreement, verify that the workflow had real enough inputs.

Check `epf_report.txt` and the job logs for:

- dependency install status
- `run_all.py` return code
- baseline checker return code
- EPF checker return code

Also check whether the workflow fell back to stub or degraded mode because:

- `PULSE_safe_pack_v0/artifacts/status.json` was missing after `run_all.py`
- `pulse_gates.yaml` was missing
- `scripts/check_gates.py` was missing
- command failures left one or both branches too partial to trust

### If the run was degraded

Do not treat the disagreement as a real paradox signal yet.

Fix the wiring first:

- make sure `run_all.py` produces a baseline status artifact when expected
- make sure `pulse_gates.yaml` exists
- make sure `scripts/check_gates.py` is present and runnable
- re-run before drawing release or topology conclusions

---

## 4. What counts as a disagreement

The current compare step reads:

- baseline decisions from `status_baseline.json["decisions"]`
- EPF-side decisions from `status_epf.json["experiments"]["epf"]`

On the EPF side, if a gate entry is a dictionary, the comparison normalizes it by reading:

1. `decision`
2. otherwise `status`
3. otherwise the raw value

A gate is counted as changed only when:

- the EPF-side value is present
- and the EPF-side value differs from the baseline-side value

Important nuance:

- `False` and `0` count as real values
- `None` means the EPF-side decision is absent

So if a gate is simply absent on the EPF side, that is degraded evidence or missing signal surface, not a confirmed decision delta.

---

## 5. Gather the comparison evidence

For a real-enough paradox candidate, collect these artifacts together:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

Recommended extras:

- the corresponding `PULSE_safe_pack_v0/artifacts/status.json`
- the corresponding `PULSE_safe_pack_v0/artifacts/report_card.html`
- the triggering commit / PR
- the relevant `pulse_gates.yaml` diff, if any
- the relevant checker / helper code diff, if any

The goal is to keep the disagreement reproducible, reviewable, and traceable.

---

## 6. Classify the disagreement

A paradox candidate is not automatically bad.  
First classify what kind of disagreement it is.

### A. Boundary sensitivity

Typical signs:

- the metric is very close to threshold
- EPF uses the adaptive band (`epsilon`) and baseline does not
- a small perturbation flips the decision

Interpretation:

- this is a stability warning around a boundary
- not necessarily a bug

Typical action:

- record it
- inspect whether the threshold is too sharp or the evidence too thin
- consider richer evaluation coverage before changing policy

### B. Missing or weak evidence

Typical signs:

- a metric is missing
- the run is partly stubbed
- sample size is too small
- the baseline or shadow decision is driven by incomplete evidence

Interpretation:

- the disagreement may be an artifact of missing information

Typical action:

- improve data collection or artifact generation
- re-run before drawing stronger conclusions

### C. Config drift

Typical signs:

- `pulse_gates.yaml` changed
- threshold, `epsilon`, `adapt`, or `min_samples` changed
- the disagreement appears immediately after config edits

Interpretation:

- the meaning of the shadow experiment changed

Typical action:

- review the config diff directly
- decide whether the change was intentional
- document why the altered shadow behavior is acceptable or not

### D. Implementation drift

Typical signs:

- `scripts/check_gates.py` changed
- EPF helper logic changed
- the disagreement appears after checker or adapter edits rather than model changes

Interpretation:

- this is tooling drift, not necessarily model drift

Typical action:

- inspect the code diff
- add or update a regression fixture
- avoid changing release meaning implicitly through shadow tooling

### E. Real behavioral fragility

Typical signs:

- the disagreement repeats across reruns
- the same gate repeatedly shows borderline instability
- EPF shadow consistently warns where the baseline barely passes or barely fails

Interpretation:

- the release result may be technically deterministic, but structurally fragile

Typical action:

- keep the finding visible
- consider staging-only rollout, more data, or broader evaluation
- discuss whether a future policy or threshold update is justified

### F. Non-reproducible or environment-sensitive result

Typical signs:

- the disagreement appears once but disappears on close reruns
- local reproduction does not match CI
- dependency or environment changes plausibly explain the difference

Interpretation:

- the signal is not yet stable enough to treat as a strong paradox candidate

Typical action:

- record the mismatch
- pin down the environment difference
- avoid policy conclusions until reproduction is stable

---

## 7. Response patterns

### Case 1 - Baseline FAIL, EPF PASS

Treat the baseline FAIL as the recorded baseline result for the experiment flow.  
Do not let EPF shadow rescue a failing release automatically.

Reasonable next steps:

- inspect whether the gate is too brittle near threshold
- collect more evidence
- open a tracked issue or PR if the pattern repeats
- only change normative policy through a deliberate reviewed change

### Case 2 - Baseline PASS, EPF FAIL or DEFER

The baseline branch still records PASS, but the shadow path is warning that the decision may be fragile.

Reasonable next steps:

- treat it as a stability warning
- consider staging-only or extra review
- expand evaluation coverage if the same gate keeps appearing
- feed the result into topology or decision-field interpretation if that helps preserve the structure

### Case 3 - Repeated disagreement on the same gate

Escalate from “interesting shadow signal” to “tracked problem”.

Reasonable next steps:

- add coverage or fixtures
- inspect whether the threshold definition is still appropriate
- decide whether the signal should stay diagnostic or be promoted into stricter policy later

Promotion into normative policy should happen in a normal reviewed PR, not inside shadow triage.

### Case 4 - EPF-side decision absent

Treat this as missing or degraded evidence first.  
Do not flatten it into “no difference”.

Reasonable next steps:

- inspect `status_epf.json`
- verify whether the EPF branch actually materialized the gate output
- fix the artifact generation path before interpreting the result

---

## 8. What to edit - and what not to edit

### If the problem is data or evidence quality

Fix:

- dataset or fixture quality
- missing artifacts
- insufficient evidence collection
- reproducibility gaps

### If the problem is EPF shadow configuration or tooling

Fix or review:

- `pulse_gates.yaml`
- `scripts/check_gates.py`
- EPF helper or adapter logic

These changes affect the shadow experiment and should stay clearly distinguished from the main release-semantics contract.

### If the problem really changes release meaning

Then the change belongs in the normative layer, for example:

- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`
- `docs/STATUS_CONTRACT.md`
- related release-gating docs or schemas

That kind of change should also come with:

- changelog coverage
- a reviewable explanation
- and, ideally, a regression fixture or reproducible example

Do not smuggle a release-policy rewrite into “just fixing the paradox runbook”.

---

## 9. Local reproduction

A close local reproduction of the current shadow workflow is:

```bash
python PULSE_safe_pack_v0/tools/run_all.py || true

if [ -f PULSE_safe_pack_v0/artifacts/status.json ]; then
  cp PULSE_safe_pack_v0/artifacts/status.json status.json
else
  echo '{"metrics": {}}' > status.json
fi

if [ -f status.json ]; then
  cp status.json status_baseline.json
  cp status.json status_epf.json
else
  echo '{"decisions": {}}' > status_baseline.json
  echo '{"experiments":{"epf":{}}}' > status_epf.json
fi

if [ -f pulse_gates.yaml ] && [ -f scripts/check_gates.py ]; then
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
else
  echo "Stub/degraded local reproduction: pulse_gates.yaml or scripts/check_gates.py missing."
fi
```

Then compare:

- baseline decisions in `status_baseline.json`
- shadow decisions under `status_epf.json["experiments"]["epf"]`

If local reproduction does not reproduce the CI disagreement, record that as a non-reproducible or environment-sensitive result.

---

## 10. What to record in the issue or PR

When a paradox candidate is real enough to track, record:

- affected gate id or ids
- baseline decision
- EPF shadow decision, or explicit absence on the EPF side
- whether the run was fully real or partially degraded
- the triggering PR or commit
- whether the disagreement reproduced
- your classification:
  - boundary sensitivity
  - missing or weak evidence
  - config drift
  - implementation drift
  - real behavioral fragility
  - non-reproducible or environment-sensitive result
- the chosen action:
  - ignore for now
  - add coverage
  - tune shadow config
  - staging-only caution
  - propose normative policy change

This keeps the shadow layer useful instead of noisy.

---

## 11. Summary

A paradox candidate means:

- the shadow interpretation disagreed with the deterministic baseline inside the current EPF experiment workflow

not:

- the main release policy has already changed

Use the disagreement to:

- inspect fragility
- improve coverage
- prioritize tracked work
- feed topology or decision-field interpretation when that adds structural clarity

Keep the release-semantics boundary explicit.
