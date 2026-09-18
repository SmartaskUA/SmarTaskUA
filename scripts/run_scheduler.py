from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
import time
from typing import Any, List


def _bootstrap_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    scheduler_dir = src_dir / "scheduler"

    for candidate in (repo_root, src_dir, scheduler_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_paths()

from scheduler.export_utils import (
    default_export_dir as _default_export_dir,
    is_table as _is_table,
    build_export_filename as _build_export_filename,
    export_table_to_csv as _export_table_to_csv,
)

from scheduler.cli import main


if __name__ == "__main__":
    raise SystemExit(main())