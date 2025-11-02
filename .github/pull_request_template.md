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

## Notes
- Follow-ups:
- Risks / mitigations:

## PULSE checklist (governance)
- [ ] PULSE CI is green on this PR
- [ ] Quality Ledger link (if enabled)
- [ ] Badges updated (PASS / RDSI / Q‑Ledger)
