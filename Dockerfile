FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install curl for uv installer and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification
COPY pyproject.toml .python-version ./

# Copy source code and reference data
COPY src/ ./src/
COPY data/ ./data/

# Install dependencies and package
RUN uv pip install --system -e .

# Create unprivileged service user for sandboxed container runtime
RUN useradd -m -u 1000 salesops && \
    mkdir -p /app/logs /app/traces /app/reports && \
    chown -R salesops:salesops /app

USER salesops

# Default entrypoint
ENTRYPOINT ["salesops-agent"]
CMD ["ask", "Summarize the current sales pipeline by stage."]
