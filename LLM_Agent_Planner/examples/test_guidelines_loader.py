"""
Test script for guidelines_loader module.

This script demonstrates loading radiotherapy treatment guidelines
and retrieving various types of information from them.
"""

import os
import sys
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guidelines_loader import load_guidelines

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*20} {title} {'='*20}")

def pretty_print(data):
    """Pretty print data."""
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)

def test_guidelines_loader():
    """Test the guidelines loader functionality."""
    print_section("Loading Guidelines")
    
    # Load all guidelines
    loader = load_guidelines()
    
    # Print loaded files
    print(f"Loaded {len(loader.loaded_files)} guideline files:")
    for filepath in loader.loaded_files:
        print(f"  - {os.path.basename(filepath)}")
    
    print_section("Structure Aliases")
    # Print some structure aliases
    for alias in ["SPINAL_CORD", "SpinalCord", "Cord", "PAROTID_LT", "PAROTID_RT"]:
        canonical = loader.get_canonical_structure_name(alias)
        print(f"{alias} -> {canonical}")
    
    print_section("Dose Constraints")
    # Get constraints for various structures
    for structure in ["SPINAL_CORD", "PAROTID_LT", "BRAIN_STEM"]:
        constraints = loader.get_constraints(structure)
        print(f"\nConstraints for {structure}:")
        pretty_print(constraints)
    
    print_section("Optimization Objectives")
    # Get objectives for various structures
    for structure in ["SPINAL_CORD", "PAROTID_LT"]:
        objectives = loader.get_objectives(structure)
        print(f"\nObjectives for {structure}:")
        pretty_print(objectives)
    
    print_section("Target Objectives with Prescription")
    # Get target objectives with prescription
    for structure in ["PTV70", "PTV63"]:
        canonical = loader.get_canonical_structure_name(structure)
        prescription = float(structure.replace("PTV", ""))  # Extract prescription from name
        objectives = loader.get_objectives(structure, prescription)
        print(f"\nObjectives for {structure} with {prescription} Gy prescription:")
        pretty_print(objectives)
    
    print_section("Beam Arrangements")
    # Get beam arrangements for different sites
    for site in ["head_and_neck", "lung", "prostate"]:
        beams = loader.get_beam_arrangements(site)
        print(f"\nBeam arrangement for {site}:")
        pretty_print(beams)
    
    print_section("Site Prescriptions")
    # Get prescription doses for different sites and risk levels
    for site in ["head_and_neck"]:
        for risk_level in ["high_risk", "intermediate_risk", "low_risk"]:
            prescription = loader.get_site_prescription(site, risk_level)
            print(f"{site} - {risk_level}: {prescription} Gy")

if __name__ == "__main__":
    print("Testing guidelines_loader module...")
    test_guidelines_loader() 