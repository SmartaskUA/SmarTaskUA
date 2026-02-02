.PHONY: help build up down restart rebuild logs clean
.PHONY: build-api build-scheduler build-analyzer build-frontend build-json-generator build-nginx
.PHONY: logs-api logs-scheduler logs-analyzer logs-frontend logs-json-generator logs-nginx

# Docker Compose file location
COMPOSE_FILE := infra/docker-compose.yml

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)SmarTask - Available Make Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Main Commands:$(NC)"
	@echo "  make build          - Build API (mvn) and all Docker images, then start"
	@echo "  make up             - Start all services (rebuild if Dockerfiles changed)"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make rebuild        - Force rebuild all services without cache"
	@echo "  make logs           - Follow logs from all services"
	@echo "  make clean-volumes  - Stop services and remove all volumes"
	@echo ""
	@echo "$(GREEN)Service-Specific Builds:$(NC)"
	@echo "  make build-api            - Rebuild API (mvn + docker)"
	@echo "  make build-scheduler      - Rebuild scheduler service"
	@echo "  make build-analyzer       - Rebuild analyzer service"
	@echo "  make build-frontend       - Rebuild frontend service"
	@echo "  make build-json-generator - Rebuild JSON generator service"
	@echo "  make build-nginx          - Rebuild nginx reverse proxy"
	@echo ""
	@echo "$(GREEN)Service-Specific Logs:$(NC)"
	@echo "  make logs-api            - View API logs"
	@echo "  make logs-scheduler      - View scheduler logs"
	@echo "  make logs-analyzer       - View analyzer logs"
	@echo "  make logs-frontend       - View frontend logs"
	@echo "  make logs-json-generator - View JSON generator logs"
	@echo "  make logs-nginx          - View nginx logs"
	@echo ""
	@echo "$(YELLOW)Access Points:$(NC)"
	@echo "  Main App:        http://localhost/"
	@echo "  JSON Generator:  http://localhost/json-gen"
	@echo "  API:             http://localhost/api"
	@echo "  RabbitMQ UI:     http://localhost:15672 (guest/guest)"

build: ## Build everything (mvn + docker) and start services
	@echo "$(BLUE) Copying master rules.json to services...$(NC)"
	@cp config/rules.json src/api/src/main/resources/rules.json
	@cp config/rules.json src/scheduler/rules.json
	@echo "$(BLUE) Building backend Java (Spring Boot)...$(NC)"
	@if [ -d "src/api" ]; then \
		cd src/api && mvn clean install && cd ../..; \
	else \
		echo "$(YELLOW) Directory 'src/api' not found!$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE) Stopping containers...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down --remove-orphans
	@echo "$(BLUE) Building and starting containers...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up --build -d
	@echo "$(GREEN) All services started!$(NC)"
	@echo ""
	@$(MAKE) -s _show_access_points

up: ## Start all services (rebuild if Dockerfiles changed)
	@echo "$(BLUE) Starting all services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up --build -d
	@echo "$(GREEN) Services started!$(NC)"
	@$(MAKE) -s _show_access_points

down: ## Stop all services
	@echo "$(BLUE) Stopping all services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down --remove-orphans
	@echo "$(GREEN) Services stopped!$(NC)"

restart: down up ## Restart all services

rebuild: ## Force rebuild all services without cache
	@echo "$(BLUE) Force rebuilding all services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down --remove-orphans
	@docker compose -f $(COMPOSE_FILE) build --no-cache
	@docker compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN) Services rebuilt and started!$(NC)"
	@echo ""
	@$(MAKE) -s _show_access_points

logs: ## Follow logs from all services
	@docker compose -f $(COMPOSE_FILE) logs -f

clean-volumes: ## Stop services and remove all volumes
	@echo "$(YELLOW)  Stopping services and removing volumes...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN) Cleanup complete!$(NC)"

# Service-specific builds
build-api: ## Rebuild API service
	@echo "$(BLUE) Rebuilding API service...$(NC)"
	@cp config/rules.json src/api/src/main/resources/rules.json
	@cd src/api && mvn install && cd ../..
	@docker compose -f $(COMPOSE_FILE) build api
	@docker compose -f $(COMPOSE_FILE) stop api
	@docker compose -f $(COMPOSE_FILE) up -d api
	@echo "$(GREEN) API service rebuilt!$(NC)"

build-scheduler: ## Rebuild scheduler service
	@echo "$(BLUE) Rebuilding scheduler service...$(NC)"
	@cp config/rules.json src/scheduler/rules.json
	@docker compose -f $(COMPOSE_FILE) build scheduler
	@docker compose -f $(COMPOSE_FILE) stop scheduler
	@docker compose -f $(COMPOSE_FILE) up -d scheduler
	@echo "$(GREEN) Scheduler service rebuilt!$(NC)"

build-analyzer: ## Rebuild analyzer service
	@echo "$(BLUE) Rebuilding analyzer service...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build analyzer
	@docker compose -f $(COMPOSE_FILE) stop analyzer
	@docker compose -f $(COMPOSE_FILE) up -d analyzer
	@echo "$(GREEN) Analyzer service rebuilt!$(NC)"

build-frontend: ## Rebuild frontend service
	@echo "$(BLUE) Rebuilding frontend service...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build frontend
	@docker compose -f $(COMPOSE_FILE) stop frontend
	@docker compose -f $(COMPOSE_FILE) up -d frontend
	@echo "$(GREEN) Frontend service rebuilt!$(NC)"

build-json-generator: ## Rebuild JSON generator service
	@echo "$(BLUE) Rebuilding JSON generator service...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build json-generator
	@docker compose -f $(COMPOSE_FILE) stop json-generator
	@docker compose -f $(COMPOSE_FILE) up -d json-generator
	@echo "$(GREEN) JSON generator service rebuilt!$(NC)"

build-nginx: ## Rebuild nginx reverse proxy
	@echo "$(BLUE) Rebuilding nginx service...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build nginx
	@docker compose -f $(COMPOSE_FILE) stop nginx
	@docker compose -f $(COMPOSE_FILE) up -d nginx
	@echo "$(GREEN) Nginx service rebuilt!$(NC)"

# Service-specific logs
logs-api: ## View API logs
	@docker compose -f $(COMPOSE_FILE) logs -f api

logs-scheduler: ## View scheduler logs
	@docker compose -f $(COMPOSE_FILE) logs -f scheduler

logs-analyzer: ## View analyzer logs
	@docker compose -f $(COMPOSE_FILE) logs -f analyzer

logs-frontend: ## View frontend logs
	@docker compose -f $(COMPOSE_FILE) logs -f frontend

logs-json-generator: ## View JSON generator logs
	@docker compose -f $(COMPOSE_FILE) logs -f json-generator

logs-nginx: ## View nginx logs
	@docker compose -f $(COMPOSE_FILE) logs -f nginx

# Internal helper (not shown in help)
_show_access_points:
	@echo "$(YELLOW)Access points:$(NC)"
	@echo "  Main App:         http://localhost/"
	@echo "  JSON Generator:   http://localhost/json-gen"
	@echo "  API:              http://localhost/api"
	@echo "  RabbitMQ UI:      http://localhost:15672 (guest/guest)"
