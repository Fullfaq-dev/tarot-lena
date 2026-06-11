FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY alembic.ini ./
COPY backend ./backend
COPY prompts ./prompts
COPY Cards-jpg ./Cards-jpg

WORKDIR /app
