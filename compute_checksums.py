#!/usr/bin/env python3
import argparse, hashlib, os, pathlib, sys

def sha256sum(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_dir(dirpath: pathlib.Path, recursive: bool) -> int:
    base = pathlib.Path(dirpath)
    if not base.exists():
        print(f"# WARN: {base} does not exist – skipping", file=sys.stderr)
        return 0

    files = []
    if recursive:
        for dp, _, fn in os.walk(base):
            for n in fn:
                files.append(pathlib.Path(dp) / n)
    else:
        for p in base.iterdir():
            if p.is_file():
                files.append(p)

    count = 0
    for f in sorted(files):
        try:
            print(f"{sha256sum(f)}  {f.relative_to(base.parent)}")
            count += 1
        except Exception as e:
            print(f"# ERROR on {f}: {e}", file=sys.stderr)
    return count

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("directories", nargs="*", default=["dist"],
                    help="One or more directories to hash (default: dist)")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="Recurse into subdirectories")
    args = ap.parse_args()

    total = 0
    for d in args.directories:
        total += hash_dir(d, args.recursive)

    # soft‑fail: ne törje el a CI-t, ha épp nincs mit hashelni
    sys.exit(0)
