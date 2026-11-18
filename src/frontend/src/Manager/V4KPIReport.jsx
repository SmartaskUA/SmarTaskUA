import React from "react";
import { Box, Chip, Divider, Paper, Stack, Typography } from "@mui/material";

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

const V4KPIReport = ({ kpis }) => {
  const demand = Number(kpis.total_demand) || 0;
  const shortage = Number(kpis.total_shortage) || 0;
  const coverage = demand ? (100 * (demand - shortage)) / demand : 100;
  const unassigned = Number(kpis.unassigned) || 0;
  const bySkill = Object.entries(kpis.shortage_by_skill || {});
  // Days a partial result.json fixed (absent on schedules solved before this was recorded).
  const fixedDays = Number(kpis.fixed_days) || 0;
  // Keys added later are absent on older schedules: show their tiles only when present.
  const has = (key) => kpis[key] !== undefined && kpis[key] !== null;
  const surplusBySkill = Object.entries(kpis.surplus_by_skill || {});
  // Ideal headcount: shown only when the package sets an ideal (C2 leaves it at 0).
  const totalIdeal = Number(kpis.total_ideal) || 0;
  const idealShortage = Number(kpis.ideal_shortage) || 0;
  const idealBySkill = Object.entries(kpis.ideal_shortage_by_skill || {});
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
      {bySkill.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" mb={1}>
            Shortage by skill
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {bySkill.map(([skill, value]) => (
              <Chip key={skill} label={`${skill}: ${value}`} size="small" variant="outlined" />
            ))}
          </Box>
        </>
      )}
      {totalIdeal > 0 && idealBySkill.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" mb={1}>
            Below the ideal, by skill
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {idealBySkill.map(([skill, value]) => (
              <Chip key={skill} label={`${skill}: ${value}`} size="small" variant="outlined" />
            ))}
          </Box>
        </>
      )}
      {surplusBySkill.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" mb={1}>
            Surplus by skill
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {surplusBySkill.map(([skill, value]) => (
              <Chip key={skill} label={`${skill}: +${value}`} size="small" variant="outlined" />
            ))}
          </Box>
        </>
      )}
    </Paper>
  );
};

export default V4KPIReport;
