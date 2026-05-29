# PULSEmech Manuscript Claim Artifact Verification v0

Status: manuscript-claim artifact verification  
Paper status: pre-draft support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-planning document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document performs a first artifact-verification pass for the selected manuscript-facing PULSEmech paper claims.

It follows:

- `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`
- `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`

The purpose is to bind selected manuscript claims to exact repository artifact paths before full prose expansion begins.

This document does not change PULSE release-authority semantics.

This document does not promote a claim into final manuscript prose by itself.

## Verification rule

A manuscript claim may move toward prose only when the following are present:

1. exact artifact paths;
2. artifact role;
3. authority / role status;
4. non-claim boundary;
5. verification result;
6. manuscript status.

Claims that still require content-level review must remain non-promotable.

## Verification status vocabulary

| Verification status | Meaning | Manuscript use |
|---|---|---|
| `path-verified` | Exact repository paths are identified and suitable for manuscript support, but final prose wording still needs review. | May be used for draft scaffolding only |
| `verified for manuscript` | Exact paths, role, boundary, and wording have been checked for manuscript prose. | Promotable |
| `accepted limitation` | Limitation claim is accepted for manuscript use. Repository artifact support may be optional when the claim is purely a non-claim. | Promotable as limitation |
| `accepted future-work` | Future-work claim is accepted and remains clearly marked as future work. | Promotable as future work |
| `needs review` | Artifact support or wording is not yet sufficient. | Not promotable |
| `defer` | Keep outside the first full draft. | Not promotable |

## Manuscript status vocabulary

| Manuscript status | Meaning |
|---|---|
| `draft-scaffold only` | May guide draft structure but should not be treated as final manuscript wording. |
| `ready for prose draft` | Claim can be used in the first full prose draft with cited artifact support. |
| `limitation-ready` | Claim can be used in the limitations section. |
| `future-work-ready` | Claim can be used in the future-work section. |
| `deferred` | Keep out of the first full draft. |

## Verification table

| Draft claim ID | Claim | Exact artifact paths | What was verified | Authority / role status | Verification result | Manuscript status | Boundary / non-claim |
|---|---|---|---|---|---|---|---|
| `D01_PROBLEM_GAP` | AI applications produce probabilistic behavior, while software release permission requires a deterministic decision at the release boundary. PULSE addresses this by measuring the pre-release evidence relation rather than explaining post-event outcomes. | `README.md`; `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Path-level support exists for probabilistic behavior → recorded evidence → artifact-bound release-authority state → deterministic software release permission, plus relational evidence-field framing. | paper-planning only | path-verified | draft-scaffold only | Does not claim PULSE explains all AI behavior or proves AI safety. |
| `D02_CORE_MECHANISM` | PULSEmech is an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision mechanism for AI release decisions. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact public identity and paper-planning paths exist for the PULSEmech mechanism statement. | normative path | path-verified | draft-scaffold only | Does not identify PULSE as a generic framework, dashboard, scorecard, or governance layer. |
| `D03_NORMATIVE_PATH` | The PULSEmech release decision materializes through recorded release evidence, `status.json`, declared policy, materialized required gates, strict fail-closed CI checking, and declared-policy CI allow/block output. | `README.md`; `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `schemas/status/status_v1.schema.json`; `pulse_gate_policy_v0.yml`; `tools/policy_to_require_args.py`; `PULSE_safe_pack_v0/tools/check_gates.py`; `.github/workflows/pulse_ci.yml` | Exact paths exist for the tuple, status artifact, declared policy, policy materialization, gate checking, and CI workflow. | normative path | path-verified | draft-scaffold only | Does not claim any single artifact alone authorizes release. |
| `D04_STATUS_ARTIFACT_ROLE` | `status.json` acts as the machine-readable release-state artifact for recorded release state. | `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `schemas/status/status_v1.schema.json`; `status.json`; `PULSE_safe_pack_v0/status.json` if present in current pack path | Exact status-contract and schema paths exist. Current status surfaces must be checked before final citation wording. | normative input | path-verified | draft-scaffold only | Does not claim `status.json` alone creates release authority. |
| `D05_DECLARED_POLICY_AND_GATE_MATERIALIZATION` | Declared policy defines required gate sets, gate registry stabilizes gate meaning, and policy-derived materialization turns declared sets into concrete required gates. | `pulse_gate_policy_v0.yml`; `pulse_gate_registry_v0.yml`; `tools/policy_to_require_args.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_policy_to_require_args_smoke.py`; `tests/test_policy_to_check_gates_e2e_smoke.py` | Exact paths exist for declared policy, gate registry, materializer, builder materialization, validator materialization checks, and policy smoke tests. | normative input / normative support | path-verified | draft-scaffold only | Does not allow hard-coded gate promotion outside declared policy. |
| `D06_FAIL_CLOSED_ENFORCEMENT` | Required gates are enforced by strict true-only fail-closed CI checking, and the declared-policy CI gate-enforcement outcome is the release decision. | `PULSE_safe_pack_v0/tools/check_gates.py`; `tests/test_check_gates_fail_closed.py`; `tests/test_policy_to_check_gates_e2e_smoke.py`; `.github/workflows/pulse_ci.yml`; `README.md` | Exact paths exist for checker, fail-closed tests, policy-to-check-gates path, CI workflow, and README decision path. | normative enforcement | path-verified | draft-scaffold only | Does not claim advisory gates block release by default. |
| `D07_AUTHORITY_BOUNDARY` | PULSE separates normative release-authority surfaces from trace, preservation, reader, diagnostic, and candidate-evidence surfaces. | `README.md`; `docs/OPTIONAL_LAYERS.md`; `docs/SPACE_RELATION_MAP_v0.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact paths exist for README authority boundary, optional/non-normative layers, topology/space relation map, and paper-planning boundary rules. | paper-planning only | path-verified | draft-scaffold only | Does not promote dashboards, ledgers, badges, manifests, packets, or diagnostic surfaces into authority by existence. |
| `D08_MANIFEST_AND_AUDIT_ROLE` | Release-authority manifests and audit bundles preserve and reconstruct the decision path but do not create a second decision engine. | `schemas/release_authority_v0.schema.json`; `PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py`; `tests/test_check_release_authority_manifest_v0.py`; `tests/test_build_release_authority_manifest_v0.py`; `tests/test_release_authority_manifest_non_interference.py`; `tools/verify_pulse_ref_ra1_package.py`; `tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py` | Exact paths exist for release-authority manifest schema/checker/tests and RA1 package verifier path. Audit-bundle prose should be tied carefully to current artifact state. | non-normative trace / non-normative preservation | path-verified | draft-scaffold only | Does not override the declared-policy CI allow/block decision. |
| `D09_PULSE_REF_PACKET_PATH` | PULSE-REF provides a guarded path from a controlled positive fixture to a reconstructable schema-aligned packet candidate. | `tests/fixtures/release_reference_v1/pass/status.json`; `tests/fixtures/release_reference_v1/pass/expected_outcome.json`; `ci/check_release_reference_complete_v1.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_check_pulse_ref_schema_aligned_packet_v0.py`; `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` | Exact paths exist for pass fixture, expected outcome, completeness guard, schema-aligned builder, builder tests, validator, validator tests, and checkpoint. | non-normative fixture / non-normative checker / non-normative packet-preparation | path-verified | draft-scaffold only | Does not claim the packet builder creates release authority or runs RA1. |
| `D10_PUBLICATION_REF_HARDENING` | Optional publication snapshot manifest references are checked for safe path, canonical path, packet-root containment, and sha256 match when present. | `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_check_pulse_ref_schema_aligned_packet_v0.py`; `schemas/pulse_ref_publication_snapshot_v0.schema.json` | Exact validator, test, and optional publication snapshot schema paths exist. | non-normative publication | path-verified | draft-scaffold only | Does not make live publication surfaces normative release authority. |
| `D11_CURRENT_V0_PACKET_BOUNDARY` | The current v0 generated packet is reconstructable, while field-point authority-map and evidence-fold-in admissibility artifacts remain reserved for a later packet-completeness layer. | `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py` | Exact checkpoint, builder, and builder-test paths exist for current v0 output boundary. | paper-planning only | path-verified | draft-scaffold only | Does not abandon future packet-completeness surfaces. |
| `D12_DRIFT_REGRESSION` | The generated schema-aligned packet output is protected by normalized golden-summary regression against silent mechanical drift. | `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json`; `ci/tools-tests.list` | Exact regression test, golden summary fixture, and tools-tests list paths exist. | non-normative regression | path-verified | draft-scaffold only | Does not use raw full-tree byte comparison and does not introduce release authority. |
| `D13_RELATIONAL_EVIDENCE_FIELD` | PULSE preserves the evidence relation behind the terminal release decision. | `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact paths exist for relational evidence-field principle and checkpoint relation. | non-normative field principle | path-verified | draft-scaffold only | Must remain explanatory and non-normative; does not replace the PULSEmech normative path. |
| `D14_NOT_MODEL_SAFETY_PROOF` | PULSE does not prove that an AI system is safe. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact paper-planning paths exist for this limitation. | boundary-claim | accepted limitation | limitation-ready | Prevents overclaiming. |
| `D15_NOT_RUNTIME_GUARDRAIL` | PULSE is not a runtime guardrail; it operates at the release boundary before deployment. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact README and paper-planning paths exist for release-boundary framing. | boundary-claim | accepted limitation | limitation-ready | Does not describe runtime interaction control. |
| `D16_NOT_HUMAN_REVIEW_REPLACEMENT` | PULSE does not replace human review. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`; operator handoff docs/tests if cited in final paper | Paper-planning paths exist; operator handoff support should be checked before final wording. | boundary-claim | accepted limitation | limitation-ready | PULSE records and enforces release evidence; it does not replace human judgment. |
| `D17_NOT_FRAMEWORK_IDENTITY` | The manuscript should not identify PULSE as a generic framework. | `README.md`; `tests/test_readme_release_authority_category_signal_v0.py`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Exact README, category-signal guard, and paper-planning paths exist. | paper-planning only | path-verified | draft-scaffold only | Prevents category flattening. |
| `D18_AI_DRAFTING_DISCLOSURE` | AI-assisted drafting and technical editing should be disclosed according to submission standards. | `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`; `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`; `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Paper-planning paths exist for disclosure placeholder. Final wording must be checked against submission standards before arXiv submission. | paper-planning only | needs review | draft-scaffold only | AI tools are not authors; human author remains responsible. |
| `D19_REPRODUCIBILITY_SPINE` | The paper should present reproducibility through artifacts, validators, tests, CI checks, and regression rather than unsupported narrative. | `README.md`; `ci/tools-tests.list`; `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` | Exact paths exist for reproducibility spine, generated packet regression, validator, builder, and checkpoint. | paper-planning only | path-verified | draft-scaffold only | Does not imply independent external replication has already occurred. |
| `D20_FUTURE_RA1_HPC` | RA1 and HPC candidate-state scaling may extend the work later. | `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md`; RA1 docs/tests if cited; HPC docs/tests if cited | Future-work support exists at planning level, but exact current/future wording must remain conservative. | future-work | accepted future-work | future-work-ready | Must not be written as current paper result unless artifact-backed. |

## Claims ready for limitation prose

The following limitation claims may be used in the first full draft limitations section:

| Draft claim ID | Manuscript status | Required wording constraint |
|---|---|---|
| `D14_NOT_MODEL_SAFETY_PROOF` | limitation-ready | Must state that PULSE does not prove model safety. |
| `D15_NOT_RUNTIME_GUARDRAIL` | limitation-ready | Must state that PULSE acts at release boundary, not runtime interaction boundary. |
| `D16_NOT_HUMAN_REVIEW_REPLACEMENT` | limitation-ready | Must state that PULSE does not replace human review or judgment. |

## Claims ready for future-work prose

The following future-work claim may be used in a future-work section:

| Draft claim ID | Manuscript status | Required wording constraint |
|---|---|---|
| `D20_FUTURE_RA1_HPC` | future-work-ready | Must keep RA1 / HPC as future extension unless exact current artifact state is cited as current result. |

## Claims still requiring manuscript wording verification

The following claims have path-level artifact verification but should not yet be treated as final prose:

| Draft claim ID | Reason |
|---|---|
| `D01_PROBLEM_GAP` | Needs careful wording to avoid overgeneralizing AI behavior. |
| `D02_CORE_MECHANISM` | Needs exact tuple wording synchronized with README and paper skeleton. |
| `D03_NORMATIVE_PATH` | Needs exact element-by-element verification before final prose. |
| `D04_STATUS_ARTIFACT_ROLE` | Needs careful wording so `status.json` is not overpromoted. |
| `D05_DECLARED_POLICY_AND_GATE_MATERIALIZATION` | Needs content-level verification of policy materializer and generated gate-set relation. |
| `D06_FAIL_CLOSED_ENFORCEMENT` | Needs exact wording around true-only and advisory/non-blocking semantics. |
| `D07_AUTHORITY_BOUNDARY` | Needs table-level manuscript wording so non-normative surfaces stay non-normative. |
| `D08_MANIFEST_AND_AUDIT_ROLE` | Needs careful separation between trace and decision authority. |
| `D09_PULSE_REF_PACKET_PATH` | Needs concise wording that builder prepares packets but does not authorize release. |
| `D10_PUBLICATION_REF_HARDENING` | Needs wording that publication surfaces remain non-normative. |
| `D11_CURRENT_V0_PACKET_BOUNDARY` | Needs wording that future surfaces are reserved, not missing failures. |
| `D12_DRIFT_REGRESSION` | Needs wording that regression detects generated-packet drift without raw full-tree comparison. |
| `D13_RELATIONAL_EVIDENCE_FIELD` | Needs non-normative framing only. |
| `D17_NOT_FRAMEWORK_IDENTITY` | Needs wording discipline throughout manuscript. |
| `D18_AI_DRAFTING_DISCLOSURE` | Needs final submission-standard wording. |
| `D19_REPRODUCIBILITY_SPINE` | Needs careful distinction between repository reproducibility and independent external replication. |

## Manuscript expansion gate

The first prose draft may begin only from claims with one of these verification results:

- `path-verified`
- `accepted limitation`
- `accepted future-work`

However, `path-verified` claims remain draft-scaffold only until final prose wording is checked.

A claim may become final manuscript wording only when it is updated to:

- `verified for manuscript`
- `accepted limitation`
- `accepted future-work`

## Artifact verification notes

### Normative path claims

Claims `D02` through `D06` must remain tightly synchronized with repository release-authority mechanics.

They should use exact wording from the README and status / policy / gate-checking artifacts where possible.

### Authority-boundary claims

Claims `D07` through `D13` must preserve non-normative role separation.

They should not imply that manifests, audit bundles, packet builders, validators, publication surfaces, or regressions create release authority.

### Limitation claims

Claims `D14` through `D16` are safe for manuscript use as limitations.

They should be short and explicit.

### Identity-protection claims

Claim `D17` is a manuscript-wide guard.

It should not appear as a defensive paragraph unless needed.

It should instead guide terminology throughout the paper.

### Disclosure claim

Claim `D18` must be checked again immediately before arXiv submission.

### Future-work claim

Claim `D20` can appear in future work only with conservative language.

## Minimum next prose draft input

The first prose draft can start from:

- `D01_PROBLEM_GAP`
- `D02_CORE_MECHANISM`
- `D03_NORMATIVE_PATH`
- `D07_AUTHORITY_BOUNDARY`
- `D09_PULSE_REF_PACKET_PATH`
- `D12_DRIFT_REGRESSION`
- `D14_NOT_MODEL_SAFETY_PROOF`
- `D15_NOT_RUNTIME_GUARDRAIL`
- `D16_NOT_HUMAN_REVIEW_REPLACEMENT`
- `D20_FUTURE_RA1_HPC`

These claims form the smallest safe paper core.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n "Verification table" docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
grep -n "D02_CORE_MECHANISM" docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
grep -n "D12_DRIFT_REGRESSION" docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
grep -n "Claims ready for limitation prose" docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
grep -n "Manuscript expansion gate" docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md
```

Expected result:

- verification table is present;
- core mechanism claim is present;
- drift regression claim is present;
- limitation-ready claims are listed;
- manuscript expansion gate is present.

## Next paper step

After this document is merged, the next paper step is:

`docs(paper): add PULSEmech minimal first-draft outline`

That outline should use only the smallest safe paper core and should not expand into full prose yet.
