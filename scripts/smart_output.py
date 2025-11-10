"""
Smart output manager that automatically selects between CSV and JSON output managers.
Based on CTCC_OUTPUT_MODE environment variable.
"""

import os
from typing import Dict, Any


class SmartOutputManager:
    """
    Wrapper that delegates to either CSVOutputManager or JSONOutputManager
    based on the CTCC_OUTPUT_MODE environment variable.

    Default: CSV mode (for backward compatibility)
    """

    def __init__(self):
        """Initialize the appropriate output manager based on environment."""
        self.output_mode = os.environ.get('CTCC_OUTPUT_MODE', 'csv').lower()
        self.script_name = None  # Will be set when write_batch_summary is called

        if self.output_mode == 'json':
            # JSON mode: Use JSONOutputManager
            from json_output_manager import JSONOutputManager
            scenario_id = os.environ.get('CTCC_SCENARIO_ID', 'default')
            self._manager = JSONOutputManager(scenario_id=scenario_id)
        else:
            # CSV mode (default): Use CTCCOutputManager
            from csv_output_manager import CTCCOutputManager
            self._manager = CTCCOutputManager()

    def write_batch_summary(self):
        """
        Write output summary.
        - CSV mode: Writes to batch_summary.csv
        - JSON mode: Saves state to JSON file for subprocess communication
        """
        if self.output_mode == 'json':
            # JSON mode: Save state to file so parent process can aggregate results
            # Get the calling script name from the stack
            import inspect
            frame = inspect.currentframe()
            caller_frame = frame.f_back
            module_name = caller_frame.f_globals.get('__name__', 'unknown')
            if module_name == '__main__':
                # Get the script filename instead
                import sys
                script_path = sys.argv[0] if sys.argv else 'unknown'
                module_name = os.path.splitext(os.path.basename(script_path))[0]

            return self._manager.save_to_file(module_name=module_name)
        else:
            # CSV mode: Write to batch_summary.csv
            return self._manager.write_batch_summary()

    def __getattr__(self, name):
        """Delegate all method calls to the underlying manager."""
        return getattr(self._manager, name)


# For backward compatibility, export as CTCCOutputManager
CTCCOutputManager = SmartOutputManager
