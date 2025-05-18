import React from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
  Chip,
  Divider,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

const colorPalette = [
  "primary", "secondary", "success", "warning", "info", "error", 
  "default", "primary", "secondary", "success", "warning", "info"
];

const generateTeamColors = (teams) => {
  const uniqueTeams = [...new Set(teams)];
  const teamColorMapping = {};

  uniqueTeams.forEach((team, index) => {
    teamColorMapping[team] = colorPalette[index % colorPalette.length];
  });

  return teamColorMapping;
};

const MetadataInfo = ({ metadata }) => {
  if (!metadata) return null;

  const {
    scheduleName,
    algorithmType,
    vacationTemplateName,
    minimunsTemplateName,
    employeesTeamInfo,
  } = metadata;

  const allTeams = employeesTeamInfo?.reduce((acc, emp) => {
    acc.push(...emp.teams);
    return acc;
  }, []);

  const teamColors = generateTeamColors(allTeams);

  return (
    <Box mt={4}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6" fontWeight="bold">
            Metadata Summary
          </Typography>
        </AccordionSummary>

        <AccordionDetails>
          <Paper elevation={0} sx={{ padding: 2 }}>
            <Box display="flex" flexDirection="column" gap={1} mb={2}>
              <Typography variant="body1">
                <strong>Calendar Name:</strong> {scheduleName}
              </Typography>
              <Typography variant="body1">
                <strong>Algorithm:</strong> {algorithmType}
              </Typography>
              <Typography variant="body1">
                <strong>Vacation Template:</strong> {vacationTemplateName}
              </Typography>
              <Typography variant="body1">
                <strong>Minimum Template:</strong> {minimunsTemplateName}
              </Typography>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              👥 Employee Teams
              
            </Typography>

            <Table size="small" sx={{ mt: 1 }}>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Employee</strong></TableCell>
                  <TableCell><strong>Teams</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employeesTeamInfo?.map((emp, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{emp.name}</TableCell>
                    <TableCell>
                      {emp.teams.map((team, i) => (
                        <Chip
                          key={i}
                          label={team}
                          size="small"
                          color={teamColors[team] || "default"}
                          sx={{ mr: 1 }}
                        />
                      ))}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default MetadataInfo;
