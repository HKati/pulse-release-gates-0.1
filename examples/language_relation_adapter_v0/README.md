# Language Relation Adapter Evaluation v0 — authored import controls

These files exercise the LRM-05 preserved-response importer. They are
**synthetic fixtures authored for tests, not observed model/provider outputs**.
No live extraction experiment or model-quality result is recorded here.

The controlling implementation contract is
[Language Relation Adapter Evaluation v0](../../docs/PULSEMECH_LANGUAGE_RELATION_ADAPTER_EVALUATION_v0.md).
The preserved LRM-01 profile and reference corpus remain unchanged.

## File roles

| File | Purpose |
| --- | --- |
| `requests.json` | Fixed source-only request inventory: 23 cases, 24 questions, 14 EN cases and 9 HU cases. |
| `captures.json` | Synthetic capture-index declarations for five selected cases; all other cases intentionally have no record. |
| `responses/en_identity.json` | Candidate for REF01: independently checkable English identity control. |
| `responses/hu_connective.json` | Candidate for REF05: the Hungarian source AND/OR difference is represented on its proper side. |
| `responses/en_quote_mismatch.json` | Deliberately wrong REF10 candidate: the before-side quotation wrapper is erased while the source bytes remain intact. |

Only `requests.json`, the public finite profile and the public input contract
belong in producer request material. The authored response files are import
controls and must not be supplied as hidden answers to an extraction experiment.
The evaluator does not load the old corpus or its expected-result file.

The exact request inventory is 37,506 bytes, SHA-256:

```text
a147703b992e7236e839174c9fe72cd71c83e4781ac27a1c81076fb9c222ca22
```

A request contains exact source/context records and source-grounded question
metadata. It excludes reference ASTs, target root IDs, correspondence, coverage
claims, interpretation families and verdicts. Its per-request digest uses the
existing profile-defined `canonical_bytes` function.

## Deliberate fixture behavior

| Case | Fixture declaration or checker behavior |
| --- | --- |
| REF01 | Completed saved candidate; before and after mapping pass. |
| REF02 | Producer-declared unsupported free paraphrase; one explicitly located unresolved correspondence item. |
| REF03 | Producer-declared extraction failure; no response file. |
| REF05 | Completed saved candidate; before and after mapping pass. |
| REF10 | Completed saved candidate; before mapping fails, after mapping passes. Confidence is deliberately `0.99` and cannot override the failure. |
| Other 18 cases | No capture record; all remain in the report as missing. |

The intended accounting is 3 checked candidates, 1 producer-declared unsupported
case, 1 producer-declared failed case and 18 missing cases. Of the 46 side-mapping
slots, 5 pass, 1 fails and 40 are not run. All 23 cases and all 24 questions remain
visible. These are importer-control outcomes, not extraction-accuracy scores.

A source-root mapping pass does not verify that the candidate selected the right
roots for a question. Every question keeps `scope_selection: "not_verified"`,
`representation_basis: "candidate_only"` and `claim_scope: "candidate_structures"`.
The captured confidence and producer identity are declarations only.

## Running the fixture

From the repository root, with the existing test dependencies installed:

```bash
python tools/evaluate_language_relation_candidates_v0.py evaluate \
  --records examples/language_relation_adapter_v0/captures.json \
  --package-root examples/language_relation_adapter_v0 \
  --output-dir /tmp/lrm05-import-controls
```

Choose a fresh output directory for each execution. Its parent must exist.
A completed report includes exact requests/records, observed raw responses, checked
input/verification pairs and the evaluation artifact. Exit zero means completed
diagnostics, including the deliberate mismatch and missing responses. The saved
`records.json` retains its original response locators; the evaluation report
names the observed response copies. It is not a rewritten replay index.

The report retains `model_quality: "not_evaluated"`,
`reference_agreement: "not_evaluated"`,
`producer_authentication: "not_verified"` and
`historical_input_isolation: "not_verified"`. No runtime trust configuration is
provided or created by this fixture.

For a real saved-response import, author a separate capture index with
`record_origin: "preserved_model_response"`, exact request/response pins and
`captured_input` candidate provenance. Preserve actual failures and unsupported
cases. Do not relabel these synthetic fixtures as a model run.

All artifacts remain diagnostic: `authority_effect: "none"`,
`release_authority_activation: false`, and `authority_status: "none"`.
