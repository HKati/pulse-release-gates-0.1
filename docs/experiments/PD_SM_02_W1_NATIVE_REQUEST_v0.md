# PD-SM-02-W1 — preserved native request v0

Status: **REQUEST_VALID_NOT_AUTHORIZED**. The five newly prepared native cases remain **NOT_RUN**. `execution_authorized: false`; `authority_effect: none`.

## Preserved preparation artifact

The [native request preparation ZIP](../evidence/PD_SM_02_W1_NATIVE_REQUEST_v0/PD_SM_02_W1_NATIVE_REQUEST_v0.zip) preserves the complete reviewed request, all twenty bound payloads, the original successful admission archive, source provenance, preparation procedure and actual offline validation receipts.

The [archive checksum](../evidence/PD_SM_02_W1_NATIVE_REQUEST_v0/PD_SM_02_W1_NATIVE_REQUEST_v0.zip.sha256) applies to the original ZIP bytes and basename. The archive has not been unpacked into repository runtime paths or rebuilt for preservation.

| Identity | Exact value |
|---|---|
| Archive filename | `PD_SM_02_W1_NATIVE_REQUEST_v0.zip` |
| Archive bytes | `444703` |
| Archive SHA-256 | `dbb532a1447f6602f6a9dda53599bd8cbb163e60f94fc2c724178bb3700e8834` |
| Native request SHA-256 | `655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a` |
| Reviewed preparation source | `6343d4e54ec8628f033400518fe08a81aa75d9b9` |
| Native request run ID | `pd-sm-02-w1-native-after-41362257003-01` |
| Exact local image/config ID | `sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3` |
| Required container runtime | CPython 3.13.5, Linux x86_64 |
| Candidate order | `P00`, `N01`, `N07`, `N08`, `N02` |
| Attempt and budget | Attempt 1; at most five candidate invocations; no automatic retry |
| Candidate executions during preparation | `0` |

The ZIP's top-level directory is `PD_SM_02_W1_NATIVE_REQUEST_v0/`. Its strict inner `package/` contains exactly twenty payload files and `request.json`; no `CLAIM.json` or `capture/` exists. The current reviewed source and prior admission bindings are companion records under `provenance/`, outside the strict inner package.

The unchanged v0 request has a historical `preparation_base` of `2890469ee82333f4d34872bbe711cda6ad9b49aa`. This fixed implementation-contract field is not the current reviewed source commit. Historical fields inside frozen inputs and reference documents retain their original bytes.

## Prior admission and completed offline checks

[Environment admission run 41362257003, attempt 1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/41362257003) completed at the reviewed preparation source. Its two controls, `probe-time` and `probe-output`, completed and replayed with zero candidate invocations. Its status remains `ADMISSION_COMPLETED_UNATTESTED`.

The original admission ZIP is nested unchanged in the preparation archive. Its SHA-256 is `95347f71c309222205bb439ab4fc20b2a897194a70e5c30bfdd08372d72617fc`, and its size is 99214 bytes.

The preparation records establish:

- `REQUEST_PREPARED_NOT_AUTHORIZED`, followed by `REQUEST_VALID_NOT_AUTHORIZED`, using the unchanged native controller and bound tool sources;
- successful offline replay of the prior admission's 76 manifest members;
- rejection of a wrong request digest, a changed P00 payload and a reordered case list even after the modified request was correctly rehashed;
- unchanged original package inventory after the negative controls;
- successful verification from a relocated, unpacked copy, and final ZIP file-inventory/hash verification.

These are offline preparation and record checks. They are not new observations of the five native W1 cases or external attestation of the acquisition.

## Execution boundary

The [native acquisition implementation](PD_SM_02_W1_NATIVE_CAPTURE_v0.md) and [separate admission implementation](PD_SM_02_W1_ADMISSION_v0.md) define different operations. The existing manual admission workflow cannot execute this five-case request. At the reviewed preparation source, a hosted native W1 execution workflow was not supplied.

This preservation change adds only the archive, its checksum and this document. A later hosted native runner requires separate implementation review and owner authorization bound to the exact native request digest. It must repeat the native path's live readiness and supervision controls on its actual execution host. The prior admission is not a permission to skip those controls.

Predictions remain preregistered expectations; `native_witness_observed` and `containment_observed` remain null and `model_native_correspondence` remains `UNRESOLVED`. The archive does not change the ordinary admission lane, release policy, required gates, normative status or release authority.
