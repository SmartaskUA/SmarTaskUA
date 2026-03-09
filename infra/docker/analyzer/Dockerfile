FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies (from src/analyzer/)
COPY src/analyzer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy analyzer service files (from src/analyzer/)
COPY src/analyzer/ .
COPY data/problems /app/data/problems

# Run the analyzer worker
CMD ["python", "-u", "analyze.py"]
