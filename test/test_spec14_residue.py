from pathlib import Path

import forge
from forge.scripts.io.taxonomy import TAXONOMY_DIMENSIONS

ROOT = Path(forge.__file__).resolve().parent.parent

ROW_REGIME_NOTE = (
    "New permanent easement, federal hybrid, lease or license of an existing corridor"
)


def test_row_regime_text_names_the_three_agreements():
    texts = [d.notes for d in TAXONOMY_DIMENSIONS if d.dimension == "row_regime"]
    assert texts == [ROW_REGIME_NOTE] * 2
    assert not [d for d in TAXONOMY_DIMENSIONS if "fee simple" in d.notes.lower()]


def test_base_delay_dimension_note_is_one_annual_cost():
    notes = [d.notes for d in TAXONOMY_DIMENSIONS if d.taxonomy_id == "base_delay"]
    assert len(notes) == 1
    assert "8 categories" not in notes[0].lower()


def test_width_header_calls_underground_author_estimates():
    head = (ROOT / "forge/yamls/20_project_category_row_widths.yaml").read_text()[:1200]
    assert "author estimates" in head and "unsourced" not in head


def test_habitat_comment_states_the_formula():
    text = (ROOT / "forge/yamls/09_environmental_mitigation.yaml").read_text()
    assert "31,683 x 321.943 / 218.056 = 46,777.53" in text