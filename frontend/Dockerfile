# Etapa 1: imagem base
FROM node:18-alpine

# Diretório de trabalho
WORKDIR /app

# Instala dependências
COPY package.json ./
COPY package-lock.json ./
RUN npm install

# Copia o restante da app
COPY . .

# Expõe a porta que o Vite usa por padrão
EXPOSE 5173

# Comando para iniciar o servidor de desenvolvimento
CMD ["npm", "run", "dev"]
