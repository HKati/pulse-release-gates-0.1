# Q3 external postflight comparison v0

Status: offline comparison component; no active capture-handoff enforcement.
Preparation base: `32d442dac168df287ee669ceada25870f8c73b31`.
Tracking: #2879 remains open.

## Scope

`tools/check_q3_external_postflight_v0.py` generalizes the selected historical
review into a bounded, read-only comparison of a separately selected Q3 v0
preflight and its retained external records. Run, source, job, artifact, request
and token-map identities are inputs, not hard-coded historical acceptance values.
The supported native profile is the existing closed v0 profile with its 21-file
source closure, a single `acquire` job and run attempt 1. Other profiles, retries,
checker versions or log representations require explicit review, not fallback.

This increment implements the offline comparison part of the planned external
postflight work. It does not complete evidence-source authentication, produce a
capture request or introduce a new prerequisite in the native capture path.

## Inputs and independent selection

The caller supplies an expectation JSON, its separately selected SHA-256 and an
input directory containing these ordinary files:

| File | Meaning | Limit |
| --- | --- | --- |
| `artifact.zip` | Original outer Actions artifact, not a review wrapper | 64 MiB |
| `run.json` | Retained metadata for the selected run and attempt | 4 MiB |
| `jobs.json` | Complete attempt-specific job listing | 4 MiB |
| `artifact.json` | Retained metadata for the exact artifact ID | 4 MiB |
| `job.log` | Raw selected job log, preserving original bytes | 16 MiB |

The closed expectation has exactly these fields:

- `record_type`: `q3_external_postflight_expectation_v0`.
- `repository`: `HKati/pulse-release-gates-0.1`.
- `source_commit`: the original full source commit, not the current main commit.
- `run_id`: canonical positive decimal string; `run_attempt`: integer 1.
- `job_id` and `artifact_id`: positive integers, not booleans.
- `request_sha256` and `token_map_sha256`: independently selected preflight anchors.
- `verifier_sha256`: SHA-256 of the reviewed comparison script's bytes.
- `inputs`: exactly the five names above, each with `sha256` and `size_bytes`.
- `source_files`: the selected 21 source paths, each with `sha256`,
  `git_blob_sha1` and `size_bytes`.

The separate expectation hash detects changed selections; it does not authenticate
the person who supplied them. Pins derived from the same retained package are
useful for reproducible comparisons, but are not independent evidence of origin.
There is no `authenticated=true`, `approved=true` or consent override input.

The archived native checker and contract are additionally pinned by reviewed
SHA-256 constants in the comparator. A caller cannot replace these pins through
the expectation. Only those two modules are loaded for `check_carrier`; arbitrary
archive code is not executed. The original source snapshot supplies the replay
inputs. Current main's collector or workflow is not substituted for the original.

## Comparisons

The comparator checks the fixed repository/owner and workflow identity; successful
manual main execution; exact source/run/attempt/job relationships; complete
single-job metadata; actor identity; and the artifact's exact ID, name, digest,
length and recorded source relationship. It checks the artifact creation window
against the selected job and records that this is a limited check, not an
artifact-attempt attestation. Expiration is inspected as recorded in the supplied
metadata, not reobserved from GitHub now.

The job log must contain exactly one **Runner Image** group within the recorded
`Set up job` interval. **Runner Image Provisioner** is a different group and is
not used as the OS image version. Duplicate, missing, nested, malformed or late
image records are rejected. The report retains the raw log digest, exact version
line and group line range, plus the carrier member/field and its digest.

The supported raw log format is timestamp-prefixed UTF-8, with an optional BOM.
The known multiline upload `path` input is narrowly supported: after its
`evidence.zip` line, only the same directory's `receipt.json`, `failure.json`
and final empty line may lack timestamps. Arbitrary continuation text and
untimestamped identity/image statements are not accepted. A different future
log representation is rejected until explicitly supported.

The log's source/request anchors, job name and upload artifact ID/name/digest/size
must agree with the selected records. Repetition of an environment anchor is
allowed only with the same value. A log-content match is still not independent
GitHub origin authentication or protection against a compromised runner.

The original outer ZIP must contain exactly `evidence.zip` and `receipt.json`.
Archive paths, duplicate members, member types, encryption, compression and
resource bounds are checked before extraction/replay. Symlink/hardlink inputs and
changing files are rejected. No input archive is extracted into the repository.

The original receipt, result, request, token-map and full selected source closure
are bound before native carrier replay. The report is produced only after a
complete `token-preflight` reconstruction; it does not rerun tokenization or
model inference. Source code is hash-selected before being loaded into a temporary
directory, which is removed on success or exception.

## Output and exit codes

| Exit | Disposition | Meaning |
| --- | --- | --- |
| 0 | `CONSISTENT_OFFLINE` | Checked retained records and image values agree |
| 2 | `REJECT_EXTERNAL_CONTRADICTION` | Internally valid carrier; image values differ |
| 1 | `REJECT_INVALID_OR_INCOMPLETE` | Missing, malformed, unsupported or inconsistent input |

**Exit 0 is not capture permission.** Every result keeps:

```text
evidence_source_authentication = not_established_by_offline_comparison
capture_consent = not_evaluated
capture_handoff_approved = false
new_execution_authorized = false
authority_effect = none
production_gate_eligible = false
current_run_evidence = false
policy_activation = false
metric_evaluated = false
```

A canonical comparison report binds the expectation, all five input byte records,
source selection, native checker identities and the observed comparator file digest.
This file digest is not an attestation of the executing process;
`verifier_execution_attested` remains false.
`--check-report` recomputes the whole comparison and requires byte equality with
that report. It does not trust a copied verdict, and it is not a signing or
capture-approval interface.

```sh
python -I -B tools/check_q3_external_postflight_v0.py \
  --expectation /absolute/path/expectation.json \
  --expectation-sha256 <reviewed-expectation-sha256> \
  --input-dir /absolute/path/retained-inputs
```

Add `--check-report /absolute/path/comparison.json` to verify a previously retained
canonical report. The script prints JSON to stdout (exit 0/2) or a bounded stable
error code to stderr (exit 1). It does not save or overwrite repository files.

## Historical compatibility and tests

The immutable historical package already preserved by #2962 is reused as the
regression fixture. There is no new copy or rewrite of the original evidence.
Run `40253690074/1` remains internally complete and externally contradictory:
startup image `20261012.334.1`, carrier image `20261023.334.3`. These values are
fixture facts, not accepted image constants in the comparator.

Tests include unchanged historical replay, synthetic image equality without
permission, mismatched metadata, source/run/job/attempt/artifact substitution,
stale request/token-map pins, unreviewed checker bytes, malformed or ambiguous
logs, archive hazards, altered claims/dispositions and canonical report replay.
Synthetic altered logs/metadata are negative or comparison controls, not newly
observed GitHub evidence and not a resolution of the original discrepancy.

The new module runs through both actual CI manifests and direct Python execution.
Combined registration is 172 Tools smoke entries and 28 targeted pytest entries.
All nine legacy literal count consumers, both cross-consumer checks and the
Pages module's manifest expectations are synchronized. Existing Pages and Q3
preservation tests remain registered. The original native schemas, profile,
collector, workflow and request constructor remain unchanged.

## Next integration boundary — explicitly not implemented here

The read-only [acquisition companion](PULSEMECH_Q3_EXTERNAL_POSTFLIGHT_ACQUISITION_v0.md)
can obtain this comparator's five inputs from exact GitHub identities and recheck
metadata after download. It leaves this offline comparator unchanged. Its saved
receipt is unsigned and cannot authenticate origin for a later reader; it does
not make comparison mandatory on any native capture entry path.

The current v0 request constructor still accepts a separately authorized capture
with an `approved_token_map_sha256`. It does not require this new comparison.
Therefore this component cannot be described as unbypassable capture enforcement.

The next increment must bind authenticated external evidence and this reviewed
comparison to request preparation, preserve the later capture's separate source
and run identities, reject copied or stale dispositions, and close every existing
native capture entry path. Any closed-schema/profile change needs an explicit
version/migration decision while retaining the original v0 reader.

After that integration is reviewed and merged, a fresh zero-generation request
may be prepared for its final exact source. Dispatch still needs explicit owner
consent. This increment grants neither that consent nor 204-response capture,
Q1 labeling, Q3 scoring, a production gate or release authority.
