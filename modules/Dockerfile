FROM python:3.11-slim


COPY . .

RUN pip install  pika pymongo pytz numpy pandas deap pika tenacity
CMD ["python3", "-u", "-m", "modules.RabbitMQClient"]
