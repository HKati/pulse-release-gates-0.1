#!/usr/bin/env python3
"""Separate prepared-runtime and original 150-slot capture verification.

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


def preparation_main(argv=None):
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


# Capture verification is separate from preparation, with no producer imports.
CAPTURE_SCHEMA = 'schemas/metrics/q2_reference_capture_v0.schema.json'
NATIVE_CHECKER = 'PULSE_safe_pack_v0/tools/check_q2_reference_qualification_v0.py'
NATIVE_SUPERVISOR = 'PULSE_safe_pack_v0/tools/qualify_q2_reference_runtime_v0.py'
CAPTURE_WORKER = 'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py'
CAPTURE_MODEL_MAP = 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json'
CAPTURE_LOCK = 'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock'
CAPTURE_DIAGNOSTIC = 'PULSE_safe_pack_v0/profiles/q2_reference_diagnostic_v0.json'
CAPTURE_QUAL_SCHEMA = 'schemas/metrics/q2_reference_qualification_v0.schema.json'
CAPTURE_RECORD_DIR = 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/'
CAPTURE_REDUCER = 'PULSE_safe_pack_v0/tools/build_q2_reference_summary.py'
CAPTURE_SUMMARY_CHECKER = 'PULSE_safe_pack_v0/tools/check_q2_reference_summary.py'
CAPTURE_SPEC = 'metrics/specs/q2_consistency_v0.yml'
CAPTURE_SOURCES = tuple(sorted({WF, PRODUCER_PATH, CHECKER_PATH, NATIVE_CHECKER, NATIVE_SUPERVISOR,
    CAPTURE_WORKER, CAPTURE_MODEL_MAP, CAPTURE_LOCK, CAPTURE_DIAGNOSTIC, CAPTURE_QUAL_SCHEMA,
    SELECTION_PATH, REQUESTS_PATH, CAPTURE_SCHEMA, CAPTURE_REDUCER, CAPTURE_SUMMARY_CHECKER, CAPTURE_SPEC,
    'schemas/metrics/q2_consistency_input_v0.schema.json', 'schemas/metrics/q2_consistency_summary_v0.schema.json',
    'schemas/dataset_manifest.schema.json', *(CAPTURE_RECORD_DIR + name for name in
    ('preparation.json', 'q2-runtime-preparation-check.json', 'q2_reference_model_files_v0.json',
     'requirements-q2-reference-v0.lock'))}))
CAPTURE_LIMITS = {'generation_seconds': 15, 'phase_seconds': 1200,
                  'memory_bytes': 4294967296, 'tasks': 64, 'retries': 0}
CAPTURE_RUNTIME = {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'device': 'cpu', 'dtype': 'torch.float32',
    'attention': 'eager', 'threads': 1, 'interop_threads': 1, 'deterministic': True, 'evaluation': True,
    'model_class': 'LlamaForCausalLM', 'seed': 1729, 'model_defaults': False, 'compile': False, 'quantization': 'none'}


def capture_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def capture_equal(a, b, code):
    expect(capture_bytes(a) == capture_bytes(b), code)


NATIVE_CHECKER_SHA256 = '25a09b19baae853344e2e656c261267dda8514c484f8477e59d1b60897bf34cc'


def capture_native(source_root):
    import importlib.util
    raw = bytes_at(source_root, NATIVE_CHECKER, JSON_LIMIT)
    expect(sha256(raw) == NATIVE_CHECKER_SHA256, 'capture_native_checker_source')
    spec = importlib.util.spec_from_file_location('q2_capture_independent_native_checks', source_root / NATIVE_CHECKER)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(source_root / NATIVE_CHECKER), 'exec'), module.__dict__)
    return module


def capture_fields(value, fields, code):
    expect(type(value) is dict and set(value) == set(fields.split()), code)


def capture_integer(value, minimum, maximum, code):
    expect(type(value) is int and minimum <= value <= maximum, code)


def capture_slots_checked(workload, jcs):
    expect(len(workload['groups']) == 50 and len(workload['occurrence_inventory']) == 150, 'capture_fixed_extent')
    result = []
    for n, group in enumerate(workload['groups'], 1):
        expect(group['group_id'] == f'q2fx-{n:03d}' and len(group['call_ids']) == 3, 'capture_group_inventory')
        expect(sha256(jcs(group['request'])) == group['request_sha256'], 'capture_request_jcs')
        for repeat, call_id in enumerate(group['call_ids'], 1):
            expect(call_id == f'q2fx-{n:03d}-r{repeat:02d}', 'capture_call_inventory')
            result.append({'ordinal': len(result) + 1, 'call_id': call_id, 'group_id': group['group_id'],
                           'repeat_index': repeat, 'request_sha256': group['request_sha256'], 'attempt': 1})
    capture_equal([{k: v for k, v in r.items() if k != 'attempt'} for r in result],
                  workload['occurrence_inventory'], 'capture_authored_slots')
    return result


def capture_source_rows(source, native):
    rows = []
    for name in CAPTURE_SOURCES:
        raw = native.read(source / name, JSON_LIMIT)
        rows.append({'path': name, 'size': len(raw), 'sha256': sha256(raw)})
    native.adopted_inputs(source)
    return rows


def capture_schema_check(root, kind, value):
    from jsonschema import Draft202012Validator
    native = capture_native(root)
    schema = native.parse(native.read(root / CAPTURE_SCHEMA, 512 * 1024))
    Draft202012Validator.check_schema(schema)
    expect(kind in schema['$defs'], 'capture_schema_kind')
    validator = Draft202012Validator({'$ref': '#/$defs/' + kind, '$defs': schema['$defs']})
    expect(not any(validator.iter_errors(value)), 'capture_schema_' + kind)


def capture_sandbox(value, stage, native):
    if stage in ('installer', 'installcheck'):
        native.verify_sandbox_observation(value, stage)
        return
    capture_fields(value, 'stage unit pid host_netns child_netns uid no_new_privs capabilities ipv4_blocked '
                   'ipv6_blocked memory_max memory_swap_max pids_max cpu_max properties run_mount'
                   + (' capture_runtime_seconds' if stage == 'captureworker' else ''), 'capture_sandbox_fields')
    expect(value['stage'] == stage and re.fullmatch(r'pulse-q2-[a-f0-9]{24}-' + stage + r'\.service', value['unit']),
           'capture_sandbox_identity')
    capture_integer(value['pid'], 2, 2**31 - 1, 'capture_sandbox_pid')
    for name in ('host_netns', 'child_netns'):
        expect(type(value[name]) is str and re.fullmatch(r'net:\[[0-9]+\]', value[name]), 'capture_netns_shape')
    expect(value['host_netns'] != value['child_netns'], 'capture_netns_equal')
    expect(type(value['uid']) is int and value['uid'] == 65534 and value['no_new_privs'] is True
           and value['capabilities'] == '0000000000000000' and value['ipv4_blocked'] is True
           and value['ipv6_blocked'] is True, 'capture_network_privileges')
    for k, v in {'memory_max': '4294967296', 'memory_swap_max': '0', 'pids_max': '64',
                 'cpu_max': '100000 100000'}.items():
        expect(value[k] == v, 'capture_resource_limits')
    properties = {'PrivateNetwork': 'yes', 'NoNewPrivileges': 'yes', 'ProtectSystem': 'strict',
        'ProtectHome': 'yes', 'KillMode': 'control-group', 'SendSIGKILL': 'yes', 'User': '65534', 'Group': '65534',
        'CapabilityBoundingSet': '', 'RestrictAddressFamilies': 'AF_UNIX'}
    expect(set(value['properties']) == set(properties) | {'RuntimeMaxUSec'}, 'capture_properties')
    for k, v in properties.items(): expect(value['properties'][k] == v, 'capture_service_enforcement')
    if stage == 'captureworker':
        seconds = value['capture_runtime_seconds']; capture_integer(seconds, 1, 1200, 'capture_worker_lifetime')
        shown = value['properties']['RuntimeMaxUSec']
        expect(type(shown) is str and shown, 'capture_runtime_display')
        total = 0
        for token in shown.split():
            m = re.fullmatch(r'([0-9]+)(h|min|s|ms|us)', token)
            expect(m is not None, 'capture_runtime_display')
            total += int(m[1]) * {'h': 3600000000, 'min': 60000000, 's': 1000000, 'ms': 1000, 'us': 1}[m[2]]
        expect(total == seconds * 1000000, 'capture_worker_lifetime')
    else:
        expect(stage in ('capturecheck', 'reduction') and value['properties']['RuntimeMaxUSec'] == '3min',
               'capture_checker_lifetime')
    native.verify_run_mount(value['run_mount'], value['unit'])


def capture_cleanup_check(value, unit):
    capture_fields(value, 'unit properties cgroup_empty_or_removed client_reaped', 'capture_cleanup_fields')
    expect(value['unit'] == unit and value['cgroup_empty_or_removed'] is True and value['client_reaped'] is True,
           'capture_cleanup_missing')
    capture_fields(value['properties'], 'LoadState ActiveState ControlGroup', 'capture_cleanup_properties')
    expect(value['properties']['LoadState'] in ('loaded', 'not-found')
           and value['properties']['ActiveState'] == 'inactive', 'capture_cleanup_active')
    expect(value['properties']['ControlGroup'] in ('', '/system.slice/' + unit), 'capture_cleanup_cgroup')


def capture_watchdog_check(record, expected_prefix, received, next_start):
    capture_fields(record, 'record_type stop_returncode units closed_ns', 'capture_timer_fields')
    expect(record['record_type'] == 'q2_capture_watchdog_closed_v0', 'capture_timer_type')
    capture_integer(record['stop_returncode'], 0, 5, 'capture_timer_returncode')
    expect(record['stop_returncode'] in (0, 1, 4, 5) and len(record['units']) == 2, 'capture_timer_stop')
    for suffix, value in zip(('timer', 'service'), record['units']):
        capture_fields(value, 'unit LoadState ActiveState', 'capture_timer_unit_fields')
        expect(value['unit'] == expected_prefix + '-watchdog.' + suffix
               and value['LoadState'] in ('loaded', 'not-found') and value['ActiveState'] == 'inactive',
               'capture_stale_timer')
    capture_integer(record['closed_ns'], received, next_start, 'capture_timer_close_order')


def capture_target_response(response, ready, slot, identity, tokenize, decode, messages, config):
    import base64
    capture_fields(response, 'record_type binding slot input_ids new_token_ids text text_utf8_base64 '
                   'stop_reason effective_generation runtime', 'capture_response_fields')
    capture_fields(ready, 'record_type binding slot input_ids effective_generation runtime', 'capture_ready_fields')
    expect(response['record_type'] == 'q2_capture_response_v0' and ready['record_type'] == 'q2_capture_slot_ready_v0',
           'capture_response_type')
    for value in (response, ready):
        capture_equal(value['slot'], slot, 'capture_slot_substitution')
        capture_equal(value['binding'], identity, 'capture_binding_substitution')
        capture_equal(value['effective_generation'], config, 'capture_generation_substitution')
        capture_equal(value['runtime'], CAPTURE_RUNTIME, 'capture_runtime_substitution')
        ids = value['input_ids']
        expect(type(ids) is list and 1 <= len(ids) <= 4096
               and all(type(i) is int and 0 <= i < 49152 for i in ids), 'capture_input_token_bounds')
    expected_ids = tokenize(messages)
    capture_equal(ready['input_ids'], expected_ids, 'capture_tokenization_changed')
    capture_equal(response['input_ids'], expected_ids, 'capture_input_changed')
    ids = response['new_token_ids']
    expect(type(ids) is list and 1 <= len(ids) <= 32 and all(type(i) is int and 0 <= i < 49152 for i in ids),
           'capture_output_token_bounds')
    if ids[-1] == 2:
        expect(2 not in ids[:-1] and response['stop_reason'] == 'eos', 'capture_eos')
    else:
        expect(len(ids) == 32 and 2 not in ids and response['stop_reason'] == 'token_limit', 'capture_unfinished_response')
    text = response['text']
    expect(type(text) is str and len(text.encode('utf-8')) <= 65536, 'capture_text_bounds')
    expect(base64.b64encode(text.encode('utf-8')).decode('ascii') == response['text_utf8_base64'], 'capture_utf8_substitution')
    expect(decode(ids) == text, 'capture_decoding_substitution')
    if response['stop_reason'] == 'eos':
        return {'response_id': slot['call_id'], 'kind': 'answer', 'answer': text}
    return {'response_id': slot['call_id'], 'kind': 'unknown'}


def capture_derived_manifest(pre, terminal, groups_raw):
    return {'manifest_version': '1.0.0', 'dataset_id': 'q2-field-extractor-' + pre['context']['run_id'],
        'time_range': {'from': pre['started_at'], 'to': terminal['ended_at']},
        'source': {'kind': 'artifact', 'uri': 'github-actions:' + REPO + '/' + pre['context']['run_id'] + '/1',
                   'description': 'Original fixed Q2 capture; reviewed collector and GitHub host trusted.'},
        'sampling': {'strategy': 'full', 'n': 50, 'seed': 0},
        'hashes': {'input_sha256': sha256(groups_raw), 'code_sha': pre['context']['source_commit']},
        'pii_handling': {'scrubbed': False, 'notes': 'Authored controlled inputs; original outputs retained without redaction.'}}


def capture_records(pre, subject, model_ready, terminal, records, workload, jcs, tokenize, decode, config):
    """Independently reconstruct all 150 responses; no acceptance flags as input."""
    slots = capture_slots_checked(workload, jcs)
    capture_equal(pre['slots'], slots, 'capture_prelaunch_extent')
    capture_equal(pre['limits'], CAPTURE_LIMITS, 'capture_limit_contract')
    expect(pre['record_type'] == 'q2_capture_prelaunch_v0' and pre['record_status'] == 'native'
           and pre['authority_effect'] == 'none' and pre['production_gate_eligible'] is False,
           'capture_prelaunch_profile')
    ctx = pre['context']
    expect(ctx['origin'] == 'owner_dispatched_github_q2_capture' and ctx['repository'] == REPO
           and ctx['workflow'] == WF and ctx['actor'] == 'HKati' and ctx['event'] == 'workflow_dispatch'
           and type(ctx['run_attempt']) is int and ctx['run_attempt'] == 1, 'capture_native_context')
    expect(pre['phase_deadline_ns'] == pre['phase_start_ns'] + 1200_000_000_000, 'capture_phase_budget')
    capture_fields(model_ready, 'record_type binding effective_generation runtime', 'capture_model_ready_fields')
    identity = {'prelaunch_sha256': sha256(capture_bytes(pre)), 'source_commit': ctx['source_commit'],
                'run_id': ctx['run_id'], 'run_attempt': 1}
    expect(model_ready['record_type'] == 'q2_capture_model_ready_v0', 'capture_model_ready_type')
    capture_equal(model_ready['binding'], identity, 'capture_model_ready_binding')
    capture_equal(model_ready['effective_generation'], config, 'capture_ready_configuration')
    capture_equal(model_ready['runtime'], CAPTURE_RUNTIME, 'capture_ready_runtime')
    expect(subject['prelaunch_sha256'] == identity['prelaunch_sha256']
           and subject['ready_sha256'] == sha256(capture_bytes(model_ready)), 'capture_subject_ready_binding')
    capture_equal(subject['effective_generation'], config, 'capture_subject_generation')
    capture_equal(subject['runtime'], CAPTURE_RUNTIME, 'capture_subject_runtime')
    identity['subject_sha256'] = sha256(capture_bytes(subject))
    expect(terminal['record_type'] == 'q2_capture_transcript_v0' and terminal['record_status'] == 'native'
           and terminal['status'] == 'completed' and terminal['error_code'] is None
           and terminal['authority_effect'] == 'none' and terminal['production_gate_eligible'] is False,
           'capture_not_complete')
    capture_equal(terminal['binding'], identity, 'capture_terminal_binding')
    expect(len(terminal['occurrences']) == 150 and len(records) == 150, 'capture_terminal_extent')
    capture_integer(terminal['worker_exit_code'], 0, 0, 'capture_worker_exit')
    capture_integer(terminal['worker_launch_ns'], pre['phase_start_ns'], pre['phase_deadline_ns'], 'capture_launch_order')
    capture_integer(terminal['worker_deadline_ns'], terminal['worker_launch_ns'], pre['phase_deadline_ns'], 'capture_worker_deadline')
    capture_integer(terminal['sandbox']['capture_runtime_seconds'], 1, 1200, 'capture_runtime_seconds')
    expect(terminal['worker_deadline_ns'] - terminal['worker_launch_ns'] ==
           terminal['sandbox']['capture_runtime_seconds'] * 1_000_000_000, 'capture_runtime_bound')
    capture_integer(terminal['session_end_ns'], terminal['worker_launch_ns'], terminal['worker_deadline_ns'], 'capture_session_deadline')
    expected_session_end = {'record_type': 'q2_capture_session_end_v0', 'binding': identity, 'completed_calls': 150}
    capture_equal(terminal['session_end'], expected_session_end, 'capture_session_end')
    from datetime import datetime
    begin = datetime.fromisoformat(pre['started_at']); end = datetime.fromisoformat(terminal['ended_at'])
    expect(begin.tzinfo is not None and end.tzinfo is not None and begin <= end, 'capture_wall_time_bounds')
    requests = {g['group_id']: g['request'] for g in workload['groups']}
    output_groups = []
    previous = terminal['worker_launch_ns']
    unit = terminal['sandbox']['unit']; prefix = unit.removesuffix('-captureworker.service')
    capture_cleanup_check(terminal['cleanup'], unit)
    for index, (slot, occ, record) in enumerate(zip(slots, terminal['occurrences'], records)):
        expect(occ['status'] == 'completed', 'capture_incomplete_slot')
        capture_equal(occ['slot'], slot, 'capture_occurrence_reordered')
        capture_integer(occ['ready_received_ns'], previous, terminal['worker_deadline_ns'], 'capture_ready_order')
        capture_integer(occ['generation_start_ns'], occ['ready_received_ns'], terminal['worker_deadline_ns'], 'capture_go_order')
        start = occ['generation_start_ns']; deadline = occ['generation_deadline_ns']
        expect(type(deadline) is int and deadline == start + 15_000_000_000
               and deadline < terminal['worker_deadline_ns'] and deadline < pre['phase_deadline_ns'], 'capture_generation_window')
        capture_integer(occ['response_received_ns'], start, deadline, 'capture_late_response')
        capture_integer(occ['watchdog_arm_begin_ns'], occ['ready_received_ns'], start, 'capture_timer_arming_order')
        expect(occ['watchdog_armed'] is True and deadline < occ['watchdog_arm_begin_ns'] + 20_000_000_000,
               'capture_timer_window')
        timer_prefix = prefix + f'-call-{index + 1:03d}'
        expect(occ['watchdog_unit'] == timer_prefix + '-watchdog.timer', 'capture_timer_substitution')
        next_start = terminal['occurrences'][index + 1]['ready_received_ns'] if index < 149 else terminal['session_end_ns']
        capture_watchdog_check(occ['watchdog_closed'], timer_prefix, occ['response_received_ns'], next_start)
        previous = occ['watchdog_closed']['closed_ns']
        response, ready = record
        derived = capture_target_response(response, ready, slot, identity, tokenize, decode,
                                          requests[slot['group_id']]['messages'], config)
        if index % 3 == 0: output_groups.append({'group_id': slot['group_id'], 'responses': []})
        output_groups[-1]['responses'].append(derived)
    group_payload = {'schema_version': 'q2_consistency_input_v0', 'record_status': 'archived_response_records',
        'extraction_profile': 'typed_final_answer_or_refusal_v0', 'grouping': {'method_id': 'exact_request_repeats_v0',
        'method_version': 'v0', 'seed': 0, 'sampling_parameters': {'repeats': 3}}, 'groups': output_groups}
    groups_raw = capture_bytes(group_payload)
    return groups_raw, capture_bytes(capture_derived_manifest(pre, terminal, groups_raw))


def capture_verified_inputs(args):
    native = capture_native(args.source_root)
    native.native_target()
    expect(sys.flags.isolated and os.getuid() == 65534 and Path(sys.prefix).resolve() == args.venv.resolve()
           and sys.prefix != sys.base_prefix, 'capture_checker_environment')
    expect(Path(__file__).resolve() == (args.source_root / CHECKER_PATH).resolve(), 'capture_checker_location')
    read = lambda name: native.read(args.evidence / name, JSON_LIMIT)
    pre_raw = read('capture-prelaunch.json'); subject_raw = read('capture-subject.json'); raw = read('transcript.json')
    expect(sha256(pre_raw) == args.expected_prelaunch_sha256 and sha256(subject_raw) == args.expected_subject_sha256
           and sha256(raw) == args.expected_transcript_sha256, 'capture_external_digests')
    pre, subject, terminal = map(native.parse, (pre_raw, subject_raw, raw))
    ready = native.parse(read('capture-model-ready.json'))
    for kind, value in (('prelaunch', pre), ('subject', subject), ('transcript', terminal), ('model_ready', ready)):
        capture_schema_check(args.source_root, kind, value)
    for value, rawval in ((pre, pre_raw), (subject, subject_raw), (terminal, raw)):
        expect(capture_bytes(value) == rawval, 'capture_canonical_record')
    ctx = pre['context']
    expect(ctx['source_commit'] == args.expected_source_sha and ctx['run_id'] == args.expected_run_id,
           'capture_external_context')
    rows = capture_source_rows(args.source_root, native)
    capture_equal(pre['source_files'], rows, 'capture_source_inventory')
    expect(sha256(capture_bytes(rows)) == args.expected_source_inventory_sha256, 'capture_external_source_inventory')
    expect(pre['preparation_source_commit'] == native.ORIGINAL_SOURCE and pre['preparation_run_id'] == native.ORIGINAL_RUN
           and pre['artifact_sha256'] == native.ARCHIVE_SHA and pre['selection_sha256'] == FIXED_SELECTION_SHA
           and pre['workload_sha256'] == FIXED_REQUESTS_SHA, 'capture_historical_bindings')
    installation_raw = read('installation.json'); installation = native.parse(installation_raw)
    expect(sha256(installation_raw) == pre['installation_sha256'], 'capture_installation_binding')
    recomputed = native.verify_installation(args.venv, args.bundle, args.evidence / 'bootstrap.json', args.evidence / 'pip-report.json')
    capture_equal(recomputed, installation, 'capture_post_installation_recheck')
    expect(sha256(capture_bytes(installation['inventory'])) == pre['environment_inventory_sha256'], 'capture_environment_inventory')
    model_map = native.parse(native.read(args.source_root / CAPTURE_MODEL_MAP))
    for item in model_map['files']:
        data = native.read(args.bundle / item['path'])
        expect(len(data) == item['size'] and sha256(data) == item['sha256'], 'capture_model_bytes')
    import importlib.metadata
    import rfc8785
    import transformers
    from transformers import AutoTokenizer, GenerationConfig
    for module in (rfc8785, transformers):
        expect(Path(module.__file__).resolve().is_relative_to(args.venv.resolve()), 'capture_checker_module_origin')
    for name, version in {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'rfc8785': '0.1.4'}.items():
        expect(importlib.metadata.version(name) == version, 'capture_checker_version')
    expect(rfc8785.dumps({'a': 1.0, 'b': -0.0}) == b'{"a":1,"b":0}', 'capture_jcs_numbers')
    expect(rfc8785.dumps({'\ue000': 1, '\U00010000': 2}) == '{"\U00010000":2,"\ue000":1}'.encode(), 'capture_jcs_order')
    selection = native.parse(native.read(args.source_root / SELECTION_PATH))
    expect(sha256(rfc8785.dumps(selection['release_subject']['definition'])) == native.DEFINITION_SHA, 'capture_selected_definition')
    tokenizer = AutoTokenizer.from_pretrained(str(args.bundle / 'model'), local_files_only=True, trust_remote_code=False, use_fast=True)
    expect(tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id) == (1, 2, 2),
           'capture_tokenizer_configuration')
    config = GenerationConfig(**native.GENERATION, disable_compile=True).to_dict()
    expected_subject = {'record_type': 'q2_capture_subject_v0', 'prelaunch_sha256': sha256(pre_raw),
        'definition_sha256': native.DEFINITION_SHA, 'worker_sha256': next(r['sha256'] for r in rows if r['path'] == CAPTURE_WORKER),
        'installation_sha256': sha256(installation_raw), 'environment_inventory_sha256': pre['environment_inventory_sha256'],
        'model_files': model_map['files'], 'platform': ctx, 'ready_sha256': sha256(read('capture-model-ready.json')),
        'effective_generation': config, 'runtime': CAPTURE_RUNTIME, 'authority_effect': 'none', 'production_gate_eligible': False}
    capture_equal(subject, expected_subject, 'capture_materialized_subject')
    prefix = terminal['sandbox']['unit'].removesuffix('-captureworker.service')
    capture_sandbox(terminal['sandbox'], 'captureworker', native)
    for stage in ('installer', 'installcheck'):
        obs = native.parse(read(stage + '-sandbox.json'))
        capture_sandbox(obs, stage, native)
        expect(obs['unit'] == prefix + '-' + stage + '.service', 'capture_cross_session_sandbox')
        capture_cleanup_check(native.parse(read(stage + '-cleanup.json')), obs['unit'])
    expected_call_files = {slot['call_id'] + suffix for slot in pre['slots']
                           for suffix in ('.ready.json', '.response.json', '.intent.json', '.utf8')}
    call_directory = args.evidence / 'calls'
    expect(not call_directory.is_symlink() and call_directory.is_dir()
           and {p.name for p in call_directory.iterdir()} == expected_call_files, 'capture_call_file_extent')
    records = []
    for occurrence in terminal['occurrences']:
        slot = occurrence['slot']; stem = 'calls/' + slot['call_id']
        intent_raw = read(stem + '.intent.json')
        expected_intent = {'slot': slot, 'binding': terminal['binding'], 'generation_seconds': 15,
                           'retries': 0, 'intent': 'before_GO'}
        expect(intent_raw == capture_bytes(expected_intent), 'capture_intent_substitution')
        objects = []
        for key, name, kind in (('response', stem + '.response.json', 'response'), ('ready', stem + '.ready.json', 'slot_ready')):
            row = occurrence[key]
            expect(row['path'] == name, 'capture_record_path')
            data = read(name)
            expect(len(data) == row['size'] and sha256(data) == row['sha256'], 'capture_record_digest')
            obj = native.parse(data); expect(capture_bytes(obj) == data, 'capture_record_canonical')
            capture_schema_check(args.source_root, kind, obj); objects.append(obj)
        text_raw = read(stem + '.utf8')
        expect(text_raw == objects[0]['text'].encode('utf-8'), 'capture_original_continuation')
        records.append(tuple(objects))
    workload = native.parse(native.read(args.source_root / REQUESTS_PATH))
    groups, manifest = capture_records(pre, subject, ready, terminal, records, workload, rfc8785.dumps,
        lambda messages: tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True),
        lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False), config)
    expect(groups == read('groups.json') and manifest == read('dataset-manifest.json'), 'capture_derived_input_substitution')
    handoff = native.parse(read('handoff.json'))
    expected_handoff = {'record_type': 'q2_capture_handoff_v0', 'binding': terminal['binding'],
        'transcript_sha256': args.expected_transcript_sha256, 'groups_sha256': sha256(groups),
        'manifest_sha256': sha256(manifest), 'authority_effect': 'none', 'production_gate_eligible': False}
    capture_equal(handoff, expected_handoff, 'capture_handoff_substitution')
    expect(read('handoff.json') == capture_bytes(expected_handoff), 'capture_handoff_encoding')
    # Inventory and original bytes are rechecked at the service's exit boundary.
    capture_equal(native.verify_installation(args.venv, args.bundle, args.evidence / 'bootstrap.json',
                  args.evidence / 'pip-report.json'), installation, 'capture_checker_runtime_mutation')
    return {**expected_handoff, 'record_type': 'q2_capture_check_v0', 'complete_original_capture_verified': True,
            'decoding_and_extraction_verified': True, 'verified_calls': 150,
            'trust_boundary': 'reviewed_collector_pinned_dependencies_and_GitHub_host'}


def capture_check_main(argv):
    parser = argparse.ArgumentParser(description='Separately check native Q2 capture; no inference or authority.')
    parser.add_argument('phase', choices=['verify-capture'])
    for name in ('source-root', 'evidence', 'bundle', 'venv', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('expected-source-sha', 'expected-run-id', 'expected-prelaunch-sha256',
                 'expected-subject-sha256', 'expected-transcript-sha256', 'expected-source-inventory-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        result = capture_verified_inputs(args)
        expect(not args.output.absolute().is_relative_to(args.evidence.absolute()), 'capture_checker_output_inside_evidence')
        with args.output.open('xb') as out:
            out.write(capture_bytes(result)); out.flush(); os.fsync(out.fileno())
        print('Q2 original capture verified; no production admission')
        return 0
    except Exception as exc:
        code = 'capture_evidence_invalid_or_unavailable'
        own_error = type(exc) is CheckError or (type(exc).__name__ == 'QualificationCheckError'
            and type(exc).__module__ == 'q2_capture_independent_native_checks')
        if own_error and len(exc.args) == 1 and type(exc.args[0]) is str and re.fullmatch('[a-z][a-z0-9_]{0,95}', exc.args[0]):
            code = exc.args[0]
        print('Q2 capture rejected: ' + code, file=sys.stderr)
        return 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'verify-capture':
        return capture_check_main(argv)
    return preparation_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
