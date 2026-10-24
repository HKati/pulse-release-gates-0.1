# Q3 native token preflight and capture v0

## Status and boundary

This is implementation for a separately authorized, finite Q3 observation path
under [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879).
Its implementation source baseline is
`d4fee2e007eb97cee652bd62cde81aef57b79b1f`, including #2948. The authored task
content remains bound to `565869f017507e2635db1b2a9dbc82bdc80c26ce`.
Implementation, synthetic tests, PR checks and merge do not constitute native
qualification, token fit, model capability, observed answers, human Q1 labels,
Q3 measurement, release admission or completion of Step 5C/5D/6/7.

The exact 204 authored tasks (102 `contract_lookup`, 102 `rule_application`)
retain the P2 question/order/context/instruction bytes. There are 102 pairs and
12 shared document-section contexts, not 204 independent trials. No paraphrase
padding, outcome-dependent selection, answer replacement or top-up is added.
The annotation review aid is deliberately absent from the execution closure.
A task is an experimental stimulus, not a previously observed answer.

The existing Q3 archived-input preparer, producer, independent metric checker,
profile and schemas remain byte-preserved. Historical Q2 49/50 FAIL and release
BLOCK remain unchanged. The fixed Q2 150-call worker is neither modified nor
imported. No Q2 acquisition/replay is repeated. No second analyzer, relation
engine, gate evaluator or release-authority path is introduced.

## Components and complete source scope

| Role | Path |
| --- | --- |
| Closed request/profile and source binding | `PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py` |
| Finite native isolation/installation/lifecycle | `PULSE_safe_pack_v0/tools/q3_native_runtime_v0.py` |
| Tokenizer-only and generation worker | `PULSE_safe_pack_v0/tools/run_q3_reference_subject_v0.py` |
| Guarded owner controller | `PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py` |
| Separate input/install/token/carrier verifier | `PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py` |
| Fixed profile and limits | `PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json` |
| Closed request schema | `schemas/metrics/q3_native_capture_request_v0.schema.json` |
| Result/receipt/record schemas | `schemas/metrics/q3_native_capture_result_v0.schema.json` |
| Four exact P2 inputs | `PULSE_safe_pack_v0/examples/q3_native_capture_v0/` |
| Manual workflow | `.github/workflows/q3_reference_acquisition_v0.yml` |

The profile names exactly 21 execution-source files. It includes the five tools,
profile, workflow, two schemas, four P2 files, two old context documents,
unchanged Q2 model map/lock and four original preparation records. This is not a
claim to snapshot the whole repository or all host software. Tests and this
contract are not executable subject inputs. The controller's literal inventory
and profile must agree before acquisition. Each source file is compared with
the selected commit's Git blob, held in memory and copied to a private source
tree before helper imports or downloaded dependency execution. The entry script,
Git database and host remain trusted. Source binding does not authenticate a
malicious root or control plane.

The profile's exact bytes are pinned in the contract and request schema. No
caller-selected digest, URL, model, command, slice or deadline can override it.
The profile lists source paths, not its own digest or future results, avoiding a
self-referential hash. A separately reviewed commit binds the complete source.
A future profile revision requires synchronized code/schema review; an expired
artifact never causes a search for the newest object with a similar name.

## Two non-interchangeable operations

### Token preflight — zero generation

The owner request must carry:

```text
mode: token-preflight
authorization: AUTHORIZE_ZERO_GENERATION_TOKEN_PREFLIGHT_AND_30_DAY_ACTIONS_RETENTION
approved_token_map_sha256: null
```

This path verifies the runtime archive, installs only its hash-locked wheel
closure offline, independently checks installed bytes, then tokenizes all 204
exact requests using the actual pinned fast tokenizer and chat template.
It instantiates no causal-language model and calls no generation operation.
Weights are checked as bytes, not executed. An independent isolated tokenizer
phase reproduces every prompt-token sequence before accepted publication.

The deterministic `token-map.json` binds the model revision, profile, task-file
identity, order, full logical-input and message digests, and each input-token
array. It contains no run identity, so a separately approved map can be compared
exactly in a future capture. Its surrounding records bind the actual run.
Token preflight proves neither answer quality nor future model readiness.

### Capture — separate approval, no hidden calls

The request must instead carry:

```text
mode: capture
authorization: AUTHORIZE_204_SINGLE_ATTEMPT_CALLS_AND_30_DAY_ACTIONS_RAW_RETENTION
approved_token_map_sha256: the externally selected verified preflight-map digest
```

This implementation does not dispatch either request. A missing, arbitrary or
changed preflight-map digest cannot pass the native map comparison. All 204
inputs are tokenized again before LOAD. Capture loads the fixed model only after
the map matches, records its actual runtime/effective configuration and binds the
subject before any GENERATE command. Loading the model is not a hidden warm-up
or inference call. Each task gets one freshly constructed tensor/configuration;
no earlier answer, conversation history or cached key/value state is supplied.

```text
owner / event / main / attempt / source / request checks
-> API control-plane checks -> exact original runtime archive
-> isolated offline installation -> independent installed-byte check
-> observed worker isolation -> EXEC -> worker_ready -> TOKENIZE
-> 204 token records -> token-map end
   preflight: FINISH -> zero-call session-end -> EOF -> exit 0 -> reap
   capture: approved map -> LOAD -> model_ready -> subject -> BIND
            -> 204 x [PREPARE -> slot_ready -> saved intent
                       -> external watchdog -> GENERATE -> original response]
            -> FINISH -> session-end(204) -> EOF -> exit 0 -> reap
-> independent token/decoding check -> exact examples projection for capture
-> source recheck -> service/timer closure -> private-tree removal
-> independent complete-carrier reconstruction -> exclusive publication
```

A token-limit response retains its raw frame, token IDs, text and termination
reason, then stops the session. No later task is generated and no UNKNOWN label
is invented. A complete EOS response with genuinely empty decoded text remains
an observed empty answer, not a transport failure; later labeling is separate.
A malformed, missing, late or partial frame is incomplete execution. A final
marker or 204 populated filenames alone cannot establish completion.

## Candidate model, platform and fixed limits

Candidate model: `HuggingFaceTB/SmolLM2-135M-Instruct`, revision
`12fd25f77366fa6b3b4b768ec3050bf629380bac`. The exact eight model/tokenizer files
and thirty wheel packages come from the unchanged Q2 preparation archive:

```text
artifact: 11282419957
original run: 37148637546 / attempt 1
size: 508460811 bytes
SHA-256: b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9
```

Availability must be checked at actual execution. Reuse is of selected input
bytes, not historical answers, a Q2 qualification verdict or historical-host
equality. This new path uses a fresh offline installation. No model/wheel payload
is copied into the repository upload or output carrier.

| Limit | Selected implementation value |
| --- | --- |
| Platform family | Ubuntu 24.04, Linux x86_64, CPython 3.11.16, systemd PID 1, cgroup v2 |
| Platform identity | Observe runner image, kernel, libc and interpreter digest; no historical Q2 equivalence |
| Model execution | CPU float32, eager attention, one intra/inter-op thread, deterministic algorithms, seed 1729 |
| Generation | Greedy, one beam/return, maximum 256 new tokens; fixed BOS 1 / EOS 2 / PAD 2 |
| Context contract | 8192 tokens, at most 7936 prompt tokens; no truncation |
| Logical request / response text | At most 16384 UTF-8 bytes each |
| Attempt boundary | At most 204; one per task; zero retries, warm-ups or diagnostic generations |
| Per-response window | 60 seconds from the supervisor's GO write boundary |
| External watchdog | 65 seconds, armed before GO; inactive state verified before the next task |
| Whole native phase | 14400 seconds, including preparation and independent verification |
| Final cleanup grace | One shared additional 180 seconds, never reset per unit |
| Independent token verification | At most 300 seconds, within the phase deadline |
| Isolated service limits | 4 GiB memory, zero swap, one CPU quota, 64 tasks |
| Individual protocol frame | At most 1 MiB; bounded aggregate pipe consumption |
| Uncompressed evidence | At most 256 MiB and 2000 regular members; individual evidence member <=16 MiB |
| Workflow | Manual only, standard `ubuntu-24.04`, 270-minute cap; no larger-runner fallback |
| Retention | 30-day Actions artifact, no overwrite |
| New spending | Request permits zero new spend; no paid inference API or billing operation |

These are ceilings, not observed consumption or duration estimates. The code does
not audit the account's billing state or promise a free host. If the selected
standard route is unavailable or its use would require additional spending,
stop rather than silently selecting another service. No owner-installed runner
is required. This path does not measure Step 6 resource coverage.

## Isolation, transport, lifecycle and failures

The privileged collector controls a fresh `/var/lib/pulse-q3-<random-id>` tree.
Sources and installed/model inputs become root-owned read-only-to-worker bytes.
The installer and model/tokenizer services run as UID/GID 65534 in independently
observed network/mount namespaces with empty capabilities, no new privileges,
no Internet socket families, fixed cgroup limits and bounded lifetime. Requested
systemd property strings alone are not accepted: the supervisor checks the actual
PID, process status, cgroups, namespace identity and `/run` mount observations
before releasing EXEC. The independent checker separately reinterprets retained
sandbox observations. This is not independent re-observation of the kernel. The controller retains
actual UTC start/end observations and monotonic per-call/exit times. These
clock domains are not asserted to be synchronized with GitHub; missing, reversed
wall-clock endpoints or a late observed worker exit cannot establish completion.

The read-only GitHub token is used by the controller for authenticated metadata
and fixed-artifact transport. It is not inherited by a subject or forwarded to
signed storage redirects. Only bounded HTTPS redirects to the explicitly
allowed storage host suffixes are accepted. The archive digest, exact member
set, sizes, file types and payload hashes are verified before extraction/install.
No downloaded Python source or model custom code is enabled.

Service/timer objects are registered before launch side effects. Unknown client
launch identity, missing inactivity evidence or unreaped processes cannot produce
successful cleanup. Failed cleanup preserves its original error and prevents a
complete result. Early workspace setup records owned identity before risky work;
uncertain ownership is not permission to delete a replacement. Output-member
modes are explicitly set and verified, independent of creation umask.

Only a successful exit, an intact receipt, matching selected archive/result
bytes and successful independent carrier reconstruction constitute this path's
complete result. An operational failure may leave a partial archive or private
residue; it must not be promoted because a filename exists. Setup failure may
produce only `failure.json` with an explicit cleanup state. Failure of the output
medium, SIGKILL, machine loss or cancellation can prevent even that record. Such
absence is not proof of cleanup or no execution. Existing output paths are not
overwritten; reconciliation precedes any later separately authorized run.

The trusted host/control plane, privileged collector, installed dependency bytes
and caller-controlled output parent remain trust boundaries. This mechanism is
not security against malicious root/kernel/runner or simultaneous malicious
same-user filesystem manipulation.

## Evidence carrier and downstream labels

Successful native publication contains `evidence.zip` and `receipt.json` only.
An incomplete attempt may also contain bounded `failure.json`; early setup
failure can have that file alone. The workflow uploads only these explicit
paths under `RUNNER_TEMP/q3-reference-capture/<run>-<attempt>/`, never the whole
workspace, model, wheelhouse, private service logs, secrets or environment.

Complete preflight has 248 evidence members plus `result.json` (249 total).
Complete capture has 1068 evidence members plus `result.json` (1069 total).
Counts follow the exact source/task inventory, not whatever happened to be
observed. Every member is identified by size and SHA-256; the result excludes
its own digest, and the external receipt binds the complete ZIP and result.
The evidence retains original received protocol bytes without reserialization.

Capture's independent native token/decoder phase reconstructs every prompt-token
sequence and decoded response, including exact UTF-8 text. It constructs the
existing five-field `examples.jsonl` representation (`example_id`, `prompt`,
`response`, `context`, `metadata`) without changing response/context bytes or
inventing labels. This is a declared projection, not a claim that provider wire
records and JSONL have identical bytes. IDs/task_form come from the predeclared
frame, not inferred answer quality or personal attributes.

An offline `check-carrier` run checks external anchors, exact source bytes,
closed inventory, input/subject/call bindings, termination/cleanup, retained native
verification records and deterministic example projection. It does not reinstall
wheels, execute the tokenizer, reacquire native origin or recompute Q3. The full
resolved GenerationConfig comparison occurs during the native independent token
check; the offline phase verifies the fixed settings and bound retained outcome.
A consistently replaced carrier **and** replaced external anchor cannot establish
original-source authenticity. Digests are not signatures or proof of label truth.

No `q1_labels.jsonl`, accepted dataset manifest, Q3 input selection or metric
report is produced by capture. Human annotation, label sealing, original-byte
selection, standalone preparation/reduction/check and durable preservation need
their separately specified steps. Do not feed an incomplete carrier into those
steps or silently top it up. Every result retains non-authority claims, including
`label_correctness=not_verified`, `metric_evaluated=false` and
`current_run_evidence=false` (no current-run **release** eligibility).

Actions artifacts on this public repository are not confidential storage.
Explicit phase approval includes repository-reader access and 30-day retention.
It is not permission to add future private/user data, publish model weights or
claim permanent preservation. Owner-selected downloaded copies and verified
readback remain a separate custody step.

## Later owner procedure, not execution authorization

Review the complete implementation, its final PR-head CI and current review,
then merge. Neither that merge nor this document authorizes a native dispatch.
Only after explicit approval of the named phase, exact frame/model/limits and
retention should a request be made from the actual reviewed clean source:

```sh
python -I -B PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py \
  --repo-root /path/to/exact-reviewed-checkout \
  --source-commit ACTUAL_REVIEWED_MAIN_SHA \
  --mode token-preflight \
  --authorization AUTHORIZE_ZERO_GENERATION_TOKEN_PREFLIGHT_AND_30_DAY_ACTIONS_RETENTION
```

This constructs request bytes only. Hash the exact UTF-8 bytes including the
chosen final newline; the manual workflow takes `source_commit`, `native_request`
and `native_request_sha256`. Do not reuse a pre-merge request. Use only the new
Q3 workflow, never Q2 acquisition. A re-run attempt greater than 1 rejects.
A separately approved capture request uses the capture authorization string and
`--approved-token-map-sha256` from the actually verified token preflight.
No future run/job/artifact ID, result hash or acceptance is predeclared.

After an authorized operation, preserve the selected original outer Actions ZIP,
inner `evidence.zip`, receipt and their identities. The later offline checker is:

```sh
python -I -B PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py \
  --phase check-carrier --source-root /path/to/exact-reviewed-checkout \
  --archive /path/to/evidence.zip \
  --expected-source-commit ACTUAL_COLLECTOR_SHA \
  --expected-archive-sha256 ACTUAL_SELECTED_INNER_ZIP_SHA256 \
  --expected-request-sha256 ACTUAL_SELECTED_REQUEST_SHA256 \
  --output /path/to/new-check-record.json
```

Checker exit 0 means complete source-bound reconstruction; exit 1 is a verified
incomplete carrier, not successful capture; exit 2 is rejection/operational error.
The request constructor exits 0 for valid request construction or 2 on rejection.
Native controller exits 0 for complete capture/preflight, 1 for a recorded
incomplete operation, 2 when entry/final publication is rejected or unavailable.
No exit code is a metric or release decision.

## Offline validation and integration

Four new pytest programs exercise contract/frame, worker/protocol, native-carrier
integration and workflow/guard/classification. Native observations and model,
tokenizer, transport and timer behavior in those tests are explicit synthetic
doubles; real temporary files/child-process framing do not make them native model
experiments. Positive complete preflight and complete 204-slot capture paths are
checked together with rehashed mutation, missing evidence, bounds, permissions,
early failures, cleanup and publication rejections. Existing Q3, Q2 hygiene and
Paradoxon controls remain separate regressions.

The four programs append to `ci/pytest-tests.list`. The 167-entry
`ci/tools-tests.list` and its count consumers remain unchanged. The hygiene rule
adds only this workflow's `acquire` job with Python 3.11.16. Both existing Q2 and
Paradoxon guard fixture factories now stage that required workflow; their prior
rules are retained. The inventory classifier grants non-authority status only to
the exact reviewed workflow text digest. Changed carriers fall back to conditional
classification. Navigation/changelog entries retain unrelated post-#2948 work.

No hosted run, model readiness, token fit, inference, label validation, resource
measurement or release activation is asserted by this implementation contract.
Keep #2879 open. The paused QRH003 handoff, DOI/SWH and root README are unchanged.
