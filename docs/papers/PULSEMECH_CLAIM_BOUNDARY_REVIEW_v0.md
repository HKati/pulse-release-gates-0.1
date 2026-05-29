# PULSEmech Paper Claim-Boundary Review v0

Status: claim-boundary review  
Paper status: pre-draft support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-planning document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document converts the broader PULSEmech artifact-to-claim map into a shorter manuscript-facing claim-boundary review.

The purpose is to decide which claims are candidates for the first full paper draft and what must be verified before each claim can enter manuscript prose.

This document does not promote any claim into final manuscript status by itself.

A claim remains non-promotable until its verification status is resolved according to the artifact-to-claim map.

## Source document

This review depends on:

`docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`

The artifact-to-claim map remains the controlling paper-planning surface for:

- verification-status vocabulary;
- authority / role status vocabulary;
- claim acceptance rule;
- claim rejection rule;
- artifact evidence classification;
- limitation and future-work exceptions.

## Working rule

Do not expand prose before claim boundaries are clean.

Do not decorate claims.

Bind claims to artifacts, authority role, non-claim boundary, and verification route.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Paper rule:

Do not explain a release outcome after the fact.

Define and verify the pre-release relation between recorded evidence, declared policy, materialized gates, and fail-closed CI enforcement.

## Review status vocabulary

| Review status | Meaning |
|---|---|
| `selected for verification` | Candidate claim selected for the first full draft, but not yet verified for manuscript prose. |
| `limitation candidate` | Boundary / limitation claim selected for later accepted-limitation review. |
| `future-work candidate` | Future-work claim selected for later accepted-future-work review. |
| `defer` | Claim remains in the broader map but should not enter the first full draft. |
| `reject from draft` | Claim should not enter the paper in its current form. |

## Promotion rule

This review does not override the artifact-to-claim map.

A selected claim may enter manuscript prose only after it satisfies the artifact-to-claim map acceptance rule, including resolved verification status.

Claims with verification status:

`to verify before manuscript`

must not be promoted into manuscript prose.

## First-draft claim set

The first full paper draft should use a narrow claim set.

The target paper is not a complete description of the whole PULSE workshop.

The target paper is a cs.SE technical paper about PULSEmech as an artifact-bound release-authority mechanism.

## Manuscript-facing claim table

| Draft claim ID | Source claim IDs | Manuscript-facing claim | Authority / role status | Review status | Verification route | Boundary / non-claim |
|---|---|---|---|---|---|---|
| `D01_PROBLEM_GAP` | `C03_PRE_RELEASE_MEASUREMENT`; `C22_RESULT_NOT_MECHANISM`; `C27_CS_SE_CATEGORY_FIT` | AI applications produce probabilistic behavior, while software release permission requires a deterministic decision at the release boundary. PULSE addresses this by measuring the pre-release evidence relation rather than explaining post-event outcomes. | paper-planning only | selected for verification | Verify against README front-door positioning, PULSEmech paper skeleton, and relational evidence-field principle. | Does not claim PULSE explains all AI behavior or proves safety. |
| `D02_CORE_MECHANISM` | `C01_RELEASE_AUTHORITY_IDENTITY`; `C02_PULSEMECH_DECISION_TUPLE` | PULSEmech is an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision mechanism for AI release decisions. | normative path | selected for verification | Verify exact tuple wording against README and paper skeleton. | Does not identify PULSE as a generic framework or dashboard. |
| `D03_NORMATIVE_PATH` | `C02_PULSEMECH_DECISION_TUPLE`; `C04_STATUS_ARTIFACT`; `C05_DECLARED_POLICY`; `C07_MATERIALIZED_REQUIRED_GATES`; `C08_TRUE_ONLY_FAIL_CLOSED_CHECKING`; `C09_CI_ALLOW_BLOCK_DECISION` | The PULSEmech release decision materializes through recorded release evidence, `status.json`, declared policy, materialized required gates, strict fail-closed CI checking, and declared-policy CI allow/block output. | normative path | selected for verification | Verify each element against README, status contract, policy, materialization tooling, check_gates behavior, and CI workflow. | Does not claim a single artifact alone authorizes release. |
| `D04_STATUS_ARTIFACT_ROLE` | `C04_STATUS_ARTIFACT` | `status.json` acts as the machine-readable release-state artifact for recorded release state. | normative input | selected for verification | Verify against `docs/STATUS_CONTRACT.md`, `docs/status_json.md`, status schema, and current status surfaces. | Does not claim `status.json` alone creates release authority. |
| `D05_DECLARED_POLICY_AND_GATE_MATERIALIZATION` | `C05_DECLARED_POLICY`; `C06_GATE_REGISTRY`; `C07_MATERIALIZED_REQUIRED_GATES` | Declared policy defines required gate sets, gate registry stabilizes gate meaning, and policy-derived materialization turns declared sets into concrete required gates. | normative input / normative support | selected for verification | Verify against `pulse_gate_policy_v0.yml`, `pulse_gate_registry_v0.yml`, policy materializer, generated materialized gate sets, and packet validator. | Does not allow hard-coded gate promotion outside declared policy. |
| `D06_FAIL_CLOSED_ENFORCEMENT` | `C08_TRUE_ONLY_FAIL_CLOSED_CHECKING`; `C09_CI_ALLOW_BLOCK_DECISION` | Required gates are enforced by strict true-only fail-closed CI checking, and the declared-policy CI gate-enforcement outcome is the release decision. | normative enforcement | selected for verification | Verify against `check_gates.py`, fail-closed tests, policy-to-check-gates tests, and CI workflow. | Does not claim advisory gates block release by default. |
| `D07_AUTHORITY_BOUNDARY` | `C10_AUTHORITY_BOUNDARY`; `C11_MANIFEST_TRACE_NOT_ENGINE`; `C12_AUDIT_BUNDLE_PRESERVATION`; `C13_EXTERNAL_EVIDENCE_SEMANTICS` | PULSE separates normative release-authority surfaces from trace, preservation, reader, diagnostic, and candidate-evidence surfaces. | paper-planning only | selected for verification | Verify against README authority boundary, optional layers, manifest docs/checker, audit bundle docs/tests, and external detector docs. | Does not promote manifests, audit bundles, dashboards, ledgers, or external summaries into authority by existence. |
| `D08_MANIFEST_AND_AUDIT_ROLE` | `C11_MANIFEST_TRACE_NOT_ENGINE`; `C12_AUDIT_BUNDLE_PRESERVATION` | Release-authority manifests and audit bundles preserve and reconstruct the decision path but do not create a second decision engine. | non-normative trace / non-normative preservation | selected for verification | Verify against manifest schema/checker, RA1-related package docs/tests, and audit bundle artifacts. | Does not override the declared-policy CI allow/block decision. |
| `D09_PULSE_REF_PACKET_PATH` | `C14_RELEASE_REFERENCE_PASS_FIXTURE`; `C15_RELEASE_REFERENCE_COMPLETENESS_GUARD`; `C16_SCHEMA_ALIGNED_PACKET_BUILDER`; `C17_SCHEMA_ALIGNED_PACKET_VALIDATOR` | PULSE-REF provides a guarded path from a controlled positive fixture to a reconstructable schema-aligned packet candidate. | non-normative fixture / non-normative checker / non-normative packet-preparation | selected for verification | Verify against pass fixture files, release-reference completeness guard, schema-aligned builder, builder tests, packet validator, and validator tests. | Does not claim the packet builder creates release authority or runs RA1. |
| `D10_PUBLICATION_REF_HARDENING` | `C18_PUBLICATION_REF_HARDENING` | Optional publication snapshot manifest references are checked for safe path, canonical path, packet-root containment, and sha256 match when present. | non-normative publication | selected for verification | Verify against packet validator and publication snapshot regression tests. | Does not make live publication surfaces normative release authority. |
| `D11_CURRENT_V0_PACKET_BOUNDARY` | `C19_CURRENT_V0_PACKET_COMPLETENESS_BOUNDARY` | The current v0 generated packet is reconstructable, while field-point authority-map and evidence-fold-in admissibility artifacts remain reserved for a later packet-completeness layer. | paper-planning only | selected for verification | Verify against checkpoint doc and current builder output contract. | Does not abandon future packet-completeness surfaces. |
| `D12_DRIFT_REGRESSION` | `C20_GENERATED_PACKET_DRIFT_REGRESSION` | The generated schema-aligned packet output is protected by normalized golden-summary regression against silent mechanical drift. | non-normative regression | selected for verification | Verify against generated packet regression test, golden summary fixture, and tools-tests list. | Does not use raw full-tree byte comparison and does not introduce release authority. |
| `D13_RELATIONAL_EVIDENCE_FIELD` | `C21_RELATIONAL_EVIDENCE_FIELD` | PULSE preserves the evidence relation behind the terminal release decision. | non-normative field principle | selected for verification | Verify against relational evidence-field principle and packet checkpoint. | Must remain explanatory and non-normative; does not replace PULSEmech path. |
| `D14_NOT_MODEL_SAFETY_PROOF` | `C23_NOT_MODEL_SAFETY_PROOF` | PULSE does not prove that an AI system is safe. | boundary-claim | limitation candidate | Review as accepted limitation before manuscript use. | Prevents overclaiming. |
| `D15_NOT_RUNTIME_GUARDRAIL` | `C24_NOT_RUNTIME_GUARDRAIL` | PULSE is not a runtime guardrail; it operates at the release boundary before deployment. | boundary-claim | limitation candidate | Review as accepted limitation before manuscript use. | Does not describe runtime interaction control. |
| `D16_NOT_HUMAN_REVIEW_REPLACEMENT` | `C25_NOT_HUMAN_REVIEW_REPLACEMENT` | PULSE does not replace human review. | boundary-claim | limitation candidate | Review as accepted limitation before manuscript use. | PULSE records and enforces release evidence; it does not replace human judgment. |
| `D17_NOT_FRAMEWORK_IDENTITY` | `C26_NOT_FRAMEWORK_IDENTITY` | The manuscript should not identify PULSE as a generic framework. | paper-planning only | selected for verification | Verify against README front-door guard and terminology boundary. | Prevents category flattening. |
| `D18_AI_DRAFTING_DISCLOSURE` | `C28_AI_ASSISTED_DRAFTING_DISCLOSURE` | AI-assisted drafting and technical editing should be disclosed according to submission standards. | paper-planning only | selected for verification | Verify disclosure wording before submission. | AI tools are not authors; human author remains responsible. |
| `D19_REPRODUCIBILITY_SPINE` | `C29_REPRODUCIBILITY_SPINE` | The paper should present reproducibility through artifacts, validators, tests, CI checks, and regression rather than unsupported narrative. | paper-planning only | selected for verification | Verify artifact list after claim verification. | Does not imply external replication has already occurred. |
| `D20_FUTURE_RA1_HPC` | `C30_FUTURE_RA1_HPC_EXTENSION` | RA1 and HPC candidate-state scaling may extend the work later. | future-work | future-work candidate | Review as accepted future work before manuscript use. | Must not be written as current capability. |

## Claims deferred from first full draft

The following claim directions should remain in the broader artifact-to-claim map but should not lead the first draft:

| Source claim | Reason for deferral |
|---|---|
| Broad governance framing | Too easy to flatten PULSE into a generic governance framework. |
| Full RA1 verification claims | RA1 should appear only as future or related packet-verification direction unless the exact artifact state is verified for current manuscript use. |
| HPC validation claims | HPC belongs in future work unless current artifact-backed validation is explicitly verified. |
| General AI safety claims | PULSE is release-authority mechanics, not an AI safety proof. |
| Runtime control claims | PULSE operates at release boundary, not as runtime guardrail. |

## Section placement plan

| Draft section | Claim IDs |
|---|---|
| Abstract | `D01`, `D02`, `D03`, `D07`, `D09`, `D12`, `D14` |
| Introduction | `D01`, `D02`, `D17` |
| Release-authority model | `D02`, `D03`, `D04`, `D05`, `D06` |
| Authority boundary | `D07`, `D08`, `D13` |
| PULSE-REF reference path | `D09`, `D10`, `D11`, `D12` |
| Validation / regression strategy | `D06`, `D09`, `D10`, `D12`, `D19` |
| Limitations | `D14`, `D15`, `D16`, `D20` |
| Disclosure | `D18` |
| Conclusion | `D02`, `D03`, `D07`, `D19` |

## First-draft abstract claim boundary

The abstract may say:

- AI applications produce probabilistic behavior while release permission requires deterministic release-boundary decisions.
- PULSEmech is an artifact-bound release-authority mechanism.
- PULSEmech binds recorded release evidence, `status.json`, declared policy, materialized required gates, and strict fail-closed CI enforcement.
- PULSE separates normative release-authority surfaces from trace, audit, reader, diagnostic, and packet-preparation surfaces.
- PULSE-REF demonstrates a reconstructable reference path through guarded fixtures, schema-aligned packet construction, validation, and normalized generated-packet regression.
- The contribution is not a model-safety proof or runtime guardrail.

The abstract must not say:

- PULSE proves AI safety.
- PULSE replaces model evaluation.
- PULSE replaces human review.
- PULSE is a runtime guardrail.
- PULSE is a generic governance framework.
- Every PULSE repository surface creates release authority.

## Verification checklist before prose expansion

Before expanding a selected claim into manuscript prose, verify:

- exact artifact path exists;
- artifact role matches the claim;
- authority / role status is vocabulary-valid;
- verification status is no longer `to verify before manuscript`;
- limitation claims are marked `accepted limitation`;
- future-work claims are marked `accepted future-work`;
- non-normative surfaces are not inflated into authority;
- current capability is not confused with future work;
- wording does not use result worship or post-hoc explanation as proof.

## Manuscript wording rules

Use:

- mechanism;
- release-authority path;
- artifact-bound;
- policy-declared;
- gate-materialized;
- CI-enforced;
- fail-closed;
- recorded evidence;
- release-state artifact;
- reconstructable packet;
- evidence relation;
- release boundary.

Avoid as identity framing:

- framework;
- dashboard;
- checklist;
- scorecard;
- governance layer;
- post-hoc audit system;
- runtime guardrail;
- AI safety proof.

## Minimum first-draft structure

The first full draft should be built from selected claims only:

1. Problem gap.
2. PULSEmech mechanism.
3. Normative path.
4. Authority boundary.
5. Implementation artifact classes.
6. PULSE-REF reference packet path.
7. Validation and drift regression.
8. Limitations.
9. Reproducibility spine.
10. Conclusion.

## Review outcome

This review selects a narrow first-draft claim set.

It does not yet mark claims as `verified for manuscript`.

The next step is artifact verification for the selected claims.

## Validation checks for this review

Before merging changes to this review, run:

```bash
grep -n "Manuscript-facing claim table" docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
grep -n "D02_CORE_MECHANISM" docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
grep -n "D12_DRIFT_REGRESSION" docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
grep -n "Claims deferred from first full draft" docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
grep -n "Verification checklist before prose expansion" docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md
```

Expected result:

- manuscript-facing claim table is present;
- core mechanism claim is present;
- drift regression claim is present;
- deferred claim directions are present;
- verification checklist is present.

## Next paper step

After this review is merged, the next paper step is:

`docs(paper): verify PULSEmech manuscript claim artifacts`

That step should verify selected claims against exact repository artifact paths and update verification statuses before any full prose expansion.
