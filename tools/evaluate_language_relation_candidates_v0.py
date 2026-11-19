#!/usr/bin/env python3
"""Export source-only LRM requests or evaluate preserved candidate responses."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.language_relation_v0.candidates import evaluate_candidates, request_bytes
from tools.language_relation_v0.io import (InputError, canonical_bytes,
                                         relative_path, strict_json)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _publish(directory: Path, payloads: dict[str, bytes]) -> None:
    """Publish into a fresh owned directory; roll back only files we created.

    All names are prevalidated before creating the destination. Directory
    descriptors keep package-controlled paths from following symlinks. The
    evaluation report is written after its referenced payloads.
    """
    entries = []
    for locator, data in payloads.items():
        parts = relative_path(locator)
        if len(parts) > 2 or not isinstance(data, bytes):
            raise InputError("unsupported publication payload")
        if locator.endswith(".json"):
            strict_json(data)
        entries.append((parts, data))
    if not entries:
        raise InputError("no publication payloads")
    files = {parts for parts, _ in entries}
    parents = {parts[:-1] for parts in files if len(parts) == 2}
    if files & parents:
        raise InputError("publication file/directory collision")
    entries.sort(key=lambda item: (item[0] == ("evaluation.json",), item[0]))
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise InputError("output directory already exists; choose a fresh path") from exc

    root_identity = _identity(directory.stat(follow_symlinks=False))
    descriptors: dict[tuple[str, ...], int] = {}
    owned_files: list[tuple[tuple[str, ...], str, tuple[int, int]]] = []
    owned_directories: list[tuple[str, tuple[int, int]]] = []
    try:
        root_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors[()] = root_fd
        if _identity(os.fstat(root_fd)) != root_identity:
            raise OSError("output directory changed before publication")
        for parent in sorted(parents):
            name = parent[0]
            os.mkdir(name, mode=0o700, dir_fd=root_fd)
            identity = _identity(os.stat(name, dir_fd=root_fd, follow_symlinks=False))
            owned_directories.append((name, identity))
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                         dir_fd=root_fd)
            descriptors[parent] = fd
            if _identity(os.fstat(fd)) != identity:
                raise OSError("output subdirectory changed before publication")
        for parts, data in entries:
            parent, name = parts[:-1], parts[-1]
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=descriptors[parent])
            owned_files.append((parent, name, _identity(os.fstat(fd))))
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        for parent, name, identity in owned_files:
            current = os.stat(name, dir_fd=descriptors[parent], follow_symlinks=False)
            if _identity(current) != identity:
                raise OSError("output file changed during publication")
        for name, identity in owned_directories:
            if _identity(os.stat(name, dir_fd=root_fd, follow_symlinks=False)) != identity:
                raise OSError("output subdirectory changed during publication")
        for parts in sorted(descriptors, key=len, reverse=True):
            os.fsync(descriptors[parts])
        if _identity(directory.stat(follow_symlinks=False)) != root_identity:
            raise OSError("output directory changed during publication")
    except BaseException:
        for parent, name, identity in reversed(owned_files):
            try:
                current = os.stat(name, dir_fd=descriptors[parent], follow_symlinks=False)
                if _identity(current) == identity:
                    os.unlink(name, dir_fd=descriptors[parent])
            except OSError:
                pass
        if () in descriptors:
            for name, identity in reversed(owned_directories):
                try:
                    current = os.stat(name, dir_fd=descriptors[()], follow_symlinks=False)
                    if _identity(current) == identity:
                        os.rmdir(name, dir_fd=descriptors[()])
                except OSError:
                    pass
        try:
            if _identity(directory.stat(follow_symlinks=False)) == root_identity:
                directory.rmdir()
        except OSError:
            pass
        raise
    finally:
        for fd in descriptors.values():
            os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("requests", help="Export the fixed source-only request set.")
    export.add_argument("--output-dir", type=Path, required=True)
    evaluate = commands.add_parser("evaluate", help="Check preserved responses; make no model call.")
    evaluate.add_argument("--records", type=Path, required=True)
    evaluate.add_argument("--package-root", type=Path)
    evaluate.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = args.output_dir.absolute()
        if output.exists() or output.is_symlink():
            raise InputError("output directory already exists; choose a fresh path")
        if args.command == "requests":
            payloads = {"requests.json": request_bytes()}
        else:
            bundle = evaluate_candidates(args.records, package_root=args.package_root)
            payloads = dict(bundle["payloads"])
            if "evaluation.json" in payloads:
                raise InputError("evaluation payload name collision")
            payloads["evaluation.json"] = canonical_bytes(bundle["evaluation"])
        _publish(output, payloads)
        print(f"Wrote {len(payloads)} preserved files: {output}")
        if args.command == "evaluate":
            print("Completed fixed-set diagnostics; inspect all case and question records.")
            print("Mapping checks do not verify target selection or establish model accuracy.")
        print("authority_effect=none; release_authority_activation=false")
        return 0
    except InputError as exc:
        print(f"Invalid input/configuration: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"Candidate evaluation/publication failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
