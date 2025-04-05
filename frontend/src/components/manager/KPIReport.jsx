import React from "react";
import { Accordion, AccordionSummary, AccordionDetails, CardContent, Typography, Box } from "@mui/material";
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const KPIReport = ({
  checkScheduleConflicts,
  checkWorkloadConflicts,
  checkUnderworkedEmployees,
  checkVacationDays,
  checkMaxWorkdays,
  checkMaxConsecutiveWorkdays,
}) => {

  // Certifique-se de que todas as verificações retornam listas ou arrays válidos
  const scheduleConflicts = checkScheduleConflicts() || [];
  const workloadConflicts = checkWorkloadConflicts() || [];
  const underworkedEmployees = checkUnderworkedEmployees() || [];
  const vacationIssues = checkVacationDays() || [];
  const maxWorkdays = checkMaxWorkdays() || [];
  const maxConsecutiveWorkdays = checkMaxConsecutiveWorkdays() || [];

  // Função para determinar a cor do status com base no número total de problemas
  const getStatusColor = () => {
    const totalIssues = [
      scheduleConflicts,
      workloadConflicts,
      underworkedEmployees,
      vacationIssues,
      maxWorkdays,
      maxConsecutiveWorkdays
    ].reduce((acc, curr) => acc + (curr.length > 0 ? 1 : 0), 0); // Conta os arrays não vazios

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
          {/* Indicador de Cor */}
          <Box sx={{ marginLeft: 2, fontSize: "2rem", color: getStatusColor() }}>
            •
          </Box>
        </AccordionSummary>

        <AccordionDetails>
          <Typography variant="body2" color="textSecondary" paragraph>
            These indicators help to monitor possible conflicts, overloads, and vacation periods in the work schedule.
          </Typography>

          {/* Verificando Conflitos de Agendamento */}
          <Typography variant="h6" color="primary">
            Checking for Schedule Conflicts
          </Typography>
          <Typography color={scheduleConflicts.length > 0 ? "error" : "success.main"}>
            {scheduleConflicts.length > 0 ? "Conflict found" : "No conflict found."}
          </Typography>

          {/* Verificando Sobrecarga de Trabalho */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Work Overload Check
          </Typography>
          <Typography color={workloadConflicts.length > 0 ? "error" : "success.main"}>
            {workloadConflicts.length > 0 ? "Overload found" : "No work overload detected."}
          </Typography>

          {/* Funcionários com Menos de 22 Dias de Trabalho no Mês */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Employees with Less than 22 Workdays in the Month
          </Typography>
          <Typography color={underworkedEmployees.length > 0 ? "error" : "success.main"}>
            {underworkedEmployees.length > 0 ? "Employees with less than 22 workdays" : "All employees worked at least 22 days."}
          </Typography>

          {/* Verificando 30 Dias de Férias por Ano */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Checking for 30 Days of Vacation per Year
          </Typography>
          <Typography color={vacationIssues.length > 0 ? "error" : "success.main"}>
            {vacationIssues.length > 0 ? "Vacation issues found" : "Vacation days correctly recorded."}
          </Typography>
          
          {/* Verificando o Máximo de 22 Dias de Trabalho por Ano */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Maximum of 22 Workdays per Year
          </Typography>
          <Typography color={maxWorkdays.length > 0 ? "error" : "success.main"}>
            {maxWorkdays.length > 0 ? "Issues found with the workday limit" : "22 workdays per month respected."}
          </Typography>

          {/* Verificando o Máximo de 5 Dias Consecutivos de Trabalho */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Maximum of 5 Consecutive Workdays
          </Typography>
          <Typography color={maxConsecutiveWorkdays.length > 0 ? "error" : "success.main"}>
            {maxConsecutiveWorkdays.length > 0 ? "Consecutive workday conflict found" : "Limit of 5 consecutive workdays respected."}
          </Typography>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
