"""
Task definitions for the Clinical Trial Protocol Review environment.
Each task has:
  - A scenario (protocol + patient records + adverse events)
  - A deterministic grader returning a score in [0.0, 1.0]
  - A difficulty: easy | medium | hard
"""

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
  IC-1: Age >= 18 and <= 75 years
  IC-2: Histologically confirmed metastatic colorectal adenocarcinoma
  IC-3: ECOG Performance Status 0 or 1
  IC-4: Adequate renal function: eGFR >= 60 mL/min/1.73m2
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

# Ground truth: which subject_ids have violations and what kind
TASK1_GROUND_TRUTH = {
    "PT-002": {"criteria": ["IC-1"], "severity": "critical"},
    "PT-003": {"criteria": ["IC-3", "IC-4"], "severity": "critical"},
    "PT-004": {"criteria": ["IC-5"], "severity": "critical"},
    "PT-005": {"criteria": ["EC-4", "EC-5"], "severity": "critical"},
}


def grade_task1(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    """
    Score Task 1: Eligibility Violation Screening

    Scoring:
    - 20 pts each for correctly identifying PT-002, PT-003, PT-004, PT-005 as having violations
    - PT-003 has 2 violations; partial credit (10 pts) if only one is found
    - PT-005 has 2 violations; partial credit (10 pts) if only one is found
    - PT-001 false-positive flag: -10 pts
    - Max: 100 pts -> normalized to [0.01, 0.99]
    """
    max_pts = 100
    pts = 0
    feedback_parts = []

    # Collect all subject_ids mentioned in findings as violations
    violation_findings = [
        f for f in findings
        if _normalize(f.get("finding_type", "")) in (
            "eligibility_violation", "protocol_deviation"
        )
    ]
    flagged_subjects = {
        str(f.get("subject_id", "")).strip().upper()
        for f in violation_findings
    }

    def desc_of(sid):
        descs = [
            _normalize(f.get("description", "") + " " + f.get("recommendation", ""))
            for f in violation_findings
            if str(f.get("subject_id", "")).upper() == sid
        ]
        return " ".join(descs)

    # PT-002: age violation
    if "PT-002" in flagged_subjects:
        d = desc_of("PT-002")
        if _mentions_any(d, ["age", "78", "ic-1", "inclusion"]):
            pts += 20
            feedback_parts.append("✓ PT-002 age violation correctly identified (+20)")
        else:
            pts += 10
            feedback_parts.append("~ PT-002 flagged but violation type unclear (+10)")
    else:
        feedback_parts.append("✗ PT-002 age violation missed (0)")

    # PT-003: ECOG PS + eGFR
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
    else:
        feedback_parts.append("✗ PT-003 violations missed (0)")

    # PT-004: prior KRAS inhibitor
    if "PT-004" in flagged_subjects:
        d = desc_of("PT-004")
        if _mentions_any(d, ["kras", "sotorasib", "prior", "ic-5", "inhibitor"]):
            pts += 20
            feedback_parts.append("✓ PT-004 prior KRAS inhibitor correctly identified (+20)")
        else:
            pts += 10
            feedback_parts.append("~ PT-004 flagged but violation type unclear (+10)")
    else:
        feedback_parts.append("✗ PT-004 prior KRAS inhibitor violation missed (0)")

    # PT-005: QTcF + CYP3A4
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
    else:
        feedback_parts.append("✗ PT-005 violations missed (0)")

    # False positive penalty: PT-001 flagged
    if "PT-001" in flagged_subjects:
        pts -= 10
        feedback_parts.append("✗ PT-001 incorrectly flagged as violation (-10)")
    else:
        pts += 20
        feedback_parts.append("✓ PT-001 correctly not flagged as violation (+20)")

    score = max(0.01, min(0.99, pts / max_pts))
    feedback = f"Task 1 Score: {pts}/{max_pts} ({score:.2f})\n" + "\n".join(feedback_parts)
    return score, feedback


# ===========================================================================
# TASK 2 — Medium: Adverse Event Severity Misclassification
# ===========================================================================

TASK2_PROTOCOL_SUMMARY = """
TRIAL: CARD-2024-112 Phase III — Drug BX-9 for heart failure (NYHA Class II-III).
SPONSOR: CardioVita Therapeutics
PHASE: III (Randomized, double-blind, placebo-controlled)

ADVERSE EVENT CLASSIFICATION (per ICH E2A):
  Grade 1 (Mild)    — Asymptomatic/mild symptoms; no intervention needed
  Grade 2 (Moderate)— Minimal intervention indicated; limits instrumental ADL
  Grade 3 (Severe)  — Medically significant but not immediately life-threatening;
                       hospitalization or prolongation of hospitalization
  Grade 4 (Life-threatening) — Urgent intervention indicated
  Grade 5 (Fatal)   — Death related to AE

SERIOUS ADVERSE EVENTS (SAEs) must be reported to sponsor within 24 hours if:
  - Any Grade 3-5 event
  - Any hospitalization (even Grade 2)
  - Any event deemed life-threatening by the investigator
  - Congenital anomaly/birth defect
  - Any other medically important event

PROTOCOL NOTE: Dyspnea requiring hospitalization is a pre-specified AE of Special Interest (AESI).
"""

TASK2_ADVERSE_EVENTS = [
    {
        "ae_id": "AE-001",
        "subject_id": "PT-201",
        "event": "Headache",
        "site_reported_grade": 1,
        "hospitalized": False,
        "duration_days": 2,
        "intervention": "Acetaminophen PRN",
        "notes": "Resolved spontaneously.",
        "correct_grade": 1,
        "is_sae": False,
        "misclassified": False,
    },
    {
        "ae_id": "AE-002",
        "subject_id": "PT-202",
        "event": "Severe dyspnea with hospitalization for 3 days",
        "site_reported_grade": 2,   # MISCLASSIFIED — should be Grade 3 SAE + AESI
        "hospitalized": True,
        "duration_days": 3,
        "intervention": "IV diuretics, oxygen supplementation",
        "notes": "Patient hospitalized. Site reported as Grade 2 and did not file SAE report.",
        "correct_grade": 3,
        "is_sae": True,
        "misclassified": True,
        "issue": "Grade downgraded; SAE not filed; AESI not flagged",
    },
    {
        "ae_id": "AE-003",
        "subject_id": "PT-203",
        "event": "Mild peripheral edema",
        "site_reported_grade": 2,
        "hospitalized": False,
        "duration_days": 14,
        "intervention": "Dose reduction",
        "notes": "Managed with dose reduction. Ongoing.",
        "correct_grade": 2,
        "is_sae": False,
        "misclassified": False,
    },
    {
        "ae_id": "AE-004",
        "subject_id": "PT-204",
        "event": "Ventricular tachycardia — 30-second episode, asymptomatic, resolved spontaneously",
        "site_reported_grade": 1,   # MISCLASSIFIED — VT is Grade 3 minimum; potentially Grade 4
        "hospitalized": False,
        "duration_days": 0,
        "intervention": "None; monitored",
        "notes": "Recorded on Holter monitor. Patient unaware. Site classified as Grade 1.",
        "correct_grade": 3,
        "is_sae": True,
        "misclassified": True,
        "issue": "VT always >= Grade 3; SAE report missing; cardiac safety signal",
    },
    {
        "ae_id": "AE-005",
        "subject_id": "PT-205",
        "event": "Acute kidney injury — creatinine 3.2x ULN",
        "site_reported_grade": 2,   # MISCLASSIFIED — creatinine >3x ULN = Grade 3
        "hospitalized": True,
        "duration_days": 5,
        "intervention": "IV fluids, nephrology consult, drug held",
        "notes": "Creatinine peaked at 3.2x ULN. Patient hospitalized. Site reported Grade 2.",
        "correct_grade": 3,
        "is_sae": True,
        "misclassified": True,
        "issue": "Creatinine >3x ULN = Grade 3 per CTCAE; hospitalization = SAE",
    },
    {
        "ae_id": "AE-006",
        "subject_id": "PT-206",
        "event": "Nausea with vomiting, unable to maintain oral intake for 24h",
        "site_reported_grade": 3,
        "hospitalized": True,
        "duration_days": 2,
        "intervention": "IV antiemetics, IV hydration",
        "notes": "SAE filed. Resolved with treatment.",
        "correct_grade": 3,
        "is_sae": True,
        "misclassified": False,
    },
    {
        "ae_id": "AE-007",
        "subject_id": "PT-207",
        "event": "Fatigue — patient reports feeling tired but continues all daily activities",
        "site_reported_grade": 3,   # MISCLASSIFIED — should be Grade 1 (continues ADL)
        "hospitalized": False,
        "duration_days": 7,
        "intervention": "None",
        "notes": "Site over-reported as Grade 3. No hospitalization, no intervention.",
        "correct_grade": 1,
        "is_sae": False,
        "misclassified": True,
        "issue": "Fatigue with no ADL limitation = Grade 1; Grade 3 is over-reporting",
    },
]

TASK2_MISCLASSIFIED_AE_IDS = {"AE-002", "AE-004", "AE-005", "AE-007"}


def grade_task2(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    """
    Score Task 2: Adverse Event Severity Misclassification

    Max 80 pts (+ up to 10 no-FP bonus + 5 rationale bonus = 95 possible):
    - AE-002: up to 15 pts (10 grade correction + 5 AESI/SAE flag)
    - AE-004: up to 17 pts (12 grade correction + 5 cardiac safety signal)
    - AE-005: up to 15 pts (grade + CTCAE reference)
    - AE-007: up to 15 pts (over-reporting identification)
    - No false positives on AE-001, AE-003, AE-006: +10 pts
    - Rationale identifies systemic reporting issues: +5 pts
    - False positive penalty: -8 pts each
    """
    max_pts = 80
    pts = 0
    feedback_parts = []

    ae_findings = [
        f for f in findings
        if _normalize(f.get("finding_type", "")) in (
            "adverse_event", "protocol_deviation", "safety_concern"
        )
    ]

    ae_to_subj = {
        "AE-002": "PT-202", "AE-004": "PT-204",
        "AE-005": "PT-205", "AE-007": "PT-207",
        "AE-001": "PT-201", "AE-003": "PT-203", "AE-006": "PT-206",
    }

    def get_ae_descs(ae_id):
        descs = []
        sid = ae_to_subj.get(ae_id, "")
        for f in ae_findings:
            desc = _normalize(f.get("description", "") + " " + f.get("recommendation", ""))
            subj = str(f.get("subject_id", "")).strip().upper()
            if ae_id.lower() in desc or subj == sid:
                descs.append(desc)
        return " ".join(descs)

    def ae_flagged(ae_id):
        sid = ae_to_subj.get(ae_id, "")
        for f in ae_findings:
            subj = str(f.get("subject_id", "")).strip().upper()
            desc = _normalize(f.get("description", "") + " " + f.get("recommendation", ""))
            if subj == sid or ae_id.lower() in desc:
                return True
        return False

    # AE-002: dyspnea — Grade 2→3, SAE, AESI
    if ae_flagged("AE-002"):
        d = get_ae_descs("AE-002")
        grade_correct = _mentions_any(d, ["grade 3", "grade-3", "grade3", "3", "sae", "serious"])
        aesi_flag = _mentions_any(d, ["aesi", "special interest", "dyspnea", "sae", "hospitali"])
        pts += 10 if grade_correct else 5
        pts += 5 if aesi_flag else 0
        feedback_parts.append(
            f"✓ AE-002 flagged {'with grade+SAE correction' if grade_correct and aesi_flag else 'partially'} "
            f"(+{10 if grade_correct else 5}{'+5 AESI' if aesi_flag else ''})"
        )
    else:
        feedback_parts.append("✗ AE-002 dyspnea misclassification missed (0)")

    # AE-004: VT — Grade 1→3, SAE
    if ae_flagged("AE-004"):
        d = get_ae_descs("AE-004")
        grade_correct = _mentions_any(d, ["grade 3", "grade-3", "3", "sae", "serious", "life"])
        cardiac_signal = _mentions_any(d, ["cardiac", "ventricular", "vt", "safety", "sae"])
        pts += 12 if grade_correct else 6
        pts += 5 if cardiac_signal else 0
        feedback_parts.append(
            f"✓ AE-004 VT flagged {'with cardiac SAE recognition' if cardiac_signal else 'partially'} "
            f"(+{12 if grade_correct else 6}{'+5' if cardiac_signal else ''})"
        )
    else:
        feedback_parts.append("✗ AE-004 VT misclassification missed (0)")

    # AE-005: AKI — Grade 2→3
    if ae_flagged("AE-005"):
        d = get_ae_descs("AE-005")
        grade_correct = _mentions_any(d, ["grade 3", "3", "ctcae", "3x", "uln"])
        pts += 15 if grade_correct else 8
        feedback_parts.append(
            f"✓ AE-005 AKI flagged {'with CTCAE reference' if grade_correct else 'partially'} "
            f"(+{15 if grade_correct else 8})"
        )
    else:
        feedback_parts.append("✗ AE-005 AKI misclassification missed (0)")

    # AE-007: fatigue — Grade 3→1 (over-reporting)
    if ae_flagged("AE-007"):
        d = get_ae_descs("AE-007")
        grade_correct = _mentions_any(d, ["grade 1", "1", "over", "over-report", "adl", "downgrade"])
        pts += 15 if grade_correct else 8
        feedback_parts.append(
            f"✓ AE-007 fatigue over-reporting flagged {'correctly' if grade_correct else 'partially'} "
            f"(+{15 if grade_correct else 8})"
        )
    else:
        feedback_parts.append("✗ AE-007 fatigue over-reporting missed (0)")

    # Bonus for rationale covering systemic issue
    if _mentions_any(rationale, ["sae", "reporting", "systematic", "site training", "pattern"]):
        pts += 5
        feedback_parts.append("✓ Rationale identifies systemic reporting issues (+5)")

    # False positive penalties for correctly classified AEs
    correct_ae_ids = ["AE-001", "AE-003", "AE-006"]
    fp_penalty = 0
    for ae_id in correct_ae_ids:
        if ae_flagged(ae_id):
            pts -= 8
            fp_penalty += 8
            feedback_parts.append(f"✗ {ae_id} incorrectly flagged as misclassified (-8)")

    if fp_penalty == 0:
        pts += 10
        feedback_parts.append("✓ No false positives on correctly classified AEs (+10)")

    score = max(0.01, min(0.99, pts / max_pts))
    feedback = f"Task 2 Score: {pts}/{max_pts} ({score:.2f})\n" + "\n".join(feedback_parts)
    return score, feedback


# ===========================================================================
# TASK 3 — Hard: Comprehensive Protocol Amendment Review
# ===========================================================================

TASK3_PROTOCOL_TEXT = """
PROTOCOL: NEURO-2024-450 Phase II — Drug NX-12 for treatment-resistant depression (TRD)
VERSION: 1.2 (Under Review for Amendment)
SPONSOR: MindBridge Pharmaceuticals

===================================================
SECTION 3: STUDY DESIGN
===================================================
Open-label, single-arm study. No control arm. Duration: 12 weeks active treatment.
Primary endpoint: Change from baseline in MADRS score at Week 8.
Secondary endpoint: Response rate (>=50% MADRS reduction) at Week 12.

PROPOSED CHANGE (Amendment A):
  Extend treatment from 12 -> 24 weeks with no change to primary endpoint timing.

PROPOSED CHANGE (Amendment B):
  Add an optional open-label extension (OLE) of up to 52 weeks for responders.
  Consent for OLE to be obtained at Week 12 visit (same day as eligibility assessment).

===================================================
SECTION 4: PATIENT POPULATION
===================================================
INCLUSION:
  - Age 22-65
  - DSM-5 diagnosis of MDD, current episode resistant to >=2 adequate antidepressant trials
  - MADRS score >=28 at screening AND baseline (within 3 days of screening)
  - Capable of providing informed consent

EXCLUSION:
  - Active suicidal ideation with plan or intent (C-SSRS score >=4)
  - Current or recent (within 6 months) substance use disorder
  - Pregnancy or intent to become pregnant
  - Current use of MAOIs

PROPOSED CHANGE (Amendment C):
  Relax exclusion EC-CSSRS: Allow enrollment of patients with C-SSRS score 4
  (active suicidal ideation WITH plan, WITHOUT intent) if monitored weekly.

===================================================
SECTION 5: SAFETY MONITORING
===================================================
Data Safety Monitoring Board (DSMB): Annual review only.
Suicidality monitoring: C-SSRS at baseline and Week 8.
Blood pressure monitoring: At screening, Week 4, Week 12.

NX-12 KNOWN RISKS (from Phase I):
  - Dose-dependent blood pressure elevation (mean +18 mmHg systolic at max dose)
  - Transient dissociative symptoms in 23% of patients at Weeks 1-2
  - Two cases of hypertensive urgency in Phase I (n=42)

PROPOSED CHANGE (Amendment D):
  Increase DSMB review from annual to quarterly.
  Add BP monitoring at Weeks 2 and 8.

===================================================
SECTION 6: STATISTICAL ANALYSIS PLAN
===================================================
Sample size: N=45 (powered for 80% power to detect 7-point MADRS change)
Analysis population: Per-protocol (PP) only.
Missing data: Last observation carried forward (LOCF).
Interim analysis: None planned.

PROPOSED CHANGE (Amendment E):
  Add a single interim analysis at 50% enrollment for futility only.

===================================================
SECTION 7: INFORMED CONSENT
===================================================
Current consent process: Written informed consent obtained at screening visit.
Consent document revision required for all amendments.

PROPOSED CHANGE (Amendment F):
  Allow verbal consent for the OLE (Amendment B) to reduce patient burden,
  with written consent waived if patient signs OLE enrollment form.
"""

# Ground truth: what a qualified medical monitor / regulatory reviewer would flag
TASK3_GROUND_TRUTH_ISSUES = {
    "amendment_c_safety": {
        "description": "Amendment C allows suicidal patients (C-SSRS>=4) with plan — unacceptable in TRD trial without intensive monitoring infrastructure beyond 'weekly check'",
        "severity": "critical",
        "keywords": ["suicid", "c-ssrs", "amendment c", "safety", "vulnerable", "risk"],
        "weight": 20,
    },
    "amendment_b_consent_timing": {
        "description": "OLE consent at same visit as eligibility assessment creates undue influence / coercion risk",
        "severity": "major",
        "keywords": ["ole", "consent", "same day", "coercio", "undue", "extension", "amendment b"],
        "weight": 15,
    },
    "amendment_f_verbal_consent": {
        "description": "Verbal consent for OLE is insufficient per ICH E6(R2) GCP — written consent required for all interventional trial participation",
        "severity": "critical",
        "keywords": ["verbal", "consent", "gcp", "ich", "written", "waiv", "amendment f"],
        "weight": 15,
    },
    "suicidality_monitoring_gap": {
        "description": "C-SSRS only at baseline and Week 8 is insufficient for TRD + suicidal risk population; should be monthly minimum",
        "severity": "major",
        "keywords": ["c-ssrs", "suicid", "monitoring", "frequen", "weekly", "monthly", "trd"],
        "weight": 15,
    },
    "bp_monitoring_still_insufficient": {
        "description": "Even with Amendment D, BP monitoring is missing at Weeks 1, 6, 16, 20 — given +18 mmHg known risk, monthly monitoring minimum is needed during OLE",
        "severity": "major",
        "keywords": ["blood pressure", "bp", "hypertens", "monitoring", "amendment d", "ole"],
        "weight": 10,
    },
    "no_control_arm_bias": {
        "description": "Open-label single-arm design in TRD (high placebo response ~30-40%) without randomized comparator limits interpretability; Amendment A extension compounds this",
        "severity": "major",
        "keywords": ["open-label", "control", "placebo", "bias", "single-arm", "interpretab"],
        "weight": 10,
    },
    "locf_missing_data": {
        "description": "LOCF is discouraged by FDA/EMA for psychiatric trials; multiple imputation or mixed-model repeated measures preferred",
        "severity": "minor",
        "keywords": ["locf", "missing data", "imputation", "fda", "ema", "mmrm"],
        "weight": 8,
    },
    "interim_analysis_alpha_spend": {
        "description": "Amendment E adds futility interim but no alpha-spending rule or stopping boundaries specified — protocol gap",
        "severity": "minor",
        "keywords": ["interim", "alpha", "spend", "futility", "boundar", "amendment e"],
        "weight": 7,
    },
}


def grade_task3(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    """
    Score Task 3: Comprehensive Protocol Amendment Review
    """
    max_pts = 100
    pts = 0
    feedback_parts = []

    findings_text = _normalize(" ".join(
        f.get("description", "") + " " + f.get("recommendation", "")
        for f in findings
    ))
    rationale_text = _normalize(rationale)
    findings_weight = 0.6 if len(findings) >= 4 else 0.3

    for issue_key, issue in TASK3_GROUND_TRUTH_ISSUES.items():
        keywords = issue["keywords"]
        weight = issue["weight"]
        hits_findings = sum(1 for k in keywords if k in findings_text)
        hits_rationale = sum(1 for k in keywords if k in rationale_text)
        hit_rate = (
            (hits_findings / len(keywords)) * findings_weight +
            (hits_rationale / len(keywords)) * (1 - findings_weight)
        )
        issue_score = hit_rate * weight
        pts += issue_score

        if issue_score > weight * 0.5:
            feedback_parts.append(f"✓ {issue_key} identified (+{issue_score:.1f})")
        else:
            feedback_parts.append(f"✗ {issue_key} missed or insufficient (+{issue_score:.1f})")

    n_recommendations = sum(1 for f in findings if len(f.get("recommendation", "")) > 30)
    if n_recommendations >= 5:
        pts += 5
        feedback_parts.append(f"✓ {n_recommendations} actionable recommendations provided (+5)")
    
    score = max(0.01, min(0.99, pts / max_pts))
    feedback = f"Task 3 Score: {pts:.1f}/{max_pts} ({score:.2f})\n" + "\n".join(feedback_parts)
    return score, feedback


# ===========================================================================
# TASK 4 — Easy/Medium: Medication Reconciliation
# ===========================================================================

TASK4_PROTOCOL_SUMMARY = """
TRIAL: CARD-2024-550 Phase II — Investigational drug RX-9 for Atrial Fibrillation.

PROHIBITED MEDICATIONS:
  - Any Vitamin K Antagonist (VKA), including Warfarin (Coumadin).
  - Strong CYP3A4 inhibitors (e.g., Ketoconazole, Itraconazole).
  - Investigational products from other trials.
"""

TASK4_PATIENT_RECORDS = [
    {
        "subject_id": "PT-401",
        "medications": ["Aspirin", "Lisinopril", "Metformin"],
        "notes": "Compliant patient."
    },
    {
        "subject_id": "PT-402",
        "medications": ["Warfarin", "Amlodipine"], # VIOLATION: Warfarin is a VKA
        "notes": "Patient forgot to mention Warfarin during screening; discovered in pharmacy logs."
    },
    {
        "subject_id": "PT-403",
        "medications": ["RX-9", "Itraconazole"], # VIOLATION: Strong CYP3A4 inhibitor
        "notes": "Fungal infection treated 2 weeks after start."
    },
]


def grade_task4(findings: List[Dict], rationale: str) -> Tuple[float, str]:
    pts = 0.0
    max_pts = 40.0
    feedback = []
    pt402 = [f for f in findings if f.get("subject_id") == "PT-402" and _mentions_any(f.get("description", ""), ["warfarin", "vka", "prohibited"])]
    if pt402:
        pts += 20.0
        feedback.append("✓ Identified PT-402 Warfarin violation.")
    pt403 = [f for f in findings if f.get("subject_id") == "PT-403" and _mentions_any(f.get("description", ""), ["itraconazole", "cyp3a4"])]
    if pt403:
        pts += 20.0
        feedback.append("✓ Identified PT-403 Itraconazole violation.")
    score = max(0.01, min(0.99, pts / max_pts))
    return score, "\n".join(feedback)


# ===========================================================================
# Task registry
# ===========================================================================

TASKS = {
    "eligibility_screening": {
        "name": "eligibility_screening",
        "difficulty": "easy",
        "description": "Identify protocol eligibility violations across 5 patient records for ONCO-2024-301.",
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
        "description": "Review 7 adverse events in CARD-2024-112 and identify all misclassifications.",
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
        "description": "Comprehensively review 6 proposed protocol amendments for NEURO-2024-450 and produce structured findings.",
        "max_steps": 5,
        "protocol_summary": "NEURO-2024-450 Phase II — Drug NX-12 for treatment-resistant depression (TRD). 6 amendments under review.",
        "patient_records": [],
        "adverse_events": [],
        "protocol_text": TASK3_PROTOCOL_TEXT,
        "grader": grade_task3,
    },
    "medication_reconciliation": {
        "name": "medication_reconciliation",
        "difficulty": "medium",
        "description": "Identify prohibited concomitant medications in Atrial Fibrillation trial CARD-2024-550.",
        "max_steps": 3,
        "protocol_summary": TASK4_PROTOCOL_SUMMARY,
        "patient_records": TASK4_PATIENT_RECORDS,
        "adverse_events": [],
        "protocol_text": "",
        "grader": grade_task4,
    },
}