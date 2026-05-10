# PULSE-REF RA1 Package Verifier Workflow v0

Status: verifier workflow contract  
Scope: PULSE-REF RA1 externally verifiable release-reference package  
Authority: documentation-only verifier workflow contract

## Core statement

A PULSE-REF RA1 package verifier reconstructs the release-reference package from archived artifacts.

It verifies that the package artifacts are present, schema-valid, digest-bound, internally consistent, and aligned with the declared-policy release-authority path.

The verifier does not create release authority.

It verifies preservation of the existing release-authority trail:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

The verifier is an audit / reconstruction tool.

It is not a release-decision engine.

## Input

The verifier receives a package root directory.

Example:

```text
tests/fixtures/pulse_ref_ra1_package_minimal/
```

The package root should contain:

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

Optional later-stage package areas may include:

```text
audit/
external_evidence/
```

## Verification order

The verifier should use a stable order.

### 1. Package manifest parse

The verifier first loads:

```text
package_manifest.json
```

The file must be valid JSON.

The manifest must validate against:

```text
schemas/pulse_ref_release_reference_package_v0.schema.json
```

The manifest binds the package-level artifact references.

It does not create release authority.

### 2. Package digest manifest parse

The verifier loads:

```text
digests/package_digests.json
```

The file must be valid JSON.

The digest manifest must validate against:

```text
schemas/pulse_ref_package_digests_v0.schema.json
```

The digest manifest binds package artifact paths to SHA-256 values.

It does not create release authority.

### 3. Artifact reference existence

Every artifact reference in `package_manifest.json` must exist under the package root.

Required artifact references include:

```text
status_artifact
gate_policy
gate_registry
materialized_gate_sets
operator_handoff_report
release_authority_manifest
ci_outcome
package_digests
```

Optional artifact references should be checked when present:

```text
publication_snapshot
audit_bundle
external_evidence
```

The verifier must reject missing required artifacts.

### 4. Path safety

Package artifact paths must be package-relative.

The verifier should reject:

```text
absolute paths
parent-directory traversal
Windows backslash paths in package references
empty paths
```

The package verifier must not follow package references outside the package root.

### 5. SHA-256 validation

For every artifact reference in `package_manifest.json`, the verifier computes the SHA-256 of the referenced file and compares it with the recorded digest.

The verifier must reject any digest mismatch.

For package digest entries in `digests/package_digests.json`, the verifier computes the SHA-256 for each listed artifact and compares it with the recorded digest.

The verifier must reject:

```text
missing artifact listed in package_digests.json
bad SHA-256 value
digest mismatch
unexpected duplicate semantic reference
```

## Digest relationship

The current RA1 minimal package fixture uses this digest relationship:

```text
package_manifest.json -> references digests/package_digests.json by SHA-256
digests/package_digests.json -> records payload artifact SHA-256 values
```

The digest manifest intentionally does not hash itself.

The digest manifest also intentionally does not hash `package_manifest.json` in the current hand-authored minimal fixture.

This avoids a circular digest relationship.

The verifier should not require `package_manifest.json` to be listed in `digests/package_digests.json` unless a later package format explicitly changes this rule.

## Schema validation

The verifier should validate package artifacts against their schemas:

```text
gates/materialized_gate_sets.json
-> schemas/pulse_ref_materialized_gate_sets_v0.schema.json

handoff/operator_handoff_report.json
-> schemas/pulse_ref_operator_handoff_report_v0.schema.json

ci/ci_outcome.json
-> schemas/pulse_ref_ci_outcome_v0.schema.json

publication/publication_snapshot.json
-> schemas/pulse_ref_publication_snapshot_v0.schema.json

digests/package_digests.json
-> schemas/pulse_ref_package_digests_v0.schema.json

package_manifest.json
-> schemas/pulse_ref_release_reference_package_v0.schema.json
```

The release authority manifest should be checked against:

```text
schemas/release_authority_v0.schema.json
```

and should also pass the existing semantic checker:

```text
PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py
```

## Gate-set reconstruction check

The verifier should reconstruct the gate sets from the packaged policy:

```text
policy/pulse_gate_policy_v0.yml
```

It should compare the reconstructed sets to:

```text
gates/materialized_gate_sets.json
```

The verifier should check:

```text
sets.required matches policy gates.required
sets.release_required matches policy gates.release_required
effective_required_gates equals ordered union of required + release_required
policy_sha256 matches packaged policy byte digest
policy_path matches package-relative policy path
authority_boundary.creates_release_authority = false
```

## Status gate satisfaction check

The verifier should load:

```text
status/status.json
```

It should confirm:

```text
metrics.run_mode = prod
diagnostics.gates_stubbed = false
```

It should verify that every gate in:

```text
gates/materialized_gate_sets.json effective_required_gates
```

exists in:

```text
status/status.json gates
```

and has value:

```text
true
```

Missing or false effective required gates must fail verification.

## Operator handoff consistency check

The verifier should load:

```text
handoff/operator_handoff_report.json
```

It should check:

```text
gate_mode = release-grade
status_source.mode = existing
status_source.status_path matches package status artifact path
status_source status SHA-256 values match status/status.json
materialized_gate_sets matches gates/materialized_gate_sets.json sets
effective_required_gates matches gates/materialized_gate_sets.json effective_required_gates
authority_boundary.creates_release_authority = false
```

For a passing RA1 minimal fixture, `ok` should be true.

For future fail-closed RA1 fixtures, `ok=false` may be valid when the package is explicitly testing fail-closed reconstruction.

## Release authority manifest consistency check

The verifier should load:

```text
release_authority/release_authority_manifest.json
```

It should check:

```text
run_identity.run_mode = prod
inputs.status_json matches status artifact path and digest
inputs.gate_policy matches policy artifact path and digest
inputs.gate_registry matches registry artifact path and digest
authority.policy_set = required+release_required
authority.release_required_materialized = true
authority.effective_required_gates matches materialized gate set effective_required_gates
evaluation.required_gate_results contains all effective required gates with true values
evaluation.failed_required_gates = []
evaluation.missing_required_gates = []
decision.state = PASS
decision.fail_closed = true
diagnostics.shadow_surfaces_non_normative = true
```

The release authority manifest preserves the release-authority trail.

It does not create release authority.

## CI outcome consistency check

The verifier should load:

```text
ci/ci_outcome.json
```

It should check:

```text
provider = github_actions
gate_check_conclusion = success
run_attempt >= 1
authority_boundary.creates_release_authority = false
```

It should compare CI identity with the release authority manifest:

```text
ci_outcome.run_id = release_authority.run_identity.run_id
ci_outcome.run_attempt = release_authority.run_identity.attempt
ci_outcome.commit_sha = release_authority.run_identity.git_sha
```

## Publication snapshot consistency check

The verifier should load:

```text
publication/publication_snapshot.json
```

It should check:

```text
creates_release_authority = false
git_sha matches ci_outcome.commit_sha
ci_outcome_url matches ci_outcome.run_url
```

Publication surfaces expose and preserve release state.

They do not authorize release.

## Authority-boundary invariants

The verifier must reject any package artifact that claims to create release authority through audit or publication surfaces.

The following must remain false when present:

```text
package_manifest.authority_boundary.creates_release_authority
digests/package_digests.authority_boundary.creates_release_authority
handoff/operator_handoff_report.authority_boundary.creates_release_authority
ci/ci_outcome.authority_boundary.creates_release_authority
publication/publication_snapshot.creates_release_authority
```

The verifier must preserve the PULSE boundary:

```text
release authority is produced by declared-policy gate enforcement and CI outcome,
not by package manifests, digest manifests, handoff reports, publication snapshots,
release authority manifests, ledgers, dashboards, summaries, docs, or audit bundles.
```

## Expected verifier output

A future verifier tool should produce a JSON report.

Suggested output fields:

```json
{
  "ok": true,
  "package_root": "<path>",
  "checked_utc": "<timestamp>",
  "schemas_validated": [],
  "artifact_digests_checked": [],
  "cross_artifact_checks": [],
  "warnings": [],
  "errors": [],
  "authority_boundary": {
    "verifier_role": "external_reconstruction_check",
    "creates_release_authority": false
  }
}
```

The verifier output is itself an audit artifact.

It does not create release authority.

## Fail-closed behavior

The verifier should fail closed on:

```text
invalid JSON
schema validation failure
missing required artifact
unsafe path
digest mismatch
policy/gate-set mismatch
status missing an effective required gate
status false for an effective required gate
handoff/status digest mismatch
release authority manifest semantic failure
CI identity mismatch
publication snapshot authority violation
unexpected release-authority claim
```

## Relation to current fixture smoke test

The current fixture-level smoke test is:

```text
tests/test_pulse_ref_ra1_minimal_package_fixture.py
```

That test already checks the current minimal package fixture.

The future verifier tool should generalize the same checks from a fixture-specific test into a reusable package verifier.

The verifier workflow contract exists to prevent the tool from becoming a second release-decision engine.

## Summary

The RA1 package verifier checks that an archived release-reference package is complete, schema-valid, digest-bound, internally consistent, and aligned with the declared-policy release-authority path.

It reconstructs and verifies release state.

It does not authorize release.
