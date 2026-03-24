# External detectors

> Portable safe-pack note for archived external detector evidence.

This safe-pack supports folding archived external detector summaries into the
final PULSE `status.json`.

It does **not** hard-wire live detector calls into the normative release path.
Whether external detector signals are advisory or release-blocking is decided by
the integrating repository’s policy and workflow.

Repo-level docs:

- Policy overview: [`../../docs/EXTERNAL_DETECTORS.md`](../../docs/EXTERNAL_DETECTORS.md)
- Implementation guide: [`../../docs/external_detector_summaries.md`](../../docs/external_detector_summaries.md)

---

## 1. Portable integration model

Recommended pattern:

1. run the external tool separately,
2. write an immutable JSON / JSONL summary,
3. archive that summary with the run artefacts,
4. fold it into the final `status.json` via
   `PULSE_safe_pack_v0/tools/augment_status.py`,
5. enforce only those external gates that the integrating repo explicitly
   promotes.

This keeps the safe-pack deterministic, artifact-first, and audit-ready.

---

## 2. Advisory vs normative use

The safe-pack is **detector-capable**, not detector-mandatory.

Typical modes:

- **Advisory / shadow**
  - detector findings are visible in `status.json` and reports,
  - but do not change the release decision.

- **Normative / gated**
  - an integrating repository may promote an aggregate external gate such as
    `gates.external_all_pass` into its required gate set.

Do not assume one global default outside the integrating repo’s own policy.

---

## 3. Evidence presence is a separate question

Aggregate detector pass/fail is not the same thing as evidence completeness.

A repository may separately require:

- external summary artefacts to be present,
- the summary files to be parseable,
- and the summaries to contain recognized metric keys.

This should be enforced explicitly by repo policy / workflow.

If evidence is missing or broken, it must never be silently reinterpreted as
`PASS`.

---

## 4. Expected summary artefacts

Typical accepted forms are:

- `*_summary.json`
- `*_summary.jsonl`

Good summary artefacts are:

- small,
- immutable,
- self-describing,
- easy to archive,
- easy to audit later.

---

## 5. Where results appear

After augmentation, external detector information may appear in:

- `PULSE_safe_pack_v0/artifacts/status.json`
- the structured `external` section of the final status artefact
- derived gates such as `gates.external_all_pass`
- human-readable reporting such as the Quality Ledger

Exact merge behavior, built-in detector mappings, and strict evidence semantics
live at repo level:

- [`../../docs/external_detector_summaries.md`](../../docs/external_detector_summaries.md)

---

## 6. Archival note

If you archive the safe-pack (for example via Zenodo / DOI), include this file
together with the repo-level external detector docs so downstream users can
reconstruct:

- what detector evidence was expected,
- how summaries were folded in,
- and whether those signals were advisory or normative in the integrating repo.
