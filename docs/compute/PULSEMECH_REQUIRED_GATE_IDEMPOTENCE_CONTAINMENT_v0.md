# Bounded idempotence containment primitives v0

## Status and scope

**Implemented: deterministic boundary requests, a sealed-input Linux launcher
primitive for explicit examples, and independent diagnostic-record checking.
Selected-runtime execution remains closed. B2 remains incomplete.**

This continuation consumes the accepted [bootstrap preparation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_BOOTSTRAP_v0.md).
It supplies the process boundary that a future reviewed bootstrap runner can use.
It does not change or execute the selected sanitizer, qualify a host, authenticate
physical execution, establish runtime closure or unlock observed acquisition.

| Component | Responsibility |
| --- | --- |
| [Coordinator](../../tools/required_gate_idempotence_containment_v0.py) | Re-admit original inputs, reconstruct a fixed boundary request and preserve one bounded example attempt. |
| [Record checker](../../tools/check_required_gate_idempotence_containment_v0.py) | Check raw stream bindings and finite probe reports against an independently reconstructed request and contract. |
| [Fixed syscall policy](../../tools/required_gate_idempotence_containment_policy_v0.py) | Encode a fixed Linux x86-64 classic BPF allowlist, with no caller-supplied rules. |
| [Static entry source](../../tools/required_gate_idempotence_containment_entry_v0.c) | Close inherited descriptors, enforce limits and replace the launcher's environment before the fixed loader command. |
| [Selection schema](../../schemas/required_gate_idempotence_containment_v0.schema.json) | Bind the selected plan, phase, host launcher, entry binary and installed entry/policy source bytes. |
| [Regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Exercise authored inputs, real bounded subprocess plumbing, record substitution and preservation failures. |

The existing bootstrap, probe, runtime, ELF, acquisition, observation and B1
implementations and schemas retain their bytes. No workflow or host policy is
changed. This package does not include a compiled entry binary or a selected
real runtime launch view.

## Independent selections and reconstruction

A containment selection has
`record_type=required_gate_idempotence_containment_selection_v0` and
`profile=linux_x86_64_bubblewrap_bootstrap_v0`. It binds:

- The externally retained bootstrap plan hash and its `example` or `selected` status.
- Exactly one fixed phase, `worker` or `collector`.
- The host launcher's absolute path, SHA-256 and size.
- The compiled entry binary's SHA-256 and size.
- The exact installed entry C source and syscall-policy Python source, including their paths, SHA-256 values and sizes.
- False execution readiness, authorization, runtime closure, bootstrap qualification, containment and production eligibility, with `authority_effect=none`.

Preparation re-admits the original bootstrap inputs through the existing checker.
It does not adopt a prior report, a mutable prepared object or a merely rehashed
request. Independent request checking reconstructs the entire canonical request
from those original inputs and requires byte-identical output.

Both native binaries must have a bounded ELF64 little-endian x86-64 header. The
entry must additionally be ET_EXEC with a nonexecutable GNU stack, bounded load
segments and no PT_INTERP, PT_DYNAMIC or PT_SHLIB. These are static format checks.
They do not prove that selected binary bytes implement the declared source.

The host launcher, its own dynamic loader/libraries, the kernel and the host
remain part of the unqualified launch environment. Binding a binary hash or
naming bubblewrap does not authenticate its behavior. Source-to-binary review,
host qualification and independently checked execution observations remain
separate obligations. Public selected execution therefore rejects with
`selected_bootstrap_execution_not_ready` before any launcher invocation or
attempt-output creation.

## Derived execution view

The existing bootstrap view contains preservation files with mode 0400. The new
request derives a separate execution projection without editing that view:

- Every bootstrap file retains its exact path and bytes.
- `/runtime/bootstrap/containment-entry` adds the independently selected static entry.
- Only that entry and `/runtime/native/ld-linux-x86-64.so.2` receive mode 0500.
- Every other file retains mode 0400; explicit view directories use mode 0700.
- The launch request requires the root filesystem and each file mount to be read-only before entry execution.

The native loader is invoked explicitly and can read the selected interpreter
without making every preserved file executable. The projection is separately
recorded; it is not described as preserving the original view's modes exactly.

Every file, the syscall program, argument vector and host launcher is placed in
an independently sealed memfd. The input seals prohibit writes, growth,
shrinkage and seal removal. Bubblewrap receives file bytes through
`--ro-bind-data`; there are no host source-directory bind mounts. Changes to a
materialized host pathname cannot replace a sealed selected payload.

The request uses an empty tmpfs root and creates only the selected directories
and files. It mounts neither `/proc` nor `/dev`, and supplies empty sealed stdin
with stdout and stderr pipes. Bubblewrap's own setup runs outside this selected
view and remains part of the unqualified host launcher boundary.

The original bootstrap file/count/byte bounds remain in force. The derived
view must also fit those bounds, including the entry. The fixed argument vector
must fit below bubblewrap's 9,000-argument parser limit, including `--args FD`.
The example runner checks descriptor headroom before creating an output prefix;
it never raises the host's descriptor limit or selects a fallback profile.

## Namespace, syscall and entry ordering

The backend requests user, IPC, PID, network, UTS and cgroup namespaces explicitly.
The mount namespace is supplied by bubblewrap. It requires `--disable-userns`
and drops all capabilities. There is no `--try` option or permissive fallback.

The parent creates one new session and process group. Bubblewrap retains that
group and uses `--die-with-parent`; an additional nested session is deliberately
omitted. On timeout, output overflow or another live-child failure, the parent
kills its still-owned process group and waits for the launcher. It never signals
a process-group ID after the launcher has already been reaped.

Bubblewrap installs the fixed classic BPF policy before executing the entry.
The filter rejects other architectures and the x32 ABI, and denies unknown
system calls. Network sockets, fork/clone, mount/namespace changes, ptrace,
io_uring, BPF loading and filesystem mutation calls are outside its allowlist.
Read/open calls expose the selected read-only view. The required `execve` call
also permits later same-process replacement; this policy does not claim to
prevent all subsequent exec calls.

The static entry accepts only one of the two fixed phase arguments. Before the
selected loader invocation, it checks no-new-privileges, seccomp filter mode and
zero effective/permitted/inheritable capabilities; closes descriptors 3 and
above; and sets hard and soft CPU, address-space, core-file, file-size and
descriptor limits. These local checks do not identify or authenticate the actual
filter or host.

The entry then executes the exact bootstrap loader command with only `LC_ALL=C`
and `TZ=UTC`. This explicit environment replacement is necessary because
bubblewrap adds `PWD` after its environment options. The original fixed probe's
strict environment contract is preserved.

The parent uses a 15-second backend deadline and caps retained stdout at 65,536
bytes and stderr at 4,096 bytes. The entry sets CPU to 5 seconds, address space to
512 MiB, core/file size to zero and open descriptors to 64 before selected
runtime execution. Launcher setup cannot use those zero-file-size and 64-FD
limits because it must first create the private file mounts; its wall/output
bounds are enforced by the parent.

## Attempt preservation and independent checking

`run-example` requires a re-admitted example selection. It performs one attempt,
without retry, resume, overwrite, automatic cleanup or alternate backend.
The new private output directory preserves:

- `request.json`, `selection.json` and `bootstrap_plan.json`.
- `attempt_start.json` before the backend attempt.
- Bounded raw prefixes in `stdout.bin` and `stderr.bin`, including failed attempts.
- `receipt.json` with `completed` or `incomplete` status when preservation succeeds.

After an overflow or deadline failure, the coordinator stops the child and
performs its bounded reap before draining both pipes nonblockingly. Each stream
retains already readable bytes up to its own remaining cap through the same
preservation sink, before the pipes close. The drain stops at EOF, a would-block
read or that stream's cap; it does not wait for additional output or restart the
attempt. The original failure remains an incomplete result. A failing capture
sink is not retried during cleanup, and a drain read or sink failure prevents a
normal receipt while retaining any prefix already written.

Before saving a normal receipt, the coordinator independently reopens all six
preserved prefix files through the original pinned directory. It requires the
exact roster, original file identities, private regular files with one link,
mode 0600, exact bytes and stable metadata. It also checks the requested output
pathname still identifies the original directory. A partial append, substituted
file or failed preservation cannot produce an accepted normal receipt; the
existing prefix remains and `attempt.incomplete.json` is written when possible.

`check-attempt` re-admits the original inputs and reconstructs the request before
checking the external receipt digest, process record, raw stream hashes/sizes and
the original generated probe contract. A completed example additionally requires
exit zero, empty stderr, a bounded elapsed interval and the exact finite probe
report, including its startup, module/resource bindings and false authority flags.

A structurally valid incomplete receipt is accepted as an incomplete record:
`attempt_complete=false` and `finite_diagnostic_valid=false`. Acceptance of that
record does not turn the failed attempt into a completed diagnostic.

The lower-level record checker's `verify_receipt` function expects an already
reconstructed request. Applications should use the coordinator's `verify_attempt`
wrapper; a caller-authored request and its new hash do not replace original-input
reconstruction. Even a completed, consistent report remains self-reported
diagnostic evidence. No receipt establishes which native object physically ran,
authenticates the host, grants qualification or unlocks acquisition.

## Building the entry for a separately selected example

The source can be built with a Linux x86-64 compiler using this finite profile:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -ffreestanding -fno-builtin -fno-pie -fno-stack-protector \
  -fno-asynchronous-unwind-tables -fno-unwind-tables \
  -nostdlib -static -no-pie -Wl,--build-id=none -Wl,-z,noexecstack \
  tools/required_gate_idempotence_containment_entry_v0.c \
  -o /absolute/path/new-containment-entry
```

The caller separately selects and retains the resulting binary hash and size.
The coordinator never invokes a compiler or downloads a launcher. A successful
build alone does not establish reproducibility or source-to-binary provenance.

The subsequent [fixed entry build acquisition and provenance path](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_BUILD_v0.md)
preserves two builds, their raw source/log/binary bindings and before/after
toolchain observations, with an independent record checker and a manual hosted
attestation workflow. It never executes the resulting entry. Same-host repeated
bytes, a future verified provenance bundle and launch-host qualification remain
distinct results; this path does not unlock the selected runtime.

## Commands

`prepare`, `check`, `run-example` and `check-attempt` take the same original runtime
selection, operator selection, capsule and bootstrap selection paths/hashes used
by bootstrap preparation. They additionally require:

```text
--bootstrap-plan PATH --bootstrap-plan-sha256 SHA256
--containment-selection PATH --containment-selection-sha256 SHA256
--launcher ABSOLUTE_SELECTED_PATH --entry-shim PATH
```

Selected source records also require the original local `--repository-root`.
`prepare` writes a new request with `--output PATH`. Other commands require
`--request PATH --request-sha256 SHA256`. `check` may write a new verification
record with `--output PATH`. `run-example` requires a new `--output-directory`.
`check-attempt` additionally requires `--receipt`, `--receipt-sha256`, `--stdout`
and `--stderr`, and may write a verification record with `--output PATH`.

Every command returns machine-readable JSON. Exit zero denotes a completed
preparation or an accepted record; an accepted incomplete receipt must still be
read using `attempt_complete`. The runner returns nonzero for an incomplete
attempt. None of these outcomes changes release authority.

## Validation and remaining work

The regression module is registered once in Tools. Live entries rise from 187
to 188, with current count consumers coordinated together; targeted pytest
remains 40. Existing historical count descriptions retain their original scope.

Tests use authored ELF/Python inputs and diagnostic records. Process-plumbing
tests run authored child helpers, including pending output in both streams after
overflow and deadline failures, independent caps, nonblocking cleanup and failed
drain preservation. Entry and syscall tests use isolated synthetic children.
CI does not assume bubblewrap is installed or that its namespaces can
be created. Unsupported host setup is an incomplete attempt, never a skipped
qualification check or successful containment evidence.

All outcomes retain diagnostic-only scope, false `containment_enforced`,
`bootstrap_execution_observed`, `runtime_execution_authenticated`,
`restored_bootstrap_qualified`, `runtime_closure_verified`, `execution_ready`,
`execution_authorized`, `observed_acquisition_supported` and
`production_gate_eligible`; `metric_pass=null` and `authority_effect=none`.

The [entry build path](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_BUILD_v0.md) supplies
the next implementation increment. Remaining work includes an actual reviewed
hosted provenance run, launcher provenance and a reviewed launch host, a bounded
example proving the boundary on that host, independently bound runtime and loader
observations, and reviewed selected-bootstrap integration. Actual reference
execution still requires separate owner authorization. B3, B4 and B5 remain
subsequent work. Preserve the original `43514702328/1` artifact, Q2 FAIL 49/50 plus
1 UNKNOWN, all twelve unsupported gates and historical Q3 scope; keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Primary implementation references

- [Bubblewrap v0.12.0 source](https://github.com/containers/bubblewrap/blob/v0.12.0/bubblewrap.c): argument bounds, environment replacement, descriptor handling and launch ordering.
- [Bubblewrap options](https://github.com/containers/bubblewrap/blob/v0.12.0/bwrap.xml): explicit namespaces, read-only data mounts and seccomp input.
- [Linux seccomp filters](https://www.kernel.org/doc/html/next/userspace-api/seccomp_filter.html): syscall filtering and inheritance across exec.
- [Linux no-new-privileges](https://www.kernel.org/doc/html/latest/userspace-api/no_new_privs.html): privilege constraints and their scope.
