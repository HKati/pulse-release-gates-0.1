# Q3 same-job runner-image observation v0

## Status and purpose

Implementation increment prepared against
`77f58886bd79bc0b8012c10a8aaea3f25c512d00`, after #2973.
This document is not a hosted execution result or authorization to dispatch.

The completed token preflight `41350046443/1` retained different image values:
`20261025.353.1` in the startup log's **Runner Image** group and
`20261026.354.1` in the native `platform.json` record. The latter is read from
`ImageVersion`; it is not computed from tokenizer output. The earlier preflight
`40253690074/1` also retains its original unresolved discrepancy.

This increment closes the missing same-job observation boundary and rejects
inconsistent or incomplete local image metadata before runtime acquisition.
It does not repair GitHub provisioning, select which conflicting label is true,
relabel historical evidence or make an inconsistent preflight admissible.

## Placement in the supported execution route

All new executable logic is in the existing source-bound
`PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py` controller.
The closed native profile still lists its original 21 source paths. No extra
executable dependency is silently inserted into that profile.

The existing manual workflow adds these observations:

1. `initial`: immediately after the exact-source checkout and **before**
   `actions/setup-python`, using isolated `/usr/bin/python3` and stdlib code.
2. `pre-sudo`: in the native step with the selected Python, immediately before
   the existing `sudo` invocation.
3. `root-entry`: in the guarded root controller, before either `execute` or
   `execute_handoff` can be called.

The first point is the earliest source-verified controller invocation. The
owner/context check and checkout precede it; this increment does **not** claim
an observation of the shell before checkout, or recover the startup moment from
a later file read. The original startup log remains a separate postflight input.

`--image-observation initial` and `--image-observation pre-sudo` are observation-
only CLI branches. They validate the real repository source, workflow context,
request and digest, then write observations and return without network access,
native acquisition, model load or tokenization. They may execute without root;
normal execution still requires the original isolated root entry guard.

The normal CLI always runs the root image gate before either native operation.
The gate does not accept an `approved` flag or a saved comparison as permission.
The v1 capture handoff still requires its original consent and fresh external
postflight. A bare v0 capture request remains rejected.

## Source selection and data minimization

The observer follows the current process's ancestor chain through `/proc` to
its actual `Runner.Worker` ancestor. It binds the process PID, process start
counter and executable path, checks the live executable inode against that path,
and derives `.setup_info` from that runner instance's root directory.

There is no directory glob, process-wide name search, environment-selected
SetupInfo filename or fallback to the first matching cached file. An unreadable,
unrecognized or ambiguous process/source is an incomplete observation.

Each point records only:

- `ImageOS` and `ImageVersion`, after bounded format validation;
- the single exact **Runner Image** group's `Image` and `Version` fields from
  that worker's `.setup_info`;
- the same two fields from the fixed `/imagegeneration/imagedata.json` path;
- each source file's byte size and SHA-256, and the observer's source SHA-256.

The **Runner Image Provisioner** group is not an image identity. Multiple image
groups, duplicate JSON keys, ambiguous case aliases, and empty, malformed or
repeated image fields reject. Every recognized field occurrence is counted
before value validation; a valid value cannot hide an invalid repetition.

No complete environment, credential file, private/internal SetupInfo group,
signed URL or raw metadata file is published. Invalid environment values are
represented by null and a stable error, not by their unfiltered content.
File reads are bounded and reject symlink/hardlink/special-file aliases.

## Bindings and comparison

Each observation binds repository, workflow, `job_key=acquire`, run ID,
attempt 1, exact source commit and the submitted request-byte digest.
The workflow is a single non-matrix acquire job. This logical job binding does
not claim an independently observed numeric API job ID; the existing external
postflight continues to bind that ID.

The phase names are fixed. Each later observation pins the exact preceding
observation bytes. The observer source must be identical across all three
records. The current process/worker identity must remain the same.
Timestamps are recorded, but no cross-process clock attestation is claimed.

The root controller requires all three points to be complete, all environment
and metadata versions to agree, `ImageOS=ubuntu24`, and both image labels to be
`ubuntu-24.04`. It also rejects changes in either source file's hash/size between
points, even when the selected version text happens to remain the same.

Possible comparison states:

| State | Meaning | Native effect |
| --- | --- | --- |
| `consistent` | Complete, correctly bound observations satisfy these local comparisons | Continue to the original native checks; no saved approval |
| `contradictory` | Complete observations disagree within or between points | Stop before either native route |
| `incomplete` | Missing, invalid, misbound, unreadable or changed records | Stop before either native route |

An observation-only CLI exit 0 means **the observation was saved**, not that its
image values are acceptable. Only the root gate evaluates the full chain.
A rejected normal controller invocation remains nonzero.

## Preservation without changing the native carrier

Records are created exclusively under:

```text
$RUNNER_TEMP/q3-runner-image/<run_id>-1/
  initial.json
  pre-sudo.json
  root-entry.json
  comparison.json
```

The sanitized JSON files use mode 0644 inside the private run directory so that
the unprivileged artifact action can read root-produced records. Existing files
and initial observation directories are never overwritten. Reads/writes are
checked; final record changes stop native entry rather than permitting execution.

Each successfully written observation is also emitted as one compact JSON line
with the prefix `Q3_RUNNER_IMAGE_OBSERVATION`. The root comparison uses
`Q3_RUNNER_IMAGE_COMPARISON`. These records therefore remain in the original
job log on both successful and failed paths. Preserve that original log along
with the native evidence; a screen excerpt is not its replacement.

On **failure only**, the workflow uploads the four explicitly named JSON paths
as `q3-runner-image-<run_id>-<attempt>`, with 30-day retention and overwrite off.
Available earlier observations can still be preserved when later stages fail.
A failure to preserve files is not reported as a complete successful observation.

A successful job still has exactly the original native artifact upload. This is
intentional: the unchanged external-postflight log parser requires a single
native upload identity, digest and size. Its strict parsing and rejection of
extra upload anchors are **not** relaxed. The diagnostic artifact is never
substituted for `q3-reference-capture-<run_id>-<attempt>`.

The original native `evidence.zip` / `receipt.json` membership is unchanged.
No new fields are inserted into native-v0 receipts, results or platform records.
The acquisition client, external comparator, handoff helper, native checker,
worker, tokenizer, fixed runtime profile and original archives remain unchanged.

## Tests and workflow classification

Regression cases extend `tests/test_q3_external_postflight_v0.py`, already
registered exactly once in both CI manifests. Existing native workflow tests
now require the two exact upload roles and the failure-only diagnostic trigger.

The normative/shadow inventory classifier's Q3 workflow SHA-256 is synchronized
to the exact changed workflow bytes. Changed permissions, triggers, retention,
name or other bytes still lose that exact-source classification; no name-based
exemption is added. This audit-preservation workflow remains non-authoritative.

Coverage includes local contradictions, sudo-boundary drift, missing and
misbound records, duplicate fields, source-file aliases, explicit process
ancestry selection, safe output, real Git-bound entry checks, rejection before
network/native callbacks, and compatibility with the unchanged postflight parser.
All synthetic controls remain synthetic; they do not identify a real hosted VM.

## Limits and next operation

This is an observation/invocation gate within the trusted runner, repository,
controller and Git database boundary, not hostile-root containment or platform
attestation. Stored records are unsigned; three matching metadata readings do
not establish the complete installed image or authenticate their producer.

The current `platform_context()` remains unchanged and still reads
`ImageVersion` without normalization. The original external postflight must
still compare the startup-log image with the native platform record. Local
consistency does not waive that later relation or the capture handoff.

The new controller/workflow bytes require a newly prepared, separately authorized
preflight from the final reviewed merge commit. Do not rerun an old attempt or
reuse a contradictory historical token-map as approved. A continued platform
metadata defect will now stop before native runtime download; merging this code
does not promise the next hosted run will be consistent.

No dispatcher, automatic retry, model call, Q1 label, Q3 metric, runtime-artifact
replacement, release policy, normative status, DOI or Software Heritage change
is included. `authority_effect=none`. Keep #2879 open.
