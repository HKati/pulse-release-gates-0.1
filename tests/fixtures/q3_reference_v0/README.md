# Synthetic Q3 reference fixtures

These fixtures test the standalone `q3_input_recomputation_v0.1` profile. They
contain programmed examples, labels and slice metadata. They are not model
outputs, historical Q2 data, an actual dataset acquisition, current-run release
evidence, or proof of label/source authenticity. `authority_effect` remains
`none` even when a synthetic metric passes and its checker accepts the report.

## Contents

- `fixture_builder.py` materializes complete examples, labels, manifest, bundle
  and separate caller-selected expected context. It imports neither producer
  nor checker and computes no expected fairness score.
- `case_expectations.json` preserves the selected expected predicates from all
  42 reviewed design cases. Each case is exercised by
  `tests/test_q3_reference_recomputation.py`, including all specified variants.
- `baseline/` contains the stable 400-example, two-group, all-supported input
  payload and its byte inventory. It contains no static producer/run identity.

The fixture builder calculates every digest and byte length from files it
actually writes or reads. A synthetic expected context is selected before any
producer report is inspected. It binds the actual resource files and producer
source snapshot plus the Python version running the fixture builder. Therefore
the same tests work under different supported Python patch versions without
pretending that an old producer/runtime identity describes the new execution.

## Running the focused tests

From the repository root, in its test environment:

```sh
python -m pytest -q tests/test_q3_reference_recomputation.py
```

All executions are local and offline. The test suite invokes only the standalone
producer and independent checker, with synthetic inputs in temporary directories.
It does not activate a gate, run a model, reconstruct Q2, or launch a workflow.

To materialize one reviewable synthetic input outside the checked-in fixtures:

```sh
python tests/fixtures/q3_reference_v0/fixture_builder.py --case 1 --out /tmp/q3-case-001
```

Cases with alternatives require `--variant`; the accepted variant names are in
`VARIANTS` in the builder. Case 37 deliberately omits the expected-context CLI
argument when run by the tests. Cases 34 and 41 mutate only the report after a
valid producer execution. Their metric inputs remain valid; the checker must
reject the changed report with exit 1.

## What is checked

The 42 cases distinguish total and per-group evidence thresholds, exact coverage
boundaries, per-dimension missing coverage, deduplicated small-group union,
non-pruning of the overall/other groups, UNKNOWN/ABSTAIN/UNSUPPORTED handling,
context eligibility, typed missing groups, exact Unicode values, invalid rows,
byte/label/source bindings, missing external expectation, valid-negative metric
verification and report tampering.

Additional focused tests cover deterministic serialization, independent input and
label ordering, undeclared metadata, validation of excluded rows, duplicate or
missing labels, malformed JSON/JSONL, closed envelopes, manifest compatibility,
schema/contract resource pins, source-authentication limits, safe paths and
non-overwrite of input files. A static AST guard rejects producer imports and
process/dynamic-import dependencies in the checker; it is an additional guard,
not a general proof of program independence.

Analytical Wilson endpoint expectations permit a diagnostic absolute error of
`1e-14` to account for binary64 rounding. Every pass/fail threshold is evaluated
without epsilon. A separate 72/73-member-group test checks two gaps that both
display as `0.05` when rounded but must receive different decisions.

## Binding-attack discipline

For semantic-invalid inputs, the builder refreshes unrelated outer hashes so
validation reaches the intended defect. For byte/anchor attacks, it keeps the
original named anchor fixed. Modified specifications and producer source files
are isolated copies; the original repository resources are not changed.

A fully self-consistent replacement with a newly selected external expectation
can be verified as that newly selected input. That does not authenticate the
original source, labels or model run. The fixed-original-anchor tests separately
prove that the same replacement cannot substitute for the original expectation.
