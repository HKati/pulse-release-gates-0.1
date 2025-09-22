#!/usr/bin/env python3
import argparse, json, os, textwrap
ap = argparse.ArgumentParser()
ap.add_argument("--status", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

data = json.load(open(a.status, encoding="utf-8"))
g = data.get("gates") or {}
m = data.get("metrics") or {}
all_pass = all(bool(v) for v in g.values())

lines = [
  "# PULSE — Quality Ledger",
  f"- **Decision:** {'PASS' if all_pass else 'FAIL'}",
  f"- **RDSI:** {m.get('RDSI', 0.0):.2f}",
  "",
  "## Gates",
]
for k,v in sorted(g.items()):
    lines.append(f"- `{k}` — **{'PASS' if v else 'FAIL'}**")

open(a.out, "w", encoding="utf-8").write("\n".join(lines))
print("Wrote", a.out)
