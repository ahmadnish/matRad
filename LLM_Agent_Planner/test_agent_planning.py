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
                        "required": ["structure_name", "objective_type", "dose_value", "penalty"],
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

            Planning Process:
            1. Start the MATLAB engine and load patient data.
            2. Examine the structure information to identify targets and OARs.
            3. Create an initial treatment plan with appropriate beam angles.
            4. Generate the beam geometry and calculate the dose influence matrix.
            5. Add optimization objectives for targets and OARs, based on clinical guidelines.
            6. Optimize the plan and evaluate quality.
            7. Then iteratively:
            - Use evaluate_plan_quality() to assess overall plan quality and get comprehensive clinical assessment for all structures
            - If the plan is suboptimal, log:
                - Why the plan is suboptimal (e.g., PTV D95 too low, OAR dose too high)
                - Key metrics from plan evaluation (D95, D50, D2, D98, V-metrics, HI, CI)
                - Clinical assessment from the plan evaluation text
                - Plan quality score and recommendations
                - Your rationale for improvement
            - Based on this rationale, adjust or add optimization objectives using the appropriate tool.
            - Re-optimize the plan and re-evaluate. 
            - After each optimization, save the plan via save_treatment_plan with corresponding iteration number.
            - Repeat this loop until either clinical criteria are met, plan quality plateaus, or the maximum number of iterations is reached.
            - If optimal, save the plan and exit.
            - If not, summarize the steps taken and restart from step 3 using different objective functions (preferable; Keep an eye on the already added objectives), beam angles, or even more impinging angles.

            Optimization Strategy:
            - For the first optimization: Use optimize_fluence() without parameters (cold-start from default weights)
            - For subsequent optimizations: Use optimize_fluence(use_previous_weights=true) to warm-start from previous results
            - Warm-start optimization typically converges faster and may find better local optima
            - The system automatically stores optimized weights after each successful optimization
            - Use warm-start when refining objectives or making incremental improvements
            - Use cold-start only when making major changes to beam configuration or starting fresh

            ## Treatment Plan Evaluation Tools

            **For comprehensive plan evaluation, use `evaluate_plan_quality()`:**
            - This is your PRIMARY tool for overall plan assessment
            - Provides complete quality indicators, DVH analysis, and clinical recommendations for all structures
            - Use this for plan approval/rejection decisions and comparing different plans
            - Returns plan-level quality scoring and comprehensive clinical assessment
            - Includes matRad's official quality indicators (D95, D50, HI, CI, V-metrics, etc.)

            **For focused structure analysis, use `calculate_dvh_analysis(structure_name)`:**
            - Use this ONLY when you need detailed analysis of a specific structure
            - For follow-up investigation after comprehensive evaluation
            - When you need structure-specific DVH plots or deep-dive analysis

            **AVOID calling both methods redundantly** - `evaluate_plan_quality()` already includes comprehensive DVH analysis for all structures.

            Clinical Guidelines:
            - Target structures (PTVs) should receive 95% of the prescribed dose (typically 50–70 Gy).
            - OARs should remain below tolerance doses per following guidelines:
                - Parotid: 25 Gy
                - Mandible: 26 Gy
                - Spinal Cord: 25 Gy
                - Optic Nerve: 35 Gy
                - Brainstem: 35 Gy
                - Larynx: 35 Gy
            - Keep a 30 Gy max dose for the "BODY" structure (or the "Skin" structure).
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


            Plan Evaluation Workflow:
            1. Primary: Use evaluate_plan_quality() for comprehensive plan assessment (all structures, quality scoring, clinical recommendations)
            2. Optional: Use calculate_dvh_analysis(structure_name) only for focused analysis of specific structures if needed

            Termination Conditions:
            - A plan is optimal if all clinical thresholds are met (use plan evaluation metrics to verify).
            - Do not iterate further if:
                - Plan quality plateaus over 5 iterations (compare plan quality scores and key metrics)
                - All objective changes result in equivalent or worse tradeoffs
            - Do not re-run dose calculation unless beam geometry or machine parameters change.

            Logging (Structured):
            Each planning decision should be logged in a structured JSON format with:
            - "reason": Explanation of the decision
            - "tool_used": Name of the matRad function invoked
            - "inputs": Parameters given to the tool
            - "outcome": Metrics after action from plan evaluation (e.g., D95 = 93.2%, HI = 0.15, Parotid Dmean = 26.1 Gy, V30Gy = 45%)
            - "clinical_assessment": Key findings from plan assessment text
            - "next_action": Planned next step

            Current patient file: {patient_file}  
            Maximum iterations allowed: {max_iterations}

            Key Quality Metrics to Monitor (from evaluate_plan_quality):
            - Targets: D95 (coverage), D50 (median), CI (conformity), HI (homogeneity)
            - OARs: max_dose, mean_dose, V30Gy, V20Gy (volume metrics)
            - All: std_dose (dose uniformity), D2/D98 (dose extremes)
            - Plan-level: quality score (0-100), clinical recommendations

            Start by getting the current plan state and then proceed step by step.  
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
                    
                    # Check if planning is complete
                    if "complete" in assistant_message.content.lower() or "finished" in assistant_message.content.lower():
                        break
                        
                    # Ask for next step
                    messages.append({"role": "user", "content": "What should we do next?"})
                
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
    patient_file = "HandN_4Agent_noconstraints.mat"  # Adjust based on available patient data
    #patient_file = "HEAD_AND_NECK.mat"
    
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