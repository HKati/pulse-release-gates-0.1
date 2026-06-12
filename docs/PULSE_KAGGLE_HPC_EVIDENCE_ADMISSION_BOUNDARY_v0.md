# Kaggle / HPC Evidence Admission Boundary v0

## Scope

This document records the Kaggle / HPC evidence-admission boundary for PULSE.

Kaggle / HPC material may be useful as diagnostic, reproducibility, benchmark, or candidate-evidence context.

It does not create release authority.

## Core boundary

```text
Kaggle trace ≠ trusted verifier
HPC benchmark ≠ verified evidence
HPC evidence bundle ≠ verified relation
notebook result ≠ gate materialization
public competition output ≠ release authority
```

Kaggle / HPC material must not create or enable:

```text
VERIFIED
trusted provenance
verified provenance
verified evidence
verified_artifacts
relation_bindings
relation satisfaction
gate materialization
status.json writing
release_authority_v0.json writing
release-authority audit bundles
policy changes
registry changes
check_gates.py changes
CI allow/block changes
--release-grade-materialized
release authority
```

## Safe staged admission path

The safe v0 admission path is:

```text
external Kaggle / HPC material
→ downloaded artifact or local packet
→ sha256-bound diagnostic evidence bundle
→ optional future candidate-evidence reference
→ future trusted verifier only
→ no release authority unless recorded, bound, checked, policy-routed,
   materialized, and enforced by strict fail-closed CI
```

The canonical PULSEmech release-authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ CI allow/block release decision
```

## Reproducibility boundary

An external URL is not recorded evidence.

A screenshot is not artifact-bound evidence.

A notebook pass is not release authority.

A reproducibility packet is not release authority.

A Kaggle public URL may be useful as metadata or external reference, but it is not sufficient as evidence by itself.

A notebook output is not sufficient unless its produced artifacts are recorded, digest-bound, and reconstructable.

A downloaded artifact must have a recorded SHA-256 digest before it can serve as diagnostic evidence.

If Kaggle state is unavailable, mutable, inaccessible, or not hash-verifiable, it remains unavailable external state, not verified evidence.

## Minimal diagnostic metadata

A future Kaggle / HPC diagnostic record may include:

- competition or dataset identifier
- notebook identifier
- notebook version
- run timestamp
- producer / author metadata
- input dataset references
- output artifact path
- output artifact SHA-256
- runtime / environment summary
- hardware or accelerator class
- reproducibility command
- license / terms note
- source URL or external reference

These fields are diagnostic metadata.

They do not create trust.

They do not verify evidence.

They do not satisfy relations.

They do not materialize gates.

## Current v0 admission rule

For current v0, Kaggle / HPC material should enter only as diagnostic or candidate evidence context.

The safest technical wrapper is a non-authoritative HPC evidence bundle.

The bundle may record:

- run identity
- code identity
- input manifest identity
- environment
- evidence items
- metrics
- provenance
- reconstruction instructions
- result metadata

The bundle remains diagnostic.

The bundle must not create release authority.

## Fold-in boundary

For Kaggle / HPC v0 admission, diagnostic evidence should remain folded out of status authority by default.

Recommended v0 default:

```text
folded_into_status = false
```

If a future policy proposes fold-in, that must be a separate review with declared policy routing, materialized required gates, and strict fail-closed CI enforcement.

## Relation and gate boundary

The following transitions are forbidden in current v0:

```text
Kaggle notebook → verified_artifact
HPC bundle → relation_binding
benchmark success → detector_materialized_ok
external run → trusted verifier
public result → release gate
```

Kaggle / HPC evidence must not currently:

- add required gates
- change policy
- change registry
- materialize detectors_materialized_ok
- satisfy external_summaries_present
- satisfy refusal_delta_evidence_present
- affect check_gates.py
- affect CI allow/block decision

## Future hardening roadmap

Future work may evaluate:

- artifact attestation
- producer identity
- notebook provenance
- dataset provenance
- environment capture
- reproducible run logs
- hash chains
- in-toto / SLSA-style evidence chains
- GitHub artifact attestations
- Kaggle external-state drift handling

These are staged hardening items.

They are not current release authority.

## Mechanical anchor

Kaggle / HPC can be a useful external stress surface.

It is not a release-authority path.

Kaggle / HPC material becomes release-relevant only if it is recorded, bound, checked, promoted through declared policy, materialized as required gates, and enforced by strict fail-closed CI.
