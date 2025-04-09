FROM python:3.11-slim

# Define diretório de trabalho dentro do container

# Copia tudo da raiz do projeto para /app
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir pika pymongo pytz
