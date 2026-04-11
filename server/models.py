from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action Space
# ---------------------------------------------------------------------------

class ClinicalTrialAction(BaseModel):
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
    task_name: str
    protocol_summary: str

    patient_records: List[Dict[str, Any]] = Field(default_factory=list)
    adverse_events: List[Dict[str, Any]] = Field(default_factory=list)

    protocol_text: str = ""
    step: int = 0
    feedback: str = ""

    # ⚠️ MUST NOT BE 0
    partial_score: float = 0.01


# ---------------------------------------------------------------------------
# Step Result
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    observation: ClinicalTrialObservation

    reward: float = 0.01  # strictly > 0; within open interval (0, 1)

    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)