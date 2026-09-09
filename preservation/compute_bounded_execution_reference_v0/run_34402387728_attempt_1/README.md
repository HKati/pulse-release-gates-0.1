# Step 5B — observed reference preservation and source-bound replay

## Record boundary

This directory preserves the actual owner-dispatched reference from work order
#2875 and the subsequent local verification of that exact artifact. It does not
change the Step 5B implementation, active policy, the original strict checker,
historical #6066 evidence, or any existing workflow.

Acquisition and verification are separate evidence events. The source is the
actual #2876 merge, not a preparation commit or a temporary PR test merge.
This preservation handoff does not predeclare its own future CI/review result,
issue closure or canonical-documentation acceptance.

## Acquired identities

| Field | Value |
| --- | --- |
| Repository | `HKati/pulse-release-gates-0.1` |
| Workflow | `PULSEmech bounded execution reference` |
| Event / branch | `workflow_dispatch` / `main` |
| Run / number / attempt | `34402387728` / `1` / `1` |
| Job | `102637163024` |
| Artifact | `10123984621` |
| Source commit | `c32508f8afb58381225fec0b426b85b00e32fe11` |
| Source tree | `74dd65d82124170b7d8f459925962bb8bc09fe2b` |

GitHub's independently retrieved attempt, job and artifact metadata agree on the
source and run. Both acquisition/reconstruction and artifact upload steps report
success. Selected connector fields and decoded log excerpts are in the evidence
archive. They are explicitly not presented as preserved raw HTTP response bytes
or a complete raw job log. Their trust root is the connected GitHub API/log view,
not a new signed execution attestation.

| Exact byte object | Bytes | SHA-256 |
| --- | ---: | --- |
| Downloaded GitHub artifact | 3270026 | `2601a68b864779b8cf99a6a2bc0fdb48c994b95067f098354d35e86e7ff178f6` |
| Inner reference capsule | 3269864 | `f726c9c240512e6f13d34bebbcfa549696adff560ee718abae84f4f121d2bc7a` |
| Prepared input carrier | 1456425 | `8b3300fc928259155e7966d1618b9629ff73a99defcfac502d643c6b622e6aa5` |
| Captured evidence carrier | 1489242 | `8097b20f4ae41686d81f113f1a06cb5eb8289b4e6ccc19a4a1e38fc09c82ab8c` |
| Acquired reconstruction carrier | 322567 | `2d54aba44975111e38abcf010819dce160006742243a7f46930cd86f42747cf1` |

Prelaunch SHA-256:

```text
0c3e602d54036e5825bf3a9aaf98fdeb98d1ac907c4427512a31dc02fa77ba80
```

The artifact ZIP is copied without byte changes. Its inner capsule is not
repacked. The six capsule members and five payload checksums were checked.
`prepared.zip` has 39 members; `capture.zip` has 55; the reconstruction has 12.
The capture's prepared inputs exactly equal the separately preserved preparation.

## Fresh local verification

The local environment was CPython 3.13.5, jsonschema 4.26.0 and PyYAML 6.0.3.
The acquisition log reports CPython 3.11.16. The compared output identity is a
result for these exact inputs and executions, not a universal cross-version claim.

All 28 source-inventory files matched the authenticated commit's Git blobs, the
clean installed source tree, the prepared carrier and the captured carrier.
Expected acquisition context was formed from separately retrieved GitHub fields,
not trusted merely because the capsule supplied an `expected_context.json`.

The preparation recipe was rerun from those exact sources and external context,
reusing only its preserved declared creation timestamp. It reproduced the entire
1,456,425-byte prepared carrier. Its reconstructed prelaunch digest was supplied
outside the capture to subsequent validation. This is not an independent
pre-acquisition timestamp attestation; ordering remains within the declared
supervisor/control-plane trust boundary.

Two complete independent-validator CLI invocations returned exit 0. Two further
separate reconstruction processes returned exit 0 and reproduced the entire
322,567-byte reconstruction ZIP exactly, including all 12 members. The reconstructed
report diagnostic contains 10/10 true checks; the relation diagnostic contains
34/34 true checks. These are diagnostic checks, not counts of pytest tests.

A first local reconstruction attempt was interrupted by the tool's 120-second
wall-clock limit before a completed exit record. It is retained as interrupted,
not PASS. The two later completed invocations have separate command, timing,
stdout, stderr and output identities. No fresh subject capture was performed.

## Observed cases and predicate separation

| Case | Actual checker exit | Consumer terminal state | Expected result matched |
| --- | ---: | --- | --- |
| `allow` | 0 | ready | true |
| `block_false` | 1 | held | true |
| `missing_required` | 2 | held | true |

Exactly six checker/consumer occurrences are bound. The resulting relation has
six expectations, six observations and six decisive planned/observed relations.
There are zero unresolved relations within this declared boundary.

```text
scope: six_declared_direct_processes_and_their_bound_io
I — bounded packet integrity: complete
E — bounded observation extent: complete
R — bounded relational coverage: complete
C — comparison_complete: true
M — resource coverage: unavailable
```

Whole-runtime-packet coverage remains `partial`; its seventh execution record is
the explicitly partial projection collector, not a seventh observed subject.
There are no resource-measurement records. The generic runtime-report summary
retains `authority_binding_complete: false` and `decision_closure_complete: false`.
This is separate from the bounded comparison's qualified relationships.

```text
compute_transition_path_complete: true
compute_transition_authority_binding_ok: true
compute_transition_unbound_mutation_absent: true
```

These three values belong only to the non-active compute candidate. They neither
change the two observed blocking checker results nor grant production authority.
The artifact-only baseline remains distinct and is hash-bound into the runtime
report. This local comparison does not claim a new complete #6066 historical replay
or completion of every wider fixed-source/runtime comparison in Step 5.

## Fresh negative checks on the acquired evidence

All ten local scenarios met their rejection/preservation assertions. Each actual
CLI returned exit 2 where rejection was expected. These are local review probes,
not newly registered permanent tests. Mutants are stored separately; the original
artifact and source checkout remain unchanged.

| Scenario | Observed rejection |
| --- | --- |
| `cross_run_context` | `acquisition_context_mismatch` |
| `wrong_prelaunch_digest` | `prelaunch_digest_mismatch` |
| `altered_committed_source_bytes` | `source_bytes_mismatch` |
| `missing_execution` | `evidence_schema_rejected` |
| `wrong_occurrence_order` | `execution_extent_mismatch` |
| `cross_case_consumer_input` | `execution_input_binding_mismatch` |
| `forged_execution_source_digest` | `execution_source_mismatch` |
| `block_promoted_to_ready` | `terminal_consumption_or_state_mismatch` |
| `connected_reconstruction_rejects_wrong_consumer` | `bounded_input_rejected: execution_input_binding_mismatch` |
| `existing_output_preserved` | `bounded_input_rejected: output_already_exists` |

The connected wrong-consumer reconstruction produced no output. A complete valid
reconstruction directed at a pre-existing unrelated file rejected publication and
left that file byte-identical. Manifest and ZIP repairs in the mutation probes
avoid confusing intended semantic rejection with accidental CRC corruption.

## Source-object availability and offline transport

Direct Git network access from the local container failed DNS resolution. The
connected GitHub Git-data API did supply the source commit's signed payload,
signature and tree. The exact 3,728-byte commit object was transported from those
fields and its Git object hash matched `c32508f8...`. GitHub reported its PGP
signature valid; this review did not perform separate local PGP verification.

The full file tree was recovered through the earlier content bundle and the two
inventory replacements, then checked against the independently retrieved upstream
root tree. No local preparation commit was relabelled as the GitHub commit.

For portability, the evidence archive contains a source-object pack with the
actual source commit and its complete tree/blob closure: 1,569 objects and 1,396
tracked files. A fresh repository imported it, checked out the genuine commit and
matched all 1,569 object bodies and the complete tree. It deliberately contains no
ancestor history and no synthetic preparation commits. It is a complete source
snapshot, not a full-history clone and not enough for an unrelated historical
#6066 campaign. Instructions are in `REPLAY.md` inside the evidence archive.

## Files and preservation scope

```text
pulsemech-bounded-reference-34402387728-1.zip
verification_record_v0.json
verification_evidence_v0.zip
preservation_manifest_v0.json
README.md
```

The preservation manifest hashes the other four files and excludes itself.
Neither that manifest nor the evidence archive's manifest is an authority verdict.
The top-level repository README is not modified by this directory's README.
No source, schema, test, workflow, policy or registry file changes are included.

After repository preservation and its review, the canonical workstream surfaces
still need their separate state update and a bounded work-order completion record.
Do not treat this handoff alone as already-merged preservation or full Step 5 closure.

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

No resource measurement, compute budgeting, deployment admission or Step 7 gate
promotion is introduced. The trusted acquisition boundary remains the reviewed
supervisor, interpreter/runtime, kernel and GitHub control-plane metadata.

```text
A tényleges referenciafutás pontos csomagját külön, Git-forráshoz kötötten
ellenőriztük. A két befejezett rekonstrukció mind a tizenkét kimeneti fájlban
és a teljes ZIP bájtjaiban megegyezik a GitHubon előállított eredménnyel.
A tíz ellenpróba a megfelelő elutasítást vagy kimenetmegőrzést adta.
Ez a hat megfigyelt folyamat körülhatárolt bizonyítása; nem erőforrásmérés,
nem aktív compute-gate és nem produkciós release-engedély.
```

Refs #2875. Implementation: #2876.
