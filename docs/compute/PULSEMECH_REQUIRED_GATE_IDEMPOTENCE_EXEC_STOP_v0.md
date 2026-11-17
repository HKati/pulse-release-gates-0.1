# B2 original launcher exec-stop acquisition v0

## Purpose and present result

This unit provides a closed original-input request, an owner-invoked collector
and an independent checker for the **original selected bubblewrap executable
and its ELF interpreter at the first kernel exec stop**. It continues from the
observed distinction between unchanged backing bytes and separately sampled
process memory in the
[private-memory transition observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_MEMORY_OBSERVATION_v0.md).

Preparation reconstructs the preserved original chain, freshly verifies the
Debian signatures at the unchanged selected evaluation epoch, and derives the
exact objects, segment occurrences, entry relationships and memory samples.
The collector implements the bounded attempt for a separately selected eligible
owner environment. **No live original-launcher exec checkpoint was acquired
while preparing this package.** Synthetic regression transcripts are test
evidence. The earlier live authored-probe observations retain their original
subjects, claims and source-bound report bytes.

```text
linux_x86_64_original_launcher_exec_stop_v0
```

This profile accepts the exact original byte selections. It has no arbitrary
command, executable replacement, memory address, loader override or post-exec
continuation option.

## Original inputs and fresh reconstruction

The complete original-input case is selected by:

```text
CASE_INPUTS.json
16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa
```

Every preparation or request check reads all **111 selected original members**,
requires all **43 historical verification sources** to remain byte-identical,
and reconstructs the existing bootstrap, containment, entry-build, launch-host
and distribution relationships. The existing independent distribution checker
performs fresh signature verification and preserves its diagnostics. The saved
replay program is preserved as an input; the new adapter never imports or runs it.

The old launch-host and distribution results must equal their original canonical
bytes. A saved accepted report alone cannot satisfy admission. The original
Release, detached signatures, complete compressed and decoded Packages index,
keyring, trust policy, Debian package and all fifteen hosted entry-build files
are retained in the companion validation archive, together with the old sources.

The signature policy still evaluates the publication at epoch **1794787200**
(2026-11-16 00:00:00 UTC). Fresh cryptographic verification is not a new network
acquisition, a current trust-policy decision or an acquisition timestamp.
The authenticated publication chain covers the bubblewrap package; it does not
authenticate all selected host libraries merely because they are in the inventory.

The preserved bootstrap/runtime capsule remains the **authored inert fixture**.
Original launcher/native bytes and hosted entry-build evidence do not turn that
capsule into the actual Q2 runtime. This profile does not execute that runtime.

### Exact initial images and memory occurrences

| Role | Preserved input | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Launcher | `native/bwrap` | 80,248 | `573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f` |
| Interpreter | `native/ld-linux-x86-64.so.2` | 225,672 | `c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307` |

The launcher is an x86-64 PIE with virtual entry `0x5590` and unchanged
`PT_INTERP` string `/lib64/ld-linux-x86-64.so.2`. The interpreter has virtual
entry `0x1d2c0`. Each image has four `PT_LOAD` segments. All eight segment
occurrences are independently checked; eight segments need not mean eight
maps-file rows.

| Object | File offset | ELF virtual address | Bytes per sample | Samples |
| --- | ---: | ---: | ---: | ---: |
| Launcher RX segment | `0x3000` | `0x3000` | 39,761 | 2 |
| Interpreter RX segment | `0x1000` | `0x1000` | 160,721 | 2 |

These four samples total **400,964 bytes**. Each has its own object,
program-header and sample occurrence. Both samples must independently match the
corresponding original file extent. Segment mapping coverage and RX byte
equality are separate obligations. RW, BSS, padding and other memory contents
are not silently included in the RX equality claim.

Four other selected objects remain explicitly unobserved at this checkpoint:
`libc.so.6`, `libcap.so.2`, `libpcre2-8.so.0` and `libselinux.so.1`.
The twelve original per-consumer dependencies remain a static graph, not twelve
inferred dynamic load events. A library's `PT_INTERP` is not recursively invoked
merely because the library is a dependency.

## One kernel event and no post-event restart

The fixed sequence is:

1. Reconstruct the original inputs and verify the selected request and sources.
2. Pin the object reached through the exact host interpreter path and compare
   its bytes with the selected interpreter before creating the child.
3. Prepare and retain the unchanged launcher in a sealed executable memfd.
4. Create the owned authored setup child, establish parent-death termination
   and `PTRACE_TRACEME`, and observe its pre-exec setup stop.
5. Pin child identity, proc directory and pidfd. Set
   `PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL`; make the single pre-exec restart.
6. Require `PTRACE_EVENT_EXEC`. A plain SIGTRAP or cooperative SIGSTOP cannot
   satisfy this checkpoint.
7. Open actual executable and process-memory descriptors **after** the event;
   preserve bracketed process/maps/register/auxv evidence and all selected
   memory samples while the child remains stopped.
8. Kill and reap the owned child, drain bounded pending output, verify the
   preserved disk prefix, and publish the capture.

There is no continuation or detach after the exec event, breakpoint patch,
register write or target-memory write. The selected event is before the new
interpreter's first userspace instruction. A complete capture means the kernel
installed the original image and the observer checked the selected relationships
there. It does not mean the original containment command was run.

The checker ties raw registers and the auxiliary vector to the exact ELF images:

```text
RIP      = AT_BASE + interpreter entry
AT_ENTRY = launcher load bias + launcher entry
AT_PHDR, AT_PHENT and AT_PHNUM = original launcher program-header layout
AT_PAGESZ = 4096
```

The child remains the same owned single-thread process and reports the observer
as `TracerPid`. Each selected mapping interval must have the required object
association, offset and permissions. Missing, duplicated or inconsistent
occurrence evidence rejects completion.

## Interpreter identity and eligible environment

The fixed interpreter path intentionally follows its normal host symlinks.
The collector pins the resulting regular object with `O_PATH`, opens that owned
object through its proc descriptor, and retains the readable descriptor.
Kernel-reported mapping device/inode and ELF offsets must agree with that
descriptor. Pathname text does not establish the association. The actual child
executable descriptor must separately match the retained sealed launcher object.

This is the explicitly selected retained-descriptor and kernel-mapping method.
It does not claim an opened `map_files` handle. The earlier local tracing and
`map_files` denials remain preserved negative observations.

An eligible owner environment must already provide Linux x86-64, 4,096-byte
pages, the exact selected loader at the original interpreter path, the required
owned-child tracing/proc/memory operations, and bounded preservation/cleanup.
The selected loader contains Debian GLIBC `2.41-12+deb13u4`; the label alone is
insufficient. Different host loader bytes reject the selected prerequisite
before the original exec attempt.

The collector does not replace a host loader, patch `PT_INTERP`, invoke a copied
loader directly, change sysctls, add capabilities or select an alternate tracing
mechanism. A GitHub Ubuntu runner is not assumed to satisfy the selection.
This unit adds no workflow or automatic dispatch.

## Failed attempts and trust boundary

Wrong host bytes, tracing denial, option failure, unexpected events, short reads,
changed objects, sample mismatches and deadlines remain visible. Every started
child is subject to owned cleanup. Pending stdout/stderr are drained
nonblockingly within their caps before pipe closure. Failed disk preservation
cannot produce a complete accepted capture.

The attempt deadline and separate cleanup allowance are user-space decision
bounds, not guaranteed preemption of an uninterruptible kernel operation.
An unreaped child prevents completion.

Kernel, procfs, observer interpreter, Python environment and host remain external
trusted components. Repeated ordinary-loader reads do not establish immutable
history. Selected memory samples do not authenticate other memory, physical
page residency, every intermediate instruction or the full native closure.

Accepted reconstruction of an incomplete record has no completed checkpoint
claim. A complete record may establish only the explicitly checked exec-stop,
image association, selected RX equality and terminal-cleanup relationships.
The broad fields remain:

```text
host_environment_qualified=false
host_launcher_runtime_verified=false
loader_resolution_verified=false
process_memory_bytes_verified=false
complete_native_closure_verified=false
containment_enforced=false
execution_ready=false
execution_authorized=false
selected_runtime_executed=false
production_gate_eligible=false
metric_pass=null
authority_effect=none
```

Owner acknowledgement permits the diagnostic acquisition in its selected
environment; it does not change release/runtime authorization fields.

## Completed original-input preparation

On 2026-11-17, the final source-bound request
`a8a2978995f7e24afcbf9dc0f985c272` reconstructed all 111 original members and
the unchanged 43-source historical verification roster. Two separate executions
of the same independent reconstruction accepted the request and produced
byte-identical canonical preparation reports. The preparation's report bytes
also equal those two reports.

| Record | Bytes | SHA-256 |
| --- | ---: | --- |
| New acquisition request | 8,181 | `5032fe3fa99873eecb782895b2667b2d13a9b04c1348322ccb2f8a090f5647f9` |
| Each preparation verification report | 1,244 | `0b705d32e8fc7fa93a17eae27264e6af05e69d1440a7bfe70a5957d4179668ab` |

Preparation and both checks each invoked the separately selected sealed GPG
verifier once, at the unchanged evaluation epoch. The review harness permitted
only that exact offline verifier and rejected original-target execution and
network operations. All ten selected current source files remained unchanged
through these three processes. The companion archive retains the request,
reports, original inputs, verifier diagnostics and process audit records.

The corrected historical mapping report reconstructed unchanged with SHA-256
`b4b21a419cadd4cffc50c56e4164e409d23516f541f473d39ad8914d4b373f45`.
The completed private-memory transition report also reconstructed unchanged
with SHA-256
`0bf00e9b47de670c173d4fdd847639f35c72856c444601287ff4ccf304b86111`.
Neither replay executed its probe or gave the earlier capture a new claim.

This completed result establishes the original-input request and its repeatable
reconstruction. Its report explicitly keeps `original_exec_reached=false` and
`kernel_exec_checkpoint_observed=false`.

All **668 containment regression cases passed** with repository-pinned CPython
3.11.16: 600 preserved cases and 68 added cases. The entire previous 227,859-byte
test prefix is unchanged. Added cases cover every sample and segment obligation,
event/register/auxv linkage, identity substitution, admission before fork,
mocked tracing and option denials, deadlines, owned cleanup, independently
capped pending streams, preparation/collector separation, and FIFO replacement
at three input boundaries. Original-target process operations are mocked in
these new tests. The existing 189 Tools and 40 targeted pytest entries remain
unchanged.

## Components and commands

| Component | Responsibility |
| --- | --- |
| [Preparation adapter](../../tools/prepare_required_gate_idempotence_exec_stop_v0.py) | Fresh original-chain admission, request preparation/checking and explicit owner dispatch |
| [Collector](../../tools/required_gate_idempotence_exec_stop_v0.py) | Owned setup, one exec stop, selected reads, preservation and cleanup |
| [Independent checker](../../tools/check_required_gate_idempotence_exec_stop_v0.py) | Exact request, original ELF obligations and raw-capture reconstruction |
| [Schema](../../schemas/required_gate_idempotence_exec_stop_v0.schema.json) | Closed structural records; semantic reconstruction still requires the checker |
| [Regression module](../../tests/test_required_gate_idempotence_containment_v0.py) | Preserved prior cases and new synthetic acquisition/lifecycle regressions |

Each output and verification directory must be new. The original-input directory
in the companion archive retains its `CASE_INPUTS.json` and `results/` reports.
Use the selected observer interpreter for preparation and later acquisition.
Retain the request digest independently of the request.

```sh
python tools/prepare_required_gate_idempotence_exec_stop_v0.py prepare \
  --originals-directory <original-input-directory> \
  --originals-sha256 16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa \
  --attempt-id <fresh-hex32> \
  --verification-directory preparation-signature --output request.json

python tools/prepare_required_gate_idempotence_exec_stop_v0.py check \
  --originals-directory <original-input-directory> \
  --originals-sha256 16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa \
  --request request.json --request-sha256 <externally-retained-request-sha256> \
  --verification-directory checker-1-signature --output checker-1.json
```

Repeat `check` in another process using separate output paths. Equal canonical
preparation reports establish repeatable reconstruction of one request, not an
acquired original exec checkpoint.

Only after review, owner selection of an eligible environment and separate
authorization for the actual original acquisition:

```sh
python tools/prepare_required_gate_idempotence_exec_stop_v0.py run-owner \
  --originals-directory <original-input-directory> \
  --originals-sha256 16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa \
  --request request.json --request-sha256 <externally-retained-request-sha256> \
  --verification-directory acquisition-signature --output-directory capture \
  --acknowledgement OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY
```

`check-capture` accepts the same original/request arguments, plus
`--capture-directory`, an external `--capture-sha256`, a fresh
`--verification-directory` and `--output`. It repeats original-input admission
before independent capture checking. The lower-level checker reconstructs the
externally pinned request/capture without executing the collector; that narrower
operation does not freshly verify the distribution signatures.

## Continuation of the established plan

The next live observation is the exact original launcher/interpreter cp0 in an
eligible, reviewed owner environment. Later checkpoints must establish actual
library resolution and relevant native occurrences. Executable entry is later
than cp0: loader initialization can run before it, so that experiment needs its
own scope. Observed containment and selected-bootstrap integration follow.

The [existing readiness plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#18-required-gate-coverage-plan-after-accepted-rejection-verification)
keeps B3 property evidence, B4 admission and B5 the actual reference distinct.
Broader Step 6 resource measurement and Step 7 promotion remain outstanding.
Preserve the original `43514702328/1` artifact, both `43854478248/1` archives,
Q2 `FAIL 49/50 +1 UNKNOWN`, all twelve unsupported gates and historical Q3 scope.
Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Primary interface references

- [Linux ptrace events and options](https://man7.org/linux/man-pages/man2/ptrace.2.html)
- [Linux auxiliary-vector fields](https://man7.org/linux/man-pages/man3/getauxval.3.html)
- [Linux mapping records](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html)
- [Linux process memory interface](https://man7.org/linux/man-pages/man5/proc_pid_mem.5.html)
- [Linux mapped-file access](https://man7.org/linux/man-pages/man5/proc_pid_map_files.5.html)
- [Linux file seals](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html)
- [Linux child waits](https://man7.org/linux/man-pages/man2/waitpid.2.html)
