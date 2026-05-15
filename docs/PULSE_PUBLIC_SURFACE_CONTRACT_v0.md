# PULSE Public Surface Contract v0

This document locks the crawler/discovery public surface contract for PULSE as a **non-release-authority** interface.

## Boundary

- The public surface supports crawler and bot discoverability only.
- The public surface is **not** a release-authority mechanism and does not grant release approval.

## Required public paths

The following paths must remain publicly reachable:

- `/`
- `/robots.txt`
- `/sitemap.xml`
- `/status.json`
- `/report_card.html`

## Stable sitemap entries

`/sitemap.xml` must include stable entries for:

- `/`
- `/report_card.html`
- `/diagnostics/`
- `/paradox/core/v0/`

## Canonical mapping

- `/` maps to project root.
- `/report_card.html` maps to `report_card.html`.

## robots.txt requirements

- `robots.txt` must allow crawler access.
- `robots.txt` must reference the project sitemap at `/sitemap.xml`.

## Audit scope

The public-surface crawler audit verifies:

- discoverability of required paths
- accessibility of crawler-facing resources

The audit **does not** verify or guarantee third-party search-indexing success.
