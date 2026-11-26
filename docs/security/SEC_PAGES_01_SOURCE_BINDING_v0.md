# SEC-PAGES-01 — Pages publication source binding v0

Status: implementation candidate; publication-source verification only.
Preparation baseline: `72e8973e54d8f94422c0dabb264b8316ac8e4de6`.
Repository: `HKati/pulse-release-gates-0.1` (`1061766508`).
Owner: `HKati` (`128643840`).

## Confirmed gap and bounded correction

At the preparation baseline, `.github/workflows/publish_report_pages.yml`
accepted a manually supplied `run_id` directly (lines 61–64), selected a
successful main-branch run without the automatic path's push-event filter
(lines 69–82), and passed only the run ID and artifact name to the downloader
(lines 144–151). The optional Pages cancellation ran before the artifact was
accepted (lines 102–136). A successful download did not establish the permitted
repository/workflow/run/commit/artifact relationship.

This is a source-admission defect, not evidence of exploitation or repository
compromise. The correction is confined to this publishing workflow, its new
read-only guard, documentation and test integration. The optional cancellation
helper is preserved, but it is reached only after source verification, site
preparation, parity checking, Pages artifact upload and final revalidation.

## Accepted publisher and producer

The publisher must run in the fixed repository on `refs/heads/main`, using
`.github/workflows/publish_report_pages.yml@refs/heads/main`. The triggering SHA,
workflow SHA and checkout HEAD must agree. The tracked checkout must be clean;
the workflow and guard bytes must equal their recorded Git blobs. The publisher
checks out its own workflow SHA, never the upstream report's revision.

A manual publication requires HKati as original actor, payload sender and
triggering actor, with the fixed account ID checked where provided by GitHub.
A publisher rerun also requires HKati as triggering actor. Automatic publication
does not require a particular upstream push actor: its source must satisfy the
same fixed repository and producer checks. A job rejected by the preliminary
condition is skipped, not a successful authorized publication.

All three selections enter the same guard:

1. The completed `workflow_run` event's run ID.
2. A canonical positive decimal manual run ID.
3. The newest result from the successful/main/push producer-run query.

Selection is not authorization. The selected run must identify PULSE CI workflow
ID `191471316`, path `.github/workflows/pulse_ci.yml`, the fixed repository and
non-fork head repository, `completed`, `success`, `push` and `main`. Its exact
`head_sha` must match `head_commit.id`; a separate Git commit lookup must return
that SHA and a valid tree SHA. The event snapshot and live API result must agree
for the automatic route. Invalid latest candidates are rejected, not skipped in
favor of an older one. An empty query fails closed.

Historical successful main/push runs remain eligible when all checks pass; their
source SHA need not equal the current main tip or publisher SHA. This does not
assert current freshness, continued reachability from main, or release authority.

## Artifact acceptance and safe acquisition

The selected run must contain exactly one `pulse-report`. Paginated listing must
be complete and stable; duplicates, ambiguity and expired entries fail closed.
The exact artifact-ID lookup must agree with the listing. Its run ID, repository
IDs, branch and source SHA must match the accepted producer run.

A GitHub-provided `sha256:` digest is mandatory. Download uses the exact artifact
ID, not a second name-based selection. The downloaded ZIP size and SHA-256 must
match the accepted metadata before extraction. After download, live run and
artifact metadata are read again and must remain unchanged.

The guard's network client performs GET requests only. It does not forward the
GitHub Authorization header across the download redirect. The redirected request
is unauthenticated, HTTPS-only, and confined to the declared GitHub Actions/Azure
artifact-storage host suffixes. API and subsequent storage redirects are not
followed. No secrets or signed storage URLs enter the receipt or error output.

The whole ZIP member list is checked before extraction. Absolute paths, parent
traversal, `.git` components, duplicate/case-colliding paths, file/directory
collisions, encrypted entries, symlinks and other special file types are rejected.
Only stored/deflated ZIP entries are supported. Files become non-executable data
under `_artifact`; no artifact-supplied code is invoked by this guard.

Explicit admission limits: 100 MiB compressed, 512 MiB expanded, 10,000 entries,
and 1,000 artifact-list results. Member names use ASCII letters, digits and
`_./@+ =,-`; shell metacharacters, control characters and other characters are
rejected, not rewritten. This bounds inputs to the existing shell-based summary.
These limits and the digest requirement are intentional compatibility constraints.
An older artifact missing a digest is not silently treated as verified.

## Run-attempt evidence limitation

GitHub's documented artifact object includes a run ID, source SHA and timestamps,
but not an independently bound artifact `run_attempt`. The receipt therefore
records `artifact_run_attempt: null` and
`attempt_evidence: creation_window_only_no_artifact_attempt_id`.

The observed run attempt is recorded separately. Artifact creation/update times
must fall within the observed run's start/completion window. For reruns, creation
at the exact second of the start is rejected as ambiguous. Earlier artifacts and
metadata changes are rejected. This temporal check is not an artifact-attempt
attestation and must not be described as one. The accepted binding scope is the
repository, producer workflow, run, commit and exact artifact bytes.

## Receipt and revalidation

The local receipt `_pages_binding/binding.json` records publisher identity,
upstream run and tree identity, exact artifact metadata, ZIP SHA-256, extracted
file sizes/hashes, selection mode and the validated optional cancellation ID.
It contains `authority_effect: none` and
`binding_scope: publication_source_not_release_authority`.

Before Pages configuration and again immediately before optional cancellation
and deployment, the guard rechecks publisher/checkout identity, live source
metadata, ZIP bytes and the extracted file manifest. The receipt is published
as `_site/diagnostics/pages_source_binding_v0.json`. It is a diagnostic record,
not a new required gate or an independent attestation.

The optional cancellation input is restricted to a positive decimal deployment
ID or a 40-character lowercase hexadecimal SHA. Its POST is not performed by the
source guard. The existing workflow helper sends it only after the preceding
checks succeed, without redirect-following. There is no fallback source, force
operation, automatic source top-up or retry introduced by this package.

## Preserved behavior and permissions

The 12 existing site-generation, schema/diagnostics, summary, parity, Pages
upload/deployment and SEO steps retain their complete parsed definitions. Tests
pin those definitions to the preparation baseline. The existing site-root choice,
landing content, URLs, report/status handling and Paradox processing are not
redesigned. The additional receipt is the sole new published diagnostic file.

Permissions remain `contents: read`, `actions: read`, `pages: write` and
`id-token: write`; concurrency and the `github-pages` environment are preserved.
No repository-content writing path is introduced. SARIF, History & Drift, OG,
normative policy, required gates, enforcement code, DOI/SWH and repository
settings are outside this change.

## Tests and acceptance limits

`tests/test_check_pages_source_binding_v0.py` uses synthetic API/ZIP fixtures and
isolated local Git fixtures without remotes. It tests positive execution,
unauthorized and incomplete identities, metadata drift, unsafe archives,
credential boundaries, CLI behavior, workflow order, preserved steps and manifest
integration. It is registered exactly once in both CI manifests. All nine
existing tools-manifest count consumers and both cross-consumer checks advance
together from 169 to 170; the pytest manifest advances from 25 to 26.

Local tests do not establish hosted execution, actual GitHub token enforcement,
a live Pages deployment, or scientific validity of report contents. The receipt
relies on GitHub-provided metadata and trusted publisher code; it is not a
cryptographic producer signature. The change does not protect against replacement
of the trusted workflow, runner compromise, or malicious content already accepted
into trusted main. No claim of HTML/JavaScript sanitization or release authority
is made. The PR head requires its own CI and review; an operational publication
requires a separately authorized execution.

## Primary API references

- [Artifact metadata, listing and download](https://docs.github.com/en/rest/actions/artifacts)
- [Workflow-run metadata and selection](https://docs.github.com/en/rest/actions/workflow-runs)
- [GitHub workflow context and identity](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
