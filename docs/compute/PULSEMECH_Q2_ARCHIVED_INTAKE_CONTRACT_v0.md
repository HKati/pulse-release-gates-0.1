# Q2 archived capture intake and release subject comparison

## Scope and identities

Work order [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
continues from reviewed main `288bb9a45764d2a30f72fdf4c417e9dd5b3087c5`,
tree `50017e5bde2b95f75536db7e478c6e41b89ec1c3` (1,452 tracked files).
That is an implementation baseline, not the executed source of the capture.
The retained checkpoint is #2879 / `6040620549`.

The fixed evidence is:

| Binding | Fixed value |
| --- | --- |
| Repository | `HKati/pulse-release-gates-0.1` |
| Capture run / attempt | `37600313529` / `1` |
| Executed capture source | `fb7b247e24f18c5314fd44f7711bd49e15020364` |
| Capture artifact | `11472726606` |
| Archive bytes | `1809263` |
| Archive SHA-256 | `88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6` |
| Measured subject SHA-256 | `ae5f9994c2ad2d59dba57f28b194aae3b9951adc3ef9a4e220af0db80b55ae29` |
| Selected definition SHA-256 | `688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5` |
| Original checked result | 150 calls; 49 CONSISTENT, 0 INCONSISTENT, 1 UNKNOWN; 49 eligible groups; FAIL |

The definition hash identifies the selected definition. The capture-subject
hash identifies the measured subject record. The release archive hash must
identify actual, separately supplied release bytes. These three roles are never
substituted for each other. No release capsule or real release archive digest
is included in this change. `release_capsule_present=false` and the null release
artifact digest in the profile record this operational limitation; they do not
prevent comparing a separately supplied real capsule later.

No capture, supplementation, retry, model invocation, token budget increase,
workload change or threshold change belongs to this integration. Historical
source/run identities are not rebound to an implementation commit or a local
synthetic test commit. The issue remains open.

## Existing hosted sequence

The PULSE CI job retains its existing jobs and steps. The existing LlamaGuard
raw evidence, canonical summary and upload precede the required-gate runner.
The `q2_consistency_ok` plan entry is unchanged and continues to invoke
`evaluate_required_gate_v0.py`. This dispatcher has a dedicated Q2 branch;
Q2 is not a generic recipe. Its sequence is:

1. Validate the prelaunch request and trusted invocation, then acquire the two
   private archives into a fresh directory outside the checkout.
2. Check complete archived native evidence and actual release subject bytes.
3. Invoke the unchanged reducer and separate summary checker in a bounded,
   credential-free process environment.
4. Read only the closed metadata proposal, remove the private tree, verify its
   absence, and validate the public record schema.
5. Write `PULSE_safe_pack_v0/artifacts/required_gate_inputs/q2_intake_result_v0.json`
   and return the actual valid PASS / valid FAIL / invalid result code.
6. Let the existing failure-tolerant diagnostics upload observe those results.

The existing candidate-status step calls `check_q2_release_intake_v0.py` through
its admission API. It performs its own authorization and fresh downloads and
uses a separate subject/metric derivation. It does not import the producer,
reuse its private directory, accept its `input_valid` flag as evidence, or skip
checks when a generic result claims PASS. Public metadata equality is an
additional constraint after independent verification.

The six existing generic recipes retain their requirements and literal PASS
admission. Twelve other requirements remain explicitly unsupported. With
missing Q2 inputs the complete policy can still yield thirteen false gates;
only twelve of those are unsupported dispositions.

## Prelaunch request and authorization

The request schema is
[`q2_release_intake_request_v0.schema.json`](../../schemas/q2_release_intake_request_v0.schema.json).
Its two transport fields are:

| Field | Meaning |
| --- | --- |
| `q2_intake_request` | Exact UTF-8 JSON request bytes, at most 16,384 bytes |
| `q2_intake_request_sha256` | SHA-256 of those exact, externally selected bytes |

The request supplies only metadata: a request ID, prospective repository/source/
workflow/event/ref identity, the committed selection, immutable capture
expectation, concrete release artifact ID/size/digest and capsule-manifest
digest, and fixed comparison/reduction profiles. It cannot supply a shell
command, URL, local path, credential, alternate interpreter or future run ID.
The request is passed in environment variables, never interpolated into a
workflow `run` script. Whitespace affects its exact digest; the request is not
silently canonicalized or amended after launch.

The request/digest pair alone does not authorize private IO. The loader also
requires the exact committed selection file, owner `HKati`, `workflow_dispatch`,
`refs/heads/main`, PULSE CI workflow ref and workflow SHA, Linux hosted Actions,
attempt 1, the actual workspace, exact current run key, and the event file's
sender/repository/ref/four input fields. The checked-out HEAD and each Q2 source
file's Git blob and executable mode must agree with the actual workflow source
commit. Reads use Git with replacement objects, external configuration and
credential helpers disabled.

`evaluation_binding` carries the current run ID, attempt, workflow SHA and
request digest separately. The prelaunch request remains unchanged. The two
whole-runtime plan implementations independently validate this metadata and
the selected source closure. Acquisition forwards the exact fields into the
subject dispatch. Acquisition context, capture context, verifier context and
the verification job's own four-file handoff guard compare the same fields.
Offline plan reconstruction is metadata/source validation, not authorization
to retrieve private archives or a Q2 admission verdict.

## Private IO, lifetime and public output

`q2_intake_io_v0.py` holds regular file descriptors, rejects symlink path
components, hardlinked inputs and special files, and compares inode/size/time
identity around reads. Archive hashes are checked on the held descriptor used
for reading. Archives are never extracted or executed. Finite bounds are:

| Boundary | Maximum |
| --- | --- |
| Request | 16 KiB |
| Capture archive | Exact 1,809,263 bytes |
| Capture members / expanded size | Exact 658 / 5,887,691 bytes |
| Capture member | 4 MiB |
| Release capsule archive | 2 GiB |
| Release capsule members | 20,000 |
| Capsule single member / total expanded bytes | 1 GiB / 1.5 GiB |
| Intake wall-clock boundary | 240 seconds |
| Semantic subprocess / each reducer or checker | At most 210 / 60 seconds, also bounded by the remaining deadline |

Names must be normalized, bounded ASCII relative POSIX paths. Duplicate names,
traversal, directory entries, parent/file collisions, encrypted or unsupported
compression, comments, extra fields, split archives and ZIP64 are rejected.
The central directory is bounded before member objects are allocated. Member
reads check CRC and expanded size. Regular modes reject privilege bits; the
only allowed link is exactly `runtime/lib64` with target bytes `lib`.

Fresh private directories have mode 0700 and private files start at 0600.
Download snapshots become read-only before semantic processing. Download paths
are derived from numeric artifact IDs in the fixed repository. A transport
token goes only to the GitHub API request. A permitted HTTPS storage redirect
gets no Authorization or Cookie header; proxies and automatic redirects are
disabled. The request cannot choose an arbitrary network endpoint.

The token is removed from the semantic environment before the producer,
admission checker or reducer starts. Generic evaluators receive no `PULSE_Q2_*`
environment variables. The reducer/checker get a minimal environment with no
inherited transport or other credentials. Private stdout/stderr go to DEVNULL;
exceptions and timeout buffers do not enter the public formatter. The runner
records fixed suppression/rejection messages. Public diagnostic codes come
from a closed vocabulary and public result keys from a closed JSON schema.
There are no prompts, responses, tokens, signed storage URLs, arbitrary
exception strings or private paths in the public result.

Context-managed cleanup and process supervision cover normal completion,
handled errors, SIGTERM/interrupt handling and timeouts. The separate candidate
consumer owns its own subprocess group and cleanup. `verified_removed` means
the private tree was removed and its absence checked. `not_created` means no
private directory was created. A failed cleanup records `not_established` and
rejects the input. SIGKILL or host loss can prevent cleanup; neither this code
nor a public record proves deletion after those events. No storage media secure
erase or host-level sandbox isolation is asserted.

## Actual capsule comparison

The capsule schema is
[`q2_release_subject_capsule_v0.schema.json`](../../schemas/q2_release_subject_capsule_v0.schema.json).
The root contains `capsule.json` plus the exact declared payload set:

| Prefix / member | Required comparison |
| --- | --- |
| `source/PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py` | Actual worker bytes from the bound capture sources |
| `source/PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json` | Actual committed selection bytes |
| `source/PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json` | Actual model-file map bytes |
| `source/PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json` | Actual selected workload bytes |
| `model/` | All eight selected files, exact sizes/digests/modes |
| `runtime/` | All 18,485 regular inventory files, exact path/size/digest/mode, plus the one link |
| `runtime/lib64` | A symlink whose exact target is `lib` |

The eight model files are `config.json`, `generation_config.json`, `merges.txt`,
`model.safetensors`, `special_tokens_map.json`, `tokenizer.json`,
`tokenizer_config.json`, and `vocab.json`. Source payload modes are 0600, as in
the archived source copies. The capsule packaging profile requires model modes
0644; this packaging requirement does not claim a historically measured model
file mode. Runtime permission bits come from the complete captured inventory.

The comparison covers all 67 effective generation settings and the complete
recorded runtime configuration. The launch descriptor fixes the worker argv,
the selected runtime Python, `-I -B`, source root, bundle location, prelaunch
record/digest binding, capture-reference mode and subject record boundary.
The wrapper is `none`; extra wrapper code, extra payloads or launch arguments
are rejected. The launch descriptor is compared as data and never executed.

The archived native-check chain binds original prelaunch, installation,
readiness, subject, handoff, groups, manifest, summary and original source
records. It is historical evidence. Platform requirements in the manifest
(Python/bootstrap binary, OS, architecture, image, kernel and libc) are checked
for exact agreement with those archived requirements, while the release host
is explicitly `not_observed`. Manifest agreement does not attest a future
release host or re-establish the original native isolation environment.

## Unchanged replay and result meaning

`build_q2_reference_summary.py`, `check_q2_reference_summary.py`, the Q2 metric
specification and original summaries remain byte-for-byte unchanged. The replay
checks actual CPython 3.11.16 and Unicode 14.0.0 plus behavior probes; no version
strings are overwritten. The existing PULSE CI Python setup is pinned to that
version. Unsupported Python/Unicode environments reject instead of rewriting
the historical summary.

The reducer's new summary must equal the original summary bytes exactly. The
separate checker independently verifies those bytes and input bindings. The
candidate checker invokes its own checking path and reverses the reducer/
checker order. A claimed PASS with repaired outer metadata still fails when
the actual unchanged reduction does not produce it.

| Outcome | `input_valid` | `metric_pass` | Exit | Production gate |
| --- | --- | --- | --- | --- |
| Valid metric PASS | `true` | `true` | 0 | Subject to separate independent candidate admission and all existing requirements |
| Correctly checked metric FAIL | `true` | `false` | 1 | Reject |
| Missing, mismatched or invalid input / replay environment / cleanup | `false` | `null` | 2 | Reject |

For the immutable original measurement, successful input verification can only
lead to the valid FAIL row: 49 eligible groups do not satisfy the minimum 50.
An absent real capsule is an invalid intake, not a verified release subject.
Synthetic positive controls test algorithms and boundaries; production loaders
cannot select their alternate profile or historical bindings.

## Coordinated source and consumer boundaries

The existing 60 whole-runtime source roles retain their meaning. Nineteen Q2
current-source obligations, including the existing required-gate runner, make
79 current source entries. Local R2 retains its nine recorded dependencies,
deduplicating the runner already included in the current set: 87 local entries.
The five additional public R2 obligations make 92 public entries. All three
candidate pin families, workflow pins, D3/D6 pins and local recorded-input
runner pins bind the coordinated implementation bytes.

These are source closure changes. The 62 state duties, eight-job topology,
147 declared steps, six current LlamaGuard inference occurrences and current
whole-runtime terminal requirements are unchanged. The 150 historical Q2 calls
are never added as current inference occurrences. Local R2 remains a bounded
reconstruction of its existing recorded inputs, not a private Q2 replay or
independent release subject admission. Export/carrier fixtures carry the source
closure without turning a public Q2 result into private evidence.

Four new tool-test modules are registered, taking `ci/tools-tests.list` from
157 to 161 entries. They are not copied into `ci/pytest-tests.list`. Each new
module has a real pytest entry point when invoked by the tools manifest.
The regression evidence must distinguish controlled transport/process probes,
synthetic complete payload comparisons, real unchanged reducer/checker
subprocesses and any separately performed original archive-only replay. An
archive-only replay cannot prove the missing release capsule binding.

Actual commands, logs, JUnit, unique test IDs, diff and delivered-file hashes
belong in the separate NEM REPO verification package. Historical test totals
are not evidence for this implementation. No hosted execution or production
subject match is claimed by an offline test result.

## Coordinated inventory correction

The reviewed 37-file inventory is extended by two existing files:
`tests/test_q2_reference_acquisition_v0.py`. Its tools-manifest assertion also
requires the exact count 157 and must become 161 with the four registered Q2
modules. This is a count-consumer correction, with no acquisition, capture,
workload or historical source behavior changed. The second path is
`.github/workflows/repo_hygiene.yml`: its previous version guard rejects the
required CPython 3.11.16 declaration in the PULSE job. The guard now permits
that exact patch only at the single `actions/setup-python` step in
`pulse_ci.yml` job `pulse`. It retains the acquisition workflow's existing
exact patch rule and exact environment.yml equality for every other
declaration. It also checks regular pinned paths, structured/text declaration
agreement, missing/duplicate setup steps and pins moved to other jobs. No job
or step is added. The acquisition test module runs the actual guard over the
complete repository workflow set and supplies its negative controls.

The delivered inventory is therefore 26 modified existing files and 13 new
files (39 total). The complete acquisition test module is part of the offline
regression run. Historical source copies and their pins are not rewritten by
this current hygiene rule.

The runner, dispatcher, candidate builder and direct admission entry point
quarantine the entire `PULSE_Q2_` environment namespace before schema checks.
Only the dedicated transport receives the saved private invocation context.
The semantic subprocess and public formatter run without that environment.
The strict ZIP reader also checks local headers and data descriptors against
the central directory and rejects prefixes, padding and unindexed payload.
A separately authored synthetic fixture exercises the full 18,485-file runtime
cardinality, including corruption of its last file; its bytes are test data,
not the missing real release capsule.
