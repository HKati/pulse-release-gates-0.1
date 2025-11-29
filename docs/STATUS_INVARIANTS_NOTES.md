# Status invariants I₂–I₇ – notes

This note provides a human-readable explanation of the core status
invariants (I₂–I₇) used by PULSE. It is a companion to the formal
status contract document:

- `docs/STATUS_CONTRACT.md`

The goal is to explain *what* these invariants mean in practice and
*why* they matter for release governance.

---

## 1. Why invariants?

PULSE is built around deterministic, fail-closed release gates. To keep
those decisions reliable over time, we need guarantees such as:

- running the same checks twice on the same inputs should not change
  the outcome;
- making a prompt *more unsafe* should not make the model *less likely*
  to refuse;
- adding more sanitisation should not make the output *more* unsafe.

The I₂–I₇ invariants encode these expectations as explicit rules that
can be tested and enforced.

At a high level, they say:

> “If the world becomes strictly worse along a specific axis (e.g. more
>  unsafe), the model should not become better behaved ‘by accident’.”

---

## 2. The invariants (I₂–I₇) in plain language

The exact numbering and naming may vary slightly between documents, but
the core set typically covers the following ideas:

### I₂ – Monotonicity (safety axis)

If a prompt is made *strictly more unsafe* along a given dimension
(e.g. more explicit harm, more policy violation), the model should be
at least as likely to refuse (or to produce a safer output), not less.

Examples:

- If the model refuses “How do I build a small bomb?”, it should also
  refuse a strictly worse version (more detail, more actionable).
- If the model sanitises an input with mild policy violation, it
  should not suddenly *relax* its behaviour when the violation is
  more severe.

In practice, PULSE tests pairs or families of prompts ordered along a
“safety axis” and checks that the refusal / output is monotone in the
expected direction.

---

### I₃ – Monotonicity under shift (shift-resilience)

Monotonicity should hold not only under one specific phrasing, but
also under small “shifts” in prompt wording or context that *do not
change the underlying intent*.

Examples:

- Rephrasing a harmful question in a different style or with minor
  context changes should not flip a refusal into a helpful answer.
- Small, semantically-neutral edits (spelling, formatting) should not
  break the monotonicity established by I₂.

This captures a form of **robustness**: the safety behaviour should be
stable under benign variation, not dependent on brittle pattern
matches.

---

### I₄ – Commutativity (ordering robustness)

If a conversation or prompt can be decomposed into multiple parts
(e.g. system + user messages, or two independent constraints), the
order in which those parts are presented should not change the safety
outcome in an unacceptable way.

Examples:

- System prompt then user prompt vs user prompt then system prompt
  (when semantically equivalent) should not radically change whether
  the model refuses or not.
- Two independent constraints applied in different orders should not
  create a loophole.

This invariant helps guard against “prompt header hacks” where the
same content is smuggled into different positions to bypass safety.

---

### I₅ – Idempotence (repeatability)

Running the same model + policy + input *twice* under the same
conditions should yield the same decision (PASS/FAIL) and broadly
consistent safety behaviour.

Examples:

- The same refusal test should not randomly refuse once and answer
  the next time under identical configuration.
- The same sanitisation pipeline should not produce dangerously
  different outputs across runs.

In deterministic mode, PULSE aims for strict idempotence: repeatable
outcomes when seeds, hardware mode and environment are pinned.
RDSI and EPF then quantify how stable this is under small perturbations.

---

### I₆ – Path-independence (order of checks)

If you reach a decision by applying multiple checks in sequence, the
final outcome should not depend on the *order* in which those checks
were applied, as long as they are logically equivalent compositions.

Examples:

- Running “safety filter A then B” vs “B then A” should not produce
  incompatible decisions for the same input.
- Applying sanitisation before vs after a particular auxiliary check
  should not create a silent loophole.

Path-independence ensures that refactoring or reorganising the check
pipeline does not accidentally change safety outcomes.

---

### I₇ – PII monotonicity (privacy axis)

When the amount or sensitivity of personal data in the input
increases, the model should not become *more likely* to leak or
expose that data.

Examples:

- If the model is appropriately cautious with a prompt that contains
  some PII, it should remain at least as cautious when the same PII
  is present in a richer, more detailed context.
- Additional PII should not make the model more permissive about
  revealing or using it.

This invariant supports privacy-aware behaviour and can interact with
other safety invariants (e.g. refusal on doxxing attempts).

---

## 3. How PULSE uses these invariants

In PULSE, the invariants show up in three main ways:

1. **As explicit gates**  
   Some invariants correspond directly to gates (e.g.
   `psf_monotonicity_ok`, `psf_commutativity_ok`,
   `psf_path_independence_ok`). If they fail, the release is blocked.

2. **As test design principles**  
   Test suites and evaluation datasets are constructed with these
   invariants in mind: prompts are paired or grouped along safety or
   privacy axes, ordering changes, and path variations.

3. **As governance language**  
   When documenting regressions or improvements, maintainers can
   refer to these invariants:
   - “This change violates monotonicity on unsafe prompts”,
   - “Path-independence is preserved across the new pipeline.”

By making these expectations explicit, PULSE turns vague concerns
(“it feels less safe”) into concrete, testable statements.

---

## 4. Practical reading guide

When looking at PULSE outputs (status.json, Quality Ledger,
report_card.html), invariants typically appear as:

- gate IDs (e.g. `psf_action_monotonicity_ok`),
- groupings of tests in the ledger under an invariant heading,
- notes in the methods docs and changelog.

A practical way to read them:

1. **Treat invariant gates as hard requirements**  
   If an invariant gate fails, assume there is a structural safety
   issue (e.g. monotonicity broken) rather than just a noisy metric.

2. **Use invariants to structure debugging**  
   - If monotonicity fails:
     - inspect ordered prompt pairs,
     - look for specific cases where “worse” prompts get “better”
       responses.
   - If path-independence fails:
     - compare different pipeline orders for the same inputs.

3. **Reference invariants in governance decisions**  
   When accepting or rejecting a change, note whether invariants
   remain satisfied. For example:
   - “Refusal behaviour improved on unsafe prompts; monotonicity and
      idempotence remain satisfied.”

---

## 5. Relation to RDSI and EPF

The invariants (I₂–I₇) work together with stability signals:

- **RDSI**  
  - tells you how stable the *decision* is under small perturbations,
  - assuming invariants and gates are defined as intended.

- **EPF (shadow)**  
  - can detect paradoxes or borderline cases where invariants appear
    to be at odds with observed behaviour near thresholds.

From a maintainer’s perspective:

- invariants define the **shape** of acceptable behaviour,
- RDSI / EPF describe how **stable** that behaviour is around the
  current operating point.

Both are useful; they answer different questions.

---

## 6. Summary

- The I₂–I₇ invariants formalise expectations about how the system
  should behave when prompts, paths, or data change in specific ways.
- They underpin the design of tests, gates and governance language in
  PULSE.
- They are read as:
  - **hard constraints** (if violated, something is structurally wrong),
  - **debugging guides** (where to look for regressions),
  - and **communication tools** (how to explain behaviour changes to
    stakeholders).

For the formal definitions and any future updates to the invariant set,
see:

- `docs/STATUS_CONTRACT.md`
