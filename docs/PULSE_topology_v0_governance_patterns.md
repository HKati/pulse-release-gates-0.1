# PULSE topology v0 governance patterns

> Practical governance patterns for using topology / Decision Engine outputs
> without blurring the repository’s normative release boundary.

This page is about **how to use topology artifacts well** in review and
governance.

It is not a release-policy contract by itself.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- topology outputs are optional and diagnostic
- governance patterns should enrich human judgment, not silently rewrite policy

For the conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For worked examples and quickstarts, see:

- `docs/PULSE_topology_v0_case_study.md`
- `docs/PULSE_topology_v0_quickstart_decision_engine_v0.md`
- `docs/PULSE_topology_v0_cli_demo.md`

---

## 1. Why governance patterns matter

A deterministic baseline gives a hard answer:

- PASS / FAIL at the required-gate layer

That is necessary, but often not sufficient for good release governance.

Reviewers also need to know things like:

- does this PASS look robust or fragile?
- does this run deserve routine confidence or cautious rollout?
- are we seeing recurring tension that should become tracked governance work?
- is the current result trustworthy, borderline, or under-evidenced?

This is where topology helps.

Topology should improve **judgment quality** without becoming an unreviewed second
policy engine.

---

## 2. The foundational rule

Always apply this order:

1. **baseline deterministic artifacts first**
   - `status.json`
   - Quality Ledger / report card

2. **optional diagnostic context second**
   - paradox / field artifacts
   - Stability Map context
   - EPF shadow outputs
   - external evidence posture

3. **topology / Decision Engine summary last**
   - reviewer-facing compression of the picture

This ordering is the single most important governance pattern.

If people read only the compact topology summary and skip the baseline evidence,
governance quality gets worse, not better.

---

## 3. Pattern: baseline-first signoff

### When to use it

Use this pattern on every release review, even when topology outputs exist.

### How it works

Start with the baseline artifacts and answer:

- what does the deterministic baseline say?
- what gates actually failed?
- what metrics and evidence are present?
- what is the current normative release posture?

Only after that should you read:

- Decision Engine summaries
- topology narratives
- dashboard views

### Why this pattern is healthy

It preserves the repo’s core invariant:

- the baseline deterministic path remains normative
- topology remains interpretation

This is the safest pattern for avoiding semantic drift.

---

## 4. Pattern: robust PASS

### Typical evidence shape

- baseline required gates pass
- optional diagnostics are quiet
- no meaningful paradox pressure is visible
- evidence looks complete enough for ordinary confidence

### Typical reviewer reading

A compact reviewer-facing topology summary may look like:

```text
release_state: PROD_OK
stability_type: stable_good
```

### Governance action

Reasonable response:

- ordinary release confidence
- normal archival / signoff
- no extra caution beyond standard process

### Why topology still helps here

Even when the run is boring, topology helps by making the “boringness” explicit
and reusable in dashboards, board views, or review notes.

---

## 5. Pattern: fragile PASS

### Typical evidence shape

- baseline required gates still pass
- but optional diagnostics are noisy:
  - EPF shadow pressure
  - paradox tension
  - repeated near-threshold behavior
  - incomplete reviewer comfort

### Typical reviewer reading

A compact topology summary may look like:

```text
release_state: PROD_OK
stability_type: unstably_good
```

### Governance action

Reasonable response:

- keep the baseline PASS unchanged
- prefer caution in rollout posture
- consider extra review, staged rollout, or tighter observation
- open follow-up work if the same pattern repeats

### Why this pattern matters

This is probably the most important topology governance pattern.

It prevents teams from collapsing:

“not blocked”

into

“comfortably production-ready.”

Topology is doing useful work here precisely because it preserves that nuance.

---

## 6. Pattern: clean FAIL

### Typical evidence shape

- deterministic baseline fails
- diagnostics do not suggest unusual ambiguity
- the run looks negative in a fairly ordinary way

### Typical reviewer reading

A compact topology-style summary may look like:

```text
release_state: BLOCK
stability_type: stable_bad
```

### Governance action

Reasonable response:

- keep the baseline FAIL authoritative
- fix the underlying issue
- rerun after remediation
- avoid over-reading optional overlays

### Why this pattern is healthy

It avoids the opposite mistake:
using richer dashboards to make a straightforward failure look more debatable
than it really is.

---

## 7. Pattern: unstable FAIL

### Typical evidence shape

- deterministic baseline fails
- diagnostics are also noisy:
  - paradox pressure
  - shadow disagreement
  - unstable or degraded evidence posture
  - unclear failure boundary

### Typical reviewer reading

A compact topology-style summary may look like:

```text
release_state: BLOCK
stability_type: unstably_bad
```

### Governance action

Reasonable response:

- treat the release as blocked
- also treat the case as a higher-priority triage / governance problem
- inspect whether the failure is:
  - a simple miss
  - a coverage problem
  - a threshold problem
  - a tooling / evidence-quality problem

### Why this pattern matters

It helps reviewers distinguish:

“failing, but ordinary”

from

“failing, and operationally confusing.”

That difference changes how much process attention the run deserves.

---

## 8. Pattern: reviewer caution without policy rewrite

This is the core governance use-case for topology.

### Healthy form

- baseline remains unchanged
- topology expresses caution through:
  - `stability_type`
  - reviewer narrative
  - board / dashboard wording
  - rollout posture recommendations

### Unhealthy form

- topology output is treated as if it silently changed required policy
- reviewers start reading a compact summary as the new source of truth
- a passing baseline is described as blocked without policy review
- missing diagnostics are treated as if they imply calm / confidence

If you find yourselves drifting toward the unhealthy form, stop and push the
change back into:

- policy
- CI
- contracts
- reviewed changelog-backed updates

---

## 9. Pattern: stage with caution

This is a governance action pattern, not necessarily a literal classifier rule.

### When to use it

Use it when:

- the baseline still passes
- the topology layer says the run is fragile
- reviewers want to preserve momentum without pretending the run is boring

### What it means in practice

Possible actions:

- narrower exposure
- staged rollout
- additional manual review
- more telemetry / observation after release
- explicit follow-up issue tied to the same run

### Why this is useful

It lets teams express caution operationally
without falsely claiming that the baseline deterministic decision already changed.

---

## 10. Pattern: repeated fragility becomes tracked work

A single fragile run may be noise.  
A repeated fragile pattern is governance information.

### Trigger signs

- the same gate family keeps showing paradox pressure
- multiple runs cluster around the same near-threshold region
- `unstably_good` style readings recur
- evidence posture is repeatedly weaker than desired

### Governance action

Reasonable response:

- open a tracked issue
- add evaluation coverage
- review thresholds and evidence shape
- decide whether a future policy change is needed

### Why this pattern matters

Topology becomes most valuable when it helps you see trends in reviewer burden
before the deterministic baseline starts failing broadly.

---

## 11. Pattern: evidence completeness is separate from release posture

Topology should not hide evidence gaps.

### Good governance question

“Did we have enough evidence to feel confident?”

### Different good governance question

“What did the current baseline classifier say?”

These are not the same question.

A run can be:

- baseline-positive

but

- reviewer-uncomfortable because evidence completeness is poor

That should remain visible.

It should not be flattened into a fake calm PASS.

---

## 12. Pattern: archive the interpretation chain

A topology summary is only useful later if the evidence chain remains intact.

### Recommended archive bundle

- `status.json`
- `report_card.html`
- `decision_engine_v0.json`, when produced
- `paradox_field_v0.json`, when produced
- Stability Map artifact, when produced
- EPF shadow artifacts, when relevant
- any reviewer note / rollout decision tied to the same run

### Why this matters

Good governance is not just about making a decision.  
It is also about being able to reconstruct why that decision made sense later.

---

## 13. Anti-patterns

Avoid these.

### Anti-pattern A — dashboard supremacy

Bad habit:

- treating a dashboard or compact summary as more authoritative than `status.json`

### Anti-pattern B — topology as secret policy

Bad habit:

- using topology wording to effectively change release semantics without a policy change

### Anti-pattern C — fabricated completeness

Bad habit:

- acting as if missing overlays imply quiet diagnostics

### Anti-pattern D — one-run overreaction

Bad habit:

- taking one noisy optional signal and immediately rewriting thresholds or policy

### Anti-pattern E — compact-summary-only review

Bad habit:

- reviewers approving or rejecting runs from the compact summary alone

All of these reduce auditability and semantic clarity.

---

## 14. A practical review template

A simple governance checklist for one run:

### Baseline

- What does the deterministic baseline say?

### Evidence

- Is evidence complete enough to trust the result?

### Diagnostics

- Are optional overlays quiet, fragile, or noisy?

### Topology summary

- Does the run look `stable_good`, `unstably_good`, `stable_bad`, `unstably_bad`, or `unknown`?

### Action

- ordinary release
- cautious rollout
- deeper review
- blocked and remediate
- tracked follow-up for repeated fragility

This is a good lightweight governance pattern because it keeps the evidence chain
visible all the way through.

---

## 15. Summary

Topology governance works best when it does three things well:

- preserves the deterministic baseline as the source of truth
- adds honest reviewer posture on top of that baseline
- turns recurring fragility into visible, tracked governance work

That is the real value of topology in this repository:

- not hidden policy
- not a second gate engine
- but better structured judgment over archived run artifacts.
