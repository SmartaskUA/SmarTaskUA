# Etapa 1: imagem base
FROM node:18-alpine

# Diretório de trabalho
WORKDIR /app

# Copia apenas arquivos de dependência primeiro para melhor cache
COPY package.json package-lock.json ./

# Instala dependências
RUN npm install

# Copia o restante da aplicação
COPY . .

# Remove qualquer cache antigo do Vite
RUN rm -rf node_modules/.vite

# Expõe a porta usada pelo Vite
EXPOSE 5173

# Comando para iniciar o servidor
CMD ["npm", "run", "dev"]
