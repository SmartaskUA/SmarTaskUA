"""What every v4 solver's `solve()` does around its model: load, fail, finish.

Failures are raised as `SisqualValidationError`, the exception RabbitMQClient
reports as FAILED_VALIDATION, so a rejected package or an infeasible model
reaches the user as a validation failure with its reasons, not as a crash.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Mapping, Optional

from .directives import SolveDirectives
from .instance import ParseError, V4Instance
from .loader import load_package
from .result_writer import write_package


def validation_error(problem_path, task_id: str, algorithm: str, failure_type: str,
                     messages: List[str], title: str):
    """A SisqualValidationError carrying `messages` as its issues. No files are written."""
    from validators.sisqual_feasibility import SisqualValidationError

    summary = f"{title}: {messages[0]}" if messages else title
    if len(messages) > 1:
        summary += f" (+{len(messages) - 1} more)"
    report = {
        "taskId": task_id,
        "status": "FAILED_VALIDATION",
        "failureType": failure_type,
        "summary": summary,
        "problemPath": str(problem_path) if problem_path else None,
        "algorithm": algorithm,
        "issueCount": len(messages),
        "errorCount": len(messages),
        "warningCount": 0,
        "issues": [
            {"code": failure_type, "severity": "error", "title": title, "message": m,
             "employeeId": None, "startDate": None, "endDate": None, "suggestedFix": None}
            for m in messages
        ],
        "generatedAt": datetime.now().isoformat(),
        "reportArtifacts": {},
    }
    return SisqualValidationError(summary, report)


def load_for_solver(problem_path, directives: SolveDirectives, task_id: str, algorithm: str) -> V4Instance:
    if not problem_path:
        raise ValueError(f"{algorithm} requires 'problem_path' pointing to a v4 problem.json or its folder")
    try:
        inst = load_package(problem_path, directives)
    except ParseError as exc:
        raise validation_error(problem_path, task_id, algorithm, "INVALID_V4_PACKAGE",
                               exc.problems, "Schema v4 package rejected") from exc
    for warning in inst.warnings:
        print(f"[{algorithm}] warning: {warning}")
    return inst


def solver_failure(problem_path, task_id: str, algorithm: str, status: str):
    """No schedule to return: infeasible, or out of time before a first solution."""
    infeasible = status.upper() == "INFEASIBLE"
    message = (f"{algorithm} returned status {status}. The parser's precheck found no contradiction, "
               "so the infeasibility depends on the full model." if infeasible else
               f"{algorithm} stopped with status {status} before finding any schedule; "
               "allow more time.")
    return validation_error(problem_path, task_id, algorithm,
                            "SOLVER_INFEASIBLE" if infeasible else "SOLVER_NO_SOLUTION",
                            [message], "Solver found no schedule")


def finish(inst: V4Instance, rows: List[List[str]], kwargs: Mapping) -> List[List[str]]:
    """Write the result package when the caller asked for one (`result_dir`)."""
    result_dir: Optional[str] = kwargs.get("result_dir")
    if result_dir:
        path = write_package(inst, rows, result_dir)
        print(f"[problem_v4] wrote {path}")
    return rows
