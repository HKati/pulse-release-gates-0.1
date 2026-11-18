# B2 original launcher exec-stop GitHub observation v0

## Status and scope

**Implemented repository process for one owner-requested original-launcher
exec-stop attempt, preservation of its complete or incomplete evidence, and
independent reconstruction in a separate GitHub job. The first manual GitHub
attempt stopped during offline environment installation, before a request or
capture was produced. A completed original checkpoint remains pending.
B2 remains incomplete.**

This unit continues the
[original launcher exec-stop acquisition](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_v0.md).
That unit established an original-input request and two accepted,
byte-identical preparation reports. It did not acquire an original-launcher
kernel exec checkpoint. The present workflow gives the next observation a
reviewed place in the repository, with fixed inputs, an explicit owner action,
bounded evidence preservation and a separate verification job.

Repository CI checks the implementation and its synthetic failure cases. A
green PR does not supply an original-launcher capture. No original-target
ptrace attempt or retry was performed while preparing this change. A new
manual GitHub run must supply its own observed result; a denied prerequisite
is retained as a denied prerequisite.

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
| First live GitHub attempt | Run `44318024733/1` preserved an incomplete environment-build prefix. A completed original-launcher checkpoint remains pending a new owner-requested dispatch. |

The actual local installer check used a rootless chroot, not Docker. Four
preserved base layers were verified before restoration; file contents, modes
and links were retained, while fourteen layer entries with nonzero UID/GID
were normalized to mapped-root ownership. The unchanged APT installer failed
earlier at its unmapped sandbox UID/GID, so that local baseline did not
reproduce the GitHub pathname diagnostic. The corrected installer completed
without changing its validation guards. A new hosted run must still establish
Docker-build completion and the separate original-checkpoint result.

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
