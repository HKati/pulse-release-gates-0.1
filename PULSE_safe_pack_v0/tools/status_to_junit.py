#!/usr/bin/env python3
import json, os, xml.etree.ElementTree as ET
from datetime import datetime

STATUS = os.environ.get("PULSE_STATUS", "status.json")
OUT = os.environ.get("PULSE_JUNIT", "reports/junit.xml")

with open(STATUS, "r", encoding="utf-8") as f:
    s = json.load(f)

tests = []
def row(k, v, kind):
    name = f"{k} - {kind}"
    passed = bool(v.get("passed", False))
    msg = json.dumps(v, ensure_ascii=False)
    tests.append((name, passed, msg))

for k, v in (s.get("invariants") or {}).items():
    row(k, v, "invariant")
for k, v in (s.get("quality") or {}).items():
    row(k, v, "quality")

ts = ET.Element("testsuite", {
    "name": "PULSE Gates",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "tests": str(len(tests)),
    "failures": str(sum(0 if p else 1 for _, p, _ in tests))
})
for name, passed, msg in tests:
    tc = ET.SubElement(ts, "testcase", {"classname": "pulse", "name": name})
    if not passed:
        fail = ET.SubElement(tc, "failure", {"message": "FAIL"})
        fail.text = msg

os.makedirs(os.path.dirname(OUT), exist_ok=True)
ET.ElementTree(ts).write(OUT, encoding="utf-8", xml_declaration=True)
print(f"Wrote {OUT}")
