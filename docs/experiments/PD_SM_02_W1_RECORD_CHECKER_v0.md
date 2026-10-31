# PD-SM-02-W1 — offline input and observation-record checker v0

Classification: **Current implementation; offline record consistency only**.<br>
Implementation preparation base: `795d2cadc2c31e7863e3f8dcae1efa8ff18e7028`.<br>
Experiment: `PD-SM-02-W1`; subject: `pd_sm_02_w1_diagnostic_healthy_v0`.<br>
`authority_effect: none`; `execution_authorized: false`.

## 1. Implemented boundary

This is the first executable checking component after the merged
[W1 contract](PD_SM_02_W1_CONTRACT_v0.md). It supplies:

- Exact admission of the frozen contract, selection, source binding, original
  scratch-pilot archive and six program/data files.
- Independent, non-executing source-operation reconstruction.
- A bounded offline check of declared operation records, process-local sequence,
  request/ACK communication and support at each recorded effect prefix.
- Synthetic conformance and rejection controls registered in both CI manifests.

The tool is [`tools/check_paradox_w1_records_v0.py`](../../tools/check_paradox_w1_records_v0.py).
It does not import or execute the candidate, mapper, checker, launcher or archived
experiment. It reads files, parses JSON/AST and reports to stdout. It does not
write a repository file, open a network connection, launch a process or dispatch
an Actions workflow.

A complete record is not automatically an authenticated observation. A producer
could fabricate an internally consistent record. This version checks the record
relation, not the truth of acquisition, observer identity, platform identity or
containment. Both supported origins (`synthetic_fixture` and
`unverified_observation_record`) retain that boundary. Digests supplied in the
record's `identities` object are syntax-checked identifiers, not verification of
the referenced harness/observer/runtime/configuration bytes.

```text
input admission: implemented
ordered record consistency: implemented
native harness: NOT_IMPLEMENTED_BY_THIS_CHANGE
native acquisition authentication: NOT_IMPLEMENTED_BY_THIS_CHANGE
external containment verification: NOT_IMPLEMENTED_BY_THIS_CHANGE
new W1 candidate execution: NOT_RUN
native_witness_observed: null
containment_observed: null
execution_authorized: false
authority_effect: none
```

The native harness, containment controller, ordered observer, admission probes
and separately bound owner authorization remain prerequisites from the W1
contract. This checker is not a substitute for any of them.

## 2. Frozen input admission

The admission path pins these exact planning bytes from #2967:

| Input | SHA-256 |
|---|---|
| Contract | `dd744fa97835627d68bb6b66e38885d8f9115e959f081b4b8645c257c75c91a0` |
| Selection | `a04ff29eba4fda99e575f1984bfa9e91622fdd02d4ddfb2e01966e25967d5620` |
| Source binding | `b43c3995b0661d828b5e433c1041c28ee5a9bf4d99ebe095b1d1f0bd892010c3` |
| Original scratch-pilot archive | `c63f2ee6e2dfae21ec3736fbd99f8169b8c5b7a06a28c8a8a3e7dad2ac2fcd18` |

It verifies all 471 manifest entries, the six program/data files and 38 selected
archive members. Candidate bytes, canonical/raw context identities, independently
parsed operations, source-region slices, selected historical model projections
and native refusal records must match the preserved originals.

The six current program/data files must still match the archived snapshot.
The later companion README is intentionally excluded from that six-file check.
No historical file, archive, fixture state or W1 planning record is rewritten.
A revision of the frozen experiment requires an explicit new contract/checker
binding; it is not silently accepted through a moving `main` alias.

From the repository root, input admission only:

```sh
python -I -S -B tools/check_paradox_w1_records_v0.py
```

Expected receipt class: `PREPARATION_VALID`. Its `execution_authorized` remains
false and its `new_candidate_executions` remains zero.

## 3. Offline record format

The format is `pd_sm_02_w1_observation_record_v0`. The checker enforces closed
key sets, duplicate-key rejection, finite JSON, bounded inputs, exact scalar
integer types (booleans are not integers), fixed case order and one attempt.

Top-level fields:

| Field | Meaning |
|---|---|
| `schema_version`, `subject` | Exact W1 record format and diagnostic subject. |
| `evidence_origin` | `synthetic_fixture` or `unverified_observation_record`; neither is authenticated acquisition. |
| `run_id`, `attempt` | Nonempty bounded identifier; attempt 1. |
| `selection_sha256`, `source_binding_sha256` | Exact frozen planning-file identities. |
| `runtime` | Declared CPython 3.13.5 / Linux x86_64 profile, not independently observed runtime. |
| `identities` | Harness, observer, containment-config, runtime-manifest and request digests; authenticity not established. |
| `cases` | Exactly P00, N01, N07, N08, N02, in that order. |

Each case carries its exact candidate/context digests, `healthy` scenario,
process-role/PID mapping, event records, request/ACK links and terminal sink/audit
bytes. A case is `COMPLETE`, `INCOMPLETE` or `NOT_RUN`. `NOT_RUN` permits no
processes, events, links or observed file bytes. An incomplete or mismatching
case stops the record sequence: subsequent cases must remain `NOT_RUN`.

Each event contains `event_id`, `run_id`, `case_id`, `attempt`, `process`,
`sequence`, `operation_index`, `kind` and `data`. Event IDs are unique within a
case. Every recorded process sequence starts at one without gaps or duplicates.
The worker's operation begin/end pairs must match the selected source operations
in order, with exact primitive arguments. Exceptions close the executed prefix;
they do not imply execution of the remaining source operations.

Required event kinds, where applicable:

```text
candidate_start
op_begin
request_send
request_receive
intent_persisted
ack_send
ack_receive
sink_write_completed
op_end
candidate_terminal
supervisor_terminal
```

For `intent_persisted`, the record supplies exact intent bytes, write return and
fsync return. For `sink_write_completed`, it supplies the exact request, written
bytes and write return. The checker matches terminal bytes against these events;
summary counts alone are insufficient. Supervisor termination must identify the
recorded worker and its terminal event, normal-exit state and exit code.

## 4. Order and effect-prefix evaluation

The checker builds a directed order from process-local event sequences and
explicit byte-matched request/ACK send/receive links. Message endpoints are
one-to-one, have the required process direction and source operation identity,
and carry the same exact bytes and payload digest. Cycles, endpoint reuse,
missing communication and unmodeled events cannot yield consistency success.

The order of objects in the outer event list is not itself cross-process order.
Timestamps are not accepted as substitutes for communication edges.

For each recorded append, evaluate the support at that effect prefix: source
justification, established request binding, request-specific reservation, prior
matching intent and ACK, audit support and single-use occurrence. A later intent
cannot support an earlier effect. Two writes cannot be replaced by one 44-byte
summary. An incomplete prefix does not prove absence of monitoring.

The independently derived record relation is then compared with the frozen
prediction. Fixture labels and expected outcomes do not manufacture observations.
The primary witnesses remain N01, N07 and N08. N02 remains a separate refusal
control; changing the rejecting primitive into an actual writer is out of scope.

| Synthetic case record | Derived record-level distinction |
|---|---|
| P00 | One effect with matching prior support. |
| N01 | One effect without recorded prior intent/ACK/audit support. |
| N07 | Two separate effects after one reservation; the second violates single use. |
| N08 | Effect before monitor support, despite terminal sink/audit bytes equal to P00. |
| N02 | Native-primitive refusal represented in the record, with no effect. |

These rows describe synthetic test inputs and record-checker outputs, not a new
native experiment. Partial writes retain their byte count and `PARTIAL_EFFECT`
classification; they are not normalized into a successful complete effect.

## 5. Result and authority boundary

| Exit | Report status | Meaning |
|---|---|---|
| 0 | `PREPARATION_VALID` | Frozen input relation verified; no record evaluated. |
| 0 | `RECORDS_CONSISTENT` | Five supplied case records meet the selected record contract and predictions. |
| 1 | `INVALID_RECORD_OR_INPUT` | Input identity, shape, source mapping or record binding rejected. |
| 2 | `RECORDS_INCOMPLETE` | Required record closure is missing; includes all-NOT_RUN inputs. |
| 3 | `RECORDS_MISMATCH` | A completed recorded outcome differs from the frozen prediction. |

Exit zero is not safety PASS, authenticated native execution, containment
acceptance, launch permission or release authority. A matching negative witness
record still describes a violation of the inner monitored-effect relation.
The report also records `verifier_source_sha256` for the checker source bytes;
this is not a runtime/platform attestation. Every observation-record report retains:

```text
acquisition_authenticity: NOT_VERIFIED
native_witness_observed: null
model_native_correspondence: UNRESOLVED
containment_observed: null
execution_authorized: false
new_candidate_executions: 0
authority_effect: none
```

## 6. Regressions and reproduction

The explicitly synthetic fixture is
[`tests/fixtures/paradox_w1_records_v0/synthetic_observations.json`](../../tests/fixtures/paradox_w1_records_v0/synthetic_observations.json).
It is not a new observed-run archive and must not be copied into W1 native evidence
as if acquired. The fixed fixture includes 117 synthetic event records.

```sh
python -I -S -B tools/check_paradox_w1_records_v0.py \
  --observations tests/fixtures/paradox_w1_records_v0/synthetic_observations.json

python -B -m pytest -q tests/test_paradox_w1_records_v0.py
```

The regression is registered once in both `ci/tools-tests.list` and
`ci/pytest-tests.list`. This change advances their inventories from 172/28 to
173/29. Nine existing literal-count consumers, their cross-consumer checks and
the Pages/Q3-postflight count checks are updated together. Their workflow,
acquisition, runtime and negative-control semantics are otherwise unchanged.
Historical documentation counts are not rewritten as current inventory claims.

No existing native launcher, gate policy, normative status, evidence archive or
W1 planning file is modified. Native acquisition and its authorization remain a
separate next implementation/execution boundary.
