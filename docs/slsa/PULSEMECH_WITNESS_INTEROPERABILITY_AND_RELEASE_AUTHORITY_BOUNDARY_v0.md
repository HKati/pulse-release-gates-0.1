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

upstream_cli_reviewed_main_revision:
69402a9a630bb0a06fe969786f7f7db30d0a01a0

upstream_library_repository:
in-toto/go-witness

upstream_library_reviewed_ref:
v0.12.0

upstream_cli_go_witness_dependency:
github.com/in-toto/go-witness v0.12.0

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

## 2. Reviewed upstream source identity

The upstream review was performed against exact public source identities.

### Witness CLI repository

```text
repository:
in-toto/witness

reviewed main revision:
69402a9a630bb0a06fe969786f7f7db30d0a01a0
```

Reviewed surfaces include:

```text
README.md
docs/about/how-witness-works.md
docs/concepts/attestor.md
docs/concepts/policy.md
docs/tutorials/getting-started.md
cmd/run.go
cmd/verify.go
internal/policy/policy.go
go.mod
GOVERNANCE.md
MAINTAINERS.md
SECURITY.md
```

### go-witness library

```text
repository:
in-toto/go-witness

reviewed ref:
v0.12.0
```

Reviewed surfaces include:

```text
run.go
verify.go
policy/policy.go
policy/step.go
attestation/factory.go
```

### Dependency relation

The reviewed Witness CLI revision declares:

```text
github.com/in-toto/go-witness v0.12.0
```

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

It must not reduce the relation to:

```text
functionary_ok:
true
```

without the signer identities that made it true.

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
```

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

A future implementation should define:

```text
schema_version:
pulsemech_witness_verification_evidence_v0

record_type:
pulsemech_witness_verification_evidence
```

The carrier should be a canonical JSON record with external exact-byte
references to the original DSSE envelopes.

This document does not create the normative schema.

A proposed high-level shape is:

```json
{
  "schema_version": "pulsemech_witness_verification_evidence_v0",
  "record_type": "pulsemech_witness_verification_evidence",
  "record_status": "example",
  "record_identity": {},
  "pulse_run_binding": {},
  "witness_source_identity": {},
  "subject_binding": {},
  "policy_binding": {},
  "attestation_sources": [],
  "attestation_collections": [],
  "verification_configuration": {},
  "step_results": [],
  "artifact_flow_relations": [],
  "verification_summary": {},
  "content_boundary": {},
  "authority_boundary": {},
  "errors": [],
  "ok": false
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

The future observed carrier must bind:

```text
Witness CLI repository
Witness CLI exact revision
Witness CLI binary SHA-256
Witness CLI version, when available
go-witness module path
go-witness exact version or revision
trusted adapter path
trusted adapter revision
trusted adapter SHA-256
trusted adapter version
execution environment identity
```

A version string alone is insufficient.

```text
version label
≠
exact executable identity
```

The producer must not allow the subject repository to select the protected
Witness adapter revision.

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
policy payload SHA-256
policy payload type
policy expiry
verified policy signer key IDs
policy signature-verification method
policy CA roots and intermediates by digest
policy timestamp-authority roots by digest
policy certificate constraints
policy Fulcio constraints
policy KMS verifier configuration identity
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
unknown policy signer
unbound external policy trust configuration
```

---

## 31. Attestation carrier binding

Every supplied attestation envelope must record:

```text
source kind
source locator
exact envelope SHA-256
exact envelope size
payload SHA-256
payload type
statement predicate type
collection name
statement subjects
verified signer key IDs
timestamp verification state
source retrieval time
```

For Archivista, also record:

```text
Archivista endpoint identity
gitoid or source-local reference
retrieved envelope SHA-256
```

The gitoid or source reference does not replace the exact retrieved bytes.

The adapter must preserve rejected collections.

```text
rejected evidence
≠
discarded evidence
```

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
```

A pass under one configuration must not be replayed as a pass under another.

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

The result must include:

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
→ emits canonical PULSEmech Witness carrier
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

contains structured verification results:
true
```

Original DSSE envelopes may remain external carrier files referenced by digest.

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
unknown policy signer
expired policy at verification event
zero-step policy
step with no required attestations
collection name mismatch
missing required attestation type
unauthorized functionary
missing verified signer identity
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
stale Witness result
previous-run result reuse
PULSE current-run mismatch
untrusted adapter source
logs-only verification input
exit-code-only verification input
unsigned unprotected structured result
incomplete StepResults
discarded rejected collections
ambiguous artifact-flow mapping represented as unique
manual status boolean input
```

---

## 45. Determinism and replay requirements

Identical canonical inputs must produce byte-identical structured output.

Required inputs include:

```text
exact Witness and adapter source identities
exact artifact subject
exact policy envelope bytes
exact attestation envelope bytes
exact trust configuration
exact verification configuration
exact verification event time
exact PULSE run binding
```

The replay must preserve:

```text
same structured result
or
an exact deterministic explanation of the changed external condition
```

Network retrieval should occur before the final PULSE admission decision.

The release decision should consume materialized, digest-bound carriers.

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

### PR 2 — structured carrier schema and example

Possible files:

```text
schemas/pulsemech_witness_verification_evidence_v0.schema.json

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
canonical record
source identities
subject binding
policy binding
attestation carrier identities
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
→ structured VerifyResult
→ canonical PULSEmech Witness carrier
```

The adapter must not parse human logs.

### PR 5 — generated observed proof

```text
exact fixture artifact
+ exact policy
+ exact attestation collections
+ exact trust configuration
→ machine-produced observed carrier
→ strict validator
→ pinned adapter replay
→ byte-identical output
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
expired policy fails at bound event time
historical event-time replay remains explicit
zero-step policy fails
empty required-attestation list fails
wrong collection name fails
missing attestation type fails
unauthorized signer fails
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
logs-only input fails
exit-code-only input fails
untrusted adapter fails
structured output is byte-deterministic
protected inputs remain byte-identical
repository remains clean
candidate path remains non-active
generic check_gates.py remains unchanged
```

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
Witness structured carrier schema:
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
