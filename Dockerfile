FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY constraints-docker.txt pyproject.toml README.md ./
COPY meeting_summary ./meeting_summary

RUN pip install --constraint constraints-docker.txt ".[diarization]"

CMD ["meeting-summary"]
