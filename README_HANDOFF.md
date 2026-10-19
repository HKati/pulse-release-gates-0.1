# QRH003 tudásfolytonossági pilot — docs-only feltöltési csomag

**Csomag jellege:** későbbi, tulajdonos által indított dokumentációs PR-hoz
előkészített négy új Markdown-fájl; a repositoryhoz jelen előkészítés
nem nyúlt, commitot, PR-t, CI-t vagy auditfutást nem indított.

## Cél

`HKati/pulse-release-gates-0.1` repository — csak a `docs/` könyvtár.
Az angol áttekintés a repó olvasói belépőpontja. A három részletes Markdown
magyar nyelvű, az eredeti terveket tartalmilag megőrző forrás.

A Word-eredetik és a korábbi QRH003 teljes bizonyítékarchívuma a
Libraryben / külön archiválásban maradnak; nem kerülnek a publikus repóba.

## Feltöltés

Javasolt branch: `docs/qrh003-knowledge-continuity-v0`

A `docs/` alkönyvtárból a négy `.md` fájlt a repository `docs/`
könyvtárába kell másolni. `INDEX_EDIT_INSTRUCTIONS.md` alapján a már
meglévő `docs/INDEX.md` QRH003-sorát és három új linkjét frissítsük.
A README és az indexutasítás NEM repo fájlok.

Commit-javaslat:
`docs(qrh003): add knowledge-continuity pilot plans`

PR cím (max. 50 karakter):
`docs: add QRH003 continuity pilot plans`

A PR érvényesítési minimuma: csak a négy új Markdown és a
`docs/INDEX.md` célzott sora változzon, minden link megnyíljon,
maradjon meg az eredeti QRH003 `BLOCK`/`MATCH` történeti státusza,
`NOT_IMPLEMENTED` proof-capture, `NOT_RUN` új próbák.

## Érinthetetlen

QRH003 kód, Q2/Step5, workflow, CI policy, kapu- és gate-registry,
checker, schema, gyökér README, DOI/SWH/Zenodo, upstream és historikus
futáseredmények. Az M1 végrehajtása külön munkacsomag.

## Alapforrások

Upstream `openai/math` commit:
`adc7f1241b42e322a6451854ab7e4b4c146bf78a`
QRH003 study v0.1.3 és eredeti történeti BLOCK/MATCH eredmények.
A tervek 2026-10-19-én a `c0895b920399cafbc14aa9fd3b6d3b68671f0220`
akkor ellenőrzött dokumentációs állapotára épültek. Új PR nyitásakor
az aktuális mainről induljon a branch, különösen mivel main közben
előreléphetett.
