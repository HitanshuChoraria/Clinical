"""
FastAPI server for the ClinicalTrialEnv OpenEnv environment.

Endpoints:
  POST /reset          → reset episode, return initial observation
  POST /step           → take action, return step result
  GET  /state          → return current internal state
  GET  /tasks          → list available tasks
  GET  /health         → health check
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add server dir to path
import sys
sys.path.insert(0, os.path.dirname(__file__))

from environment import ClinicalTrialEnv
from models import ClinicalTrialAction, StepResult
from tasks import TASKS

app = FastAPI(
    title="ClinicalTrialEnv",
    description="OpenEnv environment for Clinical Trial Protocol Review — an AI agent evaluates patient records, adverse events, and protocol amendments to identify violations and safety concerns.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single global environment instance (sufficient for benchmark evaluation)
_env: Optional[ClinicalTrialEnv] = None


# ---------------------------------------------------------------------------
# Request / Response schemas for the API
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task: str = "eligibility_screening"


class StepRequest(BaseModel):
    findings: List[Dict[str, Any]] = []
    rationale: str = ""


class ResetResponse(BaseModel):
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]


class StepResponse(BaseModel):
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "environment": "ClinicalTrialEnv", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name": t["name"],
                "difficulty": t["difficulty"],
                "description": t["description"],
                "max_steps": t["max_steps"],
            }
            for t in TASKS.values()
        ]
    }


@app.post("/reset")
def reset(req: ResetRequest = None) -> ResetResponse:
    global _env
    if req is None:
        req = ResetRequest()
    task = req.task if req and req.task else "eligibility_screening"
    if task not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task '{task}'. Available: {list(TASKS.keys())}")
    _env = ClinicalTrialEnv(task_name=task)
    result = _env.reset()
    return ResetResponse(
        observation=result.observation.model_dump(),
        reward=result.reward,
        done=result.done,
        info=result.info,
    )


@app.post("/step")
def step(req: StepRequest) -> StepResponse:
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first to initialize the environment.")
    if _env._done:
        raise HTTPException(status_code=400, detail="Episode is done. Call /reset to start a new episode.")
    action = ClinicalTrialAction(findings=req.findings, rationale=req.rationale)
    result = _env.step(action)
    return StepResponse(
        observation=result.observation.model_dump(),
        reward=result.reward,
        done=result.done,
        info=result.info,
    )


@app.get("/state")
def state() -> Dict[str, Any]:
    global _env
    if _env is None:
        return {"status": "not_initialized"}
    return _env.state()

def main():
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
