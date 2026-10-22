# Q3 standalone reference recomputation v0

## Scope and status

This package implements a standalone reference producer and an independently
written checker for `q3_input_recomputation_v0.1` (profile version `0.1.0`). It is
one implementation increment in the open Step 5C workstream tracked by
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879).

The profile was accepted for standalone implementation after review of its
explicit semantic choices. In particular, small-group coverage uses the
deduplicated union of affected eligible example IDs across declared dimensions.
This choice has its own profile identity; it does not silently change the
historical Q3 specification.

The implementation can validate a selected input bundle, produce a deterministic
Q3 result, and independently reconstruct that result. The accompanying fixtures
and regression executions are synthetic. They establish bounded implementation
behavior, not the correctness of real labels, dataset provenance, current-run
release applicability, complete Step 5C acceptance, or release authority.

The existing `q3_fairness_ok` gate is not connected to this producer. There is no
dispatcher, policy, required-gate, admission, workflow or promotion change. Before
release integration, update the canonical Q3 specification version and contract
documentation together, bind an accepted real input and runtime, and complete the
remaining Step 5C/5D requirements. Step 6 resource measurement and Step 7 promotion
remain separate work.

## Files and source boundary

| Purpose | Repository path |
| --- | --- |
| Accepted profile and decisions | `PULSE_safe_pack_v0/profiles/q3_reference_recomputation_v0.json` |
| Producer | `PULSE_safe_pack_v0/tools/build_q3_reference_summary.py` |
| Independent checker | `PULSE_safe_pack_v0/tools/check_q3_reference_summary.py` |
| Bundle, example, label and external expectation schemas | `schemas/metrics/q3_input_bundle_v0.schema.json` |
| Result schema | `schemas/metrics/q3_reference_summary_v0.schema.json` |
| Synthetic input builder and case expectations | `tests/fixtures/q3_reference_v0/` |
| Focused regression suite | `tests/test_q3_reference_recomputation.py` |

The profile selects these unchanged baseline resources from repository commit
`bb3c4791bc9399d0085d10d0d29d6d8a5e2cbfca`:

| Resource | Version | Git blob SHA-1 |
| --- | --- | --- |
| `metrics/specs/q1_groundedness_v0.yml` | `0.1.0` | `16fe7da3cb8fa304a3186955f76cea6c02cf09d3` |
| `metrics/specs/q3_fairness_v0.yml` | `0.1.1` | `4d1f6e1c4197e2465369585c78de4fd538957275` |
| `schemas/dataset_manifest.schema.json` | Existing manifest contract | `c36df74c6cb327d33b62e5d30d517b3af3b99a19` |

The profile records SHA-256 identities as well. Both tools verify the actual
resource bytes. Git object IDs and file SHA-256 values are different identifiers
and are not interchangeable.

## Input and external expectation

A bundle descriptor references exactly three local artifacts: the dataset
manifest, examples JSONL, and Q1 labels JSONL. Its closed schema binds their byte
lengths and SHA-256 values, the baseline specifications, the accepted profile,
both new schemas and the unchanged manifest schema. It also declares a dataset
ID, a reduction ID and an observation subject.

An example contains `example_id`, `prompt`, `response`, `context` and `metadata`.
The first four are strings; `metadata` is an object. Each label contains its
example ID, the complete examples-file SHA-256, the exact example-line SHA-256,
`q1_grounded_label`, `q1_eligible` and `q1_exclusion_reason`. IDs must be unique and
the example and label ID sets must match exactly. Joining is by ID and bound
bytes, never by line position.

The separately supplied `--expected` file is the caller's selected anchor. It
pins the bundle SHA-256, dataset/reduction/subject identity, profile and schema
digests, and the producer identity. Select it independently before inspecting
an untrusted report. Missing expectation fails closed; the tools do not generate
one from a report or silently trust the supplied bundle as its own authority.

Both tools additionally pin the exact input-schema bytes supported by this
implementation to SHA-256
`41e235d887822e9f7ced148bd06c7cee7cb02984ebb9a59e3f333f11497350e5`.
A newly selected external digest cannot extend or weaken that input contract.
An unsupported input schema fails with `FILE_BINDING_MISMATCH` before input
validation; the producer exits 2 without creating a report.

The producer source closure is exactly one file:
`PULSE_safe_pack_v0/tools/build_q3_reference_summary.py`. Its SHA-256, tool ID,
version and claimed Python version are selected by the expectation. The producer
checks its own identity. The checker hashes the supplied source snapshot without
importing or executing it. The checker reconstructs the expected producer
identity from the external anchor and records its own identity separately in its
verification receipt.

The byte-binding order is acyclic: examples, then labels bound to examples, then
manifest, bundle, external expectation, and report. An internally consistent
replacement cannot satisfy an unchanged original external expectation. If an
attacker can replace that expectation too, this offline mechanism does not
authenticate the original source or prove which code/runtime actually executed.

## Strict input processing

Both tools perform complete validation before scoring, including validation of
records that will later be excluded. A malformed input receives no metrics from
a partially processed subset.

- Files are bounded regular-file snapshots. Symlinks and unsafe relative paths
  are rejected; there is no network retrieval. A file changing during a read is
  rejected. The same immutable bytes supply hashes and semantic processing.
- JSON is strict UTF-8 without BOM, duplicate keys, nonfinite numbers or unpaired
  Unicode surrogates. JSONL requires nonempty LF-terminated lines and a final LF;
  blank lines and CRLF are rejected. Whole-file hashes include the final LF.
  Example-line hashes exclude only the line's terminating LF; no trimming or
  canonicalization occurs before hashing.
- The unchanged manifest schema is validated, including explicit date/date-time
  checks. This profile additionally requires nonempty, unique
  `slices.dimensions`, label source/version and a label-file hash. Manifest input
  and label hashes must match the artifacts, and `sampling.n` must equal the
  original example count before exclusions. Non-full sampling needs a seed and
  a documented selection protocol. The tools do not perform new sampling.
- Limits are 64 MiB per file, 1 MiB per JSONL line, 100,000 examples and 64 declared
  dimensions. Reports also respect the file limit. Oversized inputs/results are
  rejected rather than truncated or silently reduced.
- Output paths must name new files in existing directories. Existing files,
  symlinks and hardlink aliases cannot be overwritten. Repeated runs require
  different output paths or a fresh run directory.

The file traversal implementation requires POSIX directory-file-descriptor and
no-symlink facilities. It fails closed when those facilities are unavailable.
Python and the repository's existing `jsonschema` dependency are sufficient for
the tools; pytest is needed for the test suite. No new runtime dependency is
introduced by this package.

## Eligibility and exact group identity

This first narrow profile requires a present string `context`. Empty context is
Q1-ineligible and is retained as an excluded-record diagnostic. Missing or null
context invalidates the input; the tool does not repair legacy data. The label's
eligibility must equal `context != ""`, with `empty_context` as the only supported
exclusion reason. Other exclusion protocols need a separately defined adapter or
profile.

After Q1 eligibility filtering, `UNKNOWN` is ignored for Q3. `SUPPORTED` and
`ABSTAIN` count as passes; `UNSUPPORTED` counts as a failure. Thus:

```text
n_total = n_q1_ineligible + n_unknown_ignored + n_q3_eligible
n_q3_eligible = n_pass + n_fail
```

Overall counts include every Q3-eligible ID once, regardless of dimension count.
For each explicitly declared dimension, each eligible example belongs to one
marginal group. Intersectional groups and inferred demographic metadata are not
part of this profile.

An absent metadata key has typed identity `kind="missing", value=null`. A present
key must contain a nonempty string and has `kind="value"`. A literal
`"__MISSING__"` string is therefore an ordinary value, distinct from absence.
Nulls, empty strings, numbers, booleans, arrays and objects are invalid declared
group values. Unicode code points, case and whitespace are preserved exactly;
there is no trimming, normalization or coercion. Undeclared metadata does not
create new groups.

## Metric and coverage rules

| Rule | Accepted value |
| --- | --- |
| Minimum eligible total | 200 |
| Minimum group size for disparity | 30 |
| Maximum missing fraction | 0.05 per declared dimension |
| Maximum small-group fraction | 0.10 of the deduplicated union |
| Confidence level | 95%, fixed `z = 1.959963984540054` |
| Maximum conservative worst-group gap | 0.05 |

For eligible population `E`, let `S_d` contain IDs whose group in dimension `d`
has fewer than 30 eligible members. Small-group coverage uses
`U = union(S_d)` and passes exactly when `10 * len(U) <= len(E)`. Missing coverage
passes independently for every dimension when
`20 * missing_count[d] <= len(E)`. Integer comparisons avoid rounding at the
coverage thresholds.

For example, two disjoint small groups of 24 among 400 eligible examples produce
a union of 48 and fail 10% coverage, even though each dimension separately
excludes only 6%. If both dimensions affect the same 24 IDs, the union is 24 and
passes. Per-dimension fractions and their maximum remain diagnostics.

The union is a coverage diagnostic, not a population-pruning operation. Its IDs
remain in the overall denominator and in all otherwise eligible groups. There
is no iterative deletion. Small groups retain their counts and pass rates, with
null Wilson/gap fields; groups of at least 30 participate in disparity.

For `k` passes among `n` eligible examples, the implementations use this fixed
binary64 operation order:

```text
p = k / n
z2 = z * z
den = 1.0 + z2 / n
center = p + z2 / (2.0 * n)
margin = z * sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))
lower = max(0.0, (center - margin) / den)
upper = min(1.0, (center + margin) / den)
gap = max(0.0, overall_upper - group_lower)
```

The worst included-group gap must be at most 0.05 without rounding or epsilon.
Diagnostic analytical test vectors may tolerate binary64 endpoint rounding;
that tolerance never relaxes a pass/fail decision. Cross-language/libm bitwise
equivalence is not established by this package.

At zero eligible examples, the input may still be valid, but the metric fails
with `INSUFFICIENT_ELIGIBLE_TOTAL` and `NO_INCLUDED_GROUPS`. Undefined rates,
intervals, gaps and coverage fractions are null. Coverage flags are false;
undefined fractions do not generate invented exceeded-threshold reasons.

Q3 measures parity, not absolute quality. A sufficiently large population with
uniformly unsupported labels may pass this parity metric. That does not make
Q1 pass or authorize a release; the Q1 quality requirement remains separate.

## Report, checker and exit codes

Reports use UTF-8 JSON with `ensure_ascii=False`, sorted keys, two-space
indentation, finite values and one final LF. Dimensions, values, excluded IDs
and reason codes use the specified deterministic ordering. The result
schema is closed; invalid inputs have null metric aggregates and empty
dimension/exclusion lists.

The checker independently reads the original inputs, validates bindings,
reconstructs eligibility/groups/coverage/Wilson calculations and compares the
complete canonical report bytes. It imports neither the producer nor shared
metric logic and does not call the producer. A schema-valid report with altered
counts, identity, claim fields, floats, ordering or serialization is rejected.

| Exit | Producer | Checker |
| --- | --- | --- |
| `0` | Valid input, metric PASS | Valid input and exact reconstructed report match, including a genuine metric FAIL |
| `1` | Valid input, metric FAIL | Report is unreadable, malformed or different from reconstruction |
| `2` | Invalid input/expectation or operational failure | Invalid input/expectation or operational failure |

A producer invalid-input report is written when the producer can load its own
source and usable schema resources and can safely create a new output. An
unrecoverable source/resource-schema failure returns exit 2 with a short stderr
diagnostic and may leave no report. Output failures are reported without
overwriting an existing file.
The checker emits a separate JSON receipt to stdout and optionally to a new
`--receipt` file. Receipt success is a reconstruction result, not a second metric
verdict or an external validating authority.

If a receipt write or synchronization fails after creation, the checker attempts
to remove the file it created, guarded by its device/inode identity. Existing
destinations and observed replacements are preserved. Successful cleanup allows
retrying the same path. If the filesystem also prevents cleanup, the original
`RECEIPT_WRITE_FAILED` remains the reported failure; no successful receipt is
claimed.

Every result keeps `authority_effect="none"`, `production_gate_eligible=false`,
`current_run_evidence=false`, `source_authentication="not_established"`,
`label_correctness="not_verified"`,
`slice_metadata_correctness="not_verified"`, and `policy_activation=false`.

## Local synthetic example

From the repository root, use one Python environment for fixture creation and
producer execution. Choose a fresh directory for every run. The following
creates only synthetic input; it is not an acquisition procedure for real data.

```sh
python tests/fixtures/q3_reference_v0/fixture_builder.py \
  --case 1 --out /tmp/q3-example-001

python PULSE_safe_pack_v0/tools/build_q3_reference_summary.py \
  --bundle /tmp/q3-example-001/input_bundle.json \
  --expected /tmp/q3-example-001/expected_context.json \
  --out /tmp/q3-example-001/summary.json

python PULSE_safe_pack_v0/tools/check_q3_reference_summary.py \
  --bundle /tmp/q3-example-001/input_bundle.json \
  --expected /tmp/q3-example-001/expected_context.json \
  --summary /tmp/q3-example-001/summary.json \
  --receipt /tmp/q3-example-001/checker_receipt.json

python -m pytest -q tests/test_q3_reference_recomputation.py
```

Both tools accept `--resources-root` for the profile/schemas/baseline specs and
`--producer-source-root` for the selected source snapshot. Their ordinary
repository-relative defaults are sufficient for the example above. Real archived
inputs require a separately selected expectation; the synthetic fixture builder
is not a provenance authority for those inputs.

## Regression scope and integration boundary

The 42 reviewed design cases and their alternatives are materialized with actual
byte hashes before tool execution. Additional tests address exact numerical
boundaries, independent record ordering, deterministic serialization, malformed
JSON/JSONL, excluded-row validation, source/anchor substitution, report tampering
and safe file handling. Expected predicates are specified independently of the
two implementations. Tests refresh unrelated hashes for malformed semantic
inputs, while binding-attack tests keep their original anchor fixed.

The new test module is appended to `ci/pytest-tests.list`, which the existing
targeted-pytest step consumes. `ci/tools-tests.list`, its existing 167-test count
consumers and the Q2 regression programs are unchanged. This registration runs
synthetic regressions through the existing CI path; it does not dispatch any
workflow, connect Q3 to release admission or imply that remote CI has run.

Historical Q2 49/50 FAIL and release BLOCK remain unchanged. No prior Q2
acquisition, carrier verification, replay or field comparison is repeated here.
The 120-row Q1 reference labels and historical Q2 calls are not enlarged,
relabelled or supplied with invented slices to manufacture a Q3 dataset.
