# Inert Kaggle Notebook Skeleton Fixture v0

Status: fixture-only  
Normative status: non-normative diagnostic fixture  
Scope: local, inert Kaggle notebook skeleton shape for future diagnostic / reproducibility artifacts

## Boundary

This fixture does not run Kaggle.

This fixture does not fetch external state.

This fixture does not use Kaggle credentials.

This fixture does not write `status.json`.

This fixture does not invoke or replace `check_gates.py`.

This fixture does not change policy, registry, workflows, CI allow/block behavior, or release authority.

The notebook skeleton and expected outputs are diagnostic only.

## Packet compatibility

The expected packet preview is shaped for:

```text
schema = hpc_evidence_bundle_v0
authority_status = diagnostic_non_normative
creates_release_authority = false
```

Every emitted evidence item remains:

```text
folded_into_status = false
```

## Digest boundary

`input_manifest.sha256` is the digest of the input manifest file only.

Payload artifact digests are recorded separately under `evidence_items[].sha256` or in the local digest manifest.

The digest manifest records hashes for:

- `notebook_skeleton.ipynb`
- `expected/input_manifest.json`
- `expected/diagnostic_output.json`
- `expected/diagnostic_log.txt`
- `expected/hpc_evidence_bundle_preview.json`

The digest manifest does not self-hash.

## Expected artifacts

```text
notebook_skeleton.ipynb
expected/input_manifest.json
expected/diagnostic_output.json
expected/diagnostic_log.txt
expected/digest_manifest.json
expected/hpc_evidence_bundle_preview.json
```

## Mechanical anchor

A Kaggle notebook skeleton can make a future external run reviewable.

It cannot make an external run release-authoritative.
