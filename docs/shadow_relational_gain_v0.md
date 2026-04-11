# Shadow Relational Gain v0

Relational Gain v0 is a **shadow-only** diagnostic layer.

It evaluates relational gain signals from a dedicated input artifact,
writes a separate shadow artifact, and may fold a summary into
`status.json` under `meta.relational_gain_shadow`.

It does **not** participate in normative release authority.

---

## Status

Relational Gain v0 is implemented as a working shadow module with:

- dedicated checker logic,
- dedicated fold-in logic,
- dedicated runner,
- dedicated schema,
- layer-specific contract checker,
- canonical PASS / WARN / FAIL fixtures,
- checker regression tests,
- non-interference tests,
- and a dedicated shadow workflow.

This means the module is no longer just a research note or ad hoc
shadow experiment.

It now has an explicit machine-readable and testable contract surface.

Registry / promotion-state updates should still be recorded separately in
repo-level shadow inventory surfaces.

---

## Role

Relational Gain v0 exists to read relational gain input and produce a
bounded diagnostic verdict over two dimensions:

- edge gain
- cycle gain

It is intended for shadow review, artifact analysis, and governance
visibility.

It is **not** a release gate.

---

## Non-goals

Relational Gain v0 does **not**:

- write under `gates.*`,
- modify required gate sets,
- change `check_gates.py` release semantics,
- convert a blocked release into an allowed one,
- or gain normative authority by being present in `status.json`.

---

## Current flow

The current shadow flow is:

1. `check_relational_gain.py`
   - reads relational gain input
   - computes edge/cycle metrics
   - emits a shadow artifact

2. `fold_relational_gain_shadow.py`
   - reads the shadow artifact
   - folds a summary into `status["meta"]["relational_gain_shadow"]`

3. `run_relational_gain_shadow.py`
   - orchestrates checker + artifact write + fold-in

The fold-in is additive and non-normative.

---

## Shadow artifact

Current artifact path:

```text
PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json
```

Current artifact schema:

```text
schemas/relational_gain_shadow_v0.schema.json
```

Current artifact contract checker:

```text
PULSE_safe_pack_v0/tools/check_relational_gain_contract.py
```

The current artifact shape is tied to the actual output of
`check_relational_gain.py` and includes:

- `checker_version`
- `verdict`
- `input.path`
- `metrics.checked_edges`
- `metrics.checked_cycles`
- `metrics.max_edge_gain`
- `metrics.max_cycle_gain`
- `metrics.warn_threshold`
- `metrics.offending_edges`
- `metrics.offending_cycles`
- `metrics.near_boundary_edges`
- `metrics.near_boundary_cycles`

This page documents the **current actual artifact**, not a future
migrated common-envelope form.

---

## Verdict semantics

Relational Gain v0 emits one of:

- `PASS`
- `WARN`
- `FAIL`

Interpretation:

- `PASS`
  - no offending edge/cycle gains
  - no near-boundary edge/cycle gains
- `WARN`
  - no offending gains
  - at least one near-boundary gain
- `FAIL`
  - at least one offending gain

These verdicts are checker-local shadow diagnostics.

They do **not** become release verdicts.

---

## Fold-in surface

If fold-in succeeds, the shadow summary appears at:

```text
status["meta"]["relational_gain_shadow"]
```

The folded summary is expected to expose the current shadow result in a
compact status-facing form, including:

- `verdict`
- `max_edge_gain`
- `max_cycle_gain`
- `warn_threshold`
- `checked_edges`
- `checked_cycles`
- artifact reference metadata

Fold-in must remain:

- optional,
- additive,
- non-normative,
- and removable when the artifact is stale or absent.

---

## Neutral absence

Relational Gain v0 supports neutral absence through runner-level
`--if-input-present` behavior.

In that mode:

- missing input does not become a hard failure,
- no shadow artifact is required,
- stale `meta.relational_gain_shadow` content is removed,
- unrelated `meta.*` content is preserved,
- and release semantics remain unchanged.

Neutral absence is a shadow hygiene rule, not a release rule.

---

## Contract-hardening surfaces

Relational Gain v0 now has the following hardening surfaces:

### Layer-specific schema

```text
schemas/relational_gain_shadow_v0.schema.json
```

### Layer-specific contract checker

```text
PULSE_safe_pack_v0/tools/check_relational_gain_contract.py
```

### Canonical fixtures

```text
tests/fixtures/relational_gain_shadow_v0/pass.json
tests/fixtures/relational_gain_shadow_v0/warn.json
tests/fixtures/relational_gain_shadow_v0/fail.json
```

### Checker regression tests

```text
tests/test_check_relational_gain_contract.py
```

### Non-interference coverage

```text
tests/test_relational_gain_non_interference.py
```

### Dedicated workflow

```text
.github/workflows/relational_gain_shadow.yml
```

---

## Non-interference guarantee

Relational Gain v0 must remain non-interfering with normative release
behavior.

The required invariant is:

- same `check_gates.py`
- same required gate set
- same release outcome
- before and after Relational Gain fold-in

This is covered by dedicated end-to-end non-interference tests.

The shadow layer may add or remove `meta.relational_gain_shadow`, but it
must not alter the authoritative `gates` surface or the release result
derived from it.

---

## Invariants

Relational Gain v0 must satisfy all of the following:

- it remains shadow-only
- it never writes under `gates.*`
- it never changes required gate meaning
- fold-in is additive only
- exact artifact `checker_version` is enforced
- neutral absence remains neutral
- stale shadow state may be removed
- unrelated `meta.*` content must be preserved
- release outcomes must remain identical before and after fold-in

---

## File map

### Docs

```text
docs/shadow_relational_gain_v0.md
docs/papers/equivalence_drift_and_grounded_new_element.md
```

### Tools

```text
PULSE_safe_pack_v0/tools/check_relational_gain.py
PULSE_safe_pack_v0/tools/check_relational_gain_contract.py
PULSE_safe_pack_v0/tools/fold_relational_gain_shadow.py
PULSE_safe_pack_v0/tools/run_relational_gain_shadow.py
```

### Schema

```text
schemas/relational_gain_shadow_v0.schema.json
```

### Fixtures

```text
tests/fixtures/relational_gain_v0/*
tests/fixtures/relational_gain_shadow_v0/*
```

### Tests

```text
tests/test_check_relational_gain.py
tests/test_check_relational_gain_contract.py
tests/test_fold_relational_gain_shadow.py
tests/test_run_relational_gain_shadow.py
tests/test_relational_gain_non_interference.py
```

### Workflow

```text
.github/workflows/relational_gain_shadow.yml
```

---

## Promotion boundary

Relational Gain v0 is now a hardened shadow module, but it is still
shadow-only.

Any movement beyond that must be explicit.

In particular, none of the following are implied by this hardening work:

- advisory authority,
- policy binding,
- required-gate promotion,
- release-required status.

Those changes, if they ever happen, must be recorded separately in
policy and registry surfaces.

---

## Summary

Relational Gain v0 is now a fully implemented and contract-hardened
shadow module.

It is documented, schema-bound, checker-validated, regression-tested,
non-interference-tested, and workflow-wired.

It remains strictly non-normative, and its role is to add disciplined
shadow visibility without changing release authority.
