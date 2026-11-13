"""Bundled congestion inputs convert to all-hours spreads; annual relief stays put."""
import json
from pathlib import Path

import pytest

import forge
from test.spec05_project import ACRE_ZEROS
from test.spec07_regions import REGION_SENTINELS

SCN = Path(forge.get_scenarios_path())

# (scenario stem, old H, old p) read from git history before this task; values copied here as a check.
# Verified against git show v2.1.6:forge/scenarios/<stem>.forge. Each greenfield pair matches.
# The bundled inputs no longer store those leaves. Spread is price * hours / 8760.
OLD = {"SunZia_Delay2": (4000, 15.0), "SunZia_Delay17": (4000, 15.0),
       "CTT_Actual_Delay2": (1800, 11.47), "CTT_Counterfactual_Delay7": (1800, 11.47),
       "AEP_LRGV_ACCC": (1200, 15.0), "AEP_LRGV_ACSR_Rebuild": (1200, 15.0),
       "AEP_LRGV_Laredo_NewBuild": (1200, 15.0)}
ENERGY = {"SunZia_Delay2": 30.0, "SunZia_Delay17": 30.0,
          "CTT_Actual_Delay2": 35.0, "CTT_Counterfactual_Delay7": 35.0,
          "AEP_LRGV_ACCC": 42.0, "AEP_LRGV_ACSR_Rebuild": 42.0,
          "AEP_LRGV_Laredo_NewBuild": 42.0}


def _stored_measurements(stem: str) -> dict:
    """Historical all-hours price, written as market measurements."""
    hours, price = OLD[stem]
    spread = price * hours / 8760
    hours_forward, hours_reverse = (0, 0) if spread == 0 else (1, 0)
    prefix = "01_project_technical_details.market_measurements."
    return {
        prefix + "congestion_spread_per_mwh": spread,
        prefix + "hours_receiving_more_congested": hours_forward,
        prefix + "hours_sending_more_congested": hours_reverse,
        prefix + "receiving_energy_value_per_mwh": ENERGY[stem],
    }


@pytest.mark.parametrize("stem", sorted(OLD))
def test_relief_unchanged_by_conversion(stem):
    doc = json.loads((SCN / f"{stem}.forge").read_text())
    changes = forge.diff_changes(doc["inputs"])
    changes.update(ACRE_ZEROS)
    changes.update(_stored_measurements(stem))
    for path, value in REGION_SENTINELS.items():
        changes.setdefault(path, value)
    r = forge.run_calculation(forge.resolve_inputs(changes))
    H, p = OLD[stem]
    old_annual = H * r["benefits"]["congestion"]["relief_mw"] * p
    assert r["benefits"]["congestion"]["congestion_benefit_annual"] == pytest.approx(old_annual, rel=1e-9)


def test_no_bundled_file_has_constrained_hours():
    for f in list(SCN.glob("*.forge")) + list(Path("test/golden").glob("*.json")):
        assert "constrained_hours" not in f.read_text()
