# Site-Agnostic LLM Agent for Radiotherapy Planning

This document describes how to use the enhanced LLM agent that can plan for different cancer sites with configurable treatment parameters.

## Overview

The agent has been updated to be **site-agnostic**, meaning it can automatically adapt its planning strategy, clinical guidelines, and optimization approach based on the cancer site and treatment configuration you provide.

## Key Features

### 🎯 **Configurable Treatment Parameters**
- **Cancer Site**: Specify the type of cancer (lung, head_and_neck, prostate, breast, etc.)
- **Prescription Dose**: Total dose in Gy, or multi-level dict for SIB planning
- **Number of Fractions**: Treatment fractions
- **Treatment Technique**: IMRT, VMAT, SBRT, etc.
- **SIB Support**: Simultaneous Integrated Boost with multiple dose levels

### 🧠 **Site-Specific Intelligence**
- **Automatic Guidelines**: Loads QUANTEC/ESTRO constraints for the specified site
- **Optimized Beam Arrangements**: Uses clinically appropriate beam angles
- **Site-Specific Priorities**: Follows established clinical protocols
- **Adaptive Prompts**: Generates specialized planning instructions

### 📋 **Supported Cancer Sites**

| Site | Aliases | Key Features |
|------|---------|--------------|
| **Lung** | `lung`, `nsclc`, `lung_cancer` | Lung V20 ≤ 35%, pneumonitis prevention, 6-field IMRT |
| **Head & Neck** | `head_and_neck`, `hnc`, `oropharynx` | Parotid sparing, cord/brainstem protection, SIB planning |
| **Prostate** | `prostate` | Rectum/bladder sparing, high-precision delivery |
| **Breast** | `breast` | Heart/lung sparing, tangential fields |
| **Generic** | Any other site | Adaptable framework for other sites |

## Usage Methods

### Method 1: Direct Function Call

```python
from test_agent_planning import main, TreatmentConfiguration

# Lung cancer example
main(
    cancer_site="lung",
    prescription_dose=60.0,
    num_fractions=30,
    patient_file="lung_patient.mat",
    treatment_technique="IMRT"
)

# Head and neck example with SIB
main(
    cancer_site="head_and_neck",
    prescription_dose={"PTV6996": 70.0, "PTV5610": 56.0},  # SIB prescription
    num_fractions=35,
    patient_file="Head_and_Neck_1.mat"
)

# Head and neck example (single dose)
main(
    cancer_site="head_and_neck", 
    prescription_dose=70.0,
    num_fractions=35,
    patient_file="HandN_newskin.mat",
    treatment_technique="IMRT"
)
```

### Method 2: Command Line Interface

```bash
# Lung cancer planning (60 Gy in 30 fractions)
python run_site_specific_planning.py --site lung --dose 60 --fractions 30 --patient lung_patient.mat

# Head and neck planning (70 Gy in 35 fractions)
python run_site_specific_planning.py --site head_and_neck --dose 70 --fractions 35 --patient HandN_newskin.mat

# Prostate planning (78 Gy in 39 fractions)
python run_site_specific_planning.py --site prostate --dose 78 --fractions 39 --patient prostate_patient.mat

# SBRT lung planning (50 Gy in 5 fractions)
python run_site_specific_planning.py --site lung --dose 50 --fractions 5 --patient lung_sbrt.mat --technique SBRT
```

### Method 3: Interactive Examples

```bash
# Run interactive lung planning example
python examples/lung_planning_example.py
```

## Site-Specific Planning Details

### 🫁 **Lung Cancer Planning**

**Clinical Priorities:**
1. Spinal cord D_max ≤ 45 Gy (critical safety)
2. Lung V20 ≤ 35% and mean dose ≤ 20 Gy (pneumonitis prevention)
3. Target coverage V95% ≥ 95%
4. Heart constraints (mean ≤ 26 Gy)
5. Esophagus constraints (mean ≤ 34 Gy, D_max ≤ 74 Gy)

**Beam Configuration:**
- Default: 6-field IMRT [0°, 45°, 135°, 180°, 225°, 315°]
- Avoids direct AP/PA beams through contralateral lung

**Key VOI Operations:**
- `LUNG_MINUS_GTV`: Excludes tumor from lung dose calculations
- `LUNG_TOTAL`: Combined bilateral lung structure
- Gradient rings around PTV for conformity

**Optimization Strategy:**
```
Stage 1: Critical Safety (Cord + Basic Coverage)
Stage 2: Lung Sparing (Primary concern - V20, mean dose)  
Stage 3: Secondary OARs (Heart, esophagus, refinement)
```

### 🗣️ **Head & Neck Cancer Planning**

**Clinical Priorities:**
1. Hard OAR maxima (D0.03cc limits for cord/brainstem)
2. Target coverage (V100, D98)
3. Target hotspots (D2)
4. Gradient/spill control
5. Parotid mean dose objectives

**Beam Configuration:**
- Default: 5-field IMRT [0°, 72°, 144°, 216°, 288°]

**Key Features:**
- Simultaneous integrated boost (SIB) support
- PTV evaluation structures (PTV_eval = PTV_low \ PTV_high)
- cc→% conversion for D0.03cc constraints
- Ring structures for gradient optimization

## Configuration Examples

### Conventional Fractionation Examples

```python
# Standard lung cancer
TreatmentConfiguration(
    cancer_site="lung",
    prescription_dose=60.0,
    num_fractions=30,  # 2.0 Gy/fx
    treatment_technique="IMRT"
)

# Head and neck with SIB
TreatmentConfiguration(
    cancer_site="head_and_neck", 
    prescription_dose=70.0,
    num_fractions=35,  # 2.0 Gy/fx
    treatment_technique="IMRT"
)

# Prostate cancer
TreatmentConfiguration(
    cancer_site="prostate",
    prescription_dose=78.0,
    num_fractions=39,  # 2.0 Gy/fx
    treatment_technique="IMRT"
)
```

### Hypofractionated Examples

```python
# Lung SBRT
TreatmentConfiguration(
    cancer_site="lung",
    prescription_dose=50.0,
    num_fractions=5,   # 10.0 Gy/fx
    treatment_technique="SBRT"
)

# Prostate hypofractionation
TreatmentConfiguration(
    cancer_site="prostate",
    prescription_dose=60.0,
    num_fractions=20,  # 3.0 Gy/fx
    treatment_technique="IMRT"
)
```

## Guidelines Integration

The agent automatically loads site-specific guidelines from YAML files:

- `lung_planning_guidelines.yaml`: Lung-specific QUANTEC constraints
- `quantec_estro_guidelines.yaml`: General QUANTEC/ESTRO guidelines
- Additional site files can be added as needed

### Automatic Features:
- **Structure Aliases**: Maps various naming conventions to canonical names
- **Dose Constraints**: Loads appropriate OAR limits for the site
- **Beam Arrangements**: Uses clinically validated beam configurations
- **Optimization Objectives**: Applies site-appropriate penalty weights

## Clinical Validation

### Lung Cancer Validation
- ✅ QUANTEC lung constraints (V20 ≤ 35%, mean ≤ 20 Gy)
- ✅ RTOG 0617 protocol compliance
- ✅ Pneumonitis risk minimization
- ✅ Appropriate beam arrangements

### Head & Neck Validation  
- ✅ QUANTEC OAR constraints
- ✅ SIB planning capability
- ✅ Parotid sparing protocols
- ✅ Critical structure protection

## Advanced Usage

### Custom Site Guidelines

To add a new cancer site:

1. Create a new guidelines YAML file (e.g., `brain_planning_guidelines.yaml`)
2. Define structure aliases, constraints, and beam arrangements
3. Add site detection logic in `_generate_site_specific_prompt()`
4. Implement site-specific prompt method

### Integration with Existing Workflows

```python
# Use with existing patient data
agent = IMRTPlanningAgent(
    matrad_path="/path/to/matRad",
    treatment_config=TreatmentConfiguration(
        cancer_site="lung",
        prescription_dose=60.0,
        num_fractions=30
    )
)

# Run planning session
results = agent.run_planning_session("patient.mat", max_iterations=200)
```

## Troubleshooting

### Common Issues

1. **Guidelines not loading**: Check that YAML files are in the `guidelines/` directory
2. **Site not recognized**: Verify site name matches supported aliases
3. **Beam configuration errors**: Ensure beam angles are valid (0-359°)
4. **Dose validation**: Check that dose/fractionation is clinically reasonable

### Debug Mode

Enable detailed logging by checking the session logs in the `logs/` directory.

## Future Enhancements

- 🔄 **Additional Sites**: Prostate, breast, brain, spine
- 🎯 **SBRT Protocols**: Enhanced hypofractionation support  
- 📊 **Outcome Prediction**: Integration with NTCP models
- 🤖 **Auto-Contouring**: Integration with AI segmentation
- 📈 **Plan Comparison**: Multi-technique optimization

## Examples Directory

The `examples/` directory contains:
- `lung_planning_example.py`: Interactive lung cancer planning
- Additional site-specific examples (coming soon)

## Conclusion

The site-agnostic agent provides a flexible, clinically-validated framework for radiotherapy planning across multiple cancer sites. By simply specifying the cancer site, prescription dose, and fractionation, the agent automatically adapts its planning strategy to follow established clinical protocols and guidelines.

This approach ensures:
- **Clinical Compliance**: Follows QUANTEC/ESTRO guidelines
- **Site Optimization**: Uses appropriate priorities for each cancer type  
- **Flexibility**: Easy to extend to new sites and protocols
- **Consistency**: Standardized approach across different planners

