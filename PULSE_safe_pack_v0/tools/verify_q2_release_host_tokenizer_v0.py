#!/usr/bin/env python3
"""Owner-only externally isolated Q2 tokenizer supervision; zero inference.

Authenticated acquisition precedes credential-free services. Only the four
fixed occurrences are subjects. No worker CLI, model loader or gate is called.
Unsupported native prerequisites, partial execution or cleanup fail closed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unicodedata
import uuid

io = transport = independent = native = ObservedService = None

TOKEN = "PULSE_Q2_TOKENIZER_TOKEN"
SOURCE = "PULSE_Q2_TOKENIZER_SOURCE"
REQUEST = "PULSE_Q2_TOKENIZER_REQUEST"
DIGEST = "PULSE_Q2_TOKENIZER_REQUEST_SHA256"
NAME = "Q2 native release-host tokenizer verification v0"


def initialize_modules(source):
    """CLI calls this only on the committed, held-buffer source snapshot."""
    global io, transport, independent, native, ObservedService
    sys.path.insert(0, str(source / "PULSE_safe_pack_v0/tools"))
    io = importlib.import_module("q2_intake_io_v0")
    transport = importlib.import_module("check_q2_release_capsule_publication_v0")
    independent = importlib.import_module("check_q2_release_host_tokenizer_v0")
    native = importlib.import_module("qualify_q2_reference_runtime_v0")
    class BoundService(native.Service):
        def send(self, data):
            if data == b"EXEC\n":
                io.require(hasattr(self, "observation"), "q2_context_rejected")
                self.isolation_observed_ns = time.monotonic_ns()
            stamp = super().send(data)
            if data == b"EXEC\n": self.exec_ns = stamp
            return stamp
    ObservedService = BoundService


def bootstrap_sources(repo, env):
    """Stdlib-only guard before importing any repository helper.

    The pinned checkout/entry-point and Git object database are trusted inputs.
    Dirty helpers are never imported. Execution uses copies of the exact held
    buffers, so a pathname change between verification and import is harmless.
    """
    revision = env.get("GITHUB_SHA", "")
    workflow = ".github/workflows/q2_release_host_tokenizer_verification_v0.yml"
    expected = {"GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1", "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW_SHA": revision, "GITHUB_WORKFLOW": NAME,
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_ACTOR_ID": "128643840", "GITHUB_JOB": "verify_host", SOURCE: revision,
        "GITHUB_WORKSPACE": str(repo), "GITHUB_WORKFLOW_REF": "HKati/pulse-release-gates-0.1/" + workflow + "@refs/heads/main"}
    if (os.geteuid() != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision) or
            any(env.get(k) != v for k, v in expected.items())):
        raise ValueError("q2_context_rejected")
    clean = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
             "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    def git(args):
        p = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c", "credential.helper=",
            "-c", "core.hooksPath=/dev/null", "-c", "safe.directory=" + str(repo), *args],
            cwd=repo, env=clean, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=15, check=False)
        if p.returncode != 0 or len(p.stdout) > 65536: raise ValueError("q2_source_mismatch")
        return p.stdout
    if git(["rev-parse", "--verify", "HEAD^{commit}"]) != revision.encode() + b"\n":
        raise ValueError("q2_source_mismatch")
    def read(name):
        path = repo / name
        if any(p.is_symlink() for p in (path, *path.parents)): raise ValueError("q2_source_mismatch")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 * 1024**2:
                raise ValueError("q2_source_mismatch")
            raw = bytearray()
            while len(raw) <= 2 * 1024**2:
                chunk = os.read(fd, 65536)
                if not chunk: break
                raw.extend(chunk)
            after = os.fstat(fd)
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(raw) != before.st_size or stamp(before) != stamp(after): raise ValueError("q2_source_mismatch")
            return bytes(raw), "100755" if before.st_mode & 0o111 else "100644"
        finally: os.close(fd)
    def checked(names):
        entries = {}
        for row in git(["ls-tree", "-rz", "--full-tree", revision, "--", *names]).split(b"\0"):
            if row:
                metadata, name = row.split(b"\t"); entries[name.decode("ascii")] = metadata.decode("ascii").split()
        if set(entries) != set(names): raise ValueError("q2_source_mismatch")
        held = {}
        for name in names:
            raw, mode = read(name)
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if entries[name] != [mode, "blob", blob]: raise ValueError("q2_source_mismatch")
            held[name] = raw
        return held
    profile = "PULSE_safe_pack_v0/profiles/q2_release_host_tokenizer_verification_v0.json"
    first = checked([profile, "PULSE_safe_pack_v0/tools/verify_q2_release_host_tokenizer_v0.py"])
    def pairs(items):
        if len({k for k, _ in items}) != len(items): raise ValueError("q2_source_mismatch")
        return dict(items)
    p = json.loads(first[profile].decode("utf-8", "strict"), object_pairs_hook=pairs)
    names = p["source_paths"]
    if (not isinstance(names, list) or not 20 <= len(names) <= 60 or len(set(names)) != len(names) or
            any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", n)
                or ".." in Path(n).parts for n in names)):
        raise ValueError("q2_source_mismatch")
    held = checked(names)
    snapshot = Path(tempfile.mkdtemp(prefix="pulse-q2-bootstrap-", dir="/var/lib"))
    try:
        for name, raw in held.items():
            path = snapshot / name; path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        return snapshot
    except BaseException:
        shutil.rmtree(snapshot)
        raise


@contextmanager
def phase_boundary(seconds):
    """TERM/INT/alarm unwind into mandatory cleanup; SIGKILL gives no receipt."""
    def cancel(_signum, _frame):
        raise io.IntakeError("q2_timeout")
    old = {s: signal.signal(s, cancel) for s in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM)}
    previous = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous)
        for s, handler in old.items():
            signal.signal(s, handler)


def authorize(repo, env, budget):
    revision = env.get("GITHUB_SHA", "")
    expected = {"GITHUB_REPOSITORY": independent.REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW_SHA": revision, "GITHUB_WORKFLOW": NAME,
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": independent.REPOSITORY + "/" + independent.WORKFLOW + "@refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati", "GITHUB_ACTOR_ID": "128643840",
        "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ENVIRONMENT": "github-hosted",
        "GITHUB_WORKSPACE": str(repo), SOURCE: revision, "GITHUB_JOB": "verify_host"}
    io.require(all(env.get(k) == v for k, v in expected.items()) and
               re.fullmatch(r"[1-9][0-9]{0,23}", env.get("GITHUB_RUN_ID", "")) is not None,
               "q2_context_rejected")
    io.require(type(env.get(REQUEST)) is str and type(env.get(DIGEST)) is str and env.get("GITHUB_EVENT_PATH"),
               "q2_request_missing")
    raw = env[REQUEST].encode("utf-8", "strict")
    independent.check_request(repo, raw, env[DIGEST], revision)
    event = io.strict_json(io.read_file(Path(env["GITHUB_EVENT_PATH"]), 512 * 1024))
    io.require(event.get("inputs") == {"source_commit": revision, "native_request": env[REQUEST],
                   "native_request_sha256": env[DIGEST]} and event.get("ref") in ("main", "refs/heads/main") and
               event.get("sender", {}).get("login") == "HKati" and event["sender"].get("id") == 128643840 and
               type(event["sender"]["id"]) is int and event["sender"].get("type") == "User" and
               event.get("repository", {}).get("full_name") == independent.REPOSITORY, "q2_context_rejected")
    sources = independent.source_closure(repo, revision, budget)
    return {"repository": independent.REPOSITORY, "workflow": independent.WORKFLOW,
            "source_commit": revision, "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1,
            "job_name": "verify_host"}, sources, raw


def authenticate_current(client, binding, budget):
    main = transport.api_json(client, "/git/ref/heads/main", budget)
    io.require(main.get("object", {}).get("sha") == binding["source_commit"], "q2_source_mismatch")
    run = transport.api_json(client, f'/actions/runs/{binding["run_id"]}/attempts/1', budget)
    io.require(type(run.get("id")) is int and str(run.get("id")) == binding["run_id"] and run.get("run_attempt") == 1 and
               type(run.get("run_attempt")) is int and run.get("head_sha") == binding["source_commit"] and
               run.get("event") == "workflow_dispatch" and run.get("head_branch") == "main" and
               run.get("path") == independent.WORKFLOW and
               run.get("repository", {}).get("full_name") == independent.REPOSITORY and
               run.get("head_repository", {}).get("full_name") == independent.REPOSITORY and
               run.get("actor", {}).get("login") == run.get("triggering_actor", {}).get("login") == "HKati" and
               type(run.get("actor", {}).get("id")) is int and
               type(run.get("triggering_actor", {}).get("id")) is int and
               run.get("actor", {}).get("id") == run.get("triggering_actor", {}).get("id") == 128643840,
               "q2_context_rejected")
    jobs = transport.api_json(client, f'/actions/runs/{binding["run_id"]}/attempts/1/jobs?per_page=100', budget)
    io.require(type(jobs.get("total_count")) is int and jobs["total_count"] == 1 and
               len(jobs.get("jobs", [])) == 1, "q2_context_rejected")
    job = jobs["jobs"][0]
    io.require(job.get("name") == "verify_host" and type(job.get("id")) is int and job["id"] > 0 and
               type(job.get("run_id")) is int and str(job.get("run_id")) == binding["run_id"] and job.get("run_attempt") == 1 and
               type(job.get("run_attempt")) is int and
               job.get("head_sha") == binding["source_commit"] and job.get("status") == "in_progress", "q2_context_rejected")
    return {**binding, "job_id": str(job["id"])}


def host_record(env, p):
    release = platform.freedesktop_os_release()
    host = {"python": platform.python_version(), "os": release.get("ID", "") + "-" + release.get("VERSION_ID", ""),
            "architecture": platform.machine(), "libc": list(platform.libc_ver()),
            "kernel": platform.release(), "runner_image": env.get("ImageVersion", ""),
            "bootstrap_python_sha256": io.digest(io.read_file(Path(sys.executable).resolve(), 1024 * 1024))}
    io.require(os.geteuid() == 0 and Path("/proc/1/comm").read_text().strip() == "systemd" and
               Path("/sys/fs/cgroup/cgroup.controllers").is_file() and
               Path("/usr/bin/systemd-run").is_file() and Path("/usr/bin/systemctl").is_file() and
               platform.python_implementation() == "CPython" and unicodedata.unidata_version == "14.0.0" and
               re.fullmatch(r"[0-9]{8}\.[0-9]+(?:\.[0-9]+)?", host["runner_image"] or "") and
               all(host[k] == v for k, v in p["native_requirements"].items()) and
               sys.base_prefix == p["bootstrap_prefix"], "q2_replay_environment")
    return host


def prepare_bootstrap_library(private, p, budget):
    """Prepare the exact stock library before any subject can be launched.

    setup-python's release installer upgrades pip and creates bytecode. Rebuild
    only the pinned interpreter's library from the authenticated stock archive;
    never execute its setup.sh or pip. Verify a separate staging tree before
    replacing the installed library, then recheck the complete installed tree.
    This is privileged preparation, outside the four measured occurrences.
    """
    io.require(os.geteuid() == 0, "q2_context_rejected")
    base = Path(p["bootstrap_prefix"])
    io.require(base.is_absolute() and ".." not in base.parts and base.is_dir() and
               not any(q.is_symlink() for q in (base, *base.parents)) and
               stat.S_ISDIR((base / "lib").lstat().st_mode), "q2_file_rejected")
    archive_path = private / "bootstrap.tar.gz"
    expected = p["bootstrap"]
    io.require(io.file_binding(archive_path, expected["archive_size_bytes"], budget) ==
               {k: expected[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    interpreter = io.read_file(base / "bin/python3.11", 1024 * 1024,
                               p["bootstrap_python_sha256"], budget)
    stage = private / "bootstrap-library"; stage.mkdir(mode=0o700)
    try:
        (stage / "bin").mkdir(mode=0o700)
        io.write_new(stage / "bin/python3.11", interpreter)
        names, count, expanded = set(), 0, 0
        with tarfile.open(archive_path, "r:gz") as archive:
            for item in archive:
                budget.remaining(); count += 1; expanded += item.size
                io.require(0 <= item.size and count <= independent.BOOTSTRAP_MEMBER_COUNT and
                           expanded <= independent.BOOTSTRAP_EXPANDED_BYTES and not item.islnk(),
                           "q2_archive_limit")
                name = item.name.removeprefix("./")
                if name == ".":
                    io.require(item.isdir(), "q2_archive_rejected"); continue
                independent.bootstrap_member(name, item.isreg())
                io.require(name not in names and (item.isdir() or item.isreg() or item.issym()) and
                           not item.mode & 0o7000, "q2_archive_rejected")
                names.add(name)
                if name != "lib" and not name.startswith("lib/"): continue
                path = stage / name
                io.require(not any(q.is_symlink() for q in (path, *path.parents)), "q2_archive_rejected")
                path.parent.mkdir(parents=True, exist_ok=True)
                if item.isdir():
                    path.mkdir(mode=0o755, exist_ok=True)
                elif item.issym():
                    target = Path(name).parent / item.linkname
                    io.require(not Path(item.linkname).is_absolute() and ".." not in target.parts,
                               "q2_archive_rejected")
                    os.symlink(item.linkname, path)
                else:
                    source = archive.extractfile(item)
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with source, os.fdopen(fd, "wb") as destination:
                        size = 0
                        while True:
                            budget.remaining(); raw = source.read(65536)
                            if not raw: break
                            size += len(raw); io.require(size <= item.size, "q2_archive_rejected")
                            destination.write(raw)
                        io.require(size == item.size, "q2_archive_rejected")
                        destination.flush(); os.fsync(destination.fileno())
                    os.chmod(path, item.mode & 0o777)
        io.require(count == independent.BOOTSTRAP_MEMBER_COUNT and
                   expanded == independent.BOOTSTRAP_EXPANDED_BYTES, "q2_archive_rejected")
        library_sha = independent.verify_bootstrap(archive_path, {**p, "bootstrap_prefix": str(stage)}, budget)
        # The target is a fixed profile path, outside the preserved capsule.
        # Removing the old tree also removes installer-created bytecode and
        # distribution metadata; overwriting stock files would leave extras.
        library = base / "lib"
        io.require(stat.S_ISDIR(library.lstat().st_mode) and
                   not any(q.is_symlink() for q in (base, *base.parents)), "q2_file_rejected")
        budget.remaining(); shutil.rmtree(library)
        io.require(not os.path.lexists(library), "q2_file_rejected")
        budget.remaining(); shutil.copytree(stage / "lib", library, symlinks=True)
        io.require(independent.verify_bootstrap(archive_path, p, budget) == library_sha, "q2_replay_environment")
        return library_sha
    finally:
        shutil.rmtree(stage)
        io.require(not os.path.lexists(stage), "q2_cleanup_failed")


def projected_copy(source, destination, expected, origin, relative, budget, archive_mode=None, executable=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    transport.copy_verified(source, destination,
        {"archive_size_bytes": expected["size_bytes"], "archive_sha256": expected["sha256"]}, budget)
    os.chown(destination, 0, 65534); os.chmod(destination, 0o550 if executable else 0o440)
    return independent.file_row(destination, relative, origin, archive_mode, executable, budget)


def freeze_directories(root):
    for path in [root, *root.rglob("*")]:
        if path.is_dir() and not path.is_symlink():
            os.chown(path, 0, 65534); os.chmod(path, 0o550)


def prune_empty_verifier_directories(verifier):
    """Fresh verifier inventory represents files/links and their parents.

    Venv creates empty include directories. Remove only empty directories in
    this newly built verifier before freezing; preserved payloads are untouched.
    """
    for path in sorted(verifier.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if path.is_dir() and not path.is_symlink() and not any(path.iterdir()): path.rmdir()


def extract_projection(archive, root, role, executable_paths, budget):
    root.mkdir(mode=0o700)
    rows = []
    for name in sorted(archive.members):
        budget.remaining(); d = archive.inspect(name); path = root / io.safe_member(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if d["kind"] == "symlink":
            io.require(role == "capsule" and name == "runtime/lib64" and archive.read(name, 16) == b"lib",
                       "q2_subject_mismatch")
            os.symlink("lib", path); os.lchown(path, 0, 65534)
            rows.append({"path": name, "origin": role + ":" + name, "archive_mode": d["mode"],
                         "kind": "symlink", "uid": 0, "gid": 65534, "target": "lib"})
        else:
            io.require(d["kind"] == "file", "q2_subject_mismatch")
            # The shared read default is a JSON-sized bound. Binary runtime and
            # model payloads use their inspected size within the archive's
            # already enforced member limit; the shared default stays intact.
            raw = archive.read(name, d["size"])
            io.require(io.digest(raw) == d["sha256"] and len(raw) == d["size"], "q2_digest_mismatch")
            io.write_new(path, raw)
            executable = name in executable_paths
            os.chown(path, 0, 65534); os.chmod(path, 0o550 if executable else 0o440)
            rows.append(independent.file_row(path, name, role + ":" + name, d["mode"], executable, budget))
    freeze_directories(root)
    return rows


def prepare_verifier(private, root, p, budget):
    """Fresh separate verifier, only eight preserved wheels and fixed pip."""
    pub = transport.load_profile(private["repo"])
    wheels = private["path"] / "verifier-wheels"; wheels.mkdir(mode=0o700)
    with io.Archive(private["path"] / "preparation.zip", maximum_bytes=pub["preparation"]["archive_size_bytes"],
            max_members=pub["limits"]["preparation_members"], member_bytes=pub["limits"]["member_bytes"],
            expanded_bytes=pub["limits"]["preparation_expanded_bytes"], deadline=budget,
            expected_sha256=pub["preparation"]["archive_sha256"]) as archive:
        for row in pub["verifier_wheels"]:
            raw = archive.read("q2-runtime-preparation/" + row["path"], row["size"])
            io.require(len(raw) == row["size"] and io.digest(raw) == row["sha256"], "q2_digest_mismatch")
            io.write_new(wheels / Path(row["path"]).name, raw)
    verifier = root / "verifier"
    io.require(not verifier.exists(), "q2_file_rejected")
    rc = io.private_process([sys.executable, "-I", "-B", "-m", "venv", "--without-pip", "--copies", str(verifier)],
        cwd=private["path"], environment=native.clean_env(private["path"]), timeout=budget.remaining(60))
    io.require(rc == 0, "q2_replay_environment")
    requirement = private["path"] / "requirements.txt"
    io.write_new(requirement, "".join(f'{r["name"]}=={r["version"]} --hash=sha256:{r["sha256"]}\n'
                                     for r in pub["verifier_wheels"]).encode("ascii"))
    pip = private["path"] / pub["pip"]["filename"]
    io.read_file(pip, pub["pip"]["archive_size_bytes"], pub["pip"]["archive_sha256"], budget)
    command = [str(verifier / "bin/python"), "-I", "-B", "-c",
        "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')",
        str(pip), "--isolated", "--disable-pip-version-check", "--no-cache-dir", "install", "--no-index", "--no-deps",
        "--require-hashes", "--only-binary=:all:", "--force-reinstall", "--no-compile", "--find-links", str(wheels), "-r", str(requirement)]
    rc = io.private_process(command, cwd=private["path"], environment=native.clean_env(private["path"]),
                            timeout=budget.remaining(90), new_session=True)
    io.require(rc == 0, "q2_replay_environment")
    prune_empty_verifier_directories(verifier)
    rows = []
    for path in sorted(verifier.rglob("*")):
        relative = path.relative_to(verifier).as_posix()
        if path.is_symlink():
            io.require(relative == "lib64" and os.readlink(path) == "lib", "q2_file_rejected")
            os.lchown(path, 0, 65534)
            rows.append({"path": relative, "origin": "verifier:" + relative, "archive_mode": 0o777,
                         "kind": "symlink", "uid": 0, "gid": 65534, "target": "lib"})
        elif path.is_file():
            executable = relative in p["verifier_interpreter_entries"]
            os.chown(path, 0, 65534); os.chmod(path, 0o550 if executable else 0o440)
            rows.append(independent.file_row(path, relative, "verifier:" + relative, None, executable, budget))
    freeze_directories(verifier)
    return rows


def materialize(repo, private, root, p, sources, budget):
    ip = independent.intake.load_profile(repo)
    inputs = root / "inputs"; inputs.mkdir(mode=0o700)
    rows = []
    for role, filename in {**independent.ARCHIVE_FILES, "bootstrap": "bootstrap.tar.gz"}.items():
        e = p["bootstrap"] if role == "bootstrap" else p["inputs"][role]
        rows.append(projected_copy(private["path"] / filename, inputs / filename,
            {"size_bytes": e["archive_size_bytes"], "sha256": e["archive_sha256"]}, "input:" + role, filename, budget))
    freeze_directories(inputs)
    with independent.archived.capture_archive(private["path"] / "capture.zip", ip, budget) as capture, io.Archive(
            private["path"] / "capsule.zip", maximum_bytes=p["inputs"]["capsule"]["archive_size_bytes"],
            max_members=p["capsule_members"], member_bytes=ip["limits"]["capsule_member_bytes"],
            expanded_bytes=p["capsule_expanded_bytes"], deadline=budget, allow_runtime_link=True,
            expected_sha256=p["inputs"]["capsule"]["archive_sha256"]) as capsule:
        docs, _ = independent.archived.verify_capture(capture, ip)
        independent.archived.compare_subject(repo, capture, capsule, {"release_subject": p["inputs"]["capsule"]}, ip, docs)
        capsule_rows = extract_projection(capsule, root / "capsule", "capsule", p["interpreter_entries"], budget)
        historical_rows = extract_projection(capture, root / "historical", "historical", (), budget)
    source = root / "source"; source.mkdir(mode=0o700)
    source_rows = [projected_copy(repo / r["path"], source / r["path"], r, "source:" + r["path"], r["path"], budget)
                   for r in sources]
    freeze_directories(source)
    verifier_rows = private["verifier_rows"]
    projection = {"record_type": "q2_tokenizer_projection_v0", "trees": {
        "inputs": rows, "capsule": capsule_rows, "source": source_rows,
        "historical": historical_rows, "verifier": verifier_rows}}
    independent.check_projection(root, projection, p, budget)
    return projection, docs


class OccurrenceFailure(ValueError):
    def __init__(self, code, observation):
        self.code = code if code in io.ERROR_CODES else "q2_replay_rejected"
        super().__init__(self.code)
        self.observation = observation


def expose_projection(run_directory):
    """Permit descriptor-walking readers without exposing collector payloads."""
    private, root = run_directory / "private", run_directory / "projection"
    io.require(set(p.name for p in run_directory.iterdir()) == {"private", "projection"},
               "q2_file_rejected")
    for path in (run_directory, private, root):
        io.require(path.is_dir() and not path.is_symlink(), "q2_file_rejected")
    io.require(stat.S_IMODE(private.stat().st_mode) == 0o700, "q2_file_rejected")
    os.chown(private, 0, 0)
    # _open_regular opens every ancestor O_RDONLY|O_DIRECTORY|O_NOFOLLOW.
    # Execute-only (0711) is insufficient. Read access to the run directory
    # reveals just these two fixed names; private remains root-only 0700.
    for path in (root, run_directory):
        os.chown(path, 0, 65534); os.chmod(path, 0o550)


def failure_detail(error, fallback="q2_replay_rejected"):
    """Closed diagnostic vocabulary; exception messages never cross this edge."""
    code = getattr(error, "code", None)
    if type(code) is str and code in io.ERROR_CODES:
        return {"error_code": code, "reason": code}
    known = {"external_deadline_expired", "protocol_output_bound", "cleanup_unit_shape",
             "capture_cleanup_property_shape", "capture_cleanup_observation_missing",
             "capture_service_not_inactive", "capture_cleanup_cgroup_changed",
             "capture_cgroup_not_empty", "capture_client_not_reaped"}
    reason = error.args[0] if isinstance(error, native.NativeQualificationError) and len(error.args) == 1 else None
    return {"error_code": fallback, "reason": reason if type(reason) is str and reason in known else "unknown"}


def child_error_code(path):
    """A bounded, non-authoritative hint; never publish raw child stderr."""
    try:
        raw = io.read_file(path, 128 * 1024)
        allowed = {code.encode("ascii"): code for code in io.ERROR_CODES}
        matches = {allowed[line] for line in raw.splitlines() if line in allowed}
        return next(iter(matches)) if len(matches) == 1 else "unknown"
    except Exception:
        return "unknown"


def complete_expected(service, expected_exit, budget):
    """Exit 1 is allowed only for the predeclared negative metric builder."""
    deadline = min(service.deadline, service.runtime_deadline_ns / 1e9, budget.end)
    tail = service.reader.finish(deadline)
    io.require(len(tail) <= 128 * 1024, "q2_archive_limit")
    left = deadline - time.monotonic(); io.require(left > 0, "q2_timeout")
    rc = service.process.wait(timeout=left)
    # Keep the actual terminal exit even when it fails the declared contract.
    # A later cleanup kill/wait must not be mistaken for this completed exit.
    service.completed_exit_code = rc
    io.require(type(expected_exit) is int and expected_exit in (0, 1) and rc == expected_exit,
               "q2_replay_rejected")
    return tail, rc


def cleanup_seconds(budget):
    """One shared grace deadline, never a fresh 180 seconds for every cleanup."""
    remaining = budget.end + 180 - time.monotonic()
    io.require(remaining > 0, "q2_cleanup_failed")
    return min(180, remaining)


def freeze_output(work, handoff, declared, tail, p, budget):
    if declared["id"] == "summary_checker":
        obj = io.strict_json(tail, 128 * 1024)
        io.require(io.encode(obj) == io.encode({"ok": True, "recomputed_pass": False, "authority_effect": "none",
                           "production_gate_eligible": False}), "q2_summary_mismatch")
        io.write_new(work / "summary-check.json", io.encode(obj))
    else:
        io.require(tail == b"", "q2_replay_rejected")
    expected_names = set(declared["outputs"])
    # No raw stdout/environment is published. Only these exact files cross the
    # producer/consumer boundary; extra outputs or aliases reject the occurrence.
    io.require({f.name for f in work.iterdir()} == expected_names, "q2_file_rejected")
    handoff.mkdir(mode=0o700)
    outputs = {}
    for name in declared["outputs"]:
        raw = io.read_file(work / name, 16 * 1024 * 1024, deadline=budget)
        if name in p["historical_output_sha256"]:
            io.require(io.digest(raw) == p["historical_output_sha256"][name], "q2_summary_mismatch")
        io.write_new(handoff / name, raw); os.chown(handoff / name, 0, 65534); os.chmod(handoff / name, 0o440)
        outputs[name] = io.digest(raw)
    freeze_directories(handoff)
    return outputs


def run_occurrence(root, private, declared, projection, pre, p, budget):
    work = root / "work" / declared["id"]
    work.mkdir(mode=0o700); os.chown(work, 65534, 65534)
    input_bindings = []
    for row in declared["input_bindings"]:
        path = root / ("control" if row["producer"] == "supervisor" else "handoff/" + row["producer"]) / row["name"]
        raw = io.read_file(path, 16 * 1024 * 1024, row["sha256"], budget)
        input_bindings.append({**row, "sha256": io.digest(raw)})
    independent.check_projection(root, projection, p, budget)
    service, error, cleanup, record = None, None, None, None
    cleanup_error, cleanup_verified = None, False
    phase = "startup"
    log = private / (declared["id"] + ".stderr")
    try:
        prefix = "pulse-q2-" + uuid.uuid4().hex[:24]
        service = ObservedService.__new__(ObservedService)
        service.__init__(prefix, declared["stage"], declared["argv"], work,
            root / "verifier/bin/python", log, budget.end)
        phase = "completion"
        tail, rc = complete_expected(service, declared["expected_exit"], budget)
        exit_ns = time.monotonic_ns()
        record = {"id": declared["id"], "status": "completed", "argv": declared["argv"],
            "expected_exit": declared["expected_exit"], "exit_code": rc, "unit": service.unit,
            "pid": service.observation["pid"], "launch_ns": service.runtime_deadline_ns - 180_000_000_000,
            "isolation_observed_ns": service.isolation_observed_ns,
            "exec_ns": service.exec_ns, "exit_ns": exit_ns, "stdout_eof": service.reader.eof,
            "isolation": service.observation, "input_bindings": input_bindings}
    except BaseException as exc:
        error = exc
    finally:
        # A separate finite grace prevents expiry/cancellation from skipping the
        # cgroup/client closure. A lost host cannot create verified cleanup.
        if service is not None:
            try:
                with phase_boundary(cleanup_seconds(budget)):
                    cleanup = native.close_capture_service(service)
                    cleanup_path = independent.TOOLS + "check_q2_reference_capture_v0.py"
                    cleanup_sha = next(r["sha256"] for r in pre["source_bindings"] if r["path"] == cleanup_path)
                    cleanup_checker = independent.import_bound(root / "source", cleanup_path, cleanup_sha)
                    cleanup_checker.capture_cleanup_check(cleanup, service.unit)
                    cleanup_verified = True
            except BaseException as exc:
                cleanup_error = exc
                if error is None: error, phase = exc, "cleanup"
    try:
        if error is not None: raise error
        phase = "post_execution"
        io.require(record is not None and cleanup_verified, "q2_cleanup_failed")
        record["cleanup"] = cleanup; record["cleanup_ns"] = time.monotonic_ns()
        budget.remaining()
        independent.check_projection(root, projection, p, budget)
        io.require(independent.verify_bootstrap(root / "inputs/bootstrap.tar.gz", p, budget) == pre["bootstrap_lib_sha256"],
                   "q2_replay_environment")
        record["projection_after_sha256"] = io.digest(io.encode(projection))
        phase = "output_freeze"
        record["outputs"] = freeze_output(work, root / "handoff" / declared["id"], declared, tail, p, budget)
        record["output_frozen_ns"] = time.monotonic_ns()
        return record
    except BaseException as exc:
        detail = failure_detail(exc, "q2_cleanup_failed" if phase == "cleanup" else "q2_replay_rejected")
        partial = {"id": declared["id"], "status": "failed", "unit": getattr(service, "unit", None),
                   "pid": getattr(service, "observation", {}).get("pid"),
                   "exec_ns": getattr(service, "exec_ns", None), "stage": declared["stage"],
                   "failure_phase": phase, "failure": detail,
                   "expected_exit": declared["expected_exit"],
                   "exit_code": getattr(service, "completed_exit_code", None),
                   "child_error_code": child_error_code(log),
                   "cleanup": cleanup if cleanup_verified else None, "cleanup_verified": cleanup_verified,
                   "cleanup_error": failure_detail(cleanup_error, "q2_cleanup_failed") if cleanup_error else None}
        raise OccurrenceFailure(detail["error_code"], partial) from None


def atomic_publish(directory, name, raw):
    """Exclusive publication; failed finalization removes this new entry."""
    dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary, published = None, False
    try:
        fd, temporary = tempfile.mkstemp(prefix=".q2-tokenizer-", dir=directory)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), 0o644); os.fsync(stream.fileno())
        os.link(temporary, name, dst_dir_fd=dfd, follow_symlinks=False)
        published = True
        os.unlink(temporary); temporary = None
        os.fsync(dfd)
    except BaseException:
        if published: os.unlink(name, dir_fd=dfd)
        raise
    finally:
        try:
            if temporary is not None: os.unlink(temporary)
        finally: os.close(dfd)


def supervise(repo, environment=None, bootstrap_snapshot=None):
    env = dict(os.environ if environment is None else environment)
    token = env.pop(TOKEN, "")
    for key in tuple(os.environ):
        if key.startswith("PULSE_Q2_"): os.environ.pop(key, None)
    budget = independent.Budget(1200)
    root, private, run_directory, output, binding = None, None, None, None, None
    records = []
    accepted, error, cleaned = None, None, False
    bootstrap_cleaned = bootstrap_snapshot is None
    cleanup_errors = {}
    try:
        with phase_boundary(1200):
            p = independent.load_profile(repo)
            binding, sources, request_raw = authorize(repo, env, budget)
            host = host_record(env, p)  # Unsupported hosts reject before acquisition.
            parent = Path(env.get("RUNNER_TEMP", "")).absolute()
            io.require(parent.is_dir() and not any(q.is_symlink() for q in (parent, *parent.parents)) and
                       parent != repo and repo not in parent.parents and
                       shutil.disk_usage(Path("/var/lib")).free >= 8 * 1024**3, "q2_file_rejected")
            destination = parent / "q2-native-tokenizer"; destination.mkdir(mode=0o755)
            output = destination
            run_directory = Path(tempfile.mkdtemp(prefix="pulse-q2-tokenizer-", dir="/var/lib"))
            os.chmod(run_directory, 0o700)
            private = run_directory / "private"; private.mkdir(mode=0o700)
            root = run_directory / "projection"; root.mkdir(mode=0o700)
            client = io.GitHubArtifactTransport(token)
            binding = authenticate_current(client, binding, budget)
            for role, filename in independent.ARCHIVE_FILES.items():
                transport.download_artifact(client, p["inputs"][role], private / filename, budget)
            pub = transport.load_profile(repo)
            transport.download_bootstrap(pub["bootstrap"], private / "bootstrap.tar.gz", budget)
            transport.download_bootstrap(pub["pip"], private / pub["pip"]["filename"], budget)
            del client; token = None
            bootstrap_lib = prepare_bootstrap_library(private, p, budget)
            prepared = {"repo": repo, "path": private}
            prepared["verifier_rows"] = prepare_verifier(prepared, root, p, budget)
            independent.bind_collector_dependencies(root / "verifier", prepared["verifier_rows"], p, budget)
            projection, docs = materialize(repo, prepared, root, p, sources, budget)
            projection_raw = io.encode(projection)
            pre = {"record_type": "q2_tokenizer_prelaunch_v0", "scope": independent.SCOPE,
                "binding": binding, "source_bindings": sources, "request_sha256": io.digest(request_raw),
                "inputs": p["inputs"], "projection_root": str(root), "projection_sha256": io.digest(projection_raw),
                "bootstrap_lib_sha256": bootstrap_lib,
                "occurrences": independent.execution_plan(root, io.digest(projection_raw), p),
                "phase_start_ns": budget.start_ns, "phase_deadline_ns": budget.start_ns + 1200_000_000_000,
                "claims": independent.CLAIMS}
            control = root / "control"; control.mkdir(mode=0o700)
            for name, raw in (("request.json", request_raw), ("prelaunch.json", io.encode(pre)), ("projection.json", projection_raw)):
                io.write_new(control / name, raw); os.chown(control / name, 0, 65534); os.chmod(control / name, 0o440)
            freeze_directories(control)
            for name in ("work", "handoff"):
                (root / name).mkdir(mode=0o550); os.chown(root / name, 0, 65534)
            expose_projection(run_directory)
            independent.check_prelaunch(root / "source", pre, request_raw, projection_raw, p)
            for declared in pre["occurrences"]:
                records.append(run_occurrence(root, private, declared, projection, pre, p, budget))
            old = docs["capture-subject.json"]["platform"]
            requirements = {k: old[k] for k in p["platform_keys"]}
            accepted = {"schema_version": "q2_release_host_tokenizer_result_v0", "status": "native_tokenizer_verified",
                "scope": independent.SCOPE, "binding": binding, "source_bindings": sources, "inputs": p["inputs"],
                "request_sha256": io.digest(request_raw), "prelaunch_sha256": io.digest(io.encode(pre)),
                "projection_sha256": io.digest(projection_raw), "phase_start_ns": pre["phase_start_ns"],
                "phase_deadline_ns": pre["phase_deadline_ns"], "occurrences": records, "host": host,
                "archived_platform_requirements": requirements, "platform_matches": {k: host[k] == requirements[k] for k in requirements},
                "full_archived_platform_match": all(host[k] == requirements[k] for k in requirements),
                "metrics": p["historical_metrics"], "claims": independent.CLAIMS, "cleanup": "verified_removed",
                "independent_check": "evidence_reconstructed", "clock_relation": "not_verified", "resource_measurement": "unavailable"}
            # Private candidate only. Publishing the accepted result is deferred
            # until independent replay and deletion verification have succeeded.
            candidate = private / "candidate"; candidate.mkdir(mode=0o700)
            for name in independent.PUBLIC_FILES:
                if name == "result.json": raw = io.encode(accepted)
                elif name in ("request.json", "prelaunch.json", "projection.json"): raw = io.read_file(control / name, 16 * 1024 * 1024)
                else:
                    stage = "input_check" if name == "input-check.json" else "tokenizer_check"
                    raw = io.read_file(root / "handoff" / stage / name, 128 * 1024)
                io.write_new(candidate / name, raw)
            # Independent deterministic validation is collector work, outside the
            # four subject totals. It never repeats or claims kernel acquisition.
            independent.validate_receipt(repo, candidate, root / "inputs")
            io.require(independent.source_closure(repo, binding["source_commit"], budget) == sources, "q2_source_mismatch")
            for name in independent.PUBLIC_FILES:
                if name != "result.json":
                    atomic_publish(output, name, io.read_file(candidate / name, 16 * 1024 * 1024))
    except BaseException as exc:
        error = exc
    finally:
        token = None
        if run_directory is not None:
            try:
                with phase_boundary(cleanup_seconds(budget)):
                    shutil.rmtree(run_directory)
                    io.require(not os.path.lexists(run_directory), "q2_cleanup_failed")
                    cleaned = True
            except BaseException as exc:
                cleanup_errors["run_directory"] = failure_detail(exc, "q2_cleanup_failed")
                if error is None: error = io.IntakeError("q2_cleanup_failed")
        if bootstrap_snapshot is not None:
            try:
                with phase_boundary(cleanup_seconds(budget)):
                    shutil.rmtree(bootstrap_snapshot)
                    io.require(not os.path.lexists(bootstrap_snapshot), "q2_cleanup_failed")
                    bootstrap_cleaned = True
            except BaseException as exc:
                cleanup_errors["bootstrap_snapshot"] = failure_detail(exc, "q2_cleanup_failed")
                if error is None: error = io.IntakeError("q2_cleanup_failed")
    if error is None:
        try:
            io.require(accepted is not None and cleaned and bootstrap_cleaned, "q2_cleanup_failed")
            atomic_publish(output, "result.json", io.encode(accepted))
        except BaseException as exc:
            error = exc
        else:
            return accepted
    if output is not None:
        service_cleanup_verified = not isinstance(error, OccurrenceFailure) or error.observation.get("cleanup_verified") is True
        diagnostic = {"record_type": "q2_native_tokenizer_failure_v0", "status": "rejected",
            "error_code": error.code if isinstance(error, (io.IntakeError, OccurrenceFailure)) else "q2_replay_rejected",
            "cleanup": "verified_removed" if cleaned and bootstrap_cleaned and service_cleanup_verified else "not_verified",
            "directory_cleanup": {"run_directory": "not_created" if run_directory is None else "verified_removed" if cleaned else "not_verified",
                                  "bootstrap_snapshot": "not_required" if bootstrap_snapshot is None else "verified_removed" if bootstrap_cleaned else "not_verified"},
            "cleanup_errors": cleanup_errors,
            "occurrences": [{"id": n, "status": "completed" if i < len(records) else "not_started"}
                            for i, n in enumerate(independent.OCCURRENCES)], "claims": independent.CLAIMS}
        if isinstance(error, OccurrenceFailure):
            diagnostic["occurrences"][len(records)] = error.observation
        try: atomic_publish(output, "failure.json", io.encode(diagnostic))
        except Exception: pass  # No accepted receipt can result from a failed publication.
    raise error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = None
    try:
        repo = args.repo_root.resolve(strict=True)
        snapshot = bootstrap_sources(repo, dict(os.environ))
        initialize_modules(snapshot)
        supervise(repo, bootstrap_snapshot=snapshot)
        snapshot = None
        print("q2_native_tokenizer_verified_historical_metric_fail")
        return 0
    except Exception as exc:
        code = getattr(exc, "code", "q2_source_mismatch")
        print(code if code in (io.ERROR_CODES if io is not None else {"q2_source_mismatch", "q2_context_rejected"})
              else "q2_source_mismatch", file=sys.stderr)
        return 2
    finally:
        if snapshot is not None:
            try: shutil.rmtree(snapshot)
            except OSError: pass


if __name__ == "__main__":
    raise SystemExit(main())
