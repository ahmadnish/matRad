"""
Simple LLM Agent Demo for IMRT Planning

This script demonstrates the LLM agent workflow without requiring OpenAI API access.
It simulates how an intelligent agent would make decisions to create and improve an IMRT plan.
"""

import time
from typing import Dict, Any, List
from matrad_tools import MatRadEngine
from logger import PlanningLogger


class SimpleIMRTAgent:
    """Simplified IMRT Planning Agent that simulates LLM decision making."""
    
    def __init__(self, matrad_path: str = None):
        """Initialize the planning agent."""
        self.engine = MatRadEngine(matrad_path)
        self.logger = PlanningLogger()
        self.plan_state = {
            "engine_started": False,
            "patient_loaded": False,
            "structures": {},
            "plan_created": False,
            "beam_geometry_generated": False,
            "influence_matrix_calculated": False,
            "objectives_added": [],
            "optimization_completed": False,
            "plan_evaluated": False,
            "iteration_count": 0
        }
        
        print("🤖 Simple IMRT Planning Agent initialized")
        self.logger.log_action("initialization", "Simple agent initialized", 
                              {"matrad_path": matrad_path})
    
    def simulate_agent_decision(self, context: str) -> str:
        """Simulate agent decision making based on current context."""
        print(f"\n🧠 Agent thinking: {context}")
        time.sleep(1)  # Simulate thinking time
        return "Agent has analyzed the situation and determined the next action."
    
    def run_planning_workflow(self, patient_file: str) -> Dict[str, Any]:
        """
        Run the complete IMRT planning workflow with simulated agent decisions.
        
        Args:
            patient_file: Path to patient data file
            
        Returns:
            Dict with workflow results
        """
        print("\n" + "=" * 60)
        print("🚀 STARTING LLM AGENT IMRT PLANNING WORKFLOW")
        print("=" * 60)
        
        try:
            # Step 1: Initialize MATLAB Engine
            print("\n📍 STEP 1: Initialize MATLAB Engine")
            self.simulate_agent_decision("Need to start MATLAB engine to access matRad functionality")
            
            result = self.engine.start_engine()
            if result:
                self.plan_state["engine_started"] = True
                print("✅ MATLAB engine started successfully")
                self.logger.log_action("engine_start", "MATLAB engine started", {}, {"success": True})
            else:
                print("❌ Failed to start MATLAB engine")
                return {"success": False, "error": "MATLAB engine failed to start"}
            
            # Step 2: Load Patient Data
            print("\n📍 STEP 2: Load Patient Data")
            self.simulate_agent_decision(f"Loading patient data from {patient_file}")
            
            result = self.engine.load_patient(patient_file)
            if result.get("success"):
                self.plan_state["patient_loaded"] = True
                print(f"✅ Patient data loaded: {result.get('ct_dimensions')} voxels, {result.get('num_structures')} structures")
                self.logger.log_patient_info({
                    "patient_file": patient_file,
                    "ct_dimensions": result.get("ct_dimensions"),
                    "num_structures": result.get("num_structures")
                })
            else:
                print(f"❌ Failed to load patient: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
            # Step 3: Analyze Structures
            print("\n📍 STEP 3: Analyze Structure Information")
            self.simulate_agent_decision("Analyzing anatomy structures to understand targets and organs at risk")
            
            structures = self.engine.get_structure_names()
            if structures.get("success"):
                self.plan_state["structures"] = structures
                print(f"✅ Structure analysis complete:")
                print(f"   🎯 Targets: {structures.get('targets', [])}")
                print(f"   ⚠️  OARs: {structures.get('oars', [])}")
                print(f"   📋 Other: {structures.get('other', [])}")
            else:
                print(f"❌ Failed to get structures: {structures.get('error')}")
                return {"success": False, "error": structures.get("error")}
            
            # Step 4: Create Treatment Plan
            print("\n📍 STEP 4: Create Initial Treatment Plan")
            self.simulate_agent_decision("Creating treatment plan with appropriate beam configuration for this anatomy")
            
            result = self.engine.create_empty_plan()
            if result.get("success"):
                self.plan_state["plan_created"] = True
                print(f"✅ Treatment plan created: {result.get('num_beams')} beams, {result.get('num_fractions')} fractions")
            else:
                print(f"❌ Failed to create plan: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
            # Step 5: Optimize Beam Angles (Agent Decision)
            print("\n📍 STEP 5: Optimize Beam Arrangement")
            targets = structures.get('targets', [])
            if 'HEAD_AND_NECK' in patient_file.upper() or any('PTV' in t.upper() for t in targets):
                self.simulate_agent_decision("Detected head & neck case - using 7-field IMRT arrangement")
                beam_angles = [0, 51, 102, 153, 204, 255, 306]
            else:
                self.simulate_agent_decision("Using standard 5-field arrangement for this case")
                beam_angles = [0, 72, 144, 216, 288]
            
            result = self.engine.set_beam_angles(beam_angles)
            if result.get("success"):
                print(f"✅ Beam angles set: {beam_angles}")
            else:
                print(f"❌ Failed to set beams: {result.get('error')}")
            
            # Step 6: Generate Beam Geometry
            print("\n📍 STEP 6: Generate Beam Geometry")
            self.simulate_agent_decision("Generating detailed beam geometry and bixel structure")
            
            result = self.engine.generate_beam_geometry()
            if result.get("success"):
                self.plan_state["beam_geometry_generated"] = True
                print(f"✅ Beam geometry generated: {result.get('total_bixels')} total bixels")
            else:
                print(f"❌ Failed to generate geometry: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
            # Step 7: Calculate Dose Influence Matrix
            print("\n📍 STEP 7: Calculate Dose Influence Matrix")
            self.simulate_agent_decision("Calculating dose influence matrix - this will take some time")
            
            start_time = time.time()
            result = self.engine.calculate_influence_matrix()
            calc_time = time.time() - start_time
            
            if result.get("success"):
                self.plan_state["influence_matrix_calculated"] = True
                print(f"✅ Dose influence matrix calculated in {calc_time:.1f} seconds")
                print(f"   Matrix dimensions: {result.get('dimensions')}")
            else:
                print(f"❌ Failed to calculate matrix: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
            # Step 8: Add Optimization Objectives (Agent Intelligence)
            print("\n📍 STEP 8: Add Optimization Objectives")
            self.simulate_agent_decision("Analyzing structures to determine appropriate dose objectives")
            
            objectives_added = 0
            
            # Add target objectives
            for target in structures.get('targets', []):
                if 'PTV' in target.upper() or 'TARGET' in target.upper():
                    dose = 60.0 if 'HIGH' in target.upper() else 50.0
                    self.simulate_agent_decision(f"Setting target dose of {dose} Gy for {target}")
                    
                    result = self.engine.add_optimization_objective(target, "square_deviation", dose, 1000)
                    if result.get("success"):
                        objectives_added += 1
                        print(f"✅ Added target objective: {target} = {dose} Gy")
                        self.logger.log_objective(target, "square_deviation", dose, 1000)
            
            # Add OAR objectives
            oar_constraints = {
                'BRAINSTEM': {'type': 'max_dose', 'dose': 54.0},
                'SPINALCORD': {'type': 'max_dose', 'dose': 45.0},
                'PAROTID': {'type': 'mean_dose', 'dose': 26.0},
                'LENS': {'type': 'max_dose', 'dose': 25.0},
                'OPTIC': {'type': 'max_dose', 'dose': 55.0},
                'CHIASM': {'type': 'max_dose', 'dose': 55.0}
            }
            
            for oar in structures.get('oars', []):
                for constraint_name, constraint in oar_constraints.items():
                    if constraint_name in oar.upper():
                        self.simulate_agent_decision(f"Adding {constraint['type']} constraint for {oar}")
                        
                        result = self.engine.add_optimization_objective(
                            oar, constraint['type'], constraint['dose'], 1000
                        )
                        if result.get("success"):
                            objectives_added += 1
                            print(f"✅ Added OAR constraint: {oar} {constraint['type']} = {constraint['dose']} Gy")
                            self.logger.log_objective(oar, constraint['type'], constraint['dose'], 1000)
                        break
            
            print(f"\n📊 Total objectives added: {objectives_added}")
            
            # Step 9: Initial Optimization
            print("\n📍 STEP 9: Run Initial Optimization")
            self.simulate_agent_decision("Running fluence optimization with current objectives")
            
            start_time = time.time()
            result = self.engine.optimize_fluence()
            opt_time = time.time() - start_time
            
            if result.get("success"):
                self.plan_state["optimization_completed"] = True
                self.plan_state["iteration_count"] = 1
                print(f"✅ Initial optimization completed in {opt_time:.1f} seconds")
                self.logger.log_optimization_result(1, {"optimization_successful": True}, opt_time)
            else:
                print(f"❌ Optimization failed: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
            
            # Step 10: Evaluate Plan Quality
            print("\n📍 STEP 10: Evaluate Plan Quality")
            self.simulate_agent_decision("Analyzing plan quality and dose metrics")
            
            result = self.engine.evaluate_plan()
            if result.get("success"):
                self.plan_state["plan_evaluated"] = True
                metrics = result.get("structure_metrics", [])
                print(f"✅ Plan evaluation completed - {len(metrics)} structures analyzed")
                
                # Display key metrics
                for metric in metrics[:5]:  # Show first 5 structures
                    name = metric.get('name', 'Unknown')
                    mean_dose = metric.get('mean_dose', 0)
                    max_dose = metric.get('max_dose', 0)
                    print(f"   📊 {name}: Mean={mean_dose:.1f} Gy, Max={max_dose:.1f} Gy")
                
                self.logger.log_plan_metrics(metrics)
            else:
                print(f"❌ Plan evaluation failed: {result.get('error')}")
            
            # Step 11: Agent Analysis and Potential Improvements
            print("\n📍 STEP 11: Agent Analysis for Improvements")
            self.simulate_agent_decision("Analyzing plan metrics to determine if improvements are needed")
            
            improvements_needed = False
            
            # Simple heuristic: check if any OAR exceeds constraints
            if result.get("success"):
                for metric in result.get("structure_metrics", []):
                    if metric.get('type') == 'OAR':
                        mean_dose = metric.get('mean_dose', 0)
                        if mean_dose > 30:  # Simple threshold
                            improvements_needed = True
                            print(f"⚠️  {metric.get('name')} may need dose reduction (current: {mean_dose:.1f} Gy)")
            
            if improvements_needed:
                print("\n📍 STEP 12: Iterative Improvement")
                self.simulate_agent_decision("Adding stricter constraints for problematic structures")
                
                # Example: Add stricter constraint
                for oar in structures.get('oars', []):
                    if 'PAROTID' in oar.upper():
                        result = self.engine.add_optimization_objective(oar, "mean_dose", 20.0, 2000)
                        if result.get("success"):
                            print(f"✅ Added stricter constraint: {oar} mean ≤ 20 Gy")
                
                # Re-optimize
                self.simulate_agent_decision("Re-optimizing with improved objectives")
                start_time = time.time()
                result = self.engine.optimize_fluence()
                opt_time = time.time() - start_time
                
                if result.get("success"):
                    self.plan_state["iteration_count"] = 2
                    print(f"✅ Improved optimization completed in {opt_time:.1f} seconds")
                    self.logger.log_optimization_result(2, {"optimization_successful": True}, opt_time)
                    
                    # Re-evaluate
                    result = self.engine.evaluate_plan()
                    if result.get("success"):
                        print("✅ Plan re-evaluated after improvements")
            else:
                print("✅ Plan quality is acceptable - no improvements needed")
            
            # Step 13: Save Plan
            print("\n📍 STEP 13: Save Final Plan")
            output_file = f"optimized_plan_{int(time.time())}.mat"
            self.simulate_agent_decision(f"Saving final plan to {output_file}")
            
            result = self.engine.save_plan(output_file)
            if result.get("success"):
                print(f"✅ Plan saved to {output_file}")
            else:
                print(f"⚠️  Could not save plan: {result.get('error')}")
            
            # Final Results
            final_results = {
                "success": True,
                "objectives_added": objectives_added,
                "optimization_iterations": self.plan_state["iteration_count"],
                "plan_evaluated": self.plan_state["plan_evaluated"],
                "output_file": output_file if result.get("success") else None
            }
            
            self.logger.log_final_results(final_results)
            
            return final_results
            
        except Exception as e:
            error_msg = f"Fatal error in planning workflow: {str(e)}"
            print(f"❌ {error_msg}")
            self.logger.log_action("workflow_error", error_msg, {}, {"error": str(e)})
            return {"success": False, "error": str(e)}
        
        finally:
            try:
                self.engine.stop_engine()
                print("\n🛑 MATLAB engine stopped")
            except:
                pass


def main():
    """Main function to run the simple agent demo."""
    print("🤖 Simple LLM Agent IMRT Planning Demo")
    print("=" * 60)
    
    # Configuration
    matrad_path = "/Users/ahmadneishabouri/matRad"  # Update this path
    patient_file = "HEAD_AND_NECK.mat"  # Adjust based on available data
    
    try:
        # Create agent
        agent = SimpleIMRTAgent(matrad_path)
        
        print(f"📊 Patient file: {patient_file}")
        print(f"🏥 matRad path: {matrad_path}")
        print(f"📁 Session ID: {agent.logger.session_id}")
        
        # Run workflow
        results = agent.run_planning_workflow(patient_file)
        
        # Display results
        print("\n" + "=" * 60)
        print("📋 FINAL WORKFLOW RESULTS")
        print("=" * 60)
        
        if results["success"]:
            print("✅ Planning workflow completed successfully!")
            print(f"🎯 Objectives added: {results.get('objectives_added', 0)}")
            print(f"🔄 Optimization iterations: {results.get('optimization_iterations', 0)}")
            print(f"📊 Plan evaluated: {results.get('plan_evaluated', False)}")
            if results.get('output_file'):
                print(f"💾 Plan saved to: {results['output_file']}")
        else:
            print(f"❌ Planning workflow failed: {results.get('error')}")
        
        # Show log summary
        agent.logger.print_log_summary()
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")


if __name__ == "__main__":
    main() 