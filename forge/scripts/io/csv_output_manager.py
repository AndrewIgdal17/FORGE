# Date: 2025-10-29
# Description: Batch-summary field schema used by forge.py to build csv_equivalent dicts.

from __future__ import annotations

BATCH_SUMMARY_FIELDS = [
    # 1. Identification
    "project_name",
    "scenario_id",
    "timestamp",
    # 2. Key Parameters
    "capacity_mw",
    "line_length_miles",
    "construction_type",
    "ac_dc",
    "social_discount_rate",
    # 3. Capital Costs PV (with breakdown)
    "build_cost_pv",
    "row_cost_pv",
    "acquisition_pv",
    "row_rent_pv",
    "acquisition_afudc",
    "acquisition_nominal_total",
    "row_rent_nominal",
    "env_mitigation_pv",
    "capital_costs_pv",
    "build_cost_afudc",
    "row_cost_afudc",
    "env_mitigation_afudc",
    # 4. Operational Costs PV (with breakdown)
    "insurance_pv",
    "oandm_pv",
    "operational_costs_pv",
    # 5. Risk Costs PV (with breakdown)
    "wildfire_pv",
    "outage_pv",
    "risk_costs_pv",
    # 6. Delay Costs PV
    "delay_cost_pv",
    "congestion_delay_cost_pv",
    "emissions_displacement_delay_pv",
    "delay_costs_pv",
    # 7. Energy/Emissions Costs PV (with breakdown)
    "emissions_comp_cost_pv",
    "energy_losses_pv",
    "conductor_loss_pv",
    "converter_loss_pv",
    "energy_losses_nominal",
    "energy_emissions_costs_pv",
    # 8. Total Costs PV
    "total_costs_pv",
    # 8a. Appendix-aligned cost categories
    "hard_costs_pv",
    "soft_costs_pv",
    "emissions_costs_pv",
    # 9. Benefits PV (with breakdown)
    "congestion_benefit_pv",
    "delivered_benefit_annual",
    "delivered_benefit_nominal",
    "delivered_benefit_pv",
    "capital_recovery_pv",
    "rate_base",
    "rate_base_real",
    "annual_revenue_real",
    "displacement_avoided_benefit_pv",
    "total_benefits_pv",
    # 9a. Appendix-aligned benefit categories
    "benefits_remedial_pv",
    "benefits_enabling_pv",
    # 9b. Transparency (intermediate quantities)
    "fac_emissions_project_pv",
    "fac_emissions_noline_pv",
    # 10. BCR Metrics
    "bcr_societal",
    # Tier 1 exclusion BCRs (3 analytically motivated variants)
    "bcr_excluding_avoided_emissions",
    "bcr_excluding_wildfire_risk",
    "bcr_excluding_wildfire_risk_and_outage_risk",
    # Stakeholder perspectives
    "bcr_utility",
    "bcr_ratepayer",
    # 11. Net Benefits PV
    "net_benefit_pv",
    # Tier 1 exclusion net benefits (3 analytically motivated variants)
    "net_benefit_excluding_avoided_emissions_pv",
    "net_benefit_excluding_wildfire_risk_pv",
    "net_benefit_excluding_wildfire_risk_and_outage_risk_pv",
    # Capital and stakeholder net benefits
    "net_benefit_utility_pv",
    "net_benefit_ratepayer_pv",
]
