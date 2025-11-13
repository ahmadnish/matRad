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
from guidelines_loader import GuidelinesLoader

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


class TreatmentConfiguration:
    """Configuration class for treatment parameters."""
    def __init__(self, 
                 cancer_site: str,
                 prescription_dose: float,
                 num_fractions: int,
                 treatment_technique: str = "IMRT",
                 risk_level: str = "high_risk"):
        self.cancer_site = cancer_site
        self.prescription_dose = prescription_dose
        self.num_fractions = num_fractions
        self.treatment_technique = treatment_technique
        self.risk_level = risk_level
        self.dose_per_fraction = prescription_dose / num_fractions

class IMRTPlanningAgent:
    """LLM Agent for IMRT Planning using OpenAI function calling with structured outputs."""
    
    def __init__(self, matrad_path: str = None, treatment_config: TreatmentConfiguration = None):
        """Initialize the planning agent with matRad engine and treatment configuration."""
        self.engine = MatRadEngine(matrad_path)
        self.logger = PlanningLogger()
        self.conversation_history = []
        self.treatment_config = treatment_config
        self.guidelines_loader = GuidelinesLoader()
        self.guidelines_loader.load_all_guidelines()
        
        self.plan_state = {
            "engine_started": False,
            "patient_loaded": False,
            "plan_created": False,
            "beam_geometry_generated": False,
            "influence_matrix_calculated": False,
            "objectives_added": [],
            "optimization_completed": False,
            "plan_evaluated": False,
            "iteration_count": 0,
            "treatment_config": treatment_config.__dict__ if treatment_config else None
        }
        
        # Log initialization
        self.logger.log_action("initialization", "Agent initialized", 
                              {"matrad_path": matrad_path, "treatment_config": self.plan_state["treatment_config"]})
    
    def _generate_site_specific_prompt(self) -> str:
        """Generate a site-specific system prompt based on treatment configuration."""
        if not self.treatment_config:
            # Default to head and neck if no config provided
            return self._get_generic_prompt()
        
        site = self.treatment_config.cancer_site.lower()
        
        if site in ['lung', 'nsclc', 'lung_cancer']:
            return self._get_lung_prompt()
        elif site in ['head_and_neck', 'head_neck', 'hnc', 'oropharynx', 'larynx']:
            return self._get_head_and_neck_prompt()
        elif site in ['prostate']:
            return self._get_prostate_prompt()
        elif site in ['breast']:
            return self._get_breast_prompt()
        else:
            # Generic prompt for other sites
            return self._get_generic_prompt()
    
    def _get_lung_prompt(self) -> str:
        """Generate lung-specific planning prompt."""
        config = self.treatment_config
        beam_config = self.guidelines_loader.get_beam_arrangements('lung')
        
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization for LUNG CANCER using matRad with advanced objective management and optimization monitoring capabilities.

            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Prescription Dose: {config.prescription_dose} Gy
            - Number of Fractions: {config.num_fractions}
            - Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}

            Your goal is to create an optimal treatment plan that achieves target coverage while minimizing dose to organs at risk (OARs), following clinical best practices for lung cancer radiotherapy.

            ## LUNG CANCER PLANNING PLAYBOOK (Staged Strategy)

            **High-level approach**
            - Initialize from lung template → set beams, target eval VOIs, and baseline objectives.
            - Stage 1 (Critical OARs + Coverage) → optimize → check feasibility.
            - Stage 2 (Lung sparing + Gradient shaping) → optimize → check.
            - Stage 3 (Secondary OARs + refinement) → optimize → check.
            - Convergence test → if any priority fails, apply targeted refinements.

            **Priority rules (lexicographic for lung cancer)**
            1) Critical OAR maxima (Spinal cord D_max ≤ 45 Gy)
            2) Lung sparing (V20 ≤ 35%, Mean dose ≤ 20 Gy)
            3) Target coverage (V95% ≥ 95%, D98% ≥ 98% prescription)
            4) Target hotspots (D2% ≤ 107% prescription)
            5) Heart constraints (Mean ≤ 26 Gy, V60 ≤ 33%)
            6) Esophagus constraints (Mean ≤ 34 Gy, D_max ≤ 74 Gy)
            7) Secondary structures (brachial plexus, great vessels)

            **Required VOI operations for lung planning:**
            - `LUNG_MINUS_GTV`: `perform_voi_operation("LUNG_TOTAL","GTV","setdiff","LUNG_MINUS_GTV")` for lung dose calculations
            - `LUNG_TOTAL`: `perform_voi_operation("LUNG_LT","LUNG_RT","union","LUNG_TOTAL")` if bilateral lungs exist
            - `BODY_MINUS_PTV`: `perform_voi_operation("BODY","PTV","setdiff","BODY_MINUS_PTV")` for gradient control
            - Rings: shells around `PTV` via `create_ring_structures("PTV", [5,15,30], inner_margin_mm=0)`

            **Lung-specific beam arrangement:**
            - Default: {beam_config.get('gantry_angles', [0, 45, 135, 180, 225, 315])} degrees (6-field IMRT)
            - Avoid direct AP/PA beams through contralateral lung when possible

            **Stepwise procedure for lung cancer**
            - Step 1 — Critical Safety (Spinal Cord + Basic Coverage)
              - Spinal cord: MaxDose(45 Gy) with high penalty (1000+)
              - PTV: MinDVH({config.prescription_dose} Gy, 95%) with penalty 1000
              - Optimize. Pass if: Cord D_max ≤ 45 Gy; PTV V95% ≥ 95%

            - Step 2 — Lung Sparing (Primary Concern)
              - LUNG_MINUS_GTV: MeanDose(20 Gy) with penalty 200
              - LUNG_MINUS_GTV: MaxDVH(20 Gy, 35%) with penalty 150
              - PTV: MaxDVH({config.prescription_dose * 1.07:.1f} Gy, 2%) for hotspot control
              - Optimize. Pass if: Lung V20 ≤ 35%; Lung mean ≤ 20 Gy; PTV coverage maintained

            - Step 3 — Secondary OARs and Refinement
              - Heart: MeanDose(26 Gy) if feasible
              - Esophagus: MeanDose(34 Gy) and MaxDose(74 Gy) if present
              - PTV: MinDVH({config.prescription_dose * 0.98:.1f} Gy, 98%) for cold spot control
              - Rings for gradient optimization
              - Optimize. Ensure all previous constraints maintained

            **Lung-specific tuning guidelines:**
            - If lung V20 fails: Increase lung objective penalties by +100, consider beam angle optimization
            - If target coverage fails: Increase PTV MinDVH penalty, but maintain lung constraints
            - If cord constraint fails: Increase cord penalty to 2000+, consider beam avoidance
            - For SBRT cases (if dose/fraction > 5 Gy): Use stricter gradient control and higher penalties

            **Critical lung constraints (QUANTEC-based):**
            - Lung V20 ≤ 35% (pneumonitis risk)
            - Lung mean dose ≤ 20 Gy (pneumonitis risk)
            - Spinal cord D_max ≤ 45 Gy (myelopathy prevention)
            - Heart mean ≤ 26 Gy (pericarditis prevention)
            - Esophagus mean ≤ 34 Gy, D_max ≤ 74 Gy (esophagitis prevention)

            ## Enhanced Planning Process with Smart Objective Management:

            ### Initial Setup (Steps 1-4):
            1. Start the MATLAB engine and load patient data.
            2. Examine the structure information to identify targets and OARs.
            3. Create an initial treatment plan with lung-appropriate beam angles.
            4. Generate the beam geometry and calculate the dose influence matrix.

            ### Intelligent Objective and Constraint Management Workflow (Steps 5+):
            
            **BEFORE adding any objectives or constraints:**
            - ALWAYS use get_current_objectives() AND get_current_constraints() to check what already exists
            - Analyze existing objectives for redundancy, conflicts, or excessive constraints
            - Check constraint feasibility and compatibility with objectives
            - Focus on lung-specific priorities and constraints

            **Optimization Strategy with Convergence Monitoring:**
            - First optimization: Use optimize_fluence() (cold-start)
            - Subsequent optimizations: Use optimize_fluence(use_previous_weights=true) for warm-start
            - **ANALYZE optimization_analysis output every time:**
              - convergence_quality: "good" = continue, "moderate" = cautious, "poor" = simplify objectives
              - objective_stagnation: true = too many constraints, reduce objectives
              - small_step_sizes: true = optimization struggling, simplify problem
              - relative_improvement: <1% = likely over-constrained

            **Plan Evaluation and Completion:**
            - Use evaluate_plan_quality() for comprehensive assessment
            - Plan is complete when:
              1. Lung V20 ≤ 35% AND mean dose ≤ 20 Gy
              2. Spinal cord D_max ≤ 45 Gy
              3. PTV V95% ≥ 95%
              4. All other OAR constraints met per QUANTEC guidelines

            **CRITICAL: How to Signal Plan Completion:**
            When and ONLY when all clinical criteria are satisfied, respond with:
            "PLANNING_COMPLETE: Lung cancer plan meets all clinical requirements and is ready for clinical use."

            ## Treatment Plan Evaluation Tools
            **For comprehensive plan evaluation, use `evaluate_plan_quality()`:**
            - Primary tool for overall plan assessment with lung-specific metrics
            - Includes lung V20, V30, mean dose calculations

            ## CRITICAL: Action-Oriented Behavior:
            - When you have a plan or next step, immediately execute it using the appropriate tool
            - Reasoning should be brief and focused on lung cancer clinical priorities
            - Always provide clear clinical rationales for lung-specific objectives
            - Prioritize lung sparing while maintaining target coverage

            Start by getting the current plan state and then proceed step by step with lung cancer planning priorities.
            Always ensure your function calls use valid JSON-serializable parameters.
        """
    
    def _get_head_and_neck_prompt(self) -> str:
        """Generate head and neck specific planning prompt (existing implementation)."""
        config = self.treatment_config
        if config:
            prescription_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Prescription Dose: {config.prescription_dose} Gy
            - Number of Fractions: {config.num_fractions}
            - Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}
            """
        else:
            prescription_info = """
            ## TREATMENT CONFIGURATION:
            - Cancer Site: Head and Neck (default)
            - Prescription Dose: 70.0 Gy (high risk), 63.0 Gy (intermediate risk)
            - Number of Fractions: 35 (2 Gy/fx standard)
            - Treatment Technique: IMRT
            """
        
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad with advanced objective management and optimization monitoring capabilities.

            {prescription_info}

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
            - Then proceed to add objectives and constraints based on the Head & Neck Planning Playbook below:

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
             - Use `convert_cc_to_percent(structure_name, volume_cc)` to get exact conversion for DVH objectives.
             - **When to use**: Before adding max_dvh constraints for critical OARs (spinal cord D0.03cc ≤ 45Gy, brainstem D0.03cc ≤ 54Gy)
             - **How to use**: 
               1. Call `convert_cc_to_percent("SPINAL_CORD", 0.03)` to get percentage
               2. Use returned `volume_percent` value in `add_optimization_objective("SPINAL_CORD", "max_dvh", dose_value=45, volume_percent=result["volume_percent"])`
             - **Alternative**: If conversion unavailable, use conservative small fractions (0.1-1%) and refine iteratively.

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
                 - **Example workflow**: 
                   1. `convert_cc_to_percent("SPINAL_CORD", 0.03)` → get volume_percent
                   2. `add_optimization_objective("SPINAL_CORD", "max_dvh", dose_value=45, volume_percent=volume_percent, penalty=2000, rationale="Critical cord tolerance per TG-101")`
                 - Cord: MaxDVH(45 Gy, V0.03cc%)
                 - Brainstem: MaxDVH(54 Gy, V0.03cc%)
                 - Cord_PRV: MaxDVH(48 Gy, V0.03cc%) if PRV exists
                 - Brainstem_PRV: MaxDVH(57 Gy, V0.03cc%) if PRV exists
              - Targets:
                - PTV70: MinDVH(70 Gy, 95%), MaxDVH(74.9 Gy, 2%)
                - PTV63: MinDVH(63 Gy, 95%), MaxDVH(67.4 Gy, 2%)
              - Optimize. Pass if: OAR D0.03cc ≤ limits; PTV70 V100 ≥95%; PTV63 V100 ≥95%; D2 within caps.

            **Optimization and Monitoring Loop:**
            1. Run optimize_fluence() and CAREFULLY analyze the optimization_analysis results
            2. Evaluate plan quality and clinical metrics
            3. **CRITICAL DECISION POINT:** Based on optimization convergence AND plan quality

            **Plan Evaluation and Completion:**
            Use evaluate_plan_quality() for comprehensive plan assessment
            
            **CRITICAL: How to Signal Plan Completion:**
            When and ONLY when all clinical criteria are satisfied, respond with:
            "PLANNING_COMPLETE: Plan meets all clinical requirements and is ready for clinical use."

            ## CRITICAL: Action-Oriented Behavior:
            - When you have a plan or next step, immediately execute it using the appropriate tool
            - Reasoning should be brief and concise with clear plan-level reasoning across iterations
            - Always provide clear clinical rationales in tool calls

            Start by getting the current plan state and then proceed step by step.
            Always ensure your function calls use valid JSON-serializable parameters.
        """
    
    def _get_generic_prompt(self) -> str:
        """Generate generic site-agnostic planning prompt."""
        config = self.treatment_config
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad.

            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site if config else 'Generic'}
            - Prescription Dose: {config.prescription_dose if config else 'TBD'} Gy
            - Number of Fractions: {config.num_fractions if config else 'TBD'}
            - Dose per Fraction: {config.dose_per_fraction:.1f if config else 'TBD'} Gy
            - Treatment Technique: {config.treatment_technique if config else 'IMRT'}

            Your goal is to create an optimal treatment plan following clinical best practices for the specified cancer site.

            ## General Planning Process:
            1. Start MATLAB engine and load patient data
            2. Examine structure information
            3. Create treatment plan with appropriate beam configuration
            4. Generate beam geometry and calculate dose influence matrix
            5. Add site-appropriate objectives and/or constraints
            6. Optimize and evaluate plan quality
            7. Iterate until clinical criteria are met

            **CRITICAL: How to Signal Plan Completion:**
            "PLANNING_COMPLETE: Plan meets all clinical requirements and is ready for clinical use."

            Start by getting the current plan state and proceed step by step.
        """
    
    def _get_prostate_prompt(self) -> str:
        """Generate prostate-specific planning prompt."""
        # Placeholder for future prostate implementation
        return self._get_generic_prompt()
    
    def _get_breast_prompt(self) -> str:
        """Generate breast-specific planning prompt."""
        # Placeholder for future breast implementation
        return self._get_generic_prompt()
        
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
            },
            {
                "type": "function",
                "function": {
                    "name": "convert_cc_to_percent",
                    "description": "Convert absolute volume in cc to percentage for DVH objectives. Essential for clinical constraints like D0.03cc (spinal cord/brainstem max dose at 0.03cc). Returns both percentage and fraction formats for use in objectives.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_name": {
                                "type": "string",
                                "description": "Name of the structure to analyze"
                            },
                            "volume_cc": {
                                "type": "number",
                                "description": "Volume in cubic centimeters to convert (e.g., 0.03 for D0.03cc constraints)"
                            }
                        },
                        "required": ["structure_name", "volume_cc"],
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
                # Use provided angles or get site-specific defaults
                gantry_angles = arguments.get("gantry_angles")
                couch_angles = arguments.get("couch_angles")
                
                # If no angles provided and we have treatment config, use site defaults
                if not gantry_angles and self.treatment_config:
                    site_beams = self.guidelines_loader.get_beam_arrangements(self.treatment_config.cancer_site.lower())
                    if site_beams:
                        gantry_angles = site_beams.get('gantry_angles', [0, 72, 144, 216, 288])
                        couch_angles = site_beams.get('couch_angles', [0] * len(gantry_angles))
                        
                        # Log that we're using site-specific defaults
                        self.logger.log_action(
                            "beam_config_auto",
                            f"Using site-specific beam configuration for {self.treatment_config.cancer_site}",
                            {"gantry_angles": gantry_angles, "couch_angles": couch_angles}
                        )
                
                result_dict = self.engine.set_beam_angles(gantry_angles, couch_angles)
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
                
            elif tool_name == "convert_cc_to_percent":
                result_dict = self.engine.convert_cc_to_percent(
                    arguments["structure_name"],
                    arguments["volume_cc"]
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
        
        # Generate site-specific system prompt
        system_prompt = self._generate_site_specific_prompt()
        
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


def main(cancer_site: str = "head_and_neck", 
         prescription_dose: float = 70.0, 
         num_fractions: int = 35,
         patient_file: str = "HandN.mat",
         treatment_technique: str = "IMRT"):
    """
    Main function to test the LLM agent planning system with configurable treatment parameters.
    
    Args:
        cancer_site: Type of cancer (e.g., 'lung', 'head_and_neck', 'prostate', 'breast')
        prescription_dose: Total prescription dose in Gy
        num_fractions: Number of treatment fractions
        patient_file: Path to patient data file
        treatment_technique: Treatment technique (default: 'IMRT')
    """
    print("🚀 Starting LLM Agent IMRT Planning Test")
    print("=" * 50)
    
    # Configuration
    matrad_path = "/Users/ahmadneishabouri/matRad"  # Update this path as needed
    
    # Create treatment configuration
    treatment_config = TreatmentConfiguration(
        cancer_site=cancer_site,
        prescription_dose=prescription_dose,
        num_fractions=num_fractions,
        treatment_technique=treatment_technique
    )
    
    try:
        # Create planning agent with treatment configuration
        agent = IMRTPlanningAgent(matrad_path, treatment_config)
        
        print(f"📊 Patient file: {patient_file}")
        print(f"🏥 matRad path: {matrad_path}")
        print(f"🎯 Cancer site: {cancer_site}")
        print(f"💊 Prescription: {prescription_dose} Gy in {num_fractions} fractions ({prescription_dose/num_fractions:.1f} Gy/fx)")
        print(f"⚡ Technique: {treatment_technique}")
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