# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000 \
    THEORYBERT_HOSTED=1 \
    THEORYBERT_WORKERS=1 \
    THEORYBERT_MAX_JOBS=2 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt
COPY pyproject.toml README.md ./
COPY src/ ./src/
# The full project declares model-training dependencies. The hosted demo uses
# the installed web/runtime set and never silently downloads a model.
RUN pip install --no-deps -e .
COPY data/ ./data/
COPY docs/ ./docs/
COPY configs/ ./configs/
COPY --from=frontend /build/frontend/dist ./frontend/dist
COPY --from=frontend /build/frontend/public/fonts ./frontend/public/fonts
RUN useradd --create-home --uid 10001 theorybert \
    && mkdir -p /app/artifacts/videos \
    && chown -R theorybert:theorybert /app
USER theorybert
ENV THEORYBERT_PARSE_TIMEOUT=45
EXPOSE 10000
CMD ["python", "-m", "theorybert.web", "--host", "0.0.0.0"]
