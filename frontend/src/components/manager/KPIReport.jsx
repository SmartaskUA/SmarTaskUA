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

  const scheduleConflicts = checkScheduleConflicts();
  const workloadConflicts = checkWorkloadConflicts();
  const underworkedEmployees = checkUnderworkedEmployees();
  const vacationIssues = checkVacationDays();
  const maxWorkdays = checkMaxWorkdays();
  const maxConsecutiveWorkdays = checkMaxConsecutiveWorkdays();

  const getStatusColor = () => {
    const totalIssues = [
      scheduleConflicts.length,
      workloadConflicts.length,
      underworkedEmployees.length,
      vacationIssues.length,
      maxWorkdays.length,
      maxConsecutiveWorkdays.length
    ].reduce((acc, curr) => acc + (curr > 0 ? 1 : 0), 0);

    if (totalIssues === 0) return "success.main";
    if (totalIssues <= 2) return "warning.main";
    return "error.main";
  };

  return (
    <CardContent sx={{ display: "flex", flexDirection: "column", padding: 2, marginRight: 0 }}>
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="panel1a-content" id="panel1a-header">
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Indicadores de Desempenho (KPIs)
          </Typography>
          {/* Cor Indicadora */}
          <Box sx={{ marginLeft: 2, fontSize: "2rem", color: getStatusColor() }}>
            •
          </Box>
        </AccordionSummary>

        <AccordionDetails>
          <Typography variant="body2" color="textSecondary" paragraph>
            Esses indicadores ajudam a monitorar possíveis conflitos, sobrecargas e períodos de férias na escala de trabalho.
          </Typography>

          {/* Verificação de Conflitos de Agenda */}
          <Typography variant="h6" color="primary">
            Verificação de Conflitos de Agenda
          </Typography>
          <Typography color={scheduleConflicts.length > 0 ? "error" : "success.main"}>
            {scheduleConflicts.length > 0 ? "Conflito encontrado" : "Nenhum conflito encontrado."}
          </Typography>

          {/* Verificação de Sobrecarga de Trabalho */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Verificação de Sobrecarga de Trabalho
          </Typography>
          <Typography color={workloadConflicts.length > 0 ? "error" : "success.main"}>
            {workloadConflicts.length > 0 ? "Sobrecarregado encontrado" : "Nenhuma sobrecarga de trabalho detectada."}
          </Typography>

          {/* Funcionários com Menos de 22 Dias de Trabalho no Mês */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Funcionários com Menos de 22 Dias de Trabalho no Mês
          </Typography>
          <Typography color={underworkedEmployees.length > 0 ? "error" : "success.main"}>
            {underworkedEmployees.length > 0 ? "Funcionários com menos de 22 dias de trabalho" : "Todos os funcionários trabalharam pelo menos 22 dias."}
          </Typography>

          {/* Verificação de 30 Dias de Férias por Ano */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Verificação de 30 Dias de Férias por Ano
          </Typography>
          <Typography color={vacationIssues.length > 0 ? "error" : "success.main"}>
            {vacationIssues.length > 0 ? "Problemas com as férias" : "Férias registradas corretamente."}
          </Typography>

          {/* Verificação de Máximo de 22 Dias de Trabalho no Ano */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Máximo de 22 Dias de Trabalho no Ano
          </Typography>
          <Typography color={maxWorkdays.length > 0 ? "error" : "success.main"}>
            {maxWorkdays.length > 0 ? "Conflitos encontrados no limite de dias de trabalho" : "Limite de 22 dias por mês respeitado."}
          </Typography>

          {/* Verificação de Máximo de 5 Dias de Trabalho Consecutivos */}
          <Typography variant="h6" color="primary" sx={{ marginTop: 2 }}>
            Máximo de 5 Dias de Trabalho Consecutivos
          </Typography>
          <Typography color={maxConsecutiveWorkdays.length > 0 ? "error" : "success.main"}>
            {maxConsecutiveWorkdays.length > 0 ? "Conflito de dias consecutivos de trabalho encontrado" : "Limite de 5 dias consecutivos respeitado."}
          </Typography>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
