# PULSE decision field v0 — 5 minute tour

> Fast orientation to the optional decision-field layer on top of deterministic
> PULSE run artifacts.

This is the **short tour** version.

It is for readers who want to understand, quickly, what the decision field adds
on top of the baseline PULSE artifacts.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- the decision field is optional and diagnostic
- decision-field outputs summarize reviewer posture; they do not silently
  rewrite release policy

For the fuller conceptual layer, see:

- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_topology_v0_design_note.md`

For practical usage, see:

- `docs/PULSE_topology_v0_quickstart_decision_engine_v0.md`
- `docs/PULSE_topology_v0_cli_demo.md`
- `docs/PULSE_topology_v0_case_study.md`

---

## 1. The 30-second version

PULSE already gives you a deterministic baseline:

- `status.json`
- `report_card.html`

That baseline answers:

- did the run pass or fail the required gates?

The **decision field** adds a second question:

- how should a reviewer *interpret* the overall posture of this run?

That means the decision field is not a second gate engine.

It is a compact reviewer-facing interpretation layer.

---

## 2. The minimum evidence chain

Start with the baseline artifacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Optional context can then be layered in, for example:

- paradox / field artifacts
- Stability Map context
- EPF shadow outputs
- external evidence posture

The decision field comes **after** that evidence chain, not before it.

Good order:

1. baseline first  
2. optional diagnostics second  
3. compact decision-field interpretation last  

---

## 3. What question the decision field answers

A deterministic baseline tells you:

- PASS / FAIL / release polarity

The decision field tells you things like:

- is this PASS calm or fragile?
- is this FAIL clean or unstable?
- is this a routine review, or a reviewer-heavy one?
- does this run feel robust, borderline, or governance-heavy?

That is why the decision field is useful:  
it adds **posture**, not new hidden policy.

---

## 4. Typical output language

A decision-field-style summary often combines:

- a compact release posture
- a compact stability posture

Example vocabulary:

### Release-facing summary

- `PROD_OK`
- `BLOCK`
- `UNKNOWN`

### Stability-facing summary

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `unknown`

Interpretation rule:

- `release_state` is the compact release-facing summary
- `stability_type` carries the reviewer-facing stability posture

The two together are more useful than PASS/FAIL alone.

---

## 5. The most important reading pattern

### Calm PASS

Example reading:

```text
release_state: PROD_OK
stability_type: stable_good
```

Meaning:

- the baseline passes
- optional diagnostics are quiet enough
- reviewer concern is low

This is the **“ordinary confidence” case**.

---

### Fragile PASS

Example reading:

```text
release_state: PROD_OK
stability_type: unstably_good
```

Meaning:

- the baseline still passes
- but optional context suggests fragility, tension, or caution

This is the **“acceptable, but not comfortably boring” case**.

This is one of the most useful decision-field patterns in practice.

---

### Clean FAIL

Example reading:

```text
release_state: BLOCK
stability_type: stable_bad
```

Meaning:

- the baseline fails
- and the broader evidence does not suggest unusual ambiguity

This is a straightforward remediation case.

---

### Unstable FAIL

Example reading:

```text
release_state: BLOCK
stability_type: unstably_bad
```

Meaning:

- the baseline fails
- and diagnostics suggest tension, ambiguity, or unstable evidence

This is where the run usually needs deeper triage, not just a quick fix.

---

## 6. What the decision field is not

The decision field is **not**:

- a replacement for `status.json`
- a replacement for `check_gates.py`
- a way to silently change release policy
- a reason to ignore missing evidence
- a magic downgrade/upgrade layer for the deterministic baseline

If the compact summary and the baseline disagree, **the baseline wins**.

That rule should stay stable.

---

## 7. Why reviewers actually want this layer

Without the decision field, many runs collapse into:

- “PASS”

or

- “FAIL”

But reviewers often need something more honest.

For example, there is a big difference between:

- “PASS and comfortably robust”
- “PASS but fragile and review-heavy”

and also between:

- “FAIL in an ordinary way”
- “FAIL with instability and confusing evidence”

The decision field gives language for those distinctions.

That improves governance quality without changing the normative release contract.

---

## 8. Fast practical workflow

The shortest useful workflow is:

1. run the deterministic baseline
2. read `status.json` and the Quality Ledger
3. add optional context if you have it:
   - EPF
   - paradox
   - Stability Map
4. read the compact decision-field / Decision Engine summary **last**

This keeps interpretation anchored to evidence.

---

## 9. A good mental model

A good one-line mental model is:

> baseline tells you what the release result is  
> decision field tells you how comfortable a reviewer should feel about that result

That is why the layer is valuable.

It does not replace the baseline.  
It makes the reviewer posture more honest.

---

## 10. Summary

If you remember only three things, remember these:

- the deterministic baseline stays normative
- the decision field is optional and diagnostic
- the real value is distinguishing:

  - calm PASS from fragile PASS  
  - ordinary FAIL from unstable FAIL  

That is the core of the decision-field layer in this repository.
