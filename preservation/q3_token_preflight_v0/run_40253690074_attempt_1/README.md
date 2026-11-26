# Q3 token-preflight preservation and repository regressions v0

Status: repository integration candidate for one selected historical record.
Prepared against `HKati/pulse-release-gates-0.1` commit `72e8973e54d8f94422c0dabb264b8316ac8e4de6`.

## What this directory preserves

`Q3_TOKEN_PREFLIGHT_RECONCILIATION_40253690074.zip` is the unchanged review package (2996419 bytes):

```text
SHA-256: 0a91f36c1e7e738b27ab29a5428e3243a31e9840a4907f01dceabaccceca0c4e
```

It is a **review wrapper**, not a replacement for the original Actions archive.
Inside it, `original/q3-reference-capture-40253690074-1.zip` remains unchanged:
5897022 bytes, SHA-256
`7228d89f93ea69a7129c7d1bc915f5a8b3b800f0ef862280605178c602e6f317`.
The original artifact has ID `12621038763`, run `40253690074`, attempt `1`,
acquire job `121350855532`, source
`a9de035d1b3ac227359ca78a98274abe4c9ee186`.
The unchanged prior postflight review and all 28 original regression tests are
retained inside the wrapper. The executable repository tests are readable at
`tests/test_q3_preflight_preservation_v0.py`, not just buried in the archive.

The wrapper contains recorded data, logs, source snapshots and review code.
No model weights, tokenizer distribution, wheelhouse or private credentials are
added by this integration. Masked log fields remain masked. Original source
and provenance limitations are not removed by repository publication.

## Reproduce from the repository root

```sh
python -I -B tools/check_q3_preflight_preservation_v0.py
python -m pytest -q tests/test_q3_preflight_preservation_v0.py
```

The first command intentionally returns **2** for this historical case:
internal carrier checks pass, but external runner-image reconciliation blocks
capture handoff. Exit **1** means integrity, parsing, missing data or identity
failure. Exit **0**, defined by the review helper for consistent image strings,
is not capture consent or release authority. The selected immutable historical
archive is expected to return 2, never 0. The tests assert this expected denial,
so a green regression run does not relabel the experiment as accepted.

The executable reader checks the entire wrapper's exact size and SHA-256 before
parsing. It unpacks into a temporary directory, checks the member inventory and
replays only the two pinned historical checker modules. It does not execute the
old wrapper scripts, re-tokenize, load a model, use the network, or write to the
repository. The selected source is checked against historical bytes, not against
whatever happens to be on current main. Local temporary files are removed.

## Preserved result and unresolved discrepancy

The original receipt/result remain `complete`; the inner carrier checker passes.
The record contains 204 tasks, 144752 prompt tokens and zero generation calls.
The two original image values remain different:

- Acquire startup log: `20261012.334.1`.
- Original platform record: `20261023.334.3`.

The cause is not established. The preserved review recommendation is
`REJECT_AND_REQUIRE_NEW_TOKEN_PREFLIGHT`, on the evidence currently held.
This recommendation is not a dispatch instruction, a diagnosis of token error,
or permission to overwrite the original successful-execution record.
A later review with new independently retained evidence must be appended, not
used to silently change this historical packet.

The 21-path comparison records 20 unchanged paths and one upload-artifact pin
change between historical source and the review's fixed main commit. These are
historical comparison anchors, not assertions that future main is unchanged.

## CI integration

The new test module is registered exactly once in **both** `ci/tools-tests.list`
and `ci/pytest-tests.list`. The tools manifest grows from 169 to 170 entries; the
pytest manifest grows from 25 to 26. All nine existing literal count consumers
and both count cross-checks are updated together. Existing test entries, source
pins, workflow identities and test bodies are otherwise retained.

There are 28 ported historical review regressions and 10 repository integration
regressions, including actual CLI exit-code verification, exact archive pinning,
changed/missing/short/long input rejection, symlinks, cleanup and CI registration.
These are offline tests. A test pass is not a new hosted preflight or capture.

## Deliberate boundary and next work

This commit preserves the already completed reconciliation experiment and makes
its checks continuously executable in repository CI. It does **not** implement
the next generic external postflight verifier or its enforced capture-request
binding. `NEXT_TASK_EN.txt` inside the historical wrapper remains the design
handoff for that separate implementation; the wrapper's earlier files-only
instructions record its preparation context, not repository policy.

The current native collector, request schema/profile, capture workflow, authority
chain, and Dependabot branches are unchanged. No existing capture path is claimed
to be newly enforced by this preservation reader. Native source authentication
is not re-established merely by rehashing local copies. Owner capture consent
remains a separate requirement. No new workflow, preflight, retry, generation,
Q1 label, Q3 metric or release authority is created. Keep #2879 open.

`authority_effect=none`; `production_gate_eligible=false`;
`current_run_evidence=false`; `policy_activation=false`; `metric_evaluated=false`.

Preparation tests and exact base/preimage bindings are supplied in the separate
owner validation handoff. Merge and hosted CI results must be recorded later
against their actual commit/run identities; no successful hosted run is asserted
in this file.
