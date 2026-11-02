# PD-SM-02-W1 — manual hosted native capture v0

Classification: **Implemented manual acquisition integration; hosted native W1 execution NOT_RUN by this delivery.**  
Implementation preparation base: `db9d385b66c1f660c286b557aee931ee4f1fcea6` (PR #2976 merged).  
Subject: `pd_sm_02_w1_diagnostic_healthy_v0`.  
Authority effect: `none`.

## 1. Purpose and preserved input

This adds a GitHub-hosted entry point for the existing [native acquisition
controller](PD_SM_02_W1_NATIVE_CAPTURE_v0.md). It consumes the
[preserved request](PD_SM_02_W1_NATIVE_REQUEST_v0.md) without rebuilding it.

| Identity | Fixed value |
|---|---|
| Original archive | `docs/evidence/PD_SM_02_W1_NATIVE_REQUEST_v0/PD_SM_02_W1_NATIVE_REQUEST_v0.zip` |
| Archive bytes | `444703` |
| Archive SHA-256 | `dbb532a1447f6602f6a9dda53599bd8cbb163e60f94fc2c724178bb3700e8834` |
| Native request SHA-256 | `655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a` |
| Native request run ID | `pd-sm-02-w1-native-after-41362257003-01` |
| Reviewed request preparation source | `6343d4e54ec8628f033400518fe08a81aa75d9b9` |
| Earlier environment admission | [run 41362257003, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/41362257003) |
| Local image ID | `sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3` |
| Platform manifest | `docker.io/library/python@sha256:a7cb177dc60dfa77b223192cd0d9e6ce1aac7cf9a569023d68e7c91b6371a718` |

The historical request `preparation_base` remains
`2890469ee82333f4d34872bbe711cda6ad9b49aa`. The hosted checkout commit and
GitHub run identity are separate companion records. Neither the request nor its
twenty bound payloads is rewritten to insert the new workflow identity.

The successful earlier admission is preserved context. The native controller
performs its own two live supervision controls on the actual execution host
before P00, and checks each fresh container before sending its execution token.

## 2. Added integration

| Path | Responsibility |
|---|---|
| [Manual workflow](../../.github/workflows/paradox_w1_native_v0.yml) | Owner/source/request guard, exact checkout, offline import and verification, pinned image acquisition, one capture call, replay and artifact retention. |
| [Hosted helper](../../tools/paradox_w1_hosted_native_v0.py) | Check the original archive and full manifest, import a fresh package, bind hosted context, supervise the controller call and distinguish completion from partial evidence. |
| [Existing W1 test module](../../tests/test_paradox_w1_native_v0.py) | Additional hosted regressions, retaining its existing registration in both CI manifests. |

The five frozen native source files, record checker, case sources, predictions,
request archive and checksum remain unchanged. The helper verifies their exact
source identities before importing the controller from the reviewed checkout.
It does not import preparation scripts or programs from the ZIP.

Both existing CI test manifests retain their full contents. This integration
adds no shortened CI route and changes no Q3 test, workflow or capture behavior.
It has no required-gate, policy, release, attestation, DOI or publication wiring.

## 3. Admission to the hosted call

The only trigger is `workflow_dispatch`. The workflow runs on `ubuntu-24.04`
with `contents: read`; it has no write or OIDC permission. The initial guard
requires all of the following before checkout or image acquisition:

- Repository `HKati/pulse-release-gates-0.1` and branch `refs/heads/main`.
- Actor `HKati`, actor ID `128643840`, and triggering actor `HKati`.
- First GitHub run attempt: `GITHUB_RUN_ATTEMPT=1`.
- The entered 40-character source SHA equals both `GITHUB_SHA` and
  `GITHUB_WORKFLOW_SHA`; the workflow reference is this exact file on `main`.
- The exact preserved native request digest and its distinct authorization literal.

After checkout, the checked-out HEAD and tracked working tree are checked.
The helper additionally checks the GitHub-hosted Linux/X64 runner context,
`ImageOS=ubuntu24`, a recorded runner image version, and the same identity
and acknowledgement values. Only an explicit metadata allowlist is retained.
The general environment, credentials and Docker configuration are not copied.

The original archive, its SHA-256 sidecar, all 56 ZIP members and the 54-member
manifest are checked before any package member is written. Paths, duplicate
members, member types and decompression sizes are bounded. Only the exact
21-file native package is staged; an existing claim or capture is refused.
The original ZIP and sidecar are retained separately under `input/`.

The image is acquired by the fixed platform manifest using a fresh private
Docker configuration and the local Unix daemon. Acquisition has a 240-second
timeout, followed by an exact local-image-ID check. There is no tag fallback,
alternative image, build, dependency installation or image-acquisition retry.
The unchanged native controller continues to use `--pull=never`.

## 4. Bounded capture and interruption

The helper makes one call to the unchanged native `execute` implementation.
The order is `probe-time`, `probe-output`, then **P00 → N01 → N07 → N08 → N02**.
The first two are benign supervision controls; the candidate budget is five.
Each case has its own fresh container and scratch state.

The controller retains its existing stop conditions: failed control, failed
boundary/readiness check, incomplete observation, prediction mismatch or cleanup
failure stops the remaining plan. There is no resume, retry, top-up or candidate
substitution. The expected N02 primitive refusal remains a control result.

A 420-second cooperative deadline surrounds the controller call. SIGALRM,
SIGTERM or SIGINT records the interruption and raises once, allowing the existing
controller/boundary cleanup paths to run. Further handled signals do not interrupt
that cleanup a second time. The workflow's 15-minute hard limit leaves room for
image acquisition, bounded cleanup, replay and upload under normal runner operation.
This is not a guarantee against a hard kill, runner loss or platform cancellation.
Those events may prevent closure or upload; missing cleanup evidence stays missing.

The helper records `execution_window.json` outside the native package. A started
window is consumed even if the controller call fails; it cannot be reused in the
same working directory. `CLAIM.json` remains the native controller's local claim.

**The scope of single-use accounting is the local working copy and the first
attempt of a GitHub run.** A distinct manual dispatch creates a new hosted
machine; this implementation is not a global cross-dispatch anti-replay service.
An additional dispatch requires a separate owner review of the retained attempt.
Use the original failed run for diagnosis; do not use **Re-run jobs** or silently
start another dispatch to replace incomplete evidence.

## 5. Result and retained evidence

Replay runs after a capture attempt even when the capture step failed, provided
the runner is still operating. A missing capture is recorded explicitly.
The original capture, claim, logs and native manifest are retained without repair.

`verify-capture` can return exit 0 for a replayable stopped capture. The hosted
finalizer therefore requires all of the following for `CAPTURE_COMPLETED_UNATTESTED`:

- Successful checkout, preparation, verification, image acquisition, capture and replay.
- Matching source/context/request/archive records and successful retained exit codes.
- The exact native claim, including its frozen run ID, attempt and acknowledgement.
- A returned execution window with no recorded interruption.
- Identical controller stdout and retained capture summary, both declaring completion.
- Both completed controls, exactly five sent candidate tokens and five complete cases.
- Offline replay of the retained files agreeing with the saved replay result and
  reporting `RECORDS_CONSISTENT` for the exact request.

Any missing condition produces `INCOMPLETE_OR_BLOCKED`. A possibly started capture
without complete evidence has unknown counters (`null`), never an invented zero.
Zero is used only when the capture step was skipped and there is no execution
window, native claim or capture directory. Sent tokens are not renamed as proven
candidate invocations; original operation records carry the finer observations.

The finalizer writes `RESULT.json`, `ACQUISITION_STATUS.txt` and an outer
`MANIFEST.json` covering all retained files except itself. Hosted helper/workflow
sources are retained with flat, nonhidden filenames. The upload step runs after
both successful and failed guarded attempts, with `if-no-files-found: error`,
`overwrite: false` and 30-day retention.

Expected artifact name:

```text
pd-sm-02-w1-native-<GitHub-run-id>-1
```

`RESULT.json` is written before upload and explicitly does not attest that upload
succeeded. A completed handoff requires both the capture result and a successful
artifact upload in the GitHub job. The archive's outer manifest does not provide
third-party authenticity; the workflow, selected host, Docker daemon, kernel,
image and instrumentation remain trust roots.

Even a completed capture retains these boundaries:

```text
acquisition_authenticity: NOT_EXTERNALLY_VERIFIED
native_witness_observed: null
containment_observed: null
model_native_correspondence: UNRESOLVED
execution_authorized: false
authority_effect: none
```

Here `execution_authorized: false` means that the retained result grants no further
execution permission. The one live controller call separately requires the owner's
request-bound acknowledgement. CI success and preservation alone provide neither
that acknowledgement nor release authority.

## 6. Owner procedure after this implementation is merged

1. Open **Actions → Paradoxon W1 native capture (manual) → Run workflow**.
2. Select **main**. Set `source_commit` to the exact reviewed current `main`
   commit that contains this workflow. The preparation-base commit printed at
   the top of this document predates the new workflow and is not a dispatch SHA.
3. Keep `request_sha256` at its fixed default:
   `655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a`.
4. Enter the acknowledgement below and run the workflow once.
5. Retain the run link and original artifact for review, whether complete or blocked.

```text
I_AUTHORIZE_PD_SM_02_W1:655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a
```

No local Windows Docker setup is needed. No separate rerun of the old admission
workflow is required: the native controller performs its own live controls.
The acknowledgement permits only this fixed diagnostic attempt; it does not
authorize a model run, release, policy change or general candidate execution.

## 7. Implementation verification

The hosted regressions use the unchanged original preparation archive and
explicitly synthetic controller/Docker observations. They cover import bindings,
guard failures, execution-window interruption, false-completion rejection,
missing evidence, path resolution and failed-attempt retention. Existing W1
native and record-checker regressions remain in place.

Local validation used CPython 3.11.16 and pytest 9.2.0:

| Checks | Result |
|---|---|
| New hosted regressions | 120 passed (119 together, then the final source-drift case separately) |
| Existing W1 native/admission and record-checker regressions | 595 passed |
| CI manifest and normative/shadow inventory regressions | 41 passed |
| Total distinct pytest cases | **756 passed; no failures or skips** |
| Actual repository workflow-lint guard | All 70 workflows passed |
| New workflow shell syntax | All 7 shell blocks passed `bash -n` |
| Static script-path and embedded-step guards | Passed |
| Repository Markdown links | 300 Markdown files checked; local links resolve |

The pre-existing W1 test source is retained byte-for-byte around the added block.
Both CI manifests and all five frozen native source files match the preparation
base. These results are local implementation checks, not a new GitHub CI result.
Neither preparation nor these tests dispatch a GitHub workflow, pull an image,
contact Docker or run a W1 candidate. The first hosted native measurement remains
pending an owner dispatch.
