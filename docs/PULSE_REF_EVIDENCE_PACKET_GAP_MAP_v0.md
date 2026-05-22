# PULSE-REF Evidence Packet Gap Map v0

Status: workshop gap map  
Scope: PULSE-REF / release-grade reference evidence packet / field-instrument development  
Authority status: non-normative planning and diagnostic document

## Core statement

A release-grade PULSE reference is not merely a run.

A release-grade reference is a closed, reconstructable evidence packet.

The packet must preserve the evidence field from which release authority could be evaluated under declared policy.

This document maps the gap between the current verified PULSE field state and a future non-stubbed, materialized-evidence, release-grade reference packet.

This document does not create release authority.

## Normative release path

The normative PULSE release decision remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

A release-grade evidence packet may preserve, reconstruct, and verify that path.

It does not replace it.

## Current field state

The current PULSE field state includes defined, validated, and buildable diagnostic / evidence / authority-role surfaces:

- `recognition_surface_drift_v0`
- `hpc_evidence_bundle_v0`
- `evidence_fold_in_admissibility_v0`
- `field_point_authority_map_v0`

These surfaces are non-normative unless their outputs are explicitly routed through declared policy and enforced as required gates.

The current state is a verified field state.

It is not a final architecture.

It is not a frozen endpoint.

## Why a gap map is needed

A core or smoke run can demonstrate that the mechanism runs.

A release-grade reference packet must demonstrate that release-grade evidence was materialized, recorded, verified, routed, enforced, preserved, and reconstructable.

The gap map prevents this mistake:

core / smoke / diagnostic / reader surface  
→ mistaken for release-grade evidence

The PULSE pre-materialization rule remains:

unsupported evidence state  
→ no release authority

The extended field-instrument rules remain:

unsupported recognition state  
→ no analytic authority

unsupported compute output  
→ no release authority

unsupported fold-in state  
→ no recorded release evidence

unclassified field point  
→ no authority-role interpretation

## Evidence packet definition

A PULSE-REF release-grade evidence packet should contain, at minimum:

1. release-grade `status.json`;
2. declared gate policy;
3. gate registry;
4. materialized required + release-required gate set;
5. CI gate-enforcement outcome;
6. release authority manifest;
7. release authority audit bundle;
8. package digest manifest;
9. operator handoff report;
10. publication snapshot;
11. external evidence summaries where required;
12. no-stub / no-scaffold diagnostic proof;
13. field-point authority map;
14. evidence fold-in admissibility state;
15. optional HPC evidence bundle if compute-scale evidence is used;
16. reconstruction instructions.

The packet must be digest-backed.

The packet must be run-bound.

The packet must be commit-bound.

The packet must preserve artifact identity.

## Gap table

| Packet component | Required release-grade state | Current / known state | Gap | Authority status | Next action |
|---|---|---|---|---|---|
| `status.json` | `run_mode=prod`, release-grade status contract valid, all effective required gates literal `true` | Core / diagnostic public states may exist; release-grade packet not yet finalized | Need non-stubbed prod reference status | Normative input when recorded for the decision path | Produce release-grade status artifact |
| Declared gate policy | Policy file recorded, digest-backed, and referenced by packet | Policy exists and is used for gate materialization | Need packet-bound digest and path | Normative input | Include policy artifact + digest |
| Gate registry | Registry recorded, digest-backed, and consistent with policy | Registry exists and supports gate semantics | Need packet-bound digest and path | Normative support / semantic stabilizer | Include registry artifact + digest |
| Materialized required gate set | Required + release_required gate set materialized from declared policy | Materialization tools exist | Need release-grade materialized gate-set artifact | Normative input | Produce materialized gate-set JSON |
| Strict CI gate enforcement | Declared-policy gate-enforcement CI outcome recorded | CI enforcement exists; not every CI green is release decision | Need release-grade CI outcome bound to packet | Normative enforcement / decision outcome | Record CI outcome artifact |
| External summaries | Canonical summaries present, parsed, folded, and aggregate pass verified where required | External evidence machinery exists; current public core states may not include release-grade external evidence | Need canonical release-grade external evidence | Candidate evidence → policy-routed evidence | Produce canonical summaries |
| `detectors_materialized_ok` | Literal `true`, backed by non-stub detector materialization | Core/stub states can show false or diagnostic-only values | Need real detector materialization | Required evidence gate | Materialize detector evidence |
| `external_summaries_present` | Literal `true` under release-grade strict path | Machinery exists | Need canonical release-grade summary presence | Required evidence gate | Record summary presence |
| `external_all_pass` | Literal `true` from recognized, folded, verified summaries | Machinery exists | Need verified aggregate pass | Required evidence gate | Fold and verify summaries |
| No-stub diagnostics | `diagnostics.gates_stubbed=false`, `diagnostics.scaffold=false` | Core smoke may be stubbed/scaffolded | Need explicit no-stub / no-scaffold proof | Release-grade diagnostic requirement | Produce non-stub status |
| Release authority manifest | Audit / trace manifest created, schema-valid, non-normative, bound to status/policy/gates/CI | Manifest tools exist | Need packet-bound manifest | Audit / trace surface | Generate manifest for packet |
| Audit bundle | Bundle preserves report, status, manifest, and relevant artifacts | Audit bundle surface exists | Need packet-bound audit bundle | Audit / reconstruction surface | Assemble bundle |
| Package digest manifest | All packet payload files covered by digests | Verifier/digest tooling exists | Need complete digest coverage | Audit / reconstruction support | Generate digest manifest |
| Operator handoff report | Handoff reconstructs status source, gate mode, effective gates, and authority boundary | Handoff tools exist | Need packet-bound handoff | Audit / operator reconstruction | Generate handoff report |
| Publication snapshot | Publication metadata bound to same run / commit / package identity | Publication surfaces exist | Need run-bound publication snapshot | Publication surface / non-normative | Generate publication snapshot |
| RA1 verifier report | Verifier passes package structure, digests, schema, authority boundary, and cross-artifact consistency | RA1 verifier exists and is tested | Need verifier output for the release-grade packet | External reconstruction check / non-normative | Run verifier on packet |
| Field-point authority map | Packet field points classified by role and authority status | `field_point_authority_map_v0` contract + builder exist | Need packet-specific map | Diagnostic authority-role surface | Build packet map |
| Evidence fold-in admissibility | Any non-normative candidate evidence has admissibility state | `evidence_fold_in_admissibility_v0` contract + builder exist | Need packet-specific admissibility artifact | Diagnostic admissibility surface | Build packet admissibility artifact |
| HPC evidence bundle | Required only if HPC / compute-scale evidence is used | `hpc_evidence_bundle_v0` contract + builder exist | Optional until compute-scale evidence enters packet | Diagnostic evidence surface | Include only when used |
| Recognition-surface drift | Optional diagnostic for public/publication interpretation risk | `recognition_surface_drift_v0` exists | Optional for packet hardening | Diagnostic / non-normative | Include if publication-surface risk is inspected |
| Reconstruction instructions | Human/operator can reconstruct the evidence-to-decision chain | Partial docs/tools exist | Need packet-local instructions | Audit / operator surface | Add packet README / handoff note |

## Blocking gaps

The following gaps block a true release-grade reference packet:

- no packet-bound non-stubbed `prod` status artifact;
- no packet-bound canonical external evidence set;
- no packet-bound materialized required + release_required gate set;
- no packet-bound CI outcome for declared-policy gate enforcement;
- no complete packet digest manifest;
- no packet-bound release authority manifest;
- no packet-bound audit bundle;
- no packet-bound operator handoff report;
- no packet-bound publication snapshot;
- no full RA1 verifier pass over the assembled packet.

## Non-blocking but important hardening gaps

The following are not immediate blockers but strengthen the reference packet:

- field-point authority map for the packet;
- evidence fold-in admissibility artifact for candidate evidence;
- recognition-surface drift diagnostic for publication/reader surfaces;
- HPC evidence bundle when compute-scale evidence is used;
- stronger provenance / attestation for external summaries;
- signer / envelope requirements for future external evidence.

## Authority boundary

This gap map is non-normative.

It does not authorize, block, override, or create release authority.

It does not modify:

- release policy;
- gate registry;
- `check_gates.py`;
- status schema semantics;
- workflow release-gating semantics;
- Quality Ledger authority status;
- release authority manifest authority status;
- audit bundle authority status;
- publication surface authority semantics;
- shadow-layer authority semantics.

## Relation to field-instrument development

The release-grade evidence packet is a field-state closure, not a static architecture endpoint.

The current diagnostic contracts and builders are verified field states.

They are not permanent endpoints.

Future packet states may add, remove, or refine field points, provided each new point declares:

- role;
- authority status;
- relation to the normative materialization path;
- fold-in admissibility if applicable;
- policy route if release-relevant.

## What is safe to say

It is accurate to say:

PULSE has the diagnostic and authority-role machinery needed to define, validate, and build supporting evidence surfaces for a future release-grade reference packet.

It is not accurate to say:

The current core / smoke / reader surface is itself a release-grade reference packet.

It is not accurate to say:

A release-grade packet exists merely because a workflow ran.

It is not accurate to say:

A Quality Ledger, DOI record, dashboard, manifest, audit bundle, or publication snapshot creates release authority by itself.

## Next concrete work

The next concrete PULSE-REF work should be:

1. define a minimal release-grade packet fixture layout;
2. bind the packet to a run identity and commit SHA;
3. include status, policy, registry, materialized gate-set, CI outcome, manifest, handoff, publication snapshot, and digests;
4. run the RA1 verifier over the packet;
5. record the result as a non-normative release-grade reference proof;
6. only later consider whether any diagnostic output should be promoted through declared policy.

## Summary

A release-grade PULSE reference is not merely a run.

It is an assembled, digest-backed, reconstructable evidence packet.

The packet must show that release authority could only materialize through:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block decision

Until that packet exists, core / diagnostic / publication surfaces must not be over-read as release-grade authority.
