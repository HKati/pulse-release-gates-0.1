# PULSEmech Device Ledger Bounded Mechanical Proof v0

## Document role

```text
document_role:
current_implementation_and_completed_bounded_proof

subject:
PULSEmech Device Ledger v0 bounded mechanical proof

implementation_state:
merged_and_regression_proven

bounded_mechanical_self_proof:
closed

minimal_runnable_iphone_demonstrator:
closed

authority_effect:
none

external_validation_claim:
none
```

This document records the exact bounded proof implemented in the repository for
the PULSEmech Device Ledger v0 mechanism.

It defines:

```text
what the mechanism proves
how the proof is reconstructed
which exact artifacts carry the proof
what the separately implemented verifier does
why a privileged external validating authority is unnecessary
what the runnable iPhone demonstrator displays and exports
which claims remain explicitly absent
```

This document is a technical proof record.

It is not:

```text
a release decision
a release-authority carrier
an external certification
an institutional approval
a device-security verdict
a production iPhone monitoring specification
```

## Merged implementation identity

The minimal runnable demonstrator was merged through:

```text
pull request:
#2847

squash-merge commit:
6a358187d8fde7321963b76cc50cc77fad695dd0

direct parent:
954bd8d36490c95e601dee3e9cbaefdb81b65996

reviewed final PR head:
ce2316b9988499da71bf1eb1f51a0d699f10f925
```

Canonical references:

- [PR #2847](https://github.com/HKati/pulse-release-gates-0.1/pull/2847)
- [Merged commit `6a358187d8fde7321963b76cc50cc77fad695dd0`](https://github.com/HKati/pulse-release-gates-0.1/commit/6a358187d8fde7321963b76cc50cc77fad695dd0)

The exact parent-to-merge scope was:

```text
6 files added
0 existing files modified
0 files deleted
2630 insertions
```

The merge changed no production `PULSEmechLedgerCore` source, standalone Python
verifier, reference artifact, contract, schema, policy, gate registry,
`status.json`, release decision, publication metadata, DOI, or Zenodo
relationship.

---

## 1. Exact mechanical claim

The bounded claim is:

> PULSEmech can create an exact, closed artifact from a declared bounded
> relation, and a separately implemented verifier can reconstruct the result
> from the artifact bytes without relying on a privileged external validating
> authority.

The proof relation is:

```text
bounded relation
→ exact evidence records
→ predecessor-bound record chain
→ terminal checkpoint
→ canonical ledger
→ checkpoint signature
→ exact payload inventory
→ canonical manifest
→ package signature
→ deterministic .pulseledger
→ separately implemented verifier reconstruction
→ reproducible PASS or fail-closed rejection
```

The source of mechanical validity is:

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

It is not:

```text
developer assertion
+
external expert opinion
+
institutional approval
```

---

## 2. Verifier separation is not external authority

The following distinctions are normative for this proof:

```text
separately implemented verifier
≠
external validating authority

functional implementation separation
≠
organizational independence requirement

external reproduction event
≠
source of mechanical validity

institutional status
≠
input to the verification result
```

The verifier is separate because it does not trust a producer verdict.

It reconstructs the result from:

```text
exact .pulseledger bytes
declared canonicalization contract
declared observation contract
declared schemas
manifest inventory
member digests and sizes
record-chain relations
signature subjects
signature equations
claim boundary
authority boundary
```

Any person or organization may run the verifier.

Such a run is a new reproduction event.

The identity, title, rank, affiliation, reputation, or institutional authority
of the operator is not part of the verification equation and is not a
prerequisite of the proof.

The operator does not make the artifact valid.

The artifact and the verifier relation determine the result.

---

## 3. Implemented proof layers

| Layer | Repository path | Mechanical role |
|---|---|---|
| Device Ledger core | `apps/ios/Packages/PULSEmechLedgerCore/` | Produces the bounded ledger, checkpoint, signatures, manifest, and deterministic carrier |
| Canonicalization contract | `contracts/pulsemech_device_canonical_json_v0.json` | Declares the canonical JSON profile |
| Observation contract | `contracts/pulsemech_ios_observation_contract_v0.json` | Declares the bounded iOS observation semantics |
| Device Ledger schemas | `schemas/pulsemech_device_*_v0.schema.json` | Define ledger, manifest, signature, and verifier-report structures |
| Reference carrier | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger` | Carries the exact ten-member proof package |
| Canonical verifier report | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json` | Records the exact separate-verifier result |
| Separate verifier | `tools/verify_pulsemech_device_ledger_v0.py` | Reconstructs the proof from exact carrier bytes |
| Swift-to-verifier round trip | `SwiftPulseledgerVerifierRoundTripTests.swift` | Proves positive reproduction, determinism, and relevant fail-closed rejection |
| Runnable iPhone demonstrator | `apps/ios/PULSEmechProofApp/` | Executes the deterministic reference materialization, displays exact identities, and exports the exact carrier |
| Demonstrator workflow | `.github/workflows/pulsemech_ios_proof_app.yml` | Builds and tests the app as a non-authorizing diagnostic/shadow surface |

---

## 4. Bounded reference relation

The runnable demonstrator executes the established deterministic synthetic
reference relation:

```text
session A open
→ Wi-Fi observation
→ cellular observation
→ continuous coverage relation
→ event-bound transition
→ session A close
→ session B open
→ fresh Wi-Fi observation
→ interrupted coverage relation
→ endpoint-difference-only transition
→ terminal checkpoint
```

The resulting bounded relation contains:

```text
record count:
14

session count:
2

clock-epoch count:
2

session-boundary count:
3

continuous coverage count:
1

interrupted coverage count:
1

event-bound transition count:
1

endpoint-difference-only transition count:
1
```

These values are derived from the generated closure and checkpoint summary.

They are not independently supplied UI assertions.

### Reference-status boundary

The implemented demonstration uses:

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256
```

Therefore, this proof demonstrates the complete bounded artifact and
reconstruction mechanism.

It does not claim:

```text
a live production iPhone observation session
a production installation identity
a hardware-backed production key
a physical-device attestation
```

---

## 5. Exact artifact identities

A successful reference materialization must produce these exact identities:

| Object | Exact identity |
|---|---|
| Terminal checkpoint SHA-256 | `16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff` |
| Canonical ledger SHA-256 | `360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77` |
| Canonical manifest SHA-256 | `47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1` |
| Carrier size | `133568` bytes |
| Carrier SHA-256 | `a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3` |
| Carrier member count | `10` |
| Canonical verifier-report size | `15328` bytes |
| Canonical verifier-report SHA-256 | `5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4` |
| Verifier check count | `49` |

The reference carrier filename is:

```text
pulsemech_device_transition_ledger_reference_v0.pulseledger
```

A mismatch in the checkpoint, ledger, manifest, carrier digest, carrier size,
carrier member count, verifier-report size, or verifier-report digest fails
closed before a successful result is returned.

---

## 6. Deterministic `.pulseledger` carrier

The carrier contains exactly ten stored regular-file members in a fixed order.

Its construction binds:

```text
eight exact payload members
+
canonical manifest
+
canonical package-signature document
→ deterministic bounded ZIP carrier
→ exact .pulseledger bytes
→ carrier SHA-256
```

The carrier writer fixes:

```text
member paths
member order
stored compression
timestamps
regular-file attributes
CRC32
local headers
central-directory rows
EOCD
absence of ZIP64
absence of trailing bytes
```

The Swift writer reproduces the checked-in reference carrier byte-for-byte.

Parsed-ZIP equivalence is insufficient.

The proof requires exact carrier-byte equality.

---

## 7. Separately implemented verifier

The verifier entrypoint is:

```text
tools/verify_pulsemech_device_ledger_v0.py
```

The verifier is implemented separately from the Swift producer.

The successful report records:

```text
ok:
true

result:
verified_with_declared_unavailability

errors:
[]

failed_check_ids:
[]

failure_stage:
null

checkpoint signature_status:
verified

package signature_status:
verified

producer_code_imported:
false

verifier_implementation_relation:
separate_from_producer_code
```

The verifier performs exactly 49 declared checks.

The exact check-ID set covers:

```text
input regular-file and non-symlink boundary
carrier size
ZIP EOCD
member names
exact member set
regular member types
stored compression
fixed timestamps
CRC32
local/central consistency
absence of trailing data

manifest strict JSON
manifest canonical JSON
manifest schema
payload inventory
ledger binding
observer binding
signature contract

payload digests
payload sizes
canonicalization-contract binding
observation-contract binding
manifest-schema binding
signature-schema binding
ledger-schema binding

observer-key encoding
curve membership
fingerprint

ledger strict JSON
ledger canonical JSON
ledger schema
ledger identity
record digests
record chain
record sequence
session relations
coverage relations
event/endpoint bindings
transition relations
checkpoint closure

checkpoint-signature document
checkpoint-signature subject
checkpoint ECDSA equation

package-signature document
package-signature subject
package ECDSA equation

claim boundary
authority boundary
```

Report admission requires:

```text
report check count
=
49

report check keys
=
the exact fixed 49-check identifier set

every exact expected check value
=
passed
```

A missing required check cannot be replaced by an arbitrary successful key.

---

## 8. Positive reproduction proof

The positive proof is:

```text
Swift reference closure
→ Swift checkpoint signature
→ Swift canonical manifest
→ Swift package signature
→ Swift deterministic .pulseledger
→ separately implemented Python verifier process
→ exact canonical verifier report
```

The round-trip test requires:

```text
Swift-produced carrier bytes
=
checked-in reference carrier bytes

verifier process exit:
0

stderr:
empty

stdout:
exact checked-in canonical report bytes
```

The same carrier is verified twice.

Both executions must produce:

```text
identical process result
identical empty stderr
identical canonical stdout bytes
```

This proves that the reproduced result is determined by:

```text
exact carrier bytes
+
exact verifier implementation
```

not by generated time, temporary paths, process-local ordering, or a producer
verdict.

---

## 9. Relevant fail-closed proof

The negative proof does not corrupt the carrier randomly.

It creates a relevant mutation that preserves the ZIP structure long enough to
reach the package-signature equation.

The mutation:

```text
member:
signatures/package-signature-v0.json

first Base64 signature character:
O
→
P
```

The mutation helper recomputes and updates:

```text
local-file-header CRC32
central-directory CRC32
```

It preserves:

```text
carrier size
member order
member paths
member offsets
member sizes
manifest bytes
package-signature subject
ZIP structural admissibility
```

The same separately implemented verifier must return:

```text
process exit:
2

stderr:
empty

ok:
false

result:
rejected

failure_stage:
package_signature

failed_check_ids:
[
  "package_signature_valid"
]
```

The exact error is:

```text
stage:
package_signature

check_id:
package_signature_valid

error_code:
signature_verification_failed

member_path:
signatures/package-signature-v0.json
```

The preceding boundaries remain passed:

```text
zip_crc32_valid
package_signature_document_valid
package_signature_subject_valid
```

Only the package-signature equation fails.

This proves that:

```text
structurally admissible carrier
+
relevantly modified signature
→
fail-closed cryptographic rejection
```

---

## 10. Exact verifier-report identity

The canonical report is not admitted merely because selected decoded fields
look correct.

Before JSON decoding, the demonstrator runner requires:

```text
exact report byte count:
15328

exact report SHA-256:
5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4

opening byte:
{

closing byte:
}

UTF-8 BOM:
absent

CR:
absent

LF:
absent

trailing newline:
absent
```

Therefore, each of the following changes is rejected:

```text
key reordering
internal whitespace insertion
trailing whitespace
unknown-field modification
known-field modification
report substitution
outdated report substitution
```

The Xcode workflow also compares the repository report bytes with the report
copied into the built app bundle using exact byte comparison.

---

## 11. Same-carrier report binding in the iPhone demonstrator

The runnable iPhone demonstrator does not execute or import the Python verifier.

Its bounded relation is:

```text
current Swift-generated carrier
→ exact carrier digest, size, and member-count checks
→ exact pinned canonical verifier-report bytes
→ decoded report validation
→ report subject bound to the current carrier
→ read-only result surface
```

The app admits the report only when:

```text
report carrier filename
=
current carrier filename

report carrier size
=
current carrier size

report carrier SHA-256
=
current carrier SHA-256
```

The app therefore does not claim:

```text
the app verified itself
the UI created the proof result
a bundled text report is authoritative by presence alone
```

Instead:

```text
the separate verifier result already exists
+
the current run reproduces the exact carrier identity
+
the report is admitted only by exact byte identity
+
the report subject matches the current carrier
```

The app is a minimal runnable carrier of the already established proof.

---

## 12. Minimal runnable iPhone demonstrator

The runnable target is:

```text
apps/ios/PULSEmechProofApp/
```

It contains exactly:

```text
PULSEmechProofApp
PULSEmechProofAppTests
```

The app provides one read-only proof surface.

It displays:

```text
record count
session count
clock-epoch count
session-boundary count

continuous coverage count
interrupted coverage count
event-bound transition count
endpoint-difference-only transition count

checkpoint SHA-256
ledger SHA-256
manifest SHA-256
carrier SHA-256
carrier size

verifier result
verifier check count
verifier-bound carrier SHA-256
checkpoint-signature status
package-signature status
implementation-separation relation
producer-code-imported state

observer identity scope
key-origin profile
declared unavailability
authority effect
external-validation claim
```

A runner error produces a fail-closed error surface.

The app does not show a partial success state after a failed run.

---

## 13. Exact artifact export

The app exports:

```text
current result.carrierBytes
→ defensive Data copy
→ exact temporary file
→ system share/export surface
```

The export filename is fixed to:

```text
pulsemech_device_transition_ledger_reference_v0.pulseledger
```

The export path introduces no:

```text
ZIP reconstruction
alternate serialization
JSON conversion
Base64 conversion
text representation
artifact history
database persistence
cloud synchronization
publication action
release action
```

The exported source bytes are the same current `carrier.exactBytes` whose size
and SHA-256 appear on the read-only result surface.

---

## 14. Demonstrator workflow classification

The demonstrator workflow is:

```text
.github/workflows/pulsemech_ios_proof_app.yml
```

Its declared name is:

```text
PULSEmech iPhone Proof Demonstrator
```

The repository normative/shadow inventory classifies it as:

```text
carrier_class:
diagnostic_shadow

primary_role:
diagnostic / shadow workflow

release_path_participation:
false

required_gate_participation:
false
```

The workflow verifies:

```text
Xcode 16.4
macos-15 runner
closed two-target project boundary
shared scheme
available iPhone Simulator
Debug build
exact bundled-resource byte parity
three executable XCTest cases
Release build
tracked-file hygiene
```

This workflow does not participate in release authority.

---

## 15. Claim boundary

The proof and demonstrator explicitly do not claim:

```text
production Keychain origin
Secure Enclave origin
platform attestation
physical iPhone identity
hardware-backed production identity
device-security status
malware absence
continuous background monitoring
complete causal observation
external operator approval
external institutional validation
release decision
release-authority mutation
```

The admitted result requires:

```text
declared_unavailability_present:
true

authority_effect:
none

external_validation_claim:
none

changes_release_authority:
false

creates_release_decision:
false

creates_device_control_authority:
false

verifier_report_is_release_authority:
false
```

The successful result jointly requires:

```text
result:
verified_with_declared_unavailability

declared_unavailability_present:
true
```

A report that changes the declared-unavailability value to `false` is rejected
fail closed.

---

## 16. What is closed

The following bounded proof layers are complete:

```text
canonical Device Ledger record chain
terminal checkpoint closure
checkpoint-signature materialization
exact eight-member payload inventory
canonical manifest materialization
package-signature materialization
deterministic ten-member .pulseledger carrier
exact carrier identity
separately implemented verifier
positive Swift-to-verifier reproduction
repeated byte-deterministic reproduction
CRC-consistent relevant negative proof
exact canonical verifier-report identity
exact 49-check identifier admission
same-carrier report binding
minimal runnable iPhone proof surface
exact .pulseledger export
```

The closure status is:

```text
bounded mechanical self-proof:
closed

minimal runnable iPhone demonstrator:
closed

exact artifact export:
closed
```

---

## 17. What remains separate

The following work is not required by the bounded proof claim:

```text
general-purpose iPhone product development
live NWPathMonitor registration
production observation sessions
background monitoring
database storage
restart recovery
artifact history
full navigation
multiple proof flows
production Keychain lifecycle
Secure Enclave integration
platform attestation
physical-device identity
App Store qualification
external operator approval
external institutional certification
device-security verdict
release-decision integration
release-authority mutation
```

A later workstream may implement any of these under a new, explicitly wider
claim.

Their absence does not reopen the bounded mechanical proof recorded here.

---

## 18. Reproduction entrypoints

### Standalone verifier

```bash
python3 tools/verify_pulsemech_device_ledger_v0.py \
  examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger \
  --expected-observer-fingerprint \
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

Expected successful process state:

```text
exit status:
0

stderr:
empty

result:
verified_with_declared_unavailability

checks:
49 passed
```

### Swift package proof suite

```bash
cd apps/ios/Packages/PULSEmechLedgerCore

swift test \
  --configuration debug \
  --no-parallel \
  -j 1
```

Focused round-trip suite:

```bash
swift test \
  --configuration debug \
  --no-parallel \
  -j 1 \
  --filter SwiftPulseledgerVerifierRoundTripTests
```

### Runnable demonstrator

Open:

```text
apps/ios/PULSEmechProofApp/PULSEmechProofApp.xcodeproj
```

Run the shared scheme:

```text
PULSEmechProofApp
```

The demonstrator requires no external validating operator to create the result.

It executes the deterministic reference materialization, binds the exact
canonical verifier report to the current exact carrier, displays the bounded
result, and exports the exact carrier bytes.

---

## 19. Canonical source map

### Core implementation

- [`apps/ios/Packages/PULSEmechLedgerCore/`](../apps/ios/Packages/PULSEmechLedgerCore/)
- [`tools/verify_pulsemech_device_ledger_v0.py`](../tools/verify_pulsemech_device_ledger_v0.py)
- [`contracts/pulsemech_device_canonical_json_v0.json`](../contracts/pulsemech_device_canonical_json_v0.json)
- [`contracts/pulsemech_ios_observation_contract_v0.json`](../contracts/pulsemech_ios_observation_contract_v0.json)

### Schemas

- [`schemas/pulsemech_device_transition_ledger_v0.schema.json`](../schemas/pulsemech_device_transition_ledger_v0.schema.json)
- [`schemas/pulsemech_device_ledger_manifest_v0.schema.json`](../schemas/pulsemech_device_ledger_manifest_v0.schema.json)
- [`schemas/pulsemech_device_signature_v0.schema.json`](../schemas/pulsemech_device_signature_v0.schema.json)
- [`schemas/pulsemech_device_ledger_verification_report_v0.schema.json`](../schemas/pulsemech_device_ledger_verification_report_v0.schema.json)

### Reference artifacts

- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.json)
- [`examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json)
- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger)
- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json)

### Runnable demonstrator

- [`apps/ios/PULSEmechProofApp/`](../apps/ios/PULSEmechProofApp/)
- [`.github/workflows/pulsemech_ios_proof_app.yml`](../.github/workflows/pulsemech_ios_proof_app.yml)

---

## 20. Mechanical conclusion

The completed proof establishes:

```text
exact bounded relation
→ exact evidence chain
→ closed canonical ledger
→ checkpoint signature
→ canonical manifest
→ package signature
→ deterministic .pulseledger
→ separately implemented verifier reconstruction
→ reproducible PASS or fail-closed rejection
→ minimal runnable iPhone result surface
→ exact artifact export
```

The proof does not require a privileged external validating authority.

A third party may reproduce the result.

The third party does not create the result's truth value.

The exact artifact and the public verification mechanism carry that relation.

```text
bounded mechanical self-proof:
closed

minimal runnable iPhone bounded proof demonstrator:
closed

authority_effect:
none

external_validation_claim:
none

broader iPhone product development:
separate
```
