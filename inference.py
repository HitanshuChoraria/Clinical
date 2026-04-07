"""
Inference Script — ClinicalTrialEnv Baseline
==============================================

Baseline agent that uses an LLM (via HuggingFace router or any OpenAI-compatible
endpoint) to review clinical trial data and produce structured findings.

MANDATORY environment variables (per OpenEnv spec):
  API_BASE_URL        The API endpoint for the LLM
                      Default: https://router.huggingface.co/v1
  MODEL_NAME          The model identifier to use for inference
                      Default: Qwen/Qwen2.5-72B-Instruct
  HF_TOKEN            Your HuggingFace API token (required for HF router)
  LOCAL_IMAGE_NAME    Docker image name (if using from_docker_image)

  MY_ENV_V4_TASK      Task to run: eligibility_screening | ae_classification |
                      protocol_amendment_review | all
                      Default: eligibility_screening
  MY_ENV_V4_BENCHMARK Benchmark label in logs (default: clinical_trial_env)

Local / Ollama override (optional):
  Set API_BASE_URL=http://localhost:11434/v1 and MODEL_NAME=qwen3.5:4b
  HF_TOKEN can be any non-empty string when using local endpoints.

Usage:
  # HuggingFace (production)
  HF_TOKEN=hf_xxx python inference.py

  # Local Ollama (testing)
  API_BASE_URL=http://localhost:11434/v1 MODEL_NAME=qwen3.5:4b HF_TOKEN=ollama python inference.py

  # All tasks
  MY_ENV_V4_TASK=all HF_TOKEN=hf_xxx python inference.py

Expected baseline scores (Qwen2.5-72B via HF router):
  eligibility_screening     : ~0.75
  ae_classification         : ~0.65
  protocol_amendment_review : ~0.50
"""

import json
import os
import re
import sys
import textwrap
from typing import Any, Dict, List, Optional, Tuple

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration — mirrors the mandatory variables from the OpenEnv spec
# ---------------------------------------------------------------------------

# Defaults match the spec: HF router + a strong open model
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")

# HF_TOKEN is the primary key name per spec; fall back to API_KEY / OPENAI_API_KEY
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")

# Image name for docker-based envs (not used here but kept for spec compliance)
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "clinical-trial-env:latest")

# Task / benchmark config — use MY_ENV_V4_TASK to match spec naming
TASK_NAME  = os.getenv("MY_ENV_V4_TASK",      os.getenv("MY_ENV_TASK", "eligibility_screening"))
BENCHMARK  = os.getenv("MY_ENV_V4_BENCHMARK", "clinical_trial_env")

# Where the environment server is running
ENV_BASE_URL = os.getenv("CLINICAL_TRIAL_ENV_URL", "http://localhost:7860")

MAX_STEPS = {
    "eligibility_screening":     3,
    "ae_classification":         4,
    "protocol_amendment_review": 5,
}

# Per the spec template
TEMPERATURE           = 0.7
MAX_TOKENS            = 2000
SUCCESS_SCORE_THRESHOLD = 0.4


# ---------------------------------------------------------------------------
# Logging — exact format from OpenEnv spec
# [START] task=<task_name> env=<benchmark> model=<model_name>
# [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
# [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    action_summary = action[:120].replace("\n", " ")
    print(
        f"[STEP] step={step} action={action_summary!r} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    # score formatted to 2 decimal places per spec
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Environment client
# ---------------------------------------------------------------------------

def env_reset(task: str) -> Dict[str, Any]:
    r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task": task}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(findings: List[Dict], rationale: str) -> Dict[str, Any]:
    r = httpx.post(
        f"{ENV_BASE_URL}/step",
        json={"findings": findings, "rationale": rationale},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert medical monitor and clinical research associate (CRA) with 15 years of experience
in regulatory affairs, GCP compliance, and clinical trial oversight. You review clinical trial data
to identify protocol deviations, adverse event misclassifications, eligibility violations, and
safety concerns.

Your task is to analyze the provided clinical trial data and produce structured findings.

You MUST respond with valid JSON in exactly this format:
{
  "findings": [
    {
      "finding_type": "<protocol_deviation|adverse_event|eligibility_violation|safety_concern|amendment_recommendation>",
      "severity": "<critical|major|minor|informational>",
      "subject_id": "<patient ID or null if global finding>",
      "description": "<detailed description of the issue>",
      "recommendation": "<specific actionable recommendation>"
    }
  ],
  "rationale": "<overall summary of your review and key concerns>"
}

Rules:
- Be precise and cite specific criteria (e.g., IC-1, EC-4, Grade 3, ICH E6)
- Include ALL violations you find — missing a critical violation is worse than a false positive
- For eligibility violations, state WHICH criterion is violated
- For AE misclassifications, state the correct grade and why
- For amendment reviews, cite ICH/FDA/EMA guidelines where relevant
- Do NOT include findings for patients/events that are correctly handled
""").strip()


def build_user_prompt(obs: Dict[str, Any], step: int, feedback: str) -> str:
    parts = [f"STEP {step} — Task: {obs['task_name']}"]
    parts.append("\n" + "=" * 60)
    parts.append("PROTOCOL SUMMARY:\n" + obs["protocol_summary"])

    if obs.get("patient_records"):
        parts.append("\nPATIENT RECORDS:")
        for pt in obs["patient_records"]:
            parts.append(json.dumps(pt, indent=2))

    if obs.get("adverse_events"):
        parts.append("\nADVERSE EVENTS:")
        for ae in obs["adverse_events"]:
            # Hide ground-truth fields from agent
            ae_visible = {k: v for k, v in ae.items()
                         if k not in ("correct_grade", "is_sae", "misclassified", "issue")}
            parts.append(json.dumps(ae_visible, indent=2))

    if obs.get("protocol_text"):
        parts.append("\nFULL PROTOCOL TEXT:\n" + obs["protocol_text"])

    if feedback:
        parts.append(f"\nPREVIOUS STEP FEEDBACK:\n{feedback}")
        parts.append("(Use this feedback to refine or add to your findings)")

    parts.append(f"\nCurrent partial score: {obs.get('partial_score', 0):.2f}")
    parts.append("\nProvide your structured findings as JSON.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

def _is_local_endpoint() -> bool:
    """Detect if we're talking to a local endpoint (Ollama etc.) vs HF router."""
    return "localhost" in API_BASE_URL or "127.0.0.1" in API_BASE_URL


def _parse_json_response(text: str) -> Dict[str, Any]:
    """
    Robustly parse JSON from model output.
    HF router models return clean JSON; local models may wrap in markdown fences.
    """
    text = text.strip()
    # Strip markdown fences: ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    # If model wrapped in extra text, try to extract the JSON object
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    return json.loads(text)


def get_agent_action(
    client: OpenAI,
    obs: Dict[str, Any],
    step: int,
    feedback: str,
) -> Tuple[List[Dict], str]:
    user_prompt = build_user_prompt(obs, step, feedback)

    # Build kwargs — HF router supports response_format; local Ollama often doesn't
    create_kwargs: Dict[str, Any] = dict(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    if not _is_local_endpoint():
        # HF router + most hosted models support structured JSON output
        create_kwargs["response_format"] = {"type": "json_object"}

    try:
        completion = client.chat.completions.create(**create_kwargs)
        text = (completion.choices[0].message.content or "{}").strip()
        data = _parse_json_response(text)
        findings = data.get("findings", [])
        rationale = data.get("rationale", "")
        return findings, rationale
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return [], f"Error: {exc}"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_task(task_name: str) -> Tuple[float, bool, int, List[float]]:
    if not API_KEY:
        print("[DEBUG] No API key found. Set HF_TOKEN (HF router) or API_KEY (other endpoints).", flush=True)

    client   = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "no-key")
    max_steps = MAX_STEPS.get(task_name, 3)

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    feedback = ""

    try:
        result = env_reset(task_name)
        obs = result["observation"]

        for step in range(1, max_steps + 1):
            if result.get("done"):
                break

            findings, rationale = get_agent_action(client, obs, step, feedback)

            try:
                result = env_step(findings, rationale)
            except Exception as e:
                log_step(step=step, action=str(findings)[:80], reward=0.0, done=True, error=str(e))
                break

            reward = result.get("reward", 0.0)
            done = result.get("done", False)
            feedback = result.get("info", {}).get("grader_feedback", "")
            obs = result["observation"]

            rewards.append(reward)
            steps_taken = step
            score = result.get("info", {}).get("score", 0.0)

            log_step(
                step=step,
                action=f"{len(findings)} findings, rationale={rationale[:60]}",
                reward=reward,
                done=done,
                error=None,
            )

            if done:
                break

        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Task failed: {e}", flush=True)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score, success, steps_taken, rewards


def main():
    tasks_to_run = (
        [TASK_NAME]
        if TASK_NAME != "all"
        else ["eligibility_screening", "ae_classification", "protocol_amendment_review"]
    )

    all_scores = {}
    for task in tasks_to_run:
        print(f"\n{'='*60}", flush=True)
        print(f"Running task: {task}", flush=True)
        print(f"{'='*60}", flush=True)
        score, success, steps, rewards = run_task(task)
        all_scores[task] = score

    if len(all_scores) > 1:
        avg = sum(all_scores.values()) / len(all_scores)
        print(f"\n{'='*60}", flush=True)
        print("FINAL SUMMARY", flush=True)
        for t, s in all_scores.items():
            print(f"  {t}: {s:.3f}", flush=True)
        print(f"  Average: {avg:.3f}", flush=True)
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
