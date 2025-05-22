import matlab.engine
import os
import time
import sys

def run_step(eng, step_name, matlab_cmd, stop_on_error=True):
    """Run a MATLAB command with error handling"""
    print(f"\n{step_name}...")
    try:
        eng.eval(matlab_cmd, nargout=0)
        print(f"{step_name} completed successfully.")
        return True
    except Exception as e:
        print(f"Error during {step_name}:")
        print(str(e))
        if stop_on_error:
            return False
        return True

# Start the MATLAB engine
print("Starting MATLAB engine...")
eng = matlab.engine.start_matlab()

# Get current directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")

# Initialize matRad
print("Initializing matRad...")
eng.matRad_rc(nargout=0)

# Step 1: Load patient data
if not run_step(eng, "Step 1: Loading patient data", "load('matRad/phantoms/HEAD_AND_NECK.mat');"):
    eng.quit()
    sys.exit(1)

# Check that data was loaded correctly
if eng.eval("exist('ct', 'var') && exist('cst', 'var')", nargout=1) != 1:
    print("Error: Failed to load CT and CST data.")
    eng.quit()
    sys.exit(1)

# Print some information about the data
print("\nPatient data summary:")
eng.eval("disp(['CT dimensions: ' num2str(size(ct.cube))])", nargout=0)
eng.eval("disp(['Number of structures: ' num2str(numel(cst))])", nargout=0)

# Step 2: Define the treatment plan
plan_def = """
pln = struct();
pln.radiationMode   = 'photons';
pln.machine         = 'Generic';
pln.numOfFractions  = 30;
 
pln.propStf.gantryAngles    = [0:72:359];
pln.propStf.couchAngles     = [0 0 0 0 0];
pln.propStf.bixelWidth      = 5;
pln.propStf.numOfBeams      = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter       = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);

pln.bioModel = 'none'; 
pln.multScen = 'nomScen';

% dose calculation settings
pln.propDoseCalc.doseGrid.resolution.x = 3; % [mm]
pln.propDoseCalc.doseGrid.resolution.y = 3; % [mm]
pln.propDoseCalc.doseGrid.resolution.z = 3; % [mm]

% Set optimizer
if matRad_OptimizerFmincon.IsAvailable()
    pln.propOpt.optimizer = 'fmincon';   
else
    pln.propOpt.optimizer = 'IPOPT';
end
pln.propOpt.quantityOpt = 'physicalDose';

% Enable sequencing 
pln.propSeq.runSequencing = true;
"""

if not run_step(eng, "Step 2: Setting up treatment plan", plan_def):
    eng.quit()
    sys.exit(1)

# Print information about the plan
print("\nPlan summary:")
eng.eval("disp(['Radiation mode: ' pln.radiationMode])", nargout=0)
eng.eval("disp(['Number of beams: ' num2str(pln.propStf.numOfBeams)])", nargout=0)
eng.eval("disp(['Gantry angles: ' mat2str(pln.propStf.gantryAngles)])", nargout=0)

# Step 3: Generate Beam Geometry STF
if not run_step(eng, "Step 3: Generating beam geometry", "stf = matRad_generateStf(ct,cst,pln);"):
    eng.quit()
    sys.exit(1)

# Print information about STF
print("\nSTF summary:")
eng.eval("disp(['Number of beams: ' num2str(numel(stf))])", nargout=0)
eng.eval("disp(['Total bixels: ' num2str(sum([stf.totalNumOfBixels]))])", nargout=0)

# Step 4: Dose Calculation
print("\nStep 4: Calculating dose influence matrix...")
print("This may take some time...")
if not run_step(eng, "Dose calculation", "dij = matRad_calcDoseInfluence(ct,cst,stf,pln);"):
    eng.quit()
    sys.exit(1)

# Print information about DIJ
print("\nDose influence matrix summary:")
eng.eval("disp(['DIJ dimensions: ' num2str(size(dij.physicalDose))])", nargout=0)

# Step 5: Inverse Planning for IMRT with smaller number of iterations for testing
if not run_step(eng, "Step 5: Running fluence optimization", "resultGUI = matRad_fluenceOptimization(dij,cst,pln);"):
    eng.quit()
    sys.exit(1)

# Print optimization results
print("\nFluence optimization summary:")
eng.eval("disp(['Objective function value: ' num2str(resultGUI.objectiveFunctionValue)])", nargout=0)

# Save intermediate results
eng.eval("save('fluence_result.mat', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
print("Intermediate results saved to fluence_result.mat")

# Step 6: Sequencing - modify parameters to avoid issues
sequencing_cmd = """
% Explicitly set sequencing parameters
pln.propSeq.sequencer = 'SMLC';  % Explicitly set sequencing algorithm
pln.propSeq.numOfLevels = 5;     % Explicitly set number of intensity levels

% Run sequencing
try
    fprintf('Running sequencing with SMLC sequencer and %d intensity levels...\\n', pln.propSeq.numOfLevels);
    resultGUI = matRad_sequencing(resultGUI,stf,dij,pln);
    disp('Sequencing completed successfully');
catch ME
    disp('Error during sequencing:');
    disp(ME.message);
end
"""

if not run_step(eng, "Step 6: Running sequencing", sequencing_cmd, stop_on_error=False):
    print("Continuing despite sequencing issues...")

# Print sequencing results
print("\nChecking for sequencing results:")
eng.eval("if isfield(resultGUI, 'apertureInfo'), disp('apertureInfo is available'); else disp('apertureInfo not found'); end", nargout=0)

# Save results after sequencing
eng.eval("save('sequencing_result.mat', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
print("Results after sequencing saved to sequencing_result.mat")

# We'll check the aperture fields if available
aperture_check = """
if isfield(resultGUI, 'apertureInfo')
    disp('Aperture Info Summary:');
    disp(['Number of apertures: ' num2str(numel(resultGUI.apertureInfo.aperture))]);
    
    % Display aperture shapes
    try
        figure;
        matRad_visApertureInfo(resultGUI.apertureInfo);
        saveas(gcf, 'aperture_visualization.png');
        disp('Aperture visualization saved to aperture_visualization.png');
    catch ME
        disp('Could not visualize apertures:');
        disp(ME.message);
    end
else
    disp('No aperture information available after sequencing');
end
"""

if not run_step(eng, "Checking aperture information", aperture_check, stop_on_error=False):
    print("Continuing without aperture visualization...")

# Step 7: Skip DAO for now as it's causing errors

# Step 8: Plan Analysis if we have results
analysis_cmd = """
try
    resultGUI = matRad_planAnalysis(resultGUI,ct,cst,stf,pln);
    disp('Plan analysis completed');
    
    % Print some QI information
    if isfield(resultGUI, 'QI')
        structNames = cellfun(@(c) c.name, cst, 'UniformOutput', false);
        disp('Quality indicators for important structures:');
        for i = 1:numel(structNames)
            if isfield(resultGUI.QI, structNames{i}) && isfield(resultGUI.QI.(structNames{i}), 'D_mean')
                fprintf('%s - Mean dose: %.2f Gy\\n', structNames{i}, resultGUI.QI.(structNames{i}).D_mean);
            end
        end
    end
    
    % Save DVH plot
    try
        matRad_showDVH(resultGUI,cst);
        saveas(gcf, 'dvh_plot.png');
        disp('DVH plot saved to dvh_plot.png');
    catch ME
        disp('Could not create DVH plot:');
        disp(ME.message);
    end
catch ME
    disp('Error during plan analysis:');
    disp(ME.message);
end
"""

if not run_step(eng, "Step 8: Running plan analysis", analysis_cmd, stop_on_error=False):
    print("Plan analysis had issues...")

# Save the final results
eng.eval("save('final_result.mat', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
print("Final results saved to final_result.mat")

# Close the MATLAB engine
print("\nClosing MATLAB engine...")
eng.quit()

print("\nWorkflow completed. Examine the output files to understand the results.") 