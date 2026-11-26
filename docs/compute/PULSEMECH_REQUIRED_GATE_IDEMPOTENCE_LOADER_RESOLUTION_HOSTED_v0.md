# B2 hosted original-loader resolution observation v0

## Status and scope

**Selected original-loader observation completed:** owner-dispatched
[run `45881405789`, attempt 1](#completed-hosted-observation-458814057891)
on 2026-11-26, at source `f2854184ebb069ed6407874a68a4aaa1c84fea5c`,
completed the nine selected dependency-return observations, original entry stop,
separate hosted replay, owned cleanup and attestation verification. The result
and its exact preservation are described below.

This unit implements the GitHub acquisition and independent replay route for the
[bounded original-loader collector](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_v0.md)
merged in #3055. Its implementation base is
`a97e493fdca0d7d9bd4f472fe6825fe61e22f769`.
Implementation checks do not execute the original launcher, native probes or
this workflow. The [first owner-dispatched attempt](#first-hosted-attempt-455866533791)
stopped incomplete at cp0. The [second attempt](#second-hosted-attempt-458361762661)
passed cp0 and stopped on an unselected loader-cache mapping at the first
dependency return. Both records remain incomplete. The completed third run has
its own source and attempt identity, including the reviewed cache-absence
selection; it does not promote either earlier failure.

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
| [Environment selection](../../tools/required_gate_idempotence_loader_resolution_hosted_v0/environment.json) | Exact base, Python, GPG, OpenSSL, package and original-object bytes, with explicit loader-cache absence |
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
installs the fixed `.deb` and wheel sets offline, applies the selected cache
absence policy, checks selected file and package identities, and runs positive
and negative Ed25519 known-answer tests in that final filesystem configuration.
Fresh original GPG verification and rebuild acceptance, including their own
OpenSSL checks, still run in the unchanged admission code before native probes.
The build record is not an admission result.

The hosted filesystem explicitly selects `/etc/ld.so.cache` as
`absent_after_package_install`. Package triggers can generate this additional
resolver input, whose bytes and backing identity are outside the six selected
original ELF objects. After all package installers finish, the builder removes
only a regular, single-link cache entry through a pinned real `/etc` directory.
Symlinks, other file types, access errors, replacement and reappearance fail the
build. The builder checks absence before its final crypto tests and again before
publishing its bound build record. This operation is confined to the constructed
image; the host controller does not remove a host cache.

Acquisition, the observer and verification each passively check the current
cache absence before continuing. Acquisition and verification separately preserve
`loader-cache-state.json`; the hosted checker requires its exact phase,
environment binding and absence statement alongside the build record. Missing,
changed or contradictory state cannot establish completed hosted verification.
The selected readonly root and exact mounts provide no writable `/etc` path.
These process observations retain the existing physical-authentication limits.

The original loader's compiled default directories include
`/lib/x86_64-linux-gnu/`, `/usr/lib/x86_64-linux-gnu/`, `/lib/` and `/usr/lib/`.
The four selected dependent libraries occupy those directories, and the original
ELFs have no `DF_1_NODEFLIB` restriction. The pinned Python observer has
`RUNPATH=$ORIGIN/../lib`. Data-only inspection therefore supports cache-independent
lookup without changing original bytes, argv, environment or the accepted
rebuild policy. It does not establish completion of a future native attempt.
The native map checker still rejects every unselected file-backed mapping,
including `/etc/ld.so.cache`; there is no pathname exemption.

Acquisition preserves the base image archive, all twenty package/wheel/native
materials and five configuration files. Independent verification loads that
base archive and reconstructs its image offline without a replacement registry
or package-download path. Actual acquisition and verification image IDs are
recorded separately; reproducible image IDs are not claimed.

## Acquisition, replay and cleanup

| Phase | Execution | Required evidence |
| --- | --- | --- |
| Acquisition host | Build the selected environment and create one restricted, labelled container | Source/Git/material bindings, fixed command records and actual inspections |
| Acquisition container | Check cache absence, supervise one PID-greater-than-one observer, invoke the existing adapter once and run two separate native raw checkers | Fresh cache state, request, complete raw capture, two equal canonical reports and build record |
| Verification host | Check the exact current-run artifact and receipt; privately copy preserved bytes; rebuild offline | Artifact metadata, source and material identity, fresh container policy |
| Verification container | Check cache absence and run two separate data-only raw checkers against the preserved request and capture | Fresh cache state and two reports equal to each other and both acquisition reports |
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

The completed owner-dispatched run below is separate from those implementation
checks. Any later acquisition still requires review, PR CI and merge, the exact
reviewed main SHA, explicit policy selection and a new owner dispatch. Its result
must be assessed from both jobs, raw artifacts, all four checker reports, cleanup
and attestation. The completed loader observation does not close #2879 or
authorize another execution.

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

## Second hosted attempt: 45836176266/1

Owner-dispatched [run 45836176266, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45836176266)
used source `b88f3a4df2aabd1e9c39c98eeae9b09147c06f07`. The dispatch guards,
fresh original admission and same-observer qualifications passed. The native
capture passed cp0 and recorded two successful continuations. Its first
dependency-return checkpoint remained partial, with no accepted return event
and no terminal entry checkpoint. Acquisition stopped with
`loader_resolution_unselected_file_mapping`.

The unchanged first-return map contains one file-backed identity outside the
admitted original roster:

```text
7f434f0d2000-7f434f0d4000 r--p 00000000 00:2e 5505580                    /etc/ld.so.cache
```

That is an 8,192-byte cache mapping. The concurrently appearing
`libselinux.so.1` mapping matches its selected backing. Data-only replay of the
preserved readout against the original maps and backing records accepts cp0
and rejects the first return with the same code. The original build log records
the `libc-bin` package trigger; the environment had not selected cache absence
after installation. The strict mapping guard is retained unchanged.

The owned acquisition container was removed and its absence verified. The
verification job verified the original artifact, receipt and all 330 preserved
files, including the receipt itself, then stopped with
`loader_resolution_hosted_incomplete_prefix`. The receipt binds 329 payload
files. Attestation was skipped; this is diagnostic custody of an incomplete
attempt.

| Original artifact | ID | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [Acquisition](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45836176266/artifacts/15126560334) | `15126560334` | 220047130 | `a8d7930cfc17e0adaad619569a91cd7c67f1cb7c93b4be13b30540c088988f0c` |
| [Verification](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45836176266/artifacts/15125821404) | `15125821404` | 6773 | `6204c162e436663b377be4953854d2788e537fbc024e99416d5554eb208b1f4f` |

The acquisition receipt SHA-256 is
`6d47c807cac9e1f930b3e4f487020f887ecf884c6f09a2f0ce45020513d48a3e`.
Unchanged cp0/first-return maps, the original backing record and exact provenance
are retained as a [small regression fixture](../../tests/fixtures/loader_resolution_cache_mapping_45836176266_v0/provenance.json).
It is not a complete capture or a substitute for the original artifacts.

The selected cache-absence correction changes the hosted environment binding
and requires a fresh source-bound owner dispatch after review, CI and merge.
It does not rewrite either failed attempt, relax original admission or claim
that later return checkpoints will complete. The whole-runtime issue #2879
remains open, with `b2_complete=false`, `metric_pass=null` and
`authority_effect=none`.

## Completed hosted observation: 45881405789/1

The owner dispatched
[workflow run `45881405789`, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45881405789)
on 2026-11-26 from `main`, selecting source and workflow commit
[`f2854184ebb069ed6407874a68a4aaa1c84fea5c`](https://github.com/HKati/pulse-release-gates-0.1/tree/f2854184ebb069ed6407874a68a4aaa1c84fea5c),
the exact rebuild-policy digest above and
`OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY`. Both acquisition
and the separate replay/attestation job succeeded. The run completed at
2026-11-26 19:12:47 UTC. A later preservation commit does not replace this
execution's source identity.

### Selected original result

The preserved request ID is `0cd4d7d3267f1010a499a7b415fb2b74`. Fresh original
and selected-policy admission and the current observer's guard/two-slot
qualifications preceded one original-loader attempt. Its capture has origin
`native_original_loader_capture`, status `completed` and no failure. The
original invocation remains `argv=["bubblewrap"]`, `cwd="/"`, with only
`LC_ALL=C` and `TZ=UTC`.

The raw checker reconstructed these nine distinct original `DT_NEEDED`
consumer/provider occurrences:

| Return | Consumer | Requested name / returned original provider |
| --- | --- | --- |
| 1 | `bwrap` | `libselinux.so.1` |
| 2 | `bwrap` | `libcap.so.2` |
| 3 | `bwrap` | `libc.so.6` |
| 4 | `libselinux.so.1` | `libpcre2-8.so.0` |
| 5 | `libselinux.so.1` | `libc.so.6` |
| 6 | `libselinux.so.1` | `ld-linux-x86-64.so.2` |
| 7 | `libcap.so.2` | `libc.so.6` |
| 8 | `libc.so.6` | `ld-linux-x86-64.so.2` |
| 9 | `libpcre2-8.so.0` | `libc.so.6` |

The final checkpoint is the original executable entry. The accepted record
accounts for eleven `PTRACE_CONT` calls and zero continuations after entry,
followed by owned child termination and reaping. The final mapping inventory
contains six original objects and twenty-four `PT_LOAD` occurrences. The report
records sixteen original RX samples and eighteen return RX samples within the
selected paired-read contract. These observations do not describe execution of
the launcher's post-entry body or the selected metric runtime.

The capture contains 252 bound raw files plus `capture.json`, totaling
11,719,149 bytes. The manifest itself is 118,469 bytes, SHA-256
`b34319dc8472125612ca2d2f78eb4b7ba749944e0e639e1f7bccf4a33ea8203f`.
Both acquisition reports and both verification reports are byte-identical:
6,599 bytes each, SHA-256
`c51e8e880bfc97379708439f1aa4980497615d23389c6883bbd4434fce4c5e89`.
Their accepted status is `accepted_native_loader_resolution_record`. These are
four processes using the same independent raw-checker implementation; the two
verification processes ran in the separate reconstructed environment.

The raw reports establish `consumer_resolution_observed=true` and
`loader_resolution_verified=true` for this selected attempt. The hosted
summaries, receipt and attested binding retain their original conservative
boundary objects. Those different scopes are preserved without rewriting
either record type. The selected source/build-policy result retains its
documented service-endorsement and source-association trust assumptions.

### Selected environment and cleanup

Both phase build records select `/etc/ld.so.cache` as
`absent_after_package_install`. Both fresh `loader-cache-state.json` records
report absence and bind environment selection SHA-256
`677e221369cd27420ec726974f204b7a2be1444437ae7df494bd12786308762b`
(25,705 bytes), with their respective `acquire` and `verify` phases. All
twenty-two preserved cp0/return/entry map samples omit the cache. The raw checker
continues to reject unselected file-backed mappings; this result required no
pathname exception.

Both containers retained the selected readonly root, exact mounts, network
`none`, dropped capabilities, no-new-privileges and `docker-default` AppArmor
profile. Both terminal inspections report exit code zero, no OOM and no Docker
state error. Both owned-cleanup records report verified ownership, successful
removal and verified absence, with empty cleanup-error lists. Acquisition and
verification retain separate image and container identities; reproducible image
IDs and future-host admission are not claimed.

### Original artifacts and attestation

The complete original ZIP byte streams were checked against their provider
sizes and SHA-256 values before selecting repository evidence.

| Original artifact | ID | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [Acquisition](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45881405789/artifacts/15147471320) | `15147471320` | 227871854 | `5c1477e4051d62871bb130ef8aee0e2718f1c738be3b130cfe8c258b57b8f5c8` |
| [Verification](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45881405789/artifacts/15147282024) | `15147282024` | 86371424 | `d6b2c0b987fd61f97e68bd5c779a5eaa603551c66b7dd0fa5eeb6c3d11ff8fbe` |

The exact acquisition-receipt SHA-256 is
`cbb4a07ead4b6aef0317581d89cf9a609bae1ecbf69e19fa3ca6fc345dc35fee`.
The attested `verified-binding.json` is 28,833 bytes, SHA-256
`01ab395f8a4508c05c85bb2db4215422fc37ec8f37e39f94d1f222d4d77dcf96`.
Its original bundle is 11,501 bytes, SHA-256
`fbacce304cfa0d46b7974516f4b8a10dca07c585336df9c56fd8870b1b221b44`.

The original hosted attestation-verification command succeeded with the selected
repository, signer workflow, source/signer digests, main ref and hosted-runner
constraints. The subject, original bundle, identity, command outputs and accepted
verification record are preserved together. This authenticates the hosted
statement within its recorded boundary; physical execution authentication and
complete native closure remain false.

### Local preserved-data reconstruction

Two fresh local processes of the unchanged raw checker reproduced all four
original hosted reports byte for byte. The review used CPython 3.12.14,
jsonschema 4.26.0 and the exact selected `/usr/bin/gpg` bytes: 1,230,080 bytes,
SHA-256 `7c9d2f9416aabcd10199e2984439f49612644a948279ac56bdf70d69c8958ddf`.
Both processes freshly reconstructed the original-input and selected-policy
admission chain from the preserved inputs and exited zero. Their outputs retain
the report binding above; using two processes does not introduce a second
independently implemented checker.

The unchanged hosted checker revalidated the acquisition receipt and completed
acquisition, then reproduced the original 28,833-byte `verified-binding.json`
exactly. Both artifacts' 153 selected source entries match the actual fetched
Git tree at `f2854184ebb069ed6407874a68a4aaa1c84fea5c`. All 531 acquisition
members and 276 verification members retained their original bytes and modes.

The outer join requires the recorded absolute private-input path,
`/home/runner/work/_temp/required-gate-loader-resolution-verification-45881405789-1-private-input`.
The review created a regular-file restoration of the complete acquisition at
that previously absent path, checked all 531 member bytes and modes, performed
the unchanged join, and removed the owned copy and newly created parent
directories. No original evidence or checker was rewritten to accept a
relocated mount.

This was preserved-data reconstruction. No original process, qualification
probe or container was run, and execution in the original container image is
not claimed. The original hosted GitHub attestation verification remains
preserved evidence; its signature was **not freshly verified locally**. These
local checks remain separate from the actual hosted acquisition and its
signature-verification result.

### Repository selection and original custody

The [control evidence selection](../../preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/control_evidence_v0.zip)
retains unchanged original artifact members, including the complete unique raw
capture, current-observer qualifications, admission/signature diagnostics,
request, all four hosted checker reports, receipts and handoff, source-binding
inventories, environment/cache controls, command/runtime/cleanup records and
attestation evidence. The
[descriptive preservation inventory](../../preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/verification_record_v0.json)
provides the selection's exact byte binding, member counts and every selected
or omitted member's original artifact, path, size and SHA-256. That inventory
is not an additional independent checker report.

Selected payload bytes and original permission attributes are preserved. The
derived ZIP uses phase-prefixed paths, fixed timestamps and deflate compression;
the complete original ZIP byte streams retain their original archive metadata.

Large base-image, package/wheel and separate native-material payloads, and full
source copies including the original-input transport archive, remain in the
complete original artifacts. Their omission from the repository selection does not change the
original receipt or any original bytes. The derived control archive is neither
original GitHub ZIP and is not a complete hosted-environment replay carrier.
Full hosted replay still requires the complete originals and the selected
source/verifier environment.

Retain both original ZIP byte streams in the separate custody package
`B2_LOADER_RESOLUTION_45881405789_1_ORIGINALS.zip`, and verify their exact sizes
and hashes above. The repository-only files package is
`B2_LOADER_RESOLUTION_RUN3_REPO_FILES_v0.zip`; it does not replace original
custody. Review-workspace copies were verified. Receipt and hash verification
on the owner's own machine have not been observed. Both provider artifacts
record expiry at **2027-02-24 19:08:45 UTC**. Provider retention is not permanent
custody. This preservation introduces no LFS, source-budget increase or paid
artifact service.

### Next bounded B2 obligation

The selected nine-return original-loader observation is complete. The next
design task is the observed containment boundary and selected-bootstrap
integration: declare the exact launcher invocation, namespace/task-creation
rules, expected process relationships, collector separation, supported terminal
condition and failure behavior before implementing another acquisition profile.
The present one-tracee/task-guard profile and entry-stop acknowledgement do not
authorize continuation beyond entry or establish namespace containment.

No old capture is a live process prefix. Any later native acquisition requires
its own reviewed contract and separate owner authorization. This preservation
update performs no dispatch. Both earlier original-loader failures remain
incomplete under their own source and attempt identities.

Whole-runtime occurrence and terminal closure, selected-bootstrap execution,
B3 property evidence, B4 admission and B5 actual-reference work remain separate.
Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open
under its full Step 5C acceptance conditions, with `b2_complete=false`,
`metric_pass=null` and `authority_effect=none`.
