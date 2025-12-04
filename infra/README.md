# Infrastructure

## Overview

Infrastructure as Code (IaC) for the SmarTask application. Contains Docker Compose orchestration and all Dockerfiles for building and deploying the microservices architecture.

## Contents

```
infra/
├── docker-compose.yml           # Orchestrates all 6 services
└── docker/                      # Service Dockerfiles
    ├── api/Dockerfile           # Java Spring Boot API
    ├── frontend/Dockerfile      # React frontend
    ├── scheduler/Dockerfile     # Python scheduler worker
    └── analyzer/Dockerfile      # Python analyzer worker
```

## Services Architecture

The `docker-compose.yml` orchestrates **6 services**:

1. **frontend** - React web UI (port 5173)
2. **api** - Spring Boot REST API (port 8081)
3. **scheduler** - Python worker for schedule generation
4. **analyzer** - Python worker for KPI analysis
5. **mongodb** - Database (port 27017)
6. **rabbitmq** - Message broker (ports 5672, 15672)

## Service Communication

```
┌─────────┐     HTTP      ┌─────┐     RabbitMQ    ┌───────────┐
│ Browser │ ────────────> │ API │ ──────────────> │ Scheduler │
└─────────┘               └─────┘                 └───────────┘
     │                       │                            │
     │    WebSocket          │        MongoDB             │
     │<─────────────────────>│ <─────────────────────────>│
                             │                            │
                             │     RabbitMQ     ┌──────────┐
                             └─────────────────>│ Analyzer │
                                                └──────────┘
```

## Docker Images

### API (`docker/api/Dockerfile`)
- Base: `eclipse-temurin:17-jdk`
- Builds Maven project
- Runs Spring Boot application

### Frontend (`docker/frontend/Dockerfile`)
- Base: `node:18-alpine`
- Builds React with Vite
- Serves with Vite preview

### Scheduler (`docker/scheduler/Dockerfile`)
- Base: `python:3.11-slim`
- Installs Python dependencies
- Runs RabbitMQClient.py

### Analyzer (`docker/analyzer/Dockerfile`)
- Base: `python:3.11-slim`
- Installs Python dependencies
- Runs analyze.py

## Volumes

- **mongo-data** - Persistent MongoDB storage
- **shared_tmp** - Temporary file sharing between services

## Networks

All services run on a single Docker network for inter-service communication.

## Usage

### Start All Services

```bash
# From project root
make build      # Build and start everything
make up         # Start with existing images
```

### Stop Services

```bash
make down       # Stop all services
make clean-volumes  # Stop and remove volumes
```

### View Logs

```bash
make logs              # All services
make logs-api          # API only
make logs-scheduler    # Scheduler only
make logs-analyzer     # Analyzer only
make logs-frontend     # Frontend only
```

### Service-Specific Rebuild

```bash
make build-api
make build-frontend
make build-scheduler
make build-analyzer
```

## Ports

| Service   | Port  | Purpose                |
|-----------|-------|------------------------|
| Frontend  | 5173  | Web UI                 |
| API       | 8081  | REST API               |
| MongoDB   | 27017 | Database               |
| RabbitMQ  | 5672  | AMQP protocol          |
| RabbitMQ  | 15672 | Management UI          |

## Environment Variables

Configured in `docker-compose.yml`:
- Database connections
- RabbitMQ settings
- Service-specific configurations

## Development vs Production

**Current Setup:** Development mode
- Vite dev server with hot reload
- Volume mounts for live code updates
- Debug logging enabled

**For Production:** Requires changes
- Use production builds
- Proper secrets management
- Reverse proxy (nginx)
- SSL/TLS certificates
