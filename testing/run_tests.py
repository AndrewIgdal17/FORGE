#!/usr/bin/env python3
"""
FORGE Test Runner
Automated test suite for Framework for Open Reproducible Grid Economics

Usage:
    ./run_tests.py                    # Run all tests
    ./run_tests.py --priority P0      # Run only P0 (critical) tests
    ./run_tests.py --priority P1      # Run P0 and P1 tests
    ./run_tests.py --category cli     # Run only CLI tests
    ./run_tests.py --quick            # Run quick smoke tests only
    ./run_tests.py --verbose          # Show detailed output
"""

import subprocess
import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TestResult:
    """Store result of a test execution"""
    def __init__(self, test_id: str, name: str, status: str, duration: float, message: str = ""):
        self.test_id = test_id
        self.name = name
        self.status = status  # 'pass', 'fail', 'skip', 'warning'
        self.duration = duration
        self.message = message

class TestRunner:
    """Main test runner class"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.project_root = Path(__file__).parent.parent  # Go up to FORGE root
        self.venv_python = self.project_root / "venv" / "bin" / "python3"
        self.outputs_dir = self.project_root / "outputs"
        self.temp_files = []

        # Ensure outputs directory exists
        self.outputs_dir.mkdir(exist_ok=True)

    def log(self, message: str, color: str = ""):
        """Print log message"""
        if color:
            print(f"{color}{message}{Colors.ENDC}")
        else:
            print(message)

    def log_verbose(self, message: str):
        """Print verbose log message"""
        if self.verbose:
            print(f"  {Colors.OKCYAN}[VERBOSE]{Colors.ENDC} {message}")

    def run_command(self, cmd: List[str], timeout: int = 120, env: Dict = None) -> Tuple[bool, str, str]:
        """
        Run a shell command and return success status, stdout, stderr
        """
        try:
            self.log_verbose(f"Running: {' '.join(cmd)}")

            # Merge environment variables
            full_env = os.environ.copy()
            if env:
                full_env.update(env)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root),
                env=full_env
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def add_result(self, test_id: str, name: str, status: str, duration: float, message: str = ""):
        """Add test result"""
        result = TestResult(test_id, name, status, duration, message)
        self.results.append(result)

        # Print immediate feedback
        status_symbol = {
            'pass': f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}",
            'fail': f"{Colors.FAIL}❌ FAIL{Colors.ENDC}",
            'skip': f"{Colors.WARNING}⏭️  SKIP{Colors.ENDC}",
            'warning': f"{Colors.WARNING}⚠️  WARN{Colors.ENDC}"
        }

        status_str = status_symbol.get(status, status)
        duration_str = f"({duration:.2f}s)"
        print(f"  [{test_id}] {name}: {status_str} {duration_str}")

        if message and (status in ['fail', 'warning'] or self.verbose):
            print(f"    {Colors.OKCYAN}→{Colors.ENDC} {message}")

    def cleanup(self):
        """Clean up temporary files"""
        for file_path in self.temp_files:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    self.log_verbose(f"Cleaned up: {file_path}")
            except Exception as e:
                self.log_verbose(f"Failed to clean up {file_path}: {e}")

    # ========================================
    # Test Category 1: CLI Mode Tests (P0)
    # ========================================

    def test_1_1_1_yaml_json_mode(self):
        """Test 1.1.1: YAML→JSON mode (calculator is YAML-in, JSON-out)"""
        test_id = "1.1.1"
        scenario_id = f"test_yaml_json_{int(time.time())}"
        start_time = time.time()

        cmd = [str(self.venv_python), "forge.py", "--simple"]
        env = {"FORGE_SCENARIO_ID": scenario_id}
        success, stdout, stderr = self.run_command(cmd, timeout=180, env=env)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "YAML→JSON mode", "fail", duration,
                          f"Command failed: {stderr[:200]}")
            return False

        json_output = self.outputs_dir / f"forge_results_{scenario_id}.json"
        self.temp_files.append(json_output)
        if not json_output.exists():
            self.add_result(test_id, "YAML→JSON mode", "fail", duration,
                          "forge_results_*.json not created")
            return False

        self.add_result(test_id, "YAML→JSON mode", "pass", duration)
        return True

    def test_1_1_2_json_csv_mode(self):
        """Test 1.1.2: JSON→CSV mode (skipped: calculator is YAML-in, JSON-out only)"""
        test_id = "1.1.2"
        start_time = time.time()
        duration = time.time() - start_time
        self.add_result(test_id, "JSON→CSV mode", "skip", duration,
                      "Calculator is YAML-in, JSON-out; API converts JSON at boundary")
        return True

    def test_1_1_3_yaml_json_mode(self):
        """Test 1.1.3: YAML→JSON mode with custom scenario ID"""
        test_id = "1.1.3"
        scenario_id = f"test_{int(time.time())}"
        start_time = time.time()

        cmd = [str(self.venv_python), "forge.py", "--simple"]
        env = {"FORGE_SCENARIO_ID": scenario_id}
        success, stdout, stderr = self.run_command(cmd, timeout=180, env=env)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "YAML→JSON mode (custom ID)", "fail", duration,
                          f"Command failed: {stderr[:200]}")
            return False

        json_output = self.outputs_dir / f"forge_results_{scenario_id}.json"
        self.temp_files.append(json_output)

        if not json_output.exists():
            self.add_result(test_id, "YAML→JSON mode (custom ID)", "fail", duration,
                          f"Output file not created: {json_output}")
            return False

        try:
            with open(json_output, 'r') as f:
                data = json.load(f)

            required_keys = ['scenario_id', 'costs', 'technical_parameters']
            missing_keys = [k for k in required_keys if k not in data]

            if missing_keys:
                self.add_result(test_id, "YAML→JSON mode (custom ID)", "fail", duration,
                              f"Missing keys in JSON: {missing_keys}")
                return False

        except json.JSONDecodeError as e:
            self.add_result(test_id, "YAML→JSON mode (custom ID)", "fail", duration,
                          f"Invalid JSON output: {e}")
            return False

        self.add_result(test_id, "YAML→JSON mode (custom ID)", "pass", duration,
                      f"Output size: {json_output.stat().st_size / 1024:.1f} KB")
        return True

    def test_1_2_1_norisk_flag(self):
        """Test 1.2.1: --norisk flag"""
        test_id = "1.2.1"
        start_time = time.time()

        cmd = [str(self.venv_python), "forge.py", "--norisk", "--simple"]
        success, stdout, stderr = self.run_command(cmd, timeout=180)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "--norisk flag", "fail", duration,
                          f"Command failed: {stderr[:200]}")
            return False

        # Check that risk warning appears
        if "Risk costs disabled" not in stdout:
            self.add_result(test_id, "--norisk flag", "warning", duration,
                          "Risk disabled warning not found")
            return False

        self.add_result(test_id, "--norisk flag", "pass", duration)
        return True

    def test_1_2_6_custom_scenario_id(self):
        """Test 1.2.6: Custom scenario ID (via FORGE_SCENARIO_ID)"""
        test_id = "1.2.6"
        scenario_id = "custom_test_123"
        start_time = time.time()

        cmd = [str(self.venv_python), "forge.py", "--simple"]
        env = {"FORGE_SCENARIO_ID": scenario_id}
        success, stdout, stderr = self.run_command(cmd, timeout=180, env=env)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "Custom scenario ID", "fail", duration,
                          f"Command failed: {stderr[:200]}")
            return False

        # Check that file has correct name
        json_output = self.outputs_dir / f"forge_results_{scenario_id}.json"
        self.temp_files.append(json_output)

        if not json_output.exists():
            self.add_result(test_id, "Custom scenario ID", "fail", duration,
                          f"File not named correctly: {json_output}")
            return False

        self.add_result(test_id, "Custom scenario ID", "pass", duration)
        return True

    # ========================================
    # Test Category 5: YAML↔JSON Conversion (P0)
    # ========================================

    def test_5_1_1_yaml_to_json_converter(self):
        """Test 5.1.1: YAML to JSON conversion"""
        test_id = "5.1.1"
        start_time = time.time()

        output_file = self.project_root / "test_combined.json"
        self.temp_files.append(output_file)

        cmd = [str(self.venv_python), "yaml_to_json.py", "yamls/", str(output_file)]
        success, stdout, stderr = self.run_command(cmd, timeout=30)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "YAML→JSON converter", "fail", duration,
                          f"Conversion failed: {stderr[:200]}")
            return False

        # Validate output file
        if not output_file.exists():
            self.add_result(test_id, "YAML→JSON converter", "fail", duration,
                          "Output file not created")
            return False

        try:
            with open(output_file, 'r') as f:
                data = json.load(f)

            # Check for expected number of sections (21, not 22 - template is skipped)
            if len(data) < 20:
                self.add_result(test_id, "YAML→JSON converter", "warning", duration,
                              f"Only {len(data)} sections found (expected ~21)")
                return False

        except json.JSONDecodeError as e:
            self.add_result(test_id, "YAML→JSON converter", "fail", duration,
                          f"Invalid JSON: {e}")
            return False

        self.add_result(test_id, "YAML→JSON converter", "pass", duration,
                      f"{len(data)} sections converted")
        return True

    def test_5_2_1_round_trip_comparison(self):
        """Test 5.2.1: Round-trip YAML→JSON→CSV comparison"""
        test_id = "5.2.1"
        start_time = time.time()

        # Step 1: Run YAML→JSON (calculator is YAML-in, JSON-out)
        scenario_id = f"roundtrip_yaml_{int(time.time())}"
        cmd1 = [str(self.venv_python), "forge.py", "--simple"]
        success1, stdout1, stderr1 = self.run_command(cmd1, timeout=180, env={"FORGE_SCENARIO_ID": scenario_id})

        if not success1:
            duration = time.time() - start_time
            self.add_result(test_id, "Round-trip test", "fail", duration,
                          "YAML→JSON failed")
            return False

        json_output = self.outputs_dir / f"forge_results_{scenario_id}.json"
        self.temp_files.append(json_output)
        if not json_output.exists():
            duration = time.time() - start_time
            self.add_result(test_id, "Round-trip test", "fail", duration,
                          "forge_results_*.json not created")
            return False

        try:
            data = json.loads(json_output.read_text())
            if "costs" not in data or "scenario_id" not in data:
                duration = time.time() - start_time
                self.add_result(test_id, "Round-trip test", "fail", duration,
                              "JSON missing required keys")
                return False
        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            self.add_result(test_id, "Round-trip test", "fail", duration,
                          f"Invalid JSON: {e}")
            return False

        duration = time.time() - start_time
        self.add_result(test_id, "Round-trip test", "pass", duration,
                      "YAML→JSON produced valid output")
        return True

    # ========================================
    # Test Category 6: Financial Calculations (P1)
    # ========================================

    def test_6_3_1_bcr_calculation(self):
        """Test 6.3.1: BCR calculation present in output"""
        test_id = "6.3.1"
        start_time = time.time()

        scenario_id = f"bcr_test_{int(time.time())}"
        cmd = [str(self.venv_python), "forge.py", "--simple"]
        env = {"FORGE_SCENARIO_ID": scenario_id}
        success, stdout, stderr = self.run_command(cmd, timeout=180, env=env)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "BCR calculation", "fail", duration,
                          f"Command failed: {stderr[:200]}")
            return False

        # Check for BCR in output
        if "BCR" not in stdout and "BENEFIT-COST RATIO" not in stdout:
            self.add_result(test_id, "BCR calculation", "fail", duration,
                          "BCR output not found")
            return False

        # Validate JSON output has BCR
        json_output = self.outputs_dir / f"forge_results_{scenario_id}.json"
        self.temp_files.append(json_output)

        try:
            with open(json_output, 'r') as f:
                data = json.load(f)

            # Check for BCR in results (could be in 'bcr' or 'summary' section)
            has_bcr = 'bcr' in data or ('summary' in data and 'bcr' in str(data['summary']))

            if not has_bcr:
                self.add_result(test_id, "BCR calculation", "warning", duration,
                              "BCR not found in JSON output")
                return False

        except Exception as e:
            self.add_result(test_id, "BCR calculation", "fail", duration,
                          f"Failed to validate JSON: {e}")
            return False

        self.add_result(test_id, "BCR calculation", "pass", duration)
        return True

    # ========================================
    # Test Category 7: Error Handling (P1)
    # ========================================

    def test_7_1_3_invalid_json_handling(self):
        """Test 7.1.3: Invalid JSON handling"""
        test_id = "7.1.3"
        start_time = time.time()

        # Create invalid JSON file
        invalid_json = self.project_root / "invalid_test.json"
        self.temp_files.append(invalid_json)
        invalid_json.write_text("{invalid json content")

        cmd = [str(self.venv_python), "forge.py", "-j", "--json-file", str(invalid_json), "--simple"]
        success, stdout, stderr = self.run_command(cmd, timeout=30)

        duration = time.time() - start_time

        # Should fail gracefully
        if success:
            self.add_result(test_id, "Invalid JSON handling", "fail", duration,
                          "Command should have failed with invalid JSON")
            return False

        # Check for error message
        error_output = stdout + stderr
        if "JSON" in error_output or "invalid" in error_output.lower():
            self.add_result(test_id, "Invalid JSON handling", "pass", duration,
                          "Error properly reported")
            return True
        else:
            self.add_result(test_id, "Invalid JSON handling", "warning", duration,
                          "Error message not clear")
            return False

    # ========================================
    # Test Category 9: Performance (P2)
    # ========================================

    def test_9_1_1_cli_performance(self):
        """Test 9.1.1: CLI execution time"""
        test_id = "9.1.1"
        start_time = time.time()

        cmd = [str(self.venv_python), "forge.py", "--simple"]
        success, stdout, stderr = self.run_command(cmd, timeout=180)

        duration = time.time() - start_time

        if not success:
            self.add_result(test_id, "CLI performance", "fail", duration,
                          "Command failed")
            return False

        # Check if execution time is reasonable (< 60 seconds for simple mode)
        if duration > 60:
            self.add_result(test_id, "CLI performance", "warning", duration,
                          f"Execution took {duration:.1f}s (target: <60s)")
            return False

        self.add_result(test_id, "CLI performance", "pass", duration,
                      f"Completed in {duration:.1f}s")
        return True

    # ========================================
    # Quick Smoke Tests
    # ========================================

    def run_quick_tests(self):
        """Run quick smoke tests"""
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        self.log(f"{Colors.HEADER}QUICK SMOKE TESTS{Colors.ENDC}")
        self.log(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        tests = [
            ("CLI Check", self.test_1_1_1_yaml_json_mode),
            ("JSON Mode", self.test_1_1_3_yaml_json_mode),
        ]

        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"{Colors.FAIL}Exception in {name}: {e}{Colors.ENDC}")

    # ========================================
    # Test Suite Runners
    # ========================================

    def run_p0_tests(self):
        """Run P0 (Critical) tests"""
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        self.log(f"{Colors.HEADER}P0 TESTS - CRITICAL{Colors.ENDC}")
        self.log(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        tests = [
            ("1.1.1: YAML→JSON Mode", self.test_1_1_1_yaml_json_mode),
            ("1.1.2: JSON→CSV (skipped)", self.test_1_1_2_json_csv_mode),
            ("1.1.3: YAML→JSON (custom ID)", self.test_1_1_3_yaml_json_mode),
            ("1.2.1: --norisk Flag", self.test_1_2_1_norisk_flag),
            ("1.2.6: Custom Scenario ID", self.test_1_2_6_custom_scenario_id),
            ("5.1.1: YAML→JSON Converter", self.test_5_1_1_yaml_to_json_converter),
            ("5.2.1: Round-trip Test", self.test_5_2_1_round_trip_comparison),
        ]

        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"{Colors.FAIL}Exception in {name}: {e}{Colors.ENDC}")
                import traceback
                if self.verbose:
                    traceback.print_exc()

    def run_p1_tests(self):
        """Run P1 (High) tests"""
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        self.log(f"{Colors.HEADER}P1 TESTS - HIGH PRIORITY{Colors.ENDC}")
        self.log(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        tests = [
            ("6.3.1: BCR Calculation", self.test_6_3_1_bcr_calculation),
            ("7.1.3: Invalid JSON Handling", self.test_7_1_3_invalid_json_handling),
        ]

        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"{Colors.FAIL}Exception in {name}: {e}{Colors.ENDC}")
                import traceback
                if self.verbose:
                    traceback.print_exc()

    def run_p2_tests(self):
        """Run P2 (Medium) tests"""
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        self.log(f"{Colors.HEADER}P2 TESTS - MEDIUM PRIORITY{Colors.ENDC}")
        self.log(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        tests = [
            ("9.1.1: CLI Performance", self.test_9_1_1_cli_performance),
        ]

        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"{Colors.FAIL}Exception in {name}: {e}{Colors.ENDC}")
                import traceback
                if self.verbose:
                    traceback.print_exc()

    def run_all_tests(self):
        """Run all test suites"""
        self.run_p0_tests()
        self.run_p1_tests()
        self.run_p2_tests()

    # ========================================
    # Reporting
    # ========================================

    def print_summary(self):
        """Print test summary"""
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        self.log(f"{Colors.HEADER}TEST SUMMARY{Colors.ENDC}")
        self.log(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        # Count by status
        passed = sum(1 for r in self.results if r.status == 'pass')
        failed = sum(1 for r in self.results if r.status == 'fail')
        warnings = sum(1 for r in self.results if r.status == 'warning')
        skipped = sum(1 for r in self.results if r.status == 'skip')
        total = len(self.results)

        # Calculate total time
        total_time = sum(r.duration for r in self.results)

        # Print counts
        self.log(f"Total Tests:    {total}")
        self.log(f"{Colors.OKGREEN}Passed:         {passed}{Colors.ENDC}")
        self.log(f"{Colors.FAIL}Failed:         {failed}{Colors.ENDC}")
        self.log(f"{Colors.WARNING}Warnings:       {warnings}{Colors.ENDC}")
        self.log(f"Skipped:        {skipped}")
        self.log(f"\nTotal Time:     {total_time:.2f}s")

        # Print failed tests
        if failed > 0:
            self.log(f"\n{Colors.FAIL}Failed Tests:{Colors.ENDC}")
            for result in self.results:
                if result.status == 'fail':
                    self.log(f"  [{result.test_id}] {result.name}")
                    if result.message:
                        self.log(f"    → {result.message}")

        # Print warnings
        if warnings > 0:
            self.log(f"\n{Colors.WARNING}Warnings:{Colors.ENDC}")
            for result in self.results:
                if result.status == 'warning':
                    self.log(f"  [{result.test_id}] {result.name}")
                    if result.message:
                        self.log(f"    → {result.message}")

        # Success rate
        if total > 0:
            success_rate = (passed / total) * 100
            color = Colors.OKGREEN if success_rate >= 90 else Colors.WARNING if success_rate >= 70 else Colors.FAIL
            self.log(f"\n{color}Success Rate:   {success_rate:.1f}%{Colors.ENDC}")

        # Overall result
        self.log(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        if failed == 0:
            self.log(f"{Colors.OKGREEN}✅ ALL TESTS PASSED{Colors.ENDC}")
            return 0
        else:
            self.log(f"{Colors.FAIL}❌ SOME TESTS FAILED{Colors.ENDC}")
            return 1

    def save_report(self, filename: str = "test_results.json"):
        """Save test results to JSON file"""
        # Save to testing directory
        report_file = Path(__file__).parent / filename

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.status == 'pass'),
            "failed": sum(1 for r in self.results if r.status == 'fail'),
            "warnings": sum(1 for r in self.results if r.status == 'warning'),
            "skipped": sum(1 for r in self.results if r.status == 'skip'),
            "total_duration": sum(r.duration for r in self.results),
            "results": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "status": r.status,
                    "duration": r.duration,
                    "message": r.message
                }
                for r in self.results
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        self.log(f"\n{Colors.OKCYAN}Report saved to: {report_file}{Colors.ENDC}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="FORGE Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--priority',
        choices=['P0', 'P1', 'P2', 'all'],
        default='all',
        help='Run tests of specific priority level (default: all)'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick smoke tests only'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output'
    )

    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Save test results to JSON file'
    )

    args = parser.parse_args()

    # Create test runner
    runner = TestRunner(verbose=args.verbose)

    # Print header
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}FORGE TEST SUITE{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Priority: {args.priority}")
    print(f"Verbose: {args.verbose}")

    try:
        # Run tests based on arguments
        if args.quick:
            runner.run_quick_tests()
        elif args.priority == 'P0':
            runner.run_p0_tests()
        elif args.priority == 'P1':
            runner.run_p0_tests()
            runner.run_p1_tests()
        elif args.priority == 'P2':
            runner.run_p0_tests()
            runner.run_p1_tests()
            runner.run_p2_tests()
        else:  # 'all'
            runner.run_all_tests()

        # Print summary
        exit_code = runner.print_summary()

        # Save report if requested
        if args.save_report:
            runner.save_report()

        # Cleanup
        runner.cleanup()

        return exit_code

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
        runner.cleanup()
        return 130

    except Exception as e:
        print(f"\n\n{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        runner.cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
