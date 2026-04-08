# SAFE INIT
score = 0.01

...

reward = result.get("reward", 0.01)
reward = min(max(reward, 0.01), 0.99)

...

score = result.get("info", {}).get("score", 0.01)
score = min(max(score, 0.01), 0.99)

...

log_step(step=step, action=str(findings)[:80], reward=0.01, done=True, error=str(e))