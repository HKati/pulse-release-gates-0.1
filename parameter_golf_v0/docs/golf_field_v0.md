# Golf Field v0

Status: shadow-only draft  
Version: 0.1.0  
Scope: field observability over Parameter Golf claim streams

## Purpose

`golf_field_v0` is a shadow-only field-observability artifact for reading the Parameter Golf PR / issue stream.

It maps reported claims, visible metadata, stack patterns, and candidate review-attention signals.

It does not validate submissions.

It does not define leaderboard truth.

It does not replace reviewer judgment.

It does not change the Parameter Golf submission path.

## Boundary

`golf_field_v0` is not a submission evidence receipt.

It is not a checker output.

It is not a gate.

It is a field map.

The intended separation is:

1. validity rules,
2. triage / detection tools,
3. review-side evidence receipts,
4. field observability over the public claim stream.

`golf_field_v0` belongs only to layer 4.

## What it observes

The first version may read a manually collected or exported list of public PR-like entries containing:

- PR number,
- title,
- author,
- opened label,
- optional URL.

From those fields it may parse:

- claim type,
- reported BPB / `val_bpb`,
- observed seed count in title,
- aggregation wording,
- feature tags,
- simple visibility signals.

All parsed values are title-derived unless explicitly stated otherwise.

## What it must not claim

`golf_field_v0` must not claim that a submission is:

- legal,
- illegal,
- reproducible,
- accepted,
- rejected,
- review-ready,
- leaderboard-valid,
- statistically valid.

It may only say that such claims or signals were observed or parsed from the available input.

## Naming discipline

Use `reported_val_bpb`, not `val_bpb`, for title-derived scores.

Use `record_claim`, not `record`, for title-derived record claims.

Use `non_record_claim`, not `non_record`, for title-derived non-record claims.

Use `candidate_tension_edges`, not `paradox_edges`, for inferred relationships that require human review.

Use `visibility_signals`, not `evidence_failures`, when a field is simply not visible from the title.

## Observed / parsed / inferred / validated

The artifact must keep these categories separate:

- `observed`: directly present in the input,
- `parsed`: extracted mechanically from observed text,
- `inferred`: derived from multiple parsed or observed fields,
- `validated`: confirmed by execution, review, or recomputation.

For v0, the artifact should mostly contain observed and parsed data.

Validation fields should default to false unless a separate process explicitly sets them.

## Required limitations

Every emitted artifact should carry limitations equivalent to:

- Title-derived fields are not validation evidence.
- Missing seed count in a title does not imply missing logs.
- Regex-derived feature tags may be incomplete or wrong.
- This artifact does not validate legality, reproducibility, leaderboard correctness, or review outcomes.

## Relationship to other artifacts

`golf_field_v0` is distinct from:

- `submission_evidence_v0`: review-side evidence for a concrete submission,
- `checker_output_v0`: output from a layer-2 diagnostic or triage tool,
- Parameter Golf leaderboard state: canonical challenge state maintained by the upstream repository.

The separation is intentional.

A field map can show where attention may be useful.

It cannot decide what is true.
