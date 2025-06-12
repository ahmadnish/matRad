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
            
            return {
                "success": True,
                "num_beams": len(gantry_angles),
                "gantry_angles": gantry_angles,
                "couch_angles": couch_angles,
                "message": "Beam angles set successfully"
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
    
    def optimize_fluence(self) -> Dict[str, Any]:
        """
        Run fluence optimization based on the current plan and objectives.
        
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
            # Run fluence optimization
            print("Running fluence optimization...")
            start_time = time.time()
            self.eng.eval("resultGUI = matRad_fluenceOptimization(dij,cst,pln);", nargout=0)
            opt_time = time.time() - start_time
            
            # Instead of trying to get the entire resultGUI struct, just keep track that it exists
            # self.resultGUI = self.eng.workspace["resultGUI"]
            self.resultGUI = True  # Just mark that resultGUI exists in MATLAB workspace
            
            # Get optimization result from MATLAB without accessing objectiveFunctionValue
            # We'll check if the optimization actually completed by verifying the resultGUI exists
            has_result = self.eng.eval("exist('resultGUI', 'var')", nargout=1)
            
            if has_result != 1:
                return {"success": False, "error": "Optimization failed to produce results"}
            
            return {
                "success": True,
                "optimization_time_sec": opt_time,
                "message": "Fluence optimization completed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
        
        Args:
            structure_name: Name of the structure to calculate DVH for. If None, calculates for all structures.
            
        Returns:
            Dict with DVH data or error status.
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
            
            # Skip using matRad_planAnalysis since it's causing issues
            # Instead, calculate DVH directly if a specific structure is requested
            if structure_name:
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
                
                # Calculate DVH directly using matRad_calcDVH
                self.eng.eval(f"""
                % Get dose for this structure
                dose = resultGUI.physicalDose;
                
                % Get indices for this structure
                structIndices = cst{{{int(struct_idx)},4}}{{1}};
                
                % Get dose in structure
                doseInStruct = dose(structIndices);
                
                % Calculate DVH
                [dvh, binCenters] = matRad_calcDVH(doseInStruct, '{structure_name}', 0.1, 0);
                
                % Create return structure
                dvhData = struct();
                dvhData.dvh = dvh;
                dvhData.binCenters = binCenters;
                """, nargout=0)
                
                # Access the dvhData variable from MATLAB workspace
                dvh_data = self.eng.workspace["dvhData"]
                
                # Convert to Python lists
                try:
                    dvh_values = list(dvh_data.dvh) if hasattr(dvh_data, 'dvh') else []
                    bin_centers = list(dvh_data.binCenters) if hasattr(dvh_data, 'binCenters') else []
                    
                    return {
                        "success": True,
                        "structure": structure_name,
                        "dvh_values": dvh_values,
                        "bin_centers": bin_centers,
                        "message": f"DVH calculated for {structure_name}"
                    }
                except Exception as e:
                    return {"success": False, "error": f"Error converting DVH data: {str(e)}"}
            else:
                # Calculate basic DVH metrics for all structures
                self.eng.eval("""
                % Basic DVH calculation for all structures
                for i = 1:size(cst,1)
                    if ~isempty(cst{i,2})
                        structName = cst{i,2};
                        structIndices = cst{i,4}{1};
                        
                        if ~isempty(structIndices)
                            % Get dose for this structure
                            doseInStruct = resultGUI.physicalDose(structIndices);
                            
                            % Calculate mean, min, max
                            if ~isfield(resultGUI, 'DVHMetrics')
                                resultGUI.DVHMetrics = struct();
                            end
                            
                            resultGUI.DVHMetrics.(structName).meanDose = mean(doseInStruct);
                            resultGUI.DVHMetrics.(structName).minDose = min(doseInStruct);
                            resultGUI.DVHMetrics.(structName).maxDose = max(doseInStruct);
                        end
                    end
                end
                """, nargout=0)
                
                return {
                    "success": True,
                    "message": "Basic DVH metrics calculated for all structures"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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