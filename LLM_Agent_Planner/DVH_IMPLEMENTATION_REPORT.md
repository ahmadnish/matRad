# DVH Calculation Implementation Report
## matRad LLM Agent Planning System

**Date**: June 24, 2025  
**Author**: AI Assistant  
**Purpose**: Comprehensive documentation of DVH calculation development for future reference

---

## Executive Summary

This report documents the complete development of DVH (Dose-Volume Histogram) calculation functionality for the matRad LLM Agent Planning System. The implementation evolved from custom interpolation methods to using matRad's robust `matRad_calcQualityIndicators` function, eliminating interpolation errors and providing standardized clinical metrics.

---

## Development History

### Phase 1: Initial Problem Identification
**Issue**: Error when agent called `calculate_dvh_analysis` for structure 'OuterTarget'
```
Error using matRad_calcDVH
Too many output arguments.
```

**Root Cause**: Incorrect function call in `matrad_tools.py`:
- **Incorrect**: `[dvh, binCenters] = matRad_calcDVH(doseInStruct, '{structure_name}');`
- **Correct**: `matRad_calcDVH(cst, doseCube, dvhType, doseGrid)`

The `matRad_calcDVH` function expects:
- CST (contour structure table) 
- Full dose cube
- DVH type ('cum' for cumulative)
- Not individual dose vectors

### Phase 2: Initial Fix Implementation
**Solution**: Created temporary CST approach
```matlab
% Get CST dimensions and create a temporary CST with just this structure
[numRows, numCols] = size(cst);
tempCst = cell(1, numCols);
tempCst(1,:) = cst(struct_idx,:);

% Calculate DVH using standard matRad function
dvhResult = matRad_calcDVH(tempCst, dose, 'cum');
```

**Challenge**: Dynamic CST sizing issue (6 vs 7 columns)
**Resolution**: Added dynamic column detection with `[numRows, numCols] = size(cst);`

### Phase 3: Custom Interpolation Problems
**Initial Approach**: Manual interpolation for D-metrics and V-metrics
```matlab
% Custom interpolation attempts
unique_volumes = unique(volumes, 'stable');
unique_doses = unique(doses, 'stable');
```

**Issues Encountered**:
1. **Duplicate Values**: DVH data contained duplicate dose/volume points
2. **Interpolation Errors**: `matlab.internal.math.interp1 - Sample points must be unique`
3. **Flat Curve Regions**: DVH curves with plateau regions caused interpolation failures
4. **Data Integrity**: Manual handling of edge cases was error-prone

**Failed Solutions**:
- `unique()` function to remove duplicates
- Custom error handling for flat regions
- Graceful fallbacks when interpolation failed

### Phase 4: Agent Visual Assessment Limitation
**Question**: Could the agent see plotted visuals?
**Finding**: Agent using model "o3" is text-only, cannot see PNG files
**Result**: Agent only received filenames like "Visual Plot: dvh_PTV.png" without visual content

### Phase 5: Text-Based DVH Analysis
**Solution**: Comprehensive textual DVH analysis instead of visual assessment
```python
# Quantitative curve analysis
steepness = calculate_steepness(dvh_data)
dose_spread = d90_volume - d10_volume
low_dose_spillage = analyze_spillage(v_metrics)

# Clinical interpretation
if structure_type == 'TARGET':
    assess_coverage_quality(d95, d50)
    assess_homogeneity(hi_value)
elif structure_type == 'OAR':
    assess_sparing_quality(v_metrics)
```

### Phase 6: Final Error - Variable 'i' Issue
**Problem**: Python error "name 'i' is not defined" in DVH calculation
**Investigation**: All MATLAB loops used proper 'i' syntax, error was in Python data processing

**Root Cause**: Complex iteration through MATLAB data structures in Python:
```python
# Problematic approach
for key, value in data.items():
    if isinstance(key, str) and key.startswith('V_') and key.endswith('Gy'):
        # Complex processing led to variable scope issues
```

### Phase 7: Final Solution - matRad_calcQualityIndicators
**Decision**: Replace all custom interpolation with matRad's standard function
**Implementation**: Clean, explicit data extraction

```matlab
% Use matRad's robust quality indicators
qi = matRad_calcQualityIndicators(tempCst, pln, dose, refGy, refVol);

% Explicit field extraction
dvhData.mean_dose = qiStruct.mean;
dvhData.D95 = qiStruct.D_95;
dvhData.V_5Gy = qiStruct.V_5Gy;
% ... etc for all metrics
```

```python
# Clean Python data extraction
mean_dose = float(dvh_data['mean_dose'])
d95 = float(dvh_data['D95'])
v_5gy = float(dvh_data['V_5Gy'])
```

---

## Technical Architecture

### Current DVH Calculation Flow

1. **Structure Validation**: Find structure index in CST
2. **Temporary CST Creation**: Create single-structure CST for calculations
3. **DVH Calculation**: Use `matRad_calcDVH(tempCst, dose, 'cum')`
4. **Quality Indicators**: Use `matRad_calcQualityIndicators(tempCst, pln, dose, refGy, refVol)`
5. **Data Extraction**: Explicit field extraction to Python
6. **Clinical Assessment**: Generate comprehensive text-based analysis
7. **Visualization**: Create and save DVH plots with key metrics

### Key Functions

#### `matRad_calcQualityIndicators`
**Purpose**: Robust calculation of clinical DVH metrics
**Inputs**:
- `tempCst`: Temporary CST with single structure
- `pln`: Treatment plan structure  
- `dose`: Full dose cube (scaled by fractions)
- `refGy`: Reference doses [5, 10, 20, 30, 40, 50, 60] for V-metrics
- `refVol`: Reference volumes [2, 5, 50, 95, 98] for D-metrics

**Outputs**:
- D-metrics: D₂, D₅, D₅₀, D₉₅, D₉₈ (dose to X% volume)
- V-metrics: V₅Gy, V₁₀Gy, V₂₀Gy, V₃₀Gy, V₄₀Gy, V₅₀Gy, V₆₀Gy (volume receiving X Gy)
- Statistical metrics: mean, max, min, std
- Target metrics: Conformity Index (CI), Homogeneity Index (HI)

### Data Structure
```python
dvh_metrics = {
    "D95": 53.4,           # Dose to 95% volume
    "D50": 63.5,           # Dose to 50% volume  
    "D5": 70.4,            # Dose to 5% volume
    "D2": 71.6,            # Dose to 2% volume
    "D98": 41.2,           # Dose to 98% volume
    "mean_dose": 63.0,     # Mean dose
    "max_dose": 77.9,      # Maximum dose
    "min_dose": 7.9,       # Minimum dose
    "std_dose": 6.8,       # Standard deviation
    "V_5Gy": 1.0,          # Volume receiving ≥5 Gy (100%)
    "V_10Gy": 0.999,       # Volume receiving ≥10 Gy (99.9%)
    "V_20Gy": 0.996,       # Volume receiving ≥20 Gy (99.6%)
    "V_30Gy": 0.990,       # Volume receiving ≥30 Gy (99.0%)
    "V_40Gy": 0.983,       # Volume receiving ≥40 Gy (98.3%)
    "V_50Gy": 0.962,       # Volume receiving ≥50 Gy (96.2%)
    "V_60Gy": 0.842,       # Volume receiving ≥60 Gy (84.2%)
    "HI": 5.2,             # Homogeneity Index (targets only)
    "CI": 0.85             # Conformity Index (targets only)
}
```

---

## Clinical Assessment Implementation

### Target Assessment
```python
if structure_type == 'TARGET':
    # Homogeneity Analysis
    if hi < 5:
        assessment = "EXCELLENT homogeneity"
    elif hi < 10:
        assessment = "GOOD homogeneity"
    else:
        assessment = "Poor homogeneity - optimize plan"
    
    # Coverage Analysis
    coverage = (d95 / d50) * 100
    if coverage >= 95:
        assessment = "EXCELLENT coverage"
    elif coverage >= 90:
        assessment = "GOOD coverage"
    else:
        assessment = "Poor coverage - underdosage risk"
```

### OAR Assessment
```python
elif structure_type == 'OAR':
    if max_dose > 50:
        assessment = "HIGH-DOSE OAR: Consider constraints"
    elif max_dose > 20:
        assessment = "MODERATE-DOSE OAR: Monitor effects"
    else:
        assessment = "LOW-DOSE OAR: Good sparing achieved"
```

### DVH Curve Characteristics
```python
dose_spread = d5 - d95
if structure_type == 'TARGET':
    if dose_spread < 5:
        assessment = "STEEP curve - excellent homogeneity"
    elif dose_spread < 10:
        assessment = "MODERATE curve - good homogeneity"
    else:
        assessment = "SHALLOW curve - dose heterogeneity"
```

---

## Key Learnings

### 1. **Use Standard matRad Functions**
- **Lesson**: Always prefer matRad's built-in functions over custom implementations
- **Reasoning**: matRad functions are extensively tested, handle edge cases, and provide consistent results
- **Example**: `matRad_calcQualityIndicators` handles interpolation, duplicate values, and edge cases automatically

### 2. **Avoid Complex Data Structure Iteration**
- **Lesson**: Explicit field extraction is more reliable than dynamic iteration
- **Problem**: `for key, value in data.items()` with complex filtering led to variable scope issues
- **Solution**: Direct field access `dvh_data['field_name']` with explicit type conversion

### 3. **LLM Agents Need Text-Based Analysis**
- **Lesson**: Visual plots are not accessible to text-only LLM agents
- **Solution**: Comprehensive textual analysis with quantitative metrics and clinical interpretation
- **Benefit**: More detailed analysis than visual inspection alone

### 4. **Robust Error Handling**
- **Lesson**: DVH data can contain edge cases (flat regions, duplicates, sparse data)
- **Implementation**: Use matRad's robust functions that handle these cases internally
- **Fallback**: Always provide meaningful error messages for debugging

### 5. **Clinical Context is Essential**
- **Lesson**: Raw DVH metrics are not useful without clinical interpretation
- **Implementation**: Automated assessment of homogeneity, coverage, sparing quality
- **Benefit**: Actionable insights for treatment planning optimization

### 6. **Data Validation is Critical**
- **Lesson**: Always validate input data before processing
- **Checks**: CST existence, dose data availability, structure index validity
- **Prevention**: Graceful error handling prevents workflow interruption

---

## Current Capabilities

### DVH Calculation Features
✅ **Single Structure Analysis**: Detailed DVH metrics for individual structures  
✅ **All Structures Overview**: Summary DVH information for all structures  
✅ **Robust Quality Indicators**: D-metrics, V-metrics, CI, HI using matRad standards  
✅ **Clinical Assessment**: Automated interpretation for targets and OARs  
✅ **Visual Plots**: DVH curve generation with key metrics highlighted  
✅ **Error Handling**: Graceful failure with meaningful error messages  

### Integration with LLM Agent
✅ **Text-Based Analysis**: Comprehensive textual DVH assessment  
✅ **Clinical Recommendations**: Actionable insights for plan optimization  
✅ **Standardized Metrics**: Consistent with clinical practice  
✅ **Agent Accessibility**: All information available as structured text  

---

## Future Considerations

### Potential Enhancements
1. **Additional Quality Metrics**
   - NTCP (Normal Tissue Complication Probability)
   - TCP (Tumor Control Probability)
   - Plan complexity metrics

2. **Multi-Fraction Analysis**
   - Cumulative DVH across multiple fractions
   - Fraction-specific dose analysis
   - Adaptive planning support

3. **Comparative Analysis**
   - Plan comparison DVH metrics
   - Baseline vs. optimized plan assessment
   - Historical plan database integration

4. **Advanced Clinical Guidelines**
   - Institution-specific dose constraints
   - Protocol compliance checking
   - Automated plan acceptance criteria

### Performance Optimizations
1. **Caching**: Store calculated DVH results for repeated access
2. **Parallel Processing**: Simultaneous DVH calculation for multiple structures
3. **Memory Management**: Efficient handling of large dose matrices

---

## Technical Specifications

### Dependencies
- **matRad**: Core radiation therapy planning framework
- **MATLAB Engine for Python**: Interface between Python and MATLAB
- **matRad_calcDVH**: Standard DVH calculation function
- **matRad_calcQualityIndicators**: Quality metrics calculation function

### Input Requirements
- **CST**: Contour structure table with structure definitions
- **Dose Cube**: 3D dose distribution matrix
- **Plan**: Treatment plan structure with fraction information
- **Structure Name**: Valid structure identifier from CST

### Output Format
```python
{
    "success": True,
    "structure": "CTV63",
    "structure_type": "TARGET", 
    "dvh_assessment": "Comprehensive textual analysis...",
    "dvh_metrics": {
        # Complete metrics dictionary
    },
    "plot_file": "dvh_CTV63.png",
    "message": "DVH analyzed using matRad quality indicators"
}
```

---

## Conclusion

The DVH calculation implementation has evolved from a problematic custom solution to a robust, clinically-relevant system using matRad's standard functions. The key success factors were:

1. **Leveraging matRad Expertise**: Using `matRad_calcQualityIndicators` instead of custom interpolation
2. **Clean Data Handling**: Explicit field extraction avoiding complex iterations  
3. **Clinical Focus**: Providing actionable insights rather than raw metrics
4. **Text-Based Design**: Optimized for LLM agent consumption
5. **Robust Error Handling**: Graceful failure with informative messaging

This implementation provides the LLM agent with comprehensive, clinically-relevant DVH analysis capabilities that support effective treatment planning optimization and quality assessment.

---

**Implementation Status**: ✅ COMPLETE  
**Testing Status**: ✅ VERIFIED  
**Integration Status**: ✅ FUNCTIONAL  
**Documentation Status**: ✅ COMPREHENSIVE 