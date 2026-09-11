# Whole-runtime observation evidence v0

This contract defines the prospective Step 5C current-run whole-runtime
observation mechanism under work order #2879. It does not declare that the
mechanism has already been implemented, acquired, preserved or accepted.

## Scope

`Whole-runtime` does not mean every host process, system call, network event or
provider-internal operation. In this contract it means the complete predeclared
workflow-run, job, source-declared step, selected state, explicit external
operation and controlled model-inference graph of one current-run PULSE CI
hosted release-grade execution within a stated visibility boundary.

The scope identifier is:

```text
one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0
```

The contract does not claim host-wide tracing, complete child-process tracing,
GitHub Action internals, package-manager request completeness, complete network
paths, provider-internal model execution, model-internal state or resource
measurement.

## Role separation

The subject is one exact manually dispatched PULSE CI run:

```text
workflow: PULSE CI
path: .github/workflows/pulse_ci.yml
event/ref: workflow_dispatch / main
strict_external_evidence: true
llamaguard_evidence_mode: hosted_full_runtime
```

The new Step 5C reference workflow is an acquisition supervisor and post-run
collector. It is outside subject totals.

The existing Step 3F workflow is a post-subject producer:

```text
.github/workflows/pulsemech_compute_current_run_export_candidate.yml
```

It consumes the exact completed PULSE CI run and supplies the existing
current-run carrier, expectation and subject-input packet to the existing
compute-binding path.

Step 3G remains a separate artifact-observed analysis workflow and is not
dispatched by the Step 5C reference.

```text
PULSE CI subject
≠ Step 3F export
≠ Step 3G artifact-observed analysis
≠ Step 5C supervisor or collector
≠ independent Step 5C verifier
```

Preparation, dispatch, collection, verification, reconstruction and publication
are not observed subject work.

## Permissions and authority

The acquisition job may receive only:

```text
contents: read
actions: write
```

`actions: write` is used only to dispatch the two reviewed workflows.

The independent verification job receives only:

```text
contents: read
actions: read
```

No repository-content, policy, registry, deployment, package, issue, pull
request, release or publication write permission is introduced.

The subject PULSE CI run may produce its existing release decision. The Step 5C
mechanism neither participates in nor changes that decision.

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

## Reviewed source and dispatch identity

The reference workflow requires one owner-reviewed lowercase 40-hex
`source_commit`. Before preparation, and again immediately before each
dispatch, it requires agreement among:

```text
source_commit input
github.workflow_sha
github.sha
current main head
checked-out HEAD
```

Workflow, policy, registry, controlled LlamaGuard dataset and all other
prelaunch inputs are read from that same source commit.

The subject dispatch uses:

```text
POST repos/HKati/pulse-release-gates-0.1/actions/workflows/pulse_ci.yml/dispatches
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
```

```json
{
  "ref": "main",
  "inputs": {
    "strict_external_evidence": "true",
    "llamaguard_evidence_mode": "hosted_full_runtime"
  }
}
```

The request does not use a `return_run_details` field. The accepted response is
HTTP 200 and contains one positive `workflow_run_id`, an exact API `run_url`
and an exact repository `html_url`, all naming the same run.

After that exact subject reaches `completed / success`, Step 3F is dispatched:

```text
POST repos/HKati/pulse-release-gates-0.1/actions/workflows/pulsemech_compute_current_run_export_candidate.yml/dispatches
```

```json
{
  "ref": "main",
  "inputs": {
    "source_run_id": "<exact subject workflow_run_id>"
  }
}
```

The provider response has the same run-ID and URL requirements.

Latest-run lookup, timestamp correlation, run-list guessing, branch-only
selection and silent attempt substitution are forbidden. A malformed response,
URL/run-ID disagreement, changed `main`, wrong repository, workflow, ref, input
set, source commit or attempt is an acquisition error.

## Bounded acquisition

Every API call, poll, page and download is finite. The v0 implementation uses
checked-in bounds no weaker than:

```text
single API request: 60 seconds
subject wait: 90 minutes
Step 3F wait: 45 minutes
jobs: 64
platform step records: 2048
artifacts: 256
single API JSON body: 16 MiB
single downloaded artifact envelope: 768 MiB
aggregate downloaded artifact envelopes: 1536 MiB
capture members: 8192
capture uncompressed bytes: 2048 MiB
```

Pagination must close explicitly. Every response is untrusted input and is
subject to strict size, JSON-shape, duplicate-key, number, identifier and URL
validation.

Timeout, cancellation, rate-limit exhaustion, malformed data, incomplete
pagination or failed download produces no accepted carrier.

## Prelaunch plan

The expected graph is built and independently validated before subject
dispatch. The plan binds exact bytes for:

```text
PULSE CI workflow
Step 3F workflow
this contract and its schema
policy and gate registry
external signer and threshold policies
controlled LlamaGuard case dataset
selected action pins
selected dispatch inputs
reviewed source commit
```

It records the scope, workflow identity, job and step templates, raw conditions,
`needs` relations, stable occurrence IDs, state roles, required consumers,
terminal roles, external-operation classes, inference templates, privacy and
trust boundaries, finite limits and authority boundary.

It contains no future run ID, job database ID, artifact ID, timestamp, output
digest, PASS verdict or release decision.

The independent plan checker reconstructs the plan from exact source bytes. It
does not import or trust the plan builder. A plan derived from observed jobs,
steps, artifacts or outputs is invalid.

## Stable occurrence IDs

```text
job:
execution:step5c:job:<source-job-id>

source-declared step:
execution:step5c:step:<source-job-id>:<three-digit-source-ordinal>

collector:
execution:step5c:collector:post-run-platform-export

model inference:
inference:step5c:llamaguard:<case-id>

external operation:
call:step5c:<source-job-id>:<source-step-ordinal>:<operation-role>
```

Step ordinals come from exact workflow source order, not GitHub-generated runtime
step numbers. Duplicate identifiers are rejected.

## Reference-profile topology

The `pulse_ci_hosted_release_grade_v0` profile contains:

| Source job ID | Required result | Step templates |
| --- | --- | ---: |
| `pulse` | `success` | 83 |
| `attest_release_authority_artifact_binding` | permitted `skipped` | 2 |
| `attest_llamaguard_current_run_summary` | `success` | 8 |
| `release_grade_recorded_path` | `success` | 33 |
| `attest_release_grade_artifact_binding` | `success` | 2 |
| `assemble_release_grade_reference_package` | `success` | 6 |
| `verify_release_grade_reference_package` | `success` | 8 |
| `tools-tests` | `success` | 5 |

The selected path has:

```text
8 job templates
7 successful jobs
1 permitted skipped job
147 source-declared step templates
145 instantiated source-declared steps
101 successful step occurrences
44 permitted skipped step occurrences
2 uninstantiated steps under the skipped job
```

The core artifact-binding attestation job may be skipped only because its exact
source condition evaluates false for the selected hosted release-grade dispatch.
The later release-grade artifact-binding attestation job must succeed.

Any future topology change requires a reviewed profile decision. It is not
silently admitted because a parser can read it.

## Platform lifecycle records

GitHub-generated setup, post-action cleanup and completion records are preserved
in the raw response but excluded from the source-declared E totals.

The matcher first accounts for every planned source-declared step in source
order. Every remaining platform step must match a narrow reviewed lifecycle
allowlist derived from the action structure. Broad prefix matching is not
sufficient.

An unmatched non-lifecycle step, or a lifecycle record used to replace a missing
declared step, is an acquisition error.

## Terminal semantics

Every planned occurrence ends as one of:

```text
success
permitted skipped
failure
cancelled
timed out
launch failed
missing
unknown
```

Only `success` and a conditionally justified `permitted skipped` state satisfy
this profile. A required skipped occurrence and a permitted-skipped occurrence
that unexpectedly runs both fail closure.

The subject and provider must each use attempt 1. A rerun is a new acquisition,
not a continuation of the accepted one.

## Source and command identity

Workflow, policy, registry, dataset and repository-tool source states bind to
exact committed bytes.

A GitHub Action identity is exact only when a full immutable action commit SHA
is present in the workflow and plan.

A shell step may have an exact source command template because its complete
`run:` block is bound. That does not prove every child process, imported module
or executable byte opened later.

A directly launched repository tool has exact committed-file identity. Executed
byte identity remains partial unless a sealed-source, descriptor-bound or
equivalent mechanism proves that the verified bytes are the executed bytes.

Display names, environment values, log lines, path strings, self-declared
revisions and equal output content do not become exact execution identity.

## Observation granularity

| Layer | Step 5C state |
| --- | --- |
| workflow run | completely predeclared |
| jobs | completely predeclared |
| source-declared workflow steps | completely predeclared |
| platform lifecycle steps | retained as metadata; excluded from E |
| direct child processes | not claimed complete |
| selected state transitions | included where exact state identity exists |
| external operations | invocation boundary; internals may remain partial |
| controlled model inference | six exact case occurrences |
| resource measurement | unavailable |

A complete workflow/job/step graph is not complete host tracing. An action
invocation is not its internal process graph. A recorded model boundary is not
provider-internal execution.

## Run, job and step evidence

The observer preserves the exact subject run response and every jobs page for
the exact run and attempt. It verifies repository, workflow identity, event,
branch, source SHA, run ID/number/attempt, status, conclusion, URLs and times.

Each job binds its database ID, source job ID, run identity, terminal result,
times and runner labels. Each declared step binds its parent job, source ordinal,
source name and condition to the corresponding platform name, result, times and
source order.

Platform timestamps are platform metadata, not cryptographic authentication of
the hosted runner or GitHub control plane.

## States and consumption

The packet records exact or explicitly unavailable identities for applicable
workflow, policy, registry, evidence, status, attestation, decision, authority,
ledger, package, verification and Step 3F carrier states.

Each state records its semantic ID, type, role path or URI, content status,
digest and size where available, producer, observer, subject run, candidate,
policy/gate relation, authority-bearing status, mutation class, observation time
and secret-material status.

The observer may produce only advisory or preservation outputs. Subject-produced
final status, gate materialization and release decision remain owned by the
subject.

A consumption relation closes only when the designated consumer uses the exact
state from the exact producer occurrence. Equal bytes from another occurrence,
same filenames from another run, observer-only reads, producer self-reads or
unrelated reads are insufficient.

Step 5C does not declare whole-runtime relational coverage complete merely
because job and step extent closes. Remaining relation closure belongs to
Step 5D.

## Artifact boundary

The complete subject artifact metadata listing is preserved. Exact bytes are
required for selected terminal roles; redundant artifacts need not all be
downloaded where a verified carrier already preserves their bytes.

At minimum the exact Step 3F provider artifact must preserve and bind:

```text
complete release-grade reference package
structural package-completeness report
independent package-verification report
```

For every selected artifact the checker verifies ID, name, source run and
attempt, created/expiry time, expired state, size, GitHub SHA-256, downloaded
SHA-256 and downloaded byte count.

Expired, missing, duplicate, renamed, cross-run or digest-mismatched artifacts
are rejected. Upload success alone is not semantic validity.

## External operations

The plan identifies explicit GitHub dispatch, run/job/artifact retrieval,
artifact upload/download, checkout, setup-python, attestation and attestation
verification boundaries, plus package installation and Hugging Face model
revision/file acquisition boundaries.

The two dispatch calls belong to the supervisor, not the subject.

Subject-side operations use the strongest supported state:

```text
exact digest
metadata only
not recorded
```

No record is not proof of no call. Package-manager requests, action-internal
calls, DNS, transport paths and provider internals remain explicit gaps unless
separate evidence supports them. Authorization material, cookies and secrets
are never included.

## Controlled model inference

The exact checked-in dataset fixes six case occurrences before dispatch:

```text
benign_factual_response
violent_harm_refusal
credential_theft_refusal
private_address_refusal
self_harm_support
hate_content_refusal
```

Each inference binds the case ID, input/output state digests, model ID and exact
revision, runtime package identities, generation parameters, token counts,
parsed label/category set, response-metadata digest and parent step.

Step 5C JSON does not copy raw prompt text or raw model output. The existing
controlled source artifact may remain an opaque exact preservation input but is
not expanded into Step 5C logs or JSON.

Per-case start/completion time remains partial unless directly recorded. Token
counts are inference-usage evidence, not complete resource measurement.

## Timing and order

The packet distinguishes GitHub platform, tool-recorded, provider-reported,
derived and unknown time. Its cross-source clock state is:

```text
not_verified
```

Exact order requires source order, `needs`, same-source platform order, exact
producer-consumer state identity or another predeclared structural dependency.
Different clock domains do not establish order by timestamp alone. Estimated
duration is never represented as exact.

## Generic runtime packet

Step 5C derives one unchanged-v0 runtime packet:

```text
record_status: observed
packet_scope: subject_run
collection_mode: post_run_platform_export
packet_sequence: 0
previous_packet_sha256: null
```

Expected counts are:

```text
subject workflow jobs: 8
subject declared steps: 145
subject execution records: 153
collector execution records: 1
total execution records: 154
model inference records: 6
resource measurement records: 0
```

All records bind:

```text
GITHUB_RUN_ID=<exact subject run ID>
|GITHUB_RUN_ATTEMPT=1
|GITHUB_WORKFLOW=PULSE CI
```

The collector remains outside subject totals and does not mutate subject
artifacts.

The generic runtime schema and validator remain unchanged. Because resource
axes are unavailable and runtime internals remain explicitly excluded, generic
`coverage_status` stays `partial`. Empty resource arrays mean unavailable, not
measured zero.

## Separate Step 5C evidence contract

The new closed schema has discriminated records for:

```text
prelaunch_plan
dispatch_receipt
capture_manifest
verification_record
```

It binds the exact plan, both dispatch receipts, raw run/job/artifact responses,
selected artifact bytes, Step 3F output, generic runtime packet, existing-core
derived outputs, independent verification and two reconstructions.

This outer contract separates Step 5C I/E from the generic packet's aggregate
coverage semantics:

```text
I — acquisition and packet integrity: complete, if verified
E — selected declared observation extent: complete, if verified
R — whole-runtime relational coverage: partial
C — wider fixed-source/runtime comparison: false
M — resource coverage: unavailable
```

I/E completion never changes the generic packet to `coverage_status: complete`.

## Carriers

The prepared carrier contains the validated plan, plan diagnostic, exact source
inventory and bytes, selected dispatch inputs and expected plan digest.

The capture carrier contains both dispatch requests/responses, subject and
provider run responses, paginated job/artifact responses, exact downloaded
provider envelope and a self-closing capture manifest. It contains no verifier
verdict.

Each deterministic reconstruction contains the generic runtime packet and
diagnostic, compute-binding report and diagnostic, planned-observed relation and
diagnostic, candidate-materializer report, folded non-active status and
reconstruction inventory.

The final reference capsule contains exactly:

```text
prepared.zip
capture.zip
expected_context.json
expected_plan.sha256
reconstruction-1.zip
reconstruction-2.zip
verification_record_v0.json
SHA256SUMS
```

`SHA256SUMS` lists the other seven members in filename order and not itself. The
two reconstruction ZIP payloads must be byte-identical.

All ZIPs are `ZIP_STORED`, lexicographically ordered, timestamped
`1980-01-01 00:00:00`, fixed-mode regular files with no directory entries,
links, encryption, comments, extra fields or duplicate names.

JSON is UTF-8 without BOM, duplicate-key and non-finite-number rejecting,
NFC-normalized, sorted-key, two-space-indented and final-LF terminated.

Verification never extracts an archive. Unsafe names, traversal, absolute paths,
backslashes, NULs, unsupported compression, CRC failures and size violations
are rejected.

## Independent verification and reconstruction

The plan checker does not import the plan builder. The Step 5C checker does not
import the acquisition, capture or plan-builder implementation.

It independently verifies source objects, plan reconstruction, dispatch
receipts, subject/provider identity, jobs and steps, conditions and skips,
lifecycle exclusion, artifacts, Step 3F binding, states, external visibility,
six inferences, privacy, collector separation, runtime-packet validity,
existing-core outputs, authority boundary and carrier closure.

A self-declared carrier proves internal consistency only. Original acquisition
acceptance also requires the exact GitHub reference-workflow run and its external
workflow identity to be reviewed.

Reconstruction uses one fixed prepared carrier and one fixed capture carrier. It
does not dispatch workflows, repeat model inference, invent observations,
normalize raw bytes, use the current clock, use randomness or depend on ambient
environment values.

Two separate processes reconstruct all derived bytes. Any mismatch fails the
reference.

## Terminal closure

E is complete only when the independently validated plan is fixed before
dispatch; exact subject and provider receipts exist; both runs use attempt 1 and
succeed; all eight jobs, 145 instantiated declared steps and six inference
occurrences match their planned terminal states; no expected occurrence is
missing, duplicated or conflicting; no unexpected non-lifecycle step exists;
required artifact roles and bytes close; Step 3F binds the exact subject; the
collector remains separate; the unchanged runtime validator accepts the packet;
and two reconstructions are byte-identical.

Workflow success, a final marker or an empty missing list is insufficient unless
the checker derives closure from the prelaunch plan.

Cancellation, timeout, launch failure, missing/unknown state, cross-run
substitution, incomplete pagination or incomplete artifacts prevents E
completion.

## Fail-closed publication

At minimum the implementation rejects source, plan, input, dispatch, run,
attempt, job, step, condition, lifecycle, action, command, authority-source,
artifact, provider, inference, model, privacy, collector, mutation, resource,
coverage, output-path, reconstruction and authority-boundary mismatches.

No failed acquisition publishes a closed reference carrier.

Publication is external to the source repository and occurs only to an absent
destination. Existing output is never overwritten, truncated, renamed away or
deleted. A no-replacement primitive is required; unsupported filesystems fail
without a mutable fallback.

## Existing-core integration

The exact Step 3F packet/carrier and Step 5C runtime packet flow through:

```text
build_pulsemech_compute_binding_report_from_subject_input_v0.py
→ pulsemech_compute_binding_analyzer_core_v0.py
→ check_pulsemech_compute_binding_report_v0.py
→ build_pulsemech_compute_planned_observed_relation_v0.py
→ check_pulsemech_compute_planned_observed_relation_v0.py
→ fold_pulsemech_compute_planned_observed_relation_into_status_v0.py
```

No second analyzer, report implementation, relation engine or candidate
derivation is introduced. The report preserves exact subject identity, collector
separation, partial generic coverage, unavailable resources and actual unresolved
relations.

An all-true candidate is not required. Step 5C output is not an active policy
input.

```text
authority_binding_complete: false
decision_closure_complete: false
```

## Privacy and trust

Step 5C JSON, diagnostics, summaries and logs exclude secrets, authorization
headers, tokens, cookies, raw environment, raw request/response bodies, raw
prompt text, raw model output, uncontrolled command strings and private or
arbitrary user content.

```text
opaque_controlled_fixture_payloads_present: true
step5c_json_exposes_raw_prompt_text: false
step5c_json_exposes_raw_model_output: false
private_or_arbitrary_user_prompt_admitted: false
```

The trusted boundary includes the reviewed supervisor, plan builder, independent
plan checker, acquisition/capture tools, independent Step 5C checker, selected
CPython runtime, hosted runner, host kernel, GitHub control plane and existing
PULSE CI and Step 3F components.

It does not prove correctness against a compromised privileged host, runner,
interpreter, recorder, GitHub control plane or provider internals. Independent
reconstruction proves deterministic derivation from preserved inputs, not a
repeat of the original execution.

## Tests and handoffs

Permanent tests use `record_status: example`, deterministic mocked API responses
and bounded local carriers. They do not dispatch live workflows and are not
observed Step 5C evidence.

Keep the handoffs distinct:

```text
accepted mapping
→ contract and implementation
→ permanent regressions
→ implementation review and merge
→ reviewed owner dispatch
→ exact acquisition
→ independent validation and two reconstructions
→ preservation
→ Step 5C acceptance
→ canonical documentation synchronization
```

The implementation PR contains no invented future run, job, artifact, time,
size, digest or PASS value. The actual reference is preserved only after a
separate acquisition review.

Step 5C does not modify PULSE CI release semantics, the generic checker,
production policy, active policy sets, gate registry, existing #6066 evidence,
Step 5B evidence, Quality Ledger, Transition Meter, Device Ledger, iPhone code,
v1.3.0 or publication metadata.

Successful accepted Step 5C evidence may establish I and E only within the
declared scope. R and C remain Step 5D work; M remains Step 6 work. It does not
declare complete Step 5, whole-host observation, compute budgeting, deployment
admission, active compute enforcement or Step 7 promotion.

Refs #2879.
Builds on #2870, #2872, #2875, #2876, #2877 and #2878.
