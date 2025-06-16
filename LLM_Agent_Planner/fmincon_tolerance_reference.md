
# fmincon Tolerance Reference for matRad

## Problem: Early Stopping
fmincon may stop early with the message:
"Optimization stopped because the relative changes in all elements of x are less than options.StepTolerance = 1.000000e-10"

## Solution: Adjust Tolerances

### 1. StepTolerance (Most Important)
- **Controls**: Minimum relative change in optimization variables between iterations
- **Default**: 1e-10 (very strict)
- **Recommended**: 1e-4 to 1e-6 (less strict)
- **Impact**: Main cause of early stopping

### 2. ConstraintTolerance  
- **Controls**: Maximum acceptable constraint violation
- **Default**: 1e-6 (very strict)
- **Recommended**: 1e-3 to 1e-4 (more relaxed)
- **Impact**: Affects feasibility requirements

### 3. OptimalityTolerance
- **Controls**: First-order optimality conditions
- **Default**: 1e-6
- **Recommended**: 1e-3 to 1e-4
- **Impact**: Controls optimality stopping criteria

### 4. FunctionTolerance
- **Controls**: Minimum change in objective function
- **Default**: 1e-6
- **Recommended**: 1e-4
- **Impact**: Function value change sensitivity

## Implementation in matRad

```matlab
% Configure in plan structure
pln.propOpt.fmincon.StepTolerance = 1e-4;          % Prevent early stopping
pln.propOpt.fmincon.ConstraintTolerance = 1e-3;    % Relax constraints
pln.propOpt.fmincon.OptimalityTolerance = 1e-3;    % Relax optimality
pln.propOpt.fmincon.FunctionTolerance = 1e-4;      % Function change tolerance
pln.propOpt.fmincon.MaxIterations = 200;           % Increase max iterations
```

## Trade-offs
- **Looser tolerances**: Longer runtime, potentially better solutions
- **Stricter tolerances**: Faster convergence, may stop too early
- **Balance**: Choose based on problem complexity and time constraints
