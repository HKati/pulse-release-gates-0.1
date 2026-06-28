# PULSEmech Tier 0 publication snapshot v0

## Purpose

This note records the publication-surface identifiers for the controlled Tier 0 self-contained PULSE evidence-floor milestone.

It does not change release authority, workflow enforcement, gate policy, verifier behavior, materializer behavior, schema behavior, hosted external-model lane behavior, or fail-closed CI enforcement.

## Publication identifiers

```text
GitHub repository:
https://github.com/HKati/pulse-release-gates-0.1

GitHub Tier 0 publication snapshot:
https://github.com/HKati/pulse-release-gates-0.1/releases/tag/pulsemech-tier0-floor-20260628-b

Zenodo software concept DOI / all versions:
https://doi.org/10.5281/zenodo.17214908

Zenodo preprint / documentation DOI:
https://doi.org/10.5281/zenodo.17833583

ORCID:
https://orcid.org/0009-0001-9745-3764
```

## Citation target

The stable citation target for the PULSE software record is the Zenodo concept DOI:

```text
10.5281/zenodo.17214908
```

The GitHub Tier 0 release tag records the active Tier 0 publication snapshot:

```text
pulsemech-tier0-floor-20260628-b
```

## Tier 0 milestone

The publication snapshot is tied to the controlled Tier 0 self-contained evidence-floor milestone.

Controlled run mode:

```text
strict_external_evidence=true
llamaguard_evidence_mode=tier0_not_required
```

Observed outcome:

```text
PULSE CI
→ success

self-contained PULSE evidence floor
→ produced

hosted LlamaGuard runtime lane
→ skipped

external model pass
→ not claimed
```

## Authority boundary

```text
Tier 0 self-contained floor
≠ hosted external model evidence
≠ release authorization
```

This publication snapshot does not claim:

- LlamaGuard passed;
- external model evidence passed;
- hosted evaluator evidence was produced;
- `release_required` was bypassed;
- release authority was created;
- release was authorized;
- a completed full public release-grade reference package exists.

## Reader-surface boundary

Public pages, status renderers, DOI records, ORCID records, ResearchGate entries, Google Scholar profiles, repository badges, release notes, and documentation records are publication, reader, citation, preservation, review, or discoverability surfaces.

They do not independently produce release authority.

Release authority remains bound to the connected declared-policy path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
```

## Summary

This note records publication metadata only.

The Tier 0 milestone is now externally anchored by GitHub, Zenodo, and ORCID surfaces, while the release-authority boundary remains unchanged.
