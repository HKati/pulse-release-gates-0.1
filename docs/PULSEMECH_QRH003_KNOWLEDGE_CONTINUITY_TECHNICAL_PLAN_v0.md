# PULSEmech QRH003 — tudásfolytonossági pilot: Műszaki terv (v0.1)

**QRH003 tudásfolytonossági pilot – állításhatár, bizonyítéklánc, adatkontraktus és Transition Meter**

*V0.1 \| Tervezési állapot \| A terv elkészítésekor nem történt repoírás és nem indult új audit-, Lean-, CI- vagy replay-futás*

| **Műszaki tézis** Nem a zétaállítás matematikai igazságát igazoljuk. A rögzített zétaállítás és a bizonyítékainak viszonya átadható úgy, hogy a történeti BLOCK újraszámítható legyen, a hiányzó formális/szemantikai igazolás pedig ne változhasson hallgatólagos sikerré. |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

## 1. Pilotállítás és autoritási határ

PILOT-K1 – a rögzített openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a Math 003 „qrh003_zeta” egységéhez készített átadási csomagból az átvevő az eredeti forrásokat, a szűk állításjelentést, a történeti QRH003 döntés pontos bizonyítékait és a nyitott kérdések folytatási pontját képes rekonstruálni. A történeti döntés eredménye BLOCK, offline replay-receiptje MATCH; a csomag e két állítást tartja meg, nem állít matematikai bizonyítást.

A szigorú siker két részből áll: (i) a meglévő döntéshez tartozó bemeneti bájtok és eredmények függetlenül azonosíthatók, és a jövőbeli, külön engedélyezett replayer ugyanazt a döntést számolja; (ii) egy másik végrehajtó az előzetesen rögzített öt átadási kérdésre a készítő segítsége nélkül válaszol, és nem minősíti a hiányzó Lean/proof/szemantikai bizonyítékot igazoltnak. Egyetlen elemet sem minősítünk utólag már teljesítettnek.

Határon kívül: Riemann-hipotézis, a QRH matematikai helyességének bizonyítása, összes négy Math 003 claim teljes lezárása, upstream publikálás blokkolása, teljes natív Lean-kernel bizonyítás, közösségi tudományos konszenzus vagy a tudás társadalmi koncentrációjának mérése.

Lehetséges nem redundáns többlet: a kijelölt kézirati állítás, a formális cél, a tényleges tesztelt/verifikált artefaktumok, a hiányállapotok, a döntéshatár és a következő kutatási kérdés egyetlen, ellenőrizhető átadási egységbe kötése. Amennyiben ezt a meglévő Git/Lean/CI/archive és QRH003 riport ugyanazzal a pontossággal már biztosítja, az eredmény „nem kimutatható többlet”.

## 2. Források és tényleges állapot – 2026-10-19

| **Elem**                   | **Ellenőrzött tény**                                                                                                | **Érvényességi korlát**                                                  |
|----------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| Upstream forrás            | openai/math@adc7f1241b42…; PDF és Lean-scope/claim map rögzítve.                                                    | A rögzített forrás ≠ formális ellenőrzés.                                |
| Korábbi audit (F1)         | Két PDF bájtazonosság; 4 claim/5 export; 14 011 modul statikus import-gráf; 23 patch-terv.                          | Korábbi statikus audit, nem natív Lean-build vagy teljes runtime.        |
| QRH003 implementáció       | A jelenlegi study v0.1.3, forráshoz kötött indítás, bizonyítékbefogadás, auditdöntés, offline replay és observer.   | A PR \#2909 szerint 220 helyi PASS; ez nem most újrafuttatott teszt.     |
| Történeti payload          | A v0.1.1 teljes ZIP megvan; SHA-256 egyezik; benne a pilot_002 anchor, bundle, verifier snapshot, decision, replay. | A ZIP eredeti történeti környezetet tartalmaz, nem a v0.1.3 snapshotját. |
| Történeti döntés           | qrh003-pilot-002-20261007: BLOCK; replay MATCH; hét technikai gate nem teljesült.                                   | MATCH = döntés-replay, nem Lean-bizonyítás.                              |
| Natív capture / szakreview | NOT_IMPLEMENTED, illetve NOT_REVIEWED; production QRH certificate nincs.                                            | Sematikus forrásmap nem ad igazolt szemantikai megfelelést.              |

A v0.1.3 study pinned PULSE-alapja továbbra is 288bb9a45764d2a30f72fdf4c417e9dd5b3087c5. A mai repo-main (c0895b920399cafbc14aa9fd3b6d3b68671f0220) nem cserélheti ki csendben a történeti verifier snapshotját. A gyökér-CI sikere önmagában nem igazolja az izolált 220 QRH teszt futását.

## 3. A kiválasztott matematikai egység

Kézirati horgony: „The Quasi-Riemann Hypothesis – September 30, 2026”, 1.1. tétel (PDF 4. oldal). A szűk klasszikus olvasat: a Riemann-zétafüggvénynek nincs zérusa Re(s)\>7/8 tartományban, a meromorf pólus értelmezését külön kezelve. A Lean-cél: OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re; forrás: lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean; challenge: lean/ComparatorChallenges/QuasiRiemannHypothesis.lean és ugyanott .json.

> {s : ℂ} (hs : (7 / 8 : ℝ) \< s.re) : riemannZeta s ≠ 0

Kritikus szemantikai határ: a Lean-állítás nem tartalmaz külön s ≠ 1 feltételt. A pinned Mathlib riemannZeta teljes függvény konvenció szerinti, nemnulla értéket rendel a klasszikus pólushoz. A meromorf zérusmentesség és a teljes függvény s=1 pontbeli állítása nem ugyanaz a mondat. A kézirat–formális cél kapcsolat szakértői reviewja köteles rögzíteni a pólust, az Re(s)\>1 tartománybeli egyezést, az analitikus folytatás definíciós hídját, a kvantorokat és a használt axiómákat. Egyiket sem jelöljük automatikusan VERIFIED-ként.

A pilot egyetlen claim-családra szűkül. A Dirichlet, Hecke és Landau–Siegel célok összevetési kontextusként megőrzendők, de nem kerülnek „ellenőrzött” állapotba azért, mert ugyanabban az upstream családban találhatók.

## 4. Bizonyítékút és szerephatárok

> Kézirat/PDF + TeX (pinned) → claim_card: mit mondunk?  
> → scope + challenge + deklaráció + definíciók (pinned)  
> → függőségek, patchek, eszközlánc és használt binárisok  
> → megőrzött tényleges végrehajtási receipt (ha van)  
> → policy + materializált gate-set → QRH003 decision  
> → eredeti snapshotból offline replay → Transition Meter  
> → preservation manifest + nyitott kérdések → független átadás

A kézirati egyezést nem a PDF-hash igazolja: külön „manuscript_contains_claim” és „claim_maps_to_formal_target” kapcsolat kell. A Git commit csak forrásazonosságot rögzít. A Lean-ellenőrzés és axiómaexport saját natív receiptet igényel. A QRH003 offline döntés reprodukciója csak a döntési függvényt érinti. A human interpretation külön vizsgálat.

Authority: a Transition Meter itt diagnosztikai observer; authority_effect=none. A QRH003 saját offline auditigazolására vonatkozó kaput nem bővítjük és nem lazítjuk. A tudás-átadási READY minősítés sem production certificate, sem OpenAI-publikációs engedély.

## 5. Új, additív adatszerződések – terv, nem implementáció

| **Tervezett hordozó**                 | **Kötelező információ**                                                                                                                                                         | **Elhatárolás**                                                |
|---------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| claim_card_qrh003_zeta_v0.json        | claim_id, natural_language_claim, manuscript_locator, pole_convention, formal_target, exact_scope, excluded_claims, evidence_refs, semantic_review_status.                      | A szöveg nem helyettesíti a hivatalos matematikai szakreviewt. |
| evidence_relations_v0.json            | relation_id, source/target IDs, kind, required_obligation, evidence_refs, old/new state, artifact digest, verifier, event/observation time, confidence helyett konkrét státusz. | Minden él külön bizonyítékot igényel.                          |
| transition_assessment_v0.json         | Nyolc történeti QRH003 observer-tengely, kapcsolódó evidenciák, korlátok, újrarenderelhető állapotmátrix.                                                                       | A történeti fájl érintetlen; új az overlay.                    |
| open_questions_v0.json                | question_id, missing_edge, why_open, reproducer_instruction, required_expertise, blocking_scope, candidate_next_action, owner_or_unassigned.                                    | Nem tartalmaz megoldottnak jelölt feladatot bizonyíték nélkül. |
| preservation_inventory_v0.json        | Path, bytes, full SHA-256, access, retention, owner, license record, exact runtime/pins, retrieval method, observed availability.                                               | URL/DOI/hash nem tárolja önmagában a szükséges bájtokat.       |
| handoff_protocol_v0.md + receipt.json | Öt kötelező kérdés, vak átadó/átvevő eljárás, parancs-horgony, időbélyegek, válaszok és kategorizálás.                                                                          | Gépi replay és emberi átvehetőség külön rekord.                |

## 6. Relációk és kapufeltételek

| **Él** | **Kapcsolat**                                | **Kiinduló státusz és feloldás**                                                 |
|--------|----------------------------------------------|----------------------------------------------------------------------------------|
| E1     | PDF-bájt → 1.1. tétel                        | Forrásazonosság rögzített; a pontos olvasat ellenőrizendő claim-cardon.          |
| E2     | Tétel → scope/Lean cél                       | Source map megvan; semantikai review hiányzik; nem VERIFIED.                     |
| E3     | Lean cél → effektív forrás/dependency/binary | Statikus gráf és patch-terv megvan; build/használt bináris nincs teljesen kötve. |
| E4     | Effektív forrás → natív proof-verification   | NOT_RUN/NOT_IMPLEMENTED; nincs kitölthető pozitív proof receipt.                 |
| E5     | Megőrzött evidence + policy → BLOCK          | Történeti packethez kötött és reprodukált offline döntés.                        |
| E6     | BLOCK → replay MATCH                         | Történeti decision snapshotból rekonstruált, nem proof rebuild.                  |
| E7     | Packet → átvevő következtetés                | Jelenleg NOT_TESTED; későbbi független emberi próba.                             |

Kapu-jellegű H01–H07 elfogadási pontok csak az új tudásátadási metacsomagra érvényesek: H01 exact subject/bájtok; H02 explicit szűk claim és pólushatár; H03 E1–E7 relációk, status/refs és hiányok; H04 policy/verifier/run snapshot kötések; H05 igazolt history BLOCK + csak decision replay MATCH; H06 megőrzött bájtok, ellenőrzött elérhetőség és licencek; H07 az átvevő tényleges protokollja. Bármely hiány esetén handoff READY nincs; az eredeti QRH003 BLOCK változatlan.

## 7. Transition Meter – nyolc konkrét QRH003 tengely

| **Tengely**                           | **Történeti adat / jelen határ**                         | **Új átadási minősítés szabálya**                                                                 |
|---------------------------------------|----------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| relation_change_observation_status    | RECORDED: pinned claim → bizonyítékrelációk → BLOCK.     | OBSERVED csak eseményszintű bizonyíték+azonosság esetén; különben PARTIAL/UNRESOLVED.             |
| transition_path_verification_status   | VERIFIED_FOR_DECLARED_OFFLINE_DECISION.                  | Csak a ténylegesen végigellenőrzött döntésláncra VERIFIED; nincs proof-promotion.                 |
| endpoint_binding_status               | VERIFIED_FOR_ARTIFACT_AND_DECISION_ENDPOINTS.            | Csak manifest/anchor/status/decision/replay digesthez; a tudományos elfogadás nem végpont.        |
| time_order_status                     | LOCAL_ORDER_CONSISTENT_EXTERNALLY_UNVERIFIED.            | Per-él event/observation/verification idők; külső hiteles időt külön kell igazolni.               |
| alternative_path_closure_status       | PARTIAL_LOCAL_EMITTER_CONTROLS_OBSERVED.                 | A teljes publikációs megkerülést nem zárja ki a helyi emitterteszt.                               |
| reconstruction_reproducibility_status | VERIFIED_DECISION_REPLAY_ONLY.                           | Újraszámított döntés ≠ Lean rebuild ≠ független host.                                             |
| causal_sufficiency_status             | TEST_POLICY_CONTROL_OBSERVED_MATH_NOT_APPLICABLE.        | Csak a kontrollált TESZT kapueffektusára; matematikai oksági állítás nincs.                       |
| causal_necessity_status               | ONE_REQUIRED_GATE_MUTATION_OBSERVED_MATH_NOT_APPLICABLE. | Több kaput módosító tesztből nem szabad egyetlen kapu szükségességét levonni; izolált teszt kell. |

A központi Transition Meter-dokumentum hat általános status_axes mezőt ír elő (observation, binding, consistency, reproduction, causal, authority). Ezeket a nyolc QRH003 tengely fölötti kompatibilis vetületként is tároljuk, nem cseréljük fel a két sémát. Az ok-okozati értékek matematikai értelemben NOT_EVALUATED/N_A maradnak.

## 8. Megőrzési és hozzáférési terv

| **Réteg / konkrét bájt**                                                                                                                                            | **Hely és hozzáférés**                                                                                                    | **Tartós megőrzés feltétele**                                                                                                 |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| A / upstream forrás: két paper.pdf és TeX; 003.md; challenge .lean/.json; Nonvanishing.lean; Mathlib; lean-toolchain, lake-manifest.json, lakefile.lean, 23 patch   | OpenAI Git pinned commit; az átadási archívumba szükséges pontos forrásbájtok vagy jogszerű, ellenőrzött beszerezhetőség. | Minden normatív bemenet raw SHA-256, bájtméret és licenc, teljes dependency/patch-lista; a még hiányzó 32 csomag UNRETRIEVED. |
| B / történeti QRH003 v0.1.1 teljes ZIP; pilot_002 bundle, anchor, original verifier snapshot, policy, decision, replay, transition report, hash-locked wheel-fájlok | Jelenleg Libraryben megtalált archívum; külön owner-held és hozzáférhető másolat majd megtervezendő.                      | A 23 453 781 B ZIP teljes bájtja megőrzendő; hash-egyezés + visszaolvasási próba; privát kulcsmag nem része.                  |
| C / aktuális v0.1.3 study SOURCE_MANIFEST, EVIDENCE_REFERENCE, source_bound.py, reference, tests                                                                    | PULSE pinned main, olvasható forrás; v0.1.3 függőségi/hiteles launcher-horgonyok.                                         | A v0.1.1 archívumot nem kell átírni; a v0.1.3 forráskészlet külön verzióként marad.                                           |
| D / új kézirat- és handoff overlay                                                                                                                                  | Későbbi nem-repo csomag; megengedett belső tároló + kontrollált nyilvános kivonat.                                        | Két független, olvasható példány; minden tétel bájtjai hozzáférhetők, hiányukat külön státusz jelzi.                          |

Licenc-, tárhely- és biztonsági határ: a forráslicenceket az existing reference/licenses/ rekordokkal egyeztetni kell; a nyers kéziratokat, dependenciákat és binárisokat csak jogszerű jogosultsággal továbbadni. Pusztán az archiválás nem teszi nyíltan terjeszthetővé. Az eszközlánc reprodukciója Linux x86_64, CPython 3.12, glibc ≥ 2.34 és a lock szerinti környezet kérdése; a natív Lean és Comparator binárisdigesztje jelenleg nincs teljesen verifikálva. DOI/Zenodo/SWH állapotot a pilot nem módosít.

## 9. Aktív veszélyek és automatikus elutasítás

Idegen commit, idegen claim/export, teljes definíciós zárat érintő módosítás, hiányzó payload, nem zárt / alá nem támasztott manifeszt, hiányzó eredeti verifier, eltérő futáshoz tartozó siker, ugyanarra a pozícióra becsempészett .pyc, „fully formally verified” címke a NOT_RUN proof mellett, és megtagadott vagy félreérthető megőrzési feltétel külön hibafajta. Mindegyik az érintett kapcsolaton BLOCK/INCOMPLETE/CONFLICTING eredményhez vezet, nem töltődhet fel narratív következtetéssel.

Összehasonlító szabály: az új overlay csak akkor tekinthető hozzáadott értéknek, ha a QRH003 v0.1.3 meglévő README+archívum mellett a vak átvevő gyorsabban/pontosabban talál bizonyítékkötést vagy konkrét nyitott kutatási lépést – ezt a kísérleti terv méri. A negatív eredményt is megőrizzük.

## Forrásjegyzék és rögzített ellenőrzési határ

**\[F1\]** OpenAI Math 003 – független PULSEmech audit terve (2026-10-07, 28 oldal): PULSEMECH_OPENAI_MATH_003_AUDIT_TERV_v0.docx; korábbi felmérés, nem jelenlegi natív proof-igazolás.

**\[F2\]** Rögzített upstream: https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a ; releváns útvonalak: preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf; lean/docs/003.md; lean/ComparatorChallenges/QuasiRiemannHypothesis.{lean,json}; lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean.

**\[F3\]** QRH003 v0.1.3 README és forrás-/evidence-nyilvántartás: https://github.com/HKati/pulse-release-gates-0.1/tree/c0895b920399cafbc14aa9fd3b6d3b68671f0220/studies/openai_math_003_qrh_v0 (olvasott main: c0895b920399cafbc14aa9fd3b6d3b68671f0220).

**\[F4\]** Meglévő implementáció és vizsgálati jegyzőkönyv: PR \#2907 (v0.1.2, 185 helyi PASS), PR \#2909 (v0.1.3, 220 helyi PASS) – https://github.com/HKati/pulse-release-gates-0.1/pull/2907 és /pull/2909; az izolált QRH suite nem a root CI automatikus része.

**\[F5\]** Történeti bájtok: PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip; méret 23 453 781 B; SHA-256 ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc; ezen munkamenetben csak statikus archívum-/digestolvasás történt.

**\[F6\]** Megőrzött qrh003-pilot-002-20261007 rekordok: döntés BLOCK; replay MATCH; decision SHA-256 1383ee891397b686f4c12f96137a8e58ae1f8ed4b89c9232baac0b637e512276; natív proof capture NOT_IMPLEMENTED; production certificate nincs.

**\[F7\]** PULSEMECH_TRANSITION_METER.md, main c0895b920399cafbc14aa9fd3b6d3b68671f0220: hat tengelyes általános státuszarchitektúra; történeti QRH003-observer nyolc külön tengelye mint szakterületi vetület.

## Melléklet A – mintaszerződés és H01–H07 ellenőrzési pontok

Az alábbi struktúra tervezési példa, NEM jelenleg működő QRH003-export. A forrásazonosság és a tudományos érvényesség külön réteg. A már megőrzött BLOCK/MATCH történeti eredmény a példában nem válik ALLOW-vá.

> {  
> "schema_version": "qrh003_knowledge_handoff_v0",  
> "subject_commit": "adc7f1241b42e322a6451854ab7e4b4c146bf78a",  
> "claim_id": "qrh003_zeta",  
> "formal_target": "OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re",  
> "semantic_review": "NOT_REVIEWED",  
> "proof_capture": "NOT_IMPLEMENTED",  
> "historical_decision": {"run": "qrh003-pilot-002-20261007",  
> "result": "BLOCK", "replay": "MATCH"},  
> "authority_effect": "none",  
> "required_relations": \["E1", "E2", "E3", "E4", "E5", "E6", "E7"\],  
> "open_question_refs": \["Q-ZETA-1", "Q-PROOF-1", "Q-HANDOFF-1"\]  
> }

Az additív overlay előírt ellenőrzője utasítsa el a duplikált JSON-kulcsot, a forrásdigest nélküli normatív objektumot, a VERIFIED címkét bizonyító evidence_ref nélkül, a hiányzó required_relations kapcsolatot, és az olyan human-handoff VERIFIED állapotot, amelyhez nincs tényleges átvevői receipt.

| **Kód** | **Pozitív feltétel**                                                 | **Hiány esetén**                      |
|---------|----------------------------------------------------------------------|---------------------------------------|
| H01     | Egyetlen pinned subject, teljes kötelező bájtok + SHA-256.           | HANDOFF_NOT_READY: SOURCE_IDENTITY    |
| H02     | Szűk theorem, pólus/Mathlib-konvenció és kizárások explicitek.       | HANDOFF_NOT_READY: SEMANTIC_SCOPE     |
| H03     | E1–E7 reláció mindegyike bizonyítékhoz vagy pontos hiányhoz kötött.  | HANDOFF_NOT_READY: EDGE_COVERAGE      |
| H04     | Run, trust-domain, verifier, policy és gate-set identitás rögzítve.  | HANDOFF_NOT_READY: EXECUTION_BINDING  |
| H05     | BLOCK / MATCH / proof NOT_RUN együtt megőrzött.                      | HANDOFF_NOT_READY: DECISION_OVERCLAIM |
| H06     | A kötelező archív bájtok visszaolvashatók; megőrzési korlát látható. | HANDOFF_NOT_READY: PRESERVATION       |
| H07     | Független átvevő öt helyes válasza és folytatási kérdése receiptben. | HUMAN_HANDOFF_NOT_VERIFIED            |
