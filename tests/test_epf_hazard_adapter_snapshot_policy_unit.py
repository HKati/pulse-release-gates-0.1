import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import sanitize_snapshot_for_log


def test_snapshot_policy_allowed_prefixes_filters_keys():
    snap = {
        "a": 1.0,
        "b": 2.0,
        "nest": {
            "a": 3.0,
            "c": 4.0,
        },
    }

    sanitized, meta = sanitize_snapshot_for_log(
        snap,
        allowed_prefixes=["a", "nest.a"],
    )

    assert sanitized == {"a": 1.0, "nest": {"a": 3.0}}
    assert meta["kept"] == 2
    assert "policy" in meta
    assert "allowed_prefixes" in meta["policy"]


def test_snapshot_policy_deny_keys_drops_subtree():
    snap = {
        "keep": 1.0,
        "deny": {"x": 2.0, "y": 3.0},
    }

    sanitized, meta = sanitize_snapshot_for_log(
        snap,
        deny_keys=["deny"],
    )

    assert sanitized == {"keep": 1.0}
    assert meta["kept"] == 1
    assert "policy" in meta
    assert "deny_keys" in meta["policy"]


def test_snapshot_policy_allow_then_deny_specific_leaf():
    snap = {
        "metrics": {
            "RDSI": 0.9,
            "secret": 123.0,
        }
    }

    sanitized, meta = sanitize_snapshot_for_log(
        snap,
        allowed_prefixes=["metrics"],
        deny_keys=["metrics.secret"],
    )

    assert sanitized == {"metrics": {"RDSI": 0.9}}
    assert meta["kept"] == 1
