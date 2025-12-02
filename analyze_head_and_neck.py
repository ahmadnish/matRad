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
eng.load('~/matRad/matRad/phantoms/HIT_HandN_PAT0.mat', nargout=0)

# Display basic information about the dataset
print("\n=== HEAD_AND_NECK Dataset Overview ===")
eng.eval("disp(['CT cube dimensions: ' num2str(size(ct.cube))])", nargout=0)
eng.eval("disp(['CT resolution (mm): [' num2str(ct.resolution.x) ', ' num2str(ct.resolution.y) ', ' num2str(ct.resolution.z) ']'])", nargout=0)
eng.eval("disp(['Number of structures in CST: ' num2str(numel(cst))])", nargout=0)

# Examine the CST structure in detail
print("\n=== CST Structure Analysis ===")
eng.eval("""
fprintf('CST dimensions: %s\\n', mat2str(size(cst)));

% Extract all structure names
structNames = {};
structTypes = {};
for i = 1:size(cst,1)
    if ~isempty(cst{i,2})
        structNames{end+1} = cst{i,2};
        structTypes{end+1} = cst{i,3};
    end
end

% Display structure information
fprintf('\\nStructure Information:\\n');
fprintf('%-20s %-10s %-15s %-15s\\n', 'Name', 'Type', 'Priority', 'Voxel Count');
fprintf('%-20s %-10s %-15s %-15s\\n', '--------------------', '----------', '---------------', '---------------');

for i = 1:size(cst,1)
    if ~isempty(cst{i,2})
        name = cst{i,2};
        type = cst{i,3};
        
        % Handle tissue parameters
        if ~isempty(cst{i,5}) && isfield(cst{i,5}, 'Priority')
            priority = num2str(cst{i,5}.Priority);
        else
            priority = 'N/A';
        end
        
        % Count voxels
        if ~isempty(cst{i,4})
            voxelCount = num2str(numel(cst{i,4}{1}));
        else
            voxelCount = '0';
        end
        
        % Print row
        fprintf('%-20s %-10s %-15s %-15s\\n', name, type, priority, voxelCount);
    end
end

% Find and display target structures
fprintf('\\nTarget Structures:\\n');
targetIdx = find(strcmp(structTypes, 'TARGET'));
for i = 1:numel(targetIdx)
    fprintf('%d. %s\\n', i, structNames{targetIdx(i)});
end

% Find and display OAR structures
fprintf('\\nOrgans at Risk (OARs):\\n');
oarIdx = find(strcmp(structTypes, 'OAR'));
for i = 1:numel(oarIdx)
    fprintf('%d. %s\\n', i, structNames{oarIdx(i)});
end

% Display examples of dose objectives
fprintf('\\nExamples of Dose Objectives:\\n');
for i = 1:size(cst,1)
    if ~isempty(cst{i,2}) && ~isempty(cst{i,6})
        fprintf('Structure: %s (%s)\\n', cst{i,2}, cst{i,3});
        for j = 1:numel(cst{i,6})
            if isstruct(cst{i,6}{j})
                if isfield(cst{i,6}{j}, 'className')
                    % New objective format (v2.10.0+)
                    className = cst{i,6}{j}.className;
                    fprintf('  Objective %d: %s\\n', j, className);
                    
                    % Display parameters
                    if isfield(cst{i,6}{j}, 'parameters')
                        fprintf('    Parameters: ');
                        disp(cst{i,6}{j}.parameters);
                    end
                    
                    % Display penalty
                    if isfield(cst{i,6}{j}, 'penalty')
                        fprintf('    Penalty: %f\\n', cst{i,6}{j}.penalty);
                    end
                else
                    % Old objective format
                    fprintf('  Objective %d: Using old format\\n', j);
                    disp(cst{i,6}{j});
                end
            elseif isobject(cst{i,6}{j})
                % Object-based objective
                fprintf('  Objective %d: Object of class %s\\n', j, class(cst{i,6}{j}));
            end
        end
        fprintf('\\n');
    end
end
""", nargout=0)

# Now let's look at how to configure fmincon optimizer parameters
print("\n=== Configuring fmincon Optimizer Parameters ===")
eng.eval("""
disp('Available fmincon options:');

% Create an example of plan with specific fmincon options
examplePln = struct();
examplePln.radiationMode = 'photons';
examplePln.propOpt.optimizer = 'fmincon';

% Configure specific parameters to stop optimization early
examplePln.propOpt.fmincon.MaxIterations = 50;       % Maximum number of iterations
examplePln.propOpt.fmincon.MaxFunctionEvaluations = 100;  % Maximum number of function evaluations
examplePln.propOpt.fmincon.OptimalityTolerance = 1e-3;    % Optimality tolerance
examplePln.propOpt.fmincon.StepTolerance = 1e-3;          % Step tolerance
examplePln.propOpt.fmincon.Display = 'iter';              % Display optimization progress

disp('Example of fmincon parameters configured to stop optimization early:');
disp(examplePln.propOpt.fmincon);

disp(['For more information about fmincon options, see:', ...
      ' https://www.mathworks.com/help/optim/ug/fmincon.html#input_argument_options']);
""", nargout=0)

# Close the MATLAB engine
print("\nClosing MATLAB engine...")
eng.quit()

print("\nAnalysis completed.") 