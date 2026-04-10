from __future__ import annotations
import sys
import os
from typing import Any, Dict, List, Optional

# Add the current directory to sys.path so we can import tasks
sys.path.insert(0, os.path.dirname(__file__))

import tasks

def eligibility_grader(output: Dict[str, Any], expected: Optional[Any] = None) -> float:
    """External entry point for OpenEnv validator."""
    findings = output.get("findings", [])
    rationale = output.get("rationale", "")
    score, _ = tasks.grade_task1(findings, rationale)
    return score

def ae_grader(output: Dict[str, Any], expected: Optional[Any] = None) -> float:
    findings = output.get("findings", [])
    rationale = output.get("rationale", "")
    score, _ = tasks.grade_task2(findings, rationale)
    return score

def protocol_grader(output: Dict[str, Any], expected: Optional[Any] = None) -> float:
    findings = output.get("findings", [])
    rationale = output.get("rationale", "")
    score, _ = tasks.grade_task3(findings, rationale)
    return score

def medication_grader(output: Dict[str, Any], expected: Optional[Any] = None) -> float:
    findings = output.get("findings", [])
    rationale = output.get("rationale", "")
    score, _ = tasks.grade_task4(findings, rationale)
    return score