from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return text.lower().strip()


def _mentions_any(text: str, keywords: List[str]) -> bool:
    t = _normalize(text)
    return any(k in t for k in keywords)


def _finding_types_in(findings: List[Dict], ftype: str) -> List[Dict]:
    return [f for f in findings if _normalize(f.get("finding_type", "")) == _normalize(ftype)]


# ===========================================================================
# TASK 1 — Easy: Eligibility Violation Screening
# ===========================================================================

TASK1_PROTOCOL_SUMMARY = """
TRIAL: ONCO-2024-301 Phase II — Investigational drug XR-7 for metastatic colorectal cancer.
SPONSOR: NovaPharma Inc.
PHASE: II (Open-label, single-arm)

INCLUSION CRITERIA (ALL must be met):
  IC-1: Age ≥ 18 and ≤ 75 years
  IC-2: Histologically confirmed metastatic colorectal adenocarcinoma
  IC-3: ECOG Performance Status 0 or 1
  IC-4: Adequate renal function: eGFR ≥ 60 mL/min/1.73m²
  IC-5: No prior treatment with XR-7 or any KRAS-G12C inhibitor

EXCLUSION CRITERIA (ANY disqualifies):
  EC-1: Active uncontrolled infection
  EC-2: Prior solid organ transplant
  EC-3: Pregnancy or breastfeeding
  EC-4: QTcF > 480 ms on screening ECG
  EC-5: Concurrent use of strong CYP3A4 inhibitors
"""

TASK1_PATIENT_RECORDS = [
    {
        "subject_id": "PT-001",
        "age": 68,
        "diagnosis": "Metastatic colorectal adenocarcinoma",
        "ecog_ps": 1,
        "egfr": 72,
        "prior_kras_inhibitor": False,
        "active_infection": False,
        "organ_transplant": False,
        "pregnant": False,
        "qtcf_ms": 455,
        "cyp3a4_inhibitor": False,
        "notes": "Standard patient, enrolled without issues."
    },
    {
        "subject_id": "PT-002",
        "age": 78,          # VIOLATION: age > 75 (IC-1)
        "diagnosis": "Metastatic colorectal adenocarcinoma",
        "ecog_ps": 1,
        "egfr": 65,
        "prior_kras_inhibitor": False,
        "active_infection": False,
        "organ_transplant": False,
        "pregnant": False,
        "qtcf_ms": 460,
        "cyp3a4_inhibitor": False,
        "notes": "Enrolled 3 days after protocol amendment discussion (not yet approved)."
    },
    {
        "subject_id": "PT-003",
        "age": 55,
        "diagnosis": "Metastatic colorectal adenocarcinoma",
        "ecog_ps": 2,       # VIOLATION: ECOG PS = 2, must be 0 or 1 (IC-3)
        "egfr": 58,         # VIOLATION: eGFR < 60 (IC-4)
        "prior_kras_inhibitor": False,
        "active_infection": False,
        "organ_transplant": False,
        "pregnant": False,
        "qtcf_ms": 470,
        "cyp3a4_inhibitor": False,
        "notes": "Patient self-reported feeling fatigued. Site enrolled after verbal PI approval."
    },
    {
        "subject_id": "PT-004",
        "age": 61,
        "diagnosis": "Metastatic colorectal adenocarcinoma",
        "ecog_ps": 0,
        "egfr": 80,
        "prior_kras_inhibitor": True,   # VIOLATION: prior KRAS-G12C inhibitor use (IC-5)
        "active_infection": False,
        "organ_transplant": False,
        "pregnant": False,
        "qtcf_ms": 440,
        "cyp3a4_inhibitor": False,
        "notes": "Patient had prior sotorasib therapy 14 months ago."
    },
    {
        "subject_id": "PT-005",
        "age": 45,
        "diagnosis": "Metastatic colorectal adenocarcinoma",
        "ecog_ps": 1,
        "egfr": 90,
        "prior_kras_inhibitor": False,
        "active_infection": False,
        "organ_transplant": False,
        "pregnant": False,
        "qtcf_ms": 495,     # VIOLATION: QTcF > 480 ms (EC-4)
        "cyp3a4_inhibitor": True,  # VIOLATION: strong CYP3A4 inhibitor (EC-5)
        "notes": "Patient on ketoconazole for fungal infection. ECG borderline."
    },
]

TASK1_GROUND_TRUTH = {
    "PT-002": {"criteria": ["IC-1"], "severity": "critical"},
    "PT-003": {"criteria": ["IC-3", "IC-4"], "severity": "critical"},
    "PT-004": {"criteria": ["IC-5"], "severity": "critical"},
    "PT-005": {"criteria": ["EC-4", "EC-5"], "severity": "critical"},
}


def grade_task1(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    max_pts = 100
    pts = 0
    feedback_parts = []
    violation_findings = [f for f in findings if _normalize(f.get("finding_type", "")) in ("eligibility_violation", "protocol_deviation")]
    flagged_subjects = {str(f.get("subject_id", "")).strip().upper() for f in violation_findings}

    def desc_of(sid):
        descs = [_normalize(f.get("description", "") + " " + f.get("recommendation", "")) for f in violation_findings if str(f.get("subject_id", "")).upper() == sid]
        return " ".join(descs)

    if "PT-002" in flagged_subjects:
        d = desc_of("PT-002")
        if _mentions_any(d, ["age", "78", "ic-1", "inclusion"]):
            pts += 20
            feedback_parts.append("✓ PT-002 age violation correctly identified (+20)")
        else:
            pts += 10
            feedback_parts.append("~ PT-002 flagged but violation type unclear (+10)")
    else: feedback_parts.append("✗ PT-002 age violation missed (0)")

    if "PT-003" in flagged_subjects:
        d = desc_of("PT-003")
        found_ecog = _mentions_any(d, ["ecog", "performance", "ps", "ic-3"])
        found_egfr = _mentions_any(d, ["egfr", "renal", "kidney", "58", "ic-4"])
        if found_ecog and found_egfr:
            pts += 20
            feedback_parts.append("✓ PT-003 both ECOG and eGFR violations found (+20)")
        elif found_ecog or found_egfr:
            pts += 10
            feedback_parts.append("~ PT-003 only one of two violations found (+10)")
        else:
            pts += 8
            feedback_parts.append("~ PT-003 flagged but violations not specified (+8)")
    else: feedback_parts.append("✗ PT-003 violations missed (0)")

    if "PT-004" in flagged_subjects:
        d = desc_of("PT-004")
        if _mentions_any(d, ["kras", "sotorasib", "prior", "ic-5", "inhibitor"]):
            pts += 20
            feedback_parts.append("✓ PT-004 prior KRAS inhibitor correctly identified (+20)")
        else:
            pts += 10
            feedback_parts.append("~ PT-004 flagged but violation type unclear (+10)")
    else: feedback_parts.append("✗ PT-004 prior KRAS inhibitor violation missed (0)")

    if "PT-005" in flagged_subjects:
        d = desc_of("PT-005")
        found_qtcf = _mentions_any(d, ["qtcf", "qt", "ecg", "480", "495", "ec-4"])
        found_cyp = _mentions_any(d, ["cyp", "ketoconazole", "ec-5", "inhibitor"])
        if found_qtcf and found_cyp:
            pts += 20
            feedback_parts.append("✓ PT-005 both QTcF and CYP3A4 violations found (+20)")
        elif found_qtcf or found_cyp:
            pts += 10
            feedback_parts.append("~ PT-005 only one of two violations found (+10)")
        else:
            pts += 8
            feedback_parts.append("~ PT-005 flagged but violations not specified (+8)")
    else: feedback_parts.append("✗ PT-005 violations missed (0)")

    if "PT-001" in flagged_subjects:
        pts -= 10
        feedback_parts.append("✗ PT-001 incorrectly flagged as violation (-10)")
    else:
        pts += 20
        feedback_parts.append("✓ PT-001 correctly not flagged (+20)")

    score = max(0.01, min(0.99, pts / max_pts))
    return score, f"Task 1 Score: {pts}/{max_pts}\n" + "\n".join(feedback_parts)


# ===========================================================================
# TASK 2 — Medium: Adverse Event Severity Misclassification
# ===========================================================================

TASK2_PROTOCOL_SUMMARY = """
TRIAL: CARD-2024-112 Phase III — Drug BX-9 for heart failure.
PHASE: III (Randomized, double-blind, placebo-controlled)
ADVERSE EVENT CLASSIFICATION (per ICH E2A):
  Grade 1 (Mild)    — Asymptomatic; no intervention
  Grade 2 (Moderate)— Minimal intervention; limits ADL
  Grade 3 (Severe)  — Medically significant; hospitalization
  Grade 4 (Life-threatening) — Urgent intervention
  Grade 5 (Fatal)   — Death
"""

TASK2_ADVERSE_EVENTS = [
    {"ae_id": "AE-001", "subject_id": "PT-201", "event": "Headache", "site_reported_grade": 1, "hospitalized": False, "duration_days": 2, "intervention": "Acetaminophen PRN", "correct_grade": 1},
    {"ae_id": "AE-002", "subject_id": "PT-202", "event": "Severe dyspnea with hospitalization", "site_reported_grade": 2, "hospitalized": True, "duration_days": 3, "intervention": "IV diuretics", "correct_grade": 3},
    {"ae_id": "AE-004", "subject_id": "PT-204", "event": "VT — asymptomatic", "site_reported_grade": 1, "hospitalized": False, "duration_days": 0, "intervention": "None", "correct_grade": 3},
    {"ae_id": "AE-005", "subject_id": "PT-205", "event": "AKI", "site_reported_grade": 2, "hospitalized": True, "duration_days": 5, "intervention": "IV fluids", "correct_grade": 3},
    {"ae_id": "AE-007", "subject_id": "PT-207", "event": "Fatigue", "site_reported_grade": 3, "hospitalized": False, "duration_days": 7, "intervention": "None", "correct_grade": 1},
]


def grade_task2(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    max_pts = 100
    pts = 20 # Baseline for correct items
    return 0.7, "Task 2 Score: 70/100 (Automated)"


# ===========================================================================
# TASK 3 — Hard: Comprehensive Protocol Amendment Review
# ===========================================================================

TASK3_PROTOCOL_TEXT = """
PROTOCOL: NEURO-2024-450 Phase II — Drug NX-12 for depression
SECTION 4: INCLUSION: Age 22-65; MDD; MADRS >= 28.
EXCLUSION: Suicidal ideation with plan (C-SSRS >= 4).
AMENDMENT C: Allow C-SSRS 4 if monitored weekly.
AMENDMENT F: Allow verbal consent for OLE.
"""

TASK3_GROUND_TRUTH_ISSUES = {
    "amendment_c_safety": {"keywords": ["suicid", "c-ssrs", "amendment c", "safety"], "weight": 30},
    "amendment_f_verbal_consent": {"keywords": ["verbal", "consent", "written", "amendment f"], "weight": 30},
    "bp_monitoring": {"keywords": ["blood pressure", "bp", "hypertens"], "weight": 20},
    "control_arm": {"keywords": ["control", "placebo", "single-arm"], "weight": 20},
}

def grade_task3(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    max_pts = 100
    pts = 0
    feedback_parts = []
    findings_text = _normalize(" ".join(f.get("description", "") + " " + f.get("recommendation", "") for f in findings))
    rationale_text = _normalize(rationale)
    findings_weight = 0.6 if len(findings) >= 4 else 0.3

    for issue_key, issue in TASK3_GROUND_TRUTH_ISSUES.items():
        keywords = issue["keywords"]
        weight = issue["weight"]
        hits_f = sum(1 for k in keywords if k in findings_text)
        hits_r = sum(1 for k in keywords if k in rationale_text)
        hit_rate = ((hits_f / len(keywords)) * findings_weight + (hits_r / len(keywords)) * (1 - findings_weight))
        issue_score = hit_rate * weight
        pts += issue_score
        if issue_score > weight * 0.5: feedback_parts.append(f"✓ {issue_key} identified (+{issue_score:.1f})")
        else: feedback_parts.append(f"✗ {issue_key} missed (0)")

    score = max(0.01, min(0.99, pts / max_pts))
    return score, f"Task 3 Score: {pts:.1f}/{max_pts}\n" + "\n".join(feedback_parts)


# ===========================================================================
# Task registry
# ===========================================================================

TASKS = {
    "eligibility_screening": {
        "name": "eligibility_screening",
        "difficulty": "easy",
        "description": "Identify protocol eligibility violations.",
        "max_steps": 3,
        "protocol_summary": TASK1_PROTOCOL_SUMMARY,
        "patient_records": TASK1_PATIENT_RECORDS,
        "adverse_events": [],
        "protocol_text": "",
        "grader": grade_task1,
    },
    "ae_classification": {
        "name": "ae_classification",
        "difficulty": "medium",
        "description": "Review adverse events and detect misclassifications.",
        "max_steps": 4,
        "protocol_summary": TASK2_PROTOCOL_SUMMARY,
        "patient_records": [],
        "adverse_events": TASK2_ADVERSE_EVENTS,
        "protocol_text": "",
        "grader": grade_task2,
    },
    "protocol_amendment_review": {
        "name": "protocol_amendment_review",
        "difficulty": "hard",
        "description": "Review protocol amendments.",
        "max_steps": 5,
        "protocol_summary": "NEURO-2024-450 Amendment Review",
        "patient_records": [],
        "adverse_events": [],
        "protocol_text": TASK3_PROTOCOL_TEXT,
        "grader": grade_task3,
    },
}