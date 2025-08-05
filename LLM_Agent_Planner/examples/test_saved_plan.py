"""
Test script for matrad_tools module with saved plan.

This script tests the basic functionality of the matrad_tools module
with a head and neck IMRT planning example.
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrad_tools import create_matrad_engine

def print_result(result, step_name):
    """Print result in a formatted way."""
    print(f"\n{'='*20} {step_name} {'='*20}")
    if result["success"]:
        print(f"SUCCESS: {result.get('message', '')}")
        # Print other useful information
        for k, v in result.items():
            if k not in ["success", "message"] and not k.startswith("_"):
                print(f"  - {k}: {v}")
    else:
        print(f"ERROR: {result.get('error', 'Unknown error')}")

# Initialize matRad engine
engine = create_matrad_engine()

# Start engine
engine.start_engine()

# 1. Load patient data
#result = engine.load_patient("HEAD_AND_NECK_saved_plan.mat")
# result = engine.load_patient("HandN_saved.mat")
#result = engine.load_patient("HEAD_AND_NECK.mat")
result = engine.load_patient("HandN_4Agent_noconstraints.mat")
print_result(result, "Load Patient")

engine.resultGUI = True
engine.pln = True
engine.dij = True
engine.cst = True
engine.patient_loaded = True
engine.pln_created = True
engine.dij_calculated = True
    
# 2. Get structure information
result = engine.get_structure_names()
print_result(result, "Structure Information")

# 3. Create treatment plan
result = engine.create_empty_plan()
print_result(result, "Create Plan")

# 4. Set beam angles
beam_angles = [0, 72, 144, 216, 288]  # 5-field IMRT setup
#beam_angles = [72]
result = engine.set_beam_angles(beam_angles)
print_result(result, "Set Beam Angles")

# 5. Set optimizer
result = engine.set_optimizer(optimizer_type="fmincon", max_iterations=500)
print_result(result, "Set Optimizer")

# 6. Generate beam geometry
result = engine.generate_beam_geometry()
print_result(result, "Generate Beam Geometry")

# # 7. Calculate influence matrix
# result = engine.calculate_influence_matrix()
# print_result(result, "Calculate Influence Matrix")

# 8. Set optimization objectives
# Target objectives
result = engine.add_optimization_objective("PTV70", "square_deviation", 70.0, 1000.0)
print_result(result, "Add PTV70 Objective")

result = engine.add_optimization_objective("PTV63", "square_deviation", 63.0, 1000.0)
print_result(result, "Add PTV63 Objective")

# OAR objectives
result = engine.add_optimization_objective("PAROTID_LT", "max_dose", 25.0, 100.0)
print_result(result, "Add PAROTID_LT Objective")

result = engine.add_optimization_objective("PAROTID_RT", "max_dose", 25.0, 100.0)
print_result(result, "Add PAROTID_RT Objective")

result = engine.add_optimization_objective("SPINAL_CORD", "max_dose", 45.0, 800.0)
print_result(result, "Add SPINAL_CORD Objective")

# 9. Run fluence optimization
# result = engine.optimize_fluence()
# print_result(result, "Fluence Optimization")

# # 10. Calculate DVH
# result = engine.calculate_dvh()
# print_result(result, "Calculate DVH")

# result = engine.calculate_dvh()
# print_result(result, "Calculate DVH for PTV63")

# # 11. Evaluate plan
# result = engine.evaluate_plan()
# print_result(result, "Plan Evaluation")

# # 12. Save plan
# result = engine.save_plan("test_hn_plan.mat")
# print_result(result, "Save Plan")

print("\n" + "="*60)
print("🔍 DEBUGGING get_current_objectives()")
print("="*60)

# First, let's check if we actually have any objectives in CST
print("Checking CST structure...")
try:
    if hasattr(engine, 'eng') and engine.eng is not None:
        # Check if CST exists
        cst_exists = engine.eng.eval("exist('cst', 'var')", nargout=1)
        print(f"CST variable exists: {cst_exists}")
        
        if cst_exists:
            # Check CST size
            cst_size = engine.eng.eval("size(cst)", nargout=1)
            print(f"CST size: {cst_size}")
            
            # Check if any structures have objectives (column 6)
            has_any_objectives = engine.eng.eval("any(cellfun(@(x) ~isempty(x), cst(:,6)))", nargout=1) 
            print(f"Any structures have objectives: {has_any_objectives}")
            
            # Print structure names and their objective status
            num_structures = int(engine.eng.eval("size(cst,1)", nargout=1))
            print(f"Number of structures: {num_structures}")
            
            for i in range(1, min(num_structures + 1, 11)):  # Check first 10 structures
                has_name = engine.eng.eval(f"~isempty(cst{{{i},2}})", nargout=1)
                if has_name:
                    struct_name = str(engine.eng.eval(f"cst{{{i},2}}", nargout=1))
                    has_obj = engine.eng.eval(f"~isempty(cst{{{i},6}})", nargout=1)
                    if has_obj:
                        num_obj = int(engine.eng.eval(f"length(cst{{{i},6}})", nargout=1))
                        print(f"  {i}. {struct_name}: {num_obj} objectives")
                    else:
                        print(f"  {i}. {struct_name}: no objectives")
    else:
        print("MATLAB engine not available for debugging")
except Exception as e:
    print(f"Debug error: {e}")

print("\n" + "="*40)
print("Now calling get_current_objectives()...")
result = engine.get_current_objectives()
print_result(result, "Get Current Objectives")