# External Verification Packet v0

## Purpose

External Verification Packet v0 defines a review packet for external verification of the PULSEmech release-authority artifact relationship.

The packet is designed for:

```text
external reviewers
independent auditors
consumer-side verifiers
third-party reproduction attempts
reference integration reviewers
```

The packet records which artifacts, digests, commands, and carrier boundaries a reviewer should inspect to reconstruct the PULSEmech authority path for a declared repository state.

The packet is an external verification carrier.

It is not a release-authority carrier.

It does not create an independent release-decision engine.

## Authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

External Verification Packet v0 reviews this recorded artifact relationship.

It does not replace it.

## Review carrier boundary

The External Verification Packet is a review carrier.

It may record:

```text
repository identity
commit identity
run identity
artifact paths
artifact digests
verification commands
carrier boundaries
expected reviewer checks
known missing artifacts
reviewer conclusion fields
```

It must not silently become:

```text
release authority
required gate input
policy artifact
status artifact
publication metadata
DOI / Zenodo artifact
repository-state authority
```

## Default artifact policy

The default policy is:

```text
run-on-demand reviewer output
```

This means:

```text
The packet is generated on demand for a declared repository state.
The packet is reviewed as an external verification artifact.
The packet is not committed by default.
The packet must be tied to a specific commit / HEAD.
The working tree should remain clean after generation.
```

A future PR may adopt a checked-in packet or stable linked packet artifact, but that must be explicitly declared.

## Packet outputs

Recommended generated output names:

```text
external_verification_packet_v0.json
external_verification_packet_v0.md
```

Recommended routine output location:

```text
temporary directory outside the repository tree
```

Example:

```bash
TMPDIR="$(mktemp -d)"

python scripts/build_external_verification_packet_v0.py \
  --repo-root . \
  --out-json "$TMPDIR/external_verification_packet_v0.json" \
  --out-md "$TMPDIR/external_verification_packet_v0.md"

git status --short
```

Expected result:

```text
working tree clean
```

## Minimum packet contents

A minimal External Verification Packet v0 should contain:

```text
schema_id
schema_version
generated_utc
repository
commit
run_identity
authority_carrier
artifact_records
verification_commands
carrier_boundary_summary
reviewer_checklist
known_missing_artifacts
packet_boundary
```

## Suggested JSON shape

```json
{
  "schema_id": "pulse.external_verification_packet.v0",
  "schema_version": "0.1.0",
  "generated_utc": "...",
  "repository": {
    "name": "HKati/pulse-release-gates-0.1",
    "root": ".",
    "remote": "optional"
  },
  "commit": {
    "git_sha": "...",
    "branch": "...",
    "dirty_worktree": false
  },
  "run_identity": {
    "run_id": "...",
    "run_key": "...",
    "run_mode": "...",
    "created_utc": "..."
  },
  "authority_carrier": "status.json -> declared gate policy -> workflow-effective materialized required gate set -> strict fail-closed CI enforcement",
  "artifact_records": [],
  "verification_commands": [],
  "carrier_boundary_summary": [],
  "reviewer_checklist": [],
  "known_missing_artifacts": [],
  "packet_boundary": "external verification carrier; not release authority"
}
```

## Artifact records

Each artifact record should use this structure:

```json
{
  "role": "status",
  "path": "PULSE_safe_pack_v0/artifacts/status.json",
  "required": true,
  "exists": true,
  "sha256": "...",
  "carrier_class": "authority",
  "boundary": "recorded release-state artifact"
}
```

Recommended fields:

```text
role
path
required
exists
sha256
carrier_class
boundary
notes
```

## Required artifact roles

The packet should attempt to record these artifacts.

| Role | Typical path | Required for v0 packet | Carrier class |
|---|---|---:|---|
| status | `PULSE_safe_pack_v0/artifacts/status.json` | yes | authority |
| gate policy | `pulse_gate_policy_v0.yml` | yes | policy |
| gate registry | `pulse_gate_registry_v0.yml` | yes | policy / registry |
| release decision | `PULSE_safe_pack_v0/artifacts/release_decision_v0.json` | conditional | trace / decision materialization |
| release authority manifest | `PULSE_safe_pack_v0/artifacts/release_authority_v0.json` | conditional | trace |
| artifact provenance binding | `PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json` | conditional | binding |
| Quality Ledger | `PULSE_safe_pack_v0/artifacts/report_card.html` | conditional | reader |
| composed release-decision report | `PULSE_safe_pack_v0/artifacts/report_card.with_release_decision.html` | optional | reader |
| status summary JSON | `PULSE_safe_pack_v0/artifacts/status_summary.json` | optional | reader / summary |
| status summary Markdown | `PULSE_safe_pack_v0/artifacts/status_summary.md` | optional | reader / summary |

Conditional means:

```text
record if present
mark missing if absent
do not fabricate
do not fail unless the selected verification profile requires it
```

## Carrier classes

The packet should preserve carrier separation.

Suggested carrier classes:

```text
authority
policy
registry
enforcement
trace
reader
binding
attestation
audit_preservation
diagnostic_shadow
external_verification
```

The packet itself is:

```text
external_verification
```

## Verification commands

The packet should include commands that a reviewer can run.

Recommended commands:

```bash
python -m py_compile \
  PULSE_safe_pack_v0/tools/check_gates.py \
  PULSE_safe_pack_v0/tools/materialize_release_decision.py \
  PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py \
  PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

```bash
python -m pytest -q tests/test_artifact_provenance_binding_v0.py
```

```bash
python -m pytest -q \
  tests/test_artifact_provenance_binding_ci_wiring_smoke.py \
  tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

If the artifact provenance binding exists:

```bash
python PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py \
  --binding PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

If the inventory report builder exists:

```bash
TMPDIR="$(mktemp -d)"

python scripts/build_normative_shadow_inventory_v0.py \
  --repo-root . \
  --out-json "$TMPDIR/normative_shadow_inventory_v0.json" \
  --out-md "$TMPDIR/normative_shadow_inventory_v0.md"

git status --short
```

## Verification profiles

External verification can be performed at multiple depths.

| Profile | Purpose | Required records |
|---|---|---|
| `identity` | Verify repository / commit / run identity | repository, commit, run_identity |
| `authority-path` | Review the PULSEmech authority carrier | status, policy, registry, required gate source |
| `binding` | Verify digest-backed artifact relationship | artifact provenance binding and referenced artifacts |
| `reader-parity` | Inspect reader surfaces against recorded state | status, Quality Ledger, summaries |
| `attestation-review` | Review attestation subject and boundary | binding artifact and attestation record if available |
| `full-review` | Combine all available packet checks | all present records |

The v0 packet may support all profiles as metadata, even if the first builder implements only a subset.

## Authority-path reviewer checklist

A reviewer should verify:

```text
status.json exists
status.json is parseable
declared gate policy exists
gate registry exists
required gate source is identifiable
required gates are materialized
check_gates.py enforces literal true-only semantics
missing required gates fail closed
release-decision artifact is present when expected
binding artifact is present when expected
binding verifier passes when binding is present
reader surfaces do not claim independent authority
```

## Binding reviewer checklist

If `artifact_provenance_binding_v0.json` is present, a reviewer should verify:

```text
binding file exists
binding JSON is parseable
binding hash is present
bound artifact paths exist
bound artifact digests match
workflow-effective required gate-set digest is recorded
release decision artifact is not misattributed to check_gates.py
attestation subject is the binding carrier when attestation is present
```

## Reader-surface reviewer checklist

A reviewer should verify:

```text
Quality Ledger is a reader carrier
Quality Ledger does not claim independent release authority
public reader surface state matches recorded status fields
core/demo/stubbed states are not presented as materialized prod release-grade evidence
release-grade wording requires prod, non-stubbed, non-scaffolded, materialized evidence state
```

## Attestation reviewer checklist

When attestation exists, a reviewer should verify:

```text
attestation subject is artifact_provenance_binding_v0.json
attestation occurs after binding materialization and verification
attestation credentials are isolated to the attestation job
attestation action is pinned
artifact download is repository-explicit
main release job remains read-only
```

## Known missing artifacts

The packet must support explicit missing-artifact records.

Example:

```json
{
  "role": "artifact provenance binding",
  "path": "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json",
  "required": false,
  "exists": false,
  "sha256": null,
  "carrier_class": "binding",
  "boundary": "binding carrier missing for this reviewed state",
  "notes": "Binding may be unavailable for local or docs-only review states."
}
```

Missing optional artifacts are not failures by themselves.

Missing required artifacts must be reported as verification blockers for the selected profile.

## Packet status

Suggested packet status values:

```text
verified
partially_verified
reader_only
binding_missing
authority_artifact_missing
verification_failed
inconclusive
```

Suggested meaning:

| Status | Meaning |
|---|---|
| `verified` | Required profile artifacts exist and checks pass |
| `partially_verified` | Some checks pass but optional or conditional artifacts are missing |
| `reader_only` | Only reader surfaces could be reviewed |
| `binding_missing` | Binding profile requested but binding artifact is missing |
| `authority_artifact_missing` | Required authority artifact missing |
| `verification_failed` | A required verification check failed |
| `inconclusive` | Review could not establish enough artifact state |

## Reviewer report format

A reviewer report should contain:

```text
External Verification Packet review:
- Repository:
- Commit / HEAD:
- Packet path:
- Packet status:
- Verification profile:
- Commands run:
- Required artifacts present:
- Missing artifacts:
- Binding verification:
- Reader parity:
- Attestation review:
- Working tree clean after generation:
- Conclusion:
```

## Relation to existing PULSE documents

External Verification Packet v0 is aligned with:

```text
EXTERNAL_VERIFICATION_PATH_v0.md
RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md
NORMATIVE_SHADOW_INVENTORY_MODEL_v0.md
NORMATIVE_SHADOW_INVENTORY_REPORT_ARTIFACT_POLICY_v0.md
PULSE_NATIVE_REVIEW_FRAME_v0.md
```

This document defines the packet contract.

It does not implement the packet builder.

A later PR may add:

```text
scripts/build_external_verification_packet_v0.py
tests/test_build_external_verification_packet_v0.py
```

## Future builder boundary

A future builder should:

```text
read repository state
collect artifact records
compute sha256 digests
record missing artifacts explicitly
emit JSON packet
emit Markdown packet
write outputs to a declared path
support temporary output during review
keep working tree clean by default
```

A future builder must not:

```text
modify source files
modify release artifacts
modify status.json
modify gate policy
modify gate registry
modify release decisions
modify DOI / Zenodo paths
treat generated packets as source files by default
```

## Future checked-in packet option

A future PR may adopt a checked-in packet artifact.

If so, it must define:

```text
path
refresh procedure
commit binding
review procedure
staleness policy
authority boundary
```

Until such a policy exists, the default packet model remains:

```text
run-on-demand reviewer output
```

## Boundary held by this document

This document defines the External Verification Packet v0 contract.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The External Verification Packet remains an external verification carrier.

## Final definition

External Verification Packet v0 is:

```text
a review carrier that records repository identity, commit identity,
run identity, artifact records, digests, verification commands,
carrier boundaries, and reviewer checklist fields for reconstructing
the PULSEmech authority path from recorded artifacts.
```

It is not release authority.

It supports external verification of the artifact relationship that carries release authority.
