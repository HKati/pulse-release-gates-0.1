# Q2 repository-preservation metadata stage v0

Status: **prepared_for_owner_review_not_published**.

This is a self-contained, ten-file metadata stage of the bounded Q2
repository-preservation proposal. It contains documentation, a planned-object
manifest, a component/notice review, supplemental license texts and three
unchanged historical records. It contains **no archive payload, no LFS pointer
and no LFS attributes**. Publishing these metadata is not payload publication,
repository-backed archive custody, P2 completion or full Q2-4 acceptance.

## 1. Source and stage boundary

Preparation base: `2ca84e3e0c9709758adc48eb959f1b5e0c965c19`.
The earlier full proposal selected 16 logical paths, including five outer
archive objects and `.gitattributes`. Those six payload/storage paths are
**outside this metadata change**, not deleted from the future preservation
target. The original native acquisition, replay and comparison identities
remain distinct from this preparation base.

This deliberate split permits review of completed project records without
publishing unresolved third-party binaries or raw evidence. It does not weaken
or waive any full-payload prerequisite. No future commit, upload, permission,
cost allowance or readback success is predeclared.

## 2. Files that this stage actually contains

The [preservation manifest](repository_preservation_manifest_v0.json) lists the
ten current-stage paths under `metadata_publication_stage.repository_paths`.
The selected archive entries under `archives` describe **planned future
repository destinations only**. Each is explicitly marked
`included_in_metadata_stage=false` and `repository_presence_asserted=false`.
Their digests identify original bytes; they are not downloadable repository
files in this stage.

The [component review](redistribution_review_v0.json) and
[supplemental notices](THIRD_PARTY_NOTICES_v0.txt) retain the reviewed scopes
and limitations. Their presence does not assert that all third-party
redistribution obligations have been discharged.

## 3. Unchanged historical records

The following files are byte-preserving copies, not rewritten measurements:

- [Original four-input selection](records/REMAINING_ORIGINAL_INPUTS.json).
- [Original four-input byte-check report](records/Q2_REMAINING_INPUTS_CHECK.json).
- [Original core delivery report](records/core_delivery/DELIVERY_CHECK.json).

The prior 4/4 byte PASS and core-delivery checks remain prior observations.
No model inference, tokenization, metric replay, field comparison, original
carrier-verifier execution or new acquisition is performed by this change.
The earlier 38 positive, 10 negative-control, 19 notice and 46 direct-update
validation records remain separate prior executions, not this PR's CI result.

## 4. Notice and source-review limits

The prior bootstrap inventory and notice additions remain documented. The
later static GNU follow-up records exact build IDs and debuglink names for
three original library objects. The libgomp debuglink provides an AlmaLinux
package-version lookup candidate, **not** an authenticated source-RPM binding.
The NumPy libraries' source-package mappings remain unestablished.

P2 remains open for the previously itemized GNU source/conveyance and native
transitive notice/source questions. No optional source catalog is promoted to
a complete shipped-binary inventory. The review distinguishes existing legal
material, new observation, interpretation and unresolved obligations.

## 5. Current CI and later payload publication

All ten files in this stage are ordinary Git metadata/documentation blobs.
No workflow, checkout option, runtime tool, gate, policy, threshold, registered
test list or billing setting is changed. This stage introduces no LFS download
and no archive materialization into recursive source scans. Existing source
size guards retain their meanings.

P1-P5 in the manifest remain **unchanged full-payload requirements**:
exact owner authorization for permanent raw/public payloads; redistribution
and notice review; observed LFS quota and explicit cost boundary; separately
authorized publication at a fixed source revision; and subsequent CI plus
cold-cache retrieval of the actual published objects.

Metadata-stage CI or readback cannot be used to mark payload P5 complete.
A later payload stage must recheck then-current main and notices, publish the
exact original bytes by the approved storage path, and verify retrieval of
those bytes. A text pointer, hash or upstream Actions URL alone cannot satisfy
that check. No source archive is repacked or replaced to manufacture clearance.

## 6. Preserved authority and custody statements

```text
owner_durable_retention=not_verified
historical_comparability=not_established
q2_comparison_accepted=false
full_release_host_verified=false
authority_effect=none
```

The metric remains 49/50 FAIL and the historical release BLOCK is unchanged.
This stage does not enumerate or close every earlier Q2-1 and preparation
retention obligation. Root README, DOI/SWH, historical checkpoints, QRH003 work
and Dependabot changes are untouched. Keep #2879 open.
