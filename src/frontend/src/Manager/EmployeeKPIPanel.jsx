import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  Paper,
  Divider,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Chip,
} from "@mui/material";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const SKILL_COLORS = {
  Management: { bg: "#E6F1FB", text: "#0C447C", bar: "#185FA5" },
  Checkout:   { bg: "#EAF3DE", text: "#27500A", bar: "#3B6D11" },
  Storage:    { bg: "#FAEEDA", text: "#633806", bar: "#854F0B" },
  Employees:  { bg: "#F1EFE8", text: "#444441", bar: "#5F5E5A" },
};

function skillColor(skill) {
  return SKILL_COLORS[skill] || { bg: "#EEEDFE", text: "#3C3489", bar: "#534AB7" };
}

function StatCard({ label, value, sub, highlight }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        bgcolor: "action.hover",
        borderRadius: 1,
        borderLeft: highlight ? "3px solid" : "none",
        borderColor: highlight || "transparent",
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography variant="h5" fontWeight={500} sx={{ lineHeight: 1.3, mt: 0.25 }}>
        {value}
      </Typography>
      {sub && (
        <Typography variant="caption" color="text.disabled">
          {sub}
        </Typography>
      )}
    </Paper>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Skill usage bar
// ─────────────────────────────────────────────────────────────────────────────

function SkillUsageBar({ skill_usage_pct }) {
  if (!skill_usage_pct || Object.keys(skill_usage_pct).length === 0) return null;

  const entries = Object.entries(skill_usage_pct).sort((a, b) => b[1] - a[1]);

  return (
    <Box>
      {/* Stacked bar */}
      <Box
        sx={{
          display: "flex",
          height: 8,
          borderRadius: 4,
          overflow: "hidden",
          mb: 1,
        }}
      >
        {entries.map(([skill, pct]) => {
          const c = skillColor(skill);
          return (
            <Box
              key={skill}
              sx={{ width: `${pct}%`, bgcolor: c.bar, transition: "width .3s ease" }}
              title={`${skill}: ${pct}%`}
            />
          );
        })}
      </Box>

      {/* Legend */}
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {entries.map(([skill, pct]) => {
          const c = skillColor(skill);
          return (
            <Box
              key={skill}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                px: 1,
                py: 0.25,
                borderRadius: "999px",
                bgcolor: c.bg,
              }}
            >
              <Typography variant="caption" fontWeight={500} sx={{ color: c.text }}>
                {skill}
              </Typography>
              <Typography variant="caption" sx={{ color: c.text }}>
                {pct}%
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Daily segments table
// ─────────────────────────────────────────────────────────────────────────────

function DailySegmentsView({ daily_segments, daily_detail, filterDay }) {
  const entries = useMemo(() => {
    let all = Object.entries(daily_segments || {}).sort(([a], [b]) =>
      a.localeCompare(b)
    );
    if (filterDay) all = all.filter(([d]) => d === filterDay);
    return all;
  }, [daily_segments, filterDay]);

  if (entries.length === 0)
    return (
      <Typography variant="caption" color="text.disabled">
        No working days match the filter.
      </Typography>
    );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      {entries.map(([date, segCount]) => {
        const detail = daily_detail?.[date] || [];
        return (
          <Paper
            key={date}
            elevation={0}
            sx={{
              border: "0.5px solid",
              borderColor: "divider",
              borderRadius: 1,
              overflow: "hidden",
            }}
          >
            {/* Day header */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                px: 1.5,
                py: 0.75,
                bgcolor: "action.hover",
              }}
            >
              <Typography variant="caption" fontWeight={500}>
                {date}
              </Typography>
              <Chip
                label={`${segCount} segment${segCount !== 1 ? "s" : ""}`}
                size="small"
                sx={{
                  fontSize: 10,
                  height: 18,
                  bgcolor: segCount > 3 ? "#FEF2F2" : "#ECFDF5",
                  color: segCount > 3 ? "#7F1D1D" : "#065F46",
                }}
              />
            </Box>

            {/* Segment list */}
            {detail.length > 0 && (
              <Box sx={{ px: 1.5, py: 0.75, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                {detail.map((seg, i) => {
                  const c = skillColor(seg.skill);
                  return (
                    <Box
                      key={i}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.5,
                        px: 1,
                        py: 0.25,
                        borderRadius: 1,
                        bgcolor: c.bg,
                        fontSize: 11,
                      }}
                    >
                      <Typography variant="caption" sx={{ color: c.text, fontWeight: 500 }}>
                        {seg.start}–{seg.end}
                      </Typography>
                      <Typography variant="caption" sx={{ color: c.text }}>
                        @{seg.skill}
                      </Typography>
                      <Typography variant="caption" sx={{ color: c.text, opacity: 0.7 }}>
                        ({seg.duration_h}h)
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            )}
          </Paper>
        );
      })}
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export default function EmployeeKPIPanel({ kpis }) {
  const [selectedEmpId, setSelectedEmpId] = useState("");
  const [filterDay, setFilterDay]         = useState("");

  const employees = kpis?.Employee_KPIs?.employees ?? [];
  if (employees.length === 0) return null;

  const emp = employees.find((e) => e.emp_id === selectedEmpId) || null;

  // Day options for the second filter — only working days of selected employee
  const dayOptions = useMemo(() => {
    if (!emp) return [];
    return Object.keys(emp.daily_segments || {}).sort();
  }, [emp]);

  const consecutiveColor =
    !emp ? "text.primary"
    : emp.max_consecutive_days > 5 ? "error.main"
    : emp.max_consecutive_days === 5 ? "warning.main"
    : "success.main";

  return (
    <Box mt={3}>
      <Divider sx={{ mb: 1.5 }} />

      <Typography
        variant="overline"
        sx={{
          display: "block",
          mb: 1.5,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: "text.secondary",
        }}
      >
        Per-employee KPIs
      </Typography>

      {/* ── Filter row ── */}
      <Box sx={{ display: "flex", gap: 1.5, mb: 2, flexWrap: "wrap" }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel sx={{ fontSize: 13 }}>Employee</InputLabel>
          <Select
            value={selectedEmpId}
            label="Employee"
            onChange={(e) => {
              setSelectedEmpId(e.target.value);
              setFilterDay("");
            }}
            sx={{ fontSize: 13 }}
          >
            <MenuItem value="">
              <em>Select an employee</em>
            </MenuItem>
            {employees.map((e) => (
              <MenuItem key={e.emp_id} value={e.emp_id} sx={{ fontSize: 13 }}>
                {e.emp_id}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {emp && (
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel sx={{ fontSize: 13 }}>Filter by day</InputLabel>
            <Select
              value={filterDay}
              label="Filter by day"
              onChange={(e) => setFilterDay(e.target.value)}
              sx={{ fontSize: 13 }}
            >
              <MenuItem value="">
                <em>All days</em>
              </MenuItem>
              {dayOptions.map((d) => (
                <MenuItem key={d} value={d} sx={{ fontSize: 13 }}>
                  {d}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Box>

      {/* ── Employee detail ── */}
      {!emp ? (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            border: "0.5px solid",
            borderColor: "divider",
            borderRadius: 2,
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.disabled">
            Select an employee to view their KPIs.
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>

          {/* ── Summary cards ── */}
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1 }}>
            <StatCard
              label="Total worked hours"
              value={`${emp.total_worked_hours}h`}
              sub="over scheduling period"
            />
            <StatCard
              label="Working days"
              value={emp.total_working_days}
              sub="days with at least one shift"
            />
            <StatCard
              label="Max consecutive days"
              value={emp.max_consecutive_days}
              sub={emp.max_consecutive_days > 5 ? "exceeds limit of 5" : "within limit"}
              highlight={
                emp.max_consecutive_days > 5
                  ? "#DC2626"
                  : emp.max_consecutive_days === 5
                  ? "#D97706"
                  : undefined
              }
            />
          </Box>

          {/* ── Skill usage ── */}
          <Paper
            elevation={0}
            sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
              fontWeight={500}
              display="block"
              mb={1}
            >
              Skill usage
            </Typography>
            <SkillUsageBar skill_usage_pct={emp.skill_usage_pct} />
          </Paper>

          {/* ── Daily segments ── */}
          <Paper
            elevation={0}
            sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                mb: 1,
              }}
            >
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                Daily segments
              </Typography>
              <Typography variant="caption" color="text.disabled">
                {filterDay ? filterDay : `${Object.keys(emp.daily_segments).length} days`}
              </Typography>
            </Box>
            <DailySegmentsView
              daily_segments={emp.daily_segments}
              daily_detail={emp.daily_detail}
              filterDay={filterDay}
            />
          </Paper>
        </Box>
      )}
    </Box>
  );
}