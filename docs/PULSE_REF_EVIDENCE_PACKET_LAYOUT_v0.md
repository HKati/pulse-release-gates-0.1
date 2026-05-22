# PULSE-REF Evidence Packet Layout v0

**Status:** workshop layout specification  
**Scope:** PULSE-REF / release-grade reference evidence packet / canonical packet layout  
**Authority status:** non-normative planning and diagnostic document

## Core statement

A PULSE-REF release-grade reference is not merely a run.

A release-grade reference is a closed, digest-backed, reconstructable evidence packet.

This document defines a canonical packet layout for assembling that evidence packet.

The layout does not create release authority.

The layout preserves the artifact locations required to reconstruct the evidence-to-decision path.

## Normative release path

The normative PULSE release decision remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block decision
```

A PULSE-REF evidence packet preserves and reconstructs this path.

It does not replace it.

## Layout root

The canonical packet root is:

```text
pulse_ref_evidence_packet_v0/
```

This root may appear under a fixture, build artifact, release-reference package, or audit bundle.

Example fixture path:

```text
tests/fixtures/pulse_ref/evidence_packet_v0/
```

Example generated artifact path:

```text
artifacts/pulse_ref/evidence_packet_v0/
```

## Canonical directory layout

```text
pulse_ref_evidence_packet_v0/
  README.md
  package_manifest.json

  status/
    status.json

  policy/
    pulse_gate_policy_v0.yml
    pulse_gate_registry_v0.yml

  gates/
    materialized_gate_sets.json

  ci/
    ci_outcome.json

  release_authority/
    release_authority_manifest.json

  audit/
    release_authority_audit_bundle/
      report_card.html
      status.json
      release_authority_manifest.json

  digests/
    package_digests.json

  handoff/
    operator_handoff_report.json

  publication/
    publication_snapshot.json

  field/
    field_point_authority_map_v0.json

  admissibility/
    evidence_fold_in_admissibility_v0.json

  external/
    summaries/
      README.md

  hpc/
    hpc_evidence_bundle_v0.json

  recognition/
    recognition_surface_drift_v0.json

  reconstruction/
    reconstruction_instructions.md
```

## Required payload

The minimal release-grade reference packet should include:

| Path | Required | Role | Authority status |
|---|---:|---|---|
| `README.md` | yes | Human packet overview and authority boundary | non-normative |
| `package_manifest.json` | yes | Packet inventory and artifact references | audit / reconstruction |
| `status/status.json` | yes | Recorded release-state artifact | normative input for inspected decision path |
| `policy/pulse_gate_policy_v0.yml` | yes | Declared gate policy | normative input |
| `policy/pulse_gate_registry_v0.yml` | yes | Gate semantic registry | normative support / semantic stabilizer |
| `gates/materialized_gate_sets.json` | yes | Materialized required + release_required gate sets | normative input |
| `ci/ci_outcome.json` | yes | Declared-policy gate-enforcement CI outcome | normative enforcement / decision outcome |
| `release_authority/release_authority_manifest.json` | yes | Audit / trace manifest | non-normative trace surface |
| `audit/release_authority_audit_bundle/` | yes | Reconstructable audit bundle | non-normative audit surface |
| `digests/package_digests.json` | yes | Digest coverage for packet payload | audit / reconstruction |
| `handoff/operator_handoff_report.json` | yes | Operator reconstruction report | audit / operator surface |
| `publication/publication_snapshot.json` | yes | Publication identity snapshot | non-normative publication surface |
| `field/field_point_authority_map_v0.json` | yes | Field-point role and authority map | non-normative diagnostic surface |
| `admissibility/evidence_fold_in_admissibility_v0.json` | yes | Candidate evidence fold-in admissibility state | non-normative diagnostic surface |
| `external/summaries/` | conditional | Canonical external summaries when required | candidate evidence / policy-routed evidence |
| `hpc/hpc_evidence_bundle_v0.json` | conditional | HPC evidence bundle when compute-scale evidence is used | non-normative diagnostic evidence surface |
| `recognition/recognition_surface_drift_v0.json` | optional | Recognition-surface drift diagnostic | non-normative diagnostic surface |
| `reconstruction/reconstruction_instructions.md` | yes | Human reconstruction instructions | non-normative operator surface |

## Required identity fields

Every generated packet should preserve at least:

- packet ID;
- run ID;
- run attempt;
- run key;
- git SHA;
- created UTC;
- packet schema / layout version;
- source repository;
- status artifact path;
- status artifact SHA-256;
- policy path;
- policy SHA-256;
- gate registry path;
- gate registry SHA-256;
- materialized gate-set path;
- materialized gate-set SHA-256;
- CI outcome URL or run URL where available;
- package digest manifest path.

## Package manifest role

`package_manifest.json` records the packet inventory.

It should reference the canonical payload files by path and digest.

It should not create release authority.

It should set:

```json
{
  "authority_boundary": {
    "creates_release_authority": false
  }
}
```

The package manifest may help reconstruct the decision trail.

It must not become a second release-decision engine.

## Digest manifest role

`digests/package_digests.json` records SHA-256 digests for packet payload files.

The digest manifest must cover:

- `README.md`;
- `package_manifest.json`;
- `status/status.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `handoff/operator_handoff_report.json`;
- `publication/publication_snapshot.json`;
- `field/field_point_authority_map_v0.json`;
- `admissibility/evidence_fold_in_admissibility_v0.json`;
- any included external summary;
- any included HPC evidence bundle;
- any included recognition-surface diagnostic.

The digest manifest must not create release authority.

## Status artifact role

`status/status.json` is the recorded release-state artifact for the inspected decision path.

For a release-grade packet, it should show:

- `metrics.run_mode = "prod"`;
- release-grade status contract validity;
- explicit diagnostics object;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- required gates as literal boolean `true`;
- release_required gates as literal boolean `true`;
- detector evidence materialized when required;
- external evidence present and all pass where required.

A core or smoke status is not sufficient for a release-grade evidence packet.

## Policy and registry role

`policy/pulse_gate_policy_v0.yml` defines the required gate sets.

`policy/pulse_gate_registry_v0.yml` stabilizes gate ID meaning.

Both must be packet-bound by digest.

The materialized gate-set artifact must be consistent with both.

## Materialized gate-set role

`gates/materialized_gate_sets.json` records:

- required gates;
- release_required gates;
- effective required gates;
- policy path;
- policy digest;
- selected release lane / policy set.

This file must match the declared policy.

It must not be hand-edited to satisfy release evidence.

## CI outcome role

`ci/ci_outcome.json` records the declared-policy gate-enforcement outcome.

The CI outcome must be bound to:

- run ID;
- run attempt;
- run key;
- git SHA;
- workflow name;
- gate check conclusion;
- run URL where available;
- authority boundary stating it does not create release authority by itself.

The CI outcome is release-relevant only as the enforcement result of the declared normative path.

## Release authority manifest role

`release_authority/release_authority_manifest.json` records the evidence-policy-evaluator chain for audit and traceability.

It must be non-normative.

It must not change:

- `status.json`;
- declared gate policy;
- materialized required gate set;
- `check_gates.py`;
- CI outcome;
- release semantics.

## Audit bundle role

`audit/release_authority_audit_bundle/` preserves a reconstructable view of the release-authority trail.

It may include:

- report card;
- status artifact copy;
- release authority manifest copy;
- supporting HTML or summary surfaces.

It is audit / reconstruction only.

It does not create a second release-decision path.

## Field-point authority map role

`field/field_point_authority_map_v0.json` classifies packet field points by:

- field point ID;
- surface type;
- authority status;
- relation to the normative materialization path;
- whether it can affect release decisions;
- whether policy routing exists where required.

This prevents packet surfaces from being misread.

Every field-point claim requires authority-role classification.

## Evidence fold-in admissibility role

`admissibility/evidence_fold_in_admissibility_v0.json` records whether non-normative candidate evidence may enter a future fold-in process.

It does not fold evidence into `status.json`.

It does not authorize release.

Rule:

```text
unsupported fold-in state
→ no recorded release evidence
```

## External evidence role

`external/summaries/` contains canonical external detector summaries when required.

The external evidence directory should not accept decoy or non-canonical summaries as release-grade evidence.

Release-grade external evidence should be:

- canonical;
- schema-valid where a schema exists;
- digest-backed;
- verified;
- folded into `status.json` only through declared evidence contracts;
- policy-routed before affecting required gates.

Presence alone is not enough.

Aggregate pass alone is not enough.

## HPC evidence role

`hpc/hpc_evidence_bundle_v0.json` is included only if compute-scale evidence is used.

HPC output does not create release authority.

HPC output becomes useful to the packet only when it is materialized, recorded, digest-backed, reconstructable, role-classified, and verified.

## Recognition-surface diagnostic role

`recognition/recognition_surface_drift_v0.json` is optional.

It may inspect whether non-normative recognition surfaces alter analyzer interpretation.

It does not create analytic authority.

Rule:

```text
unsupported recognition state
→ no analytic authority
```

## Reconstruction instructions

`reconstruction/reconstruction_instructions.md` should explain how to reconstruct:

- packet identity;
- run identity;
- status artifact identity;
- policy and registry identity;
- materialized gate set;
- CI outcome;
- release authority manifest;
- audit bundle;
- digest manifest;
- field-point authority map;
- evidence fold-in admissibility;
- optional external / HPC / recognition evidence.

The instructions should identify which artifacts are normative inputs, which are enforcement outputs, and which are non-normative reconstruction or publication surfaces.

## Canonical layout invariant

A PULSE-REF evidence packet should not invent arbitrary top-level paths for core artifacts.

Canonical paths reduce verifier ambiguity.

The following paths are canonical:

- `status/status.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `digests/package_digests.json`;
- `handoff/operator_handoff_report.json`;
- `publication/publication_snapshot.json`;
- `field/field_point_authority_map_v0.json`;
- `admissibility/evidence_fold_in_admissibility_v0.json`.

## Forbidden interpretations

The packet layout must not be interpreted as:

- a second release-decision engine;
- a replacement for `status.json`;
- a replacement for declared gate policy;
- a replacement for materialized required gates;
- a replacement for strict CI gate enforcement;
- a publication badge;
- a dashboard state;
- a DOI record;
- a README claim;
- a report-only state.

## Safe interpretation

The packet layout may be interpreted as:

- a canonical evidence packet shape;
- a reconstruction aid;
- a verifier target;
- a future fixture layout;
- a release-grade reference planning surface;
- a non-normative field-state closure document.

## Next step after this layout

After this layout is accepted, the next step may be:

- create a minimal fixture directory under `tests/fixtures/pulse_ref/evidence_packet_v0/`;
- add placeholder but schema-valid packet artifacts;
- add a package manifest;
- add digest coverage;
- run the RA1 verifier or a packet-layout checker;
- record the result as non-normative until real release-grade evidence is materialized.

## Summary

A release-grade PULSE reference is not merely a run.

It is a closed, digest-backed, reconstructable evidence packet.

This layout defines where each packet field point belongs.

The packet preserves the release-authority path but does not replace it.

Release authority remains bound to:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
```


