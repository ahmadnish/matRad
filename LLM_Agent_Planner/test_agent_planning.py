"""
Test script for LLM Agent-based IMRT Planning using OpenAI Agents SDK

This script demonstrates how an LLM agent can make autonomous decisions
to create and iteratively improve an IMRT treatment plan using matRad tools.
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

# Pydantic models for structured outputs
class ToolResult(BaseModel):
    """Base model for tool execution results."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    execution_time_sec: Optional[float] = None

class PatientInfo(BaseModel):
    """Model for patient loading results."""
    success: bool
    patient_file: Optional[str] = None
    ct_dimensions: Optional[List[int]] = None
    num_structures: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None

class StructureInfo(BaseModel):
    """Model for structure information."""
    success: bool
    targets: Optional[List[str]] = None
    oars: Optional[List[str]] = None
    other: Optional[List[str]] = None
    error: Optional[str] = None

class PlanInfo(BaseModel):
    """Model for treatment plan information."""
    success: bool
    radiation_mode: Optional[str] = None
    num_fractions: Optional[int] = None
    num_beams: Optional[int] = None
    gantry_angles: Optional[List[float]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class BeamGeometryInfo(BaseModel):
    """Model for beam geometry results."""
    success: bool
    num_beams: Optional[int] = None
    total_bixels: Optional[int] = None
    beam_info: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class DoseMatrixInfo(BaseModel):
    """Model for dose influence matrix results."""
    success: bool
    dimensions: Optional[List[int]] = None
    num_voxels: Optional[int] = None
    calc_time_sec: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None

class ObjectiveInfo(BaseModel):
    """Model for optimization objective results."""
    success: bool
    structure: Optional[str] = None
    objective_type: Optional[str] = None
    dose_value: Optional[float] = None
    penalty: Optional[float] = None
    total_objectives: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None

class OptimizationInfo(BaseModel):
    """Model for optimization results."""
    success: bool
    optimization_time_sec: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None

class StructureMetric(BaseModel):
    """Model for individual structure metrics."""
    name: str
    type: str
    mean_dose: float
    max_dose: float
    min_dose: float
    std_dose: float
    V5: float
    V10: float
    V20: float

class PlanEvaluationInfo(BaseModel):
    """Model for plan evaluation results."""
    success: bool
    structure_metrics: Optional[List[StructureMetric]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class DVHInfo(BaseModel):
    """Model for DVH calculation results."""
    success: bool
    structure: Optional[str] = None
    dvh_values: Optional[List[float]] = None
    bin_centers: Optional[List[float]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class SaveInfo(BaseModel):
    """Model for plan saving results."""
    success: bool
    output_file: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

class PlanState(BaseModel):
    """Model for current plan state."""
    success: bool = True
    plan_state: Dict[str, Any]

class StructuredDecisionLog(BaseModel):
    """Model for structured decision logging by the LLM agent."""
    success: bool = True
    reason: str = Field(description="Explanation of the decision being made")
    tool_used: Optional[str] = Field(None, description="Name of the matRad function being invoked")
    inputs: Optional[Dict[str, Any]] = Field(None, description="Parameters being given to the tool")
    expected_outcome: Optional[str] = Field(None, description="Expected results from this action")
    next_action: str = Field(description="Planned next step in the treatment planning process")
    clinical_rationale: Optional[str] = Field(None, description="Clinical reasoning behind this decision")

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
                    "name": "add_optimization_objective",
                    "description": "Add an optimization objective for a structure.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure"
                            },
                            "objective_type": {
                                "type": "string",
                                "enum": ["min_dose", "max_dose", "mean_dose", "square_deviation"],
                                "description": "Type of objective"
                            },
                            "dose_value": {
                                "type": "number",
                                "description": "Dose value in Gy"
                            },
                            "penalty": {
                                "type": "number",
                                "description": "Penalty weight (default 1000)"
                            }
                        },
                        "required": ["structure_name", "objective_type", "dose_value"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_fluence",
                    "description": "Run fluence optimization based on current objectives.",
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
                    "description": "Calculate DVH for a specific structure or all structures.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of structure (optional, if not provided calculates for all)"
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
                    "name": "log_decision_reasoning",
                    "description": "Log structured reasoning for planning decisions. Use this to explain why you're taking specific actions, what you expect to achieve, and what you plan to do next. This should be called before major planning steps.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Clear explanation of why this decision is being made"
                            },
                            "tool_used": {
                                "type": "string",
                                "description": "Name of the matRad function about to be invoked (if applicable)"
                            },
                            "inputs": {
                                "type": "object",
                                "description": "Parameters that will be given to the tool (if applicable)"
                            },
                            "expected_outcome": {
                                "type": "string",
                                "description": "What you expect this action to achieve"
                            },
                            "next_action": {
                                "type": "string",
                                "description": "What you plan to do after this step"
                            },
                            "clinical_rationale": {
                                "type": "string",
                                "description": "Clinical reasoning behind this decision (if applicable)"
                            }
                        },
                        "required": ["reason", "next_action"],
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
                
            elif tool_name == "add_optimization_objective":
                result_dict = self.engine.add_optimization_objective(
                    arguments["structure_name"],
                    arguments["objective_type"],
                    arguments["dose_value"],
                    arguments.get("penalty", 1000.0)
                )
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    objective_info = {
                        "structure": arguments["structure_name"],
                        "type": arguments["objective_type"],
                        "dose": arguments["dose_value"]
                    }
                    self.plan_state["objectives_added"].append(objective_info)
                    
                    # Log the objective
                    self.logger.log_objective(
                        arguments["structure_name"],
                        arguments["objective_type"],
                        arguments["dose_value"],
                        arguments.get("penalty", 1000.0)
                    )
                
            elif tool_name == "optimize_fluence":
                result_dict = self.engine.optimize_fluence()
                result_dict = convert_matlab_types(result_dict)
                if result_dict.get("success"):
                    self.plan_state["optimization_completed"] = True
                    self.plan_state["iteration_count"] += 1
                    
                    # Log optimization result
                    execution_time = time.time() - start_time
                    self.logger.log_optimization_result(
                        self.plan_state["iteration_count"],
                        {"optimization_successful": True},
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
                
            elif tool_name == "log_decision_reasoning":
                # This tool allows the LLM to provide structured reasoning
                reasoning_log = {
                    "reason": arguments["reason"],
                    "next_action": arguments["next_action"],
                    "tool_used": arguments.get("tool_used"),
                    "inputs": arguments.get("inputs"),
                    "expected_outcome": arguments.get("expected_outcome"),
                    "clinical_rationale": arguments.get("clinical_rationale")
                }
                
                # Log this reasoning using the existing logger
                self.logger.log_action(
                    "llm_reasoning",
                    "LLM provided structured decision reasoning",
                    {},
                    reasoning_log
                )
                
                result_dict = {
                    "success": True, 
                    "message": f"Logged reasoning: {arguments['reason']}",
                    "reasoning_logged": reasoning_log
                }
                
                # Print the reasoning for immediate visibility
                print(f"\n🧠 Agent Reasoning:")
                print(f"   Why: {arguments['reason']}")
                if arguments.get("clinical_rationale"):
                    print(f"   Clinical: {arguments['clinical_rationale']}")
                if arguments.get("tool_used"):
                    print(f"   Next Tool: {arguments['tool_used']}")
                if arguments.get("expected_outcome"):
                    print(f"   Expected: {arguments['expected_outcome']}")
                print(f"   Then: {arguments['next_action']}")
                
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
            if isfield(pln, 'propOpt') && isfield(pln.propOpt, 'optimizer') && strcmp(pln.propOpt.optimizer, 'fmincon')
                
                % Set more relaxed tolerances to prevent early stopping
                pln.propOpt.fmincon.StepTolerance = 1e-4;           % Increase from default 1e-10
                pln.propOpt.fmincon.ConstraintTolerance = 1e-3;     % Increase from default 1e-6
                pln.propOpt.fmincon.OptimalityTolerance = 1e-3;     % Increase from default 1e-6
                pln.propOpt.fmincon.FunctionTolerance = 1e-4;       % Increase from default 1e-6
                
                % Increase iteration limits
                pln.propOpt.fmincon.MaxIterations = 200;            % Increase from default
                pln.propOpt.fmincon.MaxFunctionEvaluations = 400;   % Increase from default
                
                % Enable detailed display
                pln.propOpt.fmincon.Display = 'iter';
                
                disp('✅ Configured fmincon tolerances to prevent early stopping:');
                disp(['   StepTolerance: ' num2str(pln.propOpt.fmincon.StepTolerance)]);
                disp(['   ConstraintTolerance: ' num2str(pln.propOpt.fmincon.ConstraintTolerance)]);
                disp(['   OptimalityTolerance: ' num2str(pln.propOpt.fmincon.OptimalityTolerance)]);
                disp(['   FunctionTolerance: ' num2str(pln.propOpt.fmincon.FunctionTolerance)]);
                disp(['   MaxIterations: ' num2str(pln.propOpt.fmincon.MaxIterations)]);
                
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
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad.

            Your goal is to create an optimal treatment plan that achieves target coverage while minimizing dose to organs at risk (OARs), following clinical best practices. You have access to tools for beam setup, dose calculation, optimization, and plan evaluation.

            CRITICAL: You MUST use the 'log_decision_reasoning' tool before every major planning step to explain your thought process, clinical rationale, and planning strategy. This is mandatory for transparency and clinical validation.

            Planning Process:
            1. Start by logging your overall planning strategy using log_decision_reasoning
            2. Start the MATLAB engine and load patient data.
            3. Examine the structure information to identify targets and OARs.
            4. Log your beam angle selection strategy, then create an initial treatment plan with appropriate beam angles.
            5. Generate the beam geometry and calculate the dose influence matrix.
            6. Log your objective selection rationale, then add optimization objectives for targets and OARs, based on clinical guidelines.
            7. Optimize the plan and evaluate quality.
            8. Then iteratively:
            - Use evaluation tools to assess plan quality and check for any unmet clinical objectives.
            - If the plan is suboptimal, use log_decision_reasoning to document:
                - Why the plan is suboptimal (e.g., PTV D95 too low, OAR dose too high)
                - Key metrics (e.g., D95, Dmax, HI, CI)
                - Your rationale for improvement
                - What specific changes you will make
            - Based on this rationale, adjust or add optimization objectives using the appropriate tool.
            - Re-optimize the plan and re-evaluate.
            - Log your assessment after each iteration.
            - Repeat this loop until either clinical criteria are met, plan quality plateaus, or the maximum number of iterations is reached.
            - If optimal, save the plan and exit.
            - If not, summarize the steps taken and restart from step 3 using different beam angles or objective functions.

            Clinical Guidelines:
            - Target structures (PTVs) should receive 95% of the prescribed dose (typically 50–70 Gy).
            - OARs should remain below tolerance doses per QUANTEC guidelines.
            - Dose values in objective functions are total dose over all fractions; per-fraction doses apply for plan evaluation.
            - Use appropriate beam arrangements: typically 5–9 beams for H&N cases.
            - Prioritize in case of conflict:
                - 1st: PTV coverage
                - 2nd: Critical OAR sparing
                - 3rd: Non-critical structure sparing
            - Acceptable plan thresholds:
                - PTV D95 ≥ 95% of prescription
                - Homogeneity Index (HI) < 0.2
                - Conformity Index (CI) > 0.7
                - OAR doses below maximum and mean tolerances


            Termination Conditions:
            - A plan is optimal if all clinical thresholds are met.
            - Do not iterate further if:
            - Plan quality plateaus over 2 iterations
            - All objective changes result in equivalent or worse tradeoffs
            - Do not re-run dose calculation unless:
            - Beam geometry or optimization objectives change
            - Limit re-optimization to a maximum of 5 iterations, unless a >3% improvement in key metrics is expected.

            Structured Decision Logging (MANDATORY):
            You MUST call 'log_decision_reasoning' before each major step to document:
            - "reason": Clear explanation of why you're taking this action
            - "tool_used": The specific matRad function you're about to call
            - "inputs": The parameters you'll provide to that function
            - "expected_outcome": What you expect this action to achieve
            - "next_action": What you plan to do after this step
            - "clinical_rationale": Clinical justification for your decision

            Examples of when to log:
            - Before starting the planning process (overall strategy)
            - Before selecting beam angles (geometric rationale)
            - Before adding optimization objectives (clinical rationale)
            - After evaluating plan quality (assessment and next steps)
            - Before making any adjustments (improvement strategy)

            Current patient file: {patient_file}  
            Maximum iterations allowed: {max_iterations}

            Start by using log_decision_reasoning to explain your overall planning approach, then get the current plan state and proceed step by step.  
            Always ensure your function calls use valid JSON-serializable parameters.
        """
        
        # Start conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": "Please start the IMRT planning process for this patient."})
        
        iteration = 0
        while iteration < max_iterations:
            try:
                # Get LLM response with function calling
                response = client.chat.completions.create(
                    model="o3",
                    messages=messages,
                    tools=self.get_available_tools(),
                    tool_choice="auto"
                )
                
                # Add assistant message
                assistant_message = response.choices[0].message
                messages.append(assistant_message.model_dump())
                
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
                    
                    # Check if planning is complete
                    if "complete" in assistant_message.content.lower() or "finished" in assistant_message.content.lower():
                        break
                        
                    # Ask for next step
                    messages.append({"role": "user", "content": "What should we do next?"})
                
                iteration += 1
                
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
    patient_file = "HEAD_AND_NECK.mat"  # Adjust based on available patient data
    
    try:
        # Create planning agent
        agent = IMRTPlanningAgent(matrad_path)
        
        print(f"📊 Patient file: {patient_file}")
        print(f"🏥 matRad path: {matrad_path}")
        print(f"📁 Session ID: {agent.logger.session_id}")
        print("\n🤖 Starting LLM-guided planning session...")
        
        # Run planning session
        session_results = agent.run_planning_session(patient_file, max_iterations=10)
        
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