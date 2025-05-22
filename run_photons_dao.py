import matlab.engine
import os
import time

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
print("\nStep 1: Loading patient data (HEAD_AND_NECK.mat)...")
eng.load('matRad/phantoms/HEAD_AND_NECK.mat', nargout=0)
print("Data loaded successfully.")

# Step 2: Define the treatment plan
print("\nStep 2: Setting up the treatment plan...")
eng.eval("""
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

% Enable sequencing and direct aperture optimization (DAO)
pln.propSeq.runSequencing = true;
pln.propOpt.runDAO        = true;
""", nargout=0)
print("Treatment plan defined.")

# Step 3: Generate Beam Geometry STF
print("\nStep 3: Generating beam geometry (stf)...")
eng.eval("stf = matRad_generateStf(ct,cst,pln);", nargout=0)
print("Beam geometry generated.")

# Step 4: Dose Calculation
print("\nStep 4: Calculating dose influence matrix...")
print("This may take some time...")
eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
print("Dose influence matrix calculated.")

# Step 5: Inverse Planning for IMRT
print("\nStep 5: Running fluence optimization...")
eng.eval("resultGUI = matRad_fluenceOptimization(dij,cst,pln);", nargout=0)
print("Fluence optimization completed.")

# Step 6: Sequencing
print("\nStep 6: Running sequencing...")
eng.eval("resultGUI = matRad_sequencing(resultGUI,stf,dij,pln);", nargout=0)
print("Sequencing completed.")

# Step 7: Direct Aperture Optimization (DAO)
print("\nStep 7: Running direct aperture optimization (DAO)...")
eng.eval("resultGUI = matRad_directApertureOptimization(dij,cst,resultGUI.apertureInfo,resultGUI,pln);", nargout=0)
print("DAO completed.")

# Step 8: Plan Analysis
print("\nStep 8: Running plan analysis...")
eng.eval("resultGUI = matRad_planAnalysis(resultGUI,ct,cst,stf,pln);", nargout=0)
print("Plan analysis completed.")

# Save the result
print("\nSaving results...")
eng.eval("save('dao_result.mat', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
print("Results saved to dao_result.mat")

# Display structure information
print("\nShowing structure information from CST:")
eng.eval("fprintf('Number of structures: %d\\n', numel(cst));", nargout=0)
eng.eval("""
for i = 1:numel(cst)
    if ~isempty(cst{i}) && isfield(cst{i}, 'name')
        fprintf('Structure %d: %s\\n', i, cst{i}.name);
    end
end
""", nargout=0)

# Close the MATLAB engine
print("\nClosing MATLAB engine...")
eng.quit()

print("\nWorkflow completed successfully.") 