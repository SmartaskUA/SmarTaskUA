# System Architecture Overview

## System Diagram

```
                          ┌──────────┐
                          │  Browser │
                          └────┬─────┘
                               │ HTTP / WS (:80)
                               ▼
                          ┌──────────┐
                          │  nginx   │  reverse proxy — single public entry
                          └────┬─────┘
            ┌──────────────────┼────────────────────┐
            │ /                │ /json-gen           │ /api
            ▼                  ▼                     ▼
      ┌──────────┐     ┌───────────────┐       ┌──────────┐      ┌───────────┐
      │ Frontend │     │ JSON Generator│       │   API    │─────▶│ Scheduler │
      │ React +  │     │ React wizard  │       │ Spring   │      │  Python   │
      │ Vite     │     └───────────────┘       │ Boot     │      │  Worker   │
      └──────────┘                             └────┬─────┘      └─────┬─────┘
                                                    │ RabbitMQ         │
                                                    ▼                  ▼
                                               ┌──────────┐      ┌───────────┐
                                               │ Analyzer │      │  MongoDB  │
                                               │  Python  │      │ Database  │
                                               │  Worker  │      └───────────┘
                                               └──────────┘
```

## Services

| Service        | Technology         | Port (internal) | Purpose                                |
|----------------|--------------------|-----------------|----------------------------------------|
| nginx          | nginx              | **80 (public)** | Reverse proxy — single public entry    |
| Frontend       | React 18 + Vite    | 5173            | Web UI (main app)                      |
| JSON Generator | React 18 + Vite    | 5174            | Wizard that builds `problem.json` + CSV|
| API            | Spring Boot + Java | 8081            | REST API + WebSocket                   |
| Scheduler      | Python 3.11        | -               | Schedule generation worker             |
| Analyzer       | Python 3.11        | -               | KPI analysis worker                    |
| MongoDB        | MongoDB Latest     | 27017           | Data persistence                       |
| RabbitMQ       | RabbitMQ 3         | 5672 / 15672    | Message queue (15672 = management UI)  |

> The app's HTTP ports (Frontend 5173, JSON Generator 5174, API 8081) are **not** published — reach them through **nginx `:80`**. MongoDB `:27017` and RabbitMQ `:5672`/`:15672` are published for direct/dev access.

## Communication

- **Browser ↔ nginx:** all traffic enters on `:80`; nginx routes `/` → Frontend, `/json-gen/` → JSON Generator, `/api/` → API
- **Frontend ↔ API:** REST API + WebSocket (real-time updates), proxied through nginx
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

All services are served behind the nginx reverse proxy:

- **Main App:** http://localhost/ (manager/manager)
- **JSON Generator:** http://localhost/json-gen
- **API:** http://localhost/api
- **RabbitMQ Management:** http://localhost:15672 (guest/guest)

## For More Details

- Service specifics: See READMEs in `src/api/`, `src/frontend/`, `src/json-generator/`, `src/scheduler/`, `src/analyzer/`
- Infrastructure: See `infra/README.md`
- Configuration: See `config/README.md`
- problem.json flow to solvers: See `docs/architecture/problem-json-flow.md`
