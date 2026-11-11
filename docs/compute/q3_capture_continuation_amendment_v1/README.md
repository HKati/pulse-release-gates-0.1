# Q3 capture continuation amendment v1 — proposal

## Status and purpose

**Status: `proposed_for_review`.** This package records a concrete protocol
proposal for retaining one historical Q3 observation and collecting the remaining
203 authored tasks once. It contains no continuation implementation, executable
request, dispatch authorization, native execution, accepted dataset or metric
result. Future execution pins remain null in the
[continuation plan](CONTINUATION_PLAN.json), whose closed shape is defined by
[continuation_plan.schema.json](continuation_plan.schema.json).

The preparation baseline is
`be372acb8377e061409594d06ff986e5806160e8`, after cleanup repair
[#3005](https://github.com/HKati/pulse-release-gates-0.1/pull/3005).
That repair preserves the existing first-cap stop rule. This proposal defines
the separate review needed before changing that rule or admitting an observation
from an incomplete session. Review or merge of this package does not authorize
preflight, capture, annotation, scoring or release. Tracking issue
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) remains open.

## Historical result and retrospective disclosure

Run [42928275426, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/42928275426)
used source `17c86e6db6cafdd71b20e3193e0750f03474e735`. Its first task,
`Q3P2-098-L`, returned 256 new token IDs without EOS. The original response frame
and 1,217 UTF-8 response bytes were retained. The terminal record reports one
`length_terminated` occurrence and 203 `not_started` occurrences, with
`TOKEN_LIMIT_TERMINATION`. Worker cleanup was unverified. The cleanup repair does
not establish the missing inner cleanup exception or retrospectively close that
run; see the [native contract](../PULSEMECH_Q3_NATIVE_CAPTURE_v0.md).

This amendment was proposed **after observing that response and failure**. It is
not a claim that continuation after token limit, or reuse of an incomplete
session's observation, was specified before the original run. The proposed
remaining set follows the original order mechanically; neither response quality
nor a later score selects its members. The protocol transition and interruption
remain part of the collection's provenance and interpretation.

The original archive, receipt, terminal, lifecycle records and response bytes
remain unchanged. The plan binds their selected identities. The historical
result remains `incomplete` under v0, even if a future amendment-defined
observation set satisfies its own coverage conditions.

## Fixed frame, subject and partition

The original [task frame](../../../PULSE_safe_pack_v0/examples/q3_native_capture_v0/)
contains 204 tasks: 102 `contract_lookup` and 102 `rule_application`, arranged as
102 pairs over 12 shared document-section contexts. These are not 204 independent
trials. Question, prompt, context, common-instruction, task ID and order bytes
remain fixed. The exact original profile and input hashes are recorded in the
plan and [native-v0 profile](../../../PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json).

| Original ordinal | Treatment proposed here | Count |
| --- | --- | --- |
| 1: `Q3P2-098-L` | Retain the exact historical response; never regenerate it | 1 |
| 2–204: `Q3P2-043-A` through `Q3P2-063-L` | Generate each remaining task once, in original order | 203 |

The machine-readable occurrence list binds every task and original ordinal,
including the entire intervening suffix. New-session position must not replace
original ordinal. Every task's generation attempt remains 1; the new session
has at most 203 calls, while the combined frame has at most 204 task attempts.
No retries, answer replacement, warm-up calls, diagnostic generations, padding,
additional tasks or outcome-dependent top-up are proposed.

The selected model remains `HuggingFaceTB/SmolLM2-135M-Instruct` at revision
`12fd25f77366fa6b3b4b768ec3050bf629380bac`. Runtime input bytes remain the original
508,460,811-byte archive with SHA-256
`b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9`.
The existing offline installation and pinned transport checks still apply.
Generation retains CPU float32, eager attention, deterministic greedy execution,
seed 1729, one beam/return, maximum 256 new tokens, and BOS/EOS/PAD IDs 1/2/2.
The full effective configuration must match; this list is not an override surface.

## Proposed bounded-response rule

Apply the same response criterion to the retained occurrence and every new
occurrence:

| Outcome | Required token termination | Treatment |
| --- | --- | --- |
| `eos` | Between 1 and 256 new tokens; EOS is last and occurs nowhere earlier | Retain as an observed response |
| `token_limit` | Exactly 256 new tokens and no EOS | Retain as an observed bounded response, preserving the stop reason |
| Other or invalid | Missing, partial, malformed, early non-EOS, late or inconsistent response | Execution remains incomplete; stop collection |

Token termination alone is insufficient. Before advancing after a cap, the
controller must validate the complete bounded frame, task/subject/input binding,
configuration, token IDs, exact text representation and response deadline, and
must establish closure of that call's watchdog. No later task may start while
closure is uncertain. The independent checker must reconstruct these conditions
from preserved evidence.

The 60-second response window, 65-second external watchdog, 14,400-second native
phase ceiling and one shared 180-second cleanup grace remain unchanged, together
with the existing memory, context, text, frame and evidence limits. A timeout,
transport failure, invalid record or cleanup failure is not converted to a
bounded response. Valid empty decoded text remains observed text. No response
outcome automatically creates a Q1 label or exclusion.

Under v0, both [worker](../../../PULSE_safe_pack_v0/tools/run_q3_reference_subject_v0.py)
and [controller](../../../PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py)
stop at the first token limit. Their behavior remains unchanged by this package.
The proposed behavior requires a versioned implementation and request.

## Narrow admission of the retained observation

The historical native carrier lacks `token-check.json`, `worker-cleanup.json`,
`decodecheck-sandbox.json`, `decodecheck-cleanup.json`, `examples.jsonl` and
`session-end.json`. Its terminal record does not
establish EOF, exit 0 or a verified exit time. Its lifecycle record reports
unverified worker cleanup and no verified private-tree removal. These limitations
remain visible permanently; new verification cannot manufacture historical
closure.

The existing [native checker](../../../PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py)
verifies inventory and request anchors for an incomplete carrier. That result
does not independently validate the retained call or prove eligibility for a
composite dataset. A dedicated amendment-aware validator is therefore required.

Before accepting this specific retained observation, that validator must bind
the original carrier, source snapshot, request, model-ready/subject records,
token map, call intent, readiness frame, response, raw text, occurrence timing
and watchdog closure. It must also reconstruct the retained control-plane,
runtime transport, input/install and worker-sandbox records under their original
source-bound rules; checking archive hashes alone is insufficient. It must
reconcile the complete original occurrence ledger
and call-member inventory against the fixed 1+203 partition. An uncertain prior
attempt for any remaining task blocks its classification as unstarted.

A **new zero-generation verification** must reproduce the original prompt token
sequences and decode the retained response token IDs using the exact pinned
tokenizer and configuration. It must validate all 204 prompt rows and the one
historical response, retaining its own source, inputs, lifecycle and result
bindings. It may be implemented within a separately specified verification
phase; it must not load a causal-language model or generate an answer.

This establishes newly checked byte/token consistency of the retained evidence.
It does not claim that independent decoding occurred during the original run,
that the historical process exited cleanly, or that a saved hash authenticates
native origin. The accepted trust boundary remains the documented trusted
host/control plane and selected original evidence. Failure of any required
historical-observation check blocks the composite; it does not authorize
replacement of the first answer.

## Coverage and session completeness are separate

| Statement | Meaning under this proposal |
| --- | --- |
| Historical v0 session complete | False; the original result remains incomplete |
| Historical cleanup/EOF verified | Not established by the retained evidence |
| New continuation session complete | Requires 203 valid responses, terminal closure, independent checks and successful preservation |
| Combined observation set complete | Requires exactly one admitted observation for each of the original 204 tasks |
| All contributing sessions complete | False, because the historical session remains incomplete |
| Q1 labels, Q3 metric or release eligibility established | None follows from collection coverage |

Any future composite record must preserve these distinctions. It must not label
the old run complete or present the combined collection as one uninterrupted
204-call native session. The two sessions have separate source/run/subject and
platform observations; identical model and input bytes do not establish identical
hosts or eliminate time effects.

## Versioned implementation and fresh preflight

The pending implementation must address the whole contract, including request
validation, profile identity, source inventory, worker/controller behavior,
terminal counts, watchdog naming, carrier inventory, independent decoding and
composite verification. The native-v0 checker requires 204 EOS completions and
the corresponding lifecycle records. Its historical acceptance rules must remain
replayable; removing one stop assertion would not implement this proposal.

The [v1 capture handoff](../../../tools/q3_capture_handoff_v1.py) also pins the
reviewed native contract/checker and requires exact native source equality with
the selected preflight. A continuation needs an explicitly versioned admission
path with fresh acquisition and immediate in-process admission, preserving the
existing owner, source, attempt and no-overwrite protections. A saved approval or
historical successful preflight cannot substitute for those checks; see the
[handoff contract](../PULSEMECH_Q3_CAPTURE_HANDOFF_v1.md).

Fresh zero-generation preflight must use the **final reviewed implementation
commit**. The original profile digest and historical token-map digest in the
plan identify old evidence. A future v1 profile changes the map's profile binding
even when every prompt token row is identical. The future map must be separately
constructed, verified and selected; comparison with the original map must check
exact prompt-row equivalence without pretending the whole-map hashes are equal.
Future implementation, profile, preflight, request and run pins remain null
until their respective evidence exists and is separately selected.

## Composite projection and unchanged downstream processing

The future upstream adapter must preserve both original evidence carriers and
build a deterministic manifest mapping all 204 original ordinals to their exact
response bytes and source-session identities. Independent composite admission
must succeed before projection to the existing five-field `examples.jsonl`
format: `example_id`, `prompt`, `response`, `context`, `metadata`. Response and
context content remain exact; the projection records its serialization and
whole-file/line hashes. It must not fabricate missing rows or labels.

The [archived-input preparer](../../../PULSE_safe_pack_v0/tools/prepare_q3_archived_input_bundle_v0.py),
[Q3 producer](../../../PULSE_safe_pack_v0/tools/build_q3_reference_summary.py) and
[independent metric checker](../../../PULSE_safe_pack_v0/tools/check_q3_reference_summary.py)
remain unchanged. They do not themselves establish composite native provenance.
The aggregate subject must reference its composite manifest and retain both
actual run identities there. The existing single `runtime_identity` field must
not falsely assign both sessions to one run; any alternative representation
requires explicit contract review.

Human Q1 annotation, sealed label/example bindings, dataset selection, preparation
and standalone scoring remain separate steps under the
[reference contract](../PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md).
`token_limit` does not prescribe `UNKNOWN`, exclusion or failure. Insufficient
eligible labels or a negative metric may remain the result; neither permits
top-up. Historical Q2 FAIL and release BLOCK remain unchanged.

## Pending implementation acceptance conditions

Before any future execution request is considered, review must establish:

1. Exact ordered 1+203 coverage, rejection of duplicate/reordered/replacement
   tasks, and separate original-ordinal/current-session accounting.
2. Identical bounded-response rules for both evidence sources; continuation
   after cap only after valid response and verified watchdog closure; immediate
   stop on invalid, partial, late, missing or failed execution evidence.
3. Dedicated historical partial-observation validation and newly recorded
   zero-generation verification, without upgrading old completion claims.
4. Complete new-session EOF, exit, cleanup, source, token, timing and publication
   reconstruction; no positive status based only on populated files.
5. Versioned request/profile/admission compatibility, final-source preflight and
   independently selected anchors, with no implicit authorization from this plan.
6. Deterministic composite projection, rejection of inconsistent provenance or
   forged completion, preserved originals, and unchanged label/scoring boundaries.

Synthetic regression checks must exercise these acceptance and rejection cases
without claiming native execution. This proposal supplies the reviewable
decisions and evidence partition; implementing and observing them remain pending.
