# Q3 runtime part transport candidate v0

Date: 2026-11-03  
Preparation base: `7bb56fc801673ccf31ec92227bda56a4c240b357`  
Status: inactive implementation candidate; hosted retrieval not verified  
Authority effect: `none`

**Follow-up, 2026-11-10:** The [immutable-release acquisition adapter](PULSEMECH_Q3_RUNTIME_RELEASE_TRANSPORT_v0.md)
configures the published companion source and extends retrieval evidence and
independent checking. The dated inactive-candidate description below is retained
as the 2026-11-03 preparation record; actual-runner retrieval remains unverified.

## Purpose and present state

The native Q3 controller can acquire the selected runtime through a reviewed
twenty-part delivery description, reconstruct its original bytes, and pass the
result into the existing independent archive verification and installation
boundary. The implementation adds transport handling to the existing controller.
The postflight comparator, record acquirer, capture handoff and Q3 calculator
retain their roles.

The shipped candidate has no payload commit or path prefix. Its selected
transport therefore fails with `RUNTIME_TRANSPORT_UNCONFIGURED` before runtime
acquisition, control-plane acquisition or capture-handoff acquisition. It is not
a ready-to-dispatch preflight request. No existing hosted source, successful
runner retrieval, payload publication or execution authorization is asserted.

The owner reported downloading all twenty fragments into Downloads subfolders.
No hash verification of those owner-machine copies was observed. This candidate
does not depend on access to that computer or require local assembly, PowerShell,
model installation, a server, a tunnel or a self-hosted runner.

## Fixed original object

| Field | Binding |
| --- | --- |
| Filename | `q2-runtime-preparation-37148637546-1.zip` |
| Size | `508460811` bytes |
| SHA-256 | `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9` |
| Original run / attempt | `37148637546 / 1` |
| Original Actions artifact | `11282419957` |
| Original source | `77fc5d51896568db50a2a87f650711a65db8fe8c` |
| Exact split-manifest SHA-256 | `67eff809f8cf000f82b8365f1fc535ca82ffea167e2834488166915454c87f37` |
| Canonical ordered part-list SHA-256 | `0f7af070258c3bb6206c240e00cfe5464169666fbaf9fa9540b68c7ee384d341` |

The twenty names are the original filename followed by `.001` through `.020`.
Parts 001–019 contain `25423041` bytes each; part 020 contains `25423032` bytes.
Their exact contiguous offsets and SHA-256 values are retained as the
controller's `RUNTIME_PARTS` literal. The independent checker separately pins
the canonical ordered list. The split does not extract, recompress, rebuild or
replace any original archive member.

The profile's original `runtime_archive` identity remains unchanged. A new
transport location does not create a new identity for the original Actions
artifact or claim that its expired endpoint became available. The separate Q3
evidence artifact selected by postflight retains its own identity and purpose.

## Source selection and network boundary

`PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py` contains the reviewed
literal descriptor:

```python
RUNTIME_TRANSPORT = {
    'kind': 'github-repository-parts-v0',
    'repository': 'HKati/pulse-release-gates-0.1',
    'commit': None,
    'prefix': None,
}
```

The descriptor and complete part list are in an existing member of the sealed
native source set. No environment variable, workflow input, arbitrary URL or
owner-local path can override them. The native profile and its twenty-one
source paths remain unchanged.

When separately configured in reviewed source, the candidate permits only this
repository, a full nonzero forty-character commit SHA and a canonical relative
path prefix. Each filename is selected from the fixed ordered part list. The
GitHub Contents request uses raw content at that exact commit. One redirect is
permitted only to the exact corresponding immutable `raw.githubusercontent.com`
path, with the bearer token removed. Other destinations and redirect chains
are rejected. There is no retry or fallback to a different source.

The original Actions downloader remains an explicit source-code-selected route.
It still requires the original artifact metadata and original archive bytes.
It is not used as a fallback from the parts candidate.

The Contents API raw media type is necessary for files in this size range:
[GitHub Contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content).

## Acquisition and independent verification

The existing `execute()` route obtains its archive from `download_runtime()`.
For parts transport, bounded streaming enforces the exact twenty-row inventory,
order, unique names and ordinals, contiguous offsets, each size and digest, and
the full original size and digest. The existing acquisition deadline and
180-second download budget are retained. The archive is not held in memory.
Failure removes only a newly created partial destination belonging to this
attempt; a pre-existing or replaced file is not silently removed.

Successful acquisition produces the same private `work/runtime.zip` used by
the existing `K.verify_archive()` call. That independent check still validates
the exact seventy-eight ZIP entries, preparation records, thirty wheel bindings,
model map and requirements lock. Installation cannot follow a failed transport
or archive check.

`runtime-transport.json` records the selected transport, original object,
verified observed parts, reconstructed size/digest and request/run/source/
controller bindings. Its SHA-256 is required in
`prelaunch.runtime_transport_sha256`, and the record is required in the complete
carrier inventory. The native checker reads the controller's literal descriptor
using AST parsing, without importing or executing it, and independently verifies
the record against its fixed original-object and part-list pins. A receipt cannot
make an unconfigured production source acceptable.

Transport evidence does not independently authenticate a provider or VM. Its
claims retain `authority_effect=none`, `source_authentication=not_established`,
`label_correctness=not_verified` and the other existing non-authorizing limits.

## Historical replay and current capture

The external comparator accepts only complete, exact reviewed checker pairs.
It retains the previous pair for historical replay and reports the pair actually
used. It does not rewrite a historical carrier, add missing transport evidence
to it or repair a historical runner-image contradiction.

The capture handoff separately requires the current checker pair and the full
native source-byte agreement already required between selected preflight and
capture. A historical replay result cannot satisfy the new capture requirement.
The comparator, external acquirer and handoff pins are refreshed in dependency
order from their actual final bytes.

## Offline regression scope

The existing registered Q3 test files cover tiny synthetic part streams, exact
ordering, duplicates, gaps, short/oversized/corrupt bytes, final-digest errors,
deadlines, interruption and cleanup. Mock HTTP checks cover immutable source
selection, raw retrieval and credential isolation at the permitted redirect.
The actual `execute()` route is exercised with explicit transport/native phase
doubles, including failure before the installer. Coherently rehashed false
transport records are rejected by native and external verification.

Positive synthetic carriers explicitly configure copied source bytes. They do
not claim that the inactive production descriptor performed a real download.
No runtime payload is included in the patch or test fixtures. No native Q3 run,
tokenizer/model execution, response capture or scoring is performed by this
preparation. The CI test manifests and workflows are unchanged.

## Remaining activation inputs

Hosted access remains dependent on a separately authorized publication/storage
decision, an actually available immutable payload commit and approved path, and
subsequent evidence of retrieval by the real designated runner. The payload
commit must already exist before a later configuration change binds it; a
descriptor must not refer to its own unknown future commit.

The retained assessment in
[owner-local custody](q3_runtime_local_custody_v0/README.md) remains
`PREPARATION_SCOPE_INSPECTED_PUBLICATION_BLOCKED`. Its open notice/source and
owner-review items are not closed by this transport implementation. The earlier
LFS budget proposal is not a prerequisite for the selected local custody/docs
arrangement. No Git LFS, paid storage, new spending or billing change is selected.

After access is established, the existing sequence remains: separately
authorized zero-generation preflight; internal and external checks; separate
owner capture decision; at most 204 single calls with original responses
preserved; exact response-bound Q1 inputs; Q3 calculation and independent
recomputation. No automatic retry or top-up is added. Keep #2879 open.
