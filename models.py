"""
Pydantic models for the Clinical Trial Protocol Review OpenEnv environment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action Space
# ---------------------------------------------------------------------------

class ClinicalTrialAction(BaseModel):
    """
    The action an agent takes when reviewing clinical trial data.

    Fields
    ------
    findings : list of finding dicts, each with:
        - finding_type: "protocol_deviation" | "adverse_event" | "eligibility_violation"
                        | "safety_concern" | "amendment_recommendation"
        - severity: "critical" | "major" | "minor" | "informational"
        - subject_id: patient/subject ID this finding applies to (null if global)
        - description: free-text explanation of the finding
        - recommendation: what action should be taken
    rationale : overall rationale for the review (free text)
    """
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of structured findings from the protocol review"
    )
    rationale: str = Field(
        default="",
        description="Overall rationale and summary of the review"
    )


# ---------------------------------------------------------------------------
# Observation Space
# ---------------------------------------------------------------------------

class ClinicalTrialObservation(BaseModel):
    """
    What the agent sees at each step.

    Fields
    ------
    task_name       : which task is being evaluated
    protocol_summary: high-level trial description
    patient_records : list of patient data dicts
    adverse_events  : list of reported adverse event dicts
    protocol_text   : relevant sections of the trial protocol
    step            : current step number
    feedback        : feedback from previous action (empty on first step)
    partial_score   : running score so far [0.0, 1.0]
    """
    task_name: str
    protocol_summary: str
    patient_records: List[Dict[str, Any]] = Field(default_factory=list)
    adverse_events: List[Dict[str, Any]] = Field(default_factory=list)
    protocol_text: str = ""
    step: int = 0
    feedback: str = ""
    partial_score: float = 0.0


# ---------------------------------------------------------------------------
# Step Result
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    observation: ClinicalTrialObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
