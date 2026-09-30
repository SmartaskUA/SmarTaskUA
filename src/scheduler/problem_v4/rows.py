"""The schedule rows every v4 solver returns, and how to read them back.

A row is ``[employee_id, cell per day]``. A worked cell lists one segment per
run of slots with the same skills, one skill per axis the worker covers there::

    09:00-12:00@Responsibility/A+Team/T1 | 12:00-17:00@Team/T1

``idle`` marks slots where the shift covers no demanded skill. A rest cell is
the schedule_input code (``DO``, ``HOL``) or ``OFF`` for a blank cell. The
evaluator and the result writer read these cells back, so this module is the
single definition of the format.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from .instance import Shift, V4Instance
from .schema_core import MINUTES_PER_DAY, hhmm_to_min, min_to_hhmm

IDLE = "idle"
UNASSIGNED = "UNASSIGNED"

_SEGMENT = re.compile(r"^\s*(\d{2}:\d{2})-(\d{2}:\d{2})@(\S+)\s*$")


def format_worked_cell(shift: Shift, slot_skills: Dict[int, Sequence[str]], slot_minutes: int) -> str:
    """One worked day: the shift's slots, merged into runs of equal skills."""
    segments: List[Tuple[int, int, str]] = []
    for t in shift.slot_indices:
        skills = slot_skills.get(t) or ()
        tag = "+".join(skills) if skills else IDLE
        start, end = t * slot_minutes, (t + 1) * slot_minutes
        if segments and segments[-1][2] == tag and segments[-1][1] == start:
            segments[-1] = (segments[-1][0], end, tag)
        else:
            segments.append((start, end, tag))
    return " | ".join(f"{min_to_hhmm(a)}-{min_to_hhmm(b)}@{tag}" for a, b, tag in segments)


def rest_cell(inst: V4Instance, eid: str, day: str) -> str:
    """What a day without a shift shows: its schedule_input code, or OFF."""
    return inst.raw_cell(eid, day) or "OFF"


def parse_worked_cell(text: str) -> Optional[List[Tuple[int, int, Tuple[str, ...]]]]:
    """[(startMin, endMin, skills)] for a worked cell, or None for anything else.

    Segments are contiguous, so a segment that restarts below the previous end
    has crossed midnight; minutes past 1440 are restored the same way the
    schema's windows are.
    """
    if not text or "@" not in text:
        return None
    out: List[Tuple[int, int, Tuple[str, ...]]] = []
    prev_end = None
    for part in str(text).split("|"):
        m = _SEGMENT.match(part)
        if not m:
            return None
        a, b = hhmm_to_min(m.group(1)), hhmm_to_min(m.group(2))
        if prev_end is not None:
            a += MINUTES_PER_DAY * ((prev_end - a + MINUTES_PER_DAY - 1) // MINUTES_PER_DAY)
        b = a + ((b - a) % MINUTES_PER_DAY or MINUTES_PER_DAY)
        tag = m.group(3)
        out.append((a, b, () if tag == IDLE else tuple(tag.split("+"))))
        prev_end = b
    return out
