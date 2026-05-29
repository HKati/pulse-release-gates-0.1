# PULSEmech Artifact Citation Pass v0

Status: artifact citation pass  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document attaches manuscript-facing artifact anchors to the first PULSEmech prose draft.

It follows:

- `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`
- `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`
- `docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md`
- `docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md`
- `docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md`
- `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md`

The purpose is to prepare a citation-ready artifact spine before any submission-stage paper draft.

This document does not add new paper claims.

This document does not finalize academic citations.

This document does not change PULSE release-authority semantics.

## Working rule

Do not cite a claim because it sounds plausible.

Cite the artifact relation that supports it.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Paper citation rule:

Do not cite the outcome as the mechanism.

Cite the recorded artifact, declared policy, materialized gate relation, checker, validator, regression, or boundary document that supports the claim.

## Citation pass boundary

This document provides repository artifact anchors for manuscript prose.

It is not a bibliography.

It is not a literature-review spine.

It is not an arXiv submission package.

It is not a DOI / release snapshot lock.

A later submission-stage pass must decide:

- final citation format;
- commit or release tag to cite;
- DOI / Zenodo references;
- bibliography entries;
- line-level or section-level references;
- final external related-work citations.

## Citation kind vocabulary

| Citation kind | Meaning |
|---|---|
| `static repo document` | A checked-in repository document that can support explanatory or boundary prose. |
| `static repo schema` | A checked-in schema file that supports artifact shape or contract claims. |
| `static repo script` | A checked-in script or tool that supports implementation claims. |
| `static repo test` | A checked-in test or smoke test that supports validation or regression claims. |
| `workflow path` | A checked-in CI workflow file that supports workflow or generated-run claims. |
| `generated-run artifact path` | A path produced during a CI or local run. It must not be cited as a static checked-in repository file. |
| `paper-planning support` | A paper-planning document that supports manuscript boundary, wording, or claim structure. |
| `limitation support` | A document or planning surface that supports a limitation / non-claim. |
| `future-work support` | A document or planning surface that supports conservative future-work framing. |

## Citation readiness vocabulary

| Status | Meaning |
|---|---|
| `ready for draft citation` | The artifact path is suitable for first prose draft citation scaffolding. |
| `generated-run wording required` | The artifact path is generated during a run and must be described as generated, not static. |
| `boundary-only` | The artifact supports limitation / non-claim wording. |
| `needs submission-stage lock` | The artifact path is useful now but must be tied to a commit, release, DOI, or line reference before submission. |
| `do not cite as authority` | The artifact may be mentioned as trace, reader, diagnostic, packet-preparation, or preservation surface, but not as release authority. |

## Global citation safeguards

The paper must not cite:

- `status.json` as a static root repository artifact;
- generated run artifacts as checked-in repository files;
- release authority manifests as decision engines;
- audit bundles as release-authorizing artifacts;
- dashboards, badges, ledgers, Pages, or publication surfaces as release authority;
- packet builders as release-decision engines;
- validators as release-decision engines;
- regression fixtures as release permission.

The paper may cite these surfaces only with their correct role.

## Section citation map

| Paper section | Main manuscript claim | Artifact anchors | Citation kind | Readiness | Boundary |
|---|---|---|---|---|---|
| Abstract | PULSEmech is an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision mechanism. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | static repo document / paper-planning support | ready for draft citation | Do not identify PULSE as a generic framework. |
| Abstract | PULSEmech binds evidence, `status.json`, policy, materialized gates, and fail-closed CI before CI allow/block decision materializes. | `README.md`; `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `pulse_gate_policy_v0.yml`; `tools/policy_to_require_args.py`; `PULSE_safe_pack_v0/tools/check_gates.py`; `.github/workflows/pulse_ci.yml` | static repo document / static repo script / workflow path | ready for draft citation | Do not imply any single artifact authorizes release. |
| Abstract | PULSE-REF includes guarded fixture, schema-aligned packet construction, packet validation, publication-reference hardening, and normalized generated-packet regression. | `tests/fixtures/release_reference_v1/pass/status.json`; `tests/fixtures/release_reference_v1/pass/expected_outcome.json`; `ci/check_release_reference_complete_v1.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json` | static repo fixture / static repo script / static repo test | ready for draft citation | These support reconstruction and regression, not release authority by themselves. |
| Introduction | AI release decisions require deterministic release-boundary permission while AI evidence can be probabilistic or evolving. | `README.md`; `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | static repo document / paper-planning support | ready for draft citation | Do not overgeneralize to all AI behavior. |
| Introduction | PULSEmech measures the pre-release relation rather than explaining outcomes after the event. | `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | static repo document / paper-planning support | ready for draft citation | Keep this as mechanism framing, not philosophical proof. |
| Release-authority model | The deterministic decision tuple defines PULSEmech. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | static repo document / paper-planning support | ready for draft citation | Must keep exact tuple wording synchronized. |
| Release-authority model | The normative release-authority path is evidence → status artifact → policy → materialized gates → fail-closed CI → CI allow/block decision. | `README.md`; `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `pulse_gate_policy_v0.yml`; `tools/policy_to_require_args.py`; `PULSE_safe_pack_v0/tools/check_gates.py`; `.github/workflows/pulse_ci.yml` | static repo document / static repo script / workflow path | ready for draft citation | Do not cite a trace or reader surface as part of the normative path unless explicitly classified. |
| Normative artifact path | `status.json` is the machine-readable release-state artifact. | `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `schemas/status/status_v1.schema.json`; generated run artifact path: `PULSE_safe_pack_v0/artifacts/status.json`; `.github/workflows/pulse_ci.yml` | static repo document / static repo schema / generated-run artifact path / workflow path | generated-run wording required | The generated status path must not be cited as a checked-in root `status.json`. |
| Normative artifact path | Declared policy defines required gate sets. | `pulse_gate_policy_v0.yml`; `tests/test_policy_to_require_args_smoke.py`; `tests/test_policy_to_check_gates_e2e_smoke.py` | static repo policy / static repo test | ready for draft citation | Policy text alone does not authorize release. |
| Normative artifact path | Gate registry stabilizes gate meaning. | `pulse_gate_registry_v0.yml` | static repo document | ready for draft citation | Registry supports interpretation; it does not replace policy or CI enforcement. |
| Normative artifact path | Materialized required gates are derived from declared policy. | `tools/policy_to_require_args.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; generated packet artifact path: `gates/materialized_gate_sets.json` | static repo script / generated-run artifact path | generated-run wording required | Do not imply hard-coded gate promotion. |
| Normative artifact path | Required gates are checked strict true-only fail-closed. | `PULSE_safe_pack_v0/tools/check_gates.py`; `tests/test_check_gates_fail_closed.py`; `tests/test_policy_to_check_gates_e2e_smoke.py` | static repo script / static repo test | ready for draft citation | Advisory gates do not block by default. |
| Normative artifact path | The declared-policy CI gate-enforcement outcome is the release decision. | `.github/workflows/pulse_ci.yml`; `PULSE_safe_pack_v0/tools/check_gates.py`; `README.md` | workflow path / static repo script / static repo document | ready for draft citation | Not every CI job is a release-authority job. |
| Authority boundary | PULSE separates normative, trace, preservation, reader, diagnostic, and packet-preparation surfaces. | `README.md`; `docs/OPTIONAL_LAYERS.md`; `docs/SPACE_RELATION_MAP_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | static repo document / paper-planning support | ready for draft citation | Do not promote non-normative surfaces into authority. |
| Authority boundary | Release authority manifest records the evidence-policy-evaluator chain but is not a second decision engine. | `docs/release_authority_manifest_v0.md`; `schemas/release_authority_v0.schema.json`; `PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py`; `tests/test_check_release_authority_manifest_v0.py`; `tests/test_build_release_authority_manifest_v0.py`; `tests/test_release_authority_manifest_non_interference.py` | static repo document / static repo schema / static repo script / static repo test | ready for draft citation | Manifest is trace, not release authority. |
| Authority boundary | Audit bundles preserve reconstructable evidence but do not authorize release. | `docs/release_authority_manifest_v0.md`; `.github/workflows/pulse_ci.yml`; generated audit bundle path: `PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/`; generated bundle contents: `report_card.html`, `release_authority_v0.json`, `status.json`; CI artifact name: `release-authority-audit-bundle` | static repo document / workflow path / generated-run artifact path | generated-run wording required | Audit bundle is non-normative / non-blocking. |
| Authority boundary | Diagnostic and reader surfaces remain non-normative unless explicitly folded into required gates under declared policy. | `README.md`; `docs/OPTIONAL_LAYERS.md`; `docs/SPACE_RELATION_MAP_v0.md` | static repo document | ready for draft citation | Do not cite dashboard, ledger, badges, Pages, or diagnostic overlays as release authority by existence. |
| PULSE-REF reference path | The positive pass fixture is a controlled release-reference candidate. | `tests/fixtures/release_reference_v1/pass/status.json`; `tests/fixtures/release_reference_v1/pass/expected_outcome.json`; `tests/test_pulse_ref_pass_fixture_packet_baseline_candidate_v0.py` | static repo fixture / static repo test | ready for draft citation | Fixture does not authorize release. |
| PULSE-REF reference path | Release-reference completeness guard runs before packet generation. | `ci/check_release_reference_complete_v1.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py` | static repo script / static repo test | ready for draft citation | Guard does not replace PULSEmech release authority. |
| PULSE-REF reference path | Schema-aligned builder prepares reconstructable v0 packet candidate. | `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` | static repo script / static repo test / static repo document | ready for draft citation | Builder does not create release authority and does not run RA1. |
| PULSE-REF reference path | Packet validator checks artifact shape and reconstruction readiness. | `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_check_pulse_ref_schema_aligned_packet_v0.py` | static repo script / static repo test | ready for draft citation | Validator does not authorize release or prove model safety. |
| PULSE-REF reference path | Optional publication snapshot references are hardened when present. | `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_check_pulse_ref_schema_aligned_packet_v0.py`; `schemas/pulse_ref_publication_snapshot_v0.schema.json` | static repo script / static repo test / static repo schema | ready for draft citation | Publication surfaces remain non-normative. |
| PULSE-REF reference path | Current v0 packet boundary reserves field/admissibility surfaces for later packet-completeness layer. | `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py` | static repo document / static repo script / static repo test | ready for draft citation | Reserved future surfaces are not missing failures in current v0 builder. |
| Validation and regression | Generated packet output is guarded by normalized golden-summary regression. | `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json`; `ci/tools-tests.list` | static repo test / static repo fixture | ready for draft citation | Regression does not create release authority. |
| Validation and regression | Normalized regression avoids raw full-tree byte comparison because handoff reports can contain environment-specific paths. | `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json` | static repo test / static repo fixture | ready for draft citation | Do not present this as independent external replication. |
| Limitations | PULSE does not prove that an AI system is safe. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | paper-planning support / limitation support | boundary-only | Limitation only. |
| Limitations | PULSE is not a runtime guardrail. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | static repo document / limitation support | boundary-only | PULSE operates at release boundary, not runtime interaction boundary. |
| Limitations | PULSE does not replace human review. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | paper-planning support / limitation support | boundary-only | Do not turn this into a claim about human review systems generally. |
| Future work | RA1-style package verification and HPC candidate-state scaling may extend the work later. | `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md`; RA1 docs/tests if cited; HPC docs/tests if cited | static repo document / future-work support | needs submission-stage lock | Must remain future work unless exact current artifacts are cited as current result. |
| Disclosure | AI-assisted drafting and technical editing should be disclosed before submission. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | paper-planning support | needs submission-stage lock | Final disclosure wording must be checked against current submission standards. |

## Generated-run artifact wording rules

Use:

- generated run artifact path: `PULSE_safe_pack_v0/artifacts/status.json`
- generated audit bundle path: `PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/`
- generated packet artifact path: `gates/materialized_gate_sets.json` inside generated packet
- CI artifact name: `release-authority-audit-bundle`

Do not write:

- static root `status.json`;
- static `PULSE_safe_pack_v0/status.json`;
- checked-in audit bundle;
- checked-in generated packet output unless the specific fixture is actually committed.

## Static artifact citation candidates

The following static repository paths are candidate citation anchors for the first prose draft:

```text
README.md
docs/STATUS_CONTRACT.md
docs/status_json.md
schemas/status/status_v1.schema.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
tools/policy_to_require_args.py
PULSE_safe_pack_v0/tools/check_gates.py
.github/workflows/pulse_ci.yml
docs/release_authority_manifest_v0.md
schemas/release_authority_v0.schema.json
PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py
tests/test_check_release_authority_manifest_v0.py
tests/test_build_release_authority_manifest_v0.py
tests/test_release_authority_manifest_non_interference.py
tests/fixtures/release_reference_v1/pass/status.json
tests/fixtures/release_reference_v1/pass/expected_outcome.json
ci/check_release_reference_complete_v1.py
scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py
tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py
scripts/check_pulse_ref_schema_aligned_packet_v0.py
tests/test_check_pulse_ref_schema_aligned_packet_v0.py
schemas/pulse_ref_publication_snapshot_v0.schema.json
docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md
tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py
tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json
ci/tools-tests.list
docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md
docs/OPTIONAL_LAYERS.md
docs/SPACE_RELATION_MAP_v0.md
```

Before submission-stage use, each static path should be checked against the final repository state and preferably tied to a commit, release, or DOI.

## Paper-planning citation candidates

The following paper-planning documents support draft structure and claim boundaries:

```text
docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md
docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md
docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md
docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md
docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
```

These are paper-planning supports.

They should not be used as the only evidence for implementation claims when implementation artifacts exist.

## Citation pass findings

### Ready for draft citation

The following areas have enough artifact anchors for draft citation scaffolding:

- PULSEmech tuple and normative path;
- status artifact role, with generated-run wording;
- declared policy;
- gate registry;
- policy-derived materialization;
- fail-closed gate checking;
- CI workflow enforcement path;
- release authority manifest as trace;
- audit bundle as generated non-normative preservation surface;
- PULSE-REF pass fixture;
- release-reference completeness guard;
- schema-aligned builder;
- schema-aligned packet validator;
- publication snapshot ref hardening;
- normalized generated-packet regression;
- limitations around model-safety proof and runtime guardrail.

### Needs submission-stage lock

The following areas require final lock before submission-stage manuscript:

- exact commit / release / DOI references;
- final arXiv disclosure wording;
- future-work wording for RA1 / HPC;
- line-level references if the paper uses line-specific artifact citation;
- related-work citations outside the repository.

## Manuscript update guidance

When updating `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md`, insert artifact references only after confirming:

1. the artifact path exists;
2. the artifact role matches the claim;
3. generated artifacts are described as generated;
4. non-normative surfaces are not promoted into authority;
5. limitations remain short and explicit;
6. future work remains future work.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Section citation map$' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
grep -n 'PULSE_safe_pack_v0/artifacts/status.json' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
grep -n 'release_authority_audit_bundle' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
grep -n '^## Generated-run artifact wording rules$' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
grep -n '^## Static artifact citation candidates$' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
grep -n '^## Citation pass findings$' docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md
```

Expected result:

- section citation map is present;
- generated status artifact wording is present;
- generated audit bundle wording is present;
- generated-run wording rules are present;
- static artifact candidates are present;
- citation pass findings are present.

## Next paper step

After this artifact citation pass is merged, the next paper step is:

`docs(paper): add PULSEmech citation-bound prose draft v0`

That step should update the first prose draft with artifact-anchor notes while preserving the same claim boundary.
