# PULSEmech QRH003 audit reference v0

## Purpose and current state

QRH003 applies the PULSEmech evidence-to-decision mechanism to a fixed OpenAI
Math 003 subject: four configurations and five theorem exports associated
with the quasi-Riemann hypothesis reference case. The study provides source
observation, evidence admission, scoped offline decisions, decision replay
and post-decision transition observation.

The implementation is **v0.1.1**. Its native proof capture adapter is
**`NOT_IMPLEMENTED`**. The latest preserved source pilot produced **`BLOCK`**,
and its decision replay produced **`MATCH`**. No production QRH certificate
has been established. The audit result concerns the admitted evidence and
declared policy; it makes no judgment that the mathematical claim is false.

| Item | Fixed identity or state |
| --- | --- |
| Study source and operating instructions | [studies/openai_math_003_qrh_v0/README.md](../studies/openai_math_003_qrh_v0/README.md) |
| OpenAI Math subject commit | [`adc7f1241b42e322a6451854ab7e4b4c146bf78a`](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a) |
| PULSE primitive commit | [`288bb9a45764d2a30f72fdf4c417e9dd5b3087c5`](https://github.com/HKati/pulse-release-gates-0.1/tree/288bb9a45764d2a30f72fdf4c417e9dd5b3087c5) |
| Latest historical source pilot | `qrh003-pilot-002-20261007`, implementation v0.1 |
| Current source validation | 158 distinct local tests passed on 2026-10-08; zero skipped |
| Fixture evidence domain | `TEST` |
| Native proof capture | `NOT_IMPLEMENTED` |

The [configuration record](../studies/openai_math_003_qrh_v0/reference/configurations.json)
fixes the zeta, Dirichlet, Hecke and uniform Siegel configurations. Their
source identities and manuscript/formal-statement relationships are recorded
in the [claim map](../studies/openai_math_003_qrh_v0/reference/claim_map.json).
These bindings delimit the audit's subject; they do not expand it to an
entire manuscript or to later applications.

## What the study contributes

The study makes the evidence conditions for a scoped release decision
explicit and replayable. Its added object is the relationship between the
claimed subject, admitted artifacts, declared policy, executed checker and
resulting decision.

| Mechanism | Implemented contribution | Evidence boundary |
| --- | --- | --- |
| Source and scope binding | Check declared source identities and the exact configuration/export set | Static source observation does not establish compiler-resolved closure |
| Evidence admission | Verify bundle bytes, signatures, run/profile bindings and an externally supplied local anchor | A locally generated key does not establish institutional identity |
| Required-set materialization | Bind the selected policy to the exact ordered required gate set | Matching a policy name alone is insufficient |
| Offline enforcement | Invoke the nested, byte-pinned PULSE parser and gate checker; retain fail-closed decisions | Missing or inadmissible proof evidence cannot be replaced by a successful command message |
| Decision replay | Recompute and compare status, required-set and decision bytes | Identical decisions do not establish a second native proof build |
| Transition observation | Report endpoint, path, time, reconstruction and bounded control evidence after the decision | The observer has `authority_effect: NONE` |

The [implementation](../studies/openai_math_003_qrh_v0/tools/) and
[runtime notice](../studies/openai_math_003_qrh_v0/reference/pulse_runtime/NOTICE.md)
fix these mechanics and the primitive digests. The technical profile requires
ten gates; the semantic profile requires those ten plus three semantic/review
gates. Their exact identifiers and profile selection are defined in
[common.py](../studies/openai_math_003_qrh_v0/tools/common.py) and
[prepare.py](../studies/openai_math_003_qrh_v0/tools/prepare.py).

This study uses a local offline authority path within its own profile. It is
not registered as a new production gate in the repository's main release
workflow. The [Technical Overview](../PULSEMECH_TECHNICAL_OVERVIEW.md) remains
the entry point for the wider system's implemented state.

## The v0.1.1 Transition Meter observer correction

The study's [transition observer](../studies/openai_math_003_qrh_v0/tools/transition_report.py)
is a bounded application of the
[Transition Meter](../PULSEMECH_TRANSITION_METER.md). It records path completion
and reconstruction reproducibility as separate axes.

A missing-runtime TEST reproduction exposed a concrete error in the earlier
QRH observer. Evidence was admitted and a fail-closed decision replayed
exactly, but the policy parser and checker had not executed. The earlier
observer still reported a complete offline primitive path.

| Observation in the reproduced TEST case | Earlier observer | v0.1.1 observer |
| --- | --- | --- |
| Decision | `BLOCK` | `BLOCK` |
| Replay | `MATCH` | `MATCH` |
| Parser and checker attempted | Both `false` | Both `false` |
| Policy materialization verified | `false` | `false` |
| Transition-path status | `VERIFIED_FOR_DECLARED_OFFLINE_DECISION` | `INCOMPLETE_OFFLINE_PRIMITIVE_EXECUTION` |
| Reconstruction status | Decision replay verified | `VERIFIED_DECISION_REPLAY_ONLY` |

The false assertion was the complete-path label. A correctly reproduced
failure was being treated as evidence that every required primitive had
completed. The correction checks execution evidence directly while retaining
the independently established matching replay.

In v0.1.1, a complete offline-path label requires all of the following:

- Materialization is literal `true`, and both the materialized and decision
  gate lists equal the selected anchor's exact ordered required set.
- The parser was attempted, exited with integer `0`, did not time out, and
  verified the exact required set.
- The checker was attempted, exited with integer `0` or `1`, and did not
  time out. Exit `1` can represent a completed checker that correctly blocks.
- The report's admission, fresh recomputation, endpoint-byte and matching
  replay checks also succeed. A mismatch raises an error.

This establishes a precise implementation lesson: a reproducible result and
a completed execution path need their own evidence. The reproduced defect
is in the local observer's classification. It does not test or refute the
general Transition Meter architecture, and it does not establish that an
arbitrary incorrect calculation or unobserved omission can be detected.
The claimed observation remains limited to the declared predicates and
available artifacts. Thirteen
[observer regression tests](../studies/openai_math_003_qrh_v0/tests/test_transition_report.py)
retain this distinction.

The original reproduction record is preserved in the separately distributed
complete archive at
`studies/openai_math_003_qrh_v0/development_evidence/continuation_20261008/original_observer_missing_runtime_repro.json`.
It is TEST evidence. It does not replace or relabel the real historical
pilot's `BLOCK` decision.

## Reading the evidence states

**`BLOCK`** means the selected profile's conditions were not all established
by the admitted evidence. **`MATCH`** means the recorded decision was
reconstructed with the required byte equality. These outcomes can coexist.
A completed checker can also produce `BLOCK`; path completion and permission
are separate observations.

The current suite contains 145 declared collector-boundary tests plus 13
observer regressions. All 158 recorded distinct `PASS` outcomes in the local
source-subset validation on 2026-10-08. They exercise fixture-based audit and
authority mechanics. Native Lean proof execution was not part of that run.

At the pinned PULSE baseline, the main
[Tools smoke list](../ci/tools-tests.list) and
[pytest list](../ci/pytest-tests.list) do not include the study suite. Run
the study's own unittest runner in a fresh process with the environment
specified by its README. Repository CI success alone is not evidence that
these 158 cases ran.

## Historical replay and new work

The repository holds the source subset. Historical signed bundles, original
verifier snapshots, execution records, diagnostics and dependency wheels
belong to the separately supplied complete distribution. Its exact identity
and replay requirements are recorded in
[EVIDENCE_REFERENCE.json](../studies/openai_math_003_qrh_v0/EVIDENCE_REFERENCE.json).

| Complete distribution | Value |
| --- | --- |
| Filename | `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip` |
| Size | `23453781` bytes |
| SHA-256 | `ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc` |
| Public download location | Not recorded; distributed separately |

Historical `pilot_002` replay uses its original anchor, bundle and decision,
the preserved `runs/pilot_002/verifier_snapshot/tools/authority.py`, and the
pinned PULSE runtime. The archive's `REPLAY_PILOT.md` gives the procedure.
The v0.1.1 root verifier must not be substituted for that historical snapshot.

New work requires a fresh anchor for the actual local source and reference
inventory. The source subset preserves 17 study Python files and two pinned
PULSE Python primitives; its
[source manifest](../studies/openai_math_003_qrh_v0/SOURCE_MANIFEST.json)
covers that study directory. This documentation does not alter an existing
anchor or grant authority to a new one.

## Remaining work and acceptance boundary

Progress to a native technical result requires implemented proof capture
and admitted evidence for two isolated A/B builds, formal comparison, axiom
audits, compiler-resolved source and runtime closure, and the required
execution isolation and input/policy bindings. The current collector does
not provide that native capture path. The semantic profile additionally
requires its declared semantic, Lean-review and domain-review evidence;
review intake is not implemented.

The next implementation target is a capture adapter with explicit execution,
artifact and isolation contracts. A subsequent run must produce fresh
evidence under those contracts and be evaluated by the existing fail-closed
path. Local test success, documentation, a matching historical replay or a
green unrelated CI job cannot fill those missing records.
