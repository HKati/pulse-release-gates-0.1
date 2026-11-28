# B2 containment task-guard probe qualification v0

## Status and scope

This unit implements the first native qualification component following the
[startup helper and guard source contract](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_STARTUP_v0.md).
It supplies a fixed authored C probe, a bounded native acquisition command, a
closed record schema and a separate data-only verifier. Development validation
uses authored transcripts, substituted backend operations and compilation only.
**No native qualification attempt, startup helper, original launcher, static
entry, selected runtime or container was executed to prepare this unit.**

The component's possible future success is narrow: a selected probe submitted
the exact task-guard bytes, the fixed cases produced their declared observations,
the two permitted task births and selected inheritance routes were witnessed,
and every owned task was finally removed. The result depends on the declared
observer and kernel trust. Record reconstruction does not authenticate physical
execution, a build, a container image or an outer security policy.

The [complete containment-entry qualification obligations](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md#proposed-finite-budgets-and-host-gates)
remain the acceptance target. This first component does not execute the actual
startup helper, qualify its build, reproduce the complete original namespace and
mount setup, exercise openat2, or observe the separate R/T containment-filter
submissions. Those obligations are not satisfied by the guard-probe result.

Keep `b2_complete=false`, `metric_pass=null`, `authority_effect=none`, and issue
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Files and responsibilities

| File | Responsibility |
| --- | --- |
| [Fixed probe source](../../tools/required_gate_idempotence_containment_task_probe_v0.c) | Freestanding Linux x86-64 program with 21 fixed cases and the selected readonly 272-byte guard section. |
| [Native qualifier](../../tools/qualify_required_gate_idempotence_containment_task_guard_v0.py) | Own the disposable observer, acquire raw stops and selected memory, enforce the replay state machine before resumes, preserve failures and perform bounded cleanup. |
| [Independent verifier](../../tools/check_required_gate_idempotence_containment_task_guard_qualification_v0.py) | Decode raw evidence and reconstruct the case sequence, byte bindings, births, inheritance and final removal without importing or executing the qualifier or probe. |
| [Record schema](../../schemas/required_gate_idempotence_containment_task_guard_qualification_v0.schema.json) | Declare the closed evidence/report shapes and fixed limits. The verifier also enforces semantic relationships directly. |
| [Registered containment regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Append data-only, direct substituted-backend and compile-only cases while preserving the complete historical test prefix. |

All source files, schema and contract from the prior startup-helper unit remain
unchanged. The new verifier binds their exact selected identities and freshly
reconstructs the prior source contract. It does not reinterpret historical
contract success as native execution evidence.

## Selected probe and guard

The probe is a separate authored diagnostic executable. Its initial vector is:

```text
pulsemech-containment-task-probe-v0 <fixed-case-name> <observer-pid> initial
```

The environment is exactly `LC_ALL=C` and `TZ=UTC`. FD 0 is an empty readonly
sealed input, FD 1/2 are distinct owned nonblocking output pipes, and FD 3 is the
readonly fully sealed selected probe ELF. There is no expected output.

The initial L task checks equal nonroot real/effective UID and GID, zero effective,
permitted and inheritable capability sets, its parent-death setting and the fixed
descriptor metadata. It sets and reads back no-new-privileges, submits one guard,
and reads back seccomp mode and no-new-privileges. The observer captures the actual
`sock_fprog`, all 34 instructions, submission return and task-bound state.

The selected program remains:

```text
size_bytes: 272
sha256: cc75cb083fb0f6b235eb429384dfb5aaffdd4653891eb2010cd0fd5b6939a51f
```

The compiled ELF must satisfy the independent structural check and an externally
selected SHA-256. That identifies the executed bytes; it does not authenticate
source-to-binary equivalence or select a compiler trust policy.

Compile-only inspection uses the same freestanding GCC recipe as the preceding
unit: C11, O2, warnings as errors, no libc/builtins/stack protector/PIE/unwind data,
static linking, no build ID, a nonexecutable stack and `_start` as entry. The
compiled binary is an execution input for a later separately authorized attempt;
it is not included as a prequalified executable in this source change.

## Fixed native case matrix

The case order is part of the contract. All negative cases require their exact
syscall entry followed by the selected SIGSYS termination; an errno return is not
a successful guard denial. The positive clone paths must actually create their
children. EPERM or ENOSYS on a required namespace clone leaves the suite incomplete.

| IDs | Cases | Expected observation |
| --- | --- | --- |
| 1 | `native_getpid` | Guard installed; selected native getpid control; normal exit 0. |
| 2–4 | `fork`, `vfork`, `clone3` | Exact disallowed creation syscall and SIGSYS. |
| 5–7 | `io_uring_setup`, `io_uring_enter`, `io_uring_register` | Exact selected bypass-route syscall and SIGSYS. |
| 8–9 | `x32_getpid`, `compat_getpid` | The selected alternate ABI is identified from raw syscall information and denied. |
| 10–12 | `clone_unselected`, `clone_l_upper`, `clone_l_stack` | Nonselected flags, a substituted high flags word or a nonzero high stack word are denied. |
| 13–18 | `clone_r_null_tid`, `clone_r_parent_tid`, `clone_r_tls`, `clone_r_stack`, `clone_r_upper`, `clone_r_unselected` | The fixed malformed second-clone variants are denied. |
| 19 | `exec_denial` | L self-execs the exact admitted probe, does not reinstall the guard and encounters the inherited raw-fork denial. |
| 20 | `graph_inheritance` | Both permitted births occur; T self-execs and encounters the inherited denial; R and L reap their child and encounter their own inherited/retained denial. |
| 21 | `graph_cancel` | Both births and T self-exec occur; all three roles stop at their declared park entries and are removed by bounded owned cleanup. |

The successful graph uses these Linux x86-64 raw clone arguments:

| Birth | Flags | Stack | Parent TID | Child TID | TLS | Unused argument |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| L to R | `0x7e020011` | 0 | `0xa2` | `0xa3` | `0xa4` | `0xa5` |
| R to T | `0x01200011` | 0 | 0 | The actual writable probe word | 0 | `0xa5` |

The first shape ignores its unused trailing arguments. The second requires a
dynamically observed writable child-TID location; the verifier checks its initial
zero value and the kernel-written T namespace PID. These observer relationships
cannot be established by the BPF argument mask alone.

Both shapes carry SIGCHLD and produce the selected `PTRACE_EVENT_FORK` route.
The parent event message and the newborn stop may arrive in either order. Neither
side is resumed until their identity join is complete. Autotraced children are
never reattached.

## Raw observation and live admission

The initial Python bootstrap is explicitly outside the admitted probe interval.
It has fixed resource limits and a private bounded release pipe. The observer
obtains ownership, performs SEIZE with `0x0010001f`, requests INTERRUPT and consumes
that stop before releasing the bootstrap. It then reaches and admits the probe's
initial exec stop before any probe instruction runs. If initial pidfd acquisition
fails, closing the release pipe causes bounded bootstrap self-exit; that path
does not create a completed qualification record.

The journal preserves raw wait statuses, register and syscall-information bytes,
event messages, task stat/status, relevant maps and memory, and actual exec image,
argv and environment bytes. Tagged getpid calls expose fixed protocol checkpoints;
their marker values do not replace the kernel observations.

The same pure state machine checks the live sequence before every restart and
replays the final record independently. It admits only the fixed role, order,
count and syscall relationships. No ptrace instruction, register, memory or
syscall-result writes are available. SIGCHLD delivery is limited to the bound
child relationship and forwarded with its observed signal value; unrelated
signals are rejected.

The qualifier distinguishes origins at its outer controller. Every explicitly
supplied backend is `scripted_test_backend`, including an explicitly supplied
NativeBackend. Passing an authored transcript through the checker cannot promote
it to a native-origin result. Conversely, a byte checker cannot independently
prove that someone did not fabricate an entire record: native records still rely
on the selected acquisition/provenance boundary.

## Finite budgets and failed prefixes

These are the diagnostic suite's limits. They do not enlarge the separate
30-second original-observation selection in the containment-entry plan.

| Budget | Limit |
| --- | ---: |
| Suite attempts / retries | 1 / 0 |
| Fixed cases | 21, stop after the first incomplete case |
| Observation budget | 120 seconds across the selected suite |
| Each case observation / cleanup | 5 / 5 seconds |
| Expected owned tasks per case | At most 3 |
| Journal events per case / suite | 8,192 / 65,536 |
| Serialized record | 32 MiB |
| Selected probe | 256 KiB |
| Individual raw read / memory aggregate per stop | 64 KiB / 1 MiB |
| stdout / stderr | 4,096 / 4,096 bytes; empty for completed cases |

Observation reserves bounded journal space for cleanup; a shared suite budget
prevents independently bounded cases from overflowing the total record. A single
unexpected birth may be quarantined in a fourth ledger slot solely for failed
cleanup. It never becomes a permitted fourth role or a successful case.

The record retains the primary failure separately from cleanup failures. Bytes
acquired before a failed read remain an incomplete prefix where the fixed budget
permits their preservation. No timeout, omitted read, partial observation or
output truncation becomes completed evidence.

## Owned cleanup

Cleanup signals each actually owned live task through its pidfd once, in reverse
creation/role order, and drains all owned waits globally. A newly discovered
quarantined child is recorded and receives its one bounded cleanup submission.
There is no numeric-PID or process-group fallback, detach, kill-through-ptrace,
post-terminal restart or automatic retry.

Cleanup does not re-read payload memory after SIGKILL. It consumes queued raw
stops and termination notifications, polls the owned pidfds and requires final
POLLHUP plus a genuinely drained ECHILD wait ledger. POLLIN can describe a zombie;
a signal submission or a single terminal wait is not final removal proof.

An evidence-publication failure cannot prevent physical signalling and draining.
If removal remains unresolved, retain the task ownership ledger and handles,
leave subreaper restoration unclaimed, and preserve an incomplete record. The
native command is a disposable observer: its fatal path publishes that prefix
and exits so EXITKILL can take effect. EXITKILL does not retrospectively supply
missing removal evidence. Native API callers must treat `ObserverExitRequired`
as a requirement to terminate the disposable observer, not as a recoverable
qualification failure from which an original attempt may continue.

The distinctions follow Linux's documented
[ptrace stop/signal behavior](https://man7.org/linux/man-pages/man2/ptrace.2.html),
[seccomp inheritance and return actions](https://docs.kernel.org/userspace-api/seccomp_filter.html)
and [pidfd readability versus final hangup](https://man7.org/linux/man-pages/man2/pidfd_open.2.html).
Documentation describes the protocol; it does not qualify a future selected host.

## Later execution and independent checking

The separate [build and context selection unit](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_SELECTION_v0.md)
now captures two fixed compile-only builds and prepares an independently checked
selection of their actual probe output, limited build policy and exact observer
context. It preserves the qualifier source and record semantics documented here.
That preparation performs no qualification attempt and does not supply the
remaining full-host or executed startup-helper acceptance.

Actual execution requires a separately reviewed probe build and environment
selection, review of this acquisition path, and explicit owner authorization.
The native CLI requires the exact acknowledgement
`QUALIFY_CONTAINMENT_TASK_GUARD_ONLY`, externally expected probe and environment
digests, and a new output path. It does not run automatically in CI or import.

The independent checker takes the preserved record and externally expected
record/probe/environment digests. It can be run in two fresh processes using the
same selected source closure; both should produce the same canonical report.
It performs no native child creation, probe execution or schema retrieval over
the network. Outputs are create-only.

A successful future guard-probe report still leaves actual startup-helper/build
admission, full same-host containment qualification, original-entry acquisition,
hosted preservation/replay, real selected CPython, bootstrap/worker integration
and B2 property evidence as separate work. No issue is closed by this component.

## Development validation

The delivered source unit was checked on the unchanged implementation closure:

- Qualification regressions: **240 passed** using authored evidence, scripted
  backends, substituted native operations and compile-only C inspection.
- Prior task-guard/source-contract and containment-entry-plan regressions:
  **336 passed**. The entire historical containment test prefix remains byte-for-byte
  unchanged; new tests are appended in the already registered module.
- Current-repository normative workflow classification: **1 passed**. No workflow
  or CI test manifest is added or changed by this unit.
- The Draft 2020-12 schema itself and the complete authored record and report
  validated without errors.
- Two fresh independent checker processes reconstructed the same authored
  21-case record and emitted byte-identical canonical reports. Their result is
  `accepted_scripted_guard_probe_record`, with
  `native_guard_probe_record_verified=false`; it is not native evidence.
- The freestanding C source compiled with the selected strict warnings enabled.
  Structural inspection found no interpreter or dynamic section and verified the
  selected readonly guard bytes. The resulting executable was not run.

The test environment reported an existing AnyIO pytest deprecation warning;
no selected test failed. These checks validate this source component and its
evidence reconstruction. They leave actual native qualification, full-host
acceptance and original execution pending.

## Complete change inventory

The upload contains exactly these ten repository paths, without a wrapper folder:

```text
CHANGELOG.md
docs/INDEX.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_STARTUP_v0.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_QUALIFICATION_v0.md
schemas/required_gate_idempotence_containment_task_guard_qualification_v0.schema.json
tests/test_required_gate_idempotence_containment_v0.py
tools/check_required_gate_idempotence_containment_task_guard_qualification_v0.py
tools/qualify_required_gate_idempotence_containment_task_guard_v0.py
tools/required_gate_idempotence_containment_task_probe_v0.c
```
