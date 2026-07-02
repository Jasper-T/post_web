ARG DOCKER_HUB_MIRROR=docker.io/library
ARG PYTHON_IMAGE_TAG=3.12-slim

FROM ${DOCKER_HUB_MIRROR}/python:${PYTHON_IMAGE_TAG}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/.venv \
    UV_PROJECT_ENVIRONMENT=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH" \
    PYTHONPATH=/workspace \
    WEB_POST_DATA_ROOT=/data/web-post \
    LOG_LEVEL=INFO \
    LOG_DIR=/data/web-post/logs \
    LOG_ROTATION="10 MB" \
    LOG_RETENTION="14 days"

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /workspace/pyproject.toml
COPY uv.lock /workspace/uv.lock
COPY backend/wheels/ /workspace/backend/wheels/

RUN python -m pip install --upgrade pip uv \
    && uv sync --no-dev --frozen --project /workspace \
    && rm -f /workspace/backend/wheels/dsetkit-0.4.1-py3-none-any.whl

COPY backend/ /workspace/backend/

RUN rm -rf /workspace/backend/wheels \
    && mkdir -p /data/web-post /data/datasets

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3).close()"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

