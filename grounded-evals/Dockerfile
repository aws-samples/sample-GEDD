FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false appuser && \
    mkdir -p /app/data && chown -R appuser:appuser /app

COPY pyproject.toml .
COPY src/ src/
COPY docs/GEDD_optimized.gif docs/

RUN pip install --no-cache-dir -e .

EXPOSE 8080

ENV HOST=0.0.0.0 \
    PORT=8080 \
    NICEGUI_RELOAD=false

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "grounded_evals.app"]
