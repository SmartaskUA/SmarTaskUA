#!/usr/bin/env python3
"""Solution-form validation: a solution cross-checked against the expanded problem
it solves. The solution schema *states* these references (an assignmentId must be
one of that worker-day's H_wd, problemId must match) but the JSON Schema layer
cannot enforce them -- they live in another file.

A mixin on SchemaValidator (reads self.problem/base/against/report). Imports core;
never transform.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import core  # sibling module in this package
from core import iso


class SolutionChecksMixin:
    # -- layer 3: solution against its expanded problem ------------------
    def _locate_expanded(self) -> Path | None:
        """The expanded problem to cross-check a solution against.

        Explicit --against wins; otherwise a single sibling *.expanded.json is
        used. Zero or several siblings is ambiguous -> None (caller warns).
        """
        if self.against:
            return self.against
        siblings = sorted(self.base.glob("*.expanded.json"))
        return siblings[0] if len(siblings) == 1 else None

    def validate_solution(self) -> None:
        """Cross-check a solution against the expanded problem it solves.

        The solution schema *states* these references (an assignmentId must be one
        of that worker-day's H_wd, problemId must match, and so on) but the JSON
        Schema layer cannot enforce them -- they live in another file. Without this
        a solution that assigns an impossible shift still validates. Mirrors the
        id-resolution done in validate_expanded, one form later.
        """
        r = self.report
        sol = self.problem

        exp_path = self._locate_expanded()
        if not exp_path or not exp_path.exists():
            r.warn(
                "no expanded problem found to cross-check this solution against "
                "(pass --against <problem.expanded.json>); ran the schema layer only"
            )
            return
        try:
            exp = json.loads(exp_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            r.warn(f"could not read expanded problem {exp_path} ({exc}); skipped cross-checks")
            return
        if exp.get("form") != "expanded":
            r.warn(f"{exp_path.name} is not an expanded problem (form={exp.get('form')!r}); skipped cross-checks")
            return

        prob_id = exp.get("metadata", {}).get("problemId")
        if sol.get("problemId") != prob_id:
            r.error(
                f"problemId {sol.get('problemId')!r} does not match the expanded problem's "
                f"metadata.problemId {prob_id!r}"
            )

        slot = exp.get("timeGrid", {}).get("slotMinutes", 15)
        competencies = {t["code"] for t in exp.get("demand", {}).get("organizationalUnits", {}).get("competencies", [])}
        catalog = {a["id"]: a for a in exp.get("assignmentCatalog", [])}
        emp_by_id = {e["id"]: e for e in exp.get("employees", {}).get("list", [])}

        # horizon of the problem being solved
        scope = exp.get("temporalScope", {})
        s, e = iso(scope.get("start", "")), iso(scope.get("end", ""))
        horizon = set()
        if s and e and s <= e:
            horizon = {(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)}

        # per worker-day availability from the expansion
        avail: dict[tuple[str, str], dict] = {}
        for entry in exp.get("availability", []):
            for day in entry.get("days", []):
                avail[(entry["employeeId"], day["date"])] = day

        def covered_slots(aid: str) -> set[int]:
            out: set[int] = set()
            for iv in catalog.get(aid, {}).get("intervals", []):
                out |= set(range(iv["startMin"] // slot, iv["endMin"] // slot))
            return out

        status = sol.get("producedBy", {}).get("status")

        for a in sol.get("assignments", []):
            eid = a["employeeId"]
            emp = emp_by_id.get(eid)
            if emp is None:
                r.error(f"solution assigns {eid!r}, who is not in the expanded problem's employees")
                continue
            for day in a.get("days", []):
                iso_d = day["date"]
                key = (eid, iso_d)
                if horizon and iso_d not in horizon:
                    r.error(f"{eid} {iso_d}: date is outside the problem's horizon")
                if key not in avail:
                    r.error(f"{eid} {iso_d}: no such worker-day in the expanded problem")
                    continue
                a_day = avail[key]

                aid = day.get("assignmentId")
                if aid is not None:
                    if aid not in a_day.get("assignmentIds", []):
                        r.error(
                            f"{eid} {iso_d}: assignmentId {aid!r} is not one of this worker-day's "
                            f"options [H_wd]; the solver cannot pick an assignment outside it"
                        )
                    if status in ("infeasible", "error"):
                        r.error(
                            f"{eid} {iso_d}: status is {status!r} but an assignment {aid!r} is "
                            "recorded; an infeasible/error run carries no assignments"
                        )

                # A locked (hard) seed must actually name a shift -- you cannot pin a rest.
                if day.get("locked") and aid is None:
                    r.error(
                        f"{eid} {iso_d}: locked is true but assignmentId is null; a locked day must "
                        "name an assignment (express a fixed day off on the expanded side, not here)"
                    )
                # Seed <-> expanded merge coherence: a forced pin on the expanded side fixes the day,
                # so a stated (seeded/locked) assignment may not disagree with it.
                forced = a_day.get("forced")
                if forced is not None and aid is not None and aid != forced:
                    r.error(
                        f"{eid} {iso_d}: assignmentId {aid!r} contradicts the expanded problem's "
                        f"forced pin {forced!r} for this worker-day"
                    )

                if day.get("workedPreferableDayOff") and a_day.get("dayOff") != "preferable":
                    r.error(
                        f"{eid} {iso_d}: workedPreferableDayOff is true, but this day is not a "
                        f"preferable day off in the problem (dayOff={a_day.get('dayOff')!r})"
                    )

                covered = covered_slots(aid) if aid is not None else set()
                day_obj = date.fromisoformat(iso_d)
                for sp in day.get("competencyPerSlot", []):
                    lo, hi, competency = sp["startMin"], sp["endMin"], sp["competency"]
                    if competency not in competencies:
                        r.error(f"{eid} {iso_d}: competencyPerSlot competency {competency!r} is not a known competency")
                    elif competency not in {t.get("competency") for t in core.active_competencies(emp.get("competencyAssignments", []), day_obj)}:
                        r.error(f"{eid} {iso_d}: competencyPerSlot serves competency {competency!r}, which the worker does not hold that day")
                    if hi <= lo:
                        r.error(f"{eid} {iso_d}: competencyPerSlot endMin {hi} is not after startMin {lo}")
                    for bound in (lo, hi):
                        if bound % slot:
                            r.error(f"{eid} {iso_d}: competencyPerSlot boundary {bound} is not on the {slot}-minute grid")
                    if aid is not None and not set(range(lo // slot, hi // slot)) <= covered:
                        r.error(f"{eid} {iso_d}: competencyPerSlot {lo}-{hi} falls outside the chosen assignment {aid!r}")

        for sf in sol.get("shortfalls", []):
            if horizon and sf["date"] not in horizon:
                r.error(f"shortfall on {sf['date']}: date is outside the problem's horizon")
            if sf["competency"] not in competencies:
                r.error(f"shortfall on {sf['date']}: unknown competency {sf['competency']!r}")
            if sf["endMin"] <= sf["startMin"]:
                r.error(f"shortfall on {sf['date']}: endMin {sf['endMin']} is not after startMin {sf['startMin']}")
            for bound in (sf["startMin"], sf["endMin"]):
                if bound % slot:
                    r.error(f"shortfall on {sf['date']}: boundary {bound} is not on the {slot}-minute grid")

        all_days = [d for a in sol.get("assignments", []) for d in a.get("days", [])]
        r.stats["employeesAssigned"] = len(sol.get("assignments", []))
        r.stats["seededDays"] = sum(1 for d in all_days if d.get("assignmentId") is not None)
        r.stats["lockedDays"] = sum(1 for d in all_days if d.get("locked"))
        r.stats["shortfalls"] = len(sol.get("shortfalls", []))
        r.stats["crossCheckedAgainst"] = exp_path.name
