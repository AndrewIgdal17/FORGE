# forge/scripts/runners/

Case-study scenario runners. Each script loads a named project's inputs, calls `forge.run_calculation`, and writes a `.forge` scenario file.

Covered studies: CTT, LRGV ACCC, LRGV new-build, SunZia, TBC, Vineyard Wind. Shared helpers live in `forge.scripts.utils.scenario_utils`.
