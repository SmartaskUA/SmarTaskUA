# SmarTask

## Project Overview

SmarTask is an intelligent employee scheduling system that automatically generates and optimizes work schedules using constraint-based algorithms. The system respects business rules, vacation constraints, and minimum coverage requirements while providing real-time updates and comprehensive schedule analysis.

**Key Technologies:**
- **Backend:** Java 17 + Spring Boot
- **Frontend:** React 18 + Vite + TailwindCSS
- **Workers:** Python 3.11 (OR-Tools, PuLP)
- **Database:** MongoDB
- **Message Queue:** RabbitMQ
- **Infrastructure:** Docker + Docker Compose

---

## Project Structure

```
SmarTaskUA/
├── src/                              # All source code (microservices)
│   ├── api/                          # Java Spring Boot REST API
│   ├── frontend/                     # React + Vite Frontend
│   ├── scheduler/                    # Python Worker - Schedule Generation
│   │   └── algorithms/               # CSP, ILP, Greedy, Hill Climbing, etc.
│   └── analyzer/                     # Python Worker - KPI Analysis
│
├── config/                           # Centralized configuration
│   ├── rules.json                    # Business rules (consolidated)
│   └── templates/                    # CSV templates for data import
│
├── infra/                            # Infrastructure as code
│   ├── docker-compose.yml            # Service orchestration (6 services)
│   └── docker/                       # All Dockerfiles
│
├── docs/                             # Comprehensive documentation
│   ├── architecture/                 # System design & diagrams
│   ├── services/                     # Per-service documentation
│   ├── development/                  # Developer guides
│   └── algorithms/                   # Algorithm documentation
│
├── .github/workflows/                # CI/CD pipelines
├── Makefile                          # Build and deployment commands
├── CLAUDE.md                         # AI assistant context & guidelines
└── README.md                         # This file
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed

### Commands

```bash
# Show all available commands
make help

# Build everything (Maven + Docker) and start all services
make build

# Start services (without rebuilding)
make up

# Stop all services
make down

# View logs from all services
make logs
```

### Access Points

- **Web UI:** http://localhost:5173/ (manager/manager)
- **API:** http://localhost:8081/
- **RabbitMQ Management:** http://localhost:15672/ (guest/guest)

---

## Team Members

|     Name    |   GitHub  |  NMEC  |
|-------------|-----------|--------|
| João Roldão | @roldao04 | 113920 |
|             |           |        |
|             |           |        |
|             |           |        |

---

## Documentation

For detailed documentation, see:
- 