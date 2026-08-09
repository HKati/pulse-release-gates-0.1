# PULSEmech — in-toto Layout/Link Transition-Evidence Boundary v0

## WORKMARK

```text
document_role:
mechanical_mapping_and_gap_record

status:
design_and_upstream_source_review_record

review_date:
2026-08-09

pulse_repository:
HKati/pulse-release-gates-0.1

pulse_merged_repository_basis:
0b4f297538d27493f3a4daca71c31f0c8443d5a2

pulse_transition_meter_basis:
PULSEMECH_TRANSITION_METER.md

pulse_existing_slsa_vsa_state:
implemented_and_proven_non_active_candidate

pulse_existing_witness_state:
mechanical_boundary_specified_implementation_absent

upstream_repository:
in-toto/in-toto

upstream_default_branch:
develop

upstream_reviewed_revision:
a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b

upstream_package_version:
3.0.0

upstream_reviewed_surface_manifest_lines:
12

upstream_reviewed_surface_manifest_bytes:
745

upstream_reviewed_surface_manifest_sha256:
7ebf366524ea700745fd7a758861240e27a6d5b560681e9846253cae26bdec27

upstream_signature_dependency_repository:
secure-systems-lab/securesystemslib

upstream_signature_dependency_version:
1.3.1

upstream_signature_dependency_resolved_revision:
6f774190b90f0aa9d5d7e077680adbaa29c5cd6c

upstream_signature_dependency_selection_source:
in-toto/in-toto requirements-pinned.txt at reviewed revision

upstream_signature_dependency_reviewed_surface_manifest_lines:
2

upstream_signature_dependency_reviewed_surface_manifest_bytes:
135

upstream_signature_dependency_reviewed_surface_manifest_sha256:
d2c0056cb1042b3a4df9ac26bc15feb92ab4d2a159e2c52ab0b653530b517eb5

upstream_specification_repository:
in-toto/specification

upstream_specification_reviewed_revision:
6459afd8e94a332e423ba05c2862b534acbe741d

upstream_specification_version:
1.0.0

upstream_specification_reviewed_surface_manifest_lines:
1

upstream_specification_reviewed_surface_manifest_bytes:
57

upstream_specification_reviewed_surface_manifest_sha256:
36a44fc639ec528deb61b6b831f4b4a3ba68bffc82901352c977db4a7a7ca038

upstream_retrieval_method:
github_repository_api_exact_commit_and_blob_reads

upstream_external_downloaded_source_artifact:
none

source_review_scope:
complete_declared_selected_source_surface_not_whole_repository_digest

mapping_status:
mechanical_boundary_specified

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
classic in-toto layout/link verification
```

and:

```text
PULSEmech transition measurement
```

It identifies:

```text
what the in-toto layout declares

what signed link metadata records

what the official verifier checks

what a successful verification establishes

what remains unmeasured or unbound

which PULSEmech Transition Meter fields can be mapped directly

which fields can only be derived

which fields remain unresolved

which execution and trust boundaries require separate control
```

This document does not implement an in-toto integration.

This document does not define a carrier schema.

This document does not define a validator.

This document does not register a candidate gate set.

This document does not modify the existing SLSA/VSA candidate path.

This document does not modify the existing Witness interoperability boundary.

This document does not change release authority.

---

## 1. Purpose

The GitHub recommendation surface exposed the repository:

```text
in-toto/in-toto
```

as a mechanically adjacent project to PULSEmech.

The recommendation is relevant because classic in-toto provides a signed
software-supply-chain structure based on:

```text
project-owner layout

authorized functionaries

signed link metadata

materials

products

artifact rules

thresholds

sublayouts

inspections
```

This structure is close to a transition-evidence mechanism.

It is not identical to the generalized PULSEmech Transition Meter.

The first task is therefore not implementation.

The first task is measurement:

```text
Which transition objects does classic in-toto preserve?

Which transition objects does it not preserve?

Which claims can PULSEmech admit without strengthening them?

Which missing bindings must remain explicit?
```

The purpose of this document is to answer those questions before any schema,
adapter, candidate, workflow, or authority-bearing path is proposed.

---

## 2. Decision summary

The current mechanical decision is:

```text
classic in-toto is relevant to PULSEmech:
yes

classic in-toto carries signed artifact-transition evidence:
yes

classic in-toto is a complete generalized Transition Meter:
no

classic in-toto is equivalent to SLSA/VSA:
no

classic in-toto is equivalent to Witness:
no

the existing SLSA/VSA intake losslessly carries layout/link state:
no

a separate implementation lane is already justified:
not yet

a new carrier schema is defined by this document:
no

a new validator is defined by this document:
no

a new candidate set is registered:
no

the current compute workstream order changes:
no
```

The exact current position is:

```text
classic in-toto
→ strong domain-native upstream transition evidence

classic in-toto verification PASS
→ verified conformance to one exact effective layout under one exact verifier boundary

classic in-toto verification PASS
≠ complete PULSEmech transition identity

classic in-toto verification PASS
≠ PULSEmech release ALLOW
```

---

## 3. Current PULSEmech position

PULSEmech already contains three relevant layers.

### 3.1 SLSA/VSA recorded evidence intake

The existing path is:

```text
recorded SLSA VSA evidence
→ SLSA VSA intake verification
→ intake report
→ status fold-in
→ non-active candidate gates
→ policy-derived candidate require list
→ strict gate checking
```

Its current state is:

```text
implemented:
yes

tested:
yes

non-active candidate proof:
complete

release-required activation:
no
```

The current contract is specifically shaped around an in-toto Statement carrying
a SLSA Verification Summary predicate.

It is not a general lossless carrier for classic layout and link metadata.

### 3.2 Witness interoperability boundary

The existing Witness document records:

```text
Witness attestors
→ signed in-toto attestations
→ signed Witness policy
→ functionary verification
→ required-attestation verification
→ Rego evaluation
→ artifact-flow verification
→ VerificationSummary and StepResults
```

The Witness relation is already identified as a domain-specific
software-supply-chain transition instrument.

Its full structured PULSEmech integration remains unimplemented.

### 3.3 Foundational Transition Meter

The PULSEmech Transition Meter defines the generalized measurement object:

```text
identified source state
→ changed relation
→ opened, closed, or redirected path
→ identified target state
```

bound to:

```text
element-level event time

element-level observation time

measurement identity

evidence identity

verifier identity

system boundary

alternative paths

unresolved edges

reconstruction state

reproduction state

causal state

authority state
```

Classic in-toto must be mapped into this structure without being promoted beyond
the evidence it actually carries.

---

## 4. Three in-toto-related surfaces must remain separate

The word `in-toto` currently appears in several mechanically different
contexts.

They must not be collapsed.

### 4.1 in-toto Attestation Framework and SLSA predicates

This surface provides:

```text
Statement
+
subject
+
predicateType
+
predicate
+
optional signature envelope
```

A SLSA provenance or Verification Summary record can be represented through this
framework.

Its central object is authenticated predicate metadata.

### 4.2 Witness

Witness provides:

```text
attestor lifecycle
+
signed attestation collections
+
signed policy
+
functionary verification
+
required attestation types
+
Rego evaluation
+
artifact-flow relations
+
structured verification result
```

Its policy and verification model are not the classic in-toto layout/link model.

### 4.3 Classic in-toto layout/link verification

Classic in-toto provides:

```text
raw metadata carrier containing a project-owner Layout payload and complete signature inventory
+
wrapper-specific Layout signature input
+
selected matching signature relation for every supplied layout-verification key
+
per-signature status for additional carried records
+
ordered expected steps
+
authorized functionary keys
+
step thresholds
+
raw metadata carriers containing Link payloads and complete signature inventories
+
wrapper-specific Link signature inputs
+
selected matching signer relations for accepted Link candidates
+
per-signature status for additional carried records
+
materials and products
+
artifact rules
+
sublayouts
+
verification-time inspections
```

This is the subject of this document.

The separation rule is:

```text
in-toto Statement
≠ classic in-toto Layout payload

SLSA provenance
≠ signed Link metadata chain

Witness policy
≠ classic in-toto Layout payload

Witness StepResults
≠ classic in-toto summary Link

classic in-toto verification
≠ PULSEmech release transition
```

---

## 5. Reviewed upstream source identity

### 5.1 Classic in-toto implementation source

The reviewed classic in-toto source basis is:

```text
repository:
in-toto/in-toto

human-readable ref:
develop

resolved revision:
a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b

package version:
3.0.0
```

The complete declared selected implementation review surface is exactly the
following canonical path/blob manifest.

Each line is:

```text
<repository-relative path><TAB><Git blob object ID><LF>
```

Lines are sorted lexicographically by repository-relative path.

```text
README.md	22d98a233e7a375c3da8c6781f1f142ccb31be0f
in_toto/__init__.py	6ca9e6636bd222cee0294e79f7a0e7f37e530968
in_toto/in_toto_verify.py	246dac1931bce00d6abb899f12befe6a68598dce
in_toto/models/common.py	510b9d3708c5a500c46ff6ea6d8ce49ebb9025aa
in_toto/models/layout.py	88ff3fa87ec78a33ec42118be1345243909d46d2
in_toto/models/link.py	7ef05ec12099e2d1f16e9685f015c52754176359
in_toto/models/metadata.py	acd6e87aaa854952d4bbed36f59b85166016a695
in_toto/rulelib.py	2e9d2c367d9d0399cfe5caae4a0963c2db0a8f66
in_toto/runlib.py	8207871046a6b0691c2689198d8d87a874520a38
in_toto/verifylib.py	cae4498bb0636c68b814e8b4d8dba5c0cef29b76
pyproject.toml	ed5939c32538e3cd155058cdc74f10e1d00b4a5c
requirements-pinned.txt	8f3fd2facdd5bfd5263cb666642713d1d8f82bc1
```

The exact UTF-8 manifest byte identity is:

```text
lines:
12

bytes:
745

final newline:
present

SHA-256:
7ebf366524ea700745fd7a758861240e27a6d5b560681e9846253cae26bdec27
```

The declared implementation review scope is exactly this manifest.

It is not an open-ended file list.

It is not a whole-repository source audit.

### 5.2 Signature-input dependency source

The exact reviewed in-toto revision pins:

```text
securesystemslib[crypto] == 1.3.1
```

through:

```text
requirements-pinned.txt
```

The signature-input mechanics reviewed by this document cross the repository
boundary into `securesystemslib`.

The dependency source basis is:

```text
repository:
secure-systems-lab/securesystemslib

version:
1.3.1

resolved revision:
6f774190b90f0aa9d5d7e077680adbaa29c5cd6c
```

The complete declared selected dependency review surface is exactly:

```text
securesystemslib/dsse.py	d41abec92618093ef6daba90a1f82fae087b8c40
securesystemslib/formats.py	f6e00e3b1271472c5dbc1b95980637039e18ef02
```

The exact UTF-8 manifest byte identity is:

```text
lines:
2

bytes:
135

final newline:
present

SHA-256:
d2c0056cb1042b3a4df9ac26bc15feb92ab4d2a159e2c52ab0b653530b517eb5
```

This dependency surface covers the two signature-input mechanisms used by the
reviewed in-toto metadata models:

```text
Metablock Signable canonical JSON bytes
→ securesystemslib.formats.encode_canonical(...)

DSSE signature input
→ securesystemslib.dsse.Envelope.pae()
```

It is not a complete audit of `securesystemslib`.

It does not activate or add the dependency to PULSEmech.

### 5.3 in-toto specification source

The reviewed specification basis is:

```text
repository:
in-toto/specification

resolved revision:
6459afd8e94a332e423ba05c2862b534acbe741d

specification version:
1.0.0
```

The complete declared selected specification review surface is exactly:

```text
in-toto-spec.md	84234a889c1b5696a8e526a978146795cf8975b5
```

The exact UTF-8 manifest byte identity is:

```text
lines:
1

bytes:
57

final newline:
present

SHA-256:
36a44fc639ec528deb61b6b831f4b4a3ba68bffc82901352c977db4a7a7ca038
```

### 5.4 Retrieval and reproduction boundary

The review used exact GitHub repository reads bound to immutable revisions and
Git blob identities.

No generated source archive or external downloaded source bundle was used.

A later review reproduces this declared source basis only when it uses:

```text
the same three repositories
+
the same resolved revisions
+
the same canonical path/blob manifests
+
the same manifest byte construction
+
the same manifest SHA-256 identities
```

The source identities recorded here are review anchors.

They are not:

```text
a dependency activation

an installation instruction

a future-version compatibility claim

a claim that every file in any upstream repository was reviewed
```

---

## 6. Classic in-toto system model

The classic in-toto system has three principal participating roles.

### 6.1 Project owner

The project owner defines the intended supply-chain structure in a `Layout`
payload.

The project owner places that payload in a metadata wrapper and creates
signature records over the wrapper-specific signature input derived from the
payload.

The raw metadata carrier and the signature input are separate identities.

### 6.2 Functionary

A functionary performs a named supply-chain step and creates a metadata carrier
containing the resulting `Link` payload.

The functionary signs the wrapper-specific signature input for that `Link`
content.

The functionary is identified through a key authorized by the effective layout.

### 6.3 Client or verifier

The reviewed library verifier receives:

```text
parsed layout metadata

layout verification key or keys

link-directory path containing layout-associated metadata carriers

optional substitution parameters

optional enclosing step name

inspection-link persistence setting

inspection timeout
```

The command-line verifier supplies the layout metadata, layout verification
keys, link directory, and inspection timeout to that library path.

It does not receive a separate current PULSEmech release subject.

The primary verification path is:

```text
project owner defines Layout payload
→ metadata wrapper is constructed
→ wrapper-specific signature input is derived
→ signature records are added
→ functionaries perform steps
→ Link metadata wrappers and signature records are produced
→ verifier parses the raw metadata carriers
→ verifier reconstructs wrapper-specific signature inputs
→ verifier verifies layout and Link signatures
→ verifier derives the effective layout from exact substitution parameters
→ verifier applies thresholds and artifact rules
→ verifier runs inspections where declared
→ verification passes or fails
```

The current-run release subject remains outside this upstream verifier input
surface.

Its binding is a separate PULSEmech relation defined later in this document.

---

## 7. Layout payload, metadata carrier, and signature-input boundary

The `Layout` payload, the raw metadata carrier, and the signature input are
three separate objects.

### 7.1 Layout payload

The `Layout` payload defines a software supply chain through:

```text
steps

inspections

functionary public keys

expiration

human-readable description
```

In the reviewed model, the corresponding payload fields are:

```text
steps

inspect

keys

expires

readme
```

Each step may define:

```text
unique step name

authorized functionary key IDs

threshold

expected command

expected material rules

expected product rules
```

The signatures are not fields inside the `Layout` payload.

### 7.2 Traditional Metablock signature input

A traditional `Metablock` carries:

```text
signed:
Layout payload object

signatures:
signature collection
```

For this wrapper form, the signature input is:

```text
Layout.signable_bytes
```

which the reviewed implementation derives as:

```text
UTF-8(
  securesystemslib.formats.encode_canonical(
    attr.asdict(Layout)
  )
)
```

A Metablock signature therefore authenticates the canonical signed-payload
representation.

It does not authenticate as one byte string:

```text
the complete raw Metablock JSON bytes

the JSON formatting of the wrapper

the signatures collection
```

Reserializing the wrapper or adding another signature can change the raw carrier
bytes while leaving an existing signature input and existing valid signature
unchanged.

### 7.3 DSSE Envelope signature input

A DSSE `Envelope` carries:

```text
payloadType

base64-encoded payload representation in the JSON carrier

signature collection
```

The in-memory envelope contains:

```text
payloadType

decoded payload bytes

signatures
```

For this wrapper form, the signature input is:

```text
PAE(payloadType, decoded payload bytes)
```

The DSSE v1 byte construction contains literal ASCII-space separator bytes.
For the fixed ASCII in-toto payload type, the mechanical construction is:

```text
payload_type_bytes = UTF-8(payloadType)
payload_bytes = decoded payload bytes

PAE =
  b"DSSEv1"
  + b" "
  + ASCII_DECIMAL(BYTE_LENGTH(payload_type_bytes))
  + b" "
  + payload_type_bytes
  + b" "
  + ASCII_DECIMAL(BYTE_LENGTH(payload_bytes))
  + b" "
  + payload_bytes
```

The four `b" "` terms above are literal `0x20` separator bytes.
The length fields are ASCII decimal encodings of byte lengths, not implicit
concatenation and not Unicode code-point counts.

The exact reviewed `securesystemslib` implementation spells the operation as:

```python
b"DSSEv1 %d %b %d %b" % (
    len(self.payload_type),
    self.payload_type.encode("utf-8"),
    len(self.payload),
    self.payload,
)
```

The classic in-toto metadata path fixes the payload type to:

```text
application/vnd.in-toto+json
```

which is ASCII. Under that fixed profile:

```text
len(payloadType string)
=
UTF-8 byte length of payloadType
```

A future classic in-toto adapter must require this exact ASCII payload type or
reject the record as outside the reviewed profile. It must not generalize the
reviewed string-length expression to a non-ASCII payload type.

A DSSE signature therefore authenticates the exact PAE-encoded payload type and
decoded payload bytes.

It does not authenticate as one byte string:

```text
the complete raw Envelope JSON bytes

the chosen outer JSON formatting

the base64 text representation independently from its decoded payload

the signatures collection
```

Reserializing the wrapper or adding another signature can change the raw carrier
bytes while leaving an existing PAE input and existing valid signature
unchanged.

### 7.4 Signature-record verification scope

The exact reviewed layout-signature path does not validate every signature
record carried by the metadata wrapper.

The outer `verify_metadata_signatures(...)` function requires a non-empty
supplied layout-key set and iterates over every supplied verification key.
Each iteration calls the wrapper-specific `verify_signature(...)` path once.
That wrapper call validates only one matching carried signature relation for the
current supplied key.

The first-success return occurs inside the wrapper-specific call for one key.
It does not validate every carried signature record, and it does not short-circuit
the outer loop over the remaining supplied keys.

For a traditional Metablock:

```text
one supplied verification key
→ select the first carried signature record whose key ID matches the key
  or one of its subkeys
→ verify that selected signature over Layout.signable_bytes
→ return for that key invocation
```

For a DSSE Envelope:

```text
one supplied verification key
→ DSSE verify with threshold 1 over the carried signature collection
→ one matching valid signature is sufficient for that key invocation
→ return for that key invocation
```

Consequently, a successful layout-signature phase establishes:

```text
non-empty supplied verification-key set
+
for each supplied layout-verification key
→ one matching carried layout-signature relation validated
   over the wrapper-specific signature input
```

At least one supplied key therefore succeeded because the key set is non-empty.
Under the pinned outer function, PASS additionally requires the same one-matching-
signature relation for every supplied key.

It does not establish:

```text
every signature record carried by the wrapper verified

every additional signer was trusted

every unmatched signature was valid

every invalid additional signature caused failure
```

A raw carrier can therefore contain:

```text
verified signature record or records
+
additional unmatched, untrusted, invalid, or unevaluated signature records
```

while the required supplied-key verification relation still passes.

A future evidence record must preserve the complete carried signature inventory
and a per-record status such as:

```text
verified_for_supplied_key
verification_failed_for_supplied_key
unmatched_to_supplied_keys
not_evaluated_by_upstream_path
```

The upstream PASS may populate only the signature relations it actually
validated. Every other carried signature record must remain explicitly
`not_evaluated_by_upstream_path` unless a separately identified verification
operation checks it.

The same boundary applies to Link and sublayout metadata carriers. Acceptance
of one candidate Link establishes the selected matching signer relation used by
`verify_link_signature_thresholds(...)`; it does not classify every additional
signature record carried by that metadata wrapper.

### 7.5 Required identity separation

A future evidence record must preserve separately:

```text
raw metadata carrier identity:
  wrapper type
  exact raw carrier bytes
  raw carrier SHA-256
  raw carrier size

payload identity:
  payload type
  exact decoded payload bytes where the wrapper provides them
  canonical signed-payload representation where the wrapper requires it
  payload-content identity

signature-input identity:
  signature-input mode
  exact signature-input bytes
  signature-input SHA-256
  signature-input size

signature relation:
  complete carried signature inventory
  verification-key identities
  signature record selected for each supplied key
  per-signature verification status
  verified signer identities
  unevaluated signature identities
  verification result
```

The central boundary is:

```text
raw carrier identity
≠ wrapper-specific signature-input identity
```

and:

```text
valid signature over wrapper-specific input
≠ every raw carrier byte authenticated
```

and:

```text
required supplied-key verification passed
≠ every carried signature record verified
```

and:

```text
same authenticated content
+
different raw wrapper serialization or signature collection
→ different raw evidence carrier
→ not necessarily different effective layout semantics
```

The raw carrier remains an immutable evidence artifact with its own identity.

The signature establishes authenticity only for the wrapper-specific signature
input.

A future adapter must preserve both and must not substitute one identity for the
other.

### 7.6 Planned-path boundary

The layout step list carries the project owner's expected logical arrangement.

It does not, by itself, establish:

```text
the exact event time of each execution

the exact observation time of each Link

that every step actually occurred in wall-clock order

that no undeclared operation occurred between steps

that the layout itself provides sufficient security
```

The exact relation is:

```text
raw layout metadata carrier
→ wrapper parsing
→ wrapper-specific signature-input reconstruction
→ signature verification
→ authenticated Layout content under the wrapper-specific signature semantics
→ optional deterministic substitution
→ effective planned supply-chain structure
```

It is not:

```text
complete observation of the realized transition
```

---

## 8. Link payload, metadata carrier, and signer relation

A classic in-toto `Link` payload records evidence associated with one named step
or inspection.

Its primary fields are:

```text
name

command

materials

products

byproducts

environment
```

The `Link` payload normally appears inside a Metablock or DSSE metadata carrier.

The same identity separation applies:

```text
raw Link metadata carrier
≠ Link payload content identity
≠ wrapper-specific Link signature-input identity
```

The `materials` field records declared input artifacts by path and digest.

The `products` field records declared output artifacts by path and digest.

The `command` field records the command reported for the step.

The `byproducts` field may carry values such as:

```text
stdout

stderr

return value
```

The `environment` field is an opaque mapping for execution-environment
information.

A verified Link relation can establish:

```text
one exact raw metadata-carrier artifact identity
+
one wrapper type
+
one wrapper-specific signature-input identity
+
one verified signer relation
+
one Link payload content authenticated under that wrapper's signature semantics
+
one named step record
+
one declared material set
+
one declared product set
+
reported execution metadata
```

It does not establish that the signature covers every raw carrier byte.

It also does not automatically establish:

```text
complete process observation

complete filesystem observation

complete input dependency discovery

complete output discovery

causal use of every declared material

absence of every undeclared input or output
```

---

## 9. Declared artifact surface is not complete execution observation

Classic in-toto records the artifacts supplied to its recording mechanism.

This creates an explicit measurement boundary.

A file may be used or modified by a command but remain absent from the link when
it was not declared for recording.

A file may also be supplied for recording and appear in the link even when the
command did not mechanically depend on it.

Therefore:

```text
link.materials
≠ complete set of actual execution inputs

link.products
≠ complete set of actual execution outputs

artifact listed as material
≠ artifact causally used

artifact absent from link
≠ artifact absent from execution
```

The correct PULSEmech interpretation is:

```text
signed declared artifact-state observation
```

not:

```text
complete execution-state observation
```

The artifact observation coverage must remain explicit.

A future transition record must preserve at least:

```text
declared material coverage

declared product coverage

recording configuration

known excluded paths

known unobserved paths

coverage limitation state
```

No adapter may silently convert declared artifact coverage into complete process
coverage.

---

## 10. Artifact rules and relation continuity

Classic in-toto defines artifact rules including:

```text
CREATE

DELETE

MODIFY

ALLOW

DISALLOW

REQUIRE

MATCH
```

### 10.1 CREATE

A CREATE rule can establish that an artifact path:

```text
was absent from recorded materials
+
is present in recorded products
```

### 10.2 DELETE

A DELETE rule can establish that an artifact path:

```text
was present in recorded materials
+
is absent from recorded products
```

### 10.3 MODIFY

A MODIFY rule can establish that an artifact path:

```text
is present in materials
+
is present in products
+
has a different digest
```

### 10.4 MATCH

A MATCH rule can establish a relation between artifacts recorded by different
steps or inspections.

The central relation is:

```text
source artifact path
+
source artifact digest
=
destination artifact path
+
destination artifact digest
```

where the effective rule defines the source and destination artifact collections
and any path prefixes.

This is a strong artifact-continuity edge.

It can support:

```text
upstream product
→ downstream material
```

or another explicitly declared cross-step relation.

It does not automatically establish:

```text
unique causal path

wall-clock ordering

complete intermediate-state coverage

absence of another undeclared artifact path

absence of an external side channel

complete transition closure
```

### 10.5 Rule closure depends on the effective layout

Artifact rules consume matching artifact paths from an internal rule queue.

A terminal restrictive rule such as:

```text
DISALLOW *
```

is commonly required to reject artifacts not consumed by preceding rules.

Without adequate restrictive rules, an effective layout may remain permissive.

Therefore:

```text
artifact rule engine available
≠ effective layout is restrictive

layout verification PASS
≠ effective layout policy is adequate
```

---

## 11. Functionary authorization and thresholds

Each effective layout step identifies authorized functionary keys.

Link metadata is accepted for a step only when:

```text
a signature record verifies over the wrapper-specific Link signature input

the verified signing key is authorized for that effective step

the required threshold is met
```

The verifier counts distinct authorized functionary identities subject to its
key and subkey rules.

When a threshold is greater than one, the accepted links for the step must agree
on:

```text
materials

products
```

This provides strong agreement over the declared artifact states.

It does not automatically require agreement over:

```text
reported command

byproducts

environment

execution time

observation time

external side effects
```

Therefore:

```text
threshold satisfied
→ multiple authorized signers agree on declared materials and products
```

but not necessarily:

```text
threshold satisfied
→ independently reproduced complete execution
```

A PULSEmech mapping must preserve the exact threshold semantics.

It must not rename threshold agreement as general independent reproduction.

---

## 12. Sublayouts

A functionary may provide a raw metadata carrier containing a sublayout payload
and signature records instead of a raw carrier containing an ordinary `Link`
payload for a delegated step.

The verifier recursively verifies the sublayout.

A successful sublayout verification is then reduced to a summary `Link` payload
for the parent layout.

This enables hierarchical supply-chain structure:

```text
parent effective layout step
→ delegated raw sublayout metadata carrier
→ wrapper-specific sublayout signature verification
→ nested effective steps
→ verified nested result
→ parent summary Link
```

The hierarchy is useful transition evidence.

The reduction creates an important information boundary.

The parent summary does not carry every nested transition edge directly.

A future PULSEmech mapping must preserve:

```text
exact raw sublayout metadata carrier

exact sublayout wrapper type and signature records

exact sublayout signature-input identity

verified sublayout signer relation

exact authenticated sublayout-content identity

exact nested raw Link carrier tree

exact recursive verifier identity

exact substitution parameters at every recursive level

exact recursively derived effective-layout identities

exact recursive result

parent-to-sublayout delegation relation

summary-Link derivation relation
```

It must not preserve only the reduced parent summary while discarding the
verified nested path.

---

## 13. Inspection execution is a separate authority boundary

Inspections are commands defined in the effective layout and executed by the
verifier during final-product verification.

The official verification path can:

```text
load effective inspection definition
→ execute inspection command in a subprocess
→ record inspection materials and products
→ inspect return value
→ optionally write inspection link metadata
→ apply effective inspection artifact rules
```

This means:

```text
in-toto verification
≠ read-only metadata validation
```

Authenticated Layout content, derived from a raw metadata carrier through
wrapper-specific signature verification and then combined with substitution
parameters, may produce executable effective inspection instructions.

That creates a critical execution relation:

```text
verified wrapper-specific Layout signature input
+
authenticated Layout content
+
exact substitution parameter map
→ effective inspection command
→ verifier-side subprocess
→ filesystem and process effects
```

A future PULSEmech integration must not execute arbitrary admitted inspections
inside a privileged release-authority process without a separately controlled
execution boundary.

A safe future design must explicitly choose one of these modes:

```text
inspection-free effective-layout profile

or

inspection-preserved-but-not-executed profile

or

isolated inspection executor with bounded permissions and recorded effects
```

The exact mode must be part of the evidence record.

Required inspection-boundary fields would include:

```text
inspection presence

inspection execution mode

raw layout metadata-carrier identity

layout signature-input identity

complete carried layout-signature inventory

per-signature verification status

verified supplied-key signer relations

authenticated Layout-content identity

substitution parameter identity

effective inspection identity

executor identity

isolation boundary

network policy

filesystem policy

secret availability

timeout

return state

produced artifacts

persisted inspection-link state
```

This document does not select or implement such a mode.

---

## 14. Official verification procedure

The reviewed official verification function performs these principal activities:

```text
1. require a non-empty layout-verification-key set, iterate over every supplied key, and validate one matching carried signature relation for each key over the reconstructed wrapper-specific layout signature input; additional carried signatures remain unevaluated unless separately checked

2. extract the original Layout payload

3. verify original Layout expiration

4. substitute declared parameters into the extracted Layout object

5. load Link metadata carriers for effective layout steps

6. reconstruct wrapper-specific Link signature inputs, verify the accepted matching signer relation for each candidate Link, and evaluate effective-layout functionary authorization

7. recursively verify sublayouts

8. compare reported commands with effective expected commands

9. verify threshold artifact constraints

10. process effective step material and product rules

11. execute effective inspection commands

12. process effective inspection material and product rules
```

A successful run returns a summary Link.

A failed run raises a typed verification exception.

Relevant failure classes include:

```text
malformed input

required supplied-key layout-signature verification failure

layout expiration

substitution failure

missing link threshold

unauthorized signer or failure of the selected Link signature relation

threshold disagreement

artifact rule failure

inspection command failure
```

This is a strong domain verifier.

PULSEmech must treat it as a domain verifier.

PULSEmech must not silently replace it with a second independent
reimplementation of the same rule system.

### 14.1 Raw carrier, signature-input, and effective-layout identity

The verifier reconstructs the wrapper-specific signature input for the original
Layout content and verifies one matching signature relation for every supplied
layout-verification key before applying substitution.

It then mutates the extracted `Layout` object by applying the exact substitution
parameter map to:

```text
step expected commands

step expected material rules

step expected product rules

inspection commands

inspection expected material rules

inspection expected product rules
```

The complete identity must therefore preserve three layers.

#### Raw evidence-carrier identity

```text
exact raw layout metadata-carrier bytes
+
wrapper type
+
raw carrier SHA-256 and size
+
signature collection as carried
```

This identifies the exact evidence artifact received.

It is not the signature input.

#### Authenticated Layout-content identity

```text
wrapper-specific signature-input mode
+
exact signature-input bytes
+
signature-input SHA-256 and size
+
verification-key identities
+
complete carried signature inventory
+
one selected verified signature relation for each supplied verification key under the pinned outer key loop
+
per-signature verification status for selected and unselected records
+
authenticated Layout content under the wrapper-specific signature semantics
```

For Metablock this is based on canonical `Layout.signable_bytes`.

For DSSE this is based on `PAE(payloadType, decoded payload bytes)`.

#### Effective-layout semantic identity

```text
authenticated Layout-content identity
+
exact substitution parameter map
+
exact pinned substitution implementation identity
→ deterministic effective-layout identity
```

Two verification events can use raw carriers with different byte identities but
the same authenticated Layout content.

They can therefore have:

```text
different raw evidence-carrier identities
+
the same effective layout semantics
```

Two verification events can also use the same authenticated Layout content and
the same Link evidence while applying different substitution maps.

Those events do not verify the same effective path.

```text
same authenticated Layout content
+
different substitution parameter map
→ different effective layout
→ different effective path identity
```

A future adapter must preserve separately:

```text
raw layout carrier identity

wrapper-specific signature-input identity

complete carried layout-signature inventory

per-signature verification status

verified supplied-key signer relations

authenticated original Layout-content identity

substitution parameter identity

deterministically derived effective-layout identity
```

The effective-layout identity must cover the complete substituted semantic
surface used by verification.

It must not be represented only by a display name, raw wrapper digest, or
original payload label.

---

## 15. Command alignment is a soft verification state

The verifier compares:

```text
reported Link command
```

with:

```text
effective expected command
```

The reviewed implementation treats a mismatch as a warning.

It does not necessarily fail the complete verification.

The upstream code also identifies command alignment as a weak guarantee because
commands can be aliased or wrapped.

Therefore:

```text
in-toto verification PASS
≠ exact effective expected command proved
```

A future carrier must distinguish:

```text
reported command present

original expected command present

effective expected command present

substitution parameter identity

command alignment matched

command alignment mismatched

command alignment not evaluated

command alignment effect:
warning_only
```

It must not materialize:

```text
expected_command_verified:
true
```

merely because the overall in-toto verification passed.

---

## 16. The verification output is not a complete structured path report

The public `in_toto_verify(...)` function returns a summary `Link` after
successful verification.

At the exact reviewed upstream revision, `get_summary_link()` explicitly assigns:

```text
materials of the selected first-step representative Link

products of the selected last-step representative Link

byproducts of the selected last-step representative Link

command of the selected last-step representative Link
```

The summary `Link` therefore does carry the selected last-step `byproducts` and
`command`.

Those fields remain the values of one selected representative Link.

They are not automatically threshold-consensus values because threshold
agreement is checked over:

```text
materials

products
```

not over:

```text
command

byproducts

environment
```

This representation is useful for embedding one verified supply chain inside a
parent supply chain.

It is not a lossless record of:

```text
every effective step

every accepted Link carrier

every rejected or ignored Link carrier

every signature result

every threshold result

every artifact-rule result

every sublayout edge

every inspection result

every intermediate material/product relation

every command-alignment warning

every diagnostic
```

Therefore:

```text
successful in_toto_verify return value
≠ complete structured verification result
```

An adapter based only on the returned summary Link would collapse:

```text
complete internal path
→ selected first-step materials
  + selected last-step products
  + selected last-step byproducts
  + selected last-step command
```

That would discard the exact edge-level structure required by the Transition
Meter.

A future record requiring authoritative command or byproduct evidence must
preserve the exact original selected last-step Link carrier and must not infer
threshold-wide agreement from the summary Link.

Human-oriented logs are also insufficient as a normative carrier.

```text
stdout parsing
≠ lossless structured mapping

stderr parsing
≠ lossless structured mapping

process exit 0
≠ complete verification state
```

---

## 17. What a successful classic in-toto verification establishes

Under one exact raw layout metadata carrier, one wrapper-specific layout
signature input, one exact substitution map, one deterministically derived
effective layout, one trust configuration, one Link metadata-carrier set, one
verifier implementation, one inspection environment, and one verification
event, a PASS can establish that:

```text
the supplied layout-verification-key set was non-empty

for each supplied layout-verification key, one matching carried layout-signature relation validated over the reconstructed wrapper-specific signature input

additional carried layout-signature records were not thereby implied verified and remain separately classified per signature

the authenticated original Layout content passed the expiration comparison against the verifier-host UTC clock value read by the pinned verifier during that verification event

the effective layout was derived through the exact substitution parameter map

required Link metadata was found for the effective steps

for every accepted Link candidate, the selected matching signature relation verified over its wrapper-specific signature input; additional carried signature records were not thereby implied verified

accepted Link signers were authorized for their effective steps

effective step thresholds were satisfied

threshold participants agreed on declared materials and products

sublayout verification completed where present

effective artifact rules passed

effective inspections completed where present

the supplied Layout and Link evidence satisfied the complete configured effective-layout verification
```

A PASS is relative to:

```text
exact raw layout metadata-carrier bytes, SHA-256, and size

exact layout wrapper type

exact layout signature-input mode, bytes, SHA-256, and size

complete carried layout-signature inventory

exact verification-key identities

selected matching signature record and verified signer relation for each supplied verification key under the pinned outer key loop

per-signature verification status for every carried signature record

exact authenticated original Layout-content identity

exact substitution parameter map

exact deterministic substitution implementation

exact derived effective-layout identity

exact raw Link and sublayout carrier bytes and identities

exact Link and sublayout signature-input identities

exact accepted signer relations

exact effective artifact-rule set

exact verifier source or executable

exact inspection executor and environment

verification-event time record

verifier-clock acquisition method and source identity

verifier-host UTC clock observation or a bounded observation interval

clock precision, uncertainty, synchronization, and trust state

exact expiration comparison inputs and result

controlled-clock replay mode and control-mechanism identity, where replay is claimed
```

These identities are part of the domain verification state.

The current PULSEmech release subject is not part of this upstream PASS unless a
separate PULSEmech subject-binding relation is established.

---

## 18. What a successful verification does not establish

A classic in-toto PASS does not by itself establish:

```text
that the original or effective layout is secure or adequate

that the effective layout requires code review

that every relevant artifact was recorded

that every actual input was declared

that every actual output was declared

that the reported command equals the effective expected command

that the reported command was the only executed command

that the effective layout step list is a measured wall-clock sequence

that each step carries event-time and observation-time bindings

that no undeclared operation occurred between steps

that no external side channel affected the result

that every functionary acted independently

that all threshold participants used independent infrastructure

that the recorded artifact path is the unique causal path

that every alternative path was excluded

that unresolved edges were preserved as structured state

that every raw metadata-carrier byte was authenticated by its signatures

that the result is current for another run or another artifact

that any separately selected PULSEmech current-run subject matches an accepted in-toto product

that the PULSE release policy is satisfied

that the PULSE required gate set is complete

that final PULSE status is valid

that the PULSE terminal decision is ALLOW
```

The principal boundary remains:

```text
in-toto verification PASS
≠ PULSEmech release ALLOW
```

### 18.1 Current-run release-subject binding is separate

The reviewed `in_toto_verify(...)` interface does not receive a separate current
release artifact or PULSEmech subject argument.

In a layout without inspections, the verifier can pass by evaluating the Layout,
Link metadata, signatures, thresholds, and artifact rules without opening or
hashing the current artifact that PULSEmech intends to release.

Therefore:

```text
accepted final-step product record
≠ current PULSEmech release subject
```

and:

```text
in-toto verification PASS
≠ current-run subject bound
```

The required PULSEmech relation is separate:

```text
exact PULSE current-run subject identity
+
exact current-run repository, workflow, run, attempt, candidate, and source binding
+
exact product-selection rule
+
exact accepted Link or inspection-result reference
+
selected product path and digest
+
subject path and digest equality
→ current-run subject binding
```

A future binding record must preserve at least:

```text
PULSE repository

workflow identity

workflow-run ID

workflow-run attempt

release-candidate identity

source revision

subject artifact path or name

subject digest algorithm and value

selected in-toto step or inspection identity

selected accepted metadata-carrier and payload identity

selected product path

selected product digest algorithm and value

product-selection rule identity

subject-to-product comparison result

stale-evidence result
```

If no exact selection relation exists, the result remains:

```text
subject_binding_status:
unbound
```

If the selected product digest does not equal the current-run subject digest,
the result is rejected and cannot affect authority.

```text
valid historical layout and Link evidence
+
different current-run subject
→ subject binding rejected
→ authority effect none
```

The current-run subject must not be attached to an upstream PASS after the fact
without this exact relation.

---

## 19. Time-binding and verifier-clock gaps

### 19.1 Transition-element time gap

The classic `Link` model does not require explicit edge-level:

```text
event start

event completion

observation start

observation completion

clock identity

time precision

time uncertainty
```

The order of steps in the effective layout expresses expected logical structure.

Artifact `MATCH` relations can provide digest-backed dependency continuity.

Neither automatically provides measured event time.

Therefore:

```text
effective layout order
≠ observed event-time order

artifact dependency
≠ wall-clock sequence

verification-event time
≠ step event time

Link carrier creation time inferred externally
≠ bound observation time
```

The PULSEmech Transition Meter requires each ordered transition element to carry
its own event-time and observation-time bindings.

A classic in-toto mapping must therefore preserve the transition-element time
state as:

```text
unbound

partially_bound

or

externally_bound_by_separate_evidence
```

It must not manufacture transition-element timestamps from:

```text
filesystem modification time

metadata retrieval time

Git commit time

verification-event time

effective layout step index
```

unless the exact meaning and source of that time are separately recorded.

### 19.2 Layout-expiration clock boundary

The pinned verifier performs the expiration check through the mechanical
relation:

```text
parsed Layout.expires
<=
datetime.datetime.now(tz.tzutc())
→ LayoutExpiredError
```

The verifier reads the current UTC value from the verifier host during
execution.

The public verification interface does not accept a verification-time argument.

It also does not return the exact internal clock value read by the expiration
function.

Therefore:

```text
recorded verification-event time
≠ controlled verifier-clock input
```

and:

```text
same raw carriers
+
same verification keys
+
same substitutions
+
same verifier revision
+
different verifier-host clock value
→ potentially different expiration outcome
```

A layout can pass before expiration and fail when the same evidence is replayed
after expiration.

An incorrectly trusted or materially inaccurate host clock can also admit
content that should already be expired or reject content that should still be
valid.

A future evidence record must preserve the clock boundary explicitly:

```text
clock acquisition implementation:
  datetime.datetime.now(tz.tzutc())

clock source identity:
  verifier host and operating-system clock source
  synchronization source where known
  virtualization or clock-control layer where present

clock observation:
  exact UTC value when instrumented
  or
  bounded before-read and after-read UTC interval

clock quality:
  precision
  uncertainty
  synchronization status
  trust status

expiration evaluation:
  exact Layout.expires source value
  parsed expiration instant
  comparison operator
  observed or bounded verifier-clock value
  PASS or expired result
```

If the exact internal read is not instrumented, the record must not invent one.
It may preserve a bounded observation interval around the call and classify the
clock binding as partial.

### 19.3 Controlled-clock replay classes

A later replay must distinguish three mechanically different operations.

#### Full controlled-clock replay

```text
exact verifier revision
+
exact dependency set
+
exact evidence and trust inputs
+
identified isolated clock-control mechanism
+
replay clock fixed to the recorded clock observation
→ attempt to reproduce the original expiration decision
```

The record must bind:

```text
clock-control mechanism identity
clock-control configuration
replay UTC value
clock precision and uncertainty
proof that the verifier process consumed the controlled clock
```

#### Expiration-decision reconstruction

```text
exact parsed Layout.expires
+
recorded clock observation
+
exact comparison rule
→ reconstructed expiration result
```

This can reproduce the comparison result.

It is not a complete end-to-end replay of the unmodified verifier.

#### Uncontrolled current-clock verification

```text
same evidence
+
current host clock
→ new verification event
```

This is a fresh verification under a new time state.

It is not reproduction of the original expiration decision.

If controlled-clock replay cannot be established, the defined reproduction-axis
value must remain one of:

```text
bounded_replay_only
```

or:

```text
not_reproduced
```

The qualification belongs in a separate scope binding, for example:

```text
reproduction_scope:
layout_expiration_component
```

No record may claim exact expiration replay merely because it stored a timestamp
next to the verifier result.

---

## 20. Relation-change mapping

Classic in-toto can provide strong domain-specific relation changes.

The following mappings are possible.

```text
material absent
+
product present
→ artifact creation relation

material present
+
product absent
→ artifact deletion relation

same artifact path
+
different digest
→ artifact modification relation

upstream artifact digest
=
downstream artifact digest
→ artifact continuity relation
```

These can map into Transition Meter elements such as:

```text
artifact_path_created

artifact_path_deleted

artifact_content_modified

artifact_identity_carried_to_downstream_step
```

The mapping remains bounded to:

```text
declared artifact paths

effective rules

recorded digests

accepted Link payloads
```

It does not automatically create a generalized claim such as:

```text
execution capability opened

authority moved

network path opened

dependency became causally active

external state changed
```

Those relation classes require additional domain evidence.

---

## 21. Layout trust root and key-lifecycle boundary

The layout-verification keys are supplied to the verifier from outside the
layout verification procedure.

The exact reviewed path can establish that:

```text
for every supplied layout-verification key
→ one matching carried signature record verifies
   over the reconstructed wrapper-specific signature input
```

For a Metablock, the wrapper path verifies only the first carried signature
record whose key ID matches the supplied key or one of its subkeys.

The outer pinned function repeats this wrapper call for every supplied key.
The first matching signature selected for one key does not classify any other
carried signature record as valid or trusted.

For a DSSE Envelope, the wrapper path invokes threshold-one verification with
one supplied key and accepts one matching valid signature for that invocation.

This does not establish that every signature record in the raw metadata carrier
was verified, valid, or trusted.

It also does not establish that any verified signature authenticates every byte
of the raw metadata carrier.

It also does not independently establish:

```text
why the key is trusted

how the key was obtained

whether the key was revoked elsewhere

whether its usage flags permit this purpose

whether a newer layout supersedes the current Layout content

whether the layout owner remains authorized
```

The reviewed verifier does not rely on external key-attribute services for
creation time, revocation state, or usage flags.

Those trust decisions remain outside the core layout verification.

A future PULSEmech mapping must therefore bind:

```text
layout trust-root source

exact verification-key bytes

verification-key digest

key acquisition record

key authorization policy

verification-event time record

verifier-clock source identity, observation, precision, uncertainty, and trust state

revocation-handling policy

supersession policy

wrapper-specific signature-input identity

complete carried signature inventory

selected matching signature record for each supplied key under the pinned outer key loop

per-signature verification status

verified signature and signer relations
```

A key ID alone is not a complete trust-root identity.

```text
key ID
≠ key bytes

valid signature over wrapper-specific input
≠ every raw carrier byte authenticated

required supplied-key signature verification passed
≠ every carried signature record verified

outer key-loop completion
≠ complete signature-inventory verification

valid signature
≠ current authorization

authenticated Layout content
≠ effective layout current
```

---

## 22. Layout compliance is not layout adequacy

Classic in-toto verifies conformance to the supplied, deterministically derived
effective layout.

It does not determine whether the original or effective layout itself provides
sufficient security, quality, or release policy.

An effective layout may omit:

```text
code review

testing

independent functionaries

restrictive artifact rules

trusted build infrastructure

required inspections
```

and still be internally valid.

Artifact rules can also remain permissive when unconsumed artifacts are not
closed by an adequate terminal restriction.

Therefore:

```text
effective layout valid
≠ effective layout adequate

valid wrapper-specific signature over Layout content
≠ effective layout secure

effective-layout verification PASS
≠ supply-chain risk absent
```

PULSEmech must preserve two distinct objects:

```text
upstream effective-layout conformance
```

and:

```text
PULSE policy adequacy for the requested release transition
```

The first can become evidence for the second.

It cannot replace the second.

---

## 23. Layout freshness and replay boundary

Classic in-toto Layout expiration provides a time limit evaluated against the
verifier-host UTC clock read during the verification event.

The result is clock-relative.

```text
Layout accepted as not expired
≠ Layout intrinsically timeless or replay-stable
```

Expiration alone does not establish:

```text
that no newer authorized Layout-content or metadata-carrier record exists

that the received raw layout carrier or authenticated Layout content is the latest authorized state

that older still-unexpired Layout content was not replayed through another valid carrier

that the selected Layout content and raw carrier were distributed through an authenticated update path
```

The upstream specification identifies secure layout and key distribution as a
separate problem, commonly addressed through a mechanism such as TUF.

For PULSEmech admission:

```text
authenticated original Layout content not expired
≠ current authorized Layout state

wrapper-specific layout signature valid
≠ Layout content selected by current PULSE policy

old valid authenticated Layout content
≠ current authorized effective layout

not expired under one verifier-clock observation
≠ same expiration result under another clock observation

recorded verification-event timestamp
≠ controlled clock consumed by the expiration function
```

A future record must bind the exact expected authenticated Layout-content
identity, raw evidence-carrier identity, exact substitution parameter identity,
verifier-clock boundary, and expiration result through protected PULSE policy or
another authenticated selection mechanism.

---

## 24. Mapping classes

Every classic in-toto field or result must be assigned one of four mapping
classes.

### 24.1 Directly preserved

The upstream evidence surface explicitly carries or yields the object.

Examples:

```text
raw metadata-carrier bytes and identity

wrapper type

signature records

wrapper-specific signature-input identity

verified signer identity

original Layout step name

authorized functionary key IDs

step threshold

material path and digest

product path and digest

reported command

Layout expiration
```

### 24.2 Mechanically derived

The object can be derived from exact preserved upstream records through an
explicit deterministic rule.

Examples:

```text
authenticated Layout-content identity under wrapper-specific signature semantics

effective layout from authenticated Layout content plus substitution parameters

artifact created

artifact deleted

artifact modified

artifact digest continuity

effective layout step sequence index
```

A derived field must preserve:

```text
derivation rule identity

source field identities

signature-input identity where applicable

substitution parameter identity where applicable

result

derivation status
```

### 24.3 Separately supplied

The object is not carried by classic in-toto and must come from separate
evidence.

Examples:

```text
event time

observation time

layout trust-root acquisition

current-layout selection

current PULSEmech run and release-candidate identity

current-run release-subject identity

subject-to-selected-product binding rule

complete runtime input coverage

complete runtime output coverage
```

### 24.4 Unresolved

No admissible evidence establishes the object.

Examples may include:

```text
unique causal path

alternative path exclusion

complete process observation

external side-effect absence

functionary independence
```

An unresolved object must remain unresolved.

---

## 25. Transition Meter mapping matrix

| PULSEmech Transition Meter object | Classic in-toto source | Mapping state | Boundary |
|---|---|---|---|
| `source_state_ref` | Step materials | Direct for declared artifact subset | Not complete process state |
| `target_state_ref` | Step products | Direct for declared artifact subset | Not automatically the current PULSEmech release subject |
| `current_run_subject_binding` | No separate `in_toto_verify(...)` subject input | Separately established by PULSEmech through selected accepted product and digest equality | PASS alone does not bind the current release artifact |
| `relation_before` | Material path and digest set | Derived domain relation | Artifact scope only |
| `relation_after` | Product path and digest set | Derived domain relation | Artifact scope only |
| `changed_relations` | CREATE, DELETE, MODIFY results under the effective layout | Deterministically derivable | Only declared paths and effective rules |
| `ordered_transition_elements` | Ordered effective layout steps | Planned order directly available | Actual event-time order unbound |
| `path_identity` | Authenticated Layout-content identity under wrapper-specific signature semantics + exact substitution parameter map + deterministic effective-layout identity + authenticated Link-content identities + effective rules | Derivable only when all semantic inputs and the derivation procedure are preserved | Raw carrier identities remain separate evidence identities; summary Link alone is insufficient |
| `participating_entities` | Supplied verification keys and accepted Layout/Link signer relations | Direct only for the signature relations actually verified | Key identity is not full authorization provenance; extra carried signatures may remain unevaluated |
| `layout_signature_verification_scope` | Non-empty supplied layout-verification-key set + one selected matching signature relation per supplied key + complete carried signature inventory | Direct and diagnostic | The pinned outer loop requires one matching valid relation for each supplied key; additional carried signatures remain unevaluated unless separately checked |
| `system_boundary` | Raw carriers, authenticated content, effective layout, steps, sublayouts, and verification environment | Partial | General external boundary not encoded |
| `boundary_crossings` | Effective MATCH relations and sublayout delegation | Partial | Domain-specific artifact crossings |
| `event_time_binding` | No required Link field | Unavailable by default | Requires separate evidence |
| `observation_time_binding` | No required Link field | Unavailable by default | Requires separate evidence |
| `record_verification_time_binding` | Verification-event record | Separately recordable | Must not substitute for step time or for the internal clock value consumed by expiration checking |
| `verification_clock_binding` | Verifier-host UTC clock read through `datetime.datetime.now(tz.tzutc())` | Separately instrumented or bounded | Public API does not accept or return the exact clock input; source identity, precision, uncertainty, and trust must remain explicit |
| `layout_expiration_status` | Parsed `Layout.expires` compared with verifier-host clock | Domain result relative to one clock state | Same evidence can PASS before expiry and fail later; controlled-clock replay is separate |
| `measurement_refs` | Raw metadata-carrier identities + wrapper-specific signature-input identities + authenticated payload-content identities | Direct and derived components | No one identity may substitute for the others |
| `evidence_refs` | Raw layout, Link, sublayout, and inspection carriers; signature inputs; complete signature inventories and per-record statuses; substitutions; clock-bound expiration inputs; accepted result references | Direct | Full evidence, effective-layout derivation, signature-selection, and clock-boundary tree required |
| `domain_verifier_binding` | Exact in-toto verifier and exact signature-input dependency source | Separately bound | Version label alone is insufficient |
| `transition_verifier_binding` | Future PULSEmech mapper/verifier | Not implemented | Must remain separate from in-toto |
| `alternative_paths` | No native complete model | Unresolved by default | Must not be inferred from one passing effective layout |
| `excluded_paths` | Some effective artifact-rule exclusions | Partial | Not general alternative-path closure |
| `remaining_admissible_paths` | Not represented | Unresolved | Requires separate analysis |
| `unresolved_edges` | Failures and missing evidence | Partial | Not persisted as multiaxial record by default |
| `reconstruction_method` | Exact verifier replay plus signature-input reconstruction, effective-layout derivation, and mapping rule | Future derived record | Not yet implemented |
| `reproduction_status` | Exact replay may be possible only under controlled signature, substitution, inspection, environment, and clock boundaries | Bounded | A current-clock rerun is a new verification event; exact expiration replay requires a controlled clock or remains unreproduced |
| `causal_status` | Not a classic in-toto object | `not_evaluated` or `sequence_only` maximum by default | No causal promotion |
| `authority_status` | Not a classic in-toto object | `none` | PULSEmech controls authority separately |
| `authority_effect` | None | Direct PULSE boundary | Verification does not create release authority |

---

## 26. Default multiaxial status constraints

A successful classic in-toto verification must not be flattened into one status
such as:

```text
transition_verified
```

A normalized PULSEmech interpretation must preserve independent axes.

### 26.1 Observation status

For the declared artifact surface:

```text
partially_observed
```

may be appropriate when materials and products were captured around a step.

It must not become:

```text
directly_observed_complete_transition
```

unless complete observation coverage is separately proven.

### 26.2 Binding status

Artifact identities may be:

```text
bound
```

while event time, verifier-clock provenance, per-signature status, or external
boundaries remain:

```text
unbound
```

The record-level result may therefore be:

```text
partially_bound
```

### 26.3 Consistency status

A PASS can support the defined consistency-axis value:

```text
consistent
```

The exact qualification must remain outside the axis value in explicit bindings
such as:

```text
consistency_scope:
exact_raw_layout_carrier_identity
+
exact_layout_signature_input_identity
+
complete_layout_signature_inventory
+
per_signature_verification_status
+
verified_supplied_key_signer_relations
+
exact_substitution_parameter_map
+
exact_effective_layout_identity
+
exact_raw_Link_carrier_set
+
exact_Link_signature_input_identities
+
verified_Link_signer_relations
+
exact_verifier_and_signature_dependency_identity
```

A PASS does not establish consistency under another raw layout carrier, another authenticated Layout-content identity,
another substitution map, another effective layout, another Link evidence set,
another policy, or another verifier.

### 26.4 Reproduction status

Without exact environment, isolated inspection replay, and a controlled verifier
clock for the expiration check, the maximum may be:

```text
bounded_replay_only
```

A current-clock rerun is a new verification event, not an exact replay of the
original expiration decision.

Exact reproduction requires every relevant evidence, signature-selection,
substitution, execution, environment, and clock boundary to be preserved.

### 26.5 Causal status

The default is:

```text
not_evaluated
```

or, where a sequence relation is adequately supported:

```text
sequence_only
```

Classic in-toto does not establish causal necessity, sufficiency, or exclusivity.

### 26.6 Authority status

The upstream result remains:

```text
none
```

until a separate PULSE policy admits the evidence and materializes an
authority-bearing transition.

---

## 27. Evidence coverage must remain explicit

A future mapping must not compress classic in-toto evidence into a confidence
score.

Useful coverage fields include:

```text
raw_layout_carrier_present

layout_wrapper_type_present

layout_signature_input_identity_present

layout_signature_records_carried

layout_verification_keys_supplied

layout_verification_keys_with_matching_valid_signature

layout_signature_records_verified

layout_signature_records_failed

layout_signature_records_unmatched

layout_signature_records_not_evaluated

authenticated_layout_content_identity_present

substitution_parameter_map_present

effective_layout_identity_present

raw_Link_carriers_present

Link_signature_input_identities_present

accepted_Link_signer_relations_present

declared_steps

verified_steps

required_functionary_thresholds

satisfied_functionary_thresholds

declared_material_paths

declared_product_paths

matched_artifact_continuity_edges

unmatched_or_unconsumed_artifact_paths

layout_steps_with_command_alignment

layout_steps_with_command_mismatch

steps_with_event_time_binding

steps_with_observation_time_binding

verifier_clock_source_identity_present

verifier_clock_observation_status

verifier_clock_precision_and_uncertainty_present

layout_expiration_evaluation_present

controlled_clock_replay_status

sublayouts_present

sublayouts_fully_preserved

inspections_present

inspections_executed

inspection_results_preserved

current_run_subject_binding_evaluated

current_run_subject_matches_selected_product

alternative_paths_evaluated

unresolved_transition_edges
```

A meaningful record may say:

```text
1 raw layout metadata carrier preserved

1 wrapper-specific layout signature input reconstructed

3 carried layout signature records preserved

1 supplied layout-verification key

1 matching layout signature record verified for the supplied key

2 additional carried layout signature records not evaluated by the upstream path

1 authenticated Layout-content identity preserved

1 exact substitution parameter map preserved

1 deterministic effective-layout identity preserved

5 planned effective steps

5 raw Link carriers and Link signature-input identities preserved

5 signed step records accepted

3 artifact-continuity MATCH edges verified

0 step event-time bindings present

0 step observation-time bindings present

verifier-clock source identity recorded

exact internal clock read not instrumented; bounded observation interval preserved

layout expiration comparison passed under that bounded clock state

controlled-clock replay not performed

2 command alignments matched

1 command mismatch produced warning-only state

1 sublayout verified and fully preserved

current-run release-subject binding not evaluated

alternative path analysis not performed

authority effect none
```

It must not say:

```text
transition confidence:
92 percent
```

---

## 28. Relation to the existing SLSA/VSA intake

The current PULSEmech SLSA/VSA evidence schema requires an in-toto Statement
with:

```text
predicateType:
https://slsa.dev/verification_summary/v1
```

and records fields such as:

```text
subject digest

verifier identity

verification time

resource URI

policy identity and digest

input attestation digests

verification result

verified levels
```

That contract is useful for:

```text
verified provenance summary admission
```

It does not losslessly preserve:

```text
exact raw layout metadata-carrier bytes

layout wrapper type

layout signature records

wrapper-specific layout signature-input identity

authenticated Layout-content identity

external layout trust roots

exact substitution parameter map

deterministic effective-layout identity

exact raw Link metadata carriers

wrapper-specific Link signature-input identities

accepted and rejected signer relations

step thresholds

effective artifact-rule lists

rule-consumption state

sublayout carrier tree

inspection definitions

effective inspection commands

inspection execution state

command mismatch warnings

separate current-run subject-to-product binding state
```

Therefore:

```text
classic layout/link tree
→ existing SLSA/VSA schema
```

is not a lossless direct mapping.

The existing SLSA/VSA lane must not be expanded silently to absorb a different
upstream object.

---

## 29. Relation to Witness

Witness and classic in-toto overlap in software-supply-chain transition
measurement.

Both can bind forms of:

```text
step identity

functionary identity

input artifact state

output artifact state

cross-step artifact relation

policy-relative verification
```

They differ in their upstream mechanics.

### Classic in-toto

```text
raw metadata carrier containing original Layout payload and signature records

wrapper-specific layout signature input and verified signer relation

exact substitution parameter map

deterministically derived effective layout

raw metadata carriers containing Link payloads and signature records

wrapper-specific Link signature inputs and verified signer relations

functionary thresholds

artifact rules

sublayouts

client inspections
```

### Witness

```text
attestor lifecycle

signed attestation collections

signed Witness policy

required attestation types

Rego evaluation

artifactsFrom relations

VerificationSummary

StepResults
```

The existing Witness document records a richer structured verification-result
target.

The classic in-toto public verifier principally yields:

```text
summary Link
or
typed failure
```

The future PULSEmech architecture may eventually use:

```text
software_supply_chain_transition_evidence
```

with separate profiles:

```text
classic_in_toto_layout_link

witness_policy_verification
```

This document does not decide that structure.

A separate classic in-toto carrier is justified only if the shared profile
cannot preserve the upstream semantics without ambiguity or loss.

---

## 30. Domain verifier, adapter, and current-run subject boundary

The correct future relation is:

```text
raw classic in-toto metadata carriers
+
layout verification keys
+
exact substitution parameter map
+
exact verification configuration
→ official pinned in-toto domain verifier
→ wrapper-specific signature verification
→ effective-layout verification result
→ lossless PULSEmech adapter
→ normalized transition-evidence record
```

The release subject is connected only afterward through a separate PULSEmech
binding:

```text
normalized accepted in-toto product evidence
+
exact PULSE current-run subject
+
exact protected product-selection rule
+
path and digest equality
→ current-run subject binding
```

### 30.1 in-toto responsibility

Classic in-toto remains responsible for:

```text
metadata carrier loading and parsing

Layout and Link payload validation

wrapper-specific layout signature-input reconstruction

verification of one matching layout-signature relation for each supplied verification key under the pinned outer key loop

Layout expiration against the verifier-host UTC clock read during execution

substitution semantics

Link carrier discovery

wrapper-specific Link signature-input reconstruction

Link signature verification

functionary authorization under the effective layout

threshold verification

sublayout verification

effective artifact-rule semantics

effective inspection execution semantics

domain PASS or typed failure
```

### 30.2 Adapter responsibility

A future adapter would be responsible for preserving:

```text
exact upstream and signature-dependency source identities

exact raw layout metadata carrier

layout wrapper type and complete carried signature inventory

exact layout signature-input identity

selected matching signature record for every supplied verification key

per-signature verification status

verified supplied-key signer relations

authenticated original Layout-content identity

exact substitution parameter map

exact effective-layout derivation identity

exact raw Link and sublayout carriers

Link and sublayout wrapper types and complete carried signature inventories

exact Link and sublayout signature-input identities

selected matching signature records for accepted Link and sublayout candidates

per-signature verification statuses for Link and sublayout carriers

verified Link and sublayout signer relations

external layout trust roots

exact verification configuration

verifier-clock acquisition method and source identity

clock observation or bounded observation interval

clock precision, uncertainty, synchronization, and trust state

expiration comparison inputs, result, and controlled-clock replay status

exact inspection mode

domain outcome

domain warnings

directly preserved fields

derived fields and derivation rules

unavailable fields

unresolved fields

coverage limits
```

The adapter must not strengthen the domain claim.

### 30.3 PULSEmech responsibility

PULSEmech remains responsible for:

```text
cross-record identity

exact current-run repository, workflow, run, attempt, candidate, and source binding

current-run release-subject identity

protected selection of one accepted in-toto product reference

subject-to-product path and digest equality

stale-subject rejection

transition-element mapping

edge-level evidence binding

time-binding status

boundary coverage

alternative-path state

unresolved-edge preservation

replay status

authority separation
```

No upstream verification result may affect PULSEmech authority while the
current-run subject relation is unbound or mismatched.

---

## 31. No-reimplementation invariant

PULSEmech must not become a second classic in-toto verifier or a second
signature-wrapper implementation.

The forbidden path is:

```text
read in-toto metadata carriers
→ independently redefine Metablock canonical signature input
→ independently redefine DSSE PAE signature input
→ independently reimplement signature verification
→ silently mark every carried signature as verified after one required relation passes
→ independently replace the verifier-host expiration clock with an unrelated recorded timestamp
→ independently reimplement substitution semantics
→ independently reimplement threshold semantics
→ independently reimplement artifact-rule engine
→ independently reimplement sublayout recursion
→ independently reimplement inspection behavior
→ claim equivalent in-toto verification
```

This would create:

```text
duplicate semantics

divergent edge cases

version drift

new attack surface

false equivalence with upstream verification
```

The required path is:

```text
pin exact official verifier and signature-input dependency source

preserve exact raw metadata carriers

preserve wrapper-specific signature-input identities

preserve complete carried signature inventories

preserve exact verification keys, selected matching signature records, per-signature statuses, and verified signer relations

preserve exact substitution parameter map

derive and bind exact effective-layout identity

preserve verifier-clock source, observation or bound, precision, uncertainty, trust state, and expiration result

replay official verifier under controlled evidence, execution, and clock conditions

preserve typed result and complete evidence tree

map the domain result into PULSEmech without semantic promotion

bind the separate current-run release subject afterward
```

A PULSEmech validator may verify the integrity and internal consistency of the
normalized carrier and the subject-binding relation.

It must not silently replace the official domain verifier or wrapper-specific
signature semantics.

---

## 32. Future carrier decision criteria

No classic in-toto carrier is defined by this document.

A dedicated carrier becomes justified only when all of the following are
established.

### 32.1 Unique information requirement

The classic layout/link profile must provide information not losslessly carried
by:

```text
existing SLSA/VSA intake

existing future Witness carrier shape

a possible shared software-supply-chain transition-evidence carrier
```

### 32.2 Stable upstream execution boundary

A future implementation must identify a stable way to preserve:

```text
complete accepted input carrier tree

typed failures

warnings

threshold results

artifact-rule results

sublayout results

inspection results
```

without treating human logs as the normative result.

### 32.3 Exact source identity

The implementation must bind:

```text
in-toto repository and exact revision

in-toto reviewed source-surface manifest

exact pinned securesystemslib version and resolved revision

signature-input dependency reviewed surface

participating executable or library digest

adapter identity
```

### 32.4 Raw carrier, signature input, and signature-selection scope

The implementation must bind separately:

```text
exact raw metadata-carrier identities

wrapper types

complete carried signature inventories

wrapper-specific signature-input modes

exact signature-input identities

verification-key identities

selected matching signature record for every supplied verification key

per-signature verification status

verified supplied-key signer relations

unevaluated signature-record identities

authenticated payload-content identities
```

It must not claim that valid signatures authenticate every raw wrapper byte.

It must also not claim that successful required-key verification validates every
signature record carried by the wrapper.

### 32.5 Effective-layout identity

The implementation must bind:

```text
authenticated original Layout-content identity

exact substitution parameter map

exact deterministic effective-layout derivation

exact effective-layout identity

authenticated Link-content identity set
```

### 32.6 Current-run subject binding

The implementation must separately bind:

```text
exact PULSE current-run identity

exact release-candidate subject path and digest

exact selected accepted in-toto product reference

exact product-selection rule

subject-to-product path and digest equality

stale-evidence result
```

An unbound or mismatched current-run subject must have no authority effect.

### 32.7 Inspection isolation

The implementation must define and prove a safe inspection execution boundary.

### 32.8 Trust-root binding

The exact layout-verification keys and their protected selection mechanism must
be part of the record.

The record must distinguish:

```text
supplied key set
verified matching signature relation per supplied key
complete carried signature inventory
unmatched or unevaluated additional signature records
```

### 32.9 Transition-time preservation

Missing event and observation times must remain explicitly unbound.

They must not be synthesized from unrelated timestamps.

### 32.10 Verifier-clock and expiration replay boundary

The implementation must preserve:

```text
verifier-clock acquisition implementation
clock source identity
observed UTC value or bounded observation interval
clock precision and uncertainty
clock synchronization and trust state
exact Layout.expires source and parsed value
comparison rule and result
controlled-clock replay mode
clock-control mechanism identity where replay is claimed
```

A current-clock rerun must be classified as a new verification event.

It must not be represented as reproduction of the original expiration decision.

### 32.11 No causal or authority promotion

Artifact continuity must not be promoted into causal necessity, sufficiency, or
exclusivity.

Upstream PASS must remain evidence only until a separate PULSE policy explicitly
uses a complete, current-run-bound evidence relation.

If these criteria are not satisfied, a separate carrier must not be created.

---

## 33. First bounded proof question

Before any schema or candidate proposal, one bounded observed study may be used
to determine whether a dedicated carrier is necessary.

The study should use:

```text
one exact in-toto source revision

one exact securesystemslib signature-input dependency revision

one exact raw layout metadata carrier

one exact wrapper-specific layout signature input

one exact complete carried layout-signature inventory

one exact supplied layout-verification-key set

one exact selected matching signature record for each supplied key under the pinned outer key loop

one exact per-signature verification-status record

one exact authenticated original Layout-content identity

one exact substitution parameter map

one exact deterministic effective-layout identity

one exact complete raw Link and sublayout carrier tree

one exact Link and sublayout signature-input identity tree

one deterministic recorded artifact set

no inspections
or
an independently isolated inspection executor

one exact official verifier execution

one exact verification event

one identified verifier-clock source and acquisition path

one exact clock observation or bounded clock-observation interval

one recorded clock precision, uncertainty, synchronization, and trust state

one explicit controlled-clock replay mode

one exact PULSE current-run subject supplied only to the separate binding step
```

The study should preserve:

```text
all raw carrier bytes, digests, and sizes

all wrapper types and complete carried signature inventories

all wrapper-specific signature-input bytes, digests, and sizes

all supplied verification-key identities

all selected matching signature records

all per-signature verification statuses, including unevaluated records

all verified supplied-key signer relations

all original Layout steps and rules

all substitution parameters

the complete effective-layout derivation

all effective steps and rules

all accepted, rejected, and ignored Link identities where the upstream surface exposes them

verifier-clock acquisition implementation and source identity

exact clock observation or bounded observation interval

clock precision, uncertainty, synchronization, and trust state

exact expiration comparison inputs and result

controlled-clock replay configuration and result

all warnings

typed verification result

returned summary Link

the exact selected first-step and last-step representative Links

all fields lost by the summary reduction

the separate PULSE current-run subject identity

the exact selected accepted product reference

the subject-to-product comparison result

all Transition Meter fields that remain unavailable
```

The study must include at least these signature-scope cases:

```text
one supplied layout-verification key
+
one matching valid signature record
+
one additional invalid or untrusted signature record
→ required-key layout-signature phase may pass
→ additional record remains not_evaluated_by_upstream_path or separately failed
→ additional record must not be reported as verified
```

```text
two supplied layout-verification keys
+
one matching valid signature record for each key
→ required-key layout-signature phase passes
```

```text
two supplied layout-verification keys
+
one key has no matching valid signature record
→ required-key layout-signature phase fails
```

The study must include this DSSE signature-input vector:

```text
payloadType:
application/vnd.in-toto+json

expected signature input:
b"DSSEv1"
+ b" "
+ ASCII_DECIMAL(BYTE_LENGTH(UTF-8(payloadType)))
+ b" "
+ UTF-8(payloadType)
+ b" "
+ ASCII_DECIMAL(BYTE_LENGTH(decoded_payload_bytes))
+ b" "
+ decoded_payload_bytes
```

The vector must prove the literal `0x20` separators and the byte-length rule.
A non-ASCII payload type must be rejected as outside the fixed reviewed classic
in-toto profile rather than processed through an ambiguous character-count rule.

The study must include at least these verifier-clock cases:

```text
same exact evidence and verifier
+
trusted clock before Layout.expires
→ expiration check passes
```

```text
same exact evidence and verifier
+
trusted clock at or after Layout.expires
→ LayoutExpiredError
```

```text
recorded original clock observation
+
identified controlled-clock mechanism
+
exact verifier replay consuming that controlled clock
→ original expiration decision may be reproduced
```

```text
recorded timestamp only
+
uncontrolled current host clock
→ new verification event
→ not exact expiration replay
```

The study must include at least these subject-binding cases:

```text
same accepted in-toto evidence
+
current-run subject path and digest equal selected product path and digest
→ subject binding passes
```

```text
same accepted in-toto evidence
+
different current-run subject digest
→ subject binding rejected
```

```text
same accepted in-toto evidence
+
no protected product-selection rule
→ subject binding unbound
```

The study question is:

```text
Can the classic in-toto domain result and its separate current-run subject
binding be represented losslessly through an existing or shared PULSEmech
software-supply-chain transition carrier?
```

Possible results are:

```text
existing VSA path sufficient

shared carrier sufficient

classic profile extension required

dedicated carrier required

upstream result surface insufficient

subject-binding surface insufficient

inspection boundary unresolved

no implementation justified
```

The study does not create a candidate gate.

---

## 34. Implementation and scheduling effect

This document is documentation-only.

It does not alter the current PULSEmech development sequence.

The current compute workstream remains:

```text
PR #2789 current-run expectation builder
→ close remaining trust boundaries
→ merge builder
→ add permanent builder regression
→ implement carrier component
→ implement current-run subject-input wrapper
→ implement non-active candidate workflow
→ produce first current-run artifact-observed connected proof
```

The in-toto layout/link relation remains:

```text
recorded mechanical boundary
→ no implementation commitment
```

It must not be inserted into:

```text
PR #2789

the current SARIF path

the current compute workflow

the active release-required gate set
```

---

## 35. Anti-confusion invariants

```text
Layout payload
≠ raw layout metadata carrier

Link payload
≠ raw Link metadata carrier

raw metadata-carrier identity
≠ wrapper-specific signature-input identity

valid Metablock signature
→ canonical signed-payload representation authenticated
≠ complete raw Metablock bytes authenticated

valid DSSE signature
→ exact PAE with literal ASCII-space separators and byte-length fields authenticated
≠ complete raw Envelope bytes authenticated

PAE construction without the four literal `0x20` separators
≠ DSSE v1 signature input

Unicode character count for an unrestricted non-ASCII payload type
≠ general DSSE byte-length rule

fixed reviewed ASCII in-toto payload type
→ string length equals UTF-8 byte length

required supplied-key layout-signature verification passed
≠ every carried layout signature record verified

one matching signature verified for a supplied key
≠ every additional signature record valid or trusted

same authenticated payload content
+
wrapper reserialization or additional signature
→ different raw evidence carrier
→ existing signature may remain valid

same authenticated original Layout content
+
different substitution parameter map
→ different effective path identity

effective layout step order
≠ measured event-time order

verified Link signer relation
≠ complete execution observation

declared material
≠ causally used input

declared product
≠ complete output set

reported command
≠ strictly verified effective expected command

command mismatch warning
≠ verification failure

threshold agreement
≠ complete independent reproduction

artifact MATCH
≠ unique causal path

summary Link
≠ complete verified internal path

summary Link last-step command and byproducts
≠ threshold-wide command and byproduct agreement

authenticated Layout content not expired under one verifier-clock observation
≠ same expiration result under another clock observation

recorded verification-event timestamp
≠ controlled clock consumed by the expiration function

same evidence and verifier before expiry
≠ same outcome after expiry

valid wrapper-specific layout signature
≠ current trust authorization

inspection declaration
≠ safe inspection execution

verification process ran
≠ verification passed

accepted final-step product record
≠ current PULSEmech release subject

in-toto verification PASS
≠ current-run subject binding

valid historical in-toto evidence
+
different current-run subject
→ subject binding rejected

in-toto verification PASS
≠ PULSE final status

in-toto verification PASS
≠ PULSE primary CI ALLOW

upstream evidence admission
≠ release authority
```

---

## 36. Final mechanical position

Classic in-toto provides a strong software-supply-chain evidence mechanism.

Its central verified relation is:

```text
one exact raw metadata carrier containing original Layout content and a complete signature inventory
+
one wrapper-specific layout signature input
+
one selected matching signature record and verified signer relation for every supplied layout-verification key
+
per-signature status for every additional carried signature record
+
one exact substitution parameter map
+
one deterministically derived effective layout
+
one exact raw set of functionary Link metadata carriers
+
one exact set of wrapper-specific Link signature inputs and verified signer relations
+
one exact effective artifact-rule relation
+
one exact verifier execution
+
one bound verifier-clock source and expiration evaluation state
→ effective-layout-relative artifact-chain conformance under one exact clock state
```

The raw carrier identity and authenticated content identity remain separate.

This is valuable PULSEmech upstream evidence.

It can provide:

```text
declared artifact state before

declared artifact state after

authorized participant identity under the exact layout trust model

artifact creation, deletion, and modification relations

digest-backed cross-step artifact continuity

threshold agreement

hierarchical sublayout verification
```

It does not by itself provide:

```text
complete actual execution coverage

element-level event and observation time

clock-independent expiration replay without a controlled clock boundary

general opened or closed system-path identity

complete alternative-path analysis

unresolved-edge preservation as multiaxial state

causal necessity or sufficiency

binding to the current PULSEmech release subject

PULSE release authority
```

The current-run relation begins only when PULSEmech separately establishes:

```text
exact current-run subject
+
protected selected accepted in-toto product reference
+
path and digest equality
→ current-run subject binding
```

The exact relationship is:

```text
classic in-toto
→ domain-native signed artifact-transition evidence
→ possible PULSEmech evidence admission
→ separate current-run subject binding
→ possible later policy evaluation
```

not:

```text
classic in-toto
→ complete generalized Transition Meter
```

and not:

```text
classic in-toto verification PASS
→ current-run subject bound
```

and not:

```text
classic in-toto verification PASS
→ PULSEmech release ALLOW
```

The present result is therefore:

```text
mechanical relevance:
confirmed

transition-evidence value:
confirmed

raw-carrier and signature-input separation:
required

current-run subject binding:
separate and not implemented

complete Transition Meter equivalence:
rejected

dedicated carrier requirement:
not yet established

implementation effect:
none

candidate effect:
none

release-authority effect:
none
```

The value of this boundary is not that it forces another implementation lane.

The value is that it makes the precise measurement gap visible before a new
lane is built.
