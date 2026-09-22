import React, { useState } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Box,
  Paper,
  Chip,
  Grid,
  Tooltip,
  Stack,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Collapse,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

// ─── Design tokens ────────────────────────────────────────────────────────────
// Semantic colours only — no accent overrides here (MUI theme handles primary).
const T = {
  pass:    { bg: "#ECFDF5", text: "#065F46", border: "#059669" },
  fail:    { bg: "#FEF2F2", text: "#7F1D1D", border: "#DC2626" },
  warn:    { bg: "#FFFBEB", text: "#78350F", border: "#D97706" },
  neutral: { bg: "#F8FAFC", text: "#475569", border: "#CBD5E1" },
};

const SKILL_COLORS = {
  Management: { bg: "#EFF6FF", text: "#1E40AF", bar: "#2563EB" },
  Checkout:   { bg: "#F0FDF4", text: "#14532D", bar: "#16A34A" },
  Storage:    { bg: "#FFF7ED", text: "#7C2D12", bar: "#EA580C" },
  Employees:  { bg: "#F8FAFC", text: "#334155", bar: "#64748B" },
};
function skillColor(skill) {
  return SKILL_COLORS[skill] ?? { bg: "#F5F3FF", text: "#3730A3", bar: "#6366F1" };
}

// ─── Shared primitives ────────────────────────────────────────────────────────

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

function InfoTip({ title }) {
  if (!title) return null;
  return (
    <Tooltip title={title} arrow placement="top">
      <HelpOutlineIcon sx={{ fontSize: 13, color: "text.disabled", flexShrink: 0 }} />
    </Tooltip>
  );
}

// Unified status row — used by both hard constraints and soft checks
function StatusRow({ label, value, tone = "neutral", tip }) {
  const pal = T[tone] ?? T.neutral;
  return (
    <Paper
      elevation={0}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        px: 1.5,
        py: 0.875,
        border: "1px solid",
        borderColor: pal.border,
        borderLeft: `3px solid ${pal.border}`,
        borderRadius: "0 6px 6px 0",
        bgcolor: pal.bg,
      }}
    >
      <Box
        sx={{
          width: 18,
          height: 18,
          borderRadius: "4px",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          fontWeight: 700,
          bgcolor: pal.border,
          color: "#fff",
        }}
      >
        {tone === "pass" ? "✓" : tone === "fail" ? "✗" : tone === "warn" ? "!" : "—"}
      </Box>
      <Typography variant="body2" sx={{ flex: 1, color: pal.text }}>
        {label}
      </Typography>
      <InfoTip title={tip} />
      {value !== undefined && value !== null && (
        <Typography
          variant="body2"
          fontWeight={700}
          sx={{ color: pal.text, fontVariantNumeric: "tabular-nums" }}
        >
          {value}
        </Typography>
      )}
    </Paper>
  );
}

// Compact metric tile
function Tile({ label, value, sub, tone, tip }) {
  const pal = tone ? T[tone] : null;
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: 1.5,
        bgcolor: pal ? pal.bg : "action.hover",
        border: pal ? `1px solid ${pal.border}` : "1px solid transparent",
        height: "100%",
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
        sx={{
          lineHeight: 1.2,
          color: pal ? pal.text : "text.primary",
          fontVariantNumeric: "tabular-nums",
        }}
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

// Coverage bar tile (for percentages with a progress bar)
function CoverageTile({ label, value, pct, tip }) {
  const isGood = pct >= 98;
  const isMid  = pct >= 80;
  const barColor = isGood ? T.pass.border : isMid ? T.warn.border : T.fail.border;
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: "action.hover", height: "100%" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.25 }}>
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>{label}</Typography>
        <InfoTip title={tip} />
      </Box>
      <Typography
        variant="h5"
        fontWeight={600}
        sx={{ lineHeight: 1.2, color: isGood ? T.pass.text : isMid ? T.warn.text : T.fail.text, fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </Typography>
      <Box sx={{ mt: 0.75, height: 3, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
        <Box sx={{ height: "100%", width: `${Math.min(pct, 100)}%`, bgcolor: barColor, borderRadius: 2 }} />
      </Box>
    </Paper>
  );
}

// ─── Team coverage cards (Sisqual-bundle specific) ────────────────────────────
function TeamCoverageCard({ team }) {
  const cov   = Number(team.weightedMinimumCoverageRate || 0);
  const gap   = Number(team.gap || 0);
  const over  = Number(team.overstaff || 0);
  const tone  = cov >= 98 ? "pass" : cov >= 80 ? "warn" : "fail";
  const pal   = T[tone];
  const items = [
    { label: "Required", v: team.required },
    { label: "Filled",   v: team.filled   },
    { label: "Gap",      v: gap,  t: gap  > 0 ? "fail"  : "pass" },
    { label: "Overstaff",v: over, t: over > 0 ? "warn"  : null   },
  ];
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: "100%" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight={700}>{team.team}</Typography>
        <Chip
          label={`${cov.toFixed(1)}%`}
          size="small"
          sx={{ height: 20, fontSize: 11, fontWeight: 700, bgcolor: pal.bg, color: pal.text }}
        />
      </Box>
      <Box sx={{ height: 6, borderRadius: 99, bgcolor: "action.selected", overflow: "hidden", mb: 1.5 }}>
        <Box sx={{ height: "100%", width: `${Math.min(cov, 100)}%`, bgcolor: pal.border, borderRadius: 99 }} />
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.75 }}>
        {items.map(({ label, v, t }) => (
          <Box key={label} sx={{ px: 1, py: 0.75, borderRadius: 1, bgcolor: t ? T[t].bg : "action.hover" }}>
            <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
            <Typography variant="body2" fontWeight={700} sx={{ color: t ? T[t].text : "text.primary", fontVariantNumeric: "tabular-nums" }}>{v}</Typography>
          </Box>
        ))}
      </Box>
    </Paper>
  );
}

// ─── Max shortage expandable card ────────────────────────────────────────────
function MaxShortageCard({ data, fallbackValue }) {
  const [openGap, setOpenGap] = useState(null);
  if (!data && fallbackValue == null) return null;
  const maxGap = Number(data?.max_gap ?? fallbackValue ?? 0);
  const gapEntries = Object.entries(data?.gap_distribution || {})
    .map(([g, c]) => ({ gap: Number(g), count: Number(c) }))
    .filter(e => e.gap > 0 && e.count > 0)
    .sort((a, b) => b.gap - a.gap);
  const maxCount = Math.max(...gapEntries.map(e => e.count), 1);
  const gapColor = g => g >= 3 ? T.fail.border : g === 2 ? T.warn.border : "#EA580C";
  const isOk = maxGap === 0;

  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: "action.hover" }}>
      <Typography variant="caption" color="text.secondary" display="block">Max shortage (single slot)</Typography>
      <Typography variant="h5" fontWeight={600}
        sx={{ lineHeight: 1.2, mt: 0.25, mb: isOk ? 0 : 1, color: isOk ? T.pass.text : T.fail.text, fontVariantNumeric: "tabular-nums" }}>
        {maxGap}
        {!isOk && <Typography component="span" variant="caption" color="text.disabled" sx={{ ml: 0.5 }}>worker-slots</Typography>}
      </Typography>
      {gapEntries.map(({ gap, count }) => {
        const key = String(gap);
        const isOpen = openGap === key;
        const details = data?.details_by_gap?.[key] || [];
        const color = gapColor(gap);
        const byDate = details.reduce((acc, d) => { (acc[d.date] ??= []).push(d); return acc; }, {});
        return (
          <Box key={key}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, cursor: details.length > 0 ? "pointer" : "default", py: 0.25 }}
              onClick={() => details.length > 0 && setOpenGap(isOpen ? null : key)}>
              <Box sx={{ minWidth: 22, height: 18, borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: color }}>
                <Typography sx={{ fontSize: 10, fontWeight: 700, color: "#fff" }}>-{gap}</Typography>
              </Box>
              <Box sx={{ flex: 1, height: 5, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
                <Box sx={{ height: "100%", width: `${Math.round((count / maxCount) * 100)}%`, bgcolor: color, borderRadius: 2 }} />
              </Box>
              <Typography variant="caption" fontWeight={700} sx={{ color, minWidth: 28, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{count}</Typography>
              {details.length > 0 && <Typography variant="caption" color="text.disabled" sx={{ fontSize: 10 }}>{isOpen ? "▲" : "▼"}</Typography>}
            </Box>
            <Collapse in={isOpen}>
              <Box sx={{ ml: 4, mb: 0.5, display: "flex", flexDirection: "column", gap: 0.5 }}>
                {Object.entries(byDate).map(([date, slots]) => (
                  <Box key={date}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ display: "block", mb: 0.25 }}>{date}</Typography>
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.4, pl: 1 }}>
                      {slots.map((s, i) => (
                        <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 0.5, px: 0.75, py: 0.2, borderRadius: 1, bgcolor: T.fail.bg }}>
                          <Typography variant="caption" sx={{ color: T.fail.text, fontWeight: 600 }}>{s.team}</Typography>
                          <Typography variant="caption" sx={{ color: T.fail.text }}>{s.period}</Typography>
                          <Typography variant="caption" sx={{ color: T.fail.text, opacity: 0.8 }}>{s.covered}/{s.required}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ))}
                {details.length === 20 && <Typography variant="caption" color="text.disabled" sx={{ pl: 1 }}>Showing first 20 occurrences</Typography>}
              </Box>
            </Collapse>
          </Box>
        );
      })}
    </Paper>
  );
}

// ─── Employee assignment quality ──────────────────────────────────────────────
function getEmployeeTeamBreakdown(emp) {
  if (Array.isArray(emp?.teamWorkBreakdown) && emp.teamWorkBreakdown.length > 0) {
    return emp.teamWorkBreakdown
      .map(item => ({ team: item.team || item.skill || "Unknown", hours: Number(Number(item.hours || 0).toFixed(2)), percentage: Number(Number(item.percentage || item.pct || 0).toFixed(2)) }))
      .filter(item => item.hours > 0 || item.percentage > 0);
  }
  const src = emp?.teamWorkPercentages || emp?.skill_usage_pct;
  if (src && typeof src === "object") {
    const wh = Number(emp?.workedHours || 0);
    return Object.entries(src)
      .map(([team, rawPct]) => { const p = Number(rawPct || 0); return { team, hours: Number(((wh * p) / 100).toFixed(2)), percentage: Number(p.toFixed(2)) }; })
      .filter(item => item.hours > 0 || item.percentage > 0)
      .sort((a, b) => b.percentage - a.percentage);
  }
  const wh = Number(emp?.workedHours || 0);
  const nph = Number(emp?.nonPrimaryTeamHours || 0);
  const ph = Math.max(wh - nph, 0);
  const rows = [];
  if (ph > 0) rows.push({ team: emp?.primaryTeam || "Primary", hours: Number(ph.toFixed(2)), percentage: wh ? Number(((ph / wh) * 100).toFixed(2)) : 0 });
  if (nph > 0) rows.push({ team: "Other", hours: Number(nph.toFixed(2)), percentage: wh ? Number(((nph / wh) * 100).toFixed(2)) : 0 });
  return rows;
}

function SkillBar({ breakdown }) {
  if (!breakdown.length) return null;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", mb: 0.5, bgcolor: "action.selected" }}>
        {breakdown.map(item => (
          <Box key={item.team} sx={{ width: `${Math.min(Number(item.percentage || 0), 100)}%`, bgcolor: skillColor(item.team).bar }}
            title={`${item.team}: ${Number(item.percentage || 0).toFixed(1)}%`} />
        ))}
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {breakdown.map(item => {
          const c = skillColor(item.team);
          return (
            <Box key={item.team} sx={{ display: "flex", gap: 0.4, alignItems: "center", px: 0.75, py: 0.2, borderRadius: 1, bgcolor: c.bg }}>
              <Typography variant="caption" fontWeight={600} sx={{ color: c.text, fontSize: 10 }}>{item.team}</Typography>
              <Typography variant="caption" sx={{ color: c.text, fontSize: 10 }}>{Number(item.percentage || 0).toFixed(1)}%</Typography>
              <Typography variant="caption" sx={{ color: c.text, opacity: 0.65, fontSize: 10 }}>{Number(item.hours || 0).toFixed(1)}h</Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

function EmployeeDetailPanel({ emp }) {
  const breakdown = getEmployeeTeamBreakdown(emp);
  const cols = [
    { label: "Worked hours",      value: emp.workedHours ?? 0,            tip: "Total hours assigned in the generated schedule." },
    { label: "Primary util.",     value: `${Number(emp.primaryTeamUtilizationRate || 0).toFixed(1)}%`, tip: "% of hours in employee's strongest-ranked skill." },
    { label: "Non-primary h",     value: emp.nonPrimaryTeamHours ?? 0,    tip: "Hours outside primary skill." },
    { label: "Team switches",     value: emp.teamSwitches ?? 0,           tip: "Within-day skill changes." },
    { label: "Fragmented days",   value: emp.fragmentedWorkDays ?? 0,     tip: "Days with more than one work segment." },
    { label: "Duration cpl.",     value: `${Number(emp.durationComplianceRate || 0).toFixed(1)}%`, tip: "Days matching the allowed duration or EQUALS rule." },
    { label: "Demanded h cpl.",   value: `${Number(emp.demandedHoursComplianceRate || 0).toFixed(1)}%`, tip: "Working-rule days where assigned hours match requested." },
    { label: "Pref. DO worked",   value: emp.preferredDayOffWorkedDays ?? 0, tip: "Template DO days the employee still worked.", tone: Number(emp.preferredDayOffWorkedDays || 0) > 0 ? "fail" : "pass" },
    { label: "Skill penalty",     value: emp.skillPriorityPenaltyScore ?? 0, tip: "Lower-priority skill assignment penalty. Lower is better." },
    { label: "Availability",      value: emp.availabilityViolations ?? 0, tip: "Hard availability violations.", tone: Number(emp.availabilityViolations || 0) > 0 ? "fail" : "pass" },
    { label: "Consecutive",       value: emp.consecutiveDaysViolations ?? 0, tip: "Times max consecutive-days limit exceeded.", tone: Number(emp.consecutiveDaysViolations || 0) > 0 ? "fail" : "pass" },
    { label: "Min rest",          value: emp.minRestViolations ?? 0,      tip: "Insufficient rest between shifts.", tone: Number(emp.minRestViolations || 0) > 0 ? "fail" : "pass" },
  ];
  return (
    <Paper elevation={0} sx={{ p: 2, border: "1px solid", borderColor: "divider", borderRadius: 2, bgcolor: "action.hover" }}>
      <Typography variant="subtitle2" fontWeight={700} gutterBottom>
        {emp.name || emp.employeeId}
        <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>{emp.employeeId}</Typography>
      </Typography>
      <SkillBar breakdown={breakdown} />
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1 }}>
        {cols.map(c => <Tile key={c.label} label={c.label} value={c.value} tip={c.tip} tone={c.tone} />)}
      </Box>
    </Paper>
  );
}

function EmployeeAssignmentTable({ employeeRows }) {
  const [selected, setSelected] = useState("");
  const emp = employeeRows.find(e => e.employeeId === selected) || null;
  return (
    <Box mt={3}>
      <Divider sx={{ mb: 2 }} />
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5, flexWrap: "wrap", gap: 1 }}>
        <SectionLabel>Employee assignment quality</SectionLabel>
        <Chip label={`${employeeRows.length} employees`} size="small"
          sx={{ height: 20, fontSize: 11, bgcolor: "action.selected", color: "text.secondary" }} />
      </Box>
      <FormControl size="small" sx={{ minWidth: 260, mb: 2 }}>
        <InputLabel sx={{ fontSize: 13 }}>Select employee</InputLabel>
        <Select value={selected} label="Select employee" onChange={e => setSelected(e.target.value)} sx={{ fontSize: 13 }}>
          <MenuItem value=""><em>Select an employee</em></MenuItem>
          {employeeRows.map(e => (
            <MenuItem key={e.employeeId || e.name} value={e.employeeId} sx={{ fontSize: 13 }}>
              {e.name || e.employeeId}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {emp && <EmployeeDetailPanel emp={emp} />}
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight: 480, mt: 2 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {["Employee","Worked h","Primary %","Non-primary h","Switches","Fragments","Duration %","Demanded %","Pref. DO","Skill pen.","Avail.","Consec.","Min rest"].map(h => (
                <TableCell key={h} align={h === "Employee" ? "left" : "right"}
                  sx={{ fontSize: 11, whiteSpace: "nowrap", fontWeight: 600, bgcolor: "background.paper" }}>
                  {h}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {employeeRows.map(e => {
              const avFail = Number(e.availabilityViolations || 0) > 0;
              const coFail = Number(e.consecutiveDaysViolations || 0) > 0;
              const mrFail = Number(e.minRestViolations || 0) > 0;
              const doFail = Number(e.preferredDayOffWorkedDays || 0) > 0;
              return (
                <TableRow key={e.employeeId || e.name} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>{e.name || e.employeeId}</Typography>
                    <Typography variant="caption" color="text.secondary">{e.employeeId}</Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{e.workedHours ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{Number(e.primaryTeamUtilizationRate || 0).toFixed(1)}%</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{e.nonPrimaryTeamHours ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{e.teamSwitches ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{e.fragmentedWorkDays ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{Number(e.durationComplianceRate || 0).toFixed(1)}%</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{Number(e.demandedHoursComplianceRate || 0).toFixed(1)}%</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: doFail ? T.fail.text : T.pass.text }}>{e.preferredDayOffWorkedDays ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{e.skillPriorityPenaltyScore ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: avFail ? T.fail.text : T.pass.text }}>{e.availabilityViolations ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: coFail ? T.fail.text : T.pass.text }}>{e.consecutiveDaysViolations ?? 0}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: mrFail ? T.fail.text : T.pass.text }}>{e.minRestViolations ?? 0}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

// ─── Workload utilisation (per-employee bars) ─────────────────────────────────
function WorkloadRows({ employeeRows }) {
  if (!employeeRows.length) return null;
  const sorted = [...employeeRows].sort((a, b) => Number(b.workedHours || 0) - Number(a.workedHours || 0));
  const maxHours = Number(sorted[0]?.workedHours || 1);
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      {sorted.map(emp => {
        const breakdown = getEmployeeTeamBreakdown(emp);
        const hours = Number(emp.workedHours || 0);
        const pct = Math.round((hours / maxHours) * 100);
        return (
          <Box key={emp.employeeId || emp.name}
            sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 1.5, py: 0.75, border: "1px solid", borderColor: "divider", borderRadius: 1, bgcolor: "background.paper" }}>
            <Box sx={{ flex: "0 0 180px", minWidth: 0 }}>
              <Typography variant="caption" fontWeight={600} sx={{ display: "block", lineHeight: 1.25, overflowWrap: "anywhere" }}>
                {emp.name || emp.employeeId}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>{emp.employeeId}</Typography>
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ height: 6, borderRadius: 3, bgcolor: "action.selected", overflow: "hidden", mb: 0.5 }}>
                {breakdown.length > 0 ? breakdown.map(item => (
                  <Box key={item.team} component="span" sx={{ display: "inline-block", height: "100%",
                    width: `${Math.max(0, Math.min(Number(item.percentage || 0), 100))}%`,
                    bgcolor: skillColor(item.team).bar }}
                    title={`${item.team}: ${Number(item.percentage || 0).toFixed(1)}% (${Number(item.hours || 0).toFixed(1)}h)`} />
                )) : <Box sx={{ height: "100%", width: `${pct}%`, bgcolor: "text.disabled" }} />}
              </Box>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.4 }}>
                {breakdown.map(item => {
                  const c = skillColor(item.team);
                  return (
                    <Box key={item.team} sx={{ display: "flex", gap: 0.3, px: 0.6, py: 0.15, borderRadius: 1, bgcolor: c.bg }}>
                      <Typography variant="caption" fontWeight={600} sx={{ color: c.text, fontSize: 10 }}>{item.team}</Typography>
                      <Typography variant="caption" sx={{ color: c.text, fontSize: 10 }}>{Number(item.percentage || 0).toFixed(0)}%</Typography>
                    </Box>
                  );
                })}
              </Box>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 52, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
              {hours}h
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

function SkillChangesRows({ employeeRows }) {
  if (!employeeRows.length) return null;
  const rows = employeeRows.map(emp => {
    const breakdown = getEmployeeTeamBreakdown(emp);
    const activeDays = Number(emp.activeWorkDays || emp.totalActiveDays || 0);
    const meanChanges = emp.meanSkillChangesPerDay !== undefined
      ? Number(emp.meanSkillChangesPerDay || 0)
      : activeDays ? Number((Number(emp.teamSwitches || 0) / activeDays).toFixed(2)) : 0;
    return { emp, breakdown, activeDays, meanChanges };
  }).sort((a, b) => b.meanChanges - a.meanChanges);
  const maxChanges = Math.max(...rows.map(r => r.meanChanges), 0.01);
  const switchColor = v => v < 1 ? T.pass.border : v < 2 ? T.warn.border : T.fail.border;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      {rows.map(({ emp, breakdown, activeDays, meanChanges }) => {
        const pct = Math.round((meanChanges / maxChanges) * 100);
        const color = switchColor(meanChanges);
        return (
          <Box key={emp.employeeId || emp.name}
            sx={{ display: "flex", alignItems: "center", gap: 1, px: 1.5, py: 0.75, border: "1px solid", borderColor: "divider", borderRadius: 1, bgcolor: "background.paper" }}>
            <Typography variant="caption" fontWeight={600} sx={{ minWidth: 80 }}>{emp.employeeId || emp.name}</Typography>
            <Box sx={{ display: "flex", gap: 0.4, flexWrap: "wrap", minWidth: 100 }}>
              {breakdown.map(item => {
                const c = skillColor(item.team);
                return <Box key={item.team} sx={{ px: 0.6, py: 0.1, borderRadius: "3px", bgcolor: c.bg }}>
                  <Typography sx={{ fontSize: 9, fontWeight: 600, color: c.text }}>{item.team}</Typography>
                </Box>;
              })}
            </Box>
            <Box sx={{ flex: 1, height: 4, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
              <Box sx={{ height: "100%", width: `${pct}%`, bgcolor: color, borderRadius: 2 }} />
            </Box>
            <Typography variant="caption" fontWeight={700} sx={{ color, minWidth: 34, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{meanChanges}</Typography>
            <Typography variant="caption" color="text.disabled" sx={{ minWidth: 40, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{activeDays}d</Typography>
          </Box>
        );
      })}
    </Box>
  );
}

// ─── Skill allocation totals ──────────────────────────────────────────────────
function SkillAllocationSummary({ employeeRows }) {
  let totalHours = 0, totalNonPrimary = 0, totalSwitches = 0, totalFragments = 0;
  for (const e of employeeRows) {
    totalHours      += Number(e.workedHours || 0);
    totalNonPrimary += Number(e.nonPrimaryTeamHours || 0);
    totalSwitches   += Number(e.teamSwitches || 0);
    totalFragments  += Number(e.fragmentedWorkDays || 0);
  }
  const primaryRate = totalHours ? Number((((totalHours - totalNonPrimary) / totalHours) * 100).toFixed(1)) : 100;
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1 }}>
      <Tile label="Primary-skill rate"  value={`${primaryRate}%`} tip="% of all scheduled hours on each employee's top-ranked skill." />
      <Tile label="Non-primary hours"   value={Number(totalNonPrimary.toFixed(1))} tip="Total hours outside employees' primary skills." />
      <Tile label="Total team switches" value={totalSwitches} tip="Total within-day skill changes across all employees." />
      <Tile label="Fragmented days"     value={totalFragments} tip="Total employee-days with more than one work segment." />
    </Box>
  );
}

// ─── Hard-constraint row definitions ─────────────────────────────────────────
const HARD_CONSTRAINTS = [
  { key: "duplicatedAssignmentsPerDay",  label: "At most one assignment per employee per day",    tip: "Count of employee-days with overlapping time segments." },
  { key: "uncoveredSlotsWithoutSkill",   label: "Every covered slot has a skill assigned",         tip: "Worked employee-days where the schedule cell has no skill/team label." },
  { key: "consecutiveDaysViolations",    label: "No more than 5 consecutive working days",         tip: "Times an employee exceeded the maximum run of five consecutive working days." },
  { key: "minRestViolations",            label: "Min 11 h rest between consecutive shifts",        tip: "Shift-to-shift transitions with insufficient rest time. Should be 0." },
  { key: "availabilityViolations",       label: "Employees do not work on unavailable days",       tip: "Employee-days where the schedule violates stated availability constraints." },
];

// ─── Underfilled periods table ────────────────────────────────────────────────
function UnderfilledTable({ rows }) {
  if (!rows.length) return null;
  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <SectionLabel>Most critical underfilled periods</SectionLabel>
        <Chip label={`${rows.length} shown`} size="small" sx={{ height: 20, fontSize: 11, bgcolor: "action.selected", color: "text.secondary" }} />
      </Box>
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {["Date","Team","Period","Required","Actual","Shortage"].map(h => (
                <TableCell key={h} align={h === "Date" || h === "Team" || h === "Period" ? "left" : "right"}
                  sx={{ fontSize: 11, fontWeight: 600, bgcolor: "background.paper" }}>{h}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={`${row.date}-${row.team}-${i}`} hover>
                <TableCell>{row.date}</TableCell>
                <TableCell>{row.team}</TableCell>
                <TableCell>{row.label || `${row.start}–${row.end}`}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.required}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{row.actual}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: T.fail.text, fontWeight: 700 }}>{row.shortage}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

// ─── Sisqual-bundle KPI renderer (new solver format) ─────────────────────────
function renderSisqualBundleReport(metrics) {
  const hasIssues = HARD_CONSTRAINTS.some(c => Number(metrics[c.key] || 0) > 0);
  const teamCoverage    = Array.isArray(metrics.teamCoverageBreakdown) ? metrics.teamCoverageBreakdown : [];
  const underfilledRows = Array.isArray(metrics.underfilledPeriods) ? metrics.underfilledPeriods.slice(0, 12) : [];
  const employeeRows    = Array.isArray(metrics.employeeAssignmentQuality) ? metrics.employeeAssignmentQuality : [];
  const coveragePct     = Number(metrics.weightedMinimumCoverageRate || 0);

  return (
    <Box sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={2} sx={{ borderRadius: 2 }} defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>
            Schedule KPIs
          </Typography>
          <Chip
            label={hasIssues ? "Issues found" : "All clear"}
            size="small"
            sx={{ height: 22, fontSize: 11, fontWeight: 600,
              bgcolor: hasIssues ? T.fail.bg : T.pass.bg,
              color: hasIssues ? T.fail.text : T.pass.text }}
          />
        </AccordionSummary>
        <AccordionDetails sx={{ px: 2.5, pb: 3 }}>

          {/* Hard constraints */}
          <SectionLabel>Hard constraints</SectionLabel>
          <Stack spacing={0.75} mb={3}>
            {HARD_CONSTRAINTS.map(c => {
              const v = Number(metrics[c.key] || 0);
              return <StatusRow key={c.key} label={c.label} value={v} tone={v > 0 ? "fail" : "pass"} tip={c.tip} />;
            })}
          </Stack>

          {/* Coverage summary */}
          <Divider sx={{ mb: 2 }} />
          <SectionLabel>Coverage</SectionLabel>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1 }}>
            <CoverageTile
              label="Weighted minimum coverage"
              value={`${coveragePct.toFixed(1)}%`}
              pct={coveragePct}
              tip="Fulfilled required headcount / total required headcount across all 30-min team slots."
            />
            <Tile
              label="Critical underfilled slots"
              value={metrics.criticalUnderfilledPeriods ?? 0}
              tone={Number(metrics.criticalUnderfilledPeriods || 0) > 0 ? "fail" : "pass"}
              tip="30-min date/team/slot cells where coverage is below the required minimum."
            />
            <Tile
              label="Total minimum gap"
              value={metrics.totalMinimumGap ?? 0}
              tone={Number(metrics.totalMinimumGap || 0) > 0 ? "fail" : "pass"}
              tip="Total missing headcount across all required 30-min team slots."
            />
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 3 }}>
            <MaxShortageCard data={metrics.maxShortageSingleSlot} fallbackValue={metrics.maxPeriodShortage} />
            <Tile
              label="Total overstaff"
              value={metrics.totalOverstaff ?? 0}
              tone={Number(metrics.totalOverstaff || 0) > 0 ? "warn" : "pass"}
              tip="Total surplus headcount above minimum requirements across all required slots."
            />
          </Box>

          {/* Assignment quality */}
          <Divider sx={{ mb: 2 }} />
          <SectionLabel>Assignment quality</SectionLabel>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1 }}>
            <Tile label="Intra-day team switches"      value={metrics.intraDayTeamSwitches ?? 0} tip="Times employees switch skill between consecutive segments on the same day." />
            <Tile label="Fragmented work days"         value={metrics.fragmentedWorkDays ?? 0}   tip="Employee-days with more than one assigned segment." />
            <CoverageTile label="Primary skill utilisation"  value={`${Number(metrics.primaryTeamUtilizationRate || 0).toFixed(1)}%`} pct={Number(metrics.primaryTeamUtilizationRate || 0)} tip="Share of assigned hours on each employee's strongest-ranked skill." />
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1 }}>
            <Tile label="Non-primary skill hours"      value={metrics.nonPrimaryTeamHours ?? 0}  tip="Total hours worked outside employees' primary skills." />
            <CoverageTile label="Duration compliance"  value={`${Number(metrics.durationComplianceRate || 0).toFixed(1)}%`} pct={Number(metrics.durationComplianceRate || 0)} tip="Employee-days that respect the daily duration or EQUALS rule." />
            <CoverageTile label="Preferred day-off preservation" value={`${Number(metrics.preferredDayOffPreservationRate || 0).toFixed(1)}%`} pct={Number(metrics.preferredDayOffPreservationRate || 0)} tip="Template DO days that remained fully off in the generated schedule." />
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 3 }}>
            <Tile label="Skill priority penalty"       value={metrics.skillPriorityPenaltyScore ?? 0} tip="Weighted slot-level penalty for lower-priority skill assignments. Lower is better." />
          </Box>

          {/* Skill allocation totals */}
          {employeeRows.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <SectionLabel>Skill allocation</SectionLabel>
              <Box mb={3}><SkillAllocationSummary employeeRows={employeeRows} /></Box>
            </>
          )}

          {/* Team coverage breakdown */}
          {teamCoverage.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <SectionLabel>Team coverage breakdown</SectionLabel>
              <Grid container spacing={2} mb={3}>
                {teamCoverage.map(team => (
                  <Grid item xs={12} md={6} lg={3} key={team.team}>
                    <TeamCoverageCard team={team} />
                  </Grid>
                ))}
              </Grid>
            </>
          )}

          {/* Underfilled periods */}
          {underfilledRows.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <UnderfilledTable rows={underfilledRows} />
            </>
          )}

          {/* Per-employee detail */}
          {employeeRows.length > 0 && (
            <>
              <EmployeeAssignmentTable employeeRows={employeeRows} />
              <Divider sx={{ my: 2 }} />
              <SectionLabel>Workload utilisation</SectionLabel>
              <Paper elevation={0} sx={{ p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1.5, mb: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={500} display="block" mb={1}>
                  Per-employee time by skill
                </Typography>
                <WorkloadRows employeeRows={employeeRows} />
              </Paper>
              <Divider sx={{ mb: 2 }} />
              <SectionLabel>Skill changes per day</SectionLabel>
              <Paper elevation={0} sx={{ p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1.5 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={500} display="block" mb={1}>
                  Mean skill changes per working day — per employee
                </Typography>
                <SkillChangesRows employeeRows={employeeRows} />
              </Paper>
            </>
          )}

        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

// ─── Legacy shift / hourly KPI renderer ──────────────────────────────────────
const metricInfo = {
  tmFails:                    { label: "Afternoon-Morning Sequences",    description: "Times an employee works an afternoon shift followed by a morning shift the next day." },
  consecutiveDays:            { label: "Consecutive Work-Day Violations",description: "Times employees exceeded the maximum allowed run of five consecutive working days." },
  workHolidays:               { label: "Holidays & Sunday Work Days",    description: "Work days on holidays and Sundays exceeding the predefined threshold." },
  missedVacationDays:         { label: "Missed Vacation Days",           description: "Total variance between actual and target vacation days across all employees." },
  missedWorkDays:             { label: "Missed Working Days",            description: "Total variance between actual and target working days across all employees." },
  missedTeamMin:              { label: "Missed Minimums",                description: "Per team/shift/day, count of employees below the required minimum staffing level." },
  missedTeamIdeal:            { label: "Missed Ideals",                  description: "Per team/shift/day, count of employees below the ideal staffing level." },
  singleTeamViolations:       { label: "Single-Team Violations",         description: "Employees allowed only one team but worked in more than one." },
  shiftBalance:               { label: "Shift Balance",                  description: "% deviation of the most unbalanced shift distribution for any employee." },
  teamSatisfactionLevel:      { label: "Team Satisfaction Level",        description: "Median distribution of work between primary and secondary team." },
  fixedDaysOffViolations:     { label: "Fixed Days-Off Violations",      description: "Employee week/month periods where OFF days don't match the configured target." },
  workDaysTargetDeviation:    { label: "Work Days Target Deviation",     description: "Total absolute deviation from the target of 223 workdays per year across all employees." },
  vacationDaysQuotaDeviation: { label: "Vacation Quota Deviation",       description: "Total absolute deviation from the mandatory vacation days per year across all employees." },
  holidayWorkLimitViolations: { label: "Holiday Work Limit Violations",  description: "Holiday/Sunday workdays beyond the legal limit of 22, summed across employees." },
  consecutiveDaysViolations:  { label: "Consecutive Days Violations",    description: "Times an employee worked 6 or more consecutive days without a rest day." },
  totalStaffingGap:           { label: "Total Staffing Gap",             description: "Total missing staff vs required minimums across all teams, time slots, and days." },
  staffingCoverageRate:       { label: "Staffing Coverage Rate",         description: "% of time slots where the minimum staffing requirement was met." },
  totalIdealGap:              { label: "Total Ideal Gap",                description: "Total missing staff vs ideal staffing levels across all teams, time slots, and days." },
  staffingRobustnessGap:      { label: "Staffing Robustness Gap",        description: "Total missing staff vs synthetic ideal levels (minimum + 1)." },
  excessStaffing:             { label: "Excess Staffing",                description: "Total extra staff beyond required minimums across all teams, time slots, and days." },
  minRestViolations:          { label: "Minimum Rest Violations",        description: "Shift-to-shift transitions with less than the configured minimum rest time." },
};

const shiftMetrics = ["tmFails","consecutiveDays","workHolidays","missedVacationDays","missedWorkDays","missedTeamMin","missedTeamIdeal","singleTeamViolations","shiftBalance","teamSatisfactionLevel","fixedDaysOffViolations"];
const legacyHourlyMetrics = ["workDaysTargetDeviation","vacationDaysQuotaDeviation","holidayWorkLimitViolations","consecutiveDaysViolations","minRestViolations","totalStaffingGap","staffingRobustnessGap","staffingCoverageRate","totalIdealGap","excessStaffing"];
const percentMetrics = new Set(["shiftBalance","teamSatisfactionLevel","staffingCoverageRate"]);
const optionalMetrics = new Set(["fixedDaysOffViolations"]);

function renderLegacyReport(metricKeys, metrics) {
  const hasIssues = metricKeys
    .filter(k => !percentMetrics.has(k))
    .some(k => Number(metrics[k] || 0) > 0);

  return (
    <Box sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={2} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>Schedule KPIs</Typography>
          <Chip
            label={hasIssues ? "Issues found" : "All clear"}
            size="small"
            sx={{ height: 22, fontSize: 11, fontWeight: 600,
              bgcolor: hasIssues ? T.fail.bg : T.pass.bg,
              color: hasIssues ? T.fail.text : T.pass.text }}
          />
        </AccordionSummary>
        <AccordionDetails sx={{ px: 2.5, pb: 3 }}>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1 }}>
            {metricKeys.map(key => {
              const info    = metricInfo[key] || { label: key, description: "" };
              const raw     = metrics[key];
              const numeric = Number(raw ?? 0);
              const isPercent = percentMetrics.has(key);
              const isBad  = !isPercent && Number.isFinite(numeric) && numeric > 0;
              const display = raw == null ? "N/A" : isPercent ? `${Number.isInteger(numeric) ? numeric : numeric.toFixed(1)}%` : (Number.isInteger(numeric) ? numeric : numeric.toFixed(2));
              return (
                <Tile
                  key={key}
                  label={info.label}
                  value={display}
                  tip={info.description}
                  tone={isPercent ? null : isBad ? "fail" : "pass"}
                />
              );
            })}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────
const KPIReport = ({ metrics = {}, scheduleType }) => {
  if (!metrics || !Object.keys(metrics).length) return null;

  const isSisqualBundle =
    metrics.weightedMinimumCoverageRate !== undefined ||
    Array.isArray(metrics.teamCoverageBreakdown);

  if (isSisqualBundle) return renderSisqualBundleReport(metrics);

  const normalizedType = String(scheduleType || "").toLowerCase();
  const isHourly =
    normalizedType === "horas" || normalizedType === "hours" ||
    metrics.totalStaffingGap !== undefined || metrics.excessStaffing !== undefined ||
    metrics.workDaysTargetDeviation !== undefined;

  const metricKeys = (isHourly ? legacyHourlyMetrics : shiftMetrics).filter(
    k => !optionalMetrics.has(k) || metrics[k] !== undefined
  );

  return renderLegacyReport(metricKeys, metrics);
};

export default KPIReport;
