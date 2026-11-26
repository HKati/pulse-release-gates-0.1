#!/usr/bin/env python3
"""Verify LRM source binding and mapping; this CLI makes no release decision."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.language_relation_v0.io import InputError, canonical_bytes
from tools.language_relation_v0.verifier import verify_input


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--trust-config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    temporary = None
    try:
        output = args.output.absolute()
        if output.exists() or output.is_symlink():
            raise InputError("output already exists; choose a fresh artifact path")
        report = verify_input(args.input, package_root=args.package_root, trust_config=args.trust_config)
        # Publish complete bytes without overwriting an input/evidence file,
        # including one created concurrently after the preflight check.
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".lrm02-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(canonical_bytes(report))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise InputError("output already exists; choose a fresh artifact path") from exc
        temporary.unlink()
        temporary = None
        print(f"Wrote verification artifact: {output}")
        print("Completed diagnostics; authority_effect=none. Check results and both basis records.")
        return 0
    except InputError as exc:
        print(f"Invalid input/configuration: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"Verification execution failed: {exc}", file=sys.stderr)
        return 3
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
