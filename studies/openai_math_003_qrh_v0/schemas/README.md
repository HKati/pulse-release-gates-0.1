# Runtime schema

`status.schema.json` describes admitted `qrh003_runtime_status_v1` records. An admission failure has `qrh.record_role=admission_failure`, null run/time bindings and UNVERIFIED trust; it is an error envelope and is intentionally not a valid admitted status. Both forms fail closed. The verifier implements additional digest, signature, identity, policy and Boolean checks; JSON Schema success alone grants no authority.

The historical design schema `qrh003_status_v0` is not overwritten or silently reused for execution records.
