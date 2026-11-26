# PD-SM-02-W1 — bounded native-witness experiment contract v0

Classification: **Preregistered experiment contract and source-bound selection; not executed**.<br>
Preparation date: `2026-10-31`.<br>
Experiment identifier: `PD-SM-02-W1`.<br>
Inspected repository: `HKati/pulse-release-gates-0.1` at `d04264496365ee681167b194b5a9aebb4991374a`.<br>
`authority_effect: none`; `production_gate_eligible: false`.

## 1. Verification target and present state

The [preserved PD-SM-02 scratch pilot](../PULSEMECH_PARADOX_PREEXECUTION_SCRATCH_RESULT_v0.md)
records four eligible native executions and twenty pre-effect refusals. A refused
candidate was not executed: refusal does not establish native realizability of
its model counterexample.

W1 asks a different, bounded question: for three already selected counterexamples
in the exact `healthy` scenario, can a **separate diagnostic experiment** record
the predicted violating effect and its support state at the effect boundary?

This delivery freezes the candidates, scenario, witness projections, predictions,
required observations and acceptance distinctions **before** that experiment.
It includes no executable launcher, workflow or native observation. The existing
admission path is neither weakened nor used to authorize negative candidates.

```text
selection_status: PREREGISTERED
native_harness_status: NOT_IMPLEMENTED
containment_status: REQUIRED_NOT_ESTABLISHED
ordered_observer_status: REQUIRED_NOT_IMPLEMENTED
owner_execution_authorization: NOT_GRANTED_BY_THIS_CONTRACT
execution_status: NOT_RUN
new_candidate_executions: 0
observed_results: null
readiness: BLOCKED_PENDING_HARNESS_CONTAINMENT_OBSERVER_AND_AUTHORIZATION
authority_effect: none
```

[Exact case selection](PD_SM_02_W1_SELECTION_v0.json) and
[source bindings](PD_SM_02_W1_SOURCE_BINDING_v0.json) are machine-readable planning
records. Their validity is not evidence that a future experiment has run.

## 2. Exact inputs and selection rule

Use the unchanged original `PD_SM_02_SCRATCH_PILOT_20261027.zip` preserved under
`docs/evidence/PD_SM_02_SCRATCH_PILOT_20261027/`. Its identity is:

```text
bytes: 329950
sha256: c63f2ee6e2dfae21ec3736fbd99f8169b8c5b7a06a28c8a8a3e7dad2ac2fcd18
members: 473
manifest_entries: 471
manifest_sha256: 26083c5fffbfdbc4cef002db59663d6a0a262d5f36a737f8dcd4a5f20484d178
```

The program/data files at the inspected repository commit have the same Git blob
identities as the original execution snapshot. The later companion README is a
separate documentation object; it is not substituted into the historical ZIP.

The selection fixes **five candidates, one scenario and one attempt per case**.
The scenario is the original `healthy` row: normal single-request monitoring,
exact submitted request, same ACK/audit identity and one attempt. The remaining
scenario rows and nineteen other fixture cases are outside W1. The selection
makes no coverage claim over the entire finite profile or arbitrary programs.

Every selected candidate is the exact UTF-8 source from the original fixture
and archive. The JSON includes its original source text, raw source digest,
context, canonical-context digest, original raw-context digest, operation
positions and exact selected model witness. Raw-file and canonical-JSON digests
are deliberately named separately. The selected witness is a projection from a
preserved model assessment, **not a new native observation**.

Selection is based on distinct relationships rather than an intended success
rate: absent monitor support, duplicate effect, misleading terminal state,
positive useful operation, and a model/native route boundary.

## 3. Fixed case matrix

All predictions below are **static source-inspection expectations**, not results.
Each case starts with a fresh empty sink and audit surface in a separate bounded
experiment instance. The payload is exactly the UTF-8 bytes of
`BOUND_MONITORED_EFFECT` (22 bytes, no newline).

| Order | Case | Role | Diagnostic prediction | Required distinguishing observation |
|---|---|---|---|---|
| 1 | P00 | Positive control | One 22-byte effect; one matching intent; normal completion | Persisted matching intent and matching ACK precede the effect |
| 2 | N01 | Primary witness | One 22-byte effect; no intent; normal completion | Successful effect without a monitor request, intent, ACK or audit support |
| 3 | N07 | Primary witness | Two effects, 44 bytes; one intent; normal completion | Two separate successful writes for one request after one reservation |
| 4 | N08 | Primary witness | One 22-byte effect; one later intent; normal completion | Effect completes before the monitor request; support appears only later |
| 5 | N02 | Primitive-refusal control | Zero effects; `direct_effect_route_not_admitted` | Current native primitive refuses the abstract direct route before any write |

The original normal launcher refused N01, N07, N08 and N02 with
`checker_replay_not_eligible`. W1 does not rewrite those results or pretend that
those original attempts reached native effect code.

### N02 is a boundary control, not a promised native violation

The preserved model treats `direct_sink_write` as a potential effect route. The
pinned native primitive always raises `direct_effect_route_not_admitted`.
A source-level label such as `helper` does not establish an actual delegated
process or an implemented direct write. This is a conservative abstraction /
native-profile distinction, not by itself a defect in normal fail-closed admission.

W1 must preserve that native refusal. Replacing this primitive with a working
write would be a **different ablation experiment**, requiring a separate source,
profile and authorization. It must not count as realization of N02 under the
pinned native primitive. N02 does not enter the denominator of the three primary
witness realizability claims.

### N08 distinguishes a path from its final state

P00 and N08 are predicted to end with identical sink bytes and the same matching
intent content under the selected request and monitor semantics. Only the ordering
of the actual effect relative to monitor support distinguishes them.
A final sink/audit comparison, a success exit code, a simulated trace or a
candidate-supplied status is insufficient to establish the N08 witness.

## 4. Two execution boundaries, kept separate

**Normal admission boundary:** the existing mapper, checker, profile and launcher
remain unchanged. Negative assessments must not become launch-eligible. Do not
add a force flag, an exception list keyed by case ID, a changed eligible verdict,
a fabricated assessment or a private-function shortcut to the existing launcher.
Historical normal-lane records may be reused by exact digest; they are not new
runs and do not authorize W1.

**Diagnostic experiment boundary:** a later, separately reviewed harness may run
only the five exact selected candidate byte strings after explicit experiment
authorization and successful external containment validation. Its subject is
`pd_sm_02_w1_diagnostic_healthy_v0`, not normal admission or production operation.
Its process record must identify that subject even when it copies existing
primitive semantics. It must never emit a PULSE release gate or modify normative
`status.json`.

The diagnostic harness is not supplied by this contract. It must not call the
existing launcher's private child executor to evade its public checks. It needs
its own reviewed entrypoint, input binding, supervision and observation path.
The future implementation and its tests are a separate change; any new permanent
regression must be registered in both applicable CI manifests in that change.

## 5. Source-to-runtime correspondence required before native execution

Freeze the final diagnostic-harness source, observer source, containment-controller
source, runtime identity and complete selected inputs in one run request. A
complete hash inventory must bind them to the intended run and attempt. Hashes
bind bytes; they do not establish safe behavior or platform authenticity alone.

Require an explicit per-primitive correspondence review against the pinned native
source regions listed in `PD_SM_02_W1_SOURCE_BINDING_v0.json`. At minimum:

- Compile the same UTF-8-decoded string accepted by the independent closed-language
  parsers; never let an encoding cookie reinterpret the original bytes.
- Preserve ordered request binding, exact request/target/payload checks,
  request-specific reservations, one-request monitor semantics, audit persistence
  before ACK, and the actual append operation.
- Do not add ACK/audit or single-use enforcement inside `append_sink` merely to
  make the negatives disappear. Those are model obligations checked before normal
  admission; they are not additional guards in the pinned append primitive.
- Keep `direct_sink_write` rejecting. Do not turn actor labels into an unsupported
  process-isolation or delegation claim.
- Drive observations from actual operations and outputs, not fixture labels,
  expected outcomes or model counterexample contents.

The `healthy` scenario mapping is the only mapping to establish. An unimplemented
monitor fault mode or a different submitted request is not silently substituted.
If the harness cannot preserve the relevant primitive semantics and actual effect
paths, classify the attempt as `HARNESS_SEMANTICS_MISMATCH` or `NOT_IMPLEMENTED`;
do not adjust the expected witness after observing the run.

## 6. External containment and authorization prerequisites

The candidate and diagnostic runner cannot be the sole authority for their own
containment. A separately controlled supervisor must establish and record a fresh
bounded instance with:

```text
repository mount: absent
repository/workflow write token: absent
production credentials and user secrets: absent
outbound network: denied and independently checked
inputs: immutable and digest-verified
writable effects: fresh designated scratch surface only
process/time/output limits: explicit, enforced and recorded
observer and supervision controls: outside candidate modification
cleanup: whole process tree and writable experiment state accounted for
```

These are requirements, not claims that the current environment already supplies
them. A temporary directory, an empty Python builtins namespace, a sealed source
copy or a declaration that a job is isolated does not alone satisfy this contract.
A later implementation must choose an exact containment mechanism and preserve
its source/configuration, platform evidence and admission tests.

Before candidate invocation, separate controls must demonstrate both sides: the
permitted scratch effect is possible, while out-of-bound file writes, network
access, unexpected descriptors and unbounded child/output behavior are rejected
within the declared threat boundary. A false Boolean in a report cannot replace
those observations. These controls have not been implemented or run here.

Owner authorization must name W1, the exact selection digest, final harness,
observer and containment identities, runtime profile, maximum five candidate
invocations and permitted scratch effects. This contract, its eventual merge,
previous pilot consent and a green CI result do not grant that authorization.
No local installation, external account access or workflow dispatch is requested
by this delivery.

## 7. Observation contract

The later observer must capture the effect **when it occurs**, not infer it from
the final state. Each event needs a run/attempt/case identity, exact candidate
and operation identity, process/actor mapping, request/target/payload binding,
actual operation return, written-byte count and independently acquired support
state at that boundary.

Record at least the following events where applicable:

```text
candidate_start
request_bound
reservation_accepted
monitor_request_submitted
intent_write_completed_and_persisted
ack_received_and_verified
sink_write_completed
candidate_terminal
supervisor_terminal
```

A supervisor/observer must bind successful writes to the inspected sink and
preserved raw bytes. Intent and ACK records must identify the same request as
the effect. Preserve actual stdout/stderr, child status, missing observations,
partial writes and interruption; do not reduce all nonzero exits to one refusal.

For ordering across monitor and effect processes, preserve explicit ordering
edges obtained from observed communication/barriers and operation completion.
Uncorrelated timestamps or equal final hashes are insufficient. Clock readings
may supplement those edges, not silently replace them. Observer instrumentation
must not insert the missing guard or reorder candidate operations. Its effect on
the program must be reviewed and bounded before claiming correspondence.

N08 specifically requires evidence that the successful sink write completed
before `broker_request` began. N07 requires two actual write completions, not
only a 44-byte terminal file or two modeled operations. N01 requires complete
observation of the relevant prefix; missing monitoring telemetry is not proof
that no intent existed.

The diagnostic experiment must stop if observer completeness or containment
cannot be established. The result remains incomplete, not a safety PASS.

## 8. Result classification and comparison

A later independent result checker must not import or execute candidate code and
must not treat the model verdict as a native result. Its conclusions are scoped
to the exact selected witness, candidate, scenario and diagnostic profile.

| Result field | Required meaning |
|---|---|
| `run_completed` | Required process and observation records are complete; says nothing by itself about safety |
| `native_witness_observed` | Actual effect matches the bound source operation and reproduces the selected false support at that effect prefix |
| `positive_control_observed` | P00 has the one exact useful effect with matching prior support |
| `primitive_refusal_observed` | N02 preserves the selected native route rejection; this is not a realized violating effect |
| `model_native_correspondence` | `MATCH`, `MISMATCH`, or `UNRESOLVED` for the explicitly selected projection; not the whole language |
| `containment_observed` | Separate outer-boundary result; cannot be inferred from an inner witness |
| `authority_effect` | Always `none` |

Expected defects in N01/N07/N08 are **violations of the inner monitored-effect
relation**, even when the experiment matches its prediction. Do not call them
safety PASS. A harness-induced refusal in one of those cases is not a reproduced
native witness. A different effect, missing prefix, parser failure, timeout,
observer failure or unsupported runtime must remain separately classified.

All W1 observation fields in this preparation remain null / `NOT_RUN`.
Do not splice the historical P00 observation into a new W1 run. Reused historical
model and admission records retain their original identities and roles.

## 9. Fixed execution budget and evidence retention

The prospective invocation order is P00, N01, N07, N08, N02, once each, with fresh
per-case state. P00 failure or any containment/observer/readiness failure stops
the remaining plan. Preserve the failed or incomplete attempt and keep subsequent
cases `NOT_RUN`. No automatic retry, replacement candidate, top-up, partial-run
splicing or after-the-fact change of expected outcomes is permitted.

Before a future run, retain the exact request and frozen inputs. After it, retain
the complete raw observation set, ordered event records, actual sink/audit bytes,
process outcomes, independent checker output, and a closed manifest. Preserve
failed and interrupted cases as well as successful ones. The preservation record
must distinguish run source, runtime, observer, harness, acquisition, verification
and later documentation identities.

The minimum next implementation milestone is a reviewed diagnostic harness plus
outer containment and ordered-observer admission tests. Only then can separately
authorized native acquisition test the three frozen witnesses. This document does
not declare that milestone complete.

## 10. Repository scope

This delivery adds this contract and its two JSON planning records and adds one
accurately classified link to `docs/INDEX.md`. It changes no root README, existing
result record, evidence archive/checksum, implementation, profile, fixture, test,
CI manifest, workflow, policy, gate registry, normative status, DOI or Software
Heritage surface. No experiment or workflow is run by these document additions.

The existing [implementation](../../examples/paradox_preexecution_impact_v0/README.md),
[E1 / MON-1 result](../PULSEMECH_PARADOX_E1_MON1_RESULT_v0.md) and
[E2 result](../PULSEMECH_PARADOX_COMPATIBILITY_RESULT_v0.md) retain their separate
scopes. W1 is not a general Python verifier, an arbitrary-hostile-code containment
proof, cross-interpreter compatibility, production enforcement, a physical
PULSEbox result or a new release-authority mechanism.
