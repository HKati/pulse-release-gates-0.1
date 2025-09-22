#!/usr/bin/env python3
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--status", required=True)
ap.add_argument("--assets", required=False, default="badges")
ap.add_argument("--out", required=True)
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)

def svg_badge(label, value, color):
    label_w = 70; status_w = max(86, 8*len(value)); h=20; w=label_w+status_w
    return ff"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset=".1" stop-opacity=".1"/><stop offset=".9" stop-opacity=".3"/><stop offset="1" stop-opacity=".5"/></linearGradient>
  <mask id="m"><rect width="{w}" height="{h}" rx="3" fill="#fff"/></mask>
  <g mask="url(#m)"><rect width="{label_w}" height="{h}" fill="#555"/><rect x="{label_w}" width="{status_w}" height="{h}" fill="{color}"/><rect width="{w}" height="{h}" fill="url(#s)"/></g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_w/2}" y="14">{label}</text>
    <text x="{label_w + status_w/2}" y="14">{value}</text>
  </g></svg>"""

data = json.load(open(a.status, encoding="utf-8"))
g = data.get("gates") or {}
m = data.get("metrics") or {}
all_pass = all(bool(v) for v in g.values())

pulse_value = "PASS" if all_pass else "FAIL"
pulse_color = "#2da44e" if all_pass else "#d73a49"

rdsi = m.get("RDSI", 0.0)
rdsi_value = f"{rdsi:.2f}"
rdsi_color = "#2da44e" if rdsi >= 0.80 else "#fb8c00"

ql_value = "ALL PASS" if all_pass else "CHECK"
ql_color = "#2da44e" if all_pass else "#fb8c00"

open(os.path.join(a.out, "pulse_status.svg"), "w", encoding="utf-8").write(svg_badge("PULSE", pulse_value, pulse_color))
open(os.path.join(a.out, "rdsi.svg"), "w", encoding="utf-8").write(svg_badge("RDSI", rdsi_value, rdsi_color))
open(os.path.join(a.out, "q_ledger.svg"), "w", encoding="utf-8").write(svg_badge("Q-Ledger", ql_value, ql_color))

print("Wrote badges to", a.out)
