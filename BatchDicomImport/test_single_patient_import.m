function test_single_patient_import(patient_id)
% TEST_SINGLE_PATIENT_IMPORT Test DICOM import for a single HNC patient
%
% This script tests the DICOM import functionality on a single patient
% before running the full batch processing script.
%
% Usage:
%   test_single_patient_import('HNC_015')  % Test specific patient
%   test_single_patient_import()           % Test first available patient
%
% This is useful for:
% - Verifying the setup works correctly
% - Testing on a small scale before batch processing
% - Debugging import issues
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Initialize
clc;
fprintf('=================================================================\n');
fprintf('            matRad Single Patient DICOM Import Test             \n');
fprintf('=================================================================\n\n');

% Check if matRad is properly initialized
try
    matRad_cfg = MatRad_Config.instance();
    fprintf('✓ matRad configuration loaded successfully\n');
catch ME
    error('matRad not properly initialized. Please ensure matRad is in the MATLAB path and properly configured.\nError: %s', ME.message);
end

% Disable GUI elements for testing
matRad_cfg.disableGUI = true;

%% Configuration
% Set the base path to HNC data directory
hnc_base_path = '/Users/ahmadneishabouri/Work/Data/manifest-1714488710321/HNC-IMRT-70-33';

% Verify base path exists
if ~exist(hnc_base_path, 'dir')
    error('HNC data directory not found: %s', hnc_base_path);
end

fprintf('✓ HNC data directory found: %s\n', hnc_base_path);

%% Select patient
if nargin < 1 || isempty(patient_id)
    % Find first available patient
    patient_dirs = dir(fullfile(hnc_base_path, 'HNC_*'));
    patient_dirs = patient_dirs([patient_dirs.isdir]);
    
    if isempty(patient_dirs)
        error('No patient directories found matching pattern HNC_*');
    end
    
    patient_id = patient_dirs(1).name;
    fprintf('✓ No patient specified, using first available: %s\n', patient_id);
else
    fprintf('✓ Testing patient: %s\n', patient_id);
end

patient_path = fullfile(hnc_base_path, patient_id);

if ~exist(patient_path, 'dir')
    error('Patient directory not found: %s', patient_path);
end

%% Start test
fprintf('\n--- Starting DICOM Import Test ---\n');
start_time = tic;

try
    %% Verify directory structure
    fprintf('\n1. Verifying directory structure...\n');
    
    ct_dir = fullfile(patient_path, 'CT');
    struct_dir = fullfile(patient_path, 'RTSTRUCT');
    dose_dir = fullfile(patient_path, 'RTDOSE');
    
    if ~exist(ct_dir, 'dir')
        error('CT directory not found: %s', ct_dir);
    end
    if ~exist(struct_dir, 'dir')
        error('RTSTRUCT directory not found: %s', struct_dir);
    end
    if ~exist(dose_dir, 'dir')
        error('RTDOSE directory not found: %s', dose_dir);
    end
    
    fprintf('  ✓ All required directories found\n');
    
    %% Count and verify DICOM files
    fprintf('\n2. Analyzing DICOM files...\n');
    
    ct_files = dir(fullfile(ct_dir, '*.dcm'));
    struct_files = dir(fullfile(struct_dir, '*.dcm'));
    dose_files = dir(fullfile(dose_dir, '*.dcm'));
    
    fprintf('  CT files: %d\n', length(ct_files));
    fprintf('  RTSTRUCT files: %d\n', length(struct_files));
    fprintf('  RTDOSE files: %d\n', length(dose_files));
    
    if length(ct_files) == 0
        error('No CT DICOM files found');
    end
    if length(struct_files) == 0
        error('No RTSTRUCT DICOM files found');
    end
    if length(dose_files) == 0
        warning('No RTDOSE DICOM files found - continuing without dose data');
    end
    
    %% Test DICOM file validity
    fprintf('\n3. Testing DICOM file validity...\n');
    
    % Test first CT file
    try
        ct_info = dicominfo(fullfile(ct_dir, ct_files(1).name));
        fprintf('  ✓ CT files are valid DICOM (Modality: %s)\n', ct_info.Modality);
    catch ME
        error('CT DICOM files are invalid: %s', ME.message);
    end
    
    % Test RTSTRUCT file
    try
        struct_info = dicominfo(fullfile(struct_dir, struct_files(1).name));
        fprintf('  ✓ RTSTRUCT files are valid DICOM (Modality: %s)\n', struct_info.Modality);
    catch ME
        error('RTSTRUCT DICOM files are invalid: %s', ME.message);
    end
    
    % Test RTDOSE file if available
    if length(dose_files) > 0
        try
            dose_info = dicominfo(fullfile(dose_dir, dose_files(1).name));
            fprintf('  ✓ RTDOSE files are valid DICOM (Modality: %s)\n', dose_info.Modality);
        catch ME
            warning('MATLAB:DICOMError', 'RTDOSE DICOM files may be invalid: %s', ME.message);
        end
    end
    
    %% Create and test matRad importer
    fprintf('\n4. Creating matRad DICOM importer...\n');
    
    dicom_importer = matRad_DicomImporter(patient_path);
    
    % Set import options
    dicom_importer.dicomMetaBool = true;
    dicom_importer.visBool = false;
    
    fprintf('  ✓ DICOM importer created successfully\n');
    fprintf('  Files detected by importer:\n');
    fprintf('    CT: %d files\n', size(dicom_importer.importFiles.ct, 1));
    fprintf('    RTSTRUCT: %d files\n', size(dicom_importer.importFiles.rtss, 1));
    fprintf('    RTDOSE: %d files\n', size(dicom_importer.importFiles.rtdose, 1));
    
    %% Perform DICOM import
    fprintf('\n5. Importing DICOM data...\n');
    
    import_start = tic;
    dicom_importer.matRad_importDicom();
    import_time = toc(import_start);
    
    fprintf('  ✓ DICOM import completed in %.1f seconds\n', import_time);
    
    %% Analyze imported data
    fprintf('\n6. Analyzing imported data...\n');
    
    ct_data = dicom_importer.ct;
    cst_data = dicom_importer.cst;
    resultGUI_data = dicom_importer.resultGUI;
    pln_data = dicom_importer.pln;
    stf_data = dicom_importer.stf;
    
    % CT Analysis
    if ~isempty(ct_data)
        ct_size = size(ct_data.cube{1});
        fprintf('  CT Data:\n');
        fprintf('    Dimensions: %dx%dx%d\n', ct_size(1), ct_size(2), ct_size(3));
        fprintf('    Resolution: %.2f x %.2f x %.2f mm\n', ...
                ct_data.resolution.x, ct_data.resolution.y, ct_data.resolution.z);
        fprintf('    Data type: %s\n', class(ct_data.cube{1}));
        fprintf('    Value range: [%.1f, %.1f]\n', min(ct_data.cube{1}(:)), max(ct_data.cube{1}(:)));
    else
        error('CT data import failed');
    end
    
    % CST Analysis
    if ~isempty(cst_data)
        num_structures = size(cst_data, 1);
        fprintf('  Structure Data:\n');
        fprintf('    Number of structures: %d\n', num_structures);
        fprintf('    Structure names:\n');
        for i = 1:min(num_structures, 10) % Show first 10 structures
            fprintf('      %d: %s\n', i, cst_data{i, 2});
        end
        if num_structures > 10
            fprintf('      ... and %d more\n', num_structures - 10);
        end
    else
        warning('CST data is empty');
    end
    
    % Result/Dose Analysis
    if ~isempty(resultGUI_data)
        fprintf('  Dose Data:\n');
        dose_fields = fieldnames(resultGUI_data);
        fprintf('    Available dose fields: %s\n', strjoin(dose_fields, ', '));
        for i = 1:length(dose_fields)
            field = dose_fields{i};
            if isnumeric(resultGUI_data.(field)) && numel(resultGUI_data.(field)) > 1
                dose_size = size(resultGUI_data.(field));
                fprintf('    %s: %s\n', field, mat2str(dose_size));
            end
        end
    else
        fprintf('  Dose Data: Not available\n');
    end
    
    % Plan Analysis
    if ~isempty(pln_data)
        fprintf('  Plan Data: Available\n');
        if isfield(pln_data, 'radiationMode')
            fprintf('    Radiation mode: %s\n', pln_data.radiationMode);
        end
    else
        fprintf('  Plan Data: Not available\n');
    end
    
    %% Test data export
    fprintf('\n7. Testing data export...\n');
    
    % Create temporary directory for test export
    test_dir = fullfile(tempdir, ['matRad_test_' patient_id '_' datestr(now, 'HHMMSS')]);
    if ~exist(test_dir, 'dir')
        mkdir(test_dir);
    end
    
    try
        % Save CT data
        ct_file = fullfile(test_dir, 'ct.mat');
        ct = ct_data;
        save(ct_file, 'ct', '-v7.3');
        ct_size_mb = get_file_size(ct_file) / 1e6;
        
        % Save CST data
        cst_file = fullfile(test_dir, 'cst.mat');
        cst = cst_data;
        save(cst_file, 'cst', '-v7.3');
        cst_size_mb = get_file_size(cst_file) / 1e6;
        
        % Save result data if available
        result_size_mb = 0;
        if ~isempty(resultGUI_data)
            result_file = fullfile(test_dir, 'resultGUI.mat');
            resultGUI = resultGUI_data;
            save(result_file, 'resultGUI', '-v7.3');
            result_size_mb = get_file_size(result_file) / 1e6;
        end
        
        fprintf('  ✓ Data export successful\n');
        fprintf('    CT file: %.1f MB\n', ct_size_mb);
        fprintf('    CST file: %.1f MB\n', cst_size_mb);
        if result_size_mb > 0
            fprintf('    Result file: %.1f MB\n', result_size_mb);
        end
        fprintf('    Total size: %.1f MB\n', ct_size_mb + cst_size_mb + result_size_mb);
        
        % Test data loading
        fprintf('\n8. Testing data loading...\n');
        clear ct cst resultGUI;
        
        load(ct_file);
        load(cst_file);
        if exist(result_file, 'file')
            load(result_file);
        end
        
        fprintf('  ✓ Data loading successful\n');
        fprintf('    CT loaded: %dx%dx%d\n', size(ct.cube{1}));
        fprintf('    CST loaded: %d structures\n', size(cst, 1));
        
    catch ME
        error('Data export/import test failed: %s', ME.message);
    finally
        % Clean up test directory
        if exist(test_dir, 'dir')
            rmdir(test_dir, 's');
        end
    end
    
    %% Summary
    total_time = toc(start_time);
    
    fprintf('\n=================================================================\n');
    fprintf('                           TEST RESULTS                          \n');
    fprintf('=================================================================\n');
    fprintf('Patient: %s\n', patient_id);
    fprintf('Status: ✓ SUCCESS\n');
    fprintf('Total time: %.1f seconds\n', total_time);
    fprintf('Import time: %.1f seconds\n', import_time);
    fprintf('\nData Summary:\n');
    fprintf('  CT: %dx%dx%d (%.1f MB)\n', ct_size(1), ct_size(2), ct_size(3), ct_size_mb);
    fprintf('  Structures: %d (%.1f MB)\n', size(cst_data, 1), cst_size_mb);
    if result_size_mb > 0
        fprintf('  Dose: Available (%.1f MB)\n', result_size_mb);
    else
        fprintf('  Dose: Not available\n');
    end
    fprintf('\n✓ Test completed successfully!\n');
    fprintf('✓ You can now run the full batch processing with confidence.\n');
    
catch ME
    total_time = toc(start_time);
    
    fprintf('\n=================================================================\n');
    fprintf('                           TEST RESULTS                          \n');
    fprintf('=================================================================\n');
    fprintf('Patient: %s\n', patient_id);
    fprintf('Status: ✗ FAILED\n');
    fprintf('Error: %s\n', ME.message);
    fprintf('Time until failure: %.1f seconds\n', total_time);
    fprintf('\n✗ Test failed. Please resolve the issues before running batch processing.\n');
    
    % Print stack trace for debugging
    fprintf('\nStack trace:\n');
    for i = 1:length(ME.stack)
        fprintf('  %s (line %d)\n', ME.stack(i).name, ME.stack(i).line);
    end
    
    rethrow(ME);
end

end

%% Helper function
function size_bytes = get_file_size(filename)
    % Get file size in bytes
    try
        file_info = dir(filename);
        if ~isempty(file_info)
            size_bytes = file_info.bytes;
        else
            size_bytes = 0;
        end
    catch
        size_bytes = 0;
    end
end 