# Q3 runtime acquisition from the immutable input release

Date: 2026-11-10  
Preparation base: `ed1b84119ef2fcd0dcf6997a28efeee0902af27f`  
Status: source-bound acquisition adapter; actual-runner retrieval not verified  
Authority effect: `none`

## Purpose and scope

The Q3 controller selects the published runtime input companion by fixed
repository, release, tag target and asset identities. It downloads the preserved
split manifest and twenty unchanged fragments, reconstructs the original
archive, and passes the result to the existing independent archive verifier
before installation. The adapter uses the existing manual acquisition workflow;
it adds no workflow trigger, public command-line source override or fallback.

The [publication record](q3_runtime_release_binding_v0/README.md) and
[25-asset inventory](q3_runtime_release_binding_v0/RELEASE_BINDING.json) remain
the recorded 2026-11-09 checkpoint. The earlier
[part transport candidate](PULSEMECH_Q3_RUNTIME_PART_TRANSPORT_v0.md) describes
the inactive repository-parts configuration prepared on 2026-11-03. This change
configures the delivery adapter; it does not turn either historical record into
evidence of a new runner execution.

## Fixed identities

| Binding | Value |
| --- | --- |
| Transport kind | `github-release-assets-v0` |
| Public companion | `HKati/pulsemech-q3-runtime-inputs` |
| Repository ID | `1450778044` |
| Release ID | `438650666` |
| Tag | `q2-runtime-37148637546-1-v1` |
| Tag target commit | `d4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5` |
| Required release state | `draft=false`, `immutable=true` |
| Release inventory | 25 uploaded assets, `821365369` bytes |
| Manifest asset ID | `728263266` |
| Manifest filename / bytes | `Q3_RUNTIME_PARTS.json` / `7014` |
| Manifest SHA-256 | `67eff809f8cf000f82b8365f1fc535ca82ffea167e2834488166915454c87f37` |
| Original archive | `q2-runtime-preparation-37148637546-1.zip` |
| Original archive bytes | `508460811` |
| Original archive SHA-256 | `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9` |
| Original run / attempt | `37148637546 / 1` |
| Original Actions artifact | `11282419957` |
| Original source commit | `77fc5d51896568db50a2a87f650711a65db8fe8c` |

The controller's existing sealed source contains `RUNTIME_TRANSPORT`,
`RUNTIME_RELEASE_ASSETS`, `RUNTIME_ORIGIN` and `RUNTIME_PARTS` as literals. The
independent native checker reads them using the Python AST without importing or
executing the controller. It separately pins their canonical identities:

| Canonical value | SHA-256 of contract JSON encoding |
| --- | --- |
| Release source descriptor | `16ac2d147f12e0bd4db769b0bf9a9fe717465ab834a0a1cb047ce38aefb9ddac` |
| Ordered 25-asset identity list | `58c9e698caea11381e3bf2c916568cc18b0fe7bdac4cb5de2e3b2f4e81ed00dc` |
| Ordered 20-part manifest list | `0f7af070258c3bb6206c240e00cfe5464169666fbaf9fa9540b68c7ee384d341` |

The release tag target identifies the companion's preservation/documentation
commit. The original source commit identifies the runtime's original preparation.
The acquisition request's source commit identifies the reviewed controller and
checker used for a new attempt. These three identities retain their separate
roles. The expired original Actions artifact is not treated as newly available.

## Acquisition sequence

1. Validate the sealed source descriptor, complete asset inventory, unchanged
   original profile identity, fragment order, sizes, digests and offsets.
2. Read the public repository metadata, the release by numeric ID, and the exact
   tag reference. Require the public repository ID/name, immutable published
   release, tag target, and complete set of 25 uploaded assets to match. Check
   every asset's ID, filename, exact size, SHA-256 and canonical API/download URL.
3. Download `Q3_RUNTIME_PARTS.json` by numeric asset ID. Check its exact bytes and
   digest, parse strict JSON, and compare its original-object and ordered-part
   entries to the sealed constants. Historical inspection fields in the
   manifest do not become observations of the new attempt.
4. Download the twenty fragments in `.001` through `.020` order, using each
   pinned numeric asset ID. Stream directly into a new private archive file.
   Check every fragment's observed size and SHA-256, reject short or extra bytes,
   then check the original archive's size and SHA-256. No extraction,
   recompression or model execution occurs in this step.
5. Repeat the same repository, release and tag metadata checks after the final
   archive digest is verified. A failed or changed identity rejects the attempt
   and removes the archive created by that assembly call.
6. Bind `runtime-transport.json` to the exact request, source commit, run,
   attempt and controller bytes. Bind its digest into prelaunch evidence.
7. Run the unchanged independent archive verification before the existing
   installation boundary. It checks the original archive member set, wheel
   bindings, preparation records, model files and requirements identity.

Only **21 asset bodies** are fetched: the manifest and twenty fragments. The
English source/notice companion and three source RPMs remain separate release
attachments; their metadata identities are checked with the full 25-asset set.
The adapter does not download, install or execute those four files.

## Network, time and cleanup boundary

The companion is public. The new release reader sends **no GitHub token**, has
no cookie/authentication handler, ignores ambient HTTP proxy settings, and uses
verified TLS. The main repository's existing authenticated control-plane
reader retains its own scope. It is not widened to arbitrary repositories.

Metadata requests use only these fixed routes under
`https://api.github.com/repos/HKati/pulsemech-q3-runtime-inputs`:

- The repository root.
- `/releases/438650666`.
- `/git/ref/tags/q2-runtime-37148637546-1-v1`.

Binary requests use `/releases/assets/<pinned-asset-id>` with
`Accept: application/octet-stream`, as described in the
[GitHub Release assets API](https://docs.github.com/en/rest/releases/assets#get-a-release-asset).
HTTP 200 is accepted directly. A single HTTP 302 may lead to the exact HTTPS
host `release-assets.githubusercontent.com`, under that repository ID's
`/github-production-release-asset/1450778044/<UUID>` path. Other hosts, paths,
schemes, user information, fragments, status codes or redirect chains fail.
The signed query is used only in memory; receipts contain stable asset API
endpoints. Neither the token nor a signed download URL is written to evidence.

One deadline covers metadata, manifest, all fragments and the final metadata
recheck: the earlier of the existing phase deadline and 180 seconds from the
start of release acquisition. Individual request timeouts are capped at 15
seconds and the remaining budget. Bounded `read1` calls check the deadline
before and after every read. JSON bodies are capped at 1 MiB; manifest and part
bodies have their exact pinned limits. Encodings other than identity, duplicate
relevant headers, ambiguous length/transfer framing and unexpected byte counts
are rejected. There is no automatic retry, latest-release lookup, source switch
or fallback to an expired Actions artifact.

The assembler creates the destination exclusively with mode `0600`. Failures
remove only the inode created by that call. Existing files, symlinks or a
replacement inode are not deleted. The outer acquisition lifecycle retains
responsibility for closing services, preserving incomplete evidence and cleaning
the attempt workspace. No installer or subject phase is reached after failed
transport or archive verification.

## Retrieval evidence and independent replay

For this route, `runtime-transport.json` has record type
`q3_runtime_transport_v1`. Its closed structure retains:

- The fixed transport descriptor and original runtime identity.
- The manifest's observed byte identity and stable asset endpoint.
- Every fragment's observed index, offsets, size, digest, asset ID and endpoint.
- The reconstructed archive's observed size and SHA-256.
- The before/after metadata identity projections for the repository, release,
  tag and all 25 assets, excluding mutable download counters and signed URLs.
- The request/source/run/attempt/controller bindings and unchanged
  non-authorizing claims.

The independent native checker constructs the expected record using its own
pins and the reviewed source literals. It rejects missing records, fields,
wrong identities and substitutions even if a caller recomputes surrounding
receipt, prelaunch and carrier hashes. Offline consistency is not independent
authentication of provider retrieval, a signature over a receipt, or proof
that a model executed.

The external postflight comparator pins the updated native checker. The
external record acquirer and capture handoff pins are updated accordingly.
The immediately preceding part-transport checker and the earlier preserved
checker remain accepted as complete, exact historical replay pairs. They
cannot satisfy the current checker requirement for a new capture handoff.
Historical failed/image-contradictory records are not rewritten or promoted.

## Offline verification

The existing registered native and external-postflight test modules exercise
the new route without network or native model execution. Tests include:

- Public fixed-route metadata reads, exact inventory matching and rejected
  repository/release/tag/asset substitutions.
- Credential-free direct/redirected asset responses, TLS/proxy boundaries,
  duplicate headers, unsafe redirects, encoding/size limits and deadlines.
- Exact bytes of the preserved 7,014-byte manifest fixture; changed, truncated
  and oversized versions are rejected.
- Twenty tiny synthetic fragment streams through the actual assembler and
  release dispatcher, including failure before, during and after assembly.
- The actual controller-to-carrier route with explicit synthetic native
  doubles; acquisition precedes archive verification, which precedes installation.
- Independent native and external-postflight rejection of coherently rehashed
  transport forgeries, plus retained historical replay and current handoff checks.

`tests/fixtures/q3_runtime_release_v0/Q3_RUNTIME_PARTS.json` is the exact public
manifest used as offline parser/integrity input. It is not a runtime fragment,
an executed payload, or evidence that a new runner retrieved the archive.

Run the related registered regressions from the repository root with Python
3.11.16:

```sh
python -m pytest -q tests/test_q3_native_capture_contract_v0.py tests/test_q3_native_capture_protocol_v0.py tests/test_q3_native_capture_v0.py tests/test_q3_native_capture_workflow_v0.py tests/test_q3_external_postflight_v0.py tests/test_q3_preflight_preservation_v0.py
```

Preparation validation on 2026-11-10: these six modules passed **1,072 test
cases and five subtests** under Python 3.11.16. The repository Markdown link
checker also passed. A separate local compatibility check loaded the exact
preceding part-transport checker from the preparation base: a synthetic v0
carrier remained replayable, while current capture handoff rejected that
preceding checker. These are local offline checks, not results of a new hosted
workflow or observations of the designated Q3 runner.

## Next operational step and retained boundary

After code review, CI and merge, a new owner-approved request must be prepared
against the final current source. The next native step is a separately
authorized **zero-generation token preflight**, followed by evidence acquisition
and independent external comparison. Source changes here require fresh
source-compatible preflight evidence; historical success or an offline fixture
does not authorize capture. A later capture still requires the supported v1
handoff, its exact approved token map, fresh comparison and separate owner
authorization. Q3 calculation remains a later step on retained accepted inputs.

This package contains no dispatch request and performs no native run. Publication,
adapter preparation and synthetic tests do not establish actual-runner retrieval,
label correctness, measurement success or release authority:

```text
runtime_transport_ready=false
actual_runner_retrieval_verified=false
label_correctness=not_verified
authority_effect=none
```

[Main-project issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open. Original runtime bytes, the 21-file native source inventory,
profile, workflow, stimuli, models, measurement rules and prior Q2/Q3 historical
results retain their existing roles. No LFS, paid storage, local server, tunnel
or self-hosted runner is introduced.
