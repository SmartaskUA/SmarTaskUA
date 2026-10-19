# cenario2_input_only — the smallest package

[cenario2_retail](../cenario2_retail/) with everything optional removed. What remains is what every package must carry:

| file | what it is |
|---|---|
| `problem.json` | the problem — cenario2_retail's, minus the `schedules` key |
| `days_demand.csv` | workload minutes per day (header-only, as Sisqual sends it) |
| `periods_demand.csv` | headcount per window — the 313 rows of demand |
| `shifts_demand.csv` | headcount per shift type (header-only, as Sisqual sends it) |
| `schedule_input.csv` | what each employee's day asks for |

There is **no shift menu** and **no result**. That is a complete input: the menu is only needed once a result has to be checked against the shifts on offer.

```bash
cd ../..                                    # schema_v4/
make validate DIR=examples/cenario2_input_only ARGS=-v
```

The problem validates with the same warnings as cenario2_retail's. Every CSV except `problem.json` is byte-identical to cenario2_retail's, and `tests/test_examples.py` keeps it that way.
