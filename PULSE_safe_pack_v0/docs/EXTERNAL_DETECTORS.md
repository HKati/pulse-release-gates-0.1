# External detectors

PULSE supports an *optional* external detector layer that can enrich the
status with additional safety and quality signals (for example: external
alignment or safety scanners).

The PULSE safe-pack itself does **not** hard-wire any specific external
detector. Instead, it defines an interface and expects integrations to:

- run external tools (e.g. model scanners, policy checkers),
- write their findings into an extended status structure,
- keep those findings **advisory** and CI-neutral.

In other words:

- core, deterministic gates remain the only source of truth for release
  decisions;
- external detector results are logged for analysis, reporting and
  governance, but do not change pass/fail outcomes.

For the full, up-to-date guide (including schemas, examples and
integration patterns), see the top-level documentation in this
repository:

- `docs/EXTERNAL_DETECTORS.md`

If you archive this pack (e.g. via Zenodo/DOI), consider including both
this file and the top-level documentation so that external detector
behaviour remains transparent to downstream users.
