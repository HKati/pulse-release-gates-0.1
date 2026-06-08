## Relation binding anchor

The verifier report artifact now includes first-class relation bindings:

```text
relation_bindings
```

Relation bindings model the verified connections that make evidence eligible for future materialization.

They express relations such as:

```text
artifact → subject
artifact → run
artifact → policy
artifact → registry
artifact → digest
artifact → detector
artifact → gate
gate → policy
gate → verifier decision
```

This does not implement the verifier.

It does not make `--release-grade-materialized` permissive.

The current materialized prod path remains fail-closed until a trusted verifier is implemented and wired.

A future verifier may use relation bindings to expose transition-risk before release:

```text
missing relation
broken relation
stale relation
self-declared relation
unverified relation
```

A relation binding is not release authority.

A relation binding qualifies evidence for possible materialization only after verifier checks pass.

## Relation binding integrity checker

The verifier report relation-binding integrity checker is:

```text
PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py
```

Example command:

```text
python PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py \
  --report examples/release_evidence_verifier_report_v0.failed.example.json
```

The checker validates the verifier report schema when `jsonschema` is available, then applies relation integrity checks.

It fails closed when:

- `relation_bindings[].relation_id` values are duplicated
- `gate_materialization.*.relation_bindings[]` references a missing relation ID
- a referenced relation binding is not `verified=true`
- a `VERIFIED` gate materialization entry has no relation binding IDs
- verifier decision values use release-authority wording such as `PASS` or `ALLOW`

A `FAILED` report may have empty `gate_materialization`.

The checker does not implement the verifier.

It does not reopen `--release-grade-materialized`.

It does not replace `check_gates.py`.

It only checks whether a verifier report has internally consistent relation bindings.
