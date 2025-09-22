#!/usr/bin/env python3
import argparse, json, sys, os
ap = argparse.ArgumentParser()
ap.add_argument("--status", required=True)
ap.add_argument("--require", nargs="+", required=True)
args = ap.parse_args()

data = json.load(open(args.status, encoding="utf-8"))
g = data.get("gates") or {}

missing = [k for k in args.require if k not in g]
fails = [k for k in args.require if not g.get(k, False)]

if missing:
    print("[X] Missing required gates:", ", ".join(missing))
    sys.exit(2)

if fails:
    print("[X] FAIL gates:", ", ".join(fails))
    sys.exit(1)

print("[OK] All required gates PASS")
