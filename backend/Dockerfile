ARG DOCKER_HUB_MIRROR=docker.io/library
ARG PYTHON_IMAGE_TAG=3.12-slim

FROM ${DOCKER_HUB_MIRROR}/python:${PYTHON_IMAGE_TAG}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/project \
    FUXING_DATA_ROOT=/data/fuxing \
    LOG_LEVEL=INFO \
    LOG_DIR=/data/fuxing/logs \
    LOG_ROTATION="10 MB" \
    LOG_RETENTION="14 days"

WORKDIR /workspace/project

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
COPY dsetkit-0.4.0-py3-none-any.whl /tmp/dsetkit-0.4.0-py3-none-any.whl

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt \
    && python -m pip install /tmp/dsetkit-0.4.0-py3-none-any.whl \
    && rm -f /tmp/requirements.txt /tmp/dsetkit-0.4.0-py3-none-any.whl

COPY backend/ /workspace/project/backend/

RUN mkdir -p /data/fuxing /data/datasets

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3).close()"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
