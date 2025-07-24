# Quick Usage Guide for matRad Batch DICOM Import

This guide provides step-by-step instructions for using the batch DICOM import scripts I've created for your HNC-IMRT-70-33 dataset.

## Files Created

1. **`batch_dicom_import_hnc.m`** - Main batch processing script
2. **`test_single_patient_import.m`** - Test script for single patient
3. **`README_batch_dicom_import.md`** - Comprehensive documentation
4. **`USAGE_GUIDE.md`** - This quick guide

## Quick Start (Recommended Approach)

### Step 1: Setup Environment
```matlab
% Make sure matRad is in your MATLAB path
addpath('/path/to/matRad');

% Initialize matRad
matRad_cfg = MatRad_Config.instance();
```

### Step 2: Test Single Patient First
```matlab
% Test the import process on one patient to verify everything works
test_single_patient_import('HNC_015');  % or any available patient
```

### Step 3: Run Full Batch Processing
```matlab
% Process all patients (only after successful single patient test)
batch_dicom_import_hnc();
```

## What Happens During Processing

### Test Script (`test_single_patient_import.m`)
- Verifies directory structure
- Validates DICOM files
- Tests matRad import functionality
- Analyzes imported data
- Tests data export/import
- Provides detailed feedback

### Batch Script (`batch_dicom_import_hnc.m`)
- Processes all ~213 HNC patients automatically
- Creates detailed logs and progress reports
- Handles errors gracefully (continues with other patients)
- Saves standardized .mat files for each patient
- Generates comprehensive summary reports

## Expected Output

### For Each Patient Directory (e.g., HNC_015/)
```
HNC_015/
├── CT/                    # Original DICOM files
├── RTSTRUCT/             # Original DICOM files  
├── RTDOSE/               # Original DICOM files
├── ct.mat                # ← New: CT data (~20-100 MB)
├── cst.mat               # ← New: Structure data (~1-5 MB)
├── resultGUI.mat         # ← New: Dose data (~10-50 MB, if available)
├── pln.mat               # ← New: Plan data (~1 MB, if available)
└── stf.mat               # ← New: Steering data (~1 MB, if available)
```

### In Base Directory (HNC-IMRT-70-33/)
```
batch_import_log_20241213_143022.txt      # Detailed processing log
batch_import_summary_20241213_143022.mat  # MATLAB summary data
batch_import_summary_20241213_143022.csv  # CSV summary for analysis
```

## Important Notes

1. **Path Configuration**: Edit line 38 in both scripts to match your data location:
   ```matlab
   hnc_base_path = '/your/path/to/HNC-IMRT-70-33';
   ```

2. **Processing Time**: 
   - Single patient test: ~30-60 seconds
   - Full batch processing: ~2-4 hours for all patients

3. **Disk Space**: Plan for ~50-200 MB of .mat files per patient

4. **Memory**: Peak usage ~2-4 GB for large datasets

## Verification

After processing, verify success by:

1. **Check the CSV summary** for success rates
2. **Load a sample patient**:
   ```matlab
   load('HNC_015/ct.mat');
   load('HNC_015/cst.mat');
   
   % Verify data
   fprintf('CT: %dx%dx%d\n', size(ct.cube{1}));
   fprintf('Structures: %d\n', size(cst, 1));
   ```

3. **Check log files** for any error messages

## Using the Data with matRad

After import, the data is ready for matRad workflows:

```matlab
% Load patient data
load('HNC_015/ct.mat');
load('HNC_015/cst.mat');

% Standard matRad workflow
pln = matRad_createPlan(ct, cst, 'photons');
stf = matRad_generateStf(ct, cst, pln);
dij = matRad_calcPhotonDose(ct, stf, pln, cst);
% ... continue with optimization, etc.
```

## Troubleshooting

If the test script fails, check:
- matRad is properly installed and in MATLAB path
- Path to HNC data is correct
- DICOM files are not corrupted
- Sufficient disk space and memory

If batch processing has failures:
- Check the log files for specific error messages
- The CSV summary shows which patients failed
- Failed patients can be processed individually for debugging

## Need Help?

1. Check `README_batch_dicom_import.md` for comprehensive documentation
2. Review log files for detailed error information
3. Test individual patients using the test script
4. Verify matRad installation and requirements

## Summary

This automated batch import system will save you from manually loading ~213 patients one by one through the matRadGUI. Instead, you can:

1. Test one patient in ~1 minute
2. Run the batch script and let it process all patients automatically
3. Come back in a few hours to find all data imported and ready to use

The scripts follow matRad's standard import workflow and produce fully compatible .mat files that can be used directly in any matRad treatment planning workflow. 