from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOCS_INDEX = ROOT / "docs" / "index.html"

VERSIONED_RELEASE_DOI = "10.5281/zenodo.17373002"
VERSIONED_RELEASE_URL = f"https://doi.org/{VERSIONED_RELEASE_DOI}"
VERSIONED_RELEASE_BADGE = f"https://doi.org/badge/DOI/{VERSIONED_RELEASE_DOI}.svg"
VERSIONED_RELEASE_MARKDOWN_BADGE = (
    f"[![DOI]({VERSIONED_RELEASE_BADGE})]({VERSIONED_RELEASE_URL})"
)
CURRENT_RELEASE_RECORD = (
    f"- **Current release DOI / v1.0.2:** {VERSIONED_RELEASE_URL}"
)

CONCEPT_DOI_URL = "https://doi.org/10.5281/zenodo.17214908"
CONCEPT_RECORD = f"- **Concept DOI / all versions:** {CONCEPT_DOI_URL}"
PREVIOUS_RELEASE_RECORD = (
    "- **Previous release DOI / v1.0.1:** "
    "https://doi.org/10.5281/zenodo.17214909"
)
PREPRINT_RECORD = "- **Preprint DOI:** https://doi.org/10.5281/zenodo.17833583"

ACCIDENTAL_CURRENT_RELEASE_RECORD = (
    "- **Current release DOI / v1.1.1:** "
    "https://doi.org/10.5281/zenodo.18203404"
)
ACCIDENTAL_LATEST_DOI_ROUTE = "https://zenodo.org/badge/latestdoi/1061766508"
ACCIDENTAL_REPOSITORY_BADGE = "https://zenodo.org/badge/1061766508.svg"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_top_doi_badge_uses_versioned_release_doi() -> None:
    text = _read(README)

    assert VERSIONED_RELEASE_MARKDOWN_BADGE in text


def test_readme_zenodo_records_match_april_known_good_release_identity() -> None:
    text = _read(README)

    assert CURRENT_RELEASE_RECORD in text
    assert CONCEPT_RECORD in text
    assert PREVIOUS_RELEASE_RECORD in text
    assert PREPRINT_RECORD in text


def test_readme_does_not_use_accidental_current_release_or_latestdoi_route() -> None:
    text = _read(README)

    assert ACCIDENTAL_CURRENT_RELEASE_RECORD not in text
    assert ACCIDENTAL_LATEST_DOI_ROUTE not in text
    assert ACCIDENTAL_REPOSITORY_BADGE not in text


def test_docs_index_doi_badge_uses_versioned_release_doi() -> None:
    text = _read(DOCS_INDEX)

    assert VERSIONED_RELEASE_URL in text
    assert VERSIONED_RELEASE_BADGE in text


def test_docs_index_does_not_use_accidental_latestdoi_route() -> None:
    text = _read(DOCS_INDEX)

    assert ACCIDENTAL_LATEST_DOI_ROUTE not in text
    assert ACCIDENTAL_REPOSITORY_BADGE not in text
