import inspect
import json
import re

import pytest

import forge
from forge.scripts.io import yaml_loaders
from forge.scripts.io.input_metadata import INPUT_METADATA
from forge.scripts.utils import financial_utils
from forge.scripts.utils.financial_utils import capitalize_yearly_spending
from forge.scripts.utils.run_context import RunContext
from test.spec05_project import item, project_changes, run

AFUDC = "03_financing.financial.afudc.apply_afudc"
MSG = "{} is no longer an input. Only its old value (true) is accepted, and it is ignored."

# The brief names `item` as a helper for this file. These cases do not call it.
_ = item


def test_afudc_true_is_ignored():
    base = run()["benefits"]["capital_recovery"]["rate_base"]
    assert run(project_changes(**{AFUDC: True}))["benefits"]["capital_recovery"]["rate_base"] == base


@pytest.mark.parametrize("value", [False, "true", 1])
def test_afudc_other_values_are_refused(value):
    assert forge.validate_changes({AFUDC: value}) == [{"path": AFUDC, "message": MSG.format(AFUDC)}]
    with pytest.raises(forge.InvalidInputs, match=re.escape(MSG.format(AFUDC))):
        forge.resolve_inputs(project_changes(**{AFUDC: value}))


def test_afudc_true_and_null_validate():
    assert forge.validate_changes({AFUDC: True}) == []
    assert forge.validate_changes({AFUDC: None}) == []


def test_full_document_with_false_is_refused():
    doc = forge.get_defaults_template()
    doc["03_financing"]["financial"]["afudc"] = {"apply_afudc": False}
    with pytest.raises(forge.InvalidInputs, match=re.escape(MSG.format(AFUDC))):
        forge.diff_changes(doc)
    resolved = forge.resolve_inputs(project_changes())
    resolved["03_financing"]["financial"]["afudc"] = {"apply_afudc": False}
    with pytest.raises(forge.InvalidInputs, match="apply_afudc is no longer an input"):
        forge.run_calculation(resolved)


def test_bundled_document_with_true_still_diffs():
    doc = json.loads((forge.get_scenarios_path() / "SunZia_Delay2.forge").read_text())
    assert AFUDC not in forge.diff_changes(doc["inputs"])


def test_afudc_switch_is_gone():
    assert list(inspect.signature(capitalize_yearly_spending).parameters) == ["yearly", "t_cod", "afudc_rate"]
    assert not hasattr(financial_utils, "calculate_afudc_capitalized_cost")
    assert not hasattr(yaml_loaders, "load_afudc_config")
    assert "apply_afudc" not in RunContext.__dataclass_fields__
    assert "apply_afudc" not in INPUT_METADATA
    assert "afudc" not in forge.get_defaults_template()["03_financing"]["financial"]
