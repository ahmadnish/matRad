#!/usr/bin/env python3
"""
Comprehensive test script for matRad objectives and constraints functions.

IMPORTANT: This script requires the MATLAB environment to be activated first:
    source /Users/ahmadneishabouri/matlab_env/bin/activate

This script tests all functions in matrad_tools.py that deal with:
- Getting current objectives and constraints
- Adding optimization objectives (min_dose, max_dose, mean_dose, etc.)
- Removing optimization objectives
- Adding constraints (min_max_dose, min_max_mean_dose, etc.)
- Removing constraints
- Clearing all objectives

Each test saves results to separate .mat files for inspection in MATLAB.
"""

import os
import sys
import time
from pathlib import Path

# Add the LLM_Agent_Planner directory to the path
sys.path.append(str(Path(__file__).parent / "LLM_Agent_Planner"))

from matrad_tools import create_matrad_engine

def test_objectives_and_constraints():
    """Main test function for objectives and constraints."""
    
    print("=" * 80)
    print("COMPREHENSIVE TEST: matRad Objectives and Constraints Functions")
    print("=" * 80)
    
    # Initialize matRad engine
    print("\n1. Initializing matRad Engine...")
    engine = create_matrad_engine()
    
    try:
        # Start the engine
        result = engine.start_engine()
        if not result:
            print("❌ Failed to start matRad engine")
            return
        print("✅ matRad engine started successfully")
        
        # Load patient data
        print("\n2. Loading Patient Data...")
        patient_file = "HandN.mat"
        load_result = engine.load_patient(patient_file)
        if not load_result["success"]:
            print(f"❌ Failed to load patient: {load_result['error']}")
            return
        print(f"✅ Patient loaded: {load_result['message']}")
        print(f"   CT dimensions: {load_result['ct_dimensions']}")
        print(f"   Number of structures: {load_result['num_structures']}")
        
        # Get structure information
        print("\n3. Getting Structure Information...")
        struct_info = engine.get_structure_names()
        if not struct_info["success"]:
            print(f"❌ Failed to get structures: {struct_info['error']}")
            return
        
        print(f"✅ Found structures:")
        print(f"   Targets: {struct_info['targets']}")
        print(f"   OARs: {struct_info['oars']}")
        print(f"   Other: {struct_info['other']}")
        
        # Save initial state
        print("\n4. Saving Initial State...")
        save_result = engine.save_plan("test_results/00_initial_state.mat", save_results=False)
        if save_result["success"]:
            print(f"✅ Saved: {save_result['message']}")
        else:
            print(f"❌ Save failed: {save_result['error']}")
            return
        
        # Test 1: Get current objectives (should be empty initially)
        print("\n" + "="*60)
        print("TEST 1: Get Current Objectives (Initial State)")
        print("="*60)
        
        objectives_result = engine.get_current_objectives()
        if objectives_result["success"]:
            print(f"✅ Current objectives retrieved:")
            print(f"   Total objectives: {objectives_result['total_objectives']}")
            for struct_name, objectives in objectives_result['objectives_by_structure'].items():
                print(f"   {struct_name}: {len(objectives)} objectives")
                for obj in objectives:
                    print(f"     - {obj['objective_type']}: dose={obj['dose_value']}, penalty={obj['penalty']}")
        else:
            print(f"❌ Failed to get objectives: {objectives_result['error']}")
        
        # Test 2: Get current constraints (should be empty initially)
        print("\n" + "="*60)
        print("TEST 2: Get Current Constraints (Initial State)")
        print("="*60)
        
        constraints_result = engine.get_current_constraints()
        if constraints_result["success"]:
            print(f"✅ Current constraints retrieved:")
            print(f"   Total constraints: {constraints_result['total_constraints']}")
            for struct_name, constraints in constraints_result['constraints_by_structure'].items():
                print(f"   {struct_name}: {len(constraints)} constraints")
                for const in constraints:
                    print(f"     - {const['constraint_type']}: params={const['parameters']}")
        else:
            print(f"❌ Failed to get constraints: {constraints_result['error']}")
        
        # Test 3: Add various optimization objectives
        print("\n" + "="*60)
        print("TEST 3: Adding Optimization Objectives")
        print("="*60)
        
        # Get target and OAR names for testing
        targets = struct_info['targets']
        oars = struct_info['oars']
        
        if targets:
            target_name = targets[0]  # Use first target
            
            # Test different objective types
            objective_tests = [
                {"type": "min_dose", "dose": 60.0, "penalty": 1000, "rationale": "Ensure minimum target coverage"},
                {"type": "max_dose", "dose": 66.0, "penalty": 1000, "rationale": "Limit maximum target dose"},
                {"type": "mean_dose", "dose": 63.0, "penalty": 500, "rationale": "Control mean target dose"},
                {"type": "square_deviation", "dose": 63.0, "penalty": 800, "rationale": "Improve dose homogeneity"},
                {"type": "eud", "dose": 62.0, "penalty": 600, "rationale": "EUD-based optimization", "eud_exponent": 4.0},
                {"type": "min_dvh", "dose": 60.0, "penalty": 1200, "rationale": "DVH-based coverage", "volume_percent": 95.0},
                {"type": "max_dvh", "dose": 65.0, "penalty": 800, "rationale": "DVH-based dose limit", "volume_percent": 5.0}
            ]
            
            for i, obj_test in enumerate(objective_tests):
                print(f"\n   Adding {obj_test['type']} objective to {target_name}...")
                
                kwargs = {
                    "structure_name": target_name,
                    "obj_type": obj_test["type"],
                    "dose_value": obj_test["dose"],
                    "penalty": obj_test["penalty"],
                    "rationale": obj_test["rationale"]
                }
                
                # Add optional parameters
                if "eud_exponent" in obj_test:
                    kwargs["eud_exponent"] = obj_test["eud_exponent"]
                if "volume_percent" in obj_test:
                    kwargs["volume_percent"] = obj_test["volume_percent"]
                
                add_result = engine.add_optimization_objective(**kwargs)
                
                if add_result["success"]:
                    print(f"   ✅ Added {obj_test['type']}: {add_result['message']}")
                else:
                    print(f"   ❌ Failed to add {obj_test['type']}: {add_result['error']}")
                
                # Save state after each objective
                engine.save_plan(f"test_results/01_{i+1:02d}_added_{obj_test['type']}_objective.mat", save_results=False)
        
        if oars:
            oar_name = oars[0]  # Use first OAR
            
            # Add OAR objectives
            oar_objectives = [
                {"type": "max_dose", "dose": 45.0, "penalty": 2000, "rationale": "Limit OAR maximum dose"},
                {"type": "mean_dose", "dose": 20.0, "penalty": 1500, "rationale": "Minimize OAR mean dose"}
            ]
            
            for i, obj_test in enumerate(oar_objectives):
                print(f"\n   Adding {obj_test['type']} objective to {oar_name}...")
                
                add_result = engine.add_optimization_objective(
                    structure_name=oar_name,
                    obj_type=obj_test["type"],
                    dose_value=obj_test["dose"],
                    penalty=obj_test["penalty"],
                    rationale=obj_test["rationale"]
                )
                
                if add_result["success"]:
                    print(f"   ✅ Added {obj_test['type']}: {add_result['message']}")
                else:
                    print(f"   ❌ Failed to add {obj_test['type']}: {add_result['error']}")
                
                # Save state
                engine.save_plan(f"test_results/02_{i+1:02d}_added_oar_{obj_test['type']}_objective.mat", save_results=False)
        
        # Test 4: Get objectives after adding
        print("\n" + "="*60)
        print("TEST 4: Get Current Objectives (After Adding)")
        print("="*60)
        
        objectives_result = engine.get_current_objectives()
        if objectives_result["success"]:
            print(f"✅ Current objectives retrieved:")
            print(f"   Total objectives: {objectives_result['total_objectives']}")
            for struct_name, objectives in objectives_result['objectives_by_structure'].items():
                print(f"   {struct_name}: {len(objectives)} objectives")
                for obj in objectives:
                    print(f"     - {obj['objective_type']}: dose={obj['dose_value']}, penalty={obj['penalty']}")
        else:
            print(f"❌ Failed to get objectives: {objectives_result['error']}")
        
        engine.save_plan("test_results/03_all_objectives_added.mat", save_results=False)
        
        # Test 5: Add various constraints
        print("\n" + "="*60)
        print("TEST 5: Adding Constraints")
        print("="*60)
        
        if targets:
            # Add target constraints
            target_constraints = [
                {
                    "type": "min_max_dose",
                    "lower": 58.0,
                    "upper": 68.0,
                    "rationale": "Target dose range constraint"
                },
                {
                    "type": "min_max_mean_dose", 
                    "lower": 60.0,
                    "upper": 65.0,
                    "rationale": "Target mean dose constraint"
                },
                {
                    "type": "min_max_eud",
                    "lower": 59.0,
                    "upper": 66.0,
                    "eud_exponent": 3.5,
                    "rationale": "Target EUD constraint"
                },
                {
                    "type": "min_max_dvh",
                    "dose_reference": 60.0,
                    "lower": 95.0,  # 95% volume should receive at least 60 Gy
                    "upper": 100.0,
                    "rationale": "Target DVH coverage constraint"
                }
            ]
            
            for i, const_test in enumerate(target_constraints):
                print(f"\n   Adding {const_test['type']} constraint to {target_name}...")
                
                kwargs = {
                    "structure_name": target_name,
                    "constraint_type": const_test["type"],
                    "rationale": const_test["rationale"]
                }
                
                if "lower" in const_test:
                    kwargs["lower_bound"] = const_test["lower"]
                if "upper" in const_test:
                    kwargs["upper_bound"] = const_test["upper"]
                if "dose_reference" in const_test:
                    kwargs["dose_reference"] = const_test["dose_reference"]
                if "eud_exponent" in const_test:
                    kwargs["eud_exponent"] = const_test["eud_exponent"]
                
                add_result = engine.add_constraint(**kwargs)
                
                if add_result["success"]:
                    print(f"   ✅ Added {const_test['type']}: {add_result['message']}")
                else:
                    print(f"   ❌ Failed to add {const_test['type']}: {add_result['error']}")
                
                # Save state
                engine.save_plan(f"test_results/04_{i+1:02d}_added_{const_test['type']}_constraint.mat", save_results=False)
        
        if oars:
            # Add OAR constraints
            oar_constraints = [
                {
                    "type": "min_max_dose",
                    "lower": 0.0,
                    "upper": 50.0,
                    "rationale": "OAR maximum dose limit"
                },
                {
                    "type": "min_max_mean_dose",
                    "lower": 0.0,
                    "upper": 25.0,
                    "rationale": "OAR mean dose limit"
                }
            ]
            
            for i, const_test in enumerate(oar_constraints):
                print(f"\n   Adding {const_test['type']} constraint to {oar_name}...")
                
                add_result = engine.add_constraint(
                    structure_name=oar_name,
                    constraint_type=const_test["type"],
                    lower_bound=const_test["lower"],
                    upper_bound=const_test["upper"],
                    rationale=const_test["rationale"]
                )
                
                if add_result["success"]:
                    print(f"   ✅ Added {const_test['type']}: {add_result['message']}")
                else:
                    print(f"   ❌ Failed to add {const_test['type']}: {add_result['error']}")
                
                # Save state
                engine.save_plan(f"test_results/05_{i+1:02d}_added_oar_{const_test['type']}_constraint.mat", save_results=False)
        
        # Test 6: Get constraints after adding
        print("\n" + "="*60)
        print("TEST 6: Get Current Constraints (After Adding)")
        print("="*60)
        
        constraints_result = engine.get_current_constraints()
        if constraints_result["success"]:
            print(f"✅ Current constraints retrieved:")
            print(f"   Total constraints: {constraints_result['total_constraints']}")
            for struct_name, constraints in constraints_result['constraints_by_structure'].items():
                print(f"   {struct_name}: {len(constraints)} constraints")
                for const in constraints:
                    print(f"     - {const['constraint_type']}: params={const['parameters']}")
        else:
            print(f"❌ Failed to get constraints: {constraints_result['error']}")
        
        engine.save_plan("test_results/06_all_constraints_added.mat", save_results=False)
        
        # Test 7: Remove specific objectives
        print("\n" + "="*60)
        print("TEST 7: Removing Specific Objectives")
        print("="*60)
        
        if targets:
            # Remove objectives by type
            remove_tests = [
                {"type": "max_dose", "rationale": "Removing max dose objective for testing"},
                {"type": "mean_dose", "rationale": "Removing mean dose objective for testing"},
                {"index": 1, "rationale": "Removing first objective by index"}
            ]
            
            for i, remove_test in enumerate(remove_tests):
                print(f"\n   Removing objective from {target_name}...")
                
                kwargs = {
                    "structure_name": target_name,
                    "rationale": remove_test["rationale"]
                }
                
                if "type" in remove_test:
                    kwargs["objective_type"] = remove_test["type"]
                if "index" in remove_test:
                    kwargs["objective_index"] = remove_test["index"]
                
                remove_result = engine.remove_optimization_objective(**kwargs)
                
                if remove_result["success"]:
                    print(f"   ✅ Removed objective: {remove_result['message']}")
                else:
                    print(f"   ❌ Failed to remove objective: {remove_result['error']}")
                
                # Save state
                engine.save_plan(f"test_results/07_{i+1:02d}_removed_objective.mat", save_results=False)
        
        # Test 8: Remove specific constraints
        print("\n" + "="*60)
        print("TEST 8: Removing Specific Constraints")
        print("="*60)
        
        if targets:
            # Remove constraints by type
            remove_constraint_tests = [
                {"type": "min_max_dose", "rationale": "Removing min_max_dose constraint for testing"},
                {"index": 1, "rationale": "Removing first constraint by index"}
            ]
            
            for i, remove_test in enumerate(remove_constraint_tests):
                print(f"\n   Removing constraint from {target_name}...")
                
                kwargs = {
                    "structure_name": target_name,
                    "rationale": remove_test["rationale"]
                }
                
                if "type" in remove_test:
                    kwargs["constraint_type"] = remove_test["type"]
                if "index" in remove_test:
                    kwargs["constraint_index"] = remove_test["index"]
                
                remove_result = engine.remove_constraint(**kwargs)
                
                if remove_result["success"]:
                    print(f"   ✅ Removed constraint: {remove_result['message']}")
                else:
                    print(f"   ❌ Failed to remove constraint: {remove_result['error']}")
                
                # Save state
                engine.save_plan(f"test_results/08_{i+1:02d}_removed_constraint.mat", save_results=False)
        
        # Test 9: Clear all objectives for a structure
        print("\n" + "="*60)
        print("TEST 9: Clear All Objectives for Structure")
        print("="*60)
        
        if oars:
            print(f"\n   Clearing all objectives for {oar_name}...")
            clear_result = engine.clear_all_objectives(structure_name=oar_name)
            
            if clear_result["success"]:
                print(f"   ✅ Cleared objectives: {clear_result['message']}")
            else:
                print(f"   ❌ Failed to clear objectives: {clear_result['error']}")
            
            engine.save_plan("test_results/09_cleared_oar_objectives.mat", save_results=False)
        
        # Test 10: Clear all objectives for all structures
        print("\n" + "="*60)
        print("TEST 10: Clear All Objectives for All Structures")
        print("="*60)
        
        print("\n   Clearing all objectives for all structures...")
        clear_all_result = engine.clear_all_objectives()
        
        if clear_all_result["success"]:
            print(f"   ✅ Cleared all objectives: {clear_all_result['message']}")
        else:
            print(f"   ❌ Failed to clear all objectives: {clear_all_result['error']}")
        
        engine.save_plan("test_results/10_cleared_all_objectives.mat", save_results=False)
        
        # Final verification: Get final state
        print("\n" + "="*60)
        print("FINAL VERIFICATION: Get Final State")
        print("="*60)
        
        final_objectives = engine.get_current_objectives()
        final_constraints = engine.get_current_constraints()
        
        print(f"\nFinal objectives: {final_objectives['total_objectives'] if final_objectives['success'] else 'Error'}")
        print(f"Final constraints: {final_constraints['total_constraints'] if final_constraints['success'] else 'Error'}")
        
        engine.save_plan("test_results/11_final_state.mat", save_results=False)
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nSaved .mat files for inspection:")
        print("- test_results/00_initial_state.mat")
        print("- test_results/01_XX_added_*_objective.mat")
        print("- test_results/02_XX_added_oar_*_objective.mat")
        print("- test_results/03_all_objectives_added.mat")
        print("- test_results/04_XX_added_*_constraint.mat")
        print("- test_results/05_XX_added_oar_*_constraint.mat")
        print("- test_results/06_all_constraints_added.mat")
        print("- test_results/07_XX_removed_objective.mat")
        print("- test_results/08_XX_removed_constraint.mat")
        print("- test_results/09_cleared_oar_objectives.mat")
        print("- test_results/10_cleared_all_objectives.mat")
        print("- test_results/11_final_state.mat")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        print("\nCleaning up...")
        try:
            engine.stop_engine()
            print("✅ matRad engine stopped")
        except:
            print("⚠️  Warning: Could not stop matRad engine cleanly")

if __name__ == "__main__":
    # Create test results directory
    os.makedirs("test_results", exist_ok=True)
    
    # Run the comprehensive test
    test_objectives_and_constraints()
