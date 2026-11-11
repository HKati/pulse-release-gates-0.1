# Q3 bounded continuation v1

## Status and scope

This is the versioned implementation of the accepted
[continuation amendment](q3_capture_continuation_amendment_v1/README.md).
It preserves the exact first response from historical run `42928275426/1` and
permits one new attempt for each of the 203 recorded unstarted tasks. Native
execution of this implementation, fresh preflight, capture acceptance and the
combined observation set remain pending. Merging the implementation does not
dispatch a workflow or authorize a phase.

The preparation baseline is proposal merge
`27b5dcfca262272b5edfa90a2c3048c8b98aa9e1`.
The immutable [plan](q3_capture_continuation_amendment_v1/CONTINUATION_PLAN.json)
has SHA-256
`22daec9e549970c818a90be5f11c3fed9edf5fe25adeb1ac2f65cec28453f22a`.
Its proposal status and null future execution pins remain historical records.
Actual execution identities belong in the later request and retained evidence.

The historical run remains incomplete. Its missing EOF, successful exit and
worker/private-tree cleanup evidence are not supplied retrospectively. The
amendment was made after the original token-limit response was observed; its
retrospective nature remains part of the collection's provenance.

## Implementation map

| Component | Purpose |
| --- | --- |
| [Native contract v1](../../PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py) and [profile v1](../../PULSE_safe_pack_v0/profiles/q3_native_capture_v1.json) | Bind the exact amendment, 204-task frame, 1+203 partition, full effective generation configuration and 38-file source scope |
| [Manual workflow v1](../../.github/workflows/q3_reference_acquisition_v1.yml) and [controller v1](../../PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v1.py) | Enforce owner/source/attempt guards, acquire retained evidence, supervise the selected phase and preserve bounded success or failure evidence |
| [Worker v1](../../PULSE_safe_pack_v0/tools/run_q3_reference_subject_v1.py) and [runtime v1](../../PULSE_safe_pack_v0/tools/q3_native_runtime_v1.py) | Tokenize the complete frame, generate only the 203-task suffix, enforce resource bounds and establish service/watchdog closure |
| [Historical observation checker](../../tools/check_q3_historical_observation_v1.py) | Reconstruct the original partial observation and independently retokenize all 204 prompts and decode its one retained response without model generation |
| [Native checker v1](../../PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py) | Reconstruct complete new-session evidence, independent token/text checks, timing, history admission and lifecycle closure |
| [Read-only postflight acquisition v1](../../tools/acquire_q3_external_postflight_v1.py), [comparison v1](../../tools/check_q3_external_postflight_v1.py) and [handoff v2](../../tools/q3_capture_handoff_v2.py) | Reacquire the selected fresh preflight and admit capture immediately in the same process after successful comparison |
| [Composite checker](../../tools/check_q3_continuation_composite_v1.py) | Build and independently reconstruct a deterministic 204-row projection with separate historical and continuation provenance |

Closed request/result shapes are defined by the
[native request schema](../../schemas/metrics/q3_native_capture_request_v1.schema.json),
[native result schema](../../schemas/metrics/q3_native_capture_result_v1.schema.json)
and [handoff request schema](../../schemas/metrics/q3_capture_handoff_request_v2.schema.json).
Native v0 and handoff v1 files retain their earlier behavior. In particular,
the v0 first-token-limit stop rule is unchanged.

## Fixed inputs and bounded responses

The first original occurrence, `Q3P2-098-L`, is retained exactly. It is never
regenerated. New capture begins at original ordinal 2, `Q3P2-043-A`, and ends at
original ordinal 204, `Q3P2-063-L`. New records retain both original ordinal
2–204 and continuation ordinal 1–203. Every task's generation attempt is 1.

The original prompt, context, common-instruction and order bytes are unchanged.
The full 204-row token map is constructed in both preflight and capture; its
prompt rows must equal the original retained rows. The v1 map has its own
profile binding and digest, so it is not interchangeable with the old v0 map.

The model, revision, runtime archive, offline installation, CPU float32 eager
execution, deterministic settings and full effective generation configuration
remain fixed. The original 508,460,811-byte runtime archive is still acquired
from the pinned immutable companion release and checked before use. No runtime
payload or model weights are added to this repository by this implementation.

| Termination | Accepted response condition |
| --- | --- |
| EOS | 1–256 new token IDs, with EOS only at the final position |
| Token limit | Exactly 256 new token IDs, with no EOS |
| Other or inconsistent evidence | Stop; preserve the attempt as incomplete |

Before the next task starts, the controller checks the entire bounded response
frame, exact subject/task/input/configuration/runtime bindings, token IDs,
UTF-8/base64 consistency, deadline and closed watchdog. A valid empty decoded
string remains observed text. A cap alone does not imply an invalid answer,
label, exclusion or score.

The 60-second response window, 65-second external watchdog, 14,400-second native
phase ceiling and one shared 180-second cleanup grace are unchanged. The new
historical verification service has a 300-second bound within that phase.
Malformed, missing, partial, late or uncertain execution evidence halts capture.
There is no automatic retry, replacement answer, diagnostic generation or top-up.

## Historical observation admission

Every v1 preflight and capture reacquires the fixed historical capture and
runner-image artifacts, together with run, job and artifact metadata before and
after acquisition. The API metadata must identify the exact owner, source,
workflow, attempt, failed job and unexpired selected artifacts. Exact ZIP size
and digest checks precede interpretation. There is no substitute artifact,
unselected source or local fallback.

The historical checker reconstructs the original source snapshot, request,
control plane, runtime transport, installation, sandbox, 204 prompt rows,
subject/configuration, first call, response bytes, timing, watchdog closure and
complete occurrence ledger. It verifies that the other 203 tasks were unstarted.
Archived Python source is inspected as bytes; it is not imported or executed.

A fresh isolated `historicalcheck` phase then uses the pinned installed tokenizer
to reproduce all 204 prompt token sequences and decode the retained response's
token IDs to its exact 1,217 UTF-8 bytes. It does not load a causal-language model
or generate an answer. Its own successful service exit and cleanup are required
before the current worker launches.

The resulting `historical-verification.json` binds the amendment, exact reviewed
implementation commit, full source mapping, selected historical evidence and
model-file identities. It states that the one observation passed the new
verification while preserving the original incomplete-session and unverified
cleanup flags. Current acquisition and historical-phase cleanup records are
separate evidence, bound by the three history hashes in `prelaunch.json`.

The deterministic verification receipt is reproducible across fresh preflight
and capture only for the same exact implementation commit and pinned history.
Different current run/platform observations remain in their own evidence.

## Execution sequence after review

### 1. Fresh zero-generation preflight

Use the final reviewed and merged implementation commit, then prepare a closed
native-v1 `token-preflight` request. The request must contain the exact amendment
digest; both `approved_token_map_sha256` and `historical_verification_sha256`
are null for this phase. The contract's request builder validates this shape and
writes canonical request bytes; it does not dispatch anything.

The Actions workflow is named **Q3 bounded continuation preflight and capture
v1**. Its three inputs remain `source_commit`, `native_request` and
`native_request_sha256`, where the third input hashes the exact UTF-8 bytes of
the second. Only an explicit owner `workflow_dispatch` from `main`, attempt 1,
with source equal to both the checked-out and workflow commit, is admitted.

This phase acquires and verifies historical evidence, installs the fixed offline
runtime, completes zero-generation historical verification, tokenizes all 204
prompts and performs independent checks. Successful preservation and cleanup
are required. No new model response is generated.

### 2. Select and verify that preflight

Inspect the actual preflight run, exact artifact, request, source, token map,
historical receipt, image records and independent verification. A green job icon
or a saved comparison report alone is not capture admission.

The selected preflight and the later capture must use the **same exact reviewed
commit**, even if a later commit changes only documentation. Select the actual
numeric workflow ID of the new v1 workflow from its returned metadata; the old
workflow ID is not reused or inferred.

The capture request selects the verified v1 token-map digest and deterministic
historical-verification digest. It also binds the amendment. `q3_capture_handoff_v2.py`
builds the closed envelope from that native request and selected preflight
identities. Its builder performs no workflow dispatch or generation.

### 3. Separately authorized 203-task capture

The owner submits the capture handoff envelope through the same three workflow
inputs. Before native capture can start, the handoff reacquires the selected
preflight through the read-only API path, reconstructs its evidence, compares
image/source/history/token bindings, and passes admission directly to the native
controller in the same process. Historical v0 preflight and saved verdicts are
rejected as substitutes.

The controller independently reacquires and rechecks history in the new run.
Its resulting historical receipt must match the selected preflight receipt.
Only then does the worker tokenize the full frame, load the fixed model and
attempt the 203 suffix tasks once. The shared workflow concurrency group prevents
simultaneous native v0/v1 jobs on the same ref.

A complete new native carrier requires 203 valid bounded responses, their exact
ordered terminal ledger, session end, EOF, exit 0, independent token/text checks,
all five service closures, all call-watchdog closures, private-tree removal and
successful evidence publication/readback. Incomplete evidence is preserved with
its failure and never upgraded because all expected filenames happen to exist.

## Evidence and composite projection

The workflow preserves its bounded `evidence.zip`, `receipt.json` and applicable
`failure.json` as Actions artifacts for 30 days, with overwrite disabled. The
native carrier includes the unchanged original capture and runner-image ZIPs,
current acquisition records, the historical verification receipt and current
native records. A capture handoff additionally retains its selected preflight
acquisition/comparison and exact source bindings. Credentials are not evidence.

After successful capture and independent carrier verification, the separate
composite tool builds `COMPOSITE_MANIFEST.json` and `examples.jsonl`. Its CLI
requires the exact continuation native archive, archive SHA-256, request SHA-256
and source commit. `--phase build` writes new files; `--phase check` reconstructs
them from the selected carrier and requires exact byte equality. Outputs are
exclusive, and existing files are not silently overwritten.

The manifest maps each original task/ordinal to its original response member,
text digest, stop reason, subject, verification receipt and source/run/session
identity. The output consists of the admitted historical first observation and
the validated 203 new observations in the original order. Both original evidence
carriers remain preserved; the projection does not replace them. Its five-field
rows use `example_id`, `prompt`, `response`, `context` and `metadata`, with exact
serialization and whole-file/line hashes.

The combined record distinguishes:

- Complete 204-task observation coverage, only after both verification paths pass.
- An incomplete historical session and a separately complete continuation session.
- Two source/run/subject/platform observations, not one uninterrupted session.
- `runtime_identity=null` for the aggregate, with the two actual runs recorded in
  the manifest; matching input/model bytes do not establish identical hosts.

The archived-input preparer, Q1 annotation and sealed label/example selection,
Q3 producer and independent metric checker remain separate downstream steps.
No annotation, scoring or measurement is performed by this implementation.
Historical Q2 FAIL and release BLOCK remain unchanged;
`authority_effect=none`; [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open.

## Verification boundary

The registered synthetic tests cover exact 1+203 partitioning, full configuration
identity, valid EOS/cap behavior, original ordinal and watchdog ordering,
malformed/late/duplicate/replacement rejection, historical evidence bindings,
fresh same-source handoff, lifecycle closure and deterministic composite output.
Synthetic service, tokenizer/model and API fixtures do not establish that a real
runner, model or GitHub acquisition has executed successfully.

Read-only reconstruction of the preserved historical carrier is distinct from
the future tokenizer verification phase. The latter must actually run and be
retained before historical observation admission or capture can be accepted.
