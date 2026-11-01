# SEC-HISTORY-01 — History cache token permissions

**Status:** source-reviewed, locally tested hardening candidate  
**Preparation base:** `77f58886bd79bc0b8012c10a8aaea3f25c512d00`  
**Authority effect:** none  
**Execution authorization:** none

## 1. Finding and bounded correction

At the preparation base, `.github/workflows/pulse_history_drift.yml`
lines 10–13 grant `contents: read` and `actions: write`. The comment at
line 12 speculates that saving/restoring the cache needs Actions scope.
The restore step starts at line 42 and the save step at line 205.

Remove only that comment and `actions: write`. Keep the explicit map:

```yaml
permissions:
  contents: read
```

This is least-privilege hardening: an unnecessary repository-token scope,
not evidence of an exploited vulnerability. It does not add an owner-only
execution policy or change the existing manual-dispatch branch behavior.
The workflow writes diagnostic files/cache/artifacts, not repository commits.

No job-level permission override, replacement credential, cache-mode override,
repository setting or new workflow trigger is introduced.

## 2. Compatibility basis at the exact cache revision

Both cache steps retain
`actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9`.
The action metadata selects `dist/restore-only/index.js` and
`dist/save-only/index.js`, respectively, under Node 24.

The reviewed distributed JavaScript, not only a moving toolkit dependency,
contains these authentication paths:

| Path | Credential source |
|---|---|
| Cache service v2, `CacheServiceClient` constructor and `getRuntimeToken` | `ACTIONS_RUNTIME_TOKEN` |
| Legacy cache HTTP client, `createHttpClient` and bearer credential handler | `ACTIONS_RUNTIME_TOKEN` |

The save and restore bundles use the runner-provided runtime credential;
the reviewed bundles contain no `GITHUB_TOKEN` reference. Removing the
repository token's `actions: write` scope does not remove that separate
runtime token or change the cache request inputs.

The same pinned cache repository's test workflow declares only
`contents: read` and defines save, restore and restored-file verification
jobs. This is supporting upstream configuration evidence, **not a retrieved
successful execution of those jobs**.

GitHub's documented cache access policy is separate from GITHUB_TOKEN
permissions. Manual `workflow_dispatch` remains eligible for the default
cache write behavior. A runner/service restriction can still prevent cache
access; this correction neither overrides nor bypasses one.

### Recorded source identities

These Git blob IDs are the identities returned for the reviewed upstream
files. The distributed bundles were inspected through the GitHub read
connector; they are not vendored or locally rebuilt by this package.

| Upstream file at the pinned revision | Git blob ID |
|---|---|
| `save/action.yml` | `1b95184507516b6b36a065e21d77e35b3acc4986` |
| `restore/action.yml` | `93352f50541fca3b088080dba6b102051220dda2` |
| `dist/save-only/index.js` | `b3a8aa37f9f7a608d7d5a63a8990b1fd4c043759` |
| `dist/restore-only/index.js` | `2427fc716c959214d22297fbf24a33c040b968bb` |
| `src/saveImpl.ts` | `70c65e4a11ba3d065ec45a1c38011c5fd2ead173` |
| `.github/workflows/workflow.yml` | `32c071d9524668455d35791ed08ea92fe69c6edd` |

Primary references:

- [Pinned save action](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/save/action.yml).
- [Pinned restore action](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/restore/action.yml).
- [Distributed save implementation](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/dist/save-only/index.js).
- [Distributed restore implementation](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/dist/restore-only/index.js).
- [Save completion and warning behavior](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/src/saveImpl.ts).
- [Pinned upstream test configuration](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/.github/workflows/workflow.yml).
- [GitHub workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).
- [GitHub dependency cache access](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

## 3. Preserved behavior

Every existing step definition, action pin, cache path, key and restore prefix
is preserved. This includes all 13 steps and all eight shell bodies. The
workflow name, manual trigger, runner, timeout and concurrency are unchanged.

The following remain unchanged:

- `logs/status_history.jsonl` and branch/run-number-scoped cache keys;
- restoration before append, and separate save guarded by history-file presence;
- append, last-two-record selection and JSON/Markdown diagnostic diff;
- summary and diagnostic artifact upload, including existing `always()` behavior;
- Python 3.11 selection and `persist-credentials: false`;
- the existing PULSE-pack invocation and its arguments.

The new tests model restored history by prepopulating a temporary history file.
They execute the actual existing append/diff scripts and selected workflow shell
bodies, not a substitute implementation. They do **not** execute the cache action,
the PULSE pack, a model, a native candidate or any GitHub API operation.

Append timestamps retain their original time-dependent semantics. Only the
snapshot/diff processing of fixed input bytes is checked for deterministic
output; this document does not claim that complete runs are byte-identical.

## 4. Tests and CI integration

Extend the existing `tests/test_reader_surface_non_interference.py` module.
Retain the original reader/export non-interference function and its helpers
byte-for-byte. Its direct entrypoint continues to run that original test and
now also runs the new History unittest group, propagating failures.

The module is already registered once in both CI manifests. Both files remain
unchanged: 174 tools entries and 30 targeted-pytest entries at the preparation
base. No new manifest entry, count-consumer change or test dependency is needed;
PyYAML is already in `requirements.txt`.

The new group covers:

- positive read-only token configuration and unchanged cache wiring;
- missing or changed cache action identity, permission expansion, job overrides,
  changed triggers, keys, paths, save guard and unexpected behavior changes;
- duplicate YAML mappings and missing/non-mapping workflow inputs;
- initial/empty/single-record history, prior history, last-two selection,
  Unicode and blank lines;
- actual append/diff behavior, input-byte preservation and deterministic diff;
- invalid or absent status, malformed history/snapshots and missing scripts;
- shell syntax, diagnostic summary and both manifest registrations.

A canonical digest freezes the parsed workflow except the top-level permission
map. An intentional future workflow or action-pin change requires reviewing
and updating that preservation assertion. It is a regression check, not a new
runtime verifier, gate or claim of authenticated execution.

Unauthorized-actor or branch rejection is not added: no repository-writing
path is being introduced. Static mutation rejection is not a live GitHub
permission-enforcement test.

## 5. Validation and remaining execution boundary

Local validation: 50 new tests passed, including 19 subtests under pytest.
The same 50 tests passed through the direct unittest helper and from the final
ZIP extraction. Runtime: CPython 3.13.5; Python 3.11 grammar was also checked.

The original reader/export test was preserved but was not run locally because
this preparation used a partial source closure, not a full repository checkout.
It remains collected and executed by the normal CI paths. The 50-case result
must not be described as the complete expanded module's result.

Not run: full repository CI, full legacy reader module, hosted Python 3.11,
actionlint, live cache save/restore, live token authorization or workflow dispatch.
Source-established compatibility is not hosted execution evidence.

The pinned cache save implementation can warn or finish without a saved cache.
Its existing behavior is unchanged. A green workflow/step is not proof of a
successful cache save, restored content identity or authorized repository write.
A future separately authorized hosted trial must inspect the actual cache
operation records rather than infer completion from the workflow conclusion.

No release policy, required gate, normative status, release-enforcement code,
Pages, OG, SARIF, Q3/W1 implementation, DOI/SWH material or repository setting
is modified. Cache history remains a diagnostic carrier, not release authority.
