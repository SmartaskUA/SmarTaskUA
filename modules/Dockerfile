FROM python:3.11-slim

WORKDIR /app

# Copia todos os arquivos do diretório 'modules' para o container
COPY . .

# Verificar se o conteúdo de 'modules' foi copiado corretamente
RUN ls

# Instala as dependências diretamente usando o arquivo requirements.txt
RUN pip install -r requirements.txt

# O comando será definido no docker-compose (command)
