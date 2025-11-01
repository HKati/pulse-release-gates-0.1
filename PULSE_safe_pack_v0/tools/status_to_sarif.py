#!/usr/bin/env python3
import json, os, time

STATUS = os.environ.get("PULSE_STATUS", "status.json")
OUT = os.environ.get("PULSE_SARIF", "reports/sarif.json")

with open(STATUS, "r", encoding="utf-8") as f:
    s = json.load(f)

results, rules, seen = [], [], set()

def push(rule_id, level, payload):
    global results, rules, seen
    results.append({
        "ruleId": rule_id,
        "level": level,
        "message": {"text": json.dumps(payload, ensure_ascii=False)}
    })
    if rule_id not in seen:
        rules.append({
            "id": rule_id,
            "shortDescription": {"text": rule_id},
            "defaultConfiguration": {"level": level}
        })
        seen.add(rule_id)

for k, v in (s.get("invariants") or {}).items():
    push(k, "error" if not v.get("passed", False) else "none", v)

for k, v in (s.get("quality") or {}).items():
    push(k, "warning" if not v.get("passed", False) else "none", v)

sarif = {
  "version": "2.1.0",
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "runs": [{
    "tool": { "driver": { "name": "PULSE", "rules": rules }},
    "results": results,
    "invocations": [{
      "executionSuccessful": True,
      "startTimeUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }]
  }]
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(sarif, f, ensure_ascii=False, indent=2)
print(f"Wrote {OUT}")
