#!/usr/bin/env python3
"""Conservative static Lean source-import discovery, not compiler resolution.

The scanner binds bytes of every visited module and preserves absent providers,
missing imports, unsupported lexical forms, and ambiguities.  It never selects
the first of two providers.  A static fixed point is not a successful build, a
kernel axiom export, a Comparator result, or mathematical acceptance.
"""
from __future__ import annotations

# Direct scripts cannot establish source binding before their imports.
if __name__ == "__main__":
    import sys as _qrh_sys
    print("QRH003_SOURCE_BOUND_LAUNCH_REQUIRED: use source_bound.py with python -I", file=_qrh_sys.stderr)
    raise SystemExit(2)


import argparse
import bisect
from collections import Counter, deque
from pathlib import Path
import re
from typing import Sequence

try:
    from .common import AuditError, canonical_bytes, read_json, secure_read, sha256_bytes, write_json
    from .acquire import blob_sha1, collect_acquisition, read_git_tree, verify_git_snapshot
except ImportError:
    from common import AuditError, canonical_bytes, read_json, secure_read, sha256_bytes, write_json
    from acquire import blob_sha1, collect_acquisition, read_git_tree, verify_git_snapshot


DEFAULT_ROOT_MODULES = (
    "OAI.NumberTheory.DirichletL.Nonvanishing",
    "OAI.NumberTheory.DirichletL.Hecke.Nonvanishing",
    "OAI.NumberTheory.SiegelZeros.Main",
    "ComparatorChallenges.QuasiRiemannHypothesis",
    "ComparatorChallenges.DirichletSevenEighths",
    "ComparatorChallenges.HeckeSevenEighths",
    "ComparatorChallenges.SiegelZeros",
)

IDENT_PART = r"(?:«[^»\n/\\\x00]+»|[^\W\d][\w']*)"
MODULE_TOKEN = re.compile(IDENT_PART + r"(?:\." + IDENT_PART + r")*", re.UNICODE)
LEXICAL_PATTERNS = {key: re.compile(expression) for key, expression in {
    "sorry": r"\bsorry\b", "sorryAx": r"\bsorryAx\b", "axiom_keyword": r"\baxiom\b",
    "unsafe": r"\bunsafe\b", "native_decide": r"\bnative_decide\b",
    "implemented_by": r"\bimplemented_by\b", "extern": r"\bextern\b",
    "run_cmd": r"\brun_cmd\b", "eval": r"#eval\b",
    "kernel_override_option": r"\bset_option[^\n]*(?:trust|skipKernel|kernel)",
}.items()}
LEXICAL_TOKEN = re.compile(r'/\-|--|(?<![\w\'])r\#*"|"|\'(?:\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)|[^\'\\\n])\'')
COMMENT_TOKEN = re.compile(r"/\-|-/")
STRING_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)


def module_relative_path(module: str) -> str:
    """Map a recognized Lean module identifier to one contained relative path.

    Dots inside «escaped identifiers» are literal filename characters.  Unknown
    name syntax is rejected instead of being converted into a filesystem path.
    """
    if not isinstance(module, str) or not MODULE_TOKEN.fullmatch(module):
        raise AuditError("QRH003_SOURCE_MODULE_NAME_UNSUPPORTED", str(module))
    parts, offset = [], 0
    while offset < len(module):
        if module[offset] == "«":
            end = module.index("»", offset)
            part = module[offset + 1:end]
            offset = end + 1
        else:
            match = re.match(r"[^\W\d][\w']*", module[offset:], re.UNICODE)
            if match is None:
                raise AuditError("QRH003_SOURCE_MODULE_NAME_UNSUPPORTED", module)
            part = match.group()
            offset += len(part)
        if part in ("", ".", "..") or "/" in part or "\\" in part:
            raise AuditError("QRH003_SOURCE_MODULE_NAME_UNSUPPORTED", module)
        parts.append(part)
        if offset < len(module):
            if module[offset] != ".":
                raise AuditError("QRH003_SOURCE_MODULE_NAME_UNSUPPORTED", module)
            offset += 1
    return "/".join(parts) + ".lean"


def strip_comments_and_literals(text: str) -> str:
    """Preserve offsets/newlines while removing nested comments and literals.

    This is a conservative lexical pass, not Lean's elaborator.  Interpolated
    string expressions are not evaluated; lexical hit absence cannot establish
    the absence of axioms or unsafe code in the elaborated environment.
    """
    output, position = [], 0
    while match := LEXICAL_TOKEN.search(text, position):
        output.append(text[position:match.start()])
        token = match.group()
        if token == "/-":
            depth, end = 1, match.end()
            while depth:
                nested = COMMENT_TOKEN.search(text, end)
                if nested is None:
                    raise AuditError("QRH003_LEAN_UNCLOSED_COMMENT", str(match.start()))
                depth += 1 if nested.group() == "/-" else -1
                end = nested.end()
        elif token == "--":
            end = text.find("\n", match.end())
            if end == -1:
                end = len(text)
        elif token.startswith("r"):
            marker = '"' + "#" * token.count("#")
            end = text.find(marker, match.end())
            if end == -1:
                raise AuditError("QRH003_LEAN_UNCLOSED_RAW_STRING", str(match.start()))
            end += len(marker)
        elif token == '"':
            literal = STRING_TOKEN.match(text, match.start())
            if literal is None:
                raise AuditError("QRH003_LEAN_UNCLOSED_STRING", str(match.start()))
            end = literal.end()
        else:
            end = match.end()
        output.append(re.sub(r"[^\n]", " ", text[match.start():end]))
        position = end
    output.append(text[position:])
    return "".join(output)


def parse_lean_source(data: bytes) -> dict:
    """Recognize the supported static header and preliminary lexical audit hits.

    Header grammar follows the inspected Lean 4.34.1 source: optional module,
    optional prelude, then repeated [public] [meta] import [all] module-name.
    No names are imported from commented/quoted body text.  Unsupported forms
    and all lexical errors remain explicit; raw-source fallback is forbidden.
    """
    result = {"status": "PARTIAL_MATCH", "imports": [], "prelude": False,
              "module_keyword": False, "lexical_hits": {}, "errors": [],
              "parser": "restricted_static_header_v0", "compiler_parser_used": False}
    try:
        text = data.decode("utf-8", "strict")
        if "\0" in text:
            raise AuditError("QRH003_LEAN_NUL_BYTE")
        clean = strip_comments_and_literals(text)
    except (UnicodeError, AuditError) as exc:
        result["errors"].append({"code": getattr(exc, "code", "QRH003_LEAN_INVALID_UTF8"), "detail": str(exc)})
        return result
    line_breaks = [match.start() for match in re.finditer("\n", clean)]
    source_lines = text.splitlines()
    result["lines"] = len(source_lines)
    for label, expression in LEXICAL_PATTERNS.items():
        hits = []
        for match in expression.finditer(clean):
            line = bisect.bisect(line_breaks, match.start())
            hits.append({"line": line + 1, "column": match.start() - (line_breaks[line-1] + 1 if line else 0) + 1,
                         "text": source_lines[line].strip()[:400]})
        if hits:
            result["lexical_hits"][label] = hits
    result["lexical_hit_interpretation"] = "REQUIRES_TARGET_AXIOM_EXPORT_AND_CODE_REVIEW"
    offset = 1 if clean.startswith("\ufeff") else 0

    def skip_space() -> None:
        nonlocal offset
        while offset < len(clean) and clean[offset].isspace():
            offset += 1

    def keyword(word: str) -> bool:
        nonlocal offset
        end = offset + len(word)
        if clean.startswith(word, offset) and (end == len(clean) or not (clean[end].isalnum() or clean[end] in "_'")):
            offset = end
            skip_space()
            return True
        return False

    skip_space()
    result["module_keyword"] = keyword("module")
    result["prelude"] = keyword("prelude")
    while offset < len(clean):
        start = offset
        public = keyword("public")
        meta = keyword("meta")
        if not keyword("import"):
            # public section/meta def begin the body, not another import.
            offset = start
            break
        import_all = keyword("all")
        name_match = MODULE_TOKEN.match(clean, offset)
        if name_match is None:
            result["errors"].append({"code": "QRH003_LEAN_IMPORT_UNPARSED", "offset": offset})
            break
        name = name_match.group()
        try:
            module_relative_path(name)
        except AuditError as exc:
            result["errors"].append({"code": exc.code, "detail": str(exc)})
            break
        if name_match.end() < len(clean) and not clean[name_match.end()].isspace():
            result["errors"].append({"code": "QRH003_LEAN_IMPORT_TRAILING_TOKEN", "offset": name_match.end()})
            break
        result["imports"].append({"module": name, "line": bisect.bisect(line_breaks, start) + 1,
                                  "public": public, "meta": meta, "all": import_all})
        offset = name_match.end()
        skip_space()
    result["header_end_offset"] = offset
    # A line-oriented import after a closed header is unsupported (or source
    # quotation syntax).  Preserve uncertainty instead of silently ignoring it.
    tail_import = re.search(r"(?m)^[ \t]*(?:(?:public|private)[ \t]+)?(?:meta[ \t]+)?import(?:\s|$)", clean[offset:])
    if tail_import:
        result["errors"].append({"code": "QRH003_LEAN_IMPORT_OUTSIDE_RECOGNIZED_HEADER",
                                  "line": bisect.bisect(line_breaks, offset + tail_import.start()) + 1})
    result["status"] = "MATCH" if not result["errors"] else "PARTIAL_MATCH"
    return result


def _prepare_providers(source_roots: Sequence[dict]) -> tuple[list[dict], list[dict]]:
    prepared, errors, repository_cache = [], [], {}
    seen = set()
    for index, declaration in enumerate(source_roots):
        item = {"provider_id": index, "declaration": declaration, "status": "RETRIEVAL_UNAVAILABLE",
                "identity_status": "UNVERIFIED", "reasons": [], "tree": {}}
        prepared.append(item)
        try:
            package = declaration["package"]
            root = Path(declaration["path"])
            git_root = Path(declaration["git_root"])
            commit = declaration["expected_commit"]
            profile = declaration.get("source_profile", "pinned_git_source")
            subdir = declaration.get("source_subdir", "")
            item.update(package=package, path=root, git_root=git_root, expected_commit=commit,
                        source_profile=profile, source_subdir=subdir)
            key = (str(root.absolute()), package)
            if key in seen:
                raise AuditError("QRH003_SOURCE_PROVIDER_DUPLICATE", package)
            seen.add(key)
            if not root.is_dir() or root.is_symlink():
                item["reasons"].append({"code": "QRH003_SOURCE_PROVIDER_UNAVAILABLE", "path": str(root)})
                continue
            cache_key = (str(git_root.absolute()), commit)
            if cache_key not in repository_cache:
                verification = verify_git_snapshot(git_root, commit)
                tree, tree_record = read_git_tree(git_root, commit) if verification["status"] == "VERIFIED" else ({}, {})
                repository_cache[cache_key] = (verification, tree, tree_record)
            verification, tree, tree_record = repository_cache[cache_key]
            item.update(status="OBSERVED", identity_status=verification["status"],
                        verification=verification, tree=tree, tree_observation=tree_record)
            if profile == "pinned_git_source":
                expected_path = git_root / subdir
                if expected_path.absolute() != root.absolute():
                    raise AuditError("QRH003_SOURCE_PROVIDER_PATH_BINDING_MISMATCH", package)
                if declaration.get("required_patch_unapplied"):
                    raise AuditError("QRH003_REQUIRED_PATCH_NOT_MATERIALIZED", package)
            elif profile == "patch_derived_overlay":
                overlay = declaration.get("effective_manifest")
                if not isinstance(overlay, dict) or overlay.get("materialization_status") != "VERIFIED":
                    raise AuditError("QRH003_EFFECTIVE_SOURCE_MANIFEST_UNVERIFIED", package)
                if overlay.get("base_commit") != commit or Path(overlay.get("effective_path", "")).absolute() != root.absolute():
                    raise AuditError("QRH003_EFFECTIVE_SOURCE_BINDING_MISMATCH", package)
                files = overlay.get("effective_files")
                before = overlay.get("base_files")
                if not isinstance(files, dict) or not isinstance(before, dict):
                    raise AuditError("QRH003_EFFECTIVE_SOURCE_MANIFEST_MISSING", package)
                if (sha256_bytes(canonical_bytes(files)) != overlay.get("effective_manifest_sha256")
                        or sha256_bytes(canonical_bytes(before)) != overlay.get("base_manifest_sha256")):
                    raise AuditError("QRH003_EFFECTIVE_SOURCE_MANIFEST_DIGEST_MISMATCH", package)
                item["effective_files"] = files
                item["overlay_receipt_authentication"] = "REQUIRED_AT_COLLECTOR_BOUNDARY"
            else:
                raise AuditError("QRH003_SOURCE_PROFILE_UNSUPPORTED", profile)
        except (KeyError, TypeError, ValueError, OSError, AuditError) as exc:
            item.update(identity_status="MISMATCH")
            item["reasons"].append({"code": getattr(exc, "code", "QRH003_SOURCE_PROVIDER_INVALID"), "detail": str(exc)})
            errors.append({"provider_id": index, **item["reasons"][-1]})
    return prepared, errors


def resolve_static_source_closure(source_roots: Sequence[dict], root_modules: Sequence[str], *,
                                  provider_universe_status: str | None = None,
                                  max_modules: int = 200000,
                                  max_source_bytes: int = 2_147_483_648) -> dict:
    """Find a source fixed point over declared available providers with byte binding.

    ``effective_manifest`` is an acquisition observation, not a self-authenticating
    signature.  The collector must authenticate both it and this result.  Missing
    lock packages remain a separate provider-universe state even when every
    encountered import has a unique available source.
    """
    if type(max_modules) is not int or type(max_source_bytes) is not int or max_modules <= 0 or max_source_bytes <= 0:
        raise AuditError("QRH003_SOURCE_RESOURCE_LIMIT_INVALID")
    if provider_universe_status not in (None, "MATCH", "NO_MATCH", "PARTIAL_MATCH", "RETRIEVAL_UNAVAILABLE"):
        raise AuditError("QRH003_PROVIDER_UNIVERSE_STATUS_INVALID")
    providers, provider_errors = _prepare_providers(source_roots)
    modules, edges, failures = {}, [], {}
    all_available = bool(providers) and all(p["status"] == "OBSERVED" for p in providers)
    result = {"schema": "qrh003.static_source_closure.v0", "artifact_role": "collector_observation",
              "authority": "NONE", "root_modules": list(root_modules),
              "discovery_status": "RETRIEVAL_UNAVAILABLE", "static_graph_status": "RETRIEVAL_UNAVAILABLE",
              "source_identity_status": "UNVERIFIED",
              "provider_universe_status": provider_universe_status or ("MATCH" if all_available else "PARTIAL_MATCH"),
              "provider_universe_scope": "locked_package_source_inventory" if provider_universe_status is not None else "declared_provider_directories",
              "compiler_resolved_imports_status": "NOT_RUN", "axiom_profile_status": "NOT_RUN",
              "clean_build_status": "NOT_RUN", "mathematical_semantics_status": "NOT_RUN",
              "method": "restricted static header traversal plus inferred default Init; no compiler import resolver",
              "provider_errors": provider_errors, "modules": modules, "edges": edges,
              "resolution_failures": failures, "per_root": {}, "reasons": []}
    if not root_modules or len(root_modules) != len(set(root_modules)):
        result["reasons"].append({"code": "QRH003_ROOT_MODULE_SET_EMPTY_OR_DUPLICATED"})
        result["discovery_status"] = "NO_MATCH"
        return result
    source_bytes = 0

    def resolve(name: str) -> list[str] | None:
        nonlocal source_bytes
        if name in failures:
            return None
        if name in modules:
            return modules[name]["direct_imports"]
        if len(modules) >= max_modules or source_bytes >= max_source_bytes:
            failures[name] = {"status": "RETRIEVAL_UNAVAILABLE", "code": "QRH003_SOURCE_RESOURCE_LIMIT"}
            return None
        try:
            relative = module_relative_path(name)
        except AuditError as exc:
            failures[name] = {"status": "NO_MATCH", "code": exc.code, "detail": str(exc)}
            return None
        candidates, unavailable = [], []
        for provider in providers:
            root = provider.get("path")
            if root is None or provider["status"] != "OBSERVED":
                unavailable.append(provider["provider_id"])
                continue
            path = root / relative
            try:
                path.lstat()
                candidates.append(provider)
            except FileNotFoundError:
                pass
            except OSError:
                unavailable.append(provider["provider_id"])
        if len(candidates) > 1:
            failures[name] = {"status": "AMBIGUOUS", "code": "QRH003_SOURCE_IMPORT_AMBIGUOUS",
                              "providers": [p["provider_id"] for p in candidates]}
            return None
        if not candidates:
            failures[name] = {"status": "RETRIEVAL_UNAVAILABLE" if len(unavailable) == len(providers) else "NO_MATCH",
                              "code": "QRH003_SOURCE_IMPORT_UNRESOLVED", "unavailable_provider_ids": unavailable}
            return None
        provider = candidates[0]
        record = {"module": name, "package": provider["package"], "provider_id": provider["provider_id"],
                  "relative_path": relative, "source_profile": provider["source_profile"],
                  "sha256": None, "git_blob_sha1": None, "bytes": None, "lines": None,
                  "source_identity_status": "UNVERIFIED", "direct_imports": [], "reasons": []}
        modules[name] = record
        try:
            data = secure_read(provider["path"], relative)
            source_bytes += len(data)
            record.update(sha256=sha256_bytes(data), git_blob_sha1=blob_sha1(data), bytes=len(data))
            if source_bytes > max_source_bytes:
                raise AuditError("QRH003_SOURCE_RESOURCE_LIMIT", name)
            if provider["identity_status"] != "VERIFIED":
                record["reasons"].append({"code": "QRH003_SOURCE_PROVIDER_IDENTITY_UNVERIFIED"})
            elif provider["source_profile"] == "pinned_git_source":
                git_relative = provider["source_subdir"] + "/" + relative if provider["source_subdir"] else relative
                expected = provider["tree"].get(git_relative)
                record["git_relative_path"] = git_relative
                record["expected_git_blob_sha1"] = expected["oid"] if expected else None
                if expected is None or expected["type"] != "blob" or expected["mode"] not in ("100644", "100755"):
                    record["reasons"].append({"code": "QRH003_SOURCE_MODULE_NOT_IN_PIN"})
                elif expected["oid"] != record["git_blob_sha1"]:
                    record["reasons"].append({"code": "QRH003_SOURCE_MODULE_DIGEST_MISMATCH"})
                else:
                    record["source_identity_status"] = "VERIFIED"
            else:
                expected = provider.get("effective_files", {}).get(relative)
                record["expected_effective_sha256"] = expected["sha256"] if expected else None
                if expected is None or expected.get("sha256") != record["sha256"] or expected.get("git_blob_sha1") != record["git_blob_sha1"]:
                    record["reasons"].append({"code": "QRH003_EFFECTIVE_SOURCE_MODULE_DIGEST_MISMATCH"})
                else:
                    record["source_identity_status"] = "VERIFIED"
            parsed = parse_lean_source(data)
            record["parse"] = parsed
            record["lines"] = parsed.get("lines")
            record["reasons"].extend(parsed["errors"])
            for imported in parsed["imports"]:
                record["direct_imports"].append(imported["module"])
                edges.append({"from": name, "to": imported["module"], "kind": "explicit_import",
                              **{k: imported[k] for k in ("line", "public", "meta", "all")}})
            if parsed["status"] == "MATCH" and name != "Init" and not parsed["prelude"]:
                record["direct_imports"].append("Init")
                edges.append({"from": name, "to": "Init", "kind": "inferred_default_prelude"})
            return record["direct_imports"]
        except (OSError, AuditError) as exc:
            record["reasons"].append({"code": getattr(exc, "code", "QRH003_SOURCE_READ_UNAVAILABLE"), "detail": str(exc)})
            failures[name] = {"status": "RETRIEVAL_UNAVAILABLE", "code": record["reasons"][-1]["code"]}
            return None

    def visit(starts: Sequence[str]) -> dict:
        seen, frontier, queue = set(), set(), deque(starts)
        while queue:
            name = queue.popleft()
            if name in seen or name in frontier:
                continue
            imports = resolve(name)
            if imports is None:
                frontier.add(name)
                continue
            seen.add(name)
            queue.extend(imports)
        return {"modules": sorted(seen), "unresolved_frontier": sorted(frontier),
                "module_count": len(seen), "source_bytes": sum(modules[m]["bytes"] or 0 for m in seen),
                "source_lines": sum(modules[m]["lines"] or 0 for m in seen),
                "by_package": dict(sorted(Counter(modules[m]["package"] for m in seen).items()))}

    for root in root_modules:
        result["per_root"][root] = visit([root])
    result["union"] = visit(root_modules)
    module_errors = [name for name, value in modules.items() if value["reasons"]]
    lexical_errors = [name for name, value in modules.items() if value.get("parse", {}).get("status") != "MATCH"]
    identities_match = bool(modules) and all(value["source_identity_status"] == "VERIFIED" for value in modules.values())
    graph_match = bool(modules) and not failures and not lexical_errors
    result.update(static_graph_status="MATCH" if graph_match else "PARTIAL_MATCH" if modules else
                  "RETRIEVAL_UNAVAILABLE" if not any(p["status"] == "OBSERVED" for p in providers) else "NO_MATCH",
                  source_identity_status="VERIFIED" if identities_match else "PARTIAL_MATCH" if modules else "UNVERIFIED")
    result["discovery_status"] = "MATCH" if graph_match and identities_match and not module_errors else result["static_graph_status"] if not graph_match else "PARTIAL_MATCH"
    result["modules_with_errors"] = sorted(module_errors)
    result["parser_error_modules"] = sorted(lexical_errors)
    result["providers"] = []
    for provider in providers:
        public = {key: value for key, value in provider.items()
                  if key not in ("tree", "effective_files", "declaration", "verification")}
        for key in ("path", "git_root"):
            if isinstance(public.get(key), Path):
                public[key] = str(public[key])
        public["observation_scope"] = "available_provider_inventory"
        result["providers"].append(public)
    manifest = [{key: value[key] for key in ("module", "package", "relative_path", "source_profile", "sha256", "git_blob_sha1", "bytes")}
                for name, value in sorted(modules.items())]
    normalized_edges = sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["kind"], edge.get("line", 0)))
    result.update(source_manifest=manifest, source_manifest_sha256=sha256_bytes(canonical_bytes(manifest)),
                  import_graph_sha256=sha256_bytes(canonical_bytes({"roots": list(root_modules), "edges": normalized_edges})))
    result["lexical_hit_module_counts_by_package"] = {
        package: dict(sorted(Counter(hit for value in modules.values() if value["package"] == package
                                    for hit in value.get("parse", {}).get("lexical_hits", {})).items()))
        for package in sorted({value["package"] for value in modules.values()})}
    result["completion_boundary"] = {
        "available_static_source_fixed_point": graph_match,
        "all_locked_providers_retrieved": result["provider_universe_status"] == "MATCH",
        "compiler_resolved_fixed_point_verified": False,
        "all_runtime_or_precompiled_components_verified": False,
        "axiom_tokens_interpreted_as_target_dependencies": False,
        "release_authority_granted": False,
    }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--dependency-root", type=Path)
    parser.add_argument("--lean-source-root", type=Path)
    parser.add_argument("--effective-destination", type=Path)
    parser.add_argument("--acquisition", type=Path,
                        help="Existing acquisition observation; authentication remains the caller's responsibility")
    parser.add_argument("--root-module", action="append", dest="root_modules")
    parser.add_argument("--max-modules", type=int, default=200000)
    parser.add_argument("--max-source-bytes", type=int, default=2_147_483_648)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.acquisition:
        acquisition = read_json(args.acquisition)
    else:
        if args.source_root is None or args.dependency_root is None:
            parser.error("--source-root and --dependency-root are required without --acquisition")
        acquisition = collect_acquisition(args.source_root, args.dependency_root,
            lean_source_root=args.lean_source_root, effective_destination=args.effective_destination)
    for declaration in acquisition["source_roots"]:
        for field in ("path", "git_root"):
            root = Path(declaration[field]).resolve()
            output = args.output.resolve()
            if output == root or root in output.parents:
                parser.error("output must be outside input source repositories")
    result = resolve_static_source_closure(acquisition["source_roots"], args.root_modules or DEFAULT_ROOT_MODULES,
        provider_universe_status=acquisition.get("provider_universe_status"),
        max_modules=args.max_modules, max_source_bytes=args.max_source_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(result["discovery_status"])
    return 0 if result["discovery_status"] == "MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
