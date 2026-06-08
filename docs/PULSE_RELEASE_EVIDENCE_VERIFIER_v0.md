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
