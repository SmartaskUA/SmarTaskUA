# Getting Started

## Prerequisites

- **Docker** & **Docker Compose** installed
- **Git** for cloning the repository
- (Optional) **Maven** for local Java development
- (Optional) **Node.js 18** for local frontend development

**Note:** Developed on Linux (Ubuntu/Arch). May need adjustments for Windows/MacOS.

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd SmarTaskUA

# 2. Build and start all services
make build

# 3. Access the application (all behind the nginx proxy)
# Main App:       http://localhost/ (manager/manager)
# JSON Generator: http://localhost/json-gen
# API:            http://localhost/api
```

That's it! The system is running.

## Common Commands

```bash
# Show all available commands
make help

# Start services (without rebuilding)
make up

# Stop all services
make down
```

## Common Development Tasks

### Adding a New Algorithm

1. Create `src/scheduler/algorithms/my_algorithm.py`
2. Implement `solve(vacations, minimuns, employees, maxTime, year, shifts, rules)` function
3. Add to `src/scheduler/TaskManager.py` algorithms dictionary
4. Test via Web UI by selecting your algorithm

### Modifying Business Rules

1. Edit `config/rules.json` (master copy)
2. Rebuild services: `make build`
3. Restart to apply changes

**⚠️ Never edit:** `src/api/src/main/resources/rules.json` or `src/scheduler/rules.json` (generated files)

## Next Steps

- **System architecture:** See `docs/architecture/system-overview.md`
- **Service details:** See READMEs in `src/api/`, `src/frontend/`, `src/json-generator/`, `src/scheduler/`, `src/analyzer/`, `infra/`
- **Algorithms:** See `docs/algorithms/overview.md`
- **Configuration:** See `config/README.md`
