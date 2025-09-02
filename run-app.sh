#!/bin/bash
set -e  # Para o script se algum comando falhar

echo "🔧 Construindo backend Java (Spring Boot)..."
if [ -d "api" ]; then
  cd api
  mvn clean install
  cd ..
else
  echo "❌ Pasta 'api' não encontrada!"
  exit 1
fi

docker compose down --remove-orphans

echo "🐳 Subindo containers com rebuild"
docker compose up --build -d
