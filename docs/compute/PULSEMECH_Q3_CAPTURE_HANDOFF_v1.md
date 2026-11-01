# Q3 mandatory capture handoff v1

Status: implementation and offline regression package; no native dispatch or
reference acceptance is established by this document.
Preparation base: `ff37da8d62ae570d287baac0e265f0dc8c6b8dd5` (after #2971).
Tracking: #2879 remains open.

## Purpose and explicit migration decision

Connect the existing read-only acquisition component and offline comparator to
the actual native capture entry. A copied comparison verdict or unsigned saved
acquisition receipt cannot admit a capture. The reviewed controller acquires the
selected original records again and consumes the result in that same process.
There is no new third-party adjudicator, signing service or policy evaluator.

The public execution entry remains
`PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py`, called by the existing
manual `.github/workflows/q3_reference_acquisition_v0.yml` workflow. Both its CLI
and the workflow now require a `q3_capture_handoff_request_v1` envelope for capture.
A bare native-v0 capture request rejects with `CAPTURE_HANDOFF_REQUIRED`.
Native-v0 token-preflight requests retain their existing route.

The native-v0 request/profile/result schemas, worker, runtime, checker and
request constructor remain unchanged. The constructor can still produce the
inner capture request; that request is no longer a sufficient dispatch input.
The existing v0 documentation's bare-capture dispatch instruction is superseded
by this envelope procedure. Historical v0 evidence remains readable by its
original source-bound checker. No historical source snapshot is rewritten.

This is a versioned admission and preservation envelope, not an unversioned
extension of a closed native-v0 schema. The workflow name, three dispatch inputs,
action pins, permissions, upload names and retention remain unchanged.

## Source and request binding

The native controller still verifies and holds the complete 21-path native
source closure against the exact checked-out commit. For capture it additionally
checks four paths against that commit before compiling any new helper:

```text
schemas/metrics/q3_capture_handoff_request_v1.schema.json
tools/acquire_q3_external_postflight_v0.py
tools/check_q3_external_postflight_v0.py
tools/q3_capture_handoff_v1.py
```

The helper and both components execute from captured source bytes, not unchecked
imports or cached bytecode. The acquisition and comparison components stay
byte-identical to #2971/#2966. Their reviewed digests are fixed in the helper:

```text
acquirer:
35b875e6885f56cfe601ae27c92f9acd98e8ddc8805aaeb498157ff7b04e7065
comparator:
a0bbeb20ae368992883747277946f78a4926ffd71a276756ee611a81a047d16b
```

The new closed schema has exactly nine fields:

| Field | Meaning |
| --- | --- |
| `record_type` | `q3_capture_handoff_request_v1` |
| `repository` | Fixed `HKati/pulse-release-gates-0.1` |
| `capture_source_commit` | Exact capture commit, 40 lowercase hexadecimal characters |
| `native_request_utf8` | Original inner native-v0 capture request bytes represented as UTF-8 text |
| `native_request_sha256` | Independently selected digest of those exact bytes |
| `postflight_selection_utf8` | Original acquisition-v0 selection bytes represented as UTF-8 text |
| `postflight_selection_sha256` | Independently selected digest of those exact bytes |
| `handoff_source_files` | Exact SHA-256, Git blob SHA-1 and byte length of the four additional sources |
| `authorization` | Exact capture-envelope consent below |

```text
AUTHORIZE_ONE_OWNER_CAPTURE_DISPATCH_WITH_FRESH_POSTFLIGHT_AND_30_DAY_RETENTION
```

The original native capture authorization and fixed limits are also required in
the inner request. Whole-envelope bytes are separately hashed for the existing
`native_request_sha256` workflow input. The outer and inner request hashes have
different roles; neither replaces the other. Duplicate keys, additional fields,
unsupported identities and incorrect byte bindings reject.

Preflight and capture retain distinct run identities and may have distinct
commit identities. This version requires every native source path's actual bytes
to match the selected preflight's source inventory. A changed native tool,
workflow, input or profile cannot reuse a preflight merely because its token-map
hash was copied. An unsupported source change requires a new preflight, not an
approval override. The four handoff-only sources have their own capture binding;
they are not retroactively inserted into the old native profile.

Because this increment changes the native controller, the previous historical
preflight does not satisfy that source equality. Its already recorded image
contradiction also remains blocked. Prepare a fresh preflight only from the
final reviewed, merged source, under separate owner authorization.

## Mandatory live sequence

```text
existing owner/main/attempt/source/request entry guard
→ exact four-file handoff source binding
→ closed v1 envelope and inner-v0 validation
→ current owner-dispatch control-plane verification
→ exclusive current run/attempt output claim
→ current capture-run metadata observation
→ exact selected preflight metadata and original payload acquisition
→ post-download metadata recheck and unchanged offline comparison
→ current capture-run metadata recheck
→ in-process admission bound to this capture request/source/run
→ unchanged native capture core
→ native carrier reconstruction
→ composite preservation and complete-carrier reconstruction
→ exclusive final publication
```

The comparison must be `CONSISTENT_OFFLINE`; its exit 2 and all acquisition
failures stop before the native core is invoked. No model load, tokenization or
generation is attempted by the handoff helper on that rejected path. No fallback
to a saved acquisition directory, historical PASS, latest successful run or
alternative provider exists.

Current capture metadata must describe the selected in-progress manual main run,
owner and triggering owner, exact source and attempt 1. Its run ID must differ
from the selected preflight. No future run ID is invented in the request.
The native core also retains its own current-main/control-plane check.

The final output directory is created exclusively before acquisition and is
never removed to permit another invocation. This is a local same-run claim, not
a globally persistent single-use credential service. Rerun attempts greater than
1 remain rejected. A new owner-created workflow dispatch is a distinct explicit
execution authorization and must perform fresh acquisition again; the same
request bytes are not claimed to be globally unusable across owner dispatches.
There is no automatic retry or outcome-dependent top-up.

Freshness here means observations acquired during this controller invocation,
followed by immediate in-process admission and invocation of the native core.
It does not assert synchronized GitHub/local clocks, identical preflight/capture
platforms, protection from malicious root, or zero time between admission and
model execution. The native model/input/configuration checks and token-map
comparison remain mandatory within the unchanged core.

## Preservation format and failure behavior

The existing workflow still uploads only `evidence.zip`, `receipt.json` and,
on failure, `failure.json`. For a capture through this route their outer record
format is v1. The original native-v0 archive/receipt are retained unchanged inside
that envelope rather than passed off as the outer v1 archive.

A complete `evidence.zip` contains:

```text
request.json                         exact v1 dispatch envelope
capture-source/<21 native paths>     capture source snapshot
handoff-source/<4 additional paths>   reviewed handoff snapshot
capture-run.before.json
capture-run.after.json
postflight/<13 original/output files>
admission.json                       current-dispatch diagnostic record
native/evidence.zip                  unchanged native-v0 carrier
native/receipt.json                  unchanged native-v0 receipt
bundle.json                          closed inventory and terminal disposition
```

The thirteen postflight files are `selection.json`, `run.json`, `jobs.json`,
`artifact.json`, `artifact.zip`, `job.log`, `run.after.json`, `jobs.after.json`,
`artifact.after.json`, `expectation.json`, `comparison.json`, `acquisition.json`
and `inventory.json`. The embedded acquisition receipt records nine logical
transfers: the initial current-run read plus the eight original acquisition
reads. Its postflight byte inventory excludes itself exactly as before. The
later current-run read is retained separately, not silently inserted into that
already finalized receipt.

A failed acquisition preserves complete responses already written where possible;
it does not invent missing or truncated HTTP bodies. A failure after native
invocation remains `incomplete`, with any available original native files retained.
Final reconstruction failure cannot produce a complete receipt. A cleanup or
preservation failure cannot be converted into successful completion.

Private staging is removed only under its retained directory identity. Final
publication uses exclusive file creation, retained identities, mode/custody checks
and byte readback. Existing outputs are never overwritten. Storage failure,
process kill, cancellation or host loss can prevent a final failure carrier;
absence is not evidence of no execution or successful cleanup. The native core's
own bounded lifecycle/cleanup behavior is unchanged.

| Controller exit | Meaning |
| --- | --- |
| 0 | Complete capture, composite reconstruction and final publication succeeded |
| 1 | Native execution, cleanup, final reconstruction or preservation was incomplete |
| 2 | Entry/admission rejected, or final publication unavailable |

Preserved `status=rejected` identifies an admission denial before invoking the
native core. No exit code is a Q1/Q3 metric verdict or release decision.

## Independent reconstruction

`tools/q3_capture_handoff_v1.py check-carrier` requires independently selected
outer archive SHA-256, envelope SHA-256, capture source and capture run ID. Its
implementation must be read from that exact committed checkout. It verifies the
closed inventory, selected source closures, nested request/selection bindings,
before/after metadata and transfer-byte bindings; reconstructs the unchanged
external comparison; and invokes the existing separately implemented, hash-pinned
native checker on the original nested carrier. It rejects a false complete
wrapper even after its inventory has been coherently rehashed.

The check does not execute the archived capture controller, download records,
reinstall dependencies, tokenize, load a model or generate responses. An
incomplete/rejected carrier produces a non-complete inventory result, not a
fabricated complete execution reconstruction. Local saved records are unsigned:

```text
saved_record_authenticates_origin = false
verifier_execution_attested = false
artifact_attempt_attestation = null
live_origin_reobserved = false
new_execution_authorized = false
authority_effect = none
production_gate_eligible = false
current_run_evidence = false
policy_activation = false
metric_evaluated = false
```

These limits distinguish offline reconstruction from the actual controller's
live transport observation. The saved admission record is never accepted as a
permission input. Organizationally independent approval is not substituted for
this mechanism, and an unsigned JSON field is not called origin attestation.

## Owner procedure after implementation acceptance

No executable request or dispatch permission is supplied by this source package.
After the final merge, use the existing zero-generation preflight procedure on
the exact reviewed source. Reconcile its actual original artifact and retained
records before selecting the preflight identities for capture.

Create the inner native-v0 capture request using its existing constructor, with
the separately selected verified token-map digest and original capture consent.
Then construct the v1 dispatch envelope without network access:

```sh
python -I -B tools/q3_capture_handoff_v1.py build-request \
  --repo-root /absolute/exact-reviewed-checkout \
  --source-commit ACTUAL_CAPTURE_SOURCE_COMMIT \
  --native-request /absolute/native-capture-request.json \
  --native-request-sha256 INDEPENDENT_NATIVE_REQUEST_SHA256 \
  --selection /absolute/preflight-acquisition-selection.json \
  --selection-sha256 INDEPENDENT_SELECTION_SHA256 \
  --authorization AUTHORIZE_ONE_OWNER_CAPTURE_DISPATCH_WITH_FRESH_POSTFLIGHT_AND_30_DAY_RETENTION
```

This command writes request bytes to stdout only. Hash the exact emitted bytes,
including their final newline. The existing workflow's `native_request` takes
that whole v1 envelope, and `native_request_sha256` takes its hash. The
`source_commit` input names the exact capture commit. Do not dispatch the inner
native request directly, reuse a pre-merge request or infer future run IDs.

After the separately authorized capture, retain the actual original outer Actions
ZIP and extract the selected v1 `evidence.zip` without confusing their hashes.
Verify the latter with independent anchors:

```sh
python -I -B tools/q3_capture_handoff_v1.py check-carrier \
  --repo-root /absolute/exact-capture-checkout \
  --archive /absolute/preserved/evidence.zip \
  --expected-archive-sha256 SELECTED_V1_EVIDENCE_ZIP_SHA256 \
  --expected-request-sha256 SELECTED_V1_ENVELOPE_SHA256 \
  --expected-source-commit ACTUAL_CAPTURE_SOURCE_COMMIT \
  --expected-run-id ACTUAL_CAPTURE_RUN_ID
```

Successful offline reconstruction does not dispatch another capture. Both
commands require the existing POSIX/no-follow/Git environment. No new runtime
dependency, repository-write token or workflow permission is introduced.

## Bounded tests and the remaining measurement

Regression tests extend the already registered Q3 postflight test module. Both
CI manifests stay unchanged at 174 Tools entries and 30 targeted-pytest entries.
Existing comparator/acquisition tests and the historical archive remain intact.
Tests use explicitly synthetic HTTP and native execution responses, including
an exact locally committed source closure and the actual entry/request parsers.
They do not establish live provider acquisition, hosted containment, new native
inference or mathematical correctness of human-supplied labels.

This package closes the implementation-level capture admission connection on
the supported controller CLI/manual workflow. The internal `execute` function
is retained as a native-core/test seam, not a public admission API. An arbitrary
Python caller that deliberately imports internal functions, a modified workflow,
or privileged code executing the worker directly is outside this trusted-process
boundary; no language-level access-control or hostile-host guarantee is claimed.

The next empirical steps are the separately authorized fresh preflight and
capture, exact preservation, fixed Q1 annotation inputs, then the existing Q3
producer and independent checker. Capture does not create Q1 labels or score Q3.
A correctly reconstructed negative metric is an admissible measurement outcome;
incomplete evidence is not. No new annotation policy, release gate, production
eligibility, Step 5C completion, resource measurement or promotion follows from
this implementation merge. Keep #2879 open.
