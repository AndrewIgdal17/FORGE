"""
Smart output manager: always uses JSON output (YAML in, JSON out).
When run in-process, the orchestrator sets a shared output manager via run_context;
SmartOutputManager then uses that instead of creating its own (no per-script files).
"""

import os
from typing import Dict, Any

try:
    from run_context import get_output_manager
except ImportError:
    def get_output_manager():
        return None


class SmartOutputManager:
    """
    Wrapper that delegates to JSONOutputManager. When a shared manager is set
    (in-process pipeline), uses that instead.
    """

    def __init__(self):
        """Initialize: use shared output manager if set, else JSONOutputManager."""
        self.output_mode = "json"
        self.script_name = None
        self._using_shared = False

        shared = get_output_manager()
        if shared is not None:
            self._manager = shared
            self._using_shared = True
            return

        from json_output_manager import JSONOutputManager
        scenario_id = os.environ.get('FORGE_SCENARIO_ID', 'default')
        self._manager = JSONOutputManager(scenario_id=scenario_id)

    def write_batch_summary(self):
        """
        Write output: in-process uses shared aggregator (no-op here); otherwise save to JSON file.
        """
        if self._using_shared:
            return None
        import inspect
        import sys
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        module_name = caller_frame.f_globals.get('__name__', 'unknown')
        if module_name == '__main__':
            script_path = sys.argv[0] if sys.argv else 'unknown'
            module_name = os.path.splitext(os.path.basename(script_path))[0]
        return self._manager.save_to_file(module_name=module_name)

    def __getattr__(self, name):
        """Delegate all method calls to the underlying manager."""
        return getattr(self._manager, name)


# For backward compatibility, export as FORGEOutputManager
FORGEOutputManager = SmartOutputManager
