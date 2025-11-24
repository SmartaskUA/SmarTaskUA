# SmarTask - System Architecture Overview

**Last Updated:** 2025-11-24
**Version:** 1.0 (Post-Reorganization)

## Table of Contents

1. [Introduction](#introduction)
2. [High-Level Architecture](#high-level-architecture)
3. [Technology Stack](#technology-stack)
4. [Service Communication](#service-communication)
5. [Data Flow](#data-flow)
6. [Infrastructure](#infrastructure)

---

## Introduction

SmarTask is an employee scheduling system that uses advanced optimization algorithms (Constraint Satisfaction Programming, Integer Linear Programming, and various heuristics) to generate optimal work schedules while respecting business rules, vacation constraints, and minimum coverage requirements.

### System Purpose

- **Generate** employee schedules using multiple algorithms
- **Analyze** schedule quality through KPI verification and comparison
- **Manage** teams, employees, rules, and templates through a web interface
- **Persist** all data in MongoDB for historical tracking

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User/Manager                                   │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Web Service (React + Vite)                          │
│                          Port: 5173                                     │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │ REST API
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  API Service (Java Spring Boot)                         │
│                          Port: 8081                                     │
│                                                                         │
│  Endpoints:                                                             │
│    - /employees, /teams, /schedules                                     │
│    - /rules, /vacations, /references                                    │
│    - WebSocket for real-time status updates                            │
└─────────┬───────────────────────────┬───────────────────────────────────┘
          │                           │
          │ MongoDB                   │ RabbitMQ
          ▼                           ▼
┌──────────────────┐      ┌────────────────────────────────────────────┐
│                  │      │          RabbitMQ                          │
│    MongoDB       │      │                                            │
│   Port: 27017    │      │  Queues:                                   │
│                  │      │    - task-queue (schedule generation)      │
│  Collections:    │      │    - status-queue (task status updates)    │
│   - schedules    │      │    - comparison-queue (KPI analysis)       │
│   - employees    │      │                                            │
│   - teams        │      │  Exchanges:                                │
│   - vacations    │      │    - task-exchange                         │
│   - comparisons  │      │    - status-exchange                       │
│   - verifications│      │    - comparison-exchange                   │
└──────────────────┘      └────┬──────────────────┬────────────────────┘
                               │                  │
                               ▼                  ▼
                    ┌──────────────────┐  ┌──────────────────┐
                    │                  │  │                  │
                    │   Scheduler      │  │    Analyzer      │
                    │   (Python)       │  │    (Python)      │
                    │                  │  │                  │
                    │  Consumes:       │  │  Consumes:       │
                    │   task-queue     │  │   comparison-q   │
                    │                  │  │                  │
                    │  Produces:       │  │  Produces:       │
                    │   status-queue   │  │   MongoDB docs   │
                    │                  │  │                  │
                    │  Algorithms:     │  │  Functions:      │
                    │   - CSP          │  │   - KPI verify   │
                    │   - ILP          │  │   - KPI compare  │
                    │   - Greedy       │  │                  │
                    │   - Hill Climb   │  │                  │
                    └──────────────────┘  └──────────────────┘
```

---

## Technology Stack

### Frontend (Web Service)
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** TailwindCSS
- **Language:** JavaScript/JSX
- **Port:** 5173

### Backend (API Service)
- **Framework:** Spring Boot 3.x
- **Language:** Java 17
- **Build Tool:** Maven
- **Key Dependencies:**
  - Spring Data MongoDB
  - Spring RabbitMQ
  - Spring WebSocket
  - Spring Web
- **Port:** 8081

### Scheduler Worker
- **Language:** Python 3.11
- **Key Libraries:**
  - `pika` - RabbitMQ client
  - `pymongo` - MongoDB client
  - `ortools` - Google OR-Tools (CP-SAT solver)
  - `pulp` - Linear programming
  - `pandas`, `numpy` - Data manipulation

### Analyzer Worker
- **Language:** Python 3.11
- **Key Libraries:**
  - `pika` - RabbitMQ client
  - `pymongo` - MongoDB client
  - `pandas` - Data analysis
  - `holidays` - Holiday calculations

### Infrastructure
- **Message Queue:** RabbitMQ 3 with Management UI
- **Database:** MongoDB (latest)
- **Database UI:** Mongo Express
- **Containerization:** Docker + Docker Compose
- **Orchestration:** docker-compose.yml (7 services)

---

## Service Communication

### 1. User → Web → API (Synchronous)
- **Protocol:** HTTP/REST
- **Format:** JSON
- **Authentication:** (TBD - currently appears to use session-based)
- **WebSocket:** Real-time task status updates

### 2. API → Scheduler (Asynchronous)
- **Protocol:** AMQP (via RabbitMQ)
- **Queue:** `task-queue`
- **Message Format:**
  ```json
  {
    "taskId": "unique-id",
    "title": "Schedule Name",
    "algorithm": "CSP",
    "year": 2025,
    "shifts": 2,
    "vacationTemplate": "template-name",
    "minimuns": "template-name",
    "rules": { ... },
    "maxTime": 600
  }
  ```

### 3. Scheduler → API (Asynchronous - Status Updates)
- **Protocol:** AMQP
- **Queue:** `status-queue`
- **Message Format:**
  ```json
  {
    "taskId": "unique-id",
    "status": "IN_PROGRESS | COMPLETED | FAILED",
    "updatedAt": "ISO-8601 timestamp"
  }
  ```

### 4. API → Analyzer (Asynchronous)
- **Protocol:** AMQP
- **Queue:** `comparison-queue`
- **Message Format:**
  ```json
  {
    "requestId": "unique-id",
    "files": ["schedule-id-1", "schedule-id-2"],
    "vacationTemplate": "name",
    "minimunsTemplate": "name",
    "employees": "[...]",
    "year": 2025
  }
  ```

### 5. Services → MongoDB (Synchronous)
- **Protocol:** MongoDB Wire Protocol
- **Connection String:** `mongodb://admin:password@mongo:27017/`
- **Database:** `mydatabase`
- **Operations:** CRUD for all collections

---

## Data Flow

### Schedule Generation Flow

```
1. User creates schedule request in Web UI
2. Web sends POST request to API (/schedules)
3. API validates request and publishes message to task-queue
4. API returns task ID to Web
5. Scheduler consumes message from task-queue
6. Scheduler executes selected algorithm (CSP, ILP, etc.)
7. Scheduler publishes status updates to status-queue (IN_PROGRESS)
8. API consumes status updates and pushes via WebSocket to Web
9. Scheduler completes and saves result to MongoDB
10. Scheduler publishes COMPLETED status
11. Web displays generated schedule to user
```

### KPI Analysis Flow

```
1. User requests schedule comparison in Web UI
2. Web sends POST request to API (/analyze or similar)
3. API publishes message to comparison-queue
4. Analyzer consumes message
5. Analyzer fetches schedule files from shared storage
6. Analyzer computes KPIs using kpiVerification/kpiComparison
7. Analyzer saves results to MongoDB (comparisons/verifications collections)
8. Web polls or receives notification to fetch results
9. User views KPI analysis results
```

---

## Infrastructure

### Docker Compose Services

| Service Name | Container Name | Ports | Purpose |
|-------------|----------------|-------|---------|
| `mongo` | mongodb | 27017 | Primary database |
| `mongo-express` | mongo-express | 8083 | Database admin UI |
| `rabbitmq` | rabbitmq | 5672, 15672 | Message queue + UI |
| `scheduler` | scheduler | - | Schedule generation worker |
| `analyzer` | analyzer | - | KPI analysis worker |
| `api` | api | 8081 | REST API backend |
| `web` | web | 5173 | React frontend |

### Volumes

- `mongo_data` - Persistent MongoDB data
- `shared_tmp` - Shared temporary file storage for CSV exports

### Networks

- `rabbitmq_network` - Bridge network connecting all services

### Health Checks

All services implement health checks for orchestration:
- **mongo:** MongoDB ping command
- **mongo-express:** HTTP health endpoint
- **rabbitmq:** RabbitMQ diagnostics
- **scheduler:** Process check (pgrep)
- **analyzer:** Process check (pgrep)
- **api:** Spring Boot Actuator (/actuator/health)
- **web:** HTTP check on Vite dev server

---

## Scalability Considerations

### Horizontal Scaling Opportunities

1. **Scheduler Workers:** Can run multiple instances consuming from same queue
2. **Analyzer Workers:** Can run multiple instances for parallel KPI analysis
3. **API Service:** Stateless design allows multiple instances behind load balancer

### Current Limitations

- MongoDB is single-instance (not replicated)
- RabbitMQ is single-instance (not clustered)
- Frontend is single-instance dev server (production would use Nginx)

---

## Security Considerations

**⚠️ Current State (Development):**

- MongoDB uses default credentials (`admin:password`)
- RabbitMQ uses default credentials (`guest:guest`)
- No TLS/SSL on any service
- No authentication on API endpoints (appears to be basic/session-based)
- Shared temp directory has no access controls

**🔒 Production Requirements:**

- Use strong, unique credentials stored in secrets management
- Enable TLS for all external communications
- Implement proper JWT or OAuth2 authentication
- Enable MongoDB authentication and authorization
- Enable RabbitMQ user permissions and virtual hosts
- Use HTTPS for web service
- Implement rate limiting on API
- Add audit logging

---

## Maintenance and Monitoring

### Recommended Monitoring

- **RabbitMQ Management UI:** http://localhost:15672 (guest/guest)
- **Mongo Express:** http://localhost:8083 (admin/mysecretpassword)
- **API Health:** http://localhost:8081/actuator/health
- **Web:** http://localhost:5173

### Logs

- View all logs: `docker-compose logs -f`
- View specific service: `docker-compose logs -f scheduler`

### Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View service status
docker-compose ps
```

---

## References

- [Service Documentation](../services/)
- [Algorithm Documentation](../algorithms/)
- [Development Guide](../development/getting-started.md)
- [API Documentation](../services/api.md)
