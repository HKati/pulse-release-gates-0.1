# B2 original launcher exec-stop GitHub observation v0

## Status and scope

**The selected original launcher/interpreter exec-stop observation completed in
manual run `44375052171/1` on 2026-11-18. Both jobs succeeded; two independent
checker processes reproduced the completed capture, and the hosted attestation
verification succeeded. The original evidence and its narrow result are
preserved below. The earlier `44318024733/1` installation failure retains its
incomplete meaning. B2 remains incomplete.**

This unit continues the
[original launcher exec-stop acquisition](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_v0.md).
That unit established an original-input request and two accepted,
byte-identical preparation reports. It did not acquire an original-launcher
kernel exec checkpoint. The present workflow supplied the reviewed place for
the completed observation, with fixed inputs, an explicit owner action,
bounded evidence preservation and a separate verification job.

Repository CI checks the implementation and its synthetic failure cases. A
green PR does not supply an original-launcher capture. The live result below
comes from the owner's separate manual workflow dispatch. Preparing this
preservation update did not repeat acquisition. Any future manual run must
supply its own observed result; a denied prerequisite retains that meaning.

The selected checkpoint remains `linux_x86_64_original_launcher_exec_stop_v0`:
the kernel has installed the original launcher and interpreter images, and the
child is stopped at `PTRACE_EVENT_EXEC` before the new interpreter's first
userspace instruction. The collector allows one pre-exec restart and no
continuation or detach after that event. It does not run the containment entry,
selected runtime, sanitizer, model or actual reference.

## Repository components and preserved inputs

| Component | Responsibility |
| --- | --- |
| [Manual workflow](../../.github/workflows/required_gate_idempotence_exec_stop_v0.yml) | Admit the exact owner/main/attempt context; preserve acquisition and verification artifacts; attest only completed verification. |
| [Hosted driver](../../tools/required_gate_idempotence_exec_stop_hosted_v0.py) | Bind the checkout and hosted context, acquire the fixed environment inputs, run the selected phases, and finalize the evidence receipts. |
| [Bounded byte transport](../../tools/required_gate_idempotence_exec_stop_hosted_io_v0.py) | Verify the closed original-input archive and reconstruct private trees from exact file inventories. |
| [In-container phase runner](../../tools/required_gate_idempotence_exec_stop_hosted_run_v0.py) | Execute the fixed preparation/check/acquisition sequence or the separate pair of capture checks with the selected observer. |
| [Environment selection](../../tools/required_gate_idempotence_exec_stop_hosted_v0/environment.json) | Pin the base image, observer, selected loader, GPG executable, Debian additions, Python wheels and container restrictions. |
| [Offline image recipe](../../tools/required_gate_idempotence_exec_stop_hosted_v0/Dockerfile) and [builder](../../tools/required_gate_idempotence_exec_stop_hosted_v0/build_environment.py) | Install only the selected downloaded bytes without network access; check selected installed file identities and package versions. |
| [Python lock](../../tools/required_gate_idempotence_exec_stop_hosted_v0/requirements.lock) | Fix all seven wheel versions and digests; disable dependency resolution during installation. |
| [Original-input selection](../../preservation/required_gate_idempotence_exec_stop_v0/ORIGINAL_INPUTS.json) and [archive](../../preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip) | Carry the complete selected original case, preserved reports, historical sources and unchanged original hosted artifact ZIPs in the repository. |
| [Original preparation adapter](../../tools/prepare_required_gate_idempotence_exec_stop_v0.py), [collector](../../tools/required_gate_idempotence_exec_stop_v0.py) and [checker](../../tools/check_required_gate_idempotence_exec_stop_v0.py) | Retain the existing request, owner acquisition and independent capture semantics. |
| [Containment regressions](../../tests/test_required_gate_idempotence_containment_v0.py) | Retain the previous test prefix and add hosted environment, transport, workflow and lifecycle rejection cases. |

The new repository carrier has **114 regular files**, representing
**72,234,203 decoded bytes**. Its ZIP is **24,816,167 bytes**, with SHA-256:

```text
70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a
```

It retains the 111 original case members, the original `CASE_INPUTS.json` and
the two original canonical checker reports. The case manifest remains
20,420 bytes with SHA-256
`16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa`.
The two original GitHub entry-build artifact ZIPs are preserved inside the
carrier as original ZIP bytes. The carrier's packaging time is not an
acquisition time, and constructing this carrier does not recollect the
historical network inputs.

The **43 historical verification sources and ten original exec-stop source
files remain unchanged**. The hosted driver, byte transport and in-container
phase runner are additional bridge sources. The four environment files, new
workflow and original-input selection are separately bound with them. This
additional source binding does not rewrite an earlier source-bound report.

The transport verifies archive and member digests, sizes, names and the closed
file inventory before admitting the original case. Private copies use new
directories and exclusive files. Descriptor identity checks and nonblocking
opens reject substituted file types; a partial extraction or copy retains its
already written prefix for diagnosis. Preserved `replay.py` files are data:
the hosted bridge does not import or run them.

## Fixed observation-tool environment

The host workflow uses the runner's standard-library `python3` only for the
hosted bridge. Original preparation, signature verification and capture checks
use **CPython 3.11.16** in the selected Linux amd64 image:

```text
docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761
```

The environment selection also pins the manifest, image configuration and
layer byte bindings. The selected base already contains the required
`/lib64/ld-linux-x86-64.so.2`: **225,672 bytes**, SHA-256
`c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307`.
The recipe checks this exact terminal file before and after installation.
It does not install or replace libc, replace the loader, patch `PT_INTERP` or
invoke an alternate loader. A matching distribution version label alone does
not satisfy this byte selection.

The Debian dependency declaration contains eighteen exact package records.
Eleven selected versions are already present in the base; exactly seven
additional packages are installed from their pinned `.deb` bytes:

| Package | Selected version |
| --- | --- |
| `gpg` | `2.4.7-21+deb13u1+b5` |
| `gpgconf` | `2.4.7-21+deb13u1+b5` |
| `libassuan9` | `3.0.2-2` |
| `libgcrypt20` | `1.11.0-7+deb13u1` |
| `libgpg-error0` | `1.51-4` |
| `libksba8` | `1.6.7-2+b1` |
| `libnpth0t64` | `1.8-3` |

These additions are checked against the complete preserved Debian Packages
index selected by the original distribution chain. The image recipe admits
only those seven additions and checks the selected dependency versions before
and after installation. It checks the resulting `/usr/bin/gpg` bytes against
the original selected verifier.

Seven exact wheels supply the six original Python dependency selections and
the explicitly declared additional dependency for the selected interpreter:

| Python package | Selected version |
| --- | --- |
| `PyYAML` | `6.0.3` |
| `attrs` | `26.1.0` |
| `jsonschema` | `4.26.0` |
| `jsonschema-specifications` | `2025.9.1` |
| `referencing` | `0.37.0` |
| `rpds-py` | `2026.9.1` |
| `typing_extensions` | `4.16.0` |

`typing_extensions` is an additional observation-tool dependency required by
the selected `referencing` package on Python 3.11. It does not change the six
original package selections or turn the preserved authored inert runtime
capsule into the actual Q2 runtime.

The acquisition job may fetch only the selected environment inputs before
building. It preserves the downloaded package/wheel bytes and a bounded
`docker image save` archive of the selected base image. The base's inspected
configuration digest must match the selection; its fixed local tag is derived
from that digest and checked before and after building. Verification loads the
exact receipt-bound archive and checks the restored configuration identity,
without another registry pull, image save or package download. Both builds
use the same reviewed Dockerfile and checked local tag, with `--pull=false`
and `--network=none`. Debian installation passes only the seven verified local
archive paths to `dpkg --install`, with normal dependency checks and trigger
processing. It performs no dependency resolution or package download and uses
no force or fallback options. The selected base plus those seven additions
supply the already checked dependency closure; all selected package versions
and runtime file bytes are checked again after installation. Wheel installation
uses `--no-index`, `--no-deps` and `--require-hashes`.
The two actual constructed image IDs are recorded separately.
This recipe fixes the selected inputs and checks the declared installed
relationships. It does not assert byte-identical rebuilt images or complete
compiler, image-builder, host or native-runtime closure.

### Container restrictions and remaining host dependence

| Restriction | Selected setting |
| --- | --- |
| Platform | `linux/amd64` |
| User | Invoking non-root runner UID and GID |
| Network | `none` |
| Capabilities | Drop `ALL` |
| New privileges | `no-new-privileges` enabled |
| Root filesystem | Read-only |
| Source and selected input mounts | Read-only |
| Output | Separate writable preservation mount |
| Temporary directory | 64 MiB tmpfs, `nosuid,nodev` |
| Resource limits | One CPU, 1 GiB memory, 64 processes |
| Seccomp and AppArmor | Inherited Docker defaults retained |

The workflow supplies no privileged mode, added tracing capability, unconfined
policy, host-loader replacement or sysctl change. Docker restrictions and an
exact loader selection do not establish that the kernel will permit the owned
child's tracing, procfs and memory operations. Those operations remain actual
prerequisites of the one attempt. A denial is preserved without relaxing the
selected policy or automatically retrying the acquisition.

The GitHub runner, kernel, Docker engine and builder, observer environment,
procfs and retained descriptor observations remain explicit trusted components.
A manual run that reaches the collector must determine the observed result
under that particular host context.

## Two jobs and one original attempt

The workflow is manual-only, uses `ubuntu-24.04`, and gives each job a
30-minute outer timeout. Its concurrency group does not cancel an in-progress
observation. The exact source is checked out with credentials persistence
disabled. Checkout, upload, download and attestation actions use fixed commit
pins.

Each hosted acquisition or verification phase also has a 1,200-second shared
command/download budget. Owned-container cleanup has its own bounded allowance
so exhausting the phase budget does not skip removal. Ordinary command streams
have independent 4 MiB caps. The base-image export alone has a 256 MiB stdout
cap; its stderr retains the ordinary cap. The acquisition receipt admits at
most 1,024 files and 512 MiB in total. Each file is read through a bounded
regular-file descriptor. These process bounds do not promise preemption of
an uninterruptible kernel operation or preservation after a runner outage.

Both jobs admit only repository `HKati/pulse-release-gates-0.1`, repository ID
`1061766508`, event `workflow_dispatch`, ref `refs/heads/main`, actor and
triggering actor `HKati`, and run attempt **1**. The supplied source commit
must equal both `GITHUB_SHA` and `GITHUB_WORKFLOW_SHA`. The workflow reference
must identify this exact workflow on `main`. The acknowledgement is checked
again by the hosted driver.

Before checkout, each admitted job creates a private `workflow-start.json`
containing its phase and exact source, workflow, repository, actor and run
context. This makes an early checkout or setup failure preserve a visible
start prefix when the upload step can run.

### Acquisition job

The `acquire` job has read-only repository permissions. It preserves the
selected source and original-input bindings, fetches and verifies the fixed
environment inputs, and builds the observation image offline. Inside the
restricted container, it creates a **fresh host-specific request** using the
unchanged original preparation adapter. Two separate request-check processes
must reconstruct accepted, byte-identical canonical reports before the one
owner acquisition is attempted.

The owner acquisition uses the original closed profile and fixed
acknowledgement. It attempts the original launcher/interpreter cp0 once.
There is no automatic second attempt, alternate launcher, authored-probe
substitution or post-exec continuation. The original collector preserves the
raw capture or its bounded incomplete prefix and performs owned-child cleanup.

When checkout is available, finalization runs even after an acquisition
failure. It binds the available files in a receipt and exports the receipt
digest separately from the uploaded bytes. The upload retains the entire
available acquisition root, including command logs and failure diagnostics.
A failure before a receipt can be finalized retains its available prefix but
does not manufacture a verifiable receipt.

### Independent verification job

The `verify` job runs when an acquisition artifact ID and receipt digest are
available, including when the acquisition job failed. It repeats the owner and
source-context checks, downloads that exact artifact ID from the current run,
rejects a transport digest mismatch and checks the external receipt digest.
Artifact-name similarity or an accepted report found in the download cannot
replace those bindings.

The job reconstructs the exact admitted file tree into a new private copy,
including the private modes needed by the original checker. It rebuilds the
selected environment from preserved inputs and invokes the unchanged
`check-capture` path twice in separate processes. Each execution reconstructs
the original request/capture relationships and freshly verifies the original
Debian signature chain. The two accepted canonical reports must be
byte-identical. Verification does not invoke the acquisition command.

The original signature evaluation epoch remains **1794787200**
(2026-11-16 00:00:00 UTC). Fresh cryptographic checking at that selected epoch
does not update historical publication time, recollect network inputs or
establish current trust-policy freshness.

Accepted reconstruction of an incomplete capture remains an **incomplete,
failed workflow result**. Only a completed original checkpoint with successful
independent verification produces `verified-binding.json` for attestation.
The separate job signs that exact binding and preserves the original
attestation bundle and the result of its signature verification. A successful
attestation action alone is insufficient: the bounded signature verification
must also succeed. Signing permissions are confined to this job, and the
`GH_TOKEN` environment variable is confined to its signature-verification step.

## Evidence to retain and interpret

The acquisition artifact is named:

```text
required-gate-idempotence-exec-stop-<run_id>-1
```

The separate verification artifact is named:

```text
required-gate-idempotence-exec-stop-verification-<run_id>-1
```

Both uploads retain their available roots on failure, disable overwrite and
request 90-day retention. Hidden files are included so the receipt-bound copy
of `.github/workflows/required_gate_idempotence_exec_stop_v0.yml` survives the
artifact transfer. The verification root retains the original downloaded
input separately from the reconstructed private copy and new verification
outputs. An uploaded artifact is preservation evidence, not proof that the
acquisition completed.

For each actual run, retain the original downloaded GitHub artifact ZIP bytes,
run and attempt, source/workflow commit, artifact IDs, external receipt digest,
and artifact transport bindings before interpreting the result. Preserve the
following evidence as available:

- Start records, source bindings, original carrier and selected environment
  inputs, including the original Docker-save archive and downloaded
  Debian-package and wheel bytes.
- Bounded command stdout/stderr, image-build records, image and container
  observations, and failures from setup through terminal cleanup.
- The fresh request, its two canonical checks and signature diagnostics.
- The original capture record and every available raw register, auxv, process,
  maps, identity, executable and selected-memory member, including an incomplete
  attempt's retained prefix.
- The acquisition receipt, both independent capture-check reports and their
  fresh signature evidence.
- On completed verification, the exact `verified-binding.json`, original
  attestation bundle and successful signature-verification evidence.

A complete result can establish the selected launcher/interpreter image and
kernel-event relationships, **eight** independently checked `PT_LOAD`
occurrences, and **four RX samples totaling 400,964 bytes**. Every occurrence
retains its own obligation. The two repeated samples per selected RX extent
must independently equal the original backing bytes. These observations do
not cover RW, BSS, padding, all process memory or every intermediate state.

The other four selected native objects remain unobserved at cp0. The twelve
per-consumer dependency edges remain a static graph. Actual later library
resolution, native occurrences and observed containment require their own
bounded observations.

## First hosted attempt: offline installation failure

[Run 44318024733, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44318024733)
was dispatched by `HKati` from `main` on 2026-11-18. Both source and workflow
commit were `179868e6f3948dba99bf31bffdadeeda0898f1c6`.

The owner/context checks, selected input checks, dependency downloads, pinned
base-image pull, local tag checks and base-image preservation succeeded. The
offline Docker build reached the Debian installation command, where
`apt-get --no-download install` failed with exit status 100:

```text
E: Internal Error, Pathname to install is not absolute 'libgpg-error0_1.51-4_amd64.deb'
```

The command had received absolute archive paths. Its original diagnostic is
preserved in `host-commands/docker-build.stderr.bin`; the hosted acquisition
reported `hosted_docker_build_failed`. No observation container, fresh request
or original-launcher capture was produced. The verification job accepted the
receipt-bound preserved prefix, then reported `hosted_capture_not_published`.
It produced no completed binding or attestation.

| Preserved item | Binding |
| --- | --- |
| Acquisition artifact | [14433985923](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44318024733/artifacts/14433985923), 159,992,157 bytes |
| Acquisition ZIP SHA-256 | `7cbbfd7f9001339f54daa3161f4e786714e752341330f1c79e13992e3caf1a64` |
| Verification artifact | [14433133494](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44318024733/artifacts/14433133494), 319,992,180 bytes |
| Verification ZIP SHA-256 | `bcb77f596128a95ecd147268e0861bb083d5d5c4a52524c0ad32c985fbc86f65` |
| External acquisition receipt SHA-256 | `803281a14b32979fe0b76b47e69c3633fa8e3f037957301da3889c08bbaffe0a` |

The installer correction uses direct `dpkg --install` for the same seven
checked archives. The selected image, package and wheel bytes, loader binding,
observation policy and original collector/checker remain unchanged. The failed
attempt retains its original evidence and incomplete meaning; a later dispatch
must establish its own result.

## Start a new manual observation after merge

This is the retained procedure for a future separately selected observation.
The completed run below already supplies the selected cp0 result; preserving
it and specifying the next B2 obligation do not require another dispatch.

Open [PULSEmech original launcher exec-stop observation v0](https://github.com/HKati/pulse-release-gates-0.1/actions/workflows/required_gate_idempotence_exec_stop_v0.yml)
from the `HKati` account after the reviewed workflow has merged to `main`.
Choose **Run workflow** and enter:

| UI field | Exact selection |
| --- | --- |
| Branch | `main` |
| `expected_source_commit` | The full 40-character lowercase SHA of the reviewed `main` merge that contains this workflow and hosted implementation. |
| `acknowledgement` | `OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY` |

Read the newly merged commit SHA from GitHub at dispatch time. No earlier
preparation commit or illustrative hash substitutes for that selection.
The first run of a new dispatch is required; **Re-run jobs** creates a later
attempt and is rejected by this profile. A new original acquisition remains
an explicit owner decision with a new dispatch and its own preserved evidence.

Inspect both jobs and their artifacts. A green completed workflow must include
the accepted completed capture, equal independent reports and successful
attestation verification. If the attempt is incomplete or a prerequisite is
denied, retain its artifacts and inspect the exact rejected boundary before
selecting further work. The evidence does not acquire a stronger meaning from
the workflow badge alone.

## Local validation and unchanged claim boundaries

| Validation obligation | Required evidence |
| --- | --- |
| Historical source preservation | All 43 historical verification sources and ten original exec-stop source files retain their selected bytes. |
| Regression preservation | The complete 914-case test source remains an exact prefix, including the 668 pre-hosted cases; eleven installer cases are appended to the same module. |
| Original implementation test result | **914 containment cases passed: 668 prior cases plus 246 hosted cases.** All 61 normative inventory cases also passed. CPython 3.11.16 ran the completed containment suite in 115.11 seconds. |
| Installer correction test result | **986 passed: 925 containment cases and 61 normative inventory cases**, under CPython 3.11.16 in 155.84 seconds. The added tests exercise the actual builder with authored bytes, mocked process invocation, payload faults and post-install mismatches. |
| Actual offline installer validation | The complete corrected script returned 0 against the preserved base layers, seven Debian archives and seven wheels in a separate network namespace. All 87 existing Debian packages retained their versions; all three selected runtime file bindings matched. |
| Workflow admission and failure preservation | Exercise owner/source/attempt rejections, exact private start records, failed-job artifact handoff and completed-only attestation without original-target execution. |
| Input and environment selection | Check the carrier's closed inventory, per-file bytes, substituted-file rejection, fixed package/wheel selections and offline build command construction. |
| CI coverage | Keep the 189 Tools and 40 targeted pytest roster entries unchanged. |
| First live GitHub attempt | Run `44318024733/1` preserved an incomplete environment-build prefix; its request and capture remain absent. |
| Completed live GitHub observation | Run `44375052171/1` completed acquisition and separate verification. Its original capture, two equal accepted reports and successful hosted attestation verification are preserved below. |

The actual local installer check used a rootless chroot, not Docker. Four
preserved base layers were verified before restoration; file contents, modes
and links were retained, while fourteen layer entries with nonzero UID/GID
were normalized to mapped-root ownership. The unchanged APT installer failed
earlier at its unmapped sandbox UID/GID, so that local baseline did not
reproduce the GitHub pathname diagnostic. The corrected installer completed
without changing its validation guards. The later hosted run `44375052171/1`
separately established Docker-build completion and the selected original
checkpoint; the local installer test retains its narrower scope.

## Completed hosted observation — 44375052171/1

The owner dispatched [workflow run 44375052171](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44375052171),
workflow number **2**, attempt **1**, from `main` at source/workflow commit
`84b78ff1758ed3db73fbb1db1b37451ca6620373`. Both actor fields are `HKati`.
The run started at **2026-11-18 18:56:04 UTC** and completed at
**18:58:12 UTC**. Acquisition job `135051876641` and verification job
`135052510782` both succeeded.

The [descriptive preservation record](../../preservation/required_gate_idempotence_exec_stop_v0/run_44375052171_attempt_1/verification_record_v0.json)
records the source, artifact identities, selected original members, narrow
result, attestation and remaining obligations. It is an inventory and review
record, not an additional independent checker report or an authorization.

### Original artifact transport and handoff

| Original artifact | Exact ZIP bytes | Members | SHA-256 |
| --- | ---: | ---: | --- |
| [Acquisition 14460412647](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44375052171/artifacts/14460412647) | 161,254,756 | 220 | `50e3f48ee11937b880770985ec8a72b8eb668af8c50f52614490c46c6c354b4e` |
| [Verification 14460567554](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44375052171/artifacts/14460567554) | 329,299,985 | 645 | `9b9f95e2ab9a04691a8aaba6aad78874aa70e4dc1c1bb24f63f473eb36f71155` |

Downloaded original ZIP sizes and SHA-256 values match the provider metadata.
All outer members passed size, CRC and path/roster checks. The acquisition
receipt binds **219 payload files, 161,170,630 bytes**, with external SHA-256
`e57d1d742251dbbcf1f92033273889ead9b3ac23daa6f89ae4847dd613631e6c`.
Including that receipt gives the 220-member acquisition artifact. Both
verification `input/` and `private-input/` trees retain all 220 files byte for
byte. All **62 source bindings** match the exact source commit. The original
114-member input carrier, seven Debian archives and seven wheels retain their
selected bytes.

### Completed checkpoint and independent reconstruction

| Evidence | SHA-256 |
| --- | --- |
| Original request, 8,106 bytes | `c23bfc0f22e3f0a52f09c141a4956c2b7431fc2109c72fff9bcf66642043a7a9` |
| Capture record, 5,588 bytes | `0e7bc25175f9c95393ab7bd9a9895e72be5f608b17c2012c4249775e3c5dce13` |
| Each request-check report, 1,244 bytes | `81fe3f292d0922095cb52a806ff51b9bffefe610aca9c6183e1fb58c8c3deabb` |
| Each capture-check report, 2,200 bytes | `8a2769ae4e7858f73b7cca9285724aabaee152f4dbf6e5bfb6c603cea538b34b` |

The two request reports are canonical, accepted and byte-identical. The
acquisition result and the two independent capture reports are also canonical,
accepted and byte-identical. Both hosted capture checks freshly reconstructed
the distribution/launch-host chain and checked its distribution signatures at
the selected original epoch **1794787200**. They are two processes using one
checker implementation, not two acquisitions or two independent implementations.

The capture retains all **33 selected files including `capture.json`**. The
original launcher and interpreter have **eight `PT_LOAD` segment occurrences**
in total. Four RX sample records match their original file ranges exactly:
two samples of the launcher's **39,761-byte** range and two samples of the
interpreter's **160,721-byte** range. This is **400,964 sampled bytes**, or
**200,482 distinct bytes sampled twice**. It does not assert equality of all
process memory, writable data, BSS, padding or intervening states.

All six narrow flags are true:

```text
kernel_exec_checkpoint_observed
launcher_image_binding_verified
interpreter_image_binding_verified
selected_exec_memory_ranges_observed
selected_exec_rx_ranges_match_original
owned_exec_stop_cleanup_verified
```

The recorded instruction pointer is at the original interpreter entry, and
the wait record identifies `PTRACE_EVENT_EXEC`. The collector records one
pre-exec resume, **zero post-exec resumes**, no detach, and an owned child
killed and reaped after observation. Both owned containers were removed.
The verification phase did not repeat acquisition.

The preservation review also ran the unchanged lower-level capture checker in
two fresh local CPython 3.11.16 processes. Both returned 0 and produced exactly
the original 2,200-byte hosted report. This read-only reconstruction checked
the preserved request, capture and source bindings; it did not freshly verify
distribution or attestation signatures and did not run the collector.

### Hosted attestation

[Attestation 69298068](https://github.com/HKati/pulse-release-gates-0.1/attestations/69298068)
binds `verified-binding.json`, **11,522 bytes**, SHA-256
`e08c4504d77c6b73dd40f6fc38164699583bed9ff82015db7e9f19a5bc2f8e27`.
The original bundle is **11,706 bytes**, SHA-256
`74fdf59f5c309f5415e17045c4de5ddb24d78281005536d5009e628c8a196c55`.
The subject binds the original receipt, request, capture, both equal reports,
source files and run context.

The preserved `gh attestation verify` command returned 0 with the exact
repository, signer workflow, source and signer digest, `refs/heads/main`,
SLSA provenance predicate, GitHub Actions issuer and hosted-runner requirement.
Its verified statement names invocation `44375052171/attempts/1`; the verified
transparency-log timestamp is **2026-11-18 18:57:54 UTC**. The review checked
these retained bytes and their bindings. A fresh local attestation verification
was not performed: the available local `gh 2.46.0` lacks that subcommand.

### Repository selection and separate original custody

The [control evidence selection](../../preservation/required_gate_idempotence_exec_stop_v0/run_44375052171_attempt_1/control_evidence_v0.zip)
is a newly constructed **737,502-byte ZIP**, SHA-256
`788aaa185e979f5ecddfa3b17f8a45d8b74ee59671b26033b5b94c249c9359c6`.
Its **234 members, 1,513,977 decoded bytes**, are unchanged member bytes from
the two original artifacts. The record enumerates each member's original
artifact, path, size and digest. It includes the complete capture tree, request,
receipt, reports, selected process/environment records and attestation evidence.

This selection is not either original GitHub ZIP and is not a complete hosted
replay carrier. It omits the Docker base-save archive, original-input archive,
package/wheel payloads, full source copies and duplicate verification trees.
The retained receipt still binds those omitted dependencies. Replaying the
full hosted verification requires the original artifacts and reviewed tools.
Every added repository file remains below the existing **8 MiB** source-file
budget; no new exclusion or relaxed size limit is needed.

Retain these two separately supplied original files outside the repository:

```text
exec_stop_44375052171_1_acquisition_original.zip
exec_stop_44375052171_1_verification_original.zip
```

Verify their exact sizes and hashes from the table above. Original copies were
verified during this review; receipt on the owner's own machine has not been
observed. Provider retention was recorded as **2027-02-16 18:56:05 UTC** and is
not permanent custody. The smaller repository selection and its hashes do not
replace the original ZIPs. No LFS or additional paid artifact service is part
of this preservation change.

## Next bounded B2 obligation

The selected original launcher/interpreter cp0 observation is complete.
The next B2 development unit is a finite proposal for a later checkpoint that
can establish additional native-object occurrences and actual library
resolution. The four selected images still unobserved at cp0 are `libc.so.6`,
`libcap.so.2`, `libpcre2-8.so.0` and `libselinux.so.1`.

Retain all twelve static relationships with their separate meanings: **nine
`DT_NEEDED` and three `PT_INTERP` relationships**. Only the original
`bwrap`-to-interpreter relationship is required at cp0; the other eleven are
marked `not_observed_at_cp0`. The libc/libcap interpreter declarations do not
imply recursively executed interpreters. A later mapping snapshot alone would
not prove each consumer's loader-resolution relationship.

The next proposal must specify its exact checkpoint and allowed initialization,
owned-process identity, original object/segment bindings, per-relationship
evidence, finite time/event/byte limits, cleanup, failure-prefix preservation
and independent acceptance/rejection checks. Executable entry is later than
cp0 and may follow loader initialization. It therefore needs a separate
observation scope; this preservation change does not implement or authorize
post-exec continuation. Observed containment and selected-bootstrap integration
remain subsequent obligations.

The exact workflow is classified as a non-authorizing audit-preservation
carrier. Changing its reviewed bytes does not inherit that classification.
Neither this implementation nor a completed cp0 observation supplies a
property PASS, selected-runtime execution, a production gate or release
authority. Broad runtime/host/native-closure/containment fields retain their
existing meanings; `metric_pass=null` and `authority_effect=none` remain fixed.

Preserve the original `43514702328/1` verification artifact and both
`43854478248/1` entry-build artifacts. Q2 remains `FAIL 49/50 +1 UNKNOWN`;
all twelve unsupported gates and historical Q3 scope remain unchanged.
The [readiness plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#18-required-gate-coverage-plan-after-accepted-rejection-verification)
continues from the verified mechanical relationships. Later observations may
establish additional relationships, which must be checked on their own evidence.
B3 property evidence, B4 admission, B5 the actual reference, broader Step 6
resource measurement and Step 7 promotion remain outstanding. Keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.
