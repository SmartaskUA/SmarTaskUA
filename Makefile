.PHONY: help build up down restart logs clean
.PHONY: build-api build-scheduler build-analyzer build-frontend
.PHONY: logs-api logs-scheduler logs-analyzer logs-frontend

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
	@echo "  make up             - Start all services in detached mode"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - Follow logs from all services"
	@echo "  make clean-volumes  - Stop services and remove all volumes"
	@echo ""
	@echo "$(GREEN)Service-Specific Builds:$(NC)"
	@echo "  make build-api       - Rebuild API (mvn + docker)"
	@echo "  make build-scheduler - Rebuild scheduler service"
	@echo "  make build-analyzer  - Rebuild analyzer service"
	@echo "  make build-frontend  - Rebuild frontend service"
	@echo ""
	@echo "$(GREEN)Service-Specific Logs:$(NC)"
	@echo "  make logs-api        - View API logs"
	@echo "  make logs-scheduler  - View scheduler logs"
	@echo "  make logs-analyzer   - View analyzer logs"
	@echo "  make logs-frontend   - View frontend logs"
	@echo ""
	@echo "$(YELLOW)Access Points:$(NC)"
	@echo "  Web UI:          http://localhost:5173"
	@echo "  API:             http://localhost:8081"
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

up: ## Start all services in detached mode
	@echo "$(BLUE) Starting all services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN) Services started!$(NC)"
	@$(MAKE) -s _show_access_points

down: ## Stop all services
	@echo "$(BLUE) Stopping all services...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN) Services stopped!$(NC)"

restart: down up ## Restart all services

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

# Service-specific logs
logs-api: ## View API logs
	@docker compose -f $(COMPOSE_FILE) logs -f api

logs-scheduler: ## View scheduler logs
	@docker compose -f $(COMPOSE_FILE) logs -f scheduler

logs-analyzer: ## View analyzer logs
	@docker compose -f $(COMPOSE_FILE) logs -f analyzer

logs-frontend: ## View frontend logs
	@docker compose -f $(COMPOSE_FILE) logs -f frontend

# Internal helper (not shown in help)
_show_access_points:
	@echo "$(YELLOW)Access points:$(NC)"
	@echo "  Web UI:           http://localhost:5173"
	@echo "  API:              http://localhost:8081"
	@echo "  RabbitMQ UI:      http://localhost:15672 (guest/guest)"
