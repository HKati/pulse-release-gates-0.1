from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_top_doi_badge_uses_zenodo_repository_route() -> None:
    text = README.read_text(encoding="utf-8")
    assert (
        "[![DOI](https://zenodo.org/badge/1061766508.svg)]"
        "(https://zenodo.org/badge/latestdoi/1061766508)" in text
    )


def test_readme_zenodo_records_include_concept_doi_all_versions() -> None:
    text = README.read_text(encoding="utf-8")
    assert "- **Concept DOI / all versions:** https://doi.org/10.5281/zenodo.17214908" in text


def test_readme_zenodo_records_identifies_current_release_v111() -> None:
    text = README.read_text(encoding="utf-8")
    assert "- **Current release DOI / v1.1.1:** https://doi.org/10.5281/zenodo.18203404" in text


def test_readme_does_not_mark_v102_as_current_release() -> None:
    text = README.read_text(encoding="utf-8")
    assert "- **Current release DOI / v1.0.2:** https://doi.org/10.5281/zenodo.17373002" not in text
