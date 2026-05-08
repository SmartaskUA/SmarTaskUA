import React from "react";
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
      "Fulfilled required headcount divided by total required headcount across all 30-minute team slots.",
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
      "Total missing headcount across all required 30-minute team slots.",
  },
  totalOverstaff: {
    label: "Total Overstaff",
    description:
      "Total surplus headcount above minimum requirements across all required 30-minute team slots.",
  },
  intraDayTeamSwitches: {
    label: "Intra-Day Team Switches",
    description:
      "Number of times employees switch teams between consecutive assigned segments inside the same day.",
  },
  primaryTeamUtilizationRate: {
    label: "Primary Team Utilization",
    description:
      "Share of assigned hours worked in each employee's strongest-ranked team.",
  },
  durationComplianceRate: {
    label: "Duration Compliance",
    description:
      "Share of employee-days that respect the daily duration or exact time rule defined in schedule_input.csv.",
  },
  demandedHoursComplianceRate: {
    label: "Demanded Hours Compliance",
    description:
      "Share of working-rule employee-days where assigned hours exactly match the hours requested in schedule_input.csv.",
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
  "demandedHoursComplianceRate",
];

const optionalMetrics = new Set(["fixedDaysOffViolations"]);
const percentMetrics = new Set([
  "shiftBalance",
  "teamSatisfactionLevel",
  "staffingCoverageRate",
  "weightedMinimumCoverageRate",
  "primaryTeamUtilizationRate",
  "durationComplianceRate",
  "demandedHoursComplianceRate",
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

const renderSisqualReport = (metrics) => {
  const hasIssues = sisqualIssueMetrics.some((key) => Number(metrics[key] || 0) > 0);
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
            <Typography variant="subtitle1" fontWeight={800} color="#0f172a" sx={{ mb: 2 }}>
              Coverage and Assignment Summary
            </Typography>
            <SummaryGrid metricKeys={sisqualSummaryMetrics} metrics={metrics} />

            <Box mt={3}>
              <Typography variant="subtitle1" fontWeight={800} color="#0f172a" sx={{ mb: 1.5 }}>
                Rule Checks
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={4}>
                  {renderMetric("consecutiveDaysViolations", metrics.consecutiveDaysViolations, Number(metrics.consecutiveDaysViolations || 0) > 0)}
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  {renderMetric("minRestViolations", metrics.minRestViolations, Number(metrics.minRestViolations || 0) > 0)}
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  {renderMetric("availabilityViolations", metrics.availabilityViolations, Number(metrics.availabilityViolations || 0) > 0)}
                </Grid>
              </Grid>
            </Box>
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
