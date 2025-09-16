"""
Test script for LLM Agent-based IMRT Planning using OpenAI Agents SDK

This script demonstrates how an LLM agent can make autonomous decisions
to create and iteratively improve an IMRT treatment plan using matRad tools.

IMPORTANT: Before running this script, source the project environment:
    source /Users/ahmadneishabouri/matlab_env/bin/activate
"""

import os
import json
import time
import numpy as np
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from openai import OpenAI
from matrad_tools import MatRadEngine
from logger import PlanningLogger

# Initialize OpenAI client
client = OpenAI()

def convert_matlab_types(obj):
    """
    Convert MATLAB types to JSON-serializable Python types.
    
    Args:
        obj: Object that may contain MATLAB types
        
    Returns:
        JSON-serializable object
    """
    if hasattr(obj, '_data'):  # MATLAB array types
        return obj._data.tolist() if hasattr(obj._data, 'tolist') else list(obj._data)
    elif hasattr(obj, 'tolist'):  # numpy arrays
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_matlab_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_matlab_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_matlab_types(item) for item in obj)
    else:
        return obj


class IMRTPlanningAgent:
    """LLM Agent for IMRT Planning using OpenAI function calling with structured outputs."""
    
    def __init__(self, matrad_path: str = None):
        """Initialize the planning agent with matRad engine."""
        self.engine = MatRadEngine(matrad_path)
        self.logger = PlanningLogger()
        self.conversation_history = []
        self.plan_state = {
            "engine_started": False,
            "patient_loaded": False,
            "plan_created": False,
            "beam_geometry_generated": False,
            "influence_matrix_calculated": False,
            "objectives_added": [],
            "optimization_completed": False,
            "plan_evaluated": False,
            "iteration_count": 0
        }
        
        # Log initialization
        self.logger.log_action("initialization", "Agent initialized", 
                              {"matrad_path": matrad_path})
        
    def get_available_tools(self) -> List[Dict]:
        """Define the tools available to the LLM agent with structured outputs."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "start_matlab_engine",
                    "description": "Start the MATLAB engine and initialize matRad. Must be called first.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "load_patient_data",
                    "description": "Load patient CT and structure data from a .mat file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_file": {
                                "type": "string", 
                                "description": "Path to patient .mat file"
                            }
                        },
                        "required": ["patient_file"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_structure_information",
                    "description": "Get information about structures (targets, OARs) in the loaded patient.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_treatment_plan",
                    "description": "Create an empty treatment plan with default settings.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_beam_configuration",
                    "description": "Set beam angles for the treatment plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "gantry_angles": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "List of gantry angles in degrees"
                            },
                            "couch_angles": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "List of couch angles in degrees (optional)"
                            }
                        },
                        "required": ["gantry_angles"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_beam_geometry",
                    "description": "Generate beam geometry (stf) based on the current plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_dose_influence_matrix",
                    "description": "Calculate the dose influence matrix. This is computationally intensive.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_objectives",
                    "description": "Get all current optimization objectives for all structures. Essential for understanding what objectives are already set before adding new ones or making modifications.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_optimization_objective",
                    "description": "Add an optimization objective for a structure. ALWAYS provide a clear rationale explaining why this objective is necessary at this stage of the planning process. Keep the rationale short and concise.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure"
                            },
                            "objective_type": {
                                "type": "string",
                                "enum": ["min_dose", "max_dose", "mean_dose", "square_deviation", "eud", "min_dvh", "max_dvh"],
                                "description": "Type of objective"
                            },
                            "dose_value": {
                                "type": "number",
                                "description": "Dose value in Gy (for EUD: target EUD value; for DVH: dose threshold)"
                            },
                            "volume_percent": {
                                "type": "number",
                                "description": "Volume percentage for DVH objectives (e.g., 95 for 95%). Only used for min_dvh and max_dvh."
                            },
                            "eud_exponent": {
                                "type": "number",
                                "description": "EUD exponent parameter (default 3.5). Only used for eud objective. Higher values emphasize hot spots, lower values emphasize cold spots."
                            },
                            "penalty": {
                                "type": "number",
                                "description": "Penalty weight (default 1000)"
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Clear clinical rationale for why this objective is being added at this stage of the planning process (e.g., 'Ensure adequate target coverage based on prescription dose', 'Protect parotid from xerostomia risk', 'Prevent spinal cord overdose per tolerance limits')"
                            }
                        },
                        "required": ["structure_name", "objective_type", "dose_value", "penalty", "rationale"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_optimization_objective",
                    "description": "Remove a specific optimization objective from a structure. Use this to eliminate redundant or counterproductive objectives identified during optimization analysis. ALWAYS provide a clear rationale explaining why this objective is being removed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure"
                            },
                            "objective_index": {
                                "type": "integer",
                                "description": "Specific index of objective to remove (1-based, optional)"
                            },
                            "objective_type": {
                                "type": "string",
                                "enum": ["min_dose", "max_dose", "mean_dose", "square_deviation", "eud", "min_dvh", "max_dvh"],
                                "description": "Type of objective to remove (optional, removes first match)"
                            },
                            "dose_value": {
                                "type": "number",
                                "description": "Dose value to match for removal (optional, for additional specificity)"
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Clear rationale for why this objective is being removed (e.g., 'Objective causing optimization convergence issues', 'Redundant constraint with similar existing objective', 'Preventing achievement of higher priority clinical goals')"
                            }
                        },
                        "required": ["structure_name", "rationale"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_all_objectives",
                    "description": "Clear all optimization objectives for a specific structure or all structures. Use when starting fresh or when current objectives are preventing convergence.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of specific structure to clear (optional, clears all structures if omitted)"
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_constraint",
                    "description": "Add an optimization constraint for a structure. Constraints define hard limits (upper/lower bounds) rather than penalties. ALWAYS provide a clear rationale explaining why this constraint is necessary.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure"
                            },
                            "constraint_type": {
                                "type": "string",
                                "enum": ["min_max_dose", "min_max_mean_dose", "min_max_eud", "min_max_dvh"],
                                "description": "Type of constraint"
                            },
                            "lower_bound": {
                                "type": "number",
                                "description": "Lower bound value (optional). For dose constraints: minimum dose in Gy. For DVH: minimum volume fraction (0-1)."
                            },
                            "upper_bound": {
                                "type": "number", 
                                "description": "Upper bound value (optional). For dose constraints: maximum dose in Gy. For DVH: maximum volume fraction (0-1)."
                            },
                            "dose_reference": {
                                "type": "number",
                                "description": "Reference dose for DVH constraints in Gy. Required for min_max_dvh."
                            },
                            "eud_exponent": {
                                "type": "number",
                                "description": "EUD exponent parameter (default 3.5). Only used for min_max_eud constraint."
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Clear clinical rationale for why this constraint is being added (e.g., 'Hard dose limit per protocol', 'Regulatory constraint for critical structure')"
                            }
                        },
                        "required": ["structure_name", "constraint_type", "rationale"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_constraint",
                    "description": "Remove a specific optimization constraint from a structure. Use this to eliminate unnecessary or conflicting constraints. ALWAYS provide a clear rationale explaining why this constraint is being removed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure"
                            },
                            "constraint_index": {
                                "type": "integer",
                                "description": "Specific index of constraint to remove (1-based, optional)"
                            },
                            "constraint_type": {
                                "type": "string",
                                "enum": ["min_max_dose", "min_max_mean_dose", "min_max_eud", "min_max_dvh"],
                                "description": "Type of constraint to remove (optional, removes first match)"
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Clear rationale for why this constraint is being removed (e.g., 'Constraint preventing convergence', 'No longer needed after plan improvements')"
                            }
                        },
                        "required": ["structure_name", "rationale"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_constraints",
                    "description": "Get all current optimization constraints for all structures. Essential for understanding what constraints are already set before adding new ones or making modifications.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_fluence",
                    "description": "Run fluence optimization based on current objectives. Can use previous optimization results as starting point for improved convergence.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "use_previous_weights": {
                                "type": "boolean",
                                "description": "If true, use weights from previous optimization as initial values for warm-start (default: false)"
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_plan_quality",
                    "description": "Evaluate the current plan and calculate metrics for all structures.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_dvh_analysis",
                    "description": "Calculate comprehensive DVH analysis with detailed clinical assessment. For single structure: returns detailed DVH metrics (D95, D50, D5, D2, D98, V-metrics, HI/CI for targets), clinical assessment text, and individual plot. For all structures: returns summary assessment plus individual data for each structure with same detailed metrics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of specific structure to analyze (optional). If provided, returns detailed analysis for that structure only. If omitted, analyzes all structures and returns comprehensive summary plus individual structure data."
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_treatment_plan",
                    "description": "Save the current plan to a .mat file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "output_file": {
                                "type": "string",
                                "description": "Path to save the plan"
                            }
                        },
                        "required": ["output_file"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plan_state",
                    "description": "Get the current state of the planning process.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_ring_structures",
                    "description": "Create concentric ring VOIs around a reference structure for dose sparing analysis and gradient optimization. Useful for creating avoidance zones around critical structures.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reference_structure": {
                                "type": "string",
                                "description": "Name of the reference structure around which rings will be created (e.g., 'PTV', 'Brainstem')"
                            },
                            "ring_margins_mm": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "List of ring margins in mm (e.g., [5, 10, 15] creates rings at 5mm, 10mm, and 15mm from the reference structure)"
                            },
                            "inner_margin_mm": {
                                "type": "number",
                                "description": "Inner margin from reference structure in mm (default: 0). Creates gap between reference structure and first ring."
                            },
                            "visualize": {
                                "type": "boolean",
                                "description": "Whether to create visualization of the rings (default: false)"
                            }
                        },
                        "required": ["reference_structure", "ring_margins_mm"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "perform_voi_operation",
                    "description": "Perform VOI operations (union, intersection, difference) between two structures to create new combined structures. Useful for creating evaluation structures or refined target volumes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure1": {
                                "type": "string",
                                "description": "Name of the first structure"
                            },
                            "structure2": {
                                "type": "string", 
                                "description": "Name of the second structure"
                            },
                            "operation": {
                                "type": "string",
                                "enum": ["union", "intersect", "setdiff"],
                                "description": "Type of operation: 'union' (combine structures), 'intersect' (overlap only), 'setdiff' (first minus second)"
                            },
                            "new_structure_name": {
                                "type": "string",
                                "description": "Name for the new combined structure"
                            }
                        },
                        "required": ["structure1", "structure2", "operation", "new_structure_name"],
                        "additionalProperties": False
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a tool function and return the result with proper type conversion."""
        start_time = time.time()
        
        try:
            if tool_name == "start_matlab_engine":
                result = self.engine.start_engine()
                self.plan_state["engine_started"] = result
                result_dict = {
                    "success": result, 
                    "message": "MATLAB engine started" if result else "Failed to start MATLAB engine"
                }
                
            elif tool_name == "load_patient_data":
                result_dict = self.engine.load_patient(arguments["patient_file"])
                # Convert MATLAB types
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["patient_loaded"] = True
                    # Log patient information
                    self.logger.log_patient_info({
                        "patient_file": arguments["patient_file"],
                        "ct_dimensions": result_dict.get("ct_dimensions"),
                        "num_structures": result_dict.get("num_structures")
                    })
                
            elif tool_name == "get_structure_information":
                result_dict = self.engine.get_structure_names()
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "create_treatment_plan":
                result_dict = self.engine.create_empty_plan()
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["plan_created"] = True
                    
                    # # Configure fmincon tolerances to prevent early stopping
                    # try:
                    #     self._configure_fmincon_tolerances()
                    #     self.logger.log_action(
                    #         "tolerance_config", 
                    #         "Configured fmincon tolerances to prevent early stopping",
                    #         {}
                    #     )
                    # except Exception as e:
                    #     self.logger.log_action(
                    #         "tolerance_config_error",
                    #         "Failed to configure fmincon tolerances",
                    #         {"error": str(e)}
                    #     )

            elif tool_name == "set_beam_configuration":
                result_dict = self.engine.set_beam_angles(
                    arguments["gantry_angles"], 
                    arguments.get("couch_angles")
                )
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "generate_beam_geometry":
                result_dict = self.engine.generate_beam_geometry()
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["beam_geometry_generated"] = True
                
            elif tool_name == "calculate_dose_influence_matrix":
                result_dict = self.engine.calculate_influence_matrix()
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["influence_matrix_calculated"] = True
                
            elif tool_name == "get_current_objectives":
                result_dict = self.engine.get_current_objectives()
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "add_optimization_objective":
                result_dict = self.engine.add_optimization_objective(
                    arguments["structure_name"],
                    arguments["objective_type"],
                    arguments["dose_value"],
                    arguments.get("penalty", 1000.0),
                    arguments.get("rationale", "No rationale provided"),
                    arguments.get("volume_percent", 95),
                    arguments.get("eud_exponent", 3.5)
                )
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    objective_info = {
                        "structure": arguments["structure_name"],
                        "type": arguments["objective_type"],
                        "dose": arguments["dose_value"]
                    }
                    self.plan_state["objectives_added"].append(objective_info)
                    
                    # Log the objective with rationale
                    self.logger.log_objective(
                        arguments["structure_name"],
                        arguments["objective_type"],
                        arguments["dose_value"],
                        arguments.get("penalty", 1000.0)
                    )
                    
                    # Log the rationale separately for emphasis
                    self.logger.log_action(
                        "objective_rationale",
                        f"Added {arguments['objective_type']} objective to {arguments['structure_name']}",
                        {"rationale": arguments.get("rationale", "No rationale provided")},
                        {}
                    )
                    
            elif tool_name == "remove_optimization_objective":
                result_dict = self.engine.remove_optimization_objective(
                    arguments["structure_name"],
                    arguments.get("objective_index"),
                    arguments.get("objective_type"),
                    arguments.get("dose_value"),
                    arguments.get("rationale", "No rationale provided")
                )
                result_dict = convert_matlab_types(result_dict)
                
                # Log the removal rationale separately for emphasis
                if result_dict.get("success"):
                    self.logger.log_action(
                        "objective_removal_rationale",
                        f"Removed objective from {arguments['structure_name']}",
                        {"rationale": arguments.get("rationale", "No rationale provided")},
                        {}
                    )
                
            elif tool_name == "clear_all_objectives":
                result_dict = self.engine.clear_all_objectives(
                    arguments.get("structure_name")
                )
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    # Update plan state to reflect cleared objectives
                    if arguments.get("structure_name"):
                        # Remove objectives for specific structure
                        self.plan_state["objectives_added"] = [
                            obj for obj in self.plan_state["objectives_added"] 
                            if obj["structure"] != arguments["structure_name"]
                        ]
                    else:
                        # Clear all objectives
                        self.plan_state["objectives_added"] = []
                
            elif tool_name == "add_constraint":
                result_dict = self.engine.add_constraint(
                    arguments["structure_name"],
                    arguments["constraint_type"],
                    arguments.get("lower_bound"),
                    arguments.get("upper_bound"),
                    arguments.get("dose_reference"),
                    arguments.get("eud_exponent", 3.5),
                    arguments.get("rationale", "No rationale provided")
                )
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    # Log the constraint with rationale
                    self.logger.log_action(
                        "constraint_added",
                        f"Added {arguments['constraint_type']} constraint to {arguments['structure_name']}",
                        {"rationale": arguments.get("rationale", "No rationale provided")},
                        result_dict
                    )
                
            elif tool_name == "remove_constraint":
                result_dict = self.engine.remove_constraint(
                    arguments["structure_name"],
                    arguments.get("constraint_index"),
                    arguments.get("constraint_type"),
                    arguments.get("rationale", "No rationale provided")
                )
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    # Log the constraint removal with rationale
                    self.logger.log_action(
                        "constraint_removed",
                        f"Removed constraint from {arguments['structure_name']}",
                        {"rationale": arguments.get("rationale", "No rationale provided")},
                        result_dict
                    )
                
            elif tool_name == "get_current_constraints":
                result_dict = self.engine.get_current_constraints()
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "optimize_fluence":
                # Configure fmincon tolerances BEFORE optimization runs
                try:
                    self._configure_fmincon_tolerances()
                    self.logger.log_action(
                        "tolerance_config", 
                        "Configured fmincon tolerances to prevent early stopping",
                        {}
                    )
                except Exception as e:
                    self.logger.log_action(
                        "tolerance_config_error",
                        "Failed to configure fmincon tolerances",
                        {"error": str(e)}
                    )
                
                use_previous_weights = arguments.get("use_previous_weights", False)
                result_dict = self.engine.optimize_fluence(use_previous_weights=use_previous_weights)
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["optimization_completed"] = True
                    self.plan_state["iteration_count"] += 1
                    
                    # Log optimization result with warm-start information
                    execution_time = time.time() - start_time
                    optimization_info = {
                        "optimization_successful": True,
                        "start_type": result_dict.get("start_type", "unknown"),
                        "weights_stored": result_dict.get("weights_stored", False),
                        "weights_count": result_dict.get("weights_count", 0),
                        "used_previous_weights": use_previous_weights
                    }
                    self.logger.log_optimization_result(
                        self.plan_state["iteration_count"],
                        optimization_info,
                        execution_time
                    )
                
            elif tool_name == "evaluate_plan_quality":
                result_dict = self.engine.evaluate_plan()
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["plan_evaluated"] = True
                    
                    # Log plan metrics
                    if "structure_metrics" in result_dict:
                        self.logger.log_plan_metrics(result_dict["structure_metrics"])
                
            elif tool_name == "calculate_dvh_analysis":
                result_dict = self.engine.calculate_dvh(arguments.get("structure_name"))
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "save_treatment_plan":
                result_dict = self.engine.save_plan(arguments["output_file"])
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "get_plan_state":
                result_dict = {"success": True, "plan_state": convert_matlab_types(self.plan_state)}
                
            elif tool_name == "create_ring_structures":
                result_dict = self.engine.create_ring_structures(
                    arguments["reference_structure"],
                    arguments["ring_margins_mm"],
                    arguments.get("inner_margin_mm", 0),
                    arguments.get("visualize", False)
                )
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "perform_voi_operation":
                result_dict = self.engine.perform_voi_operation(
                    arguments["structure1"],
                    arguments["structure2"],
                    arguments["operation"],
                    arguments["new_structure_name"]
                )
                result_dict = convert_matlab_types(result_dict)
                
            else:
                result_dict = {"success": False, "error": f"Unknown tool: {tool_name}"}
            
            # Add execution time and ensure all types are JSON serializable
            execution_time = time.time() - start_time
            result_dict["execution_time_sec"] = execution_time
            result_dict = convert_matlab_types(result_dict)
            
            # Log the action
            self.logger.log_action(
                "tool_call",
                f"Executed {tool_name}",
                arguments,
                result_dict
            )
            
            return result_dict
                
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            execution_time = time.time() - start_time
            error_result["execution_time_sec"] = execution_time
            
            # Log the error
            self.logger.log_action(
                "tool_error",
                f"Error executing {tool_name}",
                arguments,
                error_result
            )
            
            return error_result
    
    def _compress_conversation_history(self, messages: List[Dict], max_messages: int = 20) -> List[Dict]:
        """Compress conversation history to prevent context length issues."""
        if len(messages) <= max_messages:
            return messages
        
        # Keep system prompt, first few messages, and recent messages
        system_msgs = [msg for msg in messages if msg["role"] == "system"]
        other_msgs = [msg for msg in messages if msg["role"] != "system"]
        
        if len(other_msgs) <= max_messages - len(system_msgs):
            return messages
            
        # Keep first 5 and last 10 messages, add compression note
        keep_first = 5
        keep_last = max_messages - len(system_msgs) - keep_first - 1  # -1 for compression note
        
        compressed = system_msgs + other_msgs[:keep_first]
        
        # Add compression summary
        compressed.append({
            "role": "user", 
            "content": f"[Conversation compressed: Kept first {keep_first} and last {keep_last} messages out of {len(other_msgs)} total messages to save context]"
        })
        
        compressed.extend(other_msgs[-keep_last:])
        return compressed
    
    def _configure_fmincon_tolerances(self):
        """
        Configure fmincon tolerances to prevent early stopping.
        This method sets more relaxed tolerances that allow the optimizer to run longer.
        """
        if not self.engine.initialized:
            return
            
        try:
            self.engine.eng.eval("""
            % Configure fmincon tolerances to prevent early stopping
            % First ensure pln exists and has the right structure
            if exist('pln', 'var') && isfield(pln, 'propOpt')
                
                % Force optimizer to be fmincon if not already set
                if ~isfield(pln.propOpt, 'optimizer')
                    pln.propOpt.optimizer = 'fmincon';
                end
                
                % Initialize fmincon options struct if it doesn't exist
                if ~isfield(pln.propOpt, 'fmincon')
                    pln.propOpt.fmincon = struct();
                end
                
                % Set more relaxed tolerances to prevent early stopping
                pln.propOpt.fmincon.StepTolerance = 1e-4;           % Increase from default 1e-10
                pln.propOpt.fmincon.ConstraintTolerance = 1e-3;     % Increase from default 1e-6
                pln.propOpt.fmincon.OptimalityTolerance = 1e-3;     % Increase from default 1e-6
                pln.propOpt.fmincon.FunctionTolerance = 1e-4;       % Increase from default 1e-6
                
                % Increase iteration limits
                pln.propOpt.fmincon.MaxIterations = 500;            % Increase from default
                pln.propOpt.fmincon.MaxFunctionEvaluations = 400;   % Increase from default
                
                % Enable detailed display
                pln.propOpt.fmincon.Display = 'iter';
                
                disp('✅ Configured fmincon tolerances to prevent early stopping:');
                disp(['   Optimizer: ' pln.propOpt.optimizer]);
                disp(['   StepTolerance: ' num2str(pln.propOpt.fmincon.StepTolerance)]);
                disp(['   ConstraintTolerance: ' num2str(pln.propOpt.fmincon.ConstraintTolerance)]);
                disp(['   OptimalityTolerance: ' num2str(pln.propOpt.fmincon.OptimalityTolerance)]);
                disp(['   FunctionTolerance: ' num2str(pln.propOpt.fmincon.FunctionTolerance)]);
                disp(['   MaxIterations: ' num2str(pln.propOpt.fmincon.MaxIterations)]);
                
                % Make sure the plan is saved to the base workspace
                assignin('base', 'pln', pln);
                
            else
                disp('❌ Warning: pln variable not found or missing propOpt field');
                disp('   Cannot configure fmincon tolerances');
            end
            """, nargout=0)
            
        except Exception as e:
            print(f"Warning: Could not configure fmincon tolerances: {e}")
    
    def run_planning_session(self, patient_file: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Run a complete planning session with the LLM agent using structured outputs.
        
        Args:
            patient_file: Path to patient data file
            max_iterations: Maximum number of optimization iterations
            
        Returns:
            Dict with session results
        """
        # Log session start
        self.logger.log_action(
            "session_start", 
            "Starting LLM-guided planning session",
            {"patient_file": patient_file, "max_iterations": max_iterations}
        )
        
        # Initial system prompt
        system_prompt = f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad with advanced objective management and optimization monitoring capabilities.

            Your goal is to create an optimal treatment plan that achieves target coverage while minimizing dose to organs at risk (OARs), following clinical best practices. You have access to tools for beam setup, dose calculation, optimization, plan evaluation, AND IMPORTANTLY, intelligent objective management with optimization convergence monitoring.

            ## Enhanced Planning Process with Smart Objective Management:

            ### Initial Setup (Steps 1-4):
            1. Start the MATLAB engine and load patient data.
            2. Examine the structure information to identify targets and OARs.
            3. Create an initial treatment plan with appropriate beam angles.
            4. Generate the beam geometry and calculate the dose influence matrix.

            ### Intelligent Objective and Constraint Management Workflow (Steps 5+):
            
            **BEFORE adding any objectives or constraints:**
            - ALWAYS use get_current_objectives() AND get_current_constraints() to check what already exists
            - Analyze existing objectives for redundancy, conflicts, or excessive constraints
            - Check constraint feasibility and compatibility with objectives
            - Then proceed to add objectives and constraints based on the Head & Neck Planning Playbook below.


            **Optimization and Monitoring Loop:**
            1. Run optimize_fluence() and CAREFULLY analyze the optimization_analysis results:
               - Monitor convergence quality (good/moderate/poor)
               - Check for objective stagnation and very small step sizes
               - Evaluate relative improvement percentage
               - Read optimization summary for warnings
            2. Evaluate plan quality and clinical metrics
            3. **CRITICAL DECISION POINT:** Based on optimization convergence AND plan quality:

            **If optimization shows POOR convergence (stagnation, tiny steps):**
            - This often indicates too many conflicting/redundant objectives OR infeasible constraints
            - Use get_current_objectives() AND get_current_constraints() to review all optimization functions
            - First check if constraints are feasible - remove/relax constraints if they make the problem infeasible
            - Then strategically remove redundant or conflicting objectives using remove_optimization_objective() WITH CLEAR RATIONALES
            - Use remove_constraint() if constraints are preventing convergence WITH CLEAR RATIONALES
            - ALWAYS explain WHY each objective is being removed (e.g., "Removing redundant max_dose objective conflicting with existing constraint", "Eliminating over-constraining objective causing convergence issues")
            - Consider clear_all_objectives() for specific structures if overwhelmed with objectives
            - Re-optimize with simplified objective set
            
            **If optimization converges well but plan quality is suboptimal:**
            - Add targeted objectives for specific clinical deficiencies WITH CLEAR RATIONALES
            - ALWAYS explain the clinical need for each new objective (e.g., "Adding max_dose constraint due to PTV D2 exceeding 107% per protocol", "Target coverage insufficient, adding min_dose objective to improve D95")
            - Use remove_optimization_objective() to replace ineffective objectives rather than accumulating them - PROVIDE RATIONALE for removals
            - Monitor that total objective count doesn't exceed ~8-12 across all structures
            
            **If the plan quality is good:**
            - Save plan and complete or make minor refinements only

            ### Optimization Strategy with Convergence Monitoring:
            - First optimization: Use optimize_fluence() (cold-start)
            - Subsequent optimizations: Use optimize_fluence(use_previous_weights=true) for warm-start
            - **ANALYZE optimization_analysis output every time:**
              - convergence_quality: "good" = continue, "moderate" = cautious, "poor" = simplify objectives
              - objective_stagnation: true = too many constraints, reduce objectives
              - small_step_sizes: true = optimization struggling, simplify problem
              - relative_improvement: <1% = likely over-constrained
            - If optimization stagnates for 2+ consecutive iterations, clear problematic objectives

            ## Treatment Plan Evaluation Tools

            **For comprehensive plan evaluation, use `evaluate_plan_quality()`:**
            - This is your PRIMARY tool for overall plan assessment
            - Provides complete quality indicators, DVH analysis, and clinical recommendations for all structures        
            - Includes matRad's official quality indicators (D95, D50, HI, CI, V-metrics, etc.)

            **For focused structure analysis, use `calculate_dvh_analysis(structure_name)`:**
            - Use this ONLY when you need detailed analysis of a specific structure
            - For follow-up investigation after comprehensive evaluation
            - When you need structure-specific DVH plots or deep-dive analysis

            **AVOID calling both methods redundantly** - `evaluate_plan_quality()` already includes comprehensive DVH analysis for all structures.

            **After evaluating the plan, provide a summary of the plan quality and clinical metrics, and what you think the next step should be.**

            ## Advanced Structure Management

            **Ring Structure Creation:**
            - Use `create_ring_structures()` to create concentric ring VOIs around critical structures for dose gradient optimization
            - Ideal for sparing structures where dose gradients are critical (e.g., brainstem, optic structures)
            - Example use cases:
              - Create 5mm, 10mm rings around brainstem for gradient control: `create_ring_structures("Brainstem", [5, 10])`
              - Create evaluation rings around PTV: `create_ring_structures("PTV", [5, 15, 25], inner_margin_mm=2)`
            - Ring structures can receive gradient objectives (e.g., max_dose with decreasing penalties)
            - Use inner_margin_mm to create buffer zones between reference structure and first ring

            **VOI Operations for Advanced Planning:**
            - Use `perform_voi_operation()` to create sophisticated evaluation and optimization structures
            - Common clinical applications:
              - **PTV Evaluation Structures**: Create `PTV_eval` by subtracting critical OARs from PTV using setdiff
                - Example: `perform_voi_operation("PTV", "Brainstem", "setdiff", "PTV_eval")`
                - Apply coverage objectives to PTV_eval instead of original PTV for more realistic planning
              - **Combined Target Volumes**: Union multiple PTVs for simultaneous boost planning
                - Example: `perform_voi_operation("PTV1", "PTV2", "union", "PTV_combined")`
              - **Overlap Analysis**: Use intersect to identify structure overlaps and potential planning challenges
                - Example: `perform_voi_operation("PTV", "OAR", "intersect", "PTV_OAR_overlap")`
              - **Avoidance Zones**: Create structures that exclude critical areas from optimization
                - Example: Use setdiff to create body minus critical structures for gradient control

            **Advanced Planning Workflow with Structure Management:**
            1. **After loading patient data**: Analyze structure relationships and potential overlaps
            2. **Create evaluation structures**: Use VOI operations to create clinically relevant evaluation volumes
            3. **Generate ring structures**: For critical OARs requiring dose gradients
            4. **Apply objectives strategically**: Use evaluation structures for coverage, rings for gradient control
            5. **Monitor structure-specific metrics**: Evaluate both original and derived structures

            **Structure Naming Conventions:**
            - Ring structures: Automatically named as "StructureNameRing[X]mm" (e.g., "BrainstemRing5mm")
            - VOI operations: Use descriptive names indicating the operation (e.g., "PTV_minus_Brainstem", "Combined_PTVs")
            - Evaluation structures: Use "_eval" suffix for clinical evaluation volumes

            ## Head & Neck Planning Playbook (Staged Strategy)

            **High-level approach**
            - Initialize from site template → set beams, PRVs (if available), target eval VOIs, and baseline objectives.
            - Stage 1 (Hard OARs + Coverage + Hotspots) → optimize → check feasibility.
            - Stage 2 (Cold-spots + Gradient shaping + Spill caps) → optimize → check.
            - Stage 3 (Soft means / cosmetic shaping) → optimize → check.
            - Convergence test → if any priority fails, apply targeted refinements; if repeated failures, switch strategy.
            - Deliverability checks → hotspots, MU, modulation, robustness notes. Log everything.

            **Priority rules (lexicographic)**
            1) Hard OAR maxima (D0.03 cc or equivalent)
            2) Target coverage (V100, D98)
            3) Target hotspots (D2)
            4) Spill/gradient (rings and BODY−PTVs Vx)
            5) OAR means and secondary preferences
            - Never relax a higher-priority constraint to satisfy a lower-priority one unless flagged infeasible after fallback attempts.

            **Required VOI operations (use tools):**
            - `PTV_eval`: For SIB, create PTV_low \ PTV_high → `perform_voi_operation("PTV_low","PTV_high","setdiff","PTV_low_eval")`
            - `PTV_all`: Union of all PTVs → `perform_voi_operation("PTV63","PTV70","union","PTV_all")` (extend if more PTVs)
            - `BODY−PTVs`: `perform_voi_operation("SKIN","PTV_all","setdiff","BODY_minus_PTVs")` (or BODY if available)
            - Rings: shells around `PTV_all` via `create_ring_structures("PTV_all", [5,15,30], inner_margin_mm=0)`; commonly 0–5 mm and 5–15 mm used first.

            **cc→% conversion (for D0.03cc caps):**
            - Compute OAR volume in cc = (num_voxels × voxel_volume_cc). If available, convert cc to percent as: `Vcc_percent = 100 × (cc / volume_cc)`.
            - When engine expects a fraction (0–1), use `Vcc_fraction = cc / volume_cc`. If exact volume unknown, use a conservative tiny fraction (e.g., 0.1%) and refine when data is available.

            **Objective templates (examples; adapt to site)**
            - OAR max: `max_dvh` (MaxDVH) at Dlim with V0.03cc→% on OAR and OAR_PRV when present.
            - Targets: `min_dvh`(Rx,95) and `max_dvh`(D2,2) on PTVs.
            - Cold-spots: `min_dvh`(D98,98) on PTVs/EvalPTVs.
            - Gradient: ring control with squared overdosing around caps; optionally `max_dvh` on ring Vx@Dx.
            - Spill: `BODY_minus_PTVs` `max_dvh` at 110%Rx (1 cc) and 105%Rx (10 cc) equivalents (use % fractions as needed).
            - Means: `mean_dose` for brainstem/cord/parotids if feasible.

            **Stepwise procedure**
            - Step 1 — Skeleton (Hard OARs + Coverage + Hotspots)
              - Add OAR hard maxima using `add_constraint` or strong `add_optimization_objective` max_dvh with V0.03cc%:
                - Cord: MaxDVH(45 Gy, V0.03cc%)
                - Brainstem: MaxDVH(54 Gy, V0.03cc%)
                - Cord_PRV: MaxDVH(48 Gy, V0.03cc%) if PRV exists
                - Brainstem_PRV: MaxDVH(57 Gy, V0.03cc%) if PRV exists
              - Targets:
                - PTV70: MinDVH(70 Gy, 95%), MaxDVH(74.9 Gy, 2%)
                - PTV63: MinDVH(63 Gy, 95%), MaxDVH(67.4 Gy, 2%)
              - Optimize. Pass if: OAR D0.03cc ≤ limits; PTV70 V100 ≥95%; PTV63 V100 ≥95%; D2 within caps.

            - Step 2 — Cold-spots + Gradient + Spill
              - Build eval/aux structures with tools: `PTV63_eval = PTV63 \ PTV70`, `PTV_all`, `BODY_minus_PTVs`, rings 0–5, 5–15 (optionally 15–30) via tools.
              - Add objectives:
                - PTV70: MinDVH(66.5 Gy, 98%)
                - PTV63_eval: MinDVH(59.9 Gy, 98%)
                - Rings:
                  - 0–5 mm: SquaredOverdosing p≈120 at Dcap≈58 Gy
                  - 5–15 mm: SquaredOverdosing p≈100 at Dcap≈38 Gy AND MaxDVH(60 Gy, 8%)
                - BODY−PTVs: MaxDVH(1.1×RxHigh, 1%) and MaxDVH(1.05×RxHigh, 10%)
                - If rings struggle, tighten PTV70 hotspot: MaxDVH(74.5 Gy, 2%)
              - Optimize. Pass if: rings 0–5 mm mean ≤60 Gy, 5–15 mm mean ≤40 Gy; spill within limits; Step-1 still satisfied.

            - Step 3 — Soft shaping (means/cosmetic)
              - Add feasible means: Brainstem MeanDose ≤30 Gy; Cord MeanDose ≤25 Gy; Parotids MeanDose ≤26 Gy each if feasible.
              - Optimize. Ensure Step-1/2 remain satisfied.

            **Tuning loop (automated heuristics)**
            - For each failed criterion, apply the smallest effective change and re-optimize:
              - If OAR D0.03 cc fails: +500 weight on that OAR (and PRV); consider reducing nearby PTV D2 by −0.5 Gy; optional small gantry rotation (±10–15°) if allowed.
              - If coverage V95 fails: +50–100 on that PTV MinDVH; keep OAR maxima fixed.
              - If target D2 high: tighten D2 by −0.5 Gy or raise ring penalties by +20–40.
              - If rings hot: replace ring caps with tighter thresholds; do not stack same-type terms.
              - If spill high: tighten BODY−PTVs Vx caps slightly or +20–40 weight.
            - Stop when all criteria pass with ≥0.3 Gy margins or no objective improves after two consecutive refinements.

            **Fallback strategies (on repeated failures)**
            - Lexicographic pass: temporarily convert the top failed metric to a hard cap (increase p 2–3×), re-optimize, then relax slightly.
            - Template switch: load stricter/looser site template.
            - Outer ring add: add 15–30 mm ring with SquaredOverdosing(p≈90, Dcap≈30 Gy) and optional V40 ≤35%.
            - Beam tweak: rotate start angle 10–20° or drop a beam traversing a critical OAR sector, if policy allows.
            - KBP prior: set OAR mean targets from model if available.
            - Arc/angle change (if allowed): adjust geometry.

            **Safety and consistency**
            - Never remove an OAR hard max once added.
            - Replace, don’t stack, same-type objectives on the same VOI.
            - Use eval structures for nested targets.
            - Log: beam list, VOI ops, each objective added/removed, penalties, and all QA metrics.

            Clinical Guidelines:
            - Target structures (PTVs) should receive 95% of the prescribed dose (typically 50–70 Gy).
            - OARs should remain below tolerance doses per QUANTEC guidelines.            
            - Dose values in objective functions are total dose over all fractions.
            - Use appropriate beam arrangements.
            - Prioritize in case of conflict:
                - 1st: PTV coverage
                - 2nd: Critical OAR sparing
                - 3rd: Non-critical structure sparing (Body/Skin)
            - Acceptable plan thresholds:
                - PTV D95 ≥ 95% of prescription
                - Homogeneity Index (HI) < 0.2
                - Conformity Index (CI) > 0.7
                - OAR doses below maximum and mean tolerances

            ## Objective Types and Clinical Usage:

            **Basic Dose Objectives:**
            - **min_dose**: Ensures minimum dose coverage (mainly for targets)
            - **max_dose**: Limits maximum dose (mainly for OARs)
            - **mean_dose**: Controls average dose (useful for both targets and OARs)
            - **square_deviation**: Promotes dose uniformity around a target dose

            **Advanced Objectives:**
            - **EUD (Equivalent Uniform Dose)**: 
                - For targets: Use with low exponent (1-2) to emphasize cold spots
                - For OARs: Use with high exponent (5-10) to emphasize hot spots
                - Target EUD should match prescription dose for targets
                - Default exponent is 3.5, but adjust based on clinical goals
            
            - **DVH-based Objectives:**
                - **min_dvh**: Ensures minimum volume receives threshold dose (for target coverage)
                  - Example: min_dvh with 60Gy, 95% ensures 95% of target gets ≥60Gy
                - **max_dvh**: Limits volume receiving threshold dose (for OAR sparing)  
                  - Example: max_dvh with 20Gy, 30% ensures ≤30% of OAR gets ≥20Gy
                - Volume percentage should be clinically meaningful (typically 90-99% for targets, 10-50% for OARs)

            **Objective Selection Strategy:**
            - Use **min_dose/max_dose** for simple dose limits
            - Use **EUD** when you want to control dose distribution characteristics
            - Use **DVH objectives** when specific volume-dose constraints are critical
            - Use **square_deviation** for dose uniformity around a specific value
            - Combine objectives strategically - avoid redundant or conflicting constraints

            ## Constraints vs. Objectives:

            **Constraints (Hard Limits):**
            - Define **mandatory bounds** that MUST be satisfied for plan acceptance
            - Use for regulatory limits, safety requirements, and protocol mandates
            - Available constraint types:
              - **min_max_dose**: Hard dose limits (e.g., max spinal cord dose ≤45Gy)
              - **min_max_mean_dose**: Mean dose bounds (e.g., parotid mean ≤26Gy)
              - **min_max_eud**: EUD bounds with configurable exponent
              - **min_max_dvh**: DVH bounds (e.g., V20Gy ≤30% for lung)

            **Objectives (Soft Penalties):**
            - Define **optimization goals** that guide the solution toward better plans
            - Use for plan quality improvement and competing trade-offs
            - Have penalty weights that can be adjusted

            **Constraint vs. Objective Strategy:**
            - Use **constraints** for: Safety limits, regulatory requirements, hard protocol limits
            - Use **objectives** for: Plan quality optimization, competing trade-offs, iterative improvements
            - Example approach:
              - Add constraint: `add_constraint("SpinalCord", "min_max_dose", upper_bound=45.0)` 
              - Add objective: `add_optimization_objective("SpinalCord", "max_dose", 35.0, penalty=1000)`
              - This ensures dose never exceeds 45Gy (constraint) while optimizing toward 35Gy (objective)

            **Constraint Management:**
            - **BEFORE adding constraints**: Use `get_current_constraints()` to check existing ones
            - **Be selective**: Too many constraints can make problems infeasible
            - **Provide rationales**: Always explain why each constraint is clinically necessary
            - **Monitor feasibility**: If optimization fails, consider relaxing constraints

            Plan Evaluation Workflow:
            1. Primary: Use evaluate_plan_quality() for comprehensive plan assessment (all structures, quality scoring, clinical recommendations)
            2. Optional: Use calculate_dvh_analysis(structure_name) only for focused analysis of specific structures if needed

            Termination Conditions:
            - A plan is optimal if all clinical thresholds are met (use plan evaluation metrics to verify).
            - Do not iterate further if:
                - Plan quality plateaus over 5 iterations (compare plan quality scores and key metrics)
                - All objective changes result in equivalent or worse tradeoffs
            - Do not re-run dose calculation unless beam geometry or machine parameters change.

            ## Learning and Memory Management:

            **Maintain Optimization Memory Across Iterations:**
            - Track which objective combinations led to poor convergence (stagnation, tiny steps)
            - Remember which objective modifications improved both convergence AND plan quality
            - If an objective set caused convergence issues, don't repeat the same pattern
            - Document your reasoning for objective changes in structured format

            **Pattern Recognition for Optimization Issues:**
            - Multiple min_dose + max_dose objectives on same structure = often redundant
            - Too many objectives (>3) on single structure = usually over-constrained  
            - Very high penalty weights (>10000) = can cause numerical issues
            - Objectives with dose values too close together (<2Gy difference) = often conflicting

            **Adaptive Strategy Based on Convergence History:**
            - If 2+ consecutive optimizations show poor convergence → Simplify objective set
            - If optimizer consistently stops at <20 iterations → Objectives likely over-constraining
            - If step sizes drop to <1e-12 → Problem is numerically ill-conditioned
            - If objective function barely improves (<1%) → Too many competing constraints

            ## Enhanced Termination Conditions:

            **Plan is optimal when:**
            - Optimization convergence quality is "good" or "moderate" 
            - Clinical thresholds are met (PTV D95 ≥95%, OAR doses below limits)
            - Plan quality score >80 or meets clinical requirements

            **CRITICAL: How to Signal Plan Completion:**
            When and ONLY when all clinical criteria are satisfied, respond with the EXACT phrase:
            "PLANNING_COMPLETE: Plan meets all clinical requirements and is ready for clinical use."
            
            Do NOT use this phrase unless:
            1. You have run evaluate_plan_quality() and confirmed all targets meet D95 ≥95% 
            2. All OARs are below tolerance doses
            3. Plan quality score is acceptable (>70) or all clinical requirements are met
            4. You have confirmed these metrics through actual tool results, not assumptions

            **Continue optimization if:**
            - ANY clinical threshold is not met (PTV coverage, OAR sparing)
            - Plan quality can still be improved and convergence is good
            - Optimization is working well but plan needs refinement

            **Only stop iteration if:**
            - Plan meets ALL clinical criteria (verified through evaluate_plan_quality)
            - OR: Plan quality has plateaued over 5 iterations WITH good convergence AND clinical thresholds are met
            - OR: Maximum iterations reached
            - OR: Optimization consistently fails despite objective simplification

            **Never stop unless clinical criteria are met or maximum iterations reached.**

            **IMPORTANT: Work with Available Tools Only:**
            - Do NOT ask for additional information, structure margins, or external data
            - Do NOT request modifications to the patient data or structures
            - Use ONLY the tools provided to achieve the best possible plan
            - If clinical criteria cannot be met with current data, optimize to get as close as possible
            - Make treatment planning decisions based on available structure information and dose constraints
            - If you encounter limitations, work around them using optimization objectives and beam configuration

            **Emergency Completion Criteria:**
            If after 150 iterations clinical criteria still cannot be met despite good optimization convergence:
            - Evaluate whether the plan is clinically usable (even if not ideal)
            - If the plan provides reasonable target coverage (>90%) and OAR sparing, consider accepting it
            - Use phrase "PLANNING_COMPLETE: Plan optimized to best achievable level with available data"

            Logging (Enhanced Structured Format):
            Each planning decision should be logged in a structured JSON format with:
            - "reason": Explanation of the decision
            - "tool_used": Name of the matRad function invoked
            - "inputs": Parameters given to the tool
            - "objective_rationale": For add/remove objective actions, the specific clinical reasoning provided
            - "outcome": Metrics after action from plan evaluation (e.g., D95 = 93.2%, HI = 0.15, Parotid Dmean = 26.1 Gy, V30Gy = 45%)
            - "clinical_assessment": Key findings from plan assessment text
            - "optimization_convergence": Convergence quality, stagnation status, step sizes, relative improvement
            - "objectives_status": Current number of objectives per structure, recent modifications with rationales
            - "learning": What was learned from this iteration for future objective management
            - "next_action": Planned next step with rationale

            Current patient file: {patient_file}  
            Maximum iterations allowed: {max_iterations}

            Key Quality Metrics to Monitor (from evaluate_plan_quality):
            - Targets: D95 (coverage), D50 (median), CI (conformity), HI (homogeneity)
            - OARs: max_dose, mean_dose, V30Gy, V20Gy (volume metrics)
            - All: std_dose (dose uniformity), D2/D98 (dose extremes)
            - Plan-level: quality score (0-100), clinical recommendations

            ## CRITICAL: Action-Oriented Behavior:
            
            - When you have a plan or next step, immediately execute it using the appropriate tool
            - Reasoning should be brief and concise with clear plan-level reasoning across iterations
            - If you're uncertain about something, use tools to gather information rather than asking for clarification
            - When adding or removing objectives, ALWAYS provide clear clinical rationales in the tool calls

            Start by getting the current plan state and then proceed step by step.  
            Always ensure your function calls use valid JSON-serializable parameters.
        """
        
        # Start conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({
            "role": "user", 
            "content": "Begin IMRT planning for this patient immediately. Start by checking the plan state and then proceed with the planning workflow. Take action now - do not just provide reasoning without using tools."
        })
        
        iteration = 0
        while iteration < max_iterations:
            try:
                # Get LLM response with function calling
                response = client.chat.completions.create(
                    model="gpt-5",
                    messages=messages,
                    tools=self.get_available_tools(),
                    tool_choice="auto"
                )
                
                # Add assistant message (simplified version)
                assistant_message = response.choices[0].message
                simplified_assistant = {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": assistant_message.tool_calls
                }
                messages.append(simplified_assistant)
                
                # Check if LLM wants to call functions
                if assistant_message.tool_calls:
                    for tool_call in assistant_message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        print(f"\n🔧 Agent calling: {function_name}")
                        print(f"   Arguments: {arguments}")

                        # Execute the tool
                        result = self.execute_tool(function_name, arguments)
                        
                        print(f"   Result: {result.get('message', result)}")
                        
                        # Convert result to JSON string (now guaranteed to be serializable)
                        result_json = json.dumps(result, ensure_ascii=False, indent=2)                    
                        
                        # Add tool result to conversation
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_json
                        }
                        messages.append(tool_message)
                
                else:
                    # LLM provided a text response without tool calls
                    print(f"\n💭 Agent says: {assistant_message.content}")
                    
                    # Log agent reasoning
                    self.logger.log_action(
                        "agent_reasoning",
                        "Agent provided reasoning or conclusion",
                        {},
                        {"response": assistant_message.content}
                    )
                    
                    # Check if planning is complete using the specific completion phrase
                    if "PLANNING_COMPLETE:" in assistant_message.content:
                        print("\n✅ Agent has declared the plan clinically complete!")
                        break
                        
                    # Check for emergency completion criteria
                    if iteration >= 150:
                        emergency_prompt = ("You have reached 150 iterations. If the current plan provides reasonable "
                                          "target coverage (>90%) and acceptable OAR sparing, you may complete planning "
                                          "using: 'PLANNING_COMPLETE: Plan optimized to best achievable level with available data'. "
                                          "First, run evaluate_plan_quality() to check if the plan is clinically usable.")
                        messages.append({"role": "user", "content": emergency_prompt})
                    else:
                        # Provide more specific continuation prompt emphasizing clinical requirements
                        if self.plan_state.get("plan_evaluated"):
                            continuation_prompt = ("Continue with treatment planning. Remember: you must achieve clinical targets "
                                                 "(PTV D95 ≥95%, all OAR doses below tolerance) before declaring completion. "
                                                 "What is your next step to improve the plan?")
                        else:
                            continuation_prompt = ("Continue with treatment planning. You must evaluate the plan quality first "
                                                 "and ensure all clinical criteria are met before considering the plan complete. "
                                                 "What should we do next?")
                        
                        messages.append({"role": "user", "content": continuation_prompt})
                
                iteration += 1
                
                # Compress conversation history every 10 iterations to prevent context overflow
                if iteration % 50 == 0:
                    old_length = len(messages)
                    messages = self._compress_conversation_history(messages, max_messages=25)
                    if len(messages) < old_length:
                        print(f"📝 Compressed conversation: {old_length} → {len(messages)} messages")
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {str(e)}")
                self.logger.log_action(
                    "session_error",
                    f"Error in iteration {iteration}",
                    {},
                    {"error": str(e)}
                )
                break
        
        # Final evaluation
        final_state = convert_matlab_types(self.plan_state.copy())
        session_results = {
            "success": True,
            "iterations_completed": iteration,
            "final_state": final_state,
            "messages_exchanged": len(messages)
        }
        
        # Log final results
        self.logger.log_final_results(session_results)
        
        return session_results


def main():
    """Main function to test the LLM agent planning system."""
    print("🚀 Starting LLM Agent IMRT Planning Test")
    print("=" * 50)
    
    # Configuration
    matrad_path = "/Users/ahmadneishabouri/matRad"  # Update this path as needed
    #patient_file = "/Users/ahmadneishabouri/matRad/HandN_4Agent_noconstraints.mat"  # Absolute path
    patient_file = "HandN_newskin.mat"
    
    try:
        # Create planning agent
        agent = IMRTPlanningAgent(matrad_path)
        
        print(f"📊 Patient file: {patient_file}")
        print(f"🏥 matRad path: {matrad_path}")
        print(f"📁 Session ID: {agent.logger.session_id}")
        print("\n🤖 Starting LLM-guided planning session...")
        
        # Run planning session
        session_results = agent.run_planning_session(patient_file, max_iterations=200)
        
        print("\n" + "=" * 50)
        print("📋 PLANNING SESSION RESULTS")
        print("=" * 50)
        
        if session_results["success"]:
            print(f"✅ Planning completed successfully!")
            print(f"🔄 Iterations: {session_results['iterations_completed']}")
            print(f"💬 Messages: {session_results['messages_exchanged']}")
            
            final_state = session_results["final_state"]
            print(f"\n📈 Final Plan State:")
            for key, value in final_state.items():
                if key == "objectives_added":
                    print(f"  {key}: {len(value)} objectives")
                    for i, obj in enumerate(value):
                        print(f"    {i+1}. {obj['structure']}: {obj['type']} = {obj['dose']} Gy")
                else:
                    print(f"  {key}: {value}")
        else:
            print("❌ Planning session failed")
        
        # Print log summary
        agent.logger.print_log_summary()
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        
    finally:
        # Clean up
        try:
            if 'agent' in locals():
                agent.engine.stop_engine()
                print("\n🛑 MATLAB engine stopped")
        except:
            pass
        
        print("\n🏁 Test completed")


if __name__ == "__main__":
    main() 