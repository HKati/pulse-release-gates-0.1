# PULSE Hardening Boundary Map v0

## Purpose

This document defines the v0 boundary map for the current PULSE hardening
documents and security boundary layers.

It indexes the existing boundary documents and clarifies how they relate to the
PULSEmech authority path.

It does not change PULSEmech release authority.

It does not add gates.

It does not change policy.

It does not change schemas.

It does not change CI behavior.

It does not modify `check_gates.py`.

It does not create a second release-decision engine.

## Canonical authority path

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

All boundary documents listed in this map are subordinate to this path.

No boundary document may loosen, bypass, replace, reinterpret, or override the
PULSEmech authority path.

## Scope

This document is a docs-only hardening index.

It maps the current conceptual and security hardening layers.

It may be used by maintainers, reviewers, external readers, and automated review
systems to identify which document controls which boundary.

It does not assert that all listed future work is implemented.

It does not convert advisory, diagnostic, reader, audit, or external
verification surfaces into release authority.

## Boundary map

The current PULSE hardening boundary set is:

```text
PULSEmech authority path
→ relational state transition layer
→ release-grade materialized lane
→ public / private artifact boundary
→ security threat model calibration
→ verifier and package trust-boundary hardening
```

These layers have different review functions.

They must not be collapsed into one authority category.

## Boundary documents

### 1. PULSEmech authority path

Primary location:

```text
README.md
```

Supporting security calibration:

```text
SECURITY.md
```

Role:

```text
release-decision authority
```

The PULSEmech authority path defines how recorded release evidence becomes an
allow/block release decision.

It is the only release-decision authority path.

All other documents are review, eligibility, publication, hardening,
reconstruction, or security-boundary documents unless explicitly bound through
declared policy, materialized gates, and strict CI enforcement.

### 2. Relational state transition layer

Document:

```text
docs/PULSE_RELATIONAL_STATE_TRANSITION_v0.md
```

Role:

```text
release-state relation review
```

This layer defines how state, relation, evidence binding, mechanical effect, and
decision transition remain connected above the existing PULSEmech authority path.

It does not authorize release.

It does not create a second decision engine.

It reviews whether an element can participate in a release-state transition.

Core boundary:

```text
repository existence alone does not confer release authority
relation plus evidence binding determines release-state participation
```

### 3. Release-grade materialized lane

Document:

```text
docs/PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md
```

Role:

```text
release-grade lane eligibility and materialization review
```

This layer defines when a recorded run is structurally eligible to be reviewed
as a release-grade materialized lane.

It distinguishes:

```text
release-grade lane eligibility
```

from:

```text
release permission
```

Lane eligibility does not create release permission.

Release permission remains produced only by the PULSEmech authority path.

Core boundary:

```text
release-grade lane eligibility is not release authority
release permission requires strict fail-closed CI enforcement under PULSEmech
```

### 4. Public / private artifact boundary

Document:

```text
docs/PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md
```

Role:

```text
publication exposure and artifact classification review
```

This layer defines whether artifacts may be public, private, or restricted.

It separates:

```text
release-authority role
```

from:

```text
publication exposure
```

Publication does not create release authority.

A public artifact is not authoritative because it is public.

A private artifact is not non-authoritative because it is private.

Core boundary:

```text
publication exposure and release authority must not be collapsed
```

### 5. Security threat model calibration

Document:

```text
SECURITY.md
```

Role:

```text
security risk classification and review calibration
```

The security threat model defines the repository as a CI/local tooling and
artifact verification system for an artifact-bound release-authority path.

It calibrates risk around PULSE-relevant attack classes:

- shell and workflow injection;
- path traversal;
- symlink escape;
- static-site XSS in rendered artifacts;
- supply-chain compromise;
- semantic bypass of release-state or verifier checks;
- verifier trust-boundary failures;
- forged verified packets.

Classic web-application findings are usually secondary unless they affect the
artifact-to-release-decision path or public reader-surface integrity.

Core boundary:

```text
severity follows impact on artifact integrity, verifier trust boundaries,
release-state verification, packet verification status, and CI allow/block
outcome
```

### 6. Verifier and package trust-boundary hardening

Primary implementation areas:

```text
scripts/build_external_verification_packet_v0.py
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
PULSE_safe_pack_v0/tools/verify_pulse_ref_ra1_package.py
tests/test_build_external_verification_packet_v0.py
tests/test_artifact_provenance_binding_v0.py
```

Role:

```text
tooling security boundary
```

This hardening area ensures that external verification, binding verification,
and reference package verification do not treat reviewed roots as trusted
executable-code sources or unrestricted filesystem roots.

Current boundary principles:

```text
reviewed root = artifact source / package source
trusted checkout = verifier code source
paths must resolve inside reviewed root or package root
traversal and symlink escape must fail closed
forged verified packets must not be accepted
```

Tooling hardening supports artifact integrity and external review.

It does not replace PULSEmech release authority.

## Layer relationship table

| Layer | Primary document | Function | Authority role |
|---|---|---|---|
| PULSEmech authority path | `README.md` | Produces allow/block release decision | Authority |
| Relational state transition | `docs/PULSE_RELATIONAL_STATE_TRANSITION_v0.md` | Reviews connected release-state transitions | Review layer |
| Release-grade materialized lane | `docs/PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md` | Defines lane eligibility and materialization requirements | Eligibility layer |
| Public / private artifact boundary | `docs/PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md` | Classifies publication exposure | Publication boundary |
| Security threat model | `SECURITY.md` | Calibrates security risk and review focus | Security calibration |
| Verifier/package hardening | implementation + tests | Enforces verifier and path trust boundaries | Tooling boundary |

Only the PULSEmech authority path produces release permission.

## Non-overlap rules

### 1. Review is not authority

A review layer may identify relations, eligibility, boundaries, or risks.

A review layer does not authorize release unless its output is explicitly bound
through declared policy, materialized gates, and strict CI enforcement.

### 2. Eligibility is not permission

Release-grade lane eligibility means that a recorded run is structurally
eligible for release-grade review.

It does not mean that the release is permitted.

### 3. Publication is not authority

Public exposure does not create authority.

Private retention does not remove release relevance.

Reader surfaces do not authorize release.

### 4. Security calibration is not policy wiring

The threat model calibrates risk.

It does not add gates, change policy, or alter CI behavior.

### 5. Verifier output is not release permission by itself

External verification packets, RA1 reports, artifact binding verification, and
package verifier reports may support review.

They do not create release permission unless their results are explicitly bound
into the PULSEmech authority path.

### 6. Tooling trust boundaries must remain explicit

Reviewed repositories, packages, and external artifacts are untrusted inputs.

Trusted executable verifier code must not be selected from reviewed roots.

File paths may be relative or absolute only if they resolve inside the
applicable reviewed root or package root.

## Common misclassification risks

The boundary map is intended to prevent the following misclassifications.

### Reader surface treated as authority

Risk:

```text
Quality Ledger, Pages output, badge, dashboard, report, or summary is treated as
release permission.
```

Boundary:

```text
reader surfaces are non-authoritative unless bound through declared policy,
materialized gates, and strict CI enforcement
```

### Public artifact treated as release permission

Risk:

```text
a public artifact is assumed to authorize release because it is visible
```

Boundary:

```text
publication exposure does not create release authority
```

### Release-grade lane treated as release decision

Risk:

```text
lane eligibility is interpreted as allow
```

Boundary:

```text
lane eligibility is not release permission
```

### Diagnostic or scaffold state treated as release-grade

Risk:

```text
demo, core, smoke, scaffold, diagnostic, shadow, or advisory-only state is
reviewed as release-grade materialized lane
```

Boundary:

```text
diagnostic/scaffold/stub states are not release-grade materialized lanes
```

### External verifier output treated as authority

Risk:

```text
external verification packet or RA1 report is treated as release decision
```

Boundary:

```text
external verifier output supports reconstruction and review only
```

### Reviewed root treated as trusted code source

Risk:

```text
reviewed repository or package supplies executable verifier code
```

Boundary:

```text
reviewed roots are artifact/package sources, not trusted executable-code sources
```

## Review order

When reviewing a PULSE hardening or release-state change, use the following
order.

### 1. Identify authority impact

Determine whether the change affects the PULSEmech authority path:

```text
recorded release evidence
status.json
declared policy
materialized required gate set
strict fail-closed CI enforcement
allow/block decision
```

If yes, treat as release-authority relevant.

### 2. Identify boundary layer

Determine which boundary layer the change belongs to:

```text
authority path
relational state transition
release-grade lane eligibility
public/private artifact exposure
security threat model
verifier/package trust boundary
reader surface
audit/reconstruction surface
```

### 3. Verify non-overlap

Confirm that the change does not collapse review, eligibility, publication,
security calibration, or verifier output into release authority.

### 4. Verify fail-closed behavior

If the change affects a boundary or verifier, confirm that unclear,
unbound, stale, mismatched, malformed, missing, or outside-root states fail
closed.

### 5. Verify preserved paths

Confirm that unrelated paths were not modified.

For docs-only boundary changes, expected preserved paths include:

```text
README.md
.github/workflows/*
ci/*
tests/*
schemas/*
policy/*
renderer/*
release tags
DOI / Zenodo path
```

For code security changes, the expected changed files must match the stated
security boundary being fixed.

### 6. Verify review language

Confirm that the change uses mechanical boundary language and does not rely on
general narrative, governance framing, dashboard framing, or prose-only claims.

## Boundary invariants

The following invariants apply across the hardening boundary set.

### 1. PULSEmech remains the authority path

No hardening document may create a second release-decision path.

### 2. Recorded evidence precedes release permission

Release permission cannot be inferred from prose, dashboard state, reader
surface visibility, or publication status.

### 3. Declared policy and materialized gates are required

A gate or artifact becomes release-relevant only when it is connected to the
declared policy and materialized required gate set.

### 4. Strict CI enforcement is required

Release permission cannot be created without strict fail-closed CI enforcement.

### 5. Unclear classification fails closed

Unclear release-state relation, lane eligibility, publication classification,
or verifier boundary remains non-authorizing.

### 6. External review is not authority by default

External verification supports reconstruction.

It does not replace the PULSEmech authority path.

### 7. Public status is not release permission by presence

A public `status.json` or status-derived artifact must be tied to the same
release-state relation before it can support release review.

### 8. Reviewed roots are untrusted boundaries

Reviewed repositories, packages, artifact bundles, and external verification
inputs must be treated as untrusted unless explicitly classified otherwise.

## Future map additions

Future boundary documents may be added to this map when they define stable review
or hardening roles.

Possible future entries include:

- external evidence envelope boundary;
- attestation / provenance boundary;
- release-grade detector materialization boundary;
- dependency single-truth boundary;
- packaging / `src/` layout boundary;
- blocking scan release-lane boundary;
- multi-reviewer continuity boundary;
- RA1 external verifier productization boundary;
- public status redaction boundary.

Future entries must preserve the PULSEmech authority path.

## Non-goals

This document does not define a new policy.

It does not select required gates.

It does not define a production release lane.

It does not change status schemas.

It does not change workflow behavior.

It does not change renderer behavior.

It does not modify verifier code.

It does not change release tags.

It does not change DOI or Zenodo behavior.

It does not claim that all future hardening work is complete.

## Summary

The PULSE hardening boundary map identifies the current review and hardening
layers around the PULSEmech authority path.

The authority path remains singular:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

The surrounding layers define relation review, lane eligibility, publication
classification, security risk calibration, and verifier/package trust-boundary
hardening.

Those layers support the authority path.

They do not replace it.
