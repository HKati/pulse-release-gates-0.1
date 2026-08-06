# PULSEmech — Witness interoperability and release-authority boundary v0

## WORKMARK

```text
document_role:
interoperability_mapping_and_authority_boundary_record

status:
design_and_upstream_source_review_record

review_date:
2026-08-06

pulse_repository:
HKati/pulse-release-gates-0.1

pulse_merged_repository_basis:
8f5f83309c920991a5223925e6084f5273a824c6

pulse_existing_slsa_vsa_state:
implemented_and_proven_non_active_candidate

upstream_cli_repository:
in-toto/witness

upstream_cli_reviewed_ref:
main

upstream_cli_reviewed_resolved_revision:
69402a9a630bb0a06fe969786f7f7db30d0a01a0

upstream_cli_reviewed_surface_manifest_sha256:
c9ab2237045a2c7655a07e730745a6677289e939ce3759e269073b2872952605

upstream_cli_retrieval_method:
github_repository_api_exact_commit_and_blob_reads

upstream_cli_external_downloaded_source_artifact:
none

upstream_library_repository:
in-toto/go-witness

upstream_library_reviewed_ref:
v0.12.0

upstream_library_resolved_revision:
afcde8ce90904c70054bedf999fe95b962c338a5

upstream_library_module_checksum:
h1:GjyHIF6UiFHKfach2qPymWquFlXFPlxGGCqzJAyplr0=

upstream_library_go_mod_checksum:
h1:ORIldYFODV477Eb4j+rD4PZ9IcgKTxLIDt/lLMwvycE=

upstream_library_reviewed_surface_manifest_sha256:
0532dd7ccd368f8fdc4ee2dc327981136de9574c0b96aec86726e5cd37ad5e3c

upstream_library_retrieval_method:
github_repository_api_tag_resolution_exact_commit_and_blob_reads

upstream_library_checksum_source:
witness_cli_go_sum_at_69402a9a630bb0a06fe969786f7f7db30d0a01a0

upstream_library_external_downloaded_module_artifact:
none_during_this_source_review

upstream_cli_go_witness_dependency:
github.com/in-toto/go-witness v0.12.0

upstream_review_reproducibility:
exact_revision_and_content_identity_bound

canonical_structured_payload_determinism:
required

cryptographic_wrapper_byte_identity:
not_required_across_independent_signing_events

canonical_payload_serialization_boundary:
canonical_payload_member_only

cryptographic_wrapper_serialization_domain:
outer_carrier_only

canonical_json_byte_rule:
artifact_provenance_binding_v0_exact_bytes

upstream_resigned_envelope_effect:
new_upstream_carrier_and_new_pulse_canonical_result

envelope_payload_equality:
required_for_policy_and_every_attestation

runtime_cli_identity:
required_only_when_cli_participates

x509_functionary_match_evidence:
required_when_x509_authorization_is_used

witness_interoperability_status:
mechanical_boundary_specified_implementation_absent

witness_slsa_export_mapping:
possible_existing_slsa_vsa_candidate_input_not_proven_by_this_document

witness_full_policy_verification_mapping:
dedicated_structured_carrier_required

normative_schema:
not_defined

trusted_adapter:
not_implemented

candidate_gate_set:
not_registered

workflow_integration:
none

release_required_activation:
none

release_authority_effect:
none
```

This document records the mechanical relationship between:

```text
in-toto Witness
```

and:

```text
PULSEmech artifact-bound release authority
```

It identifies the parts of Witness that can become authenticated upstream
evidence, the parts that require a dedicated lossless carrier, and the boundary
that prevents Witness verification from being mistaken for a PULSEmech release
decision.

This document does not implement Witness integration.

This document does not modify the existing SLSA/VSA candidate path.

This document does not register or activate a Witness gate.

This document does not change release authority.

---

## 1. Purpose

Witness is not merely a provenance-file generator.

Its mechanical path is:

```text
command or lifecycle step
→ pre-execution and post-execution attestors
→ versioned in-toto attestations
→ signed DSSE envelope
→ signed Witness policy
→ functionary and attestation verification
→ artifact-flow verification
→ policy verification result
```

PULSEmech has a different terminal object:

```text
recorded current-run release evidence
→ exact subject and run binding
→ declared PULSE release policy
→ workflow-effective materialized required gates
→ deterministic verifier replay
→ final status
→ strict terminal enforcement
→ primary CI ALLOW or BLOCK
```

The purpose of this document is to define the exact relation between those two
machines.

The required relationship is additive:

```text
Witness evidence and verification
→ PULSEmech evidence admission
→ PULSEmech policy materialization
→ PULSEmech terminal release transition
```

The forbidden relationship is substitution:

```text
witness verify exit 0
→ assumed PULSEmech ALLOW
```

---

## 2. Reviewed upstream source identity and review reproducibility

The upstream review is bound to immutable source identities.

A branch, tag, release label or module version is a human-readable locator.

It is not sufficient as the sole review identity.

The review record must preserve:

```text
repository identity
human-readable ref or module version
resolved immutable revision
content identity for the reviewed source
retrieval method
reviewed file surface
```

### Witness CLI repository

```text
repository:
in-toto/witness

reviewed ref:
main

resolved revision:
69402a9a630bb0a06fe969786f7f7db30d0a01a0

retrieval method:
GitHub repository API reads bound to the exact resolved commit and Git blob IDs

external downloaded source artifact:
none

reviewed-surface manifest SHA-256:
c9ab2237045a2c7655a07e730745a6677289e939ce3759e269073b2872952605
```

The reviewed CLI surface is bound by the following canonical manifest.

Each line is:

```text
<repository-relative path><TAB><Git blob object ID><LF>
```

Lines are sorted lexicographically by repository-relative path.

The manifest SHA-256 is calculated over the exact UTF-8 manifest bytes.

```text
GOVERNANCE.md	9676324722e53513b8cec87c80a912a598b8b67c
MAINTAINERS.md	bab73f118649fbfcbc464fed2fa0696eede189f3
README.md	7d56e2ced1b625dd512e981943cfec5c8190651a
SECURITY.md	1c558ac99c95d76435eecfbd4bd1e1b933b9ba41
cmd/run.go	a075663dd238bee6ec329fff2e9226b718ddcc89
cmd/verify.go	507a45e77c6a6808e979226402a54d5ec0b3a4c4
docs/about/how-witness-works.md	9fe8b9615a92ba1df03363eca0ea63c219726587
docs/concepts/attestor.md	bd8904462c788a5811d3b02913ee61f73077a186
docs/concepts/policy.md	860d34cca47d18b178b1595413f5bd746cab752b
docs/tutorials/getting-started.md	b30cdd9ab9ed8ef7655dd099b1380c850d7108d9
go.mod	869622d966106e076e44ae94ab11e9f85e53ce94
go.sum	1632e39617f78dddfeab9991f2c1eca26dc1d5e0
internal/policy/policy.go	7aac106a58a148abfdfc4e92b1787492e395600a
```

The manifest binds the exact reviewed file set.

The review used exact-revision repository API reads and Git blob identities.

It did not use a generated source archive, raw-file bundle or other external
source artifact for the CLI review.

It is not presented as a digest of every file in the upstream repository.

If a full source archive, source bundle or raw-file collection is downloaded
outside Git's object model, the review record must additionally preserve:

```text
resolved commit SHA-40
exact downloaded byte count
SHA-256 of the downloaded content
retrieval source and locator
retrieval event identity
```

A regenerated GitHub source archive must not be assumed to retain identical
compressed bytes merely because it resolves to the same commit.

The downloaded artifact identity and the resolved Git source identity are
separate records.

### go-witness library

```text
repository:
in-toto/go-witness

reviewed ref:
v0.12.0

resolved revision:
afcde8ce90904c70054bedf999fe95b962c338a5

retrieval method:
GitHub tag resolution followed by repository API reads bound to the exact
resolved commit and Git blob IDs

checksum source:
the exact Witness CLI go.sum at revision
69402a9a630bb0a06fe969786f7f7db30d0a01a0

external downloaded module artifact:
none during this source review

Go module content checksum:
h1:GjyHIF6UiFHKfach2qPymWquFlXFPlxGGCqzJAyplr0=

Go module go.mod checksum:
h1:ORIldYFODV477Eb4j+rD4PZ9IcgKTxLIDt/lLMwvycE=

reviewed-surface manifest SHA-256:
0532dd7ccd368f8fdc4ee2dc327981136de9574c0b96aec86726e5cd37ad5e3c
```

The reviewed library surface is bound by:

```text
attestation/factory.go	e4eb55ccffa48cec6c377b22f87ec1cab16bdce8
go.mod	071d765a1e3e0752b9e04b07ebfbbe8d8845f48f
policy/policy.go	1442eb8a2641da8f0a2e8e73b3862a1c789b9967
policy/step.go	42530e83b39e1109d4b839ca613936bf9345a8e3
run.go	87072c0bc45fdefde63af99965e992b815776972
verify.go	fbe91cefa11b4dee40e1c1246b48ce91a92956c0
```

The checksums recorded above are the dependency checksums carried by the
reviewed Witness CLI `go.sum` at the exact CLI revision.

This source review did not independently download a Go module ZIP or module
metadata artifact through a Go module proxy.

For a later reproduction that obtains the module through the public Go module
mechanism, the review record must preserve and verify both:

```text
module content checksum
+
go.mod checksum
```

The module version must also be resolved to the exact upstream commit used by
the review.

A module version or tag without the resolved commit remains insufficient for
source-level reproduction.

### Witness dependency relation

The reviewed Witness CLI revision declares:

```text
github.com/in-toto/go-witness v0.12.0
```

The reviewed Witness CLI `go.sum` binds that dependency to the module and
`go.mod` checksums recorded above.

### Review reproduction rule

A later review reproduces this source basis only when it uses:

```text
the same repositories
+
the same resolved revisions
+
the same reviewed-surface manifests
+
the same Go module checksums where applicable
+
the recorded retrieval methods or an explicitly recorded equivalent method
that resolves and verifies the same immutable source content
```

If the retrieval path produces an external downloaded artifact, that artifact's
exact byte identity must also be recorded.

The source identities above are review anchors.

They are not installation instructions, release promotion, dependency
activation, or a claim that an unpinned future Witness revision has identical
semantics.

---

## 3. Current PULSEmech position

PULSEmech already contains an implemented and proven non-active SLSA/VSA
recorded-intake candidate path.

The existing path is:

```text
recorded SLSA VSA evidence
→ SLSA VSA intake verifier
→ intake report
→ status fold-in
→ non-active candidate gates
→ policy-derived candidate require list
→ generic strict gate checker
```

The existing candidate set is:

```text
slsa_vsa_recorded_intake_candidate
```

Its current status remains:

```text
implemented:
yes

tested:
yes

candidate proof:
complete

active release-required enforcement:
no
```

Witness does not silently replace this lane.

Witness creates two distinct interoperability possibilities:

```text
Witness SLSA export
→ possible input to the existing SLSA/VSA candidate surface

full Witness policy verification
→ requires a dedicated structured Witness carrier
```

Those two relations must remain separate.

---

## 4. Witness system model

Witness is a pluggable software-supply-chain evidence and policy-verification
framework.

Its primary mechanics are:

```text
attest
verify
store and retrieve
```

### Attest

Witness can wrap a command or lifecycle step and collect facts through
attestors.

### Verify

Witness can verify signed attestation collections against a signed policy,
trusted functionaries, required attestation types, Rego conditions and
artifact-flow relations.

### Store and retrieve

Witness can write signed attestations to files or store and retrieve them
through Archivista.

Storage and retrieval are not equivalent to verification.

```text
attestation available
≠
attestation verified
```

---

## 5. Attestor lifecycle as a transition record

Witness attestors are ordered by lifecycle role:

```text
pre-material
→ material
→ execute
→ product
→ post-product
```

This is a domain-specific transition structure.

### Pre-material

Collects environment or infrastructure state before the principal operation.

### Material

Collects input state that may change during execution, including file digests.

### Execute

Records the command or process being executed.

### Product

Collects output state, including changed or created files.

### Post-product

Collects product-specific information after output construction.

The resulting relation is:

```text
observed input state
→ observed execution
→ observed output state
```

This is stronger than an isolated provenance statement because the mechanism
can bind facts around an actual execution boundary.

It remains narrower than the general PULSEmech Transition Meter.

Witness is specialized for software-supply-chain lifecycle transitions.

---

## 6. Attestor identity and schema binding

A Witness attestor carries:

```text
Name
Type
RunType
Schema
Attest implementation
```

The attestation `Type` is a versioned schema identifier.

This provides normalization:

```text
provider-specific or tool-specific observation
→ versioned attestation type
→ in-toto Statement predicate
→ common signed carrier
```

The plugin surface can represent evidence from environments and tools such as:

```text
Git
GitHub
GitLab
AWS
GCP
AWS CodeBuild
OCI
SLSA
SBOM
SARIF
VEX
secret scanning
command execution
material state
product state
```

Attestor registration proves only that a type can be constructed and invoked.

```text
registered attestor
≠
trusted observation

attestor execution
≠
cryptographically validated source fact
```

The upstream attestor security rule is also a PULSEmech admission rule:

```text
an attestation is only as strong as the data and validation that feed it
```

---

## 7. Witness run path

The Witness CLI `run` path:

```text
select signer
→ build attestor set
→ always include material and product attestors
→ add command-run attestor when a command is supplied
→ add selected optional attestors
→ execute attestor lifecycle
→ build attestation collection
→ build in-toto Statement
→ build DSSE envelope
→ sign envelope
→ write file and optionally store in Archivista
```

Some attestors can export separate signed attestations.

Examples include exported:

```text
SLSA provenance
SBOM
other dedicated predicate records
```

The collection and separately exported attestations are distinct carriers.

A PULSEmech adapter must preserve that distinction.

```text
collection envelope
≠
separately exported predicate envelope
```

---

## 8. Witness policy object

A Witness policy is a signed DSSE-carried document.

Its payload can define:

```text
expiry
trusted public keys
trusted X.509 roots
trusted timestamp authorities
required steps
authorized functionaries per step
required attestation types per step
Rego policies per attestation type
artifactsFrom relations
```

The current policy predicate identifier is:

```text
https://witness.testifysec.com/policy/v0.1
```

The Witness policy is an evidence-verification policy.

It is not the PULSE release policy.

```text
Witness policy
≠
pulse_gate_policy_v0.yml
```

The Witness policy determines whether Witness evidence satisfies Witness
requirements.

The PULSE policy determines whether admitted release evidence satisfies the
selected PULSE release lane.

---

## 9. Policy-signature and policy-payload separation

A complete Witness policy identity contains at least:

```text
raw DSSE envelope bytes
envelope SHA-256
payload bytes
payload SHA-256
payload type
verified policy signer identity
trusted policy-verifier roots or keys
policy expiry
policy semantic contents
```

These identities must not be collapsed.

```text
same policy payload
+ different envelope
→ different exact carrier identity
```

and:

```text
valid JSON policy payload
≠
verified signed policy
```

A PULSEmech Witness carrier must preserve both:

```text
exact carrier identity
+
verified semantic policy identity
```

A re-signed Witness policy envelope is a new upstream evidence carrier even
when it contains the same policy payload.

Because the exact original policy-envelope bytes, digest and size are canonical
PULSEmech replay inputs, replacing that envelope changes the canonical input
state and therefore changes the PULSEmech canonical verification-result
identity.

```text
same Witness policy payload
+ different signed policy envelope
→ different upstream evidence carrier
→ different PULSEmech canonical result identity
```

Only wrappers generated around an already constructed PULSEmech canonical
output payload may vary without changing that payload identity.

---

## 10. Functionary verification

Each Witness policy step defines allowed functionaries.

A functionary can be bound through:

```text
public key identity
or
X.509 trust root and certificate constraints
```

The current core verification relation accepts a collection for a step when at
least one verified signer matches an allowed functionary.

Therefore:

```text
functionary list
→ allowed signer set
```

It must not be interpreted as:

```text
all listed functionaries required
```

or:

```text
automatic N-of-M quorum
```

A quorum requirement must be expressed explicitly through a supported policy
condition or a separate admission rule.

PULSEmech must record every verified signer identity and the exact functionary
matching result.

For public-key authorization, the record must preserve the exact verified key
identity.

For X.509 authorization, the record must additionally preserve:

```text
leaf certificate exact bytes or an exact-byte external reference
leaf certificate SHA-256 and size
ordered certificate-chain identities
exact trust-anchor identity
certificate verification time
certificate subject and issuer identities
certificate serial number
URI, DNS, email and IP subject-alternative-name values
common-name and organization values when evaluated
Fulcio issuer and subject-extension values when evaluated
exact policy constraint type and expected value
exact certificate or extension value that satisfied each constraint
functionary-match result for the exact policy step
```

If certificate or chain bytes are stored externally, replay must materialize the
exact referenced DER or PEM bytes before certificate-path and constraint
verification.

It must not reduce the relation to:

```text
functionary_ok:
true
```

without the signer, certificate-chain and matched-constraint identities that
made it true.

---

## 11. Required-attestation verification

A Witness step defines required attestation types.

Current verification requires:

```text
step collection name
=
policy step name
```

An empty or unrelated collection name is not a wildcard.

A step with no required attestation types is not a valid gate.

A policy with no steps is not a valid proof.

For each required attestation type:

```text
required type absent
→ step failure
```

If multiple attestations of the same required type are present, the current
verification path evaluates the Rego policy against every matching attestor.

This prevents:

```text
violating attestor
+ appended benign attestor of same type
→ false pass
```

The PULSEmech carrier must preserve all matching attestations and all evaluation
results.

---

## 12. Rego verification

Witness policy can carry Rego modules for an expected attestation type.

A Rego result can reject an attestation based on its contents.

The PULSEmech mapping must bind:

```text
Rego policy name
Rego module bytes
Rego module SHA-256
expected attestation type
attestation instance identity
evaluation result
denial messages
```

The Rego module must not be identified only by its display name.

```text
Rego policy name
≠
Rego policy identity
```

The exact module bytes are part of the verification state.

---

## 13. Artifact-flow verification

Witness `artifactsFrom` defines a relation between steps.

The current verification rule requires a downstream step's materials to share at
least one artifact path with a passed upstream collection's artifacts.

For every overlapping path:

```text
upstream artifact digest
=
downstream material digest
```

No overlap is a failure.

A mismatching digest is a failure for that candidate relation.

The verifier searches passed upstream collections until it finds a candidate
that satisfies the artifact relation.

This proves:

```text
at least one qualifying upstream artifact-flow edge exists
```

It does not automatically prove:

```text
the edge is unique

the edge is the only causal path

every upstream collection participated

the complete downstream release transition is closed
```

For lossless PULSEmech interoperability, the selected or qualifying
artifact-flow edge must become an explicit record.

A boolean such as:

```text
artifacts_from_ok:
true
```

is insufficient.

---

## 14. Attestation-source and content identity

Witness can read attestations from:

```text
local files
memory source
Archivista
combined sources
```

A source-local reference is not a global attestation identity.

The current go-witness verification code deduplicates accepted collections using
a content-derived identity over:

```text
statement content
+
verified signer key identities
```

This protects against treating two source-local references as globally unique.

The PULSEmech carrier must preserve:

```text
retrieval source
source-local locator
exact envelope bytes
envelope SHA-256
payload SHA-256
verified signer identities
content-derived collection identity
```

Archivista or another store remains:

```text
storage and discovery surface
```

It does not become:

```text
PULSE release authority
```

---

## 15. Witness verify path

The Witness CLI verification path consumes:

```text
artifact file or directory subject
signed policy envelope
attestation files or Archivista source
policy verification key, CA or verifier
optional timestamp authority roots
optional certificate constraints
optional Fulcio constraints
optional KMS verifier configuration
```

It then invokes the go-witness verifier with:

```text
subject digests
collection source
policy signature-verification configuration
timestamp-verification configuration
certificate constraints
```

The library returns:

```text
VerificationSummary
+
StepResults
```

Each step result can preserve:

```text
accepted collections
rejected collections
rejection reasons
warnings
```

The CLI terminal behavior is:

```text
verification success
→ process exit 0

verification or policy failure
→ non-zero process exit
```

The CLI also emits human-oriented logs.

Human-oriented logs are not an admissible normative PULSEmech carrier.

```text
stdout or stderr parsing
≠
lossless structured verification mapping
```

---

## 16. Verification result carrier gap

The go-witness library constructs a verification result through a
`policyverify` attestor and a SLSA Verification Summary.

The library can sign generated results when explicit result signers are
provided.

When no result signer is supplied, the library runs the verification attestor
in insecure output mode.

The reviewed Witness CLI path supplies policy verifiers, not a result signer.

Therefore the ordinary CLI path does not guarantee a persisted, signed,
machine-readable verification-result carrier.

The visible terminal state is principally:

```text
process exit
+
logs
```

This is sufficient for a local CI stop condition.

It is not sufficient for lossless PULSEmech evidence admission.

The missing carrier must preserve:

```text
exact verifier identity
exact verifier configuration
exact policy carrier
exact attestation carriers
exact subject digests
VerificationSummary
complete StepResults
artifact-flow relation state
deterministic diagnostics
producer binding
canonical structured payload identity
cryptographic wrapper identity, when present
```

The canonical structured payload and its cryptographic wrapper are separate
identities.

```text
canonical structured payload
→ deterministic semantic record

cryptographic wrapper
→ signature, certificate, timestamp and transparency binding around that payload
```

The exact admitted wrapper remains an immutable artifact with its own byte
identity.

A separately generated PULSEmech output wrapper may have different bytes
while still binding the same PULSEmech canonical structured payload.

This variability rule does not apply to replacing or re-signing the original
upstream Witness policy or attestation envelopes, because those exact envelope
identities are canonical PULSEmech inputs.

---

## 17. What Witness proves

Under its exact policy and verifier configuration, Witness can prove that:

```text
the policy envelope was accepted under configured trust

the policy was not expired at the verification event

a required step had an accepted attestation collection

the collection signer matched an allowed functionary

required attestation types were present

embedded Rego conditions passed

configured artifact-flow relations had qualifying digest continuity

the supplied artifact subject matched the verification seed

the complete Witness policy evaluation passed
```

The proof is relative to:

```text
exact policy
exact trust roots
exact subject
exact attestation set
exact attestation sources
exact verifier implementation
exact verifier configuration
exact verification time
```

---

## 18. What Witness does not prove by itself

Witness verification does not by itself prove:

```text
that the PULSE release policy is satisfied

that the PULSE workflow-effective required-gate set is complete

that final PULSE status is valid

that every PULSE release-required gate is literal true

that the Witness result was admitted into the current PULSE run

that a durable PULSE release-decision artifact was created

that the primary PULSE CI terminal result was ALLOW

that deployment occurred

that a unique causal path exists through every software-supply-chain step
```

The exact boundary is:

```text
Witness verification PASS
≠
PULSEmech release ALLOW
```

---

## 19. Witness as a domain-specific Transition Meter

Witness measures a software-supply-chain transition:

```text
materials
→ execution
→ products
→ later material consumption
```

It can bind:

```text
who or what executed
which infrastructure was observed
which command ran
which inputs were present
which outputs were produced
which signer attested the step
which downstream step consumed matching artifacts
```

This makes Witness a concrete domain-specific transition instrument.

The broader PULSEmech Transition Meter asks for:

```text
identified source state
changed relation
opened, closed or redirected path
identified target state
time binding
evidence binding
verifier binding
alternative paths
unresolved links
authority state
```

Witness covers a strong software-artifact subset of that architecture.

It does not replace the generalized Transition Meter.

---

## 20. Common mechanical principles

Witness and PULSEmech share several mechanical rules.

```text
record presence
≠
record validity

signature presence
≠
authorized signer

step declaration
≠
step satisfaction

attestation type present
≠
attestation policy passed

artifact names overlap
≠
artifact digests match

policy exists
≠
policy imposes a non-empty requirement

verification process ran
≠
verification passed

verification passed
≠
release authority
```

Both systems are strengthened by explicit rejection of vacuous or nominal
relations.

---

## 21. Different authority objects

Witness and PULSEmech answer different terminal questions.

### Witness

```text
Does this artifact and attestation collection satisfy this signed
software-supply-chain policy?
```

### PULSEmech

```text
May this exact current release candidate cross the declared release boundary
under the complete materialized release policy?
```

The Witness terminal object is:

```text
policy verification result
```

The PULSEmech terminal object is:

```text
release transition
```

A Witness verifier can be an upstream evidence verifier inside PULSEmech.

It is not automatically the downstream PULSEmech release authority.

---

## 22. Two distinct interoperability lanes

Witness exposes two mechanically different PULSEmech integration lanes.

### Lane A — Witness SLSA export

Witness can export a dedicated SLSA provenance predicate.

Possible relation:

```text
Witness run
→ exported SLSA provenance
→ independent VSA verification
→ existing PULSE SLSA/VSA evidence intake
→ existing non-active candidate path
```

This lane can reuse the existing PULSE SLSA/VSA candidate surface only when the
exported provenance and its verification result satisfy the existing PULSE
contracts.

This document does not prove that mapping.

The exported SLSA predicate does not carry the full Witness policy-verification
state.

### Lane B — full Witness policy verification

The full Witness relation includes:

```text
signed Witness policy
trusted policy signer
trusted functionaries
required attestation types
Rego evaluations
artifact-flow verification
complete StepResults
VerificationSummary
```

This relation cannot be losslessly reduced to one SLSA provenance statement or
one VSA boolean set.

It requires a dedicated structured Witness verification carrier.

---

## 23. Witness interoperability tuple

Define the upstream Witness verification tuple:

```text
W = ⟨WS, WE, WP, WF, WR, WV, WO⟩
```

where:

```text
WS:
exact artifact subject and digest set

WE:
exact signed attestation evidence carriers

WP:
exact signed Witness policy and trust configuration

WF:
verified functionary bindings

WR:
verified step and artifact-flow relations

WV:
exact Witness verifier identity, configuration and replay state

WO:
structured Witness verification outcome
```

A lossless Witness-to-PULSE mapping must preserve every required element of
`W`.

---

## 24. Mapping Witness into the PULSEmech tuple

The PULSEmech release-transition tuple is:

```text
R = ⟨S, E, A, P, G, V, F, D⟩
```

The mapping is:

| Witness element | PULSEmech position | Boundary |
|---|---|---|
| `WS` artifact subject | `S` and `A` | Must match the exact PULSE release artifact and candidate |
| `WE` signed attestations | `E` | Upstream evidence only after PULSE admission |
| `WP` Witness policy | `E` and upstream policy-binding evidence | Does not replace PULSE release policy `P` |
| `WF` functionary binding | `E` and upstream trust evidence | Does not create PULSE authority |
| `WR` step and artifact flow | `E` and transition evidence | Does not by itself close the full PULSE transition |
| `WV` Witness verifier | upstream verifier evidence within `V` | PULSE still verifies admission and downstream state |
| `WO` verification result | admitted evidence and possible candidate-gate source | Not `D` |
| PULSE policy | `P` | Remains the PULSE release policy |
| PULSE effective gates | `G` | Remains policy-derived inside PULSE |
| PULSE final status | `F` | Remains the complete PULSE gate-state carrier |
| primary PULSE CI result | `D` | Remains terminal ALLOW or BLOCK |

The key relation is:

```text
WO
→ admitted element of E
```

not:

```text
WO
→ D
```

---

## 25. Proposed structured carrier

A future implementation should define two separate schema and serialization
domains:

```text
canonical payload schema_version:
pulsemech_witness_verification_evidence_v0

canonical payload record_type:
pulsemech_witness_verification_evidence

outer carrier schema_version:
pulsemech_witness_verification_evidence_carrier_v0

outer carrier record_type:
pulsemech_witness_verification_evidence_carrier
```

Only the `canonical_payload` member is serialized and hashed as the semantic
verification result.

Its bytes are defined by the repository
[Canonical JSON byte rule](../ARTIFACT_PROVENANCE_BINDING_v0.md#canonical-json-byte-rule):

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8")
```

The resulting byte contract is:

```text
object keys sorted
no insignificant whitespace
UTF-8 bytes
no trailing newline
NaN and Infinity rejected
the digest field omitted from the object being digested
```

A non-Python producer must emit byte-for-byte equivalent output.

Semantic JSON equality is insufficient.

The future Go adapter must pass cross-language byte-conformance vectors covering
at least:

```text
non-ASCII strings
quotation marks and backslashes
newlines and control characters
<, > and & characters
nested objects and arrays
empty objects and arrays
integers and every permitted numeric representation
```

If a numeric representation cannot be emitted byte-identically to the reference
encoder, the contract must reject or normalize it before canonical encoding.

The outer carrier records the identity of those exact payload bytes and any
cryptographic wrappers applied to them.

```text
canonical_payload
→ deterministic serialization domain

canonical_payload_identity
+ cryptographic_wrappers
→ outer carrier domain
```

The `canonical_payload` must not contain:

```text
its own final-byte digest
its own final-byte size
cryptographic wrappers applied to itself
fields derived from those wrappers
```

This prevents a self-referential serialization and signing relation.

The original Witness policy and attestation envelopes remain exact evidence
inputs referenced from inside `canonical_payload` by their own immutable
identities.

The outer `cryptographic_wrappers` collection describes only wrappers applied
to the PULSEmech canonical output payload. It does not replace or absorb the
original Witness policy and attestation envelope records.

This document does not create either normative schema.

A proposed high-level shape is:

```json
{
  "schema_version": "pulsemech_witness_verification_evidence_carrier_v0",
  "record_type": "pulsemech_witness_verification_evidence_carrier",
  "canonical_payload": {
    "schema_version": "pulsemech_witness_verification_evidence_v0",
    "record_type": "pulsemech_witness_verification_evidence",
    "record_status": "example",
    "record_identity": {},
    "pulse_run_binding": {},
    "witness_source_identity": {},
    "subject_binding": {},
    "policy_binding": {},
    "attestation_sources": [],
    "retrieval_records": [],
    "attestation_collections": [],
    "verification_configuration": {},
    "step_results": [],
    "artifact_flow_relations": [],
    "verification_summary": {},
    "content_boundary": {},
    "authority_boundary": {},
    "errors": [],
    "ok": false
  },
  "canonical_payload_identity": {
    "sha256": "<sha256-of-exact-canonical-payload-bytes>",
    "size_bytes": 0
  },
  "cryptographic_wrappers": [],
  "outer_carrier_boundary": {}
}
```

---

## 26. Record provenance branches

The future contract should distinguish:

```text
example
```

from:

```text
observed
```

### Example branch

```text
record_status:
example

fixture_provenance:
required

producer_execution:
not claimed
```

### Observed branch

```text
record_status:
observed

fixture_provenance:
forbidden

exact adapter producer:
required

exact Witness execution:
required

exact current-run binding:
required
```

A checked-in example must not claim that Witness verification actually ran.

---

## 27. PULSE current-run binding

An observed Witness carrier must bind to one exact PULSE subject run.

Required fields include:

```text
PULSE repository
PULSE workflow identity
PULSE workflow run ID
PULSE workflow run number
PULSE workflow run attempt
PULSE subject run key
source commit
source ref
release candidate ID
run mode
artifact subject name
artifact subject SHA-256
```

The adapter must reject:

```text
previous-run Witness result reuse
different release candidate
different source commit
different artifact digest
different PULSE run
different workflow attempt
stale structured result
```

A fresh wrapper report over stale Witness evidence remains stale.

---

## 28. Witness source identity

The future observed carrier must declare one execution mode:

```text
witness_execution_mode:
library_api
or
cli
```

The following identities are required in every observed record:

```text
go-witness module path
go-witness module version
go-witness exact resolved revision
go-witness module content checksum
go-witness go.mod checksum
trusted adapter path
trusted adapter revision
trusted adapter SHA-256
trusted adapter version
execution environment identity
```

When:

```text
witness_execution_mode:
cli
```

these additional fields are required:

```text
Witness CLI repository
Witness CLI human-readable ref
Witness CLI exact resolved revision
Witness CLI reviewed-source manifest SHA-256, when source review is claimed
Witness CLI binary SHA-256
Witness CLI version, when available
```

When:

```text
witness_execution_mode:
library_api
```

no Witness CLI executable identity is required, and CLI runtime fields must be
absent rather than populated with an unrelated or invented binary identity.

The upstream CLI source review recorded by this document remains a review anchor.
It is not a claim that every future adapter execution must invoke the CLI.

A version string alone is insufficient for any participating executable or
library.

```text
version label
≠
exact participating source or executable identity
```

The producer must not allow the subject repository to select the protected
Witness adapter, go-witness library or participating CLI revision.

---

## 29. Subject binding

The carrier must preserve every subject digest used to seed Witness
verification.

Required relations include:

```text
PULSE release artifact SHA-256
=
Witness verification subject SHA-256
```

For directory subjects, the digest construction algorithm and directory-root
identity must also be recorded.

Additional Witness subjects must remain visible.

The adapter must reject:

```text
missing subject
empty subject set
unsupported hash identity
artifact digest mismatch
directory digest mode mismatch
subject added only after verification
```

---

## 30. Policy binding

The carrier must record:

```text
policy envelope path or URI
policy envelope SHA-256
policy envelope size
policy payload exact-byte location or inline bytes
policy payload SHA-256
policy payload size
policy payload type
policy envelope payloadType
decoded policy-envelope payload SHA-256
decoded policy-envelope payload size
envelope-to-policy-payload equality state
policy expiry
verified policy signer key IDs
verified policy signer certificate and chain identities, when X.509 is used
exact matched policy certificate or Fulcio constraints, when used
policy signature-verification method
policy CA roots and intermediates by digest
policy timestamp-authority roots by digest
policy certificate constraints
policy Fulcio constraints
policy KMS verifier configuration identity
```

The adapter and validator must decode the DSSE envelope and establish all of the
following before accepting the policy relation:

```text
base64_decode(policy_envelope.payload)
=
exact separately supplied policy payload bytes

policy_envelope.payloadType
=
recorded policy payload type

SHA-256(base64_decode(policy_envelope.payload))
=
recorded policy payload SHA-256

DSSE PAE signature verification inputs
=
that same payloadType and those same decoded payload bytes
```

The carrier must not embed secret key material.

Trust roots can be embedded only as public verification material or referenced
through exact digests and protected source identities.

The adapter must reject:

```text
unsigned or unverified policy
expired policy at the bound verification event
policy payload-type mismatch
policy envelope digest mismatch
policy envelope decoded payload differs from separately supplied policy payload
policy envelope payloadType differs from separately supplied policy payload type
policy payload digest differs from the decoded envelope payload digest
policy signature verified over a different payloadType or payload byte sequence
unknown policy signer
unbound external policy trust configuration
```

---

## 31. Attestation carrier binding

Every supplied attestation envelope must record:

```text
source kind
source locator
retrieval event identity
original retrieval time
resolved source revision, gitoid or equivalent source identity
exact envelope SHA-256
exact envelope size
attestation payload exact-byte location or inline bytes
payload SHA-256
payload size
payload type
envelope payloadType
decoded envelope payload SHA-256
decoded envelope payload size
envelope-to-attestation-payload equality state
statement predicate type
collection name
statement subjects
verified signer key IDs
verified leaf-certificate identity, when X.509 is used
ordered verified certificate-chain identities, when X.509 is used
exact matched subject, SAN and Fulcio constraint values, when evaluated
timestamp verification state
```

For Archivista, also record:

```text
Archivista endpoint identity
gitoid or source-local reference
retrieved envelope SHA-256
retrieved envelope size
```

The gitoid or source reference does not replace the exact retrieved bytes.

The exact original envelope is an admitted carrier.

```text
original admitted envelope
→ exact bytes
→ exact size
→ exact SHA-256
→ immutable carrier identity
```

For every policy or attestation envelope, the adapter and validator must decode
the DSSE payload and establish:

```text
base64_decode(envelope.payload)
=
exact separately supplied payload bytes

envelope.payloadType
=
separately supplied payload type

SHA-256(base64_decode(envelope.payload))
=
recorded payload SHA-256

DSSE PAE signature verification inputs
=
that same payloadType and those same decoded payload bytes
```

A valid signed envelope paired with different separately supplied payload bytes
or a different payload type is not one evidence relation.

A second signed Witness envelope containing the same Witness attestation payload
is a different upstream evidence carrier.

```text
same Witness attestation payload
+ different signed Witness attestation envelope
→ distinct upstream evidence carrier
→ different canonical PULSEmech input state
→ different PULSEmech canonical result identity
```

The second envelope may be acceptable as new evidence for the same Witness
attestation payload only after independent verification of its own signature,
certificate, timestamp, transparency state and functionary authorization.

It does not preserve the earlier PULSEmech canonical-result identity because the
exact original envelope bytes, digest, size and retrieval identity are canonical
inputs.

```text
same Witness attestation payload identity
≠
same PULSEmech canonical result identity
```

Only wrappers generated around an already constructed PULSEmech canonical
output payload belong to the variable outer-wrapper domain.

The adapter must preserve rejected collections.

```text
rejected evidence
≠
discarded evidence
```

### Original and replay retrieval metadata

Every retrieval field represented in the canonical structured output is part of
the deterministic input state.

The original retrieval metadata must be preserved as recorded input:

```text
original source kind
original source locator
original resolved source identity
original retrieval event identity
original retrieval time
original retrieved carrier digest
original retrieved carrier size
```

A replay may also create new retrieval metadata.

That metadata is a new observation and must remain separate:

```text
original retrieval metadata
≠
replay retrieval metadata
```

A replay must not overwrite or silently substitute the original retrieval
record.

If the canonical output includes original retrieval metadata, reproducing the
same canonical payload requires supplying those exact original values as replay
inputs.

---

## 32. Verification configuration binding

The carrier must preserve every input that can alter Witness verification:

```text
subject digests
attestation file set
attestation source set
Archivista enabled state
search depth
policy public-key verifier identities
policy CA roots
policy CA intermediates
policy timestamp authorities
certificate common-name constraints
certificate DNS constraints
certificate email constraints
certificate organization constraints
certificate URI constraints
Fulcio extension constraints
KMS verifier-provider configuration identity
verification event time
all original retrieval metadata represented in the canonical output
```

A pass under one configuration must not be replayed as a pass under another.

A change in output-carried retrieval metadata is a change in canonical input
state.

---

## 33. Structured StepResults

Each policy step must produce a deterministic record.

Required fields include:

```text
step name
required attestation types
allowed functionary identities
accepted collection identities
rejected collection identities
rejection reasons
warnings
Rego policy identities
Rego evaluation results
functionary match mode: public_key or x509
verified signer key identities
verified leaf-certificate identity, when X.509 is used
ordered verified certificate-chain identities, when X.509 is used
verified trust-anchor identity, when X.509 is used
exact policy constraint identities
exact certificate, SAN or Fulcio values matched by those constraints
functionary-match result
step result
```

The record must preserve all reasons.

It must not stop at the first human-readable error.

The step result is derived.

It is not a self-declared boolean.

---

## 34. Explicit artifact-flow relation records

Every `artifactsFrom` relation must be materialized as an explicit edge.

Proposed edge fields:

```text
downstream step
upstream declared step
downstream collection identity
upstream collection identity
overlapping artifact paths
upstream product digest sets
downstream material digest sets
digest algorithm
match result
edge status
errors
```

Possible edge statuses include:

```text
verified
no_upstream_collection
no_artifact_overlap
digest_mismatch
ambiguous_multiple_matches
unresolved
```

A Witness pass can remain a Witness pass when one qualifying upstream candidate
exists.

PULSEmech may still record:

```text
multiple qualifying candidates
→ ambiguous relation
```

if unique transition identity is required for a later purpose.

---

## 35. Verification time and policy expiry

Witness policy expiry is time-dependent.

A reproducible record must distinguish:

```text
verification event time
policy expiry time
policy valid at verification event
replay time
policy valid at replay time
```

Historical replay must not silently change the meaning of a previously valid
verification merely because the replay occurs after policy expiry.

The record should preserve:

```text
original verification result
+
original event-time binding
+
current admissibility result
```

as separate states.

Where RFC3161 timestamp evidence exists, its exact identity must be preserved.

---

## 36. Verification outcome

The structured result should use explicit states:

```text
PASSED
FAILED
ERROR
```

The canonical payload result must include:

```text
VerificationSummary predicate type
verification result
verification time
complete StepResults
failed steps
accepted evidence count
rejected evidence count
artifact-flow result
policy verification result
errors
```

The outer carrier must separately record:

```text
canonical structured payload SHA-256
canonical structured payload byte size
cryptographic wrapper records, when present
```

The canonical payload must not contain its own final-byte identity or its own
output-wrapper records.

Process exit code is recorded separately:

```text
process_exit_code
```

The exit code does not replace the structured result.

---

## 37. Result-producer trust

A future PULSEmech adapter must not parse Witness human logs.

The preferred implementation is:

```text
small pinned trusted adapter
→ imports exact go-witness revision
→ calls structured verification API
→ emits canonical PULSEmech Witness payload
→ binds that payload into the separate outer carrier
```

A second possible upstream improvement is:

```text
Witness CLI
→ native stable machine-readable verification output
```

Until such a stable output exists, the PULSEmech adapter should use the
structured library result.

The structured result must be:

```text
signed
```

or:

```text
produced by a protected exact-revision producer
+
bound to current-run provenance
+
carried by an authenticated artifact
```

An unsigned result produced by untrusted subject code is inadmissible.

When the structured result is signed, timestamped or transparency-logged, the
adapter must verify the wrapper-to-payload relation explicitly.

The canonical structured payload is the deterministic object.

Independent signing events may legitimately produce different wrapper bytes
because of:

```text
signature randomness or signer implementation
certificate issuance
RFC3161 timestamp tokens
transparency-log entries and inclusion material
wrapper ordering or non-semantic metadata permitted by the wrapper contract
```

Such variability does not permit payload substitution.

Every accepted wrapper must verify against the exact canonical payload bytes or
payload digest recorded by the outer PULSEmech carrier.

---

## 38. Content boundary

The proposed carrier should remain metadata- and verification-record-focused.

```text
contains private keys:
false

contains secret tokens:
false

contains raw protected credentials:
false

contains artifact payloads:
false by default

contains exact external carrier digests:
true

contains exact policy and attestation identities:
true

contains original retrieval metadata inside canonical payload:
true

canonical payload contains its own final-byte identity:
false

canonical payload contains output-wrapper identities:
false

outer carrier contains canonical structured payload identity:
true

outer carrier contains cryptographic wrapper identities:
true when wrappers are present

canonical payload contains structured verification results:
true
```

Original DSSE envelopes may remain external carrier files referenced by digest.

A replay must materialize and consume their exact bytes before verifying DSSE
signatures, certificates, timestamps or transparency bindings.

An envelope identity without the corresponding exact signed bytes is not a
complete replay input.

---

## 39. Authority boundary

The proposed carrier must fix:

```text
writes_subject_repository:
false

mutates_witness_attestations:
false

mutates_witness_policy:
false

changes_pulse_policy:
false

creates_pulse_release_decision:
false

activates_pulse_gate:
false

creates_release_authority:
false

witness_verification_is_pulse_release_authority:
false

witness_process_exit_is_pulse_release_authority:
false

authority_effect:
none
```

---

## 40. Anti-confusion rules

The following distinctions are normative for this design:

```text
Witness policy
≠
PULSE release policy

Witness step
≠
PULSE gate

Witness functionary
≠
PULSE release authority

Witness attestation
≠
admitted PULSE evidence

Witness signature
≠
truth of the attested fact

Witness artifactsFrom PASS
≠
complete downstream release-transition closure

Witness VerificationSummary PASSED
≠
PULSE final status

witness verify exit 0
≠
PULSE primary CI ALLOW

Archivista storage
≠
verification

SLSA export
≠
full Witness policy-verification carrier

successful candidate proof
≠
release-required promotion
```

---

## 41. Proposed non-active candidate checks

A later implementation may introduce a non-active Witness candidate set.

A possible name is:

```text
witness_verified_supply_chain_candidate
```

No such set is registered by this document.

Possible derived candidate checks are:

```text
witness_verification_evidence_present
witness_current_run_binding_ok
witness_source_identity_bound
witness_subject_binding_ok
witness_policy_binding_ok
witness_attestation_signatures_ok
witness_functionary_binding_ok
witness_step_requirements_ok
witness_rego_policies_ok
witness_artifact_flow_ok
witness_verifier_binding_ok
witness_structured_result_carrier_ok
witness_verification_result_passed
```

The generic PULSE checker must not hardcode these names.

Any future gate values must be derived through:

```text
structured Witness carrier
→ strict validator
→ deterministic admission report
→ separate status fold-in
→ policy-derived candidate require list
→ generic check_gates.py
```

The forbidden path is:

```text
witness exit 0
→ manual true values in status.json
```

---

## 42. Existing SLSA/VSA lane relation

Witness can export a SLSA provenance predicate.

That export may be evaluated through the existing PULSE SLSA/VSA path if all
existing contracts are satisfied.

The existing candidate gates include:

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

The Witness-specific policy-verification state contains additional semantics:

```text
functionaries
required attestation collections
Rego results
artifactsFrom relations
complete StepResults
```

Those additional semantics must not be silently discarded when full Witness
verification is the intended evidence object.

---

## 43. Admission result states

A future PULSEmech Witness admission report should distinguish:

```text
source_record_valid
policy_signature_verified
policy_valid_at_event_time
attestation_signatures_verified
subject_bound
functionaries_authorized
step_requirements_satisfied
artifact_flow_verified
witness_verification_passed
current_run_bound
admission_eligible
```

No single top-level `ok` field may erase the independent failure axes.

The report can carry:

```text
ok:
true or false
```

only as a derived terminal construction state.

---

## 44. Required rejection cases

A future strict implementation must reject at least:

```text
missing Witness policy
malformed policy DSSE envelope
invalid policy signature
policy envelope decoded payload differs from separately supplied policy payload
policy envelope payloadType differs from separately supplied policy payload type
unknown policy signer
expired policy at verification event
zero-step policy
step with no required attestations
collection name mismatch
missing required attestation type
malformed attestation DSSE envelope
unsigned attestation envelope
cryptographically invalid attestation signature
attestation envelope decoded payload differs from separately supplied attestation payload
attestation envelope payloadType differs from separately supplied attestation payload type
unauthorized functionary
missing verified signer identity
X.509 functionary match without exact leaf-certificate and chain identities
X.509 functionary match without exact matched subject, SAN or Fulcio values
failing Rego result
duplicate attestation type with one violating instance
missing subject digest
subject digest mismatch
empty subject set
no artifactsFrom overlap
artifact digest mismatch
unbound search-depth change
unbound attestation-source change
source-local reference collision
modified attestation envelope
modified policy envelope
policy-envelope identity present but exact original signed envelope bytes unavailable
attestation-envelope identity present but exact original signed envelope bytes unavailable
stale Witness result
previous-run result reuse
PULSE current-run mismatch
untrusted adapter source
library_api mode with invented CLI runtime identity
cli mode with missing exact CLI source or binary identity
logs-only verification input
exit-code-only verification input
unsigned unprotected structured result
incomplete StepResults
discarded rejected collections
ambiguous artifact-flow mapping represented as unique
mutable upstream ref without resolved commit
Go module checksum mismatch
non-Go downloaded review source without content digest
cryptographic output wrapper whose PULSE canonical payload binding does not match
canonical payload containing its own final-byte digest or size
canonical payload containing output-wrapper records
original retrieval metadata overwritten by replay metadata
output-carried retrieval metadata omitted from replay input
manual status boolean input
```

---

## 45. Determinism and replay requirements

Identical canonical inputs must produce byte-identical canonical structured
payload bytes.

The deterministic object is:

```text
canonical PULSEmech Witness structured payload
```

It is not automatically:

```text
an independently regenerated signature envelope
an independently issued certificate
an independently generated RFC3161 timestamp token
an independently created transparency-log record
```

Required canonical inputs include:

```text
exact trusted adapter and go-witness library source identities
exact Witness CLI source and binary identity only when CLI participation is declared
exact artifact subject
exact policy payload bytes and payload type
exact original signed policy-envelope bytes and immutable identity
exact attestation payload bytes and payload types
exact original signed attestation-envelope bytes and immutable identities
exact envelope-to-payload equality results for policy and every attestation
exact trust configuration
exact public-key or X.509 functionary-match evidence
exact verification configuration
exact verification event time
exact PULSE run binding
all original retrieval metadata represented in the output
```

The original signed policy- and attestation-envelope bytes are canonical replay
inputs even when those envelopes are stored as external carriers.

The canonical payload may record their immutable identities and external
locations, but replay must materialize and consume the exact referenced
envelope bytes.

```text
envelope digest and size
without the exact signed envelope bytes
→ insufficient for DSSE signature, certificate or timestamp replay
```

This requirement applies to the original upstream Witness evidence envelopes.

For the policy envelope and every attestation envelope, replay must establish:

```text
decoded envelope payload bytes
=
separately supplied exact payload bytes

envelope payloadType
=
separately supplied exact payload type

recorded payload SHA-256
=
SHA-256(decoded envelope payload bytes)

DSSE signature verification
→ uses that same payloadType and those same decoded payload bytes
```

A re-signed or replaced upstream Witness envelope is a new canonical input and
therefore produces a different PULSEmech canonical result, even when the
underlying Witness policy or attestation payload bytes are unchanged.

New cryptographic wrappers generated around the already constructed PULSEmech
canonical output payload remain in the outer carrier domain and are not part of
canonical payload determinism.

For identical canonical inputs:

```text
canonical structured payload bytes A
=
canonical structured payload bytes B
```

and:

```text
canonical structured payload SHA-256 A
=
canonical structured payload SHA-256 B
```

### Cryptographic wrapper rule

This rule applies only to wrappers generated around an already constructed
PULSEmech canonical output payload.

It does not authorize replacement or re-signing of the original upstream
Witness policy or attestation envelopes without changing the canonical input
and result identity.

An independently generated PULSEmech output wrapper may differ byte-for-byte.

Allowed causes of output-wrapper variation include:

```text
signature bytes
certificate material
trusted timestamp material
transparency-log entry and inclusion material
explicitly non-semantic wrapper metadata
```

Output-wrapper variability is acceptable only when each wrapper independently
proves:

```text
payload type matches the PULSEmech canonical output type
exact PULSEmech canonical payload bytes or digest match
signature verifies
signer satisfies the selected trust policy
timestamp state satisfies the selected policy, when required
transparency state satisfies the selected policy, when required
```

Therefore:

```text
byte-identical PULSEmech canonical output payload
+
separately valid output-wrapper-to-payload binding
→ deterministic semantic reproduction
```

It does not imply:

```text
byte-identical independently generated PULSEmech output wrappers
```

```text
PULSE output wrapper W1 exact bytes
may equal or differ from
PULSE output wrapper W2 exact bytes
```

If two output wrappers differ in exact bytes, they are different carrier
artifacts.

If two output wrappers are byte-identical, they share the same content identity,
while their production-event provenance may still be recorded separately.

Either case may bind the same PULSEmech canonical output payload identity only
when the output-wrapper-to-payload relation independently verifies.

By contrast:

```text
original upstream Witness envelope E1
replaced or re-signed as E2
→ new upstream evidence carrier
→ new canonical PULSEmech input state
→ new PULSEmech canonical result identity
```

### Retrieval metadata rule

Original retrieval metadata that appears in the canonical payload is part of the
replay input.

```text
original retrieval metadata
→ fixed canonical input

replay retrieval metadata
→ new observation
```

A new retrieval event must not silently replace the original event.

If a new external condition prevents exact reproduction, the replay must emit an
exact deterministic explanation of that changed condition rather than altering
the original input record.

### Network boundary

Network retrieval should occur before the final PULSE admission decision.

The terminal release decision should consume materialized, digest-bound
carriers.

```text
live network lookup during terminal gate enforcement
→ not required
```

---

## 46. Proposed implementation sequence

### PR 1 — boundary document

```text
docs/slsa/
PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md
```

Status after merge:

```text
mechanical mapping documented
implementation absent
authority effect none
```

### PR 2 — canonical payload and outer carrier schemas and example

Possible files:

```text
schemas/pulsemech_witness_verification_evidence_v0.schema.json

schemas/pulsemech_witness_verification_evidence_carrier_v0.schema.json

examples/slsa/
pulsemech_witness_verification_evidence_example_v0.json

tests/
test_pulsemech_witness_verification_evidence_schema_v0.py
```

Status:

```text
contract only
no producer
no gate
```

### PR 3 — strict carrier validator

Possible files:

```text
tools/check_pulsemech_witness_verification_evidence_v0.py

tests/
test_check_pulsemech_witness_verification_evidence_v0.py
```

The validator must verify:

```text
outer carrier shape
canonical payload shape
exact repository canonical JSON byte procedure
cross-language canonical-byte conformance
canonical payload serialization boundary
canonical payload identity over exact payload bytes
absence of self-derived payload identity and output-wrapper fields inside the payload
PULSE output-wrapper-to-canonical-payload binding
source identities
execution-mode consistency
mandatory adapter and go-witness identities
conditional CLI identity when CLI participation is declared
subject binding
policy binding
exact original signed policy-envelope byte availability and identity
policy envelope decoded payload bytes and payloadType equal separately supplied policy inputs
exact original signed attestation-envelope byte availability and identities
every attestation envelope decoded payload bytes and payloadType equal separately supplied attestation inputs
attestation signature validity independent of functionary authorization
attestation carrier identities
public-key or complete X.509 functionary-match evidence
structured StepResults
artifact-flow relations
time binding
authority boundary
```

### PR 4 — trusted structured adapter

Preferred implementation:

```text
small Go adapter
→ pinned go-witness revision
→ library_api execution mode
→ structured VerifyResult
→ exact canonical-JSON byte conformance
→ canonical PULSEmech Witness payload
→ separate outer carrier
```

A CLI-backed adapter is also permitted when it declares:

```text
witness_execution_mode:
cli
```

and binds the exact participating CLI source and binary identity.

The adapter must not parse human logs.

### PR 5 — generated observed proof

```text
exact fixture artifact
+ exact policy payload bytes and payload type
+ exact original signed policy-envelope bytes
+ verified policy envelope-to-payload equality
+ exact attestation payload bytes and payload types
+ exact original signed attestation-envelope bytes
+ verified attestation envelope-to-payload equality
+ exact trust configuration
+ exact public-key or X.509 functionary-match evidence
+ exact original retrieval metadata
→ machine-produced canonical payload
→ separate outer carrier construction
→ strict validator
→ pinned adapter replay
→ byte-identical canonical structured payload
→ independently verified PULSE output-wrapper-to-payload binding, when wrapped
```

### PR 6 — non-active candidate surface

Only after the carrier and replay proof are complete:

```text
register non-active candidate checks
→ deterministic fold-in
→ policy-derived candidate require list
→ generic strict checker
```

### PR 7 — connected candidate proof

```text
Witness execution
→ structured carrier
→ PULSE admission report
→ candidate fold-in
→ candidate-only strict check
```

### PR 8 — current-run workflow integration

Only after the complete candidate path is proven.

### PR 9 — separate promotion decision

Any movement to:

```text
advisory
required
release_required
```

must be a separate policy PR.

---

## 47. Required regression proof

A complete regression suite must include:

```text
valid signed policy and attestation set passes
invalid policy signature fails
policy envelope paired with different separately supplied payload fails
policy envelope payloadType mismatch fails
expired policy fails at bound event time
historical event-time replay remains explicit
zero-step policy fails
empty required-attestation list fails
wrong collection name fails
missing attestation type fails
malformed attestation DSSE envelope fails
unsigned attestation envelope fails
cryptographically invalid attestation signature fails
attestation envelope paired with different separately supplied payload fails
attestation envelope payloadType mismatch fails
cryptographically valid but unauthorized attestation signer fails
X.509 functionary record without exact leaf and chain identities fails
X.509 subject, SAN or Fulcio matched-value mismatch fails
one violating duplicate attestor fails
Rego denial reason preserved
no artifact overlap fails
artifact digest mismatch fails
multiple qualifying artifact sources remain visible
all rejected collections remain visible
source-local reference collision does not merge distinct content
identical content from multiple sources deduplicates deterministically
subject digest mismatch fails
PULSE run mismatch fails
stale result fails
search-depth substitution fails
trust-root substitution fails
library_api mode succeeds without a Witness CLI binary identity
library_api mode with invented CLI participation fails
cli mode without exact CLI source and binary identity fails
logs-only input fails
exit-code-only input fails
untrusted adapter fails
mutable upstream ref without resolved commit fails
Go module checksum mismatch fails
non-Go downloaded review source without content digest fails
policy replay with envelope identity but missing exact original signed bytes fails
attestation replay with envelope identity but missing exact original signed bytes fails
external original signed envelope bytes are materialized and consumed
repository canonical JSON test vectors are byte-identical across Python and Go
non-ASCII, escape, control-character and numeric canonicalization vectors pass
canonical structured payload is byte-deterministic
canonical structured payload digest is stable
canonical payload serialization excludes its outer identity and output wrappers
canonical payload cannot contain a self-derived digest, size or output-wrapper record
mutation of outer-carrier fields outside canonical_payload leaves canonical payload bytes and digest unchanged
mutation of canonical_payload changes its digest or causes stale-identity rejection
original admitted upstream Witness envelopes remain byte-exact and digest-bound
re-signing an upstream Witness policy or attestation envelope creates a new PULSEmech canonical result identity
independently generated PULSE output wrappers may be byte-identical or byte-different
independently generated PULSE output wrappers bind the same canonical payload digest
PULSE output-wrapper payload substitution fails
timestamp variation in a PULSE output wrapper does not alter canonical payload identity
transparency-log variation in a PULSE output wrapper does not alter canonical payload identity
original retrieval metadata is a canonical replay input
replay retrieval metadata remains a separate observation
original retrieval metadata cannot be overwritten by replay metadata
changing output-carried retrieval metadata changes the canonical payload or fails
protected inputs remain byte-identical
repository remains clean
candidate path remains non-active
generic check_gates.py remains unchanged
```

The regression must test canonical payload determinism and cryptographic wrapper
handling as separate properties.

```text
payload determinism test
≠
wrapper byte-identity test
```

A valid regression may generate byte-identical or byte-different PULSEmech
output wrappers.

Each accepted output wrapper must independently verify and bind the same
PULSEmech canonical payload identity.

Mutation of outer-carrier fields outside `canonical_payload`, such as output
wrapper metadata, must not alter the canonical payload bytes or digest.

Mutation of the `canonical_payload` member must change the recomputed canonical
payload identity, or a stale `canonical_payload_identity` must cause rejection.

The canonical payload bytes must remain unchanged only by operations that stay
outside the canonical payload serialization domain.

---

## 48. Security boundary

The adapter and validator must treat these as separate trust domains:

```text
subject repository
protected PULSE control plane
Witness binary or library
Witness policy signer
Witness attestation functionaries
attestation storage
network retrieval
PULSE evidence-admission verifier
PULSE terminal release authority
```

No one domain may self-assert all identities required to accept itself.

The subject repository must not select:

```text
trusted adapter revision
trusted Witness revision
trusted PULSE admission policy
trusted verifier roots
release-required promotion state
```

---

## 49. No current activation

At the time of this document:

```text
Witness canonical payload schema:
not implemented

Witness outer carrier schema:
not implemented

Witness strict carrier validator:
not implemented

Witness trusted structured adapter:
not implemented

Witness observed replay proof:
not implemented

Witness candidate gate set:
not registered

Witness current-run workflow:
not implemented

Witness release-required enforcement:
not active

PULSE release-authority effect:
none
```

The existing SLSA/VSA candidate path remains unchanged.

---

## 50. Interoperability status

The Witness relationship is now classified as:

```text
semantic overlap:
strong

software-supply-chain transition evidence:
implemented upstream by Witness

signed attestation carrier:
implemented upstream by Witness

signed Witness policy:
implemented upstream by Witness

functionary and attestation verification:
implemented upstream by Witness

artifact-flow verification:
implemented upstream by Witness

Witness structured PULSE carrier:
specified by this document, not implemented

Witness-to-existing-SLSA/VSA export mapping:
possible, not proven by this document

full Witness-policy-verification mapping:
specified, not implemented

lossless downstream PULSE release-transition carrier:
not established

release-required activation:
none
```

This is more precise than treating all in-toto interoperability as one
undifferentiated hypothetical relation.

Witness provides a strong identified upstream evidence and verifier surface.

The complete downstream PULSEmech authority mapping remains unimplemented.

---

## 51. Mechanical conclusion

Witness and PULSEmech are complementary machines.

```text
Witness
→ observes software-supply-chain execution
→ normalizes evidence into versioned attestations
→ signs evidence carriers
→ verifies functionaries, policy, Rego and artifact flow
```

```text
PULSEmech
→ admits authenticated upstream evidence
→ binds it to the exact current release subject
→ materializes the selected PULSE release policy
→ verifies complete gate state
→ produces the terminal release transition
```

The correct composition is:

```text
Witness signed evidence
+ Witness structured verification result
→ PULSEmech Witness admission
→ non-active candidate proof
→ separate policy promotion
→ PULSEmech release-authority path
```

The incorrect composition is:

```text
witness verify exit 0
→ PULSEmech ALLOW
```

The core boundary is:

```text
Witness verifies the software-supply-chain evidence relation.

PULSEmech determines whether admitted evidence may create the release
transition.
```
