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
  Tooltip
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ErrorIcon from "@mui/icons-material/Error";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

const metricInfo = {
  tmFails: {
    label: "Afternoon-Morning Sequence",
    description: "Number of times an employee works in an afternoon shift followed by a morning shift in the day after.",
  },
  consecutiveDays: {
    label: "Consecutive Work-Day Violations",
    description: "Number of times employees exceeded the maximum allowed run of five consecutive working days.",
  },
  workHolidays: {
    label: "Holidays and Sundays Work Days",
    description: "Number of work days falling on holidays and Sundays that exceed the predefined threshold.",
  },
  missedVacationDays: {
    label: "Missed Vacation Days",
    description: "Total variance between actual and target vacation days for all employees.",
  },
  missedWorkDays: {
    label: "Missed Working Days",
    description: "Total variance between actual and target working days for all employees.",
  },
  missedTeamMin: {
    label: "Missed Minimums",
    description: "Each team, shift, and day, the count of employees below the required minimum staffing level.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description: "Number of employees allowed to work only one team but worked in more than one.",
  },
  shiftBalance: {
    label: "Shift Balance",
    description: "Percentage deviation of the most unbalanced shift distribution exhibited by any employee.",
  },
  twoTeamPreferenceLevel: {
    label: "Two Team Preference Level",
    description: "Median distribution of work between primary and secondary team for employees assigned to two teams.",
  },
};

const KPIReport = ({ metrics = {} }) => {
  const {
    tmFails = 0,
    consecutiveDays = 0,
    workHolidays = 0,
    missedVacationDays = 0,
    missedWorkDays = 0,
    missedTeamMin = 0,
    shiftBalance = 0,
    singleTeamViolations = 0,
    twoTeamPreferenceLevel = 0,
  } = metrics;

  const totalIssues = [
    tmFails,
    consecutiveDays,
    workHolidays,
    missedVacationDays,
    missedWorkDays,
    missedTeamMin,
    singleTeamViolations,
    twoTeamPreferenceLevel,
  ].filter((v) => v > 0).length;

  const getStatusChip = () =>
    totalIssues === 0 ? (
      <Chip label="No Issues" color="success" icon={<CheckCircleIcon />} />
    ) : (
      <Chip label="Issues Found" color="error" icon={<ErrorIcon />} />
    );

  const renderMetric = (key, value, isViolation, isPercentage = false) => {
    const { label, description } = metricInfo[key] || {};
    return (
      <Box>
        <Typography variant="subtitle1" fontWeight="bold" color="primary" gutterBottom>
          <Tooltip title={description || ""} arrow>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {label || key}
              <HelpOutlineIcon fontSize="small" />
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
          {value}
        </Typography>
      </Box>
    );
  };

  return (
    <CardContent sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Key Performance Indicators (KPIs)
          </Typography>
          {getStatusChip()}
        </AccordionSummary>

        <AccordionDetails>
          <Paper elevation={0} sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("tmFails", tmFails, tmFails > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("consecutiveDays", consecutiveDays, consecutiveDays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("workHolidays", workHolidays, workHolidays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("missedVacationDays", missedVacationDays, missedVacationDays > 0)}
              </Grid>
            </Grid>

            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("missedWorkDays", missedWorkDays, missedWorkDays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("missedTeamMin", missedTeamMin, missedTeamMin > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("singleTeamViolations", singleTeamViolations, singleTeamViolations > 0)}
              </Grid>
            </Grid>

            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("shiftBalance", `${shiftBalance}%`, false, true)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("twoTeamPreferenceLevel", `${twoTeamPreferenceLevel}%`, false, true)}
              </Grid>
            </Grid>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
