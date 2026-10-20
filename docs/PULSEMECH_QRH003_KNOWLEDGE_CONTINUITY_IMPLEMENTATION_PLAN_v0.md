# PULSEmech QRH003 — tudásfolytonossági pilot: Megvalósítási terv (v0.1)

**Meglévő QRH003-eredmények újrahasznosítása; szakaszfüggések, erőforrások, első munkacsomag**

*V0.1 \| Tervezési állapot \| A terv elkészítésekor nem történt repoírás és nem indult új audit-, Lean-, CI- vagy replay-futás*

| **Megvalósítási elv** Ne készüljön új QRH-auditor, új általános policy-kapu vagy új natív proof-capture addig, amíg az ismert történeti anyagból a szűk claim→evidence→decision→replay→nyitott kérdés átadása nincs lezárva. A hibás és hiányos tudásállapot ugyanolyan megőrzendő eredmény, mint a PASS. |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

## 1. Meglévő munka vs. ténylegesen szükséges új elem

| **Létező elem**                                | **Újrafelhasználás**                                                                                                                      | **Amit nem szabad állítani**                                      |
|------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| 2026-10-07 28 oldalas Math 003 auditterv       | A claim-hozzárendelés, négy claim/öt export, importgráf és eszközlánc-eltérés az első forrásleltár.                                       | A terv nem Lean-run és nem független szakreview.                  |
| studies/openai_math_003_qrh_v0 v0.1.3          | A forráskötött launcher, reference/claim_map.json, configurations, SOURCE_MANIFEST, EVIDENCE_REFERENCE, existing checkers és TM observer. | A 220 PASS csak izolált helyi suite, nem formális proof-igazolás. |
| v0.1.1 archivált disztribúció                  | Eredeti verifier-snapshot, policy, anchor, bundle, döntés, replay, report, wheels; pontos byte SHA már ismert.                            | A történeti snapshot nem írható felül az aktuális root forrással. |
| Történeti BLOCK / MATCH                        | A hiányzó proof bizonyíték bemutatható és újraszámítható döntési határát adja.                                                            | A BLOCK/MATCH nem matematikai elfogadás és nem „fully validated”. |
| PULSEmech Transition Meter és fail-closed gate | Nyolc observer-tengely, hat globális státusztengely és külön authority kontroll.                                                          | A mérési observer nem kap új release-jogosultságot.               |

## 2. Függőségi munkasorrend

A munkacsomagok egymásra épülnek, de nem igényelnek automatikusan repoírást. Az M1 után külön tulajdonosi döntés határozhatja meg, melyik lépéshez kell új futás vagy külső szereplő.

| **ID és csomag**                                | **Bemenet → konkrét kimenet**                                                                                   | **Lezárás / függőség**                                                          |
|-------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| M1 – állításhatár és statikus bizonyítéktérkép  | A meglévő audit+repo+archívum → egy claim-card, rögzített input-lock, E1–E7 relation inventory, open questions. | NINCS új futás; pontos részletek a 4. fejezetben.                               |
| M2 – TM minősítési overlay                      | M1 + történeti transition_report → nyolc tengely ref- és korláttérképe; hat canonical status_axes vetület.      | Minden élnek külön `relation_status` és `expert_review_status`; nincs math causal-promotion. |
| M3 – validáció és archiválási szerződés         | M1–M2 → JSON schema/validator és megőrzési leltár, kizárólag scratchben/future nem-repo csomagban.              | Hiányzó byte vagy review hamis READY-t nem eredményez.                          |
| M4 – kontroll/negatív próbacsomag               | M3 → K01–K19 fixture manifestek, expected reason-code és tesztjegyzőkönyv-sablon.                               | B0/B1/T külön, minden eset NOT_RUN a tényleges tesztig.                         |
| M5 – független offline decision replay          | Eredeti v0.1 snapshot + archive + lock → új execution receipt.                                                  | Külön owner-engedély; BLOCK/MATCH-t újra számolja, nem proofot.                 |
| M6 – vak tudásátadási próba                     | M3–M5 után a B0/B1/T packet + előírt öt kérdés → átvevői receipt és pontozás.                                   | Tényleges független átvevő, nincs szóbeli segítség; status NOT_RUN addig.       |
| M7 – megőrzés, összehasonlítás, partneri átadás | M1–M6 → 2 példányban olvasható archívum, license/access report, végleges gap & delta report.                    | Külső partner csak saját futás után nevezhető validálónak; DOI/SWH nem módosul. |

A későbbi szakaszok pontos, **M1-től külön** útvonalai: `M2/TRANSITION_ASSESSMENT.json`, `M3/PRESERVATION_INVENTORY.json`, `M3/CONTINUITY_STATUS.json`, `M6/HANDOFF_PROTOCOL.md`, `M6/HANDOFF_RECEIPT.json`. Ezeket a mostani PR nem állítja elő, és a történeti QRH003 adatokat nem módosítják.

## 3. Erőforrások és tényleges kockázatok

| **Szükséglet**                   | **Mennyiség / feltétel**                                                                                            | **Kockázat / megoldás**                                                                                     |
|----------------------------------|---------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Statikus leltár és interpretáció | Egy forrásértő mérnök; meglévő Library és Git read-only; nincs HPC.                                                 | A már ellenőrzött audit téves újramunkálása helyett az eltérések delta-listája.                             |
| Gépi replay                      | Később: Linux x86_64, CPython 3.12, glibc ≥ 2.34, hash-locked wheel-készlet.                                        | Az eredeti verifier/payload eltűnése vagy kompatibilitás hiánya INCONCLUSIVE/BLOCK.                         |
| Matematikai szakértelem          | Legalább egy önálló Lean/analitikus számelméleti reviewer az E2 nyitott szemantikai kapcsolathoz.                   | Saját aláírás nem független reviewer; külön reviewer receipt szükséges.                                     |
| Független átvevő                 | Az M6-hoz másik végrehajtó, saját jegyzőkönyvvel; legalább egy, erősebb eredményhez több.                           | Egy átvevővel nem általánosítható a tudásfolytonosság minden kutatóra.                                      |
| Megőrzés                         | Történeti 23,45 MB ZIP + pinned forrás/dependency/toolchain + tervezett meta-overlay; 2 biztonságos, külön másolat. | A tartós bytes/URL/licencek és külön role-based access megőrzendők.                                         |
| Jövőbeli natív teljes proof      | Csak külön scope/futtatási jogosítás után; CPU/RAM és toolchain igazolt beszerzése.                                 | A Lean/Comparator verziórés v4.34.1 vs v4.35.0-rc4 és 32 hiányzó lock-csomag eredeti audit szerint nyitott. |

Feladatszintű ráfordításbecslés: M1/M2 = kicsi (adatkapcsolati elemzés); M3/M4 = közepes (schema, negatív fixture); M5 = közepes–nagy, ha eredeti környezet újraépítése szükséges; M6/M7 = szereplő- és hozzáférésfüggő. Ezek kapacitástervezési kategóriák, nem futtatási vagy szállítási ígéretek.

## 4. Első önálló munkacsomag – M1 / KNOWLEDGE_LINK_INVENTORY

| **M1 cél** A már megőrzött történeti bizonyítékokból, új proof-végrehajtás nélkül, egyetlen QRH003-zétaállítás pontos átadásához szükséges forrás-, kapcsolat- és hiányjegyzéket előállítani. Ezzel az első későbbi munkacsomag megkezdhető CI, Lean vagy repository-írás nélkül. |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### 4.1 Pontos bemenetek

**Normatív, kötelező M1-bemenetek; az első tétel hiánya nem pótolható a történeti DOCX elolvasásával:**

- **A – Rögzített upstream:** `openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a`; QRH `paper.pdf` és `build/paper.tex` (September-30-2026), `lean/docs/003.md`, `lean/formalization.yaml`, `lean/ComparatorChallenges/QuasiRiemannHypothesis.{lean,json}`, `lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean`, releváns Mathlib-definíciók és a rögzített dependency/patch-források. A Landau–Siegel-kézirat csak scope-kontextus, és ha nem szükséges az E1–E7 tárgyához, opcionális.
- **B – Aktuális, rögzített QRH003 forrás:** `HKati/pulse-release-gates-0.1@c0895b920399cafbc14aa9fd3b6d3b68671f0220` → `studies/openai_math_003_qrh_v0/` `README.md`, `SOURCE_BINDING.md`, `SOURCE_MANIFEST.json`, `EVIDENCE_REFERENCE.json`, `reference/claim_map.json`, `reference/configurations.json`, `reference/required_boundary_tests.json`, `tools/authority.py`, `tools/transition_report.py`. A commit nem mozgó `main`-t jelent.
- **C – Eredeti történeti bizonyítékbájtok:** `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip`, **23 453 781 B**, SHA-256 `ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc`; a `REPLAY_PILOT.md` és `runs/pilot_002/` eredeti verifier snapshot/anchor/bundle/decision/replay/report állományai. A teljes archívumot ténylegesen, hozzáférési jogosultsággal be kell szerezni, majd helyben ellenőrizni; puszta hash vagy URL nem elég. Ha nem hozzáférhető: `M1_INCOMPLETE: HISTORICAL_BYTES_UNAVAILABLE`.
- **D – Külön megőrzött történeti eredményrekordok:** `PULSEMECH_QRH003_PILOT_002_DECISION.json`, `PULSEMECH_QRH003_PILOT_002_REPLAY.json`, `PULSEMECH_QRH003_PILOT_002_TRANSITION_METER.json`, `PULSEMECH_QRH003_PILOT_002_REPORT.json`. A belső ZIP-tagokkal csak a tényleges byte-összevetés után tekinthetők ugyanazon rekordoknak.

**Nem normatív, opcionális előzmény:** `PULSEMECH_OPENAI_MATH_003_AUDIT_TERV_v0.docx` (2026-10-07, 28 oldal) — **82 686 B**, SHA-256 `2cb23a9901cf4d50c2ba3b871bedc5ac2de1546bfeecf46f741014ea65a60e8e`. A készítő ChatGPT Libraryjében azonosított példány; nyilvános, önálló letöltési helye nem igazolt. Ha ezt ténylegesen felhasználjuk, a pontos bájtokat a jogosult tulajdonostól kell beszerezni, ellenőrizni, és a `M1/INPUTS_LOCK.json`-ban `optional_historical_reference` státusszal, beszerzésihorgony- és hozzáférési adatokkal rögzíteni. A DOCX hiánya önmagában **nem blokkolja** az M1-et, mert az egy-claim scope forrásait a pinned upstreamből és a QRH003 reference fájlokból kell újraolvasni. A DOCX korábban rögzített, nem önállóan igazolt eredményei történeti jelöléssel maradnak.

### 4.2 Kimeneti fájlok – az M1 végrehajtásakor

| **Név (nem-repo scratchben)**  | **Minimális rekord**                                                                                                                                   |
|--------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| M1/INPUTS_LOCK.json            | Source-id, commit/tree, elérési út, teljes digest, méret, relevancia, megőrzési státusz, változás dátuma.                                              |
| M1/CLAIM_CARD_QRH003_ZETA.json | Egy claim, PDF 1.1 tétel, Lean-célnév, pólusfeltétel, implicit definíciók, exclusions, semantic NOT_REVIEWED.                                          |
| M1/EVIDENCE_RELATIONS.json     | E1–E7 forrás/cél és `relation_kind`, `evidence_refs`, `reason_code`, **`relation_status` és külön `expert_review_status`**, teljes hat `status_axes`. |
| M1/OPEN_QUESTIONS.json         | Min. három konkrét nyitott kérdés: s=1 formal–classical mapping; natív Lean capture; teljes dependency/bináris closure; mindegyikhez closure evidence. |
| M1/M1_AUDIT_TRAIL.md           | Csak read-only lépések és forrás-hivatkozások; mit nem hajtottunk végre; gépi és emberi státusz külön.                                                 |

**Veszteségmentes státuszszótár az `M1/EVIDENCE_RELATIONS.json` fájlhoz:**

- `relation_status`: `observed_and_bound`, `reconstructable`, `hypothesized`, `missing`, `conflicting` (kötelező, pontosan egy).
- `expert_review_status`: `not_required`, `required_pending`, `verified`, `rejected` (kötelező, pontosan egy; a szakreview hiánya nem írhatja át a reláció megfigyelési státuszát).
- `requires_expert_review = (expert_review_status == "required_pending")` (származtatott, olvasható jelzés). Például `relation_status="conflicting"` és `expert_review_status="required_pending"` egyidejűleg tárolható.
- Hat külön kanonikus Transition Meter `status_axes`: observation, binding, consistency, reproduction, causal, authority; **egyik sem következtethető automatikusan** a fenti kettőből.
- `O/R/H/U/E` betűk nem érvényes JSON enumértékek: nincs ötbetűs, információvesztő összevonás és nincs automatikus VERIFIED/ALLOW promóció.

### 4.3 Lépéssor és változtatási tilalom

- 1\. Az **A–D kötelező** források és a v0.1.1 történeti archívum pontos digestjeinek egyeztetése az ismert reference rekordokkal; hiányzó normatív bájt esetén az érintett kapcsolatra `missing` és az M1-re `INCOMPLETE`, nem PASS. Eltérés vagy ütközés megőrzése és STOP. A DOCX csak opcionális E történeti kontextus. Nincs történeti fájl átírás.

- 2\. A qrh003_zeta tétel PDF-oldal/tételszám, Challenge és implementációs deklaráció külön-külön azonosítása; a pinned Mathlib s=1 konvenció és formális scope megőrzése.

- 3\. E1–E7 relációk kitöltése evidencianévvel, forrás-, cél- és időhorgonnyal; a hiányzó natív proofhoz NOT_RUN, hiányzó szakreviewhoz NOT_REVIEWED beírása.

- 4\. A historical BLOCK/MATCH döntés és digest leképezése; kifejezetten megtiltani, hogy MATCH „formally proven” jelölést adjon.

- 5\. M1 kimenetek statikus séma/teljesség-ellenőrzése és lezárás; minden még hiányzó byte / reláció / alternatív út elnevezése.

### 4.4 M1 elfogadási/lezárási feltételek

| **Feltétel** | **Ellenőrizhető kritérium**                                                                                                                                |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| M1-A         | Az 5 kimeneti fájl létrejön, és egyetlen pinned subjectet tartalmaz; checksum szerint azonos upstream és történeti archive, nincs MAIN/HEAD csendes csere. |
| M1-B         | A claim-card a kézirat 1.1 tételét, Lean-célt, s=1 teljesítés kontra pólus kettősségét és a kizárt claims-okat egyértelműen megnevezi.                     |
| M1-C         | E1–E7 teljesen elszámolt: meglévő evidence ref VAGY pontos missing_ref és ok; „UNKNOWN”-ból nem lesz PASS.                                                 |
| M1-D         | A történeti eredmény mindenhol BLOCK / MATCH / no certificate; native capture NOT_IMPLEMENTED; semantic review NOT_REVIEWED.                               |
| M1-E         | Legalább három nyitott kérdéshez next required evidence és owner/not_assigned; nincs úgy lezárt kérdés, hogy az alátámasztó bájtok hiányoznak.             |
| M1-F         | A végrehajtási napló csak read-only adatfeldolgozást mutat; nincs repo-push, commit, PR, CI/Lean/test/replay futás vagy külső üzenet.                      |

Az M1 sikeres lezárása NEM jelenti az egész pilot sikerét. Az M1 csak a következő embernek szükséges pontos, hiányőrző tudástérképet hozza létre. M5 gépi replay és M6 emberi próba későbbi külön mérés.

## 5. A három terv közös elfogadási szerződése

A technikai terv H01–H07 feltételei és E1–E7 relációi normatív horgonyként szerepelnek a kísérleti és megvalósítási tervben. A kísérleti K01–K20 mind előzetesen tervezett, NOT_RUN; csak későbbi külön engedélyezés és futási receipt változtathatja státuszukat. Minden verzió és állapot a konkrét artefaktumhoz kötött, nem fordítható automatikusan az új repó-mainre.

Végső zárócsomag várt állítása: „A qrh003_zeta tárgyú, pinned forrásra és történeti auditbizonyítékra épülő átadási csomagból egy független átvevő azonosította és önállóan újraszámította az offline BLOCK döntést, megkülönböztette a hiányzó matematikai igazolást, és egy konkrét nyitott kutatási feladatot meg tudott nevezni.” Ezt a mondatot csak akkor szabad tényleges eredményként közölni, ha a gépi és emberi próbák valóban lefutottak.

## Forrásjegyzék és rögzített ellenőrzési határ

**\[F1\]** Történeti, opcionális auditterv: `PULSEMECH_OPENAI_MATH_003_AUDIT_TERV_v0.docx` (2026-10-07, 28 oldal), 82 686 bájt; SHA-256 `2cb23a9901cf4d50c2ba3b871bedc5ac2de1546bfeecf46f741014ea65a60e8e`. Csak külön owner-controlled Library-hozzáférés bizonyított; nincs nyilvános tárolási horgony. Az M1 normatív forrásai a pinned upstream és a meglévő QRH003 reference/bizonyítékbájtok, nem ez a DOCX.

**\[F2\]** Rögzített upstream: https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a ; releváns útvonalak: preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf; lean/docs/003.md; lean/ComparatorChallenges/QuasiRiemannHypothesis.{lean,json}; lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean.

**\[F3\]** QRH003 v0.1.3 README és forrás-/evidence-nyilvántartás: https://github.com/HKati/pulse-release-gates-0.1/tree/c0895b920399cafbc14aa9fd3b6d3b68671f0220/studies/openai_math_003_qrh_v0 (olvasott main: c0895b920399cafbc14aa9fd3b6d3b68671f0220).

**\[F4\]** Meglévő implementáció és vizsgálati jegyzőkönyv: PR \#2907 (v0.1.2, 185 helyi PASS), PR \#2909 (v0.1.3, 220 helyi PASS) – https://github.com/HKati/pulse-release-gates-0.1/pull/2907 és /pull/2909; az izolált QRH suite nem a root CI automatikus része.

**\[F5\]** Történeti bájtok: PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip; méret 23 453 781 B; SHA-256 ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc; ezen munkamenetben csak statikus archívum-/digestolvasás történt.

**\[F6\]** Megőrzött qrh003-pilot-002-20261007 rekordok: döntés BLOCK; replay MATCH; decision SHA-256 1383ee891397b686f4c12f96137a8e58ae1f8ed4b89c9232baac0b637e512276; natív proof capture NOT_IMPLEMENTED; production certificate nincs.

**\[F7\]** PULSEMECH_TRANSITION_METER.md, main c0895b920399cafbc14aa9fd3b6d3b68671f0220: hat tengelyes általános státuszarchitektúra; történeti QRH003-observer nyolc külön tengelye mint szakterületi vetület.

## Melléklet A – nyitott kutatási kérdések kezdőjegyzéke

Ezek a végrehajtás első átadási kérdései, nem előzetesen megoldottnak tekintett problémák. Az egyes kérdésekhez később kötelező a status, verifier, evidence és reviewer-határ megadása.

| **Kérdés**                        | **Jelen bizonyítéki állapot**                                                                      | **Lezáró új adat**                                                                                                |
|-----------------------------------|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| Q-ZETA-1 – pólus/totalizáció      | A Mathlib riemannZeta teljes függvénye és a meromorf ζ klasszikus olvasata elkülönítendő.          | A definíciós/analitikus folytatás és s=1 kivétel pontos reviewja, digesthez kötött matematikai szakértői receipt. |
| Q-PROOF-1 – natív proof capture   | A history BLOCK: proof capture NOT_IMPLEMENTED, clean Lean/Comparator/axiom receipt nincs.         | Exact toolchain+binary és teljes dependency/patch zár; külön natív build/kernel/export/axiom felvételek.          |
| Q-RETAIN-1 – bájtmegőrzés         | Az eredeti felmérésben a 42 lock rekordból 32 forráscsomag hiányzott; új megőrzési szerződés kell. | A szükséges bájtok két külön megőrzött példánya, licencek és visszaolvasási jegyzőkönyv.                          |
| Q-HANDOFF-1 – külső megérthetőség | A vak emberi átadás még NOT_RUN.                                                                   | M6 öt kérdéses, segítés nélküli átvevői teszt, B1/T kontroll és állapotkülönbség.                                 |
