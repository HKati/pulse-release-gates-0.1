#!/usr/bin/env python3
"""Independent Q2 capsule input/tokenizer checks; no model load or authority.

The input service checks bytes and projection. The tokenizer service runs in
the capsule interpreter and reuses the frozen independent record derivation.
Receipt replay validates evidence; it does not reacquire kernel observations.
This module never imports the new supervisor.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tarfile
import time
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io
import load_q2_release_intake_v0 as intake
import evaluate_q2_archived_capture_v0 as archived

PACK = io.PACK
TOOLS = PACK + "tools/"
PROFILE = PACK + "profiles/q2_release_host_tokenizer_verification_v0.json"
REQUEST_SCHEMA = "schemas/q2_release_host_tokenizer_request_v0.schema.json"
RESULT_SCHEMA = "schemas/q2_release_host_tokenizer_result_v0.schema.json"
SELF = TOOLS + "check_q2_release_host_tokenizer_v0.py"
SUPERVISOR = TOOLS + "verify_q2_release_host_tokenizer_v0.py"
WORKFLOW = ".github/workflows/q2_release_host_tokenizer_verification_v0.yml"
SCOPE = "q2_archived_native_tokenizer_only_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
OCCURRENCES = ("input_check", "tokenizer_check", "summary_builder", "summary_checker")
SOURCE_PATHS = tuple(sorted({
    PROFILE, REQUEST_SCHEMA, RESULT_SCHEMA, SELF, SUPERVISOR, WORKFLOW,
    io.PROFILE_PATH, io.SELECTION_PATH, io.CAPSULE_SCHEMA,
    io.REDUCER, io.CHECKER, "metrics/specs/q2_consistency_v0.yml",
    "schemas/metrics/q2_consistency_input_v0.schema.json",
    "schemas/metrics/q2_consistency_summary_v0.schema.json", "schemas/dataset_manifest.schema.json",
    "schemas/metrics/q2_reference_capture_v0.schema.json",
    "schemas/metrics/q2_reference_qualification_v0.schema.json",
    PACK + "profiles/q2_reference_model_files_v0.json",
    PACK + "examples/q2_reference_field_extraction_v0/requests.json",
    PACK + "profiles/q2_release_capsule_publication_v0.json",
    "schemas/q2_release_capsule_publication_v0.schema.json",
    *(TOOLS + n + ".py" for n in ("q2_intake_io_v0", "load_q2_release_intake_v0",
        "evaluate_q2_archived_capture_v0", "check_q2_release_intake_v0",
        "check_q2_release_capsule_publication_v0", "qualify_q2_reference_runtime_v0",
        "check_q2_reference_capture_v0", "check_q2_reference_qualification_v0")),
}))
CLAIMS = {
    "authority_effect": "none", "production_gate_eligible": False,
    "active_gate_eligible": False, "same_run_release_authority_eligible": False,
    "current_inference_count": 0, "worker_launch_executed": False,
    "model_weights_loaded": False, "full_release_host_verified": False,
    "historical_metric_pass": False,
}
ARCHIVE_FILES = {"capture": "capture.zip", "preparation": "preparation.zip",
                 "capsule": "capsule.zip", "roundtrip": "roundtrip.zip"}
PUBLIC_FILES = ("request.json", "prelaunch.json", "projection.json",
                "input-check.json", "tokenizer-check.json", "result.json")
VERIFIER_MODULES = ("attr", "attrs", "jsonschema", "jsonschema_specifications", "yaml",
                    "referencing", "rfc8785", "rpds", "typing_extensions")
BOOTSTRAP_MEMBER_COUNT = 10545
BOOTSTRAP_EXPANDED_BYTES = 305323346


class Budget:
    """One monotonic budget; shared IO receives this bounded remaining API."""
    def __init__(self, seconds=1200):
        io.require(type(seconds) in (int, float) and 0 < seconds <= 1200, "q2_timeout")
        self.start_ns = time.monotonic_ns()
        self.end = self.start_ns / 1e9 + seconds

    def remaining(self, cap=30):
        left = self.end - time.monotonic()
        io.require(left > 0 and 0 < cap <= 1200, "q2_timeout")
        return min(left, cap)


def load_profile(repo):
    raw = io.read_file(repo / PROFILE, 256 * 1024)
    p = io.strict_json(raw)
    schema = io.strict_json(io.read_file(repo / REQUEST_SCHEMA, 512 * 1024))
    io.require(io.encode(p) == io.encode(schema["$defs"]["profile"]["const"]) and
               p["source_paths"] == list(SOURCE_PATHS) and p["claims"] == CLAIMS and
               [r["id"] for r in p["occurrences"]] == list(OCCURRENCES), "q2_source_mismatch")
    return p


def request_for(repo, revision):
    io.require(re.fullmatch(r"[0-9a-f]{40}", revision or "") is not None, "q2_source_mismatch")
    p = load_profile(repo)
    return {"schema_version": "q2_release_host_tokenizer_request_v0", "scope": SCOPE,
            "source_commit": revision, "profile_sha256": io.digest(io.read_file(repo / PROFILE, 256 * 1024)),
            "inputs": p["inputs"], "definition_sha256": p["definition_sha256"]}


def check_request(repo, raw, expected_digest, revision):
    io.require(type(expected_digest) is str and re.fullmatch(r"[0-9a-f]{64}", expected_digest) and
               io.digest(raw) == expected_digest, "q2_request_digest_mismatch")
    obj = io.strict_json(raw, 32 * 1024)
    # Canonical equality is a complete closed const contract before dependencies
    # or transport are initialized. Encoding also distinguishes bool from int.
    io.require(io.encode(obj) == io.encode(request_for(repo, revision)), "q2_request_invalid")
    return obj


def source_closure(repo, revision, budget):
    """Bind the actual files and Git blob/mode identities, without token env."""
    io.require(re.fullmatch(r"[0-9a-f]{40}", revision or "") is not None, "q2_source_mismatch")
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    def git(args):
        proc = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c", "credential.helper=",
                               "-c", "core.hooksPath=/dev/null", "-c", "safe.directory=" + str(repo), *args],
                              cwd=repo, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, timeout=budget.remaining(15), check=False)
        io.require(proc.returncode == 0 and len(proc.stdout) <= 65536, "q2_source_mismatch")
        return proc.stdout
    io.require(git(["rev-parse", "--verify", "HEAD^{commit}"]) == revision.encode() + b"\n", "q2_source_mismatch")
    entries = {}
    for row in git(["ls-tree", "-rz", "--full-tree", revision, "--", *SOURCE_PATHS]).split(b"\0"):
        if row:
            metadata, name = row.split(b"\t")
            entries[name.decode("ascii")] = metadata.decode("ascii").split()
    io.require(set(entries) == set(SOURCE_PATHS), "q2_source_mismatch")
    rows = []
    for name in SOURCE_PATHS:
        raw = io.read_file(repo / name, 2 * 1024 * 1024, deadline=budget)
        mode = "100755" if (repo / name).stat().st_mode & 0o111 else "100644"
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        io.require(entries[name] == [mode, "blob", blob], "q2_source_mismatch")
        rows.append({"path": name, "size_bytes": len(raw), "sha256": io.digest(raw)})
    return rows


def payload_binding(path, maximum, budget):
    """Stream held payload files, including archive-bound empty regular files.

    The shared archive transport's nonempty-file rule stays unchanged. Its
    descriptor, no-link and mutation guards also apply to zero-byte payloads.
    """
    fd, before = io._open_regular(path)
    try:
        io.require(0 <= before.st_size <= maximum, "q2_file_rejected")
        hashed, size = hashlib.sha256(), 0
        while True:
            budget.remaining()
            part = os.read(fd, 65536)
            if not part: break
            size += len(part)
            io.require(size <= maximum, "q2_file_rejected")
            hashed.update(part)
        io.require(size == before.st_size and io._identity(before) == io._identity(os.fstat(fd)),
                   "q2_unstable_input")
        return {"archive_size_bytes": size, "archive_sha256": hashed.hexdigest()}
    finally:
        os.close(fd)


def file_row(path, relative, origin, archive_mode, executable=False, budget=None):
    expected_mode = 0o550 if executable else 0o440
    info = path.lstat()
    io.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
               info.st_uid == 0 and info.st_gid == 65534 and
               stat.S_IMODE(info.st_mode) == expected_mode, "q2_file_rejected")
    bound = payload_binding(path, 1024 * 1024 * 1024, budget or Budget(180))
    return {"path": relative, "origin": origin, "archive_mode": archive_mode,
            "kind": "file", "uid": 0, "gid": 65534, "mode": expected_mode,
            "size_bytes": bound["archive_size_bytes"], "sha256": bound["archive_sha256"]}


def check_tree(root, expected, budget):
    """Complete no-alias byte, ownership, mode and directory closure check."""
    io.require(type(expected) is list and len({r["path"] for r in expected}) == len(expected), "q2_file_rejected")
    rows = {r["path"]: r for r in expected}
    directories = {"."}
    for name in rows:
        io.safe_member(name)
        directories.update(p.as_posix() for p in Path(name).parents if p.as_posix() != ".")
    actual_files, actual_dirs = set(), set()
    pending = [(root, ".")]
    while pending:
        path, relative = pending.pop()
        budget.remaining()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            io.require(info.st_uid == 0 and info.st_gid == 65534 and
                       stat.S_IMODE(info.st_mode) == 0o550 and relative in directories, "q2_file_rejected")
            actual_dirs.add(relative)
            pending.extend((p, p.relative_to(root).as_posix()) for p in path.iterdir())
        elif stat.S_ISLNK(info.st_mode):
            io.require(relative in rows and rows[relative] == {
                "path": relative, "origin": rows[relative]["origin"], "archive_mode": 0o777,
                "kind": "symlink", "uid": 0, "gid": 65534, "target": "lib"} and
                relative in ("runtime/lib64", "lib64") and os.readlink(path) == "lib" and
                info.st_uid == 0 and info.st_gid == 65534, "q2_file_rejected")
            actual_files.add(relative)
        else:
            io.require(relative in rows, "q2_file_rejected")
            r = rows[relative]
            io.require(file_row(path, relative, r["origin"], r["archive_mode"], r["mode"] == 0o550, budget) == r,
                       "q2_digest_mismatch")
            actual_files.add(relative)
    io.require(actual_files == set(rows) and actual_dirs == directories, "q2_file_rejected")


def import_bound(root, name, expected=None):
    raw = io.read_file(root / name, 2 * 1024 * 1024, expected)
    spec = importlib.util.spec_from_file_location("q2_bound_" + Path(name).stem, root / name)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(root / name), "exec"), module.__dict__)
    return module


def verify_archives(repo, inputs, p, budget):
    """Shared byte substrate plus the existing independent archived checker.

    No legacy relocated installation checker or summary subprocess is invoked.
    """
    from contextlib import ExitStack
    ip = intake.load_profile(repo)
    io.require(io.file_binding(inputs / "bootstrap.tar.gz", p["bootstrap"]["archive_size_bytes"], budget) ==
               {k: p["bootstrap"][k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    for role, filename in ARCHIVE_FILES.items():
        e = p["inputs"][role]
        io.require(io.file_binding(inputs / filename, e["archive_size_bytes"], budget) ==
                   {k: e[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    with ExitStack() as stack:
        capture = stack.enter_context(archived.capture_archive(inputs / "capture.zip", ip, budget))
        docs, raw = archived.verify_capture(capture, ip)
        capsule = stack.enter_context(io.Archive(inputs / "capsule.zip",
            maximum_bytes=p["inputs"]["capsule"]["archive_size_bytes"],
            max_members=p["capsule_members"], member_bytes=ip["limits"]["capsule_member_bytes"],
            expanded_bytes=p["capsule_expanded_bytes"], deadline=budget, allow_runtime_link=True,
            expected_sha256=p["inputs"]["capsule"]["archive_sha256"]))
        archived.compare_subject(repo, capture, capsule, {"release_subject": p["inputs"]["capsule"]}, ip, docs)
        io.require(len(capsule.members) == p["capsule_members"] and
                   sum(i.file_size for i in capsule.members.values()) == p["capsule_expanded_bytes"], "q2_subject_mismatch")
        pub = io.strict_json(io.read_file(repo / p["publication_profile"], 256 * 1024))
        prep = stack.enter_context(io.Archive(inputs / "preparation.zip",
            maximum_bytes=p["inputs"]["preparation"]["archive_size_bytes"],
            max_members=pub["limits"]["preparation_members"], member_bytes=pub["limits"]["member_bytes"],
            expanded_bytes=pub["limits"]["preparation_expanded_bytes"], deadline=budget,
            expected_sha256=p["inputs"]["preparation"]["archive_sha256"]))
        io.require(len(prep.members) == pub["limits"]["preparation_members"] and
                   sum(i.file_size for i in prep.members.values()) == pub["limits"]["preparation_expanded_bytes"], "q2_archive_rejected")
        for row in pub["verifier_wheels"]:
            actual = prep.inspect("q2-runtime-preparation/" + row["path"])
            io.require(actual["kind"] == "file" and actual["size"] == row["size"] and
                       actual["sha256"] == row["sha256"], "q2_digest_mismatch")
        roundtrip = stack.enter_context(io.Archive(inputs / "roundtrip.zip",
            maximum_bytes=p["inputs"]["roundtrip"]["archive_size_bytes"], max_members=1,
            member_bytes=128 * 1024, expanded_bytes=128 * 1024, deadline=budget,
            expected_sha256=p["inputs"]["roundtrip"]["archive_sha256"]))
        io.require(set(roundtrip.members) == {"publication.json"}, "q2_archive_rejected")
        receipt = io.strict_json(roundtrip.read("publication.json"))
        io.validate(receipt, io.read_file(repo / "schemas/q2_release_capsule_publication_v0.schema.json", 256 * 1024))
        io.require(receipt["status"] == "roundtrip_verified" and receipt["capsule"] == pub["capsule"] and
                   receipt["artifact_id"] == p["inputs"]["capsule"]["artifact_id"] and
                   receipt["binding"] == {k: p["inputs"]["capsule"][k] for k in
                       ("repository", "workflow", "source_commit", "run_id", "run_attempt")} and
                   receipt["checks"] == {k: True for k in ("capture", "subject", "replay", "summary")} and
                   receipt["release_host_verification"] == "not_observed" and receipt["historical_metric_pass"] is False and
                   receipt["current_inference_count"] == 0 and receipt["cleanup"] == "verified_removed", "q2_replay_rejected")
        return docs, raw


def bootstrap_member(name, regular):
    # These three regular files occur in the exact hash-pinned official TAR.
    # The shared capsule ZIP grammar intentionally has no general space rule.
    special = {
        "lib/python3.11/site-packages/setuptools/_vendor/jaraco/text/Lorem ipsum.txt",
        "lib/python3.11/site-packages/setuptools/command/launcher manifest.xml",
        "lib/python3.11/site-packages/setuptools/script (dev).tmpl",
    }
    if name in special:
        io.require(regular, "q2_archive_rejected")
    else:
        io.safe_member(name)


def verify_bootstrap(path, p, budget):
    e = p["bootstrap"]
    io.require(io.file_binding(path, e["archive_size_bytes"], budget) ==
               {k: e[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    rows, names, expanded, count = [], set(), 0, 0
    base = Path(p["bootstrap_prefix"])
    with tarfile.open(path, "r:gz") as archive:
        for item in archive:
            budget.remaining(); count += 1; expanded += item.size
            io.require(count <= BOOTSTRAP_MEMBER_COUNT and expanded <= BOOTSTRAP_EXPANDED_BYTES and
                       not item.islnk(), "q2_archive_limit")
            name = item.name.removeprefix("./")
            if name == ".":
                io.require(item.isdir(), "q2_archive_rejected"); continue
            bootstrap_member(name, item.isreg())
            io.require(name not in names and (item.isdir() or item.isreg() or item.issym()), "q2_archive_rejected")
            names.add(name)
            if not name.startswith("lib/") or item.isdir():
                continue
            actual = base / name
            if item.issym():
                target = Path(name).parent / item.linkname
                io.require(not Path(item.linkname).is_absolute() and ".." not in target.parts and
                           actual.is_symlink() and os.readlink(actual) == item.linkname, "q2_replay_environment")
                rows.append({"path": name, "target": item.linkname})
            else:
                stream = archive.extractfile(item)
                h, size = hashlib.sha256(), 0
                while True:
                    budget.remaining(); raw = stream.read(65536)
                    if not raw: break
                    size += len(raw); h.update(raw)
                io.require(size == item.size, "q2_archive_rejected")
                d = payload_binding(actual, 1024 * 1024 * 1024, budget)
                io.require(d == {"archive_size_bytes": size, "archive_sha256": h.hexdigest()}, "q2_replay_environment")
                rows.append({"path": name, "size_bytes": size, "sha256": h.hexdigest()})
        io.require(count == BOOTSTRAP_MEMBER_COUNT and expanded == BOOTSTRAP_EXPANDED_BYTES,
                   "q2_archive_rejected")
    actual_names = {f.relative_to(base).as_posix() for f in (base / "lib").rglob("*") if f.is_file() or f.is_symlink()}
    io.require(actual_names == {r["path"] for r in rows}, "q2_replay_environment")
    io.read_file(base / "bin/python3.11", 1024 * 1024, p["bootstrap_python_sha256"], budget)
    return io.digest(io.encode(sorted(rows, key=lambda r: r["path"])))


def verifier_dependencies(verifier, p):
    """Closed distribution inventory, without importing third-party code."""
    site = verifier / "lib/python3.11/site-packages"
    normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
    wanted = {normalize(r["name"]): r["version"] for r in p["verifier_wheels"]}
    distributions = list(importlib.metadata.distributions(path=[str(site)]))
    io.require(all(type(d.metadata["Name"]) is str and type(d.version) is str for d in distributions),
               "q2_replay_environment")
    io.require(len(distributions) == len(wanted) and
               {normalize(d.metadata["Name"]): d.version for d in distributions} == wanted,
               "q2_replay_environment")
    return site


def check_verifier_tree(verifier, rows, p, budget):
    check_tree(verifier, rows, budget)
    io.require(sorted(r["path"] for r in rows if r.get("mode") == 0o550) ==
               p["verifier_interpreter_entries"], "q2_file_rejected")
    for row in rows:
        if row.get("mode") == 0o550:
            io.require(row["sha256"] == p["bootstrap_python_sha256"], "q2_replay_environment")
    cfg = io.read_file(verifier / "pyvenv.cfg", 4096).decode("utf-8", "strict")
    fields = dict(line.split(" = ", 1) for line in cfg.splitlines() if " = " in line)
    io.require(fields.get("home") == p["bootstrap_home"] and
               fields.get("include-system-site-packages") == "false" and fields.get("version") == "3.11.16",
               "q2_replay_environment")
    return verifier_dependencies(verifier, p)


def bind_collector_dependencies(verifier, rows, p, budget):
    """Load schema/metric dependencies only from the fresh verified tree.

    The base installation stays unchanged. Refuse cached external packages;
    adding a path cannot replace an already imported dependency safely.
    """
    site = check_verifier_tree(verifier, rows, p, budget).resolve(strict=True)
    def check_loaded():
        for name, module in tuple(sys.modules.items()):
            if name.split(".", 1)[0] in VERIFIER_MODULES:
                origin = getattr(module, "__file__", None)
                io.require(origin is not None and Path(origin).resolve(strict=True).is_relative_to(site),
                           "q2_replay_environment")
    check_loaded()
    sys.path.insert(0, str(site))
    for name in VERIFIER_MODULES:
        importlib.import_module(name)
    check_loaded()
    return site


def check_projection(root, projection, p, budget):
    io.require(set(projection) == {"record_type", "trees"} and
               projection["record_type"] == "q2_tokenizer_projection_v0" and
               set(projection["trees"]) == {"inputs", "capsule", "source", "historical", "verifier"}, "q2_file_rejected")
    for name, rows in projection["trees"].items():
        if name == "verifier": check_verifier_tree(root / name, rows, p, budget)
        else: check_tree(root / name, rows, budget)
    executables = [r["path"] for r in projection["trees"]["capsule"] if r.get("mode") == 0o550]
    io.require(sorted(executables) == p["interpreter_entries"], "q2_subject_mismatch")
    for r in projection["trees"]["capsule"]:
        if r["path"] in executables:
            io.require(r["sha256"] == p["bootstrap_python_sha256"], "q2_subject_mismatch")
    for tree in ("inputs", "source", "historical"):
        io.require(all(r["kind"] == "file" and r["mode"] == 0o440 for r in projection["trees"][tree]),
                   "q2_file_rejected")
    cfg = io.read_file(root / "capsule/runtime/pyvenv.cfg", 4096).decode("utf-8", "strict")
    fields = dict(line.split(" = ", 1) for line in cfg.splitlines() if " = " in line)
    io.require(fields.get("home") == p["bootstrap_home"] and
               fields.get("include-system-site-packages") == "false" and fields.get("version") == "3.11.16",
               "q2_replay_environment")
    io.read_file(Path(p["bootstrap_home"]) / "python3.11", 1024 * 1024, p["bootstrap_python_sha256"], budget)


def check_source_projection(projection, sources):
    """Bind every projected helper, including new files, to reviewed bytes."""
    rows = projection["trees"]["source"]
    expected = {r["path"]: r for r in sources}
    io.require(len(rows) == len(sources) == len(expected) and
               {r["path"] for r in rows} == set(expected), "q2_source_mismatch")
    for row in rows:
        source = expected[row["path"]]
        io.require(row == {"path": source["path"], "origin": "source:" + source["path"],
            "archive_mode": None, "kind": "file", "uid": 0, "gid": 65534, "mode": 0o440,
            "size_bytes": source["size_bytes"], "sha256": source["sha256"]}, "q2_source_mismatch")


def check_projection_origins(repo, inputs, projection, p, docs, budget):
    """A matching self-authored projection digest is not an archive binding."""
    ip = intake.load_profile(repo)
    expected_capsule = {"capsule.json"}
    for row in docs["installation.json"]["inventory"]:
        expected_capsule.add("runtime/" + row["path"])
    expected_capsule.update("source/" + name for name in ip["source_components"])
    expected_capsule.update(r["path"] for r in docs["capture-subject.json"]["model_files"])
    io.require({r["path"] for r in projection["trees"]["capsule"]} == expected_capsule, "q2_subject_mismatch")
    with archived.capture_archive(inputs / "capture.zip", ip, budget) as capture, io.Archive(
            inputs / "capsule.zip", maximum_bytes=p["inputs"]["capsule"]["archive_size_bytes"],
            max_members=p["capsule_members"], member_bytes=ip["limits"]["capsule_member_bytes"],
            expanded_bytes=p["capsule_expanded_bytes"], deadline=budget, allow_runtime_link=True,
            expected_sha256=p["inputs"]["capsule"]["archive_sha256"]) as capsule:
        for tree, archive in (("capsule", capsule), ("historical", capture)):
            io.require({r["path"] for r in projection["trees"][tree]} == set(archive.members), "q2_file_rejected")
            for row in projection["trees"][tree]:
                d = archive.inspect(row["path"])
                io.require(row["origin"] == tree + ":" + row["path"] and row["archive_mode"] == d["mode"] and
                           row["kind"] == d["kind"], "q2_digest_mismatch")
                if d["kind"] == "file":
                    io.require((row["size_bytes"], row["sha256"]) == (d["size"], d["sha256"]), "q2_digest_mismatch")
        source_bytes = []
        for name in SOURCE_PATHS:
            data = io.read_file(repo / name, 2 * 1024 * 1024, deadline=budget)
            source_bytes.append({"path": name, "size_bytes": len(data), "sha256": io.digest(data)})
        check_source_projection(projection, source_bytes)
        for row in ip["archived_source_files"]:
            if row["path"] in SOURCE_PATHS:
                data = io.read_file(repo / row["path"], 2 * 1024 * 1024, row["sha256"], budget)
                io.require(len(data) == row["size"], "q2_source_mismatch")
        for role, filename in ARCHIVE_FILES.items():
            row = next(r for r in projection["trees"]["inputs"] if r["path"] == filename)
            io.require(row["origin"] == "input:" + role and row["archive_mode"] is None and
                       row["size_bytes"] == p["inputs"][role]["archive_size_bytes"] and
                       row["sha256"] == p["inputs"][role]["archive_sha256"], "q2_digest_mismatch")
        io.require({r["path"] for r in projection["trees"]["inputs"]} ==
                   set(ARCHIVE_FILES.values()) | {"bootstrap.tar.gz"}, "q2_file_rejected")
        b = next(r for r in projection["trees"]["inputs"] if r["path"] == "bootstrap.tar.gz")
        io.require(b["origin"] == "input:bootstrap" and b["archive_mode"] is None and
                   b["sha256"] == p["bootstrap"]["archive_sha256"] and
                   b["size_bytes"] == p["bootstrap"]["archive_size_bytes"], "q2_digest_mismatch")


def native_target(runtime, p):
    io.require(sys.flags.isolated and os.getuid() == 65534 and os.getgid() == 65534 and
               Path(sys.prefix).resolve() == runtime.resolve() and sys.prefix != sys.base_prefix and
               platform.python_implementation() == "CPython" and platform.python_version() == "3.11.16" and
               unicodedata.unidata_version == "14.0.0" and sys.base_prefix == p["bootstrap_prefix"], "q2_replay_environment")
    io.read_file(Path(sys.executable), 1024 * 1024, p["bootstrap_python_sha256"])
    io.require(not any(k.startswith(("PULSE_Q2_", "GITHUB_", "ACTIONS_")) for k in os.environ), "q2_context_rejected")


def execution_plan(root, projection_sha, p):
    ip = p["historical_output_sha256"]
    checker = str(root / "source" / SELF)
    capsule_python = str(root / "capsule/runtime/bin/python")
    common = ["--groups", str(root / "handoff/tokenizer_check/groups.json"),
              "--dataset-manifest", str(root / "handoff/tokenizer_check/dataset-manifest.json"),
              "--expected-groups-sha256", ip["groups.json"], "--expected-manifest-sha256", ip["dataset-manifest.json"]]
    def binding(name, producer, digest):
        return {"name": name, "producer": producer, "sha256": digest}
    return [
        {"id": "input_check", "stage": "capturecheck", "expected_exit": 0,
         "argv": [str(root / "verifier/bin/python"), "-I", "-B", checker, "input", "--projection-root", str(root),
                  "--output", str(root / "work/input_check")],
         "input_bindings": [binding("projection.json", "supervisor", projection_sha)],
         "outputs": ["input-check.json"]},
        {"id": "tokenizer_check", "stage": "capturecheck", "expected_exit": 0,
         "argv": [capsule_python, "-I", "-B", checker, "tokenizer", "--projection-root", str(root),
                  "--output", str(root / "work/tokenizer_check")],
         "input_bindings": [binding("input-check.json", "input_check", None)],
         "outputs": ["tokenizer-check.json", "groups.json", "dataset-manifest.json"]},
        {"id": "summary_builder", "stage": "reduction", "expected_exit": 1,
         "argv": [capsule_python, "-I", "-B", str(root / "source" / io.REDUCER), *common,
                  "--out", str(root / "work/summary_builder/summary.json")],
         "input_bindings": [binding(n, "tokenizer_check", ip[n]) for n in ("groups.json", "dataset-manifest.json")],
         "outputs": ["summary.json"]},
        {"id": "summary_checker", "stage": "reduction", "expected_exit": 0,
         "argv": [capsule_python, "-I", "-B", str(root / "source" / io.CHECKER), *common,
                  "--summary", str(root / "handoff/summary_builder/summary.json"),
                  "--expected-summary-sha256", ip["summary.json"]],
         "input_bindings": [binding(n, "tokenizer_check", ip[n]) for n in ("groups.json", "dataset-manifest.json")]
             + [binding("summary.json", "summary_builder", ip["summary.json"])],
         "outputs": ["summary-check.json"]},
    ]


def derive_records(source, evidence, tokenizer, config):
    """Frozen complete 150-record ordering, watchdog and token/text derivation."""
    frozen = import_bound(source, TOOLS + "check_q2_reference_capture_v0.py")
    native = frozen.capture_native(source)
    from jsonschema import Draft202012Validator
    schema = io.strict_json(io.read_file(source / frozen.CAPTURE_SCHEMA, 512 * 1024))
    Draft202012Validator.check_schema(schema)
    validators = {kind: Draft202012Validator({"$ref": "#/$defs/" + kind, "$defs": schema["$defs"]})
                  for kind in ("prelaunch", "subject", "model_ready", "transcript", "response", "slot_ready")}
    def validate(kind, obj):
        io.require(validators[kind].is_valid(obj), "q2_schema_rejected")
    read = lambda name: io.read_file(evidence / name, 16 * 1024 * 1024)
    pre, subject, ready, terminal = (io.strict_json(read(n)) for n in
        ("capture-prelaunch.json", "capture-subject.json", "capture-model-ready.json", "transcript.json"))
    for kind, obj in (("prelaunch", pre), ("subject", subject), ("model_ready", ready), ("transcript", terminal)):
        validate(kind, obj)
    frozen.capture_sandbox(terminal["sandbox"], "captureworker", native)
    records = []
    for occurrence in terminal["occurrences"]:
        slot = occurrence["slot"]; stem = "calls/" + slot["call_id"]
        io.safe_member(stem)
        pair = []
        for key, suffix, kind in (("response", ".response.json", "response"), ("ready", ".ready.json", "slot_ready")):
            row = occurrence[key]; data = read(stem + suffix)
            io.require(row["path"] == stem + suffix and row["size"] == len(data) and
                       row["sha256"] == io.digest(data), "q2_capture_rejected")
            obj = io.strict_json(data)
            io.require(io.encode(obj) == data, "q2_capture_rejected")
            validate(kind, obj); pair.append(obj)
        io.require(read(stem + ".utf8") == pair[0]["text"].encode("utf-8"), "q2_capture_rejected")
        expected_intent = {"slot": slot, "binding": terminal["binding"], "generation_seconds": 15,
                           "retries": 0, "intent": "before_GO"}
        io.require(read(stem + ".intent.json") == io.encode(expected_intent), "q2_capture_rejected")
        records.append(tuple(pair))
    import rfc8785
    workload = io.strict_json(io.read_file(source / frozen.REQUESTS_PATH, 1024 * 1024))
    groups, manifest = frozen.capture_records(pre, subject, ready, terminal, records, workload, rfc8785.dumps,
        lambda messages: tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True),
        lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False), config)
    io.require(groups == read("groups.json") and manifest == read("dataset-manifest.json"), "q2_replay_rejected")
    return groups, manifest


def native_tokenizer(root, prelaunch, p, output):
    runtime = root / "capsule/runtime"
    native_target(runtime, p)
    input_check = io.strict_json(io.read_file(root / "handoff/input_check/input-check.json", 32 * 1024))
    io.require(input_check == {"record_type": "q2_native_tokenizer_input_check_v0", "occurrence_id": "input_check",
        "prelaunch_sha256": io.digest(io.encode(prelaunch)), "projection_sha256": prelaunch["projection_sha256"],
        "inputs": p["inputs"], **CLAIMS}, "q2_replay_rejected")
    import rfc8785
    import transformers
    import torch
    import tokenizers
    from transformers import AutoTokenizer, GenerationConfig
    for module in (rfc8785, transformers, torch, tokenizers):
        io.require(Path(module.__file__).resolve().is_relative_to(runtime.resolve()), "q2_replay_environment")
    io.require(torch.version.cuda is None, "q2_replay_environment")
    versions = {name: importlib.metadata.version(name) for name in
                ("torch", "transformers", "rfc8785", "tokenizers", "jsonschema")}
    io.require(all(versions[k] == v for k, v in p["runtime_versions"].items()), "q2_replay_environment")
    io.require(rfc8785.dumps({"a": 1.0, "b": -0.0}) == b'{"a":1,"b":0}', "q2_replay_environment")
    tokenizer = AutoTokenizer.from_pretrained(str(root / "capsule/model"), local_files_only=True,
                                              trust_remote_code=False, use_fast=True)
    tokenizer_module = sys.modules[type(tokenizer).__module__]
    io.require(Path(tokenizer_module.__file__).resolve().is_relative_to(runtime.resolve()) and
               tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id) == (1, 2, 2),
               "q2_replay_environment")
    native = import_bound(root / "source", TOOLS + "check_q2_reference_qualification_v0.py")
    config = GenerationConfig(**native.GENERATION, disable_compile=True).to_dict()
    subject = io.strict_json(io.read_file(root / "historical/capture-subject.json", 128 * 1024))
    io.require(len(config) == 67 and io.encode(config) == io.encode(subject["effective_generation"]), "q2_subject_mismatch")
    groups, manifest = derive_records(root / "source", root / "historical", tokenizer, config)
    io.write_new(output / "groups.json", groups)
    io.write_new(output / "dataset-manifest.json", manifest)
    return {"record_type": "q2_native_tokenizer_check_v0", "prelaunch_sha256": io.digest(io.encode(prelaunch)),
            "occurrence_id": "tokenizer_check", "verified_calls": 150,
            "groups_sha256": io.digest(groups), "manifest_sha256": io.digest(manifest),
            "runtime_versions": versions, "tokenizer_class": type(tokenizer).__name__,
            "tokenizer_module": Path(tokenizer_module.__file__).resolve().relative_to(runtime).as_posix(),
            "configuration_sha256": io.digest(io.encode(config)), **CLAIMS}


def check_prelaunch(repo, pre, request_raw, projection_raw, p):
    schema = io.strict_json(io.read_file(repo / RESULT_SCHEMA, 1024 * 1024))
    io.validate(pre, io.encode({"$ref": "#/$defs/prelaunch", "$defs": schema["$defs"]}))
    io.require(set(pre) == {"record_type", "scope", "binding", "request_sha256", "source_bindings", "inputs",
        "projection_root", "projection_sha256", "bootstrap_lib_sha256", "occurrences",
        "phase_start_ns", "phase_deadline_ns", "claims"} and
        pre["record_type"] == "q2_tokenizer_prelaunch_v0" and pre["scope"] == SCOPE and
        pre["claims"] == CLAIMS and pre["inputs"] == p["inputs"] and
        pre["request_sha256"] == io.digest(request_raw) and pre["projection_sha256"] == io.digest(projection_raw) and
        pre["phase_deadline_ns"] == pre["phase_start_ns"] + 1200_000_000_000 and
        pre["occurrences"] == execution_plan(Path(pre["projection_root"]), pre["projection_sha256"], p), "q2_context_rejected")
    io.require({r["path"] for r in pre["source_bindings"]} == set(SOURCE_PATHS) and
               len(pre["source_bindings"]) == len(SOURCE_PATHS), "q2_source_mismatch")
    for row in pre["source_bindings"]:
        data = io.read_file(repo / row["path"], 2 * 1024 * 1024, row["sha256"])
        io.require(len(data) == row["size_bytes"], "q2_source_mismatch")
    check_request(repo, request_raw, pre["request_sha256"], pre["binding"]["source_commit"])


def service_check(root, mode, output):
    """One predeclared input or tokenizer service, never a full worker CLI."""
    repo = root / "source"
    p = load_profile(repo)
    budget = Budget(180)
    request_raw = io.read_file(root / "control/request.json", 32 * 1024)
    projection_raw = io.read_file(root / "control/projection.json", 16 * 1024 * 1024)
    pre = io.strict_json(io.read_file(root / "control/prelaunch.json", 256 * 1024))
    check_prelaunch(repo, pre, request_raw, projection_raw, p)
    io.require(pre["projection_root"] == str(root), "q2_file_rejected")
    io.require(Path(__file__).resolve() == (repo / SELF).resolve(), "q2_source_mismatch")
    if mode == "input":
        native_target(root / "verifier", p)
        projection = io.strict_json(projection_raw)
        check_projection(root, projection, p, budget)
        docs, _ = verify_archives(repo, root / "inputs", p, budget)
        io.require(verify_bootstrap(root / "inputs/bootstrap.tar.gz", p, budget) == pre["bootstrap_lib_sha256"],
                   "q2_replay_environment")
        check_projection_origins(repo, root / "inputs", projection, p, docs, budget)
        verifier_dependencies(root / "verifier", p)
        result = {"record_type": "q2_native_tokenizer_input_check_v0", "occurrence_id": "input_check",
                  "prelaunch_sha256": io.digest(io.encode(pre)), "projection_sha256": io.digest(projection_raw),
                  "inputs": p["inputs"], **CLAIMS}
        io.write_new(output / "input-check.json", io.encode(result))
    else:
        io.require(mode == "tokenizer", "q2_context_rejected")
        result = native_tokenizer(root, pre, p, output)
        io.write_new(output / "tokenizer-check.json", io.encode(result))


def validate_receipt(repo, evidence, inputs):
    """Independent closed replay. Observed kernel facts retain observer attribution."""
    p = load_profile(repo)
    io.require({path.name for path in evidence.iterdir()} == set(PUBLIC_FILES), "q2_file_rejected")
    files = {name: io.read_file(evidence / name, 16 * 1024 * 1024) for name in PUBLIC_FILES}
    objects = {name: io.strict_json(raw) for name, raw in files.items() if name != "request.json"}
    result, pre, projection = (objects[n] for n in ("result.json", "prelaunch.json", "projection.json"))
    io.validate(result, io.read_file(repo / RESULT_SCHEMA, 1024 * 1024))
    contract = io.strict_json(io.read_file(repo / RESULT_SCHEMA, 1024 * 1024))
    for filename, kind in (("projection.json", "projection"), ("input-check.json", "input_report"),
                           ("tokenizer-check.json", "tokenizer_report")):
        io.validate(objects[filename], io.encode({"$ref": "#/$defs/" + kind, "$defs": contract["$defs"]}))
    check_prelaunch(repo, pre, files["request.json"], files["projection.json"], p)
    io.require(source_closure(repo, pre["binding"]["source_commit"], Budget(180)) == pre["source_bindings"],
               "q2_source_mismatch")
    check_source_projection(projection, pre["source_bindings"])
    docs, original = verify_archives(repo, inputs, p, Budget(900))
    check_projection_origins(repo, inputs, projection, p, docs, Budget(900))
    # Actual original records are rechecked with the unchanged independent
    # metric core in this collector process. No extra subject is fabricated.
    archived.check_replay_environment(intake.load_profile(repo))
    metric = import_bound(repo, io.CHECKER)
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="q2-tokenizer-replay-") as folder:
        work = Path(folder)
        for name in ("groups.json", "dataset-manifest.json", "summary.json"):
            io.write_new(work / name, original[name])
        io.require(metric.verify(work / "groups.json", work / "dataset-manifest.json", work / "summary.json",
            io.digest(original["groups.json"]), io.digest(original["dataset-manifest.json"]),
            io.digest(original["summary.json"])) is False, "q2_summary_mismatch")
    io.require(result["status"] == "native_tokenizer_verified" and
               result["prelaunch_sha256"] == io.digest(files["prelaunch.json"]) and
               result["binding"] == pre["binding"] and result["inputs"] == p["inputs"] and
               result["source_bindings"] == pre["source_bindings"] and result["claims"] == CLAIMS and
               result["request_sha256"] == pre["request_sha256"] and
               result["projection_sha256"] == pre["projection_sha256"] and
               result["phase_start_ns"] == pre["phase_start_ns"] and
               result["phase_deadline_ns"] == pre["phase_deadline_ns"], "q2_replay_rejected")
    frozen = import_bound(repo, TOOLS + "check_q2_reference_capture_v0.py")
    native = frozen.capture_native(repo)
    io.require([r["id"] for r in result["occurrences"]] == list(OCCURRENCES), "q2_replay_rejected")
    previous, units, pids = pre["phase_start_ns"], set(), set()
    for declared, observed in zip(pre["occurrences"], result["occurrences"]):
        io.require(observed["id"] == declared["id"] and observed["argv"] == declared["argv"] and
                   observed["expected_exit"] == declared["expected_exit"] and
                   observed["exit_code"] == declared["expected_exit"] and observed["status"] == "completed" and
                   observed["stdout_eof"] is True and observed["unit"] not in units and observed["pid"] not in pids and
                   previous <= observed["launch_ns"] <= observed["isolation_observed_ns"] <= observed["exec_ns"] <= observed["exit_ns"] <=
                   observed["cleanup_ns"] <= observed["output_frozen_ns"] <= pre["phase_deadline_ns"] and
                   observed["exit_ns"] - observed["launch_ns"] <= 180_000_000_000,
                   "q2_replay_rejected")
        frozen.capture_sandbox(observed["isolation"], declared["stage"], native)
        frozen.capture_cleanup_check(observed["cleanup"], observed["unit"])
        io.require(observed["unit"] == observed["isolation"]["unit"] == observed["cleanup"]["unit"] and
                   observed["pid"] == observed["isolation"]["pid"] and
                   observed["projection_after_sha256"] == pre["projection_sha256"], "q2_replay_rejected")
        io.require(len(observed["input_bindings"]) == len(declared["input_bindings"]), "q2_replay_rejected")
        io.require(set(observed["outputs"]) == set(declared["outputs"]), "q2_replay_rejected")
        for actual, wanted in zip(observed["input_bindings"], declared["input_bindings"]):
            io.require(actual["name"] == wanted["name"] and actual["producer"] == wanted["producer"] and
                       (wanted["sha256"] is None or wanted["sha256"] == actual["sha256"]), "q2_replay_rejected")
        previous = observed["output_frozen_ns"]; units.add(observed["unit"]); pids.add(observed["pid"])
    input_check, token_check = objects["input-check.json"], objects["tokenizer-check.json"]
    for name, doc, index in (("input-check.json", input_check, 0), ("tokenizer-check.json", token_check, 1)):
        io.require(doc["prelaunch_sha256"] == result["prelaunch_sha256"] and
                   doc["occurrence_id"] == OCCURRENCES[index] and
                   all(type(doc[k]) is type(v) and doc[k] == v for k, v in CLAIMS.items()) and
                   result["occurrences"][index]["outputs"][name] == io.digest(files[name]), "q2_replay_rejected")
    io.require(input_check == {"record_type": "q2_native_tokenizer_input_check_v0", "occurrence_id": "input_check",
        "prelaunch_sha256": result["prelaunch_sha256"], "projection_sha256": pre["projection_sha256"],
        "inputs": p["inputs"], **CLAIMS}, "q2_replay_rejected")
    ip = intake.load_profile(repo)
    historical = p["historical_output_sha256"]
    io.require(token_check["verified_calls"] == 150 and token_check["groups_sha256"] == historical["groups.json"] and
               token_check["manifest_sha256"] == historical["dataset-manifest.json"] and
               token_check["runtime_versions"] == p["runtime_versions"] and
               token_check["configuration_sha256"] == p["configuration_sha256"] and
               result["occurrences"][1]["outputs"]["groups.json"] == historical["groups.json"] and
               result["occurrences"][1]["outputs"]["dataset-manifest.json"] == historical["dataset-manifest.json"] and
               result["occurrences"][2]["outputs"] == {"summary.json": historical["summary.json"]} and
               result["occurrences"][3]["outputs"] == {"summary-check.json": historical["summary-check.json"]},
               "q2_summary_mismatch")
    # Consumer edges retain the actual producer occurrence, including when byte
    # content happens to equal a different producer's output.
    for index in (1, 2, 3):
        for row in result["occurrences"][index]["input_bindings"]:
            producer = row["producer"]
            if producer in OCCURRENCES:
                prior = result["occurrences"][OCCURRENCES.index(producer)]
                io.require(OCCURRENCES.index(producer) < index and
                           prior["outputs"].get(row["name"]) == row["sha256"], "q2_replay_rejected")
    host, old = result["host"], result["archived_platform_requirements"]
    io.require(set(host) == set(old) == set(p["platform_keys"]) and
               result["platform_matches"] == {k: host[k] == old[k] for k in old} and
               result["full_archived_platform_match"] is all(host[k] == old[k] for k in old) and
               all(host[k] == p["native_requirements"][k] for k in p["native_requirements"]) and
               result["cleanup"] == "verified_removed" and result["independent_check"] == "evidence_reconstructed" and
               result["clock_relation"] == "not_verified" and result["resource_measurement"] == "unavailable",
               "q2_replay_environment")
    io.require(projection["record_type"] == "q2_tokenizer_projection_v0" and
               result["metrics"] == p["historical_metrics"], "q2_summary_mismatch")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("input", "tokenizer", "replay", "make-request"))
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--projection-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args(argv)
    try:
        if args.mode == "make-request":
            io.require(args.repo_root is not None and args.source_commit is not None, "q2_request_invalid")
            raw = io.encode(request_for(args.repo_root.resolve(strict=True), args.source_commit))
            sys.stdout.buffer.write(raw)
        elif args.mode == "replay":
            io.require(args.repo_root is not None and args.evidence is not None and args.inputs is not None, "q2_request_invalid")
            p = load_profile(args.repo_root.resolve(strict=True))
            io.require(sys.prefix != sys.base_prefix and sys.base_prefix == p["bootstrap_prefix"] and
                       platform.python_version() == "3.11.16", "q2_replay_environment")
            verifier_dependencies(Path(sys.prefix), p)
            validate_receipt(args.repo_root.resolve(strict=True), args.evidence.resolve(strict=True), args.inputs.resolve(strict=True))
            print("q2_tokenizer_evidence_reconstructed")
        else:
            io.require(args.projection_root is not None and args.output is not None, "q2_request_invalid")
            service_check(args.projection_root.resolve(strict=True), args.mode, args.output.resolve(strict=True))
        return 0
    except Exception as exc:
        print(exc.code if isinstance(exc, io.IntakeError) else "q2_replay_rejected", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
