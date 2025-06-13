"""
Test script for LLM Agent-based IMRT Planning using OpenAI Agents SDK

This script demonstrates how an LLM agent can make autonomous decisions
to create and iteratively improve an IMRT treatment plan using matRad tools.
"""

import os
import json
import time
from typing import Dict, Any, List
from openai import OpenAI
from matrad_tools import MatRadEngine
from logger import PlanningLogger

# Initialize OpenAI client
client = OpenAI()

class IMRTPlanningAgent:
    """LLM Agent for IMRT Planning using OpenAI function calling."""
    
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
        """Define the tools available to the LLM agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "start_matlab_engine",
                    "description": "Start the MATLAB engine and initialize matRad. Must be called first.",
                    "parameters": {"type": "object", "properties": {}}
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
                            "patient_file": {"type": "string", "description": "Path to patient .mat file"}
                        },
                        "required": ["patient_file"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_structure_information",
                    "description": "Get information about structures (targets, OARs) in the loaded patient.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_treatment_plan",
                    "description": "Create an empty treatment plan with default settings.",
                    "parameters": {"type": "object", "properties": {}}
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
                            "gantry_angles": {"type": "array", "items": {"type": "number"}, "description": "List of gantry angles in degrees"},
                            "couch_angles": {"type": "array", "items": {"type": "number"}, "description": "List of couch angles in degrees (optional)"}
                        },
                        "required": ["gantry_angles"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_beam_geometry",
                    "description": "Generate beam geometry (stf) based on the current plan.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_dose_influence_matrix",
                    "description": "Calculate the dose influence matrix. This is computationally intensive.",
                    "parameters": {"type": "object", "properties": {}}
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
                            "structure_name": {"type": "string", "description": "Name of the structure"},
                            "objective_type": {"type": "string", "enum": ["min_dose", "max_dose", "mean_dose", "square_deviation"], "description": "Type of objective"},
                            "dose_value": {"type": "number", "description": "Dose value in Gy"},
                            "penalty": {"type": "number", "description": "Penalty weight (default 1000)"}
                        },
                        "required": ["structure_name", "objective_type", "dose_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_fluence",
                    "description": "Run fluence optimization based on current objectives.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_plan_quality",
                    "description": "Evaluate the current plan and calculate metrics for all structures.",
                    "parameters": {"type": "object", "properties": {}}
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
                            "structure_name": {"type": "string", "description": "Name of structure (optional, if not provided calculates for all)"}
                        }
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
                            "output_file": {"type": "string", "description": "Path to save the plan"}
                        },
                        "required": ["output_file"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plan_state",
                    "description": "Get the current state of the planning process.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a tool function and return the result."""
        start_time = time.time()
        
        try:
            if tool_name == "start_matlab_engine":
                result = self.engine.start_engine()
                self.plan_state["engine_started"] = result
                result_dict = {"success": result, "message": "MATLAB engine started" if result else "Failed to start MATLAB engine"}
                
            elif tool_name == "load_patient_data":
                result_dict = self.engine.load_patient(arguments["patient_file"])
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
                
            elif tool_name == "create_treatment_plan":
                result_dict = self.engine.create_empty_plan()
                if result_dict.get("success"):
                    self.plan_state["plan_created"] = True
                
            elif tool_name == "set_beam_configuration":
                result_dict = self.engine.set_beam_angles(
                    arguments["gantry_angles"], 
                    arguments.get("couch_angles")
                )
                
            elif tool_name == "generate_beam_geometry":
                result_dict = self.engine.generate_beam_geometry()
                if result_dict.get("success"):
                    self.plan_state["beam_geometry_generated"] = True
                
            elif tool_name == "calculate_dose_influence_matrix":
                result_dict = self.engine.calculate_influence_matrix()
                if result_dict.get("success"):
                    self.plan_state["influence_matrix_calculated"] = True
                
            elif tool_name == "add_optimization_objective":
                result_dict = self.engine.add_optimization_objective(
                    arguments["structure_name"],
                    arguments["objective_type"],
                    arguments["dose_value"],
                    arguments.get("penalty", 1000.0)
                )
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
                if result_dict.get("success"):
                    self.plan_state["plan_evaluated"] = True
                    
                    # Log plan metrics
                    if "structure_metrics" in result_dict:
                        self.logger.log_plan_metrics(result_dict["structure_metrics"])
                
            elif tool_name == "calculate_dvh_analysis":
                result_dict = self.engine.calculate_dvh(arguments.get("structure_name"))
                
            elif tool_name == "save_treatment_plan":
                result_dict = self.engine.save_plan(arguments["output_file"])
                
            elif tool_name == "get_plan_state":
                result_dict = {"success": True, "plan_state": self.plan_state}
                
            else:
                result_dict = {"success": False, "error": f"Unknown tool: {tool_name}"}
            
            # Log the action
            execution_time = time.time() - start_time
            self.logger.log_action(
                "tool_call",
                f"Executed {tool_name}",
                arguments,
                {**result_dict, "execution_time_sec": execution_time}
            )
            
            return result_dict
                
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            execution_time = time.time() - start_time
            
            # Log the error
            self.logger.log_action(
                "tool_error",
                f"Error executing {tool_name}",
                arguments,
                {**error_result, "execution_time_sec": execution_time}
            )
            
            return error_result
    
    def run_planning_session(self, patient_file: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Run a complete planning session with the LLM agent.
        
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
        You are an expert radiation therapy planning agent. Your goal is to create an optimal IMRT treatment plan.
        
        Planning Process:
        1. Start MATLAB engine and load patient data
        2. Examine structure information to understand targets and OARs
        3. Create initial treatment plan with appropriate beam angles
        4. Generate beam geometry and calculate dose influence matrix
        5. Add optimization objectives for targets and OARs based on clinical guidelines
        6. Optimize the plan and evaluate quality
        7. If needed, iteratively improve by adjusting objectives and re-optimizing
        
        Clinical Guidelines:
        - Target structures should receive prescribed dose (typically 50-70 Gy)
        - OARs should be kept below tolerance doses
        - Use appropriate beam arrangements (typically 5-9 beams for H&N)
        - Balance target coverage with OAR sparing
        
        Current patient file: {patient_file}
        Maximum iterations allowed: {max_iterations}
        
        Start by getting the current plan state and then proceed step by step.
        """
        
        # Start conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": "Please start the IMRT planning process for this patient."})
        
        iteration = 0
        while iteration < max_iterations:
            try:
                # Get LLM response with function calling
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    tools=self.get_available_tools(),
                    tool_choice="auto",
                    temperature=0.1
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
                        
                        # Add tool result to conversation
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
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
        final_state = self.plan_state.copy()
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