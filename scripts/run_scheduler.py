from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    scheduler_dir = src_dir / "scheduler"

    for candidate in (repo_root, src_dir, scheduler_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_paths()

from scheduler.cli import main


if __name__ == "__main__":
    raise SystemExit(main())