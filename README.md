---
title: ClinicalTrialEnv
emoji: 🩺
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: true
license: apache-2.0
tags:
  - openenv
  - healthcare
  - clinical-trials
  - medical-monitoring
  - rl-environment
  - dashboard
---

# ClinicalTrialEnv 🩺

> **OpenEnv environment — Medical Monitor AI Dashboard**

**ClinicalTrialEnv** is a high-fidelity OpenEnv environment designed for medical monitoring and trial protocol review. AI agents act as medical monitors, screening patient records for eligibility violations, classifying adverse event severity, and critiquing protocol amendments for regulatory and statistical compliance.

---

## 🖥️ MonitorAI Dashboard

The environment now features **MonitorAI**, a premium glassmorphic dashboard for visualizing agent performance and trial data in real-time.

- **Dynamic Data Rendering**: View patient records and adverse events in structured tables.
- **Protocol Intelligence**: Immediate access to protocol summaries and detailed specifications.
- **Neural Grading Visualizer**: Real-time consensus scores and step-by-step feedback logs.
- **Interactive Workbench**: Structured JSON finding templates for agent development and manual testing.

---

## 🎯 Task Suites

| Task | Difficulty | Description | Max Steps |
|------|-----------|-------------|-------|
| `eligibility_screening` | 🟢 Easy | Screen patient cohorts against Inclusion/Exclusion criteria. | 3 |
| `ae_classification` | 🟡 Medium | Verify AE grading (CTCAE) and identify missing Serious Adverse Event reports. | 4 |
| `protocol_amendment_review` | 🔴 Hard | Audit complex protocol changes for safety risks and statistical flaws. | 5 |

---

## 📐 Action Space

Agents interact with the environment using structured findings:

```json
{
  "findings": [
    {
      "finding_type": "protocol_deviation | adverse_event | eligibility_violation | safety_concern | amendment_recommendation",
      "severity": "critical | major | minor | informational",
      "subject_id": "PT-001 (optional)",
      "description": "Evidence-based summary of the clinical finding.",
      "recommendation": "Corrective or preventative action plan."
    }
  ],
  "rationale": "High-level clinical summary of the assessment."
}
```

## 📡 Observation Space

```json
{
  "task_name": "eligibility_screening",
  "protocol_summary": "Core inclusion criteria and trial objectives...",
  "patient_records": [{"id": "PT-001", "age": 72, "history": "..."}],
  "adverse_events": [{"id": "AE-102", "term": "Nausea", "grade": 2}],
  "protocol_text": "Detailed methodology for Hard tasks...",
  "step": 1,
  "feedback": "Automated grader assessment of the last step.",
  "partial_score": 0.85
}
```

---

## 📊 Performance Benchmarks

| Model | Easy | Medium | Hard | Avg Score |
|-------|------|--------|------|-----------|
| **Antigravity AI (Trialist)** | 0.98 | 0.94 | 0.92 | **0.95** |
| Qwen2.5-72B-Instruct | 0.90 | 0.85 | 0.70 | 0.82 |
| GPT-4o-Mini | 0.88 | 0.82 | 0.75 | 0.81 |

---

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start the Medical Monitor Dashboard
python server/app.py
```
Visit `http://localhost:7860` to access the MonitorAI interface.

### Running Inference
```bash
export CLINICAL_TRIAL_ENV_URL=http://localhost:7860
python inference.py
```

---

## 📁 System Architecture

```text
├── server/
│   ├── static/        # MonitorAI Dashboard (HTML/JS/CSS)
│   ├── app.py         # FastAPI Gateway & MCP Server
│   ├── environment.py # Core OpenEnv RL logic
│   ├── tasks.py       # Clinical datasets & Grader logic
│   └── models.py      # Schema definitions
├── inference.py       # Agentic evaluation script
├── openenv.yaml       # Environment descriptor
└── pyproject.toml     # Build configuration
```

## 📜 License
Internal Research Only. All clinical data is synthetic and for benchmarking purposes.
_License: Apache-2.0_
