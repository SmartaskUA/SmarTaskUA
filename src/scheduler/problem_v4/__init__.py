"""Schema v4 for the solvers: one parser, one instance, one scorer, one writer.

    inst = load_package("path/to/package")      # the only v4 parser
    rows = <any v4 solver>(inst)                # ILP/CSP MD7, Hybrid, GA v4
    evaluate(inst, rows)                        # the shared KPIs
    write_package(inst, rows, "out/")           # result.json + sidecar

A partial result in the package is applied as fixed days on the same instance;
without one, nothing is fixed and every path is the same.
"""

from .directives import SolveDirectives
from .evaluate import evaluate, fixed_days, objective
from .instance import (
    REST_CODE,
    WORK_MODES,
    Employee,
    FixedDay,
    Legislation,
    ParseError,
    Shift,
    TimeSlot,
    V4Instance,
)
from .loader import load_package
from .result_writer import ResultError, result_from_rows, write_package
from .rows import IDLE, UNASSIGNED, format_worked_cell, parse_worked_cell, rest_cell

__all__ = [
    "REST_CODE", "WORK_MODES", "IDLE", "UNASSIGNED",
    "Employee", "FixedDay", "Legislation", "ParseError", "ResultError", "Shift", "SolveDirectives",
    "TimeSlot", "V4Instance",
    "evaluate", "fixed_days", "format_worked_cell", "load_package", "objective", "parse_worked_cell",
    "rest_cell", "result_from_rows", "write_package",
]
