# PULSE CI #6066 release-grade artifact preservation v0

This bundle preserves three original, unmodified GitHub Actions artifact ZIP files from the completed fixed-source hosted release-grade baseline:

- complete release-grade reference package;
- structural package-completeness report;
- independent package-verification report.

## Run identity

- repository: `HKati/pulse-release-gates-0.1`
- workflow: `PULSE CI`
- run number: `6066`
- run ID: `29249887581`
- run attempt: `1`
- source commit: `46b639706e23f80fe296a8893be18e2b5ab21f7e`
- run mode: `prod`
- `strict_external_evidence=true`
- `llamaguard_evidence_mode=hosted_full_runtime`
- active policy sets: `required + release_required`
- release decision: `PROD-PASS`

## Verification performed during preservation

- all three downloaded ZIP SHA-256 digests match the GitHub artifact API digests;
- all three downloaded ZIP sizes match the GitHub artifact API sizes;
- the complete package contains 24 files, including its digest inventory;
- all 23 inventory-declared files match their declared SHA-256 digests and byte sizes;
- structural completeness report: `complete`, `135 / 135`, zero failures;
- independent package verification: `verified`, `157 / 157`, zero errors.

See `PRESERVATION_MANIFEST_v0.json` and `SHA256SUMS` for machine-readable details.

## Authority boundary

This is a preservation copy only. It does not create release authority, does not replace the primary CI decision, does not replace the original GitHub attestations, and does not alter the preserved artifacts.

## Retention reason

The source GitHub Actions artifacts are scheduled to expire on 2026-08-12. This bundle preserves the completed evidence packet before that expiry boundary.
