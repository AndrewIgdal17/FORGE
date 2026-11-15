"""The direct delay cost carries the methodology's name (sec:base-delay, Spec 09)."""
from forge.scripts.io.input_metadata import INPUT_METADATA
from forge.scripts.io.taxonomy import TAXONOMY


def test_taxonomy_label_is_direct_delay_cost():
    assert TAXONOMY["base_delay"].label == "Direct delay cost"


def test_input_label_is_annual_direct_delay_cost():
    assert INPUT_METADATA["delay_annual_base"].label == "Annual direct delay cost"


def test_no_label_says_base_delay():
    labels = [item.label for item in TAXONOMY.values()]
    labels += [field.label for field in INPUT_METADATA.values()]
    assert not [label for label in labels if "base delay" in label.lower()]
