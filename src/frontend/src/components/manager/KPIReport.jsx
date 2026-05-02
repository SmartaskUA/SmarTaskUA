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
  preferredDayOffWorkedDays: {
    label: "Preferred Day-Off Worked Days",
    description:
      "Number of template `DO` days that still ended up assigned. This is the direct KPI counterpart of objective 4.",
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
  "preferredDayOffWorkedDays",
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

function buildPriorityTierSummary(employeeRows) {
  const grouped = new Map();

  for (const employee of employeeRows || []) {
    const key = `${employee.priorityRank ?? "?"}::${employee.priorityLabel || "Unmapped priority"}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        priorityRank: employee.priorityRank ?? Number.MAX_SAFE_INTEGER,
        priorityLabel: employee.priorityLabel || "Unmapped priority",
        employeeCount: 0,
        workedHours: 0,
        availabilityViolations: 0,
        preferredDayOffWorkedDays: 0,
        consecutiveDaysViolations: 0,
        minRestViolations: 0,
        durationComplianceRateSum: 0,
      });
    }

    const row = grouped.get(key);
    row.employeeCount += 1;
    row.workedHours += Number(employee.workedHours || 0);
    row.availabilityViolations += Number(employee.availabilityViolations || 0);
    row.preferredDayOffWorkedDays += Number(employee.preferredDayOffWorkedDays || 0);
    row.consecutiveDaysViolations += Number(employee.consecutiveDaysViolations || 0);
    row.minRestViolations += Number(employee.minRestViolations || 0);
    row.durationComplianceRateSum += Number(employee.durationComplianceRate || 0);
  }

  return Array.from(grouped.values())
    .map((row) => ({
      ...row,
      workedHours: Number(row.workedHours.toFixed(2)),
      durationComplianceRate: row.employeeCount
        ? Number((row.durationComplianceRateSum / row.employeeCount).toFixed(2))
        : 100,
    }))
    .sort((a, b) => a.priorityRank - b.priorityRank);
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
            <Chip
              label={`#${selectedEmployee.priorityRank ?? "?"}`}
              size="small"
              sx={{ height: 20, fontSize: 11, bgcolor: "#F1EFE8", color: "#5F5E5A" }}
            />
            <Typography variant="caption" color="text.secondary">
              {selectedEmployee.priorityLabel || selectedEmployee.priorityTeam || selectedEmployee.primaryTeam || "Unmapped"}
            </Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 1 }}>
            <MetricPanel label="Worked hours" value={selectedEmployee.workedHours ?? 0} />
            <MetricPanel
              label="Primary utilization"
              value={`${Number(selectedEmployee.primaryTeamUtilizationRate || 0).toFixed(2)}%`}
            />
            <MetricPanel label="Non-primary hours" value={selectedEmployee.nonPrimaryTeamHours ?? 0} />
            <MetricPanel label="Team switches" value={selectedEmployee.teamSwitches ?? 0} />
            <MetricPanel label="Fragmented days" value={selectedEmployee.fragmentedWorkDays ?? 0} />
            <MetricPanel
              label="Duration compliance"
              value={`${Number(selectedEmployee.durationComplianceRate || 0).toFixed(2)}%`}
            />
            <MetricPanel
              label="Demanded hours"
              value={`${Number(selectedEmployee.demandedHoursComplianceRate || 0).toFixed(2)}%`}
            />
            <MetricPanel
              label="Preferred DO"
              value={selectedEmployee.preferredDayOffWorkedDays ?? 0}
              color={Number(selectedEmployee.preferredDayOffWorkedDays || 0) > 0 ? "error.main" : "success.main"}
            />
            <MetricPanel label="Skill penalty" value={selectedEmployee.skillPriorityPenaltyScore ?? 0} />
            <MetricPanel
              label="Availability"
              value={selectedEmployee.availabilityViolations ?? 0}
              color={Number(selectedEmployee.availabilityViolations || 0) > 0 ? "error.main" : "success.main"}
            />
            <MetricPanel
              label="Consecutive"
              value={selectedEmployee.consecutiveDaysViolations ?? 0}
              color={Number(selectedEmployee.consecutiveDaysViolations || 0) > 0 ? "error.main" : "success.main"}
            />
            <MetricPanel
              label="Min rest"
              value={selectedEmployee.minRestViolations ?? 0}
              color={Number(selectedEmployee.minRestViolations || 0) > 0 ? "error.main" : "success.main"}
            />
          </Box>
        </Paper>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight: 520 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Employee</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell align="right">Worked h</TableCell>
              <TableCell align="right">Primary %</TableCell>
              <TableCell align="right">Non-primary h</TableCell>
              <TableCell align="right">Switches</TableCell>
              <TableCell align="right">Fragments</TableCell>
              <TableCell align="right">Duration %</TableCell>
              <TableCell align="right">Demanded %</TableCell>
              <TableCell align="right">Pref. DO</TableCell>
              <TableCell align="right">Skill penalty</TableCell>
              <TableCell align="right">Availability</TableCell>
              <TableCell align="right">Consecutive</TableCell>
              <TableCell align="right">Min rest</TableCell>
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
                <TableCell>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Chip
                      label={`#${employee.priorityRank ?? "?"}`}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: 11,
                        bgcolor: "#F1EFE8",
                        color: "#5F5E5A",
                      }}
                    />
                    <Typography variant="caption" sx={{ lineHeight: 1.2 }}>
                      {employee.priorityLabel || employee.priorityTeam || employee.primaryTeam || "Unmapped"}
                    </Typography>
                  </Box>
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

const renderSisqualReport = (metrics) => {
  const hasIssues = sisqualIssueMetrics.some((key) => Number(metrics[key] || 0) > 0);
  const teamCoverage = Array.isArray(metrics.teamCoverageBreakdown)
    ? metrics.teamCoverageBreakdown
    : [];
  const underfilledPeriods = Array.isArray(metrics.underfilledPeriods)
    ? metrics.underfilledPeriods.slice(0, 12)
    : [];
  const priorityTierSummary = Array.isArray(metrics.employeeAssignmentQuality)
    ? buildPriorityTierSummary(metrics.employeeAssignmentQuality)
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
              <StatusRow
                label="Preferred day-offs remain unworked"
                value={metrics.preferredDayOffWorkedDays ?? 0}
                suffix={metricInfo.preferredDayOffWorkedDays?.description}
                tone={Number(metrics.preferredDayOffWorkedDays || 0) > 0 ? "error" : "success"}
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
                label="Preferred day-off worked days"
                value={metrics.preferredDayOffWorkedDays ?? 0}
                color={Number(metrics.preferredDayOffWorkedDays || 0) > 0 ? "error.main" : "success.main"}
                info={metricInfo.preferredDayOffWorkedDays?.description}
              />
              <MetricPanel
                label="Skill priority penalty"
                value={metrics.skillPriorityPenaltyScore ?? 0}
                info={metricInfo.skillPriorityPenaltyScore?.description}
              />
            </Box>

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

            {priorityTierSummary.length > 0 && (
              <Box mt={4}>
                <Divider sx={{ my: 1.5 }} />
                <SectionTitle>Priority Tier Summary</SectionTitle>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Priority Tier</TableCell>
                        <TableCell align="right">Employees</TableCell>
                        <TableCell align="right">Worked Hours</TableCell>
                        <TableCell align="right">Availability</TableCell>
                        <TableCell align="right">Pref. DO Worked</TableCell>
                        <TableCell align="right">Consecutive</TableCell>
                        <TableCell align="right">Min Rest</TableCell>
                        <TableCell align="right">Duration %</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {priorityTierSummary.map((row) => (
                        <TableRow key={`${row.priorityRank}-${row.priorityLabel}`}>
                          <TableCell>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                              <Chip
                                label={`#${row.priorityRank ?? "?"}`}
                                size="small"
                                sx={{
                                  height: 20,
                                  fontSize: 11,
                                  bgcolor: "#F1EFE8",
                                  color: "#5F5E5A",
                                }}
                              />
                              <Typography variant="body2" sx={{ lineHeight: 1.2 }}>
                                {row.priorityLabel || "Unmapped priority"}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell align="right">{row.employeeCount}</TableCell>
                          <TableCell align="right">{row.workedHours}</TableCell>
                          <TableCell
                            align="right"
                            sx={{ color: Number(row.availabilityViolations || 0) > 0 ? "error.main" : "success.main" }}
                          >
                            {row.availabilityViolations}
                          </TableCell>
                          <TableCell align="right">{row.preferredDayOffWorkedDays}</TableCell>
                          <TableCell align="right">{row.consecutiveDaysViolations}</TableCell>
                          <TableCell align="right">{row.minRestViolations}</TableCell>
                          <TableCell align="right">{row.durationComplianceRate}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {employeeRows.length > 0 && (
              <EmployeeAssignmentQualityPanel employeeRows={employeeRows} />
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
