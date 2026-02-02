#!/usr/bin/env python3
"""
Automated Test Suite Runner
Runs different test configurations based on requirements
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path
import time
from typing import List, Dict

class TestSuiteRunner:
    """Runner for different test configurations"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.test_dir = self.base_dir / "tests"
        
    def run_tests(self, test_type: str = "all", coverage: bool = True, 
                  verbose: bool = True, fail_fast: bool = False) -> int:
        """
        Run tests with specified configuration
        
        Args:
            test_type: Type of tests to run (unit, integration, e2e, all, fast)
            coverage: Whether to generate coverage report
            verbose: Verbose output
            fail_fast: Stop on first failure
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        print(f"🧪 Running {test_type} tests...")
        print(f"📂 Test directory: {self.test_dir}")
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Add test selection
        if test_type == "unit":
            cmd.extend(["-m", "unit"])
        elif test_type == "integration":
            cmd.extend(["-m", "integration"])
        elif test_type == "e2e":
            cmd.extend(["-m", "e2e"])
        elif test_type == "fast":
            cmd.extend(["-m", "not slow"])
        elif test_type == "privacy":
            cmd.extend(["-m", "privacy"])
        elif test_type == "retrieval":
            cmd.extend(["-m", "retrieval"])
        
        # Add options
        if verbose:
            cmd.append("-v")
        if coverage:
            cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term-missing"])
        if fail_fast:
            cmd.append("--exitfirst")
        
        # Add test directory
        cmd.append(str(self.test_dir))
        
        print(f"🚀 Command: {' '.join(cmd)}")
        print("-" * 50)
        
        # Run tests
        start_time = time.time()
        try:
            result = subprocess.run(cmd, cwd=self.base_dir, capture_output=False)
            execution_time = time.time() - start_time
            
            print("-" * 50)
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            print(f"📊 Exit code: {result.returncode}")
            
            return result.returncode
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Test execution failed: {e}")
            return e.returncode
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            return 1
    
    def run_test_matrix(self) -> Dict[str, int]:
        """Run comprehensive test matrix"""
        test_configs = [
            ("unit", "Unit Tests"),
            ("integration", "Integration Tests"),
            ("fast", "Fast Tests"),
            ("privacy", "Privacy Tests"),
            ("retrieval", "Retrieval Tests")
        ]
        
        results = {}
        
        print("🔬 Running Comprehensive Test Matrix")
        print("=" * 60)
        
        for test_type, description in test_configs:
            print(f"\n📋 {description} ({test_type})")
            print("-" * 40)
            
            exit_code = self.run_tests(
                test_type=test_type,
                coverage=False,  # Skip coverage for faster runs
                verbose=True
            )
            
            results[test_type] = exit_code
            status = "✅ PASS" if exit_code == 0 else "❌ FAIL"
            print(f"{status} - {description}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST MATRIX SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for code in results.values() if code == 0)
        total = len(results)
        
        for test_type, exit_code in results.items():
            status = "PASS" if exit_code == 0 else "FAIL"
            print(f"{test_type:12} : {status}")
        
        print("-" * 60)
        print(f"Total: {passed}/{total} test suites passed")
        
        if passed == total:
            print("🎉 All test suites passed!")
            return 0
        else:
            print("⚠️  Some test suites failed")
            return 1
    
    def run_ci_tests(self) -> int:
        """Run CI-friendly test suite"""
        print("🚀 Running CI Test Suite")
        print("=" * 40)
        
        # Run fast tests with coverage
        return self.run_tests(
            test_type="fast",
            coverage=True,
            verbose=True,
            fail_fast=True
        )
    
    def run_development_tests(self) -> int:
        """Run development-friendly test suite"""
        print("💻 Running Development Test Suite")
        print("=" * 40)
        
        # Run unit tests with coverage, then integration tests
        unit_result = self.run_tests(
            test_type="unit",
            coverage=True,
            verbose=True
        )
        
        if unit_result != 0:
            print("❌ Unit tests failed, skipping integration tests")
            return unit_result
        
        integration_result = self.run_tests(
            test_type="integration",
            coverage=False,
            verbose=True
        )
        
        return unit_result if unit_result != 0 else integration_result

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG Platform Test Suite Runner")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "e2e", "fast", "privacy", "retrieval", "matrix", "ci", "dev"],
        default="dev",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage report generation"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    runner = TestSuiteRunner()
    
    # Map argument to method
    run_methods = {
        "matrix": runner.run_test_matrix,
        "ci": runner.run_ci_tests,
        "dev": runner.run_development_tests,
        "all": lambda: runner.run_tests("all", not args.no_coverage, not args.quiet, args.fail_fast),
        "unit": lambda: runner.run_tests("unit", not args.no_coverage, not args.quiet, args.fail_fast),
        "integration": lambda: runner.run_tests("integration", not args.no_coverage, not args.quiet, args.fail_fast),
        "e2e": lambda: runner.run_tests("e2e", not args.no_coverage, not args.quiet, args.fail_fast),
        "fast": lambda: runner.run_tests("fast", not args.no_coverage, not args.quiet, args.fail_fast),
        "privacy": lambda: runner.run_tests("privacy", not args.no_coverage, not args.quiet, args.fail_fast),
        "retrieval": lambda: runner.run_tests("retrieval", not args.no_coverage, not args.quiet, args.fail_fast)
    }
    
    # Run selected test suite
    exit_code = run_methods[args.type]()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()