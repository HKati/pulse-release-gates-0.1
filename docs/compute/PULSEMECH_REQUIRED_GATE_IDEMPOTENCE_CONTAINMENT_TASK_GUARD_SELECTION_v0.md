# B2 containment task-guard probe build and context selection v0

## Status and purpose

This unit adds a fixed compile-only build capture and a separately checked input
selection around the [task-guard qualifier](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_QUALIFICATION_v0.md).
It supplies the reviewable build, probe and observer-context records that the
qualifier's external digest arguments need. The development base is
`2351d767980639ccbcfaa5ac72b69a7cf128bdc1`, after
[PR #3063](https://github.com/HKati/pulse-release-gates-0.1/pull/3063).

The build command invokes only the independently selected compiler. It never
executes either output. Selection and independent checking read data only. No
native qualification attempt, startup helper, original launcher, static entry,
selected runtime or container is executed by the development validation of this
unit. No workflow or qualification-attempt adapter is introduced here.

The result is an explicitly selected set of input relationships. It is not
completed native evidence or full-host acceptance. Keep `b2_complete=false`,
`metric_pass=null`, `authority_effect=none` and
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Files and responsibilities

| File | Responsibility |
| --- | --- |
| [Build producer](../../tools/build_required_gate_idempotence_containment_task_probe_v0.py) | Capture two fixed compile-only builds, their actual output bytes and bounded process outcomes in distinct owned directories. |
| [Selection preparer](../../tools/prepare_required_gate_idempotence_containment_task_guard_selection_v0.py) | Independently read the observer context twice and publish one checked selection of build, probe, policy and source identities. |
| [Independent checker](../../tools/check_required_gate_idempotence_containment_task_guard_selection_v0.py) | Reconstruct build and selection relationships without importing either producer or the native qualifier. |
| [Closed schema](../../schemas/required_gate_idempotence_containment_task_guard_selection_v0.schema.json) | Define the policy, build record, selection and two report shapes. Semantic reconstruction remains the checker's responsibility. |
| [Limited build policy](required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json) | Declare the exact recipe and the narrow meaning of accepting a repeated build record. |

The new source inventory contains these five paths and the eleven unchanged
paths bound by #3063. Every earlier qualifier, probe, checker, schema and source
contract remains byte-identical. The preceding startup source contract is freshly
reconstructed; its success is not converted into execution evidence.

## Explicit limited build policy

The selected policy is
`recorded_repeated_probe_build_under_selected_compiler_v0`. Its canonical bytes
have SHA-256:

```text
68f439c03b4c4656ca19263db4eef0eccb35bf44fd9a154b6ec038efa5de474e
```

The caller supplies that accepted policy digest independently of the incoming
build record or selection. Rehashing altered policy content cannot change the
checker's fixed acceptance semantics.

Acceptance requires the exact #3063 probe C source, the externally selected
compiler path and ELF digest, two completed fixed build records, unchanged
source/compiler observations, equal actual output bytes and fresh structural
checks of each ELF and its readonly 272-byte guard section. Matching summaries
or output hashes without the corresponding actual output bytes are insufficient.

This accepts the recorded repeated-build relationship under declared builder
trust. The selected compiler's dependencies remain unverified. The command does
not claim complete compiler closure, authenticated physical build execution,
source-to-binary semantic equivalence or executed startup-helper provenance.
Two directories using the same selected compiler are two recorded repetitions,
not two independently trusted toolchains.

## Fixed compile-only capture

The recipe is fixed: freestanding C11, O2, strict warnings including conversion
and shadow warnings, no libc/builtins/stack protector/PIE/unwind data, static
linking, no build ID, a nonexecutable stack and `_start` as entry. There are no
caller-supplied flags, compiler discovery queries, alternate compilers or retries.

Each build uses `probe.c` and `probe.elf` in its own newly created directory,
`build-1` or `build-2`. The complete environment is:

```text
PATH=/usr/bin:/bin
LC_ALL=C
TZ=UTC
SOURCE_DATE_EPOCH=0
TMPDIR=.
```

The compiler is opened through non-symlink ancestors and retained by an opened
regular-file descriptor. Invocation uses that pinned descriptor while keeping
the selected canonical compiler path in argv. The public compiler identity and
opened bytes are rechecked around the builds. These endpoint observations do
not authenticate every intermediate compiler dependency or kernel operation.

| Bound | Fixed value |
| --- | ---: |
| Build count / retries | 2 / 0 |
| Each compiler invocation / cleanup | 30 seconds / 5 seconds |
| Each stdout / stderr stream | 65,536 bytes / 65,536 bytes |
| Each probe ELF | 262,144 bytes |
| Selected compiler input | 67,108,864 bytes |
| Serialized build record | 2,097,152 bytes |
| Serialized selection | 65,536 bytes |

A failed first build prevents the second. Exit failures, timeout, output
overflow, unresolved reaping, source/compiler changes, differing outputs or
failed output publication cannot produce an accepted completed build.

The compiler runs as an owned session/process group. Bounded cleanup keeps the
leader waitable while submitting group cleanup and then reaps the leader. This
is compiler-process management under the selected builder trust; it is not the
guard qualifier's independently reconstructed multi-task removal proof and does
not establish complete compiler-descendant closure.

The successful preserved directory has exactly these members:

```text
policy.json
build.json
build-1/probe.c
build-1/probe.elf
build-2/probe.c
build-2/probe.elf
```

`build.json` includes both source occurrences, stdout/stderr bytes, process
results, both actual output byte strings, source inventories and the selected
compiler observations. Each retained output is checked against its owned inode
and bytes. Interrupted builds retain their available files and an incomplete
record when publication succeeds. Abrupt process or host loss can still leave
a prefix without a valid record.

Any explicitly supplied build backend is labelled `scripted_build_backend`,
even when it wraps the native backend. Only the producer's default compiler path
uses `recorded_compile_only`. That origin label describes the acquisition route;
it is not cryptographic authentication of the physical process.

## Independent environment selection

The preparer requires a completed, independently checked build record, its
externally expected digest, the chosen output bytes and digest, and the
independently accepted policy digest. An incomplete build is preserved diagnostic
data and cannot become selected execution input.

The preparer reads the exact environment fields used by #3063:

```text
uname
boot_id
observer_executable
python_version
ids
security
lsm_label_hex
namespaces
```

It reads the context independently without importing the native qualifier or
preparing an observer. Equal nonroot real/effective IDs, the declared capability
conditions, single-threaded observation and the exact context shape are checked.
It freezes the first reading, reads again before publication and rejects any
difference. The complete source snapshot is also rechecked before publication.

Boot identity and namespace identities remain exact. A new container, reboot or
namespace change requires a new selection; those fields are never discarded to
make an old selection fit. The snapshot does not authenticate a container image,
outer seccomp/AppArmor configuration or Python dependency closure.

An explicitly supplied environment reader is always `scripted_context`. A
scripted build or scripted context keeps the combined selection
`scripted_selection`. The recorded-build/local-context alternative still sets
`native_execution_ready=false` and `execution_authorized=false`.

The selection binds the full build record, actual chosen probe, full environment,
limited policy, all sixteen source entries and the unchanged qualifier's exact
case list, limits and later acknowledgement. An acknowledgement stored as data
does not authorize execution or authenticate an owner's identity. A selection
identifier is not a global one-use ledger.

## Separate command surfaces

These commands describe the implemented interfaces. They are not instructions
to execute a native qualification during this source PR. Capitalized digests
denote independently selected exact file digests, not values copied from an
untrusted record being checked.

The separate compile-only command requires explicit compiler and policy
selection and the build-only acknowledgement:

```bash
python3 -B tools/build_required_gate_idempotence_containment_task_probe_v0.py \
  --compiler /absolute/selected/compiler \
  --expected-compiler-sha256 COMPILER_SHA256 \
  --policy docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json \
  --accepted-policy-sha256 ACCEPTED_POLICY_SHA256 \
  --acknowledgement BUILD_CONTAINMENT_TASK_PROBE_ONLY \
  --out-dir /absolute/new/probe-build
```

Prepare a context selection without executing a compiler or probe:

```bash
python3 -B tools/prepare_required_gate_idempotence_containment_task_guard_selection_v0.py \
  --build-record /absolute/probe-build/build.json \
  --expected-build-record-sha256 BUILD_RECORD_SHA256 \
  --probe /absolute/probe-build/build-1/probe.elf \
  --expected-probe-sha256 PROBE_SHA256 \
  --policy docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json \
  --accepted-policy-sha256 ACCEPTED_POLICY_SHA256 \
  --out /absolute/new/selection.json
```

Independently reconstruct that selection:

```bash
python3 -B tools/check_required_gate_idempotence_containment_task_guard_selection_v0.py selection \
  --selection /absolute/selection.json \
  --expected-selection-sha256 SELECTION_SHA256 \
  --build-record /absolute/probe-build/build.json \
  --expected-build-record-sha256 BUILD_RECORD_SHA256 \
  --probe /absolute/probe-build/build-1/probe.elf \
  --expected-probe-sha256 PROBE_SHA256 \
  --policy docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json \
  --accepted-policy-sha256 ACCEPTED_POLICY_SHA256 \
  --out /absolute/new/selection-report.json
```

The checker's `build` subcommand checks the build record without requiring a
selection or a current observer context. The independent checker performs no
compiler or subject invocation and retrieves no schemas over the network.
Reports and selections use new output paths; existing files are never replaced.
Two fresh checker processes should produce byte-identical reports from the same
selected inputs and implementation.

## Development validation

Validation on 2026-11-28 used the exact development base above and the final
five-file selection implementation. All **145 new selection/build regressions**
passed, covering independently authored records, altered policy/inputs,
incomplete builds, origin separation, context/source drift, bounded compiler
outcomes, replaced outputs and late publication/close failures. The old
entry-plan, task-guard and qualifier regression selectors passed **576 tests**.
The current-repository normative workflow inventory check also passed: **722
local tests in total**. The existing 1,464,919-byte containment test prefix and
all eleven earlier bound source files remained byte-identical. Validation used
Python 3.12; the three new tools and complete test module also parse under Python
3.11 grammar. Repository CI remains the next check after owner upload.

The build producer performed two real compile-only invocations of the selected
`/usr/bin/x86_64-linux-gnu-gcc-14`. Both completed with exit zero, reaped compiler
leaders, bounded streams and equal 10,504-byte ELF outputs. Neither output was
executed. The selected compiler's dependencies remain outside the acceptance
claim described above.

The preparer then completed a real read-only local-context selection. Two
separate fresh checker CLI processes reconstructed the preserved build and
selection, both exited zero and produced byte-identical 4,532-byte reports with
status `accepted_recorded_guard_selection`. The policy, build record, selection
and both reports validated against the closed schema; its Draft 2020-12
metaschema check also passed. These are development build and input-selection
checks. Every report retains `native_execution_ready=false`,
`native_qualification_performed=false`, `b2_complete=false`, `metric_pass=null`
and `authority_effect=none`.

The original #3064 source delivery contains exactly these eleven repository-relative paths:

```text
CHANGELOG.md
docs/INDEX.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_QUALIFICATION_v0.md
docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_SELECTION_v0.md
docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json
schemas/required_gate_idempotence_containment_task_guard_selection_v0.schema.json
tests/test_required_gate_idempotence_containment_v0.py
tools/build_required_gate_idempotence_containment_task_probe_v0.py
tools/check_required_gate_idempotence_containment_task_guard_selection_v0.py
tools/prepare_required_gate_idempotence_containment_task_guard_selection_v0.py
```

The upload package contains source and documentation only. Compiler outputs,
local-context records and development logs are not repository changes.

### PR #3064 CI runtime follow-up

The first hosted attempt at source
`b80fc7bb3b62e3223302a0dafd05ef748bbfcece` reached the existing two-hour Tools
smoke job limit. In [PULSE CI #7399](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/46140616120/job/140965640683),
the 190-entry script phase completed successfully in 1 hour 50 minutes 37
seconds. Its containment module passed all 4,300 tests in 2,244.62 seconds. The
subsequent 41-entry pytest phase was cancelled after 9 minutes 20 seconds at
41% progress. That prefix is not a completed result for the second phase.

Profiling found repeated parsing and decompression of identical preserved input
bytes in the new selection-test fixtures. The follow-up reuses only immutable
parsed data inside those fixtures. Exact input bytes and every parsing bound
or selection parameter remain part of the cache identity. Successful results
return isolated mutable containers; rejected inputs are not cached. Fixture
patches are restored after each test and bounded caches are cleared at module
teardown.

The field cache retains at most 131,072 successful exact paragraphs; the TAR
cache retains at most eight successful bounded archive decodings. The change
trades test-process memory for repeated parsing work. A representative actual
prerequisite reconstruction took 5.776 seconds without reuse, 5.709 seconds on a
cold cache and 1.786/1.767 seconds on warm calls, with identical reports. The
benchmark's peak resident memory was 915,596 KiB. These local measurements are
not a guarantee of a future hosted job duration.

Source-byte reads and bindings, metadata relationships, schema checks, complete
prerequisite source-contract reconstruction and final report construction still
run on every validation. No acceptance result, source snapshot, digest or report
is cached. The existing 145 selection/build cases and their assertions remain;
additional regressions cover cache isolation and fresh reconstruction.

The correction changes only this document, `CHANGELOG.md` and the appended
selection-test section of `tests/test_required_gate_idempotence_containment_v0.py`.
Production tools, the original test prefix, both manifests, the required check
name and the workflow's 120-minute limit remain unchanged. No probe, startup
helper, original launcher or container is executed by this correction.

The final focused selector passed **162 tests in 355.05 seconds (5 minutes 55
seconds)**: all 145 original cases plus 17 cache-isolation and reconstruction
regressions. The earlier 145-case local development run took 1,237.45 seconds.
The new integration regression compares an uncached real prerequisite report
with two freshly reconstructed reports while recording parser-cache hits.
All 911 preexisting test functions and decorators are AST-identical, and the
1,464,919-byte historical prefix remains byte-identical. The complete hosted
two-phase CI result still requires a new run on the owner's corrective commit.

## Next acceptance boundary

A later attempt adapter must freshly revalidate this complete selection in the
actual observer context, require separate owner authorization, invoke the
unchanged qualifier at most once and preserve the request, attempt and raw
qualification evidence together. No such invocation occurs in this unit.

The [full-host obligations](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md#proposed-finite-budgets-and-host-gates)
remain open, including executed startup-helper/build admission, the original
namespace/mount/openat2 setup, observation through namespace transitions,
separate R/T containment-filter submissions, the original-entry collector and
hosted preservation/replay. Real selected CPython, bootstrap/worker integration
and B2 property evidence remain separate later work.
