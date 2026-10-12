# Q2 native release-host tokenizer contract v0

This is the implementation contract for the first native Q2 unit, Q2-1, under
open work order #2879. It implements a separately declared tokenizer/reduction
boundary. Actual owner-run acquisition and accepted evidence preservation are
still required. No native completion, full Q2 closure or Step 5C acceptance is
claimed by adding these files.

The historical capture `37600313529/1` remains a valid negative measurement:
49 eligible groups out of the required 50, metric FAIL. Publication
`38097352170/1` and capsule roundtrip are historical inputs. PULSE CI
`38098605561/1` remains FAILURE with release BLOCK. A successful new tokenizer
verification does not change any of these records.

## Fixed scope and four occurrences

Scope ID: `q2_archived_native_tokenizer_only_v0`.

| Occurrence | Execution | Required outcome |
| --- | --- | --- |
| `input_check` | Independent checker in a separate pinned verifier environment | Exit 0; complete original archives, source/projection and dependency checks |
| `tokenizer_check` | Actual capsule `runtime/bin/python -I -B`; local pinned tokenizer | Exit 0; all 150 historical records independently re-tokenized/decoded; exact original groups and manifest |
| `summary_builder` | Unchanged `build_q2_reference_summary.py`, capsule interpreter | Exit 1; exact original negative summary |
| `summary_checker` | Unchanged independent `check_q2_reference_summary.py`, capsule interpreter | Exit 0; recomputed metric remains false |

This set, argv, input producers, output roles, allowed exits and sequence are
declared before launching a subject. Missing or failed occurrences cannot be
reclassified as completed. The reducer's exit 1 is valid only in its declared
role and with the exact historical output. Other nonzero exits reject.

The privileged supervisor, source bootstrap, downloader, dependency preparation,
systemd client/barrier, deterministic receipt replay and upload Action are
collectors/preparation outside these four subject totals. No additional model
occurrence is hidden there.

No original worker CLI, `AutoModelForCausalLM`, model-weight load, forward call,
`generate`, GO or fresh Q2 response acquisition is invoked. Model weights are
byte-checked data. Tokenizer replay alone establishes no native model usability.

## Input and source contracts

- [Closed profile](../../PULSE_safe_pack_v0/profiles/q2_release_host_tokenizer_verification_v0.json)
- [Request schema](../../schemas/q2_release_host_tokenizer_request_v0.schema.json)
- [Result, prelaunch and evidence schemas](../../schemas/q2_release_host_tokenizer_result_v0.schema.json)
- [Supervisor](../../PULSE_safe_pack_v0/tools/verify_q2_release_host_tokenizer_v0.py)
- [Independent checker](../../PULSE_safe_pack_v0/tools/check_q2_release_host_tokenizer_v0.py)

The request binds exact current reviewed source, actual profile bytes and fixed
input identities. It contains no future run/job/artifact ID or arbitrary URL,
command, path, model or alternative semantic profile. Its separately supplied
SHA-256 binds exact UTF-8 bytes, including any final newline. Duplicate keys,
BOM, malformed encoding, non-finite numbers, unknown fields and bool/int
substitutions reject. Matching semantic JSON does not replace the exact-byte
digest check.

| Input | Run / attempt | Artifact | Bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| Capture | `37600313529/1` | `11472726606` | 1809263 | `88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6` |
| Preparation | `37148637546/1` | `11282419957` | 508460811 | `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9` |
| Published capsule | `38097352170/1` | `11686701538` | 452116385 | `3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734` |
| Observed roundtrip receipt | `38097352170/1` | `11686476032` | 2911 | `288880eedbff4ae812d7d2020e2c55aa4814b4d9f08076473a9755ace90bcdd0` |

The profile additionally pins the existing official CPython 3.11.16 bootstrap,
its interpreter binary, pip 24.0 and eight preserved verifier wheels. Dependency
installation uses the preserved preparation wheels with no index, resolution,
dependency expansion or compilation. The verifier environment is separate from
the capsule runtime.

The collector builds and freezes this verifier before any schema/metric helper
needs third-party dependencies. It checks the full tree, interpreter/configuration,
all eight distribution identities and every loaded dependency's origin before
using that verifier's site-packages. Cached external dependencies reject. No
verifier dependencies are installed into the bootstrap Python. Empty directories
created by venv are removed only from the fresh verifier before its closed
inventory is frozen.
Binary capsule extraction uses each inspected member's size within the fixed
archive limit; it does not apply the shared JSON-read default to large libraries
or model payloads. The shared archive reader and its default limit are unchanged.

Before importing a repository helper, the CLI performs a stdlib-only owner and
committed-source check. It rejects dirty, missing, linked or mode-changed source
and copies the exact held buffers to a root-private snapshot. Helper imports use
that snapshot. The pinned checkout/entry point, Git object database, privileged
observer, runner kernel and control plane are trust boundaries; this does not
protect against a compromised privileged runner or root.

Current origin is separately checked against GitHub main/run/job metadata and
the actual checked-out source. Fixed artifact IDs are checked against their
actual API source/run/attempt/name/size/digest/expiry. The transport never selects
latest by name or forwards the GitHub token to a redirected storage host.
Unavailable or expired inputs reject; an owner-held mirror requires a separate
reviewed transport decision.

## Materialization and native target

Original archives stay unchanged and root-private. Full inventory verification
precedes payload use. The capsule has 18499 members and 1142892836 expanded bytes,
including 18485 regular runtime files and only `runtime/lib64 -> lib`.

A fresh projection outside checkout, `/home`, `/tmp` and the service's private
`/run` provides separate archive-input, capsule, current-source, historical-data
and verifier trees. The profile closes their executable entries. Payload bytes,
shebangs, pyvenv.cfg, activation scripts, pip reports, RECORD and direct_url
metadata are retained. Historical absolute path strings remain data; the old
installation checker and original full capture CLI are not run against a
relocated tree.

The fixed projection path remains
`/var/lib/pulse-q2-tokenizer-<8-character-id>/projection`. Its run directory
contains exactly two siblings: `private` and `projection`. Preparation starts
with a root-only 0700 run directory. Before any subject launch, the run directory
and projection root become root/65534 0550. The `private` directory remains
root/root 0700 and holds acquired archives, preparation files, stderr and the
candidate receipt. Only the two fixed sibling names are visible to the subject;
private payloads are not exposed. Both siblings are removed with their enclosing
run directory on handled completion or failure.

The unchanged held-descriptor reader opens every ancestor with
`O_RDONLY | O_DIRECTORY | O_NOFOLLOW`. A traverse-only 0711 ancestor is therefore
insufficient even when ordinary file traversal succeeds. The layout supplies
directory read permission without relaxing descriptor, alias or payload checks.
Local permission regressions exercise this distinction; they do not establish
native UID-65534/systemd execution.

| Kind | Owner / group | Mode |
| --- | --- | --- |
| Directories | root / 65534 | 0550 |
| Regular archive, source, model, metadata and importable files | root / 65534 | 0440 |
| Three explicitly named capsule interpreter copies | root / 65534 | 0550 |
| Three separately named verifier interpreter copies | root / 65534 | 0550 |
| Allowed lib64 link | root / 65534 | target `lib`; no other link |

The projection records original archive modes and complete projected identities.
Archive-bound zero-byte regular payloads retain their exact empty SHA-256; the
held descriptor, no-alias, mode and mutation checks still apply. The shared
transport's nonempty-archive requirement stays unchanged.
Hardlinks, extra files/directories, escaping or additional links, inaccessible
source and any byte/mode/owner drift reject. Immutable inputs are checked again
after each service and before acceptance. Work directories are separate and
UID-65534 writable. The supervisor freezes exact outputs into distinct handoff
directories; downstream edges bind the producing occurrence as well as bytes.
Equal bytes from a different occurrence are insufficient.

The target requires actual CPython 3.11.16, Unicode 14.0.0, the exact bootstrap
binary, Ubuntu 24.04 x86_64/glibc 2.39, root, systemd PID 1 and cgroup v2. The
bootstrap archive and actual base-library inventory are rechecked. Preserved
pyvenv.cfg must resolve its original base home to this verified bootstrap.

The pinned GitHub release installer's `setup.sh` upgrades pip and can create
extra distribution metadata and bytecode. After owner/source/host authorization
and authenticated acquisition, the privileged collector prepares the stock
base library from the existing pinned archive before building the verifier or
launching any occurrence. It never executes the archived installer or pip.
This preparation remains outside the four measured subject executions.

Preparation checks the archive size/digest, interpreter digest, complete TAR
member/expanded-byte bounds, names, kinds and non-escaping links. It constructs
a separate private staging tree and applies the independent complete bootstrap
check to it before touching the installed library. The fixed profile's `lib`
directory is then removed and recreated from that verified tree; the installed
closure must match the staged inventory digest. A version downgrade or an
overwrite would leave installer extras, so neither establishes byte closure.
The interpreter binary is unchanged. Target aliases, malformed archives,
partial installation, drift or staging-cleanup failure reject and cannot start
an occurrence or produce an accepted receipt. Handled failures also retain the
collector's existing mandatory private-tree cleanup and bounded diagnostics.

The bootstrap TAR's three exact stock regular filenames containing spaces use
a closed exception list; the shared capsule ZIP name grammar is unchanged.
An unlaunchable projection rejects; no old preparation directory is recreated,
capsule bytes repaired, version patched or host interpreter substituted.

All seven archived platform fields remain present. Actual values, each equality
and `full_archived_platform_match` are recorded separately. Kernel/runner-image
drift may satisfy this declared tokenizer subset, while the original complete
platform contract stays unfulfilled. `full_release_host_verified` stays false
even if all seven fields happen to match.

The frozen independent 150-record derivation checks original slots, ordering,
watchdogs, token IDs, decoded UTF-8 text, configuration and exact groups/manifest.
Schema validation is cached only within an occurrence over the same immutable
schema bytes; no validation rule is relaxed. Imports must originate in the
verified runtime, versions/configuration must match, tokenizer IDs must remain
1/2/2, and local loads use `local_files_only=true`, `trust_remote_code=false`.

## Isolation, terminal closure and failure

Each subject uses the existing reviewed systemd barrier and external observer.
Actual process privileges, namespaces, cgroup limits, systemd properties and
private `/run` mounts are checked before EXEC. Property strings or self-reports
alone are insufficient. The service runs UID/GID 65534 with no new privileges,
empty capabilities, isolated network/AF_UNIX-only access, read-only protection,
private devices, restricted namespaces and the existing bounded memory/swap,
tasks, CPU and file limits. Credential-bearing environment is not inherited.

The phase has one 1200-second monotonic deadline. Every subject is limited to
180 seconds and remaining phase time. Cleanup shares one additional 180-second
grace deadline; it is not reset per service. The workflow cap is 30 minutes.
No retries, top-ups or alternative records are attempted. Source bootstrap is
bounded preparation before this phase; it is not a subject occurrence.

Records retain launch, completed external isolation observation, EXEC write,
EOF/real exit, cgroup/client cleanup and frozen output ordering on the supervisor
clock. UTC/control-plane clocks are distinct, with `clock_relation=not_verified`.
Limits do not measure consumption: `resource_measurement=unavailable`.

| Failure | Required behavior |
| --- | --- |
| Invalid owner, source or request | Reject before payload acquisition/execution |
| Wrong, expired, missing or changed input | Reject; no alternate artifact |
| Projection, base interpreter or module/config drift | Reject; no repair/fallback |
| Missing/reordered/changed token/text record | No native verification result |
| Wrong builder/checker exit, forged PASS or wrong producer | Reject |
| Missing actual pre-EXEC isolation, timeout or EOF | Stop/reap; no completed occurrence |
| Unverified cgroup, client or private-tree cleanup | No accepted receipt |
| Cancellation, SIGKILL or host loss | Bounded failure if possible; absent trustworthy terminal evidence remains incomplete |

The accepted result is exclusive, atomic publication after all four occurrences,
independent archive/metric/receipt reconstruction, actual cleanup and source
recheck. It cannot overwrite an existing output. A rejection may publish separate
sanitized `failure.json`; later occurrences stay explicitly `not_started`, and
an observed failed occurrence is distinct. Failed cleanup never publishes
`result.json`.

Rejected occurrences retain their declared stage, failure phase, expected exit
and actual completed exit when observed. An exit produced only by cleanup is
not a completed subject exit. The primary error and a simultaneous cleanup error
are separate. Error details use closed code vocabularies; unknown errors remain
`unknown`. A private stderr read is bounded to 128 KiB and may contribute only
one unambiguous exact-line Q2 error code. Missing, oversized, aliased, unreadable
or ambiguous diagnostics yield `unknown`; raw text is never published. This code
is a diagnostic hint, not independent evidence of the failure's root cause.

Service cleanup is validated with the unchanged source-bound cleanup checker
even after a failed execution. Its `cleanup_verified` flag cannot become true
from directory deletion alone. Failure metadata separately records run-directory
and bootstrap-snapshot deletion and preserves both deletion errors when present.
The aggregate `cleanup=verified_removed` requires all relevant directory removal
and attempted-service cleanup evidence. Incomplete service cleanup leaves the
aggregate `not_verified` even if both directory trees were removed. Cleanup
verification failure never relaxes the existing inactive/cgroup/client checks.

The tokenizer supervisor handles one expected negative terminal case after the
normal stop/reap sequence. Only the declared `summary_builder` / `reduction`
occurrence with expected exit 1, an already recorded completed exit 1, stdout
EOF and a reaped client with exit 1 is eligible. No startup failure, unexpected
exit, other occurrence or cleanup-induced exit authorizes this operation.

If systemd retains `loaded` / `failed`, the supervisor first requires
`MainPID=0`, `Result=exit-code`, `ExecMainCode=1`, `ExecMainStatus=1`, the exact
or empty service cgroup path, and an empty or removed original cgroup including
descendants. It may then issue `systemctl reset-failed` for that exact service
unit only. Missing, malformed, duplicate, oversized or inconsistent observations,
remaining processes, command failure or timeout reject. An already inactive or
unloaded service needs no reset. The original completed exit remains 1.

Resetting terminal bookkeeping does not establish cleanup. The unchanged shared
cleanup collector observes the final inactive state, original cgroup and reaped
client again, and the unchanged source-bound checker validates that record.
Only then may immutable-input rechecks and exact historical-output freezing
continue. The builder's expected negative metric cannot become PASS through
this operation; no retry or service restart is introduced.

Run `38272639609/1` remains rejected. Its failure artifact reports completed
input/tokenizer checks and the builder's expected exit 1, followed by
`capture_service_not_inactive`; it does not retain the raw systemd state, and
the summary checker never started. Local regressions use explicit systemd
doubles with real process exit/EOF and filesystem checks. They do not establish
native execution of this terminal-state correction; a new owner-run verification
and evidence review remain required.

Run `38248867903/1` remains rejected. Its recorded directory removal and null
occurrence cleanup do not establish verified service cleanup. The earlier
`38174388350/1` bootstrap failure also remains rejected. Neither historical
artifact is rewritten by this layout and diagnostic correction; a new owner-run
acquisition is still required to establish native execution of the fixed source.

## Evidence and authority boundary

The public metadata artifact's accepted inventory is exactly:

- `request.json`
- `prelaunch.json`
- `projection.json`
- `input-check.json`
- `tokenizer-check.json`
- `result.json`

Raw prompts, generated text/token records, credentials, raw environment and
private stderr do not enter this artifact. Native-derived groups/manifest/summary
remain private handoff data and are required to match the original bytes. The
metadata keeps their digests, producing occurrences, original/current identities
and source bindings. The old capsule/receipts are not rewritten.

Every accepted result fixes:

```json
{"authority_effect":"none","production_gate_eligible":false,"active_gate_eligible":false,"same_run_release_authority_eligible":false,"current_inference_count":0,"worker_launch_executed":false,"model_weights_loaded":false,"full_release_host_verified":false,"historical_metric_pass":false}
```

Offline replay independently checks closed evidence, source and original archive
bindings and recomputes the negative metric with the unchanged independent core.
It does not repeat kernel acquisition or claim another native tokenizer run.
Kernel evidence remains attributed to the source-bound privileged observer.
There is no production gate/registry/policy/authority consumer for this result.

Publication sets the final file mode and synchronizes its contents before the
exclusive link becomes visible. A failure while removing the temporary link or
synchronizing the output directory removes the newly published entry. Existing
files/directories are never overwritten or populated with failure diagnostics.
The accepted result is published only after the entire run directory (including
both siblings) and the private bootstrap snapshot have been removed. Final
publication failure produces rejection metadata when possible.

## Reviewed owner-run procedure

Prepare and review the connected implementation/tests/workflow/registrations in
one PR/upload. After owner merge and CI review, select the actual reviewed main
commit. Generate a request from that commit's files; no future source revision
or run ID is assumed here.

Example request preparation in the exact reviewed checkout:

```bash
python -I -B PULSE_safe_pack_v0/tools/check_q2_release_host_tokenizer_v0.py \
  make-request --repo-root "$PWD" --source-commit "$REVIEWED_MAIN_COMMIT" \
  > /tmp/q2-native-tokenizer-request.json
python -I -B - <<'PY'
from pathlib import Path
import hashlib
raw = Path('/tmp/q2-native-tokenizer-request.json').read_bytes().rstrip(b'\n')
print(raw.decode('utf-8'))
print(hashlib.sha256(raw).hexdigest())
PY
```

The printed one-line JSON and its matching digest are the exact dispatch inputs.
From HKati, launch **one** `Q2 native release-host tokenizer verification v0`
workflow on main, attempt 1, with `source_commit`, `native_request` and
`native_request_sha256`. This is not a PULSE CI intake or fresh capture. The
workflow can succeed while preserving the historical metric FAIL.

After the actual run, bind its genuine run/job/artifact IDs and the downloaded
metadata archive's observed size/digest. Independently inspect the exact inventory
and replay with the reviewed source and retained original inputs, named
`capture.zip`, `preparation.zip`, `capsule.zip`, `roundtrip.zip`, `bootstrap.tar.gz`:

Use a separately prepared CPython 3.11.16 verifier with exactly the eight preserved
wheel versions in this profile, installed from the byte-checked preparation
archive with the fixed pip wheel, `--no-index --no-deps --require-hashes`, and no
system site-packages. This is the same dependency preparation as the collector,
not the capsule runtime or the pytest environment. Set `Q2_PINNED_VERIFIER` to
that environment's directory. The replay CLI rejects bare Python or a different
distribution inventory before evaluating a receipt.

```bash
"$Q2_PINNED_VERIFIER/bin/python" -I -B PULSE_safe_pack_v0/tools/check_q2_release_host_tokenizer_v0.py \
  replay --repo-root "$PWD" --evidence "$DOWNLOADED_METADATA_DIRECTORY" \
  --inputs "$HELD_ORIGINAL_INPUT_DIRECTORY"
```

Replay requires the exact CPython/Unicode metric environment. It does not load
the model or invoke the original worker. Preserve only the independently reviewed
actual evidence inventory, then append the bounded checkpoint to the readiness
record. Until these steps complete, native acquisition remains unverified.

## Observed implementation checks on 2026-10-11

These checks used actual CPython 3.11.16 and Unicode 14.0.0. They are local
implementation evidence, with no GitHub/native workflow execution claimed.

| Checked scope | Observed result |
| --- | --- |
| Two new tokenizer test programs and the complete normative inventory regression module | 203 passed |
| Four existing intake/compute workflow regression modules affected by manifest registration | 311 passed |
| Selected existing Q2 acquisition registration and hygiene cases | 65 passed; 724 other cases not selected |
| Original capture, preparation, published capsule and roundtrip ZIPs through the new archive checker | Exact bytes/inventories accepted; historical 49/50 metric remains false |
| Unchanged independent metric core over actual original groups, manifest and summary | Recomputed false; original 49/50 FAIL preserved |
| Official bootstrap and actual local base-library closure, including legitimate empty files | Accepted; library inventory SHA-256 `4e4f6f3425cb415c8f78d624db1c71b0dec3aba1add068b0ca5acb512cbff5fb` |
| Clean official bootstrap, actual fixed pip and all eight original verifier wheels | Fresh verifier and dependency imports accepted; original archives/negative metric checked; bootstrap library hash unchanged |
| Full actual materialization in the collector's private `/var/lib` preparation location | Byte/inventory/mode and origin checks accepted: 18499 capsule, 658 historical, 5 input, 29 source and 195 verifier entries; ownership metadata alone is an explicit local double |
| Request/result schema and workflow shell syntax | Valid |
| Complete normative inventory | No drift; only the three declared new surfaces have new classifications |

The total is **579 distinct executed regression cases**, all successful, with no
skipped cases among those executed. Repeated targeted runs are not added to that
total. Unselected tests are outside this verification scope.

The local host has supervisord rather than systemd as PID 1 and maps only
UID/GID 0. No actual UID-65534 systemd service, genuine capsule tokenizer import,
model readiness or inference was acquired here. Explicit ownership, kernel and
transport doubles exercise validation and collector failure paths; real source
guards, descriptor IO, subprocess EOF/exit, output freezing, publication/deletion
ordering and the unchanged metric core run separately. The accepted native
result remains pending the reviewed owner-run procedure above.

## First owner-run failure and bootstrap preparation correction

Native run [`38174388350/1`](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/38174388350)
used reviewed source `c4b3873478e861b87ee2a41a4697b56cbe597c56` and exact request
digest `d73ad7af928460729afaff7fb212d2ef37449ee32b277270381555cc6f93c072`.
The Python setup log records stock pip 24.0 being replaced by pip 26.2.1. The
bootstrap closure check rejected that changed library with
`q2_replay_environment`. Artifact `11714817912` contains only `failure.json`:
all four occurrences are `not_started`, cleanup is `verified_removed`, and all
non-authorizing claims are preserved. Keep this failed run as rejected evidence.

The correction's permanent preparation tests use small synthetic TARs with
explicitly scaled member/size limits and a privilege double. They execute real
descriptor IO, extraction, independent inventory checks, replacement and cleanup;
they do not acquire native isolation or tokenizer evidence. The original large
archive and actual CPython 3.11.16 library are checked separately during local
preparation validation. A new owner-run receipt and independent replay are still
required before claiming `native_tokenizer_verified`.

Correction validation on actual CPython 3.11.16: **202 regression cases passed**
(183 contract/preparation cases and 19 workflow cases, including 26 added cases).
All 27 normative-inventory regressions also passed, for 229 distinct executed
regression cases in this correction's verification scope.
At a separately allocated local prefix, the corrected preparation rejected an
extra library file before preparation, installed the original large archive's
exact library and returned the unchanged inventory SHA-256
`4e4f6f3425cb415c8f78d624db1c71b0dec3aba1add068b0ca5acb512cbff5fb`.
These checks executed zero native occurrences and do not supersede the failed
owner run or the pending native receipt.

## Regression and remaining Q2 work

Permanent tests run via the tools manifest and explicit pytest entry points:

- [Contract, file/process, source guard and evidence regressions](../../tests/test_q2_release_host_tokenizer_v0.py)
- [Manual workflow, exact pin/classification and registration regressions](../../tests/test_q2_release_host_tokenizer_workflow_v0.py)

Fixture ownership/kernel/protocol/transport tests are labeled as fixtures. Real
descriptor/permission-mode, Git source, subprocess EOF/exit and unchanged
reducer/checker tests establish those implementation behaviors. They establish
no systemd isolation, genuine tokenizer runtime, model readiness or new inference.
Actual regression results must be reported separately from owner-run evidence.

The next obligations remain finite: Q2-2 model readiness without inference;
Q2-3 the unchanged worker's complete BIND, 150 PREPARE/GENERATE exchanges,
FINISH/session-end/exit-0 protocol with separately consented 150 fresh calls;
Q2-4 independent candidate/historical comparison and exact preservation. A full
Q2-3 run may supply Q2-2 readiness evidence to avoid a redundant run. Early EOF
or killing the original worker before generation is not clean protocol completion.
Historical 49/50 FAIL is never topped up or replaced. Other unavailable gates,
Step 5C/5D, measurement and release authority stay separate; keep #2879 open.
