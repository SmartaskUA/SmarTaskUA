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
      variant="caption"
      color="text.secondary"
      fontWeight={500}
      display="block"
      mb={1}
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
// Gini bar — visual representation of fairness index
// ─────────────────────────────────────────────────────────────────────────────

function GiniBar({ value }) {
  const pct   = Math.round(value * 100);
  const color = value < 0.1 ? "#3B6D11" : value < 0.2 ? "#854F0B" : "#A32D2D";
  const label = value < 0.1 ? "Fair" : value < 0.2 ? "Moderate" : "Unequal";

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          Fairness index (Gini)
        </Typography>
        <Chip
          label={label}
          size="small"
          sx={{
            fontSize: 10,
            height: 18,
            bgcolor: value < 0.1 ? "#EAF3DE" : value < 0.2 ? "#FAEEDA" : "#FCEBEB",
            color,
          }}
        />
      </Box>
      <Box
        sx={{
          height: 6,
          borderRadius: 3,
          bgcolor: "action.selected",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${pct}%`,
            borderRadius: 3,
            bgcolor: color,
            transition: "width .4s ease",
          }}
        />
      </Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.25 }}>
        <Typography variant="caption" color="text.disabled">
          0 — equal
        </Typography>
        <Typography variant="caption" fontWeight={500} sx={{ color }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.disabled">
          1 — unequal
        </Typography>
      </Box>
    </Box>
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
    if (status === "overloaded") return { bg: "#FCEBEB", text: "#791F1F" };
    if (status === "idle")       return { bg: "#FAEEDA", text: "#633806" };
    return { bg: "#EAF3DE", text: "#27500A" };
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
                      bgcolor:
                        emp.status === "overloaded"
                          ? "#A32D2D"
                          : emp.status === "idle"
                          ? "#854F0B"
                          : "#3B6D11",
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
    mean_skill_changes_per_day,
    mean_segment_duration_hours,
    total_segments,
    total_active_employee_days,
    by_skill,
  } = data;

  const totalHours = Object.values(by_skill || {}).reduce(
    (s, v) => s + v.total_hours, 0
  );

  const switchColor =
    mean_skill_changes_per_day < 1 ? "#3B6D11"
    : mean_skill_changes_per_day < 2 ? "#854F0B"
    : "#A32D2D";

  const durColor =
    mean_segment_duration_hours >= 3 ? "#3B6D11"
    : mean_segment_duration_hours >= 1.5 ? "#854F0B"
    : "#A32D2D";

  return (
    <Box mt={2}>
      <Divider sx={{ mb: 1.5 }} />
      <Typography
        variant="subtitle2"
        color="text.secondary"
        sx={{
          mb: 1.5,
          textTransform: "uppercase",
          letterSpacing: ".05em",
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        Skill allocation
      </Typography>

      {/* ── STAT-B2 + STAT-B3 ── */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 1.5 }}>
        <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1, borderLeft: `3px solid ${switchColor}` }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Mean skill changes / day (B2)
          </Typography>
          <Typography variant="h5" fontWeight={500} sx={{ color: switchColor, lineHeight: 1.3, mt: 0.25 }}>
            {mean_skill_changes_per_day}
          </Typography>
          <Typography variant="caption" color="text.disabled">
            {total_segments} total segments · {total_active_employee_days} active days
          </Typography>
        </Paper>

        <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1, borderLeft: `3px solid ${durColor}` }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Mean segment duration (B3)
          </Typography>
          <Typography variant="h5" fontWeight={500} sx={{ color: durColor, lineHeight: 1.3, mt: 0.25 }}>
            {mean_segment_duration_hours}h
          </Typography>
          <Typography variant="caption" color="text.disabled">
            avg continuous skill block
          </Typography>
        </Paper>
      </Box>

      {/* ── Skill breakdown ── */}
      {by_skill && Object.keys(by_skill).length > 0 && (
        <Paper
          elevation={0}
          sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}
        >
          <Typography variant="caption" color="text.secondary" fontWeight={500} display="block" mb={1}>
            Time distribution by skill
          </Typography>

          {/* Stacked bar */}
          <Box sx={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", mb: 1 }}>
            {Object.entries(by_skill)
              .sort((a, b) => b[1].total_hours - a[1].total_hours)
              .map(([skill, v]) => {
                const pct = totalHours > 0 ? (v.total_hours / totalHours) * 100 : 0;
                return (
                  <Box
                    key={skill}
                    sx={{ width: `${pct}%`, bgcolor: skillColor(skill).bar }}
                    title={`${skill}: ${pct.toFixed(1)}%`}
                  />
                );
              })}
          </Box>

          {/* Rows per skill */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {Object.entries(by_skill)
              .sort((a, b) => b[1].total_hours - a[1].total_hours)
              .map(([skill, v]) => {
                const pct  = totalHours > 0 ? (v.total_hours / totalHours * 100).toFixed(1) : "0.0";
                const c    = skillColor(skill);
                const avgD = v.segments > 0 ? (v.total_hours / v.segments).toFixed(2) : "—";
                return (
                  <Box
                    key={skill}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: c.bg,
                    }}
                  >
                    <Typography variant="caption" fontWeight={500} sx={{ color: c.text, minWidth: 90 }}>
                      {skill}
                    </Typography>
                    <Typography variant="caption" sx={{ color: c.text, flex: 1 }}>
                      {v.segments} segments · {v.total_hours}h
                    </Typography>
                    <Typography variant="caption" sx={{ color: c.text, opacity: 0.8 }}>
                      avg {avgD}h/seg
                    </Typography>
                    <Typography variant="caption" fontWeight={500} sx={{ color: c.text, minWidth: 40, textAlign: "right" }}>
                      {pct}%
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
    mean_utilisation,
    variance,
    max_min_gap_hours,
    fairness_index,
    idle_employees,
    idle_threshold_pct,
    overloaded_employees,
    assignments_used,
    assignments_possible,
    assignment_rate,
    employees,
  } = data;

  const meanColor =
    mean_utilisation >= 90 ? "success.main"
    : mean_utilisation >= 70 ? "warning.main"
    : "error.main";

  return (
    <Box mt={3}>
      <Divider sx={{ mb: 1.5 }} />
      <Typography
        variant="subtitle2"
        color="text.secondary"
        sx={{
          mb: 2,
          textTransform: "uppercase",
          letterSpacing: ".05em",
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        Workload utilisation
      </Typography>

      {/* ── Row 1: STAT-A1 mean + STAT-A2 variance + STAT-A3 gap ── */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1.5 }}>
        <StatCard
          label="Mean utilisation (A1)"
          value={`${mean_utilisation}%`}
          sub="avg contracted hours used"
          accent={
            mean_utilisation >= 90 ? "#3B6D11"
            : mean_utilisation >= 70 ? "#854F0B"
            : "#A32D2D"
          }
        />
        <StatCard
          label="Utilisation variance (A2)"
          value={variance}
          sub={variance < 0.05 ? "low — well balanced" : variance < 0.15 ? "moderate" : "high — unbalanced"}
          accent={
            variance < 0.05 ? "#3B6D11"
            : variance < 0.15 ? "#854F0B"
            : "#A32D2D"
          }
        />
        <StatCard
          label="Max-min gap (A3)"
          value={`${max_min_gap_hours}h`}
          sub="between most and least loaded"
        />
      </Box>

      {/* ── Row 2: STAT-A4 Gini bar ── */}
      <Paper
        elevation={0}
        sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1, mb: 1.5 }}
      >
        <GiniBar value={fairness_index} />
      </Paper>

      {/* ── Row 3: STAT-A5 idle + STAT-A6 overloaded + STAT-A7 assignments ── */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1.5 }}>
        <StatCard
          label={`Idle employees (A5)`}
          value={idle_employees}
          sub={`below ${idle_threshold_pct}% utilisation`}
          accent={idle_employees > 0 ? "#854F0B" : undefined}
        />
        <StatCard
          label="Overloaded employees (A6)"
          value={overloaded_employees}
          sub="exceed contracted hours"
          accent={overloaded_employees > 0 ? "#A32D2D" : undefined}
        />
        <StatCard
          label="Assignments used (A7)"
          value={`${assignments_used} / ${assignments_possible}`}
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