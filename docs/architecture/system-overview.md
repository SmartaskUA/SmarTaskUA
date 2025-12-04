# System Architecture Overview

## System Diagram

```
┌──────────┐
│  Browser │
└────┬─────┘
     │ HTTP/WS
     ▼
┌──────────┐      ┌──────────┐      ┌───────────┐
│ Frontend │─────▶│   API    │─────▶│ Scheduler │
│ React+   │      │ Spring   │      │  Python   │
│ Vite     │      │ Boot     │      │  Worker   │
└──────────┘      └────┬─────┘      └─────┬─────┘
                       │                  │
                       │ RabbitMQ         │
                       ▼                  ▼
                  ┌──────────┐      ┌───────────┐
                  │ Analyzer │      │  MongoDB  │
                  │  Python  │      │ Database  │
                  │  Worker  │      └───────────┘
                  └──────────┘
```

## Services

| Service   | Technology        | Port  | Purpose                          |
|-----------|-------------------|-------|----------------------------------|
| Frontend  | React 18 + Vite   | 5173  | Web UI                           |
| API       | Spring Boot + Java| 8081  | REST API + WebSocket             |
| Scheduler | Python 3.11       | -     | Schedule generation worker       |
| Analyzer  | Python 3.11       | -     | KPI analysis worker              |
| MongoDB   | MongoDB Latest    | 27017 | Data persistence                 |
| RabbitMQ  | RabbitMQ 3        | 5672  | Message queue (15672 for UI)     |

## Communication

- **User ↔ Frontend:** Browser HTTP requests
- **Frontend ↔ API:** REST API + WebSocket (real-time updates)
- **API ↔ Scheduler:** RabbitMQ (`task-queue`, `status-queue`)
- **API ↔ Analyzer:** RabbitMQ (`comparison-queue`)
- **All Services ↔ MongoDB:** Direct database connection

## Technology Stack

**Frontend:** React 18, Vite, TailwindCSS
**Backend:** Java 17, Spring Boot, Spring Data MongoDB, Spring AMQP
**Workers:** Python 3.11, OR-Tools, PuLP, pika, pymongo
**Infrastructure:** Docker, Docker Compose, RabbitMQ, MongoDB

## Key Workflows

**Generate Schedule:**
1. User configures schedule via Web UI
2. Frontend sends request to API
3. API publishes task to RabbitMQ (`task-queue`)
4. Scheduler consumes task, runs algorithm
5. Scheduler saves result to MongoDB
6. Scheduler publishes status to RabbitMQ (`status-queue`)
7. API receives status, notifies Frontend via WebSocket

**Analyze Schedule:**
1. User requests comparison via Web UI
2. API publishes analysis request to RabbitMQ (`comparison-queue`)
3. Analyzer consumes request, calculates KPIs
4. Analyzer saves results to MongoDB
5. API retrieves results, displays in Frontend

## Access Points

- **Web UI:** http://localhost:5173 (manager/manager)
- **API:** http://localhost:8081
- **RabbitMQ Management:** http://localhost:15672 (guest/guest)

## For More Details

- Service specifics: See READMEs in `src/api/`, `src/frontend/`, `src/scheduler/`, `src/analyzer/`
- Infrastructure: See `infra/README.md`
- Configuration: See `config/README.md`
