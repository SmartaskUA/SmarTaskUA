import React, { useMemo, useState } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Chip,
  Paper,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip as ChartTooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ChartTooltip, Legend);

const MONTH_LABELS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const T = {
  pass: { bg: "#ECFDF5", text: "#065F46", border: "#059669" },
  fail: { bg: "#FEF2F2", text: "#7F1D1D", border: "#DC2626" },
};

// Monthly KPIs shown as tiles. `bad` = a value above zero is a problem.
const MONTH_TILES = [
  { key: "tmFails", label: "Backward Shift Sequences", bad: true, tip: "Times an employee works an earlier shift than the day before, in this month." },
  { key: "consecutiveDays", label: "Consecutive Work-Day Violations", bad: true, tip: "Times employees exceeded five consecutive working days, counted on the day the run goes over." },
  { key: "singleTeamViolations", label: "Single-Team Violations", bad: true, tip: "Employees allowed only one team who worked in more than one, in this month." },
  { key: "missedTeamMin", label: "Missed Minimums", bad: true, tip: "Missing staff against the minimum requirement, summed over the days of this month." },
  { key: "missedTeamIdeal", label: "Missed Ideals", bad: true, tip: "Missing staff against the ideal requirement, summed over the days of this month." },
  { key: "fixedDaysOffViolations", label: "Fixed Days-Off Violations", bad: true, optional: true, tip: "Employee week/month periods where the days off don't match the configured target." },
  { key: "shiftBalance", label: "Shift Balance", percent: true, tip: "Balance between morning, afternoon and night shifts for the least balanced employee, in this month." },
  { key: "teamSatisfactionLevel", label: "Team Satisfaction Level", percent: true, tip: "Share of work done in each employee's preferred team, in this month." },
];

// Raw counts for the month: informative, with no target attached.
const MONTH_COUNTS = [
  { key: "workedDays", label: "Days worked", tip: "Work shifts assigned in this month, summed over all employees." },
  { key: "vacationDays", label: "Vacation days", tip: "Vacation days in this month, summed over all employees." },
  { key: "specialDaysWorked", label: "Holiday/Sunday days worked", tip: "Holiday and Sunday work shifts in this month, summed over all employees." },
];

// Metrics for the evolution chart, grouped by comparable scale.
const CHART_GROUPS = [
  {
    id: "staffing",
    label: "Staffing",
    yLabel: "People",
    metrics: [
      { key: "missedTeamMin", label: "Missed minimums", color: "#DC2626" },
      { key: "missedTeamIdeal", label: "Missed ideals", color: "#D97706" },
    ],
  },
  {
    id: "rules",
    label: "Rule violations",
    yLabel: "Occurrences",
    metrics: [
      { key: "tmFails", label: "Backward Shift Sequences", color: "#7C3AED" },
      { key: "consecutiveDays", label: "6+ consecutive days", color: "#DB2777" },
      { key: "singleTeamViolations", label: "Single-team violations", color: "#0891B2" },
      { key: "fixedDaysOffViolations", label: "Fixed days-off violations", color: "#65A30D" },
    ],
  },
  {
    id: "workload",
    label: "Workload (counts)",
    yLabel: "Days",
    metrics: [
      { key: "workedDays", label: "Days worked", color: "#2563EB" },
      { key: "vacationDays", label: "Vacation days", color: "#EA580C" },
      { key: "specialDaysWorked", label: "Holiday/Sunday days worked", color: "#475569" },
    ],
  },
  {
    id: "special",
    label: "Holidays & Sundays (cumulative)",
    yLabel: "Days",
    metrics: [
      {
        key: "specialDaysWorkedCumulativeMax",
        label: "Most worked by one employee, year to date",
        color: "#475569",
      },
    ],
    limit: { key: "specialDaysLimit", label: "Annual limit" },
  },
  {
    id: "balance",
    label: "Balance (%)",
    yLabel: "%",
    metrics: [
      { key: "shiftBalance", label: "Shift balance", color: "#059669" },
      { key: "teamSatisfactionLevel", label: "Team satisfaction", color: "#4F46E5" },
    ],
  },
];

const formatValue = (value, percent) => {
  if (value === undefined || value === null) return "N/A";
  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";
  const text = Number.isInteger(n) ? String(n) : n.toFixed(1);
  return percent ? `${text}%` : text;
};

function InfoTip({ title }) {
  if (!title) return null;
  return (
    <Tooltip title={title} arrow placement="top">
      <HelpOutlineIcon sx={{ fontSize: 13, color: "text.disabled", flexShrink: 0 }} />
    </Tooltip>
  );
}

function MonthTile({ label, value, tone, tip, sub }) {
  const pal = tone ? T[tone] : null;
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: 1.5,
        bgcolor: pal ? pal.bg : "action.hover",
        border: pal ? `1px solid ${pal.border}` : "1px solid transparent",
        // Fixed floor instead of height:"100%" — Safari can misjudge the
        // stretched height of a CSS Grid item on auto-sized rows, letting
        // a tile's border overlap the row below it.
        minHeight: 84,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.25 }}>
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
          {label}
        </Typography>
        <InfoTip title={tip} />
      </Box>
      <Typography
        variant="h5"
        fontWeight={600}
        sx={{ lineHeight: 1.2, color: pal ? pal.text : "text.primary", fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </Typography>
      {sub && (
        <Typography variant="caption" color="text.disabled" sx={{ display: "block", mt: 0.25 }}>
          {sub}
        </Typography>
      )}
    </Paper>
  );
}

function MonthCard({ row }) {
  const tiles = MONTH_TILES.filter((t) => !t.optional || row[t.key] !== undefined);
  const hasIssues = tiles.some((t) => t.bad && Number(row[t.key] || 0) > 0);
  const limit = Number(row.specialDaysLimit);
  const cumulative = Number(row.specialDaysWorkedCumulativeMax);
  const overLimit = Number.isFinite(limit) && Number.isFinite(cumulative) && cumulative >= limit;

  return (
    <Accordion elevation={2} sx={{ borderRadius: 2 }} defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
        <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>
          KPIs for {MONTH_LABELS[(Number(row.month) || 1) - 1]}
        </Typography>
        <Chip
          label={hasIssues ? "Issues found" : "All clear"}
          size="small"
          sx={{
            height: 22, fontSize: 11, fontWeight: 600,
            bgcolor: hasIssues ? T.fail.bg : T.pass.bg,
            color: hasIssues ? T.fail.text : T.pass.text,
          }}
        />
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2.5, pb: 3 }}>
        <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
          The same KPIs as the yearly report, computed only on the days of this month. The yearly
          quotas (223 worked days, 30 vacation days, 22 holiday/Sunday days) are not split by month,
          so the workload below is shown as plain counts.
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 1 }}>
          {tiles.map((t) => {
            const raw = row[t.key];
            const bad = t.bad && Number(raw || 0) > 0;
            return (
              <MonthTile
                key={t.key}
                label={t.label}
                value={formatValue(raw, t.percent)}
                tip={t.tip}
                tone={t.percent ? null : bad ? "fail" : "pass"}
              />
            );
          })}
        </Box>
        <Typography variant="overline" sx={{ display: "block", mt: 2, mb: 1, fontSize: 10, fontWeight: 700, color: "text.secondary" }}>
          Workload in the month
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" }, gap: 1 }}>
          {MONTH_COUNTS.map((c) => (
            <MonthTile key={c.key} label={c.label} value={formatValue(row[c.key])} tip={c.tip} />
          ))}
          <MonthTile
            label="Holiday/Sunday, year to date"
            value={formatValue(cumulative)}
            sub={Number.isFinite(limit) ? `most worked by one employee · limit ${limit}` : undefined}
            tone={overLimit ? "fail" : null}
            tip="Highest number of holiday/Sunday days worked by a single employee from January up to the end of this month."
          />
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}

function EvolutionChart({ rows }) {
  const [groupId, setGroupId] = useState(CHART_GROUPS[0].id);
  const group = CHART_GROUPS.find((g) => g.id === groupId) || CHART_GROUPS[0];

  const chartData = useMemo(() => {
    const visible = group.metrics.filter((m) => rows.some((r) => r[m.key] !== undefined));
    const datasets = visible.map((m) => ({
      label: m.label,
      data: rows.map((r) => r[m.key] ?? null),
      borderColor: m.color,
      backgroundColor: m.color,
      tension: 0.25,
      pointRadius: 3,
    }));
    if (group.limit && rows.some((r) => r[group.limit.key] !== undefined)) {
      datasets.push({
        label: group.limit.label,
        data: rows.map((r) => r[group.limit.key] ?? null),
        borderColor: "#DC2626",
        backgroundColor: "#DC2626",
        borderDash: [6, 4],
        pointRadius: 0,
      });
    }
    return {
      labels: rows.map((r) => MONTH_LABELS[(Number(r.month) || 1) - 1].slice(0, 3)),
      datasets,
    };
  }, [rows, group]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { position: "bottom" } },
    scales: {
      x: { title: { display: true, text: "Month" } },
      y: { beginAtZero: true, title: { display: true, text: group.yLabel || "" } },
    },
  };

  return (
    <Accordion elevation={2} sx={{ borderRadius: 2, mt: 2 }} defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
        <Typography variant="subtitle1" fontWeight={700}>
          KPI evolution by month
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2.5, pb: 3 }}>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={groupId}
          onChange={(_, value) => value && setGroupId(value)}
          sx={{ mb: 2, flexWrap: "wrap" }}
        >
          {CHART_GROUPS.map((g) => (
            <ToggleButton key={g.id} value={g.id} sx={{ textTransform: "none", fontSize: 12 }}>
              {g.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Box sx={{ height: 320 }}>
          <Line data={chartData} options={options} />
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}

const MonthlyKpiReport = ({ breakdown, selectedMonth }) => {
  const rows = Array.isArray(breakdown) ? breakdown : [];
  if (!rows.length) return null;
  const row = rows.find((r) => Number(r.month) === Number(selectedMonth)) || rows[0];

  return (
    <Box sx={{ px: 0, mt: 2 }}>
      <MonthCard row={row} />
      <EvolutionChart rows={rows} />
    </Box>
  );
};

export default MonthlyKpiReport;
