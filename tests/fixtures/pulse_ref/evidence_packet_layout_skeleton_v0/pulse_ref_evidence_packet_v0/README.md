# PULSE-REF Evidence Packet Layout Skeleton v0

Status: layout skeleton fixture  
Authority status: non-normative  
Release-grade status: not release-grade evidence  
Purpose: canonical packet-path materialization only

This fixture materializes the canonical PULSE-REF evidence packet layout.

It is not a release-grade reference packet.

It does not contain real release-grade evidence.

It does not authorize, block, override, or create release authority.

The normative release decision remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

This skeleton exists so tests can verify that the canonical packet paths are physically materializable before a future schema-valid or verifier-valid packet fixture is introduced.
