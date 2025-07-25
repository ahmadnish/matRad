"""
MATLAB/matRad Tool Wrappers

This module provides Python wrapper functions for matRad MATLAB functions,
using the MATLAB Engine API for Python to interface with matRad.
"""

import os
import time
import json
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import math

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
            
            self.initialized = True
            print("matRad initialized successfully.")
            return True
            
        except Exception as e:
            error_msg = f"Error initializing MATLAB Engine: {str(e)}"
            print(error_msg)
            raise RuntimeError(error_msg)
    
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
    
    def create_empty_plan(self) -> Dict[str, Any]:
        """
        Create an empty treatment plan structure.
        
        Returns:
            Dict with plan information or error status.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        try:
            # Create a new plan
            self.eng.eval("""
            pln = struct();
            pln.radiationMode   = 'photons';
            pln.machine         = 'Generic';
            pln.numOfFractions  = 30;
             
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
            """, nargout=0)
            
            # Store plan in class
            self.pln = self.eng.workspace["pln"]
            
            # Return summary information
            gantry_angles = self.eng.eval("pln.propStf.gantryAngles", nargout=1)
            num_beams = self.eng.eval("pln.propStf.numOfBeams", nargout=1)
            
            return {
                "success": True,
                "radiation_mode": "photons",
                "num_fractions": 30,
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
            
            return {
                "success": True,
                "num_beams": len(gantry_angles),
                "gantry_angles": gantry_angles,
                "couch_angles": couch_angles,
                "weights_cleared": True,
                "message": "Beam angles set successfully. Previous optimization weights cleared."
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
            # Calculate dose influence matrix
            print("Calculating dose influence matrix (this may take some time)...")
            start_time = time.time()
            self.eng.eval("dij = matRad_calcDoseInfluence(ct,cst,stf,pln);", nargout=0)
            calc_time = time.time() - start_time
            
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
    
    def add_optimization_objective(self, structure_name: str, obj_type: str, 
                                  dose_value: float, penalty: float = 1000.0) -> Dict[str, Any]:
        """
        Add an optimization objective for a structure.
        
        Args:
            structure_name: Name of the structure to add objective for.
            obj_type: Type of objective ('min_dose', 'max_dose', 'mean_dose', 'square_deviation', etc.)
            dose_value: Dose value in Gy for the objective.
            penalty: Penalty weight for the objective.
            
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
                'min_dose': 'DoseObjectives.matRad_SquaredUnderdosing',
                'max_dose': 'DoseObjectives.matRad_SquaredOverdosing',
                'mean_dose': 'DoseObjectives.matRad_MeanDose',
                'square_deviation': 'DoseObjectives.matRad_SquaredDeviation',
                'eud': 'DoseObjectives.matRad_EUD'
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
            
            # Create the objective struct in MATLAB
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
                "total_objectives": num_objectives,
                "message": f"Added {obj_type} objective to {structure_name}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def optimize_fluence(self, use_previous_weights: bool = False) -> Dict[str, Any]:
        """
        Run fluence optimization based on the current plan and objectives.
        
        Args:
            use_previous_weights: If True and previous weights are available, 
                                use them as initial weights for warm-start optimization.
        
        Returns:
            Dict with optimization results or error status.
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
                # Set the wInit variable in MATLAB workspace
                
                optimization_cmd = "resultGUI = matRad_fluenceOptimization(dij,cst,pln,wInit);"
                start_type = "warm-start"
            else:
                print("Running fluence optimization from scratch...")
                optimization_cmd = "resultGUI = matRad_fluenceOptimization(dij,cst,pln);"
                start_type = "cold-start"
            
            # Run fluence optimization
            start_time = time.time()
            self.eng.eval(optimization_cmd, nargout=0)
            opt_time = time.time() - start_time
            
            # Instead of trying to get the entire resultGUI struct, just keep track that it exists
            # self.resultGUI = self.eng.workspace["resultGUI"]
            self.resultGUI = True  # Just mark that resultGUI exists in MATLAB workspace
            
            # Get optimization result from MATLAB without accessing objectiveFunctionValue
            # We'll check if the optimization actually completed by verifying the resultGUI exists
            has_result = self.eng.eval("exist('resultGUI', 'var')", nargout=1)
            
            if has_result != 1:
                return {"success": False, "error": "Optimization failed to produce results"}
            
            # Store the optimized weights for future use
            try:
                # Extract optimized weights from resultGUI.wUnsequenced
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
            
            return {
                "success": True,
                "optimization_time_sec": opt_time,
                "start_type": start_type,
                "weights_stored": weights_stored,
                "weights_count": weights_count,
                "message": f"Fluence optimization completed successfully ({start_type})"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
        Calculate DVH (Dose-Volume Histogram) for the specified structure or all structures.
        Creates visual DVH plots and detailed clinical assessments.
        
        Args:
            structure_name: Name of the structure to calculate DVH for. If None, calculates for all structures.
            
        Returns:
            Dict with DVH analysis and plot information.
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
        Evaluate the current treatment plan with quality indicators.
        
        Returns:
            Dict with plan evaluation metrics or error status.
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
            
            # Calculate simple metrics directly without using matRad_planAnalysis
            self.eng.eval("""
            try
                % Create metrics struct if it doesn't exist
                if ~isfield(resultGUI, 'metrics')
                    resultGUI.metrics = struct();
                end
                
                % Calculate metrics for each structure
                for i = 1:size(cst,1)
                    if ~isempty(cst{i,2})
                        structName = cst{i,2};
                        structType = cst{i,3};
                        
                        % Get voxel indices for this structure
                        if ~isempty(cst{i,4}) && ~isempty(cst{i,4}{1})
                            voxelIndices = cst{i,4}{1};
                            
                            % Get dose for this structure
                            structDose = resultGUI.physicalDose(voxelIndices);
                            
                            % Calculate basic metrics
                            resultGUI.metrics.(structName).mean = mean(structDose);
                            resultGUI.metrics.(structName).max = max(structDose);
                            resultGUI.metrics.(structName).min = min(structDose);
                            resultGUI.metrics.(structName).std = std(structDose);
                            resultGUI.metrics.(structName).V5 = sum(structDose >= 5) / numel(structDose) * 100;
                            resultGUI.metrics.(structName).V10 = sum(structDose >= 10) / numel(structDose) * 100;
                            resultGUI.metrics.(structName).V20 = sum(structDose >= 20) / numel(structDose) * 100;
                            resultGUI.metrics.(structName).type = structType;
                        end
                    end
                end
            catch ME
                warning('Metrics calculation failed: %s', ME.message);
            end
            """, nargout=0)
            
            # Get structure names
            self.eng.eval("""
            names = {};
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2})
                    names{end+1} = cst{i,2};
                end
            end
            """, nargout=0)
            
            # Access the names variable from MATLAB workspace
            struct_names = self.eng.workspace["names"]
            
            # Check if metrics were calculated
            has_metrics = self.eng.eval("isfield(resultGUI, 'metrics')", nargout=1)
            
            if not has_metrics:
                return {"success": False, "error": "Metrics calculation failed"}
            
            # Get metrics for each structure
            metrics_list = []
            
            if struct_names:
                for name in struct_names:
                    name_str = str(name)
                    
                    # Check if metrics data exists for this structure
                    has_struct_metrics = self.eng.eval(f"isfield(resultGUI.metrics, '{name_str}')", nargout=1)
                    
                    if has_struct_metrics:
                        # Get metrics
                        mean_dose = float(self.eng.eval(f"resultGUI.metrics.{name_str}.mean", nargout=1))
                        max_dose = float(self.eng.eval(f"resultGUI.metrics.{name_str}.max", nargout=1))
                        min_dose = float(self.eng.eval(f"resultGUI.metrics.{name_str}.min", nargout=1))
                        std_dose = float(self.eng.eval(f"resultGUI.metrics.{name_str}.std", nargout=1))
                        struct_type = str(self.eng.eval(f"resultGUI.metrics.{name_str}.type", nargout=1))
                        
                        # Get volume metrics
                        v5 = float(self.eng.eval(f"resultGUI.metrics.{name_str}.V5", nargout=1))
                        v10 = float(self.eng.eval(f"resultGUI.metrics.{name_str}.V10", nargout=1))
                        v20 = float(self.eng.eval(f"resultGUI.metrics.{name_str}.V20", nargout=1))
                        
                        # Create metric dict
                        metric_dict = {
                            'name': name_str,
                            'type': struct_type,
                            'mean_dose': mean_dose,
                            'max_dose': max_dose,
                            'min_dose': min_dose,
                            'std_dose': std_dose,
                            'V5': v5,
                            'V10': v10,
                            'V20': v20
                        }
                            
                        metrics_list.append(metric_dict)
            
            return {
                "success": True,
                "structure_metrics": metrics_list,
                "message": "Plan evaluation completed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_plan(self, output_file: str) -> Dict[str, Any]:
        """
        Save the current plan, results, and data to a .mat file.
        
        Args:
            output_file: Path to save the .mat file.
            
        Returns:
            Dict with save status information.
        """
        if not self.initialized:
            return {"success": False, "error": "MATLAB Engine not initialized"}
            
        if not self.patient_loaded:
            return {"success": False, "error": "No patient data loaded"}
            
        if self.resultGUI is None:
            return {"success": False, "error": "No results to save. Run optimization first."}
            
        try:
            # Save the plan and results
            print(f"Saving plan to {output_file}...")
            self.eng.eval(f"save('{output_file}', 'resultGUI', 'ct', 'cst', 'pln', 'stf', 'dij')", nargout=0)
            
            return {
                "success": True,
                "output_file": output_file,
                "message": f"Plan saved successfully to {output_file}"
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