"""
Test script for the PlanningLogger

This script demonstrates the functionality of the PlanningLogger by simulating
a typical planning session with various log entries.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the system path to import the logger module
parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from logger import PlanningLogger, create_logger


def main():
    """
    Demonstrate the PlanningLogger functionality.
    """
    print("Testing PlanningLogger...")
    
    # Create a temporary log directory for testing
    test_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_logs')
    os.makedirs(test_log_dir, exist_ok=True)
    
    # Create a logger instance with a specific session ID
    logger = create_logger(log_dir=test_log_dir, session_id="test_session_001")
    
    # Set plan information
    logger.set_plan_info("PATIENT123", "H&N_IMRT_Plan")
    
    # Log a series of actions to simulate a planning workflow
    logger.log_action(
        "load_patient", 
        "Loaded patient data", 
        {"patient_id": "PATIENT123", "structures": ["PTV", "Brainstem", "Parotid_L", "Parotid_R"]}
    )
    
    # Log beam arrangement setup
    beam_angles = [0, 72, 144, 216, 288]
    logger.log_action(
        "set_beam_angles", 
        f"Set {len(beam_angles)} beam angles for IMRT plan",
        {"angles": beam_angles, "technique": "IMRT"}
    )
    
    # Log a suggestion
    logger.log_suggestion(
        "beam_arrangement",
        "Consider adding a posterior beam at 180 degrees",
        "Better coverage of the posterior aspect of the PTV",
        {"suggested_angles": [0, 72, 144, 180, 216, 288]}
    )
    
    # Log user interaction
    logger.log_user_interaction(
        "command",
        "Add a beam at 180 degrees",
        "Added beam at 180 degrees to the plan"
    )
    
    # Log updated beam arrangement
    updated_angles = [0, 72, 144, 180, 216, 288]
    logger.log_action(
        "set_beam_angles",
        f"Updated to {len(updated_angles)} beam angles",
        {"angles": updated_angles, "technique": "IMRT"}
    )
    
    # Log dose calculation
    logger.log_action(
        "calculate_influence_matrix",
        "Calculated dose influence matrix",
        {"calculation_time": 12.5, "resolution": "3mm"}
    )
    
    # Log optimization objectives
    objectives = [
        {"type": "min_dose", "structure": "PTV", "dose": 70, "weight": 100},
        {"type": "max_dose", "structure": "PTV", "dose": 77, "weight": 100},
        {"type": "max_dvh", "structure": "Brainstem", "dose": 54, "volume": 0, "weight": 80},
        {"type": "max_dvh", "structure": "Parotid_L", "dose": 26, "volume": 50, "weight": 40},
        {"type": "max_dvh", "structure": "Parotid_R", "dose": 26, "volume": 50, "weight": 40}
    ]
    
    optimization_results = {
        "function_value": 0.0542,
        "iterations": 65,
        "time": 8.7,
        "converged": True
    }
    
    logger.log_optimization(objectives, optimization_results)
    
    # Log plan metrics
    metrics = {
        "PTV": {
            "D95": 69.5,
            "D5": 76.2,
            "V95": 98.7,
            "conformity_index": 0.92,
            "homogeneity_index": 0.10
        },
        "Brainstem": {
            "D0.1cc": 52.3,
            "Dmax": 54.1,
            "Dmean": 22.8
        },
        "Parotid_L": {
            "Dmean": 25.6,
            "V26": 48.2
        },
        "Parotid_R": {
            "Dmean": 24.9,
            "V26": 46.5
        }
    }
    
    logger.log_metrics(metrics)
    
    # Log a suggestion based on the metrics
    logger.log_suggestion(
        "objective_change",
        "Increase weight for Brainstem max dose constraint",
        "Brainstem D0.1cc is approaching the tolerance limit",
        {"structure": "Brainstem", "current_weight": 80, "suggested_weight": 100}
    )
    
    # Log an error
    logger.log_error(
        "optimization_warning",
        "Optimization reached maximum iterations before convergence",
        "IterationLimit: Max iterations (100) reached before convergence criteria satisfied"
    )
    
    # Print log summary
    print("\nLog Summary:")
    logger.print_log_summary()
    
    # Export the log to a specific file
    export_path = os.path.join(test_log_dir, "exported_test_log.json")
    logger.export_log(export_path)
    print(f"\nLog exported to: {export_path}")
    
    # Read and display the exported log to verify
    print("\nVerifying exported log content:")
    with open(export_path, 'r') as f:
        log_data = json.load(f)
        print(f"  Session ID: {log_data['session_id']}")
        print(f"  Patient ID: {log_data['patient_id']}")
        print(f"  Plan Name: {log_data['plan_name']}")
        print(f"  Number of entries: {len(log_data['entries'])}")
        
        # Count entry types
        entry_types = {}
        for entry in log_data['entries']:
            entry_type = entry['type']
            entry_types[entry_type] = entry_types.get(entry_type, 0) + 1
            
        print("  Entry types count:")
        for entry_type, count in entry_types.items():
            print(f"    - {entry_type}: {count}")
    
    print("\nTest completed successfully!")


if __name__ == "__main__":
    main() 