import matlab.engine
import os
import time

# Start the MATLAB engine
print("Starting MATLAB engine...")
eng = matlab.engine.start_matlab()

# Initialize matRad
print("Initializing matRad...")
eng.matRad_rc(nargout=0)

# Load the HEAD_AND_NECK.mat file
print("Loading HEAD_AND_NECK.mat...")
eng.load('matRad/phantoms/HEAD_AND_NECK.mat', nargout=0)

# Display dataset overview
print("\nHEAD_AND_NECK Dataset Overview:")
eng.eval("disp(['CT dimensions: ' num2str(size(ct.cube))])", nargout=0)
eng.eval("disp(['Number of structures: ' num2str(numel(cst))])", nargout=0)

# Setup treatment plan with controlled fmincon optimizer
print("\nSetting up treatment plan with fmincon optimizer parameters...")
eng.eval("""
% Create the treatment plan
pln = struct();
pln.radiationMode   = 'photons';
pln.machine         = 'Generic';
pln.numOfFractions  = 30;
 
% Setup beam geometry
pln.propStf.gantryAngles    = [0:72:359];  % 5 beams at 72 degree intervals
pln.propStf.couchAngles     = [0 0 0 0 0]; % All beams with couch at 0 degrees
pln.propStf.bixelWidth      = 5;           % 5mm bixel width
pln.propStf.numOfBeams      = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter       = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);

% Biological model and optimization settings
pln.bioModel = 'none';      % No biological model for photons
pln.multScen = 'nomScen';   % Nominal scenario
pln.propOpt.quantityOpt = 'physicalDose';  % Optimize physical dose

% Dose calculation settings
pln.propDoseCalc.doseGrid.resolution.x = 3; % [mm]
pln.propDoseCalc.doseGrid.resolution.y = 3; % [mm]
pln.propDoseCalc.doseGrid.resolution.z = 3; % [mm]

% Setup fmincon optimizer with specific parameters
if matRad_OptimizerFmincon.IsAvailable()
    pln.propOpt.optimizer = 'fmincon';
    
    % Configure fmincon to limit iterations and control convergence
    pln.propOpt.fmincon.MaxIterations = 30;       % Limit to 30 iterations
    pln.propOpt.fmincon.MaxFunctionEvaluations = 60;  % Limit function evaluations
    pln.propOpt.fmincon.OptimalityTolerance = 1e-3;   % Optimality tolerance
    pln.propOpt.fmincon.StepTolerance = 1e-3;         % Step tolerance
    pln.propOpt.fmincon.Display = 'iter';             % Show iteration details
    
    disp('Using fmincon optimizer with custom parameters:');
    disp(pln.propOpt.fmincon);
else
    pln.propOpt.optimizer = 'IPOPT';
    disp('fmincon not available, using IPOPT optimizer');
end

% Use no sequencing for pure IMRT
pln.propSeq.runSequencing = false;
pln.propOpt.runDAO = false;

% Display plan setup
disp('Treatment plan configuration:');
disp(['Radiation mode: ' pln.radiationMode]);
disp(['Number of beams: ' num2str(pln.propStf.numOfBeams)]);
disp(['Beam angles: ' mat2str(pln.propStf.gantryAngles)]);
""", nargout=0)

# Generate the beam geometry (stf)
print("\nGenerating beam geometry...")
eng.eval("stf = matRad_generateStf(ct,cst,pln);", nargout=0)

# Display beam information
print("\nBeam geometry summary:")
eng.eval("""
disp(['Number of beams: ' num2str(numel(stf))]);
totalBixels = sum([stf.totalNumOfBixels]);
disp(['Total bixels: ' num2str(totalBixels)]);

% Display individual beam details
disp('Individual beam information:');
for i = 1:numel(stf)
    fprintf('Beam %d: Gantry angle = %d°, Couch angle = %d°, Bixels = %d\\n', ...
            i, stf(i).gantryAngle, stf(i).couchAngle, stf(i).totalNumOfBixels);
end
""", nargout=0)

# Calculate dose influence matrix
print("\nCalculating dose influence matrix...")
print("This may take some time...")
start_time = time.time()
eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
calc_time = time.time() - start_time
print(f"Dose influence matrix calculation completed in {calc_time:.2f} seconds.")

# Display dose influence matrix information
print("\nDose influence matrix overview:")
eng.eval("""
disp(['DIJ dimensions: ' num2str(size(dij.physicalDose))]);
disp(['Number of voxels: ' num2str(numel(dij.doseGrid.x) * numel(dij.doseGrid.y) * numel(dij.doseGrid.z))]);
disp(['Number of bixels/spots: ' num2str(size(dij.physicalDose,2))]);
""", nargout=0)

# Run fluence optimization with the configured parameters
print("\nRunning fluence optimization with limited iterations...")
start_time = time.time()
eng.eval("resultGUI = matRad_fluenceOptimization(dij,cst,pln);", nargout=0)
opt_time = time.time() - start_time
print(f"Optimization completed in {opt_time:.2f} seconds.")

# Display optimization results
print("\nOptimization results:")
eng.eval("""
disp(['Final objective function value: ' num2str(resultGUI.objectiveFunctionValue)]);

% Display dose statistics for important structures
disp('Dose statistics for structures:');
fprintf('%-20s %-15s %-15s %-15s\\n', 'Structure', 'Min Dose (Gy)', 'Mean Dose (Gy)', 'Max Dose (Gy)');
fprintf('%-20s %-15s %-15s %-15s\\n', '--------------------', '---------------', '---------------', '---------------');

for i = 1:size(cst,1)
    if ~isempty(cst{i,2})
        name = cst{i,2};
        type = cst{i,3};
        
        % Get structure voxels
        structVoxels = [];
        if ~isempty(cst{i,4})
            structVoxels = cst{i,4}{1};
        end
        
        if ~isempty(structVoxels)
            % Get dose values for structure
            doseVals = resultGUI.physicalDose(structVoxels);
            minDose = min(doseVals);
            meanDose = mean(doseVals);
            maxDose = max(doseVals);
            
            % Print stats
            fprintf('%-20s %-15.2f %-15.2f %-15.2f\\n', name, minDose, meanDose, maxDose);
        end
    end
end
""", nargout=0)

# Save the results
print("\nSaving results...")
eng.eval("save('imrt_result.mat', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
print("Results saved to imrt_result.mat")

# Close the MATLAB engine
print("\nClosing MATLAB engine...")
eng.quit()

print("\nIMRT optimization workflow completed.") 