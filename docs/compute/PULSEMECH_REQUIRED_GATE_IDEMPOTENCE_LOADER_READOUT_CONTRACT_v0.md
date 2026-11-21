# B2 loader readout checker contract v0

## Status and scope

This unit implements a data-only contract checker and two independent fixture
checkers: original-loader register/memory relationships, and repeated two-slot
hardware-stop transcript relationships. Its development base is
`47971d77165462e0fcd20e83ece3f94fedc166b2`, after
[PR #3043](https://github.com/HKati/pulse-release-gates-0.1/pull/3043).

The checkers accept explicitly **authored test fixtures**. Their consistency
does not authenticate a process, host, clock or acquisition. Actual live
qualification and original-loader observation remain separate obligations.

| Surface | Result supplied by this unit |
| --- | --- |
| Prior static binding | Fresh reconstruction with the unchanged checker and complete preserved inputs. |
| Authored checker contract | Exact comparison with reconstructed static facts and closed policies. |
| Readout fixtures | Raw register, mapping, backing-object, memory and original occurrence joins checked. |
| Two-slot fixtures | Fixed probe identity, programmed slots, repeated stops, resumes and cleanup checked. |
| Actual live readout / hardware qualification | Not performed or supplied. |
| Original request / collector / capture admission | Not implemented; original acquisition remains blocked. |
| B2 / Q3 / authority | No completion, metric, selected-runtime execution or release authority. |

The main README, old entry profile, historical plan, original evidence and
190 Tools / 41 targeted CI registrations retain their existing bytes. Tests
are appended to the already registered containment module.

## Exact prerequisite and source separation

The [contract checker](../../tools/check_required_gate_idempotence_loader_readout_contract_v0.py)
pins the complete [static binding record](required_gate_idempotence_loader_binary_binding_v0/record_v0.json)
and its four implementation/schema files. It calls the existing `verify_binding`
API to reconstruct the historical entry evidence, full Debian inputs, source
patches, original ELF and raw DWARF relationships. A saved accepted report cannot
substitute for that reconstruction.

The freshly reconstructed static report is bound in the new authored contract.
New implementation/schema bytes are checked before and after verification;
the prior checker retains its historical-source checks. All 81 historical
source bindings remain separate from the new implementation inventory.

Historical [run 44740993943/1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/44740993943)
retains source `03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`. Its terminated child
and recorded addresses are not a resumable live prefix.

## Raw readout relationships

The [event checker](../../tools/required_gate_idempotence_loader_readout_v0.py)
uses the verified static recipe and exact original native bytes. Original
loader address `0x3671` plus the derived loader load bias selects the pre-store
checkpoint. The raw register set supplies the argument pointer from **RBX** and
the returned provider map from **RAX**. RDI and the old `args.aux` value cannot
substitute.

The selected reads are the 40-byte argument structure, 56-byte consumer and
provider map prefixes, and the exact requested name including NUL. Two stopped
samples must agree. Packed-memory manifests account for every byte exactly
once; omissions, overlaps, truncation and unused bytes reject. Readable mapping
coverage is required for runtime ranges. Both complete immutable loader RX
samples must equal the original RX segment.

Mapping coverage and backing-object identity/content determine the selected
objects. Pathnames, caller labels, SONAMEs and expected providers are insufficient.
In this fixture API the native bytes are preserved original inputs and the
before/after descriptor records are authored metadata. Their internal agreement
does not authenticate newly acquired file-descriptor contents;
`contemporaneous_backing_acquisition_authenticated=false`. A later live capture
must independently supply its contemporaneous backing-object acquisition.
For consumer and provider the checker requires:

```text
l_addr = independently derived original-object load bias
l_ld   = load bias + original PT_DYNAMIC virtual address
l_real = this map's own pointer
l_ns   = signed zero
```

The occurrence join requires:

```text
args.strtab = consumer load bias + original DT_STRTAB virtual address
args.name   = args.strtab + original DT_NEEDED string offset
name bytes  = exact original requested name followed by NUL
```

The original consumer and name determine the unique original occurrence.
Nine-event fixture validation requires every occurrence once; event order does
not assign its ordinal. Different consumers sharing one provider remain
distinct obligations.

Intermediate events require the loader, consumer and provider relevant to that
event. They do not prematurely require the final entry checker's six-object
state. Full final-entry coverage and current-run continuity remain later
acquisition obligations. Live structure bytes are checked by relationships,
not against nonexistent original runtime-data bytes in an ELF file.

## Two-slot transcript relationships

The [two-slot checker](../../tools/required_gate_idempotence_loader_two_slot_v0.py)
defines a separate fixed inert ELF as bytes. Neither this checker nor its tests
execute it. The probe is not the original loader.

The transcript requires simultaneous DR0/DR1 programming, DR7 equal to 5,
exclusive stop causes, raw registers/siginfo, explicit DR6 clearing/readback,
and both targets remaining armed after event nine. A complete fixture contains
nine slot-0 hits followed by one slot-1 terminal stop: one pre-exec resume plus
ten post-cp0 resumes, with zero post-entry continuations.

Owned process identity, finite timing, SIGKILL and reap are checked. Supported
incomplete prefixes remain incomplete, including in the wrapper's top-level
result. A tenth return cannot be followed by another resume. Single-step
requests and the RFLAGS trap flag are rejected. Software breakpoints, code or
general-register writes, detach and fallback execution are excluded.

Raw RFLAGS are retained, but the live Resume Flag policy is not qualified by
these authored transcripts. `rflags_resume_policy_qualified=false` is enforced;
no observed repeated-resume capability is inferred from a fixture sequence.

The historical entry observer's DR0-only write policy and single cp0-to-entry
continuation stay unchanged. Its old successful qualification cannot qualify
the new two-slot sequence.

## Unresolved prerequisites are enforced

The prior source/debug/binary gate includes build provenance. The static record
establishes package membership, archive-declared source identity, selected
source patching and DWARF/instruction correlations. Independently reproduced
source-to-binary equivalence and authenticated historical build provenance
remain unestablished.

No accepted builder/signer policy or alternative build-evidence route is selected
here. Package versions, build IDs, debuglink CRCs and DWARF producer strings
cannot silently satisfy that obligation. The complete source/build gate remains
**unsatisfied**.

`trace_mode` and `open_mode` are decoded, but their selected invocation policy
remains **unqualified**. Consistent fixtures do not make arbitrary modes
acceptable for acquisition.

Fresh environment/guard qualification, actual same-environment hardware
qualification, original live readout, original-input admission, a complete new
request/collector/capture contract and separate owner authorization remain open.
These blockers are fixed contract fields. The synthetic hardware and original-byte
readout fixtures are separate test subjects; their successes are not joined into
one apparently acquired original process.

## Offline verification

The [authored contract](required_gate_idempotence_loader_readout_contract_v0/contract_v0.json)
requires an external exact-byte SHA-256. From a complete checkout:

```bash
python -I -B tools/check_required_gate_idempotence_loader_readout_contract_v0.py \
  --contract docs/compute/required_gate_idempotence_loader_readout_contract_v0/contract_v0.json \
  --contract-sha256 d5e54e6f0f705c3dab757851c953085fa5f9ae7a2ce4341b51baf99b3b6ae117 \
  --output /tmp/loader-readout-contract-check.json
```

Output is canonical JSON, created exclusively after successful reconstruction.
Invalid input cannot publish an accepted report or replace an existing output.
The integration API `verify_fixtures` reconstructs the same prerequisite and
contract before checking both fixture domains. Lower-level helper results are
fixture consistency only. Closed schemas do not replace semantic reconstruction.

Run permanent regressions through the existing registered module:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_readout
```

Fixtures are implementation tests, never actual capability records or captures.

## Result boundary and next gate

Contract acceptance establishes `contract_verified=true` and
`static_binding_reconstruction_verified=true`. Outputs retain:

```text
live_private_abi_readout_qualified = false
two_slot_breakpoint_qualified = false
invocation_mode_policy_qualified = false
rflags_resume_policy_qualified = false
contemporaneous_backing_acquisition_authenticated = false
source_build_gate_satisfied = false
original_acquisition_ready = false
original_acquisition_authorized = false
consumer_resolution_observed = false
b2_complete = false
metric_pass = null
authority_effect = none
```

Next work must select and verify the missing build-evidence acceptance policy,
complete the invocation-mode decision and qualify live mechanics under a
separately reviewed acquisition contract. Fresh process, source, input, event,
final-entry and cleanup bindings must precede any newly authorized original
attempt. [Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open.
