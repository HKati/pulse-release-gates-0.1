# PULSE Field-Instrument Principle v0

Status: workshop principle  
Scope: PULSE architecture language / development orientation / authority-role interpretation  
Authority status: non-normative explanatory document

## Core statement

PULSE is not a layered tool.

PULSE is a field instrument.

It does not consist of a core box with external layers stacked around it.

It operates as an evidence-decision field in which normative, diagnostic, audit, publication, recognition, and analysis surfaces have different roles.

Release authority materializes only along the declared normative path.

## Normative materialization path

The normative release-authority path remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ CI allow/block release decision

This path is not “the core” because everything else is outside it.

It is the authority-materialization path inside the field.

## Field interpretation

PULSE should be read as:

Every PULSE element belongs to the field by its role and authority status, not by architectural distance.
There is no center-and-margin hierarchy here.

There is a field, and each element matters by role, authority status, and relation to the normative materialization path.

field  
→ role-bearing points  
→ relationships  
→ evidence tensions  
→ diagnostic signals  
→ recognition surfaces  
→ audit / reconstruction surfaces  
→ normative materialization path

Not as:

core  
→ layers  
→ dashboard  
→ audit  
→ diagnostics  
→ presentation

The layered interpretation is a classical architecture metaphor. It is useful only in limited technical contexts and can misread PULSE as a stacked tool.

The field-instrument interpretation preserves the authority roles of each surface.

## Role-bearing field points

Different PULSE surfaces have different roles.

### Normative authority path

These surfaces participate in release-authority materialization:

- recorded release evidence;
- `status.json`;
- declared gate policy;
- materialized required gate set;
- strict gate checking;
- CI allow/block outcome.

### Diagnostic surfaces

These surfaces may detect, measure, explain, or warn:

- recognition-surface drift diagnostics;
- PULSE-PD;
- EPF;
- paradox field;
- topology;
- G-field;
- hazard signals;
- shadow overlays.

Diagnostic surfaces do not create release authority unless explicitly routed through declared policy and enforced as required gates.

### Audit and reconstruction surfaces

These surfaces preserve or reconstruct evidence and decisions:

- RA1 verifier;
- audit bundle;
- release authority manifest;
- operator handoff report;
- package digests;
- publication snapshot.

They may verify consistency, reconstruct a decision trail, or expose drift.

They do not create a second release-decision path.

### Reader and publication surfaces

These surfaces help humans or external systems read the field:

- Quality Ledger;
- Pages;
- badges;
- DOI records;
- citation metadata;
- README;
- repository About;
- public summaries.

They are recognition and publication surfaces, not release-authority engines.

## Recognition rule

Every recognition claim requires mechanical evidence.

A recognition surface may say what the system is.

The field must prove it.

A title, summary, badge, DOI description, topic list, visual polish, or public description may orient attention, but it must not define the system’s authority role.

Recognition surfaces are not authority.

Form must not precede mechanics.

Mechanism first; presentation second.

## Development rule

When adding or modifying a PULSE component, classify its role before describing its value.

Use these questions:

1. Does it participate in the normative release-authority path?
2. Does it produce diagnostic evidence?
3. Does it reconstruct or audit an already materialized decision?
4. Does it publish or render an existing artifact?
5. Does it create a recognition surface?
6. Does it require policy promotion before it can affect release authority?

If the answer is unclear, the component is non-normative until explicitly routed through declared policy and enforced as a required gate.

## Language guard

Avoid describing PULSE as a stack of layers when describing its architecture.

Prefer:

- field instrument;
- evidence-decision field;
- role-bearing surface;
- diagnostic surface;
- recognition surface;
- audit surface;
- publication surface;
- authority-materialization path;
- normative path.

Use “layer” only when referring to an existing technical label or legacy document name.

The preferred architectural statement is:

PULSE is a field instrument: it operates in an evidence-decision field where normative, diagnostic, audit, publication, recognition, and analysis surfaces have different roles. Release authority materializes only along the declared normative path.

## Relation to recognition-surface poisoning

Recognition-surface poisoning occurs when a non-normative recognition surface changes an analyzer’s classification of the internal mechanics.

The field-instrument principle reduces this risk by requiring mechanism-first inspection.

The correct analysis order is:

internal mechanics  
→ normative artifacts  
→ authority-role classification  
→ recognition surface verification

The incorrect order is:

recognition surface  
→ prior category  
→ selective reading of internal artifacts  
→ confirmation of presentation narrative

## Relation to pre-materialization mechanics

PULSE pre-materialization mechanics prevents unsupported authority from materializing.

The field-instrument principle applies the same discipline to architecture interpretation.

Unsupported evidence state  
→ no release authority

Unsupported recognition state  
→ no analytic authority

## Summary

PULSE is not a layered tool.

PULSE is a field instrument.

The decision does not come from a box.

The decision materializes along the normative path of the evidence-decision field.
