# PD-SM-01-E2 compatibility execution result v0

Classification: **Completed operational record**.  
Profile: `PD-SM-01-E2-compat-v0`.  
Recorded matrix status: `MATCH`.  
Scope: E0 cases and controls on the four named CPython interpreters on Linux x86_64.  
`authority_effect: none`.

## Execution and source identities

| Record | Inspected value |
| --- | --- |
| Repository | `HKati/pulse-release-gates-0.1` |
| Hosted run | [40113600844](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/40113600844) |
| Run attempt | `1` |
| Event | `workflow_dispatch` |
| Recorded branch | `main` / `refs/heads/main` |
| Workflow | `.github/workflows/paradox_compatibility_v0.yml` |
| Workflow commit | `d4fee2e007eb97cee652bd62cde81aef57b79b1f` |
| Immutable source commit | `102145d1f1c321811c52d9d20f92cc7289127b2b` |
| Historical semantic commit | `cbeab94d8532482d34ab857bf38e9e56ae265f84` |
| GitHub run state | `completed` / `success` |
| Recorded runner image | `ubuntu24`, image version `20261023.334.3` |

The GitHub artifact metadata binds artifact `12567154104` to this run,
`main`, and the workflow commit. The downloaded `matrix/INVOCATION.json`
also records the same repository, ref, run ID, attempt,
`GITHUB_SHA`, and `GITHUB_WORKFLOW_SHA`. `matrix/SOURCE_CHECK.json` records
the immutable source snapshot; each runtime's `execution/RESULTS.json`
records that source snapshot and the historical semantic snapshot above.
These are inspected source bindings within the preserved evidence.

## Observed interpreter matrix

The four runtime probes record `implementation = CPython`, `platform = Linux`
and `machine = x86_64`. Their observed versions match the four required
versions exactly. Each matrix row reports `execution = COMPLETED`,
`status = MATCH` and return code `0`.

| Observed CPython | Platform / machine | Matching scenarios | Successful regression methods | Included control groups | Subprocess records | Row status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `3.11.14` | Linux / x86_64 | 8 | 18 | 6 | 48 | `MATCH` |
| `3.12.12` | Linux / x86_64 | 8 | 18 | 6 | 48 | `MATCH` |
| `3.13.5` | Linux / x86_64 | 8 | 18 | 6 | 48 | `MATCH` |
| `3.14.3` | Linux / x86_64 | 8 | 18 | 6 | 48 | `MATCH` |
| **Total executions / records** | **Four runtimes** | **32** | **72** | **24** | **192** | **`MATCH`** |

The 24 control-group executions are included in the 72 regression-method
executions. Each runtime's 18 method records contain six `Controls` methods
and twelve `ReferenceRegressions` methods; all record `MATCH`, with zero
regression failures and errors. Control groups `G01` through `G06` each
record `COMPLETED` / `MATCH`.

The eight scenarios are `E00`, `E10`, `E11`, `E12`, `E13`, `E20`, `E30` and
`E40`. Each records `expected_vs_observed = MATCH`. The 48 subprocess
records per runtime include G03's deliberate signal (`PROCESS_ERROR`,
return code `-15`) and timeout (`TIMEOUT`, return code `-9`) controls.
G03 records their comparison as `INCOMPLETE` and its rejection-specificity
assertion as `MATCH`. These negative-control observations remain intact.

`matrix/MATRIX.json` records all required runtime results present,
cross-version comparison performed, and all required semantic views equal.
All four `SEMANTIC_VIEW.json` files are byte-identical, each 37135 bytes.
Their common SHA-256 is:

```text
627e2181899dd412b58e4e40f39d08ab50c107786346ccef6d123fc0989df6c5
```

## Recorded semantic distinctions

The scenario comparison matches the recorded expectations while preserving
the following distinct relation, source and proof assessments on every runtime.

| Case | `reference_relation_assessment` | `reference_source_assessment` | `proof_applicability_assessment` |
| --- | --- | --- | --- |
| `E20` | `VIOLATED` | `CONTRADICTED` | `NOT_JUSTIFIED` |
| `E30` | `SATISFIED` | `UNRESOLVED` | `NOT_JUSTIFIED` |
| `E40` | `SATISFIED` | `JUSTIFIED_WITHIN_FIXTURE_BOUNDARY` | `NEW_TARGET_PROOF_REQUIRED_AND_SEPARATELY_JUSTIFIED` |

For `E40`, reuse of the old proof records `certificate_reuse = SUBJECT_MISMATCH`.
The new subject requires, and records, separate justification. A matrix match
does not erase the `E20` violation, the unresolved `E30` source assessment,
or the old-proof subject mismatch.

## Preserved original GitHub Actions artifact

| Artifact field | Verified identity |
| --- | --- |
| Artifact ID | `12567154104` |
| Artifact name | `pd-sm-01-e2-40113600844-1` |
| Original ZIP filename | `pd-sm-01-e2-40113600844-1.zip` |
| Original ZIP size | `1334079` bytes |
| Original ZIP SHA-256 | `9cbcd1c744a2bb3b7173611b8417f6be170a4d533121e7b2e3dfcdb69c54ecee` |
| ZIP file members | `1075`, with no directory entries |
| Verified `matrix/SHA256SUMS` entries | `1067` |

Repository copies:

- [Original GitHub Actions ZIP](evidence/PD_SM_01_E2_RUN_40113600844/pd-sm-01-e2-40113600844-1.zip)
- [Adjacent SHA-256 file](evidence/PD_SM_01_E2_RUN_40113600844/pd-sm-01-e2-40113600844-1.zip.sha256)

The original artifact was downloaded using GitHub's authenticated artifact
download capability, which follows the download redirect. The repository ZIP
preserves those downloaded bytes unchanged. It is an ordinary Git blob;
no archive members are unpacked into the repository and no LFS pointer replaces it.
The adjacent checksum names this original ZIP and uses two spaces between
the digest and filename, followed by a newline.

Internal evidence locations, where `<VERSION>` is one of the four versions above:

| Internal path | Record inspected |
| --- | --- |
| `matrix/MATRIX.json` | Profile, required versions, completed rows and `MATCH` |
| `matrix/INVOCATION.json` | Controller identity and hosted run/source metadata |
| `matrix/SOURCE_CHECK.json` | Selected immutable source snapshot |
| `matrix/SHA256SUMS` | Digests covering all other files under `matrix/` |
| `matrix/py<VERSION>/ROW.json` | Per-runtime row and result/semantic digests |
| `matrix/py<VERSION>/execution/RESULTS.json` | Scenario, regression, control and subprocess counts; source bindings |
| `matrix/py<VERSION>/probe.stdout` | Observed CPython/Linux/x86_64 identity |
| `matrix/py<VERSION>/SEMANTIC_VIEW.json` | Byte-compared semantic projection |
| `matrix/py<VERSION>/execution/controls/G03.json` | Deliberate process-error and timeout controls |
| `matrix/py<VERSION>/execution/logs/**/*.json` | The 48 subprocess records per runtime, with stdout/stderr references |
| `matrix.exitcode` | Recorded matrix exit code `0` |

The preserved top-level `ACQUISITION_STATUS.txt` contains `STARTED`.
Completion is recorded by the completed GitHub run, `matrix.exitcode`,
the matrix and the four runtime results; the historical marker is unchanged.

## Evidence inspection performed for this preservation

The following checks read the downloaded records without executing any archive
member, evaluator, harness or experiment:

1. Read the existing target branch and verify starting HEAD
   `d4fee2e007eb97cee652bd62cde81aef57b79b1f`. Read the run and artifact
   metadata and verify ID, name, attempt, event, branch, workflow commit,
   successful completion, artifact size and artifact digest.
2. Compute the downloaded ZIP's byte count and SHA-256 and compare both
   with the specified original artifact identity.
3. Check all ZIP CRCs, count 1075 file members, reject unsafe or noncanonical
   member paths and symlinks, and verify exact and normalized path uniqueness.
4. Parse every `matrix/SHA256SUMS` line, verify its referenced member and
   SHA-256, reject duplicate checksum paths, and confirm coverage of all 1067
   matrix files other than the checksum file itself.
5. Parse the inspected JSON records with duplicate-key and non-finite-number
   rejection. Verify the matrix profile, `MATCH`, exact required runtime set,
   presence and equality flags, and recorded `authority_effect = none`.
6. Verify the hosted metadata in `INVOCATION.json`, the source snapshot in
   `SOURCE_CHECK.json`, and both snapshot identities in all four runtime results.
7. Read all four probes, results, rows and semantic views. Compare each probe
   with its matrix observation and verify the requested version, implementation,
   platform and machine. Compare `ROW.json` with its matrix row, verify each
   result digest, and check the recorded source/frozen-core preservation flags.
8. Count the eight matching scenarios, eighteen successful and uniquely named
   regression methods, six included successful control groups, and 48 distinct
   subprocess log records for each runtime. Verify subprocess stdout/stderr
   lengths and digests against archive members. Check the signal/timeout records
   against G03's recorded negative-control observations and comparisons.
9. Verify the `E20`, `E30` and `E40` assessments against their runtime results
   and semantic views. Compare all four semantic-view byte sequences directly,
   verify their common digest, and read `matrix.exitcode = 0`.

The preservation change adds this document, the original ZIP and its checksum,
and one index entry. Its pre-commit checks verify the exact four-path scope,
the index's single insertion, relative-link targets, and the staged ZIP and
checksum bytes. No new experiment or full smoke suite is run for this task.

## Claim boundary

This record preserves E0 fixture results on the four named CPython/Linux x86_64
interpreters. E1 and MON-1 remain separate records. It establishes no Windows,
other-platform, future-interpreter, physical-causality or general-monitoring claim.

`authority_effect: none`. No release authority, policy activation or production
gate eligibility is added. The pinned reference and producers share a
specification; this preservation is not independent organisational validation
or a signed attestation. No experiment was executed during preservation.

The separate ChatGPT archival verifier, its control tests and its wrapper
archive are outside this delivery. Only the original GitHub artifact named
above is preserved here. Historical preparation and `NOT_RUN` statements
elsewhere in the repository are retained as historical records.
