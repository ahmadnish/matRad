# LLM Agent for IMRT Planning

## Overview

This project implements an intelligent Large Language Model (LLM) agent that can autonomously create and iteratively improve Intensity-Modulated Radiation Therapy (IMRT) treatment plans using matRad. The agent makes clinical decisions, selects appropriate tools, and optimizes treatment plans based on established radiotherapy guidelines.

## Features

### 🤖 Intelligent Decision Making
- **Autonomous Planning**: Agent makes clinical decisions without human intervention
- **Adaptive Workflows**: Dynamically adjusts planning strategy based on anatomy and results
- **Clinical Reasoning**: Applies radiotherapy guidelines and best practices
- **Iterative Improvement**: Automatically refines plans based on quality metrics
- **Smart Convergence Monitoring**: Analyzes optimization convergence patterns to prevent stagnation
- **Objective Learning**: Learns from previous optimization outcomes to avoid ineffective strategies

### 🔧 Comprehensive Tool Suite
- **MATLAB Integration**: Full integration with matRad radiotherapy planning system
- **Patient Loading**: Automatic CT and structure data processing
- **Beam Optimization**: Intelligent beam angle selection based on anatomy
- **Dose Calculation**: Dose influence matrix computation
- **Smart Objective Management**: 
  - View, add, remove, and clear optimization objectives
  - Intelligent detection of redundant and conflicting objectives
  - Adaptive objective simplification when optimization stagnates
- **Optimization Monitoring**: Real-time capture and analysis of MATLAB optimizer output
- **Plan Evaluation**: DVH analysis and quality metrics calculation

### 📊 Advanced Logging
- **Structured Logging**: JSON-formatted logs of all agent actions
- **Metric Tracking**: Detailed recording of optimization metrics
- **Session Management**: Complete workflow documentation
- **Error Handling**: Comprehensive error logging and recovery

## Architecture

```
LLM Agent System
├── IMRTPlanningAgent         # Main LLM agent with OpenAI integration
├── SimpleIMRTAgent          # Standalone demo without API requirements
├── MatRadEngine            # Python-MATLAB interface
├── PlanningLogger          # Structured logging system
└── Tool Functions          # Individual planning operations
```

## Quick Start

### Prerequisites

1. **MATLAB with matRad installed**
2. **Python dependencies**:
   ```bash
   pip install -r requirements_agent.txt
   ```
3. **OpenAI API key** (for full LLM agent):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Running the Simple Demo

For a quick demonstration without API requirements:

```bash
cd LLM_Agent_Planner
python simple_agent_demo.py
```

### Running the Full LLM Agent

For the complete OpenAI-powered agent:

```bash
cd LLM_Agent_Planner
python test_agent_planning.py
```

## How It Works

### 1. Planning Workflow

The agent follows a structured clinical workflow:

```
1. 🚀 Initialize MATLAB Engine
2. 📊 Load Patient Data  
3. 🔍 Analyze Anatomy Structures
4. 📋 Create Treatment Plan
5. 📐 Optimize Beam Arrangement
6. ⚙️  Generate Beam Geometry
7. 🧮 Calculate Dose Influence Matrix
8. 🎯 Add Optimization Objectives
9. ⚡ Run Fluence Optimization
10. 📈 Evaluate Plan Quality
11. 🔄 Iterative Improvements
12. 💾 Save Final Plan
```

### 2. Agent Intelligence

The LLM agent demonstrates clinical intelligence by:

- **Anatomy Recognition**: Identifies treatment site from patient file names and structure lists
- **Beam Selection**: Chooses appropriate beam arrangements (e.g., 7-field for H&N, 5-field for others)
- **Objective Setting**: Applies clinical dose constraints based on structure types
- **Quality Assessment**: Analyzes plan metrics to identify improvement opportunities
- **Adaptive Optimization**: Adds stricter constraints when plans don't meet quality standards

### 3. Clinical Guidelines Integration

The agent applies established radiotherapy guidelines:

```python
# Target Dose Prescriptions
PTV_HIGH_RISK: 60-70 Gy
PTV_INTERMEDIATE: 54-60 Gy  
PTV_LOW_RISK: 50-54 Gy

# OAR Dose Constraints (QUANTEC/ESTRO)
BRAINSTEM: Max ≤ 54 Gy
SPINAL_CORD: Max ≤ 45 Gy
PAROTID_GLANDS: Mean ≤ 26 Gy
OPTIC_STRUCTURES: Max ≤ 55 Gy
LENS: Max ≤ 25 Gy
```

## Tool Functions

### Core Planning Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `start_matlab_engine` | Initialize MATLAB/matRad | None |
| `load_patient_data` | Load CT and structure data | `patient_file` |
| `get_structure_information` | Analyze anatomy structures | None |
| `create_treatment_plan` | Initialize treatment plan | None |
| `set_beam_configuration` | Define beam angles | `gantry_angles`, `couch_angles` |
| `generate_beam_geometry` | Create beam geometry | None |
| `calculate_dose_influence_matrix` | Compute dose matrix | None |
| `add_optimization_objective` | Add dose constraints | `structure_name`, `objective_type`, `dose_value`, `penalty`, `volume_percent`, `eud_exponent` |
| `optimize_fluence` | Run optimization | None |
| `evaluate_plan_quality` | Calculate metrics | None |
| `calculate_dvh_analysis` | DVH computation | `structure_name` (optional) |
| `save_treatment_plan` | Save final plan | `output_file` |

### Objective Types

**Basic Dose Objectives:**
- **`min_dose`**: Minimum dose constraint (underdosing penalty)
- **`max_dose`**: Maximum dose constraint (overdosing penalty)  
- **`mean_dose`**: Mean dose objective
- **`square_deviation`**: Target dose with squared deviation penalty

**Advanced Objectives:**
- **`eud`**: Equivalent Uniform Dose objective
  - Configurable exponent parameter (default 3.5)
  - For targets: use low exponent (1-2) to emphasize cold spots
  - For OARs: use high exponent (5-10) to emphasize hot spots
- **`min_dvh`**: Minimum DVH constraint (ensures minimum volume receives threshold dose)
  - Configurable volume percentage (default 95%)
  - Example: `min_dvh` with 60Gy, 95% ensures 95% of target gets ≥60Gy
- **`max_dvh`**: Maximum DVH constraint (limits volume receiving threshold dose)
  - Configurable volume percentage (default 95%)
  - Example: `max_dvh` with 20Gy, 30% ensures ≤30% of OAR gets ≥20Gy

### Enhanced Objective Management Tools

| Tool | Description | Parameters | Purpose |
|------|-------------|------------|---------|
| `get_current_objectives` | View all existing objectives | None | Check for redundancies before adding new objectives |
| `remove_optimization_objective` | Remove specific objective | `structure_name`, `objective_index`, `objective_type`, `dose_value` | Eliminate conflicting or redundant objectives |
| `clear_all_objectives` | Clear objectives for structure(s) | `structure_name` (optional) | Reset when objectives prevent convergence |

### Constraint Management Tools

| Tool | Description | Parameters | Purpose |
|------|-------------|------------|---------|
| `add_constraint` | Add hard limit constraint | `structure_name`, `constraint_type`, `lower_bound`, `upper_bound`, `dose_reference`, `eud_exponent`, `rationale` | Enforce mandatory dose/volume limits |
| `remove_constraint` | Remove specific constraint | `structure_name`, `constraint_index`, `constraint_type`, `rationale` | Remove infeasible or unnecessary constraints |
| `get_current_constraints` | View all existing constraints | None | Check constraint feasibility and conflicts |

#### Constraint Types

**Available constraint types:**
- **`min_max_dose`**: Hard dose limits with lower and upper bounds
- **`min_max_mean_dose`**: Mean dose bounds for structure
- **`min_max_eud`**: EUD bounds with configurable exponent
- **`min_max_dvh`**: DVH volume constraints for specific dose levels

## 🚀 Enhanced Agent Capabilities

### Smart Optimization Monitoring

The agent now captures and analyzes MATLAB optimizer console output in real-time, providing detailed convergence analysis:

```python
# Example optimization analysis output
{
  "convergence_analysis": {
    "convergence_quality": "poor",
    "objective_stagnation": true,
    "small_step_sizes": true,
    "relative_improvement": 0.002,
    "convergence_reason": "Optimization stagnated with very small step sizes"
  },
  "optimization_trajectory": [
    {"iteration": 1, "objective": 29503.46, "alpha_pr": 0.0138},
    {"iteration": 14, "objective": 1450.79, "alpha_pr": 8.62e-16}
  ],
  "summary": "❌ Convergence quality: POOR\n⚠️ WARNING: Objective value stagnated in recent iterations"
}
```

### Intelligent Objective Management

The agent employs sophisticated strategies to prevent over-constraining:

#### **Before Adding Objectives:**
- Always checks existing objectives using `get_current_objectives()`
- Identifies redundant or conflicting constraints
- Maintains total objective count ≤ 8-12 across all structures

#### **During Optimization:**
- Monitors convergence quality (good/moderate/poor)
- Detects stagnation patterns and tiny step sizes
- Analyzes relative improvement percentages

#### **Adaptive Response to Poor Convergence:**
- **Stagnation detected** → Simplify objective set
- **Tiny step sizes (<1e-12)** → Remove redundant objectives  
- **Low improvement (<1%)** → Clear conflicting constraints
- **Multiple failures** → Reset and restart with minimal objectives

### Learning and Memory

The agent learns from optimization patterns:

```python
# Pattern Recognition Examples
- Multiple min_dose + max_dose on same structure → Often redundant
- >3 objectives per structure → Usually over-constrained
- Dose values <2Gy apart → Likely conflicting
- Very high penalties (>10000) → Can cause numerical issues
```

### Enhanced Termination Logic

**Stop conditions based on convergence patterns:**
- 2+ consecutive optimizations with poor convergence → Simplify objectives
- Optimization consistently stops at <20 iterations → Over-constraining
- Step sizes consistently <1e-12 → Numerically ill-conditioned

## Example Usage

### Basic Agent Usage

```python
from test_agent_planning import IMRTPlanningAgent

# Create agent
agent = IMRTPlanningAgent("/path/to/matRad")

# Run planning session
results = agent.run_planning_session("HEAD_AND_NECK.mat", max_iterations=10)

# View results
if results["success"]:
    print(f"✅ Planning completed in {results['iterations_completed']} iterations")
    agent.logger.print_log_summary()
```

### Manual Tool Usage

```python
from matrad_tools import MatRadEngine

# Create engine
engine = MatRadEngine("/path/to/matRad")

# Manual workflow
engine.start_engine()
result = engine.load_patient("patient.mat")
structures = engine.get_structure_names()

# Add critical constraints first (hard limits)
engine.add_constraint("SpinalCord", "min_max_dose", upper_bound=45.0, rationale="FDA safety limit")
engine.add_constraint("Brainstem", "min_max_dose", upper_bound=54.0, rationale="Critical structure tolerance")
engine.add_constraint("Parotid_L", "min_max_mean_dose", upper_bound=26.0, rationale="QUANTEC xerostomia limit")

# Add optimization objectives (soft goals)
engine.add_optimization_objective("PTV", "square_deviation", 60.0, 1000)
engine.add_optimization_objective("PTV", "min_dvh", 57.0, 1000, volume_percent=95)  # 95% gets ≥57Gy
engine.add_optimization_objective("Brainstem", "max_dose", 50.0, 1000)  # Optimize toward 50Gy, constrained at 54Gy
engine.add_optimization_objective("Parotid_L", "eud", 20.0, 1000, eud_exponent=8)  # Optimize toward 20Gy, constrained at 26Gy

# Check current optimization functions
constraints = engine.get_current_constraints()
objectives = engine.get_current_objectives()

# Optimize
engine.optimize_fluence()
metrics = engine.evaluate_plan()
```

## Logging System

### Log Structure

```json
{
  "session_id": "session_20241201_143022",
  "start_time": "2024-12-01T14:30:22",
  "patient_info": {
    "patient_file": "HEAD_AND_NECK.mat",
    "ct_dimensions": [256, 256, 150],
    "num_structures": 15
  },
  "planning_steps": [
    {
      "timestamp": "2024-12-01T14:30:25",
      "step_number": 1,
      "action_type": "tool_call",
      "description": "Executed start_matlab_engine",
      "parameters": {},
      "result": {"success": true},
      "execution_time_sec": 12.5
    }
  ],
  "objectives": [
    {
      "timestamp": "2024-12-01T14:32:15",
      "structure_name": "PTV",
      "objective_type": "square_deviation", 
      "dose_value": 60.0,
      "penalty": 1000.0
    }
  ],
  "optimization_history": [...],
  "metrics": [...],
  "final_results": {...}
}
```

### Viewing Logs

```python
from logger import PlanningLogger, print_session_summary

# Print summary of existing log
print_session_summary("logs/session_20241201_143022.json")

# Or access current session
agent.logger.print_log_summary()
```

## Configuration

### File Paths

Update paths in the test scripts:

```python
# In test_agent_planning.py or simple_agent_demo.py
matrad_path = "/path/to/your/matRad"      # matRad installation
patient_file = "your_patient_data.mat"   # Patient data file
```

### Agent Parameters

```python
# Maximum optimization iterations
max_iterations = 10

# OpenAI model settings
model = "gpt-4"
temperature = 0.1  # Lower = more deterministic
```

## Clinical Validation

### Quality Metrics

The agent evaluates plans using standard metrics:

- **Target Coverage**: V95%, V100%, D95%, D98%
- **OAR Sparing**: Mean dose, max dose, volume metrics
- **Plan Quality**: Conformity index, homogeneity index
- **Dose Statistics**: Min, max, mean, standard deviation

### Acceptance Criteria

Plans are evaluated against clinical acceptance criteria:

- Target structures receive prescribed dose ±5%
- OAR doses remain below tolerance levels
- No critical overdoses in normal tissues
- Reasonable optimization convergence

## Troubleshooting

### Common Issues

1. **MATLAB Engine Fails to Start**
   - Verify MATLAB installation and license
   - Check matRad path configuration
   - Ensure Python MATLAB Engine is installed

2. **Patient Data Loading Fails**
   - Verify .mat file exists and is readable
   - Check file contains 'ct' and 'cst' variables
   - Ensure proper MATLAB format

3. **Optimization Fails**
   - Check that objectives were added successfully
   - Verify dose influence matrix was calculated
   - Ensure sufficient objectives for all targets

4. **API Rate Limiting**
   - Reduce temperature or add delays
   - Use GPT-3.5 instead of GPT-4
   - Implement retry logic with backoff

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run agent with detailed output
```

## Contributing

### Development Setup

1. Clone repository and install dependencies
2. Set up development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements_agent.txt
   ```

3. Run tests:
   ```bash
   python -m pytest tests/
   ```

### Adding New Tools

1. Implement tool function in `MatRadEngine` class
2. Add tool definition to agent's `get_available_tools()`
3. Add execution logic to `execute_tool()` method
4. Update documentation and tests

### Guidelines

- Follow clinical radiotherapy best practices
- Maintain comprehensive logging
- Add proper error handling
- Include unit tests for new functionality
- Update documentation

## License

This project is part of the matRad radiotherapy planning system and follows the same license terms.

## Support

For questions about:
- **matRad functionality**: Refer to matRad documentation
- **Agent implementation**: Check GitHub issues
- **Clinical guidelines**: Consult QUANTEC/ESTRO publications

## References

1. matRad - A Multi-Modal Open Source Treatment Planning System
2. QUANTEC Guidelines for Normal Tissue Dose Constraints
3. ESTRO Guidelines for Radiotherapy Planning
4. OpenAI API Documentation for Function Calling 