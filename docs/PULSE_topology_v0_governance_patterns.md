# PULSE topology v0 instrument-review patterns

Legacy filename / workshop alias:

```text
docs/PULSE_topology_v0_governance_patterns.md
```

Canonical technical role:

```text
PULSE topology v0 instrument-review patterns
```

## Boundary

This document describes topology-related instrument-review patterns around PULSEmech.

It does not define PULSE.

It does not define release authority.

It does not create a second release-decision engine.

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

Topology artifacts may support review, triage, rollout posture, and diagnostic interpretation.

They are non-authorizing by default.

A topology signal becomes release-relevant only if it is:

```text
recorded as release evidence
referenced by declared policy
materialized as a required gate
enforced through the strict fail-closed CI path
```

---

## 0. Scope

This page is about how to use topology artifacts well in review without blurring the repository’s release-authority boundary.

It is not a release-policy contract by itself.

Important boundary:

```text
the deterministic baseline remains the authority carrier for release gating
topology outputs are optional and diagnostic
instrument-review patterns should enrich human judgment
instrument-review patterns must not silently rewrite policy
```

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

## 1. Why instrument-review patterns matter

A deterministic baseline gives a hard answer:

```text
PASS / FAIL at the required-gate layer
```

That is necessary, but often not sufficient for good release review.

Reviewers may also need to know:

```text
does this PASS look robust or fragile?
does this run deserve routine confidence or cautious rollout?
are we seeing recurring tension that should become tracked review work?
is the current result trustworthy, borderline, or under-evidenced?
```

This is where topology helps.

Topology should improve review quality without becoming an unreviewed second policy engine.

---

## 2. The foundational rule

Always apply this order:

1. **baseline deterministic artifacts first**

   ```text
   status.json
   Quality Ledger / report card
   declared gate policy
   workflow-effective materialized required gate set
   strict fail-closed CI result
   ```

2. **optional diagnostic context second**

   ```text
   paradox / field artifacts
   Stability Map context
   EPF shadow outputs
   external evidence posture
   topology overlays
   ```

3. **topology / Decision Engine summary last**

   ```text
   reviewer-facing compression of the recorded artifact state
   ```

This ordering is the single most important instrument-review pattern.

If people read only the compact topology summary and skip the baseline evidence, review quality gets worse, not better.

---

## 3. Pattern: baseline-first signoff

### When to use it

Use this pattern on every release review, even when topology outputs exist.

### How it works

Start with the baseline artifacts and answer:

```text
what does the deterministic baseline say?
what gates actually failed?
what metrics and evidence are present?
what is the current release-authority posture?
which required gate set was materialized?
```

Only after that should you read:

```text
Decision Engine summaries
topology narratives
reader surfaces
dashboard-style views
```

### Why this pattern is healthy

It preserves the repo’s core invariant:

```text
the baseline deterministic path remains release-authority-bearing
topology remains interpretation
```

This is the safest pattern for avoiding semantic drift.

---

## 4. Pattern: robust PASS

### Typical evidence shape

```text
baseline required gates pass
optional diagnostics are quiet
no meaningful paradox pressure is visible
evidence looks complete enough for ordinary confidence
```

### Typical reviewer reading

A compact reviewer-facing topology summary may look like:

```text
release_state: PROD_OK
stability_type: stable_good
```

### Review action

Reasonable response:

```text
ordinary release confidence
normal archival / signoff
no extra caution beyond standard process
```

### Why topology still helps here

Even when the run is ordinary, topology helps by making the stability reading explicit and reusable in review notes.

---

## 5. Pattern: fragile PASS

### Typical evidence shape

```text
baseline required gates still pass
optional diagnostics are noisy
EPF shadow pressure is visible
paradox tension is visible
near-threshold behavior repeats
reviewer confidence is lower than ordinary
```

### Typical reviewer reading

A compact topology summary may look like:

```text
release_state: PROD_OK
stability_type: unstably_good
```

### Review action

Reasonable response:

```text
keep the baseline PASS unchanged
prefer caution in rollout posture
consider extra review, staged rollout, or tighter observation
open follow-up work if the same pattern repeats
```

### Why this pattern matters

This prevents teams from collapsing:

```text
not blocked
```

into:

```text
comfortably production-ready
```

Topology is useful here precisely because it preserves that distinction.

---

## 6. Pattern: clean FAIL

### Typical evidence shape

```text
deterministic baseline fails
diagnostics do not suggest unusual ambiguity
the run looks negative in a fairly ordinary way
```

### Typical reviewer reading

A compact topology-style summary may look like:

```text
release_state: BLOCK
stability_type: stable_bad
```

### Review action

Reasonable response:

```text
keep the baseline FAIL authoritative
fix the underlying issue
rerun after remediation
avoid over-reading optional overlays
```

### Why this pattern is healthy

It avoids the opposite mistake: using richer reader surfaces to make a straightforward failure look more debatable than it is.

---

## 7. Pattern: unstable FAIL

### Typical evidence shape

```text
deterministic baseline fails
diagnostics are also noisy
paradox pressure is present
shadow disagreement is present
evidence posture is unstable or degraded
failure boundary is unclear
```

### Typical reviewer reading

A compact topology-style summary may look like:

```text
release_state: BLOCK
stability_type: unstably_bad
```

### Review action

Reasonable response:

```text
treat the release as blocked
also treat the case as higher-priority triage
inspect whether the failure is a simple miss
inspect whether the failure is a coverage problem
inspect whether the failure is a threshold problem
inspect whether the failure is a tooling / evidence-quality problem
```

### Why this pattern matters

It helps reviewers distinguish:

```text
failing, but ordinary
```

from:

```text
failing, and operationally confusing
```

That difference changes how much review attention the run deserves.

---

## 8. Pattern: reviewer caution without policy rewrite

This is the core instrument-review use case for topology.

### Healthy form

```text
baseline remains unchanged
topology expresses caution through stability_type
topology expresses caution through reviewer narrative
topology expresses caution through rollout posture recommendation
```

### Unhealthy form

```text
topology output is treated as if it silently changed required policy
reviewers start reading a compact summary as the new authority carrier
a passing baseline is described as blocked without policy review
missing diagnostics are treated as if they imply calm / confidence
```

If the review starts drifting toward the unhealthy form, stop and push the change back into:

```text
policy
CI
contracts
reviewed changelog-backed updates
```

---

## 9. Pattern: stage with caution

This is a review-action pattern, not necessarily a literal classifier rule.

### When to use it

Use it when:

```text
the baseline still passes
the topology layer says the run is fragile
reviewers want to preserve momentum without pretending the run is ordinary
```

### What it means in practice

Possible actions:

```text
narrower exposure
staged rollout
additional manual review
more telemetry / observation after release
explicit follow-up issue tied to the same run
```

### Why this is useful

It lets teams express caution operationally without falsely claiming that the deterministic baseline decision already changed.

---

## 10. Pattern: repeated fragility becomes tracked work

A single fragile run may be noise.

A repeated fragile pattern is review information.

### Trigger signs

```text
the same gate family keeps showing paradox pressure
multiple runs cluster around the same near-threshold region
unstably_good style readings recur
evidence posture is repeatedly weaker than desired
```

### Review action

Reasonable response:

```text
open a tracked issue
add evaluation coverage
review thresholds and evidence shape
decide whether a future policy change is needed
```

### Why this pattern matters

Topology becomes most valuable when it helps reviewers see trends in review burden before the deterministic baseline starts failing broadly.

---

## 11. Pattern: evidence completeness is separate from release posture

Topology should not hide evidence gaps.

Good review question:

```text
Did we have enough evidence to feel confident?
```

Different review question:

```text
What did the current baseline classifier say?
```

These are not the same question.

A run can be:

```text
baseline-positive
```

but:

```text
reviewer-uncomfortable because evidence completeness is poor
```

That should remain visible.

It should not be flattened into a fake calm PASS.

---

## 12. Pattern: archive the interpretation chain

A topology summary is only useful later if the evidence chain remains intact.

### Recommended archive bundle

```text
status.json
report_card.html
decision_engine_v0.json, when produced
paradox_field_v0.json, when produced
Stability Map artifact, when produced
EPF shadow artifacts, when relevant
reviewer note / rollout decision tied to the same run
```

### Why this matters

Good instrument review is not just about making a decision.

It is also about being able to reconstruct why that review posture made sense later.

---

## 13. Anti-patterns

Avoid these.

### Anti-pattern A — reader-surface supremacy

Bad habit:

```text
treating a reader surface or compact summary as more authoritative than status.json
```

### Anti-pattern B — topology as secret policy

Bad habit:

```text
using topology wording to effectively change release semantics without a policy change
```

### Anti-pattern C — fabricated completeness

Bad habit:

```text
acting as if missing overlays imply quiet diagnostics
```

### Anti-pattern D — one-run overreaction

Bad habit:

```text
taking one noisy optional signal and immediately rewriting thresholds or policy
```

### Anti-pattern E — compact-summary-only review

Bad habit:

```text
reviewers approving or rejecting runs from the compact summary alone
```

All of these reduce auditability and semantic clarity.

---

## 14. A practical review template

A simple instrument-review checklist for one run:

### Baseline

```text
What does the deterministic baseline say?
```

### Evidence

```text
Is evidence complete enough to trust the result?
```

### Diagnostics

```text
Are optional overlays quiet, fragile, or noisy?
```

### Topology summary

```text
Does the run look stable_good, unstably_good, stable_bad, unstably_bad, or unknown?
```

### Action

```text
ordinary release
cautious rollout
deeper review
blocked and remediate
tracked follow-up for repeated fragility
```

This is a good lightweight instrument-review pattern because it keeps the evidence chain visible all the way through.

---

## 15. Summary

Topology instrument review works best when it does three things well:

```text
preserves the deterministic baseline as the release-authority carrier
adds honest reviewer posture on top of that baseline
turns recurring fragility into visible, tracked review work
```

That is the value of topology in this repository:

```text
not hidden policy
not a second gate engine
better structured judgment over archived run artifacts
```
