from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
README_HOW_TO_CITE = ROOT / "README_HOW_TO_CITE.md"
ORCID_ADD_WORK = ROOT / "ORCID_add_work.json"
ZENODO_JSON = ROOT / ".zenodo.json"
ZENODO_PREPRINT_JSON = ROOT / "zenodo.preprint.json"
CITATION_CFF = ROOT / "CITATION.cff"

SOFTWARE_TITLE = "PULSE: Artifact-Bound Release Authority for AI Release Decisions"
CANONICAL_CONCEPT_DOI = "10.5281/zenodo.17214908"
VERSIONED_SOFTWARE_DOI = "10.5281/zenodo.17373002"
PREPRINT_DOI = "10.5281/zenodo.17833583"
UNINTENDED_DOI = "10.5281/zenodo.21031131"
REPO_URL = "https://github.com/HKati/pulse-release-gates-0.1"


CANONICAL_METADATA_FILES = (
    ZENODO_JSON,
    ZENODO_PREPRINT_JSON,
    CITATION_CFF,
    README_HOW_TO_CITE,
    ORCID_ADD_WORK,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(_read(path))


def _related_identifier_relations(payload: dict, identifier: str) -> list[str]:
    return [
        item.get("relation", "")
        for item in payload.get("related_identifiers", [])
        if item.get("identifier") == identifier
    ]


def test_json_metadata_files_are_valid() -> None:
    for path in (ZENODO_JSON, ZENODO_PREPRINT_JSON, ORCID_ADD_WORK):
        _load_json(path)


def test_zenodo_json_preserves_canonical_software_concept_identity() -> None:
    payload = _load_json(ZENODO_JSON)
    text = _read(ZENODO_JSON)

    assert payload["title"] == SOFTWARE_TITLE
    assert payload["upload_type"] == "software"
    assert UNINTENDED_DOI not in text

    # The software concept DOI is the immutable all-versions identity parent.
    assert _related_identifier_relations(payload, CANONICAL_CONCEPT_DOI) == ["isVersionOf"]
    assert _related_identifier_relations(payload, PREPRINT_DOI) == ["isDocumentedBy"]

    repo_relations = _related_identifier_relations(payload, REPO_URL)
    assert repo_relations == ["isSupplementTo"]


def test_preprint_metadata_documents_software_but_does_not_version_it() -> None:
    payload = _load_json(ZENODO_PREPRINT_JSON)
    text = _read(ZENODO_PREPRINT_JSON)

    assert payload["upload_type"] == "publication"
    assert payload["publication_type"] == "preprint"
    assert UNINTENDED_DOI not in text

    # A preprint may document the software identity, but it must never claim to
    # be a version of the software concept DOI.
    assert _related_identifier_relations(payload, CANONICAL_CONCEPT_DOI) == ["documents"]
    assert "isVersionOf" not in _related_identifier_relations(payload, CANONICAL_CONCEPT_DOI)
    assert _related_identifier_relations(payload, REPO_URL) == ["documents"]


def test_citation_cff_uses_versioned_software_doi_and_concept_identifier() -> None:
    payload = yaml.safe_load(_read(CITATION_CFF))
    text = _read(CITATION_CFF)

    assert payload["type"] == "software"
    assert payload["title"] == SOFTWARE_TITLE
    assert payload["doi"] == VERSIONED_SOFTWARE_DOI
    assert payload["preferred-citation"]["doi"] == VERSIONED_SOFTWARE_DOI
    assert UNINTENDED_DOI not in text

    identifier_values = [item.get("value") for item in payload.get("identifiers", [])]
    assert identifier_values == [CANONICAL_CONCEPT_DOI, VERSIONED_SOFTWARE_DOI]
    assert not any(
        isinstance(value, str) and "/releases/tag/pulsemech-tier0" in value
        for value in identifier_values
    )


def test_readme_how_to_cite_uses_locked_dois() -> None:
    text = _read(README_HOW_TO_CITE)

    assert f"https://doi.org/{VERSIONED_SOFTWARE_DOI}" in text
    assert f"https://doi.org/{CANONICAL_CONCEPT_DOI}" in text
    assert f"https://doi.org/{PREPRINT_DOI}" in text
    assert "https://doi.org/10.5281/zenodo.17214909" not in text
    assert UNINTENDED_DOI not in text


def test_orcid_add_work_uses_valid_current_software_doi() -> None:
    payload = _load_json(ORCID_ADD_WORK)

    assert payload["title"] == f"{SOFTWARE_TITLE} (Software, v1.0.2)"
    assert payload["type"] == "software"
    assert payload["doi"] == VERSIONED_SOFTWARE_DOI


def test_unintended_doi_is_absent_from_canonical_metadata_files() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in CANONICAL_METADATA_FILES
        if UNINTENDED_DOI in _read(path)
    ]

    assert offenders == []


def test_readme_unintended_doi_is_containment_only() -> None:
    text = _read(README)

    if UNINTENDED_DOI not in text:
        return

    assert "Temporary DOI identity containment notice" in text
    assert f"Do not cite `{UNINTENDED_DOI}`" in text
    assert text.count(UNINTENDED_DOI) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
