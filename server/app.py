from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from environment import ClinicalTrialEnv
from models import ClinicalTrialAction
from tasks import TASKS

app = FastAPI(
    title="ClinicalTrialEnv",
    description="OpenEnv environment for Clinical Trial Protocol Review.",
    version="1.0.0",
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_env: Optional[ClinicalTrialEnv] = None


@app.get("/")
def root():
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "healthy", "environment": "ClinicalTrialEnv", "version": "1.0.0"}


@app.get("/style.css")
def get_css():
    return FileResponse(os.path.join(static_path, "style.css"))


@app.get("/main.js")
def get_js():
    return FileResponse(os.path.join(static_path, "main.js"))


# ---------------------- Models ----------------------

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


# ---------------------- Endpoints ----------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "environment": "ClinicalTrialEnv",
        "version": "1.0.0"
    }


@app.get("/metadata")
def metadata():
    return {
        "name": "clinical-trial-env",
        "description": (
            "OpenEnv environment for Clinical Trial Protocol Review. "
            "AI agents act as medical monitors — screening patients for eligibility "
            "violations, classifying adverse event severity, and reviewing protocol amendments."
        ),
        "version": "1.0.0",
        "tasks": [
            {
                "name": t["name"],
                "difficulty": t["difficulty"],
                "description": t["description"],
                "max_steps": t["max_steps"],
                "has_grader": True,
                "grader": t["grader_path"],
                "score_range": [0.01, 0.99],
            }
            for t in TASKS.values()
        ],
    }


@app.get("/schema")
def schema():
    return {
        "action": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "finding_type": {
                                "type": "string",
                                "enum": [
                                    "protocol_deviation",
                                    "adverse_event",
                                    "eligibility_violation",
                                    "safety_concern",
                                    "amendment_recommendation",
                                ],
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "major", "minor", "informational"],
                            },
                            "subject_id": {"type": "string", "nullable": True},
                            "description": {"type": "string"},
                            "recommendation": {"type": "string"},
                        },
                        "required": ["finding_type", "severity", "description", "recommendation"],
                    },
                },
                "rationale": {"type": "string"},
            },
            "required": ["findings", "rationale"],
        },
        "observation": {
            "type": "object",
            "properties": {
                "task_name": {"type": "string"},
                "protocol_summary": {"type": "string"},
                "patient_records": {"type": "array"},
                "adverse_events": {"type": "array"},
                "protocol_text": {"type": "string"},
                "step": {"type": "integer"},
                "feedback": {"type": "string"},
                "partial_score": {"type": "number"},
            },
        },
        "state": {
            "type": "object",
            "properties": {
                "task_name": {"type": "string"},
                "step": {"type": "integer"},
                "done": {"type": "boolean"},
                "current_score": {"type": "number"},
                "n_findings": {"type": "integer"},
                "history": {"type": "array"},
                "elapsed_seconds": {"type": "number"},
            },
        },
    }


@app.post("/mcp")
def mcp(payload: Dict[str, Any] = {}):
    method = payload.get("method", "")
    req_id = payload.get("id", 1)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "clinical-trial-env", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "reset",
                        "description": "Reset environment",
                        "inputSchema": {"type": "object", "properties": {"task": {"type": "string"}}},
                    },
                    {
                        "name": "step",
                        "description": "Submit findings",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "findings": {"type": "array"},
                                "rationale": {"type": "string"},
                            },
                        },
                    },
                ]
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "environment": "clinical-trial-env",
            "version": "1.0.0",
            "tasks": list(TASKS.keys()),
        },
    }


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name": t["name"],
                "difficulty": t["difficulty"],
                "description": t["description"],
                "max_steps": t["max_steps"],
                "has_grader": True,
                "grader": t["grader_path"],
                "score_range": [0.01, 0.99],
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
        raise HTTPException(status_code=400, detail=f"Unknown task '{task}'")

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
        raise HTTPException(status_code=400, detail="Call /reset first.")

    if _env._done:
        raise HTTPException(status_code=400, detail="Episode done.")

    action = ClinicalTrialAction(
        findings=req.findings,
        rationale=req.rationale
    )

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
    main()