# Repository Snapshot - Before Reorganization

**Date:** 2025-11-24
**Branch:** chore/repo-reorganization
**Purpose:** Document the repository structure before reorganization for reference and potential rollback

## Directory Structure (Before Changes)

```
SmarTaskUA/
├── algorithm/              # Python scheduling algorithms (216KB)
│   ├── CSP.py, CSPv2.py
│   ├── ILP.py, ILPv2.py
│   ├── hillClimbing.py
│   ├── greedyRandomized.py
│   ├── greedyClimbing.py
│   ├── engines/           # Advanced algorithm engines
│   │   ├── CSP_Engine.py
│   │   ├── ILPEngine.py
│   │   ├── greedyClimbingEngine.py
│   │   ├── greedyRandomizedEngine.py
│   │   ├── rules_engine.py
│   │   └── rules.json     # ⚠️ DUPLICATE 1/3
│   ├── contexts/          # Algorithm contexts
│   │   ├── CPSatContext.py
│   │   ├── GreedyContext.py
│   │   └── ILPContext.py
│   ├── handlers/          # Business rules handlers
│   │   ├── rules_handlers_cpsat.py
│   │   ├── rules_handlers_greedy.py
│   │   └── rules_handlers_ilp.py
│   ├── kpiVerification.py
│   ├── kpiComparison.py
│   ├── utils.py
│   └── requirements
│
├── api/                   # Java Spring Boot backend (3.4MB)
│   ├── src/main/java/com/smardash/
│   │   ├── controller/    # 9 REST controllers
│   │   ├── model/         # 11 entities + DTOs
│   │   ├── service/       # 7 business services
│   │   ├── repository/    # 7 MongoDB repositories
│   │   ├── config/        # RabbitMQ, WebSocket, Security
│   │   ├── event/         # RabbitMQ producers/consumers
│   │   └── utils/         # CSV/File handlers
│   ├── src/main/resources/
│   │   ├── application.properties
│   │   ├── logback-spring.xml
│   │   └── rules.json     # ⚠️ DUPLICATE 2/3
│   ├── pom.xml
│   └── Dockerfile
│
├── frontend/              # React + Vite web app (52KB source)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Manager/   # Main features
│   │   │   ├── Admin/
│   │   │   └── login/
│   │   ├── components/
│   │   ├── context/
│   │   ├── styles/
│   │   └── assets/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── Dockerfile.dev
│
├── modules/               # Python RabbitMQ workers (56KB)
│   ├── RabbitMQClient.py  # Schedule generation worker
│   ├── TaskManager.py     # Algorithm dispatcher (12+ algorithms)
│   ├── MongoDBClient.py   # Database client
│   ├── analyze.py         # KPI analysis worker (separate service)
│   ├── requirements.txt
│   ├── rules.json         # ⚠️ DUPLICATE 3/3
│   └── Dockerfile
│
├── data/                  # CSV templates
│   ├── minimuns.csv
│   └── VacationTemplate.csv
│
├── docs/                  # Documentation
│   ├── SmarTask - Relatório Técnico.pdf
│   └── UTF-8Heuristica.pdf
│
├── src/                   # ⚠️ EMPTY DUPLICATE - TO BE DELETED
│   ├── api/              # Empty scaffolding (0 files)
│   ├── frontend/         # Empty scaffolding (0 files)
│   └── modules/          # Empty scaffolding (0 files)
│
├── .github/
│   ├── workflows/main.yml
│   └── ISSUE_TEMPLATE/
│
├── docker-compose.yml     # 7 services orchestration
├── Makefile              # Build/start/stop commands
├── run-app.sh            # Startup script
└── README.md

```

## Key Files Locations

### Configuration Files (Duplicated)
1. `/algorithm/engines/rules.json`
2. `/api/src/main/resources/rules.json`
3. `/modules/rules.json`

### Dockerfiles
1. `/api/Dockerfile`
2. `/frontend/Dockerfile`
3. `/frontend/Dockerfile.dev`
4. `/modules/Dockerfile`

### Python Entry Points
1. `/modules/RabbitMQClient.py` - Schedule generation worker
2. `/modules/analyze.py` - KPI analysis worker

## Docker Compose Services

```yaml
services:
  - mongo (MongoDB database)
  - mongo-express (DB admin UI)
  - rabbitmq (Message queue)
  - python-modules (Schedule generator worker)
  - analyzer (KPI analysis worker)
  - api (Java Spring Boot backend)
  - frontend (React web app)
```

## Critical Dependencies

### modules/ depends on algorithm/
- `from modules.MongoDBClient import MongoDBClient`
- `from modules.TaskManager import TaskManager`
- TaskManager imports from algorithm/*

### analyzer depends on algorithm/
- `from algorithm.kpiComparison import analyze as compareKpis`
- `from algorithm.kpiVerification import analyze as verifyKpis`

## Issues Identified

1. ✅ **Empty `/src` directory** - Contains no source files, safe to delete
2. ⚠️ **Configuration duplication** - `rules.json` in 3 locations
3. ⚠️ **Unclear service boundaries** - `/modules` and `/algorithm` are tightly coupled but separated
4. ⚠️ **Flat root structure** - Hard to navigate, no clear service grouping
5. ⚠️ **Minimal documentation** - No architecture docs, setup guides, or service documentation

## Git Status at Start

**Branch:** chore/repo-reorganization
**Main branch:** main

**Untracked files:**
- `2025-11-18-i-want-you-to-present-to-me-the-organization-of-th.txt`

**Recent commits:**
- 5578854 Change base image to eclipse-temurin:17-jdk
- 7c94d89 fixes on README.md
- 5057432 added README.md and PI report
- 348822b cleaned repo

---

**Note:** This document serves as a reference point. All changes during reorganization will be tracked in `CHANGES.md`.
