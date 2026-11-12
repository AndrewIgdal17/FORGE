"""base_year is locked at 2025 for this release."""
from pathlib import Path

import pytest

from forge.errors import InvalidInputs
from test.spec05_project import project_changes, run

ROOT = Path(__file__).resolve().parents[1]
BANNED = ('base_year": 2026', 'base_year"] = 2026')
LOCKED_FILES = (
    "forge/scenarios/CTT_Actual_Delay2.forge",
    "forge/scenarios/CTT_Counterfactual_Delay7.forge",
    "forge/scenarios/AEP_LRGV_ACCC.forge",
    "forge/scenarios/AEP_LRGV_ACSR_Rebuild.forge",
    "forge/scenarios/AEP_LRGV_Laredo_NewBuild.forge",
    "forge/scripts/runners/run_ctt.py",
    "forge/scripts/runners/run_lrgv_accc.py",
    "forge/scripts/runners/run_lrgv_newbuild.py",
)


def test_base_year_other_than_2025_is_rejected():
    changes = project_changes(**{"03_financing.financial.base_year": 2026})
    with pytest.raises(InvalidInputs, match="base_year must be 2025 in this release"):
        run(changes)


def test_bundled_scenarios_and_runners_do_not_write_base_year_2026():
    offenders = []
    for relative in LOCKED_FILES:
        text = (ROOT / relative).read_text()
        hits = [needle for needle in BANNED if needle in text]
        if hits:
            offenders.append(f"{relative}: {hits}")
    assert offenders == []
