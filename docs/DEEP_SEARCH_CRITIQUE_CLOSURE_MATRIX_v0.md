# Deep Search Critique Closure Matrix v0

## Purpose

Deep Search Critique Closure Matrix v0 records how the major review findings
were resolved in the PULSE repository.

The matrix now separates:

```text
closed internal technical findings
closed bounded mechanical proof findings
ongoing maintenance invariants
external adoption or institutional-maturity items
optional presentation or ecosystem work
```

This separation corrects a category error:

```text
mechanically reproducible verification
≠
requirement for a privileged external validating authority
```

A third party may reproduce a verification result.

The third party does not create the result's truth value.

This document is a review / audit carrier.

It does not change release authority.

## Authority carrier

The PULSEmech release-authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The Device Ledger proof and its runnable iPhone demonstrator remain separate
non-authorizing proof surfaces:

```text
carrier_class:
diagnostic_shadow

authority_effect:
none

external_validation_claim:
none
```

## Mechanical verification boundary

The bounded Device Ledger proof establishes:

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
→
bounded mechanical validity
```

The following distinctions are normative:

```text
separately implemented verifier
≠
external validating authority

functional implementation separation
≠
organizational-independence requirement

external reproduction event
≠
source of mechanical validity

institutional status
≠
verification input
```

The verifier is separate because it reconstructs the result from exact artifact
bytes without trusting a producer verdict.

Its operator's identity, title, affiliation, reputation or institutional status
does not enter the verification equation.

## Closure matrix

| Review finding | Closure layer | Current status | Remaining note |
|---|---|---|---|
| Public Pages / Quality Ledger could be misread as release-grade evidence | Public reader-surface state + reader-carrier wording | Closed internally | Later visual polish may strengthen presentation but is not a correctness blocker |
| Need clear authority-impact audit checklist | `AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md` | Closed | Human review checklist; not a second decision engine |
| Need cryptographic provenance / attestation binding | Release Authority Cryptographic Binding boundary + Artifact Provenance Binding v0 + attestation subject / workflow | Closed internally | Attestation verifies a binding carrier; it does not replace the PULSEmech authority path |
| Need normative vs shadow inventory report | Normative vs Shadow Inventory Model v0 + builder/tests + classifier + `NORMATIVE_SHADOW_INVENTORY_REPORT_ARTIFACT_POLICY_v0.md` | Closed internally | Selected audit-record model is `run-on-demand reviewer output`; generated reports are review evidence, not source or repository-state authority |
| Shadow layers may drift into implicit authority | Normative/shadow builder + current first-party workflow classification + drift regression | Closed for the current repository state | Every future workflow must receive an explicit carrier-role classification; this is an ongoing maintenance invariant |
| Need independently reproducible verification | Device Ledger exact `.pulseledger` + separately implemented verifier + positive and relevant negative round-trip proof | Closed for the bounded Device Ledger claim | Reproduction is determined by exact carrier bytes and verifier mechanics, not by operator status |
| Need an external verification path | `EXTERNAL_VERIFICATION_PATH_v0.md` + `EXTERNAL_VERIFICATION_PACKET_v0.md` + Device Ledger reproduction entrypoint | Closed as a review and reproduction path | An external execution is optional evidence of reproduction; it is not a prerequisite of mechanical validity and does not create authority |
| Public surface core / demo / prod separation should be stronger | Public reader wording + explicit `synthetic_reference`, `fixture_installation`, `diagnostic_shadow` and authority boundaries | Closed mechanically; presentation polish remains optional | The runnable demonstrator does not claim a live production observation session |
| Crypto provenance should align with in-toto / SLSA / attestation systems | Artifact provenance binding, GitHub artifact attestation wiring, SLSA/VSA candidate path and Witness boundary record | Closed as the current implementation layer | Broader ecosystem mappings may be added without redefining PULSEmech identity |
| Need clearer maintainer / governance boundary | `MAINTAINER_AUTHORITY_BOUNDARY_v0.md` | Closed for the current single-maintainer model | Multi-maintainer quorum or rotation is a later governance-adoption layer |
| PULSE is not yet institutionally mature | Maintainer boundary + external review/reproduction surfaces + machine-operable proof records | Separate external maturity status, not a mechanical-validity finding | Adoption, independent audits and institutional standardization require external actors but do not reopen the internal proof |

## Device Ledger bounded mechanical proof closure

The completed bounded relation is:

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
→ minimal runnable iPhone result surface
→ exact artifact export
```

Canonical proof record:

```text
docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md
```

Merged implementation identity:

```text
implementation PR:
#2847

squash-merge commit:
6a358187d8fde7321963b76cc50cc77fad695dd0
```

The successful reference relation requires:

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256

carrier size:
133568 bytes

carrier SHA-256:
a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3

verifier result:
verified_with_declared_unavailability

verifier checks:
49 / 49 passed

checkpoint signature:
verified

package signature:
verified
```

The positive proof requires:

```text
Swift-produced carrier
=
checked-in exact reference carrier

same carrier
→ separately implemented verifier
→ exact canonical PASS report
```

Repeated verification requires byte-identical report output.

The relevant negative proof preserves ZIP structure and CRC consistency, changes
the package signature, and requires:

```text
same verifier
→ package-signature equation boundary
→ package_signature_valid = failed
→ fail-closed rejection
```

The proof therefore establishes both:

```text
exact admissible carrier
→ PASS
```

and:

```text
structurally admissible but cryptographically modified carrier
→ FAIL
```

The app does not execute or import the Python verifier.

It admits only the exact pinned canonical verifier report after binding that
report to the exact carrier produced by the current deterministic Swift run.

## External reproduction is optional, not constitutive

Anyone may run:

```text
tools/verify_pulsemech_device_ledger_v0.py
```

over the exact `.pulseledger`.

That execution may produce:

```text
a reproduction note
an independent audit record
a case study
an integration test
an external review report
```

These are valid external records.

They do not become:

```text
the source of proof validity
a required approval
an institutional truth oracle
release authority
device-control authority
```

The mechanical result remains a function of:

```text
exact input artifact
+
declared verification contract
+
verifier implementation
```

not:

```text
who ran the verifier
which institution employed the operator
which title or reputation the operator held
```

## Normative / shadow inventory closure

The repository now carries an explicit generated-report artifact policy:

```text
docs/NORMATIVE_SHADOW_INVENTORY_REPORT_ARTIFACT_POLICY_v0.md
```

The selected model is:

```text
run-on-demand reviewer output
```

Under this model, internal closure is based on:

```text
inventory model exists
builder exists
tests exist
workflow-family classifier coverage exists
reviewer can generate JSON and Markdown reports for an exact commit
unclassified workflow drift is absent or explicitly reported
generated outputs remain outside the repository by default
working tree remains clean after generation
```

A checked-in generated report is not required for this audit model.

Generated inventory outputs remain:

```text
review evidence
≠ source files
≠ repository-state authority
≠ release-authority artifacts
```

The current first-party workflow set is classified.

The Device Ledger demonstrator workflow is explicitly classified as:

```text
carrier_class:
diagnostic_shadow

release_path_participation:
false

required_gate_participation:
false
```

A future new or renamed workflow must be classified before the current-repository
closure claim can be carried forward to that later state.

## Added and clarified internal layers

The following internal layers are implemented or explicitly recorded:

```text
Public reader-surface boundary
Release Authority Cryptographic Binding boundary
Artifact Provenance Binding v0
Artifact binding builder
Artifact binding verifier
Artifact binding schema
Artifact binding CI materialization
Artifact binding attestation subject
Isolated attestation job
Authority Impact Audit Checklist v0
External Verification Path v0
External Verification Packet v0
Normative vs Shadow Inventory Model v0
Normative vs Shadow Inventory Report builder and tests
Normative vs Shadow Inventory Report Artifact Policy v0
Maintainer Authority Boundary v0

Device Ledger canonical record chain
Device Ledger terminal checkpoint
checkpoint signature
exact payload inventory
canonical manifest
package signature
deterministic .pulseledger carrier
separately implemented standalone verifier
positive Swift-to-verifier reproduction
repeated deterministic reproduction
relevant fail-closed package-signature rejection
minimal runnable iPhone demonstrator
exact .pulseledger export
canonical bounded proof document
```

These layers close the internal technical findings identified above.

## Ongoing internal maintenance invariants

The following are continuing invariants, not unresolved proof findings:

```text
classify every new workflow by carrier role
keep diagnostic and shadow workflows outside release authority
run inventory reports against an exact commit
keep generated inventory outputs outside the repository by default
preserve a clean working tree after review-only generation
update canonical documentation when implementation state changes
treat any wider Device Ledger claim as a separate scoped workstream
preserve authority_effect = none for the bounded demonstrator
preserve external_validation_claim = none
```

Changing the selected inventory audit-record model requires a separate explicit
documentation and implementation decision.

Adding production device identity, live observation, persistent storage,
platform attestation or device-security claims also requires a new, wider claim
and separate proof boundary.

## External adoption and maturity items

The following activities require actors or adoption outside the repository:

```text
third-party reproduction event
external case study
independent audit
consumer integration
external deployment experience
multi-maintainer governance adoption
institutional standardization
```

These activities may provide evidence of adoption, use, review quality or
institutional maturity.

They are not prerequisites for the bounded mechanical validity already
established.

```text
external adoption:
separate

institutional maturity:
separate

bounded mechanical proof:
closed
```

## Optional later work

The following items are not blockers for the completed proof:

```text
stronger visual separation in public Pages / Quality Ledger
stable published inventory report if the report-artifact policy changes
broader formal ecosystem mapping
external case studies
multi-maintainer quorum or rotation charter
additional production iPhone functionality under a separately declared claim
```

Optional work must not silently change the subject of the closed proof.

## Review boundary

This matrix is a review carrier.

It does not alter:

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
standalone verifier implementation
reference artifact bytes
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

The Device Ledger demonstrator remains:

```text
diagnostic_shadow
authority_effect = none
external_validation_claim = none
```

## Closure status

Internally closed:

```text
public reader ambiguity is bounded
authority-impact review checklist exists
cryptographic provenance binding exists
binding verification exists
attestation subject and carrier exist
maintainer authority boundary exists
normative / shadow inventory model exists
inventory builder and tests exist
inventory report artifact policy is explicit
current first-party workflow families are classified
external review and reproduction paths exist
```

Bounded Device Ledger proof closed:

```text
exact record chain
terminal checkpoint
canonical ledger
checkpoint signature
canonical manifest
package signature
deterministic .pulseledger
separately implemented verifier
positive reproduction
repeated deterministic reproduction
relevant fail-closed rejection
minimal runnable iPhone demonstrator
exact artifact export
```

Separate external maturity work:

```text
third-party adoption
independent external audit
external case study
multi-maintainer governance
institutional standardization
```

No external actor is required to create the proof's truth value.

## Mechanical conclusion

PULSE has moved from:

```text
CI-bound artifact authority with first-party governance documentation
```

to:

```text
artifact-bound release authority
+ public reader boundary
+ digest-backed provenance binding
+ isolated attestation carrier
+ authority-impact review checklist
+ external review and reproduction path
+ normative / shadow inventory model, builder and explicit artifact policy
+ maintainer authority boundary
+ exact Device Ledger artifact proof
+ separately implemented verifier
+ positive and relevant negative reproduction proof
+ minimal runnable iPhone demonstrator
+ exact .pulseledger export
```

The internal technical question is closed for the bounded Device Ledger claim:

```text
Can the same result be reconstructed from the exact artifact without a
privileged external validating authority?

yes
```

The external maturity question remains separate:

```text
Will external actors adopt, reproduce, audit or standardize the mechanism?

external adoption state
```

The second question does not reverse or condition the first.

```text
normative_shadow_inventory_audit_record_model:
run-on-demand reviewer output

bounded mechanical self-proof:
closed

minimal runnable iPhone bounded proof demonstrator:
closed

authority_effect:
none

external_validation_claim:
none

broader product development:
separate

external adoption and institutional maturity:
separate
```
