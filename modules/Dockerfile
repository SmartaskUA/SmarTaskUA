FROM python:3.11-slim

WORKDIR /app

# Copia diretórios e arquivos necessários
COPY algorithm/ ./algorithm/
COPY modules/   ./modules/

# Instala dependências
RUN pip install pika pymongo pytz numpy pandas deap pulp holidays tabulate tenacity

# Comando de entrada
CMD ["python3", "-u", "-m", "modules.RabbitMQClient"]
