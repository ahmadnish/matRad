# matRad Optimization Functionality Implementation Roadmap

## Overview

This document outlines the multi-session implementation plan to expose all matRad optimization functionality to the LLM agent. Each session builds upon previous work to eventually provide complete access to matRad's optimization capabilities.

## Session Status

### ✅ Session 1: EUD and DVH Objectives (COMPLETED)

**Implemented:**
- Added `eud`, `min_dvh`, `max_dvh` to objective type enums in tool schema
- Updated matRad engine mappings to include new objective classes
- Exposed EUD exponent parameter (`eud_exponent`) for EUD objectives
- Exposed volume percentage parameter (`volume_percent`) for DVH objectives  
- Enhanced objective creation logic to handle different parameter structures:
  - EUD: `{dose_value, exponent}`
  - DVH: `{dose_value, volume_percent}`
  - Standard: `{dose_value}`
- Updated system prompts with clinical guidance for new objectives
- Updated agent README with comprehensive objective documentation

**Files Modified:**
- `test_agent_planning.py`: Tool schema updates, system prompt enhancements
- `matrad_tools.py`: Engine mappings, parameter handling
- `README_Agent.md`: Documentation updates

**Testing Required:**
- Test EUD objective creation and optimization
- Test min_dvh and max_dvh objective creation and optimization
- Verify parameter handling for all objective types
- Validate clinical guidance in system prompts

---

### 🔄 Session 2: Constraint Framework (PENDING)

**Goals:**
- Implement comprehensive constraint framework
- Add `add_constraint` tool with all constraint types
- Add constraint-aware inspection and removal
- Update system prompts with constraint guidance

**Implementation Tasks:**

#### 2.1 Add Constraint Tool Schema
```python
# Add to get_available_tools() in test_agent_planning.py
{
    "type": "function",
    "function": {
        "name": "add_constraint",
        "description": "Add optimization constraint for a structure",
        "parameters": {
            "type": "object",
            "properties": {
                "structure_name": {"type": "string"},
                "constraint_type": {
                    "type": "string",
                    "enum": ["min_max_dose", "min_max_mean_dose", "min_max_eud", "min_max_dvh"]
                },
                "lower_bound": {"type": "number", "description": "Lower bound (optional)"},
                "upper_bound": {"type": "number", "description": "Upper bound (optional)"},
                "eud_exponent": {"type": "number", "description": "EUD exponent for EUD constraints"},
                "volume_percent": {"type": "number", "description": "Volume % for DVH constraints"},
                "rationale": {"type": "string"}
            }
        }
    }
}
```

#### 2.2 Engine Implementation
```python
# Add to matrad_tools.py
def add_constraint(self, structure_name: str, constraint_type: str, 
                  lower_bound: float = None, upper_bound: float = None,
                  eud_exponent: float = None, volume_percent: float = None,
                  rationale: str = None) -> Dict[str, Any]:
    """Add optimization constraint"""
    
    # Map constraint types to matRad classes
    constraint_class_map = {
        'min_max_dose': 'DoseConstraints.matRad_MinMaxDose',
        'min_max_mean_dose': 'DoseConstraints.matRad_MinMaxMeanDose', 
        'min_max_eud': 'DoseConstraints.matRad_MinMaxEUD',
        'min_max_dvh': 'DoseConstraints.matRad_MinMaxDVH'
    }
    
    # Create constraint with appropriate parameters
    # ...implementation details
```

#### 2.3 Enhanced Inspection
- Update `get_current_objectives` to handle both objectives and constraints
- Implement proper distinction between DoseObjectives and DoseConstraints
- Add constraint-specific information to inspection results

#### 2.4 Constraint Removal
- Update `remove_optimization_objective` to handle constraints
- Add constraint-specific removal logic
- Update tool schema to include constraint types

---

### 🔄 Session 3: Robustness Support (PENDING)

**Goals:**
- Add robustness parameter to all optimization functions
- Implement robustness setting logic
- Update prompts with robustness guidance

**Implementation Tasks:**

#### 3.1 Tool Schema Updates
```python
# Add robustness parameter to add_optimization_objective and add_constraint
"robustness": {
    "type": "string",
    "enum": ["none", "STOCH", "PROB", "VWWC", "VWWC_INV", "COWC", "OWC"],
    "description": "Robustness setting (default: none)"
}
```

#### 3.2 Engine Implementation
```python
# Update objective/constraint creation to set robustness
self.eng.eval(f"""
newObj.robustness = '{robustness}';
""", nargout=0)
```

#### 3.3 Clinical Guidance
- Add robustness strategy to system prompts
- Explain when to use different robustness settings
- Provide clinical examples

---

### 🔄 Session 4: Advanced Parameters (PENDING)

**Goals:**
- Expose all configurable parameters for objectives
- Add parameter validation
- Enhance parameter documentation

**Implementation Tasks:**

#### 4.1 MeanDose Parameters
- Expose difference function parameter (Linear/Quadratic)
- Add parameter to tool schema and engine

#### 4.2 Enhanced DVH Parameters
- Add more DVH parameter options
- Implement parameter validation

#### 4.3 Advanced EUD Options
- Add more EUD configuration options
- Implement parameter bounds checking

---

### 🔄 Session 5: Comprehensive Inspection (PENDING)

**Goals:**
- Rewrite optimization function inspection
- Implement unified objective/constraint handling
- Add detailed optimization function analysis

**Implementation Tasks:**

#### 5.1 Enhanced get_current_objectives
```python
def get_optimization_functions(self) -> Dict[str, Any]:
    """Get all optimization functions (objectives and constraints)"""
    # Unified handling of both types
    # Detailed parameter extraction
    # Structure-wise organization
```

#### 5.2 Advanced Analysis
- Add optimization function conflict detection
- Implement redundancy analysis
- Provide optimization suggestions

---

### 🔄 Session 6: Testing & Validation (PENDING)

**Goals:**
- Comprehensive testing of all functionality
- Integration tests
- Performance validation
- Documentation finalization

**Testing Strategy:**

#### 6.1 Unit Tests
- Test each objective/constraint type individually
- Parameter validation tests
- Error handling tests

#### 6.2 Integration Tests
- Full planning workflow tests
- Multi-objective optimization tests
- Robustness scenario tests

#### 6.3 Clinical Validation
- Test with real patient data
- Validate clinical guidelines implementation
- Performance benchmarking

---

## Implementation Guidelines

### Code Standards
- Maintain consistent error handling
- Use type hints throughout
- Comprehensive logging
- Clear documentation strings

### Clinical Safety
- Validate all dose values
- Implement parameter bounds checking
- Provide clear clinical rationales
- Follow established guidelines

### Testing Approach
- Test each session incrementally
- Maintain backward compatibility
- Document breaking changes
- Validate with real data

## File Structure

```
LLM_Agent_Planner/
├── test_agent_planning.py      # Main agent with tool schemas
├── matrad_tools.py            # Engine implementation
├── README_Agent.md            # User documentation
├── IMPLEMENTATION_ROADMAP.md  # This file
├── tests/                     # Test files (to be created)
│   ├── test_objectives.py
│   ├── test_constraints.py
│   └── test_integration.py
└── examples/                  # Usage examples
    └── advanced_planning.py
```

## Next Session Instructions

For **Session 2** (Constraints Framework):

1. **Start with tool schema**: Add `add_constraint` tool definition
2. **Implement engine method**: Create `add_constraint` in MatRadEngine
3. **Update inspection**: Modify `get_current_objectives` to handle constraints
4. **Test thoroughly**: Verify constraint creation and inspection
5. **Update prompts**: Add constraint guidance to system prompts
6. **Update README**: Document constraint functionality

### Key Implementation Points for Session 2:

1. **Constraint vs Objective Distinction**: 
   - Constraints have upper/lower bounds instead of penalty
   - Use `isinstance(obj, 'DoseConstraints.matRad_DoseConstraint')` check
   - Handle different parameter structures

2. **Parameter Mapping**:
   - MinMaxDose: `{min_dose, max_dose, method}`
   - MinMaxMeanDose: `{min_mean, max_mean}`
   - MinMaxEUD: `{exponent, min_eud, max_eud}`
   - MinMaxDVH: `{dose_ref, vol_min, vol_max}`

3. **Tool Integration**:
   - Add constraint execution to `execute_tool()` method
   - Update logging to handle constraints
   - Ensure proper error handling

Remember to test each implementation thoroughly before moving to the next session!
