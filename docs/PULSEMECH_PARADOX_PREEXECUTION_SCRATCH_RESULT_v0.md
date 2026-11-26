# PD-SM-02 — source-bound pre-execution scratch pilot result v0

Classification: **Completed bounded local execution record; source-bound scratch evidence**.  
Experiment identifier: `PD-SM-02-SCRATCH-PILOT-v0`.  
Recorded execution date: `2026-10-27`.  
Implementation commit: `4cb5f7dbe00cfbaf5bd50f77423e4d671fa71905`.  
Profile: `PD-SM-02-preexecution-impact-v0`.  
`authority_effect: none`; `production_gate_eligible: false`.

## 1. Result

The merged PD-SM-02 implementation was exercised in one bounded local scratch
pilot. The pilot preserved the distinction between model assessment, launch
eligibility and observed native execution.

| Measurement | Result |
|---|---:|
| Exact implementation regressions before pilot | `112 passed` |
| Declared fixture obligations materialized | 24 |
| Classification / binding outcomes matching the fixture contract | 24 / 24 |
| Launch-eligible cases | 4 |
| Completed native scratch executions | 4 / 4 |
| Non-eligible authorized launch attempts | 20 |
| Non-eligible attempts blocked before output-directory creation | 20 / 20 |
| Completed positive effects | One exact 22-byte effect per executed case |
| Completed positive audit records | One matching `INTENT` record per executed case |

The four executed cases were `P00`, `P01`, `P02` and `P04`. The other twenty
cases did not execute candidate code. Their separately authorized launcher
attempts terminated before the requested output directory was created.

## 2. Repository implementation identity

Repository: `HKati/pulse-release-gates-0.1`  
Merged implementation commit: `4cb5f7dbe00cfbaf5bd50f77423e4d671fa71905`

The evidence package contains a byte-for-byte implementation snapshot. Its Git
blob identities match the seven files at the merged commit:

| File | Git blob SHA-1 | SHA-256 | Bytes |
|---|---|---|---:|
| `README.md` | `289d20c0903a6bd4e787aa91c3d14ba5765e6c0a` | `6c7f70a5add3d0cd1eb293798eb0ac5c805858e1d4396e9b0762a1a93313fb31` | 8412 |
| `check_impact.py` | `3cef3a623bafff032f993c96357a29294068f0d4` | `244c38c0c27ecd313328918b33c006d9273f01f5b4279be3dbf8f09c5888c9dd` | 38686 |
| `fixtures.json` | `76542b40898d5c13deb9163addfed9fddb47ebe0` | `f815403ae44bdbf90f63654777f53ed998e9b1ade651cf1a0927287a7ec62a19` | 47697 |
| `profile.json` | `1cd2e5928ff86e745deb8fb5a991e718448cfd7c` | `f9a469e7cf35a41e1812e1577a9c5cbb5370d537cebe54f5a16bee17aeec16d0` | 8974 |
| `run_local.py` | `dbde9517f39082a854f31ef8b97be200c9efeb75` | `9646d7c4b25034a8ab5add881c9a4ce760fd0f1cf47ab37d69a389c5b2d89e68` | 22844 |
| `source_model.py` | `5c81b43f4bf5d02118058627c48371f8996b4d70` | `2bf013c8f3f645fe32d5084852756ebf58d519c3a46df78fe03ae84a373d7714` | 14073 |
| `test_preexecution.py` | `2571640af4893df8ec1e364ac39d412c4a1401ce` | `a92688932164e0bf32be21f5c885ef5f0f208a69f014e2caac235240cce170a0` | 19918 |

This is the implementation actually assessed and launched. It is not the earlier
preparation snapshot and not an unmerged PR head.

## 3. Original evidence carrier

Repository evidence:

- [PD-SM-02 scratch-pilot ZIP](evidence/PD_SM_02_SCRATCH_PILOT_20261027/PD_SM_02_SCRATCH_PILOT_20261027.zip)
- [PD-SM-02 scratch-pilot ZIP SHA-256](evidence/PD_SM_02_SCRATCH_PILOT_20261027/PD_SM_02_SCRATCH_PILOT_20261027.zip.sha256)

| Field | Exact value |
|---|---|
| Archive filename | `PD_SM_02_SCRATCH_PILOT_20261027.zip` |
| Archive bytes | `329950` |
| Archive SHA-256 | `c63f2ee6e2dfae21ec3736fbd99f8169b8c5b7a06a28c8a8a3e7dad2ac2fcd18` |
| ZIP members | `473` |
| Internal closed-manifest SHA-256 | `26083c5fffbfdbc4cef002db59663d6a0a262d5f36a737f8dcd4a5f20484d178` |
| Internal manifest entries | `471` |
| Separate preparation-side verifier checks | `718 / 718 PASS` |

The archive preserves the implementation snapshot, environment record, complete
24-case inputs, source-derived models, independent assessments, preflight
records, raw command stdout/stderr, four positive scratch outputs, twenty
blocked-launch records, the execution protocol and a read-only package verifier.

The preparation-side verifier is supplied separately from the repository files.
It replayed model, checker and preflight records and checked the archive contents;
it is not an additional native pilot execution or third-party validation.

## 4. Recorded runtime boundary

| Field | Recorded value |
|---|---|
| Python | `CPython 3.13.5` |
| Platform | `Linux-6.18.55-x86_64-with-glibc2.41` |
| Machine | `x86_64` |
| C library | `glibc 2.41` |
| Python compiler | `GCC 14.2.0` |
| POSIX fork | `true` |
| `memfd_create` | `true` |
| `/proc/self/task` inventory | `true` |

The source was sealed in memory before each eligible child execution. The
launcher required a single-thread supervisor, exact candidate/profile/context
bindings, independent checker replay, canonical assessment equality, a new empty
output directory and the profile's exact scratch-only authorization literal.

This is a project-produced local runtime record. It is not an independent
platform attestation, cross-interpreter compatibility result or complete binary
closure of the kernel, C library and Python runtime.

## 5. Case results

| Case | Declared distinction | Observed classification / binding result | Separate preflight-only status | Separate preflight-only reason | Authorized launch result | Authorized launch terminal reason |
|---|---|---|---|---|---|---|
| `P00` | Baseline, exact subject and complete evidence | `ESTABLISHED_CONDITIONAL` | `ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH` | `eligible` | COMPLETED | — |
| `P01` | Private-local renaming | `ESTABLISHED_CONDITIONAL` | `ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH` | `eligible` | COMPLETED | — |
| `P02` | Safe delegated request | `ESTABLISHED_CONDITIONAL` | `ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH` | `eligible` | COMPLETED | — |
| `P03` | Removal of a redundant check under fixed monitor lifetime | `PROPERTY_DEPENDENT` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `launch_preflight: NO_UNCHECKED_LAUNCH` |
| `P04` | Alternative valid justification | `ESTABLISHED_CONDITIONAL` | `ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH` | `eligible` | COMPLETED | — |
| `N01` | Write before monitor evidence | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N02` | Unrestricted delegated helper | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N03` | ACK without audit accepted | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N04` | Wrong ACK accepted | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N05` | Missing source admitted | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N06` | Request substitution accepted | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N07` | Two effects under one reservation | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N08` | Safe endpoint after unsafe prefix | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N09` | Disable all useful operation | `SAFETY_ONLY_NOT_ACCEPTABLE` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N10` | Ungrounded evidence cycle | `UNRESOLVED` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `N11` | Incompatible joint support | `REFUTED_IN_MODEL` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `U01` | Unknown or dynamic code | `UNRESOLVED` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `U02` | Omitted helper route | `INVALID_MAPPING` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `U03` | Empty or inconsistent model | `INCONSISTENT_OR_INVALID` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `B01` | Post-assessment source replacement | `BINDING_REJECTED` | `BINDING_REJECTED` | `candidate_sha256` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `B02` | Changed environment or primitive | `UNRESOLVED_OR_BINDING_REJECTED` | `UNRESOLVED_OR_BINDING_REJECTED` | `environment_identity` | BLOCKED BEFORE OUTPUT | `assessment_replay_mismatch` |
| `B03` | Cross-target proof reuse | `BINDING_REJECTED` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `O01` | Missing or failed effect observer | `OBSERVATION_INCOMPLETE` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |
| `O02` | Pre-execution boundary and bounded interruption | `NO_UNCHECKED_LAUNCH` | `NO_UNCHECKED_LAUNCH` | `assessment_not_eligible` | BLOCKED BEFORE OUTPUT | `checker_replay_not_eligible` |

`P03` remains `PROPERTY_DEPENDENT`: removal of the replay-membership check alone
was not classified as a violation under the unchanged one-request monitor
lifetime, but it was also not launch-eligible. The pilot therefore preserved the
false-block control without converting it into a native execution claim. Its
authorized launcher attempt reached the launch-preflight stage and stopped with
`launch_preflight: NO_UNCHECKED_LAUNCH`.

`B01` and `B02` used a post-assessment candidate or environment substitution.
Their original assessments remained preserved. The separate `--preflight-only`
records rejected reuse through `candidate_sha256` and `environment_identity`.
Those preflight reasons are not the terminal error codes returned by the later
authorized launch attempts. `B01` stopped earlier during checker replay with
`checker_replay_not_eligible`; `B02` completed checker invocation but stopped on
canonical replay comparison with `assessment_replay_mismatch`. Neither attempt
reached `execute_scratch` or created an output directory.

## 6. Positive native observations

| Case | Candidate SHA-256 | `RESULT.json` SHA-256 | Sink SHA-256 / bytes | Audit SHA-256 / bytes |
|---|---|---|---|---|
| `P00` | `53db7f3389a37ccd59792d0309abc1890e23d172698490c3d8207853908adb04` | `17fb3c50b370549efb9dab54f77a2ac496c5c0bdcfa26a5f99a72fc076062513` | `66cb67b6520b7db10e7f1f3e057dae188a45c0268fdafba08985b2f87b3a9fb4` / 22 | `38137af8b4b411abd80e26dd5cd85ac79f77128feeecb9ec2504c4c2e65b980d` / 204 |
| `P01` | `3367cb2cf72ad7799ef5e164bf2253dce21256e88b5acb55f9ab7181aa5de5c6` | `d283a022d502adb0a5ea66bf73eea57843361c73dfbcbf03d45b135b732b5020` | `66cb67b6520b7db10e7f1f3e057dae188a45c0268fdafba08985b2f87b3a9fb4` / 22 | `38137af8b4b411abd80e26dd5cd85ac79f77128feeecb9ec2504c4c2e65b980d` / 204 |
| `P02` | `9dd80b5ffdf5942b7e09fff40fb85c0b6d1d96a58ac4a4d1d0a38067f6c09fb5` | `80c828a8d7c7ec1a1dfda67de06ec78f0aafb170bc22c1b312886db7d54fd9ac` | `66cb67b6520b7db10e7f1f3e057dae188a45c0268fdafba08985b2f87b3a9fb4` / 22 | `38137af8b4b411abd80e26dd5cd85ac79f77128feeecb9ec2504c4c2e65b980d` / 204 |
| `P04` | `53db7f3389a37ccd59792d0309abc1890e23d172698490c3d8207853908adb04` | `74618b53204b34b667107250fc542f8c339e121d1e093970cc1f99e39fb7253a` | `66cb67b6520b7db10e7f1f3e057dae188a45c0268fdafba08985b2f87b3a9fb4` / 22 | `38137af8b4b411abd80e26dd5cd85ac79f77128feeecb9ec2504c4c2e65b980d` / 204 |

For every completed case:

```text
child status = COMPLETED
child normal exit = true
child exit code = 0
effects = [{request_id: request-0, bytes: 22}]
sink bytes = BOUND_MONITORED_EFFECT
audit records = 1 matching INTENT record
authority_effect = none
```

`P00` established the baseline relation, `P01` preserved it under private-local
renaming, `P02` preserved it through the admitted delegated request role, and
`P04` preserved it with a separately grounded alternative justification.

The common sink and audit byte identities are expected because the protected
request, target and useful effect are intentionally identical across those four
cases. Candidate and assessment identities remain distinct where the program or
evidence relation differs.

## 7. Pre-execution refusal observations

The twenty non-eligible cases were passed to the exact authorized launcher path.
None created its requested output directory, and none executed candidate code.
The refusal set included:

```text
PROPERTY_DEPENDENT without launch eligibility
model counterexamples
safety-only / no-useful-operation result
unsupported closed-language coverage
invalid or empty model
post-assessment candidate and environment replacement
cross-target proof reuse
missing observer completion
incomplete pre-execution boundary
```

The artifact preserves two distinct refusal records for each non-eligible case:
a separate `--preflight-only` result and the terminal result of the later
authorized launcher attempt. The authorized attempts ended at three distinct
surfaces:

- Eighteen cases — `B01`, `B03`, `N01`–`N11`, `O01`, `O02` and `U01`–`U03` —
  stopped during independent checker replay with
  `checker_replay_not_eligible`.
- `B02` stopped after checker invocation because the replayed assessment no
  longer matched the supplied preserved assessment:
  `assessment_replay_mismatch`.
- `P03` reached the launch-preflight stage and stopped with
  `launch_preflight: NO_UNCHECKED_LAUNCH`.

Separately, the earlier preflight-only records for `B01` and `B02` reported
`candidate_sha256` and `environment_identity`. Those values demonstrate the
standalone binding checks, but they are not reported as the causal terminal
errors of the authorized launcher attempts. A nonzero launcher return is
retained with raw stderr and command records in every refused case directory.

This result demonstrates the bounded launcher's fail-closed use of the declared
pre-execution relation. It does not establish that arbitrary hostile code is
sandboxed: unsupported source is refused rather than executed.

## 8. Work procedure and package verification

The exact execution procedure is part of the artifact at:

```text
protocol/EXECUTION_PROTOCOL.md
protocol/run_pdsm02_scratch_pilot.py
```

After checksum verification and safe extraction, the read-only package verifier
can be run from the extracted package root:

```sh
python3 -I -S -B protocol/verify_package.py .
```

Expected result:

```text
status = PASS
case_count = 24
eligible_completed = 4
blocked_before_output = 20
manifest_sha256 = 26083c5fffbfdbc4cef002db59663d6a0a262d5f36a737f8dcd4a5f20484d178
```

The verifier checks the closed manifest, exact implementation Git blobs, case
inventory, positive sink/audit semantics and absence of blocked output
directories. Re-running it produces a new verification event; the command is not
itself proof that a future invocation occurred.

## 9. Boundaries

This result establishes only a bounded local relation for the declared
MON-1-derived closed orchestration language on the recorded runtime:

```text
exact source bytes
-> source-derived model
-> independent assessment
-> exact preflight binding
-> eligible scratch execution OR pre-effect refusal
-> preserved observed result
```

It does not establish:

- general Python-program analysis;
- complete source-to-runtime fidelity outside the declared language;
- compatibility on Python versions other than the recorded CPython 3.13.5 run;
- arbitrary hostile-code containment or a physical PULSEbox result;
- production enforcement, a release gate or release eligibility;
- external or organizationally independent validation;
- physical causality or an emergence-of-time result.

No archived E1 program was executed. Existing E0, E1, MON-1 and E2 records,
release policy, gate registry, `status.json`, DOI and Software Heritage surfaces
remain unchanged. The result creates no second authority engine and has
`authority_effect: none`.
