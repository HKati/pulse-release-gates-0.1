# Kaggle Run 0 Reconstruction Instructions v0

This packet is diagnostic.

It does not create release authority.

## Replay boundary

1. Run the Kaggle notebook cells in order.
2. Do not fetch external Kaggle state.
3. Do not use Kaggle credentials.
4. Do not write status.json.
5. Do not invoke or replace check_gates.py.
6. Download the generated kaggle_run_0_capture_v0.zip artifact.
7. Verify SHA-256 digests against outputs/digest_manifest.json.
8. Validate outputs/hpc_evidence_bundle_preview.json with the existing hpc_evidence_bundle_v0 contract checker after committing the artifact packet to the repository.

## Digest boundary

input_manifest.sha256 is the digest of outputs/input_manifest.json only.

Payload artifacts have separate digests under evidence_items[].sha256 and outputs/digest_manifest.json.

## Non-authority boundary

Kaggle run ≠ verifier.

Notebook output ≠ verified evidence.

Digest match ≠ relation satisfaction.

Metric score ≠ gate materialization.

Packet preview ≠ release authority.
