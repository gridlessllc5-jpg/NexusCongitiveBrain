# Fractured Survival Brain - Docker Deployment
# Use with Cloudflare Tunnel or any container platform

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt /app/backend/
COPY npc_system/requirements.txt /app/npc_system/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/npc_system/requirements.txt
RUN pip install uvicorn fastapi

# Copy application code
COPY backend/ /app/backend/
COPY npc_system/ /app/npc_system/

# Create necessary directories
RUN mkdir -p /app/npc_system/database

# Set working directory to backend
WORKDIR /app/backend

# Expose ports
EXPOSE 8001 9000

# Environment variables (override with docker-compose or -e flags)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start the backend server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
