#!/usr/bin/env python3
"""Delete dead code blocks from index.html.

Reads the file, removes specified line ranges and comment lines,
collapses excessive blank lines, and verifies brace balance.
"""

import re
import sys
from pathlib import Path

TARGET = Path(__file__).parent / "index.html"

# --- Line ranges to delete (1-indexed, inclusive) ---
# Phase 3: old result renderers + section headers
# Phase 4: old form code

DELETE_RANGES = [
    # Phase 3 block: section headers + 12 renderer functions
    (4885, 5628),

    # Phase 4: old form helpers
    (2994, 3334),   # createFormField
    (3336, 3456),   # renderObjectAsForm
    (3458, 3499),   # renderJsonInputs (original)

    # Phase 4: old conditional-visibility / post-render functions
    (6014, 6093),   # updateConditionalFieldVisibility
    (6096, 6161),   # setupConditionalFieldListeners
    (6274, 6336),   # insertCalculatedTotals
    (6424, 6453),   # updateDynamicDropdowns
    (6455, 6492),   # comment + updateConductorTypeOptions
    (6494, 6508),   # styleProminentToggles
    (6510, 6552),   # comment + insertRealWaccDisplay
    (6554, 6566),   # comment + updateRealWacc
    (6568, 6609),   # comment + moveAfudcToRevenueRequirements
    (6611, 6640),   # comment + validateCostTimingPatterns
    (6642, 6684),   # comment + filterOperationalCosts
    (6686, 6712),   # comments + applyChemicalSubscripts
    (6714, 6822),   # cleanUpSectionHeaders
    (6842, 6874),   # comment + insertLockedDiscountRate
    (6886, 6899),   # comment + filterRiskTerrains
    (6901, 6941),   # comment + filterEnvironmentalTerrains
    (6943, 7267),   # comment + restructureEnergySourceMix
    (7306, 7389),   # injectFuelMixPresetBar
    (7391, 7491),   # comment + restructureEmissionIntensities
]

DELETE_SINGLE_LINES = [
    2889,   # // humanizeKey() — extracted to hierarchy-engine.js
    7582,   # // applyTabHierarchy() + humanizeKey() — extracted to hierarchy-engine.js
]

def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(lines)
    print(f"Read {total} lines from {TARGET.name}")

    # Build set of 0-indexed line numbers to delete
    to_delete = set()
    for start, end in DELETE_RANGES:
        for i in range(start - 1, end):  # convert to 0-indexed
            if i < total:
                to_delete.add(i)
    for ln in DELETE_SINGLE_LINES:
        idx = ln - 1
        if idx < total:
            to_delete.add(idx)

    print(f"Marking {len(to_delete)} lines for deletion")

    # Verify we're deleting expected function signatures
    expected_functions = [
        "renderCostOverview", "renderDelayCosts", "renderCapitalCosts",
        "renderOperationalCosts", "renderEnergyLosses", "renderRiskCosts",
        "renderFacilitatedEmissions", "renderDisplacement", "renderEmissionsCosts",
        "renderBenefitsTab", "renderSensitivityExclusions", "renderCustomBCR",
        "createFormField", "renderObjectAsForm", "renderJsonInputs",
        "updateConditionalFieldVisibility", "setupConditionalFieldListeners",
        "insertCalculatedTotals", "updateDynamicDropdowns",
        "updateConductorTypeOptions", "styleProminentToggles",
        "insertRealWaccDisplay", "updateRealWacc",
        "moveAfudcToRevenueRequirements", "validateCostTimingPatterns",
        "filterOperationalCosts", "applyChemicalSubscripts",
        "cleanUpSectionHeaders", "insertLockedDiscountRate",
        "filterRiskTerrains", "filterEnvironmentalTerrains",
        "restructureEnergySourceMix", "injectFuelMixPresetBar",
        "restructureEmissionIntensities",
    ]

    # Safety: make sure we're NOT deleting any protected functions
    protected = [
        "renderCTCCResults", "renderBCRHeadline", "renderPerspectivesTable",
        "renderCostsByTaxonomy", "renderBenefitsByTaxonomy",
        "renderSensitivityByTaxonomy", "renderCustomBCRByTaxonomy",
        "renderInputsFromTaxonomy", "createFieldFromMetadata",
        "setupTaxonomyConditionalVisibility",
        "collectJsonData", "normalizeEnergySourceMixInCombinedData",
        "formatNumber", "formatCurrency", "formatCurrency2",
        "parseNumberInput", "getValueAtPath", "switchTab",
    ]

    deleted_content = "".join(lines[i] for i in sorted(to_delete))
    for pf in protected:
        pat = rf"\bfunction\s+{pf}\b"
        if re.search(pat, deleted_content):
            print(f"ERROR: Would delete protected function '{pf}' — aborting!")
            sys.exit(1)

    found = []
    for ef in expected_functions:
        pat = rf"\bfunction\s+{ef}\b"
        if re.search(pat, deleted_content):
            found.append(ef)
        else:
            print(f"WARNING: Expected function '{ef}' not found in deletion range")

    print(f"Confirmed {len(found)}/{len(expected_functions)} expected functions in deletion ranges")

    # Perform deletion
    kept = [line for i, line in enumerate(lines) if i not in to_delete]
    print(f"Kept {len(kept)} lines (deleted {total - len(kept)})")

    # Collapse runs of >2 blank lines
    collapsed = []
    blank_run = 0
    for line in kept:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)

    print(f"After blank-line collapse: {len(collapsed)} lines")

    # Verify brace balance in <script> sections
    in_script = False
    brace_count = 0
    for line in collapsed:
        stripped = line.strip()
        if "<script>" in line.lower():
            in_script = True
            continue
        if "</script>" in line.lower():
            in_script = False
            continue
        if in_script:
            # Skip string literals (rough)
            clean = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`|//.*$", "", line)
            brace_count += clean.count("{") - clean.count("}")

    if brace_count != 0:
        print(f"WARNING: Brace imbalance in script sections: {brace_count}")
    else:
        print("Brace balance check: PASS")

    # Write result
    TARGET.write_text("".join(collapsed), encoding="utf-8")
    print(f"Wrote {len(collapsed)} lines to {TARGET.name}")

if __name__ == "__main__":
    main()
