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
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import EmployeeKPIPanel from "./EmployeeKPIPanel";
import WorkloadUtilisationPanel from "./WorkloadUtilisationPanel";

// ─────────────────────────────────────────────────────────────────────────────
// Config — maps Python KPI keys to readable labels
// ─────────────────────────────────────────────────────────────────────────────

const ALARM_CONFIG = [
  {
    key: "Duplicated_assignments_per_day",
    label: "At most one assignment per employee per day",
  },
  {
    key: "Uncovered_slots_without_Skill",
    label: "Every covered slot has a skill assigned",
  },
  {
    key: "Maximum_Consecutive_Days",
    label: "No more than 5 consecutive working days",
  },
  {
    key: "Minimum_Rest_Time_Between_Shifts",
    label: "Minimum 11h rest between consecutive shifts",
  },
  {
    key: "Work_On_Unavailable_Days",
    label: "Employees do not work on unavailable days",
  },
  {
    key: "Sunday_Rest_Per_Month",
    label: "At least one Sunday off per month",
  },
  {
    key: "Weekly_Contracted_Hours",
    label: "Weekly contracted hours respected",
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function isPass(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value === 0;
  if (typeof value === "object" && "pass" in value) return value.pass;
  return null;
}

function getViolations(value) {
  if (typeof value === "object" && value !== null && "violations" in value) {
    return value.violations;
  }
  return null;
}

function getTotalShortageValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  if (typeof v === "object" && "value" in v) return v.value;
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function SectionTitle({ children }) {
  return (
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
      {children}
    </Typography>
  );
}

function AlarmRow({ label, pass, violations }) {
  const loaded = pass !== null;
  return (
    <Paper
      elevation={0}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        px: 1.5,
        py: 1,
        border: "0.5px solid",
        borderColor: "divider",
        borderLeft: `3px solid ${
          !loaded ? "#B4B2A9" : pass ? "#3B6D11" : "#A32D2D"
        }`,
        borderRadius: "0 8px 8px 0",
      }}
    >
      <Box
        sx={{
          width: 20,
          height: 20,
          borderRadius: "4px",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 11,
          fontWeight: 500,
          background: !loaded ? "#F1EFE8" : pass ? "#EAF3DE" : "#FCEBEB",
          color: !loaded ? "#5F5E5A" : pass ? "#27500A" : "#791F1F",
        }}
      >
        {!loaded ? "—" : pass ? "✓" : "✗"}
      </Box>

      <Typography variant="body2" sx={{ flex: 1 }}>
        {label}
      </Typography>

      {violations !== null && violations > 0 && (
        <Typography variant="caption" color="error" sx={{ mr: 0.5 }}>
          {violations} violation{violations !== 1 ? "s" : ""}
        </Typography>
      )}

      <Chip
        label={!loaded ? "—" : pass ? "Pass" : "Fail"}
        size="small"
        sx={{
          fontSize: 11,
          height: 20,
          background: !loaded ? "#F1EFE8" : pass ? "#EAF3DE" : "#FCEBEB",
          color: !loaded ? "#5F5E5A" : pass ? "#27500A" : "#791F1F",
        }}
      />
    </Paper>
  );
}

function PriorityRow({ entry }) {
  const [open, setOpen] = useState(false);
  const {
    priority, label, pass,
    failing_slots, total_slots,
    failing_dates, levels_pending,
  } = entry;
  const hasDetails = !levels_pending && failing_dates && failing_dates.length > 0;

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 1.5,
          py: 1,
          border: "0.5px solid",
          borderColor: "divider",
          borderLeft: `3px solid ${
            levels_pending ? "#B4B2A9" : pass ? "#3B6D11" : "#A32D2D"
          }`,
          borderRadius: open && hasDetails ? "0 8px 0 0" : "0 8px 8px 0",
          opacity: levels_pending ? 0.6 : 1,
        }}
      >
        {/* Priority number badge */}
        <Box
          sx={{
            width: 20,
            height: 20,
            borderRadius: "4px",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            fontWeight: 600,
            background: levels_pending
              ? "#F1EFE8"
              : pass
              ? "#EAF3DE"
              : "#FCEBEB",
            color: levels_pending
              ? "#5F5E5A"
              : pass
              ? "#27500A"
              : "#791F1F",
          }}
        >
          {levels_pending ? priority : pass ? "✓" : priority}
        </Box>

        <Typography
          variant="body2"
          sx={{ flex: 1, color: levels_pending ? "text.disabled" : "text.primary" }}
        >
          {label}
        </Typography>

        {/* Failing slots — only on the first rank for this skill */}
        {!levels_pending && !pass && (
          <Typography variant="caption" color="error" sx={{ mr: 0.5 }}>
            {failing_slots}/{total_slots} slots
          </Typography>
        )}

        {levels_pending ? (
          <Typography
            variant="caption"
            sx={{ color: "text.disabled", fontStyle: "italic", fontSize: 10 }}
          >
            pending levels
          </Typography>
        ) : (
          <Chip
            label={pass ? "Pass" : "Fail"}
            size="small"
            sx={{
              fontSize: 11,
              height: 20,
              background: pass ? "#EAF3DE" : "#FCEBEB",
              color: pass ? "#27500A" : "#791F1F",
            }}
          />
        )}

        {hasDetails && (
          <IconButton
            size="small"
            onClick={() => setOpen((v) => !v)}
            sx={{ ml: 0.5, p: 0.25 }}
          >
            {open ? (
              <ExpandLessIcon fontSize="small" />
            ) : (
              <ExpandMoreIcon fontSize="small" />
            )}
          </IconButton>
        )}
      </Paper>

      {/* Expandable failing dates — only shown on first rank */}
      {hasDetails && (
        <Collapse in={open}>
          <Paper
            elevation={0}
            sx={{
              border: "0.5px solid",
              borderTop: "none",
              borderColor: "divider",
              borderRadius: "0 0 8px 0",
              px: 1.5,
              py: 1,
              bgcolor: "action.hover",
            }}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: 0.75,
              }}
            >
              {failing_dates.map((fd, i) => (
                <Box
                  key={i}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    background: "#FCEBEB",
                    fontSize: 11,
                  }}
                >
                  <Typography variant="caption" sx={{ color: "#791F1F", fontWeight: 500 }}>
                    {fd.date}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "#791F1F" }}>
                    {fd.period}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "#791F1F" }}>
                    {fd.covered}/{fd.required} covered
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Collapse>
      )}
    </Box>
  );
}

function MetricCard({ label, value, sub, color }) {
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="h5"
        fontWeight={500}
        color={color || "text.primary"}
        sx={{ lineHeight: 1.3, mt: 0.25 }}
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
// Main component
// ─────────────────────────────────────────────────────────────────────────────

function StaffingTargetCard({ label, shortage, minimums_covered, minimums_demanded, coverage_rate }) {
  if (shortage === null || shortage === undefined) return null;
  const pct = coverage_rate ?? (minimums_demanded > 0 ? Math.round((minimums_covered / minimums_demanded) * 100) : 100);
  const isOk = shortage === 0;

  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.75 }}>
        <Typography variant="h5" fontWeight={500} color={isOk ? "success.main" : "error.main"} sx={{ lineHeight: 1.2 }}>
          {shortage}
        </Typography>
        <Typography variant="body2" color={isOk ? "success.main" : "error.main"} fontWeight={500}>
          {pct}%
        </Typography>
      </Box>
      <Box sx={{ height: 4, borderRadius: 2, bgcolor: isOk ? "#C0DD97" : "#F7C1C1", position: "relative", overflow: "hidden" }}>
        <Box sx={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pct}%`, borderRadius: 2, bgcolor: isOk ? "#3B6D11" : "#A32D2D", transition: "width .4s ease" }} />
      </Box>
      {minimums_covered !== null && minimums_covered !== undefined && minimums_demanded > 0 && (
        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: "block" }}>
          {minimums_covered}/{minimums_demanded} minimums covered
        </Typography>
      )}
    </Paper>
  );
}

function SlotFailureCard({ data }) {
  if (!data) return null;
  const { failing_slots, total_slots, failure_rate } = data;
  const isOk = failing_slots === 0;
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">Slots with failure</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.75 }}>
        <Typography variant="h5" fontWeight={500} color={isOk ? "success.main" : "error.main"} sx={{ lineHeight: 1.2 }}>
          {failing_slots}
        </Typography>
        <Typography variant="body2" color={isOk ? "success.main" : "error.main"} fontWeight={500}>
          {failure_rate}%
        </Typography>
      </Box>
      <Box sx={{ height: 4, borderRadius: 2, bgcolor: isOk ? "#C0DD97" : "#F7C1C1", position: "relative", overflow: "hidden" }}>
        <Box sx={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${failure_rate}%`, borderRadius: 2, bgcolor: isOk ? "#3B6D11" : "#A32D2D", transition: "width .4s ease" }} />
      </Box>
      <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: "block" }}>
        of {total_slots} demanded slots
      </Typography>
    </Paper>
  );
}

function MaxShortageCard({ data }) {
  if (!data) return null;
  const { max_gap, worst_slots } = data;
  const isOk = max_gap === 0;
  const worst = worst_slots?.[0];
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">Max shortage (single slot)</Typography>
      <Typography variant="h5" fontWeight={500} color={isOk ? "success.main" : "error.main"} sx={{ lineHeight: 1.2, mt: 0.25, mb: 0.5 }}>
        {max_gap}
      </Typography>
      <Typography variant="caption" color="text.disabled" sx={{ display: "block" }}>
        worker-slots in worst slot
      </Typography>
      {worst && !isOk && (
        <Typography variant="caption" color="error" sx={{ display: "block", mt: 0.5 }}>
          {worst.date} · {worst.team} · {worst.period}
        </Typography>
      )}
    </Paper>
  );
}

function MeanShortageCard({ data }) {
  if (!data) return null;
  const { mean_shortage, mean_shortage_failing, total_slots } = data;
  const isOk = mean_shortage === 0;
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">Mean shortage / slot</Typography>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.5 }}>
        <Typography variant="h5" fontWeight={500} color={isOk ? "success.main" : "error.main"} sx={{ lineHeight: 1.2 }}>
          {mean_shortage}
        </Typography>
        <Typography variant="caption" color="text.disabled">all slots</Typography>
      </Box>
      <Typography variant="caption" color="text.disabled" sx={{ display: "block" }}>
        {mean_shortage_failing} avg over failing slots · {total_slots} total
      </Typography>
    </Paper>
  );
}



function SeverityCard({ kpis }) {
  const data = kpis["Severity_Index"];
  if (!data) return null;
  const { severity_index, total_shortage, by_priority } = data;
  const isOk = severity_index === 0;

  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="caption" color="text.secondary">
        Severity index
      </Typography>

      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mt: 0.25, mb: 0.5 }}>
        <Typography
          variant="h5"
          fontWeight={500}
          color={isOk ? "success.main" : "error.main"}
          sx={{ lineHeight: 1.2 }}
        >
          {severity_index}
        </Typography>
        <Typography variant="caption" color="text.disabled">
          weighted
        </Typography>
      </Box>

      <Typography variant="caption" color="text.disabled" sx={{ display: "block", mb: 0.75 }}>
        {total_shortage} unweighted · higher priority = higher weight
      </Typography>

      {/* Mini breakdown by skill */}
      {by_priority && by_priority.filter((p) => p.shortage > 0).length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.4 }}>
          {by_priority
            .filter((p) => p.shortage > 0)
            .map((p) => (
              <Box
                key={p.priority}
                sx={{ display: "flex", alignItems: "center", gap: 0.75 }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    minWidth: 18,
                    fontSize: 10,
                    fontWeight: 600,
                    color: "#791F1F",
                    bgcolor: "#FCEBEB",
                    borderRadius: "3px",
                    px: 0.5,
                    textAlign: "center",
                  }}
                >
                  {p.priority}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
                  {p.skill}
                </Typography>
                <Typography variant="caption" color="error" fontWeight={500}>
                  ×{p.weight} = {p.weighted}
                </Typography>
              </Box>
            ))}
        </Box>
      )}
    </Paper>
  );
}

function SkillShortageCard({ skill, shortage, details }) {
  const [open, setOpen] = useState(false);
  const isOk      = shortage === 0;
  const hasDetail = details && details.length > 0;

  // Group details by date for a cleaner display
  const byDate = {};
  for (const d of details) {
    if (!byDate[d.date]) byDate[d.date] = [];
    byDate[d.date].push(d);
  }

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 1.5,
          py: 1,
          border: "0.5px solid",
          borderColor: "divider",
          borderLeft: `3px solid ${isOk ? "#3B6D11" : "#A32D2D"}`,
          borderRadius: open && hasDetail ? "0 8px 0 0" : "0 8px 8px 0",
        }}
      >
        <Typography variant="body2" fontWeight={500} sx={{ minWidth: 90 }}>
          {skill}
        </Typography>

        <Typography
          variant="h6"
          fontWeight={500}
          sx={{ color: isOk ? "success.main" : "error.main", lineHeight: 1 }}
        >
          {shortage}
        </Typography>

        <Typography variant="caption" color="text.disabled" sx={{ flex: 1 }}>
          worker-slots short
          {hasDetail && ` · ${details.length} slot${details.length !== 1 ? "s" : ""} affected`}
        </Typography>

        {hasDetail && (
          <IconButton
            size="small"
            onClick={() => setOpen((v) => !v)}
            sx={{ p: 0.25 }}
            aria-label={open ? "collapse" : "expand"}
          >
            {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        )}
      </Paper>

      {hasDetail && (
        <Collapse in={open}>
          <Paper
            elevation={0}
            sx={{
              border: "0.5px solid",
              borderTop: "none",
              borderColor: "divider",
              borderRadius: "0 0 8px 0",
              px: 1.5,
              py: 1,
              bgcolor: "action.hover",
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {Object.entries(byDate).map(([date, slots]) => (
                <Box key={date}>
                  {/* Date header */}
                  <Typography
                    variant="caption"
                    fontWeight={500}
                    color="text.secondary"
                    sx={{ display: "block", mb: 0.4 }}
                  >
                    {date}
                  </Typography>

                  {/* Slot rows */}
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, pl: 1 }}>
                    {slots.map((s, i) => (
                      <Box
                        key={i}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.75,
                          px: 1,
                          py: 0.25,
                          borderRadius: 1,
                          bgcolor: "#FCEBEB",
                          fontSize: 11,
                        }}
                      >
                        <Typography variant="caption" sx={{ color: "#791F1F", fontWeight: 500 }}>
                          {s.period}
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#791F1F" }}>
                          {s.covered}/{s.required}
                        </Typography>
                        <Chip
                          label={`-${s.gap}`}
                          size="small"
                          sx={{
                            height: 16,
                            fontSize: 10,
                            bgcolor: "#F09595",
                            color: "#501313",
                          }}
                        />
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

export default function SisqualKPIReport({ kpis }) {
  if (!kpis) return null;

  // Guard: only render for Sisqual KPI dicts
  const isSisqual = ALARM_CONFIG.some((a) => a.key in kpis);
  if (!isSisqual) return null;

  // ── Alarms ──
  const alarms = ALARM_CONFIG.map(({ key, label }) => ({
    key,
    label,
    pass:       isPass(kpis[key]),
    violations: getViolations(kpis[key]),
  }));

  const failCount   = alarms.filter((a) => a.pass === false).length;
  const loadedCount = alarms.filter((a) => a.pass !== null).length;

  // ── Shortage ──
  const shortageRaw   = kpis["Total_Shortage"] ?? null;
  const shortageValue = getTotalShortageValue(shortageRaw);
  const shortageBySkill =
    typeof shortageRaw === "object" && shortageRaw?.shortage_by_skill
      ? shortageRaw.shortage_by_skill
      : null;

  // ── Priority hierarchy ──
  const hierarchy    = kpis["Priority_Hierarchy"] ?? null;
  const priorities   = hierarchy?.priorities ?? [];
  const hierarchyPass = hierarchy?.pass ?? null;

  return (
    <Box mt={3}>

      {/* ── Section 1: Hard constraint alarms ── */}
      <SectionTitle>Hard constraint alarms</SectionTitle>
      <Stack spacing={0.75} mb={2.5}>
        {alarms.map(({ key, label, pass, violations }) => (
          <AlarmRow key={key} label={label} pass={pass} violations={violations} />
        ))}
      </Stack>

      {/* ── Section 2: Alarm priority hierarchy ── */}
      {priorities.length > 0 && (
        <>
          <Divider sx={{ my: 1.5 }} />
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1.5,
            }}
          >
            <SectionTitle>Alarm priority hierarchy</SectionTitle>
            {hierarchyPass !== null && (
              <Chip
                label={hierarchyPass ? "All levels met" : "Failures detected"}
                size="small"
                sx={{
                  fontSize: 11,
                  height: 20,
                  mb: 1.5,
                  background: hierarchyPass ? "#EAF3DE" : "#FCEBEB",
                  color: hierarchyPass ? "#27500A" : "#791F1F",
                }}
              />
            )}
          </Box>
          <Stack spacing={0.75} mb={2.5}>
            {priorities.map((entry) => (
              <PriorityRow key={entry.priority} entry={entry} />
            ))}
          </Stack>
        </>
      )}

      {/* ── Section 3: Performance metrics ── */}
      {shortageValue !== null && (
        <>
          <Divider sx={{ my: 1.5 }} />
          <SectionTitle>Performance</SectionTitle>

          {/* Standalone constraint summary block */}
          <Box sx={{ mb: 1.5 }}>
            <MetricCard
              label="Constraint violations"
              value={failCount}
              sub={`of ${loadedCount} alarms evaluated`}
              color={failCount === 0 ? "success.main" : "error.main"}
            />
          </Box>

          {/* Row 1: Total shortage (with bar) + severity index */}
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 1 }}>
            <StaffingTargetCard
              label="Total shortage (vs minimum)"
              shortage={shortageValue}
              minimums_covered={kpis["Total_Shortage"]?.minimums_covered ?? null}
              minimums_demanded={kpis["Total_Shortage"]?.minimums_demanded ?? null}
              coverage_rate={kpis["Total_Shortage"]?.coverage_rate ?? null}
            />
            <SeverityCard kpis={kpis} />
          </Box>

          {/* Row 2: Staffing Ideals + Estimated */}
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 1 }}>
            <StaffingTargetCard
              label="Staffing ideals"
              shortage={kpis["Staffing_Ideals"]?.shortage ?? null}
              minimums_covered={kpis["Staffing_Ideals"]?.minimums_covered ?? null}
              minimums_demanded={kpis["Staffing_Ideals"]?.minimums_demanded ?? null}
              coverage_rate={kpis["Staffing_Ideals"]?.coverage_rate ?? null}
            />
            <StaffingTargetCard
              label="Staffing estimated"
              shortage={kpis["Staffing_Estimated"]?.shortage ?? null}
              minimums_covered={kpis["Staffing_Estimated"]?.minimums_covered ?? null}
              minimums_demanded={kpis["Staffing_Estimated"]?.minimums_demanded ?? null}
              coverage_rate={kpis["Staffing_Estimated"]?.coverage_rate ?? null}
            />
          </Box>

          {/* Row 3: Slots with failure + Max shortage + Mean shortage */}
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
            <SlotFailureCard data={kpis["Slots_With_Failure"]} />
            <MaxShortageCard data={kpis["Max_Shortage_Single_Slot"]} />
            <MeanShortageCard data={kpis["Mean_Shortage_Per_Slot"]} />
          </Box>

          {/* Row 4: Shortage breakdown by skill — expandable */}
          {shortageBySkill && Object.keys(shortageBySkill).length > 0 && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mb: 1 }}>
              {Object.entries(shortageBySkill).map(([skill, val]) => (
                <SkillShortageCard
                  key={skill}
                  skill={skill}
                  shortage={val}
                  details={kpis["Total_Shortage"]?.failing_details_by_skill?.[skill] ?? []}
                />
              ))}
            </Box>
          )}
        </>
      )}

      {/* ── Section 4: Per-employee KPIs ── */}
      <EmployeeKPIPanel kpis={kpis} />

      {/* ── Section 5: General scheduling statistics — workload utilisation ── */}
      <WorkloadUtilisationPanel kpis={kpis} />

    </Box>
  );
}