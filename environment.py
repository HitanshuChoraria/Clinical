"""
ClinicalTrialEnv — OpenEnv-compliant environment for Clinical Trial Protocol Review.

Implements:
  reset()  → StepResult (initial observation, no reward)
  step()   → StepResult (graded observation, reward, done)
  state()  → dict of current internal state

Episode structure:
  - Each episode corresponds to one task.
  - An agent may take up to max_steps actions.
  - The final step triggers the grader and returns the terminal reward.
  - Intermediate steps return partial rewards based on incremental improvement.
  - The episode ends when done=True (max steps reached or agent signals completion).
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, Optional

from models import ClinicalTrialAction, ClinicalTrialObservation, StepResult
from tasks import TASKS


class ClinicalTrialEnv:
    """
    OpenEnv environment for clinical trial protocol review.
    """

    def __init__(self, task_name: str = "eligibility_screening") -> None:
        if task_name not in TASKS:
            raise ValueError(
                f"Unknown task '{task_name}'. Available: {list(TASKS.keys())}"
            )
        self.task_name = task_name
        self._task = TASKS[task_name]
        self._step = 0
        self._done = False
        self._all_findings: list = []
        self._all_rationale: str = ""
        self._last_score: float = 0.0
        self._last_feedback: str = ""
        self._history: list = []
        self._start_time: float = time.time()

    # ------------------------------------------------------------------
    # OpenEnv required interface
    # ------------------------------------------------------------------

    def reset(self) -> StepResult:
        """Reset the environment and return the initial observation."""
        self._step = 0
        self._done = False
        self._all_findings = []
        self._all_rationale = ""
        self._last_score = 0.0
        self._last_feedback = ""
        self._history = []
        self._start_time = time.time()

        obs = self._make_observation(feedback="", partial_score=0.0)
        return StepResult(observation=obs, reward=0.0, done=False, info={})

    def step(self, action: ClinicalTrialAction) -> StepResult:
        """
        Process one agent action and return the result.
        
        Reward shaping:
          - Intermediate steps: reward = improvement in partial score since last step
          - Final step (max_steps or agent signals done): full grader score
          - Penalty for empty/trivial actions: -0.05
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._step += 1

        # Accumulate findings and rationale across steps
        self._all_findings.extend(action.findings)
        if action.rationale:
            self._all_rationale += " " + action.rationale

        # Run grader to get current score
        grader = self._task["grader"]
        new_score, feedback = grader(self._all_findings, self._all_rationale)

        # Reward = incremental improvement in score
        reward = new_score - self._last_score

        # Penalty for trivial/empty action
        if not action.findings and not action.rationale.strip():
            reward -= 0.05

        # Determine if episode ends
        max_steps = self._task["max_steps"]
        done = self._step >= max_steps

        self._last_score = new_score
        self._last_feedback = feedback
        self._history.append({
            "step": self._step,
            "n_findings": len(action.findings),
            "score_after": new_score,
            "reward": reward,
        })

        if done:
            self._done = True

        obs = self._make_observation(feedback=feedback, partial_score=new_score)
        info = {
            "score": new_score,
            "step": self._step,
            "max_steps": max_steps,
            "grader_feedback": feedback,
        }
        return StepResult(observation=obs, reward=reward, done=done, info=info)

    def state(self) -> Dict[str, Any]:
        """Return current internal state (for debugging/inspection)."""
        return {
            "task_name": self.task_name,
            "step": self._step,
            "done": self._done,
            "current_score": self._last_score,
            "n_findings_accumulated": len(self._all_findings),
            "history": copy.deepcopy(self._history),
            "elapsed_seconds": time.time() - self._start_time,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """Clean up resources (no-op for this environment)."""
        pass
