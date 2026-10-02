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

The non-active reducer and separate recomputation checker are implemented
through #2890. This continuation was inspected at source
`6a1ede3a532a4a8e5d0d7f314fef3974c2682a0d`; that is an inspection baseline,
not the identity of a future acquisition or of the commit adding this section.

This section defines the next input-selection and acquisition contract. It
implements no collector, extraction adapter, launch guard or release recipe.
Its requirements must not be reported as already enforced by runtime code.

```text
q2_reference_reduction: implemented
q2_separate_recomputation: implemented
q2_input_acquisition_contract: defined_in_this_section
q2_evaluation_subject_selection: not_established
q2_admissible_release_input: not_established
q2_current_run_release_recipe: not_registered
q2_independent_candidate_admission: still_unsupported
unsupported_production_gate_count: 13
successful_step5c_reference_ready: false
```

### 5.1 Fix the evaluated subject before choosing a model or input

The owner-directed continuation is new Q2 input acquisition/selection, not
another search for a presumed lost original Q2 response export. No existing
response export is selected by this document.

Distinguish the release artifact, the response-producing system being evaluated,
and the evaluator. The PULSE repository commit identifies a repository source revision;
it does not by itself identify the system that produced the answers. Neither
an available hosted detector nor an arbitrary demonstration model becomes the
Q2 evaluation subject merely because it can be executed.

Before acquisition implementation or a run is authorized, record one concrete
selection containing all of the following. These field names describe the
required decision record; they are not a newly implemented schema or CLI.

| Field | Required content |
| --- | --- |
| `selection_id` | Stable identifier for this input selection and its revision. |
| `release_subject` | The release artifact/system identity and immutable version or digest to which Q2 evidence is intended to apply. |
| `evaluation_subject` | The actual response-producing system, selected model/component versions, relevant configuration and state-reset boundary. |
| `release_subject_relation` | Evidence of why this evaluated system/configuration is the subject of, or a relevant bound component of, that release. A matching display name is insufficient. |
| `task_scope` | The concrete task, intended evaluation population and answer representation. State the limits of the resulting consistency claim. |
| `request_source` | Exact source of the request set, selection procedure, permitted use and immutable request-set identity. |
| `request_protocol` | Complete ordered group/repetition inventory, request payloads, initial context and all behavior-affecting generation parameters. |
| `extraction_protocol` | Exact source/version of the response-to-typed-record mapping and its answer/refusal/unknown rules. |
| `execution_protocol` | Selected runtime/interface, source and dependency identities, seed behavior, finite call/time limits, attempt and retry rules. |
| `origin_and_preservation` | Evidence source and trust boundary for actual calls, original-byte retention, privacy/publication rules and the independent verification path. |

At the inspected source, this selection is not established. Do not insert a
model name, endpoint, dataset or task merely to fill the record. Missing
selection is a prerequisite blocker, not permission to run a convenient model
and retroactively associate its results with the release.

### 5.2 First grouping profile: exact request repeats

The design choice for the first acquisition is exact request repetition, a
subset of the existing Q2 specification's repeats/paraphrases scope. This
avoids introducing an unimplemented semantic-equivalence judge. It does not
establish robustness to paraphrases or to arbitrary context changes.

For each group, bind one complete application-level request and repeat it in
separately identified calls against the same selected evaluation subject and
fresh declared initial context. The model selection, system instructions,
conversation, tool definitions and generation parameters are part of this
request boundary. Transport identifiers may differ; they are not prompt text.

An unchanged visible question with a changed hidden conversation, model or
behavior-affecting configuration is not an exact repeat under this profile.
Record any unavailable platform state as a limitation, not as verified equality.
A seed declaration does not prove deterministic execution.

Freeze group membership, the request bytes, repetition count and ordered call
slots before the first call. Do not derive groups from observed answers or
copy one response into multiple slots. Do not split one repeated request into
multiple group IDs to inflate eligible coverage. Retain the existing bounds of
2 to 32 responses per group and at most 10,000 groups; the concrete finite workload
must be fixed by the selection rather than by these maximum bounds.

The metric remains unchanged: at least 50 eligible groups and a Wilson 95%
lower bound of at least 0.90. Plan the workload before observing results; do
not add groups, stop early or rerun until a passing score appears. Exact
agreement measures consistency under this protocol, not answer correctness.

### 5.3 Preserve actual occurrences, including unsuccessful ones

Every planned call slot requires its own occurrence identity and recorded
terminal outcome. Preserve the request/result association, actual subject and
runtime identifiers at their supported strength, and the available timing
basis. Equal response bytes do not establish two separate executions.

Set a finite retry rule before acquisition. Retain every attempted occurrence
and its outcome, and make any selected attempt mechanically traceable to that
rule. Do not silently replace failed or disagreeing answers with later ones.

A missing call, transport failure, cancellation or timeout is an acquisition
completeness problem. It is not a model-produced UNKNOWN answer. Keep the
original inventory intact and reject a claim of complete acquisition when an
obligation is unresolved. Preserve diagnostics without manufacturing responses.

A returned response whose answer cannot be extracted may map to UNKNOWN only
under the predeclared extraction rule. The reducer's existing eligibility and
UNKNOWN-group accounting remain unchanged; do not hide missing acquisition by
using its metric denominator rules.

### 5.4 Original responses and deterministic extraction

Bind every derived typed response to its exact original response bytes and
its planned call slot. The extraction implementation must operate on the
selected interface's actual response format, with exact field/byte locators
and explicitly specified error behavior. Do not invent a universal completion
parser before that interface and its response contract have been selected.

Produce the existing `typed_final_answer_or_refusal_v0` records: `answer` with
its extracted string, or typed `refusal`/`unknown` without an answer field.
Do not infer a refusal from a keyword, silently repair an invalid response,
accept an upstream PASS flag or substitute a model judge for extraction.
Leave normalization and scoring to the existing reducer and separate checker.

Keep original capture and derived groups distinct. Retain enough original
content for a separate implementation to verify extraction and grouping;
digests alone cannot reconstruct an unavailable response. This document does
not authorize publication of raw prompts or responses. Fix the permitted
controlled input set and its retention/publication boundary before collection.
Never include credentials, authorization headers or raw environment data.
Do not expand the Step 5C packet's existing privacy boundary.

### 5.5 Bind the input before reduction; do not invent future output hashes

Before calls, fix the selection, evaluated subject, evaluation source, request
inventory, extraction/generation settings and acquisition procedure. Original
response hashes are computed only after those responses actually exist.

After capture, preserve its original bytes and occurrence records. Derive the
Q2 group payload and existing dataset manifest without changing the originals.
The manifest must bind the exact group payload, its full group count and seed.
Fix the expected group/manifest digests in the separately preserved selection
or handoff record before invoking the reducer. Do not take those expectations
from the summary that is being verified.

Content hashes bind bytes; they do not authenticate a model, prove execution,
establish prelaunch ordering or create a release-subject relationship. Specify
how the selected acquisition path supports each such claim. A run ID or a
self-declared provenance field alone does not supply that evidence.

Keep acquisition identity and later reduction identity separate. Current-run
reduction of archived responses is not current-run model inference. Preserve
the original acquisition time and source; do not relabel a new response set
as a recovered historical export. The existing `archived_response_records`
label remains a declaration, not an authentication mechanism.

### 5.6 Completion and integration order

The next implementation may start only after the concrete selection in 5.1
is resolved and its complete changed-file/test inventory is fixed. It must
implement that one selected acquisition/extraction path, not a generic capture
framework or the other 12 unsupported gates.

Validate the original-to-derived path separately, including missing/duplicate
calls, changed requests, cross-subject/run substitution, forbidden retry
selection, altered extraction and consistently rehashed tampering. Then run
the existing Q2 reducer and separate recomputation checker on the exact bound
inputs. A correct FAIL summary must remain a FAIL; checker exit 0 is not metric
PASS, acquisition authentication or candidate admission.

Only then prepare the coordinated existing dispatcher/candidate-admission
integration, reconciling real input/result pointers, all dependent Step 5C
source closures, pins, fixtures and regressions together. Do not remove Q2
from either unsupported set through a partial or pin-only update.

Source review, applicable regressions, separate checking and exact source/run
binding remain required. Approval by an additional external person or
organization is not a prerequisite; it cannot replace missing origin or
execution evidence. Owner authorization to execute a selected acquisition is
not third-party validation.

No live acquisition, model call, production gate activation, successful
19-gate release or Step 5C acceptance is performed by this contract change.
#2879 remains open. The selected response-producing system and its actual
release relationship remain unresolved; this contract must not hide that fact.
