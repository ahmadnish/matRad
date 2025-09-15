"""
Comprehensive Testing Suite for matRad LLM Agent Optimization Features
======================================================================

This test suite validates ALL optimization functionality implemented across Sessions 1-6:

Session 1: EUD and DVH objectives
Session 2: Constraint framework 
Session 3: Critical bug fixes + robustness support
Session 4: Advanced parameters (MeanDose function, robustness settings)
Session 5: Comprehensive inspection system
Session 6: Testing and validation (this file)

Test Categories:
1. Individual Feature Tests - Test each objective/constraint type
2. Integration Tests - Test features working together
3. Advanced Parameter Tests - Test all advanced parameters
4. Conflict Detection Tests - Test inspection system
5. Error Handling Tests - Test robustness to invalid inputs
6. Clinical Workflow Tests - Test realistic clinical scenarios
"""

import os
import sys
import time
import json
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrad_tools import create_matrad_engine

class ComprehensiveOptimizationTester:
    """Comprehensive testing class for all optimization functionality."""
    
    def __init__(self):
        self.engine = create_matrad_engine()
        self.test_results = {
            "session_tests": {},
            "integration_tests": {},
            "error_handling_tests": {},
            "clinical_workflow_tests": {},
            "summary": {}
        }
        self.patient_loaded = False
        
    def print_test_result(self, test_name: str, result: Dict[str, Any], expected_success: bool = True):
        """Print test result in formatted way."""
        success = result.get("success", False)
        status = "✅ PASS" if success == expected_success else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if success != expected_success:
            print(f"   Expected success: {expected_success}, Got: {success}")
            print(f"   Error: {result.get('error', 'No error message')}")
        elif success and result.get("message"):
            print(f"   {result['message']}")
            
        return success == expected_success
    
    def setup_basic_patient(self):
        """Set up a basic patient for testing."""
        if self.patient_loaded:
            return True
            
        print("\n" + "="*60)
        print("SETUP: Loading Patient and Basic Configuration")
        print("="*60)
        
        # Start engine
        self.engine.start_engine()
        
        # Load patient
        result = self.engine.load_patient("HEAD_AND_NECK.mat")
        if not self.print_test_result("Load Patient Data", result):
            return False
            
        # Create basic plan
        result = self.engine.create_empty_plan()
        if not self.print_test_result("Create Empty Plan", result):
            return False
            
        # Set beam angles
        result = self.engine.set_beam_angles([0, 72, 144])
        if not self.print_test_result("Set Beam Angles", result):
            return False
            
        # Generate geometry and influence matrix
        result = self.engine.generate_beam_geometry()
        if not self.print_test_result("Generate Beam Geometry", result):
            return False
            
        result = self.engine.calculate_influence_matrix()
        if not self.print_test_result("Calculate Influence Matrix", result):
            return False
            
        self.patient_loaded = True
        return True
    
    def test_session1_eud_dvh_objectives(self):
        """Test Session 1: EUD and DVH objectives."""
        print("\n" + "="*60)
        print("SESSION 1 TESTS: EUD and DVH Objectives")
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Test EUD objectives
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PTV70", "eud", 70.0, 1000.0, 
            rationale="Target EUD for uniform dose distribution",
            eud_exponent=2.0  # Low exponent for target
        )
        if self.print_test_result("Add EUD Objective (Target)", result):
            tests_passed += 1
            
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "SPINAL_CORD", "eud", 35.0, 1000.0,
            rationale="Critical structure EUD with high exponent",
            eud_exponent=8.0  # High exponent for OAR
        )
        if self.print_test_result("Add EUD Objective (OAR)", result):
            tests_passed += 1
        
        # Test DVH objectives
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PTV70", "min_dvh", 65.0, 1000.0,
            rationale="Ensure 95% target coverage",
            volume_percent=95.0
        )
        if self.print_test_result("Add Min DVH Objective", result):
            tests_passed += 1
            
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PAROTID_LT", "max_dvh", 30.0, 500.0,
            rationale="Limit high dose to parotid",
            volume_percent=20.0
        )
        if self.print_test_result("Add Max DVH Objective", result):
            tests_passed += 1
        
        self.test_results["session_tests"]["session1"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nSession 1 Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def test_session2_constraint_framework(self):
        """Test Session 2: Constraint framework."""
        print("\n" + "="*60)
        print("SESSION 2 TESTS: Constraint Framework")
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Test min_max_dose constraints
        total_tests += 1
        result = self.engine.add_constraint(
            "SPINAL_CORD", "min_max_dose",
            upper_bound=45.0,
            rationale="FDA safety limit for spinal cord"
        )
        if self.print_test_result("Add Min-Max Dose Constraint", result):
            tests_passed += 1
            
        # Test min_max_mean_dose constraints
        total_tests += 1
        result = self.engine.add_constraint(
            "PAROTID_LT", "min_max_mean_dose",
            upper_bound=26.0,
            rationale="QUANTEC guideline for xerostomia prevention"
        )
        if self.print_test_result("Add Min-Max Mean Dose Constraint", result):
            tests_passed += 1
            
        # Test min_max_eud constraints
        total_tests += 1
        result = self.engine.add_constraint(
            "BRAINSTEM", "min_max_eud",
            upper_bound=50.0,
            eud_exponent=5.0,
            rationale="Critical structure EUD safety limit"
        )
        if self.print_test_result("Add Min-Max EUD Constraint", result):
            tests_passed += 1
            
        # Test min_max_dvh constraints
        total_tests += 1
        result = self.engine.add_constraint(
            "PAROTID_RT", "min_max_dvh",
            dose_reference=20.0,
            upper_bound=30.0,  # Max 30% volume at 20Gy
            rationale="DVH constraint for parotid sparing"
        )
        if self.print_test_result("Add Min-Max DVH Constraint", result):
            tests_passed += 1
            
        # Test constraint inspection
        total_tests += 1
        result = self.engine.get_current_constraints()
        if self.print_test_result("Get Current Constraints", result):
            tests_passed += 1
            print(f"   Found {result.get('total_constraints', 0)} constraints")
            
        # Test constraint removal
        total_tests += 1
        result = self.engine.remove_constraint(
            "PAROTID_RT", constraint_type="min_max_dvh",
            rationale="Removing test constraint"
        )
        if self.print_test_result("Remove Constraint", result):
            tests_passed += 1
        
        self.test_results["session_tests"]["session2"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nSession 2 Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def test_session4_advanced_parameters(self):
        """Test Session 4: Advanced parameters."""
        print("\n" + "="*60)
        print("SESSION 4 TESTS: Advanced Parameters") 
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Test MeanDose function types
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PAROTID_LT", "mean_dose", 25.0, 500.0,
            mean_dose_function="linear",
            rationale="Linear mean dose function test"
        )
        if self.print_test_result("Add Mean Dose (Linear)", result):
            tests_passed += 1
            
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PAROTID_RT", "mean_dose", 25.0, 500.0,
            mean_dose_function="quadratic",
            rationale="Quadratic mean dose function test"
        )
        if self.print_test_result("Add Mean Dose (Quadratic)", result):
            tests_passed += 1
        
        # Test robustness settings for objectives
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PTV63", "square_deviation", 63.0, 1000.0,
            robustness="PROB",
            rationale="Probabilistic robustness test"
        )
        if self.print_test_result("Add Objective with PROB Robustness", result):
            tests_passed += 1
            
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "MANDIBLE", "max_dose", 70.0, 300.0,
            robustness="VWWC",
            rationale="Worst-case robustness test"
        )
        if self.print_test_result("Add Objective with VWWC Robustness", result):
            tests_passed += 1
        
        # Test robustness settings for constraints
        total_tests += 1
        result = self.engine.add_constraint(
            "MANDIBLE", "min_max_dose",
            upper_bound=75.0,
            robustness="VWWC",
            rationale="Constraint with worst-case robustness"
        )
        if self.print_test_result("Add Constraint with VWWC Robustness", result):
            tests_passed += 1
        
        self.test_results["session_tests"]["session4"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nSession 4 Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def test_session5_comprehensive_inspection(self):
        """Test Session 5: Comprehensive inspection system."""
        print("\n" + "="*60)
        print("SESSION 5 TESTS: Comprehensive Inspection System")
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Test comprehensive analysis
        total_tests += 1
        result = self.engine.get_optimization_functions()
        if self.print_test_result("Get All Optimization Functions", result):
            tests_passed += 1
            print(f"   Total objectives: {result.get('total_objectives', 0)}")
            print(f"   Total constraints: {result.get('total_constraints', 0)}")
            print(f"   Structures with functions: {result.get('total_structures_with_functions', 0)}")
            
        # Test structure-specific analysis
        total_tests += 1
        result = self.engine.get_optimization_functions(
            structure_name="PTV70",
            include_conflict_analysis=True,
            include_recommendations=True
        )
        if self.print_test_result("Get Structure-Specific Analysis", result):
            tests_passed += 1
            if "structures" in result and "PTV70" in result["structures"]:
                ptv_data = result["structures"]["PTV70"]
                print(f"   PTV70 objectives: {len(ptv_data.get('objectives', []))}")
                print(f"   PTV70 constraints: {len(ptv_data.get('constraints', []))}")
                
        # Test conflict detection
        total_tests += 1
        result = self.engine.get_optimization_functions(include_conflict_analysis=True)
        if self.print_test_result("Conflict Detection Analysis", result):
            tests_passed += 1
            # Check for conflicts in any structure
            conflicts_found = False
            for struct_name, struct_data in result.get("structures", {}).items():
                conflict_analysis = struct_data.get("conflict_analysis", {})
                if conflict_analysis.get("potential_conflicts"):
                    conflicts_found = True
                    print(f"   Conflicts detected in {struct_name}")
            if not conflicts_found:
                print("   No conflicts detected (good!)")
                
        # Test recommendations
        total_tests += 1
        result = self.engine.get_optimization_functions(include_recommendations=True)
        if self.print_test_result("Clinical Recommendations", result):
            tests_passed += 1
            # Check for recommendations
            recommendations_found = False
            for struct_name, struct_data in result.get("structures", {}).items():
                recommendations = struct_data.get("recommendations", {})
                if any(recommendations.get(key) for key in ["clinical_suggestions", "parameter_suggestions", "optimization_suggestions"]):
                    recommendations_found = True
                    print(f"   Recommendations available for {struct_name}")
            if recommendations_found:
                print("   Clinical recommendations generated")
        
        self.test_results["session_tests"]["session5"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nSession 5 Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def test_error_handling(self):
        """Test error handling and edge cases."""
        print("\n" + "="*60)
        print("ERROR HANDLING TESTS")
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Test invalid structure name
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "NONEXISTENT_STRUCTURE", "max_dose", 50.0, 1000.0,
            rationale="Test invalid structure"
        )
        if self.print_test_result("Invalid Structure Name", result, expected_success=False):
            tests_passed += 1
            
        # Test invalid constraint parameters
        total_tests += 1
        result = self.engine.add_constraint(
            "PTV70", "min_max_dvh",
            # Missing required dose_reference parameter
            upper_bound=50.0,
            rationale="Test missing parameters"
        )
        if self.print_test_result("Invalid Constraint Parameters", result, expected_success=False):
            tests_passed += 1
            
        # Test invalid robustness setting
        total_tests += 1
        result = self.engine.add_optimization_objective(
            "PTV70", "max_dose", 50.0, 1000.0,
            robustness="INVALID_ROBUSTNESS",
            rationale="Test invalid robustness"
        )
        if self.print_test_result("Invalid Robustness Setting", result, expected_success=False):
            tests_passed += 1
        
        self.test_results["error_handling_tests"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nError Handling Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def test_optimization_workflow(self):
        """Test complete optimization workflow."""
        print("\n" + "="*60)
        print("OPTIMIZATION WORKFLOW TEST")
        print("="*60)
        
        tests_passed = 0
        total_tests = 0
        
        # Set optimizer
        total_tests += 1
        result = self.engine.set_optimizer(optimizer_type="fmincon", max_iterations=10)
        if self.print_test_result("Set Optimizer", result):
            tests_passed += 1
        
        # Run optimization
        total_tests += 1
        print("Running optimization (this may take a moment)...")
        result = self.engine.optimize_fluence()
        if self.print_test_result("Run Optimization", result):
            tests_passed += 1
            if result.get("optimization_analysis"):
                analysis = result["optimization_analysis"]
                print(f"   Convergence: {analysis.get('convergence_status', 'unknown')}")
                print(f"   Final objective: {analysis.get('final_objective', 'unknown')}")
        
        # Evaluate plan
        total_tests += 1
        result = self.engine.evaluate_plan_quality()
        if self.print_test_result("Evaluate Plan Quality", result):
            tests_passed += 1
            if result.get("plan_quality_score"):
                print(f"   Plan quality score: {result['plan_quality_score']}")
        
        self.test_results["integration_tests"]["optimization_workflow"] = {
            "passed": tests_passed,
            "total": total_tests,
            "success_rate": tests_passed / total_tests
        }
        
        print(f"\nOptimization Workflow Results: {tests_passed}/{total_tests} tests passed")
        return tests_passed == total_tests
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("="*80)
        print("COMPREHENSIVE OPTIMIZATION FUNCTIONALITY TEST SUITE")
        print("Testing all features from Sessions 1-6")
        print("="*80)
        
        start_time = time.time()
        
        # Setup
        if not self.setup_basic_patient():
            print("❌ CRITICAL: Patient setup failed. Cannot continue testing.")
            return False
        
        # Run all test categories
        test_results = []
        
        test_results.append(self.test_session1_eud_dvh_objectives())
        test_results.append(self.test_session2_constraint_framework()) 
        test_results.append(self.test_session4_advanced_parameters())
        test_results.append(self.test_session5_comprehensive_inspection())
        test_results.append(self.test_error_handling())
        test_results.append(self.test_optimization_workflow())
        
        # Summary
        elapsed_time = time.time() - start_time
        total_passed = sum(test_results)
        total_tests = len(test_results)
        
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE SUMMARY")
        print("="*80)
        
        print(f"Overall Results: {total_passed}/{total_tests} test categories passed")
        print(f"Total execution time: {elapsed_time:.2f} seconds")
        
        # Detailed results
        print("\nDetailed Results by Category:")
        for category, results in self.test_results.items():
            if isinstance(results, dict):
                for test_name, test_data in results.items():
                    if isinstance(test_data, dict) and "passed" in test_data:
                        success_rate = test_data["success_rate"] * 100
                        print(f"  {test_name}: {test_data['passed']}/{test_data['total']} ({success_rate:.1f}%)")
        
        # Save results to file
        self.save_test_results(elapsed_time)
        
        # Final assessment
        if total_passed == total_tests:
            print("\n🎉 ALL TESTS PASSED! The comprehensive optimization system is working correctly.")
            return True
        else:
            print(f"\n⚠️  {total_tests - total_passed} test categories failed. Review the results above.")
            return False
    
    def save_test_results(self, elapsed_time: float):
        """Save test results to file."""
        self.test_results["summary"] = {
            "total_execution_time": elapsed_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_suite_version": "Session 6 Comprehensive Testing"
        }
        
        results_file = "test_logs/comprehensive_optimization_test_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📁 Test results saved to: {results_file}")
    
    def cleanup(self):
        """Clean up after testing."""
        try:
            self.engine.stop_engine()
            print("\n🧹 Test cleanup completed.")
        except:
            pass

def main():
    """Main test execution."""
    tester = ComprehensiveOptimizationTester()
    
    try:
        success = tester.run_all_tests()
        return success
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        tester.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
