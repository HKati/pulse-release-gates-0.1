from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_target_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "pages_publish_paradox_core_bundle_v0.py"
    spec = spec_from_file_location("pages_publish_paradox_core_bundle_v0", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def target():
    return _load_target_module()


@pytest.mark.parametrize(
    "mount, expected",
    [
        ("paradox/core", ["paradox", "core"]),
        ("  paradox/core  ", ["paradox", "core"]),
        ("paradox", ["paradox"]),
        ("paradox/core/", ["paradox", "core"]),
        ("paradox/core///", ["paradox", "core"]),
    ],
)
def test_safe_mount_parts_accepts_valid_mounts(target, mount, expected):
    assert target._safe_mount_parts(mount) == expected


@pytest.mark.parametrize(
    "mount",
    [
        "",
        "   ",
        "/",
        "///",
        "/paradox/core",
        "paradox\\core",
        "a//b",
        "a/./b",
        "a/../b",
        "./a",
        "../a",
        "a/.",
        "a/..",
    ],
)
def test_safe_mount_parts_rejects_unsafe_mounts(target, mount):
    with pytest.raises(SystemExit):
        target._safe_mount_parts(mount)
