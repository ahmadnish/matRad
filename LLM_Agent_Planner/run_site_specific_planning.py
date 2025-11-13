#!/usr/bin/env python3
"""
Site-Specific Treatment Planning Script

This script demonstrates how to use the LLM agent for different cancer sites
with configurable treatment parameters.

Usage examples:
    # Lung cancer planning
    python run_site_specific_planning.py --site lung --dose 60 --fractions 30 --patient lung_patient.mat
    
    # Head and neck planning  
    python run_site_specific_planning.py --site head_and_neck --dose 70 --fractions 35 --patient HandN_newskin.mat
    
    # Prostate planning
    python run_site_specific_planning.py --site prostate --dose 78 --fractions 39 --patient prostate_patient.mat
"""

import argparse
import sys
import os
from test_agent_planning import main, TreatmentConfiguration

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Site-specific radiotherapy treatment planning with LLM agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Lung cancer (60 Gy in 30 fractions)
  python %(prog)s --site lung --dose 60 --fractions 30 --patient lung_patient.mat
  
  # Head and neck cancer (70 Gy in 35 fractions)  
  python %(prog)s --site head_and_neck --dose 70 --fractions 35 --patient HandN_newskin.mat
  
  # Prostate cancer (78 Gy in 39 fractions)
  python %(prog)s --site prostate --dose 78 --fractions 39 --patient prostate_patient.mat
  
  # Breast cancer (50 Gy in 25 fractions)
  python %(prog)s --site breast --dose 50 --fractions 25 --patient breast_patient.mat

Supported cancer sites:
  - lung, nsclc, lung_cancer
  - head_and_neck, head_neck, hnc, oropharynx, larynx
  - prostate
  - breast
        """
    )
    
    parser.add_argument(
        "--site", "-s",
        type=str,
        required=True,
        help="Cancer site (lung, head_and_neck, prostate, breast, etc.)"
    )
    
    parser.add_argument(
        "--dose", "-d",
        type=float,
        required=True,
        help="Total prescription dose in Gy"
    )
    
    parser.add_argument(
        "--fractions", "-f",
        type=int,
        required=True,
        help="Number of treatment fractions"
    )
    
    parser.add_argument(
        "--patient", "-p",
        type=str,
        required=True,
        help="Path to patient data file (.mat)"
    )
    
    parser.add_argument(
        "--technique", "-t",
        type=str,
        default="IMRT",
        choices=["IMRT", "VMAT", "3DCRT", "SBRT"],
        help="Treatment technique (default: IMRT)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=200,
        help="Maximum optimization iterations (default: 200)"
    )
    
    return parser.parse_args()

def validate_inputs(args):
    """Validate input parameters."""
    errors = []
    
    # Check dose per fraction is reasonable
    dose_per_fraction = args.dose / args.fractions
    if dose_per_fraction < 1.0 or dose_per_fraction > 20.0:
        errors.append(f"Dose per fraction ({dose_per_fraction:.1f} Gy) is outside reasonable range (1-20 Gy)")
    
    # Check total dose is reasonable
    if args.dose < 10.0 or args.dose > 100.0:
        errors.append(f"Total dose ({args.dose} Gy) is outside reasonable range (10-100 Gy)")
    
    # Check fractions
    if args.fractions < 1 or args.fractions > 50:
        errors.append(f"Number of fractions ({args.fractions}) is outside reasonable range (1-50)")
    
    # Check patient file exists (if it's not just a filename)
    if "/" in args.patient and not os.path.exists(args.patient):
        errors.append(f"Patient file not found: {args.patient}")
    
    return errors

def print_treatment_summary(args):
    """Print a summary of the treatment configuration."""
    dose_per_fraction = args.dose / args.fractions
    
    print("🎯 TREATMENT CONFIGURATION")
    print("=" * 50)
    print(f"Cancer Site:        {args.site}")
    print(f"Prescription Dose:  {args.dose} Gy")
    print(f"Number of Fractions: {args.fractions}")
    print(f"Dose per Fraction:  {dose_per_fraction:.1f} Gy")
    print(f"Treatment Technique: {args.technique}")
    print(f"Patient File:       {args.patient}")
    print(f"Max Iterations:     {args.max_iterations}")
    print("=" * 50)
    
    # Provide clinical context based on site and fractionation
    if args.site.lower() in ['lung', 'nsclc', 'lung_cancer']:
        if dose_per_fraction > 5.0:
            print("📋 Clinical Context: SBRT/Hypofractionated lung treatment")
        else:
            print("📋 Clinical Context: Conventional fractionation lung cancer")
    elif args.site.lower() in ['head_and_neck', 'head_neck', 'hnc']:
        print("📋 Clinical Context: Head and neck cancer treatment")
    elif args.site.lower() == 'prostate':
        if dose_per_fraction > 3.0:
            print("📋 Clinical Context: Hypofractionated prostate treatment")
        else:
            print("📋 Clinical Context: Conventional fractionation prostate cancer")
    elif args.site.lower() == 'breast':
        print("📋 Clinical Context: Breast cancer treatment")
    
    print()

def main_cli():
    """Main CLI function."""
    args = parse_arguments()
    
    # Validate inputs
    errors = validate_inputs(args)
    if errors:
        print("❌ Input validation errors:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # Print treatment summary
    print_treatment_summary(args)
    
    try:
        # Run the planning session
        main(
            cancer_site=args.site,
            prescription_dose=args.dose,
            num_fractions=args.fractions,
            patient_file=args.patient,
            treatment_technique=args.technique
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Planning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Planning failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main_cli()

