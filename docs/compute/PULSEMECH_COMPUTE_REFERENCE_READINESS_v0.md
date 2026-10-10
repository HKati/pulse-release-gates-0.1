# Step 5C reference readiness and first Q2 reduction unit

## Current hosted Q2 integration status

The coordinated implementation continues from main
`288bb9a45764d2a30f72fdf4c417e9dd5b3087c5`, tree
`50017e5bde2b95f75536db7e478c6e41b89ec1c3`, with 1,452 baseline files.
The dedicated Q2 intake and independent candidate admission are implemented
inside the existing required-gate path. The current partition is six generic
recipes, one dedicated Q2 path and twelve unsupported requirements. The
[archived intake contract](PULSEMECH_Q2_ARCHIVED_INTAKE_CONTRACT_v0.md) defines
private IO, exact release-capsule comparison, current-run authorization,
unchanged replay and the closed public result.

The existing repository-hygiene Python guard also recognizes the exact
3.11.16 patch in the single setup step of the PULSE job. Its acquisition rule
and every other workflow/job declaration retain their previous requirements.
This necessary existing-workflow dependency and the additional exact-count
test consumer extend the reviewed 37-file inventory to 39 files; neither
adds a workflow job or step. The actual guard runs over all repository
workflows in the offline regressions.

The Q2 reference dispatch now requires the separately configured
`PULSE_Q2_OWNER_DISPATCH_TOKEN` repository secret. The acquirer verifies its
authenticated `HKati` user identity, while retaining the reference event's
original owner and exact request binding. The secret is restricted to the
existing acquisition step and one exact subject dispatch; installation-token
observation/provider transport remains separate. This corrects the mismatch
between an Actions installation-token dispatch and the Q2 intake's mandatory
owner identity. The intake's actor checks remain strict. See the
[credential contract](PULSEMECH_Q2_ARCHIVED_INTAKE_CONTRACT_v0.md#owner-bound-reference-dispatch-credential).
The secret and the actual release capsule are operational prerequisites;
their presence or a successful hosted run is not asserted by this change.

The original capture remains run `37600313529`, attempt `1`, executed source
`fb7b247e24f18c5314fd44f7711bd49e15020364`, artifact `11472726606`:
150 calls, 49 CONSISTENT, 0 INCONSISTENT, 1 UNKNOWN; 49 eligible groups against
50 required, hence correctly checked FAIL. Its identities, input bytes,
threshold and reports are unchanged. A real release capsule is not supplied.
The implementation and synthetic controls do not establish that missing
operational input, a production subject match, hosted execution or Step 5C
readiness. #2879 remains open.

The following earlier reduction-unit baseline is retained as historical context.
Its original commit and file count are not execution identities of this change.

## Historical reduction-unit status and inspected source

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

**The initial unit supplied non-active Q2 reduction and a separate checker.
The dedicated current intake is described above; neither unit makes a
successful Step 5C reference dispatch ready.**

The current state is executable in the coordinated
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

The twelve unsupported requirements still reject at evaluation and candidate
admission. Q2 separately rejects invalid intake or a valid negative metric. Preserving hosted evidence before that rejection does not create the
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
| `q2_consistency_ok` | Consistency passes under the defined evaluation protocol. | The existing Q2 specification defines agreement groups, normalization, exact comparison, Wilson lower-bound gating and minimum eligible-group evidence. The unchanged reducer/checker now have dedicated private intake, exact capsule comparison and independently reacquiring admission. The real capsule is still missing; the original metric remains FAIL. | Dedicated Q2 path; invalid inputs or valid FAIL reject. No generic recipe or successful release binding is claimed. |
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
not a replacement acquisition design. The preparation implementation merged in
#2894 contains thirteen repository paths: the two tools, preparation workflow, one offline test program, the
inventory classifier and its test, the test manifest, the three current-count
regressions, this document, the changelog, and
[the repository-hygiene workflow](../../.github/workflows/repo_hygiene.yml).

The hygiene guard requires every pinned workflow to exist as a regular file at
its exact path before scanning version declarations; a missing, renamed or
symlinked file is rejected. Q2 must declare `3.11.16` exactly once on the shared
`3.11` line; every other workflow retains exact `environment.yml` version
equality. This does not change the selected runtime or preparation behavior.

At the preparation-only merge (#2894), four planned additions were still absent:
the model worker, adopted lock, adopted model-file map and original-capture
schema. Section 8 now adopts the two input-pin files from the first actual
preparation, retaining their original candidate records separately. The model
worker and original-capture schema remain absent. The preparation workflow
continues to emit candidates, not automatic adoptions. Native qualification,
capture, extraction, artifact/run binding and the reducer/checker handoff remain
open; input adoption does not authorize a scored acquisition.

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

The permanently registered
[offline protocol test](../../tests/test_q2_reference_acquisition_v0.py) uses
explicitly synthetic model/wheel bytes and synthetic source/run fixtures for
its protocol tests. Section 8 adds separate regressions over the small original
preparation metadata records; it does not stage real model/wheel payloads in CI. It
tests the separate reconstruction, closed inventory, fixed source/run binding,
malformed input, rehashed substitutions, no-inference CLI boundary and workflow
scope. Synthetic expectations are confined to tests and are not selectable
through a production CLI option. PR/push tests never download real weights or
run a model. Test success is not evidence of a native preparation run.

At #2894, the manifest changed from 156 to 157 programs. All original entries
remain in their original order, and all three count-sensitive checks were updated
together without weakening registration or uniqueness. The new workflow and
tools are classified by exact path as non-authorizing preparation carriers.

No current production policy, unsupported set, existing Q2 reduction/checking
source, Step 5C source pin, README, DOI identity or publication record changes.
All nineteen required gates and thirteen unsupported-gate rejections remain.
#2879 stays open; this implementation is not Step 5C reference acceptance.

## 8. Recorded runtime-input adoption — no native qualification

### 8.1 Actual preparation and retained evidence

The first owner-dispatched preparation, run `37148637546`, attempt `1`, used
source commit `77fc5d51896568db50a2a87f650711a65db8fe8c` on `main`. The retained
context identifies Ubuntu 24.04 x86_64, CPython 3.11.16 and runner image
`20260927.320.1`. Its separate checker reports byte verification and offline
dependency resolution with pip `26.2.1`; it reports no installation or inference.

The original artifact is `q2-runtime-preparation-37148637546-1`,
ID `11282419957`, size `508460811` bytes, SHA-256:

```text
b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9
```

The original preparation record SHA-256 is:

```text
832b3626e846c96e5d65052ea54c966aabf0ed5f3976ecc5d3b4a3ced006ef4f
```

Four original small records are retained under
[`PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/`](../../PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/):
`preparation.json`, `q2-runtime-preparation-check.json`,
`q2_reference_model_files_v0.json` and `requirements-q2-reference-v0.lock`.

Original candidate records remain byte-for-byte unchanged. In particular, their
`adopted: false`, `staged_review_candidate` and negative qualification/authority
fields describe the preparation event and are not rewritten retroactively.
These are real run metadata, not synthetic model-output fixtures.

The four records are a **metadata excerpt**, not the complete runtime bundle.
The original artifact also contains all model files, wheel files, upstream
metadata and source snapshots; none of those payloads is copied into this
repository change. Preserve the original artifact separately. The excerpt
cannot replace a future complete-byte check or make unavailable payloads usable.

### 8.2 Exact repository input pins

The reviewed input baseline consists of:

- [`PULSE_safe_pack_v0/requirements-q2-reference-v0.lock`](../../PULSE_safe_pack_v0/requirements-q2-reference-v0.lock):
  30 exact wheel entries, one version and one SHA-256 per distribution, including
  the selected CPU Torch wheel. All requirement-entry bytes are unchanged from
  the recorded candidate; only the explanatory first comment is updated.
- [`PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json`](../../PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json):
  the same eight model/tokenizer files for `HuggingFaceTB/SmolLM2-135M-Instruct`,
  revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, with unchanged file sizes,
  SHA-256 values and upstream Git/LFS identities.

The repository model map is a derived `q2_reference_model_files_v0` record.
Relative to the original candidate, only `record_type`, `adopted` and the added
`adoption` binding change. `adopted: true` means **reviewed repository input pins
only**, represented by `adoption.scope: runtime_input_pins_only`; it is not a
native-runtime, inference, capture or release verdict. The map retains
`native_runtime_qualified: false` and `authority_effect: none`.

The closed `adoption` object binds the preparation repository/source/workflow,
run ID and attempt, target, original artifact ID/name/size/digest, each of the
four original records by path/size/SHA-256, and the repository lock by its exact
path/size/SHA-256. The source commit here identifies the **preparation**, not the
future consumer's source commit. A later worker/capture must bind its own source
separately and preserve this input provenance instead of rebinding the old run.

The preparation/checker code and its existing source list are unchanged.
The original candidate map is still the format those preparation commands
produce/check. The derived repository map is not passed in place of that
candidate. No existing runtime command consumes `adopted` as permission.

The four root versions remain `torch==2.8.0+cpu`, `transformers==4.57.6`,
`rfc8785==0.1.4` and `jsonschema==4.25.1`. No transitive package is re-resolved,
upgraded or replaced during adoption. These are the wheel identities captured
in the recorded preparation, not a claim that any future resolver selects them.

### 8.3 Review and regression scope

The original archive digest was recomputed and matched to the Actions artifact
digest. Its 78 entries comprise 76 manifest-listed payload files plus the
preparation and separate-check records. Every listed file size and SHA-256 was
checked against its actual archived bytes. The three separately supplied
inputs and separate checker record matched their archived copies.

The review also reconciled the eight model files with retained Git/LFS metadata,
the selected BOS/EOS/PAD IDs with the actual configuration/tokenizer records,
and all 30 wheel identities with their internal metadata and retained upstream
records. Target Python requirements and active base dependencies were inspected.
This is a byte/metadata review; it does not install or execute the libraries,
qualify model imports, measure generation timing or prove network isolation.

The existing registered Q2 offline program now locks the original record hashes
and the exact candidate-to-repository transformation. Mutations cover missing
records, changed/rehashed evidence, lock entries and hashes, model file identity,
source/run/artifact rebinding and attempted authority promotion. The original
protocol cases remain. The earlier test requiring both pin files to be absent
now requires the exact reviewed adoption while retaining its no-workflow-write
and no-permission-expansion assertions. No manifest entry or count changes.
Tests over metadata do not stand in for the complete archive-byte review.

The change touches nine repository paths: two input-pin additions, four
unaltered original metadata records, the existing Q2 test program, this document
and the changelog. No workflow, producer/checker source, inventory classifier,
test manifest, core dependency set, policy, registry, Step 5C pin or DOI changes.

### 8.4 Next boundary

This adoption supplies the concrete lock and model-file map listed in 6.6.
Next implement native runtime qualification and the selected worker/capture
path against these exact inputs. Before using any payload, recheck the complete
bundle and the adopted pins. The existing preparation and separate checker
remain the basis for that staged-byte verification; adoption is not a bypass.

The qualification/capture implementation must still establish its own source
identity, installed runtime, verified local model loading, actual network
isolation and finite operating bounds. Scored acquisition remains separately
owner-authorized and must retain all 150 predeclared slots and original outputs.
No scored calls or unrecorded viability trial are performed by this change.

The metadata pins do not provide malicious-platform resistance or replace the
separate checker. No additional validating person or organization is required.
All 19 required gates and all 13 unsupported-gate rejections remain unchanged.
No production Q2 admission or Step 5C/5D/6/7 acceptance is claimed. Keep #2879 open.

## 9. Native qualification implementation — one unscored diagnostic only

This is the bounded next implementation after #2895, based on main
`bd5b8a65743999c0fae360dd1dd8ec3056b6f1e5` (tree
`38cf717d954394c3e9d2547fa840fe7a2b024288`). Sections 6–8 retain the
selection, preparation and input-adoption milestone boundaries. This section
records the newer implementation boundary; it does not retroactively change
any original evidence or declare that native qualification has run.

**Implemented code is not an observed native qualification.** No selected
model or Q2 wheel was installed or executed while preparing this change. No
workflow was dispatched. Actual target execution and the original large
artifact's byte recheck remain necessary before a native-qualified claim.
The 150-call acquisition, extraction into scored groups, materialized release
subject, reducer handoff, production admission and Step 5C acceptance remain
outside this unit. Keep #2879 open.

### 9.1 Complete bounded change inventory

This unit has eleven repository paths; it adds five and replaces six:

| Change | Repository path | Responsibility |
| --- | --- | --- |
| A | `PULSE_safe_pack_v0/tools/qualify_q2_reference_runtime_v0.py` | Root-owned source/input staging, independent preflight, actual isolated installation, external sandbox/limit enforcement, one diagnostic and evidence preservation. |
| A | `PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py` | The selected local model load and exactly one authorized diagnostic generation; original token/text records, no score. |
| A | `PULSE_safe_pack_v0/tools/check_q2_reference_qualification_v0.py` | Separate input, installed-byte and diagnostic checker; never imports or invokes either producer or worker. |
| A | `PULSE_safe_pack_v0/profiles/q2_reference_diagnostic_v0.json` | One fixed, unscored, non-workload diagnostic with no expected answer or result-driven selection. |
| A | `schemas/metrics/q2_reference_qualification_v0.schema.json` | Closed qualification/failure report shape, not the planned 150-call capture schema. |
| M | `.github/workflows/q2_reference_acquisition_v0.yml` | Preserve preparation and add a separately confirmed native-qualification mode to the existing manual workflow. |
| M | `tests/test_q2_reference_acquisition_v0.py` | Extend the already registered offline program; preserve preparation and adoption coverage. |
| M | `scripts/build_normative_shadow_inventory_v0.py` | Classify the dual-mode workflow and three added tools as non-authorizing diagnostic surfaces. |
| M | `tests/test_build_normative_shadow_inventory_v0.py` | Exercise those exact-path classifications. |
| M | `docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md` | This implementation/evidence boundary. |
| M | `CHANGELOG.md` | Bounded implementation entry. |

The two preparation Python tools remain byte-for-byte unchanged. The separate
qualification supervisor/checker are necessary to leave their historical input
contract intact, not a second acquisition architecture. The existing test
manifest still contains exactly 157 programs, with the Q2 program registered
once. No manifest-count, core CI, hygiene, policy, registry or source-pin change
is needed. The selected subject, fifty requests, 150 obligations, adopted lock,
adopted model map and all four original records are unchanged.

### 9.2 Exact bytes and separate source identities

The original preparation remains source
`77fc5d51896568db50a2a87f650711a65db8fe8c`, run `37148637546`, attempt 1,
artifact `11282419957`. The complete 508,460,811-byte ZIP must match the
previously adopted SHA-256 before parsing; every one of its 78 file members is
then checked against the preserved preparation and checker records. Changed,
missing, extra, duplicate, linked, encrypted or unsafe members are rejected.
The original preparation checker is reused as an independent verifier of the
prepared bundle, with its Git lookup still fixed to the historical source.
An exact-path `safe.directory` exception allows a root verifier to read the
runner-owned checkout without changing repository or global Git configuration.

The new consumer uses its own reviewed commit, workflow/run identity and exact
source closure. Its scripts, schema, diagnostic and unchanged inputs are copied
from matching Git blobs into root-owned staging. The old preparation source is
never replaced by that consumer commit. Prelaunch records bind source, workload,
selection, diagnostic, installed environment and the original artifact before
any generation is authorized.

### 9.3 Actual offline installation and external isolation

The implementation requires the selected native Ubuntu 24.04/x86_64/CPython
3.11.16 target, a systemd host with unified cgroup v2, and a root supervisor.
There is no degraded path for a different Python, missing namespace support,
missing control group, unavailable filter or failed privilege drop.

Installation uses a fresh virtual environment, with no system site packages.
The selected thirty wheels are installed with `--no-index`, `--require-hashes`,
`--only-binary=:all:`, `--no-cache-dir` and the complete adopted lock. There is
no source build, network fallback, dependency omission or version substitution.
The standard-library `ensurepip` bootstrap is recorded separately; bootstrap
setuptools is removed, leaving pip alone before the adopted installation.
Bootstrap CPython, its standard library, pip and the operating system remain
explicit trusted platform inputs, not falsely labelled adopted wheel entries.

A separate checker re-reads the fixed wheels and compares their payloads to the
installed files, checks the complete pip report, original wheel digests and
closed environment inventory, and rejects unowned/importable additions or
rehashed RECORD-only substitutions. Generated console launchers are separately
listed and are not the worker invocation path. The environment is frozen under
root ownership before model use, then independently recomputed again after the
worker. Bytecode caches and system-site leakage are forbidden.

The original `bootstrap.json` remains a pre-installation inventory and is never
rewritten to match a later result. The installed-byte checker derives its exact
post-freeze expectation by applying `mode & ~0o022` to regular-file permission
fields only. Paths, bytes, sizes, hashes, symlink targets and every other mode
bit remain exact. A still-writable, over-restricted, deleted or substituted
bootstrap file is rejected; the prior and frozen inventories are not treated
as interchangeable. Duplicate or malformed bootstrap rows are rejected.

Checker failures retain the bounded, checker-defined error code in the phase
log. Arbitrary exception text, paths, credentials and generated text are not
printed. After a successfully observed startup barrier, each non-worker phase
retains its pre-EXEC sandbox record even if execution later fails, after the
mandatory cleanup attempt. Cleanup or publication failures cannot replace an
earlier execution error. A retained sandbox record is not evidence of phase
success, and no failed installation check can advance to model loading.

This corrects a reproduced bootstrap/freeze/checker inconsistency investigated
after run `37310024905`; that run's generic installcheck log does not establish
its first internal rejection code. Its failed qualification remains failed.
New-head hosted validation and a separately authorized native run are required.

The installer, installed-byte checker, worker and decoding checker use separate
systemd services. `PrivateNetwork=yes`, an AF_UNIX-only socket family filter,
a denied network-send/connect syscall set, empty capabilities and
`NoNewPrivileges` operate below Python. Before each target exec, the external
supervisor checks its actual MainPID, separate network namespace, dropped UID,
capabilities, service properties and kernel cgroup values. The child cannot
proceed past its barrier on a declaration of "offline" alone.

The host `/run` is hidden by a fresh service-local tmpfs requested as
`TemporaryFileSystem=/run:rw,nosuid,nodev,noexec,size=16M,mode=0755`.
`InaccessiblePaths=/tmp` remains; a whole-`/run` inaccessible mask is not used,
because it conflicts with systemd mount-propagation setup. The root-owned 0755
replacement is not a writable host directory for the unprivileged target.

Before every `EXEC`, the supervisor reads the process's actual mount namespace,
bounded host/child `/proc/*/mountinfo` records and mountpoint metadata through
`/proc/<pid>/root`. The `/run` mount must be a distinct tmpfs not present in the
host mount inventory, with `nosuid,nodev,noexec`, a verified 16 MiB size limit,
root ownership and mode 0755.
Both effective read-only and read-write mount states are accepted; neither
exposes the host's `/run`. An ordinary host bind or a missing observation fails.
The raw observations travel in `run_mount` inside each sandbox record and are
revalidated by the separate checker without importing the supervisor.

systemd's own per-unit `/run/systemd/incoming` propagation mount is permitted
only read-only, root-owned, mode 0600 and bound to this exact service's
propagation directory. It is not traversable by UID 65534. The optional
`/run/user` and `/run/credentials` inaccessible-directory masks must be
root-owned, read-only and mode 0000. Any other or stacked submount, readable
incoming directory, missing stat or namespace change rejects startup before
`EXEC`. This preserves systemd's setup path without opening host sockets or
accepting a self-declared isolation flag. No retry or relaxed fallback is added.

Run `37250080353`, attempt 1, retained installer status `226/NAMESPACE` before
its barrier. The exact failing mount syscall was not retained. This targeted
correction addresses the upstream-documented `/run` mask incompatibility;
offline regressions and configuration review do not establish that the repaired
Ubuntu native run has passed. Historical preparation/source/run/artifact
bindings and the existing failure-evidence retention remain unchanged.

The fixed additional caps are 4 GiB memory, no swap, 64 tasks and one CPU quota.
Each service has an external runtime cap; the entire qualification has a
1,200-second outer execution timeout. At that boundary GNU `timeout` sends
`SIGTERM`; `--kill-after=180s` gives the supervisor a separate, finite cleanup
grace before `SIGKILL`. This does not change the execution deadline or grant
another diagnostic. The nested failure path can spend 25 seconds closing
the active service (two 10-second control calls and a 5-second client reap)
and 30 seconds on two 15-second watchdog removals. The 180-second grace
therefore leaves 125 seconds for evidence inventory, fsync, publication and
staging removal. This is an operating allowance, not a guarantee against
unbounded kernel/filesystem stalls. A timeout remains a failed step even
when cleanup publishes its failure report; missing evidence never qualifies.
The outer command is force-stopped after at most 1,380 nominal seconds;
normal completion does not wait for the unused grace. The 40-minute job
limit and always-run failure-artifact upload remain unchanged.

The external supervisor gives the original response
exactly 15 seconds from the nonblocking write boundary of the single generation
command.
A separate systemd fail-stop timer is armed beforehand for 20 seconds: its
five-second arming/cleanup allowance is not additional generation time. Before
GO, the supervisor requires that the timer's conservative earliest expiry and
the existing worker/phase caps all leave the complete response window. It also
rechecks this at the write boundary; insufficient remaining time fails closed, without a
shortened or extended accepted generation interval. A response received after
15 seconds is rejected even while the fail-stop timer is still active. Timely
response receipt is followed only by bounded worker exit within the already
armed caps. Full-cgroup cleanup applies on success and failure. These are
operating caps, not measured throughput or a guarantee of fit.

Sandbox evidence and a one-call intent are flushed before arming. GO is a fixed
nonblocking pipe write; the supervisor samples its monotonic timestamp
immediately before that write, after pipe setup. It accepts only a complete
write. Post-write scheduling delay cannot move the start forward or create
extra generation time. Neither systemd control calls nor evidence
fsyncs intervene before response receipt. Observed timing and any received
original response are retained after worker cleanup, also on rejection; they
are not represented as a pre-execution observation. The worker, separate
checker, selected diagnostic, original runtime pins and preparation bindings
are unchanged by this timing correction.
Live evidence is staged under `/var/tmp`, outside the home paths hidden by
`ProtectHome=yes`; it is copied to the runner artifact directory only after
services stop. Do not weaken home protection to expose the checkout.

### 9.4 One fixed diagnostic and separate recomputation

The diagnostic is `diagnostic-0001`, using the fixed authored marker request in
the new profile, not a request selected from the fifty scored groups. It has
one attempt, no retries, no expected answer, no correctness test and no Q2
score. Failure does not select another prompt, extend the budget or replace a
response.

The worker verifies local model/configuration bytes before imports and load,
uses only the selected safetensors and fast tokenizer, and requires CPU
float32, eager attention, one intra-/inter-op thread, evaluation/inference mode
and deterministic algorithms. All selected greedy parameters and BOS 1/EOS 2/
PAD 2 remain explicit. Compilation is disabled and `use_model_defaults=False`
prevents the selected Transformers implementation from restoring model-specific
generation defaults. The effective configuration is retained before the parent
sends the one generation authorization.

Original input/new token IDs, complete decoded text, its UTF-8 base64 bytes,
stop reason and source/run/call identity are preserved. A separate UTF-8 text
file is also retained. No trimming, first-word extraction, refusal inference,
repair or answer grading occurs. A completed 32-token cap is a diagnostic
completion, not a timeout; incomplete generation is failure, not UNKNOWN.
This unit does not produce scored answer groups.

The checker re-tokenizes the fixed messages, recomputes the full decoding and
JCS definition binding using the pinned libraries, rechecks the installed
payload and compares the original records, effective configuration and external
occurrence/limit observations. It does not load a model or call generation.
Shared tokenizer/JCS libraries and the trusted collector/host remain explicit
common dependencies, not independent cryptographic proof of inference against
a malicious platform.

### 9.5 Dispatch and preservation boundary

The existing manual workflow defaults to `prepare-runtime`. Its original
confirmation remains required, with diagnostic consent false. Preparation still
has no model call. The other mode, `qualify-runtime`, requires preparation
confirmation false and explicit consent to one unscored diagnostic and retention
of its original token/text records. Both modes retain owner/main/attempt-one and
exact source/workflow checks. The expected source SHA must identify the reviewed
commit containing this implementation, not substitute that SHA for the original
preparation identity.

The native mode obtains only the exact adopted artifact before entering the
isolated phase. Unavailable/expired artifacts fail closed; no fresh unreviewed
replacement is selected. Ordinary PR/push tests cannot enter this workflow.
Raw responses stay in the explicitly authorized Actions artifact, not the
repository, Zenodo or general CI output. Bounded failure evidence is retained;
missing or failed checker evidence cannot produce a qualified report.

A successful future report is limited to `one_unscored_diagnostic`.
`authority_effect=none`, `production_gate_eligible=false`,
`capture_dispatch_authorized=false` and `scored_call_count=0` remain mandatory.
A report schema match alone is not a native observation or checker success.

### 9.6 Offline verification versus still-unobserved behavior

Offline regression covers the unchanged preparation/adoption path, exact source
and retained-input binding, synthetic full archive attacks, installed-payload
substitution, complete synthetic worker/checker protocol, original token/text
mutations, missing/cross-run records, external deadline framing and cleanup,
workflow/hygiene integration, schema and non-authority boundaries. The tests
execute the actual installer body twice in fresh local environments with one
tiny **synthetic** wheel: matching hashes install, mismatched hashes reject.
Harmless child processes exercise real deadline and process-group termination.
These are not installations of the adopted Q2 closure or model executions.

The local verification environment is not the selected native target and has no
usable systemd/network-namespace privilege. Kernel service observations in the
regression suite are explicitly synthetic; command construction and syntax are
not a substitute for observing enforcement on the target. The separate handoff
records exact executed commands, final counts and logs, and distinguishes them
from interrupted development runs.

Still unobserved in this change: rechecking the complete original runtime ZIP,
the thirty-wheel native installation, real model loading/generation, actual
hosted namespace/cgroup/seccomp/timer enforcement, real token-to-text replay,
and the changed workflow on its eventual reviewed GitHub head. No 150-call
capture viability, production admission or Step 5C acceptance is asserted.

## 10. Recorded successful native qualification — one unscored diagnostic

Sections 7–9 preserve their preparation, adoption and implementation-review
milestones. Their then-unobserved runtime state is not a denial of the later
execution recorded here. The selected model, request workload and historical
preparation records are not rewritten to label those earlier milestones as
executed capture.

### 10.1 Original run and distinct artifact identities

Owner-dispatched run `37362661448`, attempt `1`, workflow run number `6`,
completed successfully at source `60af89b6c90f767b283b80888f2b114fce94c4cf`.
Its workflow is `.github/workflows/q2_reference_acquisition_v0.yml` on `main`.
The original context records Ubuntu 24.04 x86_64, CPython 3.11.16, runner image
`20260927.320.1`, kernel `6.17.0-1022-azure` and glibc 2.39.

The native qualification archive is `q2-native-qualification-37362661448-1`,
artifact ID `11367651833`, size `1128989` bytes, with SHA-256:

```text
98fd7666abf2117864249b1f027381969b404e0a5eb4085044b9062337df116d
```

It contains 39 members: `qualification.json` plus its 38 evidence entries.
The original qualification report's SHA-256 is:

```text
2720a15ab727305e14048ff3000210efec4bd6550a58f196e168c55a3c40fe69
```

This is **not** the original runtime-input archive. That remains artifact
`11282419957`, from preparation run `37148637546`, attempt 1, source
`77fc5d51896568db50a2a87f650711a65db8fe8c`, with the size and digest in 8.1.
`artifact_sha256` inside the original native report identifies that runtime
input, not the containing qualification ZIP. Neither original source is
rebound to the later commit that preserves these records.

### 10.2 Repository projection and original-byte boundary

The [recorded-qualification index](../../PULSE_safe_pack_v0/examples/q2_native_qualification_v0/run_37362661448/recorded-qualification.json)
links the native run, its containing archive, the separate preparation archive
and exactly four original report snapshots:

- [qualification.json](../../PULSE_safe_pack_v0/examples/q2_native_qualification_v0/run_37362661448/qualification.json)
- [diagnostic-check.json](../../PULSE_safe_pack_v0/examples/q2_native_qualification_v0/run_37362661448/diagnostic-check.json)
- [input-check.json](../../PULSE_safe_pack_v0/examples/q2_native_qualification_v0/run_37362661448/input-check.json)
- [prelaunch.json](../../PULSE_safe_pack_v0/examples/q2_native_qualification_v0/run_37362661448/prelaunch.json)

These four files are byte-for-byte copies, including the original serialization.
They contain report metadata, identities and digests, not original generated
text or token arrays. The new index is a preservation record, not a fifth
original runtime output, a signed attestation or an active launch input.

The repository projection is deliberately **not the complete artifact**.
Original generated text and token records stay in the owner-authorized Actions
artifact and separately retained original archive, not the repository, general
CI log or Zenodo. A complete byte/extraction replay requires the original
qualification archive; a renewed installation/decoding verification additionally
requires the original model/wheel archive and the declared native dependencies.
Four metadata files cannot replace those missing bytes.

The GitHub metadata reported expiry `2026-11-04T19:22:10Z` for the qualification
artifact. Retain its exact original ZIP separately; a hosted URL is not permanent
preservation. No tests in this change download either archive or execute a model.

### 10.3 What was established, and what was not

The original terminal report records `status=qualified`,
`native_runtime_qualified=true`, and no error. The separate diagnostic check
records `original_decoding_verified=true` and
`single_unscored_diagnostic_verified=true`. The recorded chain passed input
checking, offline installation, installed-byte checking, the local model's
single diagnostic and separate token/text checking on the stated native target.

The claimed scope remains **one unscored diagnostic on that run and source**:

```text
recorded_native_run: 37362661448 / attempt 1
recorded_qualification_status: qualified
qualification_scope: one_unscored_diagnostic
scored_call_count: 0
capture_dispatch_authorized: false
production_gate_eligible: false
authority_effect: none
150_call_capture_completeness: not_established
capture_subject_materialization: not_established
current_run_q2_release_recipe: not_registered
step5c_acceptance: not_established
```

This is not answer-correctness grading, a consistency score, a capacity proof
for 150 calls or qualification of an arbitrary future worker revision. The
trusted collector, pinned dependencies and GitHub platform remain explicit;
metadata hashes do not prove inference against a malicious platform.
Earlier failed native runs retain their original failed outcomes.

### 10.4 Immediate implementation handoff

The next executable unit remains the selected acquisition/extraction path in
5.6 and 6.3–6.6, not a new model/task selection or another diagnostic feature.
The existing preparation and diagnostic modes stay operational. Implement the
complete 150-slot terminal inventory, request/original-token-text association,
deterministic extraction, separate capture checking and exact reducer/manifest
handoff together with their source-closure, schema and regression dependencies.
Do not promote missing calls to UNKNOWN or substitute repeated copies for
separate occurrences. Fix the complete changed-file inventory before upload.

The capture must bind its own actual worker/runtime/model inventory before calls.
Do not use this diagnostic run ID as the identity of a future capture, reuse its
single response as scored input, or treat this preservation index as dispatch
authorization. Actual capture still requires a separate owner-authorized run
and its original-response retention decision after implementation review.
Production Q2 admission remains the later coordinated integration under 5.6.

This eight-path preservation unit changes no executable tool, workflow,
model selection, dependency lock, existing source pin, policy or gate. It adds
five metadata files (the index and four originals), extends the already
registered startup regression module, and updates this document and changelog.
The metadata regressions check pinned bytes, digest links, separate historical
identities, narrow scope and a closed no-raw-response projection. They are not a
new native run or a full native-artifact replay. #2879 remains open.

## 11. Selected 150-slot capture implementation — execution remains separate

This section records the implementation following the owner-reviewed inventory
in #2879, comment `6023217407`, prepared from main
`928a8a2a2dfdc4d440f7294ba589dedaf01239db`. It does not change the original
selection, preparation, qualification or preservation identities in sections
6–10. No 150-call native acquisition is claimed by this implementation change.

### 11.1 Separate entrypoints and owner consent

The existing workflow gains one additional `capture-reference` mode. Its
`confirm_capture_retention` input defaults to false and explicitly covers the
fixed 150 planned calls and retention of original token/text records in the
Actions artifact. Only the confirmation belonging to the selected mode may be
true. The preparation and one-diagnostic defaults remain unchanged.

The capture CLI rejects invalid source identities and dispatch context before
importing its local native helper. The owner, repository, main ref, first attempt,
workflow path and exact source/workflow SHA checks remain mandatory. Native
installation and observation still require Ubuntu 24.04/x86_64/CPython 3.11.16,
root supervision and the existing systemd/cgroup isolation. No synthetic-profile
CLI, runtime-cap override, retry, resume, alternate model or PR/push inference
path is introduced. Implementation tests do not dispatch this workflow.

### 11.2 Materialized subject and independent source closure

Capture rechecks the complete original runtime archive and its adopted bytes,
uses the existing fresh-venv hash-required offline installer, retains the
original bootstrap inventory and applies the unchanged root-freeze operation.
The separate installed-byte checker must succeed before model loading.

A capture-specific 23-file source closure binds the acquisition tool, worker,
capture checker, native supervisor, unchanged independent native checker,
workflow, both relevant native/capture schemas, fixed diagnostic, selected
inputs, four historical preparation records, existing Q2 reducer and summary
checker, Q2 spec/input/summary schemas and dataset-manifest schema. Current
source snapshots must equal the reviewed commit's Git blobs. This closure does
not enlarge or rename the old diagnostic's 15-file historical record.

`capture-prelaunch.json` retains the full 150-slot inventory and actual source,
installation and platform bindings. The loaded worker reports its effective
configuration without generating an answer. The supervisor then materializes
`capture-subject.json`, binding the selected definition, actual worker bytes,
eight model/tokenizer files, installed inventory, interpreter/platform and
loaded configuration. The worker acknowledges that exact subject digest before
any capture GO. The old selection's null materialized-artifact field is not
rewritten; this is a new capture-subject record, not a retrofit of old evidence.

### 11.3 One loaded model, 150 separately authorized occurrences

The capture worker has a distinct protocol:

```text
model-ready → materialized-subject BIND → subject acknowledgement
→ (PREPARE slot → slot-ready → GENERATE slot → original response) × 150
→ FINISH → session-end → EOF and successful exit
```

Each planned slot is accepted exactly once and in its fixed order. Every
iteration creates fresh request tensors, attention mask and generation config;
no conversation, past-key-value cache or generated result is reused across
calls. The immutable loaded model/tokenizer may remain in the one session.
The seed is reset to 1729 for each actual `model.generate` invocation.

The supervisor writes a root-owned intent before GO, verifies slot readiness
and binds the nonblocking authorization write and response receipt to its own
monotonic clock. Each generation retains the full 15-second response window.
Its independently armed 20-second fail-stop timer is not extra response time.
Both timer units must be observed inactive before the next authorization.
Insufficient remaining phase/worker time, stale timers and unsolicited output
reject rather than shortening the accepted interval.

The diagnostic worker's 180-second limit is unchanged. Only the explicitly
selected capture worker receives a bounded lifetime derived from the remaining
1200-second phase budget. The existing outer TERM deadline and separate
180-second cleanup grace remain; no grace is borrowed for another generation.
These are enforcement and acceptance limits, not a throughput guarantee or a
claim about unbounded kernel stalls. The supervisor checks namespace, syscall,
privilege, mount and cgroup protections before EXEC and observes cleanup after
the session. Native capture viability remains untested by offline doubles.

### 11.4 Original evidence and failure preservation

Every completed slot retains its readiness, intent, original response JSON and
complete UTF-8 continuation. Original input/new token IDs, effective configuration,
request/slot identity, subject/run/source bindings, stop reason and external
receipt times remain associated with that occurrence. Equal text is not copied
to manufacture repeated executions.

The terminal inventory always retains all 150 planned slots once fixed-input
preflight has succeeded, including slots not attempted after termination,
preparation failures and uncertain/failed attempts. Received records and bounded
partial frames remain failure evidence where available. They are never filled
in as successful responses or converted to model-produced UNKNOWN answers.
The first error survives later cleanup/publication errors; no following GO is
issued after rejection. Incomplete acquisition does not derive answer groups.

`capture.json` is published after the evidence copies and staging removal, not
before them. Missing publication is not success. The report separately records
received extent, independent original-capture verification and the metric
outcome. Phase logs and available installer/checker outputs are retained on
failure without making them successful phase results.

### 11.5 Separate reconstruction and existing Q2 reduction

`check_q2_reference_capture_v0.py verify-capture` never imports or invokes the
acquisition producer, worker or supervisor. It may use the unchanged independent
native checker's installed-byte and mount-validation functions. It separately
checks the 23-file source inventory, external prelaunch/subject/transcript
expectations, subject assembly, complete call-file extent, per-slot authorizations,
timers, cleanup and session termination. It retokenizes the exact requests and
recomputes full decoding with the pinned local tokenizer, without generating.
Installed runtime bytes are checked again at the end of verification.

The extractor preserves complete EOS-terminated text without trimming. Empty
EOS text remains an empty answer; a completed 32-token result without EOS becomes
typed UNKNOWN. Missing execution is incompleteness, never UNKNOWN. No keyword
refusal inference, answer repair or semantic judge is added.

Producer-derived `groups.json` and `dataset-manifest.json` must equal the separate
checker's reconstruction byte-for-byte. Their hashes are fixed in `handoff.json`
before the unchanged Q2 reducer executes. A separate isolated reduction phase
runs the existing builder and original-input summary checker, with explicit
handling of builder exit 1. A valid failing metric remains FAIL. The independent
capture checker succeeding does not mean metric PASS or production admission.

| Terminal report status | Meaning | Capture command exit |
| --- | --- | --- |
| `captured_metric_pass` | Complete verified original capture, verified extraction and correctly reconstructed passing Q2 summary. | 0 |
| `captured_metric_fail` | Complete verified original capture and extraction, with a correctly reconstructed failing Q2 summary, including insufficient eligible evidence. | 1 |
| `failed` | Setup, execution, evidence, checking or publication did not complete successfully. Retained diagnostics do not authorize acceptance. | 1 |

Every result keeps `authority_effect=none` and `production_gate_eligible=false`.
No production recipe is registered, and Q2 remains in both unsupported admission
sets. Production integration and Step 5C dependency reconciliation remain the
later coordinated task in 5.6.

### 11.6 Validation and remaining native boundary

The changed acquisition/startup/inventory test modules are already registered;
neither CI manifest is changed. The complete modules, the existing Q2 consistency
module and the two existing production-rejection modules are run directly with
pytest, not through an AST-selected test harness. The accompanying implementation
review bundle records exact commands, unique case identifiers, interpreter,
exit status, durations and the final source-file digests.

Coverage includes the full 150-call synthetic worker, separately reconstructed
original file I/O, two fresh-process reconstructions, actual existing reducer
and summary-checker CLIs, real harmless multi-record subprocess framing/EOF/reap,
existing real tiny-wheel offline installation/freeze checks, explicit synthetic
systemd observations, timer and deadline failures, every phase's early termination,
complete failed-slot retention, consent guards and continued production rejection.
The preparation-function byte snapshots and historical records remain checked.

Local execution uses CPython 3.13.5 in a reconstructed, byte-verified working
source set. A local Git index supports existing path-membership assertions; it
is not an upstream checkout history. No actual model package is imported or
executed by these regressions. Tokenizer/framework/platform/adoption stand-ins
in the new integration tests are explicitly synthetic. The test JCS stand-in
covers only the selected integral-number fixture subset; native worker/checker
execution requires the actual pinned `rfc8785` implementation and its vectors.

Full repository CI, the hosted 3.11.16 test execution and the native 150-call
workload are not local test claims. No quantum/physical validation, malicious-host
resistance, answer correctness, future capture result or Step 5C acceptance is
established. The prior successful one-diagnostic native run remains a distinct
historical prerequisite, not a certificate of this new revision.

Original generated records remain in the separately consented Actions artifact,
not general CI logs, repository fixtures or Zenodo. Artifact retention is finite;
full replay requires the exact original capture/runtime archives and declared
dependencies. Owner dispatch follows review of the final implementation revision
and its new source SHA; no old diagnostic response is reused as scored input.

Keep #2879 open.


## 12. Recorded native capture and verified Q2 FAIL

This is the capture-preservation milestone under
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879), following
its [reviewed nine-path inventory](https://github.com/HKati/pulse-release-gates-0.1/issues/2879#issuecomment-6037092246).
Sections 6 through 11 retain their historical selection, preparation,
qualification and implementation meanings. This section records the actual
capture result; it neither rewrites those milestones nor starts another capture.

### 12.1 Actual run and distinct original archives

The owner-dispatched `capture-reference` execution was
[run 37600313529](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/37600313529),
attempt 1, workflow run number 7, job `112722808444`, on `main` at:

```text
executed_source_commit: fb7b247e24f18c5314fd44f7711bd49e15020364
workflow: .github/workflows/q2_reference_acquisition_v0.yml
platform_reported_conclusion: failure
capture_status: captured_metric_fail
error_code: null
```

The containing capture ZIP has this separately checked identity:

```text
artifact_name: q2-reference-capture-37600313529-1
artifact_id: 11472726606
size_bytes: 1809263
zip_member_count: 658
inventoried_evidence_files: 657
sha256: 88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6
```

The original preparation remains run `37148637546` / attempt 1, source
`77fc5d51896568db50a2a87f650711a65db8fe8c`, artifact `11282419957`, with the
508,460,811-byte runtime-input ZIP and digest recorded in 8.1. The single
unscored qualification remains run `37362661448` / attempt 1, source
`60af89b6c90f767b283b80888f2b114fce94c4cf`, artifact `11367651833`, as recorded
in section 10. These are three different executions and three different archives.
None of their executed-source identities is rebound to the later preservation
or integration commit. The capture ZIP digest is not the `capture.json` digest.

### 12.2 Closed repository projection

The [recorded-capture index](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/recorded-capture.json)
binds the run, separate archive identities and exactly five original reports:

- [capture.json](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/capture.json)
- [capture-check.json](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/capture-check.json)
- [reduction.json](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/reduction.json)
- [summary.json](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/summary.json)
- [summary-check.json](../../PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/summary-check.json)

These five files retain the exact original bytes, including serialization,
negative results and non-authorizing fields. The index is a new metadata
preservation record, not a sixth original execution report, signed attestation,
new validator, dispatch consent or active policy input. Its snapshot sizes and
hashes are checked against separately pinned expectations in the registered
startup regression module, not accepted from a self-rehashed index.

`capture.json` contains the original 657-entry evidence inventory. Its `path`
values identify members of the complete capture archive, not files promised
inside the repository projection. The index's
`original_artifact_dependencies_not_copied` entries identify the original
prelaunch, subject, transcript, groups, manifest and handoff records needed for
replay. Naming and hashing these dependencies does not reproduce their bytes.
The repository directory contains only the five reports and the index.

### 12.3 Complete acquisition and negative metric are separate

The retained native capture checker records 150 verified calls, complete
original capture, and successful decoding and extraction. The terminal capture
report records 150 planned and 150 received complete slots. The reduction
retains these results:

```text
consistent_groups: 49
inconsistent_groups: 0
unknown_groups: 1
eligible_groups: 49
minimum_eligible_groups: 50
eligible_responses: 147
total_responses: 150
consistency_rate: 1.0
wilson_lower_bound: 0.9273021807795037
threshold: 0.90
insufficient_evidence: true
metric_pass: false
builder_exit_code: 1
summary_checker_exit_code: 0
summary_checker_ok: true
summary_checker_recomputed_pass: false
```

The Wilson threshold is met, but the eligible-group minimum is not. All three
`q2fx-044` occurrences reached the fixed 32-token limit without EOS, producing
typed UNKNOWN under the predeclared extraction rule. They are completed but
ineligible responses, not missing calls or timeouts. The other 49 groups are
CONSISTENT. The failure conclusion is preserved; no extra calls, replacement,
splicing, token-budget change, new cutoff or retrospective rescoring occurs.

The original summary's `inference_executed=false` describes the deterministic
reduction, not a denial of the separately recorded capture. Its
`grouping_authentication=not_established` is also unchanged: a reduction summary
alone does not authenticate upstream execution. The separate capture evidence
keeps its own identity and declared trust boundary. A correct FAIL can pass
summary verification without becoming metric PASS or candidate admission.

Post-hoc inspection of task-following/content differences remains a separate
analysis, not a preregistered answer-correctness score, a new Q2 comparator or
permission to change the workload after observing responses. Q2 agreement does
not establish answer correctness.

### 12.4 Privacy, retention and replay limits

Raw generated text, token arrays, answer-containing groups, full transcript and
the complete original archive remain outside the repository, issue and general
CI logs. The metadata projection is not a full replay package. Retain the exact
capture ZIP separately; GitHub reported expiry `2026-11-06T09:28:24Z`. An artifact
URL and a later metadata index do not attest durable owner-held retention.
That owner-held copy remains unverified by this record.

Full original-to-derived replay needs the exact capture archive. Renewed native
installation/installed-byte and tokenizer verification additionally need the
separate original runtime-input archive and the declared native environment and
dependencies. Historical reports and metadata checks do not replace these bytes
or constitute another kernel-isolation observation. The reviewed collector,
pinned dependencies and GitHub host remain inside the trust boundary; checksums
do not prove inference against a malicious host.

### 12.5 Verification and remaining handoff

This nine-path unit adds the five original reports and the new index, extends
`tests/test_q2_native_startup_diagnostics_v0.py`, and updates this readiness
record and the changelog. The already registered test module checks original
byte identity, report/index links, distinct historical roles, unchanged FAIL,
closed metadata scope and rejection of missing, extra, linked, changed or
coherently rehashed substitutions and false authority. The complete module,
including its earlier startup/qualification/capture-helper regressions, is run
locally. Exact commands, executed test IDs, results, interpreter and limits
belong to the delivery verification bundle. Metadata tests are not new native
inference, a tokenizer replay or an independent repeat of the original run.

No runtime tool, schema, workflow, test-manifest entry, policy, registry,
unsupported-gate set, existing source pin or DOI value is changed. The original
summary and capture schema meanings remain intact. Final-head repository CI and
Codex review are separate from the delivered offline tests; repository merge
and owner-held archival retention are not established merely by preparing files.

After preservation is completed, continue the coordinated dispatcher and
candidate-admission mapping under 5.6. Fix its full input/result, subject,
source-closure, pin, fixture and regression inventory before implementation;
do not partially remove Q2 from either unsupported set. Archived inference must
not be relabelled as current-run model inference or automatically admitted as
production input.

An all-true candidate is not a Step 5C acceptance requirement. The actual
partial, unresolved and false states must remain visible. This completed Q2
capture alone is not acceptance of the complete Step 5C observation boundary.
Step 5D relational work, Step 6 resource measurement and Step 7 promotion remain
separate. All preserved results keep `authority_effect=none` and
`production_gate_eligible=false`; this index authorizes no new capture.

Keep #2879 open.
