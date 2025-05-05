import React from "react";
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";

const parseGroupName = (name) => {
  const parts = name.split("-");
  return {
    team: parts[0], 
    type: parts[1], 
    shift: parts[2], 
  };
};

const MinimumsTemplate = ({ name, data }) => {
  if (!data || Object.keys(data).length === 0) return null;

  const allDays = Object.values(data)[0]?.length || 0;
  const groups = Object.entries(data).map(([key, values]) => ({
    key,
    ...parseGroupName(key),
    values,
  }));

  const teams = [...new Set(groups.map(g => g.team))];
  const shifts = ["M", "T"];
  const types = ["Minimo", "Ideal"];

  return (
    <Box mt={4}>
      <Typography variant="h6" gutterBottom>
        Visualização dos Mínimos - Template: {name}
      </Typography>
      <TableContainer component={Paper} style={{ overflowX: "auto" }}>
        <Table size="small" sx={{ borderCollapse: 'collapse', minWidth: 1200 }}>
          <TableHead>
            <TableRow>
              <TableCell rowSpan={3} sx={{ border: '1px solid #ddd', fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Grupo</TableCell>
              {[...Array(allDays).keys()].map((_, i) => (
                <TableCell
                  key={`day-${i}`}
                  align="center"
                  sx={{ border: '1px solid #ddd', fontWeight: 'bold', backgroundColor: '#f5f5f5' }}
                >
                  {i + 1}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {teams.map((team) =>
              shifts.map((shift) =>
                types.map((type) => {
                  const group = groups.find(
                    (g) => g.team === team && g.shift === shift && g.type === type
                  );
                  if (!group) return null;
                  return (
                    <TableRow key={`${team}-${shift}-${type}`}>
                      <TableCell sx={{ border: '1px solid #ddd', whiteSpace: 'nowrap', fontWeight: 500 }}>
                        {team} - {shift} - {type}
                      </TableCell>
                      {group.values.map((val, i) => (
                        <TableCell
                          key={i}
                          align="center"
                          sx={{
                            border: '1px solid #ddd',
                            padding: '6px',
                            backgroundColor: "#e8f5e9",
                          }}
                        >
                          {val}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })
              )
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default MinimumsTemplate;
