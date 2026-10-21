# Source licenses and attribution — M1 inventory

This notice describes the material physically present in
[PULSEMECH_QRH003_M1_v0_1_INCOMPLETE.zip](PULSEMECH_QRH003_M1_v0_1_INCOMPLETE.zip).
The archive is preserved byte-for-byte. Original source headers and license
records inside it remain intact.

The input lock contains 51 base64-encoded source, plan and license payloads
(884,742 decoded bytes); the claim card also retains 21 source excerpts.
Source names and dependency pins recorded only as metadata do not mean that
their full source trees, executables or other artifacts are distributed here.

## PULSE source and planning material

The embedded material includes 42 files from
`HKati/pulse-release-gates-0.1@c0895b920399cafbc14aa9fd3b6d3b68671f0220`
and four knowledge-continuity planning documents from
`2ca84e3e0c9709758adc48eb959f1b5e0c965c19`. The QRH source subset retains its
own license/source records and the PULSE runtime provenance at
`288bb9a45764d2a30f72fdf4c417e9dd5b3087c5`.

The retained license is Apache License 2.0. Its exact text is provided in
[licenses/Apache-2.0.txt](licenses/Apache-2.0.txt), with SHA-256
`c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
The repository [LICENSE](../../LICENSE) and [NOTICE](../../NOTICE) continue
to apply. The source revisions' root NOTICE matches the following retained
text (203 bytes; SHA-256
`9753bcde976cff79cabdcb3e0d6dbeea011ddd747ef8f46edcb05563bfeaadb8`):

```text
PULSE — Release Gates for Safe & Useful AI
Copyright (c) 2025 EPLabsAI

This product includes software developed by EPLabsAI and contributors.
See the LICENSE file for the Apache License, Version 2.0.
```

## OpenAI Math source excerpts and license

The claim card quotes selected manuscript, scope, configuration and Lean
source passages from
`openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a`.
The archive also embeds that revision's root LICENSE. Its Apache License 2.0
text is byte-identical to
[licenses/Apache-2.0.txt](licenses/Apache-2.0.txt), with the SHA-256 above.
The input lock and claim card retain the exact source paths, revisions,
source digests, excerpt digests and byte/line locations.

This preservation copy contains those excerpts and the license text; it does
not include the complete upstream PDF manuscripts or the separately retained
62-file historical upstream source set. No scientific endorsement is claimed.

## Mathlib source files

Three complete Lean source files, associated excerpts and the root LICENSE
are retained from
`leanprover-community/mathlib4@d13f23b723b8a846827a245b89c10fc7d3f11612`.
The exact license is provided in
[licenses/Mathlib-Apache-2.0.txt](licenses/Mathlib-Apache-2.0.txt), SHA-256
`b40930bbcf80744c86c46a12bc9da056641d722716c378f5659b9e555ef833e1`.

Each source file retains its original header, including these notices:

| Source | Copyright and author attribution |
| --- | --- |
| `Mathlib/NumberTheory/Harmonic/ZetaAsymp.lean` | Copyright (c) 2024 David Loeffler. All rights reserved. Authors: David Loeffler, Terence Tao. |
| `Mathlib/NumberTheory/LSeries/Nonvanishing.lean` | Copyright (c) 2024 Michael Stoll. All rights reserved. Authors: Michael Stoll, David Loeffler. |
| `Mathlib/NumberTheory/LSeries/RiemannZeta.lean` | Copyright (c) 2023 David Loeffler. All rights reserved. Authors: David Loeffler. |

All three headers state that the files are released under Apache License 2.0
as described in their LICENSE file. The pinned relevant source paths contain
no separate NOTICE file requiring an additional notice copy in this package.

## Other recorded components

The PULSE source subset includes license records/texts for Comparator and
lean4export, along with dependency, patch, toolchain and historical evidence
identifiers. Those records are retained as provenance; this M1 archive does
not distribute the tools' executable binaries, the hash-locked replay wheels,
a CPython/OS image or the missing dependency trees.

The original `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip` is a separately
acquired owner-controlled artifact. This notice concerns the smaller M1
inventory ZIP only. It does not grant rights to unrelated or unacquired
artifacts, claim a complete dependency-license closure or change the original
M1 `INCOMPLETE` state.

## Preservation and changes

The original M1 archive, embedded raw source payloads and retained source
excerpts are unchanged. This repository companion adds the README, archive
identity manifest, readable source notices and exact license copies, with
documentation navigation and a changelog entry. It introduces no modified
upstream source file or new proof, replay or expert-review result.
