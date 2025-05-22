import React from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CardContent,
  Typography,
  Box,
  Paper,
  Divider,
  Chip,
  Grid,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ErrorIcon from "@mui/icons-material/Error";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

const KPIReport = ({ metrics = {} }) => {
  const {
    emFails = 0,
    consecutiveDays = 0,
    workHolidays = 0,
    missedVacationDays = 0,
  } = metrics;

  const totalIssues = [emFails, consecutiveDays, workHolidays, missedVacationDays].filter(v => v > 0).length;

  const getStatusChip = () => {
    if (totalIssues === 0) {
      return <Chip label="No Issues" color="success" icon={<CheckCircleIcon />} />;
    }
    return <Chip label="Issues Found" color="error" icon={<ErrorIcon />} />;
  };

  const renderMetric = (label, value, isViolation) => (
    <Box mb={3}>
      <Typography
        variant="subtitle1"
        fontWeight="bold"
        color="primary"
        gutterBottom
      >
        {label}
      </Typography>
      <Typography
        sx={{ mb: 0.5 }}
        color={isViolation ? "error.main" : "success.main"}
      >
        {isViolation ? "Not compliant" : "Compliant"}
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
            <Grid container spacing={3}>
              <Grid item xs={12}>
                {renderMetric(
                  "Invalid T-M Shift Sequence",
                  emFails,
                  emFails > 0
                )}
              </Grid>
              <Grid item xs={12}>
                {renderMetric(
                  "More Than 5 Consecutive Working Days",
                  consecutiveDays,
                  consecutiveDays > 0
                )}
              </Grid>
              <Grid item xs={12}>
                {renderMetric(
                  "More Than 22 Working Days on Sundays + Holidays",
                  workHolidays,
                  workHolidays > 0
                )}
              </Grid>
              <Grid item xs={12}>
                {renderMetric(
                  "30 Vacation Days Per Year",
                  missedVacationDays,
                  missedVacationDays > 0
                )}
              </Grid>
            </Grid>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
