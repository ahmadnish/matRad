"""
Guidelines Loader Module

This module provides functionality to load and parse radiotherapy treatment guidelines
from YAML or JSON files, making them accessible to other modules in the LLM agent.
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path


class GuidelinesLoader:
    """
    Class for loading and accessing radiotherapy treatment guidelines.
    
    Handles loading guidelines from YAML or JSON files, resolving structure aliases,
    and providing access to dose constraints and optimization objectives.
    """
    
    def __init__(self, guidelines_dir: Optional[str] = None):
        """
        Initialize the GuidelinesLoader.
        
        Args:
            guidelines_dir: Directory containing guidelines files. If None, 
                          uses the 'guidelines' directory in the same directory as this module.
        """
        if guidelines_dir is None:
            # Default to the 'guidelines' directory in the same directory as this module
            self.guidelines_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guidelines')
        else:
            self.guidelines_dir = guidelines_dir
            
        # Storage for loaded guidelines
        self.guidelines: Dict[str, Any] = {}
        self.structure_map: Dict[str, str] = {}  # Maps structure aliases to canonical names
        self.loaded_files: List[str] = []
    
    def load_guideline(self, filename: str) -> Dict[str, Any]:
        """
        Load a single guideline file.
        
        Args:
            filename: Name of the guideline file (with or without path)
            
        Returns:
            Dict containing the loaded guideline data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported or content is invalid
        """
        # Check if filename includes path, if not, use guidelines_dir
        if os.path.dirname(filename) == '':
            filepath = os.path.join(self.guidelines_dir, filename)
        else:
            filepath = filename
            
        # Check file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Guidelines file not found: {filepath}")
            
        # Load based on file extension
        file_ext = os.path.splitext(filepath)[1].lower()
        
        try:
            if file_ext == '.yaml' or file_ext == '.yml':
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
            elif file_ext == '.json':
                with open(filepath, 'r') as f:
                    data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}. Use .yaml, .yml, or .json")
                
            # Basic validation
            if not isinstance(data, dict):
                raise ValueError(f"Invalid guideline format in {filepath}. Expected a dictionary.")
                
            # Add to loaded guidelines
            guideline_name = os.path.splitext(os.path.basename(filepath))[0]
            self.guidelines[guideline_name] = data
            self.loaded_files.append(filepath)
            
            # Update structure alias mapping
            self._update_structure_map(data)
            
            return data
            
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Error parsing {filepath}: {str(e)}")
    
    def load_all_guidelines(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all guideline files from the guidelines directory.
        
        Returns:
            Dict of loaded guidelines, keyed by guideline name
        """
        self.guidelines = {}
        self.loaded_files = []
        
        if not os.path.exists(self.guidelines_dir):
            print(f"Guidelines directory not found: {self.guidelines_dir}")
            return {}
            
        for filename in os.listdir(self.guidelines_dir):
            if filename.endswith(('.yaml', '.yml', '.json')):
                try:
                    self.load_guideline(filename)
                except Exception as e:
                    print(f"Error loading {filename}: {str(e)}")
                    
        return self.guidelines
    
    def _update_structure_map(self, data: Dict[str, Any]) -> None:
        """
        Update the structure alias mapping from loaded guideline data.
        
        Args:
            data: Loaded guideline data containing structure_aliases
        """
        if 'structure_aliases' not in data:
            return
            
        for canonical_name, aliases in data['structure_aliases'].items():
            for alias in aliases:
                self.structure_map[alias.lower()] = canonical_name
    
    def get_canonical_structure_name(self, structure_name: str) -> str:
        """
        Get the canonical structure name for a given structure name or alias.
        
        Args:
            structure_name: The structure name or alias to look up
            
        Returns:
            The canonical structure name if found in aliases, otherwise the original name
        """
        return self.structure_map.get(structure_name.lower(), structure_name)
    
    def get_constraints(self, structure_name: str) -> List[Dict[str, Any]]:
        """
        Get dose constraints for a given structure.
        
        Args:
            structure_name: Name of the structure to get constraints for
            
        Returns:
            List of constraint dictionaries for the structure, or empty list if none found
        """
        canonical_name = self.get_canonical_structure_name(structure_name)
        
        constraints = []
        for guideline_data in self.guidelines.values():
            # Check for OAR constraints
            if 'organs_at_risk' in guideline_data and canonical_name in guideline_data['organs_at_risk']:
                if 'constraints' in guideline_data['organs_at_risk'][canonical_name]:
                    constraints.extend(guideline_data['organs_at_risk'][canonical_name]['constraints'])
            
            # Check for target constraints
            if 'targets' in guideline_data:
                for target_type, target_data in guideline_data['targets'].items():
                    if isinstance(target_data, dict) and 'prescription_variability' in target_data:
                        # Standard target constraints
                        constraints.append({
                            'type': 'min_dose',
                            'limit': target_data['prescription_variability'].get('min_dose', '95%'),
                            'priority': 'high',
                            'structure_type': 'target'
                        })
                        constraints.append({
                            'type': 'max_dose',
                            'limit': target_data['prescription_variability'].get('max_dose', '107%'),
                            'priority': 'high',
                            'structure_type': 'target'
                        })
        
        return constraints
    
    def get_objectives(self, structure_name: str, prescription_dose: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get optimization objectives for a given structure.
        
        Args:
            structure_name: Name of the structure to get objectives for
            prescription_dose: Optional prescription dose for targets to scale percent-based objectives
            
        Returns:
            List of objective dictionaries for the structure, or empty list if none found
        """
        canonical_name = self.get_canonical_structure_name(structure_name)
        
        objectives = []
        for guideline_data in self.guidelines.values():
            # Check for OAR objectives
            if 'organs_at_risk' in guideline_data and canonical_name in guideline_data['organs_at_risk']:
                if 'objectives' in guideline_data['organs_at_risk'][canonical_name]:
                    objectives.extend(guideline_data['organs_at_risk'][canonical_name]['objectives'])
            
            # Check for target objectives
            if prescription_dose is not None and 'targets' in guideline_data:
                for target_type, target_data in guideline_data['targets'].items():
                    if isinstance(target_data, dict) and 'objectives' in target_data:
                        # Process percent-based objectives for targets
                        for obj in target_data['objectives']:
                            obj_copy = obj.copy()
                            if 'dose_percent' in obj_copy:
                                obj_copy['dose'] = (obj_copy['dose_percent'] / 100) * prescription_dose
                                del obj_copy['dose_percent']
                            objectives.append(obj_copy)
        
        return objectives
    
    def get_beam_arrangements(self, site: str) -> Dict[str, List[float]]:
        """
        Get default beam arrangements for a specific treatment site.
        
        Args:
            site: The treatment site (e.g., 'head_and_neck', 'lung', etc.)
            
        Returns:
            Dict with gantry_angles and couch_angles, or empty dict if site not found
        """
        for guideline_data in self.guidelines.values():
            if 'beam_arrangements' in guideline_data and site in guideline_data['beam_arrangements']:
                return guideline_data['beam_arrangements'][site]
        
        # Return empty dict if no beam arrangement found for site
        return {}
    
    def get_site_prescription(self, site: str, risk_level: str = "high_risk") -> Optional[float]:
        """
        Get the default prescription dose for a specific site and risk level.
        
        Args:
            site: Treatment site (e.g., 'head_and_neck')
            risk_level: Risk level (e.g., 'high_risk', 'intermediate_risk', 'low_risk')
            
        Returns:
            Prescription dose in Gy, or None if not found
        """
        for guideline_data in self.guidelines.values():
            if 'targets' in guideline_data and site in guideline_data['targets']:
                site_data = guideline_data['targets'][site]
                if risk_level in site_data and 'prescription' in site_data[risk_level]:
                    return site_data[risk_level]['prescription']
        
        return None


def load_guidelines(guidelines_dir: Optional[str] = None) -> GuidelinesLoader:
    """
    Convenience function to load all guidelines and return a GuidelinesLoader instance.
    
    Args:
        guidelines_dir: Directory containing guidelines files. If None, 
                      uses the 'guidelines' directory relative to this module.
                      
    Returns:
        Initialized GuidelinesLoader with all guidelines loaded
    """
    loader = GuidelinesLoader(guidelines_dir)
    loader.load_all_guidelines()
    return loader 