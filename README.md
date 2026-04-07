---
title: ClinicalTrialEnv
emoji: 🏥
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
tags:
  - openenv
  - healthcare
  - clinical-trials
  - medical-monitoring
  - rl-environment
---

# ClinicalTrialEnv 🏥

> **OpenEnv environment — Clinical Trial Protocol Review**

AI agents act as medical monitors: screen patients for eligibility violations,
classify adverse event severity, and critique protocol amendments for regulatory
compliance. A real-world, high-stakes domain with no existing OpenEnv coverage.

---

## 🎯 Tasks

| Task | Difficulty | Description | Steps |
|------|-----------|-------------|-------|
| `eligibility_screening` | 🟢 Easy | 5 patient records, 4 have violations against inclusion/exclusion criteria | 3 |
| `ae_classification` | 🟡 Medium | 7 adverse events, 4 misclassified by grade, 2 missing SAE reports | 4 |
| `protocol_amendment_review` | 🔴 Hard | 6 proposed amendments, find critical safety/GCP/statistical flaws | 5 |

---

## 📐 Action Space

```json
{
  "findings": [
    {
      "finding_type": "eligibility_violation | adverse_event | safety_concern | amendment_recommendation | protocol_deviation",
      "severity": "critical | major | minor | informational",
      "subject_id": "PT-002 or null",
      "description": "What is wrong and why",
      "recommendation": "What to do about it"
    }
  ],
  "rationale": "Overall review summary"
}
```

## 📡 Observation Space

```json
{
  "task_name": "eligibility_screening",
  "protocol_summary": "...",
  "patient_records": [...],
  "adverse_events": [...],
  "protocol_text": "... (hard task only)",
  "step": 1,
  "feedback": "grader feedback from last step",
  "partial_score": 0.40
}
```

---

## 🏆 Reward

Incremental: `reward = new_score - previous_score` at each step.
Partial credit for partial findings. False positive penalty. Empty action: –0.05.

---

## 📊 Scores

| Model | Easy | Medium | Hard | Avg |
|-------|------|--------|------|-----|
| qwen2.5:3b (local) | 0.80 | 0.83 | 0.82 | 0.82 |
| Qwen2.5-72B (HF) | ~0.90 | ~0.85 | ~0.70 | ~0.82 |

---

## 🚀 Quick Start

```bash
# Reset
curl -X POST https://YOUR-SPACE.hf.space/reset \
  -H "Content-Type: application/json" -d '{"task": "eligibility_screening"}'

# Step
curl -X POST https://YOUR-SPACE.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"findings": [{"finding_type":"eligibility_violation","severity":"critical",
       "subject_id":"PT-002","description":"Age 78 exceeds IC-1 max of 75",
       "recommendation":"Remove patient"}], "rationale": "Age violation."}'
```

## ▶️ Run Inference

```bash
pip install openai httpx

export HF_TOKEN=hf_xxx
export CLINICAL_TRIAL_ENV_URL=https://YOUR-SPACE.hf.space
export MY_ENV_V4_TASK=all
python inference.py

# Local Ollama instead:
export API_BASE_URL=http://localhost:11434/v1
export MODEL_NAME=qwen3.5:4b
export HF_TOKEN=ollama
python inference.py
```

---

## 📁 Structure

```
├── Dockerfile
├── openenv.yaml
├── requirements.txt
├── inference.py
└── server/
    ├── app.py         FastAPI server
    ├── environment.py reset/step/state
    ├── models.py      Pydantic models
    └── tasks.py       Tasks + graders
```

## 📜 License — Apache 2.0
