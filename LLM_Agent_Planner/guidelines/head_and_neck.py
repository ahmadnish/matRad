"""
Head and Neck IMRT Planning Guidelines

This module contains clinical guidelines and objectives for head and neck IMRT planning.
"""

# Sample guidelines to be expanded in future steps
HEAD_AND_NECK_GUIDELINES = {
    "targets": {
        "PTV70": {
            "prescription_dose": 70.0,  # Gy
            "objectives": [
                {"type": "min_dose", "value": 66.5, "priority": "high"},  # 95% of prescription
                {"type": "max_dose", "value": 77.0, "priority": "high"},  # 110% of prescription
            ]
        },
        "PTV63": {
            "prescription_dose": 63.0,  # Gy
            "objectives": [
                {"type": "min_dose", "value": 59.85, "priority": "high"},  # 95% of prescription
                {"type": "max_dose", "value": 69.3, "priority": "medium"},  # 110% of prescription
            ]
        }
    },
    "oars": {
        "SPINAL_CORD": {
            "objectives": [
                {"type": "max_dose", "value": 45.0, "priority": "very_high"},
            ]
        },
        "PAROTID_LT": {
            "objectives": [
                {"type": "mean_dose", "value": 26.0, "priority": "medium"},
            ]
        },
        "PAROTID_RT": {
            "objectives": [
                {"type": "mean_dose", "value": 26.0, "priority": "medium"},
            ]
        },
        "BRAIN_STEM": {
            "objectives": [
                {"type": "max_dose", "value": 54.0, "priority": "high"},
            ]
        }
    },
    "recommended_beam_angles": [0, 72, 144, 216, 288]  # 5-field IMRT setup
} 