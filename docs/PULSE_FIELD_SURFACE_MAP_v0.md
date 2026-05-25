# PULSE Field Surface Map v0

## Purpose

PULSE is an artifact-bound release-authority system for AI release decisions.

Its core mechanism is PULSEmech: recorded release evidence, machine-readable release state, declared gate policy, materialized required gates, and strict fail-closed CI enforcement produce an allow/block release decision before deployment.

The surfaces around this mechanism are field surfaces. They preserve, inspect, extend, validate, or contextualize the release-authority core.

This document defines the mechanical role of each PULSE surface so the system remains readable at full scale without flattening its release-authority structure.

## Core principle

PULSE is being made mechanically legible at its full scale.

The goal is not to reduce PULSE to a smaller category. The goal is to preserve the full field while making every surface mechanically accountable.

A PULSE surface is valid when its role, authority status, artifact relation, and promotion boundary are explicit.

## PULSEmech release-authority path

The normative PULSEmech decision path is:

recorded release evidence
→ `status.json`
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI checking
→ CI allow/block release decision

This path is the release-authority core.

A release decision is authorized only through this path, under the declared policy and the materialized required gate set for the selected lane.

## Authority rule

Only the declared release-authority path can authorize a release.

Diagnostic, audit, preservation, publication, HPC, and shadow surfaces may inspect, preserve, stress-test, or contextualize the decision path.

A surface becomes release-authoritative only when declared policy explicitly promotes its evidence or gate into the required decision path.

## Field-surface map

| Surface                        | Mechanical role                                  | Authority status                         | Promotion boundary                                                        |
| ------------------------------ | ------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------- |
| recorded release evidence      | Evidence material available before release       | Normative input                          | Already part of the release-authority path                                |
| `status.json`                  | Machine-readable release-state artifact          | Normative source                         | Already part of the release-authority path                                |
| declared gate policy           | Defines the required gates for the selected lane | Normative input                          | Already part of the release-authority path                                |
| materialized required gate set | Concrete gate set enforced by CI                 | Normative input                          | Already part of the release-authority path                                |
| `check_gates.py`               | Strict true-only gate evaluator                  | Normative enforcement                    | Already part of the release-authority path                                |
| CI allow/block result          | Final release permission result                  | Normative decision output                | Already part of the release-authority path                                |
| Quality Ledger                 | Human-readable rendering of release state        | Audit / reader surface                   | Must remain parity-bound to source artifacts                              |
| release authority manifest     | Reconstructs the decision trace                  | Audit / preservation surface             | May support reconstruction, not independent authorization                 |
| audit bundle                   | Preserves evidence and decision artifacts        | Preservation / review surface            | May support replay and review, not independent authorization              |
| external detector summaries    | External evidence inputs                         | Conditional evidence surface             | Becomes blocking only when declared policy requires it                    |
| refusal-delta evidence         | Stability signal across refusal behavior         | Conditional evidence / stability surface | Becomes blocking only when declared policy requires it                    |
| JUnit / SARIF exports          | CI and security-tooling representation           | Integration surface                      | Mirrors decision evidence; does not replace the decision path             |
| badges                         | Compact public state indicators                  | Publication surface                      | Must reflect source artifacts; cannot override them                       |
| GitHub Pages                   | Public rendering surface                         | Publication / reader surface             | Must remain derived from recorded artifacts                               |
| Zenodo / DOI records           | Preservation and citation surface                | Publication / preservation surface       | Preserves releases; does not decide releases                              |
| Kaggle artifacts / notebooks   | Reproducibility and public analysis surface      | Research / publication surface           | Supports review and reproduction; not release authority by default        |
| EPF layer                      | Diagnostic interpretation and field analysis     | Shadow / diagnostic surface              | Can inform research; becomes required only by explicit policy promotion   |
| Paradox layer                  | Diagnostic relation and anomaly interpretation   | Shadow / diagnostic surface              | Can inform research; becomes required only by explicit policy promotion   |
| topology layer                 | Structural relation and drift analysis           | Shadow / diagnostic surface              | Can inform research; becomes required only by explicit policy promotion   |
| G-field layer                  | Relational diagnostic field                      | Shadow / diagnostic surface              | Can inform research; becomes required only by explicit policy promotion   |
| HPC evidence bundle            | Large-scale validation artifact                  | Research / validation surface            | Validates decision integrity; does not replace the release-authority path |
| PULSE-COMPUTE                  | Pre-compute admission research layer             | Shadow-only research surface             | May become normative only through future declared policy                  |

## Surface classes

### 1. Normative release-authority surfaces

Normative surfaces are the surfaces that participate directly in the release decision.

They include:

* recorded release evidence
* `status.json`
* declared gate policy
* materialized required gate set
* strict fail-closed gate evaluation
* CI allow/block release result

These surfaces form the PULSEmech release-authority path.

The normative path must remain deterministic, artifact-bound, and reconstructable.

### 2. Audit and reconstruction surfaces

Audit surfaces preserve or render the decision path.

They include:

* Quality Ledger
* release authority manifest
* audit bundle
* report card surfaces
* JUnit / SARIF exports when used as representation artifacts

Their role is to make the decision inspectable, reviewable, and reconstructable.

They strengthen trust by preserving the trace from evidence to decision.

### 3. Conditional evidence surfaces

Conditional evidence surfaces can become blocking only when declared policy requires them.

They include:

* external detector summaries
* refusal-delta evidence
* release-grade external all-pass indicators
* detector materialization evidence

The rule is simple:

A conditional evidence surface participates in release authority only when policy declares it required for the selected lane.

### 4. Diagnostic and shadow surfaces

Diagnostic surfaces interpret, contextualize, or stress-test the release field.

They include:

* EPF
* Paradox
* topology
* G-field
* recognition / drift surfaces
* shadow overlays

These surfaces are part of the PULSE field.

They are valuable because they expose structure, drift, anomaly, relation, and field behavior around the release-authority path.

Their role is diagnostic unless declared policy promotes specific outputs into required release evidence.

### 5. Publication and preservation surfaces

Publication and preservation surfaces make PULSE inspectable outside the local repository context.

They include:

* GitHub Pages
* badges
* Zenodo records
* DOI-linked releases and preprints
* Kaggle datasets and notebooks
* public artifact snapshots

Their role is continuity, citation, reproducibility, and public review.

They preserve the state of the field but do not create release permission.

### 6. HPC validation surfaces

HPC validation surfaces support large-scale repeated testing of the evidence-to-decision path.

They include:

* HPC evidence bundle
* candidate release-state batches
* repeated policy/evidence combinations
* failure-mode fixtures
* reproducibility runs
* run metadata and environment profiles

HPC is used to validate release-decision integrity across many candidate evidence states.

HPC does not replace PULSEmech.

HPC stress-tests whether PULSEmech remains deterministic, reconstructable, and fail-closed when the number of candidate states, evidence combinations, and failure modes increases.

## Fellowship-stage interpretation

The fellowship-stage work is not a proposal to invent PULSE from scratch.

PULSE already has a working release-authority core.

The fellowship-stage work prepares and validates that core under larger-scale, repeated, evidence-to-decision experiments, including HPC-supported candidate-state testing.

The central fellowship-stage question is:

When is recorded AI safety, quality, detector, stability, CI, and review evidence strong enough to authorize a release under declared policy?

The HPC validation layer helps test this question across many controlled candidate states.

## Release-grade readiness relation

A release-grade PULSE run must demonstrate that the release-authority path is operating on materialized evidence rather than scaffolded or stubbed surfaces.

A release-grade reference run should preserve:

* selected release lane
* declared policy
* effective required gate set
* recorded evidence artifacts
* `status.json`
* external evidence summaries when required
* release authority manifest
* Quality Ledger rendering
* audit bundle
* CI result
* run metadata
* git SHA
* run ID
* created UTC timestamp
* artifact hashes

The release-grade reference state must be reconstructable from its archived artifacts.

## Parity rule for reader surfaces

Reader surfaces must preserve parity with their source artifacts.

If a human-readable surface renders a gate, diagnostic flag, run mode, run ID, git SHA, created timestamp, or decision state, that rendered value must match the recorded source artifact from the same run.

A reader surface may be richer than the source artifact in explanation, layout, or navigation.

A reader surface must not silently diverge from the recorded artifact it renders.

## Promotion rule

A shadow, diagnostic, audit, publication, or HPC surface may become release-authoritative only through an explicit policy promotion.

A valid promotion must define:

* the promoted evidence field
* the selected lane or policy scope
* the expected type and allowed values
* the failure behavior
* the required artifact source
* the CI enforcement point
* the reconstruction path

No implicit promotion is allowed.

## Mechanical invariants

PULSE field surfaces must preserve the following invariants:

1. Release authority is exercised before deployment.
2. Release permission is derived from recorded artifacts.
3. Required gates are declared by policy.
4. Required gates are materialized before enforcement.
5. CI enforces strict fail-closed checking.
6. Only literal true satisfies a required boolean gate.
7. Missing, false, malformed, or non-boolean gate values do not silently pass.
8. Reader surfaces must remain parity-bound to source artifacts.
9. Audit surfaces reconstruct the decision path but do not create a second decision engine.
10. Shadow surfaces may diagnose the field but do not authorize release by default.
11. HPC validation stress-tests the decision path but does not replace it.
12. Any surface promoted into authority must be promoted by declared policy.

## First implementation use

This document should be used as the reference map for the next PULSE hardening stage.

Immediate follow-up documents:

* `docs/FELLOWSHIP_HPC_VALIDATION_PLAN_v0.md`
* `docs/PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md`
* `docs/HPC_EVIDENCE_BUNDLE_v0.md`

Immediate follow-up work:

* define the first non-stubbed release-grade reference run plan
* define HPC candidate-state validation batches
* define release-grade failure-mode fixtures
* define parity checks between `status.json`, Quality Ledger, manifest, and audit bundle
* define HPC evidence bundle schema and checker

## Closing statement

PULSE is not being flattened for adoption.

PULSE is being made mechanically legible at its full scale.

The release-authority core remains deterministic, artifact-bound, policy-declared, gate-materialized, and CI-enforced.

The surrounding surfaces form the PULSE field.

The field is preserved by making every surface role explicit.
