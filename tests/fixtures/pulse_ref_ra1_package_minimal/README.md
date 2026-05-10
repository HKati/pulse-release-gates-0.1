# PULSE-REF RA1 Minimal Release-Reference Package Fixture

Status: partially populated RA1 fixture  
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

The minimal RA1 package fixture uses this target layout:

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

## Current populated artifacts

The fixture currently includes these package artifacts:

```text
status/status.json
policy/pulse_gate_policy_v0.yml
policy/pulse_gate_registry_v0.yml
gates/materialized_gate_sets.json
handoff/operator_handoff_report.json
release_authority/release_authority_manifest.json
ci/ci_outcome.json
publication/publication_snapshot.json
```

These artifacts establish the current RA1 minimal package chain:

```text
status.json
-> declared gate policy
-> materialized required gate set
-> operator handoff reconstruction
-> release authority manifest
-> CI outcome
-> publication snapshot
```

## Pending package artifacts

The fixture intentionally does not yet include:

```text
package_manifest.json
digests/package_digests.json
```

These should be added only after the currently populated artifacts are stable enough to be bound by digest.

The package manifest and digest manifest will bind the package into a stronger externally verifiable artifact set.

## Optional or later-stage areas

The following directories are reserved for later-stage package expansion:

```text
audit/
external_evidence/
```

These areas may later hold audit bundle contents and external evidence artifacts.

They are not required for the current minimal fixture state.

## Current validation coverage

The current minimal package fixture is validated by:

```text
tests/test_pulse_ref_ra1_minimal_package_fixture.py
```

That smoke test verifies the current package state:

```text
expected package artifacts exist
RA1 JSON artifacts validate against their schemas
release authority manifest passes the existing checker
materialized gate sets match the packaged policy
status artifact satisfies all effective required gates
handoff report matches status and materialized gate-set artifacts
release authority manifest matches the package core
CI outcome and publication snapshot preserve the non-authority boundary
```

This test is registered in:

```text
ci/tools-tests.list
```

so the fixture validation runs in the tools smoke suite.

## Verification intent

Future package-level validation should extend the current fixture checks to include:

```text
package_digests.json matches artifact byte contents
package_manifest.json references existing artifacts
package_manifest.json references the package digest manifest
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

The following fixture surfaces are non-normative:

```text
operator handoff report
release authority manifest
publication snapshot
package manifest
package digest manifest
README
audit bundle
external evidence directory
```

They may preserve, explain, reconstruct, or verify release state.

They do not authorize release independently.

## Current state

The RA1 minimal package fixture is partially populated and actively smoke-tested.

The next implementation step should add digest binding:

```text
digests/package_digests.json
```

After that, the package manifest can be added:

```text
package_manifest.json
```

The package manifest should reference the populated artifacts and the digest manifest without creating release authority.
