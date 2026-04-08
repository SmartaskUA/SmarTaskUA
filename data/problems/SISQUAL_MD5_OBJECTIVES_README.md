MD5 objective fixtures for `ILP_Sisqual_Hours_MathematicalDefinition5.py`

- `SISQUAL_MD5_OBJ1_COVERAGE`: isolates ObjectiveFunction1. The employee can cover either `Checkout` or `Management`, and the coverage objective should push the assignment to `Checkout`.
- `SISQUAL_MD5_OBJ2_LEVEL_SHORTAGE`: isolates ObjectiveFunction2. Two multi-skilled employees are present, and `beta_requirements.csv` forces one level-1 `Checkout` assignment and one level-1 `Management` assignment.
- `SISQUAL_MD5_OBJ3_AVERAGE_COMPETENCE`: isolates ObjectiveFunction3. The employee can cover either `Checkout` or `Management`, and the competence objective should push the assignment to the best level.
- `SISQUAL_MD5_OBJ4_DAY_OFF_SWAP`: exercises ObjectiveFunction4 together with ObjectiveFunction1. The employee has one `DO` marker inside a week, and coverage pressure on that day should make the solver swap one normal workday out and work the preferred day-off.

All fixtures read objective weights from `problem.json -> constraints.soft`.
All fixtures declare `optimization.algorithm = "ILP_Sisqual_Hours_MathematicalDefinition5"`.

Quick runs from repo root:

```bash
python3 src/scheduler/algorithms/ILP_Sisqual_Hours_MathematicalDefinition5.py data/problems/SISQUAL_MD5_OBJ1_COVERAGE/problem.json
python3 src/scheduler/algorithms/ILP_Sisqual_Hours_MathematicalDefinition5.py data/problems/SISQUAL_MD5_OBJ2_LEVEL_SHORTAGE/problem.json
python3 src/scheduler/algorithms/ILP_Sisqual_Hours_MathematicalDefinition5.py data/problems/SISQUAL_MD5_OBJ3_AVERAGE_COMPETENCE/problem.json
python3 src/scheduler/algorithms/ILP_Sisqual_Hours_MathematicalDefinition5.py data/problems/SISQUAL_MD5_OBJ4_DAY_OFF_SWAP/problem.json
```

Expected behavior:

- `OBJ1`: `E1` should be assigned to `Checkout`.
- `OBJ2`: `E1` should cover `Checkout` and `E2` should cover `Management`.
- `OBJ3`: `E1` should be assigned to `Management` because level `1` is preferred over level `3`.
- `OBJ4`: `E1` should work the `DO` day and one of the normal `4` days should become `OFF`.
