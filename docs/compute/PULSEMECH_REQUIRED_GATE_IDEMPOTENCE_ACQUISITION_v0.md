# Bounded idempotence acquisition primitives v0

## Status and supported use

**Implemented: selected-source preparation, a bounded worker/process primitive,
and synthetic acquisition orchestration. Observed acquisition remains closed;
B2 is incomplete.** This continuation follows the
[selected protocol](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_PROTOCOL_v0.md) and the
[offline observation adapter](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_OBSERVATION_v0.md).
The public command prepares selected bytes without executing the sanitizer.

The subsequent
[runtime preservation tool](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_RUNTIME_v0.md)
can preserve an independently selected runtime file set, check its static native
bindings and restore exact bytes without execution. It does not integrate the
observed launcher or establish complete runtime closure.

The worker can perform one selected application when called by a future reviewed
launcher. The process primitive supplies immutable inputs and enforces bounded
child execution. The coordinator is exercised through an explicit example-only
runner; it has no default live runner. Its successful carrier remains an
authored example. Preparation and these regressions do not supply an actual
reference, an idempotence verdict, a completed runtime closure or release
authority.

The public `acquire` command rejects with `observed_acquisition_not_ready`.
There is no flag, status edit, caller-supplied launch-grant JSON or digest that
unlocks it. Recoverable runtime closure, its review, integration of the observed
launch route and separate owner authorization must precede actual acquisition.
This is an explicit remaining implementation boundary, not a failed or completed
reference attempt.

| Surface | Responsibility |
| --- | --- |
| [Preparation and coordinator](../../tools/acquire_required_gate_idempotence_v0.py) | Bind selected sources, produce a separate preparation package, assemble synthetic records and preserve incomplete attempts. |
| [Process primitive](../../tools/required_gate_idempotence_process_v0.py) | Launch one fresh child with sealed descriptors, bound its streams and lifetime, stop its owned process group and reap it. |
| [Worker](../../tools/required_gate_idempotence_worker_v0.py) | Install limits and syscall restrictions, read the exact input, load selected modules from memory and call the selected function once. |
| [Acquisition regressions](../../tests/test_required_gate_idempotence_acquisition_v0.py) | Exercise orchestration with authored results and process restrictions with synthetic source modules. |

## Source selection before execution

The caller supplies an independently retained selection and its expected
SHA-256. The existing closed observation selection schema is reused unchanged.
The original protocol, input catalog and observation mapping retain their exact
bytes and original pins. The four selected EPF source files remain bound to
`97ab500bb9936c27632e1f40ab891d2442476786`.

The new implementation selects three additional files:

- `tools/required_gate_idempotence_worker_v0.py` as `worker`.
- `tools/acquire_required_gate_idempotence_v0.py` as `collector`.
- `tools/required_gate_idempotence_process_v0.py` as an implementation dependency.

All three must identify the selected implementation commit and match the
installed acquisition implementation bytes. This commit must actually contain
them; the earlier operator revision cannot be used as their revision. The usual
seven-source selection therefore yields a 98-member observation carrier. The
existing `91 + selected source count` rule remains unchanged.

For observed preparation, every source is recovered from its regular-file Git
blob using the existing offline, transport-disabled lookup. In-memory source
overrides are accepted only for examples. No selected source is imported or
executed during preparation. The internal prepared object is immutable and
carries a private admission created by successful validation; a reconstructed
JSON assertion or directly constructed object cannot recreate it.

Preparation binds the declared environment; it does not inspect or qualify an
actual execution host. Its report explicitly retains
`host_environment_qualified=false` and `runtime_closure_verified=false`.

## One bounded application

The process primitive supports Linux x86-64, CPython 3.11 and Unicode 14.0.0 for
synthetic regression execution. The selected reference environment remains
CPython **3.11.16** as fixed in the original protocol; accepting another 3.11
patch release for synthetic tests does not change that selection.

Each call uses a fresh interpreter with `-I -S -B`, a fixed minimal environment,
no inherited standard input and only the selected descriptors. The interpreter
bytes are read with file-identity stability checks, compared with the caller's
expected digest, copied to a sealed executable memory file and launched from
that immutable copy. The worker, request/source envelope and payload also use
sealed memory files. An opened path or a before/after digest comparison alone
does not make mutable executable bytes immutable.

The original absolute interpreter path remains `argv[0]` for CPython runtime
discovery. When its sibling `lib` exists as a real directory, that single
derived path is the child's `LD_LIBRARY_PATH`; ambient loader paths and
`LD_PRELOAD` are never inherited. Loader-special path characters, symlinks and
non-directory library locations reject. This supports dynamically linked
Python distributions when the executable is launched from a sealed descriptor.
Shared libraries, the loader and standard-library bootstrap are
still host dependencies. This implementation does not claim to have preserved
or independently verified them. The closed observed route prevents this
remaining dependency gap from being represented as a ready reference runtime.

Before any selected module top-level code runs, the worker applies the fixed
CPU, address-space, core-file and file-size limits, drops unrelated descriptors,
sets `no_new_privs` and installs an architecture-checked seccomp filter. The
filter permits a small computation-oriented syscall set, reading the designated
input descriptor and writing the two bounded collector pipes. File opens,
network operations, process creation, execution, tracing and descriptor
duplication are denied. Unsupported platforms or unavailable restrictions fail
closed; there is no permissive fallback.

The selected forecast module tries to load calibration during import. It is
therefore evaluated only after file opens have been denied, using selected
in-memory source bytes and virtual absolute source paths. Its original fallback
behavior remains intact; no ambient calibration or FieldSpec file is loaded,
and the selected source is not patched. Package parents are inert in-memory
containers, not discovered repository initialization files.

Seccomp limits the exposed syscall surface; it is not a claim of complete host
isolation. The implementation still trusts the already loaded interpreter,
bootstrap and collector. See the primary
[Linux seccomp documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)
for the mechanism and its scope.

| Bound | Enforcement |
| --- | --- |
| Worker CPU: 2 seconds | Hard `RLIMIT_CPU`. |
| Worker address space: 256 MiB | Hard `RLIMIT_AS`. |
| Core dumps and regular-file output: 0 bytes | Hard `RLIMIT_CORE` and `RLIMIT_FSIZE`; filesystem opens are also denied after bootstrap. |
| Worker wall time: 5 seconds | Parent monotonic deadline, bounded stream polling and owned-process-group termination. |
| Suite wall time: 180 seconds | Coordinator deadline passed into every application; no next occurrence after expiry. |
| Worker protocol stdout: 20 KiB; stderr: 4 KiB | Bounded parent reads; preserve the permitted prefix and reject overflow. |
| Input: 1 KiB initially, 4 KiB for derived input | Selected catalog and per-application input checks. |
| Snapshot and metadata: 4 KiB each | Worker and parent validation. |
| Applications: 24; attempts: 1 each | Fixed case/phase loop, stop on first failure, no retry or top-up. |

The parent keeps an exited child unreaped until it has stopped that child's
owned process group, avoiding a process-ID reuse interval before cleanup. It
then reaps the child and retains bounded bytes already produced on both pipes.
Resource or stream failure never turns a partial response into a complete
application receipt.

## Exact consumption and carrier assembly

The worker reads the sealed payload after restrictions are installed, computes
its actual byte count and SHA-256 and returns those read facts with canonical
snapshot and metadata bytes. The parent checks response identity, configuration,
complete read binding, canonical encoding, output domain and limits. These are
local acquisition observations, not external attestation of a hostile host.

For each synthetic coordinator case, the first application receives the exact
original bytes including their LF. The second receives the actual returned
canonical first snapshot and its exact state descriptor. The coordinator never
substitutes the original input or a prewritten expected result. All 24 execution
identities and process IDs must be distinct, and the collector is separate.

Only complete successful receipts enter the closed observation carrier. The
existing offline checker must accept that carrier before `acquisition.zip` is
published in the attempt directory. It checks the unchanged per-application
recorded-consumption rules. Unequal first and second snapshots can still be
accepted as a valid relation; this continuation calculates no property result.

Preparation records, stream journals and attempt summaries stay outside the
closed observation carrier. Its membership and schema are not extended, and it
does not contain its own digest or its enclosing manifest. The outer attempt
inventory hashes existing files and excludes itself, preserving an acyclic
binding order.

## Interrupted and rejected attempts

Evidence is written to a new private directory through descriptor-relative
operations that refuse symlink traversal and replacement. Existing directories
are rejected. Directories use mode 0700 and files mode 0600. There is no automatic
deletion, resume, retry, overwrite or publication path.

Before the first application, the coordinator preserves the selection, source
package, preparation report and attempt-start record. Before each application,
it records the selected input descriptor and occurrence ordinal. Raw stdout and
stderr are streamed to bounded files and synchronized while collection proceeds.
Produced snapshot and metadata bytes are retained before semantic/read-binding
checks; only the permitted prefix is retained on an output-size violation.
An occurrence-result journal retains bounded PID, timing, exit and read facts
even when no valid receipt can be produced. It identifies omitted malformed
fields and records observed/retained byte counts, prefix digests and truncation.

The normal terminal `attempt.json` records the attempted and completed prefix,
failure code, failed occurrence, exact file inventory and unchanged authority
boundaries. A failure has no accepted complete carrier. Abrupt process death or
storage failure may prevent the terminal summary from being written; the
already synchronized start/events/raw files remain an unfinished attempt and
must not be interpreted as a complete acquisition. A completed summary alone
does not authorize deleting its evidence.

The example runner is a testing dependency and is explicitly recorded as
synthetic. Its authored process IDs and results are not claims that the selected
operator ran. Independent worker/process tests use tiny synthetic modules in
the selected module positions; they never replace the four original pinned
source bytes in an accepted observed record.

## Preparation command

After selecting an implementation revision that contains these files, retain
the exact external selection and expected hash. This command only reads
existing Git objects and writes a new preparation directory:

```bash
python tools/acquire_required_gate_idempotence_v0.py prepare \
  --selection /absolute/path/selection.json \
  --selection-sha256 SELECTED_SELECTION_SHA256 \
  --repository-root /absolute/path/repository \
  --output-directory /absolute/path/new-preparation
```

The directory contains `selection.json`, `sources.zip`, `preparation.json` and
`preparation_inventory.json`. The source ZIP has its own inventory and original
selected source/companion bytes. It contains no acquired outputs. The JSON
report is also printed; exit 0 establishes source preparation, while exit 1
reports a stable rejection code without echoing untrusted payloads.

No runtime capsule or launcher authorization is generated. Do not treat the
source ZIP, the environment hash or a successful example as a replacement for
the outstanding runtime closure.

## Validation and remaining work

The new regression module is registered once in the Tools manifest. Tools
entries increase from 184 to 185; all dependent live count guards are updated
together. Targeted pytest remains 40. Tests cover exact derived-input flow,
per-occurrence failures, prefix preservation, output and path substitutions,
forged preparations, closed observed launch, and actual Linux process controls
with synthetic sources.

The subsequent runtime preservation implementation supplies closed selected-file
capture, static native bindings and byte-exact restoration. Its separate capsule
does not change this process primitive's live dependencies. Qualification of the
restored bootstrap, dynamic dependency coverage, actual loader-path enforcement,
host review and observed-launch integration remain outstanding. B3 property
calculation and independent reconstruction, B4 admission and B5 separately
authorized actual reference remain subsequent work.

B1 v0, its per-occurrence correction, the existing observation checker/schema,
the historical packet schemas and analyzer behavior remain unchanged. Preserve
the original artifact from `43514702328`, attempt 1; retain historical Q2 FAIL
(49/50 with 1 UNKNOWN), all twelve unsupported gate classifications and the
completed Q3 lineage. Keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

All generated preparation and attempt reports retain:

```json
{
  "execution_ready": false,
  "execution_authorized": false,
  "runtime_closure_verified": false,
  "property_semantics_verified": false,
  "metric_pass": null,
  "actual_reference_claimed": false,
  "production_gate_eligible": false,
  "authority_effect": "none"
}
```
