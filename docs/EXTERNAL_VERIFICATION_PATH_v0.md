# External Verification Path v0

## Purpose

External Verification Path v0 defines how an external reviewer can inspect,
replay, and reproduce recorded PULSEmech artifact relations without becoming
part of the authority path carried by those relations.

The document covers three distinct subjects:

```text
PULSEmech release-authority artifact relation

PULSEmech Device Ledger exact .pulseledger verification relation

PULSEmech Device Ledger Reproduction Capsule v0 relation
```

The release-authority profile makes the downstream decision-bearing relation
externally readable and mechanically reviewable through:

```text
recorded artifacts
+ declared policy
+ workflow-effective materialized required gates
+ exact verifier and binding state
+ strict terminal CI enforcement
```

The Device Ledger direct-verification profile records:

```text
exact .pulseledger
→ separately implemented standalone verifier
→ exact canonical PASS or fail-closed rejection
```

The Device Ledger Reproduction Capsule profile records the wider portable
reproduction relation:

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

These profiles make exact recorded relations available for external inspection
and reproduction.

They do not make an external person, organization, institution, reviewer, or
operator an input to the proof equation.

The canonical Device Ledger proof record is:

[PULSEmech Device Ledger Bounded Mechanical Proof v0](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)

---

## 1. Verification boundary

External verification is a review or reproduction carrier.

It may:

```text
locate exact subjects
verify repository and commit identity
verify artifact size and digest identity
replay declared validators and verifiers
reconstruct policy-derived relations
execute bounded reproduction commands
compare exact canonical outputs
record mismatches and residual uncertainty
```

It does not independently create:

```text
a release decision
a release-authority function
a device-control decision
a new verifier verdict
a replacement truth source
a required institutional approval
```

An external execution is an optional new reproduction event.

It can add evidence that the same exact inputs, implementation, and declared
execution boundary reproduce the same result.

The already recorded mechanical validity does not depend on that event.

The operator remains outside the verification equation:

```text
operator identity
≠
verification input

operator organization
≠
artifact identity

institutional status
≠
truth value

external reproduction event
≠
source of mechanical validity

separately implemented verifier
≠
external validating authority
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

For the Reproduction Capsule closure, the complete portable relation is carried
by:

```text
exact contract objects
+
exact protected payloads
+
deterministic Capsule construction
+
two isolated construction records
+
two exact positive verifier executions
+
one exact targeted negative execution
+
canonical orchestration evidence
```

Neither relation depends on:

```text
developer assertion
+
external expert opinion
+
institutional approval
```

---

## 2. Subject separation

The three profiles have different subjects.

### Release-authority subject

```text
one exact release run
+
one exact declared policy
+
one workflow-effective required-gate set
+
one final recorded state
+
one strict CI terminal result
```

### Device Ledger direct-verification subject

```text
one exact .pulseledger carrier
+
one exact standalone-verifier implementation
+
one expected observer fingerprint
```

### Device Ledger Reproduction Capsule subject

```text
one exact Capsule contract surface
+
one exact protected payload set
+
one exact reference-environment relation
+
one complete reproduction execution
+
one canonical reproduction result
```

The canonical reproduction result is an orchestration-evidence subject.

It records that the builder, runner, standalone verifier, positive executions,
negative execution, and protected-source relation completed as declared.

It does not replace the standalone verifier report.

The subject identity determines the meaning of every external review result.

A release-authority finding cannot silently rewrite a Device Ledger verifier
result.

A Device Ledger reproduction cannot silently create a release decision.

A reader or report status cannot silently become authority.

---

## 3. Carrier roles

| Carrier | Artifact / path | Mechanical role |
|---|---|---|
| Release-authority carrier | `status.json` → declared gate policy → workflow-effective materialized required-gate set → strict fail-closed CI enforcement | Carries the terminal release-authority relation |
| Binding carrier | `artifact_provenance_binding_v0.json` | Carries digest-backed release artifact relations |
| Binding verifier | `PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py` | Recomputes and verifies the binding carrier |
| Reader carrier | Quality Ledger | Presents selected recorded state |
| Trace carrier | release-authority manifest / release-decision artifact | Preserves reconstruction and decision trace |
| Release attestation subject | `artifact_provenance_binding_v0.json` | Compact cryptographic attestation subject for the recorded release-artifact relation |
| External verification carrier | reviewer checklist / reproduction commands / verification packet | Reviews or replays a recorded relation |
| Device Ledger bounded proof carrier | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger` | Carries the exact ten-member bounded Device Ledger proof subject |
| Device Ledger standalone verifier | `tools/verify_pulsemech_device_ledger_v0.py` | Reconstructs the Device Ledger result from exact carrier bytes |
| Canonical Device Ledger verifier report | `examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json` | Carries the exact standalone-verifier result for the canonical `.pulseledger` |
| Reproduction Capsule manifest schema | `schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json` | Defines the strict Capsule-manifest shape |
| Normative Reproduction Capsule contract | `contracts/pulsemech_device_ledger_reproduction_capsule_v0.json` | Fixes the exact Capsule and execution contract |
| Canonical Reproduction Capsule manifest | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json` | Binds the exact payload and archive profile without self-reference |
| Reproduction Capsule builder | `tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py` | Constructs the deterministic four-member Capsule from exact inputs |
| Reproduction runner | `tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py` | Orchestrates two constructions, two positive verifier processes, and one targeted negative process |
| Canonical Reproduction Capsule | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip` | Carries the exact four-member portable reproduction package |
| Canonical reproduction result | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json` | Carries canonical orchestration evidence; does not become a verifier verdict |
| Reference-environment attestation | workflow-generated `pulsemech_reference_environment_attestation_v0.json` | Records the exact outer-launcher image and mount preconditions for one workflow execution |
| Reproduction workflow artifact | `pulsemech-device-ledger-reproduction-bootstrap-v0` | Transports the Capsule, result, reference-environment attestation, and runner summary after successful execution |
| Permanent execution regression | `tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py` | Reconstructs and checks the complete portable proof relation |
| Device Ledger demonstrator | `apps/ios/PULSEmechProofApp/` | Displays the exact bounded result and exports the exact `.pulseledger`; `diagnostic_shadow`, not authority |

The reference-environment attestation and release-artifact attestation have
different subjects.

```text
release attestation subject:
artifact_provenance_binding_v0.json

reference-environment attestation subject:
exact bounded reproduction execution precondition
```

Neither attestation independently creates release authority.

---

## 4. External verification targets

### 4.1. Release-authority target

The release-authority target is the recorded PULSEmech downstream relation:

```text
recorded run identity
+ source commit identity
+ status.json
+ declared gate policy
+ workflow-effective materialized required-gate set
+ strict CI gate-enforcement result
+ release-decision materialization artifact
+ Quality Ledger reader artifact
+ release-authority manifest / trace artifact
+ artifact_provenance_binding_v0.json
+ binding_hash
+ optional attestation over the binding carrier
```

### 4.2. Direct Device Ledger target

The direct bounded Device Ledger target is:

```text
exact reference .pulseledger bytes
+ expected observer-key fingerprint
+ exact standalone-verifier implementation
→ exact canonical verification result
```

### 4.3. Reproduction Capsule target

The complete Reproduction Capsule target is:

```text
exact Capsule-manifest schema
+ exact normative Capsule contract
+ exact canonical Capsule manifest
+ exact protected payload bytes
+ exact deterministic builder
+ exact result schema
+ exact orchestration runner
+ exact reference environment
→ Capsule A
+ Capsule B
+ exact A/B/canonical byte equality
+ positive verifier process A
+ positive verifier process B
+ exact canonical stdout equality
+ targeted package-signature mutation
+ exact package_signature_valid rejection
+ canonical reproduction result
```

All three targets preserve:

```text
verification or reproduction
≠
release authority
```

---

## 5. Minimum artifact sets

### 5.1. Release-authority review

A release-authority reviewer should receive or locate:

```text
status.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
release_decision_v0.json
release_authority_v0.json
report_card.html
artifact_provenance_binding_v0.json
```

When available, also inspect:

```text
status_summary.json
status_summary.md
release_decision_v0_ledger_section.html
report_card.with_release_decision.html
release_authority_audit_bundle/
attestation record for artifact_provenance_binding_v0.json
```

### 5.2. Direct Device Ledger verification

Minimum set:

```text
examples/device_transition_ledger/
  pulsemech_device_transition_ledger_reference_v0.pulseledger

tools/
  verify_pulsemech_device_ledger_v0.py

expected observer fingerprint:
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

### 5.3. Reproduction Capsule contract review

Minimum contract set:

```text
schemas/
  pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json

contracts/
  pulsemech_device_ledger_reproduction_capsule_v0.json

examples/device_transition_ledger/
  pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json

tests/
  test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py
```

### 5.4. Complete Reproduction Capsule execution review

Minimum complete set:

```text
tools/
  build_pulsemech_device_ledger_reproduction_capsule_v0.py
  run_pulsemech_device_ledger_reproduction_capsule_v0.py
  verify_pulsemech_device_ledger_v0.py

schemas/
  pulsemech_device_ledger_reproduction_result_v0.schema.json

examples/device_transition_ledger/
  pulsemech_device_ledger_reproduction_capsule_v0.zip
  pulsemech_device_ledger_reproduction_result_reference_v0.json
  pulsemech_device_transition_ledger_reference_v0.pulseledger
  pulsemech_device_transition_ledger_reference_verification_v0.json

tests/
  test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py

.github/workflows/
  pulsemech_device_ledger_reproduction_capsule_v0.yml

ci/
  tools-tests.list
```

Canonical proof record:

```text
docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md
```

---

## 6. Verification profiles

External verification can be performed at different depths.

| Profile | Purpose | Required artifacts |
|---|---|---|
| Reader parity review | Check that public reader surfaces do not overstate authority | `status.json`, Quality Ledger |
| Authority-path review | Check release-decision inputs and strict enforcement | `status.json`, policy, materialized required-gate set, `check_gates.py` semantics |
| Binding verification | Check the digest-backed artifact relation | `artifact_provenance_binding_v0.json`, bound artifacts, binding verifier |
| Release attestation review | Check an attestation over the release binding carrier | binding artifact + attestation record |
| Release-grade review | Verify prod/materialized release-grade admissibility | status overlay + release-grade gates + exact run artifacts |
| Direct Device Ledger verification | Reconstruct the canonical result from one exact `.pulseledger` | exact `.pulseledger`, standalone verifier, expected observer fingerprint |
| Device Ledger Swift round trip | Reproduce Swift carrier parity and the focused relevant negative proof | Swift package + standalone verifier + canonical artifacts |
| Capsule contract review | Verify the acyclic identity model and fixed archive profile | manifest schema, normative contract, canonical manifest, contract regression |
| Capsule local proof replay | Reconstruct the complete Capsule relation on the current host | repository checkout + permanent execution regression |
| Capsule reference-environment reproduction | Execute the complete proof in the exact pinned reference environment | dedicated workflow + exact image + outer attestation + builder + runner + canonical objects |
| Canonical-result audit | Check that the recorded orchestration evidence matches the executed relation | canonical result + result schema + execution regression + exact implementation identities |

A shallower profile must not be reported as a deeper profile.

Examples:

```text
standalone verifier PASS
≠
Capsule A/B construction proof

local proof replay
≠
verified pinned-container execution

reader parity
≠
authority-path reconstruction
```

---

## 7. Device Ledger bounded reproduction profile

The bounded Device Ledger profile is a completed synthetic reference proof.

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256
```

The profile does not claim:

```text
live production iPhone observation
production installation identity
production Keychain origin
Secure Enclave origin
platform attestation
physical-device identity
device-security status
malware absence
continuous background monitoring
complete causal observation
production readiness
universal cross-platform reproducibility
external approval
release authority
```

The bounded proof contains two related execution levels:

```text
direct exact .pulseledger verification

complete Reproduction Capsule construction and execution
```

The direct verifier remains the verification implementation at both levels.

The Capsule runner remains orchestration only.

---

## 8. Direct exact `.pulseledger` verification

### 8.1. Exact positive subject

The exact reference carrier is:

```text
path:
examples/device_transition_ledger/
pulsemech_device_transition_ledger_reference_v0.pulseledger

size:
133568 bytes

SHA-256:
a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3

Git blob SHA-1:
8d9ecb2c6d42f8fd5afb10face6495ef67874b2d

member count:
10
```

Standalone verifier:

```text
path:
tools/verify_pulsemech_device_ledger_v0.py

size:
126419 bytes

SHA-256:
0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7

Git blob SHA-1:
6f5ac6323c56d22e6a908d6a2419f253617382b0
```

Expected observer fingerprint:

```text
f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

Run from the repository root:

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

producer_verdict_trusted:
false

verifier_implementation_relation:
separate_from_producer_code

authority_effect:
none
```

Canonical verifier-report identity:

```text
path:
examples/device_transition_ledger/
pulsemech_device_transition_ledger_reference_verification_v0.json

size:
15328 bytes

SHA-256:
5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4

Git blob SHA-1:
e79e70a243ff104e4d0f17d09379ae1e3962230a
```

The report remains bound to the exact carrier filename, size, and SHA-256.

### 8.2. Same-carrier repeated verification

The same exact carrier supplied to the same exact verifier must produce the same
canonical report bytes.

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

### 8.3. Base relevant negative proof

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

Expected negative state:

```text
exit status:
2

stderr:
empty

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

---

## 9. Reproduction Capsule contract

The Capsule contract was merged through:

```text
pull request:
#2851

squash-merge commit:
722fe4e85acfaac67c283862645ac9e42c831236
```

It fixes the acyclic relation:

```text
Capsule-manifest schema
→ normative Capsule contract
→ canonical Capsule manifest
→ deterministic Capsule construction
→ external canonical reproduction result
```

Exact contract identities:

| Object | Path | Size | SHA-256 | Git blob SHA-1 |
|---|---|---:|---|---|
| Capsule-manifest schema | `schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json` | `32581` | `a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c` | `6a0dabff2e5f725c6ef8e586f9cae7fff566030b` |
| Normative Capsule contract | `contracts/pulsemech_device_ledger_reproduction_capsule_v0.json` | `15947` | `ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67` | `d15fddbe9250de0ed76b3b7ebb7d679383a867b4` |
| Canonical Capsule manifest | `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json` | `8989` | `cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf` | `b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b` |

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

The manifest binds exact payload and archive identities.

It does not bind:

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

---

## 10. Deterministic four-member Capsule

The canonical Capsule is:

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

It contains exactly four `ZIP_STORED` members in this order:

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

The fixed archive profile includes:

```text
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

The checked-in Capsule is one exact deterministic builder output.

It was not manually assembled, normalized, regenerated, recompressed, or
created through a graphical archive tool.

Parsed ZIP equivalence is insufficient.

The recorded proof requires exact Capsule-byte identity.

---

## 11. Builder, result schema, and runner identities

The deterministic execution was merged through:

```text
pull request:
#2852

squash-merge commit:
21837e1e54f898a131d3a9bff89527209ddae711

post-merge review:
no actionable findings
```

Exact implementation identities:

| Object | Path | Size | SHA-256 | Git blob SHA-1 |
|---|---|---:|---|---|
| Capsule builder | `tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py` | `79156` | `1a5c48aa63eb7d74235741ff738d4f08a245096f71a76057a22b88036036e1d0` | `22fa939d7bd9706a654fbb8893ef0c06ef4e160b` |
| Reproduction-result schema | `schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json` | `71112` | `c6ff62b7c6af008ae7e15bec69452d6860dfa16c0e8a1345ce843d8713c02af7` | `7c9e68a48e79551c2929c56bdfc907ffa67d2992` |
| Reproduction runner | `tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py` | `123414` | `ffd3b9604334587030a89f20952e65417f83036161634755c6541435c5d20104` | `e9f58f9a08344b6b2dce698a25834909ecdc082a` |
| Permanent execution regression | `tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py` | `55793` | `312e2e2465e7fbefb33d7943329920d1dbb32572acde9bfb386a22bfc423e4dc` | `a1a343dfd8de4d6e12c079a8f0358b652d195c87` |
| Dedicated workflow | `.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml` | `34578` | `2f7abfa79b7259773b974198cb46abe789928fab6b8e034117a46f1ed50e2f8d` | `817b41e659179b6893785f6f021fdeec93faecc0` |

The builder constructs the Capsule.

The runner orchestrates the proof.

The standalone verifier reconstructs the Device Ledger verdict.

```text
builder
≠
runner
≠
standalone verifier
```

The result schema rejects:

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

The permanent execution regression is registered exactly once in:

```text
ci/tools-tests.list
```

The current tools-test manifest state is:

```text
active entries:
149

unique active entries:
149
```

---

## 12. Exact reference environment

The canonical reference execution is bound to:

```text
container image:
docker.io/library/python:3.11.9-slim-bookworm@sha256:
2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050

platform:
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

network during bounded reproduction:
none

runtime downloads:
forbidden

repository mount:
read-only

reference-attestation mount:
read-only

output mount:
separate writable
```

The host container runtime verifies the exact required RepoDigest before
container start.

Only after that verification does the outer launcher create the canonical
reference-environment attestation.

Attestation identity:

```text
size:
843 bytes

SHA-256:
9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca

canonical JSON:
yes

trailing newline:
absent
```

In-container operating-system, architecture, and Python observations are
additional environment checks.

They do not independently prove the OCI-image identity.

The reference-environment attestation:

```text
records an execution precondition
≠
release attestation
≠
institutional approval
≠
external validation authority
```

---

## 13. Complete reference-environment operator entrypoint

The dedicated workflow is manually dispatchable.

From a GitHub CLI session authorized to run the repository workflow:

```bash
gh workflow run \
  pulsemech_device_ledger_reproduction_capsule_v0.yml \
  --repo HKati/pulse-release-gates-0.1 \
  --ref main
```

This is a one-command dispatch of the complete reference-environment path:

```text
exact contract regression
→ exact implementation-identity admission
→ exact image pull
→ host-runtime RepoDigest verification
→ exact outer-launcher attestation
→ exact-digest container launch
→ network-disabled bounded execution
→ read-only repository mount
→ read-only attestation mount
→ separate writable output mount
→ Capsule A construction
→ Capsule B construction
→ exact Capsule equality
→ positive verifier process A
→ positive verifier process B
→ exact positive stdout equality
→ targeted negative verifier process
→ exact output verification
→ workflow-artifact transport
```

The workflow dispatch is asynchronous.

A successful run exposes the transport artifact:

```text
pulsemech-device-ledger-reproduction-bootstrap-v0
```

That artifact contains:

```text
pulsemech_device_ledger_reproduction_capsule_v0.zip
pulsemech_device_ledger_reproduction_result_reference_v0.json
pulsemech_reference_environment_attestation_v0.json
pulsemech_device_ledger_reproduction_runner_summary_v0.jsonl
```

The workflow artifact is a transport and review carrier.

It does not become release authority.

---

## 14. Portable local proof replay

From the repository root:

```bash
python3 \
  tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py
```

The no-argument launcher:

```text
removes PYTEST_ADDOPTS
removes PYTEST_PLUGINS
removes PYTEST_CURRENT_TEST
sets PYTEST_DISABLE_PLUGIN_AUTOLOAD = 1
disables external conftest influence
disables repository pytest-configuration influence
requires all 15 collected tests to produce plain passing call reports
```

It rejects:

```text
collection-only success
deselection
skipped proof execution
xfail or xpass
premature pytest success
missing proof-critical call reports
```

The local replay checks:

```text
two deterministic Capsule constructions
exact A/B/canonical Capsule equality
two separate positive verifier executions
exact canonical report bytes
targeted package-signature mutation
exact fail-closed rejection
canonical reproduction-result structure
protected-source preservation
implementation boundary
claim boundary
authority boundary
```

This command is the portable local proof-replay entrypoint.

It does not claim the pinned reference-container precondition unless executed
through the dedicated reference workflow.

```text
local replay PASS
≠
verified pinned-container execution
```

---

## 15. Inner bounded runner

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

It does not form a complete bare-host reference-environment command because the
outer launcher must first:

```text
verify the image RepoDigest
create the exact attestation
launch by exact digest
disable the network
establish the read-only repository mount
establish the read-only attestation mount
establish the separate writable output mount
```

The runner remains orchestration-only.

It does not import verifier internals or construct a replacement verifier
verdict.

---

## 16. Two isolated byte-identical constructions

The complete execution constructs:

```text
Capsule A
+
Capsule B
```

Required isolation:

```text
builder processes:
separate

temporary workspaces:
separate

output directories:
separate

Capsule output reuse:
false

temporary-file reuse:
false

materialized-member reuse:
false

computed-archive-byte reuse:
false
```

Required equality:

```text
Capsule A bytes
=
Capsule B bytes
=
checked-in canonical Capsule bytes
```

The runner also requires equal:

```text
byte counts
SHA-256 identities
member inventories
member order
corresponding member bytes
deterministic builder stdout
```

Two textual `PASS` results without exact byte-identical Capsule construction do
not satisfy the profile.

---

## 17. Two exact positive verifier executions

The standalone verifier executes twice as separate processes against the
independently constructed Capsules.

For both executions:

```text
exit status:
0

stderr:
empty

stdout size:
15328 bytes

stdout SHA-256:
5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4

stdout relation:
exact canonical expected-report bytes

result:
verified_with_declared_unavailability

ok:
true

checks:
49 / 49 passed

failed_check_ids:
[]

failure_stage:
null

checkpoint signature:
verified

package signature:
verified

producer_code_imported:
false

producer_verdict_trusted:
false

verifier_implementation_relation:
separate_from_producer_code

authority_effect:
none
```

The exact relation is:

```text
positive stdout A bytes
=
positive stdout B bytes
=
canonical expected verifier-report bytes
```

Parsed JSON equivalence alone is insufficient.

---

## 18. Targeted Capsule negative reproduction

The negative execution operates only on an isolated temporary copy of the
Capsule-materialized `.pulseledger`.

The checked-in canonical `.pulseledger`, Capsule A, and Capsule B remain
unchanged.

Mutation target:

```text
inner member:
signatures/package-signature-v0.json

field:
signature_base64

first character:
O → P
```

The mutation recomputes:

```text
local-file-header CRC32
central-directory CRC32
```

Mutated carrier identity:

```text
size:
133568 bytes

SHA-256:
4712365d309df49bc42e5cb73d98e37f2bbfc98ef7522b87320612d106157cab
```

The mutation preserves:

```text
valid ZIP structure
carrier size
member count
member names
member order
matching CRC32 fields
canonical package-signature JSON
package-signature subject
package-manifest binding
all non-target member bytes
canonical source artifact
Capsule A
Capsule B
```

Required preceding passed checks:

```text
zip_crc32_valid
package_signature_document_valid
package_signature_subject_valid
```

Required exact negative process state:

```text
exit status:
2

stderr:
empty

stdout size:
15352 bytes

stdout SHA-256:
b701c06c9b6836689f86c6983a4b4723f8524fbf0d4065e47a41c4cbabec65fd

result:
rejected

ok:
false

failure_stage:
package_signature

failed_check_ids:
[
  "package_signature_valid"
]

error_code:
signature_verification_failed

member_path:
signatures/package-signature-v0.json

producer_code_imported:
false

producer_verdict_trusted:
false

verifier_implementation_relation:
separate_from_producer_code

authority_effect:
none
```

An earlier ZIP, CRC32, JSON, inventory, manifest, or signature-subject failure
does not satisfy the negative proof.

---

## 19. Canonical reproduction result

The canonical result is:

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

Draft 2020-12 schema validation:
PASS
```

The result records:

```text
document type:
pulsemech_device_ledger_reproduction_result

schema version:
pulsemech_device_ledger_reproduction_result_v0

record status:
synthetic_reference

proof scope:
bounded_reference_reproduction

carrier class:
diagnostic_shadow

result role:
orchestration_evidence

terminal result:
bounded_reference_reproduction_completed

ok:
true

authority effect:
none
```

The result contains no:

```text
self-hash
self-size
generated timestamp
hostname
username
temporary path
workflow-run identifier
other volatile field
```

The result is orchestration evidence.

```text
canonical reproduction result
≠
standalone verifier report

canonical reproduction result
≠
second verifier verdict

canonical reproduction result
≠
release decision
```

---

## 20. Protected-source preservation

Before and after the reproduction, the runner checks ten protected repository
objects.

The recorded result requires:

```text
protected source count:
10

all exact bytes unchanged:
true

all Git blob identities unchanged:
true

drift detected:
false

repository source write attempted:
false
```

The protected set includes the exact contract, schema, canonical payload,
standalone verifier, expected report, builder, runner, and result-schema
subjects required by the execution.

The runner never overwrites the canonical repository sources.

Any protected-source drift is terminal.

---

## 21. Operator boundary

Any external person or organization may execute:

```text
the standalone verifier command
the focused Swift round-trip suite
the portable local execution regression
the dedicated reference workflow, when authorized
```

The resulting execution may be recorded as:

```text
reproduction note
external review report
independent audit record
consumer integration test
case study
compatibility record
```

The execution does not become:

```text
a required approval
a validation authority
an institutional truth oracle
release authority
device-control authority
```

The exact artifact, contract, implementation, and reconstructed relation carry
the result.

The operator's name, title, affiliation, reputation, or institutional status is
not an input to the verification equation.

---

## 22. External verification phases

### Phase 1 — Repository and commit identity

For a release-authority review, verify:

```text
repository identity
source commit identity
run identity
run key
run mode
```

For the Device Ledger and Capsule profiles, also record:

```text
repository:
HKati/pulse-release-gates-0.1

Capsule-contract merge commit:
722fe4e85acfaac67c283862645ac9e42c831236

Capsule-execution merge commit:
21837e1e54f898a131d3a9bff89527209ddae711

canonical .pulseledger identity
standalone-verifier identity
Capsule identity
canonical reproduction-result identity
expected observer fingerprint
```

Mechanical boundary:

```text
external reviewer checks identity alignment
external reviewer does not redefine the recorded result
```

### Phase 2 — Release-authority carrier inspection

Verify that the PULSEmech release-authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required-gate set
→ strict fail-closed CI enforcement
```

Review:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
required gate selection
workflow-effective required-gate set
check_gates.py true-only behavior
missing required-gate behavior
status schema / release-grade overlay
release-decision materialization
```

The Device Ledger verifier, Capsule, canonical result, and demonstrator remain
outside this release-authority carrier.

### Phase 3 — Status and policy replay

Inspect:

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

The Device Ledger verifier report and Capsule result create no release-decision
label.

### Phase 5 — Binding carrier verification

Binding carrier:

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

The verifier recomputes the recorded release-artifact relationship and accepts
only when the binding matches the supplied artifact set.

### Phase 6 — Attestation-subject review

Primary release-authority attestation subject:

```text
artifact_provenance_binding_v0.json
```

Reference-environment attestation subject:

```text
exact outer-launcher precondition for one bounded Capsule execution
```

For the release attestation, inspect:

```text
attestation subject path
subject digest
binding_hash
attestation issuer / workflow identity
attestation event context
attestation order after binding verification
```

For the reference-environment attestation, inspect:

```text
exact image name and digest
host-runtime RepoDigest verification
verified-before-container-start state
exact-digest launch state
network mode
repository mount mode
attestation mount mode
output mount mode
attestation byte identity
```

The two attestations must not be conflated.

```text
reference-environment attestation
≠
release binding attestation
≠
external validating authority
```

### Phase 7 — Public reader parity review

Reader surfaces include:

```text
Quality Ledger
public status URL
Pages rendering
badges
public release-decision display
minimal Device Ledger demonstrator
canonical Device Ledger proof record
```

Boundary:

```text
reader carrier ≠ authority carrier
publication carrier ≠ recorded authority artifact
trace carrier ≠ decision engine
audit bundle ≠ release decision
demonstrator ≠ external validating authority
proof document ≠ verifier verdict
```

The Device Ledger surfaces must preserve:

```text
record_status = synthetic_reference
identity_scope = fixture_installation
key_origin_profile = fixture_software_p256
authority_effect = none
external_validation_claim = none
```

### Phase 8 — Direct Device Ledger reproduction

Verify:

```text
exact `.pulseledger` size and SHA-256
exact verifier size and SHA-256
expected observer fingerprint
verifier exit status 0
empty stderr
exact canonical stdout bytes
49 / 49 passed checks
verified checkpoint signature
verified package signature
producer_code_imported = false
producer_verdict_trusted = false
authority_effect = none
```

### Phase 9 — Capsule reference-environment reproduction

Verify the complete workflow relation:

```text
contract regression passed
exact image RepoDigest verified before launch
exact attestation created
network disabled during bounded reproduction
repository mounted read-only
attestation mounted read-only
output mounted separately writable
Capsule A constructed
Capsule B constructed independently
A/B/canonical bytes equal
positive verifier A passed
positive verifier B passed
targeted negative reached package_signature_valid
canonical result generated
protected sources unchanged
workflow artifact published only after success
```

### Phase 10 — Canonical-result audit

Check:

```text
result size and SHA-256
Git blob SHA-1
canonical JSON framing
result schema validity
implementation identities
Capsule identity
repeated-construction state
positive reproduction cardinality = 2
negative exact failed-check set
protected-source count = 10
implementation boundary
claim boundary
authority boundary
```

A matching result object without an executed proof is insufficient.

The permanent regression must reconstruct and compare the relation.

---

## 23. Suggested external reviewer commands

### 23.1. Release-authority repository checks

```bash
python -m py_compile \
  PULSE_safe_pack_v0/tools/check_gates.py \
  PULSE_safe_pack_v0/tools/render_quality_ledger.py \
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

```bash
python -m pytest -q \
  tests/test_render_quality_ledger.py::test_q1_reference_shadow_section_renders_when_present \
  tests/test_render_quality_ledger_public_surface_state.py
```

```bash
python tests/test_tools_tests_list_smoke.py
```

### 23.2. Direct Device Ledger verification

```bash
python3 tools/verify_pulsemech_device_ledger_v0.py \
  examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger \
  --expected-observer-fingerprint \
  f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

### 23.3. Device Ledger Swift round trip

```bash
cd apps/ios/Packages/PULSEmechLedgerCore

swift test \
  --configuration debug \
  --no-parallel \
  -j 1 \
  --filter SwiftPulseledgerVerifierRoundTripTests
```

### 23.4. Portable complete Capsule replay

```bash
python3 \
  tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py
```

Expected completion:

```text
15 collected
15 plain passing call reports
```

### 23.5. Canonical reference-environment workflow

```bash
gh workflow run \
  pulsemech_device_ledger_reproduction_capsule_v0.yml \
  --repo HKati/pulse-release-gates-0.1 \
  --ref main
```

This command dispatches the complete pinned reference-environment workflow.

The resulting workflow run must finish successfully before its reproduction
record is reported as completed.

These commands are reviewer and reproducer aids.

They do not replace exact run and artifact identity checks.

They do not make the operator part of the authority path.

---

## 24. External verification checklists

### 24.1. Release-authority reviewer checklist

```text
Repository / commit identity aligned: yes / no
Run identity aligned: yes / no
status.json present and parseable: yes / no
Declared gate policy present: yes / no
Workflow-effective required-gate set reconstructable: yes / no
Required gates literal true for allow: yes / no
Release-decision artifact present: yes / no
Release label valid: yes / no
Quality Ledger parity preserved: yes / no
Release-authority manifest present: yes / no
Artifact provenance binding present: yes / no
Binding verifier passes: yes / no
Release-attestation subject is artifact_provenance_binding_v0.json: yes / no
Release attestation exists when expected: yes / no
Public reader boundary preserved: yes / no
```

### 24.2. Direct Device Ledger reproducer checklist

```text
Exact carrier path located: yes / no
Carrier byte size = 133568: yes / no
Carrier SHA-256 matches canonical identity: yes / no
Standalone-verifier identity matches: yes / no
Expected observer fingerprint supplied: yes / no
Standalone verifier exit status = 0: yes / no
Verifier stderr empty: yes / no
Verifier result = verified_with_declared_unavailability: yes / no
Exact check set = 49 passed checks: yes / no
Checkpoint signature verified: yes / no
Package signature verified: yes / no
producer_code_imported = false: yes / no
producer_verdict_trusted = false: yes / no
verifier_implementation_relation = separate_from_producer_code: yes / no
authority_effect = none: yes / no
external_validation_claim = none: yes / no
Operator identity used as a verification input: no
```

### 24.3. Reproduction Capsule reviewer checklist

```text
PR #2851 contract objects located: yes / no
Manifest schema exact identity matches: yes / no
Normative contract exact identity matches: yes / no
Canonical manifest exact identity matches: yes / no
Canonical Capsule size = 285144: yes / no
Canonical Capsule SHA-256 matches: yes / no
Canonical Capsule Git blob SHA-1 matches: yes / no
Capsule member count = 4: yes / no
Capsule member order exact: yes / no
All four members use ZIP_STORED: yes / no
All fixed archive metadata matches: yes / no
Builder exact identity matches: yes / no
Result schema exact identity matches: yes / no
Runner exact identity matches: yes / no
Reference image digest matches: yes / no
Host-runtime RepoDigest verified before start: yes / no
Attestation size = 843: yes / no
Attestation SHA-256 matches: yes / no
Bounded reproduction network = none: yes / no
Repository mount = read-only: yes / no
Attestation mount = read-only: yes / no
Output mount = separate writable: yes / no
Capsule A constructed in isolated process/workspace: yes / no
Capsule B constructed in second isolated process/workspace: yes / no
Capsule A bytes = Capsule B bytes: yes / no
Capsule A/B bytes = canonical Capsule bytes: yes / no
Positive verifier process A exit = 0: yes / no
Positive verifier process B exit = 0: yes / no
Positive stdout A/B/canonical bytes equal: yes / no
Target mutation = signature_base64 O → P: yes / no
Local-header CRC32 repaired: yes / no
Central-directory CRC32 repaired: yes / no
Negative process exit = 2: yes / no
Preceding CRC/document/subject checks passed: yes / no
Exact failed check = package_signature_valid: yes / no
Canonical result size = 31188: yes / no
Canonical result SHA-256 matches: yes / no
Canonical result Git blob SHA-1 matches: yes / no
Canonical result has no BOM, CR, LF, or trailing newline: yes / no
Protected source count = 10: yes / no
Protected exact bytes unchanged: yes / no
Protected Git blob identities unchanged: yes / no
Repository source write attempted = false: yes / no
reproduction_result_role = orchestration evidence: yes / no
producer_verdict_trusted = false: yes / no
authority_effect = none: yes / no
Operator identity used as a proof input: no
```

---

## 25. External verification report format

A minimal report should identify its subject explicitly.

```text
Reviewer:
Date:
Repository:
Commit:
Run identity:
Verification subject:
Verification profile:
Artifact set inspected:
Exact identities checked:
Commands run:
Process results:
Binding verification result:
Standalone reproduction result:
Capsule reproduction result:
Reference-environment attestation result:
Public reader parity result:
Authority-impact findings:
Residual issues:
Operator authority required:
Conclusion:
```

For the bounded Device Ledger and Reproduction Capsule profiles:

```text
Operator authority required:
no
```

A report must distinguish:

```text
command dispatched
workflow completed
artifact retrieved
artifact identity verified
proof relation reproduced
```

Dispatch alone does not establish completed reproduction.

---

## 26. External verification status classes

| Status | Meaning |
|---|---|
| Verified | The declared artifact relation was verified and no blocking mismatch was found |
| Partially verified | Some artifact relations were verified, but the required set or execution evidence remains incomplete |
| Reader-only verified | Public reader surfaces match recorded artifacts, but authority reconstruction was not completed |
| Direct Device Ledger reproduced | The exact `.pulseledger` and standalone verifier produced the exact canonical positive result |
| Capsule contract verified | The exact schema, contract, canonical manifest, and fixed archive profile matched |
| Capsule local replayed | The permanent execution regression reconstructed and passed the complete relation on the current host |
| Capsule reference reproduced | The complete proof passed in the exact pinned reference environment |
| Reproduction mismatch | An exact artifact, implementation, environment, or result identity differed |
| Binding mismatch | A release binding digest or subject mismatch was found |
| Authority mismatch | The recorded release-authority path could not be reconstructed from supplied artifacts |
| Inconclusive | Required artifacts or execution evidence were unavailable |

These statuses describe the external review or reproduction event.

They do not change:

```text
the underlying artifact
the verifier equation
the recorded release decision
release authority
device-control authority
```

A `Capsule reference reproduced` status records that a new execution matched
the exact declared reference relation.

It does not mean that the reviewer or institution created the result's
validity.

---

## 27. Integration boundary

External verification may produce:

```text
review report
reproduction note
case study
third-party reference integration
audit finding
consumer compatibility record
workflow-run reference
```

External verification does not alter:

```text
status.json
declared gate policy
materialized required-gate set
check_gates.py behavior
CI allow/block result
release-decision materialization
artifact_provenance_binding_v0.json
release attestation record
Device Ledger carrier bytes
Device Ledger canonical verifier report
Reproduction Capsule bytes
canonical reproduction-result bytes
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

A consumer integration may wrap or transport the canonical objects.

It must not silently:

```text
rewrite exact bytes
replace the standalone verifier
substitute a producer verdict
weaken the negative proof
change the claim boundary
promote the Capsule into authority
```

---

## 28. Machine-readable external verification packet

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

The current packet implementation remains unchanged by the Device Ledger
Reproduction Capsule documentation closure.

This document does not claim that the current packet builder automatically
materializes the complete Capsule profile.

A later packet-contract extension may add that profile only through an explicit
implementation and regression change.

Any such extension must preserve:

```text
operator identity is not a verification input
reproduction result is orchestration evidence
producer verdict is not trusted
authority_effect = none
external_validation_claim = none
```

The packet remains a review carrier.

It must not become:

```text
an independent release-decision engine
repository-state authority
a required external approval
a replacement for exact artifact verification
a replacement standalone verifier
```

---

## 29. Canonical source map

### Release-authority review

- [`../PULSEMECH_TECHNICAL_OVERVIEW.md`](../PULSEMECH_TECHNICAL_OVERVIEW.md)
- [`../pulse_gate_policy_v0.yml`](../pulse_gate_policy_v0.yml)
- [`../pulse_gate_registry_v0.yml`](../pulse_gate_registry_v0.yml)
- [`../PULSE_safe_pack_v0/tools/check_gates.py`](../PULSE_safe_pack_v0/tools/check_gates.py)
- [`../PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py`](../PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py)

### Canonical Device Ledger proof

- [`PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md`](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
- [`../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger)
- [`../tools/verify_pulsemech_device_ledger_v0.py`](../tools/verify_pulsemech_device_ledger_v0.py)
- [`../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json`](../examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json)

### Reproduction Capsule contract

- [`../schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json`](../schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json)
- [`../contracts/pulsemech_device_ledger_reproduction_capsule_v0.json`](../contracts/pulsemech_device_ledger_reproduction_capsule_v0.json)
- [`../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json)
- [`../tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py`](../tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py)

### Reproduction Capsule execution

- [`../tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py`](../tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [`../schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json`](../schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json)
- [`../tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py`](../tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [`../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip)
- [`../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json`](../examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json)
- [`../tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py`](../tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py)
- [`../.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml`](../.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml)
- [`../ci/tools-tests.list`](../ci/tools-tests.list)

### Runnable demonstrator

- [`../apps/ios/PULSEmechProofApp/`](../apps/ios/PULSEmechProofApp/)
- [`../.github/workflows/pulsemech_ios_proof_app.yml`](../.github/workflows/pulsemech_ios_proof_app.yml)

### External verification packet

- [`EXTERNAL_VERIFICATION_PACKET_v0.md`](EXTERNAL_VERIFICATION_PACKET_v0.md)
- [`../scripts/build_external_verification_packet_v0.py`](../scripts/build_external_verification_packet_v0.py)
- [`../tests/test_build_external_verification_packet_v0.py`](../tests/test_build_external_verification_packet_v0.py)

---

## 30. Boundary held by this document

External Verification Path v0 defines review and reproduction paths for exact
recorded PULSEmech artifact relationships.

It does not change:

```text
PULSEmech decision semantics
gate policy
required-gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
release attestation workflow behavior
Device Ledger implementation
standalone Device Ledger verifier implementation
reference .pulseledger bytes
canonical Device Ledger verifier report
Reproduction Capsule contract
Reproduction Capsule bytes
canonical reproduction-result bytes
release tags
publication metadata
DOI / Zenodo path
CITATION.cff
```

The PULSEmech release-authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required-gate set
→ strict fail-closed CI enforcement
```

The external verification carrier reviews that recorded artifact relationship.

The Device Ledger standalone verifier reconstructs the Device Ledger result
from exact artifact bytes.

The Reproduction Capsule runner orchestrates exact construction and verifier
processes without becoming a verifier.

The canonical reproduction result records orchestration evidence without
becoming a verifier verdict.

```text
external execution:
optional reproduction event

operator identity:
not a verification input

bounded Device Ledger mechanical proof:
closed

Device Ledger Reproduction Capsule contract:
closed

deterministic Reproduction Capsule execution:
closed

minimal runnable iPhone demonstrator:
closed

authority_effect:
none

external_validation_claim:
none
```
