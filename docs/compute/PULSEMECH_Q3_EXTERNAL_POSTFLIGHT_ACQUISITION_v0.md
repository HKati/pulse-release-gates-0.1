# Q3 external postflight acquisition v0

Status: implementation candidate for read-only external record acquisition.
Preparation base: `25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5`.
Tracking: #2879 remains open.

## Scope and next integration boundary

`tools/acquire_q3_external_postflight_v0.py` is the acquisition companion to the
merged offline comparator. It obtains the five comparison inputs from exact,
caller-selected GitHub identities and passes the retained bytes directly to the
reviewed comparator. It does not change the original native request, collector,
worker, profile, schema or workflow.

This increment implements the transport/acquisition part of the external-source
work. It is **not mandatory capture-handoff enforcement**, and it does not finish
portable origin authentication. The existing native capture entry points still
do not require this component. No capture permission follows from its exit code.

The offline comparator stays byte-identical to the merged #2966 correction. Its
reviewed SHA-256 is:

```text
a0bbeb20ae368992883747277946f78a4926ffd71a276756ee611a81a047d16b
```

The companion verifies and compiles those exact source bytes before acquisition;
it does not import an unchecked replacement or cached comparator bytecode.
The comparator continues to load only its two reviewed historical native-checker
modules, under its existing source and archive bounds.

## Closed, independently selected request

The caller supplies a UTF-8 JSON file and its separately selected SHA-256.
The request has exactly these fields:

| Field | Required value or role |
| --- | --- |
| `record_type` | `q3_external_postflight_acquisition_request_v0` |
| `repository` | `HKati/pulse-release-gates-0.1` |
| `source_commit` | Exact original preflight source, 40 lowercase hexadecimal characters |
| `run_id` | Canonical positive decimal string |
| `run_attempt` | Integer `1` |
| `job_id`, `artifact_id` | Exact positive integer identities; booleans are not integers here |
| `request_sha256`, `token_map_sha256` | Separately reviewed preflight identities |
| `archive` | Exactly `sha256` and `size_bytes` for the original outer Actions ZIP |
| `source_files` | The comparator's existing closed 21-file source selection, with SHA-256, Git blob SHA-1 and byte count for each path |
| `comparator_sha256` | The reviewed comparator digest above |
| `acquirer_sha256` | SHA-256 of the reviewed acquisition script bytes |

The request cannot provide arbitrary URLs, an alternative repository, an
`authenticated` flag, a capture approval, or a synthetic provider. Its JSON,
identity, source-selection and implementation bindings are checked before network
access or output-directory creation. Duplicate JSON keys are rejected.

The original archive, request, token-map and source identities must be reviewed
independently of the acquired response set. The acquisition code does not infer
these anchors from whichever run is latest, from an archive filename, or from a
copied successful disposition. Implementation-file digests detect substitutions;
they are not process-execution attestations.

## Read-only acquisition sequence

All API routes are constructed from the fixed repository and selected integers.
There is no latest-run search, retry, workflow dispatch, cancellation, rerun,
repository write, issue update or artifact deletion.

1. Read the selected run-attempt record, complete attempt-specific jobs listing,
   and exact artifact metadata. Retain each response body unchanged.
2. Apply the comparator's metadata bindings before downloading either payload.
   Require the single selected `acquire` job and an unexpired artifact. Check
   the declared expiration against the acquisition process's current UTC clock.
3. Download the exact original artifact ZIP and selected raw job log. Verify
   original archive size and SHA-256 against the reviewed selection.
4. Read all three metadata records again, retain both observations, revalidate
   their bindings and expiration, and require equal parsed JSON values. Raw
   formatting differences remain preserved. Any value change, including an
   ancillary field, rejects conservatively in this v0 implementation.
5. Build the existing comparator expectation from the reviewed identity anchors
   and actual acquired-byte digests. Run the unchanged comparator. Preserve its
   canonical expectation and comparison report.
6. Write the acquisition record and closed inventory. A partial attempt retains
   available complete responses and a failure record instead of a successful
   comparison. There is no automatic retry or completion of missing data.

There are eight logical reads on a completed sequence. The archive and job-log
reads each require a separate API redirect and storage GET, for ten HTTP requests.
The single-job contract rejects additional jobs or pagination instead of silently
using only the first page.

## Transport boundary

The implementation uses only GET, verified HTTPS, the local CA trust store, a
fixed GitHub API origin, and the pinned `2022-11-28` API version. It disables
implicit redirect following, environment-proxy discovery and cookie persistence.
No caller-supplied API host or transport adapter is available through the CLI.

An API token is read only from `GITHUB_TOKEN`. The operation needs read access to
Actions records; it does not need a repository-write token. Never paste a token
into a selection file, command argument, issue or preservation record.

The two download endpoints must return exactly HTTP 302. The Location is accepted
only from that verified API response and only when it is an HTTPS URL on a
supported `*.blob.core.windows.net` or `*.actions.githubusercontent.com` host.
Userinfo, explicit ports, fragments, control characters, backslashes, malformed
hostnames and a second redirect are rejected. These suffixes are a bounded
implementation allowlist, not a claim that every future GitHub storage endpoint
is covered. An unsupported provider change requires explicit code review.

The storage GET is constructed separately, without the GitHub Authorization
header or GitHub API headers. Signed storage URLs are not written to the receipt;
only the download hostname, fixed API route, response size and digest are recorded.
Original API/log contents are retained as evidence and are not silently redacted.

Metadata bodies are bounded to 4 MiB each, the raw log to 16 MiB and the original
ZIP to 64 MiB and its independently selected size. Content encoding must be absent
or identity. Duplicate security-relevant headers, non-200 payload responses,
invalid lengths, over-limit or truncated bodies reject. A 180-second monotonic
budget is checked around network operations and between streamed chunks, with a
maximum 20-second socket timeout per operation. This is not an independent
hard-kill supervisor; a blocked I/O operation may reach its socket timeout.

The trust boundary is the reviewed process, local filesystem/clock/CA store,
GitHub service, and API-selected storage. It is not protection against a
compromised runner, trusted process, operating system, CA store or GitHub account.

## Preservation and interpretation

The output is a new exclusive directory below an existing trusted parent, with
mode 0700 and ordinary mode-0600 files. Parent traversal does not follow symlinks.
Existing directories and members are never replaced. Complete writes are read
back; inventory finalization rechecks file types, link counts, modes and bytes.

Completed output contains:

```text
selection.json
run.json
jobs.json
artifact.json
artifact.zip
job.log
run.after.json
jobs.after.json
artifact.after.json
expectation.json
comparison.json
acquisition.json
inventory.json
```

On failure, `failure.json` replaces the successful acquisition outcome; only the
complete responses already retained are inventoried. Failed/incomplete HTTP
response bodies are not represented as complete inputs. An output-write or
inventory failure is reported as incomplete preservation, not a PASS. The
inventory excludes only its own bytes. Neither receipt nor inventory is signed.

| Exit | Meaning |
| --- | --- |
| `0` | Acquisition completed and the comparator returned `CONSISTENT_OFFLINE` |
| `2` | Acquisition completed and the comparator preserved `REJECT_EXTERNAL_CONTRADICTION` |
| `1` | Selection, acquisition, comparison or preservation was invalid/incomplete |

`status=complete` describes acquisition completion, not approval of the historical
preflight. A runner-image contradiction therefore remains exit 2. The original
`40253690074/1` receipt/result and evidence archive are never rewritten.

A live verified-TLS response is an observation obtained within this declared
transport trust boundary. **A later reader cannot establish that this observation
really happened merely by trusting the unsigned saved receipt.** Every receipt
keeps `saved_record_authenticates_origin=false`,
`verifier_execution_attested=false` and `artifact_attempt_attestation=null`.
The nested offline comparison retains its original
`evidence_source_authentication=not_established_by_offline_comparison` value.

Every outcome also retains `capture_handoff_approved=false`,
`new_execution_authorized=false`, `production_gate_eligible=false`,
`current_run_evidence=false`, `policy_activation=false`,
`capture_consent=not_evaluated` and `authority_effect=none`.
No model, tokenizer, Q1 labeling or Q3 metric is executed by this tool.

## Invocation boundary

Selection validation has no network or output-directory side effect:

```sh
python -I -B tools/acquire_q3_external_postflight_v0.py \
  --selection /absolute/reviewed-selection.json \
  --selection-sha256 <independently-reviewed-selection-sha256> \
  --validate-selection-only
```

Read-only retrieval additionally requires `GITHUB_TOKEN`, an explicitly new
output directory and `--allow-network`. Those options authorize only retrieval
of existing records; they do not authorize a native Q3 phase.

```sh
python -I -B tools/acquire_q3_external_postflight_v0.py \
  --selection /absolute/reviewed-selection.json \
  --selection-sha256 <independently-reviewed-selection-sha256> \
  --output-dir /absolute/trusted-parent/new-acquisition \
  --allow-network
```

No live selection or new run request is supplied by this implementation delivery.
The Linux no-follow file operations follow the existing comparator's platform
boundary. Python 3.11 is the target grammar; local preparation tests do not alone
qualify hosted Python/runtime behavior.

## Tests and remaining capture work

The existing `tests/test_q3_external_postflight_v0.py` is extended, not replaced
by an unregistered new test module. It is already listed once in both CI
manifests. At the preparation base there are 174 Tools smoke entries and 30
pytest entries. Both manifests, their order, all count expectations, and the
existing 194 comparator tests remain unchanged by this increment.

Acquisition tests use in-process synthetic transport/HTTP responses over the
preserved fixture. They cover selection bindings, metadata changes, expiry,
archive substitution, token isolation, redirect policy, resource bounds,
partial preservation, output non-replacement, and CLI boundaries. They do not
establish a live GitHub download, attestation or new native observation.

The next capture integration must consume a fresh acquisition inside a reviewed
trusted controller, or verify a separately designed durable origin attestation.
It must not accept a saved acquisition JSON as proof of origin. It must bind the
preflight to the later capture's distinct request/source/run, require separate
owner consent, prevent copied/stale approvals and close every native capture
entry path. Closed v0 schemas/readers and historical replay require an explicit
version/migration decision. This delivery does not change that contract or
silently enable the existing capture path.

## Primary API references

- [Workflow run attempts](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run-attempt).
- [Attempt-specific jobs](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt).
- [Raw job-log download](https://docs.github.com/en/rest/actions/workflow-jobs#download-job-logs-for-a-workflow-run).
- [Exact artifact metadata and download](https://docs.github.com/en/rest/actions/artifacts).
