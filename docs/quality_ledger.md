# PULSE Quality Ledger

> Human-readable explanation layer over `status.json`.

The **Quality Ledger** is the HTML report generated from  
`PULSE_safe_pack_v0/artifacts/status.json`.

It is intended for humans who need to review, approve, or audit a release decision:

- release owners and product leads,
- safety / red-team reviewers,
- compliance & audit,
- platform / MLOps teams operating CI.

The main artefact is:

- local: `PULSE_safe_pack_v0/artifacts/report_card.html`
- live demo: the GitHub Pages snapshot linked from the README

> CI always treats `status.json` as the source of truth.  
> The Quality Ledger is a view over that JSON, not a second decision engine.

---

## 1. Where it comes from

When you run:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

PULSE generates at least:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html` ← the Quality Ledger

In the default artifact-first CI model, the ledger is uploaded as a workflow artefact.

GitHub-native publication surfaces — such as PR comments or Pages snapshots —  
should be treated as separate opt-in workflows with explicit permissions,  
not as required parts of the main gating path.

No extra configuration is required to render the ledger locally:  
if `status.json` is present and valid, the safe-pack can produce the report.

---

## 2. What problem the Quality Ledger solves

`status.json` is machine-friendly but dense:

- nested objects,
- metrics,
- thresholds,
- gate booleans,
- optional external summaries.

The Quality Ledger makes that information reviewable by humans. It:

- flattens important signals into tables and panels,
- groups evidence by release-decision questions,
- surfaces thresholds and PASS/FAIL outcomes together,
- adds short explanations for failed or borderline gates,
- keeps the review anchored to one immutable run artefact.

It is intentionally conservative:  
if something is unclear or missing in the JSON, the ledger should surface that ambiguity instead of silently presenting it as a PASS.

---

## 3. Typical structure

A typical Quality Ledger includes the following sections.

### Header / run metadata

Usually includes:

- model / service or release identifier,
- commit or tag,
- CI run id / timestamp,
- profile or run mode.

### Decision strip

A compact banner with:

- overall decision (for example `FAIL`, `STAGE-PASS`, or `PROD-PASS`),
- RDSI and related stability signals when present,
- any break-glass note or justification, if the workflow surfaced one.

### Safety gates

A table of release-relevant safety checks, for example:

- refusal / control checks,
- sanitization-related gates,
- other deterministic invariants emitted into `gates.*`.

### Quality gates

Product-facing checks such as:

- groundedness,
- consistency,
- fairness,
- latency / cost / SLO budgets.

### Stability / refusal-delta section

When refusal-delta metrics are present, the ledger can surface:

- `metrics.refusal_delta_n`
- `metrics.refusal_delta`
- `metrics.refusal_delta_ci_low`
- `metrics.refusal_delta_ci_high`
- `metrics.refusal_policy`
- `metrics.refusal_p_mcnemar`
- `metrics.refusal_pass_min`
- `metrics.refusal_pass_strict`
- `gates.refusal_delta_pass`

### External detectors (optional)

If external summaries were folded into `status.json`, the ledger can show:

- one row per detector,
- measured value,
- configured threshold,
- detector-level PASS/FAIL,
- aggregate external result.

### Traceability / archive hints

The ledger can point reviewers to:

- `status.json`,
- optional JUnit / SARIF exports,
- detector summaries,
- other immutable run artefacts useful for audit or incident review.

---

## 4. Relationship to status.json

The Quality Ledger is a pure reader / renderer.

It should only explain data already present in immutable run artefacts, especially:

- top-level metadata fields,
- `metrics.*`,
- `gates.*`,
- optional `external.*` summaries.

It must not:

- redefine release semantics,
- compute a different gate outcome than CI,
- silently upgrade unknown / missing evidence into PASS.

If a discrepancy is ever observed between the ledger and CI behaviour,  
`status.json` and `check_gates.py` win; the renderer should be considered buggy.

For the stable public contract, see `STATUS_CONTRACT.md`.  
For the fuller walkthrough, see `status_json.md`.

---

## 5. How humans are expected to use it

Typical review flow:

### 1. Scan the decision strip

- Is the run `FAIL`, `STAGE-PASS`, or `PROD-PASS`?
- Are stability signals clearly good, borderline, or missing?

### 2. Inspect failed or borderline gates

- any failed safety gates,
- any failed quality gates,
- any failing external detector rows,
- any refusal-delta or stability warnings.

### 3. Read the justification

- which threshold was applied,
- which metric missed it,
- whether the issue looks like a data / quality / safety / ops problem.

### 4. Archive the decision context

- keep the ledger together with `status.json`,
- keep optional exports and detector summaries when they exist,
- retain enough context for future audit or incident response.

Because the ledger is static HTML, it can be attached to tickets, archived with deployment material, or shared with reviewers without giving them CI access.

---

## 6. Extensibility rules

New sections can be added to the Quality Ledger as long as they remain explanation layers.

Safe extensions include:

- extra fairness slices,
- organisation-specific compliance checklists,
- richer detector panels,
- reviewer-facing trace summaries.

The invariants are:

- CI logic remains centralised in the safe-pack and gate scripts,
- the ledger remains deterministic and reproducible,
- release semantics stay anchored to `status.json` and gate enforcement,
- optional UI / Pages surfaces remain pure readers of immutable run artefacts.

---

## 7. Minimal reviewer checklist

Before signing off a release from the ledger, confirm:

- the run identity is clear,
- the overall decision is clear,
- failed gates are visible and explained,
- any external evidence is clearly present / absent,
- the underlying `status.json` for this run is archived.
