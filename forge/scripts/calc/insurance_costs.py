# Date: 2025-10-28
# Description: This script calculates operational insurance costs for transmission line assets.
#              Insurance premiums are based on insurable asset value (conductors, structures, converters)
#              and paid annually over the project lifetime.

from __future__ import annotations

import logging

# Standard library imports
import yaml
from typing import Dict, Any

from forge.scripts.utils.smart_output import SmartOutputManager

# Local utility imports
from forge.scripts.utils.smart_loaders import (
    load_project_technical_details,
    load_financing_details,
    load_insurance_details,
)
from forge.scripts.utils.calculation_utils import normalize_construction_type_for_yaml
from forge.scripts.utils.streams import growing, pv, undiscounted
from forge.scripts.utils.weighted_miles import calculate_weighted_miles
from forge.scripts.utils.run_context import get_run_context

logger = logging.getLogger(__name__)


def calculate_insurance_costs(
    insurance_yaml: Dict[str, Any],
    conductor_cost_with_contingencies: float,
    structure_cost_with_contingencies: float,
    converter_cost_with_contingencies: float,
    project_lifetime: int,
    construction_type: str,
    wacc_real: float,
    social_discount_rate: float,
    t_cod: int,
    horizon: int,
) -> Dict[str, Any]:
    """
    Calculate operational insurance costs based on insurable asset value.

    Overhead/underground lines use a self-insurance reserve rate; converter
    stations use commercial property insurance rates.

    The premium is a base-year amount on unescalated build cost. It grows
    from year 1 and is paid from COD for the project lifetime. ``insurance_pv``
    discounts that stream at the social rate; ``insurance_pv_wacc`` uses real WACC.

    Args:
        insurance_yaml: Loaded insurance YAML data
        conductor_cost_with_contingencies: Conductor cost with contingencies
        structure_cost_with_contingencies: Structure cost with contingencies
        converter_cost_with_contingencies: Converter cost with contingencies
        project_lifetime: Project lifetime in years
        construction_type: Construction type string (e.g. "Overhead", "Underground")
        wacc_real: Real WACC
        social_discount_rate: Societal discount rate
        t_cod: First operating year
        horizon: Length of the year stream

    Returns:
        dict: Contains insurable_value, annual_premium, premium_rate, line_rate,
              converter_rate, escalation_rate, nominal_lifetime_cost, insurance_pv,
              insurance_pv_wacc, and stream
    """
    ins_cfg = insurance_yaml["insurance"]
    components = ins_cfg["insurable_components"]

    # Look up rate by construction type (fall back to default)
    rate_by_type = ins_cfg["premium_rate_by_type"]
    yaml_ct = normalize_construction_type_for_yaml(construction_type, context="environmental")
    line_rate = rate_by_type.get(yaml_ct, ins_cfg["premium_rate_default"])
    converter_rate = rate_by_type.get("converter", line_rate)

    # Explicit binary selectors (appendix §5 ξ_conductor, ξ_structure, ξ_converter)
    xi_conductor = 1.0 if components["conductors"] else 0.0
    xi_structure = 1.0 if components["structures"] else 0.0
    xi_converter = 1.0 if components["converters"] else 0.0
    line_insurable = (
        xi_conductor * conductor_cost_with_contingencies
        + xi_structure * structure_cost_with_contingencies
    )
    converter_insurable = xi_converter * converter_cost_with_contingencies

    insurable_value = line_insurable + converter_insurable
    annual_premium = (line_insurable * line_rate) + (converter_insurable * converter_rate)
    premium_rate = annual_premium / insurable_value if insurable_value > 0 else 0.0

    escalation_rate = ins_cfg["escalation_rate"]
    stream = growing(
        annual_premium, escalation_rate, t_cod, int(project_lifetime), horizon
    )
    nominal_lifetime_cost = undiscounted(stream)
    insurance_pv = pv(stream, social_discount_rate)
    insurance_pv_wacc = pv(stream, wacc_real)

    return {
        "insurable_value": insurable_value,
        "annual_premium": annual_premium,
        "premium_rate": premium_rate,
        "line_rate": line_rate,
        "converter_rate": converter_rate,
        "escalation_rate": escalation_rate,
        "nominal_lifetime_cost": nominal_lifetime_cost,
        "insurance_pv": insurance_pv,
        "insurance_pv_wacc": insurance_pv_wacc,
        "stream": stream,
    }

def main() -> None:
    """Main function to calculate and display insurance costs."""
    # Load project specifications
    project_details = load_project_technical_details()

    # Construct category identifier
    ctx = get_run_context()
    if ctx is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    category = ctx.category_string

    # Load build costs to get insurable asset values
    if ctx.build_costs is None:
        raise RuntimeError(
            f"{__name__} requires a RunContext. Run via forge.py or set up "
            "RunContext in your test fixture."
        )
    costs = ctx.build_costs

    # Load insurance parameters
    insurance_yaml = load_insurance_details()

    # Load financing parameters for present value calculation
    financing = load_financing_details()

    # Premium on the unescalated build cost, then grown from year 1.
    results = calculate_insurance_costs(
        insurance_yaml,
        costs.conductor_cost_with_contingencies,
        costs.structure_cost_with_contingencies,
        costs.converter_cost_with_contingencies,
        project_details.project_lifetime,
        project_details.construction_type,
        financing.wacc_real,
        ctx.social_discount_rate,
        ctx.t_cod,
        ctx.horizon,
    )

    from forge.scripts.utils.run_context import add_derived
    add_derived({"insurable_value": results["insurable_value"]})

    # Display results
    logger.info("=" * 80)
    logger.info("OPERATIONAL INSURANCE COST CALCULATION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Project Category: {category}")
    logger.info(f"Construction Type: {project_details.construction_type}")
    logger.info("")

    logger.info("INSURABLE ASSET VALUE:")
    ins_components = insurance_yaml["insurance"]["insurable_components"]
    if ins_components["conductors"]:
        logger.info(f"  Conductor Costs: ${costs.conductor_cost_with_contingencies:,.2f}")
    if ins_components["structures"]:
        logger.info(f"  Structure Costs: ${costs.structure_cost_with_contingencies:,.2f}")
    if ins_components["converters"]:
        logger.info(f"  Converter Costs: ${costs.converter_cost_with_contingencies:,.2f}")
    logger.info(f"  ---")
    logger.info(f"  Total Insurable Value: ${results['insurable_value']:,.2f}")
    logger.info("")

    logger.info("[NOMINAL VALUES]")
    logger.info(f"  Line Rate ({results['line_rate']:.3%}) / Converter Rate ({results['converter_rate']:.3%})")
    logger.info(f"  Blended Premium Rate: {results['premium_rate']:.3%}")
    logger.info(f"  Annual Premium (Year 1): ${results['annual_premium']:,.2f}")
    logger.info(f"  Escalation Rate: {results['escalation_rate']:.1%} real/yr")
    logger.info(f"  Project Lifetime: {project_details.project_lifetime} years")
    logger.info(f"  ---")
    logger.info(f"  TOTAL NOMINAL COST: ${results['nominal_lifetime_cost']:,.2f}")
    logger.info("")

    logger.info("[PRESENT VALUE]")
    logger.info(f"  Social Discount Rate: {ctx.social_discount_rate:.2%}")
    logger.info(f"  Real WACC: {financing.wacc_real:.2%}")
    logger.info(f"  Base Year: {financing.base_year}")
    logger.info(f"  ---")
    logger.info(f"  TOTAL PRESENT VALUE (social): ${results['insurance_pv']:,.2f}")
    logger.info(f"  TOTAL PRESENT VALUE (WACC): ${results['insurance_pv_wacc']:,.2f}")
    logger.info("")
    logger.info("NOTE: Operational risk-bearing cost is not AFUDC-eligible (operating expense).")
    logger.info("=" * 80)

    # ========================================================================
    # CSV OUTPUT - Write results to batch summary and detail CSV
    # ========================================================================

    # Initialize CSV output manager
    csv_manager = SmartOutputManager()

    # Prepare operational insurance results dictionary for CSV
    csv_results = {
        "streams": {"insurance": results["stream"]},
        "annual_premium": results["annual_premium"],
        "nominal_lifetime_cost": results["nominal_lifetime_cost"],
        "pv_total": results["insurance_pv"],
        "pv_total_wacc": results["insurance_pv_wacc"],
        "insurable_value": results["insurable_value"],
        "premium_rate": results["premium_rate"],
    }
    csv_manager.add_insurance_costs(csv_results)

    csv_manager.write_batch_summary()
