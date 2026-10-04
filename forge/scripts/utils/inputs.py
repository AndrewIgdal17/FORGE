"""Input section accessor for the active run.

``section(name)`` returns the named section of the current run's inputs dict.
Every loader that previously opened a defaults YAML file calls this
instead. The function is intentionally minimal — it reads from the RunState
that ``run_calculation`` sets before any module runs.
"""
from __future__ import annotations

from forge.scripts.utils.run_context import get_run_state


def section(name: str) -> dict:
    """Return the named input section for the active run.

    Args:
        name: YAML stem, e.g. ``"03_financing"``.

    Returns:
        The section dict from the run's inputs.

    Raises:
        KeyError: If the section name is not in the run's inputs.
        RuntimeError: If no run is active (via ``get_run_state``).
    """
    state = get_run_state()
    return state.inputs[name]
