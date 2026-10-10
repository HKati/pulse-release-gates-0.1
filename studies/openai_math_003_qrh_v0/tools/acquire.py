#!/usr/bin/env python3
"""Read-only source acquisition observations for the pinned QRH reference case.

Existing checkouts are never fetched into, checked out, patched, or updated.  The
optional fetch operation writes only previously absent children of the supplied
dependency directory.  Patches are applied only to newly exported Git trees in a
separate, previously absent output directory.  Nothing in this module executes
Lake, Lean, dependency configuration, a build, or a mathematical review.

Outputs are observations.  They do not authenticate themselves and never grant
release authority; the protected collector must bind their bytes to its receipt.
"""
from __future__ import annotations

# Direct scripts cannot establish source binding before their imports.
if __name__ == "__main__":
    import sys as _qrh_sys
    print("QRH003_SOURCE_BOUND_LAUNCH_REQUIRED: use source_bound.py with python -I", file=_qrh_sys.stderr)
    raise SystemExit(2)


import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import threading
import time
from typing import Mapping, Sequence

try:
    from .common import (AuditError, canonical_bytes, exclusive_write,
                         secure_read, sha256_bytes, strict_loads, write_json)
except ImportError:
    from common import (AuditError, canonical_bytes, exclusive_write,
                        secure_read, sha256_bytes, strict_loads, write_json)


UPSTREAM_COMMIT = "adc7f1241b42e322a6451854ab7e4b4c146bf78a"
UPSTREAM_URL = "https://github.com/openai/math.git"
LEAN_SOURCE_COMMIT = "5045d0056413266e57c625dcd7c365b10e377c52"
LEAN_SOURCE_URL = "https://github.com/leanprover/lean4.git"
TOOLCHAIN = "leanprover/lean4:v4.34.1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
PRE_RESOLUTION_PATCHES = (
    "iut", "tate-curves-theta", "genl", "heights", "pi1", "orbicurve-cores",
    "oka", "tempered-fundamental-groups", "elliptic-curves", "formal-schemes", "belyi",
)
POST_UPDATE_PATCHES = (
    "fixed-point-theorems", "PrimeNumberTheoremAnd", "Zeta3Irrational",
    "rellich-kondrachov", "carleson", "StrongPNT", "AbsorptionCutoff", "AINTLIB",
    "ClassFieldTheory", "schoenflies-lean", "SphereEversion", "gromov",
)
CHALLENGES = (
    "QuasiRiemannHypothesis", "DirichletSevenEighths", "HeckeSevenEighths", "SiegelZeros",
)
CRITICAL_PATHS = (
    "README.md", "lean/docs/003.md", "lean/formalization.yaml",
    "lean/lean-toolchain", "lean/lakefile.lean", "lean/lake-manifest.json",
    "preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf",
    "preprints/Uniform-exclusion-of-Landau-Siegel-zeros-October-1-2026/paper.pdf",
    *(f"lean/ComparatorChallenges/{name}.{extension}"
      for name in CHALLENGES for extension in ("lean", "json")),
    "lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean",
    "lean/OAI/NumberTheory/DirichletL/Hecke/Nonvanishing.lean",
    "lean/OAI/NumberTheory/SiegelZeros/Main.lean",
    "lean/OAI/NumberTheory/SiegelZeros/Conclusions/Theorem.lean",
    "lean/OAI/NumberTheory/SiegelZeros/Characters/DirichletRealZeroBoundProof.lean",
)


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise AuditError("QRH003_PATH_INVALID", repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise AuditError("QRH003_PATH_INVALID", value)
    return path.as_posix()


def _reason(code: str, detail: str = "", **extra) -> dict:
    return {"code": code, "detail": str(detail), **extra}


def _git_env() -> dict:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "LD_", "DYLD_"))}
    # Read-only observations must not perform a promisor/lazy network fetch or
    # trust replacement objects, optional index writes, or interactive prompts.
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    return env


def _command(argv: Sequence[str], *, cwd: Path | None = None,
             timeout: float = 120, keep_stdout: bool = True,
             extra_env: Mapping[str, str] | None = None) -> tuple[dict, bytes]:
    start = time.monotonic()
    record = {"argv": list(argv), "cwd": str(cwd) if cwd else None,
              "timeout_seconds": timeout, "exit_code": None, "status": "NOT_RUN",
              "environment_policy": "drop inherited GIT_*, LD_*, DYLD_*; add fixed noninteractive Git settings"}
    stdout = b""
    env = _git_env()
    if extra_env:
        env.update(extra_env)
        record["declared_environment_overrides"] = dict(extra_env)
    try:
        result = subprocess.run(list(argv), cwd=cwd, env=env, capture_output=True,
                                check=False, timeout=timeout)
        stdout = result.stdout
        record.update(exit_code=result.returncode,
                      status="SUCCESS" if result.returncode == 0 else "FAILED",
                      stderr=result.stderr.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        record.update(status="TIMEOUT", stderr=(exc.stderr or b"").decode("utf-8", "replace"))
    except OSError as exc:
        record.update(status="RETRIEVAL_UNAVAILABLE", stderr=str(exc))
    record.update(stdout_sha256=sha256_bytes(stdout), stdout_bytes=len(stdout),
                  elapsed_seconds=round(time.monotonic() - start, 6))
    if keep_stdout:
        record["stdout"] = stdout.decode("utf-8", "replace")
    return record, stdout


def _git(root: Path, *args: str, timeout: float = 120,
         keep_stdout: bool = True) -> tuple[dict, bytes]:
    # A fresh effective-source directory may live inside the audit repository.
    # Never let git apply discover that parent and silently skip patch paths as
    # being outside its subdirectory prefix.  Existing Git roots still resolve
    # their own .git directory before the ceiling is reached.
    root = Path(root).absolute()
    return _command(["git", "-c", "core.hooksPath=" + os.devnull,
                     "-c", "core.fsmonitor=false", "-c", "core.attributesFile=" + os.devnull,
                     "-C", str(root), *args],
                    timeout=timeout, keep_stdout=keep_stdout,
                    extra_env={"GIT_CEILING_DIRECTORIES": str(root.parent),
                               "GIT_DISCOVERY_ACROSS_FILESYSTEM": "0",
                               "GIT_ALLOW_PROTOCOL": ""})


def read_git_tree(source_root: Path, expected_commit: str) -> tuple[dict, dict]:
    """Return the pinned tree's path -> {mode,type,oid} map, without checkout writes.

    Tree access is explicitly unavailable if objects are absent locally.  This
    routine never falls back to HEAD, a tag, a branch, or an HTTP response.
    """
    root = Path(source_root).absolute()
    if not COMMIT_RE.fullmatch(expected_commit or ""):
        return {}, {"status": "MISMATCH", "reasons": [_reason("QRH003_SOURCE_COMMIT_NOT_PINNED")]}
    step, raw = _git(root, "ls-tree", "-r", "-z", "--full-tree", expected_commit,
                     keep_stdout=False)
    if step["status"] != "SUCCESS":
        return {}, {"status": "RETRIEVAL_UNAVAILABLE", "command": step,
                    "reasons": [_reason("QRH003_GIT_TREE_UNAVAILABLE")]}
    entries = {}
    try:
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            meta, name_bytes = entry.split(b"\t", 1)
            mode, kind, oid = meta.decode("ascii").split(" ")
            name = _safe_relative(name_bytes.decode("utf-8", "strict"))
            if name in entries:
                raise ValueError("duplicate Git path: " + name)
            entries[name] = {"mode": mode, "type": kind, "oid": oid}
    except (ValueError, UnicodeError, AuditError) as exc:
        return {}, {"status": "MISMATCH", "command": step,
                    "reasons": [_reason("QRH003_GIT_TREE_INVALID", str(exc))]}
    return entries, {"status": "VERIFIED", "entry_count": len(entries),
                     "listing_sha256": sha256_bytes(raw), "command": step, "reasons": []}


def verify_git_snapshot(source_root: Path, expected_commit: str,
                        critical_paths: Sequence[str] = (), *,
                        expected_url: str | None = None,
                        expected_sha256: Mapping[str, str] | None = None) -> dict:
    """Bind an existing HEAD and explicitly selected worktree bytes to a Git pin.

    VERIFIED means the selected bytes match the pinned Git blobs.  It does not
    mean all unselected files have been read or that the repository was built.
    Global worktree cleanliness is deliberately not assessed: git status can
    execute repository-configured fsmonitor or clean-filter commands.  Only the
    explicitly selected raw file bytes are inspected here.
    """
    root = Path(source_root).absolute()
    record = {"path": str(root), "expected_commit": expected_commit,
              "expected_url": expected_url, "status": "RETRIEVAL_UNAVAILABLE",
              "discovery_status": "RETRIEVAL_UNAVAILABLE", "observed_head": None,
              "observed_tree": None, "observed_origin": None, "files": [],
              "commands": [], "reasons": [], "verification_scope": "explicit_paths_only",
              "build_status": "NOT_RUN"}
    if not root.is_dir() or root.is_symlink():
        record["reasons"].append(_reason("QRH003_SOURCE_ROOT_UNAVAILABLE", str(root)))
        return record
    if not COMMIT_RE.fullmatch(expected_commit or ""):
        record.update(status="MISMATCH", discovery_status="NO_MATCH")
        record["reasons"].append(_reason("QRH003_SOURCE_COMMIT_NOT_PINNED", expected_commit))
        return record
    values = {}
    for key, args in (("toplevel", ("rev-parse", "--show-toplevel")),
                      ("object_format", ("rev-parse", "--show-object-format")),
                      ("head", ("rev-parse", "--verify", "HEAD")),
                      ("tree", ("rev-parse", "--verify", expected_commit + "^{tree}")),
                      ("origin", ("remote", "get-url", "origin"))):
        command, data = _git(root, *args)
        record["commands"].append(command)
        values[key] = data.decode("utf-8", "replace").strip() if command["status"] == "SUCCESS" else None
    record.update(observed_head=values["head"], observed_tree=values["tree"],
                  observed_origin=values["origin"],
                  worktree_clean=None, worktree_clean_status="NOT_ASSESSED",
                  worktree_clean_reason="git status omitted to avoid repository-configured fsmonitor/clean filters")
    if values["toplevel"] is None or values["head"] is None or values["tree"] is None:
        record["reasons"].append(_reason("QRH003_GIT_METADATA_UNAVAILABLE"))
        return record
    if Path(values["toplevel"]).resolve() != root.resolve():
        record["reasons"].append(_reason("QRH003_SOURCE_ROOT_NOT_REPOSITORY_ROOT"))
    if values["object_format"] != "sha1":
        record["reasons"].append(_reason("QRH003_GIT_OBJECT_FORMAT_UNSUPPORTED", values["object_format"]))
    if values["head"] != expected_commit:
        record["reasons"].append(_reason("QRH003_UPSTREAM_COMMIT_MISMATCH", values["head"]))
    # URL normalization is narrow and observable: only a trailing slash and .git.
    normalize = lambda value: (value or "").rstrip("/").removesuffix(".git")
    if expected_url is not None and normalize(values["origin"]) != normalize(expected_url):
        record["reasons"].append(_reason("QRH003_SOURCE_ORIGIN_MISMATCH", values["origin"]))
    tree, tree_record = read_git_tree(root, expected_commit)
    record["git_tree_observation"] = tree_record
    if tree_record["status"] != "VERIFIED":
        record["reasons"].extend(tree_record["reasons"])
        return record
    seen = set()
    for path in critical_paths:
        item = {"path": path, "status": "MISSING", "sha256": None,
                "git_blob_sha1": None, "expected_git_blob_sha1": None, "bytes": None,
                "reasons": []}
        record["files"].append(item)
        try:
            path = _safe_relative(path)
            if path in seen:
                raise AuditError("QRH003_DUPLICATE_CRITICAL_PATH", path)
            seen.add(path)
            entry = tree.get(path)
            item["expected_git_blob_sha1"] = entry["oid"] if entry else None
            if entry is None:
                raise AuditError("QRH003_SUBJECT_CRITICAL_FILE_NOT_IN_PIN", path)
            if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
                raise AuditError("QRH003_SUBJECT_UNSUPPORTED_FILE_MODE", path)
            data = secure_read(root, path)
            item.update(sha256=sha256_bytes(data), git_blob_sha1=blob_sha1(data), bytes=len(data))
            if item["git_blob_sha1"] != entry["oid"]:
                raise AuditError("QRH003_SUBJECT_DIGEST_MISMATCH", path)
            wanted = (expected_sha256 or {}).get(path)
            if wanted is not None and wanted != item["sha256"]:
                raise AuditError("QRH003_SUBJECT_DIGEST_MISMATCH", path)
            item["status"] = "VERIFIED"
        except FileNotFoundError:
            item["reasons"].append(_reason("QRH003_SUBJECT_CRITICAL_FILE_MISSING", path))
        except AuditError as exc:
            code = getattr(exc, "code", "QRH003_SUBJECT_FILE_UNAVAILABLE")
            if isinstance(exc.__cause__, FileNotFoundError):
                code = "QRH003_SUBJECT_CRITICAL_FILE_MISSING"
            # secure_read deliberately has its own fail-closed path admission;
            # retain that reason rather than converting it into an ordinary hash.
            item["status"] = ("MISSING" if code == "QRH003_SUBJECT_CRITICAL_FILE_MISSING" else
                              "MISMATCH" if "MISMATCH" in code or "NOT_IN_PIN" in code else "UNAVAILABLE")
            item["reasons"].append(_reason(code, str(exc)))
        except (OSError, ValueError) as exc:
            item["status"] = "UNAVAILABLE"
            item["reasons"].append(_reason("QRH003_SUBJECT_FILE_UNAVAILABLE", str(exc)))
        record["reasons"].extend(item["reasons"])
    if not record["reasons"]:
        record.update(status="VERIFIED", discovery_status="MATCH")
    else:
        matched = sum(x["status"] == "VERIFIED" for x in record["files"])
        record.update(status="MISMATCH" if any("MISMATCH" in x["code"] for x in record["reasons"]) else "PARTIAL",
                      discovery_status="PARTIAL_MATCH" if matched else "NO_MATCH")
    return record


def package_directory_name(name: str) -> str:
    value = name[1:-1] if name.startswith("«") and name.endswith("»") else name
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise AuditError("QRH003_DEPENDENCY_NAME_UNSUPPORTED", name)
    return value


def inventory_locked_dependencies(source_root: Path,
                                  dependency_roots: Mapping[str, Path], *,
                                  expected_count: int | None = 42) -> dict:
    """Inventory every lock record, including dependencies unavailable locally."""
    source_root = Path(source_root)
    result = {"status": "RETRIEVAL_UNAVAILABLE", "discovery_status": "RETRIEVAL_UNAVAILABLE",
              "lock_path": "lean/lake-manifest.json", "lock_sha256": None,
              "expected_count": expected_count, "records": [], "reasons": []}
    try:
        raw = secure_read(source_root, result["lock_path"])
        lock = strict_loads(raw)
        result["lock_sha256"] = sha256_bytes(raw)
        packages = lock["packages"]
        if not isinstance(packages, list):
            raise ValueError("packages must be an array")
    except (OSError, ValueError, KeyError, TypeError, AuditError) as exc:
        result["reasons"].append(_reason("QRH003_DEPENDENCY_LOCK_UNAVAILABLE", str(exc)))
        return result
    result.update(lock_version=lock.get("version"), declared_packages_dir=lock.get("packagesDir"),
                  record_count=len(packages))
    if expected_count is not None and len(packages) != expected_count:
        result["reasons"].append(_reason("QRH003_DEPENDENCY_LOCK_COUNT_MISMATCH"))
    seen = set()
    for index, package in enumerate(packages):
        item = {"lock_index": index, "lock_record": package, "package": None,
                "directory_name": None, "status": "RETRIEVAL_UNAVAILABLE",
                "discovery_status": "RETRIEVAL_UNAVAILABLE", "verification": None, "reasons": []}
        result["records"].append(item)
        try:
            if not isinstance(package, dict):
                raise AuditError("QRH003_DEPENDENCY_LOCK_RECORD_INVALID", str(index))
            name = package_directory_name(package.get("name", ""))
            item.update(package=name, directory_name=name)
            if name in seen:
                raise AuditError("QRH003_DEPENDENCY_DUPLICATE_NAME", name)
            seen.add(name)
            rev = package.get("rev")
            if package.get("type") != "git" or not isinstance(rev, str) or not COMMIT_RE.fullmatch(rev):
                raise AuditError("QRH003_DEPENDENCY_NOT_PINNED", name)
            if package.get("subDir") not in (None, ""):
                raise AuditError("QRH003_DEPENDENCY_SUBDIR_UNSUPPORTED", name)
            if not isinstance(package.get("url"), str) or not package["url"].startswith("https://"):
                raise AuditError("QRH003_DEPENDENCY_URL_UNSUPPORTED", name)
            root = dependency_roots.get(name)
            item["path"] = str(root) if root is not None else None
            if root is None or not Path(root).is_dir():
                item["reasons"].append(_reason("QRH003_DEPENDENCY_SOURCE_UNAVAILABLE", name))
                continue
            configs = [package["configFile"]] if package.get("configFile") else []
            verification = verify_git_snapshot(Path(root), rev, configs, expected_url=package["url"])
            item.update(verification=verification, status=verification["status"],
                        discovery_status=verification["discovery_status"])
            item["reasons"].extend(verification["reasons"])
        except (AuditError, TypeError, AttributeError) as exc:
            item.update(status="MISMATCH", discovery_status="NO_MATCH")
            item["reasons"].append(_reason(getattr(exc, "code", "QRH003_DEPENDENCY_LOCK_RECORD_INVALID"), str(exc)))
    verified = sum(x["status"] == "VERIFIED" for x in result["records"])
    result.update(verified_count=verified, unavailable_count=sum(x["status"] == "RETRIEVAL_UNAVAILABLE" for x in result["records"]))
    complete = bool(packages) and verified == len(packages) and not result["reasons"]
    result.update(status="VERIFIED" if complete else "PARTIAL" if verified else "RETRIEVAL_UNAVAILABLE",
                  discovery_status="MATCH" if complete else "PARTIAL_MATCH" if verified else "RETRIEVAL_UNAVAILABLE")
    return result


def discover_patch_plan(source_root: Path) -> dict:
    """Recognize the pinned Lake patch declarations without executing lakefile.lean.

    The restricted parser is specific to this selected revision.  A changed
    declaration shape/order yields PARTIAL_MATCH, never an inferred replacement.
    """
    root = Path(source_root)
    result = {"status": "RETRIEVAL_UNAVAILABLE", "records": [], "events": [],
              "declaration_execution": "NOT_RUN", "reasons": []}
    try:
        data = secure_read(root, "lean/lakefile.lean")
        text = data.decode("utf-8")
        result["lakefile_sha256"] = sha256_bytes(data)
        pre = re.search(r"private def preResolutionPatchNames\s*:[^=]+:=\s*#\[(.*?)\]", text, re.S)
        post = re.search(r"post_update pkg do(.*)\Z", text, re.S)
        post_array = re.search(r"for name in\s*#\[(.*?)\]\s*do", post.group(1), re.S) if post else None
        read_names = lambda value: tuple(package_directory_name(m.group(1)) for m in re.finditer(r"`(«[^»]+»|[A-Za-z0-9_-]+)", value))
        if pre is None or post_array is None:
            raise AuditError("QRH003_PATCH_DECLARATION_UNRECOGNIZED")
        pre_names, post_names = read_names(pre.group(1)), read_names(post_array.group(1))
        if pre_names != PRE_RESOLUTION_PATCHES or post_names != POST_UPDATE_PATCHES:
            raise AuditError("QRH003_PATCH_PHASE_ORDER_MISMATCH")
        if "for name in preResolutionPatchNames do" not in post.group(1):
            raise AuditError("QRH003_PATCH_REVERIFICATION_DECLARATION_MISSING")
        for phase, names in (("pre_resolution", pre_names), ("post_update", post_names)):
            for order, name in enumerate(names):
                relative = f"lean/patches/{name}-lean4341.patch"
                record = {"package": name, "phase": phase, "phase_order": order,
                          "declaration_order": len(result["records"]), "path": relative,
                          "sha256": None, "git_blob_sha1": None, "status": "MISSING"}
                result["records"].append(record)
                try:
                    patch = secure_read(root, relative)
                    record.update(sha256=sha256_bytes(patch), git_blob_sha1=blob_sha1(patch),
                                  bytes=len(patch), status="OBSERVED")
                except (OSError, AuditError) as exc:
                    record["reason"] = _reason("QRH003_PATCH_FILE_UNAVAILABLE", str(exc))
                    result["reasons"].append(record["reason"])
        result["events"] = ([{"phase": "pre_resolution", "action": "apply", "package": name} for name in pre_names]
                            + [{"phase": "dependency_resolution", "action": "not_executed_by_collector", "package": None}]
                            + [{"phase": "post_update", "action": "reverify_pre_resolution_patch", "package": name} for name in pre_names]
                            + [{"phase": "post_update", "action": "apply", "package": name} for name in post_names])
        result["status"] = "OBSERVED" if not result["reasons"] else "PARTIAL_MATCH"
    except (OSError, UnicodeError, AuditError) as exc:
        result["reasons"].append(_reason(getattr(exc, "code", "QRH003_PATCH_DECLARATION_UNAVAILABLE"), str(exc)))
        result["status"] = "PARTIAL_MATCH"
    return result


def fetch_pinned_repository(url: str, revision: str, destination: Path,
                            *, timeout: float = 600) -> dict:
    """Optionally fetch into a new destination; preserve failed staging evidence."""
    target = Path(destination)
    result = {"url": url, "revision": revision, "destination": str(target),
              "status": "NOT_RUN", "commands": [], "reasons": []}
    if not COMMIT_RE.fullmatch(revision or "") or not url.startswith("https://"):
        result.update(status="BLOCKED", reasons=[_reason("QRH003_FETCH_UNPINNED_OR_UNSUPPORTED")])
        return result
    if target.exists() or target.is_symlink():
        result.update(status="BLOCKED", reasons=[_reason("QRH003_FETCH_DESTINATION_EXISTS")])
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="." + target.name + "-acquisition-", dir=target.parent))
    result["staging_path"] = str(staging)
    steps = (["git", "init", "--quiet", str(staging)],
             ["git", "-C", str(staging), "remote", "add", "origin", url],
             ["git", "-C", str(staging), "fetch", "--depth=1", "origin", revision],
             ["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(staging), "checkout", "--quiet", "--detach", revision])
    for argv in steps:
        command, _ = _command(argv, timeout=timeout)
        result["commands"].append(command)
        if command["status"] != "SUCCESS":
            result.update(status=command["status"], reasons=[_reason("QRH003_FETCH_FAILED", command["status"])])
            return result
    verification = verify_git_snapshot(staging, revision, expected_url=url)
    result["verification"] = verification
    if verification["status"] != "VERIFIED":
        result.update(status="MISMATCH", reasons=verification["reasons"])
        return result
    # Refuse replacement if another actor created the final destination meanwhile.
    try:
        target.mkdir(exist_ok=False)
        for child in staging.iterdir():
            child.rename(target / child.name)
        staging.rmdir()
    except OSError as exc:
        result.update(status="FAILED", reasons=[_reason("QRH003_FETCH_FINALIZATION_FAILED", str(exc))])
        return result
    result["status"] = "RETRIEVED_AT_PINNED_REV"
    return result


def _export_git_tree(root: Path, revision: str, destination: Path) -> tuple[dict, dict]:
    """Export Git blobs, avoiding archive filters, substitutions, and symlinks."""
    tree, observation = read_git_tree(root, revision)
    if observation["status"] != "VERIFIED":
        raise AuditError("QRH003_PATCH_BASE_TREE_UNAVAILABLE")
    # git archive observes export-ignore/export-subst attributes.  A raw batch
    # blob export deliberately does not, so the source manifest covers the tree.
    destination.mkdir(parents=False, exist_ok=False)
    command = ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
               "-c", "core.attributesFile=" + os.devnull, "-C", str(root), "cat-file", "--batch"]
    export_env = _git_env()
    export_env["GIT_ALLOW_PROTOCOL"] = ""
    process = subprocess.Popen(command, env=export_env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = threading.Event()
    def stop_export():
        timed_out.set()
        if process.poll() is None:
            process.kill()
    timer = threading.Timer(120, stop_export)
    timer.daemon = True
    timer.start()
    files, exported_bytes = {}, 0
    try:
        assert process.stdin is not None and process.stdout is not None
        for relative, entry in sorted(tree.items()):
            if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
                raise AuditError("QRH003_PATCH_BASE_FILE_MODE_UNSUPPORTED", relative)
            process.stdin.write((entry["oid"] + "\n").encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline().decode("ascii", "strict").strip().split(" ")
            if len(header) != 3 or header[0] != entry["oid"] or header[1] != "blob":
                if timed_out.is_set():
                    raise AuditError("QRH003_PATCH_BASE_EXPORT_TIMEOUT", relative)
                raise AuditError("QRH003_PATCH_BASE_BLOB_UNAVAILABLE", relative)
            size = int(header[2])
            if size < 0 or size > 134217728:
                raise AuditError("QRH003_PATCH_BASE_BLOB_SIZE_LIMIT", relative)
            exported_bytes += size
            if exported_bytes > 1_073_741_824:
                raise AuditError("QRH003_PATCH_BASE_EXPORT_SIZE_LIMIT", relative)
            data = process.stdout.read(size)
            if len(data) != size or process.stdout.read(1) != b"\n" or blob_sha1(data) != entry["oid"]:
                raise AuditError("QRH003_PATCH_BASE_BLOB_MISMATCH", relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            exclusive_write(target, data)
            target.chmod(0o755 if entry["mode"] == "100755" else 0o644)
            files[relative] = {"sha256": sha256_bytes(data), "git_blob_sha1": entry["oid"],
                               "bytes": len(data), "mode": entry["mode"]}
        process.stdin.close()
        if process.wait(timeout=30) != 0:
            raise AuditError("QRH003_PATCH_BASE_EXPORT_FAILED")
    except (OSError, ValueError, AuditError, subprocess.SubprocessError) as exc:
        if timed_out.is_set():
            raise AuditError("QRH003_PATCH_BASE_EXPORT_TIMEOUT") from exc
        raise
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait()
        for stream in (process.stdout, process.stderr):
            if stream:
                stream.close()
    return files, observation


def _tree_manifest(root: Path) -> dict:
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            if path.is_symlink():
                raise AuditError("QRH003_EFFECTIVE_SOURCE_SYMLINK", str(path))
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            data = secure_read(root, relative)
            files[relative] = {"sha256": sha256_bytes(data), "git_blob_sha1": blob_sha1(data),
                               "bytes": len(data), "mode": "100755" if path.stat().st_mode & 0o111 else "100644"}
    return dict(sorted(files.items()))


def materialize_effective_sources(source_root: Path, dependencies: dict, destination: Path,
                                  *, apply_patches: bool = False) -> dict:
    """Materialize all available patched dependencies into fresh verified copies.

    All 23 declared patch records survive, even when their base source is absent.
    This preserves phase metadata but does not pretend to execute Lake's phases.
    """
    source_root, destination = Path(source_root).absolute(), Path(destination).absolute()
    plan = discover_patch_plan(source_root)
    result = {"status": "NOT_RUN", "destination": str(destination), "patch_plan": plan,
              "records": [], "authority": "NONE", "lake_resolution_status": "NOT_RUN",
              "phase_execution_status": "STATIC_ORDER_ONLY", "reasons": []}
    if not apply_patches:
        result["records"] = [{**patch, "materialization_status": "NOT_REQUESTED"} for patch in plan["records"]]
        return result
    if plan["status"] != "OBSERVED":
        result.update(status="BLOCKED", reasons=[_reason("QRH003_PATCH_PLAN_INCOMPLETE")])
        return result
    patch_identity = verify_git_snapshot(source_root, UPSTREAM_COMMIT,
        ["lean/lakefile.lean"] + [item["path"] for item in plan["records"]])
    result["patch_source_identity"] = patch_identity
    if patch_identity["status"] != "VERIFIED":
        result.update(status="BLOCKED", reasons=[_reason("QRH003_PATCH_SOURCE_IDENTITY_UNVERIFIED")])
        result["records"] = [{**patch, "materialization_status": "BLOCKED"} for patch in plan["records"]]
        return result
    protected = [source_root.resolve()] + [Path(x["path"]).resolve() for x in dependencies.get("records", []) if x.get("path")]
    resolved_destination = destination.resolve()
    if any(resolved_destination == root or root in resolved_destination.parents for root in protected):
        result.update(status="BLOCKED", reasons=[_reason("QRH003_PATCH_DESTINATION_INSIDE_SOURCE")])
        return result
    if destination.exists() or destination.is_symlink():
        result.update(status="BLOCKED", reasons=[_reason("QRH003_PATCH_DESTINATION_EXISTS")])
        return result
    destination.mkdir(parents=True, exist_ok=False)
    lookup = {x["package"]: x for x in dependencies.get("records", []) if x.get("package")}
    for patch in plan["records"]:
        item = {**patch, "materialization_status": "RETRIEVAL_UNAVAILABLE", "commands": [],
                "effective_path": None, "base_files": None, "effective_files": None, "reasons": []}
        result["records"].append(item)
        dependency = lookup.get(patch["package"])
        if dependency is None or dependency["status"] != "VERIFIED":
            item["reasons"].append(_reason("QRH003_PATCH_BASE_SOURCE_UNAVAILABLE", patch["package"]))
            continue
        try:
            revision = dependency["lock_record"]["rev"]
            base_root = Path(dependency["path"])
            fresh_base = verify_git_snapshot(base_root, revision,
                expected_url=dependency["lock_record"]["url"])
            item["base_identity"] = fresh_base
            if fresh_base["status"] != "VERIFIED":
                raise AuditError("QRH003_PATCH_BASE_IDENTITY_UNVERIFIED", patch["package"])
            target = destination / patch["package"]
            patch_data = secure_read(source_root, patch["path"])
            if sha256_bytes(patch_data) != patch["sha256"]:
                raise AuditError("QRH003_FROZEN_INPUT_CHANGED", patch["path"])
            # Freeze the exact patch bytes used by git apply; source reads later
            # cannot change the execution input through a time-of-check gap.
            patch_copy = destination / (patch["package"] + ".patch")
            exclusive_write(patch_copy, patch_data)
            item["frozen_patch_path"] = str(patch_copy)
            before, tree = _export_git_tree(base_root, revision, target)
            item.update(base_commit=revision, base_root=str(base_root), base_files=before,
                        base_manifest_sha256=sha256_bytes(canonical_bytes(before)), base_tree=tree,
                        effective_path=str(target))
            numstat, numstat_bytes = _git(target, "apply", "--numstat", "-z", str(patch_copy.resolve()))
            item["commands"].append(numstat)
            if numstat["status"] != "SUCCESS":
                raise AuditError("QRH003_PATCH_PATH_INVENTORY_FAILED")
            expected_changes = []
            for entry in numstat_bytes.split(b"\0"):
                if not entry:
                    continue
                fields = entry.split(b"\t", 2)
                if len(fields) != 3:
                    raise AuditError("QRH003_PATCH_PATH_INVENTORY_UNSUPPORTED")
                expected_changes.append(_safe_relative(fields[2].decode("utf-8", "strict")))
            item["expected_changed_paths"] = sorted(expected_changes)
            for args in (("apply", "--check"), ("apply",), ("apply", "--reverse", "--check")):
                command, _ = _git(target, *args, str(patch_copy.resolve()))
                item["commands"].append(command)
                if command["status"] != "SUCCESS":
                    raise AuditError("QRH003_PATCH_APPLY_FAILED", command["status"])
            after = _tree_manifest(target)
            changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
            if not changed or changed != sorted(expected_changes):
                raise AuditError("QRH003_PATCH_EFFECT_PATH_MISMATCH")
            item.update(effective_files=after, effective_manifest_sha256=sha256_bytes(canonical_bytes(after)),
                        changed_paths=changed, materialization_status="VERIFIED",
                        relation="pinned_git_tree_plus_exact_patch_bytes",
                        materialization_is_lake_execution=False)
        except (OSError, ValueError, UnicodeError, AuditError, subprocess.SubprocessError) as exc:
            item["materialization_status"] = "FAILED"
            item["reasons"].append(_reason(getattr(exc, "code", "QRH003_PATCH_MATERIALIZATION_FAILED"), str(exc)))
    count = sum(x["materialization_status"] == "VERIFIED" for x in result["records"])
    result.update(verified_count=count, declared_count=len(plan["records"]),
                  status="VERIFIED" if count == len(plan["records"]) else "PARTIAL_MATCH" if count else "RETRIEVAL_UNAVAILABLE")
    return result


def collect_acquisition(source_root: Path, dependency_root: Path, *,
                        lean_source_root: Path | None = None,
                        effective_destination: Path | None = None,
                        fetch_missing: bool = False, fetch_timeout: float = 600) -> dict:
    source_root, dependency_root = Path(source_root).absolute(), Path(dependency_root).absolute()
    patch_plan = discover_patch_plan(source_root)
    critical = list(CRITICAL_PATHS) + [x["path"] for x in patch_plan["records"]]
    subject = verify_git_snapshot(source_root, UPSTREAM_COMMIT, critical, expected_url=UPSTREAM_URL)
    result = {"schema": "qrh003.source_acquisition.v0", "artifact_role": "collector_observation",
              "authority": "NONE", "mathematical_review_status": "NOT_RUN", "subject": subject,
              "fetch_requested": fetch_missing, "fetch_records": [], "source_roots": [],
              "patch_plan": patch_plan, "reasons": []}
    roots = {}
    if fetch_missing and (dependency_root.resolve() == source_root.resolve()
                          or source_root.resolve() in dependency_root.resolve().parents):
        raise AuditError("QRH003_FETCH_DESTINATION_INSIDE_SOURCE")
    try:
        lock = strict_loads(secure_read(source_root, "lean/lake-manifest.json"))
        for entry in lock["packages"]:
            name = package_directory_name(entry["name"])
            roots[name] = dependency_root / name
            if fetch_missing and not roots[name].exists():
                if subject["status"] != "VERIFIED":
                    result["fetch_records"].append({"package": name, "status": "BLOCKED",
                                                    "reason": "QRH003_UNVERIFIED_LOCK_FETCH_FORBIDDEN"})
                else:
                    result["fetch_records"].append({"package": name, **fetch_pinned_repository(
                        entry["url"], entry["rev"], roots[name], timeout=fetch_timeout)})
    except (KeyError, TypeError, ValueError, OSError, AuditError) as exc:
        result["reasons"].append(_reason("QRH003_DEPENDENCY_LOCK_UNAVAILABLE", str(exc)))
    dependencies = inventory_locked_dependencies(source_root, roots)
    result["dependencies"] = dependencies
    result["provider_universe_status"] = dependencies["discovery_status"]
    lean_root = Path(lean_source_root).absolute() if lean_source_root is not None else dependency_root / "lean4"
    if fetch_missing and not lean_root.exists() and subject["status"] == "VERIFIED":
        if dependency_root.resolve() not in lean_root.resolve().parents:
            result["fetch_records"].append({"package": "lean4", "status": "BLOCKED",
                                            "reason": "QRH003_LEAN_FETCH_OUTSIDE_DEPENDENCY_ROOT"})
        else:
            result["fetch_records"].append({"package": "lean4", **fetch_pinned_repository(
                LEAN_SOURCE_URL, LEAN_SOURCE_COMMIT, lean_root, timeout=fetch_timeout)})
    lean = verify_git_snapshot(lean_root, LEAN_SOURCE_COMMIT, ("src/Init.lean",), expected_url=LEAN_SOURCE_URL)
    result["toolchain_source"] = lean
    result["toolchain_binary_status"] = "NOT_ACQUIRED_BY_THIS_COLLECTOR"
    effective = materialize_effective_sources(source_root, dependencies, effective_destination,
                  apply_patches=True) if effective_destination is not None else None
    result["effective_sources"] = effective
    def add_provider(package, root, git_root, revision, subdir="", profile="pinned_git_source", **extra):
        result["source_roots"].append({"package": package, "path": str(root), "git_root": str(git_root),
            "expected_commit": revision, "source_subdir": subdir, "source_profile": profile, **extra})
    add_provider("openai_math", source_root / "lean", source_root, UPSTREAM_COMMIT, "lean")
    overlays = {x["package"]: x for x in (effective or {}).get("records", [])}
    for entry in dependencies["records"]:
        name = entry.get("package")
        if not name:
            continue
        overlay = overlays.get(name)
        if overlay is not None and overlay["materialization_status"] == "VERIFIED":
            add_provider(name, Path(overlay["effective_path"]), Path(entry["path"]),
                         entry["lock_record"]["rev"], profile="patch_derived_overlay", effective_manifest=overlay)
        else:
            add_provider(name, roots.get(name, dependency_root / name), roots.get(name, dependency_root / name),
                         entry["lock_record"].get("rev"), required_patch_unapplied=name in PRE_RESOLUTION_PATCHES + POST_UPDATE_PATCHES)
    add_provider("lean4", lean_root / "src", lean_root, LEAN_SOURCE_COMMIT, "src")
    add_provider("lake", lean_root / "src/lake", lean_root, LEAN_SOURCE_COMMIT, "src/lake")
    result["status"] = "VERIFIED" if (subject["status"] == "VERIFIED" and dependencies["status"] == "VERIFIED"
        and lean["status"] == "VERIFIED" and effective is not None and effective["status"] == "VERIFIED") else "PARTIAL_MATCH"
    return result


run_acquisition = collect_acquisition


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--dependency-root", required=True, type=Path)
    parser.add_argument("--lean-source-root", type=Path)
    parser.add_argument("--effective-destination", type=Path)
    parser.add_argument("--fetch-missing", action="store_true",
                        help="Fetch only absent checkouts into the declared dependency directory")
    parser.add_argument("--fetch-timeout", type=float, default=600)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output == args.source_root.resolve() or args.source_root.resolve() in output.parents:
        parser.error("output must be outside the input source repository")
    record = collect_acquisition(args.source_root, args.dependency_root,
        lean_source_root=args.lean_source_root, effective_destination=args.effective_destination,
        fetch_missing=args.fetch_missing, fetch_timeout=args.fetch_timeout)
    for provider in record["source_roots"]:
        for key in ("path", "git_root"):
            root = Path(provider[key]).resolve()
            if output == root or root in output.parents:
                parser.error("output must be outside input source repositories")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, record)
    print(record["status"])
    return 0 if record["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
