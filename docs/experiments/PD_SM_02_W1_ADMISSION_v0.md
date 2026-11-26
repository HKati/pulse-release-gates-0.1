# PD-SM-02-W1 — separate environment admission v0

Status: candidate-free admission implementation and selected target; live admission
has not run. Preparation base: `25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5`.
`authority_effect: none`.

## 1. Purpose and implementation boundary

The next operational question is whether a specific Linux/Docker/image combination
can satisfy the existing W1 runtime and boundary requirements. This change supplies
a separate way to answer that question before requesting a native W1 experiment.

The new [admission controller](../../tools/run_paradox_w1_admission_v0.py) calls
the existing `one_container` lifecycle helper only for `probe-time` and
`probe-output`, always with `row=None`. Its request has a separate schema and purpose,
an empty `cases` list and an integer `maximum_candidate_invocations: 0`.
Only `request.json`, `runtime.py` and `observer.py` enter the control container.
There is no candidate source, case input or primitive profile in that mount.

The existing native controller, Docker adapter, runtime, observer and offline
record checker remain byte-identical. The new path does not call native `prepare`,
`execute` or the candidate collector. Native request validation rejects the new
request schema. An accidentally supplied candidate identifier would also fail the
unchanged runtime's empty-case lookup before PROBE/RUN or candidate collection.

The frozen W1 contract, five selected cases, original evidence, historical results,
normative authority path, root README and CI manifests are unchanged. Regressions
are appended to the already registered native W1 test module; manifest entry counts
remain 174 and 30. This is not a repetition of the earlier scratch pilot or W1
implementation deliveries.

## 2. Selected environment and image provenance

The [target record](PD_SM_02_W1_ADMISSION_TARGET_v0.json) selects the standard
GitHub-hosted `ubuntu-24.04` x64 runner class, the local Unix Docker daemon and
cgroup v2. It does not identify a future VM instance. The actual runner image,
source/workflow SHA, run/attempt, host kernel, controller interpreter, Docker daemon
identity/version and container interpreter digest are recorded during the attempt.

The official Python image was selected by read-only inspection of registry metadata
and the Dockerfile at its recorded source revision. The discovery tag is
`python:3.13.5-slim-bookworm`; execution does not resolve that moving tag.

| Identity | Recorded value |
| --- | --- |
| Platform | `linux/amd64` |
| Multi-platform index | `sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419` |
| Platform manifest / pull digest | `sha256:a7cb177dc60dfa77b223192cd0d9e6ce1aac7cf9a569023d68e7c91b6371a718` |
| Config digest / expected local image ID | `sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3` |
| Dockerfile revision | `docker-library/python@3fae0a14ac171f46e47d7ce41567e40524af5bcc` |
| Dockerfile path | `3.13/slim-bookworm/Dockerfile` |
| Inspected Dockerfile SHA-256 | `8ddf061339de82c96b0f8e66480ddcb9f756df838a817a161cf7882425ce58d3` |

Raw registry bytes are preserved in [index.json](PD_SM_02_W1_IMAGE_v0/index.json),
[manifest.json](PD_SM_02_W1_IMAGE_v0/manifest.json) and
[config.json](PD_SM_02_W1_IMAGE_v0/config.json). They were retrieved on
2026-10-31 at 22:54:57 UTC. Preparation checks their hashes, descriptor sizes,
Linux/amd64 selection, source annotation, config digest, absence of declared
volumes and declared Python version. The target record itself is pinned by the
admission controller's `TARGET_SHA256`.

The source declares CPython 3.13.5 and installation at `/usr/local/bin/python3`.
This is source and metadata evidence. No image layer was downloaded or inspected
during preparation, and no upstream build attestation was verified. The actual
interpreter, `/usr/bin/env` entrypoint, runtime probes and boundary behavior remain
to be observed by the live admission attempt.

The hosted workflow separately acquires this exact platform manifest on the host:

```text
docker.io/library/python@sha256:a7cb177dc60dfa77b223192cd0d9e6ce1aac7cf9a569023d68e7c91b6371a718
```

It checks the resulting image ID before admission. There is no tag fallback,
alternate image, retry or image build. The unchanged boundary adapter still uses
`--pull=never`. Host image acquisition is outside the control containers; their
network remains `none`.

## 3. Request, authorization and source binding

`prepare` and `verify` are offline operations. They do not contact Docker, execute
a subprocess, acquire an image or issue an execution authorization.

The package binds six tool sources, the workflow, the target and the three raw
registry records by length and SHA-256. Repository paths and Git blob SHA-1 values
are also recorded. It contains no historical candidate archive or candidate source
payload. The canonical request additionally binds the source commit, run ID,
one-attempt budget, exact image ID, unchanged runtime/policy and two control labels.

The supplied source commit is a declared reference, not independently authenticated
by offline hashing. The hosted workflow checks that reference against checked-out
HEAD, `GITHUB_SHA` and `GITHUB_WORKFLOW_SHA`, and checks the tracked working tree.
The executing tool closure must match the request and packaged bytes on both live
admission and offline replay.

`run-admission` requires the distinct literal:

```text
I_AUTHORIZE_PD_SM_02_W1_ADMISSION:<exact admission request SHA-256>
```

The native W1 authorization literal is not accepted. Admission exclusively creates
`ADMISSION_CLAIM.json`; an existing claim or evidence directory prevents reuse.
This is local single-use accounting, not a global anti-replay service or an
authenticated operator signature. Copying a package elsewhere does not turn the
claim into cryptographic identity evidence.

## 4. Live controls and preserved records

The exact selected host context must be present and agree with the source/attempt
and Ubuntu x64 target before Docker is constructed. Only the nine declared context
fields are accepted; an invalid context is rejected before its values are preserved.
No host environment dump, registry credential configuration or proxy settings enter
the evidence. Docker metadata uses the existing filtered projections.

For each of the two controls, the unchanged lifecycle performs outer inspection,
inner live readiness probes, running-state inspection, staged-input rehashing,
supervision and exact-container cleanup. The existing non-root, read-only filesystem,
scratch tmpfs, disabled network, resource limits and kernel-control requirements apply.
The control's records are replayed immediately before it counts as complete.

| Control | Required result |
| --- | --- |
| `probe-time` | One complete readiness frame; sent control token; external timeout; empty stderr; verified cleanup. No additional runtime frame is accepted as successful control output. |
| `probe-output` | One complete, valid readiness frame; sent control token; stdout limit reached with exactly 65,536 retained bytes; empty stderr; verified cleanup. |

The prior narrow output-cutoff exception is preserved: only the bytes following the
first complete readiness line of `probe-output` are opaque stress output. Every
byte remains manifest-bound. The timeout transcript remains strictly framed.
No candidate observation is processed by this new path.

The two controls must share the observed interpreter hash and host kernel identity.
Each uses a fresh container and scratch state. Failure stops the sequence and
retains available evidence. Starting the second control requires the first control
to have completed and replayed successfully.

The closed evidence inventory contains the summary, allowlisted host context,
projected daemon/image records, two control directories and bounded Docker-command
records. Complete success requires all fourteen expected Docker command records,
exact source/image/request/control arguments, bound output, common staging/capture
parents, distinct containers and verified removal/absence. Partial evidence also
rejects arbitrary commands or a candidate argument disguised by a control label.

## 5. Offline replay and result meanings

`verify-admission` starts no process or container. It checks request/source identity,
the separate claim, the exact manifest inventory, control order, inspections,
readiness, transcript, token, termination, cleanup and relevant command records.
Moving an intact package to another Linux directory is supported; the recorded original
host paths remain evidence, not paths to be executed or opened on the replay host.

| Status | Meaning |
| --- | --- |
| `ADMISSION_REQUEST_PREPARED` | Reviewable zero-candidate request created; no live control executed. |
| `ADMISSION_REQUEST_VALID_NOT_AUTHORIZED` | Offline request verification passed. |
| `ADMISSION_COMPLETED_UNATTESTED` | Both live controls completed and their required records replayed within the trusted implementation. |
| `ADMISSION_STOPPED_WITH_EVIDENCE` | The attempt stopped; retained partial records do not establish full admission. |
| `ADMISSION_RECORDS_REPLAYED` | Offline bindings checked; `admission_status` retains the original completed/stopped distinction. |
| `BLOCKED` | Required request or evidence checks failed. |

A stopped attempt can be internally replayable without being successful admission.
Missing or corrupt retained records can themselves block replay. CLI exit code is
0 for successful preparation/verification or completed admission, 2 for a stopped
attempt (including its replay), and 1 for a blocked validation.

Every result retains zero candidate budget/executions, `execution_authorized: false`,
`native_witness_observed: null`, `containment_observed: null`,
`model_native_correspondence: UNRESOLVED` and `authority_effect: none`.
The host, daemon, kernel, image and instrumentation remain trust roots. Hash binding
does not externally authenticate a completely rewritten evidence set.

## 6. Manual hosted workflow and later experiment

The [manual workflow](../../.github/workflows/paradox_w1_admission_v0.yml) has only
`workflow_dispatch`, one `ubuntu-24.04` job, a 15-minute limit, read-only repository
permission and immutable action pins. It requires owner HKati, main, matching source
and workflow SHAs, first attempt, and the exact acknowledgment
`ADMISSION_ONLY_ZERO_CANDIDATES`. It rejects reruns and supplies no automatic retry.

After this implementation is reviewed and merged, the owner can separately choose
to dispatch **Paradoxon W1 environment admission (manual)** using the exact reviewed
main commit containing this workflow. The old preparation base is not the future
dispatch SHA. Merging, CI success or delivery of these files does not dispatch it.

The workflow preserves preparation, image acquisition, admission, replay and failure
records in `pd-sm-02-w1-admission-<run_id>-<attempt>`. `RESULT.json` can report completed
admission only when all required steps and the matching offline replay succeed.
An absent request, failed pull, partial attempt or failed replay remains incomplete
or blocked. Artifact-upload failure also leaves the workflow unsuccessful.

The later five-case W1 acquisition still requires a separately reviewed final native
request and separate owner authorization. This workflow creates neither. A future
host is a new instance; the existing native path must repeat its own live admission
checks locally. This preserved result is not a portable permission to skip them.

For offline preparation/replay, the available commands are:

```sh
python -I -S -B tools/run_paradox_w1_admission_v0.py prepare \
  --repo-root /path/to/reviewed/source --output /tmp/fresh-w1-admission \
  --source-commit <exact-reviewed-source-commit> --run-id <new-admission-id>

python -I -S -B tools/run_paradox_w1_admission_v0.py verify \
  --package /tmp/fresh-w1-admission --request-sha256 <exact-admission-digest>

python -I -S -B tools/run_paradox_w1_admission_v0.py verify-admission \
  --package /path/to/preserved/package --request-sha256 <exact-admission-digest>
```

The live `run-admission` command additionally requires the distinct admission
authorization and selected host-context record described above. No live Docker
admission, W1 candidate invocation or workflow dispatch occurred while preparing
this implementation. Regression fixtures and lifecycle adapters remain synthetic.

Local preparation validation on CPython 3.13.5 / pytest 8.4.2: 231 retained native
implementation tests, 90 added admission regressions and 267 unchanged record-checker
tests passed, 588 total, with no failures or skips. Python 3.11 grammar checks,
workflow YAML parsing and the seven shell blocks' syntax checks also passed.
These are local implementation checks, not a new GitHub CI or live admission result.

## 7. Primary interface and source references

- [Docker pull by digest](https://docs.docker.com/reference/cli/docker/image/pull/)
- [Dockerfile at the recorded Python-image source revision](https://github.com/docker-library/python/blob/3fae0a14ac171f46e47d7ce41567e40524af5bcc/3.13/slim-bookworm/Dockerfile)
- [GitHub-hosted runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Original W1 acquisition implementation](PD_SM_02_W1_NATIVE_CAPTURE_v0.md)
- [W1 regression module](../../tests/test_paradox_w1_native_v0.py)

External documentation describes platform interfaces. The three preserved registry
records establish the selected metadata identities; neither source replaces the
pending live admission observations.
