#!/usr/bin/env python3
"""Expanded-form validation: conformance with MathematicalDefinition7 that a JSON
Schema cannot express -- the assignment catalog's intervals, H_wd within T_d,
mustCover/mustAvoid/mustBeWithin re-checks, forced pins, and the per-week working-day count.

A mixin on SchemaValidator (reads self.problem/base/report). Imports core and the
shared foundation; never transform.
"""

from __future__ import annotations

import csv
from collections import defaultdict

import core  # sibling module in this package
from common import parse_range
from core import iso, week_index


class ExpandedChecksMixin:
    # -- layer 3: expanded / V7 conformance -------------------------------
    def validate_expanded(self) -> None:
        p = self.problem
        r = self.report
        slot = p["timeGrid"]["slotMinutes"]

        catalog = {}
        for a in p.get("assignmentCatalog", []):
            catalog[a["id"]] = a
            covered = set()
            prev_end = None
            for iv in a["intervals"]:
                lo, hi = iv["startMin"], iv["endMin"]
                if hi <= lo:
                    r.error(f"assignment {a['id']}: endMin {hi} is not after startMin {lo}")
                if prev_end is not None and lo < prev_end:
                    r.error(
                        f"assignment {a['id']}: intervals are not in ascending order "
                        f"({lo} starts before the previous interval ended at {prev_end})"
                    )
                prev_end = hi
                for bound in (lo, hi):
                    if bound % slot:
                        r.error(
                            f"assignment {a['id']}: boundary {bound} min is not on the "
                            f"{slot}-minute grid"
                        )
                slots = set(range(lo // slot, hi // slot))
                if slots & covered:
                    r.error(f"assignment {a['id']}: intervals overlap each other")
                covered |= slots

        t_d = self._demand_slots(slot)
        open_days = {d for d, s in t_d.items() if s}
        week_start = p.get("calendar", {}).get("weekStart", "monday")
        days = self.horizon()
        origin = days[0] if days else None

        n_wk: dict[tuple[str, int], dict[str, int]] = defaultdict(
            lambda: {"open": 0, "unavailable": 0, "preferable": 0}
        )
        for d in open_days:
            dd = iso(d)
            if not dd or not origin:
                continue
            k = week_index(dd, origin, week_start)
            for emp in p.get("employees", {}).get("list", []):
                n_wk[(emp["id"], k)]["open"] += 1

        for entry in p.get("availability", []):
            eid = entry["employeeId"]
            for day in entry["days"]:
                iso_d = day["date"]
                ids = day.get("assignmentIds", [])
                day_off = day.get("dayOff")

                for aid in ids:
                    if aid not in catalog:
                        r.error(f"{eid} {iso_d}: assignmentId {aid!r} is not in assignmentCatalog")

                if day_off == "unavailable" and ids:
                    r.error(
                        f"{eid} {iso_d}: dayOff is 'unavailable' but {len(ids)} assignments are "
                        "offered; V7 constraint (5) forbids any assignment on an unavailable day"
                    )
                if day_off == "preferable" and not ids:
                    r.error(
                        f"{eid} {iso_d}: dayOff is 'preferable' but no assignments are offered. "
                        "A preferable day off is soft -- it may be worked at a penalty [x'_wd] -- "
                        "so with no options it is really 'unavailable'."
                    )
                if day.get("forced") and day["forced"] not in ids:
                    r.error(f"{eid} {iso_d}: forced assignment {day['forced']!r} is not in assignmentIds")

                if iso_d in open_days and not ids and day_off != "unavailable":
                    r.error(
                        f"{eid} {iso_d}: open day with no assignments and no 'unavailable' marker. "
                        "n_wk would count this day as workable while H_wd offers nothing, making "
                        "V7 constraint (6) unsatisfiable."
                    )

                # mustCover / mustAvoid carry the INCLUDE / EXCEPT constraints into the
                # expanded form so they are re-checkable here, not merely trusted from
                # the transformer.  Validate the windows are well-formed once, then
                # turn each into a slot-set to test every offered assignment against.
                def window_slots(windows, label):
                    out = []
                    for w in windows:
                        lo, hi = w["startMin"], w["endMin"]
                        if hi <= lo:
                            r.error(f"{eid} {iso_d}: {label} window {lo}-{hi} min has endMin <= startMin")
                        for bound in (lo, hi):
                            if bound % slot:
                                r.error(f"{eid} {iso_d}: {label} boundary {bound} min is not on the "
                                        f"{slot}-minute grid")
                        out.append((lo, hi, set(range(lo // slot, hi // slot))))
                    return out

                cover = window_slots(day.get("mustCover", []), "mustCover")
                avoid = window_slots(day.get("mustAvoid", []), "mustAvoid")
                within = window_slots(day.get("mustBeWithin", []), "mustBeWithin")

                # H_wd must not reach outside the demanded window (V7, H_wd definition).
                demanded = t_d.get(iso_d, set())
                for aid in ids:
                    a = catalog.get(aid)
                    if not a:
                        continue
                    covered = set()
                    for iv in a["intervals"]:
                        covered |= set(range(iv["startMin"] // slot, iv["endMin"] // slot))
                    if not covered <= demanded:
                        r.error(
                            f"{eid} {iso_d}: assignment {aid} covers timeslots outside T_d; V7 "
                            "requires H_wd to exclude such assignments entirely"
                        )
                    for lo, hi, wslots in cover:
                        if not wslots <= covered:
                            r.error(
                                f"{eid} {iso_d}: assignment {aid} does not cover required window "
                                f"{lo}-{hi} min (from an INCLUDE cell, recorded in mustCover)"
                            )
                    for lo, hi, wslots in avoid:
                        if wslots & covered:
                            r.error(
                                f"{eid} {iso_d}: assignment {aid} overlaps forbidden window "
                                f"{lo}-{hi} min (from an EXCEPT cell, recorded in mustAvoid)"
                            )
                    # WITHIN: the assignment must fit entirely inside one of the windows.
                    if within and not any(covered <= wslots for _, _, wslots in within):
                        allowed = ", ".join(f"{lo}-{hi} min" for lo, hi, _ in within)
                        r.error(
                            f"{eid} {iso_d}: assignment {aid} is not contained in any WITHIN "
                            f"window ({allowed}, recorded in mustBeWithin)"
                        )

                if iso_d in open_days and origin:
                    dd = iso(iso_d)
                    if dd:
                        k = week_index(dd, origin, week_start)
                        if day_off == "unavailable":
                            n_wk[(eid, k)]["unavailable"] += 1
                        elif day_off == "preferable":
                            n_wk[(eid, k)]["preferable"] += 1

        negative = 0
        for (eid, k), c in sorted(n_wk.items()):
            value = c["open"] - c["unavailable"] - c["preferable"]
            if value < 0:
                negative += 1
                r.error(
                    f"{eid} week {k}: derived n_wk is {value} (open {c['open']} - unavailable "
                    f"{c['unavailable']} - preferable {c['preferable']}); V7 constraint (6) "
                    "requires a non-negative working-day count"
                )

        referenced = {
            aid for entry in p.get("availability", [])
            for day in entry["days"] for aid in day.get("assignmentIds", [])
        }
        for dead in sorted(set(catalog) - referenced):
            r.warn(f"assignmentCatalog: {dead!r} is referenced by no worker-day")

        sizes = [len(d.get("assignmentIds", [])) for e in p.get("availability", [])
                 for d in e["days"] if d.get("assignmentIds")]
        r.stats["assignmentCatalog"] = len(catalog)
        r.stats["openDays"] = len(open_days)
        r.stats["weeks"] = len({k for _, k in n_wk})
        r.stats["negative_n_wk"] = negative
        r.stats["hwdMax"] = max(sizes) if sizes else 0
        r.stats["hwdMean"] = round(sum(sizes) / len(sizes), 1) if sizes else 0

    def _demand_slots(self, slot: int) -> dict[str, set[int]]:
        """T_d per date: the timeslots demanded on each day.

        Each demand row names a work period; the row's own start/end override it
        when present, otherwise the period's declared range applies.  A date with
        no rows is closed and lies outside D_o.
        """
        out: dict[str, set[int]] = defaultdict(set)
        demand = self.problem.get("demand", {})
        data_file = demand.get("dataFile")
        if not data_file:
            return out
        path = self.base / data_file
        if not path.exists():
            self.report.warn(f"demand file {path} not found; skipped the H_wd-within-T_d check")
            return out

        periods: dict[str, tuple[int, int]] = {}
        for wp in demand.get("workPeriods", []):
            tr = wp.get("timeRange")
            if tr:
                rng = parse_range(tr["start"], tr["end"])
                if rng:
                    periods[wp["code"]] = rng

        with path.open(newline="") as fh:
            for row in csv.DictReader(core.csv_lines(fh)):
                if not row.get("date"):
                    continue
                if row.get("start") and row.get("end"):
                    rng = parse_range(row["start"], row["end"])
                else:
                    rng = periods.get(row.get("workPeriod", ""))
                if rng:
                    out[row["date"]].update(range(rng[0] // slot, rng[1] // slot))
        return out
