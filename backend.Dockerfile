# Backend Dockerfile for Render.com
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .
COPY project_jarvis/ /app/project_jarvis/
COPY skills/ /app/skills/

# Remove dev/test files
RUN rm -f test_*.py

ENV PYTHONPATH="/app/project_jarvis:/app"
ENV APP_ENV=production

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", $PORT"]
