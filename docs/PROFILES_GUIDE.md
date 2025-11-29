# PULSE profiles and policies – v0 guide

This note explains how profiles and policies are organised in this
repository, and which files are considered the source of truth for CI.

It is intended for maintainers and contributors who need to adjust
thresholds, add new profiles, or reason about policy changes.

---

## 1. Source of truth for CI

The **canonical policy** for CI lives inside the safe-pack:

- `PULSE_safe_pack_v0/pulse_policy.yml`

This file defines:

- which gates are enabled and required,
- which thresholds and profiles are actually used by CI,
- how external detectors (if any) are wired into the gate set.

When CI runs via `.github/workflows/pulse_ci.yml`, it reads from the
safe-pack policy, not from the top-level `profiles/` directory.

**Rule of thumb:**

> If you want to change how CI behaves, change the safe-pack policy
> (`PULSE_safe_pack_v0/pulse_policy.yml`) via a reviewed pull request.

---

## 2. Profiles inside the safe-pack

The safe-pack may also contain its own profile files, for example:

- `PULSE_safe_pack_v0/profiles/…` (if present)

These are tightly coupled to the pack and can be referenced directly
from `PULSE_safe_pack_v0/pulse_policy.yml`.

Typical uses:

- alternative profile presets (e.g. stricter vs balanced),
- internal thresholds that CI can switch between via policy changes.

Changes to these profiles:

- should be treated as **behavioural changes** for CI,
- must go through normal review (including changelog and docs updates
  when they affect safety/quality gates),
- should be accompanied by a short rationale in the PR.

---

## 3. Top-level `profiles/` directory

At the repository root there is also:

- `profiles/`

This directory is used for:

- **example / experimental profiles**,
- drafts and scenario-specific configurations,
- templates that downstream users can copy into their own projects.

By default:

- **CI does not read from `profiles/` directly.**
- A profile in `profiles/` only affects CI if it is explicitly
  referenced from:
  - the safe-pack policy (`PULSE_safe_pack_v0/pulse_policy.yml`), or
  - a custom workflow / script.

Because of this, changes in `profiles/`:

- are usually **non-breaking** for CI,
- but can be important for documentation, demos, or downstream use.

When editing profiles under `profiles/`:

- keep filenames and comments clear about their intent (e.g.
  `balanced-prod.yaml`, `demo-strict.yaml`),
- avoid silently copying values that diverge from the safe-pack
  without explanation.

---

## 4. Avoiding divergence

Over time, it is possible for profiles to drift apart:

- a threshold is updated in the safe-pack policy,
- an older value remains in a sample profile under `profiles/`,
- documentation refers to one or the other.

To reduce confusion:

1. Treat `PULSE_safe_pack_v0/pulse_policy.yml` as the **single source
   of truth** for what CI actually enforces.

2. When updating important thresholds (e.g. for Q1–Q4, or core safety
   invariants):

   - update the safe-pack policy first,
   - then review sample profiles under `profiles/`:
     - either align them,
     - or add comments noting that they intentionally differ.

3. Keep documentation and profiles synced:

   - if docs mention specific default values, check that they match
     the safe-pack policy,
   - if an example profile is intentionally different, mention that
     in its header comment.

---

## 5. Governance expectations

Threshold and policy changes are governance-sensitive. In this
repository, such changes are expected to follow these patterns:

- Use **Conventional Commits / semantic PR titles** to signal that a
  change affects policy (e.g. `docs(policy): …`, `feat(gates): …`,
  `chore(policy): …`).

- Update `CHANGELOG.md` under `[Unreleased]` when:
  - tightening or loosening gate thresholds,
  - adding or removing required gates,
  - changing how external detectors participate in gating.

- Update relevant docs when:
  - the meaning of a profile changes,
  - default thresholds move,
  - new profiles are introduced for specific scenarios.

- Consider RDSI and Quality Ledger:
  - when changing thresholds, watch the impact on RDSI and the
    Quality Ledger across a few runs,
  - record any notable changes in refusal/quality behaviour in the
    governance notes or PR description.

---

## 6. Creating new profiles

When adding a new profile, decide whether it should be:

1. **CI-facing (safe-pack controlled)**

   - Add the profile under `PULSE_safe_pack_v0/profiles/` (or inline
     in `PULSE_safe_pack_v0/pulse_policy.yml`).
   - Wire it into `PULSE_safe_pack_v0/pulse_policy.yml`.
   - Update docs and changelog if it changes behaviour.
   - Treat as part of the release gating configuration.

2. **Example / experimental**

   - Add it under the top-level `profiles/` directory.
   - Document its intent in comments at the top of the file.
   - Optionally reference it from tutorials, demos, or case studies.
   - Leave CI unchanged unless explicitly wired in.

In both cases, prefer:

- descriptive filenames,
- clear comments about intent (e.g. "stricter fairness for high-risk
  deployments", "demo profile for local experiments").

---

## 7. Summary

- The safe-pack policy (`PULSE_safe_pack_v0/pulse_policy.yml`) is the
  **source of truth** for CI behaviour.
- Profiles under `PULSE_safe_pack_v0/` are CI-facing and should be
  treated as part of the release gating configuration.
- Profiles under the top-level `profiles/` directory are examples and
  experiments; they do not affect CI unless explicitly referenced.
- When thresholds or profiles that affect gating are changed:
  - update the safe-pack policy,
  - align or document differences in sample profiles,
  - update changelog and docs,
  - consider RDSI and Quality Ledger impact.

This keeps profiles useful for exploration and reuse, while preserving
a clear, auditable source of truth for what PULSE actually enforces
in CI.
