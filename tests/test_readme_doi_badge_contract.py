from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_top_doi_badge_uses_concept_doi() -> None:
    text = README.read_text(encoding="utf-8")
    assert (
        "[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17214908.svg)]"
        "(https://doi.org/10.5281/zenodo.17214908)" in text
    )


def test_readme_top_doi_badge_not_latestdoi() -> None:
    text = README.read_text(encoding="utf-8")
    assert "https://zenodo.org/badge/latestdoi/1061766508" not in text


def test_readme_zenodo_records_identifies_current_release_v111() -> None:
    text = README.read_text(encoding="utf-8")
    assert "- **Current release DOI / v1.1.1:** https://doi.org/10.5281/zenodo.18203404" in text


def test_readme_does_not_mark_v102_as_current_release() -> None:
    text = README.read_text(encoding="utf-8")
    assert "- **Current release DOI / v1.0.2:** https://doi.org/10.5281/zenodo.17373002" not in text
