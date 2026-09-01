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

exact_pulseledger_export:
closed

reproduction_capsule_contract:
closed

deterministic_reproduction_execution:
closed

canonical_reproduction_result:
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
how the deterministic Reproduction Capsule preserves the proof inputs
how two isolated Capsule constructions reproduce identical bytes
how two separate verifier processes reproduce the exact positive result
how one targeted mutation reaches the package-signature equation and fails closed
which claims and authority effects remain explicitly absent
```

This document is a technical proof record.

This document does not create:

```text
a release decision
a release-authority carrier
a gate result
an external certification
an institutional approval
a device-security verdict
a production iPhone monitoring specification
a second verifier verdict
device-control authority
```

---

## Merged implementation identity

### Bounded Device Ledger and runnable demonstrator

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

The canonical bounded proof record was merged through:

```text
pull request:
#2848

squash-merge commit:
d2be905bbdf281cb4adff97b98618340d5ca5c39
```

Canonical references:

- [PR #2848](https://github.com/HKati/pulse-release-gates-0.1/pull/2848)
- [Merged commit `d2be905bbdf281cb4adff97b98618340d5ca5c39`](https://github.com/HKati/pulse-release-gates-0.1/commit/d2be905bbdf281cb4adff97b98618340d5ca5c39)

### Reproduction Capsule contract

The exact Reproduction Capsule contract was merged through:

```text
pull request:
#2851

squash-merge commit:
722fe4e85acfaac67c283862645ac9e42c831236

required base:
0108e2c0da98c8a1fe5e739aa0f137ba6a3464e1

reviewed final PR head:
20fe4fb3b14917962f523678a955ac264f5e5879
```

Canonical references:

- [PR #2851](https://github.com/HKati/pulse-release-gates-0.1/pull/2851)
- [Merged commit `722fe4e85acfaac67c283862645ac9e42c831236`](https://github.com/HKati/pulse-release-gates-0.1/commit/722fe4e85acfaac67c283862645ac9e42c831236)

PR #2851 established:

```text
strict Capsule-manifest schema
→ normative Capsule contract
→ exact canonical manifest instance
→ permanent contract regression
→ dedicated Capsule workflow
→ canonical tools-test registration
```

It defined the construction and reproduction contract without yet constructing
or executing the Capsule.

### Deterministic Reproduction Capsule execution

The deterministic Reproduction Capsule execution was merged through:

```text
pull request:
#2852

required base:
722fe4e85acfaac67c283862645ac9e42c831236

direct parent of squash merge:
0be4554c13c26d9dec887de5daaae6e9db920b61

reviewed final PR head:
5d8792ffb5c1f555b50f01bb34fa9757e20af5ec

squash-merge commit:
21837e1e54f898a131d3a9bff89527209ddae711

repository tree:
d6aada457cdbc4ffd7a1b969104f720ae83af55c
```

Canonical references:

- [PR #2852](https://github.com/HKati/pulse-release-gates-0.1/pull/2852)
- [Merged commit `21837e1e54f898a131d3a9bff89527209ddae711`](https://github.com/HKati/pulse-release-gates-0.1/commit/21837e1e54f898a131d3a9bff89527209ddae711)

The completed PR #2852 relation is:

```text
one exact canonical .pulseledger
+
one exact Capsule manifest contract
+
the existing standalone verifier unchanged
→
one exact positive reproduction
+
a second byte-identical Capsule construction
+
one targeted fail-closed package-signature mutation rejection
```

The final automated PR state recorded:

```text
successful checks:
28

conditionally skipped checks:
6

failed checks:
0

Codex final-head review:
no major issues found

review conversations:
resolved

merge conflicts:
none
```

The Reproduction Capsule work changed no:

```text
Device Ledger evidence semantics
canonical JSON semantics
signature semantics
.pulseledger format
standalone-verifier semantics
release policy
required gate set
status.json
strict terminal gate checker
release decision
release authority
DOI
Zenodo metadata or record relationship
CITATION.cff
Git tag
GitHub Release
```

---

## 1. Exact mechanical claim

The bounded claim is:

> PULSEmech can create an exact, closed artifact from a declared bounded
> relation, and a separately implemented verifier can reconstruct the result
> from the artifact bytes without relying on a privileged external validating
> authority.

The complete proof relation is:

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
→ deterministic four-member Reproduction Capsule
→ second isolated byte-identical Capsule construction
→ two exact positive separate-process verifier reproductions
→ one targeted package-signature mutation
→ exact fail-closed cryptographic rejection
→ canonical machine-readable reproduction result
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

The source of mechanical validity is not:

```text
developer assertion
+
external expert opinion
+
institutional approval
```

The Reproduction Capsule adds a portable, deterministic carrier around the
already closed bounded proof.

It does not replace the proof object, the standalone verifier, or the verifier
report.

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

reproduction runner
≠
verifier

reproduction result
≠
verifier verdict
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

Any person or organization may run the verifier or the Reproduction Capsule
workflow.

Such a run is a new reproduction event.

The identity, title, rank, affiliation, reputation, or institutional authority
of the operator is not part of the verification equation and is not a
prerequisite of the proof.

The operator does not make the artifact valid.

The artifact, declared contracts, and verifier relation determine the result.

---

## 3. Implemented proof layers

| Layer | Repository path | Mechanical role |
|---|---|---|
| Device Ledger core | `apps/ios/Packages/PULSEmechLedgerCore/` | Produces the bounded ledger, checkpoint, signatures, manifest, and deterministic `.pulseledger` |
| Canonicalization contract | `contracts/pulsemech_device_canonical_json_v0.json` | Declares the canonical JSON profile |
| Observation contract | `contracts/pulsemech_ios_observation_contract_v0.json` | Declares the bounded iOS observation semantics |
| Device Ledger schemas | `schemas/pulsemech_device_*_v0.schema.json` | Define ledger, manifest, signature, and verifier-report structures |
| Reference carrier | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger` | Carries the exact ten-member Device Ledger proof package |
| Canonical verifier report | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json` | Records the exact separate-verifier result |
| Standalone verifier | `tools/verify_pulsemech_device_ledger_v0.py` | Reconstructs the proof from exact carrier bytes |
| Swift-to-verifier round trip | `SwiftPulseledgerVerifierRoundTripTests.swift` | Proves positive reproduction, determinism, and relevant fail-closed rejection |
| Runnable iPhone demonstrator | `apps/ios/PULSEmechProofApp/` | Executes deterministic reference materialization, displays exact identities, and exports the exact carrier |
| Demonstrator workflow | `.github/workflows/pulsemech_ios_proof_app.yml` | Builds and tests the app as a non-authorizing diagnostic/shadow surface |
| Capsule-manifest schema | `schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json` | Defines the exact four-member Capsule manifest |
| Normative Capsule contract | `contracts/pulsemech_device_ledger_reproduction_capsule_v0.json` | Fixes archive, input, execution, positive, negative, claim, and authority relations |
| Canonical Capsule manifest | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json` | Carries the exact acyclic Capsule construction contract instance |
| Capsule builder | `tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py` | Constructs the exact four-member deterministic ZIP without becoming a verifier |
| Reproduction-result schema | `schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json` | Accepts only the complete bounded reproduction relation |
| Reproduction runner | `tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py` | Orchestrates two constructions, two positive verifier processes, one negative process, and exact output publication |
| Canonical Reproduction Capsule | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip` | Carries exact copies of the manifest, `.pulseledger`, verifier, and expected report |
| Canonical reproduction result | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json` | Records deterministic orchestration evidence outside the Capsule |
| Contract regression | `tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py` | Permanently checks the PR #2851 contract surface |
| Execution regression | `tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py` | Permanently reconstructs and checks the PR #2852 execution relation |
| Dedicated Capsule workflow | `.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml` | Executes the exact reference environment and transports exact outputs without authority effect |

---

## 4. Bounded reference relation

The runnable demonstrator and Reproduction Capsule use the established
deterministic synthetic reference relation:

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

They are not independently supplied UI or reproduction-runner assertions.

### Reference-status boundary

The implemented reference uses:

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256
```

Therefore, this proof demonstrates the complete bounded artifact,
reconstruction, display, export, and deterministic Capsule-reproduction
mechanism.

It does not claim:

```text
a live production iPhone observation session
a production installation identity
a hardware-backed production key
a physical-device attestation
a physical measurement
universal cross-platform reproducibility
production readiness
```

---

## 5. Exact Device Ledger artifact identities

A successful Device Ledger reference materialization must produce these exact
identities:

| Object | Exact identity |
|---|---|
| Terminal checkpoint SHA-256 | `16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff` |
| Canonical ledger SHA-256 | `360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77` |
| Canonical manifest SHA-256 | `47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1` |
| `.pulseledger` size | `133568` bytes |
| `.pulseledger` SHA-256 | `a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3` |
| `.pulseledger` member count | `10` |
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

The `.pulseledger` contains exactly ten stored regular-file members in a fixed
order.

Its construction binds:

```text
eight exact payload members
+
canonical manifest
+
canonical package-signature document
→
deterministic bounded ZIP carrier
→
exact .pulseledger bytes
→
carrier SHA-256
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

## 7. Separately implemented standalone verifier

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

## 8. Base positive reproduction proof

The base positive proof is:

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

It does not depend on generated time, temporary paths, process-local ordering,
a producer verdict, or operator identity.

---

## 9. Base relevant fail-closed proof

The base negative proof does not corrupt the carrier randomly.

It creates a relevant mutation that preserves the ZIP structure long enough to
reach the package-signature equation.

The mutation is:

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

This proves:

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

Before JSON decoding, the demonstrator runner and the Reproduction Capsule
relation require:

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

The Xcode workflow compares the repository report bytes with the report copied
into the built app bundle using exact byte comparison.

The Reproduction Capsule carries an exact copy of the same report and compares
each separate verifier stdout byte sequence with it after verifier execution.

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

The app makes no claim that:

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

## 13. Exact artifact export and demonstrator workflow

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

## 14. Reproduction Capsule contract

The Reproduction Capsule contract fixes one acyclic identity relation:

```text
Capsule-manifest schema
→ normative Capsule contract
→ canonical Capsule manifest
→ deterministic Capsule construction
→ external canonical reproduction result
```

The manifest binds:

```text
format identity
canonical source identity
payload-member roles
payload-member paths
payload byte sizes
payload SHA-256 identities
deterministic archive profile
expected observer fingerprint
positive-result contract
repeated-construction contract
negative-mutation contract
claim boundary
implementation boundary
authority boundary
```

The manifest does not bind:

```text
its own SHA-256
its own byte size
the final Capsule SHA-256
the final Capsule byte size
its containing Git commit
a workflow-run identity
a generated timestamp
```

The final Capsule identity is carried outside the Capsule by the canonical
reproduction result.

### Exact PR #2851 contract identities

| Object | Size | SHA-256 | Git blob SHA-1 |
|---|---:|---|---|
| Capsule-manifest schema | `32581` bytes | `a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c` | `6a0dabff2e5f725c6ef8e586f9cae7fff566030b` |
| Normative Capsule contract | `15947` bytes | `ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67` | `d15fddbe9250de0ed76b3b7ebb7d679383a867b4` |
| Canonical Capsule manifest | `8989` bytes | `cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf` | `b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b` |

The canonical manifest is exact Device Canonical JSON:

```text
UTF-8 BOM:
absent

CR characters:
0

LF characters:
0

trailing newline:
absent
```

### Exact protected payload identities

The contract binds the exact existing payloads:

| Object | Size | SHA-256 |
|---|---:|---|
| Canonical `.pulseledger` | `133568` bytes | `a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3` |
| Standalone verifier | `126419` bytes | `0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7` |
| Canonical positive verifier report | `15328` bytes | `5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4` |
| Device Canonical JSON contract | `2719` bytes | `ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550` |

The expected observer fingerprint is:

```text
f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

Any mismatch against these exact inputs is terminal.

---

## 15. Deterministic Capsule archive profile

The Reproduction Capsule is a bounded four-member ZIP archive.

The exact member order is:

```text
1.
manifest/
pulsemech_device_ledger_reproduction_capsule_manifest_v0.json

2.
artifact/
pulsemech_device_transition_ledger_reference_v0.pulseledger

3.
verifier/
verify_pulsemech_device_ledger_v0.py

4.
expected/
pulsemech_device_transition_ledger_reference_verification_v0.json
```

The fixed archive profile is:

```text
archive format:
zip

compression:
ZIP_STORED

compression method code:
0

member order:
exact sequence

member timestamp:
1980-01-01 00:00:00

creator system:
3

creator version:
20

local-header version needed:
20

central-directory version needed:
20

central-directory version made by:
788

regular-file mode:
0644

external attributes:
2175008768

internal attributes:
0

general-purpose flags:
0

extra fields:
empty

member comments:
empty

archive comment:
empty

directory entries:
forbidden

data descriptors:
forbidden

encryption:
forbidden

duplicate names:
forbidden

ZIP64:
forbidden

trailing data:
forbidden

CRC32:
computed from exact member bytes
```

The Capsule carries exact source bytes.

The builder does not rewrite, normalize, regenerate, reformat, or substitute
semantically equivalent payloads.

---

## 16. Capsule builder and reproduction runner

### Capsule builder

The deterministic builder is:

```text
tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py
```

Its exact merged identity is:

```text
size:
79156 bytes

SHA-256:
1a5c48aa63eb7d74235741ff738d4f08a245096f71a76057a22b88036036e1d0

Git blob SHA-1:
22fa939d7bd9706a654fbb8893ef0c06ef4e160b
```

The builder:

```text
verifies every exact input before construction
rejects symlinks
rejects unacceptable hard-link state
uses only fixed member paths
uses one fixed member order
uses one fixed archive profile
uses ZIP_STORED
writes transactionally
does not replace an existing output
preserves canonical repository sources
operates without network access
```

The builder does not:

```text
import verifier internals
execute signature verification
construct a verifier verdict
trust a producer verdict
create a release decision
create authority
```

### Reproduction-result schema

The strict reproduction-result schema is:

```text
schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json
```

Its exact merged identity is:

```text
size:
71112 bytes

SHA-256:
c6ff62b7c6af008ae7e15bec69452d6860dfa16c0e8a1345ce843d8713c02af7

Git blob SHA-1:
7c9e68a48e79551c2929c56bdfc907ffa67d2992
```

The schema accepts only the complete bounded reproduction relation.

It rejects:

```text
partial success
warning-only success
best-effort success
substituted verification
producer-verdict trust
an earlier negative failure
source drift
unverified reference-image identity
network-enabled reproduction
volatile result fields
authority expansion
```

### Reproduction runner

The orchestration runner is:

```text
tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py
```

Its exact merged identity is:

```text
size:
123414 bytes

SHA-256:
ffd3b9604334587030a89f20952e65417f83036161634755c6541435c5d20104

Git blob SHA-1:
e9f58f9a08344b6b2dce698a25834909ecdc082a
```

The runner:

```text
constructs Capsule A in one isolated workspace and process
constructs Capsule B in a second isolated workspace and process
requires exact A/B byte equality
materializes only the fixed known payload members
executes the unchanged standalone verifier as separate processes
captures stdout and stderr as exact bytes
compares each positive stdout with the canonical report bytes
creates one isolated targeted package-signature mutation
repairs local-header and central-directory CRC32
requires the exact package_signature_valid rejection
revalidates protected sources
validates and canonically renders the reproduction result
publishes the Capsule and result transactionally
```

The runner does not:

```text
import verifier internals
call verifier functions in-process
reimplement signature verification
reimplement Device Ledger manifest verification
reimplement Device Canonical JSON verification
construct an alternative verifier verdict
trust the expected report as a producer verdict
modify repository source objects
```

The implementation relation is:

```text
builder
≠
runner
≠
standalone verifier
```

---

## 17. Exact reference environment

The canonical reference execution is bound to:

```text
container image:
docker.io/library/python:3.11.9-slim-bookworm@sha256:
2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050

container platform:
linux/amd64

architecture relation:
amd64 / x86_64

distribution:
Debian

operating-system family:
Bookworm slim image

Python implementation:
CPython

Python version:
3.11.9

Unicode data version:
14.0.0

dependency policy:
Python standard library only during reproduction

network access during bounded execution:
none

runtime downloads:
none

package installation during bounded execution:
none
```

Required environment values are:

```text
LANG:
C.UTF-8

LC_ALL:
C.UTF-8

TZ:
UTC

PYTHONDONTWRITEBYTECODE:
1

PYTHONHASHSEED:
0
```

The outer launcher:

```text
pulls the exact digest-pinned image before the bounded phase
→ verifies the host container runtime RepoDigest
→ creates an exact reference-environment attestation
→ launches by exact image digest
→ disables network access
→ mounts the repository read-only
→ mounts the attestation read-only
→ mounts a separate writable output directory
```

The exact outer-launcher attestation identity is:

```text
size:
843 bytes

SHA-256:
9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca
```

The bounded container uses:

```text
read-only container root
dropped capabilities
no-new-privileges
PID limit
read-only repository mount
read-only attestation mount
separate writable output mount
bounded tmpfs
network mode none
```

The builder and runner cannot independently prove the host runtime image
RepoDigest.

The exact outer-launcher attestation supplies that precondition.

---

## 18. Two isolated byte-identical Capsule constructions

The runner creates two independent constructions:

```text
Capsule A
→ construction process A
→ isolated workspace A
→ output A

Capsule B
→ construction process B
→ isolated workspace B
→ output B
```

Capsule B does not reuse:

```text
Capsule A output
Capsule A temporary files
Capsule A materialized members
Capsule A computed archive bytes
```

The required and completed relation is:

```text
Capsule A bytes
=
Capsule B bytes
=
checked-in canonical Capsule bytes
```

The runner and permanent regression require:

```text
Capsule A byte count
=
Capsule B byte count

SHA-256(Capsule A)
=
SHA-256(Capsule B)

Capsule A member inventory
=
Capsule B member inventory

Capsule A member order
=
Capsule B member order

every Capsule A member byte sequence
=
the corresponding Capsule B member byte sequence
```

The canonical Capsule identity is:

```text
path:
examples/device_transition_ledger/
pulsemech_device_ledger_reproduction_capsule_v0.zip

size:
285144 bytes

SHA-256:
49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678

Git blob SHA-1:
5b2647823e59bde24cf9125851c1490e3149dfab
```

Two textual `PASS` strings without byte-identical Capsule construction do not
satisfy this proof.

---

## 19. Two exact positive Capsule reproductions

The standalone verifier is executed against the positive `.pulseledger`
materialized from each independently constructed Capsule.

For both positive processes:

```text
exit status:
0

stderr:
empty

stdout size:
15328 bytes

stdout SHA-256:
5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4

ok:
true

result:
verified_with_declared_unavailability

failed_check_ids:
[]

failure_stage:
null

checkpoint signature:
verified

package signature:
verified

passed checks:
49

check count:
49

producer_code_imported:
false

producer_verdict_trusted:
false

verifier_implementation_relation:
separate_from_producer_code
```

The exact output relation is:

```text
positive verifier stdout A bytes
=
positive verifier stdout B bytes
=
canonical expected verifier-report bytes
```

Parsed JSON equivalence alone is insufficient.

The expected report is compared only after the standalone verifier has executed
as a separate process.

The expected report is not trusted as a producer verdict.

---

## 20. Targeted Capsule negative reproduction

The targeted mutation operates only on an isolated temporary copy of the
canonical `.pulseledger` materialized from Capsule A.

The checked-in canonical `.pulseledger`, Capsule A, Capsule B, and every
repository source object remain unchanged.

The mutation target is:

```text
Capsule member:
artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger

inner member:
signatures/package-signature-v0.json

field:
signature_base64

mutation:
first character O → P
```

The mutation recomputes:

```text
local-file-header CRC32
central-directory CRC32
```

The mutated carrier preserves:

```text
valid ZIP structure
same total byte size
same member count
same member order
same member names
matching CRC32 fields
canonical package-signature JSON structure
unchanged package-signature subject
unchanged manifest binding
unchanged non-target member bytes
```

The exact mutated carrier identity is:

```text
size:
133568 bytes

SHA-256:
4712365d309df49bc42e5cb73d98e37f2bbfc98ef7522b87320612d106157cab
```

The existing standalone verifier reaches package-signature cryptographic
verification.

The required preceding checks pass:

```text
zip_crc32_valid
package_signature_document_valid
package_signature_subject_valid
```

The exact negative process result is:

```text
exit status:
2

stderr:
empty

stdout size:
15352 bytes

stdout SHA-256:
b701c06c9b6836689f86c6983a4b4723f8524fbf0d4065e47a41c4cbabec65fd

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

check_id:
package_signature_valid

error_code:
signature_verification_failed

member_path:
signatures/package-signature-v0.json
```

An earlier ZIP, CRC, JSON, inventory, subject, or manifest failure does not
satisfy this proof.

---

## 21. Canonical reproduction result

The canonical reproduction result is:

```text
path:
examples/device_transition_ledger/
pulsemech_device_ledger_reproduction_result_reference_v0.json

size:
31188 bytes

SHA-256:
d0a659c572dcde11315f518d350361f6fc7690027c7e2682111f88a519b34ad1

Git blob SHA-1:
9b5a240495b357c64a510e6019e4d7189c29152e
```

Its exact byte profile is:

```text
UTF-8 BOM:
absent

CR characters:
0

LF characters:
0

trailing newline:
absent

canonical reserialization:
exact match

schema validation:
PASS
```

The result records:

```text
manifest-contract identity
canonical input identities
builder identity
runner identity
result-schema identity
reference-environment precondition
outer-launcher attestation identity
Capsule A identity
Capsule B identity
canonical Capsule identity
byte-identical construction result
positive verifier process A
positive verifier process B
positive verifier-report identities
targeted mutation identity
negative verifier process
exact failure stage
exact failed-check set
protected-source before/after identities
implementation boundary
claim boundary
authority boundary
```

The result contains no generated timestamp, workflow-run ID, hostname, username,
random identifier, machine-local absolute path, or temporary-directory name.

The result is:

```text
orchestration evidence
```

The result is not:

```text
a second verifier verdict
a replacement for the standalone verifier report
a producer verdict
a gate result
a release decision
release authority
```

---

## 22. Protected-source preservation

The reproduction runner protects ten exact repository source objects:

```text
Capsule-manifest schema
normative Capsule contract
canonical Capsule manifest
Device Canonical JSON contract
canonical .pulseledger
standalone verifier
canonical positive verifier report
Capsule builder
reproduction runner
reproduction-result schema
```

Before and after the complete reproduction relation, the runner requires:

```text
all exact bytes unchanged:
true

all Git blob identities unchanged:
true

drift detected:
false

repository source write attempted:
false

protected source count:
10
```

The outer reference-environment attestation is separately bound and must remain
unchanged throughout the bounded execution.

Any protected-source drift fails closed before successful publication.

The runner never overwrites:

```text
canonical source artifacts
standalone verifier
canonical expected report
contract or schema objects
builder or runner source
repository source files
an existing output directory
```

---

## 23. Permanent regressions and workflow proof

### Contract regression

The PR #2851 contract regression is:

```text
tests/
test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py
```

It verifies the exact contract, schema, manifest, archive, environment, positive,
negative, implementation, claim, and authority surfaces.

### Execution regression

The PR #2852 execution regression is:

```text
tests/
test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py
```

Its exact identity is:

```text
size:
55793 bytes

line count:
1500

SHA-256:
312e2e2465e7fbefb33d7943329920d1dbb32572acde9bfb386a22bfc423e4dc

Git blob SHA-1:
a1a343dfd8de4d6e12c079a8f0358b652d195c87
```

The execution regression contains 15 tests.

It independently:

```text
reconstructs Capsule A
reconstructs Capsule B
requires exact Capsule equality
executes two positive verifier processes
compares exact canonical stdout bytes
creates and validates the targeted mutation
executes the exact negative verifier process
validates the canonical reproduction result
rejects forbidden result variants
checks implementation separation
checks claim boundaries
checks authority boundaries
```

Its no-argument launcher removes inherited pytest-control variables, disables
plugin autoload and external configuration influence, and requires every
collected test to produce an ordinary passing call report.

The launcher rejects:

```text
collection-only success
deselection
skipped proof execution
xfail
xpass
premature pytest success
external plugin injection
external conftest influence
```

The execution regression is registered exactly once in:

```text
ci/tools-tests.list
```

The merged tools-test cardinality is:

```text
149 active entries
149 unique active entries
```

### Dedicated reference workflow

The dedicated workflow is:

```text
.github/workflows/
pulsemech_device_ledger_reproduction_capsule_v0.yml
```

Its declared name is:

```text
PULSEmech Device Ledger Reproduction Capsule v0
```

It preserves two distinct jobs:

```text
Capsule contract regression
→ repository CI contract checks

Capsule reference execution bootstrap
→ exact reference-environment proof execution
```

The proof output is uploaded under:

```text
artifact name:
pulsemech-device-ledger-reproduction-bootstrap-v0
```

The transported artifact contains:

```text
pulsemech_device_ledger_reproduction_capsule_v0.zip

pulsemech_device_ledger_reproduction_result_reference_v0.json

pulsemech_reference_environment_attestation_v0.json

pulsemech_device_ledger_reproduction_runner_summary_v0.jsonl
```

Artifact transport does not change the proof identities and does not create
authority.

---

## 24. Implementation, claim, and authority boundaries

### Implementation boundary

The canonical reproduction result requires:

```text
existing_verifier_modification:
forbidden

new_verifier:
none

producer_verdict_trusted:
false

reproduction_result_role:
orchestration_evidence_not_verifier_verdict

runner_role:
orchestration_only

verification_semantics_change:
none

verifier_execution:
separate_process

verifier_import_by_runner:
forbidden
```

### Claim boundary

The reference and Reproduction Capsule require:

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256

causal_completion_claim:
none

continuous_monitoring_claim:
none

device_security_claim:
none

external_validation_claim:
none

hardware_backed_identity_claim:
none

live_observation_claim:
none

malware_claim:
none

physical_measurement_claim:
none

production_device_claim:
none

production_readiness_claim:
none

universal_cross_platform_reproducibility_claim:
none
```

The pinned reference environment proves the exact recorded reference execution.

It does not silently expand into a universal cross-platform claim.

### Authority boundary

The canonical reproduction result requires:

```text
authority_effect:
none

capsule_is_release_authority:
false

changes_release_authority:
false

creates_device_control_authority:
false

creates_gate_result:
false

creates_release_decision:
false

external_operator_approval_required:
false

reproduction_result_is_release_authority:
false
```

The underlying Device Ledger verifier report also requires:

```text
verifier_report_is_release_authority:
false
```

Therefore:

```text
successful reproduction
≠
release approval

successful reproduction
≠
device-control authority

external execution
≠
external validation authority

workflow artifact
≠
authority carrier
```

---

## 25. What is closed

The following bounded proof layers are complete:

```text
canonical Device Ledger record chain
terminal checkpoint closure
checkpoint-signature materialization
exact eight-member payload inventory
canonical manifest materialization
package-signature materialization
deterministic ten-member .pulseledger carrier
exact .pulseledger identity
separately implemented verifier
positive Swift-to-verifier reproduction
repeated byte-deterministic verifier reproduction
CRC-consistent relevant negative proof
exact canonical verifier-report identity
exact 49-check identifier admission
same-carrier report binding
minimal runnable iPhone proof surface
exact .pulseledger export

strict Reproduction Capsule manifest schema
normative Reproduction Capsule contract
canonical Capsule manifest
fixed four-member ZIP profile
deterministic Capsule builder
strict reproduction-result schema
orchestration-only reproduction runner
exact reference-environment precondition
exact outer-launcher attestation
Capsule A isolated construction
Capsule B isolated construction
Capsule A/B byte identity
canonical Capsule identity
two exact positive verifier processes
targeted CRC-consistent package-signature mutation
exact package_signature_valid rejection
canonical machine-readable reproduction result
protected-source before/after preservation
permanent contract regression
permanent execution regression
dedicated reference workflow
```

The closure status is:

```text
bounded mechanical self-proof:
closed

minimal runnable iPhone demonstrator:
closed

exact artifact export:
closed

Reproduction Capsule contract:
closed

deterministic reference execution:
closed

canonical reproduction result:
closed
```

---

## 26. What remains separate

The following work is not required by the bounded proof or Reproduction Capsule
claim:

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
hardware-backed production identity
App Store qualification
external operator approval
external institutional certification
device-security verdict
malware-absence verdict
complete causal observation
universal cross-platform reproduction
release-decision integration
release-authority mutation
policy activation
new required gates
```

A later workstream may implement any of these under a new, explicitly wider
claim.

Their absence does not reopen the bounded proof or the deterministic
Reproduction Capsule closure recorded here.

---

## 27. Reproduction entrypoints

The entrypoints have distinct roles.

```text
standalone verifier
→ verifies one exact .pulseledger

Swift proof suite
→ reproduces the Swift-to-verifier relation

portable local execution regression
→ reconstructs and checks the complete Capsule proof using the current host

canonical reference workflow
→ executes the complete proof in the exact pinned reference environment

inner reproduction runner
→ bounded workflow phase requiring an exact outer-launcher attestation

iPhone demonstrator
→ displays and exports the already established bounded proof
```

### Canonical reference-environment reproduction

The complete canonical operator entrypoint is the manually dispatchable
dedicated workflow.

With GitHub CLI:

```bash
gh workflow run \
  pulsemech_device_ledger_reproduction_capsule_v0.yml \
  --repo HKati/pulse-release-gates-0.1 \
  --ref main
```

This is a one-command dispatch of:

```text
exact contract regression
→ exact image pull
→ host-runtime RepoDigest verification
→ exact outer-launcher attestation
→ exact-digest container launch
→ no-network bounded execution
→ two Capsule constructions
→ two positive verifier processes
→ targeted negative verifier process
→ exact output verification
→ workflow-artifact transport
```

The workflow dispatch is asynchronous.

The completed workflow run exposes the exact proof outputs through:

```text
pulsemech-device-ledger-reproduction-bootstrap-v0
```

The workflow creates no release decision or authority.

### Portable local proof replay

From the repository root:

```bash
python3 \
  tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py
```

The no-argument launcher executes the sanitized 15-test permanent regression.

This command checks:

```text
two deterministic Capsule constructions
exact A/B/canonical Capsule equality
two separate positive verifier executions
exact canonical report bytes
targeted package-signature mutation
exact fail-closed rejection
canonical reproduction-result structure
implementation, claim, and authority boundaries
```

This is the portable local regression entrypoint.

It does not claim the pinned container-image precondition unless it is run
through the dedicated reference workflow.

### Inner bounded runner

The dedicated workflow invokes the runner inside the exact reference container:

```bash
python3 -P \
  tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py \
  --repository-root /repo \
  --output-directory /output/reference-proof \
  --reference-environment-attestation \
    /attestation/reference_environment_attestation_v0.json
```

This is an inner bounded execution command.

It is not a complete bare-host reference-environment command because the outer
launcher must first verify the image RepoDigest, create the exact attestation,
disable the network, and establish the read-only and writable mounts.

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

It executes deterministic reference materialization, binds the exact canonical
verifier report to the current exact carrier, displays the bounded result, and
exports the exact carrier bytes.

---

## 28. Canonical source map

### Core implementation

- [`apps/ios/Packages/PULSEmechLedgerCore/`](../apps/ios/Packages/PULSEmechLedgerCore/)
- [`tools/verify_pulsemech_device_ledger_v0.py`](../tools/verify_pulsemech_device_ledger_v0.py)
- [`contracts/pulsemech_device_canonical_json_v0.json`](../contracts/pulsemech_device_canonical_json_v0.json)
- [`contracts/pulsemech_ios_observation_contract_v0.json`](../contracts/pulsemech_ios_observation_contract_v0.json)

### Device Ledger schemas

- [`schemas/pulsemech_device_transition_ledger_v0.schema.json`](../schemas/pulsemech_device_transition_ledger_v0.schema.json)
- [`schemas/pulsemech_device_ledger_manifest_v0.schema.json`](../schemas/pulsemech_device_ledger_manifest_v0.schema.json)
- [`schemas/pulsemech_device_signature_v0.schema.json`](../schemas/pulsemech_device_signature_v0.schema.json)
- [`schemas/pulsemech_device_ledger_verification_report_v0.schema.json`](../schemas/pulsemech_device_ledger_verification_report_v0.schema.json)

### Device Ledger reference artifacts

- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.json)
- [`examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json)
- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger)
- [`examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json)

### Reproduction Capsule contract

- [`schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json`](../schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json)
- [`contracts/pulsemech_device_ledger_reproduction_capsule_v0.json`](../contracts/pulsemech_device_ledger_reproduction_capsule_v0.json)
- [`examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json)
- [`tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py`](../tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py)

### Reproduction Capsule execution

- [`tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py`](../tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [`schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json`](../schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json)
- [`tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py`](../tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [`examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip)
- [`examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json)
- [`tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py`](../tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py)
- [`.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml`](../.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml)
- [`ci/tools-tests.list`](../ci/tools-tests.list)

### Runnable demonstrator

- [`apps/ios/PULSEmechProofApp/`](../apps/ios/PULSEmechProofApp/)
- [`.github/workflows/pulsemech_ios_proof_app.yml`](../.github/workflows/pulsemech_ios_proof_app.yml)

---

## 29. Mechanical conclusion

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
→ exact four-member Reproduction Capsule contract
→ deterministic Capsule A
→ isolated deterministic Capsule B
→ exact A/B/canonical Capsule byte identity
→ two exact positive standalone-verifier reproductions
→ one targeted CRC-consistent package-signature mutation
→ exact package_signature_valid rejection
→ canonical orchestration-evidence result
```

The proof does not require a privileged external validating authority.

A third party may reproduce the result.

The third party does not create the result's truth value.

The exact artifact, declared contracts, and public verification mechanism carry
that relation.

```text
bounded mechanical self-proof:
closed

minimal runnable iPhone bounded proof demonstrator:
closed

exact .pulseledger export:
closed

Reproduction Capsule contract:
closed

deterministic reference execution:
closed

canonical reproduction result:
closed

reproduction result role:
orchestration_evidence_not_verifier_verdict

authority_effect:
none

external_validation_claim:
none

broader iPhone product development:
separate
```
