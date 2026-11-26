# B2 loader two-slot hosted qualification v0

## Status and scope

**Selected hosted qualification completed:** owner-dispatched run
[`45253188286/1`](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286)
at source `624713608bcf5467c6d4be44cd026f906c45f274` completed the fixed native
probe, separate hosted replay, owned-container cleanup and hosted attestation
verification. The [completed result and preservation](#completed-hosted-qualification-452531882861)
below retain its exact scope. Original-loader acquisition, source/build
acceptance, future-host admission and B2 completion remain open.

This unit supplies a separate, manual GitHub execution and preservation route
for the existing fixed synthetic two-slot probe. It builds on the unchanged
[raw qualification implementation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_QUALIFICATION_v0.md)
and [request/attempt adapter](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_ACQUISITION_v0.md).
The implementation base is main commit
`7a82e5721629981206a50d1aae8f9ecc1d3fb629`, containing merged #3049.

Adding or merging this unit does **not** execute the workflow or establish a
successful hosted qualification. Implementation tests use authored records and
mocked host commands. A later owner-requested dispatch must select the actual
reviewed main commit containing this new workflow. No future run, artifact,
image, container, request-context or qualification digest is predetermined.

The workflow is
[`required_gate_idempotence_loader_two_slot_qualification_v0.yml`](../../.github/workflows/required_gate_idempotence_loader_two_slot_qualification_v0.yml).
It has only `workflow_dispatch`. That implementation left existing workflows,
CI manifests, original launcher collectors and the main README unchanged.
The workflow never selects the
original launcher, original package archives, native overlays, Q2/Q3 workloads
or model payloads. The complete whole-runtime scope of issue #2879 stays open.

## Execution and verification boundary

| Stage | Permitted work | Completion evidence |
| --- | --- | --- |
| Acquisition host | Select exact reviewed sources; obtain six pinned wheels and the pinned Python base; preserve those inputs; build offline; start one restricted container. | Git blob checks, preserved materials and command records, actual image/container inspections. |
| Acquisition container | Prepare its own live context-bound request; invoke the fixed probe once in a child process; run the unchanged attempt checker twice. | Original request, attempt receipt, qualification bytes and two identical canonical native reports. |
| Independent verification host | Verify the current-run artifact ID/digest and externally selected receipt digest; copy the checked artifact privately; load the preserved base and rebuild offline. | Exact artifact/source/input bindings, fresh container policy and owned cleanup. |
| Independent verification container | Run only two fresh instances of the existing data-only attempt checker against the preserved acquisition request and records. | Two canonical reports identical to each other and to the acquisition reports. |
| Hosted attestation | Sign only the completed verified binding; preserve and verify the original attestation bundle. | GitHub statement signature tied to the selected repository, workflow and source commit. |

The producer requires an observer PID of at least two. Docker's entrypoint is
therefore a bounded supervisor, not the producer. It starts exactly one fixed
`run.py probe` subprocess. That child prepares the request and invokes the
unchanged adapter in the same process. The producer retains its existing
single-thread, default-SIGCHLD, open-stdio and owned-child cleanup checks.
The verification entrypoint does not import the adapter or producer.

The probe remains the fixed 138-byte static ELF: nine accepted return stops at
the first hardware slot, one terminal stop at the second, eleven continuations
including entry and no resume after the terminal stop. The existing checker
owns register, RF/TF, raw-operation, process-identity and cleanup reconstruction.
This wrapper adds no alternative mechanics engine.

## Closed owner, source and run selection

Both jobs require all of the following before work proceeds:

- Repository `HKati/pulse-release-gates-0.1`, repository ID `1061766508`.
- Actor and triggering actor `HKati`, event `workflow_dispatch`, ref
  `refs/heads/main`, and run attempt exactly one.
- Positive real GitHub run ID and run number.
- The supplied 40-character lowercase source commit equal to both `GITHUB_SHA`
  and `GITHUB_WORKFLOW_SHA`, with the exact new workflow path on main.
- Acknowledgement `QUALIFY_LOADER_TWO_SLOT_ONLY`.

The request ID is derived from the complete validated hosted context and
profile. It is checked against the request and all reports. This prevents a
different run's otherwise valid native attempt from becoming the selected
attempt. The native expected context itself is read independently by the probe
before invocation, not reconstructed from the arriving qualification record.

The selected source closure contains exactly eighteen files: the eight existing
request/attempt sources, this new workflow, the new outer controller and hosted
checker/schema, five environment/runner files, and the unchanged bounded I/O
helper. Before downloads or builds, the host checks checkout HEAD and each
selected file's Git blob identity against the reviewed commit. It saves
`source-bindings.json` and copies the selected bytes under `source/`.

Only that selected source copy is mounted at `/repo`. The complete checkout and
original launcher artifacts are not mounted. The readonly control file binds
the source selection, actual image ID, exact environment and hosted context.
Finalization preserves the original prelaunch selection; it never replaces it
with a newly computed selection after a source change.

## Pinned environment and offline reconstruction

The environment uses the already selected Linux/amd64 Python 3.11.16 base:

| Selection | Exact binding |
| --- | --- |
| Registry reference | `docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761` |
| Base image/config | `sha256:274d131132dbdc6058ed77088525d77adaf0749a6d99f2cf7d42feb9a10737c8` |
| Observer | `/usr/local/bin/python3.11`, 14,472 bytes, SHA-256 `92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79` |

The six wheel versions are `attrs==26.1.0`, `jsonschema==4.26.0`,
`jsonschema-specifications==2025.9.1`, `referencing==0.37.0`,
`rpds-py==2026.9.1` and `typing_extensions==4.16.0`. Their exact filenames,
lengths, URLs and SHA-256 hashes are selected in
[`environment.json`](../../tools/required_gate_idempotence_loader_two_slot_hosted_v0/environment.json)
and the hash-required lock file. PyYAML and all original native dependencies are
excluded from this qualification environment.

The acquisition host preserves the base with `docker image save` and retains
every exact wheel byte stream. Both image builds use a selected local base tag,
`--pull=false`, `--no-cache` and `--network none`. The build helper checks the
environment and lock bindings, interpreter version/executable bytes, complete
wheel roster and installed versions. Pip uses no index or dependency
resolution. Inputs are checked again before the build record is published.

The verification job uses the preserved base archive and wheels. It has no
registry or dependency-download fallback. GitHub artifact-metadata and
attestation verification are separate authenticated service operations; they
do not authorize dependency replacement. Acquisition and verification image
IDs are retained as separate actual values. Equal image IDs or reproducible
image construction are not claimed.

## Runtime containment and cleanup

The actual container inspection must match the selected command, entrypoint,
image, unique name, source/run/profile/phase labels, nonroot runner UID:GID,
environment and mounts. Among the bind mounts, the source/control mounts and
verification input are readonly; only the phase's output directory is writable.

The runtime policy fixes a readonly root filesystem, network `none`, dropped
capabilities `ALL`, no-new-privileges, Docker default seccomp/AppArmor, PID limit
64, one GiB memory, one CPU, and `/tmp` as
`rw,nosuid,nodev,size=64m`. No privileged mode, `SYS_PTRACE`, unconfined policy,
automatic retry or relaxed-policy fallback is offered. If the selected hosted
runner cannot perform the probe under this policy, the result remains an
incomplete qualification with diagnostic evidence.

Both phases select `--security-opt apparmor=docker-default` explicitly when
creating their container. Docker can leave an implicit default profile empty
in the inspection of a container that has not started. Explicit selection
keeps the required profile visible before execution; the controller and the
independent checker still require `AppArmorProfile=docker-default` at both
prestart and terminal inspection, plus exactly the selected AppArmor and
no-new-privileges options. Empty, custom or unconfined profiles are rejected.

The first hosted attempt,
[run 45079210493/1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45079210493),
at source `a6babb55284ad914c9feb2e041fc2b8ec624aa68`, stopped with
`two_slot_hosted_container_defaults` while its container was still `created`.
No probe was started. Owned removal and a successful absence check completed;
the verification job rejected the preserved incomplete prefix and skipped
attestation. The regression fixtures retain the original container inspection
and plan bytes from acquisition artifact `14776900777`, whose archive SHA-256
is `ea65d7af5e10166afb3e914ea849f7968d3305bd7882d297eb8d10c5e03dcbed`.
Any modified inspection used by the regression tests is an authored case,
not evidence of a later successful qualification. The fresh reviewed-source
attempt `45253188286/1` below records the actual outcome after the correction;
it does not change the earlier incomplete result.

A successful completed result requires actual terminal state with exit code
zero, no OOM and no Docker state error. The controller then verifies container
ownership before force-removal and obtains a successful full-ID listing that
shows absence. A failed inspect alone is not proof of absence.

Cleanup has its own bounded budget. It still runs after a command timeout or
failed create response, recovering and checking the selected container's
identity where possible. Terminating the Docker client alone is not treated
as container cleanup. Both acquisition and verification must satisfy their
separate cleanup checks before a completed verified binding is published.

## Preservation and independent checking

Each job creates `workflow-start.json` before checkout. Once an acquisition
prefix exists, upload runs under `always()`. When checkout is available,
finalization also runs under `always()` and binds the available acquisition
prefix in `receipt.json`, whether complete or incomplete. If checkout itself
fails, the available workflow prefix can still be uploaded without a receipt.

The acquisition artifact is named
`required-gate-idempotence-loader-two-slot-<run-id>-1`. The verification artifact
uses the corresponding `-verification-<run-id>-1` name. They retain evidence for
90 days under the workflow's artifact settings.

The finite allowed file roster includes selected sources/materials, fixed
command records, control files, container inspections, cleanup and observation
outputs. It rejects unknown paths, symlinks, traversal, changed content and
duplicate entries. Limits are 256 files, 256 MiB per large file and 512 MiB
aggregate; critical JSON controls are at most 64 KiB. Generic bounded command
diagnostics may contain finite elapsed-time floats, while protocol controls
remain duplicate-free, integer-only JSON.

The receipt does not bind itself. Its external SHA-256 is passed through the
job output. The verifier requires that digest plus the exact artifact ID and
artifact digest, and checks GitHub artifact metadata against the selected
repository, source, run and name. It then validates the entire original
preservation and makes a private copy before reuse. The original and private
input directories are outside the verification artifact directory; the
verification result binds the separately retained acquisition artifact.

Preservation acceptance alone is not qualification completion. A prefix with
no source selection, no container, failed admission, an incomplete native
attempt, a changed request, a scripted origin, a failed command, unequal
reports or unproven cleanup cannot produce a completed binding. The verifier
returns nonzero for an incomplete prefix and preserves its diagnostics.

The two new outer tools use the existing hardened request/attempt writer for
small protocol controls. Exact content, object identity, syncing and close
failures are part of publication acceptance. A failed completed-control
publication cannot leave an accepted completed control behind.

The acquisition container writes:

- `observation/request.json` and `observation/attempt/{request.json,attempt.json,qualification.json}`.
- Two separate `observation/attempt-check-*.json` reports and bounded command records.
- `observation/acquisition-summary.json`, whose status is derived from actual results.

The verifier container writes two fresh checker reports and
`verification/verification-summary.json`. It uses the preserved original
request and expected context; it neither resamples the verification host as
the original expectation nor reacquires the probe. The host validates the
fixed commands, native report fields, all bindings and actual runtime policy.
All four canonical report byte streams must agree for completed verification.
Only the pinned container checkers execute the mechanics validator; the host
does not depend on an ambient `jsonschema` installation.

## Hosted attestation

Only a successfully published `verified-binding.json` can reach
`actions/attest`. The verification job alone has OIDC and attestation-write
permissions. All actions are pinned to the selected full commit IDs.

The original bundle is preserved. `gh attestation verify` checks the exact
repository, signer workflow, signer/source commit digests, main source ref,
SLSA provenance predicate, GitHub OIDC issuer and hosted-runner constraint.
The subject and bundle are rechecked after verification. Credentials are
passed through process environment only; no raw environment or token is
included in preservation records.

This attestation authenticates the hosted verified statement. It does not
authenticate every physical event claimed by the native record, admit a
future host, satisfy original source/build policy or grant release authority.

## Completed hosted qualification: 45253188286/1

The owner dispatched
[workflow run `45253188286`, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286)
on 2026-11-23 from `main`, selecting source and workflow commit
[`624713608bcf5467c6d4be44cd026f906c45f274`](https://github.com/HKati/pulse-release-gates-0.1/tree/624713608bcf5467c6d4be44cd026f906c45f274)
and acknowledgement `QUALIFY_LOADER_TWO_SLOT_ONLY`. Both the acquisition job
and the separate replay/attestation job succeeded. The eighteen selected source
files retained by both artifacts match that commit byte for byte.

### Selected native result and cleanup

The preserved request ID is `64a4bed1dd7e6f06333c42db52d5622e`. Its attempt
records one producer invocation with origin `native_owned_probe`, completed
mechanics and no scripted reconstruction. The fixed 138-byte ELF reached nine
accepted return stops at the first slot and one terminal stop at the second.
The raw record accounts for eleven continuations and zero post-terminal
resumes; the owned child was terminated and reaped.

The original qualification record is **122,939 bytes**, SHA-256
`4a68980210242eed77ebad836171bb4edc1f6ff3c912d61a5991176b76b422b7`.
Both acquisition reports and both separate verification reports are
byte-identical: **1,366 bytes** each, SHA-256
`656aa821bf6f9a7a89168b02bb55565a03c354133400a7937cb37a0158931fca`.
Their accepted status is `accepted_native_qualification_attempt`. These are
four processes using the same unchanged checker implementation, with the two
replay processes running in the separate verification environment.

Both phases selected `apparmor=docker-default` explicitly. Their prestart and
terminal inspections report `AppArmorProfile=docker-default` and the exact
`no-new-privileges` / `apparmor=docker-default` option pair. Both containers
terminated with exit code zero, no OOM and an empty Docker state error. Each
phase then verified ownership, successful removal and absence; both cleanup
records contain an empty error list. This records the selected runtime policy
and cleanup checks without granting general host or future-context admission.

### Original artifact and attestation bindings

Both complete original ZIP byte streams were checked against their provider
sizes and SHA-256 values before the preservation selection was made.

| Artifact | Exact original ZIP binding |
| --- | --- |
| [Acquisition artifact 14855273661](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286/artifacts/14855273661) | `required-gate-idempotence-loader-two-slot-45253188286-1`; **131,031,858 bytes**; SHA-256 `0e2c4fb0b15ba66913014959a8eaceb1fc9d2cfe4b4702b35a6103a22977226e` |
| [Verification artifact 14856708803](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/45253188286/artifacts/14856708803) | `required-gate-idempotence-loader-two-slot-verification-45253188286-1`; **1,276,240 bytes**; SHA-256 `a46d8bee7504f112ee9469559ed684dd25fa463f4449ec59c0cb37531846c48e` |

The external acquisition-receipt SHA-256 is
`89cca33cdcd41baf35ff00471485529c8f65d845fba347982c5cb926c5cd4221`.
The completed `verified-binding.json` is **6,220 bytes**, SHA-256
`151b936a8295dc38a28541ef9c784783376e5a98f36ac13052482c025901b52d`.
Its original attestation bundle is **11,770 bytes**, SHA-256
`ace2d948b5d72588f01d49f1bb52fd664ae7b4f64562e689d9c0b3287b31c31d`.
The original hosted `gh attestation verify` command exited zero with the
selected repository, signer workflow, source/signer digests, main ref and
hosted-runner constraints. The bundle, subject, verification command and
accepted verification record are preserved together. This authenticates the
hosted statement within its recorded boundary; physical-event authentication
and original source/build acceptance remain false.

### Repository selection and local reconstruction

The [control evidence selection](../../preservation/required_gate_idempotence_loader_two_slot_qualification_v0/run_45253188286_attempt_1/control_evidence_v0.zip)
retains **255 unchanged original members**: 129 from acquisition and all 126
from verification. The derived ZIP is **1,603,965 bytes**, SHA-256
`79d623d5277dee4e8c5c0552f74f1e0f069b689409be5b4de9a828d40e946e53`.
It includes the complete native request/attempt/qualification,
all four hosted reports, both eighteen-file source copies, wheel and environment
materials, command and container records, receipt and handoff, cleanup and
attestation evidence. The
[descriptive preservation inventory](../../preservation/required_gate_idempotence_loader_two_slot_qualification_v0/run_45253188286_attempt_1/verification_record_v0.json)
records the archive binding and every member's original artifact, path, size
and digest. That inventory is not an additional independent checker report.

The only omitted original member is acquisition
`host-commands/base-save.stdout.bin`, **129,640,960 bytes**. Its exact binding
remains in the unchanged acquisition receipt and preservation inventory. The
derived ZIP is neither original GitHub ZIP and is not a complete hosted replay
carrier. Complete hosted replay requires the full original acquisition,
including that base-save payload, and the separate verification evidence.

Two fresh local processes of the unchanged attempt checker reproduced all four
original hosted reports byte for byte. The local review used CPython 3.12.14 and
jsonschema 4.26.0. It also revalidated the complete acquisition receipt and
completed acquisition, and the unchanged hosted checker reproduced the original
6,220-byte `verified-binding.json` exactly. All 130 acquisition and 126
verification member bytes and modes remained unchanged.

The outer binding checker enforces the recorded absolute private-input mount,
`/home/runner/work/_temp/required-gate-loader-two-slot-verification-45253188286-1-private-input`.
The review restored a byte-identical regular-file copy of the full acquisition
at that exact path for the data-only join, then removed the temporary copy and
the parent directories it had created. The lower-level attempt replay remains
separate from this outer path requirement. No evidence or checker was rewritten
to accept a relocated mount.

This was preserved-data reconstruction: the native probe, original launcher and
Docker execution were not repeated. Execution in the original container image
and fresh local attestation-signature verification are not claimed. The
preservation inventory records these local checks separately from the original
hosted results and signature-verification command.

Retain both full original ZIPs outside the repository and verify their exact
sizes and hashes above. Review-workspace copies were verified; receipt on the
owner's own machine has not been observed. Both provider artifacts recorded an
expiry of **2027-02-21 19:51:03 UTC**. Their provider retention is not permanent
custody. No LFS, source-budget increase or additional paid artifact service is
introduced by this preservation update.

### Remaining original-loader work

The selected synthetic qualification is complete within its recorded context.
It does not execute the original launcher or establish its per-consumer loader
resolution. The accepted original source/build evidence route, fresh original
admission, complete collector/capture/checker implementation and separately
authorized original observation remain open. The nine synthetic return stops
are not nine observed original dependency resolutions.

The earlier original entry-stop result and failed first two-slot attempt retain
their own identities. Complete containment, selected-bootstrap integration,
B3 property evidence, B4 admission and B5 actual reference remain separate.
Keep `b2_complete=false`, `metric_pass=null`, `authority_effect=none` and
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open under
its full whole-runtime acceptance conditions.

## Owner sequence after review and merge

1. Review the files-only change and its mocked/data-only tests; merge it through
   the normal PR path.
2. Separately decide whether to run this new manual qualification workflow.
3. If running it, select `main`, supply its exact reviewed commit containing
   this workflow and acknowledgement `QUALIFY_LOADER_TWO_SLOT_ONLY`.
4. Inspect the acquisition artifact, independent verification artifact,
   command/runtime/cleanup records and attestation verification. A failed
   prerequisite is a preserved incomplete result, not a reason to relax policy.
5. Record the actual evidence and its narrow selected-context scope before
   deciding the next original-loader step. No run of the original launcher is
   authorized or performed by this workflow.

## Unchanged authority and project obligations

The hosted selection, summary, receipt, verification and failure records retain
the existing boundary and add `selected_runtime_executed=false`:

| Field | Value |
| --- | --- |
| `original_native_acquisition_performed` | `false` |
| `original_acquisition_ready` | `false` |
| `source_build_gate_satisfied` | `false` |
| `consumer_resolution_observed` | `false` |
| `physical_execution_authenticated` | `false` |
| `current_host_admission_satisfied` | `false` |
| `selected_runtime_executed` | `false` |
| `b2_complete` | `false` |
| `metric_pass` | `null` |
| `authority_effect` | `none` |

`selected_runtime_executed` refers to the original selected subject, not the
synthetic qualification child. A native-record reconstruction remains a
claim about its selected recorded context.

The accepted original source/build policy route, original invocation selection,
full occurrence/terminal coverage, collector exclusion and nonmutation,
original capture/preservation/independent replay, and canonical synchronization
remain separate obligations. Step 5C retains its complete whole-runtime scope;
the R/C, M and policy obligations of later steps are not collapsed into this
qualification. Historical Q2 `FAIL` (49/50 with one `UNKNOWN`) and the twelve
unsupported cases are unchanged. Keep #2879 open.
