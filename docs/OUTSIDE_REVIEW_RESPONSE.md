# Outside review response and mitigation plan (DeepSearch critique)

This document tracks external “outside review” concerns (DeepSearch critique) and how PULSE addresses them.
It is intentionally practical: it links to concrete repo artifacts and defines measurable next steps.

## Why this exists (outside view)
PULSE aims to make release gating more deterministic and auditable for AI/LLM systems.
That said, the system’s value depends on operational reality:
- CI stability and reproducibility
- documentation clarity (especially for non-authors)
- determinism boundaries (model/runtime vs measurement pipeline)
- scalability costs
- extensibility without “forking the world”

This file is the canonical place to track those concerns and our mitigation work.

---

## 1) Usability and CI integration risks

### Concern
Integrating a new tool into CI can block deploys due to environment issues, dependency conflicts, or flaky behavior.

### What we have already done
- Reviewer-friendly paradox projection output (`paradox_summary_v0.md`) produced and uploaded as artifacts.
- Regression fixtures for “empty edges” and “no atoms” to ensure fail-closed logic handles null/empty situations.
- Repo-wide hygiene guardrails:
  - block case-insensitive path collisions (file/file + file/dir)
  - block ignored workflows under `github/workflows/`
  - block nested fixtures under `tests/fixtures/**/tests/fixtures/**`
- CI supply-chain hardening:
  - minimal `GITHUB_TOKEN` permissions where possible
  - pin critical GitHub Actions to commit SHAs (deterministic CI)

### Remaining work (definition of done)
- [ ] Pin remaining high-impact workflows (e.g. `pulse_ci.yml`, `pulse_core_ci.yml`, Pages publishing, secret scans).
- [ ] Add timeouts + concurrency cancellation for long-running workflows to reduce CI stalls.
- [ ] Document “adoption modes” (shadow → advisory → gating) to avoid early hard-blocking.

---

## 2) Documentation and learning curve

### Concern
Core concepts (EPF, paradox field, RDSI, gating policy) can feel theoretical, and discoverability matters.
Broken or missing references reduce trust.

### What we have already done
- Improved documentation entrypoints and indexing (`docs/INDEX.md` + README doc map updates).
- Consolidated external detector docs with canonical policy vs summaries guidance and fixed navigation between safe-pack and repo-level docs.

### Remaining work (definition of done)
- [ ] Add a short glossary for core terms (EPF, paradox field, projection view, RDSI, gates).
- [ ] Add an FAQ focused on real integration pain points (GPU determinism, “why did this gate fail?”, adding invariants).
- [ ] Run/link-check the docs and fix any missing/404 references (e.g. “Competitor Radar” style links).

---

## 3) Scalability and performance

### Concern
Large prompt sets or multiple models can make runs slow and expensive; caching/parallelism and runtime budgets should be explicit.

### Current position
PULSE favors determinism and auditability. Performance improvements should not undermine reproducibility.

### Remaining work (definition of done)
- [ ] Define a runtime budget section (what is expected in CI vs nightly runs).
- [ ] Add optional caching (pip cache, artifact reuse where safe).
- [ ] Define/implement optional parallel execution (opt-in; deterministic ordering in outputs).
- [ ] Provide a lightweight benchmark note (what scales with #prompts, #detectors, #models).

---

## 4) Determinism boundaries and environment control

### Concern
PULSE can be deterministic as a *measurement pipeline*, but model runtimes may not be (GPU nondeterminism, cloud APIs changing behavior).

### Current position (principle)
- Determinism is guaranteed for PULSE’s *data transformations and contracts* under pinned tooling and stable inputs.
- Model/runtime determinism depends on the deployment mode:
  - local model + pinned deps: highest determinism
  - hosted API: lower determinism (responses can drift)

### Remaining work (definition of done)
- [ ] Add a “Determinism policy” doc: CPU/GPU, seeds, pinned deps, and expected variance.
- [ ] Add guidance (or tooling) for record/replay runs:
  - gating on replay (deterministic)
  - shadow/live runs for drift detection

---

## 5) Coverage and extensibility (invariants, detectors, custom checks)

### Concern
If an important invariant isn’t defined, it isn’t gated. Extending PULSE should be possible without a deep fork.

### Current position
We treat contracts and projections as the stable interface; extensions should preserve this.

### Remaining work (definition of done)
- [ ] Provide a documented extension pattern for custom checks (e.g. `custom_checks/` convention + contract outputs).
- [ ] Add a template for “new invariant” work:
  - inputs → contract → acceptance fixture → docs entry

---

## 6) Community and maintenance signals

### Concern
A new project needs clear maintenance signals: contribution path, support model, roadmap cadence.

### Remaining work (definition of done)
- [ ] Add CONTRIBUTING + issue templates
- [ ] Define support expectations (what is “best effort” vs “guaranteed”)
- [ ] Provide a lightweight roadmap snapshot

---

## Next step (immediate)
Work through the remaining items in priority order, one PR/file at a time, keeping each change:
- testable
- reviewable
- minimal in scope

The goal is not “classic polish”; the goal is to make PULSE dependable under real CI constraints.
