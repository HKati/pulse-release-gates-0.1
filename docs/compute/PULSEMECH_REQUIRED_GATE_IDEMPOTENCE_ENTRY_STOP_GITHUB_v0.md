# B2 guarded original executable-entry GitHub observation v0

**Status: owner-dispatched run `44740993943/1` completed the selected capability
qualifications, original executable-entry acquisition and separate hosted
verification. Its source, original artifacts and bounded preservation selection
are recorded below. The first run's environment-build failure remains a
separate historical result. B2 remains incomplete; `metric_pass=null` and
`authority_effect=none`.**

This integration carries the
[guarded original executable-entry collector](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_v0.md)
through one manually requested GitHub Actions run. It preserves both capability
qualifications before a fresh original attempt, reconstructs the uploaded
evidence in a separate job and permits attestation only after completed
independent verification and owned outer-container cleanup.

The earlier
[original cp0 observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_GITHUB_v0.md)
and [authored entry plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_PLAN_v0.md)
retain their original bytes and meanings. A terminated historical child is
never resumed or relabelled as the fresh attempt.

## Implementation and evidence roles

| File | Role |
| --- | --- |
| [Manual workflow](../../.github/workflows/required_gate_idempotence_entry_stop_v0.yml) | Require the exact owner, reviewed main commit and first attempt; preserve acquisition and verification artifacts. |
| [Hosted driver](../../tools/required_gate_idempotence_entry_stop_hosted_v0.py) | Bind source, run, environment inputs, artifact handoff and bounded owned-container lifecycle. |
| [In-container runner](../../tools/required_gate_idempotence_entry_stop_hosted_v0/run.py) | Run both capability qualifiers before preparation/acquisition, or independently reconstruct the preserved original capture twice. |
| [Environment selection](../../tools/required_gate_idempotence_entry_stop_hosted_v0/environment.json) | Pin the base, observer, dependency inputs, exact original native objects and container restrictions. |
| [Offline Docker recipe](../../tools/required_gate_idempotence_entry_stop_hosted_v0/Dockerfile) and [builder](../../tools/required_gate_idempotence_entry_stop_hosted_v0/build_environment.py) | Build from selected bytes without network access and verify installed object identities. |
| [Python lock](../../tools/required_gate_idempotence_entry_stop_hosted_v0/requirements.lock) | Retain exact selected wheel versions and hashes without dependency resolution. |
| [Original input selection](../../preservation/required_gate_idempotence_exec_stop_v0/ORIGINAL_INPUTS.json) | Select the existing preserved original inputs and historical source evidence. |
| [Entry preparation adapter](../../tools/prepare_required_gate_idempotence_entry_stop_v0.py) | Repeat original distribution/launch-host admission before preparing, acquiring or checking the selected entry record. |
| [Independent entry checker](../../tools/check_required_gate_idempotence_entry_stop_v0.py) | Reconstruct the original request, qualifications, stopped process relationships, sampled bytes and child cleanup. |
| [Workflow inventory](../../scripts/build_normative_shadow_inventory_v0.py) | Classify only these exact reviewed workflow bytes as a non-authorizing audit-preservation workflow. |
| [Completed-run record](../../preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/verification_record_v0.json) and [control evidence selection](../../preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/control_evidence_v0.zip) | Describe the reviewed successful run and preserve an enumerated selection of unchanged original artifact members; retain the full original ZIPs separately. |

The hosted driver uses the runner's standard-library Python for orchestration.
The selected observer and verification dependencies live in the pinned image.
The existing 72-source entry closure has a separate meaning from the additional
hosted implementation bindings; source copying does not redefine the historical
closure or certify execution.

## Exact native objects and offline environment

The selected base is the existing Linux/amd64 Python image:

```text
docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761
```

The observer remains `/usr/local/bin/python3.11`, CPython 3.11.16, with the
14,472-byte executable binding:

```text
92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79
```

The environment selection binds the original object bytes already present in
the preserved input selection. It does not select newer downloaded substitutes.

| Object | Selected treatment |
| --- | --- |
| Original launcher | Retain `native/bwrap` as input data; the collector creates its sealed memfd only for the explicitly authorized original attempt. |
| Original loader | Require the exact original bytes at `/lib64/ld-linux-x86-64.so.2`. |
| Original libc | Require the exact original bytes at `/usr/lib/x86_64-linux-gnu/libc.so.6`. |
| Original libcap | Install the preserved original at `/usr/lib/x86_64-linux-gnu/libcap.so.2` if absent; otherwise require exact equality. |
| Original libpcre2 | First restore the explicitly selected base revision at its versioned terminal path using the preserved original bytes; retain the exact SONAME symlink, then require original-byte equality. |
| Original libselinux | Install the preserved original at `/usr/lib/x86_64-linux-gnu/libselinux.so.1` if absent; otherwise require exact equality. |

The base loader and libc must already match. The environment selection permits
one explicit preparation step for libpcre2, whose base revision was identified
in the first failed run. Its `native_object_restorations` entry binds the exact
input, SONAME symlink text, versioned terminal path, 0644 mode, and before/after
byte counts and SHA-256 digests. The terminal must be a regular file with one
link under real, pinned parent directories. Unknown before bytes, changed
layout, missing input, extra restoration entries and substitutions reject.

The builder stages the verified original as a new sibling, rechecks the selected
before state and atomically replaces only the versioned terminal. It preserves
the SONAME symlink and records the observed before/after bindings. The ordinary
native-object checks still require exact original bytes. After Debian package
triggers and Python installation, the builder checks the final bytes and
symlink layout again without performing another replacement.

Other installed-object conflicts remain environment-selection failures. The
builder separately records the observation dependencies. Exact paths alone do
not establish identity: byte counts and digests are checked again before the
collector starts its original child, and the collector binds the held file
objects to their stopped mappings.

Selected Debian archives and Python wheels are acquired by the host with their
fixed sizes and hashes. Image construction uses an explicit bounded context
and `--network=none`. The verification job uses the preserved base image and
dependency material from the original artifact instead of silently retrieving
a replacement selection.

Both phase containers use the runner's numeric non-root UID:GID, a read-only
root filesystem, network mode `none`, all capabilities dropped,
`no-new-privileges`, 64 PIDs, 1 GiB of memory, one CPU and a 64-MiB `/tmp` tmpfs.
The repository and originals are read-only mounts; each phase has its own
private writable output directory. The selected default Docker seccomp and
AppArmor policies remain in force. Missing ptrace or compat-syscall capability
ends qualification; it does not select a less restrictive policy.

## Acquisition job: qualify before any original attempt

The workflow accepts only an owner-triggered `workflow_dispatch` in
`HKati/pulse-release-gates-0.1`, repository ID `1061766508`, on
`refs/heads/main`. Both the actor and triggering actor must be `HKati`.
The supplied reviewed commit must equal both `GITHUB_SHA` and
`GITHUB_WORKFLOW_SHA`; the workflow path is checked exactly. Only run attempt 1
is admitted. The concurrency group does not cancel an existing observation.

Inside one owned acquisition container the fixed sequence is:

1. Check the selected environment and exact original objects.
2. Run the separate eleven-case task-guard qualifier and the fixed authored
   hardware-breakpoint qualifier, preserving their available output and process
   diagnostics. Attempt both benign qualifiers when their invocation is possible.
3. Independently require complete qualification records, their selected sources
   and matching kernel, boot, observer and namespace context.
4. Only after both checks succeed, repeat fresh original-chain admission,
   prepare a fresh request and check it independently.
5. Invoke the original collector once with the explicit entry-only
   acknowledgement. Preserve the request, raw capture or available incomplete
   prefix, and all returned diagnostics.

Separate qualification processes share the acquisition container's namespace
context. Qualification records cannot be transferred from a different
container to satisfy this prerequisite. Their completion must precede the
original attempt, and the attempt/child identities remain subject to the
existing freshness checks.

The qualifiers execute authored benign probes. The original collector makes
one setup-to-exec continuation and one cp0-to-entry continuation, then kills
and reaps the owned child without continuing the original executable entry.
Loader relocations, initializers and IFUNC resolvers can execute during the
interval before entry. This observation does not execute the selected metric
runtime capsule or measure Q3.

A failed prerequisite prevents original request/acquisition. Available
qualification bytes still belong to the preserved attempt prefix. A timeout,
changed object, unexpected stop, incomplete capture or cleanup failure cannot
be converted into a completed observation.

## Preserved handoff and independent verification

The acquisition job finalizes a canonical receipt over the available bounded
file inventory, including the original source/environment material and both
qualification records when present. The receipt externally binds request and
capture subjects when they exist. Artifact upload preserves failed prefixes
as well as completed observations; upload success is not observation success.

The verification job selects the artifact by the upload step's exact artifact
ID, repository and current run ID, and checks its externally passed receipt
digest. It reconstructs a private tree from the closed inventory and verifies
every bound file. A receipt for an early qualification failure can establish
which bytes were preserved while still failing the requirements for complete
original observation.

For a published original capture, the separate verification container executes
the public `check-capture` path twice in fresh Python processes. Both checks
repeat original-chain admission and reconstruct the preserved qualification
and capture relations. They do not run either qualifier or the original
collector. The qualification context is the preserved acquisition context;
the verification container's new namespace IDs cannot replace it.

Before those checks, verification also revalidates the preserved acquisition
build record against its receipt binding and the source-bound environment and
lock. Both freshly built phase environments and the preserved acquisition
record must contain the exact selected restoration and observed before/after
bindings. Rehashing changed restoration metadata does not satisfy these checks.

Completed verification requires two accepted, canonical and byte-identical
reports with all selected entry-observation flags true. It also requires the
preserved acquisition container's cleanup evidence and the verification
container's own cleanup evidence. A successful inner-child cleanup does not
stand in for removal of the outer container.

Only then is `verified-binding.json` published as the attestation subject. The
workflow preserves the returned original GitHub attestation bundle and verifies
it against the exact repository, signer workflow, source/workflow commit and
main ref. The signature result remains separate from the byte-reconstruction
result and from release authority.

## Artifacts and inspection

The acquisition artifact is named:

```text
required-gate-idempotence-entry-stop-<run_id>-1
```

The separate verification artifact is named:

```text
required-gate-idempotence-entry-stop-verification-<run_id>-1
```

Both use immutable uploads with 90-day retention. Preserve their original ZIPs
before expiration when the resulting observation is selected for later use.
Repository publication of this workflow does not provide durable custody of a
future Actions artifact.

Review the source/run identity, exact environment and original object bindings,
both capability records and failure diagnostics, fresh request and original
capture, owned cleanup evidence, the two verification reports and the original
attestation-verification result. A green upload step, an accepted incomplete
record or a preserved signature bundle is not interchangeable with the next
verification stage.

## First hosted run: environment-build failure

The first owner dispatch,
[run 44652031252, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44652031252),
used source/workflow commit
`921c1cc935e325f892c962201a170479d4ce1100` on November 20, 2026. The
[acquisition job](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44652031252/job/136009020147)
rejected image construction with `hosted_docker_build_failed`; the preserved
Docker stderr identifies `build_native_host_conflict` inside the offline
builder. The
[verification job](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44652031252/job/136009219046)
then rejected with `hosted_capture_not_published`. Both jobs preserved their
available failure prefixes.

The downloaded acquisition ZIP was checked against the Actions artifact size
and digest before its saved base image was inspected as archive data:

| Item | Binding |
| --- | --- |
| Acquisition artifact ID | `14590659277` |
| Acquisition artifact name | `required-gate-idempotence-entry-stop-44652031252-1` |
| Original acquisition ZIP size | 189,321,198 bytes |
| Original acquisition ZIP SHA-256 | `93c50c648e707123820d28644f5ae8a073ba60731db5ed0ada2dbed55db59da6` |
| Acquisition receipt SHA-256 | `4667ba59a4a0cf791041efebd5677ffc071c345c45635b79eda6691c19d57dbc` |
| Docker build stderr SHA-256 | `e51f6e8ca80d30e3f6a10d9b358089693cb68af04e7c1a77027bfb0419b398a9` |
| Saved base image config SHA-256 | `274d131132dbdc6058ed77088525d77adaf0749a6d99f2cf7d42feb9a10737c8` |
| libpcre2 SONAME link | `/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0` → `libpcre2-8.so.0.14.0` |
| Base terminal object | 711,216 bytes; SHA-256 `8dde125b341abfdf4a596d2974cd3048e350cbc8d2d77acd54ea044f7815ca77` |
| Preserved original object | 711,216 bytes; SHA-256 `92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3` |

The saved base loader, libc, libcap and libselinux matched their selected
original bytes. Only libpcre2 differed. The existing equality check therefore
correctly rejected the selected base; the environment preparation had omitted
this known revision difference. The correction retains both the original
native selection and the pinned base and explicitly selects the one restoration
described above.

The preserved receipt has null task-guard qualification, hardware qualification,
request and capture fields. This run establishes a failed environment build,
not successful capability qualification, entry observation or Q3 measurement.
Artifact bindings and static inspection did not supply a completed observation.
The subsequent owner dispatch below supplies the selected original entry result
after the environment correction.

## Completed hosted observation: 44740993943/1

The second workflow run was a fresh owner dispatch, with **run attempt 1**:

| Item | Recorded value |
| --- | --- |
| Run | [44740993943, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943); workflow sequence 2 |
| Source and workflow commit | [`03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`](https://github.com/HKati/pulse-release-gates-0.1/tree/03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081) |
| Source Git tree | `d202d34ddca7e483f2274404ef72c0ed22e2b774` |
| Event and ref | `workflow_dispatch`; `refs/heads/main` |
| Actor and triggering actor | `HKati` |
| Recorded run interval | November 20, 2026, 13:03:42–13:05:40 UTC |
| Acquisition job | [136304320903](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943/job/136304320903), success |
| Verification job | [136304821660](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943/job/136304821660), success |

The acquisition completed both separate capability qualifications before the
fresh original attempt. The original child reached its live kernel exec
checkpoint and then executable entry in one cp0-to-entry continuation. It
was killed and reaped there without further continuation or detach. The
separate verification job reconstructed the preserved capture and completed
the hosted attestation verification; it did not repeat original acquisition.

The complete capture contains **78 members**, including `capture.json` and its
77 bound evidence members. The accepted reports reconstruct six selected
original ELF objects, 24 `PT_LOAD` segment occurrences, four fresh cp0 RX
samples totaling 400,964 bytes, and twelve entry RX sample occurrences totaling
4,601,548 bytes. The entry samples cover 2,300,774 distinct RX bytes twice.
All nine narrow observation flags are true. The twelve static relationships
(nine `DT_NEEDED` occurrences and three `PT_INTERP` declarations) retain
`consumer_resolution_observed=false`; they are not observations of each
consumer's actual resolution.

Both capability records and their matching acquisition context are preserved.
The task-guard qualifier completed all eleven cases; the separate hardware
qualifier completed its selected trap and owned cleanup. Both phase build
records retain the pinned libpcre2 restoration and final original-object
checks. These selected qualifications do not change the broader
`host_environment_qualified=false` boundary.

The acquisition receipt binds 306 payload files totaling 201,458,840 bytes.
Including the receipt, all 307 acquisition files match both the verification
artifact's `input/` and `private-input/` copies. All 81 source bindings match
the recorded source commit. Receipt acceptance alone remains insufficient to
claim observation completion; the accepted capture reconstruction supplies
that separate result.

### Original artifact bindings

Both original ZIP byte streams were checked against their provider size and
SHA-256 before inspection. The
[descriptive preservation record](../../preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/verification_record_v0.json)
records their inventories and the original member provenance of the repository
selection.

| Artifact | Exact original binding |
| --- | --- |
| [Acquisition artifact 14631066127](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943/artifacts/14631066127) | `required-gate-idempotence-entry-stop-44740993943-1`; **201,576,137 bytes**; SHA-256 `6b393cc38fd04cf1c21012e02cd599d3c4712cf6fb6f55761bbc11270a1b143a` |
| [Verification artifact 14630776595](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943/artifacts/14630776595) | `required-gate-idempotence-entry-stop-verification-44740993943-1`; **450,280,763 bytes**; SHA-256 `a7e00f90b2b23312ef44d139545c9277443cc627d7b1b2ffad6630f41fee2688` |

### Reconstruction and signature verification

The hosted verification result, original signature-verification result and
later local preservation review have separate meanings. Reconstructing the
capture from preserved bytes does not run the original child again, repeat
capability qualification or independently establish the truth of every host
observation. The descriptive preservation record is an inventory, not an
additional independent checker implementation or a grant of authority.

Both original hosted capture reports are accepted, byte-identical and
**12,542 bytes** each, with SHA-256
`e8cbdb4e7f25a4701be1f2b699d96702e077368cc1ddbe1d9ccc8189cb8e6bdd`.
The acquisition checker returned the same report. The two hosted verification
processes also freshly checked the original distribution signature through
the preparation adapter.

[Attestation 70148417](https://github.com/HKati/pulse-release-gates-0.1/attestations/70148417)
binds the 15,533-byte `verified-binding.json`, SHA-256
`6618bbd5fd778d32b87c8b6602c11547dcb4cc8e7cb23dd40e911c63d172d1bf`.
The preserved original bundle is 11,554 bytes, SHA-256
`93ec70cec4943080298dc5203e4b49fb7ff5dd58734be4a3202fe169874b5218`.
The original hosted `gh attestation verify` command exited zero with the
selected repository, workflow, source commit, source ref and hosted-runner
constraints. Its result is preserved alongside the subject and bundle.

Two fresh local CPython 3.12.14 processes using the unchanged lower-level
checker reproduced both original hosted reports byte for byte. This was
data-only reconstruction with jsonschema 4.26.0: no original acquisition,
qualification, native launcher or Docker execution was repeated. Distribution
and attestation signatures were not freshly verified locally. These are two
processes using the same checker implementation, not two independently
implemented checkers.

### Repository selection and separate original custody

The [control evidence selection](../../preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/control_evidence_v0.zip)
is a derived archive of unchanged original artifact members. The descriptive
record enumerates each selected member's original artifact, path, size and
digest. The full original ZIPs retain their own byte identities.

The derived ZIP is **5,682,024 bytes**, SHA-256
`75c71960080a22c88f78b92c8c9af293cc28dc41a4fbd3916e0f515755a245d0`.
It retains **309 unchanged original members** (204 acquisition and 105
verification), totaling 12,819,181 decoded bytes. These include the complete
78-member capture, both complete qualification records and their context,
requests, receipts, source-binding inventories, original checker reports,
signature diagnostics, restoration/build controls, attestation material and
both outer cleanup records.

It omits the Docker base-save payload, package/wheel and separate native
material payloads, original-input transport ZIP, full source copies and
duplicate verification input/private-input/capture trees. The original
receipt retains the omitted acquisition members' exact bindings. Each new
repository file stays below the existing 8 MiB source-entry limit; no source
exception or budget increase is introduced.

The bounded selection is not either original GitHub ZIP and is not a complete
hosted replay carrier. Full hosted verification still requires the original
artifacts and reviewed tools. Retain both original ZIPs outside the repository
and verify their exact sizes and hashes above. Copies were verified in the
review workspace; receipt on the owner's own machine has not been observed.
Both provider artifacts recorded an expiry of **2027-02-18 13:03:43 UTC**.
That retention does not establish permanent custody. No LFS or additional paid
artifact service is introduced by this preservation update.

### Next bounded B2 obligation

The selected original entry observation is complete. The next evidence
obligation is actual per-consumer loader-resolution reconstruction: observing
selected provider mappings does not determine which provider supplied each
consumer relationship. This preservation update implements no later
checkpoint and authorizes no further original execution.

Observed containment, selected-bootstrap integration, B3 property evidence,
B4 admission and B5's actual reference remain separate. The selected metric
runtime was not executed, and no Q3 measurement or complete native closure is
claimed. Keep `metric_pass=null`, `authority_effect=none` and #2879 open under
its existing acceptance conditions.

## Owner launch procedure for a future attempt

The successful run above already supplies the selected observation. Preserving
and reviewing it does not require another dispatch. Any future attempt needs
its own reviewed source and explicit owner decision.

Open
[PULSEmech original launcher entry-stop observation v0](https://github.com/HKati/pulse-release-gates-0.1/actions/workflows/required_gate_idempotence_entry_stop_v0.yml)
after the reviewed commit's CI has completed.
In **Run workflow**, select:

| Field | Value |
| --- | --- |
| Branch | `main` |
| `expected_source_commit` | The full reviewed current `main` commit containing this workflow. |
| `acknowledgement` | `OBSERVE_ORIGINAL_LAUNCHER_ENTRY_STOP_ONLY` |

Check that the selected main commit has not advanced between review and launch.
The explicit manual action authorizes this one bounded workflow attempt. A
later attempt needs a fresh workflow dispatch; **Re-run jobs** creates an
inadmissible attempt number for this profile.

This preservation update performs no dispatch. The completed run's source
identity is historical evidence, not a substitute for reviewing the main commit
selected for a future attempt.

## Validation and authority boundary

The implementation regression results below predate this preservation-only
update. The completed hosted observation and subsequent preserved-byte
reconstructions are recorded above.

Regression tests are appended to the existing containment module, preserving
the current 190-tools / 41-targeted manifest registrations. They exercise
owner/head/attempt gates, qualification ordering and rejection, exact installed
objects, source/receipt/artifact substitution, immutable preservation,
independent replay and outer cleanup using authored records and mocked native
boundaries. These are implementation tests, not a successful hosted capability
qualification or original-entry acquisition.

The environment correction adds 62 regression cases, including the real
SONAME-to-versioned-file layout, rejection of unknown before bytes, atomic
replacement failure, post-trigger layout drift and contradictory restoration
records. All 290 hosted entry-stop cases pass. A separate file-only rehearsal
using the verified first-run artifact's actual base and original bytes
reproduces `build_native_host_conflict`, restores the exact original libpcre2,
and verifies the unchanged SONAME link and other native objects. That rehearsal
runs no Docker build, package installation, qualifier or original ELF.

The full containment regression run passed 1,531 cases. The final 290-case
hosted subset also covers the two consistency checks added during review,
bringing the current containment collection to 1,533 distinct cases covered
across those runs. All 61 normative workflow-inventory tests passed, and the
local Markdown link checker accepted all 349 documents. The 190/41 CI
registration lists and reviewed workflow bytes are unchanged.

The exact workflow bytes are classified as `audit_preservation`, with
`authority_impacting=no`, no required-gate participation and no release-path
participation. Changing those bytes requires renewed carrier review and does
not inherit the reviewed hash's classification.

Provider mapping presence does not establish per-consumer loader resolution.
Capability qualification, selected image/entry relations and provenance do not
establish complete native closure, observed containment, selected-bootstrap
execution, B3 property evidence, B4 admission or B5 actual-reference completion.
The historical Q2 `FAIL 49/50 +1 UNKNOWN`, twelve unsupported gates, Q3 scope
and broader Steps 6/7 retain their meanings. Keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open under
its existing Step 5C acceptance conditions.
