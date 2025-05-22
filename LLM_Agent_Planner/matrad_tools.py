"""
MATLAB/matRad Tool Wrappers

This module provides Python wrapper functions for matRad MATLAB functions,
using the MATLAB Engine API for Python to interface with matRad.
"""

import os
import time
import json
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
from pathlib import Path

try:
    import matlab.engine
    MATLAB_AVAILABLE = True
except ImportError:
    MATLAB_AVAILABLE = False
    print("MATLAB Engine for Python not found. Using mock implementations.")


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
            bool: True if successful, False otherwise.
        """
        if not MATLAB_AVAILABLE:
            print("MATLAB Engine not available. Using mock implementation.")
            self.initialized = True
            return True
            
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
            print(f"Error initializing MATLAB Engine: {str(e)}")
            return False
    
    def stop_engine(self) -> bool:
        """
        Stop the MATLAB Engine.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if not MATLAB_AVAILABLE or not self.initialized:
            self.initialized = False
            return True
            
        try:
            self.eng.quit()
            self.initialized = False
            print("MATLAB Engine stopped.")
            return True
        except Exception as e:
            print(f"Error stopping MATLAB Engine: {str(e)}")
            return False
    
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
            
            # Store patient data in class
            self.ct = self.eng.workspace["ct"]
            self.cst = self.eng.workspace["cst"]
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
            # Extract structure information
            result = self.eng.eval("""
            structInfo = struct('targets', {}, 'oars', {}, 'other', {});
            
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2})
                    name = cst{i,2};
                    type = cst{i,3};
                    
                    if strcmp(type, 'TARGET')
                        structInfo.targets{end+1} = name;
                    elseif strcmp(type, 'OAR')
                        structInfo.oars{end+1} = name;
                    else
                        structInfo.other{end+1} = name;
                    end
                end
            end
            
            structInfo
            """, nargout=1)
            
            # Convert MATLAB struct to Python dict
            targets = [str(target) for target in result.get('targets', [])[0]]
            oars = [str(oar) for oar in result.get('oars', [])[0]]
            other = [str(structure) for structure in result.get('other', [])[0]]
            
            return {
                "success": True,
                "targets": targets,
                "oars": oars,
                "other": other
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
            # Set the optimizer
            self.eng.eval(f"""
            if strcmpi('{optimizer_type}', 'fmincon') && matRad_OptimizerFmincon.IsAvailable()
                pln.propOpt.optimizer = 'fmincon';
                
                % Set fmincon parameters
                pln.propOpt.fmincon.MaxIterations = {max_iterations};
                pln.propOpt.fmincon.MaxFunctionEvaluations = {max_iterations * 2};
                pln.propOpt.fmincon.OptimalityTolerance = 1e-3;
                pln.propOpt.fmincon.StepTolerance = 1e-3;
                pln.propOpt.fmincon.Display = 'iter';
            else
                pln.propOpt.optimizer = 'IPOPT';
                % Set IPOPT parameters if needed
            end
            """, nargout=0)
            
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
            
            # Store stf in class
            self.stf = self.eng.workspace["stf"]
            
            # Get beam info
            num_beams = self.eng.eval("numel(stf)", nargout=1)
            total_bixels = self.eng.eval("sum([stf.totalNumOfBixels])", nargout=1)
            
            # Get individual beam details
            beam_info = []
            for i in range(1, num_beams + 1):
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
                "num_beams": num_beams,
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
            
            # Store dij in class
            self.dij = self.eng.workspace["dij"]
            
            # Get matrix info
            dij_dimensions = self.eng.eval("size(dij.physicalDose)", nargout=1)
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
            
            # Find the structure index in the CST
            struct_idx = self.eng.eval(f"""
            idx = 0;
            for i = 1:size(cst, 1)
                if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                    idx = i;
                    break;
                end
            end
            idx
            """, nargout=1)
            
            if struct_idx == 0:
                return {"success": False, "error": f"Structure '{structure_name}' not found in CST"}
                
            # Add the objective
            self.eng.eval(f"""
            % Check if objectives field exists, create if not
            if ~isfield(cst{{{struct_idx},6}}, 'objectiveType') && isempty(cst{{{struct_idx},6}})
                cst{{{struct_idx},6}} = {{}};
            end
            
            % Create objective struct
            newObj = struct();
            newObj.className = '{obj_class}';
            newObj.parameters = {{{dose_value}}};
            newObj.penalty = {penalty};
            
            % Add to CST
            cst{{{struct_idx},6}}{{end+1}} = newObj;
            """, nargout=0)
            
            # Update CST in class
            self.cst = self.eng.workspace["cst"]
            
            # Get current number of objectives
            num_objectives = self.eng.eval(f"numel(cst{{{struct_idx},6}})", nargout=1)
            
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
            
            # Store resultGUI in class
            self.resultGUI = self.eng.workspace["resultGUI"]
            
            # Get optimization results
            obj_val = self.eng.eval("resultGUI.objectiveFunctionValue", nargout=1)
            
            return {
                "success": True,
                "objective_value": obj_val,
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
            
            # Update resultGUI in class
            self.resultGUI = self.eng.workspace["resultGUI"]
            
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
            # Calculate DVH
            if structure_name:
                # Find the structure index
                struct_idx = self.eng.eval(f"""
                idx = 0;
                for i = 1:size(cst, 1)
                    if ~isempty(cst{{i,2}}) && strcmp(cst{{i,2}}, '{structure_name}')
                        idx = i;
                        break;
                    end
                end
                idx
                """, nargout=1)
                
                if struct_idx == 0:
                    return {"success": False, "error": f"Structure '{structure_name}' not found in CST"}
                    
                # Calculate DVH for specific structure
                dvh_data = self.eng.eval(f"""
                % Get dose for this structure
                dose = resultGUI.physicalDose;
                doseInStruct = dose(cst{{{struct_idx},4}}{{1}});
                
                % Calculate DVH
                [dvh, binCenters] = matRad_calcDVH(doseInStruct, cst{{{struct_idx},2}}, 0.1, 0);
                
                % Return data
                struct('name', cst{{{struct_idx},2}}, 'dvh', dvh, 'binCenters', binCenters)
                """, nargout=1)
                
                # Convert to Python
                dvh_values = list(dvh_data['dvh'][0])
                bin_centers = list(dvh_data['binCenters'][0])
                
                return {
                    "success": True,
                    "structure": structure_name,
                    "dvh_values": dvh_values,
                    "bin_centers": bin_centers,
                    "message": f"DVH calculated for {structure_name}"
                }
                
            else:
                # Run plan analysis to get DVH for all structures
                print("Running plan analysis for all structures...")
                self.eng.eval("resultGUI = matRad_planAnalysis(resultGUI,ct,cst,stf,pln);", nargout=0)
                
                # Update resultGUI in class
                self.resultGUI = self.eng.workspace["resultGUI"]
                
                # Check if DVH exists
                has_dvh = self.eng.eval("isfield(resultGUI, 'DVH')", nargout=1)
                
                if not has_dvh:
                    return {"success": False, "error": "DVH calculation failed"}
                    
                return {
                    "success": True,
                    "message": "DVH calculated for all structures"
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
            # Run plan analysis
            print("Running comprehensive plan analysis...")
            self.eng.eval("resultGUI = matRad_planAnalysis(resultGUI,ct,cst,stf,pln);", nargout=0)
            
            # Update resultGUI in class
            self.resultGUI = self.eng.workspace["resultGUI"]
            
            # Check if QI exists
            has_qi = self.eng.eval("isfield(resultGUI, 'QI')", nargout=1)
            
            if not has_qi:
                return {"success": False, "error": "Quality indicators calculation failed"}
                
            # Extract structure information and quality indicators
            structure_metrics = self.eng.eval("""
            metrics = struct('structures', {});
            
            % Get structure names from CST
            structNames = {};
            for i = 1:size(cst,1)
                if ~isempty(cst{i,2})
                    structNames{end+1} = cst{i,2};
                end
            end
            
            % Get metrics for each structure if available
            for i = 1:numel(structNames)
                if isfield(resultGUI.QI, structNames{i})
                    qi = resultGUI.QI.(structNames{i});
                    
                    % Create struct with metrics
                    structMetrics = struct();
                    structMetrics.name = structNames{i};
                    
                    % Add all available metrics
                    if isfield(qi, 'D_mean')
                        structMetrics.mean_dose = qi.D_mean;
                    end
                    
                    if isfield(qi, 'D_max')
                        structMetrics.max_dose = qi.D_max;
                    end
                    
                    if isfield(qi, 'D_min')
                        structMetrics.min_dose = qi.D_min;
                    end
                    
                    % Add standard deviation if available
                    if isfield(qi, 'D_std')
                        structMetrics.std_dose = qi.D_std;
                    end
                    
                    % Add to metrics collection
                    metrics.structures{end+1} = structMetrics;
                end
            end
            
            metrics
            """, nargout=1)
            
            # Convert to Python structure
            metrics_list = []
            for struct_metric in structure_metrics.get('structures', []):
                metric_dict = {
                    'name': str(struct_metric['name']),
                }
                
                # Add available metrics
                if hasattr(struct_metric, 'mean_dose'):
                    metric_dict['mean_dose'] = float(struct_metric['mean_dose'])
                    
                if hasattr(struct_metric, 'max_dose'):
                    metric_dict['max_dose'] = float(struct_metric['max_dose'])
                    
                if hasattr(struct_metric, 'min_dose'):
                    metric_dict['min_dose'] = float(struct_metric['min_dose'])
                    
                if hasattr(struct_metric, 'std_dose'):
                    metric_dict['std_dose'] = float(struct_metric['std_dose'])
                    
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


# Mock implementation for testing without MATLAB
class MockMatRadEngine:
    """Mock implementation of MatRadEngine for testing without MATLAB."""
    
    def __init__(self, matrad_path: Optional[str] = None):
        """Initialize the mock engine."""
        self.matrad_path = matrad_path or os.getcwd()
        self.initialized = False
        self.patient_loaded = False
        self.current_patient = None
        
    def start_engine(self) -> bool:
        """Mock starting the engine."""
        print("MOCK: Starting MatRad engine")
        self.initialized = True
        return True
        
    def stop_engine(self) -> bool:
        """Mock stopping the engine."""
        print("MOCK: Stopping MatRad engine")
        self.initialized = False
        return True
        
    def load_patient(self, patient_file: str) -> Dict[str, Any]:
        """Mock loading a patient dataset."""
        print(f"MOCK: Loading patient from {patient_file}")
        self.patient_loaded = True
        self.current_patient = patient_file
        
        return {
            "success": True, 
            "patient_file": patient_file,
            "ct_dimensions": [1, 1, 1],
            "num_structures": 10,
            "message": "MOCK: Patient data loaded successfully"
        }
        
    def get_structure_names(self) -> Dict[str, Any]:
        """Mock getting structure names."""
        return {
            "success": True,
            "targets": ["PTV70", "PTV63"],
            "oars": ["PAROTID_LT", "PAROTID_RT", "SPINAL_CORD", "BRAIN_STEM"],
            "other": ["SKIN"]
        }
        
    def create_empty_plan(self) -> Dict[str, Any]:
        """Mock creating an empty plan."""
        return {
            "success": True,
            "radiation_mode": "photons",
            "num_fractions": 30,
            "num_beams": 5,
            "gantry_angles": [0, 72, 144, 216, 288],
            "message": "MOCK: Treatment plan initialized successfully"
        }
        
    def set_beam_angles(self, gantry_angles: List[float], couch_angles: Optional[List[float]] = None) -> Dict[str, Any]:
        """Mock setting beam angles."""
        return {
            "success": True,
            "num_beams": len(gantry_angles),
            "gantry_angles": gantry_angles,
            "couch_angles": couch_angles or [0] * len(gantry_angles),
            "message": "MOCK: Beam angles set successfully"
        }
        
    def set_optimizer(self, optimizer_type: str = 'fmincon', max_iterations: int = 100) -> Dict[str, Any]:
        """Mock setting optimizer."""
        return {
            "success": True,
            "optimizer": optimizer_type,
            "max_iterations": max_iterations,
            "message": f"MOCK: Optimizer set to {optimizer_type}"
        }
        
    def generate_beam_geometry(self) -> Dict[str, Any]:
        """Mock generating beam geometry."""
        return {
            "success": True,
            "num_beams": 5,
            "total_bixels": 1000,
            "beam_info": [
                {"beam_id": 1, "gantry_angle": 0, "couch_angle": 0, "num_bixels": 200},
                {"beam_id": 2, "gantry_angle": 72, "couch_angle": 0, "num_bixels": 200},
                {"beam_id": 3, "gantry_angle": 144, "couch_angle": 0, "num_bixels": 200},
                {"beam_id": 4, "gantry_angle": 216, "couch_angle": 0, "num_bixels": 200},
                {"beam_id": 5, "gantry_angle": 288, "couch_angle": 0, "num_bixels": 200}
            ],
            "message": "MOCK: Beam geometry generated successfully"
        }
        
    def calculate_influence_matrix(self) -> Dict[str, Any]:
        """Mock calculating influence matrix."""
        return {
            "success": True,
            "dimensions": [1000, 1000],
            "num_voxels": 1000,
            "calc_time_sec": 5.0,
            "message": "MOCK: Dose influence matrix calculated successfully"
        }
        
    def add_optimization_objective(self, structure_name: str, obj_type: str, 
                                  dose_value: float, penalty: float = 1000.0) -> Dict[str, Any]:
        """Mock adding optimization objective."""
        return {
            "success": True,
            "structure": structure_name,
            "objective_type": obj_type,
            "dose_value": dose_value,
            "penalty": penalty,
            "total_objectives": 1,
            "message": f"MOCK: Added {obj_type} objective to {structure_name}"
        }
        
    def optimize_fluence(self) -> Dict[str, Any]:
        """Mock fluence optimization."""
        return {
            "success": True,
            "objective_value": 85.5,
            "optimization_time_sec": 10.0,
            "message": "MOCK: Fluence optimization completed successfully"
        }
        
    def run_sequencing(self) -> Dict[str, Any]:
        """Mock running sequencing."""
        return {
            "success": True,
            "num_apertures": 50,
            "sequencing_time_sec": 3.0,
            "message": "MOCK: Sequencing completed successfully"
        }
        
    def calculate_dvh(self, structure_name: Optional[str] = None) -> Dict[str, Any]:
        """Mock calculating DVH."""
        if structure_name:
            return {
                "success": True,
                "structure": structure_name,
                "dvh_values": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                "bin_centers": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                "message": f"MOCK: DVH calculated for {structure_name}"
            }
        else:
            return {
                "success": True,
                "message": "MOCK: DVH calculated for all structures"
            }
        
    def evaluate_plan(self) -> Dict[str, Any]:
        """Mock evaluating plan."""
        return {
            "success": True,
            "structure_metrics": [
                {"name": "PTV70", "mean_dose": 70.0, "min_dose": 66.5, "max_dose": 74.0},
                {"name": "PTV63", "mean_dose": 63.0, "min_dose": 60.0, "max_dose": 66.0},
                {"name": "PAROTID_LT", "mean_dose": 20.0, "max_dose": 40.0},
                {"name": "PAROTID_RT", "mean_dose": 22.0, "max_dose": 42.0},
                {"name": "SPINAL_CORD", "max_dose": 30.0},
                {"name": "BRAIN_STEM", "max_dose": 35.0}
            ],
            "message": "MOCK: Plan evaluation completed successfully"
        }
        
    def save_plan(self, output_file: str) -> Dict[str, Any]:
        """Mock saving the plan."""
        return {
            "success": True,
            "output_file": output_file,
            "message": f"MOCK: Plan saved successfully to {output_file}"
        }


# Function to create appropriate engine based on MATLAB availability
def create_matrad_engine(matrad_path: Optional[str] = None) -> Union[MatRadEngine, MockMatRadEngine]:
    """
    Create and return appropriate matRad engine based on MATLAB availability.
    
    Args:
        matrad_path: Path to matRad installation. If None, assumes current directory.
        
    Returns:
        MatRadEngine if MATLAB is available, otherwise MockMatRadEngine.
    """
    if MATLAB_AVAILABLE:
        return MatRadEngine(matrad_path)
    else:
        return MockMatRadEngine(matrad_path) 