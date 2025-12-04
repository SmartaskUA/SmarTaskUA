FROM node:20-alpine

WORKDIR /app

# instala curl para o healthcheck (ou mude o healthcheck para wget)
RUN apk add --no-cache curl

# Copy package files (from src/frontend/)
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci

# Não copie a app aqui; vamos montar via bind mount no compose
EXPOSE 5173

# Vite a escutar em 0.0.0.0 para funcionar fora do container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
