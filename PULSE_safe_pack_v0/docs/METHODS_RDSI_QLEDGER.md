# Methods: RDSI & Quality Ledger (v0.1)

> Portable methods note for decision stability and human-readable release review.

This document explains the methodological role of:

- **RDSI** — Release Decision Stability Index
- **Quality Ledger** — the human-readable review layer over a PULSE run

It is intentionally short and portable.

For the fuller repo-level walkthroughs, see:

- [`../../docs/status_json.md`](../../docs/status_json.md)
- [`../../docs/STATUS_CONTRACT.md`](../../docs/STATUS_CONTRACT.md)
- [`../../docs/quality_ledger.md`](../../docs/quality_ledger.md)

---

## 1. Scope

PULSE separates:

- the **machine-readable release artefact** (`status.json`),
- the **human-readable review surface** (`report_card.html`),
- and optional stability / statistical interpretation such as **RDSI**.

The goal of this note is to describe the methods layer without over-coupling it
to one exact renderer layout.

---

## 2. RDSI — Release Decision Stability Index

### Goal

RDSI is intended to quantify how stable a release decision remains under small,
controlled perturbations, such as:

- seed variation,
- ordering variation,
- retry / repeat-run variation,
- other bounded replay changes that should not change semantics.

Conceptually:

- **RDSI = 1** means the decision is highly stable,
- lower values indicate greater instability or sensitivity.

### What RDSI is for

RDSI helps answer:

- “Would we make the same release decision again under nearby conditions?”
- “Is this PASS/FAIL result robust, or fragile?”
- “Should this run be treated as confidently releasable or as operationally borderline?”

### Normative vs diagnostic role

RDSI is primarily a **stability signal**.

Unless a repository explicitly promotes it into required release policy, RDSI
should be treated as:

- review guidance,
- audit context,
- and a stability summary for humans and dashboards.

It should not silently replace deterministic gate outcomes.

### Where it is surfaced

When present, RDSI is typically surfaced in:

- `status.json` under `metrics.*`
- the Quality Ledger / HTML report
- audit or reviewer-facing summaries

The exact field layout can evolve, but the methodological meaning should remain
stable.

---

## 3. Quality Ledger

### Purpose

The **Quality Ledger** is the human-readable explanation layer over one PULSE run.

Its job is to help a reviewer understand:

- what was tested,
- which gates passed or failed,
- which metrics mattered,
- whether the decision looks stable,
- and what should be archived for later audit.

### What it is not

The Quality Ledger is **not** a second decision engine.

It must not:

- recompute release semantics independently,
- silently reinterpret missing evidence as PASS,
- disagree with the normative machine-readable artefacts.

If the ledger and CI ever disagree, the underlying machine-readable artefact
wins, and the renderer should be treated as buggy.

### Typical content

A useful ledger usually includes:

- run identity / provenance,
- decision summary,
- gate outcomes,
- key metrics and thresholds,
- optional stability context (including RDSI when available),
- optional external-evidence panels,
- notes / waivers / review context where applicable.

The exact presentation may vary, but the interpretation layer should remain
purely explanatory.

---

## 4. Current artefact relationship

In the current safe-pack flow, the main entrypoint produces:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Recommended interpretation:

- `status.json` = source of truth for machine-readable release state
- `report_card.html` = human-readable Quality Ledger view over that state

This keeps the release model:

- deterministic,
- artifact-first,
- and audit-friendly.

---

## 5. Recommended interpretation rules

### For machine consumers

- read gate outcomes from the normative machine-readable artefact first,
- treat stability and ledger layers as explanation unless policy says otherwise.

### For human reviewers

Use the ledger to answer:

1. What is the release decision?
2. Which gates or metrics drove it?
3. Is the decision stable enough to trust?
4. What evidence should be archived with the release record?

### For archivists / auditors

Archive together, when available:

- `status.json`
- `report_card.html`
- optional detector summaries
- optional JUnit / SARIF exports
- any explicit review note or waiver attached to the run

---

## 6. Statistical notes (short)

When proportions or proportion deltas are reported, preferred methods include:

- **Wilson score intervals** for single proportions
- **Newcombe score-based intervals** for differences of proportions
- **McNemar’s test** for paired binary outcomes / flip analysis

These methods are preferred over weaker large-sample approximations when sample
sizes are modest or rates are near 0 or 1.

At minimum, reports should make clear:

- what was measured,
- sample size,
- chosen interval / test family,
- and the resulting operational interpretation.

---

## 7. Method invariants

The method layer should preserve these invariants:

- release semantics remain anchored to the machine-readable artefact,
- human-readable reports remain pure readers / renderers,
- stability summaries do not silently override fail-closed gates,
- archival surfaces remain reproducible from immutable run artefacts.

---

## 8. References (classical statistics)

- Wilson, E. B. (1927). *Probable inference, the law of succession, and statistical inference*. Journal of the American Statistical Association, 22(158), 209–212.
- Newcombe, R. G. (1998a). *Two-sided confidence intervals for the single proportion: comparison of seven methods*. Statistics in Medicine, 17, 857–872.
- Newcombe, R. G. (1998b). *Interval estimation for the difference between independent proportions: comparison of eleven methods*. Statistics in Medicine, 17, 873–890.
- McNemar, Q. (1947). *Note on the sampling error of the difference between correlated proportions or percentages*. Psychometrika, 12(2), 153–157.
