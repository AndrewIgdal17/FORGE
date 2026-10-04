"""Run state for the FORGE calculation pipeline.

A single ``contextvars.ContextVar`` holds each run's mutable state so that
concurrent calls on different threads see only their own data. The public
accessors (``get_run_context``, ``get_output_manager``, ``add_derived``, etc.)
read and write through that variable.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field as dc_field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from forge.scripts.calc.build_costs import BuildCosts
    from forge.scripts.io.yaml_loaders import FinancingDetails, ProjectTechnicalDetails


@dataclass
class RunContext:
    """Cached shared data for a single pipeline run.

    Populated once by the orchestrator before the module loop.
    Loaders check get_run_context() and return cached values when set,
    falling back to section() reads when None.
    """
    project_details: ProjectTechnicalDetails
    terrain_miles: dict[str, float]
    terrain_multipliers: dict[str, float]
    total_miles: float
    financing: FinancingDetails
    contingencies: dict[str, float]
    category_string: str
    row_width_feet: float
    weighted_miles: float
    average_terrain_multiplier: float
    number_of_converters: int = 0
    social_discount_rate: float = 0.0
    afudc_rate: float = 0.0
    afudc_source: str = ""
    cod_year: float = 0.0
    construction_start_year: float = 0.0
    build_costs: BuildCosts | None = None
    derived_parameters: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class RunState:
    """Per-run mutable state held in a ContextVar.

    ``inputs``      — deep copy of the caller's input dict (section stems → dicts).
    ``scenario_id`` — scenario identifier for this run.
    ``aggregator``  — the JSONOutputManager for this run (set before the module loop).
    ``run_context``  — populated by _bootstrap_run_context; None until then.
    ``derived_parameters`` — accumulated by add_derived().
    """
    inputs: dict[str, Any]
    scenario_id: str = ""
    aggregator: Any = None
    run_context: RunContext | None = None
    derived_parameters: dict[str, Any] = dc_field(default_factory=dict)


_SENTINEL = object()
_run_state_var: contextvars.ContextVar[RunState] = contextvars.ContextVar("_run_state_var")

# Attribute on RunStates created by legacy setters (set_run_context /
# set_output_manager) that ran before any explicit set_run_state().
# Not a dataclass field: RunState is unhashable, so the token cannot live in
# a WeakKeyDictionary. Cleared when both the context and the aggregator are
# gone, so get_run_state() raises again after the matching clear_* calls.
_IMPLICIT_TOKEN = "_implicit_token"


def set_run_state(state: RunState) -> contextvars.Token:
    """Set the RunState for the current context. Returns a token for reset."""
    return _run_state_var.set(state)


def get_run_state() -> RunState:
    """Return the active RunState. Raises RuntimeError if no run is active."""
    state = _run_state_var.get(_SENTINEL)
    if state is _SENTINEL:
        raise RuntimeError(
            "No active run. Call set_run_state() before accessing run state."
        )
    return state


def reset_run_state(token: contextvars.Token) -> None:
    """Reset the ContextVar to its previous value."""
    _run_state_var.reset(token)


def _ensure_run_state() -> RunState:
    """Return the active RunState, creating an implicit one if none is set.

    Current callers (``run_calculation``, tests) still call ``set_run_context``
    and ``set_output_manager`` without ``set_run_state``. Task 3 will set the
    state explicitly; until then these setters install a run so the public
    API keeps its previous behavior.
    """
    try:
        return get_run_state()
    except RuntimeError:
        state = RunState(inputs={})
        token = set_run_state(state)
        setattr(state, _IMPLICIT_TOKEN, token)
        return state


def _share_derived(state: RunState, ctx: Any) -> None:
    """Point RunState.derived_parameters at the RunContext dict.

    ``core.py`` still publishes ``RunContext.derived_parameters``. Sharing the
    dict means ``add_derived`` updates the object those readers already hold.
    """
    if ctx is None:
        return
    derived = getattr(ctx, "derived_parameters", None)
    if not isinstance(derived, dict) or derived is state.derived_parameters:
        return
    if state.derived_parameters:
        derived.update(state.derived_parameters)
    state.derived_parameters = derived


def _release_implicit_if_idle() -> None:
    """Drop an implicit RunState once context and aggregator are both clear."""
    try:
        state = get_run_state()
    except RuntimeError:
        return
    token = getattr(state, _IMPLICIT_TOKEN, None)
    if token is None:
        return
    if state.run_context is not None or state.aggregator is not None:
        return
    delattr(state, _IMPLICIT_TOKEN)
    reset_run_state(token)


# --- Accessors that read/write through RunState ---

def set_run_context(ctx: RunContext) -> None:
    """Attach the RunContext to the active RunState."""
    state = _ensure_run_state()
    state.run_context = ctx
    _share_derived(state, ctx)


def get_run_context() -> RunContext | None:
    """Return the RunContext, or None if bootstrap has not finished yet."""
    try:
        return get_run_state().run_context
    except RuntimeError:
        return None


def clear_run_context() -> None:
    """Clear the RunContext on the active RunState. No-op if no run is active."""
    try:
        get_run_state().run_context = None
    except RuntimeError:
        return
    _release_implicit_if_idle()


def set_output_manager(manager: Any) -> None:
    """Set the aggregator on the active RunState."""
    _ensure_run_state().aggregator = manager


def get_output_manager() -> Any | None:
    """Return the aggregator, or None if no run is active."""
    try:
        return get_run_state().aggregator
    except RuntimeError:
        return None


def clear_output_manager() -> None:
    """Clear the aggregator on the active RunState. No-op if no run is active."""
    try:
        get_run_state().aggregator = None
    except RuntimeError:
        return
    _release_implicit_if_idle()


def set_build_costs(costs: BuildCosts) -> None:
    """Attach build costs to the current RunContext. No-op if no context is set."""
    ctx = get_run_context()
    if ctx is not None:
        ctx.build_costs = costs


def add_derived(params: dict[str, Any]) -> None:
    """Merge derived parameters into the active RunState.

    Also updates ``RunContext.derived_parameters`` when that dict is a
    distinct object. No-op when no run is active (previous behavior).
    """
    try:
        state = get_run_state()
    except RuntimeError:
        return
    state.derived_parameters.update(params)
    ctx = state.run_context
    derived = getattr(ctx, "derived_parameters", None) if ctx is not None else None
    if isinstance(derived, dict) and derived is not state.derived_parameters:
        derived.update(params)
