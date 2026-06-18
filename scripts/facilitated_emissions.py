"""Facilitated emissions and displacement module.

Computes:
  - Layer 1: C_fac,emissions^(s) for s in {proj, noline} — absolute social cost
    of emissions from each instance's generation mix over E_delivered_annual.
  - Layer 2: C_displ,emissions^P = C_fac,emissions^no - C_fac,emissions^P —
    displacement avoided cost; enters B_avoided_emissions (benefit bucket).

Reuses the evolution engine and emissions-by-year functions from emissions.py.
Methodology note: enabling_resources_displacement_emissions_method.md §§ II.4–II.5b.
Appendix: sec:app-emissions-fac, sec:app-displacement.
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smart_output import CTCCOutputManager
from emissions import calculate_energy_mix_by_year, calculate_emissions_by_year
from smart_loaders import (
    load_emissions_details,
    load_counterfactual_energy_source_mix,
    load_financing_social_discount_rate,
)
from energy_losses import load_project_technical_details
from financial_utils import calculate_cod_year


@dataclass
class FacilitatedEmissionsResults:
    """Results from facilitated emissions / displacement calculation."""
    fac_emissions_project_pv: float = 0.0
    fac_emissions_project_nominal: float = 0.0
    fac_emissions_noline_pv: float = 0.0
    fac_emissions_noline_nominal: float = 0.0
    displacement_avoided_cost_pv: float = 0.0
    displacement_avoided_cost_nominal: float = 0.0
    project_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)
    noline_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)
    displacement_pv_by_pollutant: Dict[str, float] = field(default_factory=dict)


def _compute_instance_costs(
    energy_delivered_annual_mwh: float,
    mix_by_year: List[Dict[str, float]],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    social_discount_rate: float,
    start_year: float,
) -> tuple:
    """Compute nominal + PV emissions cost for one instance over all years.

    Returns (total_nominal, total_pv, pv_by_pollutant).
    """
    pollutants = ["co2", "sox", "nox"]
    total_nominal = 0.0
    total_pv = 0.0
    pv_by_pollutant = {p: 0.0 for p in pollutants}

    for year_idx, energy_mix in enumerate(mix_by_year):
        emissions = calculate_emissions_by_year(
            energy_delivered_annual_mwh, energy_mix, emission_intensities
        )
        year_cost = 0.0
        for pollutant, emissions_kg in emissions.items():
            base_cost = societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            growth = societal_costs.get(f"{pollutant}_cost_annual_growth", 0.0)
            cost_per_kg = base_cost * (1 + growth) ** year_idx
            pollutant_cost = emissions_kg * cost_per_kg
            year_cost += pollutant_cost

        total_nominal += year_cost

        year_number = year_idx + 1
        discount_year = start_year + year_number - 1
        year_pv = year_cost / ((1 + social_discount_rate) ** discount_year)
        total_pv += year_pv

        for pollutant, emissions_kg in emissions.items():
            base_cost = societal_costs.get(f"{pollutant}_cost_per_kg", 0.0)
            growth = societal_costs.get(f"{pollutant}_cost_annual_growth", 0.0)
            cost_per_kg = base_cost * (1 + growth) ** year_idx
            pollutant_cost = emissions_kg * cost_per_kg
            pollutant_pv = pollutant_cost / (
                (1 + social_discount_rate) ** discount_year
            )
            pv_by_pollutant[pollutant] += pollutant_pv

    return total_nominal, total_pv, pv_by_pollutant


def calculate_facilitated_emissions(
    energy_delivered_annual_mwh: float,
    energy_source_mix_details: Dict[str, Any],
    counterfactual_energy_source_mix_details: Dict[str, Any],
    emission_intensities: Dict[str, Any],
    societal_costs: Dict[str, float],
    project_lifetime: int,
    social_discount_rate: float,
    delay_years: float,
    construction_years: int,
) -> FacilitatedEmissionsResults:
    """Compute facilitated emissions (Layer 1) and displacement (Layer 2).

    Layer 1: absolute social cost of emissions for each instance (proj, noline)
    over E_delivered_annual, using the rate-based evolution engine.

    Layer 2: displacement = noline_cost - project_cost.
    """
    start_year = calculate_cod_year(delay_years, construction_years)

    proj_mix = calculate_energy_mix_by_year(
        energy_source_mix_details, project_lifetime
    )
    noline_mix = calculate_energy_mix_by_year(
        counterfactual_energy_source_mix_details, project_lifetime
    )

    proj_nom, proj_pv, proj_by_poll = _compute_instance_costs(
        energy_delivered_annual_mwh, proj_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )
    noline_nom, noline_pv, noline_by_poll = _compute_instance_costs(
        energy_delivered_annual_mwh, noline_mix, emission_intensities,
        societal_costs, social_discount_rate, start_year,
    )

    disp_pv = noline_pv - proj_pv
    disp_nom = noline_nom - proj_nom
    disp_by_poll = {
        p: noline_by_poll[p] - proj_by_poll[p] for p in proj_by_poll
    }

    return FacilitatedEmissionsResults(
        fac_emissions_project_pv=proj_pv,
        fac_emissions_project_nominal=proj_nom,
        fac_emissions_noline_pv=noline_pv,
        fac_emissions_noline_nominal=noline_nom,
        displacement_avoided_cost_pv=disp_pv,
        displacement_avoided_cost_nominal=disp_nom,
        project_pv_by_pollutant=proj_by_poll,
        noline_pv_by_pollutant=noline_by_poll,
        displacement_pv_by_pollutant=disp_by_poll,
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
    print(f"  Nominal: ${results.displacement_avoided_cost_nominal:,.2f}")
    print(f"  PV:      ${results.displacement_avoided_cost_pv:,.2f}")
    sign = "cleaner project" if results.displacement_avoided_cost_pv > 0 else "dirtier project"
    print(f"  Sign:    {sign}")
    for p, v in results.displacement_pv_by_pollutant.items():
        print(f"    {p.upper()} avoided PV: ${v:,.2f}")
    print()


def main() -> None:
    """Entry point for the facilitated emissions pipeline step."""
    (
        _compensation_percent,
        energy_source_mix_details,
        emission_intensities,
        societal_costs,
    ) = load_emissions_details()

    counterfactual_mix = load_counterfactual_energy_source_mix()

    social_discount_rate = load_financing_social_discount_rate()
    project_details = load_project_technical_details()

    output_manager = CTCCOutputManager()
    cc_results = getattr(output_manager, '_manager', output_manager).benefits.get(
        "congestion_curtailment", {}
    )
    energy_delivered_annual_mwh = cc_results.get("energy_delivered_annual_mwh_yr", 0.0)

    # Subprocess fallback: load energy_delivered from congestion_curtailment JSON on disk
    if energy_delivered_annual_mwh <= 0 and not getattr(output_manager, '_using_shared', False):
        import glob
        import json as _json_loader
        scenario_id = os.environ.get("CTCC_SCENARIO_ID", "")
        pattern = os.path.join("outputs", f"json_output_{scenario_id}_congestion_curtailment_reduction.json")
        candidates = glob.glob(pattern) or glob.glob(os.path.join("..", pattern))
        for fpath in candidates:
            try:
                with open(fpath) as _f:
                    disk_data = _json_loader.load(_f)
                disk_benefits = disk_data.get("benefits", {}).get("congestion_curtailment", {})
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
        energy_source_mix_details=energy_source_mix_details,
        counterfactual_energy_source_mix_details=counterfactual_mix,
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
        "displacement_avoided_cost_pv": results.displacement_avoided_cost_pv,
        "displacement_avoided_cost_nominal": results.displacement_avoided_cost_nominal,
        "project_co2_pv": results.project_pv_by_pollutant.get("co2", 0.0),
        "project_sox_pv": results.project_pv_by_pollutant.get("sox", 0.0),
        "project_nox_pv": results.project_pv_by_pollutant.get("nox", 0.0),
        "noline_co2_pv": results.noline_pv_by_pollutant.get("co2", 0.0),
        "noline_sox_pv": results.noline_pv_by_pollutant.get("sox", 0.0),
        "noline_nox_pv": results.noline_pv_by_pollutant.get("nox", 0.0),
        "energy_delivered_annual_mwh": energy_delivered_annual_mwh,
    }
    output_manager.add_facilitated_emissions_costs(output_results)
    output_manager.write_batch_summary()


if __name__ == "__main__":
    main()
