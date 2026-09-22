from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from typing import Any, List

_REPO_ROOT = Path(__file__).resolve().parents[2]


def default_export_dir() -> Path:
    """Same folder used by TaskManager (SCHEDULE_EXPORT_DIR), with a fallback
    to <repo_root>/exports when running locally without Docker."""
    env_dir = os.environ.get("SCHEDULE_EXPORT_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return _REPO_ROOT / "exports"


def is_table(result: Any) -> bool:
    return isinstance(result, list) and bool(result) and all(isinstance(row, list) for row in result)


def build_export_filename(algorithm_name: str, task_id: str) -> str:
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in algorithm_name)
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    return f"{safe_name}_{task_id}_{timestamp}.csv"


def export_table_to_csv(table: List[List[Any]], export_dir: Path, filename: str) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    output_path = export_dir / filename
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(table)
    return output_path