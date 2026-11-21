# B2 original-loader startup and resume acceptance contract v0

## Status and scope

This unit derives the selected original startup-mode decision from preserved
source, debug information and machine instructions. It implements additional
data-only acceptance rules for an authored initial-stack fixture, the nine
original readout fixtures and the separate two-slot transcript fixture.

The development base is `8093121b0f5325f324284588fcb2a09ba09b5dc8`, after
[PR #3044](https://github.com/HKati/pulse-release-gates-0.1/pull/3044).
Historical records, the original entry profile and the readout v0 APIs retain
their existing bytes and meanings.

| Result | Supplied by this unit |
| --- | --- |
| Prior static/readout prerequisite | Fresh reconstruction with the unchanged checkers and complete preserved inputs. |
| Selected startup-mode decision | Conditional source/debug/instruction recipe for ordinary original interpreter startup. |
| Raw initial-stack acceptance | Closed authored-fixture checks for the complete selected argument/environment structure and its process/auxv joins. |
| Return readout acceptance | Both mode fields must be zero at every selected original occurrence. |
| Execution-breakpoint resume acceptance | RF must be set and TF clear at each hardware execution stop; cp0 requires TF clear without fixing RF. |
| Actual original invocation, repeated progression or live qualification | Not acquired or established. |
| Build provenance, original acquisition and B2 | Remain open. |

The source-derived decision is narrower than a proof of the entire program's
control flow or of source-to-binary build equivalence. Its explicit invocation
assumptions and exact selected instruction ranges remain part of the result.

## Unchanged prerequisite and trust direction

The [startup contract checker](../../tools/check_required_gate_idempotence_loader_startup_contract_v0.py)
pins the complete [readout contract](required_gate_idempotence_loader_readout_contract_v0/contract_v0.json)
and its six implementation/schema files. It freshly invokes the unchanged
readout contract checker, which in turn reconstructs the prior original-loader
static binding and historical entry evidence. A saved success report cannot
replace these steps.

The original entry source remains
`03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`; all 81 historical source bindings
remain distinct from this unit's implementation inventory. The old child was
terminated and is not a reusable live prefix.

Complete pinned Debian artifacts are reassembled from the existing preservation
parts. The original loader and matching debug object are selected from their
complete packages. The new source derivation adds selected startup members from
the already preserved original source archive and replays applicable distribution
patches. It does not replace original artifacts with web excerpts or the host's
installed libc.

Before/after implementation-source checks cover both the unchanged prerequisite
and this new checker. Every public verification still requires an externally
selected exact-byte digest for its authored contract. The verification report
records actual implementation-source hashes; it does not authenticate an
otherwise untrusted checker or host.

## Selected ordinary interpreter startup

The selected original invocation remains:

```text
entry route: kernel interpreter startup of the original launcher
argv:        ["bubblewrap"]
environment: LC_ALL=C, TZ=UTC; no additional entries
cwd:         /
AT_SECURE:   0
```

The [static startup helper](../../tools/required_gate_idempotence_loader_startup_v0.py)
reconstructs five additional selected source members: `elf/rtld.c`,
`elf/dl-main.h`, `elf/dl-environ.c`,
`sysdeps/unix/sysv/linux/dl-parse_auxv.h` and
`sysdeps/unix/sysv/linux/dl-sysdep.c`. It scans all active patches and binds the
applicable source ranges, including the auxiliary-vector links into secure-mode
state and the forwarded launcher entry. It connects mode initialization to original
debug offsets and machine instructions, the original dependency-call argument
setup, and the transfer into the existing `openaux` argument structure.

For that selected startup, the expected argument fields are:

```text
trace_mode = 0
open_mode  = 0
```

The original normal/trace enum values, argument registers, frame offsets and
relative call targets are derived from the selected bytes. The integers above
are not chosen from a successful fixture or inferred from a shared library's
filename. The original invocation is interpreter startup, not a direct ld.so
command-line invocation. Initial auxiliary-vector and original ELF relations
must support that distinction.

The resulting static recipe does not authenticate the historical build. It also
does not prove that a new process actually received the selected invocation.
That latter obligation belongs to the future acquisition and is exercised here
only through explicitly authored fixtures. The selected working directory `/`
remains a declared invocation assumption: initial-stack bytes do not establish
the process's working directory.

## Complete bounded initial-stack fixture

The [additional readout checker](../../tools/required_gate_idempotence_loader_startup_readout_v0.py)
uses a separate closed
[invocation schema](../../schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json).
It does not change the old event schema or retrofit new observations into the
historical capture.

The initial stack is interpreted from the raw initial RSP. Its control words
must account for the complete selected structure:

```text
argc = 1
argv[0] pointer
argv terminator = NULL
envp[0] pointer
envp[1] pointer
envp terminator = NULL
complete auxiliary vector, including its terminator
```

The three permitted strings are exactly `bubblewrap`, `LC_ALL=C` and `TZ=UTC`,
each including NUL. Their packed representation has no unaccounted bytes.
Pointer joins, readable stack ranges, paired-sample equality, exact roster and
size limits are checked. An extra argument or environment entry cannot be hidden
by merely presenting the three permitted strings elsewhere in the fixture.
Raw arbitrary environment contents are not an accepted input to this profile.

Initial registers, mappings, auxiliary vector, process identities and pidfd
evidence must agree. Initial RIP is the fresh original loader bias plus its
original ELF entry. The original launcher entry, the interpreter entry and
`AT_SECURE=0` support the selected startup route.

The invocation fixture is joined to the original readout fixture process,
including its attempt, process/observer identity, auxiliary-vector state and
original object biases. The separate inert two-slot probe remains a different
fixture subject. Combining two valid fixture domains does not create one
apparently acquired original process.

## Selected RF/TF rule and unchanged execution boundary

For an accepted hardware execution-breakpoint stop:

```text
(RFLAGS & 0x10000) != 0    # RF set
(RFLAGS & 0x00100) == 0    # TF clear
```

The check masks these two bits; it does not require the whole flags word to equal
one fixture constant. Both stable register samples must agree. At the initial
exec checkpoint, TF must be clear but RF is not fixed: that checkpoint is not
itself the selected hardware execution-breakpoint stop.

The rule is consistent with the x86 execution-breakpoint resume mechanism. For
example, the versioned upstream Linux
[`hw_breakpoint_handler` implementation](https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/hw_breakpoint.c)
sets RF for execute breakpoints to avoid immediately faulting again on the same
instruction. This is a reference for the acceptance rule, not a claim that this
source version identifies the actual future host kernel. The selected host must
still demonstrate the required repeated progression during fresh qualification.

The existing transcript requirements continue to apply: simultaneous DR0/DR1,
exclusive causes, exact probe bytes, DR6 clearing/readback, nine return hits plus
terminal entry for a complete sequence, bounded continuation and owned cleanup.
General-register writes, single stepping, software breakpoints, detach and
post-entry continuation remain excluded. The checker does not repair a fixture
by changing its registers or continue any process.

Every original readout event must satisfy both zero-mode predicates and RF/TF
requirements. A correctly cleaned incomplete two-slot prefix remains incomplete
in the helper and the integrated report.

## Build and acquisition obligations remain explicit

The original source/build gate still needs an accepted and verified evidence
route. Package membership, build IDs, source patches, debug information and the
selected startup recipe do not independently reproduce the binary or establish
authenticated historical build-process provenance.

This unit does not select an unsigned public buildinfo file as authenticated
build evidence, introduce a new signer policy or silently require two separate
build-evidence programmes. The existing unsatisfied gate and its unselected
acceptance route remain unchanged.

The new initial-stack and resume rules are implemented acceptance predicates.
Actual original invocation, contemporaneous backing acquisition, live readout,
same-environment two-slot capability and safe repeated progression remain
unqualified. A complete new collector/capture path, fresh original-input and
environment admission, review and separate owner authorization are still needed.

## Offline verification

From a complete checkout, verify the
[authored startup contract](required_gate_idempotence_loader_startup_contract_v0/contract_v0.json):

```bash
python -I -B tools/check_required_gate_idempotence_loader_startup_contract_v0.py \
  --contract docs/compute/required_gate_idempotence_loader_startup_contract_v0/contract_v0.json \
  --contract-sha256 d4cd7d8183aedf83bb92b92a72c714bc4f5cf333a974611364bc67128c3370e1 \
  --output /tmp/loader-startup-contract-check.json
```

The output is canonical JSON. It is created exclusively after successful
verification; a rejected input cannot publish an accepted result or overwrite
an existing output.

Permanent regressions are appended to the existing registered module:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_startup
```

No original native program, synthetic native probe or collector is executed by
these data-only checks. The original 190 Tools / 41 targeted registrations,
workflows, main README and historical evidence remain unchanged.

Contract acceptance records the freshly verified static startup-mode decision
and implemented fixture/resume acceptance rules. It retains
`original_invocation_observed=false`, `invocation_mode_policy_qualified=false`,
`rflags_resume_policy_qualified=false`, `source_build_gate_satisfied=false`,
`original_acquisition_ready=false`, `b2_complete=false`, `metric_pass=null` and
`authority_effect=none`. [Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open.
