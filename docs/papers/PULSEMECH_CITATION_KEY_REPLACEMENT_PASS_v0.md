# PULSEmech Citation Key Replacement Pass v0

Status: citation key replacement pass  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document defines the first citation-key replacement pass for the PULSEmech cs.SE paper.

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
- `docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md`
- `docs/papers/PULSEMECH_RELATED_WORK_PROSE_v0.md`
- `docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md`
- `docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md`

The purpose is to define which `RW-SRC-*` source markers may be replaced with provisional citation keys in later prose drafts.

This document does not finalize bibliography entries.

This document does not create an arXiv submission package.

This document does not change PULSE release-authority semantics.

## Working rule

Do not replace a source marker just because a citation key exists.

Replace only when the lock state allows safe replacement.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Citation-key rule:

Do not cite a source as a finished bibliographic object until its metadata, locator, venue/year boundary, role, and lock state allow that use.

## Replacement boundary

This pass is not the final bibliography.

This pass is not final citation formatting.

This pass does not remove the source metadata lock as the controlling trace surface.

The source metadata lock remains the controlling document for:

- source ID;
- citation key;
- area ID;
- metadata;
- locator;
- lock status;
- venue/year boundary;
- include decision;
- source boundary.

## Replacement status vocabulary

| Replacement status | Meaning |
|---|---|
| `replace-now` | The `RW-SRC-*` marker may be replaced with the provisional citation key in a citation-keyed prose draft. |
| `replace-with-lock-note` | The marker may be paired with a provisional key only if the draft preserves the submission-lock note. |
| `do-not-replace` | The marker must remain as `RW-SRC-*` or be removed until source lock is complete. |
| `boundary-only-replace` | The marker may be replaced only in boundary / contrast prose, and any required lock note must remain visible. |
| `reserve-only` | Do not use in current prose unless the source is explicitly promoted in a later source-selection update. |
| `needs-replacement` | Placeholder or insufficient source; replace with a real source before use. |

## Replacement eligibility rule

A source is eligible for `replace-now` only when:

1. it appears in `docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md`;
2. it has a citation key assigned;
3. its lock state is `citation-ready-draft`;
4. it is not marked `submission-lock-required`;
5. it is not a placeholder;
6. it is not reserve-only;
7. its boundary is preserved in prose.

A source marked `submission-lock-required` must not be silently converted into a normal citation key.

A source marked `boundary-only` may be used only for contrast / non-identity framing.

A source marked both `boundary-only` and `submission-lock-required` must preserve both constraints during replacement.

A reserve source must remain unused until it is explicitly promoted in a later source-selection update.

A source marked `needs replacement` must not enter citation-keyed prose.

## Replacement table

| Source ID | Provisional citation key | Current lock condition | Replacement status | Allowed use | Boundary |
|---|---|---|---|---|---|
| `RW-SRC-001` | `Shahin2017CICDReview` | `submission-lock-required`; final IEEE Access DOI / publication metadata still to verify before submission. | replace-with-lock-note | CI/CD context only, if lock note is preserved. | Not PULSEmech release authority. |
| `RW-SRC-003` | `OPA_PolicyAsCode` | `submission-lock-required`; official documentation version/date or access date still to lock. | replace-with-lock-note | Policy-as-code context only, if documentation version/date lock note is preserved. | Policy text alone does not authorize release. |
| `RW-SRC-004` | `NIST2022SSDF` | `citation-ready-draft` | replace-now | Secure software development / assurance context. | Not a complete PULSEmech assurance case. |
| `RW-SRC-005` | `SLSA2026Spec` | `submission-lock-required`; SLSA v1.2 version/date still to lock. | replace-with-lock-note | Supply-chain provenance context, if SLSA version lock note is preserved. | Provenance does not authorize release by itself. |
| `RW-SRC-007` | `InTotoSpec` | `submission-lock-required`; exact specification / documentation version still to lock. | replace-with-lock-note | Supply-chain metadata / traceability comparison, if version lock note is preserved. | Trace metadata is not release authority. |
| `RW-SRC-009` | `ACM2020ArtifactBadging` | `citation-ready-draft` | replace-now | Artifact review / reproducibility terminology. | Does not prove external replication of PULSE-REF. |
| `RW-SRC-010` | `JSONSchema2020` | `citation-ready-draft` | replace-now | Schema and typed artifact context. | Schema validity is not release permission. |
| `RW-SRC-012` | `Sculley2015MLDebt` | `submission-lock-required`; final DOI / proceedings metadata still to verify before submission. | replace-with-lock-note | AI systems engineering context, if final DOI / venue lock note is preserved. | Not PULSEmech identity. |
| `RW-SRC-014` | `Mitchell2019ModelCards` | `submission-lock-required`; final ACM DOI / proceedings metadata still to verify before submission. | replace-with-lock-note | Model documentation / evaluation artifact boundary, if ACM DOI / proceedings lock note is preserved. | Model cards are evidence surfaces, not release permission. |
| `RW-SRC-015` | `NIST2023AIRMF` | `submission-lock-required`; `boundary-only`; final NIST AI RMF DOI / PDF locator still to verify before submission. | boundary-only-replace | AI governance / risk boundary contrast only, with explicit DOI / PDF locator lock note. | Do not frame PULSEmech as generic AI governance; do not drop the submission lock note. |
| `RW-SRC-016` | `Wang2026GuardrailsSoK` | `submission-lock-required`; IEEE S&P 2026 venue boundary pending final proceedings metadata / DOI. | replace-with-lock-note | Runtime guardrail boundary contrast, with explicit venue / DOI lock note. | Runtime guardrails differ from pre-release authority; do not drop the submission lock note. |
| `RW-SRC-017` | none | unresolved placeholder | needs-replacement | Do not use. | Replace or remove before submission-stage related work. |
| `RW-SRC-019` | `Okafor2022SupplyChainSoK` | `submission-lock-required`; ACM SCORED 2022 venue boundary pending final proceedings metadata / DOI. | replace-with-lock-note | Supply-chain security context only, with explicit venue / DOI lock note. | Supply-chain security context, not PULSEmech mechanism. |

## Direct replacement set

These sources may be replaced directly with citation keys in a citation-keyed prose draft:

| Source ID | Citation key |
|---|---|
| `RW-SRC-004` | `NIST2022SSDF` |
| `RW-SRC-009` | `ACM2020ArtifactBadging` |
| `RW-SRC-010` | `JSONSchema2020` |

These replacements are still provisional.

Final bibliography formatting remains required before submission-stage use.

## Lock-note replacement set

These sources may be paired with provisional citation keys only if the draft preserves a lock note or planning trace:

| Source ID | Citation key | Required lock note |
|---|---|---|
| `RW-SRC-001` | `Shahin2017CICDReview` | final IEEE Access DOI / publication metadata still to verify before submission |
| `RW-SRC-003` | `OPA_PolicyAsCode` | official documentation version/date or access date still to lock |
| `RW-SRC-005` | `SLSA2026Spec` | SLSA v1.2 version/date still to lock |
| `RW-SRC-007` | `InTotoSpec` | exact specification / documentation version still to lock |
| `RW-SRC-012` | `Sculley2015MLDebt` | final DOI / proceedings metadata still to verify before submission |
| `RW-SRC-014` | `Mitchell2019ModelCards` | final ACM DOI / proceedings metadata still to verify before submission |
| `RW-SRC-015` | `NIST2023AIRMF` | final NIST AI RMF DOI / PDF locator still to verify before submission |
| `RW-SRC-016` | `Wang2026GuardrailsSoK` | final IEEE S&P 2026 proceedings metadata / DOI still to verify before submission |
| `RW-SRC-019` | `Okafor2022SupplyChainSoK` | final ACM SCORED 2022 proceedings metadata / DOI still to verify before submission |

## Boundary-only replacement set

These sources may be used only for boundary contrast.

If a boundary-only source is also `submission-lock-required`, the replacement must preserve the required lock note.

| Source ID | Citation key | Boundary | Required lock note |
|---|---|---|---|
| `RW-SRC-015` | `NIST2023AIRMF` | Governance / risk context only; not PULSEmech identity. | final NIST AI RMF DOI / PDF locator still to verify before submission |

## Do-not-replace set

These source markers must not be replaced in current prose:

| Source ID | Reason |
|---|---|
| `RW-SRC-017` | unresolved placeholder; must be replaced with a real regression / snapshot / golden testing source or removed. |
| reserve sources not explicitly promoted | reserve-only until explicitly promoted in a later source-selection update. |

## Replacement guidance for related-work prose

When converting `docs/papers/PULSEMECH_RELATED_WORK_PROSE_v0.md` into a citation-keyed draft:

1. Replace `RW-SRC-004`, `RW-SRC-009`, and `RW-SRC-010` directly with citation keys.
2. For `submission-lock-required` sources, either:
   - keep the `RW-SRC-*` marker; or
   - use the provisional citation key with a visible lock note in the planning document.
3. For `boundary-only` sources, use boundary-marker wording and preserve any required lock note.
4. Do not replace `RW-SRC-017`.
5. Preserve every source boundary.
6. Do not use reserve sources unless they are explicitly promoted in a later source-selection update.
7. Do not cite governance sources as PULSEmech identity sources.
8. Do not cite runtime guardrail sources as PULSEmech mechanism sources.
9. Do not cite provenance sources as release-authority sources.
10. Do not cite schema sources as release-permission sources.
11. Do not allow arXiv submission year to override proceedings year or accepted venue boundary.
12. Do not remove the source metadata lock trace.

## Proposed citation-keyed marker format

For direct replacement:

```text
[Source: NIST2022SSDF]
```

For lock-note replacement:

```text
[Source: Wang2026GuardrailsSoK; submission lock required for final IEEE S&P 2026 proceedings metadata]
```

For boundary-only replacement with no separate lock requirement:

```text
[Boundary source: <CitationKey>; boundary context only]
```

For boundary-only replacement with a submission-lock requirement:

```text
[Boundary source: NIST2023AIRMF; governance / risk context only; submission lock required for final NIST AI RMF DOI / PDF locator]
```

For runtime-guardrail contrast with a submission-lock requirement:

```text
[Source: Wang2026GuardrailsSoK; runtime guardrail contrast; submission lock required for final IEEE S&P 2026 proceedings metadata]
```

For unresolved placeholders:

```text
[Source needed: RW13_RELEASE_DECISION_STABILITY / regression testing]
```

## Citation-keyed prose requirements

A future citation-keyed prose draft must include:

- citation-keyed related-work prose;
- preserved lock notes for `submission-lock-required` sources;
- preserved lock notes for boundary-only sources that are also `submission-lock-required`;
- no replacement for `RW-SRC-017`;
- no reserve source unless explicitly promoted in a later source-selection update;
- no source used outside its boundary;
- no final bibliography claim;
- next step pointing to final bibliography / BibTeX draft.

## Replacement audit checklist

Before merging a citation-keyed prose draft, verify:

- all direct replacements come from the `replace-now` set;
- all lock-required replacements preserve lock notes;
- all boundary-only replacements preserve boundary wording;
- `RW-SRC-015` boundary-only replacement preserves the NIST AI RMF DOI / PDF locator submission-lock note;
- `RW-SRC-016` remains in the lock-note replacement set and is not treated as boundary-only replacement;
- `RW-SRC-016` preserves the IEEE S&P 2026 proceedings metadata / DOI submission-lock note;
- `RW-SRC-016` uses `Wang2026GuardrailsSoK`, not `Wang2025GuardrailsSoK`;
- `RW-SRC-019` uses `Okafor2022SupplyChainSoK`, not `Okafor2024SupplyChainSoK`;
- `RW-SRC-017` is not converted to a citation key;
- reserve sources are not used unless explicitly promoted in a later source-selection update;
- no source boundary is removed;
- no source becomes final bibliography by implication.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Replacement table$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n '^## Direct replacement set$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n '^## Lock-note replacement set$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n '^## Boundary-only replacement set$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n '^## Do-not-replace set$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n '^## Replacement audit checklist$' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
awk '/^## Replacement table$/{flag=1} /^## Direct replacement set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-015.*final NIST AI RMF DOI / PDF locator still to verify before submission'
awk '/^## Lock-note replacement set$/{flag=1} /^## Boundary-only replacement set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-015.*final NIST AI RMF DOI / PDF locator still to verify before submission'
awk '/^## Boundary-only replacement set$/{flag=1} /^## Do-not-replace set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-015.*final NIST AI RMF DOI / PDF locator still to verify before submission'
awk '/^## Proposed citation-keyed marker format$/{flag=1} /^## Citation-keyed prose requirements$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'submission lock required for final NIST AI RMF DOI / PDF locator'
awk '/^## Replacement table$/{flag=1} /^## Direct replacement set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-016.*replace-with-lock-note'
awk '/^## Boundary-only replacement set$/{flag=1} /^## Do-not-replace set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-015'
! awk '/^## Boundary-only replacement set$/{flag=1} /^## Do-not-replace set$/{flag=0} flag' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md | grep -n 'RW-SRC-016'
! grep -n 'unless need[e]d' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n 'Wang2026GuardrailsSoK' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n 'Okafor2022SupplyChainSoK' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md
```

Expected result:

- replacement table is present;
- direct replacement set is present;
- lock-note replacement set is present;
- boundary-only replacement set is present;
- do-not-replace set is present;
- replacement audit checklist is present;
- NIST AI RMF lock-note wording is present in the replacement table;
- NIST AI RMF lock-note wording is present in the lock-note replacement set;
- NIST AI RMF lock-note wording is present in the boundary-only replacement set;
- NIST AI RMF lock-note wording is present in the marker-format example;
- `RW-SRC-016` remains `replace-with-lock-note`;
- `RW-SRC-016` is not present in the boundary-only replacement set;
- reserve sources require explicit promotion;
- corrected guardrail source key is present;
- corrected supply-chain source key is present;
- unresolved placeholder is tracked.

## Next paper step

After this citation key replacement pass is merged, the next paper step is:

`docs(paper): add PULSEmech citation-keyed related-work draft v0`

That step should update related-work prose with safe citation-key markers while preserving lock notes and source boundaries.
