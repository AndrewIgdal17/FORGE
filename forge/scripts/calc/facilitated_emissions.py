"""Facilitated emissions and displacement module.

Single-trajectory model (see design doc
2026-07-07__single-trajectory-grid-mix-redesign.md): one regional grid,
evolving at rate_pre_cod (without the line) or rate_post_cod (with the line's
influence). The grid state at COD is the without-line trajectory evaluated at
T_COD; both the with-line and without-line operational trajectories start from
that same COD state.

Computes:
  - Layer 1: C_fac,emissions^(s) for s in {withline, noline} — absolute social
    cost of emissions from each grid trajectory over E_delivered_annual.
  - Layer 2: C_displ,emissions^P = C_fac,emissions^no - C_fac,emissions^with —
    displacement avoided cost; enters B_avoided_emissions (benefit category).

Reuses the evolution engine and emissions-by-year functions from emissions.py.
Methodology note: enabling_resources_displacement_emissions_method.md §§ II.4–II.5b.
Appendix: sec:app-emissions-fac, sec:app-displacement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List

from forge.scripts.utils.smart_output import SmartOutputManager
from forge.scripts.calc.emissions import (
    calculate_energy_mix_by_year,
    calculate_emissions_by_year,
    compute_cod_state,
    build_mix_input,
    monetize_annual_emissions,
)
from forge.scripts.utils.smart_loaders import (
    load_emissions_details,
    load_grid_mix,
    load_financing_social_discount_rate,
)
from forge.scripts.calc.energy_losses import load_project_technical_details
from forge.scripts.utils.financial_utils import calculate_cod_year

@dataclass
class FacilitatedEmissionsResults:
    """Results from facilitated emissions / displacement calculation."""
    fac_emissions_project_pv: float = 0.0
    fac_emissions_project_nominal: float = 0.0
    fac_emissions_noline_pv: float = 0.0
    fac_emissions_noline_nominal: float = 0.0
    displacement_avoided_benefit_pv: float = 0.0
    displacement_avoided_benefit_nominal: float = 0.0
    project_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)
    noline_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)
    displacement_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)
    # Year-by-year nominal costs (length = project_lifetime), for the BCR
    # trajectory module.
    fac_emissions_withline_annual_values: List[float] = field(default_factory=list)
    fac_emissions_noline_annual_values: List[float] = field(default_factory=list)
    displacement_annual_values: List[float] = field(default_factory=list)

def _compute_instance_costs(
    energy_delivered_annual_mwh: float,
    mix_by_year: List[Dict[str, float]],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    social_discount_rate: float,
    start_year: float,
) -> tuple:
    """Compute nominal + PV emissions cost for one instance over all years.

    Returns (total_nominal, total_pv, pv_by_pollutant, annual_values).
    annual_values is the nominal (undiscounted) cost for each year, in order,
    length = len(mix_by_year) = project_lifetime.
    """
    pollutants = ["co2", "sox", "nox"]
    total_nominal = 0.0
    total_pv = 0.0
    pv_by_pollutant = {p: 0.0 for p in pollutants}
    annual_values = []

    for year_idx, energy_mix in enumerate(mix_by_year):
        emissions = calculate_emissions_by_year(
            energy_delivered_annual_mwh, energy_mix, emission_intensities
        )
        year_cost = monetize_annual_emissions(emissions, societal_costs, year_idx)
        total_nominal += year_cost
        annual_values.append(year_cost)

        year_number = year_idx + 1
        discount_year = start_year + year_number - 1
        year_pv = year_cost / ((1 + social_discount_rate) ** discount_year)
        total_pv += year_pv

        for pollutant, emissions_kg in emissions.items():
            pollutant_cost = monetize_annual_emissions(
                {pollutant: emissions_kg}, societal_costs, year_idx
            )
            pollutant_pv = pollutant_cost / (
                (1 + social_discount_rate) ** discount_year
            )
            pv_by_pollutant[pollutant] += pollutant_pv

    return total_nominal, total_pv, pv_by_pollutant, annual_values

def calculate_facilitated_emissions(
    energy_delivered_annual_mwh: float,
    grid_mix: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float,
    construction_years: int,
) -> FacilitatedEmissionsResults:
    """Compute facilitated emissions (Layer 1) and displacement (Layer 2).

    Single-trajectory model: the grid state at COD (initial mix evolved at
    rate_pre_cod through T_COD) is the shared starting point for both
    operational trajectories. Without-line continues at rate_pre_cod from COD;
    with-line evolves at rate_post_cod from COD.

    Layer 1: absolute social cost of emissions for each trajectory (withline,
    noline) over E_delivered_annual, using the rate-based evolution engine.

    Layer 2: displacement = noline_cost - withline_cost.
    """
    start_year = calculate_cod_year(delay_years, construction_years)

    cod_state_pct = compute_cod_state(grid_mix, delay_years, construction_years)
    withline_ops_input = build_mix_input(cod_state_pct, grid_mix["rate_post_cod"])
    noline_ops_input = build_mix_input(cod_state_pct, grid_mix["rate_pre_cod"])

    proj_mix = calculate_energy_mix_by_year(withline_ops_input, project_lifetime)
    noline_mix = calculate_energy_mix_by_year(noline_ops_input, project_lifetime)

    proj_nom, proj_pv, proj_by_poll, proj_annual_values = _compute_instance_costs(
        energy_delivered_annual_mwh, proj_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )
    noline_nom, noline_pv, noline_by_poll, noline_annual_values = _compute_instance_costs(
        energy_delivered_annual_mwh, noline_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )

    disp_pv = noline_pv - proj_pv
    disp_nom = noline_nom - proj_nom
    disp_by_poll = {
        p: noline_by_poll[p] - proj_by_poll[p] for p in proj_by_poll
    }
    displacement_annual_values = [
        noline_annual_values[i] - proj_annual_values[i]
        for i in range(len(noline_annual_values))
    ]

    return FacilitatedEmissionsResults(
        fac_emissions_project_pv=proj_pv,
        fac_emissions_project_nominal=proj_nom,
        fac_emissions_noline_pv=noline_pv,
        fac_emissions_noline_nominal=noline_nom,
        displacement_avoided_benefit_pv=disp_pv,
        displacement_avoided_benefit_nominal=disp_nom,
        project_pv_by_pollutant=proj_by_poll,
        noline_pv_by_pollutant=noline_by_poll,
        displacement_pv_by_pollutant=disp_by_poll,
        fac_emissions_withline_annual_values=proj_annual_values,
        fac_emissions_noline_annual_values=noline_annual_values,
        displacement_annual_values=displacement_annual_values,
    )

def print_facilitated_emissions_results(
    results: FacilitatedEmissionsResults,
    energy_delivered_annual_mwh: float,
) -> None:
    """Print facilitated emissions and displacement results."""
    print("=" * 60)
    print("FACILITATED EMISSIONS (LAYER 1)")
    print("=" * 60)
    print(f"Scope: E_delivered_annual = {energy_delivered_annual_mwh:,.2f} MWh/yr")
    print()
    print("Project path:")
    print(f"  Nominal: ${results.fac_emissions_project_nominal:,.2f}")
    print(f"  PV:      ${results.fac_emissions_project_pv:,.2f}")
    for p, v in results.project_pv_by_pollutant.items():
        print(f"    {p.upper()} PV: ${v:,.2f}")
    print()
    print("No-line (counterfactual):")
    print(f"  Nominal: ${results.fac_emissions_noline_nominal:,.2f}")
    print(f"  PV:      ${results.fac_emissions_noline_pv:,.2f}")
    for p, v in results.noline_pv_by_pollutant.items():
        print(f"    {p.upper()} PV: ${v:,.2f}")
    print()
    print("=" * 60)
    print("DISPLACEMENT AVOIDED COST (LAYER 2)")
    print("=" * 60)
    print(f"  Nominal: ${results.displacement_avoided_benefit_nominal:,.2f}")
    print(f"  PV:      ${results.displacement_avoided_benefit_pv:,.2f}")
    sign = "cleaner project" if results.displacement_avoided_benefit_pv > 0 else "dirtier project"
    print(f"  Sign:    {sign}")
    for p, v in results.displacement_pv_by_pollutant.items():
        print(f"    {p.upper()} avoided PV: ${v:,.2f}")
    print()

def main() -> None:
    """Entry point for the facilitated emissions pipeline step."""
    (
        _compensation_percent,
        emission_intensities,
        societal_costs,
    ) = load_emissions_details()

    grid_mix = load_grid_mix()

    social_discount_rate = load_financing_social_discount_rate()
    project_details = load_project_technical_details()

    output_manager = SmartOutputManager()
    actual_manager = getattr(output_manager, '_manager', output_manager)
    energy_delivered_annual_mwh = 0.0

    if hasattr(actual_manager, 'require_upstream'):
        try:
            energy_delivered_annual_mwh = actual_manager.require_upstream(
                "benefits", "congestion", "energy_delivered_annual_mwh_yr"
            )
        except KeyError as exc:
            print(f"⚠️  {exc}", flush=True)
    elif hasattr(actual_manager, 'benefits'):
        cc_results = actual_manager.benefits.get("congestion", {})
        energy_delivered_annual_mwh = cc_results.get("energy_delivered_annual_mwh_yr", 0.0)

    # Subprocess fallback: load energy_delivered from congestion JSON on disk
    if energy_delivered_annual_mwh <= 0 and not getattr(output_manager, '_using_shared', False):
        import glob
        import json as _json_loader
        scenario_id = os.environ.get("FORGE_SCENARIO_ID", "")
        pattern = os.path.join("outputs", f"json_output_{scenario_id}_congestion_reduction.json")
        candidates = glob.glob(pattern) or glob.glob(os.path.join("..", pattern))
        for fpath in candidates:
            try:
                with open(fpath) as _f:
                    disk_data = _json_loader.load(_f)
                disk_benefits = disk_data.get("benefits", {}).get("congestion", {})
                val = disk_benefits.get("energy_delivered_annual_mwh_yr", 0.0)
                if val > 0:
                    energy_delivered_annual_mwh = val
                    break
            except (OSError, ValueError):
                pass

    if energy_delivered_annual_mwh <= 0:
        print("⚠️  E_delivered_annual is 0 or missing — skipping facilitated emissions.")
        return

    results = calculate_facilitated_emissions(
        energy_delivered_annual_mwh=energy_delivered_annual_mwh,
        grid_mix=grid_mix,
        emission_intensities=emission_intensities,
        societal_costs=societal_costs,
        project_lifetime=project_details.project_lifetime,
        social_discount_rate=social_discount_rate,
        delay_years=project_details.delay_years,
        construction_years=project_details.construction_years,
    )

    print_facilitated_emissions_results(results, energy_delivered_annual_mwh)

    output_results = {
        "fac_emissions_project_pv": results.fac_emissions_project_pv,
        "fac_emissions_project_nominal": results.fac_emissions_project_nominal,
        "fac_emissions_noline_pv": results.fac_emissions_noline_pv,
        "fac_emissions_noline_nominal": results.fac_emissions_noline_nominal,
        "displacement_avoided_benefit_pv": results.displacement_avoided_benefit_pv,
        "displacement_avoided_benefit_nominal": results.displacement_avoided_benefit_nominal,
        "project_co2_pv": results.project_pv_by_pollutant.get("co2", 0.0),
        "project_sox_pv": results.project_pv_by_pollutant.get("sox", 0.0),
        "project_nox_pv": results.project_pv_by_pollutant.get("nox", 0.0),
        "noline_co2_pv": results.noline_pv_by_pollutant.get("co2", 0.0),
        "noline_sox_pv": results.noline_pv_by_pollutant.get("sox", 0.0),
        "noline_nox_pv": results.noline_pv_by_pollutant.get("nox", 0.0),
        "energy_delivered_annual_mwh": energy_delivered_annual_mwh,
        # Year-by-year nominal costs (length = project_lifetime), for the BCR
        # trajectory module.
        "fac_emissions_withline_annual_values": results.fac_emissions_withline_annual_values,
        "fac_emissions_noline_annual_values": results.fac_emissions_noline_annual_values,
        "displacement_annual_values": results.displacement_annual_values,
    }
    output_manager.add_facilitated_emissions_costs(output_results)
    output_manager.write_batch_summary()

if __name__ == "__main__":
    main()
