"""Synthetic TEST-only source and acquisition boundary tests.

These fixtures exercise the actual named content evaluators.  They are not QRH
proof evidence, do not use production signing keys, and emit no certificates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import acquire
import source_closure
from common import AuditError, canonical_bytes, sha256_bytes

try:
    from . import test_authority as authority_fixtures
except ImportError:
    import test_authority as authority_fixtures
from tools import common as bundle_common, verify as bundle_verify


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                               text=True, check=True, env=acquire._git_env())
    return completed.stdout.strip()


def repository(parent: Path, name: str, files: dict[str, str | bytes],
               origin: str = "https://example.test/source.git") -> tuple[Path, str]:
    root = parent / name
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "remote", "add", "origin", origin)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    git(root, "add", "--all")
    git(root, "-c", "user.name=QRH synthetic tests", "-c", "user.email=test@example.invalid",
        "commit", "--quiet", "-m", "Synthetic fixture only")
    return root, git(root, "rev-parse", "HEAD")


def provider(root: Path, commit: str, name: str = "fixture") -> dict:
    return {"package": name, "path": str(root), "git_root": str(root),
            "expected_commit": commit, "source_subdir": "", "source_profile": "pinned_git_source"}


@unittest.skipUnless(shutil.which("git"), "git is required for the actual Git identity evaluator")
class GitSourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qrh003-source-test-")
        self.root = Path(self.temporary.name)
        self.repo, self.pin = repository(self.root, "source", {"Proof.lean": "prelude\ntheorem t : True := True.intro\n"})

    def tearDown(self):
        self.temporary.cleanup()

    def test_actual_pinned_bytes_verified_without_build_inference(self):
        before = git(self.repo, "status", "--porcelain=v1")
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["files"][0]["git_blob_sha1"], git(self.repo, "rev-parse", self.pin + ":Proof.lean"))
        self.assertEqual(result["build_status"], "NOT_RUN")
        self.assertEqual(git(self.repo, "status", "--porcelain=v1"), before)

    def test_N01_missing_critical_source_reaches_identity_evaluator(self):
        (self.repo / "Proof.lean").unlink()
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertNotEqual(result["status"], "VERIFIED")
        self.assertIn("QRH003_SUBJECT_CRITICAL_FILE_MISSING", {x["code"] for x in result["reasons"]})

    def test_N02_changed_bytes_rejected_with_specific_digest_reason(self):
        (self.repo / "Proof.lean").write_text("prelude\ntheorem t : True := by sorry\n")
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("QRH003_SUBJECT_DIGEST_MISMATCH", {x["code"] for x in result["reasons"]})

    def test_selected_sha256_binding_is_checked_in_addition_to_git(self):
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"], expected_sha256={"Proof.lean": "0" * 64})
        self.assertEqual(result["status"], "MISMATCH")
        self.assertEqual(result["files"][0]["reasons"][0]["code"], "QRH003_SUBJECT_DIGEST_MISMATCH")

    def test_changed_head_is_not_silently_used_in_place_of_selected_commit(self):
        (self.repo / "Unrelated.txt").write_text("next revision")
        git(self.repo, "add", "--all")
        git(self.repo, "-c", "user.name=QRH synthetic tests", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "Synthetic changed head")
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("QRH003_UPSTREAM_COMMIT_MISMATCH", {x["code"] for x in result["reasons"]})
        self.assertEqual(result["expected_commit"], self.pin)

    def test_branch_name_cannot_replace_full_commit(self):
        result = acquire.verify_git_snapshot(self.repo, "main", ["Proof.lean"])
        self.assertEqual(result["status"], "MISMATCH")
        self.assertEqual(result["reasons"][0]["code"], "QRH003_SOURCE_COMMIT_NOT_PINNED")

    def test_origin_mismatch_preserved(self):
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"], expected_url="https://example.test/other.git")
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("QRH003_SOURCE_ORIGIN_MISMATCH", {x["code"] for x in result["reasons"]})

    def test_symlink_to_same_bytes_is_not_a_valid_source_replacement(self):
        original = self.repo / "Proof.lean"
        outside = self.root / "outside.lean"
        outside.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(outside)
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertNotEqual(result["status"], "VERIFIED")
        self.assertEqual(result["files"][0]["status"], "UNAVAILABLE")

    def test_fetch_into_existing_checkout_is_refused_without_running_git(self):
        with mock.patch.object(acquire, "_command") as command:
            result = acquire.fetch_pinned_repository("https://example.test/source.git", self.pin, self.repo)
        command.assert_not_called()
        self.assertEqual(result["reasons"][0]["code"], "QRH003_FETCH_DESTINATION_EXISTS")

    def test_repository_fsmonitor_canary_is_never_executed(self):
        marker = self.root / "fsmonitor-was-executed"
        hook = self.root / "fsmonitor"
        hook.write_text("#!/bin/sh\ntouch '" + str(marker) + "'\n")
        hook.chmod(0o755)
        git(self.repo, "config", "core.fsmonitor", str(hook))
        result = acquire.verify_git_snapshot(self.repo, self.pin, ["Proof.lean"])
        self.assertEqual(result["status"], "VERIFIED")
        self.assertFalse(marker.exists())
        self.assertIsNone(result["worktree_clean"])
        self.assertEqual(result["worktree_clean_status"], "NOT_ASSESSED")
        self.assertFalse(any("status" in command["argv"] for command in result["commands"]))

    def test_inherited_git_and_dynamic_loader_environment_are_removed(self):
        injected = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
                    "GIT_CONFIG_VALUE_0": "untrusted", "GIT_EXEC_PATH": "/untrusted",
                    "LD_PRELOAD": "/untrusted.so", "LD_AUDIT": "/untrusted.so",
                    "DYLD_INSERT_LIBRARIES": "/untrusted.dylib"}
        with mock.patch.dict(os.environ, injected):
            env = acquire._git_env()
        self.assertTrue(all(key not in env for key in injected))
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(env["GIT_NO_REPLACE_OBJECTS"], "1")


class HeaderParserTests(unittest.TestCase):
    def test_nested_comments_strings_and_characters_do_not_invent_imports_or_sorry(self):
        source = b'''/- import Hidden.One /- sorry -/ -/\nprelude\npublic meta import all Real.Module\ndef example := "import Hidden.Two sorryAx"\ndef character := '"'\n-- unsafe\n'''
        result = source_closure.parse_lean_source(source)
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual([x["module"] for x in result["imports"]], ["Real.Module"])
        self.assertEqual(result["lexical_hits"], {})
        self.assertEqual(result["imports"][0]["line"], 3)
        self.assertTrue(result["imports"][0]["public"])
        self.assertTrue(result["imports"][0]["meta"])
        self.assertTrue(result["imports"][0]["all"])

    def test_real_axiom_tokens_are_observations_not_axiom_profiles(self):
        source = b"prelude\naxiom unsupported : False\nunsafe def f := 0\ntheorem t : True := by sorry\ndef x := sorryAx\n"
        result = source_closure.parse_lean_source(source)
        self.assertEqual(set(result["lexical_hits"]), {"axiom_keyword", "unsafe", "sorry", "sorryAx"})
        self.assertEqual(result["lexical_hit_interpretation"], "REQUIRES_TARGET_AXIOM_EXPORT_AND_CODE_REVIEW")

    def test_multiline_header_modifiers_and_import_are_preserved(self):
        result = source_closure.parse_lean_source(b"module\nprelude\npublic\nmeta import\n all\n A.B\n#check True\n")
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["imports"][0]["module"], "A.B")

    def test_raw_string_is_not_scanned_as_code(self):
        result = source_closure.parse_lean_source(b'prelude\ndef x := r#"a "quote" sorryAx import Fake"#\n')
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["lexical_hits"], {})
        self.assertEqual(result["imports"], [])

    def test_unclosed_lexical_context_never_uses_raw_fallback(self):
        result = source_closure.parse_lean_source(b"/- unterminated\nimport Fake\n")
        self.assertEqual(result["status"], "PARTIAL_MATCH")
        self.assertEqual(result["imports"], [])
        self.assertEqual(result["errors"][0]["code"], "QRH003_LEAN_UNCLOSED_COMMENT")

    def test_invalid_utf8_preserves_unavailability(self):
        result = source_closure.parse_lean_source(b"prelude\n\xff")
        self.assertEqual(result["status"], "PARTIAL_MATCH")
        self.assertEqual(result["errors"][0]["code"], "QRH003_LEAN_INVALID_UTF8")

    def test_import_after_unrecognized_header_is_not_silently_ignored(self):
        result = source_closure.parse_lean_source(b"theorem t : True := True.intro\nimport Later\n")
        self.assertEqual(result["status"], "PARTIAL_MATCH")
        self.assertEqual(result["errors"][0]["code"], "QRH003_LEAN_IMPORT_OUTSIDE_RECOGNIZED_HEADER")

    def test_escaped_module_segment_keeps_literal_dot(self):
        self.assertEqual(source_closure.module_relative_path("A.«B.C».D"), "A/B.C/D.lean")
        result = source_closure.parse_lean_source("prelude\nimport A.«B.C».D\n".encode())
        self.assertEqual(result["imports"][0]["module"], "A.«B.C».D")

    def test_module_path_traversal_is_rejected(self):
        for module in ("../Outside", "A..B", "A/B", "A.\u00ab..\u00bb", "/A", "A.\\B"):
            with self.subTest(module=module), self.assertRaises(AuditError):
                source_closure.module_relative_path(module)


@unittest.skipUnless(shutil.which("git"), "git is required for actual source resolution")
class StaticClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qrh003-closure-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_transitive_fixed_point_hashes_actual_module_bytes(self):
        root, pin = repository(self.root, "closed", {"A.lean": "prelude\nimport B\n", "B.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"], provider_universe_status="MATCH")
        self.assertEqual(result["discovery_status"], "MATCH")
        self.assertEqual(result["source_identity_status"], "VERIFIED")
        self.assertEqual(result["union"]["modules"], ["A", "B"])
        self.assertEqual(result["modules"]["B"]["sha256"], sha256_bytes((root / "B.lean").read_bytes()))
        self.assertEqual(result["compiler_resolved_imports_status"], "NOT_RUN")
        self.assertEqual(result["axiom_profile_status"], "NOT_RUN")
        self.assertFalse(result["completion_boundary"]["release_authority_granted"])

    def test_NO_MATCH_is_distinct_from_unavailable_provider(self):
        root, pin = repository(self.root, "available", {"Other.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["Absent"])
        self.assertEqual(result["discovery_status"], "NO_MATCH")
        self.assertEqual(result["resolution_failures"]["Absent"]["status"], "NO_MATCH")
        missing = provider(self.root / "unretrieved", pin)
        unavailable = source_closure.resolve_static_source_closure([missing], ["Absent"])
        self.assertEqual(unavailable["discovery_status"], "RETRIEVAL_UNAVAILABLE")
        self.assertEqual(unavailable["resolution_failures"]["Absent"]["status"], "RETRIEVAL_UNAVAILABLE")

    def test_N05_partial_dependency_reaches_import_fixed_point_evaluator(self):
        # The committed identity is coherent and intentionally contains no B;
        # rejection is generated by traversal, not a previous hash mismatch.
        root, pin = repository(self.root, "partial", {"A.lean": "prelude\nimport B\n"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"])
        self.assertEqual(result["modules"]["A"]["source_identity_status"], "VERIFIED")
        self.assertEqual(result["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(result["resolution_failures"]["B"]["code"], "QRH003_SOURCE_IMPORT_UNRESOLVED")
        self.assertEqual(result["union"]["unresolved_frontier"], ["B"])

    def test_two_equal_byte_providers_are_still_ambiguous(self):
        first, first_pin = repository(self.root, "first", {"A.lean": "prelude\n"})
        second, second_pin = repository(self.root, "second", {"A.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure(
            [provider(first, first_pin, "first"), provider(second, second_pin, "second")], ["A"])
        self.assertNotEqual(result["discovery_status"], "MATCH")
        self.assertEqual(result["resolution_failures"]["A"]["code"], "QRH003_SOURCE_IMPORT_AMBIGUOUS")
        self.assertNotIn("A", result["modules"])

    def test_implicit_Init_is_an_explicitly_typed_inferred_edge(self):
        root, pin = repository(self.root, "implicit", {"A.lean": "theorem t : True := True.intro\n", "Init.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"])
        self.assertEqual(result["discovery_status"], "MATCH")
        self.assertEqual(result["edges"], [{"from": "A", "to": "Init", "kind": "inferred_default_prelude"}])

    def test_changed_transitive_bytes_fail_even_when_imports_are_unchanged(self):
        root, pin = repository(self.root, "changed", {"A.lean": "prelude\nimport B\n", "B.lean": "prelude\n"})
        (root / "B.lean").write_text("prelude\n-- bytes changed\n")
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"])
        self.assertEqual(result["static_graph_status"], "MATCH")
        self.assertEqual(result["source_identity_status"], "PARTIAL_MATCH")
        self.assertEqual(result["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(result["modules"]["B"]["reasons"][0]["code"], "QRH003_SOURCE_MODULE_DIGEST_MISMATCH")

    def test_missing_unreached_lock_provider_does_not_disappear(self):
        root, pin = repository(self.root, "reachable", {"A.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure(
            [provider(root, pin), provider(self.root / "missing", pin, "unretrieved")], ["A"],
            provider_universe_status="PARTIAL_MATCH")
        self.assertEqual(result["discovery_status"], "MATCH")
        self.assertEqual(result["provider_universe_status"], "PARTIAL_MATCH")
        self.assertEqual(result["providers"][1]["status"], "RETRIEVAL_UNAVAILABLE")
        self.assertFalse(result["completion_boundary"]["all_locked_providers_retrieved"])

    def test_lexical_failure_cannot_be_complete(self):
        root, pin = repository(self.root, "broken", {"A.lean": "prelude\n/- unfinished"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"])
        self.assertEqual(result["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(result["parser_error_modules"], ["A"])
        self.assertFalse(result["completion_boundary"]["available_static_source_fixed_point"])

    def test_resource_limit_keeps_unvisited_frontier(self):
        root, pin = repository(self.root, "limited", {"A.lean": "prelude\nimport B\n", "B.lean": "prelude\n"})
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A"], max_modules=1)
        self.assertEqual(result["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(result["resolution_failures"]["B"]["code"], "QRH003_SOURCE_RESOURCE_LIMIT")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO regression requires POSIX")
    def test_FIFO_rejected_without_blocking_and_failure_survives_all_traversals(self):
        root, pin = repository(self.root, "fifo", {"A.lean": "prelude\nimport B\n", "B.lean": "prelude\n"})
        (root / "B.lean").unlink()
        os.mkfifo(root / "B.lean")
        result = source_closure.resolve_static_source_closure([provider(root, pin)], ["A", "B"])
        self.assertEqual(result["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(result["resolution_failures"]["B"]["code"], "NONREGULAR_ARTIFACT")
        self.assertEqual(result["union"]["unresolved_frontier"], ["B"])
        self.assertEqual(result["per_root"]["B"]["unresolved_frontier"], ["B"])

    def test_unapplied_required_patch_prevents_source_identity_pass(self):
        root, pin = repository(self.root, "unpatched", {"A.lean": "prelude\n"})
        declaration = {**provider(root, pin), "required_patch_unapplied": True}
        result = source_closure.resolve_static_source_closure([declaration], ["A"])
        self.assertEqual(result["static_graph_status"], "MATCH")
        self.assertNotEqual(result["source_identity_status"], "VERIFIED")
        self.assertEqual(result["provider_errors"][0]["code"], "QRH003_REQUIRED_PATCH_NOT_MATERIALIZED")


class LockAndPatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qrh003-lock-test-")
        self.root = Path(self.temporary.name)
        (self.root / "lean/patches").mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def test_all_42_lock_records_retained_when_no_dependency_retrieved(self):
        packages = [{"name": f"package{index}", "rev": "a" * 40, "type": "git",
                     "url": f"https://example.test/package{index}.git", "subDir": None,
                     "configFile": "lakefile.toml", "inputRev": "main"} for index in range(42)]
        (self.root / "lean/lake-manifest.json").write_text(json.dumps({"version": "1.2.0", "packages": packages}))
        result = acquire.inventory_locked_dependencies(self.root, {})
        self.assertEqual(result["record_count"], 42)
        self.assertEqual(len(result["records"]), 42)
        self.assertEqual(result["unavailable_count"], 42)
        self.assertEqual(result["discovery_status"], "RETRIEVAL_UNAVAILABLE")
        self.assertTrue(all(x["status"] == "RETRIEVAL_UNAVAILABLE" for x in result["records"]))
        self.assertTrue(all(x["lock_record"]["inputRev"] == "main" for x in result["records"]))

    def test_unpinned_lock_record_has_its_own_explicit_reason(self):
        packages = [{"name": "unfixed", "rev": "main", "type": "git", "url": "https://example.test/package.git"}]
        (self.root / "lean/lake-manifest.json").write_text(json.dumps({"packages": packages}))
        result = acquire.inventory_locked_dependencies(self.root, {}, expected_count=1)
        self.assertEqual(result["records"][0]["status"], "MISMATCH")
        self.assertEqual(result["records"][0]["reasons"][0]["code"], "QRH003_DEPENDENCY_NOT_PINNED")

    def patch_fixture(self):
        pre = ", ".join("`«" + name + "»" for name in acquire.PRE_RESOLUTION_PATCHES)
        post = ", ".join("`«" + name + "»" for name in acquire.POST_UPDATE_PATCHES)
        lake = f"private def preResolutionPatchNames : Array Lean.Name := #[{pre}]\npost_update pkg do\n for name in preResolutionPatchNames do pure ()\n for name in #[{post}] do pure ()\n"
        (self.root / "lean/lakefile.lean").write_text(lake)
        for name in acquire.PRE_RESOLUTION_PATCHES + acquire.POST_UPDATE_PATCHES:
            (self.root / f"lean/patches/{name}-lean4341.patch").write_text("synthetic patch bytes\n")

    def test_23_patch_records_and_11_rechecks_keep_declared_phase_order(self):
        self.patch_fixture()
        result = acquire.discover_patch_plan(self.root)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(len(result["records"]), 23)
        rechecks = [x for x in result["events"] if x["action"] == "reverify_pre_resolution_patch"]
        self.assertEqual([x["package"] for x in rechecks], list(acquire.PRE_RESOLUTION_PATCHES))
        self.assertEqual(result["records"][10]["package"], "belyi")
        self.assertEqual(result["records"][11]["package"], "fixed-point-theorems")
        self.assertEqual(result["records"][22]["package"], "gromov")
        self.assertEqual(result["declaration_execution"], "NOT_RUN")

    def test_missing_patch_keeps_partial_plan_instead_of_22_complete_records(self):
        self.patch_fixture()
        (self.root / "lean/patches/belyi-lean4341.patch").unlink()
        result = acquire.discover_patch_plan(self.root)
        self.assertEqual(result["status"], "PARTIAL_MATCH")
        self.assertEqual(len(result["records"]), 23)
        self.assertEqual(result["records"][10]["status"], "MISSING")

    def test_changed_phase_order_cannot_be_silently_accepted(self):
        self.patch_fixture()
        path = self.root / "lean/lakefile.lean"
        path.write_text(path.read_text().replace("`«iut», `«tate-curves-theta»", "`«tate-curves-theta», `«iut»"))
        result = acquire.discover_patch_plan(self.root)
        self.assertEqual(result["status"], "PARTIAL_MATCH")
        self.assertEqual(result["reasons"][0]["code"], "QRH003_PATCH_PHASE_ORDER_MISMATCH")

    def test_patch_application_not_requested_does_not_write_destination(self):
        self.patch_fixture()
        destination = self.root / "unused"
        result = acquire.materialize_effective_sources(self.root, {"records": []}, destination)
        self.assertFalse(destination.exists())
        self.assertEqual(len(result["records"]), 23)
        self.assertTrue(all(x["materialization_status"] == "NOT_REQUESTED" for x in result["records"]))

    def test_quoted_package_name_is_normalized_without_path_escape(self):
        self.assertEqual(acquire.package_directory_name("«rellich-kondrachov»"), "rellich-kondrachov")
        with self.assertRaises(AuditError):
            acquire.package_directory_name("«../outside»")

    @unittest.skipUnless(shutil.which("git"), "git is required for the real patch engine")
    def test_patch_under_git_parent_applies_all_files_and_new_import_is_traversed(self):
        self.patch_fixture()
        old, new, added = b"prelude\n", b"prelude\nimport Added\n", b"prelude\n"
        patch = ("diff --git a/A.lean b/A.lean\n"
                 f"index {acquire.blob_sha1(old)}..{acquire.blob_sha1(new)} 100644\n"
                 "--- a/A.lean\n+++ b/A.lean\n@@ -1 +1,2 @@\n prelude\n+import Added\n"
                 "diff --git a/Added.lean b/Added.lean\nnew file mode 100644\n"
                 f"index {'0' * 40}..{acquire.blob_sha1(added)}\n"
                 "--- /dev/null\n+++ b/Added.lean\n@@ -0,0 +1 @@\n+prelude\n")
        (self.root / "lean/patches/PrimeNumberTheoremAnd-lean4341.patch").write_text(patch)
        source_files = {path.relative_to(self.root).as_posix(): path.read_bytes()
                        for path in (self.root / "lean").rglob("*") if path.is_file()}
        upstream, upstream_pin = repository(self.root, "upstream", source_files)
        base, base_pin = repository(self.root, "base", {"A.lean": old})
        outer, outer_pin = repository(self.root, "outer", {"README.md": "Synthetic outer repository\n"})
        destination = outer / "outputs/effective"
        dependencies = {"records": [{"package": "PrimeNumberTheoremAnd", "status": "VERIFIED",
            "path": str(base), "lock_record": {"rev": base_pin, "url": "https://example.test/source.git"}}]}
        with mock.patch.object(acquire, "UPSTREAM_COMMIT", upstream_pin):
            result = acquire.materialize_effective_sources(upstream, dependencies, destination, apply_patches=True)
        overlay = next(record for record in result["records"] if record["package"] == "PrimeNumberTheoremAnd")
        self.assertEqual(overlay["materialization_status"], "VERIFIED", overlay.get("reasons"))
        self.assertEqual(overlay["changed_paths"], ["A.lean", "Added.lean"])
        self.assertEqual(overlay["expected_changed_paths"], ["A.lean", "Added.lean"])
        self.assertEqual((base / "A.lean").read_bytes(), old)
        self.assertFalse((base / "Added.lean").exists())
        self.assertEqual(git(outer, "rev-parse", "HEAD"), outer_pin)
        declaration = {**provider(base, base_pin, "PrimeNumberTheoremAnd"),
                       "path": overlay["effective_path"], "source_profile": "patch_derived_overlay",
                       "effective_manifest": overlay}
        closure = source_closure.resolve_static_source_closure([declaration], ["A"])
        self.assertEqual(closure["discovery_status"], "MATCH")
        self.assertEqual(closure["union"]["modules"], ["A", "Added"])
        (Path(overlay["effective_path"]) / "Added.lean").write_text("prelude\nimport Ghost\n")
        changed = source_closure.resolve_static_source_closure([declaration], ["A"])
        self.assertEqual(changed["discovery_status"], "PARTIAL_MATCH")
        self.assertEqual(changed["modules"]["Added"]["reasons"][0]["code"], "QRH003_EFFECTIVE_SOURCE_MODULE_DIGEST_MISMATCH")
        self.assertEqual(changed["resolution_failures"]["Ghost"]["code"], "QRH003_SOURCE_IMPORT_UNRESOLVED")


class SignedBundleInventoryTests(unittest.TestCase):
    """Real TEST signatures and admission; no native proof or gate spoofing.

    Compose the existing signing fixture without importing its TestCase class
    into this module, which would rediscover its unrelated test methods.
    Every mutation starts from an actually admitted, closed signed bundle.
    """

    def setUp(self):
        self.fixture = authority_fixtures.AuthorityBoundaryTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.assert_admitted()

    def assert_admitted(self):
        result = bundle_verify.verify_bundle(self.fixture.bundle, self.fixture.anchor_path)
        self.assertEqual(result['anchor']['trust_domain'], 'TEST')
        self.assertEqual(set(result['snapshot']['files']), set(self.fixture.files))
        self.assertEqual(result['snapshot']['manifest_signature_sha256'],
                         sha256_bytes((self.fixture.bundle / 'manifest.signature.json').read_bytes()))
        self.assertFalse(any(result['evaluation']['gates'].values()))
        return result

    def assert_rejected(self, code):
        sealed = {name: (self.fixture.bundle / name).read_bytes()
                  for name in ('manifest.json', 'manifest.signature.json')}
        with self.assertRaises(bundle_common.AuditError) as raised:
            bundle_verify.verify_bundle(self.fixture.bundle, self.fixture.anchor_path)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(sealed, {name: (self.fixture.bundle / name).read_bytes()
                                  for name in sealed})

    def test_signed_bundle_inventory_rejects_unlisted_status_after_sealing(self):
        self.fixture.bundle.joinpath('status.json').write_bytes(b'{"gates":{"injected":true}}')
        self.assert_rejected('QRH003_BUNDLE_INVENTORY_MISMATCH')

    def test_signed_bundle_inventory_rejects_unlisted_nested_diagnostic(self):
        self.fixture.bundle.joinpath('evidence/diagnostic.txt').write_bytes(b'unsigned diagnostic')
        self.assert_rejected('QRH003_BUNDLE_INVENTORY_MISMATCH')

    def test_signed_bundle_inventory_controls_are_exempt_only_at_root(self):
        for name in ('manifest.json', 'manifest.signature.json'):
            with self.subTest(name=name):
                path = self.fixture.bundle / 'evidence' / name
                path.write_bytes((self.fixture.bundle / name).read_bytes())
                try:
                    self.assert_rejected('QRH003_BUNDLE_INVENTORY_MISMATCH')
                finally:
                    path.unlink()

    def test_signed_bundle_inventory_rejects_unlisted_empty_directory(self):
        self.fixture.bundle.joinpath('evidence/unsigned').mkdir()
        self.assert_rejected('QRH003_BUNDLE_INVENTORY_MISMATCH')

    def test_signed_bundle_inventory_accepts_declared_nested_files(self):
        # Nested control-like basenames are ordinary data only when explicitly
        # listed and signed; only the two exact root files are control objects.
        self.fixture.files['evidence/nested/status.json'] = b'{"record":"TEST data"}'
        self.fixture.files['evidence/nested/manifest.json'] = b'{"record":"TEST manifest data"}'
        self.fixture.files['logs/deeper/diagnostic.txt'] = b'listed diagnostic'
        self.fixture.rebind()
        self.assert_admitted()

    def test_signed_bundle_inventory_rejects_unlisted_file_symlink(self):
        outside = self.fixture.home / 'outside-data'
        outside.write_bytes(b'unsigned data')
        self.fixture.bundle.joinpath('unsigned-link').symlink_to(outside)
        self.assert_rejected('QRH003_SYMLINK_REJECTED')

    def test_signed_bundle_inventory_rejects_unlisted_directory_symlink(self):
        outside = self.fixture.home / 'outside-directory'
        outside.mkdir()
        outside.joinpath('status.json').write_bytes(b'{}')
        self.fixture.bundle.joinpath('unsigned-directory').symlink_to(outside, target_is_directory=True)
        self.assert_rejected('QRH003_SYMLINK_REJECTED')

    def test_signed_bundle_inventory_rejects_dangling_symlink(self):
        self.fixture.bundle.joinpath('dangling').symlink_to(self.fixture.home / 'does-not-exist')
        self.assert_rejected('QRH003_SYMLINK_REJECTED')

    def test_signed_bundle_inventory_rejects_unlisted_fifo_without_opening_it(self):
        os.mkfifo(self.fixture.bundle / 'unsigned-fifo')
        self.assert_rejected('QRH003_NONREGULAR_BUNDLE_ENTRY')

    def test_signed_bundle_inventory_rejects_missing_declared_member(self):
        self.fixture.bundle.joinpath('evidence/control.json').unlink()
        self.assert_rejected('UNSAFE_OR_MISSING_ARTIFACT')

    def test_signed_bundle_inventory_rejects_signed_duplicate_member(self):
        self.fixture.manifest['artifacts'].append(dict(self.fixture.manifest['artifacts'][0]))
        self.fixture.write_manifest()
        self.assert_rejected('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED')

    def test_signed_bundle_inventory_rejects_signed_reserved_members(self):
        original = list(self.fixture.manifest['artifacts'])
        for name in sorted(bundle_verify.RESERVED_INPUT_PATHS):
            with self.subTest(name=name):
                self.fixture.manifest['artifacts'] = original + [{
                    'path': name, 'sha256': sha256_bytes(b'{}'), 'bytes': 2,
                    'role': 'test_control', 'evidence_class': 'synthetic_fixture',
                }]
                self.fixture.write_manifest()
                self.assert_rejected('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED')

    def test_signed_bundle_inventory_rejects_reserved_root_as_directory(self):
        self.fixture.files['status.json/payload.json'] = b'{}'
        self.fixture.rebind()
        self.assert_rejected('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED')


if __name__ == "__main__":
    unittest.main()
