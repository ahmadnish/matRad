"""
Master Test Runner for Session 6
================================

This script coordinates and runs all comprehensive tests for the optimization functionality.
It provides a single entry point for validating all features implemented across Sessions 1-6.

Test Suite Components:
1. Engine Testing - Core optimization functionality
2. Agent Testing - LLM agent interface testing  
3. Performance Benchmarking - Performance validation
4. Integration Testing - End-to-end workflow testing

Usage:
    python run_all_tests.py [--fast] [--engine-only] [--agent-only] [--performance-only]
"""

import os
import sys
import time
import argparse
import json
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_engine_tests():
    """Run comprehensive engine tests."""
    print("\n🔧 RUNNING ENGINE TESTS")
    print("="*50)
    
    try:
        from test_comprehensive_optimization import main as run_engine_tests
        return run_engine_tests()
    except Exception as e:
        print(f"❌ Engine tests failed: {e}")
        return False

def run_agent_tests():
    """Run agent interface tests."""
    print("\n🤖 RUNNING AGENT TESTS")
    print("="*50)
    
    try:
        from test_agent_comprehensive import main as run_agent_tests
        return run_agent_tests()
    except Exception as e:
        print(f"❌ Agent tests failed: {e}")
        return False

def run_performance_benchmarks():
    """Run performance benchmarks."""
    print("\n⚡ RUNNING PERFORMANCE BENCHMARKS")
    print("="*50)
    
    try:
        from test_performance_benchmark import main as run_performance_tests
        return run_performance_tests()
    except Exception as e:
        print(f"❌ Performance tests failed: {e}")
        return False

def run_integration_tests():
    """Run integration tests using existing test."""
    print("\n🔗 RUNNING INTEGRATION TESTS")
    print("="*50)
    
    try:
        from test_matrad_tools import run_complete_planning_workflow
        
        print("Running complete planning workflow as integration test...")
        run_complete_planning_workflow()
        print("✅ Integration test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
        return False

def generate_test_report(results: Dict[str, bool], execution_times: Dict[str, float]):
    """Generate comprehensive test report."""
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    total_time = sum(execution_times.values())
    
    report = {
        "test_execution_summary": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_test_suites": total_tests,
            "passed_test_suites": passed_tests,
            "failed_test_suites": total_tests - passed_tests,
            "overall_success_rate": passed_tests / total_tests,
            "total_execution_time": total_time
        },
        "individual_results": {
            test_name: {
                "passed": passed,
                "execution_time": execution_times.get(test_name, 0)
            }
            for test_name, passed in results.items()
        },
        "session_validation": {
            "session_1_eud_dvh": "Tested in engine tests",
            "session_2_constraints": "Tested in engine tests", 
            "session_3_bug_fixes": "Tested in engine tests",
            "session_4_advanced_params": "Tested in engine tests",
            "session_5_comprehensive_inspection": "Tested in engine and agent tests",
            "session_6_testing_validation": "This test suite"
        }
    }
    
    # Save report
    os.makedirs("test_logs", exist_ok=True)
    with open("test_logs/master_test_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

def print_final_summary(results: Dict[str, bool], execution_times: Dict[str, float]):
    """Print comprehensive test summary."""
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    total_time = sum(execution_times.values())
    
    print("\n" + "="*80)
    print("🎯 COMPREHENSIVE TEST SUITE FINAL SUMMARY")
    print("="*80)
    
    print(f"Overall Results: {passed_tests}/{total_tests} test suites passed")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    print(f"Total Execution Time: {total_time:.1f} seconds")
    
    print("\nDetailed Results:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        time_str = f"({execution_times.get(test_name, 0):.1f}s)"
        print(f"  {status} {test_name} {time_str}")
    
    # Feature validation summary
    print("\nFeature Validation Status:")
    feature_status = {
        "EUD & DVH Objectives (Session 1)": results.get("engine_tests", False),
        "Constraint Framework (Session 2)": results.get("engine_tests", False),
        "Bug Fixes & Robustness (Session 3)": results.get("engine_tests", False), 
        "Advanced Parameters (Session 4)": results.get("engine_tests", False),
        "Comprehensive Inspection (Session 5)": results.get("agent_tests", False),
        "Agent Interface": results.get("agent_tests", False),
        "Performance": results.get("performance_tests", False),
        "Integration": results.get("integration_tests", False)
    }
    
    for feature, status in feature_status.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {feature}")
    
    # Final assessment
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 The comprehensive optimization system is fully validated and ready for production use.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed.")
        print("📋 Review the detailed results above and address any failures before deployment.")
    
    print(f"\n📁 Detailed report saved to: test_logs/master_test_report.json")

def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Run comprehensive optimization tests")
    parser.add_argument("--fast", action="store_true", help="Run faster version of tests")
    parser.add_argument("--engine-only", action="store_true", help="Run only engine tests")
    parser.add_argument("--agent-only", action="store_true", help="Run only agent tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🧪 COMPREHENSIVE OPTIMIZATION TESTING SUITE - SESSION 6")
    print("Validating all features from Sessions 1-6")
    print("="*80)
    
    start_time = time.time()
    results = {}
    execution_times = {}
    
    # Determine which tests to run
    run_all = not any([args.engine_only, args.agent_only, args.performance_only, args.integration_only])
    
    try:
        # Engine tests
        if run_all or args.engine_only:
            test_start = time.time()
            results["engine_tests"] = run_engine_tests()
            execution_times["engine_tests"] = time.time() - test_start
        
        # Agent tests
        if run_all or args.agent_only:
            test_start = time.time()
            results["agent_tests"] = run_agent_tests()
            execution_times["agent_tests"] = time.time() - test_start
        
        # Performance tests
        if run_all or args.performance_only:
            test_start = time.time()
            results["performance_tests"] = run_performance_benchmarks()
            execution_times["performance_tests"] = time.time() - test_start
        
        # Integration tests
        if run_all or args.integration_only:
            test_start = time.time()
            results["integration_tests"] = run_integration_tests()
            execution_times["integration_tests"] = time.time() - test_start
        
        # Generate report and summary
        report = generate_test_report(results, execution_times)
        print_final_summary(results, execution_times)
        
        # Return overall success
        return all(results.values()) if results else False
        
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during test execution: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
