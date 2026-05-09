# PULSE-REF RA1 Minimal Release-Reference Package Fixture

Status: fixture skeleton  
Scope: PULSE-REF RA1 externally verifiable release-reference package  
Authority: non-normative test fixture / package-layout anchor

## Purpose

This fixture directory is the target location for the first minimal PULSE-REF RA1 release-reference package.

RA1 packages bind the artifacts needed for external reconstruction of the PULSE release-authority path:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

The package preserves and verifies the release decision trail.

It does not create release authority.

## Intended package layout

The minimal RA1 package fixture is expected to use this layout:

```text
pulse_ref_ra1_package_minimal/
  README.md
  package_manifest.json
  status/
    status.json
  policy/
    pulse_gate_policy_v0.yml
    pulse_gate_registry_v0.yml
  gates/
    materialized_gate_sets.json
  handoff/
    operator_handoff_report.json
  release_authority/
    release_authority_manifest.json
  ci/
    ci_outcome.json
  publication/
    publication_snapshot.json
  digests/
    package_digests.json
  audit/
  external_evidence/
```

## Expected future artifacts

Future PRs should populate this fixture with schema-valid artifacts:

```text
package_manifest.json
status/status.json
policy/pulse_gate_policy_v0.yml
policy/pulse_gate_registry_v0.yml
gates/materialized_gate_sets.json
handoff/operator_handoff_report.json
release_authority/release_authority_manifest.json
ci/ci_outcome.json
publication/publication_snapshot.json
digests/package_digests.json
```

Optional or later-stage areas include:

```text
audit/
external_evidence/
```

## Verification intent

A future package-level smoke test should verify that:

```text
all required package artifacts exist
all JSON artifacts validate against their RA1 schemas
package_digests.json matches artifact byte contents
package_manifest.json references existing artifacts
status digest matches operator handoff status_source digest
policy digest matches materialized gate-set metadata
CI outcome is bound to the same run identity
publication snapshot does not create release authority
```

## Authority boundary

This fixture is not a release decision.

This fixture is not a second release-decision engine.

It is a package-layout and validation target for external reconstruction of the declared-policy release path.

The normative release decision remains:

```text
status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

## Current state

This PR only establishes the fixture skeleton.

It intentionally does not add package artifact JSON files yet.

The next implementation step should populate the minimal package artifacts and then add package-level validation smoke coverage.
