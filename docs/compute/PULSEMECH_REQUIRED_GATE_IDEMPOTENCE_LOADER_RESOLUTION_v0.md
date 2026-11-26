# B2 bounded original-loader acquisition and independent replay v0

## Status and scope

This unit implements a separate request, original-loader collector and raw
capture checker for the finite interval selected by the
[loader-resolution plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_PLAN_v0.md).
It supplies implementation and scripted regression coverage. It contains no
new original-loader run, successful native capture, workflow dispatch or hosted
attestation.

The subsequent [hosted execution and independent replay route](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_HOSTED_v0.md)
provides a separate manual workflow, complete offline environment and custody
contract for this collector. Its implementation does not itself perform a run.
The [first owner-dispatched hosted attempt](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_HOSTED_v0.md#first-hosted-attempt-455866533791)
stopped incomplete at cp0; its preserved process samples now cover the specific
residency-accounting regression described below.

The selected historical entry capture and completed
[two-slot probe](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_HOSTED_v0.md)
retain their original meanings. Neither is a live prefix for a new process.
The existing exec-stop, entry-stop and authored-fixture profiles are unchanged.
Their acknowledgement tokens do not authorize this profile.

A later completed native original-loader capture can establish the nine selected consumer/provider
returns and the original executable entry checkpoint for that one attempt.
It does not establish whole-runtime closure, namespace containment, Q2/Q3
measurement, selected-bootstrap execution or a production release decision.
[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open with its complete whole-runtime scope. `b2_complete=false`,
`metric_pass=null` and `authority_effect=none` remain explicit.

## Implementation inventory

| File | Responsibility |
| --- | --- |
| [Request and admission](../../tools/required_gate_idempotence_loader_resolution_v0.py) | Fixed request, source inventory, limits and fresh original/rebuild-policy admission |
| [Preparation adapter](../../tools/prepare_required_gate_idempotence_loader_resolution_v0.py) | Data-only preparation/replay commands, separate owner execution command and exclusive bounded publication |
| [Collector](../../tools/collect_required_gate_idempotence_loader_resolution_v0.py) | Fresh fixed probes, owned original process, finite hardware-stop controller and cleanup |
| [Raw readout reconstruction](../../tools/required_gate_idempotence_loader_resolution_readout_v0.py) | Native checkpoint, initial-stack, mapping, backing-byte and occurrence reconstruction |
| [Independent checker](../../tools/check_required_gate_idempotence_loader_resolution_v0.py) | Closed capture, raw inventory, process/qualification continuity and lifecycle verification |
| [Capture schema](../../schemas/required_gate_idempotence_loader_resolution_v0.schema.json) | Closed completed/incomplete capture structure |

Regression tests are appended to the already registered
[containment test module](../../tests/test_required_gate_idempotence_containment_v0.py).
No additional test file or workflow registration is required. The README,
historical records, existing native profiles and earlier fixture contracts are
unchanged.

## Admission precedes capability probes

The request binds its exact bytes, a fresh 32-hex attempt identity, the selected
observer executable, all six original ELF objects, the selected static recipe,
the nine declaration obligations, fixed invocation, guard program, limits and
the closed implementation-source roster. Constructing a request makes no
acquisition or successful qualification claim.

Before any capability probe or original fork, the public collector calls
`reconstruct_admission`. It reconstructs the complete preserved original
distribution case: 111 selected original files, 43 historical sources, the
launch-host/containment relationships, package contents and a fresh signature
verification at the original explicitly selected evaluation epoch. The two
old reports are fixed comparison oracles; they are never accepted instead of
running the verification chain. The new original request and native obligations
must equal those freshly derived from these bytes.

The original trust policy also selects the external verification executable:
`/usr/bin/gpg`, exactly 1,230,080 bytes with SHA-256
`7c9d2f9416aabcd10199e2984439f49612644a948279ac56bdf70d69c8958ddf`.
The original archive does not supply this executable. Preparation, acquisition
admission and replay therefore need an environment that provides these exact
bytes and their working runtime dependencies. A different GPG installation
fails with `signature_verifier_binding_mismatch` before capability probes or
original execution. The collector does not rewrite that policy to match the
current machine. The earlier
[hosted exec-stop environment](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_GITHUB_v0.md)
documents the selected verifier and runtime provisioning; its historical run
does not qualify a new collector environment.

The same call freshly reconstructs the
[rebuild acceptance policy](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_REBUILD_ACCEPTANCE_v0.md)
and all its preceding source, package and selected-signature relationships.
The caller must supply the independently selected exact policy SHA-256:

```text
1b1e4f414ffa7e56a8494f8a6d6051594c800cae978fa90585c4a02041bed953
```

Its presence in this document or in a request is not project adoption. The
trusted embedding caller selects it explicitly; neither a capture nor a saved
report supplies that decision. The policy retains its current-service
endorsement and unsigned source-association trust assumptions, truncated public
log and unresolved historical authority. The new collector does not turn these
assumptions into independently authenticated historical build provenance.

The bounded raw-carrier override API has a closed roster. It accepts bytes and
the named prior-verifier byte maps, not success booleans, readiness fields,
admission reports or replacement verification functions. Source bindings are
rechecked after reconstruction. A mismatch stops before probes and before the
original process.

## A new, separately acknowledged execution boundary

Only `run-owner` enters the native producer. Its exact acknowledgement is:

```text
OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY
```

This token covers the existing fixed task-guard qualification and fixed two-slot
probe as immediate preflight, followed by at most one bounded original-loader
attempt. It does not authorize a retry, an alternative launcher, a full runtime
run or a later continuation beyond entry.

The native producer obtains fresh raw guard and two-slot qualification records
itself in the current observer process. It does not accept a historical
qualification success flag. The raw records are independently checked and
bound to the current kernel, boot, namespaces, observer executable and process
continuity. Fresh observer state and context are checked again before the
original fork. An explicitly supplied backend always produces
`scripted_test_backend` evidence. The public native verifier rejects that
origin; the separate scripted verifier retains false native-observation claims.
An origin label and consistent raw records are not external authentication of
physical execution. The native verifier's narrow observation flags describe
its reconstruction of a native-profile record; physical authentication and
future-host admission remain false.

The original invocation is fixed:

```text
kernel interpreter startup
argv = ["bubblewrap"]
environment = {"LC_ALL": "C", "TZ": "UTC"}
cwd = "/"
AT_SECURE = 0
```

The fresh child has the existing qualified task-creation filter installed before
exec, with its installation receipt, program bytes, inherited-descriptor
inventory and subsequent process status preserved. The launcher is the exact
original sealed memfd. Original host-backed libraries are pinned and read in
full. Preload controls, initial stack, auxv, actual working directory and process
identity are evidence obligations. `/etc/ld.so.preload` must be freshly observed
as absent or as a stable, empty regular file, before fork, before the first
continuation and at each checkpoint. The child's pinned root and `etc`
directory must retain the complete selected metadata, including change and
modification times; ordinary reads do not alter the retained fields. A missing
file is distinguished from permission, symlink and other read errors. A pathname
alone never identifies a selected original object.

## Finite controller

At fresh kernel exec-stop (cp0), the checker derives the original loader bias,
the original executable entry address and the initial stack. Only the original
launcher and interpreter must be mapped at cp0. The other four pinned original
files are inputs for later checkpoints, not claims of current mappings.

Both execution breakpoints remain armed until termination:

- `DR0`: fresh original loader bias plus the qualified return instruction at
  ELF virtual address `0x3671`.
- `DR1`: fresh `AT_ENTRY`, equal to the original launcher bias plus its ELF
  entry address.
- `DR7=5`; only `DR0`, `DR1`, `DR6` and `DR7` may be written, with exact selected
  values and readback. General registers, code bytes and instruction pointers
  have no write path.

| Operation or event | Completed-capture requirement |
| --- | ---: |
| Continue before exec | 1 |
| Continue from cp0 through nine returns to entry | 10 |
| Total `PTRACE_CONT` | 11 |
| Unique selected dependency-return observations | 9 |
| Final original executable entry stop | 1 |
| Continue after entry | 0 |

Every return must have the selected exclusive slot-0 cause, expected stopped
signal/siginfo and instruction address. Entry requires the exclusive slot-1
cause. The Linux-visible resume flag must be set and the trap flag clear at
hardware execution stops. DR6 is cleared and verified before each continuation.
No single-step, syscall tracing, software breakpoint, register repair or detach
fallback exists.

The return breakpoint remains active after return nine. A tenth hit is an
unexpected event: preserve the available prefix, kill and reap the owned child,
and make no further continuation. Early entry, duplicate/missing occurrences,
unknown objects, changed bytes, unexpected waits, failed guard/identity checks
and timeouts also remain incomplete. There is no implicit retry or deadline
extension. Relocation, IFUNC and initialization code can execute during this
finite interval; stopping at executable entry does not imply that no userspace
code has run.

## Raw observations and independent reconstruction

The new native readout path has its own record and validation semantics. It
reuses bounded parsers where appropriate, but does not relabel an authored
fixture as native evidence or call an authored-fixture acceptance branch to
obtain native claims.

At each selected loader return, two stopped samples preserve registers,
debug-register state, maps, auxv, process status and selected memory. The
qualified argument pointer comes from RBX; the returned provider map comes from
RAX. The checker independently reconstructs the 40-byte argument structure,
56-byte consumer/provider map prefixes, base namespace, self `l_real`, original
dynamic-table and string-table addresses, and exact needed-name bytes including
NUL. It selects one original consumer/name occurrence by these joins. Event
order and the static expected provider are not observation evidence.

Intermediate checkpoints require the relevant mapped objects and reject
unselected file mappings. They do not require all six libraries to be present
before the loader has reached them. The terminal entry checkpoint requires the
complete selected six-object mapping coverage and paired original RX bytes.
The original immutable loader RX bytes are checked at every return.

### Process identity and resident-memory accounting

The collector and native checkpoint decoder validate both complete original
`stat` and `status` samples. They permit a difference only in the numeric value
of `stat` field 24 (`rss`) and the five explicitly named `status` quantities
`VmHWM`, `VmRSS`, `RssAnon`, `RssFile` and `RssShmem`. These are nonnegative,
bounded resident-memory accounting values; status units must remain `kB`.
Duplicate fields, changed field membership, malformed quantities and changes
to every other field remain rejected. Both raw samples and their separate
digests stay unchanged in the capture.

Linux documents [RSS accounting as asynchronous](https://docs.kernel.org/filesystems/proc.html).
Reading a stopped process's memory may fault in pages without resuming that
process. Residency counters therefore do not serve as process-identity or
unchanged-code evidence, and the checker does not require their totals to agree
across separately sampled procfs files. `RssAnon` belongs to the same explicit
resident-accounting family; this exception does not extend to arbitrary
`Rss*` or `Vm*` names, `VmPTE`, `VmSwap` or virtual-size fields.

PID/TGID, parent, tracer, starttime, tracing-stop state, one-thread identity,
pidfd ownership, credentials, capabilities and guard state retain their checks.
Registers, maps, auxv, debug registers, stack samples and selected memory remain
exact comparisons. Setup-to-exec continuity retains its existing identity
checks; it does not require the pre-exec process name or address layout to
survive exec. Historical authored-fixture validators retain their original
strict byte-comparison contracts.

Initial-stack evidence includes the complete bounded control structure, argv
and environment terminators, the entire auxv with terminator, and exactly the
three permitted strings. General raw environment capture is not introduced.
Packed memory samples carry exact range/offset/length manifests; omission,
overlap, surplus bytes and out-of-range pointers reject.

### Fresh reads with deduplicated storage

Every checkpoint performs new full reads through pinned original file
descriptors, with before/after device, inode, mode, size, link-count and time
metadata. The evidence binds each read to that checkpoint and compares its
bytes with the original selection. Mapping identities must join these same
backing objects. Reusing a previously computed hash is not a new read.

Byte-identical results share a content-addressed raw blob. The per-checkpoint
acquisition records remain distinct. This keeps complete repeated backing-byte
evidence within the unchanged 64 MiB live-capture bound. Checkpoint member
counts count distinct referenced paths, including backing blobs. Executable
readback can share the same original launcher blob only after its separate
actual read succeeds.

### Bounds and publication

| Bound | Value |
| --- | ---: |
| Original observation / owned cleanup | 15 seconds / 2 seconds |
| Owned original tracees | 1 |
| Wait records | 20 |
| Accepted / maximum preserved return events | 9 / 10 |
| Raw members / total raw bytes | 512 / 67,108,864 |
| Control document / proc member | 1,048,576 / 65,536 bytes |
| Members / selected runtime ranges per checkpoint | 32 / 32 |
| Runtime window / samples | 4,096 bytes / 2 |
| Packed runtime samples | 2 × 131,072 bytes |
| Loader RX sample | 160,721 bytes |
| Needed name including NUL / pointer indirections | 256 bytes / 4 |
| Mapping rows | 128 |
| stdout / stderr | 4,096 bytes each |

The fixed preflight probes retain their own existing deadlines. They occur
before the original observation interval. The source/debug prerequisite
carriers and earlier original-input archive remain separately pinned inputs;
they are not silently copied into the live capture or charged as runtime
measurements. The journal has an additional closed bound of 256 operations,
without increasing the allowed execution counts.

The adapter creates a new private directory, writes bounded flat files
exclusively, verifies the preserved bytes and publishes `capture.json` last.
An existing file/directory is not overwritten. Publication failure records an
incomplete marker where possible and cannot publish an accepted result.
Incomplete acquisition prefixes retain their raw members and owned cleanup
records. The replay reader rejects a failed-publication marker and independently
checks every raw member; `verification.json` is output, never an input oracle.

## Command interfaces

All commands run from the repository root with the project's Python
dependencies. `--help` describes the exact interfaces without running probes:

```bash
python -B tools/prepare_required_gate_idempotence_loader_resolution_v0.py --help
```

`prepare` takes a fresh caller-selected `--attempt-id`, the independently selected
`--accepted-policy-sha256` and a new `--output` path. It binds the current
observer and reconstructs admission before writing the request. `check-request`
requires the request path and an externally selected request SHA-256 and repeats
admission. Neither command qualifies the host or runs the original launcher.

`run-owner` additionally requires the new exact acknowledgement and a new
`--output-directory`. It must be invoked only in a separately selected and
reviewed execution environment. This implementation does not add or dispatch
a hosted workflow. No command line with invented future attempt IDs, source
commits or successful run results is supplied.

`check-capture` accepts the preserved request and capture directory, both
external SHA-256 selections, the separately selected policy digest and a new
report output path. It reconstructs the raw prerequisite chains and the capture
without rerunning the original or capability probes. Signature verification
uses the existing bounded verifier subprocesses; replay does not execute any
preserved payload code. Replay reports bind the preserved admission diagnostics
and the stable freshly reconstructed facts. Fresh verifier PIDs, descriptor
numbers, execution times or OpenSSL host metadata cannot make the normative
report differ for the same selected capture. Preserved verifier diagnostics
are checked for consistency, without being treated as physical authentication
of the earlier verifier process.

## Verification and next boundary

The regression suite exercises explicitly scripted events, invalid requests,
raw-byte mutations, the actual native proc dispatcher with substituted reads,
the closed ptrace surface, qualification/context joins, finite continuations,
incomplete cleanup and exclusive publication. It does not execute the original
launcher, qualify a host or manufacture a native run record.

The tests distinguish three verification responsibilities:

- Structural admission and collector tests use an explicitly scripted
  original-signature execution boundary. They assert the exact historical
  policy and original inputs, retain the original signature parser and sealed
  input checks, and reconstruct the original byte relationships and rebuild
  acceptance chain. Rebuild attestation checks still use real OpenSSL. The
  scripted signature process is not a successful execution of the historically
  pinned verifier.
- Separate cryptographic tests run the unchanged GPG verification code on the
  original Release, detached signature and keyring, with the original selected
  signers and evaluation epoch. These tests explicitly bind the current test
  host's verifier in a test-only argument set and also reject altered signed
  bytes. They do not change the archived trust policy or establish admission
  under its historical verifier selection.
- A production-path regression supplies a different verifier file to the real
  bounded file reader and requires rejection before a verifier subprocess,
  capability probe or original process can start. It does not depend on the
  test host already differing from the historical environment.

This separation keeps the portable suite meaningful on CI hosts whose GPG
bytes differ from the original selection. Complete unmodified admission under
the historical policy still requires the exact selected verifier environment;
portable tests do not certify that an arbitrary CI runner meets that condition.

The next execution step requires an owner-selected environment, exact merged
source and policy selection, one separately acknowledged fresh attempt, complete
result custody and independent replay. A successful implementation test is not
that result. Even a later successful nine-return capture leaves the remaining
B2 and whole-runtime obligations open.
