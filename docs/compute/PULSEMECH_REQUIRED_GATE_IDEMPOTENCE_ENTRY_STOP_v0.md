# B2 guarded original executable-entry observation v0

**Status: the task guard, separate capability qualifiers, original-entry
collector, closed capture schema, independent byte checker and original-input
preparation adapter are implemented. No original executable-entry capture has
been acquired. The selected hosted environment remains unqualified. B2 is
incomplete and `authority_effect=none`.**

This unit implements the next acquisition mechanism selected by the
[original executable-entry plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_PLAN_v0.md).
The authored plan, its SHA-256, the historical cp0 evidence and all 62 bound
historical sources remain unchanged. The new profile has its own request,
capture and verification meanings; an earlier terminated process cannot be
continued or relabelled as its live prefix.

## Files and interfaces

| File | Role |
| --- | --- |
| [Task-guard installer and qualifier](../../tools/required_gate_idempotence_entry_task_guard_v0.py) | Install the exact child filter, preserve its setup transcript, and separately exercise eleven authored benign capability probes. |
| [Independent task-guard checker](../../tools/check_required_gate_idempotence_entry_task_guard_v0.py) | Reconstruct the filter, installation, descriptor continuity and qualification records from bytes. |
| [Hardware qualifier](../../tools/qualify_required_gate_idempotence_entry_stop_v0.py) | Test the selected ptrace/debug-register ABI using a fixed 130-byte static ELF whose only instruction is UD2. |
| [Entry collector](../../tools/required_gate_idempotence_entry_stop_v0.py) | Own one fresh original child, retain its cp0 prefix, continue once to executable entry, sample selected evidence, then kill and reap it. |
| [Independent entry checker](../../tools/check_required_gate_idempotence_entry_stop_v0.py) | Reconstruct request, capability prerequisites, process continuity, mappings, breakpoint/trap, sampled bytes and terminal cleanup. |
| [Preparation adapter](../../tools/prepare_required_gate_idempotence_entry_stop_v0.py) | Repeat original distribution/launch-host admission for prepare, check, run-owner and check-capture. |
| [Closed schema](../../schemas/required_gate_idempotence_entry_stop_v0.schema.json) | Validate the finite record shapes and fixed policy. Structural validity alone establishes no observation. |
| [Regression tests](../../tests/test_required_gate_idempotence_containment_v0.py) | Independently authored raw fixtures, rehashed evidence rejection, native-call guards and preservation/cleanup regressions. |

The observation profile is
`linux_x86_64_original_launcher_entry_stop_v0`. Every request binds the fixed
plan, six original native byte strings, fresh attempt identifier, selected
observer, both qualification records, finite limits and the exact 72-source
closure. The observer remains `/usr/local/bin/python3.11`, 14,472 bytes,
SHA-256 `92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79`.

## Separate capability qualification

Both qualification records are mandatory before an original attempt. Their
context includes the kernel release/version, boot ID, observer executable
binding and ten namespace observations. Missing `time` or `time_for_children`
interfaces are represented explicitly as `null`; the other eight interfaces
are required. Qualification and acquisition contexts must match exactly.
The qualifiers run outside the original attempt's one-child and 15-second
budget. Their completion timestamps must precede that attempt.

### Child task guard

The selected little-endian cBPF program has 21 instructions and 168 bytes:

```text
a869a342b9be1e9d6c6f7c02833ec9a0dbfd07323613b3ae70762f1c317dd444
```

It accepts only `AUDIT_ARCH_X86_64`, rejects the x32 syscall bit, and selects
`SECCOMP_RET_KILL_PROCESS` for `clone`, `fork`, `vfork`, `clone3`,
`io_uring_setup`, `io_uring_enter` and `io_uring_register`. Other native
syscalls remain allowed. The guard prevents the selected task-creation routes;
it does not qualify containment, filesystem access, networking or all possible
effects of loader initialization. Linux's
[seccomp filter documentation](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
specifies the ABI checks, `no_new_privs` prerequisite and filter action meanings.

The owned child first replaces standard input with `/dev/null`, selects
separate output/error pipes, closes unrelated inherited descriptors, sets its
parent-death signal and disables core dumps. The only additional descriptors
at installation are the sealed launcher and a dedicated receipt pipe. Both
have close-on-exec set. After the receipt closes, the setup snapshot must
contain exactly descriptors 0, 1, 2 and the launcher; both post-exec snapshots
must contain only the same descriptors 0, 1 and 2. No inherited io_uring
descriptor can be inferred away or omitted from the observed roster.

The installation transcript binds exact filter bytes, child/parent PID,
start time, attempt/request, raw cleared-errno `prctl` returns, before/after
procfs status and the descriptor roster. The stopped parent independently
observes `NoNewPrivs=1`, `Seccomp=2`, the one-filter count increase and
continued identity at both checkpoints. This is explicitly a source-bound
installer transcript plus procfs evidence. Privileged kernel filter readback
and physical authentication remain false; `Seccomp: 2` alone is insufficient.

The separate qualifier requires all eleven cases: the seven denied native
syscalls, x32 `getpid`, compat `int 0x80` `getpid`, allowed native `getpid`, and
an authored static ELF whose post-exec `clone` must be denied. Each case has
its own process identity and preserved installation evidence. An unexpected
signal, reused case, missing result or failed cleanup prevents qualification.
The qualifier has a 30-second wall budget, a 2-second per-case budget, a
2-second cleanup window and a 512-KiB record limit.

### Hardware execution breakpoint

The separate hardware probe is a fixed 130-byte static ELF:

```text
abc49f273badbc70283221499d9cffafcdd9d2e56cd6f23fee1efcd6a6226872
```

It has no interpreter and no syscall instructions. Its entry address is
`0x400080`; the two bytes there are UD2. The qualification must stop on the
hardware breakpoint before that instruction executes, preserve the selected
raw registers/auxv/debug-register/trap evidence, then kill and reap the child.
A setup error or UD2 fault cannot qualify the breakpoint. Failed attempts
retain their available raw prefix and failure code.

The selected x86-64 ptrace ABI reads debug registers 0, 1, 2, 3, 6 and 7 at
offset `848 + 8 * register`. Initial address registers and DR7 must be zero.
The only writes, in order, are DR0 to the independently derived target,
DR6 to `0xffff0ff0`, and DR7 to 1. Their return codes and readback are retained.
`PTRACE_PEEKUSER` correctly distinguishes a legitimate `-1` value with zero
errno from a failed read. The accepted trap requires raw SIGTRAP, no ptrace
event high bits, `TRAP_HWBKPT`, the exact slot-0 debug cause and RIP/`si_addr`
equal to the target. See the selected kernel's
[ptrace implementation](https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/ptrace.c),
[debug-register ABI](https://github.com/torvalds/linux/blob/v6.11/arch/x86/include/uapi/asm/debugreg.h)
and [64-bit user structure](https://github.com/torvalds/linux/blob/v6.11/arch/x86/include/asm/user_64.h).
These references explain the mechanism; the separate probe supplies the
bounded environment-specific capability evidence.

## One original attempt and two stopped snapshots

The public preparation adapter repeats the existing original-input
reconstruction and fresh signature verification at the selected historical
evaluation epoch. Preparing a request does not start the launcher. The native
collector also checks the actual qualification context and original byte pins
before creating its child. A new attempt cannot reuse the historical cp0
identifier, qualification attempt identifiers or a qualification child's
PID/start-time pair.

The original invocation remains `argv=["bubblewrap"]`, `cwd=/`, with only
`LC_ALL=C` and `TZ=UTC`. The collector opens and pins these ordinary host
objects before exec:

| Role | Selected host path |
| --- | --- |
| Launcher | Sealed memfd containing the exact original `native/bwrap` bytes. |
| Interpreter | `/lib64/ld-linux-x86-64.so.2` |
| libc | `/usr/lib/x86_64-linux-gnu/libc.so.6` |
| libcap | `/usr/lib/x86_64-linux-gnu/libcap.so.2` |
| libpcre2 | `/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0` |
| libselinux | `/usr/lib/x86_64-linux-gnu/libselinux.so.1` |

Held regular-file descriptors, whole-file bytes and device/inode identities
bind the selected objects to their actual mappings. A path string alone
cannot establish that relation. This mechanism does not require privileged
`map_files` access and never substitutes a different library to obtain success.

There is one setup-to-exec continuation and one cp0-to-entry continuation.
The fresh cp0 prefix retains the launcher/interpreter's raw stopped state and
four RX samples. It is checked with the earlier pure low-level relationships,
without fabricating an old completed capture whose zero-continuation and
terminal-cleanup requirements would be false.

At entry, all six original objects, 24 `PT_LOAD` file extents and twelve RX
sample occurrences are required. Entry is derived from fresh `AT_ENTRY`,
launcher load bias and the original ELF `e_entry`. The target must be in the
launcher's executable file extent. Before/after raw maps, registers and auxv
must remain equal within each stopped checkpoint; process identity and auxv
must remain continuous across the two checkpoints. Registers need not equal
their earlier cp0 values after the loader interval.

The checker handles split mapping rows and permits write removal only on
pages derived from original `PT_GNU_RELRO` ranges. It rejects extra selected
occurrences, aliasing identities, wrong backing offsets and permission gains.
The separate remaining-mapping policy permits at most 128 total rows, unique
selected kernel mappings, a stack of at most 8 MiB, and at most sixteen
read-only/read-write anonymous or heap rows totalling at most 64 MiB.
Anonymous executable/shared mappings and unselected ordinary file mappings
cannot yield a positive v0 capture. All raw maps remain preserved. These
metadata checks do not claim complete process-memory byte verification.

Loader relocations, initializers and IFUNC resolvers can execute between cp0
and executable entry. The collector never resumes entry, forwards a signal,
patches target code, writes general registers/RIP, detaches or retries.
All twelve static dependency occurrences remain separately retained;
provider mapping presence does not prove per-consumer loader resolution.

## Preservation, failures and independent reconstruction

A completed capture contains 77 raw files plus `capture.json`. The closed
roster includes the request, both capability qualifications, task-guard
installation, descriptor rosters, both checkpoints, selected original file
snapshots, breakpoint programming/trap, sixteen total RX samples, bounded
output and terminal ownership records. The twelve entry samples cover
4,601,548 bytes; the four cp0 samples add 400,964 bytes.

The observation retains the plan's 15-second wall bound, 2-second cleanup
window, eight wait-record limit, 160-file ceiling, 1-MiB control-file limit,
64-KiB procfs-file limit, 4-KiB limit per output stream and 40-MiB aggregate
capture limit. Aggregate accounting includes `capture.json`. Evidence is
written into a newly created private directory, reopened and byte-compared
before publication. Existing output paths, changed ancestors, symlinked
members, altered bytes or incomplete publication cannot pass that procedure.

Unexpected stops, early exits, failed prerequisites, timeouts and changed
evidence end the attempt. The collector kills and reaps only its owned child
and any unexpected descendant identified by its own kernel ptrace event.
Failure cleanup cannot signal a zero/observer PID or re-add an already reaped
descendant. Available guard receipts and output prefixes survive setup
failure; terminal reaping remains recorded even if the finite event budget
is exhausted. Cleanup or preservation failure prevents completion.

An independent byte check may accept a correctly preserved incomplete
record while reporting `observation_complete=false` and every narrow
observation flag false. It reconstructs completed records from their raw
relationships, rather than trusting saved completion flags. The checker
does not import the collector, install filters or launch qualification probes.
The standalone capture checker performs data reconstruction; the public
`check-capture` adapter additionally repeats original-chain admission.

## Owner environment workflow

In a separately selected owner environment with the exact observer and
original host objects, the two capability commands are:

```bash
/usr/local/bin/python3.11 -I -B tools/required_gate_idempotence_entry_task_guard_v0.py \
  qualify --output /tmp/entry-task-guard-qualification.json

/usr/local/bin/python3.11 -I -B tools/qualify_required_gate_idempotence_entry_stop_v0.py \
  --output /tmp/entry-hardware-qualification.json
```

Each output path must be new. Preserve the original output bytes and select
their SHA-256 values independently. Both records must pass before using
`prepare_required_gate_idempotence_entry_stop_v0.py prepare`. Its required
inputs include the unchanged original-input directory and manifest digest,
a new signature-verification directory, a fresh attempt ID, and both
qualification paths and digests. `check` independently derives the same
request. The explicit native command is `run-owner`, with acknowledgement
`OBSERVE_ORIGINAL_LAUNCHER_ENTRY_STOP_ONLY`; authorization remains a separate
owner decision.

The separate
[GitHub hosted integration](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_GITHUB_v0.md)
now supplies the owner-controlled workflow, exact original host-object checks,
preservation of both capability records and incomplete attempts, independent
reconstruction and owned outer-container cleanup. Publishing that integration
does not dispatch an acquisition or establish successful host qualification.
The native collector's child cleanup does not assert hosted container cleanup.

## Validation scope and next evidence

Regression fixtures use the six real preserved ELF byte strings with
independently authored synthetic process, mapping, auxv, register and trap
records. They establish checker and orchestration behavior without executing
the original launcher. The tests include a separate cBPF interpreter, filter
and descriptor disagreements, invalid/rehashed qualification records,
wrong/missing entry evidence, altered memory, reused identities, forbidden
transitions, incomplete prefixes and output/preservation failures.

The local development environment is not eligible for an original attempt.
The compat `int 0x80` probe ended with SIGSEGV, which cannot establish the
required seccomp-denial observation, and the hardware probe's
`PTRACE_TRACEME` returned `EPERM`. Both outcomes remain incomplete capability
records. No original launcher or selected-runtime execution was performed.

The next operational evidence comes from the separately selected hosted
environment and its owner-controlled entry workflow, including both complete
capability qualifications and bounded outer cleanup. A separately authorized
fresh entry capture and its preserved independent reconstructions then supply
new narrow evidence.
Actual per-consumer loader resolution, observed containment,
selected-bootstrap integration, B3 property evidence, B4 admission and B5's
actual reference remain separate obligations.

All broad boundaries remain diagnostic: `metric_pass=null`,
`authority_effect=none`, no physical execution authentication, no complete
native closure, no containment/readiness/authorization promotion and no B2
completion. Q2's recorded `FAIL 49/50 +1 UNKNOWN`, the twelve unsupported
gates, Q3's existing scope and broader Steps 6/7 retain their meanings.
Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open
under its existing Step 5C acceptance conditions.
