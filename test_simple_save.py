#!/usr/bin/env python3
"""
Simple test to verify save functionality works.
"""

import os
import sys
from pathlib import Path

# Add the LLM_Agent_Planner directory to the path
sys.path.append(str(Path(__file__).parent / "LLM_Agent_Planner"))

from matrad_tools import create_matrad_engine

def test_simple_save():
    print("Testing simple save functionality...")
    
    # Create test results directory
    os.makedirs("test_results", exist_ok=True)
    
    # Initialize matRad engine
    engine = create_matrad_engine()
    
    try:
        # Start the engine
        result = engine.start_engine()
        if not result:
            print("❌ Failed to start matRad engine")
            return
        print("✅ matRad engine started successfully")
        
        # Load patient data
        patient_file = "HandN.mat"
        load_result = engine.load_patient(patient_file)
        if not load_result["success"]:
            print(f"❌ Failed to load patient: {load_result['error']}")
            return
        print(f"✅ Patient loaded successfully")
        
        # Try to save
        save_result = engine.save_plan("test_results/simple_test.mat")
        if save_result["success"]:
            print(f"✅ Save successful: {save_result['message']}")
        else:
            print(f"❌ Save failed: {save_result['error']}")
        
        # Check if file exists
        if os.path.exists("test_results/simple_test.mat"):
            file_size = os.path.getsize("test_results/simple_test.mat")
            print(f"✅ File created: test_results/simple_test.mat ({file_size} bytes)")
        else:
            print("❌ File was not created")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        try:
            engine.stop_engine()
            print("✅ matRad engine stopped")
        except:
            print("⚠️  Warning: Could not stop matRad engine cleanly")

if __name__ == "__main__":
    test_simple_save()
