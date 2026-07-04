# PULSEmech SLSA / in-toto evidence intake v0

## Function

This document defines how SLSA / in-toto verification output enters the PULSEmech release-authority path as recorded evidence.

SLSA / in-toto verification produces provenance and verification evidence.

PULSEmech records that evidence, binds it to declared policy, materializes required gates, and enforces the release transition through `check_gates.py`.

## Release-authority path

```text
SLSA / in-toto verification output
→ recorded PULSE evidence
→ final status.json
→ declared PULSE policy
→ workflow-effective materialized required gates
→ strict enforcement by check_gates.py
→ primary CI allow/block release decision
```

## Input evidence contract

A SLSA / in-toto evidence intake record carries the following fields when available:

```text
subject.digest
predicateType
verifier.id
verifier.version
timeVerified
resourceUri
policy.uri
policy.digest
inputAttestations[].uri
inputAttestations[].digest
verificationResult
verifiedLevels
dependencyLevels
slsaVersion
```

## Evidence role

The SLSA / in-toto verification result enters PULSE as evidence state.

The evidence state is recorded into the PULSE artifact chain and evaluated by declared PULSE policy.

Release authority is materialized by the PULSE path:

```text
recorded evidence
→ policy binding
→ gate materialization
→ fail-closed gate enforcement
→ CI allow/block result
```

## VSA-to-PULSE signal mapping

| SLSA / in-toto VSA field | PULSE evidence signal |
| --- | --- |
| `subject.digest` | artifact identity binding |
| `predicateType` | evidence format contract |
| `verifier.id` | verifier identity binding |
| `verifier.version` | verifier implementation record |
| `timeVerified` | verification timestamp |
| `resourceUri` | artifact resource binding |
| `policy.uri` | verification policy identity |
| `policy.digest` | verification policy version binding |
| `inputAttestations[].digest` | evidence-chain digest binding |
| `verificationResult` | verification result evidence |
| `verifiedLevels` | verified SLSA level evidence |
| `dependencyLevels` | dependency verification summary |
| `slsaVersion` | SLSA specification version record |

## Gate materialization

A PULSE policy may declare SLSA / in-toto evidence as required release evidence.

When required, the materialized gate set may include signals such as:

```text
slsa_vsa_present
slsa_vsa_signature_ok
slsa_vsa_subject_matches_artifact
slsa_vsa_predicate_type_ok
slsa_vsa_verifier_trusted
slsa_vsa_resource_uri_matches
slsa_vsa_policy_digest_matches
slsa_vsa_result_passed
slsa_vsa_verified_level_ok
```

Each signal is recorded as a literal boolean gate value in `status.json`.

## Enforcement table

| Condition | Recorded PULSE signal | Release effect when required |
| --- | --- | --- |
| VSA artifact present | `slsa_vsa_present=true` | gate can pass |
| VSA artifact absent | `slsa_vsa_present=false` | fail-closed |
| VSA signature verified | `slsa_vsa_signature_ok=true` | gate can pass |
| VSA signature mismatch | `slsa_vsa_signature_ok=false` | fail-closed |
| Subject digest matches release artifact | `slsa_vsa_subject_matches_artifact=true` | gate can pass |
| Subject digest mismatch | `slsa_vsa_subject_matches_artifact=false` | fail-closed |
| Predicate type matches expected VSA type | `slsa_vsa_predicate_type_ok=true` | gate can pass |
| Predicate type mismatch | `slsa_vsa_predicate_type_ok=false` | fail-closed |
| Verifier identity matches declared trust policy | `slsa_vsa_verifier_trusted=true` | gate can pass |
| Verifier identity outside declared trust policy | `slsa_vsa_verifier_trusted=false` | fail-closed |
| Resource URI matches expected artifact URI | `slsa_vsa_resource_uri_matches=true` | gate can pass |
| Resource URI mismatch | `slsa_vsa_resource_uri_matches=false` | fail-closed |
| Policy digest matches expected policy digest | `slsa_vsa_policy_digest_matches=true` | gate can pass |
| Policy digest mismatch | `slsa_vsa_policy_digest_matches=false` | fail-closed |
| Verification result is `PASSED` | `slsa_vsa_result_passed=true` | gate can pass |
| Verification result is `FAILED` | `slsa_vsa_result_passed=false` | fail-closed |
| Verified level matches declared PULSE requirement | `slsa_vsa_verified_level_ok=true` | gate can pass |
| Verified level below declared PULSE requirement | `slsa_vsa_verified_level_ok=false` | fail-closed |

## Decision materialization

A passing SLSA / in-toto verification result records evidence.

PULSE release authority is produced when the recorded evidence satisfies declared PULSE policy and all workflow-effective required gates pass under `check_gates.py`.

## Minimal v0 implementation path

```text
schemas/slsa_vsa_evidence_v0.schema.json
examples/slsa/slsa_vsa_evidence_example_v0.json
tools/ingest_slsa_vsa_evidence_v0.py
tests/test_ingest_slsa_vsa_evidence_v0.py
```

## Mechanical invariant

```text
verified provenance evidence
→ recorded PULSE evidence
→ materialized required gate
→ strict fail-closed enforcement
→ release allow/block
```
