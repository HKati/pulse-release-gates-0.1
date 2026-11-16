# Fixed-probe stopped executable mapping observation v0

## Status and scope

**A separate example-only observation primitive connects an exact authored
static executable, a retained sealed file object, the owned stopped child's
actual executable descriptor and the kernel-reported mapping of that object.
The observation is a cooperative post-exec checkpoint. The original launcher,
hosted entry, selected runtime, operator and model remain unexecuted by this
profile; B2 is incomplete.**

The [distribution authentication result](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LAUNCHER_DISTRIBUTION_v0.md)
already checks the signed publication-to-index-to-package-to-launcher
relationship under its independently selected trust policy. The
[launch-host plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LAUNCH_HOST_v0.md) preserves
selected static native dependencies and a passive host observation. Those
original records retain their bytes and claims.

This continuation develops one of the observation mechanisms needed by the
remaining host/native investigation. Its subject is a new fixed probe, not the
original launcher or its dependency graph. The child's own output is not used
to establish which object was mapped: the parent obtains the executable object
and process/mapping evidence from the kernel while retaining its original
immutable object handle.

## Fixed example and selected inputs

The profile is `linux_x86_64_fixed_probe_stopped_mapping_v0`. It admits only the
exact built-in 4096-byte Linux x86-64 ELF. It has one read/execute `PT_LOAD`
page at `0x400000`, an explicit non-executable `PT_GNU_STACK`, and no interpreter
or dynamic-library dependency. The bytes are constructed directly; the
collector invokes no compiler, assembler, package manager or selected runtime.

The probe accepts only the expected parent PID as eight lowercase hexadecimal
digits. It sets a
parent-death `SIGKILL`, checks that its parent is still the expected process,
then reaches a `SIGSTOP`. If execution continues unexpectedly it terminates
with a nonzero result. The collector never resumes it. The observed stop is
reported as `SIGSTOP`; the wait result alone is not a proof of who sent it.

There is no caller-provided executable, command, interpreter, alternate probe
or native target directory. A static ELF header by itself cannot admit different
bytes into this profile.

The external selection binds the attempt identity, fixed probe bytes, exact
collector/checker/probe/schema source roster, selected observer executable and
finite bounds. An independently retained selection digest is required before
collection. The attempt identity distinguishes occurrences; it is neither a
trusted timestamp nor an attestation of execution.

The selected bounds are fixed by this profile:

| Boundary | Limit |
| --- | --- |
| Observation deadline | 15 seconds |
| Owned-child cleanup opportunity | 2 seconds, also available after a failed observation exceeds its deadline |
| Completed capture timing | At most 17 seconds from attempt start through cleanup |
| Each raw proc file | 65,536 bytes |
| Selected observer executable | 33,554,432 bytes |
| Each preserved output stream | 4,096 bytes |
| Total preserved raw bytes | 41,943,040 bytes |

These are collector admission, polling and acceptance bounds. They do not make
an external kernel operation preemptible or establish whole-host resource
containment. A late or otherwise incomplete attempt cannot qualify as a
completed observation.

## Acquisition and the observed relationship

One attempt creates a new private evidence directory and preserves the selection
and attempt start before launching its owned child. The parent retains the
sealed executable descriptor throughout capture and cleanup. It obtains a
pidfd and pins the child's proc directory; all child evidence is read relative
to that owned process occurrence.

At the cooperative stop the parent preserves the actual executable descriptor's
bytes, stat identity and seals, the retained object's bytes and identity, bounded
raw process stat/status/maps before and after inspection, and the observed host
context. It does not reopen a pathname printed in a maps line as a substitute
for the actual executable object.

The checked relationship requires all of the following together:

- The kernel wait result identifies the expected child's `SIGSTOP`.
- The child has one thread, the expected parent, a stable process start identity
  and stopped state around capture.
- The retained and actual executable descriptors identify the same device and
  inode, have the full required seals, and contain the exact fixed probe bytes.
- Every file-backed mapping occurrence is interpreted independently. The exact
  executable mapping has the expected range, offset and permissions and contains
  the fixed entry point. A matching occurrence cannot excuse another wrong one.
- The before/after maps remain equal. Unknown file-backed or anonymous executable
  mappings, duplicate/overlapping ranges and unexpected process events reject
  completion.
- The parent observes terminal cleanup after `SIGKILL` and reaps its owned child.
  The expected terminal status is signal termination, not an ordinary successful
  probe exit.

Kernel-labeled mappings such as `vvar`, `vdso`, `vsyscall` and the stack are
retained separately. Their labels do not authenticate their memory contents.
The relationship concerns a mapped **backing object**. Private/relocated memory
pages, executed instruction history and complete native closure are not measured
by this observation.

## Preservation and independent reconstruction

Raw evidence is preserved with an exact bounded file roster. The terminal
capture record binds that roster without containing its own hash. Checking
requires the externally selected capture digest as well as the original
selection digest. The independent checker does not import the collector.

The checker reconstructs the process occurrence and every object/mapping
relationship from the original preserved bytes. It checks the fixed source and
probe identities and rejects cross-attempt substitution, rehashed inconsistent
records, missing raw evidence and changes to authority boundaries.

Two separate checker processes over the **same preserved capture** should
produce byte-identical canonical reports. Separate live captures retain their
different process IDs, clock values, mappings and occurrence identities; those
differences are not removed to manufacture identical observations.

Timeout, an unavailable kernel operation, an early child exit, unreadable proc
evidence, capture overflow or incomplete cleanup remains an incomplete attempt.
An accepted incomplete record never reports a completed mapping observation.
Failed preservation cannot publish a normal successful terminal record.
Existing output directories and files are not overwritten, and the collector
does not retry, resume or choose an alternate observation profile.

The producer reopens the preserved files through the held private directory
before and after publishing the capture. It checks the exact roster, original
file identities, private modes and bytes. Both the producer and directory
reader recheck every file identity after the complete read pass, so a change
to an earlier-read file during a later read cannot satisfy that pass. These
finite checks do not promise that another actor can never modify files after
verification; the external digests remain necessary for every later replay.

## Trust and claim boundaries

The observer relies on the local Linux kernel/procfs, the selected collector
source, its Python interpreter and supporting environment. Pinning source and
executable bytes does not authenticate the complete observer runtime or a
hostile kernel. Offline reconstruction checks the selected preserved evidence;
arbitrary authored JSON does not prove that a physical historical event occurred.

The new narrow result describes the fixed probe's stopped executable
backing-object relationship. Physical execution authentication, whole-host
qualification, process-memory equality, complete native closure, launcher/loader
coverage, containment, selected-runtime execution and release eligibility remain
separate claims. `authority_effect=none` and `metric_pass=null` remain unchanged.

This profile is deliberately separate from ptrace exec-event observation. An
earlier local feasibility attempt returned `PTRACE_TRACEME: EPERM` before target
exec and reaped its child. That negative result is retained separately. The
cooperative profile does not convert it into success and does not claim
interception before the first userspace instruction.

## Implementation and commands

| Component | Responsibility |
| --- | --- |
| [Fixed probe](../../tools/required_gate_idempotence_mapping_probe_v0.py) | Construct the exact authored static ELF and document its finite instructions. |
| [Collector](../../tools/required_gate_idempotence_mapping_observation_v0.py) | Admit one selection, preserve an owned stopped-process observation and perform bounded cleanup. |
| [Independent checker](../../tools/check_required_gate_idempotence_mapping_observation_v0.py) | Reconstruct the raw evidence relationship and emit a canonical, non-authorizing report. |
| [Closed schema](../../schemas/required_gate_idempotence_mapping_observation_v0.schema.json) | Define the example selection, capture and report boundaries. |
| [Registered containment regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Exercise the live authored probe, occurrence-level substitutions, incomplete records and preservation failures. |

Prepare a new selection using a separately chosen 32-character lowercase hex
attempt identity. Retain the exact resulting digest independently before running
the example. All paths below denote new outputs or the preserved originals;
uppercase hash and identity placeholders must be replaced with selected values.

```bash
python3 -I -B tools/required_gate_idempotence_mapping_observation_v0.py prepare \
  --attempt-id ATTEMPT_ID_HEX32 --output /absolute/review/selection.json

python3 -I -B tools/required_gate_idempotence_mapping_observation_v0.py run-example \
  --selection /absolute/review/selection.json \
  --selection-sha256 SELECTION_SHA256 \
  --output-directory /absolute/review/new-mapping-attempt

python3 -I -B tools/check_required_gate_idempotence_mapping_observation_v0.py \
  --selection /absolute/review/selection.json \
  --selection-sha256 SELECTION_SHA256 \
  --capture-directory /absolute/review/new-mapping-attempt \
  --capture-sha256 CAPTURE_SHA256 \
  --output /absolute/review/new-independent-report.json
```

Checker acceptance is interpreted together with `observation_complete` and the
narrow relation fields. It is not an execution permit. The example runner
returns nonzero for an incomplete attempt even if the incomplete record itself
is structurally accepted.

## Completed local observation

The final source-bound local attempt is
`aa22afde5f3640628e33afe6db2e1f5f`. Its preserved capture is `completed`;
both separate independent checker processes exited zero and emitted exactly
the same accepted 1052-byte canonical report. All 20 raw files and the terminal
capture are retained in the separate delivery validation bundle.

| Preserved item | Bytes | SHA-256 |
| --- | ---: | --- |
| Exact fixed probe | 4096 | `dfa1de8166ef6447cc053ca82abf4fd443757e926bc8dd4097c9afbfd7bb2c1a` |
| External selection | 1861 | `174ad9652c493763b202b27a04142e9272a5e93c35a0bbe5abbf8fd281861ce4` |
| Terminal capture | 3721 | `3a432d3ecbff8f1bf9164217b8a70b1cfd4fd4d8cb37dd5216d23f6a7af496ce` |
| Independent report 1 | 1052 | `83bb9bc1e908354cf33474643b04cefa8378f64aeadaa1d92988e6c3ec3616be` |
| Independent report 2 | 1052 | `83bb9bc1e908354cf33474643b04cefa8378f64aeadaa1d92988e6c3ec3616be` |

The retained and proc-executable descriptors both recorded device `1`, inode
`8205`, size `4096`, mode `0500`, link count `0` and seals `15`. The exact RX
mapping spans `0x400000` through `0x401000` with offset `0`. Before/after maps
agree. Initial wait status `4991` records the `SIGSTOP`; terminal status `9`
records `SIGKILL`, with the child reaped and no resumption recorded. These
identifiers describe this occurrence only; future attempts retain their own.

The completed report sets `observation_record_verified`,
`observation_complete`, `stopped_executable_backing_relation_verified` and
`sealed_executable_object_binding_verified` to `true`. The trust and authority
boundaries above remain in force. This is an actual local authored-probe
observation, not a GitHub-hosted run or an observation of the original launcher.

## Validation and remaining work

The delivery validation retains the actual fixed-probe capture, both independent
checker outputs, raw failure evidence and regression results separately from the
repository file package. Authored parser/mutation fixtures remain distinguishable
from the actual local process observation. The earlier ptrace-denied and simple
cooperative feasibility records retain their original, different probe bytes;
neither is relabeled as this final source-bound attempt.

The complete registered containment module passed **505 cases** under the
repository-pinned CPython **3.11.16**: all **409 existing cases** plus **96 new
mapping-observation cases**. Every original top-level test statement after the
module docstring, including all 114 prior test functions and their parameters,
is unchanged. The new cases include a real stopped capture and independent
replays, actual parent-death termination, wrong-parent rejection, per-occurrence
process/object substitutions, incomplete cleanup, bounded malformed input and
live preservation mutations. The existing CI manifest smoke check also passed.

The existing containment test module is extended without adding a CI entry;
Tools remains 189 and targeted pytest remains 40. No workflow, dependency pin,
existing runtime/containment implementation or original evidence archive changes.

The next observed launcher work must bind the original selected executable and
every relevant loader/library occurrence across its actual process transitions,
then independently observe the intended namespace/filesystem/filter/descriptor
and resource behavior. This fixed-probe observation is a tested primitive for
that work, not a record that those original transitions occurred.

Reviewed selected-bootstrap integration and separately authorized actual
reference execution remain open. B3, B4 and B5 retain their original order.
Broader Step 6 resource measurement and Step 7 policy promotion remain separate.
Preserve the original `43514702328/1` artifact, both `43854478248/1` ZIPs, Q2
`FAIL 49/50 +1 UNKNOWN`, all twelve unsupported gates and historical Q3 scope;
keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Primary implementation references

- [Linux proc executable descriptor](https://man7.org/linux/man-pages/man5/proc_pid_exe.5.html): opening the actual executable and its access checks.
- [Linux proc mapping format](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html): address, permissions, offset, device/inode and pathname ambiguity.
- [Linux memfd](https://man7.org/linux/man-pages/man2/memfd_create.2.html): retained file-object identity and sealing.
- [Linux child wait results](https://man7.org/linux/man-pages/man2/waitpid.2.html): stopped, continued and terminal child states.
- [Linux pidfd](https://man7.org/linux/man-pages/man2/pidfd_open.2.html): owned process identity and signaling/wait relationships.
- [Linux parent-death signal](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html): signal setup and parent-lifetime constraints.
- [Linux proc filesystem](https://docs.kernel.org/filesystems/proc.html): retained proc descriptors do not retarget a later process reusing the PID.
