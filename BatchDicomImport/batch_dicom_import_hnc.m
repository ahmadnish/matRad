function batch_dicom_import_hnc()
% BATCH_DICOM_IMPORT_HNC Batch import DICOM files for Head & Neck Cancer patients
%
% This script automatically loads DICOM files (CT, RTSTRUCT, RTDOSE) for all 
% HNC patients using matRad's DICOM import functionality.
% 
% Usage:
%   batch_dicom_import_hnc()
%
% Input:
%   The script expects the HNC-IMRT-70-33 folder structure with:
%   - Patient folders named HNC_XXX
%   - Each patient folder containing CT/, RTSTRUCT/, RTDOSE/ subdirectories
%
% Output:
%   - Saves ct.mat, cst.mat, and resultGUI.mat in each patient folder
%   - Creates processing logs and summary reports
%
% Created for matRad DICOM batch processing
% 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Initialize matRad environment
clc;
fprintf('=================================================================\n');
fprintf('           matRad Batch DICOM Import for HNC Patients           \n');
fprintf('=================================================================\n\n');

% Check if matRad is properly initialized
try
    matRad_cfg = MatRad_Config.instance();
    fprintf('✓ matRad configuration loaded successfully\n');
catch ME
    error('matRad not properly initialized. Please ensure matRad is in the MATLAB path and properly configured.\nError: %s', ME.message);
end

% Disable GUI elements for batch processing
matRad_cfg.disableGUI = true;

%% Configuration
% Set the base path to HNC data directory
hnc_base_path = '/Users/ahmadneishabouri/Work/Data/manifest-1714488710321/HNC-IMRT-70-33';

% Verify base path exists
if ~exist(hnc_base_path, 'dir')
    error('HNC data directory not found: %s', hnc_base_path);
end

fprintf('✓ HNC data directory found: %s\n', hnc_base_path);

%% Find all patient directories
patient_dirs = dir(fullfile(hnc_base_path, 'HNC_*'));
patient_dirs = patient_dirs([patient_dirs.isdir]); % Keep only directories

if isempty(patient_dirs)
    error('No patient directories found matching pattern HNC_*');
end

num_patients = length(patient_dirs);
fprintf('✓ Found %d patient directories\n\n', num_patients);

%% Initialize logging
log_file = fullfile(hnc_base_path, sprintf('batch_import_log_%s.txt', datestr(now, 'yyyymmdd_HHMMSS')));
log_fid = fopen(log_file, 'w');
if log_fid == -1
    warning('Could not create log file. Continuing without file logging.');
    log_fid = [];
end

% Write log header
if ~isempty(log_fid)
    fprintf(log_fid, 'matRad Batch DICOM Import Log\n');
    fprintf(log_fid, 'Started: %s\n', datestr(now));
    fprintf(log_fid, 'Base Path: %s\n', hnc_base_path);
    fprintf(log_fid, 'Number of Patients: %d\n\n', num_patients);
end

%% Initialize progress tracking
success_count = 0;
failed_patients = {};
processing_times = [];
summary_data = cell(num_patients, 8); % Patient, CT_slices, Structures, Has_Dose, Success, Time, Error, MatFile_Size

%% Process each patient
for i = 1:num_patients
    patient_id = patient_dirs(i).name;
    patient_path = fullfile(hnc_base_path, patient_id);
    
    fprintf('Processing Patient %d/%d: %s\n', i, num_patients, patient_id);
    log_msg(log_fid, sprintf('=== Processing Patient %d/%d: %s ===', i, num_patients, patient_id));
    
    % Start timing
    tic;
    
    try
        %% Verify required subdirectories exist
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
        
        log_msg(log_fid, sprintf('  ✓ Required directories found'));
        
        %% Count files for verification
        ct_files = dir(fullfile(ct_dir, '*.dcm'));
        struct_files = dir(fullfile(struct_dir, '*.dcm'));
        dose_files = dir(fullfile(dose_dir, '*.dcm'));
        
        log_msg(log_fid, sprintf('  Files found - CT: %d, RTSTRUCT: %d, RTDOSE: %d', ...
                                length(ct_files), length(struct_files), length(dose_files)));
        
        if length(ct_files) == 0
            error('No CT DICOM files found');
        end
        if length(struct_files) == 0
            error('No RTSTRUCT DICOM files found');
        end
        if length(dose_files) == 0
            warning('No RTDOSE DICOM files found - continuing without dose data');
        end
        
        %% Create matRad DICOM Importer
        fprintf('  Creating DICOM importer...\n');
        log_msg(log_fid, '  Creating matRad DICOM importer');
        
        dicom_importer = matRad_DicomImporter(patient_path);
        
        % Set import options
        dicom_importer.dicomMetaBool = true; % Include DICOM metadata
        dicom_importer.visBool = false; % Disable visualization for batch processing
        
        %% Import DICOM data
        fprintf('  Importing DICOM data...\n');
        log_msg(log_fid, '  Starting DICOM import');
        
        % Import all available data (CT, RTSTRUCT, RTDOSE if present)
        dicom_importer.matRad_importDicom();
        
        log_msg(log_fid, '  ✓ DICOM import completed');
        
        %% Extract imported data
        ct_data = dicom_importer.ct;
        cst_data = dicom_importer.cst;
        resultGUI_data = dicom_importer.resultGUI;
        pln_data = dicom_importer.pln;
        stf_data = dicom_importer.stf;
        
        %% Validate imported data
        if isempty(ct_data)
            error('CT data import failed - no data available');
        end
        if isempty(cst_data)
            warning('CST data is empty - structures may not have been imported properly');
        end
        
        % Count structures
        num_structures = 0;
        if ~isempty(cst_data)
            num_structures = size(cst_data, 1);
        end
        
        fprintf('  ✓ Data imported - CT: %dx%dx%d, Structures: %d\n', ...
                size(ct_data.cubeHU{1}, 1), size(ct_data.cubeHU{1}, 2), size(ct_data.cubeHU{1}, 3), num_structures);
        
        log_msg(log_fid, sprintf('  ✓ Data validated - CT dimensions: %dx%dx%d, Structures: %d', ...
                                size(ct_data.cubeHU{1}, 1), size(ct_data.cubeHU{1}, 2), size(ct_data.cubeHU{1}, 3), num_structures));
        
        %% Save data as .mat files
        fprintf('  Saving .mat files...\n');
        log_msg(log_fid, '  Saving data as .mat files');
        
        % Save CT data
        ct_file = fullfile(patient_path, 'ct.mat');
        ct = ct_data; % Use standard matRad variable name
        save(ct_file, 'ct', '-v7.3');
        ct_size = get_file_size(ct_file);
        
        % Save CST data
        cst_file = fullfile(patient_path, 'cst.mat');
        cst = cst_data; % Use standard matRad variable name
        save(cst_file, 'cst', '-v7.3');
        cst_size = get_file_size(cst_file);
        
        % Save result data if available
        result_size = 0;
        if ~isempty(resultGUI_data)
            result_file = fullfile(patient_path, 'resultGUI.mat');
            resultGUI = resultGUI_data; % Use standard matRad variable name
            save(result_file, 'resultGUI', '-v7.3');
            result_size = get_file_size(result_file);
        end
        
        % Save plan data if available
        if ~isempty(pln_data)
            pln_file = fullfile(patient_path, 'pln.mat');
            pln = pln_data; % Use standard matRad variable name
            save(pln_file, 'pln', '-v7.3');
        end
        
        % Save stf data if available
        if ~isempty(stf_data)
            stf_file = fullfile(patient_path, 'stf.mat');
            stf = stf_data; % Use standard matRad variable name
            save(stf_file, 'stf', '-v7.3');
        end
        
        total_size = ct_size + cst_size + result_size;
        
        fprintf('  ✓ Files saved - CT: %.1fMB, CST: %.1fMB', ct_size/1e6, cst_size/1e6);
        if result_size > 0
            fprintf(', Result: %.1fMB', result_size/1e6);
        end
        fprintf('\n');
        
        log_msg(log_fid, sprintf('  ✓ Files saved - Total size: %.1fMB', total_size/1e6));
        
        %% Record success
        processing_time = toc;
        processing_times(end+1) = processing_time;
        success_count = success_count + 1;
        
        % Store summary data
        summary_data{i, 1} = patient_id;
        summary_data{i, 2} = length(ct_files);
        summary_data{i, 3} = num_structures;
        summary_data{i, 4} = ~isempty(resultGUI_data);
        summary_data{i, 5} = true; % Success
        summary_data{i, 6} = processing_time;
        summary_data{i, 7} = '';
        summary_data{i, 8} = total_size;
        
        fprintf('  ✓ SUCCESS (%.1fs)\n\n', processing_time);
        log_msg(log_fid, sprintf('  ✓ SUCCESS - Processing time: %.1fs', processing_time));
        
    catch ME
        %% Handle errors
        processing_time = toc;
        failed_patients{end+1} = patient_id;
        
        error_msg = sprintf('ERROR: %s', ME.message);
        fprintf('  ✗ FAILED: %s\n\n', ME.message);
        log_msg(log_fid, sprintf('  ✗ FAILED: %s', ME.message));
        
        % Store failure data
        summary_data{i, 1} = patient_id;
        summary_data{i, 2} = NaN;
        summary_data{i, 3} = NaN;
        summary_data{i, 4} = false;
        summary_data{i, 5} = false; % Failed
        summary_data{i, 6} = processing_time;
        summary_data{i, 7} = error_msg;
        summary_data{i, 8} = 0;
        
        % Continue with next patient
        continue;
    end
end

%% Generate summary report
fprintf('=================================================================\n');
fprintf('                         PROCESSING SUMMARY                      \n');
fprintf('=================================================================\n');

fprintf('Total Patients: %d\n', num_patients);
fprintf('Successful: %d (%.1f%%)\n', success_count, (success_count/num_patients)*100);
fprintf('Failed: %d (%.1f%%)\n', length(failed_patients), (length(failed_patients)/num_patients)*100);

if ~isempty(processing_times)
    fprintf('Average Processing Time: %.1fs\n', mean(processing_times));
    fprintf('Total Processing Time: %.1fm\n', sum(processing_times)/60);
end

% Write summary to log
if ~isempty(log_fid)
    fprintf(log_fid, '\n=== SUMMARY ===\n');
    fprintf(log_fid, 'Total Patients: %d\n', num_patients);
    fprintf(log_fid, 'Successful: %d (%.1f%%)\n', success_count, (success_count/num_patients)*100);
    fprintf(log_fid, 'Failed: %d (%.1f%%)\n', length(failed_patients), (length(failed_patients)/num_patients)*100);
    if ~isempty(processing_times)
        fprintf(log_fid, 'Average Processing Time: %.1fs\n', mean(processing_times));
        fprintf(log_fid, 'Total Processing Time: %.1fm\n', sum(processing_times)/60);
    end
end

%% Save detailed summary
summary_file = fullfile(hnc_base_path, sprintf('batch_import_summary_%s.mat', datestr(now, 'yyyymmdd_HHMMSS')));
save(summary_file, 'summary_data', 'success_count', 'failed_patients', 'processing_times', '-v7.3');

%% Save CSV summary
csv_file = fullfile(hnc_base_path, sprintf('batch_import_summary_%s.csv', datestr(now, 'yyyymmdd_HHMMSS')));
write_csv_summary(csv_file, summary_data);

fprintf('\nSummary files saved:\n');
fprintf('  - Log: %s\n', log_file);
fprintf('  - Summary: %s\n', summary_file);
fprintf('  - CSV: %s\n', csv_file);

if ~isempty(failed_patients)
    fprintf('\nFailed Patients:\n');
    for i = 1:length(failed_patients)
        fprintf('  - %s\n', failed_patients{i});
    end
end

%% Close log file
if ~isempty(log_fid)
    fprintf(log_fid, '\nCompleted: %s\n', datestr(now));
    fclose(log_fid);
end

fprintf('\n✓ Batch processing completed!\n');

end

%% Helper Functions
function log_msg(fid, msg)
    % Log message to both console and file
    if ~isempty(fid)
        fprintf(fid, '%s: %s\n', datestr(now, 'HH:MM:SS'), msg);
    end
end

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

function write_csv_summary(filename, data)
    % Write summary data to CSV file
    try
        fid = fopen(filename, 'w');
        if fid == -1
            warning('Could not create CSV summary file');
            return;
        end
        
        % Write header
        fprintf(fid, 'Patient_ID,CT_Slices,Structures,Has_Dose,Success,Processing_Time_s,Error,Total_Size_MB\n');
        
        % Write data
        for i = 1:size(data, 1)
            fprintf(fid, '%s,', data{i, 1}); % Patient ID
            
            if isnan(data{i, 2})
                fprintf(fid, ','); % CT slices
            else
                fprintf(fid, '%d,', data{i, 2});
            end
            
            if isnan(data{i, 3})
                fprintf(fid, ','); % Structures
            else
                fprintf(fid, '%d,', data{i, 3});
            end
            
            fprintf(fid, '%d,', data{i, 4}); % Has dose
            fprintf(fid, '%d,', data{i, 5}); % Success
            fprintf(fid, '%.1f,', data{i, 6}); % Processing time
            fprintf(fid, '"%s",', data{i, 7}); % Error message
            fprintf(fid, '%.1f\n', data{i, 8}/1e6); % Total size in MB
        end
        
        fclose(fid);
    catch ME
        warning('MATLAB:CSVError', 'Error writing CSV summary: %s', ME.message);
    end
end 