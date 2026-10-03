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
q2_evaluation_subject_selection: reference_definition_fixed_in_section_6
q2_materialized_reference_subject_binding: not_established
q2_reference_runtime_qualified: false
q2_runtime_byte_preparation_implementation: implemented_in_section_7
q2_runtime_preparation_actual_run: not_recorded
q2_reference_dispatch_ready: false
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

At the #2892 contract-only inspection baseline, this selection was not
established. Section 6 now fixes one owner-operated reference definition and
its authored workload. Its concrete model/task choice is not evidence that the
application has been assembled or executed. Do not retroactively associate
unrelated model results with the selected reference or a different release.

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
#2879 remains open. Section 6 specifies the response-producing reference and
the intended component relationship. Materialized release-artifact binding,
qualified runtime bytes, actual acquisition and production admission remain
unestablished; the selection must not hide those distinct states.

## 6. Selected owner-operated reference: field extraction v0

Sections 6.1–6.7 preserve the #2893 selection milestone. Section 7 records
the subsequently implemented runtime-byte preparation phase; it does not
retroactively label the selection change as executed acquisition.

### 6.1 Decision and present change boundary

Select `pulsemech-q2-field-extractor-v0`: a minimal owner-operated reference
application, not a customer deployment, a new general assistant product, or a
claim about every PULSE release. Its only task is to return a named value from
one short, controlled English record. No external evaluator, institutional
approval, paid inference endpoint or model training is required by this choice.
Using upstream model/library artifacts and a GitHub-hosted machine still leaves
those supply-chain and platform dependencies inside the declared trust boundary.

The selected response-producing model is:

```text
repository: HuggingFaceTB/SmolLM2-135M-Instruct
revision: 12fd25f77366fa6b3b4b768ec3050bf629380bac
weights_file: model.safetensors
expected_weights_sha256:
  5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c
```

The revision and weights digest are selected from the upstream repository and
file metadata, not measured here from downloaded weights. The upstream model
card documents CPU use and the Apache-2.0 license. The choice is for a small,
locally executable reference, not because it has passed this workload. No model
responses were generated or inspected to choose the model, cases or settings.
The nominal 135M model size and approximately 269 MB weights file are upstream
metadata, not runtime memory measurements.

The two new data files are:

- [Concrete subject selection](../../PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json)
- [Complete authored workload and call inventory](../../PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json)

Their `record_type` fields name declarative records. They do not add a runtime
schema or make the existing reducer consume these records directly. In
particular, the request workload is not a Q2 answer-group input and contains
no model responses, predicted PASS records or expected answers.

This four-path change includes those two files, this readiness document and
`CHANGELOG.md`. No tool, workflow, schema, dependency installation, test-manifest
entry, production policy or existing source pin is changed by it. The existing
document index already points to this readiness document.

### 6.2 Exact reference definition and release relationship

The selection record carries a canonical `release_subject.definition` whose
SHA-256 is:

```text
688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5
```

This digest identifies the selected model/configuration/interface definition.
It is **not** the digest of an already assembled executable or a future release
package. `materialized_artifact_sha256` is null deliberately. No future artifact
hash, implementation commit, run ID, timestamp or execution result is invented.

The reference release object is the field-extractor application itself. Its
response-producing model/configuration is the one in that definition. Before
actual acquisition, assembly must bind the real worker source, installed
runtime closure, exact model/tokenizer files and relevant configuration into
a materialized subject inventory. The capture must use that exact inventory.
The candidate integration must separately carry and check the same subject
identity before any of this evidence can be used for a release decision.

The PULSE source commit identifies the evaluator/collection implementation;
it is not substituted for the model or the reference artifact identity. A
successful measurement on this application would not authorize an unrelated
PULSE package, a different model, a customer system or a different configuration.
This selection does not change the current Step 5C successful-subject graph or
make the current 19-gate reference runnable. Its integration remains a separate
source-bound task under 5.6, with no removal of required gates or evidence roles.

### 6.3 Fixed request and occurrence inventory

The workload contains exactly 50 distinct complete requests in ten controlled
families, five records per family: color, material, location, quantity, batch
code, weekday, fictional toy-robot name, shape, size and storage zone. All record
content was authored for this reference; it is not collected user traffic.
The intended evaluation population is this fixed finite set only.

Each group contains one application-level request with explicit system/user
messages, the selected model revision, generation configuration and context-reset
rule. Each request has three planned calls. All 150 call IDs and ordinals are
listed before execution, in group-major/repeat-minor order. No call ID represents
an already observed execution. Equal outputs, if any, cannot be copied between
slots or counted as independent calls without occurrence evidence.

```text
groups: 50
repeats_per_group: 3
planned_calls: 150
sampling_seed: 0
generation_seed_per_call: 1729
attempts_per_call: 1
retries: 0
batch_size: 1
workload_file_sha256:
  fa0412c6a702e220e5d0c8b09a5e854fe35ac89d4801977eeee0f2a6e5cae997
```

The dataset sampling seed does not claim that random case selection occurred:
selection is the complete fixed inventory. Greedy decoding does not use a
sampling distribution; the generation seed is fixed initialization metadata.
Do not silently switch to sampling, change seeds, add cases, resume a partial
run by splicing captures, or tune requests after observing their results.
A changed model, workload or behavior-affecting setting requires a new selected
revision and retains the earlier acquisition/result as a distinct record.

Both `request_hash_encoding` and `definition_hash_encoding` select the same
canonicalization profile: **RFC 8785 JSON Canonicalization Scheme (JCS)**.
A request hash covers only the corresponding `groups[i].request` object;
`definition_sha256` covers only `release_subject.definition`, not its sibling
hash/encoding fields. Each digest is lowercase SHA-256 of the UTF-8 JCS bytes,
without a BOM or final newline. See [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).

Apply JCS recursively, including its ECMAScript/IEEE-754 binary64 number
serialization and unsigned UTF-16 property-name ordering. Preserve array order
and string content without Unicode normalization. Reject duplicate property
names, invalid Unicode, NaN and infinities. A plain sorted compact JSON encoder
is not sufficient unless it implements these same rules.

For example, `1`, `1.0` and `1e0` serialize as `1`; `-0.0` serializes as `0`.
The stored penalty settings may retain their `1.0` spelling, but canonical
hash input contains `1`. This changes byte representation, not the selected
numeric generation values. Producer and separately implemented checker must
use this same profile and verify common canonical byte/hash test vectors.

File digests are different: `request_source.sha256` identifies the complete
committed `requests.json` bytes, including its final newline, without JCS
reserialization. Per-request hashes, all 150 occurrence references, the
selected-definition hash and the whole-workload file hash are updated together.
The selection pins that file digest independently of eventual answers.
This profile applies only to the selected-definition and per-request digests;
the existing Q2 answer-input/summary serialization, reducer/checker and
preserved carriers are unchanged.

This narrow exact-repeat/greedy profile measures agreement, not extraction
accuracy or robustness to sampling or paraphrases. Consistently wrong or
consistently unhelpful answers can agree. That limitation is retained rather
than replacing Q2 with a correctness test. The existing exact-match Q2 scoring,
minimum of 50 eligible groups and 0.90 Wilson lower-bound threshold are unchanged.
With only 50 planned groups, any ineligible group leaves insufficient evidence;
there is no post-result top-up. A correctly preserved FAIL is a valid measured
outcome, not permission to choose a new passing subset.

### 6.4 Runtime, generation and original-response extraction

The concrete runtime target is GitHub-hosted `ubuntu-24.04`, x86_64, CPython
3.11.16, PyTorch `2.8.0+cpu` and Transformers `4.57.6`. These are selected
installation targets, **not** an installed or qualified dependency closure.
The next implementation must materialize a complete wheel-only, hash-locked,
CPU-only closure and test it under the actual native target before dispatch.
No rolling `latest` model/runtime selection or fallback to another version is
permitted. The Ubuntu label itself is not an immutable OS image; record the
actual image/runtime identity and retain that platform limitation.

The worker target is CPU float32, eager attention, one intra-op and one inter-op
thread, evaluation/inference mode, deterministic algorithms, no quantization,
no compilation, no remote custom code and no pretrained pickle loading. It
loads only the eight selected snapshot files. ONNX variants, training state,
training arguments and upstream run logs are outside the selected load path.
The exact files must be checked before use; metadata-only inspection is not
claimed as downloaded-file verification.

Use the pinned tokenizer chat template with the explicit system/user messages
and `add_generation_prompt=true`. Start every generation with fresh request
state and no carried conversation or past-key-value cache. In-request caching
may be used; cross-request answer or state reuse is forbidden. All calls use
the same explicit greedy configuration in the workload: one beam, one returned
sequence, maximum 32 new tokens and the model's selected token IDs (BOS 1,
EOS/PAD 2). At this exact Instruct revision, both `config.json` and
`generation_config.json` declare BOS 1; `tokenizer_config.json` maps the BOS
`<|im_start|>` token to ID 1. Keep that selected value. The staged files must
be checked before execution; a different token configuration is not an
implicit override. Capture the effective configuration rather than inheriting
unseen behavioral overrides from a service or a changed generation configuration.

Every returned occurrence must retain the exact input IDs, new output token IDs
and full decoded continuation, with stop reason and its source/run/call binding.
Decode with the pinned tokenizer using `skip_special_tokens=true` and
`clean_up_tokenization_spaces=false`. The separate extraction checker must
recompute decoding from retained token IDs and verify the original text bytes.
No substring search, first-word extraction, JSON repair, answer replacement,
semantic judge or producer-supplied PASS is used.

For EOS-terminated generation, copy the **entire** decoded continuation into
an `answer` record without trimming or normalization. An empty continuation is
retained; the existing reducer classifies its empty normalized signature as
UNKNOWN. A completed generation at the token cap without EOS maps to typed
UNKNOWN under this predeclared extraction rule, with the original output kept.
A missing occurrence, exception, process interruption or generation timeout is
acquisition incompleteness instead, not a model-produced UNKNOWN response.

This interface exposes no native refusal channel. Refusal is not inferred from
keywords: a natural-language refusal remains generated answer text under this
profile. Reserved answer-tag collisions still fail the existing Q2 input
validation rather than being repaired or converted into passing evidence.

The selected caps are 15 seconds per generation, 1,200 seconds for the capture
phase, and 40 minutes for the separate manual workflow. They are finite
operating limits, not measured execution times or a promise that the runtime
fits them. Runtime qualification must check viability before the first scored
acquisition without inspecting this workload's model scores or adapting it to
pass. A cap failure retains the full 150-slot inventory and fails completeness.
These limits do not alter the existing PULSE CI or Step 5C workflow budgets.

### 6.5 Acquisition, preservation and independent checking boundary

Only the later owner-authorized manual workflow may perform an actual scored
capture. PR/push regression must not download model weights or run this workload
through a live model. Preparation may obtain fixed upstream artifacts; the
capture worker must execute from verified local bytes with networking disabled.
An environment variable alone is not proof of network isolation. No inference
service, API key, external reviewing person or organization is part of the path.

Before launch, fix the selection/workload hashes and actual source/runtime/model
inventory. Bind each observed call to its declared slot and the materialized
reference subject. After capture, preserve original token/text and occurrence
records, then derive groups and the existing dataset manifest. Fix the derived
input digests in a separate handoff before reduction. Missing original bytes or
unsupported execution origin prevents an accepted acquisition claim even if a
recomputed Q2 score is mathematically valid.

The separate capture checker may share pinned standard libraries/tokenization,
but must not import or call the acquisition producer to establish its verdict.
It independently checks request identity, inventory completeness, permitted
outcomes and extraction, then invokes the existing Q2 checker on exact bound
inputs. Sharing a tokenizer is an explicit common dependency, not an assertion
that the model executed or that the trust boundary is eliminated.

Runtime observation is established only within the reviewed worker/collector
and GitHub platform boundary. Retained hashes do not prove behavior against a
malicious platform or a party able to replace the trusted source and all fixed
expectations. This is not provider-independent cryptographic proof of inference.
A separate person does not fill those evidentiary gaps by approving the result.

The authored input corpus is suitable for the requested repository review.
Original generated responses and token records must be retained for checking,
with their artifact visibility/publication decision reviewed before the actual
capture dispatch. Do not print raw responses into general CI logs or publish
them automatically to the repository or Zenodo. Credentials, authorization
headers and raw environment remain forbidden. Step 5C packet privacy rules are
not expanded by selecting this separate input-acquisition path.

### 6.6 Complete next acquisition implementation inventory

The next bounded implementation is the one selected CPU acquisition/extraction
path below. These are **planned paths**, not existing implementations supplied
by the selection change. Inspect the then-current source and freeze the complete
result before owner upload. Any newly demonstrated dependency must be included
in that review before upload, not discovered as an ordinary follow-up fix during
CI. This inventory does not pre-authorize production Q2 admission.

| Change | Planned repository path | Responsibility |
| --- | --- | --- |
| A | `PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py` | One selected local model worker; original token/text response per bound call, no authority verdict. |
| A | `PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py` | Prelaunch verification, fixed workload execution, complete terminal inventory, original capture and derived groups/manifest/handoff. |
| A | `PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py` | Separately implemented original-capture, occurrence, request and extraction validation. |
| A | `PULSE_safe_pack_v0/requirements-q2-reference-v0.lock` | Complete native CPU wheel closure with exact hashes; separate from core and LlamaGuard dependencies. |
| A | `PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json` | Actual staged model/tokenizer-file identity map for the selected immutable snapshot; no invented byte digests. |
| A | `schemas/metrics/q2_reference_capture_v0.schema.json` | Closed, non-authorizing capture shape; actual versus synthetic test provenance kept distinct. |
| A | `.github/workflows/q2_reference_acquisition_v0.yml` | Owner-authorized manual reference-input job; no release/policy mutation and no live model calls on PR/push. |
| A | `tests/test_q2_reference_acquisition_v0.py` | Offline protocol/preflight/capture/checker regression program, including synthetic mutation cases and non-activation checks. |
| M | `scripts/build_normative_shadow_inventory_v0.py` | Exact-path classification of the new workflow and applicable tool surfaces without authority promotion. |
| M | `tests/test_build_normative_shadow_inventory_v0.py` | Corresponding exact inventory/category coverage. |
| M | `ci/tools-tests.list` | Register the new offline test program once; keep the existing sequence. |
| M | `tests/test_pulsemech_compute_bounded_execution_v0.py` | Reconcile the current-manifest count without changing historical counts or weakening checks. |
| M | `tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py` | Reconcile the current-manifest count without changing historical execution evidence. |
| M | `tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py` | Reconcile the current-manifest count while preserving exact registration and source-bound coverage. |
| M | `docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md` | Record the implemented boundary and actual validation state, not presumed model results. |
| M | `CHANGELOG.md` | Record the bounded acquisition implementation and unchanged authority scope. |

At this source, the planned one-program addition changes the current manifest
from 156 to 157; all three count-sensitive tests are included together. The
selection change itself leaves the 156-entry manifest untouched. Existing Q2
reduction/checking and Step 5C source pins remain unchanged in the planned
acquisition unit. Dispatcher/candidate admission and its dependent source closure
remain the later separate integration, not an omitted part of this inventory.

The next regression contract covers original-input replay; exact model/request
and source mismatches; missing/duplicate/cross-run occurrences; attempted retries;
exception/timeout versus completed-but-unextractable output; token/text and
extraction substitution; staged Instruct BOS/EOS/PAD token identity; RFC 8785
canonical byte/hash vectors for requests and definitions (including `1.0`
versus `1`, negative zero, Unicode ordering and malformed JSON); rehashed
tampering against separately fixed expectations; correct metric FAIL; and
retained rejection at production intake.
Do not count synthetic worker tests as actual model execution.

Current exit condition: the concrete subject definition and full request/call
inventory are reviewable and fixed. Actual model download, complete runtime
lock, native execution qualification, acquisition implementation, owner dispatch,
response preservation and release admission have **not** been completed by this
change. Do not add a new generic design cycle for choosing the model/task: that
choice is made here; the listed implementation is the next work.

### 6.7 Upstream basis for the selection

The following are external primary-source references used for component
selection, not external validating authorities:

- [Fixed SmolLM2 snapshot](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/12fd25f77366fa6b3b4b768ec3050bf629380bac)
- [Fixed weights identity](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/blob/12fd25f77366fa6b3b4b768ec3050bf629380bac/model.safetensors)
- [Model card and documented CPU use](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct)
- [Selected model configuration](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/blob/12fd25f77366fa6b3b4b768ec3050bf629380bac/config.json)
- [Selected generation configuration](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/blob/12fd25f77366fa6b3b4b768ec3050bf629380bac/generation_config.json)
- [Selected tokenizer configuration](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/blob/12fd25f77366fa6b3b4b768ec3050bf629380bac/tokenizer_config.json)
- [Transformers 4.57.6 distribution](https://pypi.org/project/transformers/4.57.6/)
- [PyTorch versioned CPU installations](https://pytorch.org/get-started/previous-versions/)
- [GitHub standard runner definitions](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)


## 7. Runtime-byte preparation implementation — no inference

### 7.1 Executable subset and unresolved byte inputs

The first executable subset of the sixteen-path inventory in 6.6 is now
implemented: `prepare-runtime` in
[the acquisition tool](../../PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py),
`verify-prepared-runtime` in
[the separate checker](../../PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py),
and [the owner-dispatched preparation workflow](../../.github/workflows/q2_reference_acquisition_v0.yml).
The capture subcommand deliberately does not exist in either tool. The selection,
model revision, fifty requests and 150 call slots remain byte-for-byte unchanged.

This phase is necessary to obtain the actual model and dependency bytes before
committing the planned complete lock and model-file map. It is a bounded
preparation step within 6.6, with the required repository-hygiene integration,
not a replacement acquisition design. This change contains thirteen repository
paths: the two tools, preparation workflow, one offline test program, the
inventory classifier and its test, the test manifest, the three current-count
regressions, this document, the changelog, and
[the repository-hygiene workflow](../../.github/workflows/repo_hygiene.yml).

The hygiene guard requires every pinned workflow to exist as a regular file at
its exact path before scanning version declarations; a missing, renamed or
symlinked file is rejected. Q2 must declare `3.11.16` exactly once on the shared
`3.11` line; every other workflow retains exact `environment.yml` version
equality. This does not change the selected runtime or preparation behavior.

Four originally planned additions remain absent from the repository: the model
worker, the adopted `requirements-q2-reference-v0.lock`, the adopted
`profiles/q2_reference_model_files_v0.json`, and the original-capture schema.
The preparation workflow produces candidate versions of the lock and model map
as artifacts only. They must be reviewed against actual downloaded bytes and
adopted before native qualification and the scored capture are implemented and
accepted. No placeholder hashes or fabricated successful runtime records stand
in for those files. The rest of 6.6 remains open, including capture, extraction,
artifact/run binding and the existing reducer/checker handoff.

### 7.2 What the preparation actually does

The workflow accepts an exact reviewed `main` SHA and an explicit preparation
confirmation, and requires an owner-originated first-attempt manual dispatch.
It checks dispatch/workflow/checkout identity and requires the selected Ubuntu
24.04 x86_64 / CPython 3.11.16 target before the producer contacts upstream
services. A mismatched source, platform or target version is rejected; no
floating version or alternative-model fallback is implemented.

The producer stages exactly the eight selected snapshot files. It preserves
fixed-revision upstream file metadata and compares actual file bytes with their
upstream Git-blob or LFS identity, including the previously selected weights
SHA-256. Model, generation and tokenizer BOS/EOS/PAD declarations are checked
from the staged files. It does not load the model, tokenizer classes or weights.

The selected CPU PyTorch wheel is taken only from the explicit CPU index and
checked against its index SHA-256. The other wheels are resolved from PyPI;
source distributions and build backends are excluded. Direct-URL dependency
requirements and unselected GPU/extra Torch distributions are rejected before
candidate acceptance. Each resolved wheel is independently matched to its
versioned upstream distribution metadata and actual SHA-256.

The root requirements are `torch==2.8.0+cpu`, `transformers==4.57.6`,
`rfc8785==0.1.4` and `jsonschema==4.25.1`. The last two are explicitly selected
support libraries for the already declared JCS profile and existing Q2 schema
validation; they do not alter the model/generation definition. Their transitive
closure is resolved into one-version/one-wheel, hash-pinned candidate entries.
The resolver tool itself is part of the runner/bootstrap trust boundary, not a
qualified model-runtime claim. The separate checker records its actual pip
version when performing offline resolution.

The producer and checker use standard-library code only. The checker does not
import or call the producer. It independently reconstructs the model-file map
and lock; checks all file hashes, exact source snapshots and caller-supplied
source/run/preparation expectations; rejects extra, missing, linked or replaced
files; and runs pip with `--dry-run --ignore-installed --no-index --require-hashes`
against only the staged wheel directory. This checks dependency closure and
native wheel selection without installing or importing the staged libraries.
The input is checked again after resolver inspection.

The workflow fixes `preparation.json`'s exact digest before this separate check.
That hash is a byte binding, not an independently authenticated inference proof.
The source and platform remain trusted as declared in 6.5. This phase does not
claim malicious-platform resistance or perform the later network-isolated
capture. Setup downloads are allowed; the later capture worker must still have
actual network isolation, not merely offline environment variables.

The existing JCS request/definition digests are preserved, not replaced with a
new serializer. This preparer accepts only the exact already reviewed selection
and workload bytes. Its own preparation files use a separately specified exact
UTF-8, sorted-key, two-space-indented JSON file representation with a final
newline. The full-file digest, not a claim of generic JCS serialization, binds
those preparation files.

### 7.3 Outputs, limits and next handoff

After producer and checker success, preserve exactly one Actions artifact named
`q2-runtime-preparation-<run-id>-1`. It contains the complete model files,
wheel directory, original upstream metadata, fixed source snapshots, the two
candidate identity/lock files, `preparation.json` and the separate check result.
The artifact ID, artifact digest and preparation digest are exposed in the job
summary. Only the exact verified directory and check result are uploaded; the
private resolver logs and raw environment are excluded. Hidden files are enabled
only to retain the verified `source/.github/workflows/` source snapshot.

The source code, controlled requests, model files and public distribution
metadata are the preparation publication scope. There are no generated model
responses in this phase. The response-retention/publication review required by
6.5 remains necessary before any later scored capture. Nothing is automatically
committed, tagged, deployed or sent to Zenodo.

The manual job retains the selected forty-minute bound. Preparation has an
1800-second application deadline, bounded HTTP reads, no transport retry loop,
a 64-wheel limit, per-file/metadata limits and a 1.5 GiB candidate-byte ceiling.
The offline resolver has a 180-second bound. Existing PULSE CI and Step 5C time
budgets are unchanged. Failure creates no accepted candidate or fallback PASS;
the workflow does not publish an incomplete output as a verified artifact.

Successful preparation establishes only a source/run-bound, byte-verified
candidate dependency/model inventory and offline dependency resolution. It does
not establish installation, native model compatibility, generation timing,
network-isolated inference, a materialized release subject or Q2 admission.
All of the following remain false:

```text
inference_executed
native_runtime_qualified
materialized_subject_bound
capture_dispatch_authorized
production_gate_eligible
```

After the source PR is reviewed, its CI passes and it is merged, the owner may
start this preparation-only workflow against that exact merged source. Review
the returned artifact before adopting its lock/map and continuing the remaining
worker/capture/extraction implementation. Do not substitute a PR CI success for
that manual materialization or for the later native qualification.

### 7.4 Regression and authority boundary

The new permanently registered
[offline protocol test](../../tests/test_q2_reference_acquisition_v0.py) uses
explicitly synthetic model/wheel bytes and synthetic source/run fixtures. It
tests the separate reconstruction, closed inventory, fixed source/run binding,
malformed input, rehashed substitutions, no-inference CLI boundary and workflow
scope. Synthetic expectations are confined to tests and are not selectable
through a production CLI option. PR/push tests never download real weights or
run a model. Test success is not evidence of a native preparation run.

The current manifest changes from 156 to 157 programs. All original entries
remain in their original order, and all three count-sensitive checks are updated
together without weakening registration or uniqueness. The new workflow and
tools are classified by exact path as non-authorizing preparation carriers.

No current production policy, unsupported set, existing Q2 reduction/checking
source, Step 5C source pin, README, DOI identity or publication record changes.
All nineteen required gates and thirteen unsupported-gate rejections remain.
#2879 stays open; this implementation is not Step 5C reference acceptance.
