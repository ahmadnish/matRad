# CC to Percent Conversion for DVH Objectives

## Overview

This helper function converts absolute volumes in cubic centimeters (cc) to percentages for use in DVH-based objectives. This is essential for clinical constraints like D0.03cc (maximum dose to 0.03cc of spinal cord/brainstem).

## Function Interface

### `convert_cc_to_percent(structure_name, volume_cc)`

**Parameters:**
- `structure_name` (string): Name of the structure to analyze
- `volume_cc` (float): Volume in cubic centimeters to convert (e.g., 0.03 for D0.03cc constraints)

**Returns:**
```python
{
    "success": bool,
    "structure_name": str,
    "target_volume_cc": float,
    "volume_percent": float,        # Percentage (0-100)
    "volume_fraction": float,       # Fraction (0-1)
    "structure_info": {
        "total_volume_cc": float,   # Total structure volume in cc
        "num_voxels": int,          # Number of voxels in structure
        "voxel_volume_cc": float    # Volume per voxel in cc
    },
    "message": str
}
```

## Clinical Use Cases

### 1. Critical OAR Dose Constraints

**Spinal Cord D0.03cc ≤ 45 Gy:**
```python
# Step 1: Convert cc to percentage
result = convert_cc_to_percent("SPINAL_CORD", 0.03)
volume_percent = result["volume_percent"]

# Step 2: Apply constraint using percentage
add_optimization_objective(
    "SPINAL_CORD", 
    "max_dvh", 
    dose_value=45, 
    volume_percent=volume_percent,
    penalty=2000,
    rationale="Critical cord tolerance per TG-101"
)
```

**Brainstem D0.03cc ≤ 54 Gy:**
```python
result = convert_cc_to_percent("BRAIN_STEM", 0.03)
add_optimization_objective(
    "BRAIN_STEM", 
    "max_dvh", 
    dose_value=54, 
    volume_percent=result["volume_percent"],
    penalty=2000,
    rationale="Brainstem tolerance per QUANTEC"
)
```

### 2. Other Volume-Based Constraints

**1cc and 10cc spill constraints:**
```python
# For BODY_minus_PTVs spill control
result_1cc = convert_cc_to_percent("BODY_minus_PTVs", 1.0)
result_10cc = convert_cc_to_percent("BODY_minus_PTVs", 10.0)

# Apply spill constraints
add_optimization_objective("BODY_minus_PTVs", "max_dvh", 
                         dose_value=77.0, volume_percent=result_1cc["volume_percent"])
add_optimization_objective("BODY_minus_PTVs", "max_dvh", 
                         dose_value=73.5, volume_percent=result_10cc["volume_percent"])
```

## Integration with Head & Neck Planning Playbook

### Step 1 - Skeleton (Hard OAR Constraints)

Use the conversion function before adding critical OAR constraints:

```python
# 1. Convert volumes for critical structures
cord_003cc = convert_cc_to_percent("SPINAL_CORD", 0.03)
brainstem_003cc = convert_cc_to_percent("BRAIN_STEM", 0.03)

# 2. Apply hard constraints
add_optimization_objective("SPINAL_CORD", "max_dvh", 
                         dose_value=45, volume_percent=cord_003cc["volume_percent"],
                         penalty=2000, rationale="Critical cord tolerance")

add_optimization_objective("BRAIN_STEM", "max_dvh", 
                         dose_value=54, volume_percent=brainstem_003cc["volume_percent"],
                         penalty=2000, rationale="Critical brainstem tolerance")
```

### Step 2 - Spill Control

Use for body spill constraints:

```python
# Convert spill volumes
body_1cc = convert_cc_to_percent("BODY_minus_PTVs", 1.0)
body_10cc = convert_cc_to_percent("BODY_minus_PTVs", 10.0)

# Apply spill constraints (110% and 105% of prescription)
add_optimization_objective("BODY_minus_PTVs", "max_dvh",
                         dose_value=77.0, volume_percent=body_1cc["volume_percent"])
add_optimization_objective("BODY_minus_PTVs", "max_dvh", 
                         dose_value=73.5, volume_percent=body_10cc["volume_percent"])
```

## When to Use

### Required Usage:
1. **Critical OAR constraints**: Always use for D0.03cc constraints on spinal cord, brainstem
2. **Protocol compliance**: When specific cc-based constraints are mandated
3. **Accurate dose limits**: For precise volume-dose constraints in clinical protocols

### Optional Usage:
1. **Small volume constraints**: Any DVH constraint with volumes < 5% of structure
2. **Spill control**: Body/skin constraints at specific cc volumes
3. **Research protocols**: When exact volume matching is required

## Fallback Strategy

If the conversion function is unavailable or fails:

```python
# Use conservative small percentages
# 0.03cc typically represents 0.1-1% of most OAR volumes
add_optimization_objective("SPINAL_CORD", "max_dvh", 
                         dose_value=45, volume_percent=0.5,  # Conservative 0.5%
                         penalty=2000, rationale="Conservative cord limit")
```

## Technical Details

### Volume Calculation:
- **Voxel volume** = resolution_x × resolution_y × resolution_z (mm³)
- **Structure volume** = num_voxels × voxel_volume_cc (cc)
- **Percentage** = 100 × (target_cc / total_cc)
- **Fraction** = target_cc / total_cc

### Validation:
- Ensures percentages are within [0, 100] range
- Ensures fractions are within [0, 1] range
- Handles zero-volume structures gracefully
- Provides detailed structure information for verification

## Example Results

For a typical spinal cord structure:
```python
convert_cc_to_percent("SPINAL_CORD", 0.03)
# Returns:
{
    "success": True,
    "structure_name": "SPINAL_CORD",
    "target_volume_cc": 0.03,
    "volume_percent": 0.16,           # 0.16% of total volume
    "volume_fraction": 0.0016,        # 0.16% as fraction
    "structure_info": {
        "total_volume_cc": 19.125,    # Total spinal cord volume
        "num_voxels": 425,            # Number of voxels
        "voxel_volume_cc": 0.045      # Volume per voxel
    },
    "message": "Converted 0.03 cc to 0.16% for SPINAL_CORD"
}
```

## Error Handling

Common error scenarios and solutions:

1. **Structure not found**: Check structure name spelling against available structures
2. **Zero volume structure**: Function returns 0% safely
3. **Very large target volumes**: Function caps at 100% automatically
4. **MATLAB engine issues**: Ensure patient data is loaded and engine is running

## Integration with Agent Planning

The function is automatically available as a tool in the LLM agent planning system:

```python
# Agent can call this directly:
agent.execute_tool('convert_cc_to_percent', {
    'structure_name': 'SPINAL_CORD',
    'volume_cc': 0.03
})
```

This enables the agent to automatically handle precise volume-dose constraints in clinical treatment planning scenarios.
