# Warm-Start Optimization Implementation

This document describes the implementation of warm-start optimization capability in the matRad agentic planning system.

## Overview

Warm-start optimization allows the system to use previously optimized fluence weights as initial values for subsequent optimizations. This can significantly improve convergence speed and potentially find better local optima when making incremental adjustments to the treatment plan.

## Implementation Details

### 1. MatRadEngine Changes (`matrad_tools.py`)

#### New Instance Variables
```python
# Store optimized weights for warm-start
self.optimized_weights = None
self.weights_available = False
```

#### Modified `optimize_fluence()` Method
- Added `use_previous_weights` parameter (default: False)
- Automatically stores optimized weights after successful optimization
- Uses `resultGUI.wUnsequenced` from matRad as the weight source
- Returns additional information about start type and weights

#### New `clear_optimized_weights()` Method
- Manually clears stored weights when needed
- Useful when making major changes to beam configuration

#### Automatic Weight Clearing
- `set_beam_angles()` now automatically clears weights when beam configuration changes
- This prevents using invalid weights from different beam geometries

### 2. Agent Tool Definition (`test_agent_planning.py`)

#### Updated Tool Schema
```json
{
    "name": "optimize_fluence",
    "description": "Run fluence optimization... Can use previous optimization results as starting point...",
    "parameters": {
        "properties": {
            "use_previous_weights": {
                "type": "boolean",
                "description": "If true, use weights from previous optimization as initial values for warm-start"
            }
        }
    }
}
```

#### Enhanced Execution Logging
- Tracks warm-start vs cold-start information
- Logs weight storage success/failure
- Records optimization start type for analysis

### 3. System Prompt Updates

Added optimization strategy guidance:
- First optimization: Use cold-start (default behavior)
- Subsequent optimizations: Use warm-start for faster convergence
- When to use each approach (incremental vs major changes)

## Usage Examples

### Basic Usage
```python
# First optimization (cold-start)
result1 = engine.optimize_fluence()

# Subsequent optimization (warm-start)
result2 = engine.optimize_fluence(use_previous_weights=True)
```

### Agent Tool Calls
```python
# Cold-start
{"tool_name": "optimize_fluence"}

# Warm-start
{"tool_name": "optimize_fluence", "use_previous_weights": true}
```

### When Weights Are Cleared
- When `set_beam_angles()` is called (automatic)
- When `clear_optimized_weights()` is called (manual)
- When engine is restarted

## Technical Details

### Weight Storage
- Weights are extracted from `resultGUI.wUnsequenced` after optimization
- Converted from MATLAB array to numpy array for storage
- Stored as flattened 1D array for efficiency

### Weight Passing to MATLAB
- Weights are passed as `wInit` parameter to `matRad_fluenceOptimization`
- matRad function signature: `matRad_fluenceOptimization(dij,cst,pln,wInit)`
- MATLAB handles the initialization logic internally

### Error Handling
- Graceful fallback to cold-start if weights are unavailable
- Warning messages when weight extraction fails
- Safe handling of MATLAB array conversion

## Benefits

1. **Faster Convergence**: Warm-start typically converges faster than cold-start
2. **Better Local Optima**: May find better solutions by starting from a good initial point
3. **Iterative Refinement**: Enables efficient plan refinement workflows
4. **Automatic Management**: System automatically handles weight storage and clearing

## Testing

A comprehensive test script (`examples/test_warm_start.py`) demonstrates:
- Cold-start vs warm-start timing comparison
- Weight storage and retrieval
- Automatic weight clearing
- Proper fallback behavior

## Example Agent Workflow

```
1. optimize_fluence() → Cold-start, weights stored
2. Analyze plan with DVH analysis
3. Add/modify objectives based on analysis
4. optimize_fluence(use_previous_weights=true) → Warm-start from previous weights
5. Repeat steps 2-4 for iterative improvement
```

This implementation provides a solid foundation for efficient iterative treatment planning optimization in the agentic system. 