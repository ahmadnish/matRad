"""
Comprehensive Agent Interface Testing
====================================

This script tests the LLM Agent's ability to use all optimization functionality
through the natural language interface. It simulates realistic clinical scenarios
where the agent would use the comprehensive optimization tools.

Test Scenarios:
1. Clinical Setup Workflow - Agent sets up optimization functions for head & neck case
2. Conflict Detection - Agent identifies and resolves optimization conflicts  
3. Advanced Parameters - Agent uses EUD, DVH, robustness settings appropriately
4. Inspection and Analysis - Agent uses comprehensive inspection tools
5. Troubleshooting - Agent diagnoses and fixes optimization issues
"""

import os
import sys
import time
import json
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_agent_planning import IMRTPlanningAgent

class AgentOptimizationTester:
    """Test the agent's optimization capabilities in realistic scenarios."""
    
    def __init__(self):
        self.agent = IMRTPlanningAgent()
        self.test_results = {}
        
    def print_agent_response(self, response: str, max_length: int = 200):
        """Print agent response with formatting."""
        if len(response) > max_length:
            response = response[:max_length] + "..."
        print(f"🤖 Agent: {response}")
        
    def test_clinical_setup_workflow(self):
        """Test agent setting up optimization for head & neck case."""
        print("\n" + "="*70)
        print("AGENT TEST 1: Clinical Setup Workflow")
        print("="*70)
        
        # Start planning session
        self.agent.start_planning_session("head_neck_comprehensive_test")
        
        # Load patient
        response = self.agent.execute_task(
            "Load the HEAD_AND_NECK patient data and set up basic planning with beam angles 0, 72, 144, 216, 288."
        )
        print("✅ Patient loaded and basic setup completed")
        
        # Ask agent to use comprehensive inspection before adding objectives
        response = self.agent.execute_task(
            "Before adding any optimization functions, use the comprehensive inspection tool to analyze the current state. Then set up appropriate constraints and objectives for a head and neck IMRT case."
        )
        self.print_agent_response(response)
        
        # Verify the agent used get_optimization_functions
        recent_actions = self.agent.get_recent_actions(5)
        used_comprehensive_inspection = any(
            action.get("tool_name") == "get_optimization_functions" 
            for action in recent_actions
        )
        
        if used_comprehensive_inspection:
            print("✅ Agent correctly used comprehensive inspection tool")
        else:
            print("❌ Agent did not use comprehensive inspection tool")
            
        return used_comprehensive_inspection
    
    def test_advanced_parameters_usage(self):
        """Test agent using advanced parameters appropriately."""
        print("\n" + "="*70)
        print("AGENT TEST 2: Advanced Parameters Usage")
        print("="*70)
        
        # Ask agent to add EUD objectives with appropriate parameters
        response = self.agent.execute_task(
            "Add EUD objectives for the target (PTV70) and a critical structure (SPINAL_CORD). Use clinically appropriate EUD exponents for each structure type."
        )
        self.print_agent_response(response)
        
        # Ask agent to add robustness settings
        response = self.agent.execute_task(
            "Add a constraint for the spinal cord with worst-case robustness for safety, and add a target objective with probabilistic robustness for plan quality."
        )
        self.print_agent_response(response)
        
        # Ask agent to use different MeanDose function types
        response = self.agent.execute_task(
            "Add mean dose objectives for both parotids - use linear function for one and quadratic for the other to test different optimization behaviors."
        )
        self.print_agent_response(response)
        
        # Check if agent used advanced parameters
        recent_actions = self.agent.get_recent_actions(10)
        used_advanced_params = False
        
        for action in recent_actions:
            if action.get("tool_name") == "add_optimization_objective":
                args = action.get("tool_arguments", {})
                if (args.get("eud_exponent") or 
                    args.get("mean_dose_function") or 
                    args.get("robustness", "none") != "none"):
                    used_advanced_params = True
                    break
                    
        if used_advanced_params:
            print("✅ Agent correctly used advanced parameters")
        else:
            print("❌ Agent did not use advanced parameters")
            
        return used_advanced_params
    
    def test_conflict_detection_and_resolution(self):
        """Test agent's ability to detect and resolve conflicts."""
        print("\n" + "="*70)
        print("AGENT TEST 3: Conflict Detection and Resolution")
        print("="*70)
        
        # Deliberately create a conflict by asking for conflicting objectives
        response = self.agent.execute_task(
            "Add a max_dose objective for SPINAL_CORD at 40Gy, then add a constraint with upper bound 35Gy. Use comprehensive inspection to detect any conflicts and resolve them appropriately."
        )
        self.print_agent_response(response)
        
        # Check if agent detected and resolved the conflict
        recent_actions = self.agent.get_recent_actions(10)
        
        detected_conflict = False
        resolved_conflict = False
        
        for action in recent_actions:
            if action.get("tool_name") == "get_optimization_functions":
                detected_conflict = True
            elif action.get("tool_name") in ["remove_optimization_objective", "remove_constraint"]:
                resolved_conflict = True
                
        if detected_conflict and resolved_conflict:
            print("✅ Agent detected and resolved conflict")
            return True
        else:
            print("❌ Agent did not properly handle conflict")
            return False
    
    def test_optimization_workflow(self):
        """Test complete optimization workflow."""
        print("\n" + "="*70)
        print("AGENT TEST 4: Complete Optimization Workflow")
        print("="*70)
        
        # Ask agent to run optimization and analyze results
        response = self.agent.execute_task(
            "Run fluence optimization and then evaluate the plan quality. If there are any issues, use the comprehensive inspection tool to identify problems and make improvements."
        )
        self.print_agent_response(response)
        
        # Check if agent completed the workflow
        recent_actions = self.agent.get_recent_actions(5)
        
        ran_optimization = any(
            action.get("tool_name") == "optimize_fluence"
            for action in recent_actions
        )
        
        evaluated_plan = any(
            action.get("tool_name") == "evaluate_plan_quality"
            for action in recent_actions
        )
        
        if ran_optimization and evaluated_plan:
            print("✅ Agent completed optimization workflow")
            return True
        else:
            print("❌ Agent did not complete optimization workflow")
            return False
    
    def test_clinical_recommendations(self):
        """Test agent's ability to follow clinical recommendations."""
        print("\n" + "="*70)
        print("AGENT TEST 5: Clinical Recommendations")
        print("="*70)
        
        # Ask agent to get recommendations and implement them
        response = self.agent.execute_task(
            "Use comprehensive inspection to get clinical recommendations for all structures, then implement the most important recommendations to improve the plan."
        )
        self.print_agent_response(response)
        
        # Check if agent used recommendations
        recent_actions = self.agent.get_recent_actions(10)
        
        got_recommendations = any(
            action.get("tool_name") == "get_optimization_functions" and
            action.get("tool_arguments", {}).get("include_recommendations", False)
            for action in recent_actions
        )
        
        if got_recommendations:
            print("✅ Agent requested and used clinical recommendations")
            return True
        else:
            print("❌ Agent did not use clinical recommendations")
            return False
    
    def run_comprehensive_agent_tests(self):
        """Run all agent tests."""
        print("="*80)
        print("COMPREHENSIVE AGENT OPTIMIZATION TESTING")
        print("Testing agent's ability to use all optimization features")
        print("="*80)
        
        start_time = time.time()
        
        # Run all tests
        test_results = []
        
        try:
            test_results.append(self.test_clinical_setup_workflow())
            test_results.append(self.test_advanced_parameters_usage())
            test_results.append(self.test_conflict_detection_and_resolution())
            test_results.append(self.test_optimization_workflow())
            test_results.append(self.test_clinical_recommendations())
            
        except Exception as e:
            print(f"❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Summary
        elapsed_time = time.time() - start_time
        total_passed = sum(test_results)
        total_tests = len(test_results)
        
        print("\n" + "="*80)
        print("AGENT TESTING SUMMARY")
        print("="*80)
        
        print(f"Agent Tests Passed: {total_passed}/{total_tests}")
        print(f"Total execution time: {elapsed_time:.2f} seconds")
        
        # Test breakdown
        test_names = [
            "Clinical Setup Workflow",
            "Advanced Parameters Usage", 
            "Conflict Detection & Resolution",
            "Optimization Workflow",
            "Clinical Recommendations"
        ]
        
        for i, (name, passed) in enumerate(zip(test_names, test_results)):
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} {name}")
        
        # Save results
        self.save_agent_test_results(test_results, test_names, elapsed_time)
        
        if total_passed == total_tests:
            print("\n🎉 ALL AGENT TESTS PASSED! The agent can effectively use all optimization features.")
            return True
        else:
            print(f"\n⚠️  {total_tests - total_passed} agent tests failed.")
            return False
    
    def save_agent_test_results(self, results: List[bool], test_names: List[str], elapsed_time: float):
        """Save agent test results."""
        test_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "passed_tests": sum(results),
            "execution_time": elapsed_time,
            "individual_results": {
                name: passed for name, passed in zip(test_names, results)
            },
            "test_summary": {
                "success_rate": sum(results) / len(results),
                "all_passed": all(results)
            }
        }
        
        results_file = "test_logs/agent_comprehensive_test_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"\n📁 Agent test results saved to: {results_file}")
    
    def cleanup(self):
        """Clean up after testing."""
        try:
            if hasattr(self.agent, 'engine') and self.agent.engine:
                self.agent.engine.stop_engine()
            print("\n🧹 Agent test cleanup completed.")
        except:
            pass

def main():
    """Main execution."""
    tester = AgentOptimizationTester()
    
    try:
        success = tester.run_comprehensive_agent_tests()
        return success
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during agent testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        tester.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
