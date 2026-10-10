#!/usr/bin/env python3
"""Private, bounded reconstruction of historical bytes; never execute the payload."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import urllib.parse
import venv
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io
import check_q2_release_capsule_publication_v0 as publication


def binding(path, expected, deadline):
    io.require(io.file_binding(path, expected["archive_size_bytes"], deadline) ==
               {k: expected[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")


def unpack_bootstrap(archive, destination, expected, limits, deadline):
    """Verify compressed identity, bound TAR parsing, validate every path before writes."""
    fd, before = io._open_regular(archive)
    try:
        with os.fdopen(fd, "rb", closefd=False) as stream:
            # Hash and parse the same held descriptor. A pathname re-open here
            # would permit replacement after the original digest was checked.
            io.require(before.st_size == expected["archive_size_bytes"], "q2_digest_mismatch")
            hashed, size = hashlib.sha256(), 0
            while True:
                deadline.remaining()
                raw = stream.read(65536)
                if not raw:
                    break
                size += len(raw)
                io.require(size <= before.st_size, "q2_unstable_input")
                hashed.update(raw)
            io.require(size == before.st_size and hashed.hexdigest() == expected["archive_sha256"] and
                       io._identity(before) == io._identity(os.fstat(fd)), "q2_digest_mismatch")
            stream.seek(0)
            _extract_bootstrap(stream, fd, before, destination, limits, deadline)
            io.require(io._identity(before) == io._identity(archive.stat(follow_symlinks=False)),
                       "q2_unstable_input")
    finally:
        os.close(fd)
    raw = io.read_file(destination / "bin/python3.11", 1024 * 1024, expected["interpreter_sha256"], deadline)
    io.require(bool(raw), "q2_subject_mismatch")


def _extract_bootstrap(stream, fd, before, destination, limits, deadline):
    """Only called with the descriptor whose compressed bytes were verified."""
    with tarfile.open(fileobj=stream, mode="r:gz") as tar:
        rows, names, total = [], set(), 0
        # next() bounds the member count before getmembers() could allocate it all.
        for member in tar:
            deadline.remaining()
            io.require(len(rows) < limits["bootstrap_members"], "q2_archive_limit")
            name = member.name[2:] if member.name.startswith("./") else member.name
            if name in ("", "."):
                io.require(member.isdir(), "q2_archive_rejected")
                name = "."
            else:
                name = name.rstrip("/") if member.isdir() else name
                # The pinned CPython TAR has three ordinary filenames with
                # spaces. Keep the ZIP profile unchanged; validate TAR names
                # independently, with no normalization of traversal/aliases.
                io.require(0 < len(name) <= 1024 and all(32 <= ord(c) < 127 for c in name) and
                           "\\" not in name and ":" not in name and
                           all(part not in ("", ".", "..") for part in name.split("/")),
                           "q2_archive_rejected")
            io.require(name not in names and (member.isfile() or member.isdir() or member.issym()) and
                       not member.mode & 0o7000 and 0 <= member.size <= limits["bootstrap_member_bytes"] and
                       not member.pax_headers, "q2_archive_rejected")
            if member.issym():
                io.require(member.size == 0 and "/" not in member.linkname and
                           io.safe_member(member.linkname) == member.linkname, "q2_archive_rejected")
            names.add(name)
            total += member.size
            io.require(total <= limits["bootstrap_expanded_bytes"], "q2_archive_limit")
            rows.append((name, member))
        io.require(len(rows) == limits["bootstrap_members"] and
                   total == limits["bootstrap_expanded_bytes"], "q2_archive_limit")
        kinds = {name: m for name, m in rows}
        for name, m in rows:
            for parent in Path(name).parents:
                if str(parent) != ".":
                    io.require(str(parent) in kinds and kinds[str(parent)].isdir(), "q2_archive_rejected")
            if m.issym():
                target = (Path(name).parent / m.linkname).as_posix()
                io.require(target in kinds and kinds[target].isfile(), "q2_archive_rejected")
        destination.mkdir(mode=0o700)
        for name, m in sorted(rows, key=lambda row: (len(Path(row[0]).parts), row[0])):
            if name == ".":
                continue
            if m.isdir():
                (destination / name).mkdir(mode=0o700)
        # Read compressed payloads in original TAR order. Sorting reads
        # would repeatedly rewind gzip and exhaust the bounded deadline.
        for name, m in rows:
            deadline.remaining()
            p = destination / name
            if m.isdir():
                continue
            if m.issym():
                p.symlink_to(m.linkname)
            else:
                raw = tar.extractfile(m).read(m.size + 1)
                io.require(len(raw) == m.size, "q2_archive_rejected")
                io.write_new(p, raw)
                p.chmod(m.mode & 0o777)
        io.require(io._identity(before) == io._identity(os.fstat(fd)), "q2_unstable_input")


def clean_caches(root):
    for p in sorted(root.rglob("*"), reverse=True):
        if p.is_file() and p.suffix in (".pyc", ".pyo"):
            p.unlink()
        elif p.is_dir() and p.name == "__pycache__":
            p.rmdir()


def materialize(path, raw, expected, mode):
    io.require(len(raw) == expected["size"] and io.digest(raw) == expected["sha256"], "q2_subject_mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    io.write_new(path, raw)
    path.chmod(mode)


def checked_stream(path, expected, maximum, deadline, *, target=None, check_mode=False):
    """Hash/copy a held regular file without retaining a large runtime member."""
    fd, before = io._open_regular(path)
    try:
        io.require(before.st_size == expected["size"] and 0 <= before.st_size <= maximum,
                   "q2_subject_mismatch")
        if check_mode:
            io.require(stat.S_IMODE(before.st_mode) == expected["mode"], "q2_subject_mismatch")
        hashed, size = hashlib.sha256(), 0
        while True:
            deadline.remaining()
            raw = os.read(fd, 65536)
            if not raw:
                break
            size += len(raw)
            io.require(size <= before.st_size, "q2_unstable_input")
            hashed.update(raw)
            if target is not None:
                target.write(raw)
        io.require(size == expected["size"] and hashed.hexdigest() == expected["sha256"] and
                   io._identity(before) == io._identity(os.fstat(fd)), "q2_subject_mismatch")
    finally:
        os.close(fd)


def pack(stage, expected, destination, profile, deadline):
    """Sorted stable files, explicit compression level, modes and fixed timestamp."""
    names = {p.relative_to(stage).as_posix(): p for p in stage.rglob("*") if p.is_file() or p.is_symlink()}
    io.require(set(names) == set(expected), "q2_subject_mismatch")
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=False) as archive:
        for name in sorted(expected):
            deadline.remaining()
            e, p = expected[name], names[name]
            info = zipfile.ZipInfo(name, tuple(profile["packing"]["date_time"]))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info._compresslevel = 6  # ZipInfo's explicit Python 3.11 write level.
            info.extra = info.comment = b""
            if "symlink" in e:
                io.require(name == "runtime/lib64" and e["symlink"] == "lib" and
                           p.is_symlink() and os.readlink(p) == "lib", "q2_subject_mismatch")
                raw, mode = b"lib", stat.S_IFLNK | 0o777
                info.external_attr = mode << 16
                archive.writestr(info, raw, compresslevel=6)
            else:
                info.external_attr = (stat.S_IFREG | e["mode"]) << 16
                info.file_size = e["size"]
                with archive.open(info, "w") as target:
                    checked_stream(p, e, profile["limits"]["capsule_member_bytes"], deadline,
                                   target=target, check_mode=True)
    binding(destination, profile["capsule"], deadline)


def reconstruct(repo, private, profile, deadline):
    io.require(publication.environment_record()["python"] == "3.11.16" and
               publication.environment_record()["unicode"] == "14.0.0", "q2_replay_environment")
    io.read_file(Path(sys.executable).resolve(), 1024 * 1024,
                 profile["bootstrap"]["interpreter_sha256"], deadline)
    for key, filename in (("capture", "capture.zip"), ("preparation", "preparation.zip"),
                           ("pip", profile["pip"]["filename"])):
        binding(private / filename, profile[key], deadline)
    pip_wheel = private / profile["pip"]["filename"]
    sys.path.insert(0, str(pip_wheel))
    from pip._internal.operations.install import wheel as pip_install
    from pip._internal.models.scheme import Scheme
    import pip
    io.require(pip.__version__ == "24.0", "q2_source_mismatch")
    p = publication.intake.load_profile(repo)
    limits = profile["limits"]
    with io.Archive(private / "capture.zip", maximum_bytes=profile["capture"]["archive_size_bytes"],
                    max_members=p["capture_members"], member_bytes=p["limits"]["capture_member_bytes"],
                    expanded_bytes=p["limits"]["capture_expanded_bytes"], deadline=deadline,
                    expected_sha256=profile["capture"]["archive_sha256"]) as capture, \
         io.Archive(private / "preparation.zip", maximum_bytes=profile["preparation"]["archive_size_bytes"],
                    max_members=limits["preparation_members"], member_bytes=limits["member_bytes"],
                    expanded_bytes=limits["preparation_expanded_bytes"], deadline=deadline,
                    expected_sha256=profile["preparation"]["archive_sha256"]) as prep:
        inventory = io.strict_json(capture.read("installation.json"))["inventory"]
        io.require(len(inventory) == p["runtime_regular_files"] + 1, "q2_subject_mismatch")
        subject = io.strict_json(capture.read("capture-subject.json"))
        report = io.strict_json(capture.read("pip-report.json"))
        old_stage = str(Path(urllib.parse.unquote(urllib.parse.urlsplit(
                        report["install"][0]["download_info"]["url"]).path)).parents[3])
        old_venv = old_stage + "/install/venv"
        # Historical paths are data for script/metadata byte reconstruction only.
        stage = private / "candidate"
        stage.mkdir(mode=0o700)
        runtime = stage / "runtime"
        venv.EnvBuilder(with_pip=False, symlinks=False).create(runtime)
        base_lib = runtime / "lib/python3.11/site-packages"
        def scheme(name):
            return Scheme(platlib=str(base_lib), purelib=str(base_lib),
                          headers=str(runtime / "include/site/python3.11" / name),
                          scripts=str(runtime / "bin"), data=str(runtime))
        pip_install.PipScriptMaker.executable = old_venv + "/bin/python3.11"
        pip_install.install_wheel("pip", str(pip_wheel), scheme("pip"), "bootstrap pip",
                                 pycompile=True, warn_script_location=False, requested=True)
        clean_caches(runtime)
        for name in ("bin/activate", "bin/activate.csh", "bin/activate.fish", "bin/Activate.ps1", "pyvenv.cfg"):
            path = runtime / name
            raw = io.read_file(path, 128 * 1024).replace(str(runtime).encode(), old_venv.encode())
            raw = raw.replace(str(Path(sys.base_prefix)).encode(), b"/opt/hostedtoolcache/Python/3.11.16/x64")
            if name.startswith("bin/activate"):
                raw = raw.replace(b"(runtime) ", b"(venv) ")
            if name == "pyvenv.cfg":
                raw = raw.replace(b" --without-pip", b"")
            path.write_bytes(raw)
        wheels = private / "wheelhouse"
        wheels.mkdir(mode=0o700)
        preparation = io.strict_json(prep.read("q2-runtime-preparation/preparation.json"))
        io.require(len(preparation["wheels"]) == 30, "q2_subject_mismatch")
        pip_install.PipScriptMaker.executable = old_venv + "/bin/python"
        for row in preparation["wheels"]:
            deadline.remaining()
            raw = prep.read("q2-runtime-preparation/" + io.safe_member(row["path"]), limits["member_bytes"])
            path = wheels / Path(row["path"]).name
            materialize(path, raw, row, 0o600)
            # Installation is non-executing; archived packages never enter sys.path.
            pip_install.install_wheel(row["name"], str(path), scheme(row["name"]), row["name"],
                                     pycompile=False, warn_script_location=False, direct_url=None, requested=True)
        expected = {}
        for row in subject["model_files"]:
            name = io.safe_member(row["path"])
            materialize(stage / name, prep.read("q2-runtime-preparation/" + name, limits["member_bytes"]),
                        row, p["model_capsule_mode"])
            expected[name] = {**row, "mode": p["model_capsule_mode"]}
        for name in p["source_components"]:
            raw = capture.read("source/" + name)
            row = {"size": len(raw), "sha256": io.digest(raw), "mode": p["source_archive_mode"]}
            materialize(stage / "source" / name, raw, row, row["mode"])
            expected["source/" + name] = row
        clean_caches(runtime)
        for row in inventory:
            name = io.safe_member(row["path"])
            path = runtime / name
            io.require("runtime/" + name not in expected, "q2_subject_mismatch")
            if "symlink" in row:
                io.require(row == {"path": "lib64", "symlink": "lib"} and path.is_symlink() and
                           os.readlink(path) == "lib", "q2_subject_mismatch")
            else:
                checked_stream(path, row, limits["capsule_member_bytes"], deadline)
                io.require(not row["mode"] & 0o7000, "q2_subject_mismatch")
                path.chmod(row["mode"])
            expected["runtime/" + name] = row
        manifest = {"record_type": "q2_release_subject_capsule_v0", "subject_id": p["subject_id"],
                    "definition_sha256": p["definition_sha256"],
                    "capture_subject_sha256": p["capture_expectation"]["subject_sha256"],
                    "layout_profile": p["layout_profile"],
                    "configuration": {k: subject[k] for k in ("effective_generation", "runtime")},
                    "launch": p["launch"], "platform_scope": {
                        "requirements": {k: subject["platform"][k] for k in p["platform_requirement_keys"]},
                        "release_host_verification": "not_observed"}}
        raw = io.encode(manifest)
        io.write_new(stage / "capsule.json", raw)
        expected["capsule.json"] = {"size": len(raw), "sha256": io.digest(raw), "mode": 0o600}
    pack(stage, expected, private / "capsule.zip", profile, deadline)
    io.write_new(private / "packing-environment.json", io.encode(publication.environment_record()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--reconstruct", action="store_true")
    args = parser.parse_args()
    try:
        io.require(not any(k.startswith("PULSE_Q2_") for k in os.environ), "q2_context_rejected")
        repo = args.repo_root.resolve(strict=True)
        private = io.check_private_directory(repo, args.private_input)
        with io.interrupt_boundary(700) as deadline:
            p = publication.load_profile(repo)
            context = io.strict_json(io.read_file(private / "build-context.json", 128 * 1024))
            io.require(publication.source_closure(repo, context["binding"]["source_commit"]) ==
                       context["source_bindings"], "q2_source_mismatch")
            if args.reconstruct:
                reconstruct(repo, private, p, deadline)
            else:
                bootstrap = private / "bootstrap"
                unpack_bootstrap(private / p["bootstrap"]["filename"], bootstrap, p["bootstrap"], p["limits"], deadline)
                env = io.replay_environment(private)
                env["LD_LIBRARY_PATH"] = str(bootstrap / "lib")
                rc = io.private_process([str(bootstrap / "bin/python3.11"), "-I", "-B", str(repo / publication.BUILDER),
                                         "--repo-root", str(repo), "--private-input", str(private), "--reconstruct"],
                                        cwd=private, environment=env, timeout=deadline.remaining(650))
                io.require(rc == 0, "q2_subject_mismatch")
        return 0
    except Exception as exc:
        print(exc.code if isinstance(exc, io.IntakeError) else "q2_internal_error")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
