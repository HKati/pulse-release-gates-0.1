# B2 loader two-slot qualification request and attempt v0

## Status and purpose

This unit adds the pre-execution request and preserved-attempt contract around
the [two-slot qualification implementation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_QUALIFICATION_v0.md).
The request selects the context and implementation bytes before the fixed
synthetic probe can be invoked. An independent checker binds the later attempt
to that exact request and reuses the existing raw-record checker.

The development base is `1149b997da2d73205b63f4be05efc1ac7358c6af`, after
[PR #3048](https://github.com/HKati/pulse-release-gates-0.1/pull/3048), including
the corrected `child.stat.` / `child.status.` native read dispatch.

This is a callable implementation unit in the gate 4 qualification path of the
[loader-resolution plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_PLAN_v0.md#unsatisfied-implementation-gates-and-next-unit).
The local regressions use authored records and scripted execution. They supply
no actual native qualification record or original-loader observation.

**Selected hosted result:**
[owner-dispatched run `45253188286/1`](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286)
at source `624713608bcf5467c6d4be44cd026f906c45f274` completed one actual fixed
probe through this adapter. Its
[preserved request, attempt and hosted verification](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_HOSTED_v0.md#completed-hosted-qualification-452531882861)
retain native-origin evidence separately from the authored regression cases.
Original-loader acquisition, future-context admission and B2 completion remain
open.

| Surface | Responsibility |
| --- | --- |
| Request preparation | Read the selected environment independently, before a probe, and bind the fixed profile and exact implementation inventory. |
| Attempt adapter | Require the exact acknowledgement and request digest, recheck the selection, invoke at most one fixed probe and preserve its outcome. |
| Attempt checker | Independently validate the request, receipt and raw-record bindings; reconstruct mechanics through the unchanged raw checker. |
| Hosted integration | The separate hosted route completed selected attempt `45253188286/1` with reviewed source, workflow, artifact and independent replay bindings. |
| Original loader | Still requires its separate source/build acceptance, collector, input admission and authorized observation. |

## File inventory and unchanged components

| Path | Role |
| --- | --- |
| [Request and attempt adapter](../../tools/prepare_required_gate_idempotence_loader_two_slot_v0.py) | Independent context selection, request publication and one guarded attempt. |
| [Independent attempt checker](../../tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py) | Closed request/attempt validation, external digest joins and deterministic reconstruction. |
| [Request schema](../../schemas/required_gate_idempotence_loader_two_slot_request_v0.schema.json) | Versioned request structure and finite selection. |
| [Attempt schema](../../schemas/required_gate_idempotence_loader_two_slot_attempt_v0.schema.json) | Versioned complete/incomplete receipt structure. |
| [Existing containment regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Append-only tests in the already registered test module. |

The new request inventory binds these four implementation/contract paths and
the four unchanged paths already bound by the raw qualification checker:

```text
schemas/required_gate_idempotence_loader_two_slot_qualification_v0.schema.json
tools/check_required_gate_idempotence_loader_two_slot_qualification_v0.py
tools/qualify_required_gate_idempotence_loader_two_slot_v0.py
tools/required_gate_idempotence_loader_two_slot_v0.py
```

The original four-file inventory keeps its existing meaning. The new inventory
adds the request/attempt layer without changing the earlier record, producer,
checker, fixture API or historical evidence.

## Selection before execution

The request contains the selected kernel identity, boot identity, observer
executable descriptor and namespace identities, together with the fixed probe,
finite limits, exact source inventory and request identifier. Its caller selects
the digest of the complete serialized request independently.

The preparation command reads its current context without invoking the probe.
The attempt entry point reads context and source identities again immediately
before invoking the producer. A changed context, changed implementation,
incorrect digest or incorrect acknowledgement prevents invocation.

Expected context must come from the pre-execution request. The independent
checker does not copy it from the incoming qualification record and does not
substitute the verification machine's current context.

The request identifier distinguishes selections. It is not a global one-use
ledger or proof of owner identity. An acknowledgement is an explicit invocation
safeguard; a string in a request cannot authenticate who authorized execution.
The hosted procedure must supply its own source/run/owner bindings. Source-byte
agreement here does not authenticate a Git commit or physical execution.

## One bounded attempt and preservation

The adapter reserves a new attempt directory and its output identities before
invoking the producer. Existing output is not a reason to repeat execution or
replace another attempt. It calls the unchanged producer directly so the
producer retains responsibility for its owned child and bounded cleanup.

The fixed native operation remains the 138-byte synthetic probe: nine repeated
checkpoint stops, one terminal stop, eleven continuations and zero continuations
after the terminal checkpoint. No original launcher, model, selected bootstrap
or original dependency-resolution event is part of this operation.

The preservation roster is closed:

| Member | Meaning |
| --- | --- |
| `request.json` | Exact copy of the independently selected request. |
| `qualification.json` | Available producer record bytes, including an empty or invalid publication retained as incomplete diagnostics. |
| `attempt.json` | Receipt binding the request, available qualification bytes, invocation count, context/source snapshots and outcome. |

The qualification member may be absent when no bytes could be published. Its
presence and exact extent must agree with the receipt. The receipt does not
contain its own digest: the verifier requires an externally selected receipt
digest as well as the independently selected request digest.

The adapter normally reserves all three members, so a pre-invocation failure
retains an empty qualification member. The checker also supports the explicit
absent-member diagnostic shape. Requests and receipts are each bounded to
65,536 serialized bytes; qualification records retain their existing 1,048,576
byte maximum. The raw producer's observation, cleanup, decoded-byte, entry-count
and operation-count bounds are unchanged.

Complete reconstruction requires the selected context and source inventory to
agree before and after execution, one recorded invocation, an accepted complete
raw record and all request/record/receipt joins. Explicitly supplied test
backends remain scripted in the raw record and attempt envelope.

An admission failure, interrupted invocation, incomplete raw record, missing or
invalid record, changed context/source, or publication failure cannot produce a
completed attempt. Bounded available diagnostics remain distinguishable from a
valid completed observation. No accepted-prefix or successful-hardware claim is
derived from an incomplete attempt.

The adapter introduces no automatic retry. Output publication and replacement
checks protect owned output identities; they do not authorize modifying a
replacement path created by another actor. Bounded rereads also compare the
actual persisted bytes with the intended request, qualification and receipt
bytes, so a same-inode rewrite cannot pass merely by preserving the file's
identity. Abrupt loss of the process or host
can still leave an unfinished prefix without a valid receipt. A later hosting
layer must preserve such available files and retain the failure.

When implementation bytes change after invocation, the adapter can preserve an
incomplete receipt against the exact schema cached and bound before execution.
This diagnostic-only validation cannot accept a completed receipt or produce a
mechanics verification report. Later independent reconstruction still requires
the original selected implementation. A source change must not erase the very
diagnostics that record it.

## Independent reconstruction

The checker consumes exact selected bytes. It validates closed structures,
source/context bindings, the finite member roster and the recorded outcome.
For a completed raw record it calls the existing
`check_required_gate_idempotence_loader_two_slot_qualification_v0.verify_record`
with the request's expected context. It does not implement a second hardware
mechanics engine or import the native producer.

The byte-oriented APIs are:

```python
verify_request(*, request_bytes, expected_request_sha256) -> dict

verify_attempt(
    *,
    request_bytes,
    expected_request_sha256,
    attempt_bytes,
    expected_attempt_sha256,
    qualification_bytes,
) -> dict
```

The command-line attempt checker additionally validates the exact preserved
directory roster. Reports are deterministic, and output publication is
exclusive. Repeating data-only reconstruction does not repeat the probe.

| Report status | Meaning |
| --- | --- |
| `accepted_native_qualification_attempt` | A completed native-origin record and its request/receipt joins reconstruct under the selected implementation. |
| `accepted_scripted_qualification_attempt` | The corresponding complete scripted record reconstructs as implementation evidence. |
| `preserved_incomplete` | Bounded diagnostics are bound and preserved without a completed-mechanics or valid-prefix claim. |

Neither completed status authenticates physical execution or admits another
acquisition. An incomplete receipt can retain a complete inner raw record, for
example when the post-execution source/context join fails; the outer attempt
still cannot report completed mechanics.

## Command boundary

The following commands describe the separate preparation, execution and
reconstruction surfaces. Actual execution must use the separately selected
environment and reviewed procedure. `REQUEST_SHA256` and `ATTEMPT_SHA256` mean
the independently selected 64-character lowercase hexadecimal digests of the
exact respective files; they are not future values supplied by this document.

Prepare a request without executing a probe:

```bash
python3 -B tools/prepare_required_gate_idempotence_loader_two_slot_v0.py \
  prepare --output /tmp/pulse-two-slot-request.json
```

The separate execution entry point is:

```bash
python3 -B tools/prepare_required_gate_idempotence_loader_two_slot_v0.py \
  attempt \
  --request /tmp/pulse-two-slot-request.json \
  --request-sha256 REQUEST_SHA256 \
  --acknowledgement QUALIFY_LOADER_TWO_SLOT_ONLY \
  --output-directory /tmp/pulse-two-slot-attempt
```

The request file and attempt directory must be new for their respective
creation operations. Successful preparation exits 0. An attempt exits 0 for a
completed receipt, 1 for a preserved incomplete receipt, and 2 for rejection or
a publication error. The execution command has no backend-selection argument.

Reconstruct the preserved attempt without running the probe:

```bash
python3 -B tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py \
  --request /tmp/pulse-two-slot-request.json \
  --request-sha256 REQUEST_SHA256 \
  --attempt-directory /tmp/pulse-two-slot-attempt \
  --attempt-sha256 ATTEMPT_SHA256 \
  --output /tmp/pulse-two-slot-attempt-check.json
```

The checker compares the preserved request copy with the externally supplied
request. Its exit codes are 0 for completed reconstruction, 1 for a preserved
incomplete attempt and 2 for rejection. The report output must not exist.

## Implementation validation

The new regressions are selected with:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_two_slot_attempt
```

They use authored qualification records, scripted producer backends and stubbed
context reads. They exercise the actual new adapter/checker and the unchanged
raw checker. Native probe execution, Docker execution and workflow dispatch are
outside the regression path.

The implementation increment extended the existing test file without rewriting
earlier cases. It left the main README, existing workflows, historical evidence
and the 190 Tools / 41 targeted test registrations unchanged. The later
preservation update records the selected hosted result in documentation.

## Remaining execution and issue boundary

This unit makes one precise qualification operation callable and reviewable.
It does not integrate that operation into GitHub Actions. The existing
entry-stop workflow remains a different operation: it qualifies its original
entry-stop prerequisites and then invokes the original launcher. It must not be
used as a shortcut for a qualification-only attempt.

The separate hosted integration binds the reviewed source, selected runtime
environment, owner request, workflow/run/attempt identity, actual invocation,
preserved artifact, independent reconstruction and outer cleanup. These
relationships were checked for `45253188286/1`. Any later dispatch remains a
separate owner decision at the exact reviewed revision.

The completed qualification applies to its recorded environment. It
cannot admit a future original-loader acquisition in another boot, namespace,
container or process context. Fresh original-input admission, the original
collector/capture path and the accepted source/build evidence route retain
their separate obligations.

```text
original_native_acquisition_performed = false
original_acquisition_ready = false
source_build_gate_satisfied = false
consumer_resolution_observed = false
physical_execution_authenticated = false
current_host_admission_satisfied = false
b2_complete = false
metric_pass = null
authority_effect = none
```

[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) stays
open with its full predeclared subject, occurrence, terminal-accounting,
preservation and reconstruction boundary. Historical Q2 remains FAIL with 49
eligible groups against 50 required and one UNKNOWN; the twelve unsupported
gate classifications are unchanged. Step 5D relation/comparison closure,
Step 6 resource measurement and Step 7 policy promotion remain separate.
