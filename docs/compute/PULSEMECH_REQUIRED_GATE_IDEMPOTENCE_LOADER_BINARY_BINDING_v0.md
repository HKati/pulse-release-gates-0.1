# B2 exact original-loader binary, debug and source binding v0

## Status and scope

This unit qualifies a selected **static** instruction and private-layout recipe
for the original loader already preserved in the completed entry observation.
It reconstructs the exact loader and matching debug members from full Debian
packages, checks their archive metadata relationships, replays the applicable
distribution source patches, and correlates the selected source declarations
with raw DWARF and original machine instructions.

The selected checkpoint is original loader ELF virtual address `0x3671`, before
the instruction that stores `_dl_map_object`'s return value. At that point the
argument structure pointer is in **RBX** and the returned provider map is in
**RAX**. This is an offset within the exact qualified ELF. A future observer must
add the fresh original loader load bias; an old absolute process address is not
reusable.

No native acquisition is performed by this unit. Source-to-binary equivalence
has not been independently reproduced, authenticated build-process provenance
has not been established, and the complete binary/source/build gate in the
earlier proposal is not closed. Live private-ABI readout, two-slot hardware
breakpoint qualification, a new collector and capture checker, and an actual
per-consumer resolution observation remain separate obligations.

`consumer_resolution_observed=false`, `b2_complete=false`, `metric_pass=null`
and `authority_effect=none`. [B2 issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open. This record supplies no selected-runtime result, Q3 metric result,
whole-process containment observation, complete native closure or release
authority.

## Relationship to preserved history

The unchanged [loader-resolution plan](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_PLAN_v0.md)
selects a future witness for nine original `DT_NEEDED` occurrences and a final
original executable-entry stop. Its authored record, schema and checker remain
byte-identical. The plan's null addresses and unsatisfied gate fields retain
their meaning as a historical proposal; this follow-up has its own record.

The checker freshly reconstructs the selected entry capture from
[run 44740993943, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943)
with its unchanged independent checker and all **81 historical source bindings**.
The historical source is `03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`.
That completed child was terminated. Its entry evidence cannot become a live
loader-resolution prefix or a resumable process.

The new checker separately pins the three prior proposal files, records its four
new implementation/schema bindings, and rechecks both groups plus the historical
81 files after derivation. It leaves the historical observation, original input
carrier and prior source bindings unchanged.

## Complete preserved inputs

The new [input manifest](../../preservation/required_gate_idempotence_loader_binary_binding_v0/inputs_v0.json)
binds six complete original artifacts totaling **41,590,708 bytes**. They are
stored as nine exact byte parts, each at most **8,000,000 bytes**. Concatenation
uses fixed ordinals and offsets, consumes every selected part exactly once,
and checks each part and full artifact SHA-256. Missing, extra, reordered or
substituted parts reject.

This stays below the existing proposal's 64 MiB qualification-payload budget
and below the ordinary 8 MiB repository source-entry limit per stored file.
It introduces no new large-file exception and requires no LFS service. The
expanded source archive is streamed under a separate 256 MiB decoded bound;
it is not retained as an expanded repository tree.

| Complete artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `libc6_2.41-12+deb13u4_amd64.deb` | 2,846,580 | `967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9` |
| `libc6-dbg_2.41-12+deb13u4_amd64.deb` | 7,373,052 | `0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7` |
| `Sources.xz` | 10,540,436 | `6002f81f463a2d976d84b34170367cc16da2d60bd0ba9ab9d868d6e1c1a935d9` |
| `glibc_2.41-12+deb13u4.dsc` | 7,576 | `0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e` |
| `glibc_2.41.orig.tar.xz` | 20,323,540 | `f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998` |
| `glibc_2.41-12+deb13u4.debian.tar.xz` | 499,524 | `dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d` |

The manifest retains the original Debian distribution URLs. The checker uses
the preserved bytes and needs no network. The complete older `Release`,
`Packages`, signature evidence and externally selected keyring remain in the
unchanged original input carrier.

The checked relationship is:

1. The selected historical `Release` binds the full binary and source indexes.
2. The full `Packages` index identifies the exact `libc6` and `libc6-dbg` package
   bytes, architecture, version and declared `glibc` source version.
3. Both package controls agree with that source identity. The debug package
   also declares its exact dependency on the selected `libc6` version.
4. The complete `Sources` index binds the `.dsc`, original source tar and Debian
   patch tar. The `.dsc` repeats the two source-component SHA-256 bindings.
5. The package loader member equals the historical original loader byte for
   byte. The debug member matches the exact debug binding, loader build ID and
   `.gnu_debuglink` CRC.
6. All active patches are scanned, and every applicable hunk is replayed for
   the selected source members before correlating their declarations.

The checker does not freshly run a signature verifier, assess current archive
freshness or authenticate the compiler/build process. Its trust basis includes
the unchanged selected historical signature evidence and externally selected
archive keyring. A parsed `.dsc` signature envelope is not a newly verified
signature. Matching package version, build ID and debuglink are relationships;
they are not an independent reproducible-build result. Optional unsigned or
separately unverified build-info material is not part of the accepted carrier.

## Original binary and debug identity

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Original loader | 225,672 | `c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307` |
| Matching detached debug | 556,488 | `34ab07395545cf33df8e551e809ebee6fd3fc2707ed848e390872dce539c4a78` |

Both have GNU build ID `86f7eb4ff495ed3f2831c6d3d662e4321762a2a3`.
The loader's debuglink filename is
`f7eb4ff495ed3f2831c6d3d662e4321762a2a3.debug`, with CRC32 `32eb62be`.
The checker requires the full-file SHA-256 and size bindings before parsing.
A file with a matching version string or build ID but changed bytes rejects.

The binary helper reads the original ELF and matching debug data directly. It
parses one bounded DWARF5 compilation unit, its closed form inventory, relevant
type chains, location lists and physical source-line tables. It never invokes
the target loader, debugger, host-header compiler or external disassembler.

## Selected instruction and register proof

`openaux` occupies `[0x3640, 0x3677)`, 55 original bytes. The checker partitions
the entire range into 17 selected decoded instructions. The decisive sequence
is:

| ELF virtual address | Original bytes | Meaning |
| --- | --- | --- |
| `0x3641` | `48 89 fb` | Save the incoming argument pointer in RBX. |
| `0x3644` | `48 8b 3f` | Replace RDI with the consumer map pointer. |
| `0x366c` | `e8 2f 5d 00 00` | Direct call to `_dl_map_object` at `0x93a0`. |
| **`0x3671`** | **`48 89 43 20`** | Store RAX into `args->aux`; the proposed stop is **before** this instruction. |
| `0x3675` | `5b` | Restore the caller's RBX. |
| `0x3676` | `c3` | Return. |

The matching DWARF call-site entry identifies the same callee and return PC.
The argument variable's raw location list specifies RBX throughout
`[0x3647, 0x3676)`, including the selected checkpoint. The original `.eh_frame`
range agrees with the 55-byte function, and a selected normal callee epilogue
corroborates the RAX result and restored RBX. The short epilogue check is not
an exhaustive proof of all callee paths.

At the selected checkpoint, `args->aux` has not received the new result. It may
contain an earlier or uninitialized value. The future observer must use the
live RAX value and recover the argument pointer from live RBX. RDI no longer
contains that argument pointer.

## Private layouts from the exact debug bytes

`openaux_args` is 40 bytes:

| Member | Offset | Width |
| --- | ---: | ---: |
| `map` | 0 | 8 |
| `trace_mode` | 8 | 4 |
| `open_mode` | 12 | 4 |
| `strtab` | 16 | 8 |
| `name` | 24 | 8 |
| `aux` | 32 | 8 |

The selected `link_map` has full size 1,208 bytes. The required identity and
namespace fields fit in a 56-byte prefix:

| Member | Offset | Width | Selected interpretation |
| --- | ---: | ---: | --- |
| `l_addr` | 0 | 8 | Unsigned ELF load bias. |
| `l_ld` | 16 | 8 | Pointer to this object's dynamic section. |
| `l_real` | 40 | 8 | Must equal this selected map's own address in the future witness. |
| `l_ns` | 48 | 8 | Signed namespace index; selected base namespace is 0. |

The checker binds member declarations, pointer/scalar widths, signedness and
type chains from this exact debug file. It also derives the `l_type` bitfield
used to prepare the call. Host headers or a generic glibc-version offset table
cannot replace these original-byte facts.

The read sizes are a selected future recipe. This unit does not perform those
live reads or establish their stability, accessibility or contemporaneous
backing-object identity.

## Source reconstruction and exact physical-line joins

Seven source members are retained during bounded archive inspection:

- `elf/dl-deps.c`
- `elf/dl-load.c`
- `include/link.h`
- `sysdeps/generic/ldsodefs.h`
- `sysdeps/x86_64/dl-machine.h`
- `dlfcn/dlfcn.h`
- `elf/elf.h`

The checker scans all 80 active patches in their preserved order, covering 478
file diffs and 803 hunks. The seven selected source outputs match independently
selected complete-file SHA-256 bindings. It records each relevant patch, hunk,
old/new context binding and before/after file binding.

Replay never discards context. It first checks the declared coordinates. If
those coordinates are stale, the complete old hunk must occur exactly once in
the current file, and the applied line offset is recorded. Two historical
`dl-load.c` hunks use this exact-context fallback at offset `-60`; this is not a
claim that all selected hunks apply at zero offset. Missing, altered or
ambiguous context rejects. Backup-name path alternatives in nonselected
patch blocks are retained; any ambiguous header involving a selected file
rejects.

Six raw DWARF declarations and ten selected member declarations are joined to
their exact physical source lines and identifiers. The selected checkpoint
maps to `elf/dl-deps.c` line 64. Lines are split only on LF: the form-feed byte
in `ldsodefs.h` is not an additional source line.

The DWARF line-table format contains path and directory fields, **no source
content hashes**. Source correspondence therefore remains the declared
distribution-source relationship plus the selected line/identifier and
instruction correlations. The record explicitly leaves full source-to-binary
equivalence false.

## Consumer occurrence and pointer relations

The unchanged six original ELF objects independently supply nine `DT_NEEDED`
occurrences. For each occurrence the new record preserves the original dynamic
tag ordinal, dynamic segment virtual address, string-table virtual address,
name offset, name bytes including NUL, and expected static provider candidate.
All six originals are checked for the excluded `DT_AUDIT`, `DT_DEPAUDIT`,
`DT_AUXILIARY` and `DT_FILTER` tags. Needed names must be unique within a consumer
and contain no `$` token expansion.

For a future event the required pointer relations are:

```text
args.strtab = fresh consumer load bias + original DT_STRTAB virtual address
args.name   = args.strtab + selected original DT_NEEDED string offset
```

The captured NUL-terminated name bytes must also equal the original bytes.
The recovered consumer identity and exact name select one original occurrence;
`openaux_args` does not contain a dynamic ordinal, and event order cannot supply
one. A provider already mapped for another consumer still requires its own
return event for this occurrence. An expected provider candidate is not an
observed return value.

The future witness also needs two stable stopped samples, fresh original
mapping and descriptor identity, `l_ns == 0`, and `l_real == map_pointer` for
both selected maps. Those predicates apply to the selected event; they do not
prove the absence of all other namespace activity.

## Offline verification

From a complete repository checkout with the existing checker dependencies:

```bash
python -I -B tools/check_required_gate_idempotence_loader_binary_binding_v0.py \
  --record docs/compute/required_gate_idempotence_loader_binary_binding_v0/record_v0.json \
  --record-sha256 d5679d1afab1c13db460ad8d818e5a07241b8dfeb079f410069c550c9f10d065 \
  --output /tmp/loader-binary-binding-check.json
```

The output path must be new. Accepted reports are canonical JSON and are
deterministic for identical input and implementation bytes. Output is written
only after successful reconstruction; a rejected input cannot create an
accepted report or overwrite an existing output.

Verification requires both the externally supplied record digest and the
[closed schema](../../schemas/required_gate_idempotence_loader_binary_binding_v0.schema.json).
It then derives the complete expected record anew from the preserved inputs.
Schema validity, a rehashed edited record, a producer success flag or a saved
previous verdict cannot substitute for that derivation.

The regression cases are appended to the existing containment test module.
The 190 Tools and 41 targeted CI registrations stay unchanged. Independent
standard-library oracles inspect package members, original machine bytes,
build ID, CRC, symbols and selected DWARF bytes; negative cases cover part
substitution, recipe/layout changes, source drift, strict controls, forbidden
execution/network paths and exclusive canonical outputs.

## Files and next gate

- [Authored static binding record](required_gate_idempotence_loader_binary_binding_v0/record_v0.json)
- [Independent wrapper checker](../../tools/check_required_gate_idempotence_loader_binary_binding_v0.py)
- [Original ELF and DWARF helper](../../tools/required_gate_idempotence_loader_binary_v0.py)
- [Distribution and selected source reconstruction helper](../../tools/required_gate_idempotence_loader_source_v0.py)
- [Preserved complete input manifest](../../preservation/required_gate_idempotence_loader_binary_binding_v0/inputs_v0.json)
- [Existing guarded entry observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_STOP_v0.md)

The next implementation must carry this static binding into a separately
qualified live readout and two-slot hardware capability, while resolving the
remaining source/build provenance obligation explicitly. A new request/capture
contract and independent event checker must precede any fresh owner-authorized
original-loader resolution attempt. The earlier entry profile's continuation
policy and the main README are unchanged by this unit.
