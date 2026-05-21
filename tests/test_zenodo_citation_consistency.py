from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_HOW_TO_CITE = ROOT / "README_HOW_TO_CITE.md"
ORCID_ADD_WORK = ROOT / "ORCID_add_work.json"

SOFTWARE_DOI = "10.5281/zenodo.17373002"
PREPRINT_DOI = "10.5281/zenodo.17833583"


def test_readme_how_to_cite_uses_current_preprint_doi() -> None:
    text = README_HOW_TO_CITE.read_text(encoding="utf-8")
    assert f"https://doi.org/{PREPRINT_DOI}" in text
    assert "https://doi.org/10.5281/zenodo.17214909" not in text


def test_orcid_add_work_uses_current_software_doi() -> None:
    text = ORCID_ADD_WORK.read_text(encoding="utf-8")
    assert f"\"doi\": \"{SOFTWARE_DOI}\"" in text
    assert "\"doi\": \"10.5281/zenodo.17214909\"" not in text

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
