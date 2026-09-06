# PULSEmech — Recursive Self-Improvement and Transition Provability

## Evidence-bound change, evaluation continuity, and authority to proceed

```text
document_role: foundational_architecture
document_version: v0
current_concrete_domain: artifact_bound_ai_release_transitions
recursive_self_improvement_application: architectural_extension
authority_effect: none
implementation_change: none
source_review_date: 2026-09-06
source_review_commit: 30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f
```

This document applies the PULSEmech transition-measurement principle to
recursive self-modification. It distinguishes a change, an evidenced
transition, a justified improvement claim, and permission to proceed. It is
an architectural argument, not a report of an implemented general-purpose
recursive self-improvement system.

## 1. Central statement

A modification can change more than the next version of a system. It can
also change the inputs, dependencies, evaluation conditions, and permissions
under which subsequent modifications are produced and admitted.

The consequence need not wait at a distant endpoint. A change can already
influence the process locally and become part of the conditions for later
transitions, including through feedback.

> **Delaying evaluation does not delay the effects of a change.**

This does not mean that every modification has an immediate, detectable, or
persistent effect. It means that postponing an assessment supplies no reason
to assume that the modification's effects have also been postponed.

The engineering question is therefore not merely whether a system can
produce another version. It is what justifies calling that transition an
improvement, and what permits its result to become a basis for further action.

## 2. The problem is not chronological ordering

A version sequence is useful:

```text
S0 → S1 → S2 → ...
```

It is insufficient when the representation omits the changed relations,
transition paths, evidence, and feedback through which one version affects
the production of the next.

Chronological indexing does not itself imply an absence of feedback. A
recurrence can represent feedback when its state and transition definitions
preserve the relevant dependencies. The objection here concerns a
**state-only account**, not time ordering or recurrence notation as such.

The relevant object is:

```text
identified prior state and context
→ changed relation and evidenced path
→ identified resulting state and context
→ changed conditions for subsequent transitions
```

A rich state comparison can identify particular differences. It does not
necessarily identify the path that produced them. [1]

## 3. Why endpoints do not necessarily identify the transition

Let `P(S0, S1)` be the admissible paths between two measured endpoints, and
let `M_E` retain only those endpoint measurements. If:

```text
p_a != p_b
M_E(p_a) = M_E(p_b) = (S0, S1)
```

then the endpoint record cannot distinguish the two paths. A claim that a
particular path occurred requires additional path-discriminating evidence.
This is the conditional non-injectivity argument developed in the Transition
Meter, not a claim that every possible system always has ambiguous paths. [1]

Three questions remain distinct:

```text
What differs between the observed states?
Which transition path connects them?
What causal role did that path play in a specified effect?
```

A transition record does not automatically establish causal necessity,
sufficiency, or completeness. Ordering and artifact binding can support a
reconstruction without resolving every alternative explanation. [1]

## 4. Self-modification is not yet demonstrated improvement

For this document, recursive self-modification means that a system modifies
components or conditions that participate in producing or assessing its later
modifications. Calling the process *self-improvement* adds an evaluative
claim; it does not prove that claim.

The following conclusions require different evidence:

| Conclusion | What must support it |
| --- | --- |
| A change occurred. | Identified observations or state differences. |
| This transition occurred. | A path bound to its states, sources, execution context, and evidence. |
| This transition contributed to this effect. | Claim-appropriate causal evidence, including treatment of relevant alternatives. |
| The candidate improved in a declared respect. | A valid comparison under identified objectives, measurements, constraints, and uncertainty. |
| The candidate may cross a defined boundary. | Satisfaction of the policy governing that exact boundary and candidate. |

A bounded performance improvement can be established without establishing a
complete account of a recursive process. Conversely, a reproducible
transition record is not by itself proof that performance improved.

Improvement need not be a single universal score. Its meaning can depend on a
specified task, comparison population, resource condition, non-regression
constraint, and acceptance rule. Those conditions must remain identifiable.

## 5. Evaluation conditions are themselves transition objects

The system being evaluated is not the only object that can change. A
recursive process may also modify its tests, objective, data selection,
scoring rule, policy, or verifier.

**A changed evaluation criterion must not silently replace the criterion
under which the improvement claim is made.**

Consider a hypothetical example. A candidate solves 60 of 100 tests. Remove
25 failed tests without changing the candidate's behavior, and the reported
rate becomes 60 of 75: 80% instead of 60%. The new rate describes a different
test population. It does not demonstrate improved performance on the
original population.

A defensible comparison must preserve the identities of both evaluation
contexts. When they differ, it must either establish a justified comparison
between them or report that the results are not directly comparable.

Changes to an objective, policy, or verifier are legitimate subjects of
development. Their adoption requires a separately identified transition
under an already applicable change rule. A proposed replacement must not
become its own sole basis for authorization merely because it reports success.

This does not require an infinite stack of new verifiers. It requires an
explicit, bounded acceptance basis and clear authority over changes to that
basis. The PULSEmech operator model retains human control of policy and
consequence while making the mechanical evidence machine-operable. [2]

## 6. What an iteration-bound record must preserve

The following are architectural requirements for this application, not a new
implemented schema or a claim of unlimited observation.

**Identity and scope.** Bind the source state, candidate state, source
revision, exact run and attempt where applicable, inputs, output artifacts,
and the boundary covered by the claim. Preserve dependencies on earlier
iterations when they are relevant to that claim.

**Path and time.** Identify the changed relations and the observed or
reconstructed path. Preserve element ordering, relevant boundaries, and the
distinction between event time, observation time, verification time, and
authority time. Record precision or uncertainty where applicable; a single
aggregate timestamp must not substitute for required element-level bindings.
These time distinctions follow the Transition Meter. [1]

**Evaluation and decision basis.** Bind the comparison baseline, evaluation
procedure, criteria, declared policy, effective requirements, and exact
verifier used. Identify which decision, if any, those records may support.

**Evidence classification.** Keep observed facts, reproducibly derived
relationships, assumptions, and unresolved information distinguishable.
Derived results retain the identities of their inputs and derivation method.
Unavailable evidence stays unavailable; it is not reconstructed as a fact
merely because a complete-looking record would be convenient.

**Bounded conclusions.** Preserve relevant alternative paths, observation
gaps, and causal questions that remain open. Evidence sufficient for one
claim may be insufficient for another. Where a required condition cannot be
established, it must not be treated as satisfied. An unrelated unknown does
not automatically block every possible decision.

## 7. Authority must precede the boundary it governs

Observation, evaluation, and permission to proceed are not interchangeable.
An experiment can produce evidence before a deployment decision, while the
decision still precedes the deployment it governs.

For a recursive application, the governed boundary must be explicit. It may
be admission of a candidate to the active system, incorporation of generated
material into shared memory, replacement of an evaluator, or permission for
a specified external operation. These are application examples, not claims
that all such boundaries are implemented by PULSEmech today.

A possible bounded admission relation is:

```text
candidate production and evaluation under existing permissions
→ exact transition and evaluation evidence
→ verification against the applicable decision basis
→ ALLOW or BLOCK before the defined admission boundary
→ admitted result and preserved context become inputs to later work
```

Candidate production may itself have effects. Those effects cannot be
declared harmless merely because a later promotion is gated. The application
must identify which effects are permitted during experimentation and which
require an earlier enforcement boundary.

A later evidence package cannot retroactively authorize an already crossed
boundary. A release decision does not imply control over every earlier
training, execution, or environment interaction.

## 8. Iterations must compose without losing their conditions

A valid local decision is scoped to an identified candidate, evidence set,
policy, verifier, and boundary. It is not a blanket permission for all later
versions.

When an admitted result becomes input to a later iteration, the next record
must retain the relevant predecessor identity and context changes. Earlier
evidence can be reused only where its applicability to the new claim is
established; a previous success signal is not sufficient by itself.

Even a chain of locally justified decisions does not automatically prove
unbounded improvement, global safety, or convergence. Claims across many
iterations need their own specified comparison conditions and composition
argument. The purpose of transition binding is to preserve the evidence
needed to examine those claims, not to declare them true in advance.

## 9. Relation to the present PULSEmech mechanism

The reviewed Technical Overview identifies artifact-bound AI release
transitions as the present concrete authority domain. It describes the
release relation as: [2]

```text
R = ⟨S, E, A, P, G, V, F, D⟩

S: exact subject and run identity
E: recorded release evidence
A: exact artifact and carrier identities
P: declared release-policy identity
G: workflow-effective materialized required-gate state
V: verifier identity and deterministic replay state
F: final gate-state carrier
D: terminal primary-CI ALLOW or BLOCK enforcement result
```

The decision-bearing path connects recorded current-run evidence, exact
bindings, policy-derived requirements, verifier replay, and final gate state
to strict fail-closed enforcement before deployment. Its determinism is
relative to those exact bound inputs. It does not imply that the underlying
AI behavior or an entire future training process is deterministic. [2]

The Transition Meter supplies the broader distinction between state
measurement, relation change, transition path, evidence record, and causal
claim. It identifies generalized domain extension as design rather than a
completed universal implementation. [1]

This document derives the recursive application from those two foundations.
It adds no gate, runtime interceptor, policy, verifier, or operational
permission. It does not supersede either canonical source, and it does not
claim that a general recursive self-improvement loop has been demonstrated.

## 10. Conclusion

Recursive self-improvement cannot be adequately justified by a sequence of
favorable endpoint reports when the claim also depends on how changes were
produced, evaluated, and admitted into subsequent operation.

The required connection is:

```text
identified change
+ evidenced transition
+ valid evaluation under identified conditions
+ justified authority at the governed boundary
```

Without that connection, successive states alone do not establish that a
feedback-driven self-modification process is an evidenced progression rather
than a succession of changes. The argument establishes an evidence
requirement; it does not establish that only one named implementation could
meet it.

PULSEmech makes that connection an explicit mechanical object within its
declared scope. Its relevance to recursive self-improvement is the ability
to ask, for each claimed step, what changed, what supports the comparison,
what remains unresolved, and what permits the result to affect later work.

> **The next version must not become its own justification. The transition,
> the evaluation basis, and the authority to proceed must remain bound to
> evidence, while the change may already be shaping the conditions of the
> next iteration.**

## 11. Source basis and document boundary

The source review is pinned to repository commit
`30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f` on 2026-09-06. It is a
read-only review of the cited architectural descriptions, not a new test
execution, CI result, or implementation certification. The source-review
commit is not the future commit identity of this document.

[1] [PULSEmech Transition Meter](../PULSEMECH_TRANSITION_METER.md), especially
sections 2, 4–6, and 9: transition identity, endpoint insufficiency,
claim-dependent evidence, and time binding.
[Reviewed revision](https://github.com/HKati/pulse-release-gates-0.1/blob/30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f/PULSEMECH_TRANSITION_METER.md).

[2] [PULSEmech Technical Overview](../PULSEMECH_TECHNICAL_OVERVIEW.md),
sections 1, 2, and 2A: present release-authority relation, terminal
pre-deployment decision, deterministic replay scope, and AI-native operation
with human policy and consequence control.
[Reviewed revision](https://github.com/HKati/pulse-release-gates-0.1/blob/30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f/PULSEMECH_TECHNICAL_OVERVIEW.md).

The requirements and examples in this document are architectural deductions
for the recursive application. They are not additional observed repository
results. Document classification follows the
[documentation index](INDEX.md): **Foundational architecture**.

---

## Magyar változat

```text
PULSEmech — Rekurzív önfejlesztés és az átmenetek bizonyíthatósága

Bizonyítékhoz kötött változás, az értékelés folytonossága és a továbblépés
jogosultsága

Ez a dokumentum a PULSEmech átmenetmérési alapelvét alkalmazza a rekurzív
önmódosításra. Elkülöníti a változást, a bizonyítékkal alátámasztott átmenetet,
a megalapozott fejlődési állítást és a továbblépés engedélyét. Architekturális
érvelés, nem egy általános rekurzív önfejlesztő rendszer megvalósításáról
szóló jelentés.

Dokumentumszerep: alapozó architektúra.
Változat: v0.
Jelenlegi konkrét tartomány: artifacthoz kötött AI-release-átmenetek.
Rekurzív önfejlesztési alkalmazás: architekturális kiterjesztés.
Önálló engedélyezési hatás: nincs.
Megvalósítási változtatás: nincs.
Forrásellenőrzés: 2026. szeptember 6.
Forrásként vizsgált commit:
30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f

1. Központi állítás

Egy módosítás nemcsak a rendszer következő változatát változtathatja meg.
Módosíthatja azokat a bemeneteket, függőségeket, értékelési feltételeket és
jogosultságokat is, amelyek között a későbbi módosítások létrejönnek és
elfogadhatóvá válnak.

A következménynek nem kell egy távoli végponton várakoznia. A változás már
helyben befolyásolhatja a folyamatot, és — visszacsatoláson keresztül is —
a későbbi átmenetek feltételrendszerének részévé válhat.

AZ ÉRTÉKELÉS ELHALASZTÁSA NEM HALASZTJA EL A VÁLTOZÁS HATÁSÁT.

Ez nem azt jelenti, hogy minden módosítás azonnali, észlelhető vagy tartós
hatással jár. Azt jelenti, hogy az értékelés későbbre helyezéséből nem
következik a hatások későbbre helyeződése.

A mérnöki kérdés ezért nem pusztán az, hogy a rendszer képes-e előállítani
egy újabb változatot. Hanem az, hogy mi indokolja az átmenet fejlődésnek
nevezését, és mi jogosítja fel az eredményt arra, hogy a további működés
kiindulópontjává váljon.

2. Nem az időrend a probléma

A változatok sorozata hasznos:

S0 → S1 → S2 → ...

A leírás akkor elégtelen, ha nem őrzi meg a megváltozott viszonyokat, az
átmeneti utakat, a bizonyítékokat és azokat a visszahatásokat, amelyeken
keresztül az egyik változat befolyásolja a következő létrejöttét.

Az időrendi indexelés önmagában nem jelenti a visszacsatolás hiányát.
Egy rekurzív leírás képes visszacsatolást ábrázolni, ha az állapot és az
átmenet meghatározása megőrzi a releváns függőségeket. A kifogás itt a
kizárólag állapotokat megőrző leírásra vonatkozik, nem az időrendre vagy
a rekurzív jelölésre.

A releváns tárgy:

azonosított kiinduló állapot és környezet
→ megváltozott viszony és bizonyítékkal kötött út
→ azonosított eredményállapot és környezet
→ a további átmenetek megváltozott feltételei

Részletes állapotok összehasonlításából bizonyos eltérések azonosíthatók.
Ebből még nem feltétlenül azonosítható az eltéréseket létrehozó út. [1]

3. Miért nem azonosítják feltétlenül a végállapotok az átmenetet?

Legyen P(S0, S1) a két mért végállapot közötti megengedett utak halmaza,
és M_E az a leképezés, amely csak a végállapotok méréseit őrzi meg. Ha:

p_a != p_b
M_E(p_a) = M_E(p_b) = (S0, S1)

akkor a végállapotrekord nem különbözteti meg a két utat. Egy meghatározott
út megvalósulásának állításához további, az utakat megkülönböztető bizonyíték
szükséges. Ez a Transition Meter feltételes, nem injektív leképezésre épülő
érve; nem állítás arról, hogy minden elképzelhető rendszerben mindig több
út lehetséges. [1]

Három külön kérdés marad:

Mi tér el a megfigyelt állapotok között?
Mely átmeneti út kapcsolja össze őket?
Mi volt ennek az útnak az oksági szerepe egy meghatározott hatásban?

Egy átmeneti rekord önmagában nem igazolja az oksági szükségességet,
elégségességet vagy teljességet. A sorrend és az artifactkötés támogathatja
a rekonstrukciót úgy is, hogy nem old fel minden alternatív magyarázatot. [1]

4. Az önmódosítás még nem bizonyított fejlődés

Ebben a dokumentumban a rekurzív önmódosítás azt jelenti, hogy a rendszer
olyan összetevőket vagy feltételeket módosít, amelyek részt vesznek a
későbbi módosításai előállításában vagy értékelésében. Az „önfejlesztés”
megnevezés ehhez értékelő állítást ad hozzá; nem bizonyítja ezt az állítást.

A következő következtetések eltérő bizonyítékokat igényelnek:

Változás történt.
Ehhez azonosított megfigyelések vagy állapotkülönbségek szükségesek.

Ez az átmenet történt.
Ehhez az állapotokhoz, forrásokhoz, futási környezethez és bizonyítékokhoz
kötött út szükséges.

Ez az átmenet hozzájárult ehhez a hatáshoz.
Ehhez az állításnak megfelelő oksági bizonyíték és a releváns alternatívák
kezelése szükséges.

A jelölt egy meghatározott szempontból javult.
Ehhez azonosított célok, mérések, korlátok és bizonytalanság mellett végzett,
érvényes összehasonlítás szükséges.

A jelölt átléphet egy meghatározott határt.
Ehhez az adott jelöltre és határra vonatkozó policy feltételeinek teljesülése
szükséges.

Körülhatárolt teljesítményjavulás megállapítható a teljes rekurzív folyamat
igazolása nélkül. Fordítva: egy reprodukálható átmeneti rekord önmagában
nem bizonyít teljesítményjavulást.

A fejlődésnek nem kell egyetlen univerzális pontszámot jelentenie.
Jelentése függhet meghatározott feladattól, összehasonlítási sokaságtól,
erőforrásfeltételtől, visszaesést kizáró követelménytől és elfogadási
szabálytól. Ezeknek a feltételeknek azonosíthatóknak kell maradniuk.

5. Az értékelési feltételek maguk is átmeneti tárgyak

Nemcsak az értékelt rendszer változhat. A rekurzív folyamat a tesztjeit,
célját, adatkiválasztását, pontozási szabályát, policyját vagy verifierét
is módosíthatja.

A megváltozott értékelési feltétel nem léphet észrevétlenül annak a
feltételnek a helyére, amelyre a fejlődési állítás vonatkozik.

Gondolatkísérlet: a jelölt 100 tesztből 60-at old meg. Ha a viselkedése
megváltoztatása nélkül eltávolítunk 25 sikertelen tesztet, az eredmény
75-ből 60 lesz: 60% helyett 80%. Az új arány más tesztsokaságot ír le.
Nem igazolja a teljesítmény javulását az eredeti sokaságon.

Megalapozott összehasonlításhoz mindkét értékelési környezet azonosságát
meg kell őrizni. Eltérés esetén vagy igazolni kell az összehasonlításuk
érvényességét, vagy jelezni kell, hogy az eredmények közvetlenül nem
összehasonlíthatók.

A cél, a policy vagy a verifier megváltoztatása legitim fejlesztési tárgy.
Elfogadásukhoz külön azonosított átmenet szükséges, egy már alkalmazandó
változtatási szabály alapján. A javasolt helyettesítő pusztán a saját
sikerjelzése miatt nem válhat saját engedélyezésének egyetlen alapjává.

Ez nem verifierek végtelen egymásra építését igényli. Meghatározott,
körülhatárolt elfogadási alapot és annak módosítása fölötti világos
jogosultságot igényel. A PULSEmech működési modellje megőrzi a policy és
a következmények emberi kontrollját, miközben a mechanikai bizonyítékot
géppel kezelhetővé teszi. [2]

6. Mit kell megőriznie az iterációhoz kötött rekordnak?

A következők az alkalmazás architekturális követelményei, nem új,
megvalósított séma és nem korlátlan megfigyelhetőségre vonatkozó állítások.

AZONOSSÁG ÉS HATÓKÖR.
Kötni kell a kiinduló és jelölt állapotot, a forrásrevíziót, az adott
futást és — ahol releváns — annak próbálkozását, a bemeneteket, az
előállított artifactokat és az állítás határát. Meg kell őrizni a korábbi
iterációktól való függőségeket, amennyiben az állítás szempontjából
relevánsak.

ÚT ÉS IDŐ.
Azonosítani kell a megváltozott viszonyokat és a megfigyelt vagy
rekonstruált utat. Meg kell őrizni az elemek sorrendjét, a releváns
határokat, valamint az eseményidő, megfigyelési idő, ellenőrzési idő és
engedélyezési idő különbségét. Ahol releváns, rögzíteni kell a pontosságot
vagy bizonytalanságot; egyetlen összesítő időbélyeg nem helyettesítheti a
szükséges elemenkénti kötéseket. Ezek az időbeli megkülönböztetések a
Transition Meterből következnek. [1]

ÉRTÉKELÉSI ÉS DÖNTÉSI ALAP.
Kötni kell az összehasonlítás alapját, az értékelési eljárást, a feltételeket,
a deklarált policyt, a tényleges követelményeket és az alkalmazott verifier
pontos változatát. Azonosítani kell, milyen döntést támaszthatnak alá ezek
a rekordok — ha egyáltalán felhasználhatók döntéshez.

A BIZONYÍTÉK OSZTÁLYOZÁSA.
Elkülöníthetően kell megőrizni a megfigyelt tényeket, a reprodukálhatóan
levezetett kapcsolatokat, a feltételezéseket és a feloldatlan információt.
A levezetett eredményhez megmaradnak a bemenetek és a levezetési eljárás
azonosítói. Az elérhetetlen bizonyíték elérhetetlen marad; nem válik ténnyé
attól, hogy kényelmesebb lenne egy teljesnek látszó rekord.

KÖRÜLHATÁROLT KÖVETKEZTETÉSEK.
Meg kell őrizni a releváns alternatív utakat, megfigyelési hiányokat és
nyitott oksági kérdéseket. Az egyik állításhoz elegendő bizonyíték másikhoz
elégtelen lehet. A nem igazolt kötelező feltétel nem tekinthető teljesültnek.
Egy nem kapcsolódó ismeretlen nem blokkol automatikusan minden lehetséges
döntést.

7. A jogosultságnak meg kell előznie az általa szabályozott határátlépést

A megfigyelés, az értékelés és a továbblépés engedélye nem felcserélhető.
Egy kísérlet a telepítési döntés előtt állíthat elő bizonyítékot, miközben
a döntés továbbra is megelőzi az általa szabályozott telepítést.

Rekurzív alkalmazásban a szabályozott határnak kifejezettnek kell lennie.
Lehet a jelölt felvétele az aktív rendszerbe, generált anyag beépítése a
közös memóriába, egy értékelő lecserélése vagy meghatározott külső művelet
engedélyezése. Ezek alkalmazási példák, nem állítások arról, hogy a
PULSEmech ma mindegyik határt megvalósítja.

Egy lehetséges, körülhatárolt elfogadási viszony:

jelölt előállítása és értékelése a már érvényes jogosultságok alatt
→ pontos átmeneti és értékelési bizonyíték
→ ellenőrzés az alkalmazandó döntési alap szerint
→ ALLOW vagy BLOCK a meghatározott elfogadási határ előtt
→ az elfogadott eredmény és megőrzött környezete a későbbi munka bemenete

A jelölt előállítása maga is járhat hatásokkal. Ezek nem nyilváníthatók
ártalmatlannak pusztán azért, mert a későbbi elfogadás kapuzott. Az
alkalmazásnak azonosítania kell, mely hatások megengedettek a kísérletezés
során, és melyek igényelnek korábbi érvényesítési határt.

Egy később elkészült bizonyítékcsomag nem engedélyezhet visszamenőleg egy
már megtörtént határátlépést. A release-döntés nem jelent kontrollt minden
korábbi tanítási, futási vagy környezeti kölcsönhatás fölött.

8. Az iterációk összekapcsolásakor nem veszhetnek el a feltételeik

Egy érvényes helyi döntés meghatározott jelöltre, bizonyítékhalmazra,
policyra, verifierre és határra vonatkozik. Nem általános engedély minden
későbbi változatra.

Amikor az elfogadott eredmény egy későbbi iteráció bemenetévé válik, a
következő rekordnak meg kell őriznie a releváns előd azonosságát és a
környezet változásait. Korábbi bizonyíték csak akkor használható újra,
ha az új állításra való alkalmazhatósága megalapozott; egy korábbi
sikerjelzés önmagában ehhez nem elegendő.

Még a helyileg megalapozott döntések lánca sem bizonyít automatikusan
korlátlan fejlődést, globális biztonságot vagy konvergenciát. A több
iterációra kiterjedő állításokhoz saját, meghatározott összehasonlítási
feltételek és az összekapcsolás érvényességét igazoló érvelés szükséges.
Az átmenetkötés célja az ehhez szükséges bizonyíték megőrzése, nem pedig
az állítások előzetes igaznak nyilvánítása.

9. Kapcsolat a PULSEmech jelenlegi mechanikájával

A vizsgált Technical Overview az artifacthoz kötött AI-release-átmeneteket
jelöli meg a jelenlegi konkrét engedélyezési tartományként. A release-viszony
leírása: [2]

R = ⟨S, E, A, P, G, V, F, D⟩

S: az alany és a futás pontos azonossága
E: rögzített release-bizonyíték
A: pontos artifact- és hordozóazonosságok
P: a deklarált release-policy azonossága
G: a workflowban ténylegesen érvényes, materializált kötelező kapuállapot
V: a verifier azonossága és determinisztikus újraellenőrzési állapota
F: a végső kapuállapot hordozója
D: az elsődleges CI végső ALLOW vagy BLOCK érvényesítési eredménye

A döntést hordozó út az adott futás rögzített bizonyítékát, a pontos
kötéseket, a policyból levezetett követelményeket, a verifier újrafuttatását
és a végső kapuállapotot kapcsolja a telepítés előtti, szigorú fail-closed
érvényesítéshez. Determinizmusa ezekhez a pontosan kötött bemenetekhez
viszonyított. Nem jelenti a mögöttes AI-viselkedés vagy egy teljes jövőbeli
tanítási folyamat determinizmusát. [2]

A Transition Meter adja az állapotmérés, viszonyváltozás, átmeneti út,
bizonyítékrekord és oksági állítás tágabb megkülönböztetését. Az általános
tartománykiterjesztést tervezési szintként jelöli, nem kész, univerzális
megvalósításként. [1]

Ez a dokumentum ebből a két alapból vezeti le a rekurzív alkalmazást.
Nem ad hozzá kaput, futásidejű elfogó mechanizmust, policyt, verifiert vagy
működési jogosultságot. Nem váltja fel egyik kanonikus forrást sem, és nem
állítja egy általános rekurzív önfejlesztési ciklus demonstrálását.

10. Következtetés

A rekurzív önfejlesztés nem igazolható megfelelően kedvező végállapoti
jelentések sorozatával, ha az állítás attól is függ, hogyan jöttek létre a
változások, hogyan értékelték őket, és hogyan váltak a további működés
részévé.

A szükséges kapcsolat:

azonosított változás
+ bizonyítékkal alátámasztott átmenet
+ érvényes értékelés azonosított feltételek mellett
+ megalapozott jogosultság a szabályozott határnál

E kötés hiányában az egymást követő állapotok önmagukban nem igazolják,
hogy a visszacsatolt önmódosítás bizonyítékkal megalapozott fejlődési
folyamat, nem pedig változások egymásutánja. Az érvelés bizonyítékkövetelményt
állapít meg; nem igazolja egyetlen megnevezett megvalósítás kizárólagosságát.

A PULSEmech ezt a kapcsolatot kifejezett mechanikai tárggyá teszi a deklarált
hatókörén belül. A rekurzív önfejlesztésben az a jelentősége, hogy minden
állított lépésnél megkérdezhető: mi változott, mi támasztja alá az
összehasonlítást, mi maradt feloldatlan, és mi jogosítja fel az eredményt
a későbbi munka befolyásolására.

A következő változat nem válhat saját igazolásává. Az átmenetnek, az
értékelési alapnak és a továbblépési jogosultságnak bizonyítékhoz kötöttnek
kell maradnia, miközben a változás már alakíthatja a következő iteráció
feltételeit.

11. Forrásalap és dokumentumhatár

A forrásellenőrzés a repository 2026. szeptember 6-án vizsgált
30ae2d66179ee1903b4acbe99b1b4b0e3f0a673f commitjához kötött.
A hivatkozott architekturális leírások csak olvasással végzett vizsgálata,
nem új tesztfuttatás, CI-eredmény vagy megvalósítási tanúsítás. A vizsgált
forráscommit nem ennek a dokumentumnak a majdani commitazonossága.

[1] PULSEMECH_TRANSITION_METER.md, különösen a 2., 4–6. és 9. fejezet:
átmeneti azonosság, a végállapotok elégtelensége, állításfüggő bizonyíték
és időbeli kötés.

[2] PULSEMECH_TECHNICAL_OVERVIEW.md, 1., 2. és 2A. fejezet:
a jelenlegi release-authority viszony, a telepítés előtti végső döntés,
a determinisztikus újraellenőrzés hatóköre, valamint az AI-natív működés
az emberi policy- és következménykontroll megőrzésével.

A kattintható, pontos revízióhoz kötött források az angol főszöveg
11. fejezetében találhatók.

A dokumentum követelményei és példái a rekurzív alkalmazásra vonatkozó
architekturális levezetések. Nem új, megfigyelt repository-eredmények.
A dokumentum besorolása a docs/INDEX.md szerint: Foundational architecture.
```
