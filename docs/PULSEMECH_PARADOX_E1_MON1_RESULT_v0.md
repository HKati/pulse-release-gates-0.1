# PD-SM-01-E1 / MON-1 — preserved local execution result v0

Classification: **Completed local execution record; bounded research evidence**.  
Experiment identifier: `PD-SM-01-E1`.  
Recorded experiment date: `2026-10-23`.  
Selected records: `evidence/finite_01` and `evidence/monitor_03`.  
Repository preparation basis: `4966249341842355e3223dd26500b3ee0a461623`.  
`authority_effect: none`; `production_gate_eligible: false`.

## 1. Original carrier and source identities

| Object | Exact identity |
|---|---|
| Original E1 archive | `PD_SM_01_E1_PROOF_EXTENSION.zip` |
| Archive bytes | `712329` |
| Archive SHA-256 | `88db43b1d42b98fa3fbfd63f1ce87e5e5ee787495732489c8e5a460a5fea1b21` |
| Archive Git blob SHA-1 | `df740005adbe8d5c49b23cda487f87922b771a4b` |
| Top-level ZIP file members | `201` |
| Complete outer checksum inventory | `200` entries; excludes only `SHA256SUMS` itself |
| Nested original E0 archive | `inputs/PD_SM_01_E0_PY3135_RESULT.zip`; `742176` bytes |
| Nested E0 SHA-256 | `095a3ea8717d89685094551c89e74525349cb5fcca60b3394d9bbb696454781f` |
| Nested E0 file members / checksum entries | `695 / 694` |
| Historical source commit | `102145d1f1c321811c52d9d20f92cc7289127b2b` |
| Historical semantic commit | `cbeab94d8532482d34ab857bf38e9e56ae265f84` |
| Declared historical source files checked | `12 / 12` Git blob identities |
| E0 evaluator SHA-256 | `d4bc8021f51ce6e4352fee35fbb935de8c48b6e0598d86fd9f960d308846954c` |
| E0 evaluator Git blob SHA-1 | `5a84083598d8fadfd165c3d7b29ab1f276a1d3bd` |

Repository evidence:

- [Original E1 ZIP](evidence/PD_SM_01_E1_20261023/PD_SM_01_E1_PROOF_EXTENSION.zip)
- [Original E1 ZIP SHA-256](evidence/PD_SM_01_E1_20261023/PD_SM_01_E1_PROOF_EXTENSION.zip.sha256)

The archive is preserved byte-for-byte as an ordinary Git blob, including its
nested E0 archive, earlier development records and historical scope statements.
It is not the hosted E2 artifact or the separately prepared E2 preservation
wrapper. No GitHub Actions run ID or hosted provenance is assigned to E1.

The archived E0 evaluator is byte-identical to the repository evaluator at the
preparation basis above. E1's extension programs have their own recorded content
identities; the historical repository source commit is not an execution commit
for those later local extension programs.

| Archived program | Bytes | SHA-256 |
|---|---:|---|
| `code/finite_profile.py` | 6095 | `017fc009933be55eb98507da393a6c8c7ea44881711354ea231e7a75ebb8e856` |
| `code/enforcement_probe.py` | 15948 | `7219702636681fa7109072ff532ed1dc73c5585fe45eb02d613cd9d8538c89b6` |
| `code/verify_results.py` | 4127 | `efac48e07ffe5366f21f9e2e012048634164c817206333b9f602985a9ecd5df7` |

The selected recorded runtime is CPython 3.13.5, Linux x86_64. MON-1 records
kernel `6.18.55`, supervisor thread count `1`, UID `0`, and `-I -S -B` isolation
flags. The recorded Python executable SHA-256 is
`17b78e0a93175e86f9ac03141924fd7a7f0c0c52e66b34bfa0de20ffef989df1`.
These are retained local runtime observations, not independent platform
attestation. No complete kernel/shared-library binary closure is asserted.

## 2. F1 — complete finite relation/evidence profile

Domain: nine binary relationship switches and every subset of four admitted
source premises. The protected subject remains the original latency relation.
The domain includes violating configurations.

| Field | Recorded result |
|---|---:|
| Link-switch assignments | 512 |
| Evidence subsets per assignment | 16 |
| Distinct `(assignment, evidence_mask)` rows | 8192 |
| Rows agreeing with the declared predicate | 8192 |
| Discrepancies | 0 |
| Relation violations | 8128 |
| Unresolved source assessments | 7680 |
| Justified original protected-subject proofs | 1 |

The last three counts are overlapping classifications, not additive test totals.
The complete transcript is `evidence/finite_01/F1_all_assignments.jsonl`.
For the bit order stored in that transcript, the independent link predicate is:

```text
b0 = b3 = b4 = b7 = b8 = 0
AND
b1 = b5 = b6
```

The source-assessment and proof-applicability predicates remain separate from
link satisfaction. The recorded `freeze.json` binds the evaluator, finite-profile
program and original E00 input. The current inspection recomputes the declared
predicate for each stored row without executing the archived evaluator.

## 3. F2 — grounded closure and sub-base comparisons

Domain: three propositions, all subsets of six non-self unary rules plus three
two-premise rules, and all eight base subsets.

| Field | Recorded / reconstructed value |
|---|---:|
| Rule subsets | 512 |
| Base subsets | 8 |
| Complete rule/base rows | 4096 |
| Agreement: bottom-up closure versus intersection of all closed supersets | 4096 / 4096 |
| Aggregate sub-base comparisons reported by the original program | 13824 |
| Strict withdrawals within that total | 9728 |
| Unchanged-base controls within that total | 4096 |
| Discrepancies | 0 |

The original `F2_withdrawal_comparisons` field includes `subbase == base`.
It is not a count of 13824 strict withdrawals. The full 4096-row transcript is
`evidence/finite_01/F2_all_profiles.jsonl`. Each possible sub-base is itself a
row for the same rule set, so all 13824 sub-base relations can be reconstructed
from that complete table.

Individual historical withdrawal receipts are **not stored**. The original
execution supplies its aggregate count, preserved loop and zero-failure summary.
The preservation inspection separately recomputes every row's closed-set
intersection and checks all 13824 table-derived sub-base relations, including
monotonicity under withdrawal. This is record verification, not a fresh
execution of the historical program.

The conditional least-closure derivation is retained in
`docs/CONDITIONAL_PROOFS_AND_PHYSICAL_TEST.md`. Derivation depth is not introduced
as a mechanical time coordinate.

## 4. MON-1 — selected local monitored-effect experiment

Protected effect: append to a new local scratch file. Participants: trusted
supervisor/broker, separate monitor process, restricted worker and forked
delegate. Worker restrictions: descriptor minimization and a default-deny
seccomp filter. The broker re-evaluates the E0 evidence and binds the selected
subject, input envelope and assessment to each request.

Selected run directory: `evidence/monitor_03`.

| Class | Cases | Recorded result |
|---|---:|---|
| Guarded cases with the exact useful effect | 3 | One exact 22-byte append and one matching intent record in each case |
| Guarded cases without effect | 13 | Empty target file |
| Deliberately unguarded ablation | 1 | 11-byte `UNMONITORED` write; no audit record |
| Total expected/observed comparisons | 17 | 17 `MATCH` |

| Case | Probe | Target bytes | Audit records | Recorded distinguishing result |
|---|---|---:|---:|---|
| M00 | Direct write | 0 | 0 | `EPERM` |
| M01 | Guard removed | 11 | 0 | Expected unmonitored effect |
| M02 | Delegated direct write | 0 | 0 | `EPERM` |
| M03 | `/proc` descriptor reopen | 0 | 0 | `EPERM` |
| M04 | Native `openat` syscall | 0 | 0 | `EPERM` |
| M05 | Inherited sink descriptor | 0 | 0 | `EPERM` |
| M10 | Valid broker request | 22 | 1 | Exact monitored effect |
| M11 | Valid delegated request | 22 | 1 | Exact monitored effect |
| M20 | Monitor unavailable | 0 | 0 | Monitor admission rejected |
| M21 | Monitor exits before acknowledgement | 0 | 1 | Intent alone does not permit the effect |
| M22 | Acknowledgement without audit record | 0 | 0 | No exact audit record |
| M23 | Wrong acknowledgement | 0 | 1 | Acknowledgement mismatch |
| M30 | Payload substitution | 0 | 0 | `BOUND_REQUEST_MISMATCH` |
| M31 | Target substitution | 0 | 0 | `BOUND_REQUEST_MISMATCH` |
| M32 | E20 violated relation | 0 | 0 | `SOURCE_CONDITION_NOT_JUSTIFIED` |
| M33 | E30 missing source evidence | 0 | 0 | `SOURCE_CONDITION_NOT_JUSTIFIED` |
| M40 | Replayed valid request | 22 | 1 | One effect; `ALREADY_CONSUMED` on repetition |

Each case retains `RESULT.json`, `source_assessment.json`, `sink.bin` and
`monitor.jsonl`. The inspection compares actual stored sink and audit bytes,
canonical request/subject/assessment hashes, E0 input/output bindings, recorded
process exit statuses and broker stages. All 17 source-assessment records agree
with the corresponding preserved E0 E00/E20/E30 outputs. This does not re-observe
the original kernel or processes.

The invariant argued for the admitted path is:

```text
effect(request)
  => justified source condition
     AND exact bound request
     AND matching pre-operation intent record
     AND single-use request identity
```

The kernel, controlling supervisor, broker and monitor are trusted within this
experiment. Arbitrary hostile broker/monitor behavior, external privileged
writers, kernel compromise, power-loss persistence and continuous post-effect
telemetry are outside the selected boundary. MON-1 is a local engineering
experiment, not production authority integration or a physical PULSEbox result.
The unguarded ablation's `MATCH` records the expected violation, not safety PASS.

## 5. Preservation inspection and retained history

The archive inspection performed for this preparation is read-only:

| Inspection | Result |
|---|---|
| Original ZIP identity, CRCs, bounded regular-file paths and duplicate-path checks | 201 / 201 members |
| Outer SHA-256 inventory and complete coverage | 200 / 200 |
| Nested E0 identity, CRCs and inventory coverage | 695 members; 694 / 694 hashes |
| Historical source Git blob identities | 12 / 12 |
| F1 coverage, bit order and independent result predicates | 8192 / 8192 |
| F2 coverage and independently reconstructed closed-set intersections | 4096 / 4096 |
| F2 sub-base relations reconstructed from the full table | 13824 / 13824 |
| Selected MON-1 source, case, request, assessment, target and audit bindings | 17 / 17 |
| Selected finite/MON-1 exit records and stdout summaries | Exit 0; empty stderr; matching summaries |
| Retained monitor_01 / monitor_02 source snapshots | Both match their recorded source digests |

No archived program was imported or executed during this inspection. The new
inspection utility and its 16 controls are preparation-side validation, supplied
separately from the repository files; they are not extra E1/MON-1 experiment
trials. The original `code/verify_results.py` remains unchanged in the ZIP.
Its historical checks do not include every additional preservation inspection
listed here, notably the complete sub-base reconstruction.

`monitor_01` and `monitor_02` remain development history; only `monitor_03`
supplies the selected 17-case claim. The first run's fork warning remains in
its stderr. The recorded pre-execution files are source/expectation bindings,
not externally authenticated proof of preregistration time. The contract also
retains the explicit refinement adding M32 and M33 before the selected run.

The archived E1 compatibility status remains `INCOMPLETE`, and its local
multi-version runner remains an unexecuted historical proposal. The later
[hosted E2 record](PULSEMECH_PARADOX_COMPATIBILITY_RESULT_v0.md) separately
establishes E0 compatibility on four named interpreters. It does not establish
multi-version F1/F2 or MON-1 compatibility. No archived `NOT_RUN`, `INCOMPLETE`
or failure record is rewritten.

## 6. Offline inspection entrypoints

From the repository root, check the original outer archive without extraction:

```sh
(cd docs/evidence/PD_SM_01_E1_20261023 && \
  sha256sum -c PD_SM_01_E1_PROOF_EXTENSION.zip.sha256)
```

For the original read-only result verifier, safely extract the verified archive
into a new directory outside the repository, rejecting traversal and symlinks.
`E1_ROOT` denotes its extracted `PD_SM_01_E1_PROOF_EXTENSION` member root:

```sh
E1_ROOT=/absolute/path/to/PD_SM_01_E1_PROOF_EXTENSION
python3 -I -S -B "$E1_ROOT/code/verify_results.py" "$E1_ROOT"
```

This reads the stored tables, target files and audit logs. It does not launch the
monitor, worker, model, interpreter acquisition or E1 experiment. Its expected
output is 200 verified inventory files, 8192 F1 rows, 4096 F2 rows and 17 MON-1
cases, with the 3 / 13 / 1 effect split. A future verifier invocation has its own
result and is not already performed merely because this command is documented.

Historical experiment and proof paths inside the original ZIP:

| Internal path | Role |
|---|---|
| `docs/PROOF_CONTRACT.md` | Finite domains, expected cases and trust assumptions |
| `docs/CONDITIONAL_PROOFS_AND_PHYSICAL_TEST.md` | Conditional derivations and unexecuted physical protocol |
| `evidence/finite_01/freeze.json` | Finite-program/evaluator/input/runtime bindings |
| `evidence/finite_01/F1_all_assignments.jsonl` | All 8192 F1 rows |
| `evidence/finite_01/F2_all_profiles.jsonl` | All 4096 F2 rows |
| `evidence/finite_01/RESULTS.json` | Selected finite execution summary |
| `evidence/monitor_03/PREEXECUTION.json` | Selected case list, source and environment record |
| `evidence/monitor_03/RESULTS.json` | Selected 17-case execution summary |
| `evidence/monitor_03/<CASE>/` | Source assessment, request/result, target bytes and audit bytes |
| `inputs/PD_SM_01_E0_PY3135_RESULT.zip` | Exact original E0 source/evidence package |
| `code/verify_results.py` | Original read-only result verifier |

The preserved finite checks and local observations do not assert arbitrary
Paradoxon representation completeness, general sandbox security, physical time
emergence or production integration. The archived physical LED/sensor protocol
remains `NOT_RUN`. Existing release policy, strict checker and authority
mechanism remain unchanged.
