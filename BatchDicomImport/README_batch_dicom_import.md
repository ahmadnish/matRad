# matRad Batch DICOM Import for Head & Neck Cancer Patients

This repository contains a MATLAB script for batch importing DICOM files for Head & Neck Cancer (HNC) patients using matRad's DICOM import functionality.

## Overview

The script `batch_dicom_import_hnc.m` automates the process of loading DICOM files (CT, RTSTRUCT, RTDOSE) for ~213 HNC patients, mimicking the "Load DICOM" functionality in matRadGUI but in a batch processing mode.

## Features

- **Batch Processing**: Automatically processes all HNC patient folders
- **matRad Integration**: Uses matRad's native `matRad_DicomImporter` class
- **Comprehensive Logging**: Creates detailed logs and summary reports
- **Error Handling**: Continues processing even if individual patients fail
- **Data Validation**: Verifies imported data integrity
- **Multiple Output Formats**: Saves data as .mat files with proper matRad variable names

## Requirements

- MATLAB with Image Processing Toolbox
- matRad properly installed and configured
- HNC-IMRT-70-33 dataset with the following structure:
  ```
  HNC-IMRT-70-33/
  ├── HNC_015/
  │   ├── CT/
  │   │   ├── HNC_015_CT_001.dcm
  │   │   ├── HNC_015_CT_002.dcm
  │   │   └── ...
  │   ├── RTSTRUCT/
  │   │   └── HNC_015_RTSTRUCT.dcm
  │   ├── RTDOSE/
  │   │   └── HNC_015_RTDOSE.dcm
  │   └── RTPLAN/ (optional)
  ├── HNC_016/
  └── ...
  ```

## Usage

1. **Setup matRad Environment**:
   ```matlab
   % Ensure matRad is in your MATLAB path
   addpath('/path/to/matRad');
   
   % Initialize matRad (if not already done)
   matRad_cfg = MatRad_Config.instance();
   ```

2. **Update Path in Script**:
   Edit line 38 in `batch_dicom_import_hnc.m` to point to your HNC data directory:
   ```matlab
   hnc_base_path = '/path/to/your/HNC-IMRT-70-33';
   ```

3. **Run the Script**:
   ```matlab
   batch_dicom_import_hnc();
   ```

## What the Script Does

### 1. **Environment Setup**
- Initializes matRad configuration
- Disables GUI elements for batch processing
- Verifies the HNC data directory exists

### 2. **Patient Discovery**
- Scans for all directories matching pattern `HNC_*`
- Validates required subdirectories (CT, RTSTRUCT, RTDOSE)
- Counts DICOM files for verification

### 3. **DICOM Import Process**
For each patient:
- Creates a `matRad_DicomImporter` instance
- Imports CT data (converts to water equivalent densities)
- Imports RTSTRUCT data (creates structure contours)
- Imports RTDOSE data (if available)
- Validates imported data integrity

### 4. **Data Export**
Saves the following .mat files in each patient directory:
- `ct.mat` - CT data with matRad standard format
- `cst.mat` - Clinical Structure data (contours, objectives)
- `resultGUI.mat` - Dose data (if RTDOSE was available)
- `pln.mat` - Plan data (if RTPLAN was available)
- `stf.mat` - Steering file data (if beam data was available)

### 5. **Logging and Reporting**
- Creates timestamped log files with detailed processing information
- Generates summary reports in both .mat and .csv formats
- Tracks processing times and success/failure rates

## Output Files

After processing, the following files are created in the base directory:

### Log Files
- `batch_import_log_YYYYMMDD_HHMMSS.txt` - Detailed processing log
- `batch_import_summary_YYYYMMDD_HHMMSS.mat` - MATLAB summary data
- `batch_import_summary_YYYYMMDD_HHMMSS.csv` - CSV summary for analysis

### Patient Data Files
Each patient directory will contain:
- `ct.mat` - CT data (typically 20-100 MB)
- `cst.mat` - Structure data (typically 1-5 MB)
- `resultGUI.mat` - Dose data if available (typically 10-50 MB)
- `pln.mat` - Plan data if available (typically < 1 MB)
- `stf.mat` - Steering data if available (typically < 1 MB)

## CSV Summary Format

The CSV summary contains the following columns:
- `Patient_ID` - Patient identifier (e.g., HNC_015)
- `CT_Slices` - Number of CT slices imported
- `Structures` - Number of anatomical structures found
- `Has_Dose` - Boolean indicating if dose data was available
- `Success` - Boolean indicating successful processing
- `Processing_Time_s` - Time taken to process this patient (seconds)
- `Error` - Error message if processing failed
- `Total_Size_MB` - Total size of saved .mat files (MB)

## Error Handling

The script is designed to be robust:
- Continues processing if individual patients fail
- Logs detailed error messages for debugging
- Provides summary of failed patients at the end
- Validates data integrity at each step

Common failure modes:
- Missing or corrupted DICOM files
- Non-standard DICOM formats
- Insufficient disk space
- Memory limitations for very large datasets

## Performance Considerations

- **Processing Time**: Approximately 30-120 seconds per patient depending on data size
- **Memory Usage**: Peak memory usage typically 2-4 GB for large CT datasets
- **Disk Space**: Approximately 50-200 MB of .mat files per patient
- **Total Time**: Complete processing of ~213 patients takes approximately 2-4 hours

## Troubleshooting

### Common Issues

1. **matRad Not Found**:
   ```
   Error: matRad not properly initialized
   Solution: Ensure matRad is in MATLAB path and properly configured
   ```

2. **Path Not Found**:
   ```
   Error: HNC data directory not found
   Solution: Update hnc_base_path variable in the script
   ```

3. **Memory Issues**:
   ```
   Error: Out of memory
   Solution: Close other applications, restart MATLAB, or process in smaller batches
   ```

4. **Permission Issues**:
   ```
   Error: Could not create log file
   Solution: Ensure write permissions in the HNC data directory
   ```

### Verification

To verify successful import, check:
1. Log files for any error messages
2. CSV summary for success rates
3. Individual patient folders for .mat files
4. File sizes are reasonable (not 0 bytes)

Load a sample patient to verify data integrity:
```matlab
% Load patient data
load('/path/to/HNC_015/ct.mat');
load('/path/to/HNC_015/cst.mat');

% Check CT data
fprintf('CT dimensions: %dx%dx%d\n', size(ct.cube{1}));
fprintf('CT resolution: %.2f x %.2f x %.2f mm\n', ct.resolution.x, ct.resolution.y, ct.resolution.z);

% Check structure data
fprintf('Number of structures: %d\n', size(cst, 1));
for i = 1:size(cst, 1)
    fprintf('  %d: %s\n', i, cst{i, 2});
end
```

## Script Architecture

The script is organized into several main sections:

1. **Initialization** - Environment setup and configuration
2. **Discovery** - Finding and validating patient directories
3. **Processing Loop** - Main batch processing logic
4. **Data Import** - matRad DICOM import operations
5. **Data Export** - Saving in matRad-compatible formats
6. **Reporting** - Logging and summary generation
7. **Helper Functions** - Utility functions for logging and file operations

## Customization

The script can be easily customized:

- **Path Configuration**: Update `hnc_base_path` for different datasets
- **Output Format**: Modify save operations for different file formats
- **Processing Options**: Adjust matRad importer settings
- **Logging Level**: Modify logging verbosity
- **Error Handling**: Customize error recovery strategies

## Integration with matRad Workflow

The imported data is fully compatible with standard matRad workflows:

```matlab
% After import, use standard matRad functions
load('HNC_015/ct.mat');
load('HNC_015/cst.mat');

% Create treatment plan
pln = matRad_createPlan(ct, cst, 'photons');

% Generate beam geometry
stf = matRad_generateStf(ct, cst, pln);

% Calculate dose influence matrix
dij = matRad_calcPhotonDose(ct, stf, pln, cst);

% Continue with standard matRad workflow...
```

## License and Credits

This script was developed for use with the matRad treatment planning system. 
matRad is licensed under the GPL v3 license.

For questions or issues, please refer to the matRad documentation or community forums.

---

**Last Updated**: December 2024  
**matRad Version**: Compatible with matRad 3.0+  
**MATLAB Version**: Tested with MATLAB 2019b+ 