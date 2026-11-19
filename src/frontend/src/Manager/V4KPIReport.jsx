import React from "react";
import {
  Box, Divider, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Tooltip, Typography,
} from "@mui/material";

// KPIs of a schema v4 schedule, as computed by src/scheduler/problem_v4/evaluate.py:
// the same numbers for every v4 algorithm, so runs compare directly.

// Design tokens shared with SisqualKPIReport.jsx / KPIReport.jsx
const T = {
  pass: { bg: "#ECFDF5", text: "#065F46", border: "#059669" },
  fail: { bg: "#FEF2F2", text: "#7F1D1D", border: "#DC2626" },
  warn: { bg: "#FFFBEB", text: "#78350F", border: "#D97706" },
  neutral: { bg: "#F8FAFC", text: "#475569", border: "#CBD5E1" },
};

function Tile({ label, value, hint, tone = T.neutral }) {
  return (
    <Paper
      elevation={0}
      sx={{ p: 2, flex: "1 1 180px", backgroundColor: tone.bg, border: `1px solid ${tone.border}`, borderRadius: 2 }}
    >
      <Typography variant="overline" sx={{ fontSize: 10, fontWeight: 700, color: tone.text }}>
        {label}
      </Typography>
      <Typography variant="h5" sx={{ fontWeight: 800, color: tone.text }}>
        {value}
      </Typography>
      {hint && (
        <Typography variant="caption" color="text.secondary">
          {hint}
        </Typography>
      )}
    </Paper>
  );
}

const fmt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("en-US"));

// Covered share of a skill's demand: green for covered, red for the shortage.
function CoverageBar({ pct }) {
  const tone = pct >= 100 ? T.pass : pct >= 90 ? T.warn : T.fail;
  return (
    <Box display="flex" alignItems="center" gap={1} minWidth={150}>
      <Box sx={{ flex: 1, height: 8, borderRadius: 4, backgroundColor: T.fail.bg, border: `1px solid ${T.neutral.border}`, overflow: "hidden" }}>
        <Box sx={{ width: `${Math.min(100, pct)}%`, height: "100%", backgroundColor: tone.border }} />
      </Box>
      <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 700, color: tone.text, minWidth: 48, textAlign: "right" }}>
        {pct.toFixed(1)}%
      </Typography>
    </Box>
  );
}

// One row per skill: demand, how much of it is covered, what is missing, what is extra.
// Older schedules carry only shortage/surplus per skill, so demand and cost show "—".
function SkillBreakdown({ kpis }) {
  const demand = kpis.demand_by_skill || {};
  const shortage = kpis.shortage_by_skill || {};
  const surplus = kpis.surplus_by_skill || {};
  const belowIdeal = kpis.ideal_shortage_by_skill || {};
  const cost = kpis.priority_cost_by_skill || null;
  const hasDemand = Object.keys(demand).length > 0;
  const hasIdeal = Number(kpis.total_ideal) > 0;
  const skills = [...new Set([...Object.keys(demand), ...Object.keys(shortage), ...Object.keys(surplus)])];
  if (skills.length === 0) return null;

  const rows = skills.map((skill) => {
    const need = demand[skill];
    const short = shortage[skill] || 0;
    const pct = need ? (100 * (need - short)) / need : null;
    const [axis, value] = skill.includes("/") ? skill.split("/") : ["", skill];
    return { skill, axis, value, need, short, extra: surplus[skill] || 0, ideal: belowIdeal[skill] || 0, cost: cost ? cost[skill] || 0 : null, pct };
  });
  // Worst-covered first, so the gaps are read first.
  rows.sort((a, b) => (a.pct ?? -a.short) - (b.pct ?? -b.short) || a.skill.localeCompare(b.skill));

  const head = { fontSize: 11, fontWeight: 700, color: T.neutral.text, textTransform: "uppercase", letterSpacing: 0.4 };
  const num = { fontVariantNumeric: "tabular-nums", textAlign: "right" };
  return (
    <>
      <Divider sx={{ my: 2.5 }} />
      <Typography variant="subtitle1" fontWeight={800}>
        Coverage by skill
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        Worker-slots per skill, worst-covered first. Team and Responsibility are counted separately, so one worker can
        count on both.
      </Typography>
      <Box sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={head}>Skill</TableCell>
              {hasDemand && <TableCell sx={{ ...head, ...num }}>Demand</TableCell>}
              {hasDemand && <TableCell sx={head}>Covered</TableCell>}
              <TableCell sx={{ ...head, ...num }}>
                <Tooltip title="worker-slots below the minimum"><span>Short</span></Tooltip>
              </TableCell>
              <TableCell sx={{ ...head, ...num }}>
                <Tooltip title="worker-slots above the minimum"><span>Surplus</span></Tooltip>
              </TableCell>
              {hasIdeal && (
                <TableCell sx={{ ...head, ...num }}>
                  <Tooltip title="worker-slots below the ideal; not in the objective"><span>Below ideal</span></Tooltip>
                </TableCell>
              )}
              {cost && (
                <TableCell sx={{ ...head, ...num }}>
                  <Tooltip title="sum of p_sl over this skill's covered demand"><span>Priority cost</span></Tooltip>
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.skill} sx={{ backgroundColor: r.short > 0 ? T.fail.bg : "transparent" }}>
                <TableCell>
                  <Typography variant="body2" fontWeight={700}>{r.value}</Typography>
                  <Typography variant="caption" color="text.secondary">{r.axis}</Typography>
                </TableCell>
                {hasDemand && <TableCell sx={num}>{fmt(r.need)}</TableCell>}
                {hasDemand && <TableCell>{r.pct === null ? "—" : <CoverageBar pct={r.pct} />}</TableCell>}
                <TableCell sx={{ ...num, fontWeight: 700, color: r.short > 0 ? T.fail.text : T.pass.text }}>{fmt(r.short)}</TableCell>
                <TableCell sx={{ ...num, color: r.extra > 0 ? T.warn.text : "text.secondary" }}>
                  {r.extra > 0 ? `+${fmt(r.extra)}` : "0"}
                </TableCell>
                {hasIdeal && <TableCell sx={num}>{fmt(r.ideal)}</TableCell>}
                {cost && <TableCell sx={num}>{fmt(r.cost)}</TableCell>}
              </TableRow>
            ))}
            <TableRow sx={{ "& td": { borderTop: `2px solid ${T.neutral.border}`, fontWeight: 800 } }}>
              <TableCell>Total</TableCell>
              {hasDemand && <TableCell sx={num}>{fmt(kpis.total_demand)}</TableCell>}
              {hasDemand && (
                <TableCell>
                  <CoverageBar pct={kpis.total_demand ? (100 * (kpis.total_demand - kpis.total_shortage)) / kpis.total_demand : 100} />
                </TableCell>
              )}
              <TableCell sx={num}>{fmt(kpis.total_shortage)}</TableCell>
              <TableCell sx={num}>{kpis.total_surplus ? `+${fmt(kpis.total_surplus)}` : "0"}</TableCell>
              {hasIdeal && <TableCell sx={num}>{fmt(kpis.ideal_shortage)}</TableCell>}
              {cost && <TableCell sx={num}>{fmt(kpis.priority_cost)}</TableCell>}
            </TableRow>
          </TableBody>
        </Table>
      </Box>
    </>
  );
}

const V4KPIReport = ({ kpis }) => {
  const demand = Number(kpis.total_demand) || 0;
  const shortage = Number(kpis.total_shortage) || 0;
  const coverage = demand ? (100 * (demand - shortage)) / demand : 100;
  const unassigned = Number(kpis.unassigned) || 0;
  // Days a partial result.json fixed (absent on schedules solved before this was recorded).
  const fixedDays = Number(kpis.fixed_days) || 0;
  // Keys added later are absent on older schedules: show their tiles only when present.
  const has = (key) => kpis[key] !== undefined && kpis[key] !== null;
  // Ideal headcount: shown only when the package sets an ideal (C2 leaves it at 0).
  const totalIdeal = Number(kpis.total_ideal) || 0;
  const idealShortage = Number(kpis.ideal_shortage) || 0;
  const dayOffWorked = Number(kpis.day_off_worked) || 0;
  const dayOffWorkedFixed = Number(kpis.day_off_worked_fixed) || 0;
  // Hard-rule breaches: any of them makes the result invalid.
  const violations = [
    ["missing employee rows", Number(kpis.missing_rows) || 0],
    ["shifts on unavailable days", Number(kpis.work_on_unavailable) || 0],
    ["slots on a skill not held", Number(kpis.foreign_skill_slots) || 0],
  ].filter(([, n]) => n > 0);

  return (
    <Paper elevation={0} sx={{ p: 3, mt: 3, border: "1px solid #e2e8f0", borderRadius: 3 }}>
      <Typography variant="h6" fontWeight={800} mb={2}>
        Schedule KPIs
      </Typography>
      <Stack direction="row" flexWrap="wrap" gap={2}>
        <Tile
          label="Demand covered"
          value={`${coverage.toFixed(1)}%`}
          hint={`${demand - shortage} of ${demand} worker-slots`}
          tone={shortage === 0 ? T.pass : coverage >= 90 ? T.warn : T.fail}
        />
        <Tile label="Shortage" value={shortage} hint="worker-slots below the minimum" />
        {has("total_surplus") && (
          <Tile label="Surplus" value={kpis.total_surplus} hint="worker-slots above the minimum" />
        )}
        {totalIdeal > 0 && (
          <Tile
            label="Ideal covered"
            value={`${((100 * (totalIdeal - idealShortage)) / totalIdeal).toFixed(1)}%`}
            hint={`${idealShortage} worker-slots below the ideal · not in the objective`}
            tone={idealShortage === 0 ? T.pass : T.warn}
          />
        )}
        <Tile label="Priority cost" value={kpis.priority_cost ?? "N/A"} hint="sum of p_sl over covered demand" />
        {has("objective") && (
          <Tile
            label="Objective"
            value={kpis.objective}
            hint="w1·shortage + w2·priority + w3·day-offs worked (default weights)"
          />
        )}
        {(dayOffWorked > 0 || dayOffWorkedFixed > 0) && (
          <Tile
            label="Preferred days off worked"
            value={dayOffWorked + dayOffWorkedFixed}
            hint={`${dayOffWorked} chosen by the solver · ${dayOffWorkedFixed} fixed by result.json`}
            tone={T.warn}
          />
        )}
        <Tile
          label="Work days without a shift"
          value={unassigned}
          hint={unassigned ? "the result is not valid" : "every work day has a shift"}
          tone={unassigned ? T.fail : T.pass}
        />
        {fixedDays > 0 && (
          <Tile
            label="Fixed days"
            value={fixedDays}
            hint={`kept from result.json · ${kpis.open_days ?? "?"} decided by the solver`}
          />
        )}
        {violations.length > 0 && (
          <Tile
            label="Rule violations"
            value={violations.reduce((sum, [, n]) => sum + n, 0)}
            hint={violations.map(([label, n]) => `${n} ${label}`).join(" · ")}
            tone={T.fail}
          />
        )}
      </Stack>
      <SkillBreakdown kpis={kpis} />
    </Paper>
  );
};

export default V4KPIReport;
