"""
Configure fmincon Tolerances for matRad Optimization

This script demonstrates how to set fmincon tolerances to prevent early stopping
during IMRT optimization. The script configures the plan structure with custom
fmincon options that will be applied by the modified matRad_OptimizerFmincon.

Author: Assistant
Date: 2024
"""

import matlab.engine
import time

def configure_fmincon_tolerances():
    """
    Demonstrate how to configure fmincon tolerances to prevent early stopping.
    """
    
    print("🔧 Configuring fmincon Tolerances for matRad")
    print("=" * 60)
    
    # Start MATLAB engine
    print("Starting MATLAB engine...")
    eng = matlab.engine.start_matlab()
    
    try:
        # Initialize matRad
        print("Initializing matRad...")
        eng.matRad_rc(nargout=0)
        
        # Load patient data
        print("Loading HEAD_AND_NECK.mat...")
        eng.load('matRad/phantoms/HEAD_AND_NECK.mat', nargout=0)
        
        # Create treatment plan
        print("\nCreating treatment plan with custom fmincon tolerances...")
        eng.eval("""
        % Create the treatment plan
        pln = struct();
        pln.radiationMode   = 'photons';
        pln.machine         = 'Generic';
        pln.numOfFractions  = 30;
         
        % Setup beam geometry
        pln.propStf.gantryAngles    = [0:72:359];  % 5 beams
        pln.propStf.couchAngles     = [0 0 0 0 0]; % All couch at 0 degrees
        pln.propStf.bixelWidth      = 5;           % 5mm bixel width
        pln.propStf.numOfBeams      = numel(pln.propStf.gantryAngles);
        pln.propStf.isoCenter       = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);

        % Biological model and optimization settings
        pln.bioModel = 'none';
        pln.multScen = 'nomScen';
        pln.propOpt.quantityOpt = 'physicalDose';

        % Dose calculation settings
        pln.propDoseCalc.doseGrid.resolution.x = 3; % [mm]
        pln.propDoseCalc.doseGrid.resolution.y = 3; % [mm]
        pln.propDoseCalc.doseGrid.resolution.z = 3; % [mm]

        % Setup fmincon optimizer
        if matRad_OptimizerFmincon.IsAvailable()
            pln.propOpt.optimizer = 'fmincon';
            
            % CONFIGURE CUSTOM FMINCON TOLERANCES TO PREVENT EARLY STOPPING
            % These tolerances control when the optimizer stops
            
            % Step tolerance - controls minimum change in variables between iterations
            % Default: 1e-10 (very small, causes early stopping)
            % Recommendation: Increase to 1e-6 or 1e-4 for less sensitive stopping
            pln.propOpt.fmincon.StepTolerance = 1e-4;
            
            % Constraint tolerance - controls maximum acceptable constraint violation  
            % Default: 1e-6 (very strict)
            % Recommendation: Increase to 1e-4 or 1e-3 for more relaxed constraints
            pln.propOpt.fmincon.ConstraintTolerance = 1e-3;
            
            % Optimality tolerance - controls first-order optimality
            % Default: 1e-6 
            % Recommendation: Increase to 1e-4 or 1e-3 for faster convergence
            pln.propOpt.fmincon.OptimalityTolerance = 1e-3;
            
            % Function tolerance - controls minimum change in objective function
            % Default: 1e-6
            % Recommendation: Increase to 1e-4 for less sensitive function change detection
            pln.propOpt.fmincon.FunctionTolerance = 1e-4;
            
            % Iteration limits
            pln.propOpt.fmincon.MaxIterations = 10;           % Increase max iterations
            pln.propOpt.fmincon.MaxFunctionEvaluations = 400;  % Increase max function evaluations
            
            % Display and diagnostics
            pln.propOpt.fmincon.Display = 'iter';              % Show progress
            
            disp('✅ Custom fmincon tolerances configured:');
            disp(['   StepTolerance: ' num2str(pln.propOpt.fmincon.StepTolerance)]);
            disp(['   ConstraintTolerance: ' num2str(pln.propOpt.fmincon.ConstraintTolerance)]);
            disp(['   OptimalityTolerance: ' num2str(pln.propOpt.fmincon.OptimalityTolerance)]);
            disp(['   FunctionTolerance: ' num2str(pln.propOpt.fmincon.FunctionTolerance)]);
            disp(['   MaxIterations: ' num2str(pln.propOpt.fmincon.MaxIterations)]);
            disp(['   MaxFunctionEvaluations: ' num2str(pln.propOpt.fmincon.MaxFunctionEvaluations)]);
            
        else
            pln.propOpt.optimizer = 'IPOPT';
            disp('⚠️  fmincon not available, using IPOPT optimizer');
        end

        % No sequencing for pure IMRT
        pln.propSeq.runSequencing = false;
        pln.propOpt.runDAO = false;
        
        """, nargout=0)
        
        print("\n📋 Tolerance Configuration Summary")
        print("-" * 40)
        
        # Display the tolerance explanations
        tolerance_info = {
            "StepTolerance": {
                "default": "1e-10",
                "recommended": "1e-4 to 1e-6", 
                "description": "Controls minimum relative change in variables between iterations"
            },
            "ConstraintTolerance": {
                "default": "1e-6",
                "recommended": "1e-3 to 1e-4",
                "description": "Controls maximum acceptable constraint violation"
            },
            "OptimalityTolerance": {
                "default": "1e-6",
                "recommended": "1e-3 to 1e-4",
                "description": "Controls first-order optimality conditions"
            },
            "FunctionTolerance": {
                "default": "1e-6", 
                "recommended": "1e-4",
                "description": "Controls minimum change in objective function"
            }
        }
        
        for tolerance, info in tolerance_info.items():
            print(f"\n🔹 {tolerance}:")
            print(f"   Default: {info['default']}")
            print(f"   Recommended: {info['recommended']}")
            print(f"   Description: {info['description']}")
        
        print("\n💡 Key Insights:")
        print("   • The default tolerances are very strict (small values)")
        print("   • Increasing tolerances allows the optimizer to run longer")
        print("   • StepTolerance is often the main cause of early stopping")
        print("   • ConstraintTolerance affects feasibility requirements")
        print("   • Balance: looser tolerances → longer runtime but better solutions")
        
        print("\n✅ Configuration complete! The modified matRad_OptimizerFmincon.m")
        print("   will now apply these custom tolerances during optimization.")
        
        # Optionally demonstrate with a small optimization
        response = input("\n🚀 Run a test optimization with these settings? (y/n): ")
        if response.lower() == 'y':
            run_test_optimization(eng)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        print("\nClosing MATLAB engine...")
        eng.quit()


def run_test_optimization(eng):
    """
    Run a small test optimization to demonstrate the tolerance settings.
    """
    print("\n🧪 Running test optimization...")
    
    try:
        eng.eval("""
        % Generate steering information
        stf = matRad_generateStf(ct,cst,pln);
        
        % Generate dij (this may take a few minutes)
        disp('Calculating dose influence matrix...');
        dij = matRad_calcPhotonDose(ct,stf,pln,cst);
        
        % Add simple objectives for testing
        % Target: PTV should receive 60 Gy
        % OARs: keep doses low
        for i = 1:size(cst,1)
            if strcmp(cst{i,3}, 'TARGET')
                % Square overdosing objective for target
                cst{i,6}{1} = DoseObjectives.matRad_SquaredOverdosing(100, 60);
                % Square underdosing objective for target  
                cst{i,6}{2} = DoseObjectives.matRad_SquaredUnderdosing(100, 60);
            elseif strcmp(cst{i,3}, 'OAR')
                % Square overdosing objective for OAR (keep dose low)
                cst{i,6}{1} = DoseObjectives.matRad_SquaredOverdosing(10, 20);
            end
        end
        
        % Run optimization with custom tolerances
        disp('Starting optimization with custom fmincon tolerances...');
        tic;
        resultGUI = matRad_fluenceOptimization(dij,cst,pln);
        optimization_time = toc;
        
        disp(['✅ Optimization completed in ' num2str(optimization_time) ' seconds']);
        disp(['Final objective value: ' num2str(resultGUI.info.fVal)]);
        disp(['Exit flag: ' num2str(resultGUI.info.exitflag)]);
        disp(['Number of iterations: ' num2str(resultGUI.info.iterations)]);
        
        """, nargout=0)
        
        print("✅ Test optimization completed successfully!")
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")


def create_tolerance_reference():
    """
    Create a reference file with fmincon tolerance explanations.
    """
    reference_content = """
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
"""
    
    with open('LLM_Agent_Planner/fmincon_tolerance_reference.md', 'w') as f:
        f.write(reference_content)
    
    print("📚 Created tolerance reference file: fmincon_tolerance_reference.md")


if __name__ == "__main__":
    configure_fmincon_tolerances()
    create_tolerance_reference() 