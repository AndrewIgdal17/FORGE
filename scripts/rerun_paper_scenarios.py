#!/usr/bin/env python3
"""
Re-run all CTCC real-world case study scenarios via the web API, update .ctcc
files with fresh results, and generate paper CSVs for figure generation.

Prerequisites:
    CTCC server running at http://127.0.0.1:8000
    (start with: cd repos/ctcc && ./run_calc_server.command)

Usage:
    cd repos/ctcc
    venv/bin/python3 scripts/rerun_paper_scenarios.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

API_URL = "http://127.0.0.1:8000/api/ctcc/calculate"
SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
PAPER_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "Projects" / "CTCC" / "Paper1" / "data"

CASE_STUDY_SCENARIOS = {
    1: ["CTT_Actual_Delay2", "CTT_Counterfactual_Delay7"],
    2: ["SunZia_Delay17", "SunZia_Delay2", "SunZia_NoDelay"],
    3: ["AEP_LRGV_ACCC", "AEP_LRGV_ACSR_Rebuild"],
    4: ["TBC_Delay4", "TBC_NoDelay"],
    5: ["VW1_Delay2", "VW1_Delay6"],
}

# Map paper CSV line_item names -> extraction path from API response
# Values come from results.bcr (flat PV fields) or results.costs (nested)
LINE_ITEM_EXTRACTION = {
    "build": lambda r: r["costs"]["build"]["total_pv"],
    "row_capital": lambda r: r["costs"]["row"].get("row_capital_pv", 0),
    "env_mitigation": lambda r: r["costs"]["environmental"]["total_pv"],
    "oandm": lambda r: r["costs"]["oandm"]["total_pv"],
    "insurance": lambda r: r["costs"]["insurance"]["pv_total"],
    "row_rent": lambda r: r["costs"]["row"].get("row_rent_pv", 0),
    "line_losses": lambda r: r["bcr"].get("energy_losses_pv", 0),
    "residual_exceedance": lambda r: r["bcr"].get("residual_exceedance_pv", 0),
    "base_delay": lambda r: r["bcr"].get("delay_cost_pv", 0),
    "congestion_delay": lambda r: r["bcr"].get("congestion_delay_cost_pv", 0),
    "curtailment_delay": lambda r: r["bcr"].get("curtailment_delay_cost_pv", 0),
    "wildfire_risk": lambda r: r["costs"]["wildfire"]["pv_cost"],
    "outage_risk": lambda r: r["costs"]["outage"]["pv_cost"],
    "emissions": lambda r: r["costs"]["emissions"]["total_pv"],
    "facilitated_emissions": lambda r: r.get("summary", {}).get("fac_emissions_project_pv", 0) or 0,
}

SCENARIO_TO_CS = {}
for cs, scenarios in CASE_STUDY_SCENARIOS.items():
    for s in scenarios:
        SCENARIO_TO_CS[s] = cs


def extract_scenario_id(filename: str) -> str:
    """Extract scenario ID from filename: 'S1' from 'S1 CA Rural...', 'CTT_Actual_Delay2' from 'CTT_Actual_Delay2.ctcc'."""
    match = re.match(r"(S[\w]*\d+)", filename)
    if match:
        return match.group(1)
    stem = Path(filename).stem
    if stem:
        return stem
    raise ValueError(f"Cannot extract scenario ID from: {filename}")


def run_scenario(inputs: dict, scenario_id: str) -> dict:
    """POST inputs to the CTCC API and return the full JSON response."""
    payload = json.dumps({
        "combined_data": inputs,
        "scenario_id": scenario_id,
        "input_mode": "json",
    }).encode("utf-8")

    req = Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=120) as resp:
        response = json.loads(resp.read().decode("utf-8"))

    if not response.get("success"):
        raise RuntimeError(f"API error for {scenario_id}: {response.get('error')}")

    return response


def main() -> None:
    # Verify server is reachable
    try:
        urlopen("http://127.0.0.1:8000/api/final_combined", timeout=5)
    except URLError:
        print("ERROR: CTCC server not reachable at http://127.0.0.1:8000")
        print("Start it with: cd repos/ctcc && ./run_calc_server.command")
        sys.exit(1)

    ctcc_files = sorted(SCENARIOS_DIR.glob("*.ctcc"))
    if not ctcc_files:
        print(f"ERROR: No .ctcc files found in {SCENARIOS_DIR}")
        sys.exit(1)

    print(f"Found {len(ctcc_files)} scenario files")
    print("=" * 100)

    inner_results_by_scenario = {}

    for ctcc_file in ctcc_files:
        scenario_id = extract_scenario_id(ctcc_file.name)
        print(f"  Running {scenario_id} ({ctcc_file.name})...", end=" ", flush=True)

        with open(ctcc_file, "r") as f:
            data = json.load(f)

        inputs = data["inputs"]
        t0 = time.time()
        response = run_scenario(inputs, scenario_id)
        elapsed = time.time() - t0

        inner = response.get("results", response)
        data["results"] = inner
        with open(ctcc_file, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        inner_results_by_scenario[scenario_id] = inner
        print(f"OK ({elapsed:.1f}s)")

    print("\n" + "=" * 100)
    print("\nAll scenarios complete. Generating paper CSVs...\n")

    # Generate case_study_cost_line_items.csv
    PAPER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    line_items_path = PAPER_DATA_DIR / "case_study_cost_line_items.csv"
    with open(line_items_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_study", "scenario", "line_item", "value_billions"])
        for cs_num in sorted(CASE_STUDY_SCENARIOS.keys()):
            for sid in CASE_STUDY_SCENARIOS[cs_num]:
                r = inner_results_by_scenario[sid]
                for line_item, extractor in LINE_ITEM_EXTRACTION.items():
                    try:
                        value = extractor(r) or 0
                    except (KeyError, TypeError):
                        value = 0
                    writer.writerow([cs_num, sid, line_item, f"{value / 1e9:.2f}"])
    print(f"  Wrote {line_items_path}")

    # Generate case_study_total_costs.csv
    totals_path = PAPER_DATA_DIR / "case_study_total_costs.csv"
    with open(totals_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_study", "scenario", "total_costs_billions"])
        for cs_num in sorted(CASE_STUDY_SCENARIOS.keys()):
            for sid in CASE_STUDY_SCENARIOS[cs_num]:
                r = inner_results_by_scenario[sid]
                total = r.get("bcr", {}).get("total_costs_pv", 0) or 0
                writer.writerow([cs_num, sid, f"{total / 1e9:.2f}"])
    print(f"  Wrote {totals_path}")

    # Print summary table for paper verification
    print("\n" + "=" * 100)
    header = f"{'Scenario':<30} {'Total($B)':<11} {'Risk($B)':<11} {'BCR_sys':<9} {'BCR_xWF':<9} {'BCR_xWF+O':<10} {'NetBen($B)':<11}"
    print(header)
    print("-" * 100)
    for cs_num in sorted(CASE_STUDY_SCENARIOS.keys()):
        for sid in CASE_STUDY_SCENARIOS[cs_num]:
            r = inner_results_by_scenario[sid]
            bcr = r.get("bcr", {})
            summary = r.get("summary", {})

            total = (bcr.get("total_costs_pv", 0) or 0) / 1e9
            risk = (summary.get("total_risk_pv", 0) or 0) / 1e9
            bcr_sys = bcr.get("bcr_societal", 0) or 0
            bcr_xwf = bcr.get("bcr_excluding_wildfire_risk", 0) or 0
            bcr_xwfo = bcr.get("bcr_excluding_wildfire_risk_and_outage_risk", 0) or 0
            benefits = (bcr.get("total_benefits_pv", 0) or 0) / 1e9
            net_ben = benefits - total

            print(f"{sid:<30} {total:<11.2f} {risk:<11.2f} {bcr_sys:<9.3f} {bcr_xwf:<9.3f} {bcr_xwfo:<10.3f} {net_ben:<11.2f}")
        print()

    print("Done. Use these values to update main.tex tables.")


if __name__ == "__main__":
    main()
