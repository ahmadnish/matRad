# Advanced Structure Management for LLM Agent Planning

## Overview

This module extends the LLM Agent Planning system with advanced structure management capabilities, enabling the creation of ring structures and performing VOI (Volume of Interest) operations. These features allow for more sophisticated treatment planning strategies and dose optimization.

## Environment Setup

**IMPORTANT**: Before running any tests or MATLAB engine related functionality, you must source the project environment:

```bash
source /Users/ahmadneishabouri/matlab_env/bin/activate
```

This environment contains the required Python packages including the MATLAB Engine for Python. All test scripts and agent functionality require this environment to be active.

## New Functionality

### 1. Ring Structure Creation (`create_ring_structures`)

Creates concentric ring VOIs around any reference structure for dose gradient optimization.

#### Interface
```python
create_ring_structures(
    reference_structure: str,      # Name of reference structure
    ring_margins_mm: List[float],  # List of ring margins in mm
    inner_margin_mm: float = 0,    # Inner buffer margin in mm
    visualize: bool = False        # Create visualization
)
```

#### Clinical Applications
- **Dose Gradient Control**: Create rings around critical structures (brainstem, optic structures) to control dose fall-off
- **Evaluation Zones**: Generate evaluation rings around PTVs to assess dose conformity
- **Optimization Constraints**: Apply graduated dose constraints to ring structures

#### Examples
```python
# Create gradient control rings around brainstem
create_ring_structures("Brainstem", [5, 10, 15])
# Creates: BrainstemRing5mm, BrainstemRing10mm, BrainstemRing15mm

# Create evaluation rings around PTV with 2mm buffer
create_ring_structures("PTV", [5, 15, 25], inner_margin_mm=2)
# Creates: PTVRing5mm, PTVRing15mm, PTVRing25mm (starting 2mm from PTV edge)
```

### 2. VOI Operations (`perform_voi_operation`)

Performs set operations (union, intersection, difference) between two structures to create new combined structures.

#### Interface
```python
perform_voi_operation(
    structure1: str,           # First structure name
    structure2: str,           # Second structure name  
    operation: str,            # 'union', 'intersect', or 'setdiff'
    new_structure_name: str    # Name for new structure
)
```

#### Operation Types
- **`union`**: Combines both structures (A ∪ B)
- **`intersect`**: Only overlapping regions (A ∩ B)  
- **`setdiff`**: First structure minus second (A - B)

#### Clinical Applications

##### PTV Evaluation Structures
```python
# Create PTV evaluation volume excluding brainstem overlap
perform_voi_operation("PTV", "Brainstem", "setdiff", "PTV_eval")
# Use PTV_eval for coverage objectives instead of original PTV
```

##### Combined Target Volumes
```python
# Union multiple PTVs for simultaneous boost planning
perform_voi_operation("PTV1", "PTV2", "union", "PTV_combined")
```

##### Overlap Analysis
```python
# Identify problematic overlaps
perform_voi_operation("PTV", "SpinalCord", "intersect", "PTV_Cord_overlap")
```

##### Avoidance Zones
```python
# Create body excluding critical structures
perform_voi_operation("BODY", "Brainstem", "setdiff", "BODY_minus_Brainstem")
```

## Implementation Details

### MATLAB Function Integration

#### Ring Creation
- Uses `matRad_VOICreateRings.m` from `userdata/scripts/`
- Leverages `matRad_addMargin.m` for precise voxel expansion
- Supports 26-connectivity for smooth margin expansion
- Automatically handles voxel-to-mm conversions based on CT resolution

#### VOI Operations  
- Uses `matRad_VOIOperations.m` from `userdata/scripts/`
- Performs operations on linear voxel indices for efficiency
- Automatically inherits appropriate structure types and colors
- Handles CST (Clinical Structure Template) updates

### Error Handling
- Validates structure names against loaded patient data
- Checks for valid operation types
- Provides detailed error messages for troubleshooting
- Ensures MATLAB functions are properly added to path

## Agent Tool Integration

### Tool Definitions
Both functions are integrated as LLM agent tools with structured parameter validation:

```json
{
  "name": "create_ring_structures",
  "description": "Create concentric ring VOIs around a reference structure",
  "parameters": {
    "reference_structure": "string",
    "ring_margins_mm": "array of numbers", 
    "inner_margin_mm": "number (optional)",
    "visualize": "boolean (optional)"
  }
}
```

```json
{
  "name": "perform_voi_operation", 
  "description": "Perform VOI operations between two structures",
  "parameters": {
    "structure1": "string",
    "structure2": "string",
    "operation": "enum: union|intersect|setdiff",
    "new_structure_name": "string"
  }
}
```

## Clinical Workflow Integration

### Advanced Planning Strategy

1. **Structure Analysis Phase**
   - Load patient data and examine structure relationships
   - Identify critical structure overlaps and proximity issues
   - Plan structure modifications based on clinical priorities

2. **Structure Creation Phase**
   - Create PTV evaluation volumes excluding critical OARs
   - Generate ring structures around critical OARs for gradient control
   - Combine target volumes if simultaneous boost planning needed

3. **Optimization Setup Phase**
   - Apply coverage objectives to evaluation structures (not original PTVs)
   - Use ring structures for graduated dose constraints
   - Set up gradient objectives with decreasing penalties on rings

4. **Plan Evaluation Phase**
   - Evaluate both original structures and derived structures
   - Assess dose gradients using ring structure metrics
   - Verify coverage on evaluation volumes

### Structure Naming Conventions

- **Ring Structures**: Auto-generated as `{StructureName}Ring{X}mm`
  - Example: `BrainstemRing5mm`, `PTVRing15mm`
  
- **VOI Operations**: Use descriptive names indicating the operation
  - Examples: `PTV_minus_Brainstem`, `Combined_PTVs`, `PTV_eval`

- **Evaluation Structures**: Use `_eval` suffix for clinical evaluation volumes
  - Examples: `PTV_eval`, `GTV_eval`

## Usage Examples

### Example 1: Brainstem Sparing with Gradient Control
```python
# 1. Create gradient control rings around brainstem
create_ring_structures("Brainstem", [3, 6, 10])

# 2. Create PTV evaluation volume excluding brainstem
perform_voi_operation("PTV", "Brainstem", "setdiff", "PTV_eval") 

# 3. Apply graduated objectives
# - Hard constraint: Brainstem < 45 Gy
# - Gradient: BrainstemRing3mm < 50 Gy, BrainstemRing6mm < 55 Gy  
# - Coverage: PTV_eval coverage objectives
```

### Example 2: Multi-Target Planning
```python
# 1. Combine multiple PTVs
perform_voi_operation("PTV1", "PTV2", "union", "PTV_combined")

# 2. Create evaluation volume excluding all critical OARs
perform_voi_operation("PTV_combined", "SpinalCord", "setdiff", "PTV_eval_step1")
perform_voi_operation("PTV_eval_step1", "Brainstem", "setdiff", "PTV_eval_final")

# 3. Apply coverage objectives to PTV_eval_final
```

### Example 3: Complex Head & Neck Planning
```python
# 1. Create comprehensive ring system
create_ring_structures("Brainstem", [3, 6, 10])
create_ring_structures("SpinalCord", [3, 6])
create_ring_structures("OpticNerve_L", [2, 5])
create_ring_structures("OpticNerve_R", [2, 5])

# 2. Create evaluation structures
perform_voi_operation("PTV", "Brainstem", "setdiff", "PTV_eval_step1")
perform_voi_operation("PTV_eval_step1", "SpinalCord", "setdiff", "PTV_eval")

# 3. Create dose falloff zone
create_ring_structures("PTV", [5, 15, 25], inner_margin_mm=2)

# 4. Apply sophisticated objective set with gradient control
```

## Future Extensions

### Planned Enhancements
1. **Multi-step VOI Operations**: Chain multiple operations automatically
2. **Template-based Structure Creation**: Pre-defined structure templates for common anatomical sites
3. **Automated Overlap Detection**: Identify and resolve structure overlaps automatically
4. **Dynamic Ring Generation**: Adaptive ring spacing based on dose gradients
5. **Structure Quality Metrics**: Validate structure quality and suggest improvements

### Integration Opportunities
- **DVH Analysis**: Extend DVH analysis to include derived structures
- **Plan Comparison**: Compare plans with and without advanced structures
- **Optimization Monitoring**: Track convergence improvement with advanced structures
- **Clinical Reporting**: Generate reports including derived structure metrics

## Technical Notes

### Performance Considerations
- Ring creation scales with number of margins and structure size
- VOI operations are performed on linear indices for efficiency  
- Large structures (>100,000 voxels) may require additional processing time
- Visualization should be used sparingly for large ring sets

### Memory Usage
- Each ring structure stores full voxel masks
- Consider memory usage for patients with many large structures
- MATLAB workspace size may increase significantly with complex structure hierarchies

### Compatibility
- Requires matRad installation with geometry functions
- Compatible with all matRad optimization engines
- Tested with head & neck and brain cases
- Should work with any anatomical site

## Troubleshooting

### Common Issues
1. **Structure Not Found**: Verify structure names using `get_structure_information()`
2. **Path Issues**: Ensure `userdata/scripts/` is accessible from matRad path
3. **Memory Errors**: Reduce number of rings or use smaller margins for large structures
4. **Visualization Errors**: Disable visualization for automated planning workflows

### Error Messages
- `"Reference structure 'X' not found"`: Check spelling and available structures
- `"Invalid operation 'X'"`: Use only 'union', 'intersect', or 'setdiff'
- `"Ring creation failed"`: Check MATLAB function availability and parameters
- `"VOI operation failed"`: Verify both structures exist and have valid voxel data

## Conclusion

The advanced structure management functionality significantly enhances the LLM Agent Planning system's capability to handle complex clinical scenarios. By enabling sophisticated structure manipulations, the system can now address challenging planning situations that require gradient control, overlap resolution, and advanced evaluation strategies.

These tools are particularly valuable for:
- Head & neck cases with complex anatomy
- Brain cases requiring precise gradient control
- Multi-target treatments
- Re-irradiation scenarios
- Research applications requiring sophisticated dose analysis

The integration maintains the system's ease of use while providing powerful capabilities for expert-level treatment planning optimization.
