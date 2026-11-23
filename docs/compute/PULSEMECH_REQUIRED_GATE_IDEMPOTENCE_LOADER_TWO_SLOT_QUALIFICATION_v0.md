# B2 loader two-slot qualification implementation v0

## Status and place in the plan

This unit implements a separate producer and an independent raw-record checker
for the fixed, synthetic two-slot hardware probe. It advances the implementation
portion of gate 4 in the
[loader-resolution plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_PLAN_v0.md#unsatisfied-implementation-gates-and-next-unit).
Its implementation regressions do not supply an actual qualification record or
an original loader capture.

**Selected native result:** the later hosted route completed one fixed probe in
[owner-dispatched run `45253188286/1`](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286)
at source `624713608bcf5467c6d4be44cd026f906c45f274`. The
[completed hosted qualification and preservation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_HOSTED_v0.md#completed-hosted-qualification-452531882861)
retain the actual request, native record, four matching hosted reports, cleanup
and hosted attestation verification. This selected result does not admit a
future host, observe the original loader or complete B2.

The development base is `90ffaf4ad09e02f41fcfb47ecc8c33e640f8770f`, after
[PR #3047](https://github.com/HKati/pulse-release-gates-0.1/pull/3047).
Its selected rebuild signatures and original-byte joins retain their meaning.
Historical key authority, accepted build policy and signed source-input coverage
remain open as described in the
[rebuild-attestation binding](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_REBUILD_ATTESTATION_BINDING_v0.md).

| Surface | Result supplied here |
| --- | --- |
| Producer | A new bounded controller and a narrow Linux x86-64 backend for one fixed synthetic probe. |
| Native record | A separately identified closed format preserving raw bytes, operations, context, implementation identity and incomplete outcomes. |
| Independent checker | Fresh reconstruction of the selected raw mechanics, with an externally selected record digest and context. |
| Implementation regressions | Authored raw records and a scripted backend; no native capability probe is executed by the tests. |
| Actual selected environment | Completed bounded hosted result `45253188286/1`; later acquisitions still require their own selection, authorization and fresh admission. |
| Original loader | No new invocation, dependency-return event or provider-resolution evidence. |
| B2 and issue #2879 | Incomplete and open under the existing scope. |

The old single-slot entry qualifier and the authored two-slot fixture helper
retain their exact bytes and APIs. A fixture is never converted into native
evidence by changing its label and calling the old fixture checker.

## Implementation inventory

| Path | Responsibility |
| --- | --- |
| [Producer](../../tools/qualify_required_gate_idempotence_loader_two_slot_v0.py) | Fixed native operation surface, controller, bounded preservation and exclusive publication. |
| [Independent checker](../../tools/check_required_gate_idempotence_loader_two_slot_qualification_v0.py) | Closed input validation, raw mechanics reconstruction and deterministic report. |
| [Record schema](../../schemas/required_gate_idempotence_loader_two_slot_qualification_v0.schema.json) | Versioned structural contract; schema validity alone does not establish mechanics or native execution. |
| [Existing pure probe helper](../../tools/required_gate_idempotence_loader_two_slot_v0.py) | Unchanged fixed probe construction; its fixture verification API is not a native verification path. |
| [Existing containment test module](../../tests/test_required_gate_idempotence_containment_v0.py) | Append-only regressions in the already registered module. |

The implementation inventory binds the first four paths. It is checked before
and after reconstruction. No record contains its own digest; the caller selects
the exact record bytes independently. The source inventory does not authenticate
an otherwise untrusted producer, checker or kernel.

## Fixed probe and finite execution interval

The selected probe is a 138-byte static ELF with no interpreter. Its complete
instruction sequence is:

```text
MOV ECX, 9
return_checkpoint: NOP
LOOP return_checkpoint
terminal_checkpoint: UD2
```

The selected addresses are fixed by these exact authored bytes:

| Property | Value |
| --- | --- |
| ELF load base | `0x400000` |
| Initial entry | `0x400080` |
| Slot 0 / repeated checkpoint | `0x400085` |
| Slot 1 / terminal checkpoint | `0x400088` |
| Armed DR7 | `5` |
| Permitted debug-register writes | DR0, DR1, DR6 and DR7 only |
| Repeated checkpoint stops | Nine, with ECX progressing from 9 to 1 |
| Terminal checkpoint stops | One, with ECX equal to 0 |
| Total successful PTRACE_CONT operations | Eleven |
| Continuations after terminal checkpoint | Zero |

The nine repeated stops exercise breakpoint and resume mechanics. They are not
nine original `DT_NEEDED` events. The terminal probe checkpoint is not the
original launcher's executable entry. The terminal `UD2` must never execute.

The first continuation advances the stopped child to exec. The second advances
from the kernel exec checkpoint to the first repeated stop. Nine further
continuations advance through the remaining repeated stops to the terminal
checkpoint. Both slots remain armed after the ninth repeated stop. A tenth
repeated stop is retained as an unexpected event, followed by cleanup without
another continuation.

The producer clears DR6 and records its readback before each continuation.
At each hardware stop, two raw register samples must agree and satisfy the
existing [startup/resume rule](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_STARTUP_CONTRACT_v0.md#selected-rftf-rule-and-unchanged-execution-boundary):

```text
(RFLAGS & 0x10000) != 0   # RF set
(RFLAGS & 0x00100) == 0   # TF clear
```

At the kernel exec checkpoint, TF must be clear; RF is not fixed. No general
register or instruction-pointer rewrite, single-step operation, software
breakpoint, target-memory write, detach or post-terminal continuation is part
of this profile.

## Raw evidence and process identity

The producer preserves the bounded original process-status files, raw registers,
debug-register readbacks, signal information and fixed probe bytes. Raw values
are stored as hexadecimal bytes with their exact size and SHA-256 descriptors.
The checker rejects extra, missing or substituted completed record inputs;
saved success fields cannot replace the required raw relations. A completed
record has exactly 137 raw entries and 61 operations in its journal.

The child is bound through its owned process relationship, start time, pidfd and
pinned proc directory. The expected executable bytes and live probe instructions
must agree with the fixed probe. The two selected debug slots and their exclusive
stop causes must agree with the corresponding instruction addresses and loop
state.

Native preflight requires a single observer thread, open standard descriptors
and the default Python `SIGCHLD` disposition. An ignored signal or an installed
Python handler could reap the child outside the controller and invalidate the
owned, unreaped PID assumption used by exceptional cleanup. The producer rejects
such a caller configuration instead of resetting its signal handling.

Complete raw `/proc/<pid>/status` files are retained, including additional
informational fields. Required PID, parent, tracer, thread and namespace
identities are parsed from those bytes. The checker does not require unrelated
accounting fields or the complete `/proc/<pid>/stat` and `/proc/<pid>/status`
files to remain byte-identical across samples. Stable registers, debug registers
and selected code bytes have separate equality obligations.

Linux documents that an open proc descriptor for a dead process does not act on
a new process that later reuses the same PID; the descriptor alone does not
prevent PID reuse. The pidfd and raw identity joins therefore remain necessary.
See the kernel's [proc filesystem documentation](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
and the [ptrace interface](https://man7.org/linux/man-pages/man2/ptrace.2.html).

## Preservation and failure bounds

| Bound | Maximum |
| --- | ---: |
| Observation interval | 15 seconds |
| Cleanup interval | 2 seconds |
| Serialized qualification record | 1,048,576 bytes |
| Decoded raw bytes | 262,144 bytes |
| Raw entries | 160 |
| Journal operations | 128 |
| Individual proc input | 65,536 bytes |

The serialized-record limit is checked before JSON parsing. Raw extents and
their aggregate are checked before decoding or hashing the raw bodies. The
smaller decoded-byte limit leaves room for hexadecimal encoding and the control
journal within the plan's one-MiB qualification-control budget.

An attempt can fail before exec, while programming a breakpoint, between the
two stable samples, at an unexpected stop, at a deadline or during cleanup.
Such attempts retain their bounded available evidence and failure phase. An
incomplete record does not satisfy the completed mechanics contract, even if
its captured prefix contains several correct stops.

The output destination is reserved exclusively before a native attempt begins.
An existing file is never overwritten and cannot trigger a new probe attempt.
A write, synchronization or destination-identity failure invalidates the newly
owned output descriptor and returns failure. A concurrently substituted path is
not unlinked or truncated. An empty reserved output can remain after a failed
publication; it is not a qualification record. No automatic retry is introduced.

## Checker API and local regressions

The independent checker accepts:

```python
verify_record(
    *,
    record_bytes: bytes,
    expected_record_sha256: str,
    expected_context: dict,
) -> dict
```

The caller must select the context independently of the incoming record. The
checker does not read a new host context and describe it as the old acquisition
environment. The record's before/after context includes kernel identity, boot
identity, the observer executable descriptor and the selected namespace links.

The checker CLI accepts `--record`, `--record-sha256`, `--expected-context`,
`--expected-context-sha256` and `--output`. Both input digests identify exact
externally selected bytes. The output is canonical JSON and must not exist.
The checker never forks the probe or invokes the native backend.

The reconstructed status distinguishes three cases:

| Status | Meaning |
| --- | --- |
| `accepted_native_qualification_record` | A completed record declaring the native producer origin satisfies the raw mechanics and selected binding checks. |
| `accepted_scripted_qualification_record` | A completed scripted backend record satisfies those same mechanics checks as implementation evidence. |
| `preserved_incomplete` | Bounded incomplete diagnostics are preserved; no complete mechanics or valid-prefix claim is made. |

Only complete records can set `complete_mechanics_verified=true`. The two
completed origins remain distinct in `native_record_reconstructed` and
`scripted_record_reconstructed`. Neither status sets
`current_host_admission_satisfied` or `physical_execution_authenticated`.

The producer API is `qualify(backend=None)`. Its internally constructed backend
selects `native_owned_probe`; any explicitly supplied backend selects
`scripted_test_backend`. Supplying a test backend cannot request native origin.
The actual native producer is an execution entry point; it is not part of the
data-only verification command or the regression command below.

Run the new implementation regressions from the repository root:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_two_slot_qualification
```

The tests use independent authored raw values, a scripted operation backend and
the data-only checker CLI. They check failed and partial operations, raw input
substitutions, identities, RF/TF, exact stop and continuation accounting,
source/context changes, publication behavior and unchanged prior interfaces.
They do not run the synthetic ELF or the original launcher. Local test success
does not establish that the current or future runner supports the selected
hardware behavior.

## Evidence and admission boundary

A reconstructed record establishes the relations supported by its raw bytes.
It does not independently authenticate that those bytes came from physical
execution. A producer-declared native origin is not an execution attestation.
Scripted backend records remain explicitly identified as implementation tests.

Actual qualification requires the selected environment, exact executed
source, preserved acquisition, independent reconstruction and freshness/admission
joins. A record from another kernel, boot, namespace or observer identity cannot
silently qualify a new acquisition. The separate hosted result linked above
records those relationships for its own attempt; this implementation unit does
not grant authorization or admission to another attempt.

The original source/build evidence route remains a separate obligation. An
accepted original buildd route or an accepted rebuild route may satisfy the
selected policy; this package does not require both routes or invent missing
historical authority. Original startup/readouts, the full loader collector and
capture checker, fresh original-input admission and separately authorized
original acquisition remain subsequent work.

The work retains:

```text
source_build_gate_satisfied = false
original_acquisition_ready = false
consumer_resolution_observed = false
physical_execution_authenticated = false
current_host_admission_satisfied = false
b2_complete = false
metric_pass = null
authority_effect = none
```

Historical Q2 remains FAIL, including 49 eligible groups against 50 required
and one UNKNOWN. The twelve unsupported gate classifications are unchanged.
The main README, workflows, historical evidence and the 190 Tools / 41 targeted
registrations retain their existing bytes.

[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) remains
open. Its original whole-runtime occurrence and terminal-accounting conditions
are not narrowed. Step 5D relational closure, Step 6 resource measurement and
Step 7 policy promotion remain separate.
