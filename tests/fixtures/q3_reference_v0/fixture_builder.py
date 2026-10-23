"""Materialize synthetic Q3 conformance inputs, never historical/model evidence.

The builder uses no evaluator or checker code. It computes byte bindings only;
expected metric outcomes live in case_expectations.json and the focused tests.
Each call creates a new, caller-selected synthetic expectation before any report
is read. Tests for a fixed-anchor attack deliberately retain the original bytes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE = "q3_input_recomputation_v0.1"
PRODUCER_PATH = "PULSE_safe_pack_v0/tools/build_q3_reference_summary.py"
CHECKER_PATH = "PULSE_safe_pack_v0/tools/check_q3_reference_summary.py"
RESOURCE_PATHS = {
    "contract_sha256": "PULSE_safe_pack_v0/profiles/q3_reference_recomputation_v0.json",
    "input_schema_sha256": "schemas/metrics/q3_input_bundle_v0.schema.json",
    "result_schema_sha256": "schemas/metrics/q3_reference_summary_v0.schema.json",
    "dataset_manifest_schema_sha256": "schemas/dataset_manifest.schema.json",
}
SPEC_PATHS = {
    "q1": "metrics/specs/q1_groundedness_v0.yml",
    "q3_baseline": "metrics/specs/q3_fairness_v0.yml",
}
VARIANTS = {
    26: ("null", "number", "boolean", "array", "object", "empty"),
    30: ("missing_dimensions", "empty_dimensions", "duplicate_dimensions"),
    31: ("changed_examples_bytes", "changed_q3_spec_bytes", "changed_q1_labels_bytes"),
    38: ("subject_swap", "reduction_swap"),
    40: ("one_group", "two_groups"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def row_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_bytes(json_bytes(value))


def variants(case_id: int):
    return VARIANTS.get(case_id, (None,))


@dataclass
class Fixture:
    root: Path
    resources_root: Path
    producer_source_root: Path
    omit_expected_argument: bool = False

    @property
    def bundle(self) -> Path:
        return self.root / "input_bundle.json"

    @property
    def expected(self) -> Path:
        return self.root / "expected_context.json"

    @property
    def examples(self) -> Path:
        return self.root / "examples.jsonl"

    @property
    def labels(self) -> Path:
        return self.root / "q1_labels.jsonl"

    @property
    def manifest(self) -> Path:
        return self.root / "dataset_manifest.json"


def base_records(n=400):
    width = max(3, len(str(n)))
    examples = [{
        "example_id": f"e{i + 1:0{width}d}",
        "prompt": "Synthetic conformance prompt; no model was called.",
        "response": "Synthetic conformance response.",
        "context": "Synthetic nonempty context.",
        "metadata": {"region": "a" if i < n // 2 else "b"},
    } for i in range(n)]
    labels = [{
        "example_id": e["example_id"],
        "q1_grounded_label": "SUPPORTED",
        "q1_eligible": True,
        "q1_exclusion_reason": None,
    } for e in examples]
    return examples, labels, ["region"]


def partition(examples, dimension, groups):
    """Assign ordered (value-or-None, count) groups in one population."""
    cursor = 0
    for value, count in groups:
        for e in examples[cursor:cursor + count]:
            if value is None:
                e["metadata"].pop(dimension, None)
            else:
                e["metadata"][dimension] = value
        cursor += count
    if cursor != len(examples):
        raise ValueError("A fixture partition must cover the whole population")


def records_for_case(case_id: int, variant=None):
    """Encode the accepted 42 recipes; no metric is computed here."""
    n = {2: 199, 3: 200, 7: 200, 16: 220, 19: 420, 25: 600, 39: 2000}.get(case_id, 400)
    examples, labels, dimensions = base_records(n)
    if case_id in (2, 3, 7, 16, 17, 18, 19, 33):
        partition(examples, "region", [("a", n)])
    if case_id == 4:
        partition(examples, "region", [("rare", 29), ("common", 371)])
    elif case_id == 5:
        partition(examples, "region", [("small", 30), ("large", 370)])
    elif case_id == 6:
        partition(examples, "region", [(f"g{i:02d}", 20) for i in range(20)])
    elif case_id == 7:
        for label in labels:
            label["q1_grounded_label"] = "UNKNOWN"
    elif case_id in (8, 9):
        missing = 20 if case_id == 8 else 21
        partition(examples, "region", [(None, missing), ("a", n - missing)])
    elif case_id in (10, 11):
        rare_b = 20 if case_id == 10 else 21
        partition(examples, "region", [("rare_a", 20), ("rare_b", rare_b), ("common", n - 20 - rare_b)])
    elif case_id in (12, 13, 14, 15):
        dimensions = ["A", "B"]
        for e in examples:
            e["metadata"] = {}
        if case_id == 14:
            partition(examples, "A", [("a", 200), ("b", 200)])
            partition(examples, "B", [("c", 200), ("d", 200)])
        else:
            partition(examples, "A", [("rare", 24), ("common", 376)])
            if case_id == 12:
                partition(examples, "B", [("common", 24), ("rare", 24), ("common", 352)])
            elif case_id == 13:
                partition(examples, "B", [("rare", 24), ("common", 376)])
            else:
                partition(examples, "B", [("small_but_comparable", 80), ("large", 320)])
    elif case_id == 16:
        for label in labels[200:]:
            label["q1_grounded_label"] = "UNKNOWN"
    elif case_id in (17, 33):
        for label in labels[200:]:
            label["q1_grounded_label"] = "UNSUPPORTED"
    elif case_id == 18:
        for label in labels[200:]:
            label["q1_grounded_label"] = "ABSTAIN"
    elif case_id == 19:
        for e, label in zip(examples[400:], labels[400:]):
            e["context"] = ""
            label["q1_eligible"] = False
            label["q1_exclusion_reason"] = "empty_context"
    elif case_id == 20:
        examples[0]["context"] = ""
    elif case_id == 21:
        labels[0]["q1_eligible"] = False
        labels[0]["q1_exclusion_reason"] = "empty_context"
    elif case_id == 22:
        examples[0]["context"] = None
    elif case_id == 23:
        del examples[0]["context"]
    elif case_id == 24:
        partition(examples, "region", [(None, 20), ("__MISSING__", 80), ("other", 300)])
    elif case_id == 25:
        partition(examples, "region", [(value, 100) for value in ("en", "EN", "en ", " ", "é", "e\u0301")])
    elif case_id == 26:
        invalid = {"null": None, "number": 1, "boolean": False, "array": [], "object": {}, "empty": ""}
        examples[0]["metadata"]["region"] = invalid[variant]
    elif case_id == 27:
        e, lab, _ = base_records(1)
        e[0]["example_id"] = lab[0]["example_id"] = "e401"
        e[0]["metadata"] = {"region": "a"}
        e[0]["context"] = ""
        lab[0].update(q1_grounded_label="NOT_A_Q1_LABEL", q1_eligible=False,
                      q1_exclusion_reason="empty_context")
        examples += e
        labels += lab
    elif case_id == 28:
        # Keep labels unique so duplicate-example validation precedes joining.
        examples[1]["example_id"] = examples[0]["example_id"]
    elif case_id == 39:
        dimensions = ["A", "B"]
        for e in examples:
            e["metadata"] = {}
        partition(examples, "A", [(None, 80), ("common", 1920)])
        partition(examples, "B", [("common", 80), (None, 80), ("common", 1840)])
    elif case_id == 40:
        for label in labels:
            label["q1_grounded_label"] = "UNSUPPORTED"
        if variant == "one_group":
            partition(examples, "region", [("all", 400)])
    return examples, labels, dimensions


def artifact(path: Path):
    data = path.read_bytes()
    return {"path": path.name, "size_bytes": len(data), "sha256": sha256(data)}


def resource_bindings(resources_root: Path):
    return {key: sha256((resources_root / name).read_bytes())
            for key, name in RESOURCE_PATHS.items()}


def producer_identity(producer_source_root: Path):
    return {
        "tool_id": "PULSE_q3_reference", "tool_version": "0.1.0",
        "python_version": platform.python_version(),
        "source_files": [{"path": PRODUCER_PATH,
                          "sha256": sha256((producer_source_root / PRODUCER_PATH).read_bytes())}],
    }


def write_fixture(root: Path, examples, labels, dimensions, *,
                  resources_root=REPO_ROOT, producer_source_root=REPO_ROOT,
                  dataset_id="q3-synthetic-conformance-v0", manifest_transform=None,
                  label_transform=None, bundle_transform=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    fixture = Fixture(root, Path(resources_root), Path(producer_source_root))
    lines = [row_bytes(e) for e in examples]
    examples_bytes = b"\n".join(lines) + b"\n"
    fixture.examples.write_bytes(examples_bytes)
    bound_labels = copy.deepcopy(labels)
    for line, label in zip(lines, bound_labels):
        label["examples_sha256"] = sha256(examples_bytes)
        label["example_line_sha256"] = sha256(line)
    if label_transform:
        label_transform(bound_labels)
    fixture.labels.write_bytes(b"\n".join(row_bytes(row) for row in bound_labels) + b"\n")
    manifest = {
        "manifest_version": "1.0.0", "dataset_id": dataset_id,
        "time_range": {"from": "2026-10-22", "to": "2026-10-22"},
        "source": {"kind": "other", "uri": "urn:pulse:synthetic:q3-conformance:v0",
                   "description": "Synthetic fixture; dates are fixture metadata, not acquisition evidence."},
        "sampling": {"strategy": "full", "n": len(examples)},
        "pii_handling": {"scrubbed": False, "notes": "Entirely generated synthetic strings; no human data."},
        "labels": {"ground_truth_source": "synthetic-conformance-design",
                   "version": "0.1.0", "notes": "Programmed fixture labels, not verified model judgements."},
        "hashes": {"input_sha256": sha256(examples_bytes),
                   "labels_sha256": sha256(fixture.labels.read_bytes())},
        "slices": {"dimensions": dimensions},
    }
    if manifest_transform:
        manifest_transform(manifest)
    write_json(fixture.manifest, manifest)
    specs = {}
    for key, path in SPEC_PATHS.items():
        data = (fixture.resources_root / path).read_bytes()
        specs[key] = {
            "spec_id": "q1_groundedness_v0" if key == "q1" else "q3_fairness_v0",
            "spec_version": "0.1.0" if key == "q1" else "0.1.1",
            "repository_path": path,
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest(),
            "sha256": sha256(data),
        }
    bindings = resource_bindings(fixture.resources_root)
    subject = {"kind": "synthetic_fixture", "subject_id": "q3-synthetic-subject-v0",
               "source_reference": "urn:pulse:synthetic:q3-conformance:v0", "runtime_identity": None}
    bundle = {
        "record_type": "q3_input_bundle", "contract_profile": PROFILE,
        "dataset_id": dataset_id, "reduction_id": "q3-synthetic-reduction-v0",
        "observation_subject": subject,
        "artifacts": {"dataset_manifest": artifact(fixture.manifest),
                      "examples_jsonl": artifact(fixture.examples),
                      "q1_labels_jsonl": artifact(fixture.labels)},
        "spec_bindings": specs, "contract_bindings": bindings,
        "production_gate_eligible": False, "authority_effect": "none",
    }
    if bundle_transform:
        bundle_transform(bundle)
    write_json(fixture.bundle, bundle)
    expected = {
        "record_type": "q3_expected_context", "contract_profile": PROFILE,
        "input_bundle_sha256": sha256(fixture.bundle.read_bytes()),
        **bindings, "dataset_id": bundle["dataset_id"], "reduction_id": bundle["reduction_id"],
        "observation_subject": bundle["observation_subject"],
        "expected_producer": producer_identity(fixture.producer_source_root),
        "expectation_origin": "synthetic_test_anchor", "authority_effect": "none",
    }
    write_json(fixture.expected, expected)
    return fixture


def rebind_bundle(fixture: Fixture, *, refresh_expectation=True):
    """Rebind actual data bytes for semantic tests; never used for fixed-pin attacks."""
    bundle = read_json(fixture.bundle)
    for key, path in (("dataset_manifest", fixture.manifest),
                      ("examples_jsonl", fixture.examples), ("q1_labels_jsonl", fixture.labels)):
        if key in bundle["artifacts"]:
            bundle["artifacts"][key] = artifact(path)
    write_json(fixture.bundle, bundle)
    if refresh_expectation:
        expected = read_json(fixture.expected)
        expected["input_bundle_sha256"] = sha256(fixture.bundle.read_bytes())
        write_json(fixture.expected, expected)


def replace_examples_bytes(fixture: Fixture, data: bytes):
    """Preserve a deliberate malformed raw record while refreshing outer hashes."""
    fixture.examples.write_bytes(data)
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    labels = [json.loads(line) for line in fixture.labels.read_bytes().splitlines()]
    for i, label in enumerate(labels):
        label["examples_sha256"] = sha256(data)
        if i < len(lines):
            label["example_line_sha256"] = sha256(lines[i])
    fixture.labels.write_bytes(b"\n".join(row_bytes(row) for row in labels) + b"\n")
    manifest = read_json(fixture.manifest)
    manifest["hashes"].update(input_sha256=sha256(data),
                              labels_sha256=sha256(fixture.labels.read_bytes()))
    write_json(fixture.manifest, manifest)
    rebind_bundle(fixture)


def copy_resources(destination: Path, source=REPO_ROOT):
    destination.mkdir(parents=True, exist_ok=True)
    for relative in list(RESOURCE_PATHS.values()) + list(SPEC_PATHS.values()):
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(source) / relative, path)
    return destination


def copy_producer_source(destination: Path, source=REPO_ROOT):
    target = destination / PRODUCER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(source) / PRODUCER_PATH, target)
    return destination


def materialize(case_id: int, root: Path, *, variant=None, resources_root=REPO_ROOT,
                producer_source_root=REPO_ROOT):
    if not 1 <= case_id <= 42 or variant not in variants(case_id):
        raise ValueError("Unknown conformance case/variant")
    examples, labels, dimensions = records_for_case(case_id, variant)
    def manifest_mutation(manifest):
        if case_id == 30:
            if variant == "missing_dimensions":
                del manifest["slices"]["dimensions"]
            elif variant == "empty_dimensions":
                manifest["slices"]["dimensions"] = []
            else:
                manifest["slices"]["dimensions"] = ["region", "region"]
    def label_mutation(bound_labels):
        if case_id == 35:
            bound_labels[0]["example_line_sha256"] = sha256(b"outside-this-dataset")
    def bundle_mutation(bundle):
        if case_id == 29:
            del bundle["artifacts"]["dataset_manifest"]
    fixture = write_fixture(root, examples, labels, dimensions,
                            resources_root=resources_root,
                            producer_source_root=producer_source_root,
                            manifest_transform=manifest_mutation,
                            label_transform=label_mutation,
                            bundle_transform=bundle_mutation)
    if case_id == 31:
        if variant == "changed_examples_bytes":
            fixture.examples.write_bytes(fixture.examples.read_bytes().replace(b"Synthetic", b"Subverted", 1))
        elif variant == "changed_q1_labels_bytes":
            fixture.labels.write_bytes(fixture.labels.read_bytes().replace(b'"SUPPORTED"', b'"UNSUPPORTED"', 1))
        else:
            fixture.resources_root = copy_resources(fixture.root / "modified_resources", fixture.resources_root)
            path = fixture.resources_root / SPEC_PATHS["q3_baseline"]
            path.write_bytes(path.read_bytes() + b"\n# synthetic mutation after pinning\n")
    elif case_id == 32:
        fixture.labels.unlink()
    elif case_id == 36:
        fixed_expected = fixture.expected.read_bytes()
        examples[0]["prompt"] = "Different synthetic source; same aggregate counts."
        fixture = write_fixture(root, examples, labels, dimensions,
                                resources_root=resources_root,
                                producer_source_root=producer_source_root,
                                dataset_id="q3-synthetic-substituted-dataset")
        fixture.expected.write_bytes(fixed_expected)
    elif case_id == 37:
        fixture.omit_expected_argument = True
    elif case_id == 38:
        bundle = read_json(fixture.bundle)
        if variant == "subject_swap":
            bundle["observation_subject"]["subject_id"] = "q3-synthetic-other-subject"
        else:
            bundle["reduction_id"] = "q3-synthetic-other-reduction"
        write_json(fixture.bundle, bundle)
    elif case_id == 42:
        fixture.producer_source_root = copy_producer_source(fixture.root / "modified_producer", fixture.producer_source_root)
        path = fixture.producer_source_root / PRODUCER_PATH
        path.write_bytes(path.read_bytes() + b"\n# synthetic mutation after source pinning\n")
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=int, default=1)
    parser.add_argument("--variant")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resources-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--producer-source-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    fixture = materialize(args.case, args.out, variant=args.variant,
                          resources_root=args.resources_root,
                          producer_source_root=args.producer_source_root)
    print(json.dumps({"synthetic_only": True, "authority_effect": "none",
                      "bundle": str(fixture.bundle), "expected": str(fixture.expected)}))


if __name__ == "__main__":
    main()
