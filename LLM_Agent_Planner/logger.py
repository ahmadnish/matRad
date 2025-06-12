"""
Logger for IMRT Planning Agent

This module implements logging functionality for the IMRT planning agent,
tracking all actions, decisions, and state changes during the planning process.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class PlanningLogger:
    """
    Logger for the radiotherapy planning agent.
    
    Records agent actions, optimization changes, plan metrics, and user interactions
    during the planning process. Logs are stored as structured JSON.
    """
    
    def __init__(self, log_dir: Optional[str] = None, session_id: Optional[str] = None):
        """
        Initialize the PlanningLogger.
        
        Args:
            log_dir: Directory where log files will be stored. If None, 
                    uses 'logs' directory in the same directory as this module.
            session_id: Unique identifier for the planning session. If None,
                       generates a timestamp-based ID.
        """
        if log_dir is None:
            # Default to the 'logs' directory in the same directory as this module
            self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        else:
            self.log_dir = log_dir
            
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Generate session ID if not provided
        if session_id is None:
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            self.session_id = session_id
            
        # Initialize log data structure
        self.log_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "patient_id": None,
            "plan_name": None,
            "entries": []
        }
        
        # Path to the JSON log file
        self.log_file_path = os.path.join(self.log_dir, f"{self.session_id}.json")
        
        # Initialize log file
        self._save_log()
        
        # Log session start
        self.log_action("session_start", "Planning session initialized")
    
    def set_plan_info(self, patient_id: str, plan_name: str) -> None:
        """
        Set the patient ID and plan name for this planning session.
        
        Args:
            patient_id: Patient identifier
            plan_name: Name of the treatment plan
        """
        self.log_data["patient_id"] = patient_id
        self.log_data["plan_name"] = plan_name
        self._save_log()
        
        self.log_action("plan_info_set", 
                        f"Plan info set: Patient {patient_id}, Plan '{plan_name}'",
                        {"patient_id": patient_id, "plan_name": plan_name})
    
    def log_action(self, action_type: str, description: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an agent action.
        
        Args:
            action_type: Type of action (e.g., 'load_patient', 'set_beam_angles', etc.)
            description: Human-readable description of the action
            data: Optional structured data related to the action
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "action",
            "action_type": action_type,
            "description": description,
        }
        
        if data:
            entry["data"] = data
            
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def log_optimization(self, objectives: List[Dict[str, Any]], results: Dict[str, Any]) -> None:
        """
        Log optimization objectives and results.
        
        Args:
            objectives: List of optimization objectives used
            results: Results of the optimization (function value, iterations, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "optimization",
            "objectives": objectives,
            "results": results
        }
        
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log plan evaluation metrics.
        
        Args:
            metrics: Dictionary of plan evaluation metrics
                    (e.g., DVH points, conformity indices, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "metrics",
            "metrics": metrics
        }
        
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def log_suggestion(self, suggestion_type: str, suggestion: str, 
                       reason: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a suggestion made by the agent.
        
        Args:
            suggestion_type: Type of suggestion (e.g., 'beam_arrangement', 'objective_change')
            suggestion: The actual suggestion text
            reason: Reasoning behind the suggestion
            data: Optional structured data related to the suggestion
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "suggestion",
            "suggestion_type": suggestion_type,
            "suggestion": suggestion,
            "reason": reason
        }
        
        if data:
            entry["data"] = data
            
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def log_user_interaction(self, interaction_type: str, user_input: str, 
                           agent_response: Optional[str] = None) -> None:
        """
        Log user interaction with the agent.
        
        Args:
            interaction_type: Type of interaction (e.g., 'query', 'command', 'feedback')
            user_input: Input provided by the user
            agent_response: Optional response from the agent
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "user_interaction",
            "interaction_type": interaction_type,
            "user_input": user_input
        }
        
        if agent_response:
            entry["agent_response"] = agent_response
            
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def log_error(self, error_type: str, error_message: str, 
                stack_trace: Optional[str] = None) -> None:
        """
        Log an error that occurred during the planning process.
        
        Args:
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace for debugging
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": error_type,
            "error_message": error_message
        }
        
        if stack_trace:
            entry["stack_trace"] = stack_trace
            
        self.log_data["entries"].append(entry)
        self._save_log()
    
    def _save_log(self) -> None:
        """
        Save the current log data to the JSON file.
        """
        with open(self.log_file_path, 'w') as f:
            json.dump(self.log_data, f, indent=2)
    
    def get_log(self) -> Dict[str, Any]:
        """
        Get the complete log data.
        
        Returns:
            Dictionary containing all log data
        """
        return self.log_data
    
    def get_entries_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """
        Get log entries filtered by type.
        
        Args:
            entry_type: Type of entries to retrieve (e.g., 'action', 'metrics', 'suggestion')
            
        Returns:
            List of log entries of the specified type
        """
        return [entry for entry in self.log_data["entries"] if entry["type"] == entry_type]
    
    def print_log_summary(self) -> None:
        """
        Print a summary of the log entries.
        """
        entry_types = {}
        for entry in self.log_data["entries"]:
            entry_type = entry["type"]
            if entry_type in entry_types:
                entry_types[entry_type] += 1
            else:
                entry_types[entry_type] = 1
        
        print(f"Log Summary for Session {self.session_id}:")
        print(f"  Patient: {self.log_data['patient_id'] or 'Not set'}")
        print(f"  Plan: {self.log_data['plan_name'] or 'Not set'}")
        print(f"  Start Time: {self.log_data['start_time']}")
        print(f"  Total Entries: {len(self.log_data['entries'])}")
        print("  Entry Types:")
        for entry_type, count in entry_types.items():
            print(f"    - {entry_type}: {count}")
    
    def export_log(self, filepath: Optional[str] = None) -> str:
        """
        Export the log to a specified JSON file.
        
        Args:
            filepath: Path where to save the exported log. If None,
                    uses a timestamped filename in the log directory.
                    
        Returns:
            Path to the exported log file
        """
        if filepath is None:
            export_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(self.log_dir, 
                                   f"export_{self.session_id}_{export_time}.json")
        
        with open(filepath, 'w') as f:
            json.dump(self.log_data, f, indent=2)
            
        return filepath


def create_logger(log_dir: Optional[str] = None, session_id: Optional[str] = None) -> PlanningLogger:
    """
    Convenience function to create a new PlanningLogger instance.
    
    Args:
        log_dir: Directory where log files will be stored
        session_id: Unique identifier for the planning session
        
    Returns:
        Initialized PlanningLogger instance
    """
    return PlanningLogger(log_dir, session_id) 