# PULSEmech Regression Source Gap Closure v0

Status: regression source gap closure  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document closes the `RW-SRC-017` regression / snapshot / golden-testing source gap for the future PULSEmech cs.SE paper.

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
- `docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md`
- `docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md`
- `docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md`

The purpose is to replace the unresolved placeholder `RW-SRC-017` with concrete source candidates for regression testing and golden-master-style testing context.

This document does not finalize the bibliography.

This document does not add new PULSEmech mechanism claims.

This document does not create an arXiv submission package.

This document does not change PULSE release-authority semantics.

## Working rule

Do not close a source gap by decoration.

Close it only when the replacement source supports the mechanism or boundary relation that the gap represents.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Regression-source rule:

Do not claim that external regression-testing literature authorizes PULSE release decisions.

Use regression-testing literature only to contextualize the internal PULSE-REF generated-packet regression and drift-detection method.

## Closure target

The gap being closed is:

```text
RW-SRC-017 — regression / snapshot / golden testing literature placeholder
```

The previous status was:

```text
needs replacement
```

The new closure decision is:

```text
replace RW-SRC-017 with two concrete sources:
- RW-SRC-021
- RW-SRC-022
```

## Replacement source summary

| New Source ID | Canonical Area ID | Citation key | Source role | Include decision | Closure role |
|---|---|---|---|---|---|
| `RW-SRC-021` | `RW13_RELEASE_DECISION_STABILITY`; `RW02_CI_CD_GATES` | `Pan2021MLTSPReview` | methodological support / context | include | General regression testing / test selection-prioritization context. |
| `RW-SRC-022` | `RW13_RELEASE_DECISION_STABILITY`; `RW06_REPRODUCIBLE_ARTIFACTS` | `Kraus2020VisualTestingGoldenMaster` | methodological support / boundary context | reserve-or-include | Golden-master-style testing context for generated artifact comparison / drift detection. |

## Source metadata closure table

| Source ID | Area ID | Citation key | Metadata | Locator | Source role | Include decision | Lock status | Boundary |
|---|---|---|---|---|---|---|---|---|
| `RW-SRC-021` | `RW13_RELEASE_DECISION_STABILITY`; `RW02_CI_CD_GATES` | `Pan2021MLTSPReview` | Rongqi Pan, Mojtaba Bagherzadeh, Taher A. Ghaleb, Lionel Briand. “Test Case Selection and Prioritization Using Machine Learning: A Systematic Literature Review.” arXiv preprint, 2021. | arXiv:2106.13891; final venue / DOI if any still to verify before submission. | methodological support / context | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Supports regression testing / test selection-prioritization context; does not define PULSEmech release authority. |
| `RW-SRC-022` | `RW13_RELEASE_DECISION_STABILITY`; `RW06_REPRODUCIBLE_ARTIFACTS` | `Kraus2020VisualTestingGoldenMaster` | Daniel Kraus, Jeremias Rößler, Martin Sulzmann. “Visual Testing of GUIs by Abstraction.” arXiv preprint, 2020. | arXiv:2007.10419; final venue / DOI if any still to verify before submission. | methodological support / boundary context | reserve-or-include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Supports golden-master-style comparison context; does not claim PULSE-REF is a GUI visual testing method. |

## Closure decision

`RW-SRC-017` should no longer be used as a source placeholder in manuscript-facing prose.

The closure path is:

```text
RW-SRC-017
→ replaced by RW-SRC-021 for general regression testing / test selection-prioritization context
→ optionally supported by RW-SRC-022 for golden-master-style comparison context
```

## Manuscript impact

The citation-keyed related-work draft should replace:

```text
[Source needed: RW13_RELEASE_DECISION_STABILITY / regression testing]
```

with a lock-aware source note such as:

```text
[Source: Pan2021MLTSPReview; submission lock required for final venue / DOI metadata]
```

If golden-master-style context is kept, it may also add:

```text
[Source: Kraus2020VisualTestingGoldenMaster; submission lock required for final venue / DOI metadata]
```

## Recommended prose adjustment

The related-work prose should remain compact.

Recommended replacement wording:

```text
Regression testing and test-selection literature provides the broader software-testing context for treating regression checks as mechanisms for detecting unintended changes after software evolution [Source: Pan2021MLTSPReview; submission lock required for final venue / DOI metadata]. Golden-master-style testing is also relevant as a comparison pattern for detecting output drift against a reference artifact, but PULSE-REF uses this idea only as internal packet-output drift detection, not as release authority [Source: Kraus2020VisualTestingGoldenMaster; submission lock required for final venue / DOI metadata].
```

Boundary sentence:

```text
These sources contextualize regression and reference-output comparison; they do not authorize PULSE releases and do not replace the PULSEmech declared-policy evidence-to-decision path.
```

## Source-boundary constraints

When using `RW-SRC-021`:

- use it for regression testing / test selection-prioritization context;
- do not use it as proof that PULSE validates model safety;
- do not use it as release-authority evidence;
- do not turn test selection/prioritization into the PULSEmech mechanism.

When using `RW-SRC-022`:

- use it only for golden-master-style reference-output comparison context;
- do not imply that PULSE-REF is GUI visual testing;
- do not imply that golden-master comparison grants release permission;
- do not treat visual-testing results as equivalent to PULSE release authority.

## Source-table update requirements

A later source-table update should:

1. add `RW-SRC-021` to the literature source table;
2. add `RW-SRC-022` to the literature source table as `reserve-or-include` or `reserve`;
3. mark `RW-SRC-017` as closed by replacement;
4. update the initial include set if `RW-SRC-021` is used in related-work prose;
5. update the reserve set if `RW-SRC-022` remains optional;
6. update the source metadata lock with both new sources;
7. preserve `submission-lock-required` status until final venue / DOI metadata is verified.

## Citation-key replacement requirements

Before replacing prose markers:

| Source ID | Citation key | Replacement treatment |
|---|---|---|
| `RW-SRC-021` | `Pan2021MLTSPReview` | lock-note replacement |
| `RW-SRC-022` | `Kraus2020VisualTestingGoldenMaster` | lock-note replacement if included; reserve-only if not promoted |

`RW-SRC-017` must not receive a citation key.

## Updated source-gap status

| Gap ID | Previous status | New closure status | Notes |
|---|---|---|---|
| `G01_RW_SRC_017` | replace-or-remove | closed-by-replacement-planned | Replacement sources selected; source table / metadata lock update still required. |
| `RW-SRC-017` | needs replacement | deprecated placeholder | Must not appear in final manuscript prose. |
| `RW-SRC-021` | new | submission-lock-required | Main regression-testing context source. |
| `RW-SRC-022` | new | submission-lock-required / reserve-or-include | Optional golden-master-style context source. |

## Closure gate

The regression source gap is closed for planning only after this document is merged.

It becomes closed for manuscript only after:

- `RW-SRC-021` is added to the literature source table;
- source metadata lock includes `RW-SRC-021`;
- related-work prose replaces the `RW-SRC-017` placeholder;
- `RW-SRC-017` is removed from manuscript-facing prose;
- `RW-SRC-022` is either included with lock note or held in reserve with explicit non-use status;
- final citation metadata remains locked or visibly `submission-lock-required`.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Replacement source summary$' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n '^## Source metadata closure table$' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n '^## Closure decision$' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n '^## Source-table update requirements$' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n '^## Updated source-gap status$' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n 'RW-SRC-021' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n 'RW-SRC-022' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n 'Pan2021MLTSPReview' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n 'Kraus2020VisualTestingGoldenMaster' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_REGRESSION_SOURCE_GAP_CLOSURE_v0.md
```

Expected result:

- replacement source summary is present;
- source metadata closure table is present;
- closure decision is present;
- source-table update requirements are present;
- updated source-gap status is present;
- `RW-SRC-021` is present;
- `RW-SRC-022` is present;
- `Pan2021MLTSPReview` is present;
- `Kraus2020VisualTestingGoldenMaster` is present;
- `RW-SRC-017` remains tracked as deprecated placeholder.

## Next paper step

After this regression source gap closure document is merged, the next paper step is:

`docs(paper): update PULSEmech source tables for regression gap closure`

That step should update the literature source table, source metadata lock, and related-work prose to reflect `RW-SRC-021` / `RW-SRC-022` and retire `RW-SRC-017` from manuscript-facing prose.
