# Fixed idempotence entry build acquisition and provenance v0

## Status and scope

**Implemented: two fixed builds of the repository-owned containment entry,
preserved build records, independent offline checking, and a manual GitHub
provenance workflow. B2 remains incomplete.**

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

An uploaded bundle is not itself a successful verification result. A future run
must be reviewed using its exact source commit, run/attempt, artifact IDs, original
bundle and verifier exit/output. The final evidence remains outside this
implementation package until that run actually exists. Signed build provenance
authenticates the checked workflow identity and subject binding; it does not
prove compiler correctness, source/binary semantic equivalence or host fitness.

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

Remaining B2 work includes an actual reviewed hosted provenance run, launcher
provenance and host qualification, a bounded contained example, independently
bound runtime/loader observations and reviewed selected-bootstrap integration.
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
