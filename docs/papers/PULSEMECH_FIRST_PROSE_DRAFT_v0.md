# PULSEmech First Prose Draft v0

Status: first prose draft  
Paper status: controlled manuscript-style draft  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper draft  
Repository status: does not change PULSE release-authority semantics

## Draft-control notice

This is the first controlled prose draft for the future PULSEmech cs.SE paper.

It follows:

- `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`
- `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`
- `docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md`
- `docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md`
- `docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md`

This draft does not introduce new technical claims.

This draft does not promote path-verified claims into final manuscript status.

This draft must be checked against artifact references before submission-stage use.

This draft does not change PULSE release-authority semantics.

## Working title

Artifact-Bound Release Authority for AI Applications:  
A Fail-Closed Evidence-to-Decision Mechanism

## Short title

PULSEmech: Artifact-Bound Release Authority for AI Release Decisions

## Abstract

AI applications and AI-enabled systems can produce probabilistic behavior and evolving release evidence, while software release permission requires a deterministic decision at the release boundary. This paper presents PULSEmech, an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision mechanism for AI release decisions.

PULSEmech binds recorded release evidence to a machine-readable `status.json` artifact, declared gate policy, materialized required gates, and strict fail-closed CI enforcement before a declared-policy CI allow/block decision can materialize. The mechanism separates normative release-authority surfaces from trace, audit, reader, diagnostic, and packet-preparation surfaces.

The paper also describes the PULSE-REF support layer: a guarded release-reference fixture, schema-aligned packet construction, packet validation, publication-reference hardening, and normalized generated-packet regression. The contribution is a software-engineering release-authority mechanism. It is not a model-safety proof, runtime guardrail, or generic governance framework.

## 1. Introduction

AI applications and AI-enabled systems create a software-engineering problem at the release boundary. Their behavior and evidence surfaces can be probabilistic, evolving, detector-mediated, review-mediated, or CI-mediated. At the same time, software release permission must be expressed as a deterministic decision before deployment effects propagate.

This creates a structural gap between candidate AI behavior and deterministic software release permission. Scores, dashboards, reports, review statements, and pipeline outputs can provide evidence, but they do not by themselves define artifact-bound release authority. A release decision requires a controlled path that determines when recorded evidence is strong enough to authorize release under declared policy.

PULSEmech addresses this gap by defining a release-authority mechanism in which permission materializes only through a recorded evidence state, a machine-readable status artifact, declared policy, materialized required gates, and strict fail-closed CI enforcement. The mechanism shifts release-decision integrity from post-outcome explanation to pre-release artifact-bound relation measurement.

The paper focuses on PULSEmech as a software-engineering mechanism for AI release decisions. It does not present a new machine learning model, training method, runtime guardrail, or proof that an AI system is safe. It also does not define PULSE as a generic governance framework. The technical contribution is narrower: artifact-bound release authority for AI applications and AI-enabled systems.

## 2. Release-authority model

PULSEmech defines release authority as a materialized evidence-to-decision path. The mechanism does not infer release permission from a detached score, dashboard, review statement, or post-outcome explanation. Instead, release permission materializes only when recorded evidence, release-state artifacts, declared policy, materialized gates, and fail-closed enforcement are bound together at the release boundary.

The PULSEmech deterministic decision tuple is:

```text
(recorded release evidence,
 status.json,
 declared gate policy,
 materialized required gate set,
 strict fail-closed CI checking)
→ CI allow/block release decision
```

The normative PULSEmech path is:

```text
recorded release evidence
→ recorded status.json artifact
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
```

This path is relational rather than decorative. The decision is not created by the presence of one artifact in isolation. A `status.json` file alone does not authorize release. A policy file alone does not authorize release. A manifest alone does not authorize release. A release decision materializes through the complete relation between recorded evidence, machine-readable release state, declared policy, materialized required gates, and fail-closed CI enforcement.

In this model, release authority is located before release effects propagate. The mechanism measures whether release permission can materialize from the pre-release evidence relation. It does not rely on explaining an outcome after deployment.

## 3. Normative artifact path

The normative artifact path begins with recorded release evidence. Candidate evidence becomes release-relevant when it is represented in a machine-readable release-state artifact and evaluated under declared policy.

The `status.json` artifact records machine-readable release state. It is interpreted in relation to the declared gate policy, the selected required gate set, and the release mode. The status artifact is not a free-standing release decision; it is a normative input when bound to the rest of the PULSEmech path.

Declared gate policy defines the gate sets used by the release lane. The gate registry stabilizes gate identity and meaning. Policy-derived materialization turns declared gate sets into concrete required gates. This matters because gate enforcement should not depend on ad hoc promotion or hidden hard-coding. Required gates must be derived from declared policy.

Strict fail-closed CI enforcement evaluates required gates as literal true-only release conditions. Missing, false, malformed, or non-literal required gate states do not silently become release permission. In the enforced path, the declared-policy CI allow/block outcome is the release decision.

This is the core software-engineering role of PULSEmech: it converts recorded release evidence into deterministic release permission under declared policy, while preserving the path by which that decision was produced.

## 4. Authority boundary

PULSE separates normative release-authority surfaces from trace, preservation, reader, diagnostic, and packet-preparation surfaces.

Normative surfaces define or enforce the release decision. These include recorded release evidence when bound into the decision path, the machine-readable release-state artifact, declared policy, materialized required gates, and strict fail-closed CI checking.

Trace surfaces record the decision path. Preservation surfaces retain artifacts for audit or reconstruction. Reader surfaces render release state for humans or public surfaces. Diagnostic surfaces may produce candidate evidence, but they do not affect release authority unless explicitly folded into recorded evidence and enforced as required gates under declared policy.

The release authority manifest records the evidence-policy-evaluator chain. It is a trace surface, not a second decision engine. Audit bundles preserve reconstructable evidence, but they do not authorize release. Dashboards, ledgers, badges, and publication pages render or preserve state; they do not create release authority by existing.

This boundary prevents surface-role collapse. A reader surface is not a decision engine. A trace artifact is not an enforcement mechanism. A diagnostic output is not release permission. A packet builder prepares reconstructable artifacts, but it does not authorize release. The normative release decision remains the PULSEmech path.

## 5. PULSE-REF reference path

PULSE-REF provides a support layer for reconstructable reference packet work. The current schema-aligned packet-builder bridge starts from a controlled positive release-reference fixture and produces a reconstructable v0 packet candidate.

The current PULSE-REF chain is:

```text
release_reference_v1/pass fixture
→ release-reference completeness guard
→ policy-derived materialized gates
→ schema-aligned packet builder
→ canonical packet artifacts
→ schema-aligned packet validator
→ publication_snapshot manifest-ref hardening
→ checkpoint doc
→ current v0 packet-completeness boundary
→ normalized generated packet regression
```

The pass fixture is a controlled positive release-reference candidate. The release-reference completeness guard runs before packet generation. The schema-aligned builder prepares a reconstructable v0 packet candidate. The packet validator checks canonical packet artifact shape, manifest references, digest references, schema alignment, policy-derived gate materialization, and reconstruction readiness.

Optional publication snapshot references are hardened when present through safe path, canonical path, packet-root containment, and digest checks. This protects publication-reference integrity without promoting live publication surfaces into release authority.

The generated-packet regression protects the current schema-aligned packet output from silent drift. It uses a normalized golden summary rather than raw full-tree byte comparison, because generated handoff reports can contain environment-specific paths.

The PULSE-REF path supports the paper by showing that PULSEmech is not only described at the decision-path level. It is also supported by artifact preparation, validation, and drift-regression surfaces. These surfaces remain non-normative unless they are part of the declared release-authority path. The fixture does not authorize release. The builder does not create release authority. The validator does not create release authority. The packet preserves and reconstructs the evidence relation.

## 6. Validation and regression strategy

The validation strategy is release-decision integrity validation, not model-performance benchmarking.

PULSE checks whether release permission can materialize under declared policy. Required gates must be present and literal true. Missing, false, malformed, non-literal, stubbed, scaffolded, or incomplete release-reference states fail the relevant guard or checker path.

This validation targets the release decision path rather than model quality in the abstract. It checks whether the evidence-to-decision relation is complete, typed, materialized, and enforced. A run can produce reports or artifacts without producing release authority. A packet can preserve evidence without authorizing release. A publication surface can render state without becoming normative.

Packet validation checks canonical packet artifact shape, manifest references, digest references, schema alignment, policy-derived gate materialization, and reconstruction readiness. The goal is to ensure that a packet candidate can be inspected and reconstructed without confusing packet existence with release permission.

The normalized generated-packet regression protects against silent mechanical drift in builder output. The regression records the current generated packet output as a normalized summary: canonical paths, schema identifiers, package manifest references, policy-derived gate sets, CI outcome core, release-authority decision core, handoff command kinds, digest artifact keys, source fixture identity, and authority-boundary flags. It intentionally avoids raw full-tree byte comparison to avoid failing on environment-specific path noise.

This gives the release-decision mechanism a reproducibility spine: artifact contracts, validators, tests, CI checks, and regression surfaces. It does not claim independent external replication, and it does not claim model safety.

## 7. Limitations

PULSE does not prove that an AI system is safe.

PULSE is not a runtime guardrail. It operates at the release boundary before deployment, not at the live interaction boundary during use.

PULSE does not replace human review. It records, structures, and enforces release evidence under declared policy. Human review may remain part of the evidence field or operational process, but PULSE does not replace human judgment.

PULSE does not turn dashboards, ledgers, manifests, audit bundles, packets, or publication surfaces into release authority by existence.

These limitations are part of the mechanism boundary. They keep the contribution narrow: PULSEmech is a software-engineering release-authority mechanism for AI release decisions.

## 8. Future work

Future work may extend the reference packet path toward stricter RA1-style package verification and larger candidate-state validation.

RA1-style verification may provide a stricter package-verification path for release-reference artifacts. HPC candidate-state scaling may later support broader validation over multiple release candidates, packet states, or evidence configurations.

These directions remain future work unless a future manuscript section cites exact current artifacts and keeps the capability boundary clear. They should not be written as current paper results unless supported by verified current artifact paths.

## 9. Disclosure

The author used AI-assisted drafting and technical editing during manuscript preparation. All claims, artifact references, code paths, repository links, and conclusions were reviewed and approved by the human author, who takes full responsibility for the submitted work.

Final disclosure wording must be checked again before submission.

AI tools are not authors.

## 10. Conclusion

PULSEmech makes AI release permission artifact-bound, policy-declared, gate-materialized, and fail-closed before release effects propagate.

The mechanism shifts release-decision integrity from post-outcome explanation to pre-release artifact-bound relation measurement. Its normative path binds recorded release evidence, a machine-readable release-state artifact, declared policy, materialized required gates, and strict CI enforcement into a declared-policy allow/block release decision.

The paper contribution is a software-engineering release-authority mechanism for AI release decisions, supported by PULSE-REF artifact preparation, validation, and drift-regression surfaces. The contribution is not a model-safety proof, runtime guardrail, or generic governance framework.

## Artifact citation pass required

Before this draft can move toward submission-stage manuscript form, every artifact reference must be checked against:

- `docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md`
- current repository paths;
- generated-run artifact path wording;
- authority-boundary role classification.

Do not cite generated run artifacts as static checked-in repository files.

Do not cite non-normative surfaces as release-authority engines.

## Draft status table

| Section | Status | Next action |
|---|---|---|
| Abstract | first prose draft | verify artifact references and final wording |
| Introduction | first prose draft | verify problem-gap wording |
| Release-authority model | first prose draft | verify tuple wording against README |
| Normative artifact path | first prose draft | verify status / policy / gate wording |
| Authority boundary | first prose draft | verify non-normative surface wording |
| PULSE-REF reference path | first prose draft | verify current chain and v0 boundary |
| Validation and regression strategy | first prose draft | verify regression wording |
| Limitations | first prose draft | keep concise |
| Future work | first prose draft | keep conservative |
| Disclosure | first prose draft | check before submission |
| Conclusion | first prose draft | keep mechanism-focused |

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Abstract$' docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
grep -n '^## 2\. Release-authority model$' docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
grep -n '^## 5\. PULSE-REF reference path$' docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
grep -n '^## 7\. Limitations$' docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
grep -n '^## Artifact citation pass required$' docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md
```

Expected result:

- abstract heading is present;
- release-authority model heading is present;
- PULSE-REF reference path heading is present;
- limitations heading is present;
- artifact citation pass section is present.

## Next paper step

After this first prose draft is merged, the next paper step is:

`docs(paper): add PULSEmech artifact citation pass`

That pass should attach manuscript-facing artifact references to the prose draft and check generated-run artifact wording before any submission-stage draft is prepared.
