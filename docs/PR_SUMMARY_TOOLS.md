# PR summary tooling

This note documents the scripts used to post PULSE results back to
pull requests, and clarifies their intended roles.

PULSE can surface its outcomes to PRs in two main ways:

- as a human-readable Quality Ledger comment,
- as badges and structured status in the CI UI.

This document focuses on the PR comment tooling.

---

## Canonical path: safe-pack Q-Ledger commenter

The **canonical entry point** for PR comments is the script shipped
inside the safe-pack:

- `PULSE_safe_pack_v0/tools/ci/pr_comment_qledger.py`

Characteristics:

- Lives alongside the pack and its policies.
- Designed to consume the pack’s outputs (status, Quality Ledger) and
  format them into a concise PR comment.
- Intended to be called from CI workflows that already run the
  PULSE_safe_pack_v0 tooling.

Typical usage (conceptually):

- A GitHub Actions job runs the safe-pack CI.
- After the gates and Quality Ledger are produced, the workflow calls
  `pr_comment_qledger.py` with:
  - a reference to the status/ledger artefacts,
  - information about the target PR (e.g. repo, PR number, token).

Exact arguments and wiring are defined in the CI workflow files; this
script is considered the **supported** path for PR summarisation.

---

## Top-level helper: scripts/summarize_to_pr.py

The repository also contains a top-level helper:

- `scripts/summarize_to_pr.py`

This script is provided as an **example / integration helper** for
projects that want to experiment with custom PR summaries or that
cannot rely on the pack layout directly.

Characteristics:

- Lives outside the safe-pack.
- May wrap or complement the safe-pack commenter.
- Not required by the core PULSE CI and **not** treated as the primary
  API surface for PR comments.

Downstream users can:

- copy or adapt this script for their own CI setups,
- use it as a reference when building custom integrations with their
  internal tooling.

---

## Recommended usage

For this repository and for most users of the PULSE safe-pack:

- Use `PULSE_safe_pack_v0/tools/ci/pr_comment_qledger.py` as the main
  PR comment entry point.
- Consider `scripts/summarize_to_pr.py` as:
  - an example,
  - or a starting point for custom integrations, especially if you
    cannot call the safe-pack tooling directly.

For external integrations:

- Prefer scripting *around* the safe-pack outputs (status, Quality
  Ledger) rather than duplicating the core logic.
- Keep any custom PR summary scripts in your own repositories, using
  this repo’s scripts as inspiration rather than a hard dependency.

---

## Future consolidation

In future versions, parts of this structure may be consolidated further,
for example:

- a single, well-documented CLI entry point for PR summaries, or
- a small library module that is imported by both CI workflows and
  external scripts.

Until then, this document serves as the source of truth for how the
existing PR summary scripts are intended to be used.
