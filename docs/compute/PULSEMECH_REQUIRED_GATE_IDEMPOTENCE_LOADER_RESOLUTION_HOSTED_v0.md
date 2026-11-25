# B2 hosted original-loader resolution observation v0

## Status and scope

This unit implements the GitHub acquisition and independent replay route for the
[bounded original-loader collector](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_v0.md)
merged in #3055. Its implementation base is
`a97e493fdca0d7d9bd4f472fe6825fe61e22f769`.
Implementation checks do not execute the original launcher, native probes or
this workflow. The [first owner-dispatched attempt](#first-hosted-attempt-455866533791)
stopped incomplete at cp0. A new actual hosted attempt remains a separate
owner-dispatched operation at the reviewed main commit containing the repair.

The selected interval remains nine unique original-loader dependency returns,
followed by original executable entry: eleven `PTRACE_CONT` calls in total and
zero continuations after entry. The existing collector owns its fresh task-guard
and two-slot qualification in the same current observer. Historical entry and
synthetic qualification records cannot replace those observations.

[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
retains its complete whole-runtime scope. A completed capture can establish the
narrow original-loader observations reconstructed by the raw checker. It does
not establish full-runtime closure, selected bootstrap execution, physical
execution authentication, future-host admission, B2 completion, Q2/Q3 results
or release authority. The hosted boundary remains conservative:
`b2_complete=false`, `metric_pass=null`, `authority_effect=none`.

## Implementation inventory

| Component | Responsibility |
| --- | --- |
| [Manual workflow](../../.github/workflows/required_gate_idempotence_loader_resolution_v0.yml) | Owner/source/policy selection, separate acquisition and verification jobs, preserved failure prefixes and completion-only attestation |
| [Host controller](../../tools/required_gate_idempotence_loader_resolution_hosted_v0.py) | Exact source snapshots, bounded input transport, offline builds, restricted owned containers and cleanup |
| [Independent hosted checker](../../tools/check_required_gate_idempotence_loader_resolution_hosted_v0.py) | Closed context, commands, sources, raw-byte/report joins, artifact handoff, receipts and verified statement |
| [Environment selection](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/environment.json) | Exact base, Python, GPG, OpenSSL, package and original-object bytes |
| [Dockerfile](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/Dockerfile), [lock](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/requirements.lock), [builder](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/build_environment.py) | Offline environment reconstruction and checked build record |
| [Container runner](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/run.py) | One observer subprocess or two separate data-only checker processes |
| [Hosted schema](../../schemas/required_gate_idempotence_loader_resolution_hosted_v0.schema.json) | Closed hosted controls and finite source/material/evidence vocabulary |

Regressions extend the already registered
[containment test module](../../tests/test_required_gate_idempotence_containment_v0.py).
The workflow has an explicit exact-byte `audit_preservation` classification in
the [normative inventory](../../scripts/build_normative_shadow_inventory_v0.py),
with [classification regressions](../../tests/test_build_normative_shadow_inventory_v0.py).
It is not a required gate or release path. Existing workflow profiles, original
collectors, historical records and CI test manifests retain their contracts.

## Closed dispatch selection

The workflow is named **PULSEmech original loader resolution observation v0**
and accepts only `workflow_dispatch`. Both jobs require repository
`HKati/pulse-release-gates-0.1`, repository ID `1061766508`, actor and triggering
actor `HKati`, ref `refs/heads/main`, positive run identifiers and attempt one.
The exact new workflow path and source commit must agree with GitHub's context.

| Required input | Selection |
| --- | --- |
| `expected_source_commit` | The actual reviewed 40-character lowercase main SHA containing this workflow; equal to `GITHUB_SHA` and `GITHUB_WORKFLOW_SHA` |
| `accepted_policy_sha256` | `1b1e4f414ffa7e56a8494f8a6d6051594c800cae978fa90585c4a02041bed953` |
| `acknowledgement` | `OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY` |

The policy input has no default. It is an explicit selection of the
[scoped rebuild acceptance policy](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_REBUILD_ACCEPTANCE_v0.md),
including that policy's current-service endorsement and unsigned
source-association assumptions, truncated public log and unresolved historical
authority. A policy digest in a saved request, capture or report is insufficient.
The trusted dispatch context carries the selection through the container
environment, request checks, both replay commands and final attested binding.

The hosted `request_id` is the first 32 hexadecimal characters of the SHA-256
of the canonical profile and full validated context. It becomes the raw
request's `attempt_id`. Changing the source, run, policy or context therefore
cannot reuse another attempt's record. No future run, container, image,
artifact or capture digest is predicted by this implementation.

A later approved execution uses a new **Run workflow** dispatch. **Re-run jobs**
does not satisfy the attempt-one contract. The concurrency group does not
cancel an active observation in favor of another dispatch.

## Complete offline inputs and selected environment

The collector's 58 request-source entries are part of a larger offline
admission dependency set. The hosted source roster explicitly selects 153
repository paths, including the 143 paths read by complete default admission,
the new hosted implementation and its standard-library transport dependency.
It includes original archives and split source/package carriers, preserved
historical source checks, schemas, plans, policy records and original signature
inputs. Dependencies are selected before execution, not discovered from its
output. Large carriers have individual finite bounds.

Before downloading or building, the controller checks HEAD and every selected
file's Git blob identity against the supplied reviewed commit. It preserves the
exact source descriptors and bytes, then repeats identity checks after work.
Only this selected copy is mounted at `/repo`; a successful check never replaces
the initial source selection with a later one.

| Runtime selection | Exact binding |
| --- | --- |
| Base manifest | `docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761` |
| Base config | `sha256:274d131132dbdc6058ed77088525d77adaf0749a6d99f2cf7d42feb9a10737c8` |
| Python | `/usr/local/bin/python3.11`, version `3.11.16`, 14,472 bytes, SHA-256 `92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79` |
| GPG | `/usr/bin/gpg`, 1,230,080 bytes, SHA-256 `7c9d2f9416aabcd10199e2984439f49612644a948279ac56bdf70d69c8958ddf` |
| OpenSSL | `/usr/bin/openssl`, 1,103,304 bytes, SHA-256 `f4aa15f2822f670af7b5c1043d7aa6ebbbc64229fd2fae382edfc6a4524749c1` |

The fixed base already contains the selected OpenSSL executable and runtime
libraries. Its compressed OCI layers were inspected as data against their
selected lengths and hashes during implementation. This is byte provenance,
not runtime qualification. The new environment explicitly selects twelve
runtime files, seven Debian overlay packages, seven Python wheels and six
original native objects. Every URL, length and hash is in the environment file.
The hash-required Python lock includes PyYAML needed by the original admission
closure. Verification uses only the preserved bytes.

The original loader and libc must already match. The inherited, separately
selected `libpcre2` restoration accepts only its exact known base bytes and
replaces them with the exact original bytes while preserving the selected
SONAME link and terminal path. Other unknown native conflicts fail. The
launcher remains build data; no build step executes it.

Both builds use the selected local base tag, `--pull=false`, `--no-cache` and
`--network none`. The builder checks the complete materials before mutation,
installs the fixed `.deb` and wheel sets offline, checks selected file and
package identities, and runs positive and negative Ed25519 known-answer tests.
Fresh original GPG verification and rebuild acceptance, including their own
OpenSSL checks, still run in the unchanged admission code before native probes.
The build record is not an admission result.

Acquisition preserves the base image archive, all twenty package/wheel/native
materials and five configuration files. Independent verification loads that
base archive and reconstructs its image offline without a replacement registry
or package-download path. Actual acquisition and verification image IDs are
recorded separately; reproducible image IDs are not claimed.

## Acquisition, replay and cleanup

| Phase | Execution | Required evidence |
| --- | --- | --- |
| Acquisition host | Build the selected environment and create one restricted, labelled container | Source/Git/material bindings, fixed command records and actual inspections |
| Acquisition container | Supervise one PID-greater-than-one observer; invoke the existing adapter once; run two separate native raw checkers | Request, complete raw capture, two equal canonical reports and build record |
| Verification host | Check the exact current-run artifact and receipt; privately copy preserved bytes; rebuild offline | Artifact metadata, source and material identity, fresh container policy |
| Verification container | Run two separate data-only raw checkers against the preserved request and capture | Two reports equal to each other and both acquisition reports |
| Hosted completion | Reconstruct both phases and owned cleanup, then create and attest `verified-binding.json` | Bound original evidence, four report bindings and verified GitHub attestation bundle |

The PID 1 entrypoint supervises exactly one `run.py observe` worker. The worker
constructs its current-observer request and calls the unchanged `run-owner`
adapter in the same process. Only the collector may perform the fresh native
qualifications and original acquisition. The verification path imports no
adapter or collector and provides no native retry or fallback.

Each raw checker independently reconstructs the original and rebuild-policy
inputs and verifies the complete capture. The hosted checker separately joins
the request, manifest, every raw file, stable admission facts, report counts and
the exact recorded checker arguments. Optional saved `verification.json` is
diagnostic custody and is never used as the replay oracle. Scripted origins,
incomplete records, differing reports, policy/source substitutions or missing
cleanup cannot produce a completed hosted statement.

The selected Docker contract is nonroot numeric runner UID:GID, readonly root,
network `none`, dropped capabilities `ALL`, no-new-privileges, default seccomp,
explicit `apparmor=docker-default`, PID limit 64, one CPU, one GiB memory and
`/tmp` mounted `rw,nosuid,nodev,size=64m`. The exact inspected environment,
entrypoint, command, labels and mount permissions must match the recorded plan.
There is no added `SYS_PTRACE` capability, unconfined policy or relaxed retry.

Owned cleanup checks the exact run/source/profile/phase labels and container ID
before force removal, then verifies absence. A failed removal or unavailable
identity is an incomplete result. The collector separately owns killing and
reaping its original child. A successful Docker command alone is insufficient
for completed evidence.

The unchanged original observation limit remains 15 seconds plus its 2-second
cleanup interval. The hosted observer command has a finite 240-second budget
for admission, qualifications, acquisition and adapter verification; each of
the two fresh checker commands has 180 seconds. Host commands share the
1200-second stage deadline, with bounded cleanup after failure. These outer
budgets do not enlarge the original trace interval or continuation allowance.

## Preservation and attestation

A private workflow prefix is created before checkout. Once its directory
exists, the upload guard is published even if writing the prefix later fails.
The available acquisition prefix is finalized as completed or incomplete and
uploaded without overwrite, including hidden files, with 90-day retention.
The closed hosted limit is 1024 files and 768 MiB, excluding the separately
bounded one-MiB receipt. Individual files retain tighter role-specific limits.
The raw collector's 512-file and 64-MiB limits remain unchanged.

The verification job consumes the exact acquisition artifact ID, GitHub digest
and externally handed-off receipt digest. Download digest mismatch is an error.
It checks artifact metadata against the same repository, run and source before
reconstruction. An incomplete acquisition can retain useful diagnostic custody,
but preservation itself never becomes capture acceptance.

Only the completed independent verified binding is an attestation subject.
The original bundle and signature-verification output are preserved and tied
to this workflow, main ref and exact source commit. Hosted attestation
authenticates the statement and its selected GitHub identity; it cannot turn
self-reported process records into externally authenticated physical execution.

## Implementation verification and next boundary

The implementation regressions exercise closed dispatch guards and actual
prefix publication; exact workflow classification; the full source and material
rosters; standard-library host imports; selected environment and crypto checks;
single adapter invocation; separate data-only replay; report/policy/raw-byte
joins; bounded custody; and owned cleanup failures. Scripted collector fixtures
remain explicitly scripted. Public GPG/OpenSSL signature tests are separate
from native acquisition tests and do not qualify the host.

After review, PR CI and merge, select the actual resulting main SHA and review
the policy and acknowledgement together before an owner dispatch. Assess both
jobs, raw artifacts, all four checker reports, cleanup and attestation before
preserving any completed result. A green implementation PR or uploaded artifact
alone does not finish original acquisition or close #2879.

## First hosted attempt: 45586653379/1

Owner-dispatched [run 45586653379, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45586653379)
used source `fbcc8ccfadbc317ece1aeacb4c0eff50d0fcfe59`. The owner, source,
acknowledgement and selected-policy guards passed. Acquisition produced an
incomplete native-profile record at the first exec-stop checkpoint, with
`loader_resolution_checkpoint_changed`, one continuation and no accepted
dependency returns. No terminal executable-entry checkpoint was obtained.

The two cp0 process samples differed only in resident-memory accounting:

| Field | Before | After |
| --- | ---: | ---: |
| `stat` field 24 (`rss`, pages) | 0 | 40 |
| `status` `VmHWM` (`kB`) | 12 | 212 |
| `status` `VmRSS` (`kB`) | 12 | 212 |
| `status` `RssFile` (`kB`) | 0 | 160 |
| `status` `RssShmem` (`kB`) | 0 | 40 |

Registers, maps, auxv, stack samples and the paired original executable-memory
samples were byte-identical. The collector read 39,761 page-aligned bytes from
the sealed-memfd launcher and 160,721 page-aligned bytes from the file-backed
loader. At 4 KiB per page, those ranges cover 40 KiB and 160 KiB respectively,
matching the resident-accounting increases. This supports the explanation that
observer reads faulted those pages in; it is not external authentication of the
specific kernel's execution. The upstream [proc-memory read path](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/master/fs/proc/base.c)
uses remote-memory access, whose [page-acquisition contract](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux.git/+/7b9acbb6aad4f54623dcd4bd4b1a60fe0c727b09/mm/gup.c)
allows pages to be faulted in. Linux also documents asynchronous RSS accounting.

The acquisition container's retained cleanup record reports verified ownership,
successful removal and verified absence. The verification job checked the
exact acquisition artifact, receipt and all 320 receipt-bound files, then
stopped on the incomplete prefix. Attestation was skipped. This is preserved
diagnostic custody, not completed original-loader reconstruction.

| Original artifact | ID | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Acquisition | `15008174005` | 220025688 | `0403474d2419084fba6133c17140cf190d5b8acc923cf3587d43467f34d29127` |
| Verification | `15009441127` | 6774 | `50188b1baab6f41d109cff7140690cdbb5dcac03745d5cab8cdd25e041e43933` |

The acquisition receipt SHA-256 is
`a1fb3e81c6f3911c3c771a907e70acd83b88a0cd9dd8490606e6e73b87ee71cf`.
Four unchanged cp0 process samples and their exact artifact/source provenance
are retained as [regression inputs](../../tests/fixtures/loader_resolution_proc_residency_45586653379_v0/provenance.json).
That small test fixture is explicitly not a complete capture or a replacement
for the original artifacts. The original incomplete record is not rewritten or
promoted by the [native process-pair correction](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_v0.md#process-identity-and-resident-memory-accounting).
A fresh owner dispatch after repair review, CI and merge is still required.
