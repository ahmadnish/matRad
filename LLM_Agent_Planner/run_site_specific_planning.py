#!/usr/bin/env python3
"""
Site-Specific Treatment Planning Script

This script uses the LLM agent for different cancer sites. Prescription dose
and fractions are automatically inferred from structure names using the
analyze_and_filter_structures tool.

Usage examples:
    # Plan a patient (prescription inferred from structure names)
    python run_site_specific_planning.py --site head_and_neck --patient ~/matRad/userdata/patients/HNC_001.mat
    
    # Plan with specific model
    python run_site_specific_planning.py --site lung --patient ~/matRad/userdata/patients/LUNG_001.mat --model gpt-4o
"""

import argparse
import sys
import os
from test_agent_planning import main

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Site-specific radiotherapy treatment planning with LLM agent. Prescription dose is inferred from structure names.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plan a patient (prescription inferred from structure names like PTV6996 = 69.96 Gy)
  python %(prog)s --site head_and_neck --patient ~/matRad/userdata/patients/HNC_001.mat
  
  # Plan with specific model
  python %(prog)s --site lung --patient ~/matRad/userdata/patients/LUNG_001.mat --model gpt-4o

Supported cancer sites:
  - lung, nsclc, lung_cancer
  - head_and_neck, head_neck, hnc, oropharynx, larynx
  - prostate
  - breast

Supported models (default: gpt-5.1):
  OpenAI: gpt-5.1, gpt-5, gpt-4o, gpt-4o-mini, gpt-4-turbo
  Anthropic: claude-sonnet-4-5-20250929, claude-opus-4-1-20250805, claude-haiku-4-5-20251001, claude-3-5-sonnet-latest
        """
    )
    
    parser.add_argument(
        "--site", "-s",
        type=str,
        required=True,
        help="Cancer site (lung, head_and_neck, prostate, breast, etc.)"
    )
    
    parser.add_argument(
        "--patient", "-p",
        type=str,
        required=True,
        help="Path to patient data file (.mat), e.g., ~/matRad/userdata/patients/HNC_001.mat"
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
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="gpt-5.1",
        help="LLM model to use (default: gpt-5.1). Options: gpt-5.1, gpt-5, gpt-4o, claude-sonnet-4-5-20250929, claude-opus-4-1-20250805, claude-haiku-4-5-20251001, etc."
    )
    
    return parser.parse_args()


def print_treatment_summary(args):
    """Print a summary of the treatment configuration."""
    print("🎯 TREATMENT CONFIGURATION")
    print("=" * 50)
    print(f"Cancer Site:        {args.site}")
    print(f"Prescription:       Will be inferred from structure names")
    print(f"Treatment Technique: {args.technique}")
    print(f"LLM Model:          {args.model}")
    print(f"Patient File:       {os.path.expanduser(args.patient)}")
    print(f"Max Iterations:     {args.max_iterations}")
    print("=" * 50)
    print("📋 Note: Prescription dose and fractions will be inferred")
    print("   from target structure names (e.g., PTV6996 = 69.96 Gy)")
    print()

def main_cli():
    """Main CLI function."""
    args = parse_arguments()
    
    # Expand user path
    patient_file = os.path.expanduser(args.patient)
    
    # Print treatment summary
    print_treatment_summary(args)
    
    try:
        # Run the planning session (prescription will be inferred)
        main(
            cancer_site=args.site,
            patient_file=patient_file,
            treatment_technique=args.technique,
            model=args.model
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Planning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Planning failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main_cli()

