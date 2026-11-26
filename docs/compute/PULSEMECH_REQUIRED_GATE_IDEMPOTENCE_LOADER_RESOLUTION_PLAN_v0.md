# Required-gate idempotence: per-consumer loader-resolution plan v0

## Status and scope

This unit implements an authored proposal, a closed plan schema and an independent
data-only plan checker for the next B2 observation. It selects a finite candidate
mechanism for observing the provider returned by the original loader for each of
the nine selected `DT_NEEDED` occurrences. **It does not implement or perform that
observation.** The original-loader instruction locations and private data-layout
recipes remain unqualified; the new collector, capture schema and raw-capture
checker remain unimplemented.

The development base is `0353b1f5f4e247783098e3275bcac5dcdf10a6f1`, after
[PR #3041](https://github.com/HKati/pulse-release-gates-0.1/pull/3041). The successful
historical entry acquisition remains bound to source
`03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081` and
[run 44740993943, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943).
The later merge commit must not replace that historical source identity.

| Item | State established by this unit |
| --- | --- |
| Historical original entry capture | Reconstructed from its complete preserved capture with the unchanged entry checker. |
| Six original native objects | Exact original bytes, ELF metadata and 24 `PT_LOAD` occurrences rederived. |
| Nine `DT_NEEDED` declarations | Consumer, original dynamic-entry position, name and expected static provider independently derived. |
| Three `PT_INTERP` declarations | Kept separate from dependency-return events; only the launcher has historical kernel-interpreter continuity. |
| Proposed return-event mechanism | Selected with fixed witness, continuity, failure and budget requirements. |
| Exact binary location / ABI recipes | Unsatisfied; plan fields are `null`, not guessed offsets. |
| New trace acquisition / loader-resolution verification | Not performed; both remain false. |
| B2 / issue #2879 / authority | B2 incomplete, issue open, `metric_pass=null`, `authority_effect=none`. |

The current [README](../../README.md) already describes the completed entry
observation and the outstanding per-consumer resolution step. This unit does not
replace or edit it. The ordered B2–B5 obligations remain in the
[reference-readiness plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#186-ordered-implementation-units-and-acceptance-conditions).

## Files and exact proposal identity

| File | Purpose |
| --- | --- |
| [Authored plan](required_gate_idempotence_loader_resolution_plan_v0/plan_v0.json) | Fixed proposed mechanism, independently derived static inventory and explicit unsatisfied gates. |
| [Plan schema](../../schemas/required_gate_idempotence_loader_resolution_plan_v0.schema.json) | Closed structural contract; schema validity is not historical reconstruction or acquisition. |
| [Plan checker](../../tools/check_required_gate_idempotence_loader_resolution_plan_v0.py) | Fresh reconstruction of the selected historical capture, independent ELF derivation and complete proposal comparison. |
| [Containment regression module](../../tests/test_required_gate_idempotence_containment_v0.py) | New `entry_resolution_plan` cases in the already registered module. |

The authored plan is 33,641 bytes with SHA-256:

```text
ff33f96d0095f949763125d67da1159112b067b86c2fe3b5f1302f55cb193d7d
```

The checker requires the exact input digest as an external argument. It does not
place the plan's own digest inside the plan or create a self-hash cycle. It accepts
equivalent JSON formatting only when the caller supplies the digest of those exact
bytes; duplicate keys, non-integer numbers, non-finite values and ambiguous types
are rejected. Its report is canonical JSON.

## Historical prerequisite: what is reconstructed

The selected repository carrier is the existing
[entry control archive](../../preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/control_evidence_v0.zip):

| Property | Required value |
| --- | --- |
| Archive bytes | 5,682,024 |
| Archive SHA-256 | `75c71960080a22c88f78b92c8c9af293cc28dc41a4fbd3916e0f515755a245d0` |
| Members / decoded bytes | 309 / 12,819,181 |
| Complete capture | 78 members, including `capture.json` |
| Historical sources | 81 exact hosted source bindings |
| Request SHA-256 | `15341c355cd90e3e4f11e25f5941196c98ad3de0f4dfa9b05acf9a5472f3aeae` |
| Capture SHA-256 | `f6a8af188cc93ac6ad375ae09252abd7b14e699e4900cca357a6eb165194823d` |
| Canonical historical report SHA-256 | `e8cbdb4e7f25a4701be1f2b699d96702e077368cc1ddbe1d9ccc8189cb8e6bdd` |

The new checker selects those identities independently of the caller's plan. It
reads every bounded ZIP member without extracting paths, checks the capture's
exact roster, reconciles original receipt members, qualification copies, source
inventories and preserved cleanup controls, and calls the unchanged
[`verify_capture`](../../tools/check_required_gate_idempotence_entry_stop_v0.py)
over the original request, capture and 77 raw members. The reconstructed canonical
report must equal both preserved hosted reports and retain all nine narrow entry
flags and the original negative boundaries.

All 81 historical source files are checked before and after reconstruction. The
three historically selected plan/carrier paths have independently fixed read
limits, including the existing 24,816,167-byte original-input ZIP. Ordinary source
and control reads remain capped at 1 MiB. The new checker and schema have their own
separate source bindings; they are never relabelled as historical implementation.

This is lower-level preserved-byte reconstruction. The bounded control selection
omits some dependencies of full hosted replay. The plan checker does not run GPG,
Docker, a collector or the original executable, and does not freshly verify
distribution or attestation signatures. The earlier completed hosted checks keep
their recorded meaning; see the
[entry observation and custody record](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_GITHUB_v0.md#completed-hosted-observation-447409939431).

## Independent static occurrence inventory

The six original native files total 3,262,624 bytes. The checker reads the verified
before/after ELF bytes from the capture, requires their original identities and
equality, and parses the original `PT_DYNAMIC` table and string table directly.
For each dependency it records the consumer file binding, program-header index,
dynamic-entry ordinal, file offset and virtual address, needed ordinal, name,
string-table offset, name file offset and expected provider binding.

| Consumer | Its selected `DT_NEEDED` names, in original declaration order |
| --- | --- |
| `native/bwrap` | `libselinux.so.1`, `libcap.so.2`, `libc.so.6` |
| `native/libc.so.6` | `ld-linux-x86-64.so.2` |
| `native/libcap.so.2` | `libc.so.6` |
| `native/libpcre2-8.so.0` | `libc.so.6` |
| `native/libselinux.so.1` | `libpcre2-8.so.0`, `libc.so.6`, `ld-linux-x86-64.so.2` |
| `native/ld-linux-x86-64.so.2` | None |

Repeated names across consumers remain separate obligations. The four consumers
that request `libc.so.6` require four distinct consumer events even if they receive
the same provider pointer. Expected providers are **static candidates**, not
observed resolution results. Every new occurrence row retains
`consumer_resolution_observed=false`.

The three `PT_INTERP` declarations belong to `bwrap`, `libc.so.6` and `libcap.so.2`.
Only the launcher's declaration participates in the historical kernel exec
continuity. The other two are static executable metadata; this plan does not
pretend they caused two additional kernel interpreter launches or include them in
the nine `DT_NEEDED` return events.

## Why select a loader return event

The inspected glibc 2.41 source walks each consumer's dynamic declarations and
calls `openaux` for an ordinary `DT_NEEDED` request. That helper calls
`_dl_map_object`, whose result is the selected map. The map can be returned from an
already loaded object as well as a new mapping. See the original
[dependency traversal](https://github.com/bminor/glibc/blob/glibc-2.41/elf/dl-deps.c#L186-L265)
and [loaded-object reuse](https://github.com/bminor/glibc/blob/glibc-2.41/elf/dl-load.c#L1890-L1934).

The selected candidate therefore observes the instruction immediately following
that call in the **exact original loader binary**. At that point the new result
must come from the qualified live return register, `RAX`. The store to `args.aux`
has not necessarily occurred, so that field cannot be treated as the fresh result.
The saved argument pointer must be recovered using a binary-qualified recipe; it
must not be assumed to remain in `RDI`. The relevant source structure is
[`openaux`](https://github.com/bminor/glibc/blob/glibc-2.41/elf/dl-deps.c#L46-L69).

These upstream source facts support the proposed mechanism. They do not establish
the source/debug-to-binary relationship, instruction offset, calling convention at
that instruction or private structure layout of the preserved distribution
binary. Those remain explicit unsatisfied gates. The loader's original whole-file
identity is fixed; generic version-based offsets and offsets from the host's
headers are forbidden. glibc itself identifies the later `link_map` fields as
[private implementation details](https://github.com/bminor/glibc/blob/glibc-2.41/include/link.h#L95-L151).

A global loaded-object list does not associate every consumer occurrence with its
provider. An entry-only reconstruction from more specific private loader lists
could be investigated under a different, sufficiently qualified contract, but it
is not the witness selected here. This plan makes no claim that all possible
read-only entry snapshots are intrinsically incapable of supplying such evidence.

## Event identity and independent reconstruction

Each proposed event must preserve enough raw evidence for these joins:

1. Bind the same owned PID/TID, process start time and pidfd identity to fresh cp0,
   each resolution stop and final original entry.
2. Establish the exact hardware stop from wait status, siginfo, raw registers,
   debug-register programming/readback and live original loader instruction bytes.
3. Recover the original consumer from the raw argument structure and qualified
   `link_map` fields, original ELF identity, contemporaneous mapping and backing
   object. A pointer or pathname alone is insufficient.
4. Bind the raw requested-name pointer and bounded NUL-terminated bytes to that
   consumer's original dynamic string occurrence. This profile excludes dynamic
   string tokens and duplicate names within one consumer. The unique
   `(original consumer, needed name)` pair supplies the original dynamic-entry
   ordinal; global event order does not manufacture it.
5. Bind the live returned provider map to the expected original provider, its
   actual mapping and backing object. Check the selected consumer/provider maps
   are non-proxy maps in the base namespace. This does not prove absence of every
   other namespace or loader operation.
6. Require exactly one accepted event for each of the nine static occurrences,
   two stable stopped samples of every required runtime range and register set,
   final entry continuity, complete preservation and owned termination/reaping.

Runtime argument and `link_map` bytes are checked through those qualified pointer
and identity relations. They are not required to equal nonexistent original
runtime-data bytes in an ELF file. Immutable loader instruction/RX samples have
their separate original-byte equality obligation. At fresh cp0 the selected RX
objects are the launcher and interpreter; at final entry all six selected native
objects have their RX obligations.

Neither a saved success flag nor `ldd`, loader listing output, `LD_DEBUG` text,
audit callbacks, static SONAME matching or provider presence can substitute for
the raw event joins. Symbol binding, lazy binding, all IFUNC behavior, complete
process memory and complete native execution remain outside this selected claim.

## Proposed finite execution interval

This is a **new profile**. The existing entry profile and its single cp0-to-entry
continuation are unchanged.

Two independently qualified hardware execution breakpoints would remain armed
from fresh cp0 until final entry: slot 0 at the original loader return checkpoint,
slot 1 at freshly derived `AT_ENTRY`. The latter must equal the original launcher
load bias plus its original ELF entry address. Proposed debug writes are limited
to `DR0`, `DR1`, `DR6` and `DR7`; `DR7=5` enables the two selected local execution
slots, subject to the still-required readback, cause and repeated-resume
qualification. The earlier slot-0-only capability record is insufficient.

| Positive execution operation | Exact count |
| --- | ---: |
| Resume before exec | 1 |
| Resumes from cp0 through the nine returns to entry | 10 |
| Total `PTRACE_CONT` | 11 |
| Accepted dependency-return events | 9 |
| Final original-entry checkpoint | 1 |
| Resumes after entry | 0 |

The return breakpoint must remain active after event nine. A tenth return is
preserved as an unexpected event, followed by owned `SIGKILL` and reap without
another resume. Missing/duplicate events, an unknown consumer/provider, an early
entry, loader exception, unexpected signal or exec event, unreadable evidence,
guard failure or timeout cannot produce a completed observation. No implicit
retry, deadline extension, detach, general-register rewrite, software breakpoint
or code-patching fallback is permitted.

The original invocation remains `argv=["bubblewrap"]`, `cwd="/"`, with only
`LC_ALL=C` and `TZ=UTC`. A fresh qualified task-creation guard remains required.
Loader relocation, IFUNC and initialization code may run before executable entry;
this is not a stop before all userspace execution.

Exactly nine is a positive acceptance cardinality, not an unconditional promise
about runtime behavior. Preload and audit mechanisms require fresh control
evidence, including `/etc/ld.so.preload`; glibc handles both
[preload sources and dynamic audit tags](https://github.com/bminor/glibc/blob/glibc-2.41/elf/rtld.c#L1746-L1929).
`DT_AUDIT`, `DT_DEPAUDIT`, `DT_FILTER` and `DT_AUXILIARY` remain outside the selected
ELF profile. Initializers can cause additional loader activity; unexpected hits
at the selected return checkpoint reject. This mechanism does not observe every
possible `dlopen` call. The vDSO has a
[separate kernel-object setup path](https://github.com/bminor/glibc/blob/glibc-2.41/elf/setup-vdso.h)
and remains bounded kernel mapping metadata, not a tenth selected provider.

## Proposed preservation budgets

The limits are fixed before acquisition and cannot be expanded after start.
Their timing feasibility is not established by this plan check.

| Limit | Value |
| --- | ---: |
| Observation deadline / cleanup window | 15 seconds / 2 seconds |
| Owned tracees | 1 |
| Wait records | 20 |
| Accepted / maximum preserved return events | 9 / 10 |
| Raw capture files / total decoded capture bytes | 512 / 67,108,864 |
| Control / proc file bytes | 1,048,576 / 65,536 |
| stdout / stderr bytes | 4,096 each |
| Files / runtime-memory ranges per event | 32 / 32 |
| Runtime window / samples per range | 4,096 bytes / 2 |
| Packed runtime-memory sample blobs per event | 2, each at most 131,072 bytes |
| Total sampled runtime-memory bytes per event | 262,144 |
| Loader RX samples per event | 2, each 160,721 bytes |
| Pointer indirections / requested-name bytes including NUL | 4 / 256 |
| Mapping rows | 128 |
| Separate source/debug qualification carrier | At most 67,108,864 bytes |
| Qualification control inside the live capture | At most 1,048,576 bytes |

The two packed raw sample blobs need exact range/offset/length manifests. The
future raw checker must reject omissions, overlaps, unused bytes and out-of-bounds
ranges. Packing keeps the memory sample count compatible with the per-event file
cap. The separately hash-bound source/debug payload is outside the live capture's
64 MiB limit; its bounded qualification control and binding belong inside it.
No such payload is added to Git by this plan unit.

## Unsatisfied implementation gates and next unit

The plan fixes eight unsatisfied gates:

1. Exact original-loader source, distribution patch/build and matching debug-data
   binding.
2. Original instruction/control-flow proof and live return/saved-argument recipe.
3. Private layouts, selected namespace/map identity and exact occurrence join.
4. Simultaneous two-slot hardware capability and repeated-resume qualification.
5. Closed new request, capture, event and incomplete-prefix schemas.
6. Bounded collector and independent raw-event checker.
7. Fresh selected environment and original-input admission.
8. Separately owner-authorized fresh acquisition, preservation and independent
   verification of its actual result.

The next implementation unit begins with gates 1–3. If the selected original
binary does not admit a provable post-call checkpoint and bounded data recipe,
this proposal must be revised under a new reviewed contract; no guessed offset or
silent alternative is allowed. A synthetic hardware capability probe can qualify
mechanics, but cannot supply the original binary proof or the nine original
consumer observations.

Even a later complete nine-event observation would prove only the returned
providers for these selected declarations during that attempt. It would not close
[issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879), all B2
obligations, B3 property proof, B4 admission or the B5 actual reference by itself.
No Q3 measurement, selected-bootstrap execution or release authority follows.

## Run the data-only plan checker

From the repository root, using the project's normal Python dependencies:

```bash
python -B tools/check_required_gate_idempotence_loader_resolution_plan_v0.py \
  --plan docs/compute/required_gate_idempotence_loader_resolution_plan_v0/plan_v0.json \
  --plan-sha256 ff33f96d0095f949763125d67da1159112b067b86c2fe3b5f1302f55cb193d7d \
  --output /tmp/pulse-loader-resolution-plan-check.json
```

The output path must not exist. Invalid input cannot create an accepted output,
and an existing file is preserved. The checker reads the selected historical
carrier itself; callers cannot replace the baseline with a different archive path.
No network, signature subprocess or native acquisition is required.

The targeted regression command is:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k entry_resolution_plan
```

The new tests remain in the already registered containment module. Both CI
inventories retain their existing 190 Tools / 41 targeted entries. Historical
plans, capture/checker schemas, source bindings, artifacts and authority boundaries
retain their meanings.
