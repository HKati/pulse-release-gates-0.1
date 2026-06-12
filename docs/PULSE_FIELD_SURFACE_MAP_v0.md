# PULSE Field Surface Map v0

## Purpose

PULSE is an artifact-bound release-authority system for AI release decisions.

Its core mechanism is PULSEmech: recorded release evidence, machine-readable release state, declared gate policy, materialized required gates, and strict fail-closed CI enforcement produce an allow/block release decision before deployment.

The surfaces around this mechanism are field surfaces.

They preserve, inspect, extend, validate, render, or contextualize the release-authority core.

This document defines the mechanical role of each PULSE surface so the system remains readable at full scale while preserving its release-authority structure.

## Core principle

PULSE is made mechanically legible at full scale.

The goal is not to reduce PULSE to a smaller category.

The goal is to preserve the full PULSE field while making every surface mechanically accountable.

A PULSE surface is mechanically legible when its role, authority status, artifact relation, source relation, and promotion boundary are explicit.

A PULSE surface may act as:

- normative release authority
- normative input
- normative enforcement
- audit / reconstruction surface
- preservation surface
- conditional evidence surface
- publication surface
- diagnostic / shadow surface
- research / validation surface

The field is not flattened.

The field is made explicit.

## PULSEmech release-authority path

The normative PULSEmech decision path is:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ CI allow/block release decision

This path is the release-authority core.

A release decision is authorized only through this path, under the declared policy and the materialized required gate set for the selected lane.

## Authority rule

Release authority is exercised only through the declared PULSEmech path.

Diagnostic, audit, preservation, publication, HPC, and shadow surfaces may inspect, preserve, stress-test, contextualize, render, or compare the decision path.

Carrier roles remain explicit

Reader, diagnostic, publication, preservation, HPC, and shadow carriers are non-authorizing carriers unless a specific artifact field is folded into recorded release evidence and enforced as a required gate under declared policy.

The PULSEmech path carries release authority.

No whole surface is implicitly promoted into the release-authority path.

## Recorded artifact and public reader surface

PULSE distinguishes recorded release artifacts from public reader surfaces.

A recorded `status.json` artifact can carry release-authority input when it belongs to the declared release run and is tied to the relevant run identity.

A public `status.json` URL is a reader / access carrier for release-state data.

The Quality Ledger, Pages, badges, public URLs, and rendered views present recorded state through public reader or publication carriers.

Publication and reader carriers are derived carriers.

Authority review is tied to the recorded artifact source for a declared run and is compared through the same run identity:

- `run_id`
- `git_sha`
- `created_utc`
- artifact source
- artifact hash when available

The public reader surface presents recorded state.

The PULSEmech path carries release authority.

## Field-surface map

| Surface | Mechanical role | Authority status | Promotion boundary |
|---|---|---|---|
| recorded release evidence | Evidence material available before release | Normative input | Already part of the release-authority path |
| recorded `status.json` artifact | Machine-readable release-state artifact for a declared run | Normative source | Normative only as the recorded artifact bound to the selected run |
| public `status.json` URL | Public reader / access carrier for release-state data | Reader / access carrier | Authority review uses the recorded artifact bound to run identity | 
| declared gate policy | Defines the required gates for the selected lane | Normative input | Already part of the release-authority path |
| materialized required gate set | Concrete gate set enforced by CI | Normative input | Already part of the release-authority path |
| `check_gates.py` | Strict true-only gate evaluator | Normative enforcement | Already part of the release-authority path |
| CI allow/block result | Final release permission result | Normative decision output | Already part of the release-authority path |
| Quality Ledger | Public reader carrier for recorded release state, reader-visible evidence state, traceability fields, and gate outcomes | Reader carrier | Non-authorizing carrier; parity-bound to recorded source artifacts |
| release authority manifest | Reconstructs the decision trace | Audit / preservation surface | May support reconstruction; does not authorize independently |
| audit bundle | Preserves evidence and decision artifacts | Preservation / review surface | May support replay and review; does not authorize independently |
| external detector summaries | External evidence inputs | Conditional evidence surface | Becomes blocking only when declared policy requires a specific field or gate |
| refusal-delta evidence | Stability signal across refusal behavior | Conditional evidence / stability surface | Becomes blocking only when declared policy requires a specific field or gate |
| JUnit / SARIF exports | CI and security-tooling representation | Integration surface | Mirrors decision evidence; does not replace the decision path |
| badges | Compact public state indicators derived from recorded artifacts | Publication carrier | Derived carrier only |
| GitHub Pages | Public reader / publication carrier for rendered artifacts | Reader / publication carrier | Derived carrier only |
| GitHub Pages | Public rendering surface | Publication / reader surface | Must remain derived from recorded artifacts |
| Zenodo / DOI records | Preservation and citation surface | Publication / preservation surface | Preserves releases; does not decide releases |
| Kaggle artifacts / notebooks | Reproducibility and public analysis surface | Research / publication surface | Supports review and reproduction; not release authority by default |
| EPF layer | Diagnostic interpretation and field analysis | Shadow / diagnostic surface | Can inform research; a specific output becomes required only by explicit policy promotion |
| Paradox layer | Diagnostic relation and anomaly interpretation | Shadow / diagnostic surface | Can inform research; a specific output becomes required only by explicit policy promotion |
| topology layer | Structural relation and drift analysis | Shadow / diagnostic surface | Can inform research; a specific output becomes required only by explicit policy promotion |
| G-field layer | Relational diagnostic field | Shadow / diagnostic surface | Can inform research; a specific output becomes required only by explicit policy promotion |
| recognition / drift surfaces | Diagnostic state-change and relation tracking | Shadow / diagnostic surface | Can inform research; a specific output becomes required only by explicit policy promotion |
| HPC evidence bundle | Large-scale validation artifact for candidate-state testing | Research / validation surface | Supports decision-integrity validation; does not authorize release |
| PULSE-COMPUTE | Pre-compute admission research layer | Shadow / research surface | Separate future policy question; not release authority by default |

## Surface classes

### 1. Normative release-authority surfaces

Normative surfaces are the surfaces that participate directly in the release decision.

They include:

- recorded release evidence
- recorded `status.json` artifact
- declared gate policy
- materialized required gate set
- strict fail-closed gate evaluation
- CI allow/block release result

These surfaces form the PULSEmech release-authority path.

The normative path must remain deterministic, artifact-bound, policy-declared, gate-materialized, CI-enforced, and reconstructable.

### 2. Audit and reconstruction surfaces

Audit surfaces preserve or render the decision path.

They include:

- Quality Ledger
- release authority manifest
- audit bundle
- report card surfaces
- JUnit / SARIF exports when used as representation artifacts

Their role is to make the decision inspectable, reviewable, and reconstructable.

They strengthen trust by preserving the trace from evidence to decision.

They do not create a second decision engine.

### 3. Conditional evidence surfaces

Conditional evidence surfaces can become blocking only when declared policy requires them.

They include:

- external detector summaries
- refusal-delta evidence
- release-grade external all-pass indicators
- detector materialization evidence

The rule is:

A conditional evidence surface participates in release authority only when a specific evidence field or gate is declared required for the selected lane.

No conditional evidence surface becomes release-authoritative as a whole surface.

### 4. Diagnostic and shadow surfaces

Diagnostic surfaces interpret, contextualize, or stress-test the release field.

They include:

- EPF
- Paradox
- topology
- G-field
- recognition / drift surfaces
- shadow overlays

These surfaces are part of the PULSE field.

They are valuable because they expose structure, drift, anomaly, relation, and field behavior around the release-authority path.

Their role is diagnostic unless declared policy promotes a specific output into required release evidence.

The diagnostic field is preserved.

The authority boundary remains explicit.

### 5. Publication and preservation surfaces

Publication and preservation surfaces make PULSE inspectable outside the local repository context.

They include:

- GitHub Pages
- badges
- Zenodo records
- DOI-linked releases and preprints
- Kaggle datasets and notebooks
- public artifact snapshots

Their role is continuity, citation, reproducibility, and public review.

They preserve the state of the field but do not create release permission.

A publication surface must not be treated as release authority merely because it displays release-state information.

### 6. HPC validation surfaces

HPC validation surfaces support large-scale repeated testing of the evidence-to-decision path.

They include:

- HPC evidence bundle
- candidate release-state batches
- repeated policy/evidence combinations
- failure-mode fixtures
- reproducibility runs
- run metadata and environment profiles

HPC is used to validate release-decision integrity across many candidate evidence states.

HPC does not replace PULSEmech.

HPC stress-tests whether PULSEmech remains deterministic, reconstructable, and fail-closed when the number of candidate states, evidence combinations, and failure modes increases.

HPC validation artifacts are research and validation artifacts unless a future declared policy explicitly promotes a specific evidence field or gate.

## Fellowship-stage interpretation

The fellowship-stage work is not a proposal to invent PULSE from scratch.

PULSE already has a working release-authority core.

The fellowship-stage work prepares and validates that core under larger-scale, repeated, evidence-to-decision experiments, including HPC-supported candidate-state testing.

The central fellowship-stage question is:

When is recorded AI safety, quality, detector, stability, CI, and review evidence strong enough to authorize a release under declared policy?

The HPC validation layer helps test this question across many controlled candidate states.

HPC may diagnostically test candidate decision-field behavior.

PULSEmech remains the only release-authority mechanism.

## Release-grade readiness relation

A release-grade PULSE run must demonstrate that the release-authority path is operating on materialized evidence rather than scaffolded or stubbed surfaces.

A release-grade reference run should preserve:

- selected release lane
- declared policy
- effective required gate set
- recorded evidence artifacts
- recorded `status.json` artifact
- external evidence summaries when required
- release authority manifest
- Quality Ledger rendering
- audit bundle
- CI result
- run metadata
- git SHA
- run ID
- created UTC timestamp
- artifact source
- artifact hashes

The release-grade reference state must be reconstructable from its archived artifacts.

A release-grade reference state must not rely on a live mutable URL as a substitute for recorded evidence.

## Parity rule for reader surfaces

Reader surfaces must preserve parity with their recorded source artifacts.

If a human-readable surface renders a gate, diagnostic flag, run mode, run ID, git SHA, created timestamp, artifact source, or decision state, that rendered value must match the recorded source artifact from the same run.

Parity checks must bind comparisons to the same run identity:

- `run_id`
- `git_sha`
- `created_utc`
- artifact source
- artifact hash when available

A reader surface may be richer than the source artifact in explanation, layout, navigation, or summary.

A reader surface must not silently diverge from the recorded artifact it renders.

## Promotion rule

A shadow, diagnostic, audit, publication, HPC, or research surface does not become release-authoritative as a whole surface.

Only a specific evidence field or gate may become release-relevant, and only through explicit policy promotion.

A valid promotion must define:

- the promoted evidence field or gate
- the selected lane or policy scope
- the expected type and allowed values
- the failure behavior
- the required artifact source
- the CI enforcement point
- the reconstruction path
- the reader-surface parity requirement when rendered publicly

No implicit promotion is allowed.

No advisory, diagnostic, shadow, publication, or HPC output may silently become a required release gate.

## Mechanical invariants

PULSE field surfaces must preserve the following invariants:

1. Release authority is exercised before deployment.
2. Release permission is derived from recorded artifacts.
3. Required gates are declared by policy.
4. Required gates are materialized before enforcement.
5. CI enforces strict fail-closed checking.
6. Only literal true satisfies a required boolean gate.
7. Missing, false, malformed, or non-boolean gate values do not silently pass.
8. A recorded `status.json` artifact and a live/public `status.json` URL are not the same authority category.
9. Reader surfaces must remain parity-bound to recorded source artifacts.
10. Reader-surface parity must be bound to the same run identity.
11. Audit surfaces reconstruct the decision path but do not create a second decision engine.
12. Shadow surfaces may diagnose the field but do not authorize release by default.
13. HPC validation stress-tests the decision path but does not replace it.
14. Any promoted field or gate must be promoted by declared policy.
15. No whole non-normative surface is implicitly promoted into release authority.

## First implementation use

This document should be used as the reference map for the next PULSE hardening stage.

Immediate follow-up documents:

- `docs/FELLOWSHIP_HPC_VALIDATION_PLAN_v0.md`
- `docs/PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md`
- `docs/HPC_EVIDENCE_BUNDLE_v0.md`

Immediate follow-up work:

- define the first non-stubbed release-grade reference run plan
- define HPC candidate-state validation batches
- define release-grade failure-mode fixtures
- define parity checks between recorded `status.json`, Quality Ledger, manifest, and audit bundle
- define HPC evidence bundle schema and checker
- define recorded-artifact versus live-public-surface comparison rules
- define promotion rules for future conditional evidence fields

## Closing statement

PULSE is made mechanically legible at full scale.

The release-authority core remains deterministic, artifact-bound, policy-declared, gate-materialized, and CI-enforced.

The surrounding surfaces form the PULSE field.

The field is preserved by making every surface role explicit, every authority boundary enforceable, and every rendered state accountable to its recorded artifact source.

PULSE is not reduced to a smaller category.

PULSE is preserved as a full release-authority field instrument.
