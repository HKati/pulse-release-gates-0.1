# PULSEmech QRH003 — tudásfolytonossági pilot: Kísérleti terv (v0.1)

**Próbák, kontrollok, Transition Meter-kritériumok, gépi és emberi átadás**

*V0.1 \| Tervezési állapot \| A terv elkészítésekor nem történt repoírás és nem indult új audit-, Lean-, CI- vagy replay-futás*

| **Kísérleti állítás** A hozzáadott átadási réteg a meglévő QRH003 döntési bizonyítékokra építve kimutathatóan javítja a bizonyítékhatár felismerhetőségét, vagy helyesen megállapítja, hogy nincs mérhető többlet. Az eredeti matematikai igazolás NOT_RUN/BLOCK státusza változatlan. |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

## 1. Előzetes feltételek és kísérleti csatornák

A vizsgálat tárgya kizárólag qrh003_zeta. Fagyasztott subject: openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a. Kiinduló történeti csomag: qrh003-pilot-002-20261007, v0.1 eredeti verifier snapshot; BLOCK / MATCH, nincs certificate. A ma olvasott v0.1.3 code kifejezett, külön új anchor nélkül nem nevezhető a történeti futás ellenőrzőjének.

| **Kar**                  | **Mit kap az átvevő**                                                                                | **Mit mérünk**                                    |
|--------------------------|------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| B0: közönséges forrás    | Pinned upstream Git/PDF/Lean/files és szokásos dokumentáció; explicit QRH003 átadási overlay nélkül. | Független eligazodás csak a meglévő forrásokon.   |
| B1: jelenlegi QRH003     | B0 + v0.1.3 README és eredeti, ellenőrzött v0.1.1 history packet, minden megőrzött korláttal.        | A meglévő QRH003 már önmagában mennyit old meg?   |
| T: QH continuity overlay | B1 + claim card, reláció-státuszmátrix, nyitott kérdések, preservation index és handoff útmutató.    | Valóban ad-e nem redundáns többletet az új réteg? |

Az összevetésben ugyanaz a subject-commit, archívumbázis, átvevői feladat, időmérési szabály és hozzáférési jog szerepel. A sorrendi tanulási torzítást váltakozó kar-sorrenddel és külön átvevőkkel csökkentjük; egyetlen átvevő esetén az eredmény leíró, nem általánosítható. A B0 kar nem köteles sikerre – az információhiány szintén mérés.

## 2. Előre rögzített próbastátusz

| **Státusz**  | **Jelentés**                                                                                                                                |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| PASS         | Az elvárt határviselkedés megfigyelhető és a szükséges fájlhoz/futáshoz kötött bizonyíték teljes; elvárt BLOCK is PASS teszteredmény lehet. |
| FAIL         | Igazoltan rossz döntés, hibás átadás, bizonyított félreminősítés, vagy megkerülés; a kapu naplója nem írja felül a tényleges következményt. |
| INCONCLUSIVE | A megfigyelés vagy bizonyíték hiányos/ellentmondásos; nem számít sikernek.                                                                  |
| NOT_RUN      | Kizárólag tervezett, de meg sem indított próba; nem kerül a teljesített számlálóba.                                                         |

A történeti döntés BLOCK és replay MATCH már megőrzött eredmény: H0. Az alábbi K01–K20 esetek az új tudásátadási protokoll előírásai, e tervben mind NOT_RUN, kivéve ahol a történeti forrásból csak statikusan hozzáférhető előfeltétel ismert. Nem állítunk 20 végrehajtott próbát.

## 3. Próbamátrix – 20 előre rögzített eset

### Kísérletek K01–K05

| **ID / típus**                     | **Bemenet és eljárás**                                                                                                                                                                                 | **Elvárt kimenet / PASS feltétel**                                                             |
|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| K01 — Érvényes történeti packet    | Eredeti v0.1.1 ZIP + pilot_002; ellenőrzött read-only intake, majd külön engedéllyel eredeti replay. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása. | BLOCK + MATCH, nincs igazolás; PASS ha: A döntés és a replay azonos, korlát külön feltüntetve. |
| K02 — Claim és fájlhorgony pozitív | Pinned PDF 4. o. 1.1 + challenge + Nonvanishing.lean; relation-tábla készítése. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                      | E1 forráskötés, E2 review-pending; PASS ha: Nincs VERIFIED semantic jelző review nélkül.       |
| K03 — Idegen upstream commit       | A manifest pinned commitját másik commitra cseréljük; ne töltsünk új forrást a teszt alatt. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.          | IDENTITY_CONFLICT / BLOCK; PASS ha: Nem fogad el csak branchnevet/HEAD-et.                     |
| K04 — Idegen tétel sikerreceiptje  | Zéta sorhoz Dirichlet/Hecke exportazonosítót rendelünk. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                                              | CLAIM_MISMATCH / BLOCK; PASS ha: A célazonosság explicit és hibás kötés észlelt.               |
| K05 — Módosított kézirati állítás  | A claim-card 7/8 küszöbét vagy tartományát módosítjuk, PDF-változás nélkül. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                          | SCOPE_CONFLICT; PASS ha: Nem marad azonos hivatkozású VERIFIED claim.                          |

### Kísérletek K06–K10

| **ID / típus**                           | **Bemenet és eljárás**                                                                                                                                                                 | **Elvárt kimenet / PASS feltétel**                                                                              |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| K06 — Módosított Lean tételtípus         | A tételkontraktus kwantorját/feltételét módosítjuk fiktív mintában. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                  | FORMAL_SCOPE_CHANGED; PASS ha: Nincs egyedi hasonló nevű fájlból PASS.                                          |
| K07 — Módosult definíció azonos típussal | A hivatkozott definíció-/deklarációlezárás azonos nevű eltérő bájtú tagot tartalmaz. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása. | DEFINITION_BINDING_CONFLICT; PASS ha: A zárttípus-azonosítás nem csak pretty-print.                             |
| K08 — Más függőség / patch               | lake-manifest vagy patch-sorrend váltása a statikus leltárban. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                       | EFFECTIVE_TREE_UNBOUND; PASS ha: Az eredeti lock/patch effektív fa nem minősül egyezőnek.                       |
| K09 — Hiányzó natív Lean receipt         | A meglévő NOT_IMPLEMENTED capture-t pozitívként próbáljuk leírni. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                    | PROOF_NOT_RUN; handoff meta-visszautasítás; PASS ha: A hiányzó build nem válik formális sikerrel egyenértékűvé. |
| K10 — Más futás sikere                   | TEST sikerreceiptet jelölünk az eredeti PRODUCTION ticket bizonyítékául. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.             | RUN/TRUST_DOMAIN_CONFLICT; PASS ha: A run/attempt/trust domain nem mosható össze.                               |

### Kísérletek K11–K15

| **ID / típus**                            | **Bemenet és eljárás**                                                                                                                                                           | **Elvárt kimenet / PASS feltétel**                                                                                          |
|-------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| K11 — Hiányzó auditdöntési rekord         | Decision.json eltávolítása próbacsomagból; az eredeti archívumot nem írjuk át. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása. | DECISION_MISSING; PASS ha: Hash/hivatkozás nem pótolhatja az eredeti bájtokat.                                              |
| K12 — Replay hamis túlértelmezése         | BLOCK/MATCH kézhezvétele után „proof reproduced” címkét generálunk. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.            | OVERCLAIM_REJECTED; PASS ha: A címke csak decision replay, proof NOT_RUN.                                                   |
| K13 — Szemantikai review hiánya           | Reviewer receipt nélkül semantic_match=true mezőt teszünk a kártyára. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.          | EXPERT_REVIEW_MISSING; PASS ha: READY nincs; matematikai értelem nem bizonyított.                                           |
| K14 — Póluspont értelmezési határa        | Elhagyjuk a s=1 konvenciót a zéta claim-cardról. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                               | CLAIM_INTERPRETATION_INCOMPLETE; PASS ha: A Mathlib-teljesítés és klasszikus meromorf olvasat elkülönítve kell szerepeljen. |
| K15 — Részleges eredmény túláltalánosítva | Csak zéta cél látható, de „teljes Math 003 formally checked” állítást írunk. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.   | SCOPE_OVERCLAIM; PASS ha: A négy claim / öt export és kizárások nem tűnhetnek el.                                           |

### Kísérletek K16–K20

| **ID / típus**                                  | **Bemenet és eljárás**                                                                                                                                                                         | **Elvárt kimenet / PASS feltétel**                                                                                          |
|-------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| K16 — Python forráscache/launcher csere         | v0.1.3 kontrollként nem jóváhagyott .pyc vagy mutable entry megadása jövőbeli tesztfixtúrán. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása. | SOURCE_BOUNDARY_BLOCK; PASS ha: Nem juthat TEST ALLOW-ig mérgezett cache-ből.                                               |
| K17 — Csak hash maradt a szükséges bájt helyett | A handoff csomagból az archívumot kivesszük, sha256-sor megmarad. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                            | PRESERVATION_BYTES_MISSING; PASS ha: Nem nevezhető reprodukálható archívum-átadásnak.                                       |
| K18 — Hiányzó nyitott kérdés                    | A kérdésjegyzékből a proof-capture / semantic review hiányát töröljük. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.                       | UNRESOLVED_PATH_LOST; PASS ha: Átadás READY nincs, nyitott kérdés rekonstruálható kell maradjon.                            |
| K19 — TM hamis oksági kizárólagossága           | A policy-testből matematikai oksági szükségesség/kizárólagosság címkét képzünk. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.              | CAUSAL_OVERCLAIM; PASS ha: Csak a lokális TEST-kapuváltozás következménye rögzíthető.                                       |
| K20 — Vak átvevő, megszakítás nélkül            | Másik ember/ügynök csak csomagot és előírt kérdéseket kap, készítőt nem kérdezheti. / Eljárás: izolált próbapéldány vagy csak dokumentum-variáns, soha nem az eredeti bájtok átírása.          | Öt válasz + egy folytatási kérdés, forrásrefs; PASS ha: Nincs szóbeni segítés, minden válasz minősített és visszaolvasható. |

## 4. Gépi replay és kézi értelmezés – külön két vizsgálat

### 4.1 Gépi replay

A későbbi végrehajtó az eredeti historical verifier snapshotot, az eredeti anchor/bundle/decision bájtokat és a pinned futási környezetet használja. Először függetlenül kiszámítja az archívum és belső tagjai digestjét, megvizsgálja a manifestet, majd kizárólag a korábbi REPLAY_PILOT.md szerint hajtja végre az offline replayt. A v0.1.3 aktuális root verifier nem cserélhető az eredeti v0.1 snapshotra.

Megőrzendő: futási parancs és argumentumok, run/attempt, futtató exact hash, input manifest/hash, process exit és normatív output, döntés byte digest, \`MATCH\` vagy eltérés, host-rendszer azonosítói, független időbélyeg ha elérhető. Várható result a korábbi forrás alapján BLOCK / MATCH, de a független jövőbeli próba ma NOT_RUN.

### 4.2 Emberi átadási vizsgálat

Az átvevő előzetesen nem kapott belső magyarázatot, nem kérhet szóbeli segítséget, és kérdéseit előre rögzített formában jegyzi. A csomag alapján saját szavaival és pontos fájlhorgonnyal válaszol: (1) mi az egyetlen vizsgált állítás; (2) melyik forráscommit/artefaktum/authority-profil érvényes; (3) mit tud önállóan replayelni; (4) mi nem igazolt; (5) melyik konkrét nyitott kérdésen folytatható a munka. Időráfordítás és visszakeresési lépések a B0/B1/T karoknál azonos módon mérendők.

A teljesítés dokumentumszintű: mind az öt válasz megfelel az előre rögzített megoldókulcsnak, nincs félrevezető matematikai igazolási állítás, és az átvevő legalább egy kutatható folytatási kérdést a hiányzó relációhoz és szükséges bizonyítékhoz köt. Szubjektív „értem” visszajelzés nem elegendő. Külső függetlenség csak tényleges személy/azonosító és protokoll után állítható.

## 5. Mérőszámok és kiértékelés

| **Mérőszám**             | **Pontosan számított egység**                                                  | **Küszöb / értelmezés**                                                          |
|--------------------------|--------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| Decision replay match    | Bájtazonos normatív döntés / érvényes jövőbeli offline futás                   | 1/1 kötelező a teljes kézhezvett replay-állításhoz; ma NOT_RUN.                  |
| Overclaim count          | Proof/semantic/acceptance státusz téves VERIFIED-nek állítva                   | 0 tolerált; bármelyik hibás minősítés FAIL.                                      |
| Negative-case prevention | K03–K19 szükséges elutasításai / végrehajtott informatív esetek                | Minden kötelező futtatott negatív próba meg kell feleljen; NOT_RUN nem a nevező. |
| Retained byte coverage   | Hivatkozott kötelező bájttételek visszaolvasható száma / összes kötelező tétel | 100% a deklarált aktuális csomagban; külső szerver URL nem bájtmegőrzés.         |
| Evidence-edge coverage   | E1–E7 közül refs + ellenőrzési státusz + known gap együtt rögzített élek száma | 7/7 elszámolt; lehet INCOMPLETE; nem 7/7 VERIFIED.                               |
| Handoff task accuracy    | Öt kérdés közül helyesen és forrással megválaszolt                             | 5/5 szükséges a lokális átvehetőségi teljesítéshez.                              |
| Continuation specificity | Nyitott kérdésnek van missing_edge, szükséges új bizonyíték, reproducer        | ≥1 helyes konkrét folytatási feladat.                                            |
| Incremental utility      | T-kar helyes válaszpontossága / idő / hiányfelismerés B1-hez képest            | Előre rögzített metrikák szerint; nincs különbség → „nem kimutatható többlet”.   |

## 6. Lezárási döntési logika

TECHNICAL HANDOFF READY csak H01–H06 teljes, érvényes és archivált rekordjával, az adott határra vonatkozó hiányok explicit leírásával jelölhető. HUMAN HANDOFF VERIFIED csak H07 tényleges független átadási próbája után állhat elő. Ha elvárt pozitív replayt nem tudunk végrehajtani, a gépi rész INCONCLUSIVE/NOT_RUN, nem PASS. A QRH003 audit result továbbra is BLOCK; nincs tanúsítvány.

Kísérleti siker = valid döntés-replay + hibák helyes elutasítása + 5/5 emberi átadási eredmény + a hiányok megőrzése + legalább egy rögzített, nem redundáns előny a B1 kontrollhoz képest. A pilot fontos negatív eredménye is publikálható: bizonyítéklánc-átadás működik, de B1-hez képest mérhető többlet nincs; vagy a megőrzéshez/teljes replayhez még szükséges bájt hiányzik. Mindkettő levonható új matematikai állítás nélkül.

Stop feltételek: sérült történeti archívum, hiányzó rögzített forráspár, váratlan source-binding konfliktus, bizonyítatlan reviewt állító címke, eltérő futás igazolása, nem reprodukálható döntés vagy tárolási/licencprobléma. A hibásan félbeszakított esetet lezáró receipt és oka együtt őrzendő.

## 7. Kísérlet előtti kötelező regiszter

Minden jövőbeli próba előtt fagyasztani kell: test_id, tamper fixture digest, per-próba manifest, original-bundle hash, elvárt output és reason_code, verzió/runner/tool hash, output könyvtár, tesztelésre jogosult végrehajtó, mintanagyság, próbák sorrendje, acceptance változtatási tilalom. A műveletekhez új tulajdonosi engedély kell; ez a terv nem engedélyez CI, Lean vagy QA futást.

## Forrásjegyzék és rögzített ellenőrzési határ

**\[F1\]** OpenAI Math 003 – független PULSEmech audit terve (2026-10-07, 28 oldal): PULSEMECH_OPENAI_MATH_003_AUDIT_TERV_v0.docx; korábbi felmérés, nem jelenlegi natív proof-igazolás.

**\[F2\]** Rögzített upstream: https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a ; releváns útvonalak: preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf; lean/docs/003.md; lean/ComparatorChallenges/QuasiRiemannHypothesis.{lean,json}; lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean.

**\[F3\]** QRH003 v0.1.3 README és forrás-/evidence-nyilvántartás: https://github.com/HKati/pulse-release-gates-0.1/tree/c0895b920399cafbc14aa9fd3b6d3b68671f0220/studies/openai_math_003_qrh_v0 (olvasott main: c0895b920399cafbc14aa9fd3b6d3b68671f0220).

**\[F4\]** Meglévő implementáció és vizsgálati jegyzőkönyv: PR \#2907 (v0.1.2, 185 helyi PASS), PR \#2909 (v0.1.3, 220 helyi PASS) – https://github.com/HKati/pulse-release-gates-0.1/pull/2907 és /pull/2909; az izolált QRH suite nem a root CI automatikus része.

**\[F5\]** Történeti bájtok: PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip; méret 23 453 781 B; SHA-256 ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc; ezen munkamenetben csak statikus archívum-/digestolvasás történt.

**\[F6\]** Megőrzött qrh003-pilot-002-20261007 rekordok: döntés BLOCK; replay MATCH; decision SHA-256 1383ee891397b686f4c12f96137a8e58ae1f8ed4b89c9232baac0b637e512276; natív proof capture NOT_IMPLEMENTED; production certificate nincs.

**\[F7\]** PULSEMECH_TRANSITION_METER.md, main c0895b920399cafbc14aa9fd3b6d3b68671f0220: hat tengelyes általános státuszarchitektúra; történeti QRH003-observer nyolc külön tengelye mint szakterületi vetület.

## Melléklet A – kitöltetlen átvevői tesztreceipt

Ez a sablon későbbi méréshez készült. A mezők aktuális kísérleti állapota NOT_RUN. A történeti BLOCK/MATCH gépi eredmény és a későbbi emberi megfelelés nem azonos esemény.

| **Mező**              | **Átvevői bizonyíték – később kitöltendő**                                                            |
|-----------------------|-------------------------------------------------------------------------------------------------------|
| Környezet és szereplő | participant_id; no_verbal_help=true; test_arm=B0/B1/T; received_packet_sha256; execution_timestamp    |
| Q1: tárgy             | Kézirat/állítás pontos hivatkozása, claim ID, Lean-célazonosító.                                      |
| Q2: feltételek        | Source commit, verifier/policy kötés, trust domain, kivételek és hiányok.                             |
| Q3: replay            | Döntésújraszámítás parancsa és kimenete; NOT_RUN, ha nem futott.                                      |
| Q4: nem igazolt       | Proof capture, szemantika, tudományos elfogadás; mindegyik külön status és bizonyíték.                |
| Q5: továbblépés       | Konkrét missing_edge, szükséges új evidence, következő kutatási lépés.                                |
| Értékelés             | 0–5 dokumentált válasz, overclaim_count, kézi review receipt, verdict PASS/FAIL/INCONCLUSIVE/NOT_RUN. |
