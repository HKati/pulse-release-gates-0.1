# PULSEmech Q3 runtime input companion

This record connects the main PULSEmech repository,
[`HKati/pulse-release-gates-0.1`](https://github.com/HKati/pulse-release-gates-0.1),
to its published runtime input companion,
[`HKati/pulsemech-q3-runtime-inputs`](https://github.com/HKati/pulsemech-q3-runtime-inputs).

The companion holds the exact runtime input selected for Q3, together with its
split manifest, source materials and notices. The main repository retains the Q3
implementation, verification contracts and this reference to the external inputs.

**Status:** published immutable input companion; metadata identity checked;
actual-runner retrieval remains unverified. This is a reader/audit record.
It does not configure or activate a runtime acquisition path.

## Fixed release identity

| Field | Value |
| --- | --- |
| Release | [Q3 runtime input — Q2 preparation 37148637546/1](https://github.com/HKati/pulsemech-q3-runtime-inputs/releases/tag/q2-runtime-37148637546-1-v1) |
| Release ID | `438650666` |
| Tag | `q2-runtime-37148637546-1-v1` |
| Tag target commit | `d4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5` |
| Publication time | `2026-11-09T18:37:00Z` |
| GitHub state checked | `draft=false`, `immutable=true` |
| Uploaded assets | `25` |
| Uploaded asset total | `821365369` bytes |
| Main repository documentation base | `ae2fad9ee6b0925b9d4141d079e43624ffc2546d` |

[RELEASE_BINDING.json](RELEASE_BINDING.json) records every asset's exact name,
GitHub asset ID, byte count, SHA-256, download URL and API URL. Runtime fragments
also carry their ordered index and byte offsets.

The tag-specific link above identifies this release. Consumers should use the
recorded release and asset identities together with size and digest checks.
A moving `latest` URL or the runtime repository's `main` branch does not
identify this exact delivery set.

## What belongs to this companion

| Material | Uploaded assets | Exact bytes |
| --- | ---: | ---: |
| `q2-runtime-preparation-37148637546-1.zip.001` through `.020` | 20 | 508460811 |
| `Q3_RUNTIME_PARTS.json` | 1 | 7014 |
| `Q3_RUNTIME_SOURCE_NOTICE_COMPANION_v2.zip` | 1 | 30532275 |
| `gcc-8.5.0-26.el8_10.alma.1.src.rpm` | 1 | 65714006 |
| `gcc-libraries-8.3.1-2.1.1.el7.src.rpm` | 1 | 137336608 |
| `gcc-4.8.5-44.el7.src.rpm` | 1 | 79314655 |
| **Total** | **25** | **821365369** |

The complete original archive is reconstructed by concatenating the twenty
unchanged fragment files in manifest order. It is not a twenty-sixth uploaded
asset. GitHub's automatically generated source-code ZIP/tar archives contain the
runtime repository's Git tree; they are not this preserved runtime archive.

Original archive identity:

- Filename: `q2-runtime-preparation-37148637546-1.zip`
- Bytes: `508460811`
- SHA-256: `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9`
- Original run / attempt: `37148637546 / 1`
- Original Actions artifact: `11282419957`
- Original source commit: `77fc5d51896568db50a2a87f650711a65db8fe8c`

The runtime repository's release tag target is the documentation/preservation
commit. It does not replace the original runtime source commit above.

## Verification recorded at publication

On 2026-11-09, the public
[GitHub release API response](https://api.github.com/repos/HKati/pulsemech-q3-runtime-inputs/releases/438650666)
and [tag reference](https://api.github.com/repos/HKati/pulsemech-q3-runtime-inputs/git/refs/tags/q2-runtime-37148637546-1-v1)
were read. All 25 asset names, exact byte counts and GitHub-reported SHA-256
digests matched the preserved reference inventory. The asset names and IDs
were unique, every asset was reported `uploaded`, and their sizes summed to
821,365,369 bytes. The locally preserved manifest and version-2 companion bytes
were also rehashed against their expected identities.

This check used metadata returned by GitHub. It did not download the 25
published binaries, reconstruct the archive, rerun the independent archive
verifier or retrieve the files from the actual Q3 runner.

A future consumer must verify fragment bytes, reconstruct the original in
manifest order, check its complete size and SHA-256, and apply the existing
independent archive verification before accepting that runtime.

## Discovery and acquisition

The root [README](../../../README.md#q3-runtime-input-companion) and
[documentation index](../../INDEX.md#q3-runtime-input-companion--publication-checkpoint-2026-11-09)
link to this record. A reader or repository-indexing agent can identify the
companion and its exact asset set through these ordinary Markdown links and
the machine-readable JSON.

A clone or source ZIP of the main repository includes the checked-in
documentation and JSON. The external release assets require a separate
download. This record does not claim that a particular crawler has followed
the links, indexed the release or downloaded its assets.

At main repository base `ae2fad9ee6b0925b9d4141d079e43624ffc2546d`,
the [acquisition controller](../../../PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py)
still selects an inactive `github-repository-parts-v0` transport whose payload
commit and prefix are unset. The published companion has release assets, so the
next implementation step is an explicitly pinned release-asset acquisition
path that retains the existing integrity and independent verification checks.
The current controller does not consume `RELEASE_BINDING.json`.

The existing [transport contract](../PULSEMECH_Q3_RUNTIME_PART_TRANSPORT_v0.md),
[runner-image observation contract](../PULSEMECH_Q3_RUNNER_IMAGE_OBSERVATION_v0.md)
and [capture handoff](../PULSEMECH_Q3_CAPTURE_HANDOFF_v1.md) retain their scope.
Implementation review, actual-runner retrieval and any subsequent execution
decision remain separate steps.

## Retained records and terms

The earlier [local-custody record](../q3_runtime_local_custody_v0/README.md) and
[source/notice preparation record](../q3_runtime_source_notice_v1/README.md)
remain historical records with their original dates and limitations. This
publication checkpoint records the later delivery event without rewriting them
or asserting custody of other Q2 archives.

Third-party materials retain their original terms and notices. The scope of the
runtime repository's own documentation license is stated in its
[README at the release commit](https://github.com/HKati/pulsemech-q3-runtime-inputs/blob/d4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5/README.md).
This reference does not broaden those permissions or assert complete legal
clearance.

## Q3 boundary

- `runtime_transport_ready=false`
- `actual_runner_retrieval_verified=false`
- `label_correctness=not_verified`
- `authority_effect=none`

Publication and this reference do not authorize or start preflight, capture,
model execution or Q3 measurement.
[Main-project issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open.
