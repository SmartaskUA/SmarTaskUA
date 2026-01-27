# JSON Problem Definition System

## Purpose

This directory contains the **unified JSON schema** for defining employee scheduling problems in a clear, domain-focused, human-readable format that is **decoupled from algorithm implementation**.

### Why This Exists

**Problem:** Scheduling algorithms need tabular data (rows of vacations, requirements, etc.), but problem definitions should be expressed in business terms that are easy to validate, maintain, and extend.

**Solution:** A 3-layer architecture:

```
Problem JSON → Transformer → Algorithm Inputs → Solver → CSV Output
(What)         (How)         (Implementation)
```

1. **Problem JSON** (this directory) - Business-readable problem definition
2. **Transformer** (to be implemented) - Converts JSON → algorithm inputs
3. **Algorithm** (existing) - ILP, CSP, Greedy solvers

---

## Design Principles

### 1. Separation of Concerns
- **Problem definition** is independent of **algorithm implementation**
- Switch algorithms without changing problem files
- Update business rules without touching solver code

### 2. Progressive Complexity
- **Simple problems** use basic features (teams, simple demand)
- **Complex problems** enable advanced features (competencies, multi-level demand, schedule input)
- Feature flags control which modules are active

### 3. Human-Readable
- ISO dates instead of day indices
- Named entities (employees, competencies, teams)
- Clear constraint descriptions
- Self-documenting structure

### 4. Validation-Friendly
- Formal JSON Schema for validation
- Required vs. optional fields clearly defined
- Conditional requirements based on feature flags

---

## What's Inside

```
json_generation/
├── schema.json                          # Formal JSON Schema with validation
├── examples/
│   ├── simple_problem.json              # Basic: 5 employees, 2 teams, 7 days
│   ├── medium_problem_teams.json        # Team model + full constraints
│   ├── medium_problem_competencies.json # Competency model + priorities
│   └── complex_problem.json             # ALL features (BFarias_Problema2.pdf)
├── FORMAT.md                            # Parameter reference guide
└── README.md                            # This file
```

---

## Quick Start

### 1. Choose Your Complexity

| Complexity | Use When | Example File |
|------------|----------|--------------|
| **Simple** | Basic scheduling with fixed teams | `simple_problem.json` |
| **Medium** | Need vacations, multiple constraints | `medium_problem_teams.json` |
| **Advanced** | Skill-based allocation, priorities | `medium_problem_competencies.json` |
| **Full** | All features (BFarias specs) | `complex_problem.json` |

### 2. Create Your Problem JSON

Start from an example, modify for your needs:

```bash
cp examples/simple_problem.json my_problem.json
# Edit my_problem.json with your data
```

### 3. Validate (optional)

```bash
# Validate against schema (requires JSON schema validator)
jsonschema -i my_problem.json schema.json
```

### 4. Transform & Solve

```python
from scheduler.preprocessor.problem_transformer import ProblemTransformer
from scheduler.TaskManager import TaskManager

# Load problem
with open('my_problem.json') as f:
    problem = json.load(f)

# Transform to algorithm inputs
transformer = ProblemTransformer(problem)
inputs = transformer.to_algorithm_inputs()

# Solve
manager = TaskManager()
result = manager.run_task(**inputs)
```

---

## Key Concepts

### Feature Flags
Control which optional modules are enabled:
- `useCompetencyModel` - Skill-based (vs. fixed teams)
- `useScheduleInput` - Pre-existing schedule with markings
- `useMultiLevelDemand` - Minimo/ideal/estimado levels
- `useAdvancedConstraints` - Day-off swapping, breaks
- And more...

### Employee Models
- **Team model** - Employees assigned to fixed teams (A, B, C)
- **Competency model** - Employees have skills with levels (EG-1, CAJ-2)

### Demand Models
- **Simple** - Just minimum and ideal coverage
- **Multi-level** - Minimo/ideal/estimado with priority hierarchies

---

## Documentation

- **[FORMAT.md](FORMAT.md)** - Complete parameter reference
- **[schema.json](schema.json)** - Formal JSON Schema
- **examples/** - 4 progressive examples

---

## Next Steps

1. **Implement Transformer** - Build `src/scheduler/preprocessor/problem_transformer.py`
2. **Test Transformation** - Verify JSON → algorithm inputs conversion
3. **Integrate with API** - Accept JSON problems via REST endpoints
4. **Add Validation** - Schema validation before transformation

---

## Based On

- **BFarias_Problema2.pdf** - Primary specification (latest)
- **BFarias_Doc_Sisqual.pdf** - Additional context
- Existing algorithm implementations (ILP, CSP, Greedy)
