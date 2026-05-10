import React, { useState } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CardContent,
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
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ErrorIcon from "@mui/icons-material/Error";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

const metricInfo = {
  tmFails: {
    label: "Afternoon-Morning Sequence",
    description:
      "Number of times an employee works in an afternoon shift followed by a morning shift in the day after.",
  },
  consecutiveDays: {
    label: "Consecutive Work-Day Violations",
    description:
      "Number of times employees exceeded the maximum allowed run of five consecutive working days.",
  },
  workHolidays: {
    label: "Holidays and Sundays Work Days",
    description:
      "Number of work days falling on holidays and Sundays that exceed the predefined threshold.",
  },
  missedVacationDays: {
    label: "Missed Vacation Days",
    description:
      "Total variance between actual and target vacation days for all employees.",
  },
  missedWorkDays: {
    label: "Missed Working Days",
    description:
      "Total variance between actual and target working days for all employees.",
  },
  missedTeamMin: {
    label: "Missed Minimums",
    description:
      "Each team, shift, and day, the count of employees below the required minimum staffing level.",
  },
  missedTeamIdeal: {
    label: "Missed Ideals",
    description:
      "Each team, shift, and day, the count of employees below the ideal staffing level.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description:
      "Number of employees allowed to work only one team but worked in more than one.",
  },
  shiftBalance: {
    label: "Shift Balance",
    description:
      "Percentage deviation of the most unbalanced shift distribution exhibited by any employee.",
  },
  teamSatisfactionLevel: {
    label: "Team Satisfaction Level",
    description:
      "Median distribution of work between primary and secondary team for employees assigned to two teams.",
  },
  fixedDaysOffViolations: {
    label: "Fixed Days-Off Violations",
    description:
      "Number of employee week/month periods where OFF='0' days do not match the configured target after vacation adjustment (prorate/strict).",
  },
  workDaysTargetDeviation: {
    label: "Work Days Target Deviation",
    description:
      "Total absolute deviation from the target of 223 workdays per year, summed across all employees (0 means everyone has exactly 223 workdays).",
  },
  vacationDaysQuotaDeviation: {
    label: "Vacation Days Quota Deviation",
    description:
      "Total absolute deviation from the mandatory vacation days per year, across all employees (0 means everyone has exactly 30 vacation days).",
  },
  holidayWorkLimitViolations: {
    label: "Holiday Work Limit Violations",
    description:
      "Total number of holiday/sunday workdays beyond the legal limit of 22, summed across employees.",
  },
  consecutiveDaysViolations: {
    label: "Consecutive Days Violations",
    description:
      "Total count of violations where an employee worked 6 or more consecutive days without a rest day.",
  },
  totalStaffingGap: {
    label: "Total Staffing Gap",
    description:
      "Total missing staff compared to required minimums across all teams, time slots and days.",
  },
  staffingCoverageRate: {
    label: "Staffing Coverage Rate",
    description:
      "Percentage of time slots where the minimum staffing requirement was met (100% means all minimums were satisfied).",
  },
  totalIdealGap: {
    label: "Total Ideal Gap",
    description:
      "Total missing staff compared to ideal staffing levels across all teams, time slots and days (N/A when no ideal requirements are provided).",
  },
  staffingRobustnessGap: {
    label: "Staffing Robustness Gap",
    description:
      "Total missing staff compared to synthetic ideal levels (minimum + 1) across all teams, time slots and days. Measures schedule buffer above minimum requirements.",
  },
  excessStaffing: {
    label: "Excess Staffing",
    description:
      "Total extra staff assigned beyond required minimums across all teams, time slots and days.",
  },
  minRestViolations: {
    label: "Minimum Rest Violations",
    description:
      "Number of shift-to-shift transitions where the rest time between consecutive working days is less than the configured minimum (should be 0 if the schedule is valid).",
  },
  weightedMinimumCoverageRate: {
    label: "Weighted Minimum Coverage",
    description:
      "Fulfilled required staffing divided by total required staffing across all 30-minute team slots.",
  },
  criticalUnderfilledPeriods: {
    label: "Critical Underfilled Slots",
    description:
      "Count of 30-minute date, team, slot cells where actual coverage is below the required minimum.",
  },
  maxPeriodShortage: {
    label: "Max Period Shortage",
    description:
      "Largest single shortage found in any date, team, work-period cell.",
  },
  totalMinimumGap: {
    label: "Total Minimum Gap",
    description:
      "Total missing staff across all required 30-minute team slots.",
  },
  totalOverstaff: {
    label: "Total Overstaff",
    description:
      "Total of staff exceeding minimum requirements across all required 30-minute team slots.",
  },
  intraDayTeamSwitches: {
    label: "Intra-Day Team Switches",
    description:
      "Number of times staff switch teams between consecutive assigned segments inside the same day.",
  },
  primaryTeamUtilizationRate: {
    label: "Primary Team Utilization",
    description:
      "Share of assigned hours worked in each staff member's strongest-ranked team.",
  },
  durationComplianceRate: {
    label: "Duration Compliance",
    description:
      "Share of staff-days that respect the daily duration or exact time rule defined in schedule_input.csv.",
  },
  preferredDayOffPreservationRate: {
    label: "Preferred Day-Off Preservation",
    description:
      "Share of template `DO` days that remained fully off in the generated schedule.",
  },
  skillPriorityPenaltyScore: {
    label: "Skill Priority Penalty",
    description:
      "Weighted slot-level penalty for assigning employees to lower-priority skills. Lower is better. This mirrors objective 5.",
  },
  fragmentedWorkDays: {
    label: "Fragmented Work Days",
    description:
      "Count of employee-days with more than one assigned segment.",
  },
  nonPrimaryTeamHours: {
    label: "Non-Primary Team Hours",
    description:
      "Total assigned hours worked outside each employee's strongest-ranked team.",
  },
  availabilityViolations: {
    label: "Availability Violations",
    description:
      "Count of employee-days where the generated schedule violates the employee's stated availability constraints.",
  },
};

const shiftMetrics = [
  "tmFails",
  "consecutiveDays",
  "workHolidays",
  "missedVacationDays",
  "missedWorkDays",
  "missedTeamMin",
  "missedTeamIdeal",
  "singleTeamViolations",
  "shiftBalance",
  "teamSatisfactionLevel",
  "fixedDaysOffViolations",
];

const legacyHourlyMetrics = [
  "workDaysTargetDeviation",
  "vacationDaysQuotaDeviation",
  "holidayWorkLimitViolations",
  "consecutiveDaysViolations",
  "minRestViolations",
  "totalStaffingGap",
  "staffingRobustnessGap",
  "staffingCoverageRate",
  "totalIdealGap",
  "excessStaffing",
];

const sisqualSummaryMetrics = [
  "weightedMinimumCoverageRate",
  "criticalUnderfilledPeriods",
  "maxPeriodShortage",
  "totalMinimumGap",
];

const sisqualAssignmentMetrics = [
  "intraDayTeamSwitches",
  "fragmentedWorkDays",
  "primaryTeamUtilizationRate",
  "nonPrimaryTeamHours",
  "durationComplianceRate",
];

const optionalMetrics = new Set(["fixedDaysOffViolations"]);
const percentMetrics = new Set([
  "shiftBalance",
  "teamSatisfactionLevel",
  "staffingCoverageRate",
  "weightedMinimumCoverageRate",
  "primaryTeamUtilizationRate",
  "durationComplianceRate",
  "preferredDayOffPreservationRate",
]);
const sisqualIssueMetrics = [
  "criticalUnderfilledPeriods",
  "totalMinimumGap",
  "consecutiveDaysViolations",
  "minRestViolations",
  "availabilityViolations",
];

const formatMetricValue = (key, rawValue) => {
  if (rawValue === null || rawValue === undefined) return "N/A";
  const numeric = Number(rawValue);
  if (!Number.isFinite(numeric)) return String(rawValue);
  const rounded = Number.isInteger(numeric) ? numeric : Number(numeric.toFixed(2));
  return percentMetrics.has(key) ? `${rounded}%` : rounded;
};

const renderMetric = (key, rawValue, isViolation, isPercentage = false) => {
  const info = metricInfo[key] || { label: key, description: "" };
  return (
    <Box>
      <Typography variant="subtitle1" fontWeight="bold" color="primary" gutterBottom>
        <Tooltip title={info.description || ""} arrow>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {info.label || key}
            <HelpOutlineIcon fontSize="inherit" />
          </span>
        </Tooltip>
      </Typography>
      <Typography
        color={
          isPercentage
            ? "text.primary"
            : isViolation
            ? "error.main"
            : "success.main"
        }
      >
        {formatMetricValue(key, rawValue)}
      </Typography>
    </Box>
  );
};

const SummaryGrid = ({ metricKeys, metrics }) => (
  <Grid container spacing={3}>
    {metricKeys.map((key) => (
      <Grid item xs={12} sm={6} md={3} key={key}>
        {renderMetric(
          key,
          metrics[key],
          !percentMetrics.has(key) && Number(metrics[key] || 0) > 0,
          percentMetrics.has(key)
        )}
      </Grid>
    ))}
  </Grid>
);

const getStatusChip = (hasIssues) =>
  hasIssues ? (
    <Chip label="Issues Found" color="error" icon={<ErrorIcon />} />
  ) : (
    <Chip label="No Issues" color="success" icon={<CheckCircleIcon />} />
  );

const renderLegacyReport = (metricKeys, metrics, issueKeys) => {
  const hasIssues = issueKeys.some((key) => Number(metrics[key] || 0) > 0);
  return (
    <CardContent sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Key Performance Indicators (KPIs)
          </Typography>
          {getStatusChip(hasIssues)}
        </AccordionSummary>
        <AccordionDetails>
          <Paper elevation={0} sx={{ p: 3 }}>
            <SummaryGrid metricKeys={metricKeys} metrics={metrics} />
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

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

function StatusRow({ label, value, tone = "neutral", suffix = null }) {
  const colors = {
    success: { border: "#3B6D11", bg: "#EAF3DE", fg: "#27500A" },
    error: { border: "#A32D2D", bg: "#FCEBEB", fg: "#791F1F" },
    neutral: { border: "#5F5E5A", bg: "#F1EFE8", fg: "#5F5E5A" },
  };
  const palette = colors[tone] || colors.neutral;

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
        borderLeft: `3px solid ${palette.border}`,
        borderRadius: "0 8px 8px 0",
      }}
    >
      <Box sx={{ flex: 1, display: "flex", alignItems: "center", gap: 0.75 }}>
        <Typography variant="body2">
          {label}
        </Typography>
        <Tooltip title={suffix || ""} arrow>
          <HelpOutlineIcon sx={{ fontSize: 15, color: "text.secondary" }} />
        </Tooltip>
      </Box>
      <Typography variant="body2" fontWeight={700} sx={{ color: palette.fg }}>
        {value}
      </Typography>
      {suffix && (
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {suffix}
        </Typography>
      )}
    </Paper>
  );
}

function MetricPanel({ label, value, sub, color = "text.primary", info = "" }) {
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        {info ? (
          <Tooltip title={info} arrow>
            <HelpOutlineIcon sx={{ fontSize: 14, color: "text.secondary" }} />
          </Tooltip>
        ) : null}
      </Box>
      <Typography variant="h5" fontWeight={500} color={color} sx={{ lineHeight: 1.3, mt: 0.25 }}>
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

function TeamCoverageCard({ team }) {
  const coverage = Number(team.weightedMinimumCoverageRate || 0);
  const gap = Number(team.gap || 0);
  const overstaff = Number(team.overstaff || 0);
  const coverageTone =
    coverage >= 98 ? "success" : coverage >= 85 ? "warning" : "error";
  const palette = {
    success: { accent: "#3B6D11", soft: "#EAF3DE", text: "#27500A" },
    warning: { accent: "#B86500", soft: "#FFF1DB", text: "#8A4B00" },
    error: { accent: "#A32D2D", soft: "#FCEBEB", text: "#791F1F" },
  }[coverageTone];

  const statItems = [
    { label: "Required", value: team.required, tone: "neutral" },
    { label: "Filled", value: team.filled, tone: "neutral" },
    { label: "Gap", value: gap, tone: gap > 0 ? "error" : "success" },
    { label: "Overstaff", value: overstaff, tone: overstaff > 0 ? "warning" : "neutral" },
  ];

  const statTone = {
    neutral: { bg: "#F5F5F4", fg: "#44403C" },
    success: { bg: "#EAF3DE", fg: "#27500A" },
    warning: { bg: "#FFF1DB", fg: "#8A4B00" },
    error: { bg: "#FCEBEB", fg: "#791F1F" },
  };

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        height: "100%",
        pb: 3,
        borderRadius: 2,
        borderColor: "divider",
        background:
          "linear-gradient(180deg, rgba(248,250,252,0.96) 0%, rgba(255,255,255,1) 100%)",
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 1,
          mb: 1.5,
        }}
      >
        <Typography variant="subtitle1" fontWeight={700}>
          {team.team}
        </Typography>
        <Chip
          label={`${coverage.toFixed(2)}%`}
          size="small"
          sx={{
            height: 22,
            fontSize: 11,
            fontWeight: 700,
            bgcolor: palette.soft,
            color: palette.text,
          }}
        />
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75 }}>
        Coverage
      </Typography>
      <Box
        sx={{
          position: "relative",
          height: 8,
          borderRadius: 999,
          bgcolor: "#E7E5E4",
          overflow: "hidden",
          mb: 1.5,
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            width: `${Math.max(0, Math.min(coverage, 100))}%`,
            bgcolor: palette.accent,
            borderRadius: 999,
          }}
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 1,
        }}
      >
        {statItems.map((item) => (
          <Box
            key={item.label}
            sx={{
              px: 1,
              py: 0.9,
              borderRadius: 1.5,
              bgcolor: statTone[item.tone].bg,
            }}
          >
            <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
              {item.label}
            </Typography>
            <Typography
              variant="body2"
              fontWeight={700}
              sx={{ color: statTone[item.tone].fg, lineHeight: 1.25 }}
            >
              {item.value}
            </Typography>
          </Box>
        ))}
      </Box>
    </Paper>
  );
}

const NATIVE_SKILL_COLORS = {
  Management: { bg: "#E6F1FB", text: "#0C447C", bar: "#185FA5" },
  Checkout: { bg: "#EAF3DE", text: "#27500A", bar: "#3B6D11" },
  Storage: { bg: "#FAEEDA", text: "#633806", bar: "#854F0B" },
  Employees: { bg: "#F1EFE8", text: "#444441", bar: "#5F5E5A" },
};

function nativeSkillColor(skill) {
  return NATIVE_SKILL_COLORS[skill] || { bg: "#EEEDFE", text: "#3C3489", bar: "#534AB7" };
}

const employeeAssignmentInfo = {
  workByTeam: "Shows what percentage of this employee's scheduled hours were spent on each skill.",
  employee: "Employee name and internal ID.",
  workedHours: "Total number of hours assigned to this employee in the generated schedule.",
  primaryUtilization: "Percentage of assigned hours worked on the employee's primary or strongest team.",
  nonPrimaryHours: "Hours assigned outside the employee's primary team.",
  teamSwitches: "How many times the employee changes team between consecutive work segments on the same day.",
  fragmentedDays: "Number of days where the employee has more than one work segment.",
  durationCompliance: "Percentage of days where the assigned shift duration matches the allowed duration or exact rule from the input.",
  demandedHours: "Percentage of working-rule days where assigned hours exactly match the requested hours.",
  preferredDayOff: "Preferred day-off days where the employee was still scheduled to work. Lower is better.",
  skillPenalty: "Penalty for assigning work in lower-priority skills or teams. Lower is better.",
  availability: "Hard availability violations, such as working on unavailable days. This should be zero.",
  consecutive: "Times the employee exceeded the maximum consecutive working-days rule. This should be zero.",
  minRest: "Times the employee had less than the required rest between consecutive shifts. This should be zero.",
};

const skillAllocationInfo = {
  primaryTeamRate: "Percentage of all scheduled hours that were worked on each employee's primary or strongest team.",
  nonPrimaryHours: "Total scheduled hours worked outside employees' primary teams.",
  teamSwitches: "Total number of within-day changes from one team to another.",
  fragmentedDays: "Total number of employee-days split into more than one work segment.",
};

function InfoLabel({ children, info, align = "left" }) {
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: align === "right" ? "flex-end" : "flex-start",
        gap: 0.35,
        width: "100%",
      }}
    >
      <span>{children}</span>
      {info && (
        <Tooltip title={info} arrow>
          <HelpOutlineIcon sx={{ fontSize: 13, color: "text.secondary" }} />
        </Tooltip>
      )}
    </Box>
  );
}

function getEmployeeTeamBreakdown(employee) {
  if (Array.isArray(employee?.teamWorkBreakdown) && employee.teamWorkBreakdown.length > 0) {
    return employee.teamWorkBreakdown
      .map((item) => {
        const team = item.team || item.skill || "Unknown";
        const hours = Number(item.hours || 0);
        const percentage = Number(item.percentage || item.pct || 0);
        return {
          team,
          hours: Number(hours.toFixed(2)),
          percentage: Number(percentage.toFixed(2)),
        };
      })
      .filter((item) => item.hours > 0 || item.percentage > 0);
  }

  const percentageSource = employee?.teamWorkPercentages || employee?.skill_usage_pct;
  if (percentageSource && typeof percentageSource === "object") {
    const workedHours = Number(employee?.workedHours || 0);
    return Object.entries(percentageSource)
      .map(([team, rawPct]) => {
        const percentage = Number(rawPct || 0);
        return {
          team,
          hours: Number(((workedHours * percentage) / 100).toFixed(2)),
          percentage: Number(percentage.toFixed(2)),
        };
      })
      .filter((item) => item.hours > 0 || item.percentage > 0)
      .sort((a, b) => b.percentage - a.percentage || a.team.localeCompare(b.team));
  }

  const workedHours = Number(employee?.workedHours || 0);
  const nonPrimaryHours = Number(employee?.nonPrimaryTeamHours || 0);
  const primaryHours = Math.max(workedHours - nonPrimaryHours, 0);
  const rows = [];

  if (primaryHours > 0) {
    rows.push({
      team: employee?.primaryTeam || "Primary team",
      hours: Number(primaryHours.toFixed(2)),
      percentage: workedHours ? Number(((primaryHours / workedHours) * 100).toFixed(2)) : 0,
    });
  }

  if (nonPrimaryHours > 0) {
    rows.push({
      team: "Other teams",
      hours: Number(nonPrimaryHours.toFixed(2)),
      percentage: workedHours ? Number(((nonPrimaryHours / workedHours) * 100).toFixed(2)) : 0,
    });
  }

  return rows;
}

function EmployeeTeamBreakdown({ employee }) {
  const breakdown = getEmployeeTeamBreakdown(employee);
  if (!breakdown.length) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        mb: 1.5,
        border: "0.5px solid",
        borderColor: "divider",
        borderRadius: 1,
        bgcolor: "background.paper",
      }}
    >
      <Typography variant="caption" color="text.secondary" fontWeight={600} display="block" mb={0.75}>
        <InfoLabel info={employeeAssignmentInfo.workByTeam}>Work by skill</InfoLabel>
      </Typography>
      <Box sx={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", mb: 0.75, bgcolor: "action.selected" }}>
        {breakdown.map((item) => (
          <Box
            key={item.team}
            sx={{
              width: `${Math.max(0, Math.min(Number(item.percentage || 0), 100))}%`,
              bgcolor: nativeSkillColor(item.team).bar,
            }}
            title={`${item.team}: ${Number(item.percentage || 0).toFixed(2)}%`}
          />
        ))}
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {breakdown.map((item) => {
          const color = nativeSkillColor(item.team);
          return (
            <Box
              key={item.team}
              sx={{ display: "flex", alignItems: "center", gap: 0.4, px: 0.75, py: 0.25, borderRadius: 1, bgcolor: color.bg }}
            >
              <Typography variant="caption" fontWeight={600} sx={{ color: color.text, fontSize: 10 }}>
                {item.team}
              </Typography>
              <Typography variant="caption" sx={{ color: color.text, fontSize: 10 }}>
                {Number(item.percentage || 0).toFixed(2)}%
              </Typography>
              <Typography variant="caption" sx={{ color: color.text, opacity: 0.75, fontSize: 10 }}>
                {Number(item.hours || 0).toFixed(2)}h
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Paper>
  );
}

function EmployeeAssignmentQualityPanel({ employeeRows }) {
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");
  const selectedEmployee =
    employeeRows.find((employee) => employee.employeeId === selectedEmployeeId) || null;

  return (
    <Box mt={4}>
      <Divider sx={{ my: 1.5 }} />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          mb: 1.5,
          flexWrap: "wrap",
        }}
      >
        <SectionTitle>Employee Assignment Quality</SectionTitle>
        <Chip
          label={`${employeeRows.length} employees`}
          size="small"
          sx={{
            height: 22,
            fontSize: 11,
            bgcolor: "#F1EFE8",
            color: "#5F5E5A",
          }}
        />
      </Box>

      <FormControl size="small" sx={{ minWidth: 280, mb: 2 }}>
        <InputLabel sx={{ fontSize: 13 }}>Employee</InputLabel>
        <Select
          value={selectedEmployeeId}
          label="Employee"
          onChange={(event) => setSelectedEmployeeId(event.target.value)}
          sx={{ fontSize: 13 }}
        >
          <MenuItem value="">
            <em>Select an employee</em>
          </MenuItem>
          {employeeRows.map((employee) => (
            <MenuItem
              key={employee.employeeId || employee.name}
              value={employee.employeeId}
              sx={{ fontSize: 13 }}
            >
              {employee.name || employee.employeeId}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedEmployee && (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            mb: 2,
            border: "0.5px solid",
            borderColor: "divider",
            borderRadius: 2,
            bgcolor: "action.hover",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, flexWrap: "wrap" }}>
            <Typography variant="subtitle2" fontWeight={700}>
              {selectedEmployee.name || selectedEmployee.employeeId}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {selectedEmployee.employeeId}
            </Typography>
          </Box>
          <EmployeeTeamBreakdown employee={selectedEmployee} />
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 1 }}>
            <MetricPanel
              label="Worked hours"
              value={selectedEmployee.workedHours ?? 0}
              info={employeeAssignmentInfo.workedHours}
            />
            <MetricPanel
              label="Primary utilization"
              value={`${Number(selectedEmployee.primaryTeamUtilizationRate || 0).toFixed(2)}%`}
              info={employeeAssignmentInfo.primaryUtilization}
            />
            <MetricPanel
              label="Non-primary hours"
              value={selectedEmployee.nonPrimaryTeamHours ?? 0}
              info={employeeAssignmentInfo.nonPrimaryHours}
            />
            <MetricPanel
              label="Team switches"
              value={selectedEmployee.teamSwitches ?? 0}
              info={employeeAssignmentInfo.teamSwitches}
            />
            <MetricPanel
              label="Fragmented days"
              value={selectedEmployee.fragmentedWorkDays ?? 0}
              info={employeeAssignmentInfo.fragmentedDays}
            />
            <MetricPanel
              label="Duration compliance"
              value={`${Number(selectedEmployee.durationComplianceRate || 0).toFixed(2)}%`}
              info={employeeAssignmentInfo.durationCompliance}
            />
            <MetricPanel
              label="Demanded hours"
              value={`${Number(selectedEmployee.demandedHoursComplianceRate || 0).toFixed(2)}%`}
              info={employeeAssignmentInfo.demandedHours}
            />
            <MetricPanel
              label="Preferred DO"
              value={selectedEmployee.preferredDayOffWorkedDays ?? 0}
              color={Number(selectedEmployee.preferredDayOffWorkedDays || 0) > 0 ? "error.main" : "success.main"}
              info={employeeAssignmentInfo.preferredDayOff}
            />
            <MetricPanel
              label="Skill penalty"
              value={selectedEmployee.skillPriorityPenaltyScore ?? 0}
              info={employeeAssignmentInfo.skillPenalty}
            />
            <MetricPanel
              label="Availability"
              value={selectedEmployee.availabilityViolations ?? 0}
              color={Number(selectedEmployee.availabilityViolations || 0) > 0 ? "error.main" : "success.main"}
              info={employeeAssignmentInfo.availability}
            />
            <MetricPanel
              label="Consecutive"
              value={selectedEmployee.consecutiveDaysViolations ?? 0}
              color={Number(selectedEmployee.consecutiveDaysViolations || 0) > 0 ? "error.main" : "success.main"}
              info={employeeAssignmentInfo.consecutive}
            />
            <MetricPanel
              label="Min rest"
              value={selectedEmployee.minRestViolations ?? 0}
              color={Number(selectedEmployee.minRestViolations || 0) > 0 ? "error.main" : "success.main"}
              info={employeeAssignmentInfo.minRest}
            />
          </Box>
        </Paper>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight: 520 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell><InfoLabel info={employeeAssignmentInfo.employee}>Employee</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.workedHours}>Worked h</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.primaryUtilization}>Primary %</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.nonPrimaryHours}>Non-primary h</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.teamSwitches}>Switches</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.fragmentedDays}>Fragments</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.durationCompliance}>Duration %</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.demandedHours}>Demanded %</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.preferredDayOff}>Pref. DO</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.skillPenalty}>Skill penalty</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.availability}>Availability</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.consecutive}>Consecutive</InfoLabel></TableCell>
              <TableCell align="right"><InfoLabel align="right" info={employeeAssignmentInfo.minRest}>Min rest</InfoLabel></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {employeeRows.map((employee) => (
              <TableRow key={employee.employeeId || employee.name}>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {employee.name || employee.employeeId}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {employee.employeeId}
                  </Typography>
                </TableCell>
                <TableCell align="right">{employee.workedHours ?? 0}</TableCell>
                <TableCell align="right">{Number(employee.primaryTeamUtilizationRate || 0).toFixed(2)}%</TableCell>
                <TableCell align="right">{employee.nonPrimaryTeamHours ?? 0}</TableCell>
                <TableCell align="right">{employee.teamSwitches ?? 0}</TableCell>
                <TableCell align="right">{employee.fragmentedWorkDays ?? 0}</TableCell>
                <TableCell align="right">{Number(employee.durationComplianceRate || 0).toFixed(2)}%</TableCell>
                <TableCell align="right">{Number(employee.demandedHoursComplianceRate || 0).toFixed(2)}%</TableCell>
                <TableCell
                  align="right"
                  sx={{ color: Number(employee.preferredDayOffWorkedDays || 0) > 0 ? "error.main" : "success.main" }}
                >
                  {employee.preferredDayOffWorkedDays ?? 0}
                </TableCell>
                <TableCell align="right">{employee.skillPriorityPenaltyScore ?? 0}</TableCell>
                <TableCell
                  align="right"
                  sx={{ color: Number(employee.availabilityViolations || 0) > 0 ? "error.main" : "success.main" }}
                >
                  {employee.availabilityViolations ?? 0}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ color: Number(employee.consecutiveDaysViolations || 0) > 0 ? "error.main" : "success.main" }}
                >
                  {employee.consecutiveDaysViolations ?? 0}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ color: Number(employee.minRestViolations || 0) > 0 ? "error.main" : "success.main" }}
                >
                  {employee.minRestViolations ?? 0}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

function NativeWorkloadUtilisationPanel({ employeeRows }) {
  if (!employeeRows.length) return null;

  const workedHours = employeeRows.map((employee) => Number(employee.workedHours || 0));
  const totalHours = workedHours.reduce((sum, value) => sum + value, 0);
  const maxHours = Math.max(...workedHours, 0);
  const minHours = Math.min(...workedHours, 0);
  const averageHours = employeeRows.length ? totalHours / employeeRows.length : 0;
  const employeeSkillRows = employeeRows
    .map((employee) => ({
      employee,
      breakdown: getEmployeeTeamBreakdown(employee),
    }))
    .sort((a, b) => Number(b.employee.workedHours || 0) - Number(a.employee.workedHours || 0));
  const skillsUsed = new Set(
    employeeSkillRows.flatMap((row) => row.breakdown.map((item) => item.team))
  ).size;

  return (
    <Box mt={4}>
      <Divider sx={{ my: 1.5 }} />
      <SectionTitle>Workload Utilisation</SectionTitle>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 1, mb: 1.5 }}>
        <MetricPanel label="Total worked hours" value={Number(totalHours.toFixed(2))} />
        <MetricPanel label="Average hours" value={Number(averageHours.toFixed(2))} />
        <MetricPanel label="Max-min gap" value={Number((maxHours - minHours).toFixed(2))} />
        <MetricPanel label="Skills used" value={skillsUsed} />
      </Box>

      <Paper elevation={0} sx={{ p: 1.5, border: "0.5px solid", borderColor: "divider", borderRadius: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1, flexWrap: "wrap" }}>
          <Typography variant="caption" color="text.secondary" fontWeight={500}>
            Per-employee time by skill
          </Typography>
          <Chip
            label="percent of each worker's assigned time"
            size="small"
            sx={{
              height: 20,
              fontSize: 10,
              bgcolor: "#F1EFE8",
              color: "#5F5E5A",
            }}
          />
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {employeeSkillRows.map(({ employee, breakdown }) => {
            const hours = Number(employee.workedHours || 0);

            return (
              <Box
                key={employee.employeeId || employee.name}
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
                <Box
                  sx={{
                    flex: "0 0 190px",
                    width: 190,
                    minWidth: 0,
                    overflow: "hidden",
                  }}
                >
                  <Typography
                    variant="caption"
                    fontWeight={600}
                    sx={{
                      display: "block",
                      lineHeight: 1.25,
                      whiteSpace: "normal",
                      overflowWrap: "anywhere",
                    }}
                  >
                    {employee.name || employee.employeeId}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" noWrap>
                    {employee.employeeId}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box
                    sx={{
                      display: "flex",
                      height: 8,
                      borderRadius: 4,
                      bgcolor: "action.selected",
                      overflow: "hidden",
                      mb: 0.65,
                    }}
                  >
                    {breakdown.length > 0 ? (
                      breakdown.map((item) => {
                        const pct = Math.max(0, Math.min(Number(item.percentage || 0), 100));
                        return (
                          <Box
                            key={item.team}
                            sx={{
                              width: `${pct}%`,
                              minWidth: pct > 0 ? 3 : 0,
                              bgcolor: nativeSkillColor(item.team).bar,
                            }}
                            title={`${item.team}: ${pct.toFixed(2)}% (${Number(item.hours || 0).toFixed(2)}h)`}
                          />
                        );
                      })
                    ) : (
                      <Box sx={{ width: "100%", bgcolor: "action.disabledBackground" }} />
                    )}
                  </Box>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {breakdown.map((item) => {
                      const color = nativeSkillColor(item.team);
                      return (
                        <Box
                          key={item.team}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 0.4,
                            px: 0.75,
                            py: 0.2,
                            borderRadius: 1,
                            bgcolor: color.bg,
                          }}
                        >
                          <Typography variant="caption" fontWeight={600} sx={{ color: color.text, fontSize: 10 }}>
                            {item.team}
                          </Typography>
                          <Typography variant="caption" sx={{ color: color.text, fontSize: 10 }}>
                            {Number(item.percentage || 0).toFixed(2)}%
                          </Typography>
                        </Box>
                      );
                    })}
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 64, textAlign: "right" }}>
                  {hours}h
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Paper>
    </Box>
  );
}

function NativeSkillAllocationPanel({ employeeRows }) {
  if (!employeeRows.length) return null;

  let totalWorkedHours = 0;
  let totalNonPrimaryHours = 0;
  let totalSwitches = 0;
  let totalFragments = 0;

  for (const employee of employeeRows) {
    totalWorkedHours += Number(employee.workedHours || 0);
    totalNonPrimaryHours += Number(employee.nonPrimaryTeamHours || 0);
    totalSwitches += Number(employee.teamSwitches || 0);
    totalFragments += Number(employee.fragmentedWorkDays || 0);
  }

  const primaryRate = totalWorkedHours
    ? Number((((totalWorkedHours - totalNonPrimaryHours) / totalWorkedHours) * 100).toFixed(2))
    : 100;

  return (
    <Box mt={4}>
      <Divider sx={{ my: 1.5 }} />
      <SectionTitle>Skill Allocation</SectionTitle>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 1 }}>
        <MetricPanel
          label="Primary-team rate"
          value={`${primaryRate}%`}
          info={skillAllocationInfo.primaryTeamRate}
        />
        <MetricPanel
          label="Non-primary hours"
          value={Number(totalNonPrimaryHours.toFixed(2))}
          info={skillAllocationInfo.nonPrimaryHours}
        />
        <MetricPanel
          label="Team switches"
          value={totalSwitches}
          info={skillAllocationInfo.teamSwitches}
        />
        <MetricPanel
          label="Fragmented days"
          value={totalFragments}
          info={skillAllocationInfo.fragmentedDays}
        />
      </Box>
    </Box>
  );
}

const renderSisqualReport = (metrics) => {
  const hasIssues = sisqualIssueMetrics.some((key) => Number(metrics[key] || 0) > 0);
  const teamCoverage = Array.isArray(metrics.teamCoverageBreakdown)
    ? metrics.teamCoverageBreakdown
    : [];
  const underfilledPeriods = Array.isArray(metrics.underfilledPeriods)
    ? metrics.underfilledPeriods.slice(0, 12)
    : [];
  const employeeRows = Array.isArray(metrics.employeeAssignmentQuality)
    ? metrics.employeeAssignmentQuality
    : [];

  return (
    <CardContent sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }} defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Sisqual Hour KPIs
          </Typography>
          {getStatusChip(hasIssues)}
        </AccordionSummary>
        <AccordionDetails>
          <Paper elevation={0} sx={{ p: 3 }}>
            <SectionTitle>Hour Constraint Alarms</SectionTitle>
            <Stack spacing={0.75} mb={2.5}>
              <StatusRow
                label="No more than 5 consecutive working days"
                value={metrics.consecutiveDaysViolations ?? 0}
                suffix={metricInfo.consecutiveDaysViolations?.description}
                tone={Number(metrics.consecutiveDaysViolations || 0) > 0 ? "error" : "success"}
              />
              <StatusRow
                label="Minimum 11h rest between consecutive shifts"
                value={metrics.minRestViolations ?? 0}
                suffix={metricInfo.minRestViolations?.description}
                tone={Number(metrics.minRestViolations || 0) > 0 ? "error" : "success"}
              />
              <StatusRow
                label="Employees do not work on unavailable days"
                value={metrics.availabilityViolations ?? 0}
                suffix={metricInfo.availabilityViolations?.description}
                tone={Number(metrics.availabilityViolations || 0) > 0 ? "error" : "success"}
              />
            </Stack>

            <Divider sx={{ my: 1.5 }} />
            <SectionTitle>Coverage Summary</SectionTitle>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
              <MetricPanel
                label="Weighted minimum coverage"
                value={`${Number(metrics.weightedMinimumCoverageRate || 0).toFixed(2)}%`}
                color="text.primary"
                info={metricInfo.weightedMinimumCoverageRate?.description}
              />
              <MetricPanel
                label="Critical underfilled slots"
                value={metrics.criticalUnderfilledPeriods ?? 0}
                color={Number(metrics.criticalUnderfilledPeriods || 0) > 0 ? "error.main" : "success.main"}
                info={metricInfo.criticalUnderfilledPeriods?.description}
              />
              <MetricPanel
                label="Total minimum gap"
                value={metrics.totalMinimumGap ?? 0}
                color={Number(metrics.totalMinimumGap || 0) > 0 ? "error.main" : "success.main"}
                info={metricInfo.totalMinimumGap?.description}
              />
            </Box>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
              <MetricPanel
                label="Max period shortage"
                value={metrics.maxPeriodShortage ?? 0}
                color={Number(metrics.maxPeriodShortage || 0) > 0 ? "error.main" : "success.main"}
                info={metricInfo.maxPeriodShortage?.description}
              />
              <MetricPanel
                label="Total overstaff"
                value={metrics.totalOverstaff ?? 0}
                color={Number(metrics.totalOverstaff || 0) > 0 ? "warning.main" : "success.main"}
                info={metricInfo.totalOverstaff?.description}
              />
            </Box>

            <Divider sx={{ my: 1.5 }} />
            <SectionTitle>Assignment Quality</SectionTitle>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
              <MetricPanel label="Intra-day team switches" value={metrics.intraDayTeamSwitches ?? 0} info={metricInfo.intraDayTeamSwitches?.description} />
              <MetricPanel label="Fragmented work days" value={metrics.fragmentedWorkDays ?? 0} info={metricInfo.fragmentedWorkDays?.description} />
              <MetricPanel
                label="Primary team utilization"
                value={`${Number(metrics.primaryTeamUtilizationRate || 0).toFixed(2)}%`}
                info={metricInfo.primaryTeamUtilizationRate?.description}
              />
            </Box>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
              <MetricPanel label="Non-primary team hours" value={metrics.nonPrimaryTeamHours ?? 0} info={metricInfo.nonPrimaryTeamHours?.description} />
              <MetricPanel
                label="Duration compliance"
                value={`${Number(metrics.durationComplianceRate || 0).toFixed(2)}%`}
                info={metricInfo.durationComplianceRate?.description}
              />
            </Box>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, mb: 1 }}>
              <MetricPanel
                label="Preferred day-off preservation"
                value={`${Number(metrics.preferredDayOffPreservationRate || 0).toFixed(2)}%`}
                info={metricInfo.preferredDayOffPreservationRate?.description}
              />
              <MetricPanel
                label="Skill priority penalty"
                value={metrics.skillPriorityPenaltyScore ?? 0}
                info={metricInfo.skillPriorityPenaltyScore?.description}
              />
            </Box>
            {employeeRows.length > 0 && (
              <NativeSkillAllocationPanel employeeRows={employeeRows} />
            )}
            {teamCoverage.length > 0 && (
              <Box mt={4}>
                <Divider sx={{ my: 1.5 }} />
                <SectionTitle>Team Coverage Breakdown</SectionTitle>
                <Grid container spacing={2}>
                  {teamCoverage.map((team) => (
                    <Grid item xs={12} md={6} lg={3} key={team.team}>
                      <TeamCoverageCard team={team} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}

            {underfilledPeriods.length > 0 && (
              <Box sx={{ mt: 4, pt: 1 }}>
                <Divider sx={{ mt: 0, mb: 2 }} />
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 1,
                    mb: 1.5,
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    sx={{
                      textTransform: "uppercase",
                      letterSpacing: ".05em",
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    Most Critical Underfilled Periods
                  </Typography>
                  <Chip
                    label={`${underfilledPeriods.length} shown`}
                    size="small"
                    sx={{
                      height: 22,
                      fontSize: 11,
                      bgcolor: "#F1EFE8",
                      color: "#5F5E5A",
                    }}
                  />
                </Box>
                <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell>Team</TableCell>
                        <TableCell>Period</TableCell>
                        <TableCell align="right">Required</TableCell>
                        <TableCell align="right">Actual</TableCell>
                        <TableCell align="right">Shortage</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {underfilledPeriods.map((row, index) => (
                        <TableRow key={`${row.date}-${row.team}-${row.workPeriod}-${index}`}>
                          <TableCell>{row.date}</TableCell>
                          <TableCell>{row.team}</TableCell>
                          <TableCell>{row.label || `${row.start}-${row.end}`}</TableCell>
                          <TableCell align="right">{row.required}</TableCell>
                          <TableCell align="right">{row.actual}</TableCell>
                          <TableCell align="right" sx={{ color: "error.main", fontWeight: 700 }}>
                            {row.shortage}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {employeeRows.length > 0 && (
              <>
                <EmployeeAssignmentQualityPanel employeeRows={employeeRows} />
                <NativeWorkloadUtilisationPanel employeeRows={employeeRows} />
              </>
            )}
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

const KPIReport = ({ metrics = {}, scheduleType }) => {
  if (!metrics || !Object.keys(metrics).length) {
    return null;
  }

  const normalizedType = String(scheduleType || "").toLowerCase();
  const isSisqualHourly =
    metrics.weightedMinimumCoverageRate !== undefined ||
    Array.isArray(metrics.teamCoverageBreakdown);

  if (isSisqualHourly) {
    return renderSisqualReport(metrics);
  }

  const isHourly =
    normalizedType === "horas" ||
    normalizedType === "hours" ||
    metrics.totalStaffingGap !== undefined ||
    metrics.excessStaffing !== undefined ||
    metrics.workDaysTargetDeviation !== undefined;

  const metricKeys = (isHourly ? legacyHourlyMetrics : shiftMetrics).filter(
    (key) => !optionalMetrics.has(key) || metrics[key] !== undefined
  );
  const issueKeys = metricKeys.filter((key) => key !== "shiftBalance" && key !== "teamSatisfactionLevel");

  return renderLegacyReport(metricKeys, metrics, issueKeys);
};

export default KPIReport;
