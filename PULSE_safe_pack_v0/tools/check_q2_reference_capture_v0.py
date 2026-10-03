#!/usr/bin/env python3
"""Separately verify Q2 prepared runtime candidates; capture is not implemented.

No import or invocation of the acquisition producer is used. Verification needs
an externally supplied preparation-file digest, exact source commit and run ID.
Its verdict is only about staged candidate bytes and offline wheel resolution.
It never proves native model execution, release-artifact binding or Q2 admission.
"""
from __future__ import annotations

import argparse
import email.parser
import hashlib
import html.parser
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile

REPO = "HKati/pulse-release-gates-0.1"
WF = ".github/workflows/q2_reference_acquisition_v0.yml"
PRODUCER_PATH = "PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py"
CHECKER_PATH = "PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py"
SELECTION_PATH = "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json"
REQUESTS_PATH = "PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json"
SOURCES = (WF, PRODUCER_PATH, CHECKER_PATH, SELECTION_PATH, REQUESTS_PATH)
FIXED_SELECTION_SHA = "e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e"
FIXED_REQUESTS_SHA = "fa0412c6a702e220e5d0c8b09a5e854fe35ac89d4801977eeee0f2a6e5cae997"
MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_REV = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
FIXED_WEIGHTS_SHA = "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"
MODEL_NAMES = {"config.json", "generation_config.json", "merges.txt", "model.safetensors",
               "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.json"}
TORCH_NAME = "torch-2.8.0+cpu-cp311-cp311-manylinux_2_28_x86_64.whl"
ROOT_VERSIONS = {"torch": "2.8.0+cpu", "transformers": "4.57.6", "rfc8785": "0.1.4", "jsonschema": "4.25.1"}
EXPECTED_STATE = {"authority_effect": "none", "production_gate_eligible": False,
                  "inference_executed": False, "native_runtime_qualified": False,
                  "materialized_subject_bound": False, "capture_dispatch_authorized": False,
                  "dependency_closure_status": "staged_review_candidate"}
ORIGIN = "owner_dispatched_github_preparation"
JSON_LIMIT = 16 * 1024 * 1024
FILE_LIMIT = 512 * 1024 * 1024
TOTAL_LIMIT = 1536 * 1024 * 1024


class CheckError(ValueError):
    pass


def expect(test, code):
    if not test: raise CheckError(code)


def sha256(data): return hashlib.sha256(data).hexdigest()


def load_json(raw):
    expect(len(raw) <= JSON_LIMIT and not raw.startswith(b"\xef\xbb\xbf"), "json_size_or_bom")
    def pairs(values):
        keys = [k for k, _ in values]
        expect(len(keys) == len(set(keys)), "duplicate_property")
        return dict(values)
    def constant(_): raise CheckError("non_finite_number")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        def strings(value, depth=0):
            expect(depth <= 64, "excessive_depth")
            if type(value) is str: value.encode("utf-8")
            elif type(value) is float: expect(math.isfinite(value), "non_finite_number")
            elif type(value) is list:
                for item in value: strings(item, depth + 1)
            elif type(value) is dict:
                for key, item in value.items(): strings(key, depth + 1); strings(item, depth + 1)
        strings(obj)
        return obj
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CheckError("malformed_json") from exc


def json_file_bytes(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def keys(obj, names, code):
    expect(type(obj) is dict and set(obj) == set(names.split()), code)


def valid_path(name):
    expect(type(name) is str and 0 < len(name) <= 240 and "\\" not in name and ":" not in name,
           "invalid_relative_path")
    parsed = PurePosixPath(name)
    expect(not parsed.is_absolute() and parsed.as_posix() == name and all(x not in (".", "..")
           for x in name.split("/")) and "//" not in name, "invalid_relative_path")
    return parsed


def bytes_at(root, name, limit=FILE_LIMIT):
    parsed = valid_path(name)
    path = root
    for part in parsed.parts:
        path = path / part
        expect(not path.is_symlink(), "symlink_forbidden")
    st = path.lstat()
    expect(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size <= limit, "file_kind_or_size")
    with path.open("rb") as stream: data = stream.read(limit + 1)
    expect(len(data) == st.st_size, "unstable_file")
    return data


def git_blob(repo_root, commit, relative):
    command = ["/usr/bin/git", "--no-replace-objects", "-c", "protocol.allow=never",
               "-c", "core.hooksPath=/dev/null", "-C", str(repo_root), "cat-file", "blob",
               f"{commit}:{relative}"]
    proc = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=30,
                          env={"PATH": os.defpath, "HOME": str(repo_root), "LANG": "C.UTF-8"})
    expect(proc.returncode == 0, "source_commit_unavailable")
    return proc.stdout


def normalize_name(name):
    expect(type(name) is str and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name), "invalid_package_name")
    return re.sub(r"[-_.]+", "-", name).lower()


def wheel_metadata(path):
    with zipfile.ZipFile(path) as archive:
        contents = archive.infolist()
        expect(len(contents) <= 50000 and len({x.filename for x in contents}) == len(contents), "wheel_duplicates")
        for info in contents:
            p = PurePosixPath(info.filename)
            expect(not p.is_absolute() and ".." not in p.parts and "\\" not in info.filename,
                   "wheel_traversal")
        records = [x for x in contents if x.filename.endswith(".dist-info/METADATA")
                   and len(PurePosixPath(x.filename).parts) == 2]
        expect(len(records) == 1 and records[0].file_size <= JSON_LIMIT, "wheel_metadata_missing")
        msg = email.parser.BytesParser().parsebytes(archive.read(records[0]), headersonly=True)
    expect(len(msg.get_all("Name", [])) == len(msg.get_all("Version", [])) == 1, "wheel_identity_ambiguous")
    name = normalize_name(msg["Name"]); version = msg["Version"]
    expect(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.+!-]*", version), "invalid_package_version")
    expect(not name.startswith(("nvidia-", "cuda-")) and name not in {"triton", "torchvision", "torchaudio"},
           "non_selected_dependency")
    expect(all("@" not in x and "://" not in x for x in msg.get_all("Requires-Dist", [])),
           "url_dependency_forbidden")
    expect(normalize_name(path.name.split("-", 1)[0]) == name, "wheel_distribution_mismatch")
    return name, version


def verify_tokens(root):
    for filename in ("config.json", "generation_config.json"):
        config = load_json(bytes_at(root, "model/" + filename, JSON_LIMIT))
        expect(type(config) is dict, "invalid_model_configuration")
        expect(all(type(config.get(key)) is int and config[key] == val
                   for key, val in {"bos_token_id": 1, "eos_token_id": 2, "pad_token_id": 2}.items()),
               "model_token_configuration_mismatch")
    tokenizer_cfg = load_json(bytes_at(root, "model/tokenizer_config.json", JSON_LIMIT))
    for name, target in {"bos_token": "<|im_start|>", "eos_token": "<|im_end|>",
                         "pad_token": "<|im_end|>"}.items():
        value = tokenizer_cfg.get(name)
        actual = value.get("content") if type(value) is dict else value
        expect(actual == target, "tokenizer_special_token_mismatch")
    expect(type(tokenizer_cfg.get("chat_template")) is str and bool(tokenizer_cfg["chat_template"]),
           "missing_chat_template")
    tk = load_json(bytes_at(root, "model/tokenizer.json", JSON_LIMIT))
    expect(type(tk.get("added_tokens")) is list, "missing_added_tokens")
    for number, text in ((1, "<|im_start|>"), (2, "<|im_end|>")):
        hits = [t for t in tk["added_tokens"] if type(t) is dict and t.get("id") == number]
        expect(len(hits) == 1 and hits[0].get("content") == text and hits[0].get("special") is True,
               "tokenizer_token_id_mismatch")


def verify_model(root):
    meta = load_json(bytes_at(root, "upstream/model.json", JSON_LIMIT))
    expect(meta.get("sha") == MODEL_REV and meta.get("id", meta.get("modelId")) == MODEL_ID,
           "wrong_model_revision")
    siblings = meta.get("siblings")
    expect(type(siblings) is list and len(siblings) <= 1024, "missing_model_inventory")
    selected = [x for x in siblings if type(x) is dict and x.get("rfilename") in MODEL_NAMES]
    expect(len(selected) == 8 and {x["rfilename"] for x in selected} == MODEL_NAMES, "model_inventory_not_exact")
    rows = []
    for item in sorted(selected, key=lambda x: x["rfilename"]):
        name = item["rfilename"]; path = "model/" + name
        raw = bytes_at(root, path)
        expect(re.fullmatch(r"[a-f0-9]{40}", str(item.get("blobId", ""))), "model_git_blob_missing")
        if item.get("lfs") is not None:
            lfs = item["lfs"]
            expect(type(lfs) is dict and type(lfs.get("size")) is int and len(raw) == lfs["size"],
                   "model_lfs_size_mismatch")
            expect(lfs.get("sha256") == sha256(raw), "model_lfs_digest_mismatch")
        else:
            expect(type(item.get("size")) is int and len(raw) == item["size"], "model_blob_size_mismatch")
            expected_git = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
            expect(item["blobId"] == expected_git, "model_git_blob_mismatch")
        if name == "model.safetensors":
            expect(sha256(raw) == FIXED_WEIGHTS_SHA, "selected_model_weights_changed")
        rows.append({"path": path, "size": len(raw), "sha256": sha256(raw),
                     "upstream_blob_sha1": item["blobId"],
                     "upstream_lfs_sha256": item["lfs"]["sha256"] if item.get("lfs") else None})
    model_map = {"record_type": "q2_reference_model_files_candidate_v0", "model_repository": MODEL_ID,
                 "model_revision": MODEL_REV, "files": rows, "authority_effect": "none",
                 "native_runtime_qualified": False, "adopted": False}
    expect(bytes_at(root, "q2_reference_model_files_v0.json", JSON_LIMIT) == json_file_bytes(model_map),
           "model_map_not_reconstructed")
    verify_tokens(root)


class CPUIndex(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.urls = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            for name, value in attrs:
                if name == "href" and value: self.urls.append(value)


def verify_wheels(root, rows):
    expect(type(rows) is list and 4 <= len(rows) <= 64, "wheel_list_size")
    names = set(); output = []; extras = set()
    for row in rows:
        keys(row, "name version path sha256 size upstream_metadata url", "wheel_record_fields")
        p = valid_path(row["path"])
        expect(len(p.parts) == 2 and p.parts[0] == "wheelhouse" and p.name.endswith(".whl"), "wheel_path_scope")
        expect(re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", p.name), "wheel_path_spelling")
        raw = bytes_at(root, row["path"])
        expect(row["sha256"] == sha256(raw) and type(row["size"]) is int and row["size"] == len(raw),
               "wheel_byte_mismatch")
        name, version = wheel_metadata(root / row["path"])
        expect(row["name"] == name and row["version"] == version and name not in names,
               "wheel_identity_mismatch")
        names.add(name)
        if name == "torch":
            expect(p.name == TORCH_NAME and version == "2.8.0+cpu", "torch_wheel_variant")
            expect(row["upstream_metadata"] == "upstream/torch-cpu-index.html", "torch_metadata_path")
            parser = CPUIndex(); parser.feed(bytes_at(root, row["upstream_metadata"], JSON_LIMIT).decode())
            matches = set()
            for link in parser.urls:
                url = urllib.parse.urlsplit(urllib.parse.urljoin("https://download.pytorch.org/whl/cpu/torch/", link))
                if urllib.parse.unquote(url.path.rsplit("/", 1)[-1]) != TORCH_NAME: continue
                expect(url.scheme == "https" and url.hostname in {"download.pytorch.org", "download-r2.pytorch.org"}
                       and url.port in (None, 443) and not url.username and not url.password and not url.query,
                       "torch_download_source")
                matches.add((urllib.parse.urlunsplit(url._replace(fragment="")), url.fragment))
            expect(matches == {(row["url"], "sha256=" + row["sha256"])}, "torch_index_binding")
        else:
            mp = f"upstream/pypi/{name}-{version}.json"
            expect(row["upstream_metadata"] == mp, "pypi_metadata_path")
            extras.add(mp)
            meta = load_json(bytes_at(root, mp, JSON_LIMIT)); info = meta.get("info", {})
            expect(normalize_name(info.get("name", "")) == name and info.get("version") == version,
                   "pypi_release_identity")
            hits = [x for x in meta.get("urls", []) if x.get("filename") == p.name]
            expect(len(hits) == 1, "pypi_file_selection")
            hit = hits[0]; url = urllib.parse.urlsplit(hit.get("url", ""))
            expect(url.scheme == "https" and url.hostname == "files.pythonhosted.org" and url.port in (None, 443)
                   and not url.username and not url.password and not url.query and not url.fragment,
                   "pypi_source_origin")
            expect(hit.get("packagetype") == "bdist_wheel" and hit.get("yanked") is False
                   and hit.get("digests", {}).get("sha256") == row["sha256"] and hit["url"] == row["url"],
                   "pypi_original_bytes_mismatch")
        output.append((name, version, sha256(raw), row["path"]))
    versions = {name: version for name, version, _, _ in output}
    expect(all(versions.get(name) == version for name, version in ROOT_VERSIONS.items()), "root_versions_changed")
    expected_lock = "# Q2 runtime review candidate; native model qualification and adoption are pending.\n"
    expected_lock += "".join(f"{name}=={version} --hash=sha256:{h}\n" for name, version, h, _ in sorted(output))
    expect(bytes_at(root, "requirements-q2-reference-v0.lock", JSON_LIMIT) == expected_lock.encode("ascii"),
           "lock_not_exactly_reconstructed")
    return output, extras


def inspect_bundle(root, expected_digest, expected_source, expected_run, repo_root):
    expect(re.fullmatch(r"[0-9a-f]{64}", expected_digest), "bad_expected_digest")
    expect(re.fullmatch(r"[0-9a-f]{40}", expected_source), "bad_expected_source")
    expect(re.fullmatch(r"[1-9][0-9]{0,19}", expected_run), "bad_expected_run")
    expect(root.is_dir() and not root.is_symlink(), "bundle_root_invalid")
    raw = bytes_at(root, "preparation.json", JSON_LIMIT)
    expect(sha256(raw) == expected_digest, "external_preparation_digest_mismatch")
    report = load_json(raw)
    keys(report, "record_type context roots state wheels source_paths files", "preparation_fields")
    expect(raw == json_file_bytes(report), "preparation_file_encoding")
    expect(report["record_type"] == "q2_reference_runtime_preparation_v0", "wrong_phase")
    expect(report["state"] == EXPECTED_STATE and all(type(report["state"][key]) is type(value)
           for key, value in EXPECTED_STATE.items()), "authority_or_readiness_promotion")
    expect(report["roots"] == ROOT_VERSIONS and report["source_paths"] == list(SOURCES), "source_or_root_scope")
    ctx = report["context"]
    keys(ctx, "repository source_commit workflow run_id run_attempt event actor python architecture os runner_image origin",
         "context_fields")
    expect(ctx["repository"] == REPO and ctx["source_commit"] == expected_source and ctx["workflow"] == WF,
           "source_binding_mismatch")
    expect(ctx["run_id"] == expected_run and type(ctx["run_attempt"]) is int and ctx["run_attempt"] == 1,
           "run_binding_mismatch")
    expect(ctx["event"] == "workflow_dispatch" and ctx["actor"] == "HKati" and ctx["origin"] == ORIGIN,
           "origin_profile_mismatch")
    expect(ctx["python"] == "3.11.16" and ctx["os"] == "ubuntu-24.04" and ctx["architecture"] == "x86_64",
           "runtime_target_mismatch")
    expect(type(ctx["runner_image"]) is str and 0 < len(ctx["runner_image"]) <= 128
           and "\n" not in ctx["runner_image"], "runner_image_invalid")
    entries = report["files"]
    expect(type(entries) is list and 20 <= len(entries) <= 150, "file_inventory_size")
    indexed = {}; total = 0
    for item in entries:
        keys(item, "path size sha256", "file_inventory_fields")
        name = item["path"]; valid_path(name)
        expect(name not in indexed and name != "preparation.json", "duplicate_or_self_file")
        data = bytes_at(root, name)
        expect(type(item["size"]) is int and item["size"] == len(data) and item["sha256"] == sha256(data),
               "file_inventory_digest")
        total += len(data); expect(total <= TOTAL_LIMIT, "bundle_total_size")
        indexed[name] = item
    expect(list(indexed) == sorted(indexed), "file_inventory_order")
    actual = set()
    for path in root.rglob("*"):
        expect(not path.is_symlink(), "symlink_forbidden")
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
        else: expect(path.is_dir(), "special_file_forbidden")
    expect(actual == set(indexed) | {"preparation.json"}, "extra_or_missing_file")
    for relative in SOURCES:
        source = bytes_at(root, "source/" + relative, JSON_LIMIT)
        expect(source == git_blob(repo_root, expected_source, relative), "source_snapshot_mismatch")
    expect(sha256(bytes_at(root, "source/" + SELECTION_PATH, JSON_LIMIT)) == FIXED_SELECTION_SHA,
           "selected_definition_replaced")
    expect(sha256(bytes_at(root, "source/" + REQUESTS_PATH, JSON_LIMIT)) == FIXED_REQUESTS_SHA,
           "authored_workload_replaced")
    verify_model(root)
    wheels, metadata_paths = verify_wheels(root, report["wheels"])
    allowed = {"model/" + n for n in MODEL_NAMES} | {"source/" + n for n in SOURCES}
    allowed |= {"upstream/model.json", "upstream/torch-cpu-index.html", "requirements-q2-reference-v0.lock",
                "q2_reference_model_files_v0.json"} | {p for _, _, _, p in wheels} | metadata_paths
    expect(set(indexed) == allowed, "non_selected_preparation_file")
    return report, wheels


def resolve_offline(root, wheels):
    expect(platform.python_implementation() == "CPython" and platform.python_version() == "3.11.16",
           "native_target_required_for_resolution")
    expect(platform.system() == "Linux" and platform.machine() == "x86_64", "native_machine_required")
    osr = platform.freedesktop_os_release()
    expect(osr.get("ID") == "ubuntu" and osr.get("VERSION_ID") == "24.04", "native_os_required")
    with tempfile.TemporaryDirectory(prefix="q2-closure-check-") as td:
        temp = Path(td); report_path = temp / "pip-report.json"
        command = [sys.executable, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
                   "--no-input", "install", "--dry-run", "--ignore-installed", "--only-binary=:all:",
                   "--no-cache-dir", "--no-index", "--find-links", str(root / "wheelhouse"),
                   "--require-hashes", "-r", str(root / "requirements-q2-reference-v0.lock"),
                   "--report", str(report_path)]
        env = {"PATH": os.defpath, "HOME": str(temp), "TMPDIR": str(temp), "LANG": "C.UTF-8",
               "PIP_CONFIG_FILE": os.devnull, "PYTHONNOUSERSITE": "1"}
        with (temp / "pip.log").open("xb") as log:
            proc = subprocess.run(command, env=env, cwd=temp, stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=log, timeout=180)
        expect(proc.returncode == 0, "offline_dependency_resolution_failed")
        result = load_json(bytes_at(temp, "pip-report.json", JSON_LIMIT))
        expect(result.get("version") == "1", "unsupported_pip_report")
        installed = result.get("install")
        expect(type(installed) is list and len(installed) == len(wheels), "incomplete_dependency_closure")
        observed = set()
        expected = {(n, v): (root / p).resolve() for n, v, _, p in wheels}
        for item in installed:
            metadata = item.get("metadata", {}); pair = (normalize_name(metadata.get("name", "")), metadata.get("version"))
            expect(pair in expected and pair not in observed, "dependency_substitution")
            observed.add(pair)
            url = urllib.parse.urlsplit(item.get("download_info", {}).get("url", ""))
            expect(url.scheme == "file" and url.netloc in ("", "localhost")
                   and Path(urllib.parse.unquote(url.path)).resolve() == expected[pair], "nonlocal_resolver_input")
        expect(observed == set(expected), "incomplete_dependency_closure")
        pip_version = result.get("pip_version")
        expect(type(pip_version) is str and re.fullmatch(r"[0-9][A-Za-z0-9.+-]*", pip_version), "pip_version_missing")
        return pip_version


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify-prepared-runtime")
    verify.add_argument("--input-dir", type=Path, required=True)
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--expected-preparation-sha256", required=True)
    verify.add_argument("--expected-source-sha", required=True)
    verify.add_argument("--expected-run-id", required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.input_dir.absolute(); repo_root = args.repo_root.resolve(strict=True)
        expect(Path(__file__).resolve() == (repo_root / CHECKER_PATH).resolve(), "checker_location_mismatch")
        _, wheels = inspect_bundle(root, args.expected_preparation_sha256, args.expected_source_sha,
                                   args.expected_run_id, repo_root)
        pip_version = resolve_offline(root, wheels)
        # Detect any mutation during resolver inspection; do not trust only the initial scan.
        inspect_bundle(root, args.expected_preparation_sha256, args.expected_source_sha, args.expected_run_id, repo_root)
        result = {"record_type": "q2_prepared_runtime_check_v0", "preparation_sha256": args.expected_preparation_sha256,
                  "source_commit": args.expected_source_sha, "run_id": args.expected_run_id,
                  "candidate_bytes_verified": True, "offline_dependency_resolution_checked": True,
                  "pip_version": pip_version, "installation_performed": False, **EXPECTED_STATE}
        expect(not args.output.exists() and not args.output.is_symlink(), "checker_output_exists")
        expect(not args.output.absolute().is_relative_to(root), "checker_output_inside_input")
        with args.output.open("xb") as stream: stream.write(json_file_bytes(result))
        print("Q2 prepared candidate verified; no installation, model execution or release acceptance")
        return 0
    except CheckError as exc:
        print(f"Q2 prepared candidate rejected: {exc}", file=sys.stderr)
    except (OSError, subprocess.SubprocessError, zipfile.BadZipFile, KeyError, TypeError, ValueError):
        print("Q2 prepared candidate rejected: incomplete_or_invalid_preparation", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
