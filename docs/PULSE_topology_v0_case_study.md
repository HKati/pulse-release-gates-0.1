# PULSE topology v0 case study

> Real-world-style worked example for reading one run through the optional
> topology layer.

This case study is **illustrative but realistic**.

It is designed to show how a reviewer can interpret a run using:

- the deterministic baseline artifacts,
- optional EPF/paradox-style diagnostic context,
- and a topology-style summary layer.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- the topology layer remains diagnostic
- the case study shows reviewer interpretation, not an automatic policy rewrite

For the conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_overview_v0.md`

For the EPF/paradox side, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PARADOX_RUNBOOK.md`

---

## 1. Scenario

Assume a release candidate for a retrieval-heavy assistant has just completed a
deterministic PULSE run.

The baseline run is positive:

- the required deterministic gates pass
- the report card looks broadly healthy
- no single gate blocks shipping

But the run does **not** feel comfortably boring.

Optional diagnostics suggest that the release is:

- near-threshold on an important quality dimension,
- beginning to show boundary sensitivity under shadow analysis,
- and accumulating reviewer-visible tension.

This is exactly the kind of situation where a topology-style interpretation is
more useful than a plain PASS/FAIL reading.

---

## 2. Baseline deterministic reading

The baseline artifacts are:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

A reviewer starts here first.

### Example baseline reading

- deterministic release posture: positive
- required gates: PASS
- obvious blocker: none
- immediate release meaning: baseline says the run is acceptable

At this stage, the baseline is still the authoritative answer.

A topology layer is only allowed to interpret what comes next; it is not allowed
to replace this baseline decision.

---

## 3. Optional diagnostic context

Now the reviewer looks at additional diagnostic surfaces.

### 3.1 EPF shadow signal

The EPF shadow path suggests that one important boundary is fragile:

- under a nearby shadow interpretation, one gate becomes less comfortable,
- or a previously clean pass starts to look near-threshold and warning-heavy.

This does **not** change the baseline result.  
It changes the reviewer’s confidence in how *robust* that result feels.

### 3.2 Paradox / field signal

A paradox-style view suggests that the same family of signals keeps appearing
together when the run is stressed:

- a quality gate is not failing deterministically,
- but it is involved in recurring tension with another release-relevant signal,
- and the pattern is no longer isolated enough to ignore casually.

Again, this is not a new release gate.  
It is evidence that the run is becoming **review-heavy**.

### 3.3 Optional external evidence context

If external detector summaries are present, they can further shape the reviewer
picture:

- perhaps all folded detector rows still pass overall,
- but evidence presence is uneven,
- or the run’s broader evidence posture feels less complete than ideal.

This still does not replace the deterministic baseline.  
It enriches the interpretation.

---

## 4. What topology adds

Without topology, the reviewer is left with a blunt summary:

- “baseline PASS”

With topology, the reviewer can say something more honest:

- “baseline PASS, but not comfortably”
- “the run is acceptable, though it looks operationally fragile”
- “this is a candidate for staging caution rather than routine production confidence”

That is the key value of the topology layer.

It adds a **stability posture** on top of the baseline release polarity.

---

## 5. Topology reading of this run

A topology-oriented reading of this scenario would likely be:

### Baseline release polarity

- positive

### Stability posture

- fragile / unstable rather than calm

### Paradox pressure

- present but not yet strong enough to replace the release decision

### Reviewer posture

- caution
- staging-first or extra review may be more honest than “ordinary PROD confidence”

A topology-style summary for this case is therefore:

- `unstably_good`

That label means:

- the baseline run is still positive,
- but the optional diagnostic context says the positivity is not comfortably robust.

---

## 6. Decision-engine style summary

A compact reviewer-facing Decision Engine style output for this same case might
look like:

```json
{
  "release_state": "STAGE_ONLY",
  "stability_type": "unstably_good",
  "reason": "Deterministic baseline remains positive, but optional shadow/paradox context suggests boundary fragility and elevated reviewer caution."
}
```

Interpretation:

- `STAGE_ONLY` here is a review/governance summary
- it is **not**, by itself, the normative release policy
- it is the topology layer’s honest compression of the broader picture

This is exactly the kind of output that is useful in dashboards, PR summaries,
or reviewer handoff notes.

---

## 7. Why this is better than plain PASS/FAIL

If the repo only said:

```
PASS
```

then reviewers might infer:

“safe to treat as ordinary production confidence”

But that would flatten away important context.

The topology layer lets the repo preserve a more faithful statement:

- the run is currently acceptable,
- but the acceptance is fragile enough to deserve caution.

That is governance value.

It helps teams avoid the common mistake of equating:

“not currently blocked”

with

“robust and boring enough for routine release.”

---

## 8. What topology does not do in this case

Even in this more interesting case, topology must still respect the normative
boundary.

It does **not**:

- silently convert baseline PASS into baseline FAIL
- silently change required gate policy
- rescue a failing baseline with a prettier narrative
- treat missing diagnostics as evidence of stability

So the correct reading is:

- baseline remains authoritative
- topology contributes reviewer posture
- policy changes still belong in the normal reviewed normative path

---

## 9. Recommended reviewer action

For a case like this, a reasonable reviewer response is:

- keep the deterministic baseline result visible and unchanged
- record that the run looks `unstably_good`
- prefer a cautious rollout posture
- inspect whether the same instability repeats on later runs
- open a tracked follow-up if the same gate family keeps appearing under
  shadow/paradox pressure

This is the kind of case where topology is most valuable:  
it improves judgment **before** the deterministic baseline starts failing.

---

## 10. Artifact chain for this case

A practical artifact chain for this case looks like:

### Required baseline artifacts

- `status.json`
- `report_card.html`

### Optional diagnostic artifacts

- EPF shadow outputs
- paradox / field outputs
- optional external detector summaries

### Optional topology outputs

- stability-oriented summary
- decision-engine style compact summary
- reviewer-facing narrative / dashboard entry

This preserves a clean evidence stack:

1. baseline evidence first
2. optional context second
3. topology interpretation last

---

## 11. A contrasting case

It helps to compare this with two simpler cases.

### Case A — `stable_good`

- baseline PASS
- shadow context quiet
- little to no paradox pressure
- ordinary production confidence

### Case B — `unstably_good` (this case study)

- baseline PASS
- shadow context warning-heavy
- recurring tension visible
- staging caution or extra review feels appropriate

The topology layer is what makes that distinction explicit and reusable.

---

## 12. Summary

This case study shows why **Topology v0** matters.

The deterministic baseline still answers:

> “is the run currently acceptable?”

The topology layer adds a second, reviewer-facing question:

> “how comfortable should we feel about that answer?”

In this worked example, the right interpretation is not:

- “blocked”

and not:

- “routine production confidence”

It is:

- **positive, but fragile**
- **`unstably_good`**

Caution is warranted even though the baseline still passes.
