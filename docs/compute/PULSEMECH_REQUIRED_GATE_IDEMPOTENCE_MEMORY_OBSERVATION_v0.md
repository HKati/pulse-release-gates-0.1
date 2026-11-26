# Fixed-probe private-memory transition observation v0

## Measured relationship and scope

**A separate fixed authored probe connects one retained sealed executable
object, its kernel-reported mappings and two selected ranges of actual process
memory at two cooperative stops. One bounded continuation writes one specified
data byte. The executable backing bytes and object identity remain unchanged
while the selected private data page changes.**

This extends the [stopped mapping observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_MAPPING_OBSERVATION_v0.md).
That earlier profile identifies the executable backing object at one stop and
never resumes its child. Its source files, original captures and conclusions
remain unchanged. The present profile has a new probe, a new source selection,
two stops and explicitly sampled virtual-memory bytes.

The question is concrete: **does an unchanged sealed backing object establish
unchanged selected process-memory bytes across this transition?** The retained
observations answer each part separately. A completed record verifies unchanged
backing bytes, unchanged selected code bytes, and exactly the predeclared change
in the selected data page. The latter differs from its unchanged backing page.

The subject is this authored probe. The original launcher, hosted entry,
selected runtime, operator and model are not executed by this profile. B2 remains
open. This measurement informs the later original-launcher acquisition protocol
by making backing-object identity and sampled memory equality separate, explicit
obligations.

## Exact subject selected before execution

Profile: `linux_x86_64_fixed_probe_private_memory_transition_v0`.

The probe is one exact 8,192-byte Linux x86-64 static ELF, directly defined by
the selected Python source. There is no compiler or assembler invocation during
collection, interpreter segment, dynamic-library dependency or supplied command.
The only argument encodes the actual observer PID as eight lowercase hexadecimal
digits. Parent-death `SIGKILL` and the expected-parent check precede both stops.

| Selected range | Virtual address | Bytes | ELF offset | Mapping permissions |
| --- | --- | --- | --- | --- |
| `rx` | `0x400000` | 4,096 | 0 | `r-xp` |
| `rw` | `0x401000` | 4,096 | 4,096 | `rw-p` |

The ELF has two `PT_LOAD` segments and an explicit nonexecuting `PT_GNU_STACK`.
Its entry point is `0x4000e8`. The data page is initially all zero. After the
first stop, exactly one successful collector-issued `SIGCONT` permits a fixed
instruction to write `0x5a` at data offset 256, virtual address `0x401100`, before
the second self-stop. No other instruction writes the selected data page.
Unexpected continuation after the second stop exits 124. Failure codes 125,
126 and 127 retain the parent-death setup, argument and parent-check meanings.

The selection fixes the exact probe digest/size, observer executable, eight
source bindings, two ordered checkpoints, both ranges, exact transition and
finite limits. There is no caller-selected executable, memory address, range
length or replacement payload. The source roster comprises the new probe,
collector, checker and schema plus the four unchanged mapping-profile files
whose low-level helpers are reused. The checker never imports either collector.

## Acquisition sequence

The collector creates a new private output directory, preserves selection and
attempt start, retains a sealed executable memfd and spawns only its owned
fixed probe. It obtains a pidfd and pins the child's proc directory. The parent
retains its original backing descriptor until after terminal cleanup.

At each checkpoint, the collector:

1. Observes the expected child's `SIGSTOP` and records the monotonic stop time.
2. Retains raw stat/status/maps before acquisition, pidfd information, the
   actual executable descriptor's bytes/identity/seals and bounded host context.
3. Opens the fixed `mem` entry relative to the pinned proc directory with
   `O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK`, checks that descriptor's
   identity and performs bounded `pread` operations for the two selected pages.
4. Preserves two samples of each page, then retains the bracketing maps/status/
   stat records and checks descriptor stability and absence of another child
   event during acquisition.
5. Independently reconstructs that checkpoint and verifies the preserved disk
   prefix before marking it preserved.

Only after checkpoint `cp0` is fully preserved and checked may the collector
send its single `SIGCONT` through the owned pidfd. While awaiting `cp1`, it
preserves at most one reported `WCONTINUED` event. That event is optional because
the second stop can supersede it before a wait call observes it. A continued
event before `cp0`, a duplicate continued event, another stop signal or premature
termination cannot complete this profile.

After `cp1`, the collector kills and reaps the child. It rereads the retained
backing descriptor and preserves its final bytes and object record, then checks
the complete capture. The expected terminal wait status is `SIGKILL`, not a
successful ordinary exit. Neither the wait result nor checkpoint numbering
authenticates the signal sender or the complete executed instruction history.

## Every occurrence has its own obligation

The independent checker derives the address-to-file relationship from the
admitted ELF program headers and checks every file-backed mapping. It requires
exactly the two selected mappings, the expected private permissions and offsets,
and the same retained device/inode at both checkpoints. Unknown or overlapping
mappings cannot be excused by one matching occurrence. Kernel-labeled stack,
`vvar`, `vdso` and optional `vvar_vclock`/`vsyscall` mappings are retained and
bounded separately; their memory contents are not sampled by this profile.

Both samples of each selected range must match one another and that
checkpoint's exact expected bytes:

| Occurrence | Required samples | Relationship to backing bytes |
| --- | --- | --- |
| `cp0 / rx` | Exact initial code page, twice | Equal |
| `cp0 / rw` | Exact all-zero data page, twice | Equal |
| `cp1 / rx` | Exact initial code page, twice | Equal |
| `cp1 / rw` | Exact data page with offset 256 set to `0x5a`, twice | Different at offset 256 only |

A correct first occurrence cannot satisfy the second occurrence's obligation.
The checker reconstructs all four relations from the retained samples, not from
producer-written comparison flags. Swapped checkpoints, a reused initial data
page at `cp1`, another changed byte, a changed code sample or inconsistent
second sample cannot yield a completed relation even if their manifest hashes
are recomputed consistently.

Process PID/parent/start-time identity, a single thread, no observed tracer,
stopped state, maps and namespace context are checked at each checkpoint and
across the pair. The actual executable object and retained object must agree.
The retained backing bytes before and after cleanup must equal the exact
selected ELF. The memory descriptor identity must remain consistent. These
checks concern the owned process occurrence and the selected ranges, not all
memory in the process or host.

## Bounded preservation and failures

The profile retains the earlier finite bounds: 15 seconds for observation,
a separate 2-second cleanup opportunity, at most 17 seconds for a completed
attempt, 65,536 bytes per proc record, 33,554,432 bytes for the observer
executable, 4,096 bytes per output stream and 41,943,040 total raw bytes.
Each page read requests exactly 4,096 bytes at its fixed address.

There are 39 raw members: 11 global files and 14 files for each checkpoint.
`capture.json` binds their sorted exact inventory. Selection and capture digests
must be supplied independently for later reconstruction. Attempt identity
distinguishes observations; it is not an authenticated timestamp.

An unavailable memory interface, permission denial, short read, changed process,
unexpected event or deadline failure preserves the available bounded evidence
as incomplete. Short memory samples are retained before size rejection. The
collector never replaces an unavailable memory read with the backing page or
switches to a different acquisition interface. Cleanup still targets only the
owned child and retains bounded pending stdout/stderr. Failed cleanup cannot
produce a completed observation.

The implementation reuses the corrected nonblocking input admission and
private-output preservation primitives. All existing ancestors are pinned
without following symlinks. Output files are exclusive, single-link and private.
The producer checks the original disk prefix before and after publication;
the reader rechecks file identities and the complete directory roster after
reading. An incomplete-preservation marker prevents ordinary capture admission.
These are finite checks; they do not promise that saved files can never change
after verification. Later replays must use the independent digests again.

The deadlines bound collection decisions and completed-record acceptance. They
do not make an external kernel or filesystem operation preemptible and do not
establish whole-host resource containment.

## Result and trust boundary

`status=accepted` means the record was accepted by the checker. A complete
observation additionally has `observation_complete=true` and these narrow fields:

- `sealed_backing_object_unchanged`
- `selected_memory_ranges_observed`
- `selected_rx_pages_match_backing`
- `selected_rw_transition_observed`

The four `memory_relations` rows carry their own checkpoint/range identity,
address, size, file offset, observed-byte binding, backing-byte binding and
derived equality. A completed record has `changed_data_offsets=[256]`.
An accepted incomplete record has all narrow completion fields false, no
relation rows, an empty delta list and its retained failure reason.

The observer still relies on the local Linux kernel/procfs, selected Python
executable, standard library and selected source. Source/digest reconstruction
does not authenticate a hostile observer, kernel or historical event. The
samples are virtual-memory reads: neither physical residency nor all process
memory is established. The broad `process_memory_bytes_verified` field remains
false; the new fields name the exact sampled ranges instead.

The record remains `record_status=example`, `diagnostic_only=true`,
`authority_effect=none` and `metric_pass=null`. Launcher/loader verification,
complete native closure, host qualification, containment enforcement,
selected-runtime execution, execution readiness and production-gate eligibility
retain their existing false boundaries. The earlier denied ptrace feasibility
and earlier mapping observation remain separate preserved results.

## Completed local observation

A completed source-bound attempt on 2026-11-17 retained all 39 raw members,
observed both stops and one continuation, preserved the specified one-byte
data change, and killed/reaped its owned child. Two separate executions of
the same independent checker accepted that capture and produced byte-identical
canonical reports. The collector's reconstructed report also equals those bytes.

| Record | Bytes | SHA-256 |
| --- | --- | --- |
| Selection | 2,882 | `3608a80ff843f4e8aa420956aae1b8044aa29db40995b13f3cc6cfbad1775ac7` |
| Capture | 6,783 | `95c6b91f1b4a7286caf8db16cf2b7aa2559336909f5909178c097b002e0c1b0f` |
| Each canonical report | 2,485 | `0bf00e9b47de670c173d4fdd847639f35c72856c444601287ff4ccf304b86111` |
| Fixed probe ELF | 8,192 | `b914d532059e8fb804a5358e9946849510d9362265c4ff112b5c5d5482bd1bb1` |

The attempt identity is `65aa5d7f4a0e40eaa2482aa024a27b54`. Both actual executable
descriptors and both retained-backing observations identify device 1, inode 478,
size 8,192 and seals 15. Those device/inode values describe this occurrence,
not reusable global identities. Both code-page samples at each stop match
their backing page. The first data page matches its backing page; the second
differs only at offset 256, from `0x00` to `0x5a`.

All eight selected source files remained byte-identical through collection and
both checker executions. The separate validation archive preserves the original
selection, raw capture, reports, process logs and exact verifier source files.
Its offline replay does not execute either probe or the selected runtime.

The previous corrected single-stop observation
`e8dda0c10f7349748d221f47c7422fee` also reconstructed again with its unchanged
selected checker. Its report remains byte-identical with SHA-256
`b4b21a419cadd4cffc50c56e4164e409d23516f541f473d39ad8914d4b373f45`.
The new observation neither rewrites that selection nor gives it a new claim.

The full containment regression module passed all **600 cases** with the
repository-pinned CPython 3.11.16: the existing 508 cases and 92 added cases.
Its complete previous 193,489-byte test prefix is unchanged. The added cases
include actual denied/short/changed-read failures at either checkpoint,
pre-continuation preservation substitution, all eight sample obligations,
checkpoint/mapping/process substitution, optional and unexpected continued
events, bounded malformed controls and the inherited FIFO admission boundary.
The existing 189 Tools entries and 40 targeted pytest entries remain unchanged.

## Implementation and commands

| Component | Responsibility |
| --- | --- |
| [Fixed probe](../../tools/required_gate_idempotence_memory_probe_v0.py) | Exact two-stop ELF and fixed one-byte transition |
| [Collector](../../tools/required_gate_idempotence_memory_observation_v0.py) | Owned-child acquisition, bounded preservation and cleanup |
| [Independent checker](../../tools/check_required_gate_idempotence_memory_observation_v0.py) | Closed selection, all occurrence obligations and raw-evidence reconstruction |
| [Schema](../../schemas/required_gate_idempotence_memory_observation_v0.schema.json) | Closed structural record shapes; semantic checking still requires the checker |
| [Existing containment regression module](../../tests/test_required_gate_idempotence_containment_v0.py) | Preserved earlier cases and new observation regressions |

Use the selected observer interpreter for preparation and collection. The
following shows the interface; substitute a fresh 32-lowercase-hex attempt ID
and independently retained full digests. Each output path must be new.

```sh
python tools/required_gate_idempotence_memory_observation_v0.py prepare \
  --attempt-id <fresh-hex32> --output selection.json

python tools/required_gate_idempotence_memory_observation_v0.py run-example \
  --selection selection.json --selection-sha256 <selection-sha256> \
  --output-directory capture

python tools/check_required_gate_idempotence_memory_observation_v0.py \
  --selection selection.json --selection-sha256 <selection-sha256> \
  --capture-directory capture --capture-sha256 <capture-sha256> \
  --output checker-1.json
```

Run the checker again in a separate process with another new report path.
Byte-identical reports from those runs establish repeatable reconstruction of
the same capture. They are two executions of one independent implementation,
not two independent implementations or two identical live observations.

## Continuation of B2

This result gives the original-launcher acquisition protocol a sharper
requirement: name separately which backing objects were observed and which
memory ranges or transformations were actually checked. The next subject is
the original selected launcher and every relevant loader/native occurrence in
its reviewed acquisition environment, followed by observed containment and
selected-bootstrap integration.

The [original launcher exec-stop acquisition](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_EXEC_STOP_v0.md)
implements the first concrete slice: the unchanged launcher and its selected
interpreter at the kernel exec stop, with separate mapping and RX-memory
obligations. Request preparation reconstructs the original chain; an actual
original-target capture remains a separately authorized owner observation.
This continuation preserves the present completed two-stop probe capture and
its source-bound report bytes.

The [preserved plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#18-required-gate-coverage-plan-after-accepted-rejection-verification)
continues in its established order. B3 property evidence, B4 admission and B5
the separately authorized actual reference remain distinct. Broader Step 6
resource measurement and Step 7 promotion remain separate outstanding work.
Preserve the original `43514702328/1` artifact, both `43854478248/1` archives,
Q2 `FAIL 49/50 +1 UNKNOWN`, all twelve unsupported gates and historical Q3 scope.
Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

## Primary implementation references

- [Linux proc memory interface](https://man7.org/linux/man-pages/man5/proc_pid_mem.5.html): memory reads and permission checks.
- [Linux mapping format](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html): ranges, permissions, private mappings, offsets and device/inode.
- [Linux memory mappings](https://man7.org/linux/man-pages/man2/mmap.2.html): private changes and their relationship to the underlying file.
- [Linux file seals](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html): sealed file contents and shared writable mappings.
- [Linux child waits](https://man7.org/linux/man-pages/man2/waitpid.2.html): stop, continued and terminal reports.
- [Linux proc filesystem](https://docs.kernel.org/filesystems/proc.html): pinned proc descriptors and process lifetime.
