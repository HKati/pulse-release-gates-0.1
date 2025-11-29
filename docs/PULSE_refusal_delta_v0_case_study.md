# PULSE refusal-delta v0 – case study

This case study illustrates how to read the refusal-delta metrics
together with RDSI when comparing two model versions under PULSE.

The goal is not to derive new math, but to provide a concrete,
governance-friendly story for how a maintainer can reason about
refusal behaviour and stability.

---

## 1. Scenario

We have two model variants:

- **Model A (baseline)** – currently deployed, known-good refusal
  policy.
- **Model B (candidate)** – proposed update with a refined refusal
  policy.

We run the PULSE safe-pack for both, under the same policy/profile:

- same refusal-related gates (e.g. `pass_controls_refusal`,
  monotonicity invariants),
- same evaluation dataset and configuration,
- deterministic CI runner (as far as practical).

For each run we obtain:

- `status.json` + Quality Ledger,
- refusal-delta metrics (baseline vs candidate),
- RDSI for the overall decision.

---

## 2. Refusal-delta metrics (conceptual)

Refusal-delta is intended to give an audit-friendly view of how the
refusal behaviour changes between the baseline and the candidate.

Typical quantities (conceptually):

- Δ refusal rate on **unsafe** prompts (we want *higher* refusal):
  - positive Δ → candidate refuses more unsafe content.
- Δ refusal rate on **safe** prompts (we want *lower* refusal):
  - positive Δ → candidate refuses more safe content (potentially bad).
- confidence intervals or p-values on these deltas.

A simplified example (numbers illustrative):

```text
Unsafe prompts (should refuse):
  baseline_refusal_rate   = 0.82
  candidate_refusal_rate  = 0.90
  delta                   = +0.08  (CI: [+0.04, +0.11])

Safe prompts (should answer):
  baseline_refusal_rate   = 0.07
  candidate_refusal_rate  = 0.10
  delta                   = +0.03  (CI: [+0.01, +0.06])
```

Interpretation:

- On unsafe prompts, Model B refuses more often (good).
- On safe prompts, Model B also refuses more often (potentially
  over-conservative).

Refusal-delta does **not** make the decision by itself; it simply
quantifies the trade-off.

---

## 3. RDSI vs refusal-delta

RDSI is a per-run stability index: it measures how robust the release
decision is under small perturbations (e.g. sampling variation,
slight changes in conditions).

In this case:

- we compute RDSI for the Model B run under the current gate policy,
- we look at refusal-delta and RDSI **together**.

Example summary (illustrative):

```text
Model B run:

Overall decision: PASS
RDSI: 0.86  (Δ = -0.03 vs recent runs, within expected variation)

Refusal-delta:
  unsafe prompts: delta = +0.08  (CI: [+0.04, +0.11])
  safe prompts:  delta = +0.03  (CI: [+0.01, +0.06])
```

Key observations:

- RDSI is high enough to consider the decision stable under small
  perturbations.
- Refusal-delta shows a clear improvement on unsafe prompts, and a
  smaller (but non-zero) regression on safe prompts.

For a governance-minded maintainer, the question becomes:

> “Is this shift in the *safe* refusal rate acceptable, given the
>  gain on unsafe prompts?”

PULSE does not answer that value judgement; it provides stable,
auditable numbers to support it.

---

## 4. Governance decisions – patterns

This section sketches a few common patterns for human decision-making
based on refusal-delta + RDSI.

### 4.1 Clear improvement, stable

- Unsafe Δ positive and sizeable (candidate refuses more unsafe).
- Safe Δ close to zero (no meaningful change for safe prompts).
- RDSI high (decision stable).

Action:

- Treat as a **clear improvement**.
- Document in the Quality Ledger / changelog that refusal behaviour
  improved without measurable cost to safe prompts.
- Promote Model B (subject to normal review) and archive the metrics.

### 4.2 Trade-off: stricter but still acceptable

- Unsafe Δ positive and meaningful.
- Safe Δ positive but modest; CI suggests a small increase in safe
  refusals.
- RDSI still high.

Action:

- Recognise this as a **policy trade-off**:
  - safer on unsafe content,
  - slightly more conservative on safe content.
- Convene product/safety owners if needed to confirm that this
  trade-off is acceptable.
- If accepted:
  - merge with a short justification, referencing the refusal-delta
    numbers and RDSI in the PR / governance notes.
- If not accepted:
  - either adjust thresholds/policies,
  - or iterate on the candidate model before deployment.

### 4.3 Regression: too many safe refusals

- Unsafe Δ near zero (no significant gain).
- Safe Δ positive and significant (much more safe content refused).
- RDSI may still be high (the regression is stable but undesirable).

Action:

- Treat this as a **regression**:
  - refusal-delta shows a clear increase in over-refusal, without
    improvement on unsafe prompts.
- Recommended:
  - reject or rework the candidate,
  - possibly tighten gates that protect utility on safe prompts (e.g.
    by using refusal-delta thresholds as additional signals).

### 4.4 Unstable situation

- Refusal-delta is noisy (wide confidence intervals, small sample).
- RDSI noticeably lower than usual:
  - decisions flip under small perturbations,
  - or the gate sits near the refusal thresholds.

Action:

- Consider this an **unstable** situation:
  - gather more data,
  - re-run evaluations with larger samples,
  - check whether the policy or the dataset is aligned with the
    intended refusal behaviour.
- Avoid making strong policy changes based on a single, unstable run.

---

## 5. How this fits into PULSE

Where does this case study sit in the broader PULSE picture?

- Core deterministic gates:
  - still enforce refusal-related invariants and thresholds.
- Refusal-delta:
  - adds a more nuanced, audit-ready view of how refusal behaviour
    changes between versions.
- RDSI:
  - ensures that the underlying decision is not fragile under small
    perturbations.
- Governance:
  - uses refusal-delta + RDSI as input to human decisions, not as
    automatic gate-flippers.

In other words:

> PULSE keeps the gates deterministic and fail-closed, while refusal-
> delta and RDSI provide the narrative and numbers needed to explain
> *why* a policy change is acceptable or not.

---

## 6. Suggested workflow

A simple workflow for using refusal-delta and RDSI in practice:

1. Run PULSE safe-pack for baseline and candidate models.
2. Inspect refusal-delta metrics (unsafe vs safe prompts).
3. Check RDSI for the candidate run.
4. Classify the situation using the patterns above
   (clear improvement, trade-off, regression, unstable).
5. Record the decision and reasoning in:
   - the PR description,
   - the Quality Ledger / changelog,
   - or your internal governance system.

This closes the loop between:
- quantitative metrics (refusal-delta, RDSI),
- deterministic gates,
- and human decisions about model and policy evolution.
