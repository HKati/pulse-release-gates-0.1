# PULSE decision field overview (v0)

> High-level overview of the optional decision-field layer on top of
> deterministic PULSE run artifacts.

The decision field is a **review and interpretation layer**.

It exists to help humans ask questions such as:

- is this run merely passing, or robustly passing?
- does the run look calm, fragile, or review-heavy?
- where is tension accumulating across gates, metrics, and overlays?
- how should a reviewer summarize the run without rewriting release semantics?

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- the decision field is optional
- decision-field outputs are interpretive, not automatically normative

For the broader topology layer, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_topology_epf_hook_v0.md`

For the current repository state and normative boundary, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

## 1. What the decision field is

PULSE already has a deterministic release core:

- one run produces a machine-readable `status.json`
- the main CI path enforces fail-closed gate outcomes
- the Quality Ledger explains the run for humans

The decision field sits **above** that core.

Its job is not to decide from scratch.
Its job is to interpret the broader shape of one run, using archived artifacts.

A useful mental model is:

- **gates** tell you whether the run passed or failed deterministically
- **metrics** tell you what was measured
- **shadow / overlay artifacts** tell you where fragility or tension may be building
- **the decision field** turns that into a reviewer-facing picture of the run

That makes the decision field an **artifact-first interpretation layer**.

---

## 2. Normative boundary

Keep this order stable:

1. **deterministic baseline**
   - authoritative release decision

2. **diagnostic / shadow context**
   - EPF shadow
   - paradox / field overlays
   - external evidence context
   - hazard or other review-oriented overlays

3. **decision-field interpretation**
   - stability language
   - reviewer caution
   - compact release narratives
   - optional decision-engine style summaries

If a decision-field output and the deterministic gate path disagree, the
deterministic gate path wins.

The decision field must never silently:

- rescue a deterministic FAIL,
- convert missing evidence into PASS,
- or rewrite release policy by implication.

---

## 3. What the decision field reads

The decision field should be **artifact-first**.

Its natural inputs are archived artifacts such as:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- optional EPF shadow outputs
- optional paradox / field overlays
- optional external detector summaries

This matters because the decision field should remain:

- reproducible,
- reviewable,
- and auditable from immutable run artifacts.

It should not depend on hidden live computation that creates new release meaning.

---

## 4. What the decision field tries to express

The decision field is useful when a plain PASS/FAIL answer is not enough.

Typical questions it helps answer:

- is the run **stable** or **fragile**?
- is the run **review-light** or **review-heavy**?
- is there **paradox pressure** or unresolved tension?
- should the run feel like:
  - ordinary production confidence,
  - staging caution,
  - or governance follow-up?

A decision field is therefore less about raw measurement and more about
**structured reviewer interpretation**.

---

## 5. Relationship to topology

The decision field belongs to the broader topology family.

A clean split is:

- **topology layer**
  - the overall optional diagnostic family

- **decision field**
  - one way of representing the state of a run inside that family

- **stability map**
  - a more explicitly stability-oriented projection

- **decision engine**
  - a compact summarizer that may emit reviewer-facing states

So the decision field is best understood as a **conceptual and reviewer-facing
projection inside the topology layer**, not as an entirely separate system.

---

## 6. Relationship to the Decision Engine

A decision-field view is broader than a single compact label, but it pairs
naturally with a diagnostic Decision Engine.

For example, a Decision Engine may summarize a run with reviewer-facing states
such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`
- `UNKNOWN`

Those should be interpreted as **diagnostic governance summaries** unless and
until the repository explicitly promotes them into normative policy.

That distinction matters:

- the vocabulary may resemble release language,
- but the baseline deterministic path remains authoritative.

The decision field provides the richer context around why a run is being
summarized that way.

---

## 7. Relationship to EPF shadow

EPF shadow is one of the most useful optional inputs to a decision field.

A helpful split is:

- **baseline** answers:
  - “what is the deterministic release decision?”

- **EPF shadow** answers:
  - “how fragile does that decision look near the boundary?”

- **decision field** answers:
  - “what reviewer posture does that imply?”

Good uses of EPF in the decision field include:

- distinguishing clean PASS from fragile PASS
- surfacing repeated boundary sensitivity
- highlighting runs that deserve staging caution
- identifying governance pressure before deterministic failure appears

Bad uses would be:

- letting EPF shadow silently overrule the baseline
- treating one shadow disagreement as an implicit policy rewrite
- treating missing EPF artifacts as evidence of calm or stability

For the detailed bridge, see:

- `docs/PULSE_topology_epf_hook_v0.md`

---

## 8. Relationship to paradox / field overlays

Paradox and field overlays often capture:

- tension,
- conflict structure,
- unresolved tradeoffs,
- or repeated instability patterns.

The decision field uses those as **interpretation inputs**.

That means paradox artifacts can help the decision field say things like:

- “this run is passing, but the same gate family keeps showing tension”
- “this run is operationally acceptable, but not comfortably stable”
- “this run should be reviewed as governance-heavy rather than routine”

So paradox signals are often part of the evidence base for the decision field,
not the whole decision field by themselves.

---

## 9. Typical interpretation patterns

### Case A — Deterministic PASS, quiet diagnostics

Decision-field interpretation:

- stable positive state
- low reviewer concern
- ordinary release confidence

### Case B — Deterministic PASS, noisy diagnostics

Decision-field interpretation:

- fragile PASS
- unstable positive state
- staging caution
- reviewer attention warranted

Important: deterministic PASS remains normative.

### Case C — Deterministic FAIL, lighter shadow pressure

Decision-field interpretation may note that the run is less unstable than
expected, but it must not silently convert FAIL into unblock.

### Case D — Repeated disagreement on one gate family

This is where the decision field becomes especially useful.

It can summarize the pattern as:

- governance debt,
- threshold-review pressure,
- evidence-coverage gap,
- or candidate for future policy discussion.

That is a stronger, more honest narrative than a one-run PASS/FAIL alone.

---

## 10. Recommended reading order

A practical reading order for one run is:

1. **Read the deterministic baseline**
   - `status.json`
   - Quality Ledger / report card

2. **Read the optional diagnostic context**
   - EPF shadow outputs
   - paradox / field overlays
   - external evidence status

3. **Read the decision-field interpretation**
   - reviewer-facing summary
   - stability or caution language
   - decision-engine style output, if present

This order keeps the decision field anchored to evidence.

---

## 11. What the decision field is good for

The decision field is especially valuable for:

- reviewer summaries
- governance dashboards
- staging-vs-production caution language
- stability narratives
- prioritizing follow-up work
- explaining why a run that technically passes still feels operationally fragile

It is **not** the right place to hide release-policy changes.

If release semantics need to change, that belongs in:

- policy,
- the main CI gate path,
- the status contract,
- and reviewed changelog-backed updates.

---

## 12. Design invariants

A healthy decision-field layer keeps these invariants stable:

- deterministic baseline remains normative
- decision-field outputs remain artifact-first
- optional shadow context stays optional
- missing diagnostic artifacts never become silent PASS
- reviewer language does not become an implicit release-policy rewrite
- the layer remains reproducible from archived run artifacts

If one of these changes, update the canonical docs in the same reviewed change.

---

## 13. Related docs

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PARADOX_RUNBOOK.md`
- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`
