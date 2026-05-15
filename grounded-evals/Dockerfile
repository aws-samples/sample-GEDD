FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

EXPOSE 8080

ENV HOST=0.0.0.0 \
    PORT=8080 \
    NICEGUI_RELOAD=false \
    STORAGE_SECRET=change-me-in-production

CMD ["python", "-m", "grounded_evals.app"]
