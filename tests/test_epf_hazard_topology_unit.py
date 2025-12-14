import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_topology import (
    compute_hazard_topology,
    REGION_STABLY_GOOD,
    REGION_UNSTABLY_GOOD,
    REGION_STABLY_BAD,
    REGION_UNSTABLY_BAD,
    REGION_UNKNOWN,
)


def test_topology_stably_good_excludes_hazard_gate_by_default():
    gates = {"a": True, "b": True, "epf_hazard_ok": False}
    topo = compute_hazard_topology(gates, hazard_zone="GREEN")
    assert topo.region == REGION_STABLY_GOOD
    assert topo.baseline_ok is True
    assert topo.stable is True


def test_topology_unstably_good():
    gates = {"a": True, "b": True}
    topo = compute_hazard_topology(gates, hazard_zone="AMBER")
    assert topo.region == REGION_UNSTABLY_GOOD
    assert topo.baseline_ok is True
    assert topo.stable is False


def test_topology_stably_bad():
    gates = {"a": True, "b": False}
    topo = compute_hazard_topology(gates, hazard_zone="GREEN")
    assert topo.region == REGION_STABLY_BAD
    assert topo.baseline_ok is False
    assert topo.stable is True


def test_topology_unstably_bad():
    gates = {"a": True, "b": False}
    topo = compute_hazard_topology(gates, hazard_zone="RED")
    assert topo.region == REGION_UNSTABLY_BAD
    assert topo.baseline_ok is False
    assert topo.stable is False


def test_topology_unknown_zone():
    gates = {"a": True}
    topo = compute_hazard_topology(gates, hazard_zone="???")
    assert topo.region == REGION_UNKNOWN
    assert topo.baseline_ok is True
    assert topo.stable is None
