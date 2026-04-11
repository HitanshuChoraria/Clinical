from __future__ import annotations

import copy
import time
from typing import Any, Dict

from models import ClinicalTrialAction, ClinicalTrialObservation, StepResult
from tasks import TASKS


class ClinicalTrialEnv:
    def __init__(self, task_name: str = "eligibility_screening") -> None:
        if task_name not in TASKS:
            raise ValueError(
                f"Unknown task '{task_name}'. Available: {list(TASKS.keys())}"
            )

        self.task_name = task_name
        self._task = TASKS[task_name]

        self._step = 0
        self._done = False
        self._all_findings = []
        self._all_rationale = ""

        # ⚠️ strictly inside (0,1) — never 0 or 1
        self._last_score = 0.01
        self._last_feedback = ""

        self._history = []
        self._start_time = time.time()

    # ---------------------------------------------------------
    # OpenEnv required interface
    # ---------------------------------------------------------

    def reset(self) -> StepResult:
        self._step = 0
        self._done = False
        self._all_findings = []
        self._all_rationale = ""

        self._last_score = 0.01  # strictly > 0
        self._last_feedback = ""
        self._history = []
        self._start_time = time.time()

        obs = self._make_observation(feedback="", partial_score=0.01)

        return StepResult(
            observation=obs,
            reward=0.01,  # strictly inside (0,1) — status quo minimum
            done=False,
            info={}
        )

    def step(self, action: ClinicalTrialAction) -> StepResult:
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._step += 1

        # Accumulate actions
        self._all_findings.extend(action.findings)

        if action.rationale:
            self._all_rationale += " " + action.rationale

        # Call grader
        grader = self._task["grader"]
        result = grader(self._all_findings, self._all_rationale)

        # Support both return formats
        if isinstance(result, tuple):
            new_score, feedback = result
        else:
            new_score = result
            feedback = ""

        # Clamp score strictly inside (0.01, 0.99) — open interval, never 0 or 1
        new_score = float(new_score)
        new_score = min(max(new_score, 0.01), 0.99)

        # Reward = incremental improvement over previous score
        reward = new_score - self._last_score

        # Clamp reward strictly inside (0.01, 0.99) per OpenEnv open-interval spec
        reward = min(max(reward, 0.01), 0.99)

        # Minimal reward for empty actions — never 0
        if not action.findings and not action.rationale.strip():
            reward = 0.01

        max_steps = self._task["max_steps"]
        done = self._step >= max_steps

        self._last_score = new_score
        self._last_feedback = feedback

        self._history.append({
            "step": self._step,
            "score_after": new_score,
            "reward": reward,
        })

        if done:
            self._done = True

        obs = self._make_observation(
            feedback=feedback,
            partial_score=new_score
        )

        info = {
            "score": new_score,
            "step": self._step,
            "max_steps": max_steps,
            "feedback": feedback,
        }

        return StepResult(
            observation=obs,
            reward=reward,
            done=done,
            info=info
        )

    def state(self) -> Dict[str, Any]:
        return {
            "task_name": self.task_name,
            "step": self._step,
            "done": self._done,
            "current_score": self._last_score,
            "n_findings": len(self._all_findings),
            "history": copy.deepcopy(self._history),
            "elapsed_seconds": time.time() - self._start_time,
        }

    # ---------------------------------------------------------
    # Internal helper
    # ---------------------------------------------------------

    def _make_observation(self, feedback: str, partial_score: float) -> ClinicalTrialObservation:
        task = self._task

        return ClinicalTrialObservation(
            task_name=self.task_name,
            protocol_summary=task["protocol_summary"],
            patient_records=task["patient_records"],
            adverse_events=task["adverse_events"],
            protocol_text=task["protocol_text"],
            step=self._step,
            feedback=feedback,
            partial_score=partial_score,
        )

    def close(self) -> None:
        pass