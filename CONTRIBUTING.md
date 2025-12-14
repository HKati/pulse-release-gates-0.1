# Contributing

Thanks for contributing to PULSE!

---

## Local development

Quick checks (examples):
- Run PULSE (baseline):
  `python PULSE_safe_pack_v0/tools/run_all.py`

- Run unit tests (if applicable in your change):
  `pytest -q`

Tip: If you use conda, prefer the repo's `environment.yml` to match CI as closely as possible.

---

## Commit style: Conventional Commits
Use Conventional Commits for PR titles and commit messages:

- `feat(gates): add refusal-delta gate to required set`
- `fix(ci): add actions:read permission to Pages workflow`
- `docs(citation): add ORCID and arXiv link`
- `chore(repo): add CODEOWNERS and PR template`
- `refactor(pack): simplify run_all entrypoint`
- `test(q-ledger): add regression test for p95 latency`

---

## How to contribute (fast path)

1) Open an issue first (unless it's a trivial typo).
   - Bug: use **Bug report**
   - Docs: use **Documentation**
   - Feature: use **Feature request**
2) Keep changes PR-sized and link the issue in the PR (e.g., `Closes #123`).
3) Do not post security vulnerabilities in public issues.
   Please use the Security Policy (see `SECURITY.md`).

Types: feat, fix, docs, chore, ci, refactor, perf, test, build.  
Keep the title ≤ 72 chars; explain **Why** and **How** in the body.

---
  
## DCO (Developer Certificate of Origin)
All commits must be signed off:

- CLI: `git commit -s -m "feat: message"`
- GitHub web editor: add a last line to the commit message:
  `Signed-off-by: Your Name <your@email.example>`

The name/email must match your GitHub account.  
By signing off, you certify you have the right to submit the work under the project license.

---

## Changelog
Update `CHANGELOG.md` under **[Unreleased]** with your changes (Added/Changed/Fixed/Security/Docs).  
Policy/threshold changes must include rationale and update `profiles/` + `docs/`.

## PR checklist
- PULSE CI is green.
- Quality Ledger attached (link to Pages if enabled, or artifact).
- Badges updated by CI.
- If profiles/thresholds changed: rationale + docs.

---

## Automated review (Codex)

This GitHub repository is configured to use Codex
(`chatgpt-codex-connector` bot) as an external AI reviewer for pull
requests. Codex itself is not part of the PULSE codebase; it runs as a
GitHub integration.

Codex is triggered when you:

- open a PR for review,
- mark a draft as ready,
- or comment `@codex review` on a PR.
...

Codex comments are advisory. Maintainers make the final decision.

Please do not include secrets, credentials, or sensitive data in PR descriptions,
logs, or artifacts. If you prefer not to receive an automated Codex review,
mention it explicitly in the PR description.

