FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (from src/scheduler/)
COPY src/scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy master rules.json from config/
COPY config/rules.json ./rules.json

# Copy bundled problem definitions used by problem-native solvers.
COPY data/problems ./data/problems

# Copy the entire scheduler service (from src/scheduler/)
COPY src/scheduler/ .

# Ensure analyzer package is available inside the scheduler container
COPY src/analyzer/ ./analyzer

# The command will be specified in docker-compose.yml
CMD ["python3", "RabbitMQClient.py"]
