FROM python:3.11-slim

WORKDIR /app

# Install deps first (copy only requirements, not source)
COPY ./modules/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the code
COPY algorithm/ ./algorithm/
COPY modules/   ./modules/

CMD ["python3", "-u", "-m", "modules.RabbitMQClient"]
