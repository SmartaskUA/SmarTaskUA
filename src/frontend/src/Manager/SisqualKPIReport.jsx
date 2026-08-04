import React, { useState } from "react";
import {
  Box,
  Typography,
  Stack,
  Paper,
  Chip,
  Divider,
  Collapse,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import EmployeeKPIPanel from "./EmployeeKPIPanel";
import WorkloadUtilisationPanel from "./WorkloadUtilisationPanel";

// ─── Design tokens (shared with KPIReport.jsx) ───────────────────────────────
const T = {
  pass:    { bg: "#ECFDF5", text: "#065F46", border: "#059669" },
  fail:    { bg: "#FEF2F2", text: "#7F1D1D", border: "#DC2626" },
  warn:    { bg: "#FFFBEB", text: "#78350F", border: "#D97706" },
  neutral: { bg: "#F8FAFC", text: "#475569", border: "#CBD5E1" },
};

// ─── Alarm config ─────────────────────────────────────────────────────────────
const ALARM_CONFIG = [
  { key: "Duplicated_assignments_per_day",      label: "At most one assignment per employee per day" },
  { key: "Uncovered_slots_without_Skill",       label: "Every covered slot has a skill assigned" },
  { key: "Maximum_Consecutive_Days",            label: "No more than 5 consecutive working days" },
  { key: "Minimum_Rest_Time_Between_Shifts",    label: "Minimum 11 h rest between consecutive shifts" },
  { key: "Work_On_Unavailable_Days",            label: "Employees do not work on unavailable days" },
  { key: "Sunday_Rest_Per_Month",               label: "At least one Sunday off per month" },
  { key: "Weekly_Contracted_Hours",             label: "Weekly contracted hours respected" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function isPass(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value === 0;
  if (typeof value === "object" && "pass" in value) return value.pass;
  return null;
}

function getViolations(value) {
  if (typeof value === "object" && value !== null && "violations" in value) return value.violations;
  return null;
}

function getTotalShortageValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  if (typeof v === "object" && "value" in v) return v.value;
  return null;
}

function getMetricShortageValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  if (typeof v === "object" && "shortage" in v) return v.shortage;
  if (typeof v === "object" && "value" in v) return v.value;
  return null;
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

// Unified status row — matches the StatusRow in KPIReport.jsx
function StatusRow({ label, value, tone = "neutral", sub, chip, violations }) {
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
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body2" sx={{ color: pal.text }}>{label}</Typography>
        {sub && <Typography variant="caption" color="text.secondary">{sub}</Typography>}
      </Box>
      {violations !== null && violations !== undefined && violations > 0 && (
        <Typography variant="caption" sx={{ color: pal.text, fontWeight: 700 }}>{violations}×</Typography>
      )}
      {value !== null && value !== undefined && (
        <Typography variant="body2" fontWeight={700} sx={{ color: pal.text, fontVariantNumeric: "tabular-nums" }}>
          {value}
        </Typography>
      )}
      {chip !== undefined && (
        <Chip
          label={chip}
          size="small"
          sx={{ height: 20, fontSize: 11, fontWeight: 600, bgcolor: pal.border, color: "#fff" }}
        />
      )}
    </Paper>
  );
}

// Coverage progress tile
function CoverageTile({ label, shortage, covered, demanded, coverageRate }) {
  if (shortage === null || shortage === undefined) return null;
  const pct = coverageRate ?? (demanded > 0 ? Math.round((covered / demanded) * 100) : 100);
  const isOk = shortage === 0;
  const pal = isOk ? T.pass : T.fail;
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: "action.hover", height: "100%" }}>
      <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.75 }}>
        <Typography variant="h5" fontWeight={600} sx={{ color: pal.text, lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>
          {shortage}
        </Typography>
        <Typography variant="body2" fontWeight={600} sx={{ color: pal.text }}>{pct}%</Typography>
      </Box>
      <Box sx={{ height: 4, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
        <Box sx={{ height: "100%", width: `${pct}%`, bgcolor: pal.border, borderRadius: 2 }} />
      </Box>
      {covered !== null && covered !== undefined && demanded > 0 && (
        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: "block" }}>
          {covered}/{demanded} minimums covered
        </Typography>
      )}
    </Paper>
  );
}

function MetricTile({ label, value, sub, tone }) {
  const pal = tone ? T[tone] : null;
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: pal ? pal.bg : "action.hover", border: pal ? `1px solid ${pal.border}` : "1px solid transparent" }}>
      <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
      <Typography variant="h5" fontWeight={600} sx={{ lineHeight: 1.2, mt: 0.25, color: pal ? pal.text : "text.primary", fontVariantNumeric: "tabular-nums" }}>
        {value}
      </Typography>
      {sub && <Typography variant="caption" color="text.disabled" display="block" sx={{ mt: 0.25 }}>{sub}</Typography>}
    </Paper>
  );
}

// ─── Priority hierarchy row ───────────────────────────────────────────────────
function PriorityRow({ entry }) {
  const [open, setOpen] = useState(false);
  const { priority, label, pass, failing_slots, total_slots, failing_dates, levels_pending } = entry;
  const hasDetails = !levels_pending && failing_dates && failing_dates.length > 0;
  const tone = levels_pending ? "neutral" : pass ? "pass" : "fail";
  const pal = T[tone];

  return (
    <Box>
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
          borderRadius: open && hasDetails ? "0 6px 0 0" : "0 6px 6px 0",
          bgcolor: pal.bg,
          opacity: levels_pending ? 0.6 : 1,
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
          {levels_pending ? priority : pass ? "✓" : priority}
        </Box>
        <Typography variant="body2" sx={{ flex: 1, color: levels_pending ? "text.disabled" : pal.text }}>{label}</Typography>
        {!levels_pending && !pass && (
          <Typography variant="caption" sx={{ color: pal.text, fontVariantNumeric: "tabular-nums" }}>{failing_slots}/{total_slots} slots</Typography>
        )}
        {levels_pending ? (
          <Typography variant="caption" sx={{ color: "text.disabled", fontStyle: "italic", fontSize: 10 }}>pending</Typography>
        ) : (
          <Chip label={pass ? "Pass" : "Fail"} size="small"
            sx={{ height: 20, fontSize: 11, fontWeight: 600, bgcolor: pal.border, color: "#fff" }} />
        )}
        {hasDetails && (
          <IconButton size="small" onClick={() => setOpen(v => !v)} sx={{ ml: 0.5, p: 0.25 }}>
            {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        )}
      </Paper>
      {hasDetails && (
        <Collapse in={open}>
          <Paper elevation={0} sx={{ border: "1px solid", borderTop: "none", borderColor: T.fail.border, borderRadius: "0 0 6px 0", px: 1.5, py: 1, bgcolor: T.fail.bg }}>
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 0.75 }}>
              {failing_dates.map((fd, i) => (
                <Box key={i} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 1, py: 0.5, borderRadius: 1, bgcolor: "rgba(0,0,0,0.04)" }}>
                  <Typography variant="caption" sx={{ color: T.fail.text, fontWeight: 600 }}>{fd.date}</Typography>
                  <Typography variant="caption" sx={{ color: T.fail.text }}>{fd.period}</Typography>
                  <Typography variant="caption" sx={{ color: T.fail.text }}>{fd.covered}/{fd.required} covered</Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Collapse>
      )}
    </Box>
  );
}

// ─── Severity index card ──────────────────────────────────────────────────────
function SeverityTile({ kpis }) {
  const data = kpis["Severity_Index"];
  if (!data) return null;
  const { severity_index, total_shortage, by_priority } = data;
  const isOk = severity_index === 0;
  const pal = isOk ? T.pass : T.fail;
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: pal.bg, border: `1px solid ${pal.border}`, height: "100%" }}>
      <Typography variant="caption" color="text.secondary" display="block">Severity index</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.5 }}>
        <Typography variant="h5" fontWeight={600} sx={{ color: pal.text, lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>{severity_index}</Typography>
        <Typography variant="caption" color="text.disabled">weighted</Typography>
      </Box>
      <Typography variant="caption" color="text.disabled" display="block" sx={{ mb: 0.75 }}>
        {total_shortage} unweighted · higher priority = higher weight
      </Typography>
      {by_priority && by_priority.filter(p => p.shortage > 0).length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.4 }}>
          {by_priority.filter(p => p.shortage > 0).map(p => (
            <Box key={p.priority} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
              <Typography variant="caption" sx={{ minWidth: 18, fontSize: 10, fontWeight: 700, color: T.fail.text, bgcolor: T.fail.bg, borderRadius: "3px", px: 0.5, textAlign: "center" }}>
                {p.priority}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>{p.skill}</Typography>
              <Typography variant="caption" sx={{ color: T.fail.text, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>×{p.weight} = {p.weighted}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Paper>
  );
}

// ─── Slot failure tile ────────────────────────────────────────────────────────
function SlotFailureTile({ data }) {
  if (!data) return null;
  const { failing_slots, total_slots, failure_rate } = data;
  const isOk = failing_slots === 0;
  const pal = isOk ? T.pass : T.fail;
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: pal.bg, border: `1px solid ${pal.border}`, height: "100%" }}>
      <Typography variant="caption" color="text.secondary" display="block">Slots with failure</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.75 }}>
        <Typography variant="h5" fontWeight={600} sx={{ color: pal.text, lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>{failing_slots}</Typography>
        <Typography variant="body2" fontWeight={600} sx={{ color: pal.text }}>{failure_rate}%</Typography>
      </Box>
      <Box sx={{ height: 4, borderRadius: 2, bgcolor: "action.selected", overflow: "hidden" }}>
        <Box sx={{ height: "100%", width: `${failure_rate}%`, bgcolor: pal.border, borderRadius: 2 }} />
      </Box>
      <Typography variant="caption" color="text.disabled" display="block" sx={{ mt: 0.5 }}>of {total_slots} demanded slots</Typography>
    </Paper>
  );
}

// ─── Max shortage tile ────────────────────────────────────────────────────────
function MaxShortageTile({ data }) {
  const [openGap, setOpenGap] = useState(null);
  if (!data) return null;
  const { max_gap, gap_distribution, details_by_gap } = data;
  const isOk = max_gap === 0;
  const gapEntries = Object.entries(gap_distribution || {})
    .map(([g, count]) => ({ gap: parseInt(g), count }))
    .sort((a, b) => b.gap - a.gap);
  const maxCount = gapEntries.length > 0 ? Math.max(...gapEntries.map(e => e.count)) : 1;
  const gapColor = g => g >= 3 ? T.fail.border : g === 2 ? T.warn.border : "#EA580C";

  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: 1.5, bgcolor: "action.hover", height: "100%" }}>
      <Typography variant="caption" color="text.secondary" display="block">Max shortage (single slot)</Typography>
      <Typography variant="h5" fontWeight={600}
        sx={{ lineHeight: 1.2, mt: 0.25, mb: isOk ? 0 : 1, color: isOk ? T.pass.text : T.fail.text, fontVariantNumeric: "tabular-nums" }}>
        {max_gap}
        {!isOk && <Typography component="span" variant="caption" color="text.disabled" sx={{ ml: 0.5 }}>worker-slots</Typography>}
      </Typography>
      {gapEntries.map(({ gap, count }) => {
        const key = String(gap);
        const isOpen = openGap === key;
        const details = details_by_gap?.[key] ?? [];
        const color = gapColor(gap);
        const byDate = {};
        for (const d of details) { (byDate[d.date] ??= []).push(d); }
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
                    <Typography variant="caption" fontWeight={600} color="text.secondary" display="block" sx={{ mb: 0.25 }}>{date}</Typography>
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

// ─── Shortage by skill expandable rows ───────────────────────────────────────
function SkillShortageRow({ skill, shortage, details }) {
  const [open, setOpen] = useState(false);
  const isOk = shortage === 0;
  const pal = isOk ? T.pass : T.fail;
  const hasDetail = details && details.length > 0;
  const byDate = {};
  for (const d of details) { (byDate[d.date] ??= []).push(d); }

  return (
    <Box>
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
          borderRadius: open && hasDetail ? "0 6px 0 0" : "0 6px 6px 0",
          bgcolor: pal.bg,
        }}
      >
        <Typography variant="body2" fontWeight={600} sx={{ minWidth: 90, color: pal.text }}>{skill}</Typography>
        <Typography variant="h6" fontWeight={700} sx={{ color: pal.text, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{shortage}</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
          worker-slots short{hasDetail && ` · ${details.length} slot${details.length !== 1 ? "s" : ""} affected`}
        </Typography>
        {hasDetail && (
          <IconButton size="small" onClick={() => setOpen(v => !v)} sx={{ p: 0.25 }} aria-label={open ? "collapse" : "expand"}>
            {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        )}
      </Paper>
      {hasDetail && (
        <Collapse in={open}>
          <Paper elevation={0} sx={{ border: "1px solid", borderTop: "none", borderColor: pal.border, borderRadius: "0 0 6px 0", px: 1.5, py: 1, bgcolor: pal.bg }}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {Object.entries(byDate).map(([date, slots]) => (
                <Box key={date}>
                  <Typography variant="caption" fontWeight={600} color="text.secondary" display="block" sx={{ mb: 0.4 }}>{date}</Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, pl: 1 }}>
                    {slots.map((s, i) => (
                      <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 0.75, px: 1, py: 0.25, borderRadius: 1, bgcolor: "rgba(0,0,0,0.06)" }}>
                        <Typography variant="caption" sx={{ color: pal.text, fontWeight: 600 }}>{s.period}</Typography>
                        <Typography variant="caption" sx={{ color: pal.text }}>{s.covered}/{s.required}</Typography>
                        <Chip label={`-${s.gap}`} size="small" sx={{ height: 16, fontSize: 10, bgcolor: pal.border, color: "#fff" }} />
                      </Box>
                    ))}
                  </Box>
                </Box>
              ))}
            </Box>
          </Paper>
        </Collapse>
      )}
    </Box>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SisqualKPIReport({ kpis }) {
  if (!kpis) return null;
  if (!ALARM_CONFIG.some(a => a.key in kpis)) return null;

  const alarms = ALARM_CONFIG.map(({ key, label }) => ({
    key,
    label,
    pass:       isPass(kpis[key]),
    violations: getViolations(kpis[key]),
  }));

  const failCount   = alarms.filter(a => a.pass === false).length;
  const loadedCount = alarms.filter(a => a.pass !== null).length;
  const hasAlarms   = failCount > 0;

  const shortageRaw      = kpis["Total_Shortage"] ?? null;
  const shortageValue    = getTotalShortageValue(shortageRaw);
  const shortageBySkill  = typeof shortageRaw === "object" && shortageRaw?.shortage_by_skill
    ? shortageRaw.shortage_by_skill : null;
  const hierarchy        = kpis["Priority_Hierarchy"] ?? null;
  const priorities       = hierarchy?.priorities ?? [];
  const hierarchyPass    = hierarchy?.pass ?? null;

  const softChecks = [
    {
      key: "Total_Shortage",
      label: "Minimum coverage shortage minimized",
      value: shortageValue,
      pass: shortageValue === null ? null : shortageValue === 0,
      sub: kpis["Total_Shortage"]?.coverage_rate !== undefined
        ? `${kpis["Total_Shortage"].coverage_rate}% minimum coverage`
        : "Missing staff against minimum demand",
    },
    {
      key: "Staffing_Ideals",
      label: "Ideal staffing shortage minimized",
      value: getMetricShortageValue(kpis["Staffing_Ideals"]),
      pass: getMetricShortageValue(kpis["Staffing_Ideals"]) === null ? null : getMetricShortageValue(kpis["Staffing_Ideals"]) === 0,
      sub: kpis["Staffing_Ideals"]?.coverage_rate !== undefined ? `${kpis["Staffing_Ideals"].coverage_rate}% ideal coverage` : "Missing staff against ideal demand",
    },
    {
      key: "Staffing_Estimated",
      label: "Estimated staffing shortage minimized",
      value: getMetricShortageValue(kpis["Staffing_Estimated"]),
      pass: getMetricShortageValue(kpis["Staffing_Estimated"]) === null ? null : getMetricShortageValue(kpis["Staffing_Estimated"]) === 0,
      sub: kpis["Staffing_Estimated"]?.coverage_rate !== undefined ? `${kpis["Staffing_Estimated"].coverage_rate}% estimated coverage` : "Missing staff against estimated demand",
    },
    {
      key: "Slots_With_Failure",
      label: "Slots with staffing failure minimized",
      value: kpis["Slots_With_Failure"]?.failing_slots,
      pass: kpis["Slots_With_Failure"]?.failing_slots === undefined ? null : kpis["Slots_With_Failure"].failing_slots === 0,
      sub: kpis["Slots_With_Failure"]?.failure_rate !== undefined ? `${kpis["Slots_With_Failure"].failure_rate}% failure rate` : "Date/team/period cells below target",
    },
    {
      key: "Max_Shortage_Single_Slot",
      label: "Maximum single-slot shortage minimized",
      value: kpis["Max_Shortage_Single_Slot"]?.max_gap,
      pass: kpis["Max_Shortage_Single_Slot"]?.max_gap === undefined ? null : kpis["Max_Shortage_Single_Slot"].max_gap === 0,
      sub: "Worst shortage in one demanded slot",
    },
    {
      key: "Severity_Index",
      label: "Priority-weighted shortage minimized",
      value: kpis["Severity_Index"]?.severity_index,
      pass: kpis["Severity_Index"]?.severity_index === undefined ? null : kpis["Severity_Index"].severity_index === 0,
      sub: "Higher-priority shortage carries higher weight",
    },
  ].filter(c => c.value !== null && c.value !== undefined);

  return (
    <Box mt={3}>
      <Accordion elevation={2} sx={{ borderRadius: 2 }} defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>Schedule KPIs</Typography>
          <Chip
            label={hasAlarms ? "Issues found" : "All clear"}
            size="small"
            sx={{ height: 22, fontSize: 11, fontWeight: 600,
              bgcolor: hasAlarms ? T.fail.bg : T.pass.bg,
              color: hasAlarms ? T.fail.text : T.pass.text }}
          />
        </AccordionSummary>
        <AccordionDetails sx={{ px: 2.5, pb: 3 }}>

          {/* Hard constraints */}
          <SectionLabel>Hard constraints</SectionLabel>
          <Stack spacing={0.75} mb={3}>
            {alarms.map(({ key, label, pass, violations }) => {
              const tone = pass === null ? "neutral" : pass ? "pass" : "fail";
              return <StatusRow key={key} label={label} tone={tone} violations={pass === false ? violations : null} />;
            })}
          </Stack>

          {/* Soft objectives */}
          {softChecks.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <SectionLabel>Soft objectives</SectionLabel>
              <Stack spacing={0.75} mb={3}>
                {softChecks.map(({ key, label, pass, value, sub }) => {
                  const tone = pass === null ? "neutral" : pass ? "pass" : "warn";
                  return <StatusRow key={key} label={label} value={value} tone={tone} sub={sub} />;
                })}
              </Stack>
            </>
          )}

          {/* Priority hierarchy */}
          {priorities.length > 0 && (
            <>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
                <SectionLabel>Alarm priority hierarchy</SectionLabel>
                {hierarchyPass !== null && (
                  <Chip label={hierarchyPass ? "All levels met" : "Failures detected"} size="small"
                    sx={{ height: 20, fontSize: 11, fontWeight: 600,
                      bgcolor: hierarchyPass ? T.pass.bg : T.fail.bg,
                      color: hierarchyPass ? T.pass.text : T.fail.text }} />
                )}
              </Box>
              <Stack spacing={0.75} mb={3}>
                {priorities.map(entry => <PriorityRow key={entry.priority} entry={entry} />)}
              </Stack>
            </>
          )}

          {/* Coverage performance */}
          {shortageValue !== null && (
            <>
              <Divider sx={{ mb: 2 }} />
              <SectionLabel>Coverage performance</SectionLabel>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 1 }}>
                <CoverageTile
                  label="Total shortage (vs minimum)"
                  shortage={shortageValue}
                  covered={kpis["Total_Shortage"]?.minimums_covered ?? null}
                  demanded={kpis["Total_Shortage"]?.minimums_demanded ?? null}
                  coverageRate={kpis["Total_Shortage"]?.coverage_rate ?? null}
                />
                <CoverageTile
                  label="Staffing ideals"
                  shortage={kpis["Staffing_Ideals"]?.shortage ?? null}
                  covered={kpis["Staffing_Ideals"]?.minimums_covered ?? null}
                  demanded={kpis["Staffing_Ideals"]?.minimums_demanded ?? null}
                  coverageRate={kpis["Staffing_Ideals"]?.coverage_rate ?? null}
                />
                <CoverageTile
                  label="Staffing estimated"
                  shortage={kpis["Staffing_Estimated"]?.shortage ?? null}
                  covered={kpis["Staffing_Estimated"]?.minimums_covered ?? null}
                  demanded={kpis["Staffing_Estimated"]?.minimums_demanded ?? null}
                  coverageRate={kpis["Staffing_Estimated"]?.coverage_rate ?? null}
                />
              </Box>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: shortageBySkill ? 1 : 3 }}>
                <SlotFailureTile data={kpis["Slots_With_Failure"]} />
                <MaxShortageTile data={kpis["Max_Shortage_Single_Slot"]} />
                <SeverityTile kpis={kpis} />
              </Box>

              {shortageBySkill && Object.keys(shortageBySkill).length > 0 && (
                <>
                  <SectionLabel>Shortage by skill</SectionLabel>
                  <Stack spacing={0.75} mb={3}>
                    {Object.entries(shortageBySkill).map(([skill, val]) => (
                      <SkillShortageRow
                        key={skill}
                        skill={skill}
                        shortage={val}
                        details={kpis["Total_Shortage"]?.failing_details_by_skill?.[skill] ?? []}
                      />
                    ))}
                  </Stack>
                </>
              )}

              <MetricTile
                label="Constraint violations"
                value={failCount}
                sub={`of ${loadedCount} alarms evaluated`}
                tone={failCount === 0 ? "pass" : "fail"}
              />
            </>
          )}

          {/* Per-employee KPIs */}
          <EmployeeKPIPanel kpis={kpis} />

          {/* Workload utilisation */}
          <WorkloadUtilisationPanel kpis={kpis} />

        </AccordionDetails>
      </Accordion>
    </Box>
  );
}
