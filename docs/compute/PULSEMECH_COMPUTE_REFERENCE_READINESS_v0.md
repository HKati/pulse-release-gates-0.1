# Step 5C reference readiness and first Q2 reduction unit

## Status and inspected source

This document continues work order
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) after merged
[#2886](https://github.com/HKati/pulse-release-gates-0.1/pull/2886) and
[#2889](https://github.com/HKati/pulse-release-gates-0.1/pull/2889).

The inspected baseline is:

```text
source_commit: ce03813308aaef366100d9463791aac428433f95
source_tree: 19995f7266ad6793b964d7fbd41e580243f1abe5
tracked_file_entries: 1412
required_gate_count: 19
registered_recipe_count: 6
unsupported_required_gate_count: 13
```

These are baseline identities, not the identity of the later commit that adds
this document and the Q2 implementation. A running Dependabot branch is not the
source of this unit. The old correction is not reopened.

**This unit supplies non-active Q2 reference reduction and a separate Q2
recomputation checker. It does not register a Q2 release recipe, remove an
unsupported gate, or make a successful Step 5C reference dispatch ready.**

The baseline state is executable in the unchanged
[dispatcher](../../PULSE_safe_pack_v0/tools/evaluate_required_gate_v0.py) and
[candidate admission](../../PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py).
All 19 requirements and four `release_required` obligations remain in the
[production policy](../../pulse_gate_policy_v0.yml).

## 1. Why regression success is not reference readiness

The existing
[whole-runtime observation contract](PULSEMECH_COMPUTE_WHOLE_RUNTIME_OBSERVATION_CONTRACT_v0.md)
selects `pulse_ci_hosted_release_grade_v0`: seven successful jobs, one permitted
skipped job, and the declared downstream artifact roles. The acquisition path
requires the selected PULSE CI subject to complete successfully before the
Step 3F export proceeds.

The 13 unsupported requirements still reject at both evaluation and candidate
admission. Preserving hosted evidence before that rejection does not create the
later executions or artifacts required by the successful-reference profile.

Consequently, the following are different results:

```text
regression success
!= correct preservation of evidence followed by release BLOCK
!= successful selected reference acquisition
!= Step 5C I/E acceptance
!= Step 5D relational closure / Step 6 resource measurement / Step 7 promotion
```

Do not remove jobs, gates or evidence roles to turn the second result into the
third. Do not substitute the six-gate terminal TEST profile for production.

## 2. Updated gate-by-gate availability

The earlier pre-acquisition inventory identified assertion-only reference
summaries for these gates. This baseline now rejects those summaries explicitly.
The table below refines the next work; it does not reopen that admission choice.

The normative meanings below are from
[`pulse_gate_registry_v0.yml`](../../pulse_gate_registry_v0.yml).
`BASE_GATES` in [`run_all.py`](../../PULSE_safe_pack_v0/tools/run_all.py) contains
smoke defaults for demo/core, not the missing production computations. The
[old generic reference reducer](../../PULSE_safe_pack_v0/tools/build_required_gate_reference_summary_v0.py)
checks supplied assertion records; it does not recompute these properties.

| Required gate | Existing declared intent | Available basis / missing unit in the selected route | Disposition in this unit |
| --- | --- | --- | --- |
| `effect_present` | Pack control suite: expected control effect is present under the current run_all protocol. | Registry intent and smoke default exist. A source-bound control protocol, admissible observations and an effect calculation are not supplied by that default. Define the concrete effect comparison before implementing it. | Unsupported; unchanged. |
| `pass_controls_comm` | Pack control suite: comm-related control checks pass under the current run_all protocol. | Registry intent and smoke default exist. A concrete communication-control case set, expected outcomes and substantive reducer must be identified and bound; a PASS label is not that control protocol. | Unsupported; unchanged. |
| `psf_monotonicity_ok` | Monotonicity invariant holds for the test suite. | The selected release route does not supply a bound domain/order, transformations and evaluated suite from which this invariant is recomputed. Do not invent these from the gate name. | Unsupported; unchanged. |
| `psf_mono_shift_resilient` | Monotonicity invariant remains valid under shift/perturbation tests. | Requires the monotonicity protocol plus an explicit perturbation family and admissible perturbed observations. These are not established by the static reference assertions. | Unsupported; unchanged. |
| `psf_commutativity_ok` | Commutativity invariant holds for the test suite. | Requires identified operators, paired execution paths, comparison domain and input suite. Related algebra or matching booleans do not establish this gate's executed protocol. | Unsupported; unchanged. |
| `psf_comm_shift_resilient` | Commutativity invariant remains valid under shift/perturbation tests. | Requires the commutativity protocol and separately declared perturbation coverage. No replacement is admitted merely because a summary says that the checks passed. | Unsupported; unchanged. |
| `sanit_shift_resilient` | Sanitization remains effective under small perturbations. | The registered sanitization control/effectiveness recipe does not establish perturbed-case resilience. Bind the perturbations, expected sanitization effects and comparison before admitting this requirement. | Unsupported; unchanged. |
| `psf_action_monotonicity_ok` | Action-monotonicity invariant holds for the test suite. | An action domain/order, transformed executions and the evaluated suite must be identified. No such calculation is provided by the selected assertion-only reference route. | Unsupported; unchanged. |
| `psf_idempotence_ok` | Idempotence invariant holds for the test suite. | Requires identified repeated applications and a bound equivalence rule for their outputs. Neither a display flag nor the general mathematical identity supplies the execution evidence. | Unsupported; unchanged. |
| `psf_path_independence_ok` | Path-independence invariant holds for the test suite. | Requires predeclared alternative paths, common endpoint/comparison domain and admissible executions. Do not delete unobserved paths to obtain completeness. | Unsupported; unchanged. |
| `psf_pii_monotonicity_ok` | PII monotonicity constraint holds for the test suite. | Requires a declared PII representation/order and admissible transformations, without inferring sensitive attributes. The gate intent is not a complete replacement protocol. | Unsupported; unchanged. |
| `q2_consistency_ok` | Consistency passes under the defined evaluation protocol. | The existing Q2 specification defines agreement groups, normalization, exact comparison, Wilson lower-bound gating and minimum eligible-group evidence. This unit implements reduction and separate recomputation on a narrowly typed archived-record profile. Admissible release input selection and current-run admission remain unimplemented. | Non-active reducer/checker added; production gate remains unsupported. |
| `q3_fairness_ok` | Fairness criteria pass under the defined evaluation protocol. | The existing Q3 specification defines marginal declared slices, Q1 labels, coverage limits and conservative disparity. No corresponding selected release recipe exists. It needs its own input contract and substantive calculation; it is not folded into Q2. | Unsupported; unchanged. |

This is an availability conclusion about the inspected route, not a claim that
no related research, mathematics, historical example or diagnostic exists
elsewhere in the repository. The inspected Python occurrences of Q2/Q3 outside
the admission path are consumers of existing signals, not replacements for the
specified group/slice calculations. `docs/METHODS_Q1_Q2.md` describes a Jaccard
proxy; this unit does **not** substitute that proxy for the exact-match Q2
metric specification.

The six existing recipes are retained without new certification of their
input quality or of live-model behavior:

```text
pass_controls_refusal
refusal_delta_pass
pass_controls_sanit
sanitization_effective
q1_grounded_ok
q4_slo_ok
```

## 3. Selected first unit: Q2 archived-record reduction

Q2 has a concrete, existing
[metric specification](../../metrics/specs/q2_consistency_v0.yml).
It can be implemented without inventing an operator algebra or the meaning of
an underspecified control. Q3 has additional Q1-label and slice-coverage duties;
those remain a separate unit.

The Q2 spec is unchanged: `q2_consistency_v0`, version `0.1.0`, exact-match
comparison, alpha `0.05`, threshold `0.90`, and at least 50 eligible groups.
Both new tools require its existing SHA-256:

```text
bab4249805bf00099e95d5fc638d07a9537bd5b90195a54b3e4f88c192744ad4
```

Both tools also independently pin the exact bytes of the new input/summary
schemas and the existing dataset-manifest schema. A changed installed contract
cannot self-authorize by placing its new digest in the summary. A later contract
change requires a coordinated reviewed source-profile revision.

A spec edit cannot silently change the mathematics under this profile. The
normal-approximation constant is `1.959963984540054`, also used by the existing
Q1 reference reducer. The two Q2 implementations use algebraically separate
Wilson forms in a 60-digit Decimal context. The pass decision uses the computed
Decimal lower bound, not a rounded displayed score. A zero-success count has an
exact zero lower bound. JSON numeric outputs are binary64 display values.

### 3.1 New input profile, not a free-text semantic judge

The spec names final-answer/refusal extraction but does not define a universal
parser for arbitrary model completions. This unit therefore declares the narrow
profile `typed_final_answer_or_refusal_v0`. It reads supplied final-answer fields
and typed refusal/unknown records. It does not search raw completions, infer
refusals from words, group prompts after the fact, or call another model.

[Input schema](../../schemas/metrics/q2_consistency_input_v0.schema.json):

```json
{
  "schema_version": "q2_consistency_input_v0",
  "record_status": "synthetic_fixture",
  "extraction_profile": "typed_final_answer_or_refusal_v0",
  "grouping": {
    "method_id": "explicit-groups",
    "method_version": "v0",
    "seed": 0,
    "sampling_parameters": {"repeats": 2}
  },
  "groups": [
    {
      "group_id": "group-001",
      "responses": [
        {"response_id": "response-001", "kind": "answer", "answer": " Yes "},
        {"response_id": "response-002", "kind": "answer", "answer": "YES"}
      ]
    }
  ]
}
```

This one-group example is deliberately insufficient for PASS. Tests generate
larger synthetic inputs only in temporary directories. No synthetic PASS
fixture is installed as a production recipe input.

`record_status` is either `synthetic_fixture` or `archived_response_records`.
The second value is a retained input declaration, **not authentication that
archival or inference actually occurred**. `observed` and live-execution
promotions are not accepted by this profile.

Each group contains 2 to 32 response records. Group IDs are unique, and response
IDs are unique across the entire payload; repeated identifiers cannot inflate
coverage. IDs are bounded ASCII identifiers, not free-form prompt fields.
The three response forms are:

```text
kind=answer  + string answer
kind=refusal, with no answer field
kind=unknown, with no answer field
```

For answer records, the exact order is trim whitespace, casefold, then Unicode
NFKC. No second trimming/casefolding or internal-whitespace merging is added.
An empty normalized answer is UNKNOWN. Refusal and unknown are typed tags, not
answer text; normalized reserved tag spellings in an answer field are rejected
rather than being allowed to impersonate a control tag.

At least two non-UNKNOWN response signatures make a group eligible. All equal
eligible signatures mean CONSISTENT, otherwise INCONSISTENT. Fewer than two
means UNKNOWN. UNKNOWN groups are retained and counted, but excluded from the
rate denominator exactly as the Q2 spec requires. This unit adds no new
unknown-fraction threshold. Insufficient eligible evidence fails.

The Unicode database version is recorded and independently compared on replay.
Byte-identical reconstruction is claimed only for matching source/schema and
runtime-normalization versions, not across arbitrary Python/Unicode revisions.

### 3.2 Original-byte and manifest binding

The [existing dataset-manifest schema](../../schemas/dataset_manifest.schema.json)
is reused without modification. A valid manifest is mandatory. In this narrow
profile, `sampling.n` counts agreement groups and must equal the supplied group
count. The manifest seed must be a literal integer equal to the grouping seed.
The manifest's `hashes.input_sha256` must identify the exact original group
payload. Seed and grouping-method declarations do not prove that the claimed
generation procedure was executed.

Both tools require caller-supplied expected SHA-256 values for the original
groups and manifest. The checker also requires an expected summary digest.
Expected digests must come from the caller's selected input contract, not from
the summary being checked. Simply hashing arbitrary files immediately before
verification is not evidence of authentic selection or prelaunch fixation.

Inputs are read through bounded regular-file descriptors; symlink inputs,
size violations, changed files, duplicate JSON keys, invalid UTF-8/Unicode,
non-finite numbers and malformed schema instances are rejected. Limits are
8 MiB for group input, 512 KiB for manifest/schema/spec files, and 16 MiB for a
summary supplied to the checker. There are at most 10,000 groups and 8,192
characters per answer. These are operating limits of this profile, not a new
metric threshold.

The summary records the original input/manifest byte hashes and sizes, as well
as the selected metric spec and schema snapshots. This is content binding. It
is **not** an authenticated GitHub run, a proof of executed-source identity,
a signature, or proof that the prompts grouped together are semantically
equivalent. That upstream contract remains required before release integration.

### 3.3 Producer and separate checker

The [builder](../../PULSE_safe_pack_v0/tools/build_q2_reference_summary.py)
computes group labels, coverage counts, rate, Wilson lower limit and the
reference decision. It publishes canonical JSON without replacing an existing
output. The destination directory must already exist.

The [checker](../../PULSE_safe_pack_v0/tools/check_q2_reference_summary.py)
independently reads the bound inputs, validates their contracts, recomputes
signatures and counts, uses a separate Wilson formulation, and compares the
entire canonical summary bytes. It never imports or invokes the producer.
Updating a summary's own hash after changing its decision, counts, labels,
normalization version or authority fields cannot make it pass this comparison.

The [summary schema](../../schemas/metrics/q2_consistency_summary_v0.schema.json)
is only structural. Schema validity alone is not a correct Q2 calculation.

| Entrypoint | Exit/result meaning |
| --- | --- |
| Builder exit 0 | A valid passing reference summary was published. |
| Builder exit 1 | A valid failing reference summary was published, including insufficient evidence. |
| Builder exit 2 | Invalid/mismatched input or publication error; do not admit the invocation. An existing output is never replaced or silently erased. |
| Checker exit 0, `ok=true` | The summary matches the original inputs. Read `recomputed_pass` separately; a correct FAIL summary also verifies. |
| Checker exit 2 | The summary, inputs, expectations or installed metric contract do not match. |

All results retain `authority_effect=none` and `production_gate_eligible=false`.
No answer text is copied to the summary or error output. Opaque group identifiers
remain in the result; the caller remains responsible for appropriate input and
identifier privacy.

### 3.4 Invocation contract

These are offline artifact operations, not reference-workflow dispatches.
The expected values below are supplied by a previously fixed input contract.
They are not future run IDs or hashes invented by this document.

```sh
python -I -B PULSE_safe_pack_v0/tools/build_q2_reference_summary.py \
  --groups "$Q2_GROUPS" \
  --dataset-manifest "$Q2_MANIFEST" \
  --expected-groups-sha256 "$EXPECTED_Q2_GROUPS_SHA256" \
  --expected-manifest-sha256 "$EXPECTED_Q2_MANIFEST_SHA256" \
  --out "$Q2_SUMMARY"
```

```sh
python -I -B PULSE_safe_pack_v0/tools/check_q2_reference_summary.py \
  --groups "$Q2_GROUPS" \
  --dataset-manifest "$Q2_MANIFEST" \
  --summary "$Q2_SUMMARY" \
  --expected-groups-sha256 "$EXPECTED_Q2_GROUPS_SHA256" \
  --expected-manifest-sha256 "$EXPECTED_Q2_MANIFEST_SHA256" \
  --expected-summary-sha256 "$EXPECTED_Q2_SUMMARY_SHA256"
```

Do not put these under a production `q2_consistency_ok` recipe yet. In
particular, the checker's successful exit is not a substitute for the metric
pass value, admissible input provenance or the existing candidate-admission
requirements.

## 4. Complete unit inventory and verification obligations

This unit has nine repository paths:

| Change | Path | Responsibility |
| --- | --- | --- |
| A | `PULSE_safe_pack_v0/tools/build_q2_reference_summary.py` | Native archived-record reduction; no production recipe. |
| A | `PULSE_safe_pack_v0/tools/check_q2_reference_summary.py` | Separate original-input recomputation; no producer verdict import. |
| A | `schemas/metrics/q2_consistency_input_v0.schema.json` | Closed typed input profile. |
| A | `schemas/metrics/q2_consistency_summary_v0.schema.json` | Closed non-authorizing summary shape. |
| A | `tests/test_q2_consistency_reference_v0.py` | Positive, negative, binding, replay and non-activation regression coverage. |
| M | `ci/tools-tests.list` | Register the new program exactly once; retain all existing entries. |
| A | `docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md` | Gate availability, Q2 contract and finite follow-on boundary. |
| M | `docs/INDEX.md` | Discoverability of this implementation/readiness boundary. |
| M | `CHANGELOG.md` | Record the non-active metric unit without claiming gate promotion. |

Required regression coverage includes at least:

- correct PASS, metric FAIL and insufficient-evidence FAIL from original records;
- exact normalization order, typed refusal/unknown handling and group eligibility;
- duplicate or missing records, wrong manifest extent/seed/hash, malformed input;
- rehashed summary manipulation, source-spec drift and normalization-version drift;
- fresh-process byte-identical reconstruction and no output replacement;
- separate checker success on a correct FAIL, without production promotion;
- retention of all 13 unsupported entries in both existing admission paths.

The new program is registered alongside Q4; no workflow/job, permission or
budget changes are required. The declared Step 5C subject workflow, its
bindings, 62 role duties, historical carriers, six-gate terminal TEST profile,
production policy and candidate-admission code are unchanged. Existing
whole-runtime regressions remain registered and must run on the new PR head.

Source review, applicable regressions and the separate mechanical checking path
remain required. A separate external person, validator organization or
institutional approval is not an additional prerequisite.

## 5. Finite next boundary: admissible Q2 input and coordinated admission

Completing this unit resolves **the absence of a Q2 reference reducer and its
separate recomputation path**. It does not resolve input authenticity or release
admission. The readiness state after this unit is:

```text
q2_reference_reduction: implemented_in_this_change
q2_separate_recomputation: implemented_in_this_change
q2_admissible_release_input: not_established
q2_current_run_release_recipe: not_registered
q2_independent_candidate_admission: still_unsupported
unsupported_production_gate_count: 13
successful_step5c_reference_ready: false
```

Before a later Q2 integration unit, identify one admissible response-group
snapshot, its dataset manifest, grouping/extraction procedure and exact
source/run relationship. Archived evidence must remain labelled archived;
synthetic test data must not be relabelled as actual acquisition.

Then map the new reducer and checker into the existing dispatcher and separate
candidate-admission path, with the real input/result pointers, all dependent
Step 5C source closures, pins, fixtures and regressions reconciled together.
Freeze that **next** complete inventory before owner upload; this document does
not pre-authorize a partial pin-only change or silently remove Q2 from either
unsupported set.

If admissible Q2 inputs are not available, record that exact blocker. Do not
create a generic capture framework or implement the other 12 gates as an
unbounded prerequisite. #2879 remains open. README synchronization stays a
separate small documentation change, not part of metric implementation.
