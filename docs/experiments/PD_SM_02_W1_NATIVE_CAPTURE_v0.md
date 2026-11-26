# PD-SM-02-W1 — bounded diagnostic acquisition implementation v0

Classification: **Implemented acquisition path; live-container admission and W1 native execution NOT_RUN**.<br>
Preparation base: `2890469ee82333f4d34872bbe711cda6ad9b49aa`.<br>
Subject: `pd_sm_02_w1_diagnostic_healthy_v0`.<br>
Authority effect: `none`.

## 1. Implemented boundary

This implements the producer side of the [preregistered W1 experiment](PD_SM_02_W1_CONTRACT_v0.md),
using the unchanged [offline record checker](PD_SM_02_W1_RECORD_CHECKER_v0.md).
It does not revise the selected candidates, their predictions or normal admission.

| Component | File | Responsibility |
|---|---|---|
| Controller | [`run_paradox_w1_native_v0.py`](../../tools/run_paradox_w1_native_v0.py) | Freeze the exact request; enforce explicit command authorization and single-use local claim; supervise the fixed sequence; retain evidence and replay it offline. |
| External boundary | [`paradox_w1_docker_boundary_v0.py`](../../tools/paradox_w1_docker_boundary_v0.py) | Construct and inspect a restricted local Docker container; bound CLI streams/time; remove the exact container and verify absence. |
| Instrumented runtime | [`paradox_w1_native_runtime_v0.py`](../../tools/paradox_w1_native_runtime_v0.py) | Independently parse and compile exact UTF-8 text, implement the pinned healthy-scenario primitives, collect actual operation returns in separate processes. |
| Record assembler | [`paradox_w1_native_observer_v0.py`](../../tools/paradox_w1_native_observer_v0.py) | Bind process inventory, operation I/O telemetry, wait results, communication records and terminal bytes to the existing record format. |

The runtime never imports or calls the old launcher's private executor. The normal
mapper, checker, launcher, profile and eligible verdicts stay unchanged. There is
no `force` switch in that lane. Only the five frozen diagnostic sources are eligible
for this separate request-bound path; there is no arbitrary-program input option.

## 2. Evidence and trust boundary

The instrumentation is trusted implementation code around actual primitive calls,
not an independent kernel trace. A collector process is separate from the worker
and monitor. The host-side controller is outside all three container processes.
The closed candidate namespace cannot name or replace instrumentation objects;
exact bytes and independent AST/operation reconstruction are checked before launch.
The observer does not load expected verdicts or model witnesses to fabricate events.

The host, local Docker daemon, kernel, selected image and reviewed instrumentation
remain trust roots. The implementation is **not** a sandbox proof for arbitrary
hostile Python, a container-escape proof, platform attestation or third-party validation.
An operator must select a reviewed, credential-free image containing the required
runtime. A digest alone does not demonstrate that an image has no embedded secrets.
No repository, host home, credentials directory or Docker socket is mounted into a
candidate container. The container entrypoint clears inherited environment variables.
Daemon metadata is projected to required fields before preservation; proxy URLs,
registry configuration and image environment values are not copied into the evidence.

Even a future successful capture remains `CAPTURE_COMPLETED_UNATTESTED`. The existing
checker still emits `acquisition_authenticity: NOT_VERIFIED`,
`native_witness_observed: null`, `model_native_correspondence: UNRESOLVED` and
`containment_observed: null`. The controller records its own acquisition and boundary
observations but does not silently promote these to externally authenticated facts.
The offline capture verifier checks internal bindings and replay, not the truth of
an attacker-rewritten complete evidence set.

## 3. Frozen request and authorization

`prepare` first uses the pinned record checker to admit the original W1 inputs.
It copies twenty payloads into a fresh directory outside the repository: frozen
planning/source/evidence files, five sanitized case inputs, and the controller,
boundary, runtime, assembler and unchanged checker source files.

The canonical `request.json` binds every payload digest and length, all five tool
sources, the exact local image ID, runtime profile, containment policy, case order,
maximum five candidate invocations and the two benign supervision controls.
Its digest is printed for review. Preparation never calls Docker, pulls an image,
executes a candidate or grants authorization.

A local image ID must have the exact form `sha256:<64 lowercase hex digits>`.
A moving image tag or registry alias is rejected; `--pull=never` is always used.
No Docker image has been selected, acquired or tested by this delivery.

Execution requires both the exact request digest and the separate command literal
`I_AUTHORIZE_PD_SM_02_W1:<that request digest>`. That literal is an explicit operator
acknowledgment, not cryptographic proof of the operator's identity. A protected
manual workflow/identity integration is not supplied by this change.

Before contacting Docker, execution rechecks the request, all payload bytes and the
currently executing five-file tool closure. It then creates `CLAIM.json` exclusively.
An existing claim or capture directory blocks reuse, including after a failed run.
There is no automatic retry, resume, top-up or substitution. This is local single-use
accounting; copying a request to another machine is not a global anti-replay service.

The host uses only the local Unix daemon endpoint `/var/run/docker.sock`, with an
empty private Docker configuration and a minimal CLI environment. No remote context,
image build/pull, account login, package installation or workflow dispatch is performed.

## 4. External containment and admission controls

The selected profile requires Linux x86_64, cgroup v2 and an image with CPython 3.13.5
at `/usr/local/bin/python3`. Docker is a pre-existing execution dependency, not a new
Python dependency. A different runtime or missing facility blocks acquisition.

| Enforced request setting | Value |
|---|---|
| Container root filesystem | Read-only |
| Effective user/group | `65532:65532`; not root |
| Network | `none`; no ports, devices, host namespaces or added capabilities |
| Capabilities/security | Drop `ALL`; `no-new-privileges`; require active seccomp |
| Inputs | A fresh, read-only `/inputs` mount containing only staged execution inputs/tools |
| Writable experiment files | Fresh `/scratch` tmpfs, 1 MiB, noexec/nosuid/nodev; no host writable bind |
| PID budget | 16 |
| Memory/swap | 128 MiB memory; zero additional swap |
| CPU budget | 0.5 CPU; worker CPU time limit also applied |
| Files/descriptors | 64 KiB file-size limit; 64 descriptors; core dumps disabled |
| Container lifetime | External wall deadline; no restart policy |
| Output | Bounded stdout/stderr; incomplete prefixes retained |

Before starting the container, the controller independently inspects the actual
Docker configuration, image, mounts, labels, limits, entrypoint and created state.
The container cannot invoke a candidate merely by reaching its Python entrypoint:
it first needs the exact `PROBE` message. It then measures runtime/kernel properties,
checks the effective cgroup and privilege settings, and executes fixed benign probes:

- Scratch write/fsync/readback succeeds and is removed.
- Writes at four out-of-bound paths are rejected.
- Only loopback is present and a bounded network-connect probe returns a no-route error.
- Inherited descriptor inventory contains only stdin, stdout and stderr.
- A bounded fork probe reaches the process limit and reaps all its children.
- The file-size limit is exercised; its probe file is removed.

These are live observations required by the future run, not observations claimed
from unit-test JSON. The host validates the readiness payload, reinspects the running
container and rehashes staged inputs before sending the exact `RUN` message. The
observed interpreter-binary digest and kernel identity must remain constant across
controls and cases. A declared Boolean alone cannot trigger that transition.

Before P00, two separate benign containers test the outer supervisor's timeout and
output-limit behavior. They use the same boundary profile but no candidate source.
Each must be stopped and its container removal verified. These controls are not extra
W1 candidate invocations. Failure in either control stops the candidate plan.

The Docker runtime checks and all five W1 cases were **not executed during this
implementation preparation**. The local environment had no Docker CLI. Unit tests
exercise inspection/probe rejection and lifecycle logic with an explicitly synthetic
backend; benign local subprocesses exercise the generic stream/time supervisor.

## 5. Primitive correspondence and operation observation

The native worker compiles the exact decoded UTF-8 text, not bytes, without rewriting
the candidate AST. A wrapper binds each actual primitive invocation to its source
position and arguments, emits begin/end records and invokes its implementation.
The wrapper does not decide the expected outcome or insert omitted candidate guards.

| Pinned native behavior | Diagnostic implementation |
|---|---|
| Ordered request binding | Binding is created at `bind_request`, never hoisted. |
| Source/request/unused guards | Same closure, exact request and request-specific used-state checks. |
| Reservation | Request-specific `used` and `reserved` sets. |
| Broker monitor | A separate child receives the actual request, writes and fsyncs intent, then sends ACK. |
| ACK/audit checks | Bind the same request and digest, not merely a nonempty message. |
| Append | Check request and reservation; perform the real unbuffered append and fsync. Do not insert ACK/audit or single-use guards inside append. |
| Short append | Preserve the actual count, including 0–21 bytes, with normal return when the primitive returns normally. |
| Direct write | Always raise `direct_effect_route_not_admitted` at `direct_sink_write`; never replace it with an effective direct writer. |

The two prior review corrections remain active in the unchanged record checker:
primitive refusal is bound to the reached source operation, and a faithful short
write is retained as a partial effect rather than rejected for its count alone.

Write completion is recorded immediately after the append call returns and before
fsync, including the actual byte prefix and return value. Intent persistence is
recorded after its write and fsync complete. Communication frames preserve actual
sent/received bytes. Process-local sequences and matched communication edges, not
wall-clock timestamps or outer JSON-list order, supply ordering to the checker.

The collector binds worker/monitor spawn records, process IDs, monitor wait status,
worker wait status, stream EOF and final scratch bytes. It records unexpected stdout/
stderr as raw telemetry and refuses to label that case a complete supported capture.
Timeouts, partial traces and missing closure remain incomplete; they are never filled
from the synthetic fixture. In particular N07 requires two write completions, and
N08's write-before-monitor ordering cannot be repaired by matching final audit bytes.

Instrumentation can delay operations through its bounded event pipe. This is an
explicit observation assumption for this fixed healthy, single-request experiment.
It does not add the missing support relation or claim timing invariance for arbitrary
concurrent programs. Live source-to-runtime correspondence remains to be exercised.

## 6. Stop, cleanup and evidence

Candidate order is P00, N01, N07, N08, N02, once each, with a fresh container and
scratch state. The controller supplies each completed record to the unchanged W1
checker before starting the next candidate. A partial effect, prediction mismatch,
failed positive control, missing observation or boundary failure stops the remaining
plan. Subsequent cases remain `NOT_RUN`. A started but unclosed case remains incomplete.

A failed attempt retains the original request, CLI commands and bounded output
prefixes, filtered Docker inspections, readiness/control records, raw operation
frames, terminal bytes when available, cleanup outcome, assembled record, checker
output and summary. A closed manifest covers every retained evidence file except
the root manifest itself. A missing file or a changed byte breaks offline verification.

The controller always attempts removal of the exact created container ID, checks its
request label, and verifies that it is absent from the daemon's container inventory.
A cleanup failure is recorded and stops the sequence; it is not reported as successful
scratch disposal. The local claim remains consumed. Transient staged inputs are
removed after the attempt; their exact bytes remain in the prepared package.

`verify-capture` performs no process or container execution. It rechecks the frozen
request, closed inventory, controller/observer/runtime identities, complete-case
Docker policy records, readiness consistency, cleanup and terminal records, then
reconstructs case records and replays the existing checker. It reports the record
status separately from acquisition authenticity. Hash-consistent fabricated evidence
is still not externally authenticated acquisition.

The output-limit control can stop at its 65,536-byte stdout cap inside a JSON line.
For `probe-output` only, after checking the recorded `output_limit` termination
and sent execution token, replay strictly parses the first complete readiness
line and requires it to match the separately validated readiness record. The
remaining capped bytes are retained unchanged as opaque stress-control output;
the closed manifest still binds every byte. A missing, malformed, mismatched or
incomplete readiness frame is rejected. The general frame parser, timeout-control
transcript and all candidate transcripts retain strict complete-line framing.
This exception does not accept a truncated candidate observation as complete.

## 7. Non-executing commands and later acquisition

These are interfaces, not a claim that a native acquisition has occurred.
The image must be separately selected and reviewed before preparing a real request.
No installation or Windows-local execution is required for this repository delivery.

```sh
# Preparation only, using a separately reviewed, pre-existing exact local image ID.
python -I -S -B tools/run_paradox_w1_native_v0.py prepare \
  --image-id sha256:<reviewed-local-image-id> \
  --run-id <new-run-identifier> --output /tmp/<fresh-w1-package>

# Offline request verification only.
python -I -S -B tools/run_paradox_w1_native_v0.py verify \
  --package /tmp/<fresh-w1-package> --request-sha256 <exact-request-digest>

# Offline verification of a subsequently preserved capture.
python -I -S -B tools/run_paradox_w1_native_v0.py verify-capture \
  --package /path/to/preserved/package --request-sha256 <exact-request-digest>
```

The `execute` subcommand additionally requires `--authorize` with the exact literal
specified in section 3. Publishing this implementation, CI success or earlier pilot
consent does not supply that authorization. A later owner-approved acquisition may
run in a controlled Linux environment after source review and image selection.
There is no Actions workflow or automatic candidate launch in this delivery.

## 8. Regression registration and present result

[`tests/test_paradox_w1_native_v0.py`](../../tests/test_paradox_w1_native_v0.py) is registered
once in both existing manifests: Tools smoke 173 to 174; targeted pytest 29 to 30.
Twelve existing test modules receive count/cross-count updates only, including the
previous W1 regression module. Their functional tests and the old checker are retained.

Recorded local preparation validation: 190 new controls and 267 existing W1 tests
passed on CPython 3.13.5, without skips. The synthetic lifecycle tests do not run
candidate code. Separate benign subprocess controls exercise host time/output limits.
No live Docker, full repository suite or new GitHub CI result is claimed here.

```text
implementation: diagnostic_controller_runtime_collector_and_boundary_available
fixed_record_checker: unchanged
live_docker_admission: NOT_RUN
selected_execution_image: NOT_SELECTED
W1_candidate_executions: 0
native_witness_observed: null
containment_observed: null
execution_authorized_by_delivery: false
authority_effect: none
```

No root README, Technical Overview, frozen W1 planning record, existing native
launcher, historical evidence/archive/checksum, workflow, production policy, gate,
normative status, DOI or Software Heritage material is changed.

## 9. External interface references

The implementation uses the documented Docker create/start/inspect interfaces.
These sources describe interfaces and limits, not validation of this implementation:

- [Docker container create](https://docs.docker.com/reference/cli/docker/container/create/)
- [Docker container start](https://docs.docker.com/reference/cli/docker/container/start/)
- [Docker container inspect](https://docs.docker.com/reference/cli/docker/container/inspect/)
- [Docker runtime options](https://docs.docker.com/engine/containers/run/)
- [Docker Engine security assumptions](https://docs.docker.com/engine/security/)
