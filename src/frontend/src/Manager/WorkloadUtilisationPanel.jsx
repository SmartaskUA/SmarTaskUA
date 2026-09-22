import React, { useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Divider,
  Chip,
} from "@mui/material";

// ─────────────────────────────────────────────────────────────────────────────
// Small reusable pieces
// ─────────────────────────────────────────────────────────────────────────────

function SectionLabel({ children }) {
  return (
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
      {children}
    </Typography>
  );
}

function StatCard({ label, value, sub, accent }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        bgcolor: "action.hover",
        borderRadius: 1,
        ...(accent && { borderLeft: `3px solid ${accent}` }),
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography
        variant="h5"
        fontWeight={500}
        sx={{ lineHeight: 1.3, mt: 0.25, color: accent || "text.primary" }}
      >
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
// Employee utilisation list
// ─────────────────────────────────────────────────────────────────────────────

function EmployeeUtilList({ employees }) {
  const [showAll, setShowAll] = useState(false);

  const sorted = [...employees].sort(
    (a, b) => (b.utilisation_pct ?? 0) - (a.utilisation_pct ?? 0)
  );
  const visible = showAll ? sorted : sorted.slice(0, 8);

  const statusStyle = (status) => {
    if (status === "overloaded") return { bg: "#FEF2F2", text: "#7F1D1D", bar: "#DC2626" };
    if (status === "idle")       return { bg: "#FFFBEB", text: "#78350F", bar: "#D97706" };
    return { bg: "#ECFDF5", text: "#065F46", bar: "#059669" };
  };

  return (
    <Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
        {visible.map((emp) => {
          const pct = emp.utilisation_pct ?? 0;
          const s   = statusStyle(emp.status);
          return (
            <Box
              key={emp.emp_id}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                px: 1.5,
                py: 0.75,
                border: "0.5px solid",
                borderColor: "divider",
                borderRadius: 1,
                bgcolor: "background.paper",
              }}
            >
              {/* ID */}
              <Typography
                variant="caption"
                fontWeight={500}
                sx={{ minWidth: 80, color: "text.primary" }}
              >
                {emp.emp_id}
              </Typography>

              {/* Utilisation bar */}
              <Box sx={{ flex: 1, position: "relative" }}>
                <Box
                  sx={{
                    height: 5,
                    borderRadius: 2,
                    bgcolor: "action.selected",
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      height: "100%",
                      width: `${Math.min(pct, 100)}%`,
                      borderRadius: 2,
                      bgcolor: s.bar,
                      transition: "width .3s ease",
                    }}
                  />
                </Box>
              </Box>

              {/* Hours */}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ minWidth: 80, textAlign: "right" }}
              >
                {emp.actual_hours}h
                {emp.expected_hours != null && (
                  <span style={{ opacity: 0.6 }}> / {emp.expected_hours}h</span>
                )}
              </Typography>

              {/* Status chip */}
              <Chip
                label={pct != null ? `${pct}%` : "—"}
                size="small"
                sx={{
                  fontSize: 10,
                  height: 18,
                  minWidth: 44,
                  bgcolor: s.bg,
                  color: s.text,
                }}
              />
            </Box>
          );
        })}
      </Box>

      {sorted.length > 8 && (
        <Typography
          variant="caption"
          color="text.info"
          sx={{ mt: 0.75, display: "block", cursor: "pointer", textAlign: "center" }}
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show less" : `Show all ${sorted.length} employees`}
        </Typography>
      )}
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Skill allocation section
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

function SkillAllocationSection({ data }) {
  if (!data) return null;

  const {
    mean_segment_duration_hours,
    total_segments,
    total_active_employee_days,
    by_skill,
    per_employee,
  } = data;

  const totalHours = Object.values(by_skill || {}).reduce(
    (s, v) => s + v.total_hours, 0
  );

  const durColor =
    mean_segment_duration_hours >= 3 ? "#059669"
    : mean_segment_duration_hours >= 1.5 ? "#D97706"
    : "#DC2626";

  const maxChanges = per_employee
    ? Math.max(...per_employee.map(e => e.mean_changes_per_day), 0.01)
    : 0.01;

  const switchColor = (val) =>
    val < 1 ? "#059669" : val < 2 ? "#D97706" : "#DC2626";

  return (
    <Box mt={2}>
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
        Skill allocation
      </Typography>

      {/* ── STAT-B4 mean segment duration ── */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 1.5 }}>
        <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1, borderLeft: `3px solid ${durColor}` }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Mean segment duration (B4)
          </Typography>
          <Typography variant="h5" fontWeight={500} sx={{ color: durColor, lineHeight: 1.3, mt: 0.25 }}>
            {mean_segment_duration_hours}h
          </Typography>
          <Typography variant="caption" color="text.disabled">
            {total_segments} segments · {total_active_employee_days} active days
          </Typography>
        </Paper>

        {/* Time distribution stacked bar summary */}
        {by_skill && Object.keys(by_skill).length > 0 && (
          <Paper elevation={0} sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={500} display="block" mb={0.75}>
              Time by skill
            </Typography>
            <Box sx={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", mb: 0.75 }}>
              {Object.entries(by_skill)
                .sort((a, b) => b[1].total_hours - a[1].total_hours)
                .map(([skill, v]) => {
                  const pct = totalHours > 0 ? (v.total_hours / totalHours) * 100 : 0;
                  return (
                    <Box key={skill} sx={{ width: `${pct}%`, bgcolor: skillColor(skill).bar }} title={`${skill}: ${pct.toFixed(1)}%`} />
                  );
                })}
            </Box>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {Object.entries(by_skill)
                .sort((a, b) => b[1].total_hours - a[1].total_hours)
                .map(([skill, v]) => {
                  const pct  = totalHours > 0 ? (v.total_hours / totalHours * 100).toFixed(1) : "0.0";
                  const c    = skillColor(skill);
                  return (
                    <Box key={skill} sx={{ display: "flex", alignItems: "center", gap: 0.4, px: 0.75, py: 0.2, borderRadius: 1, bgcolor: c.bg }}>
                      <Typography variant="caption" fontWeight={500} sx={{ color: c.text, fontSize: 10 }}>{skill}</Typography>
                      <Typography variant="caption" sx={{ color: c.text, fontSize: 10 }}>{pct}%</Typography>
                    </Box>
                  );
                })}
            </Box>
          </Paper>
        )}
      </Box>

      {/* ── STAT-B3 per-employee mean skill changes ── */}
      {per_employee && per_employee.length > 0 && (
        <Paper elevation={0} sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={500} display="block" mb={1}>
            Mean skill changes / day — per employee (B3)
          </Typography>

          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {per_employee.map((emp) => {
              const pct   = Math.round((emp.mean_changes_per_day / maxChanges) * 100);
              const color = switchColor(emp.mean_changes_per_day);
              return (
                <Box
                  key={emp.emp_id}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    px: 1.5,
                    py: 0.75,
                    border: "0.5px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    bgcolor: "background.paper",
                  }}
                >
                  {/* Employee ID */}
                  <Typography variant="caption" fontWeight={500} sx={{ minWidth: 80 }}>
                    {emp.emp_id}
                  </Typography>

                  {/* Skills used badges */}
                  <Box sx={{ display: "flex", gap: 0.4, flexWrap: "wrap", minWidth: 100 }}>
                    {emp.skills_used.map((sk) => {
                      const c = skillColor(sk);
                      return (
                        <Box key={sk} sx={{ px: 0.6, py: 0.1, borderRadius: "3px", bgcolor: c.bg }}>
                          <Typography sx={{ fontSize: 9, fontWeight: 600, color: c.text }}>
                            {sk}
                          </Typography>
                        </Box>
                      );
                    })}
                  </Box>

                  {/* Bar */}
                  <Box sx={{ flex: 1, height: 5, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
                    <Box sx={{ height: "100%", width: `${pct}%`, bgcolor: color, borderRadius: 2, transition: "width .3s ease" }} />
                  </Box>

                  {/* Mean changes value */}
                  <Typography variant="caption" fontWeight={500} sx={{ color, minWidth: 34, textAlign: "right" }}>
                    {emp.mean_changes_per_day}
                  </Typography>

                  {/* Active days */}
                  <Typography variant="caption" color="text.disabled" sx={{ minWidth: 52, textAlign: "right" }}>
                    {emp.total_active_days}d
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Paper>
      )}
    </Box>
  );
}



export default function WorkloadUtilisationPanel({ kpis }) {
  const data = kpis?.Workload_Utilisation;
  if (!data) return null;

  const {
    max_min_gap_hours,
    idle_employees,
    idle_threshold_pct,
    overloaded_employees,
    assignments_used,
    assignments_possible,
    assignment_rate,
    employees,
  } = data;

  return (
    <Box mt={3}>
      <Divider sx={{ mb: 1.5 }} />
      <Typography
        variant="overline"
        sx={{
          display: "block",
          mb: 2,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: "text.secondary",
        }}
      >
        Workload utilisation
      </Typography>

      {/* ── Row 1: Gap + Idle + Overloaded + Assignments ── */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, mb: 1.5 }}>
        <StatCard
          label="Max-min gap"
          value={`${max_min_gap_hours}h`}
          sub="most vs least loaded"
        />
        <StatCard
          label="Idle employees"
          value={idle_employees}
          sub={`below ${idle_threshold_pct}% utilisation`}
          accent={idle_employees > 0 ? "#D97706" : undefined}
        />
        <StatCard
          label="Overloaded employees"
          value={overloaded_employees}
          sub="exceed contracted hours"
          accent={overloaded_employees > 0 ? "#DC2626" : undefined}
        />
        <StatCard
          label="Assignments used"
          value={`${assignments_used}/${assignments_possible}`}
          sub={`${assignment_rate}% selection rate`}
        />
      </Box>

      {/* ── Per-employee list ── */}
      <Paper
        elevation={0}
        sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}
      >
        <SectionLabel>Per-employee utilisation</SectionLabel>
        <EmployeeUtilList employees={employees || []} />
      </Paper>

      {/* ── Skill allocation (STAT-B3, B4) ── */}
      <SkillAllocationSection data={kpis?.Skill_Allocation_Stats} />
    </Box>
  );
}