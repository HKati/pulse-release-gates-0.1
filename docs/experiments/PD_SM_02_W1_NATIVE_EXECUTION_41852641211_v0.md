# PD-SM-02-W1 — native execution 41852641211, attempt 1

**Classification:** completed, internally replayed native capture; external authenticity unverified.  
**Open point:** host runner-image provenance discrepancy.  
**Recorded source and preservation preparation base:** `9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0`.  
**Authority effect:** `none`.

## 1. Execution identity and result

This document preserves the first hosted W1 native capture of the fixed
five-case request. The original GitHub artifact remains byte-for-byte unchanged.
The separate review and replay files describe inspection of that artifact;
they do not replace the original capture records.

| Field | Recorded value |
|---|---|
| Repository | `HKati/pulse-release-gates-0.1` |
| Run / attempt | [41852641211 / 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/41852641211) |
| Capture job | [126652755887](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/41852641211/job/126652755887) |
| Source commit | [`9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0`](https://github.com/HKati/pulse-release-gates-0.1/commit/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0) |
| Trigger / owner | `workflow_dispatch` / `HKati` |
| GitHub conclusion | `completed` / `success` |
| Run timestamps, UTC | `2026-11-04T14:56:45Z` to `2026-11-04T14:57:07Z` |
| Reported total duration | 22 seconds |
| Capture status | `CAPTURE_COMPLETED_UNATTESTED` |
| Sent candidate execution tokens / complete case records | 5 / 5 |
| Live supervision controls | `probe-time`, `probe-output`, both completed |
| Offline record result | `RECORDS_CONSISTENT` |
| Request SHA-256 | `655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a` |

All twelve job steps completed successfully, including replay, finalization
and artifact upload. The original `RESULT.json` was written before upload, so
its `artifact_upload: NOT_OBSERVED_BY_THIS_PREUPLOAD_RECORD` field is preserved.
The later successful upload is supported separately by the job log and artifact
metadata recorded in the companion review.

The executed integration and its limits are described by the
[hosted W1 contract at the recorded source](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/docs/experiments/PD_SM_02_W1_HOSTED_NATIVE_v0.md).

## 2. Preserved files and original artifact identity

| File | Role |
|---|---|
| [Original GitHub artifact ZIP](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/pd-sm-02-w1-native-41852641211-1.zip) | Original archive bytes; 322 file members, including its outer manifest. |
| [Original ZIP checksum](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/pd-sm-02-w1-native-41852641211-1.zip.sha256) | SHA-256 of the original artifact, with its original basename. |
| [Capture job log](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/job-126652755887.log) | Unedited UTF-8 representation returned by the GitHub job-log API, including original ANSI characters and newlines. |
| [Offline replay stdout](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/OFFLINE_REPLAY.json) | Exact output bytes of the review-time offline replay. |
| [Preservation review](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/REVIEW.json) | Run/job/artifact bindings, integrity checks, case results and the unresolved provenance finding. |

Original artifact ID: **13334174596**. Original size: **905066 bytes**.

```text
SHA-256: 16c65c69115cdc0c5445f4e471c7c723fc3b6414eb74b5258b84ddc093d2e4c7
```

This digest agrees with the GitHub artifact metadata and upload log. The
retained job-log representation is 40011 bytes, SHA-256
`0475268c6af97f438b96525964f1699b5a9f13eb4493a30f351ca5e42bfbba0b`. The GitHub artifact's recorded expiry is
`2026-12-04T14:57:03Z`; the repository copies preserve the selected evidence
beyond that temporary download window once committed.

The original ZIP already contains the unchanged native request archive,
checksum, staged package, claim, host context, image records, operation
transcripts, cleanup records and both manifests. None is rewritten or repacked
inside the original artifact. The delivery ZIP used to transport these
repository files is a separate wrapper and has a different checksum.

## 3. Integrity and offline inspection

The review checked the original ZIP digest and CRC, all 321 files covered by
its outer manifest, the fixed request and original request archive, and the
exact native sources. A separate copy of the five native verifier sources was
obtained from the recorded repository commit and matched against their bound
SHA-256 values before the local offline replay.

The review-time `verify-capture` used CPython 3.12.14. It returned exit code 0,
empty stderr, `CAPTURE_RECORDS_REPLAYED` and `RECORDS_CONSISTENT`, covering 269
native capture manifest members. Its stdout is byte-identical to the original
artifact's `replay.stdout`; [OFFLINE_REPLAY.json](../evidence/PD_SM_02_W1_NATIVE_41852641211_1/OFFLINE_REPLAY.json)
preserves those exact output bytes. This verification executed zero new
candidates and made no Docker, image-acquisition or workflow-dispatch call.

For a later offline replay, extract a copy of the original artifact into a fresh
directory, obtain the verifier sources from the recorded commit, and run only:

```sh
python -I -S -B /path/to/reviewed-checkout/tools/run_paradox_w1_native_v0.py verify-capture \
  --package /path/to/extracted-artifact/package \
  --request-sha256 655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a
```

The preserved input files remain unchanged during this inspection. The
companion review records source digests and the original/local output comparison;
it is not an externally signed attestation of acquisition authenticity.

## 4. Five-case recorded outcome

| Case | Effects / sink bytes / audit records | Recorded inner relation | Interpretation of retained observations |
|---|---|---|---|
| P00 | 1 / 22 / 1 | `SATISFIED` | Required INTENT, ACK and checks precede the single effect. |
| N01 | 1 / 22 / 0 | `VIOLATED` | The effect occurs without required intent, acknowledgement or audit support. |
| N07 | 2 / 44 / 1 | `VIOLATED` | A second effect for the same request violates single-use support. |
| N08 | 1 / 22 / 1 | `VIOLATED` | The effect completes before the monitor request; later INTENT/audit and ACK do not establish support at the effect. |
| N02 | 0 / 0 / 0 | `NO_EFFECT` | The primitive refuses the direct route before any effect, with `direct_effect_route_not_admitted`. |

All five records are complete and match their frozen predictions. N02's
`PRIMITIVE_REFUSED` terminal is its expected control outcome. The containing
capture and replay complete successfully.

P00 and N08 have the same recorded final sink size and audit count. Their
different relation results depend on support available when the effect
occurred. This comparison is bounded to the five selected records and the
[frozen W1 contract](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/docs/experiments/PD_SM_02_W1_CONTRACT_v0.md).

## 5. Unresolved runner-image provenance

| Evidence source | Exact value |
|---|---|
| Preserved job log, `Runner Image` group, `Version` | `20261025.353.1` |
| Original artifact `host_context.json`, `/github/ImageVersion` | `20261026.354.1` |
| Job log's linked image release | `ubuntu24/20261025.353` |

The two version fields disagree. The release-link spelling is retained
separately and is not substituted for either version. The cause is not
established by this review.

The implemented W1 checks validate the recorded host requirements,
`ImageVersion` syntax and prepare-to-capture continuity. They do not compare
the startup-log version with the environment value. This finding therefore
preserves the existing `CAPTURE_COMPLETED_UNATTESTED` and `RECORDS_CONSISTENT`
results while leaving full runner-image provenance uncorroborated. No new gate
is applied retroactively and no original JSON status is rewritten.

The exact matching Docker image ID
`sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3`
binds the container image. It is a different identity from the host runner image
and does not resolve the host-version disagreement.

## 6. Claim boundary and follow-up

The original result retains:

```text
acquisition_authenticity: NOT_EXTERNALLY_VERIFIED
native_witness_observed: null
containment_observed: null
model_native_correspondence: UNRESOLVED
execution_authorized: false
authority_effect: none
```

This preservation supports inspection of a complete, internally replayed
capture within its stated trust assumptions. It does not establish external
acquisition authenticity, general model/native correspondence, or cyclic-impact
recognition.

The next analysis can examine the five recorded relations and the origin of
the two runner-image values using these retained inputs. This preservation
starts no new attempt and grants no further execution or release permission.
The original run, log and artifact remain the reference for the open provenance
question.
