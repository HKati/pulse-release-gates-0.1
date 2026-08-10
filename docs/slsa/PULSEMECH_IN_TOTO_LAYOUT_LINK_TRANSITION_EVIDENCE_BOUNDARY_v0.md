# PULSEmech — in-toto Layout/Link Transition-Evidence Boundary v0

## WORKMARK

```text
document_role:
source_bound_interoperability_and_transition_evidence_mapping

status:
design_and_upstream_source_review_record

review_date:
2026-08-10

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

upstream_ref:
develop

upstream_resolved_revision:
a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b

upstream_package_version:
3.0.0

upstream_reviewed_surface_manifest_lines:
14

upstream_reviewed_surface_manifest_bytes:
886

upstream_reviewed_surface_manifest_sha256:
e0e374e3b02f82ab1e2854ecb60a9e01c5d5b9a9b7dc8c912f939cf595d44e1b

upstream_signature_dependency_repository:
secure-systems-lab/securesystemslib

upstream_signature_dependency_version:
1.3.1

upstream_signature_dependency_resolved_revision:
6f774190b90f0aa9d5d7e077680adbaa29c5cd6c

upstream_signature_dependency_reviewed_surface_manifest_lines:
2

upstream_signature_dependency_reviewed_surface_manifest_bytes:
135

upstream_signature_dependency_reviewed_surface_manifest_sha256:
d2c0056cb1042b3a4df9ac26bc15feb92ab4d2a159e2c52ab0b653530b517eb5

upstream_specification_repository:
in-toto/specification

upstream_specification_resolved_revision:
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

document_scope:
classic_in_toto_upstream_mechanics_and_pulsemech_evidence_boundary

normative_schema:
none

adapter_specification:
none

candidate_gate_set:
none

workflow_integration:
none

release_required_activation:
none

release_authority_effect:
none
```

This document maps the classic in-toto layout/link verification mechanism into
the PULSEmech Transition Meter vocabulary.

It records:

```text
upstream source identity
upstream object and verifier mechanics
evidence and identity layers
artifact-relation coverage
current-run subject-binding boundary
Transition Meter mapping
future implementation decision criteria
```

The document is a source-bound boundary record. It does not define a carrier,
schema, adapter, workflow, candidate gate, or authority-bearing path.

---

## 1. Mechanical position

Classic in-toto provides a signed software-supply-chain verification path:

```text
project-owner Layout policy
→ functionary Link evidence
→ signature and authorization checks
→ threshold checks
→ artifact-rule verification
→ optional sublayout verification
→ optional inspection execution
→ domain PASS or typed failure
```

PULSEmech can use a verified classic in-toto result as upstream evidence after
preserving its exact identity and coverage boundaries.

The complete relation is:

```text
classic in-toto domain verification
→ normalized upstream transition evidence
→ separate PULSEmech current-run subject binding
→ separate PULSEmech policy evaluation
→ possible later PULSEmech transition decision
```

The current decision is:

```text
mechanical relevance:
confirmed

signed artifact-transition evidence value:
confirmed

complete generalized Transition Meter coverage:
not established

direct carrier requirement:
deferred pending observed replay

implementation effect:
none

candidate effect:
none

release-authority effect:
none
```

---

## 2. Reviewed upstream source identity

### 2.1 Classic in-toto implementation surface

```text
repository:
in-toto/in-toto

resolved revision:
a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b

package version:
3.0.0
```

The complete declared selected review surface is this canonical path/blob
manifest.

Each line is encoded as:

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
in_toto/resolver/__init__.py	a81d7f377125f2a4828149b6283b6da00dd00187
in_toto/resolver/_resolver.py	4b7635b286fe9b324bd502993b77e26a4b84d61d
in_toto/rulelib.py	2e9d2c367d9d0399cfe5caae4a0963c2db0a8f66
in_toto/runlib.py	8207871046a6b0691c2689198d8d87a874520a38
in_toto/verifylib.py	cae4498bb0636c68b814e8b4d8dba5c0cef29b76
pyproject.toml	ed5939c32538e3cd155058cdc74f10e1d00b4a5c
requirements-pinned.txt	8f3fd2facdd5bfd5263cb666642713d1d8f82bc1
```

Manifest identity:

```text
lines:
14

bytes:
886

final newline:
present

SHA-256:
e0e374e3b02f82ab1e2854ecb60a9e01c5d5b9a9b7dc8c912f939cf595d44e1b
```

This review surface covers the layout/link models, metadata wrappers,
verification sequence, artifact-rule engine, command execution, artifact
resolvers, path recording, sublayouts, inspections, and CLI boundary used by
this document.

### 2.2 Signature-input dependency surface

The reviewed in-toto revision pins:

```text
securesystemslib[crypto] == 1.3.1
```

The selected dependency source basis is:

```text
repository:
secure-systems-lab/securesystemslib

resolved revision:
6f774190b90f0aa9d5d7e077680adbaa29c5cd6c

version:
1.3.1
```

The declared selected review surface is:

```text
securesystemslib/dsse.py	d41abec92618093ef6daba90a1f82fae087b8c40
securesystemslib/formats.py	f6e00e3b1271472c5dbc1b95980637039e18ef02
```

Manifest identity:

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

This dependency surface covers the canonical JSON and DSSE PAE constructions
used to define wrapper-specific signature inputs. Cryptographic primitive
implementation is consumed through the pinned upstream verification API and is
outside this selected source review.

### 2.3 Specification surface

```text
repository:
in-toto/specification

resolved revision:
6459afd8e94a332e423ba05c2862b534acbe741d

specification version:
1.0.0
```

```text
in-toto-spec.md	84234a889c1b5696a8e526a978146795cf8975b5
```

Manifest identity:

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

### 2.4 Review reproduction

The source review is reproduced only by using the same repositories, resolved
revisions, canonical manifests, and manifest digests.

The manifests define the complete selected review scope. They are not presented
as whole-repository audits or dependency activation instructions.

---

## 3. Upstream object model

Classic in-toto uses distinct policy, evidence, wrapper, and execution objects.

| Object | Mechanical role |
|---|---|
| `Layout` payload | Declares steps, functionaries, thresholds, expected commands, artifact rules, inspections, keys, and expiry |
| metadata carrier | Stores a `Layout` or `Link` payload and signature records in Metablock or DSSE form |
| signature input | Wrapper-specific bytes authenticated by a selected signature relation |
| `Link` payload | Records one step or inspection name, materials, products, command, byproducts, and environment |
| link-directory entry | Associates a discovered carrier with an expected step and authorized key candidate |
| sublayout | Delegates one step to a nested signed layout and nested evidence tree |
| inspection | Executes a verifier-side command and creates a generated inspection `Link` result |
| summary `Link` | Reduces a verified chain to selected first-step materials and selected last-step products, command, and byproducts |

The project owner signs Layout content. Functionaries sign Link content. The
verifier evaluates the resulting evidence under the effective Layout policy.

---

## 4. Wrapper and signature semantics

### 4.1 Raw carrier identity

The exact serialized metadata file is an evidence artifact:

```text
raw carrier identity
=
wrapper type
+
exact raw bytes
+
byte size
+
content digest
+
complete carried signature inventory
```

Raw carrier identity records what was received. Signature verification operates
on a separate wrapper-specific input.

### 4.2 Metablock signature input

A Metablock contains:

```text
signed:
Layout or Link payload

signatures:
signature records
```

Its signature input is the UTF-8 canonical JSON representation of the `signed`
payload:

```text
UTF-8(
  securesystemslib.formats.encode_canonical(
    attr.asdict(payload)
  )
)
```

Wrapper formatting and the signature collection are outside this signature
input.

### 4.3 DSSE signature input

A DSSE Envelope signature authenticates the PAE-encoded payload type and decoded
payload bytes.

For the reviewed classic in-toto profile:

```text
payload_type_bytes = UTF-8("application/vnd.in-toto+json")
payload_bytes = decoded envelope payload bytes

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

The four separators are literal ASCII space bytes (`0x20`). The reviewed
payload type is ASCII, so its string length equals its UTF-8 byte length in this
fixed profile.

### 4.4 Signature-verification scope

The layout-signature phase receives a non-empty set of verification keys. The
outer verifier calls the wrapper-specific verification path once for every
supplied key.

For each supplied key, the reviewed path establishes one matching valid
signature relation:

```text
supplied verification key
+
selected matching carried signature record
+
wrapper-specific signature input
→ verified relation for that supplied key
```

A Metablock selects the first matching signature record for the supplied key or
one of its subkeys. A DSSE Envelope performs threshold-one verification for the
single supplied key passed to that invocation.

Additional carried signature records remain separate inventory entries. Their
status is one of:

```text
verified_for_supplied_key
verification_failed_for_supplied_key
unmatched_to_supplied_keys
not_evaluated_by_upstream_path
```

The same separation applies to Link and sublayout carriers.

---

## 5. Official verification sequence

The reviewed library path performs the following sequence:

```text
1. validate one matching Layout signature relation for every supplied verification key
2. extract the original Layout payload
3. compare Layout.expires with the verifier-host current UTC clock
4. apply the exact substitution parameter map to the extracted Layout object
5. discover Link carriers through the link-directory filename convention
6. verify accepted Link signatures and effective-step functionary authorization
7. verify sublayouts recursively
8. compare reported commands with effective expected commands
9. verify threshold agreement over materials and products
10. evaluate effective step artifact rules
11. execute effective inspections and generate inspection Link results
12. evaluate inspection artifact rules
13. return a summary Link or raise a typed failure
```

The command-line path supplies the layout carrier, verification keys, link
directory, and inspection timeout. The library path also accepts substitution
parameters, an enclosing step name, and inspection-link persistence control.

A separate current PULSEmech release subject is not an upstream verifier input.

---

## 6. Identity stack

The previous sections define several identities that must remain separate. One
flat `path_identity` cannot safely represent all of them.

### 6.1 Raw evidence identity

```text
I_raw
=
exact raw carrier identities
+
wrapper types
+
complete carried signature inventories
```

This layer includes the root Layout carrier, discovered Link carriers, sublayout
carriers, and any persisted inspection carriers.

### 6.2 Authenticated content identity

```text
I_auth
=
wrapper-specific signature-input identities
+
selected verified key/signature relations
+
authenticated Layout, Link, and sublayout payload identities
```

This layer records authenticated content under the exact wrapper semantics. It
does not replace `I_raw`.

### 6.3 Effective Layout identity

The verifier mutates the extracted Layout object by substituting values into:

```text
step expected commands
step expected material rules
step expected product rules
inspection commands
inspection expected material rules
inspection expected product rules
```

The effective Layout identity is derived from the actual post-substitution
Layout content:

```text
I_effective_layout
=
identity of the complete substituted Layout object used by verification
```

The exact substitution map remains a separate verification-event input.

Two different substitution maps can produce identical effective Layout content
when their differences are unused. In that case:

```text
substitution-map identities differ
effective Layout identity is equal
planned path semantics are equal
verification-event input identities differ
```

A different effective Layout or another changed path-defining input produces a
different planned path.

### 6.4 Link-discovery binding identity

The verifier associates carriers with effective steps through directory lookup
using the `<step>.<keyid-prefix>.link` convention.

Each discovery binding preserves:

```text
link-directory root identity
relative directory-entry path and exact filename
effective step identity
full authorized key or subkey identity used to construct the lookup
key-ID prefix relation
loaded raw carrier identity
```

This association is part of the evidence path. The same signed carrier loaded
under another discovery entry represents another verifier input relation even
when its bytes and signature input remain unchanged.

### 6.5 Observed evidence-path identity

```text
I_observed_path
=
I_effective_layout
+
ordered Link-discovery bindings
+
accepted authenticated Link payload identities
+
threshold-selection results
+
sublayout delegation and nested-result identities
+
inspection result identities and execution outcomes
+
effective artifact-rule results
```

When inspections execute, each result contributes:

```text
effective inspection identity
executor boundary
return state
generated inspection Link payload identity
recorded materials and products
command and byproducts
persisted carrier identity when written
```

Inspection results are runtime evidence. They are part of the observed evidence
path rather than the planned Layout identity.

### 6.6 Verification-event identity

```text
I_verification_event
=
I_raw
+
I_auth
+
exact substitution-map identity
+
I_effective_layout
+
link-discovery bindings
+
I_observed_path
+
verifier and dependency identities
+
verification configuration
+
clock binding
+
terminal PASS or typed failure
```

Two events may share planned and observed path semantics while retaining
different event identities because an unused substitution input, clock state,
raw wrapper serialization, or other non-path event input differs.

### 6.7 PULSEmech current-run subject binding

The current release subject is connected after upstream verification through a
separate PULSEmech relation described in Section 9.

---

## 7. Evidence semantics and coverage

### 7.1 Declared artifact capture

A Link records the artifact paths supplied to the recording mechanism.

```text
materials
→ declared recorded pre-step artifact state

products
→ declared recorded post-step artifact state
```

This surface supports strong digest-bound artifact evidence. Its coverage is the
configured recording surface rather than a complete process trace.

### 7.2 Artifact rules

The effective Layout rule language provides these bounded relations:

```text
CREATE
→ recorded artifact absent before and present after

DELETE
→ recorded artifact present before and absent after

MODIFY
→ recorded artifact present before and after with different digest

MATCH
→ selected artifact path and digest continuity across named steps or inspections

ALLOW / DISALLOW / REQUIRE
→ policy constraints over the recorded artifact queues
```

These relations operate over declared paths, accepted Link evidence, and the
effective rule set.

### 7.3 Command alignment

The verifier compares a reported Link command with the effective expected
command. A mismatch produces a warning and does not by itself fail the complete
verification.

The evidence record therefore preserves:

```text
reported command
effective expected command
alignment result
warning-only enforcement state
```

### 7.4 Threshold scope

Threshold verification requires enough distinct authorized functionary
relations and agreement over:

```text
materials
products
```

Command, byproducts, environment, and time are outside that threshold-agreement
surface.

### 7.5 Summary Link scope

At the reviewed revision, the returned summary Link carries:

```text
materials from the selected first-step representative Link
products from the selected last-step representative Link
command from the selected last-step representative Link
byproducts from the selected last-step representative Link
```

The summary is a chain reduction. It does not preserve the internal discovery
bindings, all step records, rejected candidates, threshold details, rule
results, sublayout path, inspection results, or warnings.

---

## 8. Time, expiry, and replay

### 8.1 Transition-element time

The standard Link payload does not require event-time or observation-time
bindings for each step. Effective Layout order and MATCH continuity provide
logical and artifact dependency structure rather than measured wall-clock order.

PULSEmech therefore records transition-element time as:

```text
unbound
partially_bound
or
externally_bound_by_separate_evidence
```

### 8.2 Expiration clock

The reviewed verifier evaluates:

```text
parsed Layout.expires
<=
datetime.datetime.now(tz.tzutc())
```

The clock value is read from the verifier host during execution. The public API
does not receive or return that exact value.

A verification-event clock binding records:

```text
clock acquisition implementation
host and operating-system clock-source identity
synchronization or clock-control source where known
exact clock observation when instrumented
or bounded before/after observation interval
precision and uncertainty
trust state
parsed Layout.expires
comparison result
```

### 8.3 Replay classes

```text
controlled-clock end-to-end replay
→ verifier process consumes an identified controlled clock state

expiration-decision reconstruction
→ recorded expiry, clock observation, and comparison rule reproduce the decision

current-clock verification
→ new verification event under the current host clock
```

The PULSEmech reproduction axis uses the defined values from the Transition
Meter, with scope recorded separately. A current-clock rerun is not an exact
replay of the original expiration decision.

---

## 9. Artifact namespaces and current-run subject binding

### 9.1 Recorded in-toto artifact identity

An in-toto artifact reference combines:

```text
resolver or URI scheme
recorded path identity
digest algorithm and value
```

The recorded path may be affected by resolver configuration such as a base
path, path normalization, scheme handling, exclusions, or left-stripped
prefixes. The Link payload does not necessarily carry the complete recording
configuration that produced its path strings.

### 9.2 PULSEmech subject identity

The current-run PULSEmech subject belongs to a separately controlled namespace:

```text
current repository and source revision
workflow run and attempt
release-candidate identity
subject artifact namespace
subject canonical identifier
subject digest algorithm and value
```

### 9.3 Protected namespace mapping

Current-run binding uses a protected mapping policy rather than unexplained raw
path-string equality.

```text
current PULSE subject reference
+
protected subject-to-product namespace mapping
→ canonical in-toto product-space reference
```

The binding passes only when:

```text
mapped canonical subject reference
=
selected accepted product reference
```

and:

```text
subject digest algorithm and value
=
selected product digest algorithm and value
```

The mapping identity preserves its namespace roots, resolver or recording
assumptions, normalization rule, and selection policy. When recording provenance
or mapping inputs are insufficient, the path relation remains `unbound` even if
a digest happens to match.

### 9.4 Subject-binding result

```text
accepted upstream product evidence
+
exact PULSE current-run subject
+
protected product-selection rule
+
protected namespace mapping
+
canonical reference equality
+
digest equality
→ current-run subject binding
```

Historical evidence attached to a different current-run subject is rejected at
this boundary.

---

## 10. Transition Meter mapping

| Transition Meter object | Classic in-toto source | Recorded status |
|---|---|---|
| planned path | effective post-substitution Layout | directly derived from actual substituted output |
| source state | accepted Link materials | bound within the declared artifact-capture surface |
| target state | accepted Link or inspection products | bound within the declared artifact-capture surface |
| observed path evidence | discovery-bound accepted Links, nested sublayout results, inspection results | partial domain-specific path evidence |
| changed relation | CREATE, DELETE, MODIFY, and MATCH outcomes | deterministic artifact-relation mapping |
| participating entities | supplied Layout verification keys and accepted functionary signer relations | bound for the relations actually verified |
| event time | no required standard Link field | unbound unless separate evidence is admitted |
| observation time | no required standard Link field | unbound unless separate evidence is admitted |
| verifier time | verification-event and clock evidence | separately bound; distinct from step time |
| current-run subject | separate PULSEmech namespace mapping and digest relation | outside upstream PASS; separately bound |
| alternative paths | no complete native alternative-path model | unresolved unless separate analysis is added |
| reproduction | exact evidence replay under preserved execution and clock boundaries | `reproduced`, `bounded_replay_only`, `not_reproduced`, or `not_tested` by scope |
| causal state | classic in-toto does not evaluate necessity or sufficiency | `not_evaluated` or `sequence_only` |
| authority state | controlled by PULSEmech policy | `none` at this upstream boundary |

A positive normalized record uses the existing Transition Meter status vocabulary:

```text
observation_status:
partially_observed

binding_status:
partially_bound

consistency_status:
consistent

reproduction_status:
bounded_replay_only

causal_status:
sequence_only

authority_status:
none
```

The exact scope of each value is carried through evidence, verifier, Layout,
clock, discovery, inspection, and subject-binding references rather than by
inventing new status values.

---

## 11. Relation to existing PULSEmech evidence paths

### 11.1 SLSA/VSA

The implemented SLSA/VSA lane carries a verification summary with subject,
verifier, policy, input-attestation, result, and level information.

It does not losslessly carry the classic in-toto Layout carrier, signature-input
relations, effective Layout, discovery bindings, complete Link tree, thresholds,
artifact-rule results, sublayouts, inspections, clock boundary, or separate
current-run subject mapping.

### 11.2 Witness

Witness carries attestor lifecycle evidence, signed attestation collections,
signed policy, functionary checks, required-attestation and Rego results,
artifact-flow relations, VerificationSummary, and StepResults.

Classic in-toto provides a distinct layout/link, threshold, artifact-rule,
sublayout, and inspection mechanism.

A future PULSEmech carrier may use a shared software-supply-chain transition core
with upstream-specific profiles. This document leaves that decision open until
observed replay proves the required information boundary.

---

## 12. Domain and PULSEmech responsibilities

### 12.1 Classic in-toto domain verifier

The pinned upstream verifier owns:

```text
metadata parsing
wrapper-specific signature-input construction
signature and authorization evaluation
Layout expiration
substitution semantics
Link discovery
threshold semantics
sublayout recursion
artifact-rule semantics
inspection execution
summary Link construction
domain PASS or typed failure
```

### 12.2 Future adapter

A future adapter, if justified, preserves:

```text
source identities
raw carrier identities
authenticated content identities
effective Layout identity
exact substitution-map identity
link-discovery bindings
accepted, rejected, and ignored candidate state where exposed
threshold and rule results
sublayout result identities
inspection result identities and outcomes
clock boundary
domain result and warnings
coverage and unresolved-state information
```

The adapter records upstream results; it does not reimplement the in-toto
verifier.

### 12.3 PULSEmech

PULSEmech owns:

```text
current-run identity
subject namespace and digest identity
protected product selection and namespace mapping
subject-to-product binding
transition-element normalization
alternative-path and unresolved-edge preservation
replay classification
policy binding
authority separation
```

---

## 13. Bounded observed replay before implementation

A carrier decision follows one source-bound, non-authoritative observed replay.

### 13.1 Initial profile

The first replay uses:

```text
one exact in-toto revision
one exact dependency revision
one exact Layout carrier and verification-key set
one exact substitution map
one exact link-directory tree
one deterministic artifact set
inspection-free effective Layout
one exact verifier execution
one recorded clock boundary
one separate PULSE current-run subject-binding test
```

### 13.2 Required preservation

The replay preserves:

```text
raw Layout, Link, and sublayout carriers
wrapper types and signature inventories
signature-input identities and verified signer relations
effective Layout output identity
exact substitution-map identity
link-directory root and discovery bindings
accepted step evidence and threshold selections
artifact-rule outcomes
clock evidence and expiration result
summary Link and source representative Links
terminal result and warnings
current-run namespace mapping and subject-binding result
Transition Meter fields that remain unavailable
```

### 13.3 Required boundary cases

The replay includes:

```text
different substitution maps producing the same effective Layout
→ same planned path identity
→ different verification-event input identity

same carrier copied to another discovery filename
→ different discovery binding
→ replay must preserve the association actually evaluated

inspection-enabled later profile with different generated inspection results
→ different observed evidence-path identity

same upstream PASS with a different current-run subject digest
→ subject binding rejected

same digest with unresolved path namespace mapping
→ subject path binding remains unbound

same evidence before and after Layout expiry
→ separate clock-relative verification events
```

### 13.4 Decision outcomes

The replay may establish one of these results:

```text
existing VSA summary path is sufficient
shared software-supply-chain carrier is sufficient
classic in-toto profile extension is required
dedicated classic in-toto carrier is required
upstream result surface is insufficient
subject namespace mapping is insufficient
inspection boundary remains unresolved
no implementation is justified
```

The replay remains non-authoritative and does not register a candidate gate.

---

## 14. Development and authority boundary

The current PULSEmech connected-proof workstream remains the active
implementation path.

The classic in-toto sequence is:

```text
source-bound boundary record
→ bounded observed replay
→ carrier decision
→ adapter decision
→ non-active candidate decision
→ separate promotion decision
```

This document changes no dependency, schema, validator, workflow, policy,
registry, status semantics, gate set, release decision, or release authority.

---

## 15. Final position

Classic in-toto supplies a strong domain-native transition-evidence surface:

```text
signed planned supply-chain policy
+
discovery-bound authenticated step evidence
+
threshold agreement
+
artifact-state and artifact-continuity rules
+
nested supply-chain results
+
optional inspection results
→ effective-Layout-relative software-artifact-chain verification
```

PULSEmech adds the separate layers required for a current release transition:

```text
exact current-run subject
+
protected artifact-namespace mapping
+
subject-to-product binding
+
Transition Meter normalization
+
policy and authority control
```

The measured boundary is now explicit:

```text
classic in-toto domain PASS
→ upstream transition evidence

upstream transition evidence
+
current-run subject binding
→ admissible PULSEmech evidence relation

admissible evidence relation
+
separate PULSE policy
→ possible later release-transition decision
```

The next technical question is determined by observed replay rather than by an
assumed implementation lane.

---

## References

### PULSEmech

- [PULSEmech Transition Meter](../../PULSEMECH_TRANSITION_METER.md)
- [PULSEmech Technical Overview](../../PULSEMECH_TECHNICAL_OVERVIEW.md)
- [PULSEmech SLSA / in-toto evidence intake](../PULSE_SLSA_EVIDENCE_INTAKE_v0.md)
- [PULSEmech / SLSA provenance-to-transition alignment](../PULSEMECH_SLSA_PROVENANCE_TO_TRANSITION_v0.md)
- [PULSEmech Witness interoperability and release-authority boundary](PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md)

### Upstream source basis

- [in-toto implementation at the reviewed revision](https://github.com/in-toto/in-toto/tree/a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b)
- [in-toto specification at the reviewed revision](https://github.com/in-toto/specification/blob/6459afd8e94a332e423ba05c2862b534acbe741d/in-toto-spec.md)
- [securesystemslib at the reviewed revision](https://github.com/secure-systems-lab/securesystemslib/tree/6f774190b90f0aa9d5d7e077680adbaa29c5cd6c)
