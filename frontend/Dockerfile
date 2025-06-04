FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN rm -rf node_modules/.vite
RUN npm ci
EXPOSE 5173
CMD ["npm", "run", "dev"]
