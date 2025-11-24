FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy analyzer service files
COPY . .

# Run the analyzer worker
CMD ["python", "-u", "analyze.py"]
