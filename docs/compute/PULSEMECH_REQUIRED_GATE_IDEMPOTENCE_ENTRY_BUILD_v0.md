# Fixed idempotence entry build acquisition and provenance v0

## Status and scope

**Implemented: two fixed builds of the repository-owned containment entry,
preserved build records, independent offline checking, and a manual GitHub
provenance workflow. The first hosted build/provenance observation,
`43854478248/1`, completed and is preserved below. B2 remains incomplete.**

This continuation supplies a reviewable build path for the static entry used by
the [containment primitives](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_v0.md).
It compiles the unchanged C source twice in separate private directories and
requires identical binary bytes. It never executes either resulting binary,
the selected runtime, the sanitizer, a model or an actual reference.

The two builds share one host and observed toolchain. Their equality establishes
the recorded repeat-build result for this finite recipe. It does not establish
agreement between independent builders, complete compiler closure, semantic
equivalence between source and binary, or qualification of the launch host.

| Component | Responsibility |
| --- | --- |
| [Acquisition tool](../../tools/required_gate_idempotence_entry_build_v0.py) | Check the selected source and compiler, perform the two bounded builds, and preserve their bytes and observations. |
| [Independent checker](../../tools/check_required_gate_idempotence_entry_build_v0.py) | Recheck the closed evidence roster, external digests, fixed request and each build's raw bindings without executing a process. |
| [Request schema](../../schemas/required_gate_idempotence_entry_build_v0.schema.json) | Describe the closed source, compiler, recipe, limits, context and authority boundary. |
| [Manual workflow](../../.github/workflows/required_gate_idempotence_entry_build_v0.yml) | Build with read-only repository permissions, then independently check, attest and verify the record in a separate job. |
| [Regressions](../../tests/test_required_gate_idempotence_entry_build_v0.py) | Exercise independent records, substitutions, filesystem failures, bounded subprocess plumbing and workflow restrictions. |

The schema is pinned by SHA-256 in the checker. The existing containment,
bootstrap, runtime, acquisition, observation and B1 implementations and schemas
retain their bytes. Existing execution workflows retain their bytes. Repository
hygiene admits the exact Python patch only for the new workflow's `build` and
`attest` setup steps; the new workflow has only a manual trigger.

## Fixed source and recipe

The source is
`tools/required_gate_idempotence_containment_entry_v0.c`: 4,598 bytes, SHA-256
`0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f`.
Acquisition requires a full source commit, the checkout's `HEAD` at that commit,
and agreement between its Git blob, the checkout source and the installed
tool's pinned source. The source and checkout are checked again after building.

The caller selects an absolute compiler path and retains its SHA-256 separately.
The tool resolves the path and checks an ordinary executable ELF64 little-endian
x86-64 file before invoking it. It does not install a compiler, discover an
alternative compiler on failure or accept caller-provided build flags.

Both fresh build directories contain the same `entry.c` bytes and use exactly:

```text
SELECTED_COMPILER -v -std=c11 -O2 -Wall -Wextra -Werror
  -ffreestanding -fno-builtin -fno-pie -fno-stack-protector
  -fno-asynchronous-unwind-tables -fno-unwind-tables
  -nostdlib -static -no-pie -Wl,--build-id=none -Wl,-z,noexecstack
  entry.c -o entry
```

The environment is exactly `PATH=/usr/bin:/bin`, `LC_ALL=C`, `TZ=UTC`,
`SOURCE_DATE_EPOCH=0` and `TMPDIR=.`. Compiler stdout must be empty for an accepted
build. Raw stderr preserves the verbose stage commands emitted by GCC's `-v`
option. The same relative input and output names avoid varying the recipe with
the two private directory names; the compiler still runs on an unqualified host.

Before and after the builds, the producer preserves the compiler's `--version`
output and its `-print-prog-name` queries for `as`, `cc1`, `collect2` and `ld`.
Each of those tools, and the compiler itself, has a recorded lookup path,
resolved path, SHA-256 and size. The producer requires stable observed identities
and bytes across the before/after observations and rechecks all components after
the final query in each phase. A path or hash observation does not authenticate
which process image actually executed or cover all compiler inputs, libraries,
specifications and host services.

## Bounds and failure preservation

| Resource | Fixed bound |
| --- | --- |
| Build executions | Exactly two; no automatic retry. |
| Each build process | 30 seconds. |
| Each compiler query | 10 seconds. |
| Retained stdout per process | 65,536 bytes. |
| Retained stderr per process | 262,144 bytes. |
| Each resulting entry | 16 MiB. |
| Each observed compiler/tool file | 128 MiB. |
| Each JSON control file | 1 MiB. |

The output directory must be new, private and outside the selected checkout.
Builds use owned directory descriptors for their working directories. Input
copies and raw output pass through the preservation sink; an append must succeed
before its bytes count as captured. The produced entry is checked and synced
before adoption into the evidence set.

Each compiler process starts in its own session and process group. The parent
observes leader exit without reaping it, stops the still-owned group, and then
performs a bounded reap. A leader that closes its output pipes and exits cannot
leave a same-group descendant running merely because its own return code is
already available. This process management is not a compiler sandbox or a claim
that descendants cannot leave the group.

After an overflow, deadline or process failure, both pipes are drained
nonblockingly through the same sink up to their separate remaining caps. A drain
stops at EOF, would-block or the cap. It neither waits for future output nor
retries the build. A sink failure is not retried during cleanup.

The first failed build prevents the second build. Failed attempts keep their
existing raw prefixes and write `attempt.incomplete.json` when possible. A
partial append, failed drain, changed source, substituted file, unequal binary
or changed toolchain observation cannot produce an accepted completed record.

Successful compiler-query output is first retained in raw temporary files, then
embedded losslessly as canonical base64 in the corresponding toolchain JSON.
Those temporary files are removed only after the enclosing JSON has been saved
and rechecked. A failure before incorporation retains the raw files. This
consolidation is limited to successfully preserved query output.

The producer checks every retained file's identity and bytes, the directory
identities and exact inventory before publishing `record.json`. Publication uses
a synced pending file and a no-overwrite link. A publication failure retains an
incomplete prefix; an extra pending file or incomplete marker is rejected by the
offline checker's closed roster.

## Preserved evidence and independent checking

One successful acquisition has exactly these fifteen files:

| File | Retained content |
| --- | --- |
| `request.json` | Canonical fixed request, external source commit, selected compiler, context and false authority fields. |
| `source.c` | Exact pinned source bytes. |
| `toolchain-before.json`, `toolchain-after.json` | Tool identities, raw query/version output and bounded process observations. |
| `build-1/entry.c`, `build-2/entry.c` | Separate exact source copies consumed by the two builds. |
| `build-1/entry`, `build-2/entry` | Both complete binary byte strings. |
| `build-1/stdout.bin`, `build-2/stdout.bin` | Raw compiler stdout. |
| `build-1/stderr.bin`, `build-2/stderr.bin` | Raw compiler stderr. |
| `build-1/result.json`, `build-2/result.json` | Separate commands, environments, process observations and source/output/binary bindings. |
| `record.json` | Canonical completed record binding the other fourteen files. |

The checker requires independently supplied source-commit, request-digest and
record-digest values. Every occurrence is checked separately: one correctly
bound build cannot compensate for the other build consuming different source
bytes, reporting a different command or binding unrelated output. Both entries
must pass the existing static ELF shape checks and have identical raw bytes.

JSON must be canonical and have the exact expected fields and types. Duplicate
keys, nonfinite values, floating-point substitutions, excessive nesting,
out-of-range integers and authority-field changes are rejected. The checker
recomputes the manifest hashes and byte counts from the preserved files and
compares before/after toolchain observations independently of process timings.

The filesystem reader pins directories and files with non-following descriptors,
requires ordinary files with one link, checks stable metadata and the exact
inventory, and bounds every read. It rejects symlinks, hard links, special files,
unexpected entries and replaced paths. It permits ordinary permission-bit
normalization by GitHub artifact transport; acquisition's private creation modes
are not treated as transported evidence of isolation.

The checker performs no compiler, entry, selected-runtime, network or GitHub
execution. Its acceptance means the finite record is internally consistent with
the fixed contract and externally retained digests. It does not authenticate the
producer's process observations or a caller-authored GitHub context.

## Local commands

Use a Linux x86-64 host, the repository's Python dependencies, a separately
selected compiler and a new output path. The capitalized arguments below are
placeholders for previously retained exact values:

```bash
python tools/required_gate_idempotence_entry_build_v0.py acquire \
  --repository-root /absolute/path/to/checkout \
  --source-commit FULL_HEX40_SOURCE_COMMIT \
  --compiler /absolute/resolved/compiler \
  --compiler-sha256 RETAINED_COMPILER_SHA256 \
  --output-directory /absolute/path/to/new-entry-build

python tools/check_required_gate_idempotence_entry_build_v0.py \
  --evidence-dir /absolute/path/to/new-entry-build \
  --source-commit FULL_HEX40_SOURCE_COMMIT \
  --request-sha256 RETAINED_REQUEST_SHA256 \
  --record-sha256 RETAINED_RECORD_SHA256 \
  --output /absolute/path/to/new-verification.json
```

Verification output must be a new path outside the evidence directory. Commands
emit machine-readable JSON and return nonzero on rejection. A local example
uses `context.kind=local_example`; `--github` requires the exact workflow context
instead of silently upgrading a local observation.

## Manual hosted provenance path

The workflow is an implemented path for a later explicitly requested run. Adding
or merging it does not dispatch it or create a verified GitHub attestation.
Its two required dispatch inputs are:

- `expected_source_commit`: the full reviewed commit on `main`.
- `acknowledgement`: exactly `BUILD_ENTRY_ONLY_NO_RUNTIME_EXECUTION`.

Both jobs guard the fixed repository name and ID, owner/triggering actor `HKati`,
`refs/heads/main`, `workflow_dispatch`, attempt 1, and matching source/workflow
commit identities. Actions are pinned by full commit SHA. Python is selected as
3.11.16 and the existing hash-locked attestation requirements file is checked
against its pinned digest before installation.

The shared repository-hygiene guard requires the exact workflow path and exactly
one `actions/setup-python` step in each of `build` and `attest`, both pinned to
`3.11.16`. Every ordinary job retains the core `3.11` rule. Missing or renamed
jobs, missing or duplicate setup steps, broader version selectors and patch
drift reject. Existing synthetic guard environments include the newly required
workflow so their positive and negative controls continue to test their intended
rules. The entry-build regressions execute the actual shared guard as well.

The [normative/shadow inventory](../../scripts/build_normative_shadow_inventory_v0.py)
classifies only the exact reviewed workflow path and bytes as build-evidence
preservation. Its `attestation_participation=true` describes the workflow's
signing role; `required_gate_participation=false`,
`release_path_participation=false` and `authority_effect=none` retain the
non-authorizing boundary. This classification is not a record that the workflow
has run or that a signature has been verified. Changed bytes or an alternate
workflow path require a new explicit classification review.

The **build job** has only `contents: read`. It records the context, selects and
hashes the installed GCC, runs the finite acquisition, independently checks the
result, and exposes the exact upload artifact ID plus request and record digests.
Its artifact upload runs even on failure so partial diagnostics remain available.
The artifact name is
`required-gate-idempotence-entry-build-RUN_ID-RUN_ATTEMPT`.

The separate **attest job** has the GitHub identity and attestation permissions.
It downloads that exact current-run artifact ID into a fresh directory, requires
the transport digest check to succeed, rechecks all fifteen evidence files, and
compares the request context with the live workflow context. It then attests
`evidence/record.json`, whose closed manifest binds both binaries and all raw
evidence. The compiler receives no attestation token from this job.

The signer preserves the original attestation bundle bytes and an identity file
binding the source/workflow commit, run/attempt, original build artifact ID,
request, record and bundle digests. It runs `gh attestation verify` against that
bundle with the fixed repository and signer workflow, source/workflow digests,
source ref, SLSA provenance predicate, GitHub OIDC issuer and denial of self-hosted
runners. Verification has a 120-second timeout and bounded log files; its raw
stdout, stderr and exit code are preserved. The final artifact upload also runs
on failure, with name
`required-gate-idempotence-entry-attestation-RUN_ID-RUN_ATTEMPT`.

An uploaded bundle is not itself a successful verification result. Every run
must be reviewed using its exact source commit, run/attempt, artifact IDs, original
bundle and verifier exit/output. The first completed hosted observation is
recorded in the next section, separately from the implementation and its original
offline records. Signed build provenance authenticates the checked workflow
identity and subject binding; it does not prove compiler correctness,
source/binary semantic equivalence or host fitness.

## Completed hosted observation — 43854478248/1

**Completed bounded operational record.** The owner-dispatched
[first hosted run](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/43854478248)
completed successfully on 2026-11-16. It acquired two actual fixed-source builds,
checked their original evidence in separate build and signing jobs, and completed
the hosted signature verification. The unchanged artifacts and their
[preservation inventory](../../preservation/required_gate_idempotence_entry_build_v0/run_43854478248_attempt_1/verification_record_v0.json)
retain the evidence for this observation. The later inventory describes those
results; it is not another independent checker report or an execution permit.

### Run, source and artifact identities

| Identity | Recorded value |
| --- | --- |
| Repository / repository ID | `HKati/pulse-release-gates-0.1` / `1061766508` |
| Run / number / attempt | `43854478248` / `1` / `1` |
| Event / ref | `workflow_dispatch` / `refs/heads/main` |
| Actor / triggering actor | `HKati` / `HKati` |
| Source commit and workflow SHA | `f290aee20cd610e4fdb358dbf34d054ec351d390` |
| Source tree | `30b4e7d11f95f88b0b95e7b04b9ad29a9d95a381` |
| Workflow path | `.github/workflows/required_gate_idempotence_entry_build_v0.yml` |
| Build job | [133255107740](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/43854478248/job/133255107740), successful |
| Signing and verification job | [133255324365](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/43854478248/job/133255324365), successful |
| Run creation / terminal update | `2026-11-16T11:04:28Z` / `2026-11-16T11:05:33Z` |
| Acknowledgement required by the executed workflow | `BUILD_ENTRY_ONLY_NO_RUNTIME_EXECUTION` |

The following source bytes belong to that exact hosted commit. A later commit
which adds this observation does not become the source of the historical build.

| Source object | Bytes | SHA-256 |
| --- | ---: | --- |
| Fixed entry C source | 4598 | `0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f` |
| Acquisition tool | 30687 | `557940d01a67f8bb2023b22b21121be9ac965995ce0ddfbabf6bf09ec9e2311c` |
| Independent checker | 22242 | `6a452044251bdcd6551bb653f1472eabbc213b3d0f5560494b0046668a325900` |
| Request schema | 8499 | `ff382fe396ef01309db95ad129b30b6ec4c4dc8d4460d54448637c9cdac6d6af` |
| Manual workflow | 21140 | `53a2c0ce99355899cf9296ce7c8a3cd932ae436e825665789fca7e13f1a47be6` |
| Hosted dependency lock | 898 | `dfea85090305c5dd7ea5b3f829cbb450621087d4b07179019a285a7d41badb28` |

| Preserved original ZIP | Artifact ID | Members | Bytes | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| [Build artifact](../../preservation/required_gate_idempotence_entry_build_v0/run_43854478248_attempt_1/required-gate-idempotence-entry-build-43854478248-1.zip) | `14221130752` | 20 | 64298 | `1ad3f84009ff7446e204ab18cb61bd5494a6d1182878833de017a438a3f36855` |
| [Attestation artifact](../../preservation/required_gate_idempotence_entry_build_v0/run_43854478248_attempt_1/required-gate-idempotence-entry-attestation-43854478248-1.zip) | `14220256431` | 27 | 93740 | `04bc923532e4ed8f3e2b564704fe6687619915c4a4fea45724af99473dfcb788` |

Both downloaded ZIPs match their separately retrieved GitHub API digests and byte
counts. They are preserved without recompression or repackaging. The API reports
90-day Actions retention ending at `2027-02-14T11:04:30Z`; these exact repository
copies retain the original evidence beyond that hosted retention period. The
API metadata is a separately retrieved description, not an independent signature
over this later documentation inventory.

### Observed build and handoff relationships

The build artifact contains the closed fifteen-file `evidence/` directory and
the original acquisition, compiler-selection, workflow-start and checker
records. The attestation artifact retains all twenty build-artifact files under
`input/`, with byte-identical contents, alongside the signing and verification
records. Its `original-build-artifact-id.txt` and `attestation-identity.json`
agree with the original build artifact ID `14221130752`.

| Evidence object | Bytes | SHA-256 |
| --- | ---: | --- |
| `evidence/request.json` | 2268 | `e2a2df9acf7d63574396e3ccb9851c2bad9a22d177b38ab95f3f99228d388fe2` |
| `evidence/record.json` | 2922 | `330246bc2edea58dfdd5e22de33d6bca8df702cfc38391136b4ed93738739583` |
| Each hosted `build-1/entry` and `build-2/entry` | 9568 | `7a21b2e4d60dc080149d9a919b604e39f6fb29be42d462e979b46d3c439b95ab` |
| Each original hosted checker report | 1407 | `f968bdca9544265843e3cd0b29953e24998dfe88453ed6bce9c699146f2a1f06` |
| Original `attestation.bundle.json` | 11334 | `f0ebc390b9996d2ff9d5e27fa546c76e45dbad78513a0317ca3597b6fcd28e97` |
| Original `verification.stdout.json` | 14591 | `c6d2e0f9d897f032f5d0ddab742619f938743651a6fbbdf7f1deb5ac9875d629` |

Both hosted checker executions accepted the evidence. Each separately validates
the source, command, environment, process and raw output bindings for both build
occurrences. Their canonical reports are byte-identical and record
`entry_build_record_verified=true`, `repeat_build_equal=true`,
`entry_static_shape_verified=true` and `toolchain_observations_stable=true`.
They are two executions of the same independent checker implementation in
separate jobs.

The selected compiler was `/usr/bin/x86_64-linux-gnu-gcc-13`, reporting
`13.3.0` from Ubuntu package `13.3.0-6ubuntu2~24.04.1`; its preserved identity is
1023032 bytes, SHA-256
`1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26`.
The two 9568-byte binaries are equal to each other under this recorded hosted
recipe and toolchain. This observation makes no equality claim about binaries
built with a different toolchain or host.

### Hosted signature verification and later local replay

Attestation `68081318` binds the closed build record. The preserved original
bundle and identity agree on the source/workflow commit, run/attempt, original
build artifact, request and record digests. The actual hosted
`gh attestation verify` step returned `0`, preserved as `0` followed by LF in
`verification.exit-code.txt`, with empty `verification.stderr.bin`. Its JSON
output retains the verified subject and provenance. The command required the
fixed repository and signer workflow, exact source and workflow digests,
`refs/heads/main`, the GitHub OIDC issuer, the SLSA provenance v1 predicate and
denial of self-hosted runners.

Later local checking used the unchanged checker from
`f290aee20cd610e4fdb358dbf34d054ec351d390`, once against each separately extracted
original artifact's evidence. Both fresh processes returned `0` with empty
stderr and accepted reports. Each reproduced all 1407 bytes of both original
hosted reports. These two later processes and the two hosted processes use the
same checker; they are not four independent implementations. The local replay
read preserved bytes and did not compile or execute an entry, selected runtime,
original operator or model.

Local checking used CPython `3.11.16`, jsonschema `4.26.0`, PyYAML `6.0.3` and
jsonschema-specifications `2025.9.1`. Local `rpds-py` was `2026.9.1`; the unchanged
hosted lock selects `2026.6.3`. The matching source-bound reports are results for
these actual executions; they do not claim an identical hosted dependency
environment. Fresh local cryptographic signature verification was not performed.
The retained successful signature verification is the original hosted execution,
whose command, exit code and output are preserved separately from the later
offline record checks.

For an offline record replay, use a separate clean checkout at the exact hosted
source commit and extract the unchanged ZIPs into separate fresh directories.
From that source checkout, run the checker with these external identity pins;
each output path must be new and outside its evidence directory:

```bash
python3 -I -B tools/check_required_gate_idempotence_entry_build_v0.py \
  --evidence-dir /absolute/path/to/extracted-build/evidence \
  --source-commit f290aee20cd610e4fdb358dbf34d054ec351d390 \
  --request-sha256 e2a2df9acf7d63574396e3ccb9851c2bad9a22d177b38ab95f3f99228d388fe2 \
  --record-sha256 330246bc2edea58dfdd5e22de33d6bca8df702cfc38391136b4ed93738739583 \
  --output /absolute/path/to/new-build-record-check.json

python3 -I -B tools/check_required_gate_idempotence_entry_build_v0.py \
  --evidence-dir /absolute/path/to/extracted-attestation/input/evidence \
  --source-commit f290aee20cd610e4fdb358dbf34d054ec351d390 \
  --request-sha256 e2a2df9acf7d63574396e3ccb9851c2bad9a22d177b38ab95f3f99228d388fe2 \
  --record-sha256 330246bc2edea58dfdd5e22de33d6bca8df702cfc38391136b4ed93738739583 \
  --output /absolute/path/to/new-attestation-record-check.json
```

These commands reproduce the offline record checks. They do not repeat the
hosted build or the cryptographic signature verification.

### Preserved claim boundary

This observation establishes the recorded relationship among the exact source,
two hosted builds, their original byte evidence, independent record checks and
the separately verified hosted attestation. The build and checker records retain
their original `github_build_provenance_verified=false` field: the later signing
result is a separate event, not an edit to those earlier offline records.

No produced entry, selected runtime, original operator or actual reference was
executed by this workflow or the later replay. Compiler closure, source/binary
semantic equivalence, authenticated toolchain execution, launcher/host
qualification and selected-bootstrap integration remain separate obligations.
The preservation inventory grants no execution readiness, metric PASS or release
authority. B2 remains incomplete; the original `43514702328/1` evidence, Q2 FAIL
49/50 plus 1 UNKNOWN, all twelve unsupported gates and historical Q3 scope retain
their recorded meanings. Issue #2879 stays open.

## Validation and remaining work

The new regression module is registered once in Tools. Live entries rise from
188 to 189, with all current count consumers coordinated; targeted pytest remains
40. Tests use independently authored records, finite real source compilation and
authored process helpers. Produced entry binaries are never executed by these
tests. No test assumes bubblewrap is installed or that host namespaces work.

Successful checking sets only the finite record, repeat-build, static-shape and
stable-observation results. It keeps `entry_binary_executed`,
`compiler_closure_verified`, `source_binary_equivalence_verified`,
`toolchain_execution_authenticated`, `github_build_provenance_verified` and
`host_launcher_runtime_verified` false. The offline record is not rewritten after
a later signature verification; that verification has its own preserved result.

All inherited execution, bootstrap, runtime, containment, qualification and
production-eligibility flags stay false; `metric_pass=null`,
`actual_reference_claimed=false` and `authority_effect=none`. The selected
bootstrap route remains closed.

The first reviewed hosted provenance observation is preserved above. Remaining
B2 work includes launcher provenance and host qualification, a bounded contained
example, independently bound runtime/loader observations and reviewed
selected-bootstrap integration.
Actual reference execution still requires separate owner authorization. B3, B4
and B5 remain subsequent work. Preserve the original `43514702328/1` artifact,
Q2 FAIL 49/50 plus 1 UNKNOWN, all twelve unsupported gates and historical Q3
scope; keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
open.

## Primary implementation references

- [GCC overall options](https://gcc.gnu.org/onlinedocs/gcc/Overall-Options.html): `-v` emits the commands for the compilation stages while executing them.
- [Reproducible Builds definition](https://reproducible-builds.org/docs/definition/): repeatability is relative to specified source, build environment and instructions.
- [GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations): signed provenance and its verification have a narrower scope than software correctness or security.
- [GitHub CLI attestation verification](https://cli.github.com/manual/gh_attestation_verify): bundle, signer, source, issuer and runner restrictions used by the manual workflow.
