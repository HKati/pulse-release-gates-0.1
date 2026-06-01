# Release Authority Attestation Subject v0

## Purpose

Release Authority Attestation Subject v0 defines the primary attestation subject for the PULSE release-authority artifact relationship.

The primary attestation subject is:

```text
artifact_provenance_binding_v0.json
```

The attestation layer binds the provenance carrier that already records the digest-backed artifact relationship around the PULSEmech authority path.

This document defines the attestation subject boundary before any workflow-level attestation wiring is introduced.

## Carrier roles

| Carrier | Artifact / path | Mechanical role |
|---|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement | Carries release authority |
| Binding carrier | `artifact_provenance_binding_v0.json` | Carries the digest-backed artifact relation |
| Verification carrier | `verify_artifact_provenance_binding_v0.py` | Recomputes and checks the binding relation |
| Reader carrier | Quality Ledger | Presents recorded state |
| Trace carrier | release authority manifest / release decision artifact | Preserves reconstruction and decision trace |
| Attestation subject | `artifact_provenance_binding_v0.json` | Primary subject for later cryptographic attestation |
| Attestation carrier | later cryptographic attestation over the binding carrier | Attests the binding carrier |

## Authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

This path carries the release-authority mechanism.

## Binding carrier

The binding carrier is:

```text
artifact_provenance_binding_v0.json
```

The binding carrier records the artifact relationship around the PULSEmech authority path.

It carries:

```text
recorded run identity
+ git SHA
+ status.json digest
+ declared gate policy digest
+ workflow-effective required gate set digest
+ strict CI gate-enforcement result
+ release-decision materialization record
+ Quality Ledger reader artifact digest
+ release authority manifest digest
+ binding subjects
+ binding hash
```

## Primary attestation subject

The primary attestation subject is the binding carrier:

```text
artifact_provenance_binding_v0.json
```

Mechanical role:

```text
artifact_provenance_binding_v0.json
= compact attestation subject for the recorded release-authority artifact relationship
```

The attestation subject is compact because the binding carrier already records the artifact graph.

## Carried artifact relationship

The attestation subject carries the relationship between:

- recorded run identity,
- source commit identity,
- `status.json`,
- declared gate policy,
- workflow-effective materialized required gate set,
- strict CI gate-enforcement result,
- release-decision materialization artifact,
- Quality Ledger reader artifact,
- release authority manifest / trace artifact,
- binding subject list,
- binding hash.

The attestation layer later verifies the binding carrier as the recorded artifact relationship.

## Subject boundary

The attestation subject boundary is:

```text
primary subject:
artifact_provenance_binding_v0.json

carried relation:
status.json
+ declared gate policy
+ workflow-effective materialized required gate set
+ strict CI gate-enforcement result
+ release-decision materialization artifact
+ Quality Ledger reader artifact
+ release authority manifest / trace artifact
+ binding_hash
```

The subject boundary keeps attestation graph-shaped instead of file-scattered.

## Verification before attestation

The binding carrier is verified before attestation.

Verification carrier:

```text
verify_artifact_provenance_binding_v0.py
```

The verifier recomputes:

- bound file digests,
- inline object digests,
- workflow-effective gate-set digest,
- strict CI gate-enforcement digest,
- binding subject digests,
- `binding_hash`.

Attestation is introduced after the binding carrier verifies.

## Attestation target model

The later attestation workflow should attest:

```text
artifact_provenance_binding_v0.json
```

and should preserve the binding hash as the compact digest of the release-authority artifact relation.

Suggested attestation subject record:

```text
subject path:
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json

subject role:
release-authority artifact binding carrier

subject digest:
sha256 of artifact_provenance_binding_v0.json

carried digest:
binding_hash
```

## Mechanical order

The release-authority cryptographic path is introduced in this order:

```text
1. PULSEmech authority path
2. Artifact Provenance Binding v0
3. Binding verification
4. Attestation subject declaration
5. Later cryptographic attestation workflow
```

This document defines step 4.

## Future workflow boundary

A later workflow-level attestation PR may add:

```text
ci(crypto): attest release authority artifact binding
```

Expected future mechanics:

```text
build artifact_provenance_binding_v0.json
→ verify artifact_provenance_binding_v0.json
→ attest artifact_provenance_binding_v0.json
→ upload attestation / provenance record
```

That future workflow must preserve:

- PULSEmech decision semantics,
- gate policy,
- `check_gates.py` behavior,
- status schema,
- Quality Ledger renderer behavior,
- release tags,
- DOI / Zenodo path.

## Boundary held by this document

This document declares the attestation subject boundary only.

It defines:

```text
artifact_provenance_binding_v0.json
= primary attestation subject
```

and:

```text
later cryptographic attestation
= attestation carrier over the binding carrier
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The binding carrier remains:

```text
artifact_provenance_binding_v0.json
```

The verification carrier remains:

```text
verify_artifact_provenance_binding_v0.py
```
