# PULSE Release-Grade Materialized Lane v0

## Purpose

This document defines the v0 review requirements for a release-grade
materialized lane in PULSE.

It does not change PULSEmech release authority.

It does not add gates.

It does not change policy.

It does not change schemas.

It does not change CI behavior.

It does not modify `check_gates.py`.

It defines the conditions under which a recorded run may be reviewed as a
release-grade materialized lane above the existing PULSEmech authority path.

## Authority boundary

The PULSEmech authority path remains unchanged:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

The release-grade materialized lane does not create a second release-decision
engine.

It defines lane eligibility and materialization requirements.

Release permission remains produced only by the existing PULSEmech authority
path.

## Scope

This v0 document is definitional.

It may be used for review, hardening planning, and future implementation
alignment.

It does not assert that any current public run satisfies release-grade
materialized lane requirements.

It does not convert reader surfaces, dashboards, reports, manifests, audit
bundles, Pages outputs, or external verifier reports into release authority.

Those surfaces remain audit or reconstruction surfaces unless they are explicitly
bound through declared policy, materialized gates, and strict CI enforcement into
the PULSEmech authority path.

## Core distinction

A release-grade lane is not the same as a release-grade decision.

A release-grade lane is the recorded execution context in which all required
release evidence, status state, declared policy, materialized gate set, and CI
enforcement are concrete enough to support a release decision.

A release-grade decision is the final allow/block outcome produced by strict
fail-closed CI enforcement under the PULSEmech authority path.

The lane may be eligible for release-grade review only when materialization
requirements are satisfied.

The release decision may become permitted only when the PULSEmech authority path
is satisfied.

## Definitions

### Lane

A lane is a declared execution context for evaluating release-state artifacts.

Examples of lane-like contexts may include demo, core, diagnostic, shadow,
staging, or release-grade execution.

This document defines the release-grade materialized lane only.

### Release-grade lane

A release-grade lane is a pre-deployment execution context intended to evaluate
whether a candidate release may be allowed or blocked under declared release
policy.

A release-grade lane must not rely on scaffold, placeholder, stubbed, or
advisory-only evidence.

### Materialized lane

A materialized lane is a lane whose required release-state inputs are recorded,
parseable, policy-bound, gate-materialized, and enforceable by strict CI.

Materialized does not mean that every possible diagnostic or advisory artifact
exists.

It means that every artifact or gate required for the release decision is present
or fail-closed according to the declared authority path.

### Scaffold state

A scaffold state is a recorded state that contains placeholder, stubbed,
synthetic, incomplete, or diagnostic-only release evidence.

A scaffold state may be useful for development, smoke testing, reader-surface
validation, or pipeline construction.

A scaffold state is not a release-grade materialized lane.

### Stubbed gate state

A stubbed gate state is a recorded state where gate values are supplied as
placeholder or all-true smoke values rather than derived from materialized
release evidence.

A stubbed gate state is not a release-grade materialized lane.

### Detector materialization

Detector materialization means that detector or external evidence required by
release policy is present, parseable, subject-bound, and folded into status or
gate state through the declared release evidence path.

Detector materialization does not occur through filename presence alone.

Detector materialization must be derived from recorded evidence and declared
rules.

### Lane eligibility

Lane eligibility means that a recorded run can be reviewed as a release-grade
materialized lane.

Lane eligibility does not create release permission.

Lane eligibility only means that the recorded run is structurally eligible to
enter the existing PULSEmech release-decision path.

## Release-grade materialized lane model

The v0 model is:

```text
declared release-grade run context
→ recorded release evidence
→ non-scaffold status state
→ declared policy
→ materialized required/release_required gate set
→ materialized evidence-derived gate values
→ strict fail-closed CI enforcement
→ allow/block release decision
```

This model is a review model.

It does not replace PULSEmech.

## Minimum lane eligibility requirements

A recorded run is eligible for release-grade materialized lane review only when
all of the following requirements are satisfied.

### 1. Declared release-grade context

The run must be explicitly identifiable as a release-grade or production release
context.

The context must be recorded in machine-readable form.

A run that is demo, core, smoke, scaffold, diagnostic, shadow, or advisory-only
is not a release-grade materialized lane.

### 2. Parseable status artifact

The run must include a parseable `status.json` artifact.

The artifact must satisfy the applicable status schema.

A missing, malformed, non-object, or schema-invalid `status.json` fails closed.

### 3. Non-scaffold status state

The recorded status state must not contain scaffold or stub indicators that are
active for the release lane.

The following indicators are incompatible with release-grade materialized lane
eligibility when active:

```text
scaffold=true
gates_stubbed=true
stub_profile present for an all-true or smoke profile
detectors_materialized_ok=false when detector evidence is release-required
```

Equivalent future scaffold or stub indicators must be treated the same way.

### 4. Declared gate policy

The run must have a declared gate policy.

The declared policy must identify the required gate sets used for the lane.

The required gate set must not be empty.

A missing policy, malformed policy, empty required gate set, or unresolved
policy source fails closed.

### 5. Workflow-effective materialized required gate set

The workflow-effective required gate set must be materialized from declared
policy and lane context.

For release-grade runs, the materialized gate set must include the gates required
by the release lane.

The gate set must be recorded or reconstructable from recorded inputs.

A gate that is only described in prose is not materialized.

### 6. Evidence-derived gate values

Required gate values must be derived from recorded release evidence.

A required gate value must be a literal boolean value in the recorded status
state.

Only literal `true` can satisfy a required gate.

Missing gates, non-boolean gates, null values, strings, numbers, objects, arrays,
or false values do not satisfy required gates.

### 7. Detector and external evidence materialization

If detector or external evidence is required by release policy, the evidence
must be materialized before it can support a release-grade lane.

Materialization requires at least:

- recorded evidence artifact;
- parseable structure;
- subject identity or artifact binding;
- freshness or run identity sufficient for the release context;
- deterministic fold-in rule or declared status/gate mapping;
- fail-closed handling for missing, malformed, stale, or mismatched evidence.

Filename presence alone is not detector materialization.

Advisory detector output alone is not release-grade evidence.

### 8. Artifact binding and provenance review

Release-grade materialized lane review should include artifact binding or
provenance review when such artifacts are present or required by policy.

Binding or provenance review must not replace the PULSEmech authority path.

Binding or provenance artifacts may support the review of release-state
consistency, artifact identity, digest coverage, and reconstruction.

If binding or provenance review is required by policy, failure to verify must
fail closed.

If binding or provenance review is advisory only, it must not create release
permission.

### 9. Reader-surface non-authority

Reader surfaces may display release-state information.

Reader surfaces do not authorize release.

Reader surfaces include, but are not limited to:

- Quality Ledger outputs;
- dashboards;
- badges;
- SARIF/JUnit outputs;
- Markdown summaries;
- rendered HTML reports;
- Pages outputs;
- audit bundles;
- RA1 reports;
- external verification packets.

A reader surface can participate in release review only when it is explicitly
bound into the recorded release-state relation and its mechanical effect is
defined by declared policy, materialized gates, and strict CI enforcement.

### 10. Strict fail-closed CI enforcement

A release-grade materialized lane must end in strict fail-closed CI enforcement.

The CI path must invoke the required gate checker.

The CI path must not ignore non-zero gate-check results.

The CI path must not treat missing gates, malformed status, empty required sets,
stubbed gates, or advisory-only evidence as release permission.

The final release decision must remain allow/block.

## Fail-closed conditions

A recorded run is not eligible for release-grade materialized lane status if any
of the following conditions hold:

```text
status.json is missing
status.json is malformed
status.json is schema-invalid
run context is demo/core/smoke/scaffold/shadow/advisory-only
scaffold=true
gates_stubbed=true
stub or all-true smoke profile is active
declared policy is missing or malformed
workflow-effective required gate set is missing
workflow-effective required gate set is empty
required gate is missing
required gate is not literal boolean true
required detector evidence is missing
required detector evidence is malformed
required detector evidence is stale or subject-mismatched
required external evidence is advisory-only
binding/provenance required by policy fails verification
CI does not run strict gate enforcement
CI ignores strict gate enforcement failure
reader surface is treated as authority without policy/gate/CI binding
```

Any unclear transition remains fail-closed.

## Non-goals

This document does not define a production release policy.

It does not select required gates.

It does not make detector evidence normative.

It does not change the status schema.

It does not change CI workflows.

It does not change `check_gates.py`.

It does not promote external verifier reports to release authority.

It does not assert that a current public PULSE run is release-grade
materialized.

## Review sequence v0

A release-grade materialized lane review follows this sequence.

### 1. Identify the run context

Confirm whether the run is declared as release-grade.

If the run context is demo, core, smoke, scaffold, shadow, or advisory-only, the
review stops.

Result:

```text
not release-grade materialized lane
```

### 2. Validate status

Confirm that `status.json` exists, parses as a JSON object, and satisfies the
applicable schema.

If not, the review fails closed.

### 3. Check scaffold and stub indicators

Confirm that scaffold and stub indicators are not active for the release-grade
lane.

If scaffold or stub indicators are active, the review fails closed.

### 4. Resolve declared policy

Confirm that declared policy exists and identifies the required gate set for the
lane.

If no required gate set can be resolved, the review fails closed.

### 5. Materialize required gates

Confirm that the workflow-effective required gate set is materialized.

If the set is missing, empty, or only described in prose, the review fails
closed.

### 6. Verify gate values

Confirm that every required gate is present in the recorded status state and is
literal boolean `true`.

If any required gate is missing or not literal boolean `true`, the review fails
closed.

### 7. Review detector and external evidence

If detector or external evidence is required by policy, confirm that the
evidence is materialized and bound to the release context.

If it is missing, malformed, stale, mismatched, or advisory-only, the review
fails closed.

### 8. Review binding and provenance

If binding or provenance artifacts are present or required, confirm that they do
not contradict the release-state relation.

If binding or provenance verification is required by policy and fails, the
review fails closed.

### 9. Confirm reader-surface boundary

Confirm that reader surfaces are not treated as release authority.

Reader surfaces must not override status, policy, gates, or strict CI.

### 10. Confirm strict CI outcome

Confirm that strict CI enforcement produced the allow/block decision.

Only this outcome can produce release permission.

## Relationship to PULSEmech

The release-grade materialized lane is an eligibility and materialization layer.

PULSEmech remains the authority layer.

The lane determines whether the recorded run is structurally eligible to enter
release-grade review.

PULSEmech determines whether the release is allowed or blocked.

The two must not be collapsed.

## Future implementation notes

Future PRs may implement machine-readable checks for this lane only if they
preserve the PULSEmech authority boundary.

A future implementation may include:

- explicit lane classification artifact;
- scaffold/stub fail-closed checker;
- release-grade detector materialization checker;
- public/private artifact boundary classifier;
- materialized evidence inventory;
- release-grade lane summary artifact;
- external evidence freshness and subject-binding checks.

Any executable implementation must include regression tests and must preserve
strict fail-closed behavior.

## Summary

A release-grade materialized lane is a recorded release execution context whose
required evidence, status state, declared policy, required gate set, gate values,
and strict CI enforcement are concrete enough to support a PULSEmech
allow/block release decision.

It is not a new authority path.

It is not a reader surface.

It is not a dashboard state.

It is not a prose claim.

It is a materialized eligibility layer above the existing PULSEmech
release-authority path.
