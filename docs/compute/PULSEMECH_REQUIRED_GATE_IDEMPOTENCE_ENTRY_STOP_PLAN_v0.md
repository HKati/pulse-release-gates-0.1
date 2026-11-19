# B2 original executable-entry observation plan v0

**Status: an authored observation proposal, a closed plan schema and an
independent byte-only plan checker are implemented. No executable-entry
capture has been acquired. B2 remains incomplete.**

This unit follows the completed
[original launcher/interpreter cp0 observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_GITHUB_v0.md#completed-hosted-observation--443750521711).
It selects a finite next observation of the original executable at its ELF
entry point. The proposed observation must account for the loader and
initializers that can execute between cp0 and entry. The current unit checks
the proposal against preserved evidence and original ELF bytes; it does not
implement a collector, capture schema, capture checker or hosted workflow.

## Files and profiles

| File | Role |
| --- | --- |
| [Authored plan](required_gate_idempotence_entry_stop_plan_v0/plan_v0.json) | Fixed checkpoint, execution boundary, original-object obligations, evidence groups and limits. |
| [Closed schema](../../schemas/required_gate_idempotence_entry_stop_plan_v0.schema.json) | Structural validation and fixed proposal policy. It cannot establish that an acquisition occurred. |
| [Independent checker](../../tools/check_required_gate_idempotence_entry_stop_plan_v0.py) | Reconstruct the historical cp0 report and derive the proposed native-object, segment, RX-sample and static-relationship obligations from original bytes. |
| [Regression tests](../../tests/test_required_gate_idempotence_containment_v0.py) | Positive preserved-byte reconstruction and rejection of altered evidence, obligations, limits and authority claims. |

The plan profile is
`linux_x86_64_original_launcher_entry_stop_plan_v0`. The separately proposed,
unimplemented acquisition profile is
`linux_x86_64_original_launcher_entry_stop_v0`.

The plan is 26,997 bytes. Its externally supplied SHA-256 is:

```text
2e289c818aaa6a51ab6757dc0995a5fe78f38e7022a8b7ca35ea250a45b0f191
```

The checker accepts an independently supplied plan digest. It does not take a
digest claimed inside the plan as its own admission authority. The schema
closes every object, binds the fixed policy, and bounds the derived tables;
the checker still reconstructs their values independently.

## Historical baseline and a new attempt

The selected baseline is owner-dispatched
[run 44375052171, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44375052171),
from source commit `84b78ff1758ed3db73fbb1db1b37451ca6620373`.
Its accepted cp0 capture covered the original launcher and interpreter at
`PTRACE_EVENT_EXEC`, with zero post-exec continuations and completed owned
cleanup. That historical child was terminated and reaped. It cannot be
resumed by this proposal.

The checker reads two existing, unchanged repository carriers:

| Carrier | Bytes | SHA-256 |
| --- | ---: | --- |
| [Selected cp0 control evidence](../../preservation/required_gate_idempotence_exec_stop_v0/run_44375052171_attempt_1/control_evidence_v0.zip) | 737,502 | `788aaa185e979f5ecddfa3b17f8a45d8b74ee59671b26033b5b94c249c9359c6` |
| [Original input bytes](../../preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip) | 24,816,167 | `70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a` |

A future acquisition requires a new attempt, new original-input admission
and its own live cp0 prefix. Its process identity must remain continuous
through the later entry checkpoint. Historical PIDs, load biases and ASLR
addresses are not reusable. The completed historical cp0 record cannot serve
as the live prefix: its checker requires terminal cleanup and zero
post-exec resumes. A new profile must express the live prefix and its later
cleanup without changing those historical meanings.

The current plan checker performs the lower-level historical reconstruction.
It does not freshly verify Debian signatures or the hosted attestation, or
replay the complete hosted environment. The separately retained original
hosted ZIPs retain their existing custody requirement.

## Exact proposed checkpoint and allowed execution

The target is the fresh process's `AT_ENTRY`, independently matched to the
fresh original-launcher load bias plus the original ELF `e_entry`. The
address must fall within the original launcher's executable `PT_LOAD` file
extent. An arbitrary address, historical address, symbol such as `main`,
alternate loader or modified target is outside this proposal.

The candidate stop mechanism is x86-64 hardware execution breakpoint slot 0.
Only `DR0`, `DR6` and `DR7` may be written: `DR0` selects the derived target,
`DR7=1` enables the local slot-0 execution breakpoint, and `DR6` is reset and
read back under the qualified ABI. Programming and readback must be preserved.
The accepted entry event must have `SIGTRAP`, no `PTRACE_EVENT` high bits,
`TRAP_HWBKPT`, the slot-0 cause without another significant debug cause, and
`RIP` equal to the derived target before its instruction executes.

No target-code patch, software-breakpoint fallback, general-register or
instruction-pointer write, detach or retry is allowed. The exact hardware
support and debug-register ABI remain to be qualified. Linux's
[x86 ptrace implementation](https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/ptrace.c)
and [hardware-breakpoint handling](https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/hw_breakpoint.c)
are the mechanism references, not evidence of this environment's support.
The future implementation must handle `PTRACE_PEEKUSER` return values
correctly; a helper that requires every ptrace operation to return zero is
not suitable for register reads.

There is one pre-exec resume, one cp0-to-entry resume, and zero post-entry
resumes. The original invocation remains `argv=["bubblewrap"]`, `cwd=/`,
with only `LC_ALL=C` and `TZ=UTC` in its selected environment. No `LD_*`
injection, signal forwarding or fallback checkpoint is selected. Unexpected
stops, additional exec events, early exit, timeout or missing evidence produce
an incomplete prefix followed by owned cleanup.

Entry is later than the kernel exec stop. The glibc x86-64 startup path calls
initialization before transferring control to executable entry; dependency
constructors, applicable executable preinitializers and IFUNC resolvers can
run during startup. See the
[startup implementation](https://github.com/bminor/glibc/blob/glibc-2.41/sysdeps/x86_64/dl-machine.h),
[initializer implementation](https://github.com/bminor/glibc/blob/glibc-2.41/elf/dl-init.c)
and [dynamic-linker guidance](https://snapshots.sourceware.org/glibc/trunk/2026-04-15_23-51_1776297061/manual/html_node/Dynamic-Linker-Hardening.html).
These sources explain the mechanism; they do not establish a source-to-binary
reproduction of the selected preserved loader.

The proposal therefore makes no claim that no native code or side effect
occurred before entry. Its `selected_runtime_executed=false` retains the
existing selected-runtime-capsule meaning. Registers must be stable during
each stopped snapshot, but need not equal the earlier cp0 registers; the
execution interval changes them, and debug-trap handling can set the resume
flag.

## Selected objects, segments and RX samples

All six original native objects are required for a positive future entry
observation. Their bytes are selected from the original carrier, rather than
from whatever packages happen to be installed on the observer host.

| Original member | Whole-file bytes | `PT_LOAD` occurrences | RX file offset | RX bytes per sample | Sample occurrences |
| --- | ---: | ---: | ---: | ---: | ---: |
| `native/bwrap` | 80,248 | 4 | 12,288 | 39,761 | 2 |
| `native/ld-linux-x86-64.so.2` | 225,672 | 4 | 4,096 | 160,721 | 2 |
| `native/libc.so.6` | 1,995,216 | 4 | 163,840 | 1,451,581 | 2 |
| `native/libcap.so.2` | 47,288 | 4 | 12,288 | 19,973 | 2 |
| `native/libpcre2-8.so.0` | 711,216 | 4 | 12,288 | 501,093 | 2 |
| `native/libselinux.so.1` | 202,984 | 4 | 28,672 | 127,645 | 2 |
| **Total** | **3,262,624** | **24** | | **2,300,774 distinct bytes** | **12** |

The twelve sample occurrences cover **4,601,548 sampled bytes**. Both samples
of each selected RX file extent must equal its original bytes. This does not
authenticate whole process memory or intervening states. The current plan's
`entry_observed` fields are all false.

Each selected object needs one unambiguous mapped occurrence, an actual
mapped-object descriptor and whole-file binding, plus before/after stopped
identity, maps, auxv and register evidence. Every selected `PT_LOAD` file
extent must be covered. A segment may span several `/proc/<pid>/maps` rows.
GNU RELRO can remove write permission after relocation; the future checker
must derive that change and reject unsupported permission gains. See glibc's
[RELRO protection implementation](https://github.com/bminor/glibc/blob/glibc-2.41/elf/dl-reloc.c).
The old two-image cp0 mapping routine cannot be reused unchanged for this
later state.

Anonymous, TLS, heap, stack and kernel mappings need a separate bounded
metadata policy. Unselected mappings remain in the raw maps evidence and
do not become part of a claimed complete native closure. A missing,
substituted or ambiguous selected object makes the observation incomplete or
rejected; its obligation cannot be removed to obtain success. The existing
hosted environment's loader/observer pins do not establish that the four
additional selected DSOs are installed there.

## Static relationships and remaining resolution evidence

The checker retains all twelve original static relationships as separate
consumer occurrences. The nine `DT_NEEDED` declarations are:

| Consumer | Selected providers |
| --- | --- |
| `bwrap` | `libc.so.6`, `libcap.so.2`, `libselinux.so.1` |
| `libc.so.6` | `ld-linux-x86-64.so.2` |
| `libcap.so.2` | `libc.so.6` |
| `libpcre2-8.so.0` | `libc.so.6` |
| `libselinux.so.1` | `ld-linux-x86-64.so.2`, `libc.so.6`, `libpcre2-8.so.0` |

The three `PT_INTERP` declarations belong to `bwrap`, `libc.so.6` and
`libcap.so.2`. Only the launcher's declaration requires fresh kernel
interpreter continuity in this observation. The other two remain static
metadata and do not imply recursively executed interpreters.

Presence of a selected provider in maps does not establish that a particular
consumer resolved a dependency through it. All proposed
`provider_mapping_observed` and `consumer_resolution_observed` fields remain
false. A later capture may establish the selected mappings; actual
per-consumer loader resolution still requires a separately specified raw
witness and independent reconstruction. The plan does not invent that witness
or promote a static dependency table into a dynamic observation.

## Task creation and owned cleanup

The proposed observation owns one tracee. Ptrace fork/clone event logging
alone cannot establish that no additional task was created. Linux permits
`CLONE_UNTRACED` to suppress the corresponding event, and io_uring's worker
path uses an untraced thread-creation route. See
[`kernel/fork.c`](https://github.com/torvalds/linux/blob/v6.11/kernel/fork.c)
and [`io_uring/io-wq.c`](https://github.com/torvalds/linux/blob/v6.11/io_uring/io-wq.c).

The proposal requires a separately validated child seccomp filter before
the original exec, with `no_new_privs`, native x86-64 ABI checks, rejection of
compat/x32 paths, and `SECCOMP_RET_KILL_PROCESS` for `clone`, `clone3`, `fork`,
`vfork`, `io_uring_setup`, `io_uring_enter` and `io_uring_register`. There must
be no inherited io_uring descriptor. The
[kernel seccomp documentation](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
describes ABI checks, installation prerequisites and kill-before-syscall
semantics; syscall filtering alone is not whole-containment qualification.

**The exact filter program, installation/denial evidence and their checker
are not implemented or selected by this unit.** A `Seccomp: 2` field alone
does not identify the installed filter. Privileged filter readback is not
assumed to be available in the existing restricted environment. These are
implementation gates before any entry acquisition.

The proposed ptrace options are `EXITKILL`, `TRACECLONE`, `TRACEEXEC`,
`TRACEFORK` and `TRACEVFORK`. Any unexpected event ends the attempt as
incomplete. Cleanup must kill and reap owned work and remove the owned outer
container, including failure paths. Cleanup or preservation failure cannot
return a complete observation. No global cleanup or unrelated process
selection is authorized.

## Finite evidence and limits

A new closed capture schema and independent capture checker must preserve
the request/attempt, fresh cp0 prefix, entry checkpoint, breakpoint programming
and trap, task-guard installation, selected object descriptors/bytes,
maps/auxv/registers/identity, RX samples, bounded events/output, and terminal
cleanup or the available incomplete prefix. Their exact rosters remain to be
implemented. Saved success booleans cannot replace raw reconstruction.

| Limit | Proposed bound |
| --- | ---: |
| Observation wall time | 15 seconds |
| Cleanup window | 2 seconds |
| Owned tracees | 1 |
| Wait records | 8 |
| Capture files | 160 |
| Each control file | 1,048,576 bytes |
| Each procfs file | 65,536 bytes |
| Standard output / standard error | 4,096 bytes each |
| Total capture | 41,943,040 bytes |
| Deadline extensions, implicit retries, post-entry resumes | 0 |

Two whole-file snapshots of all selected objects, all twelve RX samples and
the selected observer total 11,141,268 bytes. The plan checker adds an
8,388,608-byte control/procfs allowance and requires that minimum to fit the
total capture limit. This arithmetic establishes a plan budget, not measured
capture size or observed runtime/resource use.

## Independent plan check

The checker operates on data only. It has no native-process acquisition path.
It performs these checks in order:

1. Verify the externally supplied plan digest, strict JSON representation and
   closed plan schema. Duplicate keys, non-integer numbers and non-finite
   values are rejected.
2. Bind the exact historical archive, closed member inventory and selected
   request/capture/report/receipt bytes. Reconstruct the original cp0 report
   with the unchanged original checker, and require byte equality with both
   saved accepted reports.
3. Match all 62 historical source bindings against current repository bytes,
   before and after derivation. Reconcile selected acquisition members with
   the original receipt and verified binding.
4. Bind the original carrier and six selected native byte strings. Independently
   derive ELF layouts, dynamic declarations, initialization metadata, RX
   ranges/hashes and all twelve static relationships. Compare the authored
   plan with canonical derived values, including totals and the observer.
5. Check the finite byte budget and stable checker/schema sources. Emit a
   canonical diagnostic report with plan consistency accepted and every
   acquisition, readiness and authority boundary retained.

From the repository root, with the repository's Python dependencies installed:

```bash
python -I -B tools/check_required_gate_idempotence_entry_stop_plan_v0.py \
  --plan docs/compute/required_gate_idempotence_entry_stop_plan_v0/plan_v0.json \
  --plan-sha256 2e289c818aaa6a51ab6757dc0995a5fe78f38e7022a8b7ca35ea250a45b0f191 \
  --output /tmp/entry-stop-plan-check-1.json
```

The output path must not already exist. A second fresh checker process can
write a different new path and the resulting canonical reports must be byte
identical when all inputs and checker/schema bytes are unchanged. An accepted
plan report is not an entry observation or a fresh signature verification.

The appended `entry_stop_plan` regressions live in the existing containment
test file already selected by `ci/tools-tests.list`. They cover the preserved
positive input, rehashed plan alterations, raw archive/source bindings,
structural-versus-semantic rejection, execution guards and CLI behavior.
No workflow or CI test inventory is changed by this unit.

## Next implementation gates and authority boundary

The next unit must select and validate the exact task-creation filter and its
installation/denial evidence, then implement the new owned cp0-to-entry
collector, closed capture schema and independent checker. The exact native
environment, paths, breakpoint capability and cleanup behavior require
qualification before a separately owner-authorized new attempt. A later
per-consumer resolution witness, observed containment and selected-bootstrap
integration remain additional obligations.

The plan and its accepted report retain `record_status=proposal`,
`diagnostic_only=true`, `metric_pass=null` and `authority_effect=none`.
`entry_checkpoint_observed`, `native_acquisition_performed`,
`loader_resolution_verified`, `complete_native_closure_verified`,
`containment_enforced`, `execution_ready`, `execution_authorized`,
`production_gate_eligible` and `b2_complete` remain false. The successful
historical cp0 reconstruction is separately nested in the report and cannot
promote those current proposal fields.

Q2 remains `FAIL 49/50 +1 UNKNOWN`; all twelve unsupported gates, historical
Q3 scope, B3 property evidence, B4 admission, B5 the actual reference and
broader Steps 6 and 7 retain their existing status. Keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.
The [readiness plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#18-required-gate-coverage-plan-after-accepted-rejection-verification)
continues to govern those later evidence requirements.
