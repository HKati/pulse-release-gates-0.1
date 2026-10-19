# INDEX.md — pontos beillesztési utasítás (NEM REPOSITORY FÁJL)

Ezt a fájlt **nem kell feltölteni**. Csak a `docs/INDEX.md` meglévő
`### External challenge companions` szakaszában végrehajtandó, kizárólag
QRH003-hivatkozásokat érintő módosítás leírása.

## 1. Meglévő QRH003-sor frissítése

A `PULSEMECH_QRH003_AUDIT_REFERENCE_v0.md` hivatkozással kezdődő,
még `v0.1.2`-t és `185` tesztet említő sort cseréld a következőre:

```markdown
- [PULSEMECH_QRH003_AUDIT_REFERENCE_v0.md](PULSEMECH_QRH003_AUDIT_REFERENCE_v0.md) — **Current isolated audit demonstrator, v0.1.3.** Source-bound QRH003 audit, 220 recorded local tests, historical `BLOCK` / replay `MATCH`; native proof capture `NOT_IMPLEMENTED`, no production certificate.
```

## 2. Új, kizárólag tervezési linkek

Közvetlenül a QRH003-sor után illeszd be:

```markdown
- [QRH003 knowledge-continuity overview](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_OVERVIEW_v0.md) — **Pending operational target / design-only.** English canonical overview of one scoped Math 003 claim, retained `BLOCK/MATCH`, nonpromotable gaps, planned handoff and M1–M7.
- [QRH003 knowledge-continuity technical plan](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_TECHNICAL_PLAN_v0.md) — **Pending operational target / design-only.** Claim-to-evidence continuity, typed relation links, existing Transition Meter axes; no new proof claim.
- [QRH003 knowledge-continuity experiment plan](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_EXPERIMENT_PLAN_v0.md) — **Pending operational target / design-only.** Twenty planned K01–K20 controls and independent handoff comparison; all new trials `NOT_RUN`.
- [QRH003 knowledge-continuity implementation plan](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_IMPLEMENTATION_PLAN_v0.md) — **Pending operational target / design-only.** M1–M7 dependency sequence; M1 static inventory first.
```

**Fontos:** a `docs/INDEX.md` teljes fájlját nem tesszük az előkészített
ZIP-be, hogy egy közben előrelépett `main` munkáját ne írjuk felül.
Kizárólag a célzott öt sor kerüljön módosításra, a friss HEAD
ellenőrzése mellett.
