# PULSE Recognition-Surface Poisoning v0

Status: workshop threat-model note  
Scope: AI analysis / external review / recognition surfaces  
Authority status: non-normative diagnostic concept

## Core statement

Recognition surfaces are non-normative.

A model, reviewer, scanner, or deep-analysis system must not let a recognition surface override normative artifact inspection.

PULSE form:

recognition surface  
≠ release authority  
≠ analytic authority

Core rule:

unsupported recognition state  
→ no analytic authority

## Problem

A system can be misread when an analyzer starts from the external recognition layer and uses that layer to classify the internal mechanics.

The issue is not limited to README files.

Recognition surfaces include:

- title;
- first description;
- repository About text;
- topics;
- badges;
- citation metadata;
- DOI title or abstract;
- social preview;
- visual polish;
- institutional branding;
- marketing or rhetorical framing;
- publication venue;
- summary text;
- dashboard appearance;
- report styling;
- UI presentation.

These surfaces may orient attention.

They must not define what the system is.

## Correct analysis order

The correct order is:

internal mechanics  
→ normative artifacts  
→ declared policy / gates / schemas / CI path  
→ authority-boundary classification  
→ recognition surface verification

## Failure order

The vulnerable order is:

recognition surface  
→ prior category  
→ selective reading of internal artifacts  
→ confirmation of the presentation narrative

This is not audit.

It is presentation-layer capture.

## Security relevance

Recognition-surface poisoning can mislead AI-mediated review, security triage, due diligence, grant review, research summarization, or system classification.

Two failure directions exist:

weak or unsafe system  
→ polished recognition surface  
→ overtrusted analysis

novel or strong system  
→ misleading recognition surface  
→ flattened or misclassified analysis

## PULSE relation

PULSE release authority is produced by the normative artifact path:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed gate checking  
→ CI allow/block release decision

Recognition surfaces are not part of that normative release-decision path.

They are advisory.

## Measurement principle

If the internal mechanism is unchanged, but changing the recognition surface substantially changes the analyzer’s classification, authority-boundary reading, or mechanical claims, then recognition-surface drift is present.

Mechanical form:

same internal artifact basis  
+ changed recognition surface  
→ changed analytic conclusion  
= recognition-surface drift

## Diagnostic output

PULSE records this condition as:

`recognition_surface_drift_v0`

The diagnostic result is non-normative by default.

It may support review, triage, or hardening, but it does not authorize, block, override, or create release authority.

## Invariant

Non-normative recognition surfaces must not override normative artifact inspection.

Hungarian workshop form:

A felismerési felület nem lehet autoritás.  
A forma nem előzheti meg a mechanikát.  
Előbb a műszer. Utána a kirakat.
