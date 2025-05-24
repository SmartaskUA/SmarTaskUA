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
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ErrorIcon from "@mui/icons-material/Error";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

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
    twoTeamPreferenceViolations = 0,
  } = metrics;

  // Só contam para "Issues Found" as métricas de contagem (não percentuais)
  const totalIssues = [
    tmFails,
    consecutiveDays,
    workHolidays,
    missedVacationDays,
    missedWorkDays,
    missedTeamMin,
    singleTeamViolations,
  ].filter(v => v > 0).length;

  const getStatusChip = () => {
    if (totalIssues === 0) {
      return <Chip label="No Issues" color="success" icon={<CheckCircleIcon />} />;
    }
    return <Chip label="Issues Found" color="error" icon={<ErrorIcon />} />;
  };

  const renderMetric = (label, value, isViolation, isPercentage = false) => (
    <Box>
      <Typography
        variant="subtitle1"
        fontWeight="bold"
        color="primary"
        gutterBottom
      >
        {label}
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
            {/* Linha 1 */}
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("Afternoon-Morning Sequence", tmFails, tmFails > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("Consecutive Work-Day Violations", consecutiveDays, consecutiveDays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("Holidays and Sundays Work Days", workHolidays, workHolidays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderMetric("Missed Vacation Days", missedVacationDays, missedVacationDays > 0)}
              </Grid>
            </Grid>

            {/* Linha 2 */}
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("Missed Working Days", missedWorkDays, missedWorkDays > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("Missed Minimums", missedTeamMin, missedTeamMin > 0)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("Single Team Violations", singleTeamViolations, singleTeamViolations > 0)}
              </Grid>
            </Grid>

            {/* Linha 3 – Percentagens */}
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("Shift Balance", `${shiftBalance}%`, false, true)}
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                {renderMetric("Two Team Preference Level", `${twoTeamPreferenceViolations}%`, false, true)}
              </Grid>
            </Grid>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
