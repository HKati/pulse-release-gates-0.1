# Security Intake Policy (v0)

This document defines the **canonical intake gate** for introducing new
dependencies, external code, PoCs, or tooling into this repository.

The **PR template contains the operational intake checklist**.
This document defines the policy, scope, and rationale behind that gate.

---

## Scope

This policy applies when a change introduces:
- new third-party dependencies (npm / pip / etc.)
- external repositories, PoCs, or copied code
- binaries, scripts, or tools not previously used in the project
- CI / workflow steps that execute external code

It does **not** apply to:
- pure refactors of existing, already-reviewed dependencies
- documentation-only changes with no executable impact

---

## Intake Outcomes

Each intake is classified as one of:

- **PASS**  
  Low-risk, well-understood source. May proceed to merge.

- **REVIEW**  
  Ambiguous or medium-risk signals. Requires isolated execution and
  focused review before merge.

- **HARD STOP**  
  High-risk signals detected. Must not be merged.

---

## Hard Stop Signals

Any of the following automatically triggers **HARD STOP**:

- password-protected ZIPs or opaque binary downloads
- instructions to disable OS protections (AV / Defender / Gatekeeper)
- obfuscated code, base64 blobs, or runtime-downloaded executables
- postinstall / preinstall scripts without strong justification
- requests for SSH keys, tokens, or broad filesystem access
- unclear provenance or freshly created maintainer accounts

---

## Review Signals

The following require **REVIEW** and isolated execution:

- new dependency with limited maintainer history
- unclear outbound network behavior
- unusual CI workflow steps or permissions
- partial or marketing-heavy documentation

---

## Isolation Requirements (for REVIEW)

When an intake is marked **REVIEW**, first execution must occur in:
- a container, VM, or otherwise disposable environment
- with no access to user home directories, SSH keys, or tokens
- with outbound network access restricted unless justified

---

## Decision Authority

- Any reviewer may declare **HARD STOP**.
- **HARD STOP decisions are final** and do not require consensus.
- Disputes should err on the side of rejection.

This policy exists to reduce decision pressure and remove
“curiosity-driven execution” risk.

---

## Relationship to SECURITY.md

This document governs **what enters the repository**.
`SECURITY.md` governs **how vulnerabilities are reported**.

They serve distinct and complementary purposes.

---

## Versioning

- Current version: **v0**
- Changes to this policy must be reviewed like code changes.
