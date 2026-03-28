# HARDENING_PLAN

## Governing principle

Modern development is built on queryable, auditable, and reproducible system state; interfaces are views, never the source of truth.

**Status:** maintainer-facing working plan for the v0 maturity pass
**Purpose:** make v0 stable, auditable, and boringly reliable before any v2 work begins  
**Scope:** release semantics, CI enforcement, dependency truth, packaging, repository structure, and documentation clarity  
**Out of scope:** new features, new gates, new integrations, UI polish, public backlog expansion, and v2 roadmap work

---

## 1. Intent

This document defines the repository hardening sequence for the **v0 maturity pass**.

This is **not** a v2 roadmap.  
This is **not** a public issue backlog.  
This is **not** a feature-planning cycle.

The objective is to remove critical ambiguity and operational fragility from the repository so that v0 becomes a clean, trusted base for later versioned evolution.

---

## 2. Normative invariants that must not be weakened

The maturity pass must preserve and clarify the following invariants:

1. `status.json` is the normative release artifact.
2. `check_gates` enforces **True-only** gate semantics.
3. Missing required gates fail closed.
4. The gate set required by CI is normative.
5. Renderers, dashboards, overlays, Pages, shadow runs, and other diagnostic surfaces are **non-normative**.
6. Release semantics must remain reproducible from normative artifacts without depending on presentation layers.

Any change that weakens or blurs these invariants is out of scope for this hardening pass.

---

## 3. Non-goals

During the maturity pass, the repository will **not**:

- add new gates
- add new external detectors
- add new policy layers
- add new UI/reporting capabilities
- expand the public roadmap
- open a broad issue backlog for future work
- start v2 planning in parallel with foundation hardening

The repository first becomes clean and mature.  
Only then does future planning become relevant.

---

## 4. Working rules for the maturity pass

### 4.1 No feature work
No new capability work enters the repository during this pass.

### 4.2 No mixed PRs
A pull request may do **one** of the following:
- lock behavior
- harden CI
- unify dependencies
- refactor structure without changing behavior
- clarify documentation

It must not combine behavior changes with broad refactors.

### 4.3 Test first, refactor second
Critical behavior must be locked with tests **before** internal restructuring begins.

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
- `v0-maturity-00`
- `v0-maturity-01`
- `v0-maturity-02`

---

## 5. Critical risks to remove

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
**Risk:** teams read aggregate pass as evidence presence, or confuse diagnostic surfaces with normative surfaces  
**Removed by:** Phase 1 and Phase 5 together

---

## 6. Execution sequence

The hardening pass follows this order:

1. **Phase 0 — Baseline freeze**
2. **Phase 1 — Contract lock**
3. **Phase 2 — CI hardening**
4. **Phase 3 — Dependency single truth**
5. **Phase 4 — Packaging and `src/` layout**
6. **Phase 5 — Release clarity and doc cleanup**
7. **Phase 6 — Maturity audit**

This order is intentional and should not be inverted.

---

## 7. Phase plan

---

### Phase 0 — Baseline freeze

**Suggested branch/PR name:** `hardening/00-baseline-freeze`

**Objective:**  
Freeze the current observable truth before any refactor begins.

**Work items:**
- [ ] Create baseline fixtures for representative outputs:
  - [ ] `status.json`
  - [ ] JUnit output
  - [ ] SARIF output
  - [ ] any stable report artifact that matters operationally
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

**Rollback tag:** `v0-maturity-00`

---

### Phase 1 — Contract lock

**Suggested branch/PR name:** `hardening/01-contract-lock`

**Objective:**  
Lock the normative release behavior with tests.

**Work items:**

#### A. `check_gates` behavior lock
- [ ] Add tests proving `True` is the only passing value
- [ ] Add tests proving `False` fails
- [ ] Add tests proving `None` fails
- [ ] Add tests proving `"true"` fails
- [ ] Add tests proving `1` fails
- [ ] Add tests proving missing required gates fail closed
- [ ] Lock missing-gate vs non-True-gate exit behavior if distinct

#### B. `status` contract lock
- [ ] Add minimal valid `status.json` tests
- [ ] Add invalid structure tests for `gates`
- [ ] Add invalid `metrics.run_mode` tests
- [ ] Add tests for missing required minimal fields

#### C. Policy parser lock
- [ ] Add regression tests for multiline list handling
- [ ] Add regression tests for inline list handling
- [ ] Add regression tests for comments and spacing
- [ ] Add regression tests for empty lines and formatting variations

#### D. `augment_status` critical semantics lock
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
- [ ] Any semantic drift in the release core breaks tests immediately

**Rollback tag:** `v0-maturity-01`

---

### Phase 2 — CI hardening

**Suggested branch/PR name:** `hardening/02-ci-hardening`

**Objective:**  
Make semantic protection mandatory at merge time.

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

**Deliverables:**
- [ ] Required CI checks protecting the release core
- [ ] Branch protection aligned with critical repository behavior

**Exit criteria:**
- [ ] A PR that breaks core semantics cannot merge
- [ ] Contract validation is enforced automatically, not manually

**Rollback tag:** `v0-maturity-02`

---

### Phase 3 — Dependency single truth

**Suggested branch/PR name:** `hardening/03-deps-single-truth`

**Objective:**  
Establish one authoritative dependency model.

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

**Rollback tag:** `v0-maturity-03`

---

### Phase 4 — Packaging and `src/` layout

**Suggested branch/PR name:** `hardening/04-src-layout`

**Objective:**  
Replace the fragile script-heavy structure with a maintainable package layout without changing normative behavior.

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
- [ ] Baseline snapshots remain stable or intentionally and explicitly updated

**Rollback tag:** `v0-maturity-04`

---

### Phase 5 — Release clarity and documentation cleanup

**Suggested branch/PR name:** `hardening/05-release-clarity`

**Objective:**  
Remove human ambiguity from the repository surface.

**Work items:**
- [ ] Add a short `docs/core_mental_model.md`
- [ ] Add a short `docs/release_checklist.md`
- [ ] Add a small mode matrix clarifying:
  - [ ] demo
  - [ ] core
  - [ ] release-grade
- [ ] Explicitly define what is stable vs experimental
- [ ] Explicitly restate that diagnostic surfaces are non-normative
- [ ] Make external evidence semantics impossible to misread:
  - [ ] evidence presence is one thing
  - [ ] aggregate pass is another thing
  - [ ] release-grade enforcement must say which is required

**Deliverables:**
- [ ] Short operator-facing docs
- [ ] Clear differentiation between normative and diagnostic surfaces
- [ ] Clear release-grade guidance

**Exit criteria:**
- [ ] A new engineer can quickly answer:
  - [ ] what is the source of truth?
  - [ ] what blocks release?
  - [ ] what does not block release?
  - [ ] how do evidence presence and aggregate pass differ?

**Rollback tag:** `v0-maturity-05`

---

### Phase 6 — Maturity audit

**Suggested branch/PR name:** `hardening/06-maturity-audit`

**Objective:**  
Verify that the repository is now mature enough to serve as the base for later evolution.

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

**Deliverables:**
- [ ] Final maturity audit result
- [ ] Explicit signoff that v0 is now a clean base

**Exit criteria:**
- [ ] All maturity checklist items pass
- [ ] The repository no longer requires defensive explanation to be trusted operationally

**Rollback tag:** `v0-maturity-06`

---

## 8. Merge discipline

During the maturity pass:

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

---

## 9. Minimum completion gate before any v2 work

No v2 planning track should begin until all of the following are true:

- [ ] release semantics are locked by tests
- [ ] CI required checks are active and enforced
- [ ] dependency truth is singular and documented
- [ ] clean install works for the core path
- [ ] the core runtime no longer depends on `sys.path` hacks
- [ ] normative vs diagnostic surfaces are clearly separated
- [ ] external evidence semantics are clear in both tests and docs
- [ ] baseline snapshots are stable and explainable
- [ ] the repository passes the maturity audit

This is the actual entry gate to later versioned work.

---

## 10. After the maturity pass

Only after this document is fully completed should the repository move on to:

- public issue creation
- v2 planning
- capability expansion
- new integration work
- broader governance or roadmap work

The sequence is deliberate:

**first maturity, then roadmap**

---

## 11. Definition of success

The v0 maturity pass is successful when the repository becomes:

- operationally predictable
- semantically locked
- CI-enforced
- dependency-clean
- structurally maintainable
- documentation-clear
- trustworthy as a base for future evolution

The goal is not to make v0 larger.  
The goal is to make v0 solid.

---
