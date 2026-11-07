#!/usr/bin/env python3
"""Measure bounded language relations and publish diagnostic artifacts."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.language_relation_v0.comparator import measure_bundle
from tools.language_relation_v0.io import InputError, canonical_bytes


def _publish(directory: Path, bundle: dict) -> None:
    """Own a new directory before writing; never overwrite an existing path."""
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise InputError("output directory already exists; choose a fresh path") from exc
    descriptor = None
    created = {}
    identity = directory.stat(follow_symlinks=False)
    try:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (identity.st_dev, identity.st_ino):
            raise OSError("output directory changed before publication")
        for name, value in (("verification.json", bundle["verification"]),
                            ("measurement.json", bundle["measurement"])):
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=descriptor)
            info = os.fstat(fd)
            created[name] = (info.st_dev, info.st_ino)
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical_bytes(value))
                stream.flush()
                os.fsync(stream.fileno())
        os.fsync(descriptor)
    except BaseException:
        if descriptor is not None:
            for name, expected in created.items():
                try:
                    info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) == expected:
                        os.unlink(name, dir_fd=descriptor)
                except OSError:
                    pass
        try:
            current = directory.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                directory.rmdir()
        except OSError:
            pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--trust-config", type=Path)
    parser.add_argument("--comparison-trust-config", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = args.output_dir.absolute()
        if output.exists() or output.is_symlink():
            raise InputError("output directory already exists; choose a fresh path")
        bundle = measure_bundle(args.input, package_root=args.package_root,
                                trust_config=args.trust_config,
                                comparison_trust_config=args.comparison_trust_config)
        _publish(output, bundle)
        print(f"Wrote measurement and verification artifacts: {output}")
        print("Completed diagnostics; inspect each target's state, scope and unresolved obligations.")
        print("authority_effect=none; release_authority_activation=false")
        return 0
    except InputError as exc:
        print(f"Invalid input/configuration: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"Measurement execution failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
