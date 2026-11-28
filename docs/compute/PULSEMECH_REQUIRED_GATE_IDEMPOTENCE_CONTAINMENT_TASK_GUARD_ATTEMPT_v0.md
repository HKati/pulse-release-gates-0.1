# B2 selected containment task-guard attempt v0

## Status and purpose

This unit implements the single-attempt adapter following the
[probe build and context selection](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_SELECTION_v0.md)
merged in [PR #3064](https://github.com/HKati/pulse-release-gates-0.1/pull/3064).
Its exact development base is
`8036eccdf403a770e9f63f8b6fd6d0a123acc0eb`.

The adapter joins a separately acknowledged request to the unchanged
[21-case qualifier](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_QUALIFICATION_v0.md).
It freshly reconstructs the selected inputs, compares the actual observer
context, invokes the qualifier at most once and preserves the request, original
inputs, attempt record and available raw qualification bytes together. The
independent checker reconstructs those relationships from the preserved bytes.

Development validation uses authored raw records and substituted backends. It
does not execute a native probe, startup helper, original launcher, static entry,
selected runtime, container or workflow. The implementation supplies no actual
qualification result. Native acquisition and its complete execution procedure
require a later owner-reviewed step.

Keep `b2_complete=false`, `metric_pass=null`, `authority_effect=none` and
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Files and responsibilities

| File | Responsibility |
| --- | --- |
| [Attempt adapter](../../tools/run_required_gate_idempotence_containment_task_guard_attempt_v0.py) | Reserve owned output, admit the request, sample the current context, invoke the unchanged qualifier once and preserve the available evidence. |
| [Independent checker](../../tools/check_required_gate_idempotence_containment_task_guard_attempt_v0.py) | Reconstruct the request, selection and raw qualification without importing the adapter, preparer or native qualifier. |
| [Closed schema](../../schemas/required_gate_idempotence_containment_task_guard_attempt_v0.schema.json) | Define request, attempt and verification-report shapes; semantic admission remains the checker's responsibility. |
| [Registered regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Append scripted, byte-reconstruction and filesystem-failure cases while retaining the complete previous test prefix. |

The new source inventory freezes all sixteen implementation, policy and schema
inputs selected by #3064, then binds the new adapter, checker and schema. Earlier
source contracts, qualifier behavior, build policy and evidence meanings remain
unchanged. No workflow or test-manifest entry is added.

## Request and admission order

The caller supplies the exact selection, build record, probe and policy bytes,
with four external SHA-256 selections. A request retains both the actual input
bindings and those caller-supplied expectations, along with its identifier,
execution mode, source inventory, finite limits and explicit acknowledgement.
Constructing this request does not admit mismatched inputs.

The runtime acknowledgement is:

```text
QUALIFY_CONTAINMENT_TASK_GUARD_ONLY
```

Its presence inside the saved selection is not authorization to execute. The
adapter requires it separately at the invocation boundary. The string does not
authenticate the human owner or grant a reusable permission for later runs.

The admission sequence is:

1. Check the separate acknowledgement and reject a substituted context reader
   unless an explicit backend is also supplied.
2. Construct the bounded request and reserve a new owned output directory and
   fixed file set. Existing files or directories are not overwritten.
3. Preserve and close the exact input files and request before acquisition.
4. Freshly verify the request through the existing selection checker, including
   the repeated build, policy, probe and full prerequisite source contract.
5. Require `recorded_build_and_local_context` for the default native route.
6. Read and freeze the actual context; compare its complete canonical bytes with
   the selected context, including boot, namespace, executable and security
   identities. A second source snapshot is checked immediately before invocation.
7. Increment the recorded invocation count and call the unchanged qualifier once
   with the selected probe and environment digests. The qualifier independently
   checks its context before preparing its observer.
8. Preserve the returned raw bytes, recheck context and source identities, and
   independently replay complete evidence before publishing a completed attempt.

The public API supports an explicitly injected backend for development tests.
Any supplied backend is scripted, even an object whose class is `NativeBackend`.
A substituted context reader cannot silently retain the default native route.
The independent checker requires the request mode, selection origin and raw
qualification origin to agree.

The one-call limit applies to one adapter invocation and newly reserved output
set. There is no global ledger consuming a selection ID. Reusing a selection in
another separately authorized process is not prevented or represented as global
single-use enforcement.

## Preserved bundle

The output is a new flat directory. All files use private creation permissions;
the selected binary is preserved as data. The exact permitted membership is:

| Name | Maximum bytes | Meaning |
| --- | ---: | --- |
| `request.json` | 131,072 | Exact requested inputs, external expectations, source inventory and limits. |
| `attempt.json` | 131,072 | Recorded admission, invocation, completion and failure state. |
| `selection.json` | 65,536 | Original selected build/probe/context relationships. |
| `build_record.json` | 2,097,152 | Original repeated compile-only build record. |
| `probe.elf` | 262,144 | Exact selected probe bytes; no replacement build is performed. |
| `policy.json` | 65,536 | Original explicitly accepted limited build policy. |
| `qualification.json` | 33,554,432 | Exact returned raw record, present only when available. |

The unchanged qualifier retains its own 21-case roster, 120-second observation
budget, five-second per-case and cleanup budgets, event/byte limits and owned-task
cleanup obligations. The adapter adds no retry or alternate probe path.

The attempt records `invocation_count` as zero or one, a separate preflight
result, before/after context and source observations, the raw record's binding,
its replay state, the primary failure, cleanup failures and whether the observer
must terminate. A producer's `completed` value alone cannot establish acceptance.

## Incomplete and fatal outcomes

| Recorded situation | Meaning |
| --- | --- |
| Rejected selection or context, zero invocations | The available request/input prefix is retained. Invalid admission inputs do not acquire an accepted verification report. |
| Qualifier raises without a raw record | One invocation is recorded; raw evidence is unavailable and completion is false. |
| Raw record is incomplete | Its bounded original bytes remain preserved; complete qualification is false. |
| Raw record cannot be replayed | Bytes remain diagnostic evidence only; `qualification_verification=rejected`. |
| Owned tasks remain unresolved | Preserve the available prefix, require observer exit and prevent completion in either execution mode. |
| Output replacement, partial publication or close failure | Invalidate only the owned completion inode. Unrelated replacements are preserved; an incomplete filesystem prefix may remain unverifiable. |

The unchanged qualifier can raise `ObserverExitRequired(record)`. The adapter
also recognizes the explicit unresolved-observer cleanup marker or retained
unresolved tasks in a returned record, including a scripted-origin result. It
preserves the available raw record with `qualification_verification=not_checked`
and propagates its own fatal exception. It does not spend another full replay
cycle delaying termination while tasks remain unresolved.

The native CLI is the disposable observer. Its final action on this path is
`os._exit(1)`, even if publication or descriptor cleanup fails. The qualifier's
EXITKILL mechanism depends on actual observer termination; returning a normal
error is insufficient. A library caller must honor this fatal exception by
terminating its disposable observer. Exit itself is not evidence of successful
task removal.

Output parents and members are opened without following caller-controlled
symlinks. Publication checks owned inode identities, exact member names and
actual bytes, including public-path rechecks. Immutable inputs and raw evidence
close before the final attempt is published. Late failures invalidate the owned
completion inode and cannot overwrite a replacement belonging to someone else.

## Independent reconstruction

The checker accepts external SHA-256 selections for the attempt, request,
selection, build record, probe and policy. It rejects changed member rosters,
symlinks, hard links, replaced directories, altered bytes and rehashed semantic
changes. It never samples the verifier's current environment as a substitute for
the recorded acquisition context.

For a structurally viable attempt it freshly reconstructs the selected build
and policy through the preceding checker, then replays the raw qualification
through the unchanged raw-record checker. The before/after observations, mode,
selected environment and probe must satisfy the declared relationships. Fatal,
missing, rejected or incomplete evidence cannot become a completed attempt.

The three report states are:

```text
accepted_native_selected_guard_attempt
accepted_scripted_selected_guard_attempt
preserved_incomplete_selected_guard_attempt
```

These are byte-reconstruction results within the declared acquisition trust.
The checker does not authenticate human authorization, physical invocation
counts, the host kernel or acquisition process. Its explicit flags include
`owner_identity_authenticated=false` and
`invocation_count_physically_authenticated=false`.

The offline CLI uses `--bundle`, `--expected-attempt-sha256`,
`--expected-request-sha256`, `--expected-selection-sha256`,
`--expected-build-record-sha256`, `--expected-probe-sha256`,
`--accepted-policy-sha256` and `--out`. The derived report must be outside the
original bundle so that its member inventory remains exact. Each checker process
reconstructs the input relationships independently.

## Development validation

The appended regressions exercise complete scripted acquisition and independent
replay, explicit acknowledgement, admission before invocation, single-call
failure handling, immutable context snapshots, source drift, rehashed controls,
raw-record tampering, origin separation, fatal observer termination and owned
publication failures. CLI checks use authored records and a stubbed fatal exit;
they do not start the qualifier's native backend.

The final focused run passed **68 tests in 161.15 seconds (2 minutes 41 seconds)**.
It includes two fresh data-only checker CLI processes with byte-identical reports
and schema validation of the produced request, attempt and report. Two combined
directory-rename/consumed-descriptor-close regressions first exposed an owned
completion invalidation defect and passed after the retained-directory fix.

All 922 preceding test functions and decorators retain their ASTs; the complete
1,535,810-byte prior test prefix remains byte-identical. The sixteen prior bound
source files, both CI manifests and the 120-minute Tools smoke workflow remain
unchanged. Python 3.11 grammar, schema structure and local Markdown links were
also checked.

The tests reuse only the bounded pure-parser fixture caches reviewed in #3064.
Admission results, source snapshots, digests, prerequisite relationships and
verification reports are not cached. The measured focused duration is local
implementation evidence; it does not guarantee a hosted job duration. Complete
hosted PR CI remains the owner's subsequent gate.

## Remaining acceptance boundary

A later owner-reviewed acquisition route must fix the actual source revision,
build inputs, compiler selection, environment and outer restrictions, prepare a
fresh selection and start this adapter as a disposable observer. Its complete
original evidence must then be preserved and independently checked in separate
processes. This unit introduces no hosted controller or workflow and performs
no such acquisition.

Even a future accepted native guard-probe record does not admit the executed
startup helper, compiler dependencies, original namespace/mount/openat2 setup,
separate R/T containment filters, original-entry collector or selected CPython
runtime. Those remain the
[containment plan's full-host obligations](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md#proposed-finite-budgets-and-host-gates).
Full B2 and the whole-runtime scope of #2879 remain open.
