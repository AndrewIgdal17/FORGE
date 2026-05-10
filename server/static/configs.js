// CTCC Config Objects
// Extracted from index.html — loaded via <script src="/static/configs.js"> before the main inline script.

// =============================================
// Comparison Metric Configs
// =============================================

      const COMPARISON_METRICS = [
        { group: 'Project Parameters', metrics: [
          { key: 'ac_dc', label: 'AC / DC', path: 'technical_parameters.ac_dc', format: 'text' },
          { key: 'baseline_price_mwh', label: 'Baseline price ($/MWh)', path: 'technical_parameters.baseline_electricity_price_per_mwh', format: 'number2' },
          { key: 'capacity_mw', label: 'Capacity (MW)', path: 'technical_parameters.capacity_mw', format: 'number' },
          { key: 'conductor_type', label: 'Conductor type', path: 'technical_parameters.conductor_type', format: 'text' },
          { key: 'construction_years', label: 'Construction (yr)', path: 'technical_parameters.construction_years', format: 'number' },
          { key: 'construction_type', label: 'Construction type', path: 'technical_parameters.construction_type', format: 'text' },
          { key: 'converter_type', label: 'Converter type', path: 'technical_parameters.converter_type', format: 'text' },
          { key: 'delay_years', label: 'Delay (yr)', path: 'technical_parameters.delay_years', format: 'number' },
          { key: 'lifetime', label: 'Lifetime (yr)', path: 'technical_parameters.project_lifetime_years', format: 'number' },
          { key: 'line_length', label: 'Line length (mi)', path: 'technical_parameters.line_length_miles', format: 'number2' },
          { key: 'line_utilization', label: 'Line utilization', path: 'technical_parameters.line_utilization', format: 'number2' },
        ]},
        { group: 'Benefit-Cost Ratio', metrics: [
          { key: 'bcr_capital', label: 'BCR Capital', path: 'bcr.bcr_capital', format: 'number3' },
          { key: 'bcr_ratepayer', label: 'BCR Ratepayer', path: 'bcr.bcr_ratepayer', format: 'number3' },
          { key: 'bcr_system', label: 'BCR System', path: 'bcr.bcr_system', format: 'number3' },
          { key: 'bcr_utility', label: 'BCR Utility', path: 'bcr.bcr_utility', format: 'number3' },
          { key: 'custom_bcr', label: 'Custom BCR', path: '__custom__', format: 'number3' },
        ]},
        { group: 'Costs (PV)', metrics: [
          { key: 'build_pv', label: 'Build Cost', path: 'costs.build.total_pv', format: 'currency' },
          { key: 'env_pv', label: 'Environmental Cost', path: 'costs.environmental.total_pv', format: 'currency' },
          { key: 'insurance_pv', label: 'Insurance Cost', path: 'costs.insurance.pv_total', format: 'currency', zeroIfMissing: true },
          { key: 'row_capital_pv', label: 'ROW Capital Cost', path: 'costs.row.row_capital_pv', format: 'currency' },
          { key: 'row_rent_pv', label: 'ROW Rent Cost', path: 'costs.row.row_rent_pv', format: 'currency' },
          { key: 'total_capital_pv', label: 'Total Capital Cost', path: 'summary.total_capital_pv', format: 'currency' },
          { key: 'total_operational_pv', label: 'Total Operational Cost', path: 'summary.total_operational_pv', format: 'currency' },
          { key: 'grand_total_pv', label: 'Total System Cost', path: 'summary.total_costs_pv', format: 'currency' },
        ]},
        { group: 'Benefits', metrics: [
          { key: 'benefits_remedial_pv', label: 'Remedial Benefits', path: 'bcr.benefits_remedial_haircut_pv', format: 'currency' },
          { key: 'benefits_enabling_pv', label: 'Enabling Benefits', path: 'bcr.benefits_enabling_haircut_pv', format: 'currency' },
          { key: 'congestion_pv', label: 'Congestion Benefits', path: 'bcr.congestion_benefit_haircut_pv', format: 'currency' },
          { key: 'curtailment_pv', label: 'Curtailment Benefits', path: 'bcr.curtailment_benefit_haircut_pv', format: 'currency' },
          { key: 'custom_nb', label: 'Custom Net Benefit', path: '__custom__', format: 'currency' },
          { key: 'net_benefit_ratepayer_pv', label: 'Net Benefit (Ratepayer)', path: 'bcr.net_benefit_ratepayer_pv', format: 'currency' },
          { key: 'net_benefit_pv', label: 'Net Benefit (System)', path: 'bcr.net_benefit_pv', format: 'currency' },
          { key: 'net_benefit_utility_pv', label: 'Net Benefit (Utility)', path: 'bcr.net_benefit_utility_pv', format: 'currency' },
          { key: 'revenue_pv', label: 'Revenue', path: 'bcr.revenue_pv', format: 'currency' },
          { key: 'total_benefits_pv', label: 'Total Benefits', path: 'bcr.total_benefits_haircut_pv', format: 'currency' },
        ]},
        { group: 'Cost Buckets (PV)', metrics: [
          { key: 'hard_costs_pv', label: 'Hard Costs', path: 'bcr.hard_costs_pv', format: 'currency' },
          { key: 'soft_costs_pv', label: 'Soft Costs', path: 'bcr.soft_costs_pv', format: 'currency' },
          { key: 'emissions_costs_pv', label: 'Emissions Costs', path: 'bcr.emissions_costs_pv', format: 'currency' },
        ]},
        { group: 'Risk Costs (PV)', metrics: [
          { key: 'outage_pv', label: 'Outage Cost', path: 'costs.outage.pv_cost', format: 'currency', zeroIfMissing: true },
          { key: 'total_risk_pv', label: 'Total Risk Cost', path: 'summary.total_risk_pv', format: 'currency' },
          { key: 'wildfire_pv', label: 'Wildfire Cost', path: 'costs.wildfire.pv_cost', format: 'currency', zeroIfMissing: true },
        ]},
        { group: 'Delay Costs (PV)', metrics: [
          { key: 'delay_pv', label: 'Base Delay Cost', path: 'costs.delay.total_pv', format: 'currency', zeroIfMissing: true },
        ]},
        { group: 'Energy / Emissions (PV)', metrics: [
          { key: 'emissions_pv', label: 'Loss-Comp Emissions', path: 'costs.emissions.total_pv', format: 'currency', zeroIfMissing: true },
          { key: 'fac_emissions_pv', label: 'Facilitated Emissions', path: 'bcr.fac_emissions_project_pv', format: 'currency', zeroIfMissing: true },
          { key: 'displacement_pv', label: 'Displacement Avoided', path: 'bcr.displacement_avoided_cost_pv', format: 'currency', zeroIfMissing: true },
          { key: 'line_loss_pv', label: 'Line Loss Cost', path: 'costs.line_loss.total_pv', format: 'currency', zeroIfMissing: true },
          { key: 'total_energy_emissions_pv', label: 'Total Energy/Emissions Cost', path: 'summary.total_energy_emissions_pv', format: 'currency' },
        ]},
        { group: 'BCR Sensitivity Exclusions', metrics: [
          { key: 'bcr_excl_em', label: 'BCR excl. Emissions', path: 'bcr.bcr_excluding_emissions', format: 'number3' },
          { key: 'bcr_excl_em_ll', label: 'BCR excl. Emissions + Losses', path: 'bcr.bcr_excluding_emissions_and_linelosses', format: 'number3' },
          { key: 'bcr_excl_em_ll_wf', label: 'BCR excl. Emissions + Losses + Wildfire', path: 'bcr.bcr_excluding_emissions_and_linelosses_and_wildfire_risk', format: 'number3' },
          { key: 'bcr_excl_em_ll_wf_out', label: 'BCR excl. Emissions + Losses + Wildfire + Outage', path: 'bcr.bcr_excluding_emissions_and_linelosses_and_wildfire_risk_and_outage_risk', format: 'number3' },
          { key: 'bcr_excl_ll', label: 'BCR excl. Line Losses', path: 'bcr.bcr_excluding_linelosses', format: 'number3' },
          { key: 'bcr_excl_out', label: 'BCR excl. Outage', path: 'bcr.bcr_excluding_outage_risk', format: 'number3' },
          { key: 'bcr_excl_wf', label: 'BCR excl. Wildfire', path: 'bcr.bcr_excluding_wildfire_risk', format: 'number3' },
          { key: 'bcr_excl_wf_out', label: 'BCR excl. Wildfire + Outage', path: 'bcr.bcr_excluding_wildfire_risk_and_outage_risk', format: 'number3' },
        ]},
      ];

      /** Maps each COMPARISON_METRICS `group` to a super-group for the hierarchical add-column picker. */
      const COMPARISON_GROUP_SUPERGROUP = {
        'Project Parameters': 'project',
        'Benefit-Cost Ratio': 'bcr',
        'Costs (PV)': 'costs',
        'Cost Buckets (PV)': 'costs',
        'Benefits': 'benefits',
        'Risk Costs (PV)': 'costs',
        'Delay Costs (PV)': 'costs',
        'Energy / Emissions (PV)': 'costs',
        'BCR Sensitivity Exclusions': 'sensitivity',
      };

      const COMPARISON_SUPERGROUP_ORDER = ['project', 'bcr', 'costs', 'benefits', 'sensitivity'];
      const COMPARISON_SUPERGROUP_LABEL = {
        project: 'Project Information',
        bcr: 'Benefit-Cost Ratio (BCR)',
        costs: 'Costs',
        benefits: 'Benefits',
        sensitivity: 'BCR Sensitivity Adjustments',
      };

      const CMP_PICKER_STORAGE_KEY = 'ctcc-cmp-picker-details';

      // Comparison catalog: group order is fixed (BCR Sensitivity Exclusions last); within each group,
      // metrics are alphabetical by label. Flatten order drives sortComparisonColumnsByCatalog(); add-column UI is the
      // hierarchical popover (super-groups → catalog group → metric buttons), not a flat <select>.
      const COMPARISON_METRIC_KEY_ORDER = (() => {
        const order = new Map();
        let idx = 0;
        for (const g of COMPARISON_METRICS) {
          for (const m of g.metrics) {
            if (!order.has(m.key)) order.set(m.key, idx++);
          }
        }
        return order;
      })();

      const UNKNOWN_METRIC_CATALOG_INDEX = Number.MAX_SAFE_INTEGER;

// =============================================
// Input Form Configs
// =============================================

      // Tab configuration for input tabs
      const TAB_CONFIG = [
        { id: 'project', label: 'Project', sections: ['01_project_technical_details'] },
        { id: 'route-terrain', label: 'Route & Terrain', sections: ['02_project_physical_details'] },
        { id: 'financial', label: 'Financial', sections: ['03_financing', '19_cost_timing_patterns'] },
        { id: 'capital-costs', label: 'Capital Costs', sections: ['11_project_row_details', '09_environmental_mitigation'] },
        { id: 'operational', label: 'Operational Costs', sections: ['04_insurance', '12_project_om_vegetation_management'] },
        { id: 'delay-costs', label: 'Delay Costs', sections: ['05_delays'] },
        { id: 'risk', label: 'Risk Costs', sections: ['06_wildfire_costs', '07_outage_costs'] },
        { id: 'emissions', label: 'Emissions', sections: ['18_energy_source_mix', '16_emissions_reductions'] },
        { id: 'benefits', label: 'Benefits', sections: ['17_congestion_curtailment_reductions'] },
      ];

      /**
       * TAB_HIERARCHY — single source of truth for within-tab layout.
       *
       * To change a tab's field ordering, section grouping, collapsing, or
       * labeling: add/edit entries here. Do NOT write ad-hoc DOM layout functions.
       *
       * Matching primitives:
       *   matchPath   — JSON dot path (matches data-section-path on Reset buttons
       *                 or data-section-key on .tab-section-header elements).
       *                 Finds the existing section header + its content.
       *   matchFields — array of data-field-path suffixes. Extracts individual
       *                 fields from their current grid and regroups them into a
       *                 new synthetic section.
       *
       * Children (sub-grouping within a section):
       *   children: [{ matchFields, label, collapsed }, { matchPath, label, collapsed }]
       *   matchFields children — extract fields into labeled collapsible sub-sections.
       *   matchPath children   — relabel/collapse existing subsection headers within
       *                          the parent's content.
       *
       * Tiers:
       *   first-glance — prominent, always visible at top
       *   working      — visible, standard form fields
       *   advanced     — collapsed by default (collapsible-header/content pattern)
       *
       * The engine (applyTabHierarchy) claims elements, physically reorders them
       * to match this config's array order, applies decorations (label, tier, note),
       * then processes children for sub-grouping. Unclaimed elements go at the end.
       *
       * Design doc: Projects/CTCC/input_app_audit/within-tab-hierarchy-proposal.md
       */
      const TAB_HIERARCHY = {
        'project': {
          sections: [
            {
              id: 'project-setup',
              label: 'Project Setup',
              tier: 'first-glance',
              matchPath: '01_project_technical_details.project',
              note: 'Core project parameters. Capacity maps to appendix C_new; reconductoring fields define C_old.',
              children: [
                {
                  label: 'Identity & Technology',
                  matchFields: ['name', 'construction_type', 'ac_dc', 'capacity_mw', 'conductor_type',
                                'number_of_converters', 'converter_type', 'converter_loss_percentage']
                },
                {
                  label: 'Reconductoring & ROW Context',
                  matchFields: ['reconductoring', 'uses_existing_row', 'old_capacity_mw', 'old_conductor_type', 'old_ac_dc']
                },
                {
                  label: 'Utilization & Reference Price',
                  matchFields: ['line_utilization', 'baseline_electricity_price_per_mwh']
                }
              ]
            },
            {
              id: 'timeline',
              label: 'Timeline',
              tier: 'first-glance',
              matchPath: '01_project_technical_details.timeline',
              note: 'Construction years, delay years, and project lifetime — used across AFUDC timing and all PV calculations.'
            }
          ],
          resetButton: 'single'
        },
        'route-terrain': {
          sections: [
            {
              id: 'terrain-parent',
              matchPath: '02_project_physical_details.terrain',
              hidden: true
            },
            {
              id: 'terrain-miles',
              label: 'Terrain Miles',
              tier: 'first-glance',
              matchPath: '02_project_physical_details.terrain.terrain_miles',
              note: 'Miles by terrain type. Zero-mile terrains are hidden from cost calculations. Totals and weighted miles are computed.'
            },
            {
              id: 'terrain-multipliers',
              label: 'Terrain Multipliers',
              tier: 'advanced',
              matchPath: '02_project_physical_details.terrain.terrain_multipliers',
              note: 'Cost multiplier by terrain type — applied to build costs via weighted miles.'
            }
          ],
          resetButton: 'single'
        },
        'financial': {
          sections: [
            {
              id: 'financing-parent',
              matchPath: '03_financing',
              hidden: true
            },
            {
              id: 'financial-parent',
              matchPath: '03_financing.financial',
              hidden: true
            },
            {
              id: 'core-rates',
              label: 'Financial Parameters',
              tier: 'first-glance',
              matchFields: ['base_year', 'inflation_rate', 'wacc_nominal', 'social_discount_rate'],
              note: 'Discount rates and inflation for present-value calculations. Real WACC discounts market costs/benefits; social rate discounts externalities.'
            },
            {
              id: 'contingencies',
              label: 'Build Contingencies',
              tier: 'working',
              matchPath: '03_financing.financial.contingencies',
              note: 'Contingency factors applied to terrain-adjusted build cost components.'
            },
            {
              id: 'capital-structure',
              matchPath: '03_financing.financial.capital_structure',
              hidden: true
            },
            {
              id: 'revenue',
              label: 'Revenue & Return',
              tier: 'working',
              matchPath: '03_financing.financial.revenue'
            },
            {
              id: 'afudc-config',
              label: 'AFUDC Configuration',
              tier: 'advanced',
              matchPath: '03_financing.financial.afudc',
              note: 'AFUDC rate equals nominal WACC. Controls whether pre-construction spending earns AFUDC.'
            },
            {
              id: 'afudc-timing',
              label: 'AFUDC Timing Patterns',
              tier: 'advanced',
              matchPath: '19_cost_timing_patterns',
              note: 'Spending split by cost component for AFUDC capitalization to COD.'
            }
          ],
          resetButton: 'single'
        },
        'capital-costs': {
          sections: [
            {
              id: 'cap-row-tab-header',
              matchPath: '11_project_row_details',
              hidden: true
            },
            {
              id: 'capital-row-corridor',
              label: 'Capital ROW (Acquisition & Holding)',
              tier: 'first-glance',
              matchPath: '11_project_row_details.right_of_way',
              note: 'Per-zone corridor inputs: acquisition and holding (option fees) per §2.1.2. Rent belongs under Operational Costs per appendix §2.2.3; rent fields remain here until field migration lands.'
            },
            {
              id: 'cap-env-tab-header',
              matchPath: '09_environmental_mitigation',
              hidden: true
            },
            {
              id: 'environmental-mitigation',
              label: 'Environmental Mitigation',
              tier: 'working',
              matchPath: '09_environmental_mitigation.environmental_mitigation',
              note: 'Base mitigation ($/acre by terrain and construction type) and credit costs/ratios per §2.1.3. Reconductoring forces wetland/habitat credits to zero in the model.'
            }
          ],
          resetButton: 'single'
        },
        'operational': {
          sections: [
            {
              id: 'om-parent',
              matchPath: '12_project_om_vegetation_management',
              hidden: true
            },
            {
              id: 'om-vegetation',
              label: 'O&M — Vegetation Management',
              tier: 'first-glance',
              matchPath: '12_project_om_vegetation_management.vegetation_management_om_costs',
              note: 'Editable slice of §2.2.1 O&M (vegetation $/mile/yr by terrain). Other O&M (conductor, converter, structure) are template-driven.'
            },
            {
              id: 'insurance-parent',
              matchPath: '04_insurance',
              hidden: true
            },
            {
              id: 'operational-insurance',
              label: 'Operational Insurance',
              tier: 'working',
              matchPath: '04_insurance.insurance',
              note: 'Premium rate, insurable components, and construction-type overrides per §2.2.2.'
            }
          ],
          resetButton: 'single'
        },
        'delay-costs': {
          sections: [
            {
              id: 'delays-parent',
              matchPath: '05_delays',
              hidden: true
            },
            {
              id: 'base-delay-categories',
              label: 'Base Delay Cost Categories (Annual)',
              tier: 'first-glance',
              matchPath: '05_delays.annual_delay_costs',
              note: '§2.2.6 — constant annual costs for each delay year; PV is a level annuity at real WACC. Congestion (§2.2.7) and curtailment (§2.2.8) delay costs are computed from benefit inputs, not entered here.'
            }
          ],
          resetButton: 'single'
        },
        'risk': {
          sections: [
            {
              id: 'risk-wildfire-eal',
              label: 'Expected Cost of Wildfires',
              tier: 'working',
              matchPath: '06_wildfire_costs.wildfire',
              note: 'Expected wildfire cost: severity per event, ignition by terrain, construction-type multipliers, risk growth (§2.3.2).',
              children: [
                {
                  matchPath: '06_wildfire_costs.wildfire.ignition_rates_by_terrain',
                  label: 'Base Ignition Rates by Terrain',
                  collapsed: true
                },
                {
                  matchPath: '06_wildfire_costs.wildfire.ignition_rate_multiplier',
                  label: 'Construction-Type Multipliers',
                  collapsed: true
                }
              ]
            },
            {
              id: 'risk-outage',
              label: 'Expected Cost of Outages',
              tier: 'working',
              matchPath: '07_outage_costs.outage',
              note: 'Outage EAC: rates × duration × capacity at risk × tiered VoLL, risk growth (§2.3.3).',
              children: [
                {
                  matchPath: '07_outage_costs.outage.value_of_lost_load',
                  label: 'Value of Lost Load (VoLL Tiers)',
                  collapsed: true
                },
                {
                  matchPath: '07_outage_costs.outage.outage_duration_by_terrain',
                  label: 'Outage Duration by Terrain',
                  collapsed: true
                },
                {
                  matchPath: '07_outage_costs.outage.outage_duration_multiplier',
                  label: 'Duration Multipliers by Construction Type',
                  collapsed: true
                },
                {
                  matchPath: '07_outage_costs.outage.outage_rates.overhead',
                  label: 'Outage Frequency — Overhead',
                  collapsed: true
                },
                {
                  matchPath: '07_outage_costs.outage.outage_rates.underground',
                  label: 'Outage Frequency — Underground',
                  collapsed: true
                },
                {
                  matchPath: '07_outage_costs.outage.outage_rates.subsea',
                  label: 'Outage Frequency — Subsea',
                  collapsed: true
                }
              ]
            },
            {
              id: 'risk-parent-06',
              matchPath: '06_wildfire_costs',
              hidden: true
            },
            {
              id: 'risk-parent-07',
              matchPath: '07_outage_costs',
              hidden: true
            }
          ],
          resetButton: 'single'
        },
        'emissions': {
          sections: [
            {
              id: 'emissions-parent-16',
              matchPath: '16_emissions_reductions',
              hidden: true
            },
            {
              id: 'emissions-parent-18',
              matchPath: '18_energy_source_mix',
              hidden: true
            },
            {
              id: 'emissions-loss-comp',
              label: 'Loss-Compensation Emissions',
              tier: 'first-glance',
              matchPath: '16_emissions_reductions.emissions_reductions',
              note: 'Fraction α of line losses compensated; societal externality prices per kg (§2.4.1). Project-path shares come from Energy Source Mix below.'
            },
            {
              id: 'emissions-energy-mix',
              label: 'Energy Source Mix (Project Path)',
              tier: 'working',
              matchPath: '18_energy_source_mix.energy_source_mix',
              note: 'Initial shares and growth/decay rates for the project-path fuel mix. Preset bar selects regional defaults.'
            },
            {
              id: 'emissions-counterfactual-mix',
              label: 'Counterfactual Energy Source Mix (No-Line)',
              tier: 'working',
              matchPath: '18_energy_source_mix.counterfactual_energy_source_mix',
              note: 'No-line path for facilitated emissions and displacement reporting (§2.4.2). Defaults: same percentages as project mix, rates frozen at 0%.'
            },
            {
              id: 'emissions-intensities',
              label: 'Emission Intensities',
              tier: 'advanced',
              matchPath: '16_emissions_reductions.emissions_reductions.emission_intensities',
              note: 'kg/MWh by source × pollutant. Shared across loss-comp and facilitated emissions. Most users keep defaults.'
            }
          ],
          resetButton: 'single'
        },
        'benefits': {
          sections: [
            {
              id: 'benefits-parent',
              matchPath: '17_congestion_curtailment_reductions',
              hidden: true
            },
            {
              id: 'benefits-greenfield-remedial',
              label: 'Remedial Benefits (Greenfield)',
              tier: 'first-glance',
              matchPath: '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions',
              note: 'Congestion and curtailment relief inputs (greenfield). Delivered energy benefit is computed from capacity relief × utilization × 8760.',
              children: [
                {
                  matchPath: '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints',
                  label: 'Congestion — Binding Hours & Capacity',
                  collapsed: false
                },
                {
                  matchPath: '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.costs',
                  label: 'Congestion — Economic Valuation',
                  collapsed: false
                },
                {
                  matchPath: '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.curtailment',
                  label: 'Curtailment Reduction Parameters',
                  collapsed: false
                }
              ]
            },
            {
              id: 'benefits-recon-remedial',
              label: 'Remedial Benefits (Reconductoring)',
              tier: 'first-glance',
              matchPath: '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions',
              note: 'Reconductoring variant; effective relief = C_new − C_old.',
              children: [
                {
                  matchPath: '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints',
                  label: 'Congestion — Binding Hours & Capacity',
                  collapsed: false
                },
                {
                  matchPath: '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.costs',
                  label: 'Congestion — Economic Valuation',
                  collapsed: false
                },
                {
                  matchPath: '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.curtailment',
                  label: 'Curtailment Reduction Parameters',
                  collapsed: false
                }
              ]
            }
          ],
          resetButton: 'single'
        }
      };

      // Custom field ordering within sections
      const SECTION_FIELD_ORDER = {
        '03_financing.financial': ['base_year', 'inflation_rate', 'wacc_nominal', 'social_discount_rate', 'contingencies'],
        '16_emissions_reductions.emissions_reductions': ['compensation_percent', 'societal_costs_per_kg', 'emission_intensities'],
        '18_energy_source_mix.energy_source_mix': ['coal', 'oil', 'natural_gas', 'solar', 'wind', 'hydro', 'nuclear', 'other'],
        '18_energy_source_mix.counterfactual_energy_source_mix': ['coal', 'oil', 'natural_gas', 'solar', 'wind', 'hydro', 'nuclear', 'other']
      };

      const FIELD_LABEL_RENAME = {
        'compensation_percent': 'Loss Compensation Rate (\u03B1)',
        'severity_per_event': 'Uninsured Severity ($/event)',
        'capacity_at_risk_factor': 'Capacity at Risk (\u03C6)',
      };

      // Conductor type options filtered by construction type
      const CONDUCTOR_TYPE_BY_CONSTRUCTION = {
        'Overhead': ['Standard Aluminum Conductor', 'Advanced Aluminum Conductor'],
        'Underground Direct-Buried': ['Underground Copper Conductor'],
        'Underground Tunnel': ['Underground Copper Conductor'],
        'Subsea': ['Subsea Copper Conductor']
      };

      // Capacity options by AC/DC
      const CAPACITY_OPTIONS_BY_AC_DC = {
        'AC': [140, 329, 394, 460, 657, 1792, 2598, 6625],
        'DC': [500, 1500, 2000, 2400, 6000]
      };

      // Field metadata: units, help text, required status
      const FIELD_METADATA = {
        // Project Overview
        '01_project_technical_details.project.name': { required: true, help: 'Unique identifier for this project scenario' },
        '01_project_technical_details.project.construction_type': { required: true, help: 'Overhead, underground, or subsea. Determines build cost templates, terrain multiplier applicability, O&M rates, and outage/wildfire risk profiles.' },
        '01_project_technical_details.project.ac_dc': { required: true, help: 'AC or DC transmission. DC adds converter stations and converter losses; AC uses power factor in loss calculations.' },
        '01_project_technical_details.project.capacity_mw': { required: true, unit: 'MW', help: 'Nameplate capacity (C_new). Used for line losses, delivered energy, outage cost (capacity at risk), and effective capacity relief.' },
        '01_project_technical_details.project.conductor_type': { required: true, help: 'Determines per-mile conductor costs, resistance (for line losses), and O&M rates from the build cost templates.' },
        '01_project_technical_details.project.number_of_converters': { help: 'Number of AC/DC converter stations (DC only). Typically 2 (one at each end). Drives converter build cost and converter energy losses.' },
        '01_project_technical_details.project.converter_type': { help: 'LCC (Line Commutated Converter) or VSC (Voltage Source Converter). Determines converter loss percentage defaults (LCC ~0.75%, VSC ~1%).' },
        '01_project_technical_details.project.converter_loss_percentage': { unit: '%', help: 'Fraction of through-power lost per converter station. Defaults: 0.75% for LCC, 1% for VSC. Drives converter energy losses.' },
        '01_project_technical_details.project.reconductoring': { help: 'Enable if upgrading an existing transmission line (replaces conductor on existing structures). Disables structure/converter costs; effective relief = C_new \u2212 C_old instead of \u03C6 \u00D7 C_new.' },
        '01_project_technical_details.project.uses_existing_row': { help: 'Enable if the project uses an existing right-of-way (lease/license). Switches ROW costs from acquisition/holding to rent, and may change rent start year.' },
        '01_project_technical_details.project.line_utilization': { help: 'Average fraction of rated capacity used over the year (0\u20131). E.g. 0.7 = 70% utilized. Drives delivered energy (benefit), line losses (cost), and delay opportunity costs.' },
        '01_project_technical_details.project.baseline_electricity_price_per_mwh': { unit: '$/MWh', help: 'Wholesale electricity price used to value thermal line losses and delivered energy benefit. Should reflect the system marginal energy price.' },
        '01_project_technical_details.project.old_capacity_mw': { unit: 'MW', help: 'Existing line capacity before reconductoring (C_old). Effective capacity relief = C_new \u2212 C_old.' },
        '01_project_technical_details.project.old_conductor_type': { help: 'Conductor type of the existing line before reconductoring. Used for old-line resistance and loss calculations.' },
        '01_project_technical_details.project.old_ac_dc': { help: 'AC or DC type of the existing line before reconductoring. Determines old-line loss calculation method.' },
        '01_project_technical_details.timeline.construction_years': { required: true, unit: 'years', help: 'Duration of construction. Build, ROW, and environmental costs are spread over this period for PV. AFUDC compounds from midpoint of construction to COD.' },
        '01_project_technical_details.timeline.delay_years': { required: true, unit: 'years', help: 'Pre-construction permitting/regulatory delay. Drives base delay costs, ROW holding costs, AFUDC compounding, and congestion/curtailment delay opportunity costs.' },
        '01_project_technical_details.timeline.project_lifetime': { required: true, unit: 'years', help: 'Operational lifetime after COD. O&M, insurance, ROW rent, line losses, risk costs, and benefits all accrue over this period.' },

        // Physical Route - terrain miles and multipliers
        '02_project_physical_details.terrain.terrain_multipliers.forested': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment). Applied to build costs per weighted mile.' },
        '02_project_physical_details.terrain.terrain_multipliers.scrubbed_flat': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.wetland': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.farmland': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.desert_barren': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.urban': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.rolling_hills': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.mountain': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_multipliers.subsea': { help: 'Cost multiplier relative to flat terrain (1.0 = no adjustment).' },
        '02_project_physical_details.terrain.terrain_miles.forested': { unit: 'miles', help: 'Route miles through forested terrain. Drives build costs (via weighted miles), ROW area, environmental mitigation, wildfire ignition rates, and outage rates for this terrain.' },
        '02_project_physical_details.terrain.terrain_miles.scrubbed_flat': { unit: 'miles', help: 'Route miles through scrubbed flat terrain. Zero-mile terrains are excluded from all cost and risk calculations.' },
        '02_project_physical_details.terrain.terrain_miles.wetland': { unit: 'miles', help: 'Route miles through wetland terrain. Drives wetland mitigation credits and wetland-specific environmental costs.' },
        '02_project_physical_details.terrain.terrain_miles.farmland': { unit: 'miles', help: 'Route miles through farmland terrain.' },
        '02_project_physical_details.terrain.terrain_miles.desert_barren': { unit: 'miles', help: 'Route miles through desert/barren terrain.' },
        '02_project_physical_details.terrain.terrain_miles.urban': { unit: 'miles', help: 'Route miles through urban terrain. Typically has the highest terrain cost multiplier.' },
        '02_project_physical_details.terrain.terrain_miles.rolling_hills': { unit: 'miles', help: 'Route miles through rolling hills terrain.' },
        '02_project_physical_details.terrain.terrain_miles.mountain': { unit: 'miles', help: 'Route miles through mountain terrain.' },
        '02_project_physical_details.terrain.terrain_miles.subsea': { unit: 'miles', help: 'Route miles through subsea terrain. Subsea segments use subsea-specific build costs and outage rates.' },

        // Financial
        '03_financing.financial.inflation_rate': { help: 'Annual inflation rate (\u03C0). Used in the Fisher equation to convert nominal WACC to real WACC: r_real = (1 + r_nom)/(1 + \u03C0) \u2212 1.' },
        '03_financing.financial.base_year': { required: true, help: 'Reference year for all present-value calculations. All dollar amounts are expressed in base-year dollars.' },
        '03_financing.financial.wacc_nominal': { help: 'Nominal Weighted Average Cost of Capital. Used as AFUDC rate and for utility-perspective discounting. Converted to real WACC via Fisher equation for societal PV.' },
        '03_financing.financial.social_discount_rate': { help: 'Rate for discounting externality costs: emissions, expected wildfire cost, expected outage cost. OMB Circular A-4 recommends 2\u20137%.' },
        '03_financing.financial.capital_structure.equity_percent': { help: 'Fraction of capital from equity financing. Must sum with debt percent to 1.0.' },
        '03_financing.financial.capital_structure.debt_percent': { help: 'Fraction of capital from debt financing. Must sum with equity percent to 1.0.' },
        '03_financing.financial.capital_structure.cost_of_equity': { help: 'Required return on equity investment' },
        '03_financing.financial.capital_structure.cost_of_debt': { help: 'Interest rate on debt financing' },
        '03_financing.financial.contingencies.conductor_contingency': { help: 'Contingency factor for conductor costs (0\u201350%). Applied as (1 + factor) \u00D7 terrain-adjusted conductor cost.' },
        '03_financing.financial.contingencies.structure_contingency': { help: 'Contingency factor for structure costs (0\u201350%). Applied as (1 + factor) \u00D7 terrain-adjusted structure cost.' },
        '03_financing.financial.contingencies.converter_contingency': { help: 'Contingency factor for converter costs (0\u201350%, DC only). Applied as (1 + factor) \u00D7 converter cost.' },
        '03_financing.financial.revenue.rate_based.enabled': { help: 'Enable rate-based revenue requirement calculation. When on, computes annual revenue = allowed return rate \u00D7 rate base (capitalized AFUDC-eligible costs).' },
        '03_financing.financial.revenue.rate_based.allowed_return_rate': { help: 'Annual return rate on rate base (regulatory allowed return). Revenue = rate \u00D7 nominal rate base at COD.' },
        '03_financing.financial.afudc.apply_afudc': { help: 'Apply Allowance for Funds Used During Construction. Compounds pre-COD capital spending at nominal WACC to the commercial operation date.' },
        '03_financing.financial.afudc.delay_period_active_work': { help: 'If enabled, AFUDC accrues during the delay period (pre-construction work in progress). If disabled, AFUDC is suspended during delay — conservative default per FERC.' },
        // AFUDC Timing Patterns
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.during_delay': { help: 'Fraction of build cost incurred during delay period (typically 0 \u2014 construction hasn\u2019t started).' },
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.during_construction': { help: 'Fraction of build cost incurred during construction (typically 1.0 \u2014 spread uniformly).' },
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.afudc_eligible': { help: 'Whether build costs qualify for AFUDC capitalization (Account 107 CWIP). Typically yes.' },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.during_delay': { help: 'Fraction of ROW acquisition cost incurred during delay (typically 0.8 \u2014 land acquired before construction).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.during_construction': { help: 'Fraction of ROW acquisition cost incurred during construction (typically 0.2 \u2014 final parcels).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.afudc_eligible': { help: 'Whether ROW acquisition qualifies for AFUDC. Typically yes \u2014 capitalized to plant cost.' },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.during_delay': { help: 'Fraction of ROW holding (option fee) incurred during delay (typically 1.0 \u2014 holding costs are a delay-period expense).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.during_construction': { help: 'Fraction of ROW holding incurred during construction (typically 0).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.afudc_eligible': { help: 'Whether ROW holding qualifies for AFUDC. Often no \u2014 treated as operating expense.' },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.during_delay': { help: 'Fraction of ROW rent incurred during delay (0 for most agreement types).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.during_construction': { help: 'Fraction of ROW rent incurred during construction (0 \u2014 rent is an operational cost post-COD).' },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.afudc_eligible': { help: 'Whether ROW rent qualifies for AFUDC. No \u2014 operational expense.' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.during_delay': { help: 'Fraction of base mitigation/restoration cost incurred during delay (typically 0).' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.during_construction': { help: 'Fraction of base mitigation cost incurred during construction (typically 1.0).' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.afudc_eligible': { help: 'Whether base environmental mitigation qualifies for AFUDC. Typically yes \u2014 necessary for plant readiness.' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.during_delay': { help: 'Fraction of environmental credit purchases during delay (typically 0.2 \u2014 early permitting).' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.during_construction': { help: 'Fraction of environmental credit purchases during construction (typically 0.8).' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.afudc_eligible': { help: 'Whether environmental credits qualify for AFUDC. Typically yes \u2014 required for regulatory approval.' },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.during_delay': { help: 'Fraction of delay costs incurred during delay (1.0 by definition).' },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.during_construction': { help: 'Fraction of delay costs incurred during construction (0 by definition).' },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.afudc_eligible': { help: 'Whether delay costs qualify for AFUDC. Typically no \u2014 expensed, not capitalized.' },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.during_delay': { help: 'Fraction of O&M incurred during delay (0 \u2014 O&M begins at COD).' },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.during_construction': { help: 'Fraction of O&M incurred during construction (0 \u2014 O&M begins at COD).' },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.afudc_eligible': { help: 'Whether O&M qualifies for AFUDC. No \u2014 operating expense.' },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.during_delay': { help: 'Fraction of construction insurance incurred during delay (typically 0).' },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.during_construction': { help: 'Fraction of construction insurance incurred during construction (typically 1.0).' },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.afudc_eligible': { help: 'Whether construction insurance qualifies for AFUDC. Can be capitalized as part of construction cost.' },

        // Insurance (Tab 5 — Operational Costs)
        '04_insurance.insurance.premium_rate': { help: 'Annual insurance premium as fraction of insured value. Applied to the sum of insured component build costs.' },
        '04_insurance.insurance.insurable_components.conductors': { help: 'Include conductor build costs in the insured value base.' },
        '04_insurance.insurance.insurable_components.structures': { help: 'Include structure build costs in the insured value base.' },
        '04_insurance.insurance.insurable_components.converters': { help: 'Include converter build costs in the insured value base (DC only).' },
        '04_insurance.insurance.premium_by_construction_type.overhead': { help: 'Construction-phase premium multiplier for overhead lines.' },
        '04_insurance.insurance.premium_by_construction_type.underground': { help: 'Construction-phase premium multiplier for underground lines.' },
        '04_insurance.insurance.premium_by_construction_type.subsea': { help: 'Construction-phase premium multiplier for subsea lines.' },

        // Environmental Mitigation (Tab 4 — Capital Costs)
        '09_environmental_mitigation.environmental_mitigation.mitigation_uplift_factor': { help: 'Multiplier applied to base per-acre mitigation costs to account for project-specific conditions (§2.1.3). 1.0 = no uplift.' },

        // Delays (Tab 6 — Delay Costs)
        '05_delays.annual_delay_costs.legal': { unit: '$/year', help: 'Annual legal costs incurred during each delay year (litigation, regulatory counsel).' },
        '05_delays.annual_delay_costs.admin': { unit: '$/year', help: 'Annual administrative overhead during each delay year.' },
        '05_delays.annual_delay_costs.labor': { unit: '$/year', help: 'Annual labor costs to maintain project readiness during each delay year.' },
        '05_delays.annual_delay_costs.material_and_equipment': { unit: '$/year', help: 'Annual material storage and equipment maintenance during each delay year.' },
        '05_delays.annual_delay_costs.regulatory': { unit: '$/year', help: 'Annual regulatory compliance and permitting costs during each delay year.' },
        '05_delays.annual_delay_costs.public_relations': { unit: '$/year', help: 'Annual community engagement and public relations costs during each delay year.' },
        '05_delays.annual_delay_costs.project_management': { unit: '$/year', help: 'Annual project management overhead during each delay year.' },
        '05_delays.annual_delay_costs.miscellaneous': { unit: '$/year', help: 'Other annual costs during each delay year not captured above.' },

        // Wildfire
        '06_wildfire_costs.wildfire.severity_per_event': { unit: '$/event', help: 'Average cost per wildfire ignition event (societal damages, deductibles, liability costs).' },
        '06_wildfire_costs.wildfire.risk_growth_rate': { help: 'Annual increase in wildfire risk' },
        '06_wildfire_costs.wildfire.discount_rate_source': { help: 'Which discount rate to use for wildfire cost PV' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.forested': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for forested terrain (before construction-type multiplier).' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.scrubbed_flat': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for scrubbed flat terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.wetland': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for wetland terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.farmland': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for farmland terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.desert_barren': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for desert/barren terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.urban': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for urban terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.rolling_hills': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for rolling hills terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.mountain': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for mountain terrain.' },
        '06_wildfire_costs.wildfire.ignition_rates_by_terrain.subsea': { unit: 'events/mi/yr', help: 'Base wildfire ignition rate for subsea terrain (typically 0).' },
        '06_wildfire_costs.wildfire.ignition_rate_multiplier.overhead': { help: 'Multiplier applied to base ignition rate for overhead construction.' },
        '06_wildfire_costs.wildfire.ignition_rate_multiplier.underground': { help: 'Multiplier applied to base ignition rate for underground construction (typically 0).' },
        '06_wildfire_costs.wildfire.ignition_rate_multiplier.subsea': { help: 'Multiplier applied to base ignition rate for subsea construction (typically 0).' },

        // Outage (Tab 7 — Risk Costs)
        '07_outage_costs.outage.capacity_at_risk_factor': { help: 'Fraction of line capacity lost per outage event (0\u20131). 1.0 = radial (all capacity lost); <1 for meshed/redundant configurations.' },
        '07_outage_costs.outage.risk_growth_rate': { help: 'Annual increase in outage risk (compounds over project lifetime).' },
        '07_outage_costs.outage.outage_duration_by_terrain.forested': { unit: 'hrs/event', help: 'Average outage duration for forested terrain (before construction-type multiplier).' },
        '07_outage_costs.outage.outage_duration_by_terrain.scrubbed_flat': { unit: 'hrs/event', help: 'Average outage duration for scrubbed flat terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.wetland': { unit: 'hrs/event', help: 'Average outage duration for wetland terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.farmland': { unit: 'hrs/event', help: 'Average outage duration for farmland terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.desert_barren': { unit: 'hrs/event', help: 'Average outage duration for desert/barren terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.urban': { unit: 'hrs/event', help: 'Average outage duration for urban terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.rolling_hills': { unit: 'hrs/event', help: 'Average outage duration for rolling hills terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.mountain': { unit: 'hrs/event', help: 'Average outage duration for mountain terrain.' },
        '07_outage_costs.outage.outage_duration_by_terrain.subsea': { unit: 'hrs/event', help: 'Average outage duration for subsea terrain.' },
        '07_outage_costs.outage.outage_duration_multiplier.overhead': { help: 'Duration multiplier for overhead construction type.' },
        '07_outage_costs.outage.outage_duration_multiplier.underground': { help: 'Duration multiplier for underground construction type.' },
        '07_outage_costs.outage.outage_duration_multiplier.subsea': { help: 'Duration multiplier for subsea construction type.' },

        // Congestion & Curtailment — Greenfield (Tab 9 — Benefits)
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.flow_factor': { help: 'Fraction of nameplate capacity that effectively relieves the constraint (0\u20131). Accounts for flow distribution on meshed networks. Greenfield: \u03C6 \u00D7 C_new = effective relief.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.binding_hours': { unit: 'hrs/year', help: 'Hours per year the transmission constraint is binding.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.average_exceedance': { unit: 'MW', help: 'Average MW exceeding constraint capacity when binding.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.saturation_factor': { help: 'Conservative haircut applied to congestion benefit (0 = no haircut, 1 = full haircut). Reduces benefit to account for uncertainty.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.costs.average_congestion_price': { unit: '$/MWh', help: 'Average locational marginal price differential during binding hours.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.curtailment.curtailment_hours_total': { unit: 'hrs/year', help: 'Total annual hours of renewable curtailment relieved by the project.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.curtailment.average_curtailment_mw': { unit: 'MW', help: 'Average MW curtailed during curtailment hours.' },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.curtailment.average_curtailment_price': { unit: '$/MWh', help: 'Typically PPA price or avoided cost of curtailed energy.' },

        // Congestion & Curtailment — Reconductoring (Tab 9 — Benefits)
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.flow_factor': { help: 'Fraction of incremental capacity (C_new − C_old) that relieves the constraint.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.binding_hours': { unit: 'hrs/year', help: 'Hours per year the transmission constraint is binding.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.average_exceedance': { unit: 'MW', help: 'Average MW exceeding constraint capacity when binding.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.saturation_factor': { help: 'Conservative haircut on congestion benefit (0 = no haircut, 1 = full haircut).' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.costs.average_congestion_price': { unit: '$/MWh', help: 'Average locational marginal price differential during binding hours.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.curtailment.curtailment_hours_total': { unit: 'hrs/year', help: 'Total annual hours of curtailment relieved.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.curtailment.average_curtailment_mw': { unit: 'MW', help: 'Average MW curtailed during curtailment hours.' },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.curtailment.average_curtailment_price': { unit: '$/MWh', help: 'Typically PPA price or avoided cost of curtailed energy.' },

        // Emissions (Tab 8)
        '16_emissions_reductions.emissions_reductions.compensation_percent': { help: 'Fraction of line energy losses compensated by additional generation (\u03B1). 1.0 = all losses compensated; 0 = no loss-compensation emissions.' },
        '16_emissions_reductions.emissions_reductions.societal_costs_per_kg.co2_cost_per_kg': { unit: '$/kg', help: 'Societal cost of CO\u2082 emissions per kilogram (social cost of carbon).' },
        '16_emissions_reductions.emissions_reductions.societal_costs_per_kg.sox_cost_per_kg': { unit: '$/kg', help: 'Societal cost of SO\u2093 emissions per kilogram.' },
        '16_emissions_reductions.emissions_reductions.societal_costs_per_kg.nox_cost_per_kg': { unit: '$/kg', help: 'Societal cost of NO\u2093 emissions per kilogram.' }
      };

      // Add ROW zone units + help for all 15 zones
      for (let i = 1; i <= 15; i++) {
        const z = `zone_${i}`;
        FIELD_METADATA[`11_project_row_details.right_of_way.${z}.miles`] = { unit: 'miles', help: 'Route miles through this ROW zone. Zone miles × ROW width = zone acreage for cost calculations.' };
        FIELD_METADATA[`11_project_row_details.right_of_way.${z}.acquisition_cost`] = { unit: '$/acre', help: 'Per-acre land acquisition cost for this zone (§2.1.2). Applied to zone acreage for capital ROW cost.' };
        FIELD_METADATA[`11_project_row_details.right_of_way.${z}.rent_cost`] = { unit: '$/acre/year', help: 'Annual per-acre rent for existing ROW (§2.2.3). Classified as operational cost; remains here until field migration.' };
        FIELD_METADATA[`11_project_row_details.right_of_way.${z}.hold_cost`] = { unit: '$/acre/year', help: 'Annual per-acre holding cost (option fee) during delay and construction periods (§2.1.2).' };
      }

      // Add outage rate units for all construction type × terrain combinations
      ['overhead', 'underground', 'subsea'].forEach(ct => {
        ['forested', 'scrubbed_flat', 'wetland', 'farmland', 'desert_barren', 'urban', 'rolling_hills', 'mountain', 'subsea'].forEach(terrain => {
          FIELD_METADATA[`07_outage_costs.outage.outage_rates.${ct}.${terrain}`] = { unit: 'outages/mi/yr' };
        });
      });

      // Fields to show/hide based on conditions
      const CONDITIONAL_FIELDS = {
        // DC-only fields
        dc_only: [
          '01_project_technical_details.project.number_of_converters',
          '01_project_technical_details.project.converter_type',
          '01_project_technical_details.project.converter_loss_percentage',
          '03_financing.financial.contingencies.converter_contingency'
        ],
        // Reconductoring-only fields
        reconductoring_only: [
          '01_project_technical_details.project.old_capacity_mw',
          '01_project_technical_details.project.old_conductor_type',
          '01_project_technical_details.project.old_ac_dc'
        ],
        // Fields permanently hidden from UI (data retained in JSON for backend)
        always_hidden: [
          // Greenfield comparison fields (moved to Counterfactual Calculators subtab)
          '01_project_technical_details.project.greenfield_comparison_capacity_mw',
          '01_project_technical_details.project.greenfield_comparison_conductor_type',
          // Capital structure (CTCC defaults to WACC nominal)
          '03_financing.financial.capital_structure.equity_percent',
          '03_financing.financial.capital_structure.debt_percent',
          '03_financing.financial.capital_structure.cost_of_equity',
          '03_financing.financial.capital_structure.cost_of_debt',
          // Risk discount rate selectors (locked to social discount rate)
          '06_wildfire_costs.wildfire.discount_rate_source',
          '06_wildfire_costs.wildfire.discount_rate_custom',
          '07_outage_costs.outage.discount_rate_type',
          // Congestion near-binding fields (removed per user request)
          '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.near_binding_hours',
          '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.near_average_exceedance',
          '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.near_binding_relief_factor',
          '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.costs.value_of_lost_load',
          '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.near_binding_hours',
          '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.near_average_exceedance',
          '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.near_binding_relief_factor',
          '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.costs.value_of_lost_load'
        ]
      };

      // Field configuration for special input types
      const FIELD_CONFIG = {
        // Dropdowns
        '01_project_technical_details.project.construction_type': {
          type: 'dropdown',
          options: ['Overhead', 'Underground Direct-Buried', 'Underground Tunnel', 'Subsea']
        },
        '01_project_technical_details.project.ac_dc': {
          type: 'dropdown',
          options: ['AC', 'DC']
        },
        // Conductor type — options filtered dynamically by construction_type
        '01_project_technical_details.project.conductor_type': {
          type: 'dropdown',
          options: ['Standard Aluminum Conductor', 'Advanced Aluminum Conductor', 'Underground Copper Conductor', 'Subsea Copper Conductor']
        },
        // Capacity MW — dynamic dropdown based on AC/DC
        '01_project_technical_details.project.capacity_mw': {
          type: 'dynamic_dropdown',
          optionSets: CAPACITY_OPTIONS_BY_AC_DC,
          dependsOn: '01_project_technical_details.project.ac_dc',
          suffix: ' MW'
        },
        // Old capacity MW — dynamic dropdown for reconductoring
        '01_project_technical_details.project.old_capacity_mw': {
          type: 'dynamic_dropdown',
          optionSets: CAPACITY_OPTIONS_BY_AC_DC,
          dependsOn: '01_project_technical_details.project.ac_dc',
          suffix: ' MW',
          allowBlank: true
        },
        // Base year — plain number, no comma formatting
        '03_financing.financial.base_year': { type: 'dropdown', options: Array.from({length: 31}, (_, i) => 2020 + i) },
        '01_project_technical_details.project.number_of_converters': {
          type: 'dropdown',
          options: [0, 1, 2]
        },
        '01_project_technical_details.project.converter_type': {
          type: 'dropdown',
          options: ['NA', 'LCC Converter', 'VSC Converter']
        },
        '01_project_technical_details.project.old_conductor_type': {
          type: 'dropdown',
          options: ['', 'Standard Aluminum Conductor', 'Advanced Aluminum Conductor', 'Underground Copper Conductor', 'Subsea Copper Conductor']
        },
        '01_project_technical_details.project.old_ac_dc': {
          type: 'dropdown',
          options: ['', 'AC', 'DC']
        },
        '06_wildfire_costs.wildfire.discount_rate_source': {
          type: 'dropdown',
          options: ['social', 'wacc_real', 'custom']
        },
        '07_outage_costs.outage.discount_rate_type': {
          type: 'dropdown',
          options: ['social', 'wacc_real']
        },

        // Toggles (booleans that should be toggle switches)
        '01_project_technical_details.project.reconductoring': { type: 'toggle' },
        '01_project_technical_details.project.uses_existing_row': { type: 'toggle' },
        '03_financing.financial.afudc.apply_afudc': { type: 'toggle' },
        '03_financing.financial.afudc.delay_period_active_work': { type: 'toggle' },
        '03_financing.financial.revenue.rate_based.enabled': { type: 'toggle' },
        '04_insurance.insurance.insurable_components.conductors': { type: 'toggle' },
        '04_insurance.insurance.insurable_components.structures': { type: 'toggle' },
        '04_insurance.insurance.insurable_components.converters': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.afudc_eligible': { type: 'toggle' },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.afudc_eligible': { type: 'toggle' },

        // Sliders — pct:true means the text box displays as % (value×100)
        '01_project_technical_details.project.line_utilization': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '03_financing.financial.inflation_rate': { type: 'slider', min: 0, max: 0.2, step: 0.005, pct: true },
        '03_financing.financial.wacc_nominal': { type: 'slider', min: 0, max: 0.2, step: 0.005, pct: true },
        '03_financing.financial.social_discount_rate': { type: 'slider', min: 0, max: 0.1, step: 0.005, pct: true },
        '03_financing.financial.contingencies.conductor_contingency': { type: 'slider', min: 0, max: 0.5, step: 0.01, pct: true },
        '03_financing.financial.contingencies.structure_contingency': { type: 'slider', min: 0, max: 0.5, step: 0.01, pct: true },
        '03_financing.financial.contingencies.converter_contingency': { type: 'slider', min: 0, max: 0.5, step: 0.01, pct: true },
        '03_financing.financial.capital_structure.equity_percent': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '03_financing.financial.capital_structure.debt_percent': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '03_financing.financial.capital_structure.cost_of_equity': { type: 'slider', min: 0, max: 0.3, step: 0.005, pct: true },
        '03_financing.financial.capital_structure.cost_of_debt': { type: 'slider', min: 0, max: 0.2, step: 0.005, pct: true },
        '03_financing.financial.revenue.rate_based.allowed_return_rate': { type: 'slider', min: 0, max: 0.2, step: 0.005, pct: true },
        '04_insurance.insurance.premium_rate': { type: 'slider', min: 0, max: 1, step: 0.001, pct: true },
        '06_wildfire_costs.wildfire.risk_growth_rate': { type: 'slider', min: 0, max: 0.1, step: 0.005, pct: true },
        '07_outage_costs.outage.risk_growth_rate': { type: 'slider', min: 0, max: 0.1, step: 0.005, pct: true },
        '07_outage_costs.outage.capacity_at_risk_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '16_emissions_reductions.emissions_reductions.compensation_percent': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.flow_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.congestion.constraints.saturation_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '17_congestion_curtailment_reductions.greenfield_congestion_curtailment_reductions.curtailment.curtailment_saturation_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.flow_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.congestion.constraints.saturation_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        '17_congestion_curtailment_reductions.reconductoring_congestion_curtailment_reductions.curtailment.curtailment_saturation_factor': { type: 'slider', min: 0, max: 1, step: 0.01 },
        // Cost timing patterns sliders (0-1, shown as %)
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.build_costs.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_acquisition.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_holding.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.row_rent.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_base.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.environmental_mitigation_credits.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.delay_costs.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.operations_and_maintenance.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.during_delay': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true },
        '19_cost_timing_patterns.cost_timing_patterns.construction_insurance.during_construction': { type: 'slider', min: 0, max: 1, step: 0.01, pct: true }
      };
