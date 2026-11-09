"""Externality streams are societal only; avoided emissions is its own benefit."""
import pytest

from forge.scripts.io.taxonomy import TAXONOMY
from forge.scripts.utils.streams import pv

from test.spec05_project import item, project_changes, run

MIX = "18_energy_source_mix.grid_mix."
EXT = ("wildfire_eac", "outage_eac", "emissions_comp", "avoided_emissions_benefit")
_FUELS = ("coal", "oil", "natural_gas", "solar", "wind", "hydro", "nuclear", "other")


def _mix_changes():
    c = {MIX + "initial.coal": 0.5, MIX + "initial.natural_gas": 0.5,
         MIX + "rate_pre_cod.coal": 0.0, MIX + "rate_post_cod.coal": -0.03}
    return project_changes(**c)


def test_avoided_emissions_survive():
    r = run(_mix_changes())
    assert item(r, "avoided_emissions_benefit")["value_pv"] != 0.0


def test_avoided_emissions_zero_when_rates_equal():
    # Spec over brief: SunZia_Delay2 pre- and post-COD rates differ, so bare
    # project_changes() is not the zero case. Copy each post-COD rate onto the
    # matching pre-COD rate. Intensities in 16_emissions_reductions.yaml are
    # already non-zero, so this case adds no intensity overrides.
    changes = project_changes()
    for fuel in _FUELS:
        post_key = MIX + "rate_post_cod." + fuel
        pre_key = MIX + "rate_pre_cod." + fuel
        changes[pre_key] = changes[post_key] if post_key in changes else 0.0
    assert item(run(changes), "avoided_emissions_benefit")["value_pv"] == 0.0


def test_externalities_societal_only():
    r = run(_mix_changes())
    for tid in EXT:
        i = item(r, tid)
        assert i["value_pv_wacc"] is None
        assert i["value_pv"] == pytest.approx(pv(i["stream"], 0.02), rel=1e-9)


def test_taxonomy_has_31_items_and_no_removed_ids():
    ids = {t.id for t in TAXONOMY.values()}
    assert len(ids) == 31
    assert not ids & {"emissions_fac", "emissions_displacement_delay", "congestion_delay"}


def test_wildfire_grows_from_base_year():                              # A2
    T = "01_project_technical_details.timeline."
    WG = "06_wildfire_costs.wildfire.risk_growth_rate"
    a = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3, WG: 0.02}))
    b = run(project_changes(**{T+"delay_years": 2, T+"construction_years": 3, WG: 0.0}))
    assert item(a, "wildfire_eac")["stream"][5] == pytest.approx(item(b, "wildfire_eac")["stream"][5] * 1.02**5)
