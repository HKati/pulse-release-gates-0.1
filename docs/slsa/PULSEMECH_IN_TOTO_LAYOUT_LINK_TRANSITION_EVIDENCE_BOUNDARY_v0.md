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

upstream_reviewed_surface_manifest_sha256:
d488223c04f2eed4fe486de4491326bcff308339b05515bb0c8ab3eb657b3025

upstream_specification_repository:
in-toto/specification

upstream_specification_reviewed_revision:
6459afd8e94a332e423ba05c2862b534acbe741d

upstream_specification_version:
1.0.0

upstream_specification_reviewed_surface_manifest_sha256:
36a44fc639ec528deb61b6b831f4b4a3ba68bffc82901352c977db4a7a7ca038

reviewed_surface_manifest_byte_rule:
utf8_lexicographically_sorted_path_tab_git_blob_lf

upstream_retrieval_method:
github_repository_api_exact_commit_and_blob_reads

upstream_external_downloaded_source_artifact:
none

source_review_scope:
complete_declared_reviewed_surface_not_whole_repository_digest

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
→ verified conformance to one exact effective layout
  under one exact verifier boundary

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
signed project-owner layout carrier
+
ordered expected steps
+
authorized functionary keys
+
step thresholds
+
signed link metadata carriers
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
≠ signed link metadata chain

Witness policy
≠ classic in-toto Layout payload

Witness StepResults
≠ classic in-toto summary Link

classic in-toto verification
≠ PULSEmech release transition
```

---

## 5. Reviewed upstream source identity

The reviewed classic in-toto source basis is:

```text
repository:
in-toto/in-toto

revision:
a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b

package version:
3.0.0
```

The complete declared implementation review surface is bound by the following
canonical manifest.

Each record is:

```text
<repository-relative path><TAB><Git blob object ID><LF>
```

Records are sorted lexicographically by repository-relative path.

The exact UTF-8 manifest bytes contain:

```text
README.md	22d98a233e7a375c3da8c6781f1f142ccb31be0f
in_toto/__init__.py	6ca9e6636bd222cee0294e79f7a0e7f37e530968
in_toto/in_toto_verify.py	246dac1931bce00d6abb899f12befe6a68598dce
in_toto/models/layout.py	88ff3fa87ec78a33ec42118be1345243909d46d2
in_toto/models/link.py	7ef05ec12099e2d1f16e9685f015c52754176359
in_toto/models/metadata.py	acd6e87aaa854952d4bbed36f59b85166016a695
in_toto/verifylib.py	cae4498bb0636c68b814e8b4d8dba5c0cef29b76
pyproject.toml	ed5939c32538e3cd155058cdc74f10e1d00b4a5c
```

Manifest SHA-256:

```text
d488223c04f2eed4fe486de4491326bcff308339b05515bb0c8ab3eb657b3025
```

The reviewed specification basis is:

```text
repository:
in-toto/specification

revision:
6459afd8e94a332e423ba05c2862b534acbe741d

specification version:
1.0.0
```

The complete declared specification review surface is:

```text
in-toto-spec.md	84234a889c1b5696a8e526a978146795cf8975b5
```

Manifest SHA-256:

```text
36a44fc639ec528deb61b6b831f4b4a3ba68bffc82901352c977db4a7a7ca038
```

The review used exact GitHub repository reads bound to immutable revisions and
Git object content.

No generated source archive or external downloaded source bundle was used.

The declared manifests identify the complete source surface on which this
document's upstream mechanical claims rely.

They are not:

```text
whole-repository digests

dependency activation

installation instructions

future-version compatibility claims
```

Mechanics outside the declared manifests are not represented as reviewed by this
record.

---

## 6. Classic in-toto system model

The classic in-toto system has three principal participating roles and several
separate payload and carrier objects.

### 6.1 Project owner

The project owner defines the intended supply-chain structure in a Layout
payload.

The owner signs a metadata carrier that contains that Layout payload.

The project owner does not place signatures inside the Layout payload itself.

### 6.2 Functionary

A functionary performs a named supply-chain step and signs a metadata carrier
that contains the resulting Link payload.

The functionary is identified through a key authorized by the effective layout.

### 6.3 Client or verifier

The verifier receives:

```text
signed layout metadata carrier

layout verification key or keys

signed link metadata carriers

final product or verification subject

optional substitution parameters

inspection execution environment
```

and evaluates whether the supplied supply-chain evidence satisfies the effective
layout.

The primary path is:

```text
project owner defines Layout payload
→ project owner signs metadata carrier containing Layout payload
→ functionaries perform steps
→ functionaries sign metadata carriers containing Link payloads
→ verifier loads layout carrier and link carriers
→ verifier authenticates carriers and extracts payloads
→ verifier derives effective layout where substitutions are supplied
→ verifier applies thresholds and artifact rules
→ verifier runs inspections
→ verification passes or fails
```

### 6.4 Payload and signed-carrier separation

The reviewed metadata abstraction supports separate signed-carrier forms.

A traditional metadata carrier can be represented as:

```text
Metablock
├── signed:
│   └── Layout or Link payload
└── signatures:
    └── signature records
```

A DSSE carrier can be represented as:

```text
Envelope
├── payloadType
├── payload:
│   └── serialized Layout or Link payload bytes
└── signatures:
    └── signature records
```

The exact wrapper type, wrapper bytes, payload bytes and signatures are separate
identity-bearing objects.

In this document, the shorthand:

```text
signed layout carrier
```

means:

```text
exact signed metadata wrapper
+
exact contained Layout payload
+
exact wrapper-to-payload relation
+
exact signatures
```

It does not mean that signatures are fields inside the Layout payload.

The same separation applies to signed Link carriers.

---

## 7. The Layout payload and its signed carrier

### 7.1 Layout payload

A Layout payload defines a software supply chain through:

```text
_type

steps

inspections

functionary public keys

expiration

human-readable description
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

The Layout step list carries the project owner's expected logical arrangement.

It does not, by itself, establish:

```text
the exact event time of each execution

the exact observation time of each Link

that every step actually occurred in wall-clock order

that no undeclared operation occurred between steps

that the layout itself provides sufficient security
```

The Layout payload is:

```text
planned supply-chain semantics
```

It is not:

```text
a signature carrier
```

and it is not:

```text
complete observation of the realized transition
```

### 7.2 Signed layout carrier

The signed layout carrier contains the Layout payload and the signatures or
signature envelope that authenticate it.

A future PULSEmech mapping must preserve separately:

```text
signed wrapper type

exact signed wrapper bytes

signed wrapper SHA-256

exact Layout payload bytes

Layout payload SHA-256

wrapper payload type where present

wrapper-to-payload equality

signature records

verified signer identities
```

The invariant is:

```text
Layout payload
≠ signed metadata carrier
```

and:

```text
valid Layout payload
≠ verified signed layout carrier
```

---

## 8. The Link payload and its signed carrier

A classic in-toto Link records evidence associated with one named step or
inspection.

Its primary fields are:

```text
name

command

materials

products

byproducts

environment
```

The Link payload normally appears inside a signed metadata carrier.

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

A verified signed Link carrier establishes:

```text
one signing identity
+
one named step record
+
one declared material set
+
one declared product set
+
reported execution metadata
```

It does not automatically establish:

```text
complete process observation

complete filesystem observation

complete input dependency discovery

complete output discovery

causal use of every declared material

absence of every undeclared input or output
```

A future PULSEmech mapping must preserve:

```text
exact signed Link wrapper

exact Link payload

wrapper-to-payload relation

signature identity

payload semantic fields
```

without collapsing those objects into one unqualified `link` identity.

---

## 9. Declared artifact surface is not complete execution observation

Classic in-toto records the artifacts supplied to its recording mechanism.

This creates an explicit measurement boundary.

A file may be used or modified by a command but remain absent from the Link when
it was not declared for recording.

A file may also be supplied for recording and appear in the Link even when the
command did not mechanically depend on it.

Therefore:

```text
link.materials
≠ complete set of actual execution inputs

link.products
≠ complete set of actual execution outputs

artifact listed as material
≠ artifact causally used

artifact absent from Link
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

where the effective rule defines the source and destination artifact
collections and any path prefixes.

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
≠ layout policy is adequate
```

---

## 11. Functionary authorization and thresholds

Each effective layout step identifies authorized functionary keys.

Signed Link metadata is accepted for a step only when:

```text
the Link signature verifies

the signing key is authorized for that step

the required threshold is met
```

The verifier counts distinct authorized functionary identities subject to its
key and subkey rules.

When a threshold is greater than one, the accepted Links for the step must agree
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

A functionary may provide a signed sublayout carrier instead of an ordinary
signed Link carrier for a delegated step.

The verifier recursively verifies the sublayout.

A successful sublayout verification is then reduced to a summary Link for the
parent layout.

This enables hierarchical supply-chain structure:

```text
parent layout step
→ delegated signed sublayout carrier
→ nested steps
→ verified nested result
→ parent summary Link
```

The hierarchy is useful transition evidence.

The reduction creates an important information boundary.

The parent summary does not carry every nested transition edge directly.

A future PULSEmech mapping must preserve:

```text
exact signed sublayout carrier

exact nested Link carrier tree

exact recursive verifier identity

exact recursive verification inputs

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
→ optionally write inspection Link metadata
→ apply inspection artifact rules
```

This means:

```text
in-toto verification
≠ read-only metadata validation
```

A supplied layout and substitution set may determine executable inspection
instructions.

That creates a critical execution relation:

```text
authenticated original layout carrier
+
exact substitution parameters
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

original inspection definition

effective substituted inspection definition

executor identity

isolation boundary

network policy

filesystem policy

secret availability

timeout

return state

produced artifacts

persisted inspection-Link state
```

This document does not select or implement such a mode.

---

## 14. Official verification procedure and effective-layout identity

The reviewed official verification function performs these principal
activities:

```text
1. verify signed layout carrier signatures

2. extract the Layout payload

3. verify Layout expiration

4. substitute declared parameters into the Layout payload

5. load Link metadata for effective-layout steps

6. verify Link signatures and authorized functionaries

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

layout signature failure

layout expiration

substitution failure

missing Link threshold

unauthorized or invalid Link signatures

threshold disagreement

artifact-rule failure

inspection-command failure
```

This is a strong domain verifier.

PULSEmech must treat it as a domain verifier.

PULSEmech must not silently replace it with a second independent
reimplementation of the same rule system.

### 14.1 Original signed layout and effective layout are separate identities

The verification procedure authenticates the original signed layout carrier,
then applies the exact substitution parameter map before evaluating commands and
artifact rules.

The effective path is therefore:

```text
exact original signed layout carrier
+
exact original Layout payload
+
exact substitution parameter map
+
exact pinned substitution implementation
→
deterministically derived effective Layout semantics
```

Two verification runs can share:

```text
the same original signed layout carrier

the same signed Link carriers
```

while applying different:

```text
effective commands

effective material rules

effective product rules

effective inspection commands
```

when their substitution maps differ.

Therefore:

```text
original signed layout identity
≠ effective-layout identity
```

A future carrier must bind:

```text
exact original signed layout wrapper

exact original Layout payload

exact substitution parameter map

exact substitution implementation identity

deterministically derived effective-layout identity

effective expected commands

effective material and product rules

effective inspection commands and rules
```

This document does not define the normative serialization for the future
effective-layout identity.

A future contract must define it before an effective-layout digest can become
normative.

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
reported command

original expected command

effective expected command

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

## 16. Verification output is not a complete structured path report

The public `in_toto_verify(...)` function returns a summary Link after successful
verification.

For the exact reviewed revision, the summary is constructed by explicitly
assigning:

```text
materials of the first effective-layout step

products of the last effective-layout step

byproducts of the last effective-layout step

command of the last effective-layout step
```

The command and byproducts fields are copied from the selected last-step
representative Link in the reviewed source revision.

They are not left at their default values in that revision.

This representation is useful for embedding one verified supply chain inside a
parent supply chain.

It is not a lossless record of:

```text
every step

every accepted Link

every ignored or rejected Link

every signature result

every threshold result

every artifact-rule result

every sublayout edge

every inspection result

every intermediate material/product relation

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
→ first materials
+ last products
+ selected last-step command and byproducts
```

That would discard the exact edge-level structure required by the Transition
Meter.

The selected last-step command and byproducts also must not be promoted into
threshold-wide agreement, because threshold equality is checked over materials
and products.

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

Under one exact original signed layout carrier, exact Layout payload, exact
substitution set, exact effective-layout identity, trust configuration, Link
set, verifier implementation, inspection environment, and verification event, a
PASS can establish that:

```text
the supplied layout carrier was accepted under the supplied
layout-verification keys

the original Layout had not expired at verification time

the exact substitutions were applied without failure

required Link metadata was found for the effective steps

accepted Links had valid signatures

accepted Link signers were authorized by the effective step definitions

step thresholds were satisfied

threshold participants agreed on declared materials and products

sublayout verification completed where present

effective artifact rules passed

effective inspections completed where present

the final product passed the complete configured effective-layout verification
```

A PASS is relative to:

```text
exact original signed layout wrapper bytes

exact original Layout payload bytes

exact layout signatures

exact external layout-verification keys

exact substitution parameter map

exact pinned substitution implementation

deterministically derived effective-layout identity

exact Link and sublayout carriers

exact effective artifact-rule set

exact effective expected-command set

exact verifier source or executable

exact inspection executor and environment

exact verification time
```

These identities are part of the domain verification state.

---

## 18. What a successful verification does not establish

A classic in-toto PASS does not by itself establish:

```text
that the layout is secure or adequate

that the layout requires code review

that every relevant artifact was recorded

that every actual input was declared

that every actual output was declared

that the reported command equals the effective expected command

that the reported command was the only executed command

that the layout step list is a measured wall-clock sequence

that each step carries event-time and observation-time bindings

that no undeclared operation occurred between steps

that no external side channel affected the result

that every functionary acted independently

that all threshold participants used independent infrastructure

that the recorded artifact path is the unique causal path

that every alternative path was excluded

that unresolved edges were preserved as structured state

that the result is current for another run or another artifact

that the PULSE release policy is satisfied

that the PULSE required-gate set is complete

that final PULSE status is valid

that the PULSE terminal decision is ALLOW
```

The principal boundary remains:

```text
in-toto verification PASS
≠ PULSEmech release ALLOW
```

---

## 19. Time-binding gap

The classic Link model does not require explicit edge-level:

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

Artifact MATCH relations can provide digest-backed dependency continuity.

Neither automatically provides measured event time.

Therefore:

```text
effective-layout order
≠ observed event-time order

artifact dependency
≠ wall-clock sequence

verification time
≠ step event time

Link creation time inferred externally
≠ bound observation time
```

The PULSEmech Transition Meter requires each ordered transition element to carry
its own event-time and observation-time bindings.

A classic in-toto mapping must therefore preserve the time state as:

```text
unbound

partially_bound

or

externally_bound_by_separate_evidence
```

It must not manufacture timestamps from:

```text
filesystem modification time

metadata retrieval time

Git commit time

verification time

layout step index
```

unless the exact meaning and source of that time are separately recorded.

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

accepted Links
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

The verifier can establish that:

```text
the supplied key verifies a signature on the exact signed layout carrier
```

It does not independently establish:

```text
why the key is trusted

how the key was obtained

whether the key was revoked elsewhere

whether its usage flags permit this purpose

whether a newer layout supersedes the current layout

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

verification event time

revocation-handling policy

supersession policy
```

A key ID alone is not a complete trust-root identity.

```text
key ID
≠ key bytes

valid signature
≠ current authorization

layout signed
≠ layout current
```

---

## 22. Layout compliance is not layout adequacy

Classic in-toto verifies conformance to the effective layout derived from the
authenticated original layout and exact substitutions.

It does not determine whether that effective layout provides sufficient
security, quality, or release policy.

A layout may omit:

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
Layout payload valid
≠ layout adequate

layout carrier signed
≠ layout secure

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

Classic in-toto Layout expiration provides a time limit.

Expiration alone does not establish:

```text
that no newer layout exists

that the current layout is the latest authorized layout

that an older still-unexpired layout was not replayed

that the layout was distributed through an authenticated update path
```

The upstream specification identifies secure layout and key distribution as a
separate problem, commonly addressed through a mechanism such as TUF.

For PULSEmech admission:

```text
layout not expired
≠ layout current

layout signature valid
≠ layout selected by current PULSE policy

old valid layout
≠ current authorized layout
```

A future record must bind the exact expected signed layout carrier and exact
allowed substitution set through protected PULSE policy or another
authenticated selection mechanism.

---

## 24. Mapping classes

Every classic in-toto field or result must be assigned one of four mapping
classes.

### 24.1 Directly preserved

The upstream carrier explicitly records the object.

Examples:

```text
Layout step name

authorized functionary key IDs

step threshold

Link signer identity

material path and digest

product path and digest

reported command

Layout expiration

signed wrapper and signature records
```

### 24.2 Mechanically derived

The object can be derived from exact preserved upstream records through an
explicit deterministic rule.

Examples:

```text
artifact created

artifact deleted

artifact modified

artifact digest continuity

effective-layout step sequence index

effective-layout identity
```

A derived field must preserve:

```text
derivation rule identity

source field identities

transformation-input identities

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
| `target_state_ref` | Step products | Direct for declared artifact subset | Not complete process state |
| `relation_before` | Material path and digest set | Derived domain relation | Artifact scope only |
| `relation_after` | Product path and digest set | Derived domain relation | Artifact scope only |
| `changed_relations` | CREATE, DELETE, MODIFY results under effective rules | Deterministically derivable | Only declared paths and effective rules |
| `ordered_transition_elements` | Ordered effective-layout steps | Planned order derivable | Actual event-time order unbound |
| `path_identity` | Original signed-layout carrier + original Layout payload + exact substitution map + pinned substitution implementation + deterministic effective-layout identity + signed Link tree + effective rules | Derivable only when every exact carrier and transformation input is preserved | Summary Link alone is insufficient |
| `participating_entities` | Functionary keys and accepted Link signers | Direct | Key identity is not full authorization provenance |
| `system_boundary` | Effective layout, step, sublayout and verification environment | Partial | General external boundary not encoded |
| `boundary_crossings` | MATCH relations and sublayout delegation | Partial | Domain-specific artifact crossings |
| `event_time_binding` | No required Link field | Unavailable by default | Requires separate evidence |
| `observation_time_binding` | No required Link field | Unavailable by default | Requires separate evidence |
| `record_verification_time_binding` | Verification event | Separately recordable | Must not substitute for step time |
| `measurement_refs` | Exact signed layout and Link carriers | Direct | Wrapper and payload identities must remain separate |
| `evidence_refs` | Signed layout, Links, sublayouts and inspection Links | Direct | Full carrier tree required |
| `domain_verifier_binding` | Exact in-toto verifier and exact configuration | Separately bound | Version label alone is insufficient |
| `transition_verifier_binding` | Future PULSEmech mapper/verifier | Not implemented | Must remain separate from in-toto |
| `alternative_paths` | No native complete model | Unresolved by default | Must not be inferred from one passing layout |
| `excluded_paths` | Some artifact-rule exclusions | Partial | Not general alternative-path closure |
| `remaining_admissible_paths` | Not represented | Unresolved | Requires separate analysis |
| `unresolved_edges` | Failures and missing evidence | Partial | Not persisted as multiaxial record by default |
| `reconstruction_method` | Exact verifier replay plus mapping rule | Future derived record | Not yet implemented |
| `reproduction_status` | Exact replay may be possible | Bounded | Inspections, environment and substitutions affect replay |
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

A normalized PULSEmech interpretation must preserve independent axes and use only
the status vocabulary defined by the foundational Transition Meter.

### 26.1 Observation status

For the declared artifact surface:

```text
partially_observed
```

may be appropriate when materials and products were captured around a step.

It must not become:

```text
directly_observed
```

for the complete transition unless complete observation coverage is separately
proven.

### 26.2 Binding status

Artifact identities may be:

```text
bound
```

while event time or external boundaries remain:

```text
unbound
```

The record-level result may therefore be:

```text
partially_bound
```

### 26.3 Consistency status

A PASS can support the defined axis value:

```text
consistent
```

The qualification belongs in separate bindings such as:

```text
consistency_scope:
exact_effective_layout_and_exact_verification_inputs

original_layout_carrier_ref:
<exact identity>

substitution_parameter_ref:
<exact identity>

effective_layout_ref:
<deterministically derived identity>

domain_verifier_ref:
<exact identity>
```

The consistency axis must not invent:

```text
consistent_under_exact_layout
```

as a new status value.

A PASS does not establish consistency under another layout, substitution set,
policy, verifier or evidence set.

### 26.4 Reproduction status

Without exact environment and isolated inspection replay, the maximum may be:

```text
bounded_replay_only
```

Exact reproduction requires every relevant input and execution boundary to be
preserved.

### 26.5 Causal status

The default is:

```text
not_evaluated
```

or, where a sequence relation is adequately supported:

```text
sequence_only
```

Classic in-toto does not establish causal necessity, sufficiency, or
exclusivity.

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

sublayouts_present

sublayouts_fully_preserved

inspections_present

inspections_executed

inspection_results_preserved

substitution_parameters_present

effective_layout_identity_present

alternative_paths_evaluated

unresolved_transition_edges
```

A meaningful record may say:

```text
5 planned effective-layout steps

5 signed step records accepted

3 artifact-continuity MATCH edges verified

0 step event-time bindings present

0 step observation-time bindings present

2 command alignments matched

1 command mismatch produced warning-only state

1 sublayout verified and fully preserved

exact substitution parameter map preserved

effective-layout identity derived

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
signed layout wrapper bytes

Layout payload bytes

layout signatures

external layout trust roots

exact substitution parameters

effective-layout identity

every signed Link wrapper and payload

step thresholds

artifact-rule lists

rule-consumption state

sublayout tree

inspection definitions

inspection execution state

command mismatch warnings
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
signed layout carrier

signed Link carriers

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

A separate classic in-toto carrier is justified only if a shared profile cannot
preserve the upstream semantics without ambiguity or loss.

---

## 30. Domain verifier and adapter boundary

The correct future relation is:

```text
classic in-toto layout and Link carriers
→ official pinned in-toto domain verifier
→ domain verification result
→ lossless PULSEmech adapter
→ normalized transition-evidence record
→ PULSEmech transition verification
```

### 30.1 in-toto responsibility

Classic in-toto remains responsible for:

```text
metadata wrapper parsing

Layout and Link payload validation

layout signature verification

layout expiration

parameter substitution semantics

Link discovery

Link signature verification

functionary authorization

threshold verification

sublayout verification

artifact-rule semantics

inspection execution semantics

domain PASS or typed failure
```

### 30.2 Adapter responsibility

A future adapter would be responsible for preserving:

```text
exact upstream source identity

exact signed layout and Link carriers

exact payload identities

wrapper-to-payload relations

external layout trust roots

exact substitution parameter map

deterministic effective-layout identity

exact verification configuration

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

current-run subject binding

transition-element mapping

edge-level evidence binding

time-binding status

boundary coverage

alternative-path state

unresolved-edge preservation

replay status

authority separation
```

---

## 31. No-reimplementation invariant

PULSEmech must not become a second classic in-toto verifier.

The forbidden path is:

```text
read in-toto carriers
→ independently reimplement metadata signatures
→ independently reimplement parameter substitution
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
pin exact official verifier

preserve exact verifier identity

replay official verifier under controlled conditions

preserve typed result and complete input tree

map the domain result into PULSEmech without semantic promotion
```

A PULSEmech validator may verify the integrity and internal consistency of the
normalized carrier.

It must not silently replace the official domain verifier.

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
complete accepted input tree

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
upstream repository

exact revision

package version

complete declared reviewed-source manifest

dependency identities

participating source or executable digest

adapter identity
```

### 32.4 Signed-carrier and payload separation

The implementation must preserve:

```text
exact wrapper bytes

exact payload bytes

wrapper type

wrapper-to-payload relation

signature records

verified signer identities
```

for Layout, Link and sublayout carriers.

### 32.5 Effective-layout identity

The implementation must bind:

```text
original signed layout carrier

original Layout payload

exact substitution map

exact substitution implementation

deterministically derived effective-layout identity
```

### 32.6 Inspection isolation

The implementation must define and prove a safe inspection execution boundary.

### 32.7 Trust-root binding

The exact layout-verification keys and their protected selection mechanism must
be part of the record.

### 32.8 Time-gap preservation

Missing event and observation times must remain explicitly unbound.

They must not be synthesized from unrelated timestamps.

### 32.9 No causal promotion

Artifact continuity must not be promoted into causal necessity, sufficiency, or
exclusivity.

### 32.10 No authority promotion

Upstream PASS must remain evidence only until a separate PULSE policy explicitly
uses it.

If these criteria are not satisfied, a separate carrier must not be created.

---

## 33. First bounded proof question

Before any schema or candidate proposal, one bounded observed study may be used
to determine whether a dedicated carrier is necessary.

The study should use:

```text
one exact upstream in-toto revision

one exact signed layout carrier

one exact original Layout payload

one exact layout trust-root set

one exact substitution parameter map

one exact derived effective-layout identity

one exact complete Link and sublayout carrier tree

one deterministic artifact set

no inspections
or
an independently isolated inspection executor

one exact official verifier execution

one exact verification event
```

The study should preserve:

```text
all input bytes and digests

all wrapper and payload identities

all wrapper-to-payload relations

all signer identities

all original layout steps and rules

all substitution parameters

all effective commands and rules

all accepted Links

all warnings

typed verification result

returned summary Link

all fields lost by summary reduction

all Transition Meter fields that remain unavailable
```

The study question is:

```text
Can the classic in-toto domain result be represented losslessly through an
existing or shared PULSEmech software-supply-chain transition carrier?
```

Possible results are:

```text
shared carrier sufficient

classic profile extension required

dedicated carrier required

upstream result surface insufficient

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
≠ signed layout metadata carrier

Link payload
≠ signed Link metadata carrier

original signed Layout payload
≠ effective substituted Layout semantics

same original layout and Links
+
different substitution map
→ different effective path identity

signed layout
≠ secure layout

layout step order
≠ measured event-time order

signed Link
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

layout not expired
≠ latest authorized layout

valid layout signature
≠ current trust authorization

inspection declaration
≠ safe inspection execution

verification process ran
≠ verification passed

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

Its central verified object is:

```text
one exact signed planned layout carrier
+
one exact original Layout payload
+
one exact substitution parameter map
+
one deterministic effective-layout identity
+
one exact set of signed functionary step carriers
+
one exact effective artifact-rule relation
+
one exact verifier execution
→ effective-layout-relative artifact-chain conformance
```

This is valuable PULSEmech upstream evidence.

It can provide:

```text
declared artifact state before

declared artifact state after

authorized participant identity

artifact creation, deletion, and modification relations

digest-backed cross-step artifact continuity

threshold agreement

hierarchical sublayout verification
```

It does not by itself provide:

```text
complete actual execution coverage

element-level event and observation time

general opened or closed system-path identity

complete alternative-path analysis

unresolved-edge preservation as multiaxial state

causal necessity or sufficiency

PULSE release authority
```

The exact relation is:

```text
classic in-toto
→ domain-native signed artifact-transition evidence
→ possible PULSEmech evidence admission
```

not:

```text
classic in-toto
→ complete generalized Transition Meter
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
