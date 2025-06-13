"""
Logger Module for IMRT Planning Agent

This module provides logging functionality to record agent actions,
optimization changes, and plan metrics during the planning process.
"""

import json
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


class PlanningLogger:
    """Logger for recording IMRT planning session activities."""
    
    def __init__(self, session_id: Optional[str] = None, log_dir: str = "logs"):
        """
        Initialize the planning logger.
        
        Args:
            session_id: Unique identifier for the planning session
            log_dir: Directory to store log files
        """
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_file = self.log_dir / f"{self.session_id}.json"
        self.session_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "patient_info": {},
            "planning_steps": [],
            "metrics": [],
            "objectives": [],
            "optimization_history": [],
            "final_results": {}
        }
        
        # Initialize log file
        self._save_log()
    
    def log_action(self, action_type: str, description: str, 
                   parameters: Optional[Dict] = None, 
                   result: Optional[Dict] = None) -> None:
        """
        Log an agent action or planning step.
        
        Args:
            action_type: Type of action (e.g., 'tool_call', 'optimization', 'evaluation')
            description: Human-readable description of the action
            parameters: Parameters used for the action
            result: Result or outcome of the action
        """
        step_entry = {
            "timestamp": datetime.now().isoformat(),
            "step_number": len(self.session_data["planning_steps"]) + 1,
            "action_type": action_type,
            "description": description,
            "parameters": parameters or {},
            "result": result or {},
            "success": result.get("success", True) if result else True
        }
        
        self.session_data["planning_steps"].append(step_entry)
        self._save_log()
    
    def log_patient_info(self, patient_data: Dict[str, Any]) -> None:
        """
        Log patient information.
        
        Args:
            patient_data: Dictionary containing patient information
        """
        self.session_data["patient_info"] = {
            "timestamp": datetime.now().isoformat(),
            **patient_data
        }
        self._save_log()
    
    def log_objective(self, structure_name: str, objective_type: str, 
                     dose_value: float, penalty: float = 1000.0) -> None:
        """
        Log an optimization objective.
        
        Args:
            structure_name: Name of the structure
            objective_type: Type of objective
            dose_value: Dose value in Gy
            penalty: Penalty weight
        """
        objective_entry = {
            "timestamp": datetime.now().isoformat(),
            "structure_name": structure_name,
            "objective_type": objective_type,
            "dose_value": dose_value,
            "penalty": penalty
        }
        
        self.session_data["objectives"].append(objective_entry)
        self._save_log()
    
    def log_optimization_result(self, iteration: int, convergence_data: Dict[str, Any],
                               execution_time: float) -> None:
        """
        Log optimization results.
        
        Args:
            iteration: Optimization iteration number
            convergence_data: Data about optimization convergence
            execution_time: Time taken for optimization
        """
        opt_entry = {
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "execution_time_sec": execution_time,
            "convergence_data": convergence_data
        }
        
        self.session_data["optimization_history"].append(opt_entry)
        self._save_log()
    
    def log_plan_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log plan evaluation metrics.
        
        Args:
            metrics: Dictionary containing plan metrics
        """
        metrics_entry = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
        self.session_data["metrics"].append(metrics_entry)
        self._save_log()
    
    def log_final_results(self, final_data: Dict[str, Any]) -> None:
        """
        Log final planning results.
        
        Args:
            final_data: Final planning session data
        """
        self.session_data["final_results"] = {
            "timestamp": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            **final_data
        }
        self._save_log()
    
    def get_full_log(self) -> Dict[str, Any]:
        """
        Get the complete log data.
        
        Returns:
            Complete session log data
        """
        return self.session_data.copy()
    
    def print_log_summary(self) -> None:
        """Print a summary of the planning session log."""
        print("\n" + "=" * 60)
        print(f"📝 PLANNING SESSION LOG SUMMARY")
        print("=" * 60)
        print(f"Session ID: {self.session_id}")
        print(f"Start Time: {self.session_data['start_time']}")
        
        if self.session_data["patient_info"]:
            print(f"\n👤 Patient Info:")
            for key, value in self.session_data["patient_info"].items():
                if key != "timestamp":
                    print(f"  {key}: {value}")
        
        print(f"\n🔧 Planning Steps: {len(self.session_data['planning_steps'])}")
        for i, step in enumerate(self.session_data["planning_steps"][-5:], 1):  # Show last 5 steps
            status = "✅" if step["success"] else "❌"
            print(f"  {status} {step['action_type']}: {step['description']}")
        
        if len(self.session_data["planning_steps"]) > 5:
            print(f"  ... and {len(self.session_data['planning_steps']) - 5} more steps")
        
        print(f"\n🎯 Objectives Added: {len(self.session_data['objectives'])}")
        for obj in self.session_data["objectives"]:
            print(f"  • {obj['structure_name']}: {obj['objective_type']} = {obj['dose_value']} Gy")
        
        print(f"\n🔄 Optimization Iterations: {len(self.session_data['optimization_history'])}")
        
        print(f"\n📊 Metric Evaluations: {len(self.session_data['metrics'])}")
        
        if self.session_data["final_results"]:
            print(f"\n✅ Final Results Available")
            
        print(f"\n📁 Log File: {self.log_file}")
    
    def export_log(self, output_file: str) -> bool:
        """
        Export log to a specific file.
        
        Args:
            output_file: Path to export the log
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting log: {str(e)}")
            return False
    
    def _save_log(self) -> None:
        """Save the current log data to file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save log file: {str(e)}")


def load_session_log(log_file: str) -> Optional[Dict[str, Any]]:
    """
    Load a planning session log from file.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Log data dictionary or None if failed
    """
    try:
        with open(log_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading log file: {str(e)}")
        return None


def list_session_logs(log_dir: str = "logs") -> List[str]:
    """
    List available session log files.
    
    Args:
        log_dir: Directory containing log files
        
    Returns:
        List of log file paths
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return []
    
    return [str(f) for f in log_path.glob("*.json")]


# Example usage functions
def print_session_summary(log_file: str) -> None:
    """Print a summary of a specific session log."""
    log_data = load_session_log(log_file)
    if log_data:
        logger = PlanningLogger()
        logger.session_data = log_data
        logger.print_log_summary()


if __name__ == "__main__":
    # Example usage
    logger = PlanningLogger("test_session")
    
    # Log some example actions
    logger.log_action("initialization", "Starting MATLAB engine")
    logger.log_patient_info({"patient_file": "HEAD_AND_NECK.mat", "num_structures": 15})
    logger.log_objective("PTV", "min_dose", 50.0, 1000)
    logger.log_optimization_result(1, {"objective_value": 1234.5}, 45.2)
    
    # Print summary
    logger.print_log_summary() 