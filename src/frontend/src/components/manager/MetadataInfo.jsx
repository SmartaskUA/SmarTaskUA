import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Divider,
  Button,
} from "@mui/material";
import MinimumsTemplate from "./MinimumsTemplate";
import VacationsTemplate from "./VacationsTemplate";

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
  const [showInfo, setShowInfo] = useState(false);
  const [showMinimums, setShowMinimums] = useState(false);
  const [showVacation, setShowVacation] = useState(false);

  useEffect(() => {
    console.log("Metadata Info:", metadata);
  }, [metadata]);

  if (!metadata) return null;

  const {
    scheduleName,
    algorithmType,
    vacationTemplateName,
    vacationTemplateData,
    minimunsTemplateName,
    minimunsTemplateData,
    employeesTeamInfo,
    year,
  } = metadata;

  const allTeams = employeesTeamInfo?.reduce((acc, emp) => {
    acc.push(...emp.teams);
    return acc;
  }, []);
  const teamColors = generateTeamColors(allTeams);

  return (
    <Box mt={4}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Metadata Information
      </Typography>

      <Box mb={2} display="flex" gap={2} flexWrap="wrap">
        <Button
          variant={showInfo ? "contained" : "outlined"}
          color="primary"
          onClick={() => setShowInfo(!showInfo)}
        >
          {showInfo ? "Hide Information" : "Show Information"}
        </Button>

        <Button
          variant={showMinimums ? "contained" : "outlined"}
          color="success"
          onClick={() => setShowMinimums(!showMinimums)}
        >
          {showMinimums ? "Hide Minimums" : "Show Minimums"}
        </Button>

        <Button
          variant={showVacation ? "contained" : "outlined"}
          color="warning"
          onClick={() => setShowVacation(!showVacation)}
        >
          {showVacation ? "Hide Vacation" : "Show Vacation"}
        </Button>
      </Box>

      {showInfo && (
        <Paper elevation={0} sx={{ padding: 2, mb: 3, borderRadius: 2 }}>
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
            <Typography variant="body1">
              <strong>Year:</strong> {year}
            </Typography>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Employee Teams
          </Typography>
          <Table size="small" sx={{ mt: 1 }}>
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Employee</strong>
                </TableCell>
                <TableCell>
                  <strong>Teams</strong>
                </TableCell>
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
      )}

      {showMinimums && (
        <MinimumsTemplate name={minimunsTemplateName} data={minimunsTemplateData} />
      )}

      {showVacation && (
        <VacationsTemplate name={vacationTemplateName} data={vacationTemplateData} year={year} />
      )}
    </Box>
  );
};

export default MetadataInfo;
