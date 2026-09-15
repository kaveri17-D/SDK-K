FROM python:3.12-slim

WORKDIR /workspace

# Install system dependencies for postgres connectivity and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY backend/requirements.txt /workspace/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt

# Copy application source
COPY backend /workspace/backend

ENV PYTHONPATH=/workspace
EXPOSE 8000

# Run migrations and start FastAPI server
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
