# PULSE-REF RA1 Operating Proof v0

Status: operating proof note  
Scope: PULSE-REF RA1 minimal release-reference package verifier  
Authority: non-normative documentation of automated verifier behavior

## Purpose

This note records what the current PULSE-REF RA1 verifier proves operationally.

The proof target is not a broad claim that PULSE is a complete production platform.

The proof target is narrower and mechanical:

A canonical RA1 release-reference package can be externally reconstructed and verified from archived artifacts, and selected malformed or inconsistent package states fail closed while still producing schema-valid verifier reports.

## Operating claim

The RA1 verifier proves the following operational path:

```text
package_manifest.json
-> declared package artifact paths
-> artifact SHA-256 bindings
-> package digest coverage
-> package file inventory
-> regular-file payload boundary
-> canonical RA1 layout
-> artifact schema validation
-> gate-policy reconstruction
-> status required-gate satisfaction
-> operator handoff reconstruction
-> release authority manifest consistency
-> CI/publication identity consistency
-> authority-boundary checks
-> verifier report
```

The verifier does not authorize release.

It reconstructs and checks an archived release-reference package.

## Authority boundary

The verifier is an external reconstruction check.

It does not create release authority.

The normative release decision remains:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

The following surfaces remain non-normative unless explicitly promoted by declared policy:

```text
verifier report
release authority manifest
operator handoff report
publication snapshot
Quality Ledger
dashboards
audit bundles
```

## Canonical RA1 package layout

The canonical RA1 minimal package layout is:

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
```

The verifier enforces the canonical artifact paths declared in `package_manifest.json`.

## Positive proof

The canonical RA1 minimal fixture is expected to verify successfully:

```bash
python tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py
```

The valid fixture path is:

```text
tests/fixtures/pulse_ref_ra1_package_minimal/
```

Expected result:

```text
OK: PULSE-REF RA1 package verifier tool smoke passed
```

The valid verifier report must satisfy:

```text
report schema is pulse_ref_package_verifier_report_v0
report ok is true
errors is empty
artifact schema checks are true
artifact digest checks are true
cross-artifact checks are true
verifier authority boundary has creates_release_authority=false
```

## Cross-artifact checks

The verifier emits and checks the RA1 package through these cross-artifact checks:

```text
materialized_gate_sets_match_policy
status_satisfies_effective_required_gates
handoff_matches_status_and_gate_sets
release_authority_manifest_matches_package_core
ci_outcome_and_publication_match_release_identity
package_digests_cover_manifest_payload
package_inventory_matches_manifest
package_payload_files_are_regular_files
package_manifest_uses_canonical_layout
package_identity_matches_release_surfaces
package_manifest_authority_boundary
package_digests_authority_boundary
package_id_consistency
```

Each check is part of reconstruction evidence.

None of these checks creates release authority.

## Negative proof matrix

The verifier smoke test mutates the canonical fixture and expects fail-closed behavior.

Each failure case must return non-zero and still emit a schema-valid verifier report.

| Failure case | Expected result | Boundary proved |
|---|---:|---|
| package manifest digest mismatch | fail | artifact SHA binding |
| symlink resolves outside package root | fail | package-root containment |
| malformed digest string | fail | schema-valid failure reporting |
| schema-invalid package artifact | fail | artifact schema enforcement |
| false effective required gate | fail | required gate satisfaction |
| materialized gate-set policy mismatch | fail | policy-to-gate reconstruction |
| handoff status digest mismatch | fail | handoff/status reconstruction |
| handoff effective required gates mismatch | fail | handoff/gate-set reconstruction |
| release authority status digest mismatch | fail | release authority input binding |
| release authority effective gates mismatch | fail | release authority/gate-set binding |
| CI outcome commit mismatch | fail | CI/release identity consistency |
| publication CI URL mismatch | fail | publication/CI identity consistency |
| missing package digest entry | fail | digest coverage |
| unexpected package digest entry | fail | digest coverage exactness |
| untracked package file | fail | package inventory exactness |
| missing package file | fail | package inventory exactness |
| symlinked declared artifact inside package | fail | regular-file payload boundary |
| non-canonical status artifact path | fail | canonical layout |
| package manifest git SHA drift | fail | package identity consistency |

## Report schema proof

The verifier report must remain schema-valid for both passing and failing cases.

Required smoke checks:

```bash
python tests/test_pulse_ref_package_verifier_report_schema_v0.py
python tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py
```

Optional pytest form:

```bash
python -m pytest -q tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py
```

## Fixture proof

The RA1 minimal package fixture must remain internally consistent.

Required smoke check:

```bash
python tests/test_pulse_ref_ra1_minimal_package_fixture.py
```

Optional pytest form:

```bash
python -m pytest -q tests/test_pulse_ref_ra1_minimal_package_fixture.py
```

## What this proves

This proves that the RA1 reference package can be reconstructed as an artifact-bound release-state package.

It proves that:

```text
declared artifact paths are canonical
package files match declared inventory
declared payload files are regular files
digest coverage is exact
artifact hashes bind to current bytes
package artifacts validate against schemas
materialized gate sets match packaged policy
status satisfies effective required gates
operator handoff matches status and gate sets
release authority manifest matches package core
CI and publication surfaces match release identity
package identity does not drift across release surfaces
verifier reports stay schema-valid
verifier authority boundary remains non-normative
```

## What this does not prove

This does not prove that every future PULSE release is safe.

This does not prove full production security, supply-chain provenance, SBOM completeness, or organizational compliance.

This does not replace release policy, gate semantics, status evidence, strict gate checking, or primary CI release-decision authority.

This is an operating proof for the RA1 reference package reconstruction path.

## Summary

PULSE-REF RA1 operating proof is:

```text
canonical package
-> verifier reconstruction
-> positive pass
-> negative fail-closed mutations
-> schema-valid reports
-> non-authorizing verifier boundary
```

The verifier demonstrates that archived RA1 package evidence can be checked mechanically without turning the verifier, ledger, manifest, publication snapshot, or handoff report into a second release-decision engine.
