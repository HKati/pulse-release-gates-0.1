# Parameter Golf v0 — mini-scope implementation plan

## Principle

This is **sidecar work**, not a new center of gravity for the repo.

The main repo remains focused on PULSE core development.
Parameter Golf only gets a narrow, well-bounded companion surface.

## Deliverables in this slice

1. `parameter_golf_v0/README.md`
2. `parameter_golf_v0/issue_129_comment_draft.md`
3. `schemas/parameter_golf_submission_evidence_v0.schema.json`
4. `tools/verify_parameter_golf_submission_v0.py`
5. `docs/parameter_golf_submission_evidence_v0.md`
6. `examples/parameter_golf_submission_evidence_v0.example.json`
7. `tests/test_parameter_golf_submission_evidence_v0.py`

## Why this slice is small enough

- no changes to `PULSE_safe_pack_v0/`
- no changes to `pulse_gate_policy_v0.yml`
- no changes to required gates
- no workflow added in v0
- no counted-path integration into the external challenge

## Suggested commit order

### Commit 1
`feat(parameter-golf): add shadow-only evidence contract v0`

Add:
- schema
- example artifact
- docs note
- folder README

### Commit 2
`feat(parameter-golf): add submission evidence verifier v0`

Add:
- verifier CLI
- local usage examples in docs

### Commit 3
`test(parameter-golf): add schema and verifier smoke tests`

Add:
- pytest coverage for example / strict mismatch / schema invalid

### Commit 4 (optional, only after community signal)
`docs(parameter-golf): add upstream discussion draft`

Add or refine:
- issue comment draft
- possible follow-up design notes based on feedback

## Definition of done

Done means:
- example validates,
- verifier returns 0 for the example,
- verifier returns non-zero on malformed evidence,
- strict mode fails on semantic mismatches,
- no normative PULSE path changed.

## Out of scope for now

- GitHub Actions workflow
- artifact upload wiring
- any PR into `openai/parameter-golf`
- any new PULSE gates
- any claim that tokenizer bytes must be counted
