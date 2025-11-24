FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire scheduler service (including algorithms)
COPY . .

# The command will be specified in docker-compose.yml
CMD ["python3", "RabbitMQClient.py"]
