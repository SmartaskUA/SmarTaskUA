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
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

const KPIReport = ({
  checkScheduleConflicts,
  checkWorkloadConflicts,
  checkUnderworkedEmployees,
  checkVacationDays,
}) => {
  const scheduleConflicts = checkScheduleConflicts() || [];
  const workloadConflicts = checkWorkloadConflicts() || [];
  const underworkedEmployees = checkUnderworkedEmployees() || [];
  const vacationIssues = checkVacationDays() || [];

  const totalIssues = [
    scheduleConflicts,
    workloadConflicts,
    underworkedEmployees,
    vacationIssues,
  ].filter((arr) => arr.length > 0).length;

  const getStatusChip = () => {
    if (totalIssues === 0)
      return (
        <Chip
          label="No Issues"
          color="success"
          icon={<CheckCircleIcon />}
        />
      );
    if (totalIssues <= 2)
      return (
        <Chip
          label="Some Warnings"
          color="warning"
          icon={<WarningAmberIcon />}
        />
      );
    return (
      <Chip
        label="Multiple Issues"
        color="error"
        icon={<ErrorIcon />}
      />
    );
  };

  const renderIssueList = (list) =>
    list.length > 0 && (
      <ul style={{ marginTop: 6, paddingLeft: 20 }}>
        {list.map((item, idx) => (
          <li key={idx}>
            <Typography variant="body2">
              {typeof item === "string"
                ? item
                : `${item.employee ? `Emp ${item.employee}` : ""}${
                    item.day ? ` — ${item.day}` : ""
                  }`}
            </Typography>
          </li>
        ))}
      </ul>
    );

  const renderSection = (title, data, successMsg, errorMsg) => (
    <Box mb={3}>
      <Typography
        variant="subtitle1"
        fontWeight="bold"
        color="primary"
        gutterBottom
      >
        {title}
      </Typography>
      <Typography
        sx={{ mb: 0.5 }}
        color={data.length > 0 ? "error.main" : "success.main"}
      >
        {data.length > 0 ? errorMsg : successMsg}
      </Typography>
      {renderIssueList(data)}
    </Box>
  );

  return (
    <CardContent sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{ flexGrow: 1 }}
          >
            Key Performance Indicators (KPIs)
          </Typography>
          {getStatusChip()}
        </AccordionSummary>

        <AccordionDetails>
          <Paper elevation={0} sx={{ p: 3 }}>
            <Typography
              variant="body2"
              color="text.secondary"
              mb={2}
            >
              These indicators help identify scheduling conflicts,
              overwork issues, and incorrect vacation entries.
            </Typography>

            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={3}>
              <Grid item xs={12}>
                {renderSection(
                  "Invalid T-M Shift Sequence",
                  scheduleConflicts,
                  "No conflicts found.",
                  "Conflicts found on these days:"
                )}
              </Grid>

              <Grid item xs={12}>
                {renderSection(
                  "More Than 5 Consecutive Working Days",
                  workloadConflicts,
                  "No overload detected.",
                  "Overloaded employees:"
                )}
              </Grid>

              <Grid item xs={12}>
                {renderSection(
                  "More Than 22 Working Days on Weekends/Holidays",
                  underworkedEmployees,
                  "All employees are within limits.",
                  "Employees with excessive workload:"
                )}
              </Grid>

              <Grid item xs={12}>
                {renderSection(
                  "30 Vacation Days Per Year",
                  vacationIssues,
                  "All vacation records are correct.",
                  "Employees with incorrect vacation days:"
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
