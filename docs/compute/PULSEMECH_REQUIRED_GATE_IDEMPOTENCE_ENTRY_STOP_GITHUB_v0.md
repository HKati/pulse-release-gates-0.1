# B2 guarded original executable-entry GitHub observation v0

**Status: the owner-controlled hosted integration is implemented. Its first
hosted run stopped during image construction, before capability qualification
or original executable-entry acquisition. The selected environment correction
below addresses that preserved build failure; a fresh hosted attempt remains
required. B2 remains incomplete; `metric_pass=null` and `authority_effect=none`.**

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
Artifact bindings and static inspection do not replace a new owner-dispatched
run after the correction is merged and its CI has passed.

## Owner launch procedure after merge

Open
[PULSEmech original launcher entry-stop observation v0](https://github.com/HKati/pulse-release-gates-0.1/actions/workflows/required_gate_idempotence_entry_stop_v0.yml)
after this workflow is merged and the reviewed commit's CI has completed.
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

This implementation change performs no dispatch. The exact launch commit is
selected only after merge; the implementation's development base is not a
substitute for that future reviewed main commit.

## Validation and authority boundary

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
