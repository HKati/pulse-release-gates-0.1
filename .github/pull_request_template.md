<!-- PULSE PR Template v1.0 — keep sections; fill what applies. -->

## Summary
<!-- Short: what changes and why? -->

## What’s included
- [ ] Code
- [ ] Docs
- [ ] CI / workflow
- Paths / files touched:

## CI usage
```yaml
# Minimal snippet — how this change runs in CI
name: PULSE CI (minimal)
on: [push, pull_request]
jobs:
  pulse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: python PULSE_safe_pack_v0/tools/run_all.py
      - uses: actions/upload-artifact@v4
        with:
          name: pulse-report
          path: |
            PULSE_safe_pack_v0/artifacts/**
            reports/*.xml
            reports/*.json
```

## Impact
- Additive / backwards-compatible
- Breaking change — details:
- Performance / SLO impact:
- Security considerations:

What’s included
 Code
 Docs
 CI / workflow

Paths / files touched:

CI usage

# Minimal snippet — how this change runs in CI
name: PULSE CI (minimal)
on: [push, pull_request]
jobs:
  pulse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: python PULSE_safe_pack_v0/tools/run_all.py
      - uses: actions/upload-artifact@v4
        with:
          name: pulse-report
          path: |
            PULSE_safe_pack_v0/artifacts/**
            reports/*.xml
            reports/*.json

Impact
Additive / backwards-compatible

Breaking change — details:

Performance / SLO impact:

Security considerations:

### Security Intake (v0) — dependency / external code (if applicable)
**Intake v0:** PASS | REVIEW | HARD STOP  
**Isolation used (if REVIEW):** yes / no  

**Reasons (1–3 bullets):**
- 
- 
- 

**Checks**
- [ ] No password-protected ZIP / random binary download involved
- [ ] Repo age ≥ 12 months and maintainer history looks real
- [ ] No postinstall/preinstall scripts (or justified + reviewed)
- [ ] No obfuscation / base64 blobs / runtime-downloaded binaries
- [ ] No instructions like “disable Defender/AV”
- [ ] First run done in VM/container (if REVIEW)

> If any HIGH-risk signal appears → mark **HARD STOP** and do not merge.

Notes

Follow-ups:

Risks / mitigations:

PULSE checklist (governance)
 PULSE CI is green on this PR
 Quality Ledger link (if enabled)
 Badges updated (PASS / RDSI / Q-Ledger)


## Notes
- Follow-ups:
- Risks / mitigations:

## PULSE checklist (governance)
- [ ] PULSE CI is green on this PR
- [ ] Quality Ledger link (if enabled)
- [ ] Badges updated (PASS / RDSI / Q‑Ledger)
