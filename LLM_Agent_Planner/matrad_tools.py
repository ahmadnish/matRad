"""
MATLAB/matRad Tool Wrappers

This module provides Python wrapper functions for matRad MATLAB functions,
using the MATLAB Engine API for Python to interface with matRad.
"""

import os
import time
import json
import numpy as np

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import math
from openai import OpenAI

import matlab.engine

class MatRadEngine:
    """Wrapper for MATLAB Engine with matRad functionality."""
    
    def __init__(self, matrad_path: Optional[str] = None):
        """
        Initialize the MATLAB Engine with matRad path.
        
        Args:
            matrad_path: Path to matRad installation. If None, assumes current directory.
        """
        self.eng = None
        self.matrad_path = matrad_path or os.getcwd()
        self.initialized = False
        self.patient_loaded = False
        self.current_patient = None
        
        # Store planning variables
        self.ct = None
        self.cst = None
        self.pln = None
        self.stf = None
        self.dij = None
        self.resultGUI = None
        
        # Store optimized weights for warm-start
        self.optimized_weights = None
        self.weights_available = False
        
    def start_engine(self) -> bool:
        """
        Start the MATLAB Engine and initialize matRad.
        
        Returns:
            bool: True if successful.
            
        Raises:
            RuntimeError: If MATLAB Engine is not available or initialization fails.
        """        
            
        try:
            print("Starting MATLAB Engine...")
            self.eng = matlab.engine.start_matlab()
            
            # Change to matRad directory
            self.eng.cd(self.matrad_path)
            
            # Initialize matRad
            print("Initializing matRad...")
            self.eng.matRad_rc(nargout=0)
            
            # Disable GUI elements (waitbars, plot windows, etc.)
            print("Disabling GUI elements...")
            self.disable_gui_elements()
            
            self.initialized = True
            print("matRad initialized successfully.")
            return True
            
        except Exception as e:
            error_msg = f"Error initializing MATLAB Engine: {str(e)}"
            print(error_msg)
            raise RuntimeError(error_msg)
    
    def disable_gui_elements(self) -> bool:
        """
        Disable all GUI elements including waitbars, plot windows, and progress indicators.
        This prevents pop-ups during dose calculation and optimization.
        
        Returns:
            bool: True if successful.
        """
        if not self.eng:
            return False
            
        try:
            # Set global matRad configuration to disable GUI
            self.eng.eval("""
            % Get matRad configuration instance
            matRad_cfg = MatRad_Config.instance();
            
            % Disable all GUI elements including waitbars and pop-outs
            matRad_cfg.disableGUI = true;
            
            % Also disable any potential plot functions for fmincon
            % This will be applied when the optimizer is configured
            fprintf('✅ GUI elements disabled - no waitbars or plot windows will appear\\n');
            """, nargout=0)
            
            print("✅ Successfully disabled GUI elements")
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Could not disable GUI elements: {e}")
            return False
    
    def stop_engine(self) -> bool:
        """
        Stop the MATLAB Engine.
        
        Returns:
            bool: True if successful.
            
        Raises:
            RuntimeError: If there's an error stopping the MATLAB Engine.
        """
        if not self.initialized:
            self.initialized = False
            return True
            
        try:
            self.eng.quit()
            self.initialized = False
            print("MATLAB Engine stopped.")
            return True
        except Exception as e:
            error_msg = f"Error stopping MATLAB Engine: {str(e)}"
            print(error_msg)
            raise RuntimeError(error_msg)
    
    def load_patient(self, patient_file: str) -> Dict[str, Any]:
        """
        Load a patient dataset from .mat file.
        
        Args:
            patient_file: Path to the .mat file containing patient data.
            
        Returns:
            Dict with patient information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        try:
            # Check if file exists
            if not os.path.exists(patient_file):
                # Try checking if it's in matRad/phantoms
                phantom_path = os.path.join(self.matrad_path, "matRad", "phantoms", patient_file)
                if os.path.exists(phantom_path):
                    patient_file = phantom_path
                else:
                    return {"success": False, "error": f"Patient file not found: {patient_file}"}
            
            # Load the patient data
            print(f"Loading patient data from {patient_file}...")
            self.eng.load(patient_file, nargout=0)
            
            # Check if ct and cst variables exist
            ct_exists = self.eng.eval("exist('ct', 'var')", nargout=1)
            cst_exists = self.eng.eval("exist('cst', 'var')", nargout=1)
            
            if ct_exists != 1 or cst_exists != 1:
                return {"success": False, "error": "Patient data missing CT or CST information"}
            
            # Get basic information about the dataset
            ct_dimensions = self.eng.eval("size(ct.cube)", nargout=1)
            num_structures = self.eng.eval("numel(cst)", nargout=1)
            
            # Instead of directly accessing the workspace, store references to the variables
            # The CT structure is usually fine to access directly
            self.ct = self.eng.workspace["ct"]
            
            # For the CST, don't try to get it directly as a Python object
            # Just keep a reference that it exists in the MATLAB workspace
            self.cst = None  # We'll just use the MATLAB workspace version
            
            self.current_patient = patient_file
            self.patient_loaded = True
            
            # Return summary information
            return {
                "success": True, 
                "patient_file": patient_file,
                "ct_dimensions": ct_dimensions,
                "num_structures": num_structures,
                "message": "Patient data loaded successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_structure_names(self) -> Dict[str, Any]:
        """
        Get the names of all structures in the loaded patient.
        
        Returns:
            Dict with structure names and types or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # First check if cst exists in the MATLAB workspace
            cst_exists = self.eng.eval("exist('cst', 'var')", nargout=1)
            if cst_exists != 1:
                return {"success": False, "error": "CST not found in MATLAB workspace"}
            
            # Get the size of the cst to determine how many structures there are
            cst_size = self.eng.eval("size(cst, 1)", nargout=1)
            
            # Initialize empty lists for the different structure types
            target_list = []
            oar_list = []
            other_list = []
            
            # Loop through structures one by one to get names and types
            for i in range(1, int(cst_size) + 1):
                # Get the structure name
                name = self.eng.eval(f"cst{{{i},2}}", nargout=1)
                
                # Skip empty structures
                if not name:
                    continue
                    
                # Get the structure type
                struct_type = self.eng.eval(f"cst{{{i},3}}", nargout=1)
                
                # Add to appropriate list
                if struct_type == "TARGET":
                    target_list.append(str(name))
                elif struct_type == "OAR":
                    oar_list.append(str(name))
                else:
                    other_list.append(str(name))
            
            return {
                "success": True,
                "targets": target_list,
                "oars": oar_list,
                "other": other_list
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_structure_volumes(self) -> Dict[str, Any]:
        """
        Get structure volumes (in voxels), types, and priorities.
        
        Returns:
            Dict with structure details including voxel counts and priorities, or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # First check if cst exists
            cst_exists = self.eng.eval("exist('cst', 'var')", nargout=1)
            if cst_exists != 1:
                return {"success": False, "error": "CST not found in MATLAB workspace"}
            
            # Get cst size
            cst_size = self.eng.eval("size(cst, 1)", nargout=1)
            
            structures = []
            
            for i in range(1, int(cst_size) + 1):
                name = self.eng.eval(f"cst{{{i},2}}", nargout=1)
                if not name:
                    continue
                
                struct_type = self.eng.eval(f"cst{{{i},3}}", nargout=1)
                
                # Get volume (num voxels)
                # cst{i,4} is a cell array of indices. For 3D, it's usually 1 element.
                # We'll take the length of the first element.
                num_voxels = self.eng.eval(f"numel(cst{{{i},4}}{{1}})", nargout=1)
                
                # Get priority
                # cst{i,5} is a struct. Check if Priority field exists.
                try:
                    # Check if Priority field exists in the struct
                    has_priority = self.eng.eval(f"isfield(cst{{{i},5}}, 'Priority')", nargout=1)
                    if has_priority:
                        priority = self.eng.eval(f"cst{{{i},5}}.Priority", nargout=1)
                    else:
                        priority = 0 # Default 
                except:
                    priority = 0
                
                structures.append({
                    "name": str(name),
                    "type": str(struct_type),
                    "voxels": int(num_voxels),
                    "priority": int(priority)
                })
                
            return {
                "success": True,
                "structures": structures
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_empty_plan(self, num_fractions: int = 30) -> Dict[str, Any]:
        """
        Create an empty treatment plan structure.
        
        Args:
            num_fractions: Number of treatment fractions (default: 30)
        
        Returns:
            Dict with plan information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Create a new plan
            self.eng.eval(f"""
            pln = struct();
            pln.radiationMode   = 'photons';
            pln.machine         = 'Generic';
            pln.numOfFractions  = {num_fractions};
             
            % Default beam setup - will be modified later
            pln.propStf.gantryAngles    = [0:72:359];
            pln.propStf.couchAngles     = zeros(1, numel([0:72:359]));
            pln.propStf.bixelWidth      = 5;
            pln.propStf.numOfBeams      = numel(pln.propStf.gantryAngles);
            pln.propStf.isoCenter       = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);

            % Biological and optimization settings
            pln.bioModel = 'none'; 
            pln.multScen = 'nomScen';
            pln.propOpt.quantityOpt = 'physicalDose';

            % Dose calculation settings
            pln.propDoseCalc.doseGrid.resolution.x = 3; % [mm]
            pln.propDoseCalc.doseGrid.resolution.y = 3; % [mm]
            pln.propDoseCalc.doseGrid.resolution.z = 3; % [mm]
            
            % Default IMRT without sequencing or DAO
            pln.propSeq.runSequencing = false;
            pln.propOpt.runDAO = false;
            
            % Set up fmincon with GUI elements disabled
            pln.propOpt.fmincon.Display = 'off';
            pln.propOpt.fmincon.PlotFcn = [];  % Disable all plot functions
            """, nargout=0)
            
            # Store plan in class
            self.pln = self.eng.workspace["pln"]
            
            # Return summary information
            gantry_angles = self.eng.eval("pln.propStf.gantryAngles", nargout=1)
            num_beams = self.eng.eval("pln.propStf.numOfBeams", nargout=1)
            
            return {
                "success": True,
                "radiation_mode": "photons",
                "num_fractions": num_fractions,
                "num_beams": num_beams,
                "gantry_angles": list(gantry_angles[0]),
                "message": "Treatment plan initialized successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def set_beam_angles(self, gantry_angles: List[float], couch_angles: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Set the beam angles for the treatment plan.
        
        Args:
            gantry_angles: List of gantry angles in degrees.
            couch_angles: List of couch angles in degrees. If None, all zeros.
            
        Returns:
            Dict with beam setup information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.pln is None:
            return {"success": False, "error": "No treatment plan created. Call create_empty_plan first."}
            
        try:
            # Prepare couch angles if not provided
            if couch_angles is None:
                couch_angles = [0] * len(gantry_angles)
                
            # Validate inputs
            if len(gantry_angles) != len(couch_angles):
                return {"success": False, "error": "Number of gantry and couch angles must match"}
                
            # Convert to MATLAB arrays
            gantry_array = matlab.double(gantry_angles)
            couch_array = matlab.double(couch_angles)
            
            # Update plan
            self.eng.eval(f"""
            pln.propStf.gantryAngles = {gantry_array};
            pln.propStf.couchAngles = {couch_array};
            pln.propStf.numOfBeams = numel(pln.propStf.gantryAngles);
            pln.propStf.isoCenter = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
            """, nargout=0)
            
            # Update plan in class
            self.pln = self.eng.workspace["pln"]
            
            # Clear optimized weights since beam configuration changed
            self.optimized_weights = None
            self.weights_available = False

            print("Generating beam geometry...")
            self.eng.eval("stf = matRad_generateStf(ct,cst,pln);", nargout=0)
            
            # Instead of trying to get the entire stf struct, just keep track that it exists
            # self.stf = self.eng.workspace["stf"]  
            self.stf = True  # Just mark that stf exists in MATLAB workspace
            
            # Get beam info
            num_beams = self.eng.eval("numel(stf)", nargout=1)
            num_beams_int = int(num_beams)
            total_bixels = self.eng.eval("sum([stf.totalNumOfBixels])", nargout=1)
            
            # Get individual beam details
            beam_info = []
            for i in range(1, num_beams_int + 1):
                gantry = self.eng.eval(f"stf({i}).gantryAngle", nargout=1)
                couch = self.eng.eval(f"stf({i}).couchAngle", nargout=1)
                bixels = self.eng.eval(f"stf({i}).totalNumOfBixels", nargout=1)
                beam_info.append({
                    "beam_id": i,
                    "gantry_angle": gantry,
                    "couch_angle": couch,
                    "num_bixels": bixels
                })
            
            return {
                "success": True,
                "num_beams": len(gantry_angles),
                "gantry_angles": gantry_angles,
                "couch_angles": couch_angles,
                "num_beams": num_beams_int,
                "total_bixels": total_bixels,
                "beam_info": beam_info,
                "weights_cleared": True,
                "message": "Beam angles and beam geometry set successfully. Previous optimization weights cleared."
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def set_optimizer(self, optimizer_type: str = 'fmincon', max_iterations: int = 100) -> Dict[str, Any]:
        """
        Set the optimizer for the treatment plan.
        
        Args:
            optimizer_type: Type of optimizer ('fmincon' or 'IPOPT').
            max_iterations: Maximum number of iterations.
            
        Returns:
            Dict with optimizer information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.pln is None:
            return {"success": False, "error": "No treatment plan created. Call create_empty_plan first."}
            
        try:
            # First set global config max iterations - this is used by all optimizers
            self.eng.eval(f"matRad_cfg = MatRad_Config.instance(); matRad_cfg.defaults.propOpt.maxIter = {max_iterations};", nargout=0)                    
            # Update plan in class
            self.pln = self.eng.workspace["pln"]
            
            # Get optimizer info
            current_optimizer = self.eng.eval("pln.propOpt.optimizer", nargout=1)
            
            return {
                "success": True,
                "optimizer": current_optimizer,
                "max_iterations": max_iterations,
                "message": f"Optimizer set to {current_optimizer}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def generate_beam_geometry(self) -> Dict[str, Any]:
        """
        Generate the beam geometry (stf) based on the current plan.
        
        Returns:
            Dict with beam geometry information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.pln is None:
            return {"success": False, "error": "No treatment plan created. Call create_empty_plan first."}
            
        try:
            # Generate beam geometry
            print("Generating beam geometry...")
            self.eng.eval("stf = matRad_generateStf(ct,cst,pln);", nargout=0)
            
            # Instead of trying to get the entire stf struct, just keep track that it exists
            # self.stf = self.eng.workspace["stf"]  
            self.stf = True  # Just mark that stf exists in MATLAB workspace
            
            # Get beam info
            num_beams = self.eng.eval("numel(stf)", nargout=1)
            num_beams_int = int(num_beams)
            total_bixels = self.eng.eval("sum([stf.totalNumOfBixels])", nargout=1)
            
            # Get individual beam details
            beam_info = []
            for i in range(1, num_beams_int + 1):
                gantry = self.eng.eval(f"stf({i}).gantryAngle", nargout=1)
                couch = self.eng.eval(f"stf({i}).couchAngle", nargout=1)
                bixels = self.eng.eval(f"stf({i}).totalNumOfBixels", nargout=1)
                beam_info.append({
                    "beam_id": i,
                    "gantry_angle": gantry,
                    "couch_angle": couch,
                    "num_bixels": bixels
                })
            
            return {
                "success": True,
                "num_beams": num_beams_int,
                "total_bixels": total_bixels,
                "beam_info": beam_info,
                "message": "Beam geometry generated successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_influence_matrix(self) -> Dict[str, Any]:
        """
        Calculate the dose influence matrix.
        
        Returns:
            Dict with influence matrix information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.pln is None:
            return {"success": False, "error": "No treatment plan created. Call create_empty_plan first."}
            
        if self.stf is None:
            return {"success": False, "error": "No beam geometry created. Call generate_beam_geometry first."}
            
        try:
            import numpy as np

            # Check gantry and couch angles for all beams
            num_beams = int(self.eng.eval("numel(stf)", nargout=1))
            gantry_angles = []
            couch_angles = []
            for i in range(1, num_beams + 1):
                gantry = float(self.eng.eval(f"stf({i}).gantryAngle", nargout=1))
                couch = float(self.eng.eval(f"stf({i}).couchAngle", nargout=1))
                gantry_angles.append(gantry)
                couch_angles.append(couch)

            # Utility: check if all couch angles are zero & gantry equidistant
            all_couch_zero = all(np.isclose(c, 0.0) for c in couch_angles)
            if all_couch_zero and num_beams > 1:
                # Calculate differences between sorted angles modulo 360
                sorted_gantry = sorted([g % 360 for g in gantry_angles])
                diffs = [(sorted_gantry[(i+1)%num_beams] - sorted_gantry[i]) % 360 for i in range(num_beams)]
                uniform_step = np.round(np.mean(diffs), 2)
                is_equidistant = False #all(np.isclose(d, uniform_step, atol=1e-3) for d in diffs)

                if is_equidistant:
                    # Construct file name
                    step_int = int(round(uniform_step))
                    dij_name = f"dij_{num_beams}_{step_int}.mat"
                    import os
                    if os.path.exists(dij_name):
                        print(f"Loading precomputed dose-influence matrix from '{dij_name}'...")
                        self.eng.eval(f"load('{dij_name}', 'dij');", nargout=0)
                        calc_time = 0
                    else:
                        print(f"Calculating dose influence matrix (equidistant gantry, will save as '{dij_name}') ...")
                        start_time = time.time()
                        self.eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
                        calc_time = time.time() - start_time
                        print(f"Saving dose-influence matrix as '{dij_name}'...")
                        self.eng.eval(f"save('{dij_name}', 'dij', '-v7.3')", nargout=0)
                else:
                    # Not equidistant, compute and save as default
                    print("Calculating dose influence matrix (non-uniform gantry/couch)...")
                    start_time = time.time()
                    self.eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
                    calc_time = time.time() - start_time
                    self.eng.eval("save('dij.mat', 'dij', '-v7.3')", nargout=0)
            else:
                # Not all couch angles zero, compute and save as default
                print("Calculating dose influence matrix (may take some time)...")
                start_time = time.time()
                self.eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
                calc_time = time.time() - start_time
                self.eng.eval("save('dij.mat', 'dij', '-v7.3')", nargout=0)
            
            # Instead of trying to get the entire dij struct, just keep track that it exists
            # self.dij = self.eng.workspace["dij"]
            self.dij = True  # Just mark that dij exists in MATLAB workspace
            
            # Get matrix info
            dij_dimensions = self.eng.eval("size(dij.physicalDose{1})", nargout=1)
            num_voxels = self.eng.eval("numel(dij.doseGrid.x) * numel(dij.doseGrid.y) * numel(dij.doseGrid.z)", nargout=1)
            
            return {
                "success": True,
                "dimensions": list(dij_dimensions),
                "num_voxels": num_voxels,
                "calc_time_sec": calc_time,
                "message": "Dose influence matrix calculated successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_current_objectives(self) -> Dict[str, Any]:
        """
        Get all current optimization objectives for all structures.
        
        Returns:
            Dict with current objectives information organized by structure.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Get total number of structures
            num_structures = int(self.eng.eval("size(cst,1)", nargout=1))
            
            objectives_dict = {}
            total_count = 0
            
            # Loop through each structure
            for i in range(1, num_structures + 1):  # MATLAB 1-based indexing
                # Check if structure has a name
                has_name = self.eng.eval(f"~isempty(cst{{{i},2}})", nargout=1)
                if not has_name:
                    continue
                    
                # Get structure name
                struct_name = str(self.eng.eval(f"cst{{{i},2}}", nargout=1))
                
                # Check if structure has objectives
                has_objectives = self.eng.eval(f"~isempty(cst{{{i},6}})", nargout=1)
                if not has_objectives:
                    continue
                    
                # Get number of objectives for this structure
                num_objectives = int(self.eng.eval(f"length(cst{{{i},6}})", nargout=1))
                
                struct_objectives = []
                
                # Loop through each objective/constraint for this structure
                for j in range(1, num_objectives + 1):  # MATLAB 1-based indexing
                    try:
                        # Get className
                        class_name = str(self.eng.eval(f"cst{{{i},6}}{{{j}}}.className", nargout=1))
                        
                        # Check if this is an objective (has penalty) or constraint (no penalty)
                        is_objective = self.eng.eval(f"isfield(cst{{{i},6}}{{{j}}}, 'penalty')", nargout=1)
                        
                        if not is_objective:
                            # Skip constraints - they will be handled by get_current_constraints
                            continue
                            
                        # Get penalty (only objectives have this field)
                        penalty = float(self.eng.eval(f"cst{{{i},6}}{{{j}}}.penalty", nargout=1))
                        
                        # Get dose value (parameters)
                        dose_value = None
                        try:
                            # Try to get the first parameter (dose value)
                            has_params = self.eng.eval(f"isfield(cst{{{i},6}}{{{j}}}, 'parameters') && ~isempty(cst{{{i},6}}{{{j}}}.parameters)", nargout=1)
                            if has_params:
                                # Check if parameters is a cell array
                                is_cell = self.eng.eval(f"iscell(cst{{{i},6}}{{{j}}}.parameters)", nargout=1)
                                if is_cell:
                                    dose_value = float(self.eng.eval(f"cst{{{i},6}}{{{j}}}.parameters{{1}}", nargout=1))
                                else:
                                    dose_value = float(self.eng.eval(f"cst{{{i},6}}{{{j}}}.parameters(1)", nargout=1))
                        except:
                            dose_value = None
                        
                        # Map className to readable type
                        objective_type_map = {
                            'DoseObjectives.matRad_SquaredUnderdosing': 'min_dose',
                            'DoseObjectives.matRad_SquaredOverdosing': 'max_dose',
                            'DoseObjectives.matRad_QuarticOverdosing': 'quartic_overdosing',
                            'DoseObjectives.matRad_MeanDose': 'mean_dose',
                            'DoseObjectives.matRad_SquaredDeviation': 'square_deviation',
                            'DoseObjectives.matRad_EUD': 'eud',
                            'DoseObjectives.matRad_MinDVH': 'min_dvh',
                            'DoseObjectives.matRad_MaxDVH': 'max_dvh'
                        }
                        objective_type = objective_type_map.get(class_name, 'unknown')
                        
                        objective_info = {
                            "structure_index": i,
                            "objective_index": j,
                            "objective_type": objective_type,
                            "dose_value": dose_value,
                            "penalty": penalty,
                            "className": class_name
                        }
                        
                        struct_objectives.append(objective_info)
                        total_count += 1
                        
                    except Exception as e:
                        print(f"Warning: Could not read objective {j} for structure {struct_name}: {e}")
                        continue
                
                if struct_objectives:
                    objectives_dict[struct_name] = struct_objectives
            
            return {
                "success": True,
                "objectives_by_structure": objectives_dict,
                "total_objectives": total_count,
                "message": f"Found {total_count} objectives across {len(objectives_dict)} structures"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_optimization_objective(self, structure_name: str, objective_index: int = None, 
                                    objective_type: str = None, dose_value: float = None,
                                    rationale: str = None) -> Dict[str, Any]:
        """
        Remove a specific optimization objective from a structure.
        
        Args:
            structure_name: Name of the structure
            objective_index: Specific index of objective to remove (1-based, optional)
            objective_type: Type of objective to remove (optional, removes first match)
            dose_value: Dose value to match for removal (optional, for additional specificity)
            rationale: Short explanation of why this objective is being removed.
            
        Returns:
            Dict with removal status and information.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Map objective types to matRad objective classes
            obj_class_map = {
                'min_dose': 'DoseObjectives.matRad_SquaredUnderdosing',
                'max_dose': 'DoseObjectives.matRad_SquaredOverdosing',
                'quartic_overdosing': 'DoseObjectives.matRad_QuarticOverdosing',
                'mean_dose': 'DoseObjectives.matRad_MeanDose',
                'square_deviation': 'DoseObjectives.matRad_SquaredDeviation',
                'eud': 'DoseObjectives.matRad_EUD',
                'min_dvh': 'DoseObjectives.matRad_MinDVH',
                'max_dvh': 'DoseObjectives.matRad_MaxDVH'
            }
            
            target_class = obj_class_map.get(objective_type) if objective_type else None
            
            # First, find structure index
            self.eng.eval(f"""
            struct_idx = 0;
            for i = 1:size(cst,1)
                if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                    struct_idx = i;
                    break;
                end
            end
            """, nargout=0)
            
            struct_idx = int(self.eng.workspace["struct_idx"])
            if struct_idx == 0:
                return {"success": False, "error": f"Structure '{structure_name}' not found"}
            
            # Remove objective based on criteria
            if objective_index is not None:
                # Remove by specific index
                self.eng.eval(f"""
                objectives = cst{{{struct_idx},6}};
                if length(objectives) >= {objective_index}
                    removed_obj = objectives{{{objective_index}}};
                    objectives({objective_index}) = [];
                    cst{{{struct_idx},6}} = objectives;
                    removal_success = true;
                    remaining_count = length(objectives);
                else
                    removal_success = false;
                    remaining_count = length(objectives);
                end
                """, nargout=0)
            else:
                # Remove by type and/or dose value
                dose_condition = f"&& abs(obj.parameters{{1}} - {dose_value}) < 1e-6" if dose_value is not None else ""
                class_condition = f"&& strcmp(obj.className, '{target_class}')" if target_class else ""
                
                self.eng.eval(f"""
                objectives = cst{{{struct_idx},6}};
                removal_success = false;
                removed_idx = 0;
                
                for j = 1:length(objectives)
                    obj = objectives{{j}};
                    if true {class_condition} {dose_condition}
                        removed_obj = obj;
                        objectives(j) = [];
                        removal_success = true;
                        removed_idx = j;
                        break;
                    end
                end
                
                cst{{{struct_idx},6}} = objectives;
                remaining_count = length(objectives);
                """, nargout=0)
            
            removal_success = bool(self.eng.workspace["removal_success"])
            remaining_count = int(self.eng.workspace["remaining_count"])
            
            if removal_success:
                return {
                    "success": True,
                    "structure": structure_name,
                    "remaining_objectives": remaining_count,
                    "rationale": rationale or "No rationale provided",
                    "message": f"Removed objective from {structure_name}. {remaining_count} objectives remaining. Rationale: {rationale or 'No rationale provided'}"
                }
            else:
                return {
                    "success": False, 
                    "error": f"No matching objective found for removal in {structure_name}",
                    "rationale": rationale or "No rationale provided"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_all_objectives(self, structure_name: str = None) -> Dict[str, Any]:
        """
        Clear all optimization objectives for a structure or all structures.
        
        Args:
            structure_name: Name of specific structure to clear (optional, clears all if None)
            
        Returns:
            Dict with clearing status and information.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            if structure_name:
                # Clear objectives for specific structure
                self.eng.eval(f"""
                struct_idx = 0;
                for i = 1:size(cst,1)
                    if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                        struct_idx = i;
                        break;
                    end
                end
                
                if struct_idx > 0
                    cst{{struct_idx,6}} = {{}};
                    cleared_success = true;
                else
                    cleared_success = false;
                end
                """, nargout=0)
                
                cleared_success = bool(self.eng.workspace["cleared_success"])
                if cleared_success:
                    return {
                        "success": True,
                        "structure": structure_name,
                        "message": f"Cleared all objectives for {structure_name}"
                    }
                else:
                    return {"success": False, "error": f"Structure '{structure_name}' not found"}
            else:
                # Clear all objectives for all structures
                self.eng.eval("""
                cleared_count = 0;
                for i = 1:size(cst,1)
                    if ~isempty(cst{i,6})
                        cleared_count = cleared_count + length(cst{i,6});
                        cst{i,6} = {};
                    end
                end
                """, nargout=0)
                
                cleared_count = int(self.eng.workspace["cleared_count"])
                return {
                    "success": True,
                    "cleared_objectives": cleared_count,
                    "message": f"Cleared all {cleared_count} objectives from all structures"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_constraint(self, structure_name: str, constraint_type: str,
                      lower_bound: float = None, upper_bound: float = None,
                      dose_reference: float = None, eud_exponent: float = 3.5,
                      rationale: str = None) -> Dict[str, Any]:
        """
        Add an optimization constraint for a structure.
        
        Args:
            structure_name: Name of the structure to add constraint for.
            constraint_type: Type of constraint ('min_max_dose', 'min_max_mean_dose', 'min_max_eud', 'min_max_dvh')
            lower_bound: Lower bound value (optional).
            upper_bound: Upper bound value (optional).
            dose_reference: Reference dose for DVH constraints in Gy.
            eud_exponent: EUD exponent parameter (default 3.5).
            rationale: Short explanation of why this constraint is being added.
            
        Returns:
            Dict with constraint information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Map constraint types to matRad constraint classes
            constraint_class_map = {
                'min_max_dose': 'DoseConstraints.matRad_MinMaxDose',
                'min_max_mean_dose': 'DoseConstraints.matRad_MinMaxMeanDose',
                'min_max_eud': 'DoseConstraints.matRad_MinMaxEUD',
                'min_max_dvh': 'DoseConstraints.matRad_MinMaxDVH'
            }
            
            if constraint_type not in constraint_class_map:
                return {"success": False, "error": f"Unsupported constraint type: {constraint_type}. Supported types: {list(constraint_class_map.keys())}"}
                
            constraint_class = constraint_class_map[constraint_type]
            
            # First, find structure index
            self.eng.eval(f"""
            struct_idx = 0;
            for i = 1:size(cst,1)
                if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                    struct_idx = i;
                    break;
                end
            end
            """, nargout=0)
            
            struct_idx = int(self.eng.workspace["struct_idx"])
            if struct_idx == 0:
                return {"success": False, "error": f"Structure '{structure_name}' not found"}
            
            # Create the constraint struct in MATLAB with appropriate parameters
            if constraint_type == 'min_max_dose':
                # MinMaxDose: parameters = {min_dose, max_dose, method}
                min_dose = lower_bound if lower_bound is not None else 0
                max_dose = upper_bound if upper_bound is not None else float('inf')
                self.eng.eval(f"""
                % Create new MinMaxDose constraint
                newConstraint = struct();
                newConstraint.className = '{constraint_class}';
                newConstraint.parameters = {{{min_dose}, {max_dose}, 1}};  % method = 1 (approx)
                """, nargout=0)
                
            elif constraint_type == 'min_max_mean_dose':
                # MinMaxMeanDose: parameters = {min_mean, max_mean}
                min_mean = lower_bound if lower_bound is not None else 0
                max_mean = upper_bound if upper_bound is not None else float('inf')
                self.eng.eval(f"""
                % Create new MinMaxMeanDose constraint
                newConstraint = struct();
                newConstraint.className = '{constraint_class}';
                newConstraint.parameters = {{{min_mean}, {max_mean}}};
                """, nargout=0)
                
            elif constraint_type == 'min_max_eud':
                # MinMaxEUD: parameters = {exponent, min_eud, max_eud}
                min_eud = lower_bound if lower_bound is not None else 0
                max_eud = upper_bound if upper_bound is not None else float('inf')
                self.eng.eval(f"""
                % Create new MinMaxEUD constraint
                newConstraint = struct();
                newConstraint.className = '{constraint_class}';
                newConstraint.parameters = {{{eud_exponent}, {min_eud}, {max_eud}}};
                """, nargout=0)
                
            elif constraint_type == 'min_max_dvh':
                # MinMaxDVH: parameters = {dose_ref, vol_min, vol_max}
                if dose_reference is None:
                    return {"success": False, "error": "dose_reference is required for min_max_dvh constraint"}
                vol_min = lower_bound if lower_bound is not None else 0
                vol_max = upper_bound if upper_bound is not None else 100
                # Convert volume fractions to percentages for matRad
                vol_min_pct = vol_min * 100 if vol_min <= 1.0 else vol_min
                vol_max_pct = vol_max * 100 if vol_max <= 1.0 else vol_max
                self.eng.eval(f"""
                % Create new MinMaxDVH constraint
                newConstraint = struct();
                newConstraint.className = '{constraint_class}';
                newConstraint.parameters = {{{dose_reference}, {vol_min_pct}, {vol_max_pct}}};
                """, nargout=0)
            
            # Check if constraints field exists for this structure
            has_constraints = self.eng.eval(f"~isempty(cst({int(struct_idx)},6))", nargout=1)
            
            if not has_constraints:
                # Initialize empty cell array if no objectives/constraints exist
                self.eng.eval(f"cst({int(struct_idx)},6) = {{}};", nargout=0)
            
            # Add the constraint to the structure
            self.eng.eval(f"""
            % Get current objectives/constraints
            currentObjConstraints = cst{{{int(struct_idx)},6}};
            % Add new constraint
            currentObjConstraints{{end+1}} = newConstraint;
            % Update CST
            cst{{{int(struct_idx)},6}} = currentObjConstraints;
            """, nargout=0)
            
            # Get the number of objectives/constraints
            num_obj_constraints = self.eng.eval(f"numel(cst({int(struct_idx)},6))", nargout=1)
            
            return {
                "success": True,
                "structure": structure_name,
                "constraint_type": constraint_type,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "dose_reference": dose_reference,
                "eud_exponent": eud_exponent if constraint_type == 'min_max_eud' else None,
                "rationale": rationale or "No rationale provided",
                "total_obj_constraints": num_obj_constraints,
                "message": f"Added {constraint_type} constraint to {structure_name}. Rationale: {rationale or 'No rationale provided'}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_constraint(self, structure_name: str, constraint_index: int = None,
                         constraint_type: str = None, rationale: str = None) -> Dict[str, Any]:
        """
        Remove a specific optimization constraint from a structure.
        
        Args:
            structure_name: Name of the structure
            constraint_index: Specific index of constraint to remove (1-based, optional)
            constraint_type: Type of constraint to remove (optional, removes first match)
            rationale: Short explanation of why this constraint is being removed.
            
        Returns:
            Dict with removal status and information.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Map constraint types to matRad constraint classes
            constraint_class_map = {
                'min_max_dose': 'DoseConstraints.matRad_MinMaxDose',
                'min_max_mean_dose': 'DoseConstraints.matRad_MinMaxMeanDose',
                'min_max_eud': 'DoseConstraints.matRad_MinMaxEUD',
                'min_max_dvh': 'DoseConstraints.matRad_MinMaxDVH'
            }
            
            target_class = constraint_class_map.get(constraint_type) if constraint_type else None
            
            # First, find structure index
            self.eng.eval(f"""
            struct_idx = 0;
            for i = 1:size(cst,1)
                if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                    struct_idx = i;
                    break;
                end
            end
            """, nargout=0)
            
            struct_idx = int(self.eng.workspace["struct_idx"])
            if struct_idx == 0:
                return {"success": False, "error": f"Structure '{structure_name}' not found"}
            
            # Remove constraint based on criteria
            if constraint_index is not None:
                # Remove by specific index
                self.eng.eval(f"""
                objConstraints = cst{{{struct_idx},6}};
                if length(objConstraints) >= {constraint_index}
                    removed_item = objConstraints{{{constraint_index}}};
                    objConstraints({constraint_index}) = [];
                    cst{{{struct_idx},6}} = objConstraints;
                    removal_success = true;
                    remaining_count = length(objConstraints);
                else
                    removal_success = false;
                    remaining_count = length(objConstraints);
                end
                """, nargout=0)
            else:
                # Remove by type (first match)
                class_condition = f"&& strcmp(item.className, '{target_class}')" if target_class else ""
                
                self.eng.eval(f"""
                objConstraints = cst{{{struct_idx},6}};
                removal_success = false;
                removed_idx = 0;
                
                for j = 1:length(objConstraints)
                    item = objConstraints{{j}};
                    % Check if it's a constraint (has no penalty field) and matches type
                    if ~isfield(item, 'penalty') {class_condition}
                        removed_item = item;
                        objConstraints(j) = [];
                        removal_success = true;
                        removed_idx = j;
                        break;
                    end
                end
                
                cst{{{struct_idx},6}} = objConstraints;
                remaining_count = length(objConstraints);
                """, nargout=0)
            
            removal_success = bool(self.eng.workspace["removal_success"])
            remaining_count = int(self.eng.workspace["remaining_count"])
            
            if removal_success:
                return {
                    "success": True,
                    "structure": structure_name,
                    "remaining_obj_constraints": remaining_count,
                    "rationale": rationale or "No rationale provided",
                    "message": f"Removed constraint from {structure_name}. {remaining_count} items remaining. Rationale: {rationale or 'No rationale provided'}"
                }
            else:
                return {
                    "success": False, 
                    "error": f"No matching constraint found for removal in {structure_name}",
                    "rationale": rationale or "No rationale provided"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_current_constraints(self) -> Dict[str, Any]:
        """
        Get all current optimization constraints for all structures.
        
        Returns:
            Dict with current constraints information organized by structure.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Get total number of structures
            num_structures = int(self.eng.eval("size(cst,1)", nargout=1))
            
            constraints_dict = {}
            total_count = 0
            
            # Loop through each structure
            for i in range(1, num_structures + 1):  # MATLAB 1-based indexing
                # Check if structure has a name
                has_name = self.eng.eval(f"~isempty(cst{{{i},2}})", nargout=1)
                if not has_name:
                    continue
                    
                # Get structure name
                struct_name = str(self.eng.eval(f"cst{{{i},2}}", nargout=1))
                
                # Check if structure has objectives/constraints
                has_obj_constraints = self.eng.eval(f"~isempty(cst{{{i},6}})", nargout=1)
                if not has_obj_constraints:
                    continue
                    
                # Get number of objectives/constraints for this structure
                num_obj_constraints = int(self.eng.eval(f"length(cst{{{i},6}})", nargout=1))
                
                struct_constraints = []
                
                # Loop through each objective/constraint for this structure
                for j in range(1, num_obj_constraints + 1):  # MATLAB 1-based indexing
                    try:
                        # Get className
                        class_name = str(self.eng.eval(f"cst{{{i},6}}{{{j}}}.className", nargout=1))
                        
                        # Check if it's a constraint (no penalty field)
                        has_penalty = self.eng.eval(f"isfield(cst{{{i},6}}{{{j}}}, 'penalty')", nargout=1)
                        if has_penalty:
                            continue  # Skip objectives
                        
                        # Get parameters
                        parameters = []
                        try:
                            has_params = self.eng.eval(f"isfield(cst{{{i},6}}{{{j}}}, 'parameters') && ~isempty(cst{{{i},6}}{{{j}}}.parameters)", nargout=1)
                            if has_params:
                                # Get number of parameters
                                num_params = int(self.eng.eval(f"length(cst{{{i},6}}{{{j}}}.parameters)", nargout=1))
                                for k in range(1, num_params + 1):
                                    # Check if parameters is a cell array
                                    is_cell = self.eng.eval(f"iscell(cst{{{i},6}}{{{j}}}.parameters)", nargout=1)
                                    if is_cell:
                                        param_val = float(self.eng.eval(f"cst{{{i},6}}{{{j}}}.parameters{{{k}}}", nargout=1))
                                    else:
                                        param_val = float(self.eng.eval(f"cst{{{i},6}}{{{j}}}.parameters({k})", nargout=1))
                                    parameters.append(param_val)
                        except:
                            parameters = []
                        
                        # Map className to readable type
                        constraint_type_map = {
                            'DoseConstraints.matRad_MinMaxDose': 'min_max_dose',
                            'DoseConstraints.matRad_MinMaxMeanDose': 'min_max_mean_dose',
                            'DoseConstraints.matRad_MinMaxEUD': 'min_max_eud',
                            'DoseConstraints.matRad_MinMaxDVH': 'min_max_dvh'
                        }
                        constraint_type = constraint_type_map.get(class_name, 'unknown')
                        
                        constraint_info = {
                            "structure_index": i,
                            "constraint_index": j,
                            "constraint_type": constraint_type,
                            "parameters": parameters,
                            "className": class_name
                        }
                        
                        struct_constraints.append(constraint_info)
                        total_count += 1
                        
                    except Exception as e:
                        print(f"Warning: Could not read constraint {j} for structure {struct_name}: {e}")
                        continue
                
                if struct_constraints:
                    constraints_dict[struct_name] = struct_constraints
            
            return {
                "success": True,
                "constraints_by_structure": constraints_dict,
                "total_constraints": total_count,
                "message": f"Found {total_count} constraints across {len(constraints_dict)} structures"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_optimization_objective(self, structure_name: str, obj_type: str, 
                                  dose_value: float, penalty: float = 1000.0, 
                                  rationale: str = None, volume_percent: float = None,
                                  eud_exponent: float = None) -> Dict[str, Any]:
        """
        Add an optimization objective for a structure.
        
        Args:
            structure_name: Name of the structure to add objective for.
            obj_type: Type of objective ('square_underdosing', 'square_overdosing', 'quartic_overdosing', 'mean_dose', 'square_deviation', 'eud', 'min_dvh', 'max_dvh')
            dose_value: Dose value in Gy for the objective (for EUD: target EUD value; for DVH: dose threshold).
            penalty: Penalty weight for the objective.
            rationale: Short explanation of why this objective is being added.
            volume_percent: Volume percentage for DVH objectives (e.g., 95 for 95%). Only used for min_dvh and max_dvh.
            eud_exponent: EUD exponent parameter (default 3.5). Only used for eud objective.
            
        Returns:
            Dict with objective information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Map objective types to matRad objective classes
            obj_class_map = {
                'square_underdosing': 'DoseObjectives.matRad_SquaredUnderdosing',
                'square_overdosing': 'DoseObjectives.matRad_SquaredOverdosing',
                'quartic_overdosing': 'DoseObjectives.matRad_QuarticOverdosing',
                'mean_dose': 'DoseObjectives.matRad_MeanDose',
                'square_deviation': 'DoseObjectives.matRad_SquaredDeviation',
                'eud': 'DoseObjectives.matRad_EUD',
                'min_dvh': 'DoseObjectives.matRad_MinDVH',
                'max_dvh': 'DoseObjectives.matRad_MaxDVH'
            }
            
            if obj_type not in obj_class_map:
                return {"success": False, "error": f"Unsupported objective type: {obj_type}. Supported types: {list(obj_class_map.keys())}"}
                
            obj_class = obj_class_map[obj_type]
            
            # First, find structure index (do this in one step)
            # Get all structure names from CST
            all_struct_names = self.eng.eval("""
            structNames = {};
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2})
                    structNames{end+1} = cst{i,2};
                end
            end            
            """, nargout=0)

            all_struct_names = self.eng.workspace["structNames"]
            
            # Convert to list of strings
            struct_names_list = [str(name) for name in all_struct_names]
            
            # Find the index of the target structure
            if structure_name not in struct_names_list:
                return {"success": False, "error": f"Structure '{structure_name}' not found in CST"}
            
            # Get all indices of rows in CST
            self.eng.eval("""
            indices = [];
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2})
                    indices(end+1) = i;
                end
            end
            """, nargout=0)
            
            # Access the indices variable from MATLAB workspace
            cst_indices = self.eng.workspace["indices"]
            cst_indices = np.array(cst_indices).flatten()
            
            # Find the corresponding index in CST
            struct_idx = cst_indices[struct_names_list.index(structure_name)]
            
            # Create the objective struct in MATLAB with appropriate parameters
            if obj_type == 'eud':
                # EUD objective: parameters = {dose_value, exponent}
                eud_exp = eud_exponent if eud_exponent is not None else 3.5
                self.eng.eval(f"""
                % Create new EUD objective
                newObj = struct();
                newObj.className = '{obj_class}';
                newObj.parameters = {{{dose_value}, {eud_exp}}};
                newObj.penalty = {penalty};
                """, nargout=0)
            elif obj_type in ['min_dvh', 'max_dvh']:
                # DVH objective: parameters = {dose_value, volume_percent}
                vol_pct = volume_percent if volume_percent is not None else 95.0
                self.eng.eval(f"""
                % Create new DVH objective
                newObj = struct();
                newObj.className = '{obj_class}';
                newObj.parameters = {{{dose_value}, {vol_pct}}};
                newObj.penalty = {penalty};
                """, nargout=0)
            else:
                # Standard objectives: parameters = {dose_value}
                self.eng.eval(f"""
                % Create new objective
                newObj = struct();
                newObj.className = '{obj_class}';
                newObj.parameters = {{{dose_value}}};
                newObj.penalty = {penalty};
                """, nargout=0)
            
            # Check if objectives field exists for this structure
            has_objectives = self.eng.eval(f"~isempty(cst({int(struct_idx)},6))", nargout=1)
            
            if not has_objectives:
                # Initialize empty cell array if no objectives exist
                self.eng.eval(f"cst({int(struct_idx)},6) = {{}};", nargout=0)
            
            # Add the objective to the structure
            self.eng.eval(f"""
            % Get current objectives
            currentObj = cst{{{int(struct_idx)},6}};
            % Add new objective
            currentObj{{end+1}} = newObj;
            % Update CST
            cst{{{int(struct_idx)},6}} = currentObj;
            """, nargout=0)
            
            # Get the number of objectives
            num_objectives = self.eng.eval(f"numel(cst({int(struct_idx)},6))", nargout=1)
            
            return {
                "success": True,
                "structure": structure_name,
                "objective_type": obj_type,
                "dose_value": dose_value,
                "penalty": penalty,
                "rationale": rationale or "No rationale provided",
                "total_objectives": num_objectives,
                "message": f"Added {obj_type} objective to {structure_name}."
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def optimize_fluence(self, use_previous_weights: bool = False) -> Dict[str, Any]:
        """
        Run fluence optimization with detailed monitoring and console output capture.
        
        Args:
            use_previous_weights: If True and previous weights are available, 
                                use them as initial weights for warm-start optimization.
        
        Returns:
            Dict with optimization results, convergence analysis, and console output.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.pln is None:
            return {"success": False, "error": "No treatment plan created. Call create_empty_plan first."}
            
        if self.dij is None:
            return {"success": False, "error": "No influence matrix calculated. Call calculate_influence_matrix first."}
            
        try:
            # Determine optimization command based on whether to use previous weights
            if use_previous_weights and self.weights_available and self.optimized_weights is not None:
                print("Running fluence optimization with previous weights for warm-start...")
                optimization_cmd = "resultGUI = matRad_fluenceOptimization(dij,cst,pln);"
                start_type = "warm-start"
            else:
                print("Running fluence optimization from scratch...")
                optimization_cmd = "resultGUI = matRad_fluenceOptimization(dij,cst,pln);"
                start_type = "cold-start"
            
            # Set up diary to capture console output
            import tempfile
            temp_dir = tempfile.gettempdir()
            diary_file = os.path.join(temp_dir, f"matrad_opt_log_{int(time.time())}.txt")
            
            self.eng.eval(f"""
            % Start diary to capture optimization output
            diary('{diary_file}');
            diary on;
            
            % Store start time
            opt_start_time = tic;
            
            fprintf('\\n=== OPTIMIZATION STARTING ===\\n');
            fprintf('Start type: {start_type}\\n');
            fprintf('==============================\\n\\n');
            """, nargout=0)
            
            try:
                # Run optimization with output capture
                start_time = time.time()
                self.eng.eval(f"""
                try
                    fprintf('Optimzation initiating...\\n');
                    {optimization_cmd}
                    opt_success = true;
                    opt_error = '';                    
                    save(['resultGUIs/resultGUI_' datestr(now,'yyyymmdd_HHMM') '.mat'], 'resultGUI', 'ct', 'cst', 'pln', 'stf', '-v7.3');
                    fprintf('Optimization successful: resultGUI saved to resultGUIs/resultGUI_%s.mat\\n', datestr(now,'yyyymmdd_HHMM'));
                catch ME
                    opt_success = false;
                    opt_error = getReport(ME, 'extended');
                    fprintf('Optimization failed: %s\\n', ME.message);
                end
                
                opt_duration = toc(opt_start_time);
                fprintf('\\n=== OPTIMIZATION COMPLETED ===\\n');
                fprintf('Duration: %.2f seconds\\n', opt_duration);
                fprintf('Success: %s\\n', mat2str(opt_success));
                fprintf('===============================\\n');
                
                % Stop diary
                diary off;
                """, nargout=0)
                
                opt_time = time.time() - start_time
                
                # Check if optimization was successful
                opt_success = bool(self.eng.workspace["opt_success"])
                
                if not opt_success:
                    opt_error = str(self.eng.workspace["opt_error"])
                    
                    # Read and parse the diary output even for failed optimization
                    optimization_analysis = self._parse_optimization_output(diary_file)
                    
                    # Clean up diary file
                    try:
                        os.remove(diary_file)
                    except:
                        pass
                    
                    return {
                        "success": False, 
                        "error": f"Optimization failed: {opt_error}",
                        "optimization_time_sec": opt_time,
                        "start_type": start_type,
                        "optimization_analysis": optimization_analysis
                    }
                
                # Mark that resultGUI exists in MATLAB workspace
                self.resultGUI = True
                
                # Verify optimization completed
                has_result = self.eng.eval("exist('resultGUI', 'var')", nargout=1)
                if has_result != 1:
                    return {"success": False, "error": "Optimization failed to produce results"}
                
                # Store the optimized weights for future use
                try:
                    # Extract optimized weights from resultGUI.w
                    self.eng.workspace['wInit'] = self.eng.eval("resultGUI.w", nargout=1)
                    # Convert from MATLAB array to numpy array
                    self.optimized_weights = self.eng.workspace['wInit']
                    self.weights_available = True
                    weights_stored = True
                    weights_count = len(self.optimized_weights)
                    print(f"Stored {weights_count} optimized weights for future warm-start")
                except Exception as e:
                    print(f"Warning: Could not store optimized weights: {e}")
                    weights_stored = False
                    weights_count = 0
                
                # Read and parse the diary output
                optimization_analysis = self._parse_optimization_output(diary_file)
                
                # Clean up diary file
                try:
                    os.remove(diary_file)
                except:
                    pass
                
                return {
                    "success": True,
                    "optimization_time_sec": opt_time,
                    "start_type": start_type,
                    "weights_stored": weights_stored,
                    "weights_count": weights_count,
                    "optimization_analysis": optimization_analysis,
                    "message": f"Fluence optimization completed successfully ({start_type})"
                }
                
            except Exception as e:
                # Make sure diary is turned off
                try:
                    self.eng.eval("diary off;", nargout=0)
                except:
                    pass
                raise e
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_optimization_output(self, diary_file: str) -> Dict[str, Any]:
        """
        Parse the optimization console output to extract key metrics and convergence information.
        Supports both IPOPT and fmincon output formats.
        
        Args:
            diary_file: Path to the diary file containing optimization output
            
        Returns:
            Dict with parsed optimization metrics and analysis
        """
        try:
            with open(diary_file, 'r') as f:
                output = f.read()
            
            analysis = {
                "convergence_analysis": {},
                "final_status": {},
                "optimization_trajectory": [],
                "warnings": [],
                "summary": "",
                "optimizer_type": "unknown"
            }
            
            lines = output.split('\n')
            iterations = []
            
            # Detect optimizer type
            if any("fmincon" in line.lower() or "interior-point" in line for line in lines):
                analysis["optimizer_type"] = "fmincon"
                analysis = self._parse_fmincon_output(lines, analysis)
            elif any("ipopt" in line.lower() for line in lines):
                analysis["optimizer_type"] = "ipopt"
                analysis = self._parse_ipopt_output(lines, analysis)
            else:
                # Try to parse as generic format
                analysis = self._parse_generic_output(lines, analysis)
            
            # Analyze convergence if we have iterations
            if analysis["optimization_trajectory"]:
                analysis["convergence_analysis"] = self._analyze_convergence(analysis["optimization_trajectory"])
                del analysis["optimization_trajectory"]
            
            # Generate summary
            analysis["summary"] = self._generate_optimization_summary(analysis)
            
            return analysis
            
        except Exception as e:
            return {
                "raw_output": "",
                "convergence_analysis": {},
                "final_status": {},
                "optimization_trajectory": [],
                "warnings": [f"Failed to parse optimization output: {str(e)}"],
                "summary": f"Failed to parse optimization output: {str(e)}",
                "optimizer_type": "unknown"
            }

    def _parse_fmincon_output(self, lines: List[str], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse fmincon-specific output format."""
        iterations = []
        in_iteration_table = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for optimization settings
            if "Applied custom fmincon option:" in line:
                option_parts = line.split("Applied custom fmincon option:")[1].strip()
                if "=" in option_parts:
                    key, value = option_parts.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if "final_status" not in analysis:
                        analysis["final_status"] = {}
                    if "settings" not in analysis["final_status"]:
                        analysis["final_status"]["settings"] = {}
                    analysis["final_status"]["settings"][key] = value
            
            # Look for diagnostic information
            elif "Number of variables:" in line:
                try:
                    analysis["final_status"]["num_variables"] = int(line.split(":")[1].strip())
                except:
                    pass
            elif "Number of nonlinear inequality constraints:" in line:
                try:
                    analysis["final_status"]["nonlinear_ineq_constraints"] = int(line.split(":")[1].strip())
                except:
                    pass
            elif "Number of nonlinear equality constraints:" in line:
                try:
                    analysis["final_status"]["nonlinear_eq_constraints"] = int(line.split(":")[1].strip())
                except:
                    pass
            elif "Algorithm selected" in line and i+1 < len(lines):
                algorithm = lines[i+1].strip()
                analysis["final_status"]["algorithm"] = algorithm
            
            # Look for iteration table headers (multiple formats)
            elif ("Iter F-count" in line and "f(x)" in line and "Feasibility" in line) or \
                 ("Iter F-count" in line and "f(x)" in line and "optimality" in line) or \
                 (line_stripped.startswith("Iter") and "f(x)" in line):
                in_iteration_table = True
                continue
        
            # Parse iteration data
            elif in_iteration_table and line_stripped:
                # Check if this is still an iteration line
                parts = line_stripped.split()
                
                # Handle different iteration line formats
                if len(parts) >= 5 and parts[0].isdigit():
                    try:
                        iteration_data = {
                            "iteration": int(parts[0]),
                            "f_count": int(parts[1]),
                            "objective": float(parts[2]),
                            "feasibility": float(parts[3]),
                            "optimality": float(parts[4]),
                            "step_norm": float(parts[5]) if len(parts) > 5 else None
                        }
                        iterations.append(iteration_data)
                    except (ValueError, IndexError):
                        # If we can't parse as iteration data, we've probably left the table
                        if "Converged" in line or "stopped" in line or line_stripped == "":
                            in_iteration_table = False
                        continue
                elif len(parts) >= 3 and parts[0].isdigit():
                    # Handle shorter iteration lines (just iter, f-count, objective, ...)
                    try:
                        iteration_data = {
                            "iteration": int(parts[0]),
                            "f_count": int(parts[1]) if len(parts) > 1 else None,
                            "objective": float(parts[2]) if len(parts) > 2 else None,
                            "feasibility": float(parts[3]) if len(parts) > 3 else None,
                            "optimality": float(parts[4]) if len(parts) > 4 else None,
                            "step_norm": float(parts[5]) if len(parts) > 5 else None
                        }
                        iterations.append(iteration_data)
                    except (ValueError, IndexError):
                        continue
                else:
                    # Check if we've reached the end of iteration table
                    if "Converged" in line or "stopped" in line or line_stripped == "" or \
                       line_stripped.startswith("_") or "diagnostic" in line.lower():
                        in_iteration_table = False
            
            # Look for final convergence message
            elif "Converged to an infeasible point" in line:
                analysis["final_status"]["convergence_status"] = "infeasible"
                analysis["warnings"].append("Optimization converged to an infeasible point")
            elif "fmincon stopped because" in line:
                # Get the full stopping message
                stop_message = line.strip()
                # Also get the next few lines for complete message
                for j in range(i+1, min(i+4, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("Warning"):
                        stop_message += " " + lines[j].strip()
                    else:
                        break
                analysis["final_status"]["stop_reason"] = stop_message
            
            # Look for warnings
            elif line.startswith("Warning:"):
                analysis["warnings"].append(line.strip())
            
            # Look for duration and success status
            elif "Duration:" in line:
                try:
                    duration_str = line.split("Duration:")[1].strip()
                    duration_match = duration_str.split()[0]  # Get first number
                    analysis["final_status"]["duration_seconds"] = float(duration_match)
                except:
                    pass
            elif "Success:" in line:
                try:
                    success_str = line.split("Success:")[1].strip().lower()
                    analysis["final_status"]["success"] = success_str == "true"
                except:
                    pass
        
        analysis["optimization_trajectory"] = iterations
        
        # Set final objective and iterations from trajectory
        if iterations:
            analysis["final_status"]["final_objective"] = iterations[-1]["objective"]
            analysis["final_status"]["total_iterations"] = len(iterations)
            analysis["final_status"]["final_feasibility"] = iterations[-1]["feasibility"]
            analysis["final_status"]["final_optimality"] = iterations[-1]["optimality"]
        
        return analysis

    def _parse_ipopt_output(self, lines: List[str], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse IPOPT-specific output format."""
        iterations = []
        
        for line in lines:
            line = line.strip()
            
            # Look for iteration lines (IPOPT format)
            if line.startswith('Iter') and 'Feasibility' in line:
                # Header line - skip
                continue
            elif len(line.split()) >= 10 and line.split()[0].isdigit():
                # Iteration data line
                parts = line.split()
                try:
                    iteration_data = {
                        "iteration": int(parts[0]),
                        "objective": float(parts[1]),
                        "inf_pr": float(parts[2]),
                        "inf_du": float(parts[3]),
                        "lg_mu": float(parts[4]),
                        "norm_d": float(parts[5]),
                        "lg_rg": parts[6],
                        "alpha_du": float(parts[7]),
                        "alpha_pr": float(parts[8]),
                        "ls": int(parts[9]) if parts[9].isdigit() else 0
                    }
                    iterations.append(iteration_data)
                except (ValueError, IndexError):
                    continue
            
            # Look for final statistics
            elif "Number of Iterations" in line:
                try:
                    analysis["final_status"]["total_iterations"] = int(line.split(':')[1].strip())
                except:
                    pass
            elif "Objective" in line and "scaled" in line:
                try:
                    # Extract final objective value
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'e' in part and ('+' in part or '-' in part):
                            analysis["final_status"]["final_objective"] = float(part)
                            break
                except:
                    pass
            elif "Number of objective function evaluations" in line:
                try:
                    analysis["final_status"]["function_evaluations"] = int(line.split('=')[1].strip())
                except:
                    pass
            elif "Total CPU secs in IPOPT" in line:
                try:
                    analysis["final_status"]["ipopt_time"] = float(line.split('=')[1].strip())
                except:
                    pass
            elif "Total CPU secs in NLP function evaluations" in line:
                try:
                    analysis["final_status"]["function_eval_time"] = float(line.split('=')[1].strip())
                except:
                    pass
        
        analysis["optimization_trajectory"] = iterations
        return analysis

    def _parse_generic_output(self, lines: List[str], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse generic optimization output format."""
        # Try to extract basic information that might be present in any format
        iterations = []
        
        for line in lines:
            line = line.strip()
            
            # Look for any warning messages
            if line.startswith("Warning:"):
                analysis["warnings"].append(line)
            
            # Look for duration
            elif "Duration:" in line:
                try:
                    duration_str = line.split("Duration:")[1].strip()
                    duration_match = duration_str.split()[0]
                    analysis["final_status"]["duration_seconds"] = float(duration_match)
                except:
                    pass
        
        analysis["optimization_trajectory"] = iterations
        return analysis

    def _analyze_convergence(self, iterations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze the convergence behavior of the optimization.
        Handles both IPOPT and fmincon iteration formats.
        
        Args:
            iterations: List of iteration data dictionaries
            
        Returns:
            Dict with convergence analysis
        """
        if not iterations:
            return {}
        
        analysis = {}
        
        # Extract objective values (common to both formats)
        objectives = [it["objective"] for it in iterations]
        
        # Extract step sizes based on format
        step_sizes = []
        feasibility_vals = []
        optimality_vals = []
        
        # Determine format based on available keys
        if iterations[0].get("alpha_pr") is not None:
            # IPOPT format
            step_sizes = [it.get("alpha_pr", 0) for it in iterations]
            feasibility_vals = [it.get("inf_pr", 0) for it in iterations]
        elif iterations[0].get("step_norm") is not None:
            # fmincon format
            step_sizes = [it.get("step_norm", 0) for it in iterations if it.get("step_norm") is not None]
            feasibility_vals = [it.get("feasibility", 0) for it in iterations]
            optimality_vals = [it.get("optimality", 0) for it in iterations]
        
        # Check for stagnation (objective not changing)
        if len(objectives) >= 3:
            recent_objectives = objectives[-5:]  # Last 5 iterations
            obj_variance = float(np.var(recent_objectives)) if len(recent_objectives) > 1 else 0.0
            analysis["objective_stagnation"] = obj_variance < 1e-6
            analysis["objective_variance_recent"] = obj_variance
        
        # Check for diminishing step sizes
        if len(step_sizes) >= 3:
            recent_steps = step_sizes[-3:]
            analysis["small_step_sizes"] = all(step < 1e-10 for step in recent_steps if step is not None)
            valid_steps = [s for s in step_sizes if s is not None]
            if valid_steps:
                analysis["min_step_size"] = float(min(valid_steps))
                analysis["max_step_size"] = float(max(valid_steps))
        
        # Analyze feasibility progression
        if feasibility_vals:
            analysis["initial_feasibility"] = float(feasibility_vals[0])
            analysis["final_feasibility"] = float(feasibility_vals[-1])
            analysis["feasibility_improvement"] = float(feasibility_vals[0] - feasibility_vals[-1])
        
        # Analyze optimality progression (fmincon specific)
        if optimality_vals:
            analysis["initial_optimality"] = float(optimality_vals[0])
            analysis["final_optimality"] = float(optimality_vals[-1])
            analysis["optimality_improvement"] = float(optimality_vals[0] - optimality_vals[-1])
        
        # Overall convergence assessment
        analysis["total_iterations"] = len(iterations)
        analysis["objective_improvement"] = float(objectives[0] - objectives[-1]) if len(objectives) > 1 else 0
        analysis["relative_improvement"] = float(analysis["objective_improvement"] / objectives[0]) if objectives[0] != 0 else 0
        
        # Convergence quality assessment
        stagnation = analysis.get("objective_stagnation", False)
        small_steps = analysis.get("small_step_sizes", False)
        
        if stagnation and small_steps:
            analysis["convergence_quality"] = "poor"
            analysis["convergence_reason"] = "Optimization stagnated with very small step sizes"
        elif analysis["relative_improvement"] > 0.1:
            analysis["convergence_quality"] = "good"
            analysis["convergence_reason"] = "Significant objective improvement achieved"
        elif analysis["relative_improvement"] > 0.01:
            analysis["convergence_quality"] = "moderate"
            analysis["convergence_reason"] = "Moderate objective improvement achieved"
        else:
            analysis["convergence_quality"] = "poor"
            analysis["convergence_reason"] = "Limited objective improvement"
        
        return analysis

    def _generate_optimization_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the optimization results.
        
        Args:
            analysis: Full optimization analysis dictionary
            
        Returns:
            String summary of optimization performance
        """
        summary_lines = []
        
        convergence = analysis.get("convergence_analysis", {})
        final_status = analysis.get("final_status", {})
        
        # Basic statistics
        if final_status.get("total_iterations"):
            summary_lines.append(f"🔄 Completed {final_status['total_iterations']} iterations")
        
        if final_status.get("final_objective"):
            summary_lines.append(f"📊 Final objective value: {final_status['final_objective']:.2e}")
        
        # Convergence assessment
        if convergence.get("convergence_quality"):
            quality = convergence["convergence_quality"]
            reason = convergence.get("convergence_reason", "")
            emoji = {"good": "✅", "moderate": "⚠️", "poor": "❌"}.get(quality, "❓")
            summary_lines.append(f"{emoji} Convergence quality: {quality.upper()}")
            if reason:
                summary_lines.append(f"   Reason: {reason}")
        
        # Improvement metrics
        if convergence.get("relative_improvement") is not None:
            improvement = convergence["relative_improvement"] * 100
            summary_lines.append(f"📈 Objective improvement: {improvement:.1f}%")
        
        # Warning indicators
        if convergence.get("objective_stagnation"):
            summary_lines.append("⚠️  WARNING: Objective value stagnated in recent iterations")
        
        if convergence.get("small_step_sizes"):
            min_step = convergence.get("min_step_size", 0)
            summary_lines.append(f"⚠️  WARNING: Very small step sizes detected (min: {min_step:.2e})")
        
        # Performance metrics
        if final_status.get("function_evaluations"):
            summary_lines.append(f"🔢 Function evaluations: {final_status['function_evaluations']}")
        
        if final_status.get("ipopt_time"):
            summary_lines.append(f"⏱️  IPOPT time: {final_status['ipopt_time']:.1f}s")
        
        return "\n".join(summary_lines) if summary_lines else "No optimization summary available"
    
    def clear_optimized_weights(self) -> Dict[str, Any]:
        """
        Clear stored optimized weights. Useful when beam configuration changes significantly.
        
        Returns:
            Dict with operation status.
        """
        self.optimized_weights = None
        self.weights_available = False
        return {
            "success": True,
            "message": "Optimized weights cleared. Next optimization will use cold-start."
        }
    
    def run_sequencing(self) -> Dict[str, Any]:
        """
        Run MLC sequencing on the optimized fluence map.
        
        Returns:
            Dict with sequencing results or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.resultGUI is None:
            return {"success": False, "error": "No optimization results available. Call optimize_fluence first."}
            
        try:
            # Enable sequencing in plan
            self.eng.eval("pln.propSeq.runSequencing = true;", nargout=0)
            self.eng.eval("pln.propSeq.sequencer = 'SMLC';", nargout=0)
            self.eng.eval("pln.propSeq.numOfLevels = 5;", nargout=0)
            
            # Run sequencing
            print("Running sequencing...")
            start_time = time.time()
            self.eng.eval("resultGUI = matRad_sequencing(resultGUI,stf,dij,pln);", nargout=0)
            seq_time = time.time() - start_time
            
            # Check if apertureInfo exists
            has_aperture = self.eng.eval("isfield(resultGUI, 'apertureInfo')", nargout=1)
            
            if not has_aperture:
                return {
                    "success": False, 
                    "error": "Sequencing did not produce valid aperture information",
                    "sequencing_time_sec": seq_time
                }
                
            # Get sequencing results
            num_apertures = self.eng.eval("numel(resultGUI.apertureInfo.aperture)", nargout=1)
            
            return {
                "success": True,
                "num_apertures": num_apertures,
                "sequencing_time_sec": seq_time,
                "message": "Sequencing completed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_dvh(self, structure_name: Optional[str] = None) -> Dict[str, Any]:
        """
        **SPECIALIZED TOOL FOR FOCUSED DVH ANALYSIS**
        
        Calculate DVH (Dose-Volume Histogram) for specific structure analysis using matRad's quality indicators.
        Creates detailed DVH plots and structure-specific clinical assessments.
        
        **USE THIS FOR:**
        - Focused analysis of a specific structure's dose distribution
        - Detailed DVH curve examination for individual structures
        - Structure-specific quality indicator deep-dive
        - When you need detailed DVH plots for specific structures
        - Follow-up analysis after comprehensive plan evaluation
        
        **NOTE:** For overall plan evaluation, use evaluate_plan() instead.
        
        Args:
            structure_name: Name of the structure to calculate DVH for. If None, calculates for all structures.
            
        Returns:
            Dict with detailed DVH analysis and structure-specific clinical assessment.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.resultGUI is None:
            return {"success": False, "error": "No optimization results available. Call optimize_fluence first."}
            
        try:
            # Check if resultGUI has a physicalDose field
            has_dose = self.eng.eval("isfield(resultGUI, 'physicalDose')", nargout=1)
            if not has_dose:
                return {"success": False, "error": "No dose information available in result"}
            
            if structure_name:
                return self._calculate_single_structure_dvh(structure_name)
            else:
                return self._calculate_all_structures_dvh()
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_single_structure_dvh(self, structure_name: str) -> Dict[str, Any]:
        """Calculate DVH for a single structure with detailed assessment."""
        
        # Find the structure index
        self.eng.eval(f"""
        structIdx = 0;
        for i = 1:size(cst,1)
            if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                structIdx = i;
                break;
            end
        end
        """, nargout=0)
        
        # Access the structIdx variable from MATLAB workspace
        struct_idx = self.eng.workspace["structIdx"]
        
        if int(struct_idx) == 0:
            return {"success": False, "error": f"Structure '{structure_name}' not found in CST"}
        
        # Calculate DVH and quality indicators using matRad's robust function
        dvh_data = self._calculate_structure_metrics(int(struct_idx))
        
        # Create detailed clinical assessment
        assessment = self._generate_clinical_assessment(dvh_data)
        
        # Create individual DVH plot
        plot_file = self._create_single_structure_plot(dvh_data)
        
        return {
            "success": True,
            "structure": dvh_data["structure_name"],
            "structure_type": dvh_data["structure_type"],
            "dvh_assessment": assessment,
            "dvh_metrics": {
                "D95": dvh_data["D95"],
                "D50": dvh_data["D50"],
                "D5": dvh_data["D5"],
                "D2": dvh_data["D2"],
                "D98": dvh_data["D98"],
                "mean_dose": dvh_data["mean_dose"],
                "max_dose": dvh_data["max_dose"],
                "min_dose": dvh_data["min_dose"],
                "std_dose": dvh_data["std_dose"],
                "V_5Gy": dvh_data["V_5Gy"],
                "V_10Gy": dvh_data["V_10Gy"],
                "V_20Gy": dvh_data["V_20Gy"],
                "V_30Gy": dvh_data["V_30Gy"],
                "V_40Gy": dvh_data["V_40Gy"],
                "V_50Gy": dvh_data["V_50Gy"],
                "V_60Gy": dvh_data["V_60Gy"],
                "HI": dvh_data["HI"],
                "CI": dvh_data["CI"]
            },
            "plot_file": plot_file,
            "message": f"DVH analyzed for {structure_name} using matRad quality indicators"
        }
    
    def _calculate_all_structures_dvh(self) -> Dict[str, Any]:
        """Calculate DVH for all structures with detailed assessments."""
        
        # Just get structure information - let individual calls handle DVH/QI calculations
        self.eng.eval("""
        % Store all structure indices that have data
        validStructIndices = [];
        for i = 1:size(cst,1)
            if ~isempty(cst{i,2}) && ~isempty(cst{i,4})
                validStructIndices(end+1) = i;
            end
        end
        """, nargout=0)
        
        # Get valid structure indices and handle matlab.double array
        matlab_indices = self.eng.workspace["validStructIndices"]
        
        # Convert matlab.double array to Python list
        if hasattr(matlab_indices, '_data'):
            # matlab.double array - extract the underlying data
            valid_indices = [int(idx) for idx in matlab_indices._data]
        elif isinstance(matlab_indices, (list, tuple)):
            # Already a Python list/tuple
            valid_indices = [int(idx) for idx in matlab_indices]
        else:
            # Single value
            valid_indices = [int(matlab_indices)]
        
        # Calculate metrics for each structure
        all_structures_data = []
        structure_names = []
        
        for idx in valid_indices:
            dvh_data = self._calculate_structure_metrics(idx)
            assessment = self._generate_clinical_assessment(dvh_data)
            
            structure_result = {
                "structure_name": dvh_data["structure_name"],
                "structure_type": dvh_data["structure_type"],
                "dvh_assessment": assessment,
                "dvh_metrics": {
                    "D95": dvh_data["D95"],
                    "D50": dvh_data["D50"],
                    "D5": dvh_data["D5"],
                    "D2": dvh_data["D2"],
                    "D98": dvh_data["D98"],
                    "mean_dose": dvh_data["mean_dose"],
                    "max_dose": dvh_data["max_dose"],
                    "min_dose": dvh_data["min_dose"],
                    "std_dose": dvh_data["std_dose"],
                    "V_5Gy": dvh_data["V_5Gy"],
                    "V_10Gy": dvh_data["V_10Gy"],
                    "V_20Gy": dvh_data["V_20Gy"],
                    "V_30Gy": dvh_data["V_30Gy"],
                    "V_40Gy": dvh_data["V_40Gy"],
                    "V_50Gy": dvh_data["V_50Gy"],
                    "V_60Gy": dvh_data["V_60Gy"],
                    "HI": dvh_data["HI"],
                    "CI": dvh_data["CI"]
                }
            }
            all_structures_data.append(structure_result)
            structure_names.append(dvh_data["structure_name"])
        
        # Create comprehensive plot
        plot_file = self._create_all_structures_plot(valid_indices)
        
        # Generate summary assessment
        summary_assessment = self._generate_summary_assessment(all_structures_data)
        
        return {
            "success": True,
            "num_structures": len(all_structures_data),
            "structure_names": structure_names,
            "structures_data": all_structures_data,
            "dvh_assessment": summary_assessment,
            "plot_file": plot_file,
            "message": f"DVH analyzed for all {len(all_structures_data)} structures using matRad quality indicators"
        }
    
    def _calculate_structure_metrics(self, struct_idx: int) -> Dict[str, Any]:
        """Calculate comprehensive metrics for a single structure using matRad quality indicators."""
        
        self.eng.eval(f"""
        % Get the full dose cube (already scaled by fractions)
        numOfFractions = pln.numOfFractions;
        dose = resultGUI.physicalDose * numOfFractions;
        
        % Get CST dimensions and create a temporary CST with just this structure
        [numRows, numCols] = size(cst);
        tempCst = cell(1, numCols);
        tempCst(1,:) = cst({struct_idx},:);
        
        % Calculate DVH using standard matRad function
        dvhResult = matRad_calcDVH(tempCst, dose, 'cum');
        
        % Calculate quality indicators using matRad's robust function
        refVol = [2 5 50 95 98];  % For D2, D5, D50, D95, D98
        refGy = [5 10 20 30 40 50 60];  % For V5Gy, V10Gy, etc.
        qi = matRad_calcQualityIndicators(tempCst, pln, dose, refGy, refVol);
        
        % Extract all data into a simple structure for Python access
        dvhData = struct();
        dvhData.structure_name = dvhResult(1).name;
        dvhData.structure_type = cst{{{struct_idx},3}};
        dvhData.dvh_values = dvhResult(1).volumePoints;
        dvhData.bin_centers = dvhResult(1).doseGrid;
        
        % Basic quality metrics from matRad QI
        qiStruct = qi(1);
        dvhData.mean_dose = qiStruct.mean;
        dvhData.max_dose = qiStruct.max;
        dvhData.min_dose = qiStruct.min;
        dvhData.std_dose = qiStruct.std;
        dvhData.D95 = qiStruct.D_95;
        dvhData.D50 = qiStruct.D_50;
        dvhData.D5 = qiStruct.D_5;
        dvhData.D2 = qiStruct.D_2;
        dvhData.D98 = qiStruct.D_98;
        
        % V-metrics from matRad QI
        dvhData.V_5Gy = qiStruct.V_5Gy;
        dvhData.V_10Gy = qiStruct.V_10Gy;
        dvhData.V_20Gy = qiStruct.V_20Gy;
        dvhData.V_30Gy = qiStruct.V_30Gy;
        dvhData.V_40Gy = qiStruct.V_40Gy;
        dvhData.V_50Gy = qiStruct.V_50Gy;
        dvhData.V_60Gy = qiStruct.V_60Gy;
        
        % Target-specific metrics (CI/HI) if available
        if strcmp(cst{{{struct_idx},3}}, 'TARGET')
            % Look for CI and HI fields in QI
            field_names = fieldnames(qiStruct);
            ci_fields = field_names(startsWith(field_names, 'CI_'));
            hi_fields = field_names(startsWith(field_names, 'HI_'));
            
            if ~isempty(ci_fields)
                dvhData.CI = qiStruct.(ci_fields{{1}});
            else
                dvhData.CI = NaN;
            end
            
            if ~isempty(hi_fields)
                dvhData.HI = qiStruct.(hi_fields{{1}});
            else
                dvhData.HI = NaN;
            end
        else
            dvhData.CI = NaN;
            dvhData.HI = NaN;
        end
        """, nargout=0)
        
        # Get the results from MATLAB and convert to Python dict
        matlab_dvh_data = self.eng.workspace["dvhData"]
        
        # Helper function to safely extract values from matlab objects and format to 2 decimal places
        def safe_extract(value):
            if hasattr(value, '_data'):
                # matlab.double - extract underlying data
                val = float(value._data[0]) if len(value._data) > 0 else float('nan')
            elif hasattr(value, '__float__'):
                val = float(value)
            else:
                val = float('nan')
            
            # Format to 2 decimal places unless it's NaN
            return round(val, 2) if not (val != val) else val  # val != val checks for NaN
        
        # Helper function to extract arrays from matlab objects and format to 2 decimal places
        def safe_extract_array(value):
            if hasattr(value, '_data'):
                # matlab.double array - extract the underlying data and format to 2 decimal places
                return [round(float(x), 2) for x in value._data]
            elif isinstance(value, (list, tuple)):
                return [round(float(x), 2) for x in value]
            else:
                return [round(float(value), 2)] if value is not None else []
        
        return {
            "structure_name": str(matlab_dvh_data['structure_name']),
            "structure_type": str(matlab_dvh_data['structure_type']),
            "mean_dose": safe_extract(matlab_dvh_data['mean_dose']),
            "max_dose": safe_extract(matlab_dvh_data['max_dose']),
            "min_dose": safe_extract(matlab_dvh_data['min_dose']),
            "std_dose": safe_extract(matlab_dvh_data['std_dose']),
            "D95": safe_extract(matlab_dvh_data['D95']),
            "D50": safe_extract(matlab_dvh_data['D50']),
            "D5": safe_extract(matlab_dvh_data['D5']),
            "D2": safe_extract(matlab_dvh_data['D2']),
            "D98": safe_extract(matlab_dvh_data['D98']),
            "V_5Gy": safe_extract(matlab_dvh_data['V_5Gy']),
            "V_10Gy": safe_extract(matlab_dvh_data['V_10Gy']),
            "V_20Gy": safe_extract(matlab_dvh_data['V_20Gy']),
            "V_30Gy": safe_extract(matlab_dvh_data['V_30Gy']),
            "V_40Gy": safe_extract(matlab_dvh_data['V_40Gy']),
            "V_50Gy": safe_extract(matlab_dvh_data['V_50Gy']),
            "V_60Gy": safe_extract(matlab_dvh_data['V_60Gy']),
            "HI": safe_extract(matlab_dvh_data.get('HI', float('nan'))),
            "CI": safe_extract(matlab_dvh_data.get('CI', float('nan'))),
            "dvh_values": safe_extract_array(matlab_dvh_data['dvh_values']),
            "bin_centers": safe_extract_array(matlab_dvh_data['bin_centers'])
        }
    
    def _generate_clinical_assessment(self, dvh_data: Dict[str, Any]) -> str:
        """Generate detailed clinical assessment for a structure."""
        import math
        
        structure_name = dvh_data["structure_name"]
        structure_type = dvh_data["structure_type"]
        mean_dose = dvh_data["mean_dose"]
        max_dose = dvh_data["max_dose"]
        min_dose = dvh_data["min_dose"]
        std_dose = dvh_data["std_dose"]
        d2 = dvh_data["D2"]
        d5 = dvh_data["D5"]
        d50 = dvh_data["D50"]
        d95 = dvh_data["D95"]
        d98 = dvh_data["D98"]
        
        # V-metrics
        v_5gy = dvh_data["V_5Gy"]
        v_10gy = dvh_data["V_10Gy"]
        v_20gy = dvh_data["V_20Gy"]
        v_30gy = dvh_data["V_30Gy"]
        v_40gy = dvh_data["V_40Gy"]
        v_50gy = dvh_data["V_50Gy"]
        v_60gy = dvh_data["V_60Gy"]
        
        # Target metrics
        ci = dvh_data["CI"]
        hi = dvh_data["HI"]
        
        assessment = []
        assessment.append(f"DVH ASSESSMENT FOR {structure_type}: {structure_name}")
        assessment.append("=" * 60)
        assessment.append("QUALITY INDICATORS (matRad_calcQualityIndicators):")
        assessment.append(f"  Mean Dose: {mean_dose:.2f} Gy")
        assessment.append(f"  D2: {d2:.2f} Gy | D5: {d5:.2f} Gy | D50: {d50:.2f} Gy | D95: {d95:.2f} Gy | D98: {d98:.2f} Gy")
        assessment.append(f"  Dose Range: {min_dose:.2f} - {max_dose:.2f} Gy")
        
        # V-metrics summary
        assessment.append(f"VOLUME METRICS:")
        assessment.append(f"  V5Gy: {v_5gy*100:.2f}% | V10Gy: {v_10gy*100:.2f}% | V20Gy: {v_20gy*100:.2f}%")
        assessment.append(f"  V30Gy: {v_30gy*100:.2f}% | V40Gy: {v_40gy*100:.2f}% | V50Gy: {v_50gy*100:.2f}% | V60Gy: {v_60gy*100:.2f}%")
        
        # Target-specific analysis
        if structure_type == 'TARGET':
            assessment.append(f"TARGET QUALITY ASSESSMENT:")
            if not math.isnan(hi):
                assessment.append(f"  Homogeneity Index: {hi:.2f}")
                if hi < 5:
                    assessment.append(f"    EXCELLENT homogeneity")
                elif hi < 10:
                    assessment.append(f"    GOOD homogeneity")
                else:
                    assessment.append(f"    Poor homogeneity - optimize plan")
            
            if not math.isnan(ci):
                assessment.append(f"  Conformity Index: {ci:.2f}")
                if ci > 0.9:
                    assessment.append(f"    EXCELLENT conformity")
                elif ci > 0.8:
                    assessment.append(f"    GOOD conformity")
                else:
                    assessment.append(f"    Poor conformity - dose spillage")
            
            # Coverage analysis
            coverage = (d95 / d50) * 100 if d50 > 0 else 0
            assessment.append(f"  Coverage: D95 = {coverage:.2f}% of D50")
            if coverage >= 95:
                assessment.append(f"    EXCELLENT coverage")
            elif coverage >= 90:
                assessment.append(f"    GOOD coverage")
            else:
                assessment.append(f"    Poor coverage - underdosage risk")
        
        elif structure_type == 'OAR':
            assessment.append(f"OAR SPARING ASSESSMENT:")
            if max_dose > 50:
                assessment.append(f"  HIGH-DOSE OAR: Max dose {max_dose:.2f} Gy")
            elif max_dose > 20:
                assessment.append(f"  MODERATE-DOSE OAR: Max dose {max_dose:.2f} Gy") 
            else:
                assessment.append(f"  LOW-DOSE OAR: Max dose {max_dose:.2f} Gy - good sparing")
        
        # DVH curve analysis
        dose_spread = d5 - d95
        assessment.append(f"DVH CURVE ANALYSIS:")
        assessment.append(f"  Dose Spread (D5-D95): {dose_spread:.2f} Gy")
        if structure_type == 'TARGET':
            if dose_spread < 5:
                assessment.append(f"    STEEP curve - excellent homogeneity")
            elif dose_spread < 10:
                assessment.append(f"    MODERATE curve - good homogeneity")
            else:
                assessment.append(f"    SHALLOW curve - dose heterogeneity")
        
        return "\n".join(assessment)
    
    def _create_single_structure_plot(self, dvh_data: Dict[str, Any]) -> str:
        """Create DVH plot for a single structure."""
        structure_name = dvh_data["structure_name"]
        d95 = dvh_data["D95"]
        d50 = dvh_data["D50"]
        
        self.eng.eval(f"""
        % Create DVH plot
        figure('Position', [100, 100, 800, 600], 'Visible', 'off');
        plot(dvhData.bin_centers, dvhData.dvh_values, 'LineWidth', 2);
        xlabel('Dose (Gy)', 'FontSize', 12);
        ylabel('Volume (%)', 'FontSize', 12);
        title(['DVH for ' dvhData.structure_name], 'FontSize', 14);
        grid on;
        
        % Add key points
        hold on;
        plot({d95}, 95, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
        plot({d50}, 50, 'go', 'MarkerSize', 8, 'MarkerFaceColor', 'g');
        legend({{'DVH Curve', 'D95', 'D50'}}, 'Location', 'best');
        
        % Save plot
        plotFilename = ['dvh_' strrep(dvhData.structure_name, ' ', '_') '.png'];
        saveas(gcf, plotFilename);
        close(gcf);
        """, nargout=0)
        
        plot_filename = f"dvh_{structure_name.replace(' ', '_')}.png"
        return plot_filename
    
    def _create_all_structures_plot(self, valid_indices: List[int]) -> str:
        """Create comprehensive DVH plot for all structures."""
        self.eng.eval(f"""
        % Get structure data for plotting
        numOfFractions = pln.numOfFractions;
        dose = resultGUI.physicalDose * numOfFractions;
        dvhResults = matRad_calcDVH(cst, dose, 'cum');
        
        % Create a comprehensive DVH plot for all structures
        figure('Position', [100, 100, 1200, 800], 'Visible', 'off');
        colors = lines(length(dvhResults));
        legendEntries = {{}};
        
        for i = 1:length(dvhResults)
            % Plot this structure's DVH
            plot(dvhResults(i).doseGrid, dvhResults(i).volumePoints, ...
                 'Color', colors(i,:), 'LineWidth', 2);
            hold on;
            legendEntries{{end+1}} = dvhResults(i).name;
        end
        
        xlabel('Dose (Gy)', 'FontSize', 12);
        ylabel('Volume (%)', 'FontSize', 12);
        title('DVH for All Structures', 'FontSize', 14);
        legend(legendEntries, 'Location', 'bestoutside', 'Interpreter', 'none');
        grid on;
        
        % Save comprehensive plot
        plotFilename = 'dvh_all_structures.png';
        saveas(gcf, plotFilename);
        close(gcf);
        """, nargout=0)
        
        return 'dvh_all_structures.png'
    
    def _generate_summary_assessment(self, all_structures_data: List[Dict[str, Any]]) -> str:
        """Generate summary assessment for all structures."""
        
        num_structures = len(all_structures_data)
        structure_names = [data["structure_name"] for data in all_structures_data]
        targets = [data for data in all_structures_data if data["structure_type"] == 'TARGET']
        oars = [data for data in all_structures_data if data["structure_type"] == 'OAR']
        
        summary = []
        summary.append(f"DVH ANALYSIS SUMMARY - ALL STRUCTURES")
        summary.append("=" * 60)
        summary.append(f"Total Structures Analyzed: {num_structures}")
        summary.append(f"Targets: {len(targets)} | OARs: {len(oars)}")
        summary.append(f"Structures: {', '.join(structure_names)}")
        summary.append("")
        
        # Target summary
        if targets:
            summary.append("TARGET SUMMARY:")
            for target in targets:
                metrics = target["dvh_metrics"]
                summary.append(f"  {target['structure_name']}:")
                summary.append(f"    Coverage: D95={metrics['D95']:.1f}Gy, Mean={metrics['mean_dose']:.1f}Gy")
                if not math.isnan(metrics['HI']):
                    summary.append(f"    Quality: HI={metrics['HI']:.2f}, CI={metrics['CI']:.2f}")
                summary.append("")
        
        # OAR summary
        if oars:
            summary.append("OAR SUMMARY:")
            for oar in oars:
                metrics = oar["dvh_metrics"]
                summary.append(f"  {oar['structure_name']}:")
                summary.append(f"    Sparing: Max={metrics['max_dose']:.1f}Gy, Mean={metrics['mean_dose']:.1f}Gy")
                summary.append(f"    Low-dose spill: V5Gy={metrics['V_5Gy']*100:.1f}%, V20Gy={metrics['V_20Gy']*100:.1f}%")
                summary.append("")
        
        summary.append("DETAILED ASSESSMENTS:")
        summary.append("Use the structures_data field for individual structure analysis.")
        summary.append("Each structure includes comprehensive DVH metrics and clinical assessment.")
        
        return "\n".join(summary)
    
    def evaluate_plan(self) -> Dict[str, Any]:
        """
        **PRIMARY TOOL FOR COMPREHENSIVE PLAN EVALUATION**
        
        Comprehensive evaluation of the current treatment plan using matRad's official quality indicators.
        Includes DVH analysis, quality metrics, clinical assessments, and visual plots for ALL structures.
        
        **USE THIS FOR:**
        - Overall plan quality assessment
        - Treatment plan approval/rejection decisions
        - Comparing different treatment plans
        - Getting complete clinical summary of the plan
        - Plan-level quality scoring and recommendations
        
        **Returns comprehensive data including:**
        - Plan-level quality assessment with clinical recommendations
        - Quality indicators for all structures (D95, D50, HI, CI, etc.)
        - DVH data and plots for all structures
        - Plan quality score (0-100)
        - Target coverage and OAR sparing summaries
        
        Returns:
            Dict with comprehensive plan evaluation including DVH, quality indicators, and clinical assessments.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.resultGUI is None:
            return {"success": False, "error": "No optimization results available. Call optimize_fluence first."}
            
        try:
            # Check if resultGUI has a physicalDose field
            has_dose = self.eng.eval("isfield(resultGUI, 'physicalDose')", nargout=1)
            if not has_dose:
                return {"success": False, "error": "No dose information available in result"}
            
            # Get all valid structure indices
            self.eng.eval("""
            % Store all structure indices that have data
            validStructIndices = [];
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2}) && ~isempty(cst{i,4})
                    validStructIndices(end+1) = i;
                end
            end
            """, nargout=0)
            
            # Get valid structure indices and handle matlab.double array
            matlab_indices = self.eng.workspace["validStructIndices"]
            
            # Convert matlab.double array to Python list
            if hasattr(matlab_indices, '_data'):
                valid_indices = [int(idx) for idx in matlab_indices._data]
            elif isinstance(matlab_indices, (list, tuple)):
                valid_indices = [int(idx) for idx in matlab_indices]
            else:
                valid_indices = [int(matlab_indices)]
            
            # Calculate comprehensive quality indicators and DVH for all structures
            all_structures_data = []
            structure_names = []
            
            for idx in valid_indices:
                # Calculate comprehensive metrics using matRad's official quality indicators
                dvh_data = self._calculate_structure_metrics(idx)
                assessment = self._generate_clinical_assessment(dvh_data)
                
                structure_result = {
                    "structure_name": dvh_data["structure_name"],
                    "structure_type": dvh_data["structure_type"],
                    "clinical_assessment": assessment,
                    "quality_indicators": {
                        "D95": dvh_data["D95"],
                        "D50": dvh_data["D50"],
                        "D5": dvh_data["D5"],
                        "D2": dvh_data["D2"],
                        "D98": dvh_data["D98"],
                        "mean_dose": dvh_data["mean_dose"],
                        "max_dose": dvh_data["max_dose"],
                        "min_dose": dvh_data["min_dose"],
                        "std_dose": dvh_data["std_dose"],
                        "V_5Gy": dvh_data["V_5Gy"],
                        "V_10Gy": dvh_data["V_10Gy"],
                        "V_20Gy": dvh_data["V_20Gy"],
                        "V_30Gy": dvh_data["V_30Gy"],
                        "V_40Gy": dvh_data["V_40Gy"],
                        "V_50Gy": dvh_data["V_50Gy"],
                        "V_60Gy": dvh_data["V_60Gy"],
                        "HI": dvh_data["HI"],
                        "CI": dvh_data["CI"]
                    }
                }
                all_structures_data.append(structure_result)
                structure_names.append(dvh_data["structure_name"])
            
            # Create comprehensive DVH plot for all structures
            plot_file = self._create_all_structures_plot(valid_indices)
            
            # Generate overall plan assessment
            plan_assessment = self._generate_plan_assessment(all_structures_data)
            
            # Separate targets and OARs for summary
            targets = [data for data in all_structures_data if data["structure_type"] == 'TARGET']
            oars = [data for data in all_structures_data if data["structure_type"] == 'OAR']
            
            # Calculate plan-level metrics
            plan_metrics = self._calculate_plan_level_metrics(targets, oars)
            
            return {
                "success": True,
                "plan_assessment": plan_assessment,
                "plan_metrics": plan_metrics,
                "num_structures": len(all_structures_data),
                "num_targets": len(targets),
                "num_oars": len(oars),
                "structure_names": structure_names,
                "structures_evaluation": all_structures_data,
                "dvh_plot": plot_file,
                "message": f"Comprehensive plan evaluation completed using matRad quality indicators for {len(all_structures_data)} structures"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_plan_assessment(self, all_structures_data: List[Dict[str, Any]]) -> str:
        """Generate overall plan assessment summary."""
        import math
        
        targets = [data for data in all_structures_data if data["structure_type"] == 'TARGET']
        oars = [data for data in all_structures_data if data["structure_type"] == 'OAR']
        
        assessment = []
        assessment.append("COMPREHENSIVE TREATMENT PLAN EVALUATION")
        assessment.append("=" * 60)
        assessment.append(f"Evaluated using matRad_calcQualityIndicators")
        assessment.append(f"Total Structures: {len(all_structures_data)} (Targets: {len(targets)}, OARs: {len(oars)})")
        assessment.append("")
        
        # TARGET EVALUATION
        if targets:
            assessment.append("TARGET EVALUATION:")
            assessment.append("-" * 30)
            
            excellent_targets = 0
            good_targets = 0
            poor_targets = 0
            
            for target in targets:
                qi = target["quality_indicators"]
                name = target["structure_name"]
                
                assessment.append(f"{name}:")
                assessment.append(f"  Prescription Coverage: D95={qi['D95']:.1f}Gy, D98={qi['D98']:.1f}Gy")
                assessment.append(f"  Dose Statistics: Mean={qi['mean_dose']:.1f}Gy, Max={qi['max_dose']:.1f}Gy")
                
                # Coverage assessment
                coverage_ratio = qi['D95'] / qi['D50'] if qi['D50'] > 0 else 0
                if coverage_ratio >= 0.95:
                    assessment.append(f"  ✓ EXCELLENT coverage ({coverage_ratio*100:.1f}%)")
                    excellent_targets += 1
                elif coverage_ratio >= 0.90:
                    assessment.append(f"  ○ GOOD coverage ({coverage_ratio*100:.1f}%)")
                    good_targets += 1
                else:
                    assessment.append(f"  ✗ POOR coverage ({coverage_ratio*100:.1f}%) - Risk of underdosage")
                    poor_targets += 1
                
                # Homogeneity assessment
                if not math.isnan(qi['HI']):
                    if qi['HI'] < 5:
                        assessment.append(f"  ✓ EXCELLENT homogeneity (HI={qi['HI']:.2f})")
                    elif qi['HI'] < 10:
                        assessment.append(f"  ○ GOOD homogeneity (HI={qi['HI']:.2f})")
                    else:
                        assessment.append(f"  ✗ POOR homogeneity (HI={qi['HI']:.2f})")
                
                # Conformity assessment
                if not math.isnan(qi['CI']):
                    if qi['CI'] > 0.9:
                        assessment.append(f"  ✓ EXCELLENT conformity (CI={qi['CI']:.2f})")
                    elif qi['CI'] > 0.8:
                        assessment.append(f"  ○ GOOD conformity (CI={qi['CI']:.2f})")
                    else:
                        assessment.append(f"  ✗ POOR conformity (CI={qi['CI']:.2f}) - Dose spillage")
                
                assessment.append("")
            
            # Target summary
            assessment.append(f"TARGET SUMMARY: {excellent_targets} excellent, {good_targets} good, {poor_targets} poor")
            assessment.append("")
        
        # OAR EVALUATION
        if oars:
            assessment.append("OAR SPARING EVALUATION:")
            assessment.append("-" * 30)
            
            well_spared = 0
            moderate_dose = 0
            high_dose = 0
            
            for oar in oars:
                qi = oar["quality_indicators"]
                name = oar["structure_name"]
                
                assessment.append(f"{name}:")
                assessment.append(f"  Dose Statistics: Max={qi['max_dose']:.1f}Gy, Mean={qi['mean_dose']:.1f}Gy")
                assessment.append(f"  Volume Metrics: V5Gy={qi['V_5Gy']*100:.1f}%, V20Gy={qi['V_20Gy']*100:.1f}%, V50Gy={qi['V_50Gy']*100:.1f}%")
                
                # Sparing assessment
                if qi['max_dose'] < 10:
                    assessment.append(f"  ✓ EXCELLENT sparing (Max dose <10Gy)")
                    well_spared += 1
                elif qi['max_dose'] < 30:
                    assessment.append(f"  ○ MODERATE exposure (Max dose {qi['max_dose']:.1f}Gy)")
                    moderate_dose += 1
                else:
                    assessment.append(f"  ⚠ HIGH dose exposure (Max dose {qi['max_dose']:.1f}Gy)")
                    high_dose += 1
                
                assessment.append("")
            
            # OAR summary
            assessment.append(f"OAR SUMMARY: {well_spared} well-spared, {moderate_dose} moderate dose, {high_dose} high dose")
            assessment.append("")
        
        # Overall plan assessment
        assessment.append("OVERALL PLAN QUALITY:")
        assessment.append("-" * 30)
        
        if targets:
            target_quality = excellent_targets / len(targets)
            if target_quality >= 0.8:
                assessment.append("✓ TARGET COVERAGE: EXCELLENT")
            elif target_quality >= 0.6:
                assessment.append("○ TARGET COVERAGE: GOOD")
            else:
                assessment.append("✗ TARGET COVERAGE: NEEDS IMPROVEMENT")
        
        if oars:
            oar_quality = well_spared / len(oars)
            if oar_quality >= 0.8:
                assessment.append("✓ OAR SPARING: EXCELLENT")
            elif oar_quality >= 0.6:
                assessment.append("○ OAR SPARING: GOOD")
            else:
                assessment.append("⚠ OAR SPARING: NEEDS IMPROVEMENT")
        
        assessment.append("")
        assessment.append("RECOMMENDATION:")
        if targets and oars:
            overall_quality = (excellent_targets + well_spared) / (len(targets) + len(oars))
            if overall_quality >= 0.8:
                assessment.append("✓ Plan is clinically acceptable - proceed with treatment")
            elif overall_quality >= 0.6:
                assessment.append("○ Plan is adequate but could benefit from minor optimization")
            else:
                assessment.append("✗ Plan needs significant reoptimization before clinical use")
        
        return "\n".join(assessment)
    
    def _calculate_plan_level_metrics(self, targets: List[Dict], oars: List[Dict]) -> Dict[str, Any]:
        """Calculate plan-level summary metrics."""
        import math
        
        plan_metrics = {
            "target_summary": {},
            "oar_summary": {},
            "plan_quality_score": 0.0
        }
        
        if targets:
            # Target metrics
            mean_target_coverage = sum([t["quality_indicators"]["D95"] for t in targets]) / len(targets)
            mean_target_homogeneity = sum([t["quality_indicators"]["HI"] for t in targets if not math.isnan(t["quality_indicators"]["HI"])]) / max(1, len([t for t in targets if not math.isnan(t["quality_indicators"]["HI"])]))
            mean_target_conformity = sum([t["quality_indicators"]["CI"] for t in targets if not math.isnan(t["quality_indicators"]["CI"])]) / max(1, len([t for t in targets if not math.isnan(t["quality_indicators"]["CI"])]))
            
            plan_metrics["target_summary"] = {
                "mean_D95": round(mean_target_coverage, 2),
                "mean_homogeneity_index": round(mean_target_homogeneity, 2),
                "mean_conformity_index": round(mean_target_conformity, 2),
                "num_targets": len(targets)
            }
        
        if oars:
            # OAR metrics
            mean_oar_max_dose = sum([o["quality_indicators"]["max_dose"] for o in oars]) / len(oars)
            mean_oar_mean_dose = sum([o["quality_indicators"]["mean_dose"] for o in oars]) / len(oars)
            mean_v20 = sum([o["quality_indicators"]["V_20Gy"] for o in oars]) / len(oars)
            
            plan_metrics["oar_summary"] = {
                "mean_max_dose": round(mean_oar_max_dose, 2),
                "mean_mean_dose": round(mean_oar_mean_dose, 2),
                "mean_V20Gy": round(mean_v20 * 100, 2),
                "num_oars": len(oars)
            }
        
        # Calculate overall quality score (0-100)
        quality_score = 0
        if targets:
            # Target score based on coverage and homogeneity
            target_score = min(100, (mean_target_coverage / 60) * 50)  # Up to 50 points for coverage
            if not math.isnan(mean_target_homogeneity):
                homogeneity_score = max(0, 25 - mean_target_homogeneity * 2.5)  # Up to 25 points for homogeneity
                target_score += homogeneity_score
            quality_score += target_score
        
        if oars:
            # OAR score based on sparing (lower doses = higher score)
            oar_score = max(0, 25 - (mean_oar_max_dose / 60) * 25)  # Up to 25 points for OAR sparing
            quality_score += oar_score
        
        plan_metrics["plan_quality_score"] = round(quality_score, 1)
        
        return plan_metrics

    def create_ring_structures(self, reference_structure: str, ring_margins_mm: List[float], 
                             inner_margin_mm: float = 0, visualize: bool = False) -> Dict[str, Any]:
        """
        Create concentric ring VOIs around a reference structure.
        
        Args:
            reference_structure: Name of the reference structure (e.g., "PTV")
            ring_margins_mm: List of ring margins in mm (e.g., [5, 10, 15])
            inner_margin_mm: Inner margin from reference structure in mm (default: 0)
            visualize: Whether to create visualization (default: False)
            
        Returns:
            Dict with success status and ring information
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB engine not started"}
        
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Find reference structure index by querying MATLAB directly
            struct_info = self.get_structure_names()
            if not struct_info.get("success"):
                return {"success": False, "error": "Could not get structure information"}
                
            # Handle both possible formats: 'structures' or separate 'targets'/'oars'/'other'
            if "structures" in struct_info:
                structure_names = [s["name"] for s in struct_info.get("structures", [])]
            else:
                # Combine targets, oars, and other into one list
                structure_names = []
                structure_names.extend(struct_info.get("targets", []))
                structure_names.extend(struct_info.get("oars", []))
                structure_names.extend(struct_info.get("other", []))
                
            if reference_structure not in structure_names:
                return {"success": False, "error": f"Reference structure '{reference_structure}' not found. Available: {structure_names}"}
            
            # Find the actual CST index from MATLAB (1-based)
            matlab_code_find_index = f"""
            ref_index = 0;
            for i = 1:size(cst, 1)
                if strcmp(cst{{i, 2}}, '{reference_structure}')
                    ref_index = i;
                    break;
                end
            end
            """
            self.eng.eval(matlab_code_find_index, nargout=0)
            ref_index = int(self.eng.eval("ref_index"))
            
            if ref_index == 0:
                return {"success": False, "error": f"Reference structure '{reference_structure}' not found in CST. Available: {structure_names}"}
            
            # Convert parameters to MATLAB format
            ring_margins_str = '[' + ', '.join(map(str, ring_margins_mm)) + ']'
            
            # Add the ring creation function to MATLAB path
            self.eng.eval("addpath('userdata/scripts')", nargout=0)
            
            # Call the ring creation function
            matlab_code = f"""
            try
                [cst, ringInfo] = matRad_VOICreateRings(ct, cst, {ring_margins_str}, {ref_index}, {inner_margin_mm}, {str(visualize).lower()});
                
                % Convert ringInfo to individual variables that can be returned
                ring_names = cell(length(ringInfo), 1);
                ring_margins = zeros(length(ringInfo), 1);
                ring_voxels = zeros(length(ringInfo), 1);
                
                for i = 1:length(ringInfo)
                    ring_names{{i}} = ringInfo(i).name;
                    ring_margins(i) = ringInfo(i).margin_mm;
                    ring_voxels(i) = ringInfo(i).voxelsAdded;
                end
                
                ring_creation_success = true;
                ring_creation_error = '';
                
            catch ME
                ring_creation_success = false;
                ring_creation_error = ME.message;
                ring_names = {{}};
                ring_margins = [];
                ring_voxels = [];
            end
            """
            
            self.eng.eval(matlab_code, nargout=0)
            
            # Get results
            success = bool(self.eng.eval("ring_creation_success"))
            if not success:
                error_msg = self.eng.eval("ring_creation_error")
                return {"success": False, "error": f"Ring creation failed: {error_msg}"}
            
            # Get ring information from individual variables
            try:
                ring_names = self.eng.eval("ring_names")
                ring_margins = self.eng.eval("ring_margins")
                ring_voxels = self.eng.eval("ring_voxels")
                
                # Convert MATLAB data to Python list of dicts
                ring_info = []
                
                # Handle MATLAB cell array for names
                if hasattr(ring_names, '__iter__') and len(ring_names) > 0:
                    # Extract data from MATLAB arrays
                    names_list = list(ring_names) if hasattr(ring_names, '__iter__') else [ring_names]
                    margins_list = list(ring_margins) if hasattr(ring_margins, '__iter__') else [ring_margins]
                    voxels_list = list(ring_voxels) if hasattr(ring_voxels, '__iter__') else [ring_voxels]
                    
                    for i in range(len(names_list)):
                        # Extract values from MATLAB data types
                        name = str(names_list[i])
                        
                        # Handle matlab.double objects
                        if hasattr(margins_list[i], '_data'):
                            margin_val = float(margins_list[i]._data[i])
                        elif hasattr(margins_list[i], '__iter__') and len(margins_list[i]) > 0:
                            margin_val = float(margins_list[i][0])
                        else:
                            margin_val = float(margins_list[i])
                            
                        if hasattr(voxels_list[i], '_data'):
                            voxels_val = int(voxels_list[i]._data[i])
                        elif hasattr(voxels_list[i], '__iter__') and len(voxels_list[i]) > 0:
                            voxels_val = int(voxels_list[i][0])
                        else:
                            voxels_val = int(voxels_list[i])
                        
                        ring_info.append({
                            "name": name,
                            "margin_mm": margin_val,
                            "voxels_added": voxels_val
                        })
            except Exception as e:
                # If data extraction fails, create basic info from input parameters
                ring_info = []
                for i, margin in enumerate(ring_margins_mm):
                    ring_info.append({
                        "name": f"{reference_structure}Ring{margin}mm",
                        "margin_mm": float(margin),
                        "voxels_added": 0  # Unknown
                    })
            
            # Set priorities for newly created ring structures
            for ring in ring_info:
                # Set minimal priority for ring structure
                self.eng.eval(f"""
                for i = 1:size(cst, 1)
                    if strcmp(cst{{i, 2}}, '{ring["name"]}')
                        cst{{i, 5}}.Priority = 3;
                        break;
                    end
                end
                """, nargout=0)
            
            return {
                "success": True,
                "message": f"Created {len(ring_margins_mm)} ring structures around {reference_structure}",
                "reference_structure": reference_structure,
                "ring_margins_mm": ring_margins_mm,
                "inner_margin_mm": inner_margin_mm,
                "rings_created": ring_info,
                "num_rings": len(ring_info)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def perform_voi_operation(self, structure1: str, structure2: str, operation: str, 
                            new_structure_name: str) -> Dict[str, Any]:
        """
        Perform VOI operations (union, intersection, difference) between two structures.
        
        Args:
            structure1: Name of first structure
            structure2: Name of second structure  
            operation: Type of operation ('union', 'intersect', 'setdiff')
            new_structure_name: Name for the new combined structure
            
        Returns:
            Dict with success status and operation information
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB engine not started"}
        
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        valid_operations = ['union', 'intersect', 'setdiff']
        if operation not in valid_operations:
            return {"success": False, "error": f"Invalid operation '{operation}'. Valid operations: {valid_operations}"}
            
        try:
            # Get structure information
            struct_info = self.get_structure_names()
            if not struct_info.get("success"):
                return {"success": False, "error": "Could not get structure information"}
                
            # Handle both possible formats: 'structures' or separate 'targets'/'oars'/'other'
            if "structures" in struct_info:
                structure_names = [s["name"] for s in struct_info.get("structures", [])]
            else:
                # Combine targets, oars, and other into one list
                structure_names = []
                structure_names.extend(struct_info.get("targets", []))
                structure_names.extend(struct_info.get("oars", []))
                structure_names.extend(struct_info.get("other", []))
                
            if structure1 not in structure_names:
                return {"success": False, "error": f"Structure '{structure1}' not found. Available: {structure_names}"}
            if structure2 not in structure_names:
                return {"success": False, "error": f"Structure '{structure2}' not found. Available: {structure_names}"}
            
            # Find the actual CST indices from MATLAB (1-based)
            matlab_code_find_indices = f"""
            ix1 = 0; ix2 = 0;
            for i = 1:size(cst, 1)
                if strcmp(cst{{i, 2}}, '{structure1}')
                    ix1 = i;
                end
                if strcmp(cst{{i, 2}}, '{structure2}')
                    ix2 = i;
                end
            end
            """
            self.eng.eval(matlab_code_find_indices, nargout=0)
            ix1 = int(self.eng.eval("ix1"))
            ix2 = int(self.eng.eval("ix2"))
            
            if ix1 == 0:
                return {"success": False, "error": f"Structure '{structure1}' not found in CST"}
            if ix2 == 0:
                return {"success": False, "error": f"Structure '{structure2}' not found in CST"}
            
            # Add the VOI operations function to MATLAB path
            self.eng.eval("addpath('userdata/scripts')", nargout=0)
            
            # Call the VOI operation function
            matlab_code = f"""
            try
                [cst, newIx] = matRad_VOIOperations(cst, {ix1}, {ix2}, '{operation}', '{new_structure_name}');
                
                % Get information about the new structure
                newStructInfo.name = cst{{newIx, 2}};
                newStructInfo.type = cst{{newIx, 3}};
                newStructInfo.num_voxels = length(cst{{newIx, 4}}{{1}});
                newStructInfo.index = newIx;
                
                voi_operation_success = true;
                voi_operation_error = '';
                
            catch ME
                voi_operation_success = false;
                voi_operation_error = ME.message;
                newStructInfo = struct();
            end
            """
            
            self.eng.eval(matlab_code, nargout=0)
            
            # Get results
            success = bool(self.eng.eval("voi_operation_success"))
            if not success:
                error_msg = self.eng.eval("voi_operation_error")
                return {"success": False, "error": f"VOI operation failed: {error_msg}"}
            
            # Get new structure information
            new_struct_info = self.eng.eval("newStructInfo")
            
            # Set priority for newly created structure
            # Set minimal priority based on structure type
            if str(new_struct_info["type"]) == "TARGET":
                priority = 1
            elif str(new_struct_info["type"]) == "OAR":
                priority = 2
            else:
                priority = 3
                
            self.eng.eval(f"""
            for i = 1:size(cst, 1)
                if strcmp(cst{{i, 2}}, '{new_structure_name}')
                    cst{{i, 5}}.Priority = {priority};
                    break;
                end
            end
            """, nargout=0)
            
            return {
                "success": True,
                "message": f"Successfully created '{new_structure_name}' from {operation} of '{structure1}' and '{structure2}'",
                "operation": operation,
                "structure1": structure1,
                "structure2": structure2,
                "new_structure": {
                    "name": str(new_struct_info["name"]),
                    "type": str(new_struct_info["type"]),
                    "num_voxels": int(new_struct_info["num_voxels"]),
                    "index": int(new_struct_info["index"])
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def convert_cc_to_percent(self, structure_name: str, volume_cc: float) -> Dict[str, Any]:
        """
        Convert absolute volume in cc to percentage for DVH objectives.
        
        Args:
            structure_name: Name of the structure to analyze
            volume_cc: Volume in cubic centimeters to convert (e.g., 0.03 for D0.03cc constraints)
            
        Returns:
            Dict with volume_percent, volume_fraction, and structure info
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB engine not started"}
        
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Get structure information to find the structure
            struct_info = self.get_structure_names()
            if not struct_info.get("success"):
                return {"success": False, "error": "Could not get structure information"}
                
            # Handle both possible formats: 'structures' or separate 'targets'/'oars'/'other'
            if "structures" in struct_info:
                structure_names = [s["name"] for s in struct_info.get("structures", [])]
            else:
                # Combine targets, oars, and other into one list
                structure_names = []
                structure_names.extend(struct_info.get("targets", []))
                structure_names.extend(struct_info.get("oars", []))
                structure_names.extend(struct_info.get("other", []))
                
            if structure_name not in structure_names:
                return {"success": False, "error": f"Structure '{structure_name}' not found. Available: {structure_names}"}
            
            # Find the actual CST index from MATLAB (1-based)
            matlab_code_find_index = f"""
            struct_index = 0;
            for i = 1:size(cst, 1)
                if strcmp(cst{{i, 2}}, '{structure_name}')
                    struct_index = i;
                    break;
                end
            end
            """
            self.eng.eval(matlab_code_find_index, nargout=0)
            struct_index = int(self.eng.eval("struct_index"))
            
            if struct_index == 0:
                return {"success": False, "error": f"Structure '{structure_name}' not found in CST"}
            
            # Calculate volume conversion
            matlab_code = f"""
            try
                % Get structure voxel indices
                struct_voxels = cst{{struct_index, 4}}{{1}};
                num_voxels = length(struct_voxels);
                
                % Calculate voxel volume in cc
                voxel_volume_mm3 = ct.resolution.x * ct.resolution.y * ct.resolution.z;
                voxel_volume_cc = voxel_volume_mm3 / 1000; % Convert mm³ to cc
                
                % Calculate total structure volume in cc
                total_volume_cc = num_voxels * voxel_volume_cc;
                
                % Calculate conversion
                target_volume_cc = {volume_cc};
                if total_volume_cc > 0
                    volume_percent = 100 * (target_volume_cc / total_volume_cc);
                    volume_fraction = target_volume_cc / total_volume_cc;
                else
                    volume_percent = 0;
                    volume_fraction = 0;
                end
                
                % Ensure within valid range [0, 100] for percent
                volume_percent = max(0, min(100, volume_percent));
                volume_fraction = max(0, min(1, volume_fraction));
                
                conversion_success = true;
                conversion_error = '';
                
            catch ME
                conversion_success = false;
                conversion_error = ME.message;
                volume_percent = 0;
                volume_fraction = 0;
                total_volume_cc = 0;
                num_voxels = 0;
                voxel_volume_cc = 0;
            end
            """
            
            self.eng.eval(matlab_code, nargout=0)
            
            # Get results
            success = bool(self.eng.eval("conversion_success"))
            if not success:
                error_msg = self.eng.eval("conversion_error")
                return {"success": False, "error": f"Volume conversion failed: {error_msg}"}
            
            # Extract conversion results
            volume_percent = float(self.eng.eval("volume_percent"))
            volume_fraction = float(self.eng.eval("volume_fraction"))
            total_volume_cc = float(self.eng.eval("total_volume_cc"))
            num_voxels = int(self.eng.eval("num_voxels"))
            voxel_volume_cc = float(self.eng.eval("voxel_volume_cc"))
            
            return {
                "success": True,
                "structure_name": structure_name,
                "target_volume_cc": volume_cc,
                "volume_percent": volume_percent,
                "volume_fraction": volume_fraction,
                "structure_info": {
                    "total_volume_cc": total_volume_cc,
                    "num_voxels": num_voxels,
                    "voxel_volume_cc": voxel_volume_cc
                },
                "message": f"Converted {volume_cc} cc to {volume_percent:.2f}% for {structure_name}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_overlap_priorities(self, structure_priorities: Dict[str, int] = None) -> Dict[str, Any]:
        """Set minimal overlap priorities: TARGET=1, OAR=2, other=3."""
        if not self.initialized or not self.patient_loaded:
            return {"success": False, "error": "Engine not initialized or no patient loaded"}
            
        try:
            # Set minimal priorities: TARGET=1, OAR=2, other=3
            self.eng.eval("""
            for i = 1:size(cst,1)
                if strcmp(cst{i,3}, 'TARGET')
                    cst{i,5}.Priority = 1;
                elseif strcmp(cst{i,3}, 'OAR')
                    cst{i,5}.Priority = 2;
                else
                    cst{i,5}.Priority = 3;
                end
            end
            cst = matRad_setOverlapPriorities(cst);
            """, nargout=0)
            
            return {"success": True, "message": "Minimal overlap priorities applied (TARGET=1, OAR=2, other=3)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_and_filter_structures(self, provided_prescription_dose: Optional[float] = None) -> Dict[str, Any]:
        """
        LLM-based structure analysis and filtering tool.
        
        Analyzes all structures in the plan, removes helper/evaluation structures,
        keeps only main targets and critical OARs, infers prescription dose from
        structure names, and provides QUANTEC-based OAR sparing guidelines.
        
        Args:
            provided_prescription_dose: Optional prescription dose to validate against inferred dose
            
        Returns:
            Dict with filtered structures, inferred prescription, and OAR guidelines
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB engine not initialized"}
        
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
        
        try:
            # Get all structure information
            struct_info = self.get_structure_names()
            if not struct_info.get("success"):
                return {"success": False, "error": "Could not get structure information"}
            
            # Get all structure names and types
            all_structures = []
            targets = struct_info.get("targets", [])
            oars = struct_info.get("oars", [])
            others = struct_info.get("other", [])
            
            for target in targets:
                all_structures.append({"name": target, "type": "TARGET"})
            for oar in oars:
                all_structures.append({"name": oar, "type": "OAR"})
            for other in others:
                all_structures.append({"name": other, "type": "OTHER"})
            
            # Use LLM to analyze structures
            
            client = OpenAI(base_url="https://eu.api.openai.com/v1")
            
            structure_list = "\n".join([f"- {s['name']} ({s['type']})" for s in all_structures])
            
            prompt = f"""
            You are a clinical radiotherapy expert. Analyze these structures from a treatment plan and provide:

            1. KEEP: Main target structures and critical/important OARs only and any structure that may resemble the outer boundary of the patient (e.g. SKIN, BODY, External, etc.).
            2. REMOVE: Helper structures (eval, union, diff, ring, minus, plus, combined, etc.)
            3. INFER: Prescription dose from target structure names (e.g., PTV6996 = 69.96 Gy, PTV70 = 70 Gy)
            4. PROVIDE: QUANTEC-based OAR sparing guidelines

            STRUCTURES:
            {structure_list}

            Respond in this exact JSON format:
            {{
                "keep_structures": [
                    {{"name": "structure_name", "type": "TARGET|OAR", "rationale": "why keep"}}
                ],
                "remove_structures": [
                    {{"name": "structure_name", "rationale": "why remove"}}
                ],
                "inferred_prescription": {{
                    "primary_dose_gy": 70.0,
                    "target_doses": {{"PTV70": 70.0}},
                    "confidence": "high|medium|low",
                    "rationale": "how dose was inferred"
                }},
                "quantec_guidelines": [
                    {{"structure": "SPINAL_CORD", "constraint": "D_max ≤ 45 Gy"}},
                    {{"structure": "BRAINSTEM", "constraint": "D_max ≤ 54 Gy"}}
                ]
            }}

            Focus on:
            - Keep only essential clinical structures
            - Remove any helper/evaluation/combined structures  
            - Infer dose from numeric patterns in target names
            - Provide standard QUANTEC constraints for identified OARs
            """

            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structure_analysis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "keep_structures": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "rationale": {"type": "string"}
                                    },
                                    "required": ["name", "type", "rationale"]
                                }
                            },
                            "remove_structures": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "rationale": {"type": "string"}
                                    },
                                    "required": ["name", "rationale"]
                                }
                            },
                            "inferred_prescription": {
                                "type": "object",
                                "properties": {
                                    "primary_dose_gy": {"type": "number"},
                                    "target_doses": {"type": "object"},
                                    "confidence": {"type": "string"},
                                    "rationale": {"type": "string"}
                                },
                                "required": ["primary_dose_gy", "target_doses", "confidence", "rationale"]
                            },
                            "quantec_guidelines": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "structure": {"type": "string"},
                                        "constraint": {"type": "string"}
                                    },
                                    "required": ["structure", "constraint"]
                                }
                            }
                        },
                        "required": ["keep_structures", "remove_structures", "inferred_prescription", "quantec_guidelines"]
                    }
                }
            }

            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format=response_format
            )
                    
            analysis = json.loads(response.choices[0].message.content)

            analysis_ = {                
                "inferred_prescription": analysis.get("inferred_prescription", {}),
                "quantec_guidelines": analysis.get("quantec_guidelines", [])
            }            
            
            # Validate inferred prescription against provided dose
            inferred_dose = analysis["inferred_prescription"]["primary_dose_gy"]            
            
            if provided_prescription_dose is not None:
                dose_difference = abs(inferred_dose - provided_prescription_dose)
                if dose_difference > 1.0:  # Allow 5 Gy tolerance
                    return {
                        "success": False, 
                        "error": f"Inferred prescription dose ({inferred_dose} Gy) differs significantly from provided dose ({provided_prescription_dose} Gy). Difference: {dose_difference:.1f} Gy"
                    }
            
            # Remove structures marked for removal
            structures_to_remove = [s["name"] for s in analysis["remove_structures"]]
            
            # Check keep structures for empty voxel indices and add to removal list
            for struct_info in analysis["keep_structures"]:
                struct_name = struct_info["name"]
                try:
                    # Find structure index in CST
                    matlab_code = f"""
                    check_idx = 0;
                    for i = 1:size(cst, 1)
                        if strcmp(cst{{i, 2}}, '{struct_name}')
                            check_idx = i;
                            break;
                        end
                    end
                    """
                    self.eng.eval(matlab_code, nargout=0)
                    check_idx = int(self.eng.eval("check_idx"))
                    
                    if check_idx > 0:
                        # Check if voxel indices (cst{i, 4}{1}) are empty
                        has_voxels = self.eng.eval(f"~isempty(cst{{{check_idx}, 4}}) && ~isempty(cst{{{check_idx}, 4}}{{1}})", nargout=1)
                        if not has_voxels:
                            # Structure has no voxel data, add to removal list
                            if struct_name not in structures_to_remove:
                                structures_to_remove.append(struct_name)
                                
                except Exception as e:
                    # If we can't check the structure, continue
                    continue
            
            removal_results = []
            
            for struct_name in structures_to_remove:
                try:
                    # Find structure index in CST
                    matlab_code = f"""
                    remove_idx = 0;
                    for i = 1:size(cst, 1)
                        if strcmp(cst{{i, 2}}, '{struct_name}')
                            remove_idx = i;
                            break;
                        end
                    end
                    """
                    self.eng.eval(matlab_code, nargout=0)
                    remove_idx = int(self.eng.eval("remove_idx"))
                    
                    if remove_idx > 0:
                        # Remove the structure from CST
                        self.eng.eval(f"cst({remove_idx}, :) = [];", nargout=0)
                        removal_results.append({"name": struct_name, "removed": True})
                    else:
                        removal_results.append({"name": struct_name, "removed": False, "reason": "not found"})
                        
                except Exception as e:
                    removal_results.append({"name": struct_name, "removed": False, "reason": str(e)})
            


            print(f"Removal results: {removal_results}")

            return {
                "success": True,
                "analysis": analysis_,             
                "structures_removed": len([r for r in removal_results if r["removed"]]),
                "structures_kept": len(analysis["keep_structures"])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}    

    def save_plan(self, output_file: str, save_results: bool = True) -> Dict[str, Any]:
        """
        Save the current plan, results, and data to a .mat file.
        
        Args:
            output_file: Path to save the .mat file.
            save_results: If True, save optimization results (requires resultGUI). 
                         If False, save only basic data (ct, cst, pln, stf, dij if available).
            
        Returns:
            Dict with save status information.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Determine what to save based on availability and requirements
            variables_to_save = []
            
            # Always save basic patient data
            variables_to_save.extend(['ct', 'cst'])
            
            # Add plan if it exists
            if self.pln is not None:
                has_pln = self.eng.eval("exist('pln', 'var')", nargout=1)
                if has_pln == 1:
                    variables_to_save.append('pln')
            
            # Add stf if it exists
            if self.stf is not None:
                has_stf = self.eng.eval("exist('stf', 'var')", nargout=1)
                if has_stf == 1:
                    variables_to_save.append('stf')
            
            # Add dij if it exists
            if self.dij is not None:
                has_dij = self.eng.eval("exist('dij', 'var')", nargout=1)                
            
            # Add results if requested and available
            if save_results:
                if self.resultGUI is None:
                    return {"success": False, "error": "No results to save. Run optimization first or set save_results=False."}
                has_results = self.eng.eval("exist('resultGUI', 'var')", nargout=1)
                if has_results == 1:
                    variables_to_save.append('resultGUI')
            
            if not variables_to_save:
                return {"success": False, "error": "No data available to save"}
            
            # Create save command
            variables_str = "', '".join(variables_to_save)
            save_command = f"save('{output_file}', '{variables_str}')"
            
            # Save the data
            print(f"Saving to {output_file}...")
            print(f"Variables: {variables_to_save}")
            self.eng.eval(save_command, nargout=0)

            if has_dij:
                self.eng.eval("save('dij.mat', 'dij', '-v7.3')", nargout=0)
            
            return {
                "success": True,
                "output_file": output_file,
                "variables_saved": variables_to_save,
                "message": f"Data saved successfully to {output_file} (variables: {', '.join(variables_to_save)})"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Function to create matRad engine
def create_matrad_engine(matrad_path: Optional[str] = None) -> MatRadEngine:
    """
    Create and return a matRad engine instance.
    
    Args:
        matrad_path: Path to matRad installation. If None, assumes current directory.
        
    Returns:
        MatRadEngine instance.
    """
    return MatRadEngine(matrad_path) 