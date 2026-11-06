# Q3 runtime source and notice preparation record v1

Date: 2026-11-06  
Repository: `HKati/pulse-release-gates-0.1`  
Documentation preparation base: `625aa536ab1f5e3adc695c1a2d2ed9d11ca74101`  
Status: source and observed-notice companion prepared; runner delivery pending  
Authority effect: `none`

## 1. Purpose and position in the Q3 plan

This directory records the completed source-attribution and notice preparation
for the exact original Q2 runtime selected as the Q3 input. It preserves the
result and binds its separately retained evidence by filename, byte count and
SHA-256. Only these three text files are intended for the repository.

| Plan item | Recorded position |
| --- | --- |
| Q3 checks and execution controls | Implemented: historical preflight retention, external postflight comparison, exact-record acquisition, capture handoff and early runner-image observation |
| Twenty-part runtime transport | Implemented and merged in #2981; production source remains unconfigured |
| Original runtime recovery | Exact original ZIP recovered and checked; no repacking |
| Owner-local custody | Owner reports all 20 fragments downloaded into Downloads subfolders; owner-machine hashes have not been verified |
| Source and notice preparation | Explicitly inventoried source attributions and companion materials prepared, as recorded in `RESULT.json` |
| Runtime and source delivery to the actual runner | No approved destination or verified retrieval is established |
| Accepted capture, response-bound Q1 inputs and completed Q3 measurement | Not completed |

The completed Q3 components do not need to be rebuilt for this recording.
The current technical blocker is delivery of the same original runtime bytes
to the actual runner, with the prepared source and notice materials accounted
for in the chosen delivery arrangement.

## 2. Three repository files and their roles

| File | Purpose |
| --- | --- |
| [README.md](README.md) | Explains the completed work, its place in the plan, retained limits and the next step |
| [RESULT.json](RESULT.json) | Byte-for-byte copy of the completed companion's result, without reformatting |
| [EVIDENCE_INDEX.json](EVIDENCE_INDEX.json) | Exact companion identity, selected internal evidence identities and the three GNU source-archive identities and upstream URLs |

The retained result was prepared at
`2026-11-06T01:12:24.630646+00:00` against reviewed main
`003d25b15dbac62bac247e70900260aaab8b0012`.
Its `prepared_at_utc`, `reviewed_main`, execution flags and
`repository_write_performed=false` describe that historical inspection.
They are not rewritten to describe a later documentation commit.

The repository was subsequently read at
`625aa536ab1f5e3adc695c1a2d2ed9d11ca74101` for this additive delivery.
The target directory was absent. The exact ref/tree observation and the
statically inspected controller identity are recorded in `EVIDENCE_INDEX.json`.

Retained result SHA-256:
`88c4bb567b013f535bec8b7ecb786e6e3b7809ea3089a6db8b6d2ce9c9d7b0e4`.

## 3. Exact original input and separately retained evidence

| Object | Filename | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Original runtime | `q2-runtime-preparation-37148637546-1.zip` | 508460811 | `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9` |
| Source and notice companion | `Q3_RUNTIME_SOURCE_NOTICE_COMPANION_v1.zip` | 30470832 | `7a72828947d276060b28b3668ad6a569771aefe837e8c50f94833c6f4f2ff54c` |

Original run/attempt: `37148637546/1`; original artifact: `11282419957`;
original source: `77fc5d51896568db50a2a87f650711a65db8fe8c`.
Recovery does not revive the unavailable original Actions endpoint or create
a new provider artifact identity.

The companion contains 1,253 files, including detailed comparisons, source
materials, notices and unchanged historical records. Its recorded validation
has 548 passed byte checks and no failures. The consolidated notice file
contains 154 unique full texts while preserving their origins.

The original runtime and its 20 fragments remain outside this documentation
delivery. The full companion is retained separately. The three complete GNU
source RPMs are also retained separately and are not inside the companion ZIP:

| Original runtime object | Identified source RPM |
| --- | --- |
| Torch `libgomp.so.1` | `gcc-8.5.0-26.el8_10.alma.1.src.rpm` |
| NumPy `libgfortran-040039e1-0352e75f.so.5.0.0` | `gcc-libraries-8.3.1-2.1.1.el7.src.rpm` |
| NumPy `libquadmath-96973f99-934c22de.so.0.0.0` | `gcc-4.8.5-44.el7.src.rpm` |

`EVIDENCE_INDEX.json` supplies each source RPM's exact upstream URL, size and
SHA-256. It also binds the companion's full manifest, comparisons, notice
index, validation record and original 78-member archive inventory. Evidence
member paths in that JSON are relative to the companion ZIP root, not
repository paths.

An identity index is not a download service. No public companion URL, runtime
host or automatic runner access is established by these files. Private custody
links are deliberately excluded from the repository index. Recorded upstream
availability belongs to the companion inspection, not a promise of future
availability or a completed source-conveyance arrangement.

## 4. Completed work and its exact limits

The retained inspection established matching build IDs, code/data sections
and normalized dynamic symbol tables for all three GNU objects against the
identified official distribution binaries. Whole ELF files differ because
their loader metadata was adjusted in the wheels; those differences are
recorded. Their exact source packages, build specifications, distribution
patches and legal materials were collected: 274 material records in total.

The companion also includes source and legal materials for 113 distinct
observed Rust crates, plus two further evidenced native source crates.
Their registry checksums match. The 39 observed Tokenizers crate checksums
also match the pinned source lock. Thirty original wheels and their metadata,
54 original notice files, the previously prepared Tokenizers and LibYAML
notices, and the exact model-card binding are retained.

These are scoped static findings. They do not assert a complete native SBOM,
a verified compiled feature set, a source-to-binary rebuild, cryptographically
verified RPM public-key signatures, or blanket legal publication clearance.
The detailed limitations remain in `RESULT.json`.

| Retained gap | Position after this work |
| --- | --- |
| G1 | Separate CPython/bootstrap obligations remain outside the selected runtime-archive inspection |
| G2 | Source/build/patch attribution for the three GNU objects is complete; actual source conveyance is pending |
| G3 | Source and notice materials for the explicitly observed catalog are prepared; no complete binary SBOM is claimed |
| G4 | Disclosure of the exact 78 runtime ZIP members still requires the separate owner decision |
| G5 | Delivery of the exact companion and sources with the runtime remains part of the owner-selected delivery arrangement |

The earlier
[local-custody record](../q3_runtime_local_custody_v0/README.md) and its
[preparation assessment](../q3_runtime_local_custody_v0/PREPARATION_SCOPE_RESULT.json)
remain unchanged. This new dated result records the subsequent G2/G3 work.
The historical LFS proposal is not an active instruction.

## 5. Transport and CI are separate from this documentation

The
[twenty-part transport implementation](../PULSEMECH_Q3_RUNTIME_PART_TRANSPORT_v0.md)
was merged in
[#2981](https://github.com/HKati/pulse-release-gates-0.1/pull/2981)
at `8a49591054bf8e812a675b8113c1f16b5f4025c7`.
Its retained merge-CI result is
[PULSE CI #7206, run 41733625069/1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/41733625069),
completed successfully on that merge commit.

That historical CI result is not the CI result of this new documentation,
nor a claim about the later preparation-base commit. No documentation PR
number, head, CI result or merge is asserted in this package.

At the newly inspected main, the controller's `RUNTIME_TRANSPORT` still has
`commit=None` and `prefix=None`. The route remains inactive and fails closed
before runtime acquisition. This is not a ready-to-dispatch preflight request.

The carried-forward native preflight `41350046443/1` had a complete receipt
for 204 tasks, 144752 prompt tokens and zero generation calls. Its capture
handoff remains blocked by the recorded runner-image contradiction:
startup `20261025.353.1` versus platform record `20261026.354.1`.
Neither this record nor the earlier image-check fix repairs that historical
run or the blocked `40253690074/1` run. No new native run is asserted here.

## 6. Next work and owner boundaries

The next technical task is to specify the concrete no-LFS/no-paid-storage
delivery route for the exact original runtime and its source/notice materials.
Preparation of these documentation files does not choose or authorize a host.
Putting the 20 runtime fragments into the project repository was not approved
by the owner and is not implied by the merged transport implementation.

Once a concrete delivery arrangement is separately authorized, implement and
pin its source, then verify retrieval of the original bytes by the actual
runner without model execution. Subsequent measurement remains:

1. A separately authorized, fresh source-bound zero-generation preflight.
2. Internal and external checks.
3. A separate owner capture decision.
4. At most 204 one-shot responses, preserving the original responses.
5. Q1 inputs bound to those exact responses.
6. Q3 calculation, separate recomputation and evidence retention.

No automatic retry, top-up, substitute model or silent runtime replacement is
authorized. Local custody does not authorize local model execution, a
self-hosted runner, server, tunnel or access to the owner's computer.
The owner has reported the downloads; no PowerShell task is required by this
documentation delivery, and owner-machine hashes remain unverified.

Git LFS, paid storage, new spending and billing changes remain excluded.
Repository writes require separate authorization; the owner opens the PR and
controls its merge. This preparation delegates no work to external Codex.
No new external-person approval gate or full-SBOM/rebuild prerequisite is added.

Keep #2879 open. `label_correctness=not_verified` and
`authority_effect=none` remain unchanged. The endpoint is a reconstructable
measurement result, including a negative result; an incomplete run is not a
completed measurement.

## 7. Repository delivery scope

Add exactly:

```text
docs/compute/q3_runtime_source_notice_v1/README.md
docs/compute/q3_runtime_source_notice_v1/RESULT.json
docs/compute/q3_runtime_source_notice_v1/EVIDENCE_INDEX.json
```

No existing file is replaced or deleted. No payload, source archive, executable,
LFS pointer, workflow, profile, checker, test or CI-list change belongs in this
delivery. DOI/SWH identities, release policy and normative status are unchanged.
If any of the three destination files already exists when applying the
package, compare it before applying; this package does not authorize overwrite.
