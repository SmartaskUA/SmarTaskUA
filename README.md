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
├── src/                              # All source code (6 microservices)
│   ├── api/                          # Java Spring Boot REST API
│   ├── frontend/                     # React + Vite frontend (main app)
│   ├── json-generator/              # React wizard — builds schema v4 packages (problem.json + CSVs)
│   ├── scheduler/                    # Python worker — schedule generation
│   │   ├── problem_v4/               # the schema v4 parser, scorer and result writer
│   │   └── algorithms/               # ILP, CP-SAT, heuristics, GA, ...
│   └── analyzer/                     # Python worker — KPI analysis
│
├── config/                           # Centralized configuration
│   ├── rules.json                    # Master business rules (copied to api + scheduler at build)
│   ├── templates/                    # CSV/Excel templates for data import
│   └── examples/                     # Sample config snippets
│
├── data/                             # Sample problem fixtures (problem.json + CSVs)
│   └── problems/
│
├── infra/                            # Infrastructure as code
│   ├── docker-compose.yml            # Orchestration: api, frontend, json-generator,
│   │                                 #   scheduler, analyzer, nginx
│   └── docker/                       # All Dockerfiles + nginx reverse-proxy config
│
├── docs/                             # Documentation
│   ├── architecture/                 # System design & diagrams (markdown)
│   ├── algorithms/                   # Algorithm documentation (markdown)
│   ├── development/                  # Developer guides (markdown)
│   ├── adr/                          # Architecture Decision Records
│   ├── specifications/               # Problem specs & math definitions (PDF/docx)
│   ├── references/                   # Third-party / academic source material (PDF)
│   ├── results/                      # Experimental results (PDF)
│   └── reports/                      # Technical reports / deliverables (PDF)
│
├── json_generation/                  # Schema history (v2 → v4); schema_v4/ holds the canonical
│                                     #   v4 schema, validator and example packages
├── scripts/                          # Helper scripts (e.g. validate_general_rules.py)
├── .github/workflows/                # CI/CD pipelines
├── Makefile                          # Build and deployment commands
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

### Solve a problem

In the app: **Problems** → pick or upload a v4 package → *Use In Schedule* → *Generate*. Or from a shell:

```bash
make solve PKG=json_generation/schema_v4/examples/cenario2_partial ALG=all
```

Everything about it: **[docs/how-to-solve.md](docs/how-to-solve.md)**.

### Access Points

All services are served behind the nginx reverse proxy:

- **Main App:** http://localhost/ (manager/manager)
- **JSON Generator:** http://localhost/json-gen
- **API:** http://localhost/api
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

Start at the **[docs index](docs/README.md)**. The main folders:
- **[docs/architecture/](docs/architecture/)** — system design & diagrams
- **[docs/development/](docs/development/)** — developer getting-started guides
- **[docs/algorithms/](docs/algorithms/)** — algorithm documentation
- **[docs/adr/](docs/adr/)** — architecture decision records
- **[docs/specifications/](docs/specifications/)** — problem specs & mathematical definitions
- **[docs/references/](docs/references/)** — third-party & academic source material
- **[docs/results/](docs/results/)** & **[docs/reports/](docs/reports/)** — experimental results & technical reports