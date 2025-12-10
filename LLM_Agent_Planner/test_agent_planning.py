"""
Test script for LLM Agent-based IMRT Planning using OpenAI or Anthropic Models

This script demonstrates how an LLM agent can make autonomous decisions
to create and iteratively improve an IMRT treatment plan using matRad tools.

SUPPORTED MODELS (Top Models for Agentic Work - Updated Nov 2025):
    OpenAI (GPT-5 Series - Latest):
        - gpt-5.1: Latest model with improved reasoning and warmer personality (Nov 2025)
        - gpt-5: Multimodal with advanced reasoning capabilities (Aug 2025)
        - gpt-4o (default): Reliable balance of speed and capability
        - gpt-4o-mini: Faster, cost-effective option
        - gpt-4-turbo: Strong reasoning and function calling
    
    Anthropic (Claude 4.5/4.1 Series - Latest):
        - claude-sonnet-4-5-20250929: Excellent for coding and agentic tasks (Sep 2025)
        - claude-opus-4-1-20250805: Most capable for complex reasoning (Aug 2025)
        - claude-haiku-4-5-20251001: Fast and efficient for simpler tasks (Oct 2025)
        - claude-3-5-sonnet-latest: Previous generation, proven performance
        - claude-3-5-sonnet-20241022: Stable version with excellent capabilities

USAGE:
    # With default model (gpt-4o - stable and reliable)
    python test_agent_planning.py
    
    # With latest OpenAI models
    from test_agent_planning import main, print_supported_models
    main(model="gpt-5.1")      # Latest GPT-5.1 (Nov 2025)
    main(model="gpt-5")        # GPT-5 (Aug 2025)
    main(model="gpt-4o-mini")  # Cost-effective option
    
    # With latest Anthropic models (requires: pip install anthropic)
    main(model="claude-sonnet-4-5-20250929")  # Latest Sonnet (Sep 2025)
    main(model="claude-opus-4-1-20250805")    # Latest Opus (Aug 2025)
    main(model="claude-haiku-4-5-20251001")   # Latest Haiku (Oct 2025)
    
    # Print all supported models
    print_supported_models()

IMPORTANT: Before running this script, source the project environment:
    source /Users/ahmadneishabouri/matlab_env/bin/activate
"""

import os
import json
import time
import numpy as np

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from openai import OpenAI
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
from matrad_tools import MatRadEngine
from logger import PlanningLogger
from guidelines_loader import GuidelinesLoader

# Supported models for agentic work (Top 5+ from OpenAI and Anthropic - Updated Nov 2025)
SUPPORTED_MODELS = {
    # OpenAI models - Latest GPT-5 series (Released Aug-Nov 2025)
    "gpt-5.1": {"provider": "openai", "description": "GPT-5.1 - Latest with improved reasoning (Nov 2025)"},
    "gpt-5": {"provider": "openai", "description": "GPT-5 - Multimodal with advanced reasoning (Aug 2025)"},
    "gpt-4o": {"provider": "openai", "description": "GPT-4 Omni - Reliable balance of speed and capability"},
    "gpt-4o-mini": {"provider": "openai", "description": "GPT-4 Omni Mini - Faster, cost-effective"},
    "gpt-4-turbo": {"provider": "openai", "description": "GPT-4 Turbo - Strong reasoning and function calling"},
    
    # Anthropic models - Latest Claude 4.5 and 4.1 series (Released 2025)
    "claude-sonnet-4-5-20250929": {"provider": "anthropic", "description": "Claude Sonnet 4.5 - Excellent for coding and agentic tasks (Sep 2025)"},
    "claude-opus-4-1-20250805": {"provider": "anthropic", "description": "Claude Opus 4.1 - Most capable for complex reasoning (Aug 2025)"},
    "claude-haiku-4-5-20251001": {"provider": "anthropic", "description": "Claude Haiku 4.5 - Fast and efficient for simpler tasks (Oct 2025)"},
    "claude-3-5-sonnet-20241022": {"provider": "anthropic", "description": "Claude 3.5 Sonnet - Proven stable version"},
    "claude-3-5-sonnet-latest": {"provider": "anthropic", "description": "Claude 3.5 Sonnet Latest - Most recent 3.5 version"},
}

# Initialize clients (will be used based on selected model)
openai_client = OpenAI(base_url="https://eu.api.openai.com/v1")
anthropic_client = Anthropic(base_url="https://eu.api.openai.com/v1") if ANTHROPIC_AVAILABLE else None

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
                 prescription_dose: Optional[Union[float, Dict[str, float]]] = None,
                 num_fractions: Optional[int] = None,
                 treatment_technique: str = "IMRT",
                 patient_file: str = "HandN.mat"):
        self.cancer_site = cancer_site
        self.num_fractions = num_fractions
        self.treatment_technique = treatment_technique
        self.patient_file = patient_file
        
        # Handle prescription - can be None (to be inferred), single dose, or SIB dict
        if prescription_dose is None:
            self.prescription_dose = None
            self.prescription_doses = None
            self.dose_per_fraction = None
            self.is_sib = False
        elif isinstance(prescription_dose, dict):
            self.prescription_doses = prescription_dose
            self.prescription_dose = max(prescription_dose.values())
            self.is_sib = True
            self.dose_per_fraction = self.prescription_dose / num_fractions if num_fractions else None
        else:
            self.prescription_dose = prescription_dose
            self.prescription_doses = {"primary": prescription_dose}
            self.is_sib = False
            self.dose_per_fraction = prescription_dose / num_fractions if num_fractions else None

class IMRTPlanningAgent:
    """LLM Agent for IMRT Planning using OpenAI/Anthropic function calling with structured outputs."""
    
    def __init__(self, matrad_path: str = None, treatment_config: TreatmentConfiguration = None, model: str = "gpt-5.1"):
        """
        Initialize the planning agent with matRad engine and treatment configuration.
        
        Args:
            matrad_path: Path to matRad installation
            treatment_config: Treatment configuration object
            model: Model to use (e.g., "gpt-4o", "claude-3-5-sonnet-latest")
        """
        # Validate model
        if model not in SUPPORTED_MODELS:
            print(f"⚠️  Warning: Model '{model}' not in supported list. Attempting to use anyway.")
            print(f"   Supported models: {list(SUPPORTED_MODELS.keys())}")
            # Infer provider from model name
            if "claude" in model.lower():
                self.model_provider = "anthropic"
            else:
                self.model_provider = "openai"
        else:
            self.model_provider = SUPPORTED_MODELS[model]["provider"]
        
        # Check if Anthropic is available if needed
        if self.model_provider == "anthropic" and not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic client not available. Install with: pip install anthropic")
        
        self.model = model
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
                              {"matrad_path": matrad_path, 
                               "treatment_config": self.plan_state["treatment_config"],
                               "model": self.model,
                               "model_provider": self.model_provider})
    
    def _generate_site_specific_prompt(self) -> str:
        """Generate a site-specific system prompt based on treatment configuration."""
        if not self.treatment_config:
            # Default to head and neck if no config provided
            return self._get_generic_prompt()
        
        site = self.treatment_config.cancer_site.lower()
        
        if site in ['lung', 'nsclc', 'lung_cancer']:
            return self._get_lung_prompt()
        elif site in ['head_and_neck', 'head_neck', 'hnc', 'oropharynx', 'larynx']:
            print("Getting head and neck prompt")            
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
        
        if config and config.prescription_dose is not None:
            config_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Patient File: {config.patient_file}
            - Prescription Dose: {config.prescription_dose} Gy
            - Number of Fractions: {config.num_fractions}
            - Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}"""
        else:
            config_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site if config else 'Lung'}
            - Patient File: {config.patient_file if config else 'Unknown'}
            - Prescription Dose: **TO BE INFERRED** from structure names using analyze_and_filter_structures()
            - Number of Fractions: **TO BE INFERRED**
            - Treatment Technique: {config.treatment_technique if config else 'IMRT'}"""
        
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization for LUNG CANCER using matRad with advanced objective management and optimization monitoring capabilities.
{config_info}

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

            **CRITICAL MATRAD OPTIMIZATION FINDINGS:**
            - **Overlap Priorities**: `matRad` strictly enforces overlap priorities. If Target=1 and OAR=2, the OAR voxels in the overlap region are REMOVED from the OAR optimization.
            - **Penalty Scaling**: Objectives are normalized by `1/N_voxels` (Mean Squared Error). **Large structures (Lungs, Body) DILUTE errors, so they need HIGHER penalties (5000+) to be effective.** Small structures naturally generate strong signals.
            - **Soft vs Hard**: Use constraints (add_constraint) for critical OAR limits (e.g. Cord Max) if soft objectives fail.

            **Stepwise procedure for lung cancer (using inferred prescription from structure analysis)**
            - Step 1 — Critical Safety (Spinal Cord + Basic Coverage)
              - **Use `get_structure_volumes()`**: Check volumes.
              - Spinal cord: Use QUANTEC guidelines from analyze_and_filter_structures() results
              - PTV: MinDVH(inferred_prescription_dose, 95%) with penalty 1000
              - Optimize. Pass if: All QUANTEC constraints met; PTV V95% ≥ 95%
              - Use evaluate_plan_quality() then record_thoughts() to assess progress

            - Step 2 — Lung Sparing (Primary Concern)
              - LUNG_MINUS_GTV: MeanDose(20 Gy) with penalty 200
              - LUNG_MINUS_GTV: MaxDVH(20 Gy, 35%) with penalty 150
              - PTV: MaxDVH(107% of inferred_prescription_dose, 2%) for hotspot control
              - Optimize. Pass if: Lung V20 ≤ 35%; Lung mean ≤ 20 Gy; PTV coverage maintained
              - Use evaluate_plan_quality() then record_thoughts() to assess progress

            - Step 3 — Secondary OARs and Refinement
              - Apply additional QUANTEC guidelines from structure analysis for heart, esophagus, etc.
              - PTV: MinDVH(98% of inferred_prescription_dose, 98%) for cold spot control
              - Rings for gradient optimization based on inferred prescription
              - Optimize. Ensure all previous constraints maintained
              - Use evaluate_plan_quality() then record_thoughts() to assess final plan

            **Lung-specific tuning guidelines:**
            - If lung V20 fails: Increase lung objective penalties by +100, consider beam angle optimization
            - If target coverage fails: Increase PTV MinDVH penalty, but maintain lung constraints
            - If cord constraint fails: Increase cord penalty to 2000-5000, consider beam avoidance
            - For SBRT cases (if dose/fraction > 5 Gy): Use stricter gradient control and higher penalties

            **Critical lung constraints (QUANTEC-based):**
            - Lung V20 ≤ 35% (pneumonitis risk)
            - Lung mean dose ≤ 20 Gy (pneumonitis risk)
            - Spinal cord D_max ≤ 45 Gy (myelopathy prevention)
            - Heart mean ≤ 26 Gy (pericarditis prevention)
            - Esophagus mean ≤ 34 Gy, D_max ≤ 74 Gy (esophagitis prevention)

            ## Enhanced Planning Process with Smart Objective Management:

            ### Initial Setup (Steps 1-5):
            1. Start the MATLAB engine and load patient data.
            2. **MANDATORY: Structure Analysis & Prescription Inference**: ALWAYS call analyze_and_filter_structures() immediately after loading patient data.
               - This will remove helper structures, infer prescription dose from target names, and provide QUANTEC guidelines.
               - Use the inferred prescription and guidelines for all subsequent planning steps.
            3. **Structure Survey**: Use `get_structure_volumes()` to check sizes and priorities.
               - **Penalty Scaling**: Objectives are Mean Squared Error. Large structures (Lungs, Body) dilute errors and need **HIGHER** penalties (e.g. 5000+) to be effective.
            4. Create an initial treatment plan with lung-appropriate beam angles.
            5. Generate the beam geometry and calculate the dose influence matrix.

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
            - ALWAYS follow evaluate_plan_quality() with record_thoughts() to document your clinical assessment and next steps
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
        if config and config.prescription_dose is not None:
            # Handle multi-level prescriptions
            if config.is_sib:
                dose_info = "\n".join([f"    * {target}: {dose} Gy" for target, dose in config.prescription_doses.items()])
                prescription_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Patient File: {config.patient_file}
            - Prescription Doses (SIB):{dose_info}
            - Number of Fractions: {config.num_fractions}
            - Primary Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}
            """
            else:
                prescription_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Patient File: {config.patient_file}
            - Prescription Dose: {config.prescription_dose} Gy
            - Number of Fractions: {config.num_fractions}
            - Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}
            """
        else:
            prescription_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site if config else 'Head and Neck'}
            - Patient File: {config.patient_file if config else 'Unknown'}
            - Prescription Dose: **TO BE INFERRED** from structure names using analyze_and_filter_structures()
            - Number of Fractions: **TO BE INFERRED**
            - Treatment Technique: {config.treatment_technique if config else 'IMRT'}
            """
        
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad with advanced objective management and optimization monitoring capabilities, following a strictly lexicographic optimization strategy.

            {prescription_info}

            Your goal is to create an optimal treatment plan that achieves target coverage while minimizing dose to organs at risk (OARs), following clinical best practices. You have access to tools for beam setup, dose calculation, optimization, plan evaluation, AND IMPORTANTLY, intelligent objective management with optimization convergence monitoring.

            ## Complete Planning Workflow (Follow Sequentially):

            ### Phase A: Initial Setup & Data Preparation
            1. **Initialize**: Start MATLAB engine and load patient data
            2. **MANDATORY: Structure Analysis & Prescription Inference**: ALWAYS call analyze_and_filter_structures() immediately after loading patient data
               - This tool will automatically:
                 * Remove helper/evaluation structures (eval, union, diff, ring, minus, plus, combined, etc.)
                 * Keep only main target structures and critical OARs
                 * Infer prescription dose from target structure names (e.g., PTV6996 = 69.96 Gy, PTV70 = 70 Gy)
                 * Provide QUANTEC-based OAR sparing guidelines for planning protocol
               - Use the inferred prescription dose and guidelines for all subsequent planning steps
               - If prescription inference fails or has low confidence, request clarification before proceeding
            3. **Structure Survey**: Use `get_structure_volumes()` to get voxel counts and priorities.
               - **CRITICAL PENALTY SCALING**: matRad objectives use **Mean** Squared Error (normalized by `1/N_voxels`).
               - **LARGE structures (Body, Skin, Lung)**: Errors are "diluted" by the huge voxel count (N is large, so 1/N is tiny). **You MUST use HIGHER penalties (e.g., 5000-10000) for large structures** to make the optimizer "feel" localized hot spots.
               - **SMALL structures**: Errors result in large MSE values (N is small). Standard penalties (e.g., 500-1000) are usually sufficient.
            4. **Setup beams**: Create treatment plan with appropriate beam angles (at least 9 coplanar beams)
            5. **Calculate dose matrix**: Generate beam geometry and calculate dose influence matrix (dij)
               - Verify calculation completes successfully before proceeding

            ### Phase B: VOI Creation & Preparation (Based on Filtered Structures)
            6. **Create evaluation structures**:
        
               - Base all structure operations on the inferred prescription and kept structures
               -  If needed, create evaluation volumes based on the identified targets:
               - `PTV_all`: Union of all remaining PTVs (if multiple targets exist)
               - `PTV_eval`: For SIB cases, subtract higher dose from lower dose PTVs as needed
               - `BODY_minus_PTVs`: Spillage control volume using external boundary structure
               - `Rings`: Gradient control shells around primary PTV`
               - And whatever else is needed to create the evaluation structures.
            
            7. **Check existing objectives**: ALWAYS use get_current_objectives() AND get_current_constraints()
               - Analyze for redundancy, conflicts, or excessive constraints
               - Clear or modify conflicting objectives before proceeding

            ### Phase C: Staged Optimization (Lexicographic Priority)

            **PRIORITY HIERARCHY (Never compromise higher for lower):**
            A. Target coverage (V100%, D98) and hotspots (D2%) - HIGHEST PRIORITY
            B. Early `squared_overdosing` (NOT square_deviation) BODY_minus_PTVs (or NT) control with high penalties (e.g. 10000+) - HIGH PRIORITY.
            C. Hard OAR maxima (D0.03cc or equivalent)
            D. Dose spillage/gradient (rings and BODY_minus_PTVs)
            E. OAR mean doses and cosmetic shaping - LOWEST PRIORITY

            **CRITICAL MATRAD OPTIMIZATION FINDINGS:**
            - **Overlap Priorities**: `matRad` strictly enforces overlap priorities. If Target=1 and OAR=2, the OAR voxels in the overlap region are REMOVED from the OAR optimization. You CANNOT spare an OAR in the overlap region if it has a higher priority number (lower priority) than the target.
            - **Penalty Scaling**: Objectives are normalized by `1/N_voxels`. **Large structures (Body, Skin) require HIGHER penalties (10x comparing to PTV penalty) because their error signal is diluted by thousands of empty voxels.** Small structures generate strong signals naturally.
            - **Soft vs Hard**: Objectives (e.g., `square_overdosing`) are "soft" and can be violated if the penalty is paid. Constraints (e.g., `min_max_dose`) are "hard" and strict. Use constraints if you absolutely must cap a dose (e.g. Cord Max), but be aware this can cause infeasibility.

            **STAGE 1 — Target Coverage, Hotspots & Basic BODY_minus_PTVs Guardrail**
            
            8. **Add Stage 1 objectives (TARGETS + BASIC BODY_minus_PTVs GUARDRAIL)**:
               - **Use inferred prescription doses from analyze_and_filter_structures() results**
                                       
               - **Target hotspot control** (limit D2%)
                         
               - ** IMPORTANT: BODY_minus_PTVs hotspot guardrail with high penalties (e.g. 10000+)** (to avoid extreme non-PTV hot spots while keeping targets dominant):
                 * BODY_minus_PTVs: square_overdosing with high penalties (e.g. 10000+)
                 * BODY_minus_PTVs: MaxDVH(primary_prescription_dose, ~0.1-1%) to keep the maximum dose outside PTVs at or below the primary inferred prescription dose
                 * If very high dose still exist, try to localize where it is by looking at the DVH analysis of each structure or help structures (e.g. if it's in the ring, or in the BODY_minus_PTVs, or in the target, or in the OAR, etc.)
                 * IMPORTANT: If you see very high dose in the BODY_minus_PTVs, you need to adjust the penalties and re-optimize. Scale penalties based on volume from get_structure_volumes(). Body needs higher penalties than other structures in order to be effective.

            9. **Optimize Stage 1**: Run optimize_fluence() and analyze optimization_analysis results
            
            10. **Evaluate Stage 1**: Use evaluate_plan_quality() then record_thoughts() to document assessment and check:
               - ✓ PASS CRITERIA: Each target V100% ≥ 95% AND D98 ≥ 95% of its inferred prescription dose
               - ✓ PASS CRITERIA: Each target D2% ≤ 107% of its inferred prescription dose               
               - If ANY criterion fails → adjust penalties/parameters, re-optimize
               - If infeasible after 3 attempts → report conflict and move to Stage 2
           
           **STAGE 2 — Critical OAR Hard Limits (Safety)**
           
           11. **Add Stage 2 objectives** (only after Stage 1 passes and target coverage is acceptable):
               - **Critical OAR hard limits** (use QUANTEC guidelines from analyze_and_filter_structures() results):
                 * Apply the specific constraints provided by the structure analysis tool
                 * Use cc→% conversion for D0.03cc constraints as needed
                 * **Scale penalties based on volume**: Large structures (e.g. Lungs, Brain, Body) need HIGH penalties (500-2000+) to overcome dilution.
                 * Ensure there are **no hot spots** in BODY_minus_PTVs.

            12. **Optimize Stage 2**: Run optimize_fluence() and analyze results
           
           13. **Evaluate Stage 2**: Use evaluate_plan_quality() then record_thoughts() to document assessment. Check Stage 1 criteria still met PLUS:
               - ✓ PASS CRITERIA: Stage 1 (target coverage + hotspots) maintained (no degradation)
               - ✓ PASS CRITERIA: All QUANTEC guidelines from analyze_and_filter_structures() are met
               - ✓ PASS CRITERIA: BODY_minus_PTVs MaxDVH < 50% of primary inferred prescription dose
               - If ANY Stage 2 criterion fails → adjust OAR penalties/parameters and re-optimize, DO NOT proceed to Stage 3
               - If infeasible after 3 attempts → report conflict and continue to Stage 3
           
           **STAGE 3 — Gradient, Spillage & OAR Mean Doses (Refinement)**
           
            14. **Add Stage 3 objectives** (only after Stage 2 passes):
               - **Dose spillage control (BODY_minus_PTVs)**:                 
                 
                 * Generally **push the DVH for BODY_minus_PTVs toward ≤ 50% of inferred prescription dose across as much of the volume as possible** (e.g. combine small-volume and larger-volume MaxDVH objectives with moderate penalties).
               
               - **Gradient shaping with rings**:
                 * Ring_0_5mm: MaxDVH(~105-110% of inferred Rx, moderate penalty)
                 * Ring_5_15mm: MaxDVH(~50-80% of inferred Rx, lower penalty)
               
               - **Target cold spot tightening** (only if Stage 1 coverage is comfortably met):
                 * Use 95% of each target's inferred prescription dose for D95 constraints
                 * Apply MinDVH(95% of inferred dose, 98%) for each target as appropriate
               
               - **Secondary OAR constraints** (mean dose reduction, lowest priority within Stage 3):
                 * Apply additional OAR mean dose objectives based on QUANTEC guidelines from analyze_and_filter_structures()
               
               - **Fine-tuning** (optional, use low penalties and never at expense of higher stages):
                 * Additional ring constraints for cosmetic shaping
                 * Minor adjustments to homogeneity if needed

            15. **Final optimization**: Run optimize_fluence()
           
           16. **Final evaluation**: Use evaluate_plan_quality() then record_thoughts() with comprehensive summary to verify ALL stages pass:
               - Stage 1 criteria (target coverage + hotspots based on inferred doses)
               - Stage 2 criteria (QUANTEC guidelines from structure analysis)
               - Stage 3 criteria (spillage + gradient based on inferred doses)
               - Stage 3 mean dose goals - DESIRABLE (acceptable if not fully met)
               - Save_treatment_plan() if plan meets or approaches clinical standards

            ### Phase D: Iteration & Refinement
            
            17. **If plan not acceptable**:
               - Identify which stage/priority is failing (Stage 1 > Stage 2 > Stage 3)
               - For higher priority failures (Stage 1 targets): adjust beam angles, increase target penalties, check feasibility against inferred prescription
               - For mid-priority failures (Stage 2 OAR hard limits): adjust OAR penalties based on QUANTEC guidelines from structure analysis. Consider using hard constraints (add_constraint) if soft objectives fail, but watch for infeasibility.
               - For lower priority issues (Stage 3 gradient, spillage, mean doses): reduce lower-priority penalties to protect higher priorities
               - Document reasoning with record_thoughts()
               - Re-optimize (cold-start) and re-evaluate               

            18. **Convergence monitoring**:
                - Review optimization_analysis for each run
                - Check for stagnation (cost function not improving)
                - Check for oscillation (metrics bouncing)
                - Adjust optimizer tolerance or penalties if needed

            ## cc→% Conversion Protocol:
            - **Purpose**: Convert absolute volume constraints (cc) to percentage for DVH objectives
            - **Usage**: `result = convert_cc_to_percent(structure_name, volume_cc)`
            - **Example**: `vol_pct = convert_cc_to_percent("SPINAL_CORD", 0.03)["volume_percent"]`
            - **Fallback**: If tool unavailable, use 0.1-1% for small structures, 1-5% for medium structures
            
            ## CRITICAL: Evaluation & Documentation Rule
            - Every time you call `evaluate_plan_quality()`, you MUST immediately call `record_thoughts()` to document the current plan quality, your clinical interpretation, and your next actions.
            
            ## Structure Overlap Management

            **When to use set_overlap_priorities?**
            - IMMEDIATELY after loading patient data and BEFORE dose calculation
            - When structures overlap (common: PTV overlaps with critical OARs like spinal cord, brainstem)
            **CRITICAL:** Always call this BEFORE `calculate_dose_influence_matrix()` to ensure proper voxel assignment in overlapping regions.
            **IMPORTANT FINDING**: Lower priority number = Higher Priority. If Target=1 and OAR=2, Target wins overlap. To spare OAR in overlap, OAR must be 1 and Target 2 (but this sacrifices coverage).

            ## Plan Completion Signal:
            When and ONLY when ALL of the following are met:
               - Stage 1 criteria: Target coverage + hotspots within specification
               - Stage 2 criteria: Critical OAR hard limits respected
               - Stage 3 criteria: Gradient and BODY_minus_PTVs acceptable (spillage controlled, no excessive hotspots)
               - Plan clinically deliverable and safe
            
            Respond with: **"PLANNING_COMPLETE: Plan meets all clinical requirements and is ready for clinical use."**

            ## Action-Oriented Behavior:
            - Keep in mind load_the_patient() leads to losing all previous objectives and constraints set and sets it to default
            - **CRITICAL WORKFLOW**: After loading patient data, IMMEDIATELY call analyze_and_filter_structures() before any other planning steps
            - Be concise: Brief clinical reasoning, then immediate tool execution
            - Document decisions: Use record_thoughts() at stage transitions and after evaluations
            - Save progress: Use save_treatment_plan() after each successful stage        

            Start by getting the current plan state and proceeding through Phase A systematically.
            Always ensure your function calls use valid JSON-serializable parameters.
        """
    
    def _get_generic_prompt(self) -> str:
        """Generate generic site-agnostic planning prompt."""
        config = self.treatment_config
        
        if config and config.prescription_dose is not None:
            config_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site}
            - Patient File: {config.patient_file}
            - Prescription Dose: {config.prescription_dose} Gy
            - Number of Fractions: {config.num_fractions}
            - Dose per Fraction: {config.dose_per_fraction:.1f} Gy
            - Treatment Technique: {config.treatment_technique}"""
        else:
            config_info = f"""
            ## TREATMENT CONFIGURATION:
            - Cancer Site: {config.cancer_site if config else 'Generic'}
            - Patient File: {config.patient_file if config else 'Unknown'}
            - Prescription Dose: **TO BE INFERRED** from structure names using analyze_and_filter_structures()
            - Number of Fractions: **TO BE INFERRED**
            - Treatment Technique: {config.treatment_technique if config else 'IMRT'}"""
        
        return f"""
            You are a clinically experienced radiotherapy planning agent, specializing in IMRT optimization using matRad.
{config_info}

            Your goal is to create an optimal treatment plan following clinical best practices for the specified cancer site.

            ## General Planning Process:
            1. Start MATLAB engine and load patient data
            2. **MANDATORY: Structure Analysis & Prescription Inference**: ALWAYS call analyze_and_filter_structures() immediately after loading patient data
               - This will remove helper structures, infer prescription dose from target names, and provide QUANTEC guidelines
               - Use the inferred prescription and guidelines for all subsequent planning steps
            3. **Structure Survey**: Use `get_structure_volumes()` to get voxel counts and priorities.
               - **CRITICAL**: Use voxel counts to scale your penalties. matRad objectives are volume-normalized (Mean Squared Error).
               - **LARGE structures (Body, Skin) need HIGHER penalties (e.g., 5000+) because their error signal is diluted by the huge number of voxels.**
            4. Create treatment plan with appropriate beam configuration
            5. Generate beam geometry and calculate dose influence matrix
            6. Add site-appropriate objectives and/or constraints based on inferred prescription and QUANTEC guidelines.
               - **Constraint Strategy**: Use soft objectives (e.g., square_overdosing) first. If critical OAR sparing fails, switch to hard constraints (e.g., min_max_dose) but be aware of feasibility.
               - **Penalty Scaling**: Scale penalties PROPORTIONAL to volume size (Large Volume = High Penalty).
            7. Optimize fluence            
            8. Evaluate plan quality using evaluate_plan_quality(), then ALWAYS use record_thoughts() to review and summarize objectives/constraints (and confirm their implementation), then concisely provide a plan summary and clear next steps
            9. Iterate until clinical criteria based on inferred prescription are met

            ## Important Considerations:        
            - Skin, Body, or External structure is the patient boundary. Use it to create new structures and help structures you may need.
            - Structures may overlap, use tools (e.g. perform_voi_operation) to create new structures and help structures you may need.
            - Create Skin_excl structure (Skin setdiff all_structures) and maintain a D_max < 0.5 x prescription dose.
            - Keep in mind load_the_patient() leads to losing all previous objectives and constraints set and sets it to default. 
            - **Structure Overlap Management**:
                - Use set_overlap_priorities() to manage structure overlap ALWAYS BEFORE calculate_dose_influence_matrix() and optimize_fluence().
                - **CRITICAL**: Lower priority number = Higher Priority. If Target=1 and OAR=2, Target wins overlap.
            
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
                    "name": "get_structure_volumes",
                    "description": "Get detailed structure information including voxel counts (volume), types, and overlap priorities. CRITICAL for determining penalty scaling (smaller structures often need higher penalties) and checking overlap behavior (lower priority number = higher priority).",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "record_thoughts",
                    "description": "Record agent thoughts, reasoning, or planning notes. Use this to summarize current thinking, plan next steps, or note important observations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "thoughts": {
                                "type": "string",
                                "description": "Agent thoughts, reasoning, or planning notes"
                            }
                        },
                        "required": ["thoughts"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_overlap_priorities",
                    "description": "Set minimal overlap priorities: TARGET=1, OAR=2, other=3. Optionally provide custom priorities.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "structure_priorities": {
                                "type": "object",
                                "description": "Optional dictionary mapping structure names to priority values. If not provided, uses minimal defaults.",
                                "additionalProperties": {
                                    "type": "integer"
                                }
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_and_filter_structures",
                    "description": "LLM-based structure analysis tool. Removes helper/evaluation structures, keeps only main targets and critical OARs, infers prescription dose from structure names, and provides QUANTEC-based OAR sparing guidelines.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "provided_prescription_dose": {
                                "type": "number",
                                "description": "Optional prescription dose in Gy to validate against inferred dose from structure names"
                            }
                        },
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
                
            elif tool_name == "get_structure_volumes":
                result_dict = self.engine.get_structure_volumes()
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "create_treatment_plan":
                num_fractions = 30  # Default
                if self.treatment_config and self.treatment_config.num_fractions:
                    num_fractions = self.treatment_config.num_fractions
                result_dict = self.engine.create_empty_plan(num_fractions=num_fractions)
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
                
            elif tool_name == "set_overlap_priorities":
                structure_priorities = arguments.get("structure_priorities")
                result_dict = self.engine.set_overlap_priorities(structure_priorities)
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "analyze_and_filter_structures":
                provided_dose = arguments.get("provided_prescription_dose")
                result_dict = self.engine.analyze_and_filter_structures(provided_dose)
                result_dict = convert_matlab_types(result_dict)
                
            elif tool_name == "record_thoughts":
                # Store thoughts in plan state and return success
                thoughts = arguments["thoughts"]
                if "thoughts" not in self.plan_state:
                    self.plan_state["thoughts"] = []
                self.plan_state["thoughts"].append({
                    "timestamp": time.time(),
                    "content": thoughts
                })
                result_dict = {
                    "success": True,
                    "message": "Thoughts recorded successfully",
                    "thoughts": thoughts
                }
                
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
        
        # Keep system prompt separate
        system_msgs = [msg for msg in messages if msg["role"] == "system"]
        other_msgs = [msg for msg in messages if msg["role"] != "system"]
        
        if len(other_msgs) <= max_messages - len(system_msgs):
            return messages
        
        # Group messages into conversation units (assistant+tool pairs, user messages)
        conversation_units = []
        i = 0
        while i < len(other_msgs):
            msg = other_msgs[i]
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                # Find all corresponding tool messages
                unit = [msg]
                i += 1
                while i < len(other_msgs) and other_msgs[i]["role"] == "tool":
                    unit.append(other_msgs[i])
                    i += 1
                conversation_units.append(unit)
            else:
                # Single message unit
                conversation_units.append([msg])
                i += 1
        
        # Calculate how many units we can keep
        available_slots = max_messages - len(system_msgs) - 1  # -1 for compression note
        
        if len(conversation_units) <= available_slots:
            return messages
        
        # Keep first few and last few units
        keep_first_units = min(3, available_slots // 2)
        keep_last_units = available_slots - keep_first_units
        
        if keep_last_units < 0:
            keep_last_units = 0
            keep_first_units = available_slots
        
        # Build compressed conversation
        compressed = system_msgs[:]
        
        # Add first units
        for unit in conversation_units[:keep_first_units]:
            compressed.extend(unit)
        
        # Add compression summary
        compressed.append({
            "role": "user", 
            "content": f"[Conversation compressed: Kept first {keep_first_units} and last {keep_last_units} conversation units out of {len(conversation_units)} total units to save context]"
        })
        
        # Add last units
        if keep_last_units > 0:
            for unit in conversation_units[-keep_last_units:]:
                compressed.extend(unit)
        
        return compressed
    
    def _convert_to_anthropic_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI-style messages to Anthropic format.
        Anthropic doesn't support 'tool' role - tool results must be in 'user' messages.
        """
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                continue  # System messages handled separately
            elif msg["role"] == "tool":
                # Convert tool result to user message with tool_result content
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", "unknown"),
                            "content": msg["content"]
                        }
                    ]
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # Convert assistant message with tool calls to Anthropic format
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"])
                    })
                
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content
                })
            else:
                # Regular user or assistant message
                anthropic_messages.append(msg)
        
        return anthropic_messages
    
    def _call_llm(self, messages: List[Dict], tools: List[Dict]) -> Any:
        """
        Call the appropriate LLM provider (OpenAI or Anthropic) based on configured model.
        
        Args:
            messages: Conversation messages
            tools: Available tools/functions
            
        Returns:
            LLM response object
        """
        if self.model_provider == "openai":
            return openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        elif self.model_provider == "anthropic":
            # Extract system message
            system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
            
            # Convert messages to Anthropic format (handles tool role conversion)
            anthropic_messages = self._convert_to_anthropic_messages(messages)
            
            # Convert tools to Anthropic format
            anthropic_tools = []
            for tool in tools:
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "input_schema": func["parameters"]
                })
            
            return anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_message,
                messages=anthropic_messages,
                tools=anthropic_tools
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
    
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
        
        # Print messages content to file
        with open('messages_debug.txt', 'w') as f:
            import json
            f.write("=== INITIAL MESSAGES ===\n")
            f.write(json.dumps(messages, indent=2))
        
        iteration = 0
        while iteration < max_iterations:
            try:
                # Get LLM response with function calling
                response = self._call_llm(messages, self.get_available_tools())
                
                # Parse response based on provider
                if self.model_provider == "openai":
                    assistant_message = response.choices[0].message
                    tool_calls_serializable = None
                    if assistant_message.tool_calls:
                        tool_calls_serializable = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                            } for tc in assistant_message.tool_calls
                        ]
                    simplified_assistant = {
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": tool_calls_serializable
                    }
                    messages.append(simplified_assistant)
                    
                elif self.model_provider == "anthropic":
                    # Convert Anthropic response to OpenAI-like format
                    content_text = ""
                    tool_calls_serializable = []
                    
                    for content_block in response.content:
                        if content_block.type == "text":
                            content_text = content_block.text
                        elif content_block.type == "tool_use":
                            tool_calls_serializable.append({
                                "id": content_block.id,
                                "type": "function",
                                "function": {
                                    "name": content_block.name,
                                    "arguments": json.dumps(content_block.input)
                                }
                            })
                    
                    simplified_assistant = {
                        "role": "assistant",
                        "content": content_text if content_text else None,
                        "tool_calls": tool_calls_serializable if tool_calls_serializable else None
                    }
                    messages.append(simplified_assistant)
                    
                    # Create a simple object to mimic OpenAI's structure
                    class SimpleMessage:
                        def __init__(self, content, tool_calls):
                            self.content = content
                            self.tool_calls = []
                            if tool_calls:
                                for tc in tool_calls:
                                    class ToolCall:
                                        def __init__(self, tc_dict):
                                            self.id = tc_dict["id"]
                                            class Function:
                                                def __init__(self, func_dict):
                                                    self.name = func_dict["name"]
                                                    self.arguments = func_dict["arguments"]
                                            self.function = Function(tc_dict["function"])
                                    self.tool_calls.append(ToolCall(tc))
                    
                    assistant_message = SimpleMessage(content_text, tool_calls_serializable)
                
                # Count tokens and log messages at each iteration
                total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
                with open('messages_debug.txt', 'a') as f:
                    f.write(f"\n\n=== ITERATION {iteration} ===\n")
                    f.write(f"Total chars: {total_chars}, Est tokens: {total_chars//4}\n")
                    f.write(json.dumps(messages, indent=2))
                
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
                                                 "If body minus PTVs has very high dose, you need to adjust the penalties and re-optimize (10x penalties for BODY_minus_PTVs with square_overdosing objective)."
                                                 "try to localize where the high dose is by looking at the DVH analysis of each structure or help structures (e.g. if it's in the ring, or in the BODY_minus_PTVs, or in the target, or in the OAR, etc.)"
                                                 "If you have exhausted all possible adjustments, you may define a compromise to the clinical requirements by ~5% of the prescription goal dose for the target or OAR."
                                                 "Finally, you can declare the plan complete with 'PLANNING_COMPLETE: Plan optimized to best achievable level with available data'. ")
                        else:
                            continuation_prompt = ("Continue with treatment planning. You must evaluate the plan quality first "
                                                 "and ensure all clinical criteria are met before considering the plan complete. "
                                                 "What should we do next?")
                        
                        messages.append({"role": "user", "content": continuation_prompt})
                
                iteration += 1
                
                # Compress conversation history every 10 iterations to prevent context overflow
                if iteration % 100 == 0:
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


def print_supported_models():
    """Print list of supported models for agentic work."""
    print("\n" + "=" * 70)
    print("🤖 SUPPORTED MODELS FOR AGENTIC PLANNING")
    print("=" * 70)
    
    openai_models = {k: v for k, v in SUPPORTED_MODELS.items() if v["provider"] == "openai"}
    anthropic_models = {k: v for k, v in SUPPORTED_MODELS.items() if v["provider"] == "anthropic"}
    
    print("\n📘 OpenAI Models:")
    for model_name, info in openai_models.items():
        print(f"  • {model_name:30s} - {info['description']}")
    
    print("\n📗 Anthropic Models:")
    for model_name, info in anthropic_models.items():
        print(f"  • {model_name:30s} - {info['description']}")
    
    print("\n" + "=" * 70)
    print("💡 Usage: Set model parameter when calling main() or IMRTPlanningAgent()")
    print("   Example: main(model='gpt-4o') or main(model='claude-3-5-sonnet-latest')")
    print("=" * 70 + "\n")


def main(cancer_site: str = "head_and_neck", 
         prescription_dose: Optional[Union[float, Dict[str, float]]] = None, 
         num_fractions: Optional[int] = None,
         patient_file: str = "HandN.mat",
         treatment_technique: str = "IMRT",
         model: str = "gpt-4o"):
    """
    Main function to test the LLM agent planning system with configurable treatment parameters.
    
    Args:
        cancer_site: Type of cancer (e.g., 'lung', 'head_and_neck', 'prostate', 'breast')
        prescription_dose: Total prescription dose in Gy, or dict for SIB. If None, inferred from structure names.
        num_fractions: Number of treatment fractions. If None, uses site-specific defaults.
        patient_file: Path to patient data file
        treatment_technique: Treatment technique (default: 'IMRT')
        model: LLM model to use (default: 'gpt-4o'). See print_supported_models() for options.
    """
    print("🚀 Starting LLM Agent IMRT Planning Test")
    print("=" * 50)
    
    # Configuration        
    matrad_path = os.path.expanduser("~/matRad")
    
    # Create treatment configuration
    treatment_config = TreatmentConfiguration(
        cancer_site=cancer_site,
        prescription_dose=prescription_dose,
        num_fractions=num_fractions,
        treatment_technique=treatment_technique,
        patient_file=patient_file
    )
    
    try:
        # Create planning agent with treatment configuration
        agent = IMRTPlanningAgent(matrad_path, treatment_config, model=model)
        
        print(f"📊 Patient file: {patient_file}")
        print(f"🏥 matRad path: {matrad_path}")
        print(f"🎯 Cancer site: {cancer_site}")
        if prescription_dose is None:
            print(f"💊 Prescription: Will be inferred from structure names")
        elif isinstance(prescription_dose, dict):
            dose_info = ", ".join([f"{target}: {dose} Gy" for target, dose in prescription_dose.items()])
            primary_dose = max(prescription_dose.values())
            print(f"💊 Prescription (SIB): {dose_info} in {num_fractions} fractions ({primary_dose/num_fractions:.1f} Gy/fx primary)")
        else:
            print(f"💊 Prescription: {prescription_dose} Gy in {num_fractions} fractions ({prescription_dose/num_fractions:.1f} Gy/fx)")
        print(f"⚡ Technique: {treatment_technique}")
        print(f"🤖 Model: {model} ({SUPPORTED_MODELS.get(model, {}).get('provider', 'unknown')})")
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
    # Print available models
    # print_supported_models()
    
    # Run with default model (gpt-5.1 - stable and reliable)
    main()
    
    # Examples with different models:
    
    # Latest OpenAI models (GPT-5 series):
    # main(model="gpt-5.1")      # Latest GPT-5.1 with improved reasoning (Nov 2025)
    # main(model="gpt-5")        # GPT-5 multimodal with advanced reasoning (Aug 2025)
    # main(model="gpt-4o-mini")  # Faster, cost-effective GPT-4 option
    
    # Latest Anthropic models (Claude 4.5/4.1 series - requires: pip install anthropic):
    # main(model="claude-sonnet-4-5-20250929")  # Latest Sonnet for coding and agentic tasks (Sep 2025)
    # main(model="claude-opus-4-1-20250805")    # Latest Opus for complex reasoning (Aug 2025)
    # main(model="claude-haiku-4-5-20251001")   # Latest Haiku, fast and efficient (Oct 2025)
    # main(model="claude-3-5-sonnet-latest")    # Previous generation, proven performance 