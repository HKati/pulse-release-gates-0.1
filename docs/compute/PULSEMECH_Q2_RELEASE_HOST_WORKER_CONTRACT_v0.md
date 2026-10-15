# Q2 native release-host worker contract v0

## Status and fixed scope

This is the separate, non-authorizing implementation contract for combined Q2-2
model readiness and Q2-3 full worker verification under open work order #2879.
The implementation and offline fixtures do not establish native acquisition,
actual model loading, 150 fresh inferences, accepted Q2-4 comparison or full Q2 /
Step 5C/5D acceptance. A reviewed upload/merge and a separate explicit owner
execution-and-retention decision are required before a native run.

Scope: `q2_capsule_worker_protocol_v0`. Platform contract:
`strict_archived_platform_identity_v0`.

The earlier [Q2-1 tokenizer contract](PULSEMECH_Q2_RELEASE_HOST_TOKENIZER_CONTRACT_v0.md)
keeps its four occurrences and all zero-inference claims. Its actual native run
`38478598045/1`, original acquisition source
`d44bf963cbac377366e95ae7ac9e3603fff894a4` and separate canonical replay are unchanged.
[Readiness section 13](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#13-recorded-q2-1-native-tokenizer-and-canonical-replay-checkpoint)
remains the bounded native checkpoint, not proof of this new worker execution.

Historical capture `37600313529/1` remains 150 responses, 147 eligible responses,
49 eligible groups out of the required 50, one UNKNOWN group, metric FAIL /
release BLOCK. No historical record is topped up, reclassified, replaced or
rebound to the new collector commit. Q2-3 is a different, separately consented
execution of the unchanged fixed subject.

## Implementation and trust boundaries

| Role | Bound implementation |
| --- | --- |
| Closed profile and request construction | [Profile](../../PULSE_safe_pack_v0/profiles/q2_release_host_worker_verification_v0.json), [request schema](../../schemas/q2_release_host_worker_request_v0.schema.json), [contract helper](../../PULSE_safe_pack_v0/tools/q2_release_host_worker_contract_v0.py) |
| Privileged collector and native adapter | [verify_q2_release_host_worker_v0.py](../../PULSE_safe_pack_v0/tools/verify_q2_release_host_worker_v0.py) |
| Independent input, token/text, metric and carrier checks | [check_q2_release_host_worker_v0.py](../../PULSE_safe_pack_v0/tools/check_q2_release_host_worker_v0.py) |
| Complete protocol reconstruction | [check_q2_release_host_worker_protocol_v0.py](../../PULSE_safe_pack_v0/tools/check_q2_release_host_worker_protocol_v0.py) |
| Result, plan, prelaunch, lifecycle and check records | [Result schema](../../schemas/q2_release_host_worker_result_v0.schema.json) |
| Manual owner-controlled acquisition | [Workflow](../../.github/workflows/q2_release_host_worker_verification_v0.yml) |
| Permanent offline tests | [Protocol](../../tests/test_q2_release_host_worker_protocol_v0.py), [integration](../../tests/test_q2_release_host_worker_v0.py) |

The stdlib-only entry guard checks owner/event/ref/attempt and exact committed
source before importing repository helpers. It verifies Git blob/mode identities
and held bytes, then imports helpers from a root-private copy. The current
source closure is the explicit 39-path profile inventory, not the whole project.
Current collector source and the original worker/capsule acquisition identities
are distinct. Original worker, model, workload, metric and Q2-1 files remain
unchanged. There is no new generic runtime engine, policy input or gate recipe.

The checked-out entry point, Git object database, privileged observer, runner
kernel, GitHub control plane and pinned Actions remain trust boundaries. This
contract is not protection from a compromised root/runner and is not an
organizationally independent audit. Source-bound independent reconstruction is
not a second kernel observation.

## Owner request and strict platform decision

The request binds the actual reviewed collector commit, profile bytes, unchanged
input identities, worker/workload digests, this scope, 150 planned calls and
precisely declared retention. It has no arbitrary command, alternate URL/model,
future job/run/artifact ID or fallback input. Duplicate keys, malformed encoding,
unknown fields, mismatched byte digests and bool/integer substitutions reject.
The workflow event separately binds the same request bytes and owner identity.
GitHub current-main, run-attempt and single-job metadata are checked before
artifact acquisition. Source changes or unavailable/expired original inputs
reject; there is no search for a newer artifact with the same name.

The required consent marker is:

```text
AUTHORIZE_150_FRESH_CALLS_AND_30_DAY_ACTIONS_RAW_EVIDENCE_RETENTION
```

Preparing or merging this implementation is not that consent. The request
constructor requires its explicit consent switch but only emits request bytes;
it does not dispatch, acquire, load a model or authorize anyone other than the
subsequently authenticated owner. The existing read-only workflow token is used
only for transport and control-plane verification; it is not inherited by
subjects or forwarded to redirected artifact storage.

All seven historical platform requirements must match before new model calls:

| Field | Required value |
| --- | --- |
| Python | CPython 3.11.16 / Unicode 14.0.0 |
| Bootstrap interpreter SHA-256 | `a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc` |
| OS | `ubuntu-24.04` |
| Architecture | `x86_64` |
| Runner image | `20261004.327.1` |
| Kernel | `6.17.0-1022-azure` |
| libc | `glibc`, `2.39` |

The native target also requires root, systemd PID 1 and cgroup v2. Python version
text alone does not replace the original binary and base-library checks. A newer
hosted image/kernel rejects even if it could execute the model. A future
compatibility contract would need separate review; neither the old manifest nor
this profile is silently relaxed to fit the runner. Even a complete matching run
keeps `full_release_host_verified=false`: this unit does not discharge every
whole-runtime obligation.

## Four phases and one complete worker session

| Phase | Execution and required evidence |
| --- | --- |
| `input_check` | Separate pinned verifier; original archive/capsule/source/projection checks; exit 0. |
| `worker` | Unchanged capsule worker CLI in explicit `capture-reference` mode, original capsule interpreter; full model-ready/BIND/150-slot/FINISH/EOF/exit-0 protocol. |
| `tokenizer_check` | Separate capsule-interpreter service; independently tokenize/decode all original new response records, reconstruct groups/manifest and retain the checker-produced token map; exit 0. |
| `reduction_check` | Separate capsule-interpreter service; unchanged metric builder and independent checker. Builder 0 for PASS or 1 for FAIL, checker 0, outer service 0 only after valid independent verification. |

The worker is executed from the immutable capsule's `source/` tree, not a
regenerated copy or a new loader. Its explicit 16-argument command template is
fixed in the prelaunch execution plan. The original `capture_session_exchange`
provides per-call permission and external watchdog handling. A model-ready record
is emitted before BIND and supplies the Q2-2 readiness observation within this
same full Q2-3 run. There is no separate diagnostic generation or readiness run.

```text
source / input / strict host checks
→ actual pre-EXEC isolation observation
→ original worker, --mode capture-reference
→ model_ready → freeze subject → BIND → original bound acknowledgement
→ 150 × [PREPARE → slot_ready → external watchdog → GENERATE → response]
→ FINISH → session_end(completed_calls=150) → actual stdout EOF → exit 0 → reap
→ verified worker and watchdog cleanup
→ independent tokenizer and metric phases
→ source/input recheck → all private-tree cleanup
→ independent carrier verification → exclusive publication
```

The fixed 50×3 slot inventory, request ordering, model revision, eight model and
tokenizer files, original runtime, CPU float32/eager configuration, seed 1729,
greedy settings and 32-token continuation bound remain unchanged. No retry,
151st call, response replacement, mixed-run concatenation or historical top-up is
permitted. A completed token-limit outcome may produce UNKNOWN; missing response,
timeout, missing FINISH or forced termination is incompleteness, not UNKNOWN.

One monotonic 1200-second phase budget covers acquisition/preparation/execution.
Checker services have a 180-second bound; the worker is additionally bounded by
the remaining phase time. Per-call observation has the unchanged 15-second
window and 20-second external watchdog. Cleanup has one shared extra 180-second
grace, not a reset for each unit. The workflow cap is 30 minutes. These are
execution limits, not measured consumption: `resource_measurement=unavailable`.
UTC/control-plane time is not silently identified with the supervisor clock;
`clock_relation=not_verified` remains explicit.

## Projection, observations and cleanup

The existing immutable archive/bootstrap/verifier preparation is reused without
changing its byte rules. Its original installer is not executed; the existing
verified stock-library preparation is applied before any subject. The new root
is `/var/lib/pulse-q2-worker-<8-character-id>/projection`; the sibling `private`
directory remains root-only. Subject files are root/65534 read-only. Writable
phase outputs are separate and frozen only after the producing service's real
exit and verified cgroup/client cleanup. Equal bytes from a different occurrence
do not substitute for a producer binding.

Actual privileges, namespaces, cgroup limits and systemd isolation are observed
before EXEC using the unchanged native barrier/observer. A property string,
fixture or successful exit alone is insufficient. Services and watchdogs are
registered before creation, so failure during construction does not remove the
cleanup obligation. Both service/cgroup/client and timer closure are checked;
private-directory deletion alone never proves process termination.

`lifecycle-before-cleanup.json` explicitly records `private_tree_cleanup=pending`
for downstream checking while the projection exists. Only after actual removal
is `lifecycle.json` emitted with `verified_removed`; every other field must
remain byte-equivalent in meaning. The protocol component defaults to requiring
final cleanup. Its separately requested pre-cleanup mode cannot claim cleanup.
The original execution error is retained when cleanup also fails, and an
unverified unit prevents accepted publication.

## Carrier, exposure and independent reconstruction

The native workflow publishes only `evidence.zip`, `receipt.json` or a bounded
`failure.json`, in the declared `q2-native-worker-<run>-<attempt>` Actions artifact.
It never uploads the entire workspace, model/bootstrap archives or private log
directory. Inner evidence has exactly 618 regular files: 18 named metadata and
derivation files plus 150×4 original slot-ready/response/intent/UTF-8 records.
The exact set is computed by `evidence_names()` and independently checked.
The result binds the other 617 file digests. Archive and result digests are in
the separate receipt. Original wire-record bytes are retained; they are not
re-serialized to make a comparison pass.

**This future Actions carrier includes raw generated text, token IDs and the
answer-bearing groups. Actions storage is not confidential storage.** The owner
must explicitly accept repository-reader access and 30-day retention in the
request before any new generation. GitHub documents that signed-in users with
repository read access can download workflow artifacts:
[Downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).
No raw original capture, new generated response, token array or prompt is
committed to this repository or included in the implementation delivery. The
workflow does not print these payloads to general CI logs. No model weights or
credentials belong in the carrier. A private destination requires a different
reviewed transport/retention contract, not an informal destination override.

The two metric CLIs actually recompute and cross-check the new native metric in
the isolated reduction phase. A complete valid measurement may still return
FAIL. Its result is not production authorization and cannot overwrite the
historical 49/50 result.

The independent `check-evidence` CLI reconstructs the closed carrier against
externally selected archive/result digests and exact reviewed source. It checks
original slot records, producer hashes, lifecycle, all four phase observations,
recorded checker outputs and deterministic group/manifest reconstruction using
the retained independent token map. It explicitly returns
`native_origin_reacquired=false`, `tokenization_reperformed=false` and
`metric_recomputed=false`: this offline carrier check does not execute the
original tokenizer or metric anew. A replay check does not establish durable
custody, authentic external selection, another native observation or Q2-4
candidate/historical comparability. Those remain separately reviewed duties.

## Failure and authority contract

| Failure | Required disposition |
| --- | --- |
| Missing/changed owner, source, request or explicit consent | Reject before subject acquisition or execution. |
| Missing/expired input; changed original bytes or strict host | Reject; no alternative artifact/runtime or relaxed profile. |
| Missing pre-EXEC observation, foreign BIND or any wrong slot | No complete worker result; stop/reap and verify cleanup. |
| Timeout, missing EOF/FINISH/session-end, nonzero worker exit | Retain rejection; never reclassify as UNKNOWN or completion. |
| Token/text/configuration or independent metric mismatch | No accepted result. |
| Service, watchdog, cgroup, client or private-tree cleanup unverified | No accepted result or receipt. |
| Final verifier/publication failure | Remove incomplete publication where possible; bounded failure only. |
| SIGKILL, cancellation or host loss without terminal evidence | Incomplete, even when a partial file exists. |

Every result preserves `authority_effect=none`, `production_gate_eligible=false`,
`active_gate_eligible=false`, `same_run_release_authority_eligible=false`,
`historical_metric_pass=false`, `full_release_host_verified=false` and
`q2_comparison_accepted=false`. The workflow participates in no required gate,
attestation, certificate or release path. Q2-4, other unavailable gate evaluators,
Step 5C/5D and #2879 remain open.

## Later owner procedure — not an instruction to execute during implementation

First review and upload the complete implementation batch, including the manual
workflow, guard, classifier, both test registrations and documentation. Wait for
that actual PR's checks and review before merging. Local tests do not replace
PR-head CI. A Dependabot-only change elsewhere must not be overwritten with an
old full-repository snapshot.

After merge, separately review the 150-call boundary, strict platform and raw
Actions exposure/retention. Only following that explicit owner decision may a
request be constructed from an exact clean checkout of the new reviewed main:

```bash
source_commit="$(git rev-parse --verify HEAD^{commit})"
python -I -B PULSE_safe_pack_v0/tools/q2_release_host_worker_contract_v0.py \
  --repo-root "$PWD" --source-commit "$source_commit" \
  --authorize-150-and-actions-retention > q2-worker-request.json
```

This command creates request bytes only. Compute SHA-256 over the exact UTF-8
bytes that will be entered in the manual workflow, including the chosen final
newline. Do not compute one representation's digest and submit another.
Use **Actions → Q2 native release-host worker verification v0 → Run workflow**,
select main and provide `source_commit`, `native_request` and
`native_request_sha256`. Do not use the tokenizer workflow or an old request.
An attempt greater than 1 rejects; a failed result cannot be turned into a
successful reference by rerunning a job. Any later new run needs its own reviewed
request and decision, not a search for a preferable metric result.

After an actual completed run, select its exact artifact/run/attempt/source,
retain the downloaded original bytes and receipt, and verify the inner carrier
using the matching exact source checkout. Neither digest below is known before
that real run; placeholders are not usable evidence:

```bash
python -I -B PULSE_safe_pack_v0/tools/check_q2_release_host_worker_v0.py \
  --phase check-evidence --source /path/to/exact-reviewed-source \
  --root /path/to/evidence.zip \
  --expected-archive-sha256 ACTUAL_SELECTED_INNER_ARCHIVE_SHA256 \
  --expected-result-sha256 ACTUAL_SELECTED_RESULT_SHA256
```

No native run ID, job ID, artifact ID, result digest or acceptance is fabricated
by this implementation. Later Q2-4 work must predeclare the historical/candidate
comparison and exact accepted preservation. The earlier original-input durable
owner-held retention status remains `not_verified` until separately evidenced.

## Regression integration

The tools manifest appends the protocol and integration test programs exactly
once, 165 to 167 entries, preserving prior ordering. All seven existing literal
count consumers are reconciled together. The existing acquisition hygiene
fixture includes the new workflow. The Python pin exception is restricted to
this exact workflow and its `verify_host` job. Normative inventory recognizes
only this reviewed workflow's exact normalized text digest as a non-authorizing
carrier; renaming or changing authority/permission/trigger/pin/retention bytes
requires new review. Existing workflow classifications stay unchanged.

Offline tests include the actual unchanged worker CLI and exchange running in
real child processes with explicit toy model/tokenizer and kernel/timer doubles,
full collector custody/publication under synthetic transport/host services,
negative request/origin/slot/token/terminal/cleanup cases, both real metric CLIs,
physical archive constraints and actual workflow/hygiene/classification guards.
They establish implementation behavior, not native model or systemd evidence.
The delivery's validation report identifies exact executed cases, failures,
environment changes and source-restoration limits; no native qualification is
implied by a Python version label or successful fixture.
