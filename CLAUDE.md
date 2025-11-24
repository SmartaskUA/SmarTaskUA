# SmarTask Repository Context for AI Assistants

**Repository:** SmarTaskUA
**Purpose:** Employee scheduling system using constraint optimization algorithms
**Last Updated:** 2025-11-24 (Post-Reorganization)

---

## Quick Overview

SmarTask is a microservices-based employee scheduling system that generates optimized work schedules using various algorithms (CSP, ILP, Greedy, Hill Climbing) while respecting business rules, vacation constraints, and minimum coverage requirements.

**Key Technologies:** Java/Spring Boot (API), React/Vite (Web), Python (Workers), MongoDB, RabbitMQ

---

## Repository Structure

```
SmarTaskUA/
├── src/                         # All source code (microservices)
│   ├── api/                     # Java Spring Boot REST API
│   ├── frontend/                # React + Vite frontend
│   ├── scheduler/               # Python worker - schedule generation
│   │   ├── algorithms/          # CSP, ILP, Greedy, Hill Climbing
│   │   ├── RabbitMQClient.py   # Queue consumer
│   │   ├── TaskManager.py      # Algorithm dispatcher
│   │   └── MongoDBClient.py    # Database client
│   └── analyzer/                # Python worker - KPI analysis
│       ├── analyze.py           # Queue consumer
│       ├── kpiVerification.py  # Single schedule KPIs
│       └── kpiComparison.py    # Multi-schedule comparison
│
├── config/                      # Centralized configuration
│   ├── rules.json              # Business rules (CONSOLIDATED)
│   └── templates/              # CSV templates for data import
│
├── infra/                       # Infrastructure as code
│   ├── docker-compose.yml      # Service orchestration (6 services)
│   └── docker/                 # All Dockerfiles
│       ├── api/Dockerfile
│       ├── frontend/Dockerfile
│       ├── scheduler/Dockerfile
│       └── analyzer/Dockerfile
│
├── docs/                        # Comprehensive documentation
│   ├── architecture/           # System design & diagrams
│   ├── services/               # Per-service documentation
│   ├── development/            # Developer guides
│   └── algorithms/             # Algorithm documentation
│
├── .github/                    # CI/CD workflows
├── Makefile                    # All build/deploy commands
├── CHANGES.md                  # Detailed reorganization log
└── README.md                   # Main documentation entry point
```

---

## Architecture at a Glance

**4 Main Services:**

1. **Frontend** (`src/frontend/`) - React frontend on port 5173
2. **API** (`src/api/`) - Spring Boot backend on port 8081
3. **Scheduler** (`src/scheduler/`) - Python worker consuming `task-queue`
4. **Analyzer** (`src/analyzer/`) - Python worker consuming `comparison-queue`

**Communication:**
- User ↔ Web ↔ API: HTTP/REST + WebSocket
- API ↔ Scheduler: RabbitMQ (`task-queue`, `status-queue`)
- API ↔ Analyzer: RabbitMQ (`comparison-queue`)
- All services ↔ MongoDB for data persistence

**Full architecture:** See `docs/architecture/system-overview.md`

---

## Common Tasks

### Finding Code

| What | Where |
|------|-------|
| REST API endpoints | `src/api/src/main/java/smartask/api/controllers/` |
| Frontend pages | `src/frontend/src/` |
| Algorithm implementations | `src/scheduler/algorithms/` |
| Schedule generation logic | `src/scheduler/TaskManager.py` |
| KPI calculation | `src/analyzer/kpiVerification.py` |
| Business rules | `config/rules.json` |
| Data models | `src/api/src/main/java/smartask/api/models/` |
| Docker Compose | `infra/docker-compose.yml` |
| All Dockerfiles | `infra/docker/` |
| Build commands | `Makefile` |

### Running the System

```bash
# Show all available commands
make help

# Build everything (mvn + docker) and start
make build

# Start services (without building)
make up

# View logs (all services)
make logs

# View logs (specific service)
make logs-api
make logs-scheduler
make logs-analyzer
make logs-frontend

# Stop all services
make down

# Restart everything
make restart

# Clean up (remove volumes)
make clean
```

### Key Ports

- **5173** - Web UI (React)
- **8081** - API (Spring Boot)
- **27017** - MongoDB
- **15672** - RabbitMQ Management UI
- **5672** - RabbitMQ AMQP

---

## Important Concepts

### Business Rules (`config/rules.json`)

The system enforces scheduling constraints through a rules engine:
- **Hard constraints:** Must be satisfied (team eligibility, max consecutive days, vacation blocks)
- **Soft constraints:** Preferred but can be violated (minimum coverage with penalties)

**Key Rules:**
- Employees work max 5 days in any 6-day window
- Max 22 Sundays/holidays per year per employee
- Exactly 223 workdays per year per employee
- No backward shift transitions (Night → Morning forbidden)
- Vacation days ("F") cannot be scheduled

**⚠️ IMPORTANT:** One source file had 300 workdays instead of 223 - now consolidated to 223. Verify with domain expert if needed.

### Shared Temporary Storage

The system uses a Docker-managed volume (`shared_tmp`) for temporary CSV exports:
- **API** writes schedule exports to this volume
- **Scheduler/Analyzer** read schedules from this volume
- **No folder in repository** - Docker manages it internally
- Data persists between container restarts but can be cleared with `make clean`

### Algorithms

The scheduler supports 12+ algorithms (see `src/scheduler/TaskManager.py`):
- **CSP** - Constraint Satisfaction (Google OR-Tools CP-SAT)
- **ILP** - Integer Linear Programming (PuLP)
- **Greedy Randomized** - Heuristic approach
- **Hill Climbing** - Local search optimization
- **Hybrid** - Combinations (e.g., Greedy + Hill Climbing)
- **Engines** - Advanced versions with rules engine integration

Each algorithm receives the same inputs: employees, vacations, minimums, shifts, year, rules, maxTime.

### Data Models

**Key MongoDB Collections:**
- `schedules` - Generated work schedules
- `employees` - Employee profiles (name, teams, skills)
- `teams` - Team definitions
- `vacations` - Vacation templates
- `references` - Minimum coverage requirements (minimunsTemplates)
- `comparisons` - Multi-schedule KPI comparisons
- `verifications` - Single-schedule KPI validations

---

## Code Standards & Patterns

### Python Services (Scheduler, Analyzer)

**Import Paths:**
- ✅ `from algorithms.CSP import solve` (scheduler)
- ✅ `from kpiVerification import analyze` (analyzer)
- ❌ `from algorithm.X` (old path - removed)
- ❌ `from modules.X` (old path - removed)

**Structure:**
- RabbitMQ consumers in main files (`RabbitMQClient.py`, `analyze.py`)
- Business logic in separate modules
- Shared utilities in `algorithms/utils.py`

### Java Service (API)

**Package Structure:**
- `controller` - REST endpoints (@RestController)
- `service` - Business logic (@Service)
- `repository` - MongoDB access (@Repository)
- `model` - Entities and DTOs
- `config` - Spring configuration
- `event` - RabbitMQ producers/consumers

**Key Patterns:**
- DTOs for request/response
- Service layer for business logic
- Repository pattern for data access
- WebSocket for real-time updates

### Frontend (Web)

**Structure:**
- `pages/` - Main views (Manager, Admin, Login)
- `components/` - Reusable UI components
- `context/` - React Context (AuthContext)
- `styles/` - CSS files

**Tech Stack:**
- React 18 with hooks
- Vite for build
- TailwindCSS for styling

---

## Testing & Debugging

### Access Services

- **Web UI:** http://localhost:5173
- **API:** http://localhost:8081
- **API Health:** http://localhost:8081/actuator/health
- **RabbitMQ UI:** http://localhost:15672 (guest/guest)

### Common Issues

**Scheduler not processing tasks?**
- Check RabbitMQ queue: http://localhost:15672
- View logs: `make logs-scheduler`
- Verify MongoDB connection
- Check if algorithm import errors exist

**API not connecting to services?**
- Verify RabbitMQ is healthy
- Check MongoDB connection
- Review application.properties configuration
- Check network connectivity in docker-compose

**Frontend not loading?**
- Check API is running on 8081
- Review browser console for errors
- Verify CORS configuration in API

---

## Development Workflow

### Making Changes

1. **Frontend changes:** Files hot-reload automatically (Vite dev server)
2. **API changes:** `make build-api`
3. **Scheduler changes:** `make build-scheduler`
4. **Analyzer changes:** `make build-analyzer`
5. **Frontend rebuild:** `make build-frontend`

### Adding New Algorithm

1. Create new file in `src/scheduler/algorithms/new_algorithm.py`
2. Implement `solve(vacations, minimuns, employees, maxTime, year, shifts, rules)` function
3. Add to `TaskManager.py` algorithms dictionary
4. Test via API endpoint with algorithm name
5. Document in `docs/algorithms/`

### Adding New Rule

1. Edit `config/rules.json`
2. Implement rule handler in `src/scheduler/algorithms/handlers/`
3. Register handler in appropriate engine
4. Update documentation

---

## Recent Changes (2025-11-24)

**Major Reorganization Completed:**

✅ Renamed `services/` → `src/` for cleaner structure
✅ Consolidated all infrastructure to `infra/` directory
✅ Moved all Dockerfiles to `infra/docker/` with subdirectories
✅ Enhanced Makefile with comprehensive build commands
✅ Removed `scripts/` folder - all functionality now in Makefile
✅ Cleaned up root directory (removed old scripts and files)
✅ Fixed `shared_tmp` as proper Docker volume (no longer a bind mount folder)
✅ Consolidated 3 duplicate `rules.json` files into `config/rules.json`
✅ Merged `modules/` and `algorithm/` into `src/scheduler/`
✅ Created separate `src/analyzer/` for KPI analysis
✅ Updated all Python imports (`algorithm.*` → `algorithms.*`)
✅ Created comprehensive documentation structure

**Breaking Changes:**
- Folder renamed: `services/` → `src/`
- All Dockerfiles moved: `src/*/Dockerfile` → `infra/docker/*/Dockerfile`
- Docker Compose location: root → `infra/docker-compose.yml`
- Service names changed: `python-modules` → `scheduler`
- Python import paths changed throughout codebase
- Build scripts removed - use `make` commands instead
- `shared_tmp/` no longer a folder in repo (Docker volume only)

**See:** `CHANGES.md` for complete change log

---

## Contributing Guidelines

### Before Making Changes

1. Read relevant service documentation in `docs/services/`
2. Understand the data flow (see `docs/architecture/system-overview.md`)
3. Check if similar functionality exists elsewhere

### Code Changes

1. Follow existing patterns in the service
2. Update imports if moving files
3. Test locally with `docker-compose up`
4. Update documentation if adding features

### Documentation

- Update service docs in `docs/services/` when changing APIs
- Update README.md if changing setup process
- Update CLAUDE.md if changing structure significantly

---

## Useful Resources

- **Main Documentation:** `README.md`
- **Architecture:** `docs/architecture/system-overview.md`
- **Reorganization Details:** `CHANGES.md`
- **Original Structure:** `docs/REPOSITORY_SNAPSHOT_BEFORE_REORGANIZATION.md`
- **Service Docs:** `docs/services/` (when created)

---

## Notes for AI Assistants

### When Asked About...

**"Where is X?"** → Use the repository structure above
**"How does scheduling work?"** → Refer to architecture docs and scheduler service
**"How to add a feature?"** → Check service docs + follow development workflow
**"What algorithms are available?"** → List from TaskManager.py or docs/algorithms/
**"Why is X not working?"** → Check common issues + logs

### Important Context

- This is a **production system** - be careful with breaking changes
- **Rules are critical** - verify with domain expert before changing
- **Services are decoupled** - changes to one shouldn't break others
- **Documentation is comprehensive** - refer users to docs when possible
- **Security is basic** - warn about production deployment requirements

---

*This file helps AI assistants understand the repository structure and provide better assistance. Keep it updated when making significant changes.*
