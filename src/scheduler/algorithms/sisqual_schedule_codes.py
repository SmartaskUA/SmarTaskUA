"""Loads Sisqual's real ScheduleCode registry and looks up codes by time range.

The registry (`data/sisqual_schedule_codes.csv`, sourced from the "Schedule
Code Complete" file Sisqual provided) lists every ScheduleCode they
recognize. Each entry maps to one of:
  - a single continuous time range, e.g. "09:00-17:00"
  - a split shift: a continuous overall span with one unpaid break carved
    out of the middle, e.g. "07:30-15:30 (12:00-12:30)" -- worked 07:30 to
    15:30, on a break from 12:00 to 12:30, so ScheduleWeightMinutes is the
    480-minute span minus the 30-minute break = 450
  - a fixed non-worked label, e.g. "Day off", "Espaço", "Folga Complementar"

The registry is the source of truth for ScheduleWeightMinutes too: it is
NOT always the raw span between clock-in and clock-out -- confirmed
mathematically across all 89,390 break-annotated entries (span minus break
equals ScheduleWeightMinutes with zero exceptions).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from algorithms.sisqual_hours_utils import parse_hhmm

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "sisqual_schedule_codes.csv"

_SINGLE_RANGE_RE = re.compile(r"^(\d{2}:\d{2})-(\d{2}:\d{2})$")
_SPLIT_RANGE_RE = re.compile(r"^(\d{2}:\d{2})-(\d{2}:\d{2}) \((\d{2}:\d{2})-(\d{2}:\d{2})\)$")

# Sisqual's registry has only 4 non-worked codes -- far fewer than the 8
# distinct markers our solvers produce (DO/FDO/VAC/NOT/MED/CLOSED/OFF/
# UNASSIGNED). Per explicit direction, markers with no dedicated Sisqual
# code collapse onto the closest real concept: any deliberate day-off-style
# marker becomes "Day off"; anything representing an empty/unassigned cell
# becomes "Espaço" (blank). "Folga Complementar" (a compensatory day off) has
# no corresponding marker in our model and is intentionally left unused.
NON_WORKED_LABEL_BY_MARKER = {
    "DO": "Day off",
    "FDO": "Day off",
    "VAC": "Day off",
    "NOT": "Day off",
    "MED": "Day off",
    "CLOSED": "Espaço",
    "OFF": "Espaço",
    "UNASSIGNED": "Espaço",
}


class SisqualScheduleCodeRegistry:
    """Looks up real Sisqual ScheduleCodes by time range or non-worked label."""

    def __init__(self, registry_path: Path = DEFAULT_REGISTRY_PATH):
        self._by_time_range: Dict[Tuple[int, int], int] = {}
        self._by_split_range: Dict[Tuple[int, int, int, int], int] = {}
        self._by_label: Dict[str, int] = {}
        self._weight_by_code: Dict[int, int] = {}
        self._load(registry_path)

    def _load(self, registry_path: Path) -> None:
        with registry_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = int(row["Code"])
                description = row["Description"].strip()
                weight = int(row["ScheduleWeightMinutes"])
                self._weight_by_code[code] = weight

                split_match = _SPLIT_RANGE_RE.match(description)
                if split_match is not None:
                    start_min = parse_hhmm(split_match.group(1))
                    end_min = parse_hhmm(split_match.group(2))
                    break_start_min = parse_hhmm(split_match.group(3))
                    break_end_min = parse_hhmm(split_match.group(4))
                    self._add_best(
                        self._by_split_range,
                        (start_min, end_min, break_start_min, break_end_min),
                        code,
                    )
                    continue

                single_match = _SINGLE_RANGE_RE.match(description)
                if single_match is not None:
                    start_min = parse_hhmm(single_match.group(1))
                    end_min = parse_hhmm(single_match.group(2))
                    self._add_best(self._by_time_range, (start_min, end_min), code)
                    continue

                # Non-time label (e.g. "Day off", "Espaço", "Flexible").
                self._by_label.setdefault(description, code)

    @staticmethod
    def _add_best(table: Dict, key, code: int) -> None:
        # Sisqual's own registry has a handful of (start, end[, break]) keys
        # with more than one valid code (a legacy hand-picked one and the
        # equivalent grid-generated one). Pick the smaller code
        # deterministically -- both are valid, this is just a tiebreak, not
        # a confirmed preference from Sisqual.
        existing = table.get(key)
        if existing is None or code < existing:
            table[key] = code

    def code_for_time_range(self, start_min: int, end_min: int) -> Optional[int]:
        """Return the real ScheduleCode for a single continuous period, if any.

        Returns None if no registry entry matches exactly (e.g. the period
        isn't aligned to the registry's grid, or its duration falls outside
        the range the grid covers).
        """

        return self._by_time_range.get((start_min, end_min))

    def code_for_split_shift(
        self,
        start_min: int,
        end_min: int,
        break_start_min: int,
        break_end_min: int,
    ) -> Optional[int]:
        """Return the real ScheduleCode for a split shift, if any.

        `start_min`/`end_min` is the overall span; `break_start_min`/
        `break_end_min` is the single unpaid break carved out of the middle
        (i.e. period 1 is start_min..break_start_min, period 2 is
        break_end_min..end_min). Returns None if no exact match exists.
        """

        return self._by_split_range.get((start_min, end_min, break_start_min, break_end_min))

    def code_for_non_worked_marker(self, marker: str) -> Optional[int]:
        """Return the real ScheduleCode for a non-worked marker (DO, VAC, ...)."""

        label = NON_WORKED_LABEL_BY_MARKER.get(marker.upper())
        if label is None:
            return None
        return self._by_label.get(label)

    def weight_for_code(self, code: int) -> Optional[int]:
        """Return the registry's own ScheduleWeightMinutes for a real code."""

        return self._weight_by_code.get(code)
