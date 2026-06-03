# HARDENING_PLAN

## Boundary

This document describes repository hardening and release-grade infrastructure hardening around PULSEmech.

It is an operational plan for the v0 hardening pass.

It does not define PULSE.

PULSE is an artifact-bound release-authority mechanism for AI release decisions.

The PULSEmech authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

Hardening layers such as required checks, branch protection, dependency single truth, packaging layout, clean-install validation, signing, SLSA, Sigstore, in-toto, provenance attestations, and publication-surface clarity may strengthen the repository or the release-grade infrastructure around PULSEmech.

They are supporting layers.

They are not the definition of PULSE.

## Operating principle

Queryable, auditable, and reproducible system state is the operational basis of this repository.

Interfaces, dashboards, rendered reports, Pages surfaces, and summaries are views over recorded artifacts.

They are not the source of release authority unless explicitly promoted through recorded evidence, declared policy, materialized required gates, and strict fail-closed CI enforcement.

**Status:** maintainer-facing operational plan for the v0 hardening pass  
**Purpose:** make the v0 repository base stable, auditable, reproducible, and operationally reliable before later versioned work begins  
**Scope:** release semantics, CI enforcement, dependency truth, packaging, repository structure, and documentation clarity  
**Out of scope:** new features, new gates, new integrations, UI polish, public backlog expansion, and v2 roadmap work

---

## 1. Intent

This document defines the repository hardening sequence for the v0 hardening pass.

This is not a v2 roadmap.

This is not a public issue backlog.

This is not a feature-planning cycle.

The objective is to remove ambiguity and operational fragility from the repository and from release-grade infrastructure around PULSEmech.

The outcome should be a clean v0 base for later versioned evolution.

The PULSEmech authority path remains unchanged:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

---

## 2. PULSEmech invariants that must not be weakened

The hardening pass must preserve and clarify the following invariants:

1. `status.json` is the recorded release-state artifact.
2. `check_gates.py` enforces literal `true`-only required-gate PASS semantics.
3. Missing required gates fail closed.
4. The workflow-effective required gate set is materialized from the declared gate policy.
5. Renderers, dashboards, overlays, Pages, summaries, shadow runs, and diagnostic surfaces are non-authorizing by default.
6. Release semantics must remain reproducible from recorded artifacts, declared policy, materialized required gates, and fail-closed CI enforcement without depending on presentation layers.
7. Repository hardening layers may strengthen operation and reproducibility, but they do not redefine PULSEmech.

Any change that weakens or blurs these invariants is out of scope for this hardening pass.

---

## 3. Non-goals

During the hardening pass, the repository will not:

- add new gates
- add new external detectors
- add new policy layers
- add new UI/reporting capabilities
- expand the public roadmap
- open a broad issue backlog for future work
- start v2 planning in parallel with foundation hardening
- treat repository-hardening tasks as new PULSEmech capability work

The repository first becomes stable as a v0 base.

Only then does later roadmap work become relevant.

---

## 4. Working rules for the hardening pass

### 4.1 No feature work

No new capability work enters the repository during this pass.

### 4.2 No mixed PRs

A pull request may do one of the following:

- lock behavior
- harden CI
- unify dependencies
- refactor structure without changing behavior
- clarify documentation
- add focused regression coverage

It must not combine behavior changes with broad refactors.

### 4.3 Test first, refactor second

Critical behavior must be locked with tests before internal restructuring begins.

### 4.4 Keep current entrypoints temporarily stable

Existing scripts and CLI entrypoints may remain as compatibility wrappers during the hardening pass.

### 4.5 No public issue backlog yet

The unit of work during this pass is:

- internal plan
- focused branch
- focused PR
- explicit acceptance criteria

### 4.6 Rollback point after each phase

Every completed phase should end with an internal rollback tag, for example:

- `v0-hardening-00`
- `v0-hardening-01`
- `v0-hardening-02`

---

## 5. Critical risks to remove

These risks are repository and release-grade infrastructure risks around PULSEmech.

They are not definitions of PULSE.

### CR-01 — Release semantics are not locked tightly enough by tests

**Risk:** silent drift in gate meaning, exit behavior, or contract interpretation  
**Removed by:** Phase 1

### CR-02 — CI is not strict enough to block semantic regressions

**Risk:** a valid-looking PR can merge while breaking the release core  
**Removed by:** Phase 2

### CR-03 — Dependency truth is split across multiple sources

**Risk:** inconsistent installs, unclear runtime surface, reproducibility problems  
**Removed by:** Phase 3

### CR-04 — Script-heavy import structure is operationally fragile

**Risk:** brittle execution model, hidden import assumptions, poor maintainability  
**Removed by:** Phase 4

### CR-05 — External evidence behavior can still be misunderstood by humans

**Risk:** teams read aggregate pass as evidence presence, or confuse diagnostic surfaces with release-authority surfaces  
**Removed by:** Phase 1 and Phase 5 together

### CR-06 — Public surfaces can be read as release-grade authority without enough context

**Risk:** a Pages / Quality Ledger / rendered report surface is mistaken for the PULSEmech authority path  
**Removed by:** Phase 5

---

## 6. Execution sequence

The hardening pass follows this order:

1. **Phase 0 — Baseline freeze**
2. **Phase 1 — Contract lock**
3. **Phase 2 — CI hardening**
4. **Phase 3 — Dependency single truth**
5. **Phase 4 — Packaging and `src/` layout**
6. **Phase 5 — Release clarity and documentation cleanup**
7. **Phase 6 — Hardening audit**

This order is operational.

It should not be inverted without an explicit reason.

---

## 7. Phase plan

---

### Phase 0 — Baseline freeze

**Suggested branch/PR name:** `hardening/00-baseline-freeze`

**Objective:**  
Freeze the current observable repository truth before refactor work begins.

**Work items:**

- [ ] Create baseline fixtures for representative outputs:
  - [ ] `status.json`
  - [ ] JUnit output
  - [ ] SARIF output
  - [ ] stable report artifacts that matter operationally
- [ ] Add snapshot normalization for non-semantic fields such as timestamps where needed
- [ ] Record the current stable behavior that refactors are not allowed to change
- [ ] Ensure the baseline is reproducible enough to detect unintended semantic drift

**Deliverables:**

- [ ] Snapshot fixtures committed to the repository
- [ ] Small normalization helper for nondeterministic fields
- [ ] Explicit statement of stable surfaces and expected behavior

**Exit criteria:**

- [ ] The repository has baseline artifacts that can be compared after refactor work
- [ ] Time-dependent noise does not invalidate snapshot comparison
- [ ] No intentional behavior changes are introduced in this phase

**Rollback tag:** `v0-hardening-00`

---

### Phase 1 — Contract lock

**Suggested branch/PR name:** `hardening/01-contract-lock`

**Objective:**  
Lock the PULSEmech release behavior with tests.

**Work items:**

#### A. `check_gates.py` behavior lock

- [ ] Add tests proving `True` is the only passing value
- [ ] Add tests proving `False` fails
- [ ] Add tests proving `None` fails
- [ ] Add tests proving `"true"` fails
- [ ] Add tests proving `1` fails
- [ ] Add tests proving missing required gates fail closed
- [ ] Lock missing-gate vs non-True-gate exit behavior if distinct

#### B. `status.json` contract lock

- [ ] Add minimal valid `status.json` tests
- [ ] Add invalid structure tests for `gates`
- [ ] Add invalid `metrics.run_mode` tests
- [ ] Add tests for missing required minimal fields
- [ ] Add tests proving reader / summary fields cannot replace `gates.*`

#### C. Policy parser lock

- [ ] Add regression tests for multiline list handling
- [ ] Add regression tests for inline list handling
- [ ] Add regression tests for comments and spacing
- [ ] Add regression tests for empty lines and formatting variations
- [ ] Add tests proving the materialized required gate set is derived from declared policy

#### D. `augment_status.py` critical semantics lock

- [ ] Add refusal-delta ingest tests
- [ ] Add external summary present/absent tests
- [ ] Add strict external evidence mode tests
- [ ] Add parse-error fail-closed behavior tests
- [ ] Add tests proving evidence presence and aggregate pass are distinct concepts

**Deliverables:**

- [ ] Contract-focused test suite covering the release core
- [ ] Locked semantics for the most critical repository paths

**Exit criteria:**

- [ ] Critical release semantics are test-defined rather than informally assumed
- [ ] Semantic drift in the release core breaks tests immediately

**Rollback tag:** `v0-hardening-01`

---

### Phase 2 — CI hardening

**Suggested branch/PR name:** `hardening/02-ci-hardening`

**Objective:**  
Make semantic protection mandatory at merge time.

**Boundary:**  
CI hardening strengthens the repository around PULSEmech. It does not redefine PULSEmech.

**Work items:**

- [ ] Add or strengthen a dedicated contract test workflow
- [ ] Run it on pull requests and on `main`
- [ ] Make the following checks required:
  - [ ] `workflow-lint`
  - [ ] `contract-tests`
  - [ ] `pulse-core-ci`
- [ ] Ensure failing contract tests block merges
- [ ] Upload useful debug artifacts for failures where practical
- [ ] Keep CI focused on critical-path protection, not broad style enforcement
- [ ] Keep release-authority credentials and attestation credentials isolated where applicable

**Deliverables:**

- [ ] Required CI checks protecting the release core
- [ ] Branch protection aligned with critical repository behavior

**Exit criteria:**

- [ ] A PR that breaks core semantics cannot merge
- [ ] Contract validation is enforced automatically, not manually
- [ ] CI hardening remains a support layer around the PULSEmech authority path

**Rollback tag:** `v0-hardening-02`

---

### Phase 3 — Dependency single truth

**Suggested branch/PR name:** `hardening/03-deps-single-truth`

**Objective:**  
Establish one authoritative dependency model for repository reproducibility.

**Boundary:**  
Dependency single truth is repository reproducibility hardening. It is not a PULSEmech identity criterion.

**Decision:**  
`pyproject.toml` becomes the primary dependency truth.

**Work items:**

- [ ] Introduce `pyproject.toml`
- [ ] Define dependency groups:
  - [ ] core
  - [ ] dev/test
  - [ ] report/render
  - [ ] optional external-evals
- [ ] Demote `requirements.txt` from primary truth
- [ ] Keep `requirements.txt` only if needed as a generated/exported or compatibility file
- [ ] Keep `environment.yml` only as a convenience layer, not as a competing truth
- [ ] Add a clean-install smoke path in CI:
  - [ ] fresh environment
  - [ ] install core
  - [ ] run core path
  - [ ] validate schema
  - [ ] enforce gates

**Deliverables:**

- [ ] One documented authoritative dependency model
- [ ] Clean-install smoke validation for the core runtime path

**Exit criteria:**

- [ ] A fresh environment can install and run the core path without guesswork
- [ ] There is no ambiguity about which dependency surface is authoritative
- [ ] Dependency hardening remains separate from release-authority semantics

**Rollback tag:** `v0-hardening-03`

---

### Phase 4 — Packaging and `src/` layout

**Suggested branch/PR name:** `hardening/04-src-layout`

**Objective:**  
Replace fragile script-heavy structure with a maintainable package layout without changing PULSEmech behavior.

**Boundary:**  
Packaging improves maintainability. It does not change the release-authority tuple.

**Work items:**

- [ ] Introduce `src/`-based package layout
- [ ] Move critical logic into modules, for example:
  - [ ] `gates`
  - [ ] `status`
  - [ ] `render`
  - [ ] `cli`
- [ ] Preserve existing scripts as thin compatibility wrappers
- [ ] Remove `sys.path` injection from critical paths
- [ ] Separate pure logic from orchestration more clearly
- [ ] Keep output behavior stable unless explicitly justified and snapshot-reviewed

**Deliverables:**

- [ ] `src/` package layout
- [ ] Compatibility wrappers for current entrypoints
- [ ] No `sys.path` hack in the core path

**Exit criteria:**

- [ ] Internal structure is maintainable
- [ ] External entrypoints still work
- [ ] Baseline snapshots remain stable or are intentionally and explicitly updated
- [ ] PULSEmech release semantics remain unchanged

**Rollback tag:** `v0-hardening-04`

---

### Phase 5 — Release clarity and documentation cleanup

**Suggested branch/PR name:** `hardening/05-release-clarity`

**Objective:**  
Remove human ambiguity from repository and public reader surfaces.

**Work items:**

- [ ] Add a short `docs/core_mental_model.md`
- [ ] Add a short `docs/release_checklist.md`
- [ ] Add a small mode matrix clarifying:
  - [ ] demo
  - [ ] core
  - [ ] release-grade
- [ ] Explicitly define what is stable vs experimental
- [ ] Explicitly restate that diagnostic surfaces are non-authorizing by default
- [ ] Make external evidence semantics difficult to misread:
  - [ ] evidence presence is one thing
  - [ ] aggregate pass is another thing
  - [ ] release-grade enforcement must say which is required
- [ ] Clarify the public Pages / Quality Ledger boundary:
  - [ ] publication surface
  - [ ] reader surface
  - [ ] recorded artifact view
  - [ ] not independent release authority

**Deliverables:**

- [ ] Short operator-facing docs
- [ ] Clear differentiation between release-authority and diagnostic surfaces
- [ ] Clear release-grade guidance
- [ ] Public surface wording aligned with recorded artifact state

**Exit criteria:**

- [ ] A new engineer can quickly answer:
  - [ ] what is the source of release authority?
  - [ ] what blocks release?
  - [ ] what does not block release?
  - [ ] how do evidence presence and aggregate pass differ?
  - [ ] how should Pages / Quality Ledger be read?

**Rollback tag:** `v0-hardening-05`

---

### Phase 6 — Hardening audit

**Suggested branch/PR name:** `hardening/06-hardening-audit`

**Objective:**  
Verify that the repository is stable enough to serve as the v0 base for later evolution.

**Work items:**

- [ ] Perform clean clone validation
- [ ] Perform clean install validation
- [ ] Run the core path end to end
- [ ] Run the release-grade path end to end
- [ ] Validate schema behavior
- [ ] Validate gate enforcement behavior
- [ ] Validate artifact export behavior
- [ ] Compare outputs against baseline snapshots
- [ ] Walk through docs, workflows, and outputs to confirm they say the same thing
- [ ] Confirm that hardening documentation is framed as support infrastructure around PULSEmech

**Deliverables:**

- [ ] Final hardening audit result
- [ ] Explicit signoff that v0 is now a clean base

**Exit criteria:**

- [ ] All hardening checklist items pass
- [ ] Repository operation is predictable from documented artifacts and tests
- [ ] The hardening plan does not redefine PULSEmech

**Rollback tag:** `v0-hardening-06`

---

## 8. Merge discipline

During the hardening pass:

- one phase = one focused PR
- no mixed semantic change + broad refactor in the same PR
- snapshot changes must be justified
- wrapper compatibility should be preserved until the pass is complete
- every merged phase gets a rollback tag
- every PR description should include:
  - goal
  - critical risk removed
  - what is intentionally not included
  - acceptance criteria
  - rollback point
  - PULSEmech boundary statement when relevant

---

## 9. Minimum completion gate before later versioned work

No v2 planning track should begin until all of the following are true:

- [ ] release semantics are locked by tests
- [ ] CI required checks are active and enforced
- [ ] dependency truth is singular and documented
- [ ] clean install works for the core path
- [ ] the core runtime no longer depends on `sys.path` hacks
- [ ] release-authority and diagnostic surfaces are clearly separated
- [ ] external evidence semantics are clear in both tests and docs
- [ ] public reader surfaces distinguish core/demo/stubbed and release-grade/prod/materialized states
- [ ] baseline snapshots are stable and explainable
- [ ] the repository passes the hardening audit

This is the repository-hardening completion gate for later versioned work.

It is not the definition of PULSE.

---

## 10. After the hardening pass

Only after this document is completed should the repository move on to:

- public issue creation
- v2 planning
- capability expansion
- new integration work
- broader maintainer-process work
- roadmap expansion

The sequence is deliberate:

```text
first hardening, then roadmap
```

---

## 11. Definition of success

The v0 hardening pass is successful when the repository becomes:

- operationally predictable
- semantically locked
- CI-enforced
- dependency-clear
- structurally maintainable
- documentation-clear
- reproducible from recorded artifacts
- trustworthy as a base for future versioned work

The goal is not to make v0 larger.

The goal is to make the v0 base solid while preserving the PULSEmech authority path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```
