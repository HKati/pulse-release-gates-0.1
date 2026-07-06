import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / "pulse_gate_policy_v0.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
POLICY_TO_REQUIRE_ARGS = ROOT / "tools" / "policy_to_require_args.py"

SLSA_VSA_GATES = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]

REQUIRED_LIKE_SETS = [
    "required",
    "core_required",
    "release_required",
]

FORBIDDEN_BLOCKING_SET_NAMES = [
    "required",
    "core_required",
    "release_required",
    "prod_required",
    "stage_required",
    "blocking",
    "release_blocking",
]


def _strip_inline_comment(text: str) -> str:
    return text.split("#", 1)[0].strip()


def _parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []

    inner = value[1:-1].strip()
    if not inner:
        return []

    return [part.strip() for part in inner.split(",") if part.strip()]


def _extract_gate_set(text: str, gate_set: str) -> tuple[bool, list[str]]:
    lines = text.splitlines()

    in_gates = False
    in_set = False
    gates_indent = None
    set_indent = None
    found_set = False
    out: list[str] = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        clean = _strip_inline_comment(stripped)
        if not clean:
            continue

        indent = len(line) - len(line.lstrip(" "))

        if clean == "gates:":
            in_gates = True
            in_set = False
            gates_indent = indent
            set_indent = None
            continue

        if in_gates and gates_indent is not None and indent <= gates_indent and ":" in clean and clean != "gates:":
            in_gates = False
            in_set = False
            gates_indent = None
            set_indent = None

        if not in_gates:
            continue

        if in_set and set_indent is not None and indent == set_indent and ":" in clean and not clean.startswith("-"):
            key = clean.split(":", 1)[0].strip()
            if key and key != gate_set:
                in_set = False
                set_indent = None

        if ":" in clean and not clean.startswith("-"):
            key, rest = clean.split(":", 1)
            key = key.strip()
            rest = rest.strip()

            if key == gate_set:
                found_set = True
                set_indent = indent

                if rest.startswith("[") and rest.endswith("]"):
                    out.extend(_parse_inline_list(rest))
                    in_set = False
                    continue

                in_set = True
                continue

        if not in_set:
            continue

        if clean.startswith("- "):
            gate_id = _strip_inline_comment(clean[2:])
            if gate_id:
                out.append(gate_id)

    return found_set, out


def _extract_registry_gate_block(text: str, gate_id: str) -> str:
    lines = text.splitlines()
    marker = f"  {gate_id}:"

    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == marker:
            start = index
            break

    if start is None:
        return ""

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            end = index
            break

    return "\n".join(lines[start:end])


def _policy_to_require_args(gate_set: str) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            str(POLICY_TO_REQUIRE_ARGS),
            "--policy",
            str(POLICY),
            "--set",
            gate_set,
            "--format",
            "newline",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_slsa_vsa_advisory_policy_gates_v0() -> None:
    assert POLICY.exists()
    assert REGISTRY.exists()
    assert POLICY_TO_REQUIRE_ARGS.exists()

    policy_text = POLICY.read_text(encoding="utf-8")
    registry_text = REGISTRY.read_text(encoding="utf-8")

    found_advisory, advisory_gates = _extract_gate_set(policy_text, "advisory")
    assert found_advisory, "advisory gate set is missing from pulse_gate_policy_v0.yml"

    missing_from_advisory = [gate for gate in SLSA_VSA_GATES if gate not in advisory_gates]
    assert not missing_from_advisory, f"SLSA VSA gates missing from advisory set: {missing_from_advisory}"

    for gate in SLSA_VSA_GATES:
        block = _extract_registry_gate_block(registry_text, gate)

        assert block, f"{gate} missing from pulse_gate_registry_v0.yml"
        assert "category: external" in block, f"{gate} must be an external evidence gate"
        assert "default_normative: false" in block, f"{gate} must remain non-normative by default"

    for gate_set in FORBIDDEN_BLOCKING_SET_NAMES:
        found_set, gates = _extract_gate_set(policy_text, gate_set)
        if not found_set:
            continue

        leaked = [gate for gate in SLSA_VSA_GATES if gate in gates]
        assert not leaked, f"SLSA VSA gates must not appear in {gate_set}: {leaked}"

    for gate_set in REQUIRED_LIKE_SETS:
        materialized = _policy_to_require_args(gate_set)
        leaked = [gate for gate in SLSA_VSA_GATES if gate in materialized]
        assert not leaked, f"policy_to_require_args materialized advisory SLSA VSA gates for {gate_set}: {leaked}"

    materialized_advisory = _policy_to_require_args("advisory")
    missing_from_materialized_advisory = [
        gate for gate in SLSA_VSA_GATES if gate not in materialized_advisory
    ]
    assert not missing_from_materialized_advisory, (
        "SLSA VSA gates missing from materialized advisory set: "
        f"{missing_from_materialized_advisory}"
    )


def test_slsa_vsa_advisory_policy_gates_v0() -> None:
    check_slsa_vsa_advisory_policy_gates_v0()


if __name__ == "__main__":
    check_slsa_vsa_advisory_policy_gates_v0()
    print("OK: SLSA VSA gates are registered and advisory-only")
