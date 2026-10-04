"""Tests for RunState, ContextVar, and section() accessor."""
from __future__ import annotations

import threading

import pytest

from forge.scripts.utils.run_context import (
    RunState,
    get_run_state,
    set_run_state,
    reset_run_state,
    get_run_context,
    set_run_context,
    get_output_manager,
    set_output_manager,
    add_derived,
)
from forge.scripts.utils.inputs import section


def _make_inputs():
    return {
        "01_project_technical_details": {"project": {"capacity_mw": 500}},
        "03_financing": {"financial": {"inflation_rate": 0.02}},
    }


def test_get_run_state_raises_when_unset():
    with pytest.raises(RuntimeError, match="No active run"):
        get_run_state()


def test_set_and_get_run_state():
    inputs = _make_inputs()
    state = RunState(inputs=inputs, scenario_id="test_1")
    token = set_run_state(state)
    try:
        assert get_run_state() is state
        assert get_run_state().scenario_id == "test_1"
    finally:
        reset_run_state(token)


def test_reset_clears_state():
    state = RunState(inputs=_make_inputs(), scenario_id="test_2")
    token = set_run_state(state)
    reset_run_state(token)
    with pytest.raises(RuntimeError, match="No active run"):
        get_run_state()


def test_section_returns_named_section():
    inputs = _make_inputs()
    state = RunState(inputs=inputs, scenario_id="test_3")
    token = set_run_state(state)
    try:
        result = section("01_project_technical_details")
        assert result == {"project": {"capacity_mw": 500}}
    finally:
        reset_run_state(token)


def test_section_raises_for_unknown_name():
    state = RunState(inputs=_make_inputs(), scenario_id="test_4")
    token = set_run_state(state)
    try:
        with pytest.raises(KeyError, match="no_such_section"):
            section("no_such_section")
    finally:
        reset_run_state(token)


def test_section_raises_when_no_run():
    with pytest.raises(RuntimeError, match="No active run"):
        section("01_project_technical_details")


def test_threads_see_own_state():
    """Two threads with different RunStates see their own inputs."""
    results = {}

    def worker(name, capacity):
        inputs = {"01_project_technical_details": {"project": {"capacity_mw": capacity}}}
        state = RunState(inputs=inputs, scenario_id=name)
        token = set_run_state(state)
        try:
            s = section("01_project_technical_details")
            results[name] = s["project"]["capacity_mw"]
        finally:
            reset_run_state(token)

    t1 = threading.Thread(target=worker, args=("a", 100))
    t2 = threading.Thread(target=worker, args=("b", 999))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert results == {"a": 100, "b": 999}


def test_run_context_reads_from_run_state():
    """get_run_context() returns RunState.run_context."""
    state = RunState(inputs=_make_inputs(), scenario_id="test_ctx")
    token = set_run_state(state)
    try:
        assert get_run_context() is None  # run_context not attached yet
    finally:
        reset_run_state(token)


def test_output_manager_reads_from_run_state():
    """get_output_manager() returns RunState.aggregator."""
    sentinel = object()
    state = RunState(inputs=_make_inputs(), scenario_id="test_om", aggregator=sentinel)
    token = set_run_state(state)
    try:
        assert get_output_manager() is sentinel
    finally:
        reset_run_state(token)


def test_add_derived_writes_to_run_state():
    state = RunState(inputs=_make_inputs(), scenario_id="test_derived")
    token = set_run_state(state)
    try:
        add_derived({"foo": 42})
        assert get_run_state().derived_parameters["foo"] == 42
    finally:
        reset_run_state(token)


def test_clear_run_context_keeps_explicit_run_state():
    """clear_run_context() detaches the context and leaves an explicit RunState."""
    from forge.scripts.utils.run_context import clear_run_context

    state = RunState(inputs=_make_inputs(), scenario_id="explicit")
    token = set_run_state(state)
    try:
        set_run_context(object())
        clear_run_context()
        assert get_run_state() is state
        assert get_run_context() is None
    finally:
        reset_run_state(token)


def test_legacy_output_manager_survives_clearing_context():
    """run_calculation clears the context before the aggregator."""
    from forge.scripts.utils.run_context import clear_output_manager, clear_run_context

    sentinel_mgr = object()
    sentinel_ctx = object()
    set_output_manager(sentinel_mgr)
    set_run_context(sentinel_ctx)
    try:
        assert get_output_manager() is sentinel_mgr
        assert get_run_context() is sentinel_ctx
        clear_run_context()
        assert get_output_manager() is sentinel_mgr
        assert get_run_context() is None
    finally:
        clear_output_manager()
        clear_run_context()
    with pytest.raises(RuntimeError, match="No active run"):
        get_run_state()


def test_legacy_set_run_context_without_explicit_state():
    """Callers that have not switched to set_run_state still attach a context."""
    from forge.scripts.utils.run_context import clear_run_context

    sentinel = object()
    clear_run_context()
    try:
        set_run_context(sentinel)
        assert get_run_context() is sentinel
    finally:
        clear_run_context()
    with pytest.raises(RuntimeError, match="No active run"):
        get_run_state()


def test_add_derived_mirrors_onto_run_context():
    """Existing readers still find derived parameters on RunContext."""
    from forge.scripts.utils.run_context import RunContext, clear_run_context

    ctx = RunContext(
        project_details=None,  # type: ignore[arg-type]
        terrain_miles={},
        terrain_multipliers={},
        total_miles=0.0,
        financing=None,  # type: ignore[arg-type]
        contingencies={},
        category_string="",
        row_width_feet=0.0,
        weighted_miles=0.0,
        average_terrain_multiplier=0.0,
    )
    clear_run_context()
    try:
        set_run_context(ctx)
        add_derived({"foo": 42})
        assert ctx.derived_parameters["foo"] == 42
        assert get_run_state().derived_parameters["foo"] == 42
    finally:
        clear_run_context()
    with pytest.raises(RuntimeError, match="No active run"):
        get_run_state()
