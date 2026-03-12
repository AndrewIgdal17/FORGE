"""
Run context for in-process pipeline: shared output manager so scripts
can use a single aggregator when orchestrated by ctcc.py instead of
each writing their own file (subprocess mode).

Orchestrator sets the manager before the script loop and clears after.
Scripts get it via SmartOutputManager (no signature change).
"""

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
