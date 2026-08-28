# External Verification Path v0

## Purpose

External Verification Path v0 defines how an external reviewer can inspect and
reproduce the PULSE release-authority artifact relationship without becoming
part of the release-authority path.

The goal is to make the PULSE authority model externally readable, replayable,
and mechanically checkable through recorded artifacts, declared policy,
materialized gate sets, provenance binding, and attestation subject boundaries.

This document also records the bounded Device Ledger reproduction profile:

```text
exact .pulseledger
→ separately implemented verifier
→ reproducible PASS or fail-closed rejection
```

That profile demonstrates mechanical reproducibility without making an external
person, organization, or institution part of the proof equation.

## Verification boundary

External verification is a review carrier.

It inspects or reproduces a recorded artifact relationship.

It does not create an independent release decision function.

An external execution is an optional reproduction event.

It may provide additional evidence that the same exact artifact and verifier
produce the same result.

It is not a prerequisite of mechanical validity.

The operator is not an input to the verification equation.

```text
separately implemented verifier
≠ external validating authority

external reproduction event
≠ source of mechanical validity

operator identity
≠ verification input

institutional status
≠ truth value
```

For the bounded Device Ledger proof, validity is carried by:

```text
exact artifact
+
declared contract
+
exact binding chain
+
separately implemented verifier
+
reproducible result
```

not by:

```text
developer assertion
+
external expert opinion
+
institutional approval
```

## Carrier roles

| Carrier | Artifact / path | Mechanical role |
|---|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement | Carries release authority |
| Binding carrier | `artifact_provenance_binding_v0.json` | Carries digest-backed artifact relation |
| Verification carrier | `verify_artifact_provenance_binding_v0.py` | Recomputes and checks artifact relation |
| Reader carrier | Quality Ledger | Presents recorded state |
| Trace carrier | release authority manifest / release decision artifact | Preserves reconstruction and decision trace |
| Attestation subject | `artifact_provenance_binding_v0.json` | Primary subject for cryptographic attestation |
| External verification carrier | reviewer checklist / reproduction commands / verification packet | Reviews the recorded artifact relationship |
| Device Ledger bounded proof carrier | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger` | Carries the exact bounded Device Ledger proof subject; does not create release authority |
| Device Ledger standalone verifier | `tools/verify_pulsemech_device_ledger_v0.py` | Reconstructs the result from exact carrier bytes; separate implementation, not external authority |
| Device Ledger demonstrator | `apps/ios/PULSEmechProofApp/` | Displays the exact bounded result and exports the exact carrier; `diagnostic_shadow`, not authority |

## External verification target

The external verification target for the release-authority profile is the
recorded PULSE release-authority artifact relationship:

```text
recorded run identity
+ source commit identity
+ status.json
+ declared gate policy
+ workflow-effective materialized required gate set
+ strict CI gate-enforcement result
+ release-decision materialization artifact
+ Quality Ledger reader artifact
+ release authority manifest / trace artifact
+ artifact_provenance_binding_v0.json
+ binding_hash
+ optional attestation over the binding carrier
```

The external reproduction target for the bounded Device Ledger profile is:

```text
exact reference .pulseledger bytes
+ expected observer-key fingerprint
+ exact standalone-verifier implementation
→ exact canonical verification result
```

The two profiles have different subjects.

They preserve the same boundary:

```text
verification or reproduction
≠ release authority
```

## Minimum artifact set

A release-authority reviewer should receive or locate the following artifacts:

```text
status.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
release_decision_v0.json
release_authority_v0.json
report_card.html
artifact_provenance_binding_v0.json
```

When available, the reviewer should also inspect:

```text
status_summary.json
status_summary.md
release_decision_v0_ledger_section.html
report_card.with_release_decision.html
release_authority_audit_bundle/
attestation record for artifact_provenance_binding_v0.json
```

For the bounded Device Ledger reproduction profile, the minimum set is:

```text
examples/device_transition_ledger/
  pulsemech_device_transition_ledger_reference_v0.pulseledger

tools/
  verify_pulsemech_device_ledger_v0.py

expected observer fingerprint:
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

The canonical proof record is:

```text
docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md
```

## Verification profiles

External verification can be performed at different depths.

| Profile | Purpose | Required artifacts |
|---|---|---|
| Reader parity review | Check that public reader surfaces do not overstate authority | `status.json`, Quality Ledger |
| Authority path review | Check release decision inputs and gate enforcement path | `status.json`, policy, required gate set, `check_gates.py` semantics |
| Binding verification | Check digest-backed artifact relation | `artifact_provenance_binding_v0.json`, bound artifacts |
| Attestation review | Check attested binding carrier | binding artifact + attestation record |
| Reproducibility review | Re-run targeted tests and artifact verifiers | repo checkout + test commands |
| Release-grade review | Verify prod/materialized release-grade admissibility | status contract overlay + release-grade gates |
| Device Ledger bounded reproduction | Reproduce the exact positive result and relevant fail-closed rejection without external authority | exact `.pulseledger`, standalone verifier, expected observer fingerprint, focused round-trip tests |

## Device Ledger bounded reproduction profile

The bounded Device Ledger profile is a completed synthetic reference proof.

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256
```

It does not claim:

```text
live production iPhone observation
production installation identity
production Keychain origin
Secure Enclave origin
platform attestation
physical-device identity
device-security status
continuous background monitoring
external approval
release authority
```

### Exact positive subject

The exact reference carrier is:

```text
path:
examples/device_transition_ledger/
pulsemech_device_transition_ledger_reference_v0.pulseledger

size:
133568 bytes

SHA-256:
a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3
```

Run:

```bash
python3 tools/verify_pulsemech_device_ledger_v0.py \
  examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger \
  --expected-observer-fingerprint \
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

Expected process state:

```text
exit status:
0

stderr:
empty

ok:
true

result:
verified_with_declared_unavailability

checks:
49 / 49 passed

checkpoint signature:
verified

package signature:
verified

producer_code_imported:
false

verifier_implementation_relation:
separate_from_producer_code
```

The canonical report remains bound to the exact carrier filename, size, and
SHA-256.

### Repeated reproduction

The same exact carrier supplied to the same exact verifier must produce
byte-identical canonical report output.

```text
same exact carrier
+
same verifier implementation
→
same exact report bytes
```

The result must not depend on:

```text
generated time
temporary pathname
random ordering
process-local identity
producer verdict
operator identity
operator organization
```

### Relevant negative proof

The focused Swift round-trip suite performs a CRC-consistent mutation of:

```text
signatures/package-signature-v0.json
```

It preserves ZIP structural admissibility and reaches the package-signature
equation.

Run:

```bash
cd apps/ios/Packages/PULSEmechLedgerCore

swift test \
  --configuration debug \
  --no-parallel \
  -j 1 \
  --filter SwiftPulseledgerVerifierRoundTripTests
```

The focused suite proves:

```text
original Swift-produced carrier
→ same standalone verifier
→ PASS

repeated original carrier
→ same standalone verifier
→ byte-identical PASS report

CRC-consistent package-signature mutation
→ same standalone verifier
→ FAIL at package_signature_valid
```

Expected negative result:

```text
exit status:
2

result:
rejected

failure_stage:
package_signature

failed_check_ids:
[
  "package_signature_valid"
]

error_code:
signature_verification_failed
```

The preceding ZIP CRC, package-signature document, and package-signature subject
checks remain passed.

### Operator boundary

Any external person or organization may execute the positive command or the
focused suite.

The resulting execution may be recorded as:

```text
reproduction note
external review report
independent audit record
consumer integration test
case study
```

The execution does not become:

```text
a required approval
a validation authority
an institutional truth oracle
release authority
device-control authority
```

The proof remains valid because the exact artifact and verification mechanism
carry the result.

## External verification phases

### Phase 1 — Repository and commit identity

Verify:

```text
repository identity
source commit identity
run identity
run key
run mode
```

Expected fields may appear in:

```text
status.json
artifact_provenance_binding_v0.json
release_authority_v0.json
CI metadata
```

Mechanical boundary:

```text
external reviewer checks identity alignment
external reviewer does not redefine the release decision
```

For the Device Ledger bounded profile, also record:

```text
carrier path
carrier size
carrier SHA-256
verifier path
verifier source revision
expected observer fingerprint
```

### Phase 2 — Authority carrier inspection

Verify that the PULSEmech release-authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Review these authority-impacting elements:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
required gate selection
workflow-effective required gate set
check_gates.py true-only behavior
missing required gate behavior
status schema / release-grade overlay
release-decision materialization
```

The Device Ledger demonstrator and standalone report remain outside this
release-authority carrier.

### Phase 3 — Status and policy replay

A release-authority reviewer should inspect:

```text
status.json
gates.*
metrics.run_mode
diagnostics.gates_stubbed
diagnostics.scaffold
detectors_materialized_ok
external_summaries_present
external_all_pass
required gate set
```

Mechanical checks:

```text
required gates are present
required gate values are literal true for allow
missing required gates fail closed
false / null / string / number values are not PASS
release-grade run requires prod/materialized/non-stubbed/non-scaffolded state
```

### Phase 4 — Release-decision materialization review

Verify that release-level labels come from release-decision materialization.

Expected labels:

```text
FAIL
STAGE-PASS
PROD-PASS
```

Mechanical split:

```text
check_gates.py
= strict CI gate-enforcement carrier

release_decision_v0.json / materialize_release_decision.py
= release-decision materialization carrier
```

The Device Ledger verifier report creates no release-decision label.

### Phase 5 — Binding carrier verification

The release-authority binding carrier is:

```text
artifact_provenance_binding_v0.json
```

Verifier:

```text
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

Expected command when artifacts are available:

```bash
python PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py \
  --binding PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

The verifier recomputes:

```text
status.json digest
declared policy digest
Quality Ledger digest
release-decision artifact digest
release-authority manifest digest
workflow-effective required gate-set digest
strict CI gate-enforcement digest
binding subject digests
binding_hash
```

Verification accepts only when the recorded artifact relationship matches the
current artifact set.

### Phase 6 — Attestation subject review

Primary release-authority attestation subject:

```text
artifact_provenance_binding_v0.json
```

Mechanical role:

```text
artifact_provenance_binding_v0.json
= compact attestation subject for the recorded release-authority artifact relationship
```

Attestation review checks:

```text
attestation subject path
subject digest
binding_hash
attestation issuer / workflow identity
attestation event context
attestation occurs after binding verification
```

The attestation carrier verifies the binding carrier.

The binding carrier records the artifact relationship.

The release-authority carrier remains the PULSEmech path.

The bounded Device Ledger proof does not require an attestation or
institutional signer to establish its mechanical result.

### Phase 7 — Public reader surface parity review

Review public reader surfaces for parity with recorded artifacts.

Reader surfaces include:

```text
Quality Ledger
public status URL
Pages rendering
badges
public release-decision display
minimal Device Ledger demonstrator
```

Boundary:

```text
reader carrier ≠ authority carrier
publication carrier ≠ recorded authority artifact
trace carrier ≠ decision engine
audit bundle ≠ release decision
demonstrator ≠ external validating authority
```

Public reader surfaces must preserve:

```text
run mode
evidence materialization state
stub/scaffold state
required gate decision display
authority carrier path
traceability fields
reference or production status
claim boundary
```

The Device Ledger demonstrator must preserve:

```text
record_status = synthetic_reference
identity_scope = fixture_installation
key_origin_profile = fixture_software_p256
authority_effect = none
external_validation_claim = none
```

## Suggested external reviewer commands

For a release-authority repository checkout:

```bash
python -m py_compile \
  PULSE_safe_pack_v0/tools/check_gates.py \
  PULSE_safe_pack_v0/tools/render_quality_ledger.py \
  PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py \
  PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

Targeted tests:

```bash
python -m pytest -q tests/test_artifact_provenance_binding_v0.py
```

```bash
python -m pytest -q \
  tests/test_artifact_provenance_binding_ci_wiring_smoke.py \
  tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

```bash
python -m pytest -q \
  tests/test_render_quality_ledger.py::test_q1_reference_shadow_section_renders_when_present \
  tests/test_render_quality_ledger_public_surface_state.py
```

Tools manifest coherence:

```bash
python tests/test_tools_tests_list_smoke.py
```

Device Ledger standalone reproduction:

```bash
python3 tools/verify_pulsemech_device_ledger_v0.py \
  examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger \
  --expected-observer-fingerprint \
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

Device Ledger positive, repeated-determinism, and relevant negative proof:

```bash
cd apps/ios/Packages/PULSEmechLedgerCore

swift test \
  --configuration debug \
  --no-parallel \
  -j 1 \
  --filter SwiftPulseledgerVerifierRoundTripTests
```

These commands are reviewer and reproducer aids.

They do not replace the recorded CI run.

They do not make the operator part of the authority path.

## External verification checklist

A release-authority reviewer should answer:

```text
Repository / commit identity aligned: yes / no
Run identity aligned: yes / no
status.json present and parseable: yes / no
Declared gate policy present: yes / no
Workflow-effective required gate set reconstructable: yes / no
Required gates literal true for allow: yes / no
Release-decision artifact present: yes / no
Release label valid: yes / no
Quality Ledger parity preserved: yes / no
Release authority manifest present: yes / no
Artifact provenance binding present: yes / no
Binding verifier passes: yes / no
Attestation subject is artifact_provenance_binding_v0.json: yes / no
Attestation exists when expected: yes / no
Public reader surface boundary preserved: yes / no
```

A bounded Device Ledger reproducer should answer:

```text
Exact carrier path located: yes / no
Carrier byte size = 133568: yes / no
Carrier SHA-256 matches the canonical identity: yes / no
Expected observer fingerprint supplied: yes / no
Standalone verifier exit status = 0: yes / no
Verifier stderr empty: yes / no
Verifier result = verified_with_declared_unavailability: yes / no
Exact check set = 49 passed checks: yes / no
Checkpoint signature verified: yes / no
Package signature verified: yes / no
producer_code_imported = false: yes / no
verifier_implementation_relation = separate_from_producer_code: yes / no
authority_effect = none: yes / no
external_validation_claim = none: yes / no
Operator identity used as a verification input: no
```

## External verification report format

A minimal external verification report should include:

```text
Reviewer:
Date:
Repository:
Commit:
Run identity:
Verification subject:
Artifact set inspected:
Verification profile:
Commands run:
Binding verification result:
Standalone reproduction result:
Attestation review result:
Public reader parity result:
Authority-impact findings:
Residual issues:
Operator authority required:
Conclusion:
```

For the bounded Device Ledger profile:

```text
Operator authority required:
no
```

## External verification status classes

| Status | Meaning |
|---|---|
| Verified | Artifact relationship verified and no blocking mismatch found |
| Partially verified | Some artifact relation verified, but artifact set or attestation incomplete |
| Reader-only verified | Public reader surface matches recorded artifacts, but authority artifact replay not completed |
| Reproduced | The declared exact artifact and verifier produced the expected bounded result |
| Reproduction mismatch | Exact artifact identity or verifier result differed from the declared bounded result |
| Binding mismatch | Binding digest or subject mismatch found |
| Authority mismatch | Recorded release-authority path cannot be reconstructed from supplied artifacts |
| Inconclusive | Required artifacts unavailable |

These statuses describe the review or reproduction event.

They do not change:

```text
the underlying artifact
the verifier equation
the recorded release decision
release authority
device-control authority
```

A `Reproduced` status records that an execution matched the expected result.

It does not mean that the reviewer or institution created the result's
validity.

## Integration boundary

External verification can produce:

```text
review report
reproduction note
case study
third-party reference integration
audit finding
consumer compatibility record
```

External verification does not alter:

```text
status.json
declared gate policy
materialized required gate set
check_gates.py behavior
CI allow/block result
release decision materialization
artifact_provenance_binding_v0.json
attestation record
Device Ledger carrier bytes
Device Ledger canonical verifier report
Device Ledger claim boundary
```

The relation is:

```text
optional external execution
→ additional reproduction evidence
```

not:

```text
external approval
→ mechanical validity
```

## Machine-readable external verification packet

The repository defines:

```text
docs/EXTERNAL_VERIFICATION_PACKET_v0.md
```

The current builder implementation is:

```text
scripts/build_external_verification_packet_v0.py
```

The builder regression is:

```text
tests/test_build_external_verification_packet_v0.py
```

The default packet policy is:

```text
run-on-demand reviewer output
```

Recommended output location:

```text
temporary directory outside the repository tree
```

The packet may record:

```text
repository
commit
run identity
artifact paths
artifact digests
verification commands
expected results
binding hash
attestation subject
known missing artifacts
reviewer checklist
reviewer note
```

The packet remains a review carrier.

It must not become:

```text
an independent release-decision engine
repository-state authority
a required external approval
a replacement for exact artifact verification
```

A later PR may extend the packet with the Device Ledger bounded reproduction
profile.

Such an extension must preserve:

```text
operator identity is not a verification input
authority_effect = none
external_validation_claim = none
```

## Boundary held by this document

External Verification Path v0 defines review and reproduction paths for
recorded PULSEmech artifact relationships.

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
Device Ledger implementation
standalone Device Ledger verifier implementation
reference .pulseledger bytes
canonical Device Ledger verifier report
release tags
publication metadata
DOI / Zenodo path
```

The PULSEmech release-authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The external verification carrier reviews that recorded artifact relationship.

The bounded Device Ledger verifier reconstructs its result from exact artifact
bytes.

It does not become an external validating authority.

```text
external execution:
optional reproduction event

operator identity:
not a verification input

bounded Device Ledger mechanical proof:
closed

minimal runnable iPhone demonstrator:
closed

authority_effect:
none

external_validation_claim:
none
```
