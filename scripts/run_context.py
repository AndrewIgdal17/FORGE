"""
Run context for in-process pipeline.

Provides two global singletons:
1. Output manager — shared aggregator so scripts don't each write their own file.
2. RunContext — cached YAML data so loaders skip redundant file I/O.

Orchestrator sets both before the script loop and clears after.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from build_costs import BuildCosts
    from yaml_loaders import FinancingDetails, ProjectTechnicalDetails


# ---------------------------------------------------------------------------
# Output manager (existing)
# ---------------------------------------------------------------------------

_current_output_manager = None


def set_output_manager(manager):
    """Set the shared output manager (used by orchestrator for in-process runs)."""
    global _current_output_manager
    _current_output_manager = manager


def get_output_manager():
    """Return the shared output manager, or None if not in in-process mode."""
    return _current_output_manager


def clear_output_manager():
    """Clear the shared output manager after the script loop."""
    global _current_output_manager
    _current_output_manager = None


# ---------------------------------------------------------------------------
# RunContext — shared YAML data cache
# ---------------------------------------------------------------------------


@dataclass
class RunContext:
    """Cached shared data for a single pipeline run.

    Populated once by the orchestrator before the module loop.
    Loaders check get_run_context() and return cached values when set,
    falling back to YAML reads when None (subprocess / standalone mode).
    """

    project_details: ProjectTechnicalDetails
    terrain_miles: Dict[str, float]
    terrain_multipliers: Dict[str, float]
    total_miles: float
    financing: FinancingDetails
    contingencies: Dict[str, float]
    category_string: str
    row_width_feet: float
    weighted_miles: float
    average_terrain_multiplier: float
    build_costs: Optional[BuildCosts] = None
    derived_parameters: Dict[str, Any] = dc_field(default_factory=dict)


_current_run_context: Optional[RunContext] = None


def set_run_context(ctx: RunContext) -> None:
    """Set the shared RunContext for the current pipeline run."""
    global _current_run_context
    _current_run_context = ctx


def get_run_context() -> Optional[RunContext]:
    """Return the shared RunContext, or None if not in in-process mode."""
    return _current_run_context


def clear_run_context() -> None:
    """Clear the shared RunContext after the pipeline run."""
    global _current_run_context
    _current_run_context = None


def set_build_costs(costs: BuildCosts) -> None:
    """Attach build costs to the current RunContext. No-op if no context is set."""
    global _current_run_context
    if _current_run_context is not None:
        _current_run_context.build_costs = costs


def add_derived(params: Dict[str, Any]) -> None:
    """Merge derived parameters into the current RunContext. No-op if no context is set."""
    if _current_run_context is not None:
        _current_run_context.derived_parameters.update(params)
