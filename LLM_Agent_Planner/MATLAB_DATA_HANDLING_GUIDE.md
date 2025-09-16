# MATLAB Engine Data Handling Guide

## Critical Pattern Documentation

This document addresses a recurring pattern in MATLAB-Python data handling that has caused issues multiple times. **Always refer to this guide when working with MATLAB engine data extraction.**

## The Problem Pattern

When extracting data from MATLAB arrays through the Python engine, there are specific patterns that must be followed to correctly access individual elements.

### Issue 1: Structure Data Format Variations

**Problem**: MATLAB functions may return structure data in different formats depending on implementation.

**Example from `get_structure_names()`**:
```python
# WRONG assumption - expecting unified format
structures = [s["name"] for s in struct_info.get("structures", [])]

# CORRECT handling - check for multiple possible formats
if "structures" in struct_info:
    structure_names = [s["name"] for s in struct_info.get("structures", [])]
else:
    # Handle separated format
    structure_names = []
    structure_names.extend(struct_info.get("targets", []))
    structure_names.extend(struct_info.get("oars", []))
    structure_names.extend(struct_info.get("other", []))
```

**Lesson**: Always check for multiple possible data formats when interfacing with MATLAB functions.

### Issue 2: MATLAB Array Element Access

**Problem**: MATLAB arrays returned to Python have special data structures that require specific access patterns.

**Example from `create_ring_structures()`**:

MATLAB returns data like:
```python
margins_list = [matlab.double([5.0]), matlab.double([10.0])]
voxels_list = [matlab.double([4169.0]), matlab.double([6803.0])]
```

**WRONG approach**:
```python
# This gets the first element from ALL arrays, not the i-th element
margin_val = float(margins_list[i]._data[0])  # Always gets [0], not [i]
voxels_val = int(voxels_list[i]._data[0])     # Always gets [0], not [i]
```

**CORRECT approach**:
```python
# This gets the i-th element from the i-th array
margin_val = float(margins_list[i]._data[i])  # Gets [i] from i-th array
voxels_val = int(voxels_list[i]._data[i])     # Gets [i] from i-th array
```

**Lesson**: When accessing MATLAB array elements, use the loop index consistently across both the array selection and the element selection.

### Issue 3: CST Index Mapping

**Problem**: Python list indices don't match MATLAB CST row indices.

**WRONG approach**:
```python
# Python indices don't match MATLAB CST indices
structures = combine_all_structure_categories()
ref_index = structures.index(reference_structure) + 1  # WRONG!
```

**CORRECT approach**:
```python
# Query MATLAB directly for the correct CST index
matlab_code = f"""
ref_index = 0;
for i = 1:size(cst, 1)
    if strcmp(cst{{i, 2}}, '{reference_structure}')
        ref_index = i;
        break;
    end
end
"""
self.eng.eval(matlab_code, nargout=0)
ref_index = int(self.eng.eval("ref_index"))
```

**Lesson**: Always use MATLAB-side lookups for CST indices rather than Python-side index calculations.

## General MATLAB-Python Data Handling Principles

### 1. Data Type Inspection
Always inspect the actual data types returned by MATLAB:
```python
print(f"Type: {type(matlab_data)}")
print(f"Data: {matlab_data}")
if hasattr(matlab_data, '_data'):
    print(f"_data: {matlab_data._data}")
```

### 2. Robust Data Extraction Pattern
```python
def extract_matlab_value(matlab_obj, index=None):
    """Robustly extract value from MATLAB object."""
    if hasattr(matlab_obj, '_data'):
        data = matlab_obj._data
        if index is not None:
            return data[index] if len(data) > index else data[0]
        else:
            return data[0] if len(data) > 0 else 0
    elif hasattr(matlab_obj, '__iter__') and len(matlab_obj) > 0:
        return matlab_obj[index] if index is not None else matlab_obj[0]
    else:
        return matlab_obj
```

### 3. Format Validation
Always validate data formats before processing:
```python
# Check for expected fields
required_fields = ['field1', 'field2']
for field in required_fields:
    if field not in matlab_result:
        # Handle missing field or use alternative access pattern
        pass
```

### 4. Index Consistency
When working with arrays and indices:
```python
# WRONG - mixing different indexing schemes
for i in range(len(python_list)):
    value = matlab_array[0]._data[i]  # Inconsistent indexing

# CORRECT - consistent indexing
for i in range(len(python_list)):
    value = matlab_array[i]._data[i]  # Consistent indexing
```

## Debugging MATLAB Data Issues

### 1. Add Debug Prints
```python
print(f"MATLAB data type: {type(matlab_data)}")
print(f"MATLAB data contents: {matlab_data}")
if hasattr(matlab_data, '_data'):
    print(f"_data contents: {matlab_data._data}")
    print(f"_data type: {type(matlab_data._data)}")
```

### 2. Test with Simple Cases
Always test with minimal examples:
```python
# Test with single element first
test_result = eng.eval("test_var = 42;")
print(f"Simple test: {eng.eval('test_var')}")

# Then test with arrays
test_result = eng.eval("test_array = [1, 2, 3];")
test_data = eng.eval("test_array")
print(f"Array test: {test_data}")
```

### 3. Verify MATLAB-side Data
Always verify the data exists correctly in MATLAB:
```python
eng.eval("disp('MATLAB data:'); disp(variable_name);", nargout=0)
```

## Common Error Patterns to Avoid

1. **Assuming single data format**: Always check for multiple possible formats
2. **Inconsistent indexing**: Use the same index for both array selection and element access
3. **Python-side CST indexing**: Always use MATLAB-side lookups for structure indices
4. **Missing error handling**: Always wrap MATLAB data access in try-catch blocks
5. **Ignoring data types**: Always inspect and handle MATLAB-specific data types

## Resolution Checklist

When encountering MATLAB data issues:

- [ ] Print actual data types and contents
- [ ] Check for multiple possible data formats
- [ ] Verify indexing consistency 
- [ ] Test with minimal examples
- [ ] Add comprehensive error handling
- [ ] Validate data exists in MATLAB workspace
- [ ] Use MATLAB-side operations for complex lookups

## Future Reference

This pattern has appeared in:
1. `get_structure_names()` - multiple format handling
2. `create_ring_structures()` - array element access  
3. CST index mapping - MATLAB vs Python indices
4. `test_structure_management.py` verification step - same format handling issue

**Pattern Recognition**: Any time you're working with structure lists, always implement the dual-format handling pattern:

```python
# Standard pattern for structure list handling
if "structures" in struct_info:
    structure_names = [s["name"] for s in struct_info.get("structures", [])]
else:
    # Handle separated format
    structure_names = []
    structure_names.extend(struct_info.get("targets", []))
    structure_names.extend(struct_info.get("oars", []))
    structure_names.extend(struct_info.get("other", []))
```

Always refer to this guide when implementing new MATLAB-Python interfaces to avoid repeating these patterns.
