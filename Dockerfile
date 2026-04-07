FROM python:3.11-slim

# ── HuggingFace Spaces metadata ──────────────────────────────────────────────
# Spaces expects the app to listen on port 7860
EXPOSE 7860

# Labels required/recommended for HF Spaces + OpenEnv discovery
LABEL org.opencontainers.image.title="ClinicalTrialEnv" \
      org.opencontainers.image.description="OpenEnv environment for Clinical Trial Protocol Review" \
      org.opencontainers.image.version="1.0.0" \
      space.huggingface.sdk="docker" \
      openenv="true"

# ── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ── App setup ─────────────────────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

# ── Health check (used by HF Spaces readiness probe) ─────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# ── Non-root user (HF Spaces security requirement) ───────────────────────────
RUN useradd -m -u 1000 appuser
USER appuser

# ── Start ─────────────────────────────────────────────────────────────────────
CMD ["python", "server/app.py"]
