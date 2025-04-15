import React from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CardContent,
  Typography,
  Box,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

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

  const getStatusColor = () => {
    const totalIssues = [
      scheduleConflicts,
      workloadConflicts,
      underworkedEmployees,
      vacationIssues,
    ].reduce((acc, curr) => acc + (curr.length > 0 ? 1 : 0), 0);

    if (totalIssues === 0) return "success.main";
    if (totalIssues <= 2) return "warning.main";
    return "error.main";
  };

  return (
    <CardContent sx={{ display: "flex", flexDirection: "column", padding: 2, marginRight: 0 }}>
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="panel1a-content" id="panel1a-header">
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Performance Indicators (KPIs)
          </Typography>
          <Box sx={{ marginLeft: 2, fontSize: "2rem", color: getStatusColor() }}>
            •
          </Box>
        </AccordionSummary>

        <AccordionDetails>
          <Typography variant="body2" color="textSecondary" paragraph>
            These indicators help to monitor possible conflicts, overloads, and vacation periods in the work schedule.
          </Typography>

          <Typography variant="h6" color="primary">
            Invalid T-M sequence
          </Typography>
          <Typography color={scheduleConflicts.length > 0 ? "error" : "success.main"}>
            {scheduleConflicts.length > 0 ? "Conflict found" : "No conflict found."}
          </Typography>

          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            No more than 5 consecutive workdays
          </Typography>
          <Typography color={workloadConflicts.length > 0 ? "error" : "success.main"}>
            {workloadConflicts.length > 0 ? "Overload found" : "No work overload detected."}
          </Typography>

          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Max 22 workdays (Sundays and holidays) per year
          </Typography>
          <Typography color={underworkedEmployees.length > 0 ? "error" : "success.main"}>
            {underworkedEmployees.length > 0 ? "Employees with more than 22 workdays" : "All employees worked less than 22 days."}
          </Typography>

          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            30 days of vacation per year
          </Typography>
          <Typography color={vacationIssues.length > 0 ? "error" : "success.main"}>
            {vacationIssues.length > 0 ? "Vacation issues found" : "Vacation days correctly recorded."}
          </Typography>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
