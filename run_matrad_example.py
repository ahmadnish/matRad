import matlab.engine
import os

# Start the MATLAB engine
print("Starting MATLAB engine...")
eng = matlab.engine.start_matlab()

# Get current directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")

# Change to the matRad directory if needed
eng.cd(current_dir)

# Initialize matRad
print("Initializing matRad...")
eng.matRad_rc(nargout=0)

# Load the HEAD_AND_NECK.mat file
print("Loading HEAD_AND_NECK.mat...")
eng.load('matRad/phantoms/HEAD_AND_NECK.mat', nargout=0)

# Get information about loaded variables
print("Inspecting loaded data...")
eng.eval("whos", nargout=0)

# Check if the variables exist
ct_exists = eng.eval("exist('ct', 'var')", nargout=1)
print(f"CT data exists: {ct_exists == 1}")

cst_exists = eng.eval("exist('cst', 'var')", nargout=1)
print(f"CST data exists: {cst_exists == 1}")

# Inspect CT data structure if it exists
if ct_exists == 1:
    ct_fields = eng.eval('fieldnames(ct)', nargout=1)
    print("\nCT data fields:")
    for field in ct_fields:
        print(f"- {field}")
    
    # Get dimensions of ct.cube
    ct_dims = eng.eval('size(ct.cube)', nargout=1)
    print(f"CT cube dimensions: {ct_dims}")

# Inspect CST data structure if it exists
if cst_exists == 1:
    cst_size = eng.eval('size(cst)', nargout=1)
    print(f"\nCST dimensions: {cst_size}")
    
    # Get number of structures
    num_structures = eng.eval('numel(cst)', nargout=1)
    print(f"Number of structures in CST: {num_structures}")
    
    # Print information about the first structure
    print("First structure information:")
    eng.eval("disp(cst{1})", nargout=0)

# Close the MATLAB engine
print("\nClosing MATLAB engine...")
eng.quit() 