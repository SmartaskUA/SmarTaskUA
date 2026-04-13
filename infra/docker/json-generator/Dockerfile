FROM node:20-alpine

WORKDIR /app

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy package files (from src/json-generator/)
COPY src/json-generator/package.json src/json-generator/package-lock.json* ./
RUN npm ci || npm install

# Don't copy the app here; we'll mount via bind mount in compose
EXPOSE 5174

# Vite listening on 0.0.0.0 to work outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]
