# Build stage: compilers live here only.
FROM python:3.11-slim AS build
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md* ./
COPY src/ src/
RUN pip install --no-cache-dir --prefix=/install .

# Runtime stage: no compilers, non-root, non-editable install.
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false appuser
COPY --from=build /install /usr/local
COPY docs/GEDD_optimized.gif docs/
RUN chown -R appuser:appuser /app

EXPOSE 8080

# 0.0.0.0 inside the container; the app requires authentication on non-loopback binds.
ENV HOST=0.0.0.0 \
    PORT=8080 \
    NICEGUI_RELOAD=false

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "grounded_evals.app"]
