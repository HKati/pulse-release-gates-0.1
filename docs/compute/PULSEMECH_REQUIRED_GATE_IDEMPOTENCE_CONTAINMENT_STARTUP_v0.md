# Required-gate idempotence: containment startup helper and task guard v0

## Status and evidence boundary

This unit implements the **startup helper source, exact task-guard policy and
independent source-contract checker** after merged
[PR #3061](https://github.com/HKati/pulse-release-gates-0.1/pull/3061), at base
`92886ff5c6e86729d5a2837c18710d4c274c8fd7`.
The immutable [containment-entry plan JSON](required_gate_idempotence_containment_entry_plan_v0/plan_v0.json)
and its original [source-inventory JSON](required_gate_idempotence_containment_entry_plan_v0/source_bindings_v0.json)
remain unchanged. Their independent checker
is rerun from preserved original carriers during source-contract verification.

The implementation contains real freestanding C and a separately constructed
classic-BPF program. Its validation is data-only and compile-only. **The helper
and original launcher have not been run by this unit.** There is no native
qualifier, task-graph collector or hosted workflow for this new profile yet.
Compiler output and synthetic syscall descriptions cannot satisfy those gates.

The [authored contract](required_gate_idempotence_containment_task_guard_v0/contract_v0.json)
has `record_status=authored_source_contract`. A successful independent report
has `record_status=verified_source_contract`. Only these three claims become
true in that report:

- `startup_source_contract_verified`
- `guard_policy_bytes_verified`
- `prerequisite_plan_reconstructed`

Host qualification, guard installation, helper/launcher execution, containment,
native acquisition, authenticated build provenance, source/binary equivalence,
selected-runtime admission, execution readiness and authorization all remain
false. Keep `b2_complete=false`, `metric_pass=null`, `authority_effect=none`,
and whole-runtime [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
open under its complete scope.

## Implemented components

| Component | Responsibility |
| --- | --- |
| [Startup C helper](../../tools/required_gate_idempotence_containment_startup_v0.c) | Fixed pre-exec phase of L; validate its inherited inputs, wait for exact release framing, install the selected guard and make the one selected launcher exec call. |
| [Pure guard core](../../tools/required_gate_idempotence_containment_task_guard_v0.py) | Assemble exact forward-only classic BPF; provide a data interpreter, independent reference predicate and strict authored two-birth validator. It has no installer or native entry point. |
| [Independent checker](../../tools/check_required_gate_idempotence_containment_task_guard_v0.py) | Compare the authored contract with independently fixed policy, source pins and golden BPF; reconstruct the prior plan from original carriers. Read the new helper/core as bytes without importing either. |
| [Closed schema](../../schemas/required_gate_idempotence_containment_task_guard_v0.schema.json) | Separate the authored contract from its verification report and reject extra keys, type substitutions and altered fixed policy. |
| [Authored contract](required_gate_idempotence_containment_task_guard_v0/contract_v0.json) | Bind the exact current source closure and compile-only recipe; retain the finite budgets and explicit pending native qualification obligations. |

The historical one-tracee installer and checker retain their exact bytes and
meaning. The new policy is specific to the original bubblewrap minimal-entry
profile; it is not an alternate acceptance mode for historical bootstrap runs.

## Exact task-creation policy

The generated program contains **34 instructions / 272 bytes**, with SHA-256:

```text
cc75cb083fb0f6b235eb429384dfb5aaffdd4653891eb2010cd0fd5b6939a51f
```

The C helper embeds those same bytes in the read-only `.pulse_task_guard` ELF
section. The checker has independently selected golden bytes. Regression tests
use a separate BPF interpreter and a direct policy predicate.

The filter requires Linux x86-64, rejects x32, and kills raw `fork` (57),
`vfork` (58), `clone3` (435) and `io_uring_setup/enter/register` (425–427).
It permits `clone` (56) only with one of these complete 64-bit argument shapes:

| Intended birth | Flags | Stack | Other argument conditions |
| --- | --- | --- | --- |
| L → R | `0x000000007e020011` | Full 64-bit zero | Arguments 2–5 are ignored because the selected source's raw clone supplies only flags and stack. |
| R → T | `0x0000000001200011` | Full 64-bit zero | Parent-TID argument 2 is zero; child-TID argument 3 is nonzero; TLS argument 4 is zero; unused argument 5 is ignored. |

High-word substitutions are checked. The child-TID pointer remains dynamic:
nonzero does not establish that it belongs to writable memory of the observed
task. Other native syscalls remain available to the original setup path. This
task-creation layer is separate from the selected 145-instruction containment
BPF delivered on FD 5.

**The kernel filter does not identify L/R/T or limit how often a permitted shape
can occur.** The future observer must check the task role, event order, count,
source-derived arguments and actual child-TID memory relationship at each
consumed syscall-entry stop before restarting that task. The pure
`validate_birth_sequence()` API checks only two authored call descriptions;
successful synthetic data is never accepted as observed birth evidence.

## Startup helper contract

The helper accepts exactly two arguments: its fixed name
`pulsemech-containment-startup-v0` and a canonical decimal expected observer PID.
It uses raw Linux syscalls, without libc, a shell, an allocator or task creation.
Its source contains the one fixed launcher transition described below.

It checks the expected parent before and after setting
`PR_SET_PDEATHSIG(SIGKILL)`, reads back that setting, and rechecks it after
release and before exec. Real/effective UID and GID must each agree and be
nonzero. Both halves of the effective, permitted and inheritable capability
sets must be zero. These checks do not claim capability-bounding-set or ambient
readback.

The parent-death mechanism does not authenticate the observer and is not
retroactive if the parent already died before it was set. It is cleared in
forked children; the later task graph requires the separately observed ptrace
`EXITKILL` and owned cleanup contract. These Linux semantics are described by
the [Linux man-pages project](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html).

### Fixed descriptors

The helper changes cwd to `/`, closes descriptors 8 and above, sets and reads
back descriptor flags, and validates this table before waiting for release:

| FD | Object | Inheritance |
| ---: | --- | --- |
| 0 | Separate empty read-only fully sealed regular input. | Survives launcher exec. |
| 1 | Nonblocking stdout pipe write end. | Survives launcher exec. |
| 2 | Separate nonblocking stderr pipe write end. | Survives launcher exec. |
| 3 | Exact 454-byte NUL-separated argument input. | Survives launcher exec. |
| 4 | Exact 9,568-byte selected static-entry ELF. | Survives launcher exec. |
| 5 | Exact 1,160-byte selected containment BPF. | Survives launcher exec. |
| 6 | Exact 80,248-byte original bubblewrap ELF. | `FD_CLOEXEC`; fixed `execveat` target. |
| 7 | Separate nonblocking barrier pipe read end. | `FD_CLOEXEC`; explicitly closed after successful release and revalidation. |

Regular input descriptors are `O_RDONLY`, optionally with the kernel's
`O_LARGEFILE` status bit, at offset zero and with exactly the four selected
seals (`15`). Every descriptor, including each pipe endpoint, must have the
current task's UID/GID. Regular input modes must not carry set-ID bits.
Exact size and SHA-256 are checked through bounded
`pread64` calls, which preserve offsets; metadata, content and flags are
checked again after release. Pipe roles and regular input roles must each use
distinct objects. Full output-byte caps remain the observer's responsibility.

Local device/inode and metadata comparisons detect substitutions within the
checked snapshots. They do not authenticate the barrier writer, establish
unobserved open-file-description continuity, or prove ownership of another
pipe endpoint. The future observer must bind every relevant identity, seal,
content, access mode, offset and inheritance flag at consumed stops.

### Release, deadline and exec

The release token is the eight bytes `PULSEv0\n`, followed by EOF. A partial
token, wrong byte, suffix, missing EOF, parent loss or timeout fails closed.
The barrier has an independent finite iteration bound. The one monotonic
30-second helper deadline includes setup, both byte validations and release;
it is not restarted between phases. Hashing reads at most 4,096 bytes at a
time, with bounded inner SHA-256 work and deadline checks between chunks.
This avoids adding a clock syscall for each SHA compression block to the
observer's unchanged trace-event budget.

The observer must first seize L with `0x0010001f`, request its interrupt and
consume the resulting stop before releasing the private barrier.
[`PTRACE_SEIZE`](https://man7.org/linux/man-pages/man2/ptrace.2.html) does not
itself stop a task. The helper cannot prove that the correct observer followed
that protocol; an authorized collector and actual stop evidence remain gates.

After descriptor and credential revalidation, the helper closes FD 7, sets and
reads back no-new-privileges, submits the exact new filter once, and reads back
seccomp mode and no-new-privileges. Mode readback does not read back installed
program bytes. The outer observer must independently record the submission
bytes, task identity and successful return.

The final call is exactly:

```text
execveat(6, "", ["bubblewrap", "--args", "3"],
         ["LC_ALL=C", "TZ=UTC"], AT_EMPTY_PATH)
```

It has no path fallback, alternate binary or EINTR retry. The
[`execveat` empty-path contract](https://man7.org/linux/man-pages/man2/execveat.2.html)
selects the object referred to by FD 6; the observer must also check that
descriptor's current selected object and the actual exec transition. No helper
diagnostic or return value can replace the exec event and admitted image.
Failures permit at most one short nonblocking stderr write and then terminate.

## Independent checking and source closure

The contract binds the helper, pure guard core, independent checker and schema,
the exact prior checker/schema, immutable plan/inventory, and unchanged legacy
guard/checker. The checker separately pins the newly reviewed helper/core
source bytes and historical sources. Rehashing an altered contract cannot
select a weaker policy, alternate helper or changed prerequisite.

Verification takes an immutable snapshot of caller-supplied input bytes,
reconstructs the prior plan from its exact 14 original carriers, checks the
clone/ptrace relationships, and verifies that implementation files remain
unchanged. File reads reject symlinked directories, symlink/hardlink inputs,
unexpected file types and changed identities. Report publication is
create-only and preserves any caller-owned replacement on a failed write.

From the repository root, the following is a **data-only checker invocation**.
Select the exact authored-contract digest from the reviewed change before
using it:

```sh
python tools/check_required_gate_idempotence_containment_task_guard_v0.py \
  --contract docs/compute/required_gate_idempotence_containment_task_guard_v0/contract_v0.json \
  --expected-contract-sha256 20a17df1c1307ef5113044335ee70b8aa96d7d68322f1acc1fe5e9a18ba8bf64 \
  --repo-root . \
  --out /tmp/containment-task-guard-source-verification-v0.json
```

The output path must not exist. This command does not install a filter,
invoke a compiler, start a probe, run the helper, launch bubblewrap or dispatch
a workflow. The checker never imports the new helper/guard implementation.
Its schema resolver blocks external retrieval both with the modern registry
API and the older resolver API supported by the repository's
`jsonschema>=4.0` dependency range. The prior plan checker uses its already
pinned source/schema snapshot without changing that checker's acceptance code.

## Compile-only validation

The authored contract contains the exact fixed freestanding GCC recipe.
Tests may invoke the compiler to produce a temporary ELF and then read that
file as data. They never execute the compiler output.

`verify_compiled_helper()` requires a caller-selected exact ELF digest and
checks bounded ELF64/x86-64 `ET_EXEC` structure, an executable entry mapping,
no interpreter/dynamic/TLS program segment, no writable executable load, a
non-executable stack, and the exact guard in a read-only allocated section.
Its result is limited to `static_shape_verified` and
`guard_section_bytes_verified`; source/binary equivalence, authenticated build
provenance, host qualification and native execution stay false.

A malicious compiler could emit different executable instructions while
retaining those structural properties. Consequently, shape success is never
helper-build admission. The later qualifier needs a separately selected
toolchain/build relationship and the exact helper bytes actually executed.

## Regression coverage and unchanged boundaries

New regressions are appended to the existing registered containment test module.
They cover independent BPF semantics, both full-width clone masks, unused-register
handling, wrong architecture/x32 and forbidden syscalls, strict data types,
role/order/count substitutions in authored fixtures, rehashed contract/source
changes, malformed compiled ELF and guard sections, source/input snapshot
continuity, create-only publication and forbidden process/network entry points.

The historical containment-test prefix, both old guard files, prior plan
checker/schema, original authored plan/inventory and **190 Tools / 41 targeted
pytest entries** retain their exact bytes. No workflow or classifier is added.
No complete CI run, native qualification or hosted attempt is inferred from
the local targeted checks.

### Recorded local validation

| Check | Result for this source unit |
| --- | --- |
| New `containment_task_guard` regression selection | 236 passed, including the modern and closed legacy schema-resolver paths. |
| Existing `containment_entry_plan` regression selection | 100 passed. |
| Current-repository unclassified-workflow-drift regression | 1 passed. |
| Helper compilation | Fixed freestanding recipe succeeded; compiler output was inspected as data and never executed. |
| Two fresh source-checker CLI processes | Byte-identical 7,082-byte reports, `verified_source_contract`. |
| Prior-checker snapshot adapter | Same 5,548-byte result as the unchanged original verifier on identical original inputs; no prior source/schema reread. |
| Repository Markdown link check | All local links resolved across 363 Markdown files. |
| Historical source/test/CI boundaries | Exact old guard/checker, plan/checker/schema, plan/inventory JSON, 1,326,369-byte test prefix and both CI manifests preserved. |

The two fresh reports have SHA-256:

```text
ddbfb726eaee81d780de539a9449b54141b13119c5182015718a156d148b9193
```

These are source, policy, parser and compiler-output checks. They supply no
native helper execution, host qualification or completed containment result.

## Next acceptance boundary

The first implementation component is now the separate
[task-guard probe qualifier and independent raw-evidence checker](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_TASK_GUARD_QUALIFICATION_v0.md).
It supplies a fixed 21-case authored probe for the guard, permitted task births,
inheritance and owned cleanup. Its development validation performs no native
execution. It does not execute this startup helper or satisfy the remaining
full-host obligations below; the source contract in this document stays unchanged.

Complete native qualification still requires the full harness and independently
reconstructible raw evidence. It must qualify the exact executed helper/build,
observer, kernel, image and outer security configuration; both clone shapes and
inherited guard denials; the owned barrier/parent-loss protocol; stopped task
birth joins; namespace/mount/openat2 and cross-namespace observation; separate
R/T containment-filter submissions; and bounded cancellation and complete owned
cleanup. Expected denial of an extra user namespace is distinct from failure of
an operation required by the selected setup.

Only after that implementation, review and separate execution authorization can
an actual qualifying attempt occur. The bounded original-entry collector and
hosted acquisition/replay route follow their own acceptance gates. Full runtime
closure, real selected CPython, bootstrap/worker integration and B2 property
evidence remain separate later work.

## Complete change inventory

| Path | Change |
| --- | --- |
| `tools/required_gate_idempotence_containment_startup_v0.c` | New fixed freestanding helper source. |
| `tools/required_gate_idempotence_containment_task_guard_v0.py` | New pure guard builder, interpreter, predicate and authored policy. |
| `tools/check_required_gate_idempotence_containment_task_guard_v0.py` | New independent source-contract and compiled-shape checker. |
| `schemas/required_gate_idempotence_containment_task_guard_v0.schema.json` | New closed authored-contract/report schema. |
| `docs/compute/required_gate_idempotence_containment_task_guard_v0/contract_v0.json` | New exact authored source and compile-only selection. |
| `tests/test_required_gate_idempotence_containment_v0.py` | Append targeted data-only and compile-only regressions. |
| `docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_STARTUP_v0.md` | This source-contract and qualification-boundary document. |
| `docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md` | Add current implementation links without changing the historical JSON. |
| `docs/INDEX.md` | Add the source unit beside its prerequisite plan. |
| `CHANGELOG.md` | Record the bounded implementation and evidence limits. |
