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

  const renderIssueList = (list) => {
    return list.length > 0 ? (
      <ul style={{ marginTop: 4, paddingLeft: 20 }}>
        {list.map((item, idx) => (
          <li key={idx}>
            <Typography variant="body2">{item}</Typography>
          </li>
        ))}
      </ul>
    ) : null;
  };

  return (
    <CardContent sx={{ padding: 0, marginTop: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel1a-content"
          id="panel1a-header"
          sx={{ px: 2 }}
        >
          <Typography variant="h6" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Performance Indicators (KPIs)
          </Typography>
          <Box sx={{ marginLeft: 2, fontSize: "2rem", color: getStatusColor() }}>
            •
          </Box>
        </AccordionSummary>

        <AccordionDetails>
          <Paper elevation={1} sx={{ p: 2, bgcolor: "background.paper" }}>
            <Typography variant="body2" color="textSecondary" paragraph>
              Estes indicadores ajudam a monitorar possíveis conflitos de escala, sobrecarga de trabalho e férias.
            </Typography>

            <Divider sx={{ mb: 2 }} />

            <Typography variant="h6" color="primary" gutterBottom>
              Sequência inválida T-M
            </Typography>
            <Typography color={scheduleConflicts.length > 0 ? "error" : "success.main"}>
              {scheduleConflicts.length > 0
                ? "Conflitos encontrados nos dias:"
                : "Nenhum conflito encontrado."}
            </Typography>
            {renderIssueList(scheduleConflicts)}

            <Typography variant="h6" color="primary" sx={{ mt: 3 }} gutterBottom>
              Mais de 5 dias consecutivos de trabalho
            </Typography>
            <Typography color={workloadConflicts.length > 0 ? "error" : "success.main"}>
              {workloadConflicts.length > 0
                ? "Funcionários em sobrecarga:"
                : "Nenhuma sobrecarga detectada."}
            </Typography>
            {renderIssueList(workloadConflicts)}

            <Typography variant="h6" color="primary" sx={{ mt: 3 }} gutterBottom>
              Mais de 22 dias úteis trabalhados no ano
            </Typography>
            <Typography color={underworkedEmployees.length > 0 ? "error" : "success.main"}>
              {underworkedEmployees.length > 0
                ? "Funcionários com carga excessiva:"
                : "Todos os funcionários estão dentro do limite."}
            </Typography>
            {renderIssueList(underworkedEmployees)}

            <Typography variant="h6" color="primary" sx={{ mt: 3 }} gutterBottom>
              30 dias de férias por ano
            </Typography>
            <Typography color={vacationIssues.length > 0 ? "error" : "success.main"}>
              {vacationIssues.length > 0
                ? "Funcionários com férias incorretas:"
                : "Todos os registros de férias estão corretos."}
            </Typography>
            {renderIssueList(vacationIssues)}
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
