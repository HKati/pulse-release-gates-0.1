# PULSEmech Literature Source Table v0

Status: literature source table  
Paper status: pre-related-work support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document records the first source-selection pass for the PULSEmech cs.SE paper.

It follows:

- `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`
- `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`
- `docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md`
- `docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md`
- `docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md`
- `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md`
- `docs/papers/PULSEMECH_CITATION_BOUND_PROSE_DRAFT_v0.md`
- `docs/papers/PULSEMECH_RELATED_WORK_SCAFFOLD_v0.md`
- `docs/papers/PULSEMECH_LITERATURE_SEARCH_PLAN_v0.md`

The purpose is to record candidate external sources before related-work prose is written.

This document does not write the related-work section.

This document does not finalize bibliography entries.

This document does not change PULSE release-authority semantics.

## Working rule

Do not add a source because it sounds related.

Add a source only when it supports mechanism, boundary, context, or contrast.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Source-selection rule:

Do not cite outcomes as mechanisms.

Classify each source by mechanism role, boundary role, or context role.

## Canonical area ID rule

All `Area ID` values must match the canonical related-work area IDs declared in:

- `docs/papers/PULSEMECH_RELATED_WORK_SCAFFOLD_v0.md`
- `docs/papers/PULSEMECH_LITERATURE_SEARCH_PLAN_v0.md`

Do not rename related-work area IDs in this source table.

If a source belongs to multiple areas, list multiple canonical `Area ID` values.

## Source quality tiers

| Tier | Source type | Use |
|---|---|---|
| `T1_PRIMARY` | Peer-reviewed papers, arXiv papers, official standards, official technical specifications, official project documentation for technical systems. | Preferred for related work. |
| `T2_TECHNICAL` | Technical reports, reputable engineering papers, conference proceedings, well-documented open-source project docs. | Acceptable when primary literature is limited. |
| `T3_CONTEXT` | High-quality institutional reports or reputable industry technical blogs. | Context only; not central evidence. |
| `T4_BACKGROUND` | General articles, opinion pieces, popular commentary. | Avoid unless needed for non-technical background. |
| `EXCLUDE` | Marketing pages, unsupported claims, vague governance commentary, vendor promotional material, non-technical opinion. | Do not use. |

## Source role vocabulary

| Source role | Meaning |
|---|---|
| `context` | Locates PULSEmech in a broader technical area. |
| `direct comparison` | Provides mechanism-level comparison. |
| `boundary contrast` | Helps explain what PULSEmech is not. |
| `terminology support` | Supports careful use of standard terms. |
| `methodological support` | Supports validation, reproducibility, regression, or artifact methodology. |
| `standard / specification` | Provides technical standard or formal reference point. |
| `exclude` | Source should not be used in the paper. |

## Include decision vocabulary

| Decision | Meaning |
|---|---|
| `include` | Candidate source is suitable for the first related-work prose pass. |
| `reserve` | Candidate source is useful but should be held for later or used only if space allows. |
| `boundary-only` | Candidate source should be used only to clarify contrast / non-identity. |
| `exclude` | Candidate source should not be used. |
| `needs final citation lock` | Source is useful but must be converted to final citation format and stable locator before submission-stage use. |

## Literature source table

| Source ID | Canonical Area ID | Citation anchor | Source quality tier | Source role | Why relevant | Boundary | Include decision |
|---|---|---|---|---|---|---|---|
| `RW-SRC-001` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | Shahin, Babar, Zhu — “Continuous Integration, Delivery and Deployment: A Systematic Review on Approaches, Tools, Challenges and Practices” | `T1_PRIMARY` | context / direct comparison | Systematic review of continuous integration, delivery, deployment approaches, tools, practices, and challenges. Useful for positioning PULSEmech relative to CI/CD and release gating. | Do not equate CI/CD practice with declared-policy release authority. | include |
| `RW-SRC-002` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | Shahin, Zahedi, Babar, Zhu — “An Empirical Study of Architecting for Continuous Delivery and Deployment” | `T1_PRIMARY` | context / direct comparison | Provides empirical context for continuous delivery/deployment architecture and release practices. | Use for release-engineering context, not as proof that conventional CD provides PULSEmech-style authority. | reserve |
| `RW-SRC-003` | `RW03_POLICY_AS_CODE` | Open Policy Agent documentation | `T1_PRIMARY` | direct comparison / terminology support | Official OPA documentation describes policy-as-code, Rego, policy decision-making, and CI/CD use cases. Useful for declared-policy comparison. | OPA-style policy decisions are context; PULSEmech does not treat policy text alone as release authority. | include |
| `RW-SRC-004` | `RW04_SOFTWARE_ASSURANCE`; `RW05_SUPPLY_CHAIN_PROVENANCE` | NIST SP 800-218 — Secure Software Development Framework (SSDF) Version 1.1 | `T1_PRIMARY` | standard / specification / context | Official NIST guidance for secure software development practices. Useful as software assurance and secure-development context. | SSDF supports secure development context; PULSEmech remains a release-authority mechanism, not a complete assurance framework. | include |
| `RW-SRC-005` | `RW05_SUPPLY_CHAIN_PROVENANCE` | SLSA specification v1.2 | `T1_PRIMARY` | standard / specification / methodological support | Official SLSA specification describes supply-chain security levels, provenance, attestation formats, and artifact verification concepts. | Provenance and verification support reconstruction and trust; they do not themselves authorize release in PULSEmech. | include |
| `RW-SRC-006` | `RW05_SUPPLY_CHAIN_PROVENANCE` | Tamanna et al. — “Analyzing Challenges in Deployment of the SLSA Framework for Software Supply Chain Security” | `T1_PRIMARY` | context / methodological support | Empirical source on adoption challenges for SLSA and provenance workflows. Useful for practical implementation context. | Use to discuss adoption / implementation friction, not PULSEmech identity. | reserve |
| `RW-SRC-007` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | in-toto official documentation / project description | `T1_PRIMARY` | standard / specification / direct comparison | in-toto is an open metadata standard for making software supply-chain steps transparent: what steps were performed, by whom, and in what order. | Supply-chain metadata supports traceability; it is not release authority by itself. | include |
| `RW-SRC-008` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW12_AUDITABILITY_AND_TRACEABILITY` | The Update Framework official project documentation | `T1_PRIMARY` | standard / specification / boundary contrast | TUF provides context for securing software update systems and protecting against compromised repositories or signing keys. | TUF concerns update-system security; PULSEmech concerns release-authority materialization before release. | reserve |
| `RW-SRC-009` | `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | ACM Artifact Review and Badging policy | `T1_PRIMARY` | methodological support / terminology support | ACM artifact policy defines artifact review, reproducibility / repeatability / replicability terminology, and artifact evaluation expectations. | Use for artifact/reproducibility terminology; do not imply PULSE-REF packets are independently reproduced results. | include |
| `RW-SRC-010` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | JSON Schema Draft 2020-12 official specification | `T1_PRIMARY` | standard / specification / terminology support | Official JSON Schema specification supports schema-based artifact shape and validation language. | Schema validity supports artifact checking; it is not release permission. | include |
| `RW-SRC-011` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | Attouche et al. — “Validation of Modern JSON Schema: Formalization and Complexity” | `T1_PRIMARY` | methodological support / reserve | Formalization source for JSON Schema validation complexity. Useful if the paper needs deeper schema-validation context. | Likely too deep for main related work; use only if schema-validation discussion grows. | reserve |
| `RW-SRC-012` | `RW08_MLOPS_RELEASE_READINESS` | Sculley et al. — “Hidden Technical Debt in Machine Learning Systems” | `T1_PRIMARY` | context / boundary contrast | Classic ML systems engineering paper on technical debt and maintenance risks in ML systems. Useful for positioning AI systems as software-engineering objects. | Do not recast PULSEmech as a model-training or ML-debt solution. | include |
| `RW-SRC-013` | `RW08_MLOPS_RELEASE_READINESS` | Google Cloud — “MLOps: Continuous delivery and automation pipelines in machine learning” | `T2_TECHNICAL` | context / boundary contrast | Technical documentation on ML pipelines, CI/CD automation, and model deployment processes. | PULSEmech is not an MLOps platform or training pipeline. | reserve |
| `RW-SRC-014` | `RW09_AI_EVALUATION_INFRASTRUCTURE` | Mitchell et al. — “Model Cards for Model Reporting” | `T1_PRIMARY` | context / boundary contrast | Establishes model documentation and reporting as evaluation / transparency artifacts. Useful for distinguishing evidence documentation from release authority. | Model cards and evaluation reports are candidate evidence, not automatic release permission. | include |
| `RW-SRC-015` | `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | NIST AI Risk Management Framework | `T1_PRIMARY` | boundary contrast / context | Official AI risk-management framework context. Useful only to situate PULSEmech relative to broader AI risk-management language. | Do not frame PULSEmech as a generic AI governance or risk-management framework. | boundary-only |
| `RW-SRC-016` | `RW11_RUNTIME_GUARDRAILS` | Wang et al. — “SoK: Evaluating Jailbreak Guardrails for Large Language Models” | `T1_PRIMARY` | boundary contrast | Systematization of LLM jailbreak guardrails and runtime safety mechanisms. Useful to contrast runtime guardrails with pre-release authority. | PULSEmech is not runtime guardrail behavior; it operates before deployment. | include |
| `RW-SRC-017` | `RW13_RELEASE_DECISION_STABILITY` | Regression / snapshot / golden testing literature placeholder | `T1_PRIMARY` / to fill | methodological support | A stronger specific source is still needed for regression / snapshot / golden testing methodology. | Do not use this placeholder in final prose. | needs final citation lock |
| `RW-SRC-018` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW13_RELEASE_DECISION_STABILITY` | Kalu et al. — “A Longitudinal Study of Usability in Identity-Based Software Signing” | `T1_PRIMARY` | context / methodological support | Current source on identity-based signing usability and verification workflow friction in software signing ecosystems. Useful if source table needs a modern signing / verification workflow source. | Signing usability is context; it does not define PULSEmech release authority. | reserve |
| `RW-SRC-019` | `RW05_SUPPLY_CHAIN_PROVENANCE` | Okafor et al. — “SoK: Analysis of Software Supply Chain Security by Establishing Secure Design Properties” | `T1_PRIMARY` | context / methodological support | Systematizes software supply-chain security properties and approaches. Useful for supply-chain context. | Supply-chain security properties are adjacent context, not the PULSEmech mechanism. | include |
| `RW-SRC-020` | `RW04_SOFTWARE_ASSURANCE`; `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | Barrett et al. — “Actionable Guidance for High-Consequence AI Risk Management” | `T1_PRIMARY` | boundary contrast / reserve | AI risk-management source useful for context if the paper needs a careful governance boundary. | Use only as boundary contrast; do not pull paper into catastrophic-risk governance framing. | reserve |

## Initial include set

The first related-work prose pass should prioritize these sources:

| Source ID | Reason |
|---|---|
| `RW-SRC-001` | CI/CD systematic review context. |
| `RW-SRC-003` | Policy-as-code / declarative enforcement context. |
| `RW-SRC-004` | Secure software development / assurance context. |
| `RW-SRC-005` | Supply-chain provenance and attestation specification context. |
| `RW-SRC-007` | Supply-chain metadata / traceability comparison. |
| `RW-SRC-009` | Artifact review and reproducibility terminology. |
| `RW-SRC-010` | Schema-based artifact contract context. |
| `RW-SRC-012` | AI systems engineering / ML technical debt context. |
| `RW-SRC-014` | AI model documentation / evaluation artifact boundary. |
| `RW-SRC-016` | Runtime guardrail boundary contrast. |
| `RW-SRC-019` | Software supply-chain security context. |

## Reserve set

The following sources should be held in reserve:

| Source ID | Reason |
|---|---|
| `RW-SRC-002` | Useful but may overlap with `RW-SRC-001`. |
| `RW-SRC-006` | Useful SLSA adoption context if source table needs implementation friction. |
| `RW-SRC-008` | Useful for update-system security if supply-chain section expands. |
| `RW-SRC-011` | Useful only if schema validation discussion deepens. |
| `RW-SRC-013` | Useful if MLOps contrast needs more detail. |
| `RW-SRC-018` | Useful if software signing / verification workflow friction becomes relevant. |
| `RW-SRC-020` | Useful only for careful AI governance / risk-management boundary. |

## Gap list after first source pass

The first source pass still has gaps:

| Gap | Needed source type |
|---|---|
| `RW13_RELEASE_DECISION_STABILITY` | Strong source for regression testing, golden tests, snapshot testing, or drift detection in software engineering. |
| `RW12_AUDITABILITY_AND_TRACEABILITY` | A stronger source specifically on traceability / auditability in software systems may be useful. |
| `RW04_SOFTWARE_ASSURANCE` | A stronger software assurance / assurance-case source may be useful if the paper discusses assurance more than briefly. |
| Related-work final prose | Needs source-specific prose after final include set is locked. |
| Bibliography formatting | Needs final citation format, stable URLs/DOIs/arXiv IDs, and commit/release lock. |

## Source use boundaries

### Release engineering / CI/CD

Use sources to say:

- continuous integration, delivery, and deployment are established software-engineering practices;
- release pipelines and gates are part of software release practice;
- PULSEmech differs by making release permission artifact-bound and declared-policy enforced.

Do not say:

- ordinary CI/CD already provides PULSEmech release authority.

### Policy-as-code

Use sources to say:

- policy-as-code / declarative policy engines show machine-checkable policy patterns;
- PULSEmech uses declared gate policy and materialized required gates.

Do not say:

- policy text alone creates release permission.

### Supply-chain provenance

Use sources to say:

- provenance, attestation, metadata, and supply-chain integrity are established technical concerns;
- PULSE-REF packets, manifests, digests, and generated-run artifact wording belong near this area.

Do not say:

- provenance alone authorizes release.

### Reproducible artifacts

Use sources to say:

- artifact review and reproducibility terminology matter for research artifacts and verification;
- PULSE-REF provides reconstructable evidence packets and generated-packet regression.

Do not say:

- PULSE-REF already proves independent external replication.

### AI evaluation / MLOps

Use sources to say:

- AI systems have deployment, evaluation, documentation, and technical-debt concerns;
- PULSEmech treats these as candidate release evidence or context.

Do not say:

- PULSEmech is an ML training system, model card, MLOps platform, or model-performance benchmark.

### Runtime guardrails

Use sources to say:

- runtime guardrails are an active technical area;
- PULSEmech differs by acting before deployment at the release boundary.

Do not say:

- PULSEmech is a runtime safety filter.

## Related-work prose plan

The next related-work prose pass should be compact.

Suggested order:

1. Release engineering and CI/CD release gates.
2. Policy-as-code and declared enforcement.
3. Supply-chain provenance, artifact integrity, and reproducible artifacts.
4. AI release readiness and evaluation artifacts.
5. Runtime guardrails and AI governance as boundary contrast.
6. Decision stability / regression testing gap placeholder.

The prose should use only the `include` sources first.

Reserve sources should be used only if a paragraph needs additional support.

## Bibliography lock required

Before submission-stage use, each included source must be converted to final citation format.

For each source, lock:

- full author list;
- title;
- venue or publisher;
- year;
- DOI if available;
- arXiv ID if applicable;
- stable URL if needed;
- final include decision.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Literature source table$' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n '^## Initial include set$' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n '^## Reserve set$' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n '^## Gap list after first source pass$' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n '^## Related-work prose plan$' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n 'RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n 'RW12_AUDITABILITY_AND_TRACEABILITY' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
grep -n 'RW13_RELEASE_DECISION_STABILITY' docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md
```

Expected result:

- literature source table is present;
- initial include set is present;
- reserve set is present;
- gap list is present;
- related-work prose plan is present;
- canonical area IDs remain aligned with the scaffold and search plan.

## Next paper step

After this literature source table is merged, the next paper step is:

`docs(paper): add PULSEmech related-work prose v0`

That step should write a compact related-work prose section using only the initial include set and preserving all source boundaries.
