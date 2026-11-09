"""Bundled scenarios and live results carry no facilitated-emissions keys."""
import json
from pathlib import Path

from test.spec05_project import project_changes, run

ROOT = Path(__file__).resolve().parents[1]


def test_no_facilitated_strings_anywhere():
    hits = []
    for base in (ROOT / "forge", ROOT / "test" / "golden"):
        for p in base.rglob("*"):
            if p.suffix in {".py", ".yaml", ".forge", ".json"} and p.is_file():
                text = p.read_text(errors="ignore")
                if "facilitated" in text or "fac_emissions" in text:
                    hits.append(str(p.relative_to(ROOT)))
    assert hits == []


def test_results_and_taxonomy_have_no_facilitated_keys():
    r = run(project_changes())
    assert "facilitated" not in json.dumps(r) and "fac_emissions" not in json.dumps(r)


def test_bundled_inputs_use_new_escalation_key():
    for p in (ROOT / "forge" / "scenarios").glob("*.forge"):
        fin = json.loads(p.read_text())["inputs"]["03_financing"]["financial"]
        assert "construction_cost_escalation_nominal" in fin and "construction_cost_escalation_rate" not in fin
