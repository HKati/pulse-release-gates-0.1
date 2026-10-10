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

### Owner-bound reference dispatch credential

The reference workflow dispatches the Q2 subject with the separate repository
secret `PULSE_Q2_OWNER_DISPATCH_TOKEN`. Before the single subject POST, the
acquisition tool requests `GET https://api.github.com/user` with that same
credential and requires `login=HKati`, integer `id=128643840`, and `type=User`.
The GitHub installation token does not satisfy this owner identity. Missing,
expired, mismatched, oversized, malformed or redirected identity responses
reject before dispatch; there is no fallback, retry or run-list search.

Use an owner-created fine-grained personal access token restricted to
`HKati/pulse-release-gates-0.1`, with Actions read/write and the default metadata
read permission. The authenticated-user endpoint requires no additional
fine-grained permission. This secret is an operational prerequisite, separate
from the still-missing real release capsule. Neither is created by the code
change. The token value must not be placed in the request, plan, repository,
public artifact or review comment.

The owner secret is exposed only to the existing acquisition step. Both
reference jobs require the original actor and triggering actor to be `HKati`
and the actor ID to be `128643840`. The live acquisition CLI also reads a
bounded stable event file and compares the sender login/ID/type, repository,
ref and all three original reference inputs with its environment. A matching
request digest alone cannot authorize another actor to use the owner secret.
The existing workflow/ref/source/attempt checks and independent plan replay
remain required before dispatch.

Both event consumers accept exactly the short `main` representation or the
canonical `refs/heads/main` branch representation. The trusted environment
still requires `GITHUB_REF=refs/heads/main`; tags, other branches and arbitrary
aliases reject. This follows the full branch ref in GitHub's
[official webhook example](https://github.com/octokit/webhooks/blob/main/payload-examples/api.github.com/workflow_dispatch/payload.json).
The outbound dispatch body remains exactly `ref=main`; no request bytes or
source identities are rewritten to normalize an incoming event.

The owner transport is confined to one exact, already bound subject request.
It clears its credential reference on success or failure, rejects reuse and
cannot download artifacts or dispatch the provider. The separate
`GITHUB_TOKEN` continues to handle observation, artifact transport and the
existing Step 3F provider dispatch. It is not forwarded to the subject run:
PULSE CI receives its own run-scoped token for the two existing private-intake
consumers. The owner secret is removed from the acquisition environment and
is absent from all child-process environments and public diagnostics.
This is credential lifetime control, not a claim of memory zeroization after
SIGKILL or host loss.

The request bytes and digest remain unchanged across dispatch. The returned
current run ID remains in the separate dispatch receipt and evaluation
binding. Both Q2 consumers retain their own strict `HKati` event checks and
independent reads; a bot-origin subject invocation is still rejected.

API contracts: [authenticated user](https://docs.github.com/en/rest/users/users#get-the-authenticated-user)
and [workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

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
strings are overwritten. The existing PULSE CI `pulse` and `tools-tests`
Python setups are both pinned to that version. The tools manifest includes
the real replay regressions, so its existing smoke step first compares the
actual interpreter and Unicode database with the fixed replay profile.
Runtime drift rejects before compilation or execution of the manifest.
Unsupported environments reject without rewriting the historical summary.

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
that exact patch at exactly one `actions/setup-python` step in each of the
`pulse_ci.yml` jobs `pulse` and `tools-tests`. The latter executes the Q2
replay regressions and must satisfy the same interpreter requirement.
It retains the acquisition workflow's existing
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


## Bounded capsule publication and verified negative intake

The manual `q2_release_capsule_publication_v0.yml` workflow has two separate
jobs, `build` and `verify_download`, on Ubuntu 24.04 / CPython 3.11.16. Its only
input is `source_commit`: the reviewed main commit must equal the dispatch,
workflow, checkout and API-observed main identities. Both jobs require the
original HKati user (ID 128643840), triggering actor, main ref and first attempt.
The event and a separate 26-path publication source closure are checked before
payload transport. The existing intake source-role closure is unchanged.

Both jobs install the eight verifier dependencies exclusively from the pinned
preparation archive. The publication profile binds each wheel's name, version,
archive member, size and SHA-256. The pinned pip 24.0 bootstrap installs them
with `--no-index`, `--no-deps`, `--require-hashes`, `--only-binary=:all:` and
`--force-reinstall`; an already installed version cannot replace the verified
bytes. The receipt includes these exact dependency identities. The credentialed
supervisor uses only the standard library before this installation; installer
and semantic children receive the restricted, credential-free environment.

The closed publication profile fixes preparation artifact 11282419957
(run 37148637546/1), capture artifact 11472726606 (run 37600313529/1), their
original source commits and full archive digests, the official CPython
3.11.16 bootstrap and pip 24.0 wheel. API origin, attempt, expiry, size and
digest checks precede each download. No latest-by-name replacement, caller URL,
command, alternate profile or caller-selected interpreter is accepted.
Read-only transport credentials are absent from private build/replay children
and storage redirects. Bounded ZIP/TAR parsing, private 0700 staging, finite
process lifetimes and verified cleanup apply; an existing output is rejected.
The bootstrap TAR is hashed and parsed through the same held file descriptor.
Mutation or replacement is rejected before the extracted interpreter can run.

The builder reconstructs historical installation path strings as data and
checks the complete runtime inventory before packing. It executes the pinned
bootstrap and installer, never the reconstructed interpreter, worker or model.
All 18,499 capsule members have fixed content and modes; the only runtime
symlink is `lib64 -> lib`. Packing fixes lexical order, timestamp
2026-10-10 00:00:00, Unix attributes, DEFLATE level 6, empty extra/comment fields
and no ZIP64. The required complete ZIP is 452,116,385 bytes with SHA-256
`3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734`.
A compression or payload difference stops publication; the expected identity
must never be silently updated. The observed Python/Unicode/zlib environment
is recorded in the receipt.

Before upload, the separate checker verifies the full capsule and original
capture using the existing independent byte-comparison/replay function. These
parameters are not a fabricated authenticated intake request. The capsule
is checked by an internal `check-private` subprocess in a new, sibling private
directory. Only freshly copied, digest-checked capture/capsule archives and
supervisor-authored source context enter that directory; builder verdicts,
replay files and other residue do not. Its closed result is checked against
the expected binding, and both private directories must be removed before a
public receipt is written. This internal CLI alone cannot authenticate or
publish a receipt. The raw capsule
upload uses pinned `actions/upload-artifact`, `archive: false`, no overwrite,
one exact ZIP path and 30-day retention. The second job independently checks
the actual artifact's current run/source origin, downloads it afresh and repeats
the complete comparison. Only this job can emit `roundtrip_verified` with the
observed artifact ID. `preupload_verified` carries no future artifact ID.
A failed post-upload verification may leave an artifact but no accepted
roundtrip receipt. No workflow dispatch or release decision follows automatically.

The existing required-gate step additionally invokes
`check_q2_release_intake_v0.py --verify-recorded-negative` when either Q2
request field is present. This mode independently authenticates, reacquires,
replays and compares all metadata against the producer's fixed public record.
It requires valid input, all five checks, `metric_pass: false`, inner
`process_exit: 1`, exact request/source/run/artifact binding and verified cleanup.
A complete match atomically creates, without overwrite:

`PULSE_safe_pack_v0/artifacts/required_gate_inputs/q2_intake_independent_result_v0.json`.

Its outer exit 0 means only that the historical negative result was verified.
The original required-gate nonzero exit is retained. A zero gate exit with this
historical negative request fails closed. Missing/partial input, mismatch,
timeout, cleanup uncertainty or unsafe/stale output produces no accepted
independent result. With both request fields empty, the prior shell path remains.
The existing diagnostics upload retains both metadata files; no new PULSE CI
job or step is added. The existing `admit` API remains strictly PASS-only.

Hosted publication/roundtrip and the later owner-triggered direct PULSE CI run
are not established by local regression tests. A later request needs the actual
verified artifact ID and the then-current reviewed main commit. Direct PULSE CI
also runs its existing LlamaGuard work and can stop before Q2. The whole-runtime
reference acquirer's successful-subject requirement is unchanged and must not
be relaxed to accept this expected FAIL. The 49 eligible groups remain below
the required 50, the twelve unsupported policy requirements remain unsupported,
and issue #2879 is not closed by this publication work. No new inference,
release-host observation, ALLOW decision or production certificate is claimed.
