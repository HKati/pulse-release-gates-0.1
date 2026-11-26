# SEC-OG-01 — bounded OG image repository write

Status: prepared hardening candidate; no hosted workflow execution is claimed.
Scope: `.github/workflows/make_org.yml` and its supporting guard/regressions.
The workflow filename is intentionally preserved.

## Source and integration baseline

Repository: `HKati/pulse-release-gates-0.1` (repository ID `1061766508`).
The source inspection used main commit
`0be50ccf71dffdbcfc1cc57b2aeb767ead868c4d`.
The inspected `make_org.yml` Git blob is
`17782376f0c82f6b67cde620861c0d9f5bbd9a58`.

The replacement-file integration baseline is the reviewed/read-only snapshot
of PR #2959 at `b44ba8c33dc25c311e9dd864e46224dba1ce20fe`, including its
Anchor Integrity registration and synchronized 168-entry tools manifest.
That PR was still open at preparation. This does not designate its head as an
accepted main commit or authorize its merge. Apply this separate work package
only after #2959 is accepted and merged, and only if the affected source files
still match the separately supplied baseline inventory. A squash-merge SHA
may differ; the exact affected-file Git blobs are the comparison anchors.
Do not apply these full manifest replacements to the earlier main snapshot.

The new test brings the integrated tools manifest to 169 entries and the
pytest manifest to 25 entries. All nine existing literal count consumers and
the two cross-consumer regex checks move together. The already prepared
Dependabot/workflow-pin corrections in this baseline are preserved.

## Findings: confirmed source gaps versus preventive hardening

In the inspected workflow:

- Lines 22–36 allocate `contents: write` to the entire generation job without
  an owner/ref/source authorization guard in that job.
- Lines 43–80 install Pillow and generate the image in that same write-capable
  job. This establishes the permission scope, not exploitation of a dependency.
- Lines 82–102 stage one named output, but do not independently verify the
  complete staged/committed path set, exact parent, or explicit target ref.
- Lines 100–102 put the token in the local remote URL and perform a bare
  `git push`. The no-change path at lines 92–95 already exists and is preserved.

Missing explicit authorization and complete write-scope verification are
confirmed gaps relative to the owner-only/one-file requirement. Job separation,
nonpersistent authentication and strict PNG intake are preventive hardening.
No unauthorized write, token disclosure, repository compromise, or link to an
external incident is established by this source review.

Source permalink:
https://github.com/HKati/pulse-release-gates-0.1/blob/0be50ccf71dffdbcfc1cc57b2aeb767ead868c4d/.github/workflows/make_org.yml

## Authorization and execution

Only a `workflow_dispatch` from `refs/heads/main` in the fixed repository is
eligible. The repository name/ID, owner name/ID (`HKati`, `128643840`), original
actor name/ID, triggering actor, workflow path/ref, workflow SHA and source SHA
are checked. Missing or mismatched identity is rejected. GitHub-provided event
repository/owner/sender metadata is checked as well.

The read-only job rejects unauthorized context before checkout, so denial is
not presented as a successful authorized write. Both jobs check out the exact
`${{ github.sha }}` with `persist-credentials: false`. The trusted guard checks
the actual Git HEAD and a clean checkout. The write-capable job also has an
explicit authorization condition before it is allocated.

The source must be an exact, tracked `100644` ordinary file within the checkout.
Absolute/traversing/noncanonical paths, control characters, symlinks, hardlinks
and changed source bytes are rejected. Input bytes are bounded to 64 MiB.
The input color retains the original Pillow color interpretation.

Generation retains the original sequence:
`convert("RGB")` -> `ImageOps.contain((1200, 630))` -> background canvas ->
centered paste -> PNG. There is no crop. Python 3.11 and `Pillow>=10,<12` remain
the generation job's existing dependency choices; the writer does not install
or import Pillow. Changes to dependency pins are outside this package.

## Data-only handoff

The read-only job uploads exactly an image and a closed JSON receipt under an
artifact name containing both run ID and attempt. The writer selects the exact
artifact ID output by that job, within the current run. It does not accept a
user-supplied artifact name, alternate repository or alternate run ID.
The pinned download action is configured with `digest-mismatch: error`.

The writer independently checks the candidate's exact two-file set, its source
Git blob and source hash, all expected context fields, current run/attempt,
output SHA-256, output length and fixed output path. The expected PNG hash is
also passed through the producing job's output. The receipt cannot authorize
itself by claiming another actor, source or attempt.

PNG validation uses the standard library: signature, exact 1200x630 8-bit RGB
IHDR, chunk order/CRC, bounded IDAT decompression, row filters, IEND and absence
of trailing content. Only the IHDR/IDAT/IEND subset emitted by this generator is
accepted. PNG intake is bounded to 8 MiB. It does not execute artifact code.

A rerun of only the writer cannot relabel an artifact from an earlier attempt.
Such a mismatch is rejected. A new authorized full run/attempt must regenerate
the candidate; there is no automatic retry or fallback.

## One-file commit and exact-tip push

The only permitted changed path is `og_image_1200x630.png`, mode `100644`.
An unchanged image returns `unchanged_no_commit_no_push` without creating a
commit or requiring a push token. Creation of an absent output is supported.

For a changed image, Git plumbing constructs the blob/tree/commit without
project hooks or attributes filters. The staged path set, committed path set,
sole parent and committed image bytes are checked. Unexpected staged paths
or a modified source checkout cause rejection.

The push has one explicit `<verified commit>:refs/heads/main` refspec and a fixed
HTTPS repository URL. A temporary trusted pre-push hook requires the advertised
old remote SHA to equal the source SHA, and checks the exact sole ref-update
tuple. This rejects advances, rewinds, deletion and other refs. Normal Git
server-side old-object checks remain in force. There is no force push,
force-with-lease, rebase, permission escalation, alternate credential or retry.
An unconfirmed push result is not reported as success or automatically repeated.

Global/system Git config and inherited Git environment overrides are excluded.
Dangerous local redirects/credential settings are rejected. Authentication uses
a temporary askpass helper whose file contains no token literal. The token is
passed only in the push process environment and is not written into the remote
URL or repository config. Temporary hook/askpass files are removed on exit.

## Permission and trust limits

Generation: `contents: read`. Writer: `contents: write`, with no additional
permission classes. The token's maximum existing permission is not broadened.
However, `contents: write` is still a repository-scoped capability, not a
server-enforced per-file token. The bounded write relies on the reviewed
workflow/guard, pinned actions, trusted GitHub context and hosted runner.

This is not a defense against a principal who can replace those trusted
controls or compromise the runner/platform. Existing branch protections are
not changed or bypassed. A server refusal remains a refusal. A successful
hosted authorization/permission test has not been performed here.

The generated receipt is a publication/asset-write candidate, not release
approval. No release gate, normative status, required set, policy or authority
code is changed. Pages, History & Drift and SARIF are separate unchanged tasks.

## Tests and execution scope

`tests/test_make_og_write_boundary_v0.py` is registered once in both existing CI
manifests. It runs through pytest or directly as a smoke program. It requires
only the existing pytest/PyYAML test stack, not Pillow installation in CI.

It covers allowed/denied identity, missing/mismatched source, closed receipts,
stale attempts, exact artifact selection, malformed PNGs, extra staged paths,
one-file commit construction, unchanged/absent outputs, actual local bare-repo
pushes, stale remote advances/rewinds/deletion, and workflow permission wiring.
The generation choreography has an explicit narrow Pillow test substitute.

Separate preparation validation compares the original transform with the
candidate using real Pillow 11.3.0 on 12 synthetic image/color cases. Those are
local byte-parity checks, not a GitHub-hosted generation result.

The preparation report records actual test counts, environment, final ZIP
replay and affected-file hashes. Existing Q2/Q3/compute manifest sections are
also executed from their source; that narrower check is not described as full
module execution. No full repository suite, hosted permission boundary,
GitHub push, workflow dispatch, merge or deployment is claimed.

References:
- https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
- https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
- https://git-scm.com/docs/githooks#_pre_push
- https://github.com/actions/download-artifact/blob/9000827ccba6bdab643e8b6fd33ac0654aef8333/action.yml
