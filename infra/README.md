# Infrastructure

## Overview

Infrastructure as Code (IaC) for the SmarTask application. Contains Docker Compose orchestration and all Dockerfiles for building and deploying the microservices architecture.

## Contents

```
infra/
├── docker-compose.yml             # Orchestrates all 8 services
└── docker/                        # Service Dockerfiles
    ├── nginx/Dockerfile           # nginx reverse proxy
    ├── nginx/nginx.conf           # Proxy routes (/, /api/, /json-gen/)
    ├── api/Dockerfile             # Java Spring Boot API
    ├── frontend/Dockerfile        # React frontend (main app)
    ├── json-generator/Dockerfile  # React problem.json wizard
    ├── scheduler/Dockerfile       # Python scheduler worker
    └── analyzer/Dockerfile        # Python analyzer worker
```

## Services Architecture

The `docker-compose.yml` orchestrates **8 services**:

1. **nginx** - Reverse proxy and single public entry point (port 80)
2. **frontend** - React web UI / main app (internal port 5173)
3. **json-generator** - React wizard that builds `problem.json` + CSVs (internal port 5174)
4. **api** - Spring Boot REST API + WebSocket (internal port 8081)
5. **scheduler** - Python worker for schedule generation
6. **analyzer** - Python worker for KPI analysis
7. **mongodb** - Database (port 27017)
8. **rabbitmq** - Message broker (ports 5672, 15672)

## Service Communication

```
┌─────────┐  HTTP :80   ┌───────┐  (reverse proxy)
│ Browser │ ──────────> │ nginx │
└─────────┘             └───┬───┘
                            │ routes by path
        ┌───────────────────┼────────────────────┐
        │ /                 │ /json-gen           │ /api
        ▼                   ▼                     ▼
   ┌──────────┐      ┌───────────────┐         ┌─────┐   RabbitMQ   ┌───────────┐
   │ Frontend │      │ JSON Generator│         │ API │ ───────────> │ Scheduler │
   └──────────┘      └───────────────┘         └──┬──┘              └───────────┘
                                                  │ RabbitMQ / MongoDB
                                                  ▼
                                           ┌──────────┐      ┌──────────┐
                                           │ Analyzer │      │ MongoDB  │
                                           └──────────┘      └──────────┘
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

### JSON Generator (`docker/json-generator/Dockerfile`)
- Base: `node:18-alpine`
- Builds the React wizard with Vite
- Served at `/json-gen` via nginx

### nginx (`docker/nginx/Dockerfile`)
- Base: `nginx:alpine`
- Reverse proxy; config in `docker/nginx/nginx.conf`
- Routes `/` → frontend, `/json-gen/` → json-generator, `/api/` → api

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

| Service        | Port  | Exposure | Purpose              |
|----------------|-------|----------|----------------------|
| nginx          | 80    | public   | Reverse proxy entry  |
| Frontend       | 5173  | internal | Web UI               |
| JSON Generator | 5174  | internal | problem.json wizard  |
| API            | 8081  | internal | REST API + WebSocket |
| MongoDB        | 27017 | published| Database             |
| RabbitMQ       | 5672  | published| AMQP protocol        |
| RabbitMQ       | 15672 | published| Management UI        |

> "internal" = reachable only through nginx / the Docker network; "published" = mapped to the host.

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
- Use production builds (currently Vite dev servers behind nginx)
- Proper secrets management
- SSL/TLS termination at nginx (reverse proxy is already in place)
- Restrict the published MongoDB/RabbitMQ host ports
